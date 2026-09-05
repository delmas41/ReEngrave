#!/usr/bin/env python3
"""H3 — inter-staff GAP FINGERPRINTS and REGISTER CONTINUITY as pairwise MATCH features.

MEASUREMENT ONLY. **No pipeline code is modified.** `tools/omr/slots.py` is
imported and called; `slots.build_reference`, `slots.align` and `slots._pair_score`
run exactly as shipped. The augmented arms wrap `_pair_score` in a
benchmark-local closure that ADDS a feature term; nothing under `tools/` or
`backend/` is touched. Fixture loading, re-detection assertions, vendored
labels, the truth construction and the PARTNER METRIC are imported from
`probe_union_roster.py` so this number is comparable to H1′'s by construction.

────────────────────────────────────────────────────────────────────────────
PRE-REGISTERED TARGET (written before the first run; verbatim from the brief)

  (1) a new `_pair_score` term must be worth **more than 1.5** where
      `beethoven-…-p4` needs it, AND
  (2) **`brahms-…-p3` must stay 28/28** (its insert margin is also 1.5), AND
  (3) the p.4 union must be reached by the **CORRECT ROUTE** — gap Timpani,
      append Basso — not merely at the correct SIZE. Arm C of H1′ hit a 12-slot
      roster by inserting at index 6 and scored only 15/22. ROSTER SIZE ALONE
      WOULD HAVE DECLARED SUCCESS. The continuity column is reported beside
      every roster-size claim; a shape check is necessary and not sufficient.

THE CENTRAL DESIGN CONSTRAINT. The features earn their place by being
independent of BOTH labels AND `group_index`. Labels are silent on the four
string staves that would settle p.4; `group_index` disagrees between the two
systems of `brahms-…-p3` from DETECTION NOISE of the same magnitude as p.4's
real lineup change. **Measuring the correlation with `group_index` is part of
this experiment, not a postscript** — reported per feature, per row.
────────────────────────────────────────────────────────────────────────────

## The two features

1. **Gap fingerprint** — pure geometry, no detector, no OCR. For each staff, the
   vertical gap to the staff above and below, in units of that system's own
   median staff-line spacing, then divided by the system's own median gap. The
   second normalisation is DECLARED IN ADVANCE and is not free: system 0 of
   `beethoven-…-984073-p4` is set with visibly wider gaps throughout than
   system 1 (its Corni gap is 7.37 staff spaces against 4.13 for the same true
   pair), so raw gaps are not comparable between systems of one page.
   ⚠️ Disclosed: the gap vectors of `…-984073-p4` and `brahms-…-p3` WERE
   inspected before that normalisation was fixed. See MATCH_FEATURES.md.

2. **Register continuity** — the median pitch of a staff's pitched noteheads,
   from the committed fixture transcriptions.
   ⚠️ `n_noteheads_detected` is recorded beside every register figure and
   zero-detection staves are their own stratum. Per the retracted alarm in
   `docs/staff-identity-audit-plan-2026-09-04.md`, "this staff has no
   noteheads" is NOT treated as evidence of rest and NOT treated as an
   abstention-worthy defect: five Dvořák p5 staves called resting were
   genuinely resting. A pair where either side has no pitched notehead simply
   contributes 0 — the feature abstains for that pair and the abstention is
   COUNTED.

## Inputs and provenance

* **Fixtures** — the 20-row gate, READ-ONLY, from the reconciliation worktree,
  suffix `.reconciliation.omr.json` (the main checkout's `fixtures/` is the
  stale 11-row `..graft09` set). `staff_geometry.line_ys_page` and
  `line_spacing_px` are present on all 396 staves and are the gap substrate;
  notehead detections with a `pitch` are the register substrate.
* **`group_index`** — NOT in the fixtures, so it comes from
  `probe_union_roster.py`'s cached structure-only re-detection
  (`render_page` + `detect_staves`, no YOLO, no OCR). Used ONLY by the shipped
  `_pair_score` and by the correlation test.
* **Labels** — `vendored-labels/classified.json`, as in H1′.
* **`works.json`** — SCORING ONLY, never an input. Dossiers barred entirely.

    python3 benchmarks/omr-structure-rnd-2026-09/probe_match_features.py
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import probe_union_roster as UR          # noqa: E402  (fixture + truth + metric)

FIXTURES = UR.FIXTURES
SUFFIX = UR.SUFFIX
OUT = HERE / "match-features.json"


# ═══════════════════════════════════════════════════════════════════════════
# feature extraction — from the committed fixtures
# ═══════════════════════════════════════════════════════════════════════════
def fixture_features(rid: str):
    """`[[staff-feature dict]]` per system, ordered top-to-bottom on the page."""
    path = FIXTURES / f"{rid}{SUFFIX}"
    assert path.exists(), f"EMPTY INPUT — no fixture at {path}"
    doc = json.loads(path.read_text())
    systems = []
    for pg in doc.get("pages", []):
        for sysrec in pg.get("systems", []):
            staves = sysrec.get("staves") or []
            if not staves:
                continue
            rows = []
            for st in staves:
                g = st["staff_geometry"]
                heads = [d for m in st["measures"] for d in m["detections"]
                         if d.get("category") == "notehead"]
                pitched = [d["pitch"] for d in heads if d.get("pitch")]
                rows.append({
                    "staff_index": st["staff_index"],
                    "top_y": g["line_ys_page"][0],
                    "bottom_y": g["line_ys_page"][-1],
                    "line_spacing_px": g["line_spacing_px"],
                    "n_noteheads_detected": len(heads),
                    "n_noteheads_pitched": len(pitched),
                    "median_midi": (statistics.median(_midi(p) for p in pitched)
                                    if pitched else None),
                })
            rows.sort(key=lambda r: r["top_y"])
            systems.append(rows)
    assert systems, f"no systems in fixture {rid}"
    return systems


_STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _midi(pitch: str) -> int:
    """`'Bb4'`/`'C#3'`/`'C4'` -> MIDI. A real parser over the pitch grammar, not
    a regex over a structured format: step letter, then any run of accidental
    characters, then a signed octave."""
    s = str(pitch)
    assert s and s[0].upper() in _STEP, f"unparseable pitch {pitch!r}"
    semis = _STEP[s[0].upper()]
    i = 1
    while i < len(s) and s[i] in "b#-+♭♯":
        # '-' is ambiguous (flat, or a negative octave). It only ever means flat
        # when a digit follows it later in the string, which the loop enforces.
        if s[i] == "-" and s[i + 1:].lstrip("-").isdigit() and i == len(s) - 2:
            break
        semis += 1 if s[i] in "#+♯" else -1
        i += 1
    octave = int(s[i:])
    return semis + 12 * (octave + 1)


def gap_vectors(system_rows):
    """`(above, below)` per staff, in units of the system's median gap.

    Two normalisations, both declared before the run:
      * gaps are first expressed in STAFF SPACES (divided by the system's median
        `line_spacing_px`), which makes editions comparable;
      * then divided by the system's own MEDIAN GAP, because the two systems of
        one page are not set to the same vertical density.
    """
    n = len(system_rows)
    if n < 2:
        return [None] * n, [None] * n
    spacing = statistics.median(r["line_spacing_px"] for r in system_rows)
    assert spacing > 0, "zero staff-line spacing"
    raw = [(system_rows[i]["top_y"] - system_rows[i - 1]["bottom_y"]) / spacing
           for i in range(1, n)]
    med = statistics.median(raw)
    assert med > 0, "non-positive median inter-staff gap"
    norm = [g / med for g in raw]
    above = [None] + norm
    below = norm + [None]
    return above, below


def pair_distance_gap(a1, b1, i, a2, b2, j):
    """Mean absolute difference over the gap components DEFINED ON BOTH SIDES.

    Returns `None` when no component is shared — an edge staff against an
    interior one shares one component; the two first staves share `below` only.
    `None` is an abstention and is counted, never imputed as agreement.
    """
    parts = []
    if a1[i] is not None and a2[j] is not None:
        parts.append(abs(a1[i] - a2[j]))
    if b1[i] is not None and b2[j] is not None:
        parts.append(abs(b1[i] - b2[j]))
    return (sum(parts) / len(parts)) if parts else None


def pair_distance_register(r1, r2):
    """Absolute median-pitch difference in SEMITONES, or `None` where either
    staff has no pitched notehead. The zero-detection stratum, not a defect."""
    if r1["median_midi"] is None or r2["median_midi"] is None:
        return None
    return abs(r1["median_midi"] - r2["median_midi"])


# ═══════════════════════════════════════════════════════════════════════════
# alignments
# ═══════════════════════════════════════════════════════════════════════════
def align_on_distance(n1, n2, dist, skip_cost):
    """Monotone alignment minimising total distance, skips priced `skip_cost`.

    `dist(i, j)` may return `None` (the feature abstains); an abstaining pair is
    scored at `skip_cost` so that abstention is never cheaper OR dearer than a
    skip — the feature says nothing and the path is decided by its neighbours.
    """
    INF = float("inf")
    dp = [[INF] * (n2 + 1) for _ in range(n1 + 1)]
    back = [[None] * (n2 + 1) for _ in range(n1 + 1)]
    dp[0][0] = 0.0
    for i in range(1, n1 + 1):
        dp[i][0], back[i][0] = dp[i - 1][0] + skip_cost, "skip1"
    for j in range(1, n2 + 1):
        dp[0][j], back[0][j] = dp[0][j - 1] + skip_cost, "skip2"
    for i in range(1, n1 + 1):
        for j in range(1, n2 + 1):
            d = dist(i - 1, j - 1)
            take = dp[i - 1][j - 1] + (skip_cost if d is None else d)
            s1 = dp[i - 1][j] + skip_cost
            s2 = dp[i][j - 1] + skip_cost
            best, mv = take, "take"
            if s1 < best:
                best, mv = s1, "skip1"
            if s2 < best:
                best, mv = s2, "skip2"
            dp[i][j], back[i][j] = best, mv
    pairs, i, j = [], n1, n2
    while i > 0 or j > 0:
        mv = back[i][j]
        if mv == "take":
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif mv == "skip1":
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs, dp[n1][n2]


def truth_pairs(m1):
    """The UNAMBIGUOUS half of the truth correspondence: positions of system 1
    whose acceptable partner set is a singleton. Condensed positions (Beethoven
    p.4's `Bassi`, acceptable against either `Violoncello` or `Basso`) are
    excluded from the distance sums and COUNTED separately."""
    return sorted((i, next(iter(v))) for i, v in m1.items() if len(v) == 1)


def diagonal_pairs(n1, n2):
    return [(i, i) for i in range(min(n1, n2))]


def score_pairs(pairs, n1, n2, m0, m1_):
    """The H1' PARTNER METRIC, applied to a raw pairing rather than to a roster.

    Each matched pair makes the two staves partners; every unmatched staff
    predicts `None`. Scored by `probe_union_roster.score_arm` so the number is
    the same object H1' reports — correct / decisions, each correspondence
    counted twice.
    """
    assign, nxt = {}, 0
    mate1 = dict(pairs)
    mate2 = {j: i for i, j in pairs}
    for i in range(n1):
        assign[(0, i)] = nxt
        nxt += 1
    for j in range(n2):
        assign[(1, j)] = (assign[(0, mate2[j])] if j in mate2 else nxt)
        if j not in mate2:
            nxt += 1
    n, ok, _ = UR.score_arm(assign, m0, m1_)
    return ok, n


def partner_ceiling(n1, n2, m0, m1_):
    """The BEST partner score any monotone one-to-one alignment can reach.

    ⚠️ It is not always the full denominator, and this is a real artifact of my
    own method rather than a property of the aligner: on Beethoven p.4 TWO
    system-1 staves (Violoncello, Basso) are each acceptable only against the
    single condensed `Bassi` staff of system 2, and a one-to-one alignment can
    give `Bassi` to only one of them. The other necessarily predicts `None`
    against a non-empty acceptable set and is charged. Reported so no arm is
    read against a target it cannot reach.
    """
    def sc(i, j):
        return int(j in m0[i]) + int(i in m1_[j])

    NEG = float("-inf")
    dp = [[NEG] * (n2 + 1) for _ in range(n1 + 1)]
    dp[0][0] = 0
    for i in range(1, n1 + 1):
        dp[i][0] = dp[i - 1][0] + int(not m0[i - 1])
    for j in range(1, n2 + 1):
        dp[0][j] = dp[0][j - 1] + int(not m1_[j - 1])
    for i in range(1, n1 + 1):
        for j in range(1, n2 + 1):
            dp[i][j] = max(dp[i - 1][j - 1] + sc(i - 1, j - 1),
                           dp[i - 1][j] + int(not m0[i - 1]),
                           dp[i][j - 1] + int(not m1_[j - 1]))
    return dp[n1][n2]


def best_truth_alignment(n1, n2, m0, m1_):
    """A monotone one-to-one alignment attaining `partner_ceiling` — the best a
    roster-driven aligner could possibly do on this row. Used as "the path the
    union would take", against which the diagonal is priced."""
    def sc(i, j):
        return int(j in m0[i]) + int(i in m1_[j])

    dp = [[0] * (n2 + 1) for _ in range(n1 + 1)]
    back = [[None] * (n2 + 1) for _ in range(n1 + 1)]
    for i in range(1, n1 + 1):
        dp[i][0], back[i][0] = dp[i - 1][0] + int(not m0[i - 1]), "skip1"
    for j in range(1, n2 + 1):
        dp[0][j], back[0][j] = dp[0][j - 1] + int(not m1_[j - 1]), "skip2"
    for i in range(1, n1 + 1):
        for j in range(1, n2 + 1):
            opts = [(dp[i - 1][j - 1] + sc(i - 1, j - 1), "take"),
                    (dp[i - 1][j] + int(not m0[i - 1]), "skip1"),
                    (dp[i][j - 1] + int(not m1_[j - 1]), "skip2")]
            dp[i][j], back[i][j] = max(opts, key=lambda t: t[0])
    pairs, i, j = [], n1, n2
    while i > 0 or j > 0:
        mv = back[i][j]
        if mv == "take":
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif mv == "skip1":
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


def feature_margin(diag, truth_align, dist):
    """`Σ_diagonal d − Σ_truth d`, the coefficient of the weight.

    Adding `-W * d` to `_pair_score` changes (truth path − diagonal path) by
    exactly `W * this`, because the feature term touches only MATCHED pairs and
    the base score already prices gaps and inserts. So:

      * `<= 0` — NO positive weight can move this row toward the truth. The
        feature votes for the wrong answer and the question of "how much is it
        worth" does not arise.
      * `> 0`  — the weight needed to clear H1′'s measured 1.5 deficit is
        `1.5 / margin`, and that same weight must then be shown not to break
        `brahms-…-p3`.
    """
    sd = sum(d for i, j in diag if (d := dist(i, j)) is not None)
    st = sum(d for i, j in truth_align if (d := dist(i, j)) is not None)
    margin = sd - st
    return {"sum_distance_diagonal": round(sd, 6),
            "sum_distance_truth_path": round(st, 6),
            "margin_per_unit_weight": round(margin, 6),
            "weight_needed_for_1_5": (None if margin <= 0 else round(1.5 / margin, 4)),
            "any_positive_weight_can_help": margin > 0}


def mean_distance(pairs, dist):
    vals = [d for i, j in pairs if (d := dist(i, j)) is not None]
    n_abstain = len(pairs) - len(vals)
    return ((sum(vals) / len(vals)) if vals else None), len(vals), n_abstain


# ═══════════════════════════════════════════════════════════════════════════
# group_index correlation — part of the experiment, not a postscript
# ═══════════════════════════════════════════════════════════════════════════
def group_auc(n1, n2, dist, g1, g2):
    """AUC of `-distance` as a classifier of `group_index agreement` over ALL
    cross-system pairs. 0.5 = independent; >0.5 = the feature says what
    `group_index` says, and therefore inherits its noise."""
    pos, neg = [], []
    for i in range(n1):
        for j in range(n2):
            d = dist(i, j)
            if d is None:
                continue
            (pos if g1[i] == g2[j] else neg).append(-d)
    if not pos or not neg:
        return None, len(pos), len(neg)
    wins = sum((1.0 if p > q else 0.5 if p == q else 0.0) for p in pos for q in neg)
    return wins / (len(pos) * len(neg)), len(pos), len(neg)


# ⚠️ NO ARM D. The A/B through `slots.align` was NOT run: the discriminator
# stage below answers the question on its own, and the work was PARKED by a
# redirect on 2026-09-05 before any wiring arm was started. See
# MATCH_FEATURES.md — nothing here reports an A/B number.


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)

    from tools.omr import slots
    from tools.omr.types import PageWithStaves
    from tools.library.score_library import library_root

    fixstruct = UR.load_fixture_structures()
    labels = UR.load_labels()
    works = json.loads(UR.WORKS.read_text())
    rows = {r["row_id"]: r for r in works["rows"]}
    assert len(rows) == 20, f"expected 20 works.json rows, got {len(rows)}"

    multi = sorted(r for r, s in fixstruct.items() if len(s) > 1)
    assert len(multi) == 11, f"expected 11 multi-system rows, found {len(multi)}"

    cache = json.loads(UR.CACHE.read_text()) if UR.CACHE.exists() else {}
    assert cache, "EMPTY INPUT — the H1' detection cache is missing"
    lib = Path(library_root())

    SKIPS = [round(0.05 * k, 3) for k in range(1, 41)]      # 0.05 .. 2.00
    WEIGHTS = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0]

    results, abstentions = [], []
    n_staves_seen = 0
    zero_stratum = {"staves_with_zero_noteheads": 0,
                    "staves_with_zero_pitched": 0, "staves_total": 0}

    for rid in multi:
        row = rows[rid]
        key = f"{row['edition']['catalog_path']}#p{row['page']['pdf_page_index']}"
        assert key in cache, f"no cached detection for {rid} ({key})"
        record = cache[key]
        structure = [len(s) for s in record]
        if structure != fixstruct[rid]:
            abstentions.append({"row_id": rid, "kind": "STRUCTURE_MISMATCH",
                                "detected": structure, "fixture": fixstruct[rid]})
            continue

        feats = fixture_features(rid)
        assert [len(s) for s in feats] == fixstruct[rid], \
            f"{rid}: fixture feature systems {[len(s) for s in feats]} != {fixstruct[rid]}"
        assert len(feats) == 2, "the partner metric assumes exactly two systems"

        lineups, tier, why = UR.truth_lineups(rows, rid, structure)
        if lineups is None:
            abstentions.append({"row_id": rid, "kind": "NO_PER_SYSTEM_TRUTH",
                                "tier": tier, "why": why})
            continue

        f1, f2 = feats
        n1, n2 = len(f1), len(f2)
        n_staves_seen += n1 + n2
        for srows in feats:
            for r in srows:
                zero_stratum["staves_total"] += 1
                zero_stratum["staves_with_zero_noteheads"] += (r["n_noteheads_detected"] == 0)
                zero_stratum["staves_with_zero_pitched"] += (r["n_noteheads_pitched"] == 0)

        a1, b1 = gap_vectors(f1)
        a2, b2 = gap_vectors(f2)
        d_gap = lambda i, j: pair_distance_gap(a1, b1, i, a2, b2, j)      # noqa: E731
        d_reg = lambda i, j: pair_distance_register(f1[i], f2[j])          # noqa: E731
        d_both = lambda i, j: _combine(d_gap(i, j), d_reg(i, j))           # noqa: E731

        m0, m1_, union_truth = UR.truth_correspondence(lineups[0], lineups[1])
        ceiling = partner_ceiling(n1, n2, m0, m1_)
        best_align = best_truth_alignment(n1, n2, m0, m1_)
        diag_ok, diag_dec = score_pairs(diagonal_pairs(n1, n2), n1, n2, m0, m1_)
        tp = truth_pairs(m0)
        dp_ = diagonal_pairs(n1, n2)
        truth_is_diagonal = set(tp) <= set(dp_)

        g1 = [st["group_index"] for st in record[0]]
        g2 = [st["group_index"] for st in record[1]]

        per_feature = {}
        for fname, dist in (("gap", d_gap), ("register", d_reg), ("gap+register", d_both)):
            mt, nt, at = mean_distance(tp, dist)
            md, nd, ad = mean_distance(dp_, dist)
            auc, npos, nneg = group_auc(n1, n2, dist, g1, g2)
            sweep = []
            for sk in SKIPS:
                pairs, cost = align_on_distance(n1, n2, dist, sk)
                ok, dec = score_pairs(pairs, n1, n2, m0, m1_)
                sweep.append({"skip_cost": sk,
                              "continuity_correct": ok, "decisions": dec,
                              "at_ceiling": ok >= ceiling,
                              "argmax_is_truth": set(pairs) == set(tp),
                              "argmax_is_diagonal": pairs == dp_,
                              "n_pairs": len(pairs)})
            per_feature[fname] = {
                "mean_distance_truth_pairs": mt, "n_truth_pairs": nt,
                "n_truth_pairs_abstained": at,
                "mean_distance_diagonal": md, "n_diagonal_pairs": nd,
                "n_diagonal_abstained": ad,
                "delta_diagonal_minus_truth": (None if (mt is None or md is None)
                                               else round(md - mt, 6)),
                "group_index_auc": (None if auc is None else round(auc, 4)),
                "group_auc_n_agree_pairs": npos, "group_auc_n_disagree_pairs": nneg,
                "skip_sweep": sweep,
                "skip_costs_where_argmax_is_truth":
                    [s["skip_cost"] for s in sweep if s["argmax_is_truth"]],
                "skip_costs_at_partner_ceiling":
                    [s["skip_cost"] for s in sweep if s["at_ceiling"]],
                "best_continuity_over_sweep": max(s["continuity_correct"] for s in sweep),
                "weight_margin": feature_margin(dp_, best_align, dist),
            }

        results.append({
            "row_id": rid, "tier": tier, "structure": structure,
            "truth_union_size": union_truth,
            "partner_ceiling": ceiling, "decisions": n1 + n2,
            "diagonal_continuity": diag_ok,
            "best_truth_alignment": best_align,
            "truth_pairs": tp, "truth_is_a_subset_of_the_diagonal": truth_is_diagonal,
            "n_condensed_or_ambiguous_positions":
                len([i for i, v in m0.items() if len(v) > 1]),
            "group_index_per_system": [g1, g2],
            "group_index_agrees_diagonally":
                [int(g1[i] == g2[i]) for i in range(min(n1, n2))],
            "gap_vectors_above": [a1, a2],
            "gap_vectors_below": [b1, b2],
            "register": [[{"n_noteheads_detected": r["n_noteheads_detected"],
                           "n_noteheads_pitched": r["n_noteheads_pitched"],
                           "median_midi": r["median_midi"]} for r in s]
                         for s in feats],
            "features": per_feature,
        })
        print(f"   {rid:44s} {tier:9s} "
              f"gapΔ={per_feature['gap']['delta_diagonal_minus_truth']} "
              f"regΔ={per_feature['register']['delta_diagonal_minus_truth']} "
              f"diag={diag_ok}/{n1+n2} ceil={ceiling} "
              f"gapBest={per_feature['gap']['best_continuity_over_sweep']} "
              f"regBest={per_feature['register']['best_continuity_over_sweep']} "
              f"gapAUC={per_feature['gap']['group_index_auc']}", file=sys.stderr)

    assert results, "EMPTY OUTPUT — every row abstained; nothing was measured"
    assert n_staves_seen > 0, "EMPTY INPUT — no staves"

    # ── the separation question, asked exactly as the brief frames it ────────
    P4 = ["beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"]
    HOLD = "brahms-sym1-mvt1-317803-p3"
    by_row = {r["row_id"]: r for r in results}

    separation = {}
    for fname in ("gap", "register", "gap+register"):
        ok_p4 = {r: (by_row[r]["features"][fname]["skip_costs_at_partner_ceiling"]
                     if r in by_row else None) for r in P4}
        hold = (by_row[HOLD]["features"][fname]["skip_costs_at_partner_ceiling"]
                if HOLD in by_row else None)
        # a skip cost that is right on BOTH p.4 rows AND on the row that must
        # not move — and, for completeness, on every scored row at once.
        sets = [set(v or []) for v in ok_p4.values()] + [set(hold or [])]
        joint = sorted(set.intersection(*sets)) if all(sets) else []
        all_rows = [set(r["features"][fname]["skip_costs_at_partner_ceiling"])
                    for r in results]
        joint_all = sorted(set.intersection(*all_rows)) if all_rows else []
        margins = {r["row_id"]: r["features"][fname]["weight_margin"] for r in results}
        separation[fname] = {
            "weight_margins": margins,
            "rows_where_a_positive_weight_could_help":
                [k for k, v in margins.items() if v["any_positive_weight_can_help"]],
            "skip_costs_correct_on_p4": ok_p4,
            "skip_costs_correct_on_the_row_that_must_not_move": hold,
            "skip_costs_correct_on_p4_AND_brahms_p3": joint,
            "skip_costs_correct_on_ALL_scored_rows": joint_all,
            "separates": bool(joint),
        }

    payload = {
        "meta": {
            "target": ("PRE-REGISTERED: (1) worth > 1.5 in _pair_score units on "
                       "beethoven-...-p4; (2) brahms-...-p3 stays 28/28; "
                       "(3) the p.4 union reached by the CORRECT ROUTE (gap "
                       "Timpani, append Basso), continuity reported beside any "
                       "roster-size claim."),
            "fixtures": str(FIXTURES), "fixture_suffix": SUFFIX,
            "n_fixture_rows": 20, "n_fixture_staves": 396,
            "multi_system_rows": multi,
            "gap_substrate": "fixture staff_geometry.line_ys_page + line_spacing_px",
            "register_substrate": "fixture notehead detections carrying a pitch",
            "group_index_substrate": "probe_union_roster.py detection cache "
                                     "(render_page + detect_staves; no YOLO, no OCR)",
            "works_json": "SCORING ONLY, never an input; dossiers barred",
            "skip_cost_sweep": [SKIPS[0], SKIPS[-1], len(SKIPS)],
            "weights_reserved_for_arm_D": WEIGHTS,
        },
        "zero_detection_stratum": zero_stratum,
        "separation": separation,
        "abstentions": abstentions,
        "rows": results,
    }
    Path(a.out).write_text(json.dumps(payload, indent=1))

    print("\n" + "=" * 78, file=sys.stderr)
    print(f"rows measured: {len(results)}  abstained: {len(abstentions)}", file=sys.stderr)
    print(f"zero-detection stratum: {zero_stratum}", file=sys.stderr)
    for fname, s in separation.items():
        print(f"{fname:14s} separates p4-vs-brahms-p3: {s['separates']}  "
              f"joint={s['skip_costs_correct_on_p4_AND_brahms_p3'][:6]}  "
              f"all-rows={s['skip_costs_correct_on_ALL_scored_rows'][:6]}",
              file=sys.stderr)
    print(f"wrote {a.out}", file=sys.stderr)
    return 0


def _combine(dg, dr):
    """Gap in normalised-gap units, register in semitones/12. Both `None` ->
    abstain; one `None` -> the other alone."""
    parts = [x for x in (dg, None if dr is None else dr / 12.0) if x is not None]
    return (sum(parts) / len(parts)) if parts else None


if __name__ == "__main__":
    raise SystemExit(main())
