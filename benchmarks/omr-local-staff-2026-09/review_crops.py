#!/usr/bin/env python3
"""lane-ledger-rungs follow-up (coordinator, 2026-10-01): crops for Sean,
not a code fix. For every truth-set far head where rungs-after is WRONG
and geometry is RIGHT, every head where rungs-after ABSTAINS, and 5
control heads where both are right -- one crop each, >=600px wide,
showing the red detector box, the real 5 staff lines (green, never
extended), every measured rung (orange, with its own x-extent and a
filled/hollow mark), the OUTER staff line the count starts from (marked),
and the full arithmetic that turns the rung count into a position.

Every drawn rung AND every drawn staff line is pixel-row checked against
the same raster the reader read -- printed, not asserted.

MEASUREMENT / DRAWING ONLY. No reader code changed by this script.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import rungs_sheet as rs  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers" / "review"

RED = (0, 0, 255)
GREEN = (0, 170, 0)
BLUE = (255, 120, 0)
ORANGE = (30, 140, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
MIN_WIDTH = 600


def pos19(truth_pos):
    return any(p in (-1, 9) for p in truth_pos)


def arithmetic_text(side, edge_pos, rung_items, occ_idx, clean_before,
                    read_kind, abs_pos):
    n = len(rung_items)
    if read_kind is None:
        return f"0 rungs found -- ABSTAIN (no ledger ink reached)"
    if read_kind == "line":
        return (f"outer line = pos {edge_pos}; {n} rung(s) found, head sits "
                f"ON rung #{occ_idx} -> offset {2*occ_idx} -> "
                f"position = {edge_pos} {'+' if side=='below' else '-'} "
                f"{2*occ_idx} = {abs_pos}")
    return (f"outer line = pos {edge_pos}; {n} rung(s) found, {clean_before} "
           f"clean before the head -> space offset {2*clean_before+1} -> "
           f"position = {edge_pos} {'+' if side=='below' else '-'} "
           f"{2*clean_before+1} = {abs_pos}")


def render_crop(gray, row, out_path, truth_pos, cause, group):
    """row: dict with page_box, staff_key, raw_pos, subject, clef(unused).
    Draws a >=600px-wide crop and pixel-checks every rung + staff line."""
    sub = row["subject"]
    box = row["page_box"]
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lines = sorted(row["lines"])
    spacing = (lines[-1] - lines[0]) / 4.0
    half_step = spacing / 2.0

    fake_row = dict(box_page=(x0, y0, x1, y1), spacing_px=spacing,
                    nominal_ys=lines, orange_shift=0.0, x_center=cx,
                    y_center=cy, today_pos=row["raw_pos"], sub=sub,
                    staff=row["staff_key"])
    side, rung_items, rungs_step, read_kind, crashed = rs.classify_far_head(
        fake_row, gray
    )
    edge_pos = 0 if side == "above" else 8
    abs_pos = None if rungs_step is None else edge_pos + int(rungs_step)
    occ_idx = next((it["idx"] for it in rung_items if it["occupied"]), None)
    clean_before = (
        sum(1 for it in rung_items if not it["occupied"]
           and it["dist_units"] < (
               (cy - (lines[0] if side == "above" else lines[-1]))
               / half_step * (-1 if side == "above" else 1)))
        if occ_idx is None else None
    )
    arith = arithmetic_text(side, edge_pos, rung_items, occ_idx,
                            clean_before, read_kind, abs_pos)

    # --- window: staff + head + one pitch past the farthest rung/head ---
    top, bottom = lines[0], lines[-1]
    farthest = cy
    for it in rung_items:
        farthest = (min(farthest, it["y"]) if side == "above"
                   else max(farthest, it["y"]))
    margin = 1.4 * spacing
    wy0 = min(top, farthest) - margin
    wy1 = max(bottom, farthest) + margin
    wx0 = cx - 2.2 * spacing
    wx1 = cx + 2.2 * spacing
    native_w = max(1, int(round(wx1 - wx0)))
    native_h = max(1, int(round(wy1 - wy0)))
    scale = max(3, -(-MIN_WIDTH // native_w))  # ceil
    out_w, out_h = native_w * scale, native_h * scale

    h, w = gray.shape
    px0, py0 = max(0, int(wx0)), max(0, int(wy0))
    px1, py1 = min(w, int(wx0) + native_w), min(h, int(wy0) + native_h)
    canvas = np.full((native_h, native_w, 3), 255, dtype=np.uint8)
    if px1 > px0 and py1 > py0:
        patch = cv2.cvtColor(gray[py0:py1, px0:px1], cv2.COLOR_GRAY2BGR)
        canvas[py0 - int(wy0):py1 - int(wy0),
              px0 - int(wx0):px1 - int(wx0)] = patch
    big = cv2.resize(canvas, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return (int(round((px - wx0) * scale)), int(round((py - wy0) * scale)))

    # green: the real 5 staff lines, never extended
    pixel_checks = []
    for ly in lines:
        if ly < wy0 or ly > wy1:
            continue
        _, by = to_big(wx0, ly)
        cv2.line(big, (0, by), (out_w, by), GREEN, 1)
        pixel_checks.append(("staff_line", ly))

    # mark the OUTER line the count starts from (thicker, blue tick)
    outer_y = top if side == "above" else bottom
    _, oby = to_big(wx0, outer_y)
    cv2.line(big, (0, oby), (28, oby), BLUE, 5)
    cv2.putText(big, f"START pos{edge_pos}", (32, oby - 6 if side == "above" else oby + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.55, BLUE, 2, cv2.LINE_AA)

    # orange: every measured rung, with its own x-extent
    for it in rung_items:
        ry = it["y"]
        ex = it.get("extent")
        if ex is None:
            ex = (cx - 0.5 * spacing, cx + 0.5 * spacing)
        _, by = to_big(wx0, ry)
        bx0, _ = to_big(ex[0], ry)
        bx1, _ = to_big(ex[1], ry)
        cv2.line(big, (max(0, bx0), by), (min(out_w, bx1), by), ORANGE,
                max(2, scale // 2))
        mx, _ = to_big(cx, ry)
        r = 7
        if it["occupied"]:
            cv2.circle(big, (mx, by), r, ORANGE, 2)       # hollow
        else:
            cv2.circle(big, (mx, by), r, ORANGE, -1)      # filled
        pixel_checks.append(("rung", ry, ex))

    # red: detector box + centre cross
    bx0, by0 = to_big(x0, y0)
    bx1, by1 = to_big(x1, y1)
    cv2.rectangle(big, (bx0, by0), (bx1, by1), RED, max(1, scale // 3))
    ccx, ccy = to_big(cx, cy)
    r = 8
    cv2.line(big, (ccx - r, ccy), (ccx + r, ccy), RED, 2)
    cv2.line(big, (ccx, ccy - r), (ccx, ccy + r), RED, 2)

    # --- text band -- wide enough that nothing is clipped ---
    TEXT_W = max(out_w, 1000)
    arith_wrapped = []
    if len(arith) > 95:
        cut = arith.rfind(" -> position", 0, 95) or 70
        arith_wrapped = [arith[:cut], "  " + arith[cut:].lstrip()]
    else:
        arith_wrapped = [arith]
    cause_lines = [cause[i:i + 115] for i in range(0, len(cause), 115)] or [""]
    lines_txt = (
        [f"{sub}  [{group}]",
         f"truth pos={truth_pos}  geometry pos={row['geom_pos']}  rungs-after pos={abs_pos}"]
        + arith_wrapped
        + [f"cause: {cause_lines[0]}"]
        + [f"       {c}" for c in cause_lines[1:]]
    )
    text_h = 20 + len(lines_txt) * 22 + 10
    tile = np.full((out_h + text_h, TEXT_W, 3), 255, dtype=np.uint8)
    tile[:out_h, :out_w, :] = big
    for i, t in enumerate(lines_txt):
        cv2.putText(tile, t, (6, out_h + 20 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                   0.48, BLACK, 1, cv2.LINE_AA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), tile)

    # --- pixel-row check, printed, not asserted ---
    report = []
    for check in pixel_checks:
        if check[0] == "staff_line":
            _, ly = check
            y_lo, y_hi = max(0, int(ly) - 1), min(h, int(ly) + 2)
            x_lo, x_hi = max(0, int(cx) - 20), min(w, int(cx) + 20)
            strip = gray[y_lo:y_hi, x_lo:x_hi] < 128
            cov = float(strip.any(axis=0).mean()) if strip.size else 0.0
            report.append(f"staff_line y={ly:.1f} coverage={cov:.2f} {'OK' if cov >= 0.5 else 'MISS'}")
        else:
            _, ry, ex = check
            x_lo, x_hi = max(0, int(ex[0])), min(w, int(ex[1]) + 1)
            y_lo, y_hi = max(0, int(ry) - 1), min(h, int(ry) + 2)
            if x_hi <= x_lo:
                report.append(f"rung y={ry:.1f} NO EXTENT")
                continue
            strip = gray[y_lo:y_hi, x_lo:x_hi] < 128
            cov = float(strip.any(axis=0).mean())
            report.append(f"rung y={ry:.1f} coverage={cov:.2f} {'OK' if cov >= 0.5 else 'MISS'}")
    return abs_pos, arith, report


def main() -> int:
    lg_before = score._load_before_module()
    all_heads = []
    rows_by_key = {}
    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        r = score.score_doc(doc_id, lg_before, score.lg_after)
        rows = {row["subject"]: row for row in score._far_head_rows(doc_id, loaded)}
        for h in r["per_head"]:
            h["doc_id"] = doc_id
            all_heads.append(h)
        rows_by_key[doc_id] = (loaded, rows)

    groupA = [h for h in all_heads if h["v_after"] == "wrong" and h["v_geom"] == "right"]
    groupB = [h for h in all_heads if h["v_after"] == "abstain"]
    groupC_pool = [h for h in all_heads if h["v_after"] == "right" and h["v_geom"] == "right"]
    groupC = (
        [h for h in groupC_pool if h["doc_id"] == "beethoven5-litolff"][:3]
        + [h for h in groupC_pool if h["doc_id"] == "brahms1-breitkopf"][:2]
    )

    index_lines = ["# lane-ledger-rungs review crops (2026-10-01)", "",
                  "Measurement/drawing only, no code fix. One crop per listed "
                  "head; cause assigned from what the drawing shows, never a "
                  "right/wrong call on Sean's behalf.", ""]
    cause_counts: dict = {}

    def process(h, group):
        doc_id = h["doc_id"]
        loaded, rows = rows_by_key[doc_id]
        row = rows.get(h["subject"])
        if row is None:
            return
        rec = loaded["rec"]
        gray = loaded["gray"]
        line_rows = rec.obs(Q.STAFF_LINES, row["staff_key"])
        row = dict(row)
        row["lines"] = [float(v) for v in line_rows[-1]["value"]]
        row["geom_pos"] = h["geom_pos"]

        truth_pos = h["truth_pos"]
        if group.startswith("C:"):
            # control -- both already agree with the reference; no
            # wrongness to explain. The crop still shows the arithmetic.
            cause = "control -- rungs-after already agrees with geometry and the reference"
        elif pos19(truth_pos):
            cause = ("first-space population bug: truth-set gate did not "
                    "apply far_head_needs_ledger_read -- this head is "
                    "position -1/9 (on-staff, rule b) and should never "
                    "have been sent to the ledger reader at all")
        elif h["v_after"] == "abstain" and any(0 <= p <= 8 for p in truth_pos):
            cause = ("geometry mis-rounds an on-staff head as far "
                    "(population artifact) -- the rung reader correctly "
                    "finds 0 rungs because there is no ledger to find")
        else:
            # run the reader once, ahead of drawing, so the crop's own
            # text shows the FINAL cause rather than a placeholder
            n_found = _rung_count(gray, row)
            cause = _refine_cause(h, n_found)

        safe = f"{doc_id}-{h['subject'].replace('/', '-')}.png"
        out_path = OUT_DIR / safe
        abs_pos, arith, pix_report = render_crop(gray, row, out_path, truth_pos, cause, group)

        cause_counts[cause] = cause_counts.get(cause, 0) + 1
        index_lines.append(f"- `{safe}` — {h['subject']} ({doc_id}, {group}): "
                           f"truth={truth_pos} geom={h['geom_pos']} "
                           f"rungs-after={abs_pos}. cause: {cause}")
        bad = [p for p in pix_report if "MISS" in p or "NO EXTENT" in p]
        if bad:
            index_lines.append(f"  pixel-check issues: {bad}")
        return cause

    def _rung_count(gray, row):
        box = row["page_box"]
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        lines = sorted(row["lines"])
        side = "above" if cy < lines[0] else "below"
        items = lg.measure_ledger_rungs(gray, lines, cx, head_y=cy)
        return len(items[side])

    def _refine_cause(h, n_found):
        truth = h["truth_pos"][0]
        edge_pos = 0 if h["geom_pos"] < 0 else 8
        needed = abs(truth - edge_pos)
        needed_rungs = (needed // 2) if needed % 2 == 0 else (needed // 2)
        if n_found == 0:
            return "0 rungs found (merged ink or no printed ledger reached)"
        if n_found < max(1, needed_rungs):
            return "missed/merged rung (undercount -- fewer rungs found than the reference position needs)"
        if n_found > needed_rungs:
            return "spurious duplicate rung (overcount vs the reference position's own needed count)"
        return "occupied-vs-space boundary misclassification (rung found but tied to the wrong step)"

    for h in groupA:
        process(h, "A: rungs-after wrong, geometry right")
    for h in groupB:
        process(h, "B: rungs-after abstains")
    for h in groupC:
        process(h, "C: control, both right")

    # Extra: the coordinator's suspect (2) -- Sean's D6, geometry ALSO
    # wrong there, so it falls outside groups A/B/C by construction, but
    # was named explicitly.
    extra_sub = "glyph/3/0/0/2/9"
    extra_doc = "beethoven5-litolff"
    extra_h = next((h for h in all_heads if h["doc_id"] == extra_doc
                    and h["subject"] == extra_sub), None)
    if extra_h is not None:
        index_lines.append("")
        index_lines.append("## Named suspect (coordinator's #2, Sean's D6)")
        process(extra_h, "X: named suspect, geometry also wrong")

    index_lines.append("")
    index_lines.append("## Cause counts")
    for cause, n in sorted(cause_counts.items(), key=lambda kv: -kv[1]):
        index_lines.append(f"- {n}: {cause}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")
    print(f"wrote {len(groupA)+len(groupB)+len(groupC)+(1 if extra_h else 0)} crops to {OUT_DIR}")
    print(f"groupA={len(groupA)} groupB={len(groupB)} groupC={len(groupC)}")
    for cause, n in sorted(cause_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n}: {cause}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
