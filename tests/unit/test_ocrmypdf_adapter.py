"""Test dell'adapter ocrmypdf (Fase 4.2): comando, esecuzione, sorgente trasparente."""

import unittest
from pathlib import Path

from pdfbook.ocr.ocrmypdf_adapter import (
    OcrConfig,
    OcrError,
    OcrSource,
    looks_scanned,
    ocrmypdf_command,
)

from .fakes import make_block, make_line, make_page


class CommandTest(unittest.TestCase):
    def test_default_command(self):
        argv = ocrmypdf_command("in.pdf", "out.pdf")
        self.assertEqual(argv[0], "ocrmypdf")
        self.assertIn("--language", argv)
        self.assertIn("ita+eng", argv)
        self.assertEqual(argv[-2:], ["in.pdf", "out.pdf"])

    def test_options_follow_config(self):
        argv = ocrmypdf_command(
            "in.pdf", "out.pdf", OcrConfig(language="eng", jobs=4, deskew=False, optimize=0)
        )
        self.assertIn("--jobs", argv)
        self.assertIn("4", argv)
        self.assertNotIn("--deskew", argv)
        self.assertEqual(argv[argv.index("--optimize") + 1], "0")

    def test_skip_text_is_on_by_default(self):
        self.assertIn("--skip-text", ocrmypdf_command("a", "b"))


class FakePageSource:
    def __init__(self, pages, label="src"):
        self.pages = list(pages)
        self.label = label
        self.closed = False

    @property
    def page_count(self):
        return len(self.pages)

    def page(self, index):
        return self.pages[index]

    def close(self):
        self.closed = True

    @property
    def doc(self):
        return self.label


def text_page(number=1):
    return make_page(make_block("b0", [make_line("Testo abbastanza lungo da essere utile.")]), number=number)


def scan_page(number=1):
    page = make_page(number=number)
    from pdfbook.domain.models import Rect

    page.image_boxes = [Rect(0, 0, 612, 792)]
    return page


class FakeRunner:
    def __init__(self, error=None, write=True):
        self.error = error
        self.write = write
        self.calls = []

    def run(self, argv):
        self.calls.append(list(argv))
        if self.error:
            raise self.error
        if self.write:
            Path(argv[-1]).write_bytes(b"%PDF-1.7 ocr")


class LooksScannedTest(unittest.TestCase):
    def test_text_document_is_not_scanned(self):
        self.assertFalse(looks_scanned(FakePageSource([text_page(1), text_page(2)])))

    def test_scan_document_is_scanned(self):
        self.assertTrue(looks_scanned(FakePageSource([scan_page(1), scan_page(2)])))

    def test_empty_document_is_not_judged(self):
        self.assertFalse(looks_scanned(FakePageSource([])))


class OcrSourceTest(unittest.TestCase):
    def opener(self, path):
        # Il PDF prodotto dall'OCR finto contiene testo: la sorgente è quella nuova.
        pages = [text_page(1)] if str(path).endswith("ocr.pdf") else [scan_page(1)]
        return FakePageSource(pages, label=str(path))

    def test_text_document_is_returned_untouched(self):
        source = FakePageSource([text_page(1)])
        wrapped = OcrSource.open("in.pdf", opener=lambda _p: source)
        self.assertFalse(wrapped.ocr_applied)
        self.assertIs(wrapped.source, source)
        self.assertEqual(wrapped.page_count, 1)

    def test_scanned_document_runs_ocrmypdf(self):
        runner = FakeRunner()
        wrapped = OcrSource.open(
            "in.pdf", runner=runner, opener=self.opener
        )
        self.assertTrue(wrapped.ocr_applied)
        self.assertEqual(len(runner.calls), 1)
        self.assertIn("--skip-text", runner.calls[0])
        self.assertTrue(wrapped.source.label.endswith("ocr.pdf"))

    def test_missing_binary_error_is_propagated(self):
        runner = FakeRunner(error=OcrError("ocrmypdf non è installato"))
        with self.assertRaises(OcrError) as ctx:
            OcrSource.open("in.pdf", runner=runner, opener=self.opener)
        self.assertIn("ocrmypdf", str(ctx.exception))

    def test_empty_output_is_an_error(self):
        runner = FakeRunner(write=False)
        with self.assertRaises(OcrError):
            OcrSource.open("in.pdf", runner=runner, opener=self.opener)

    def test_close_removes_the_temporary_directory(self):
        wrapped = OcrSource.open("in.pdf", runner=FakeRunner(), opener=self.opener)
        workdir = wrapped._workdir
        self.assertTrue(workdir.exists())
        wrapped.close()
        self.assertFalse(workdir.exists())

    def test_ocr_can_be_disabled_by_config(self):
        runner = FakeRunner()
        source = FakePageSource([text_page(1)])
        wrapped = OcrSource.open("in.pdf", runner=runner, opener=lambda _p: source)
        self.assertFalse(wrapped.ocr_applied)
        self.assertEqual(runner.calls, [])


class SettingsTest(unittest.TestCase):
    def test_invalid_mode_is_rejected(self):
        from pdfbook.config.settings import AppSettings

        with self.assertRaises(ValueError):
            AppSettings(ocr="forse")

    def test_default_is_auto(self):
        from pdfbook.config.settings import AppSettings

        self.assertEqual(AppSettings().ocr, "auto")


if __name__ == "__main__":
    unittest.main()
