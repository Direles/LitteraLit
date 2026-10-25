"""Scarica i font del bundle (Fase 1.4).

I binari non stanno nel repository: pesano, e la licenza OFL vuole che l'attribuzione viaggi
con i file. Questo script li prende da sorgenti note (Google Fonts, Adobe) e li mette in
``assets/fonts``, stampando percorso, byte e SHA-256 così il pin è verificabile a mano.

    py tools/fetch_fonts.py                 # tutte le famiglie mancanti
    py tools/fetch_fonts.py --family inter  # solo una
    py tools/fetch_fonts.py --check         # verifica cosa manca, senza scaricare

Nessuna dipendenza: ``urllib`` della standard library. Se la rete non c'è, lo script lo dice
e la cascata dei font continua a funzionare con i font di sistema.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdfbook.fonts.bundled import BUNDLE_FAMILIES, BundledFonts, default_bundle_root  # noqa: E402

_GOOGLE = "https://github.com/google/fonts/raw/main/ofl/"
_SOURCES: dict[str, str] = {
    # Adobe Source Serif 4: quattro stili statici (serif da testo, peso corretto).
    "SourceSerif4-Regular.ttf": "https://github.com/adobe-fonts/source-serif/raw/release/TTF/SourceSerif4-Regular.ttf",
    "SourceSerif4-Bold.ttf": "https://github.com/adobe-fonts/source-serif/raw/release/TTF/SourceSerif4-Bold.ttf",
    "SourceSerif4-It.ttf": "https://github.com/adobe-fonts/source-serif/raw/release/TTF/SourceSerif4-It.ttf",
    "SourceSerif4-BoldIt.ttf": "https://github.com/adobe-fonts/source-serif/raw/release/TTF/SourceSerif4-BoldIt.ttf",
    # Inter: upstream distribuisce solo il variabile (una istanza: usata per il regular).
    "InterVariable.ttf": _GOOGLE + "inter/Inter%5Bopsz%2Cwght%5D.ttf",
    # Noto variabili: copertura ampia (latino, greco, cirillico), una sola istanza.
    "NotoSerif-Variable.ttf": _GOOGLE + "notoserif/NotoSerif%5Bwdth%2Cwght%5D.ttf",
    "NotoSans-Variable.ttf": _GOOGLE + "notosans/NotoSans%5Bwdth%2Cwght%5D.ttf",
    # RTL: arabo (istanza Regular del variabile). L'ebraico resta ai font di sistema.
    "NotoNaskhArabic-Variable.ttf": _GOOGLE + "notonaskharabic/NotoNaskhArabic%5Bwght%5D.ttf",
}

#: Famiglie troppo grandi per il bundle: si usano i font di sistema o un'installazione manuale.
_SKIP_NOTE = {
    "noto-cjk": "Noto Serif CJK pesa ~25 MB per lingua: installalo dal sistema se ti serve il cinese.",
}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.dest) if args.dest else default_bundle_root()
    wanted = _wanted(args.family)
    if not wanted:
        print(f"Famiglia sconosciuta: {args.family} (disponibili: {', '.join(BUNDLE_FAMILIES)})")
        return 2
    root.mkdir(parents=True, exist_ok=True)
    missing = [name for name in wanted if not (root / name).is_file()]
    if args.check:
        print(f"Cartella: {root}")
        print("Mancanti: " + (", ".join(missing) if missing else "nessuno"))
        return 0 if not missing else 1
    failures = 0
    for name in missing:
        url = _SOURCES.get(name)
        if url is None:
            print(f"  {name}: nessuna sorgente nota")
            failures += 1
            continue
        try:
            payload = _download(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  {name}: download fallito ({exc})")
            failures += 1
            continue
        (root / name).write_bytes(payload)
        print(f"  {name}: {len(payload)} byte  sha256={hashlib.sha256(payload).hexdigest()[:16]}…")
    bundle = BundledFonts.discover(root)
    print(f"Famiglie disponibili: {', '.join(bundle.available()) or 'nessuna'}")
    for note in _SKIP_NOTE.values():
        print(f"Nota: {note}")
    if failures:
        print(f"{failures} file non scaricati: controlla la rete o aggiorna le URL.")
    print("Aggiungi le licenze OFL accanto ai font quando li distribuisci.")
    return 0 if not failures else 1


def _download(url: str, *, timeout: float = 120.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "LitteraLit-font-fetch"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL noti
        return response.read()


def _wanted(family: str | None) -> list[str]:
    families = [family] if family else list(BUNDLE_FAMILIES)
    names: list[str] = []
    for key in families:
        names.extend(BUNDLE_FAMILIES.get(key, {}).values())
    return names


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fetch_fonts", description="Scarica i font del bundle")
    parser.add_argument("--dest", default=None, help="cartella di destinazione (default assets/fonts)")
    parser.add_argument("--family", default=None, help=", ".join(BUNDLE_FAMILIES))
    parser.add_argument("--check", action="store_true", help="elenca i file mancanti senza scaricare")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
