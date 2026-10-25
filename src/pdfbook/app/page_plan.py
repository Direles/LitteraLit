"""Piani di traduzione per pagina, con stitching (Fase 2).

Trasforma le pagine estratte in **unità di traduzione**: normalmente un blocco = un'unità,
ma due blocchi consecutivi di pagine diverse possono diventare un'unica unità (paragrafo
che continua). Il piano dice anche dove va ricollocata la traduzione, così la pipeline non
deve conoscere né il flow né la segmentazione.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from pdfbook.domain.models import PageLayout, TextBlock
from pdfbook.layout.flow import Continuation, detect_continuations, merged_text
from pdfbook.layout.segmentation import is_structured_block

__all__ = ["PagePlan", "UnitTarget", "block_units", "build_plans"]


@dataclass(frozen=True)
class UnitTarget:
    """Dove va la traduzione di un'unità: un blocco, oppure due (unità stitched)."""

    first_block: str
    second_block: str | None = None
    first_text: str = ""
    second_text: str = ""


@dataclass
class PagePlan:
    """Cosa chiedere al traduttore per una pagina e dove mettere il risultato."""

    page: PageLayout
    requests: dict[str, str] = field(default_factory=dict)
    targets: dict[str, UnitTarget] = field(default_factory=dict)
    incoming: dict[str, str] = field(default_factory=dict)


def block_units(page: PageLayout) -> dict[str, str]:
    """Unità "naturali": ``b{i}`` per la prosa, ``b{i}_l{j}`` per le colonne."""
    units: dict[str, str] = {}
    for block in page.blocks:
        text = block.text
        if not text.strip():
            continue
        if is_structured_block(block):
            for index, line in enumerate(block.lines):
                if line.text.strip():
                    units[f"{block.id}_l{index}"] = line.text
        else:
            units[block.id] = text
    return units


def build_plans(pages: Sequence[PageLayout], *, stitch: bool = True) -> list[PagePlan]:
    """Costruisce un piano per pagina, unendo le continuazioni se ``stitch`` è attivo."""
    plans = [PagePlan(page=page, requests=block_units(page)) for page in pages]
    if not stitch:
        return plans
    for target in plans:
        target.targets = {
            key: UnitTarget(first_block=key) for key in target.requests
        }
    for continuation in detect_continuations(pages):
        _apply(plans, continuation)
    return plans


def _apply(plans: list[PagePlan], continuation: Continuation) -> None:
    first_plan = plans[continuation.previous_index]
    second_plan = plans[continuation.next_index]
    first_key = continuation.previous_block
    second_key = continuation.next_block
    if first_key not in first_plan.requests or second_key not in second_plan.requests:
        return  # blocco strutturato o già unito: si lascia com'è (euristica conservativa)
    previous_block = _block_by_id(first_plan.page, first_key)
    following_block = _block_by_id(second_plan.page, second_key)
    if previous_block is None or following_block is None:
        return
    text = merged_text(previous_block, following_block, hyphen=continuation.hyphen)
    first_plan.requests.pop(first_key)
    second_plan.requests.pop(second_key)
    first_plan.requests[continuation.key] = text
    first_plan.targets.pop(first_key, None)
    first_plan.targets[continuation.key] = UnitTarget(
        first_block=first_key,
        second_block=second_key,
        first_text=previous_block.text,
        second_text=following_block.text,
    )


def _block_by_id(page: PageLayout, block_id: str) -> TextBlock | None:
    for block in page.blocks:
        if block.id == block_id:
            return block
    return None
