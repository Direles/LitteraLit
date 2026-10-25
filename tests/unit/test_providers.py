"""Test dei provider (M2): trasporto, estrazione della risposta, registry."""

import unittest

import requests

from pdfbook.domain.models import TranslationSettings
from pdfbook.translation.providers import ProviderError, create_provider, provider_endpoint
from pdfbook.translation.providers.anthropic import AnthropicProvider
from pdfbook.translation.providers.base import error_detail, post_json
from pdfbook.translation.providers.gemini import GeminiProvider
from pdfbook.translation.providers.openai_compatible import OpenAIChatProvider


class StubResponse:
    def __init__(self, data=None, status=200, text=""):
        self._data = data
        self.status_code = status
        self.text = text

    def json(self):
        if self._data is None:
            raise ValueError("nessun JSON")
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class StubSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, *, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


class TransportTest(unittest.TestCase):
    def test_http_error_exposes_api_message(self):
        session = StubSession(StubResponse({"error": {"message": "insufficient quota"}}, status=429))
        with self.assertRaises(ProviderError) as ctx:
            post_json(session, "http://x", {}, {})
        self.assertIn("insufficient quota", str(ctx.exception))

    def test_non_json_body_is_degraded(self):
        session = StubSession(StubResponse(status=500, text="upstream down"))
        with self.assertRaises(ProviderError) as ctx:
            post_json(session, "http://x", {}, {})
        self.assertIn("upstream down", str(ctx.exception))

    def test_network_error_is_normalized(self):
        session = StubSession(error=requests.ConnectionError("boom"))
        with self.assertRaises(ProviderError):
            post_json(session, "http://x", {}, {})

    def test_response_must_be_object(self):
        session = StubSession(StubResponse([1, 2, 3]))
        with self.assertRaises(ProviderError):
            post_json(session, "http://x", {}, {})

    def test_error_detail_fallbacks(self):
        self.assertEqual(error_detail(StubResponse({"detail": "ko"})), "ko")
        self.assertEqual(error_detail(StubResponse({"error": "ko"})), "ko")
        self.assertTrue(error_detail(StubResponse(status=418)).startswith("HTTP 418"))


class OpenAICompatibleTest(unittest.TestCase):
    def make(self, session):
        return OpenAIChatProvider(
            name="deepseek", endpoint="https://api.deepseek.com", model="m", api_key="k",
            session=session,
        )

    def test_extracts_content_and_builds_request(self):
        session = StubSession(StubResponse({"choices": [{"message": {"content": '{"a": "b"}'}}]}))
        provider = self.make(session)
        self.assertEqual(provider.complete("sys", "usr"), '{"a": "b"}')
        call = session.calls[0]
        self.assertEqual(call["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(call["headers"]["Authorization"], "Bearer k")
        self.assertEqual(call["json"]["response_format"], {"type": "json_object"})
        self.assertEqual(call["json"]["messages"][0]["role"], "system")

    def test_chat_suffix_is_not_duplicated(self):
        provider = OpenAIChatProvider(
            name="openai", endpoint="https://api.openai.com/v1/chat/completions",
            model="m", api_key="k", session=StubSession(StubResponse({})),
        )
        self.assertEqual(provider.endpoint, "https://api.openai.com/v1/chat/completions")

    def test_missing_content_raises(self):
        session = StubSession(StubResponse({"choices": [{"message": {}}]}))
        with self.assertRaises(ProviderError):
            self.make(session).complete("s", "u")

    def test_empty_choices_raises(self):
        session = StubSession(StubResponse({"choices": []}))
        with self.assertRaises(ProviderError):
            self.make(session).complete("s", "u")


class GeminiTest(unittest.TestCase):
    def test_uses_header_and_not_query_string(self):
        session = StubSession(StubResponse({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}))
        provider = GeminiProvider(model="gemini-x", api_key="secret", session=session)
        self.assertEqual(provider.complete("s", "u"), "ok")
        call = session.calls[0]
        self.assertNotIn("key=", call["url"])
        self.assertEqual(call["headers"]["x-goog-api-key"], "secret")
        self.assertIn("gemini-x", call["url"])
        self.assertEqual(call["json"]["generationConfig"]["responseMimeType"], "application/json")

    def test_blocked_prompt_reports_reason(self):
        session = StubSession(StubResponse({"promptFeedback": {"blockReason": "SAFETY"}}))
        provider = GeminiProvider(model="m", api_key="k", session=session)
        with self.assertRaises(ProviderError) as ctx:
            provider.complete("s", "u")
        self.assertIn("SAFETY", str(ctx.exception))

    def test_missing_parts_raises(self):
        session = StubSession(StubResponse({"candidates": [{"content": {}}]}))
        provider = GeminiProvider(model="m", api_key="k", session=session)
        with self.assertRaises(ProviderError):
            provider.complete("s", "u")


class AnthropicTest(unittest.TestCase):
    def test_skips_thinking_block(self):
        data = {"content": [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "ok"}]}
        session = StubSession(StubResponse(data))
        provider = AnthropicProvider(model="claude", api_key="k", session=session)
        self.assertEqual(provider.complete("s", "u"), "ok")
        headers = session.calls[0]["headers"]
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        self.assertEqual(headers["x-api-key"], "k")
        self.assertEqual(session.calls[0]["json"]["system"], "s")

    def test_without_text_block_raises(self):
        session = StubSession(StubResponse({"content": [{"type": "thinking"}]}))
        provider = AnthropicProvider(model="m", api_key="k", session=session)
        with self.assertRaises(ProviderError):
            provider.complete("s", "u")


class RegistryTest(unittest.TestCase):
    def test_builds_every_provider(self):
        expected = {
            "Google Gemini": "gemini",
            "OpenAI": "openai",
            "DeepSeek": "deepseek",
            "Anthropic Claude": "anthropic",
            "Custom OpenAI-Compatible": "custom",
        }
        for name, slug in expected.items():
            extra = {"base_url": "http://localhost:11434/v1"} if slug == "custom" else {}
            settings = TranslationSettings(provider=name, model="m", **extra)
            provider = create_provider(settings, "k", session=StubSession(StubResponse({})))
            self.assertEqual(provider.name, slug)

    def test_unknown_provider(self):
        with self.assertRaises(ProviderError):
            create_provider(TranslationSettings(provider="Altro", model="m"), "k")

    def test_key_required_except_custom(self):
        with self.assertRaises(ProviderError):
            create_provider(TranslationSettings(provider="OpenAI", model="m"), "  ")
        settings = TranslationSettings(
            provider="Custom OpenAI-Compatible", model="m", base_url="http://h/v1"
        )
        self.assertIsNotNone(create_provider(settings, ""))

    def test_custom_requires_base_url(self):
        settings = TranslationSettings(provider="Custom OpenAI-Compatible", model="m")
        with self.assertRaises(ProviderError):
            provider_endpoint(settings)


if __name__ == "__main__":
    unittest.main()
