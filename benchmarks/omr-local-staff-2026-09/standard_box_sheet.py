#!/usr/bin/env python3
"""lane-standard-head-box (2026-10-04): the sheet. One tile per far head whose
read changes under a STANDARD-size box (S1 / S2 of score_standard_box.py) plus
Sean's named tiles 1, 3, 4, 7-10 of the 10-wrong sheet regardless.

Real print at the gather's 600 dpi, scaled x6 (cubic). Drawn:
  RED thin      the detector's box
  CYAN          the standard box (page-measured head size, centre from the
                template's free position search) -- the box the S1 reading used
  ORANGE        a ledger the S1 reading COUNTED
  MAGENTA dash  a line the ink offered that the S1 reading threw away, with
                the rule that threw it
  GREEN tick    where the reference's pitch would sit

Pixel checks (numbers printed and written to the key json):
  every drawn LINE  ink on its row +-1 px beside the box vs 0.5 sp off it
                    (wrong10_sheet.check_and_snap; a line off ink is snapped
                    and reported)
  every drawn BOX   the head's opened-ink blob (stem / ledger / staff remnants
                    opened away, components through the standard oval, clipped
                    to +-1.2 sp) -- share of the blob inside the box, share of
                    the box that is ink, and the blob's four extents against
                    the box's four edges (px)
  CONTROLS          the same box check on clean in-staff heads: correct centre
                    vs the same box displaced 1 sp (must read worse), and the
                    search started 0.3 sp / 1.2 sp off the head (recovers /
                    fails)

    python3 benchmarks/omr-local-staff-2026-09/standard_box_sheet.py --sheet out/print/ledgers/standard_box
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

import edge_census as ec  # noqa: E402
import edge_fix_sheet as efs  # noqa: E402
import far_edge_crops as fec  # noqa: E402
import score_far_side as sf  # noqa: E402
import score_standard_box as sb  # noqa: E402
import wrong10_sheet as w10  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402
from tools.omr.annotate import standard_head_box as shb  # noqa: E402

CYAN, RED, ORANGE, MAGENTA, GREEN = (0, 190, 220), (200, 0, 0), (255, 140, 0), (230, 0, 200), (0, 150, 0)
SCALE = 6
HALF_W_SP = 4.4
NAMED = ["glyph/1/0/10/7/1", "glyph/3/0/0/2/9", "glyph/3/0/0/6/2", "glyph/3/0/7/4/3",
         "glyph/3/0/7/6/1", "glyph/3/0/7/7/0", "glyph/3/1/0/6/0"]
SEAN = {
    "glyph/1/0/10/7/1": "half note ON the line above the staff; box too small, grabs only the upper half",
    "glyph/3/0/0/2/9": "in a space; the notehead box is too big",
    "glyph/3/0/0/6/2": "ON its line (-6): the open-ended half note; the reference (-4) is wrong",
    "glyph/3/0/7/4/3": "pink line should be L2, the red box is where it should be",
    "glyph/3/0/7/6/1": "the thrown line IS the ledger; the red box is right",
    "glyph/3/0/7/7/0": "the thrown line IS the ledger; the red box is right",
    "glyph/3/1/0/6/0": "the thrown line IS the ledger; the red box is right",
}


def read_trace_box(h, box):
    h2 = dict(h, box=tuple(float(v) for v in box))
    ec.uninstall()
    pos, reason = sf.read(h2, **sf.ARMS["fix1_far"])
    ec.install()
    try:
        pos1, reason1, tr = efs.read_arm(h2, **efs.ARM_KW["after"])
    finally:
        ec.uninstall()
    assert (pos1, reason1) == (pos, reason), (h["subject"], pos1, pos, reason1, reason)
    return h2, pos, reason, tr


def box_blob_numbers(gray, box, centre, spacing, shape):
    """The head's opened-ink blob vs a box (see module doc)."""
    cx, cy = centre
    poly = ht.geometry_outline_poly(cx, cy, spacing, shape["tilt_deg"], shape["width_sp"], shape["height_sp"])
    pad = int(round(2.2 * spacing))
    H, W = gray.shape
    wx0, wy0 = max(0, int(cx) - pad), max(0, int(cy) - pad)
    wx1, wy1 = min(W, int(cx) + pad + 1), min(H, int(cy) + pad + 1)
    win = gray[wy0:wy1, wx0:wx1]
    ink = win <= ht._otsu_threshold(win)
    d = max(3, int(round(0.42 * spacing)) | 1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    op = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    oval = np.zeros(op.shape, np.uint8)
    cv2.fillPoly(oval, [np.array([[x - wx0, y - wy0] for x, y in poly], np.int32)], 1)
    oval = oval.astype(bool)
    clip = np.zeros(op.shape, bool)
    hw = int(round(1.2 * spacing))
    clip[max(0, int(cy - hw) - wy0):int(cy + hw) - wy0 + 1, max(0, int(cx - hw) - wx0):int(cx + hw) - wx0 + 1] = True
    num, lab = cv2.connectedComponents((op & clip).astype(np.uint8))
    keep = np.zeros_like(op)
    for i in range(1, num):
        comp = lab == i
        if (comp & oval).any():
            keep |= comp
    ys, xs = np.nonzero(keep)
    if xs.size == 0:
        return None
    bx = np.zeros(op.shape, bool)
    x0, y0, x1, y1 = box
    bx[max(0, int(round(y0)) - wy0):max(0, int(round(y1)) - wy0 + 1), max(0, int(round(x0)) - wx0):max(0, int(round(x1)) - wx0 + 1)] = True
    inter = (keep & bx).sum()
    return dict(blob_in_box=round(float(inter / keep.sum()), 2),
                box_is_ink=round(float(inter / max(1, bx.sum())), 2),
                d_left=round(float(xs.min() + wx0 - x0), 1), d_right=round(float(xs.max() + wx0 - x1), 1),
                d_top=round(float(ys.min() + wy0 - y0), 1), d_bottom=round(float(ys.max() + wy0 - y1), 1),
                blob_wh_px=[int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)])


def controls(D, n=12):
    """In-staff clean heads: the standard box at the found centre vs displaced
    1 sp (box check can fail), and the search started off the head."""
    shp_for = D["shapes"]
    cand = [h for h in D["heads_in"] if h["isolated"] and h["meas"]["ok"] and h["kind"] == "filled"
            and 2 <= h["pos"] <= 6]
    cand.sort(key=lambda h: (h["page"], h["subject"]))
    idx = np.linspace(0, len(cand) - 1, n).round().astype(int)
    rows = []
    for i in idx:
        h = cand[int(i)]
        shp, tm, sp, g = shp_for[h["page"]], D["tmpl"][h["page"]], h["spacing"], D["pages"].get(h["page"])
        b = h["meas"]["blob"]
        ms = w10.__dict__.get("_ms") or None
        import shape_from_page as sfp
        m = sfp.moments_shape(b["outer"])
        tcx, tcy = b["org"][0] + m["cx"], b["org"][1] + m["cy"]      # the head's OWN centroid on the print
        x0, y0, x1, y1 = h["box"]
        dcx, dcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        out = dict(subject=h["subject"], pos=h["pos"])
        for tag, off in (("det", (0.0, 0.0)), ("off0.3", (0.3, 0.3)), ("off1.2", (1.2, 0.0))):
            box0 = (x0 + off[0] * sp, y0 + off[1] * sp, x1 + off[0] * sp, y1 + off[1] * sp)
            st = shb.standard_head_box(g, box0, sp, tm, shp, "filled", None)
            out[tag] = round(float(np.hypot(st["centre"][0] - tcx, st["centre"][1] - tcy) / sp), 2)
        # box check: right centre vs 1 sp displaced
        stb = shb.standard_box_at(tcx, tcy, sp, shp["width_sp"], shp["height_sp"], shp["tilt_deg"])
        dsp = shb.standard_box_at(tcx + sp, tcy, sp, shp["width_sp"], shp["height_sp"], shp["tilt_deg"])
        n1 = box_blob_numbers(g, stb, (tcx, tcy), sp, shp)
        n2 = box_blob_numbers(g, dsp, (tcx, tcy), sp, shp)
        out["box_right"] = n1["blob_in_box"] if n1 else None
        out["box_displaced"] = n2["blob_in_box"] if n2 else None
        rows.append(out)
    return rows


def make_tile(h, st, h1, pos, counted, dropped, sp, sign, edge, edge_pos, ref, number, boxes_fit):
    from PIL import Image, ImageDraw, ImageFont
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    sx0, sy0, sx1, sy1 = st["box"]
    cx = (x0 + x1) / 2.0
    ref_y = edge + sign * abs(ref - edge_pos) * sp / 2.0
    ys_in = [y0, y1, sy0, sy1, edge, ref_y] + list(counted) + [d[0] for d in dropped]
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
        for xs in range(0, tw, 26):
            d.line([(xs, py), (xs + 13, py)], fill=MAGENTA, width=2)
        label(6, py + 3, lab, MAGENTA)
    ax, ay = P(x0, y0)
    bx, by = P(x1 + 1, y1 + 1)
    d.rectangle([ax, ay, bx, by], outline=RED, width=1)
    ax, ay = P(sx0, sy0)
    bx, by = P(sx1 + 1, sy1 + 1)
    d.rectangle([ax, ay, bx, by], outline=CYAN, width=3)
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
    Ds, res = {}, {}
    for doc in ts.DOCS:
        Ds[doc] = sb.build(doc)
        res[doc] = sb.run_arms(Ds[doc])
    # control: S0 equals the committed 32/10/2 and 11/0/0
    for doc in ts.DOCS:
        print("S0", doc, ec.tally([r["reads"]["S0"]["v"] for r in res[doc].values()]))
    lit = "beethoven5-litolff"
    assert ec.tally([r["reads"]["S0"]["v"] for r in res[lit].values()]) == {"right": 32, "wrong": 10, "abstain": 2}
    D = Ds[lit]
    far = {h["subject"]: h for h in D["far"]}
    changed = [s for s, r in res[lit].items()
               if any((r["reads"][a]["pos"], r["reads"][a]["v"]) != (r["reads"]["S0"]["pos"], r["reads"]["S0"]["v"])
                      for a in ("S1", "S2"))]
    show = sorted(set(changed) | set(NAMED), key=lambda s: (s not in NAMED, NAMED.index(s) if s in NAMED else 0, s))
    # named first, in Sean's order, then the other changed heads
    tiles, key = [], []
    for n, s in enumerate(show, start=1):
        h, r = far[s], res[lit][s]
        st = r["st"]
        sp = h["spacing"]
        h1, pos, reason, tr = read_trace_box(h, st["box"])
        assert (pos, reason) == (r["reads"]["S1"]["pos"], r["reads"]["S1"]["reason"]), s
        counted, dropped, sp_, sign, edge, edge_pos = w10.lines_for(h1, pos, tr)
        cen = ec.census_row(h1, pos, reason, tr)
        px, c2, d2 = [], [], []
        for y in counted:
            yy, pn, mv, good = w10.check_and_snap(h1, y, sp)
            c2.append(yy)
            px.append(dict(kind="orange", y=round(y, 1), moved_px=mv, on_ink=good, **w10._nums(pn)))
        for y, lab in dropped:
            yy, pn, mv, good = w10.check_and_snap(h1, y, sp)
            d2.append((yy, lab))
            px.append(dict(kind="magenta", y=round(y, 1), moved_px=mv, on_ink=good, label=lab, **w10._nums(pn)))
        shp = D["shapes"][h["page"]]
        fit = dict(red=box_blob_numbers(h["gray"], h["box"], st["centre"], sp, shp),
                   cyan=box_blob_numbers(h["gray"], st["box"], st["centre"], sp, shp))
        ref = h["truth"][0]
        img = make_tile(h, st, h1, pos, c2, d2, sp, sign, edge, edge_pos, ref, n, fit)
        tiles.append(dict(n=n, subject=s, img=img, r=r, ref=ref, h=h))
        key.append(dict(n=n, subject=s, named=s in NAMED, sean=SEAN.get(s),
                        reads={a: dict(pos=v["pos"], v=v["v"], reason=v["reason"]) for a, v in r["reads"].items()},
                        reference=r["truth"], standard_box=st["box"], detector_box=h["box"],
                        centre_shift_sp=st["shift_sp"], size_ratio=st["size_ratio"], gate_pass=st["pass"], fit=st["fit"],
                        evidenced_at_standard_box=tr.get("evidenced"),
                        census_drops_at_standard_box=cen["drops"], derive_pops=tr.get("pops"),
                        pixel_check_lines=px, pixel_check_boxes=fit, frame_control=fec._frame_control(h, sp)))
    ctrl = {doc: controls(Ds[doc]) for doc in ts.DOCS}
    outdir = Path(sys.argv[sys.argv.index("--sheet") + 1])
    outdir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    pad, cap, top = 24, 250, 170
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
    dr.text((pad, 14), "Standard-size head box on Litolff far heads.  Real print, 600 dpi, x%d." % SCALE, fill=(0, 0, 0), font=f)
    yy = 62
    for l in wrap("RED thin = the detector's box.  CYAN = the STANDARD box (page-measured head size, centre from the template's free "
                  "search; the box the 'after' reading used).  ORANGE = ledger counted.  MAGENTA dashed = line thrown, with the rule.  "
                  "GREEN tick = the reference pitch.  Captions: S0 detector box / S1 standard box on every head / S2 standard box only "
                  "where the template fit passes its pre-set gate.", W):
        dr.text((pad, yy), l, fill=(0, 0, 0), font=fs)
        yy += 30
    y = top
    for r, hh in zip(rows, rh):
        for c, t in enumerate(r):
            x = pad + c * (cw + pad)
            sheet.paste(t["img"], (x, y))
            yy = y + t["img"].height + 6
            rd = t["r"]["reads"]
            st = t["r"]["st"]
            dr.text((x, yy), f"{t['n']}. {t['subject']}", fill=(0, 0, 0), font=fs)
            yy += 30
            lines = [f"before S0 (detector box): {rd['S0']['pos']} {rd['S0']['v']}",
                     f"after S1 (standard box): {rd['S1']['pos']} {rd['S1']['v']}   S2: {rd['S2']['pos']} {rd['S2']['v']} "
                     f"(gate {'PASS' if st['pass'] else 'fail'}: IoU {st['fit']['iou_open']} off {st['fit']['offset_open_sp']} sp)",
                     f"reference: {t['ref']}   box shift {st['shift_sp']} sp, size x{st['size_ratio']}"]
            if t["subject"] in SEAN:
                lines.append("Sean: " + SEAN[t["subject"]])
            for ln in lines:
                for l in wrap(ln, cw):
                    dr.text((x, yy), l, fill=(160, 0, 0) if ln.startswith("Sean") else (0, 0, 0), font=fs)
                    yy += 28
        y += hh
    out = outdir / "standard_box_sheet.png"
    sheet.save(out)
    (outdir / "standard_box_key.json").write_text(json.dumps(dict(tiles=key, controls=ctrl), indent=1, default=sb._clean))
    print("sheet:", out.resolve(), sheet.size)
    print("\n== per-tile numbers ==")
    for k in key:
        print(f"{k['n']:>2} {k['subject']:18} S0 {k['reads']['S0']['pos']}/{k['reads']['S0']['v']} S1 {k['reads']['S1']['pos']}/{k['reads']['S1']['v']} "
              f"S2 {k['reads']['S2']['pos']}/{k['reads']['S2']['v']} ref={k['reference']} gate={k['gate_pass']} fit={k['fit']} "
              f"shift={k['centre_shift_sp']} size={k['size_ratio']} evidenced@std={k['evidenced_at_standard_box']}")
        print("    S1 reason:", k["reads"]["S1"]["reason"][:140])
        for dd in k["census_drops_at_standard_box"]:
            print("    drop:", {a: (round(b, 2) if isinstance(b, float) else b) for a, b in dd.items()})
        for p in k["pixel_check_lines"]:
            print("    line:", p["kind"], "y", p["y"], "moved", p["moved_px"], "on_ink", p["on_ink"], "near", p["near_on"], "/", p["near_off"],
                  "ridge", p["ridge_on"], "/", p["ridge_off"], p.get("label", ""))
        print("    box red :", k["pixel_check_boxes"]["red"])
        print("    box cyan:", k["pixel_check_boxes"]["cyan"])
        print("    frame control on/off:", round(k["frame_control"]["on"], 2), round(k["frame_control"]["off"], 2))
    print("\n== controls (in-staff clean heads) ==")
    for doc, rows_ in ctrl.items():
        print(doc, "centre error (sp) search from detector / 0.3 sp off / 1.2 sp off: medians",
              [round(float(np.median([r_[t] for r_ in rows_])), 2) for t in ("det", "off0.3", "off1.2")],
              "max", [round(float(max(r_[t] for r_ in rows_)), 2) for t in ("det", "off0.3", "off1.2")],
              "| blob-in-box right vs displaced 1sp: mean",
              round(float(np.mean([r_["box_right"] for r_ in rows_ if r_["box_right"] is not None])), 2),
              round(float(np.mean([r_["box_displaced"] for r_ in rows_ if r_["box_displaced"] is not None])), 2))


if __name__ == "__main__":
    main()
