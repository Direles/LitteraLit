"""Test della translation memory (M3): chiave composta, atomicità, thread-safety."""

import json
import tempfile
import threading
import unittest
from pathlib import Path

from pdfbook.domain.models import TranslationSettings
from pdfbook.translation.cache import CACHE_VERSION, TranslationCache, make_key


class KeyTest(unittest.TestCase):
    def test_partition_is_mandatory(self):
        with self.assertRaises(ValueError):
            make_key("testo", "")

    def test_key_depends_on_partition(self):
        a = make_key("testo", "part-a")
        b = make_key("testo", "part-b")
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_key_is_stable_and_whitespace_insensitive(self):
        self.assertEqual(make_key("  ciao  ", "p"), make_key("ciao", "p"))

    def test_version_is_part_of_the_contract(self):
        self.assertGreaterEqual(CACHE_VERSION, 2)


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "cache.json"
        self.cache = TranslationCache(self.path, "part", autosave_every=0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_put_get_and_stats(self):
        self.assertIsNone(self.cache.get("ciao"))
        self.cache.put("ciao", "hello")
        self.assertEqual(self.cache.get("ciao"), "hello")
        self.assertEqual(self.cache.stats(), {"entries": 1, "hits": 1, "misses": 1})

    def test_contains(self):
        self.cache.put("ciao", "hello")
        self.assertTrue(self.cache.contains("ciao"))
        self.assertFalse(self.cache.contains("altro"))

    def test_put_many_skips_blanks_and_counts_new(self):
        added = self.cache.put_many({"a": "x", "  ": "y", "b": "z"})
        self.assertEqual(added, 2)
        self.assertEqual(self.cache.entries, 2)

    def test_put_many_is_idempotent(self):
        self.cache.put_many({"a": "x"})
        self.assertEqual(self.cache.put_many({"a": "x"}), 0)

    def test_persistence_roundtrip(self):
        self.cache.put("ciao", "hello")
        self.assertTrue(self.cache.save())
        again = TranslationCache(self.path, "part", autosave_every=0)
        self.assertEqual(again.get("ciao"), "hello")

    def test_atomic_save_leaves_no_tmp_file(self):
        self.cache.put("ciao", "hello")
        self.cache.save()
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["cache.json"])

    def test_autosave_triggers_after_threshold(self):
        cache = TranslationCache(self.path, "part", autosave_every=2)
        cache.put("a", "1")
        self.assertFalse(self.path.exists())
        cache.put("b", "2")
        self.assertTrue(self.path.exists())

    def test_dirty_flag(self):
        self.assertFalse(self.cache.dirty)
        self.cache.put("a", "1")
        self.assertTrue(self.cache.dirty)
        self.cache.save()
        self.assertFalse(self.cache.dirty)

    def test_corrupted_file_does_not_block(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{non json", encoding="utf-8")
        cache = TranslationCache(self.path, "part", autosave_every=0)
        self.assertEqual(cache.entries, 0)
        cache.put("a", "1")
        self.assertEqual(cache.get("a"), "1")

    def test_file_with_non_string_values_is_sanitized(self):
        self.path.write_text(json.dumps({"k": 1, "v": "ok"}), encoding="utf-8")
        cache = TranslationCache(self.path, "part", autosave_every=0)
        self.assertEqual(cache.entries, 1)


class PartitionIsolationTest(unittest.TestCase):
    def test_settings_create_isolated_caches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            italian = TranslationCache.for_settings(
                path, TranslationSettings(provider="DeepSeek", model="m"), autosave_every=0
            )
            english = TranslationCache.for_settings(
                path, TranslationSettings(provider="DeepSeek", model="m", target_lang="Inglese"),
                autosave_every=0,
            )
            italian.put("ciao", "hello")
            italian.save()
            self.assertEqual(english.get("ciao"), None)

    def test_glossary_changes_partition(self):
        base = TranslationSettings(provider="p", model="m")
        with_terms = base.with_glossary(["Sprint"])
        self.assertNotEqual(base.cache_partition(), with_terms.cache_partition())


class ThreadSafetyTest(unittest.TestCase):
    def test_concurrent_puts_do_not_lose_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = TranslationCache(Path(tmp) / "cache.json", "part", autosave_every=0)
            errors: list[Exception] = []

            def worker(offset: int) -> None:
                try:
                    for index in range(20):
                        cache.put(f"t{offset}-{index}", f"v{offset}-{index}")
                except Exception as exc:  # pragma: no cover - solo diagnosi
                    errors.append(exc)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            self.assertEqual(cache.entries, 160)
            self.assertTrue(cache.save())


if __name__ == "__main__":
    unittest.main()
