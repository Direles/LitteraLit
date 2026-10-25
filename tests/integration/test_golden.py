"""Test golden (Fase 0): il risultato su un PDF sintetico non deve regredire.

Il confronto è sui **contatori**, non sulla geometria esatta: i numeri assoluti di un
layout possono variare di frazioni di punto fra piattaforme, ma il numero di blocchi,
le tipologie di issue e il conteggio dei `perfect` sono il contratto del comportamento.
"""

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from pdfbook.app import JobSpec, TranslationJob, build_runtime
from pdfbook.config.settings import AppSettings
from unit.fakes import EchoProvider

from .test_pipeline_fixtures import build_pdf

BASELINE = Path(__file__).resolve().parents[1] / "golden" / "baseline.json"
PERFECT_TOLERANCE = 1


class GoldenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_fixture(self):
        pdf = self.root / "fixture.pdf"
        build_pdf(pdf, pages=2)
        settings = AppSettings(
            provider="DeepSeek", model="deepseek-chat", api_key="k",
            cache_path=self.root / "cache.json",
        )
        spec = JobSpec(input_pdf=pdf, output_pdf=self.root / "out.pdf", settings=settings)
        runtime = build_runtime(pdf, settings)
        runtime.provider = EchoProvider()
        return TranslationJob(spec, runtime, sleep=lambda _: None).run()

    def test_pages_and_blocks_match_baseline(self):
        result = self.run_fixture()
        self.assertEqual(result.pages, self.baseline["pages"])
        self.assertEqual(result.blocks, self.baseline["blocks"])

    def test_issue_kinds_match_baseline(self):
        # Il provider finto non traduce davvero (prefissa "IT "): wrong_language e repetition
        # sono quindi attese e fanno parte della fotografia, non sono un difetto del test.
        # special_char_leak documenta il difetto §11.7/1 di PyMuPDF (NBSP nello strato testo).
        result = self.run_fixture()
        kinds = dict(sorted(Counter(issue.kind.value for issue in result.report.issues).items()))
        self.assertEqual(kinds, self.baseline["issue_kinds"])

    def test_perfect_is_stable(self):
        result = self.run_fixture()
        expected = self.baseline["summary"]["perfect"]
        self.assertLessEqual(abs(result.summary["perfect"] - expected), PERFECT_TOLERANCE)

    def test_font_counters_are_stable(self):
        result = self.run_fixture()
        for key in ("embedded_fonts_reused", "system_fonts_used", "base14_fallback"):
            self.assertEqual(result.summary[key], self.baseline["summary"][key], key)

    def test_no_base14_fallback_on_fixture(self):
        result = self.run_fixture()
        self.assertEqual(result.summary["base14_fallback"], 0)


if __name__ == "__main__":
    unittest.main()
