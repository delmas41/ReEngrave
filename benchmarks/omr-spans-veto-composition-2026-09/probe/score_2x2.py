"""Score the 2x2 from two `compose.py` report blobs.

Every cell is reported with BOTH numbers, because one hides which outcome you
got:

  IMPOSSIBLE          staves before the finale named Piccolo / Contrabassoon /
                      Trombone. Beethoven's trombones enter in the finale and
                      the reference encodings' part lists say movements 1-3
                      contain none of the three, so any such name is
                      categorically wrong whatever the page prints. The BENEFIT.
  CORRECT / WRONG /   on FULL systems only, against the printed lineup. A veto
  UNNAMED             turns a name into `unnamed`; whether that name was right
                      is the COST, and a single "impossible" count cannot say.

The distinction the veto branch insists on is kept: `refused` (unnamed, honest)
is not `misnamed` (wrong, not honest).

## Where the names come from, and the one assumption

`compose.py` writes no staff dicts, so a staff's emitted name is its slot's
name -- which is exactly what the blob records (`staff_slots` x
`slot_instruments`). That covers every instrument this bug is about: on
Beethoven 5 all three trombones, the piccolo and the contrabassoon are
`label`-sourced slots.

⚠️ ASSUMPTION: a system's staves run top to bottom in `staff_index` order.
`absent_instrument._anchored_keys` already relies on this (it sorts staff
indices and treats the result as vertical order), and it is checked here rather
than assumed: the judgeable-staff count is asserted against the 807 the
absent-instrument branch's FULL transcription scored through
`staff_geometry.line_ys_page`. A different ordering would not give the same
count on the same systems.

Usage:  score_2x2.py SPANS-OFF.json SPANS-ON.json [--expect-judgeable 807]
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

FINALE_ONLY = {"Piccolo", "Contrabassoon", "Trombone"}
FINALE_FIRST_PAGE = 44

# (first_page, last_page, size) -> lineup, top to bottom. Read off the print by
# the absent-instrument branch (crops/p1-margin.png, crops/p44-margin.png) and
# copied verbatim so the two measurements are scored against one truth.
LINEUPS = [
    (0, 43, 12, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
                 "Timpani", "Violin", "Violin", "Viola", "Cello",
                 "Contrabass"]),
    (44, 200, 17, ["Piccolo", "Flute", "Oboe", "Clarinet", "Bassoon",
                   "Contrabassoon", "Horn", "Trumpet", "Timpani",
                   "Trombone", "Trombone", "Trombone", "Violin", "Violin",
                   "Viola", "Cello", "Contrabass"]),
]


def load(path):
    r = json.load(open(path))
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not b:
        raise SystemExit(f"REFUSING: {path} has no veto report block")
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in b["staff_slots"]}
    name_by_slot = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    vetoed = {(v["page_index"], v["system_index"], v["staff_index"])
              for v in b["vetoes"]}
    veto_rows = {(v["page_index"], v["system_index"], v["staff_index"]): v
                 for v in b["vetoes"]}
    return {
        "path": path,
        "mvt": r.get("movement_reference"),
        "reference": (r.get("contextual") or {}).get("reference") or [],
        "slot_by_staff": slot_by_staff,
        "name_by_slot": name_by_slot,
        "vetoed": vetoed,
        "veto_rows": veto_rows,
        "rule": b.get("rule"), "window": b.get("window"), "mode": b.get("mode"),
    }


def names(arm, veto_on: bool) -> dict[tuple[int, int, int], str | None]:
    """The name each staff record comes out with, in one cell of the 2x2."""
    out = {}
    for key, slot in arm["slot_by_staff"].items():
        if veto_on and key in arm["vetoed"]:
            out[key] = None
        else:
            out[key] = arm["name_by_slot"].get(slot) if slot >= 0 else None
    return out


def truth_for(page: int, size: int):
    for lo, hi, n, lineup in LINEUPS:
        if lo <= page <= hi and size == n:
            return lineup
    return None


def judgeable(keys) -> dict[tuple[int, int, int], str]:
    """`{staff key: printed instrument}` for staves on FULL systems only.

    A system carrying every staff the region has needs no page-by-page reading:
    nothing can be added to a full lineup, so a system of exactly N staves in a
    region whose lineup is N IS that lineup, in printed order. Reduced systems
    are not scored -- which parts were dropped is a fact about the page.
    """
    by_system: dict[tuple[int, int], list[int]] = {}
    for page, system, staff in keys:
        by_system.setdefault((page, system), []).append(staff)
    out = {}
    for (page, system), staves in by_system.items():
        lineup = truth_for(page, len(staves))
        if lineup is None:
            continue
        for pos, staff in enumerate(sorted(staves)):
            out[(page, system, staff)] = lineup[pos]
    return out


def cell(tag, emitted, truth):
    before = [k for k in emitted if k[0] < FINALE_FIRST_PAGE]
    bad = [k for k in before if emitted[k] in FINALE_ONLY]
    correct = wrong = unnamed = 0
    for k, want in truth.items():
        got = emitted.get(k)
        if got is None:
            unnamed += 1
        elif got == want:
            correct += 1
        else:
            wrong += 1
    return {
        "tag": tag,
        "impossible": len(bad),
        "impossible_keys": set(bad),
        "impossible_by_name": collections.Counter(emitted[k] for k in bad),
        "impossible_pages": sorted({k[0] for k in bad}),
        "staves_before_finale": len(before),
        "judgeable": len(truth),
        "correct": correct, "wrong": wrong, "unnamed": unnamed,
        "correct_keys": {k for k, want in truth.items()
                         if emitted.get(k) == want},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spans_off")
    ap.add_argument("spans_on")
    ap.add_argument("--expect-judgeable", type=int, default=807)
    ap.add_argument("--expect-baseline-impossible", type=int, default=91)
    args = ap.parse_args()

    off = load(args.spans_off)
    on = load(args.spans_on)

    if set(off["slot_by_staff"]) != set(on["slot_by_staff"]):
        raise SystemExit("REFUSING: the two arms saw different staff records — "
                         "they did not share a read pass")
    keys = list(off["slot_by_staff"])
    truth = judgeable(keys)

    print("=== INPUT ASSERTIONS ===")
    print(f"  staff records          : {len(keys)}")
    print(f"  pages                  : {len({k[0] for k in keys})}")
    print(f"  reference slots        : off={len(off['reference'])} "
          f"on={len(on['reference'])}")
    print(f"  veto config            : mode={off['mode']} rule={off['rule']} "
          f"window={off['window']}")
    print(f"  judgeable (full systems): {len(truth)} "
          f"(expected {args.expect_judgeable})")
    if len(truth) != args.expect_judgeable:
        print("  ⚠️ JUDGEABLE COUNT DISAGREES with the absent-instrument "
              "branch's full transcription. Either the staff ordering "
              "assumption is wrong or the segmentation moved — do not read "
              "the cost column until this is explained.")
    slots_changed = sum(1 for k in keys
                        if off["slot_by_staff"][k] != on["slot_by_staff"][k])
    print(f"  slot assignments moved by spans: {slots_changed} of {len(keys)}")

    cells = {}
    for stag, arm in (("spans-off", off), ("spans-on", on)):
        for vtag, von in (("veto-off", False), ("veto-on", True)):
            cells[(stag, vtag)] = cell(f"{stag} / {vtag}",
                                       names(arm, von), truth)

    base = cells[("spans-off", "veto-off")]
    print()
    print("=== BASELINE VALIDATION ===")
    print(f"  spans-off / veto-off IMPOSSIBLE = {base['impossible']} "
          f"(the whole-work session's figure: "
          f"{args.expect_baseline_impossible})")
    if base["impossible"] != args.expect_baseline_impossible:
        print("  ⚠️ THE BASELINE DOES NOT REPRODUCE. This harness is measuring "
              "something narrower than the claim and NO OTHER ARM IS "
              "COMPARABLE TO IT. Stop here.")
    for k, v in base["impossible_by_name"].most_common():
        print(f"      {v:4d}  {k}")
    print(f"  on pages: {base['impossible_pages']}")

    print()
    print("=== THE 2x2 ===")
    print(f"{'':22s} {'IMPOSSIBLE':>11s} {'correct':>8s} {'wrong':>7s} "
          f"{'unnamed':>8s}   of {len(truth)} judgeable")
    for stag in ("spans-off", "spans-on"):
        for vtag in ("veto-off", "veto-on"):
            c = cells[(stag, vtag)]
            print(f"  {stag:10s} {vtag:9s} {c['impossible']:11d} "
                  f"{c['correct']:8d} {c['wrong']:7d} {c['unnamed']:8d}")

    print()
    print("=== CORRECT NAMES LOST, against the baseline cell ===")
    for stag in ("spans-off", "spans-on"):
        for vtag in ("veto-off", "veto-on"):
            if (stag, vtag) == ("spans-off", "veto-off"):
                continue
            c = cells[(stag, vtag)]
            lost = base["correct_keys"] - c["correct_keys"]
            emitted = names(off if stag == "spans-off" else on,
                            vtag == "veto-on")
            to_unnamed = sum(1 for k in lost if emitted.get(k) is None)
            gained = c["correct_keys"] - base["correct_keys"]
            print(f"  {stag:10s} {vtag:9s}  lost {len(lost):3d} "
                  f"({to_unnamed} refused / {len(lost) - to_unnamed} misnamed) "
                  f" gained {len(gained):3d}")
            kinds = collections.Counter(
                (truth[k], str(emitted.get(k))) for k in lost)
            for (want, got), n in kinds.most_common(6):
                print(f"        {n:4d}  printed {want:14s} -> {got}")

    print()
    print("=== WHAT THE VETO REFUSED, and where ===")
    for stag, arm in (("spans-off", off), ("spans-on", on)):
        emitted = names(arm, False)
        rows = collections.Counter()
        for k in arm["vetoed"]:
            nm = emitted.get(k)
            era = "before finale" if k[0] < FINALE_FIRST_PAGE else "finale"
            imp = nm in FINALE_ONLY and k[0] < FINALE_FIRST_PAGE
            adj = ("IMPOSSIBLE" if imp
                   else "judgeable-correct" if truth.get(k) == nm
                   else "judgeable-wrong" if k in truth
                   else "no truth here")
            rows[(nm, era, adj)] += 1
        print(f"  {stag}: {len(arm['vetoed'])} vetoes")
        for (nm, era, adj), n in rows.most_common():
            print(f"      {n:5d}  {str(nm):16s} {era:14s} {adj}")

    print()
    print("=== THE INTERESTING FAILURE: does a span boundary LICENSE an "
          "instrument the veto would have refused? ===")
    off_names, on_names = names(off, False), names(on, False)
    licensed = [k for k in keys
                if k in off["vetoed"] and k not in on["vetoed"]]
    print(f"  vetoed with spans off, NOT vetoed with spans on: "
          f"{len(licensed)}")
    still_bad = [k for k in licensed
                 if k[0] < FINALE_FIRST_PAGE and on_names[k] in FINALE_ONLY]
    print(f"    of those, still named a finale-only instrument: "
          f"{len(still_bad)}")
    if still_bad:
        print("    ⚠️ THIS IS THE COMPOSITION FAULT. The span boundary re-"
              "licensed a name the veto refused, so the veto must run INSIDE "
              "spans rather than beside them.")
    kinds = collections.Counter(
        (str(off_names[k]), str(on_names[k])) for k in licensed)
    for (a, b), n in kinds.most_common(8):
        print(f"      {n:5d}  was {a:16s} -> now {b}")
    newly = [k for k in keys if k not in off["vetoed"] and k in on["vetoed"]]
    print(f"  NOT vetoed with spans off, vetoed with spans on: {len(newly)}")
    kinds = collections.Counter(
        (str(off_names[k]), str(on_names[k])) for k in newly)
    for (a, b), n in kinds.most_common(8):
        print(f"      {n:5d}  was {a:16s} -> now {b}")

    print()
    print("=== the 18 finale strings the veto refuses with spans off ===")
    off_refused_strings = {k for k in off["vetoed"]
                           if k[0] >= FINALE_FIRST_PAGE}
    on_refused_strings = {k for k in on["vetoed"] if k[0] >= FINALE_FIRST_PAGE}
    print(f"  spans-off: {len(off_refused_strings)}   "
          f"spans-on: {len(on_refused_strings)}   "
          f"recovered by spans: "
          f"{len(off_refused_strings - on_refused_strings)}")
    for tag, s, arm in (("spans-off", off_refused_strings, off),
                        ("spans-on", on_refused_strings, on)):
        nm = names(arm, False)
        c = collections.Counter(str(nm[k]) for k in s)
        print(f"    {tag}: " + ", ".join(f"{k} x{v}"
                                         for k, v in c.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
