"""Trim a reference movement to the measures one scanned page actually holds.

RUNS INSIDE `.venv-omrned`, NOT THE REPO'S PYTHON. Like
`tools/omr/_omrned_worker.py`, this is executed by an interpreter that has
music21 10.5 and musicdiff but does NOT have this project on its path, so it
must stay free of `tools.*` imports.

    .venv-omrned/bin/python benchmarks/omr-scan-e2e-2026-09/trim_reference.py \
        --source /abs/reference.mxl --first 1 --last 16 --out /abs/truth.musicxml

WHY THE VENV AND NOT THE HOST. The host is Python 3.9 with music21 8.3.0; the
venv is 3.14 with music21 10.5.0, which is the music21 musicdiff itself parses
with. Two reasons to prefer it, and the first is not optional:

  A PAIR HANDED TO musicdiff MUST SHARE ONE EXTENSION. `_omrned_worker._stage`
  sets `suffix = ".musicxml"` whenever the two suffixes differ and then
  converts BOTH files through music21 — which its own comment warns "launders
  syntax errors ... musicdiff deliberately parses the prediction leniently and
  the truth strictly, and a conversion here erases that distinction." Passing a
  raw `.mxl` reference beside a `.musicxml` prediction therefore launders the
  PREDICTION. The truth has to be written out as `.musicxml` either way; the
  only real choice is which music21 writes it.

  Writing it here means the file is produced and consumed by the same parser,
  so the ground truth takes no cross-version round trip. The host's 8.3.0 emits
  real warnings on these files (`Line <dashes> stop without start`, `Could not
  import wedge`).

`orchestral_eval` trims on the HOST (`parsed.measures(first, last_used)`,
music21 8.3.0). The two benchmarks therefore prepare truth differently. That is
deliberate — they are different corpora and their pooled figures are not
comparable anyway. It was not left as an assumption: the same prediction was
scored against this trimmer's Beethoven 5 truth and against
`benchmarks/omr-first-run-2026-08/truth/beet5-mm1-16.musicxml`, which was
produced the other way. RESULTS.md records what the two gave.

MEASURE NUMBERS, NOT INDICES. `Stream.measures(a, b)` matches measure NUMBERS
and is INCLUSIVE at both ends; `indicesNotNumbers=True` is positional with an
EXCLUSIVE end. Verified in both interpreters. The distinction is load-bearing
because the corpus uses both anacrusis conventions:

    Mahler 5   reference numbers the pickup 0   -> measures(0, 8) keeps it,
                                                   measures(1, 8) drops it
    Bach BWV1048  reference numbers the pickup 1 -> the print numbers the first
                                                   FULL bar 1, so reference =
                                                   print + 1

So callers pass reference measure NUMBERS taken from a hand-verified map, never
a count. `collect=` (which re-attaches Clef / TimeSignature / Instrument /
KeySignature / MetronomeMark at the head of the window) is passed by keyword,
because 8.3.0 takes it positionally and 10.5.0 makes it keyword-only.

REPEATS. musicdiff compares the WRITTEN measure sequence — nothing calls
`expandRepeats()` and music21 does not expand on parse — so a repeat mark is a
barline property, not a duplication. But a window that opens after a
`Repeat(direction='start')` inherits a dangling end-repeat, so unmatched
repeats are stripped and the count is reported rather than hidden.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from music21 import bar, converter
import music21


def _measure_facts(score) -> dict:
    parts = list(score.parts)
    if not parts:
        return {"n_parts": 0, "n_measures": 0, "measure_numbers": []}
    measures = list(parts[0].getElementsByClass("Measure"))
    first = measures[0] if measures else None
    counts = sorted({len(list(p.getElementsByClass("Measure"))) for p in parts})
    return {
        "n_parts": len(parts),
        "n_measures": len(measures),
        "measure_numbers": [m.number for m in measures][:40],
        "measure_counts_across_parts": counts,
        "first_measure_ql": float(first.duration.quarterLength) if first is not None else None,
        "first_measure_padding_left": float(getattr(first, "paddingLeft", 0) or 0)
        if first is not None else None,
    }


def _strip_unmatched_repeats(score) -> int:
    """Drop repeat marks the window cut in half.

    A trimmed window can inherit an end-repeat whose start is outside it (or the
    reverse). That is not a notation difference the pipeline could ever have
    got right, so charging for it would measure the trim rather than the
    reading.
    """
    removed = 0
    for part in score.parts:
        marks = []
        for measure in part.getElementsByClass("Measure"):
            for element in list(measure.getElementsByClass(bar.Repeat)):
                marks.append((measure, element))
        opens = [m for m in marks if m[1].direction == "start"]
        closes = [m for m in marks if m[1].direction == "end"]
        # Pair them off in order; anything left over is dangling.
        n_paired = min(len(opens), len(closes))
        for measure, element in opens[n_paired:] + closes[n_paired:]:
            measure.remove(element)
            removed += 1
    return removed


def trim(source: Path, first: int, last: int, out: Path,
         merge_parts: list[list[int]] | None = None,
         keep_repeats: bool = False) -> dict:
    score = converter.parse(str(source))
    whole = _measure_facts(score)

    window = score.measures(
        first, last,
        collect=("Clef", "TimeSignature", "Instrument", "KeySignature"),
    )
    trimmed_facts = _measure_facts(window)

    numbers = trimmed_facts["measure_numbers"]
    if not numbers:
        raise SystemExit(
            f"measures({first}, {last}) selected NOTHING from {source.name}. "
            f"The movement's own numbering runs "
            f"{whole['measure_numbers'][:3]}… — these are measure NUMBERS, not "
            f"indices, and the file may number a pickup 0."
        )

    stripped = 0 if keep_repeats else _strip_unmatched_repeats(window)

    merged = None
    if merge_parts:
        window = window.partsToVoices(voiceAllocation=merge_parts,
                                      permitOneVoicePerPart=False)
        merged = len(list(window.parts))

    out.parent.mkdir(parents=True, exist_ok=True)
    window.write("musicxml", fp=str(out))

    return {
        "source": str(source),
        "out": str(out),
        "bytes": out.stat().st_size,
        "requested": [first, last],
        "music21": music21.__version__,
        "python": sys.version.split()[0],
        "movement": {k: whole[k] for k in
                     ("n_parts", "n_measures", "first_measure_ql",
                      "first_measure_padding_left")},
        "movement_first_numbers": whole["measure_numbers"][:5],
        "window": {
            "n_parts": trimmed_facts["n_parts"],
            "n_measures": trimmed_facts["n_measures"],
            "measure_numbers": numbers,
            "first_measure_ql": trimmed_facts["first_measure_ql"],
            "first_measure_padding_left": trimmed_facts["first_measure_padding_left"],
        },
        "unmatched_repeats_stripped": stripped,
        "parts_after_merge": merged,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, required=True,
                    help="the reference .mxl / .musicxml for ONE movement")
    ap.add_argument("--first", type=int, required=True,
                    help="first reference measure NUMBER (inclusive)")
    ap.add_argument("--last", type=int, required=True,
                    help="last reference measure NUMBER (inclusive)")
    ap.add_argument("--out", type=Path, required=True,
                    help="where to write the trimmed truth; MUST end .musicxml")
    ap.add_argument("--merge-parts", default=None,
                    help='JSON list of lists mapping printed staff -> reference '
                         'part indices, e.g. "[[0,1],[2,3],[4]]". Produces the '
                         '"as printed" truth via partsToVoices. UNVALIDATED '
                         'against musicdiff — a second column, not the headline.')
    ap.add_argument("--keep-repeats", action="store_true",
                    help="do not strip repeat marks the window cut in half")
    args = ap.parse_args(argv)

    if args.out.suffix.lower() not in (".musicxml", ".xml"):
        ap.error(f"--out must be .musicxml (got {args.out.suffix!r}) — a pair "
                 "handed to musicdiff must share one extension or BOTH get "
                 "laundered through music21. See the module docstring.")

    merge = json.loads(args.merge_parts) if args.merge_parts else None
    report = trim(args.source, args.first, args.last, args.out,
                  merge_parts=merge, keep_repeats=args.keep_repeats)
    json.dump(report, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
