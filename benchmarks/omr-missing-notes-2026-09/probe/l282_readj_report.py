#!/usr/bin/env python3
"""l282_readj_report: the three `l282_readj.py` arms (base / thin / full) of ONE record, side by side. ROADMAP 2.82.

  1. Head verdicts: base -> thin -> full, by (old -> new) with counts (GATHER+ADJUDICATE only).
  2. Ink refusals per (head, stroke) by reason, per arm.
  3. On Sean's page (`--tb`, the `l282_truthbeams.py --json` of this record): every stroke refused `one_stem`
     (by any head) in base, then in full -- split REAL BEAM (a truth beam box under it) / NOT A BEAM (what he boxed
     instead), and the same for `too_thin`: "truth beams refused one_stem before -> after, and non-beams still refused".

    python3 l282_readj_report.py --prefix DIR/tag [--tb tb.json] [--page 0]
"""
import argparse
import collections
import json


def label_of(r):
    return "REAL BEAM" if r["is_beam"] else "not a beam: " + r["label"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--tb", default=None)
    a = ap.parse_args()
    arms = {m: json.load(open(f"{a.prefix}-{m}.json")) for m in ("base", "thin", "full")}
    print("== 1. head duration verdicts ==")
    for lo, hi in (("base", "thin"), ("thin", "full"), ("base", "full")):
        moves = collections.Counter()
        for k, v in arms[lo]["verdicts"].items():
            w = arms[hi]["verdicts"].get(k)
            if w != v:
                moves[(" ".join(str(x) for x in (v[0], v[1] if v[0] == "decided" else v[2], v[3])),
                       " ".join(str(x) for x in (w[0], w[1] if w[0] == "decided" else w[2], w[3])))] += 1
        print(f"   {lo} -> {hi}: {sum(moves.values())} heads changed")
        for (o, n), c in sorted(moves.items(), key=lambda t: -t[1]):
            print(f"      {c:4d}  {o}  ->  {n}")
    print("\n== 2. ink refusals per (head, stroke) by reason ==")
    for m, d in arms.items():
        print(f"   {m:5s}", dict(collections.Counter(d["reasons"].values())))
    if a.tb:
        rows = {r["id"]: r for r in json.load(open(a.tb))["rows"]}
        print("\n== 3. on Sean's page: strokes refused (by any head) -- real beams vs not ==")
        for reason in ("one_stem", "no_stem_at_ends", "too_thin", "beyond_core"):
            for m in ("base", "full"):
                per = collections.defaultdict(set)
                for key, why in arms[m]["reasons"].items():
                    if why != reason:
                        continue
                    sid = key.split("|", 1)[1]
                    if sid in rows:
                        per[sid].add(key.split("|", 1)[0])
                c = collections.Counter(label_of(rows[s]) for s in per)
                print(f"   {reason:16s} {m:5s} strokes refused: {sum(c.values()):3d}  " + "; ".join(f"{k}: {v}" for k, v in sorted(c.items())))
        for m in ("base", "full"):
            ids = sorted({k.split("|", 1)[1] for k, w in arms[m]["reasons"].items() if w == "one_stem"} & set(rows))
            print(f"\n   one_stem [{m}] strokes on the page:")
            for s in ids:
                r = rows[s]
                print(f"      {s} {r['reader'][:3]} ratio {r['ratio']} ends {r.get('ends')} {r['w_px']:.0f}x{r['h_px']:.0f}px -> {label_of(r)}")


if __name__ == "__main__":
    main()
