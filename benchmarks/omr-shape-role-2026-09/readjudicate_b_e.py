"""GATHER ONCE, ADJUDICATE TWICE — the 2.12b / 2.12e arm.

    python3 .../readjudicate_b_e.py <record.json> --control
    python3 .../readjudicate_b_e.py <record.json> --label <id> --out <json>

⚠️⚠️ **BASE AND ARM ARE BOTH REBUILT ON THIS TREE, AND THE RECORD IS NOT THE
BASELINE.** CLAUDE.md §6b: the committed verdicts of the shared records no
longer reproduce on today's tree, so a delta measured against the FILE would
be a measurement of every landing since it was gathered. `--off` restores the
two new rules to the nothing they produced before -- `_rest_slot_verdict`
returns `None` (no slot was ever computed) and `_flag_direction` returns `{}`
(no comparison was ever made) -- and everything else runs identically, so the
difference between the two runs is this lane and nothing else.

⚠️ `--control` is the half that CAN FAIL: it compares the `--off` rebuild
against the record's own `duration` verdicts and prints N of N. A number short
of N is not this lane's fault and is not hidden -- it is the tree having
moved, and it is printed before any delta so no delta can be read without it.

⚠️ **BLIND TO GATHER, like every tool of its shape.** It re-adjudicates ONE
saved record, so a change to what GATHER files is invisible to it and a zero
here is not evidence about one. Both lines are ADJUDICATE-only by
construction (`benchmarks/omr-shape-role-2026-09/FINDINGS.md` §5: *GATHER:
unchanged ... No re-gather*), which is exactly why this instrument is the
right one for them.

⚠️ The two arms are EXPORTED as well as adjudicated, because a duration that
narrows is a note that leaves the file and a bar whose sum changes, and
neither shows up in a verdict census.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate, infer          # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged import export as SX                         # noqa: E402
from tools.omr.staged.record import Log, Subject                  # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH            # noqa: E402


def rebuild(rec: dict) -> Log:
    """⚠️ `record_io.load_record` AND NOWHERE ELSE (CLAUDE.md §4b / 1.1b): a
    verdict's id lists are pooled in the file and a naive `json.load` iterates
    the strings `"$pool"` and `"ins"`."""
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


def _disable() -> None:
    """Return the two new rules to the nothing they produced before.

    ⚠️ NOT "delete the feature": with no slot verdict `_rest_ruling` falls
    through to exactly the class lookup it had, which is still there,
    unchanged, underneath; with no flag comparison the duration detail is the
    dict it always was.
    """
    RH._rest_slot_verdict = lambda name, step: None
    RH._flag_direction = lambda ev, flags: {}


def _run(rec: dict) -> Log:
    log = rebuild(rec)
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    return log


def _duration_verdicts(log: Log) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == "duration"}


def _summarise(log: Log) -> dict:
    """Everything this lane claims, read off ONE adjudicated log."""
    vs = _duration_verdicts(log)
    out = {
        "duration_outcomes": collections.Counter(
            v["outcome"] for v in vs.values()),
        "duration_reasons": collections.Counter(
            v.get("reason") for v in vs.values()),
        "rest_slot_says": collections.Counter(),
        "flag_direction_source": collections.Counter(),
        "flag_disagreements": 0,
        "flags_attached_total": 0,
    }
    for v in vs.values():
        d = v.get("detail") or {}
        if "slot_says" in d:
            out["rest_slot_says"][str(d.get("slot_says"))] += 1
        elif "slot" in d:
            out["rest_slot_says"][str(d.get("slot"))] += 1
        if d.get("flag_direction_source"):
            out["flag_direction_source"][d["flag_direction_source"]] += 1
        if d.get("detector_role_disagrees"):
            out["flag_disagreements"] += 1
        out["flags_attached_total"] += int(d.get("flags_attached") or 0)
    for k in ("duration_outcomes", "duration_reasons", "rest_slot_says",
              "flag_direction_source"):
        out[k] = dict(out[k])
    return out


def _export(log: Log) -> dict:
    """The file's own accounting, so a narrowed rest is priced and not just
    counted. ⚠️ `to_musicxml` RAISES `Unbalanced` rather than returning a
    flag, so a refusal that reaches one counter and not the other fails here
    loudly instead of being reported as a clean number."""
    xml, report = SX.to_musicxml({"record": log.to_json()})
    cov = SX.coverage({"record": log.to_json()},
                      written=report.get("written_by_family"))
    census = cov.get("status_census") or {}
    return {
        "notes": xml.count("<note"),
        "rests": xml.count("<rest"),
        "notes_not_written": report.get("notes_not_written") or {},
        "notes_not_written_total": report.get("notes_not_written_total"),
        # ⚠️ `to_musicxml` RAISES on an imbalance, so reading `False` here is
        # impossible; the key is carried anyway so a future change that
        # downgrades the raise to a flag cannot pass unnoticed.
        "balance": report.get("balance") or {},
        "census_unaccounted": census.get("unaccounted"),
        "census_balanced": census.get("balanced"),
        "bars_held_out": (report.get("notes_not_written") or {}).get(
            "bar_does_not_add_up"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="?")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    loaded = load_record(a.record)
    rec = loaded["record"]
    prov = loaded.get("provenance") or {}

    def control(log: Log) -> dict:
        got = _duration_verdicts(log)
        want = {v["subject"]: v for v in rec["verdicts"]
                if v["quantity"] == "duration"}
        same = diff = 0
        kinds: collections.Counter = collections.Counter()
        for key, w in want.items():
            g = got.get(key)
            if g is None:
                kinds["absent from the rebuild"] += 1
                diff += 1
                continue
            if (g["outcome"] == w["outcome"]
                    and g.get("value") == w.get("value")):
                same += 1
            else:
                diff += 1
                kinds["%s -> %s" % (w["outcome"], g["outcome"])] += 1
        print("CONTROL duration: %d of %d reproduced (outcome+value), "
              "%d differ, %+d extra"
              % (same, len(want), diff, len(got) - len(want)), flush=True)
        if kinds:
            print("   differ:", kinds.most_common(8), flush=True)
        return {"reproduced": same, "on_the_record": len(want),
                "differ": diff, "extra": len(got) - len(want),
                "kinds": dict(kinds.most_common(8))}

    # ⚠️ THE CONTROL IS THE BASE RUN, NOT A THIRD ONE. `--control` and `--off`
    # disable exactly the same two rules and re-adjudicate exactly the same
    # log, so running them separately would be one 30-minute re-adjudication
    # of a 478 MB record spent reproducing a number the base run already has.
    if a.off or a.control:
        _disable()
    log = _run(rec)
    if a.control or a.off:
        ctrl = control(log)
        if a.control:
            return 0 if ctrl["differ"] == 0 and ctrl["extra"] == 0 else 1
    else:
        ctrl = None
    res = {"label": a.label, "record": a.record, "arm": "off" if a.off else "on",
           "provenance": {"commit": prov.get("commit"),
                          "dirty": prov.get("dirty")},
           "control": ctrl,
           "adjudicate": _summarise(log), "export": _export(log)}
    text = json.dumps(res, indent=1, default=str)
    if a.out:
        pathlib.Path(a.out).write_text(text)
        print("wrote", a.out)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
