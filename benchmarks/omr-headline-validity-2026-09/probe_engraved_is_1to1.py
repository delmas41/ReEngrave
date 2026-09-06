"""Is the ENGRAVED headline's page a faithful rendering of its own truth?

The 11-work engraved benchmark builds its input page BY RENDERING THE TRUTH:
`orchestral_eval.excerpt()` writes `<work>.musicxml` from a music21 `Score`,
runs `musicxml2ly` on THAT FILE, and renders the resulting `.ly` with LilyPond.
So the page and the truth are the same object twice, and Sean's fault —
"2 flutes on one staff on the page and 2 separate staves in the MXL" — cannot
occur there: an encoding that splits the flutes renders two flute staves.

This probe stops that from being an argument and makes it a measurement, per
work, on the fixtures actually scored:

  truth parts     `<score-part>` in `fixtures/<work>.musicxml` (ElementTree)
  page staves     staff CONTEXTS in `fixtures/<work>.ly`, the file LilyPond drew
  our parts       `<score-part>` in `fixtures/<work>.omr.musicxml`

⚠️ THE ONE LEGITIMATE INEQUALITY IS A GRAND STAFF, AND IT RUNS THE OTHER WAY.
`musicxml2ly` flattens a part declaring `<staves>2</staves>` into two Staff
contexts, so a 2-staff part renders as 2 staves — one part, two staves. That is
a SPLIT, the opposite of condensation, and it never leaves a truth part without
a printed staff. The probe reports declared staves alongside part counts so the
two directions cannot be confused.

    python3 benchmarks/omr-headline-validity-2026-09/probe_engraved_is_1to1.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import accuracy_record  # noqa: E402

FIX = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
# ⚠️ COUNTING `\new Staff` ALONE UNDERCOUNTS, and the first cut of this probe
# reported Mahler 34-against-38 and Dvořák 17-against-19 because of it — i.e. it
# manufactured exactly the condensation it was written to rule out. musicxml2ly
# emits ONE context per part, but the context is `\new DrumStaff` for
# unpitched percussion and `\new RhythmicStaff` for a one-line part, and a part
# declaring two staves becomes a `\new PianoStaff` wrapping `\context Staff =
# "1"` and `\context Staff = "2"`. Printed staves = one per top-level context,
# plus one extra for each numbered inner Staff beyond the wrapper.
NEW_STAFF = re.compile(r"\\new\s+(?:Drum|Rhythmic|Tab)?Staff\b")
PIANO_STAFF = re.compile(r"\\new\s+(?:Piano|Grand)Staff\b")
INNER_STAFF = re.compile(r'\\context\s+Staff\s*=\s*"')


def printed_staves(ly_text: str) -> dict:
    """How many staves LilyPond actually draws, by context kind."""
    plain = len(NEW_STAFF.findall(ly_text))
    piano = len(PIANO_STAFF.findall(ly_text))
    inner = len(INNER_STAFF.findall(ly_text))
    return {"plain_staff_contexts": plain, "piano_staff_wrappers": piano,
            "numbered_inner_staves": inner, "total": plain + inner}


def parts_and_staves(xml: Path) -> tuple[int, int, list[str]]:
    root = ET.parse(xml).getroot()
    ids = [sp.get("id") for sp in root.iter("score-part")]
    declared = {}
    for part in root.iter("part"):
        n = 1
        for st in part.iter("staves"):
            try:
                n = max(n, int((st.text or "1").strip()))
            except ValueError:
                pass
        declared[part.get("id")] = n
    multi = [pid for pid in ids if declared.get(pid, 1) > 1]
    return len(ids), sum(declared.get(pid, 1) for pid in ids), multi


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BENCH / "engraved-1to1.json"))
    args = ap.parse_args(argv)

    rows = []
    for work in accuracy_record.BENCHMARK_WORKS:
        truth = FIX / f"{work}.musicxml"
        ly = FIX / f"{work}.ly"
        ours = FIX / f"{work}.omr.musicxml"
        if not truth.is_file() or not ly.is_file():
            rows.append({"work": work, "missing": True})
            continue
        n_parts, n_declared, multi = parts_and_staves(truth)
        staffing = printed_staves(ly.read_text(errors="replace"))
        n_ly = staffing["total"]
        entry = {
            "work": work,
            "truth_parts": n_parts,
            "truth_declared_staves": n_declared,
            "multi_staff_parts": multi,
            "ly_printed_staves": n_ly,
            "ly_contexts": staffing,
            "page_staves_equal_truth_declared_staves": n_ly == n_declared,
            "every_truth_part_has_a_printed_staff": n_ly >= n_parts,
            "condensation_present": n_ly < n_parts,
        }
        if ours.is_file():
            entry["our_parts"] = parts_and_staves(ours)[0]
        rows.append(entry)

    ok = [r for r in rows if not r.get("missing")]
    doc = {
        "generated_by": "benchmarks/omr-headline-validity-2026-09/"
                        "probe_engraved_is_1to1.py",
        "works": rows,
        "verdict": {
            "n_works": len(ok),
            "n_with_condensation": sum(1 for r in ok if r["condensation_present"]),
            "n_page_staves_match_declared": sum(
                1 for r in ok if r["page_staves_equal_truth_declared_staves"]),
            "works_where_staves_exceed_parts": [
                r["work"] for r in ok if r["ly_printed_staves"] > r["truth_parts"]],
        },
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")

    staff_col = "printed"
    print(f"{'work':26s} {'parts':>6s} {'declared':>9s} {staff_col:>11s} "
          f"{'ours':>5s}  condensation?")
    for r in rows:
        if r.get("missing"):
            print(f"{r['work']:26s}  (no fixture on disk)")
            continue
        print(f"{r['work']:26s} {r['truth_parts']:>6d} "
              f"{r['truth_declared_staves']:>9d} {r['ly_printed_staves']:>11d} "
              f"{r.get('our_parts', '-'):>5}  "
              f"{'YES' if r['condensation_present'] else 'none'}")
    v = doc["verdict"]
    print()
    print(f"works with a truth part that has NO printed staff: "
          f"{v['n_with_condensation']} of {v['n_works']}")
    print(f"page staff count == truth declared staff count on "
          f"{v['n_page_staves_match_declared']} of {v['n_works']}")
    if v["works_where_staves_exceed_parts"]:
        print("staves EXCEED parts (a grand staff split, the harmless "
              "direction) on: " + ", ".join(v["works_where_staves_exceed_parts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
