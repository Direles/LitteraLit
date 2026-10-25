"""Scarica i font del bundle (Fase 1.4).

I binari non stanno nel repository: pesano, e la licenza OFL vuole che l'attribuzione viaggi
con i file. Questo script li prende da una sorgente nota e li mette in ``assets/fonts``,
stampando percorso, byte e SHA-256 così il pin è verificabile a mano.

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

_SOURCES: dict[str, str] = {
    "Inter-Regular.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Regular.ttf",
    "Inter-Bold.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Bold.ttf",
    "Inter-Italic.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Italic.ttf",
    "Inter-BoldItalic.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-BoldItalic.ttf",
}
#: Adobe Source Serif e Google Noto arrivano dai loro repository ufficiali.
_SOURCES.update(
    {
        name: "https://github.com/adobe-fonts/source-serif/raw/release/TTF/" + name
        for styles in (BUNDLE_FAMILIES["source-serif"],)
        for name in styles.values()
    }
)
_SOURCES.update(
    {
        name: "https://github.com/notofonts/latin-greek-cyrillic/raw/main/unhinted/ttf/"
        + name.split("-")[0]
        + "/"
        + name
        for family in ("noto-serif", "noto-sans")
        for name in BUNDLE_FAMILIES[family].values()
    }
)


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
    print("Aggiungi le licenze OFL accanto ai font quando li distribuisci.")
    return 0 if not failures else 1


def _download(url: str, *, timeout: float = 60.0) -> bytes:
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
    parser.add_argument("--family", default=None, help="inter, source-serif, noto-serif, noto-sans")
    parser.add_argument("--check", action="store_true", help="elenca i file mancanti senza scaricare")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
