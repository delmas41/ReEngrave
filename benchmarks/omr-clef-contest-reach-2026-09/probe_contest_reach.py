#!/usr/bin/env python3
"""Does `clef_evidence["contest"]` have a population `clef_correction` could act on?

A PRE-REGISTERED REACH GATE. `docs/pipeline-gather-then-adjudicate-2026-09-07.md`
recommends giving the contest record a consumer in `clef_correction`: the clef
argmax decides with no instrument in scope, `clef_correction` runs later with the
instrument in hand, so it could reconsider a clef knowing what the argmax nearly
chose. This probe asks whether that population EXISTS before anyone builds it.

Four columns, in the order the gate asks them:

  A  contest        the staff recorded a contest at all
  B  differs        the contest had a losing candidate differing from the winner,
                    read in BOTH available senses (see below)
  C  reachable      `clef_correction` has an admissible INSTRUMENT for this staff
  D  actionable     reachable AND the instrument's expected clef disagrees with
                    the clef the argmax left in effect

⚠️ TWO TRAPS, NAMED IN THE WORK ORDER AND HONOURED HERE.

1. `contest["disagrees"]` IS NOT COLUMN B. It compares runner-up to winner
   WITHIN a cell, so it exists only where two candidates resolved — and every
   known mid-staff clef flip is the only clef detection in its cell
   (`n_resolved == 1`), carrying no `disagrees` key at all. `disagrees` is
   absent exactly where the answer lives. So B is computed two ways and
   reported apart:
     B1 within-cell — >= 2 DISTINCT clef names among the cell's resolved
        candidates, recomputed from `candidates` rather than read off the
        `disagrees` boolean (the boolean is then cross-checked against it);
     B2 flip — `clef_in_effect_after` != `clef_in_effect_before`, recomputed
        from the two fields rather than read off `overturns_inherited` (again
        cross-checked). This is the sense the record's own docstring calls
        "the contest that matters".
   B = B1 or B2.

2. `overturns_inherited` IS PRE-REPAIR. It says the argmax flipped the clef,
   not that the flip survived to the output — a dossier override can put the
   inherited clef back. It is reported as what it is and never as a count of
   wrong clefs in the file. (On this corpus the point is moot in one direction:
   the scan gate runs `dossier=None` by protocol, which the probe asserts.)

REACH (column C) is taken from the CONSUMER'S OWN TRACE, not reconstructed.
`clef_correction.correct_clefs_from_instruments` writes
`staff["clef_proposal_evidence"]` for every staff it was handed an instrument
for, and `contextual.py` hands it `read_instruments` — the dict already filtered
of the sources the consumer refuses (`score_order` always; `roster` unless
`OMR_ROSTER_CLEF`). Unpitched instruments are skipped before the trace is
written. So the trace's PRESENCE is the reachability predicate, decided by the
code under test rather than by this probe's reading of it. A second, independent
route (instrument fields on the staff dict) is computed alongside and the two
are required to agree; a disagreement is reported, loudly, as a finding.

Usage:
    probe_contest_reach.py FIXTURE.omr.json [...] [--json OUT] [--quiet]

Exits non-zero on an empty or unusable input set — see `_load`. Prove that guard
fires before trusting a table of zeros:

    probe_contest_reach.py /nonexistent/path.omr.json ; echo $?     # 2
    probe_contest_reach.py                            ; echo $?     # 2
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# The 20-row gate holds two scans of ONE Litolff plate (imslp 984073 and
# 575951, offset by a leading page). They are not independent evidence, so `n`
# is reported as DISTINCT DOCUMENTS and those two share a key.
DOCUMENT_OF_ROW = {
    "beethoven-sym5-mvt1-984073": "beethoven-5 / Litolff 1870",
    "beethoven-sym5-mvt1-575951": "beethoven-5 / Litolff 1870",
    "dvorak-sym9-mvt1-405834": "dvorak-9 / Simrock",
    "brahms-sym1-mvt1-317803": "brahms-1 / Breitkopf",
    "mahler-sym5-mvt1-local": "mahler-5 / Peters",
    "bach-brandenburg3-mvt1-468678": "bach-bwv1048 / Peters",
}

# The sources `clef_correction` refuses, restated here ONLY to cross-check the
# consumer's own trace. `contextual.py` is the authority; if these disagree the
# probe says so rather than picking one.
REFUSED_SOURCES = {"score_order", "roster"}

# `clef_correction.MID_STAFF_CHANGE_VETOES`, restated so this probe can report
# how much of the mid-staff flip population ALREADY has a consumer. Imported
# rather than copied where the import works; the literal is the fallback so the
# probe runs standalone against a fixture directory.
try:  # pragma: no cover - convenience
    from tools.omr.clef_correction import (  # type: ignore
        MID_STAFF_CHANGE_VETOES, TREBLE_OVERRIDE_INSTRUMENTS)
except Exception:  # noqa: BLE001
    MID_STAFF_CHANGE_VETOES = {("Violin", "treble", "bass"),
                               ("Viola", "alto", "bass")}
    TREBLE_OVERRIDE_INSTRUMENTS = ("Viola", "Bassoon", "Contrabassoon", "Timpani")


class BadInput(Exception):
    pass


def _row_id(path: Path) -> str:
    """`beethoven-sym5-mvt1-984073-p1.clefcontest.omr.json` -> row id."""
    name = path.name
    for suffix in (".omr.json",):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    # strip an arm tag: everything from the first '.' after the row id
    return name.split(".")[0]


def _document(row_id: str) -> str:
    stem = row_id.rsplit("-p", 1)[0]
    return DOCUMENT_OF_ROW.get(stem, f"UNMAPPED:{stem}")


def _load(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    """Read every fixture, or raise. A silent empty set is the failure this
    guard exists for: seven probes this week printed clean tables of zeros and
    looked healthy, and one caused a false retraction."""
    if not paths:
        raise BadInput("no input files given")
    out: list[tuple[Path, dict[str, Any]]] = []
    for p in paths:
        if not p.is_file():
            raise BadInput(f"missing input file: {p}")
        try:
            doc = json.loads(p.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BadInput(f"unreadable JSON: {p}: {exc}") from exc
        if not isinstance(doc, dict) or not doc.get("pages"):
            raise BadInput(f"no pages in {p}")
        out.append((p, doc))
    n_staves = sum(len(sy.get("staves", []))
                   for _, d in out
                   for pg in d["pages"] for sy in pg.get("systems", []))
    if n_staves == 0:
        raise BadInput(
            f"{len(out)} file(s) loaded and ZERO staves among them — the input "
            f"set cannot answer the question")
    return out


def _contests(staff: dict[str, Any]) -> list[tuple[str, dict[str, Any], bool]]:
    """Every contest recorded for this staff, as (where, contest, is_first_cell).

    Two sites carry it: the staff's own `clef_evidence` (its FIRST CELL's dict,
    lifted by `transcribe`) and any measure's `clef_evidence` (every cell). The
    first cell's record therefore appears at BOTH sites and must not be counted
    twice.

    ⚠️ The dedup is BY CONTENT, not by index. `transcribe` renumbers
    `measure_index` (`measure["measure_index"] = new_index`), so the staff's
    first CELL is not reliably `measure_index == 0` — an index-keyed dedup would
    silently double-count exactly the staves whose measures were renumbered.
    The two sites hold the same dict object before serialisation, so equal
    content is the reliable key.
    """
    staff_ev = staff.get("clef_evidence") or {}
    staff_c = staff_ev.get("contest")
    found: list[tuple[str, dict[str, Any], bool]] = []
    first_seen = False
    for m in staff.get("measures", []):
        ev = m.get("clef_evidence") or {}
        c = ev.get("contest")
        if not c:
            continue
        is_first = (not first_seen) and c == staff_c
        first_seen = first_seen or is_first
        found.append((f"m{m.get('measure_index')}", c, is_first))
    if staff_c and not first_seen:
        # ⚠️ PREPEND. The staff-level dict is cell 0's, so when the measure it
        # was written on did not survive to the output (measures are merged and
        # renumbered downstream) it still belongs at the FRONT of the sequence.
        # Appending it would put cell 0 after cells that ran later and silently
        # corrupt any order-dependent reading — which `_overturns` is.
        found.insert(0, ("staff", staff_c, True))
    return found


def _within_cell_differs(contest: dict[str, Any]) -> bool:
    """>= 2 DISTINCT clef names among this cell's resolved candidates.

    Recomputed from `candidates`, NOT read off `contest["disagrees"]`, so the
    recorded boolean can be cross-checked against it.
    """
    names = {c.get("clef") for c in contest.get("candidates", [])
             if c.get("resolved")}
    names.discard(None)
    return len(names) > 1


def _flip(contest: dict[str, Any]) -> bool:
    """The argmax winner differs from the clef the cell came in with.

    Recomputed from `clef_in_effect_before` / `_after` rather than read off
    `overturns_inherited`. ⚠️ PRE-REPAIR — see the module docstring.
    """
    before = contest.get("clef_in_effect_before")
    after = contest.get("clef_in_effect_after")
    return before is not None and after is not None and after != before


def _overturns(contests: list[tuple[str, dict[str, Any], bool]]) -> int:
    """Flips that overturn a clef some reader ESTABLISHED on this staff.

    ⚠️ THIS, NOT "not the first cell", IS THE POPULATION THE RECOMMENDATION IS
    ABOUT. Two different things both satisfy `after != before`:

      ESTABLISHING  the staff is still on `_default_clef_for_position` (treble)
                    because nothing has read a clef yet, and a cell finally
                    reads one. Dvorak p5 is full of these — its staves' FIRST
                    cells record `n_candidates: 0`, and a later cell reads
                    Bassoon-bass at 0.88 / Trombone-alto at 0.92. That is the
                    pipeline working, and `before == "treble"` there is the
                    positional default, not a reading.
      OVERTURNING   a clef WAS read, and a later cell contradicts it. This is
                    the documented fault (984073-p1 s9 Viola alto->bass @0.59).

    Counting the first kind as the second inflates the population with exactly
    the cells where the argmax is right. So `established` is tracked from the
    contests' own `clef_in_effect_after` — the positional default never
    establishes anything — and only a contradiction of an established reading
    counts. Requires `contests` in document order (see `_contests`).
    """
    established: str | None = None
    n = 0
    for _where, c, _first in contests:
        after = c.get("clef_in_effect_after")
        if after is None:
            continue
        if established is not None and after != established:
            n += 1
        established = after
    return n


def _reachable_by_trace(staff: dict[str, Any]) -> bool:
    """The consumer's own answer: it wrote a trace, so it had an instrument."""
    return isinstance(staff.get("clef_proposal_evidence"), dict)


def _label_sourced(staff: dict[str, Any]) -> bool:
    """The STRICTER gate the recommendation pre-registered: `instrument_source
    == "label"`, i.e. the instrument was named by a margin label READ on the
    page.

    §7.2 names this as the pass criterion ("on staves that also satisfy
    `instrument_source == 'label'` — the existing provenance gate"). It is
    NARROWER than what `clef_correction`'s FILL path admits: that path takes
    `read_instruments`, which also admits `score_order_ambiguity` (a label the
    prior disambiguated, not a name it invented). Both are reported, because
    which one applies depends on which tier a new consumer would sit in — the
    OVERRIDE tier and `veto_implausible_clef_changes` both require `label`.
    """
    return staff.get("instrument_source") == "label"


def _reachable_by_fields(staff: dict[str, Any]) -> bool:
    """The independent route, from the identity fields on the staff dict."""
    if not staff.get("instrument"):
        return False
    if staff.get("unpitched"):
        return False
    if staff.get("instrument_veto"):
        return False
    return staff.get("instrument_source") not in REFUSED_SOURCES


def analyse(paths: list[Path]) -> dict[str, Any]:
    loaded = _load(paths)
    rows: list[dict[str, Any]] = []
    exits: Counter = Counter()
    # The funnel that decides column D: where does `propose_clef` exit on the
    # staves that HAVE a contest and ARE reachable? A null D is uninformative
    # without this — "the instrument agrees with the argmax" and "the staff has
    # too few noteheads to ask" are different reasons for the same zero.
    exits_bc: Counter = Counter()
    xcheck = {
        # ⚠️ NOT a must-be-zero. `contest["disagrees"]` compares the TOP TWO
        # ranked candidates only, so it reads False on a genuine THREE-way
        # disagreement (two agreeing clefG plus a dissenting clefF). The
        # recomputation counts DISTINCT resolved clefs, so it is a superset.
        # Every hit is inspected and reported; see FINDINGS.
        "disagrees_top2_vs_distinct_EXPECTED_NONZERO": 0,
        "overturns_key_vs_recomputed": 0,
        "reach_trace_vs_fields": 0,
        "winner_vs_trace_current_clef": 0,
        # `read_clef_rung_ran` is True only where `read_clef=(cell_idx == 0)`
        # was passed, so it is an INDEPENDENT route to "this is the staff's
        # first cell" — keyed on a flag the pipeline set, not on this probe's
        # content dedup. They must agree on every contest.
        "first_cell_dedup_vs_read_clef_rung": 0,
        "dossier_seeded_staves": 0,
    }
    actionable_detail: list[dict[str, Any]] = []
    mid_detail: list[dict[str, Any]] = []

    for path, doc in loaded:
        rid = _row_id(path)
        row = {
            "row_id": rid, "document": _document(rid), "file": path.name,
            "staves": 0, "A_contest": 0, "B1_within_cell": 0, "B2_flip": 0,
            "B2_mid_staff": 0, "B2_overturn": 0, "B_differs": 0,
            "C_reachable": 0,
            "D_actionable": 0, "BC_differs_and_reachable": 0,
            "MID_and_reachable": 0, "MID_uncovered": 0,
            "C_label": 0, "BC_label": 0, "MID_and_label": 0,
            "OVER_and_reachable": 0, "OVER_and_label": 0,
            "seconds": doc.get("_scan_eval_seconds"),
        }
        for page in doc["pages"]:
            for system in page.get("systems", []):
                for staff in system.get("staves", []):
                    row["staves"] += 1
                    contests = _contests(staff)
                    has_contest = bool(contests)
                    b1 = any(_within_cell_differs(c) for _, c, _f in contests)
                    b2 = any(_flip(c) for _, c, _f in contests)
                    # ⚠️ THE DECOMPOSITION THAT MATTERS. On a staff's FIRST
                    # cell `clef_in_effect_before` is the POSITIONAL DEFAULT
                    # (treble) that every staff starts under, not a clef any
                    # reader established — so "the argmax flipped it" is just
                    # the opening clef being READ, which is the pipeline
                    # working. A bassoon staff reading bass at m0 is a flip by
                    # the letter of the field and is not an error. Only a
                    # LATER cell flips a clef that was actually established,
                    # and that is the population carrying the known errors.
                    b2_mid = any(_flip(c) for _, c, f in contests if not f)
                    # The strict reading — see `_overturns`.
                    b2_over = _overturns(contests) > 0
                    differs = b1 or b2

                    # ---- cross-check 0: the two routes to "first cell"
                    for _w, c, f in contests:
                        rung = c.get("read_clef_rung_ran")
                        if rung is not None and bool(rung) != f:
                            xcheck["first_cell_dedup_vs_read_clef_rung"] += 1

                    # ---- cross-check 1: recorded booleans vs recomputed
                    for _, c, _f in contests:
                        if "disagrees" in c and c["disagrees"] != _within_cell_differs(c):
                            xcheck["disagrees_top2_vs_distinct_EXPECTED_NONZERO"] += 1
                        if "overturns_inherited" in c \
                                and bool(c["overturns_inherited"]) != _flip(c):
                            xcheck["overturns_key_vs_recomputed"] += 1

                    # ---- cross-check 2: is a dossier in play? If none is, the
                    # pre-repair/post-repair distinction on `overturns_inherited`
                    # cannot bite, because the dossier override is the repair.
                    # The scan gate runs `dossier=None` by protocol; this checks
                    # rather than assumes it.
                    ev = staff.get("clef_evidence") or {}
                    if ev.get("dossier"):
                        xcheck["dossier_seeded_staves"] += 1

                    # ---- column C, two independent routes
                    r_trace = _reachable_by_trace(staff)
                    r_fields = _reachable_by_fields(staff)
                    if r_trace != r_fields:
                        xcheck["reach_trace_vs_fields"] += 1
                    reachable = r_trace
                    label_sourced = _label_sourced(staff) and reachable

                    trace = staff.get("clef_proposal_evidence") or {}
                    if trace:
                        exits[trace.get("exit", "?")] += 1

                    # ---- cross-check 3: the trace's view of the clef in
                    # effect against the argmax winner the contest recorded.
                    winner_after = next(
                        (c.get("clef_in_effect_after") for _, c, f in contests
                         if f and c.get("clef_in_effect_after")), None)
                    if trace and winner_after and trace.get("current_clef") \
                            and trace["current_clef"] != winner_after:
                        xcheck["winner_vs_trace_current_clef"] += 1

                    # ---- column D: the instrument's expected clef DISAGREES
                    # with what the argmax left in effect. `exit == "proposed"`
                    # is exactly that: propose_clef returned a shift, having
                    # already refused `already_in_effect` and `would_worsen_fit`.
                    proposed = trace.get("exit") == "proposed"

                    # ---- the mid-staff flip population, itemised. This is
                    # what a new consumer would actually be handed.
                    if b2_mid or b2_over:
                        instr = staff.get("instrument")
                        _est: str | None = None
                        _kind: dict[int, str] = {}
                        for _i, (_w, _c, _f) in enumerate(contests):
                            _a = _c.get("clef_in_effect_after")
                            if _a is None:
                                continue
                            _kind[_i] = ("overturn"
                                         if _est is not None and _a != _est
                                         else "establish")
                            _est = _a
                        src = staff.get("instrument_source")
                        for _i, (where, c, f) in enumerate(contests):
                            if f or not _flip(c):
                                continue
                            triple = (instr, c.get("clef_in_effect_before"),
                                      c.get("clef_in_effect_after"))
                            covered = triple in MID_STAFF_CHANGE_VETOES
                            mid_detail.append({
                                "row_id": rid, "document": _document(rid),
                                "staff_index": staff.get("staff_index"),
                                "where": where, "instrument": instr,
                                "instrument_source": src,
                                "from_clef": triple[1], "to_clef": triple[2],
                                "kind": _kind.get(_i, "?"),
                                "n_resolved": c.get("n_resolved"),
                                "winner_confidence": c.get("winner_confidence"),
                                "reachable": reachable,
                                # the EXISTING consumer for this population
                                "veto_covers_it": covered,
                                "veto_would_see_it": src == "label",
                                "already_vetoed": bool(
                                    staff.get("clef_change_veto")),
                            })
                        if reachable:
                            row["MID_and_reachable"] += 1
                        # "uncovered" = the EXISTING consumer
                        # (`veto_implausible_clef_changes`) would not handle
                        # this flip even with its flag on. Its gate is BOTH
                        # `instrument_source == "label"` AND the
                        # (instrument, from, to) triple being in the table, so
                        # failing either leaves the flip uncovered.
                        handled = _label_sourced(staff) and any(
                            (staff.get("instrument"),
                             c.get("clef_in_effect_before"),
                             c.get("clef_in_effect_after"))
                            in MID_STAFF_CHANGE_VETOES
                            for _w, c, f in contests
                            if not f and _flip(c))
                        if reachable and not handled:
                            row["MID_uncovered"] += 1

                    row["A_contest"] += has_contest
                    row["B1_within_cell"] += b1
                    row["B2_flip"] += b2
                    row["B2_mid_staff"] += b2_mid
                    row["B2_overturn"] += b2_over
                    if b2_over and reachable:
                        row["OVER_and_reachable"] += 1
                    if b2_over and label_sourced:
                        row["OVER_and_label"] += 1
                    row["B_differs"] += differs
                    row["C_reachable"] += reachable
                    row["C_label"] += label_sourced
                    if differs and label_sourced:
                        row["BC_label"] += 1
                    if b2_mid and label_sourced:
                        row["MID_and_label"] += 1
                    if differs and reachable:
                        row["BC_differs_and_reachable"] += 1
                        exits_bc[trace.get("exit", "?")] += 1
                    if differs and reachable and proposed:
                        row["D_actionable"] += 1
                        actionable_detail.append({
                            "row_id": rid, "document": _document(rid),
                            "staff_index": staff.get("staff_index"),
                            "instrument": trace.get("instrument"),
                            "instrument_source": staff.get("instrument_source"),
                            "current_clef": trace.get("current_clef"),
                            "proposed_clef": trace.get("chosen"),
                            "b1_within_cell": b1, "b2_flip": b2,
                            "clef_source": staff.get("clef_source"),
                        })
        rows.append(row)

    pooled = {k: sum(r[k] for r in rows) for k in
              ("staves", "A_contest", "B1_within_cell", "B2_flip",
               "B2_mid_staff", "B2_overturn", "OVER_and_reachable",
               "OVER_and_label", "B_differs", "C_reachable",
               "BC_differs_and_reachable", "MID_and_reachable",
               "MID_uncovered", "C_label", "BC_label", "MID_and_label",
               "D_actionable")}
    docs = sorted({r["document"] for r in rows})
    return {
        "n_files": len(rows), "n_documents": len(docs), "documents": docs,
        "rows": rows, "pooled": pooled,
        "propose_clef_exits": dict(exits.most_common()),
        "propose_clef_exits_over_contested_reachable": dict(exits_bc.most_common()),
        "cross_checks": xcheck,
        "actionable_detail": actionable_detail,
        "mid_staff_flip_detail": mid_detail,
    }


def _print(report: dict[str, Any]) -> None:
    hdr = (f"{'row_id':34s} {'stav':>5s} {'A':>4s} {'B1':>4s} {'B2':>4s} "
           f"{'B2mid':>6s} {'OVER':>5s} {'OV&C':>5s} {'OV&Cl':>6s} {'B':>4s} {'C':>4s} {'Clab':>5s} {'B&C':>4s} "
           f"{'B&Cl':>5s} {'MID&C':>6s} {'MID&Cl':>7s} {'unc':>4s} {'D':>3s}")
    print(hdr)
    print("-" * len(hdr))
    for r in report["rows"]:
        print(f"{r['row_id']:34s} {r['staves']:>5d} {r['A_contest']:>4d} "
              f"{r['B1_within_cell']:>4d} {r['B2_flip']:>4d} "
              f"{r['B2_mid_staff']:>6d} {r['B2_overturn']:>5d} "
              f"{r['OVER_and_reachable']:>5d} {r['OVER_and_label']:>6d} "
              f"{r['B_differs']:>4d} "
              f"{r['C_reachable']:>4d} {r['C_label']:>5d} "
              f"{r['BC_differs_and_reachable']:>4d} {r['BC_label']:>5d} "
              f"{r['MID_and_reachable']:>6d} {r['MID_and_label']:>7d} "
              f"{r['MID_uncovered']:>4d} {r['D_actionable']:>3d}")
    p_ = report["pooled"]
    print("-" * len(hdr))
    print(f"{'POOLED':34s} {p_['staves']:>5d} {p_['A_contest']:>4d} "
          f"{p_['B1_within_cell']:>4d} {p_['B2_flip']:>4d} "
          f"{p_['B2_mid_staff']:>6d} {p_['B2_overturn']:>5d} "
          f"{p_['OVER_and_reachable']:>5d} {p_['OVER_and_label']:>6d} "
          f"{p_['B_differs']:>4d} "
          f"{p_['C_reachable']:>4d} {p_['C_label']:>5d} "
          f"{p_['BC_differs_and_reachable']:>4d} {p_['BC_label']:>5d} "
          f"{p_['MID_and_reachable']:>6d} {p_['MID_and_label']:>7d} "
          f"{p_['MID_uncovered']:>4d} {p_['D_actionable']:>3d}")
    print()
    print(f"files {report['n_files']}, DISTINCT DOCUMENTS "
          f"{report['n_documents']}: {', '.join(report['documents'])}")
    print()
    print("A     staff recorded a contest at all")
    print("B1    >= 2 DISTINCT resolved candidate clefs in some cell")
    print("B2    argmax flipped the clef in effect, ANY cell (PRE-REPAIR)")
    print("B2mid ... restricted to a NON-first cell — the first cell's "
          "'before' is the positional")
    print("      default every staff starts under, so a first-cell flip is the "
          "clef being READ, not an error")
    print("OVER  *** THE POPULATION *** flips that overturn a clef a reader "
          "ESTABLISHED — as opposed")
    print("      to a clef finally being READ on a staff that had none "
          "(see `_overturns`)")
    print("OV&C  OVER and C        OV&Cl  OVER and instrument_source=='label'")
    print("B     B1 or B2")
    print("C     clef_correction has an admissible instrument (ITS OWN trace)")
    print("Clab  ... and instrument_source == 'label' — the criterion §7.2 "
          "pre-registered, and the")
    print("      gate the OVERRIDE tier and veto_implausible_clef_changes "
          "both actually require")
    print("B&C   B and C")
    print("B&Cl  B and Clab")
    print("MID&C B2mid and C  — the population a new consumer would be handed")
    print("MID&Cl ... under the pre-registered 'label' gate")
    print("unc   MID&C that the EXISTING consumer "
          "(veto_implausible_clef_changes) would still")
    print("      not handle with its flag on — it needs source=='label' AND "
          "the (instr,from,to)")
    print("      triple in MID_STAFF_CHANGE_VETOES; failing either leaves the "
          "flip uncovered")
    print("D     B and C and the instrument's expected clef disagrees "
          "(propose_clef exit == 'proposed')")
    print()
    print("propose_clef exits over ALL reachable staves:      ",
          report["propose_clef_exits"])
    print("propose_clef exits over CONTESTED+reachable (B&C): ",
          report["propose_clef_exits_over_contested_reachable"])
    print()
    xc = dict(report["cross_checks"])
    expected = xc.pop("disagrees_top2_vs_distinct_EXPECTED_NONZERO", 0)
    print("cross-checks (ALL MUST BE 0):", xc)
    print(f"  `disagrees` top-2 vs distinct-clef recomputation: {expected} "
          f"(explained, not a fault — see the module docstring)")
    mid = report["mid_staff_flip_detail"]
    print()
    print(f"MID-STAFF FLIPS: {len(mid)} across "
          f"{len({(m['row_id'], m['staff_index']) for m in mid})} staves")
    for m in mid:
        print("  " + json.dumps(m))
    if report["actionable_detail"]:
        print()
        print("ACTIONABLE (column D):")
        for d in report["actionable_detail"]:
            print("  " + json.dumps(d))


def _self_test() -> int:
    """Synthetic staves with known answers, for the counting logic itself.

    The corpus cannot falsify a counting bug: a double-count and a real
    population look identical in a total. These fixtures pin the two rules the
    totals depend on — the first-cell/staff-level DEDUP, and the
    first-cell-vs-mid-staff SPLIT — and each is written so it FAILS if the rule
    is dropped.
    """
    def contest(before, after, cands=(), n_res=1):
        c = {"clef_in_effect_before": before, "clef_in_effect_after": after,
             "candidates": [{"clef": x, "resolved": True} for x in cands],
             "n_resolved": n_res, "winner": after}
        return c

    # 1. The first cell's contest appears at BOTH sites and must count ONCE.
    opening = contest("treble", "bass")
    staff = {
        "staff_index": 0, "instrument": "Bassoon", "instrument_source": "label",
        "clef_evidence": {"contest": opening},
        "clef_proposal_evidence": {"exit": "already_in_effect"},
        "measures": [{"measure_index": 7, "clef_evidence": {"contest": opening}}],
    }
    got = _contests(staff)
    assert len(got) == 1, f"dedup failed: {len(got)} contests, expected 1"
    assert got[0][2] is True, "the shared record is the FIRST cell"
    # ⚠️ measure_index is 7, not 0 — an index-keyed dedup would double-count.

    # 2. A later cell's flip is MID-STAFF; the opening flip is not.
    mid = contest("alto", "bass")
    staff2 = {
        "staff_index": 1, "instrument": "Viola", "instrument_source": "label",
        "clef_evidence": {"contest": contest("treble", "alto")},
        "clef_proposal_evidence": {"exit": "already_in_effect"},
        "measures": [
            {"measure_index": 0, "clef_evidence": {"contest": contest("treble", "alto")}},
            {"measure_index": 4, "clef_evidence": {"contest": mid}},
        ],
    }
    cs = _contests(staff2)
    assert len(cs) == 2, f"expected 2 contests, got {len(cs)}"
    assert [f for _w, _c, f in cs] == [True, False], "first-cell split wrong"
    assert sum(_flip(c) for _w, c, _f in cs) == 2, "both flip"
    assert sum(_flip(c) for _w, c, f in cs if not f) == 1, "ONE is mid-staff"

    # 3. Reachability: the two routes must agree, and score_order is refused.
    assert _reachable_by_trace(staff2) and _reachable_by_fields(staff2)
    so = {"instrument": "Oboe", "instrument_source": "score_order"}
    assert not _reachable_by_fields(so) and not _reachable_by_trace(so)

    # 4. B1 is recomputed, not read off `disagrees`.
    assert _within_cell_differs(contest("treble", "alto", ("alto", "treble"), 2))
    assert not _within_cell_differs(contest("treble", "treble", ("treble", "treble"), 2))

    # 5. establish vs overturn, and the PREPEND ordering that makes it right.
    #    Mirrors dvorak p5: cell 0 recorded a contest with NO candidates and no
    #    `clef_in_effect_after`, and it did not survive into `measures`.
    opening_blank = {"candidates": [], "n_candidates": 0, "n_resolved": 0,
                     "winner": None, "clef_in_effect_before": "treble",
                     "read_clef_rung_ran": True}
    later = contest("treble", "bass")
    staff3 = {
        "staff_index": 2, "instrument": "Bassoon", "instrument_source": "label",
        "clef_evidence": {"contest": opening_blank},
        "clef_proposal_evidence": {"exit": "already_in_effect"},
        "measures": [{"measure_index": 0, "clef_evidence": {"contest": later}}],
    }
    cs3 = _contests(staff3)
    assert cs3[0][0] == "staff", "cell 0 must come FIRST even when its measure is gone"
    assert _overturns(cs3) == 0, (
        "a clef read after nothing was read ESTABLISHES; it does not overturn")

    # A real overturn: alto established, then bass.
    staff4 = {
        "staff_index": 3, "instrument": "Viola", "instrument_source": "label",
        "clef_evidence": {"contest": contest("treble", "alto")},
        "clef_proposal_evidence": {"exit": "already_in_effect"},
        "measures": [
            {"measure_index": 0, "clef_evidence": {"contest": contest("treble", "alto")}},
            {"measure_index": 4, "clef_evidence": {"contest": contest("alto", "bass")}},
        ],
    }
    assert _overturns(_contests(staff4)) == 1, "alto->bass after alto IS an overturn"
    # and the opening treble->alto alone is not
    assert _overturns(_contests(staff2)) == 1

    print("self-test OK: dedup, first-cell split, reachability, B1, "
          "establish-vs-overturn, cell-0 ordering")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fixtures", nargs="*", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="check the counting logic on synthetic staves")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    try:
        report = analyse(args.fixtures)
    except BadInput as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        _print(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
