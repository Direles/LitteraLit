"""Test dei controlli geometrici (P0.5): sovrapposizioni e clipping."""

import unittest
from types import SimpleNamespace

from pdfbook.domain.models import IssueKind
from pdfbook.qa.checks_geometry import MAX_ISSUES_PER_PAGE, check_page_geometry, run_box


def item(text="testo", *, x=100.0, baseline=200.0, size=10.0, width=60.0, block="b0"):
    return SimpleNamespace(x=x, baseline_y=baseline, text=text, size=size, width=width, block_id=block)


class BoxTest(unittest.TestCase):
    def test_box_is_built_around_the_baseline(self):
        box = run_box(item(size=10.0, width=50.0))
        self.assertAlmostEqual(box.x0, 100.0)
        self.assertAlmostEqual(box.x1, 150.0)
        self.assertAlmostEqual(box.y0, 192.0)
        self.assertAlmostEqual(box.y1, 202.5)

    def test_zero_width_uses_text_estimate(self):
        box = run_box(item(text="abcdef", size=10.0, width=0.0))
        self.assertGreater(box.width, 0)


class OverlapTest(unittest.TestCase):
    def test_overlapping_blocks_are_flagged(self):
        issues = check_page_geometry(
            3, [item(block="b0"), item(block="b1", baseline=201.0)], page_width=612, page_height=792
        )
        self.assertEqual([issue.kind for issue in issues], [IssueKind.TEXT_OVERLAP])
        self.assertEqual(issues[0].block, "b0")
        self.assertIn("b1", issues[0].detail)

    def test_same_block_lines_never_overlap(self):
        issues = check_page_geometry(
            1, [item(block="b0"), item(block="b0", baseline=201.0)], page_width=612, page_height=792
        )
        self.assertEqual(issues, [])

    def test_adjacent_lines_are_not_overlaps(self):
        issues = check_page_geometry(
            1,
            [item(block="b0", baseline=200.0), item(block="b1", baseline=213.0)],
            page_width=612,
            page_height=792,
        )
        self.assertEqual(issues, [])

    def test_slight_contact_is_tolerated(self):
        issues = check_page_geometry(
            1,
            [item(block="b0", baseline=200.0), item(block="b1", baseline=210.5)],
            page_width=612,
            page_height=792,
        )
        self.assertEqual(issues, [])

    def test_many_overlaps_are_capped(self):
        items = [item(block=f"b{index}", baseline=200.0 + index * 0.1) for index in range(12)]
        issues = check_page_geometry(1, items, page_width=612, page_height=792)
        self.assertLessEqual(len(issues), MAX_ISSUES_PER_PAGE)

    def test_blank_runs_are_ignored(self):
        issues = check_page_geometry(
            1, [item(text="   "), item(text=" ", baseline=201.0)], page_width=612, page_height=792
        )
        self.assertEqual(issues, [])


class ClippingTest(unittest.TestCase):
    def test_beyond_right_margin(self):
        issues = check_page_geometry(1, [item(x=600.0, width=40.0)], page_width=612, page_height=792)
        self.assertEqual(issues[0].kind, IssueKind.CLIPPED)
        self.assertIn("destro", issues[0].detail)

    def test_before_left_margin(self):
        issues = check_page_geometry(1, [item(x=-10.0)], page_width=612, page_height=792)
        self.assertEqual(issues[0].kind, IssueKind.CLIPPED)
        self.assertIn("sinistro", issues[0].detail)

    def test_below_page(self):
        issues = check_page_geometry(1, [item(baseline=800.0)], page_width=612, page_height=792)
        self.assertEqual(issues[0].kind, IssueKind.CLIPPED)
        self.assertIn("sotto", issues[0].detail)

    def test_above_page(self):
        issues = check_page_geometry(1, [item(baseline=-5.0)], page_width=612, page_height=792)
        self.assertEqual(issues[0].kind, IssueKind.CLIPPED)
        self.assertIn("sopra", issues[0].detail)

    def test_within_tolerance(self):
        issues = check_page_geometry(1, [item(x=600.0, width=10.0)], page_width=612, page_height=792)
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
