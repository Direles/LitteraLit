"""Test della pipeline (M4): cache, chunking, retry, chiavi mancanti."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.domain.models import TranslationSettings
from pdfbook.translation.cache import TranslationCache
from pdfbook.translation.pipeline import TranslationPipeline
from pdfbook.translation.providers.base import ProviderError


class FakeProvider:
    name = "fake"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system, user):
        self.calls.append({"system": system, "user": user})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def json_response(mapping):
    import json
    return json.dumps(mapping, ensure_ascii=False)


class PipelineTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = TranslationCache(Path(self.tmp.name) / "tm.json", "part", autosave_every=0)
        self.settings = TranslationSettings(provider="DeepSeek", model="deepseek-chat")
        self.sleeps = []

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, *responses, **kwargs):
        return TranslationPipeline(
            provider=FakeProvider(*responses),
            cache=self.cache,
            settings=self.settings,
            sleep=self.sleeps.append,
            **kwargs,
        )


class TranslationTest(PipelineTestCase):
    def test_translates_and_caches(self):
        pipeline = self.make(json_response({"a": "uno", "b": "due"}))
        outcome = pipeline.translate({"a": "one", "b": "two"})
        self.assertEqual(dict(outcome.translations), {"a": "uno", "b": "due"})
        self.assertTrue(outcome.complete)
        self.assertEqual(outcome.requested, 2)
        self.assertEqual(pipeline.cache.get("one"), "uno")

    def test_cache_hit_skips_provider(self):
        self.cache.put("one", "uno")
        pipeline = self.make()  # nessuna risposta: se chiamasse il provider fallirebbe
        outcome = pipeline.translate({"a": "one"})
        self.assertEqual(dict(outcome.translations), {"a": "uno"})
        self.assertEqual(outcome.cached, 1)
        self.assertEqual(pipeline.provider.calls, [])

    def test_missing_key_is_reported_not_faked(self):
        pipeline = self.make(json_response({"a": "uno"}))
        outcome = pipeline.translate({"a": "one", "b": "two"})
        self.assertEqual(outcome.missing, ("b",))
        self.assertFalse(outcome.complete)
        self.assertNotIn("b", outcome.translations)
        self.assertIsNone(self.cache.get("two"))

    def test_blank_values_do_not_call_provider(self):
        pipeline = self.make()
        outcome = pipeline.translate({"a": "   ", "b": ""})
        self.assertEqual(dict(outcome.translations), {"a": "", "b": ""})
        self.assertEqual(pipeline.provider.calls, [])

    def test_context_is_passed_to_the_prompt(self):
        pipeline = self.make(json_response({"a": "uno"}))
        pipeline.translate({"a": "one"}, context="pagina precedente")
        self.assertIn("pagina precedente", pipeline.provider.calls[0]["system"])

    def test_glossary_reaches_the_prompt(self):
        self.settings = self.settings.with_glossary(["Sprint"])
        pipeline = self.make(json_response({"a": "uno"}))
        pipeline.translate({"a": "one"})
        self.assertIn("'Sprint'", pipeline.provider.calls[0]["system"])

    def test_large_batch_is_chunked(self):
        pipeline = self.make(
            json_response({"a": "uno"}),
            json_response({"b": "due"}),
            json_response({"c": "tre"}),
            max_chars=20,
        )
        outcome = pipeline.translate({"a": "x" * 10, "b": "y" * 10, "c": "z" * 10})
        self.assertTrue(outcome.complete)
        self.assertEqual(len(pipeline.provider.calls), 3)


class RetryTest(PipelineTestCase):
    def test_retries_then_succeeds(self):
        pipeline = self.make(ProviderError("429"), json_response({"a": "uno"}))
        outcome = pipeline.translate({"a": "one"})
        self.assertEqual(dict(outcome.translations), {"a": "uno"})
        self.assertEqual(self.sleeps, [1.5])

    def test_retries_on_unparseable_response(self):
        pipeline = self.make("non json", json_response({"a": "uno"}))
        outcome = pipeline.translate({"a": "one"})
        self.assertEqual(dict(outcome.translations), {"a": "uno"})

    def test_exhausted_retries_raise(self):
        pipeline = self.make(ProviderError("down"), ProviderError("down"), ProviderError("down"))
        with self.assertRaises(ProviderError):
            pipeline.translate({"a": "one"})
        self.assertEqual(self.sleeps, [1.5, 2.25])

    def test_empty_payload_is_retried(self):
        pipeline = self.make("{}", json_response({"a": "uno"}))
        self.assertEqual(dict(pipeline.translate({"a": "one"}).translations), {"a": "uno"})


class ShortenTest(PipelineTestCase):
    def test_returns_shorter_version_and_caches(self):
        pipeline = self.make(json_response({"short": "breve"}))
        self.assertEqual(pipeline.shorten("very long original", "traduzione lunga", 10), "breve")
        self.assertEqual(pipeline.cache.get("[short]10|very long original"), "breve")

    def test_cached_shortening_does_not_call_provider(self):
        self.cache.put("[short]10|orig", "breve")
        pipeline = self.make()
        self.assertEqual(pipeline.shorten("orig", "traduzione lunga", 10), "breve")
        self.assertEqual(pipeline.provider.calls, [])

    def test_longer_or_missing_short_keeps_current(self):
        pipeline = self.make(json_response({"short": "molto più lunga della corrente"}))
        current = "corta"
        self.assertEqual(pipeline.shorten("originale", current, 5), current)

    def test_failure_keeps_current(self):
        pipeline = self.make(ProviderError("x"), ProviderError("x"), ProviderError("x"))
        self.assertEqual(pipeline.shorten("orig", "corrente", 5), "corrente")

    def test_invalid_budget_returns_current(self):
        pipeline = self.make()
        self.assertEqual(pipeline.shorten("orig", "corrente", 0), "corrente")


class IsolationTest(PipelineTestCase):
    def test_other_settings_do_not_reuse_cache(self):
        other = TranslationPipeline(
            provider=FakeProvider(json_response({"a": "uno"})),
            cache=TranslationCache(Path(self.tmp.name) / "tm.json", "other-part", autosave_every=0),
            settings=self.settings,
            sleep=self.sleeps.append,
        )
        other.translate({"a": "one"})
        self.assertIsNone(self.cache.get("one"))


if __name__ == "__main__":
    unittest.main()
