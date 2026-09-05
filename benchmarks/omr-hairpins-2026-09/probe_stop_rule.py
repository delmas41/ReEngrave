"""Which note does a hairpin STOP on? Sweep the one constant that decides.

A slur is drawn OVER its notes and a hairpin BETWEEN them, so the slur pass's
overlap test finds nothing here — 0 of 4 detections on the Mahler 5 fixture.
Once that is known the START is unambiguous, the last note at or before the
left edge. The STOP is not, and the ink cannot be asked:

  * a hairpin can END ON a note — a crescendo drawn up to the downbeat it
    arrives at, which is the shape the Mahler truth's `m5 -> m6` crescendo has;
  * or END UNDER one, drawn in the space a long note leaves, in which case the
    note it started on is also the note it stops on. TWO of that page's three
    truth hairpins are this shape.

Both are real and one page cannot choose between them — the trap this project
has recorded before, that a benchmark of three pages cannot falsify a story
about one of them. What separates the two is how close the next attack stands
to the ink's end, so `export._WEDGE_STOP_REACH_NOTEHEADS` is a distance in
notehead widths and this sweeps it. At 0 every hairpin closes on the note still
sounding; at a large value every one reaches for the next attack.

Scoring pairs our exported wedges with the truth's by (part, start measure,
start offset) and asks whether the KIND and the DURATION agree. That is what
musicdiff compares: a wedge is a music21 spanner, its offset is its first
note's and its duration reaches to the end of its last, and
`crescendodurationedit` is the charge for getting the second half wrong.

    python3 benchmarks/omr-hairpins-2026-09/probe_stop_rule.py
    python3 benchmarks/omr-hairpins-2026-09/probe_stop_rule.py --works mahler-sym5-mvt1

Runs the music21 half out of process in `.venv-omrned`, the same way
`tools/omr/omr_ned.py` does and for the same reason: the host is Python 3.9 and
music21 >= 9.9.1 is not.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import accuracy_record, export  # noqa: E402
from tools.omr.omr_ned import interpreter  # noqa: E402

#: Reaches to sweep, in notehead widths. 0.0 is "always the note still
#: sounding"; 99.0 is "always the next attack, however far off".
REACHES = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 99.0)

#: Reads the wedge spanners out of a MusicXML file, as
#: `[[part_index, part_name, kind, start_measure, start_offset, duration], …]`.
#: Runs INSIDE `.venv-omrned` and must not import from `tools.*`.
_READER = r'''
import json, sys, warnings
warnings.filterwarnings("ignore")
import music21 as m21

out = []
score = m21.converter.parse(sys.argv[1])
for pi, part in enumerate(score.parts):
    for sp in part.recurse().getElementsByClass(m21.dynamics.DynamicWedge):
        first, last = sp.getFirst(), sp.getLast()
        measure = first.getContextByClass(m21.stream.Measure)
        try:
            start = first.getOffsetInHierarchy(score)
            end = last.getOffsetInHierarchy(score) + last.duration.quarterLength
        except Exception:
            continue
        out.append([pi, part.partName, type(sp).__name__,
                    measure.number if measure is not None else None,
                    float(first.offset), float(end - start)])
print(json.dumps(out))
'''


def read_wedges(path: Path) -> list[list]:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(_READER)
        script = fh.name
    try:
        proc = subprocess.run([str(interpreter()), script, str(path)],
                              capture_output=True, text=True)
    finally:
        Path(script).unlink(missing_ok=True)
    if proc.returncode != 0:
        raise SystemExit(f"reading {path.name} failed:\n{proc.stderr[-2000:]}")
    return json.loads(proc.stdout)


def key(entry: list) -> tuple:
    """What musicdiff pairs an extra on: where it starts, in which part."""
    return (entry[0], entry[3], round(entry[4], 4))


def score_rule(fixtures: Path, works: tuple[str, ...],
               reach: float, start_rule: str = "nearest") -> dict:
    export._WEDGE_START_RULE = start_rule
    export._WEDGE_STOP_REACH_NOTEHEADS = reach
    rows = []
    for work in works:
        js = fixtures / f"{work}.omr.json"
        truth_path = fixtures / f"{work}.musicxml"
        if not (js.is_file() and truth_path.is_file()):
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".musicxml",
                                         delete=False) as fh:
            fh.write(export.to_musicxml(json.loads(js.read_text())))
            pred_path = Path(fh.name)
        try:
            pred = read_wedges(pred_path)
        finally:
            pred_path.unlink(missing_ok=True)
        truth = read_wedges(truth_path)

        by_key = {key(t): t for t in truth}
        paired = kind_ok = duration_ok = 0
        for p in pred:
            t = by_key.get(key(p))
            if t is None:
                continue
            paired += 1
            kind_ok += int(p[2] == t[2])
            duration_ok += int(abs(p[5] - t[5]) < 1e-6 and p[2] == t[2])
        rows.append({"work": work, "truth": len(truth), "pred": len(pred),
                     "paired": paired, "kind_ok": kind_ok,
                     "exact": duration_ok})
    return {"reach": reach, "start": start_rule, "rows": rows,
            "truth": sum(r["truth"] for r in rows),
            "pred": sum(r["pred"] for r in rows),
            "paired": sum(r["paired"] for r in rows),
            "exact": sum(r["exact"] for r in rows)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path,
                    default=ROOT / "benchmarks" / "omr-orchestral-e2e"
                    / "fixtures")
    ap.add_argument("--works", nargs="+", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    works = tuple(args.works or accuracy_record.BENCHMARK_WORKS)
    report = [score_rule(args.fixtures, works, reach, start)
              for start in ("before", "nearest") for reach in REACHES]

    print(f"{'start':>8s} {'reach':>6s} {'truth':>6s} {'ours':>6s} "
          f"{'paired':>7s} {'exact':>6s}")
    for r in report:
        print(f"{r['start']:>8s} {r['reach']:>6.1f} {r['truth']:>6d} "
              f"{r['pred']:>6d} {r['paired']:>7d} {r['exact']:>6d}")
    print("\nper work, at each setting:")
    for r in report:
        for row in r["rows"]:
            if row["truth"] or row["pred"]:
                print(f"  {r['start']:>8s} {r['reach']:>5.1f}  "
                      f"{row['work']:22s} truth {row['truth']:>2d}  ours "
                      f"{row['pred']:>2d}  paired {row['paired']:>2d}  exact "
                      f"{row['exact']:>2d}")
    if args.out:
        args.out.write_text(json.dumps(report, indent=1) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
