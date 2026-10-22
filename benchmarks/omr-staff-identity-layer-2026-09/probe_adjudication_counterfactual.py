#!/usr/bin/env python3
"""Would the named mechanism actually fix the error? — adjudication as evidence.

MEASUREMENT ONLY.

The adjudication of the 14 roster-arm errors found one fact that dominates all
of them: **in 14 of 14, the roster entry at that ordinal IS the truth.** The
roster held the right answer at the right index and the aligner chose something
else. So the errors are not identification failures; they are the alignment
declining evidence it already had.

Rather than assert mechanisms in prose, each is run as a counterfactual arm on
the same pages and scored the same way:

    DP (as measured)   fit_layouts against the page-1 roster
    +CAPACITY          a roster entry may be used at most as many times as the
                       roster lists it. Beethoven's roster has exactly TWO
                       Violin entries, so a THIRD Violin is impossible — the
                       aligner currently emits one.
    ORDINAL            no alignment at all: staff i takes roster[i]. The
                       degenerate case, included because if the systems are
                       simply "the roster minus a suppressed tail" it should
                       do well, and that would say the DP's freedom is what
                       costs us.
    ORDINAL-if-equal   ordinal assignment ONLY where the system's staff count
                       equals the roster length; otherwise fall back to the DP.
                       The honest version of the above — it never guesses
                       through a suppression.

⚠️ These are counterfactuals on n=14 errors over 3 engravings, two of which are
one plate. They price a WORK ORDER; they are not a result and nothing is
proposed for shipping on them.

    python3 .../probe_adjudication_counterfactual.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                     # noqa: E402
from tools.omr.score_layouts import ScoreLayout, fit_layouts  # noqa: E402

IDENT = HERE / "heldout-identity.json"


def family(n):
    m = INST.lookup(n) if n else None
    return m.instrument.family if m else None


def main():
    ident = json.loads(IDENT.read_text())
    by_sys = defaultdict(list)
    for r in ident["records"]:
        if r["TRUTH"]:
            by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])
    rosters = {}
    for (rid, sidx), g in by_sys.items():
        w = rid.rsplit("-p", 1)[0]
        p = int(rid.rsplit("-p", 1)[1])
        if w not in rosters or (p, sidx) < rosters[w][0]:
            rosters[w] = ((p, sidx), [r["TRUTH"] for r in g])

    def dp_assign(g, lineup, capacity=False):
        n = len(g)
        clefs = {i: r["clef_read"] for i, r in enumerate(g) if r["clef_read"]}
        lay = (ScoreLayout("page1-roster", tuple(lineup), ""),)
        fit = fit_layouts(n, labels=None, clefs=clefs or None, layouts=lay)
        pred = [fit.assignment[i] if fit else None for i in range(n)]
        if not capacity:
            return pred
        # CAPACITY: never emit a roster entry more often than the roster lists
        # it. Applied as a post-pass so the DP is untouched; the surplus
        # assignment is dropped to an ABSTENTION rather than re-guessed,
        # because dropping is honest and re-guessing needs a rule we have not
        # measured.
        cap = Counter(lineup)
        used = Counter()
        out = []
        for p in pred:
            if p and used[p] < cap[p]:
                used[p] += 1
                out.append(p)
            else:
                out.append(None)
        return out

    def ordinal_assign(g, lineup, only_if_equal=False):
        n = len(g)
        if only_if_equal and n != len(lineup):
            return dp_assign(g, lineup)
        return [lineup[i] if i < len(lineup) else None for i in range(n)]

    arms = {
        "DP (as measured)": lambda g, l: dp_assign(g, l),
        "+CAPACITY": lambda g, l: dp_assign(g, l, capacity=True),
        "ORDINAL": lambda g, l: ordinal_assign(g, l),
        "ORDINAL-if-equal": lambda g, l: ordinal_assign(g, l, True),
    }

    print(f"{'arm':20s} {'n':>4s} {'named':>6s} {'cov':>7s} {'right':>6s} "
          f"{'prec':>7s} {'cross-fam err':>14s}")
    results = {}
    for name, fn in arms.items():
        tot = named = right = cross = 0
        for (rid, sidx), g in by_sys.items():
            w = rid.rsplit("-p", 1)[0]
            key, lineup = rosters[w]
            if (int(rid.rsplit("-p", 1)[1]), sidx) == key:
                continue
            pred = fn(g, lineup)
            for i, r in enumerate(g):
                tot += 1
                p = pred[i]
                if not p:
                    continue
                named += 1
                if p in r["TRUTH_acceptable"]:
                    right += 1
                elif family(p) != family(r["TRUTH"]):
                    cross += 1
        results[name] = (named / tot, right / named if named else 0)
        print(f"{name:20s} {tot:4d} {named:6d} {named/tot:7.3f} {right:6d} "
              f"{right/named if named else 0:7.3f} {cross:14d}")

    print(f"""
⚠️ READ `ORDINAL` WITH ITS PRECONDITION. It assigns staff i the roster's i-th
   entry with no alignment at all, so it can only work where the printed system
   IS the roster minus a suppressed TAIL. It is a diagnostic of how much of
   this corpus has that shape, not a proposal — a page that suppresses a MIDDLE
   staff would be misnamed from that staff down, and this corpus is too small
   to say how often that happens.""")

    (HERE / "adjudication-counterfactual.json").write_text(
        json.dumps({k: list(v) for k, v in results.items()}, indent=1))


if __name__ == "__main__":
    main()
