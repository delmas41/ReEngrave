#!/usr/bin/env python3
"""lane-r8-sheets (2026-10-02): three phone-sized contact sheets for the
ROUND-8 ledger reader AS SHIPPED WITH CAUSES C+D WIRED
(`score.reader_absolute_position(..., four_causes_cd=True)` --
`score_truth_set_rungs.score_doc(doc_id, four_causes_cd=True)` is the
configuration that reproduces FINDINGS' "rungs, C+D fully wired":
Litolff right=25 wrong=14 abstain=5 (n=44, matching geometry's own
wrong count), Brahms right=11 wrong=0 abstain=0.

MEASUREMENT / DRAWING ONLY -- no record mutation, no re-gather, no
change to tools/. Reuses `neither_right_sheet_r8.py`'s own tile-drawing
code (crop, green = real staff lines measured locally never extended,
orange = every rung the reader found at its measured y/x-extent, red =
the head's own box, cyan = reference position) unchanged except the
caption, which now also states geometry's own verdict (needed for
sheets 2 and 3, since those sheets mix heads where geometry is right
and heads where it is wrong). Subjects for each sheet are DERIVED from
`score_truth_set_rungs.score_doc`'s own per-head tally -- never
hand-listed -- so the sheet's population always matches the tally
printed by `score_truth_set_rungs.main()`.

Three sheets, Litolff only (brahms is 11/0/0 -- nothing for any of
these three buckets):

  1. r8_geom_right_rungs_undecided.png -- geometry RIGHT, rungs ABSTAIN.
  2. r8_rungs_wrong.png -- rungs WRONG (every one of the 14), caption
     states geometry's own verdict on each.
  3. r8_both_wrong.png -- geometry AND rungs (C+D) BOTH wrong. A rung
     verdict of ABSTAIN is not WRONG and is excluded from this sheet;
     any such heads are reported separately by `main()`'s own stdout
     listing, never silently folded in.

    python3 benchmarks/omr-local-staff-2026-09/r8_three_sheets.py
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
import rungs_sheet as rs  # noqa: E402  (reused: rung_extent)
import combined_scorer as cs  # noqa: E402  (reused: _rungs_y_for_head)
from tools.omr.staged.record import Q  # noqa: E402

FOUR_CAUSES_CD = True
OUT_DIR = REPO / "out" / "print" / "ledgers"

TARGET_TILE_W = 700          # "each tile >= 700 px"
UPSCALE = 3
PAD_SPACES_X = 3.0
PAD_SPACES_Y = 1.5
COLS = 3                     # "3 tiles per row"
MAX_SHEET_W = 2600            # "<= 2600 px wide"
JPEG_QUALITY = 85

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
CYAN = (220, 200, 0)
BLACK = (0, 0, 0)


def _position_to_y(pos: float, lines, spacing: float) -> float:
    half_step = spacing / 2.0
    return lines[0] + pos * half_step


def _gap_ratios(rungs_y, spacing):
    return [abs(rungs_y[i + 1] - rungs_y[i]) / spacing
            for i in range(len(rungs_y) - 1)] if spacing > 0 else []


def _tile(doc_id, row, rec, pages, boxes_by_page, acc_boxes_by_page):
    """Same crop/draw/pixel-check as `neither_right_sheet_r8._tile`,
    with one addition: the caption also names geometry's own verdict
    (plain `reference X -- geometry Y -- ledgers Z (N found) -- branch:
    ...` line), since sheets 2 and 3 mix heads where geometry alone is
    right and heads where it is also wrong."""
    box = row["page_box"]
    staff_key = row["staff_key"]
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    global_lines = [float(y) for y in line_rows[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    page_boxes = boxes_by_page.get(row["page"], [])
    page_acc_boxes = acc_boxes_by_page.get(row["page"], [])

    rungs_pos, reason = score.reader_absolute_position(
        gray, lines, box, row["subject"], page_boxes,
        page_accidental_boxes=page_acc_boxes, four_causes_cd=FOUR_CAUSES_CD,
    )
    rungs_y, _sp, _side = cs._rungs_y_for_head(
        gray, lines, box, row["subject"], page_boxes,
        page_accidental_boxes=page_acc_boxes, four_causes_cd=FOUR_CAUSES_CD,
    )

    geom_pos = int(round(row["raw_pos"]))
    clef_v = rec.value(Q.CLEF, staff_key)
    truth_pos = sorted(set(score.truth_positions(row["truth_pitches"], str(clef_v))))
    ref_pos = truth_pos[0] if truth_pos else geom_pos

    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    ref_y = _position_to_y(ref_pos, lines, spacing)

    # pixel-row check: every drawn line (staff + rung) must sit on ink
    # it claims to, or be marked UNCHECKED -- never silently drawn wrong.
    import tools.omr.annotate.ledger_grid as lg  # local import matches sibling script
    checked_rows = []
    binary_thr = lg._otsu_threshold(
        gray[max(0, int(min(lines))):int(max(lines)) + 1,
             max(0, int(cx - 2 * spacing)):int(cx + 2 * spacing)]
    )
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
            xe0, xe1 = crop_x0, crop_x1
        p0, p1 = to_tile(xe0, ry), to_tile(xe1, ry)
        cv2.line(crop, p0, p1, ORANGE, 3)

    tl, br = to_tile(x0, y0), to_tile(x1, y1)
    cv2.rectangle(crop, tl, br, RED, 3)

    cyan_x0 = to_tile(cx - 1.2 * spacing, ref_y)[0]
    cyan_x1 = to_tile(cx + 1.2 * spacing, ref_y)[0]
    cyan_y = to_tile(cx, ref_y)[1]
    cv2.line(crop, (cyan_x0, cyan_y), (cyan_x1, cyan_y), CYAN, 3)

    gaps = _gap_ratios(rungs_y, spacing)
    gaps_text = ("gaps: " + ", ".join(f"{g:.1f}" for g in gaps) + " x staff space"
                 if gaps else "gaps: (fewer than 2 rungs found)")
    rungs_label = (f"{rungs_pos}" if rungs_pos is not None else "undecided")
    geom_verdict = "right" if geom_pos in truth_pos else "wrong"
    ledger_verdict = "right" if (rungs_pos is not None and rungs_pos in truth_pos) \
        else ("undecided" if rungs_pos is None else "wrong")
    lines_text = [
        f"{doc_id}  {row['subject']}",
        f"reference {ref_pos} -- geometry {geom_pos} ({geom_verdict}) -- "
        f"ledgers {rungs_label} ({len(rungs_y)} found, {ledger_verdict})",
        gaps_text,
        f"branch: {reason}"[:95],
    ]
    unchecked = sum(1 for _, _, ok in checked_rows if not ok)
    if unchecked:
        lines_text.append(f"[!] {unchecked} drawn line(s) could not be pixel-confirmed")

    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1
    text_w = max(cv2.getTextSize(t, font, font_scale, thickness)[0][0]
                 for t in lines_text)
    canvas_w = max(crop.shape[1], text_w + 16)
    legend_h = 24 * (len(lines_text) + 1)
    out = np.full((crop.shape[0] + legend_h, canvas_w, 3), 255, dtype=np.uint8)
    out[:crop.shape[0], :crop.shape[1]] = crop
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, crop.shape[0] + 20 + i * 22),
                    font, font_scale, BLACK, thickness, cv2.LINE_AA)

    return out, checked_rows, rungs_pos, geom_pos, ref_pos, geom_verdict, ledger_verdict


def _build_sheet(doc_subjects, out_name, caches):
    """`doc_subjects`: list of (doc_id, subject). Builds + writes the
    PNG and a JPEG (quality 85) copy; returns per-tile verdicts for the
    reply/coverage report."""
    loaded_cache, rows_cache, boxes_cache, acc_cache = caches
    tiles = []
    coverage_rows_total = 0
    coverage_rows_bad = 0
    report = []
    for doc_id, subject in doc_subjects:
        loaded = loaded_cache[doc_id]
        row = rows_cache[doc_id].get(subject)
        if row is None:
            print(f"  {doc_id:<22} {subject:<20} NOT IN FAR-HEAD POPULATION")
            continue
        pages = score.PageCache(loaded["cfg"])
        (tile, checked, rungs_pos, geom_pos, ref_pos,
         geom_verdict, ledger_verdict) = _tile(
            doc_id, row, loaded["rec"], pages, boxes_cache[doc_id], acc_cache[doc_id],
        )
        n_bad = sum(1 for _, _, ok in checked if not ok)
        coverage_rows_total += len(checked)
        coverage_rows_bad += n_bad
        print(f"  {doc_id:<22} {subject:<20} ref={ref_pos:>3} geom={geom_pos:>3} "
              f"({geom_verdict:<5}) rungs={rungs_pos} ({ledger_verdict:<9}) "
              f"pixel-check: {len(checked) - n_bad}/{len(checked)}")
        tiles.append(tile)
        report.append(dict(subject=subject, geom_verdict=geom_verdict,
                            ledger_verdict=ledger_verdict))

    if not tiles:
        print(f"  no heads qualify for {out_name} -- nothing to sheet")
        return report, coverage_rows_total, coverage_rows_bad

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
    png_path = OUT_DIR / f"{out_name}.png"
    jpg_path = OUT_DIR / f"{out_name}.jpg"
    cv2.imwrite(str(png_path), sheet)
    cv2.imwrite(str(jpg_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    print(f"  wrote {png_path} and {jpg_path} "
          f"({len(tiles)} tiles, {sheet.shape[1]}x{sheet.shape[0]})")
    return report, coverage_rows_total, coverage_rows_bad


def main() -> int:
    doc_id = "beethoven5-litolff"   # brahms is 11/0/0 -- empty for all 3 buckets
    loaded = ts.load_doc(doc_id)
    rows_by_subject = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
    boxes_by_page = score._notehead_boxes_by_page(loaded["rec"])
    acc_by_page = score._accidental_boxes_by_page(loaded["rec"])
    caches = (
        {doc_id: loaded}, {doc_id: rows_by_subject},
        {doc_id: boxes_by_page}, {doc_id: acc_by_page},
    )

    result = score.score_doc(doc_id, four_causes_cd=FOUR_CAUSES_CD)
    per_head = result["per_head"]
    tally = result["tally"]["rungs_after"]
    print(f"=== {doc_id} rungs_after (four_causes_cd=True) tally: {dict(tally)} ===\n")

    geom_right_rungs_undecided = [
        h for h in per_head if h["v_geom"] == "right" and h["v_after"] == "abstain"
    ]
    rungs_wrong = [h for h in per_head if h["v_after"] == "wrong"]
    both_wrong = [
        h for h in per_head if h["v_after"] == "wrong" and h["v_geom"] == "wrong"
    ]
    wrong_geom_but_rungs_undecided = [
        h for h in per_head if h["v_geom"] == "wrong" and h["v_after"] == "abstain"
    ]

    print(f"1) geometry RIGHT, rungs UNDECIDED: {len(geom_right_rungs_undecided)}")
    report1, t1, b1 = _build_sheet(
        [(doc_id, h["subject"]) for h in geom_right_rungs_undecided],
        "r8_geom_right_rungs_undecided", caches,
    )
    print()

    print(f"2) rungs WRONG: {len(rungs_wrong)}")
    report2, t2, b2 = _build_sheet(
        [(doc_id, h["subject"]) for h in rungs_wrong],
        "r8_rungs_wrong", caches,
    )
    print()

    print(f"3) BOTH geometry and rungs WRONG: {len(both_wrong)}")
    report3, t3, b3 = _build_sheet(
        [(doc_id, h["subject"]) for h in both_wrong],
        "r8_both_wrong", caches,
    )
    print()

    print(f"(separately, NOT on sheet 3: geometry wrong + rungs UNDECIDED "
          f"(not counted as wrong): {len(wrong_geom_but_rungs_undecided)} -- "
          f"{[h['subject'] for h in wrong_geom_but_rungs_undecided]})")

    total_rows = t1 + t2 + t3
    total_bad = b1 + b2 + b3
    coverage = 1.0 - (total_bad / total_rows if total_rows else 0.0)
    print(f"\nPixel-row coverage across all 3 sheets: {total_rows - total_bad}/{total_rows} "
          f"= {coverage:.3f} (threshold >= 0.5)")
    if coverage < 0.5:
        print("  [!] COVERAGE BELOW THRESHOLD")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
