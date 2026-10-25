"""Test della verifica del glossario (Fase 5.1)."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.qa.checks_glossary import check_glossary, contains_term


class ContainsTest(unittest.TestCase):
    def test_case_and_spacing_insensitive(self):
        self.assertTrue(contains_term("il  Product   Owner decide", "product owner"))

    def test_absent_term(self):
        self.assertFalse(contains_term("il responsabile di prodotto", "Product Owner"))

    def test_empty_term_is_ignored(self):
        self.assertFalse(contains_term("testo", "  "))


class GlossaryCheckTest(unittest.TestCase):
    def test_kept_term_has_no_issues(self):
        issues = check_glossary(1, {"b0": "The Sprint ends today"}, {"b0": "Lo Sprint finisce oggi"}, ["Sprint"])
        self.assertEqual(issues, [])

    def test_lost_term_is_flagged(self):
        issues = check_glossary(2, {"b0": "The Sprint ends today"}, {"b0": "La corsa finisce oggi"}, ["Sprint"])
        self.assertEqual(len(issues), 1)
        self.assertIs(issues[0].kind, IssueKind.GLOSSARY_VIOLATION)
        self.assertEqual(issues[0].block, "b0")
        self.assertIn("Sprint", issues[0].detail)

    def test_term_absent_from_original_is_not_checked(self):
        issues = check_glossary(1, {"b0": "Una frase qualsiasi"}, {"b0": "A sentence"}, ["Backlog"])
        self.assertEqual(issues, [])

    def test_missing_translation_is_skipped(self):
        self.assertEqual(check_glossary(1, {"b0": "Sprint"}, {}, ["Sprint"]), [])

    def test_empty_glossary(self):
        self.assertEqual(check_glossary(1, {"b0": "Sprint"}, {"b0": "Sprint"}, []), [])

    def test_multiple_terms_and_units(self):
        originals = {"b0": "The Sprint and the Backlog", "b1": "Only Sprint"}
        translations = {"b0": "Lo Sprint e il backlog", "b1": "Solo Sprint"}
        self.assertEqual(len(check_glossary(3, originals, translations, ["Sprint", "Backlog"])), 0)

    def test_each_violation_is_reported_once_per_term(self):
        issues = check_glossary(
            1, {"b0": "Sprint Sprint"}, {"b0": "corsa corsa"}, ["Sprint"]
        )
        self.assertEqual(len(issues), 1)


if __name__ == "__main__":
    unittest.main()
