"""Does dotting a REST change anything a page did not ask it to?

GATHER ONCE, ADJUDICATE TWICE, over a saved record — `readjudicate.py`'s
harness, imported rather than copied, so the two arms differ only in the rule
under test and carry no detector jitter.

⚠️ THE CHANGE IS ADJUDICATE-ONLY, WHICH IS WHY THIS INSTRUMENT CAN SEE IT.
`readjudicate` states its own blind spot: it rebuilds a `Log` from a SAVED
record, so a GATHER change never enters and `--control` would pass whatever it
did. `_rest_ruling` reading its dots from the CELL instead of from the rest's
own glyph subject touches no gathered row, so this is the right tool. (The
sibling arc work in the same session DOES change GATHER — `Q.CELL_BOX` — and
must not be measured here.)

⚠️ TWO ARMS AND TWO QUESTIONS, kept apart because a single total would hide the
second. (1) Do RESTS gain dots — the fix's purpose. (2) Do NOTEHEADS lose any —
the cost, which exists because widening the target pool to `noteheads + rests`
lets a rest win a dot a notehead used to take. The second is the one nobody
asked about, and it is the one this file exists to answer.

    python3 rest_dot_arm.py <staged.json>
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1] / "omr-staged-duration-beams-2026-09"))

import json                                                    # noqa: E402
import readjudicate as RJ                                      # noqa: E402
from tools.omr.staged import adjudicate                        # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH         # noqa: E402
from tools.omr.staged.record import Q                          # noqa: E402


def _arm(rec, *, old_rest_dots: bool):
    """One re-adjudication. `old_rest_dots` restores the pre-fix read."""
    keep_pool, keep_rest = RH._attached_dots, RH._rest_ruling
    if old_rest_dots:
        # ⚠️ THE OLD BEHAVIOUR, REPRODUCED RATHER THAN DELETED. `_rest_ruling`
        # asked the REST's own glyph subject for `Q.AUG_DOT`, and gather files
        # a dot on the DOT's glyph — so it found nothing. Returning nothing is
        # that same nothing, arrived at honestly, which is `_disable`'s rule.
        def _no_rest_dots(ev, cell, head_box, space):
            if ev.rows(Q.REST):
                return []
            return keep_pool(ev, cell, head_box, space)
        RH._attached_dots = _no_rest_dots
    try:
        log = RJ.rebuild(rec)
        adjudicate.run(log)
        return RJ.durations(log)
    finally:
        RH._attached_dots, RH._rest_ruling = keep_pool, keep_rest


def _reach(rec) -> dict:
    """What this document can even SHOW, measured before any arm is read.

    ⚠️⚠️ A CLEAN ZERO IS NOT A RESULT UNTIL THIS IS PRINTED BESIDE IT. This
    repo has a recorded case of "a clean, believable zero that was the shell",
    and the shape recurs: a change that moves nothing because it is inert and
    one that moves nothing because the page holds nothing to move are the same
    number. A dot the detector never fired cannot be reattached by any rule.
    """
    obs = rec["observations"]
    cell = lambda s: "/".join(s.split("/")[1:5])              # noqa: E731
    rest_cells = {cell(o["subject"]) for o in obs if o["quantity"] == "rest"}
    dots = [cell(o["subject"]) for o in obs if o["quantity"] == "aug_dot"]
    return {"aug_dot rows": len(dots),
            "rest rows": sum(1 for o in obs if o["quantity"] == "rest"),
            "dots in a cell that holds a rest": sum(
                1 for c in dots if c in rest_cells)}


def _kind(rec) -> dict:
    """`subject -> "rest" | "note"`, off the gathered rows, not the verdicts."""
    rests = {o["subject"] for o in rec["observations"] if o["quantity"] == "rest"}
    return {o["subject"]: ("rest" if o["subject"] in rests else "note")
            for o in rec["observations"]
            if o["quantity"] in ("rest", "notehead_class")}


def main() -> int:
    rec = json.load(open(sys.argv[1]))["record"]
    print("REACH (what this document can show):")
    for k, v in _reach(rec).items():
        print(f"  {k:34s} {v}")
    print()
    kind = _kind(rec)
    new = _arm(rec, old_rest_dots=False)
    old = _arm(rec, old_rest_dots=True)

    if "--positive-control" in sys.argv:
        # ⚠️ THE INSTRUMENT MUST BE SHOWN CAPABLE OF REPORTING MOVEMENT ON
        # THIS RECORD, or a zero above is indistinguishable from a probe that
        # compares a file with itself. Disabling dots for NOTEHEADS is a
        # change this document DOES hold ink for, so it must move -- and if it
        # does not, the zero above says nothing about the rule under test.
        keep = RH._attached_dots
        RH._attached_dots = lambda ev, cell, head_box, space: []
        try:
            none_at_all = _arm(rec, old_rest_dots=False)
        finally:
            RH._attached_dots = keep
        n = sum(1 for s_, v in none_at_all.items()
                if v["value"] != new[s_]["value"])
        # ⚠️ THE COUNT IS THE PROBE'S WHOLE DYNAMIC RANGE ON THIS DOCUMENT,
        # AND IT IS REPORTED AS SUCH RATHER THAN AS A PASS. "Live" only rules
        # out a probe comparing a file with itself; a control that can move n
        # verdicts cannot detect a regression smaller than n, so quoting it as
        # a clean bill of health would be the second mistake in the same
        # place. On Litolff p1-3, n is ONE.
        verdict = ("INSTRUMENT DEAD — ignore every number above" if not n
                   else f"instrument LIVE, and its WHOLE RANGE here is {n} "
                        f"verdict{'s' if n != 1 else ''}: this rules out a "
                        f"dead probe and establishes nothing more")
        print(f"POSITIVE CONTROL — with ALL dots off, {n} verdicts move "
              f"({verdict})\n")

    print(f"subjects with a duration: old {len(old)}  new {len(new)}")
    # ⚠️ THE CONTROL COMES FIRST. If the two arms disagree about which
    # subjects exist at all, the comparison below is between two different
    # populations and every number after it is a measurement of the harness.
    if set(old) != set(new):
        print("!! the arms cover different subjects — STOP")
        return 2

    moved = Counter()
    dots_gained = Counter()
    for sub, nv in new.items():
        ov = old[sub]
        k = kind.get(sub, "?")
        if ov["outcome"] != nv["outcome"] or ov["value"] != nv["value"]:
            moved[k] += 1
            od = (ov["value"] or {}).get("dots") if isinstance(ov["value"], dict) else None
            nd = (nv["value"] or {}).get("dots") if isinstance(nv["value"], dict) else None
            if (nd or 0) > (od or 0):
                dots_gained[k] += 1
            elif (nd or 0) < (od or 0):
                dots_gained[k + " LOST"] += 1
    print(f"\nverdicts that MOVED, by kind : {dict(moved) or 'none'}")
    print(f"  of those, dots gained      : {dict(dots_gained) or 'none'}")
    print("\ndotted verdicts, old -> new:")
    for k in ("rest", "note"):
        f = lambda d: sum(1 for s, v in d.items() if kind.get(s) == k       # noqa: E731
                          and isinstance(v["value"], dict) and v["value"].get("dots"))
        print(f"  {k:5s}: {f(old)} -> {f(new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
