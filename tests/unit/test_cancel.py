"""Test dell'annullamento cooperativo di un job (Fase 6.1)."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.app import JobSpec, TranslationJob
from pdfbook.app.errors import Cancelled, classify, describe
from pdfbook.config.settings import AppSettings

from .fakes import EchoProvider, FakeSource, make_block, make_line, make_page, make_runtime


def corpus(pages=6):
    return FakeSource(
        [
            make_page(
                make_block("b0", [make_line(f"Testo della pagina {number}, abbastanza lungo.")]),
                number=number,
            )
            for number in range(1, pages + 1)
        ]
    )


class CancelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = AppSettings(
            provider="DeepSeek",
            model="deepseek-chat",
            api_key="k",
            cache_path=self.root / "cache.json",
            checkpoint_every=1,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def job(self, source, provider):
        spec = JobSpec(
            input_pdf=self.root / "in.pdf",
            output_pdf=self.root / "out.pdf",
            settings=self.settings,
        )
        runtime = make_runtime(source, provider, self.root / "cache.json", save_calls=[])
        return TranslationJob(spec, runtime, sleep=lambda _s: None)

    def test_cancel_before_the_second_page_stops_the_run(self):
        calls = []

        def cancel():
            calls.append(1)
            return len(calls) > 1

        with self.assertRaises(Cancelled):
            self.job(corpus(6), EchoProvider()).run(cancel=cancel)

    def test_cancel_keeps_the_journal_for_resume(self):
        from pdfbook.app.journal import journal_path

        source = corpus(4)
        # Annulla appena il job ha chiesto la prima pagina: il journal deve restare.
        with self.assertRaises(Cancelled):
            self.job(source, EchoProvider()).run(cancel=lambda: bool(source.requested))
        self.assertTrue(journal_path(self.root / "out.pdf").exists())

    def test_without_cancel_the_run_completes(self):
        result = self.job(corpus(3), EchoProvider()).run(cancel=lambda: False)
        self.assertEqual(result.pages, 3)

    def test_cancel_error_is_actionable(self):
        message = describe(Cancelled("annullato dall'utente"))
        self.assertIn("annullato", message.lower())
        self.assertIn("--resume", message)
        self.assertEqual(classify(Cancelled("x")), "cancelled")


if __name__ == "__main__":
    unittest.main()
