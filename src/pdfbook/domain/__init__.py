"""Dominio: strutture dati condivise e contratti.

Questo layer non importa nulla dal resto del package (regola R5): solo stdlib.
"""

from .models import (
    BlockKind,
    IssueKind,
    Line,
    PageLayout,
    QAIssue,
    QAReport,
    Rect,
    Span,
    TextBlock,
    TranslationSettings,
)

__all__ = [
    "BlockKind",
    "IssueKind",
    "Line",
    "PageLayout",
    "QAIssue",
    "QAReport",
    "Rect",
    "Span",
    "TextBlock",
    "TranslationSettings",
]
