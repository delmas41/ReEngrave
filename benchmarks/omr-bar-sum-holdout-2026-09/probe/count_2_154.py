"""ROADMAP 2.154 -- VOLUME of every bar-sum decider in a 20261014-night record (STAGED EVALUATE/INFER; one ijson pass, under
the record-load lock). For each LIVE duration verdict written by a decider that reads the bar sum, classify what it superseded:
PICK (the prior was NARROWED: the bar chose among a reader's candidates -- arm a) or MOVE (the prior was DECIDED: the bar changed
a decided value -- arm b), and the direction (longer / shorter / same). Also counts `reinstate_rest_between_staves` (a rest's
PRESENCE by a voice shortfall), which sets no note value.
usage: count_2_154.py DOC OUT.json     DOC = litolff | brahms
"""
import collections
import json
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

DOC, OUT = sys.argv[1], sys.argv[2]
BAR = {"reconcile_duration", "infer:collapse_bare_stem_by_bar", "infer:collapse_narrowed_by_bar"}

byid = {}
dur_ids = []
rest_reinstated = 0
with rec.lock():
    for v in rec.items(rec.RECORDS[DOC], "verdicts"):
        if v.get("decider") == "reinstate_rest_between_staves":
            rest_reinstated += 1
        if v["quantity"] != "duration":
            continue
        val = v["value"] if isinstance(v["value"], dict) else {}
        byid[v["id"]] = dict(sub=v["subject"], sup=v.get("supersedes"), decider=v.get("decider"), reason=v.get("reason"),
                             outcome=v["outcome"], beats=val.get("beats"), written=val.get("written"),
                             levels=val.get("beam_levels"),
                             cands=[(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                                    if isinstance(c.get("value"), dict)])
superseded = {b["sup"] for b in byid.values() if b["sup"]}
c = collections.Counter()
examples = collections.defaultdict(list)
for vid, b in byid.items():
    if b["decider"] not in BAR:
        continue
    live = vid not in superseded
    prior = byid.get(b["sup"]) if b["sup"] else None
    kind = "PICK" if prior and prior["outcome"] == "narrowed" else ("MOVE" if prior and prior["outcome"] == "decided" else "?")
    pb = prior and (prior["beats"] if prior["outcome"] == "decided" else (prior["cands"][0] if prior["cands"] else None))
    d = "?"
    if pb is not None and b["beats"] is not None:
        d = "longer" if b["beats"] > pb + 1e-9 else ("shorter" if b["beats"] < pb - 1e-9 else "same")
    if kind == "PICK":
        d += "/top" if prior["cands"] and prior["cands"][0] == b["beats"] else "/not-top"
    key = "%s %s %s %s" % (b["decider"], kind, d, "live" if live else "superseded")
    c[key] += 1
    if len(examples[key]) < 5:
        examples[key].append(dict(sub=b["sub"], prior=prior and dict(outcome=prior["outcome"], reason=prior["reason"],
                                                                  beats=prior["beats"], cands=prior["cands"]),
                                  beats=b["beats"]))
out = dict(doc=DOC, counts=dict(sorted(c.items())), reinstate_rest_between_staves=rest_reinstated, examples=examples)
json.dump(out, open(OUT, "w"), indent=1)
for k, n in sorted(c.items()):
    print("%6d  %s" % (n, k))
print("reinstate_rest_between_staves", rest_reinstated)
