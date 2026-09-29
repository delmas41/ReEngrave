"""ROADMAP 2.6d — manager's pre-merge check: because `ledger_direction` is
now a HARD GATE, one false CV rung decides a note's staff outright. Lists
EVERY `glyph_owner` / `belongs_to_a_nearer_staff` verdict that changes
BASE (no CV reader at all) -> ARM (the current tree, CV merged in), from
ONE saved record -- no re-gather (`review.rerun.rebuild_gather` replays the
record's own GATHER rows; BASE is the same replay with every
`ledger_rung_ink` row dropped before it).

    python3 benchmarks/omr-owner-domain-2026-09/verify_cv_rungs_2_6d.py \
        <record.json> --out <summary.json>
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.getcwd())

from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401
from tools.omr.staged.record import (  # noqa: E402
    Candidate, Outcome, Q, Subject, Verdict)
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather  # noqa: E402

INJECT = (Q.LEDGER_IS_NOT_A_LEDGER, Q.INSTRUMENT, Q.CLEF)
SEED = 2026092901


def _outcome(v):
    return {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED,
            "abstained": Outcome.ABSTAINED}[v["outcome"]]


def _build_log(rec: dict, *, drop_cv: bool) -> "A.Log":
    if drop_cv:
        rec = dict(rec)
        rec["observations"] = [r for r in (rec.get("observations") or ())
                               if r["quantity"] != Q.LEDGER_RUNG_INK]
        rec["abstentions"] = [r for r in (rec.get("abstentions") or ())
                              if r["quantity"] != Q.LEDGER_RUNG_INK]
    log, _ids = rebuild_gather(rec)
    log.freeze()
    superseded = {v.get("supersedes") for v in rec["verdicts"]
                 if v.get("supersedes")}
    for v in rec["verdicts"]:
        if v["id"] in superseded or v["quantity"] not in INJECT:
            continue
        log.record(Verdict(
            id=log._next_id("vrd"), subject=Subject.from_key(v["subject"]),
            quantity=v["quantity"], outcome=_outcome(v), value=v["value"],
            decider=v["decider"], reason=v["reason"],
            candidates=tuple(Candidate(c["value"], c["support"])
                             for c in (v.get("candidates") or ()))))
    A._ensure_decisions()
    return log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    rec = load_record(a.record)["record"]
    arm_log = _build_log(rec, drop_cv=False)
    base_log = _build_log(rec, drop_cv=True)

    owner_spec = A.REGISTRY[Q.GLYPH_OWNER]
    np_spec = A.REGISTRY[Q.NOTEHEAD_IS_NOT_A_NOTEHEAD]

    # every contested glyph (glyph_owner's own domain)
    contested = sorted({r["subject"] for r in rec["observations"]
                        if r["quantity"] == Q.GLYPH_BAND_DISTANCE})
    owner_changed = []
    for key in contested:
        sub = Subject.from_key(key)
        b = A.adjudicate_one(base_log, owner_spec, sub)
        v = A.adjudicate_one(arm_log, owner_spec, sub)
        if (b.outcome.value, b.value, b.reason) != (v.outcome.value, v.value,
                                                     v.reason):
            owner_changed.append({
                "subject": key,
                "base": [b.outcome.value, b.value, b.reason],
                "arm": [v.outcome.value, v.value, v.reason],
                "arm_ledger": (v.detail or {}).get("ledger")})

    # every notehead with a filed-far signal (2.7b's own reach)
    far_heads = sorted({r["subject"] for r in rec["observations"]
                        if r["quantity"] == Q.NOTEHEAD_CLASS})
    np_changed = []
    for key in far_heads:
        sub = Subject.from_key(key)
        b = A.adjudicate_one(base_log, np_spec, sub)
        v = A.adjudicate_one(arm_log, np_spec, sub)
        bsig = (b.detail or {}).get("nearer_staff_signal") or {}
        vsig = (v.detail or {}).get("nearer_staff_signal") or {}
        if not bsig and not vsig:
            continue
        if (b.value, b.reason) != (v.value, v.reason):
            np_changed.append({
                "subject": key,
                "base": [b.value, b.reason],
                "arm": [v.value, v.reason],
                "arm_ledger": vsig.get("ledger")})

    # the found=True CV rows that changed NOTHING -- a random 10
    cv_true = [r for r in rec["observations"]
              if r["quantity"] == Q.LEDGER_RUNG_INK and r["value"] is True]
    changed_subjects = {c["subject"] for c in owner_changed} | \
        {c["subject"] for c in np_changed}
    unchanged_true = [r for r in cv_true if r["subject"] not in changed_subjects]
    rng = random.Random(SEED)
    rng.shuffle(unchanged_true)
    sample_unchanged = unchanged_true[:10]

    out = {
        "record": a.record,
        "cv_rows_found_true": len(cv_true),
        "owner_verdicts_changed": owner_changed,
        "nearer_staff_verdicts_changed": np_changed,
        "sample_unchanged_true": [
            {"subject": r["subject"], "detail": r["detail"]}
            for r in sample_unchanged],
    }
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"owner changed: {len(owner_changed)}  "
          f"nearer_staff changed: {len(np_changed)}  "
          f"cv_true: {len(cv_true)}  sampled_unchanged: {len(sample_unchanged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
