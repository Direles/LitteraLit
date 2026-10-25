"""Interfaccia a riga di comando (M11).

Due comandi: ``translate`` (job completo) e ``doctor`` (diagnostica di configurazione e
verifica del gate QA su un report esistente). Nessuna chiave viene mai stampata.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pdfbook import __version__
from pdfbook.app import JobSpec, TranslationJob, build_runtime
from pdfbook.app.errors import EXIT_CODES, classify, describe
from pdfbook.config.settings import LOG_LEVELS, load_settings, parse_glossary
from pdfbook.qa.report import gate, parse_report

__all__ = ["main", "build_parser", "ENV_FILE"]

# File di configurazione locale letto dalla working directory (mai committato).
ENV_FILE = ".env"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdfbook", description="Traduzione di libri PDF")
    parser.add_argument("--version", action="version", version=f"pdfbook {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    translate = sub.add_parser("translate", help="traduce un PDF")
    translate.add_argument("input")
    translate.add_argument("output")
    translate.add_argument("--provider", default=None)
    translate.add_argument("--model", default=None)
    translate.add_argument("--lang", default=None)
    translate.add_argument("--glossary", default=None, help="termini separati da virgola")
    translate.add_argument("--pages", default=None, help="es. 1-10 oppure 7")
    translate.add_argument("--cache", default=None)
    translate.add_argument("--missing-policy", choices=("skip", "keep"), default="skip")
    translate.add_argument("--overflow-policy", choices=("keep_size", "shrink"), default="keep_size")
    translate.add_argument("--log-level", choices=LOG_LEVELS, default=None)
    translate.add_argument("--workers", type=int, default=None, help="chunk tradotti in parallelo")
    translate.add_argument("--rate-limit", type=float, default=None, help="richieste al secondo")
    translate.add_argument("--max-cost", type=float, default=None, help="tetto di spesa in USD")
    translate.add_argument(
        "--resume", action="store_true", help="riprendi il lavoro interrotto (journal + cache)"
    )

    doctor = sub.add_parser("doctor", help="mostra la configurazione e verifica un report QA")
    doctor.add_argument("report", nargs="?", default=None)

    cache = sub.add_parser("cache", help="statistiche e pulizia della translation memory")
    cache.add_argument("--cache", default=None, help="percorso del file di cache")
    cache.add_argument("--prune", action="store_true", help="elimina le voci vecchie/in eccesso")
    cache.add_argument("--max-age", type=float, default=None, help="età massima in giorni")
    cache.add_argument("--max-entries", type=int, default=None, help="numero massimo di voci")

    sub.add_parser("gui", help="avvia l'interfaccia desktop")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "translate":
        return _translate(args)
    if args.command == "doctor":
        return _doctor(args)
    if args.command == "cache":
        return _cache(args)
    if args.command == "gui":
        return _gui()
    return 2


def _settings_from_args(args: argparse.Namespace):
    """Impostazioni da ambiente/`.env`, con gli argomenti della CLI come override."""
    settings = load_settings(env_file=ENV_FILE)
    overrides: dict[str, object] = {}
    if args.provider:
        overrides["provider"] = args.provider
    if args.model:
        overrides["model"] = args.model
    if args.lang:
        overrides["target_lang"] = args.lang
    if args.glossary is not None:
        overrides["glossary"] = parse_glossary(args.glossary)
    if args.cache:
        overrides["cache_path"] = Path(args.cache).expanduser()
    if args.log_level:
        overrides["log_level"] = args.log_level
    if args.workers:
        overrides["workers"] = max(int(args.workers), 1)
    if args.rate_limit is not None:
        overrides["rate_limit"] = max(float(args.rate_limit), 0.0)
    if args.max_cost is not None:
        overrides["max_cost"] = max(float(args.max_cost), 0.0)
    return type(settings)(**{**settings.__dict__, **overrides}) if overrides else settings


def _translate(args: argparse.Namespace) -> int:
    settings = _settings_from_args(args)
    _configure_logging(settings.log_level)

    missing = settings.missing_required()
    if missing:
        print("Configurazione incompleta: " + ", ".join(missing), file=sys.stderr)
        return 2

    page_start, page_end = _parse_pages(args.pages)
    spec = JobSpec(
        input_pdf=Path(args.input),
        output_pdf=Path(args.output),
        settings=settings,
        page_start=page_start,
        page_end=page_end,
        missing_policy=args.missing_policy,
        overflow_policy=args.overflow_policy,
        resume=args.resume,
    )
    logging.info("avvio job: %s", settings.redacted())
    runtime = build_runtime(spec.input_pdf, settings)
    try:
        result = TranslationJob(spec, runtime).run(progress=_progress)
    except Exception as exc:  # noqa: BLE001 - l'errore diventa un messaggio e un codice
        print(describe(exc), file=sys.stderr)
        return EXIT_CODES[classify(exc)]

    print(f"PDF: {result.output_pdf}")
    print(f"Report QA: {result.report_path}")
    print(f"Pagine: {result.pages} | blocchi: {result.blocks} | issue: {len(result.report.issues)}")
    if result.resumed_pages:
        print(f"Ripresa: {result.resumed_pages} pagine già tradotte riutilizzate dalla cache")
    tokens = result.summary.get("tokens_in", 0) + result.summary.get("tokens_out", 0)
    if tokens:
        cost = result.summary.get("cost_usd_micro", 0) / 1_000_000
        print(f"Token: {result.summary.get('tokens_in', 0)} in / {result.summary.get('tokens_out', 0)} out"
              + (f" · costo stimato: {cost:.2f} USD" if cost else ""))
    violations = result.violations()
    for violation in violations:
        print(f"GATE: {violation}")
    return 0 if not violations else 1


def _doctor(args: argparse.Namespace) -> int:
    settings = load_settings(env_file=ENV_FILE)
    print("Configurazione:")
    for key, value in settings.redacted().items():
        print(f"  {key}: {value}")
    missing = settings.missing_required()
    print("Campi obbligatori mancanti: " + (", ".join(missing) if missing else "nessuno"))
    if not args.report:
        return 0 if not missing else 2
    report = parse_report(args.report)
    violations = gate(report)
    print(f"Report: {len(report.issues)} issue | gate: {'PASS' if not violations else 'FAIL'}")
    for violation in violations:
        print(f"  {violation}")
    return 0 if not violations else 1


def _parse_pages(raw: str | None) -> tuple[int | None, int | None]:
    if not raw:
        return None, None
    if "-" in raw:
        start, _, end = raw.partition("-")
        return int(start), int(end)
    page = int(raw)
    return page, page


def _cache(args: argparse.Namespace) -> int:
    """Statistiche e potatura della translation memory: nessuna chiave viene stampata."""
    from pdfbook.translation.cache import TranslationCache

    settings = load_settings(env_file=ENV_FILE)
    path = args.cache or settings.cache_path
    cache = TranslationCache.for_maintenance(path)
    if not cache.path.exists():
        print(f"Cache assente: {path}")
        return 0
    before = cache.entries
    removed = 0
    if args.prune:
        removed = cache.prune(max_entries=args.max_entries, max_age_days=args.max_age)
    stats = cache.stats()
    print(f"Cache: {cache.path}")
    print(f"  voci: {before} -> {stats['entries']} (rimosse {removed})")
    print(f"  dimensione: {stats['bytes'] / 1024:.1f} KB")
    if not args.prune:
        print("  usa --prune --max-age 90 per liberare spazio")
    return 0


def _gui() -> int:
    """Avvia la GUI (import ritardato: ``customtkinter`` serve solo qui)."""
    from pdfbook.gui.app import main as gui_main

    gui_main()
    return 0


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _progress(current: int, total: int, message: str) -> None:
    print(f"[{current}/{total}] {message}")


if __name__ == "__main__":
    sys.exit(main())
