"""ROADMAP 2.58d -- replay library: rebuild the inputs of `adjudicate_glyph_owner` / `reconcile_group_owners` from the
`stem_owner_extract.py` pickle, optionally add `Q.HEAD_STEM_REACH` rows (from `stem_owner_measure.py`), and run the REAL
decision harness (`adjudicate.adjudicate_one`) over every contested head. GATHER+ADJUDICATE only; nothing written.
"""
from __future__ import annotations
import collections
import os
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from tools.omr.staged import adjudicate as A  # noqa: E402
import tools.omr.staged.adjudicators  # noqa: E402,F401  (registers the decisions)
from tools.omr.staged.adjudicators import ownership as OWN  # noqa: E402
from tools.omr.staged.record import (Candidate, Log, Outcome, Subject, Verdict, Q, READERS)  # noqa: E402

KEEP_VERDICTS = ("instrument", "clef", "ledger_is_not_a_ledger", "notehead_is_not_a_notehead")


def load(path):
    return pickle.load(open(path, "rb"))


def contested(data):
    """{head subject: page box} for every head with a `glyph_band_distance` row (the glyph_owner domain)."""
    dom = {o["subject"] for o in data["obs"] if o["quantity"] == "glyph_band_distance"}
    out = {}
    for o in data["obs"]:
        if o["quantity"] == "glyph_box" and o["subject"] in dom:
            bb = (o.get("detail") or {}).get("bbox_page_px")
            if bb and len(bb) == 4:
                out[o["subject"]] = tuple(float(v) for v in bb)
    return out


def staff_spacing(data):
    return {o["subject"]: float(o["value"]) for o in data["obs"] if o["quantity"] == "staff_spacing"}


def build_log(data, stems=None, pages=None):
    """A `Log` of every input row (optionally only `pages`), the kept verdicts, and, if given, the stem rows
    `{subject: measure_head_stem result}`."""
    log = Log()
    keep = (lambda s: True) if pages is None else (lambda s: int(s.split("/")[1]) in pages)
    for o in data["obs"]:
        if not keep(o["subject"]):
            continue
        log.observe(Subject.from_key(o["subject"]), o["quantity"], o["value"], reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **dict(o.get("detail") or {}))
    for a in data["abst"]:
        if not keep(a["subject"]):
            continue
        log.abstain(Subject.from_key(a["subject"]), a["quantity"], reader=a["reader"], frame=a["frame"],
                    reason=a["reason"], **dict(a.get("detail") or {}))
    for v in data["verdicts"]:
        if v["quantity"] not in KEEP_VERDICTS or v["_superseded"] or not keep(v["subject"]):
            continue
        log.record(Verdict(id=log._next_id("vrd"), subject=Subject.from_key(v["subject"]), quantity=v["quantity"],
                           outcome=Outcome(v["outcome"]), value=v.get("value"), decider=v.get("decider") or "x",
                           reason=v.get("reason") or "x", detail=dict(v.get("detail") or {}),
                           candidates=tuple(Candidate(c["value"], c["support"]) for c in v.get("candidates") or [])))
    for s, res in (stems or {}).items():
        if not keep(s):
            continue
        d = {k: v for k, v in res.items() if k != "direction"}
        log.observe(Subject.from_key(s), Q.HEAD_STEM_REACH, res["direction"], reader=READERS.CV_HEAD_STEM_REACH,
                    frame="page", **d)
    return log


def run_owner(log, heads, stem_on):
    """{head: (outcome, value, reason, detail)} through the real harness, flag set as asked."""
    spec = A.REGISTRY["glyph_owner"]
    old = os.environ.get(OWN.STEM_OWNER_ENV)
    os.environ[OWN.STEM_OWNER_ENV] = "1" if stem_on else "0"
    try:
        out = {}
        for s in heads:
            v = A.adjudicate_one(log, spec, Subject.from_key(s))
            out[s] = (v.outcome.value if hasattr(v.outcome, "value") else str(v.outcome), v.value, v.reason,
                      dict(v.detail))
    finally:
        if old is None:
            os.environ.pop(OWN.STEM_OWNER_ENV, None)
        else:
            os.environ[OWN.STEM_OWNER_ENV] = old
    return out


def record_owner_verdicts(data):
    """The record's own `glyph_owner` verdicts BY THE DECISION (not the group stage): {subject: (outcome, value, reason)}."""
    out = {}
    for v in data["verdicts"]:
        if v["quantity"] == "glyph_owner" and v.get("decider") == "adjudicate_glyph_owner" and not v["_superseded"]:
            out[v["subject"]] = (v["outcome"], v.get("value"), v.get("reason"))
    return out


def groups(data):
    """{mark group id: [member subjects]} from the `mark_group` rows."""
    g = collections.defaultdict(list)
    for o in data["obs"]:
        if o["quantity"] == "mark_group" and (o.get("detail") or {}).get("family") == "notehead":
            g[o["value"]].append(o["subject"])
    return dict(g)
