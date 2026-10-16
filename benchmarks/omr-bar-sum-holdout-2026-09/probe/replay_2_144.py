"""ROADMAP 2.144 -- re-decide a handful of whole SYSTEMS of a record (STAGED ADJUDICATE..INFER, `pipeline.decide`) with the
flag OFF and ON; no whole-record load (ijson-streamed rows of the named systems only).
usage: replay_2_144.py RECORD OUT.json "p,s;p,s;..." 
OUT: per notehead glyph in those systems: {off: [nn_value, nn_reason, dur_beats], on: [...]}"""
import ijson, json, os, sys
sys.path.insert(0, ".")
P, OUT = sys.argv[1], sys.argv[2]
keep = {tuple(int(x) for x in t.split(",")) for t in sys.argv[3].split(";") if t}
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
            if want(it["subject"]): rec[k].append(it)
print({k: len(v) for k, v in rec.items()}, flush=True)
from tools.omr.staged.record import Q
from tools.omr.staged.review import rerun as RR
res = {}
for arm, env in (("off", "0"), ("on", "1")):
    os.environ["OMR_HEAD_INSIDE_A_CLEF_BOX"] = env
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    d = log.to_json()
    stand = {}
    for v in d["verdicts"]:
        if v["quantity"] in (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.DURATION, Q.REST_IS_NOT_A_REST) and v["subject"].startswith("glyph/"):
            val = v["value"]
            stand.setdefault(v["subject"], {})[v["quantity"]] = [v["outcome"], val.get("beats") if isinstance(val, dict) else val, v["reason"]]
    res[arm] = stand
    print(arm, len(stand), flush=True)
json.dump(res, open(OUT, "w"))
