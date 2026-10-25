"""Rende importabile ``src/`` anche quando la discovery parte da ``tests/``.

Duplica intenzionalmente le due righe di ``tests/__init__.py``: unittest può
importare questo package come top-level (``-s tests``) oppure come
``tests.unit`` (``-t .``) e in entrambi i casi il path deve essere pronto.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
