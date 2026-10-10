#!/usr/bin/env python3
"""l282_stats: on Sean's page (Brahms 317803 pdf 0), the profile statistics of `l282_profile.py` for the
strokes `l282_truthbeams.py` labelled REAL BEAM / not a beam. ROADMAP 2.82. A reading probe.

    python3 l282_stats.py --tb tb.json --prof prof.json
"""
import argparse
import collections
import json


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * (len(v) - 1)))] if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tb", required=True)
    ap.add_argument("--prof", required=True)
    a = ap.parse_args()
    tb = json.load(open(a.tb))["rows"]
    prof = json.load(open(a.prof))
    keys = ("med_ratio", "win1", "win1.5", "win2", "run2", "run2_5")
    groups = collections.defaultdict(list)
    for r in tb:
        p = prof.get(r["id"])
        if not p:
            continue
        lab = "REAL BEAM" if r["is_beam"] else "not beam: " + r["label"]
        groups[lab].append((r, p))
    for lab, rows in sorted(groups.items()):
        print(f"== {lab}  (n={len(rows)})")
        for k in keys:
            v = [p[k] for _, p in rows]
            print(f"   {k:8s} min {min(v):6.2f}  p10 {pct(v, .1):6.2f}  med {pct(v, .5):6.2f}  p90 {pct(v, .9):6.2f}  max {max(v):6.2f}")
    print()
    print("== every stroke with median < 1.75 (the 2.74 cut) and its sustained span ==")
    for lab, rows in sorted(groups.items()):
        for r, p in sorted(rows, key=lambda t: -t[1]["win1.5"]):
            if p["med_ratio"] < 1.75 and (p["win1.5"] >= 1.75 or lab == "REAL BEAM"):
                print(f"   {lab:22s} {r['id']} {r['reader']:9s} med {p['med_ratio']:.2f} win1 {p['win1']:.2f} "
                      f"win1.5 {p['win1.5']:.2f} win2 {p['win2']:.2f} run2 {p['run2']:.2f}sp run2_5 {p['run2_5']:.2f}sp "
                      f"width {p['w_sp']:.1f}sp box {r['page_box']}")


if __name__ == "__main__":
    main()
