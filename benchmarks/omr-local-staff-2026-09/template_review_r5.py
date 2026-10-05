#!/usr/bin/env python3
"""lane-ledger-template-fix, round 3 (2026-10-04): the control first.

Sean on the last sheet: the blue oval is "still not close" -- WRONG SHAPE OR
TILT, and IN THE WRONG PLACE. So before any far head:

  1. CONTROL: 6 clean, isolated, IN-STAFF heads per document (3 on a line,
     3 in a space) picked by SHAPE GATE ONLY (never by how well the matcher
     does on them). The template must sit on these first.
  2. SHAPE FROM THE PAGE (`shape_from_page.py`): width / height / tilt are the
     medians of per-head moment fits over clean isolated heads that pass an
     oval gate, taken from heads ON A LINE (see that file: heads in a space
     touch both neighbouring lines and read ~20 degrees too flat).
  3. PLACEMENT: the matcher searches +-0.4 sp horizontally as well as
     vertically (`dx_range_spaces`), and its HEAD term reads ink with stems
     and line remnants removed by an opening (`head_ink_mode="opening"`)
     instead of blanking whole stem columns, which ate the head's edge.
  4. SELF-CHECK on every tile: IoU of the oval with the head's ink blob (box
     +-0.3 sp, staff/ledger rows masked outside the oval) and the offset
     between the oval centre and the blob centroid. IoU < 0.7 or offset >
     0.15 sp is a MISS and is reported as one.

No scoring of any reader. Run:
    python3 benchmarks/omr-local-staff-2026-09/template_review_r3.py
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
import combined_scorer as cs  # noqa: E402
import shape_from_page as sfp  # noqa: E402
import template_review10 as tr  # noqa: E402  (selection + ladder helpers)
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers"
SHEET = OUT_DIR / "template_review_r5.jpg"
BLUE_ONLY = OUT_DIR / "template_review_r5_blueonly.jpg"
CHECKS = OUT_DIR / "template_review_r5_checks.json"
DX_RANGE_SPACES = 0.4
CUT_SPACES = 0.3
IOU_MIN, OFFSET_MAX_SP = 0.7, 0.15
HALF_W_SPACES, HALF_H_SPACES = 2.6, 3.2
TARGET_SPACING_PX = 90
COLS = 4
RED, ORANGE, BLUE, BLACK = (0, 0, 220), (30, 140, 255), (255, 80, 0), (0, 0, 0)


def doc_shape(doc_id, heads):
    """Per-doc oval from ON-LINE heads that pass the gate (fallback: all
    passing heads, said out loud)."""
    ok = [h for h in heads if h["kind"] == "filled" and h["isolated"] and h["meas"]["ok"]]
    on = [h for h in ok if h["pos"] % 2 == 0 and h["meas"]["angle_defined"]]
    use = on if len(on) >= 8 else [h for h in ok if h["meas"]["angle_defined"]]
    med = lambda k: float(np.median([h["meas"][k] for h in use]))
    shape = dict(width_sp=med("long_sp"), height_sp=med("short_sp"), tilt_deg=med("tilt"),
                 n=len(use), source="on-line heads" if use is on else "ALL passing heads")
    tilts = np.array([h["meas"]["tilt"] for h in use])
    shape["tilt_iqr"] = [round(float(x), 1) for x in np.percentile(tilts, [25, 75])]
    return shape


def print_agrees_with_position(h, max_off_sp=0.2):
    """A control must be CLEAN: on the print, the head's own ink centroid sits
    within `max_off_sp` of a staff line (on-line) or of the middle of a space,
    and which of the two agrees with our staff-position parity. Read off the
    local staff lines and the head blob -- never off the matcher. (Round 4: a
    'pos 7 in a space' control sat 0.32 sp off a line and 0.19 off the space
    middle; it is not a clean control for an on-line / in-space test.)"""
    b = h["meas"]["blob"]
    ms = sfp.moments_shape(b["outer"])
    cy = b["org"][1] + ms["cy"]
    ly = sorted(h["lines"])
    d_line = min(abs(cy - y) for y in ly)
    d_space = min(abs(cy - (a + c) / 2.0) for a, c in zip(ly[:-1], ly[1:]))
    sp = h["spacing"]
    on_line = d_line < d_space
    return (min(d_line, d_space) <= max_off_sp * sp) and (on_line == (h["pos"] % 2 == 0))


def pick_controls(heads, n_each=3):
    """3 on a line + 3 in a space, filled, isolated, gate-passing. Evenly
    spread over the sorted passing list -- never chosen by matcher output."""
    ok = sorted([h for h in heads if h["kind"] == "filled" and h["isolated"] and h["meas"]["ok"]
                 and print_agrees_with_position(h)],
                key=lambda h: (h["page"], h["subject"]))
    out = []
    for par in (0, 1):
        sub = [h for h in ok if h["pos"] % 2 == par]
        if not sub:
            continue
        idx = np.linspace(0, len(sub) - 1, n_each + 2)[1:-1].round().astype(int)
        out += [sub[i] for i in idx]
    return out


def oval_vs_ink(gray, box, spacing, thickness, line_ys, poly_page, cx_oval, cy_oval):
    """IoU of the oval with the head's ink blob, and centre offset (spaces).
    `ink` = Otsu; rows of the given staff/ledger lines are cleared OUTSIDE the
    oval; the blob is the ink inside box +-0.3 sp (components overlapping the
    oval). `iou_open` repeats it with stems/remnants opened away first."""
    x0, y0, x1, y1 = box
    m = int(round(CUT_SPACES * spacing))
    rx0, ry0, rx1, ry1 = int(x0) - m, int(y0) - m, int(x1) + m + 1, int(y1) + m + 1
    pad = int(round(1.5 * spacing))
    wx0, wy0 = rx0 - pad, ry0 - pad
    wx1, wy1 = rx1 + pad, ry1 + pad
    H, W = gray.shape
    wx0, wy0, wx1, wy1 = max(0, wx0), max(0, wy0), min(W, wx1), min(H, wy1)
    win = gray[wy0:wy1, wx0:wx1]
    ink = win <= ht._otsu_threshold(win)
    oval = np.zeros(ink.shape, np.uint8)
    cv2.fillPoly(oval, [np.array([[x - wx0, y - wy0] for x, y in poly_page], np.int32)], 1)
    oval = oval.astype(bool)
    half = int(round(thickness / 2.0)) + 1
    for ly in line_ys:
        r = int(round(ly - wy0))
        r0, r1 = max(0, r - half), min(ink.shape[0], r + half + 1)
        if r1 > r0:
            ink[r0:r1, :] &= oval[r0:r1, :]
    d = max(3, int(round(0.42 * spacing)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    ink_open = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    cut = np.zeros(ink.shape, bool)
    cut[max(0, ry0 - wy0):max(0, ry1 - wy0), max(0, rx0 - wx0):max(0, rx1 - wx0)] = True

    def one(mask):
        cand = mask & cut
        num, lab = cv2.connectedComponents(cand.astype(np.uint8))
        keep = np.zeros_like(cand)
        for i in range(1, num):
            comp = lab == i
            if (comp & oval).any():
                keep |= comp
        if not keep.any():
            return 0.0, None
        iou = float((keep & oval).sum() / (keep | oval).sum())
        ys, xs = np.nonzero(keep)
        off = float(np.hypot(xs.mean() + wx0 - cx_oval, ys.mean() + wy0 - cy_oval) / spacing)
        return iou, off
    iou, off = one(ink)
    iou_o, off_o = one(ink_open)
    return dict(iou=round(iou, 2), offset_sp=None if off is None else round(off, 2),
                iou_open=round(iou_o, 2), offset_open_sp=None if off_o is None else round(off_o, 2))


def render_tile(label, doc_id, row_like, rec, pages, templates, shape, boxes_by_page,
                nh_by_page, acc_by_page, show_overlays=True, zoom_override=None,
                caption=None, controls=False):
    """One tile + its numbers. `row_like` has subject/page/box/kind and
    (for far heads) staff_key/page_box."""
    box = row_like["box"]
    gray = pages.get(row_like["page"])
    lines = row_like["lines"]
    spacing = row_like["spacing"]
    subject = row_like["subject"]
    kind = row_like["kind"]
    nh = nh_by_page.get(row_like["page"], [])
    acc = acc_by_page.get(row_like["page"], [])
    others = [b for (s, b) in nh if s != subject] + [b for (_s, b) in acc]
    match = ht.match_head_template(gray, box, spacing, templates, exclude_boxes=others,
                                   kind=kind, dx_range_spaces=DX_RANGE_SPACES,
                                   head_ink_mode="opening", decide="staged",
                                   line_term="coverage")
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    mcx = match.get("center_x", cx) if match else cx
    mcy = match["center_y"] if match else cy
    var = match["best_variant"] if match and match.get("best_variant") else None

    rungs, side = [], None
    if not controls:
        rungs, _sp, side = cs._rungs_y_for_head(gray, lines, box, subject, nh,
                                                page_accidental_boxes=acc, four_causes_cd=True)
    line_ys = list(lines) + list(rungs)

    cx0 = int(round(cx - HALF_W_SPACES * spacing)); cx1 = int(round(cx + HALF_W_SPACES * spacing))
    cy0 = int(round(cy - HALF_H_SPACES * spacing)); cy1 = int(round(cy + HALF_H_SPACES * spacing))
    H, W = gray.shape
    g = np.full((cy1 - cy0, cx1 - cx0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(0, cx0), max(0, cy0), min(W, cx1), min(H, cy1)
    g[sy0 - cy0:sy1 - cy0, sx0 - cx0:sx1 - cx0] = gray[sy0:sy1, sx0:sx1]
    zoom = zoom_override or max(3, int(round(TARGET_SPACING_PX / spacing)))
    img = cv2.cvtColor(cv2.resize(g, (g.shape[1] * zoom, g.shape[0] * zoom),
                                  interpolation=cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)

    def T(px, py):
        return (int(round((px - cx0 + 0.5) * zoom)), int(round((py - cy0 + 0.5) * zoom)))

    if show_overlays:
        for y in lines:
            if cy0 + 1 <= y <= cy1 - 2:
                cv2.line(img, T(cx0, y), T(cx1, y), ORANGE, 1)
        for y in rungs:
            if cy0 + 1 <= y <= cy1 - 2:
                cv2.line(img, T(x0 - 0.6 * spacing, y), T(x1 + 0.6 * spacing, y), ORANGE, 1)
    def outline(px, py, scale):
        if shape.get("mask") is not None:
            return ht.mask_outline_poly(shape["mask"], px, py, scale)
        return ht.geometry_outline_poly(px, py, scale, shape["tilt_deg"],
                                        shape["width_sp"], shape["height_sp"])
    pts = outline((mcx - cx0 + 0.5) * zoom, (mcy - cy0 + 0.5) * zoom, spacing * zoom).astype(np.int32)
    cv2.polylines(img, [pts], True, BLUE, 2, cv2.LINE_AA)
    if show_overlays:
        cv2.rectangle(img, T(x0, y0), T(x1, y1), RED, 1)

    poly_page = outline(mcx, mcy, spacing)
    thick = row_like.get("thickness", 4.0)
    chk = oval_vs_ink(gray, box, spacing, thick, line_ys, poly_page, mcx, mcy)
    chk.update(label=label, doc=doc_id, subject=subject, kind=kind, variant=var,
               margin=None if not match else round(float(match["margin"]), 3),
               score_on=None if not match or match.get("score_on") is None else round(float(match["score_on"]), 3),
               score_space=None if not match or match.get("score_space") is None else round(float(match["score_space"]), 3),
               dx_sp=round((mcx - cx) / spacing, 2), dy_sp=round((mcy - cy) / spacing, 2),
               dx_px=round(mcx - cx, 1), dy_px=round(mcy - cy, 1), spacing=round(spacing, 1))
    chk["MISS"] = bool((chk["iou"] < IOU_MIN) or (chk["offset_sp"] is None)
                       or (chk["offset_sp"] > OFFSET_MAX_SP))

    if caption is None:
        return img, chk
    lines_text = caption(chk, match, row_like, rungs, side)
    font, fs = cv2.FONT_HERSHEY_SIMPLEX, 0.5
    tw = max(cv2.getTextSize(t, font, fs, 1)[0][0] for t in lines_text)
    cw = max(img.shape[1], tw + 12)
    lh = 22 * len(lines_text) + 8
    out = np.full((img.shape[0] + lh, cw, 3), 255, np.uint8)
    out[:img.shape[0], :img.shape[1]] = img
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (6, img.shape[0] + 20 + i * 22), font, fs, BLACK, 1, cv2.LINE_AA)
    return out, chk


def grid(tiles, cols=COLS):
    tw = max(t.shape[1] for t in tiles); th = max(t.shape[0] for t in tiles)
    n = (len(tiles) + cols - 1) // cols
    g = np.full((n * th, cols * tw, 3), 255, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        g[r * th:r * th + t.shape[0], c * tw:c * tw + t.shape[1]] = t
    return g


def banner(text, w, h=34):
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.putText(img, text, (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.62, BLACK, 1, cv2.LINE_AA)
    return img



def make_templates(shape, thick, med_sp):
    tilt = shape["tilt_deg"]
    kw = dict(width_spaces={"filled": shape["width_sp"], "hollow": shape["width_sp"]},
              height_spaces={"filled": shape["height_sp"], "hollow": shape["height_sp"]})
    if shape.get("mask") is not None:
        kw["shape_masks"] = {"filled": shape["mask"], "hollow": shape["mask"]}
    tm = ht.build_geometry_templates({"filled": tilt, "hollow": tilt}, {},
                                     thick * ht.CANONICAL_PX_PER_SPACE / med_sp, **kw)
    return sht.templates_for_page({"pooled": tm}, 0)


def _centred(mask):
    ys, xs = np.nonzero(mask)
    dx = int(round(ht.CANONICAL_W / 2.0 - xs.mean()))
    dy = int(round(ht.CANONICAL_H / 2.0 - ys.mean()))
    return np.roll(np.roll(mask, dy, axis=0), dx, axis=1)


def candidate_shapes(heads, pages, shape_a):
    """A: the round-3 oval. B: an oval (long/short/tilt from the clean LEMON-gated
    on-line heads) with its lower edge cut flat at a fraction fitted to the mean
    shape. C: the mean shape of those heads, aligned on measured centroids."""
    out = {"A_oval": dict(shape_a)}
    lemon = [h for h in heads if h["kind"] == "filled" and h["isolated"] and h["meas"].get("ok_lemon")
             and h["pos"] % 2 == 0 and h["meas"].get("angle_defined")]
    if len(lemon) < 8:
        return out
    med = lambda k: float(np.median([h["meas"][k] for h in lemon]))
    prob, n = sfp.mean_shape(heads, pages)
    mean_mask = prob >= 0.5
    long_sp, short_sp, tilt = med("long_sp"), med("short_sp"), med("tilt")
    best_f, best_iou = 1.0, -1.0
    mm = _centred(mean_mask)
    for f in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7):
        e = _centred(ht.head_shape_mask(long_sp, short_sp, tilt, f))
        iou = float((e & mm).sum() / (e | mm).sum())
        if iou > best_iou:
            best_f, best_iou = f, iou
    flat = _centred(ht.head_shape_mask(long_sp, short_sp, tilt, best_f))
    out["B_flat_oval"] = dict(width_sp=long_sp, height_sp=short_sp, tilt_deg=tilt, mask=flat,
                              flat_bottom_fraction=best_f, n=len(lemon),
                              iou_with_mean_shape=round(best_iou, 3))
    out["C_mean_shape"] = dict(width_sp=long_sp, height_sp=short_sp, tilt_deg=tilt, mask=mm,
                               n=n, mean_area_sp2=round(float(mm.sum()) / ht.CANONICAL_PX_PER_SPACE ** 2, 3))
    return out


def main() -> int:
    ctrl_tiles, far_tiles, checks, shapes, shape_report = [], [], [], {}, {}
    spare = {}   # tiles for the blue-only sheet
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        heads = sfp.in_staff_heads(doc_id, loaded, pages)
        sfp.annotate_heads(doc_id, loaded, pages, heads)
        shape_a = doc_shape(doc_id, heads)
        thick = float(np.median([h["thickness"] for h in heads]))
        med_sp = float(np.median([h["spacing"] for h in heads]))
        boxes_by_page = sht._page_glyph_boxes(rec)
        nh = score._notehead_boxes_by_page(rec)
        acc = score._accidental_boxes_by_page(rec)
        cands = candidate_shapes(heads, pages, shape_a)
        ctrl_heads = pick_controls(heads)
        report = {}
        for name, shp in cands.items():
            tpl_c = make_templates(shp, thick, med_sp)
            res = []
            for h in ctrl_heads:
                _t, c = render_tile("control", doc_id, dict(h, thickness=h["thickness"]), rec, pages, tpl_c,
                                    shp, boxes_by_page, nh, acc, controls=True)
                res.append(c)
            report[name] = dict(mean_iou=round(float(np.mean([c["iou"] for c in res])), 3),
                                mean_offset_sp=round(float(np.mean([9 if c["offset_sp"] is None else c["offset_sp"] for c in res])), 3),
                                n_miss=sum(c["MISS"] for c in res),
                                variant_agree=sum((h["pos"] % 2 == 0) == (c["variant"] == "on_line")
                                                  for h, c in zip(ctrl_heads, res)),
                                per_head_iou=[c["iou"] for c in res])
            print(f"  candidate {name}: {report[name]}")
        best = max(report, key=lambda k: (report[k]["mean_iou"], k == "A_oval"))
        shape = cands[best]
        shape_report[doc_id] = dict(chosen=best, candidates=report,
                                    params={k: {kk: vv for kk, vv in v.items() if kk != "mask"}
                                            for k, v in cands.items()})
        shapes[doc_id] = shape_report[doc_id]
        print("  CHOSEN", best)
        tpl = make_templates(shape, thick, med_sp)
        # ---- controls
        for h in ctrl_heads:
            rl = dict(h, thickness=h["thickness"])
            def cap(chk, match, r, rungs, side, h=h):
                par = "on a line" if h["pos"] % 2 == 0 else "in a space"
                return [f"CONTROL {doc_id.split('-')[0]} {h['subject']} ({par})",
                        f"oval moved dx {chk['dx_sp']:+.2f} dy {chk['dy_sp']:+.2f} sp   variant {chk['variant']}",
                        f"IoU {chk['iou']:.2f} (stems opened away {chk['iou_open']:.2f})  offset {chk['offset_sp']} sp"
                        + ("   MISS" if chk["MISS"] else "")]
            tile, chk = render_tile("control", doc_id, rl, rec, pages, tpl, shape, boxes_by_page,
                                    nh, acc, caption=cap, controls=True)
            chk["position"] = h["pos"]
            ctrl_tiles.append(tile); checks.append(chk)
            spare.setdefault(("control", doc_id), []).append(h)

        # ---- far heads (same selection rule as before)
        rows = score._far_head_rows(doc_id, loaded)
        rows_by_subject = {r["subject"]: r for r in rows if r.get("page_box")}
        scored = set()
        for r in rows:
            if r["subject"] == "glyph/1/0/10/14/1" or not r["truth_pitches"] or not r.get("page_box"):
                continue
            cv = rec.value(Q.CLEF, r["staff_key"])
            if cv is not None and score.truth_positions(r["truth_pitches"], str(cv)):
                scored.add(r["subject"])
        want = 7 if doc_id == "beethoven5-litolff" else 3
        for row in tr._select(doc_id, rows_by_subject, scored, boxes_by_page, want):
            gl = [float(y) for y in rec.obs(Q.STAFF_LINES, row["staff_key"])[-1]["value"]]
            gray = pages.get(row["page"])
            lines = score.frame_lines_for_head(gray, gl, row["page_box"])
            sp = (max(lines) - min(lines)) / 4.0
            entry = {s: c for (s, c, b) in boxes_by_page.get(row["page"], [])}
            cls = entry.get(row["subject"], "noteheadBlackOnLine")
            rl = dict(subject=row["subject"], page=row["page"], box=tuple(row["page_box"]),
                      kind="filled" if "Black" in cls else "hollow", lines=lines, spacing=sp,
                      thickness=thick)
            cvv = rec.value(Q.CLEF, row["staff_key"])
            ref = sorted(set(score.truth_positions(row["truth_pitches"], str(cvv))))
            r8, _ = score.reader_absolute_position(gray, lines, rl["box"], row["subject"],
                                                   nh.get(row["page"], []),
                                                   page_accidental_boxes=acc.get(row["page"], []),
                                                   four_causes_cd=True)
            def cap(chk, match, r, rungs, side, row=row, ref=ref, r8=r8, lines=lines, sp=sp):
                ladder = tr._ladder(lines, rungs, side)
                step, flag = tr._template_step(chk["variant"], r["box"][1] * 0 + (match["center_y"] if match else 0),
                                               ladder, sp, side)
                where = {"on_line": "on a line", "in_space": "in a space"}.get(chk["variant"], "no answer")
                und = " (UNDECIDED)" if (match is None or match.get("undecided")) else ""
                return [f"FAR {doc_id.split('-')[0]} {row['subject']} ({r['kind']})",
                        f"template: {where}, step {step}{und}" + (f" [{flag}]" if flag else "")
                        + f"   round 8: {'abstains' if r8 is None else 'step ' + str(r8)}"
                        f"   ref: {','.join(map(str, ref)) or 'none'}",
                        f"oval moved dx {chk['dx_sp']:+.2f} dy {chk['dy_sp']:+.2f} sp   "
                        f"IoU {chk['iou']:.2f} (stems opened {chk['iou_open']:.2f})  offset {chk['offset_sp']} sp"
                        + ("   MISS" if chk["MISS"] else "")]
            tile, chk = render_tile("far", doc_id, rl, rec, pages, tpl, shape, boxes_by_page,
                                    nh, acc, caption=cap)
            chk["reference"] = ref
            chk["round8"] = r8
            far_tiles.append(tile); checks.append(chk)
            spare.setdefault(("far", doc_id), []).append((rl, rec, pages, tpl, shape, boxes_by_page, nh, acc))
        # keep per-doc context for the blue-only sheet
        spare[("ctx", doc_id)] = (rec, pages, tpl, shape, boxes_by_page, nh, acc)
        print()

    # ---- blue-only (2 control, 2 far), x6, NO red / orange
    blue = []
    for doc_id, n_ctrl, n_far in (("beethoven5-litolff", 1, 1), ("brahms1-breitkopf", 1, 1)):
        rec, pages, tpl, shape, bbp, nh, acc = spare[("ctx", doc_id)]
        heads = spare[("control", doc_id)]
        h = heads[0] if n_ctrl == 1 else heads[0]
        t, _c = render_tile("blue", doc_id, h, rec, pages, tpl, shape, bbp, nh, acc,
                            show_overlays=False, zoom_override=6,
                            caption=lambda c, m, r, ru, s, h=h, d=doc_id:
                            [f"CONTROL {d.split('-')[0]} {h['subject']}"], controls=True)
        blue.append(t)
        far = spare[("far", doc_id)][0]
        rl, rec, pages, tpl, shape, bbp, nh, acc = far
        t, _c = render_tile("blue", doc_id, rl, rec, pages, tpl, shape, bbp, nh, acc,
                            show_overlays=False, zoom_override=6,
                            caption=lambda c, m, r, ru, s, rl=rl, d=doc_id:
                            [f"FAR {d.split('-')[0]} {rl['subject']}"])
        blue.append(t)

    legend = ("RED box = detector box.   BLUE oval = best-matching head (width/height/tilt measured from this "
              "page's clean heads on a line) at the position the matcher chose, searching +-0.4 sp sideways "
              "as well as up/down.   ORANGE = staff lines at the head's x + ledgers round 8 measured.   "
              "Real print underneath.")
    cg, fg = grid(ctrl_tiles), grid(far_tiles)
    W_ = max(cg.shape[1], fg.shape[1])
    def pad(a):
        o = np.full((a.shape[0], W_, 3), 255, np.uint8); o[:, :a.shape[1]] = a; return o
    sheet = np.vstack([banner(legend, W_), banner("CONTROL: 12 clean isolated IN-STAFF heads "
                       "(6 per document: 3 on a line, 3 in a space) -- the oval must sit on THESE first", W_),
                       pad(cg), banner("FAR HEADS: the same 10 as the last sheet", W_), pad(fg)])
    if sheet.shape[1] > 2600:
        f = 2600 / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)), interpolation=cv2.INTER_AREA)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(SHEET), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    bg = grid(blue, 2)
    cv2.imwrite(str(BLUE_ONLY), np.vstack([banner("BLUE only (no box, no lines), x6: judge the shape alone. "
                                                  "Top-left/bottom-left = control; right = far head.", bg.shape[1]), bg]),
                [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    CHECKS.write_text(json.dumps(dict(shapes=shapes, tiles=checks), indent=1, default=str))

    print("\nlabel   doc        subject            kind   var       dx_sp  dy_sp   IoU  IoUopen  off_sp  MISS")
    for c in checks:
        print(f"{c['label']:<7} {c['doc'].split('-')[0]:<10} {c['subject']:<18} {c['kind']:<6} {str(c['variant']):<9}"
              f" {c['dx_sp']:+.2f}  {c['dy_sp']:+.2f}  {c['iou']:.2f}  {c['iou_open']:.2f}    {c['offset_sp']}  {'MISS' if c['MISS'] else ''}")
    print("wrote", SHEET, BLUE_ONLY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
