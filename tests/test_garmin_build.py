"""Build-wrapper failure fixtures, without executing a Garmin compiler."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from garmin.build import ROOT, main, verify_dial_resources


class GarminBuildFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        sdk = self.root / "sdk"
        java_bin = self.root / "java" / "bin"
        (sdk / "bin").mkdir(parents=True)
        java_bin.mkdir(parents=True)
        (sdk / "bin" / ("monkeyc.bat" if os.name == "nt" else "monkeyc")).write_text("unused fixture")
        (java_bin / ("java.exe" if os.name == "nt" else "java")).write_text("unused fixture")
        key = self.root / "fixture.der"
        key.write_bytes(b"not a real signing key")
        self.output = self.root / "build"
        self.arguments = ["--sdk", str(sdk), "--java-bin", str(java_bin), "--key", str(key),
                          "--output-dir", str(self.output)]

    def test_timeout_retains_partial_diagnostics_without_claiming_a_program(self):
        error = subprocess.TimeoutExpired("fixture", 300, output=b"resource error before timeout\n")
        with patch("garmin.build.subprocess.run", side_effect=error):
            self.assertEqual(main(self.arguments), 1)
        self.assertEqual((self.output / "compiler.log").read_bytes(), b"resource error before timeout\n")
        report = json.loads((self.output / "build.json").read_text())
        self.assertEqual(report["version"], "0.12.0")
        self.assertEqual(report["status"], "failed")
        self.assertIn("timeout", report["error"])
        self.assertNotIn("program", report)

    def test_nonzero_exit_preserves_partial_output_and_diagnostics(self):
        def fail(command, **kwargs):
            Path(command[command.index("-o") + 1]).write_bytes(b"incomplete program fixture")
            return subprocess.CompletedProcess(command, 7, stdout="invalid device fixture\n")
        with patch("garmin.build.subprocess.run", side_effect=fail):
            self.assertEqual(main(self.arguments), 7)
        self.assertEqual((self.output / "ClairObscur.prg").read_bytes(), b"incomplete program fixture")
        self.assertEqual((self.output / "compiler.log").read_text(), "invalid device fixture\n")
        report = json.loads((self.output / "build.json").read_text())
        self.assertEqual(report["compiler_exit_code"], 7)
        self.assertEqual(report["status"], "failed")
        self.assertNotIn("program", report)

    def test_zero_exit_without_program_is_failure(self):
        result = subprocess.CompletedProcess([], 0, stdout="no program fixture\n")
        with patch("garmin.build.subprocess.run", return_value=result):
            self.assertEqual(main(self.arguments), 1)
        report = json.loads((self.output / "build.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertNotIn("program", report)

    def test_compiler_child_cannot_inherit_an_interactive_java_override(self):
        overrides = {"_JAVA_OPTIONS": "-Djava.awt.headless=false",
                     "JDK_JAVA_OPTIONS": "-Djava.awt.headless=false",
                     "JAVA_TOOL_OPTIONS": "-Djava.awt.headless=false"}
        result = subprocess.CompletedProcess([], 1, stdout="fixture only\n")
        with patch.dict(os.environ, overrides), patch("garmin.build.subprocess.run", return_value=result) as execute:
            self.assertEqual(main(self.arguments), 1)
            child = execute.call_args.kwargs["env"]
            self.assertNotIn("_JAVA_OPTIONS", child)
            self.assertNotIn("JDK_JAVA_OPTIONS", child)
            self.assertEqual(child["JAVA_TOOL_OPTIONS"],
                             "-Djava.awt.headless=true -Xmx1g -XX:ActiveProcessorCount=2")
            self.assertEqual({key: os.environ[key] for key in overrides}, overrides)

    def test_previous_output_is_never_overwritten_or_compiled_into(self):
        self.output.mkdir()
        retained = self.output / "previous.prg"
        retained.write_bytes(b"retain exactly")
        with patch("garmin.build.subprocess.run") as execute:
            with self.assertRaises(SystemExit):
                main(self.arguments)
        execute.assert_not_called()
        self.assertEqual(list(self.output.iterdir()), [retained])
        self.assertEqual(retained.read_bytes(), b"retain exactly")

    def copied_dial_fixture(self):
        root = self.root / "source"
        for name in ("garmin/generate_dial_art.py", "garmin/watchface/source/FaceModel.mc",
                     "tokens-monochrome.json", "garmin/watchface/resources/dial/provenance.json",
                     "garmin/watchface/resources/dial/clair.png",
                     "garmin/watchface/resources/dial/obscur.png"):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        # A valid copied fixture must pass before a deliberate fault is added.
        verify_dial_resources(root)
        return root

    def test_changed_dial_png_is_rejected_before_output_or_compiler(self):
        root = self.copied_dial_fixture()
        resource = root / "garmin/watchface/resources/dial/obscur.png"
        changed = resource.read_bytes() + b"changed fixture"
        resource.write_bytes(changed)
        with patch("garmin.build.ROOT", root), patch("garmin.build.subprocess.run") as execute:
            with self.assertRaisesRegex(ValueError, "Static dial resource changed: obscur.png"):
                main(self.arguments)
        execute.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertEqual(resource.read_bytes(), changed)

    def test_changed_dial_source_is_rejected_before_output_or_compiler(self):
        root = self.copied_dial_fixture()
        source = root / "garmin/watchface/source/FaceModel.mc"
        changed = source.read_bytes() + b"\n// stale dial source fixture\n"
        source.write_bytes(changed)
        with patch("garmin.build.ROOT", root), patch("garmin.build.subprocess.run") as execute:
            with self.assertRaisesRegex(ValueError, "Static dial source changed: FaceModel.mc"):
                main(self.arguments)
        execute.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertEqual(source.read_bytes(), changed)
