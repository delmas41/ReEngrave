#!/usr/bin/env python3
"""H1' — build the slot aligner's reference roster as a UNION over a page's systems.

MEASUREMENT ONLY. **No pipeline code is modified.** `tools/omr/slots.py` is
imported and called; `slots.build_reference` and `slots.align` run exactly as
shipped in arm A, and arm B swaps ONLY the roster constructor for the
benchmark-local `build_reference_union` below, calling the same unmodified
`slots.align`.

────────────────────────────────────────────────────────────────────────────
PRE-REGISTERED SUCCESS CRITERION (written before the run; see UNION_ROSTER.md)

  (1) arm B must produce a **12-slot** union on BOTH Beethoven 5 p.4 rows
      (`...-984073-p4`, `...-575951-p4`), and
  (2) arm B must not degrade continuity on ANY row arm A already gets right.

A union that fixes p4 by breaking Brahms p3/p4 is a FAILURE, exactly as the
bracket-shape detector was.
────────────────────────────────────────────────────────────────────────────

## Fixture provenance — the trap that has been hit three times

The 20-row gate lives ONLY in the reconciliation worktree, suffix
`.reconciliation.omr.json`. The main checkout's `fixtures/` holds the stale
11-row `..graft09` set; pointing there measures the wrong gate. Read-only:
another agent works in that tree.

## The label substrate, and why it is not the circular one

`slots.align`'s dominant term is the RAW per-system margin label. The fixtures
retain only the resolved, post-join `instrument` field, which is assigned BY
the slot join — circular for this purpose (the class-6 result). So the labels
here come from `vendored-labels/classified.json`: the labels workstream's
COMMITTED per-(row, system, position) ladder answers, each carrying the rung
that produced it (`resolved_by`). Reusing them rather than re-running the OCR
is sound because `git diff 672607c9 HEAD -- tools/omr/{instruments,staff_labels,
staff_labels_surya,staff_labels_tesseract,staff_detector,contextual,
system_grouping,slots,preprocessing}.py` is EMPTY on this tree, and it spends
no CPU on a shared machine where another agent is doing OCR concurrently.

⚠️ `Staff.group_index` — `_pair_score`'s second term — is NOT in the fixtures,
so the staves themselves are re-detected here (`render_page` + `detect_staves`,
no YOLO, no OCR). Re-detection may not reproduce the fixtures' structure: the
labels workstream measured it differing on the Mahler rows. Every row therefore
ASSERTS its re-detected per-system staff counts against the fixture's and
ABSTAINS, counted, where they differ.

## Scoring

`benchmarks/omr-scan-e2e-2026-09/works.json`, SCORING ONLY, never an input.
Dossiers barred entirely.

Two tiers, reported separately and never pooled:

* PRIMARY — rows carrying `systems_as_printed`, a hand-verified PER-SYSTEM
  lineup. These are the only rows that can state a continuity truth outright.
* SECONDARY — rows whose page-level `staves` list has exactly
  `n_staves / n_systems` entries, which asserts every system prints the SAME
  lineup, i.e. that the ordinal join is correct. ⚠️ This is MY reading of the
  key, not a per-system map the key states; it is labelled as such everywhere
  and kept out of the primary number. It exists so criterion (2) — "does not
  degrade a row arm A gets right" — has rows to be tested on.

Rows with neither are ABSTAINED and counted.

    python3 benchmarks/omr-structure-rnd-2026-09/probe_union_roster.py
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"
WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
VEND = HERE / "vendored-labels"
DPI = 600                     # works.json protocol.dpi
CACHE = HERE / "union-roster-detect-cache.json"


# ═══════════════════════════════════════════════════════════════════════════
# ARM B — the union roster. BENCHMARK-LOCAL. Nothing under tools/ changes.
# ═══════════════════════════════════════════════════════════════════════════
def _candidate_pool(views):
    """`build_reference`'s own filtering, reproduced so the union is taken over
    the SAME pool the shipped chooser picks from.

    The guards stay upstream of the union and keep doing exactly their job: they
    filter candidate SYSTEMS (a phase-1 merge is ~2x its neighbours and repeats
    an instrument), and a union is constructed after filtering rather than
    being a candidate itself.
    """
    from tools.omr import slots

    views = [v for v in views if v.size]
    if not views:
        return []
    sizes = sorted(v.size for v in views)
    median = sizes[len(sizes) // 2]
    cap = median * slots.REFERENCE_MAX_SIZE_RATIO
    candidates = [v for v in views if v.size <= cap and not slots._looks_merged(v)]
    if not candidates:
        candidates = views
    counts = collections.Counter(v.size for v in candidates)
    recurring = [v for v in candidates if counts[v.size] > 1]
    if recurring:
        candidates = recurring
    return candidates


def _renumber(protos):
    """`[(group_index, instrument)] -> [Slot]`, positions rebuilt over the run."""
    from tools.omr.slots import Slot

    n = max(1, len(protos) - 1)
    return [Slot(index=i, group_index=g, instrument=name, position=i / n)
            for i, (g, name) in enumerate(protos)]


def _merge_system(view, roster, trace, costs=None):
    """Fold one system into the roster, allowing BOTH kinds of gap.

    `slots.align` allows deletions on the reference side only — a part this
    system does not print. A union additionally needs the converse: a part this
    system prints that the roster does not yet hold. So this is `align`'s DP
    with one extra move.

    ⚠️ THE INSERTION COST IS `slots.GAP_PENALTY`, BY SYMMETRY — NOT A TUNED
    CONSTANT. A slot the system does not print and a staff the roster does not
    hold are the same event seen from the two sides, so they are priced the
    same. No constant is introduced by this probe.
    """
    from tools.omr import slots

    m, n = view.size, len(roster)
    if m == 0:
        return [(s.group_index, s.instrument) for s in roster]
    if n == 0:
        return [(st.group_index, view.labels.get(st.staff_index))
                for st in view.staves]

    denom = max(1, m - 1)
    positions = [i / denom for i in range(m)]
    labels = [view.labels.get(st.staff_index) for st in view.staves]
    GAP, INSERT = costs or (slots.GAP_PENALTY, slots.GAP_PENALTY)

    NEG = float("-inf")
    dp = [[NEG] * (n + 1) for _ in range(m + 1)]
    back = [[None] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = 0.0
    for j in range(1, n + 1):
        dp[0][j] = GAP * j
        back[0][j] = "gap"
    for i in range(1, m + 1):
        dp[i][0] = INSERT * i
        back[i][0] = "ins"
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            best, mv = dp[i][j - 1] + GAP, "gap"
            ins = dp[i - 1][j] + INSERT
            if ins > best:
                best, mv = ins, "ins"
            take = dp[i - 1][j - 1] + slots._pair_score(
                view.staves[i - 1], labels[i - 1], roster[j - 1], positions[i - 1])
            if take >= best:
                best, mv = take, "take"
            dp[i][j], back[i][j] = best, mv

    out: list[tuple[int, str | None]] = []
    i, j = m, n
    n_ins = n_gap = n_fill = 0
    while i > 0 or j > 0:
        mv = back[i][j]
        if mv == "take":
            slot = roster[j - 1]
            name = slot.instrument
            if name is None and labels[i - 1] is not None:
                # A union of INFORMATION as well as of slots: a slot no system
                # has named yet takes the name this one prints.
                name = labels[i - 1]
                n_fill += 1
            out.append((slot.group_index, name))
            i, j = i - 1, j - 1
        elif mv == "ins":
            st = view.staves[i - 1]
            out.append((st.group_index, labels[i - 1]))
            n_ins += 1
            i -= 1
        else:
            out.append((roster[j - 1].group_index, roster[j - 1].instrument))
            n_gap += 1
            j -= 1
    out.reverse()
    trace.append({"system_size": m, "roster_before": n, "roster_after": len(out),
                  "inserts": n_ins, "slot_gaps": n_gap, "labels_filled": n_fill})
    return out


def insert_margin(view, roster):
    """How far the merge was from inserting a slot, in the DP's own units.

    ⚠️ DIAGNOSTIC, NOT A KNOB. Returns `optimal - best_path_using_>=1_insert`.
    Zero or negative means the union grew. A positive value is the score the
    diagonal wins by, readable against the constants that produced it: a
    GAP_PENALTY is 1.0, a bracket-group agree/disagree swing is 3.0, a label
    match is 6.0 and a label CONFLICT is -8.0 (a 14.0 swing). It says what
    magnitude of NEW evidence a union would need — it is not a threshold to
    lower, and this probe proposes none.
    """
    from tools.omr import slots

    m, n = view.size, len(roster)
    if m == 0 or n == 0:
        return None
    denom = max(1, m - 1)
    positions = [i / denom for i in range(m)]
    labels = [view.labels.get(st.staff_index) for st in view.staves]
    NEG = float("-inf")
    # dp[k][i][j], k = whether an insert has been used
    dp = [[[NEG] * (n + 1) for _ in range(m + 1)] for _ in range(2)]
    dp[0][0][0] = 0.0
    for j in range(1, n + 1):
        dp[0][0][j] = slots.GAP_PENALTY * j
    for i in range(1, m + 1):
        dp[1][i][0] = slots.GAP_PENALTY * i
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            for k in (0, 1):
                cands = [dp[k][i][j - 1] + slots.GAP_PENALTY,
                         dp[k][i - 1][j - 1] + slots._pair_score(
                             view.staves[i - 1], labels[i - 1], roster[j - 1],
                             positions[i - 1])]
                if k == 1:      # an insert may arrive here, or already have
                    cands.append(dp[0][i - 1][j] + slots.GAP_PENALTY)
                    cands.append(dp[1][i - 1][j] + slots.GAP_PENALTY)
                dp[k][i][j] = max(cands)
    opt = max(dp[0][m][n], dp[1][m][n])
    with_ins = dp[1][m][n]
    if with_ins == NEG:
        return None
    return round(opt - with_ins, 6)


def build_reference_union(views, trace=None, costs=None):
    """The roster as the UNION over the page's systems.

    `build_reference` picks ONE system, which cannot be the roster when
    DIFFERENT systems suppress DIFFERENT staves (Beethoven 5 p.4: system 1
    prints no Timpani, system 2 condenses Violoncello + Basso into `Bassi`;
    both count 11 and the union is 12). Seeded with exactly the system
    `build_reference` would have chosen, so arm B is arm A plus whatever the
    other systems add — never less.
    """
    from tools.omr import slots

    trace = [] if trace is None else trace
    pool = _candidate_pool(views)
    if not pool:
        return []
    seed = max(pool, key=lambda v: (v.size, len(v.labels)))
    protos = [(st.group_index, seed.labels.get(st.staff_index))
              for st in seed.staves]
    for v in pool:
        if v is seed:
            continue
        protos = _merge_system(v, _renumber(protos), trace, costs)
    return _renumber(protos)


# ═══════════════════════════════════════════════════════════════════════════
# inputs
# ═══════════════════════════════════════════════════════════════════════════
def load_fixture_structures():
    paths = sorted(FIXTURES.glob(f"*{SUFFIX}"))
    assert paths, f"EMPTY INPUT — no fixtures under {FIXTURES}"
    assert len(paths) == 20, f"expected the 20-row gate, found {len(paths)}"
    out = {}
    for p in paths:
        rid = os.path.basename(p).split(".reconciliation")[0]
        doc = json.loads(p.read_text())
        out[rid] = [len(s["staves"]) for pg in doc.get("pages", [])
                    for s in pg.get("systems", []) if s.get("staves")]
        assert out[rid], f"no systems in fixture {rid}"
    n = sum(sum(v) for v in out.values())
    assert n == 396, f"expected 396 fixture staves, counted {n}"
    return out


def load_labels():
    """(row_id, system, position) -> (instrument name or None, rung)."""
    doc = json.loads((VEND / "classified.json").read_text())
    staves = doc["staves"]
    assert len(staves) == 407, f"expected 407 classified staves, got {len(staves)}"
    out = {}
    for s in staves:
        out[(s["row_id"], s["system"], s["position"])] = (
            s["resolved"], s["resolved_by"], s["reads"].get("ladder", ""))
    assert len(out) == 407
    return out


def detect(pdf: Path, page_index: int):
    """Staves only — no YOLO, no OCR. Cached, because rendering at 600 dpi on a
    shared CPU is the expensive half and nothing here is random."""
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves

    pws = detect_staves(render_page(pdf, page_index, dpi=DPI))
    by_sys: dict[int, list] = {}
    for s in sorted(pws.staves, key=lambda s: s.top_y):
        by_sys.setdefault(s.system_index, []).append(s)
    return [[{"staff_index": s.staff_index, "group_index": s.group_index,
              "top_y": s.top_y, "system_index": s.system_index}
             for s in by_sys[k]] for k in sorted(by_sys)]


def staves_from(record, page_index):
    """Rebuild real `Staff` objects — `slots` reads `staff_index`,
    `system_index`, `group_index` and `top_y` and nothing else."""
    from tools.omr.types import Staff

    out = []
    for sysi, sysrec in enumerate(record):
        for st in sysrec:
            out.append(Staff(page_index=page_index, staff_index=st["staff_index"],
                             line_ys=[st["top_y"] + 10 * k for k in range(5)],
                             x_start=0, x_end=1000,
                             system_index=st["system_index"],
                             group_index=st["group_index"]))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# truth
# ═══════════════════════════════════════════════════════════════════════════
def _deref(rows, rid, key):
    r = rows[rid]
    v = r.get(key)
    seen = set()
    while isinstance(v, str) and v.startswith("same-as:"):
        nxt = v.split(":", 1)[1]
        assert nxt not in seen, f"same-as cycle at {rid}"
        seen.add(nxt)
        r = rows[nxt]
        v = r.get(key)
    return v


def truth_lineups(rows, rid, structure):
    """Per-system lineups as `[[(name, frozenset(parts))]]`, plus the tier.

    Returns `(lineups, tier, why)`; `lineups is None` means abstain.
    """
    row = rows[rid]
    sap = _deref(rows, rid, "systems_as_printed")
    if isinstance(sap, dict):
        keys = sorted(k for k in sap if k.startswith("system_"))
        if len(keys) != len(structure):
            return None, "PRIMARY", (f"systems_as_printed names {len(keys)} systems, "
                                     f"the page reads {len(structure)}")
        lineups = [[(e["name"], frozenset(e["parts"])) for e in sap[k]] for k in keys]
        if [len(l) for l in lineups] != structure:
            return None, "PRIMARY", (f"lineup sizes {[len(l) for l in lineups]} != "
                                     f"detected {structure}")
        return lineups, "PRIMARY", "hand-verified per-system lineup"

    st = _deref(rows, rid, "staves")
    if isinstance(st, list):
        n_sys = row["page"]["n_systems"]
        if len(st) * n_sys == row["page"]["n_staves"] and \
                all(s == len(st) for s in structure):
            one = [(e.get("name"), frozenset(e.get("parts", []))) for e in st]
            return ([one] * len(structure), "SECONDARY",
                    "page-level `staves` asserts one lineup for every system")
        return None, "SECONDARY", ("page-level `staves` does not divide evenly "
                                   "into the detected systems")
    return None, "NONE", "the row states no lineup at all"


def _lcs_pairs(a, b):
    """Longest common subsequence over exact part-sets."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = (1 + dp[i + 1][j + 1]) if a[i] == b[j] \
                else max(dp[i + 1][j], dp[i][j + 1])
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            out.append((i, j))
            i, j = i + 1, j + 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def truth_correspondence(l1, l2):
    """`(pairs1to2, pairs2to1, union_size)`.

    Each map sends a position to the SET of acceptable partner positions in the
    other system — a set because a CONDENSED staff legitimately stands for two
    parts, so Beethoven p.4's `Bassi` is correct against either `Violoncello`
    or `Basso`. An empty set means "this part is not printed in the other
    system" and is a positive claim, not an abstention.
    """
    p1 = [x[1] for x in l1]
    p2 = [x[1] for x in l2]
    anchors = _lcs_pairs(p1, p2)
    m1 = {i: set() for i in range(len(p1))}
    m2 = {j: set() for j in range(len(p2))}
    for i, j in anchors:
        m1[i] = {j}
        m2[j] = {i}
    union = len(anchors)
    bounds = [(-1, -1)] + anchors + [(len(p1), len(p2))]
    for (ia, ja), (ib, jb) in zip(bounds, bounds[1:]):
        g1 = list(range(ia + 1, ib))
        g2 = list(range(ja + 1, jb))
        matched1, matched2 = set(), set()
        for i in g1:
            for j in g2:
                if p1[i] <= p2[j] or p2[j] <= p1[i]:   # condensation either way
                    m1[i].add(j)
                    m2[j].add(i)
                    matched1.add(i)
                    matched2.add(j)
        # A slot is contributed by each side's entries, with a condensed pair
        # counting once.
        union += max(len(g1), len(g2)) if (matched1 or matched2) \
            else len(g1) + len(g2)
    return m1, m2, union


# ═══════════════════════════════════════════════════════════════════════════
# scoring
# ═══════════════════════════════════════════════════════════════════════════
def partners(assign):
    """`slot per (system, position)` -> `(system, position) -> partner position
    in the OTHER system, or None`. Two systems only, which is every
    multi-system row on this corpus."""
    by_slot = collections.defaultdict(list)
    for (s, p), slot in assign.items():
        if slot >= 0:
            by_slot[slot].append((s, p))
    out = {}
    for (s, p), slot in assign.items():
        mates = [q for (t, q) in by_slot.get(slot, []) if t != s] if slot >= 0 else []
        out[(s, p)] = mates[0] if len(mates) == 1 else (None if not mates else "MULTI")
    return out


def score_arm(assign, m0, m1):
    """decisions, correct, per-staff detail."""
    got = partners(assign)
    detail, correct = [], 0
    for (s, p), mate in sorted(got.items()):
        want = (m0 if s == 0 else m1)[p]
        ok = (mate in want) if want else (mate is None)
        correct += bool(ok)
        detail.append({"system": s, "position": p, "predicted_partner": mate,
                       "acceptable": sorted(want), "ok": bool(ok)})
    return len(detail), correct, detail


# ═══════════════════════════════════════════════════════════════════════════
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "union-roster.json"))
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args(argv)

    from tools.omr import slots
    from tools.omr.types import PageWithStaves
    from tools.library.score_library import library_root

    fixstruct = load_fixture_structures()
    labels = load_labels()
    works = json.loads(WORKS.read_text())
    rows = {r["row_id"]: r for r in works["rows"]}
    assert len(rows) == 20, f"expected 20 works.json rows, got {len(rows)}"
    assert set(rows) == set(fixstruct), "works.json rows and fixtures disagree"

    multi = sorted(r for r, s in fixstruct.items() if len(s) > 1)
    assert len(multi) == 11, f"expected 11 multi-system rows, found {len(multi)}"
    assert all(len(fixstruct[r]) == 2 for r in multi), \
        "a row has more than two systems — the partner metric assumes two"

    lib = Path(library_root())
    cache = json.loads(CACHE.read_text()) if (CACHE.exists() and not a.no_cache) else {}

    results, abstentions = [], []
    n_labels_used = 0
    rungs = collections.Counter()

    for rid in multi:
        row = rows[rid]
        pdf = lib / row["edition"]["catalog_path"]
        assert pdf.exists(), f"PDF not in the score library: {pdf}"
        pidx = row["page"]["pdf_page_index"]

        key = f"{row['edition']['catalog_path']}#p{pidx}"
        if key not in cache:
            print(f"== detecting {rid} ({key})", file=sys.stderr)
            cache[key] = detect(pdf, pidx)
            CACHE.write_text(json.dumps(cache))
        record = cache[key]
        structure = [len(s) for s in record]

        # ── the abstention the brief demands, asserted rather than assumed ──
        if structure != fixstruct[rid]:
            abstentions.append({"row_id": rid, "kind": "STRUCTURE_MISMATCH",
                                "detected": structure, "fixture": fixstruct[rid]})
            print(f"   ABSTAIN {rid}: re-detected {structure} != fixture "
                  f"{fixstruct[rid]}", file=sys.stderr)
            continue

        lineups, tier, why = truth_lineups(rows, rid, structure)
        if lineups is None:
            abstentions.append({"row_id": rid, "kind": "NO_PER_SYSTEM_TRUTH",
                                "tier": tier, "why": why, "structure": structure})
            print(f"   ABSTAIN {rid}: {why}", file=sys.stderr)
            continue

        # ── labels: raw per-system, with the rung that read each ────────────
        lab: dict[int, str] = {}
        provenance = []
        for sysi, sysrec in enumerate(record):
            for pos, st in enumerate(sysrec):
                name, rung, raw = labels.get((rid, sysi, pos), (None, None, ""))
                provenance.append({"system": sysi, "position": pos, "raw": raw,
                                   "resolved": name, "rung": rung})
                if name:
                    lab[st["staff_index"]] = name
                    n_labels_used += 1
                    rungs[rung] += 1
        assert len(provenance) == sum(structure)

        pws = PageWithStaves(page=None, staves=staves_from(record, pidx))
        views = slots._views(pws, lab)
        assert [v.size for v in views] == structure

        ref_a = slots.build_reference(views)
        trace = []
        ref_b = build_reference_union(views, trace)
        assert len(ref_b) >= len(ref_a), "the union came out smaller than the seed"

        # ⚠️ ARM C IS A REFUTATION, NOT A PROPOSAL. Gap and insert are set to
        # ZERO — free — which is the cheapest a union can possibly be made
        # without inventing a new term. It exists to answer one question: can
        # ANY reweighting of the terms `_pair_score` already has separate the
        # p.4 rows (where the union is right) from the rows arm A already gets
        # right? If arm C fixes p.4 and also breaks a correct row, no such
        # weighting exists and the answer is new evidence, not new constants.
        trace_c = []
        ref_c = build_reference_union(views, trace_c, costs=(0.0, 0.0))

        m0, m1, union_truth = truth_correspondence(lineups[0], lineups[1])

        arms = {}
        for name, ref in (("A_control", ref_a), ("B_union", ref_b),
                          ("C_free_gaps_REFUTATION", ref_c)):
            assign = {}
            for sysi, view in enumerate(views):
                for pos, slot in enumerate(slots.align(view, ref)):
                    assign[(sysi, pos)] = slot
            n, ok, detail = score_arm(assign, m0, m1)
            arms[name] = {"roster_size": len(ref), "decisions": n, "correct": ok,
                          "accuracy": ok / n if n else None, "detail": detail,
                          "roster": [{"index": s.index, "group": s.group_index,
                                      "instrument": s.instrument} for s in ref]}

        # ── diagnostic: what the merge decided, and by how much ─────────────
        pool = _candidate_pool(views)
        seed = max(pool, key=lambda v: (v.size, len(v.labels)))
        margins = [{"system": i,
                    "is_seed": v is seed,
                    "insert_margin_vs_optimal": (None if v is seed
                                                 else insert_margin(v, ref_a))}
                   for i, v in enumerate(views)]

        results.append({
            "row_id": rid, "tier": tier, "why_scoreable": why,
            "structure": structure, "n_labels": len(lab),
            "group_index_per_system": [[st["group_index"] for st in s]
                                       for s in record],
            "labels_per_system": [[labels.get((rid, i, p), (None,))[0]
                                   for p in range(len(s))]
                                  for i, s in enumerate(record)],
            "insert_margins": margins,
            "truth_union_size": union_truth,
            "truth_lineups": [[(n_, sorted(p)) for n_, p in l] for l in lineups],
            "merge_trace": trace, "merge_trace_arm_C": trace_c, "label_provenance": provenance,
            "arms": arms,
        })
        print(f"   {rid:44s} {tier:9s} truth_union={union_truth:2d} "
              f"A: roster={arms['A_control']['roster_size']:2d} "
              f"{arms['A_control']['correct']}/{arms['A_control']['decisions']}  "
              f"B: roster={arms['B_union']['roster_size']:2d} "
              f"{arms['B_union']['correct']}/{arms['B_union']['decisions']}  "
              f"C: roster={arms['C_free_gaps_REFUTATION']['roster_size']:2d} "
              f"{arms['C_free_gaps_REFUTATION']['correct']}/"
              f"{arms['C_free_gaps_REFUTATION']['decisions']}",
              file=sys.stderr)

    assert results, "EMPTY OUTPUT — every row abstained; nothing was measured"
    assert n_labels_used > 0, "EMPTY INPUT — not one label resolved"

    # ── criterion ────────────────────────────────────────────────────────────
    by_row = {r["row_id"]: r for r in results}
    p4 = ["beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"]
    c1 = {r: (by_row[r]["arms"]["B_union"]["roster_size"] if r in by_row else None)
          for r in p4}
    crit1 = all(v == 12 for v in c1.values())
    regressions = [r["row_id"] for r in results
                   if r["arms"]["B_union"]["correct"] < r["arms"]["A_control"]["correct"]]
    crit2 = not regressions

    c_fix = [r["row_id"] for r in results
             if r["arms"]["C_free_gaps_REFUTATION"]["correct"]
             > r["arms"]["A_control"]["correct"]]
    c_break = [r["row_id"] for r in results
               if r["arms"]["C_free_gaps_REFUTATION"]["correct"]
               < r["arms"]["A_control"]["correct"]]

    payload = {
        "arm_C_refutation": {
            "what": ("gap and insert set to ZERO — the cheapest a union can be "
                     "made from the terms already present. NOT a proposal."),
            "rows_improved": c_fix, "rows_regressed": c_break,
            "reads": ("if this both fixes and breaks, no reweighting of the "
                      "existing terms separates the cases"),
        },
        "meta": {
            "criterion": ("PRE-REGISTERED: (1) arm B yields a 12-slot union on "
                          "both Beethoven 5 p.4 rows; (2) arm B degrades no row "
                          "arm A already gets right."),
            "fixtures": str(FIXTURES), "fixture_suffix": SUFFIX,
            "n_fixture_rows": 20, "n_fixture_staves": 396,
            "multi_system_rows": multi,
            "labels_source": "vendored-labels/classified.json (labels workstream "
                             "@672607c9; readers byte-identical on this tree)",
            "labels_used": n_labels_used,
            "label_rungs": dict(rungs),
            "dpi": DPI,
            "arm_A": "slots.build_reference + slots.align, unmodified",
            "arm_B": "benchmark-local build_reference_union + slots.align, "
                     "unmodified; insertion cost == slots.GAP_PENALTY by "
                     "symmetry, no constant introduced",
        },
        "criterion_1_p4_union_is_12": {"met": crit1, "observed": c1},
        "criterion_2_no_regression": {"met": crit2, "regressed_rows": regressions},
        "met": bool(crit1 and crit2),
        "abstentions": abstentions,
        "rows": results,
    }
    Path(a.out).write_text(json.dumps(payload, indent=1))

    print("\n" + "=" * 78, file=sys.stderr)
    print(f"rows measured: {len(results)}   abstained: {len(abstentions)}",
          file=sys.stderr)
    for tier in ("PRIMARY", "SECONDARY"):
        rs = [r for r in results if r["tier"] == tier]
        if not rs:
            continue
        da = sum(r["arms"]["A_control"]["decisions"] for r in rs)
        ca = sum(r["arms"]["A_control"]["correct"] for r in rs)
        cb = sum(r["arms"]["B_union"]["correct"] for r in rs)
        cc = sum(r["arms"]["C_free_gaps_REFUTATION"]["correct"] for r in rs)
        print(f"{tier:10s} n={len(rs):2d}  A {ca}/{da}   B {cb}/{da}   "
              f"C {cc}/{da}", file=sys.stderr)
    print(f"criterion 1 (p4 union == 12): {crit1}  {c1}", file=sys.stderr)
    print(f"criterion 2 (no regression) : {crit2}  {regressions}", file=sys.stderr)
    print(f"PRE-REGISTERED CRITERION MET: {bool(crit1 and crit2)}", file=sys.stderr)
    print(f"wrote {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
