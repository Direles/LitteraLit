"""Test della classificazione errori (Fase 3.4)."""

import unittest

from pdfbook.app.errors import EXIT_CODES, classify, describe
from pdfbook.translation.json_repair import JsonRepairError
from pdfbook.translation.providers.base import ProviderError


class ClassifyTest(unittest.TestCase):
    def test_configuration_errors(self):
        self.assertEqual(classify(ValueError("x")), "config")

    def test_missing_file(self):
        self.assertEqual(classify(FileNotFoundError("x")), "input")

    def test_provider_and_parsing(self):
        self.assertEqual(classify(ProviderError("429")), "provider")
        self.assertEqual(classify(JsonRepairError("rotto", "raw")), "provider")

    def test_unknown_is_layout(self):
        self.assertEqual(classify(KeyError("x")), "layout")

    def test_exit_codes_are_stable(self):
        self.assertEqual(
            EXIT_CODES,
            {
                "ok": 0,
                "gate": 1,
                "config": 2,
                "input": 3,
                "provider": 4,
                "layout": 5,
                "cancelled": 130,
            },
        )

    def test_cancelled_is_its_own_category(self):
        from pdfbook.app.errors import Cancelled, classify, describe

        self.assertEqual(classify(Cancelled("basta")), "cancelled")
        self.assertIn("--resume", describe(Cancelled("basta")))


class DescribeTest(unittest.TestCase):
    def test_messages_explain_the_remedy(self):
        self.assertIn(".env", describe(ValueError("provider vuoto")))
        self.assertIn("percorso", describe(FileNotFoundError("in.pdf")))
        self.assertIn("chiave", describe(ProviderError("401 unauthorized")))

    def test_detail_is_preserved(self):
        self.assertIn("429", describe(ProviderError("429 too many requests")))

    def test_fallback_message(self):
        self.assertTrue(describe(RuntimeError("boom")).startswith("Errore durante l'elaborazione"))


if __name__ == "__main__":
    unittest.main()
