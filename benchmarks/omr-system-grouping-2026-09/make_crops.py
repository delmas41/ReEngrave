#!/usr/bin/env python3
"""Adjudication artifacts for a set of (pdf, page) rows: a left-margin crop,
and optionally a full-page detection overlay.

Systems are adjudicated by counting LEFT BRACKETS on a margin crop, never
from whole-page thumbnails — at thumbnail scale a bracket-GROUP gap (winds |
brass | strings) looks exactly like a system break (see repo-state.md §2.1,
eval_grouping.py's own GT-method note). This script exists to make that crop
cheaply, for whatever page list the sweep/anomaly step hands it.

Re-renders and re-runs `detect_staves` fresh for each row (cheap — a few
hundred ms) rather than trying to reconstruct full `Staff` objects from
sweep.jsonl's stored geometry dicts, since the overlay needs full `line_ys`
and this keeps one code path for both crop and overlay.

Usage:
    python3 make_crops.py --input anomaly_shortlist.json
    python3 make_crops.py --input sweep.jsonl --cap 20 --overlay
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]
sys.path.insert(0, str(WORKTREE_ROOT))
sys.path.insert(0, str(HERE))

import cv2  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.types import PageWithStaves  # noqa: E402
from tools.omr.visualize import draw_overlay  # noqa: E402

import sweep as sweep_mod  # noqa: E402  (LIBRARY_ROOT, compute_render_params)

DEFAULT_OUT_DIR = HERE / "crops"
MARGIN_MAX_WIDTH_FRAC = 0.45
MARGIN_REACH_SPACINGS = 10.0
MARGIN_MAX_HEIGHT_PX = 2400
UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize(s: str) -> str:
    return UNSAFE_CHARS.sub("_", s or "unknown")


def load_rows(input_path: Path):
    """Accepts a JSON array of row dicts, or a JSONL file (one dict/line, as
    sweep.jsonl is). Each row needs `pdf_rel`-or-`pdf` and `page`; `dpi` is
    reused if present, else recomputed."""
    text = input_path.read_text()
    rows = None
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            rows = obj
        elif isinstance(obj, dict) and "rows" in obj:
            rows = obj["rows"]
    except json.JSONDecodeError:
        pass
    if rows is None:  # JSONL
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return rows


def resolve_pdf_path(row: dict) -> Path:
    raw = row.get("pdf") or row.get("pdf_rel")
    p = Path(raw)
    if p.is_absolute():
        return p
    return sweep_mod.LIBRARY_ROOT / raw


def margin_crop_gray(pi, staves):
    h, w = pi.height, pi.width
    if staves:
        min_x_start = min(s.x_start for s in staves)
        spacings = [s.line_spacing_px for s in staves if s.line_spacing_px and s.line_spacing_px > 0]
        median_spacing = statistics.median(spacings) if spacings else 20.0
        x1 = int(round(min_x_start + MARGIN_REACH_SPACINGS * median_spacing))
    else:
        x1 = int(round(MARGIN_MAX_WIDTH_FRAC * w))
    x1 = max(1, min(x1, int(round(MARGIN_MAX_WIDTH_FRAC * w)), w))

    crop_rgb = pi.rgb[:, 0:x1]
    gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    if gray.shape[0] > MARGIN_MAX_HEIGHT_PX:
        scale = MARGIN_MAX_HEIGHT_PX / gray.shape[0]
        new_w = max(1, int(round(gray.shape[1] * scale)))
        gray = cv2.resize(gray, (new_w, MARGIN_MAX_HEIGHT_PX), interpolation=cv2.INTER_AREA)
    return gray


def process_row(row: dict, out_dir: Path, overlay: bool):
    pdf_path = resolve_pdf_path(row)
    page = row["page"]
    dpi = row.get("dpi")
    if not dpi:
        import fitz
        doc = fitz.open(pdf_path)
        try:
            rect = doc[page].rect
        finally:
            doc.close()
        dpi, _ = sweep_mod.compute_render_params(rect.width, rect.height)

    pub_token = _sanitize(row.get("publisher_token") or "unknown")
    pdf_stem = _sanitize(pdf_path.stem)
    base = f"{pub_token}--{pdf_stem}--p{page:03d}"

    pi = render_page(pdf_path, page, dpi=dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)

    out_dir.mkdir(parents=True, exist_ok=True)
    margin_path = out_dir / f"{base}-margin.png"
    cv2.imwrite(str(margin_path), margin_crop_gray(pi, staves))

    overlay_path = None
    if overlay:
        bgr = draw_overlay(PageWithStaves(page=pi, staves=staves))
        overlay_path = out_dir / f"{base}-overlay.png"
        cv2.imwrite(str(overlay_path), bgr)

    return margin_path, overlay_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True, help="JSON array or JSONL of row dicts (pdf/pdf_rel, page, [dpi, publisher_token])")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--overlay", action="store_true")
    ap.add_argument("--cap", type=int, default=60)
    args = ap.parse_args()

    rows = load_rows(args.input)
    if args.cap:
        rows = rows[: args.cap]
    print(f"{len(rows)} rows to crop (cap={args.cap})")

    n_ok = n_err = 0
    for i, row in enumerate(rows):
        try:
            margin_path, overlay_path = process_row(row, args.out_dir, args.overlay)
            n_ok += 1
            msg = f"  [{i+1}/{len(rows)}] {margin_path.name}"
            if overlay_path:
                msg += f" + {overlay_path.name}"
            print(msg)
        except Exception as exc:  # noqa: BLE001
            n_err += 1
            print(f"  [{i+1}/{len(rows)}] ERROR {row.get('pdf_rel') or row.get('pdf')} "
                  f"p{row.get('page')}: {type(exc).__name__}: {exc}", file=sys.stderr)

    print(f"done: {n_ok} ok, {n_err} error, wrote to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
