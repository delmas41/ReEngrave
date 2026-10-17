"""ROADMAP 2.159 -- the GATHER rows a head's fill is read from, for (a) every head_fill_from_ink head and (b) every
notehead Sean judged a duration for (benchmarks/acceptance/judged-tiles.json, litolff + brahms, a glyph key whose
night-record page box sits inside his tile's box). Read from the 20261016-night per-page slices; no page gathered.
usage: head_rows_2_159.py SLICEDIR OUTDIR   -> OUTDIR/heads_<doc>.json {subject: {...}}"""
import json
import os
import sys

SD, OUT = sys.argv[1:3]
J = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
for doc in ("litolff", "brahms"):
    hf = json.load(open(os.path.join(OUT, doc + "_hf.json")))
    want = {}
    for r in hf["hf"]:
        want.setdefault(r["subject"], {})["hf"] = {"detail": r["detail"]}
    for t in J:
        if t.get("doc") == doc and t.get("answer_kind") == "duration" and t.get("subject_kind") == "glyph" \
                and isinstance(t.get("value"), (int, float)):
            want.setdefault(t["subject"], {}).setdefault("judged", []).append(
                {"item": t["item"], "tile": t["tile"], "answer": t["answer"], "value": t["value"],
                 "page_box": t.get("page_box")})
    cells = {s.replace("glyph/", "cell/").rsplit("/", 1)[0]: s for s in want}
    pages = sorted({int(s.split("/")[1]) for s in want})
    for pg in pages:
        p = os.path.join(SD, doc, "p%02d.observations.jsonl" % pg)
        for line in open(p):
            i = line.find('"subject": "')
            if i < 0:
                continue
            sub = line[i + 12:line.find('"', i + 12)]
            if sub in want:
                o = json.loads(line)
                q = o["quantity"]
                if q in ("glyph_box", "notehead_class", "notehead_ink", "notehead_recentre", "head_line_cut"):
                    want[sub][q] = {"value": o["value"], "detail": o.get("detail")}
            elif sub.startswith("cell/"):
                o = None
                if '"cell_staff_space"' in line:
                    o = json.loads(line)
                    for s in want:
                        if s.startswith(sub.replace("cell/", "glyph/") + "/"):
                            want[s]["space"] = o["value"]
        for line in open(os.path.join(SD, doc, "p%02d.verdicts.jsonl" % pg)):
            if '"adjudicate_duration"' not in line:
                continue
            i = line.find('"subject": "')
            sub = line[i + 12:line.find('"', i + 12)]
            if sub in want and "adj" not in want[sub]:
                v = json.loads(line)
                if v.get("decider") == "adjudicate_duration":
                    d = v.get("detail") or {}
                    want[sub]["adj"] = {"reason": v["reason"], "outcome": v["outcome"],
                                        "stems_attached": d.get("stems_attached"),
                                        "head_fill_first": d.get("head_fill_first"),
                                        "beam_evidence": d.get("beam_evidence"), "staff_space": d.get("staff_space")}
    json.dump(want, open(os.path.join(OUT, "heads_%s.json" % doc), "w"))
    print(doc, len(want), "judged", sum(1 for w in want.values() if "judged" in w),
          "with ink row", sum(1 for w in want.values() if "notehead_ink" in w))
