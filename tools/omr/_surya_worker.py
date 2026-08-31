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


def _lines(predictor, image) -> list[tuple[str, float]]:
    """`(text, y_centre)` for every block Surya reads.

    `full_page=True` is not optional: without it the predictor looks for layout
    regions, finds none on a bare margin strip, and returns nothing at all.
    """
    out: list[tuple[str, float]] = []
    for page in predictor([image], full_page=True):
        for block in getattr(page, "blocks", []) or []:
            if getattr(block, "skipped", False) or getattr(block, "error", None):
                continue
            text = _text_of(block)
            polygon = getattr(block, "polygon", None)
            if not text or not polygon:
                continue
            ys = [point[1] for point in polygon]
            out.append((text, (min(ys) + max(ys)) / 2.0))
    return out


def _assign(lines, tick_ys, staff_indices) -> dict[int, str]:
    """Map each block to the staff whose tick it sits nearest."""
    if not tick_ys or len(tick_ys) != len(staff_indices):
        return {}
    spacing = ((max(tick_ys) - min(tick_ys)) / (len(tick_ys) - 1)
               if len(tick_ys) > 1 else float("inf"))
    tolerance = spacing * _TOLERANCE

    per_staff: dict[int, list[tuple[float, str]]] = {}
    for text, y in lines:
        distances = [abs(y - t) for t in tick_ys]
        best = min(range(len(distances)), key=distances.__getitem__)
        if distances[best] > tolerance:
            continue
        per_staff.setdefault(staff_indices[best], []).append((distances[best], text))

    # A label wrapped over two lines ("Clarinetti" / "in C") lands as two blocks
    # on one staff; join them nearest-tick first so the instrument word leads.
    return {idx: " ".join(t for _, t in sorted(items))
            for idx, items in per_staff.items()}


def main() -> int:
    job = json.load(sys.stdin)
    systems = job.get("systems") or []
    if not systems:
        json.dump({"error": "no systems supplied"}, sys.stdout)
        return 2

    from PIL import Image                                  # noqa: PLC0415
    from surya.inference import SuryaInferenceManager      # noqa: PLC0415
    from surya.recognition import RecognitionPredictor     # noqa: PLC0415

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
            # in the label count, and only the raw text tells them apart.
            "raw_lines": [t for t, _ in lines],
        })

    json.dump({"systems": results}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
