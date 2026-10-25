"""Test di prezzi e limite di frequenza (Fase 3.2/3.3)."""

import unittest

from pdfbook.config.pricing import PRICES, estimate_cost, price_for
from pdfbook.translation.ratelimit import RateLimiter


class PricingTest(unittest.TestCase):
    def test_exact_and_prefix_match(self):
        self.assertEqual(price_for("deepseek-chat"), PRICES["deepseek-chat"])
        self.assertEqual(price_for("claude-sonnet-4-5-20260101"), PRICES["claude-sonnet-4-5"])

    def test_unknown_model(self):
        self.assertIsNone(price_for("modello-inventato"))
        self.assertIsNone(estimate_cost("modello-inventato", 1000, 1000))

    def test_cost_formula(self):
        # deepseek-chat: 0.27 USD/1M input, 1.10 USD/1M output
        cost = estimate_cost("deepseek-chat", 1_000_000, 1_000_000)
        self.assertAlmostEqual(cost, 0.27 + 1.10)

    def test_negative_tokens_are_clamped(self):
        self.assertEqual(estimate_cost("deepseek-chat", -10, -10), 0.0)

    def test_empty_model(self):
        self.assertIsNone(price_for(""))


class RateLimiterTest(unittest.TestCase):
    def make(self, interval):
        now = {"value": 0.0}
        sleeps: list[float] = []

        def sleep(seconds):
            sleeps.append(seconds)
            now["value"] += seconds

        limiter = RateLimiter(interval, clock=lambda: now["value"], sleep=sleep)
        return limiter, now, sleeps

    def test_first_call_is_immediate(self):
        limiter, _, sleeps = self.make(1.0)
        limiter.wait()
        self.assertEqual(sleeps, [])

    def test_second_call_waits(self):
        limiter, _, sleeps = self.make(1.0)
        limiter.wait()
        limiter.wait()
        self.assertEqual(sleeps, [1.0])

    def test_no_limit_never_sleeps(self):
        limiter, _, sleeps = self.make(0.0)
        limiter.wait()
        limiter.wait()
        self.assertEqual(sleeps, [])

    def test_elapsed_time_is_respected(self):
        limiter, now, sleeps = self.make(1.0)
        limiter.wait()
        now["value"] = 2.0
        limiter.wait()
        self.assertEqual(sleeps, [])

    def test_from_rate(self):
        limiter = RateLimiter.from_rate(2.0)
        self.assertAlmostEqual(limiter.min_interval, 0.5)
        self.assertEqual(RateLimiter.from_rate(0).min_interval, 0.0)

    def test_negative_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            RateLimiter(-1)


if __name__ == "__main__":
    unittest.main()
