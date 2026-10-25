"""Pannello di configurazione della GUI (M11).

Raccoglie provider, modello, lingua e glossario e li converte in ``AppSettings``.
**La chiave API non viene mai salvata**: vive solo in memoria per la sessione (R11).
"""

from __future__ import annotations

import threading
from dataclasses import replace
from tkinter import messagebox

import customtkinter as ctk

from pdfbook.app.errors import describe
from pdfbook.config.settings import LANGUAGES, MODEL_SUGGESTIONS, AppSettings
from pdfbook.translation.providers.discovery import LOCAL_PRESETS, list_models
from pdfbook.translation.providers.registry import PROVIDER_NAMES

__all__ = ["ConfigPanel"]


class ConfigPanel(ctk.CTkFrame):
    """Sidebar: provider, credenziali, modello, lingua, glossario."""

    def __init__(self, master, settings: AppSettings) -> None:
        super().__init__(master, width=280, corner_radius=0)
        self.settings = settings
        self.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(self, text="CONFIGURAZIONE", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="w"
        )
        ctk.CTkLabel(self, text="Provider LLM:").grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.provider = ctk.CTkOptionMenu(
            self, values=list(PROVIDER_NAMES), command=self._on_provider_change
        )
        self.provider.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.provider.set(settings.provider if settings.provider in PROVIDER_NAMES else PROVIDER_NAMES[0])

        ctk.CTkLabel(self, text="API Key (non salvata):").grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.api_key = ctk.CTkEntry(self, show="*", placeholder_text="chiave API...")
        self.api_key.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        if settings.api_key:
            self.api_key.insert(0, settings.api_key)

        ctk.CTkLabel(self, text="Modello:").grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        self.model = ctk.CTkComboBox(self, values=list(MODEL_SUGGESTIONS.get(settings.provider, ("default",))))
        self.model.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        self.model.set(settings.model)
        self.refresh_button = ctk.CTkButton(
            self, text="Leggi modelli caricati", height=26, command=self.refresh_models
        )
        self.refresh_button.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="ew")
        self.models_status = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(size=11))
        self.models_status.grid(row=7, column=0, padx=20, pady=(30, 0), sticky="w")

        ctk.CTkLabel(self, text="Base URL (solo custom):").grid(row=8, column=0, padx=20, pady=(10, 0), sticky="w")
        self.base_url = ctk.CTkEntry(self, placeholder_text=LOCAL_PRESETS["lm-studio"])
        self.base_url.grid(row=9, column=0, padx=20, pady=5, sticky="ew")
        if settings.base_url:
            self.base_url.insert(0, settings.base_url)

        ctk.CTkLabel(self, text="Lingua e glossario:").grid(row=10, column=0, padx=20, pady=(10, 0), sticky="w")
        self.language = ctk.CTkOptionMenu(self, values=list(LANGUAGES))
        self.language.set(settings.target_lang)
        self.language.grid(row=11, column=0, padx=20, pady=5, sticky="ew")

        self.glossary = ctk.CTkEntry(self, placeholder_text="Sprint, backlog (separati da virgola)")
        self.glossary.grid(row=12, column=0, padx=20, pady=(5, 20), sticky="ew")
        if settings.glossary:
            self.glossary.insert(0, ", ".join(settings.glossary))

    # ---------- API ----------

    def to_settings(self) -> AppSettings:
        """Impostazioni correnti del pannello (segreto incluso, solo in memoria)."""
        glossary = tuple(
            term.strip() for term in self.glossary.get().split(",") if term.strip()
        )
        return replace(
            self.settings,
            provider=self.provider.get(),
            model=self.model.get().strip(),
            target_lang=self.language.get(),
            base_url=self.base_url.get().strip(),
            glossary=glossary,
            api_key=self.api_key.get().strip(),
        )

    def validate(self) -> tuple[bool, str]:
        """Controllo locale prima di avviare: restituisce ``(ok, messaggio)``."""
        settings = self.to_settings()
        missing = settings.missing_required()
        if missing:
            return False, "Campi mancanti: " + ", ".join(missing)
        if not settings.model:
            return False, "Selezionare un modello."
        return True, ""

    def _on_provider_change(self, provider: str) -> None:
        suggestions = MODEL_SUGGESTIONS.get(provider, ("default",))
        self.model.configure(values=list(suggestions))
        self.model.set(suggestions[0])
        if provider == "Custom OpenAI-Compatible" and not self.base_url.get().strip():
            self.base_url.insert(0, LOCAL_PRESETS["lm-studio"])

    # ---------- modelli del server locale ----------

    def refresh_models(self) -> None:
        """Legge ``/v1/models`` dall'endpoint configurato e popola la tendina."""
        base_url = self.base_url.get().strip() or LOCAL_PRESETS["lm-studio"]
        if not self.base_url.get().strip():
            self.base_url.insert(0, base_url)
        self.models_status.configure(text="lettura modelli…")
        threading.Thread(target=self._fetch_models, args=(base_url,), daemon=True).start()

    def _fetch_models(self, base_url: str) -> None:
        try:
            models = list_models(base_url, api_key=self.api_key.get().strip(), timeout=4.0)
        except Exception as exc:  # noqa: BLE001 - l'errore si mostra, non si propaga
            message = describe(exc)
            self.after(0, lambda: self._models_failed(base_url, message))
            return
        self.after(0, lambda: self._models_loaded(models))

    def _models_loaded(self, models) -> None:
        if not models:
            self.models_status.configure(text="nessun modello caricato: caricalo in LM Studio")
            return
        self.model.configure(values=[model.id for model in models])
        self.model.set(models[0].id)
        self.models_status.configure(text=f"{len(models)} modelli trovati")

    def _models_failed(self, base_url: str, message: str) -> None:
        self.models_status.configure(text="lettura non riuscita")
        messagebox.showerror("Modelli non leggibili", f"{base_url}\n\n{message}")
