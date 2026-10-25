"""Limite di frequenza per provider (Fase 3.2).

Un token-bucket minimale: garantisce un intervallo minimo fra due chiamate, condiviso fra
i thread che traducono chunk diversi. Meglio rallentare che collezionare 429.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

__all__ = ["RateLimiter"]


class RateLimiter:
    """Intervallo minimo fra due chiamate, thread-safe."""

    def __init__(self, min_interval: float, *, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if min_interval < 0:
            raise ValueError("min_interval non può essere negativo")
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None
        self._lock = threading.Lock()

    @classmethod
    def from_rate(cls, requests_per_second: float, **kwargs) -> RateLimiter:
        """Costruisce il limiter da richieste al secondo (0 = nessun limite)."""
        if requests_per_second <= 0:
            return cls(0.0, **kwargs)
        return cls(1.0 / requests_per_second, **kwargs)

    def wait(self) -> None:
        """Blocca finché non è trascorso l'intervallo minimo dall'ultima chiamata."""
        if self.min_interval <= 0:
            return
        with self._lock:
            now = self._clock()
            if self._last is not None:
                delay = self.min_interval - (now - self._last)
                if delay > 0:
                    self._sleep(delay)
                    now = self._clock()
            self._last = now
