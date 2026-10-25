"""Test della geometria dei run (M9): baseline, allineamenti, shift, altezze."""

import unittest

from pdfbook.domain.models import Rect
from pdfbook.rendering.runs import (
    baselines_for,
    column_x,
    extra_height,
    shift_for,
    tail,
    x_for,
)

from .fakes import FakeResolver, make_block, make_line


class BaselinesTest(unittest.TestCase):
    def test_reuses_original_baselines(self):
        block = make_block("b0", [make_line("a", y0=100.0), make_line("b", y0=112.0)])
        self.assertEqual(baselines_for(block, 10.0, 2, 5.0), [115.0, 127.0])

    def test_computes_extra_baselines_with_shift(self):
        block = make_block("b0", [make_line("a", y0=100.0)])
        self.assertEqual(
            [round(value, 2) for value in baselines_for(block, 8.0, 3, 2.0)],
            [112.0, 122.0, 132.0],
        )


class PositionsTest(unittest.TestCase):
    def test_left_center_right(self):
        self.assertEqual(x_for(10.0, 100.0, 20.0, "left"), 10.0)
        self.assertEqual(x_for(10.0, 100.0, 20.0, "center"), 50.0)
        self.assertEqual(x_for(10.0, 100.0, 20.0, "right"), 90.0)

    def test_column_positions_use_column_margin(self):
        self.assertEqual(column_x(80.0, 300.0, 100.0, 20.0, "left"), 80.0)
        self.assertEqual(column_x(80.0, 300.0, 100.0, 20.0, "center"), 120.0)
        self.assertEqual(column_x(80.0, 300.0, 100.0, 20.0, "right"), 278.0)

    def test_column_right_never_crosses_column_start(self):
        self.assertEqual(column_x(80.0, 90.0, 100.0, 60.0, "right"), 80.0)


class ShiftTest(unittest.TestCase):
    def test_no_overlap_no_shift(self):
        self.assertEqual(shift_for(Rect(0, 100, 100, 120), [(Rect(200, 0, 300, 50), 80.0)]), 0.0)

    def test_overlap_uses_max_overflow(self):
        placed = [(Rect(0, 100, 100, 120), 130.0), (Rect(0, 100, 100, 120), 140.0)]
        self.assertEqual(shift_for(Rect(10, 120, 90, 140), placed), 20.0)

    def test_overflow_never_negative(self):
        self.assertEqual(shift_for(Rect(0, 0, 10, 10), [(Rect(0, 0, 10, 10), 5.0)]), 0.0)


class HeightTest(unittest.TestCase):
    def test_extra_height_for_multi_line_column(self):
        runs = [
            type("R", (), {"size": 10.0, "text": "a"})(),
            type("R", (), {"size": 10.0, "text": "b"})(),
        ]
        self.assertAlmostEqual(extra_height(runs), 12.5)

    def test_single_line_has_no_extra_height(self):
        self.assertEqual(extra_height([type("R", (), {"size": 10.0})()]), 0.0)
        self.assertEqual(extra_height([]), 0.0)

    def test_tail_scales_with_size(self):
        self.assertAlmostEqual(tail([type("R", (), {"size": 20.0})()]), 6.0)
        self.assertEqual(tail([]), 0.0)


class ResolverUsageTest(unittest.TestCase):
    def test_runs_resolve_font_by_span_name(self):
        from pdfbook.rendering.runs import prose_runs

        resolver = FakeResolver()
        block = make_block("b0", [make_line("ciao")])
        prose_runs(
            block, lines=["ciao"], size=10.0, baselines=[110.0], alignments=["left"], resolver=resolver
        )
        self.assertEqual(resolver.resolved, ["MinionPro-Regular"])


if __name__ == "__main__":
    unittest.main()
