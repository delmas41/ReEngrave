#!/usr/bin/env python3
"""Are our errors WITHIN a family or ACROSS one? — the price of the hierarchy.

MEASUREMENT ONLY, on committed data.

Sean reads family first: "is this woodwinds, brass, percussion or strings — and
then placement within that family. What is it before and after." That is a
change to the SHAPE of the alignment, not another signal:

    FLAT subsequence matching lets one error travel the whole page. A staff
    dropped in the brass shifts every index below it, so a slip in the winds
    can misname a cello.
    TWO-LEVEL matching contains it. Align the four family BLOCKS, then align
    within each block; a deletion inside the brass cannot move the string
    block because the family boundary re-anchors it.

⚠️ WE HAVE NEVER MEASURED WHICH KIND OF ERROR WE HAVE. Horn read as Trumpet is
a small error; Horn read as Viola is a structural failure. Pooling them hid the
distinction, and it decides how much the hierarchy is worth BEFORE it is built.

PRE-REGISTERED, both readings:

  MOSTLY WITHIN-FAMILY  the family level is already solid and only the fine
                        grain fails ⇒ the two-level split is picking up
                        something real, and the inner question shortens from
                        "which of ~14 roster entries" to "which of the ~4
                        brass entries", which is the question clef and
                        transposition can actually answer.
  MANY CROSS-FAMILY     the family assignment ITSELF is the problem ⇒ the
                        hierarchy must be built on a source strong enough to
                        carry it, which is a different and larger job than
                        re-shaping the aligner.

Also reports FAMILY-LEVEL coverage and precision as their own row, because a
layer that names the family on every staff and the instrument on 0.903 is more
useful than one number implies — and `P(set)` consumers can use a family with
no instrument at all.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_family_errors.py

── RESULT 2026-09-05: BOTH PRE-REGISTERED READINGS CAME TRUE, ON DIFFERENT ARMS
198 records. Truth families: woodwind 65, brass 47, string 69, percussion 15,
voice 2; 0 truth names without a family.

    LAYOUT reference (coverage 0.793, so 41 staves ABSTAIN)
        named wrongly 20 — WITHIN family 13 (0.650), ACROSS 7 (0.350)

    PAGE-1 ROSTER reference (coverage 1.000, nothing hidden)
        named wrongly 14 — WITHIN family  4 (0.286), ACROSS 10 (0.714)

⚠️⚠️ THE SPLIT INVERTS BETWEEN THE ARMS, AND ABSTENTION IS THE CONFOUND. The
layout arm's "mostly within-family" is computed over only the 20 staves it was
confident enough to NAME; its 41 abstentions — the hard cases — are excluded
from the split entirely. The roster arm names everything, so its errors include
those same hard staves and are disproportionately structural. **The
pre-registered dichotomy is not robust to the arm, and I am not picking a
side**: at n=20 and n=14 neither number can carry the hierarchy decision.

WHAT IS SOLID, in both arms: THE FAMILY LEVEL IS MATERIALLY MORE RELIABLE THAN
THE INSTRUMENT LEVEL.

    level        coverage  precision
    instrument      0.793      0.873      (layout ref)
    family          0.793      0.955
    instrument      1.000      0.903      (page-1 roster ref, n=145)
    family          1.000      0.931

⭑ Family precision 0.955 vs instrument 0.873 — the layer knows WHICH SECTION a
staff belongs to far better than which instrument, on every arm measured. That
supports reporting family as its own row from here on, and it is directly
usable by a `P(set)` consumer, which can act on a family with no instrument at
all.

THE CROSS-FAMILY ERRORS, named individually because there are few enough:
woodwind->brass x3, percussion->string x2 (Timpani read as Violin — the
structural failure Sean's hierarchy is aimed at), brass->woodwind x1,
brass->percussion x1.

⚠️ SO THE HIERARCHY IS NOT YET PRICED. What this probe establishes is that the
family level is the STRONGER of the two levels, which is a precondition for a
two-level alignment being worth building; what it cannot establish at this n is
how much containment would buy. The 10 cross-family errors under the roster arm
are where it would act, out of 145 staves.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                  # noqa: E402
from tools.omr.score_layouts import ScoreLayout, fit_layouts  # noqa: E402

IDENT = HERE / "heldout-identity.json"


def family(name):
    if not name:
        return None
    m = INST.lookup(name)
    return m.instrument.family if m else None


def acceptable_families(accept):
    return {family(a) for a in accept if family(a)}


def main():
    ident = json.loads(IDENT.read_text())
    recs = [r for r in ident["records"] if r["TRUTH"]]
    print(f"records with truth: {len(recs)}   tag {ident['meta']['tag']!r}")
    if not recs:
        raise SystemExit("REFUSING to report: no records.")

    fams = Counter(family(r["TRUTH"]) for r in recs)
    print(f"  truth families: {dict(fams)}")
    unresolved = sum(1 for r in recs if family(r["TRUTH"]) is None)
    print(f"  truth names with NO family in the lexicon: {unresolved}")

    # ── the split ───────────────────────────────────────────────────────────
    within = across = 0
    detail = Counter()
    abstain_fam = 0
    for r in recs:
        tf = family(r["TRUTH"])
        got = r["HELDOUT"]
        if got and got in r["TRUTH_acceptable"]:
            continue                                   # right, not an error
        if not got:
            abstain_fam += 1                           # abstention, no family
            continue
        gf = family(got)
        if gf and tf and gf == tf:
            within += 1
        else:
            across += 1
        detail[(tf, gf)] += 1
    wrong = within + across
    print(f"\n{'='*72}\nTHE SPLIT — every staff NAMED WRONGLY\n{'='*72}")
    print(f"  named wrongly            {wrong}")
    print(f"    WITHIN family          {within}  "
          f"({within/wrong if wrong else 0:.3f})")
    print(f"    ACROSS families        {across}  "
          f"({across/wrong if wrong else 0:.3f})")
    print(f"  (abstentions, which have no family to be wrong about: "
          f"{abstain_fam})")
    print(f"\n  confusions (truth family -> named family):")
    for (tf, gf), c in detail.most_common(12):
        mark = "  within" if tf == gf else "  ACROSS"
        print(f"    {c:3d}  {str(tf):10s} -> {str(gf):10s}{mark}")

    # ── family-level coverage and precision, as their own row ───────────────
    print(f"\n{'='*72}\nFAMILY LEVEL vs INSTRUMENT LEVEL\n{'='*72}")

    def score(level):
        tot = named = right = 0
        for r in recs:
            tot += 1
            got = r["HELDOUT"]
            if not got:
                continue
            named += 1
            if level == "instrument":
                if got in r["TRUTH_acceptable"]:
                    right += 1
            else:
                if family(got) and family(got) in acceptable_families(
                        r["TRUTH_acceptable"]):
                    right += 1
        return tot, named, named / tot, right, right / named if named else 0

    print(f"  {'level':14s} {'n':>4s} {'named':>6s} {'coverage':>9s} "
          f"{'right':>6s} {'precision':>10s}")
    out = {}
    for level in ("instrument", "family"):
        tot, named, cov, right, prec = score(level)
        out[level] = (cov, prec)
        print(f"  {level:14s} {tot:4d} {named:6d} {cov:9.3f} {right:6d} "
              f"{prec:10.3f}")
    print(f"\n  ⭑ family precision {out['family'][1]:.3f} against instrument "
          f"{out['instrument'][1]:.3f}")

    # ── the same, under the PAGE-1 ROSTER reference ─────────────────────────
    by_sys = defaultdict(list)
    for r in recs:
        by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])
    rosters = {}
    for (rid, sidx), g in by_sys.items():
        w = rid.rsplit("-p", 1)[0]
        p = int(rid.rsplit("-p", 1)[1])
        if w not in rosters or (p, sidx) < rosters[w][0]:
            rosters[w] = ((p, sidx), [r["TRUTH"] for r in g])
    tot = named = right_i = right_f = 0
    r_within = r_across = 0
    for (rid, sidx), g in by_sys.items():
        w = rid.rsplit("-p", 1)[0]
        key, lineup = rosters[w]
        if (int(rid.rsplit("-p", 1)[1]), sidx) == key:
            continue
        clefs = {i: r["clef_read"] for i, r in enumerate(g) if r["clef_read"]}
        lay = (ScoreLayout("page1-roster", tuple(lineup), ""),)
        fit = fit_layouts(len(g), labels=None, clefs=clefs or None, layouts=lay)
        for i, r in enumerate(g):
            tot += 1
            got = fit.assignment[i] if fit else None
            if not got:
                continue
            named += 1
            if got in r["TRUTH_acceptable"]:
                right_i += 1
            else:
                tf, gf = family(r["TRUTH"]), family(got)
                if tf and gf and tf == gf:
                    r_within += 1
                else:
                    r_across += 1
            if family(got) in acceptable_families(r["TRUTH_acceptable"]):
                right_f += 1
    if tot:
        print(f"\n  UNDER THE PAGE-1 ROSTER (oracle roster, join only, n={tot}):")
        print(f"    instrument  coverage {named/tot:.3f}  precision "
              f"{right_i/named if named else 0:.3f}")
        print(f"    family      coverage {named/tot:.3f}  precision "
              f"{right_f/named if named else 0:.3f}")
        rw = r_within + r_across
        print(f"    of {rw} wrong: WITHIN family {r_within} "
              f"({r_within/rw if rw else 0:.3f}), ACROSS {r_across}")

    (HERE / "family-errors.json").write_text(json.dumps({
        "within": within, "across": across,
        "levels": {k: list(v) for k, v in out.items()},
    }, indent=1))


if __name__ == "__main__":
    main()
