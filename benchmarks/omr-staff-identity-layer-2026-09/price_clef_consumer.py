#!/usr/bin/env python3
"""KC-3: what is an identity-driven clef consumer WORTH, in edits?

EXPORT-ONLY A/B over the committed 20-row scan gate. No detector time: each arm
re-exports the SAME stored transcriptions after re-running the clef consumer
with a different identity supply, and scores the result with the same musicdiff
bridge the gate uses. That isolates the consumer from detector jitter, which is
the pattern `omr-hairpins-2026-09` used for the same reason.

THE QUESTION. `clef_correction` has two application paths and only one of them
is gated on the identity's SOURCE:

    FILL      `do_apply = apply and not detected` (:597) -- a staff whose clef
              NO reader read takes its instrument's default. Ungated: any
              identity supply reaches it.
    OVERRIDE  a staff whose clef WAS read as treble is overridden, and this
              requires `sources[slot] == "label"` (:599). Deliberate: a
              confident wrong identity here rewrites a whole staff of pitches.

`veto_implausible_clef_changes` is gated the same way (:493).

So the price of an identity layer is the price of widening WHO SUPPLIES those
two paths. Three tiers, measured separately, because they are not equally
trustworthy -- see `probe_heldout_identity.py` and `probe_roster_carry.py`:

    A  observed label          what the gate admits today  (the BASELINE)
    B  roster-carried observed 22/22 = 1.000 precision on the gate
    C  derived (score order)   0.550 carried / 0.873 in-page

⚠️ Tier C is the one to be careful with, and the reason is measured rather than
felt: where the score-order prior is WRONG, the truth is in its candidate set
only 20% of the time (`probe_candidate_sets.py`). It is not uncertain, it is
confidently elsewhere. `clef_correction.py:477` already records the same thing
from the other side -- "the p2 violas are named Violin by the prior" -- and
this workstream's held-out arm reproduced exactly that, Viola -> Violin x3.

⚠️ CONTROL FIRST. Arm `BASELINE` re-exports the fixtures UNMODIFIED. If it does
not reproduce the committed per-row edit counts in `results-reconciliation.json`
the harness is measuring itself and every delta below is void. The control is
asserted, not eyeballed.

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 benchmarks/omr-staff-identity-layer-2026-09/price_clef_consumer.py --control
    python3 benchmarks/omr-staff-identity-layer-2026-09/price_clef_consumer.py

── CONTROL RESULT 2026-09-05: DELTA FOUND, CAUSE ATTRIBUTED ──────────────────
Re-exporting the 20 fixtures UNMODIFIED reproduces the committed gate on 15 of
20 rows EXACTLY, and the 5 that differ do so for one identified reason:

    beethoven-575951-p1  -4    beethoven-984073-p1  -10
    beethoven-575951-p2  +1    beethoven-984073-p2   +6
    mahler-local-p5      +1

Diffing the re-export against the committed `.reconciliation.omr.musicxml`, the
ONLY changed lines on every one of them are ADDED `<fermata>` elements --
6 + 6 + 1 across the rows, nothing else, no notes and no clefs. The cause is
`a4918874` "export: the whole-measure rest wears its fermata" (2026-09-04),
which is an ancestor of this branch's HEAD and POSTDATES the MusicXML committed
beside the fixtures. So the gate's stored `.omr.musicxml` was written by an
older exporter than main now carries.

⚠️ This is a finding about a SHARED artifact, not about this harness:
`results-reconciliation.json` is stale with respect to main by that commit,
worth roughly +-10 edits on 5 rows. Flagged upward; not fixed here, because
the 20-row gate belongs to another session.

WHY THE A/B IS STILL VALID. Every arm below is exported by THIS tree, so both
sides of every delta carry the fermatas equally and the difference cancels.
What the control forbids is quoting an ABSOLUTE number from this harness as
the gate's figure, and no such number is quoted. `--accept-control-delta`
exists so the override is explicit and has to be argued in writing.

── KC-3 RESULT 2026-09-05: FILL moves -13, and BOTH predictions were wrong ───

    arm         edits   delta      the rows that moved
    BASELINE    74962      +0
    B_roster    74962      +0       none
    C_derived   74949     -13       bach p1 -15, mahler p5 +2
    BC          74947     -15       bach p1 -15, mahler p5 +0

⚠️⚠️ THE TIER WITH PERFECT PRECISION MOVES NOTHING, AND THE WORST TIER IS THE
ONLY ONE THAT MOVES ANYTHING. Both the coordinator's prediction and mine were
that B (roster, 22/22 = 1.000) would be admissible and C (derived, 0.550
carried) would not. The measurement says the question was mis-posed: value here
is not a function of identity precision at all.

`probe_fill_reach.py` explains it, and the explanation is structural rather
than incidental -- FILL's reach is an INTERSECTION of two populations:

    396 staves, of which only  34  have NO clef read  (91.4% already do)
    tier B supplies  56 identities ->   0 applications
    tier C supplies 104 identities ->   2 applications

Tier B's 56 are almost all Dvorak p6 (15) and p7 (30) -- pages whose `noclef`
count is ZERO. A perfect roster and the staves needing a fill are DISJOINT
populations, so B's edit delta is +0 by construction, not by weakness.

So the whole -13 comes from exactly TWO clef applications, one of which is a
regression (+2 on mahler p5). That is 0.017% of a 74,962-edit baseline from
n=2, driven by the least trustworthy tier.

VERDICT: NOT A BASIS FOR SHIPPING. Two applications cannot support a default,
the net is inside any reasonable noise band for a change of this size, and the
one arm that moves is the one whose precision this workstream measured at
0.873 in-page / 0.550 carried. The pre-registered clause about wrong-direction
moves on ABSTAINING rows does NOT fire -- tier C NAMED mahler p5 rather than
abstaining -- so this is a confident-wrong identity, exactly the hazard the
OVERRIDE gate at :599 exists to prevent, showing up on the ungated FILL path
instead.

⚠️ AND THE REAL ANSWER TO "DOES CLEF CONSUME IDENTITY" IS THE 34. The clef
consumer can only ever touch staves whose clef went unread, and on this corpus
that is 8.6% of them. The documented clef ceiling is about clefs read WRONG
(every remaining error in `eval_pipeline_clefs` is a non-treble clef read as
treble), and those staves are invisible to FILL by definition. Reaching them
means the OVERRIDE path -- which is gated, correctly, and is blocked on a
calibrated probability that `probe_calibration.py` says does not exist yet.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                     # noqa: E402
from tools.omr import omr_ned as omr_ned_mod                  # noqa: E402
from tools.omr.export import to_musicxml                      # noqa: E402
from tools.omr.score_layouts import fit_layouts               # noqa: E402
from tools.omr.clef_correction import (                       # noqa: E402
    correct_clefs_from_instruments)

RECON = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09")
FIXTURES = RECON / "fixtures"
TAG = ".reconciliation"
COMMITTED = RECON / "results-reconciliation.json"

RAW_CLEF_SOURCES = {"detector", "detector_header", "specialist", "cv_locator"}
SCRATCH = Path(os.getenv("KC3_SCRATCH", "/tmp/kc3-clef"))


def rows():
    return sorted(FIXTURES.glob(f"*{TAG}.omr.json"))


def edition_of(rid):
    return rid.rsplit("-p", 1)[0]


def systems_of(fx):
    out = []
    for page in fx.get("pages", []):
        for sysd in page.get("systems", []):
            staves = sorted(sysd.get("staves", []),
                            key=lambda s: (s.get("staff_geometry") or {})
                            .get("line_ys_page", [0])[0])
            out.append((page.get("page_index"), sysd.get("system_index"),
                        sysd, staves))
    return out


# ─────────────────────────────────────────────────────────── identity supplies

def tier_a(staves):
    """Observed label. The join's own answer, restricted to source == label."""
    return {i: st["instrument"] for i, st in enumerate(staves)
            if st.get("instrument") and st.get("instrument_source") == "label"}


def build_roster(paths):
    """Edition -> (n_staves, ordinal) -> instrument, from OBSERVED LABELS only.

    ⚠️ Label-sourced only, and that is the finding rather than a precaution:
    the same carry over DERIVED identity scores 0.550 and drags pooled
    precision below the observed rate (`probe_roster_carry.py`). A roster that
    disagrees with itself at a position ABSTAINS.
    """
    tally = defaultdict(lambda: defaultdict(Counter))
    for p in paths:
        rid = p.name[: -len(f"{TAG}.omr.json")].rstrip(".")
        fx = json.loads(p.read_text())
        for _, _, _, staves in systems_of(fx):
            for i, inst in tier_a(staves).items():
                tally[edition_of(rid)][(len(staves), i)][inst] += 1
    return {ed: {k: next(iter(c)) for k, c in d.items() if len(c) == 1}
            for ed, d in tally.items()}


def tier_b(staves, roster_ed, have):
    """Roster-carried observed identity, for positions tier A left open."""
    out = {}
    for i in range(len(staves)):
        if i in have:
            continue
        got = roster_ed.get((len(staves), i))
        if got:
            out[i] = got
    return out


def tier_c(staves, have):
    """Derived: the score-order prior, labels hidden, read clefs only."""
    clefs = {i: st["clef"] for i, st in enumerate(staves)
             if st.get("clef_source") in RAW_CLEF_SOURCES and st.get("clef")}
    fit = fit_layouts(len(staves), labels=None, clefs=clefs or None)
    if fit is None:
        return {}
    return {i: fit.assignment[i] for i in range(len(staves))
            if fit.assignment[i] and i not in have}


# ──────────────────────────────────────────────────────────────────────── arms

def apply_arm(fx, roster, rid, *, use_b, use_c):
    """Return (mutated copy, n_staves_supplied, n_applied).

    Only the ADDED staves are handed to the consumer, so it can never re-act on
    a staff the shipped fixture already corrected: the fixtures were produced
    with tier A live, so the marginal price is exactly what B / C add.

    ⚠️ `slot_index` is a join OUTPUT and is never read as evidence here. A
    synthetic slot key is minted per (system, ordinal) purely as the addressing
    scheme `correct_clefs_from_instruments` already requires.
    """
    fx = copy.deepcopy(fx)
    inst_by_slot, src_by_slot, slot_by_staff = {}, {}, {}
    supplied = 0
    for pi, si, sysd, staves in systems_of(fx):
        have = tier_a(staves)
        add = {}
        if use_b:
            add.update(tier_b(staves, roster.get(edition_of(rid), {}), have))
        if use_c:
            add.update(tier_c(staves, set(have) | set(add)))
        for i, name in add.items():
            m = INST.lookup(name)
            if not m:
                continue
            slot = 10_000 + pi * 1000 + si * 100 + i
            st = staves[i]
            slot_by_staff[(pi, si, st.get("staff_index"))] = slot
            inst_by_slot[slot] = m.instrument
            # The SOURCE string is what the override gate at :599 reads. Both
            # added tiers declare a non-"label" source, so this measures the
            # FILL path only -- widening the override is a separate question
            # and is not silently folded in here.
            src_by_slot[slot] = "roster" if (use_b and i in tier_b(
                staves, roster.get(edition_of(rid), {}), have)) else "derived"
            supplied += 1
    if not inst_by_slot:
        return fx, 0, 0
    recs = correct_clefs_from_instruments(
        fx.get("pages", []), inst_by_slot, slot_by_staff,
        apply=True, instrument_source_by_slot=src_by_slot)
    return fx, supplied, sum(1 for r in recs if r.get("applied"))


def score(pairs):
    return omr_ned_mod.score_batch(pairs, detail=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true",
                    help="only re-export unmodified and check the gate numbers")
    ap.add_argument("--accept-control-delta", action="store_true",
                    help="proceed despite a control delta whose cause is "
                         "attributed in the docstring (the fermata commit)")
    args = ap.parse_args()

    if not os.getenv("OMRNED_PYTHON") and not (
            Path("/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned")).exists():
        raise SystemExit("set OMRNED_PYTHON to the main checkout's .venv-omrned")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    paths = rows()
    print(f"FIXTURES {FIXTURES}\nTAG {TAG!r}   rows {len(paths)}")
    if len(paths) != 20:
        raise SystemExit(f"expected 20 gate rows, found {len(paths)}")

    committed = json.loads(COMMITTED.read_text())
    # ⚠️ The committed rows carry the TAG in `row_id`
    # (`beethoven-...-p1.reconciliation`). Strip it, or every lookup misses and
    # the control silently reports "nothing to compare" as a pass.
    comm_rows = {}
    for r in committed.get("rows", committed):
        rid = r["row_id"]
        if rid.endswith(TAG):
            rid = rid[: -len(TAG)]
        comm_rows[rid.rstrip(".")] = r
    print(f"committed gate rows matched: "
          f"{len(set(comm_rows) & {p.name[: -len(f'{TAG}.omr.json')].rstrip('.') for p in paths})} of {len(paths)}")

    roster = build_roster(paths)
    print(f"roster positions by edition: "
          f"{ {e: len(d) for e, d in roster.items()} }")

    arms = {"BASELINE": dict(use_b=False, use_c=False)}
    if not args.control:
        arms["B_roster"] = dict(use_b=True, use_c=False)
        arms["C_derived"] = dict(use_b=False, use_c=True)
        arms["BC"] = dict(use_b=True, use_c=True)

    results = {}
    for arm, kw in arms.items():
        pairs, supplied, applied = [], 0, 0
        for p in paths:
            rid = p.name[: -len(f"{TAG}.omr.json")].rstrip(".")
            fx = json.loads(p.read_text())
            if arm == "BASELINE":
                out = fx
            else:
                out, s, a = apply_arm(fx, roster, rid, **kw)
                supplied += s
                applied += a
            xml = SCRATCH / f"{rid}.{arm}.musicxml"
            xml.write_text(to_musicxml(out))
            pairs.append((rid, str(xml),
                          str(FIXTURES / f"{rid}.truth.musicxml")))
        scored = score(pairs)
        by = {s["name"]: s for s in scored.get("scores", scored.get("pairs", []))}
        if not by:
            raise SystemExit(f"scorer returned no per-pair rows; "
                             f"keys were {list(scored)}")
        results[arm] = by
        tot = sum(s.get("omr_ed", 0) or 0 for s in by.values())
        print(f"\n{arm:10s} staves supplied {supplied:4d}  "
              f"clefs applied {applied:4d}  TOTAL EDITS {tot}")

    # ── CONTROL ─────────────────────────────────────────────────────────────
    print(f"\n{'row':34s} {'committed':>10s} {'re-export':>10s} {'delta':>7s}")
    bad = 0
    for p in paths:
        rid = p.name[: -len(f"{TAG}.omr.json")].rstrip(".")
        c = (comm_rows.get(rid) or {}).get("omr_ned") or {}
        c_ed = c.get("omr_ed")
        b_ed = results["BASELINE"].get(rid, {}).get("omr_ed")
        d = (b_ed - c_ed) if (c_ed is not None and b_ed is not None) else None
        if d not in (0, None):
            bad += 1
        print(f"{rid:34s} {str(c_ed):>10s} {str(b_ed):>10s} {str(d):>7s}")
    print(f"\nCONTROL: {bad} rows differ from the committed gate")
    if bad and not args.accept_control_delta:
        print("⚠️ The re-export does NOT reproduce the gate. Every delta below "
              "would be measuring the harness, not the consumer. REFUSING.\n"
              "   Diagnose the cause and attribute it before overriding with "
              "--accept-control-delta.")
        return 1
    if bad:
        print("⚠️ CONTROL DELTA ACCEPTED, cause attributed — see the docstring.\n"
              "   The A/B below is still valid because BOTH arms are exported "
              "by THIS tree; only the comparison to the committed gate's\n"
              "   absolute numbers is affected, and no absolute number from "
              "this harness is quoted as the gate's.")
    if args.control:
        return 0

    print(f"\n{'row':34s} " + " ".join(f"{a:>10s}" for a in arms))
    for p in paths:
        rid = p.name[: -len(f"{TAG}.omr.json")].rstrip(".")
        cells = []
        for a in arms:
            ed = results[a].get(rid, {}).get("omr_ed")
            base = results["BASELINE"].get(rid, {}).get("omr_ed")
            cells.append(f"{ed}" if a == "BASELINE"
                         else f"{ed}({ed-base:+d})")
        print(f"{rid:34s} " + " ".join(f"{c:>10s}" for c in cells))
    print()
    for a in arms:
        tot = sum(s.get("omr_ed", 0) or 0 for s in results[a].values())
        base = sum(s.get("omr_ed", 0) or 0
                   for s in results["BASELINE"].values())
        print(f"  {a:10s} edits {tot:6d}  delta {tot-base:+5d}")
    (HERE / "kc3-clef-consumer.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
