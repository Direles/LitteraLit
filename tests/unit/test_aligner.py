"""Test dell'allineamento (M7): righe dentro il blocco e blocchi a riga singola."""

import unittest

from pdfbook.domain.models import Line, Rect, Span, TextBlock
from pdfbook.layout.aligner import (
    alignments_for,
    line_alignment,
    single_line_alignment,
)


def line(text, x0, x1, y=10.0):
    return Line(
        spans=[Span(text=text, size=10.0)],
        bbox=Rect(x0, y - 8, x1, y + 2),
        origin_y=y,
    )


def block(lines, x0, x1):
    return TextBlock(id="b", bbox=Rect(x0, 0, x1, 100), lines=list(lines))


class LineAlignmentTest(unittest.TestCase):
    def test_full_width_line_is_left(self):
        b = block([line("piena", 0, 200)], 0, 200)
        self.assertEqual(line_alignment(b.lines[0], b), "left")

    def test_centered_line(self):
        b = block([line("titolo", 60, 140)], 0, 200)
        self.assertEqual(line_alignment(b.lines[0], b), "center")

    def test_right_aligned_line(self):
        b = block([line("firma", 120, 200)], 0, 200)
        self.assertEqual(line_alignment(b.lines[0], b), "right")

    def test_short_line_at_left_margin(self):
        b = block([line("breve", 0, 40)], 0, 200)
        self.assertEqual(line_alignment(b.lines[0], b), "left")

    def test_degenerate_geometry_is_left(self):
        b = TextBlock(id="b", bbox=Rect(0, 0, 0, 10), lines=[line("x", 0, 0)])
        self.assertEqual(line_alignment(b.lines[0], b), "left")


class SingleLineAlignmentTest(unittest.TestCase):
    def test_centered_on_page(self):
        b = block([line("Titolo", 250, 350)], 250, 350)
        self.assertEqual(single_line_alignment(b, page_width=600), "center")

    def test_wide_block_is_not_considered_centered(self):
        b = block([line("Titolo molto largo", 50, 550)], 50, 550)
        self.assertEqual(single_line_alignment(b, page_width=600), "left")

    def test_right_margin_block(self):
        b = block([line("nota", 400, 595)], 400, 595)
        self.assertEqual(single_line_alignment(b, page_width=600), "right")

    def test_left_block(self):
        b = block([line("testo", 72, 300)], 72, 300)
        self.assertEqual(single_line_alignment(b, page_width=600), "left")

    def test_zero_page_width(self):
        b = block([line("x", 0, 10)], 0, 10)
        self.assertEqual(single_line_alignment(b, page_width=0), "left")


class AlignmentsForTest(unittest.TestCase):
    def test_single_line_block_repeats_alignment(self):
        b = block([line("Titolo", 250, 350)], 250, 350)
        self.assertEqual(alignments_for(b, 600, 3), ("center", "center", "center"))

    def test_multi_line_uses_original_lines_then_last(self):
        b = block([line("prima", 0, 200), line("finale", 120, 200)], 0, 200)
        self.assertEqual(alignments_for(b, 600, 3), ("left", "right", "right"))

    def test_zero_lines(self):
        b = block([line("x", 0, 10)], 0, 10)
        self.assertEqual(alignments_for(b, 600, 0), ())


if __name__ == "__main__":
    unittest.main()
