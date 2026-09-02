"""Score candidate `<direction>` placement rules against the truth's own offsets.

`_direction_slots` decides which note a dynamic or a word is emitted before, and
getting it wrong costs DOUBLE — musicdiff deletes the mark where we put it and
inserts it where it belongs, each charged the mark's full character count. So it
is worth trying rules. The problem is that trying one through the benchmark
costs an hour, which is enough to stop anyone trying a fourth.

This scores them in seconds. It reads a transcription's marks and events once,
then replays every rule over them and compares against the offsets music21 reads
out of the truth — the same file, parsed the same way musicdiff parses it.

    # once per tree, ~4 min a work: the marks and the events they choose between
    python3 benchmarks/omr-direction-text-2026-09/score_placement_rules.py \\
        --dump brahms-sym1-mvt1 beethoven-sym5-mvt1

    # then as often as you like, ~2 s
    .venv-omrned/bin/python \\
        benchmarks/omr-direction-text-2026-09/score_placement_rules.py

WHAT IT DOES NOT MEASURE. A mark the reader never proposed, or read wrongly, is
invisible here — this pairs prediction to truth BY TEXT and scores only where the
mark exists on both sides. It answers "is this mark on the right beat", and
nothing else. The pooled OMR-NED run is still the number that counts.

THE SPLIT IT MADE VISIBLE, which is the reason it exists: of the four marks the
shipped rule misplaced, only ONE was a placement error. Two sit on the correct
event in a bar whose earlier note lost its augmentation dot, so the event itself
is at the wrong time — no placement rule reaches them. Comparing rules on a
pooled score would have hidden that; comparing them mark by mark could not.

Two halves, because music21 needs Python >= 3.10 and the pipeline is on 3.9:
`--dump` runs in the repo's interpreter and writes JSON, and the scoring runs in
`.venv-omrned`. Same shape as `omr_ned.py` and `_omrned_worker.py`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
MARKS_JSON = Path(__file__).with_name("placement-marks.json")

DEFAULT_WORKS = ("brahms-sym1-mvt1", "beethoven-sym5-mvt1")


# ── the rules ───────────────────────────────────────────────────────────────
#
# Each takes the measure's events and a mark's x, and returns the index it is
# emitted before. `len(events)` means "after everything".

RULES: dict[str, Callable[[list[dict[str, Any]], float], int]] = {}


def rule(fn):
    RULES[fn.__name__] = fn
    return fn


@rule
def first_at_or_past(events, x):
    """What shipped first. Correct only when a mark's left edge is at or left
    of its own note, which is not reliable in either direction."""
    for i, e in enumerate(events):
        if e["x"] is not None and e["x"] >= x:
            return i
    return len(events)


@rule
def nearest(events, x):
    placed = [i for i, e in enumerate(events) if e["x"] is not None]
    if not placed:
        return len(events)
    return min(placed, key=lambda i: (abs(events[i]["x"] - x), -i))


@rule
def nearest_note(events, x):
    """Rests are not candidates — you do not mark a rest `ff`."""
    notes = [i for i, e in enumerate(events)
             if e["x"] is not None and not e["rest"]]
    if not notes:
        return nearest(events, x)
    return min(notes, key=lambda i: (abs(events[i]["x"] - x), -i))


@rule
def nearest_note_keep_tail(events, x):
    """SHIPPED. `nearest_note`, except a mark right of EVERY event keeps the
    past-the-end position instead of snapping back — which is what a bar with a
    MISSED note needs."""
    xs = [e["x"] for e in events if e["x"] is not None]
    if xs and x > max(xs):
        return len(events)
    return nearest_note(events, x)


# ── the dump half (repo interpreter) ────────────────────────────────────────

def dump(works: list[str], weights: str, dpi: int | None) -> None:
    from tools.omr.export import (group_chords_in_measure, measure_directions,
                                  split_events_into_voices)
    from tools.omr.transcribe import transcribe

    opts = {"dpi": dpi} if dpi is not None else {}
    out: dict[str, list[dict[str, Any]]] = {}
    for work in works:
        result = transcribe(pdf_path=FIXTURES / f"{work}.pdf", pages=[0],
                            weights=weights, contextual=False, progress=False,
                            read_direction_text=True, **opts)
        rows = []
        staves = [s for sys_ in result["pages"][0]["systems"]
                  for s in sys_["staves"]]
        for staff_index, staff in enumerate(staves):
            for measure in staff.get("measures", []):
                marks = measure_directions(measure)
                if not marks:
                    continue
                voices = split_events_into_voices(
                    group_chords_in_measure(measure.get("detections", [])))
                rows.append({
                    # The parts are 1:1 with the staves on these one-system
                    # fixtures, which is what lets the join be by index.
                    "staff": staff_index,
                    "measure": measure["measure_index"],
                    "marks": [{"x": m[0], "kind": m[1], "text": m[2]}
                              for m in marks],
                    "events": [{"x": e.get("x_position"),
                                "dur": e.get("duration_beats"),
                                "rest": e.get("kind") == "rest"}
                               for e in (voices[0] if voices else [])],
                })
        out[work] = rows
        print(f"{work}: {len(rows)} measures carrying marks")
    MARKS_JSON.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {MARKS_JSON}")


# ── the scoring half (.venv-omrned) ─────────────────────────────────────────

def _truth_marks(work: str) -> dict[tuple[int, Any], list[tuple[float, str, str]]]:
    from music21 import converter, dynamics, expressions

    score = converter.parse(str(FIXTURES / f"{work}.musicxml"))
    out: dict[tuple[int, Any], list[tuple[float, str, str]]] = {}
    for part_index, part in enumerate(score.parts):
        for measure in part.getElementsByClass("Measure"):
            here = []
            for el in measure.recurse():
                if isinstance(el, dynamics.Dynamic):
                    here.append((float(el.getOffsetInHierarchy(measure)),
                                 "dynamic", el.value))
                elif isinstance(el, expressions.TextExpression):
                    here.append((float(el.getOffsetInHierarchy(measure)),
                                 "words", el.content))
            if here:
                out[(part_index, measure.number)] = here
    return out


def _onsets(events) -> tuple[list[float], float]:
    run, out = 0.0, []
    for e in events:
        out.append(round(run, 4))
        run += (e["dur"] or 0.0)
    return out, round(run, 4)


def score() -> int:
    if not MARKS_JSON.is_file():
        print(f"no {MARKS_JSON.name}; run with --dump first", file=sys.stderr)
        return 2
    pred = json.loads(MARKS_JSON.read_text())

    tally = {name: {"hit": 0, "miss": 0, "words": 0, "dyn": 0} for name in RULES}
    detail: dict[str, list[str]] = {name: [] for name in RULES}
    for work, rows in pred.items():
        truth = _truth_marks(work)
        for row in rows:
            onsets, total = _onsets(row["events"])
            got = truth.get((row["staff"], row["measure"] + 1), [])
            for mark in row["marks"]:
                want = next((o for o, k, c in got
                             if c == mark["text"] and k == mark["kind"]), None)
                if want is None:
                    continue        # not a placement question — see the header
                for name, fn in RULES.items():
                    index = fn(row["events"], mark["x"])
                    offset = onsets[index] if index < len(onsets) else total
                    if abs(offset - want) < 1e-4:
                        tally[name]["hit"] += 1
                        continue
                    tally[name]["miss"] += 1
                    # An offset miss is charged the mark twice: deleted where we
                    # put it, inserted where it belongs.
                    cost = 2 * len(mark["text"])
                    tally[name]["words" if mark["kind"] == "words" else "dyn"] += cost
                    detail[name].append(
                        f"{work.split('-')[0][:9]:9s} staff {row['staff']:2d} "
                        f"m{row['measure']} {mark['kind']:7s} {mark['text']!r} "
                        f"-> {offset}, truth {want}")

    print(f"{'rule':26s} {'hit':>4s} {'miss':>5s} {'word edits':>11s} "
          f"{'dyn edits':>10s}")
    for name in RULES:
        t = tally[name]
        print(f"{name:26s} {t['hit']:>4d} {t['miss']:>5d} "
              f"{t['words']:>11d} {t['dyn']:>10d}")
    for name in RULES:
        print(f"\n-- {name} misplaces --")
        for line in detail[name] or ["   (none)"]:
            print(f"   {line}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", nargs="*", metavar="WORK",
                    help="re-transcribe and refresh placement-marks.json "
                         "(repo interpreter, minutes); omit to score the "
                         "existing dump (.venv-omrned, seconds)")
    ap.add_argument("--weights", default=None)
    ap.add_argument("--dpi", type=int, default=None)
    args = ap.parse_args(argv)

    if args.dump is not None:
        from tools.omr.transcribe import DEFAULT_WEIGHTS
        dump(list(args.dump) or list(DEFAULT_WORKS),
             args.weights or DEFAULT_WEIGHTS, args.dpi)
        return 0
    return score()


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
