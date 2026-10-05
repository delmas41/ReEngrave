#!/usr/bin/env python3
"""lane-ledger-far-edge-crops (2026-10-04) -- MEASURE + CROPS ONLY.

Sean, asked "Outside the staff, if a ledger touches the far side of a head and
no other note sits farther out, is that head ON that ledger?": *"Depends, show
me crops."*  This script (1) finds every far head in both truth sets with a
thin flat rung at/near its FAR edge (the side away from the staff), (2) splits
them into (a) reference ON that line, (b) reference in the space nearer the
staff, (c) a chord partner sits farther out, and (3) cuts ONE contact sheet
with only a number on each tile (the key file maps number -> subject, group,
reference, our answer).  NO reader change; `tools/` untouched.  The reader is
only CALLED (as `score_edge_fix.py` calls it).

    python3 benchmarks/omr-local-staff-2026-09/far_edge_crops.py \
        [--json out.json] [--sheet out/print/ledgers/far_edge]

GEOMETRIC TEST (all in staff spaces `sp`, from the head's box, + = farther from
the staff):  rn / rf / rm = the rung's signed distance from the box's near edge /
far edge / middle (`edge_census._rel_numbers`).  A FAR-EDGE RUNG is a rung the
bare ink walk offers (`measure_ledger_rungs` on the head's column with NO
other-head/accidental masking -- `edge_census.stage0_candidates`, which already
requires a thin flat run) that `edge_census._is_edge_related` calls 'far':
more than 0.25 sp from the box middle (else 'mid', a through candidate) and
within [-0.45, +0.35] sp of the box's far edge.  Those are the census's own
numbers; nothing here is tuned.  `rows[i]['far_rung']` carries the numbers.

Controls (printed first): the fix-1 arm (`near_edge_ledgers` +
`restore_masked_near_edge`) must tally Litolff 29/13/2, Brahms 11/0/0.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import edge_census as ec  # noqa: E402
import score_edge_fix as sef  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

INK = 140                      # gray < INK is ink (pages are near-bitonal)
PARTNER_DX_SP = 1.7            # chord partner: centre within this many sp in x
PARTNER_DY_MIN_SP = 0.5        # ... and at least this much farther out
PARTNER_DY_MAX_SP = 3.0


def _ink_frac(gray, y, xa, xb, tol=1):
    """Fraction of columns xa..xb where any row y-tol..y+tol is ink."""
    h, w = gray.shape
    xa, xb = max(0, int(round(xa))), min(w, int(round(xb)))
    ya, yb = max(0, int(round(y)) - tol), min(h, int(round(y)) + tol + 1)
    if xb <= xa or yb <= ya:
        return 0.0
    band = gray[ya:yb, xa:xb] < INK
    return float(band.any(axis=0).mean())


def raw_run(gray, y, box, sp):
    """Length (sp) of the raw ink (+-1 px of row y) running outward from each
    side of the box, starting 3 px inside its edge, capped at 1.6 sp."""
    x0, _, x1, _ = box
    H, W = gray.shape
    yi = int(round(y))
    out = {}
    for sgn, nm in ((-1, "left"), (1, "right")):
        xi = int(round(x1)) - 3 if sgn > 0 else int(round(x0)) + 3
        n, lim = 0, int(1.6 * sp) + 3
        while n < lim:
            x = xi + sgn * n
            if not (0 <= x < W) or not (gray[max(0, yi - 1):yi + 2, x] < INK).any():
                break
            n += 1
        xend = xi + sgn * n
        out[nm] = (xend, (xend - x1) / sp if sgn > 0 else (x0 - xend) / sp)
    return out


def pixel_numbers(gray, y, box, sp):
    """Ink fraction on the arrowed row vs 0.5 sp off it (+-1 px tolerance):
    SPAN = head width +-0.5 sp (the requested test); STUB = the better of the
    two 0.1..1.1 sp zones beside the box (the census's sheet test)."""
    x0, _, x1, _ = box
    span_on = _ink_frac(gray, y, x0 - 0.5 * sp, x1 + 0.5 * sp)
    span_off = max(_ink_frac(gray, y - 0.5 * sp, x0 - 0.5 * sp, x1 + 0.5 * sp),
                   _ink_frac(gray, y + 0.5 * sp, x0 - 0.5 * sp, x1 + 0.5 * sp))
    out = {}
    for side, (a, b) in dict(left=(x0 - 1.1 * sp, x0 - 0.1 * sp),
                             right=(x1 + 0.1 * sp, x1 + 1.1 * sp)).items():
        on = _ink_frac(gray, y, a, b)
        off = max(_ink_frac(gray, y - 0.5 * sp, a, b), _ink_frac(gray, y + 0.5 * sp, a, b))
        out[side] = (on, off)
    best = max(out, key=lambda s: out[s][0] - out[s][1])
    return dict(span_on=span_on, span_off=span_off, stub_side=best,
                stub_on=out[best][0], stub_off=out[best][1],
                stub_left=out["left"], stub_right=out["right"])


def analyse(h, ans_pos, ans_reason):
    x0, y0, x1, y1 = h["box"]
    ys = sorted(float(v) for v in h["lines"])
    sp = (ys[-1] - ys[0]) / 4.0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    side, s0 = ec.stage0_candidates(h)
    sign = -1.0 if side == "above" else 1.0
    edge = ys[0] if sign < 0 else ys[-1]
    # ladder (nearest the staff first); rungs closer than 0.5 sp are one
    # ledger (a thick ledger's two edges).
    lad: List[float] = []
    for y in sorted(s0, key=lambda v: sign * (v - edge)):
        if lad and abs(y - lad[-1]) < 0.5 * sp:
            continue
        lad.append(y)
    truth = h["truth"]
    row = dict(subject=h["subject"], doc=h["doc"], page=h["page"], side=side,
               sp=sp, box=list(h["box"]), truth=truth, answer=ans_pos,
               reason=ans_reason, ladder_sp=[round(sign * (y - edge) / sp, 2) for y in lad])
    far = None
    # keep the OUTERMOST qualifying rung. tier "census": the census's own 'far'
    # relation (_is_edge_related). tier "far_half": a rung more than the
    # shipped middle-row probe tolerance (0.15 sp) past the box middle and no
    # more than 0.35 sp beyond the far edge -- the census band PLUS the rungs
    # on the head's far half that the census calls 'mid' (|rm| <= 0.25).
    for n, y in enumerate(lad, start=1):
        rn, rf, rm = ec._rel_numbers(y, h["box"], sp, sign)
        tier = None
        if ec._is_edge_related(y, h["box"], sp, sign) == "far":
            tier = "census"
        elif rm > 0.15 and rf <= 0.35:
            tier = "far_half"
        if tier:
            far = dict(y=y, ordinal=n, rn=round(rn, 2), rf=round(rf, 2), rm=round(rm, 2),
                       tier=tier, line_pos=int(sign * 2 * n + (0 if sign < 0 else 8)))
    row["far_rung"] = far
    # chord partner farther out (any detector notehead box)
    partners = []
    for sid, b in h["boxes"]:
        if sid == h["subject"]:
            continue
        bx, by = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        dy = sign * (by - cy) / sp
        if abs(bx - cx) <= PARTNER_DX_SP * sp and PARTNER_DY_MIN_SP <= dy <= PARTNER_DY_MAX_SP:
            partners.append(dict(subject=sid, dx_sp=round((bx - cx) / sp, 2), dy_sp=round(dy, 2)))
    row["partner_farther"] = partners
    if far is not None:
        lp = far["line_pos"]
        t = truth[0] if truth else None
        row["on_it_answer"] = lp
        row["ref_vs_line"] = (None if t is None else
                              "on" if t == lp else
                              "space_nearer" if t == lp - int(sign) else "other")
        row["pixels"] = pixel_numbers(h["gray"], far["y"], h["box"], sp)
        px = row["pixels"]
        # the READER'S OWN jut test (read-only call): a thin, flat, connected
        # line at the rung's row juts out of the box by >= 0.15 sp, other
        # noteheads' and accidentals' ink blanked first.
        others = [b for (sid, b) in h["boxes"] if sid != h["subject"]] + [b for (_s, b) in h["acc"]]
        jut = lg.thin_flat_jut_evidence(h["gray"], far["y"], tuple(h["box"]), sp, exclude_boxes=others)
        row["jut"] = dict(ok=bool(jut["ok"]), why=jut["why"],
                          left_sp=round(float(jut.get("left_jut", 0)) / sp, 2),
                          right_sp=round(float(jut.get("right_jut", 0)) / sp, 2))
        rr = raw_run(h["gray"], far["y"], h["box"], sp)
        row["raw_run_sp"] = {k: round(v[1], 2) for k, v in rr.items()}
        row["jut_ok"] = bool(jut["ok"])
        row["backed_by_ink"] = bool(jut["ok"]) or max(v[1] for v in rr.values()) >= 0.1
        if partners:
            grp = "c"
        elif not row["backed_by_ink"]:
            grp = "x"      # no ledger ink beyond the head: the head's own outline / a slur
        elif row["ref_vs_line"] == "on":
            grp = "a"
        elif row["ref_vs_line"] == "space_nearer":
            grp = "b"
        else:
            grp = "o"
        row["group"] = grp
    return row


# ------------------------------------------------------------------ sheet
PX_PER_SP = 110.0          # display scale: every tile shows 110 px per staff space
WIN_W_SP, WIN_H_SP = 7.0, 6.0
RED, BLUE = (200, 0, 0), (0, 90, 220)


def _frame_control(h, sp):
    """Staff outer line (on the head's side) vs 0.5 sp beyond it, over the
    tile's x range: the frame is right if the line row is mostly ink and
    the row outside it is not (can fail: a shifted frame reads off/on)."""
    x0, _, x1, _ = h["box"]
    cx = (x0 + x1) / 2.0
    ys = sorted(float(v) for v in h["lines"])
    hh = (h["box"][1] + h["box"][3]) / 2.0
    sign = -1.0 if hh < ys[0] else 1.0
    yl = ys[0] if sign < 0 else ys[-1]
    a, b = cx - WIN_W_SP / 2 * sp, cx + WIN_W_SP / 2 * sp
    return dict(on=_ink_frac(h["gray"], yl, a, b), off=_ink_frac(h["gray"], yl + sign * 0.5 * sp, a, b))


def make_tile(h, row, number):
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    sp = row["sp"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    ax0, ay0 = int(round(cx - WIN_W_SP / 2 * sp)), int(round(cy - WIN_H_SP / 2 * sp))
    ax1, ay1 = int(round(cx + WIN_W_SP / 2 * sp)), int(round(cy + WIN_H_SP / 2 * sp))
    H, W = gray.shape
    crop = np.full((ay1 - ay0, ax1 - ax0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(ax0, 0), max(ay0, 0), min(ax1, W), min(ay1, H)
    crop[sy0 - ay0:sy1 - ay0, sx0 - ax0:sx1 - ax0] = gray[sy0:sy1, sx0:sx1]
    tw, th = int(round(WIN_W_SP * PX_PER_SP)), int(round(WIN_H_SP * PX_PER_SP))
    big = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_CUBIC)
    img = Image.fromarray(big).convert("RGB")
    d = ImageDraw.Draw(img)

    def P(x, y):
        return ((x - ax0) * tw / (ax1 - ax0), (y - ay0) * th / (ay1 - ay0))

    # corner brackets just OUTSIDE the box corners (the head's ink stays visible)
    L, g, wd = 0.28 * PX_PER_SP, 5, 3
    bx0, by0 = P(x0, y0)
    bx1, by1 = P(x1, y1)
    for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        px, py = px - dx * g, py - dy * g
        d.line([(px, py), (px + dx * L, py)], fill=RED, width=wd)
        d.line([(px, py), (px, py + dy * L)], fill=RED, width=wd)
    # arrow: HORIZONTAL, at the arrowed row, pointing at the end of the ink that
    # runs along that row beside the head (the ledger's stub), from the
    # open side. Raw ink (+-1 px), scanned outward from the box edge.
    far, px_ = row["far_rung"], row["pixels"]
    yr = far["y"]

    rr = raw_run(gray, yr, h["box"], sp)
    cand = [(nm, (-1 if nm == "left" else 1), v[0], v[1]) for nm, v in rr.items()]
    # prefer a side whose ink ends in white within 1.0 sp (not bridged into a neighbour)
    good = [c for c in cand if 0.1 <= c[3] <= 1.0] or cand
    nm, sgn, xend, ext = max(good, key=lambda c: c[3])
    tipx, tipy = P(xend + sgn * 0.12 * sp, yr)
    L2 = 0.9 * PX_PER_SP
    tailx, taily = tipx + sgn * L2, tipy
    d.line([(tailx, taily), (tipx, tipy)], fill=BLUE, width=3)
    for dy in (-10, 10):
        d.line([(tipx, tipy), (tipx + sgn * 18, tipy + dy)], fill=BLUE, width=3)
    sx = xend + sgn * 0.12 * sp
    # number, top-left, on a white chip
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
    d.rectangle([0, 0, 78, 62], fill=(255, 255, 255))
    d.text((8, 4), str(number), fill=(0, 0, 0), font=font)
    d.rectangle([0, 0, tw - 1, th - 1], outline=(120, 120, 120), width=2)
    return img, dict(tip_page=(float(sx), float(yr)), arrow_side=nm, ink_run_sp=round(float(ext), 2),
                     arrowed_row_page=float(far["y"]), crop_page=[ax0, ay0, ax1, ay1], scale=tw / (ax1 - ax0))


def make_sheet(rows, heads, outdir: Path):
    from PIL import Image, ImageDraw, ImageFont
    cand = [r for r in rows if r["far_rung"] and r.get("group") in ("a", "b", "c")]
    # the arrow must point at ink: span ink on the row > 0.5 sp off it
    pick = [r for r in cand if r["pixels"]["span_on"] > r["pixels"]["span_off"]]
    excluded = [dict(subject=r["subject"], group=r["group"], reason="span ink on <= off",
                     pixels=r["pixels"]) for r in cand if r not in pick]
    pick.sort(key=lambda r: ("bac".index(r["group"]), r["subject"]))   # all (b) first
    pick = pick[:16]
    random.Random(7).shuffle(pick)
    by = {(h["doc"], h["subject"]): h for d in heads for h in heads[d]}
    tiles, key = [], []
    tw, th = int(WIN_W_SP * PX_PER_SP), int(WIN_H_SP * PX_PER_SP)
    for i, r in enumerate(pick, start=1):
        h = by[(r["doc"], r["subject"])]
        img, geo = make_tile(h, r, i)
        tiles.append(img)
        fc = _frame_control(h, r["sp"])
        p = r["pixels"]
        key.append(dict(
            tile=i, subject=r["subject"], doc=r["doc"], page=r["page"], group=r["group"],
            group_meaning={"a": "reference says ON the arrowed line",
                           "b": "reference says NOT on it (space nearer the staff)",
                           "c": "a chord partner (detector notehead) sits farther out"}[r["group"]],
            reference_pos=r["truth"], round8_fix1_answer=r["answer"], round8_fix1_verdict=r["verdict"],
            answer_if_on_arrowed_line=r["on_it_answer"], far_rung=r["far_rung"],
            partner_farther=r["partner_farther"], jut=r["jut"], raw_run_sp=r["raw_run_sp"], ref_vs_line=r["ref_vs_line"], pixels=p, frame_control=fc,
            arrow=geo, display_px_per_sp=PX_PER_SP, source_scale=geo["scale"],
            pixel_ok=bool(p["span_on"] > p["span_off"] and p["stub_on"] > p["stub_off"]
                          and fc["on"] > fc["off"])))
    ncol = 2
    nrow = (len(tiles) + ncol - 1) // ncol
    pad, top = 24, 120
    W = ncol * tw + (ncol + 1) * pad
    Hh = top + nrow * th + (nrow + 1) * pad
    sheet = Image.new("RGB", (W, Hh), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
    d.text((pad, 24), "Red corner brackets = the note.  Blue arrow = the line touching its far side.", fill=(0, 0, 0), font=font)
    d.text((pad, 70), "For each tile: is the note ON the arrowed line?", fill=(0, 0, 0), font=font)
    for i, t in enumerate(tiles):
        rr, cc = divmod(i, ncol)
        sheet.paste(t, (pad + cc * (tw + pad), top + pad + rr * (th + pad)))
    outdir.mkdir(parents=True, exist_ok=True)
    sheet.save(outdir / "far_edge_sheet.png")
    (outdir / "far_edge_key.json").write_text(json.dumps(
        dict(tiles=key, excluded_after_pixel_check=excluded,
             not_on_sheet=[dict(subject=r["subject"], group=r.get("group"), truth=r["truth"],
                                far_rung=r["far_rung"], jut=r.get("jut"))
                           for r in rows if r["far_rung"] and r.get("group") in ("o", "x")]),
        indent=1, default=str))
    print(f"\nsheet: {outdir/'far_edge_sheet.png'} ({len(tiles)} tiles)")
    for k in key:
        p = k["pixels"]
        print(f"  tile {k['tile']:2} {k['subject']:18} grp {k['group']} ref {k['reference_pos']} ours {k['round8_fix1_answer']} "
              f"on-it {k['answer_if_on_arrowed_line']}  span {p['span_on']:.2f}/{p['span_off']:.2f} "
              f"stub {p['stub_on']:.2f}/{p['stub_off']:.2f}({p['stub_side']}) frame {k['frame_control']['on']:.2f}/{k['frame_control']['off']:.2f} "
              f"ok={k['pixel_ok']}")


def main() -> int:
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    res = sef.run(heads)
    for d in ts.DOCS:   # CONTROL
        for arm in ("default", "part12"):
            vs = [r["v"] for r in res[arm][d].values()]
            print(f"control {arm:8} {d:20} {ec.tally(vs)} n={len(vs)}")
    rows: List[Dict[str, Any]] = []
    for d in ts.DOCS:
        for h in heads[d]:
            r = res["part12"][d][h["subject"]]
            rows.append(analyse(h, r["pos"], r["reason"]))
            rows[-1]["verdict"] = r["v"]
    far = [r for r in rows if r["far_rung"]]
    print(f"\nfar heads: {len(rows)}; with a far-edge rung: {len(far)}")
    for d in ts.DOCS:
        sub = [r for r in far if r["doc"] == d]
        cnt = {g: sum(1 for r in sub if r["group"] == g) for g in "abcox"}
        print(f"  {d}: heads with far-edge rung {len(sub)}  a={cnt['a']} b={cnt['b']} c={cnt['c']} other={cnt['o']} no_ink={cnt['x']}  (census-band {sum(1 for r in sub if r['far_rung']['tier']=='census')})")
    print(f"\n{'head':18} {'grp':3} {'ref':>5} {'ours':>5} {'onit':>5} {'ord':>3} "
          f"{'rn':>5} {'rf':>5} {'rm':>5} partner  span on/off  stub on/off")
    for r in sorted(far, key=lambda r: (r["doc"], r["group"], r["subject"])):
        f, p = r["far_rung"], r["pixels"]
        print(f"{r['subject']:18} {r['group']:1}{r['far_rung']['tier'][0]:2} {str(r['truth']):>5} {str(r['answer']):>5} "
              f"{r['on_it_answer']:>5} {f['ordinal']:>3} {f['rn']:>5} {f['rf']:>5} {f['rm']:>5} "
              f"{len(r['partner_farther'])}  {p['span_on']:.2f}/{p['span_off']:.2f}  "
              f"{p['stub_on']:.2f}/{p['stub_off']:.2f}({p['stub_side'][0]})  {r['verdict']}")
    nofar = [r for r in rows if not r["far_rung"]]
    print(f"\nheads WITHOUT a far-edge rung ({len(nofar)}) by verdict:",
          {v: sum(1 for r in nofar if r["verdict"] == v) for v in ("right", "wrong", "abstain")})
    nine = ["3/0/7/2/4", "3/0/7/3/1", "3/0/7/3/2", "3/0/7/3/4", "3/0/7/4/3",
            "3/0/7/6/1", "3/0/7/7/0", "3/0/8/6/10", "3/1/0/6/0"]
    print("\nthe 9 remaining Litolff misses: where the walk's rungs sit (rn, rf, rm in sp; ref/ours)")
    for r in rows:
        if r["subject"].replace("glyph/", "") in nine:
            hh = next(h for h in heads[r["doc"]] if h["subject"] == r["subject"])
            sp = r["sp"]
            sign = -1.0 if r["side"] == "above" else 1.0
            _, s0 = ec.stage0_candidates(hh)
            nums = [tuple(round(v, 2) for v in ec._rel_numbers(y, hh["box"], sp, sign)) for y in s0]
            print(f"  {r['subject']:18} ref {r['truth']} ours {r['answer']} far_rung="
                  f"{'yes' if r['far_rung'] else 'no '} group={r.get('group','-')} rungs(rn,rf,rm)={nums}")
    if "--sheet" in sys.argv:
        make_sheet(rows, heads, Path(sys.argv[sys.argv.index("--sheet") + 1]))
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(
            json.dumps(rows, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
