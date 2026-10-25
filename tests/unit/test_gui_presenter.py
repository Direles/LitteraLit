"""Test del presenter della GUI (Fase 6.1): ETA, digest, riepilogo, anteprima."""

import unittest

from pdfbook.domain.models import IssueKind, QAIssue, QAReport
from pdfbook.gui.presenter import (
    ProgressTracker,
    digest_lines,
    issue_digest,
    preview_pairs,
    summary_lines,
)

from .fakes import make_block, make_line, make_page


class ProgressTest(unittest.TestCase):
    def test_percent(self):
        tracker = ProgressTracker()
        tracker.begin(now=0.0, total=10)
        view = tracker.update(current=2, total=10, now=60.0)
        self.assertAlmostEqual(view.percent, 0.2)

    def test_eta_hidden_for_the_first_pages(self):
        tracker = ProgressTracker()
        tracker.begin(now=0.0, total=100)
        view = tracker.update(current=1, total=100, now=10.0)
        self.assertIsNone(view.eta_seconds)

    def test_eta_computed_from_rate(self):
        tracker = ProgressTracker()
        tracker.begin(now=0.0, total=100)
        view = tracker.update(current=10, total=100, now=60.0)
        self.assertEqual(view.eta_seconds, 540)
        self.assertAlmostEqual(view.rate_per_minute, 10.0)

    def test_no_eta_on_the_last_page(self):
        tracker = ProgressTracker()
        tracker.begin(now=0.0, total=5)
        self.assertIsNone(tracker.update(current=5, total=5, now=50.0).eta_seconds)

    def test_label_is_human_readable(self):
        tracker = ProgressTracker()
        tracker.begin(now=0.0, total=120)
        label = tracker.update(current=20, total=120, now=60.0).label()
        self.assertIn("20/120 pagine", label)
        self.assertIn("20.0 pagine/min", label)
        self.assertIn("mancano 5m 00s", label)

    def test_restart_resets_state(self):
        tracker = ProgressTracker()
        tracker.begin(now=0.0, total=10)
        tracker.update(current=5, total=10, now=30.0)
        tracker.begin(now=100.0, total=4)
        view = tracker.update(current=1, total=4, now=110.0)
        self.assertEqual(view.pages_total, 4)


class DigestTest(unittest.TestCase):
    def report(self):
        report = QAReport()
        for page, kind in ((3, IssueKind.CLIPPED), (3, IssueKind.CLIPPED), (3, IssueKind.FONT_REDUCED)):
            report.add(QAIssue(page=page, kind=kind, block="b1", detail="x"))
        report.add(QAIssue(page=7, kind=IssueKind.REPETITION, detail="y"))
        return report

    def test_grouped_by_page(self):
        digest = issue_digest(self.report())
        self.assertEqual(sum(digest[3].values()), 3)
        self.assertEqual(sum(digest[7].values()), 1)

    def test_pages_with_more_issues_come_first(self):
        self.assertEqual(list(issue_digest(self.report()))[0], 3)

    def test_lines_are_readable(self):
        lines = digest_lines(self.report())
        self.assertTrue(lines[0].startswith("pagina 3"))
        self.assertIn("clipped 2", lines[0])

    def test_limit_is_respected(self):
        self.assertEqual(len(issue_digest(self.report(), limit=1)), 1)


class SummaryTest(unittest.TestCase):
    def result(self, with_issue=False):
        from pdfbook.app.metrics import RunMetrics

        report = QAReport()
        if with_issue:
            report.add(QAIssue(page=2, kind=IssueKind.TEXT_MISSING, block="b4", detail="riga persa"))

        class FakeResult:
            resumed_pages = 2
            glossary_suggestions = ["Sprint"]
            report = None

            def violations(self):
                return [] if not with_issue else ["text_missing: 1 occorrenze"]

        FakeResult.report = report
        return FakeResult(), RunMetrics(pages=10, seconds=60.0)

    def test_lines_contain_metrics_and_gate(self):
        result, metrics = self.result()
        lines = summary_lines(result, metrics)
        self.assertTrue(any("10 pagine" in line for line in lines))
        self.assertIn("Gate: PASS", lines)
        self.assertTrue(any("Ripresa: 2" in line for line in lines))
        self.assertTrue(any("Glossario suggerito: Sprint" in line for line in lines))

    def test_failing_gate_is_explicit(self):
        result, metrics = self.result(with_issue=True)
        lines = summary_lines(result, metrics)
        self.assertIn("Gate: FAIL", lines)
        self.assertTrue(any(line.startswith("GATE:") for line in lines))
        self.assertTrue(any("riga persa" in line for line in lines))


class PreviewTest(unittest.TestCase):
    def test_pairs_follow_reading_order(self):
        page = make_page(
            make_block("b0", [make_line("primo")]),
            make_block("b1", [make_line("secondo")]),
        )
        pairs = preview_pairs(page, {"b0": "first", "b1": "second"})
        self.assertEqual(pairs, [("primo", "first"), ("secondo", "second")])

    def test_missing_translation_is_none(self):
        page = make_page(make_block("b0", [make_line("primo")]))
        self.assertEqual(preview_pairs(page, {})[0][1], None)

    def test_limit(self):
        page = make_page(*[make_block(f"b{i}", [make_line(f"riga {i}")]) for i in range(5)])
        self.assertEqual(len(preview_pairs(page, {}, limit=3)), 3)


if __name__ == "__main__":
    unittest.main()
