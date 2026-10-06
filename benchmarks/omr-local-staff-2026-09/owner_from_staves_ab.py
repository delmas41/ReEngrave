"""lane-owner-from-staves (2026-10-06): re-decide `glyph_owner` on a SAVED record with the staves tier OFF and ON,
on ONE tree (CLAUDE.md §6b: base vs arm on one tree; no gather). Writes every subject's saved / off / on verdict.

    python3 benchmarks/omr-local-staff-2026-09/owner_from_staves_ab.py REC.record.json OUT.json

Control that can fail: the OFF arm must reproduce the record's own saved `glyph_owner` verdicts (`reproduced`); an arm
that moved nothing and one that never ran are the same number, so the ON arm prints its own reach first and exits
non-zero (DEAD) at zero.
"""
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.getcwd())

from tools.omr.staged import adjudicate as A  # noqa: E402
from tools.omr.staged import adjudicators  # noqa: E402,F401
from tools.omr.staged.adjudicators import ownership as O  # noqa: E402
from tools.omr.staged.record import Candidate, Outcome, Q, Subject, Verdict  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review.rerun import rebuild_gather  # noqa: E402

INJECT = (Q.LEDGER_IS_NOT_A_LEDGER, Q.INSTRUMENT, Q.CLEF)
_O = {"decided": Outcome.DECIDED, "narrowed": Outcome.NARROWED, "abstained": Outcome.ABSTAINED}


def summarise(v):
    d = v.detail or {}
    return dict(outcome="decided" if v.value is not None else "abstained", value=v.value, reason=v.reason,
                measured=d.get("measured"), owner_box=d.get("owner_box"),
                staff_band=d.get("staff_band"))


def main(path, out_path, only=None):
    t0 = time.time()
    rec = load_record(path)["record"]
    known = {v for k, v in vars(Q).items() if isinstance(v, str) and not k.startswith("_")}
    drop = sorted({r["quantity"] for r in rec["observations"] + rec["abstentions"]} - known)
    if drop:
        # an older record may carry a quantity this tree no longer spells (the truth-set records do); say which
        print("dropping quantities this tree does not know:", drop)
        rec = dict(rec)
        rec["observations"] = [o for o in rec["observations"] if o["quantity"] in known]
        rec["abstentions"] = [a for a in rec["abstentions"] if a["quantity"] in known]
    if os.environ.get("AB_DROP_OWNER_LEDGERS") == "1":
        # the DEFAULT tree: `OMR_FARHEAD_OWNER_LEDGERS` is OFF there, so no `Q.FAR_HEAD_OWNER_LEDGER` row is ever
        # filed; the 10-06 records were gathered with it ON. Dropping the rows makes the OFF arm what a default
        # gather would have decided (it no longer reproduces the saved verdicts, by design).
        rec = dict(rec)
        rec["observations"] = [o for o in rec["observations"] if o["quantity"] != Q.FAR_HEAD_OWNER_LEDGER]
        rec["abstentions"] = [a for a in rec["abstentions"] if a["quantity"] != Q.FAR_HEAD_OWNER_LEDGER]
    log, _ids = rebuild_gather(rec)
    log.freeze()
    superseded = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    current = {}
    for v in rec["verdicts"]:
        if v["id"] not in superseded:
            current[(v["quantity"], v["subject"])] = v
    saved = {}
    for (q, key), v in current.items():
        if q in INJECT:
            log.record(Verdict(
                id=log._next_id("vrd"), subject=Subject.from_key(key), quantity=q, outcome=_O[v["outcome"]],
                value=v["value"], decider=v["decider"], reason=v["reason"],
                candidates=tuple(Candidate(c["value"], c["support"]) for c in (v.get("candidates") or ()))))
        elif q == Q.GLYPH_OWNER:
            saved[key] = v
    A._ensure_decisions()
    spec = A.REGISTRY[Q.GLYPH_OWNER]
    # a re-decision must not be RECORDED (the log refuses a second adjudication): call the decision body on its own
    # declared evidence, exactly as `adjudicate_one` does, and read the Ruling
    def rule(sub):
        r = spec.fn(A.Evidence(log, sub, spec))
        assert r.reason in spec.reasons, r.reason
        return r
    res = {}
    reproduced = 0
    keys = sorted(saved) if only is None else [k for k in only if k in saved]
    for key in keys:
        sub = Subject.from_key(key)
        os.environ.pop(O.FROM_STAVES_ENV, None)
        off = rule(sub)
        os.environ[O.FROM_STAVES_ENV] = "1"
        on = rule(sub)
        os.environ.pop(O.FROM_STAVES_ENV, None)
        s = saved[key]
        if (s["value"], s["reason"]) == (off.value, off.reason):
            reproduced += 1
        res[key] = dict(saved=[s["outcome"], s["value"], s["reason"]], off=summarise(off), on=summarise(on))
    n = len(keys)
    moved = [k for k, r in res.items() if r["off"]["value"] != r["on"]["value"]]
    reason_on = Counter(r["on"]["reason"] for r in res.values())
    banded = sum(v for k, v in reason_on.items() if k in ("staff_band", "staff_band_no_box"))
    out = dict(record=path, subjects=n, reproduced=reproduced, owner_changed=len(moved),
               tier_fired=banded, reasons_on=dict(reason_on),
               transitions=dict(Counter(f"{res[k]['off']['reason']}->{res[k]['on']['reason']}" for k in moved)),
               seconds=round(time.time() - t0, 1), results=res)
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"subjects {n}  OFF reproduces saved {reproduced}/{n}")
    print(f"tier fired {banded} ({reason_on.get('staff_band', 0)} staff_band, "
          f"{reason_on.get('staff_band_no_box', 0)} staff_band_no_box)")
    print(f"owner changed OFF->ON: {len(moved)}")
    for k, v in sorted(out["transitions"].items(), key=lambda kv: -kv[1]):
        print(f"   {v:5d}  {k}")
    if banded == 0:
        print("DEAD: the tier fired on nothing")
        sys.exit(3)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
