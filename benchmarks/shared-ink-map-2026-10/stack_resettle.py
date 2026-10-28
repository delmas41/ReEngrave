"""ROADMAP 2.202c (read-only, no gather): re-settle the narrowed heads of a lane_report out dir's ON arm with the stacked-level tip reading.
usage: stack_resettle.py REPORT_OUT_DIR   (prints per plate: heads that were stroke_candidate / disagree_narrowed, how many now agree with main's `before`)"""
import collections, json, pathlib, sys
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/shared-ink-map-2026-10")
from tools.omr.staged import beam_strokes as BS
import beams_cause as BC, beam_faults_records as BF

rep = pathlib.Path(sys.argv[1]); res = {}
for plate in ("litolff", "brahms"):
    views = BF.load_views(rep / "work" / ("%s.on.gathered.record.json" % plate))
    mini = json.load(open(rep / "work" / ("%s.on.mini-record.json" % plate)))
    c = collections.Counter(); fixed = []; broke = []
    for v in mini["verdicts"]:
        if v["quantity"] != "duration" or v.get("supersedes"):
            continue
        d = (v.get("detail") or {}).get("beams_from_strokes")
        if not d or not d.get("tip") or d.get("flag_levels"):
            continue
        side = v["detail"].get("beam_side")
        if side not in ("up", "down"):
            continue
        cell = "/".join(v["subject"].split("/")[1:5])
        vs = views.get(cell, []); by = {s.ordinal: s for s in vs}
        stem = by.get(d["tip"]["stem"])
        if stem is None:
            continue
        for stack in (False, True):
            BS.STACK_FILTER = stack
            n = len(BS.tip_reading(vs, BS.roles(vs), stem, side)["beams"])
            agree = d["before"][0] <= n <= d["before"][1]
            c[(d["settled"], stack, agree)] += 1
            if stack is False: old = agree
        if d["settled"] in ("stroke_candidate", "disagree_narrowed") and not old and agree: fixed.append(v["subject"])
        if old and not agree: broke.append(v["subject"])
    print(plate, "fixed", len(fixed), "broke", len(broke), "broke:", broke[:8])
    for k, n in sorted(c.items(), key=str): print("  ", k, n)
