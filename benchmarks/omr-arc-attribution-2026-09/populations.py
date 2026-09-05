"""Pool every arc of the 11 works and split by whether its PART has arcs at all
in the truth.

A part whose truth carries zero slurs and zero ties is a part where every arc we
predicted is spurious by construction — no per-arc ground truth needed. That is
the only clean label available, and it is exactly the Timpani case. Parts whose
truth does carry arcs are the mixed pool: most of their arcs are real.
"""
from __future__ import annotations
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from probe_arc_dy import rows_for  # noqa: E402

WORKS = ["beethoven-sym3-mvt1", "beethoven-sym5-mvt1", "brahms-sym1-mvt1",
         "brahms-sym4-mvt1", "bruckner-sym5-mvt1", "dvorak-sym9-mvt4",
         "mahler-sym5-mvt1", "mozart-sym40-mvt1", "mozart-sym41-mvt1",
         "tchaikovsky-sym4-mvt2", "tchaikovsky-sym6-mvt2"]


def truth_arc_counts(path):
    root = ET.parse(path).getroot()
    out = []
    for part in root.iter("part"):
        s = sum(1 for x in part.iter("slur") if x.get("type") == "start")
        t = sum(1 for x in part.iter("tied") if x.get("type") == "start")
        out.append(s + t)
    return out


def hist(vals, edges):
    counts = [0] * (len(edges) + 1)
    for v in vals:
        for i, e in enumerate(edges):
            if v < e:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default="/Users/seanjohnson/Desktop/ReEngrave/"
                    ".claude/worktrees/sad-austin-7e16e7/benchmarks/"
                    "omr-orchestral-e2e/fixtures")
    args = ap.parse_args()
    fix = Path(args.fixtures)
    silent, voiced, nocov_silent, nocov_voiced = [], [], 0, 0
    for w in WORKS:
        jpath, tpath = fix / f"{w}.omr.json", fix / f"{w}.musicxml"
        if not jpath.exists() or not tpath.exists():
            print(f"skip {w}")
            continue
        tc = truth_arc_counts(tpath)
        for r in rows_for(jpath):
            # staff index within the system is the part ordinal for these
            # single-system fixtures; a work whose parts do not line up 1:1
            # simply lands its rows in the mixed pool.
            silent_part = r["staff"] < len(tc) and tc[r["staff"]] == 0
            if r["dy"] is None:
                if silent_part:
                    nocov_silent += 1
                else:
                    nocov_voiced += 1
                continue
            (silent if silent_part else voiced).append(r["dy"])
    edges = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]
    labels = ([f"<{edges[0]}"]
              + [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
              + [f">={edges[-1]}"])
    hs, hv = hist(silent, edges), hist(voiced, edges)
    print(f"{'dy (spaces)':>12} {'silent-part':>12} {'arc-bearing':>12}")
    for lab, a, b in zip(labels, hs, hv):
        print(f"{lab:>12} {a:12d} {b:12d}")
    print(f"{'TOTAL':>12} {len(silent):12d} {len(voiced):12d}")
    print(f"{'no coverage':>12} {nocov_silent:12d} {nocov_voiced:12d}")


if __name__ == "__main__":
    main()
