"""Test della pipeline di documento (M11) con sorgente, provider e canvas finti."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.app import JobSpec, TranslationJob, batch_for_page
from pdfbook.config.settings import AppSettings
from pdfbook.domain.models import Rect
from pdfbook.qa.report import parse_report
from pdfbook.translation.providers.base import ProviderError

from .fakes import (
    EchoProvider,
    FailingProvider,
    FakeSource,
    PartialProvider,
    make_block,
    make_line,
    make_page,
    make_runtime,
)


def simple_page(*texts, number=1):
    return make_page(*[make_block(f"b{index}", [make_line(text)]) for index, text in enumerate(texts)], number=number)


class JobTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = AppSettings(
            provider="DeepSeek", model="deepseek-chat", api_key="k",
            cache_path=self.root / "cache.json",
        )
        self.saved = []

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, **kwargs):
        return JobSpec(
            input_pdf=self.root / "in.pdf",
            output_pdf=self.root / "out.pdf",
            settings=self.settings,
            **kwargs,
        )

    def run_job(self, source, provider, **kwargs):
        runtime = make_runtime(source, provider, self.root / "cache.json", save_calls=self.saved)
        return TranslationJob(self.spec(), runtime, sleep=lambda _: None).run(**kwargs)


class JobTest(JobTestCase):
    def test_saves_pdf_and_report(self):
        source = FakeSource([simple_page("Hello"), simple_page("World", number=2)])
        result = self.run_job(source, EchoProvider())
        self.assertEqual(self.saved, [str(self.root / "out.pdf")])
        self.assertTrue(result.report_path.exists())
        self.assertEqual((result.pages, result.blocks), (2, 2))
        self.assertEqual(result.violations(), [])
        self.assertEqual(result.summary["blocks"], 2)
        self.assertEqual(result.summary["system_fonts_used"], 1)

    def test_report_is_parseable_and_compatible(self):
        source = FakeSource([simple_page("Hello")])
        result = self.run_job(source, EchoProvider())
        parsed = parse_report(result.report_path)
        self.assertEqual(len(parsed.issues), 0)

    def test_missing_translation_blocks_the_gate(self):
        source = FakeSource([simple_page("Uno", "Due")])
        result = self.run_job(source, PartialProvider(keep=1))
        self.assertTrue(result.violations())
        self.assertIn("untranslated_unresolved", result.violations()[0])

    def test_page_range_limits_work(self):
        source = FakeSource([simple_page("A", number=1), simple_page("B", number=2), simple_page("C", number=3)])
        result = TranslationJob(
            self.spec(page_start=2, page_end=2),
            make_runtime(source, EchoProvider(), self.root / "cache.json", save_calls=self.saved),
            sleep=lambda _: None,
        ).run()
        self.assertEqual(source.requested, [1])
        self.assertEqual(result.pages, 1)

    def test_empty_document_raises_and_closes(self):
        source = FakeSource([make_page()])
        with self.assertRaises(ValueError):
            self.run_job(source, EchoProvider())
        self.assertTrue(source.closed)

    def test_provider_failure_propagates_and_closes(self):
        source = FakeSource([simple_page("Hello")])
        provider = FailingProvider()
        with self.assertRaises(ProviderError):
            self.run_job(source, provider)
        self.assertEqual(provider.calls, 3)
        self.assertTrue(source.closed)

    def test_cache_avoids_second_call(self):
        provider = EchoProvider()
        source = FakeSource([simple_page("Hello")])
        self.run_job(source, provider)
        calls_after_first = provider.calls
        self.run_job(source, provider)
        self.assertEqual(provider.calls, calls_after_first)

    def test_progress_is_reported(self):
        calls = []
        source = FakeSource([simple_page("A"), simple_page("B", number=2)])
        self.run_job(source, EchoProvider(), progress=lambda *args: calls.append(args))
        self.assertEqual([entry[0] for entry in calls], [1, 2])
        self.assertEqual(calls[-1][1], 2)


class BatchTest(unittest.TestCase):
    def test_prose_blocks_use_block_id(self):
        page = make_page(make_block("b0", [make_line("uno")]), make_block("b1", [make_line("due")]))
        self.assertEqual(batch_for_page(page), {"b0": "uno", "b1": "due"})

    def test_structured_blocks_use_line_keys(self):
        left = make_line("Titolo:", x0=0.0, width=60.0)
        right = make_line("Sottotitolo", x0=100.0, width=120.0)
        block = make_block("b0", [left, right], bbox=Rect(0, 100, 260, 130))
        self.assertEqual(batch_for_page(make_page(block)), {"b0_l0": "Titolo:", "b0_l1": "Sottotitolo"})

    def test_blank_blocks_are_skipped(self):
        page = make_page(make_block("b0", [make_line("   ")]))
        self.assertEqual(batch_for_page(page), {})


if __name__ == "__main__":
    unittest.main()
