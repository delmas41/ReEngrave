"""Does each cut sit on a PLATEAU, or is it holding the answer up?

⚠️ A constant read off the population it is about to judge is a constant fitted
to it. Every cut here is first DERIVED from the document's own 395 detected
`restWhole` glyphs -- a population the rule never touches -- and this then asks
the only question that makes that honest: move it, and does the answer change?

A cut that sits on a plateau is a description of two separated populations. A
cut that changes the answer every step is a threshold, and a threshold read off
one document is a property of that document.

    python3 .../sweep.py --cache cache.json --truth truth.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def _k(s, n):
    return tuple(int(x) for x in s.split("/")[1:1 + n])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--truth", required=True)
    a = ap.parse_args()

    c = json.load(open(a.cache))
    box, cls, rest, lines, spacing = {}, {}, {}, {}, {}
    for o in c["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                box[s] = pb
        elif q == "notehead_class":
            cls[s] = o["value"]
        elif q == "rest":
            rest[s] = o["value"]
        elif q == "staff_lines":
            lines[_k(s, 3)] = o["value"]
        elif q == "staff_spacing":
            spacing[_k(s, 3)] = o["value"]

    def geom(sub):
        pb, k = box.get(sub), _k(sub, 3)
        ly, sp = lines.get(k), spacing.get(k)
        if not pb or not ly or not sp:
            return None
        h, w = (pb[3] - pb[1]) / sp, (pb[2] - pb[0]) / sp
        if h <= 0:
            return None
        return h, w / h, (max(ly) - (pb[1] + pb[3]) / 2.0) / (sp / 2.0)

    heads = {s: g for s in cls if s in box and (g := geom(s))}
    wr = {s: g for s in rest if s in box
          and str(rest[s]).lower().startswith("restwhole") and (g := geom(s))}
    print(f"POSITIVE CONTROL: {len(heads)} noteheads, {len(wr)} whole rests")
    if not heads or not wr:
        print("DEAD", file=sys.stderr)
        return 2
    truth = {t["subject"]: t["verdict"] for t in json.load(open(a.truth))}

    by_staff = collections.defaultdict(list)
    for s, g in wr.items():
        by_staff[_k(s, 3)].append((int(s.split("/")[4]), g[2]))

    def fires(hmax, amin, amax, slot_tol, nb_bars, nb_steps):
        out = []
        for s, (h, asp, step) in heads.items():
            if not (h <= hmax and amin <= asp <= amax):
                continue
            if abs(step - 5.5) <= slot_tol:
                out.append(s)
                continue
            cell = int(s.split("/")[4])
            for c2, st2 in by_staff.get(_k(s, 3), ()):
                if abs(c2 - cell) <= nb_bars and abs(st2 - step) <= nb_steps:
                    out.append(s)
                    break
        return out

    base = dict(hmax=0.84, amin=1.63, amax=3.09, slot_tol=1.0,
                nb_bars=2, nb_steps=1.5)
    b = set(fires(**base))
    print(f"\nBASE rule fires on {len(b)} of {len(heads)} noteheads "
          f"({100.0 * len(b) / len(heads):.1f}%)")
    n = collections.Counter(truth[s] for s in b if s in truth)
    print(f"  hand verdicts among them: {dict(n)}  "
          f"(a 'notehead' here would be a REAL NOTE DELETED)")

    for name, values in (("hmax", [0.70, 0.75, 0.80, 0.84, 0.90, 1.00, 1.10]),
                         ("amin", [1.20, 1.40, 1.63, 1.80, 2.00]),
                         ("amax", [2.40, 2.80, 3.09, 3.50, 4.50, 6.00]),
                         ("slot_tol", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]),
                         ("nb_bars", [1, 2, 3, 4, 8]),
                         ("nb_steps", [0.5, 1.0, 1.5, 2.0, 3.0])):
        print(f"\n  --- {name} ---")
        for v in values:
            kw = dict(base)
            kw[name] = v
            f = set(fires(**kw))
            nn = collections.Counter(truth[s] for s in f if s in truth)
            mark = "  <-- shipped" if v == base[name] else ""
            print(f"    {name}={v:<6} fires {len(f):>4}   "
                  f"vs base: +{len(f - b)} / -{len(b - f)}   "
                  f"adjudicated {dict(nn)}{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
