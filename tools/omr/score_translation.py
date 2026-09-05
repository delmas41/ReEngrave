"""Detected → exported → truth, per symbol family: where a signal is lost.

`export_coverage` already compares the truth's element counts against ours and
fires on the categorical case — the truth has some and we emit **zero**. That
found seven gaps. What it cannot see is the quantitative one: the truth has 30,
we emit 16, and the detector found 29. Same shape, different size, and
invisible until someone opens the bucket by hand.

The missing term is the DETECTOR's own count. With it the arithmetic separates
the two failures that OMR-NED fuses:

    truth 30 · detected  4 · exported  4   we never saw them        (reading)
    truth 30 · detected 29 · exported 16   we saw and lost them     (translation)

This generalises the funnel that located the eventless-measure bug, where 14
dynamics were read, computed into `<direction>` elements, and dropped by the
whole-measure-rest branch.

⚠️ **THE THREE COLUMNS ARE NOT ALWAYS IN THE SAME UNIT, and where they are not
this says so rather than quietly comparing them.** MusicXML writes a slur as a
`<slur>` at each end, so the truth's count is twice the arcs an engraver drew,
while the detector counts arcs. `unit_mismatch` marks those families; read the
DETECTED→EXPORTED delta there, never the raw ratio.

    python3 -m tools.omr.score_translation read.omr.json truth.musicxml
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .export import to_musicxml
from .export_coverage import element_counts

#: `family -> (detector class prefixes, MusicXML element, unit note)`.
#: The element is `export_coverage.VISIBLE`'s name, so the two tools cannot
#: drift apart on what a thing is called.
FAMILIES: dict[str, tuple[tuple[str, ...], str, str | None]] = {
    "accidental":      (("accidental",), "accidental", None),
    "augmentation_dot": (("augmentationdot",), "dot", None),
    "dynamic_letter":  (("dynamicp", "dynamicm", "dynamicf", "dynamics",
                         "dynamicz", "dynamicr"), "dynamics",
                        "the detector counts LETTERS, the file counts words: "
                        "`ff` is two detections and one <dynamics>"),
    "hairpin":         (("dynamiccrescendohairpin", "dynamicdiminuendohairpin"),
                        "wedge",
                        "MusicXML writes a <wedge> at each end, so the truth "
                        "counts two per hairpin"),
    "fermata":         (("fermata",), "fermata", None),
    "articulation":    (("artic",), "articulations",
                        "one <articulations> block can hold several marks"),
    "slur":            (("slur",), "slur",
                        "MusicXML writes a <slur> at each end, so the truth "
                        "counts two per arc"),
    "tie":             (("tie",), "tied",
                        "MusicXML writes a <tied> at each end"),
    "beam":            (("beam",), "beam",
                        "one <beam> per note per level, not per stroke"),
    "tuplet":          (("tuplet", "fingering3"), "tuplet",
                        "the detector counts digit/bracket glyphs"),
}


def detected_counts(result: dict[str, Any]) -> Counter:
    """How many of each family the DETECTOR put on the page."""
    out: Counter = Counter()
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                for meas in staff.get("measures", []):
                    for det in meas.get("detections", []):
                        norm = "".join(c for c in (det.get("class") or "").lower()
                                       if c.isalnum())
                        for family, (prefixes, _el, _n) in FAMILIES.items():
                            if any(norm.startswith(p) for p in prefixes):
                                out[family] += 1
                                break
    return out


def funnel(result: dict[str, Any], truth_xml: str,
           ours_xml: str | None = None) -> dict[str, Any]:
    ours = element_counts(ours_xml if ours_xml is not None else to_musicxml(result))
    truth = element_counts(truth_xml)
    det = detected_counts(result)

    rows = []
    for family, (_prefixes, element, note) in FAMILIES.items():
        rows.append({
            "family": family,
            "element": element,
            "detected": det.get(family, 0),
            "exported": ours.get(element, 0),
            "truth": truth.get(element, 0),
            "unit_mismatch": note,
        })
    return {"rows": rows}


def verdict(row: dict[str, Any]) -> str:
    """Which half of the pipeline a shortfall is in — or that there is none.

    ⚠️ Judged against the TRUTH, not against the detector. An early cut asked
    "did fewer reach the file than were detected" and called
    `augmentation_dot 120 -> 116` a drop, when the truth has 116 and the export
    is exactly right: four spurious detections were correctly not used. A
    detector count above the truth is over-detection, and the exporter refusing
    it is the pipeline working.

    ⚠️ The detected column is only comparable with the other two where
    `unit_mismatch` is None. Where it is not, the shortfall is reported without
    attributing it, rather than attributed on a number that does not mean the
    same thing.
    """
    t_, d, e = row["truth"], row["detected"], row["exported"]
    if t_ == 0 and e == 0:
        return ("absent from this work" if d == 0
                else f"{d} spurious detections, correctly not exported")
    if e == t_:
        return "matches the truth"
    if e > t_:
        return f"over-emitted ({e} vs {t_})"
    if e == 0 and d > 0:
        # Categorical, and the one verdict a unit mismatch cannot muddy: zero
        # is zero in any unit. This is the shape that has cost this project
        # nine fixes.
        return f"READ AND DROPPED — detected {d}, truth {t_}, exported NONE"
    if row["unit_mismatch"]:
        return f"short of the truth ({e} vs {t_}) — unit differs, inspect"
    if d >= t_:
        return f"READ AND LOST — detected {d}, truth {t_}, exported {e}"
    return f"UNDER-READ — detected {d} of {t_}, exported {e}"


def report(rows: list[dict[str, Any]]) -> None:
    print(f"{'family':18s} {'element':16s} {'detect':>7s} {'export':>7s} "
          f"{'truth':>6s}   verdict")
    for r in sorted(rows, key=lambda r: r["family"]):
        print(f"{r['family']:18s} {r['element']:16s} {r['detected']:7d} "
              f"{r['exported']:7d} {r['truth']:6d}   {verdict(r)}")
    notes = [r for r in rows if r["unit_mismatch"] and
             (r["detected"] or r["exported"] or r["truth"])]
    if notes:
        print("\n⚠️ different units, read the detected->exported step only:")
        for r in notes:
            print(f"   {r['family']}: {r['unit_mismatch']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcription", type=Path)
    ap.add_argument("truth", type=Path)
    ap.add_argument("--ours", type=Path,
                    help="our exported MusicXML (default: export it now)")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    result = json.loads(args.transcription.read_text())
    out = funnel(result, args.truth.read_text(),
                 args.ours.read_text() if args.ours else None)
    report(out["rows"])
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
