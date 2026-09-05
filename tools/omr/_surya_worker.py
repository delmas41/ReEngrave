"""Surya margin-label worker — runs INSIDE .venv-surya, not in the repo's Python.

surya-ocr needs Python >= 3.10 and pulls torch + transformers; the host is 3.9
and the backend image has no business carrying a second vision stack. So the
reader runs out of process and talks JSON, the same shape `_omrned_worker.py`
uses for musicdiff and `maestro_bridge.py` for node.

NOTHING IN THE REPO MAY IMPORT THIS MODULE. It is executed as a standalone
script by an interpreter that has surya but NOT this project's dependencies.
Keep it free of `tools.*` imports.

Protocol — one JSON job on stdin, one JSON result on stdout:

    {"systems": [{"png_b64": "...", "staff_indices": [0, 1, 2],
                  "tick_ys": [40.0, 120.0, 200.0], "gutter_px": 70}]}

ONE PROCESS FOR THE WHOLE PAGE. Surya auto-spawns a llama.cpp server and loads a
650M GGUF on first use, which dominates everything else — about 70 s against
1.5 s per system afterwards. So every system on the page goes in one job.
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
from html import unescape

# Blocks whose centre is further than this fraction of the tick spacing from
# every tick are dropped. The crop reaches past the staves at top and bottom, so
# a page header read as an instrument is a real risk, and a wrong instrument is
# worse than none — it propagates through slots into a wrong clef.
_TOLERANCE = 0.5


def _text_of(block) -> str:
    """Surya 2 returns each block's content as HTML, not a plain string.

    A label arrives as `<p>Flauti</p>` and a two-line one carries a `<br>`, so
    tags become spaces rather than being deleted — else "Clarinetti<br>in C"
    reads as "Clarinettiin C" and the lexicon misses it.
    """
    html = getattr(block, "html", None) or getattr(block, "raw_label", "") or ""
    return unescape(re.sub(r"<[^>]+>", " ", html)).replace("\xa0", " ").strip()


def _lines_with_boxes(predictor, image) -> list[tuple[str, float, float, float]]:
    """`(text, y_centre, x_left, height)` for every block Surya reads.

    `full_page=True` is not optional: without it the predictor looks for layout
    regions, finds none on a bare margin strip, and returns nothing at all.

    `height` (the polygon's own y-extent) exists for `_assign`'s runaway-block
    gate below — Surya's layout step occasionally fails to segment a tall,
    dense margin at all and returns the WHOLE crop as one block, and only the
    block's own size says so; its y-centre looks like an ordinary label.
    """
    out: list[tuple[str, float, float, float]] = []
    for page in predictor([image], full_page=True):
        for block in getattr(page, "blocks", []) or []:
            if getattr(block, "skipped", False) or getattr(block, "error", None):
                continue
            text = _text_of(block)
            polygon = getattr(block, "polygon", None)
            if not text or not polygon:
                continue
            ys = [point[1] for point in polygon]
            xs = [point[0] for point in polygon]
            out.append((text, (min(ys) + max(ys)) / 2.0, min(xs), max(ys) - min(ys)))
    return out


def _lines(predictor, image) -> list[tuple[str, float, float]]:
    """`(text, y_centre, height)` — the margin reader's view, which needs no x."""
    return [(text, y, h) for text, y, _x, h in _lines_with_boxes(predictor, image)]


#: A block taller than this fraction of the WHOLE SYSTEM's tick span cannot be
#: one staff's label — measured on the two known runaway cases (Beethoven 5 /
#: imslp-575951 p.58, Mahler 5 p.163) against every correctly-split block on
#: Boléro's dense pages (`benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md`):
#: a real label's block, even a wrapped two-line one, never exceeds a small
#: fraction of the span it sits in, while Surya's failure mode is the ENTIRE
#: crop read as one block. See that file for the two populations.
_RUNAWAY_HEIGHT_FRACTION = 0.5


def _assign(lines, tick_ys, staff_indices) -> dict[int, str]:
    """Map each block to the staff whose tick it sits nearest.

    A block whose own height swallows most of the system's tick span is
    dropped outright, before the nearest-tick test — it is not a garbled
    READING of one staff's label, it is Surya's layout step failing to split
    the crop at all, and forcing it onto the nearest tick turns "the OCR did
    not segment" into "this staff plays the piccolo", a confident wrong
    instrument rather than an honest abstention.
    """
    if not tick_ys or len(tick_ys) != len(staff_indices):
        return {}
    span = max(tick_ys) - min(tick_ys) if len(tick_ys) > 1 else 0.0
    spacing = (span / (len(tick_ys) - 1)) if len(tick_ys) > 1 else float("inf")
    tolerance = spacing * _TOLERANCE
    height_cap = span * _RUNAWAY_HEIGHT_FRACTION if span else float("inf")

    per_staff: dict[int, list[tuple[float, str]]] = {}
    for text, y, height in lines:
        if height > height_cap:
            continue
        distances = [abs(y - t) for t in tick_ys]
        best = min(range(len(distances)), key=distances.__getitem__)
        if distances[best] > tolerance:
            continue
        per_staff.setdefault(staff_indices[best], []).append((distances[best], text))

    # A label wrapped over two lines ("Clarinetti" / "in C") lands as two blocks
    # on one staff; join them nearest-tick first so the instrument word leads.
    return {idx: " ".join(t for _, t in sorted(items))
            for idx, items in per_staff.items()}


def _read_crops(predictor, Image, crops: list[str]) -> list[dict]:
    """Plain OCR: one image in, its text out. No tick mapping.

    The second job this worker answers, added for `direction_text`. A margin
    crop holds a COLUMN of labels and has to be split by which staff each sits
    beside; a direction crop holds one word and has nothing to split. Sharing
    the process is the whole point — the 650M GGUF loads once either way, and
    it is the load that costs.

    Blocks are joined in READING order, top-to-bottom then left-to-right, so a
    phrase Surya breaks into two blocks (`espr.` / `e legato`) comes back as
    one string in the order it is printed.
    """
    out = []
    for b64 in crops:
        image = Image.open(io.BytesIO(base64.standard_b64decode(b64))).convert("RGB")
        try:
            lines = _lines_with_boxes(predictor, image)
        except Exception as exc:                            # noqa: BLE001
            out.append({"text": "", "error": f"{type(exc).__name__}: {exc}"})
            continue
        lines.sort(key=lambda item: (round(item[1] / 20.0), item[2]))
        out.append({"text": " ".join(text for text, _y, _x, _h in lines).strip()})
    return out


def main() -> int:
    job = json.load(sys.stdin)
    systems = job.get("systems") or []
    crops = job.get("crops")

    from PIL import Image                                  # noqa: PLC0415
    from surya.inference import SuryaInferenceManager      # noqa: PLC0415
    from surya.recognition import RecognitionPredictor     # noqa: PLC0415

    if crops is not None:
        predictor = RecognitionPredictor(SuryaInferenceManager())
        json.dump({"crops": _read_crops(predictor, Image, crops)}, sys.stdout)
        return 0

    if not systems:
        json.dump({"error": "no systems supplied"}, sys.stdout)
        return 2

    predictor = RecognitionPredictor(SuryaInferenceManager())

    results = []
    for system in systems:
        image = Image.open(io.BytesIO(
            base64.standard_b64decode(system["png_b64"]))).convert("RGB")
        gutter = int(system.get("gutter_px") or 0)
        # Crop the gutter off, or Surya reads the staff-index digits drawn in it
        # and every system gains a label called "7".
        margin = image.crop((gutter, 0, image.width, image.height))
        tick_ys = [float(y) for y in system.get("tick_ys") or []]
        staff_indices = [int(i) for i in system.get("staff_indices") or []]

        try:
            lines = _lines(predictor, margin)
        except Exception as exc:                            # noqa: BLE001
            results.append({"labels": {}, "raw_lines": [],
                            "error": f"{type(exc).__name__}: {exc}"})
            continue

        labels = _assign(lines, tick_ys, staff_indices)
        results.append({
            "labels": {str(k): v for k, v in sorted(labels.items())},
            # Kept because a mapping bug and an OCR failure are indistinguishable
            # in the label count, and only the raw text tells them apart. Height
            # rides along too: a block the runaway-height gate dropped is a
            # THIRD failure mode a bare text list can't tell from "OCR read
            # nothing here" or "assigned fine" — a mapping bug, an OCR miss, and
            # a rejected runaway all look identical in `labels` alone.
            "raw_lines": [{"text": t, "height": h} for t, _y, h in lines],
        })

    json.dump({"systems": results}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
