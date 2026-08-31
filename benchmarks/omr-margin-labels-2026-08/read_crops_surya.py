#!/usr/bin/env python3
"""Stage 2, free tier: read the SAME margin crops with Surya 2 instead of Claude.

`read_crops.py` reads these crops with `claude-opus-5` and costs about a cent a
system. Surya 2 (datalab-to/surya, Apache-2.0 code) is a 650M OCR VLM that runs
locally on Apple Silicon through llama.cpp, so if it can read a margin the
per-page cost of instrument identity goes to zero. This scores it on exactly the
crops the paid reader was scored on, against exactly the same free ground truth.

    .venv-surya/bin/python benchmarks/omr-margin-labels-2026-08/read_crops_surya.py

THE HARD PART IS NOT THE OCR, IT IS THE ROW ASSIGNMENT. Claude is handed the
crop with a numbered gutter and asked to key its answer to those numbers, which
an OCR engine cannot do — it returns text and boxes, not answers. So the gutter
is measured out of the image instead: it is filled a flat 232 grey, each staff
carries a black tick at its vertical centre near the gutter's right edge, and
`crop.staff_indices` in the manifest lists those staves top to bottom. Finding
the ticks and zipping them against that list recovers the mapping without
re-running staff detection.

The gutter is then CROPPED OFF before OCR, or Surya reads the index digits as
text and every system gains a label called "7".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html import unescape
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent

# The gutter is drawn at a flat 232; the page beside it is near-white. Anything
# darker than this is ink — a tick or an index digit.
_GREY = 232
_GREY_TOL = 6
_INK = 100


def find_gutter_width(arr: np.ndarray) -> int:
    """Width of the grey gutter in pixels, measured rather than assumed.

    `staff_labels_vision.GUTTER_PX` is 70, but a crop taller than MAX_EDGE_PX is
    downscaled on the way out, and the gutter with it, so the constant is only
    right for crops that escaped the resize.
    """
    grey = np.abs(arr.astype(int) - _GREY).max(axis=2) <= _GREY_TOL
    # A gutter column is mostly grey; the page column beside it is mostly white.
    frac = grey.mean(axis=0)
    cols = np.flatnonzero(frac > 0.5)
    if cols.size == 0:
        return 0
    # Take the leading run so a grey smudge on the page cannot extend it.
    width = 1
    while width < cols.size and cols[width] == cols[width - 1] + 1:
        width += 1
    return int(cols[width - 1]) + 1


def find_tick_rows(arr: np.ndarray, gutter: int) -> list[float]:
    """Y centre of each staff tick, top to bottom.

    Ticks are drawn in the gutter's right-hand edge and the index digits at its
    far left, so restricting to the right 30% separates them.
    """
    if gutter <= 0:
        return []
    band = arr[:, max(0, int(gutter * 0.7)):gutter]
    dark = (band.astype(int).max(axis=2) < _INK).any(axis=1)
    rows = np.flatnonzero(dark)
    if rows.size == 0:
        return []
    centres, run = [], [rows[0]]
    for y in rows[1:]:
        if y - run[-1] <= 2:
            run.append(y)
        else:
            centres.append(float(np.mean(run)))
            run = [y]
    centres.append(float(np.mean(run)))
    return centres


def _text_of(block) -> str:
    """Surya 2 returns each block's content as HTML, not a plain string.

    A margin label arrives as `<p>Flauti</p>` and a two-line one as a block
    carrying a `<br>`, so tags become spaces rather than being deleted — else
    "Clarinetti<br>in C" reads as "Clarinettiin C" and the lexicon misses it.
    """
    html = getattr(block, "html", None) or getattr(block, "raw_label", "") or ""
    text = re.sub(r"<[^>]+>", " ", html)
    return unescape(text).replace("\xa0", " ").strip()


def surya_lines(predictor, image: Image.Image) -> list[tuple[str, float]]:
    """`(text, y_centre)` for every block Surya reads, in the image's own pixels.

    `full_page=True` because the alternative is handing it layout results, and
    a margin strip has no layout to speak of — it is one column of short labels.
    Without it the predictor finds no regions and returns nothing at all.
    """
    predictions = predictor([image], full_page=True)
    out: list[tuple[str, float]] = []
    for page in predictions:
        for block in getattr(page, "blocks", []) or []:
            if getattr(block, "skipped", False) or getattr(block, "error", None):
                continue
            text = _text_of(block)
            if not text:
                continue
            polygon = getattr(block, "polygon", None)
            if not polygon:
                continue
            ys = [point[1] for point in polygon]
            out.append((text, (min(ys) + max(ys)) / 2.0))
    return out


def assign(lines: list[tuple[str, float]], ticks: list[float],
           staff_indices: list[int]) -> dict[int, str]:
    """Map each OCR line to the staff whose tick it sits nearest.

    A line further than half the tick spacing from every tick is dropped: the
    crop reaches past the staves at top and bottom, and a page header read as a
    label is worse than no label at all.
    """
    if not ticks or len(ticks) != len(staff_indices):
        return {}
    spacing = (max(ticks) - min(ticks)) / max(1, len(ticks) - 1)
    tolerance = spacing * 0.5

    per_staff: dict[int, list[tuple[float, str]]] = {}
    for text, y in lines:
        distances = [abs(y - t) for t in ticks]
        best = int(np.argmin(distances))
        if distances[best] > tolerance:
            continue
        per_staff.setdefault(staff_indices[best], []).append((distances[best], text))

    # A label wrapped over two lines ("Clarinetti" / "in C") lands as two lines
    # on one staff; join them in reading order, nearest tick first.
    return {idx: " ".join(t for _, t in sorted(items))
            for idx, items in per_staff.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops", default=str(HERE / "crops"))
    ap.add_argument("--out", default=str(HERE / "results-surya.json"))
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor

    crops = Path(args.crops)
    manifest = json.loads((crops / "manifest.json").read_text())
    if args.limit:
        manifest = manifest[: args.limit]

    manager = SuryaInferenceManager()
    predictor = RecognitionPredictor(manager)

    results, started = [], time.time()
    for entry in manifest:
        path = crops / entry["png"]
        image = Image.open(path).convert("RGB")
        arr = np.asarray(image)

        gutter = find_gutter_width(arr)
        ticks = find_tick_rows(arr, gutter)
        margin = image.crop((gutter, 0, image.width, image.height))

        t0 = time.time()
        try:
            lines = surya_lines(predictor, margin)
        except Exception as exc:                              # noqa: BLE001
            print(f"  surya failed on {entry['png']}: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        elapsed = time.time() - t0

        labels = assign(lines, ticks, entry["staff_indices"])
        results.append({
            "png": entry["png"],
            "labels": {str(k): v for k, v in sorted(labels.items())},
            "truth": entry["truth"],
            "diagnostics": {
                "gutter_px": gutter,
                "ticks_found": len(ticks),
                "staves_expected": len(entry["staff_indices"]),
                "ocr_lines": len(lines),
                "seconds": round(elapsed, 2),
                # Kept because a mapping bug and an OCR failure look identical
                # in the score, and only the raw text tells them apart.
                "raw_lines": [t for t, _ in lines],
            },
        })
        status = ("ok" if len(ticks) == len(entry["staff_indices"])
                  else f"TICKS {len(ticks)}!={len(entry['staff_indices'])}")
        print(f"  {entry['png']:52s} {len(labels):2d} labels  "
              f"{len(lines):2d} lines  {elapsed:5.1f}s  {status}")

    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"\n{len(results)} crops read in {time.time() - started:.0f}s "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
