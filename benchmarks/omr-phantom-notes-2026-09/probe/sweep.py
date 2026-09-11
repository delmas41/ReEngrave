"""THE THREE CONSTANTS, swept -- is each on a PLATEAU or on a slope?

⚠️ A constant read off a gap should be flat around its value; one that is
tuned moves the answer as you move it. This prints, for each of the three, the
count the joint rule catches and -- the number that matters more -- how many
of the document's OWN correctly-detected whole rests the same cut would keep,
which is the recall side the catch count cannot show.

    python3 .../sweep.py --record R.json
"""
from __future__ import annotations

import argparse
import json


def rows_of(path):
    rec = json.load(open(path))["record"]
    spacing, lines = {}, {}
    for o in rec["observations"]:
        if o["subject"].startswith("staff/"):
            k = tuple(int(x) for x in o["subject"].split("/")[1:4])
            if o["quantity"] == "staff_spacing":
                spacing[k] = float(o["value"])
            elif o["quantity"] == "staff_lines":
                lines[k] = o["value"]
    out = []
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        pg = (o.get("detail") or {}).get("bbox_page_px")
        if not pg:
            continue
        b = o["subject"].split("/")
        k = (int(b[1]), int(b[2]), int(b[3]))
        sp, ly = spacing.get(k), lines.get(k)
        if not sp or not ly:
            continue
        cls = o["value"][0]
        fam = ("notehead" if cls.startswith("notehead")
               else "rest" if cls in ("restWhole", "restHalf") else None)
        if not fam:
            continue
        w, h = (pg[2] - pg[0]) / sp, (pg[3] - pg[1]) / sp
        if h <= 0:
            continue
        out.append({"fam": fam, "h": h, "a": w / h,
                    "step": (max(ly) - (pg[1] + pg[3]) / 2.0) / (sp / 2.0)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    a = ap.parse_args()
    rows = rows_of(a.record)
    nh = [r for r in rows if r["fam"] == "notehead"]
    rs = [r for r in rows if r["fam"] == "rest"]
    print(f"noteheads {len(nh)}   detected whole/half rests {len(rs)}")
    if not rs:
        raise SystemExit("dead join")

    def catch(rr, hmax, amin, tol):
        return sum(1 for r in rr if r["h"] < hmax and r["a"] > amin
                   and abs(r["step"] - 5.5) <= tol)

    print("\nHEIGHT (aspect>1.8, tol 1.0)")
    for hmax in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.10):
        print(f"  h < {hmax:.2f}   noteheads flagged {catch(nh,hmax,1.8,1.0):>3}"
              f"   real rests kept {catch(rs,hmax,1.8,1.0):>3}/{len(rs)}")
    print("\nASPECT (h<0.85, tol 1.0)")
    for amin in (1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.2, 2.4):
        print(f"  a > {amin:.1f}    noteheads flagged {catch(nh,0.85,amin,1.0):>3}"
              f"   real rests kept {catch(rs,0.85,amin,1.0):>3}/{len(rs)}")
    print("\nPOSITION TOLERANCE, steps either side of 5.5 (h<0.85, a>1.8)")
    for tol in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0):
        print(f"  |step-5.5| <= {tol:<5} noteheads flagged "
              f"{catch(nh,0.85,1.8,tol):>3}   real rests kept "
              f"{catch(rs,0.85,1.8,tol):>3}/{len(rs)}")


if __name__ == "__main__":
    main()
