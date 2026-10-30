"""Actual activity lifecycle logic on a synthetic JVM host, not phone acceptance."""

import importlib.util
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "android_activity_lifecycle_fixture",
    ROOT / "tests/fixtures/android_activity_lifecycle.py",
)
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


def java_tools():
    """Use an existing matching JDK; this test never installs one."""
    configured = os.environ.get("THEME_TEST_JAVA_BIN")
    executable = ".exe" if os.name == "nt" else ""
    if configured:
        directory = Path(configured).expanduser().resolve()
    else:
        compiler = shutil.which("javac")
        if not compiler:
            return None
        directory = Path(compiler).resolve().parent
    java = directory / ("java" + executable)
    javac = directory / ("javac" + executable)
    release = directory.parent / "release"
    if not java.is_file() or not javac.is_file() or not release.is_file():
        return None
    version = re.search(r'JAVA_VERSION="(\d+)', release.read_text(encoding="utf-8"))
    if not version or int(version[1]) < 17:
        return None
    return java, javac


def limit_owned_process(process):
    """Apply conservative controls only to the child created by this test."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessAffinityMask.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)
        ]
        kernel.GetProcessAffinityMask.restype = wintypes.BOOL
        kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        kernel.SetProcessAffinityMask.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x0200 | 0x0400, False, process.pid)
        if not handle:
            raise OSError(ctypes.get_last_error(), "Cannot control owned JVM process")
        try:
            allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
            if not kernel.GetProcessAffinityMask(handle, ctypes.byref(allowed), ctypes.byref(system)):
                raise OSError(ctypes.get_last_error(), "Cannot read owned JVM affinity")
            one_cpu = allowed.value & -allowed.value
            if not one_cpu or not kernel.SetProcessAffinityMask(handle, one_cpu):
                raise OSError(ctypes.get_last_error(), "Cannot limit owned JVM to one CPU")
        finally:
            kernel.CloseHandle(handle)
    else:
        if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(process.pid, {min(os.sched_getaffinity(process.pid))})
        if hasattr(os, "setpriority"):
            os.setpriority(os.PRIO_PROCESS, process.pid, max(10, os.getpriority(os.PRIO_PROCESS, process.pid)))


def stop_owned_process(process):
    if process.poll() is None:
        if os.name == "nt":
            # These exact compiler/harness commands create JVM threads, not child
            # processes. TerminateProcess stops those threads with their owner.
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    process.communicate(timeout=10)


def run_bounded(command, directory, environment):
    options = {"start_new_session": True}
    if os.name == "nt":
        options = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS}
    process = subprocess.Popen(
        command, cwd=directory, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
        errors="replace", shell=False, **options,
    )
    try:
        limit_owned_process(process)
        stdout, stderr = process.communicate(timeout=45)
    except BaseException:
        stop_owned_process(process)
        raise
    finally:
        if process.poll() is None:
            stop_owned_process(process)
    return process.returncode, stdout, stderr


class ActivityLifecycleHostTests(unittest.TestCase):
    def test_completed_report_lifecycle_without_inventory_persistence_or_rescan(self):
        tools = java_tools()
        if tools is None:
            self.skipTest("JDK17+ unavailable; set THEME_TEST_JAVA_BIN or put a matching JDK on PATH")
        java, javac = tools
        temporary_base = Path(tempfile.gettempdir()).resolve()
        with tempfile.TemporaryDirectory(prefix="themes-activity-lifecycle-") as temporary:
            root = Path(temporary).resolve()
            self.assertEqual(root.parent, temporary_base)
            self.assertTrue(root.name.startswith("themes-activity-lifecycle-"))
            actual_source = ROOT / "android/app/src/io/github/t92t1914/obscuricons/IconPackActivity.java"
            source_bytes = actual_source.read_bytes()
            sources, assets = FIXTURE.write_fixture(
                root, actual_source, ROOT / "android/app/res/values/strings.xml"
            )
            self.assertEqual(sources[0].read_bytes(), source_bytes)
            classes = root / "classes"
            classes.mkdir()
            owned_temp = root / "owned-temp"
            owned_temp.mkdir()
            environment = os.environ.copy()
            for key in ("JAVA_TOOL_OPTIONS", "_JAVA_OPTIONS", "JDK_JAVA_OPTIONS", "CLASSPATH"):
                environment.pop(key, None)
            for key in ("TEMP", "TMP", "TMPDIR"):
                environment[key] = str(owned_temp)
            compile_command = [
                str(javac), "-J-Xmx256m", "-J-XX:ActiveProcessorCount=1",
                "-J-XX:-UsePerfData", "-J-Djava.awt.headless=true",
                "-encoding", "UTF-8", "-proc:none", "-g:none", "-d", str(classes),
                *map(str, sources),
            ]
            code, stdout, stderr = run_bounded(compile_command, root, environment)
            self.assertEqual(code, 0, f"Host fixture did not compile:\n{stdout}\n{stderr}")
            self.assertEqual(stderr, "", stderr)
            code, stdout, stderr = run_bounded([
                str(java), "-Xmx128m", "-XX:ActiveProcessorCount=1", "-XX:-UsePerfData",
                "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8",
                "-Djava.io.tmpdir=" + str(owned_temp), "-cp", str(classes),
                "host.LifecycleWitness", str(assets),
            ], root, environment)
            self.assertEqual(code, 0, f"Actual activity host contract failed:\n{stdout}\n{stderr}")
            self.assertEqual(stderr, "", stderr)
            self.assertEqual(sum(line.startswith("PASS ") for line in stdout.splitlines()), 29, stdout)
            self.assertFalse(any(line.startswith("FAIL ") for line in stdout.splitlines()), stdout)
            self.assertIn("RESULT failures=0 activeCoverageWorkers=0", stdout)
            self.assertEqual(actual_source.read_bytes(), source_bytes)
            self.assertEqual(list(owned_temp.iterdir()), [])
            print("Activity lifecycle host: 29 synthetic checks passed; no Android/device qualification.")
        self.assertFalse(root.exists(), "Owned fixture directory was not removed")


if __name__ == "__main__":
    unittest.main()
