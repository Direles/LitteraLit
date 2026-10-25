"""Test dell'estrattore (M8) su dizionari compatibili con PyMuPDF: nessun PDF aperto."""

import unittest

from pdfbook.extraction.pdf_extractor import (
    block_from_raw,
    extract_page,
    image_box,
    is_text_block,
    line_from_raw,
    span_from_raw,
)


def raw_span(text="ciao", *, size=10.0, font="MinionPro-Regular", origin=(72.0, 100.0), color=0):
    return {
        "text": text,
        "font": font,
        "size": size,
        "color": color,
        "origin": origin,
        "bbox": (72.0, 90.0, 172.0, 102.0),
    }


def raw_line(*spans, bbox=(72.0, 90.0, 200.0, 102.0)):
    return {"spans": list(spans) or [raw_span()], "bbox": bbox}


def raw_block(*lines, bbox=(72.0, 90.0, 400.0, 200.0), kind=0):
    return {"type": kind, "bbox": bbox, "lines": list(lines) or [raw_line()]}


class SpanTest(unittest.TestCase):
    def test_full_span(self):
        span = span_from_raw(raw_span("prova", size=9.5, color=255))
        self.assertEqual((span.text, span.size, span.color), ("prova", 9.5, 255))

    def test_missing_fields_are_neutral(self):
        span = span_from_raw({"text": "x"})
        self.assertEqual((span.font_name, span.size, span.color), ("", 0.0, 0))


class LineTest(unittest.TestCase):
    def test_line_uses_span_origin(self):
        line = line_from_raw(raw_line(raw_span(origin=(72.0, 111.5))))
        self.assertAlmostEqual(line.origin_y, 111.5)

    def test_origin_fallback_from_bbox(self):
        span = raw_span(size=10.0)
        span["origin"] = None
        line = line_from_raw(raw_line(span, bbox=(0.0, 0.0, 50.0, 12.0)))
        self.assertAlmostEqual(line.origin_y, 10.0)

    def test_blank_lines_are_dropped(self):
        self.assertIsNone(line_from_raw(raw_line(raw_span("   "))))

    def test_line_without_spans(self):
        self.assertIsNone(line_from_raw({"spans": [], "bbox": (0, 0, 10, 10)}))

    def test_invalid_bbox_is_dropped(self):
        self.assertIsNone(line_from_raw(raw_line(bbox=(100, 100, 10, 10))))

    def test_multiple_spans_are_concatenated(self):
        line = line_from_raw(raw_line(raw_span("Ciao "), raw_span("mondo")))
        self.assertEqual(line.text, "Ciao mondo")


class BlockTest(unittest.TestCase):
    def test_block_id_and_lines(self):
        block = block_from_raw(raw_block(raw_line(), raw_line()), index=3)
        self.assertEqual((block.id, block.line_count), ("b3", 2))

    def test_block_without_valid_lines(self):
        self.assertIsNone(block_from_raw(raw_block(raw_line(raw_span(" ")))))

    def test_block_bbox_is_recovered_from_lines(self):
        block = block_from_raw({"type": 0, "lines": [raw_line(bbox=(10, 20, 110, 40))]})
        self.assertEqual(block.bbox.normalized(), (10, 20, 110, 40))


class PageTest(unittest.TestCase):
    def test_separation_between_text_and_obstacles(self):
        page = extract_page(
            {"blocks": [
                raw_block(),
                {"type": 1, "bbox": (0.0, 0.0, 600.0, 300.0)},
                raw_block(raw_line(raw_span("secondo"))),
            ]},
            number=4,
            width=612.0,
            height=792.0,
        )
        self.assertEqual(page.number, 4)
        self.assertEqual(len(page.blocks), 2)
        self.assertEqual([box.normalized() for box in page.image_boxes], [(0.0, 0.0, 600.0, 300.0)])
        self.assertEqual([block.id for block in page.blocks], ["b0", "b1"])

    def test_blocks_that_fail_do_not_shift_numbering_source(self):
        page = extract_page(
            {"blocks": [raw_block(raw_line(raw_span(" "))), raw_block()]},
            number=1, width=100.0, height=100.0,
        )
        self.assertEqual([block.id for block in page.blocks], ["b0"])

    def test_empty_page(self):
        page = extract_page({"blocks": []}, number=9, width=10.0, height=20.0)
        self.assertEqual((page.blocks, page.image_boxes), ([], []))

    def test_non_mapping_entries_are_ignored(self):
        page = extract_page({"blocks": ["spazzatura", raw_block()]}, number=1, width=10.0, height=10.0)
        self.assertEqual(len(page.blocks), 1)


class HelpersTest(unittest.TestCase):
    def test_is_text_block(self):
        self.assertTrue(is_text_block({"type": 0}))
        self.assertFalse(is_text_block({"type": 1}))

    def test_image_box_validation(self):
        self.assertIsNone(image_box({"bbox": (5, 5)}))
        self.assertIsNone(image_box({"bbox": "nope"}))
        self.assertIsNotNone(image_box({"bbox": (0, 0, 1, 1)}))


if __name__ == "__main__":
    unittest.main()
