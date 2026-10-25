"""Test dello shaping RTL/CJK via markup (Fase 4.5)."""

import unittest

from pdfbook.domain.models import IssueKind
from pdfbook.rendering.shaped import direction_for, paint_shaped, shaped_css
from pdfbook.rendering.vector_renderer import VectorRenderer

from .fakes import FakeCanvas, FakeResolver, make_block, make_line, make_page

ARABIC = "مرحبا بالعالم، هذا نص تجريبي."
HEBREW = "שלום עולם"
CHINESE = "你好世界，这是一个测试。"


class CssTest(unittest.TestCase):
    def test_arabic_is_rtl(self):
        self.assertEqual(direction_for("arabic"), "rtl")

    def test_chinese_is_ltr(self):
        self.assertEqual(direction_for("han"), "ltr")

    def test_css_contains_direction_and_size(self):
        css = shaped_css("arabic", 11.0)
        self.assertIn("direction: rtl", css)
        self.assertIn("11.0pt", css)

    def test_font_stack_mentions_noto_for_arabic(self):
        self.assertIn("Noto", shaped_css("arabic", 10.0))

    def test_unknown_system_gets_generic_stack(self):
        self.assertIn("'Noto Sans'", shaped_css("georgian", 10.0))


class PaintTest(unittest.TestCase):
    def block(self):
        return make_block("b0", [make_line("x", y0=100, width=300)])

    def test_markup_has_direction_and_text(self):
        canvas = FakeCanvas()
        result = paint_shaped(
            self.block(), make_page(self.block()), ARABIC, system="arabic", canvas=canvas
        )
        self.assertTrue(result.painted)
        _box, markup, css = canvas.markup[0]
        self.assertIn('dir="rtl"', markup)
        self.assertIn(ARABIC, markup)
        self.assertIn("direction: rtl", css)

    def test_html_is_escaped(self):
        canvas = FakeCanvas()
        paint_shaped(self.block(), make_page(), "<b>&</b>", system="han", canvas=canvas)
        _box, markup, _css = canvas.markup[0]
        self.assertNotIn("<b>&</b>", markup)
        self.assertIn("&lt;b&gt;", markup)

    def test_empty_text_is_not_painted(self):
        canvas = FakeCanvas()
        result = paint_shaped(self.block(), make_page(), "   ", system="arabic", canvas=canvas)
        self.assertFalse(result.painted)
        self.assertEqual(canvas.markup, [])


class RendererTest(unittest.TestCase):
    def page(self):
        return make_page(make_block("b0", [make_line("nota", y0=100, width=300)]))

    def test_arabic_goes_through_markup(self):
        canvas = FakeCanvas()
        result = VectorRenderer(FakeResolver(), shaping=True).render_page(
            canvas, self.page(), {"b0": ARABIC}
        )
        self.assertEqual(len(canvas.markup), 1)
        self.assertEqual(canvas.runs, [])
        self.assertEqual(result.shaped, 1)
        self.assertIn(IssueKind.SHAPED_TEXT, [issue.kind for issue in result.issues])

    def test_chinese_goes_through_markup(self):
        canvas = FakeCanvas()
        VectorRenderer(FakeResolver(), shaping=True).render_page(
            canvas, self.page(), {"b0": CHINESE}
        )
        self.assertEqual(len(canvas.markup), 1)

    def test_latin_stays_on_text_writer(self):
        canvas = FakeCanvas()
        VectorRenderer(FakeResolver(), shaping=True).render_page(
            canvas, self.page(), {"b0": "testo normale"}
        )
        self.assertEqual(canvas.markup, [])
        self.assertTrue(canvas.runs)

    def test_shaping_can_be_disabled(self):
        canvas = FakeCanvas()
        result = VectorRenderer(FakeResolver(), shaping=False).render_page(
            canvas, self.page(), {"b0": ARABIC}
        )
        self.assertEqual(canvas.markup, [])
        self.assertEqual(result.shaped, 0)

    def test_hebrew_is_rtl_in_the_markup(self):
        canvas = FakeCanvas()
        VectorRenderer(FakeResolver(), shaping=True).render_page(
            canvas, self.page(), {"b0": HEBREW}
        )
        _box, markup, _css = canvas.markup[0]
        self.assertIn('dir="rtl"', markup)

    def test_empty_translation_is_not_shaped(self):
        canvas = FakeCanvas()
        VectorRenderer(FakeResolver(), shaping=True).render_page(canvas, self.page(), {})
        self.assertEqual(canvas.markup, [])

    def test_shaped_text_is_extractable(self):
        canvas = FakeCanvas()
        VectorRenderer(FakeResolver(), shaping=True).render_page(
            canvas, self.page(), {"b0": ARABIC}
        )
        self.assertIn(ARABIC, canvas.text())


if __name__ == "__main__":
    unittest.main()
