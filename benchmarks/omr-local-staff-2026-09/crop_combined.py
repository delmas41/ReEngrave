#!/usr/bin/env python3
"""ROADMAP 2.54 -- crops every truth-set head where
`ledger_grid.combine_farhead_position`'s answer DIFFERS from plain
geometry, plus one contact sheet, for Sean to read.

Each tile (>= 600px tall): the head's box, the LOCAL staff lines
(`score_truth_set_rungs.frame_lines_for_head`, never the global/
extrapolated ones -- CLAUDE.md sec10), the rungs this head's own rung
reader found, and a text block naming the reference, geometry, rungs,
combined position and the branch taken.

MEASUREMENT ONLY -- writes PNGs under `out/print/ledgers/combined/` and
one contact sheet `out/print/ledgers/combined_sheet.png`.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import cv2

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import combined_scorer as cs  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers" / "combined"
SHEET_PATH = REPO / "out" / "print" / "ledgers" / "combined_sheet.png"

PAD_SPACES = 3.0
MIN_TILE_H = 600

RED = (0, 0, 220)        # the head's own box
GREEN = (60, 200, 60)    # local staff lines
ORANGE = (30, 140, 255)  # rungs found beside this head
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _crop_tile(gray, box, lines, rungs_y, spacing, texts):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    pad = PAD_SPACES * spacing
    cx0 = max(0, int(cx - 3.0 * spacing))
    cx1 = min(gray.shape[1], int(cx + 3.0 * spacing))
    cy0 = max(0, int(min(lines[0], y0) - pad))
    cy1 = min(gray.shape[0], int(max(lines[-1], y1) + pad))
    crop = cv2.cvtColor(gray[cy0:cy1, cx0:cx1], cv2.COLOR_GRAY2BGR)
    h, w = crop.shape[:2]
    scale = max(1, int(round(MIN_TILE_H / max(h, 1))))
    if scale > 1:
        crop = cv2.resize(crop, (w * scale, h * scale),
                          interpolation=cv2.INTER_NEAREST)

    def to_tile(px, py):
        return (int((px - cx0) * scale), int((py - cy0) * scale))

    for ly in lines:
        p0 = to_tile(cx0, ly)
        p1 = to_tile(cx1, ly)
        cv2.line(crop, p0, p1, GREEN, 1)
    for ry in rungs_y:
        p0 = to_tile(cx0, ry)
        p1 = to_tile(cx1, ry)
        cv2.line(crop, p0, p1, ORANGE, 2)
    tl = to_tile(x0, y0)
    br = to_tile(x1, y1)
    cv2.rectangle(crop, tl, br, RED, 2)

    legend_h = 24 * (len(texts) + 1)
    out = np.full((h * scale + legend_h, w * scale, 3), 255, dtype=np.uint8)
    out[:h * scale] = crop
    for i, t in enumerate(texts):
        cv2.putText(out, t, (6, h * scale + 20 + i * 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, BLACK, 1, cv2.LINE_AA)
    return out


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tiles = []
    for doc_id in ts.DOCS:
        r = cs.score_doc(doc_id)
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        boxes_by_page = score._notehead_boxes_by_page(rec)
        rows_by_sub = {row["subject"]: row for row in score._far_head_rows(doc_id, loaded)}

        for h in r["per_head"]:
            if h["combined_pos"] == h["geom_pos"]:
                continue  # unchanged from plain geometry -- not of interest
            row = rows_by_sub[h["subject"]]
            box = row["page_box"]
            staff_key = row["staff_key"]
            line_rows = rec.obs(Q.STAFF_LINES, staff_key)
            global_lines = [float(y) for y in line_rows[-1]["value"]]
            gray = pages.get(row["page"])
            lines = score.frame_lines_for_head(gray, global_lines, box)
            spacing = (max(lines) - min(lines)) / 4.0
            page_boxes = boxes_by_page.get(row["page"], [])
            rungs_y, _spacing, _side = cs._rungs_y_for_head(
                gray, lines, box, row["subject"], page_boxes)

            name = f"{doc_id}__{row['subject'].replace('/', '_')}"
            texts = [
                f"{doc_id}  {row['subject']}",
                f"reference: {h['truth_pos']}   geometry: {h['geom_pos']}"
                f" ({'right' if h['v_geom']=='right' else 'wrong'})",
                f"rungs: {h['rungs_pos']} ({h['v_rungs']})   "
                f"max_gap_dev: {h['max_gap_deviation']}",
                f"COMBINED: {h['combined_pos']} ({h['v_combined']})   "
                f"branch: {h['branch']}",
            ]
            tile = _crop_tile(gray, box, lines, rungs_y, spacing, texts)
            cv2.imwrite(str(OUT_DIR / f"{name}.png"), tile)
            tiles.append((name, tile, h))
            print(f"wrote {name}.png  branch={h['branch']} "
                 f"geom={h['v_geom']} combined={h['v_combined']}")

    if not tiles:
        print("no heads differ from plain geometry -- nothing to sheet")
        return

    cols = 3
    rows_n = (len(tiles) + cols - 1) // cols
    tile_w = max(t[1].shape[1] for t in tiles)
    tile_h = max(t[1].shape[0] for t in tiles)
    sheet = np.full((rows_n * tile_h, cols * tile_w, 3), 255, dtype=np.uint8)
    for i, (name, tile, h) in enumerate(tiles):
        r, c = divmod(i, cols)
        th, tw = tile.shape[:2]
        sheet[r * tile_h:r * tile_h + th, c * tile_w:c * tile_w + tw] = tile
    cv2.imwrite(str(SHEET_PATH), sheet)
    print(f"wrote {SHEET_PATH} ({len(tiles)} tiles)")


if __name__ == "__main__":
    build()
