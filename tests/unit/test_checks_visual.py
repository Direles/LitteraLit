"""Test dei controlli visivi (Fase 0): SSIM mascherato, mappa dell'inchiostro."""

import unittest

from pdfbook.domain.models import IssueKind, Rect
from pdfbook.qa.checks_visual import (
    MAX_INK_RATIO,
    MIN_GRAPHICS_SSIM,
    PageImage,
    check_page_visual,
    ink_density,
    ssim,
    tile_ink,
)


def uniform(width=32, height=32, value=255, pt_width=100.0):
    return PageImage(pixels=bytes([value]) * (width * height), width=width, height=height, pt_width=pt_width)


def with_block(width=32, height=32, box=None, value=0, pt_width=100.0):
    """Immagine bianca con un rettangolo nero (coordinate in pixel)."""
    data = bytearray([255]) * (width * height)
    x0, y0, x1, y1 = box or (0, 0, width // 2, height // 2)
    for y in range(y0, min(y1, height)):
        for x in range(x0, min(x1, width)):
            data[y * width + x] = value
    return PageImage(pixels=bytes(data), width=width, height=height, pt_width=pt_width)


class PageImageTest(unittest.TestCase):
    def test_rejects_empty_dimensions(self):
        with self.assertRaises(ValueError):
            PageImage(pixels=b"", width=0, height=10)

    def test_rejects_short_buffer(self):
        with self.assertRaises(ValueError):
            PageImage(pixels=b"\x00" * 10, width=32, height=32)

    def test_pixel_access(self):
        image = with_block(8, 8, box=(0, 0, 4, 4))
        self.assertEqual(image.at(0, 0), 0)
        self.assertEqual(image.at(7, 7), 255)


class InkTest(unittest.TestCase):
    def test_white_page_has_no_ink(self):
        self.assertEqual(ink_density(uniform()), 0.0)

    def test_black_page_is_full_ink(self):
        self.assertEqual(ink_density(uniform(value=0)), 1.0)

    def test_half_block(self):
        image = with_block(32, 32, box=(0, 0, 32, 16))
        self.assertAlmostEqual(ink_density(image, step=1), 0.5, places=2)

    def test_tiles_are_row_major(self):
        image = with_block(40, 40, box=(0, 0, 20, 20))
        tiles = tile_ink(image, grid=2)
        self.assertEqual(len(tiles), 4)
        self.assertGreater(tiles[0], 0.9)
        self.assertLess(tiles[1], 0.01)
        self.assertLess(tiles[3], 0.01)


class SsimTest(unittest.TestCase):
    def test_identical_images(self):
        self.assertAlmostEqual(ssim(uniform(), uniform()), 1.0, places=4)

    def test_different_images_score_lower(self):
        score = ssim(uniform(), with_block())
        self.assertLess(score, 0.9)

    def test_mask_ignores_changed_area(self):
        base = uniform(32, 32)
        changed = with_block(32, 32, box=(0, 0, 32, 32))
        box = Rect(0, 0, 100, 100)  # copre tutta la pagina (pt_width=100)
        self.assertAlmostEqual(ssim(base, changed, mask=[box]), 1.0, places=4)

    def test_size_mismatch_raises(self):
        with self.assertRaises(ValueError):
            ssim(uniform(32, 32), uniform(16, 16))

    def test_fully_masked_page_is_neutral(self):
        self.assertEqual(ssim(uniform(), with_block(), mask=[Rect(0, 0, 100, 100)]), 1.0)


class CheckPageTest(unittest.TestCase):
    def test_identical_pages_have_no_issues(self):
        self.assertEqual(check_page_visual(1, uniform(), uniform()), [])

    def test_graphics_change_is_flagged(self):
        issues = check_page_visual(2, uniform(), with_block(box=(0, 0, 32, 32)))
        self.assertIn(IssueKind.VISUAL_DRIFT, [issue.kind for issue in issues])

    def test_text_area_change_is_not_a_graphics_issue(self):
        original = uniform(32, 32)
        rendered = with_block(32, 32, box=(2, 2, 28, 28))
        issues = check_page_visual(
            3, original, rendered, text_boxes=[Rect(0, 0, 90, 90)]
        )
        self.assertEqual([issue for issue in issues if issue.kind is IssueKind.VISUAL_DRIFT], [])

    def test_lost_ink_in_a_tile_is_missing_text(self):
        original = with_block(40, 40, box=(0, 0, 40, 20))
        issues = check_page_visual(4, original, uniform(40, 40, pt_width=100.0))
        self.assertIn(IssueKind.TEXT_MISSING, [issue.kind for issue in issues])

    def test_size_mismatch_is_flagged(self):
        issues = check_page_visual(5, uniform(32, 32), uniform(16, 16))
        self.assertEqual(issues[0].kind, IssueKind.VISUAL_DRIFT)
        self.assertIn("dimensioni", issues[0].detail)

    def test_thresholds_are_declared(self):
        self.assertAlmostEqual(MIN_GRAPHICS_SSIM, 0.98)
        self.assertGreater(MAX_INK_RATIO, 1.0)

    def test_issues_are_capped(self):
        original = with_block(80, 80, box=(0, 0, 80, 80))
        issues = check_page_visual(6, original, uniform(80, 80))
        self.assertLessEqual(len(issues), 6)


if __name__ == "__main__":
    unittest.main()
