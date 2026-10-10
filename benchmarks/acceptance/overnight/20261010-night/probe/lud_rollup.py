#!/usr/bin/env python3
"""lud_rollup: tonight's narrowing reason -> the guard input that newly fired ->
the item that introduced that guard, with counts. Reads only the per-note CSVs
lud_attrib.py wrote.

The item for a guard input is a `git log -S` fact (see UNDECIDED.md):
  ink refused too_thin / not_straight / one_stem   56fa83ab (2.74; thresholds 4fc81f65; guard 0f880dde)
  ink refused through_heads                        34972ddc (2.77, "rhythm leftovers")
  ink refused no_stem_at_ends                      0d08e10c (2.77 review), refined 3a5b5af4 (2.77b)
  stem side None -> up/down (ruler fallback)       3a5b5af4 (2.77b)
  decided-arc strokes changed                      the arc-kind decision changed (2.75 tie/slur rule family)
  hooks_counted                                    6c14783e (2.69)
  hollow_head_bare_stem                            a116c4ee (2.70)
"""
import collections
import csv
import re
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "undecided"
SIMPLE74 = {"too_thin", "not_straight", "one_stem"}
LEFT77 = {"through_heads", "no_stem_at_ends"}


def tags(r):
    toks = set(filter(None, r["ink_refusal_why"].split("/")))
    wc = r["what_changed"]
    t = set()
    if toks & SIMPLE74:
        t.add("2.74 (ink: too thin / bowed / one stem)")
    if toks & LEFT77:
        t.add("2.77/2.77b (ink: through the heads / no stem at the ends)")
    if "stem side None->" in wc:
        t.add("2.77b (stem side read by the ruler)")
    if "decided-arc strokes" in wc:
        t.add("arc decision changed (decided-arc strokes differ)")
    return t


def main():
    out = []
    P = out.append
    for doc in ("brahms1-breitkopf", "beethoven5-litolff"):
        rows = list(csv.DictReader(open(D / f"changed-notes-{doc}.csv")))
        k2n = [r for r in rows if r["kind"] == "kept_to_narrowed"]
        n2k = [r for r in rows if r["kind"] == "narrowed_to_kept"]
        P(f"=== {doc}: {len(k2n)} notes kept -> narrowed")
        by_reason_tags = collections.defaultdict(collections.Counter)
        marg = collections.Counter()
        for r in k2n:
            t = tags(r)
            key = " + ".join(sorted(t)) if t else "no guard input differs between the nights"
            by_reason_tags[r["tonight_reason"]][key] += 1
            for x in t:
                marg[x] += 1
        for reason, c in sorted(by_reason_tags.items(), key=lambda kv: -sum(kv[1].values())):
            P(f"  reason `{reason}`: {sum(c.values())}")
            for key, n in c.most_common():
                P(f"      {n:5d}  {key}")
        P("  marginal: notes carrying each guard input (a note can carry several)")
        for x, n in marg.most_common():
            P(f"      {n:5d}  {x}")
        P(f"\n=== {doc}: {len(n2k)} notes narrowed -> kept")
        c2 = collections.Counter()
        for r in n2k:
            m = re.match(r"^tonight decided by `(\w+)`; last night `(\w+)`", r["what_changed"])
            now, last = (m.group(1), m.group(2)) if m else (r["tonight_reason"], "?")
            t = tags(r)
            if now == "hooks_counted":
                item = "2.69 (hooks are counted at the stem tip)"
            elif now == "hollow_head_bare_stem":
                item = "2.70 (hollow head, bare stem = half)"
            elif t:
                item = " + ".join(sorted(t))
            else:
                item = "no guard input differs between the nights"
            c2[(last, now, item)] += 1
        for (last, now, item), n in c2.most_common():
            P(f"      {n:5d}  last night `{last}` -> tonight `{now}`  via {item}")
        P("")
    txt = "\n".join(out)
    (D / "rollup.txt").write_text(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
