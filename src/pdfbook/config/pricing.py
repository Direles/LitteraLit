"""Prezzi indicativi dei modelli, per stimare il costo di una run (Fase 3.3).

Valori in **USD per milione di token** (input, output). Sono ordini di grandezza, non
tariffe contrattuali: servono a evitare sorprese, non a fare fatturazione. Aggiornarli è
un'operazione di configurazione, non di codice.
"""

from __future__ import annotations

__all__ = ["PRICES", "estimate_cost", "price_for"]

# (input, output) in USD / 1M token
PRICES: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def price_for(model: str) -> tuple[float, float] | None:
    """Prezzo ``(input, output)`` del modello, con match per prefisso; ``None`` se ignoto."""
    name = (model or "").strip().lower()
    if not name:
        return None
    if name in PRICES:
        return PRICES[name]
    for known, price in PRICES.items():
        if name.startswith(known):
            return price
    return None


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    """Costo stimato in USD, oppure ``None`` se il modello non è in tabella."""
    price = price_for(model)
    if price is None:
        return None
    input_price, output_price = price
    return (max(tokens_in, 0) * input_price + max(tokens_out, 0) * output_price) / 1_000_000
