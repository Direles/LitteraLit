"""Test della normalizzazione testuale (P0.5)."""

import unittest
from collections import Counter

from pdfbook.qa.textnorm import collapse, count_special, lost_tokens, normalize, tokens


class NormalizeTest(unittest.TestCase):
    def test_nbsp_becomes_space(self):
        self.assertEqual(normalize("IT\u00a0Contents"), "IT Contents")

    def test_soft_hyphen_is_removed(self):
        self.assertEqual(normalize("multi\u00adteam"), "multiteam")

    def test_typographic_punctuation_is_mapped(self):
        self.assertEqual(normalize("a\u2014b\u2013c"), "a-b-c")
        self.assertEqual(normalize("\u201ccitazione\u201d"), '"citazione"')
        self.assertEqual(normalize("l\u2019idea"), "l'idea")
        self.assertEqual(normalize("ecc\u2026"), "ecc...")

    def test_whitespace_is_collapsed(self):
        self.assertEqual(normalize("  due   righe\n\nqui "), "due righe qui")
        self.assertEqual(collapse("a \t b"), "a b")

    def test_nfkc_normalization(self):
        self.assertEqual(normalize("\uff21\uff22"), "AB")


class TokensTest(unittest.TestCase):
    def test_tokens_are_lowercase_words(self):
        self.assertEqual(tokens("Il Team, davvero!"), ["il", "team", "davvero"])

    def test_tokens_ignore_typographic_noise(self):
        self.assertEqual(tokens("multi\u00adteam\u00a0x"), ["multiteam", "x"])

    def test_lost_tokens_multiset(self):
        lost = lost_tokens(["uno due due tre"], ["uno due tre"])
        self.assertEqual(lost, Counter({"due": 1}))

    def test_empty_inputs(self):
        self.assertEqual(tokens(""), [])
        self.assertEqual(lost_tokens([], []), Counter())


class SpecialCharsTest(unittest.TestCase):
    def test_counts_before_normalization(self):
        counts = count_special("a\u2014b\u2014c\u2019d")
        self.assertEqual(counts["\u2014"], 2)
        self.assertEqual(counts["\u2019"], 1)

    def test_plain_text_has_no_specials(self):
        self.assertEqual(count_special("testo normale - con trattino"), Counter())


if __name__ == "__main__":
    unittest.main()
