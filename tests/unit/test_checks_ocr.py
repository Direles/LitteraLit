"""Test del confronto fra due letture OCR (Fase 4.4)."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.qa.checks_ocr import (
    MIN_SIMILARITY,
    check_transcripts,
    compare_transcripts,
    tokens,
)

PAGE = (
    "La traduzione automatica dei libri richiede cura nel layout. "
    "Ogni blocco deve restare nella sua area, senza invadere le colonne vicine."
)


class TokensTest(unittest.TestCase):
    def test_punctuation_is_ignored(self):
        self.assertEqual(tokens("Ciao, mondo!"), ["ciao", "mondo"])

    def test_case_is_normalised(self):
        self.assertEqual(tokens("Ciao MONDO"), ["ciao", "mondo"])

    def test_digits_are_not_words(self):
        self.assertEqual(tokens("pagina 12 di 300"), ["pagina", "di"])


class CompareTest(unittest.TestCase):
    def test_identical_transcripts(self):
        diff = compare_transcripts(PAGE, PAGE)
        self.assertEqual(diff.similarity, 1.0)
        self.assertEqual(diff.missing, ())
        self.assertTrue(diff.ok)

    def test_one_word_missing(self):
        diff = compare_transcripts(PAGE, PAGE.replace("cura", ""))
        self.assertLess(diff.similarity, 1.0)
        self.assertIn("cura", diff.missing)

    def test_completely_different_text(self):
        diff = compare_transcripts(PAGE, "Testo completamente diverso che non c'entra nulla")
        self.assertLess(diff.similarity, 0.2)
        self.assertFalse(diff.ok)

    def test_empty_primary(self):
        diff = compare_transcripts("", PAGE)
        self.assertEqual(diff.similarity, 0.0)

    def test_both_empty_is_not_a_problem(self):
        diff = compare_transcripts("", "")
        self.assertEqual(diff.similarity, 1.0)
        self.assertEqual(diff.words, 0)

    def test_extra_words_are_reported(self):
        diff = compare_transcripts(PAGE, PAGE + " Parola intrusa.")
        self.assertIn("intrusa", diff.extra)


class IssueTest(unittest.TestCase):
    def test_matching_pages_produce_no_issue(self):
        self.assertEqual(check_transcripts(4, PAGE, PAGE), [])

    def test_divergent_pages_produce_one_issue(self):
        issues = check_transcripts(4, PAGE, "Testo di un altro libro, completamente diverso.")
        self.assertEqual(len(issues), 1)
        self.assertIs(issues[0].kind, IssueKind.SCAN_FALLBACK)
        self.assertEqual(issues[0].page, 4)
        self.assertIn("similarità", issues[0].detail)

    def test_threshold_is_configurable(self):
        near = compare_transcripts(PAGE, PAGE.replace("cura", ""))
        self.assertGreaterEqual(near.similarity, MIN_SIMILARITY)
        self.assertEqual(check_transcripts(1, PAGE, PAGE.replace("cura", "")), [])
        issues = check_transcripts(1, PAGE, PAGE.replace("cura", ""), min_similarity=0.999)
        self.assertEqual(len(issues), 1)

    def test_empty_page_is_ignored(self):
        self.assertEqual(check_transcripts(1, "", "qualcosa"), [])


if __name__ == "__main__":
    unittest.main()
