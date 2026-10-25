"""QA: report, controlli geometrici e di glifo.

Il QA **misura**, non corregge: nessun modulo qui deve modificare un PDF o una traduzione.
"""

from .checks_geometry import PositionedText, check_page_geometry, run_box
from .checks_glossary import check_glossary
from .checks_glyphs import check_page_glyphs
from .report import GATE_KINDS, gate, parse_report, report_path, write_report
from .textnorm import count_special, normalize, tokens

__all__ = [
    "GATE_KINDS",
    "PositionedText",
    "check_glossary",
    "check_page_geometry",
    "check_page_glyphs",
    "count_special",
    "gate",
    "normalize",
    "parse_report",
    "report_path",
    "run_box",
    "tokens",
    "write_report",
]
