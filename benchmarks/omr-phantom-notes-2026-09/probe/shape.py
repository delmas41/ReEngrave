"""A NOTEHEAD IS AN OVAL, A WHOLE REST IS A BAR OF INK -- measured on this
document's OWN ink, both sides.

The positive reference is the thing that makes this more than an assertion:
the same page holds hundreds of whole rests the detector DID call `restWhole`,
so the two populations can be measured against each other in the same units,
on the same plate, at the same DPI. Without that side, "aspect 2.0 is
rest-shaped" is a number from another document's label audit.

⚠️ SPACING IS PER STAFF and every figure is in staff spaces. ⚠️ The comparison
is against `restWhole` AND `restHalf`, because they are the same rectangle
sitting on the other side of a line -- a shape rule cannot tell them apart and
must not pretend to.

    python3 .../shape.py --record R.json [--lone lone.json]
"""
from __future__ import annotations

import argparse
import collections
import json


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--lone", help="lone.py's rows, to place the suspects")
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]
    spacing = {}
    for o in rec["observations"]:
        if o["quantity"] == "staff_spacing":
            b = o["subject"].split("/")
            spacing[(int(b[1]), int(b[2]), int(b[3]))] = float(o["value"])

    conf = {o["subject"]: o["score"] for o in rec["observations"]
            if o["quantity"] == "glyph_conf"}
    groups = collections.defaultdict(list)
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        pg = (o.get("detail") or {}).get("bbox_page_px")
        if not pg:
            continue
        b = o["subject"].split("/")
        sp = spacing.get((int(b[1]), int(b[2]), int(b[3])))
        if not sp:
            continue
        cls = o["value"][0]
        w, h = (pg[2] - pg[0]) / sp, (pg[3] - pg[1]) / sp
        if h <= 0:
            continue
        fam = ("notehead" if cls.startswith("notehead")
               else "restWhole/Half" if cls in ("restWhole", "restHalf")
               else "rest*" if cls.startswith("rest")
               else None)
        if fam:
            groups[fam].append({"cls": cls, "w": w, "h": h, "a": w / h,
                                "conf": conf.get(o["subject"])})

    print("family                    n     height(sp)          aspect(w/h)")
    for fam in ("notehead", "restWhole/Half", "rest*"):
        g = groups.get(fam, [])
        if not g:
            print(f"{fam:<22} 0   -- EMPTY, check the join")
            continue
        hs = [r["h"] for r in g]
        asp = [r["a"] for r in g]
        print(f"{fam:<22} {len(g):<5} "
              f"med {pct(hs,.5):.2f} [{pct(hs,.05):.2f}-{pct(hs,.95):.2f}]   "
              f"med {pct(asp,.5):.2f} [{pct(asp,.05):.2f}-{pct(asp,.95):.2f}]")
    print()

    nh = groups["notehead"]
    rw = groups["restWhole/Half"]
    print("=== the joint test: SQUAT (low height) AND WIDE (high aspect) ===")
    for hcut in (0.85, 0.90, 0.95, 1.00):
        for acut in (1.6, 1.8, 2.0):
            fn = sum(1 for r in nh if r["h"] < hcut and r["a"] > acut)
            fr = sum(1 for r in rw if r["h"] < hcut and r["a"] > acut)
            print(f"  h < {hcut:.2f} and aspect > {acut:.1f}   "
                  f"noteheads caught {fn:>4}/{len(nh)} ({fn/len(nh):.3%})   "
                  f"whole/half rests caught {fr:>4}/{len(rw)} ({fr/len(rw):.1%})")
    print()

    if a.lone:
        rows = [r for r in json.load(open(a.lone)) if "aspect" in r]
        print(f"=== the {len(rows)} lone notes of underfull bars, in these units ===")
        hit = [r for r in rows if r["h_sp"] < 0.95 and r["aspect"] > 1.8]
        print(f"  squat AND wide (rest-shaped): {len(hit)}")
        for r in sorted(hit, key=lambda r: -r["aspect"]):
            print(f"    {r['part']:>4} m{r['measure']:<4} p{r['page']}s{r['system']}"
                  f"st{r['staff']}c{r['cell']:<3} {r['exported'][0]:<4} "
                  f"h={r['h_sp']:.2f} a={r['aspect']:.2f} conf={r['conf']:.2f} "
                  f"step={r['step_from_bottom_line']}")


if __name__ == "__main__":
    main()
