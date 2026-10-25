"""Test del riconoscimento note a piè di pagina (Fase 2.6)."""

import unittest
from dataclasses import replace

from pdfbook.app.page_plan import build_plans
from pdfbook.domain.models import BlockKind, Rect
from pdfbook.layout.notes import is_footnote_block, mark_notes, page_body_size

from .fakes import make_block, make_line, make_page


def body_block(block_id, y0, size=10.0, lines=2):
    built = [make_line(f"riga di corpo {index}", y0=y0 + index * 12, size=size) for index in range(lines)]
    return make_block(block_id, built)


def note_block(block_id, y0, text="12 Si veda il capitolo precedente.", size=8.0):
    return make_block(block_id, [make_line(text, y0=y0, size=size)])


class FootnoteTest(unittest.TestCase):
    def page(self):
        return make_page(
            body_block("b0", 100),
            body_block("b1", 160),
            note_block("n0", 700),
        )

    def test_body_size_is_the_prose_size(self):
        self.assertEqual(page_body_size(self.page()), 10.0)

    def test_note_at_bottom_with_small_font_is_detected(self):
        page = self.page()
        block = page.blocks[-1]
        self.assertTrue(
            is_footnote_block(block, body_size=10.0, page_height=page.height)
        )

    def test_small_font_high_on_page_is_not_a_note(self):
        page = make_page(note_block("n0", 100))
        self.assertFalse(
            is_footnote_block(page.blocks[0], body_size=10.0, page_height=page.height)
        )

    def test_body_font_at_bottom_is_not_a_note(self):
        page = make_page(body_block("b0", 100), note_block("n0", 700, size=10.0))
        self.assertFalse(
            is_footnote_block(page.blocks[-1], body_size=10.0, page_height=page.height)
        )

    def test_bottom_text_without_marker_is_not_a_note(self):
        block = note_block("n0", 700, text="Questa riga non ha un riferimento iniziale.")
        self.assertFalse(is_footnote_block(block, body_size=10.0, page_height=792.0))

    def test_mark_notes_only_touches_unknown_blocks(self):
        page = self.page()
        page.blocks[-1] = replace(page.blocks[-1], kind=BlockKind.CAPTION)
        marked = mark_notes(page)
        self.assertIs(marked, page)

    def test_mark_notes_sets_footnote_kind(self):
        marked = mark_notes(self.page())
        self.assertEqual([block.kind for block in marked.blocks][-1], BlockKind.FOOTNOTE)
        self.assertEqual(marked.blocks[0].kind, BlockKind.UNKNOWN)


class StitchingTest(unittest.TestCase):
    def test_note_does_not_stitch_pages(self):
        first = make_page(body_block("b0", 100))
        second = make_page(
            body_block("b1", 100).__class__(
                id="b1",
                bbox=Rect(40, 100, 500, 130),
                lines=[make_line("continuazione della frase", y0=100)],
            ),
            note_block("n0", 700),
        )
        plans = build_plans([first, second], stitch=True, furniture=False, notes=True)
        # Lo stitching usa i blocchi di prosa: b0+b1 diventano un'unica unità, la nota no.
        self.assertIn("p0:b0+p1:b1", plans[0].requests)
        self.assertIn("n0", plans[1].requests)

    def test_note_on_first_page_is_not_merged_with_next(self):
        first = make_page(body_block("b0", 100), note_block("n0", 700))
        second = make_page(body_block("b1", 100))
        plans = build_plans([first, second], stitch=True, furniture=False, notes=True)
        self.assertIn("b1", plans[1].requests)
        self.assertNotIn("n0", plans[1].incoming)

    def test_notes_can_be_disabled(self):
        marked = build_plans([self.page()], notes=False)
        self.assertNotEqual(marked[0].page.blocks[-1].kind, BlockKind.FOOTNOTE)

    def page(self):
        return make_page(body_block("b0", 100), note_block("n0", 700))


if __name__ == "__main__":
    unittest.main()
