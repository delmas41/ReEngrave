"""GATHER ONCE, ADJUDICATE TWICE — the key-signature arm of roadmap 2.9.

    python3 .../readjudicate.py <record.json> --control
    python3 .../readjudicate.py <record.json> --off all   --out /tmp/base.json
    python3 .../readjudicate.py <record.json>             --out /tmp/arm.json

⚠️ THE CONTROL IS IN TWO HALVES BECAUSE ONE OF THEM CANNOT FAIL ALONE.

  * `clef` is NOT under test, so the rebuild must reproduce every clef verdict
    the pipeline wrote, exactly. That half proves the REBUILD — a mismatch
    there means the log was reassembled wrongly and every later number is a
    measurement of this harness.
  * `key_signature` with `--off all` must reproduce every VALUE the record
    holds. `--off` restores the old behaviour by making the two new readers
    return nothing, which is what they DID before they existed. ⚠️ The REASON
    words legitimately differ (`fitted` / `fitted_by_template` /
    `fitted_by_template_engraved` are now one `fitted_no_markers`, and
    `markers_without_a_run` is gone), so the control compares outcome and
    value and prints the reason movement separately rather than calling it a
    failure.

⚠️ BLIND TO GATHER, like every tool of its shape: it re-adjudicates ONE saved
record, so a change to what GATHER files is invisible to it and a zero here
is not evidence about one. The marker rows this item reads were already being
gathered, which is exactly why this instrument is the right one.

⚠️ `--out` writes `{"record": ...}` and no provenance stamp; it is an input to
`staged.export`, never a baseline.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate, infer          # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                  # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402
from tools.omr.staged.adjudicators import header as H             # noqa: E402


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


def _disable(which: str) -> None:
    """Return the two new readers to the nothing they produced before.

    ⚠️ NOT "delete the feature": with no marker run and no concert key, the
    decision falls through to exactly the header precedence it had, which is
    still there, unchanged, underneath.
    """
    if which in ("markers", "all"):
        H._marker_run = lambda marks, space: (None, "no_markers", {})
    if which in ("system", "all"):
        H._concert = lambda ev, subject, written: (None, None)
    if which in ("part", "all"):
        # ⚠️ ROADMAP 2.9b. ONE flag over both halves — `_part_checked` reads
        # the same predicate the INFER rule's switch does, so this returns the
        # decision to exactly 2.9's behaviour rather than to a half-state no
        # shipped tree has been in.
        os.environ["OMR_PART_KEY"] = "0"


def verdicts_of(log: Log, quantity: str) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == quantity}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--off", choices=["markers", "system", "part", "all"],
                    default=None)
    ap.add_argument("--out")
    a = ap.parse_args()

    rec = load_record(a.record)["record"]
    if a.control:
        a.off = "all"
    if a.off:
        _disable(a.off)
    log = rebuild(rec)
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    # ⚠️⚠️ THE SECOND EVALUATE PASS, AND THIS HARNESS WAS MISSING IT — WHICH
    # `staged/pipeline.py` HAS RUN SINCE ROADMAP 2.10. Measured 2026-09-23 on
    # the Litolff arm before this line existed: **186 staves with an inferred
    # key and ZERO key-derived `Q.ACCIDENTAL` verdicts beneath any of them**,
    # while the 142 read keys carried 1,099. An inference that changes nothing
    # downstream is inert in exactly the way that looks like a clean result,
    # and the arm was reporting the file it would produce WRONG — fewer
    # `<alter>`s than the base, from a rule that decides more keys.
    #
    # ⚠️ It is the one line that makes this harness's exported MusicXML the
    # same file the pipeline would write. `run_over` is bounded to the
    # consequences of what INFER wrote, so it is not a second full pass.
    evaluate.run_over(log, infer.inferred_verdicts(log))

    if a.control:
        bad = 0
        for quantity in ("clef", "key_signature"):
            got = verdicts_of(log, quantity)
            want = {v["subject"]: v for v in rec["verdicts"]
                    if v["quantity"] == quantity}
            same = diff = 0
            kinds: collections.Counter = collections.Counter()
            moved: collections.Counter = collections.Counter()
            for key, w in want.items():
                g = got.get(key)
                if g is None:
                    kinds["absent from the rebuild"] += 1
                    diff += 1
                    continue
                if g["outcome"] == w["outcome"] and g.get("value") == w.get("value"):
                    same += 1
                    if g.get("reason") != w.get("reason"):
                        moved[f"{w.get('reason')} -> {g.get('reason')}"] += 1
                else:
                    diff += 1
                    kinds[f"{w.get('value')}({w['outcome']}) -> "
                          f"{g.get('value')}({g['outcome']})"] += 1
            extra = len(got) - len(want)
            print(f"CONTROL {quantity}: {same} of {len(want)} reproduced "
                  f"(outcome+value), {diff} differ, {extra:+d} extra")
            if kinds:
                print("   differ:", kinds.most_common(8))
            if moved:
                print("   reason moved (value unchanged):", moved.most_common(8))
            bad += diff + abs(extra)
        return 0 if bad == 0 else 1

    keys = verdicts_of(log, "key_signature")
    sysk = verdicts_of(log, "system_key")
    print("key_signature:",
          collections.Counter(v["outcome"] for v in keys.values()).most_common())
    print("reasons:",
          collections.Counter(v.get("reason") for v in keys.values()).most_common())
    print("system_key:",
          collections.Counter(v.get("reason") for v in sysk.values()).most_common())
    if a.out:
        pathlib.Path(a.out).write_text(
            json.dumps({"record": log.to_json()}, indent=1, default=str))
        print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
