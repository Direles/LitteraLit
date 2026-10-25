"""Pulizia della translation memory (Fase 3.5).

La cache cresce a ogni libro tradotto e non scade mai: senza una politica diventa un file
da centinaia di MB con voci vecchie che nessuno riuserà. Qui la logica **pura** di potatura,
separata da I/O e dal lock di ``TranslationCache``:

* ``max_age_days``: elimina le voci più vecchie del limite (per data di scrittura);
* ``max_entries``: se resta troppa roba, tiene le più recenti;
* le voci legacy senza data non vengono buttate per età (non si conosce), ma sono le prime
  a cadere quando serve spazio.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = ["Entry", "normalise", "prune"]

_SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class Entry:
    """Una voce della cache: traduzione + istante di scrittura (0 = sconosciuto)."""

    value: str
    stamp: int = 0


def normalise(raw: Any) -> Entry | None:
    """Accetta il formato corrente ``{"v":…, "t":…}`` e quello legacy (stringa)."""
    if isinstance(raw, str):
        return Entry(raw, 0)
    if isinstance(raw, Mapping):
        value = raw.get("v")
        if not isinstance(value, str):
            return None
        stamp = raw.get("t", 0)
        return Entry(value, int(stamp) if isinstance(stamp, (int, float)) else 0)
    return None


def prune(
    entries: Mapping[str, Any],
    *,
    max_entries: int | None = None,
    max_age_days: float | None = None,
    now: float | None = None,
) -> tuple[dict[str, dict[str, Any]], int]:
    """Restituisce ``(voci_tenute, quante_rimosse)`` applicando età e tetto dimensione."""
    current = time.time() if now is None else now
    kept: dict[str, Entry] = {}
    removed = 0
    for key, raw in entries.items():
        entry = normalise(raw)
        if entry is None:
            removed += 1
            continue
        if max_age_days is not None and entry.stamp and _age_days(entry.stamp, current) > max_age_days:
            removed += 1
            continue
        kept[key] = entry
    if max_entries is not None and len(kept) > max(0, max_entries):
        ordered = sorted(kept.items(), key=lambda item: item[1].stamp, reverse=True)
        survivors = ordered[: max(0, max_entries)]
        removed += len(kept) - len(survivors)
        kept = dict(survivors)
    return {key: {"v": entry.value, "t": entry.stamp} for key, entry in kept.items()}, removed


def _age_days(stamp: int, now: float) -> float:
    return max(0.0, (now - stamp) / _SECONDS_PER_DAY)
