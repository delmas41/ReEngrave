"""ROADMAP 2.153 -- REACH: for every LIVE `duration` verdict of a 20261014-night record (STAGED; one ijson pass over
`record.verdicts`, no whole-record load, under the record-load lock), count it by (decider, reason, outcome) and by feature
tags read off the adjudicator's own detail, and cross it with the coverage file's HELD bars (bars_held_out_sum.held; under =
every voice shorter than the bar, over = any voice longer).
usage: count_2_153.py DOC OUT.json     DOC = litolff | brahms
"""
import collections
import json
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

DOC, OUT = sys.argv[1], sys.argv[2]
COV = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}[DOC]
cov = json.load(open("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261014-night/compare/%s.coverage.json" % COV))
held = {}
for b in cov["bars_held_out_sum"]["held"]:
    vs = [v["units"] for v in b["voices"]]
    w = b["want_units"]
    kind = "under" if vs and all(u < w for u in vs) else ("over" if any(u > w for u in vs) else "mixed")
    held[(b["page"], b["system"], b["staff"], b["cell"])] = kind

chains = collections.defaultdict(list)
with rec.lock():
    for v in rec.items(rec.RECORDS[DOC], "verdicts"):
        if v["quantity"] != "duration" or not v["subject"].startswith("glyph/"):
            continue
        d = v.get("detail") or {}
        keep = {k: d.get(k) for k in ("head_is_open", "beam_evidence", "stems_attached", "beams_by_stem", "levels_certain",
                                       "beams_neighbour_staff", "beams_decided_arc", "beams_beyond_stem", "yolo_beams",
                                       "cv_beams", "flag_levels", "dots_attached", "beam_side", "head")}
        val = v["value"] if isinstance(v["value"], dict) else {}
        chains[v["subject"]].append(dict(id=v["id"], sup=v.get("supersedes"), decider=v.get("decider"), reason=v.get("reason"),
                                         outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"),
                                         levels=val.get("beam_levels"), f=keep if v.get("decider") == "adjudicate_duration" else None))
print("subjects", len(chains), flush=True)

by = collections.Counter()
tags = collections.Counter()
chain_kinds = collections.Counter()
for g, ch in chains.items():
    sup = {c["sup"] for c in ch if c["sup"]}
    live = [c for c in ch if c["id"] not in sup]
    L = (live or ch)[-1]
    first = next((c for c in ch if c["f"]), None)
    p = g.split("/")
    bar = tuple(int(x) for x in p[1:5])
    h = held.get(bar)
    keys = [("%s/%s/%s" % (L["decider"], L["reason"], L["outcome"]))]
    f = first["f"] if first else {}
    if first and first["outcome"] == "decided" and first["reason"] in ("head_and_marks", "hooks_counted"):
        lc, bj = f.get("levels_certain") or 0, f.get("beams_by_stem") or 0
        keys.append("FIRST %s/be=%s" % (first["reason"], f.get("beam_evidence")))
        if not f.get("flag_levels") and lc > 0 and bj == 0:
            keys.append("TAG A0 levels_read_with_no_stroke_joined_to_a_stem")
        if not f.get("flag_levels") and lc > bj > 0:
            keys.append("TAG A1 levels_exceed_joined_strokes")
        if not f.get("flag_levels") and bj > 0 and lc == bj and (f.get("beams_neighbour_staff") or f.get("beams_decided_arc")):
            keys.append("TAG B joined_stroke_while_arc_or_neighbour_ink_near")
        if first["reason"] == "head_and_marks" and lc == 0 and not f.get("flag_levels") and f.get("beam_evidence") == "reader_declined":
            keys.append("TAG C unflagged_unbeamed_quarter_where_beam_reader_declined")
        if first["reason"] == "head_and_marks" and f.get("head_is_open") is False:
            keys.append("TAG black_head_no_interior_white_row")
    if len(ch) > 1:
        chain_kinds["%s -> %s" % (ch[0]["decider"] + "/" + str(ch[0]["reason"]), L["decider"] + "/" + str(L["reason"]))] += 1
    for k in keys:
        by[(k, "all")] += 1
        if h:
            by[(k, "held")] += 1
            by[(k, "held_" + h)] += 1
res = collections.defaultdict(dict)
for (k, c), n in by.items():
    res[k][c] = n
json.dump(dict(doc=DOC, subjects=len(chains), held_bars=len(held), res=res, chains=chain_kinds.most_common(60)), open(OUT, "w"), indent=1)
print("held bar kinds", collections.Counter(held.values()))
for k, v in sorted(res.items(), key=lambda kv: -kv[1].get("all", 0))[:45]:
    print("%6d held %5d (under %4d over %4d)  %s" % (v.get("all", 0), v.get("held", 0), v.get("held_under", 0), v.get("held_over", 0), k))
