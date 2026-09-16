"""music21 READ-BACK: does `<measure number=N>` name one instant, to a parser?

    python3 benchmarks/omr-measure-numbering-2026-09/probe/read_back.py --check

⚠️ THE ARM NEXT DOOR CHECKS THE TEXT; THIS CHECKS WHAT A CONSUMER SEES. The
defect was reported by Verovio (`Mismatching measure number 87`), i.e. by a
reader parsing the file — so the repair has to be verified the same way and
not by reading the attribute we just wrote. music21 is the reader available
here (Python 3.11 in this container, so it imports in process).

Two questions, and the second is the one that matters:

  1. **The identical-music control.** Parsed, the two files must hold the same
     parts, the same number of measures per part, and the SAME NOTE SEQUENCE —
     pitch and quarter-length, in order. If any of that moves, the change
     wrote music and must be stopped. ⚠️ Its POSITIVE control is that the
     measure NUMBERS parsed back do differ, or the whole comparison is being
     run against a file that was never renumbered.

  2. **One number, one instant.** music21 gives the measure numbers each part
     carries, in order; the system map gives what the nth measure of each part
     IS — `(page, system, bar within the system)`. Joining them says whether a
     number names one instant across the whole file. That join is the only
     place the map is used, and it is used for the TRUTH side, never to
     produce the numbers being checked.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent

BASE = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4.musicxml"
NEW = HERE / "out/beethoven5-mvt1-p1-p4.document-numbered.musicxml"
SYSTEM_MAP = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"


def read(path):
    from music21 import converter
    score = converter.parse(str(path), format="musicxml")
    parts = []
    for p in score.parts:
        measures = list(p.getElementsByClass("Measure"))
        seq = []
        for m in measures:
            for n in m.recurse().notesAndRests:
                seq.append((getattr(n, "nameWithOctave", None)
                            or ("chord:" + ".".join(
                                x.nameWithOctave for x in n)
                                if n.isChord else "rest"),
                            float(n.duration.quarterLength)))
        parts.append({"id": p.id,
                      "numbers": [m.number for m in measures],
                      "n_measures": len(measures),
                      "sequence": seq})
    return parts


def instants_from_map(smap):
    """`{part_index: [(page, system, bar_in_system), ...]}` in file order."""
    order, by_part = [], collections.defaultdict(list)
    for sd in smap["systems"]:
        key = (sd["page"], sd["system"])
        order.append(key)
        for st in sd["staves"]:
            by_part[st["part_index"]].append(
                (order.index(key), key, int(st["n_measures"])))
    out = {}
    for pi, rows in by_part.items():
        seq = []
        for _o, key, n in sorted(rows, key=lambda r: r[0]):
            seq.extend((key[0], key[1], i) for i in range(n))
        out[pi] = seq
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not NEW.is_file():
        print("INSTRUMENT DEAD: run numbering_arm.py --write first")
        return 2

    smap = json.loads(SYSTEM_MAP.read_text())
    base, new = read(BASE), read(NEW)
    problems = []

    print("=" * 78)
    print("0. REACH")
    print("=" * 78)
    print("   parts parsed      : %d / %d" % (len(base), len(new)))
    print("   measures parsed   : %d / %d"
          % (sum(p["n_measures"] for p in base),
             sum(p["n_measures"] for p in new)))
    print("   note+rest events  : %d / %d"
          % (sum(len(p["sequence"]) for p in base),
             sum(len(p["sequence"]) for p in new)))
    if not base or not any(p["sequence"] for p in base):
        print("INSTRUMENT DEAD: nothing parsed back.")
        return 2

    # ── 1. identical music ──────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("1. IDENTICAL-MUSIC CONTROL (music21, parsed)")
    print("=" * 78)
    same_ids = [p["id"] for p in base] == [p["id"] for p in new]
    same_counts = ([p["n_measures"] for p in base]
                   == [p["n_measures"] for p in new])
    same_seq = all(a["sequence"] == b["sequence"] for a, b in zip(base, new))
    print("   same part ids                  : %s" % same_ids)
    print("   same measure count per part    : %s" % same_counts)
    print("   same NOTE SEQUENCE per part    : %s" % same_seq)
    numbers_differ = any(a["numbers"] != b["numbers"]
                         for a, b in zip(base, new))
    print("   measure NUMBERS differ (positive control): %s" % numbers_differ)
    for flag, msg in ((same_ids, "part ids moved"),
                      (same_counts, "measure counts moved"),
                      (same_seq, "THE NOTE SEQUENCE MOVED — this change wrote music"),
                      (numbers_differ, "numbers identical: nothing was renumbered")):
        if not flag:
            problems.append(msg)

    # ── 2. one number, one instant ──────────────────────────────────────────
    print()
    print("=" * 78)
    print("2. ONE NUMBER, ONE INSTANT — music21's numbers x the system map")
    print("=" * 78)
    truth = instants_from_map(smap)
    for label, parsed in (("per-part (committed)", base),
                          ("document (renumbered)", new)):
        names = collections.defaultdict(set)
        mismatched = 0
        for pi, p in enumerate(parsed):
            seq = truth.get(pi, [])
            if len(seq) != len(p["numbers"]):
                mismatched += 1
                continue
            for num, inst in zip(p["numbers"], seq):
                names[num].add(inst)
        ambiguous = {n: v for n, v in names.items() if len(v) > 1}
        print("   %-22s numbers %4d   AMBIGUOUS %3d   parts the map could "
              "not align %d"
              % (label, len(names), len(ambiguous), mismatched))
        if mismatched:
            problems.append("%s: the map does not align with the parsed file"
                            % label)
        if label.startswith("document") and ambiguous:
            problems.append("the document scheme still has %d ambiguous "
                            "numbers" % len(ambiguous))
        if label.startswith("per-part"):
            for n, v in sorted(ambiguous.items())[:3]:
                print("        number %-4d names %s"
                      % (n, ", ".join("p%d/s%d bar %d" % t for t in sorted(v))))

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
    else:
        print("ALL CONTROLS PASS")
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
