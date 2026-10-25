"""Test delle righe d'indice (M6): riconoscimento e riallineamento dei puntini."""

import unittest

from pdfbook.layout.toc import TOC_LINE_RE, is_toc_line, optimize_toc_line


def measure_one_per_char(text):
    return float(len(text))


class RecognitionTest(unittest.TestCase):
    def test_dotted_entry(self):
        self.assertTrue(is_toc_line("Capitolo 1 ......... 12"))

    def test_spaced_dots_entry(self):
        self.assertTrue(is_toc_line("Titolo. . . . . . .204"))

    def test_roman_page_number(self):
        self.assertTrue(is_toc_line("Prefazione ......... xiv"))

    def test_underscore_fill(self):
        self.assertTrue(is_toc_line("Indice ________ 3"))

    def test_plain_sentence_is_not_toc(self):
        self.assertFalse(is_toc_line("Il team ha discusso a lungo del prodotto."))

    def test_number_at_end_without_fill_is_not_toc(self):
        self.assertFalse(is_toc_line("Nel 2024 abbiamo rilasciato 12"))

    def test_regex_is_exposed_for_reuse(self):
        self.assertTrue(TOC_LINE_RE.match("Parte I .... 1"))


class OptimizationTest(unittest.TestCase):
    def test_fill_is_recomputed_to_fit(self):
        original = "Capitolo 18: Pianificare ..... 203"
        result = optimize_toc_line(original, measure=measure_one_per_char, max_width=40)
        self.assertLessEqual(len(result), 40)
        self.assertTrue(result.startswith("Capitolo 18: Pianificare"))
        self.assertTrue(result.endswith("203"))

    def test_keeps_fill_character(self):
        result = optimize_toc_line("Titolo ______ 12", measure=measure_one_per_char, max_width=25)
        self.assertIn("_", result)
        self.assertNotIn(".", result)

    def test_non_toc_text_is_returned_unchanged(self):
        text = "Una frase normale senza numeri finali."
        self.assertEqual(optimize_toc_line(text, measure=measure_one_per_char, max_width=30), text)

    def test_title_only_line_is_untouched(self):
        text = "..... 12"
        self.assertEqual(optimize_toc_line(text, measure=measure_one_per_char, max_width=60), text)

    def test_no_space_left_keeps_original(self):
        original = "Titolo lunghissimo ..... 203"
        self.assertEqual(optimize_toc_line(original, measure=measure_one_per_char, max_width=5), original)


if __name__ == "__main__":
    unittest.main()
