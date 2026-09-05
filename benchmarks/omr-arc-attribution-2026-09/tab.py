"""Tabulate ops-<tag>/ directories: per-work musicdiff COST (the edit count the
benchmark reports), side by side, plus the category totals."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

WORKS = ["beethoven-sym3-mvt1", "beethoven-sym5-mvt1", "brahms-sym1-mvt1",
         "brahms-sym4-mvt1", "bruckner-sym5-mvt1", "dvorak-sym9-mvt4",
         "mahler-sym5-mvt1", "mozart-sym40-mvt1", "mozart-sym41-mvt1",
         "tchaikovsky-sym4-mvt2", "tchaikovsky-sym6-mvt2"]


def load(tag, root):
    out = {}
    for w in WORKS:
        p = Path(root) / f"ops-{tag}" / f"{w}.json"
        if p.exists():
            d = json.loads(p.read_text())
            out[w] = (d["total_cost"], Counter(d.get("cost_by_category", {})))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--root", default=str(Path(__file__).parent))
    ap.add_argument("--cat", default=None)
    args = ap.parse_args()
    tabs = [load(t, args.root) for t in args.tags]
    print(f"{'work':26s}" + "".join(f"{t:>16}" for t in args.tags))
    tot = [0] * len(tabs)
    for w in WORKS:
        cells = ""
        for i, tb in enumerate(tabs):
            if w in tb:
                v = tb[w][1].get(args.cat, 0) if args.cat else tb[w][0]
                tot[i] += v
                cells += f"{v:>16d}"
            else:
                cells += f"{'-':>16}"
        print(f"{w:26s}{cells}")
    print(f"{'POOLED':26s}" + "".join(f"{v:>16d}" for v in tot))
    if not args.cat:
        cats = set()
        for tb in tabs:
            for _, c in tb.values():
                cats |= set(c)
        print()
        for cat in sorted(cats):
            print(f"{cat:26s}" + "".join(
                f"{sum(c.get(cat, 0) for _, c in tb.values()):>16d}" for tb in tabs))


if __name__ == "__main__":
    main()
