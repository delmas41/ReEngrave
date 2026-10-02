#!/usr/bin/env python3
"""Sean's request (2026-10-01, mid-lane-farhead-combined): show the heads
where NEITHER method gets it right -- geometry WRONG and the rung reader
WRONG-OR-UNDECIDED -- on the 44 Litolff + 11 Brahms truth set, with the
CURRENT code on this branch (the "as shipped" rungs reader, `ROUND7_
CLEANUP_ENABLED = False`). NO PIPELINE CODE CHANGED: this reuses
`combined_scorer.py`/`score_truth_set_rungs.py`/`truth_set_2_44c.py`
unchanged and only draws.

Each tile: red box = the head; green = the LOCAL staff lines
(`score_truth_set_rungs.frame_lines_for_head`, never extended); orange =
every rung the reader found, at its OWN measured y across its OWN
measured x-extent (`rungs_sheet.rung_extent`, reused unchanged); a cyan
tick at the y the REFERENCE says the head sits at; text naming the
reference, geometry, ledgers (and how many rungs), and the measured gap
between each pair of found rungs in staff spaces.

    python3 benchmarks/omr-local-staff-2026-09/neither_right_sheet.py
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
import rungs_sheet as rs  # noqa: E402  (reused: rung_extent)
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT_PATH = REPO / "out" / "print" / "ledgers" / "neither_right_sheet.png"

TARGET_TILE_W = 700          # "≥ 700 px wide"
UPSCALE = 3                  # "(×3)"
PAD_SPACES_X = 3.0
PAD_SPACES_Y = 1.5
COLS = 3
MAX_SHEET_W = 4000

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
CYAN = (220, 200, 0)
BLACK = (0, 0, 0)


def _position_to_y(pos: float, lines, spacing: float) -> float:
    """Same convention `gather_notehead_positions` writes:
    `pos = (y - top_y) / half_step`, inverted."""
    half_step = spacing / 2.0
    return lines[0] + pos * half_step


def _gap_ratios(rungs_y, spacing):
    return [abs(rungs_y[i + 1] - rungs_y[i]) / spacing
           for i in range(len(rungs_y) - 1)] if spacing > 0 else []


def _collect():
    bad = []
    for doc_id in ts.DOCS:
        r = cs.score_doc(doc_id)
        loaded = ts.load_doc(doc_id)
        rows_by_sub = {row["subject"]: row
                      for row in score._far_head_rows(doc_id, loaded)}
        for h in r["per_head"]:
            if h["v_geom"] == "wrong" and h["v_rungs"] in ("wrong", "unread"):
                bad.append((doc_id, h, rows_by_sub[h["subject"]], loaded))
    return bad


def _tile(doc_id, h, row, loaded):
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    boxes_by_page = score._notehead_boxes_by_page(rec)
    box = row["page_box"]
    staff_key = row["staff_key"]
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    global_lines = [float(y) for y in line_rows[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    page_boxes = boxes_by_page.get(row["page"], [])
    rungs_y, _sp, side = cs._rungs_y_for_head(gray, lines, box, row["subject"], page_boxes)

    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    ref_pos = h["truth_pos"][0]
    ref_y = _position_to_y(ref_pos, lines, spacing)

    # ── pixel-row check: every drawn line (staff + rung) must sit on ink
    # it claims to, or be marked UNCHECKED -- never silently drawn wrong.
    checked_rows = []
    binary_thr = lg._otsu_threshold(gray[max(0, int(min(lines))):int(max(lines)) + 1,
                                        max(0, int(cx - 2 * spacing)):int(cx + 2 * spacing)])
    for ly in lines:
        yi = int(round(ly))
        row_ink = gray[yi, max(0, int(cx - spacing)):int(cx + spacing)]
        ok = bool((row_ink <= binary_thr).any()) if row_ink.size else False
        checked_rows.append(("staff", ly, ok))
    extents = []
    for ry in rungs_y:
        ext = rs.rung_extent(gray, ry, cx, spacing)
        extents.append(ext)
        ok = ext is not None
        checked_rows.append(("rung", ry, ok))

    crop_x0 = max(0, int(cx - PAD_SPACES_X * spacing))
    crop_x1 = min(gray.shape[1], int(cx + PAD_SPACES_X * spacing))
    crop_y0 = max(0, int(min(min(lines), y0, ref_y) - PAD_SPACES_Y * spacing))
    crop_y1 = min(gray.shape[0], int(max(max(lines), y1, ref_y) + PAD_SPACES_Y * spacing))
    crop = cv2.cvtColor(gray[crop_y0:crop_y1, crop_x0:crop_x1], cv2.COLOR_GRAY2BGR)
    h0, w0 = crop.shape[:2]
    scale = max(UPSCALE, int(np.ceil(TARGET_TILE_W / max(w0, 1))))
    crop = cv2.resize(crop, (w0 * scale, h0 * scale), interpolation=cv2.INTER_NEAREST)

    def to_tile(px, py):
        return (int((px - crop_x0) * scale), int((py - crop_y0) * scale))

    for kind, ly, ok in checked_rows:
        if kind != "staff":
            continue
        p0, p1 = to_tile(crop_x0, ly), to_tile(crop_x1, ly)
        cv2.line(crop, p0, p1, GREEN, 2)

    for ry, ext in zip(rungs_y, extents):
        if ext is not None:
            xe0, xe1 = ext
        else:
            xe0, xe1 = crop_x0, crop_x1   # UNCHECKED fallback -- still drawn, labelled
        p0, p1 = to_tile(xe0, ry), to_tile(xe1, ry)
        cv2.line(crop, p0, p1, ORANGE, 3)

    tl, br = to_tile(x0, y0), to_tile(x1, y1)
    cv2.rectangle(crop, tl, br, RED, 3)

    cyan_x0, cyan_x1 = to_tile(cx - 1.2 * spacing, ref_y)[0], to_tile(cx + 1.2 * spacing, ref_y)[0]
    cyan_y = to_tile(cx, ref_y)[1]
    cv2.line(crop, (cyan_x0, cyan_y), (cyan_x1, cyan_y), CYAN, 3)

    gaps = _gap_ratios(rungs_y, spacing)
    gaps_text = ("gaps: " + ", ".join(f"{g:.1f}" for g in gaps) + " x staff space"
                if gaps else "gaps: (fewer than 2 rungs found)")
    rungs_label = (f"{h['rungs_pos']}" if h["rungs_pos"] is not None else "undecided")
    lines_text = [
        f"{doc_id}  {row['subject']}",
        f"reference: {ref_pos}  --  geometry said {h['geom_pos']}  --  "
        f"ledgers said {rungs_label} ({len(rungs_y)} ledgers found)",
        gaps_text,
    ]
    unchecked = sum(1 for _, _, ok in checked_rows if not ok)
    if unchecked:
        lines_text.append(f"[!] {unchecked} drawn line(s) could not be pixel-confirmed")

    # ⚠️ The legend's own text must never be clipped by a narrow crop (a
    # tight head-only crop is often far narrower than its own longest
    # line of text): the canvas is padded to fit the WIDEST line,
    # measured by `cv2.getTextSize`, never just the image's own width.
    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.62, 1
    text_w = max(cv2.getTextSize(t, font, font_scale, thickness)[0][0]
                for t in lines_text)
    canvas_w = max(crop.shape[1], text_w + 16)
    legend_h = 26 * (len(lines_text) + 1)
    out = np.full((crop.shape[0] + legend_h, canvas_w, 3), 255, dtype=np.uint8)
    out[:crop.shape[0], :crop.shape[1]] = crop
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, crop.shape[0] + 22 + i * 24),
                   font, font_scale, BLACK, thickness, cv2.LINE_AA)
    return out, checked_rows


def build():
    bad = _collect()
    tiles = []
    for doc_id, h, row, loaded in bad:
        tile, checked = _tile(doc_id, h, row, loaded)
        n_bad = sum(1 for _, _, ok in checked if not ok)
        print(f"{doc_id:<22} {row['subject']:<20} ref={h['truth_pos'][0]:>3} "
             f"geom={h['geom_pos']:>3} rungs={h['rungs_pos']}  "
             f"pixel-check: {len(checked)-n_bad}/{len(checked)} lines confirmed")
        tiles.append(tile)

    if not tiles:
        print("no heads qualify -- nothing to sheet")
        return

    tile_w = max(t.shape[1] for t in tiles)
    tile_h = max(t.shape[0] for t in tiles)
    rows_n = (len(tiles) + COLS - 1) // COLS
    sheet = np.full((rows_n * tile_h, COLS * tile_w, 3), 255, dtype=np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, COLS)
        th, tw = t.shape[:2]
        sheet[r * tile_h:r * tile_h + th, c * tile_w:c * tile_w + tw] = t

    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), sheet)
    print(f"\nwrote {OUT_PATH} ({len(tiles)} tiles, {sheet.shape[1]}x{sheet.shape[0]})")


if __name__ == "__main__":
    build()
