"""ROADMAP 2.153 -- list the glyphs of a 20261014-night record whose STORED first `adjudicate_duration` verdict DECIDED a beam
level (head_and_marks / hooks_counted, no flag) from more strokes than any stem is joined to: levels_certain > beams_by_stem
(the notes OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM can change), plus the joined-beam controls. One ijson pass, under the record lock.
usage: list_a_2_153.py DOC OUT.json"""
import json
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

DOC, OUT = sys.argv[1:3]
COV = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}[DOC]
cov = json.load(open("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261014-night/compare/%s.coverage.json" % COV))
held = {(b["page"], b["system"], b["staff"], b["cell"]) for b in cov["bars_held_out_sum"]["held"]}
a, joined, plain = [], [], []
with rec.lock():
    for v in rec.items(rec.RECORDS[DOC], "verdicts"):
        if v["quantity"] != "duration" or v.get("decider") != "adjudicate_duration" or v["outcome"] != "decided":
            continue
        if v["reason"] not in ("head_and_marks", "hooks_counted") or not v["subject"].startswith("glyph/"):
            continue
        d = v.get("detail") or {}
        if d.get("flag_levels"):
            continue
        lc, bj = d.get("levels_certain") or 0, d.get("beams_by_stem") or 0
        p = v["subject"].split("/")
        bar = tuple(int(x) for x in p[1:5])
        row = dict(glyph=v["subject"], levels=lc, joined=bj, held=bar in held, be=d.get("beam_evidence"),
                   stem_side=d.get("beam_side"), arc=d.get("beams_decided_arc"), neigh=d.get("beams_neighbour_staff"))
        if lc > bj:
            a.append(row)
        elif lc >= 1 and bj >= 1 and lc == bj:
            joined.append(row)
        elif lc == 0 and d.get("head_is_open") is False and d.get("beam_evidence") == "none_over_this_note":
            plain.append(row)
json.dump(dict(a=a, joined=joined, plain=plain), open(OUT, "w"))
print(DOC, "A (certain > joined):", len(a), "held", sum(r["held"] for r in a), "| joined controls:", len(joined), "| plain:", len(plain))
