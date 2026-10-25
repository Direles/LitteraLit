"""Test delle metriche di run (Fase 7)."""

import unittest
from collections import Counter

from pdfbook.app.metrics import RunMetrics, format_metrics, from_summary


class DerivationTest(unittest.TestCase):
    def test_pages_per_minute(self):
        metrics = RunMetrics(pages=60, seconds=120.0)
        self.assertAlmostEqual(metrics.pages_per_minute, 30.0)

    def test_zero_seconds_does_not_divide_by_zero(self):
        self.assertEqual(RunMetrics(pages=5, seconds=0.0).pages_per_minute, 0.0)

    def test_cost_per_page(self):
        self.assertAlmostEqual(RunMetrics(pages=100, cost_usd=2.0).cost_per_page, 0.02)

    def test_cache_hit_rate(self):
        self.assertAlmostEqual(RunMetrics(cache_hits=3, cache_misses=1).cache_hit_rate, 0.75)

    def test_blocking_issues_use_the_gate(self):
        metrics = RunMetrics(issues={"glyph_missing": 2, "clipped": 9})
        self.assertEqual(metrics.blocking_issues, 2)


class FromSummaryTest(unittest.TestCase):
    def test_counters_are_mapped(self):
        summary = {"tokens_in": 100, "tokens_out": 200, "cost_usd_micro": 1_500_000, "cache_hits": 4}
        metrics = from_summary(summary, pages=10, blocks=40, seconds=30.0)
        self.assertEqual((metrics.tokens_in, metrics.tokens_out), (100, 200))
        self.assertAlmostEqual(metrics.cost_usd, 1.5)
        self.assertEqual(metrics.cache_hits, 4)

    def test_missing_counters_are_zero(self):
        metrics = from_summary({}, pages=1, blocks=1, seconds=1.0)
        self.assertEqual(metrics.cost_usd, 0.0)
        self.assertEqual(metrics.issues, {})

    def test_issue_counts_are_copied_without_zeros(self):
        counts = Counter({"clipped": 3, "repetition": 0})
        metrics = from_summary({}, pages=2, blocks=2, seconds=2.0, issue_counts=counts)
        self.assertEqual(metrics.issues, {"clipped": 3})

    def test_dict_round_trip_is_json_friendly(self):
        metrics = from_summary({"tokens_in": 10}, pages=3, blocks=9, seconds=6.0)
        payload = metrics.as_dict()
        self.assertEqual(payload["pages"], 3)
        self.assertAlmostEqual(payload["pages_per_minute"], 30.0)
        self.assertIsInstance(payload["cost_usd"], float)


class FormatTest(unittest.TestCase):
    def test_line_contains_volumes_and_speed(self):
        line = format_metrics(RunMetrics(pages=12, blocks=48, seconds=60.0))
        self.assertIn("12 pagine", line)
        self.assertIn("12.0 pagine/min", line)
        self.assertIn("48 blocchi", line)

    def test_cost_and_cache_appear_only_when_present(self):
        plain = format_metrics(RunMetrics(pages=1, seconds=1.0))
        self.assertNotIn("$", plain)
        self.assertNotIn("cache", plain)
        rich = format_metrics(
            RunMetrics(pages=2, seconds=1.0, tokens_in=5, tokens_out=5, cost_usd=0.5, cache_hits=1)
        )
        self.assertIn("$0.50", rich)
        self.assertIn("cache 100%", rich)

    def test_top_issues_are_listed(self):
        line = format_metrics(RunMetrics(pages=1, seconds=1.0, issues={"clipped": 5, "repetition": 1}))
        self.assertIn("issue: clipped 5", line)


if __name__ == "__main__":
    unittest.main()
