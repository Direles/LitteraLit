"""Test del paragraph stitching (Fase 2): rilevamento, fusione, ridistribuzione."""

import unittest

from .fakes import make_block, make_line, make_page


def page_with(texts, *, number=1, top=90.0, step=40.0):
    blocks = [
        make_block(f"b{index}", [make_line(text, y0=top + index * step, width=380.0)])
        for index, text in enumerate(texts)
    ]
    return make_page(*blocks, number=number)


class DetectionTest(unittest.TestCase):
    def detect(self, first_page_texts, second_page_texts):
        from pdfbook.layout.flow import detect_continuations

        return detect_continuations([
            page_with(first_page_texts, number=1),
            page_with(second_page_texts, number=2),
        ])

    def test_lowercase_continuation_is_detected(self):
        found = self.detect(
            ["Il testo continua senza punto e finisce qui"],
            ["perché la frase prosegue sulla pagina dopo. Fine."],
        )
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0].previous_block, found[0].next_block), ("b0", "b0"))

    def test_terminal_punctuation_blocks_the_join(self):
        self.assertEqual(self.detect(
            ["Il paragrafo finisce con un punto."],
            ["e la pagina dopo inizia con una minuscola."],
        ), [])

    def test_uppercase_start_is_not_a_continuation(self):
        self.assertEqual(self.detect(
            ["Il testo resta aperto senza punto"],
            ["Ma la pagina dopo inizia con una maiuscola."],
        ), [])

    def test_far_away_block_is_not_joined(self):
        from pdfbook.layout.flow import detect_continuations

        pages = [
            page_with(["Il testo resta aperto senza punto"]),
            make_page(
                make_block("b0", [make_line("continua in fondo alla pagina", y0=700.0)]),
                number=2,
            ),
        ]
        self.assertEqual(detect_continuations(pages), [])

    def test_different_column_is_not_joined(self):
        from pdfbook.layout.flow import detect_continuations

        pages = [
            page_with(["Il testo resta aperto senza punto"]),
            make_page(
                make_block("b0", [make_line("continua ma in un'altra colonna", y0=90.0, x0=300.0)]),
                number=2,
            ),
        ]
        self.assertEqual(detect_continuations(pages), [])

    def test_short_previous_text_is_ignored(self):
        self.assertEqual(self.detect(["Corto"], ["continua con altre parole qui."]), [])

    def test_key_is_stable(self):
        found = self.detect(
            ["Il testo continua senza punto e finisce qui"],
            ["perché la frase prosegue sulla pagina dopo."],
        )
        self.assertEqual(found[0].key, "p0:b0+p1:b0")

    def test_hyphen_is_detected_and_joined(self):
        from pdfbook.layout.flow import detect_continuations, merged_text

        pages = [
            page_with(["Il testo si interrompe su una parola iphen-"]),
            page_with(["otizzata che continua dopo."], number=2),
        ]
        found = detect_continuations(pages)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].hyphen)
        merged = merged_text(pages[0].blocks[0], pages[1].blocks[0], hyphen=True)
        self.assertIn("iphenotizzata", merged)

    def test_merged_text_adds_a_space(self):
        from pdfbook.layout.flow import merged_text

        previous = make_block("b0", [make_line("prima parte")])
        following = make_block("b0", [make_line("seconda parte")])
        self.assertEqual(merged_text(previous, following, hyphen=False), "prima parte seconda parte")


class SplitTest(unittest.TestCase):
    def split(self, first, second, translated):
        from pdfbook.layout.flow import split_translation

        return split_translation(first, second, translated)

    def test_splits_at_sentence_boundary(self):
        first = "x" * 50
        second = "y" * 50
        translated = "Prima frase abbastanza lunga. Seconda frase altrettanto lunga."
        result = self.split(first, second, translated)
        self.assertTrue(result.exact)
        self.assertTrue(result.first.startswith("Prima frase"))
        self.assertTrue(result.second.startswith("Seconda frase"))

    def test_splits_at_space_when_no_sentence(self):
        result = self.split("x" * 40, "y" * 60, "una sola frase molto lunga senza punteggiatura interna")
        self.assertTrue(result.usable)
        self.assertFalse(result.exact)

    def test_returns_all_in_first_when_impossible(self):
        result = self.split("x" * 50, "y" * 50, "corto")
        self.assertEqual(result.first, "corto")
        self.assertEqual(result.second, "")
        self.assertFalse(result.usable)

    def test_empty_translation(self):
        result = self.split("a", "b", "   ")
        self.assertEqual((result.first, result.second, result.exact), ("", "", False))

    def test_parts_are_proportional(self):
        result = self.split("x" * 100, "y" * 100, "alfa beta gamma delta epsilon zeta eta theta")
        self.assertTrue(result.usable)
        self.assertLess(abs(len(result.first) - len(result.second)), len(result.first) + len(result.second))


if __name__ == "__main__":
    unittest.main()
