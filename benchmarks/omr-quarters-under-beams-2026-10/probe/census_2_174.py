"""ROADMAP 2.174 step 2a -- census of DECIDED quarters (`head_and_marks`, written 1.0, no dots, head not open, a stem attached)
on a plate's per-page slices (`pages_2_165.py`), by what the cell's beam readers saw and why the strokes did not count for the head.
usage: census_2_174.py DOC SLICEDIR OUT.json"""
import collections
import glob
import json
import os
import sys

DOC, SD, OUT = sys.argv[1:4]
D = os.path.join(SD, DOC)
rows = []
cnt = collections.Counter()
for p in sorted(glob.glob(os.path.join(D, "p*.verdicts.jsonl"))):
    first, chain = {}, collections.defaultdict(list)
    for l in open(p):
        v = json.loads(l)
        if v["quantity"] != "duration":
            continue
        s = v["subject"]
        chain[s].append(v)
        if v.get("decider") == "adjudicate_duration" and s not in first:
            first[s] = v
    for s, v in first.items():
        val = v.get("value") if isinstance(v.get("value"), dict) else {}
        if v["outcome"] != "decided":
            continue
        d = v.get("detail") or {}
        cnt["decided_" + str(v.get("reason"))] += 1
        if val.get("written") != 1.0 or val.get("dots") or d.get("head_is_open"):
            continue
        has_stem = bool(d.get("stems_attached") or d.get("beam_side"))
        cnt["quarter_with_stem" if has_stem else "quarter_no_stem"] += 1
        ch = chain[s]
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        live = ([x for x in ch if x["id"] not in sup] or ch)[-1]
        lv = live.get("value") if isinstance(live.get("value"), dict) else {}
        rows.append(dict(subject=s, reason=v.get('reason'), has_stem=has_stem, cv=d.get("cv_beams"), yolo=d.get("yolo_beams"), yolo_kept=d.get("yolo_kept"),
                         far=d.get("beams_far_side"), beyond=d.get("beams_beyond_stem"), ledger=d.get("beams_ledger_line"),
                         slash=d.get("beams_slash"), nbr=d.get("beams_neighbour_staff"), arc=d.get("beams_decided_arc"),
                         ink=d.get("beams_not_by_ink"), ink_why=d.get("beams_not_by_ink_why"), by_stem=d.get("beams_by_stem"),
                         stems=d.get("stems_attached"), side=d.get("beam_side"), cert=d.get("levels_certain"),
                         poss=d.get("levels_possible"), evid=d.get("beam_evidence"), guarded=d.get("beyond_stem_kept_no_other_mark"),
                         tol=d.get("join_tolerance_px"), space=d.get("staff_space"),
                         standing=dict(outcome=live["outcome"], reason=live.get("reason"), decider=live.get("decider"),
                                       beats=lv.get("beats"), written=lv.get("written"))))
for r in [x for x in rows if x['has_stem'] and x['reason'] == 'head_and_marks']:
    seen_cv, seen_yolo = bool(r["cv"]), bool(r["yolo"])
    cnt["quarter_cv_and_yolo" if seen_cv and seen_yolo else "quarter_cv_only" if seen_cv else "quarter_yolo_only" if seen_yolo else "quarter_no_beam_in_cell"] += 1
json.dump(dict(rows=rows, counts=cnt), open(OUT, "w"))
print(DOC, dict(cnt))
