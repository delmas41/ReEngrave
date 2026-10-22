"""ROADMAP 2.175 -- control candidates for the blind tiles, streamed from a night record (under the record-load lock).

usage: controls_2_175.py PLATE(litolff|brahms) OUT.json
Writes, per cell, the heads whose stored `Q.HEAD_STEM` verdict is DECIDED `one_stem` (value = the stem row id), the kept
heads' duration verdict, and the head box in page pixels, so a PLAIN one-stem head (one head on its stem) and a CHORD with
one stem (>= 2 heads on one stem) can be picked. Nothing is decided here."""
import collections
import json
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

LIB = rec.LIB
PATHS = {"litolff": LIB + "beethoven5-litolff-mvt1-whole-20261018-night.record.json",
         "brahms": LIB + "brahms1-breitkopf-mvt1-whole-20261018-night.record.json"}
plate, out = sys.argv[1], sys.argv[2]
heads = {}
with rec.lock():
    for o in rec.items(PATHS[plate], "observations"):
        if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/") and str(o["value"][0]).startswith("notehead"):
            bb = (o.get("detail") or {}).get("bbox_page_px")
            if bb:
                heads[o["subject"]] = {"bb": [round(v, 1) for v in bb], "cls": o["value"][0]}
    stem = {}
    dur = {}
    refused = set()
    for v in rec.items(PATHS[plate], "verdicts"):
        s = v["subject"]
        if s not in heads:
            continue
        q = v["quantity"]
        if q == "head_stem":
            stem[s] = (v["outcome"], v.get("reason"), v.get("value") if isinstance(v.get("value"), str) else None)
        elif q == "duration":
            val = v.get("value") if isinstance(v.get("value"), dict) else {}
            dur[s] = (v["outcome"], val.get("beats"))
        elif q == "notehead_is_not_a_notehead" and v["outcome"] == "decided" and v.get("value") is True:
            refused.add(s)
cells = collections.defaultdict(lambda: collections.defaultdict(list))
for s, st in stem.items():
    if s in refused or st[0] != "decided" or st[1] != "one_stem":
        continue
    cells[tuple(s.split("/")[1:5])][st[2]].append(s)
plain, chord = [], []
for c, by_stem in cells.items():
    for st, subs in by_stem.items():
        for s in subs:
            if dur.get(s, (None,))[0] != "decided":
                continue
            (chord if len(subs) >= 2 else plain).append(s)
json.dump({"heads": {s: {**heads[s], "dur": dur.get(s)} for s in set(plain[:4000]) | set(chord[:4000])},
           "plain": plain, "chord": chord}, open(out, "w"))
print(plate, "heads", len(heads), "plain one-stem", len(plain), "chord-on-one-stem", len(chord))
