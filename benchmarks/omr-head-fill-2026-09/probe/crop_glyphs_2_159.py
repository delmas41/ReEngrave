"""ROADMAP 2.159 -- for each litolff-unread-35 crop 1-22: every glyph in that (page, system, staff, cell) with its
first and live duration verdict (reason, outcome, candidates) and its notehead class. usage: SLICEDIR INDEX OUT.json"""
import collections
import json
import os
import sys

SD, IDX, OUT = sys.argv[1:4]
idx = [t for t in json.load(open(IDX)) if t["n"] <= 22]
want = {"glyph/%d/%d/%d/%d/" % (t["page"], t["system"], t["staff"], t["cell"]): t["n"] for t in idx}
res = collections.defaultdict(lambda: collections.defaultdict(dict))
for pg in sorted({t["page"] for t in idx}):
    for line in open(os.path.join(SD, "litolff", "p%02d.verdicts.jsonl" % pg)):
        v = json.loads(line)
        s = v.get("subject", "")
        pre = s.rsplit("/", 1)[0] + "/"
        if pre not in want or v.get("quantity") != "duration":
            continue
        e = res[want[pre]][s]
        b = dict(outcome=v["outcome"], reason=v["reason"], decider=v["decider"],
                 value=(v.get("value") or {}).get("written") if isinstance(v.get("value"), dict) else None,
                 cands=[(c.get("value") or {}).get("written") for c in (v.get("candidates") or [])])
        e.setdefault("first", b)
        e["live"] = b
        if v["decider"] == "adjudicate_duration":
            d = v.get("detail") or {}
            e["adj_detail"] = {k: d.get(k) for k in ("head", "head_fill_first", "stems_attached", "beam_evidence",
                                                     "staff_space")}
            e["adj_detail"]["iw"] = ((d.get("notehead_ink") or {}).get("interior_white"))
json.dump(res, open(OUT, "w"), indent=1)
for n in sorted(res):
    for s, e in res[n].items():
        print(n, s, "first:", e["first"]["outcome"], e["first"]["reason"], e["first"]["cands"] or e["first"]["value"],
              "| live:", e["live"]["outcome"], e["live"]["reason"], e["live"]["cands"] or e["live"]["value"])
