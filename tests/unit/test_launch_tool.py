"""Test delle funzioni pure del lanciatore (tools/launch.py)."""

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("pdfbook_launch", ROOT / "tools" / "launch.py")
launch = importlib.util.module_from_spec(SPEC)
sys.modules["pdfbook_launch"] = launch
SPEC.loader.exec_module(launch)


class VenvPathTest(unittest.TestCase):
    def test_windows_layout(self):
        path = launch.venv_python(Path(".venv"), platform="win32")
        self.assertEqual(path.as_posix(), ".venv/Scripts/python.exe")

    def test_unix_layout(self):
        for platform in ("darwin", "linux"):
            path = launch.venv_python(Path(".venv"), platform=platform)
            self.assertEqual(path.as_posix(), ".venv/bin/python")


class LaunchersTest(unittest.TestCase):
    def test_windows_prefers_py_launcher(self):
        self.assertEqual(launch.python_candidates(platform="win32")[0], ["py", "-3"])

    def test_unix_prefers_python3(self):
        self.assertEqual(launch.python_candidates(platform="linux")[0], ["python3"])

    def test_launchers_exist_for_every_platform(self):
        for name in ("start.cmd", "start.command", "start.sh"):
            self.assertTrue((ROOT / name).exists(), name)


class CommandTest(unittest.TestCase):
    def test_no_arguments_opens_the_gui(self):
        self.assertEqual(launch.cli_command([]), ["-m", "pdfbook.cli", "gui"])

    def test_arguments_are_forwarded(self):
        self.assertEqual(
            launch.cli_command(["doctor", "report.json"]),
            ["-m", "pdfbook.cli", "doctor", "report.json"],
        )


if __name__ == "__main__":
    unittest.main()
