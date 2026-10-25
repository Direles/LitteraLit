"""Test del riconoscimento di scansioni (Fase 4.1)."""

import unittest

from pdfbook.domain.models import Rect
from pdfbook.extraction.scan_detect import has_text, is_scanned_page, scan_report
from unit.fakes import make_block, make_line, make_page


def text_page(number=1, text="Un paragrafo abbastanza lungo da contare come testo vero."):
    return make_page(make_block("b0", [make_line(text)]), number=number)


def image_page(number=1):
    page = make_page(number=number)
    page.image_boxes = [Rect(0, 0, 612, 792)]
    return page


class DetectionTest(unittest.TestCase):
    def test_page_with_text_is_not_scanned(self):
        self.assertFalse(is_scanned_page(text_page()))

    def test_empty_page_with_image_is_scanned(self):
        self.assertTrue(is_scanned_page(image_page()))

    def test_empty_page_without_image_is_not_scanned(self):
        self.assertFalse(is_scanned_page(make_page()))

    def test_threshold_on_characters(self):
        self.assertFalse(has_text(text_page(text="ciao")))
        self.assertTrue(has_text(text_page(text="ciao " * 10)))


class ReportTest(unittest.TestCase):
    def test_scanned_document_message_suggests_ocrmypdf(self):
        report = scan_report([image_page(1), image_page(2)])
        self.assertTrue(report.all_scanned)
        self.assertIn("ocrmypdf", report.message())

    def test_mixed_document_lists_pages(self):
        report = scan_report([text_page(1), image_page(2), text_page(3)])
        self.assertFalse(report.all_scanned)
        self.assertEqual(report.scanned, (2,))
        self.assertIn("pagine 2", report.message())

    def test_mostly_scanned_document(self):
        report = scan_report([image_page(1), image_page(2), text_page(3)])
        self.assertTrue(report.mostly_scanned)
        self.assertIn("2 pagine su 3", report.message())

    def test_document_without_text_gets_generic_hint(self):
        report = scan_report([make_page(number=1)])
        self.assertIn("OCR", report.message())


if __name__ == "__main__":
    unittest.main()
