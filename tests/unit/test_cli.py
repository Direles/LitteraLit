"""Test della CLI (M11): parsing argomenti, doctor, guardie sui segreti."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pdfbook.cli import _parse_pages, build_parser, main
from pdfbook.domain.models import IssueKind, QAIssue, QAReport
from pdfbook.qa.report import write_report


class ParserTest(unittest.TestCase):
    def test_translate_defaults(self):
        args = build_parser().parse_args(["translate", "in.pdf", "out.pdf"])
        self.assertEqual((args.command, args.missing_policy, args.overflow_policy),
                         ("translate", "skip", "keep_size"))

    def test_pages_parsing(self):
        self.assertEqual(_parse_pages("7"), (7, 7))
        self.assertEqual(_parse_pages("3-9"), (3, 9))
        self.assertEqual(_parse_pages(None), (None, None))

    def test_missing_command_is_an_error(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args([])


class DoctorTest(unittest.TestCase):
    def run_doctor(self, env, report_path=None):
        argv = ["doctor"] + ([report_path] if report_path else [])
        with patch.dict(os.environ, env, clear=True), redirect_stdout(io.StringIO()) as out:
            code = main(argv)
        return code, out.getvalue()

    def test_missing_key_is_reported(self):
        code, output = self.run_doctor({})
        self.assertEqual(code, 2)
        self.assertIn("PDFBOOK_API_KEY", output)

    def test_key_is_never_printed(self):
        code, output = self.run_doctor({"PDFBOOK_API_KEY": "sk-molto-segreto"})
        self.assertEqual(code, 0)
        self.assertNotIn("sk-molto-segreto", output)
        self.assertIn("has_api_key: True", output)

    def test_gate_on_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "Libro.pdf"
            report = QAReport()
            report.add(QAIssue(page=1, kind=IssueKind.FONT_REDUCED, block="b0"))
            path = write_report(pdf, report)
            code, output = self.run_doctor({"PDFBOOK_API_KEY": "k"}, str(path))
            self.assertEqual(code, 0)
            self.assertIn("PASS", output)

            broken = QAReport()
            broken.add(QAIssue(page=1, kind=IssueKind.UNTRANSLATED_UNRESOLVED, block="b0"))
            path = write_report(pdf, broken)
            code, output = self.run_doctor({"PDFBOOK_API_KEY": "k"}, str(path))
            self.assertEqual(code, 1)
            self.assertIn("FAIL", output)


class TranslateGuardTest(unittest.TestCase):
    def test_missing_key_blocks_the_run_without_network(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {}, clear=True),
            redirect_stdout(io.StringIO()),
        ):
            code = main(["translate", str(Path(tmp) / "in.pdf"), str(Path(tmp) / "out.pdf")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
