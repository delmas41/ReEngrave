#!/usr/bin/env python3
"""ROADMAP 2.44 lane (`lane-2.44-first-two-stages`) print check: for every
scored far head where geometry, reader 1 (`LEDGER_CLEAN_COUNT`), reader 2
(`LEDGER_RUNG_GRID`) and option B disagree, cut a crop at the gather's own
DPI with the subject head bracketed (RED box) and each candidate's own
staff position drawn as a tick, legend in the image:

  CYAN   = geometry (today's `Q.NOTEHEAD_STAFF_POSITION` rounding)
  MAGENTA = reader 1 (count-the-clean-ledgers)
  GREEN  = reader 2 (`measure_ledger_rungs` grid)
  ORANGE = local geometry (two flanking column re-fit, ROADMAP 2.44c)
  YELLOW dashed = the reference's own truth pitch, for the same staff
          position, computed by inverting the clef the SAME way
          `_pitch_from_position` reads it forward

MEASUREMENT ONLY (CLAUDE.md §8): reads the committed small-re-gather
records this lane's own `truth_set_2_44c.py` already loaded; writes only
PNGs under `out/print/2.44/`. Run from the repo root:

    python3 -m benchmarks.omr-ledger-extrapolation-2026-09.crop_disagreements_2_44
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import fitz  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tools.omr.staged import export as EXP  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.pitch_resolver import _pitch_from_position  # noqa: E402

import json  # noqa: E402

HERE = Path(__file__).resolve().parent
DOCS_JSON_MODULE = "benchmarks.omr-ledger-extrapolation-2026-09.truth_set_2_44c"
import importlib  # noqa: E402
TS = importlib.import_module(DOCS_JSON_MODULE)

OUT_DIR = REPO / "out/print/2.44"

# (doc_id, subject) picked from the truth-set's own disagreement scan --
# every row here is SCORED (truth known) and has >=2 distinct candidate
# pitches among {geometry, reader1, reader2, option B, local geometry}.
# Includes Sean's two named chords (`glyph/3/0/0/2/{1,3,4,9}`, DECISIONS
# 2026-09-30) plus the richest other disagreements on each document.
PICKS = [
    ("beethoven5-litolff", "glyph/1/0/3/7/3"),
    ("beethoven5-litolff", "glyph/3/0/0/2/1"),
    ("beethoven5-litolff", "glyph/3/0/0/2/3"),
    ("beethoven5-litolff", "glyph/3/0/0/2/4"),
    ("beethoven5-litolff", "glyph/3/0/0/2/9"),
    ("beethoven5-litolff", "glyph/3/0/0/7/1"),
    ("beethoven5-litolff", "glyph/1/0/10/8/1"),
    ("brahms1-breitkopf", "glyph/1/1/0/4/0"),
]

COLORS = {
    "geometry": (0, 220, 220),
    "reader1": (230, 0, 230),
    "reader2": (0, 200, 0),
    "local_geometry": (255, 140, 0),
}


def _font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except Exception:
        return ImageFont.load_default()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    loaded = {}
    rows_by_doc = {}
    for doc_id in TS.DOCS:
        loaded[doc_id] = TS.load_doc(doc_id)
        rows_by_doc[doc_id] = {r["subject"]: r
                               for r in TS.build_rows(doc_id, loaded[doc_id])}

    made = []
    for doc_id, sub in PICKS:
        cfg = TS.DOCS[doc_id]
        L = loaded[doc_id]
        rec: EXP.Record = L["rec"]
        row = rows_by_doc[doc_id].get(sub)
        if row is None:
            print(f"SKIP {doc_id} {sub}: not a far head in this gather")
            continue
        parts = sub.split("/")
        page, system, staff_i, cell, glyph_i = (int(x) for x in parts[1:6])
        staff_key = f"staff/{page}/{system}/{staff_i}"
        clef_v = rec.value(Q.CLEF, staff_key)
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        if not line_rows or clef_v is None or not row.get("page_box"):
            print(f"SKIP {doc_id} {sub}: missing staff lines / clef / box")
            continue
        global_lines = sorted(float(y) for y in line_rows[-1]["value"])
        top = global_lines[0]
        half = (global_lines[-1] - top) / 8.0   # 4 half-steps per line gap
        px0, py0, px1, py1 = row["page_box"]
        cx = (px0 + px1) / 2.0

        def y_of_pos(pos_steps: float) -> float:
            return top + pos_steps * half

        def pos_of_pitch(name: Optional[str]) -> Optional[float]:
            if not name:
                return None
            # invert `_pitch_from_position` by scanning the small integer
            # range any far head lives in -- cheap, exact (no algebraic
            # inverse is exposed, and none is needed for a +-20 step scan).
            for p in range(-30, 31):
                if _pitch_from_position(p, str(clef_v)) == name:
                    return p
            return None

        ticks = []
        for key, pitch_field in (("geometry", "geom_pitch"),
                                 ("reader1", "r1_pitch"),
                                 ("reader2", "r2_pitch"),
                                 ("local_geometry", "local_pitch")):
            pitch = row.get(pitch_field)
            if not pitch:
                continue
            pos = pos_of_pitch(pitch)
            if pos is None:
                continue
            ticks.append((key, pitch, y_of_pos(pos)))

        truth = row.get("truth_pitches") or []
        truth_label = "/".join(f"{l}{o}" for l, o in truth) if truth else "?"

        pdf_path = cfg["pdf"]
        doc = fitz.open(str(pdf_path))
        pm = doc[cfg["pdf_page_index"]].get_pixmap(dpi=cfg["dpi"])
        img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples).convert("RGB")
        doc.close()

        wy0 = int(min([top] + [t[2] for t in ticks] + [py0]) - 6 * half)
        wy1 = int(max([global_lines[-1]] + [t[2] for t in ticks] + [py1]) + 6 * half)
        wx0 = int(cx - 14 * half)
        wx1 = int(cx + 14 * half)
        wx0, wy0 = max(0, wx0), max(0, wy0)
        wx1, wy1 = min(img.width, wx1), min(img.height, wy1)
        crop = img.crop((wx0, wy0, wx1, wy1)).convert("RGB")
        scale = 3
        crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
        draw = ImageDraw.Draw(crop)

        def X(x):
            return (x - wx0) * scale

        def Y(y):
            return (y - wy0) * scale

        for gy in global_lines:
            draw.line([(X(wx0), Y(gy)), (X(wx1), Y(gy))], fill=(160, 160, 160), width=1)

        draw.rectangle([X(px0) - 2, Y(py0) - 2, X(px1) + 2, Y(py1) + 2],
                       outline=(255, 0, 0), width=3)

        legend_y = 6
        font = _font(16)
        for key, pitch, y in ticks:
            color = COLORS[key]
            draw.line([(X(wx0), Y(y)), (X(wx1), Y(y))], fill=color, width=2)
            po = _our_letter_octave(pitch)
            right = bool(truth) and po in truth
            mark = "RIGHT" if right else ("WRONG" if truth else "?")
            draw.text((6, legend_y), f"{key}: {pitch} ({mark})", fill=color, font=font)
            legend_y += 18
        draw.text((6, legend_y), f"print truth: {truth_label}",
                  fill=(255, 215, 0), font=font)

        safe = sub.replace("/", "-")
        out_path = OUT_DIR / f"{doc_id}-{safe}.png"
        crop.save(out_path)
        made.append(out_path)
        print(f"wrote {out_path}  truth={truth_label}  "
             f"candidates={[(k, p) for k, p, _ in ticks]}")

    print(f"{len(made)} crops written to {OUT_DIR}")
    return 0


def _our_letter_octave(name: str) -> Optional[Tuple[str, int]]:
    letter = name[0]
    rest = name[1:]
    i = 0
    while i < len(rest) and rest[i] in "#b":
        i += 1
    try:
        return letter, int(rest[i:])
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
