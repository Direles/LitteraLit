"""Test degli stili inline (Fase 1.1/1.2): tag, parsing, a capo con metriche miste."""

import unittest

from pdfbook.domain.models import Line, Rect, Span, TextBlock

from .fakes import make_block, make_line


def styled_block():
    spans = [
        Span(text="Testo normale ", font_name="MinionPro-Regular", size=10.0),
        Span(text="grassetto", font_name="MinionPro-Bold", size=10.0),
        Span(text=" e corsivo", font_name="MinionPro-Italic", size=10.0),
    ]
    line = Line(spans=spans, bbox=Rect(0, 100, 300, 112), origin_y=110)
    return TextBlock(id="b0", bbox=Rect(0, 100, 300, 112), lines=[line])


class EmphasisTest(unittest.TestCase):
    def test_detects_bold_and_italic(self):
        from pdfbook.layout.styles import block_has_emphasis

        self.assertTrue(block_has_emphasis(styled_block()))

    def test_plain_block_has_no_emphasis(self):
        from pdfbook.layout.styles import block_has_emphasis

        block = make_block("b0", [make_line("testo normale")])
        self.assertFalse(block_has_emphasis(block))

    def test_tags_are_placed_around_emphasised_spans(self):
        from pdfbook.layout.styles import tag_block_text

        tagged = tag_block_text(styled_block())
        self.assertIn("<b>grassetto</b>", tagged)
        self.assertIn("<i> e corsivo</i>", tagged)
        self.assertTrue(tagged.startswith("Testo normale"))


class ParseTest(unittest.TestCase):
    def test_pieces_carry_style(self):
        from pdfbook.layout.styles import parse_tagged

        pieces = parse_tagged("ciao <b>forte</b> e <i>piano</i> fine")
        by_text = {piece.text: (piece.bold, piece.italic) for piece in pieces}
        self.assertEqual(by_text["forte"], (True, False))
        self.assertEqual(by_text["piano"], (False, True))
        self.assertEqual(by_text["ciao"], (False, False))

    def test_markers_are_stripped_from_words(self):
        from pdfbook.layout.styles import parse_tagged, plain_text

        pieces = parse_tagged("uno <b>due</b>")
        self.assertEqual(plain_text(pieces), "uno due")

    def test_unbalanced_tags_do_not_crash(self):
        from pdfbook.layout.styles import parse_tagged

        pieces = parse_tagged("uno <b>due tre")
        self.assertEqual(len(pieces), 3)
        self.assertTrue(all(isinstance(piece.text, str) for piece in pieces))

    def test_has_markers_and_strip(self):
        from pdfbook.layout.styles import has_markers, strip_markup

        self.assertTrue(has_markers("a <i>b</i>"))
        self.assertFalse(has_markers("a b"))
        self.assertEqual(strip_markup("a <b>b</b> <i>c</i>"), "a b c")


class WrapTest(unittest.TestCase):
    def make_measure(self):
        widths = {(False, False): 1.0, (True, False): 2.0, (False, True): 1.5, (True, True): 2.0}

        from pdfbook.layout.styles import piece_size

        def measure(piece, size):
            base = size * widths[(piece.bold, piece.italic)]
            return len(piece.text) * base * (piece_size(piece, size) / size if size else 1.0)

        return measure

    def test_splits_when_width_is_exceeded(self):
        from pdfbook.layout.styles import StyledPiece, wrap_pieces

        pieces = [StyledPiece(f"parola{index}") for index in range(6)]
        lines = wrap_pieces(pieces, measure=self.make_measure(), size=10.0, max_width=80.0)
        self.assertGreater(len(lines), 1)
        self.assertEqual(sum(len(line) for line in lines), 6)

    def test_bold_words_take_more_space(self):
        from pdfbook.layout.styles import StyledPiece, wrap_pieces

        plain = [StyledPiece("aaaaaa") for _ in range(3)]
        bold = [StyledPiece("aaaaaa", bold=True) for _ in range(3)]
        plain_lines = wrap_pieces(plain, measure=self.make_measure(), size=10.0, max_width=100.0)
        bold_lines = wrap_pieces(bold, measure=self.make_measure(), size=10.0, max_width=100.0)
        self.assertGreaterEqual(len(bold_lines), len(plain_lines))

    def test_single_piece_always_fits(self):
        from pdfbook.layout.styles import StyledPiece, wrap_pieces

        lines = wrap_pieces(
            [StyledPiece("parolalunga", bold=True)],
            measure=self.make_measure(),
            size=10.0,
            max_width=5.0,
        )
        self.assertEqual(len(lines), 1)


class ScriptTest(unittest.TestCase):
    def block_with_superscript(self):
        from pdfbook.domain.models import Line, Span, TextBlock

        spans = [
            Span(text="nota", font_name="MinionPro-Regular", size=10.0, origin_y=110),
            Span(text="12", font_name="MinionPro-Regular", size=6.5, origin_y=107),
        ]
        line = Line(spans=spans, bbox=Rect(0, 100, 200, 112), origin_y=110)
        return TextBlock(id="b0", bbox=Rect(0, 100, 200, 112), lines=[line])

    def test_detects_superscript(self):
        from pdfbook.layout.scripts import dominant_size, script_of

        line = self.block_with_superscript().lines[0]
        self.assertAlmostEqual(dominant_size(line), 10.0)
        self.assertEqual(script_of(line.spans[1], line), "sup")

    def test_normal_span_is_not_a_script(self):
        from pdfbook.layout.scripts import script_of

        line = self.block_with_superscript().lines[0]
        self.assertIsNone(script_of(line.spans[0], line))

    def test_block_needs_tags_when_it_has_scripts(self):
        from pdfbook.layout.styles import block_needs_tags

        self.assertTrue(block_needs_tags(self.block_with_superscript()))

    def test_tags_wrap_the_note_reference(self):
        from pdfbook.layout.styles import tag_block_text

        self.assertIn("<sup>12</sup>", tag_block_text(self.block_with_superscript()))

    def test_parse_sup_and_sub(self):
        from pdfbook.layout.styles import parse_tagged

        pieces = parse_tagged("testo<sup>3</sup> e<sub>2</sub>")
        scripts = {piece.text: piece.script for piece in pieces}
        self.assertEqual(scripts["3"], "sup")
        self.assertEqual(scripts["2"], "sub")

    def test_script_size_and_baseline(self):
        from pdfbook.layout.scripts import script_baseline_offset, script_scale

        self.assertLess(script_scale("sup"), 1.0)
        self.assertLess(script_baseline_offset("sup", 10.0), 0.0)
        self.assertGreater(script_baseline_offset("sub", 10.0), 0.0)
        self.assertEqual(script_baseline_offset(None, 10.0), 0.0)


if __name__ == "__main__":
    unittest.main()
