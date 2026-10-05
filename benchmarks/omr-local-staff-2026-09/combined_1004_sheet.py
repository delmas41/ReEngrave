#!/usr/bin/env python3
"""lane-farhead-combined-1004 (2026-10-04): the sheet for Sean.  The Litolff far
heads still wrong/undecided after exclusion + standard box + hollow fill (E3 of
score_combined_1004.py), plus `glyph/3/0/0/6/2` (reference wrong per Sean) for
the record.  Real print at the gather's 600 dpi, x6 (cubic).

  RED corner brackets   the note (the detector's box, just outside its ink)
  CYAN rectangle        the head box the reader ACTUALLY used (the standard box
                        where its gate passed, otherwise the detector's box)
  ORANGE line           a ledger the reader counted
  MAGENTA dashed line   a line the ink offered that the reader threw away (why)
  GREEN tick            where the reference's pitch would sit

Every orange / magenta line is pixel-checked (w10.check_and_snap: ink on its
row +-1 px vs 0.5 sp off, beside the box; a line not on ink is snapped to the
ink row it names within 0.35 sp, and the move is reported); the cyan box is
checked against the head's own opened-ink blob (standard_box_sheet
.box_blob_numbers); a frame control (staff edge line on vs 0.5 sp beyond) must
read on > off.

    python3 benchmarks/omr-local-staff-2026-09/combined_1004_sheet.py --sheet out/print/ledgers/combined_1004
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import accidental_census as ac  # noqa: E402
import edge_census as ec  # noqa: E402
import far_edge_crops as fec  # noqa: E402
import score_combined_1004 as sc  # noqa: E402
import score_standard_box as sb  # noqa: E402
import standard_box_sheet as sbs  # noqa: E402
import wrong10_sheet as w10  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

CYAN, RED, ORANGE, MAGENTA, GREEN = (0, 190, 220), (200, 0, 0), (255, 140, 0), (230, 0, 200), (0, 150, 0)
SCALE = 6
HALF_W_SP = 4.4
FOR_THE_RECORD = {"glyph/3/0/0/6/2"}


def traced_read(h, box, kw):
    """The same read as the scorer, with the walk recorded (run-time wrappers of
    edge_census); asserted equal to the unrecorded read."""
    h2 = dict(h, box=tuple(float(v) for v in box))
    ec.uninstall()
    pos, reason = sc.se.read(h2, **kw)
    ec.install()
    lg.derive_far_head_step = ac._derive
    try:
        pos1, reason1, tr = ac.read(h2, record=True, **kw)
    finally:
        ec.uninstall()
    assert (pos1, reason1) == (pos, reason), (h["subject"], pos, pos1, reason, reason1)
    return h2, pos, reason, tr


def make_tile(h, box_used, counted, dropped, sp, sign, edge, edge_pos, ref, number):
    from PIL import Image, ImageDraw, ImageFont
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    ux0, uy0, ux1, uy1 = box_used
    cx = (x0 + x1) / 2.0
    ref_y = edge + sign * abs(ref - edge_pos) * sp / 2.0
    ys_in = [y0, y1, uy0, uy1, edge, ref_y] + list(counted) + [d[0] for d in dropped]
    lo, hi = min(ys_in), max(ys_in)
    lo -= (1.2 * sp if sign > 0 else 0.9 * sp)
    hi += (0.9 * sp if sign > 0 else 1.2 * sp)
    ax0, ax1 = int(round(cx - HALF_W_SP * sp)), int(round(cx + HALF_W_SP * sp))
    ay0, ay1 = int(round(lo)), int(round(hi))
    H, W = gray.shape
    crop = np.full((ay1 - ay0, ax1 - ax0), 255, np.uint8)
    a0, b0, a1, b1 = max(ax0, 0), max(ay0, 0), min(ax1, W), min(ay1, H)
    crop[b0 - ay0:b1 - ay0, a0 - ax0:a1 - ax0] = gray[b0:b1, a0:a1]
    tw, th = (ax1 - ax0) * SCALE, (ay1 - ay0) * SCALE
    big = cv2.resize(crop, (tw, th), interpolation=cv2.INTER_CUBIC)
    img = Image.fromarray(big).convert("RGB")
    d = ImageDraw.Draw(img)
    P = lambda x, y: ((x - ax0 + 0.5) * SCALE, (y - ay0 + 0.5) * SCALE)  # noqa: E731
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
        for xs_ in range(0, tw, 26):
            d.line([(xs_, py), (xs_ + 13, py)], fill=MAGENTA, width=2)
        label(6, py + 3, lab, MAGENTA)
    # cyan = the box the reader used
    ax, ay = P(ux0, uy0)
    bx, by = P(ux1 + 1, uy1 + 1)
    d.rectangle([ax, ay, bx, by], outline=CYAN, width=3)
    # red corner brackets, just outside the cyan/detector extent
    L, g, wd = 0.28 * sp * SCALE, 9, 3
    bx0, by0 = P(min(x0, ux0), min(y0, uy0))
    bx1, by1 = P(max(x1, ux1) + 1, max(y1, uy1) + 1)
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
    Ds, res = sc.run()
    lit = sc.LIT
    # controls (each can fail)
    t = sc.tallies(res)
    assert t[("M0", lit)][0] == {"right": 32, "wrong": 10, "abstain": 2}, t
    assert t[("E1", lit)][0] == {"right": 36, "wrong": 6, "abstain": 2}, t
    assert t[("E3", lit)][0] == {"right": 40, "wrong": 3, "abstain": 1}, t
    for arm in sc.ARMS:
        assert t[(arm, "brahms1-breitkopf")][0] == {"right": 11, "wrong": 0, "abstain": 0}, (arm, t)
    D = Ds[lit]
    heads = {x["subject"]: x for x in D["far"]}
    show = []
    for s, r in res[lit].items():
        e = r["reads"]["E3"]
        tr_ = sc.SEAN.get(s, r["truth"])
        if ec.verdict(e["pos"], tr_) != "right" or s in FOR_THE_RECORD:
            show.append(s)
    show.sort(key=lambda s: (s in FOR_THE_RECORD, s))
    tiles, key = [], []
    for n, s in enumerate(show, start=1):
        h, r = heads[s], res[lit][s]
        e = r["reads"]["E3"]
        sp = h["spacing"]
        h2, pos, reason, tr = traced_read(h, e["box"], sc.kw_of("E3"))
        assert (pos, reason) == (e["pos"], e["reason"])
        counted, dropped, sp_, sign, edge, edge_pos = w10.lines_for(h2, pos, tr)
        if pos is None and "head's own outline" in reason:
            # the reader's own words for it: the only row found IS the head's outline
            dropped = [(y, "thrown: the head's own outline") for y, _lab in dropped]
        px, c2, d2 = [], [], []
        for y in counted:
            yy, pn, mv, good = w10.check_and_snap(h2, y, sp)
            c2.append(yy)
            px.append(dict(kind="orange", y=round(y, 1), moved_px=mv, on_ink=good, **w10._nums(pn)))
        for y, lab in dropped:
            yy, pn, mv, good = w10.check_and_snap(h2, y, sp)
            d2.append((yy, lab))
            px.append(dict(kind="magenta", y=round(y, 1), moved_px=mv, on_ink=good, label=lab, **w10._nums(pn)))
        ref = sc.SEAN.get(s, r["truth"])[0]
        st = r["s2h"]
        shp = D["shapes"][h["page"]]
        centre = st["centre"] if e["std_used"] else (((h["box"][0] + h["box"][2]) / 2.0), ((h["box"][1] + h["box"][3]) / 2.0))
        boxnum = sbs.box_blob_numbers(h["gray"], tuple(e["box"]), centre, sp, shp)
        img = make_tile(h, e["box"], c2, d2, sp, sign, edge, edge_pos, ref, n)
        tiles.append(dict(n=n, subject=s, img=img, pos=pos, ref=ref, r=r, e=e, record=s in FOR_THE_RECORD))
        key.append(dict(n=n, subject=s, ours=pos, reference_as_scored=r["truth"], reference_vs_sean=ref,
                        reason=reason, std_box_used=e["std_used"], box_used=e["box"], detector_box=list(h["box"]),
                        gate=dict(passed=st["pass"], **st["fit"]), counted=len(counted), thrown=len(dropped),
                        pixel_check_lines=px, pixel_check_box_used=boxnum, frame_control=fec._frame_control(h, sp),
                        reads={a: dict(pos=v["pos"], v=v["v"]) for a, v in r["reads"].items()}))
    outdir = Path(sys.argv[sys.argv.index("--sheet") + 1])
    outdir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    pad, cap, top = 24, 230, 230
    cols = 2
    cw = max(t_["img"].width for t_ in tiles)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    rh = [max(t_["img"].height for t_ in r_) + cap for r_ in rows]
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, top + sum(rh) + pad), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)

    def wrap(text, width):
        out, cur = [], ""
        for w in text.split():
            t_ = (cur + " " + w).strip()
            if dr.textlength(t_, font=fs) > width and cur:
                out.append(cur)
                cur = w
            else:
                cur = t_
        return out + [cur]

    W = sheet.width - 2 * pad
    dr.text((pad, 14), "Litolff far heads still not right after all of today's pieces together.  Real print, 600 dpi, x%d." % SCALE,
            fill=(0, 0, 0), font=f)
    yy = 62
    for l in wrap("RED corner brackets = the note.   CYAN box = the head box the reader actually used (the page-standard box where its fit "
                  "check passed, otherwise the detector's).   ORANGE line = a ledger the reader counted.   MAGENTA dashed = a line the ink "
                  "offered that the reader threw away (label = why).   GREEN tick at the left = where the reference's pitch would sit.   "
                  "Under each: what we read / what the reference says.   Tile 4 is only for the record: it now reads right against what Sean read.", W):
        dr.text((pad, yy), l, fill=(0, 0, 0), font=fs)
        yy += 32
    y = top
    for r_, hh in zip(rows, rh):
        for c, t_ in enumerate(r_):
            x = pad + c * (cw + pad)
            sheet.paste(t_["img"], (x, y))
            yy = y + t_["img"].height + 6
            dr.text((x, yy), f"{t_['n']}. {t_['subject']}", fill=(0, 0, 0), font=fs)
            yy += 30
            for l in wrap(f"we read ({t_['pos']}): {w10.words(t_['pos'])}", cw):
                dr.text((x, yy), l, fill=(0, 0, 0), font=fs)
                yy += 28
            rtxt = f"reference ({t_['ref']}): {w10.words(t_['ref'])}"
            if t_["record"]:
                rtxt += "  [the file's reference says -4; Sean: -6]"
            for l in wrap(rtxt, cw):
                dr.text((x, yy), l, fill=(160, 0, 0) if t_["record"] else (0, 0, 0), font=fs)
                yy += 28
            for l in wrap("box: " + ("standard box" if t_["e"]["std_used"] else "detector's box (standard box not trusted: its fit check failed)"), cw):
                dr.text((x, yy), l, fill=(90, 90, 90), font=fs)
                yy += 28
        y += hh
    out = outdir / "combined_1004_sheet.png"
    sheet.save(out)
    (outdir / "combined_1004_key.json").write_text(json.dumps(key, indent=1, default=sb._clean))
    print("sheet:", out.resolve(), sheet.size)
    for k in key:
        print(f"\n{k['n']}. {k['subject']} we={k['ours']} ref(scored)={k['reference_as_scored']} ref(Sean)={k['reference_vs_sean']}"
              f" std_box={k['std_box_used']} gate={k['gate']} | {k['reason']}")
        for p in k["pixel_check_lines"]:
            print("    line:", p["kind"], "y", p["y"], "moved_px", p["moved_px"], "on_ink", p["on_ink"],
                  "near on/off", p["near_on"], "/", p["near_off"], "ridge", p["ridge_on"], "/", p["ridge_off"], p.get("label", ""))
        print("    cyan box vs head blob:", k["pixel_check_box_used"])
        print("    frame control on/off:", round(k["frame_control"]["on"], 2), round(k["frame_control"]["off"], 2))


if __name__ == "__main__":
    main()
