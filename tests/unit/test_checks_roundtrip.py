"""Test del round-trip del testo disegnato (Fase 1.5)."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.qa.checks_roundtrip import (
    MIN_ROUNDTRIP,
    check_roundtrip,
    roundtrip_ratio,
    special_chars,
)

PARAGRAPH = "Il testo tradotto deve restare testo, non disegno: copia e ricerca funzionano."


class RatioTest(unittest.TestCase):
    def test_identical_text(self):
        self.assertEqual(roundtrip_ratio([PARAGRAPH], PARAGRAPH), 1.0)

    def test_normalisation_tolerates_typography(self):
        typed = PARAGRAPH.replace(":", ": ")
        self.assertGreaterEqual(roundtrip_ratio([PARAGRAPH], typed), MIN_ROUNDTRIP)

    def test_missing_text_is_zero(self):
        self.assertEqual(roundtrip_ratio([PARAGRAPH], ""), 0.0)

    def test_nbsp_does_not_count_as_a_lost_character(self):
        with_nbsp = PARAGRAPH.replace(" ", "\u00a0")
        self.assertGreaterEqual(roundtrip_ratio([PARAGRAPH], with_nbsp), MIN_ROUNDTRIP)

    def test_nothing_expected(self):
        self.assertEqual(roundtrip_ratio([], "qualcosa"), 1.0)


class SpecialCharsTest(unittest.TestCase):
    def test_counts_nbsp_and_soft_hyphen(self):
        counts = special_chars("a\u00a0b\u00adc\u00a0")
        self.assertEqual(counts["nbsp"], 2)
        self.assertEqual(counts["soft_hyphen"], 1)

    def test_clean_text(self):
        self.assertEqual(special_chars(PARAGRAPH), {})


class CheckTest(unittest.TestCase):
    def test_matching_page_has_no_issue(self):
        self.assertEqual(check_roundtrip(1, [PARAGRAPH], PARAGRAPH), [])

    def test_lost_text_is_reported(self):
        issues = check_roundtrip(3, [PARAGRAPH], "qualcosa")
        kinds = [issue.kind for issue in issues]
        self.assertIn(IssueKind.ROUNDTRIP_LOSS, kinds)
        self.assertEqual(issues[0].page, 3)

    def test_special_chars_are_counted_when_frequent(self):
        leaked = "\u00a0".join(PARAGRAPH.split(" "))
        issues = check_roundtrip(2, [PARAGRAPH], leaked)
        kinds = [issue.kind for issue in issues]
        self.assertIn(IssueKind.SPECIAL_CHAR_LEAK, kinds)

    def test_one_stray_nbsp_is_tolerated(self):
        text = PARAGRAPH + "\u00a0"
        issues = check_roundtrip(1, [PARAGRAPH], text)
        self.assertFalse([i for i in issues if i.kind is IssueKind.SPECIAL_CHAR_LEAK])

    def test_empty_expected_is_ignored(self):
        self.assertEqual(check_roundtrip(1, ["  "], ""), [])


if __name__ == "__main__":
    unittest.main()
