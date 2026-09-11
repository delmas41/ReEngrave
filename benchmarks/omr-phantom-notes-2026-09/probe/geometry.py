"""IS THE PHANTOM NOTE'S INK NOTEHEAD-SHAPED? Measured over every notehead.

Two candidate discriminators, measured together because the repo's record is
that ONE signal is never enough (`_drop_unladdered_noteheads`: "neither signal
sufficient alone"):

  SHAPE     a notehead is an oval about one staff space tall and a little
            wider; a whole rest is a filled RECTANGLE about half a space tall
            and a whole space wide, so it is flatter and squatter.
  POSITION  a whole rest HANGS FROM THE SECOND LINE FROM THE TOP -- an
            engraving convention, fixed whatever the clef or the music -- so
            its centre sits at a single staff position, ~5.5 counting the
            bottom line as 0.

⚠️ Everything here is in STAFF SPACES, never pixels: the staves of this
document differ in spacing and a pixel threshold would be a property of one
plate. Spacing comes from `Q.STAFF_SPACING`, per staff.

⚠️ It prints the FULL notehead population before any split, so a zero in a
sub-population can be told from a dead join.

    python3 .../geometry.py --record R.json --cands C.json
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics as st


def load(path):
    return json.load(open(path))["record"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--cands", help="candidate bars, to split the population")
    ap.add_argument("--locations", help="json of [page,system,staff,cell] to mark")
    ap.add_argument("--json", help="write per-notehead rows here")
    a = ap.parse_args()

    rec = load(a.record)

    spacing = {}          # (page,system,staff) -> float
    for o in rec["observations"]:
        if o["quantity"] == "staff_spacing":
            b = o["subject"].split("/")
            spacing[(int(b[1]), int(b[2]), int(b[3]))] = float(o["value"])

    pos = {o["subject"]: o["value"] for o in rec["observations"]
           if o["quantity"] == "notehead_staff_position"}
    nclass = {o["subject"]: o["value"] for o in rec["observations"]
              if o["quantity"] == "notehead_class"}
    conf = {o["subject"]: o["score"] for o in rec["observations"]
            if o["quantity"] == "glyph_conf"}

    rows = []
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        sub = o["subject"]
        if sub not in nclass:
            continue
        b = sub.split("/")
        key = (int(b[1]), int(b[2]), int(b[3]))
        sp = spacing.get(key)
        pg = (o.get("detail") or {}).get("bbox_page_px")
        if not sp or not pg:
            continue
        w = (pg[2] - pg[0]) / sp
        h = (pg[3] - pg[1]) / sp
        rows.append({
            "subject": sub, "cell": int(b[4]),
            "page": key[0], "system": key[1], "staff": key[2],
            "cls": o["value"][0], "conf": conf.get(sub),
            "w_sp": w, "h_sp": h, "aspect": (w / h) if h else None,
            "pos": pos.get(sub),
        })

    print(f"noteheads with box + spacing + class   {len(rows)}   "
          f"(record holds {len(nclass)} notehead_class rows)")
    if not rows:
        raise SystemExit("dead join")

    allh = [r["h_sp"] for r in rows]
    alla = [r["aspect"] for r in rows if r["aspect"]]
    print(f"  height  (staff spaces)  median {st.median(allh):.3f}  "
          f"p10 {sorted(allh)[len(allh)//10]:.3f}  "
          f"p90 {sorted(allh)[9*len(allh)//10]:.3f}")
    print(f"  aspect  (w/h)           median {st.median(alla):.3f}  "
          f"p10 {sorted(alla)[len(alla)//10]:.3f}  "
          f"p90 {sorted(alla)[9*len(alla)//10]:.3f}")
    print()

    if a.locations:
        marked = {tuple(x) for x in json.load(open(a.locations))}
        inside = [r for r in rows
                  if (r["page"], r["system"], r["staff"], r["cell"]) in marked]
        others = [r for r in rows
                  if (r["page"], r["system"], r["staff"], r["cell"]) not in marked]
        print(f"=== noteheads in CANDIDATE bars      {len(inside)} ===")
        print(f"=== noteheads everywhere else        {len(others)} ===")
        for name, grp in (("candidate", inside), ("other", others)):
            if not grp:
                continue
            h = sorted(r["h_sp"] for r in grp)
            asp = sorted(r["aspect"] for r in grp if r["aspect"])
            p = sorted(r["pos"] for r in grp if r["pos"] is not None)
            print(f"\n  {name}: n={len(grp)}")
            print(f"    height median {st.median(h):.3f}   "
                  f"[{h[0]:.3f} .. {h[-1]:.3f}]")
            print(f"    aspect median {st.median(asp):.3f}   "
                  f"[{asp[0]:.3f} .. {asp[-1]:.3f}]")
            print(f"    conf   median "
                  f"{st.median([r['conf'] for r in grp if r['conf']]):.3f}")
            if p:
                print(f"    pos    "
                      f"{dict(collections.Counter(round(x * 2) / 2 for x in p).most_common(8))}")
            print(f"    class  "
                  f"{dict(collections.Counter(r['cls'] for r in grp).most_common(6))}")

    if a.json:
        json.dump(rows, open(a.json, "w"))
        print(f"\nwrote {len(rows)} notehead rows -> {a.json}")


if __name__ == "__main__":
    main()
