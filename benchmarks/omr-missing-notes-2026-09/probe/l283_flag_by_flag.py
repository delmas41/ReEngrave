#!/usr/bin/env python3
"""l283_flag_by_flag: Sean's 34 flag boxes one by one, base -> arm. For each `flag*` box of his: the stem it hangs from, the black
heads on that stem, and the standing ADJUDICATE duration verdict of those heads in the base and the arm record (rows from
`l283_truth_score.py --json`, base and arm in one file). A flag is READ where at least one head on its stem acknowledges it (decided
at level >= 1, or narrowed with no level-0 candidate); RIGHT where one is decided at his level. A flag whose stem Sean did not box,
or whose heads are not black-and-judged, is listed apart and never counted. ROADMAP 2.83 probe.

    python3 l283_flag_by_flag.py --rows truth_rows.json
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_truth import Truth  # noqa: E402


def state(pair):
    """('right'|'narrowed+'|..., detail) -> 'right' | 'read' | 'not_read' | 'abstained' for a flagged head (level >= 1)."""
    cls, det = pair
    if cls == "right":
        return "right"
    if cls == "narrowed+":
        lv = det[1] if isinstance(det, (list, tuple)) and len(det) > 1 else []
        return "read" if lv and 0 not in lv else "not_read"
    if cls == "narrowed-":
        return "read" if det and 0 not in det[1] else "wrong"
    if cls == "wrong":
        return "wrong"
    return cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    a = ap.parse_args()
    rows = json.loads(Path(a.rows).read_text())
    by_truth = {r["truth"]: r for r in rows}
    T = Truth()
    from l283_flag_geometry import find_stem  # noqa: E402
    tab = collections.Counter()
    for f in sorted(T.flags, key=lambda i: (i.rect[1], i.rect[0])):
        found = find_stem(T, f)
        if not found:
            print(f"{f.id:7s} no stem box of his")
            tab[("no_stem_box", "")] += 1
            continue
        _k, stem, end = found
        heads = [h for h in T.heads if stem in T.stem_of(h)]
        judged = [by_truth[h.id] for h in heads if h.id in by_truth]
        if not judged:
            print(f"{f.id:7s} {f.cls:11s} stem {stem.id:6s} heads {len(heads)} none judged (not black / not in a fully labeled cell)")
            tab[("not_judged", "")] += 1
            continue
        bs = sorted((state(r["base"]) for r in judged))
        as_ = sorted((state(r["arm"]) for r in judged))
        rank = {"right": 0, "read": 1, "not_read": 2, "wrong": 3, "abstained": 4, "unmatched": 5}
        b_best = min(bs, key=lambda x: rank.get(x, 9))
        a_best = min(as_, key=lambda x: rank.get(x, 9))
        tips = sorted({str(r["arm_tip"]) for r in judged})
        print(f"{f.id:7s} {f.cls:11s} stem {stem.id:6s} heads {len(judged)}  base {bs}  ->  arm {as_}   arm tip: {tips}")
        tab[(b_best, a_best)] += 1
    print("\nper flag, best state of its heads, base -> arm:")
    for (b, a_), n in sorted(tab.items(), key=lambda kv: -kv[1]):
        print(f"  {b:12s} -> {a_:12s} {n}")


if __name__ == "__main__":
    main()
