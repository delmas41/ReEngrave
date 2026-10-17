"""ROADMAP 2.154 -- re-score Sean's 23 answered tiles (out/print/2.154-review/answers.json) against the CURRENT replayed arm
records (out/2.154/rr_<doc>.<arm>.record.json), after the bare-stem confirm exemption. Base is unchanged by the flag.
usage: rescore_2_154.py
"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged.judged import parse_answer  # noqa: E402

ans = json.load(open("out/print/2.154-review/answers.json"))["tiles"]
cache = {}


def live(doc, arm):
    if (doc, arm) not in cache:
        ch = collections.defaultdict(list)
        for v in json.load(open("out/2.154/rr_%s.%s.record.json" % (doc, arm)))["record"]["verdicts"]:
            if v["quantity"] == "duration":
                ch[v["subject"]].append(v)
        out = {}
        for g, c in ch.items():
            sup = {x.get("supersedes") for x in c if x.get("supersedes")}
            out[g] = ([x for x in c if x["id"] not in sup] or c)[-1]
        cache[(doc, arm)] = out
    return cache[(doc, arm)]


def verdict(v, want):
    val = v["value"] if isinstance(v["value"], dict) else {}
    if v["outcome"] == "decided":
        return "right" if abs((val.get("written") or -9) - want) < 1e-6 else "wrong", val.get("written")
    if v["outcome"] == "narrowed":
        c = sorted({(x.get("value") or {}).get("written") for x in v.get("candidates") or ()} - {None})
        return ("narrowed-holding" if any(abs(x - want) < 1e-6 for x in c) else "narrowed-not"), c
    return v["outcome"], None


tally = collections.Counter()
for t in ans:
    want = parse_answer(t["sean"])[1]
    group = t["role"] + ("/bare_stem" if t["bare_stem"] and t["role"] == "bar_pick" else "")
    res = {arm: verdict(live(t["doc"], arm)[t["glyph"]], want) for arm in ("base", "a", "b")}
    assert res["base"][0] == t["base_verdict"], (t["n"], res["base"], t["base_verdict"])
    tally[(group, res["base"][0], res["a"][0], res["b"][0])] += 1
    print("%2d %-24s sean=%-6s base=%-6s %-6s a=%-12s %-17s b=%-12s %s" % (
        t["n"], group, t["sean"], res["base"][1], res["base"][0], res["a"][1], res["a"][0], res["b"][1], res["b"][0]))
print()
for k, n in sorted(tally.items()):
    print("%2d  %-24s base=%-6s a=%-17s b=%s" % ((n,) + k))
