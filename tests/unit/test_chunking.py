"""Test del chunking per frase (Fase 5.2)."""

import unittest

from pdfbook.translation.chunking import (
    PART_SEPARATOR,
    join_parts,
    split_long_unit,
    split_parts,
    split_sentences,
)


class SentenceTest(unittest.TestCase):
    def test_simple_sentences(self):
        self.assertEqual(
            split_sentences("Prima frase. Seconda frase! Terza?"),
            ["Prima frase.", "Seconda frase!", "Terza?"],
        )

    def test_no_punctuation_is_one_sentence(self):
        self.assertEqual(split_sentences("senza punteggiatura"), ["senza punteggiatura"])

    def test_ellipsis_is_a_boundary(self):
        self.assertEqual(len(split_sentences("Aspetta… poi continua.")), 2)

    def test_abbreviation_does_not_split(self):
        text = "Vedi e.g. questo esempio. Poi altro."
        self.assertEqual(len(split_sentences(text)), 2)

    def test_decimal_numbers_do_not_split(self):
        self.assertEqual(len(split_sentences("Il valore è 3.14 circa. Fine.")), 2)

    def test_empty_text(self):
        self.assertEqual(split_sentences("   "), [])

    def test_quotes_are_preserved(self):
        sentences = split_sentences('Disse: "vado." Poi uscì.')
        self.assertTrue(sentences[0].endswith('"'))


class LongUnitTest(unittest.TestCase):
    def text(self, count=6):
        return " ".join(f"Questa è la frase numero {index} del blocco." for index in range(count))

    def test_short_unit_is_untouched(self):
        self.assertEqual(split_long_unit("a", "breve", 100), [("a", "breve")])

    def test_long_unit_is_split_on_sentences(self):
        parts = split_long_unit("a", self.text(), 80)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(text) <= 80 for _key, text in parts))
        self.assertTrue(all(key.startswith("a#") for key, _text in parts))

    def test_pieces_cover_all_the_text(self):
        parts = split_long_unit("a", self.text(), 80)
        self.assertEqual(len(" ".join(text for _k, text in parts).split()), len(self.text().split()))

    def test_single_long_sentence_splits_on_words(self):
        parts = split_long_unit("a", "parola " * 40, 60)
        self.assertGreater(len(parts), 1)

    def test_indices_are_sequential(self):
        keys = [key for key, _text in split_long_unit("a", self.text(12), 60)]
        self.assertEqual(keys, [f"a{PART_SEPARATOR}{i}" for i in range(len(keys))])


class SplitPartsTest(unittest.TestCase):
    def test_whole_and_parts(self):
        whole, parts = split_parts({"a": "x", "b#0": "y", "b#1": "z"})
        self.assertEqual(set(whole), {"a"})
        self.assertEqual(parts["b"], ["b#0", "b#1"])

    def test_parts_are_ordered_numerically(self):
        _whole, parts = split_parts({"b#10": "", "b#2": ""})
        self.assertEqual(parts["b"], ["b#2", "b#10"])

    def test_join(self):
        self.assertEqual(join_parts("b", {"b#0": "uno", "b#1": "due"}), "uno due")

    def test_missing_piece_returns_none(self):
        self.assertIsNone(join_parts("b", {"b#0": "uno"}, expected=2))

    def test_parts_without_expectation_are_joined(self):
        self.assertEqual(join_parts("b", {"b#0": "uno"}), "uno")

    def test_empty_piece_returns_none(self):
        self.assertIsNone(join_parts("b", {"b#0": "", "b#1": "due"}))


if __name__ == "__main__":
    unittest.main()
