"""Colori: dall'intero RGB di PyMuPDF alla tupla 0..1 usata dal rendering."""

from __future__ import annotations

__all__ = ["rgb_from_int", "rgb_to_hex"]


def rgb_from_int(color: int | None) -> tuple[float, float, float]:
    """Intero 0xRRGGBB → ``(r, g, b)`` in 0..1; ``None`` diventa nero."""
    if not color:
        return (0.0, 0.0, 0.0)
    return (
        ((color >> 16) & 0xFF) / 255.0,
        ((color >> 8) & 0xFF) / 255.0,
        (color & 0xFF) / 255.0,
    )


def rgb_to_hex(color: tuple[float, float, float]) -> str:
    """Tupla 0..1 → ``#rrggbb`` (utile nei log e nei report)."""
    red, green, blue = (max(0, min(255, round(channel * 255))) for channel in color)
    return f"#{red:02x}{green:02x}{blue:02x}"
