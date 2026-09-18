"""MARGINAL REACH -- what the convention adds to the tier that already shipped.

⚠️ THE WHOLE POINT IS THAT 472 IS NOT THE ANSWER. Both shared records are
PRE-tier (`no_stem` 793 on Litolff, and no `beam_mate` verdict anywhere), so
`omr-stem-ink-2026-09`'s "472 heads it can speak for" is measured over a
population that still includes the 152 heads the beam-mate tier now serves.
The number a decision should be taken on is what the convention adds AFTER
that tier has run.

It cross-tabulates, per non-whole-note head:

    rows   what the POST-tier record says   (beam_mate / no_stem / ...)
    cols   what the convention says         (speaks / both / neither)

and reports the overlap and the marginal set.

⚠️ THE AGREEMENT CELL IS A CROSS-CHECK, NOT AN ARBITER, and this file will not
call it one. Where both speak they can be compared -- but they are NOT
independent. The beam-mate borrows a MATE's `stem_projection`, which reads
`Q.STEM` rows and every notehead box in the cell; the convention reads raster
ink beside THIS head plus its own box and the staff spacing. They share the
notehead boxes and the plate, and differ in which ink they read and by what
method. *An arbiter correlated with one party sides with its own family* --
that already happened on this quantity when a probe claimed the beam "shares
an input with neither" and it shared the FRAME. So the agreement is reported
with its correlation named and is not used to settle anything.

    python3 marginal_reach.py --rows out/L-rows.json \
        --pre out/L-pre.json --post out/L-post.json --label L
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path


def load_verdicts(path: str) -> dict:
    d = json.loads(Path(path).read_text())
    v = d.get("verdicts") or {}
    if not v:
        raise SystemExit(f"DEAD: {path} holds no verdicts")
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True, help="convention_rows.py output")
    ap.add_argument("--pre", required=True, help="stem_arm --out, tier OFF")
    ap.add_argument("--post", required=True, help="stem_arm --out, tier ON")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    conv = {r["subject"]: r for r in
            json.loads(Path(a.rows).read_text())["rows"]}
    pre, post = load_verdicts(a.pre), load_verdicts(a.post)
    if not conv:
        print("DEAD: no convention rows", file=sys.stderr)
        return 2

    #: ⚠️ THE POPULATION IS THE PRE-TIER ABSTENTION, NOT EVERY HEAD. Whole
    #: notes are already out of `conv` (they carry no stem and the decision is
    #: right to abstain); this narrows to the heads the pre-tier record could
    #: not read, which is the population either mechanism is for.
    pop = [s for s, r in conv.items()
           if pre.get(s, {}).get("reason") == "no_stem"]
    if not pop:
        print("DEAD: no head is `no_stem` in the tier-OFF arm -- the arms are "
              "not what they claim.", file=sys.stderr)
        return 2

    tab: collections.Counter = collections.Counter()
    for s in pop:
        tab[(post.get(s, {}).get("reason") or "ABSENT",
             conv[s]["state"])] += 1

    post_reasons = sorted({k[0] for k in tab})
    states = ("speaks", "both", "neither")
    print(f"{a.label}: {len(pop)} heads the tier-OFF arm could not read "
          f"(whole notes already excluded)\n")
    print(f"{'post-tier reason':<18} " + "".join(f"{s:>10}" for s in states)
          + f"{'total':>10}")
    for pr in post_reasons:
        row = [tab[(pr, s)] for s in states]
        print(f"{pr:<18} " + "".join(f"{n:>10}" for n in row)
              + f"{sum(row):>10}")
    col = [sum(tab[(pr, s)] for pr in post_reasons) for s in states]
    print(f"{'total':<18} " + "".join(f"{n:>10}" for n in col)
          + f"{sum(col):>10}")

    served = sum(tab[("beam_mate", s)] for s in states)
    overlap = tab[("beam_mate", "speaks")]
    gross = sum(tab[(pr, "speaks")] for pr in post_reasons)
    marginal = sum(tab[(pr, "speaks")] for pr in post_reasons
                   if pr != "beam_mate")
    still = sum(tab[("no_stem", s)] for s in states)

    print(f"\n== the number this directory exists for ==")
    print(f"   convention speaks for (GROSS, what the sibling reports) {gross:>6}")
    print(f"   of those, the beam-mate tier ALREADY serves (OVERLAP)   {overlap:>6}")
    print(f"   MARGINAL REACH                                          {marginal:>6}")
    print(f"   beam-mate tier reach on this document                   {served:>6}")
    print(f"   heads still unread after the tier                       {still:>6}")
    if served:
        print(f"   convention speaks for {overlap / served:.1%} of the "
              f"beam-mate population, vs {marginal / still:.1%} of the rest"
              if still else "")

    agree = collections.Counter()
    for s in pop:
        pv = post.get(s, {})
        if pv.get("reason") != "beam_mate" or not conv[s]["says"]:
            continue
        agree["AGREES" if conv[s]["says"] == str(pv.get("value"))
              else "disagrees"] += 1
    tot = agree["AGREES"] + agree["disagrees"]
    print(f"\n== CROSS-CHECK where BOTH speak (n={tot}) -- NOT an arbiter, "
          f"see the docstring ==")
    for k, n in agree.most_common():
        print(f"   {k:<12} {n:>6}")
    if tot:
        print(f"   -> they agree {agree['AGREES'] / tot:.1%}")

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"label": a.label, "population": len(pop),
             "gross": gross, "overlap": overlap, "marginal": marginal,
             "beam_mate_reach": served, "still_unread": still,
             "table": {f"{k[0]}|{k[1]}": n for k, n in tab.items()},
             "both_speak_agreement": dict(agree)}, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
