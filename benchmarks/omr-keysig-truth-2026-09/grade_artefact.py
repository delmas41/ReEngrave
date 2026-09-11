#!/usr/bin/env python3
"""Grade the SHIPPED artefact's key signatures against the hand-read print.

    python3 benchmarks/omr-keysig-truth-2026-09/grade_artefact.py

⚠️ IT GRADES TWICE, BECAUSE TWO DIFFERENT QUESTIONS HAVE DIFFERENT ANSWERS AND
POOLING THEM WOULD FLATTER US.

  * the READING grade — did `adjudicate_key_signature` decide, and was the
    decision right?  An abstention is its own outcome here, never a zero.
  * the FILE grade — what does a human cleaning the file up actually see?  A
    staff whose key abstained is exported with NO `<key>` element at all, and
    MusicXML has no way to say *"a reader could not tell"*: a missing key is
    read as no accidentals.  So an abstention on the Corni, Trombe and Timpani
    comes out RIGHT IN THE FILE by accident of the convention, and an
    abstention anywhere else comes out WRONG.  That is the ABSENT/DECLINED
    collapse this repo already records for empty measures, in the header.

⚠️ IT GRADES THE STAFF, NOT THE PART, and that is the whole reason it can
attribute anything.  The exported `<part>` is a JOIN of one staff per system;
if the join misaligns, a correctly-read key lands in the wrong part and a
part-level grade charges the key reader for the joiner's mistake.  The staff
column is what the key reader is responsible for; the part column is what the
reader plus the joiner produce together, and the difference between them is
the joiner's bill.

The instrument is the committed `system-map-p1-p4.json`, which
`build_sheet`'s own README says is *"derived by calling export.build; asserted
against the emitted XML measure-for-measure"* — so grading it is grading the
file, and no 132 MB record is needed.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MAP = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"
XML = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4.musicxml"


def load_truth() -> dict:
    return json.loads((HERE / "truth.json").read_text())


def rows(truth: dict, smap: dict) -> list[dict]:
    """One row per PRINTED staff, carrying what the file made of it."""
    by_sys = {(s["page"], s["system"]): s for s in smap["systems"]}
    out = []
    for t in truth["systems"]:
        got = by_sys.get((t["page"], t["system"]))
        if got is None:
            raise SystemExit(f"no system map row for page {t['page']} "
                             f"system {t['system']}")
        # ⚠️ A CONTROL THAT CAN FAIL. If the hand-read lineup and the machine's
        # staff count disagree, the two are not talking about the same system
        # and every row below it would be silently offset.
        if len(got["staves"]) != len(t["lineup"]):
            raise SystemExit(
                f"page {t['page']} system {t['system']}: hand-read "
                f"{len(t['lineup'])} printed staves, the file has "
                f"{len(got['staves'])} — grading them would be a guess")
        for i, inst in enumerate(t["lineup"]):
            st = got["staves"][i]
            spec = truth["instruments"][inst]
            out.append({
                "page": t["page"], "system": t["system"], "staff": i,
                "instrument": inst,
                "truth_fifths": spec["fifths"], "truth_clef": spec["clef"],
                "read_fifths": st["fifths"], "read_clef": st["clef"],
                "slot": st["part_index"], "part_id": st["part_id"],
            })
    return out


def grade_reading(r: dict) -> str:
    if r["read_fifths"] is None:
        return "abstained"
    return "correct" if r["read_fifths"] == r["truth_fifths"] else "wrong"


def grade_file(r: dict) -> str:
    """What the file says. A missing <key> is no accidentals to any reader."""
    in_file = 0 if r["read_fifths"] is None else r["read_fifths"]
    return "right" if in_file == r["truth_fifths"] else "WRONG"


def grade_clef(r: dict) -> str:
    if r["read_clef"] is None:
        return "abstained"
    return "correct" if r["read_clef"] == r["truth_clef"] else "wrong"


def main(argv: list[str]) -> int:
    truth = load_truth()
    smap = json.loads(MAP.read_text())
    rs = rows(truth, smap)

    print(f"REACH: {len(rs)} printed staff-systems over "
          f"{len(truth['systems'])} systems, 4 pdf pages.\n")

    print(f"{'pg/sy':>6} {'#':>2} {'instrument':<20} {'truth':>5} "
          f"{'read':>5}  {'reading':<9} {'file':<5} "
          f"{'clef(t)':<7} {'clef(r)':<7} {'clef':<9} slot")
    for r in rs:
        print(f"{r['page']}/{r['system']:<4} {r['staff']:>2} "
              f"{r['instrument']:<20} {r['truth_fifths']:>5} "
              f"{str(r['read_fifths']):>5}  {grade_reading(r):<9} "
              f"{grade_file(r):<5} {r['truth_clef']:<7} "
              f"{str(r['read_clef']):<7} {grade_clef(r):<9} {r['slot']}")

    def tally(fn):
        t: dict[str, int] = {}
        for r in rs:
            t[fn(r)] = t.get(fn(r), 0) + 1
        return t

    print("\nREADING (what adjudicate_key_signature did):", tally(grade_reading))
    print("FILE    (what a human cleaning up sees)    :", tally(grade_file))
    print("CLEF    (the upstream question)            :", tally(grade_clef))

    wrong = [r for r in rs if grade_reading(r) == "wrong"]
    print(f"\nWRONG READINGS: {len(wrong)}")
    for r in wrong:
        print(f"  p{r['page']}/s{r['system']} staff {r['staff']:>2} "
              f"{r['instrument']:<20} truth {r['truth_fifths']:>3} "
              f"read {r['read_fifths']:>3}  clef read "
              f"{r['read_clef']} ({grade_clef(r)})")

    # ── The joiner's bill, stated apart from the reader's ──────────────────
    # A staff whose slot is not its instrument's slot puts whatever was read
    # into another instrument's part. That is not a key-signature defect and
    # must not be counted as one.
    canonical: dict[str, int] = {}
    for r in rs:
        if r["page"] == 1:
            canonical[r["instrument"]] = r["slot"]
    canonical.setdefault("Violoncello e Basso", canonical["Violoncello"])
    misjoined = [r for r in rs
                 if canonical.get(r["instrument"]) is not None
                 and r["slot"] != canonical[r["instrument"]]]
    print(f"\nSTAFF-SYSTEMS JOINED TO THE WRONG PART: {len(misjoined)} of "
          f"{len(rs)}  (slots anchored on page 1's full 12-staff lineup)")
    for r in misjoined:
        print(f"  p{r['page']}/s{r['system']} staff {r['staff']:>2} "
              f"{r['instrument']:<20} -> slot {r['slot']} "
              f"({r['part_id']}), belongs in slot "
              f"{canonical[r['instrument']]}")

    if "--check" in argv:
        # A positive control: the grader must actually be reading a file with
        # key signatures in it. A run that found none would print a clean
        # sheet of abstentions and look like a result.
        read = sum(1 for r in rs if r["read_fifths"] is not None)
        if read == 0:
            print("\nDEAD INSTRUMENT: no staff carries a key signature at "
                  "all — this is not a result, it is a broken input.")
            return 2
    json.dump(rs, (HERE / "grade-before.json").open("w"), indent=1)
    print(f"\nwrote {HERE / 'grade-before.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
