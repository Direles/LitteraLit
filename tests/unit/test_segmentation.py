"""Test della segmentazione (M7): righe affiancate, indici, classificazione."""

import unittest

from pdfbook.domain.models import BlockKind, Line, Rect, Span, TextBlock
from pdfbook.layout.segmentation import (
    ROW_Y_TOLERANCE,
    classify_block,
    group_rows,
    has_multi_column_row,
    is_structured_block,
    toc_ratio,
)


def make_line(text, *, y=10.0, x0=0.0, width=100.0, size=10.0):
    span = Span(text=text, font_name="MinionPro-Regular", size=size)
    return Line(spans=[span], bbox=Rect(x0, y - 8, x0 + width, y + 2), origin_y=y)


def make_block(lines, *, bbox=None):
    box = bbox or Rect(0, 0, 300, 40)
    return TextBlock(id="b0", bbox=box, lines=list(lines))


class GroupRowsTest(unittest.TestCase):
    def test_same_baseline_groups_columns(self):
        left = make_line("Capitolo 18:", y=10, x0=0, width=60)
        right = make_line("Pianificare", y=10.2, x0=70, width=120)
        rows = group_rows([right, left])
        self.assertEqual(len(rows), 1)
        self.assertEqual([line.text for line in rows[0]], ["Capitolo 18:", "Pianificare"])

    def test_different_baseline_are_separate_rows(self):
        rows = group_rows([make_line("uno", y=10), make_line("due", y=25)])
        self.assertEqual(len(rows), 2)

    def test_tolerance_boundary(self):
        just_inside = make_line("b", y=10 + ROW_Y_TOLERANCE - 0.1)
        self.assertEqual(len(group_rows([make_line("a", y=10), just_inside])), 1)
        just_outside = make_line("b", y=10 + ROW_Y_TOLERANCE + 1)
        self.assertEqual(len(group_rows([make_line("a", y=10), just_outside])), 2)

    def test_rows_are_sorted_by_position(self):
        rows = group_rows([make_line("giù", y=40), make_line("su", y=10)])
        self.assertEqual([row[0].text for row in rows], ["su", "giù"])

    def test_multi_column_detection(self):
        rows = [make_line("a", y=10, x0=0, width=50), make_line("b", y=10, x0=60, width=50)]
        self.assertTrue(has_multi_column_row(rows))
        self.assertFalse(has_multi_column_row([make_line("a", y=10)]))


class TocRatioTest(unittest.TestCase):
    def test_ratio_counts_index_lines(self):
        lines = [make_line("Capitolo 1 ...... 12"), make_line("Testo normale.")]
        self.assertAlmostEqual(toc_ratio(lines), 0.5)

    def test_empty_block(self):
        self.assertEqual(toc_ratio([]), 0.0)


class StructuredTest(unittest.TestCase):
    def test_index_block_is_structured(self):
        block = make_block([
            make_line("Introduzione ...... 1", y=10),
            make_line("Capitolo 2 ...... 25", y=25),
        ])
        self.assertTrue(is_structured_block(block))

    def test_two_column_block_is_structured(self):
        block = make_block([
            make_line("Parte I:", y=10, x0=0, width=50),
            make_line("Le basi", y=10, x0=60, width=100),
        ])
        self.assertTrue(is_structured_block(block))

    def test_plain_paragraph_is_not_structured(self):
        block = make_block([
            make_line("Prima riga di un paragrafo normale.", y=10),
            make_line("Seconda riga che continua il discorso.", y=25),
        ])
        self.assertFalse(is_structured_block(block))

    def test_single_line_is_never_structured(self):
        self.assertFalse(is_structured_block(make_block([make_line("Capitolo 1 ...... 12")])))


class ClassifyTest(unittest.TestCase):
    def test_index_rows(self):
        block = make_block([
            make_line("Introduzione ...... 1"),
            make_line("Capitolo 2 ...... 25"),
        ])
        self.assertIs(classify_block(block).kind, BlockKind.TOC_ROW)

    def test_chapter_heading(self):
        self.assertIs(classify_block(make_block([make_line("CAPITOLO 18")])).kind, BlockKind.TITLE)

    def test_short_colon_heading(self):
        block = make_block([make_line("Ricetta per la Review:")])
        self.assertIs(classify_block(block).kind, BlockKind.TITLE)

    def test_list_item(self):
        self.assertIs(classify_block(make_block([make_line("■ Discuti la qualità")])).kind,
                      BlockKind.LIST_ITEM)
        self.assertIs(classify_block(make_block([make_line("1. Primo passo")])).kind,
                      BlockKind.LIST_ITEM)

    def test_paragraph(self):
        block = make_block([make_line("Questo è un paragrafo discorsivo del libro.")])
        self.assertIs(classify_block(block).kind, BlockKind.PARAGRAPH)

    def test_bare_number_is_caption_like(self):
        self.assertIs(classify_block(make_block([make_line("247")])).kind, BlockKind.CAPTION)

    def test_classify_does_not_mutate_original(self):
        block = make_block([make_line("CAPITOLO 3")])
        classify_block(block)
        self.assertIs(block.kind, BlockKind.UNKNOWN)

    def test_empty_block_is_unknown(self):
        block = TextBlock(id="b", bbox=Rect(0, 0, 10, 10), lines=[make_line("   ")])
        self.assertIs(classify_block(block).kind, BlockKind.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
