"""Test del renderer di pagina (M9) con canvas e resolver finti."""

import unittest

from pdfbook.domain.models import IssueKind, Rect
from pdfbook.rendering.vector_renderer import VectorRenderer

from .fakes import (
    FakeCanvas,
    FakeResolver,
    FakeShortener,
    make_block,
    make_line,
    make_page,
)


def renderer(**kwargs):
    kwargs.setdefault("resolver", None)
    resolver = kwargs.pop("resolver") or FakeResolver()
    return VectorRenderer(resolver, **kwargs)


def two_line_block():
    return make_block(
        "b0",
        [make_line("x", y0=100.0), make_line("y", y0=112.0)],
        bbox=Rect(0, 100, 200, 124),
    )


class BasicTest(unittest.TestCase):
    def test_redacts_then_draws_translation(self):
        block = make_block("b0", [make_line("Hello world")])
        canvas = FakeCanvas()
        result = renderer().render_page(canvas, make_page(block), {"b0": "Ciao mondo"})
        self.assertEqual((len(canvas.redactions), canvas.applied), (1, 1))
        self.assertEqual([run.text for run in canvas.runs], ["Ciao mondo"])
        self.assertEqual((result.issues, result.perfect), ([], 1))

    def test_page_without_blocks_does_nothing(self):
        canvas = FakeCanvas()
        result = renderer().render_page(canvas, make_page(), {})
        self.assertEqual((canvas.redactions, canvas.runs, result.issues), ([], [], []))

    def test_color_comes_from_the_span(self):
        block = make_block("b0", [make_line("ciao", color=0x0000FF)])
        canvas = FakeCanvas()
        renderer().render_page(canvas, make_page(block), {"b0": "ciao"})
        self.assertEqual(canvas.runs[0].color, (0.0, 0.0, 1.0))


class MissingTranslationTest(unittest.TestCase):
    def test_skip_policy_reports_and_draws_nothing(self):
        canvas = FakeCanvas()
        result = renderer(missing_policy="skip").render_page(
            canvas, make_page(make_block("b0", [make_line("Hello")])), {}
        )
        self.assertEqual(canvas.runs, [])
        self.assertIs(result.issues[0].kind, IssueKind.UNTRANSLATED_UNRESOLVED)
        self.assertEqual(result.issues[0].block, "b0")

    def test_keep_policy_draws_original_but_still_flags(self):
        canvas = FakeCanvas()
        result = renderer(missing_policy="keep").render_page(
            canvas, make_page(make_block("b0", [make_line("Hello")])), {}
        )
        self.assertEqual([run.text for run in canvas.runs], ["Hello"])
        self.assertIs(result.issues[0].kind, IssueKind.UNTRANSLATED_UNRESOLVED)

    def test_invalid_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            VectorRenderer(FakeResolver(), missing_policy="ignora")


class StructuredTest(unittest.TestCase):
    def build(self):
        left = make_line("Titolo:", x0=0.0, y0=100.0, width=60.0)
        right = make_line("Sottotitolo", x0=100.0, y0=100.0, width=120.0)
        return make_block("b0", [left, right], bbox=Rect(0, 100, 260, 130))

    def test_columns_use_line_keys_and_own_x(self):
        canvas = FakeCanvas()
        result = renderer().render_page(
            canvas, make_page(self.build()), {"b0_l0": "Titolo:", "b0_l1": "Sottotitolo"}
        )
        self.assertEqual([run.text for run in canvas.runs], ["Titolo:", "Sottotitolo"])
        self.assertEqual([round(run.x, 1) for run in canvas.runs], [0.0, 100.0])
        self.assertEqual(result.issues, [])

    def test_missing_column_is_reported_with_line_key(self):
        canvas = FakeCanvas()
        result = renderer().render_page(canvas, make_page(self.build()), {"b0_l0": "Titolo:"})
        self.assertEqual([issue.block for issue in result.issues], ["b0_l1"])

    def test_fitting_columns_count_as_perfect(self):
        canvas = FakeCanvas()
        result = renderer().render_page(
            canvas, make_page(self.build()), {"b0_l0": "Titolo:", "b0_l1": "Sottotitolo"}
        )
        self.assertEqual((result.perfect, result.issues), (1, []))

    def test_column_overflow_is_flagged(self):
        left = make_line("Titolo:", x0=0.0, y0=100.0, width=40.0)
        right = make_line("Sottotitolo", x0=100.0, y0=100.0, width=40.0)
        block = make_block("b0", [left, right], bbox=Rect(0, 100, 140, 130))
        canvas = FakeCanvas()
        result = renderer().render_page(
            canvas, make_page(block), {"b0_l0": "ok", "b0_l1": "testo molto lungo che non entra"}
        )
        self.assertIn(IssueKind.CLIPPED, [issue.kind for issue in result.issues])
        self.assertEqual(result.issues[0].block, "b0_l1")
        self.assertEqual(result.perfect, 0)


class CellRenderTest(unittest.TestCase):
    def test_cell_never_shifts(self):
        from pdfbook.domain.models import BlockKind

        cell = make_block("b0", [make_line("molto lungo " * 6)], bbox=Rect(0, 100, 120, 112))
        cell.kind = BlockKind.TABLE_CELL
        below = make_block("b1", [make_line("sotto", y0=120.0)])
        canvas = FakeCanvas()
        renderer(overflow_policy="keep_size").render_page(
            canvas, make_page(cell, below), {"b0": "testo " * 40, "b1": "sotto"}
        )
        # La cella resta alla sua baseline: non viene spostata da chi la precede.
        self.assertAlmostEqual(canvas.runs[0].baseline_y, 110.0)

    def test_cell_overflow_is_reported_as_misaligned(self):
        from pdfbook.domain.models import BlockKind

        cell = make_block("b0", [make_line("x")], bbox=Rect(0, 100, 60, 112))
        cell.kind = BlockKind.TABLE_CELL
        canvas = FakeCanvas()
        result = renderer().render_page(
            canvas, make_page(cell), {"b0": "parola " * 20}
        )
        self.assertIn(IssueKind.TABLE_MISALIGNED, [issue.kind for issue in result.issues])


class LayoutTest(unittest.TestCase):
    def test_centered_block_is_drawn_centered(self):
        block = make_block("b0", [make_line("Titolo", x0=250, width=100)], bbox=Rect(250, 100, 350, 112))
        canvas = FakeCanvas()
        renderer().render_page(canvas, make_page(block), {"b0": "Titolo"})
        self.assertAlmostEqual(canvas.runs[0].x, 250 + (100 - len("Titolo") * 10 * 0.5) / 2)

    def test_long_translation_reduces_font_and_flags(self):
        canvas = FakeCanvas()
        result = renderer().render_page(canvas, make_page(two_line_block()), {"b0": "parola " * 12})
        self.assertEqual(result.font_reduced, 1)
        self.assertIn(IssueKind.FONT_REDUCED, [issue.kind for issue in result.issues])
        self.assertLess(canvas.runs[0].size, 10.0)
        self.assertTrue(result.perfect)

    def test_overflowing_translation_shifts_the_next_block(self):
        first = make_block("b0", [make_line("x", y0=100.0)])
        second = make_block("b1", [make_line("y", y0=140.0)])
        canvas = FakeCanvas()
        result = renderer(overflow_policy="shrink").render_page(
            canvas, make_page(first, second), {"b0": "parola " * 30, "b1": "y"}
        )
        self.assertGreaterEqual(result.shifted, 1)
        self.assertIn(IssueKind.CLIPPED, [issue.kind for issue in result.issues])
        self.assertGreater(canvas.runs[-1].baseline_y, 150)

    def test_shortener_is_used_when_font_would_shrink_too_much(self):
        shortener = FakeShortener("Breve")
        canvas = FakeCanvas()
        result = renderer(shortener=shortener).render_page(
            canvas, make_page(two_line_block()), {"b0": "parola " * 16}
        )
        self.assertEqual(len(shortener.calls), 1)
        self.assertEqual(result.retranslated, 1)
        self.assertIn(IssueKind.RETRANSLATED, [issue.kind for issue in result.issues])
        self.assertEqual([run.text for run in canvas.runs], ["Breve"])

    def test_shortener_not_called_for_short_text(self):
        shortener = FakeShortener()
        block = make_block("b0", [make_line("x")])
        renderer(shortener=shortener).render_page(FakeCanvas(), make_page(block), {"b0": "breve"})
        self.assertEqual(shortener.calls, [])

    def test_undrawable_run_becomes_text_missing(self):
        canvas = FakeCanvas(fail_containing="X")
        result = renderer().render_page(
            canvas, make_page(make_block("b0", [make_line("x")])), {"b0": "Testo X"}
        )
        self.assertEqual(result.not_drawn, 1)
        self.assertIn(IssueKind.TEXT_MISSING, [issue.kind for issue in result.issues])


if __name__ == "__main__":
    unittest.main()
