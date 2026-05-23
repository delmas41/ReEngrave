"""Phase 1.1 — PDF rendering, binarization, deskewing.

Public surface:
    render_page(pdf_path, page_index, dpi=600) -> PageImage
    render_pdf(pdf_path, dpi=600) -> list[PageImage]
    binarize(rgb) -> binary image
    deskew(rgb, binary) -> (rgb_deskewed, binary_deskewed, angle_deg)

The PageImage returned from render_page() / render_pdf() is already
binarized and deskewed.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from skimage.filters import threshold_sauvola

from .types import PageImage


# ─── PDF rendering ───────────────────────────────────────────────────────────


def render_page(pdf_path: str | Path, page_index: int, dpi: int = 600) -> PageImage:
    """Render one page of a PDF to a high-DPI numpy array, then binarize +
    deskew."""
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)
    try:
        if page_index < 0 or page_index >= doc.page_count:
            raise IndexError(f"page_index {page_index} out of range (0..{doc.page_count - 1})")
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        # fitz Pixmap → numpy. Samples are in RGB order when alpha=False.
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 1:
            rgb = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        elif pix.n == 3:
            rgb = arr.copy()
        elif pix.n == 4:
            rgb = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
        else:
            raise RuntimeError(f"unexpected channel count {pix.n}")
    finally:
        doc.close()

    binary = binarize(rgb)
    rgb_d, binary_d, angle = deskew(rgb, binary)
    return PageImage(
        pdf_path=pdf_path,
        page_index=page_index,
        dpi=dpi,
        rgb=rgb_d,
        binary=binary_d,
        skew_correction_deg=angle,
    )


def render_pdf(pdf_path: str | Path, dpi: int = 600, max_pages: int | None = None) -> list[PageImage]:
    """Render every page of a PDF (or up to `max_pages`)."""
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)
    n = doc.page_count
    doc.close()
    end = min(n, max_pages) if max_pages else n
    return [render_page(pdf_path, i, dpi=dpi) for i in range(end)]


# ─── Binarization ────────────────────────────────────────────────────────────


def binarize(rgb: np.ndarray, window_size: int = 25, k: float = 0.2) -> np.ndarray:
    """Sauvola adaptive thresholding. Returns uint8 with 255=paper, 0=ink.

    Sauvola handles uneven illumination and yellowed paper much better than
    Otsu — important for scanned scores where some pages are darker than
    others.
    """
    if rgb.ndim == 3:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    else:
        gray = rgb

    # scikit-image's threshold_sauvola returns the threshold *map*, not a
    # mask. We compare pixel-wise to produce the binary image.
    thresh = threshold_sauvola(gray, window_size=window_size, k=k)
    binary = (gray > thresh).astype(np.uint8) * 255  # paper=255, ink=0
    return binary


# ─── Deskewing ───────────────────────────────────────────────────────────────


def deskew(rgb: np.ndarray, binary: np.ndarray, max_correction_deg: float = 5.0) -> tuple[np.ndarray, np.ndarray, float]:
    """Estimate page skew via Hough line detection on the binary image, then
    rotate both rgb and binary to correct it. Returns (rgb, binary, angle).

    The skew angle is detected from the longest horizontal-ish lines on the
    page (which should be staff lines). If no clear skew is detected (or it
    exceeds max_correction_deg), the page is returned unrotated.
    """
    h, w = binary.shape
    # Hough wants edge pixels; we have a binary where ink=0. Invert for cv2.
    edges = cv2.bitwise_not(binary)

    # Restrict Hough to nearly-horizontal lines: theta near pi/2.
    # Returns array of [rho, theta] rows.
    lines = cv2.HoughLines(
        edges,
        rho=1,
        theta=np.pi / 720,                  # 0.25° resolution
        threshold=int(w * 0.4),             # line must span ~40% of page width
        min_theta=np.pi / 2 - np.deg2rad(max_correction_deg),
        max_theta=np.pi / 2 + np.deg2rad(max_correction_deg),
    )

    if lines is None or len(lines) == 0:
        return rgb, binary, 0.0

    # Each line's theta is the angle of the normal from the origin to the
    # line. For a horizontal line, theta = pi/2; deviation from pi/2 is the
    # skew angle (in radians).
    angles_deg = [float(np.rad2deg(line[0][1] - np.pi / 2)) for line in lines]
    median_angle = float(np.median(angles_deg))

    if abs(median_angle) < 0.1:
        return rgb, binary, 0.0

    # Rotate both images. cv2.warpAffine fills new corners with the most
    # common edge color (paper, 255).
    M = cv2.getRotationMatrix2D((w / 2, h / 2), median_angle, 1.0)
    rgb_d = cv2.warpAffine(
        rgb, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    binary_d = cv2.warpAffine(
        binary, M, (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return rgb_d, binary_d, median_angle


# ─── CLI / smoke test ────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse, sys, os

    ap = argparse.ArgumentParser(description="Render + binarize + deskew a PDF page")
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("--page", type=int, default=0, help="Page index (0-based)")
    ap.add_argument("--dpi", type=int, default=600, help="Render DPI")
    ap.add_argument("--out", default=None, help="Output base path (writes <out>.rgb.png and <out>.bin.png)")
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    print(f"page {args.page}: {pi.width}x{pi.height} @ {args.dpi} DPI, skew corrected {pi.skew_correction_deg:.3f}°")

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        cv2.imwrite(f"{args.out}.rgb.png", cv2.cvtColor(pi.rgb, cv2.COLOR_RGB2BGR))
        cv2.imwrite(f"{args.out}.bin.png", pi.binary)
        print(f"wrote {args.out}.rgb.png and {args.out}.bin.png")
