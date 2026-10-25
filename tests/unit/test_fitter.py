"""Test del fitting tipografico (M6) con metriche finte: nessun PDF, nessun font."""

import unittest

from pdfbook.domain.models import Rect
from pdfbook.layout.fitter import (
    LINE_HEIGHT_FACTOR,
    MIN_FONT_FRACTION,
    MIN_FONT_SIZE,
    estimate_max_chars,
    fit_text,
    wrap_text,
)


def measure(text, size):
    """Metrica da laboratorio: larghezza = caratteri * metà del corpo."""
    return len(text) * size * 0.5


class FakeHyphenation:
    """Sillabatore deterministico: spezza dopo 4 caratteri se c'è spazio."""

    def split_for_width(self, word, width_of, available):
        if len(word) < 6:
            return None
        prefix = word[:4] + "-"
        if width_of(prefix) <= available:
            return prefix, word[4:]
        return None


BOUNDS = Rect(0, 0, 100, 200)


class WrapTest(unittest.TestCase):
    def test_short_text_stays_on_one_line(self):
        self.assertEqual(wrap_text("ciao", measure=measure, size=10, max_width=100), ["ciao"])

    def test_wraps_within_width(self):
        lines = wrap_text("uno due tre quattro cinque", measure=measure, size=10, max_width=60)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(measure(line, 10), 60)

    def test_hyphenation_is_used_for_long_words(self):
        lines = wrap_text(
            "straordinariamente", measure=measure, size=10, max_width=40,
            hyphenation=FakeHyphenation(),
        )
        self.assertTrue(any(line.endswith("-") for line in lines))
        self.assertEqual("".join(line.rstrip("-") for line in lines), "straordinariamente")

    def test_without_hyphenation_long_word_overflows(self):
        lines = wrap_text("straordinariamente", measure=measure, size=10, max_width=40)
        self.assertEqual(lines, ["straordinariamente"])

    def test_newlines_are_preserved_as_line_breaks(self):
        lines = wrap_text("prima\nseconda", measure=measure, size=10, max_width=100)
        self.assertEqual(lines, ["prima", "seconda"])

    def test_toc_line_is_recomputed_inside_width(self):
        lines = wrap_text(
            "Capitolo molto lungo ..... 42", measure=measure, size=6, max_width=100
        )
        self.assertLessEqual(measure(lines[0], 6), 100)
        self.assertTrue(lines[0].endswith("42"))


class FitTest(unittest.TestCase):
    def test_keeps_target_size_when_it_fits(self):
        result = fit_text(
            "testo breve", measure=measure, max_width=200, target_size=12, max_lines=2,
            bounds=BOUNDS,
        )
        self.assertTrue(result.fits)
        self.assertEqual(result.size, 12)
        self.assertEqual(len(result.lines), 1)

    def test_reduces_size_until_lines_fit(self):
        result = fit_text(
            "parole " * 5, measure=measure, max_width=100, target_size=12, max_lines=2,
            bounds=BOUNDS,
        )
        self.assertTrue(result.fits)
        self.assertEqual(result.size, 10)
        self.assertLessEqual(len(result.lines), 2)

    def test_keeps_target_size_when_nothing_fits(self):
        result = fit_text(
            "parole " * 80, measure=measure, max_width=30, target_size=12, max_lines=1,
            bounds=Rect(0, 0, 30, 400),
        )
        self.assertFalse(result.fits)
        self.assertAlmostEqual(result.size, 12)

    def test_shrink_policy_goes_to_the_floor(self):
        result = fit_text(
            "parole " * 80, measure=measure, max_width=30, target_size=12, max_lines=1,
            bounds=Rect(0, 0, 30, 400), overflow_policy="shrink",
        )
        self.assertFalse(result.fits)
        self.assertAlmostEqual(result.size, max(12 * MIN_FONT_FRACTION, MIN_FONT_SIZE))

    def test_obstacle_forces_smaller_size(self):
        obstacle = Rect(0, 0, 100, 20)
        result = fit_text(
            "parole " * 4, measure=measure, max_width=100, target_size=12, max_lines=1,
            bounds=Rect(0, 0, 100, 200), obstacles=[obstacle],
        )
        self.assertLess(result.size, 12)

    def test_obstacle_covering_everything_never_fits(self):
        result = fit_text(
            "testo", measure=measure, max_width=100, target_size=12, max_lines=5,
            bounds=Rect(0, 0, 100, 50), obstacles=[Rect(0, 0, 100, 50)],
        )
        self.assertFalse(result.fits)

    def test_line_height_and_reduction_helpers(self):
        result = fit_text(
            "parole " * 5, measure=measure, max_width=100, target_size=12, max_lines=2,
            bounds=BOUNDS,
        )
        self.assertAlmostEqual(result.line_height, result.size * LINE_HEIGHT_FACTOR)
        self.assertTrue(result.reduced_compared_to(12))

    def test_hyphenation_helps_fitting(self):
        without = fit_text(
            "straordinariamente", measure=measure, max_width=40, target_size=10, max_lines=1,
            bounds=BOUNDS,
        )
        with_hyph = fit_text(
            "straordinariamente", measure=measure, max_width=40, target_size=10, max_lines=1,
            bounds=BOUNDS, hyphenation=FakeHyphenation(),
        )
        self.assertGreaterEqual(with_hyph.size, without.size)


class EstimateTest(unittest.TestCase):
    def test_positive_and_scales_with_lines(self):
        one = estimate_max_chars(measure, size=10, max_width=100, num_lines=1, sample="abc def")
        three = estimate_max_chars(measure, size=10, max_width=100, num_lines=3, sample="abc def")
        self.assertGreater(one, 0)
        self.assertGreater(three, one)

    def test_empty_sample_uses_default(self):
        self.assertGreater(
            estimate_max_chars(measure, size=10, max_width=100, num_lines=2, sample=""), 0
        )


if __name__ == "__main__":
    unittest.main()
