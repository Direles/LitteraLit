"""Test del registry dei font di sistema (M5)."""

import unittest

from pdfbook.fonts.platform_fonts import (
    SYSTEM_FONTS,
    classify,
    current_platform,
    resolve_path,
    system_font_paths,
)


class ClassifyTest(unittest.TestCase):
    def test_sans_by_default(self):
        self.assertEqual(classify("GuardianSans-Regular"), ("sans", False, False))

    def test_serif_and_styles(self):
        self.assertEqual(classify("MinionPro-BoldItalic"), ("serif", True, True))

    def test_mono_wins(self):
        self.assertEqual(classify("URWTypewriterT-RegulNarrO"), ("mono", False, False))

    def test_narrow(self):
        self.assertEqual(classify("MyriadPro-Condensed"), ("sans-narrow", False, False))

    def test_serif_has_priority_over_narrow(self):
        self.assertEqual(classify("MinionPro-Cond")[0], "serif")


class PathsTest(unittest.TestCase):
    def test_every_platform_declares_all_families(self):
        for platform in ("windows", "macos", "linux"):
            paths = system_font_paths(platform)
            self.assertEqual(set(paths), {"sans", "sans-narrow", "serif", "mono"})

    def test_linux_paths_are_absolute(self):
        self.assertTrue(all(p.startswith("/") for p in system_font_paths("linux")["sans"]))

    def test_current_platform_is_known(self):
        self.assertIn(current_platform(), SYSTEM_FONTS)

    def test_resolve_prefers_requested_style(self):
        chosen = resolve_path("serif", bold=True, platform="linux", exists=lambda path: True)
        self.assertTrue(chosen.endswith("DejaVuSerif-Bold.ttf"))

    def test_resolve_falls_back_to_regular(self):
        def exists(path):
            return path.endswith("DejaVuSerif.ttf")

        chosen = resolve_path("serif", bold=True, italic=True, platform="linux", exists=exists)
        self.assertTrue(chosen.endswith("DejaVuSerif.ttf"))

    def test_resolve_returns_none_when_nothing_exists(self):
        self.assertIsNone(resolve_path("sans", platform="linux", exists=lambda path: False))


if __name__ == "__main__":
    unittest.main()
