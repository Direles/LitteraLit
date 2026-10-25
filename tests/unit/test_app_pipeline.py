"""Test della pipeline di documento (M11) con sorgente, provider e canvas finti."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.app import JobSpec, TranslationJob, block_units, build_plans
from pdfbook.config.settings import AppSettings
from pdfbook.domain.models import Rect
from pdfbook.qa.report import parse_report
from pdfbook.translation.providers.base import ProviderError

from .fakes import (
    EchoProvider,
    FailingProvider,
    FakeSource,
    FixedProvider,
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
        self.assertEqual(block_units(page), {"b0": "uno", "b1": "due"})

    def test_structured_blocks_use_line_keys(self):
        left = make_line("Titolo:", x0=0.0, width=60.0)
        right = make_line("Sottotitolo", x0=100.0, width=120.0)
        block = make_block("b0", [left, right], bbox=Rect(0, 100, 260, 130))
        self.assertEqual(block_units(make_page(block)), {"b0_l0": "Titolo:", "b0_l1": "Sottotitolo"})

    def test_blank_blocks_are_skipped(self):
        page = make_page(make_block("b0", [make_line("   ")]))
        self.assertEqual(block_units(page), {})


class StitchTest(JobTestCase):
    def build_source(self):
        first = make_page(
            make_block("b0", [make_line("Il testo resta aperto senza punto finale")]), number=1
        )
        second = make_page(
            make_block("b0", [make_line("continua sulla pagina seguente con altre parole.")]), number=2
        )
        return FakeSource([first, second])

    def test_continuation_is_translated_once(self):
        provider = EchoProvider()
        result = self.run_job(self.build_source(), provider)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(result.summary.get("stitched"), 1)
        self.assertEqual(result.violations(), [])

    def test_stitch_can_be_disabled(self):
        settings = AppSettings(
            provider="DeepSeek", model="m", api_key="k",
            cache_path=self.root / "cache2.json", stitch_paragraphs=False,
        )
        provider = EchoProvider()
        runtime = make_runtime(self.build_source(), provider, settings.cache_path, save_calls=[])
        spec = JobSpec(self.root / "in.pdf", self.root / "out.pdf", settings)
        TranslationJob(spec, runtime, sleep=lambda _: None).run()
        self.assertEqual(provider.calls, 2)

    def test_unusable_split_fails_the_gate(self):
        result = self.run_job(self.build_source(), FixedProvider("x"))
        self.assertIn("split_failed", " ".join(result.violations()))


class PlanTest(unittest.TestCase):
    def test_continuation_merges_requests(self):
        first = make_page(
            make_block("b0", [make_line("Il testo resta aperto senza punto finale")]), number=1
        )
        second = make_page(
            make_block("b0", [make_line("continua sulla pagina seguente con parole")]), number=2
        )
        plans = build_plans([first, second])
        self.assertEqual(len(plans[0].requests), 1)
        self.assertEqual(plans[1].requests, {})
        target = plans[0].targets[next(iter(plans[0].requests))]
        self.assertEqual((target.first_block, target.second_block), ("b0", "b0"))

    def test_stitch_disabled_keeps_blocks_separate(self):
        pages = [
            make_page(make_block("b0", [make_line("aperto senza punto finale qui")]), number=1),
            make_page(make_block("b0", [make_line("continua sulla pagina seguente")]), number=2),
        ]
        plans = build_plans(pages, stitch=False)
        self.assertEqual(len(plans[0].requests), 1)
        self.assertEqual(len(plans[1].requests), 1)

    def test_terminated_paragraph_is_not_merged(self):
        pages = [
            make_page(make_block("b0", [make_line("Il paragrafo finisce con un punto.")]), number=1),
            make_page(make_block("b0", [make_line("e la pagina dopo inizia minuscola")]), number=2),
        ]
        plans = build_plans(pages)
        self.assertEqual(len(plans[0].requests), 1)
        self.assertEqual(len(plans[1].requests), 1)


if __name__ == "__main__":
    unittest.main()
