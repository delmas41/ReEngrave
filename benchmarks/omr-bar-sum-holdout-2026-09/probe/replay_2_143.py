"""ROADMAP 2.143 -- re-decide named whole SYSTEMS of a record (STAGED ADJUDICATE..INFER) with OMR_REFUSED_HEAD_NO_DURATION
OFF and ON; ijson-streamed rows of the named systems only (no whole-record load; take the shared record lock first).
usage: replay_2_143.py RECORD OUT.json "p,s;p,s;..."
OUT: {arm: {glyph_subject: {quantity: [outcome, value, reason, decider]}}} for duration + the two refusals."""
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
for arm, env in (("off", ""), ("on", "1")):
    os.environ["OMR_REFUSED_HEAD_NO_DURATION"] = env
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    d = log.to_json()
    sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
    stand = {}
    for v in d["verdicts"]:
        if v["id"] in sup: continue
        if v["quantity"] in (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.DURATION) and v["subject"].startswith("glyph/"):
            val = v["value"]
            if isinstance(val, dict): val = [val.get("beats"), val.get("beam_levels")]
            stand.setdefault(v["subject"], {})[v["quantity"]] = [v["outcome"], val, v["reason"], v.get("decider")]
    res[arm] = stand
    allv = {}
    for v in d['verdicts']:
        if v['id'] in sup: continue
        allv[v['subject'] + '|' + v['quantity']] = json.dumps([v['outcome'], v['value'], v['reason']], sort_keys=True, default=str)
    res[arm + '_all'] = allv
    res[arm + "_hist"] = {sj: [[v["id"], v["outcome"], v["reason"], v.get("decider"), v.get("supersedes")]
                               for v in d["verdicts"] if v["subject"] == sj and v["quantity"] == Q.DURATION]
                          for sj in ("glyph/14/1/8/4/6", "glyph/14/0/10/0/8")}
    print(arm, len(stand), flush=True)
res['diff_all'] = {k: [res['off_all'].get(k), res['on_all'].get(k)] for k in set(res['off_all']) | set(res['on_all']) if res['off_all'].get(k) != res['on_all'].get(k)}
del res['off_all'], res['on_all']
json.dump(res, open(OUT, "w"))
