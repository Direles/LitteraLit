"""Test dei controlli di qualità del testo (Fase 5.4)."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.qa.checks_text import (
    check_language,
    check_length_ratio,
    check_repetitions,
    run_text_checks,
)

ORIGINAL = (
    "This is a fairly long paragraph of English prose, written to be long enough that the "
    "length ratio check has something meaningful to compare."
)


class LengthRatioTest(unittest.TestCase):
    def test_balanced_translation_has_no_issue(self):
        issues = check_length_ratio(1, {"b0": ORIGINAL}, {"b0": "Questa e una traduzione di " * 3})
        self.assertEqual(issues, [])

    def test_too_short_translation_is_reported(self):
        issues = check_length_ratio(3, {"b0": ORIGINAL}, {"b0": "Troppo breve."})
        self.assertEqual([issue.kind for issue in issues], [IssueKind.LENGTH_RATIO])
        self.assertEqual(issues[0].page, 3)

    def test_short_original_is_ignored(self):
        issues = check_length_ratio(1, {"b0": "Hello"}, {"b0": "Ciao"})
        self.assertEqual(issues, [])

    def test_missing_translation_is_not_a_ratio_issue(self):
        issues = check_length_ratio(1, {"b0": ORIGINAL}, {})
        self.assertEqual(issues, [])


class RepetitionTest(unittest.TestCase):
    def test_loop_is_reported(self):
        loop = "il modello continua a ripetere la stessa identica frase senza motivo"
        issues = check_repetitions(2, {"b0": loop, "b1": loop, "b2": loop})
        self.assertEqual(issues[0].kind, IssueKind.REPETITION)
        self.assertTrue(all(issue.kind is IssueKind.REPETITION for issue in issues))
        self.assertIn("3 volte", issues[0].detail)

    def test_normal_text_is_clean(self):
        issues = check_repetitions(
            1,
            {
                "b0": "La prima frase parla di una cosa completamente diversa dalle altre.",
                "b1": "La seconda invece introduce un argomento nuovo e distinto.",
            },
        )
        self.assertEqual(issues, [])

    def test_issue_has_no_block_because_it_spans_units(self):
        loop = " ".join(["parola"] * 12)
        issues = check_repetitions(1, {"b0": loop}, threshold=2)
        self.assertIsNone(issues[0].block)


class LanguageTest(unittest.TestCase):
    def italian(self):
        return (
            "Il testo tradotto è in italiano e parla di un libro che non è ancora stato "
            "pubblicato, con le parole che servono per riconoscere la lingua. "
        ) * 3

    def english(self):
        return (
            "The translated text is still in English and speaks about a book that has not been "
            "published yet, with the words that are needed to recognise the language. "
        ) * 3

    def test_italian_translation_is_accepted(self):
        self.assertEqual(check_language(1, {"b0": self.italian()}, expected="it"), [])

    def test_english_answer_is_flagged(self):
        issues = check_language(1, {"b0": self.english()}, expected="it")
        self.assertEqual([issue.kind for issue in issues], [IssueKind.WRONG_LANGUAGE])

    def test_short_text_is_not_judged(self):
        self.assertEqual(check_language(1, {"b0": "Ciao mondo"}, expected="it"), [])

    def test_unknown_expected_language_is_skipped(self):
        self.assertEqual(check_language(1, {"b0": self.english()}, expected="zz"), [])


class RunAllTest(unittest.TestCase):
    def test_length_and_language_issues_coexist(self):
        issues = run_text_checks(1, {"b0": ORIGINAL}, {"b0": "The text is still English."})
        kinds = {issue.kind for issue in issues}
        self.assertIn(IssueKind.LENGTH_RATIO, kinds)
        self.assertNotIn(IssueKind.REPETITION, kinds)


if __name__ == "__main__":
    unittest.main()
