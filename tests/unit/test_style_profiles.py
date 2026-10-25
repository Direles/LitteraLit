"""Test dei profili di stile (Fase 5.5)."""

import unittest

from pdfbook.domain.models import TranslationSettings
from pdfbook.translation.prompts import build_translation_prompt
from pdfbook.translation.style import DEFAULT_PROFILE, PROFILES, profile_names, resolve, style_rule


class ProfileTest(unittest.TestCase):
    def test_default_profile_has_no_rule(self):
        self.assertEqual(style_rule(resolve("")), "")
        self.assertEqual(resolve(None).name, DEFAULT_PROFILE)

    def test_known_profiles(self):
        self.assertIn("accademico", profile_names())
        self.assertIn("narrativo", PROFILES)

    def test_unknown_profile_is_an_error(self):
        with self.assertRaises(ValueError) as ctx:
            resolve("accademicoo")
        self.assertIn("accademico", str(ctx.exception))

    def test_rule_mentions_name_and_register(self):
        rule = style_rule(resolve("scorrevole"))
        self.assertIn("scorrevole", rule)
        self.assertIn("readable", rule)

    def test_rule_number_can_be_shifted(self):
        self.assertTrue(style_rule(resolve("accademico"), number=6).startswith("\n6."))


class PromptTest(unittest.TestCase):
    def test_default_prompt_has_no_style_rule(self):
        prompt = build_translation_prompt("Italiano")
        self.assertNotIn("STYLE (", prompt)

    def test_style_is_appended(self):
        prompt = build_translation_prompt("Italiano", style="accademico")
        self.assertIn("STYLE (accademico, formale)", prompt)

    def test_numbering_follows_glossary(self):
        plain = build_translation_prompt("Italiano", style="narrativo")
        with_glossary = build_translation_prompt("Italiano", glossary=["Sprint"], style="narrativo")
        self.assertIn("\n5. STYLE", plain)
        self.assertIn("\n6. STYLE", with_glossary)

    def test_invalid_style_fails_loudly(self):
        with self.assertRaises(ValueError):
            build_translation_prompt("Italiano", style="boh")


class PartitionTest(unittest.TestCase):
    def settings(self, style):
        return TranslationSettings(provider="p", model="m", style=style)

    def test_style_is_part_of_the_cache_partition(self):
        self.assertNotEqual(
            self.settings("fedele").cache_partition(), self.settings("narrativo").cache_partition()
        )

    def test_same_style_same_partition(self):
        self.assertEqual(
            self.settings("accademico").cache_partition(), self.settings("accademico").cache_partition()
        )


if __name__ == "__main__":
    unittest.main()
