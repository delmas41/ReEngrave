"""lane-arc-owner-regression: replay `adjudicate_arc_owner` (STAGED, ADJUDICATE only, READ ONLY) over the inputs a shared record
holds: every notehead GLYPH_BOX, ARC_BOX, STAFF_SPACING row, plus the record's own standing `glyph_owner` verdicts (so the heads
are grouped by the owner the record decided, exactly as the live decision reads them).  The pickle comes from
`arc_owner_extract.py` (ONE `record_io.load_record` per record).

  from arc_owner_replay import load, build_log, run_arcs
"""
from __future__ import annotations
import pickle, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.staged import adjudicate as A
import tools.omr.staged.adjudicators  # noqa: registers the decisions
from tools.omr.staged.record import Log, Outcome, Subject, Verdict, Q


def load(path):
    return pickle.load(open(path, "rb"))


def build_log(data, systems=None):
    """A `Log` of the arc-relevant rows (optionally only the given (page, system) pairs) + the record's glyph_owner verdicts."""
    log = Log()
    keep = (lambda subj: True) if systems is None else (
        lambda subj: tuple(subj.split("/")[1:3]) in systems)
    for o in data["obs"]:
        if not keep(o["subject"]):
            continue
        sub = Subject.from_key(o["subject"])
        log.observe(sub, o["quantity"], o["value"], reader=o["reader"], frame=o["frame"], score=o.get("score"),
                    **dict(o.get("detail") or {}))
    for v in data["verdicts"]:
        if v["quantity"] != "glyph_owner" or not keep(v["subject"]):
            continue
        log.record(Verdict(id=log._next_id("vrd"), subject=Subject.from_key(v["subject"]), quantity=v["quantity"],
                           outcome=Outcome(v["outcome"]), value=v.get("value"), decider=v.get("decider") or "x",
                           reason=v.get("reason") or "x"))
    return log


def run_arcs(log, arc_subjects, fn=None):
    """{arc subject: (outcome, value, reason, detail)} for each arc, through the REAL harness (`adjudicate_one`)."""
    spec = A.REGISTRY["arc_owner"] if "arc_owner" in A.REGISTRY else None
    if spec is None:
        raise SystemExit("arc_owner not in REGISTRY")
    out = {}
    for s in arc_subjects:
        sub = Subject.from_key(s)
        if fn is not None:
            import dataclasses
            spec2 = dataclasses.replace(spec, fn=fn)
        else:
            spec2 = spec
        v = A.adjudicate_one(log, spec2, sub)
        out[s] = (v.outcome.value if hasattr(v.outcome, "value") else str(v.outcome), v.value, v.reason, dict(v.detail))
    return out
