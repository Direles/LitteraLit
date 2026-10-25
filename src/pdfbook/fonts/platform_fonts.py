"""Registry dei font di sistema per piattaforma (M5).

Un solo posto che conosce i percorsi dei font: ``FontResolver`` chiede *quale file*
usare e non sa nulla di Windows, macOS o Linux. I test iniettano una funzione
``exists`` per non dipendere dalla macchina.

I percorsi sono **candidati**: si usa il primo che esiste davvero.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping

__all__ = [
    "SYSTEM_FONTS",
    "classify",
    "resolve_path",
    "system_font_paths",
]

Family = str  # "sans" | "sans-narrow" | "serif" | "mono"

_WIN_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_LINUX_DEJAVU = "/usr/share/fonts/truetype/dejavu"
_MAC_DIR = "/System/Library/Fonts"

# Piattaforma → famiglia → (regular, bold, italic, bold-italic); il primo esistente vince.
SYSTEM_FONTS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "windows": {
        "sans": ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
        "sans-narrow": ("ARIALN.TTF", "ARIALNB.TTF", "ARIALNI.TTF", "ARIALNBI.TTF"),
        "serif": ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
        "mono": ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf"),
    },
    "macos": {
        "sans": ("Helvetica.ttc", "Helvetica.ttc", "Helvetica.ttc", "Helvetica.ttc"),
        "sans-narrow": ("Helvetica.ttc",),
        "serif": ("Times.ttc",),
        "mono": ("Menlo.ttc",),
    },
    "linux": {
        "sans": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf", "DejaVuSans-BoldOblique.ttf"),
        "sans-narrow": ("DejaVuSansCondensed.ttf",),
        "serif": (
            "DejaVuSerif.ttf",
            "DejaVuSerif-Bold.ttf",
            "DejaVuSerif-Italic.ttf",
            "DejaVuSerif-BoldItalic.ttf",
        ),
        "mono": (
            "DejaVuSansMono.ttf",
            "DejaVuSansMono-Bold.ttf",
            "DejaVuSansMono-Oblique.ttf",
            "DejaVuSansMono-BoldOblique.ttf",
        ),
    },
}

_BASES = {"windows": _WIN_DIR, "macos": _MAC_DIR, "linux": _LINUX_DEJAVU}

_MONO_HINTS = ("typewriter", "courier", "mono", "ocr", "consol")
_SERIF_HINTS = ("minion", "times", "georgia", "garamond", "serif", "book")
_NARROW_HINTS = ("condensed", "narrow", "compressed")
_BOLD_HINTS = ("bold", "black", "heavy", "semibold", "demibold")
_ITALIC_HINTS = ("italic", "oblique")


def current_platform() -> str:
    """Piattaforma normalizzata: ``windows``, ``macos`` o ``linux``."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def classify(pdf_font_name: str) -> tuple[Family, bool, bool]:
    """Classifica un nome font PDF in ``(famiglia, bold, italic)``.

    L'ordine dei test conta: ``narrow`` prevale su ``serif`` solo se il nome non è
    già chiaramente serif (es. "MinionPro-Cond" resta serif).
    """
    name = pdf_font_name.lower()
    bold = any(hint in name for hint in _BOLD_HINTS)
    italic = any(hint in name for hint in _ITALIC_HINTS)
    if any(hint in name for hint in _MONO_HINTS):
        family: Family = "mono"
    elif any(hint in name for hint in _SERIF_HINTS):
        family = "serif"
    elif any(hint in name for hint in _NARROW_HINTS):
        family = "sans-narrow"
    else:
        family = "sans"
    return family, bold, italic


def system_font_paths(platform: str | None = None) -> Mapping[str, tuple[str, ...]]:
    """percorso assoluto candidato per famiglia, con la variante nell'ordine 0..3."""
    platform = platform or current_platform()
    base = _BASES.get(platform, _LINUX_DEJAVU)
    return {
        family: tuple(os.path.join(base, name) for name in names)
        for family, names in SYSTEM_FONTS.get(platform, SYSTEM_FONTS["linux"]).items()
    }


def resolve_path(
    family: Family,
    bold: bool = False,
    italic: bool = False,
    *,
    platform: str | None = None,
    exists: Callable[[str], bool] = os.path.exists,
) -> str | None:
    """Primo file esistente per famiglia/stile, o ``None`` se la piattaforma non ha nulla."""
    paths = system_font_paths(platform)
    candidates = paths.get(family) or paths.get("sans", ())
    index = (2 if italic else 0) + (1 if bold else 0)
    ordered = [candidates[index] if index < len(candidates) else candidates[0], *candidates]
    for path in ordered:
        if path and exists(path):
            return path
    return None
