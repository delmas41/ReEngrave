"""How fragile is the 16/16? Perturb ONE clef reading and see what breaks.

⚠️ THIS IS THE MEASUREMENT THAT DECIDES WHETHER THE RULE IS SHIPPABLE, and it
is not the accuracy one. On this document the clef reads 20/20 on the unnamed
staves and 12/12 on the reference -- a PERFECT witness -- so "16 forced, 0
grafts" is the rule's best case and says nothing about what it does when the
witness is wrong. A rule that goes SILENT on a bad clef is safe on documents
this one cannot represent; a rule that GRAFTS on one is not, and the
difference is invisible in the headline.

Two arms, because the two clef populations play different parts:
  UNNAMED  -- the staff's own reading, the thing being constrained
  REFERENCE-- the slot's reading, the constraint itself; one error here moves
              every staff of every short system, so it is the wider blast.

For each single-reading perturbation, the rule is re-run and each of the 25 is
scored again. What is counted is not "does the answer change" but WHICH WAY:
a forced-but-wrong placement is a GRAFT and is the failure that matters; a
placement that becomes an abstention, or a system that becomes unsatisfiable,
is the rule failing SAFE.
"""
import collections
import copy
import itertools
import sys

import table
from probe_forced_by_clef import assignments, classify

CLEFS = ("treble", "bass", "alto", "tenor")


def run(staves, printed_lineups, ref_names, slot_clef, clef_of):
    """`{subject: (slot|None, class)}` for every unnamed staff."""
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
            c = clef_of.get(s.subject)
            if s.named or c is None:
                allowed[s.ordinal] = None
            else:
                allowed[s.ordinal] = {i for i, rc in slot_clef.items() if rc == c}
        sols = assignments(len(grp), pinned, n_slots, allowed)
        for s in unnamed:
            if not sols:
                out[s.subject] = (None, "no_solution")
                continue
            got = {sol[s.ordinal] for sol in sols}
            if len(got) == 1:
                slot = got.pop()
                out[s.subject] = (slot, classify(s.printed, ref_names[slot]))
            else:
                out[s.subject] = (None, "ambiguous")
    return out


def summarise(res):
    c = collections.Counter(v[1] for v in res.values())
    return c


def main() -> int:
    staves, printed_lineups, _ = table.load()
    ref_names = table.reference_lineup()
    ref = sorted([s for s in staves if s.sys_key == (1, 0)],
                 key=lambda s: s.ordinal)
    base_slot_clef = {s.ordinal: s.clef for s in ref}
    base_clef_of = {s.subject: s.clef for s in staves}

    base = run(staves, printed_lineups, ref_names, base_slot_clef, base_clef_of)
    bc = summarise(base)
    print("=" * 74)
    print("BASELINE (the shipped readings)")
    print("=" * 74)
    print("   %s" % dict(bc))
    forced0 = bc["ok"] + bc["condensation"] + bc["graft"]
    print("   forced %d, grafts %d" % (forced0, bc["graft"]))
    if forced0 == 0:
        print("DEAD: the baseline forces nothing -- nothing to perturb",
              file=sys.stderr)
        return 2

    unnamed = [s for s in staves if not s.named]

    print()
    print("=" * 74)
    print("ARM 1 -- perturb ONE UNNAMED staff's own clef")
    print("=" * 74)
    tally = collections.Counter()
    grafting = []
    n_arms = 0
    for s in unnamed:
        for c in CLEFS:
            if c == s.clef:
                continue
            n_arms += 1
            clef_of = dict(base_clef_of)
            clef_of[s.subject] = c
            res = run(staves, printed_lineups, ref_names, base_slot_clef, clef_of)
            g = summarise(res)["graft"]
            f = sum(summarise(res)[k] for k in ("ok", "condensation", "graft"))
            tally["arms"] += 1
            tally["grafts"] += g
            if g:
                grafting.append((s.subject, s.clef, c, g))
            if f < forced0:
                tally["went_quieter"] += 1
            elif f > forced0:
                tally["went_louder"] += 1
            else:
                tally["same_reach"] += 1
    print("   arms run                     %d" % n_arms)
    print("   arms producing a GRAFT       %d" % len(grafting))
    print("   arms where reach FELL        %d" % tally["went_quieter"])
    print("   arms where reach ROSE        %d" % tally["went_louder"])
    print("   arms where reach unchanged   %d" % tally["same_reach"])
    for g in grafting:
        print("      GRAFT %s  %s->%s  (%d grafted)" % g)

    print()
    print("=" * 74)
    print("ARM 2 -- perturb ONE REFERENCE slot's clef (the wider blast)")
    print("=" * 74)
    tally2 = collections.Counter()
    grafting2 = []
    for i, name in enumerate(ref_names):
        for c in CLEFS + (None,):
            if c == base_slot_clef[i]:
                continue
            slot_clef = dict(base_slot_clef)
            slot_clef[i] = c
            res = run(staves, printed_lineups, ref_names, slot_clef, base_clef_of)
            g = summarise(res)["graft"]
            f = sum(summarise(res)[k] for k in ("ok", "condensation", "graft"))
            tally2["arms"] += 1
            tally2["grafts"] += g
            if g:
                grafting2.append((i, name, base_slot_clef[i], c, g, f))
    print("   arms run                     %d" % tally2["arms"])
    print("   arms producing a GRAFT       %d" % len(grafting2))
    for i, name, was, now, g, f in grafting2:
        print("      GRAFT slot %2d %-14s %s->%s : %d grafted, %d forced"
              % (i, name, was, now, g, f))

    print()
    print("=" * 74)
    print("VERDICT")
    print("=" * 74)
    total_grafting = len(grafting) + len(grafting2)
    print("   single-reading perturbations tried : %d" % (n_arms + tally2["arms"]))
    print("   of those, producing a GRAFT        : %d" % total_grafting)
    print("   -> the rule fails %s under a wrong clef"
          % ("SAFE" if total_grafting == 0 else "UNSAFE"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
