"""2.139: what OMR_DYNAMIC_LEXICON_WORD=1 would do to the blue `dyn.` cells, from the cached rows
(uses the adjudicator's own helpers on shim rows, so the rule is the shipped one).
usage: 2.139_on.py NAME"""
import sys, json, types, collections
sys.path.insert(0, ".")
from tools.omr.staged.adjudicators import text as T
O = "benchmarks/omr-direction-text-2026-09/out/2.139/"
name = sys.argv[1]
ver = {v["subject"]: v for v in json.load(open(O + name + "_ver.json")) if v["quantity"] == "dynamic"}
obs = json.load(open(O + name + "_obs.json")); byid = {o["id"]: o for o in obs}
sides = {o["subject"]: o["value"] for o in obs if o["quantity"] == "dynamic_letter_neighbours"}
words = collections.defaultdict(list)
for o in obs:
    if o["quantity"] == "direction_word" and (o.get("detail") or {}).get("bbox_page_px"):
        p = o["subject"].split("/"); words[tuple(p[1:3])].append((tuple(o["detail"]["bbox_page_px"]), str(o["value"])))
res = collections.Counter(); out = []
for cell, v in ver.items():
    if v.get("reason") != "unspellable": continue
    p = cell.split("/"); wb = words[tuple(p[1:3])]
    letters = [byid[i] for w in v["detail"]["words"] for i in w["letters"] if i in byid]
    keep, drop = [], []
    for o in letters:
        row = types.SimpleNamespace(detail=o["detail"], value=o["value"], subject=o["subject"])
        s = sides.get(o["subject"])
        gone = False
        if T._letter_of_a_known_word(row, wb) and s is not None and not T._is_a_letter_of_a_known_word(s) \
                and T._lone_letter_of_a_lexicon_word(row):
            gone = True
        (drop if gone else keep).append(o["detail"].get("letter") or o["value"])
    kind = "blue dyn. GONE (word is the text direction)" if letters and not keep else \
           ("partly dropped, residue stays" if drop else "unchanged")
    res[kind] += 1; out.append({"cell": cell, "drop": drop, "keep": keep, "kind": kind})
print(name, dict(res)); json.dump(out, open(O + name + "_on.json", "w"), indent=1)
for r in out:
    if r["kind"] != "unchanged": print(r)
