"""Test dei prompt (M4): contenuto, limiti, normalizzazione."""

import json
import unittest

from pdfbook.translation.prompts import (
    MAX_CONTEXT_CHARS,
    build_shorten_payload,
    build_shorten_prompt,
    build_translation_prompt,
    build_user_payload,
    glossary_terms,
)


class TranslationPromptTest(unittest.TestCase):
    def test_contains_target_language_and_rules(self):
        prompt = build_translation_prompt("Italiano")
        self.assertIn("Italiano", prompt)
        self.assertIn("Return ONLY the translated JSON object", prompt)
        self.assertIn("■", prompt)

    def test_glossary_terms_are_quoted(self):
        prompt = build_translation_prompt("Italiano", glossary=["Sprint", " Backlog ", ""])
        self.assertIn("'Sprint'", prompt)
        self.assertIn("'Backlog'", prompt)
        self.assertNotIn("''", prompt)

    def test_context_is_truncated(self):
        prompt = build_translation_prompt("Italiano", context="x" * 5000, max_context_chars=100)
        body = prompt.split("---")[1]
        self.assertEqual(len(body.strip()), 100)

    def test_default_context_budget(self):
        prompt = build_translation_prompt("Italiano", context="y" * 9000)
        body = prompt.split("---")[1]
        self.assertEqual(len(body.strip()), MAX_CONTEXT_CHARS)

    def test_empty_context_does_not_add_section(self):
        self.assertNotIn("previous page", build_translation_prompt("Italiano", context="   "))

    def test_glossary_normalization(self):
        self.assertEqual(glossary_terms([" Sprint ", "", "Sprint", "Backlog"]), ("Sprint", "Backlog"))


class ShortenPromptTest(unittest.TestCase):
    def test_mentions_budget_and_language(self):
        prompt = build_shorten_prompt("Italiano", 120, glossary=["Sprint"])
        self.assertIn("120 characters", prompt)
        self.assertIn("Italiano", prompt)
        self.assertIn("Sprint", prompt)

    def test_rejects_non_positive_budget(self):
        with self.assertRaises(ValueError):
            build_shorten_prompt("Italiano", 0)

    def test_payload_shape(self):
        payload = json.loads(build_shorten_payload("orig", "corrente", 80))
        self.assertEqual(payload, {
            "original_english": "orig", "current_translation": "corrente", "max_chars": 80,
        })


class UserPayloadTest(unittest.TestCase):
    def test_preserves_unicode_and_keys(self):
        payload = build_user_payload({"b1": "città — prova", "b2": "ok"})
        self.assertIn("città — prova", payload)
        self.assertEqual(list(json.loads(payload)), ["b1", "b2"])


if __name__ == "__main__":
    unittest.main()
