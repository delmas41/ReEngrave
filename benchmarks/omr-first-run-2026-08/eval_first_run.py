"""Score one page of a REAL SCAN against the work's reference MusicXML.

Every end-to-end number this repo holds was measured on a page the project
RENDERED from the same MusicXML it then scored against (`orchestral_eval`), or
on a single element of a scan measured in isolation — clefs on 52 hand-read
staves, key signatures on 42, the part-staff join on three pages. Nothing had
ever taken a scan the pipeline has never seen, run it with the defaults a user
gets, and asked what came out.

That is what this does, and the honesty of it rests on three rules:

  NO DOSSIER. `data/dossiers/` is GENERATED from the same Gradus MusicXML used
  here as truth, so `--dossier` would hand the run the answer it is being
  scored on. The run is plain `transcribe`, defaults, nothing else.

  THE PAGE IS THE TRUTH, NOT THE FILE. Clefs and key signatures are hand-read
  off the scan, because the reference and the edition genuinely disagree —
  Breitkopf prints Trombe and Timpani with no key signature and the Gradus file
  gives them three flats. A pipeline that reads the page correctly must not be
  marked wrong for it.

  THE MEASURE WINDOW IS ESTABLISHED INDEPENDENTLY. Beethoven 5 page 1 is
  measures 1-17: counted as full-height ink columns on the Flauti staff (a
  staff of whole-bar rests, so the only full-height ink is a barline), and
  confirmed by the reference, where every wind part's first note is m.18.

WHAT THE COMPARISON IS. Pitches are compared as MULTISETS per printed staff,
not as sequences. A printed staff can carry two reference parts (Flauti is
Flute 1 + Flute 2), and the reading order of two condensed parts on one staff
is genuinely ambiguous, so an order-sensitive alignment would measure the
ambiguity rather than the recognition. Multisets refuse to guess.

Each staff is scored twice, and the gap between the two is the point:

  exact   nameWithOctave — 'E-4' and 'E4' are different notes.
  step    letter+octave, accidental discarded.

`step` recall far above `exact` recall means the pipeline found the right
notehead in the right place and got the accidental wrong, which on this page is
what an unread key signature does to a staff.

    python3 benchmarks/omr-first-run-2026-08/eval_first_run.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from music21 import converter

ROOT = Path(__file__).resolve().parents[2]
BENCH = Path(__file__).resolve().parent
TRUTH_MXL = Path(
    "/Users/seanjohnson/Desktop/gradus-vercel/public/scores/beethoven-sym5-mvt1.mxl"
)
OMR_XML = BENCH / "out" / "beet5-p1.omr.musicxml"
OMR_JSON = BENCH / "out" / "beet5-p1.omr.json"

#: Page 1 of IMSLP984073 carries measures 1-17. See the module docstring for how
#: that was established without asking the pipeline.
FIRST_MEASURE, LAST_MEASURE = 1, 17

#: The printed page's twelve staves, each naming the reference parts it carries.
#: Six of the twelve are condensed pairs, which is why the join is written out
#: rather than inferred: 18 parts do not line up with 12 staves by position.
#: `clef` and `key` are HAND-READ off the scan (see rule 2 in the docstring).
STAVES = [
    {"name": "Flauti",          "parts": [0, 1],   "clef": "treble", "key": -3},
    {"name": "Oboi",            "parts": [2, 3],   "clef": "treble", "key": -3},
    {"name": "Clarinetti in B", "parts": [4, 5],   "clef": "treble", "key": -1},
    {"name": "Fagotti",         "parts": [6, 7],   "clef": "bass",   "key": -3},
    {"name": "Corni in Es",     "parts": [8, 9],   "clef": "treble", "key": 0},
    {"name": "Trombe in C",     "parts": [10, 11], "clef": "treble", "key": 0},
    {"name": "Timpani in C.G.", "parts": [12],     "clef": "bass",   "key": 0},
    {"name": "Violino I",       "parts": [13],     "clef": "treble", "key": -3},
    {"name": "Violino II",      "parts": [14],     "clef": "treble", "key": -3},
    {"name": "Viola",           "parts": [15],     "clef": "alto",   "key": -3},
    {"name": "Violoncello",     "parts": [16],     "clef": "bass",   "key": -3},
    {"name": "Basso",           "parts": [17],     "clef": "bass",   "key": -3},
]


def pitches(part, first: int | None = None, last: int | None = None):
    """Every sounding pitch in a part, optionally restricted to a measure span.

    Chords are expanded to one entry per pitch: counting chord OBJECTS hides a
    six-note chord behind a single tally.
    """
    exact: Counter = Counter()
    step: Counter = Counter()
    dur: Counter = Counter()
    measures = list(part.getElementsByClass("Measure"))
    if first is not None:
        measures = measures[first - 1:last]
    for measure in measures:
        for note in measure.recurse().notes:
            ql = round(float(note.duration.quarterLength), 4)
            for pitch in note.pitches:
                exact[pitch.nameWithOctave] += 1
                step[f"{pitch.step}{pitch.octave}"] += 1
                dur[(pitch.nameWithOctave, ql)] += 1
    return exact, step, dur


def score(truth: Counter, got: Counter) -> dict:
    matched = sum((truth & got).values())
    n_truth, n_got = sum(truth.values()), sum(got.values())
    return {
        "truth": n_truth,
        "omr": n_got,
        "matched": matched,
        "recall": round(matched / n_truth, 4) if n_truth else None,
        "precision": round(matched / n_got, 4) if n_got else None,
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stem", default="beet5-p1",
                    help="basename under out/ to score (default: beet5-p1)")
    args = ap.parse_args()
    omr_xml = BENCH / "out" / f"{args.stem}.omr.musicxml"
    omr_json = BENCH / "out" / f"{args.stem}.omr.json"

    truth_score = converter.parse(str(TRUTH_MXL))
    omr_score = converter.parse(str(omr_xml))
    omr_parts = list(omr_score.parts)
    raw = json.loads(omr_json.read_text())
    omr_staves = raw["pages"][0]["systems"][0]["staves"]

    if len(omr_parts) != len(STAVES):
        print(f"!! staff count differs: page has {len(STAVES)}, "
              f"OMR emitted {len(omr_parts)} parts — rows below are positional")

    rows = []
    totals = {k: Counter() for k in ("t_exact", "g_exact", "t_step",
                                     "g_step", "t_dur", "g_dur")}
    clef_ok = key_ok = 0

    for i, spec in enumerate(STAVES):
        t_exact, t_step, t_dur = Counter(), Counter(), Counter()
        for p in spec["parts"]:
            e, s, d = pitches(truth_score.parts[p], FIRST_MEASURE, LAST_MEASURE)
            t_exact += e
            t_step += s
            t_dur += d
        g_exact, g_step, g_dur = pitches(omr_parts[i]) if i < len(omr_parts) \
            else (Counter(), Counter(), Counter())

        read = omr_staves[i] if i < len(omr_staves) else {}
        got_clef = read.get("clef")
        ks = read.get("key_signature") or {}
        got_key = ks.get("sharps", 0) - ks.get("flats", 0)
        clef_ok += got_clef == spec["clef"]
        key_ok += got_key == spec["key"]

        rows.append({
            "staff": i,
            "name": spec["name"],
            "clef_truth": spec["clef"],
            "clef_omr": got_clef,
            "clef_ok": got_clef == spec["clef"],
            "key_truth": spec["key"],
            "key_omr": got_key,
            "key_read": bool(read.get("key_signature_read")),
            "key_ok": got_key == spec["key"],
            "exact": score(t_exact, g_exact),
            "step": score(t_step, g_step),
            "with_duration": score(t_dur, g_dur),
        })
        for key, counter in (("t_exact", t_exact), ("g_exact", g_exact),
                             ("t_step", t_step), ("g_step", g_step),
                             ("t_dur", t_dur), ("g_dur", g_dur)):
            totals[key] += counter

    pooled = {
        "exact": score(totals["t_exact"], totals["g_exact"]),
        "step": score(totals["t_step"], totals["g_step"]),
        "with_duration": score(totals["t_dur"], totals["g_dur"]),
    }

    truth_measures = LAST_MEASURE - FIRST_MEASURE + 1
    omr_measures = max((s["n_measures"] for s in omr_staves), default=0)
    report = {
        "source_pdf": raw["source_pdf"],
        "page_index": raw["pages"][0].get("page_index"),
        "measures_window": [FIRST_MEASURE, LAST_MEASURE],
        "dossier": None,
        "structure": {
            "systems_truth": 1,
            "systems_omr": raw["n_systems_total"],
            "staves_truth": len(STAVES),
            "staves_omr": raw["n_staves_total"],
            "measures_truth": truth_measures,
            "measures_omr": omr_measures,
        },
        "clef_accuracy": f"{clef_ok}/{len(STAVES)}",
        "key_accuracy": f"{key_ok}/{len(STAVES)}",
        "key_signatures_actually_read": sum(1 for r in rows if r["key_read"]),
        "pooled": pooled,
        "per_staff": rows,
    }
    out = BENCH / f"{args.stem}-firstrun.json"
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"{'staff':<17}{'clef':>16}{'key':>10}"
          f"{'notes t/omr':>14}{'exact R/P':>16}{'step R/P':>16}")
    for r in rows:
        clef = f"{r['clef_omr']}{'' if r['clef_ok'] else ' X'}"
        key = f"{r['key_omr']}{'' if r['key_ok'] else ' X'}"
        e, s = r["exact"], r["step"]
        counts = "{}/{}".format(e["truth"], e["omr"])
        exact = "{}/{}".format(e["recall"], e["precision"])
        step = "{}/{}".format(s["recall"], s["precision"])
        print(f"{r['name']:<17}{clef:>16}{key:>10}"
              f"{counts:>14}{exact:>18}{step:>18}")
    print()
    print("clefs", report["clef_accuracy"],
          "| keys", report["key_accuracy"],
          f"(read on {report['key_signatures_actually_read']})",
          "| measures", f"{omr_measures}/{truth_measures}")
    for name, sc in pooled.items():
        print(f"pooled {name:<14} truth {sc['truth']:>4} omr {sc['omr']:>4} "
              f"matched {sc['matched']:>4}  R {sc['recall']}  P {sc['precision']}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
