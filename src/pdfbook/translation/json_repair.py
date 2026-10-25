"""Parsing e riparazione del JSON prodotto dai modelli (migrazione M1).

I modelli restituiscono "quasi JSON": a volte avvolgono tutto in un code fence, a volte
lasciano virgolette non escapate dentro i valori. Qui si applica una scala di degradazione
**deterministica** e testabile:

1. ``json.loads`` diretto;
2. rimozione del code fence (anche non chiuso);
3. estrazione per chiave con regex + decodifica dei singoli valori.

Contratto: restituisce ``dict[str, str]``; se nessuna strategia funziona solleva
``JsonRepairError`` conservando il payload (il chiamante decide se ritentare o salvarlo).
Nessun ``print``, nessuno stato globale (R13/R6).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence

__all__ = [
    "JsonRepairError",
    "escape_unescaped_quotes",
    "parse_json_object",
    "strip_code_fence",
]

_FENCE_RE = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\r?\n?(.*?)```", re.DOTALL)
_KEY_LINE_RE = re.compile(r"""["']?([A-Za-z0-9_\-]+)["']?\s*:""")
_MAX_STORED_RAW = 2000


class JsonRepairError(ValueError):
    """Il payload non è riconducibile a un oggetto JSON di stringhe."""

    def __init__(self, message: str, raw: str) -> None:
        super().__init__(f"{message} (payload: {len(raw)} caratteri)")
        self.raw = raw[:_MAX_STORED_RAW]


def strip_code_fence(raw: str) -> str:
    """Rimuove un blocco ```json ...``` (anche senza chiusura finale)."""
    text = raw.strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    if text.startswith("```"):
        return "\n".join(text.splitlines()[1:]).strip()
    return text


def escape_unescaped_quotes(text: str) -> str:
    """Escapa le virgolette non precedute da backslash (mantiene gli escape esistenti)."""
    out: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            out.append(char)
            escaped = False
        elif char == "\\":
            out.append(char)
            escaped = True
        elif char == '"':
            out.append('\\"')
        else:
            out.append(char)
    return "".join(out)


def parse_json_object(
    raw: str,
    expected_keys: Iterable[str] | None = None,
) -> dict[str, str]:
    """Estrae un oggetto ``{chiave: stringa}`` dal testo grezzo del modello."""
    keys = list(dict.fromkeys(expected_keys)) if expected_keys is not None else None
    text = raw.strip()
    if not text:
        raise JsonRepairError("risposta vuota", raw)

    for candidate in (text, strip_code_fence(text)):
        parsed = _loads_object(candidate)
        if parsed is not None:
            return _select(parsed, keys)

    return _select(_extract_by_keys(strip_code_fence(text), keys), keys)


def _loads_object(text: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _select(parsed: Mapping[str, object], keys: Sequence[str] | None) -> dict[str, str]:
    selected = parsed.keys() if keys is None else (k for k in keys if k in parsed)
    result: dict[str, str] = {}
    for key in selected:
        value = parsed[key]
        if isinstance(value, str):
            result[str(key)] = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            result[str(key)] = str(value)
    return result


def _extract_by_keys(text: str, keys: Sequence[str] | None) -> dict[str, str]:
    """Fallback: individua ``"chiave": "valore"`` anche con JSON malformato."""
    if keys is None:
        keys = list(dict.fromkeys(_KEY_LINE_RE.findall(text)))
    if not keys:
        raise JsonRepairError("nessuna chiave riconoscibile", text)

    positions = _key_positions(text, keys)
    if not positions:
        raise JsonRepairError("nessuna delle chiavi attese è presente", text)

    result: dict[str, str] = {}
    for index, (key, _, value_start) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        result[key] = _decode_value(text[value_start:end])
    return result


def _key_positions(text: str, keys: Sequence[str]) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    for key in keys:
        pattern = r"""["']?""" + re.escape(key) + r"""["']?\s*:\s*["']"""
        match = re.search(pattern, text)
        if match:
            found.append((key, match.start(), match.end()))
    return sorted(found, key=lambda item: item[1])


def _decode_value(chunk: str) -> str:
    value = _trim_chunk(chunk)
    escaped = escape_unescaped_quotes(value)
    escaped = escaped.replace("\n", "\\n").replace("\r", "\\r")
    try:
        return json.loads('"' + escaped + '"')
    except json.JSONDecodeError:
        return (
            value.replace('\\"', '"')
            .replace("\\\\", "\\")
            .replace("\\n", "\n")
            .replace("\\t", "\t")
        )


def _trim_chunk(chunk: str) -> str:
    """Ritaglia il valore fino alla virgoletta di chiusura, scartando la struttura."""
    value = chunk.strip()
    if value.endswith(","):
        value = value[:-1].rstrip()
    last_quote = value.rfind('"')
    if last_quote != -1:
        trailing = value[last_quote + 1:].strip()
        if not trailing or set(trailing) <= {",", "}"}:
            value = value[: last_quote + 1]
    value = value.strip()
    if value.startswith('"'):
        value = value[1:]
    if value.endswith('"'):
        value = value[:-1]
    return value
