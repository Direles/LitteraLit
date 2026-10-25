"""Font bundle del progetto (Fase 1.4).

Un libro tradotto con font arbitrari di sistema cambia metrica da macchina a macchina: le
righe si adattano diversamente, i test golden non sono riproducibili e il PDF esce diverso
per ogni utente. Il bundle è un insieme **piccolo e dichiarato** di famiglie OFL, con ruoli
stabili:

| Famiglia | Ruolo |
|---|---|
| Inter | sans-serif moderno (equivalente di Helvetica/Franklin) |
| Source Serif | serif da testo (equivalente di Minion/Times) |
| Noto Serif / Noto Sans | copertura ampia (cirillico, greco, simboli) |

I binari **non sono nel repository** (licenza OFL sì, peso no): si scaricano una volta con
``python tools/fetch_fonts.py``. Questo modulo è solo il registro e la ricerca su disco: se il
bundle non c'è, la cascata dei font funziona come prima.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "BUNDLE_FAMILIES",
    "BUNDLED_PRIORITY",
    "BundledFonts",
    "bundle_family_for",
    "default_bundle_root",
]

#: Famiglie del bundle: nome logico → file per stile.
#: Solo file con **istanza statica o variabile "Regular"**: un grassetto non viene mai
#: sostituito con il regular (il resolver chiede lo stile esatto), quindi non si degrada il peso.
#: L'ebraico resta fuori: i Noto variabili espongono l'istanza Thin, peggio del font di sistema.
BUNDLE_FAMILIES: dict[str, dict[tuple[bool, bool], str]] = {
    "source-serif": {
        (False, False): "SourceSerif4-Regular.ttf",
        (True, False): "SourceSerif4-Bold.ttf",
        (False, True): "SourceSerif4-It.ttf",
        (True, True): "SourceSerif4-BoldIt.ttf",
    },
    "inter": {
        (False, False): "InterVariable.ttf",
    },
    "noto-serif": {
        (False, False): "NotoSerif-Variable.ttf",
    },
    "noto-sans": {
        (False, False): "NotoSans-Variable.ttf",
    },
    "noto-arabic": {
        (False, False): "NotoNaskhArabic-Variable.ttf",
    },
}

#: Da nome font PDF (normalizzato) alla famiglia del bundle, in ordine di preferenza.
BUNDLED_PRIORITY: tuple[tuple[tuple[str, ...], str], ...] = (
    (("inter", "roboto", "opensans", "lato", "arial", "helvetica", "franklin", "verdana"), "inter"),
    (
        (
            "sourceserif",
            "minion",
            "times",
            "georgia",
            "garamond",
            "caslon",
            "palatino",
            "baskerville",
            "cambria",
            "charter",
        ),
        "source-serif",
    ),
    (("notoserif",), "noto-serif"),
    (("notosans", "dejavu"), "noto-sans"),
    (("naskh", "arabic"), "noto-arabic"),
)


def default_bundle_root() -> Path:
    """Cartella ``assets/fonts`` accanto al repository (o ``PDFBOOK_FONT_DIR``)."""
    override = os.environ.get("PDFBOOK_FONT_DIR", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "assets" / "fonts"


@dataclass(frozen=True)
class BundledFonts:
    """Registro su disco: quali famiglie ci sono davvero e dove."""

    root: Path
    files: dict[str, dict[tuple[bool, bool], Path]]

    @classmethod
    def discover(cls, root: str | os.PathLike[str] | None = None) -> BundledFonts:
        base = Path(root) if root is not None else default_bundle_root()
        files: dict[str, dict[tuple[bool, bool], Path]] = {}
        for family, styles in BUNDLE_FAMILIES.items():
            found: dict[tuple[bool, bool], Path] = {}
            for style, filename in styles.items():
                candidate = base / filename
                if candidate.is_file():
                    found[style] = candidate
            if found:
                files[family] = found
        return cls(root=base, files=files)

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(self.files))

    def has(self, family: str) -> bool:
        return family in self.files

    def path_for(self, family: str, bold: bool, italic: bool) -> str | None:
        """Percorso dello stile richiesto, con ripiego su regular della stessa famiglia."""
        styles = self.files.get(family)
        if not styles:
            return None
        for key in ((bold, italic), (bold, False), (False, italic), (False, False)):
            path = styles.get(key)
            if path is not None:
                return str(path)
        return None

    def exact_path_for(self, family: str, bold: bool, italic: bool) -> str | None:
        """Solo lo stile esatto: evita di rendere un grassetto con il regular."""
        path = self.files.get(family, {}).get((bold, italic))
        return str(path) if path is not None else None

    def families_for(self, pdf_font_name: str) -> Iterable[str]:
        """Famiglie del bundle compatibili con un nome font del PDF, in ordine di preferenza."""
        normalized = _normalize_name(pdf_font_name)
        for needles, family in BUNDLED_PRIORITY:
            if self.has(family) and any(needle in normalized for needle in needles):
                yield family


def bundle_family_for(pdf_font_name: str, fonts: BundledFonts) -> str | None:
    """Prima famiglia del bundle compatibile, o ``None``."""
    return next(iter(fonts.families_for(pdf_font_name)), None)


def _normalize_name(name: str) -> str:
    return "".join(char for char in name.lower().split("+")[-1] if char.isalnum())
