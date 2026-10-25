"""Contabilità di token e costo per la run (Fase 3.3).

Tiene traccia di quanto si sta spendendo e applica il tetto configurato. Il costo è una
**stima** basata su una tabella indicativa (``config/pricing.py``): serve a evitare
sorprese, non a fare fatturazione.
"""

from __future__ import annotations

from pdfbook.config.pricing import estimate_cost

from .errors import UsageError

__all__ = ["account_costs"]


def account_costs(
    *,
    model: str,
    tokens_in: int,
    tokens_out: int,
    counters: dict[str, int],
    max_cost: float = 0.0,
) -> float | None:
    """Aggiorna i contatori con token e costo; solleva ``UsageError`` oltre il tetto."""
    counters["tokens_in"] = tokens_in
    counters["tokens_out"] = tokens_out
    cost = estimate_cost(model, tokens_in, tokens_out)
    if cost is None:
        return None
    counters["cost_usd_micro"] = int(round(cost * 1_000_000))
    if max_cost > 0 and cost > max_cost:
        raise UsageError(
            f"tetto di spesa superato: {cost:.2f} USD > {max_cost:.2f} USD. "
            "Rilancia con --resume dopo aver alzato --max-cost o ridotto l'intervallo."
        )
    return cost
