"""GUI desktop (M11).

Interfaccia sottile: raccoglie i parametri, avvia ``TranslationJob`` in un thread daemon e
mostra progresso, log e esito. **Nessun salvataggio di segreti** e nessuna logica di
traduzione: tutto vive nei layer sottostanti.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from pdfbook.app import JobResult, JobSpec, TranslationJob, build_runtime
from pdfbook.app.errors import describe
from pdfbook.app.metrics import from_summary
from pdfbook.config.settings import load_settings
from pdfbook.qa.html_report import write_html

from .config_panel import ConfigPanel
from .presenter import ProgressTracker, digest_lines, summary_lines

__all__ = ["TranslatorApp", "main"]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TranslatorApp(ctk.CTk):
    """Finestra principale: configurazione a sinistra, file e log a destra."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Book Translator")
        self.geometry("980x680")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.panel = ConfigPanel(self, load_settings(env_file=".env"))
        self.tracker = ProgressTracker()
        self.started_at = 0.0
        self.cancel_requested = False
        self._preview_paths: tuple[str, str, int] | None = None
        self.panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        main = ctk.CTkFrame(self)
        main.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(6, weight=1)
        self.main_frame = main
        self._build_main(main)
        self._enable_drop(main)

    def _build_main(self, main) -> None:
        """Titolo, campi, pulsanti, barra e log della colonna di destra."""
        ctk.CTkLabel(main, text="TRADUZIONE LIBRI PDF", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="w"
        )
        self.input_entry = self._file_row(main, 1, "PDF di input", self._browse_input)
        self.output_entry = self._file_row(main, 2, "PDF di output", self._browse_output)
        self._pages_row(main, 3)

        self.start_button = ctk.CTkButton(
            main, text="Avvia traduzione", height=40,
            font=ctk.CTkFont(size=14, weight="bold"), command=self._start,
        )
        self.start_button.grid(row=4, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.cancel_button = ctk.CTkButton(
            main, text="Annulla", height=28, fg_color="#7a2f2f", hover_color="#934040",
            state="disabled", command=self._cancel_run,
        )
        self.cancel_button.grid(row=4, column=0, padx=20, pady=(6, 5), sticky="e")
        self.preview_button = ctk.CTkButton(
            main, text="Anteprima", height=28, width=110, state="disabled",
            command=self._open_preview,
        )
        self.preview_button.grid(row=4, column=0, padx=(20, 120), pady=(6, 5), sticky="w")
        self.progress = ctk.CTkProgressBar(main)
        self.progress.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        self.progress.set(0.0)
        self.log_box = ctk.CTkTextbox(main, height=220, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=6, column=0, padx=20, pady=(5, 20), sticky="nsew")

    # ---------- costruzione widget ----------

    def _file_row(self, parent, row: int, label: str, browse) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label).grid(row=row * 2 - 1, column=0, padx=20, pady=(10, 0), sticky="w")
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row * 2, column=0, padx=20, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(frame, placeholder_text="nessun file selezionato")
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(frame, text="Sfoglia...", width=90, command=browse).grid(row=0, column=1)
        return entry

    def _pages_row(self, parent, row: int) -> None:
        ctk.CTkLabel(parent, text="Pagine (vuoto = tutte)").grid(
            row=row * 2 + 1, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row * 2 + 2, column=0, padx=20, pady=5, sticky="ew")
        self.page_start = ctk.CTkEntry(frame, placeholder_text="da")
        self.page_start.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.page_end = ctk.CTkEntry(frame, placeholder_text="a")
        self.page_end.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

    # ---------- azioni ----------

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(title="Seleziona PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, path)
        source = Path(path)
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, str(source.with_name(f"{source.stem}-ITALIANO{source.suffix}")))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Salva PDF tradotto", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
        )
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def _start(self) -> None:
        ok, message = self.panel.validate()
        if not ok:
            self._log(f"Errore: {message}")
            return
        input_pdf = self.input_entry.get().strip()
        output_pdf = self.output_entry.get().strip()
        if not input_pdf or not os.path.exists(input_pdf):
            self._log("Errore: selezionare un PDF di input valido.")
            return
        if not output_pdf:
            self._log("Errore: indicare il file di output.")
            return
        spec = JobSpec(
            input_pdf=Path(input_pdf),
            output_pdf=Path(output_pdf),
            settings=self.panel.to_settings(),
            page_start=self._int_or_none(self.page_start.get()),
            page_end=self._int_or_none(self.page_end.get()),
        )
        self.start_button.configure(state="disabled", text="Traduzione in corso...")
        self.cancel_button.configure(state="normal")
        self.cancel_requested = False
        self.progress.set(0.0)
        self.tracker.begin(time.perf_counter(), 0)
        self.started_at = time.perf_counter()
        self.log_box.delete("1.0", "end")
        threading.Thread(target=self._worker, args=(spec,), daemon=True).start()

    def _worker(self, spec: JobSpec) -> None:
        try:
            runtime = build_runtime(spec.input_pdf, spec.settings)
            result = TranslationJob(spec, runtime).run(
                progress=self._progress, cancel=lambda: self.cancel_requested
            )
        except Exception as exc:  # noqa: BLE001 - l'errore va mostrato, non propagato
            message = describe(exc)
            self.after(0, lambda: self._failed(message))
            return
        self.after(0, lambda: self._finished(result))

    def _cancel_run(self) -> None:
        """Annullamento cooperativo: il job si ferma prima della pagina successiva."""
        self.cancel_requested = True
        self.cancel_button.configure(state="disabled")
        self._log("Annullamento richiesto: mi fermo a fine pagina, journal e cache restano.")

    def _open_preview(self) -> None:
        from .preview_window import PreviewWindow

        if self._preview_paths is None:
            return
        original, output, pages = self._preview_paths
        PreviewWindow(self, original_pdf=original, output_pdf=output, pages=pages)

    def _enable_drop(self, widget) -> None:
        """Drag & drop del PDF, se l'extra opzionale ``tkinterdnd2`` è installato."""
        try:
            from tkinterdnd2 import DND_FILES

            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:  # noqa: BLE001 - l'extra non c'è: si usa il pulsante Sfoglia
            self._log("Trascinamento non disponibile (opzionale: pip install tkinterdnd2).")

    # ---------- callback UI ----------

    def _progress(self, current: int, total: int, message: str) -> None:
        view = self.tracker.update(current, total, time.perf_counter())

        def update() -> None:
            self.progress.set(view.percent)
            self._log(f"{message} · {view.label()}")
        self.after(0, update)

    def _finished(self, result: JobResult) -> None:
        self.start_button.configure(state="normal", text="Avvia traduzione")
        self.cancel_button.configure(state="disabled")
        self.preview_button.configure(state="normal")
        self._preview_paths = (
            str(self.input_entry.get().strip()),
            str(result.output_pdf),
            result.pages or 1,
        )
        self.progress.set(1.0)
        metrics = from_summary(
            result.summary,
            pages=result.pages,
            blocks=result.blocks,
            seconds=time.perf_counter() - self.started_at,
        )
        for line in summary_lines(result, metrics):
            self._log(line)
        self._log(f"PDF: {result.output_pdf}")
        self._log(f"Report QA: {result.report_path}")
        try:
            self._log(f"Report leggibile: {write_html(result.report_path)}")
        except OSError as exc:
            self._log(f"Report HTML non scritto: {exc}")
        for line in digest_lines(result.report):
            self._log(line)
        violations = result.violations()
        if not violations:
            messagebox.showinfo("Traduzione completata", f"PDF salvato in:\n{result.output_pdf}")

    def _failed(self, message: str) -> None:
        self.start_button.configure(state="normal", text="Avvia traduzione")
        self.cancel_button.configure(state="disabled")
        self._log(f"[ERRORE] {message}")
        messagebox.showerror("Errore", message)

    def _on_drop(self, event) -> None:
        """Percorso trascinato → campo di input (e output accanto, se vuoto)."""
        raw = str(getattr(event, "data", "")).strip().strip("{}")
        if not raw:
            return
        path = raw.split("}")[0] if "}" in raw else raw
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, path)
        if not self.output_entry.get().strip():
            candidate = Path(path)
            self.output_entry.insert(0, str(candidate.with_name(f"{candidate.stem}_IT.pdf")))
        self._log(f"File trascinato: {path}")

    def _log(self, message: str) -> None:
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")
        logging.getLogger("pdfbook.gui").info(message)

    @staticmethod
    def _int_or_none(raw: str) -> int | None:
        value = raw.strip()
        if not value.isdigit():
            return None
        return int(value)


def main() -> None:
    """Avvia la GUI (log su file accanto a quelli della CLI)."""
    from pdfbook.config.logging import configure

    configure("INFO")
    TranslatorApp().mainloop()


if __name__ == "__main__":
    main()
