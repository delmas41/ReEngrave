"""ROADMAP 2.102 (b): re-ADJUDICATE one saved record's GATHER rows with today's
tree and diff every `adjudicate_duration` verdict against the recorded one.

GATHER + ADJUDICATE only (Sean 2026-09-30). The record's own adjudicate-stage
duration verdicts are the base, this tree's are the arm; anything that differs
for a reason other than `not_a_note_mark` / the hollow-half gate is NOISE and is
reported as such (the control: a rebuild that does not reproduce is no A/B).
Blind to GATHER changes by construction (CLAUDE.md 6b).

    python3 benchmarks/omr-held-out-2026-10/p102_readj.py REC OUT.json
"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import adjudicate  # noqa: E402
from tools.omr.staged import adjudicators, consequences  # noqa: E402,F401
from tools.omr.staged.record import Log, Q, Subject  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402


def rebuild(rec):
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: int(str(t[0]["id"]).split(":")[-1]))
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"),
                        derived_from=tuple(r.get("basis") or ()), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"],
                        reason=r["reason"], **detail)
    return log


def key(v):
    val = v.get("value")
    return (v["outcome"], v["reason"],
            (val or {}).get("beats") if isinstance(val, dict) else None)


rec = load_record(sys.argv[1])["record"]
base = {v["subject"]: v for v in rec["verdicts"]
        if v["quantity"] == "duration" and v["decider"] == "adjudicate_duration"}
log = rebuild(rec)
adjudicate.run(log)
arm = {v["subject"]: v for v in log.to_json()["verdicts"]
       if v["quantity"] == "duration" and v["decider"] == "adjudicate_duration"}
refused = {v["subject"]: v["reason"] for v in log.to_json()["verdicts"]
           if v["quantity"] == "notehead_is_not_a_notehead"
           and v["outcome"] == "decided" and v["value"] is True}
changed = []
tally = collections.Counter()
for s, b in base.items():
    a = arm.get(s)
    if a is None:
        tally["absent in arm"] += 1
        continue
    if key(a) == key(b):
        tally["same"] += 1
        continue
    kind = (f"{b['outcome']}:{b['reason']} -> {a['outcome']}:{a['reason']}")
    tally[kind] += 1
    changed.append({"subject": s, "was": key(b), "now": key(a),
                    "refused_as": refused.get(s),
                    "why": (a.get("detail") or {}).get("why")})
print(sys.argv[1].split("/")[-1], "duration verdicts", len(base))
for k, n in tally.most_common(12):
    print("   ", n, k)
json.dump(changed, open(sys.argv[2], "w"), indent=0, default=str)
