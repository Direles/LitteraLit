"""Test del font bundle (Fase 1.4): registro su disco e uso nella cascata."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.fonts.bundled import (
    BUNDLE_FAMILIES,
    BundledFonts,
    bundle_family_for,
    default_bundle_root,
)
from pdfbook.fonts.resolver import FontResolver


class FakeFont:
    """Font finto: copre tutti i glifi salvo quando dichiarato altrimenti."""

    def __init__(self, marker: str, coverage: bool = True) -> None:
        self.marker = marker
        self.coverage = coverage

    def has_glyph(self, code: int) -> int:
        return 1 if self.coverage else 0

    def text_length(self, text: str, fontsize: float = 0.0) -> float:
        return len(text) * fontsize


def touch_family(root: Path, family: str, *, styles=((False, False), (True, False))):
    for style in styles:
        name = BUNDLE_FAMILIES[family][style]
        (root / name).write_bytes(b"\x00" * 8)


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_directory_has_no_families(self):
        bundle = BundledFonts.discover(self.root)
        self.assertEqual(bundle.available(), ())

    def test_partial_family_is_still_available(self):
        touch_family(self.root, "inter")
        bundle = BundledFonts.discover(self.root)
        self.assertEqual(bundle.available(), ("inter",))
        self.assertTrue(bundle.path_for("inter", False, False))
        # L'italic manca: si ripiega sul regular della stessa famiglia.
        self.assertEqual(
            Path(bundle.path_for("inter", False, True)).name, "Inter-Regular.ttf"
        )

    def test_missing_italic_falls_back_to_regular(self):
        touch_family(self.root, "inter")
        bundle = BundledFonts.discover(self.root)
        self.assertEqual(
            Path(bundle.path_for("inter", False, True)).name, "Inter-Regular.ttf"
        )

    def test_unknown_style_name_is_ignored(self):
        (self.root / "Altro.ttf").write_bytes(b"\x00")
        self.assertEqual(BundledFonts.discover(self.root).available(), ())

    def test_default_root_can_be_overridden(self):
        import os

        os.environ["PDFBOOK_FONT_DIR"] = str(self.root)
        try:
            self.assertEqual(default_bundle_root(), self.root)
        finally:
            os.environ.pop("PDFBOOK_FONT_DIR", None)


class FamilyMatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        touch_family(self.root, "inter")
        touch_family(self.root, "source-serif")
        self.bundle = BundledFonts.discover(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sans_serif_names_map_to_inter(self):
        for name in ("Helvetica", "ABCDEF+Arial-Bold", "FranklinGothic-Book"):
            self.assertEqual(bundle_family_for(name, self.bundle), "inter", name)

    def test_serif_names_map_to_source_serif(self):
        for name in ("MinionPro-Regular", "TimesNewRomanPSMT", "Georgia"):
            self.assertEqual(bundle_family_for(name, self.bundle), "source-serif", name)

    def test_unknown_family_returns_none(self):
        self.assertIsNone(bundle_family_for("Wingdings-Regular", self.bundle))


class ResolverPriorityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        touch_family(self.root, "inter")
        self.bundle = BundledFonts.discover(self.root)
        self.made = []

    def tearDown(self):
        self.tmp.cleanup()

    def factory(self, **kwargs):
        self.made.append(kwargs)
        return FakeFont(kwargs.get("path") or kwargs.get("name") or "font")

    def test_bundle_is_preferred_over_system(self):
        resolver = FontResolver(
            None,
            font_factory=self.factory,
            bundle=self.bundle,
            exists=lambda _name: True,
            platform="linux",
        )
        resolver.resolve("Helvetica")
        self.assertEqual(resolver.stats.bundle_used, 1)
        self.assertEqual(resolver.stats.system_fallback, 0)

    def test_without_bundle_system_is_used(self):
        resolver = FontResolver(
            None,
            font_factory=self.factory,
            exists=lambda _name: True,
            platform="linux",
        )
        resolver.resolve("Helvetica")
        self.assertEqual(resolver.stats.bundle_used, 0)
        self.assertEqual(resolver.stats.system_fallback, 1)

    def test_bundle_falls_back_when_glyphs_are_missing(self):
        resolver = FontResolver(
            None,
            font_factory=lambda **kwargs: FakeFont("narrow", coverage=False),
            bundle=self.bundle,
            exists=lambda _name: False,
        )
        resolver.resolve("Helvetica")
        self.assertEqual(resolver.stats.bundle_used, 0)
        self.assertEqual(resolver.stats.base14_fallback, 1)


if __name__ == "__main__":
    unittest.main()
