"""Test dell'aggancio della memoria terminologica al job (Fase 5.3)."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.app import JobSpec, TranslationJob
from pdfbook.config.settings import AppSettings

from .fakes import EchoProvider, FakeSource, make_block, make_line, make_page, make_runtime

PARAGRAPH = (
    "Kent Beck describes Extreme Programming in this chapter and explains why the practice "
    "matters for teams that adopt it on real projects."
)


def corpus_page(number=1):
    return make_page(make_block("b0", [make_line(PARAGRAPH)]), number=number)


class SuggestionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = AppSettings(
            provider="DeepSeek",
            model="deepseek-chat",
            api_key="k",
            cache_path=self.root / "cache.json",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_job(self, pages, **settings):
        spec = JobSpec(
            input_pdf=self.root / "in.pdf",
            output_pdf=self.root / "out.pdf",
            settings=AppSettings(
                provider="DeepSeek",
                model="deepseek-chat",
                api_key="k",
                cache_path=self.root / "cache.json",
                stitch_paragraphs=False,
                **settings,
            ),
        )
        runtime = make_runtime(FakeSource(pages), EchoProvider(), self.root / "cache.json", save_calls=[])
        return TranslationJob(spec, runtime, sleep=lambda _: None).run()

    def test_recurring_names_become_suggestions(self):
        result = self.run_job([corpus_page(number) for number in range(1, 4)])
        self.assertTrue(result.glossary_suggestions, result.glossary_suggestions)

    def test_already_known_terms_are_not_suggested(self):
        result = self.run_job(
            [corpus_page(number) for number in range(1, 4)], glossary=("Kent Beck",)
        )
        self.assertNotIn("Kent Beck", result.glossary_suggestions)

    def test_single_page_suggests_nothing(self):
        result = self.run_job([corpus_page()])
        self.assertEqual(result.glossary_suggestions, [])


if __name__ == "__main__":
    unittest.main()
