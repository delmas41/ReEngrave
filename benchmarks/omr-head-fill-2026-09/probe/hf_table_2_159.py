"""ROADMAP 2.159 -- one line per head_fill_from_ink verdict: what the 2.148 first step read and why it did not decide.
usage: hf_table_2_159.py OUTDIR [INDEX.json]   (INDEX = litolff-unread-35 index: marks the crop number)"""
import collections
import json
import os
import sys

OUT = sys.argv[1]
idx = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else []
crop = {}
for t in idx:
    if t["n"] <= 22:
        crop[(t["page"], t["system"], t["staff"], t["cell"])] = t["n"]


def fields(r):
    d = r["detail"] or {}
    hf = d.get("head_fill_first") or {}
    ni = d.get("notehead_ink") or {}
    iw = ni.get("interior_white") or {}
    sp = d.get("staff_space") or 0
    box = iw.get("box")
    return dict(
        fill=hf.get("fill"), rs=hf.get("rows_share"), hole=hf.get("hole_share"), nhs=hf.get("not_head_sized"),
        box_sp=(round(box[2] / sp, 2), round(box[3] / sp, 2)) if box and sp else None, frame=ni.get("ink_frame"),
        src=ni.get("box_source"), beam=d.get("beam_evidence"), stems=d.get("stems_attached"), head=d.get("head"))


for doc in ("litolff", "brahms"):
    D = json.load(open(os.path.join(OUT, doc + "_hf.json")))
    c = collections.Counter()
    for r in D["hf"]:
        f = fields(r)
        _, pg, sy, st, ce, gi = r["subject"].split("/")
        n = crop.get((int(pg), int(sy), int(st), int(ce))) if doc == "litolff" else None
        live = (D["chain"].get(r["subject"]) or [{}])[-1]
        c[(f["fill"], bool(f["nhs"]), f["frame"])] += 1
        if n or len(sys.argv) > 3:
            print(doc, n, r["subject"], f, "live:", live.get("outcome"), live.get("reason"))
    print(doc, sorted(c.items(), key=lambda kv: -kv[1]))
