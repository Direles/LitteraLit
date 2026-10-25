"""Traduzione di una pagina a partire dal piano (Fase 2/5).

Separa due responsabilità che nel job stavano insieme: *cosa chiedere* (piano) e *come
ricollocare le risposte* (unità semplici, continuazioni spezzate, glossario). Il job resta
orchestrazione pura.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from pdfbook.domain.models import IssueKind, QAIssue, QAReport
from pdfbook.layout.flow import split_translation
from pdfbook.qa.checks_glossary import check_glossary
from pdfbook.qa.checks_text import run_text_checks
from pdfbook.translation.pipeline import TranslationPipeline
from pdfbook.translation.terminology import Terminology

from .page_plan import PagePlan, UnitTarget

__all__ = ["PageTranslator"]


@dataclass
class PageTranslator:
    """Traduce le unità di una pagina e riporta le continuazioni alla pagina dopo."""

    translator: TranslationPipeline
    glossary: Sequence[str] = ()
    target_lang: str = "it"
    terminology: Terminology = field(default_factory=Terminology)

    def suggestions(self, *, limit: int = 40) -> list[str]:
        """Termini ricorrenti da proporre come glossario (Fase 5.3), esclusi quelli già attivi."""
        known = {term.strip().lower() for term in self.glossary if term.strip()}
        return [
            term.text
            for term in self.terminology.candidates(limit=limit * 2)
            if term.text.strip().lower() not in known
        ][:limit]

    def translate(
        self,
        plans: list[PagePlan],
        index: int,
        previous: str | None,
        report: QAReport,
        counters: dict[str, int],
    ) -> dict[str, str]:
        plan = plans[index]
        translations = dict(plan.incoming)
        if not plan.requests:
            return translations
        outcome = self.translator.translate(plan.requests, context=previous)
        self.terminology.observe(plan.page.number, plan.requests.values())
        for issue in check_glossary(
            plan.page.number, plan.requests, outcome.translations, self.glossary
        ):
            report.add(issue)
        for issue in run_text_checks(
            plan.page.number, plan.requests, outcome.translations, expected_lang=self.target_lang
        ):
            report.add(issue)
        for unit_key, value in outcome.translations.items():
            target = plan.targets.get(unit_key)
            if target is None:
                continue
            if target.second_block is None:
                translations[target.first_block] = value
                continue
            self._split(plans, index, target, value, translations, report, counters)
        return translations

    @staticmethod
    def _split(
        plans: list[PagePlan],
        index: int,
        target: UnitTarget,
        translated: str,
        translations: dict[str, str],
        report: QAReport,
        counters: dict[str, int],
    ) -> None:
        plan = plans[index]
        split = split_translation(target.first_text, target.second_text, translated)
        translations[target.first_block] = split.first
        if not split.usable:
            report.add(
                QAIssue(
                    page=plan.page.number,
                    kind=IssueKind.SPLIT_FAILED,
                    block=target.first_block,
                    detail=f"non divisibile: {target.second_block} resta senza traduzione",
                )
            )
            return
        plans[index + 1].incoming[target.second_block] = split.second
        counters["stitched"] += 1
        report.add(
            QAIssue(
                page=plan.page.number,
                kind=IssueKind.PARAGRAPH_STITCHED,
                block=target.first_block,
                detail=f"continua in {target.second_block} (pagina {plans[index + 1].page.number})",
            )
        )
