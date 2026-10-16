"""ROADMAP 2.150b -- same replay as replay_2_150.py but the arm is OMR_REST_STROKE_INTO_HEAD (the ink test). The rows GATHER
would file (Q.REST_INK_CONTACT) are computed here off the 600 dpi page raster by the SAME `rest_ink.measure` (production
staff-line removal on a stand-in cell, ink_2_150b.py) and injected into the slice before the re-decide, in BOTH arms; only
the flag differs. usage: replay_2_150b.py DOC RECORD OUT.json "p,s;p,s"   (DOC = brahms|litolff)
Original header: ROADMAP 2.150 -- re-decide (ADJUDICATE..INFER via the review rerun) AND EXPORT a handful of whole SYSTEMS of a
record, OMR_REST_WIDTH_FLOOR OFF vs ON; no whole-record load (ijson-streamed rows of the named systems only).
usage: replay_2_150.py RECORD OUT.json "p,s;p,s;..."
OUT[arm] = {_rests, _notes, _report, _verdicts: {subject|quantity: [outcome, value, reason]}}; MusicXML per arm beside
OUT (compare with xml_diff_2_145.py). The pattern is replay_2_145.py's, flag swapped."""
import json
import os
import sys

import ijson

sys.path.insert(0, ".")
DOC, P, OUT, SYS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import ink_2_150b as INK  # noqa: E402
keep = {tuple(int(x) for x in t.split(",")) for t in SYS.split(";") if t}


def want(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return (int(p[1]), int(p[2])) in keep
    return True


rec = {"observations": [], "abstentions": []}
with open(P, "rb") as f:
    for k in rec:
        f.seek(0)
        for it in ijson.items(f, "record.%s.item" % k, use_float=True):
            if want(it["subject"]):
                rec[k].append(it)
print({k: len(v) for k, v in rec.items()}, flush=True)
# the rows GATHER would file for the rest boxes of these systems (decides nothing)
_cache = INK.rows(DOC)
_n = 900000
_injected, _none = 0, 0
for g in sorted(_cache["rest_rows"]):
    if not want(g):
        continue
    m = INK.measure_glyph(DOC, g)
    if m is None:
        _none += 1
        continue
    _n += 1
    rec["observations"].append({"id": "obs:%06d" % _n, "subject": g, "quantity": "rest_ink_contact",
                                "value": m["thin_run_sp"], "reader": "cv_rest_ink_contact",
                                "frame": "cell:%s" % g.split("/")[4], "score": None, "basis": [], "detail": m})
    _injected += 1
print("rest_ink_contact rows injected", _injected, "no measurement", _none, flush=True)
from tools.omr.staged.review import rerun as RR  # noqa: E402

res = {}
for arm, env in (("off", ""), ("on", "1")):
    os.environ["OMR_REST_STROKE_INTO_HEAD"] = env
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    d = result["record"]
    try:
        xml, report, refusals, placed = RR.export_with_subjects(result)
    except Exception as e:  # noqa: BLE001
        xml, report = "", {}
        print("EXPORT FAILED", repr(e))
    allv = {}
    for v in d["verdicts"]:
        allv["%s|%s" % (v["subject"], v["quantity"])] = [v["outcome"], json.dumps(v["value"], sort_keys=True,
                                                                                   default=str)[:90], v.get("reason")]
    out = {"_notes": xml.count("<note"), "_rests": xml.count("<rest"),
           "_report": {k: report.get(k) for k in ("notes_not_written_total", "notes_not_written",
                                                  "bars_held_out_sum")},
           "_verdicts": allv}
    open(OUT.replace(".json", "-%s.musicxml" % arm), "w").write(xml)
    res[arm] = out
    print(arm, out["_notes"], out["_rests"], flush=True)
json.dump(res, open(OUT, "w"), indent=1, default=str)
off, on = res["off"]["_verdicts"], res["on"]["_verdicts"]
ch = [k for k in sorted(set(off) | set(on)) if off.get(k) != on.get(k)]
print("verdicts changed:", len(ch))
for k in ch[:80]:
    print("  ", k, off.get(k), "->", on.get(k))
