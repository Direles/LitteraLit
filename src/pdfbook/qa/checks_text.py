"""Controlli di qualità del **testo** tradotto (Fase 5.4).

Tre famiglie di difetti che nessun controllo geometrico vede:

* **omissione**: la traduzione è molto più corta dell'originale (un capoverso perso, una riga
  saltata dal modello);
* **ripetizione**: lo stesso giro di parole compare più volte nella stessa pagina (loop del
  modello, riga duplicata);
* **lingua sbagliata**: il modello risponde in inglese o in un'altra lingua.

Tutti e tre sono **informativi**: non bloccano il gate, servono a chi rilegge. Le soglie sono
larghe apposta — l'italiano è più lungo dell'inglese, e un dialogo ha frasi brevissime.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping

from pdfbook.domain.models import IssueKind, QAIssue

__all__ = [
    "LENGTH_RATIO_MAX",
    "LENGTH_RATIO_MIN",
    "MAX_REPETITION_ISSUES",
    "SHINGLE_WORDS",
    "check_language",
    "check_length_ratio",
    "check_repetitions",
    "run_text_checks",
]

#: Rapporto minimo/massimo accettabile fra lunghezza tradotta e originale (in caratteri).
LENGTH_RATIO_MIN = 0.45
LENGTH_RATIO_MAX = 2.4
#: Sotto questa lunghezza il rapporto non è affidabile (titoli, didascalie, numeri).
MIN_CHARS_FOR_RATIO = 40
#: Dimensione dello shingle usato per scoprire le ripetizioni.
SHINGLE_WORDS = 7
#: Quante volte deve comparire uno shingle per essere sospetto.
REPEAT_THRESHOLD = 3
#: Massimo numero di ripetizioni segnalate per pagina (le più frequenti).
MAX_REPETITION_ISSUES = 3

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

#: Parole funzionali: bastano a distinguere le lingue che interessano, senza dipendenze.
def _words(text: str) -> frozenset[str]:
    """Parole di una lista separata da spazi, come insieme."""
    return frozenset(text.split())


_STOPWORDS: dict[str, frozenset[str]] = {
    "it": _words(
        "il lo la i gli le di del della che e ? un una per con non "
        "si in al alla dei delle come pi? anche questo questa sono essere ha hanno nel nella"
    ),
    "en": _words(
        "the of and to in is that for it as with was on are "
        "be this by not or from at which but have has had they you we"
    ),
    "fr": _words(
        "le la les de des du et est un une pour avec "
        "dans que qui ne pas sur au aux ce cette sont ?tre plus"
    ),
    "de": _words(
        "der die das und ist ein eine f?r mit von den "
        "dem des nicht auf sich sind wird auch als bei aus"
    ),
    "es": _words(
        "el la los las de del y es un una para con "
        "en que no por se su al como m?s tambi?n son est?"
    ),
}


def check_length_ratio(
    page: int,
    originals: Mapping[str, str],
    translations: Mapping[str, str],
    *,
    min_ratio: float = LENGTH_RATIO_MIN,
    max_ratio: float = LENGTH_RATIO_MAX,
) -> list[QAIssue]:
    """Segnala unità tradotte troppo corte o troppo lunghe rispetto all'originale."""
    issues: list[QAIssue] = []
    for key, original in originals.items():
        translated = translations.get(key)
        if not translated or len(original.strip()) < MIN_CHARS_FOR_RATIO:
            continue
        ratio = len(translated.strip()) / max(len(original.strip()), 1)
        if min_ratio <= ratio <= max_ratio:
            continue
        issues.append(
            QAIssue(
                page=page,
                kind=IssueKind.LENGTH_RATIO,
                block=key,
                detail=f"rapporto lunghezza {ratio:.2f} (atteso {min_ratio:.2f}–{max_ratio:.2f})",
            )
        )
    return issues


def check_repetitions(
    page: int,
    translations: Mapping[str, str],
    *,
    size: int = SHINGLE_WORDS,
    threshold: int = REPEAT_THRESHOLD,
) -> list[QAIssue]:
    """Segnala giri di parole ripetuti nella stessa pagina (loop o riga duplicata)."""
    shingles: Counter[tuple[str, ...]] = Counter()
    for text in translations.values():
        words = [word.lower() for word in _WORD.findall(text or "")]
        for index in range(len(words) - size + 1):
            shingles[tuple(words[index : index + size])] += 1
    issues: list[QAIssue] = []
    for shingle, count in shingles.most_common(MAX_REPETITION_ISSUES):
        if count < threshold:
            continue
        issues.append(
            QAIssue(
                page=page,
                kind=IssueKind.REPETITION,
                detail=f"\"{' '.join(shingle)}\" ripetuto {count} volte",
            )
        )
    return issues


def check_language(
    page: int,
    translations: Mapping[str, str],
    *,
    expected: str = "it",
    min_words: int = 20,
) -> list[QAIssue]:
    """Segnala una pagina tradotta in una lingua diversa da quella attesa."""
    text = " ".join(value for value in translations.values() if value)
    words = [word.lower() for word in _WORD.findall(text)]
    if len(words) < min_words:
        return []
    scores = {
        lang: sum(1 for word in words if word in stopwords)
        for lang, stopwords in _STOPWORDS.items()
    }
    winner = max(scores, key=lambda lang: scores[lang])
    expected_key = _normalise_lang(expected)
    if expected_key not in _STOPWORDS or winner == expected_key:
        return []
    if scores[expected_key] == 0 or scores[winner] <= scores[expected_key]:
        return []
    return [
        QAIssue(
            page=page,
            kind=IssueKind.WRONG_LANGUAGE,
            detail=f"lingua probabile '{winner}', attesa '{expected_key}'",
        )
    ]


def run_text_checks(
    page: int,
    originals: Mapping[str, str],
    translations: Mapping[str, str],
    *,
    expected_lang: str = "it",
) -> list[QAIssue]:
    """Tutti i controlli testuali della pagina, in un solo passaggio."""
    return (
        check_length_ratio(page, originals, translations)
        + check_repetitions(page, translations)
        + check_language(page, translations, expected=expected_lang)
    )


def _normalise_lang(lang: str) -> str:
    return (lang or "").strip().lower()[:2]
