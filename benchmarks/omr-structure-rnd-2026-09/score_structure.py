#!/usr/bin/env python3
"""H0 — a STRUCTURE metric for the 20-row scan gate.

Three INDEPENDENT sub-scores, never pooled with each other and never pooled
into an edit count:

  1. ROSTER RECOVERY  — did we report the right ordered printed lineup?
  2. CONTINUITY       — does the same printed part get the same slot in every
                        system it is printed in?
  3. IDENTITY         — do we name each staff's instrument, and correctly?

WHY THIS EXISTS.  OMR-NED cannot referee structure work on this corpus:
`benchmarks/omr-staff-structure-2026-09/FINDINGS.md` §6 measured that slot
assignment and staff segmentation cost nothing in the bucket that is supposed
to hold them, 87% of the `entire staff` bucket is a condensation floor tied
with Audiveris to the edit, and `benchmarks/omr-structural-parts-2026-09/
FINDINGS.md` showed the structural buckets INVERT SIGN depending on whether a
count oracle exists.  A correct structure fix therefore moves pooled OMR-NED by
a rounding error, and a wrong one can improve it.

HARD RULE, enforced by construction: this file emits no edit counts and no
combined score.  The three sub-scores are reported side by side and never
summed.

Inputs are read-only.  No detector is run.  No tuning parameter exists.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Provenance — stated here, asserted below, and reprinted into the JSON.
# --------------------------------------------------------------------------

# The 20-row scan gate's transcriptions live ONLY in the reconciliation
# worktree.  The main checkout's fixtures/ still holds the 11-row `..graft09`
# set; a script pointed there measures the OLD gate and says nothing about
# this one.  READ-ONLY: another agent may be working in that tree.
FIXTURE_DIR = (
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation/"
    "benchmarks/omr-scan-e2e-2026-09/fixtures"
)
FIXTURE_SUFFIX = ".reconciliation.omr.json"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKS_JSON = os.path.join(REPO, "benchmarks", "omr-scan-e2e-2026-09", "works.json")

# Hand-verified expectations.  An audit that can return "nothing found" must
# first prove it looked at something.
EXPECT_FIXTURES = 20
EXPECT_ROWS = 20
EXPECT_STAVES = 396
EXPECT_MULTI_SYSTEM_ROWS = 11

# --------------------------------------------------------------------------
# Truth-name -> canonical instrument kind.
#
# WRITTEN BY HAND, deliberately NOT taken from tools/omr/instruments.py.  That
# lexicon is part of the system under test (it is what turned `Tr. Alt.` into
# a singer and reads `Hoerner in Es` as Trumpet on the Breitkopf Brahms);
# normalising the truth with it would hide exactly the errors this metric is
# built to see.  Every key below is a printed staff name that occurs verbatim
# in works.json; a name not in this table is an ABSTENTION, never a guess.
#
# A frozenset value is a CONDENSED staff — one printed staff carrying two
# reference sections.  The prediction can only name one of them, so a
# prediction inside the set counts as correct.  That leniency is recorded.
# --------------------------------------------------------------------------
CELLO = "Cello"
CBASS = "Contrabass"

TRUTH_NAME_TO_KIND: Dict[str, Any] = {
    # --- Beethoven 5, Litolff (both scans) ---
    "Flauti": "Flute",
    "Oboi": "Oboe",
    "Clarinetti in B": "Clarinet",
    "Clarinetti in A": "Clarinet",
    "Fagotti": "Bassoon",
    "Corni in Es": "Horn",
    "Trombe in C": "Trumpet",
    "Timpani in C.G.": "Timpani",
    "Violino I": "Violin",
    "Violino II": "Violin",
    "Viola": "Viola",
    "Violoncello": CELLO,
    "Basso": CBASS,
    "Violoncello e Basso": frozenset({CELLO, CBASS}),
    "Bassi (Violoncello e Basso)": frozenset({CELLO, CBASS}),
    # --- Brahms 1, Breitkopf ---
    "2 Floten": "Flute",
    "2 Oboen": "Oboe",
    "2 Klarinetten in B": "Clarinet",
    "2 Fagotte": "Bassoon",
    "Kontrafagott": "Contrabassoon",
    "4 Horner in C 1./2.": "Horn",
    "4 Horner in Es 3./4.": "Horn",
    "2 Trompeten in C": "Trumpet",
    "Pauken in C u.G": "Timpani",
    "1. Violine": "Violin",
    "2. Violine": "Violin",
    "Bratsche": "Viola",
    "Violoncell": CELLO,
    "Kontrabass": CBASS,
    # --- Dvorak 9, Simrock ---
    "Corni I.II. in E": "Horn",
    "Corni III.IV. in C": "Horn",
    "Trombe in E": "Trumpet",
    "Tromboni I.II.": "Trombone",
    "Trombone basso": "Trombone",
    "Tympani A.E.H.": "Timpani",
    "Contrabasso": CBASS,
    # --- Mahler 5, Peters (five-line staves only; see MAHLER_ONE_LINE) ---
    "Vier Floten": "Flute",
    "Drei Hoboen": "Oboe",
    "Drei Klarinetten in A": "Clarinet",
    "Zwei Fagotte": "Bassoon",
    "Contrafagott": "Contrabassoon",
    "Sechs Horner in F (upper)": "Horn",
    "Sechs Horner in F (lower)": "Horn",
    "Vier Trompeten in B (upper)": "Trumpet",
    "Vier Trompeten in B (lower)": "Trumpet",
    "Drei Posaunen": "Trombone",
    "Tuba": "Tuba",
    "Pauken": "Timpani",
    "Erste Violinen": "Violin",
    "Zweite Violinen": "Violin",
    "Violen": "Viola",
    "Violoncelle": CELLO,
    "Basse": CBASS,
}

# Umlauts are stripped before lookup so the table above stays ASCII-legible;
# the works.json spellings carry them.
def _fold(name: str) -> str:
    table = {"ö": "o", "ä": "a", "ü": "u", "ß": "ss",
             "Ö": "O", "Ä": "A", "Ü": "U", "é": "e"}
    return "".join(table.get(ch, ch) for ch in name).strip()


# Mahler's five ONE-LINE percussion staves.  A five-line staff detector cannot
# find them by construction, so they are excluded from the roster truth and
# counted as a structural abstention rather than scored as misses.
MAHLER_ONE_LINE = {
    "Becken", "Grosse Trommel", "Kleine Trommel", "Tamtam",
    "Becken u. Gr.Trommel von einem geschlagen",
}


def kind_of(printed_name: str) -> Optional[Any]:
    return TRUTH_NAME_TO_KIND.get(_fold(printed_name))


def kinds_match(pred: Optional[str], truth: Any) -> bool:
    if pred is None or truth is None:
        return False
    if isinstance(truth, frozenset):
        return pred in truth
    return pred == truth


def kind_sets_overlap(a: Any, b: Any) -> bool:
    sa = a if isinstance(a, frozenset) else frozenset({a})
    sb = b if isinstance(b, frozenset) else frozenset({b})
    return bool(sa & sb)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_works() -> Tuple[Dict[str, dict], List[str]]:
    with open(WORKS_JSON) as fh:
        doc = json.load(fh)
    rows = doc["rows"]
    order = [r["row_id"] for r in rows]
    return {r["row_id"]: r for r in rows}, order


def resolve_same_as(value: Any, field: str, rows: Dict[str, dict], depth: int = 0) -> Any:
    """works.json stores some `staves` / `systems_as_printed` blocks as the
    string "same-as:<row_id>".  Follow it (bounded), never guess."""
    if depth > 4:
        raise RuntimeError("same-as chain too deep")
    if isinstance(value, str) and value.startswith("same-as:"):
        target = value.split(":", 1)[1]
        if target not in rows:
            raise KeyError(f"same-as target {target!r} not in works.json")
        return resolve_same_as(rows[target].get(field), field, rows, depth + 1)
    return value


def load_prediction(row_id: str) -> List[List[dict]]:
    """-> list of systems, each a list of staff dicts, in printed order."""
    path = os.path.join(FIXTURE_DIR, row_id + FIXTURE_SUFFIX)
    with open(path) as fh:
        doc = json.load(fh)
    systems: List[List[dict]] = []
    for page in doc["pages"]:
        for sysd in page["systems"]:
            systems.append(list(sysd["staves"]))
    return systems


# --------------------------------------------------------------------------
# Truth extraction: per-system printed lineups, or an explicit abstention.
# --------------------------------------------------------------------------

def truth_lineups(row: dict, rows: Dict[str, dict]) -> Tuple[Optional[List[List[str]]], str, str]:
    """Return (lineups | None, source, reason).

    `lineups[i]` is the ordered printed staff NAMES of system i.
    """
    row_id = row["row_id"]
    page = row.get("page", {})
    n_systems = page.get("n_systems")
    n_staves = page.get("n_staves")

    sap = resolve_same_as(row.get("systems_as_printed"), "systems_as_printed", rows)
    if isinstance(sap, dict):
        keys = sorted(k for k in sap if k != "_purpose")
        lineups = [[s["name"] for s in sap[k]] for k in keys]
        if len(lineups) != n_systems:
            return None, "systems_as_printed", (
                f"systems_as_printed lists {len(lineups)} systems, page says {n_systems}")
        if sum(len(x) for x in lineups) != n_staves:
            return None, "systems_as_printed", (
                "systems_as_printed staff total disagrees with page.n_staves")
        return lineups, "systems_as_printed", "per-system lineups stated explicitly"

    staves = resolve_same_as(row.get("staves"), "staves", rows)
    if isinstance(staves, list):
        names = [s["name"] for s in staves]
        # A single map is a per-system lineup ONLY when the arithmetic says the
        # page is n_systems copies of it.  Otherwise the map asserts one lineup
        # for the page and cannot decide continuity -> abstain.
        if n_systems * len(names) == n_staves:
            return [list(names) for _ in range(n_systems)], "staves_map_x_systems", (
                f"one {len(names)}-staff map x {n_systems} systems == page.n_staves")
        return None, "staves_map", (
            f"map of {len(names)} does not tile {n_staves} staves over "
            f"{n_systems} systems — asserts one lineup for the page")

    cond = row.get("condensation")
    if isinstance(cond, dict) and isinstance(cond.get("staves_as_printed"), list):
        allnames = [s["name"] for s in cond["staves_as_printed"]]
        five = [n for n in allnames if _fold(n) not in {_fold(x) for x in MAHLER_ONE_LINE}]
        if n_systems == 1 and len(five) == n_staves:
            return [five], "condensation.staves_as_printed", (
                f"{len(allnames) - len(five)} one-line percussion staves excluded "
                "(a five-line detector cannot find them)")
        return None, "condensation.staves_as_printed", (
            "five-line subset does not match page.n_staves")

    return None, "none", "row carries no printed-lineup truth (OMR-NED-only row)"


# --------------------------------------------------------------------------
# 1. ROSTER RECOVERY
# --------------------------------------------------------------------------

def lcs_matches(pred: Sequence[Optional[str]], truth: Sequence[Any]) -> int:
    """Length of the longest order-preserving matching between the predicted
    kinds and the truth kinds.  No tuning, no fuzzy scoring."""
    n, m = len(pred), len(truth)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if kinds_match(pred[i], truth[j]):
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    return dp[0][0]


def score_roster(row_id: str, lineups: List[List[str]], pred_systems: List[List[dict]]) -> dict:
    per_system = []
    for i, names in enumerate(lineups):
        truth_kinds = [kind_of(n) for n in names]
        unmapped = [n for n, k in zip(names, truth_kinds) if k is None]
        pred_kinds = [st.get("instrument") for st in pred_systems[i]]
        matched = lcs_matches(pred_kinds, truth_kinds)
        positional = None
        if len(pred_kinds) == len(truth_kinds):
            positional = sum(kinds_match(p, t) for p, t in zip(pred_kinds, truth_kinds))
        per_system.append({
            "system_index": i,
            "n_truth": len(truth_kinds),
            "n_pred": len(pred_kinds),
            "over": max(0, len(pred_kinds) - matched),
            "under": max(0, len(truth_kinds) - matched),
            "aligned_matches": matched,
            "positional_matches": positional,
            "unmapped_truth_names": unmapped,
        })
    return {
        "row_id": row_id,
        "systems": per_system,
        "n_truth": sum(s["n_truth"] for s in per_system),
        "n_pred": sum(s["n_pred"] for s in per_system),
        "over": sum(s["over"] for s in per_system),
        "under": sum(s["under"] for s in per_system),
        "aligned_matches": sum(s["aligned_matches"] for s in per_system),
        "positional_matches": (
            sum(s["positional_matches"] for s in per_system)
            if all(s["positional_matches"] is not None for s in per_system) else None),
    }


# --------------------------------------------------------------------------
# 2. CONTINUITY  (multi-system rows only)
#
# Scored as SLOT LINKAGE between systems, pairwise, which needs no global slot
# numbering and therefore imputes nothing where the page's union order is
# ambiguous:
#
#   truth link  = two staves in different systems printing the SAME part
#   pred  link  = two staves in different systems given the same slot_index
#   precision   = |pred & truth| / |pred|      recall = |pred & truth| / |truth|
#
# A staff whose printed part is RE-CONDENSED in the other system (Beethoven
# p.4's `Violoncello`+`Basso` against `Bassi (Violoncello e Basso)`) is
# UNPAIRABLE: it is excluded from both sides and counted, never scored.
# --------------------------------------------------------------------------

def score_continuity(row_id: str, lineups: List[List[str]], pred_systems: List[List[dict]]) -> dict:
    n_sys = len(lineups)
    # per-system name -> staff position; names are unique within a system on
    # this corpus, asserted below.
    unpairable: List[Tuple[int, int, str]] = []
    for i in range(n_sys):
        c = Counter(lineups[i])
        dup = [n for n, k in c.items() if k > 1]
        assert not dup, f"{row_id}: duplicate printed names in system {i}: {dup}"

    # Decide unpairable staves: unmatched across a pair, but whose canonical
    # kind-set overlaps an unmatched staff in the other system (a condensation
    # change, not a suppression).
    unpair_set = set()
    for i in range(n_sys):
        for j in range(i + 1, n_sys):
            a_un = [(p, n) for p, n in enumerate(lineups[i]) if n not in set(lineups[j])]
            b_un = [(p, n) for p, n in enumerate(lineups[j]) if n not in set(lineups[i])]
            for pa, na in a_un:
                ka = kind_of(na)
                for pb, nb in b_un:
                    kb = kind_of(nb)
                    if ka is not None and kb is not None and kind_sets_overlap(ka, kb):
                        unpair_set.add((i, pa))
                        unpair_set.add((j, pb))
    for (si, pi) in sorted(unpair_set):
        unpairable.append((si, pi, lineups[si][pi]))

    truth_links = set()
    for i in range(n_sys):
        for j in range(i + 1, n_sys):
            pos_j = {n: p for p, n in enumerate(lineups[j])}
            for pa, na in enumerate(lineups[i]):
                if (i, pa) in unpair_set:
                    continue
                pb = pos_j.get(na)
                if pb is None or (j, pb) in unpair_set:
                    continue
                truth_links.add(((i, pa), (j, pb)))

    pred_links = set()
    for i in range(n_sys):
        for j in range(i + 1, n_sys):
            slots_j = {}
            for pb, st in enumerate(pred_systems[j]):
                s = st.get("slot_index")
                if s is not None:
                    slots_j.setdefault(s, pb)
            for pa, st in enumerate(pred_systems[i]):
                if (i, pa) in unpair_set:
                    continue
                s = st.get("slot_index")
                if s is None:
                    continue
                pb = slots_j.get(s)
                if pb is None or (j, pb) in unpair_set:
                    continue
                pred_links.add(((i, pa), (j, pb)))

    correct = truth_links & pred_links
    return {
        "row_id": row_id,
        "n_truth_links": len(truth_links),
        "n_pred_links": len(pred_links),
        "n_correct_links": len(correct),
        "precision": (len(correct) / len(pred_links)) if pred_links else None,
        "recall": (len(correct) / len(truth_links)) if truth_links else None,
        "unpairable_staves": [{"system": s, "position": p, "name": n} for s, p, n in unpairable],
        "wrong_links": sorted(
            [{"a": list(a), "b": list(b),
              "a_name": lineups[a[0]][a[1]], "b_name": lineups[b[0]][b[1]]}
             for a, b in (pred_links - truth_links)],
            key=lambda d: (d["a"], d["b"])),
    }


# --------------------------------------------------------------------------
# 3. IDENTITY
#
# Coverage and precision reported SEPARATELY, coverage first.  Pairing is
# positional within a system and is only attempted where the predicted staff
# count equals the truth lineup length; otherwise the system abstains whole.
# --------------------------------------------------------------------------

def score_identity(row_id: str, lineups: List[List[str]], pred_systems: List[List[dict]]) -> dict:
    total = named = correct = 0
    abstained_systems = 0
    unmapped = 0
    wrong: List[dict] = []
    for i, names in enumerate(lineups):
        pred = pred_systems[i]
        if len(pred) != len(names):
            abstained_systems += 1
            continue
        for p, (nm, st) in enumerate(zip(names, pred)):
            k = kind_of(nm)
            if k is None:
                unmapped += 1
                continue
            total += 1
            got = st.get("instrument")
            if got is None:
                continue
            named += 1
            if kinds_match(got, k):
                correct += 1
            else:
                wrong.append({"system": i, "position": p, "printed": nm,
                              "truth_kind": sorted(k) if isinstance(k, frozenset) else k,
                              "predicted": got,
                              "source": st.get("instrument_source")})
    return {
        "row_id": row_id,
        "n_scoreable": total,
        "n_named": named,
        "n_correct": correct,
        "coverage": (named / total) if total else None,
        "precision": (correct / named) if named else None,
        "abstained_systems": abstained_systems,
        "unmapped_truth_names": unmapped,
        "wrong": wrong,
    }


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "structure-score.json"))
    args = ap.parse_args()

    # ---- provenance assertions: prove we looked at something -------------
    assert os.path.isdir(FIXTURE_DIR), f"fixture dir missing: {FIXTURE_DIR}"
    fixtures = sorted(f for f in os.listdir(FIXTURE_DIR) if f.endswith(FIXTURE_SUFFIX))
    assert len(fixtures) == EXPECT_FIXTURES, (
        f"expected {EXPECT_FIXTURES} fixtures with suffix {FIXTURE_SUFFIX}, found "
        f"{len(fixtures)} in {FIXTURE_DIR} — are you pointed at the 11-row graft09 set?")

    rows, order = load_works()
    assert len(order) == EXPECT_ROWS, f"works.json has {len(order)} rows, expected {EXPECT_ROWS}"
    fixture_ids = {f[: -len(FIXTURE_SUFFIX)] for f in fixtures}
    assert fixture_ids == set(order), (
        "fixture set and works.json rows disagree: "
        f"only-fixture={sorted(fixture_ids - set(order))} only-works={sorted(set(order) - fixture_ids)}")

    preds = {rid: load_prediction(rid) for rid in order}
    n_staves_seen = sum(len(s) for sysl in preds.values() for s in sysl)
    assert n_staves_seen == EXPECT_STAVES, (
        f"read {n_staves_seen} predicted staves, expected {EXPECT_STAVES}")
    n_multi = sum(1 for sysl in preds.values() if len(sysl) > 1)
    assert n_multi == EXPECT_MULTI_SYSTEM_ROWS, (
        f"{n_multi} multi-system rows, expected {EXPECT_MULTI_SYSTEM_ROWS}")
    n_slotted = sum(1 for sysl in preds.values() for s in sysl for st in s
                    if st.get("slot_index") is not None)
    assert n_slotted == EXPECT_STAVES, f"only {n_slotted}/{EXPECT_STAVES} staves carry slot_index"

    # ---- per row ---------------------------------------------------------
    roster: List[dict] = []
    continuity: List[dict] = []
    identity: List[dict] = []
    abstentions: List[dict] = []

    for rid in order:
        row = rows[rid]
        pred_systems = preds[rid]
        lineups, source, reason = truth_lineups(row, rows)

        if lineups is None:
            abstentions.append({"row_id": rid, "sub_score": "roster", "truth_source": source,
                                "reason": reason})
            abstentions.append({"row_id": rid, "sub_score": "identity", "truth_source": source,
                                "reason": reason})
            if len(pred_systems) > 1:
                abstentions.append({"row_id": rid, "sub_score": "continuity",
                                    "truth_source": source, "reason": reason})
            continue

        assert len(lineups) == len(pred_systems), (
            f"{rid}: truth has {len(lineups)} systems, prediction has {len(pred_systems)}")

        r = score_roster(rid, lineups, pred_systems)
        r["truth_source"] = source
        r["truth_note"] = reason
        roster.append(r)

        idn = score_identity(rid, lineups, pred_systems)
        idn["truth_source"] = source
        identity.append(idn)

        if len(pred_systems) > 1:
            c = score_continuity(rid, lineups, pred_systems)
            c["truth_source"] = source
            c["tier"] = "A-explicit" if source == "systems_as_printed" else "B-derived"
            continuity.append(c)

    assert roster, "roster scored zero rows"
    assert continuity, "continuity scored zero rows"
    assert identity, "identity scored zero rows"

    # ---- pooling (WITHIN a sub-score only — never across) ----------------
    def pool_roster(rs: List[dict]) -> dict:
        nt = sum(r["n_truth"] for r in rs)
        return {
            "rows": len(rs),
            "n_truth_staves": nt,
            "n_pred_staves": sum(r["n_pred"] for r in rs),
            "over": sum(r["over"] for r in rs),
            "under": sum(r["under"] for r in rs),
            "aligned_matches": sum(r["aligned_matches"] for r in rs),
            "aligned_accuracy": sum(r["aligned_matches"] for r in rs) / nt if nt else None,
            "positional_matches": sum(r["positional_matches"] for r in rs),
            "positional_accuracy": sum(r["positional_matches"] for r in rs) / nt if nt else None,
        }

    def pool_cont(cs: List[dict]) -> dict:
        tl = sum(c["n_truth_links"] for c in cs)
        pl = sum(c["n_pred_links"] for c in cs)
        ok = sum(c["n_correct_links"] for c in cs)
        return {"rows": len(cs), "truth_links": tl, "pred_links": pl, "correct_links": ok,
                "precision": ok / pl if pl else None, "recall": ok / tl if tl else None,
                "unpairable_staves": sum(len(c["unpairable_staves"]) for c in cs)}

    def pool_ident(ids: List[dict]) -> dict:
        t = sum(i["n_scoreable"] for i in ids)
        n = sum(i["n_named"] for i in ids)
        c = sum(i["n_correct"] for i in ids)
        return {"rows": len(ids), "n_scoreable": t, "n_named": n, "n_correct": c,
                "coverage": n / t if t else None, "precision": c / n if n else None,
                "unmapped_truth_names": sum(i["unmapped_truth_names"] for i in ids)}

    pooled = {
        "roster_recovery": pool_roster(roster),
        "continuity": {
            "all": pool_cont(continuity),
            "tier_A_explicit_per_system_truth": pool_cont(
                [c for c in continuity if c["tier"] == "A-explicit"]),
            "tier_B_derived_from_one_map": pool_cont(
                [c for c in continuity if c["tier"] == "B-derived"]),
        },
        "identity": pool_ident(identity),
    }

    global_named = sum(1 for sysl in preds.values() for s in sysl for st in s
                       if st.get("instrument") is not None)
    src = Counter(st.get("instrument_source")
                  for sysl in preds.values() for s in sysl for st in s)

    out = {
        "_what_this_is": [
            "H0, a STRUCTURE metric. Three INDEPENDENT sub-scores. They are never",
            "pooled with each other and never combined with an edit count: a",
            "structure score and an edit count answer different questions, and",
            "merging them is how the ES/EM repricing fooled two sessions.",
        ],
        "provenance": {
            "fixture_dir": FIXTURE_DIR,
            "fixture_suffix": FIXTURE_SUFFIX,
            "n_fixtures": len(fixtures),
            "works_json": WORKS_JSON,
            "n_rows": len(order),
            "n_predicted_staves": n_staves_seen,
            "n_multi_system_rows": n_multi,
            "truth_is_scoring_only": True,
            "dossiers_used": False,
            "detector_run": False,
            "name_normalizer": "hand table in this file — NOT tools/omr/instruments.py",
        },
        "pooled": pooled,
        "global_identity_coverage": {
            "n_staves": n_staves_seen,
            "n_named": global_named,
            "coverage": global_named / n_staves_seen,
            "instrument_source_counts": dict(src),
        },
        "per_row": {
            "roster_recovery": roster,
            "continuity": continuity,
            "identity": identity,
        },
        "abstentions": abstentions,
    }

    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")

    print_report(out)
    print(f"\nwrote {args.out}")
    return 0


def _pct(x: Optional[float]) -> str:
    return "  --  " if x is None else f"{x:.4f}"


def print_report(out: dict) -> None:
    p = out["provenance"]
    print("H0 STRUCTURE METRIC — 20-row scan gate")
    print(f"  fixtures : {p['n_fixtures']} x {p['fixture_suffix']}")
    print(f"             {p['fixture_dir']}")
    print(f"  truth    : {p['works_json']}  ({p['n_rows']} rows, scoring only)")
    print(f"  staves   : {p['n_predicted_staves']}   multi-system rows: {p['n_multi_system_rows']}")
    print("  no detector run, no dossier, truth never an input\n")

    print("=== 1. ROSTER RECOVERY (coverage first) ===")
    r = out["pooled"]["roster_recovery"]
    print(f"  coverage: {r['rows']} of {p['n_rows']} rows carry a printed-lineup truth "
          f"({r['n_truth_staves']} truth staves)")
    print(f"  pred staves {r['n_pred_staves']}  over {r['over']}  under {r['under']}")
    print(f"  order-preserving alignment accuracy : {_pct(r['aligned_accuracy'])}"
          f"  ({r['aligned_matches']}/{r['n_truth_staves']})")
    print(f"  strict positional accuracy          : {_pct(r['positional_accuracy'])}"
          f"  ({r['positional_matches']}/{r['n_truth_staves']})")
    print(f"  {'row':40s} {'src':26s} {'T':>4s} {'P':>4s} {'ovr':>4s} {'und':>4s} {'algn':>5s} {'pos':>5s}")
    for row in out["per_row"]["roster_recovery"]:
        print(f"  {row['row_id']:40s} {row['truth_source']:26s} {row['n_truth']:4d} "
              f"{row['n_pred']:4d} {row['over']:4d} {row['under']:4d} "
              f"{row['aligned_matches']:5d} "
              f"{('%5d' % row['positional_matches']) if row['positional_matches'] is not None else '   --'}")

    print("\n=== 2. CONTINUITY (slot linkage across systems) ===")
    c = out["pooled"]["continuity"]
    print(f"  coverage: {c['all']['rows']} of {p['n_multi_system_rows']} multi-system rows scored")
    for label, key in (("all", "all"),
                       ("tier A (explicit per-system truth)", "tier_A_explicit_per_system_truth"),
                       ("tier B (one map x n_systems)", "tier_B_derived_from_one_map")):
        b = c[key]
        print(f"  {label:36s} rows {b['rows']:2d}  links T{b['truth_links']:3d}/P{b['pred_links']:3d}"
              f"  correct {b['correct_links']:3d}  precision {_pct(b['precision'])}"
              f"  recall {_pct(b['recall'])}")
    print(f"  {'row':40s} {'tier':11s} {'T':>4s} {'P':>4s} {'ok':>4s} {'prec':>7s} {'rec':>7s} {'unpair':>7s}")
    for row in out["per_row"]["continuity"]:
        print(f"  {row['row_id']:40s} {row['tier']:11s} {row['n_truth_links']:4d} "
              f"{row['n_pred_links']:4d} {row['n_correct_links']:4d} "
              f"{_pct(row['precision']):>7s} {_pct(row['recall']):>7s} "
              f"{len(row['unpairable_staves']):7d}")

    print("\n=== 3. IDENTITY (coverage before precision) ===")
    i = out["pooled"]["identity"]
    g = out["global_identity_coverage"]
    print(f"  coverage: {i['rows']} rows scoreable, {i['n_scoreable']} staves with a mapped truth name")
    print(f"  named {i['n_named']}/{i['n_scoreable']}  coverage {_pct(i['coverage'])}"
          f"   correct {i['n_correct']}/{i['n_named']}  precision {_pct(i['precision'])}")
    print(f"  (whole corpus, no truth needed: {g['n_named']}/{g['n_staves']} staves named, "
          f"coverage {_pct(g['coverage'])})")
    print(f"  {'row':40s} {'scor':>5s} {'namd':>5s} {'corr':>5s} {'cov':>7s} {'prec':>7s}")
    for row in out["per_row"]["identity"]:
        print(f"  {row['row_id']:40s} {row['n_scoreable']:5d} {row['n_named']:5d} "
              f"{row['n_correct']:5d} {_pct(row['coverage']):>7s} {_pct(row['precision']):>7s}")

    print("\n=== ABSTENTIONS ===")
    if not out["abstentions"]:
        print("  none")
    for a in out["abstentions"]:
        print(f"  {a['row_id']:40s} {a['sub_score']:11s} [{a['truth_source']}] {a['reason']}")


if __name__ == "__main__":
    sys.exit(main())
