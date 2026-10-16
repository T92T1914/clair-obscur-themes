"""Compile the separate watch face with an already provisioned Connect IQ SDK."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TARGET = "fenix9pro47mm"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True, help="Installed Connect IQ SDK directory")
    parser.add_argument("--java-bin", type=Path, required=True, help="Directory containing the Java runtime executable")
    parser.add_argument("--key", type=Path, required=True, help="Private developer key outside the source tree")
    parser.add_argument("--output-dir", type=Path, required=True, help="New build directory under outputs/ or outside this repository")
    parser.add_argument("--tests", action="store_true", help="Compile SDK tests without launching or running the simulator")
    options = parser.parse_args(argv)
    sdk = options.sdk.resolve()
    java_bin = options.java_bin.resolve()
    key = options.key.resolve()
    output = options.output_dir.resolve()
    compiler = sdk / "bin" / ("monkeyc.bat" if os.name == "nt" else "monkeyc")
    java = java_bin / ("java.exe" if os.name == "nt" else "java")
    if not compiler.is_file():
        parser.error("Connect IQ compiler is missing. Complete the official SDK Manager setup first.")
    if not java.is_file():
        parser.error("The selected Java runtime is missing.")
    if not key.is_file() or key.is_relative_to(ROOT):
        parser.error("Supply an existing private developer key outside the source tree.")
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / "outputs"):
        parser.error("Build outputs inside this repository must stay under outputs/.")
    if output.exists():
        parser.error("The output directory already exists. Select a new directory to preserve the previous build.")
    # Windows batch launchers interpret shell syntax even with shell=False.
    # Keep literal paths free of command expansion and redirection characters.
    if os.name == "nt" and any(any(c in str(p) for c in '&|<>^%!"\r\n') for p in (sdk, java_bin, key, output, ROOT)):
        parser.error("The Windows compiler launcher requires paths without shell metacharacters.")

    sys.path.insert(0, str(ROOT))
    from themeforge.garmin import main as check_palette
    check_palette(["--check"])
    output.mkdir(parents=True)
    program = output / ("ClairObscur-tests.prg" if options.tests else "ClairObscur.prg")
    command = [str(compiler), "-f", str(ROOT / "garmin/watchface/monkey.jungle"),
               "-d", TARGET, "-o", str(program), "-y", str(key), "-w"]
    command += ["-t"] if options.tests else ["-r"]
    environment = os.environ.copy()
    environment["PATH"] = str(java_bin) + os.pathsep + environment.get("PATH", "")
    environment["JAVA_HOME"] = str(java_bin.parent)
    environment.pop("_JAVA_OPTIONS", None)
    environment.pop("JDK_JAVA_OPTIONS", None)
    environment["JAVA_TOOL_OPTIONS"] = "-Djava.awt.headless=true"
    report = {"target": TARGET, "test_build": options.tests, "status": "running",
              "scope": "compiler diagnostics only; no simulator, device or runtime test execution"}
    receipt = output / "build.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(command, cwd=ROOT / "garmin/watchface", env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                   timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        (output / "compiler.log").write_text(completed.stdout, encoding="utf-8")
        print(completed.stdout, end="")
        code = completed.returncode
        report["compiler_exit_code"] = code
        report["status"] = "failed" if code else "compiled"
        if code == 0:
            if not program.is_file() or program.stat().st_size == 0:
                report["status"] = "failed"
                report["error"] = "Compiler returned zero without a nonempty program."
                code = 1
            else:
                report["program"] = {"name": program.name, "bytes": program.stat().st_size,
                                     "sha256": hashlib.sha256(program.read_bytes()).hexdigest()}
    except subprocess.TimeoutExpired as error:
        partial = error.output or b""
        if isinstance(partial, str):
            partial = partial.encode("utf-8")
        (output / "compiler.log").write_bytes(partial)
        report["status"] = "failed"
        report["error"] = "Compiler exceeded the 300-second timeout. Partial diagnostics are retained."
        code = 1
    except OSError as error:
        (output / "compiler.log").write_text(str(error) + "\n", encoding="utf-8")
        report["status"] = "failed"
        report["error"] = str(error)
        code = 1
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
