"""Test della potatura della cache (Fase 3.5)."""

import json
import tempfile
import time
import unittest
from pathlib import Path

from pdfbook.translation.cache import TranslationCache, make_key
from pdfbook.translation.cache_prune import normalise, prune

DAY = 86_400


class NormaliseTest(unittest.TestCase):
    def test_current_format(self):
        entry = normalise({"v": "ciao", "t": 100})
        self.assertEqual((entry.value, entry.stamp), ("ciao", 100))

    def test_legacy_string_has_no_stamp(self):
        entry = normalise("ciao")
        self.assertEqual((entry.value, entry.stamp), ("ciao", 0))

    def test_garbage_is_rejected(self):
        self.assertIsNone(normalise(42))
        self.assertIsNone(normalise({"t": 1}))


class PruneTest(unittest.TestCase):
    def entries(self):
        now = 10 * DAY
        return {
            "a": {"v": "vecchia", "t": int(now - 40 * DAY)},
            "b": {"v": "recente", "t": int(now - 1 * DAY)},
            "c": "legacy",
            "d": {"v": "rotta"},
        }

    def test_age_removes_only_old_entries(self):
        kept, removed = prune(self.entries(), max_age_days=30, now=10 * DAY)
        self.assertEqual(removed, 1)  # solo "vecchia" ha una data oltre il limite
        self.assertEqual(set(kept), {"b", "c", "d"})

    def test_legacy_entries_survive_age_prune(self):
        kept, _ = prune(self.entries(), max_age_days=1, now=10 * DAY)
        self.assertIn("c", kept)

    def test_max_entries_keeps_newest(self):
        kept, removed = prune(self.entries(), max_entries=2, now=10 * DAY)
        self.assertEqual(removed, 2)
        self.assertIn("b", kept)

    def test_legacy_entries_are_evicted_first(self):
        kept, _ = prune(self.entries(), max_entries=1, now=10 * DAY)
        self.assertEqual(set(kept), {"b"})

    def test_nothing_to_do(self):
        kept, removed = prune({"a": {"v": "x", "t": 5}}, now=10 * DAY)
        self.assertEqual((kept, removed), ({"a": {"v": "x", "t": 5}}, 0))


class CachePruneTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "cache.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_old_entries_are_removed_from_disk(self):
        key = make_key("uno", "p")
        old = int(time.time() - 40 * DAY)
        self.path.write_text(json.dumps({key: {"v": "one", "t": old}}), encoding="utf-8")
        maintenance = TranslationCache.for_maintenance(self.path)
        self.assertEqual(maintenance.prune(max_age_days=30), 1)
        self.assertEqual(maintenance.entries, 0)

    def test_legacy_file_stays_readable(self):
        key = make_key("uno", "p")
        self.path.write_text(json.dumps({key: "one"}), encoding="utf-8")
        cache = TranslationCache(self.path, "p")
        self.assertEqual(cache.get("uno"), "one")

    def test_prune_rewrites_in_current_format(self):
        key = make_key("uno", "p")
        self.path.write_text(json.dumps({key: "one"}), encoding="utf-8")
        cache = TranslationCache.for_maintenance(self.path)
        cache.prune()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw[key], {"v": "one", "t": 0})

    def test_stats_report_size(self):
        cache = TranslationCache(self.path, "p")
        cache.put("uno", "one")
        cache.save()
        stats = cache.stats()
        self.assertEqual(stats["entries"], 1)
        self.assertGreater(stats["bytes"], 0)


if __name__ == "__main__":
    unittest.main()
