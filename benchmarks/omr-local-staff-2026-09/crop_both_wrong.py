#!/usr/bin/env python3
"""lane-ledger-rungs (2026-10-01): crops of every Litolff far head where
geometry AND rungs are BOTH wrong (round 3, f349ffd2) -- Litolff 11,
Brahms 0 (confirmed directly off `ledger_breakdown_r3.csv`'s own
geom_verdict/rungs_verdict columns, same "both_wrong" definition Table B
used: geometry wrong AND rungs wrong-or-undecided).

NO CODE CHANGES to the reader. Measurement/drawing only, reusing
`score_truth_set_rungs`/`truth_set_2_44c` unchanged.

One contact sheet (`out/print/ledgers/both_wrong_sheet.png`, same style
as review3: red box, green real 5 staff lines never extended, orange
measured rungs with filled/hollow mark) plus one crop per head under
`out/print/ledgers/both_wrong/`. Each tile adds: a cyan tick at the y the
REFERENCE position would put the head (computed from the found rungs
when available, else from plain staff spacing -- the text says which),
and chord detail (how many reference notes share that onset, and which
stack rank this head was paired with).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

CSV_PATH = REPO / "benchmarks" / "omr-local-staff-2026-09" / "ledger_breakdown_r3.csv"
OUT_DIR = REPO / "out" / "print" / "ledgers" / "both_wrong"
SHEET_PATH = REPO / "out" / "print" / "ledgers" / "both_wrong_sheet.png"

RED = (0, 0, 255)
GREEN = (0, 170, 0)
BLUE = (255, 120, 0)
CYAN = (255, 255, 0)
ORANGE = (30, 140, 255)
BLACK = (0, 0, 0)
MIN_WIDTH = 600
NATIVE_TILE = 100  # >=300px at x3 scale, matches review3's own minimum


def chord_detail(rec, doc_id: str, family: Optional[str], bar: Optional[int],
                 ref_root, page: int, system: int, staff: int, cell: int,
                 glyph_i: int) -> Optional[Dict[str, Any]]:
    """Re-derives chord SIZE and this glyph's stack RANK the SAME way
    `truth_set_2_44c.onset_exact_truth` does (duplicated read-only, never
    editing that function) -- it returns only the single paired pitch,
    not these two numbers."""
    if family is None or bar is None:
        return None
    cell_key = f"cell/{page}/{system}/{staff}/{cell}"
    our_events = ts._our_cell_events(rec, cell_key)
    if not our_events:
        return None
    found = ts._our_event_for_glyph(our_events, glyph_i)
    if found is None:
        return None
    our_idx, our_glyphs = found
    _, ref_ids = ts._FAMILY_MAPS[doc_id][family]
    ref_bars = ts._union_bars(ref_ids, ref_root)
    truth_groups = ts._truth_onset_groups(ref_bars, str(bar))
    if len(our_events) != len(truth_groups) or not (0 <= our_idx < len(truth_groups)):
        return None
    truth_pitches = truth_groups[our_idx]
    if len(our_glyphs) != len(truth_pitches):
        return None
    if len(our_glyphs) == 1:
        return dict(chord_size=1, rank=1)
    ys: Dict[int, float] = {}
    for gi in our_glyphs:
        box_obs = rec.obs(Q.GLYPH_BOX, f"glyph/{page}/{system}/{staff}/{cell}/{gi}")
        if box_obs:
            detail = box_obs[-1].get("detail") or {}
            page_box = detail.get("bbox_page_px")
            if page_box:
                ys[gi] = (page_box[1] + page_box[3]) / 2.0
    if len(ys) != len(our_glyphs):
        return dict(chord_size=len(truth_pitches), rank=None)
    sorted_ys = sorted(ys.values())
    min_gap = min((b - a for a, b in zip(sorted_ys, sorted_ys[1:])), default=None)
    staff_key = f"staff/{page}/{system}/{staff}"
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    spacing_px = ((max(float(y) for y in line_rows[-1]["value"])
                  - min(float(y) for y in line_rows[-1]["value"])) / 4.0
                 if line_rows else 0.0)
    if min_gap is not None and spacing_px > 0 and \
            min_gap < ts.DUPLICATE_BOX_MIN_GAP_SPACES * spacing_px:
        return dict(chord_size=len(truth_pitches), rank=None)
    order = sorted(our_glyphs, key=lambda gi: ys[gi])
    rank = order.index(glyph_i) + 1  # 1 = top of stack
    return dict(chord_size=len(truth_pitches), rank=rank)


def render_tile(gray, box, lines, subject, truth_pos, geom_pos, rungs_pos,
                chord, ref_tick_y, ref_tick_source, other_boxes):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lines = sorted(lines)
    top, bottom = lines[0], lines[-1]
    spacing = (bottom - top) / 4.0
    side = "above" if cy < top else "below"

    items = lg.measure_ledger_rungs(
        gray, lines, cx, head_y=cy, exclude_boxes=other_boxes,
        head_box_x=(x0, x1),
    )[side]

    farthest = cy
    for ry in items:
        farthest = min(farthest, ry) if side == "above" else max(farthest, ry)
    farthest = min(farthest, ref_tick_y) if side == "above" else max(farthest, ref_tick_y)
    margin = 1.4 * spacing
    wy0 = min(top, farthest) - margin
    wy1 = max(bottom, farthest) + margin
    wx0 = cx - 2.2 * spacing
    wx1 = cx + 2.2 * spacing
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

    edge_pos = 0 if side == "above" else 8
    edge = top if side == "above" else bottom
    _, oby = to_big(wx0, edge)
    cv2.line(big, (0, oby), (28, oby), BLUE, 5)
    cv2.putText(big, f"START pos{edge_pos}", (32, oby - 6 if side == "above" else oby + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLUE, 2, cv2.LINE_AA)

    for ry in items:
        ex0, ex1 = _rung_extent(gray, ry, cx, spacing, other_boxes)
        _, by = to_big(wx0, ry)
        bx0g, _ = to_big(ex0, ry)
        bx1g, _ = to_big(ex1, ry)
        cv2.line(big, (max(0, bx0g), by), (min(out_w, bx1g), by), ORANGE, max(2, scale // 2))
        mx, _ = to_big(cx, ry)
        occupied = abs(ry - cy) < spacing * 0.75
        if occupied:
            cv2.circle(big, (mx, by), 7, ORANGE, 2)   # hollow -- head on it
        else:
            cv2.circle(big, (mx, by), 7, ORANGE, -1)  # filled -- clean

    # cyan tick: where the REFERENCE position puts the head
    _, rby = to_big(wx0, ref_tick_y)
    cv2.line(big, (out_w - 24, rby), (out_w, rby), CYAN, 4)

    bx0, by0 = to_big(x0, y0)
    bx1, by1 = to_big(x1, y1)
    cv2.rectangle(big, (bx0, by0), (bx1, by1), RED, max(1, scale // 3))
    ccx, ccy = to_big(cx, cy)
    cv2.line(big, (ccx - 8, ccy), (ccx + 8, ccy), RED, 2)
    cv2.line(big, (ccx, ccy - 8), (ccx, ccy + 8), RED, 2)

    TEXT_W = max(out_w, 1000)
    chord_txt = "chord size unknown"
    if chord is not None:
        chord_txt = (f"chord size {chord['chord_size']}, paired rank "
                     f"{chord['rank']} of {chord['chord_size']} (1=top)"
                     if chord["chord_size"] > 1 else "not a chord (solo onset)")
    lines_txt = [
        f"{subject}",
        f"reference pos={truth_pos}  geometry pos={geom_pos}  rungs pos={rungs_pos}",
        chord_txt,
        f"cyan tick: reference position, from {ref_tick_source}",
    ]
    text_h = 20 + len(lines_txt) * 22 + 10
    tile = np.full((out_h + text_h, TEXT_W, 3), 255, dtype=np.uint8)
    tile[:out_h, :out_w, :] = big
    for i, t in enumerate(lines_txt):
        cv2.putText(tile, t[:160], (6, out_h + 20 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                   0.48, BLACK, 1, cv2.LINE_AA)
    return tile, out_w, out_h


def _rung_extent(gray, y, x_probe, spacing, exclude_boxes):
    h, w = gray.shape
    y_i = int(round(y))
    y0, y1 = max(0, y_i - 1), min(h, y_i + 2)
    x_half = int(round(2.5 * spacing))
    x0 = max(0, int(round(x_probe)) - x_half)
    x1 = min(w, int(round(x_probe)) + x_half)
    window = gray[y0:y1, x0:x1].copy()
    for (bx0, by0, bx1, by1) in exclude_boxes:
        ex0, ey0 = max(int(bx0), x0), max(int(by0), y0)
        ex1, ey1 = min(int(bx1) + 1, x1), min(int(by1) + 1, y1)
        if ex1 > ex0 and ey1 > ey0:
            window[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0] = 255
    thr = lg._otsu_threshold(window)
    ink_cols = (window <= thr).any(axis=0)
    bridge = int(round(lg.RUNG_BRIDGE_GAP_SPACES * spacing))
    runs = []
    n = len(ink_cols)
    i = 0
    while i < n:
        if ink_cols[i]:
            j = i
            while j < n and ink_cols[j]:
                j += 1
            if runs and i - runs[-1][1] <= bridge:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    if not runs:
        return (x_probe - 0.5 * spacing, x_probe + 0.5 * spacing)
    probe_col = int(round(x_probe)) - x0
    containing = [r for r in runs if r[0] <= probe_col < r[1]]
    r = containing[0] if containing else min(
        runs, key=lambda r: min(abs(r[0] - probe_col), abs(r[1] - 1 - probe_col)))
    return float(x0 + r[0]), float(x0 + r[1] - 1)


def main() -> int:
    both_wrong_rows = []
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            if row["geom_verdict"] == "wrong" and row["rungs_verdict"] in ("wrong", "undecided"):
                both_wrong_rows.append(row)

    litolff = [r for r in both_wrong_rows if r["doc"] == "beethoven5-litolff"]
    brahms = [r for r in both_wrong_rows if r["doc"] == "brahms1-breitkopf"]
    print(f"confirmed: Litolff {len(litolff)}, Brahms {len(brahms)}")

    loaded = ts.load_doc("beethoven5-litolff")
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    boxes_by_page = score._notehead_boxes_by_page(rec)
    rows_by_sub = {row["subject"]: row for row in score._far_head_rows("beethoven5-litolff", loaded)}
    detmap = ts._subject_detections(loaded["parts"])
    offsets = loaded["offsets"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tiles = []
    notes = []

    for csv_row in litolff:
        sub = csv_row["subject"]
        row = rows_by_sub.get(sub)
        if row is None:
            continue
        box = row["page_box"]
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        line_rows = rec.obs(Q.STAFF_LINES, row["staff_key"])
        lines = [float(v) for v in line_rows[-1]["value"]]
        gray = pages.get(row["page"])
        others = [b for (s, b) in boxes_by_page.get(row["page"], []) if s != sub]

        truth_pos = int(csv_row["ref_pos"])
        side = "above" if truth_pos < 0 else "below"
        edge = min(lines) if side == "above" else max(lines)
        sign = -1.0 if side == "above" else 1.0
        spacing = (max(lines) - min(lines)) / 4.0
        half_step = spacing / 2.0

        items = lg.measure_ledger_rungs(
            gray, lines, cx, head_y=cy, exclude_boxes=others, head_box_x=(x0, x1)
        )[side]
        edge_pos = 0 if side == "above" else 8
        offset_needed = abs(truth_pos - edge_pos)
        if items:
            # place the tick using the SAME ladder arithmetic (2 half
            # steps per rung found, nearest-first) as derive_far_head_step
            n_needed = offset_needed // 2
            if n_needed >= 1 and n_needed <= len(items):
                ref_tick_y = items[n_needed - 1] + sign * (
                    (offset_needed - 2 * n_needed) * half_step)
                source = "found rungs (walked to the reference's own step)"
            else:
                ref_tick_y = edge + sign * offset_needed * half_step
                source = "plain staff spacing (reference step beyond measured rungs)"
        else:
            ref_tick_y = edge + sign * offset_needed * half_step
            source = "plain staff spacing (no rungs measured)"

        # chord detail
        page, system, staff, cell, glyph_i = (int(v) for v in sub.split("/")[1:6])
        det = detmap.get(sub)
        family = ts._family_for_part_id("beethoven5-litolff", det["our_part_id"]) if det else None
        bar = None
        if det is not None:
            off = offsets.get((det["page"], det["system"]))
            if off is not None:
                bar = off + det["cell"] + 1 + loaded["bar_correction"]
        chord = chord_detail(rec, "beethoven5-litolff", family, bar, loaded["ref_root"],
                             page, system, staff, cell, glyph_i)

        tile, tw, th = render_tile(
            gray, box, lines, sub, truth_pos, int(csv_row["geom_pos"]),
            (csv_row["rungs_pos"] or "None"), chord, ref_tick_y, source, others,
        )
        out_path = OUT_DIR / f"{sub.replace('/', '-')}.png"
        cv2.imwrite(str(out_path), tile)
        tiles.append(tile)
        print(f"wrote {out_path}")
        notes.append((sub, csv_row, chord))

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
        cv2.putText(sheet, "red=box  green=staff(real 5)  orange=rung(filled clean/hollow on-head)  cyan=reference position",
                   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLACK, 1, cv2.LINE_AA)
        for i, t in enumerate(tiles):
            r, c = divmod(i, cols)
            y = legend_h + pad + r * (th + pad)
            x = pad + c * (tw + pad)
            sheet[y:y + t.shape[0], x:x + t.shape[1]] = t
        SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(SHEET_PATH), sheet)
        print(f"wrote {SHEET_PATH} ({len(tiles)} tiles)")

    print("\nper-head notes (what the drawing shows -- fill in by inspection):")
    for sub, csv_row, chord in notes:
        print(f"  {sub}: ref={csv_row['ref_pos']} geom={csv_row['geom_pos']} "
             f"rungs={csv_row['rungs_pos']} chord={chord}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
