"""OCR con ocrmypdf + Tesseract (Fase 4.2).

Il modo più economico per rendere traducibile una scansione: farle aggiungere uno **strato
di testo invisibile** da ocrmypdf, poi usare la pipeline esistente senza modifiche. Nessun
modello da addestrare, nessuna GPU, e il PDF originale non viene toccato (si lavora su una
copia temporanea).

Il modulo non importa ``ocrmypdf``: lo esegue come processo. Così i test girano senza
binari installati e l'errore, se manca, è un messaggio che dice cosa installare.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pdfbook.extraction.fitz_source import PdfPageSource
from pdfbook.extraction.scan_detect import has_text

__all__ = [
    "OcrConfig",
    "OcrError",
    "OcrSource",
    "SubprocessRunner",
    "ocrmypdf_command",
]

log = logging.getLogger(__name__)

#: Quante pagine guardare per decidere se il documento è una scansione.
SAMPLE_PAGES = 6


class OcrError(RuntimeError):
    """OCR richiesto ma non eseguibile (binario assente, uscita non valida)."""


@dataclass(frozen=True)
class OcrConfig:
    """Parametri passati a ocrmypdf (pochi e motivati)."""

    language: str = "ita+eng"
    jobs: int = 0
    deskew: bool = True
    rotate_pages: bool = True
    skip_text: bool = True
    optimize: int = 1


def ocrmypdf_command(
    input_pdf: str | Path, output_pdf: str | Path, config: OcrConfig | None = None
) -> list[str]:
    """Argomenti di ocrmypdf per la copia OCR di un PDF."""
    config = config or OcrConfig()
    argv = ["ocrmypdf", "--language", config.language]
    if config.jobs:
        argv += ["--jobs", str(config.jobs)]
    if config.deskew:
        argv.append("--deskew")
    if config.rotate_pages:
        argv.append("--rotate-pages")
    if config.skip_text:
        argv.append("--skip-text")
    argv += ["--optimize", str(config.optimize), str(input_pdf), str(output_pdf)]
    return argv


class SubprocessRunner:
    """Esecutore reale: ``subprocess.run`` con errori tradotti in ``OcrError``."""

    def __init__(self, timeout: float = 3_600.0) -> None:
        self.timeout = timeout

    def run(self, argv: Sequence[str]) -> None:
        try:
            completed = subprocess.run(  # noqa: S603 - argv costruito qui, nessuna shell
                list(argv), capture_output=True, text=True, timeout=self.timeout, check=False
            )
        except FileNotFoundError as exc:
            raise OcrError(
                "ocrmypdf non è installato: `pip install ocrmypdf` e installa Tesseract "
                "(Windows: https://github.com/UB-Mannheim/tesseract/wiki; macOS: brew install "
                "tesseract; Linux: apt install tesseract-ocr tesseract-ocr-ita)"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise OcrError(f"ocrmypdf ha superato il timeout di {self.timeout:.0f}s") from exc
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout or "").strip().splitlines()[-3:]
            raise OcrError("ocrmypdf ha fallito: " + " | ".join(tail))


class OcrSource:
    """Sorgente di pagine che applica l'OCR **solo se serve**, su una copia temporanea.

    Se il PDF ha già testo, il wrapper è trasparente: nessun processo, nessun file in più.
    """

    def __init__(
        self,
        source,
        *,
        workdir: Path | None = None,
        ocr_applied: bool = False,
        command: Sequence[str] = (),
    ) -> None:
        self.source = source
        self._workdir = workdir
        self.ocr_applied = ocr_applied
        self.command = tuple(command)

    @classmethod
    def open(
        cls,
        pdf_path: str,
        *,
        config: OcrConfig | None = None,
        runner: object | None = None,
        opener: Callable[[str], object] = PdfPageSource.open,
    ) -> OcrSource:
        """Apre il PDF; se è una scansione produce prima la copia OCR."""
        source = opener(pdf_path)
        if not looks_scanned(source):
            return cls(source)
        workdir = Path(tempfile.mkdtemp(prefix="pdfbook-ocr-"))
        output = workdir / "ocr.pdf"
        command = ocrmypdf_command(pdf_path, output, config or OcrConfig())
        executor = runner if runner is not None else SubprocessRunner()
        source.close()
        try:
            executor.run(command)  # type: ignore[attr-defined]
        except OcrError:
            shutil.rmtree(workdir, ignore_errors=True)
            raise
        if not output.is_file() or output.stat().st_size == 0:
            shutil.rmtree(workdir, ignore_errors=True)
            raise OcrError("ocrmypdf non ha prodotto un PDF: controlla i log del comando")
        log.info("OCR applicato: %s", output)
        return cls(opener(str(output)), workdir=workdir, ocr_applied=True, command=command)

    # ---------- DocumentSource ----------

    @property
    def doc(self):
        return self.source.doc

    @property
    def page_count(self) -> int:
        return self.source.page_count

    def page(self, index: int):
        return self.source.page(index)

    def close(self) -> None:
        self.source.close()
        if self._workdir is not None:
            shutil.rmtree(self._workdir, ignore_errors=True)
            self._workdir = None


def looks_scanned(source, *, sample: int = SAMPLE_PAGES) -> bool:
    """``True`` se la maggioranza delle pagine campionate non ha testo utile."""
    total = max(int(source.page_count), 0)
    if not total:
        return False
    indexes = range(min(total, max(sample, 1)))
    empty = sum(1 for index in indexes if not has_text(source.page(index)))
    return empty * 2 > len(list(indexes))
