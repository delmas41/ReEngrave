#!/usr/bin/env python3
"""l288_compare: BASE vs ARM records (each from its own clean checkout, GATHER+ADJUDICATE only) for ROADMAP 2.88.

Heads are matched by glyph key and the box checked equal (a GATHER change would move boxes; this lane changes none). Prints the
transition table of the standing `Q.DURATION` verdict (outcome:reason, beats), the heads the arm DECIDED a half that base did not
(the restored population) with their readings, and every change that is NOT narrowed->decided-half (there must be none).

    python3 l288_compare.py --base base.json [base2.json] --arm arm.json [arm2.json] [--json changed.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

from l288_population import build  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402


def label(r):
    if r["outcome"] == "decided":
        return f'decided:{r["reason"]}:{r["beats"]}'
    if r["outcome"] == "narrowed":
        return f'narrowed:{r["reason"]}'
    return f'{r["outcome"]}:{r["reason"]}'


def load(paths):
    rows = {}
    for p in paths:
        for r in build(RD.load_run(p)):
            rows[r["key"]] = r
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", nargs="+", required=True)
    ap.add_argument("--arm", nargs="+", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    B, A = load(a.base), load(a.arm)
    both = sorted(set(B) & set(A))
    print(f"heads: base {len(B)} arm {len(A)} both {len(both)} (only base {len(set(B) - set(A))}, only arm {len(set(A) - set(B))})")
    moved = [k for k in both if B[k]["box_page"] and A[k]["box_page"] and
             max(abs(x - y) for x, y in zip(B[k]["box_page"], A[k]["box_page"])) > 1.0]
    print("box moved > 1px:", len(moved))
    changed = [k for k in both if label(B[k]) != label(A[k])]
    print("duration verdicts changed:", len(changed), "of", len(both))
    c = collections.Counter((label(B[k]), label(A[k])) for k in changed)
    for (b, x), n in c.most_common():
        print(f"  {n:4d}  {b}  ->  {x}")
    out = []
    for k in changed:
        b, x = B[k], A[k]
        out.append({"key": k, "page": b["page"], "base": label(b), "arm": label(x), "status": x["status"], "box_page": x["box_page"],
                    "h_sp": x["h_sp"], "w_sp": x["w_sp"], "ink": x["ink"], "tip": x["tip"], "side": x["side"]})
    if a.json:
        Path(a.json).write_text(json.dumps(out))
    bad = [o for o in out if not (o["base"].startswith("narrowed:head_fill_from_ink") and o["arm"].startswith("decided:hollow_head_bare_stem"))]
    print("changes other than narrowed head_fill -> decided half:", len(bad))
    for o in bad[:30]:
        print("   ", o["key"], o["base"], "->", o["arm"])


if __name__ == "__main__":
    main()
