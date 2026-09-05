#!/usr/bin/env python3
"""Runs INSIDE `.venv-surya`. Dumps every OCR block with its y and height.

`_surya_worker.py` returns `raw_lines` (text + height) but not the block's
y-centre, and the y-centre is the whole question for Phase 2 (ii): a name
engraved once across a braced pair sits BETWEEN two ticks, and `_assign` snaps
it to the nearer one. Designing that rule from the images rather than from the
blocks would be designing from an impression.

Must not import from `tools.*` — the venv has surya and nothing of this repo,
the same contract `_omrned_worker.py` and `_surya_worker.py` keep.

    stdin  {"systems": [{"png_b64", "staff_indices", "tick_ys", "gutter_px"}]}
    stdout {"systems": [{"blocks": [{"text", "y", "h", "x"}], "tick_ys": [...]}]}
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
from html import unescape


def _text_of(block) -> str:
    html = getattr(block, "html", None) or getattr(block, "raw_label", "") or ""
    return unescape(re.sub(r"<[^>]+>", " ", html)).replace("\xa0", " ").strip()


def main() -> int:
    from PIL import Image
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor

    job = json.load(sys.stdin)
    predictor = RecognitionPredictor(SuryaInferenceManager())
    out = []
    for system in job.get("systems", []):
        image = Image.open(io.BytesIO(base64.standard_b64decode(
            system["png_b64"]))).convert("RGB")
        gutter = int(system.get("gutter_px") or 0)
        margin = image.crop((gutter, 0, image.width, image.height))
        blocks = []
        for page in predictor([margin], full_page=True):
            for block in getattr(page, "blocks", []) or []:
                if getattr(block, "skipped", False) or getattr(block, "error", None):
                    continue
                text = _text_of(block)
                poly = getattr(block, "polygon", None)
                if not text or not poly:
                    continue
                ys = [p[1] for p in poly]
                xs = [p[0] for p in poly]
                blocks.append({"text": text, "y": (min(ys) + max(ys)) / 2.0,
                               "h": max(ys) - min(ys), "x": min(xs),
                               "y0": min(ys), "y1": max(ys)})
        out.append({"blocks": blocks, "tick_ys": system.get("tick_ys"),
                    "staff_indices": system.get("staff_indices")})
    json.dump({"systems": out}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
