#!/usr/bin/env python3
"""Held-out-label staff identity: can the page name its own staves?

MEASUREMENT ONLY. Changes no pipeline behaviour. Reads the scan gate's
already-committed transcriptions; spends no detector time.

THE QUESTION. Sean's redirect: identity should be resolved once per page as a
first-class product, after which clef / key / range / transposition become
CONSUMERS of it rather than evidence for it. The measurement that decides
whether that is possible is the held-out one:

    hide the margin labels, predict each staff's instrument from geometry,
    clef, bracket group and score order alone, and score the prediction
    against the hand-read page truth the predictor never saw.

⚠️ FIXTURE PROVENANCE. The 20-row human-verified gate exists ONLY in the
`reconciliation` worktree as `<row>.reconciliation.omr.json`. The main
checkout's `fixtures/` holds the STALE 11-row `..graft09` set, which is what
`benchmarks/omr-staff-identity-2026-09/build_evidence.py` defaults to. This
probe ASSERTS the row count and the tag it actually loaded and prints both, so
a figure from here can never be silently differenced against an 11-row one.
`--tag` / `--fixtures` override.

⚠️ ANSWER-KEY DISCIPLINE. `works.json` `staves[]` (hand-read from the print) is
the SCORING KEY and is never consulted by an arm. Dossiers are not read at all
— they are generated from the same MusicXML the gate scores against, so a
dossier-fed arm is a labelled ceiling arm and never a benchmark figure.

⚠️ NO JOIN-ASSIGNED FIELD IS EVIDENCE. `staff["instrument"]`, `slot_index`,
`instrument_source`, `instrument_family` and any clef whose `clef_source` is
`slot_continuity` or `dossier` are OUTPUTS of the part->staff join. They are
read here for exactly one purpose — arm SHIPPED, which is by definition the
join's own answer — and are excluded from every predicting arm. The exclusion
is asserted, not assumed: `--audit-inputs` prints the per-arm input counts.

ARMS
    SHIPPED   staff["instrument"] as the pipeline wrote it (labels + everything)
    HELDOUT   fit_layouts(n, labels={}, clefs=<clefs a reader actually READ>)
    FLOOR     fit_layouts(n, labels={}, clefs={})  -- position alone
    CEILING   fit_layouts(n, labels=<truth>, clefs=<read>)  -- what the prior can
              do when identity is handed to it; a ceiling, never a result

    ORACLE_LAYOUT  held out, but the layout pool restricted to those whose
              vocabulary CONTAINS the true lineup -- reads the truth to build
              itself, so a ceiling demonstration and never an accuracy

Every arm is evaluated per (row, system, ordinal) -- PAGE-LEVEL keys, never
`slot_index`, because a slot is itself the output of an alignment.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_heldout_identity.py

── RESULTS 2026-09-05 ────────────────────────────────────────────────────────
20 rows / 396 staves / 198 scoreable / 180 clefs read / 0 unresolvable truth
names / 3 ENGRAVINGS (the two Beethoven scans are one plate).

    arm             spoke  coverage  right  precision
    SHIPPED           175     0.884    160      0.914
    HELDOUT           157     0.793    137      0.873
    ORACLE_LAYOUT     169     0.854    115      0.680
    FLOOR              62     0.313     46      0.742
    CEILING           196     0.990    196      1.000

KC-1 PASSES (bar: precision >= 0.75 at coverage >= 0.60). Hiding every margin
label costs 0.041 precision and 0.091 coverage. ⚠️ The bar came from the prior
11-row `.graft09` S5 figure (0.626 / 0.753) and is a REPRODUCTION bar: different
rows, different denominator, do not difference the two.

Per arm (HELDOUT coverage / precision):

    Breitkopf / BRAHMS 1     labels everything          0.886 / 0.806
    Litolff   / BEETHOVEN 5  winds+brass, strings never 0.971 / 0.955
    Simrock   / DVORAK 9     first page of movement     0.483 / 0.828

⚠️⚠️ THESE ROWS ARE LABELLED BY PUBLISHER AND THAT IS MISLEADING: in this
corpus **publisher is perfectly confounded with composer** -- Breitkopf carries
only Brahms, Litolff only Beethoven, Simrock only Dvorak (verified: each arm's
work set is a single composer). So a "publisher" row IS a work row, and the
COMPOSITIONAL reading is the correct one.

**Which instruments stand in a system is compositional; only whether the page
REVEALS it is a publisher fact.** Beethoven writes the timpani in and the flute
out — no engraver has a say. The engraver decides labelling, condensation, and
whether a tacet staff is suppressed rather than printed as rests. Publisher is
therefore never an explanatory variable for instrumentation here, and no prior
of the form "this house's pages carry these instruments" may be built from this
table.

Read the spread that way and it stops being about houses:

  - BEETHOVEN 5 scores 0.955 because its 12-staff lineup essentially IS
    `classical-condensed` — a fact about the standard orchestra of 1808. Its
    FLOOR arm (position alone, no clef, no label) scores precision 1.000 on 38
    staves. That is a TEMPLATE MATCHING, not a rule succeeding.
  - BRAHMS 1 is the hardest at 0.806 because its 14-staff lineup includes a
    Contrabassoon that no layout places at that position — an orchestration
    fact about 1876. It is the same residual §5 isolates.

The publisher HOLDOUT still stands, but for evidence availability rather than
instrumentation: a house decides how much the page tells you, so a rule fitted
where labels are rich can fail where they are sparse. That is the Simrock 45/45
vs Litolff 2/50 shape. The Litolff arm tests whether the rule secretly depends
on being told the answer — it is not a publisher effect on identity.

REFUSED HERE. (1) `LayoutFit.agreement` cannot serve as the identity record's
confidence: 70% of WRONG answers sit at 1.000 against 89% of right ones. It does
not separate, which is why confidence must be DERIVED from what pruning fired.
(2) Choosing the layout whose vocabulary contains the lineup is measured and
WORSE -- 0.873 -> 0.680. Brahms 1 prints 14 staves and only `late-romantic-large`
(20 parts) holds its lineup, so the aligner must skip 6 parts with no anchor
saying which; `classical-condensed` at 12-against-14 is a near-size match and
loses only the Contrabassoon. The near-size match is load-bearing.

CORRECTED IN FLIGHT: this probe scored a correct `Contrabass` as an error on 2
Litolff records because `lookup("Basso")` returns `Bass voice`, the lexicon's
first answer for an ambiguous alias. `omr-part-staff-join-2026-08/RESULTS.md`
records THE SAME BUG shipped in its own harness, undetected since written. See
`acceptable()`. Pooled SHIPPED precision 0.903 -> 0.914.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST          # noqa: E402
from tools.omr.score_layouts import LAYOUTS, fit_layouts  # noqa: E402

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
FIXTURE_CANDIDATES = [
    MAIN / ".claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures",
    REPO / "benchmarks/omr-scan-e2e-2026-09/fixtures",
    MAIN / "benchmarks/omr-scan-e2e-2026-09/fixtures",
]
WORKS_CANDIDATES = [
    MAIN / ".claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/works.json",
    REPO / "benchmarks/omr-scan-e2e-2026-09/works.json",
    MAIN / "benchmarks/omr-scan-e2e-2026-09/works.json",
]

# A clef is EVIDENCE only where a reader produced it. `slot_continuity` and
# `dossier` are written by the contextual pass THROUGH the join, so feeding
# them back in would close the loop this probe exists to open.
RAW_CLEF_SOURCES = {"detector", "detector_header", "specialist", "cv_locator"}

PUBLISHER = {
    "beethoven": "Litolff",
    "brahms": "Breitkopf",
    "dvorak": "Simrock",
    "mahler": "Peters",
    "bach": "Peters(Bach)",
}

# Two scans of one plate are ONE engraving, not a replication.
ENGRAVING = {
    "beethoven-sym5-mvt1-575951": "beethoven-litolff-plate",
    "beethoven-sym5-mvt1-984073": "beethoven-litolff-plate",
}


def _pick(cands, what):
    for c in cands:
        if c.exists():
            return c
    raise SystemExit(f"no {what} found; looked in {[str(c) for c in cands]}")


# ───────────────────────────────────────────────────────────── truth (KEY only)

def resolve_truth(row, by_id, _depth=0):
    """(list of staff dicts, provenance). Follows `same-as:` aliases."""
    if _depth > 4:
        return None, "alias-loop"
    st = row.get("staves")
    if isinstance(st, str) and st.startswith("same-as:"):
        got, prov = resolve_truth(by_id[st.split(":", 1)[1]], by_id, _depth + 1)
        return got, f"alias->{prov}"
    if isinstance(st, list):
        return st, "works.json:staves"
    cond = row.get("condensation") or {}
    sap = cond.get("staves_as_printed")
    if isinstance(sap, list):
        return sap, "condensation.staves_as_printed"
    return None, "NONE"


def canonical(name):
    """A printed label -> the lexicon's canonical instrument name, or None.

    Both sides of every comparison go through this, so `Corni I.II. in E` and
    the layout's `Horn` meet on one spelling. A name the lexicon cannot resolve
    is EXCLUDED from the denominator and counted, never scored as a miss --
    it is the scorer that failed there, not the arm.
    """
    if not name:
        return None
    m = INST.lookup(str(name))
    return m.instrument.name if m else None


def acceptable(name):
    """Every instrument a printed truth label could legitimately mean.

    ⚠️ `lookup` returns the lexicon's FIRST answer for an ambiguous alias, and
    for `Basso` that is `Bass voice` -- so scoring a correct `Contrabass`
    against it counts a right answer wrong. `omr-part-staff-join-2026-08`
    records having shipped exactly this bug in its own harness ("the harness
    had been counting a correct Contrabass as an error since it was written"),
    and this probe reproduced it on 2 Litolff records before it was fixed.
    Where the alias that fired is ambiguous, EVERY candidate is accepted.
    """
    if not name:
        return frozenset()
    m = INST.lookup(str(name))
    if not m:
        return frozenset()
    cands = INST.candidates_for_alias(m.alias)
    if cands:
        return frozenset(c.name for c in cands)
    return frozenset({m.instrument.name})


# ─────────────────────────────────────────────────────────────────── evidence

def systems_of(fx):
    """[(system_index, [staff dicts top-to-bottom])] over the whole result."""
    out = []
    for page in fx.get("pages", []):
        for sysd in page.get("systems", []):
            staves = list(sysd.get("staves", []))
            staves.sort(key=lambda s: (s.get("staff_geometry") or {}).get(
                "line_ys_page", [0])[0])
            out.append((page.get("page_index"), sysd.get("system_index"), staves))
    return out


def read_clefs(staves):
    """{ordinal: clef} for clefs a READER produced. Never a defaulted one."""
    got = {}
    for i, st in enumerate(staves):
        if st.get("clef_source") in RAW_CLEF_SOURCES and st.get("clef"):
            got[i] = st["clef"]
    return got


def shipped_instruments(staves):
    """{ordinal: instrument} as the pipeline wrote it. JOIN OUTPUT -- arm
    SHIPPED only. Never handed to a predicting arm."""
    return {i: st["instrument"] for i, st in enumerate(staves)
            if st.get("instrument")}


# ────────────────────────────────────────────────────────────────────── arms

def arm_fit(n, labels, clefs):
    fit = fit_layouts(n, labels=labels or None, clefs=clefs or None)
    if fit is None:
        return {}, None, {}
    named = {i: fit.assignment[i] for i in range(n) if fit.assignment[i]}
    agree = {i: fit.agreement[i] for i in range(n)}
    return named, fit.layout.name, agree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=os.getenv("IDENTITY_TAG", ".reconciliation"))
    ap.add_argument("--fixtures", default=None)
    ap.add_argument("--out", default=str(HERE / "heldout-identity.json"))
    ap.add_argument("--audit-inputs", action="store_true")
    args = ap.parse_args()

    fxdir = Path(args.fixtures) if args.fixtures else _pick(
        FIXTURE_CANDIDATES, "fixtures dir")
    works = json.loads(_pick(WORKS_CANDIDATES, "works.json").read_text())
    rows = works["rows"]
    by_id = {r["row_id"]: r for r in rows}

    paths = sorted(fxdir.glob(f"*{args.tag}.omr.json"))
    print(f"FIXTURES  {fxdir}")
    print(f"TAG       {args.tag!r}   rows on disk: {len(paths)}")
    if not paths:
        raise SystemExit(f"no fixtures matching *{args.tag}.omr.json in {fxdir}")

    records = []
    n_staves_seen = 0
    excluded_unresolvable = Counter()
    rows_without_truth = []

    for p in paths:
        rid = p.name[: -len(f"{args.tag}.omr.json")].rstrip(".")
        row = by_id.get(rid)
        fx = json.loads(p.read_text())
        syss = systems_of(fx)
        n_staves_seen += sum(len(s) for _, _, s in syss)
        if row is None:
            rows_without_truth.append((rid, "no works.json row"))
            continue
        truth, prov = resolve_truth(row, by_id)
        if not truth:
            rows_without_truth.append((rid, "no page truth"))
            continue

        work = rid.split("-sym")[0].split("-brandenburg")[0]
        pub = PUBLISHER.get(work, "?")
        edition = rid.rsplit("-p", 1)[0]
        engraving = ENGRAVING.get(edition, edition)

        for page_idx, sys_idx, staves in syss:
            n = len(staves)
            # The truth is a LINEUP (one row of instruments). It applies to a
            # system only when that system prints exactly that many staves --
            # a system with tacet staves suppressed is a different lineup and
            # pairing by position would name the wrong instrument. Abstain.
            if n != len(truth):
                rows_without_truth.append(
                    (f"{rid} sys{sys_idx}", f"n_staves {n} != truth {len(truth)}"))
                continue

            clefs = read_clefs(staves)
            truth_named = {i: canonical(t.get("name")) for i, t in enumerate(truth)}
            for i, t in enumerate(truth):
                if truth_named[i] is None:
                    excluded_unresolvable[str(t.get("name"))] += 1

            heldout, lay_h, ag_h = arm_fit(n, {}, clefs)
            floor, lay_f, ag_f = arm_fit(n, {}, {})
            ceil_labels = {i: v for i, v in truth_named.items() if v}
            ceiling, lay_c, ag_c = arm_fit(n, ceil_labels, clefs)
            shipped = shipped_instruments(staves)

            # ── ORACLE-LAYOUT arm (a CEILING, never a result) ───────────────
            # Restrict the layout pool to those whose part vocabulary CONTAINS
            # this lineup, then run the identical held-out fit. It answers one
            # question and no other: how much of the held-out error is the
            # prior committing to the wrong template, as against weak per-staff
            # evidence. It reads the truth to choose the pool, so it can never
            # be quoted as an accuracy.
            lineup = {v for v in truth_named.values() if v}
            pool = tuple(l for l in LAYOUTS if lineup <= set(l.parts))
            if pool:
                fit_o = fit_layouts(n, labels=None, clefs=clefs or None,
                                    layouts=pool)
                oracle = ({i: fit_o.assignment[i] for i in range(n)
                           if fit_o.assignment[i]} if fit_o else {})
                lay_o = fit_o.layout.name if fit_o else None
            else:
                oracle, lay_o = {}, None

            for i in range(n):
                records.append({
                    "ORACLE_LAYOUT": oracle.get(i),
                    "oracle_layout_name": lay_o,
                    "layout_pool_size": len(pool),
                    "row_id": rid, "publisher": pub, "engraving": engraving,
                    "page_index": page_idx, "system_index": sys_idx,
                    "ordinal": i, "n_staves": n,
                    "TRUTH": truth_named[i],
                    "TRUTH_acceptable": sorted(acceptable(truth[i].get("name"))),
                    "TRUTH_printed": truth[i].get("name"),
                    "truth_provenance": prov,
                    "clef_read": clefs.get(i),
                    "SHIPPED": shipped.get(i),
                    "HELDOUT": heldout.get(i), "heldout_layout": lay_h,
                    "heldout_agreement": ag_h.get(i),
                    "FLOOR": floor.get(i), "floor_layout": lay_f,
                    "CEILING": ceiling.get(i), "ceiling_layout": lay_c,
                })

    # ── assert we looked at something ───────────────────────────────────────
    print(f"\nINPUT AUDIT")
    print(f"  staves in fixtures            {n_staves_seen}")
    print(f"  scoreable staff records       {len(records)}")
    print(f"  clefs actually READ           "
          f"{sum(1 for r in records if r['clef_read'])}")
    print(f"  truth names the lexicon could not resolve "
          f"{sum(excluded_unresolvable.values())} "
          f"({len(excluded_unresolvable)} distinct)")
    for name, c in excluded_unresolvable.most_common():
        print(f"      {c:3d}  {name!r}")
    if rows_without_truth:
        print(f"  ABSTAINED (no comparable truth):")
        for what, why in rows_without_truth:
            print(f"      {what:34s} {why}")
    if not records:
        raise SystemExit("REFUSING to report: zero scoreable records.")

    def score(recs, arm):
        """coverage = arm named it; precision = named AND right, over named.

        `right` accepts any member of TRUTH_acceptable -- see `acceptable()`.
        """
        scoreable = [r for r in recs if r["TRUTH"]]
        named = [r for r in scoreable if r[arm]]
        right = [r for r in named if r[arm] in r["TRUTH_acceptable"]]
        return (len(scoreable), len(named),
                len(named) / len(scoreable) if scoreable else 0.0,
                len(right), len(right) / len(named) if named else 0.0)

    arms = ["SHIPPED", "HELDOUT", "ORACLE_LAYOUT", "FLOOR", "CEILING"]

    def table(title, recs):
        print(f"\n{title}   (n scoreable = "
              f"{len([r for r in recs if r['TRUTH']])})")
        print(f"  {'arm':9s} {'spoke':>6s} {'coverage':>9s} {'right':>6s} "
              f"{'precision':>10s}")
        for a in arms:
            tot, spoke, cov, right, prec = score(recs, a)
            print(f"  {a:9s} {spoke:6d} {cov:9.3f} {right:6d} {prec:10.3f}")

    table("POOLED — 20-row scan gate", records)

    by_pub = defaultdict(list)
    for r in records:
        by_pub[r["publisher"]].append(r)
    for pub in sorted(by_pub):
        table(f"PUBLISHER {pub}", by_pub[pub])

    by_eng = defaultdict(list)
    for r in records:
        by_eng[r["engraving"]].append(r)
    print("\nENGRAVINGS represented (two scans of one plate = ONE engraving):")
    for e in sorted(by_eng):
        print(f"  {e:34s} {len(by_eng[e]):4d} staff records")

    # Where does HELDOUT lose to SHIPPED, and on what?
    print("\nHELDOUT errors by truth family (scoreable & named & wrong):")
    fam = Counter()
    for r in records:
        if r["TRUTH"] and r["HELDOUT"] and r["HELDOUT"] != r["TRUTH"]:
            m = INST.lookup(r["TRUTH"])
            fam[(m.instrument.family if m else "?", r["TRUTH"], r["HELDOUT"])] += 1
    for (f, t, g), c in fam.most_common(20):
        print(f"  {c:3d}  {f:10s} truth {t:14s} -> said {g}")

    out = Path(args.out)
    out.write_text(json.dumps({
        "meta": {
            "fixtures": str(fxdir), "tag": args.tag,
            "n_fixture_rows": len(paths),
            "n_staves_in_fixtures": n_staves_seen,
            "n_scoreable_records": len(records),
            "unresolvable_truth_names": dict(excluded_unresolvable),
            "abstained": rows_without_truth,
        },
        "records": records,
    }, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
