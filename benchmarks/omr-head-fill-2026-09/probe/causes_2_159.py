"""ROADMAP 2.159 -- why each head_fill_from_ink head was not DECIDED a half, read off its own rows, in the order the reader
asks (2.148 first step: head-sized box -> slit share -> own stem). One cause per head, the FIRST gate it failed.
usage: causes_2_159.py OUTDIR [INDEX.json]"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from separate_2_159 import measures, gate  # noqa: E402

OUT = sys.argv[1]
crop = {}
if len(sys.argv) > 2:
    for t in json.load(open(sys.argv[2])):
        if t["n"] <= 22:
            crop.setdefault("glyph/%d/%d/%d/%d/" % (t["page"], t["system"], t["staff"], t["cell"]), []).append(t["n"])


def cause(h):
    a = h.get("adj") or {}
    hf = a.get("head_fill_first") or {}
    g = gate(h)
    if not hf:
        return "no_first_reading"
    if hf.get("not_head_sized"):
        ok, w, hh = g
        if hh < 0.9:
            return "box_too_short (h<0.9sp)"
        if hh > 1.8:
            return "box_too_tall (h>1.8sp)"
        if w < 1.1:
            return "box_too_narrow (w<1.1sp)"
        if w > 1.9:
            return "box_too_wide (w>1.9sp)"
        return "not_head_sized?"
    if hf.get("fill") is None:
        return "slit_between (0.06<rows_share<0.18)"
    if hf.get("fill") == "hollow" and not a.get("stems_attached"):
        return "hollow_but_no_stem_attached"
    return "other:" + str(hf.get("fill"))


tab = {}
for doc in ("litolff", "brahms"):
    H = json.load(open(os.path.join(OUT, "heads_%s.json" % doc)))
    c = collections.Counter()
    stems0 = collections.Counter()
    lines = []
    for s, h in H.items():
        if "hf" not in h:
            continue
        k = cause(h)
        c[k] += 1
        a = h.get("adj") or {}
        stems0[(k, bool(a.get("stems_attached")))] += 1
        m = measures(h)
        ni = (h.get("notehead_ink") or {}).get("detail") or {}
        row = dict(subject=s, cause=k, gate=gate(h), stems=a.get("stems_attached"), beam=a.get("beam_evidence"),
                   rows_share=m.get("rows_share (2.148 slit)"), hole=m.get("hole_share (2.148 hole)"),
                   c23_raw=m.get("2.23 centre ink, raw"), c23_off=m.get("2.23 centre ink, line rows out"),
                   whole_net=m.get("whole-head ink, lines erased"), box_source=ni.get("box_source"),
                   crops=crop.get(s.rsplit("/", 1)[0] + "/") if doc == "litolff" else None)
        lines.append(row)
    tab[doc] = {"causes": dict(c), "by_stem": {"%s|stem=%s" % k: v for k, v in stems0.items()}, "rows": lines}
    print(doc, sum(c.values()), c.most_common())
    print("   with/without own stem:", sorted(stems0.items()))
json.dump(tab, open(os.path.join(OUT, "causes.json"), "w"), indent=0)
print("\nthe litolff-unread-35 crop heads:")
for r in sorted(tab["litolff"]["rows"], key=lambda r: (r["crops"] or [99])[0]):
    if r["crops"]:
        print(r["crops"], r["subject"], r["cause"], "gate", r["gate"], "stems", r["stems"], "rs", r["rows_share"],
              "hole", r["hole"], "c23", r["c23_raw"], r["c23_off"], "whole", r["whole_net"], r["box_source"])
