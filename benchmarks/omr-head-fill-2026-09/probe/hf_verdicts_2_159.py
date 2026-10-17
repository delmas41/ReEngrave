"""ROADMAP 2.159 -- every head_fill_from_ink verdict of the 20261016-night records (per-page slices), with its detail,
plus every verdict that later SUPERSEDES one of them (the live reading), into one json per doc.
usage: hf_verdicts_2_159.py SLICEDIR OUTDIR"""
import glob
import json
import os
import sys

SD, OUT = sys.argv[1:3]
os.makedirs(OUT, exist_ok=True)
for doc in ("litolff", "brahms"):
    rows, subj = [], set()
    pages = sorted(glob.glob(os.path.join(SD, doc, "p*.verdicts.jsonl")))
    for p in pages:
        for line in open(p):
            if '"head_fill_from_ink"' not in line:
                continue
            v = json.loads(line)
            if v.get("reason") != "head_fill_from_ink":
                continue
            subj.add(v["subject"])
            rows.append({k: v.get(k) for k in ("id", "subject", "outcome", "reason", "used", "candidates", "detail",
                                                "supersedes")})
    later = {}
    for p in pages:
        for line in open(p):
            if '"duration"' not in line:
                continue
            v = json.loads(line)
            if v.get("quantity") == "duration" and v.get("subject") in subj:
                later.setdefault(v["subject"], []).append(
                    {k: v.get(k) for k in ("id", "outcome", "value", "decider", "reason", "supersedes")})
    json.dump({"hf": rows, "chain": later}, open(os.path.join(OUT, doc + "_hf.json"), "w"))
    print(doc, len(rows), len(subj))
