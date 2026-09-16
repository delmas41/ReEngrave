"""Do the witnesses agree with EACH OTHER, and is the agreement worth more?

The duration work here is on record that two repairs were **SUPER-ADDITIVE** —
each alone left the bar still wrong, because a bar is right only when every
note in it is. Two weak witnesses that AGREE may be worth more than either,
and no separate table can show that. Three witnesses over one arc:

  * **S2/S5** — the existing position grammar: the flanked heads sit on the
    same staff STEP (tie) or different ones (slur). Available on 345 arcs.
  * **S4-broad** — the arc's near edge is past the stem tip (`t_axis >= τ`)
    ⇒ SLUR, else ABSTAIN. One-sided by Sean's own construction.
  * **S6-broad** — this arc is the LOWER (tie) or UPPER (slur) member of a
    stack within 3 staff spaces.

⚠️ THE S6 BAND IS READ OFF ITS OWN DOSE-RESPONSE, NOT FITTED TO THIS TABLE.
`widen_s6.py` shows agreement at 0.909 / 0.750 / 0.700 inside 3 spaces and
0.55 beyond, on every relaxation; 3 spaces is where that curve flattens and
was chosen before this file existed. S4's `τ` is NOT chosen at all — the whole
sweep is printed.

⚠️ AGREEMENT WITH THE DETECTOR IS NOT ACCURACY. Two witnesses agreeing with
each other and with the detector is three readings of one piece of ink.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict


def _is_tie(cls) -> bool:
    return str(cls).lower().startswith("tie")


def _binom_tail(k: int, n: int, p: float = 0.5) -> float:
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
               for i in range(k, n + 1))


def s6_per_arc(rows, *, max_gap=300.0):
    """What S6 says about each ARC, from the pair it belongs to.

    An arc in two stacks with contradicting orders SAYS NOTHING — refusing is
    the rule `adjudicate_voices`' divisi guard already applies, and picking one
    would be the probe deciding what the record does not.
    """
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[r["cell"]].append(r)
    says = {}
    for cell_rows in by_cell.values():
        for a in cell_rows:
            ax0, ay0, ax1, ay1 = a["box"]
            votes = set()
            for b in cell_rows:
                if a["subject"] == b["subject"]:
                    continue
                bx0, by0, bx1, by1 = b["box"]
                if min(ax1, bx1) - max(ax0, bx0) <= 0:
                    continue
                gap = -(min(ay1, by1) - max(ay0, by0))
                if not 0 < gap < max_gap:
                    continue
                votes.add("slur" if (ay0 + ay1) < (by0 + by1) else "tie")
            says[a["subject"]] = votes.pop() if len(votes) == 1 else None
    return says


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("widen_json")
    a = ap.parse_args(argv)
    rows = json.load(open(a.widen_json))["rows"]
    s6 = s6_per_arc(rows)

    def s2s5(r):
        if r["flanked"] < 2 or r["first_step"] is None or r["last_step"] is None:
            return None
        return "tie" if r["first_step"] == r["last_step"] else "slur"

    def s4(r, thr):
        if not r["eps"]:
            return None
        t = max(e["t_axis"] for e in r["eps"])
        return "slur" if t >= thr else None      # one-sided: near ⇒ abstain

    report = {"n_arcs": len(rows)}
    report["availability"] = {
        "S2_S5": sum(1 for r in rows if s2s5(r) is not None),
        "S6_within_3_spaces": sum(1 for r in rows if s6.get(r["subject"])),
        "S4_at_t_axis_1.0": sum(1 for r in rows if s4(r, 1.0)),
        "S2_S5_and_S6": sum(1 for r in rows
                            if s2s5(r) and s6.get(r["subject"])),
        "S4_and_S6_at_1.0": sum(1 for r in rows
                                if s4(r, 1.0) and s6.get(r["subject"])),
        "all_three_at_1.0": sum(1 for r in rows if s2s5(r) and s6.get(r["subject"])
                                and s4(r, 1.0)),
    }

    def agree(sub, witness):
        k = sum(1 for r in sub if witness(r) == ("tie" if _is_tie(r["cls"])
                                                 else "slur"))
        base = sum(1 for r in sub
                   if not _is_tie(r["cls"])) / len(sub) if sub else 0.0
        return {"n": len(sub), "correct": k,
                "agreement": round(k / len(sub), 4) if sub else None,
                "base_rate_slur_in_this_subset": round(base, 4)}

    # ── each witness alone, over ITS OWN population ─────────────────────────
    report["alone"] = {
        "S2_S5": agree([r for r in rows if s2s5(r)], s2s5),
        "S6": agree([r for r in rows if s6.get(r["subject"])],
                    lambda r: s6[r["subject"]]),
    }

    # ── S2/S5 and S6 together: do they agree, and does it help? ─────────────
    both = [r for r in rows if s2s5(r) and s6.get(r["subject"])]
    conc = [r for r in both if s2s5(r) == s6[r["subject"]]]
    disc = [r for r in both if s2s5(r) != s6[r["subject"]]]
    report["S2_S5_with_S6"] = {
        "both_speak": len(both),
        "they_CONCUR": len(conc),
        "they_CONFLICT": len(disc),
        "concur_rate": round(len(conc) / len(both), 4) if both else None,
        "when_they_CONCUR_agreement_with_reading": agree(conc, s2s5),
        "when_they_CONFLICT_S2_S5_agreement": agree(disc, s2s5),
        "when_they_CONFLICT_S6_agreement": agree(
            disc, lambda r: s6[r["subject"]]),
        # ⚠️ THE SUPER-ADDITIVITY TEST: is concurring better than either alone?
        "S2_S5_alone_on_the_both_population": agree(both, s2s5),
        "S6_alone_on_the_both_population": agree(
            both, lambda r: s6[r["subject"]]),
        "p_binomial_when_they_CONCUR": round(_binom_tail(
            sum(1 for r in conc
                if s2s5(r) == ("tie" if _is_tie(r["cls"]) else "slur")),
            len(conc), 0.5), 5) if conc else None,
    }

    # ⚠️⚠️ THE CONTROL WITHOUT WHICH "THEY CONCUR ⇒ 0.75" IS NOT A RESULT.
    # Conditioning on two noisy predictors AGREEING raises measured accuracy
    # even when one of them is pure noise — it is a selection effect, and this
    # repo's own rule is that a plausible aggregate is not evidence that its
    # parts are real. So S2/S5's labels are PERMUTED within the joint
    # population, keeping its marginal mix exactly, and the concur-subset
    # agreement is recomputed. If the real 0.75 sits inside that null, the
    # joint result is the selection effect and nothing more.
    import random
    truth = {r["subject"]: ("tie" if _is_tie(r["cls"]) else "slur")
             for r in both}
    real_labels = [s2s5(r) for r in both]
    s6_labels = [s6[r["subject"]] for r in both]
    truths = [truth[r["subject"]] for r in both]
    null = []
    rng = random.Random(20260915)
    for _ in range(20000):
        shuf = real_labels[:]
        rng.shuffle(shuf)
        hit = tot = 0
        for lab, s6l, tr in zip(shuf, s6_labels, truths):
            if lab == s6l:
                tot += 1
                hit += (lab == tr)
        if tot:
            null.append(hit / tot)
    null.sort()
    obs = len(conc) and sum(
        1 for r in conc
        if s2s5(r) == truth[r["subject"]]) / len(conc)
    report["S2_S5_with_S6"]["PERMUTATION_NULL"] = {
        "draws": len(null), "seed": 20260915,
        "observed_concur_agreement": round(obs, 4),
        "null_median": round(null[len(null) // 2], 4),
        "null_p95": round(null[int(0.95 * len(null))], 4),
        "p_value": round(sum(1 for v in null if v >= obs) / len(null), 5)
        if null else None,
        "observed_concur_n": len(conc),
    }

    # ── S4 swept against the other two ─────────────────────────────────────
    # ⚠️⚠️ THE OBVIOUS TABLE HERE IS VACUOUS BY CONSTRUCTION AND THE FIRST
    # DRAFT PRINTED IT. S4 is ONE-SIDED — it only ever says "slur" — so
    # "agreement of S4 on subset X" is identically the slur SHARE of X, and
    # comparing it with X's own base rate compares a number with itself. Every
    # such cell read `agreement == base_rate` to four decimals, which is the
    # tell. A one-sided rule can only be scored by comparing the population it
    # FIRES on against the population it does NOT, so that is what this does.
    def slur_share(sub):
        k = sum(1 for r in sub if not _is_tie(r["cls"]))
        return {"n": len(sub), "slur": k,
                "slur_share": round(k / len(sub), 4) if sub else None}

    report["S4_conditioned_on_the_others"] = []
    for thr in (0.0, 0.5, 1.0, 1.5, 2.0):
        blk = {"t_axis_at_least": thr}
        # Among arcs S6 speaks about, does S4 firing raise the slur share
        # ABOVE what S6 already implies? Split three ways so neither witness
        # is being scored against itself.
        for label, pred in (("S6_says_slur", lambda r: s6.get(r["subject"]) == "slur"),
                            ("S6_says_tie", lambda r: s6.get(r["subject"]) == "tie"),
                            ("S2_S5_says_slur", lambda r: s2s5(r) == "slur"),
                            ("S2_S5_says_tie", lambda r: s2s5(r) == "tie")):
            sub = [r for r in rows if pred(r) and r["eps"]]
            fires = [r for r in sub if s4(r, thr)]
            quiet = [r for r in sub if not s4(r, thr)]
            blk[label] = {
                "S4_fires": slur_share(fires),
                "S4_silent": slur_share(quiet),
                "difference_in_slur_share": (
                    round(len([r for r in fires if not _is_tie(r["cls"])]) / len(fires)
                          - len([r for r in quiet if not _is_tie(r["cls"])]) / len(quiet), 4)
                    if fires and quiet else None)}
        report["S4_conditioned_on_the_others"].append(blk)

    json.dump(report, sys.stdout, indent=2)
    print()
    if not both:
        print("DEAD: no arc has two witnesses.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
