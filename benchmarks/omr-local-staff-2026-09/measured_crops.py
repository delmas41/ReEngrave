#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01): crops of every far head whose answer
CHANGES between plain geometry and the new THIRD reader, `ledger_grid.
ledger_measured_geometry` (interpolation/extrapolation on the measured
ledger ladder). Measurement/drawing only -- the reader itself lives in
tools/omr/annotate/ledger_grid.py and is not wired into the product path.

Each crop (>=600px wide): red detector box, green real 5 staff lines
(never extended), magenta rows for every measured ledger (the same ones
`measure_ledger_rungs` found, with Sean's own both-side-stub / box-length
/ lateral-exclusion rules already applied), and text: subject, reference
position, geometry position, rungs (derive_far_head_step) position, and
the ledger-measured position with its own reason (interpolated / extra-
polated / fallback).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers" / "measured"
SHEET_PATH = REPO / "out" / "print" / "ledgers" / "measured_sheet.png"

RED = (0, 0, 255)
GREEN = (0, 170, 0)
BLUE = (255, 120, 0)
MAGENTA = (255, 0, 255)
BLACK = (0, 0, 0)
MIN_WIDTH = 600


def render_tile(gray, box, lines, subject, truth_pos, geom_pos, rungs_pos,
                ledger_pos, ledger_reason, ledger_ys, side):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lines = sorted(lines)
    top, bottom = lines[0], lines[-1]
    spacing = (bottom - top) / 4.0
    edge = top if side == "above" else bottom
    edge_pos = 0 if side == "above" else 8

    farthest = cy
    for ly in ledger_ys:
        farthest = min(farthest, ly) if side == "above" else max(farthest, ly)
    margin = 1.3 * spacing
    wy0 = min(top, farthest, cy) - margin
    wy1 = max(bottom, farthest, cy) + margin
    wx0 = cx - 1.8 * spacing
    wx1 = cx + 1.8 * spacing
    native_w = max(1, int(round(wx1 - wx0)))
    native_h = max(1, int(round(wy1 - wy0)))
    scale = max(3, -(-MIN_WIDTH // native_w))
    out_w, out_h = native_w * scale, native_h * scale

    h, w = gray.shape
    px0, py0 = max(0, int(wx0)), max(0, int(wy0))
    px1, py1 = min(w, int(wx0) + native_w), min(h, int(wy0) + native_h)
    canvas = np.full((native_h, native_w, 3), 255, dtype=np.uint8)
    if px1 > px0 and py1 > py0:
        patch = cv2.cvtColor(gray[py0:py1, px0:px1], cv2.COLOR_GRAY2BGR)
        canvas[py0 - int(wy0):py1 - int(wy0), px0 - int(wx0):px1 - int(wx0)] = patch
    big = cv2.resize(canvas, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return (int(round((px - wx0) * scale)), int(round((py - wy0) * scale)))

    for ly in lines:
        if ly < wy0 or ly > wy1:
            continue
        _, by = to_big(wx0, ly)
        cv2.line(big, (0, by), (out_w, by), GREEN, 1)

    _, oby = to_big(wx0, edge)
    cv2.line(big, (0, oby), (28, oby), BLUE, 5)
    cv2.putText(big, f"START pos{edge_pos}",
               (32, oby - 6 if side == "above" else oby + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLUE, 2, cv2.LINE_AA)

    for ly in ledger_ys:
        if ly < wy0 or ly > wy1:
            continue
        _, by = to_big(wx0, ly)
        cv2.line(big, (int(0.25 * out_w), by), (out_w, by), MAGENTA, 3)

    bx0, by0 = to_big(x0, y0)
    bx1, by1 = to_big(x1, y1)
    cv2.rectangle(big, (bx0, by0), (bx1, by1), RED, max(1, scale // 3))
    ccx, ccy = to_big(cx, cy)
    cv2.line(big, (ccx - 8, ccy), (ccx + 8, ccy), RED, 2)
    cv2.line(big, (ccx, ccy - 8), (ccx, ccy + 8), RED, 2)

    TEXT_W = max(out_w, 950)
    lines_txt = [
        f"{subject}",
        f"reference={truth_pos}  geometry={geom_pos}  rungs={rungs_pos}  "
        f"ledger-measured={ledger_pos}",
        f"ledger-measured reason: {ledger_reason}"[:150],
    ]
    text_h = 20 + len(lines_txt) * 22 + 10
    tile = np.full((out_h + text_h, TEXT_W, 3), 255, dtype=np.uint8)
    tile[:out_h, :out_w, :] = big
    for i, t in enumerate(lines_txt):
        cv2.putText(tile, t, (6, out_h + 20 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                   0.46, BLACK, 1, cv2.LINE_AA)
    return tile


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tiles = []
    changed_total = 0

    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        boxes_by_page = score._notehead_boxes_by_page(rec)
        rows_by_sub = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
        r = score.score_doc(doc_id)
        changed = [h for h in r["per_head"]
                  if h["v_ledger"] != "fallback" and h["ledger_pos"] != h["geom_pos"]]
        changed_total += len(changed)
        print(f"{doc_id}: {len(changed)} changed heads")

        for h in changed:
            row = rows_by_sub.get(h["subject"])
            if row is None:
                continue
            box = row["page_box"]
            x0, y0, x1, y1 = box
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            line_rows = rec.obs(Q.STAFF_LINES, row["staff_key"])
            lines = [float(v) for v in line_rows[-1]["value"]]
            top = min(lines)
            side = "above" if cy < top else "below"
            gray = pages.get(row["page"])
            others = [b for (s, b) in boxes_by_page.get(row["page"], [])
                     if s != row["subject"]]
            spacing = (max(lines) - min(lines)) / 4.0
            ledger_ys = lg.measure_ledger_rungs(
                gray, lines, cx, head_y=cy, exclude_boxes=others,
                head_box_x=(x0, x1),
            )[side]

            tile = render_tile(
                gray, box, lines, h["subject"], h["truth_pos"], h["geom_pos"],
                h["after_pos"], h["ledger_pos"], h["ledger_reason"], ledger_ys, side,
            )
            out_path = OUT_DIR / f"{doc_id}-{h['subject'].replace('/', '-')}.png"
            cv2.imwrite(str(out_path), tile)
            tiles.append(tile)
            print(f"  wrote {out_path}")

    # --- contact sheet ---
    if tiles:
        tw = max(t.shape[1] for t in tiles)
        th = max(t.shape[0] for t in tiles)
        cols = 4
        rows_n = -(-len(tiles) // cols)
        pad = 8
        legend_h = 40
        sheet_w = cols * tw + (cols + 1) * pad
        sheet_h = legend_h + rows_n * th + (rows_n + 1) * pad
        sheet = np.full((sheet_h, sheet_w, 3), 255, dtype=np.uint8)
        cv2.putText(sheet,
                   "red=box  green=staff(real 5)  magenta=measured ledger rows  blue=outer staff line",
                   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLACK, 1, cv2.LINE_AA)
        for i, t in enumerate(tiles):
            r_, c_ = divmod(i, cols)
            y = legend_h + pad + r_ * (th + pad)
            x = pad + c_ * (tw + pad)
            sheet[y:y + t.shape[0], x:x + t.shape[1]] = t
        SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(SHEET_PATH), sheet)
        print(f"wrote {SHEET_PATH} ({len(tiles)} tiles)")

    print(f"\ntotal changed heads: {changed_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
