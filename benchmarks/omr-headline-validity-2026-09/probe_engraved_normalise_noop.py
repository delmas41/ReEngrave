"""Does page-normalisation move the ENGRAVED pool? It must not, and here is why.

The coordinator asked for this explicitly: *"if normalisation is anything other
than a no-op on the engraved pool, that is a finding about the renderer."*

There is no hand-read `staves` map for the engraved works and there does not
need to be one: `probe_engraved_is_1to1.py` measures that the rendered page
prints exactly the truth's DECLARED staves on 11 of 11 works, with zero parts
lacking a printed staff. So the page's staff list IS the truth's part list, and
the only map page-normalisation could be given is the IDENTITY — one part per
staff, nothing merged.

This probe hands it exactly that and scores the same prediction against both
truths. Any movement is a defect in the transform (or in the renderer), not a
measurement.

    python3 benchmarks/omr-headline-validity-2026-09/probe_engraved_normalise_noop.py
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))

import page_normalise  # noqa: E402
from tools.omr import accuracy_record, omr_ned as omr_ned_mod  # noqa: E402

FIX = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
DERIVED = BENCH / "derived-truth-engraved"


def identity_map(xml: Path) -> list[dict]:
    """One staff per part — indexed the way `page_normalise` indexes.

    ⚠️ NOT by `<score-part>`. music21 splits a part declaring `<staves>2</staves>`
    into two `PartStaff` objects, so `.parts` is LONGER than the score-part list
    on exactly the two works that have a grand staff. Building the map from the
    XML gave 18 entries against 19 parts on Dvořák 9, the transform dropped the
    unnamed one, and the work "improved" by 42 edits. It now refuses instead
    (`IncompleteMap`); this builds the map from the same list the transform
    walks.
    """
    from music21 import converter

    parts = list(converter.parse(str(xml)).parts)
    return [{"name": getattr(p, "partName", None) or f"P{i}", "parts": [i]}
            for i, p in enumerate(parts)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", nargs="+", default=None)
    ap.add_argument("--out", default=str(BENCH / "engraved-normalise-noop.json"))
    args = ap.parse_args(argv)

    works = args.works or list(accuracy_record.BENCHMARK_WORKS)
    pairs, rows = [], []
    for work in works:
        truth = FIX / f"{work}.musicxml"
        pred = FIX / f"{work}.omr.musicxml"
        if not truth.is_file() or not pred.is_file():
            rows.append({"work": work, "skipped": "no fixture"})
            continue
        norm = DERIVED / f"{work}.identity-normalised.musicxml"
        rep = page_normalise.write(truth, identity_map(truth), norm,
                                   source_reference=str(truth))
        rows.append({"work": work,
                     "n_source_parts": rep["n_source_parts"],
                     "n_output_parts": rep["n_output_parts"],
                     "measure_census": rep["measure_census"]})
        pairs.append((f"{work}|raw", pred, truth))
        pairs.append((f"{work}|norm", pred, norm))

    scored = omr_ned_mod.score_batch(pairs, detail="AllObjects")
    by = {p["name"]: p for p in scored.get("pairs", [])}
    moved = []
    for r in rows:
        if r.get("skipped"):
            continue
        a = by.get(f"{r['work']}|raw") or {}
        b = by.get(f"{r['work']}|norm") or {}
        r["raw"] = {"omr_ned": a.get("omr_ned"), "omr_ed": a.get("omr_ed")}
        r["identity_normalised"] = {"omr_ned": b.get("omr_ned"),
                                    "omr_ed": b.get("omr_ed")}
        r["delta_edits"] = (b.get("omr_ed", 0) - a.get("omr_ed", 0))
        if r["delta_edits"]:
            moved.append(r["work"])

    doc = {"generated_by": "benchmarks/omr-headline-validity-2026-09/"
                           "probe_engraved_normalise_noop.py",
           "transform_version": page_normalise.TRANSFORM_VERSION,
           "verdict": {"n_scored": len([r for r in rows if not r.get("skipped")]),
                       "works_that_moved": moved,
                       "is_a_no_op": not moved},
           "works": rows}
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")

    print(f"{'work':26s} {'raw ed':>7s} {'norm ed':>8s} {'delta':>7s}")
    for r in rows:
        if r.get("skipped"):
            print(f"{r['work']:26s}  {r['skipped']}")
            continue
        print(f"{r['work']:26s} {r['raw']['omr_ed']:>7d} "
              f"{r['identity_normalised']['omr_ed']:>8d} "
              f"{r['delta_edits']:>+7d}")
    print()
    print("NO-OP" if not moved else f"MOVED on: {', '.join(moved)}")
    return 0 if not moved else 1


if __name__ == "__main__":
    sys.exit(main())
