#!/usr/bin/env python3
"""lane-ledger-shape (2026-10-02): two phone-sized contact sheets so Sean
can SEE why the shape trace disagrees with round 8 on real ink.

DRAWING ONLY -- no record mutation, no re-gather, no change to
`tools/omr/annotate/ledger_shape_trace.py` or `ledger_grid.py`; the
evidence-function substitution is the SAME local monkeypatch
`score_shape_trace.py` already uses, scoped to this process only.

  1. shape_regressions.jpg -- every head RIGHT under round 8 but NOT
     right under the shape trace (14 Litolff + 5 Brahms, the regression
     list `score_shape_trace.py` already prints).
  2. shape_flips.jpg -- the two heads that gated the lane:
     `glyph/3/0/7/2/4` (flips to right) and `glyph/3/0/7/0/7` (still
     undecided).

Each tile draws: the TRACED OUTLINE (thin magenta polyline, left/right
extent per traced row), the FITTED OVAL (yellow ellipse + centre cross),
the detected LINE BANDS (orange, at band y / x-extent), the detector box
(thin red), local staff lines (green), and the reference tick (cyan).
Caption: "reference X -- round 8 Y -- trace Z -- trace reason".

    python3 benchmarks/omr-local-staff-2026-09/shape_sheets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate import ledger_shape_trace as shtr  # noqa: E402

FOUR_CAUSES_CD = True
OUT_DIR = REPO / "out" / "print" / "ledgers"

TARGET_TILE_W = 700
UPSCALE = 3
PAD_SPACES_X = 3.0
PAD_SPACES_Y = 1.75
COLS = 3
MAX_SHEET_W = 2600
JPEG_QUALITY = 85

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
CYAN = (220, 200, 0)
MAGENTA = (220, 0, 220)
YELLOW = (0, 220, 220)
BLACK = (0, 0, 0)

REGRESSIONS = {
    "beethoven5-litolff": [
        "glyph/1/0/10/8/1", "glyph/1/0/3/7/3", "glyph/3/0/0/2/3",
        "glyph/3/0/0/5/12", "glyph/3/0/5/4/5", "glyph/3/0/5/7/0",
        "glyph/3/0/7/2/3", "glyph/3/0/7/3/5", "glyph/3/0/7/4/0",
        "glyph/3/0/7/4/2", "glyph/3/0/7/6/2", "glyph/3/0/7/6/4",
        "glyph/3/0/8/2/5", "glyph/3/1/0/9/0",
    ],
    "brahms1-breitkopf": [
        "glyph/1/1/0/2/4", "glyph/1/1/0/4/6", "glyph/1/1/8/4/4",
        "glyph/1/1/8/5/0", "glyph/1/1/8/6/0",
    ],
}
FLIPS = {
    "beethoven5-litolff": ["glyph/3/0/7/2/4", "glyph/3/0/7/0/7"],
}


def _position_to_y(pos: float, lines, spacing: float) -> float:
    return lines[0] + pos * (spacing / 2.0)


def _tile(doc_id, row, rec, pages, boxes_by_page, acc_boxes_by_page):
    box = row["page_box"]
    staff_key = row["staff_key"]
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    global_lines = [float(y) for y in line_rows[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    page_boxes = boxes_by_page.get(row["page"], [])
    page_acc_boxes = acc_boxes_by_page.get(row["page"], [])
    subject = row["subject"]

    round8_pos, round8_reason = score.reader_absolute_position(
        gray, lines, box, subject, page_boxes,
        page_accidental_boxes=page_acc_boxes, four_causes_cd=FOUR_CAUSES_CD,
    )

    original = lg.head_middle_rung_evidence
    lg.head_middle_rung_evidence = shtr.shape_trace_middle_rung_evidence
    try:
        trace_pos, trace_reason = score.reader_absolute_position(
            gray, lines, box, subject, page_boxes,
            page_accidental_boxes=page_acc_boxes, four_causes_cd=FOUR_CAUSES_CD,
        )
    finally:
        lg.head_middle_rung_evidence = original

    others = [b for (s, b) in page_boxes if s != subject]
    if page_acc_boxes:
        others = others + [b for (_s, b) in page_acc_boxes]
    trace = shtr.trace_head_shape(gray, box, spacing, exclude_boxes=others)

    geom_pos = int(round(row["raw_pos"]))
    clef_v = rec.value(Q.CLEF, staff_key)
    truth_pos = sorted(set(score.truth_positions(row["truth_pitches"], str(clef_v))))
    ref_pos = truth_pos[0] if truth_pos else geom_pos

    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    ref_y = _position_to_y(ref_pos, lines, spacing)

    all_ys = [min(lines), max(lines), y0, y1, ref_y]
    if trace is not None:
        all_ys += [trace.oval_top_y, trace.oval_bottom_y]
        all_ys += [y for y in trace.rows_y]
    crop_x0 = max(0, int(cx - PAD_SPACES_X * spacing))
    crop_x1 = min(gray.shape[1], int(cx + PAD_SPACES_X * spacing))
    crop_y0 = max(0, int(min(all_ys) - PAD_SPACES_Y * spacing))
    crop_y1 = min(gray.shape[0], int(max(all_ys) + PAD_SPACES_Y * spacing))
    crop = cv2.cvtColor(gray[crop_y0:crop_y1, crop_x0:crop_x1], cv2.COLOR_GRAY2BGR)
    h0, w0 = crop.shape[:2]
    scale = max(UPSCALE, int(np.ceil(TARGET_TILE_W / max(w0, 1))))
    crop = cv2.resize(crop, (w0 * scale, h0 * scale), interpolation=cv2.INTER_NEAREST)

    def to_tile(px, py):
        return (int((px - crop_x0) * scale), int((py - crop_y0) * scale))

    # green: staff lines, extended across the crop width.
    for ly in lines:
        p0, p1 = to_tile(crop_x0, ly), to_tile(crop_x1, ly)
        cv2.line(crop, p0, p1, GREEN, 2)

    # magenta: traced outline, left and right extents per row.
    if trace is not None:
        left_pts, right_pts = [], []
        for y, l, r in zip(trace.rows_y, trace.left_x, trace.right_x):
            if l is None or r is None:
                continue
            left_pts.append(to_tile(l, y))
            right_pts.append(to_tile(r, y))
        if len(left_pts) >= 2:
            cv2.polylines(crop, [np.array(left_pts, dtype=np.int32)],
                          False, MAGENTA, 2)
        if len(right_pts) >= 2:
            cv2.polylines(crop, [np.array(right_pts, dtype=np.int32)],
                          False, MAGENTA, 2)

        # yellow: fitted oval (ellipse) + centre cross.
        ocx, ocy = cx, trace.oval_center_y
        oh = max(1.0, (trace.oval_bottom_y - trace.oval_top_y) / 2.0)
        ow = max(1.0, trace.oval_half_width)
        center_tile = to_tile(ocx, ocy)
        axes_tile = (int(ow * scale), int(oh * scale))
        cv2.ellipse(crop, center_tile, axes_tile, 0, 0, 360, YELLOW, 2)
        cs_ = 10
        cv2.line(crop, (center_tile[0] - cs_, center_tile[1]),
                  (center_tile[0] + cs_, center_tile[1]), YELLOW, 2)
        cv2.line(crop, (center_tile[0], center_tile[1] - cs_),
                  (center_tile[0], center_tile[1] + cs_), YELLOW, 2)

        # orange: detected ledger bands, at their own y / x-extent.
        for band in trace.ledger_bands:
            p0 = to_tile(band["left_x"], band["y"])
            p1 = to_tile(band["right_x"], band["y"])
            cv2.line(crop, p0, p1, ORANGE, 3)

    # red: detector box, thin.
    tl, br = to_tile(x0, y0), to_tile(x1, y1)
    cv2.rectangle(crop, tl, br, RED, 1)

    # cyan: reference tick.
    cyan_x0 = to_tile(cx - 1.2 * spacing, ref_y)[0]
    cyan_x1 = to_tile(cx + 1.2 * spacing, ref_y)[0]
    cyan_y = to_tile(cx, ref_y)[1]
    cv2.line(crop, (cyan_x0, cyan_y), (cyan_x1, cyan_y), CYAN, 3)

    def _verdict(pos):
        if pos is None:
            return "undecided"
        return "right" if pos in truth_pos else "wrong"

    round8_label = f"{round8_pos}" if round8_pos is not None else "undecided"
    trace_label = f"{trace_pos}" if trace_pos is not None else "undecided"
    lines_text = [
        f"{doc_id}  {subject}",
        f"reference {ref_pos} -- round 8 {round8_label} ({_verdict(round8_pos)}) "
        f"-- trace {trace_label} ({_verdict(trace_pos)})",
        f"trace reason: {trace_reason}"[:100],
    ]

    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    text_w = max(cv2.getTextSize(t, font, font_scale, thickness)[0][0]
                 for t in lines_text)
    canvas_w = max(crop.shape[1], text_w + 16)
    legend_h = 24 * (len(lines_text) + 1)
    out = np.full((crop.shape[0] + legend_h, canvas_w, 3), 255, dtype=np.uint8)
    out[:crop.shape[0], :crop.shape[1]] = crop
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, crop.shape[0] + 20 + i * 22),
                    font, font_scale, BLACK, thickness, cv2.LINE_AA)

    return out, dict(
        subject=subject, doc_id=doc_id, round8=_verdict(round8_pos),
        trace=_verdict(trace_pos), trace_reason=trace_reason,
        round8_reason=round8_reason,
    )


def _build_sheet(doc_subjects, out_name):
    tiles, report = [], []
    for doc_id, subject in doc_subjects:
        loaded = ts.load_doc(doc_id)
        rows_by_subject = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
        row = rows_by_subject.get(subject)
        if row is None:
            print(f"  {doc_id:<22} {subject:<20} NOT IN FAR-HEAD POPULATION")
            continue
        pages = score.PageCache(loaded["cfg"])
        boxes_by_page = score._notehead_boxes_by_page(loaded["rec"])
        acc_by_page = score._accidental_boxes_by_page(loaded["rec"])
        tile, info = _tile(doc_id, row, loaded["rec"], pages, boxes_by_page, acc_by_page)
        print(f"  {doc_id:<22} {subject:<20} round8={info['round8']:<9} "
              f"trace={info['trace']:<9}")
        tiles.append(tile)
        report.append(info)

    if not tiles:
        print(f"  no heads qualify for {out_name} -- nothing to sheet")
        return report

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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jpg_path = OUT_DIR / f"{out_name}.jpg"
    cv2.imwrite(str(jpg_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    print(f"  wrote {jpg_path} ({len(tiles)} tiles, {sheet.shape[1]}x{sheet.shape[0]})")
    return report


def main() -> int:
    reg_subjects = [
        (doc_id, sub) for doc_id, subs in REGRESSIONS.items() for sub in subs
    ]
    flip_subjects = [
        (doc_id, sub) for doc_id, subs in FLIPS.items() for sub in subs
    ]

    print("=== shape_regressions.jpg ===")
    reg_report = _build_sheet(reg_subjects, "shape_regressions")
    print("\n=== shape_flips.jpg ===")
    flip_report = _build_sheet(flip_subjects, "shape_flips")

    print("\n=== per-tile reasons (for the cause write-up) ===")
    for info in reg_report:
        print(f"  {info['doc_id']:<22} {info['subject']:<20} "
              f"trace={info['trace']:<9} reason={info['trace_reason']}")
    for info in flip_report:
        print(f"  {info['doc_id']:<22} {info['subject']:<20} "
              f"trace={info['trace']:<9} reason={info['trace_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
