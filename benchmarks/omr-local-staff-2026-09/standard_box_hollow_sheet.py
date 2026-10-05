#!/usr/bin/env python3
"""lane-standard-box-hollow (2026-10-04): the sheet + the controls.

One tile per HOLLOW far head (both documents) plus every head whose read or
box changed between S2 and S2H, plus Sean's tile 4 (`glyph/3/0/0/6/2`, which
the detector calls BLACK but whose ink holds a counter). Real print at the
gather's 600 dpi, scaled x6 (cubic). Drawn:
  RED thin      the detector's box
  CYAN          the standard box (page-measured head size, centre from the
                template's free search ON THE COUNTER-FILLED PAGE)
  BLUE          the template's outline at that centre
  YELLOW tint   the counter pixels that were filled
  ORANGE        a ledger the S2H reading COUNTED
  MAGENTA dash  a line the ink offered that the S2H reading threw away
  GREEN tick    where the reference's pitch would sit

Controls (printed; each can fail):
  F  every in-staff head the detector calls FILLED: number with a counter
     found (must be ~0)
  H  every in-staff head the detector calls HOLLOW: number with a counter
     found (must be ~all)
  G  in-staff hollow heads, the template fit's own gate (IoU >= 0.70, offset
     <= 0.15 sp) on the raw page vs the counter-filled page, and the free
     search's centre error against the head's own filled-blob centroid

    python3 benchmarks/omr-local-staff-2026-09/standard_box_hollow_sheet.py --sheet out/print/ledgers/standard_box_hollow
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
import far_edge_crops as fec  # noqa: E402
import score_standard_box as sb  # noqa: E402
import score_standard_box_hollow as sbh  # noqa: E402
import standard_box_sheet as sbs  # noqa: E402
import wrong10_sheet as w10  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402
from tools.omr.annotate import standard_head_box as shb  # noqa: E402

CYAN, RED, ORANGE, MAGENTA, GREEN, BLUE = (0, 190, 220), (200, 0, 0), (255, 140, 0), (230, 0, 200), (0, 150, 0), (30, 60, 255)
SCALE = 6
HALF_W_SP = 4.4
SEAN = {
    "glyph/1/0/10/7/1": "(tile 1) half note ON the line above the staff; box too small, grabs only the upper half",
    "glyph/3/0/0/6/2": "(tile 4) ON its line (-6): the open-ended half note; the reference (-4) is wrong",
}
SEAN_READ = {"glyph/3/0/0/6/2": [-6]}


def make_tile(h, st, box_used, hmask_win, counted, dropped, sp, sign, edge, edge_pos, ref, number, shp):
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

    # filled counter pixels, tinted yellow (mask is over the pocket window)
    if hmask_win is not None:
        (wx0, wy0, _wx1, _wy1), mask = hmask_win
        ys, xs = np.nonzero(mask)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for yv, xv in zip(ys, xs):
            px, py = P(xv + wx0 - 0.5, yv + wy0 - 0.5)
            od.rectangle([px, py, px + SCALE, py + SCALE], fill=(255, 230, 0, 150))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)
    for i, y in enumerate(counted):
        _, py = P(0, y)
        d.line([(0, py), (tw, py)], fill=ORANGE, width=2)
        label(tw - 150, py - 30, f"counted L{i + 1}", ORANGE)
    for y, lab in dropped:
        _, py = P(0, y)
        for xs_ in range(0, tw, 26):
            d.line([(xs_, py), (xs_ + 13, py)], fill=MAGENTA, width=2)
        label(6, py + 3, lab, MAGENTA)
    ax, ay = P(x0, y0)
    bx, by = P(x1 + 1, y1 + 1)
    d.rectangle([ax, ay, bx, by], outline=RED, width=1)
    ax, ay = P(sx0, sy0)
    bx, by = P(sx1 + 1, sy1 + 1)
    d.rectangle([ax, ay, bx, by], outline=CYAN, width=3)
    poly = ht.geometry_outline_poly(st["centre"][0], st["centre"][1], sp, shp["tilt_deg"], shp["width_sp"], shp["height_sp"])
    d.line([P(x, y) for x, y in list(poly) + [poly[0]]], fill=BLUE, width=2)
    _, ry = P(0, ref_y)
    d.line([(0, ry), (26, ry)], fill=GREEN, width=5)
    _, ey = P(0, edge)
    label(34, ey - 13, "staff edge line", (90, 90, 90))
    d.rectangle([0, 0, 66, 56], fill=(255, 255, 255))
    d.text((8, 4), str(number), fill=(0, 0, 0), font=big_font)
    d.rectangle([0, 0, tw - 1, th - 1], outline=(120, 120, 120), width=2)
    return img


def fill_controls(D):
    """F / H / G controls on every in-staff head of a document."""
    out = dict(F_n=0, F_pocket=[], H_n=0, H_pocket=0, G=[])
    for h in D["heads_in"]:
        shp, thick = D["shapes"][h["page"]], D["thick"][h["page"]]
        gray = D["pages"].get(h["page"])
        gf, info = shb.fill_counter(gray, h["box"], h["spacing"], thick, shp["height_sp"], shp["width_sp"], h["kind"] == "hollow")
        if h["kind"] == "filled":
            out["F_n"] += 1
            if info["pockets"]:
                out["F_pocket"].append(h["subject"])
            else:
                assert gf is gray
        else:
            out["H_n"] += 1
            out["H_pocket"] += bool(info["pockets"])
            if not info["pockets"] or not h["isolated"] or not h["meas"]["ok"]:
                pass
            # G: gate + centre error on the raw vs the filled page
            tm = D["tmpl"][h["page"]]
            row = dict(subject=h["subject"], isolated=bool(h["isolated"]))
            blob_c = None
            ys, xs = None, None
            for tag, g in (("raw", gray), ("filled", gf)):
                st = shb.standard_head_box(g, h["box"], h["spacing"], tm, shp, "hollow", None)
                poly = ht.geometry_outline_poly(st["centre"][0], st["centre"][1], h["spacing"], shp["tilt_deg"], shp["width_sp"], shp["height_sp"])
                chk = sb.r7.oval_vs_ink(g, h["box"], h["spacing"], thick, list(h["lines"]), poly, st["centre"][0], st["centre"][1])
                ok = bool(st["placed"] and chk["offset_open_sp"] is not None and chk["iou_open"] >= shb.FIT_IOU_MIN
                          and chk["offset_open_sp"] <= shb.FIT_OFFSET_MAX_SPACES)
                row[tag] = dict(iou=chk["iou_open"], off=chk["offset_open_sp"], gate=ok, centre=st["centre"])
            # the head's own centroid: the filled ink blob (Otsu) nearest the box centre, in a +-0.8 sp window
            sp = h["spacing"]
            x0, y0, x1, y1 = h["box"]
            m = int(round(0.9 * sp))
            wx0, wy0 = int(x0) - m, int(y0) - m
            win = gf[wy0:int(y1) + m + 1, wx0:int(x1) + m + 1]
            ink = (win <= ht._otsu_threshold(win)).astype(np.uint8)
            dd = max(3, int(round(0.42 * sp)) | 1)
            op = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dd, dd)))
            num, lab = cv2.connectedComponents(op)
            bcx, bcy = (x0 + x1) / 2 - wx0, (y0 + y1) / 2 - wy0
            best = None
            for i in range(1, num):
                yy, xx = np.nonzero(lab == i)
                dist = np.hypot(xx.mean() - bcx, yy.mean() - bcy)
                if best is None or dist < best[0]:
                    best = (dist, xx.mean() + wx0, yy.mean() + wy0)
            if best is not None:
                for tag in ("raw", "filled"):
                    c = row[tag]["centre"]
                    row[tag]["err_sp"] = round(float(np.hypot(c[0] - best[1], c[1] - best[2]) / sp), 2)
            out["G"].append(row)
    return out


def main():
    from PIL import Image, ImageDraw, ImageFont
    Ds, res = {}, {}
    for doc in ts.DOCS:
        Ds[doc] = sb.build(doc)
        res[doc] = {}
        for h in Ds[doc]["far"]:
            s2 = sb.standard_for(h, Ds[doc])
            s2h = sbh.standard_hollow(h, Ds[doc])
            row = dict(s2=s2, s2h=s2h, truth=h["truth"], kind=h["kind"], reads={})
            for arm, box in (("S0", h["box"]), ("S2", s2["box"] if s2["pass"] else h["box"]),
                             ("S2H", s2h["box"] if s2h["pass"] else h["box"])):
                pos, reason = sb.read(h, box, **sb.READER)
                row["reads"][arm] = dict(pos=pos, reason=reason, v=ec.verdict(pos, h["truth"]),
                                         box=[round(float(v), 2) for v in box])
            res[doc][h["subject"]] = row
    for doc in ts.DOCS:
        print("S0", doc, ec.tally([r["reads"]["S0"]["v"] for r in res[doc].values()]),
              "S2", ec.tally([r["reads"]["S2"]["v"] for r in res[doc].values()]),
              "S2H", ec.tally([r["reads"]["S2H"]["v"] for r in res[doc].values()]))
    lit = "beethoven5-litolff"
    assert ec.tally([r["reads"]["S0"]["v"] for r in res[lit].values()]) == {"right": 32, "wrong": 10, "abstain": 2}
    show = []
    for doc in ts.DOCS:
        for s, r in res[doc].items():
            ch = (r["reads"]["S2"]["pos"], r["reads"]["S2"]["box"]) != (r["reads"]["S2H"]["pos"], r["reads"]["S2H"]["box"])
            if r["kind"] == "hollow" or ch or s in SEAN:
                show.append((doc, s))
    show.sort(key=lambda t: (t[1] not in SEAN, t[0], t[1]))
    tiles, key = [], []
    for n, (doc, s) in enumerate(show, start=1):
        D = Ds[doc]
        h = {x["subject"]: x for x in D["far"]}[s]
        r = res[doc][s]
        st, sp = r["s2h"], h["spacing"]
        shp = D["shapes"][h["page"]]
        box_used = r["reads"]["S2H"]["box"]
        h1, pos, reason, tr = sbs.read_trace_box(h, box_used)
        assert (pos, reason) == (r["reads"]["S2H"]["pos"], r["reads"]["S2H"]["reason"]), s
        counted, dropped, sp_, sign, edge, edge_pos = w10.lines_for(h1, pos, tr)
        px, c2, d2 = [], [], []
        for y in counted:
            yy, pn, mv, good = w10.check_and_snap(h1, y, sp)
            c2.append(yy)
            px.append(dict(kind="orange", y=round(y, 1), moved_px=mv, on_ink=good, **w10._nums(pn)))
        for y, lab in dropped:
            yy, pn, mv, good = w10.check_and_snap(h1, y, sp)
            d2.append((yy, lab))
            px.append(dict(kind="magenta", y=round(y, 1), moved_px=mv, on_ink=good, label=lab, **w10._nums(pn)))
        thick = D["thick"][h["page"]]
        gf, info = shb.fill_counter(h["gray"], h["box"], sp, thick, shp["height_sp"], shp["width_sp"], h["kind"] == "hollow")
        boxes = dict(
            red_raw=sbs.box_blob_numbers(h["gray"], h["box"], st["centre"], sp, shp),
            cyan_raw=sbs.box_blob_numbers(h["gray"], st["box"], st["centre"], sp, shp),
            red_filled=sbs.box_blob_numbers(gf, h["box"], st["centre"], sp, shp),
            cyan_filled=sbs.box_blob_numbers(gf, st["box"], st["centre"], sp, shp))
        ref = h["truth"][0]
        img = make_tile(h, st, box_used, ((info["window"], info["mask"]) if info["pockets"] else None),
                        c2, d2, sp, sign, edge, edge_pos, ref, n, shp)
        tiles.append(dict(n=n, subject=s, doc=doc, img=img, r=r, ref=ref, h=h))
        key.append(dict(n=n, doc=doc, subject=s, kind=r["kind"], sean=SEAN.get(s), reference=r["truth"],
                        reads={a: dict(pos=v["pos"], v=v["v"], reason=v["reason"], box=v["box"]) for a, v in r["reads"].items()},
                        gate_s2=dict(r["s2"]["fit"], passed=r["s2"]["pass"]), gate_s2h=dict(r["s2h"]["fit"], passed=r["s2h"]["pass"]),
                        pockets=info["pockets"], standard_box_s2h=st["box"], detector_box=h["box"],
                        pixel_check_lines=px, pixel_check_boxes=boxes, frame_control=fec._frame_control(h, sp)))
    ctrl = {doc: fill_controls(Ds[doc]) for doc in ts.DOCS}
    outdir = Path(sys.argv[sys.argv.index("--sheet") + 1])
    outdir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    pad, cap, top = 24, 270, 190
    cols = 2
    cw = max(t["img"].width for t in tiles)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    rh = [max(t["img"].height for t in r_) + cap for r_ in rows]
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
    dr.text((pad, 14), "Standard head box with the half note's counter FILLED.  Real print, 600 dpi, x%d." % SCALE, fill=(0, 0, 0), font=f)
    yy = 62
    for l in wrap("RED thin = detector box.  CYAN = standard box (centre from the template's free search on the counter-filled page).  "
                  "BLUE = template outline.  YELLOW tint = counter pixels filled.  ORANGE = ledger counted.  MAGENTA dashed = line thrown.  "
                  "GREEN tick = reference pitch.  Captions: before = S2 (standard box where the fit passes, counter NOT filled), "
                  "after = S2H (counter filled first), reference, Sean.", W):
        dr.text((pad, yy), l, fill=(0, 0, 0), font=fs)
        yy += 30
    y = top
    for r_, hh in zip(rows, rh):
        for c, t in enumerate(r_):
            x = pad + c * (cw + pad)
            sheet.paste(t["img"], (x, y))
            yy = y + t["img"].height + 6
            rd, st2, st2h = t["r"]["reads"], t["r"]["s2"], t["r"]["s2h"]
            dr.text((x, yy), f"{t['n']}. {t['subject']} ({'Litolff' if 'beeth' in t['doc'] else 'Brahms'}, class {t['r']['kind']})", fill=(0, 0, 0), font=fs)
            yy += 30
            lines = [f"before S2: {rd['S2']['pos']} {rd['S2']['v']}  (gate {'PASS' if st2['pass'] else 'fail'}: IoU {st2['fit']['iou_open']} off {st2['fit']['offset_open_sp']})",
                     f"after S2H: {rd['S2H']['pos']} {rd['S2H']['v']}  (gate {'PASS' if st2h['pass'] else 'fail'}: IoU {st2h['fit']['iou_open']} off {st2h['fit']['offset_open_sp']}; "
                     f"{len(st2h['pockets'])} pocket(s) filled)  detector box S0: {rd['S0']['pos']} {rd['S0']['v']}",
                     f"reference: {t['ref']}"]
            if t["subject"] in SEAN:
                lines.append("Sean: " + SEAN[t["subject"]])
            for ln in lines:
                for l in wrap(ln, cw):
                    dr.text((x, yy), l, fill=(160, 0, 0) if ln.startswith("Sean") else (0, 0, 0), font=fs)
                    yy += 28
        y += hh
    out = outdir / "standard_box_hollow_sheet.png"
    sheet.save(out)
    (outdir / "standard_box_hollow_key.json").write_text(json.dumps(dict(tiles=key, controls=ctrl), indent=1, default=sb._clean))
    print("sheet:", out.resolve(), sheet.size)
    print("\n== per-tile numbers ==")
    for k in key:
        print(f"{k['n']:>2} {k['subject']:18} {k['kind']:6} S0 {k['reads']['S0']['pos']}/{k['reads']['S0']['v']} S2 {k['reads']['S2']['pos']}/{k['reads']['S2']['v']} "
              f"S2H {k['reads']['S2H']['pos']}/{k['reads']['S2H']['v']} ref={k['reference']} gate S2 {k['gate_s2']} S2H {k['gate_s2h']}")
        for p in k["pixel_check_lines"]:
            print("    line:", p["kind"], "y", p["y"], "moved", p["moved_px"], "on_ink", p["on_ink"], "near", p["near_on"], "/", p["near_off"],
                  "ridge", p["ridge_on"], "/", p["ridge_off"], p.get("label", ""))
        for nm, v in k["pixel_check_boxes"].items():
            print("    box", nm, v)
        print("    frame control on/off:", round(k["frame_control"]["on"], 2), round(k["frame_control"]["off"], 2))
    print("\n== controls ==")
    for doc, c in ctrl.items():
        print(doc[:8], f"F filled-class in-staff heads {c['F_n']}: with a counter found {len(c['F_pocket'])} {c['F_pocket'][:8]}")
        print(doc[:8], f"H hollow-class in-staff heads {c['H_n']}: with a counter found {c['H_pocket']}")
        G = c["G"]
        if G:
            iso = [g for g in G if g["isolated"]]
            for lbl, sub in (("all", G), ("isolated", iso)):
                if sub:
                    print(doc[:8], f"G {lbl} n={len(sub)}: gate pass raw {sum(g['raw']['gate'] for g in sub)} -> filled {sum(g['filled']['gate'] for g in sub)};"
                          f" centre error median raw {np.median([g['raw'].get('err_sp', np.nan) for g in sub]):.2f} -> filled {np.median([g['filled'].get('err_sp', np.nan) for g in sub]):.2f} sp")


if __name__ == "__main__":
    main()
