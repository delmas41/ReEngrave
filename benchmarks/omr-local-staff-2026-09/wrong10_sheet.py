#!/usr/bin/env python3
"""lane-ledger-wrong10-sheet (2026-10-04): ONE crop sheet of the far heads the
round-8 reader (fix 1 + far-side rule) still gets WRONG on Litolff (32/10/2 of
44).  Reads only; `tools/` untouched.

One numbered tile per head: the real print cut from the gather's own render
(600 dpi, nearest the staff edge to past the head), scaled x6 (cubic), centred
on the head.  Drawn on each tile:

  RED corner brackets   the detector's box for the head (just outside its ink)
  ORANGE thin line      a ledger the reader COUNTED
  MAGENTA dashed line   a line the ink offered that the reader threw away,
                        with a short label of why
  GREEN tick (margin)   where the reference's pitch would sit (nominal grid)

Under each tile, plain words: what we read / what the reference says.
Every orange / magenta line is pixel-checked (ink on its row +-1 px vs the same
rows 0.5 sp off it, in the 1 sp stub zones beside the box, and over the head
span); a drawn line that is not on ink is snapped to the ink row it names (or
dropped from the drawing and reported) BEFORE the sheet is written.  A frame
control (staff outer line vs 0.5 sp beyond it) must read on > off.

    python3 benchmarks/omr-local-staff-2026-09/wrong10_sheet.py \
        --sheet out/print/ledgers/wrong10
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402

import edge_census as ec  # noqa: E402
import edge_fix_sheet as efs  # noqa: E402
import far_edge_crops as fec  # noqa: E402
import score_far_side as sf  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

ORANGE, MAGENTA, RED, GREEN = (255, 140, 0), (230, 0, 200), (200, 0, 0), (0, 150, 0)
SCALE = 6                      # integer upscale of the gather-DPI raster
HALF_W_SP = 4.4                # tile half-width in staff spaces
REF_WRONG = sf.WRONG_REFERENCE

DROP_LABEL = {
    "clears_box": "thrown: not clear past the head",
    "collapse_edges": "thrown: head's own edge",
    "derive_pop": "thrown: lies past the head",
    "exclusion_or_cascade": "thrown: other note's ink",
    "beyond": "thrown: lies past the head",
}


# ------------------------------------------------------------ plain words
def _ord(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def words(pos):
    """Staff position (half-steps from the TOP line, 0 = top line, 8 = bottom
    line; negative = above, >8 = below) in plain words."""
    if pos is None:
        return "nothing (abstained)"
    if 0 <= pos <= 8:
        return ("on staff line %d" % (pos // 2 + 1)) if pos % 2 == 0 else \
            "in staff space %d" % (pos // 2 + 1)
    if pos < 0:
        n, edge, side = -pos, "top line", "above"
    else:
        n, edge, side = pos - 8, "bottom line", "below"
    if n % 2 == 0:
        return f"ON the {_ord(n // 2)} ledger line {side} the staff"
    k = (n - 1) // 2
    if k == 0:
        return f"in the SPACE just {side} the staff ({edge} to 1st ledger)"
    return f"in the SPACE {side} the {_ord(k)} ledger (between ledger {k} and {k + 1})"


# ------------------------------------------------------------ the reader's lines
def read_trace(h):
    """Final reader answer (fix 1 + far-side rule, the scored arm) plus the
    trace of the same walk (fix-1 arm: the far-side rule's wrapper is not
    traceable, and it must not -- and is asserted not to -- change the head)."""
    ec.uninstall()
    pos, reason = sf.read(h, **sf.ARMS["fix1_far"])
    ec.install()
    try:
        pos1, reason1, tr = efs.read_arm(h, **efs.ARM_KW["after"])
    finally:
        ec.uninstall()
    assert (pos1, reason1) == (pos, reason), (h["subject"], pos1, pos, reason1, reason)
    return pos, reason, tr


def lines_for(h, pos, tr):
    ys = sorted(float(v) for v in h["lines"])
    sp = (ys[-1] - ys[0]) / 4.0
    cy = (h["box"][1] + h["box"][3]) / 2.0
    sign = -1.0 if cy < ys[0] else 1.0
    edge = ys[0] if sign < 0 else ys[-1]
    edge_pos = 0 if sign < 0 else 8
    ladder = sorted(tr.get("final_ladder") or [], key=lambda v: sign * v)
    n = 0 if pos is None else int(sign * (pos - edge_pos)) // 2
    counted = list(ladder[:n])
    cen = ec.census_row(h, pos, "", tr)
    drops = []
    for d in cen["drops"]:
        drops.append((float(d["y"]), DROP_LABEL[d["rule"]]))
    for y in ladder[n:]:
        drops.append((float(y), DROP_LABEL["beyond"]))
    side, s0 = ec.stage0_candidates(h)
    for y in s0:
        drops.append((float(y), DROP_LABEL["exclusion_or_cascade"]))
    kept = []
    for y, lab in drops:
        if any(abs(y - c) < 0.35 * sp for c in counted):
            continue
        if any(abs(y - k[0]) < 0.35 * sp for k in kept):
            continue
        kept.append((y, lab))
    kept.sort(key=lambda t: sign * t[0])
    return counted, kept, sp, sign, edge, edge_pos


def near_stub(h, y, sp):
    """Ink beside the head on row y (+-1 px) vs the same zone 0.5 sp off it:
    the 0.1..0.6 sp zones just outside the box, left and right; the better
    side.  Also the 1 sp stub and the head-span numbers (far_edge_crops)."""
    x0, _, x1, _ = h["box"]
    g = h["gray"]
    best = None
    for side, (a, b) in dict(left=(x0 - 0.6 * sp, x0 - 0.1 * sp),
                             right=(x1 + 0.1 * sp, x1 + 0.6 * sp)).items():
        on = fec._ink_frac(g, y, a, b)
        off = max(fec._ink_frac(g, y - 0.5 * sp, a, b), fec._ink_frac(g, y + 0.5 * sp, a, b))
        if best is None or on - off > best[1] - best[2]:
            best = (side, on, off)
    pn = fec.pixel_numbers(g, y, h["box"], sp)
    # longest contiguous ink run (+-1 px of the row) beside the box, in sp,
    # within 1.2 sp of it, on the row vs the same at 0.5 sp off (max of the two)
    def run(yy):
        best_r = 0
        for a, b in ((x0 - 1.2 * sp, x0), (x1, x1 + 1.2 * sp)):
            a, b = max(0, int(a)), min(g.shape[1], int(b))
            ya = max(0, int(round(yy)) - 1)
            col = (g[ya:int(round(yy)) + 2, a:b] < fec.INK).any(axis=0)
            n = 0
            for v in col:
                n = n + 1 if v else 0
                best_r = max(best_r, n)
        return best_r / sp
    # ridge: dark px per row over the whole zone beside AND through the head
    # (a ledger is a ridge ~4-5 px thick): best of rows y-1..y+1 vs the rows
    # 5 px either side of y
    za, zb = max(0, int(x0 - 1.2 * sp)), min(g.shape[1], int(x1 + 1.2 * sp))
    cnt = lambda yy: int((g[int(round(yy)), za:zb] < fec.INK).sum())  # noqa: E731
    pn["ridge_on"] = max(cnt(y - 1), cnt(y), cnt(y + 1))
    pn["ridge_off"] = max(cnt(y - 5), cnt(y + 5))
    pn["run_on"] = run(y)
    pn["run_off"] = max(run(y - 0.5 * sp), run(y + 0.5 * sp))
    pn["near_side"], pn["near_on"], pn["near_off"] = best
    return pn


def check_and_snap(h, y, sp):
    """Pixel-check a line; a line not on ink (near-stub on < 0.6 or on-off <
    0.3) is moved to the best ink row within +-0.35 sp (reported).
    Returns (y_used, numbers, moved_px, ok)."""
    def ok(pn):
        return ((pn["near_on"] >= 0.6 and pn["near_on"] - pn["near_off"] >= 0.3)
                or (pn["ridge_on"] >= 15 and pn["ridge_on"] >= 1.8 * pn["ridge_off"]))
    pn0 = near_stub(h, y, sp)
    if ok(pn0):
        return y, pn0, 0, True
    best_y, best_pn = y, pn0
    for dy in range(-int(0.35 * sp), int(0.35 * sp) + 1):
        pn = near_stub(h, y + dy, sp)
        if (pn["near_on"] - pn["near_off"]) > (best_pn["near_on"] - best_pn["near_off"]) + 1e-9:
            best_y, best_pn = y + dy, pn
    return best_y, best_pn, int(round(best_y - y)), ok(best_pn)


# ------------------------------------------------------------ drawing
def make_tile(h, pos, counted, dropped, sp, sign, edge, edge_pos, ref, number):
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    cx = (x0 + x1) / 2.0
    ref_y = edge + sign * abs(ref - edge_pos) * sp / 2.0
    ys_in = [y0, y1, edge, ref_y] + [c for c in counted] + [d[0] for d in dropped]
    lo, hi = min(ys_in), max(ys_in)
    # include the first staff space past the edge so the staff edge is in view
    lo -= (1.2 * sp if sign > 0 else 0.9 * sp)
    hi += (0.9 * sp if sign > 0 else 1.2 * sp)
    ax0, ax1 = int(round(cx - HALF_W_SP * sp)), int(round(cx + HALF_W_SP * sp))
    ay0, ay1 = int(round(lo)), int(round(hi))
    H, W = gray.shape
    crop = np.full((ay1 - ay0, ax1 - ax0), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(ax0, 0), max(ay0, 0), min(ax1, W), min(ay1, H)
    crop[sy0 - ay0:sy1 - ay0, sx0 - ax0:sx1 - ax0] = gray[sy0:sy1, sx0:sx1]
    tw, th = (ax1 - ax0) * SCALE, (ay1 - ay0) * SCALE
    big = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_CUBIC)
    img = Image.fromarray(big).convert("RGB")
    d = ImageDraw.Draw(img)
    P = lambda x, y: ((x - ax0) * SCALE, (y - ay0) * SCALE)  # noqa: E731
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    big_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)

    def label(x, y, text, col):
        w = d.textlength(text, font=font)
        d.rectangle([x - 3, y - 2, x + w + 3, y + 26], fill=(255, 255, 255))
        d.text((x, y), text, fill=col, font=font)

    for i, y in enumerate(counted):
        _, py = P(0, y)
        d.line([(0, py), (tw, py)], fill=ORANGE, width=2)
        label(tw - 150, py - 30, f"counted L{i + 1}", ORANGE)
    for y, lab in dropped:
        _, py = P(0, y)
        for xs in range(0, tw, 26):
            d.line([(xs, py), (xs + 13, py)], fill=MAGENTA, width=2)
        label(6, py + 3, lab, MAGENTA)
    L, g, wd = 0.28 * sp * SCALE, 5, 3
    bx0, by0 = P(x0, y0)
    bx1, by1 = P(x1, y1)
    for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        px, py = px - dx * g, py - dy * g
        d.line([(px, py), (px + dx * L, py)], fill=RED, width=wd)
        d.line([(px, py), (px, py + dy * L)], fill=RED, width=wd)
    _, ry = P(0, ref_y)
    d.line([(0, ry), (26, ry)], fill=GREEN, width=5)
    _, ey = P(0, edge)
    label(34, ey - 13, "staff edge line", (90, 90, 90))
    d.rectangle([0, 0, 66, 56], fill=(255, 255, 255))
    d.text((8, 4), str(number), fill=(0, 0, 0), font=big_font)
    d.rectangle([0, 0, tw - 1, th - 1], outline=(120, 120, 120), width=2)
    return img


def main():
    from PIL import Image, ImageDraw, ImageFont
    heads = {d: ec.load_heads(d) for d in ts.DOCS}
    res = sf.run(heads)
    tallies = {}
    for arm in ("default", "fix1", "fix1_far"):
        for d in ts.DOCS:
            vs = [r["v"] for r in res[arm][d].values()]
            tallies[(arm, d)] = ec.tally(vs)
            print(f"control {arm:9} {d:20} {ec.tally(vs)} n={len(vs)}")
    litolff = "beethoven5-litolff"
    assert tallies[("fix1_far", litolff)] == {"right": 32, "wrong": 10, "abstain": 2}, tallies
    wrong = [h for h in heads[litolff] if res["fix1_far"][litolff][h["subject"]]["v"] == "wrong"]
    assert len(wrong) == 10 and any(h["subject"] in REF_WRONG for h in wrong)
    tiles, key = [], []
    for i, h in enumerate(wrong, start=1):
        s = h["subject"]
        pos, reason, tr = read_trace(h)
        counted, dropped, sp, sign, edge, edge_pos = lines_for(h, pos, tr)
        ref = h["truth"][0]
        # pixel check (and snap where a drawn line is not on ink)
        px, c2, d2 = [], [], []
        for y in counted:
            yy, pn, mv, good = check_and_snap(h, y, sp)
            c2.append(yy)
            px.append(dict(kind="orange", y=round(y, 1), moved_px=mv, on_ink=good, **_nums(pn)))
        for y, lab in dropped:
            yy, pn, mv, good = check_and_snap(h, y, sp)
            d2.append((yy, lab))
            px.append(dict(kind="magenta", y=round(y, 1), moved_px=mv, on_ink=good, label=lab, **_nums(pn)))
        fc = fec._frame_control(h, sp)
        tiles.append(dict(
            n=i, subject=s, h=h, img=make_tile(h, pos, c2, d2, sp, sign, edge, edge_pos, ref, i),
            pos=pos, ref=ref, reason=reason, ref_wrong=s in REF_WRONG))
        key.append(dict(n=i, subject=s, ours=pos, reference=ref, reason=reason,
                        reference_wrong_per_sean=s in REF_WRONG, sp=sp, frame_control=fc,
                        counted=len(counted), thrown=len(dropped), pixel_check=px))
    outdir = Path(sys.argv[sys.argv.index("--sheet") + 1]) if "--sheet" in sys.argv else None
    if outdir is None:
        return
    outdir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    pad, cap, top = 24, 170, 200
    cols = 2
    cw = max(t["img"].width for t in tiles)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    rh = [max(t["img"].height for t in r) + cap for r in rows]
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, top + sum(rh) + pad), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)

    def wrap(text, width):
        out, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if dr.textlength(t, font=fs) > width and cur:
                out.append(cur)
                cur = w
            else:
                cur = t
        return out + [cur]

    W = sheet.width - 2 * pad
    dr.text((pad, 14), "The 10 far heads on Litolff still read WRONG (round 8 + far-side rule).  "
            "Real print at the gather's 600 dpi, x%d." % SCALE, fill=(0, 0, 0), font=f)
    yy = 62
    for line in ("RED corner brackets = the note.   ORANGE line = a ledger the reader counted.   "
                 "MAGENTA dashed line = a line the ink offered that the reader threw away (label = why).   "
                 "GREEN tick at the left edge = where the reference's pitch would sit (nominal grid).   "
                 "Under each tile: what we read / what the reference says.",):
        for l in wrap(line, W):
            dr.text((pad, yy), l, fill=(0, 0, 0), font=fs)
            yy += 32
    y = top
    for r, hh in zip(rows, rh):
        for c, t in enumerate(r):
            x = pad + c * (cw + pad)
            sheet.paste(t["img"], (x, y))
            yy = y + t["img"].height + 6
            dr.text((x, yy), f"{t['n']}. {t['subject']}", fill=(0, 0, 0), font=fs)
            yy += 30
            for l in wrap(f"we read ({t['pos']}): {words(t['pos'])}", cw):
                dr.text((x, yy), l, fill=(0, 0, 0), font=fs)
                yy += 28
            rtxt = f"reference ({t['ref']}): {words(t['ref'])}"
            if t["ref_wrong"]:
                rtxt += "  [reference wrong per Sean: the head is ON its line]"
            for l in wrap(rtxt, cw):
                dr.text((x, yy), l, fill=(160, 0, 0) if t["ref_wrong"] else (0, 0, 0), font=fs)
                yy += 28
        y += hh
    out = outdir / "wrong10_sheet.png"
    sheet.save(out)
    (outdir / "wrong10_key.json").write_text(json.dumps(key, indent=1, default=str))
    print("sheet:", out.resolve(), sheet.size)
    print("\n#  subject              ours  ref   reason")
    for k in key:
        print(f"{k['n']:>2} {k['subject']:20} {k['ours']!s:>5} {k['reference']!s:>5}  {k['reason']}"
              + ("   [reference wrong per Sean]" if k["reference_wrong_per_sean"] else ""))
    print("\npixel check (stub zones beside the box, row +-1 px, on vs 0.5 sp off; span = head width +-0.5 sp)")
    for k in key:
        print(k["n"], k["subject"], "frame control on/off:",
              round(k["frame_control"]["on"], 2), round(k["frame_control"]["off"], 2))
        for p in k["pixel_check"]:
            print("   ", p)


def _nums(pn):
    return dict(ridge_on=pn["ridge_on"], ridge_off=pn["ridge_off"], near_on=round(pn["near_on"], 2), near_off=round(pn["near_off"], 2),
                near_side=pn["near_side"], stub_on=round(pn["stub_on"], 2), stub_off=round(pn["stub_off"], 2),
                span_on=round(pn["span_on"], 2), span_off=round(pn["span_off"], 2),
                stub_side=pn["stub_side"])


if __name__ == "__main__":
    main()
