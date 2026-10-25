"""Costruzione dei prompt (M4).

Separare i prompt dal trasporto rende possibile: testarli senza rete, cambiarli senza
toccare provider o pipeline, e misurarne l'effetto (A/B) senza rischiare regressioni.

I template conservano le istruzioni validate sul campo della Gen 2 (gergo tecnico in
inglese, glossario vincolante, contesto della pagina precedente) con una differenza:
il contesto è **troncato in modo esplicito e configurabile**, non a colpi di slice sparsi.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence

__all__ = [
    "MAX_CONTEXT_CHARS",
    "SHORTEN_MAX_CHARS",
    "build_shorten_payload",
    "build_shorten_prompt",
    "build_translation_prompt",
    "build_user_payload",
    "glossary_terms",
]

MAX_CONTEXT_CHARS = 1500
SHORTEN_MAX_CHARS = 4000

_BASE_RULES = (
    "You are a professional book translator. Translate the values of the provided JSON object "
    "from English to {target_lang}.\n"
    "Please follow these advanced guidelines:\n"
    "1. Autonomously analyze the subject matter of the page (e.g., software engineering, agile "
    "design, management, etc.).\n"
    "2. Preserve standard technical jargon and industry-specific terminology in English (such as "
    "'User Story', 'MVP', 'Sprint', 'Release', 'framework', 'backlog', 'wireframe', etc.) if they "
    "are widely accepted and commonly left in English within the target language's professional "
    "environment.\n"
    "3. Maintain a natural, cohesive, and fluent tone across the sequential JSON blocks as they "
    "represent consecutive paragraphs of a book page.\n"
    "4. Return ONLY the translated JSON object containing the exact same keys. Do not explain, do "
    "not add markdown wrapping, do not add comments. Keep bullet characters (like '■') intact. "
    "Preserve formatting details like multiple consecutive spaces or tabs where possible. "
    "If the text contains tags such as <b> or <i>, keep them exactly around their translated content."
)

_GLOSSARY_RULE = "\n5. MANDATORY GLOSSARY: the following terms must remain EXACTLY as-is, untranslated: {terms}."

_CONTEXT_RULE = (
    "\n6. For stylistic and terminological consistency, here is the text of the previous page "
    "(do NOT translate it, use it only as context):\n---\n{context}\n---"
)


def build_translation_prompt(
    target_lang: str,
    *,
    glossary: Iterable[str] = (),
    context: str | None = None,
    max_context_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    """Prompt di sistema per la traduzione di un batch JSON."""
    prompt = _BASE_RULES.format(target_lang=target_lang)
    terms = ", ".join(f"'{term.strip()}'" for term in glossary if term and term.strip())
    if terms:
        prompt += _GLOSSARY_RULE.format(terms=terms)
    if context and context.strip():
        trimmed = context.strip()[: max(0, max_context_chars)]
        prompt += _CONTEXT_RULE.format(context=trimmed)
    return prompt


def build_shorten_prompt(
    target_lang: str,
    max_chars: int,
    *,
    glossary: Iterable[str] = (),
) -> str:
    """Prompt per ottenere una traduzione più corta a parità di significato."""
    if max_chars <= 0:
        raise ValueError("max_chars deve essere positivo")
    terms = ", ".join(f"'{term.strip()}'" for term in glossary if term and term.strip())
    glossary_note = f" Keep these terms untranslated: {terms}." if terms else ""
    return (
        "You are a professional book translator working with strict layout constraints. "
        f"The following {target_lang} translation is too long to fit the space of the original text "
        f"on the page. Rewrite it so that it is AT MOST {max_chars} characters long (including "
        f"spaces), while preserving the full meaning. Use more concise phrasing, but stay natural "
        f"and fluent.{glossary_note} "
        'Return ONLY a JSON object: {"short": "<the shortened translation>"}'
    )


def build_user_payload(batch: Mapping[str, str]) -> str:
    """Serializza il batch come oggetto JSON preservando i caratteri non ASCII."""
    return json.dumps(dict(batch), ensure_ascii=False)


def build_shorten_payload(original: str, current: str, max_chars: int) -> str:
    """Payload per ``build_shorten_prompt`` (chiavi fisse, documentate nel prompt)."""
    return json.dumps(
        {"original_english": original, "current_translation": current, "max_chars": max_chars},
        ensure_ascii=False,
    )


def glossary_terms(glossary: Sequence[str]) -> tuple[str, ...]:
    """Normalizza il glossario: trim, scarta vuoti, deduplica mantenendo l'ordine."""
    seen: dict[str, None] = {}
    for term in glossary:
        cleaned = term.strip()
        if cleaned:
            seen.setdefault(cleaned, None)
    return tuple(seen)
