"""Test di integrazione (Fase 0): PDF sintetici generati al volo, nessun dato editoriale.

I PDF di prova sono costruiti in memoria con PyMuPDF: il repository resta privo di file
binari e di contenuti protetti, e i test girano identici in locale e in CI.
"""

import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz

from pdfbook.app import JobSpec, TranslationJob, build_runtime
from pdfbook.config.settings import AppSettings
from pdfbook.qa.report import parse_report
from pdfbook.translation.providers.base import ProviderError
from unit.fakes import EchoProvider, FailingProvider

BODY = "This is a translated paragraph with several words in the body of the page."


def build_pdf(path: Path, pages: int = 2) -> None:
    """PDF nativo semplice: un titolo, un paragrafo e un numero di pagina per pagina."""
    doc = fitz.open()
    for number in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 90), f"Chapter {number + 1}", fontsize=18, fontname="helv")
        for line in range(6):
            page.insert_text((72, 130 + line * 14), BODY, fontsize=10, fontname="helv")
        page.insert_text((72, 700), "42", fontsize=9, fontname="helv")
    doc.save(str(path))
    doc.close()


class PipelineIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pdf = self.root / "fixture.pdf"
        build_pdf(self.pdf, pages=2)

    def tearDown(self):
        self.tmp.cleanup()

    def settings(self, **overrides):
        base = {
            "provider": "DeepSeek",
            "model": "deepseek-chat",
            "api_key": "k",
            "cache_path": self.root / "cache.json",
        }
        base.update(overrides)
        return AppSettings(**base)

    def run_job(self, provider=None, settings=None):
        settings = settings or self.settings()
        spec = JobSpec(
            input_pdf=self.pdf,
            output_pdf=self.root / "out.pdf",
            settings=settings,
        )
        runtime = build_runtime(self.pdf, settings)
        runtime.provider = provider or EchoProvider()
        return TranslationJob(spec, runtime, sleep=lambda _: None).run()

    def test_fixture_is_translated_and_report_written(self):
        result = self.run_job()
        self.assertTrue(Path(result.output_pdf).exists())
        self.assertEqual(result.pages, 2)
        self.assertGreater(result.blocks, 0)
        self.assertTrue(result.report_path.exists())

    def test_report_is_parseable_and_counters_are_consistent(self):
        result = self.run_job()
        parsed = parse_report(result.report_path)
        self.assertEqual(len(parsed.issues), len(result.report.issues))
        self.assertGreater(result.summary["blocks"], 0)

    def test_output_text_contains_the_translation(self):
        result = self.run_job()
        with fitz.open(result.output_pdf) as doc:
            text = "".join(page.get_text() for page in doc)
        self.assertIn("IT", text)

    def test_visual_qa_finds_no_drift_on_a_clean_run(self):
        result = self.run_job()
        drift = [issue for issue in result.report.issues if issue.kind.value == "visual_drift"]
        self.assertEqual(drift, [])

    def test_visual_qa_can_be_disabled(self):
        result = self.run_job(settings=self.settings(visual_qa=False))
        self.assertTrue(result.report_path.exists())

    def test_provider_failure_stops_the_job(self):
        with self.assertRaises(ProviderError):
            self.run_job(provider=FailingProvider())


if __name__ == "__main__":
    unittest.main()
