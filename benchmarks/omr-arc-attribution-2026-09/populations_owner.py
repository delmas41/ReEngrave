"""The two-sided population: an arc's clearance against its OWN staff's heads,
and against the best rival staff's.

Split by whether the part's TRUTH carries any arc at all. A part with zero
slurs and zero ties in the truth is one where every arc we predicted is
spurious by construction — the only per-arc label available without hand
reading, and it is exactly the Brahms Timpani.

Only arcs covering >= 2 noteheads in their own staff are counted: an arc
covering fewer never becomes a slur, so it is not what a drop rule is for.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from probe_owner import rows  # noqa: E402
from populations import WORKS, truth_arc_counts  # noqa: E402

FIX_DEFAULT = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
               "sad-austin-7e16e7/benchmarks/omr-orchestral-e2e/fixtures")


def gather(fix):
    fix = Path(fix)
    out = []
    for w in WORKS:
        j, t = fix / f"{w}.omr.json", fix / f"{w}.musicxml"
        if not (j.exists() and t.exists()):
            continue
        tc = truth_arc_counts(t)
        for r in rows(j):
            if r["ncov"] < 2 or r["own"] is None:
                continue
            silent = r["staff"] < len(tc) and tc[r["staff"]] == 0
            out.append((w, silent, r))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=FIX_DEFAULT)
    ap.add_argument("--margins", default="0.5,0.75,1.0,1.25,1.5,2.0")
    ap.add_argument("--near", default="0.25,0.5,0.75,1.0")
    args = ap.parse_args()
    data = gather(args.fixtures)
    n_sil = sum(1 for _, s, _ in data if s)
    print(f"arcs covering >=2 heads: {len(data)}  "
          f"(silent-part {n_sil}, arc-bearing {len(data) - n_sil})")

    print("\n-- own clearance, spaces --")
    edges = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    for lo, hi in zip([0.0] + edges, edges + [99.0]):
        a = sum(1 for _, s, r in data if s and lo <= r["own"] < hi)
        b = sum(1 for _, s, r in data if not s and lo <= r["own"] < hi)
        print(f"  [{lo:4.2f},{hi:5.2f})  silent {a:4d}   arc-bearing {b:4d}")

    print("\n-- drop rule sweep: own - best >= margin AND best <= near --")
    print(f"{'margin':>7} {'near':>5} {'drop@silent':>12} {'drop@bearing':>13}")
    for margin in [float(x) for x in args.margins.split(",")]:
        for near in [float(x) for x in args.near.split(",")]:
            a = b = 0
            for _, s, r in data:
                best = r["best"]
                if best is None:
                    continue
                if best[0] <= near and r["own"] - best[0] >= margin:
                    if s:
                        a += 1
                    else:
                        b += 1
            print(f"{margin:7.2f} {near:5.2f} {a:12d} {b:13d}")


if __name__ == "__main__":
    main()
