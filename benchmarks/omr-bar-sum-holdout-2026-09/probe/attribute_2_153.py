"""ROADMAP 2.153 -- ATTRIBUTE each judged value error: re-decide the SLICE of its system(s) with the CURRENT code defaults
(STAGED ADJUDICATE..INFER via review.rerun), and print, per target glyph, the whole DURATION chain (decider, reason,
outcome, value) the replay built and the one the record itself stored. No flag is set here: whatever main defaults are.
usage: attribute_2_153.py SLICE.json DOC OUT.json     (DOC = key in out/2.153/targets.json)"""
import json
import sys

sys.path.insert(0, ".")
SL, DOC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
targets = json.load(open("out/2.153/targets.json"))[DOC]
rec = json.load(open(SL))
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import replay_util_2_153 as RU  # noqa: E402


def brief(v):
    val = v["value"]
    if isinstance(val, dict):
        val = {k: val[k] for k in ("beats", "written", "dots", "beam_levels", "head_fill", "is_rest") if k in val}
    cands = [c.get("value", {}).get("written") for c in (v.get("candidates") or [])]
    return dict(id=v["id"], decider=v.get("decider"), reason=v.get("reason"), outcome=v["outcome"], value=val,
                cands=cands or None, supersedes=v.get("supersedes"))


def chains(verdicts):
    by = {}
    for v in verdicts:
        if v["quantity"] == Q.DURATION:
            by.setdefault(v["subject"], []).append(v)
    return by


def live(chain):
    sup = {v.get("supersedes") for v in chain if v.get("supersedes")}
    l = [v for v in chain if v["id"] not in sup]
    return (l or chain)[-1]


stored = chains(rec["verdicts"])
log, _ = RU.rebuild(rec)
RR.run_stages(log)
d = log.to_json()
replay = chains(d["verdicts"])
res = []
for t in targets:
    g = t["glyph"]
    sc, rc = stored.get(g, []), replay.get(g, [])
    row = dict(t, stored=[brief(v) for v in sc], stored_live=brief(live(sc)) if sc else None,
               replay=[brief(v) for v in rc], replay_live=brief(live(rc)) if rc else None)
    # the detail of the replay's live verdict (what the decider recorded) -- first 700 chars
    if rc:
        row["replay_live_detail"] = json.dumps(live(rc).get("detail"), default=str)[:900]
        row["replay_live_basis_n"] = len(live(rc).get("basis") or [])
    res.append(row)
json.dump(res, open(OUT, "w"), indent=1, default=str)
for r in res:
    sl, rl = r["stored_live"], r["replay_live"]
    f = lambda x: None if x is None else "%s/%s %s %s" % (x["decider"], x["reason"], x["outcome"], x["value"].get("written") if isinstance(x["value"], dict) else x["cands"])
    print(r["item"], r["n"], "Sean:", r["sean"], "| stored:", f(sl), "| replay:", f(rl), "| same" if f(sl) == f(rl) else "| CHANGED")
