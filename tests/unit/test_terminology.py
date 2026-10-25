"""Test della memoria terminologica (Fase 5.3)."""

import unittest

from pdfbook.translation.terminology import Terminology, candidates, glossary_lines


class CandidateTest(unittest.TestCase):
    def test_repeated_proper_noun_is_proposed(self):
        terms = candidates(["Kent Beck ha scritto il libro."] * 4)
        self.assertIn("Kent Beck", [term.text for term in terms])

    def test_single_occurrence_is_ignored(self):
        terms = candidates(["Kent Beck ha scritto il libro."])
        self.assertEqual(terms, [])

    def test_sentence_start_is_not_a_proper_noun(self):
        terms = candidates(["The story begins here.", "The story ends here.", "The story again."])
        self.assertNotIn("The", [term.text for term in terms])

    def test_acronyms_are_proposed(self):
        terms = candidates(["Usiamo MVP e Sprint.", "MVP e Sprint ancora.", "MVP sempre."])
        texts = [term.text for term in terms]
        self.assertIn("MVP", texts)

    def test_technical_word_with_inner_capital_is_proposed(self):
        terms = candidates(["JavaScript ovunque."] * 3)
        self.assertIn("JavaScript", [term.text for term in terms])

    def test_pages_are_counted(self):
        memory = Terminology(min_occurrences=2)
        memory.observe(1, ["Kent Beck scrive."])
        memory.observe(2, ["Kent Beck corregge."])
        term = memory.candidates()[0]
        self.assertEqual((term.text, term.pages, term.occurrences), ("Kent Beck", 2, 2))

    def test_limit_is_respected(self):
        memory = Terminology(min_occurrences=1)
        for index in range(10):
            memory.observe(1, [f"Il termine Termine{index} qui."])
        self.assertEqual(len(memory.candidates(limit=3)), 3)

    def test_ordering_prefers_frequency_then_pages(self):
        memory = Terminology(min_occurrences=1)
        memory.observe(1, ["Alpha Beta."])
        memory.observe(2, ["Alpha Beta."])
        memory.observe(3, ["Gamma Delta."])
        self.assertEqual(memory.candidates()[0].text, "Alpha Beta")


class GlossaryTest(unittest.TestCase):
    def test_lines_are_plain_text(self):
        memory = Terminology(min_occurrences=2)
        memory.observe(1, ["Kent Beck scrive."])
        memory.observe(2, ["Kent Beck corregge."])
        self.assertEqual(memory.glossary_lines(), ["Kent Beck"])

    def test_glossary_lines_from_mapping_filters_rare_terms(self):
        lines = glossary_lines({"Kent Beck": 5, "Raro": 1})
        self.assertEqual(lines, ["Kent Beck"])


if __name__ == "__main__":
    unittest.main()
