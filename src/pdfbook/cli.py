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

    doctor = sub.add_parser("doctor", help="mostra la configurazione e verifica un report QA")
    doctor.add_argument("report", nargs="?", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "translate":
        return _translate(args)
    if args.command == "doctor":
        return _doctor(args)
    return 2


def _translate(args: argparse.Namespace) -> int:
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
    if overrides:
        settings = type(settings)(**{**settings.__dict__, **overrides})
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
    )
    logging.info("avvio job: %s", settings.redacted())
    runtime = build_runtime(spec.input_pdf, settings)
    result = TranslationJob(spec, runtime).run(progress=_progress)

    print(f"PDF: {result.output_pdf}")
    print(f"Report QA: {result.report_path}")
    print(f"Pagine: {result.pages} | blocchi: {result.blocks} | issue: {len(result.report.issues)}")
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


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _progress(current: int, total: int, message: str) -> None:
    print(f"[{current}/{total}] {message}")


if __name__ == "__main__":
    sys.exit(main())
