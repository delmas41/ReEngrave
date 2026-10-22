"""SEAN'S RULE: WHERE THE NOTE FALLS AGAINST THE MIDDLE LINE NAMES THE STEM.

Sean, 2026-09-17: *"the stem rules ... are very consistent unless there are
multiple voices per staff. If it is just one voice, where the note falls
compared to the middle line of the staff determines direction."*

⚠️ THE RULE AND ITS EXCEPTION ARE ONE STATEMENT, and the exception is the
whole design problem. On a single-voice staff a note above the middle line
takes a stem DOWN and one below takes it UP; in two voices the convention is
abolished -- the upper voice is stems-UP throughout and the lower stems-DOWN,
whatever the pitch. So a rule that cannot tell the two apart is right most of
the time and confidently wrong exactly where a bar has two voices, which is
the population `adjudicate_event`'s divisi guard and `Q.VOICES` exist to keep
straight.

⚠️⚠️ AND `Q.VOICES` CANNOT BE THE GATE: it is ORDER 22 and `stem_direction`
is 17, so asking it would read `None` -- and it is DERIVED FROM the stem
directions, so even if the order allowed it the gate would be circular.

So the gate measured here is the BAR'S OWN STEMMED HEADS. Every head whose
direction a stem already decided is a test of whether the convention holds in
this bar: if all of them obey it, the bar behaves as one voice and the rule
may speak for the heads that have no stem; if any contradicts it, the bar is
two-voiced (or misread) and the rule stays quiet. That is the document
telling us whether its own convention applies, and it needs nothing that runs
later.

⚠️ SCORED LEAVE-ONE-OUT: a head is never part of the evidence that decides it.

⚠️ AND AN UPPER BOUND, as always here: a head with no stem is a head whose ink
the CV rung could not read, so an accuracy measured on heads WITH one is a
ceiling for the same rule applied to heads without.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record import Kind, Subject              # noqa: E402

#: The middle line of a five-line staff, in half-spaces DOWN FROM THE TOP
#: LINE -- which is the unit `gather` files `Q.NOTEHEAD_STAFF_POSITION` in
#: (`(y_center - top_y) / half_step`, so the lines are 0, 2, 4, 6, 8).
#:
#: ⚠️ NOT A TUNED CONSTANT AND NOT A THRESHOLD. It is where the third line is.
MIDDLE_LINE = 4.0


def position_says(pos):
    """The direction the convention gives a head at `pos`.

    ⚠️ A NOTE ON THE MIDDLE LINE TAKES A STEM DOWN by convention, and it is
    the one value where engravers genuinely differ -- so it is scored apart
    below rather than folded in.
    """
    if pos < MIDDLE_LINE:
        return "down"
    if pos > MIDDLE_LINE:
        return "up"
    return "down"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "position-rule.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    print(f"record provenance: {doc.get('provenance')}")

    pos_of = {}
    for o in rec["observations"]:
        if o["quantity"] == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    decided = {v["subject"]: v["value"] for v in verdicts
               if v["outcome"] == "decided"}
    no_stem = [v["subject"] for v in verdicts if v["reason"] == "no_stem"]
    print(f"\nstaff positions on the record: {len(pos_of)}")
    print(f"held-out answers (decided by a stem): {len(decided)}")
    print(f"heads with no stem: {len(no_stem)}")
    if not pos_of:
        print("⚠️ NOT ONE POSITION READ — every zero below is this probe's "
              "key, not the page.", file=sys.stderr)
        return 2

    def cell(k):
        return Subject.from_key(k).at(Kind.CELL).to_key()

    in_cell = collections.defaultdict(list)
    for sub in decided:
        in_cell[cell(sub)].append(sub)

    # ── 1. the bare convention, scored on every head a stem decided ─────────
    tally = collections.Counter()
    on_line = collections.Counter()
    for sub, want in decided.items():
        pos = pos_of.get(sub)
        if pos is None:
            continue
        got = position_says(pos)
        tally["right" if got == want else "wrong"] += 1
        if abs(pos - MIDDLE_LINE) < 1e-9:
            on_line["right" if got == want else "wrong"] += 1
    n = tally["right"] + tally["wrong"]
    print(f"\n── 1. THE BARE CONVENTION, on all {n} decided heads")
    print(f"   right {tally['right']}   wrong {tally['wrong']}   "
          f"accuracy {tally['right'] / max(1, n):.3f}")
    print(f"   of those, ON the middle line: right {on_line['right']}  "
          f"wrong {on_line['wrong']}")

    # ── 2. per BAR: does the convention hold where it can be tested? ────────
    bars = collections.Counter()
    for c, subs in in_cell.items():
        witnessed = [s for s in subs if pos_of.get(s) is not None]
        if not witnessed:
            bars["no witness"] += 1
            continue
        bad = sum(1 for s in witnessed
                  if position_says(pos_of[s]) != decided[s])
        bars["obeys (0 contradictions)" if bad == 0
             else "contradicted"] += 1
    print(f"\n── 2. BARS, by whether their own stemmed heads obey it")
    for k, v in bars.most_common():
        print(f"   {v:6d}  {k}")

    # ── 3. the GATED rule, leave-one-out ────────────────────────────────────
    for min_witnesses in (1, 2, 3):
        right = wrong = 0
        for sub, want in decided.items():
            pos = pos_of.get(sub)
            if pos is None:
                continue
            others = [s for s in in_cell[cell(sub)]
                      if s != sub and pos_of.get(s) is not None]
            if len(others) < min_witnesses:
                continue
            if any(position_says(pos_of[s]) != decided[s] for s in others):
                continue
            got = position_says(pos)
            right += got == want
            wrong += got != want
        reach = 0
        for sub in no_stem:
            pos = pos_of.get(sub)
            if pos is None:
                continue
            others = [s for s in in_cell[cell(sub)]
                      if pos_of.get(s) is not None]
            if len(others) < min_witnesses:
                continue
            if any(position_says(pos_of[s]) != decided[s] for s in others):
                continue
            reach += 1
        fires = right + wrong
        print(f"\n── 3. GATED on the bar obeying it, >= {min_witnesses} "
              f"witness(es), LEAVE-ONE-OUT")
        print(f"   fires {fires}   right {right}   wrong {wrong}   "
              f"accuracy {right / max(1, fires):.3f}   "
              f"reach on no_stem {reach}")
        tally[f"gated_{min_witnesses}"] = {
            "fires": fires, "right": right, "wrong": wrong,
            "accuracy": round(right / max(1, fires), 4), "reach": reach}

    base = collections.Counter(decided.values()).most_common(1)[0]
    print(f"\nbaseline 'always {base[0]}': {base[1] / len(decided):.3f}")

    Path(a.json).write_text(json.dumps(
        {"bare": {"right": tally["right"], "wrong": tally["wrong"]},
         "on_middle_line": dict(on_line),
         "bars": dict(bars),
         "gated": {k: v for k, v in tally.items()
                   if isinstance(v, dict)},
         "baseline": {"value": base[0],
                      "accuracy": round(base[1] / len(decided), 4)}},
        indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
