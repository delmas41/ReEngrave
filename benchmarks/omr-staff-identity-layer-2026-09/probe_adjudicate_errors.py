#!/usr/bin/env python3
"""The 14 roster-arm errors, each with the evidence a READER would have.

MEASUREMENT ONLY — this probe DUMPS; the adjudication is hand work and its
verdicts live in ADJUDICATION below.

THE QUESTION. `probe_page1_roster.py` reaches precision 0.903 with roster +
order + clef and NOTHING ELSE. Family-first hierarchy, brackets, staff spacing,
the roster's own family ordering, transposition and written range are all
unspent. So: is the residual a probabilistic ceiling, or a list of unhandled
cases? Every error is classified into exactly one of

    A UNHANDLED   the evidence is on the page and we did not ask for it
                  -> name the mechanism; the A list IS the work order
    B IRREDUCIBLE the page genuinely does not say, and a reader could not
                  settle it either -> the real floor
    C UPSTREAM    the identity logic was fine; the clef / label / segmentation
                  feeding it was wrong -> another layer's problem

⚠️ CLASS C MATTERS AND MUST NOT BE POOLED. An identity error caused by a
misread clef is not evidence about identity, and counting it inflates the
apparent floor.

⚠️ BE ADVERSARIAL ABOUT B. The standard is what a reader would do with this
page in front of them, and Sean's own procedure is the reference: roster,
family, position within family, then clef and transposition.

⚠️ n = 14 errors, ONE arm, THREE engravings (two of the four rows are one
plate). This yields a WORK ORDER and a FLOOR ESTIMATE, never a rate.

⚠️ `group_index` is NOT in these fixtures — they predate its serialisation
(committed this session). Where an adjudication cites a bracket, that is a
statement about evidence the page carries and the pipeline can now see, not
about a field present in this JSON. Staff SPACING is computed here directly
from `staff_geometry.line_ys_page`, so the spacing evidence IS measured.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_adjudicate_errors.py

── ADJUDICATION 2026-09-05 ───────────────────────────────────────────────────
VERDICT:  A (unhandled) 14   ·   B (irreducible) 0   ·   C (upstream) 0

⚠️⚠️ THE FACT THAT DECIDES ALL FOURTEEN: **in 14 of 14, the roster entry at
that ordinal IS the truth.** The roster held the right answer at the right
index and the aligner chose otherwise. These are not identification failures;
they are the alignment declining evidence it already had. Counterfactuals on
the same pages (`probe_adjudication_counterfactual.py`):

    arm                  cov    prec   cross-family errors
    DP (as measured)   1.000   0.903        10
    +CAPACITY          0.938   0.934         8
    ORDINAL-if-equal   1.000   0.952         4
    ORDINAL            1.000   1.000         0

TWO MECHANISMS ACCOUNT FOR THE FOURTEEN, 7 AND 7.

A1 — EQUAL-COUNT BALANCE (7 errors: brahms p3 s0, p4 s0, p4 s1 x2 each at
     ord 4 and 8; dvorak p7 s0 ord 3 and 7).
     Every one sits in a system whose staff count EQUALS the roster length
     (brahms 14 v 14, dvorak 15 v 15). ⚠️ When m == n, the only order-preserving
     bijection IS THE IDENTITY MAP — a skip must be paid for by a continuation
     elsewhere, and both are wrong by construction. The DP is free to do it
     anyway and does. This is a HARD LOGICAL CONSTRAINT the aligner does not
     enforce, not a heuristic: forbid gaps and continuations when m == n.
     Fixes exactly these 7 (`ORDINAL-if-equal`, 131 -> 138).

A2 — SUPPRESSION AT THE ROSTER TAIL (7 errors: all Beethoven p2, both scans,
     ord 9 and 10 of 11 against a 12-entry roster).
     The page prints 11 staves for a 12-entry roster and the missing entry is
     the LAST. Two sub-faults:
       · ord 9, Viola read as Violin/Cello — the Viola staff's clef is MISREAD
         as treble, and the aligner lets one weak clef outvote roster+order.
         ⚠️ Filed A, not C: the clef fault is upstream and real, but the layer
         had the roster ordinal and did not use it, so the identity logic was
         NOT fine. Partly reachable by CAPACITY — Beethoven's roster holds
         exactly TWO Violin entries and the aligner emits a THIRD, which is
         impossible on its face (prec 0.903 -> 0.934, at 9 staves of coverage).
       · ord 10, Cello read as the roster's last entry — both take bass clef,
         so clef cannot separate them, and the POSITIONAL term prefers the last
         roster entry (staff 10/10 = 1.000 against Cello at 10/11 = 0.909).
         The reader's answer is that this edition CONDENSES cello and bass onto
         one staff, so the entry is not suppressed but MERGED — which is the
         existing `OMR_CONDENSED_PARTS` territory, and the hardest of the three.

B — ZERO, and the standard was applied adversarially. A reader holding the
    page-1 roster and counting staves gets all 14 right; `ORDINAL` scoring
    145/145 is that reader, mechanised. ⚠️ ITS SUCCESS IS CONDITIONAL: every
    later system in THIS corpus is the roster minus a suppressed TAIL, so a
    page suppressing a MIDDLE staff would be misnamed from there down and this
    corpus cannot say how often that happens. The B count is 0 on the evidence
    available, not a proof that no irreducible case exists.

C — ZERO. The three misread Viola clefs are genuine upstream faults, but they
    are not counted here because the identity layer had sufficient evidence to
    survive them. Pooling them into the floor would have inflated it.

⇒ SEAN'S POSITION IS SUPPORTED ON THIS EVIDENCE: the residual is unhandled
cases, not a probabilistic ceiling. The work order, by errors fixed:
    1. equal-count balance constraint   7   (hard constraint, no tuning)
    2. roster capacity / uniqueness     4   (costs coverage; needs a rule for
                                             the surplus rather than dropping)
    3. condensation at the roster tail  3   (overlaps OMR_CONDENSED_PARTS)

⚠️ n = 14 errors, ONE arm, THREE engravings (two of the four rows are one
plate). A work order and a floor estimate, never a rate.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                     # noqa: E402
from tools.omr.score_layouts import ScoreLayout, fit_layouts  # noqa: E402

IDENT = HERE / "heldout-identity.json"
FIXTURES = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
            "reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures")
TAG = ".reconciliation"


def family(n):
    m = INST.lookup(n) if n else None
    return m.instrument.family if m else None


def geometry_index():
    """(row_id, system_index, ordinal) -> staff dict, for spacing and key sig."""
    import glob
    out = {}
    for p in sorted(glob.glob(f"{FIXTURES}/*{TAG}.omr.json")):
        rid = Path(p).name[: -len(f"{TAG}.omr.json")].rstrip(".")
        for page in json.loads(Path(p).read_text()).get("pages", []):
            for sysd in page.get("systems", []):
                staves = sorted(
                    sysd.get("staves", []),
                    key=lambda s: (s.get("staff_geometry") or {})
                    .get("line_ys_page", [0])[0])
                for i, st in enumerate(staves):
                    out[(rid, sysd.get("system_index"), i)] = st
    return out


def gaps(geo, rid, sidx, i, n):
    """Vertical gap in STAFF SPACES to the staff above and below."""
    def top(k):
        g = (geo.get((rid, sidx, k)) or {}).get("staff_geometry") or {}
        ys = g.get("line_ys_page")
        return (ys[0], ys[-1], g.get("line_spacing_px")) if ys else None
    me = top(i)
    if not me:
        return None, None
    sp = me[2] or 1
    up = dn = None
    if i > 0 and top(i - 1):
        up = round((me[0] - top(i - 1)[1]) / sp, 2)
    if i < n - 1 and top(i + 1):
        dn = round((top(i + 1)[0] - me[1]) / sp, 2)
    return up, dn


def main():
    ident = json.loads(IDENT.read_text())
    geo = geometry_index()
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

    errors = []
    for (rid, sidx), g in sorted(by_sys.items()):
        w = rid.rsplit("-p", 1)[0]
        key, lineup = rosters[w]
        if (int(rid.rsplit("-p", 1)[1]), sidx) == key:
            continue
        n = len(g)
        clefs = {i: r["clef_read"] for i, r in enumerate(g) if r["clef_read"]}
        lay = (ScoreLayout("page1-roster", tuple(lineup), ""),)
        fit = fit_layouts(n, labels=None, clefs=clefs or None, layouts=lay)
        pred = [fit.assignment[i] if fit else None for i in range(n)]
        for i, r in enumerate(g):
            got = pred[i]
            if got and got in r["TRUTH_acceptable"]:
                continue
            up, dn = gaps(geo, rid, sidx, i, n)
            st = geo.get((rid, sidx, i)) or {}
            ks = st.get("key_signature") if st.get("key_signature_read") else None
            nbk = []
            for j in (i - 1, i + 1):
                s2 = geo.get((rid, sidx, j))
                nbk.append((s2.get("key_signature")
                            if s2 and s2.get("key_signature_read") else None))
            errors.append({
                "row": rid, "sys": sidx, "ord": i, "n": n,
                "TRUTH": r["TRUTH"], "TRUTH_family": family(r["TRUTH"]),
                "PRED": got, "PRED_family": family(got),
                "clef_read": r["clef_read"],
                "roster_at_ord": lineup[i] if i < len(lineup) else None,
                "truth_above": g[i-1]["TRUTH"] if i else None,
                "truth_below": g[i+1]["TRUTH"] if i+1 < n else None,
                "pred_above": pred[i-1] if i else None,
                "pred_below": pred[i+1] if i+1 < n else None,
                "gap_above_spaces": up, "gap_below_spaces": dn,
                "keysig": ks, "keysig_neighbours": nbk,
                "roster": lineup,
            })

    print(f"ROSTER-ARM ERRORS: {len(errors)}\n")
    for k, e in enumerate(errors, 1):
        cross = "CROSS-FAMILY" if e["TRUTH_family"] != e["PRED_family"] else "within"
        print(f"{'='*74}\n[{k}] {e['row']} sys{e['sys']} ord{e['ord']}/{e['n']}"
              f"   {cross}")
        print(f"   TRUTH {e['TRUTH']} ({e['TRUTH_family']})   "
              f"PRED {e['PRED']} ({e['PRED_family']})")
        print(f"   clef read: {e['clef_read']}   roster entry at this ordinal: "
              f"{e['roster_at_ord']}")
        print(f"   truth  above/below: {e['truth_above']} / {e['truth_below']}")
        print(f"   pred   above/below: {e['pred_above']} / {e['pred_below']}")
        print(f"   staff GAP above/below (spaces): {e['gap_above_spaces']} / "
              f"{e['gap_below_spaces']}")
        print(f"   key sig: {e['keysig']}   neighbours: {e['keysig_neighbours']}")
    (HERE / "adjudication-input.json").write_text(json.dumps(errors, indent=1))
    print(f"\nwrote {HERE / 'adjudication-input.json'}")


if __name__ == "__main__":
    main()
