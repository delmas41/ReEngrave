"""Attribute the OMR-NED `wrong note` / `wrong pitch` budget to a CAUSE per part.

A category is not a cause. `BRAHMS_ATTRIBUTION_2026-09-01.md` turned one page's
share of it into one by hand — align each part against the truth, bucket the
deltas, see whether they concentrate — and found a staff whose five-line window
had locked onto a beam. This is that method made repeatable, with two
corrections that the by-hand version could not have seen.

CORRECTION 1 — `wrong note` IS NOT WRONG PITCHES. musicdiff maps `noteins` and
`notedel` to `wrong note`, and `pitchnameedit` to a SEPARATE `wrong pitch`
category. So `wrong note` counts notes present on one side and absent on the
other. It reads as "we got the notes wrong" and means "we and the truth
disagree about which notes are there".

CORRECTION 2 — ALIGNING ON PITCH NAMES HIDES THE LARGEST FAILURE THERE IS.
`difflib.SequenceMatcher` over pitch names finds no matching block at all in a
part that is uniformly transposed, so every note becomes an insert plus a
delete and the part reports ZERO wrong pitches. A whole staff read four
positions low — the single worst thing that can happen to a part — is therefore
invisible to the name-based method, and it was: Brahms Violin 1 scored 4
"replaced" notes while being wrong in all 39.

So the alignment here is BY MEASURE AND INDEX, not by pitch name. The benchmark
excerpts agree on measure counts by construction (the fixture is engraved from
the truth), and within a measure the note order is the exporter's reading order
on both sides, so index pairing is meaningful and — unlike name matching — has
no way to skip a wrong note.

Each measure is then classified, and the classes are the causes:

    exact    identical pitch AND duration sequences
    duration every pitch right, at least one duration wrong — a RHYTHM
             failure, which is what most of `wrong note` turns out to be
    order    the same pitches in a different sequence — an export/voicing
             ordering difference, which musicdiff does not charge for
    shift:k  every paired note off by the SAME k staff positions — a
             geometric failure: a misfitted staff window, or a wrong clef
    accid    right staff positions, wrong accidentals — key signature
    mixed    paired, and disagreeing in no one pattern
    count    the two sides do not even agree how many notes are in the bar

Pitch is tested before duration, so a measure that is wrong in both is filed
under the pitch fault; `notes_wrong_duration` counts duration disagreements
across every class and is the figure to read for rhythm.

    python3 benchmarks/omr-ned-2026-08/attribute_wrong_notes.py
    python3 benchmarks/omr-ned-2026-08/attribute_wrong_notes.py --detail

Runs on the host Python: it needs music21, not musicdiff, so no venv.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from music21 import converter, pitch as m21pitch  # noqa: E402

FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
DEFAULT_WORKS = ("beethoven-sym5-mvt1", "brahms-sym1-mvt1", "mahler-sym5-mvt1")

_CACHE: dict[str, tuple[int, int]] = {}


def _coords(name: str) -> tuple[int, int]:
    """(midi, diatonicNoteNum) for a pitch name, memoised — these are hot."""
    got = _CACHE.get(name)
    if got is None:
        p = m21pitch.Pitch(name)
        got = (p.midi, p.diatonicNoteNum)
        _CACHE[name] = got
    return got


def measures_of(path: Path) -> list[dict[str, Any]]:
    """Per part: its name and, per measure, `(pitch, quarterLength)` in order.

    Chords are expanded to one entry per pitch, in the order the file gives
    them — the order is data here, since disagreeing about it is one of the
    causes this is trying to separate.
    """
    score = converter.parse(str(path))
    out = []
    for idx, part in enumerate(score.parts):
        bars = []
        for measure in part.getElementsByClass("Measure"):
            names = []
            for element in measure.recurse().notes:
                ql = round(float(element.duration.quarterLength), 6)
                names.extend((p.nameWithOctave, ql) for p in element.pitches)
            bars.append(names)
        out.append({
            "index": idx,
            "name": (part.partName or f"part{idx}").strip(),
            "bars": bars,
        })
    return out


def classify(truth: list[tuple[str, float]],
             pred: list[tuple[str, float]]) -> dict[str, Any]:
    """One measure of one part: which class, the deltas, and the rhythm count."""
    if truth == pred:
        return {"cls": "exact", "n": len(truth), "deltas": [], "dur_wrong": 0}
    if len(truth) != len(pred):
        return {"cls": "count", "n": max(len(truth), len(pred)), "deltas": [],
                "dur_wrong": 0, "n_truth": len(truth), "n_pred": len(pred)}
    if not truth:
        return {"cls": "exact", "n": 0, "deltas": [], "dur_wrong": 0}

    dur_wrong = sum(1 for (_, t_ql), (_, p_ql) in zip(truth, pred)
                    if t_ql != p_ql)
    t_names = [n for n, _ in truth]
    p_names = [n for n, _ in pred]
    if t_names == p_names:
        # Every pitch right; only the rhythm is wrong. This is the class the
        # name-based method could not express at all.
        return {"cls": "duration", "n": len(truth), "deltas": [],
                "dur_wrong": dur_wrong}
    if sorted(t_names) == sorted(p_names):
        return {"cls": "order", "n": len(truth), "deltas": [],
                "dur_wrong": dur_wrong}

    deltas = []
    for t_name, p_name in zip(t_names, p_names):
        t_midi, t_dia = _coords(t_name)
        p_midi, p_dia = _coords(p_name)
        deltas.append({"truth": t_name, "pred": p_name,
                       "positions": p_dia - t_dia, "semitones": p_midi - t_midi})
    positions = {d["positions"] for d in deltas}
    if positions == {0}:
        cls = "accid"
    elif len(positions) == 1:
        cls = f"shift:{positions.pop():+d}"
    else:
        cls = "mixed"
    return {"cls": cls, "n": len(truth), "deltas": deltas,
            "dur_wrong": dur_wrong}


def attribute_work(work_id: str, pred: Path, truth: Path) -> dict[str, Any]:
    truth_parts = measures_of(truth)
    pred_parts = measures_of(pred)
    if len(truth_parts) != len(pred_parts):
        # Pairing parts positionally is only defensible when both sides agree
        # how many there are; anything else measures the pairing.
        return {"work_id": work_id, "part_aligned": False,
                "truth_parts": len(truth_parts), "pred_parts": len(pred_parts)}

    parts = []
    for t_part, p_part in zip(truth_parts, pred_parts):
        bars = []
        for bar_idx in range(max(len(t_part["bars"]), len(p_part["bars"]))):
            t_bar = t_part["bars"][bar_idx] if bar_idx < len(t_part["bars"]) else []
            p_bar = p_part["bars"][bar_idx] if bar_idx < len(p_part["bars"]) else []
            rec = classify(t_bar, p_bar)
            rec["measure"] = bar_idx + 1
            bars.append(rec)
        classes = Counter(b["cls"] for b in bars)
        notes_by_class: Counter = Counter()
        for b in bars:
            notes_by_class[b["cls"]] += b["n"]
        # A part is called SHIFTED when every measure that disagrees at all
        # disagrees by the same constant — one geometric fault, not many.
        shifts = {c for c in classes if c.startswith("shift:")}
        parts.append({
            "index": t_part["index"],
            "truth_name": t_part["name"],
            "pred_name": p_part["name"],
            "truth_notes": sum(len(b) for b in t_part["bars"]),
            "pred_notes": sum(len(b) for b in p_part["bars"]),
            "measure_classes": dict(classes.most_common()),
            "notes_by_class": dict(notes_by_class.most_common()),
            "notes_wrong_duration": sum(b["dur_wrong"] for b in bars),
            "uniform_shift": shifts.pop() if len(shifts) == 1 and not (
                classes.keys() - {"exact", *shifts}) else None,
            "bars": bars,
        })

    notes_by_class: Counter = Counter()
    for p in parts:
        for cls, n in p["notes_by_class"].items():
            notes_by_class[cls] += n
    # Every shift bucket rolled together, since the interesting fact is "a
    # constant offset" rather than which offset.
    rolled: Counter = Counter()
    for cls, n in notes_by_class.items():
        rolled["shift" if cls.startswith("shift:") else cls] += n

    return {
        "work_id": work_id,
        "part_aligned": True,
        "parts": parts,
        "notes_wrong_duration": sum(p["notes_wrong_duration"] for p in parts),
        "notes_by_class": dict(notes_by_class.most_common()),
        "notes_by_class_rolled": dict(rolled.most_common()),
        "truth_notes": sum(p["truth_notes"] for p in parts),
        "pred_notes": sum(p["pred_notes"] for p in parts),
    }


def report(result: dict[str, Any], detail: bool = False) -> None:
    print(f"\n=== {result['work_id']}")
    if not result["part_aligned"]:
        print(f"  parts differ ({result['truth_parts']} truth vs "
              f"{result['pred_parts']} pred) — no per-part alignment")
        return
    total = result["truth_notes"]
    print(f"  truth notes {total}   pred notes {result['pred_notes']}")
    print("  notes by measure class:")
    for cls, n in result["notes_by_class_rolled"].items():
        print(f"    {cls:10s} {n:>5d}  {n / total * 100:5.1f}%")
    dur = result["notes_wrong_duration"]
    print(f"  notes with a wrong DURATION (any class, paired bars only): "
          f"{dur}  {dur / total * 100:.1f}%")
    print(f"\n  {'#':>3s} {'part':20s} {'truth':>6s} {'durX':>4s}  "
          f"measure classes                          uniform shift")
    for p in sorted(result["parts"],
                    key=lambda p: -(p["truth_notes"]
                                    - p["notes_by_class"].get("exact", 0))):
        wrong = p["truth_notes"] - p["notes_by_class"].get("exact", 0)
        if not wrong and not detail:
            continue
        classes = " ".join(f"{k}={v}" for k, v in p["measure_classes"].items())
        print(f"  {p['index']:>3d} {p['truth_name'][:20]:20s} "
              f"{p['truth_notes']:>6d} {p['notes_wrong_duration']:>4d}  "
              f"{classes[:38]:38s} {p['uniform_shift'] or ''}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--works", nargs="+", default=list(DEFAULT_WORKS))
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--detail", action="store_true",
                    help="list clean parts too")
    args = ap.parse_args(argv)

    results = []
    for work_id in args.works:
        pred = args.fixtures / f"{work_id}.omr.musicxml"
        truth = args.fixtures / f"{work_id}.musicxml"
        if not pred.is_file() or not truth.is_file():
            print(f"{work_id}: missing fixture — run orchestral_eval first",
                  file=sys.stderr)
            continue
        res = attribute_work(work_id, pred, truth)
        results.append(res)
        report(res, detail=args.detail)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
