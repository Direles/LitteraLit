"""Profili di stile per libro (Fase 5.5).

Lo stesso testo tradotto "fedelmente" e "scorrevolmente" dà risultati diversi: un saggio
accademico vuole calchi e citazioni intatte, un memoir vuole frasi naturali. Il profilo è
**solo una riga di prompt** (più la partizione di cache), non una riscrittura: cambiare
stile non deve cambiare struttura, glossario o gestione dei tag.

I profili sono pochi e dichiarati: un elenco aperto di stili liberi produrrebbe testi
imprevedibili e cache inutilizzabile.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["DEFAULT_PROFILE", "PROFILES", "StyleProfile", "profile_names", "resolve", "style_rule"]

DEFAULT_PROFILE = "fedele"


@dataclass(frozen=True)
class StyleProfile:
    """Uno stile: nome, registro e regola aggiuntiva per il prompt."""

    name: str
    register: str
    guidance: str


PROFILES: dict[str, StyleProfile] = {
    DEFAULT_PROFILE: StyleProfile(
        name=DEFAULT_PROFILE,
        register="neutro",
        guidance="",
    ),
    "scorrevole": StyleProfile(
        name="scorrevole",
        register="naturale",
        guidance=(
            "Prefer natural, readable sentences over literal calques; split long English "
            "sentences when Italian reads better, without adding or removing information."
        ),
    ),
    "accademico": StyleProfile(
        name="accademico",
        register="formale",
        guidance=(
            "Keep a formal academic register; preserve hedged claims (may, might, suggests) and "
            "do not simplify technical reasoning. Keep quotations and citations word-for-word."
        ),
    ),
    "narrativo": StyleProfile(
        name="narrativo",
        register="letterario",
        guidance=(
            "Preserve the narrative voice and rhythm, including deliberate fragments and "
            "repetitions; do not smooth away the author's style."
        ),
    ),
}


def profile_names() -> tuple[str, ...]:
    return tuple(PROFILES)


def resolve(name: str | None) -> StyleProfile:
    """Profilo richiesto, con fallback esplicito al default se il nome è vuoto.

    Un nome **sconosciuto** è un errore di configurazione, non un silenzio: chi scrive
    ``PDFBOOK_STYLE=accademicoo`` deve accorgersene subito.
    """
    key = (name or DEFAULT_PROFILE).strip().lower()
    if not key:
        return PROFILES[DEFAULT_PROFILE]
    if key not in PROFILES:
        raise ValueError(
            f"profilo di stile sconosciuto: '{name}' (disponibili: {', '.join(profile_names())})"
        )
    return PROFILES[key]


def style_rule(profile: StyleProfile, number: int = 7) -> str:
    """Regola numerata da accodare al prompt; stringa vuota per il profilo di default."""
    if not profile.guidance:
        return ""
    return f"\n{number}. STYLE ({profile.name}, {profile.register}): {profile.guidance}"
