"""Is the phantom-note population INSIDE the dedupe repair's reach?

⚠️⚠️ THE QUESTION, STATED SO IT CAN COME BACK "NO".  The artefact Sean read
carries **1,793** pitched notes — the count BEFORE
*A CONTEST is RESOLVED, not relocated* took it to 1,618 by refusing 176 as
`owned_by_another_staff`.  FINDINGS.md §7 ranks a re-export first, because
until it runs nobody knows how much of the observation is already repaired.
**That re-export needs the staged record, which no cloud container holds.**
This probe asks the same question from the other side, off two committed
artefacts, and it can only ever answer for the BARS — never for the notes.

THE STRUCTURAL CLAIM IT RESTS ON, derived from the two functions rather than
assumed:

  * `export._place_notes` writes a note at the SUBJECT's own staff and refuses
    it when `A.is_relocated_copy(subject, owner)` — i.e. when the owner names
    another staff.  The arm that produced 1,793 stubs that predicate to
    `False`; the artefact Sean read *relocated* instead.  Either way, **every
    note whose base and fix destinations differ is a glyph carrying an
    ownership verdict**, and
  * `adjudicate_glyph_owner` declares `subjects_from=Q.GLYPH_BAND_DISTANCE`,
    and `gather_ownership_evidence` files a band row ONLY for a detection that
    shares its detector CATEGORY with a detection on ANOTHER STAFF of the SAME
    SYSTEM at more than `CONTEST_IOU = 0.3`.

    ⚠️ ROADMAP 2.6 MOVED BOTH VALUES (2026-09-23), and this probe's headline
    was computed under the OLD ones -- smufl NAME equality at 0.5.  The domain
    is now WIDER on both axes, so a bar this file once called UNREACHABLE may
    hold a contest today.  Re-run it before quoting its zero again.

  **=> A bar holding no member of such a contest cannot change.**  That is a
  one-sided claim and it is the only one available here: a bar that DOES hold
  one may or may not change, because which copy is refused is the OWNER's
  verdict and this container does not hold it.

⚠️ THE FRAME.  `box_a`/`box_b` in the pairs table are PAGE PIXELS, and a
page-pixel box is a fact about ONE page — two pages superimpose exactly, which
is the error `reach.py`'s own first run made.  Nothing here compares boxes at
all: the join is on the SUBJECT ADDRESS `(page, system, staff, cell)`, and the
cell index is the bar index within the system (`Subject.cell` restarts per
system; corroborated below against the exporter's own system map).

⚠️ IT IS A SUPERSET TEST, DELIBERATELY.  The committed pairs table is built at
IoU 0.3, which is now exactly the contest gate, so filtering at 0.3 gives a
population that CONTAINS `glyph_owner`'s.  "Zero pairs here" is therefore
sound; the count at the OLD 0.5 gate is reported beside it, and the difference
between the two is what ROADMAP 2.6 handed in.

⚠️ TWO CONTROLS, BOTH ABLE TO FAIL, because the headline here is a ZERO and a
zero from a dead instrument reads identically to a zero from a clean page.

  1. **The cell-index agreement.**  Indexing a contest at its members' own
     addresses is only a complete join if both members of a cross-staff
     contest carry the SAME cell index — otherwise a note relocated into bar
     `c` could come from a glyph filed at bar `c±1` and this probe would miss
     it.  Measured, not assumed, and printed.
  2. **The positive control.**  The dedupe session named two cells by hand as
     the `ffff`: `cell/1/0/7/0` and `cell/1/0/8/0`.  This probe re-finds them
     through the same index it uses for the phantom bars, so a lookup that
     silently returns nothing cannot pass.  `--check` exits non-zero if it
     does not light up.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
ROOT = BENCH.parent.parent

PAIRS = ROOT / "benchmarks/omr-staged-dedupe-2026-09/out/pairs-p1-p4.json"
MAP = ROOT / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"

#: `gather.CONTEST_IOU`.  Restated here ONLY because importing
#: `tools.omr.staged.gather` drags in the detector, which this container has no
#: weights for; `tests/test_contest_join.py` asserts the two are equal.
#: ⚠️ 0.5 until ROADMAP 2.6 put it back to the frozen legacy reader's swept
#: 0.3 (`transcribe._CROSS_STAFF_DUPLICATE_IOU`).
CONTEST_IOU = 0.3


def addr(key: str):
    """(page, system, staff, cell) out of `glyph/p/sys/staff/cell/glyph`."""
    k = key.split("/")
    return (int(k[1]), int(k[2]), int(k[3]), int(k[4]))


def load_offenders(path: Path, page: int, system: int):
    """Print-silent bars holding a pitched note, as FINDINGS §4 counts them."""
    rows = json.load(open(path))
    out = []
    for r in rows:
        if not r["print_silent"] or not r["pitches"]:
            continue
        out.append({
            "page": page, "system": system,
            "staff": r["staff"], "cell": r["bar"],
            "part": r["part"], "measure": r["measure"],
            "pitches": r["pitches"], "clef": r["clef"],
            "wrote": r["wrote"], "rest_too": "rest" in r["wrote"],
        })
    return out


_LETTER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
#: `steps.BOTTOM_LINE` -- the diatonic index of each clef's bottom line.
_BOTTOM_LINE = {"treble": 4 * 7 + 2, "bass": 2 * 7 + 4, "alto": 3 * 7 + 3,
                "tenor": 3 * 7 + 1}


def step_of(pitch, clef):
    """Staff step from the BOTTOM line, one step per half space.

    ⚠️ Parsed leniently on purpose: `steps.step_of` does `int(pitch[1:])`,
    which raises on an accidental (`Ab3`).  The step does not depend on the
    accidental, so it is stripped.
    """
    if not pitch or clef not in _BOTTOM_LINE:
        return None
    letter = pitch[0]
    octv = "".join(ch for ch in pitch[1:] if ch.isdigit() or ch == "-")
    if letter not in _LETTER or not octv:
        return None
    return int(octv) * 7 + _LETTER[letter] - _BOTTOM_LINE[clef]


def where_it_stands(step):
    """FINDINGS §4's partition: the rest slot, outside the staff, or elsewhere.

    A whole rest hangs under the fourth line from the bottom, so its body
    occupies steps 5-6 whatever the clef.  The staff itself spans 0-8.
    """
    if step is None:
        return "no_step"
    if 5 <= step <= 6:
        return "at_the_rest_slot"
    if step < 0 or step > 8:
        return "outside_the_staff"
    return "inside_elsewhere"


def head_base(c):
    """`noteheadHalfInSpace` -> `noteheadHalf`.

    ⚠️ THE SUFFIX IS THE ONE THING TWO STAVES MUST DISAGREE ABOUT.  It names
    whether the head sits ON A LINE or IN A SPACE -- a fact about the staff the
    head was read against.  One piece of ink in the gap between two staves
    lands at different positions in their two grids, so the detector can
    legitimately call it `...OnLine` in one cell and `...InSpace` in the other.

    ⚠️ UNTIL ROADMAP 2.6 THAT ENDED THE CONTEST: the gate was
    `di.smufl_name == dj.smufl_name`, so the identity test was keyed on the
    disputed quantity and said THERE IS NO CONTEST.  It is now
    `di.category == dj.category`, so a suffix-only pair IS a contest and is
    filed in `cross` below -- still counted separately, because how many of the
    domain arrived that way is the thing 2.6 measured.
    """
    for suf in ("InSpace", "OnLine"):
        if c.endswith(suf):
            return c[:-len(suf)]
    return c


def index_pairs(pairs, family="notehead_class"):
    """address -> the pairs touching it, split by scope and by the class gate."""
    cross = collections.defaultdict(list)     # cross-staff, one CATEGORY
    suffix = collections.defaultdict(list)    # of those, suffix differs only
    incell = collections.defaultdict(list)    # same cell (the NMS residue)
    for p in pairs:
        if p["family"] != family:
            continue
        a, b = addr(p["a"]), addr(p["b"])
        if p["scope"] == "same_system_other_staff":
            # ⚠️ EVERY cross-staff pair of this family is one category (the
            # family IS the category), so since ROADMAP 2.6 every one of them
            # is in the domain.  `suffix` is now a REPORTING split over
            # `cross`, not an exclusion from it.
            cross[a].append(p)
            cross[b].append(p)
            if (not p["same_class"]
                    and head_base(p["class_a"]) == head_base(p["class_b"])):
                suffix[a].append(p)
                suffix[b].append(p)
        elif p["scope"] == "same_cell":
            incell[a].append(p)
    return cross, suffix, incell


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=str(PAIRS))
    ap.add_argument("--map", default=str(MAP))
    ap.add_argument("--silent", action="append", default=None,
                    metavar="JSON:PAGE:SYSTEM",
                    help="a silent_bars.py output with its page and system")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the instrument is DEAD")
    args = ap.parse_args(argv)

    silent = args.silent or [
        f"{BENCH}/out/silent-p4s0.json:4:0",
        f"{BENCH}/out/silent-p3s0.json:3:0",
    ]

    d = json.load(open(args.pairs))
    pairs = d["pairs"]

    # ── REACH, FIRST ───────────────────────────────────────────────────────
    print("REACH")
    print(f"  pairs table: iou={d['iou']}  n_subjects={d['n_subjects']}  "
          f"pairs={len(pairs)}")
    if d["iou"] > CONTEST_IOU:
        print(f"  DEAD: the table's own IoU {d['iou']} is ABOVE the contest "
              f"gate {CONTEST_IOU}; it is not a superset of the domain.")
        return 2

    smap = json.load(open(args.map))
    sys_shape = {
        (s["page"], s["system"]): (
            len(s["staves"]), max(st["n_measures"] for st in s["staves"]))
        for s in smap["systems"]}
    seen = collections.defaultdict(lambda: [set(), set()])
    for p in pairs:
        for side in ("a", "b"):
            pg, sy, st, c = addr(p[side])
            seen[(pg, sy)][0].add(st)
            seen[(pg, sy)][1].add(c)
    print(f"  systems in the exporter's map: {len(sys_shape)}")
    print(f"  systems the pairs table sees : {len(seen)}")
    bad = []
    for k, (staves, cells) in sorted(seen.items()):
        shape = sys_shape.get(k)
        if not (shape and max(staves) < shape[0] and max(cells) < shape[1]):
            bad.append((k, shape, max(staves), max(cells)))
    if bad:
        print("  ⚠️ ADDRESS DISAGREEMENT with the exporter's map:")
        for k, shape, ms, mc in bad:
            print(f"     {k} map={shape} pairs max staff={ms} max cell={mc}")
    else:
        print("  every pair address lies inside its system's (staves, bars) "
              "from the exporter's own map")
        print("  -- so the record's CELL index is the bar index this join "
              "needs, checked rather than assumed")

    # ── CONTROL 1: is the address join COMPLETE? ───────────────────────────
    # A contest relocates a note into the OWNER's bar at the SUBJECT's own
    # cell index, so indexing by each member's address is a complete join only
    # if both members carry the same cell index.  Measured.
    same_cell_idx = diff_cell_idx = 0
    for p in pairs:
        if p["scope"] != "same_system_other_staff":
            continue
        if addr(p["a"])[3] == addr(p["b"])[3]:
            same_cell_idx += 1
        else:
            diff_cell_idx += 1
    print(f"  cross-staff pairs sharing a CELL index: {same_cell_idx} "
          f"| differing: {diff_cell_idx}")
    if diff_cell_idx:
        print("  ⚠️ the address join is INCOMPLETE -- a relocation can land in "
              "a bar this probe does not index")

    cross, suffix, incell = index_pairs(pairs)

    # ── CONTROL 2: a positive control the same index must light up ─────────
    # `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §2a names these two
    # cells by hand as the printed `ff` that reached the file as `ffff`.
    pc_cross, _pc_sfx, _pc_ic = index_pairs(pairs, family="dynamic_letter")
    pc = [(1, 0, 7, 0), (1, 0, 8, 0)]
    pc_hits = {a: len(pc_cross.get(a, [])) for a in pc}
    print(f"  POSITIVE CONTROL (the hand-named `ffff` cells): {pc_hits}")
    pc_live = all(v > 0 for v in pc_hits.values())
    if not pc_live:
        print("  ⚠️ DEAD: the index does not re-find a contest the dedupe "
              "session named by hand.")

    def n(scope, same_class=True, gate=0.0):
        return sum(1 for p in pairs
                   if p["family"] == "notehead_class" and p["scope"] == scope
                   and p["same_class"] == same_class and p["iou"] >= gate)

    n_cross_dom = n("same_system_other_staff", True, CONTEST_IOU)
    n_cross_all = n("same_system_other_staff", True)
    n_incell = sum(1 for p in pairs if p["family"] == "notehead_class"
                   and p["scope"] == "same_cell")
    n_suffix = sum(1 for p in pairs
                   if p["family"] == "notehead_class"
                   and p["scope"] == "same_system_other_staff"
                   and not p["same_class"]
                   and head_base(p["class_a"]) == head_base(p["class_b"])
                   and p["iou"] >= CONTEST_IOU)
    print(f"  notehead CROSS-STAFF contests: {n_cross_dom} at IoU>="
          f"{CONTEST_IOU}  ({n_cross_all} in the 0.3 superset)")
    print(f"  notehead SAME-CELL duplicates: {n_incell}"
          f"   -- OUTSIDE the repair's domain by construction")
    print(f"  notehead cross-staff pairs REFUSED by the same-class gate for "
          f"the InSpace/OnLine suffix ALONE: {n_suffix} at IoU>={CONTEST_IOU}")

    if args.check and (n_cross_dom == 0 or not seen or bad or not pc_live
                       or diff_cell_idx):
        print("DEAD: nothing to join, an address disagreement, an incomplete "
              "join, or a positive control that did not light up.")
        return 2

    # ── THE JOIN ───────────────────────────────────────────────────────────
    offenders = []
    for spec in silent:
        path, pg, sy = spec.rsplit(":", 2)
        offenders += load_offenders(Path(path), int(pg), int(sy))

    strict = [o for o in offenders if not o["rest_too"]]
    print("\nPOPULATION")
    print(f"  print-silent bars holding a pitched note     : {len(offenders)}")
    print(f"  ...of those, holding NO rest (FINDINGS §4's) : {len(strict)}")
    print(f"  phantom notes in those bars                  : "
          f"{sum(len(o['pitches']) for o in strict)}")

    print("\nJOIN  -- does the repair's domain reach these bars?")
    print(f"  {'bar':<22} {'notes':>5} {'x>=.5':>6} {'x>=.3':>6} "
          f"{'sufx':>5} {'incell':>6}  verdict")
    tally = collections.Counter()
    note_tally = collections.Counter()
    rows = []
    for o in offenders:
        a = (o["page"], o["system"], o["staff"], o["cell"])
        cs = cross.get(a, [])
        c5 = sum(1 for p in cs if p["iou"] >= CONTEST_IOU)
        c3 = len(cs)
        sf = len(suffix.get(a, []))
        ic = len(incell.get(a, []))
        if c3 == 0:
            v = "UNREACHABLE by the repair"
        elif c5 == 0:
            v = "below the gate (0.3 only)"
        else:
            v = "in the domain -- CANNOT TELL"
        if not o["rest_too"]:
            tally[v] += 1
            note_tally[v] += len(o["pitches"])
        name = f"{o['part']} m{o['measure']} st{o['staff']} b{o['cell']}"
        flag = "" if not o["rest_too"] else "  (+rest, outside §4's 13)"
        print(f"  {name:<22} {len(o['pitches']):>5} {c5:>6} {c3:>6} "
              f"{sf:>5} {ic:>6}  {v}{flag}")
        rows.append({**o, "cross_at_gate": c5, "cross_superset": c3,
                     "cross_suffix_only": sf, "same_cell": ic, "verdict": v})

    print("\nTHE ANSWER, over the 13 bars / 25 notes FINDINGS §4 counts:")
    for k, c in tally.most_common():
        print(f"  {c:>3} bars  {note_tally[k]:>3} notes   {k}")

    # ── THE CROSS-TAB: where a note STANDS against whether the repair
    #    could have reached its bar.  FINDINGS §4 partitions the 25 by
    #    position; the join partitions the 13 bars by reach; this is both.
    print("\nCROSS-TAB  (the 25 notes: where they stand x whether the repair "
          "reaches their bar)")
    xtab = collections.Counter()
    for o in offenders:
        if o["rest_too"]:
            continue
        a = (o["page"], o["system"], o["staff"], o["cell"])
        reach = ("reachable" if any(p["iou"] >= CONTEST_IOU
                                    for p in cross.get(a, []))
                 else "UNREACHABLE")
        for p in o["pitches"]:
            xtab[(where_it_stands(step_of(p, o["clef"])), reach)] += 1
    places = ("at_the_rest_slot", "outside_the_staff", "inside_elsewhere",
              "no_step")
    print(f"  {'':<20} {'UNREACHABLE':>12} {'reachable':>12} {'total':>7}")
    for pl in places:
        u = xtab[(pl, "UNREACHABLE")]
        r = xtab[(pl, "reachable")]
        if u or r:
            print(f"  {pl:<20} {u:>12} {r:>12} {u + r:>7}")
    tu = sum(v for (_p, rr), v in xtab.items() if rr == "UNREACHABLE")
    tr = sum(v for (_p, rr), v in xtab.items() if rr == "reachable")
    print(f"  {'TOTAL':<20} {tu:>12} {tr:>12} {tu + tr:>7}")
    if tu + tr != 25:
        print(f"  ⚠️ the partition is {tu + tr}, not the 25 FINDINGS §4 counts")

    # ── AND ONE FACT THE PADDING STORY NEEDS: IS THERE A NEIGHBOUR AT ALL? ──
    # FINDINGS §4 attributes the outside-the-staff notes to "the measure cell's
    # 4-6-space PADDING from a neighbour".  A note ABOVE the top staff of a
    # system has no staff above it, so that account cannot cover it.  Read off
    # the exporter's own map rather than guessed.
    print("\nIS THERE A NEIGHBOUR ON THAT SIDE?  (outside-the-staff notes only)")
    edge = collections.Counter()
    for o in offenders:
        if o["rest_too"]:
            continue
        n_staves = sys_shape.get((o["page"], o["system"]), (0, 0))[0]
        for p in o["pitches"]:
            s = step_of(p, o["clef"])
            if where_it_stands(s) != "outside_the_staff":
                continue
            if s > 8 and o["staff"] == 0:
                edge["ABOVE the TOP staff -- no neighbour above"] += 1
            elif s < 0 and o["staff"] == n_staves - 1:
                edge["BELOW the BOTTOM staff -- no neighbour below"] += 1
            else:
                edge["a neighbouring staff is on that side"] += 1
    for k, c in edge.most_common():
        print(f"  {c:>3}  {k}")

    out = BENCH / "out" / "contest-join.json"
    out.write_text(json.dumps({
        "pairs_iou": d["iou"], "contest_gate": CONTEST_IOU,
        "controls": {"cross_pairs_same_cell_index": same_cell_idx,
                     "cross_pairs_differing_cell_index": diff_cell_idx,
                     "positive_control_ffff_cells":
                         {"/".join(map(str, k)): v
                          for k, v in pc_hits.items()}},
        "notehead_cross_at_gate": n_cross_dom,
        "notehead_cross_superset": n_cross_all,
        "notehead_same_cell": n_incell,
        "notehead_cross_suffix_only_at_gate": n_suffix,
        "bars": rows,
        "cross_tab": {f"{pl}|{rr}": v for (pl, rr), v in sorted(xtab.items())},
        "outside_the_staff_side": dict(edge),
    }, indent=1))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
