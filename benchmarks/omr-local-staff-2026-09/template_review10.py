#!/usr/bin/env python3
"""lane-ledger-template-fix (2026-10-04): ONE review sheet, no scoring.

Sean: "no scoring this round, only templates and one review sheet."
This script builds geometry templates (`measure_head_tilt.py`'s tilt) and
MATCHES them against real far heads for DISPLAY. Nothing is tallied.

Per tile (real GREYSCALE print, centred on the detector box):
  RED thin box   = detector box
  BLUE oval      = the best-matching geometry head (1.3 x 1.0 staff
                   spaces, tilted at the measured angle) at the height
                   the matcher chose
  ORANGE lines   = staff lines read at the head's own x
                   (`score.frame_lines_for_head` = `local_staff_lines`)
                   and the ledgers the round-8 rung reader measured
                   (`ledger_grid.measure_ledger_rungs`, four_causes_cd=True,
                   exactly the arguments `score.reader_absolute_position`
                   uses) -- never a thin-row scan, never extrapolated.
Label: ONE template answer (the matcher's variant, `on a line` / `in a
space`) with its step read off the MEASURED ladder, then round 8's step
(`score.reader_absolute_position(four_causes_cd=True)`, as
`score_four_causes_cd.py` calls it) and the reference.

Population: far heads that HAVE a reference (the `score_doc` population);
the three round-8-undecided heads the first sheet used are kept. A
second sheet (`template_review10_controls.jpg`) shows the heads the
manager named, for the diagnostics only.

    python3 benchmarks/omr-local-staff-2026-09/template_review10.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import score_head_template as sht  # noqa: E402
import measure_head_tilt as mht  # noqa: E402
import combined_scorer as cs  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers"
OUT_PATH = OUT_DIR / "template_review10.jpg"
CONTROLS_PATH = OUT_DIR / "template_review10_controls.jpg"
CHECKS_PATH = OUT_DIR / "template_review10_checks.json"
MAX_SHEET_W = 2600
JPEG_QUALITY = 88
HALF_W_SPACES = 2.6   # crop is CENTRED on the detector box centre
HALF_H_SPACES = 3.2
TARGET_TILE_SPACING_PX = 90  # one staff space ~90 px on the tile (>= x3)
LEDGER_DRAW_BEYOND_BOX_SPACES = 0.6  # ledger line drawn this far past the box
STUB_ZONE_SPACES = 0.25      # stub check zone just outside each box edge
                             # (ledger_grid needs a stub >= 0.15 sp)
MISS_FRACTION = 0.6          # an orange line below this is a MISS

RED = (0, 0, 220)
ORANGE = (30, 140, 255)
BLUE = (255, 80, 0)
BLACK = (0, 0, 0)

#: round-8-undecided heads the first sheet used (kept).
MUST_INCLUDE = ["glyph/3/0/7/0/7", "glyph/3/0/7/2/4", "glyph/3/0/8/6/10"]
#: heads the manager named -- rendered on the controls sheet only.
CONTROL_SUBJECTS = {
    "beethoven5-litolff": ["glyph/1/0/9/14/8", "glyph/1/0/11/2/3", "glyph/1/0/9/3/5"],
    "brahms1-breitkopf": ["glyph/0/0/0/0/5", "glyph/0/0/0/0/6", "glyph/0/0/0/6/20"],
}


def _select(doc_id, rows_by_subject, scored_subjects, boxes_by_page, want):
    """Diverse, hand-stated mix (kind x side x parity) from the heads that
    HAVE a reference. Never chosen by agreement with any reader."""
    out, seen = [], set()
    for sub in MUST_INCLUDE:
        if sub in rows_by_subject and sub in scored_subjects:
            out.append(rows_by_subject[sub]); seen.add(sub)
    buckets = {}
    for sub in sorted(scored_subjects):
        if sub in seen or sub not in rows_by_subject:
            continue
        r = rows_by_subject[sub]
        entry = {s: (cls, b) for (s, cls, b) in boxes_by_page.get(r["page"], [])}
        found = entry.get(sub)
        if found is None:
            continue
        cls = found[0]
        kind = "filled" if "Black" in cls else ("hollow" if (
            "Half" in cls or "Whole" in cls) else None)
        if kind is None:
            continue
        pos = int(round(r["raw_pos"]))
        key = (kind, "above" if pos < 4 else "below",
               "on_ledger" if pos % 2 == 0 else "in_space")
        buckets.setdefault(key, []).append(r)
    keys = sorted(buckets)
    i = 0
    while len(out) < want and keys:
        key = keys[i % len(keys)]
        if buckets[key]:
            r = buckets[key].pop(0)
            out.append(r); seen.add(r["subject"])
            i += 1
        else:
            keys.remove(key)
    return out[:want]


def _ladder(lines, rungs, side):
    """[(y, step)] -- the 5 staff lines (steps 0,2,..,8) plus the
    MEASURED ledger rungs, nearest-edge-first, 2 half-steps apiece."""
    ys = sorted(lines)
    ladder = [(y, 2 * i) for i, y in enumerate(ys)]
    for i, ry in enumerate(rungs):
        ladder.append((ry, -2 * (i + 1) if side == "above" else 8 + 2 * (i + 1)))
    return sorted(ladder)


def _template_step(variant, mcy, ladder, spacing, side):
    """The template's ONE answer as a step on the measured ladder, plus a
    flag where the ladder cannot support it."""
    if variant is None:
        return None, "no template answer"
    ys = [y for y, _ in ladder]
    near_i = int(np.argmin([abs(y - mcy) for y in ys]))
    dy = (mcy - ys[near_i]) / spacing
    if variant == "on_line":
        if abs(dy) <= 0.5:
            return ladder[near_i][1], ("" if abs(dy) <= 0.25 else
                                       f"oval {dy:+.2f} sp off that line")
        return ladder[near_i][1], f"NO measured line within half a space ({dy:+.2f} sp)"
    above = [(y, p) for y, p in ladder if y < mcy]
    below = [(y, p) for y, p in ladder if y >= mcy]
    if above and below:
        pa, pb = above[-1][1], below[0][1]
        if abs(pb - pa) == 2:
            return (pa + pb) // 2, ""
        return (pa + pb) / 2.0, "gap between measured lines is not one space"
    if side == "above" and below:
        return below[0][1] - 1, "beyond the outermost measured ledger"
    if side == "below" and above:
        return above[-1][1] + 1, "beyond the outermost measured ledger"
    return None, "no ladder"


def _line_dark_fraction(ink, y_page, cy0, cols):
    r = int(round(y_page - cy0))
    if r < 1 or r >= ink.shape[0] - 1 or len(cols) == 0:
        return None
    band = ink[r - 1:r + 2, :]
    return float(band.any(axis=0)[cols].mean())


def _head_tile(doc_id, row, rec, pages, templates_by_page, outer_tilt,
               boxes_by_page, nh_boxes_by_page, acc_boxes_by_page):
    box = row["page_box"]
    staff_key = row["staff_key"]
    global_lines = [float(y) for y in rec.obs(Q.STAFF_LINES, staff_key)[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    subject = row["subject"]
    page_boxes = boxes_by_page.get(row["page"], [])
    nh_boxes = nh_boxes_by_page.get(row["page"], [])
    acc_boxes = acc_boxes_by_page.get(row["page"], [])
    entry = {sb: (cls, b) for (sb, cls, b) in page_boxes}
    cls, _b = entry.get(subject, ("noteheadBlackOnLine", box))
    kind = "filled" if "Black" in cls else "hollow"
    # Exclude exactly what round 8 excludes: OTHER noteheads + accidentals.
    # (The first fixed sheet excluded EVERY other detection, so a ledgerLine /
    # slur / beam box overlapping the head blanked the head's own ink and the
    # matcher scored exactly 0.0 -> default height.)
    others = ([b for (sb, b) in nh_boxes if sb != subject]
              + [b for (_sb, b) in acc_boxes])
    templates = sht.templates_for_page(templates_by_page, row["page"])
    match = ht.match_head_template(gray, box, spacing, templates,
                                   exclude_boxes=others, kind=kind)

    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    clef_v = rec.value(Q.CLEF, staff_key)
    truth_pos = sorted(set(score.truth_positions(row["truth_pitches"], str(clef_v))))
    geom_pos = int(round(row["raw_pos"]))
    # round 8, exactly as score_four_causes_cd.py / score_doc call it
    r8_pos, r8_why = score.reader_absolute_position(
        gray, lines, box, subject, nh_boxes,
        page_accidental_boxes=acc_boxes, four_causes_cd=True)
    rungs, _sp, side = cs._rungs_y_for_head(
        gray, lines, box, subject, nh_boxes,
        page_accidental_boxes=acc_boxes, four_causes_cd=True)

    var = match["best_variant"] if match and match.get("best_variant") else None
    mcy = match["center_y"] if match else cy
    ladder = _ladder(lines, rungs, side)
    step, flag = _template_step(var, mcy, ladder, spacing, side)

    # centred window (clamped only by the page edge)
    cx0 = int(round(cx - HALF_W_SPACES * spacing)); cx1 = int(round(cx + HALF_W_SPACES * spacing))
    cy0 = int(round(cy - HALF_H_SPACES * spacing)); cy1 = int(round(cy + HALF_H_SPACES * spacing))
    H, W = gray.shape
    gcrop = np.full((cy1 - cy0, cx1 - cx0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(0, cx0), max(0, cy0), min(W, cx1), min(H, cy1)
    gcrop[sy0 - cy0:sy1 - cy0, sx0 - cx0:sx1 - cx0] = gray[sy0:sy1, sx0:sx1]
    ink = gcrop <= ht._otsu_threshold(gcrop)   # for the CHECKS only, never shown
    zoom = max(3, int(round(TARGET_TILE_SPACING_PX / spacing)))
    img = cv2.cvtColor(gcrop, cv2.COLOR_GRAY2BGR)
    img = cv2.resize(img, (img.shape[1] * zoom, img.shape[0] * zoom),
                     interpolation=cv2.INTER_CUBIC)

    def T(px, py):
        return (int(round((px - cx0 + 0.5) * zoom)), int(round((py - cy0 + 0.5) * zoom)))

    bx0c, bx1c = int(round(x0 - cx0)), int(round(x1 - cx0))
    cxc = cx - cx0
    ncols = ink.shape[1]
    out_box = np.array([c for c in range(ncols) if not (bx0c <= c <= bx1c)])
    zone = max(2, int(round(STUB_ZONE_SPACES * spacing)))
    left_cols = np.array([c for c in range(bx0c - zone, bx0c) if 0 <= c < ncols])
    right_cols = np.array([c for c in range(bx1c + 1, bx1c + 1 + zone) if 0 <= c < ncols])
    draw_beyond = LEDGER_DRAW_BEYOND_BOX_SPACES * spacing
    line_checks = []
    for y in lines:                      # staff lines: full tile width
        if cy0 + 1 <= y <= cy1 - 2:
            cv2.line(img, T(cx0, y), T(cx1, y), ORANGE, 1)
            line_checks.append(dict(what="staff", y=round(float(y), 1),
                                    dark=_line_dark_fraction(ink, y, cy0, out_box)))
    for y in rungs:                      # ledgers: +-1.4 sp around the head
        if cy0 + 1 <= y <= cy1 - 2:
            cv2.line(img, T(x0 - draw_beyond, y), T(x1 + draw_beyond, y), ORANGE, 1)
            dl = _line_dark_fraction(ink, y, cy0, left_cols)
            dr = _line_dark_fraction(ink, y, cy0, right_cols)
            line_checks.append(dict(what="ledger", y=round(float(y), 1),
                                    dark_left=dl, dark_right=dr,
                                    dark=max(v for v in (dl, dr, -1.0) if v is not None)))
    for lc in line_checks:
        for k in ("dark", "dark_left", "dark_right"):
            if lc.get(k) is not None:
                lc[k] = round(lc[k], 2)
        if lc.get("dark") is not None and lc["dark"] >= 0:
            lc["MISS"] = lc["dark"] < MISS_FRACTION

    tilt = outer_tilt.get(kind, 0.0)
    pts = ht.geometry_outline_poly((cx - cx0 + 0.5) * zoom, (mcy - cy0 + 0.5) * zoom,
                                   spacing * zoom, tilt).astype(np.int32)
    cv2.polylines(img, [pts], True, BLUE, 2, cv2.LINE_AA)
    cv2.rectangle(img, T(x0, y0), T(x1, y1), RED, 1)

    # --- pixel self-check numbers ---
    hy0, hy1 = max(0, int(y0 - cy0)), int(y1 - cy0)
    bi = ink[hy0:hy1, max(0, bx0c):bx1c]
    ys_i, xs_i = np.nonzero(bi)
    ink_cy_page = (ys_i.mean() + hy0 + cy0) if ys_i.size else None
    tm = np.zeros(ink.shape, np.uint8)
    cv2.fillPoly(tm, [np.array([[int(round(x - cx0)), int(round(y - cy0))]
                                for x, y in ht.geometry_outline_poly(
                                    cx, mcy, spacing, tilt)], np.int32)], 1)
    t_in_ink = float((ink & (tm > 0)).sum() / max(1, int(tm.sum())))
    hb = np.zeros(ink.shape, bool)
    hb[hy0:hy1, max(0, bx0c):bx1c] = True
    head_ink = ink & hb
    head_cov = float((head_ink & (tm > 0)).sum() / max(1, head_ink.sum()))

    # item-4 diagnostic: why that height? score at chosen vs ink-centred
    diag = {}
    if match and match.get("shift_scores") and var and ink_cy_page is not None:
        ss = match["shift_scores"][var]
        chosen = int(round(mcy - cy))
        ink_shift = int(round(ink_cy_page - cy))
        near = min(ss, key=lambda s: abs(s - ink_shift)) if ss else None
        diag = dict(chosen_shift_px=chosen, ink_centroid_shift_px=ink_shift,
                    score_at_chosen=round(ss.get(chosen, float("nan")), 3),
                    score_at_ink_centre=(round(ss[near], 3) if near is not None else None),
                    oval_minus_ink_centre_px=round(float(mcy - ink_cy_page), 1),
                    oval_minus_ink_centre_sp=round(float(mcy - ink_cy_page) / spacing, 2))
    check = dict(doc=doc_id, subject=subject, kind=kind, zoom=zoom,
                 spacing=round(spacing, 1), variant=var, template_step=step,
                 template_flag=flag, round8_step=r8_pos, round8_reason=r8_why,
                 reference=truth_pos, geometry=geom_pos,
                 box_ink_frac=round(float(bi.mean()) if bi.size else 0.0, 2),
                 tmpl_in_ink=round(t_in_ink, 2), head_ink_covered=round(head_cov, 2),
                 lines=line_checks, diag=diag)

    und = "  (UNDECIDED, low margin)" if (match is None or match.get("undecided")) else ""
    where = {"on_line": "on a line", "in_space": "in a space"}.get(var, "no answer")
    ref_txt = ",".join(str(p) for p in truth_pos) if truth_pos else "none"
    r8_txt = f"step {r8_pos}" if r8_pos is not None else "abstains"
    lines_text = [
        f"{doc_id.split('-')[0]} {subject} ({kind})",
        f"template: {where}, step {step}{und}" + (f"  [{flag}]" if flag else ""),
        f"round 8: {r8_txt}    reference: {ref_txt}",
    ]
    font, fs = cv2.FONT_HERSHEY_SIMPLEX, 0.55
    tw = max(cv2.getTextSize(t, font, fs, 1)[0][0] for t in lines_text)
    cw = max(img.shape[1], tw + 16)
    lh = 24 * (len(lines_text) + 1)
    out = np.full((img.shape[0] + lh, cw, 3), 255, np.uint8)
    out[:img.shape[0], :img.shape[1]] = img
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, img.shape[0] + 22 + i * 24), font, fs, BLACK, 1, cv2.LINE_AA)
    return out, check


def _templates_panel(doc_id, templates_by_page, info):
    tiles = []
    page = sorted(k for k in templates_by_page.keys() if k != "pooled")[0]
    tmpls = templates_by_page[page]
    for key in sorted(tmpls.keys()):
        kind, variant = key
        img = (tmpls[key].img * 255).clip(0, 255).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        img = cv2.resize(img, (img.shape[1] * 2, img.shape[0] * 2),
                         interpolation=cv2.INTER_NEAREST)
        cv2.putText(img, f"{kind}/{variant}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(img)
    h = max(t.shape[0] for t in tiles)
    row = np.full((h, sum(t.shape[1] for t in tiles) + 8 * (len(tiles) - 1), 3),
                  255, dtype=np.uint8)
    x = 0
    for t in tiles:
        row[:t.shape[0], x:x + t.shape[1]] = t
        x += t.shape[1] + 8
    out = np.full((row.shape[0] + 20, row.shape[1], 3), 255, dtype=np.uint8)
    out[:row.shape[0], :row.shape[1]] = row
    cv2.putText(out, f"{doc_id} templates (page {page}): {info}"[:200], (4, row.shape[0] + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, BLACK, 1, cv2.LINE_AA)
    return out


def _grid(tiles, cols=2):
    tw = max(t.shape[1] for t in tiles); th = max(t.shape[0] for t in tiles)
    rows_n = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows_n * th, cols * tw, 3), 255, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * th:r * th + t.shape[0], c * tw:c * tw + t.shape[1]] = t
    return sheet


def _legend(width):
    text = ("RED box = detector box.   BLUE oval = best-matching geometry head "
            "(1.3 x 1.0 staff spaces, tilted at the measured angle) at the height "
            "the matcher chose.   ORANGE = staff lines at the head's x + the ledgers "
            "round 8 measured.   Greyscale = the real print.")
    img = np.full((34, width, 3), 255, np.uint8)
    cv2.putText(img, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BLACK, 1, cv2.LINE_AA)
    return img


def _finish(tiles, extra_top=None):
    grid = _grid(tiles)
    parts = [_legend(grid.shape[1])]
    if extra_top is not None:
        w = grid.shape[1]
        if extra_top.shape[1] < w:
            pad = np.full((extra_top.shape[0], w, 3), 255, np.uint8)
            pad[:, :extra_top.shape[1]] = extra_top
            extra_top = pad
        parts.append(extra_top)
    sheet = np.vstack(parts + [grid])
    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)
    return sheet


def main() -> int:
    panels, main_tiles, ctrl_tiles, checks = [], [], [], []
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        measurements = mht.collect_doc_measurements(doc_id)
        summary = mht.summarize(doc_id, measurements)
        outer_tilt = {k: v.get("outer_tilt_deg", 0.0) for k, v in summary.items()}
        templates_by_page, info = sht.build_geometry_templates_for_doc(doc_id)
        panels.append(_templates_panel(doc_id, templates_by_page, info))

        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        rows = score._far_head_rows(doc_id, loaded)
        rows_by_subject = {r["subject"]: r for r in rows if r.get("page_box")}
        # the score_doc population = far heads that HAVE a reference
        scored = set()
        for r in rows:
            if r["subject"] == "glyph/1/0/10/14/1" or not r["truth_pitches"] or not r.get("page_box"):
                continue
            clef_v = rec.value(Q.CLEF, r["staff_key"])
            if clef_v is not None and score.truth_positions(r["truth_pitches"], str(clef_v)):
                scored.add(r["subject"])
        boxes_by_page = sht._page_glyph_boxes(rec)
        nh = score._notehead_boxes_by_page(rec)
        acc = score._accidental_boxes_by_page(rec)
        want = 7 if doc_id == "beethoven5-litolff" else 3
        for row in _select(doc_id, rows_by_subject, scored, boxes_by_page, want):
            tile, chk = _head_tile(doc_id, row, rec, pages, templates_by_page,
                                   outer_tilt, boxes_by_page, nh, acc)
            main_tiles.append(tile); checks.append(dict(chk, sheet="main"))
        for sub in CONTROL_SUBJECTS.get(doc_id, []):
            if sub in rows_by_subject:
                tile, chk = _head_tile(doc_id, rows_by_subject[sub], rec, pages,
                                       templates_by_page, outer_tilt,
                                       boxes_by_page, nh, acc)
                ctrl_tiles.append(tile); checks.append(dict(chk, sheet="controls"))
        print()

    panel_w = max(p.shape[1] for p in panels)
    stack = []
    for p in panels:
        if p.shape[1] != panel_w:
            p = cv2.resize(p, (panel_w, int(p.shape[0] * panel_w / p.shape[1])))
        stack.append(p)
    top = np.vstack(stack)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), _finish(main_tiles, top), [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    cv2.imwrite(str(CONTROLS_PATH), _finish(ctrl_tiles), [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    CHECKS_PATH.write_text(json.dumps(checks, indent=1, default=str))
    for c in checks:
        miss = [l for l in c["lines"] if l.get("MISS")]
        print(f"{c['sheet']:8} {c['subject']:<18} {c['kind']:<6} var={c['variant']} step={c['template_step']} "
              f"r8={c['round8_step']} ref={c['reference']}  MISSES={miss}")
    print(f"wrote {OUT_PATH} ({len(main_tiles)} tiles) and {CONTROLS_PATH} ({len(ctrl_tiles)} tiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
