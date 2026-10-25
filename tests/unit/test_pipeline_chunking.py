"""Test del chunking per frase dentro la pipeline (Fase 5.2)."""

import json
import tempfile
import unittest
from pathlib import Path

from pdfbook.domain.models import TranslationSettings
from pdfbook.translation.cache import TranslationCache
from pdfbook.translation.chunking import PART_SEPARATOR
from pdfbook.translation.pipeline import TranslationPipeline

LONG = " ".join(f"Questa è la frase numero {index} del blocco lungo." for index in range(8))


class EchoJsonProvider:
    """Provider che risponde in JSON con una traduzione riconoscibile per chiave."""

    name = "echo"

    def __init__(self):
        self.calls = []

    def complete(self, system, user):
        from pdfbook.translation.providers.base import Completion

        self.calls.append(user)
        payload = json.loads(user)
        return Completion(json.dumps({key: f"IT-{key}" for key in payload}), 10, 10)


class ChunkingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = TranslationCache(Path(self.tmp.name) / "tm.json", "p", autosave_every=0)
        self.settings = TranslationSettings(provider="DeepSeek", model="deepseek-chat")

    def tearDown(self):
        self.tmp.cleanup()

    def pipeline(self, provider, max_chars=200):
        return TranslationPipeline(
            provider=provider,
            cache=self.cache,
            settings=self.settings,
            max_chars=max_chars,
            sleep=lambda _s: None,
        )

    def test_long_unit_is_split_and_rejoined(self):
        provider = EchoJsonProvider()
        outcome = self.pipeline(provider).translate({"b0": LONG})
        self.assertIn("b0", outcome.translations)
        self.assertTrue(outcome.translations["b0"].startswith("IT-b0"))
        self.assertIn("IT-b0", outcome.translations["b0"])
        self.assertEqual(outcome.missing, ())
        self.assertGreater(len(provider.calls), 1)

    def test_short_units_are_not_split(self):
        provider = EchoJsonProvider()
        outcome = self.pipeline(provider, max_chars=600).translate({"a": "one", "b": "two"})
        self.assertEqual(set(outcome.translations), {"a", "b"})
        self.assertEqual(len(provider.calls), 1)

    def test_part_keys_never_leak(self):
        provider = EchoJsonProvider()
        outcome = self.pipeline(provider).translate({"b0": LONG})
        self.assertFalse([key for key in outcome.translations if PART_SEPARATOR in key])


if __name__ == "__main__":
    unittest.main()
