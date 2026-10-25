"""Applicazione: orchestrazione del documento.

Contiene il job (``pipeline``) e la costruzione delle dipendenze reali (``runtime``).
Nessuna logica di dominio: qui si compone soltanto.
"""

from .pipeline import JobResult, JobSpec, TranslationJob, batch_for_page
from .runtime import Runtime, build_runtime

__all__ = ["JobResult", "JobSpec", "Runtime", "TranslationJob", "batch_for_page", "build_runtime"]
