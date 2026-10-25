"""Test dell'anteprima prima/dopo (Fase 6.1)."""

import unittest

from pdfbook.gui.preview import PreviewPage, preview_page, preview_text

from .fakes import make_block, make_line, make_page


class FakeSource:
    def __init__(self, pages):
        self.pages = list(pages)
        self.closed = False

    @property
    def page_count(self):
        return len(self.pages)

    def page(self, index):
        return self.pages[index]

    def close(self):
        self.closed = True


def page(*texts, number=1):
    return make_page(
        *[make_block(f"b{index}", [make_line(text)]) for index, text in enumerate(texts)],
        number=number,
    )


class PreviewTest(unittest.TestCase):
    def opener_for(self, original, output):
        sources = {"in.pdf": FakeSource(original), "out.pdf": FakeSource(output)}

        def opener(path):
            return sources[path]

        return opener

    def test_pairs_are_aligned(self):
        preview = preview_page(
            "in.pdf",
            "out.pdf",
            1,
            opener=self.opener_for([page("Hello", "World")], [page("Ciao", "Mondo")]),
        )
        self.assertEqual(preview.pairs, [("Hello", "Ciao"), ("World", "Mondo")])

    def test_missing_translation_is_none(self):
        preview = preview_page(
            "in.pdf", "out.pdf", 1, opener=self.opener_for([page("Hello", "World")], [page("Ciao")])
        )
        self.assertEqual(preview.pairs[-1][1], None)

    def test_coverage_counts_translated_blocks(self):
        preview = preview_page(
            "in.pdf", "out.pdf", 1, opener=self.opener_for([page("A", "B")], [page("a")])
        )
        self.assertEqual(preview.translated, 1)
        self.assertAlmostEqual(preview.coverage, 0.5)

    def test_page_number_out_of_range(self):
        preview = preview_page(
            "in.pdf", "out.pdf", 9, opener=self.opener_for([page("A")], [page("a")])
        )
        self.assertEqual(preview.pairs, [])
        self.assertEqual(preview.number, 9)

    def test_sources_are_closed(self):
        sources = {"in.pdf": FakeSource([page("A")]), "out.pdf": FakeSource([page("a")])}
        preview_page("in.pdf", "out.pdf", 1, opener=lambda path: sources[path])
        self.assertTrue(sources["in.pdf"].closed)
        self.assertTrue(sources["out.pdf"].closed)

    def test_preview_text_is_readable(self):
        text = preview_text(PreviewPage(1, 612.0, 792.0, [("Hello", "Ciao"), ("World", None)]))
        self.assertIn("ORIGINALE: Hello", text)
        self.assertIn("TRADOTTO: Ciao", text)
        self.assertIn("TRADOTTO: —", text)


if __name__ == "__main__":
    unittest.main()
