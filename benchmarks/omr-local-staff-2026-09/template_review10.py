#!/usr/bin/env python3
"""lane-ledger-template (2026-10-02, Sean): ONE review sheet, no re-score.

Sean, after reading `template_geom_templates.jpg`: "NO SCORING this
round, only templates and one review sheet." Manager's read of that
sheet: (1) the ~2 deg outer tilt was an artefact of fitting WITH the
staff lines left in; (2) the hollow template (thin ring, big empty
centre) does not look like a real Litolff half note; (3) the "real
head" comparison panels were not framed on the heads at all.

This script does NOT call `score_head_template.score_doc_with_templates`
or anything that compares a reader's answer to round 8 -- it only builds
geometry templates (`measure_head_tilt.py`'s re-measured, line-masked
tilt + axis-ratio numbers) and MATCHES them against 10 real far heads
for display. A verdict (on-line/space, margin) and a reference TICK are
shown for visual calibration only -- never tallied, never compared to
round 8.

    python3 benchmarks/omr-local-staff-2026-09/template_review10.py
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
import score_head_template as sht  # noqa: E402
import measure_head_tilt as mht  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.geometry import (  # noqa: E402
    STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES,
)
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers"
OUT_PATH = OUT_DIR / "template_review10.jpg"
MAX_SHEET_W = 2600
JPEG_QUALITY = 85
ZOOM = 4
PAD_SPACES_X = 2.2
PAD_SPACES_Y = 2.8  # generous -- ledgers must be fully in frame

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
CYAN = (220, 200, 0)
YELLOW = (0, 220, 220)
BLACK = (0, 0, 0)

#: Always-included subjects (the brief's own named heads).
MUST_INCLUDE = ["glyph/3/0/7/0/7", "glyph/3/0/7/2/4", "glyph/3/0/8/6/10"]


def _position_to_y(pos: float, lines, spacing: float) -> float:
    return lines[0] + pos * (spacing / 2.0)


def _select_10(doc_id: str, loaded) -> list:
    """A diverse, hand-stated mix -- filled/hollow, above/below,
    on-ledger/in-space -- NEVER chosen by truth agreement (CLAUDE.md
    rule 5, "no default flips on agreement with our own reading"). Class
    and parity are GATHER facts (detector class, staff position's own
    parity), not a truth comparison."""
    rec = loaded["rec"]
    rows = score._far_head_rows(doc_id, loaded)
    boxes_by_page = sht._page_glyph_boxes(rec)
    out = []
    seen = set()
    must = [r for r in rows if r["subject"] in MUST_INCLUDE]
    for r in must:
        out.append(r)
        seen.add(r["subject"])

    buckets = {}
    for r in rows:
        if r["subject"] in seen:
            continue
        entry = {s: (cls, box) for (s, cls, box) in boxes_by_page.get(r["page"], [])}
        found = entry.get(r["subject"])
        if found is None:
            continue
        cls, _box = found
        kind = "filled" if "Black" in cls else ("hollow" if (
            "Half" in cls or "Whole" in cls) else None)
        if kind is None:
            continue
        pos = int(round(r["raw_pos"]))
        side = "above" if pos < 4 else "below"
        parity = "on_ledger" if pos % 2 == 0 else "in_space"
        key = (kind, side, parity)
        buckets.setdefault(key, []).append(r)

    need = 10 - len(out)
    keys = sorted(buckets.keys())
    i = 0
    while need > 0 and keys:
        key = keys[i % len(keys)]
        bucket = buckets.get(key, [])
        if bucket:
            r = bucket.pop(0)
            if r["subject"] not in seen:
                out.append(r)
                seen.add(r["subject"])
                need -= 1
        else:
            keys.remove(key)
            if not keys:
                break
            continue
        i += 1
    return out[:10]


HALF_W_SPACES = 2.6   # crop is CENTRED on the detector box centre
HALF_H_SPACES = 3.2
TARGET_TILE_SPACING_PX = 90  # zoom so one staff space is ~90 px (>= x3)
BLUE = (255, 80, 0)


def _local_ink_rungs(ink: np.ndarray, bx0: int, bx1: int, spacing: float):
    """Rows (crop coords) holding a horizontal line of INK beside the head:
    the strip left of the box and the strip right of it must each be mostly
    ink on one side. Purely local -- nothing extrapolated from staff
    spacing. Returns [(row_centre, band_height)]."""
    h, w = ink.shape
    reach = int(round(1.0 * spacing))
    ls = ink[:, max(0, bx0 - reach):max(0, bx0 - 2)]
    rs = ink[:, min(w, bx1 + 2):min(w, bx1 + reach)]
    def frac(strip):
        return strip.mean(axis=1) if strip.size else np.zeros(h)
    hit = (frac(ls) >= 0.8) | (frac(rs) >= 0.8)
    out, i = [], 0
    while i < h:
        if hit[i]:
            j = i
            while j + 1 < h and hit[j + 1]:
                j += 1
            # a rung is thin: wider than ~0.5 spacing is a blob, not a line
            if (j - i + 1) <= 0.5 * spacing:
                out.append(((i + j) / 2.0, j - i + 1))
            i = j + 1
        else:
            i += 1
    return out


def _head_tile(doc_id, row, rec, pages, templates_by_page, outer_tilt,
               boxes_by_page, acc_boxes_by_page):
    box = row["page_box"]
    staff_key = row["staff_key"]
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    global_lines = [float(y) for y in line_rows[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    subject = row["subject"]
    page_boxes = boxes_by_page.get(row["page"], [])
    entry = {sb: (cls, b) for (sb, cls, b) in page_boxes}
    cls, _b = entry.get(subject, ("noteheadBlackOnLine", box))
    kind = "filled" if "Black" in cls else "hollow"
    others = [b for (sb, c, b) in page_boxes if sb != subject]
    templates = sht.templates_for_page(templates_by_page, row["page"])
    match = ht.match_head_template(gray, box, spacing, templates,
                                   exclude_boxes=others, kind=kind)

    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0   # detector box centre, page px
    clef_v = rec.value(Q.CLEF, staff_key)
    truth_pos = sorted(set(score.truth_positions(row["truth_pitches"], str(clef_v))))
    geom_pos = int(round(row["raw_pos"]))
    r8_pos, _why = score.reader_absolute_position(
        gray, lines, box, subject, [(sb, b) for (sb, c, b) in page_boxes],
        page_accidental_boxes=acc_boxes_by_page.get(row["page"], []),
        four_causes_cd=True)

    # centred window (clamped only by the page edge)
    cx0 = int(round(cx - HALF_W_SPACES * spacing)); cx1 = int(round(cx + HALF_W_SPACES * spacing))
    cy0 = int(round(cy - HALF_H_SPACES * spacing)); cy1 = int(round(cy + HALF_H_SPACES * spacing))
    H, W = gray.shape
    gcrop = np.full((cy1 - cy0, cx1 - cx0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(0, cx0), max(0, cy0), min(W, cx1), min(H, cy1)
    gcrop[sy0 - cy0:sy1 - cy0, sx0 - cx0:sx1 - cx0] = gray[sy0:sy1, sx0:sx1]
    thr = ht._otsu_threshold(gcrop)
    ink = gcrop <= thr
    zoom = max(3, int(round(TARGET_TILE_SPACING_PX / spacing)))
    img = cv2.cvtColor(gcrop, cv2.COLOR_GRAY2BGR)
    img = cv2.resize(img, (img.shape[1] * zoom, img.shape[0] * zoom),
                     interpolation=cv2.INTER_NEAREST)

    def T(px, py):  # page px -> tile px
        return (int(round((px - cx0) * zoom)), int(round((py - cy0) * zoom)))

    bx0c, bx1c = int(round(x0 - cx0)), int(round(x1 - cx0))
    rungs = _local_ink_rungs(ink, bx0c, bx1c, spacing)
    for (rc, _bh) in rungs:  # orange: local ink lines
        yy = int(round((rc + 0.5) * zoom))
        cv2.line(img, (0, yy), (img.shape[1], yy), ORANGE, 2)

    tilt = outer_tilt.get(kind, 0.0)
    mcy = match["center_y"] if match else cy
    poly = ht.geometry_outline_poly(cx, mcy, spacing, tilt)
    # tile-space polygon (poly is built in page px, scaled by one space)
    pts = ht.geometry_outline_poly((cx - cx0) * zoom, (mcy - cy0) * zoom,
                                   spacing * zoom, tilt).astype(np.int32)
    cv2.polylines(img, [pts], True, BLUE, 2, cv2.LINE_AA)
    cv2.rectangle(img, T(x0, y0), T(x1, y1), RED, 1)

    # --- pixel self-check numbers (page px, measured off the ink) ---
    bi = ink[max(0, int(y0 - cy0)):int(y1 - cy0), max(0, bx0c):bx1c]
    box_ink = float(bi.mean()) if bi.size else 0.0
    ys_i, xs_i = np.nonzero(bi)
    cen_off = ((xs_i.mean() + max(0, bx0c)) - (cx - cx0), (ys_i.mean() + max(0, int(y0 - cy0))) - (cy - cy0)) if xs_i.size else (None, None)
    tm = np.zeros(ink.shape, np.uint8)
    cv2.fillPoly(tm, [np.array([[int(round(x - cx0)), int(round(y - cy0))] for x, y in poly], np.int32)], 1)
    t_area = int(tm.sum())
    t_in_ink = float((ink & (tm > 0)).sum() / max(1, t_area))
    # head ink = ink inside the detector box, minus rows that are rungs
    hb = np.zeros(ink.shape, bool)
    hb[max(0, int(y0 - cy0)):int(y1 - cy0), max(0, bx0c):bx1c] = True
    head_ink = ink & hb
    head_cov = float((head_ink & (tm > 0)).sum() / max(1, head_ink.sum()))
    pxs, pys = poly[:, 0], poly[:, 1]
    top_x = pxs[pys == pys.min()].mean() - mcy * 0 - cx
    check = dict(subject=subject, kind=kind, zoom=zoom, spacing=round(spacing, 1),
                 box_ink_frac=round(box_ink, 2),
                 ink_centroid_off_px=tuple(None if v is None else round(float(v), 1) for v in cen_off),
                 tmpl_in_ink=round(t_in_ink, 2), head_ink_covered=round(head_cov, 2),
                 tmpl_w_px=int(pxs.max() - pxs.min()), tmpl_h_px=int(pys.max() - pys.min()),
                 tilt_deg=round(tilt, 1), topmost_x_minus_centre_px=round(float(top_x), 1),
                 n_ink_rungs=len(rungs))

    pos_c = (mcy - lines[0]) / (spacing / 2.0)
    pos_i = int(round(pos_c))
    var = match["best_variant"] if match and match.get("best_variant") else None
    where = {"on_line": "on a line", "in_space": "in a space"}.get(var, "no answer")
    parity_says = "on a line" if pos_i % 2 == 0 else "in a space"
    if var is not None and parity_says != where:
        where += f" (its height implies {parity_says}: disagree)"
    und = "  (UNDECIDED)" if (match is None or match.get("undecided")) else ""
    ref_txt = ",".join(str(p) for p in truth_pos) if truth_pos else "none"
    lines_text = [
        f"{doc_id.split('-')[0]} {subject} ({kind})",
        f"template says: {where}; height step {pos_i}{und}",
        f"round 8: {'abstained' if r8_pos is None else r8_pos}   geometry: {geom_pos}   reference: {ref_txt}",
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
        tmpl = tmpls[key]
        img = (tmpl.img * 255).clip(0, 255).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        img = cv2.resize(img, (img.shape[1] * 3, img.shape[0] * 3),
                         interpolation=cv2.INTER_NEAREST)
        label = f"{kind}/{variant}"
        cv2.putText(img, label, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, BLACK, 1,
                    cv2.LINE_AA)
        tiles.append(img)
    h = max(t.shape[0] for t in tiles)
    row = np.full((h, sum(t.shape[1] for t in tiles) + 8 * (len(tiles) - 1), 3),
                  255, dtype=np.uint8)
    x = 0
    for t in tiles:
        row[:t.shape[0], x:x + t.shape[1]] = t
        x += t.shape[1] + 8
    caption = f"{doc_id} templates (page {page}): {info}"
    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
    out = np.full((row.shape[0] + 20, row.shape[1], 3), 255, dtype=np.uint8)
    out[:row.shape[0], :row.shape[1]] = row
    cv2.putText(out, caption[:180], (4, row.shape[0] + 15), font, font_scale, BLACK,
                thickness, cv2.LINE_AA)
    return out


def main() -> int:
    panels = []
    head_tiles = []
    checks = []
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
        want = 7 if doc_id == "beethoven5-litolff" else 3
        remaining = max(0, min(want, 10 - len(head_tiles)))
        selected = _select_10(doc_id, loaded)[:remaining] if remaining else []
        for row in selected:
            tile, chk = _head_tile(doc_id, row, rec, pages, templates_by_page,
                                   outer_tilt, sht._page_glyph_boxes(rec),
                                   score._accidental_boxes_by_page(rec))
            head_tiles.append(tile)
            checks.append(chk)
            print("  CHECK", chk)
        print()

    # 10 head tiles total across both docs, 2 columns.
    head_tiles = head_tiles[:10]
    cols = 2
    tile_w = max(t.shape[1] for t in head_tiles)
    tile_h = max(t.shape[0] for t in head_tiles)
    rows_n = (len(head_tiles) + cols - 1) // cols
    heads_sheet = np.full((rows_n * tile_h, cols * tile_w, 3), 255, dtype=np.uint8)
    for i, t in enumerate(head_tiles):
        r, c = divmod(i, cols)
        th, tw = t.shape[:2]
        heads_sheet[r * tile_h:r * tile_h + th, c * tile_w:c * tile_w + tw] = t

    panel_w = max(p.shape[1] for p in panels)
    panels_resized = []
    for p in panels:
        if p.shape[1] != panel_w:
            f = panel_w / p.shape[1]
            p = cv2.resize(p, (panel_w, int(p.shape[0] * f)))
        panels_resized.append(p)
    panels_stack = np.full((sum(p.shape[0] for p in panels_resized), panel_w, 3),
                           255, dtype=np.uint8)
    y = 0
    for p in panels_resized:
        panels_stack[y:y + p.shape[0], :p.shape[1]] = p
        y += p.shape[0]

    full_w = max(panels_stack.shape[1], heads_sheet.shape[1])

    def pad_to_width(img, w):
        if img.shape[1] == w:
            return img
        out = np.full((img.shape[0], w, 3), 255, dtype=np.uint8)
        out[:, :img.shape[1]] = img
        return out

    panels_stack = pad_to_width(panels_stack, full_w)
    heads_sheet = pad_to_width(heads_sheet, full_w)
    legend = ("RED thin box = detector box.  BLUE oval = best-matching geometry head "
              "(1.3 x 1.0 staff spaces, tilted at the measured angle) at its matched "
              "height.  ORANGE lines = staff/ledger lines read from the INK beside the "
              "head (local, never extrapolated).")
    lg_img = np.full((34, full_w, 3), 255, np.uint8)
    cv2.putText(lg_img, legend, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BLACK, 1, cv2.LINE_AA)
    sheet = np.vstack([lg_img, panels_stack, heads_sheet])

    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    import json
    (OUT_DIR / "template_review10_checks.json").write_text(json.dumps(checks, indent=1))
    print(f"wrote {OUT_PATH} ({len(head_tiles)} head tiles, "
          f"{sheet.shape[1]}x{sheet.shape[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
