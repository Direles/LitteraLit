"""Applicazione: orchestrazione del documento.

Contiene il job (``pipeline``) e la costruzione delle dipendenze reali (``runtime``).
Nessuna logica di dominio: qui si compone soltanto.
"""

from .page_plan import PagePlan, UnitTarget, build_plans
from .pipeline import JobResult, JobSpec, TranslationJob, block_units
from .runtime import Runtime, build_runtime

__all__ = [
    "JobResult",
    "JobSpec",
    "PagePlan",
    "Runtime",
    "TranslationJob",
    "UnitTarget",
    "block_units",
    "build_plans",
    "build_runtime",
]
