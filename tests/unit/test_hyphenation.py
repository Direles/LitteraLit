"""Test della sillabazione (M6): con pyphen, senza pyphen, senza dizionario."""

import unittest

from pdfbook.layout.hyphenation import LANG_CODES, Hyphenation


class RealBackendTest(unittest.TestCase):
    def test_italian_dictionary_is_available(self):
        hyphenation = Hyphenation("Italiano")
        self.assertTrue(hyphenation.available)
        self.assertTrue(hyphenation.language == "Italiano")

    def test_pairs_for_long_word(self):
        pairs = tuple(Hyphenation("Italiano").pairs("straordinariamente"))
        self.assertTrue(pairs, "attese sillabazioni per una parola lunga")

    def test_short_word_is_not_split(self):
        self.assertEqual(tuple(Hyphenation("Italiano").pairs("casa")), ())

    def test_split_respects_available_width(self):
        hyphenation = Hyphenation("Italiano")

        def width_of(chunk):
            return len(chunk)  # 1 punto per carattere

        split = hyphenation.split_for_width("straordinariamente", width_of, 12)
        self.assertIsNotNone(split)
        prefix, suffix = split
        self.assertTrue(prefix.endswith("-"))
        self.assertLessEqual(len(prefix), 12)
        self.assertEqual(prefix[:-1] + suffix, "straordinariamente")

    def test_no_room_returns_none(self):
        hyphenation = Hyphenation("Italiano")
        self.assertIsNone(hyphenation.split_for_width("straordinariamente", len, 1))

    def test_language_map_is_declared(self):
        for lang in ("Italiano", "Inglese", "Spagnolo", "Francese", "Tedesco"):
            self.assertIn(lang, LANG_CODES)


class DegradedBackendTest(unittest.TestCase):
    def test_missing_pyphen_degrades_explicitly(self):
        hyphenation = Hyphenation("Italiano", module=None)
        self.assertFalse(hyphenation.available)
        self.assertEqual(tuple(hyphenation.pairs("straordinariamente")), ())

    def test_unknown_language_is_not_available(self):
        hyphenation = Hyphenation("Russo")
        self.assertFalse(hyphenation.available)

    def test_broken_dictionary_is_contained(self):
        class Broken:
            @staticmethod
            def Pyphen(lang):
                raise RuntimeError("dizionario assente")

        hyphenation = Hyphenation("Italiano", module=Broken)
        self.assertFalse(hyphenation.available)


if __name__ == "__main__":
    unittest.main()
