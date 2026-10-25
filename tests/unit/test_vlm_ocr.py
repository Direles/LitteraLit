"""Test del layer OCR VLM (Fase 4.3): parser `<|det|>` e client con trasporto finto."""

import unittest

from pdfbook.domain.models import BlockKind
from pdfbook.ocr.det_parser import parse_det, to_page_layout
from pdfbook.ocr.vlm_adapter import VlmConfig, VlmOcr, VlmOcrError

OUTPUT = (
    "<|det|>title [40, 20, 560, 60]Capitolo primo\n"
    "<|det|>text [40, 80, 560, 300]Era una notte buia e tempestosa, e la pioggia batteva.\n"
    "<|det|>footnote [40, 700, 560, 730]1 Nota a pie di pagina."
)


class ParserTest(unittest.TestCase):
    def test_blocks_are_parsed_in_order(self):
        parsed = parse_det(OUTPUT)
        self.assertEqual(len(parsed.blocks), 3)
        self.assertEqual(parsed.blocks[0].kind, "title")
        self.assertTrue(parsed.blocks[1].text.startswith("Era una notte"))

    def test_bbox_is_read(self):
        block = parse_det(OUTPUT).blocks[0]
        self.assertEqual(block.bbox, (40.0, 20.0, 560.0, 60.0))

    def test_no_markers_means_no_blocks(self):
        self.assertEqual(parse_det("testo senza marcatori").blocks, [])

    def test_invalid_bbox_is_skipped_with_reason(self):
        parsed = parse_det("<|det|>text [10, 20]senza coordinate complete")
        self.assertEqual(parsed.blocks, [])
        self.assertEqual(parsed.skipped, 1)
        self.assertIn("bbox non valida", parsed.problems[0])

    def test_inverted_bbox_is_rejected(self):
        parsed = parse_det("<|det|>text [100, 100, 10, 10]invertita")
        self.assertEqual(parsed.skipped, 1)

    def test_empty_text_is_skipped(self):
        parsed = parse_det("<|det|>text [10, 10, 100, 50]   ")
        self.assertEqual(parsed.skipped, 1)

    def test_normalized_coordinates_are_scaled(self):
        block = parse_det("<|det|>text [0.1, 0.2, 0.5, 0.4]ciao").blocks[0]
        self.assertEqual(block.normalized(1000.0, 500.0), (100.0, 100.0, 500.0, 200.0))

    def test_absolute_coordinates_are_not_scaled(self):
        block = parse_det("<|det|>text [100, 200, 500, 400]ciao").blocks[0]
        self.assertEqual(block.normalized(1000.0, 500.0), (100.0, 200.0, 500.0, 400.0))


class LayoutTest(unittest.TestCase):
    def test_kinds_are_mapped(self):
        page = to_page_layout(parse_det(OUTPUT).blocks, number=7, width=600, height=800)
        self.assertEqual(page.number, 7)
        self.assertEqual([block.kind for block in page.blocks], [
            BlockKind.TITLE,
            BlockKind.PARAGRAPH,
            BlockKind.FOOTNOTE,
        ])

    def test_text_is_preserved(self):
        page = to_page_layout(parse_det(OUTPUT).blocks, number=1, width=600, height=800)
        self.assertIn("tempestosa", page.blocks[1].text)

    def test_degenerate_boxes_are_dropped(self):
        parsed = parse_det("<|det|>text [10, 10, 10.5, 10.5]minuscolo")
        page = to_page_layout(parsed.blocks, number=1, width=600, height=800)
        self.assertEqual(page.blocks, [])


class VlmOcrTest(unittest.TestCase):
    def client(self, response, calls=None):
        def post_json(url, payload, headers):
            if calls is not None:
                calls.append((url, payload, headers))
            return response

        return VlmOcr(
            config=VlmConfig(model="unlimited-ocr", base_url="http://local:30000/v1"),
            post_json=post_json,
            render_png=lambda index: f"png{index}".encode(),
        )

    def test_page_is_transcribed(self):
        page = self.client({"choices": [{"message": {"content": OUTPUT}}]}).page(0, number=3)
        self.assertEqual(len(page.blocks), 3)
        self.assertEqual(page.number, 3)

    def test_request_contains_image_and_prompt(self):
        calls = []
        self.client({"choices": [{"message": {"content": OUTPUT}}]}, calls).page(1)
        url, payload, headers = calls[0]
        self.assertTrue(url.endswith("/chat/completions"))
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_empty_answer_is_an_error(self):
        with self.assertRaises(VlmOcrError):
            self.client({"choices": [{"message": {"content": "niente"}}]}).page(0)

    def test_missing_choices_is_an_error(self):
        with self.assertRaises(VlmOcrError):
            self.client({"error": "boom"}).page(0)

    def test_transport_error_is_wrapped(self):
        def broken(url, payload, headers):
            raise OSError("connection refused")

        client = VlmOcr(VlmConfig(model="m"), post_json=broken, render_png=lambda i: b"x")
        with self.assertRaises(VlmOcrError) as ctx:
            client.page(0)
        self.assertIn("non raggiungibile", str(ctx.exception))

    def test_list_content_is_joined(self):
        response = {"choices": [{"message": {"content": [{"text": OUTPUT}]}}]}
        page = self.client(response).page(0)
        self.assertEqual(len(page.blocks), 3)


if __name__ == "__main__":
    unittest.main()
