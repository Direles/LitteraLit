"""Test del riconoscimento tabelle (Fase 2.3)."""

import unittest

from pdfbook.domain.models import BlockKind, Rect

from .fakes import make_block, make_line, make_page


def cell(text, x0, y0, width=90.0):
    return make_block(f"c_{x0}_{y0}", [make_line(text, x0=x0, y0=y0, width=width)])


def row(y0, texts, x_positions=(60.0, 200.0, 340.0)):
    return [cell(text, x, y0) for text, x in zip(texts, x_positions, strict=True)]


def grid_page(rows=3, *, number=1):
    blocks = []
    for index in range(rows):
        blocks.extend(row(200.0 + index * 20.0, (f"voce{index}a", f"voce{index}b", f"voce{index}c")))
    return make_page(*blocks, number=number)


class DetectionTest(unittest.TestCase):
    def test_grid_is_detected(self):
        from pdfbook.layout.tables import detect_tables

        tables = detect_tables(grid_page(3))
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].column_count, 3)
        self.assertEqual(len(tables[0].rows), 3)
        self.assertEqual(len(tables[0].cells), 9)

    def test_two_rows_are_not_enough(self):
        from pdfbook.layout.tables import detect_tables

        self.assertEqual(detect_tables(grid_page(2)), [])

    def test_single_column_is_not_a_table(self):
        from pdfbook.layout.tables import detect_tables

        blocks = [cell(f"riga {index}", 60.0, 200.0 + index * 20.0) for index in range(4)]
        self.assertEqual(detect_tables(make_page(*blocks)), [])

    def test_misaligned_columns_break_the_table(self):
        from pdfbook.layout.tables import detect_tables

        page = grid_page(3)
        page.blocks[3].bbox = Rect(300.0, page.blocks[3].bbox.y0, 390.0, page.blocks[3].bbox.y1)
        self.assertEqual(detect_tables(page), [])

    def test_multi_line_paragraphs_are_ignored(self):
        from pdfbook.layout.tables import detect_tables

        blocks = []
        for index in range(3):
            blocks.append(
                make_block(
                    f"p{index}",
                    [make_line("testo lungo", y0=200.0 + index * 20.0)],
                )
            )
        self.assertEqual(detect_tables(make_page(*blocks)), [])

    def test_long_cells_are_ignored(self):
        from pdfbook.layout.tables import detect_tables

        blocks = []
        for index in range(3):
            blocks.extend(row(200.0 + index * 20.0, ("x" * 300, "y" * 300, "z" * 300)))
        self.assertEqual(detect_tables(make_page(*blocks)), [])

    def test_two_separate_tables(self):
        from pdfbook.layout.tables import detect_tables

        blocks = []
        for index in range(3):
            blocks.extend(row(200.0 + index * 20.0, ("a", "b"), x_positions=(60.0, 200.0)))
        for index in range(3):
            blocks.extend(row(400.0 + index * 20.0, ("c", "d"), x_positions=(60.0, 200.0)))
        tables = detect_tables(make_page(*blocks))
        self.assertEqual(len(tables), 2)


class MarkTest(unittest.TestCase):
    def test_cells_are_marked(self):
        from pdfbook.layout.tables import mark_tables

        page = mark_tables(grid_page(3))
        kinds = [block.kind for block in page.blocks]
        self.assertEqual(set(kinds), {BlockKind.TABLE_CELL})

    def test_page_without_tables_is_untouched(self):
        from pdfbook.layout.tables import mark_tables

        page = make_page(make_block("b0", [make_line("un paragrafo normale")]))
        self.assertIs(mark_tables(page), page)

    def test_explicit_kind_survives_classification(self):
        from pdfbook.layout.segmentation import classify_block
        from pdfbook.layout.tables import mark_tables

        page = mark_tables(grid_page(3))
        classified = classify_block(page.blocks[0])
        self.assertIs(classified.kind, BlockKind.TABLE_CELL)


if __name__ == "__main__":
    unittest.main()
