"""ROADMAP 2.154 -- compare the replayed ARMS of one slice (mini records written by `replay_record_2_153.py`): every glyph whose
live duration differs from the base, by (base decider/reason -> arm outcome), plus Sean's answers where a judged tile or a 2.153
tile names the glyph. STAGED EVALUATE/INFER.
usage: arms_2_154.py DOC PREFIX OUT.json BASE ARM [ARM ...]
  PREFIX.<arm>.record.json are the mini records; DOC = litolff | brahms
"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged  # noqa: E402

DOC, PREFIX, OUT, BASE = sys.argv[1:5]
ARMS = sys.argv[5:]
KEY153 = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a033e6dfd0d2cc37a/out/2.153/tiles-key.json"
ANS153 = "out/print/2.153-review/answers.json"


def live(path):
    chains = collections.defaultdict(list)
    for v in json.load(open(path))["record"]["verdicts"]:
        if v["quantity"] == "duration" and v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        l = [x for x in ch if x["id"] not in sup] or ch
        out[g] = l[-1]
    return out


def show(v):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], beats=val.get("beats"), decider=v.get("decider"), reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


# Sean's answers on this doc: judged index (duration answers) + the 2.153 tiles
sean = {}
for r in json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]:
    if r["doc"] == DOC and r["answer_kind"] == "duration" and r["value"] is not None and r["subject_kind"] == "glyph":
        for s in r["subjects"] or [r["subject"]]:
            sean[s] = ("%s/%s" % (r["item"], r["tile"]), float(r["value"]))
try:
    ans = {t["n"]: t["sean"] for t in json.load(open(ANS153))["tiles"]}
    for k in json.load(open(KEY153)):
        if k["doc"] == DOC and k["n"] in ans:
            word = ans[k["n"]].strip().lower()
            val = {"8": 0.5, "4": 1.0, "dot 4": 1.5, "16": 0.25, "2": 2.0}.get(word)
            if val is not None:
                sean[k["glyph"]] = ("2.153/%s" % k["n"], val)
except FileNotFoundError:
    pass


def verdict_vs(v, want):
    if v is None:
        return "not_found"
    if v["outcome"] == "decided":
        return "right" if abs((v["beats"] or -9) - want) < 1e-6 else "wrong"
    if v["outcome"] == "narrowed":
        return "narrowed-holding" if any(abs(c - want) < 1e-6 for c in v["cands"] or ()) else "narrowed-not"
    return "abstained"


base = live("%s.%s.record.json" % (PREFIX, BASE))
report = {"doc": DOC, "arms": {}}
for arm in ARMS:
    a = live("%s.%s.record.json" % (PREFIX, arm))
    kinds = collections.Counter()
    rows = []
    judged_moves = collections.Counter()
    for g in sorted(set(base) | set(a)):
        vb, va = show(base.get(g)), show(a.get(g))
        if vb == va:
            if g in sean:
                judged_moves["same:" + verdict_vs(vb, sean[g][1])] += 1
            continue
        k = "%s/%s -> %s/%s" % ((vb or {}).get("decider"), (vb or {}).get("reason"), (va or {}).get("outcome"),
                                (va or {}).get("reason"))
        kinds[k] += 1
        row = dict(glyph=g, base=vb, arm=va)
        if g in sean:
            row["sean"] = sean[g]
            row["base_vs_sean"] = verdict_vs(vb, sean[g][1])
            row["arm_vs_sean"] = verdict_vs(va, sean[g][1])
            judged_moves["%s -> %s" % (row["base_vs_sean"], row["arm_vs_sean"])] += 1
        rows.append(row)
    report["arms"][arm] = dict(changed=len(rows), kinds=dict(kinds.most_common()), judged=dict(judged_moves), rows=rows)
    print("== %s vs %s: %d glyphs changed" % (arm, BASE, len(rows)))
    for k, n in kinds.most_common(12):
        print("   %5d  %s" % (n, k))
    print("   judged:", dict(judged_moves))
    for r in rows:
        if "sean" in r:
            print("     %-28s sean=%s base=%s %s -> arm=%s %s" % (r["sean"][0], r["sean"][1], r["base_vs_sean"],
                  (r["base"] or {}).get("reason"), r["arm_vs_sean"], (r["arm"] or {}).get("cands")))
json.dump(report, open(OUT, "w"), indent=1)
