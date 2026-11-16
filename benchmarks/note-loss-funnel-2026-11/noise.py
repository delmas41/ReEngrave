"""ROADMAP 2.311 -- THE NOISE FLOOR: two gathers of the same pages by the same tree, written notes compared by place.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/noise.py A.facts.json B.facts.json \
        --pages 0,4 --unit 32 [--json OUT]

A written note (or rest) of run A pairs with one of run B on the same page, same kind, centres within half a staff space
(greedy, nearest first). Unpaired = written in one run only; the other run's fate for the glyph box at that place (the
exporter's own refusal name) says why. Paired notes that differ are counted by what differs (type / dots / pitch / blue).
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from tools.omr.staged.judged import boxes_overlap


def hosts(f: dict, pages: set) -> list:
    return [h for h in f["written"] if h["page"] in pages]


def pair(a: list, b: list, tol: float) -> tuple:
    cand = []
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            if x["page"] == y["page"] and x["kind"] == y["kind"]:
                d = abs(x["cx"] - y["cx"]) + abs(x["cy"] - y["cy"])
                if d <= tol:
                    cand.append((d, i, j))
    ta, tb, pairs = set(), set(), []
    for d, i, j in sorted(cand):
        if i in ta or j in tb:
            continue
        ta.add(i)
        tb.add(j)
        pairs.append((i, j))
    return pairs, [i for i in range(len(a)) if i not in ta], [j for j in range(len(b)) if j not in tb]


def fate_at(f: dict, h: dict) -> str:
    gl = [g for g in f["glyphs"].values() if g["page"] == h["page"] and (g["head"] or g["rest"])
          and boxes_overlap(g["box"], h["box"])[0]]
    if not gl:
        return "no box at this place"
    fates = [g["fate"] or "no_fate" for g in gl]
    for want in fates:
        if want not in ("written", "written_relocated"):
            return want
    return "written (moved beyond the pairing tolerance, or paired to another note)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--pages", required=True)
    ap.add_argument("--unit", type=float, required=True)
    ap.add_argument("--json")
    ar = ap.parse_args()
    pages = {int(x) for x in ar.pages.split(",")}
    fa, fb = json.load(open(ar.a)), json.load(open(ar.b))
    a, b = hosts(fa, pages), hosts(fb, pages)
    pairs, only_a, only_b = pair(a, b, ar.unit / 2)
    diff = collections.Counter()
    ex = collections.defaultdict(list)
    for i, j in pairs:
        x, y = a[i], b[j]
        for k in ("type", "pitch", "blue"):
            if x[k] != y[k]:
                diff[k] += 1
                ex[k].append((x["rg"], x[k], y[k]))
        if len((x.get("sub") or {}).get("dot") or []) != len((y.get("sub") or {}).get("dot") or []):
            diff["dots"] += 1
    why_a = collections.Counter(fate_at(fb, a[i]) for i in only_a)
    why_b = collections.Counter(fate_at(fa, b[j]) for j in only_b)
    print("pages %s: written A %d, B %d; paired %d; A only %d; B only %d" % (sorted(pages), len(a), len(b), len(pairs), len(only_a), len(only_b)))
    print("  paired but different: %s" % dict(diff))
    print("  written in A only -- B's fate there: %s" % dict(why_a.most_common()))
    print("  written in B only -- A's fate there: %s" % dict(why_b.most_common()))
    ia, ib = fa.get("provenance"), fb.get("provenance")
    if ar.json:
        Path(ar.json).write_text(json.dumps(dict(pairs=len(pairs), only_a=[a[i] for i in only_a], only_b=[b[j] for j in only_b],
                                                 diff=dict(diff), examples={k: v[:20] for k, v in ex.items()},
                                                 why_a=dict(why_a), why_b=dict(why_b)), default=str, indent=0))


if __name__ == "__main__":
    main()
