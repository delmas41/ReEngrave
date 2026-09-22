"""REACH, per channel, before any accuracy claim.

Sean, 2026-09-22: *"margin names, instrumentation lists from the doc or a
dossier, Order, family brackets should all come first in determining what the
instrument is"*, and the clef only where we are SURE of it. This measures what
each of those is worth, added in that order, on the staves the shipped reader
says nothing about.

THE RULE UNDER TEST, stated before it is scored:

  A printed score may OMIT a tacet part; it may never REORDER one (C62). So a
  system's staves map to the reference lineup in STRICTLY INCREASING order.
  Every channel is a CONSTRAINT on that map, never a score:

    order    a staff whose margin was read takes a slot of that name
    bracket  a staff in the system's Nth family block takes a slot in the
             reference's Nth family block  (C58: interior barlines stop at
             family boundaries, and `Q.STAFF_GROUP` is read off where they
             stop -- not off a printed bracket, which this edition has none of)
    clef     a staff takes a slot whose own staff on the REFERENCE system read
             the same clef

  Enumerate every surviving assignment. A staff takes a slot only where EVERY
  one of them agrees -- `_forced_pairing`'s own discipline, extended with more
  constraints rather than replaced by a score. Where they disagree it ABSTAINS.

⚠️ A CHANNEL MAY NARROW OR ABSTAIN; IT MAY NEVER EMPTY THE SOLUTION SET. Where
a channel makes a system unsatisfiable the channel is DROPPED for that system
and the fact is counted, because a constraint that deletes the right answer is
worse than one that never spoke. That is Sean's *evidence contributes, it never
gates*, made mechanical.

⚠️ THE BAR IS GRAFTS, NOT CORRECTNESS. `benchmarks/omr-slot-index-2026-09`
measured that naming unnamed staves BY POSITION scores MORE correct (66 vs 50)
and grafts 9 staves doing it. A rule that names more and grafts one is worse
than one that names fewer and grafts none.
"""
import json
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

import channels

MAX_ENUM = 200000     # a system this ambiguous is a "cannot tell", not a slow one

#: ⚠️ `unnamed_only` IS A CHANNEL PROPERTY, NOT A TUNING KNOB, and the first
#: run of this probe is what found it. A NAMED staff is already pinned by its
#: own name, so a clef constraint on it can add nothing -- and it can SUBTRACT
#: everything: on p2/s1 the Fagotti's FALSE `tenor` (the CV locator firing
#: unopposed at margin exactly 1.0) names a clef NO reference slot reads, the
#: system goes unsatisfiable, and the whole clef channel is dropped for it.
#: Four forced staves, lost to one wrong reading on a staff the clef was never
#: needed for. `probe_forced_by_clef.py` had this right without saying why.
ARMS = (
    ("order", ("order",)),
    ("order+bracket", ("order", "bracket")),
    ("order+bracket+clef(raw, all staves)", ("order", "bracket", "clef")),
    ("order+bracket+clef(raw, unnamed only)", ("order", "bracket", "clef", "unnamed_only")),
    ("order+bracket+clef(sure, all staves)", ("order", "bracket", "clef_sure")),
    ("order+bracket+clef(sure, unnamed only)", ("order", "bracket", "clef_sure", "unnamed_only")),
    ("order+clef(raw, unnamed only)  [prior art]", ("order", "clef", "unnamed_only")),
    ("order+bracket+clef(TREBLE-OR-NOT, unnamed only)",
     ("order", "bracket", "clef_sure", "treble_or_not", "unnamed_only")),
    ("order+bracket+clef(INSTRUMENT clefs, unnamed only)",
     ("order", "bracket", "clef_sure", "instrument_clefs", "unnamed_only")),
)

#: ⚠️⚠️ THE WEAKER CLEF CLAIM, AND THE ONLY ONE BOTH DOCUMENTS SUPPORT.
#: `probe_clef_stability.py` measures that a slot's clef is constant for every
#: instrument on both plates EXCEPT the cello and the bassoon -- which alternate
#: bass and tenor as a matter of course, so the reference's own reading of those
#: slots is not a property of the slot at all (Breitkopf's reference reads its
#: cello slot `tenor` and three later systems read the same slot `bass`, all at
#: margin 4.5). What IS constant on both is coarser: a staff in a G clef is
#: never a viola, a cello or a bass, and a staff NOT in a G clef is never a
#: violin. That is the boundary-finding job and nothing more.
def _treble_or_not(c):
    return None if c is None else (c == "treble")


def block_map(sys_blocks: List[Optional[int]],
              ref_blocks: List[Optional[int]]) -> Optional[Dict[int, int]]:
    """`{this system's block id -> the reference's block id}`, or None.

    ⚠️ ORDER-PRESERVING AND EQUAL-COUNT ONLY. A system that prints fewer
    family blocks than the reference has had a whole section go tacet, and
    WHICH section is exactly what this channel would then be guessing. It
    returns None instead and the caller drops the channel for that system.
    """
    a = _runs(sys_blocks)
    b = _runs(ref_blocks)
    if not a or not b or len(a) != len(b):
        return None
    return {x: y for x, y in zip(a, b)}


def _runs(seq: Sequence[Optional[int]]) -> List[int]:
    out: List[int] = []
    for x in seq:
        if x is None:
            return []
        if not out or out[-1] != x:
            out.append(x)
    return out


def allowed_slots(st, arm: Tuple[str, ...], ref_names, ref_blocks, ref_clefs,
                  bmap, ref_admissible=None) -> Optional[Set[int]]:
    """The slots this staff may take under `arm`, or None for "no opinion"."""
    n = len(ref_names)
    sets: List[Set[int]] = []
    # ⚠️⚠️ A REFERENCE SLOT THE DOCUMENT COULD NOT READ MUST WIDEN THE
    # CANDIDATE SET, NEVER EMPTY IT -- and the first run of this probe got
    # that wrong and was caught by its own no-solution counter. Breitkopf's
    # reference lineup has THREE slots whose own margin the reader could not
    # resolve (one of them the horn staff whose label truncates to `'(C)'`),
    # and requiring a named staff to match a slot name made every system
    # holding those staves UNSATISFIABLE. `None` on the reference side is
    # "we do not know what this slot is", which excludes nobody.
    if "order" in arm and st.named:
        sets.append({i for i, nm in enumerate(ref_names)
                     if nm is None or nm == st.instrument})
    if "bracket" in arm and bmap is not None and st.block is not None:
        want = bmap.get(st.block)
        if want is not None:
            sets.append({i for i, b in enumerate(ref_blocks)
                         if b is None or b == want})
    clef = None
    if not ("unnamed_only" in arm and st.named):
        if "clef_sure" in arm:
            clef = st.sure_clef()
        elif "clef" in arm:
            clef = st.clef if st.clef_outcome == "decided" else None
    if clef is not None:
        if "instrument_clefs" in arm and ref_admissible is not None:
            sets.append({i for i, adm in enumerate(ref_admissible)
                         if adm is None or clef in adm})
        elif "treble_or_not" in arm:
            want = _treble_or_not(clef)
            sets.append({i for i, c in enumerate(ref_clefs)
                         if c is None or _treble_or_not(c) == want})
        else:
            sets.append({i for i, c in enumerate(ref_clefs)
                         if c is None or c == clef})
    if not sets:
        return None
    out = set(range(n))
    for s in sets:
        out &= s
    return out


def assignments(n_staves: int, allowed: Dict[int, Optional[Set[int]]],
                n_slots: int) -> List[Tuple[int, ...]]:
    out: List[Tuple[int, ...]] = []

    def walk(ordinal: int, lo: int, acc: List[int]) -> None:
        if len(out) > MAX_ENUM:
            return
        if ordinal == n_staves:
            out.append(tuple(acc))
            return
        hi = n_slots - (n_staves - ordinal)
        for slot in range(lo, hi + 1):
            ok = allowed.get(ordinal)
            if ok is not None and slot not in ok:
                continue
            acc.append(slot)
            walk(ordinal + 1, slot + 1, acc)
            acc.pop()

    walk(0, 0, [])
    return out


def solve(grp, arm, ref_names, ref_blocks, ref_clefs, bmap, ref_admissible=None):
    """`(solutions, dropped)` -- `dropped` names channels this system refused."""
    dropped: List[str] = []
    use = list(arm)
    while True:
        allowed = {s.ordinal: allowed_slots(s, tuple(use), ref_names,
                                            ref_blocks, ref_clefs, bmap,
                                            ref_admissible)
                   for s in grp}
        sols = assignments(len(grp), allowed, len(ref_names))
        if sols or len(use) <= 1:
            return sols, dropped
        # ⚠️ DROP THE WEAKEST CHANNEL FIRST, and the order is Sean's own:
        # the clef is the least certain thing here and is the first to go.
        for weakest in ("clef", "clef_sure", "bracket"):
            if weakest in use:
                use.remove(weakest)
                dropped.append(weakest)
                break
        else:
            return sols, dropped


def main() -> int:
    record = sys.argv[1] if len(sys.argv) > 1 else "litolff"
    score = record == "litolff"      # print truth is LITOLFF ONLY
    staves, counts, raw = channels.load(record)
    ref_sys, ref_names, ref_blocks = channels.reference(staves, counts)
    by_sys: Dict[Tuple[int, int], list] = {}
    for s in staves:
        by_sys.setdefault(s.sys_key, []).append(s)
    for k in by_sys:
        by_sys[k].sort(key=lambda s: s.ordinal)
    ref_grp = by_sys[ref_sys]
    ref_clefs: List[Optional[str]] = [None] * len(ref_names)
    for s in ref_grp:
        if s.ordinal < len(ref_names):
            ref_clefs[s.ordinal] = s.clef if s.clef_outcome == "decided" else None

    ref_admissible = [channels.clefs_for(
        s.instrument, s.expected_clef) for s in
        sorted(ref_grp, key=lambda x: x.ordinal)]
    while len(ref_admissible) < len(ref_names):
        ref_admissible.append(None)

    full, printed = (channels.printed_truth() if score else ([], {}))
    if score:
        for s in staves:
            lineup = printed.get(s.sys_key)
            if lineup and s.ordinal < len(lineup):
                s.printed = lineup[s.ordinal]

    unnamed = [s for s in staves if not s.named]
    print("=" * 78)
    print("RECORD %s   md5 %s" % (record, raw["_record_md5"]))
    print("=" * 78)
    print("  staves                     %d over %d systems" % (len(staves), len(by_sys)))
    print("  reference system           p%d/s%d, %d slots" % (ref_sys[0], ref_sys[1], len(ref_names)))
    print("  reference names            %s" % [n or "-" for n in ref_names])
    print("  reference family blocks    %s" % ref_blocks)
    print("  reference clefs            %s" % [c or "-" for c in ref_clefs])
    print("  reference admissible clefs %s"
          % [("/".join(a) if a else "-") for a in ref_admissible])
    print()
    print("  CHANNEL REACH, over all %d staves:" % len(staves))
    print("    margin name read           %d" % sum(1 for s in staves if s.label))
    print("    instrument DECIDED         %d  (%s)" % (
        sum(1 for s in staves if s.named),
        dict(_count(s.instrument_reason for s in staves if s.named))))
    print("    family block read          %d" % sum(1 for s in staves if s.block is not None))
    print("    clef decided               %d" % sum(1 for s in staves if s.clef_outcome == "decided"))
    print("    clef decided AND sure      %d" % sum(1 for s in staves if s.sure_clef()))
    print()
    print("  THE POPULATION -- staves whose instrument ABSTAINED: %d" % len(unnamed))
    if not unnamed:
        print("  DEAD: this record has no population for any of these channels.",
              file=sys.stderr)
        _dump(record, {"population": 0, "arms": {}}, staves, ref_names)
        return 3
    print("    of those, margin label read  %d" % sum(1 for s in unnamed if s.label))
    print("    of those, family block read  %d" % sum(1 for s in unnamed if s.block is not None))
    print("    of those, clef decided       %d" % sum(1 for s in unnamed if s.clef_outcome == "decided"))
    print("    of those, clef SURE          %d" % sum(1 for s in unnamed if s.sure_clef()))

    results = {}
    for label, arm in ARMS:
        print()
        print("-" * 78)
        print("ARM  %s" % label)
        print("-" * 78)
        forced = ambiguous = no_solution = 0
        # ⚠️⚠️ RECORDED, AND THE MUTATION BATTERY IS WHY. This is the single
        # most important number in the arm and it existed only on stdout: the
        # difference between "the clef contributed" and "the clef was REFUSED
        # and ORDER did all the work" is invisible in the forced/ambiguous
        # counts, so an arm that silently lost its clef channel scored
        # identically to one that used it. A judge that cannot see that cannot
        # test the headline claim.
        dropped_by_system = {}
        verdict = _count([])
        rows = []
        control_ok = control_bad = 0
        for key in sorted(by_sys):
            grp = by_sys[key]
            if all(s.named for s in grp):
                continue
            bmap = block_map([s.block for s in grp], ref_blocks)
            sols, dropped = solve(grp, arm, ref_names, ref_blocks, ref_clefs,
                                  bmap, ref_admissible)
            if not sols:
                no_solution += sum(1 for s in grp if not s.named)
                print("  p%d/s%d  NO SOLUTION" % key)
                continue
            if dropped:
                dropped_by_system["p%d/s%d" % key] = list(dropped)
            note = ""
            if dropped:
                note = "   [channel dropped: %s]" % ",".join(dropped)
            if "bracket" in arm and bmap is None:
                note += "   [bracket silent: block counts differ]"
            print("  p%d/s%d  %2d staves, %2d unnamed -> %d assignment(s)%s"
                  % (key[0], key[1], len(grp),
                     sum(1 for s in grp if not s.named), len(sols), note))
            for s in grp:
                got = {sol[s.ordinal] for sol in sols}
                if s.named:
                    # CONTROL: the order channel must reproduce the shipped
                    # `_forced_pairing` wherever that decided.
                    if s.slot_outcome == "decided" and len(got) == 1:
                        if got.copy().pop() == s.slot:
                            control_ok += 1
                        else:
                            control_bad += 1
                            print("      CONTROL MISMATCH st%d: ours %s, record %s"
                                  % (s.ordinal, got, s.slot))
                    continue
                if len(got) == 1:
                    slot = got.copy().pop()
                    forced += 1
                    cls = channels.classify(s.printed, full[slot]) if score else "unscored"
                    verdict[cls] += 1
                    rows.append({"subject": s.subject, "slot": slot,
                                 "slot_name": full[slot] if score else None,
                                 "printed": s.printed, "class": cls,
                                 "clef": s.clef, "clef_margin": s.clef_margin,
                                 "block": s.block})
                    flag = "   <== GRAFT" if cls == "graft" else ""
                    print("      FORCED  st%-2d -> slot %2d  %-22s (print: %s) [%s]%s"
                          % (s.ordinal, slot,
                             (full[slot] if score else ref_names[slot]) or "-",
                             s.printed or "?", cls, flag))
                else:
                    ambiguous += 1
                    rows.append({"subject": s.subject, "slot": None,
                                 "candidates": sorted(got), "printed": s.printed,
                                 "class": "ambiguous", "clef": s.clef,
                                 "block": s.block})
                    print("      abstain st%-2d -> %s"
                          % (s.ordinal, sorted(got)))
        print()
        print("  FORCED %d / ambiguous %d / no-solution %d   of %d"
              % (forced, ambiguous, no_solution, len(unnamed)))
        if score:
            print("  scored:  ok %d   condensation %d   ** GRAFT %d **   unknown %d"
                  % (verdict["ok"], verdict["condensation"], verdict["graft"],
                     verdict["unknown"]))
        print("  CONTROL (named staves vs the record's own slot_index): %d agree, %d differ"
              % (control_ok, control_bad))
        print("  channel REFUSED on %d system(s): %s"
              % (len(dropped_by_system), dropped_by_system or "none"))
        results[label] = {"forced": forced, "ambiguous": ambiguous,
                          "no_solution": no_solution,
                          "systems_channel_dropped": len(dropped_by_system),
                          "dropped_by_system": dropped_by_system,
                          "scored": dict(verdict) if score else None,
                          "control_agree": control_ok, "control_differ": control_bad,
                          "rows": rows}

    _dump(record, {"population": len(unnamed), "arms": results,
                   "reference_system": list(ref_sys),
                   "reference_names": ref_names,
                   "reference_blocks": ref_blocks,
                   "reference_clefs": ref_clefs,
                   "record_md5": raw["_record_md5"]}, staves, ref_names)
    return 0


def _count(it):
    import collections
    c = collections.Counter(it)
    for k in ("ok", "condensation", "graft", "unknown", "unscored", "ambiguous"):
        c.setdefault(k, 0)
    return c


def _dump(record, payload, staves, ref_names):
    out = channels.HERE / "out" / ("reach-%s.json" % record)
    payload["staves"] = [
        {"subject": s.subject, "label": s.label, "instrument": s.instrument,
         "instrument_reason": s.instrument_reason, "block": s.block,
         "clef": s.clef, "clef_outcome": s.clef_outcome,
         "clef_margin": s.clef_margin, "printed": s.printed,
         "slot": s.slot, "slot_reason": s.slot_reason}
        for s in staves]
    out.write_text(json.dumps(payload, indent=1))
    print()
    print("wrote %s" % out)


if __name__ == "__main__":
    raise SystemExit(main())
