"""ROADMAP 2.145 -- re-decide (ADJUDICATE..INFER via `pipeline.decide`) AND EXPORT a handful of whole SYSTEMS of a record,
flag OFF vs ON; no whole-record load (ijson-streamed rows of the named systems only, one pass).
usage: replay_2_145.py RECORD OUT.json "p,s;p,s;..." HEAD_SUBJECT [HEAD_SUBJECT ...]
OUT[arm][head] = {nn, duration, placed: category the EXPORT wrote for that subject (None = not written), fate}
   plus OUT[arm]["_notes"] = <note count of the exported MusicXML for these systems>, OUT[arm]["_rests"] = <rest count>.
Flag: OMR_HEAD_INK_IS_A_REST ("" = OFF, "1" = ON)."""
import json
import os
import sys

import ijson

sys.path.insert(0, ".")
P, OUT, SYS = sys.argv[1], sys.argv[2], sys.argv[3]
HEADS = sys.argv[4:]
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
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

res = {}
for arm, env in (("off", ""), ("on", "1")):
    os.environ["OMR_HEAD_INK_IS_A_REST"] = env
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    d = result["record"]
    vs = {}
    for v in d["verdicts"]:
        if v["subject"] in HEADS and v["quantity"] in (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.DURATION):
            val = v["value"]
            vs.setdefault(v["subject"], {})[v["quantity"]] = [v["outcome"], val.get("beats") if isinstance(val, dict) else val,
                                                               v["reason"], bool(isinstance(val, dict) and val.get("is_rest"))]
    try:
        xml, report, refusals, placed = RR.export_with_subjects(result)
        pl = {g: c for g, c in placed}
        rf = {}
        for s, r in refusals:
            rf.setdefault(s, []).append(r)
    except Exception as e:  # noqa: BLE001
        xml, report, pl, rf = "", {}, {}, {}
        print("EXPORT FAILED", repr(e))
    allv = {}
    for v in d["verdicts"]:
        allv["%s|%s" % (v["subject"], v["quantity"])] = [v["outcome"], json.dumps(v["value"], sort_keys=True, default=str)[:90],
                                                         v.get("reason")]
    out = {}
    for h in HEADS:
        out[h] = {"nn": vs.get(h, {}).get(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD), "duration": vs.get(h, {}).get(Q.DURATION),
                  "placed": pl.get(h), "not_written": rf.get(h)}
    out["_notes"] = xml.count("<note")
    out["_rests"] = xml.count("<rest")
    out["_report"] = {k: report.get(k) for k in ("notes_not_written_total", "notes_not_written", "bars_held_out_sum")}
    open(OUT.replace(".json", "-%s.musicxml" % arm), "w").write(xml)
    out["_verdicts"] = allv
    res[arm] = out
    print(arm, out["_notes"], out["_rests"], flush=True)
json.dump(res, open(OUT, "w"), indent=1, default=str)
