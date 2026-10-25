"""Finestra di anteprima prima/dopo (Fase 6.1).

Una finestra sola, due colonne: originale a sinistra, tradotto a destra, con il selettore di
pagina e il conto della copertura. Nessuna logica di dominio: le coppie arrivano da
``gui/preview.py``.
"""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from pdfbook.app.errors import describe

from .preview import PreviewPage, preview_page

__all__ = ["PreviewWindow"]


class PreviewWindow(ctk.CTkToplevel):
    """Anteprima testo a fronte della pagina scelta."""

    def __init__(self, master, *, original_pdf: str, output_pdf: str, pages: int) -> None:
        super().__init__(master)
        self.title("Anteprima — originale e tradotto")
        self.geometry("1080x640")
        self.original_pdf = original_pdf
        self.output_pdf = output_pdf
        self.pages = max(pages, 1)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.page_var = ctk.StringVar(value="1")
        self.selector = ctk.CTkOptionMenu(
            self,
            values=[str(number) for number in range(1, self.pages + 1)],
            variable=self.page_var,
            command=lambda _value: self.refresh(),
            width=90,
        )
        self.selector.grid(row=0, column=0, padx=(15, 6), pady=10, sticky="w")
        self.info = ctk.CTkLabel(self, text="", anchor="w")
        self.info.grid(row=0, column=1, padx=6, pady=10, sticky="w")

        self.left = self._textbox(self, "ORIGINALE", 0, row=1)
        self.right = self._textbox(self, "TRADOTTO", 1, row=1)
        self.left_box = self.left
        self.right_box = self.right

        self.refresh()

    def _textbox(self, parent, title: str, column: int, *, row: int) -> ctk.CTkTextbox:
        panel = ctk.CTkFrame(parent)
        panel.grid(row=row, column=column, padx=(12, 6) if column == 0 else (6, 12), pady=(0, 12), sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(panel, text=title, font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=8, pady=(8, 2), sticky="w"
        )
        box = ctk.CTkTextbox(panel, wrap="word", font=ctk.CTkFont(size=12))
        box.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        return box

    def refresh(self) -> None:
        try:
            page = preview_page(self.original_pdf, self.output_pdf, self._page_number())
        except Exception as exc:  # noqa: BLE001 - l'anteprima non deve chiudere la GUI
            messagebox.showerror("Anteprima non disponibile", describe(exc))
            return
        self._fill(page)

    def _fill(self, page: PreviewPage) -> None:
        self.left_box.delete("1.0", "end")
        self.right_box.delete("1.0", "end")
        for original, translated in page.pairs:
            self.left_box.insert("end", original + "\n\n")
            self.right_box.insert("end", (translated or "—") + "\n\n")
        self.info.configure(
            text=(
                f"{len(page.pairs)} blocchi · {page.coverage:.0%} con traduzione"
                if page.pairs
                else "pagina senza testo estratto"
            )
        )

    def _page_number(self) -> int:
        try:
            return max(1, min(int(self.page_var.get()), self.pages))
        except (TypeError, ValueError):
            return 1
