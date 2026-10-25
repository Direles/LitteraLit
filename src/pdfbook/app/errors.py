"""Classificazione degli errori per l'utente (Fase 3.4).

Un errore deve dire **cosa fare**, non solo cosa è andato storto. Qui si mappa un'eccezione
in un codice di uscita stabile e in un messaggio azionabile, senza perdere la causa
originale (che resta nei log).
"""

from __future__ import annotations

import pymupdf as fitz

from pdfbook.translation.json_repair import JsonRepairError
from pdfbook.translation.providers.base import ProviderError

__all__ = [
    "EXIT_CODES",
    "UsageError",
    "classify",
    "describe",
]

EXIT_CODES = {
    "ok": 0,
    "gate": 1,
    "config": 2,
    "input": 3,
    "provider": 4,
    "layout": 5,
}


class UsageError(ValueError):
    """Configurazione o argomenti non validi (codice 2)."""


def classify(error: BaseException) -> str:
    """Categoria dell'errore: chiave di ``EXIT_CODES``."""
    # Prima i tipi specifici: JsonRepairError è anche un ValueError.
    if isinstance(error, (ProviderError, JsonRepairError)):
        return "provider"
    if isinstance(error, (UsageError, ValueError)):
        return "config"
    if isinstance(error, (FileNotFoundError, IsADirectoryError, fitz.FileDataError)):
        return "input"
    return "layout"


def describe(error: BaseException) -> str:
    """Messaggio per l'utente, con il rimedio concreto."""
    category = classify(error)
    detail = str(error) or type(error).__name__
    if category == "config":
        return (
            f"Configurazione non valida: {detail}. "
            "Controlla il file .env (PDFBOOK_PROVIDER, PDFBOOK_MODEL, PDFBOOK_API_KEY)."
        )
    if category == "input":
        return (
            f"File non leggibile: {detail}. "
            "Verifica il percorso e che il PDF non sia protetto da password."
        )
    if category == "provider":
        return (
            f"Errore del provider: {detail}. "
            "Verifica la chiave, il nome del modello e la connessione; "
            "se è un limite di frequenza, riprova più tardi."
        )
    return f"Errore durante l'elaborazione: {detail}."
