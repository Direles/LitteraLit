"""Test del logging su file con rotazione (Fase 3.6)."""

import logging
import tempfile
import unittest
from pathlib import Path

from pdfbook.config.logging import LOG_FORMAT, configure, default_log_path, shutdown


class ConfigureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        shutdown()
        self.tmp.cleanup()

    def test_writes_to_file(self):
        path = configure("INFO", log_file=self.root / "sub" / "run.log", console=False)
        self.assertEqual(path, self.root / "sub" / "run.log")
        logging.getLogger("pdfbook.test").info("ciao")
        logging.shutdown()
        content = path.read_text(encoding="utf-8")
        self.assertIn("pdfbook.test: ciao", content)
        self.assertIn("INFO", content)

    def test_creates_parent_directories(self):
        path = configure("DEBUG", log_file=self.root / "a" / "b" / "run.log", console=False)
        self.assertTrue(path.parent.is_dir())

    def test_configure_is_idempotent(self):
        configure("INFO", log_file=self.root / "run.log", console=False)
        configure("INFO", log_file=self.root / "run.log", console=False)
        marked = [h for h in logging.getLogger().handlers if getattr(h, "_pdfbook_handler", False)]
        self.assertEqual(len(marked), 1)

    def test_rotation_creates_backup(self):
        path = configure(
            "INFO", log_file=self.root / "run.log", console=False, max_bytes=200, backups=2
        )
        logger = logging.getLogger("pdfbook.rotate")
        for index in range(80):
            logger.info("riga numero %s con un po di testo per superare il limite", index)
        for handler in logging.getLogger().handlers:
            handler.flush()
        self.assertTrue(path.exists())
        backups = list(self.root.glob("run.log.*"))
        self.assertTrue(backups, "atteso almeno un file ruotato")

    def test_unwritable_path_does_not_raise(self):
        target = self.root / "file_non_dir"
        target.write_text("x", encoding="utf-8")
        path = configure("INFO", log_file=target / "run.log", console=False)
        self.assertIsNone(path)

    def test_console_handler_can_be_disabled(self):
        configure("INFO", log_file=self.root / "run.log", console=False)
        console = [
            h
            for h in logging.getLogger().handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        self.assertEqual(console, [])

    def test_format_contains_level_and_logger(self):
        self.assertIn("%(levelname)", LOG_FORMAT)
        self.assertIn("%(name)s", LOG_FORMAT)


class DefaultPathTest(unittest.TestCase):
    def test_env_override(self):
        import os

        os.environ["PDFBOOK_LOG_FILE"] = "C:/tmp/custom.log" if os.name == "nt" else "/tmp/custom.log"
        try:
            self.assertEqual(default_log_path().name, "custom.log")
        finally:
            os.environ.pop("PDFBOOK_LOG_FILE", None)

    def test_default_ends_with_log_file(self):
        self.assertTrue(str(default_log_path()).endswith("pdfbook.log"))


class ShutdownTest(unittest.TestCase):
    def test_handlers_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            configure("INFO", log_file=Path(tmp) / "run.log", console=False)
            shutdown()
            marked = [h for h in logging.getLogger().handlers if getattr(h, "_pdfbook_handler", False)]
            self.assertEqual(marked, [])


if __name__ == "__main__":
    unittest.main()
