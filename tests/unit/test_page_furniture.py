"""Test di header/footer e numeri di pagina (Fase 2.4)."""

import unittest

from pdfbook.domain.models import Rect

from .fakes import make_block, make_line, make_page

HEADER_Y = 20.0
BODY_Y = 200.0


def page_with(header=None, body=None, *, number=1, height=792.0):
    """Pagina con header in fascia alta e corpo a metà pagina."""
    blocks = []
    if header is not None:
        blocks.append(make_block("b0", [make_line(header, y0=HEADER_Y, width=380.0)]))
    if body is not None:
        blocks.append(make_block("b1", [make_line(body, y0=BODY_Y, width=380.0)]))
    return make_page(*blocks, number=number, height=height)


class NormalizeTest(unittest.TestCase):
    def test_digits_become_placeholder(self):
        from pdfbook.layout.page_furniture import normalize

        self.assertEqual(normalize("Capitolo 12"), "capitolo #")
        self.assertEqual(normalize("  Pagina   xiv "), "pagina #")

    def test_page_number_detection(self):
        from pdfbook.layout.page_furniture import is_page_number

        for text in ("42", "xiv", " 7 "):
            self.assertTrue(is_page_number(text), text)
        for text in ("Capitolo 42", "", "quarantadue"):
            self.assertFalse(is_page_number(text), text)


class MarginTest(unittest.TestCase):
    def test_top_and_bottom_zones(self):
        from pdfbook.layout.page_furniture import in_margin

        short = page_with(height=200.0)
        top_block = make_block("b0", [make_line("header", y0=1.0, width=100.0)])
        bottom_block = make_block("b0", [make_line("footer", y0=185.0, width=100.0)])
        body_block = make_block("b0", [make_line("corpo", y0=100.0, width=100.0)])
        self.assertTrue(in_margin(top_block, short))
        self.assertTrue(in_margin(bottom_block, short))
        self.assertFalse(in_margin(body_block, short))


class DetectionTest(unittest.TestCase):
    def test_repeated_running_head_is_detected(self):
        from pdfbook.layout.page_furniture import detect_furniture

        pages = [
            page_with("Lo User Story Mapping", f"corpo numero {index}", number=index + 1)
            for index in range(3)
        ]
        self.assertEqual(detect_furniture(pages), {(0, "b0"), (1, "b0"), (2, "b0")})

    def test_page_numbers_are_detected_alone(self):
        from pdfbook.layout.page_furniture import detect_furniture

        pages = [page_with(None, f"corpo {index}", number=index + 1) for index in range(2)]
        for index, page in enumerate(pages):
            page.blocks.append(
                make_block("num", [make_line(str(12 + index), y0=760.0, width=30.0)])
            )
        furniture = detect_furniture(pages)
        self.assertIn((0, "num"), furniture)
        self.assertIn((1, "num"), furniture)

    def test_body_text_is_not_furniture(self):
        from pdfbook.layout.page_furniture import detect_furniture

        pages = [page_with(None, f"paragrafo {index}", number=index + 1) for index in range(3)]
        self.assertEqual(detect_furniture(pages), set())

    def test_single_page_does_not_create_a_pattern(self):
        from pdfbook.layout.page_furniture import detect_furniture

        self.assertEqual(detect_furniture([page_with("Titolo corrente", "testo")]), set())

    def test_structured_blocks_are_ignored(self):
        from pdfbook.layout.page_furniture import detect_furniture

        toc_lines = [
            make_line("Capitolo 1 ...... 10", y0=20.0, width=200.0),
            make_line("Capitolo 2 ...... 20", y0=32.0, width=200.0),
        ]
        toc = make_block("toc", toc_lines, bbox=Rect(0, 12, 400, 40))
        pages = [page_with(None, f"corpo {index}", number=index + 1) for index in range(3)]
        for page in pages:
            page.blocks.append(toc)
        self.assertNotIn((0, "toc"), detect_furniture(pages))


class PlanIntegrationTest(unittest.TestCase):
    def test_furniture_is_not_translated(self):
        from pdfbook.app.page_plan import build_plans

        pages = [
            page_with("Titolo corrente", f"corpo {index}", number=index + 1) for index in range(3)
        ]
        plans = build_plans(pages)
        self.assertNotIn("b0", plans[0].requests)
        self.assertEqual(plans[0].incoming.get("b0"), "Titolo corrente")
        self.assertIn("b1", plans[0].requests)


if __name__ == "__main__":
    unittest.main()
