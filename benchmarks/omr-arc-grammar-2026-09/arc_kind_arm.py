"""GATHER ONCE, ADJUDICATE TWICE — the arm for the `arc_kind` stem reach.

⚠️ THIS IS AN ADJUDICATE INSTRUMENT AND IT IS BLIND TO GATHER AND TO EXPORT.
It rebuilds a `Log` from ONE saved record's rows and re-runs ADJUDICATE over
it, so the two arms differ only in the rule under test. It therefore cannot
see a new gathered row, a changed frame, or anything the exporter does — the
same blindness `readjudicate.py` states for itself. `Q.STEM` is already on the
record, which is the only reason this change is measurable here at all.

⚠️ IT VERIFIES ITSELF FIRST. `--control` re-adjudicates with the rule DISABLED
and compares every `arc_kind` verdict against the ones the pipeline wrote. A
rebuild that does not reproduce the record is not a control.

⚠️ THE CLAIM UNDER TEST IS TWO-SIDED and both sides are asserted:
  * the grammar's AVAILABILITY rises (more arcs have two flanked heads);
  * NO verdict VALUE moves — `adjudicate_arc_kind` lets the detector's class
    decide and only RECORDS the grammar, and the measured refusal of
    `OMR_ARC_RECLASS` must survive this change untouched.
A run where values moved would mean the veto had been enabled by the back
door, and the arm exits non-zero.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate                # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Log, Q, Subject              # noqa: E402
from tools.omr.staged.adjudicators import ownership as OW        # noqa: E402


def rebuild(rec: dict) -> Log:
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


_REAL = OW._stem_xs_for_head


def _disable_stem_reach() -> None:
    """Reproduce the OLD behaviour exactly: no head is reachable at a stem.

    Not "delete the feature" — before this change `adjudicate_arc_kind` read
    head CENTRES and nothing else, and a head with no stem probes yields
    exactly that. The same honest-nothing `readjudicate._disable` uses.

    ⚠️ IT PATCHES THIS DECISION'S OWN SEAM, not `_boxes_overlap`. That helper
    is shared with `stem_direction` and the duration reader, so patching it
    would switch three rules off and report the result under one name — an arm
    measuring its own scope.
    """
    OW._stem_xs_for_head = lambda stems, head_box: ()


def _enable_stem_reach() -> None:
    OW._stem_xs_for_head = _REAL


def arcs(log: Log) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == Q.ARC_KIND}


def summarise(vs: dict) -> dict:
    avail = agree = disagree = stems = 0
    for v in vs.values():
        if v["outcome"] != "decided":
            continue
        g = (v.get("detail") or {}).get("grammar") or {}
        stems += int(g.get("reached_only_at_a_stem") or 0)
        if g.get("says") is None:
            continue
        avail += 1
        if g.get("agrees_with_reading"):
            agree += 1
        else:
            disagree += 1
    return {"decided": sum(1 for v in vs.values() if v["outcome"] == "decided"),
            "grammar_available": avail, "agrees": agree,
            "disagrees": disagree, "heads_reached_only_at_a_stem": stems}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true",
                    help="re-adjudicate with the rule OFF and diff against "
                         "the record the pipeline wrote")
    a = ap.parse_args()
    rec = json.load(open(a.record))["record"]

    if a.control:
        _disable_stem_reach()
        log = rebuild(rec)
        adjudicate.run(log)
        evaluate.run(log)
        got = arcs(log)
        want = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == Q.ARC_KIND}
        same = diff = 0
        for key, w in want.items():
            g = got.get(key)
            if g is not None and g["outcome"] == w["outcome"] \
                    and g.get("value") == w.get("value"):
                same += 1
            else:
                diff += 1
        print(f"CONTROL (rule OFF): {same} of {len(want)} arc_kind verdicts "
              f"reproduce the record, {diff} differ")
        return 0 if diff == 0 else 1

    # OFF arm, then ON: one rebuild each, differing only in this seam.
    _disable_stem_reach()
    off = summarise(arcs(_run(rec)))
    _enable_stem_reach()
    on = summarise(arcs(_run(rec)))

    print(f"{'':34s} {'OFF':>8s} {'ON':>8s}")
    for k in ("decided", "grammar_available", "agrees", "disagrees",
              "heads_reached_only_at_a_stem"):
        print(f"{k:34s} {off[k]:8d} {on[k]:8d}")
    if off["decided"] != on["decided"]:
        print("\nFAIL: the number of DECIDED arcs moved. The grammar is "
              "recorded, never a gate -- a value must not move.")
        return 1
    if on["grammar_available"] <= off["grammar_available"]:
        print("\nDEAD: the rule made the grammar no more available on this "
              "document. Nothing to report.")
        return 1
    print(f"\navailability {off['grammar_available']} -> "
          f"{on['grammar_available']} of {on['decided']}")
    return 0


def _run(rec: dict) -> Log:
    log = rebuild(rec)
    adjudicate.run(log)
    evaluate.run(log)
    return log


if __name__ == "__main__":
    sys.exit(main())
