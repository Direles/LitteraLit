"""Test del riconoscimento dei sistemi di scrittura (Fase 4.5)."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.layout.writing_system import (
    SUPPORTED,
    classify_text,
    describes_rtl,
    text_blocks_outside,
)

from .fakes import make_block, make_line, make_page


class ClassifyTest(unittest.TestCase):
    def test_latin(self):
        self.assertEqual(classify_text("Ciao, come stai?").name, "latin")

    def test_cyrillic_and_greek_are_supported(self):
        for sample in ("Привет мир", "Καλημέρα κόσμε"):
            system = classify_text(sample)
            self.assertTrue(system.supported, sample)

    def test_arabic_is_rtl_and_unsupported(self):
        system = classify_text("مرحبا بالعالم")
        self.assertEqual(system.name, "arabic")
        self.assertTrue(describes_rtl(system))
        self.assertFalse(system.supported)

    def test_hebrew_is_rtl(self):
        self.assertTrue(describes_rtl(classify_text("שלום עולם")))

    def test_han_and_hangul_are_detected(self):
        self.assertEqual(classify_text("你好世界").name, "han")
        self.assertEqual(classify_text("안녕하세요").name, "hangul")

    def test_digits_and_punctuation_are_not_a_script(self):
        system = classify_text("1234 — !?")
        self.assertEqual(system.name, "none")
        self.assertTrue(system.supported)

    def test_mixed_text_uses_the_majority(self):
        self.assertEqual(classify_text("Hello Привет Привет").name, "cyrillic")


class BlocksTest(unittest.TestCase):
    def page(self, *texts):
        return make_page(*[make_block(f"b{i}", [make_line(text)]) for i, text in enumerate(texts)])

    def test_latin_page_has_no_findings(self):
        self.assertEqual(text_blocks_outside(self.page("Ciao mondo")), [])

    def test_arabic_block_is_reported(self):
        found = text_blocks_outside(self.page("Ciao", "مرحبا بالعالم"))
        self.assertEqual(found, [("b1", "arabic")])

    def test_supported_set_can_be_narrowed(self):
        found = text_blocks_outside(self.page("Привет мир"), supported={"latin"})
        self.assertEqual(found, [("b0", "cyrillic")])

    def test_default_supported_set(self):
        self.assertEqual(set(SUPPORTED), {"latin", "cyrillic", "greek"})


class IssueKindTest(unittest.TestCase):
    def test_kind_exists(self):
        self.assertEqual(IssueKind.UNSUPPORTED_SCRIPT.value, "unsupported_script")


if __name__ == "__main__":
    unittest.main()
