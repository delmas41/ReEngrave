"""2.170 step 2a: stream one night record's verdicts ONCE (ijson, never a whole load) and keep every adjudicate_duration verdict
narrowed `beam_discounted_uncertain` / `beams_ambiguous` (detail + candidates) plus each such glyph's STANDING duration verdict
(the last of its chain not superseded), and the head_stem verdict. usage: extract_2_170.py litolff|brahms OUT.json"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec as RC  # noqa: E402

PATH = {"litolff": RC.LIB + "beethoven5-litolff-mvt1-whole-20261018-night.record.json",
        "brahms": RC.LIB + "brahms1-breitkopf-mvt1-whole-20261018-night.record.json"}
REASONS = {"beam_discounted_uncertain", "beams_ambiguous"}
doc, out = sys.argv[1:3]
first, chain, hs = {}, defaultdict(list), {}
for v in RC.items(PATH[doc], "verdicts"):
    q = v["quantity"]
    if q == "duration":
        s = v["subject"]
        if v.get("decider") == "adjudicate_duration" and s not in first:
            first[s] = dict(reason=v.get("reason"), outcome=v["outcome"], detail=v.get("detail"),
                            candidates=v.get("candidates"), value=v.get("value"), used=v.get("used"))
        chain[s].append(dict(id=v["id"], sup=v.get("supersedes"), outcome=v["outcome"], reason=v.get("reason"),
                             decider=v.get("decider"), value=v.get("value")))
    elif q == "head_stem" and v["subject"] not in hs:
        hs[v["subject"]] = [v["outcome"], v.get("reason")]
keep = {s: f for s, f in first.items() if f["reason"] in REASONS}
standing = {}
for s in keep:
    ch = chain[s]
    sup = {c["sup"] for c in ch if c["sup"]}
    live = [c for c in ch if c["id"] not in sup] or ch
    standing[s] = live[-1]
allfirst = defaultdict(int)
for s, f in first.items():
    allfirst[f["outcome"] + ":" + str(f["reason"])] += 1
json.dump(dict(narrowed=keep, standing=standing, head_stem={s: hs.get(s) for s in keep}, first_reason_counts=allfirst),
          open(out, "w"))
print("DONE", doc, "first verdicts", len(first), "kept", len(keep))
