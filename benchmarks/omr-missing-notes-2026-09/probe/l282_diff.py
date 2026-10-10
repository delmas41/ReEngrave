#!/usr/bin/env python3
"""l282_diff: base -> arm, every note head's standing ADJUDICATE `Q.DURATION` verdict (GATHER+ADJUDICATE only,
CLAUDE.md §6b). Heads are matched by subject key (the GATHER boxes are identical across the two arms --
the control prints the share of heads whose box is the same on both sides); a verdict is summarised as
`decided <beats>` or `narrowed <reason> {candidate beats}`. Prints the change table (old -> new, by
count), the 2.81 population (base `beam_discounted_uncertain`) and what each became, and writes the
changed heads to JSON for the tiles.

    python3 l282_diff.py --base R0 --arm R1 [--json changed.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RO  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def beats(v):
    if not isinstance(v, dict):
        return None
    return v.get("beats")


def summ(v):
    if v is None:
        return ("none", None, None, None)
    o = v["outcome"]
    if o == "decided":
        return ("decided", beats(v.get("value")), None, v.get("reason"))
    if o == "narrowed":
        c = tuple(sorted({beats(x.get("value")) for x in (v.get("candidates") or []) if beats(x.get("value")) is not None}))
        return ("narrowed", None, c, v.get("reason"))
    return (o, None, None, v.get("reason"))


def label(s):
    k, b, c, r = s
    if k == "decided":
        return f"decided {b}"
    if k == "narrowed":
        return f"narrowed {r} {list(c)}"
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="a base record (loaded whole)")
    ap.add_argument("--base-summaries", default=None,
                    help="l282_overnight_verdicts.py output: the base's verdict summaries, no record")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    r1 = RO.load_run(a.arm)
    keys1 = {k for k, g in r1.glyphs.items() if str(g.cls or "").startswith("notehead")}
    if a.base:
        r0 = RO.load_run(a.base)
        keys0 = {k for k, g in r0.glyphs.items() if str(g.cls or "").startswith("notehead")}
        both = sorted(keys0 & keys1)
        same_box = sum(1 for k in both if r0.glyphs[k].box_page == r1.glyphs[k].box_page)
        base_sum = lambda k: summ(r0.standing(k, Q.DURATION, "ADJUDICATE"))   # noqa: E731
    else:
        sj = json.load(open(a.base_summaries))
        keys0 = set(sj)
        both = sorted(keys0 & keys1)
        same_box = len(both)
        base_sum = lambda k: tuple(tuple(x) if isinstance(x, list) else x for x in sj[k])   # noqa: E731
    print(f"heads: base {len(keys0)}, arm {len(keys1)}, in both {len(both)}; same box {same_box}")
    moves = collections.Counter()
    changed = []
    pop81_base = 0
    pop81_to = collections.Counter()
    for k in both:
        s0 = base_sum(k)
        s1 = summ(r1.standing(k, Q.DURATION, "ADJUDICATE"))
        if s0[3] == "beam_discounted_uncertain" and s0[0] == "narrowed":
            pop81_base += 1
            pop81_to[label(s1)] += 1
        if s0 == s1:
            continue
        moves[(label(s0), label(s1))] += 1
        g = r1.glyphs[k]
        changed.append({"key": k, "old": label(s0), "new": label(s1), "box": list(g.box_page) if g.box_page else None,
                        "cls": g.cls, "old_reason": s0[3], "new_reason": s1[3]})
    print(f"duration verdicts changed: {len(changed)} of {len(both)}")
    for (o, n), c in sorted(moves.items(), key=lambda t: -t[1]):
        print(f"   {c:4d}  {o}  ->  {n}")
    print(f"\nthe 2.81 population (base `beam_discounted_uncertain`): {pop81_base}")
    for lab, c in pop81_to.most_common():
        print(f"   {c:4d}  -> {lab}")
    if a.json:
        Path(a.json).write_text(json.dumps(changed, indent=1))


if __name__ == "__main__":
    main()
