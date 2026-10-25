"""Test del journal di avanzamento (Fase 3.1)."""

import json
import tempfile
import unittest
from pathlib import Path

from pdfbook.app.journal import (
    JOURNAL_SUFFIX,
    Journal,
    journal_path,
    load_journal,
    remove_journal,
    save_journal,
)


class PathTest(unittest.TestCase):
    def test_journal_sits_next_to_the_output(self):
        self.assertEqual(journal_path("libri/out.pdf").name, "out.pdf.job.json")

    def test_suffix_is_declared(self):
        self.assertTrue(JOURNAL_SUFFIX.endswith(".json"))


class RoundtripTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "out.pdf"

    def tearDown(self):
        self.tmp.cleanup()

    def journal(self, **overrides):
        base = {
            "input_pdf": "in.pdf",
            "output_pdf": str(self.out),
            "fingerprint": "abc123",
            "pages_total": 10,
            "pages_done": 4,
        }
        base.update(overrides)
        return Journal(**base)

    def test_save_and_load(self):
        save_journal(self.journal())
        loaded = load_journal(self.out)
        self.assertIsNotNone(loaded)
        self.assertEqual((loaded.pages_done, loaded.pages_total), (4, 10))
        self.assertEqual(loaded.fingerprint, "abc123")

    def test_progress_ratio(self):
        self.assertAlmostEqual(self.journal().progress, 0.4)

    def test_missing_journal(self):
        self.assertIsNone(load_journal(self.out))

    def test_corrupted_journal_is_ignored(self):
        journal_path(self.out).write_text("{non json", encoding="utf-8")
        self.assertIsNone(load_journal(self.out))

    def test_unknown_version_is_ignored(self):
        path = journal_path(self.out)
        path.write_text(json.dumps({"version": 99, "pages_total": 1}), encoding="utf-8")
        self.assertIsNone(load_journal(self.out))

    def test_incomplete_journal_is_ignored(self):
        path = journal_path(self.out)
        path.write_text(json.dumps({"version": 1}), encoding="utf-8")
        self.assertIsNone(load_journal(self.out))

    def test_remove_journal(self):
        save_journal(self.journal())
        remove_journal(self.out)
        self.assertFalse(journal_path(self.out).exists())

    def test_remove_missing_journal_is_safe(self):
        remove_journal(self.out)

    def test_save_is_atomic(self):
        save_journal(self.journal())
        leftovers = [p.name for p in self.out.parent.iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
