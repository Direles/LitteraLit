"""Test della scoperta modelli su endpoint locali (LM Studio, Ollama)."""

import unittest

from pdfbook.translation.providers.base import ProviderError
from pdfbook.translation.providers.discovery import (
    LOCAL_PRESETS,
    ModelInfo,
    is_local,
    list_models,
    models_endpoint,
    parse_models,
)


class EndpointTest(unittest.TestCase):
    def test_adds_v1_and_models(self):
        self.assertEqual(models_endpoint("http://localhost:1234"), "http://localhost:1234/v1/models")

    def test_accepts_v1_and_trailing_slash(self):
        self.assertEqual(models_endpoint("http://localhost:1234/v1/"), "http://localhost:1234/v1/models")

    def test_adds_scheme(self):
        self.assertEqual(models_endpoint("localhost:1234"), "http://localhost:1234/v1/models")

    def test_custom_path_is_preserved(self):
        self.assertEqual(models_endpoint("http://host:8000/openai/v1"), "http://host:8000/openai/v1/models")

    def test_empty_is_an_error(self):
        with self.assertRaises(ProviderError):
            models_endpoint("  ")

    def test_presets(self):
        self.assertEqual(LOCAL_PRESETS["lm-studio"], "http://localhost:1234/v1")
        self.assertIn("ollama", LOCAL_PRESETS)


class LocalTest(unittest.TestCase):
    def test_localhost_is_local(self):
        for url in ("http://localhost:1234/v1", "http://127.0.0.1:8080/v1", "http://[::1]:9000"):
            self.assertTrue(is_local(url), url)

    def test_remote_is_not_local(self):
        self.assertFalse(is_local("https://api.openai.com/v1"))


class ParseTest(unittest.TestCase):
    def test_openai_format(self):
        models = parse_models({"data": [{"id": "qwen2.5-7b-instruct", "owned_by": "lmstudio"}]})
        self.assertEqual(models, [ModelInfo("qwen2.5-7b-instruct", "lmstudio", 0)])

    def test_context_length_is_read(self):
        models = parse_models({"data": [{"id": "m", "context_length": 32768}]})
        self.assertEqual(models[0].context_length, 32768)

    def test_ollama_style_list(self):
        models = parse_models({"models": [{"name": "llama3.2:3b"}]})
        self.assertEqual(models[0].id, "llama3.2:3b")

    def test_strings_are_accepted(self):
        self.assertEqual([m.id for m in parse_models({"data": ["a", "b"]})], ["a", "b"])

    def test_duplicates_and_blanks_are_dropped(self):
        models = parse_models({"data": [{"id": "a"}, {"id": "a"}, {"id": " "}, 42]})
        self.assertEqual([m.id for m in models], ["a"])

    def test_empty_payload(self):
        self.assertEqual(parse_models({}), [])

    def test_label_mentions_context(self):
        self.assertEqual(ModelInfo("m", "", 8192).label, "m (8192 token)")


class ListTest(unittest.TestCase):
    def test_returns_models_via_injected_transport(self):
        calls = []

        def fake(url, headers, timeout):
            calls.append((url, headers, timeout))
            return {"data": [{"id": "qwen2.5-7b-instruct"}]}

        models = list_models("http://localhost:1234", get_json=fake)
        self.assertEqual([m.id for m in models], ["qwen2.5-7b-instruct"])
        self.assertEqual(calls[0][0], "http://localhost:1234/v1/models")
        self.assertNotIn("Authorization", calls[0][1])

    def test_api_key_is_sent_when_present(self):
        seen = {}

        def fake(url, headers, timeout):
            seen.update(headers)
            return {"data": []}

        list_models("http://localhost:1234/v1", api_key="k", get_json=fake)
        self.assertEqual(seen["Authorization"], "Bearer k")

    def test_transport_error_becomes_actionable(self):
        def broken(url, headers, timeout):
            raise ProviderError("connessione rifiutata")

        with self.assertRaises(ProviderError) as ctx:
            list_models("http://localhost:1234", get_json=broken)
        self.assertIn("connessione rifiutata", str(ctx.exception))

    def test_connection_error_mentions_lm_studio(self):
        import requests

        def refused(url, headers, timeout):
            raise requests.ConnectionError("refused")

        with self.assertRaises(ProviderError) as ctx:
            list_models("http://localhost:1234", get_json=refused)
        self.assertIn("LM Studio", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
