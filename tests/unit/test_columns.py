"""Test dell'ordine di lettura multi-colonna (Fase 2.5)."""

import unittest
from dataclasses import replace

from pdfbook.domain.models import Rect
from pdfbook.layout.columns import apply_reading_order, detect_columns, reading_order

from .fakes import make_block, make_line, make_page


def block(block_id, x0, x1, y0, y1):
    built = make_block(block_id, [make_line(f"testo {block_id}", y0=y0 + 10)])
    return replace(built, bbox=Rect(x0, y0, x1, y1))


def two_column_page():
    # Ordine di estrazione intercalato: sinistra, destra, sinistra, destra.
    return make_page(
        block("b0", 40, 280, 100, 140),
        block("b1", 320, 560, 100, 140),
        block("b2", 40, 280, 160, 200),
        block("b3", 320, 560, 160, 200),
    )


class DetectTest(unittest.TestCase):
    def test_two_columns_are_found(self):
        columns = detect_columns(two_column_page().blocks, 612.0)
        self.assertEqual(len(columns), 2)
        self.assertEqual(columns[0].blocks, ("b0", "b2"))
        self.assertEqual(columns[1].blocks, ("b1", "b3"))

    def test_single_column_page_has_no_columns(self):
        page = make_page(block("b0", 40, 560, 100, 140), block("b1", 40, 560, 160, 200))
        self.assertEqual(detect_columns(page.blocks, 612.0), [])

    def test_small_gutter_is_not_a_column_split(self):
        page = make_page(
            block("b0", 40, 290, 100, 140),
            block("b1", 295, 560, 100, 140),
            block("b2", 40, 290, 160, 200),
            block("b3", 295, 560, 160, 200),
        )
        self.assertEqual(detect_columns(page.blocks, 612.0), [])

    def test_one_sided_blocks_are_not_columns(self):
        page = make_page(
            block("b0", 40, 280, 100, 140),
            block("b1", 320, 560, 100, 140),
            block("b2", 40, 280, 160, 200),
        )
        self.assertEqual(detect_columns(page.blocks, 612.0), [])


class OrderTest(unittest.TestCase):
    def test_reading_order_is_column_by_column(self):
        self.assertEqual(reading_order(two_column_page().blocks, 612.0), ["b0", "b2", "b1", "b3"])

    def test_single_column_keeps_order(self):
        page = make_page(block("b1", 40, 560, 100, 140), block("b0", 40, 560, 160, 200))
        self.assertEqual(reading_order(page.blocks, 612.0), ["b1", "b0"])

    def test_full_width_title_above_columns_comes_first(self):
        page = two_column_page()
        page.blocks.insert(0, block("title", 40, 560, 40, 70))
        self.assertEqual(reading_order(page.blocks, 612.0)[0], "title")

    def test_full_width_block_inside_columns_is_ambiguous(self):
        page = two_column_page()
        page.blocks.append(block("figure", 40, 560, 145, 155))
        self.assertEqual(
            reading_order(page.blocks, 612.0), [b.id for b in page.blocks]
        )

    def test_full_width_block_below_columns_comes_last(self):
        page = two_column_page()
        page.blocks.append(block("foot", 40, 560, 220, 250))
        self.assertEqual(reading_order(page.blocks, 612.0)[-1], "foot")

    def test_apply_reading_order_is_identity_without_columns(self):
        page = make_page(block("b0", 40, 560, 100, 140))
        self.assertIs(apply_reading_order(page), page)

    def test_apply_reading_order_reorders_blocks(self):
        page = apply_reading_order(two_column_page())
        self.assertEqual([b.id for b in page.blocks], ["b0", "b2", "b1", "b3"])
        self.assertEqual(page.blocks[1].bbox.x0, 40.0)

    def test_build_plans_uses_column_order(self):
        from pdfbook.app.page_plan import build_plans

        plans = build_plans([two_column_page()], stitch=False, furniture=False)
        self.assertEqual(list(plans[0].requests), ["b0", "b2", "b1", "b3"])


if __name__ == "__main__":
    unittest.main()
