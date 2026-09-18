"""Can the rule be SAVED by demanding robustness instead of mere forcing?

probe_sensitivity.py shows the forced-by-clef rule GRAFTS under a single wrong
clef -- 19 of 128 perturbations. The natural repair is not a threshold but a
stronger definition of "forced": place a staff only where its slot is the same
under EVERY single-reading perturbation of the clef evidence, so that no one
misread clef can move it. That is the same move `_forced_pairing` already
makes (place only what is forced) applied to the evidence rather than to the
ordering.

TWO FIXES ARE APPLIED FIRST, because otherwise this would measure my own bugs
rather than the mechanism:
  (1) A reference slot whose clef ABSTAINED must match EVERY clef, not none.
      As written in probe_forced_by_clef it excluded the slot outright, which
      is a fallback converting "cannot tell" into a definite answer -- this
      repo's own standing rule -- and arm 2 caught it as `treble->None`
      grafting.
  (2) Likewise an unnamed staff whose clef abstained is unconstrained, which
      probe_forced_by_clef already did.

If robust reach is ~0 the mechanism is dead and that is the result. If it
keeps meaningful reach at zero grafts across every arm, it is shippable.
"""
import collections
import sys

import table
from probe_forced_by_clef import assignments, classify

CLEFS = ("treble", "bass", "alto", "tenor", None)


def allowed_for(staff, clef, slot_clef):
    """Slots this clef permits. An ABSENT reading on either side matches all."""
    if clef is None:
        return None
    return {i for i, rc in slot_clef.items() if rc is None or rc == clef}


def solve(staves, printed_lineups, ref_names, slot_clef, clef_of):
    out = {}
    n_slots = len(ref_names)
    for key in sorted(printed_lineups):
        grp = sorted([s for s in staves if s.sys_key == key],
                     key=lambda s: s.ordinal)
        unnamed = [s for s in grp if not s.named]
        if not unnamed:
            continue
        pinned = {s.ordinal: s.slot for s in grp if s.slot is not None}
        allowed = {}
        for s in grp:
            allowed[s.ordinal] = (None if s.named
                                  else allowed_for(s, clef_of.get(s.subject),
                                                   slot_clef))
        sols = assignments(len(grp), pinned, n_slots, allowed)
        for s in unnamed:
            if not sols:
                out[s.subject] = None
                continue
            got = {sol[s.ordinal] for sol in sols}
            out[s.subject] = got.pop() if len(got) == 1 else None
    return out


def main() -> int:
    staves, printed_lineups, _ = table.load()
    ref_names = table.reference_lineup()
    ref = sorted([s for s in staves if s.sys_key == (1, 0)],
                 key=lambda s: s.ordinal)
    base_slot_clef = {s.ordinal: s.clef for s in ref}
    base_clef_of = {s.subject: s.clef for s in staves}
    unnamed = [s for s in staves if not s.named]

    base = solve(staves, printed_lineups, ref_names, base_slot_clef,
                 base_clef_of)
    n_base = sum(1 for v in base.values() if v is not None)
    print("=" * 74)
    print("BASELINE, with the two fixes applied (absent clef matches ALL)")
    print("=" * 74)
    cls = collections.Counter()
    for s in unnamed:
        slot = base.get(s.subject)
        cls["forced" if slot is not None else "abstain"] += 1
        if slot is not None:
            cls[classify(s.printed, ref_names[slot])] += 1
    print("   forced %d, abstained %d" % (cls["forced"], cls["abstain"]))
    print("   of the forced: ok %d  condensation %d  GRAFT %d"
          % (cls["ok"], cls["condensation"], cls["graft"]))
    if n_base == 0:
        print("DEAD: baseline forces nothing", file=sys.stderr)
        return 2

    # ── every single-reading perturbation, of both populations
    arms = []
    for s in unnamed:
        for c in CLEFS:
            if c == s.clef:
                continue
            co = dict(base_clef_of)
            co[s.subject] = c
            arms.append(("unnamed %s %s->%s" % (s.subject, s.clef, c),
                         base_slot_clef, co))
    for i in range(len(ref_names)):
        for c in CLEFS:
            if c == base_slot_clef[i]:
                continue
            sc = dict(base_slot_clef)
            sc[i] = c
            arms.append(("ref slot %d %s->%s" % (i, base_slot_clef[i], c),
                         sc, base_clef_of))

    print()
    print("=" * 74)
    print("ROBUSTNESS -- %d single-reading perturbations" % len(arms))
    print("=" * 74)
    stable = {s.subject: base.get(s.subject) for s in unnamed}
    grafts_anywhere = collections.Counter()
    for label, sc, co in arms:
        res = solve(staves, printed_lineups, ref_names, sc, co)
        for s in unnamed:
            got = res.get(s.subject)
            if got is not None and classify(s.printed,
                                            ref_names[got]) == "graft":
                grafts_anywhere[s.subject] += 1
            if stable.get(s.subject) is not None and got != stable[s.subject]:
                stable[s.subject] = None

    n_stable = sum(1 for v in stable.values() if v is not None)
    print("   placements forced in the BASELINE            %d" % n_base)
    print("   still forced to the SAME slot in every arm   %d" % n_stable)
    print()
    rcls = collections.Counter()
    for s in unnamed:
        slot = stable.get(s.subject)
        if slot is None:
            continue
        rcls[classify(s.printed, ref_names[slot])] += 1
    print("   of the robustly forced: ok %d  condensation %d  GRAFT %d"
          % (rcls["ok"], rcls["condensation"], rcls["graft"]))
    print()
    print("   staves that GRAFT under at least one arm: %d of %d"
          % (len(grafts_anywhere), len(unnamed)))
    for sub, n in sorted(grafts_anywhere.items()):
        st = next(x for x in unnamed if x.subject == sub)
        print("      %-16s printed=%-20s grafts in %d arm(s)"
              % (sub, st.printed, n))

    print()
    print("=" * 74)
    print("VERDICT")
    print("=" * 74)
    if n_stable == 0:
        print("   ROBUST REACH IS ZERO -- every placement the rule makes can be")
        print("   moved by a single wrong clef reading. The mechanism is dead.")
    else:
        print("   robust reach %d of %d unnamed staves" % (n_stable, len(unnamed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
