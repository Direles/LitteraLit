"""Layer di traduzione: adapter, pipeline, memorie.

Solo esportazioni: l'implementazione vive nei moduli (R1).
"""

from .cache import CACHE_VERSION, TranslationCache, make_key
from .json_repair import JsonRepairError, escape_unescaped_quotes, parse_json_object

__all__ = [
    "CACHE_VERSION",
    "JsonRepairError",
    "TranslationCache",
    "escape_unescaped_quotes",
    "make_key",
    "parse_json_object",
]
