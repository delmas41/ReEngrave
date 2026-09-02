"""Can this benchmark see a mark on a bar with no notes? The corpus question.

`46e42a4` fixed a bar with no detected events dropping its `<direction>` marks
on the way out — the eighth instance of recognised-then-dropped, and the first
that **no engraved measurement could have caught**. Not because the check was
weak: because the corpus was. An engraved page has notes in every bar and never
takes the empty-measure path, so the fault needed a scan, where a staff rests
through a bar that still carries a `sempre`.

That makes "does the benchmark contain the case" a question a widening has to
answer out loud rather than assume. This answers it, in two directions.

    # can it fire? — reads the TRUTH, needs no pipeline run
    python3 benchmarks/omr-direction-text-2026-09/probe_empty_measure_marks.py

    # would it have fired? — reads an OMR export beside its truth
    python3 benchmarks/omr-direction-text-2026-09/probe_empty_measure_marks.py --pred

**The two questions are different and both matter.** The TRUTH side asks whether
the corpus contains a bar that carries a mark and no note — the shape the bug
needs. The PRED side asks whether our own export has a measure with a mark and
nothing else in it, which is where the bug actually fired: the trigger is the
DETECTOR finding nothing, so a bar of rests in the truth that we detect as a
rest is NOT a trigger (a rest is an event), while a bar we simply missed is.

So a corpus can be clean on the truth side and still exercise the bug through
detection failure. Report both; do not treat either alone as coverage.

VERIFIED NEUTRAL IN BOTH CONFIGURATIONS. `46e42a4` measures 0.1066 / 767 with
the reader off and 0.0849 / 623 with it on, both identical to the tree without
the fix — which is the point: the engraved benchmark cannot reach the path in
EITHER configuration, so neither number is evidence the fix works. The unit
tests are.

RESULT on the three works as of 2026-09-02: **0 triggering bars on either
side.** Beethoven's `Allegro con brio` sits on a rests-only bar, which is the
shape — but a rest IS an event, so the detector finds it, the normal path runs,
and the marks survive. That work exported its one word correctly throughout.
**The benchmark does not guard this fix**; the two unit tests in
`test_direction_text.py` are the only thing that does. A widening to 11 works
should re-run this and say which of the new works, if any, changes that.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"

_MEASURE = re.compile(r"<measure[^>]*number=\"([^\"]+)\"[^>]*>(.*?)</measure>", re.S)
_PART = re.compile(r'<part id="([^"]+)">(.*?)</part>', re.S)


def marked_noteless_measures(xml: str) -> list[tuple[str, str, str]]:
    """`(part, measure, what mark)` for bars carrying a mark and NO note."""
    out = []
    for part_id, body in _PART.findall(xml):
        for number, measure in _MEASURE.findall(body):
            # A pitched note is what makes a bar non-empty for this purpose;
            # count a measure as noteless when every <note> in it is a rest.
            notes = re.findall(r"<note\b.*?</note>", measure, re.S)
            pitched = [n for n in notes if "<pitch" in n]
            if pitched:
                continue
            marks = []
            if "<words" in measure:
                marks.append("words")
            if "<dynamics" in measure:
                marks.append("dynamics")
            if "<wedge" in measure:
                marks.append("wedge")
            if marks:
                out.append((part_id, number,
                            f"{'+'.join(marks)}"
                            f"{' (rests only)' if notes else ' (nothing)'}"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", action="store_true",
                    help="read `<work>.omr.musicxml` instead of the truth")
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    args = ap.parse_args(argv)

    suffix = ".omr.musicxml" if args.pred else ".musicxml"
    files = sorted(p for p in args.fixtures.glob(f"*{suffix}")
                   if args.pred or not p.name.endswith(".omr.musicxml"))
    if not files:
        print(f"no {suffix} under {args.fixtures}", file=sys.stderr)
        return 2

    rests_only = empty = 0
    for path in files:
        hits = marked_noteless_measures(path.read_text())
        rests_only += sum(1 for _p, _n, w in hits if "rests only" in w)
        empty += sum(1 for _p, _n, w in hits if "nothing" in w)
        print(f"\n{path.name}: {len(hits)} marked bar(s) with no pitched note")
        for part, number, what in hits[:12]:
            print(f"    {part} m{number}  {what}")

    print(f"\n{'':-<62}")
    side = "our export" if args.pred else "the truth"
    print(f"in {side}: {rests_only} marked bar(s) of RESTS ONLY, "
          f"{empty} carrying NOTHING")
    # The two are not the same evidence and reporting one number would hide it.
    if empty:
        print("A bar with nothing in it is the exact trigger: the detector finds "
              "no event, the whole-measure-rest path runs, and before 46e42a4 the "
              "marks went with it. This corpus exercises the bug directly.")
    elif rests_only:
        print("Rests-only bars are the SHAPE but not the trigger. A rest IS an "
              "event, so a detector that finds it takes the normal path and the "
              "marks survive — Beethoven's `Allegro con brio` sits on such a bar "
              "and exported correctly throughout. This corpus reaches the bug "
              "only if detection FAILS on one of these bars, which is luck, not "
              "coverage. Treat it as unguarded.")
    else:
        print("NONE. This corpus cannot exercise the empty-measure path at all, "
              "so a regression there would pass every test here — the blind spot "
              "46e42a4 came out of. The check was fine; the corpus had no "
              "instance of the case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
