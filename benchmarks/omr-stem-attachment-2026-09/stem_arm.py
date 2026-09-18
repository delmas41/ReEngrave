"""ADJUDICATE TWICE OVER ONE GATHER — the beam-mate tier's fire set, exactly.

⚠️ WHY THIS EXISTS AND `omr-staged-duration-beams-2026-09/readjudicate.py` DOES
NOT SERVE. That harness is the right shape and it `json.load`s the record,
which on the 443 MB Breitkopf one is several gigabytes of Python objects --
`recordstream.py`'s own docstring says so, and *a probe that dies on the SECOND
publisher is a probe that can only ever confirm the first*. This rebuilds the
same `Log` from a STREAM, and reports `stem_direction` rather than `duration`.

⚠️ THE CONTROL RUNS THE OTHER WAY ROUND FROM THE USUAL ONE, and that is worth
reading before trusting a number here. Both shared records are PRE-tier --
`no_stem` 793 on Litolff, and no `beam_mate` verdict anywhere -- so
re-adjudicating UNCHANGED does **not** reproduce them; it is the arm. What
reproduces them is re-adjudicating with the beam-mate tier DISABLED. So
`--control` disables the tier and requires every `stem_direction` verdict to
come back identical. A control that cannot fail is not a control, so
`--positive-control` runs the same comparison WITHOUT disabling the tier and
requires it to DIFFER.

⚠️ WHAT IT IS BLIND TO. It isolates ADJUDICATE over a FIXED gather, so it
cannot see a GATHER change -- a new quantity, a new detail field, a changed
frame. That is not a footnote here: the attachment convention is a reading of
PIXELS, `Evidence` exposes only record rows, and no adjudicator in this tree
imports an image library. Any tier built on the convention therefore needs a
GATHER producer first, and **this harness would report `--control` clean across
that change and prove nothing about it.**

    python3 stem_arm.py <record.json> --control
    python3 stem_arm.py <record.json> --positive-control
    python3 stem_arm.py <record.json> --out out/<label>-verdicts.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0] / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                            # noqa: E402
from tools.omr.staged import adjudicate, evaluate                # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH           # noqa: E402

#: The quantities whose verdicts the beam-mate tier can move. `stem_direction`
#: is the tier's own; `event` and `voices` are its only two consumers
#: (`Q.EVENT` ORDER 21, `Q.VOICES` 22 -- both read it INSIDE adjudicate, which
#: is why the fourth stage cannot serve this quantity at all).
AFFECTED = ("stem_direction", "event", "voices")


def rebuild(path: str | Path) -> Log:
    """One `Log` holding exactly the saved record's GATHER rows, in id order.

    ⚠️ ID ORDER, not file order, and it is the same sort the duration harness
    does: observations and abstentions are two arrays in the record and the
    pipeline interleaved them, so replaying them apart would hand ADJUDICATE a
    log it never saw.
    """
    rows = [(r, "obs") for r in stream_array(path, "observations")]
    try:
        rows += [(r, "abs") for r in stream_array(path, "abstentions")]
    except KeyError:
        pass          # a record with no abstention array is legal, not empty
    rows.sort(key=lambda t: t[0]["id"])

    log = Log()
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


def disable_beam_mate() -> None:
    """Reproduce the PRE-tier behaviour exactly.

    ⚠️ Not "delete the feature": the pre-tier code fell straight through to
    `Ruling.abstain("no_stem")` when no stem met the head, which is what a
    borrow returning None does. Returning None is that same nothing, arrived
    at honestly.
    """
    RH._direction_from_a_beam_mate = lambda ev, cell, head_box, stems: None


def verdicts_of(log: Log, quantity: str) -> dict:
    return {v["subject"]: v for v in log.to_json()["verdicts"]
            if v["quantity"] == quantity}


def _saved(path: str | Path, quantity: str) -> dict:
    return {v["subject"]: v for v in stream_array(path, "verdicts")
            if v.get("quantity") == quantity}


def _same(a: dict, b: dict) -> bool:
    return (a.get("outcome") == b.get("outcome")
            and a.get("reason") == b.get("reason")
            and json.dumps(a.get("value"), sort_keys=True, default=str)
            == json.dumps(b.get("value"), sort_keys=True, default=str))


def compare(log: Log, path: str) -> tuple[int, int, int]:
    """Total / reproduced / differing, over every quantity the tier can move."""
    tot = same = diff = 0
    for q in AFFECTED:
        want, got = _saved(path, q), verdicts_of(log, q)
        kinds: collections.Counter = collections.Counter()
        for key, w in want.items():
            g = got.get(key)
            tot += 1
            if g is not None and _same(g, w):
                same += 1
            else:
                diff += 1
                kinds[f"{w.get('reason')} -> "
                      f"{'ABSENT' if g is None else g.get('reason')}"] += 1
        extra = len(got) - len(want)
        print(f"   {q:<16} {len(want):>6} saved, {len(want) - sum(kinds.values()):>6}"
              f" reproduced, {sum(kinds.values()):>5} differ, {extra:+d} extra")
        if kinds:
            for k, n in kinds.most_common(6):
                print(f"        {k}: {n}")
        diff += max(0, extra)
    return tot, same, diff


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--control", action="store_true",
                    help="disable the beam-mate tier; every verdict must match")
    ap.add_argument("--positive-control", action="store_true",
                    help="leave it on; the verdicts must DIFFER")
    ap.add_argument("--out", help="write per-subject stem_direction verdicts")
    a = ap.parse_args()

    if a.control:
        disable_beam_mate()
    log = rebuild(a.record)
    adjudicate.run(log)
    evaluate.run(log)

    sd = verdicts_of(log, "stem_direction")
    if not sd:
        print("DEAD: the rebuild produced no stem_direction verdict at all",
              file=sys.stderr)
        return 2
    reasons = collections.Counter(
        (v.get("outcome"), v.get("reason")) for v in sd.values())
    print(f"{Path(a.record).name}: {len(sd)} stem_direction verdicts")
    for k, n in reasons.most_common():
        print(f"   {k}: {n}")

    if a.control or a.positive_control:
        print("\n== against the saved record ==")
        tot, same, diff = compare(log, a.record)
        print(f"   TOTAL {same} of {tot} reproduced, {diff} differ")
        if a.control:
            if diff:
                print("\nFAILED: the tier-disabled rebuild does not reproduce "
                      "the record, so no arm over it means anything.",
                      file=sys.stderr)
                return 1
            print("\nCONTROL CLEAN")
            return 0
        if not diff:
            print("\nDEAD: the tier ON reproduces the record exactly, so the "
                  "control above has no teeth -- either the record is already "
                  "post-tier or the tier never fires.", file=sys.stderr)
            return 2
        print("\nPOSITIVE CONTROL: the arms differ, as they must")
        return 0

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"record": str(a.record),
             "verdicts": {k: {"outcome": v.get("outcome"),
                              "reason": v.get("reason"),
                              "value": v.get("value")}
                          for k, v in sd.items()}}, indent=1, default=str))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
