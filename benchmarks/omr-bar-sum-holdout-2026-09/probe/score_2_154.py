"""ROADMAP 2.154 -- record Sean's answers to out/print/2.154-review and score base / arm a / arm b against them.

Writes answers.json in 2.153's shape (verbatim + per tile: n, doc, glyph, role, sean, base, arm_a, arm_b and each one's verdict)
and adds `tiles` (n, doc, glyph) to manifest.json so the judged index carries the subject. Verdicts: decided == Sean -> right;
decided != Sean -> wrong; narrowed whose candidates hold Sean's value -> narrowed-holding, else narrowed-not.
A tile is a BARE STEM when the narrowing the bar acted on was a bare stem's {unbeamed, one beam}: base decider
`infer:collapse_bare_stem_by_bar`, or an arm's standing reason `beam_discounted_uncertain` / the arc-ink collapse of one.
usage: score_2_154.py
"""
import collections
import json
import re
import sys

sys.path.insert(0, ".")
from tools.omr.staged.judged import parse_answer  # noqa: E402

VERBATIM = ("1.4 2.dot4 3.8 4.4 5.16 6.dot 4 7.8  8.8 9.4. 10.4 11.8 12.2 13.dot4 14.8 15.dot 4 16.dot4 17. dot 4 18.4 "
            "19.4 20.4 21.2 22.4 23.4")
DIR = "out/print/2.154-review/"
key = json.load(open("out/2.154/tiles-key.json"))
parts = re.findall(r"(\d+)\.\s*(dot\s*\d+|\d+)\.?", VERBATIM)
sean = {int(n): re.sub(r"dot\s*", "dot ", v) for n, v in parts}
assert sorted(sean) == list(range(1, len(key) + 1)), sorted(sean)
BARE = ("beam_discounted_uncertain", "refused_strokes_are_slurs_or_too_thin_for_a_beam")


def verdict(v, want):
    if v["outcome"] == "decided":
        return "right" if abs((v["written"] or -9) - want) < 1e-6 else "wrong"
    if v["outcome"] == "narrowed":
        cands = v["cands"] or []     # `written` already includes the dot
        return "narrowed-holding" if any(abs(c - want) < 1e-6 for c in cands) else "narrowed-not"
    return v["outcome"]


rows, tally = [], collections.Counter()
for k in key:
    word = sean[k["n"]]
    kind, want = parse_answer(word)
    assert kind == "duration", (k["n"], word)
    bare = (k["base"]["decider"] == "infer:collapse_bare_stem_by_bar"
            or k["arm_a"]["reason"] in BARE or k["arm_b"]["reason"] in BARE)
    group = k["role"] + ("/bare_stem" if bare and k["role"] == "bar_pick" else "")
    r = dict(n=k["n"], doc=k["doc"], glyph=k["glyph"], role=k["role"], bare_stem=bare, sean=word,
             base=k["base"], arm_a=k["arm_a"], arm_b=k["arm_b"],
             base_verdict=verdict(k["base"], want), arm_a_verdict=verdict(k["arm_a"], want),
             arm_b_verdict=verdict(k["arm_b"], want))
    rows.append(r)
    tally[(group, r["base_verdict"], r["arm_a_verdict"], r["arm_b_verdict"])] += 1
json.dump(dict(answered="2026-10-16", verbatim=VERBATIM,
               question="What is the written value of the note in the blue box (4, dotted 4, 8 ...)?", tiles=rows),
          open(DIR + "answers.json", "w"), indent=1)
man = json.load(open(DIR + "manifest.json"))
man["tiles"] = [dict(n=k["n"], doc=k["doc"], glyph=k["glyph"]) for k in key]
json.dump(man, open(DIR + "manifest.json", "w"), indent=1)


def val(v):
    if v["outcome"] == "decided":
        return str(v["written"])
    return "narrowed %s" % v["cands"]


for r in rows:
    print("%2d %-7s %-24s sean=%-6s base=%-12s %-17s a=%-20s %-17s b=%-20s %s" % (
        r["n"], r["doc"], r["role"] + ("*" if r["bare_stem"] else ""), r["sean"], val(r["base"]), r["base_verdict"],
        val(r["arm_a"]), r["arm_a_verdict"], val(r["arm_b"]), r["arm_b_verdict"]))
print()
for k, n in sorted(tally.items()):
    print("%2d  %-24s base=%-6s a=%-17s b=%s" % ((n,) + k))
