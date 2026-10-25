"""Test del report QA in HTML (Fase 6.2)."""

import json
import tempfile
import unittest
from pathlib import Path

from pdfbook.qa.html_report import html_from_report, write_html

REPORT = {
    "summary": {"blocks": 10},
    "pages": [
        {
            "page": 3,
            "issues": [
                {"type": "clipped", "page": 3, "block": "b2", "detail": "sfora di 4 pt"},
                {"type": "text_missing", "page": 3, "block": "b7", "detail": "riga non disegnata"},
            ],
        },
        {
            "page": 5,
            "issues": [
                {"type": "repetition", "page": 5, "detail": "\"<script>\" ripetuto 3 volte"},
            ],
        },
    ],
}


class HtmlTest(unittest.TestCase):
    def test_contains_title_and_summary(self):
        html = html_from_report(REPORT)
        self.assertIn("Report QA", html)
        self.assertIn("3 issue", html)
        self.assertIn("2 pagine", html)

    def test_issue_rows_are_rendered(self):
        html = html_from_report(REPORT)
        self.assertIn("clipped", html)
        self.assertIn("<code>b2</code>", html)
        self.assertIn("sfora di 4 pt", html)

    def test_detail_is_escaped(self):
        html = html_from_report(REPORT)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_blocking_issues_are_highlighted(self):
        html = html_from_report(REPORT)
        self.assertIn('class="blocking"', html)

    def test_empty_report_says_so(self):
        html = html_from_report({"pages": []})
        self.assertIn("Nessuna issue", html)

    def test_counts_chips(self):
        html = html_from_report(REPORT)
        self.assertIn('<span class="count">clipped <b>1</b></span>', html)

    def test_summary_cards_are_rendered(self):
        html = html_from_report(REPORT)
        self.assertIn("blocchi", html)
        self.assertIn(">10<", html)

    def test_summary_cards_are_optional(self):
        html = html_from_report({"summary": {"cost_usd_micro": 2_500_000}, "pages": []})
        self.assertIn("2.5000", html)


class WriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.report = self.root / "libro_qa_report.json"
        self.report.write_text(json.dumps(REPORT), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_next_to_the_report(self):
        target = write_html(self.report)
        self.assertEqual(target.name, "libro_qa_report_qa_report.html")
        self.assertTrue(target.exists())
        self.assertIn("Report QA", target.read_text(encoding="utf-8"))

    def test_explicit_output_path(self):
        target = write_html(self.report, self.root / "dentro" / "r.html")
        self.assertTrue(target.exists())
        self.assertEqual(target.parent.name, "dentro")


if __name__ == "__main__":
    unittest.main()
