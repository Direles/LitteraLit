"""Test del report QA (M10): formato compatibile, atomicità, gate."""

import json
import tempfile
import unittest
from pathlib import Path

from pdfbook.domain.models import IssueKind, QAIssue, QAReport
from pdfbook.qa.report import (
    GATE_KINDS,
    gate,
    parse_report,
    report_path,
    write_report,
)


def sample_report():
    report = QAReport()
    report.add(QAIssue(page=2, kind=IssueKind.FONT_REDUCED, block="b1", detail="9.0pt -> 7.0pt"))
    report.add(QAIssue(page=2, kind=IssueKind.OVERFLOW_SHIFTED, detail="shift 4.2pt"))
    report.add(QAIssue(page=3, kind=IssueKind.UNTRANSLATED_UNRESOLVED, block="multiple"))
    return report


class ReportPathTest(unittest.TestCase):
    def test_suffix_next_to_pdf(self):
        self.assertEqual(report_path("libri/Libro.pdf").name, "Libro_qa_report.json")

    def test_idempotent_on_report_path(self):
        self.assertEqual(report_path("Libro_qa_report.json").name, "Libro_qa_report.json")

    def test_extension_agnostic(self):
        self.assertEqual(report_path(Path("out/Prova.ITALIANO.pdf")).name, "Prova.ITALIANO_qa_report.json")


class WriteReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf = Path(self.tmp.name) / "Libro.pdf"

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_file_with_legacy_shape(self):
        written = write_report(self.pdf, sample_report())
        self.assertTrue(written.exists())
        payload = json.loads(written.read_text(encoding="utf-8"))
        self.assertIn("pages", payload)
        self.assertIn("summary", payload)
        self.assertEqual(payload["summary"]["font_reduced"], 1)
        self.assertEqual(payload["pages"][0]["page"], 2)

    def test_atomic_write_leaves_no_temp_file(self):
        write_report(self.pdf, sample_report())
        leftovers = [p.name for p in self.pdf.parent.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_extra_counters_are_merged(self):
        written = write_report(self.pdf, sample_report(), counters={"blocks": 42, "perfect": 40})
        summary = json.loads(written.read_text(encoding="utf-8"))["summary"]
        self.assertEqual(summary["blocks"], 42)
        self.assertEqual(summary["font_reduced"], 1)

    def test_roundtrip_through_parse(self):
        written = write_report(self.pdf, sample_report())
        parsed = parse_report(written)
        self.assertEqual(len(parsed.issues), 3)
        self.assertEqual(parsed.count(IssueKind.UNTRANSLATED_UNRESOLVED), 1)


class ParseLegacyTest(unittest.TestCase):
    def test_accepts_legacy_payload_with_string_block(self):
        payload = {
            "pages": [{"page": 1, "issues": [
                {"block": "multiple", "type": "untranslated_unresolved", "detail": "3 blocchi"},
                {"block": 4, "type": "font_reduced", "detail": "9.0pt -> 6.5pt"},
            ]}],
            "summary": {"blocks": 4207, "perfect": 4109},
        }
        report = parse_report(payload)
        self.assertEqual(len(report.issues), 2)
        self.assertEqual(report.issues[0].block, "multiple")
        self.assertEqual(report.issues[1].block, "4")

    def test_unknown_types_are_ignored(self):
        payload = {"pages": [{"page": 1, "issues": [{"type": "nuovo_tipo_sconosciuto"}]}]}
        self.assertEqual(len(parse_report(payload).issues), 0)

    def test_malformed_file_returns_empty_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "x.json"
            broken.write_text("{non json", encoding="utf-8")
            self.assertEqual(len(parse_report(broken).issues), 0)

    def test_missing_file_returns_empty_report(self):
        self.assertEqual(len(parse_report("non_esiste.json").issues), 0)


class GateTest(unittest.TestCase):
    def test_clean_report_passes(self):
        report = QAReport()
        report.add(QAIssue(page=1, kind=IssueKind.FONT_REDUCED, block="b1"))
        self.assertEqual(gate(report), [])

    def test_untranslated_blocks_fail(self):
        violations = gate(sample_report())
        self.assertEqual(len(violations), 1)
        self.assertIn("untranslated_unresolved", violations[0])

    def test_custom_gate_kinds(self):
        report = QAReport()
        report.add(QAIssue(page=1, kind=IssueKind.TEXT_OVERLAP, block="b2"))
        self.assertEqual(gate(report), [])
        self.assertEqual(len(gate(report, kinds=(IssueKind.TEXT_OVERLAP,))), 1)

    def test_gate_kinds_are_declared(self):
        self.assertIn(IssueKind.GLYPH_MISSING, GATE_KINDS)
        self.assertIn(IssueKind.TEXT_MISSING, GATE_KINDS)


if __name__ == "__main__":
    unittest.main()
