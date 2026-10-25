"""Test della cascata di risoluzione font (M5), senza PyMuPDF."""

import unittest

from pdfbook.fonts.resolver import LANG_TEST_CHARS, FontResolver


class FakeFont:
    def __init__(self, marker: str) -> None:
        self.marker = marker

    def has_glyph(self, code: int) -> int:
        char = chr(code)
        return 1 if (char.isascii() or self.marker == "full") else 0

    def text_length(self, text: str, fontsize: float) -> float:
        return len(text) * fontsize * 0.5


def factory(*, buffer=None, path=None, name=None):
    marker = "full" if buffer == b"full" else "partial"
    return FakeFont(marker)


class FakeSource:
    def __init__(self, pages, buffers=None, fail_on=()):
        self._pages = pages
        self._buffers = buffers or {}
        self._fail_on = set(fail_on)

    @property
    def page_count(self):
        return len(self._pages)

    def page_fonts(self, page_index):
        return self._pages[page_index]

    def extract_font(self, xref):
        if xref in self._fail_on:
            raise RuntimeError("xref rotto")
        for page in self._pages:
            for candidate, name in page:
                if candidate == xref:
                    buffer = self._buffers.get(name) or self._buffers.get(name.split("+")[-1])
                    return name, "ttf", "TrueType", buffer
        raise KeyError(xref)


def make_resolver(source=None, *, exists=True, glyphs=None):
    return FontResolver(
        source,
        font_factory=factory,
        target_lang="Italiano",
        platform="linux",
        exists=lambda path: exists,
    )


class CascadeTest(unittest.TestCase):
    def test_reuses_embedded_font_when_coverage_is_complete(self):
        source = FakeSource([[(1, "ABCDEF+GuardianSans-Regular")]], {"GuardianSans-Regular": b"full"})
        resolver = make_resolver(source)
        font = resolver.resolve("GuardianSans-Regular")
        self.assertEqual(font.marker, "full")
        self.assertEqual(resolver.stats.embedded_reused, 1)
        self.assertTrue(resolver.covered("GuardianSans-Regular"))

    def test_skips_embedded_font_without_target_glyphs(self):
        source = FakeSource([[(1, "GuardianSans-Regular")]], {"GuardianSans-Regular": b"partial"})
        resolver = make_resolver(source, exists=True)
        font = resolver.resolve("GuardianSans-Regular")
        self.assertEqual(font.marker, "partial")
        self.assertEqual(resolver.stats.system_fallback, 1)
        self.assertFalse(resolver.covered("GuardianSans-Regular"))

    def test_fuzzy_match_on_same_family(self):
        source = FakeSource(
            [[(1, "GuardianSans-Bold"), (2, "GuardianSans-Regular")]],
            {"GuardianSans-Bold": b"full", "GuardianSans-Regular": b"full"},
        )
        resolver = make_resolver(source)
        resolver.resolve("GuardianSans-BoldItalic")
        self.assertEqual(resolver.stats.fuzzy_reused, 1)

    def test_base14_last_resort_is_counted(self):
        resolver = make_resolver(None, exists=False)
        resolver.resolve("Qualcosa-Regular")
        self.assertEqual(resolver.stats.base14_fallback, 1)

    def test_unreadable_xref_does_not_break_resolution(self):
        source = FakeSource([[(1, "Broken-Regular")]], {"Broken-Regular": b"full"}, fail_on={1})
        resolver = make_resolver(source)
        resolver.resolve("Broken-Regular")
        self.assertEqual(resolver.stats.embedded_reused, 0)

    def test_cache_counts_once(self):
        source = FakeSource([[(1, "GuardianSans-Regular")]], {"GuardianSans-Regular": b"full"})
        resolver = make_resolver(source)
        resolver.resolve("GuardianSans-Regular")
        resolver.resolve("GuardianSans-Regular")
        self.assertEqual(resolver.stats.embedded_reused, 1)

    def test_text_length_uses_resolved_font(self):
        resolver = make_resolver(None, exists=False)
        self.assertAlmostEqual(resolver.text_length("abcd", "X-Regular", 10), 20.0)

    def test_language_coverage_set_includes_typographic_characters(self):
        self.assertIn("\u2014", LANG_TEST_CHARS["Italiano"])
        self.assertIn("\u2019", LANG_TEST_CHARS["Italiano"])


if __name__ == "__main__":
    unittest.main()
