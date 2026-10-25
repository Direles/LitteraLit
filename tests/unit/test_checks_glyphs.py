"""Test dei controlli sui glifi (P0.5): caratteri persi e testo mancante."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.qa.checks_glyphs import LOST_TOKEN_RATIO, check_page_glyphs


class SpecialCharactersTest(unittest.TestCase):
    def test_identical_text_has_no_issues(self):
        text = "Il team ha discusso \u2014 a lungo \u2014 del prodotto."
        self.assertEqual(check_page_glyphs(1, [text], text), [])

    def test_lost_em_dash_is_detected(self):
        expected = "sviluppatori \u2014 ritmo, linguaggio e dinamiche"
        actual = "sviluppatori \u00b7 ritmo, linguaggio e dinamiche"
        issues = check_page_glyphs(1, [expected], actual)
        self.assertEqual(len(issues), 1)
        self.assertIs(issues[0].kind, IssueKind.GLYPH_MISSING)
        self.assertIn("2014", issues[0].detail)

    def test_nbsp_and_soft_hyphen_do_not_raise_false_positives(self):
        expected = "Multi-Team Project \u2014 dettagli"
        actual = "Multi\u00adTeam\u00a0Project \u2014 dettagli"
        self.assertEqual(check_page_glyphs(1, [expected], actual), [])

    def test_partial_loss_is_counted(self):
        expected = "a \u2014 b \u2014 c \u2014 d"
        actual = "a \u2014 b \u00b7 c \u00b7 d"
        issues = check_page_glyphs(1, [expected], actual)
        self.assertIn("3 attesi, 1 resi", issues[0].detail)

    def test_curly_quotes_are_checked(self):
        issues = check_page_glyphs(1, ["\u201ccitazione\u201d"], ['"citazione"'])
        self.assertEqual(issues[0].kind, IssueKind.GLYPH_MISSING)


class MissingTextTest(unittest.TestCase):
    def test_whole_page_missing(self):
        expected = "uno due tre quattro cinque sei sette otto"
        issues = check_page_glyphs(1, [expected], "")
        self.assertIn(IssueKind.TEXT_MISSING, [issue.kind for issue in issues])

    def test_small_loss_is_tolerated(self):
        expected = " ".join(f"parola{index}" for index in range(20))
        actual = " ".join(f"parola{index}" for index in range(20) if index != 7)
        self.assertEqual(check_page_glyphs(1, [expected], actual), [])

    def test_loss_above_threshold_is_flagged(self):
        expected = " ".join(f"parola{index}" for index in range(20))
        actual = " ".join(f"parola{index}" for index in range(10))
        issues = check_page_glyphs(1, [expected], actual)
        self.assertEqual([issue.kind for issue in issues], [IssueKind.TEXT_MISSING])
        self.assertIn("10/20", issues[0].detail)

    def test_short_texts_are_not_judged(self):
        self.assertEqual(check_page_glyphs(1, ["due parole"], ""), [])

    def test_threshold_is_declared(self):
        self.assertAlmostEqual(LOST_TOKEN_RATIO, 0.30)

    def test_segments_are_joined(self):
        issues = check_page_glyphs(1, ["uno due", "tre quattro", "cinque"], "altro testo")
        self.assertTrue(issues)

    def test_empty_expectation_is_ignored(self):
        self.assertEqual(check_page_glyphs(1, [], "qualcosa"), [])
        self.assertEqual(check_page_glyphs(1, ["   "], "qualcosa"), [])


if __name__ == "__main__":
    unittest.main()
