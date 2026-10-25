"""Applicazione: orchestrazione del documento.

Contiene il job (``pipeline``) e la costruzione delle dipendenze reali (``runtime``).
Nessuna logica di dominio: qui si compone soltanto.
"""

from .job_result import JobResult
from .journal import Journal, load_journal, remove_journal, save_journal
from .page_plan import PagePlan, UnitTarget, build_plans
from .pipeline import JobSpec, TranslationJob, block_units
from .runtime import Runtime, build_runtime

__all__ = [
    "JobResult",
    "JobSpec",
    "Journal",
    "PagePlan",
    "Runtime",
    "TranslationJob",
    "UnitTarget",
    "block_units",
    "build_plans",
    "build_runtime",
    "load_journal",
    "remove_journal",
    "save_journal",
]
