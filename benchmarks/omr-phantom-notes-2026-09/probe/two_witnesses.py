"""SHAPE x POSITION, over every notehead and every detected whole rest.

The repo's rule for a veto is that one signal is never enough
(`_drop_unladdered_noteheads`: "neither signal sufficient alone"). Here the two
are INDEPENDENT of each other in the way that matters -- one is about the ink's
outline, the other about where an ENGRAVER is obliged to put it -- so agreeing
is evidence and disagreeing is a refusal to decide.

  SHAPE     squat and wide: a bar of ink, not an oval.
  POSITION  a whole rest hangs UNDER THE SECOND LINE FROM THE TOP. With the
            bottom line 0 and one step per half space, its body spans step 6
            down to step 5, centre ~5.5. A half rest sits ON the middle line,
            step 4 up to 5, centre ~4.5. Both are fixed by convention and
            neither moves with the clef, the key or the music.

⚠️ THE POSITIVE REFERENCE IS THE DOCUMENT'S OWN CORRECTLY-DETECTED WHOLE RESTS.
If they do not concentrate at the step the convention names, the convention is
not visible in this reading and the whole rule is void -- so that distribution
is printed FIRST, before any claim about noteheads.

    python3 .../two_witnesses.py --record R.json
"""
from __future__ import annotations

import argparse
import collections
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--h-max", type=float, default=0.85)
    ap.add_argument("--aspect-min", type=float, default=1.8)
    ap.add_argument("--tol", type=float, default=1.0,
                    help="steps either side of the whole rest's own 5.5")
    ap.add_argument("--json")
    a = ap.parse_args()

    rec = json.load(open(a.record))["record"]
    spacing, lines = {}, {}
    for o in rec["observations"]:
        if o["subject"].startswith("staff/"):
            k = tuple(int(x) for x in o["subject"].split("/")[1:4])
            if o["quantity"] == "staff_spacing":
                spacing[k] = float(o["value"])
            elif o["quantity"] == "staff_lines":
                lines[k] = o["value"]
    conf = {o["subject"]: o["score"] for o in rec["observations"]
            if o["quantity"] == "glyph_conf"}

    rows = []
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
               else "restWhole" if cls == "restWhole"
               else "restHalf" if cls == "restHalf" else None)
        if not fam:
            continue
        w, h = (pg[2] - pg[0]) / sp, (pg[3] - pg[1]) / sp
        if h <= 0:
            continue
        cy = (pg[1] + pg[3]) / 2.0
        step = (max(ly) - cy) / (sp / 2.0)
        rows.append({"subject": o["subject"], "fam": fam, "cls": cls,
                     "page": k[0], "system": k[1], "staff": k[2],
                     "cell": int(b[4]), "w": w, "h": h, "a": w / h,
                     "step": step, "conf": conf.get(o["subject"])})

    print(f"rows with box + spacing + staff lines   {len(rows)}")
    fams = collections.Counter(r["fam"] for r in rows)
    print(f"  {dict(fams)}")
    if not fams.get("restWhole"):
        raise SystemExit("no restWhole -- dead join, do not read anything below")
    print()

    # ---- POSITIVE REFERENCE: where do the REAL whole rests sit? ----
    print("=== the document's own detected whole rests, by staff step ===")
    band = collections.Counter()
    for r in rows:
        if r["fam"] != "restWhole":
            continue
        band[round(r["step"] * 2) / 2] += 1
    rw = [r for r in rows if r["fam"] == "restWhole"]
    inband = [r for r in rw if abs(r["step"] - 5.5) <= a.tol]
    for k, v in sorted(band.items()):
        mark = "  <-- convention" if abs(k - 5.5) <= a.tol else ""
        print(f"  step {k:>6}   {v}{mark}")
    print(f"  within {a.tol} steps of 5.5: {len(inband)} of {len(rw)} "
          f"({len(inband)/len(rw):.1%})")
    print()

    nh = [r for r in rows if r["fam"] == "notehead"]
    print(f"=== noteheads, {len(nh)} ===")
    shape = [r for r in nh if r["h"] < a.h_max and r["a"] > a.aspect_min]
    print(f"  SHAPE alone   (h<{a.h_max}, aspect>{a.aspect_min})   {len(shape)}"
          f"  ({len(shape)/len(nh):.2%})")
    posn = [r for r in nh if abs(r["step"] - 5.5) <= a.tol]
    print(f"  POSITION alone (|step-5.5| <= {a.tol})            {len(posn)}"
          f"  ({len(posn)/len(nh):.2%})")
    both = [r for r in shape if abs(r["step"] - 5.5) <= a.tol]
    print(f"  BOTH                                          {len(both)}"
          f"  ({len(both)/len(nh):.2%})")
    print()
    print("  ⚠️ POSITION ALONE is nearly uninformative: the whole-rest band is "
          "\n     where C5/D5 live in treble, which is ordinary music. It is "
          "\n     only a witness BESIDE the shape, never instead of it.")
    print()
    print("  the BOTH population, by class and confidence:")
    print(f"    {dict(collections.Counter(r['cls'] for r in both))}")
    cs = sorted(r["conf"] for r in both if r["conf"])
    if cs:
        print(f"    conf median {cs[len(cs)//2]:.3f}  [{cs[0]:.3f}..{cs[-1]:.3f}]")
    allc = sorted(r["conf"] for r in nh if r["conf"])
    print(f"    all noteheads conf median {allc[len(allc)//2]:.3f}")
    print()
    print("  how many of those cells ALSO carry a detected rest of any kind:")
    restcells = {(r["page"], r["system"], r["staff"], r["cell"])
                 for r in rows if r["fam"] != "notehead"}
    n_with = sum(1 for r in both
                 if (r["page"], r["system"], r["staff"], r["cell"]) in restcells)
    print(f"    {n_with} of {len(both)}")

    if a.json:
        json.dump(both, open(a.json, "w"), indent=1)
        print(f"\nwrote {len(both)} suspects -> {a.json}")


if __name__ == "__main__":
    main()
