"""Font: risoluzione dei font da usare nel PDF tradotto.

Espone solo il necessario: ``FontResolver`` per la cascata, ``platform_fonts`` per i
percorsi di sistema e ``fitz_adapter`` per l'integrazione con PyMuPDF.
"""

from .platform_fonts import classify, resolve_path, system_font_paths
from .resolver import FontResolver, ResolverStats

__all__ = ["FontResolver", "ResolverStats", "classify", "resolve_path", "system_font_paths"]
