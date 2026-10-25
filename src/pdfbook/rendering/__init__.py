"""Rendering: dal testo tradotto al PDF.

Il layer disegna soltanto: le decisioni tipografiche sono in ``layout``, le metriche in
``fonts``, i problemi rilevati diventano ``QAIssue`` (``qa``).
"""

from .canvas import PageCanvas, TextRun
from .colors import rgb_from_int
from .vector_renderer import PageRenderResult, VectorRenderer

__all__ = ["PageCanvas", "PageRenderResult", "TextRun", "VectorRenderer", "rgb_from_int"]
