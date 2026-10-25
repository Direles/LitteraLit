"""Test di integrazione: pipeline completa su PDF sintetici.

Rende importabili sia ``src/`` sia la cartella ``tests/`` (per i doppi condivisi) in
entrambe le modalità di esecuzione: ``discover -s tests`` e ``unittest tests.integration…``.
"""

import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
for candidate in (TESTS, TESTS.parent / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
