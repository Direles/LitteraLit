"""Test della configurazione (M11): ambiente, segreti, validazione."""

import tempfile
import unittest
from pathlib import Path

from pdfbook.config.settings import (
    AppSettings,
    load_env_file,
    load_settings,
    parse_glossary,
)


class DefaultsTest(unittest.TestCase):
    def test_defaults_with_empty_environment(self):
        settings = load_settings({})
        self.assertEqual(settings.provider, "DeepSeek")
        self.assertEqual(settings.target_lang, "Italiano")
        self.assertEqual(settings.glossary, ())
        self.assertEqual(settings.api_key, "")

    def test_environment_overrides(self):
        settings = load_settings({
            "PDFBOOK_PROVIDER": "OpenAI",
            "PDFBOOK_MODEL": "gpt-4o",
            "PDFBOOK_TARGET_LANG": "Tedesco",
            "PDFBOOK_GLOSSARY": "Sprint, Backlog ,Sprint",
            "PDFBOOK_API_KEY": "segreto",
        })
        self.assertEqual(settings.provider, "OpenAI")
        self.assertEqual(settings.model, "gpt-4o")
        self.assertEqual(settings.target_lang, "Tedesco")
        self.assertEqual(settings.glossary, ("Sprint", "Backlog"))
        self.assertEqual(settings.api_key, "segreto")

    def test_cache_path_is_expanded(self):
        settings = load_settings({"PDFBOOK_CACHE_PATH": "~/tm.json"})
        self.assertTrue(str(settings.cache_path).endswith("tm.json"))
        self.assertNotIn("~", str(settings.cache_path))

    def test_env_file_is_overridden_by_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("PDFBOOK_PROVIDER=OpenAI\n# commento\nPDFBOOK_MODEL=gpt-4o\n", encoding="utf-8")
            settings = load_settings({"PDFBOOK_PROVIDER": "DeepSeek"}, env_file=env_file)
            self.assertEqual(settings.provider, "DeepSeek")
            self.assertEqual(settings.model, "gpt-4o")

    def test_missing_env_file_is_ignored(self):
        self.assertEqual(load_env_file("non_esiste.env"), {})


class ValidationTest(unittest.TestCase):
    def test_language_is_validated(self):
        with self.assertRaises(ValueError):
            AppSettings(target_lang="Russo")

    def test_log_level_is_validated(self):
        with self.assertRaises(ValueError):
            AppSettings(log_level="VERBOSE")

    def test_api_key_required_for_known_providers(self):
        self.assertEqual(AppSettings(provider="Google Gemini").missing_required(), ("PDFBOOK_API_KEY",))
        self.assertEqual(AppSettings(provider="DeepSeek", api_key="k").missing_required(), ())

    def test_custom_provider_requires_base_url(self):
        settings = AppSettings(provider="Custom OpenAI-Compatible")
        self.assertEqual(settings.missing_required(), ("PDFBOOK_BASE_URL",))

    def test_translation_settings_are_projected(self):
        projection = AppSettings(
            provider="OpenAI", model="gpt-4o", glossary=("Sprint",), api_key="k"
        ).translation_settings()
        self.assertEqual(
            (projection.provider, projection.model, projection.glossary),
            ("OpenAI", "gpt-4o", ("Sprint",)),
        )


class SecretsTest(unittest.TestCase):
    def test_repr_does_not_contain_the_key(self):
        settings = AppSettings(api_key="sk-segreto")
        self.assertNotIn("sk-segreto", repr(settings))

    def test_redacted_reports_only_presence(self):
        redacted = AppSettings(api_key="sk-segreto").redacted()
        self.assertNotIn("api_key", redacted)
        self.assertTrue(redacted["has_api_key"])
        self.assertNotIn("sk-segreto", str(redacted))

    def test_glossary_parser(self):
        self.assertEqual(parse_glossary(" a, ,b ,a "), ("a", "b"))
        self.assertEqual(parse_glossary(""), ())


if __name__ == "__main__":
    unittest.main()
