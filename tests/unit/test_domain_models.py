"""Test del contratto di dominio: Rect, blocchi, settings, QA report."""

import unittest

from pdfbook.domain.models import (
    BlockKind,
    IssueKind,
    Line,
    PageLayout,
    QAIssue,
    QAReport,
    Rect,
    Span,
    TextBlock,
    TranslationSettings,
)


def make_block(text: str = "ciao", kind: BlockKind = BlockKind.PARAGRAPH) -> TextBlock:
    span = Span(text=text, font_name="GuardianSans-Regular", size=10.0, color=0)
    line = Line(spans=[span], bbox=Rect(0, 0, 100, 12), origin_y=10.0)
    return TextBlock(id="b0", bbox=Rect(0, 0, 100, 12), lines=[line], kind=kind)


class RectTest(unittest.TestCase):
    def test_rejects_inverted_rect(self):
        with self.assertRaises(ValueError):
            Rect(10, 5, 2, 9)

    def test_intersection_and_ratio(self):
        a, b = Rect(0, 0, 10, 10), Rect(5, 5, 15, 15)
        inter = a.intersection(b)
        self.assertEqual(inter.normalized(), (5, 5, 10, 10))
        self.assertAlmostEqual(a.overlap_ratio(b), 25 / 100)

    def test_disjoint_intersection_is_none(self):
        self.assertIsNone(Rect(0, 0, 10, 10).intersection(Rect(20, 20, 30, 30)))
        self.assertEqual(Rect(0, 0, 10, 10).overlap_ratio(Rect(20, 20, 30, 30)), 0.0)

    def test_union_covers_both(self):
        self.assertEqual(Rect(0, 0, 1, 1).union(Rect(-1, 2, 3, 4)).normalized(), (-1, 0, 3, 4))


class TextBlockTest(unittest.TestCase):
    def test_text_and_key(self):
        block = make_block("prima riga")
        self.assertEqual(block.text, "prima riga")
        self.assertEqual(block.line_count, 1)
        self.assertEqual(block.global_key(7), "p7:b0")

    def test_requires_a_line(self):
        with self.assertRaises(ValueError):
            TextBlock(id="b0", bbox=Rect(0, 0, 1, 1), lines=[])

    def test_blank_span_detection(self):
        self.assertTrue(Span(text="   ").is_blank())
        self.assertFalse(Span(text="x").is_blank())


class PageLayoutTest(unittest.TestCase):
    def test_text_blocks_filters_empty(self):
        page = PageLayout(number=1, width=600, height=800, blocks=[make_block("a"), make_block(" ")])
        self.assertEqual(len(page.text_blocks()), 1)

    def test_blocks_overlapping(self):
        page = PageLayout(number=1, width=600, height=800, blocks=[make_block("a")])
        self.assertEqual(len(page.blocks_overlapping(Rect(10, 10, 20, 20))), 1)
        self.assertEqual(page.blocks_overlapping(Rect(300, 300, 320, 320)), [])


class TranslationSettingsTest(unittest.TestCase):
    def test_requires_provider_and_model(self):
        with self.assertRaises(ValueError):
            TranslationSettings(provider="", model="x")
        with self.assertRaises(ValueError):
            TranslationSettings(provider="x", model=" ")

    def test_cache_partition_changes_with_settings(self):
        base = TranslationSettings(provider="DeepSeek", model="deepseek-chat")
        other_lang = TranslationSettings(provider="DeepSeek", model="deepseek-chat", target_lang="Inglese")
        other_provider = TranslationSettings(provider="OpenAI", model="deepseek-chat")
        self.assertNotEqual(base.cache_partition(), other_lang.cache_partition())
        self.assertNotEqual(base.cache_partition(), other_provider.cache_partition())

    def test_cache_partition_includes_glossary_and_is_stable(self):
        base = TranslationSettings(provider="DeepSeek", model="m")
        with_terms = base.with_glossary(["Sprint", "Backlog", "Sprint"])
        self.assertNotEqual(base.cache_partition(), with_terms.cache_partition())
        self.assertEqual(with_terms.glossary, ("Backlog", "Sprint"))
        self.assertEqual(base.cache_partition(), TranslationSettings(provider="DeepSeek", model="m").cache_partition())


class QAReportTest(unittest.TestCase):
    def test_add_and_count(self):
        report = QAReport()
        report.add(QAIssue(page=2, kind=IssueKind.FONT_REDUCED, block="b1", detail="9pt -> 7pt"))
        report.add(QAIssue(page=2, kind=IssueKind.GLYPH_MISSING, detail="em-dash perso"))
        self.assertEqual(report.count(IssueKind.FONT_REDUCED), 1)
        self.assertEqual(len(report.issues_for_page(2)), 2)
        payload = report.to_dict()
        self.assertEqual(payload["summary"]["font_reduced"], 1)
        self.assertEqual(payload["pages"][0]["page"], 2)

    def test_to_dict_shape_matches_legacy_report(self):
        report = QAReport()
        report.add(QAIssue(page=1, kind=IssueKind.UNTRANSLATED_UNRESOLVED, block="multiple"))
        page_payload = report.to_dict()["pages"][0]
        self.assertIn("issues", page_payload)
        self.assertEqual(set(page_payload["issues"][0]) >= {"page", "type"}, True)


if __name__ == "__main__":
    unittest.main()
