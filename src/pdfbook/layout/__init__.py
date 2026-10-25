"""Layout: segmentazione, allineamento, sillabazione e fitting tipografico.

Dipende da ``domain`` (geometria) e ``fonts`` (metriche), mai da ``rendering`` (R5).
"""

from .aligner import alignments_for, line_alignment, single_line_alignment
from .fitter import MIN_FONT_FRACTION, FitResult, estimate_max_chars, fit_text, wrap_text
from .hyphenation import Hyphenation
from .segmentation import (
    ROW_Y_TOLERANCE,
    classify_block,
    group_rows,
    has_multi_column_row,
    is_structured_block,
    toc_ratio,
)
from .toc import is_toc_line, optimize_toc_line

__all__ = [
    "MIN_FONT_FRACTION",
    "ROW_Y_TOLERANCE",
    "FitResult",
    "Hyphenation",
    "alignments_for",
    "classify_block",
    "estimate_max_chars",
    "fit_text",
    "group_rows",
    "has_multi_column_row",
    "is_structured_block",
    "is_toc_line",
    "line_alignment",
    "optimize_toc_line",
    "single_line_alignment",
    "toc_ratio",
    "wrap_text",
]
