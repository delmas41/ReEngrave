#!/usr/bin/env python3
"""Score any margin-label reader against the free text-layer truth, identically.

`read_crops.py` scored Claude inline, which was fine when Claude was the only
reader. Comparing readers needs the scoring lifted out, so that the paid reader
and a local OCR engine are judged by the same code on the same crops — otherwise
the comparison measures two scoring functions as much as two readers.

    python3 benchmarks/omr-margin-labels-2026-08/score_readers.py \
        results.json results-surya.json

Scoring is on the RESOLVED INSTRUMENT, not the raw string: `Fg.` and `Fag.` are
both Bassoon and both correct. Ground-truth strings are re-resolved here rather
than trusted from the manifest, so a lexicon fix cannot make an old manifest
disagree with itself.

    agree        both the text layer and the reader resolve, to the same thing
    disagree     both resolve, differently          <- the number that decides it
    recovered    reader resolved one the text layer could not   <- the point
    missed       text layer resolved one the reader could not
    both_silent  neither — usually a genuinely unlabelled staff
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr import instruments

HERE = Path(__file__).resolve().parent


def reader_labels(entry: dict) -> dict[str, str]:
    """The reader's output, whichever key the producing script used."""
    for key in ("labels", "vision", "surya", "reader"):
        if key in entry and isinstance(entry[key], dict):
            return {str(k): v for k, v in entry[key].items()}
    return {}


def resolve(text) -> str | None:
    if not text or not isinstance(text, str) or not text.strip():
        return None
    hit = instruments.lookup(text.strip())
    return hit.instrument.name if hit else None


def score(results: list[dict], manifest_by_png: dict[str, dict]):
    tally = collections.Counter()
    notes: list[str] = []
    for entry in results:
        png = entry["png"]
        manifest_entry = manifest_by_png.get(png)
        if manifest_entry is None:
            continue
        truth = entry.get("truth") or manifest_entry.get("truth") or {}
        labels = reader_labels(entry)

        for idx in manifest_entry["staff_indices"]:
            t_raw = (truth.get(str(idx)) or {}).get("text")
            t_inst = resolve(t_raw)
            r_raw = labels.get(str(idx))
            r_inst = resolve(r_raw)

            if t_inst and r_inst:
                key = "agree" if t_inst == r_inst else "disagree"
                tally[key] += 1
                if key == "disagree" and len(notes) < 20:
                    notes.append(f"  DISAGREE  {png} staff {idx}: "
                                 f"text {t_raw!r}->{t_inst} vs "
                                 f"reader {r_raw!r}->{r_inst}")
            elif r_inst:
                tally["recovered"] += 1
                if len(notes) < 20:
                    notes.append(f"  RECOVERED {png} staff {idx}: "
                                 f"text {t_raw!r} -> reader {r_raw!r} -> {r_inst}")
            elif t_inst:
                tally["missed"] += 1
                if len(notes) < 20:
                    notes.append(f"  MISSED    {png} staff {idx}: "
                                 f"text {t_raw!r}->{t_inst}, reader {r_raw!r}")
            else:
                tally["both_silent"] += 1
                # An unresolvable non-empty string is a READ that the lexicon
                # rejected, which is a different failure from silence and the
                # one most likely to be a clipped word.
                if r_raw and len(notes) < 20:
                    notes.append(f"  UNRESOLVED {png} staff {idx}: "
                                 f"reader {r_raw!r} matched no instrument")
    return tally, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+", help="one or more results JSON files")
    ap.add_argument("--crops", default=str(HERE / "crops"))
    ap.add_argument("--detail", action="store_true", help="print per-staff notes")
    args = ap.parse_args()

    manifest = json.loads((Path(args.crops) / "manifest.json").read_text())
    by_png = {e["png"]: e for e in manifest}

    rows = []
    for path in args.results:
        results = json.loads(Path(path).read_text())
        tally, notes = score(results, by_png)
        rows.append((Path(path).stem, tally, notes, len(results)))

    keys = ("agree", "disagree", "recovered", "missed", "both_silent")
    width = max(len(name) for name, *_ in rows) + 2
    print(f"{'reader':{width}s} {'crops':>5s} " +
          " ".join(f"{k:>11s}" for k in keys) + "   resolved-acc")
    for name, tally, _, n_crops in rows:
        resolved = tally["agree"] + tally["disagree"]
        acc = f"{tally['agree']}/{resolved}" if resolved else "-"
        pct = f" ({tally['agree'] / resolved:.0%})" if resolved else ""
        print(f"{name:{width}s} {n_crops:>5d} " +
              " ".join(f"{tally[k]:>11d}" for k in keys) + f"   {acc}{pct}")

    if args.detail:
        for name, _, notes, _ in rows:
            print(f"\n--- {name} ---")
            for note in notes:
                print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
