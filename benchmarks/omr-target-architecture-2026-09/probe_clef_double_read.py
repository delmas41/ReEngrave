#!/usr/bin/env python3
"""Are the pipeline's TWO clef readings independent? — read-only.

`docs/architecture-decision-map.md` §3.2(b) records that a clef is read twice
per staff (the header pre-pass at `transcribe.py:4677`, and the measure pass)
and that the two are never compared, calling the comparison "free" and
"UNMEASURED". This probe measures it from stored artefacts and answers a
narrower question than the one that was asked, because the wider one is
answered statically:

  * the pre-pass clef rung is `_clef_from_dets(_header_detections(detector,
    start_cells[0], ...))` and the measure-pass rung is the argmax inside
    `_detections_for_cell(detector, staff_cells[0], ...)`.
    `start_cells` and `staff_cells` are both `systems[sys_idx][staff_idx]` —
    the SAME list object — and both calls pass the same conf/imgsz/iou/nms.
    The clef subset of the detections is untouched between them
    (`_drop_clipped_notehead_fragments` filters noteheads only), and both
    take a strict-greater argmax over the same list in the same order.
    So where the detector speaks, the two readings agree BY CONSTRUCTION.

  * therefore the only staves on which the two readings CAN differ are those
    where the detector was silent on that cell, and each side then falls
    through to a different rung on a DIFFERENT CROP.

What this measures, per staff carrying `clef_evidence`:

  A  the two detector rungs' SILENCE coincides
     (`contest.n_resolved == 0`  vs  `cv_locator_header_prepass` present —
     the pre-pass locator runs only when the pre-pass detector said nothing)
  B  on the silent population, whether the CV locator reading the HEADER crop
     and the CV locator reading the MEASURE cell reach the same verdict.

Input: transcription JSONs that carry `clef_evidence`. That key is written
unconditionally but is a build product — no committed artefact holds it. It is
produced by a scan-gate arm, e.g.

    python3 -m tools.omr.training.scan_eval --tag=clefcontest   # ~2600 s

Pass the fixtures directory holding the resulting `*.omr.json`.

Exit codes:  0 measured · 1 an internal cross-check failed · 2 missing or
empty input (no directory, no matching files, or no staff carrying
`clef_evidence`).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path


def staves_with_evidence(paths):
    for path in paths:
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError) as exc:  # unreadable is not "empty"
            print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
            raise SystemExit(2)
        for page in doc.get("pages", []):
            for system in page.get("systems", []):
                for staff in system.get("staves", []):
                    if staff.get("clef_evidence"):
                        yield path.name, staff


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", required=True, type=Path,
                    help="directory of transcription JSONs carrying clef_evidence")
    ap.add_argument("--glob", default="*.omr.json")
    args = ap.parse_args()

    if not args.fixtures.is_dir():
        print(f"REFUSED: no such directory: {args.fixtures}", file=sys.stderr)
        return 2
    paths = sorted(args.fixtures.glob(args.glob))
    if not paths:
        print(f"REFUSED: no files matching {args.glob!r} in {args.fixtures}",
              file=sys.stderr)
        return 2

    n_staves = 0
    silence = collections.Counter()          # (measure_silent, prepass_silent)
    verdicts = collections.Counter()         # (header_crop_clef, measure_cell_clef)
    reasons = collections.Counter()
    divergent: list[tuple] = []
    for name, staff in staves_with_evidence(paths):
        ev = staff["clef_evidence"]
        n_staves += 1
        contest = ev.get("contest") or {}
        measure_silent = int(contest.get("n_resolved", 0)) == 0
        prepass = ev.get("cv_locator_header_prepass")
        silence[(measure_silent, prepass is not None)] += 1
        measure_loc = ev.get("cv_locator")
        if prepass is None or measure_loc is None:
            continue
        a, b = prepass.get("clef"), measure_loc.get("clef")
        verdicts[(a, b)] += 1
        reasons[(prepass.get("reason"), measure_loc.get("reason"))] += 1
        if a != b:
            divergent.append((
                name, staff.get("staff_index"),
                prepass.get("reason"), a, prepass.get("symmetry"),
                measure_loc.get("reason"), b, measure_loc.get("symmetry"),
                staff.get("clef_source"), staff.get("clef"),
            ))

    if n_staves == 0:
        print(f"REFUSED: {len(paths)} file(s) read, no staff carries "
              f"'clef_evidence'. These are not clef-contest artefacts.",
              file=sys.stderr)
        return 2

    n_both_silent = silence[(True, True)]
    n_split = silence[(True, False)] + silence[(False, True)]
    print(f"files                                   {len(paths)}")
    print(f"staves carrying clef_evidence           {n_staves}")
    print()
    print("A · do the two DETECTOR rungs fall silent on the same staves?")
    print(f"  both spoke                            {silence[(False, False)]}")
    print(f"  both silent                           {n_both_silent}")
    print(f"  DIVERGENT (one silent, one not)       {n_split}")
    print()
    n_pairs = sum(verdicts.values())
    if n_pairs:
        agree = sum(v for k, v in verdicts.items() if k[0] == k[1])
        both_found = sum(v for k, v in verdicts.items()
                         if k[0] is not None and k[1] is not None)
        neither = verdicts[(None, None)]
        print("B · on the silent population, the CV locator read TWICE — "
              "header crop vs measure cell")
        print(f"  staves with both locator runs         {n_pairs}")
        print(f"  same verdict                          {agree}"
              f"   (of which BOTH FOUND NOTHING: {neither})")
        print(f"  both located a clef                   {both_found}")
        print(f"  DIFFERENT verdict                     {n_pairs - agree}")
        print()
        print("  by direction:")
        for (a, b), n in sorted(verdicts.items(), key=lambda kv: -kv[1]):
            if a != b:
                print(f"    header={a!s:<7} measure={b!s:<7} {n}")
        # Of the divergent staves, how many END on a clef that contradicts
        # the one a locator DID read at runtime? A located reading that the
        # staff then agrees with cost nothing; one it contradicts is a live
        # disagreement the pipeline resolved without recording that it had one.
        contradicted = [r for r in divergent
                        if (r[9] or "").split("_")[0] != (r[3] or r[6])]
        print(f"  final clef CONTRADICTS the located one   "
              f"{len(contradicted)} of {len(divergent)}")
        print()
        print("  the divergent staves (file, staff, header reason/clef/sym, "
              "measure reason/clef/sym, final source, final clef):")
        for row in divergent:
            sa = f"{row[4]:.3f}" if isinstance(row[4], (int, float)) else "-"
            sb = f"{row[7]:.3f}" if isinstance(row[7], (int, float)) else "-"
            print(f"    {row[0][:38]:<38} s{row[1]:<3} "
                  f"{row[2]:<14}{str(row[3]):<7}{sa:<7} "
                  f"{row[5]:<14}{str(row[6]):<7}{sb:<7} "
                  f"{str(row[8]):<16}{row[9]}")

    # Cross-check: the pre-pass locator runs IF AND ONLY IF the pre-pass
    # detector was silent, and the measure-pass contest records the measure
    # detector's silence. If the two detector rungs are the same call on the
    # same object, `n_split` must be 0. A non-zero value falsifies the static
    # argument in this docstring and is a finding, not a probe bug — so it is
    # reported, and the exit code says the cross-check failed.
    if n_split:
        print(f"\nCROSS-CHECK FAILED: {n_split} staves where exactly one "
              f"detector rung was silent. The two rungs are NOT the same call.",
              file=sys.stderr)
        return 1
    print("\ncross-check: the two detector rungs' silence coincides on "
          f"{n_staves}/{n_staves} staves — consistent with them being the "
          "same call on the same cell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
