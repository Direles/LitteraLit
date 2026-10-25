"""Prova di carico: 500 pagine, 1500 blocchi, workers e ripresa (Fase 3.7).

Non verifica la qualità tipografica (quella la misurano i test golden): verifica che la
pipeline **non esploda** e non perda blocchi quando il libro è grande, che il
parallelismo non produca chiamate duplicate e che la ripresa non richiami il provider.
"""

import tempfile
import time
import unittest
from pathlib import Path

from pdfbook.app import JobSpec, TranslationJob
from pdfbook.config.settings import AppSettings
from pdfbook.qa.report import gate, parse_report
from unit.fakes import EchoProvider, FakeSource, make_block, make_line, make_page, make_runtime

PAGES = 500
BLOCKS_PER_PAGE = 3


class CountingProvider(EchoProvider):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def complete(self, prompt: str, system: str | None = None):
        self.calls += 1
        return super().complete(prompt, system)


def paragraph(page_number: int, index: int) -> str:
    filler = (
        "Questa e una frase di riempimento abbastanza lunga da somigliare a un paragrafo "
        "di un libro vero, con parole comuni e nessuna sorpresa tipografica."
    )
    return f"Pagina {page_number}, blocco {index}. {filler} {filler}"


def stress_pages(pages: int = PAGES) -> FakeSource:
    built = []
    for number in range(1, pages + 1):
        blocks = [
            make_block(
                f"b{index}",
                [
                    make_line(
                        paragraph(number, index)[offset : offset + 90],
                        y0=100 + index * 80 + line * 12,
                    )
                    for line, offset in enumerate((0, 90, 180, 270))
                ],
            )
            for index in range(BLOCKS_PER_PAGE)
        ]
        built.append(make_page(*blocks, number=number))
    return FakeSource(built)


class StressTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = AppSettings(
            provider="DeepSeek",
            model="deepseek-chat",
            api_key="k",
            cache_path=self.root / "cache.json",
            checkpoint_every=50,
            workers=4,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def job(self, runtime, **kwargs):
        spec = JobSpec(
            input_pdf=self.root / "in.pdf",
            output_pdf=self.root / "out.pdf",
            settings=self.settings,
            **kwargs,
        )
        return TranslationJob(spec, runtime, sleep=lambda _: None)

    def runtime(self, source, provider):
        return make_runtime(source, provider, self.root / "cache.json", save_calls=[])

    def test_500_pages_do_not_raise(self):
        provider = CountingProvider()
        started = time.perf_counter()
        result = self.job(self.runtime(stress_pages(), provider)).run()
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 120.0, f"troppo lento: {elapsed:.1f}s")
        self.assertEqual(result.blocks, PAGES * BLOCKS_PER_PAGE)
        self.assertGreater(provider.calls, 0)

    def test_report_has_no_blocking_issue(self):
        source = stress_pages(pages=40)
        job = self.job(self.runtime(source, EchoProvider()))
        result = job.run()
        report = parse_report(result.report_path)
        self.assertEqual(gate(report), [])

    def test_resume_does_not_call_the_provider_again(self):
        source = stress_pages(pages=30)
        first = CountingProvider()
        job = self.job(self.runtime(source, first))
        job.run()

        second = CountingProvider()
        job = self.job(self.runtime(source, second), resume=True)
        result = job.run()
        self.assertEqual(second.calls, 0, "la ripresa non deve ritradurre")
        self.assertEqual(result.blocks, 30 * BLOCKS_PER_PAGE)

    def test_every_page_is_visited_once(self):
        source = stress_pages(pages=25)
        job = self.job(self.runtime(source, EchoProvider()))
        job.run()
        self.assertEqual(source.requested, list(range(25)))


if __name__ == "__main__":
    unittest.main()
