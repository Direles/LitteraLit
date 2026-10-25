"""Confronto visivo originale ↔ output (Fase 0).

Un paragone pixel-per-pixel originale/output **non** ha senso quando cambia la lingua:
i glifi sono diversi per definizione. Servono due metriche ortogonali, entrambe oneste:

1. **Fedeltà grafica**: SSIM calcolato *fuori* dalle aree di testo. Immagini e grafica
   devono restare identiche: se cambiano, qualcosa si è rotto nel rendering.
2. **Mappa dell'inchiostro**: densità di nero per riquadro. Dove c'era testo e non c'è
   più nulla, il testo è sparito; dove non c'era e ora c'è, è comparso qualcosa di
   indesiderato (riquadri, shift eccessivi).

Il modulo è puro: riceve immagini in scala di grigi come ``bytes``. Chi rende le pagine
è il canvas (``PageCanvas.snapshot``), quindi `qa` non dipende da PyMuPDF (R5).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from pdfbook.domain.models import IssueKind, QAIssue, Rect

__all__ = [
    "MAX_INK_RATIO",
    "MIN_GRAPHICS_SSIM",
    "MIN_INK_RATIO",
    "PageImage",
    "check_page_visual",
    "ink_density",
    "ssim",
    "tile_ink",
]

MIN_GRAPHICS_SSIM = 0.98
MIN_INK_RATIO = 0.55
MAX_INK_RATIO = 1.80
TILE_GRID = 4
TILE_EMPTY = 0.002
TILE_LOST_RATIO = 0.35
MASK_PADDING_PX = 2
MAX_ISSUES = 6


@dataclass(frozen=True)
class PageImage:
    """Pagina renderizzata in scala di grigi (un byte per pixel)."""

    pixels: bytes
    width: int
    height: int
    pt_width: float = 0.0
    stride: int = 0

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("immagine senza dimensioni")
        step = self.stride or self.width
        if len(self.pixels) < step * self.height:
            raise ValueError("buffer troppo piccolo per le dimensioni dichiarate")

    @property
    def row_stride(self) -> int:
        return self.stride or self.width

    def at(self, x: int, y: int) -> int:
        return self.pixels[y * self.row_stride + x]


def ink_density(image: PageImage, *, step: int = 2) -> float:
    """Frazione media di inchiostro (0 = foglio bianco, 1 = tutto nero)."""
    total = 0
    count = 0
    for value in _pixels(image, step):
        total += value
        count += 1
    return 0.0 if not count else 1.0 - total / (count * 255.0)


def tile_ink(image: PageImage, *, grid: int = TILE_GRID) -> list[float]:
    """Densità di inchiostro per riquadro, in ordine riga per riga."""
    if grid < 1:
        raise ValueError("grid deve essere >= 1")
    sums = [0] * (grid * grid)
    counts = [0] * (grid * grid)
    tile_w = image.width / grid
    tile_h = image.height / grid
    for y in range(image.height):
        row = min(int(y / tile_h), grid - 1)
        for x in range(image.width):
            index = row * grid + min(int(x / tile_w), grid - 1)
            sums[index] += image.at(x, y)
            counts[index] += 1
    return [1.0 - s / (c * 255.0) if c else 0.0 for s, c in zip(sums, counts, strict=True)]


def ssim(
    original: PageImage,
    rendered: PageImage,
    *,
    mask: Sequence[Rect] = (),
    step: int = 2,
) -> float:
    """SSIM globale (finestra unica) sulle aree non mascherate."""
    _require_same_size(original, rendered)
    bits = _mask(original, mask)
    count = total_a = total_b = total_aa = total_bb = total_ab = 0
    step = max(step, 1)
    for y in range(0, original.height, step):
        offset = y * original.row_stride
        for x in range(0, original.width, step):
            if bits is not None and bits[offset + x]:
                continue
            value_a = original.pixels[offset + x]
            value_b = rendered.pixels[offset + x]
            count += 1
            total_a += value_a
            total_b += value_b
            total_aa += value_a * value_a
            total_bb += value_b * value_b
            total_ab += value_a * value_b
    if count == 0:
        return 1.0
    mean_a = total_a / count
    mean_b = total_b / count
    var_a = max(total_aa / count - mean_a * mean_a, 0.0)
    var_b = max(total_bb / count - mean_b * mean_b, 0.0)
    covariance = total_ab / count - mean_a * mean_b
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    numerator = (2 * mean_a * mean_b + c1) * (2 * covariance + c2)
    denominator = (mean_a * mean_a + mean_b * mean_b + c1) * (var_a + var_b + c2)
    return 1.0 if denominator == 0 else max(min(numerator / denominator, 1.0), -1.0)


def check_page_visual(
    page_number: int,
    original: PageImage,
    rendered: PageImage,
    *,
    text_boxes: Sequence[Rect] = (),
    min_graphics_ssim: float = MIN_GRAPHICS_SSIM,
) -> list[QAIssue]:
    """Issue visive della pagina: grafica alterata, aree di testo vuote, inchiostro anomalo."""
    if (original.width, original.height) != (rendered.width, rendered.height):
        return [
            QAIssue(
                page=page_number,
                kind=IssueKind.VISUAL_DRIFT,
                detail=f"dimensioni pagina cambiate: {rendered.width}x{rendered.height} "
                f"invece di {original.width}x{original.height}",
            )
        ]
    issues: list[QAIssue] = []
    graphics = ssim(original, rendered, mask=text_boxes)
    if graphics < min_graphics_ssim:
        issues.append(
            QAIssue(
                page=page_number,
                kind=IssueKind.VISUAL_DRIFT,
                detail=f"grafica alterata fuori dal testo (SSIM {graphics:.3f} < {min_graphics_ssim:.2f})",
            )
        )
    issues.extend(_tile_issues(page_number, original, rendered, text_boxes))
    return issues[:MAX_ISSUES]


def _tile_issues(
    page_number: int,
    original: PageImage,
    rendered: PageImage,
    text_boxes: Sequence[Rect],
) -> list[QAIssue]:
    issues: list[QAIssue] = []
    for index, (before, after) in enumerate(
        zip(tile_ink(original), tile_ink(rendered), strict=True)
    ):
        if before >= TILE_EMPTY and after < before * TILE_LOST_RATIO:
            issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.TEXT_MISSING,
                    detail=f"riquadro {index}: inchiostro da {before:.3f} a {after:.3f}",
                )
            )
        elif not _tile_covered_by_text(index, original, text_boxes) and before < TILE_EMPTY <= after:
            issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.VISUAL_DRIFT,
                    detail=f"riquadro {index}: inchiostro inatteso ({after:.3f})",
                )
            )
    return issues


def _tile_covered_by_text(index: int, image: PageImage, boxes: Sequence[Rect]) -> bool:
    """``True`` se il centro del riquadro cade dentro un'area di testo prevista."""
    if not boxes or image.pt_width <= 0:
        return False
    row, column = divmod(index, TILE_GRID)
    center_x = (column + 0.5) * image.pt_width / TILE_GRID
    pt_height = image.pt_width * image.height / image.width
    center_y = (row + 0.5) * pt_height / TILE_GRID
    return any(
        box.x0 <= center_x <= box.x1 and box.y0 <= center_y <= box.y1 for box in boxes
    )


def _require_same_size(original: PageImage, rendered: PageImage) -> None:
    if (original.width, original.height) != (rendered.width, rendered.height):
        raise ValueError("le immagini devono avere le stesse dimensioni")


def _pixels(image: PageImage, step: int) -> Iterator[int]:
    step = max(step, 1)
    for y in range(0, image.height, step):
        offset = y * image.row_stride
        for x in range(0, image.width, step):
            yield image.pixels[offset + x]


def _mask(image: PageImage, boxes: Sequence[Rect]) -> bytearray | None:
    """Maschera sui pixel (1 = escluso dal confronto) per le aree di testo."""
    if not boxes:
        return None
    bits = bytearray(image.row_stride * image.height)
    scale = image.width / image.pt_width if image.pt_width > 0 else 1.0
    for box in boxes:
        x0 = max(int((box.x0 - MASK_PADDING_PX) * scale), 0)
        x1 = min(int((box.x1 + MASK_PADDING_PX) * scale), image.width - 1)
        y0 = max(int((box.y0 - MASK_PADDING_PX) * scale), 0)
        y1 = min(int((box.y1 + MASK_PADDING_PX) * scale), image.height - 1)
        if x1 < x0 or y1 < y0:
            continue
        for y in range(y0, y1 + 1):
            start = y * image.row_stride + x0
            bits[start: start + (x1 - x0 + 1)] = b"\x01" * (x1 - x0 + 1)
    return bits
