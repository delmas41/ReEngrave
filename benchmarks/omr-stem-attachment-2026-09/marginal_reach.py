"""MARGINAL REACH -- what the convention adds to the tier that already shipped.

⚠️⚠️ THE WHOLE POINT IS THAT 472 IS NOT THE ANSWER. Both shared records are
PRE-tier -- `no_stem` 793 on Litolff, and no `beam_mate` verdict anywhere -- so
`omr-stem-ink-2026-09`'s "472 heads the convention can speak for" is measured
over a population that still contains the 152 heads the beam-mate tier now
serves. `docs/engraving-conventions.md` pools the two documents into "reach
**1,125 heads that currently abstain**", which inherits the same double count.
The number a decision should be taken on is what the convention adds AFTER that
tier has run.

It cross-tabulates, per head the record abstained `no_stem` on:

    rows   what the shipped beam-mate tier does   (beam_mate / stays no_stem)
    cols   what the convention says               (speaks / both / neither)

⚠️ THE AGREEMENT CELL IS A CROSS-CHECK, NOT AN ARBITER, and this file will not
call it one. Where both speak they can be compared -- but they are NOT
independent. The beam-mate borrows a MATE's `stem_projection`, which reads
`Q.STEM` rows and every notehead box in the cell; the convention reads raster
ink beside THIS head plus its own box and the staff spacing. They share the
notehead boxes and the plate, and differ in which ink they read and by what
method. *An arbiter correlated with one party sides with its own family* --
which already happened on this quantity, when a probe claimed the beam "shares
an input with neither" and it shared the FRAME. So the agreement is reported
with its correlation named, and settles nothing.

    python3 marginal_reach.py --rows out/L-rows.json \
        --beammate out/L-beammate.json --label L --out out/L-marginal.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.line_detection import STEM_MAX_HEIGHT_LINES      # noqa: E402

#: The physical gate `transfer_check.py` prices. Both edges are
#: `line_detection`'s own, IMPORTED: a run shorter than the shortest component
#: that module calls a stem, or longer than the longest, is not a stem -- its
#: comment on the cap says in terms *"That is a barline, and it is what the cap
#: is for."*
GATE_LO, GATE_HI = 2.0, STEM_MAX_HEIGHT_LINES


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True, help="convention_rows.py output")
    ap.add_argument("--beammate", required=True, help="beam_mate_set.py output")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    conv = {r["subject"]: r for r in
            json.loads(Path(a.rows).read_text())["rows"]}
    fired = json.loads(Path(a.beammate).read_text())["fired"]
    if not conv or not fired:
        print("DEAD: one of the two inputs is empty", file=sys.stderr)
        return 2

    #: The population is the record's own `no_stem` abstention, with whole
    #: notes already excluded by `convention_rows.py` (they carry no stem and
    #: the decision is right to abstain on them).
    pop = [s for s, r in conv.items() if r["reason"] == "no_stem"]
    if not pop:
        print("DEAD: no `no_stem` head carries a convention row",
              file=sys.stderr)
        return 2

    states = ("speaks", "both", "neither")
    tab: collections.Counter = collections.Counter()
    for s in pop:
        tab[("beam_mate" if s in fired else "stays no_stem",
             conv[s]["state"])] += 1

    print(f"{a.label}: {len(pop)} heads abstained `no_stem` "
          f"(whole notes excluded)\n")
    print(f"{'the shipped tier':<20}" + "".join(f"{x:>10}" for x in states)
          + f"{'total':>10}")
    for pr in ("beam_mate", "stays no_stem"):
        row = [tab[(pr, x)] for x in states]
        print(f"{pr:<20}" + "".join(f"{n:>10}" for n in row)
              + f"{sum(row):>10}")
    col = [sum(tab[(pr, x)] for pr in ("beam_mate", "stays no_stem"))
           for x in states]
    print(f"{'total':<20}" + "".join(f"{n:>10}" for n in col)
          + f"{sum(col):>10}")

    served = sum(tab[("beam_mate", x)] for x in states)
    overlap = tab[("beam_mate", "speaks")]
    gross = sum(tab[(pr, "speaks")] for pr in ("beam_mate", "stays no_stem"))
    marginal = tab[("stays no_stem", "speaks")]
    still = sum(tab[("stays no_stem", x)] for x in states)

    # the same, under the physical gate on the run length
    def gated(pr):
        return sum(1 for s in pop
                   if (("beam_mate" if s in fired else "stays no_stem") == pr)
                   and conv[s]["says"]
                   and GATE_LO <= max(conv[s]["R_up"],
                                      conv[s]["L_down"]) <= GATE_HI)
    g_marg, g_over = gated("stays no_stem"), gated("beam_mate")

    print(f"\n== THE NUMBER THIS DIRECTORY EXISTS FOR ==")
    print(f"   convention speaks for (GROSS, as published)        {gross:>6}")
    print(f"   of those, the beam-mate tier ALREADY serves        {overlap:>6}")
    print(f"   MARGINAL REACH                                     {marginal:>6}")
    print(f"   ... under the physical gate [{GATE_LO:g}, {GATE_HI:g}] spaces  "
          f"        {g_marg:>6}")
    print(f"\n   beam-mate tier reach on this document              {served:>6}")
    print(f"   heads still unread after it                        {still:>6}")
    if served and still:
        print(f"\n   the convention speaks for {overlap/served:.1%} of the "
              f"beam-mate population and {marginal/still:.1%} of the rest")

    agree = collections.Counter()
    for s in pop:
        if s not in fired or not conv[s]["says"]:
            continue
        agree["AGREES" if conv[s]["says"] == fired[s] else "disagrees"] += 1
    tot = agree["AGREES"] + agree["disagrees"]
    print(f"\n== CROSS-CHECK where BOTH speak (n={tot}) -- NOT an arbiter ==")
    for k, n in agree.most_common():
        print(f"   {k:<12} {n:>6}")
    if tot:
        print(f"   -> they agree {agree['AGREES']/tot:.1%}")

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"label": a.label, "population": len(pop),
             "gross": gross, "overlap": overlap, "marginal": marginal,
             "marginal_gated": g_marg, "overlap_gated": g_over,
             "gate": [GATE_LO, GATE_HI],
             "beam_mate_reach": served, "still_unread": still,
             "table": {f"{k[0]}|{k[1]}": n for k, n in tab.items()},
             "both_speak_agreement": dict(agree)}, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
