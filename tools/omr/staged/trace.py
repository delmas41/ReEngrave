"""What did each STAGE do to THIS symbol — and to this family, step by step.

Sean, 2026-09-18: *"I think we need a systematic process for walking each
symbol through the whole process and testing what each stage does to the
recognition. ... I don't think we are close to knowing what every stage does
and at every turn we are continually surprised by what info is going or not
going somewhere, even though we have spent a lot of time mapping it all out
and theoretically have checked all of the connections."*

⚠️⚠️ **WHY THE TEN EXISTING CHECKS DO NOT ANSWER HIM, AND THIS IS THE WHOLE
DESIGN ARGUMENT.** `inventory`, `health`, `gather_coverage`, `export_coverage`,
`wiring`, `capture`, `reach`, `record_coverage`, `brakes` and `no_producer` are
every one of them AGGREGATE and STATIC. They ask *is a declared input read
where it is filed*, *does any reader read this quantity*, *what does no family
claim*, *was this refusal's premise overtaken*. **Not one of them can be given
a subject and asked what happened to it** — checked before this module was
written: the complete set of value-taking options across all ten is `--out`,
`--run`, `--root`, `--scan`. So the connections are verified in the abstract
and nothing replays one symbol's journey, which is exactly the gap Sean names:
*the mapping is checked and the surprises continue.*

CLAUDE.md's five-stages section traces ONE real note (`glyph/1/0/2/4/1`) by
hand, in prose, in a plan document. **This automates that trace.**

    python3 -m tools.omr.staged.trace --check
    python3 -m tools.omr.staged.trace --run rec.json --subject glyph/1/0/2/4/1
    python3 -m tools.omr.staged.trace --run rec.json --family note
    python3 -m tools.omr.staged.trace --run rec.json --empty-claims

⚠️ **NOT A DUPLICATE OF `score_translation.funnel`, and that was checked rather
than assumed.** That funnel is *detected → exported → truth* per family over a
LEGACY `read.omr.json`, and its question is *which half of the pipeline lost
this*. This one is *ink → detections → gathered → adjudicated → evaluated →
inferred → written* over a STAGED record, and its question is *what did each
STAGE do*. Different substrate, different columns, no overlap in what either
can answer. `no_producer.Report.funnel` is a narrowing funnel over the call
graph and is the SHAPE this one copies — labelled steps, each a strict subset
of the one above, with the reach printed first.

⚠️⚠️ **THREE THINGS THIS DELIBERATELY DOES NOT DO.**

1. **It does not re-implement the exporter's refusal ladder.** It calls
   `export.to_musicxml` and reads `report["notes_not_written"]`. The
   alternative has been tried and is recorded in `_place_notes`' own
   docstring: `benchmarks/omr-cleanup-count-2026-09/build_sheet.py` held its
   own copy of "the three refusals in order", the exporter grew to five, and
   it reported 542 held-back notes where the real rule refuses 738. **A second
   copy of a rule is how the two drift**, so the EXPORT step of the funnel is
   the exporter's own answer or it is an ABSTENTION.
2. **It does not claim an ABLATION.** Sean asked to *"walk through adding each
   step progressively"*, and that cannot be run literally: EXPORT reads
   ADJUDICATE's verdicts, so there is no *GATHER only, exported* arm. What IS
   switchable is named in `ABLATABLE` below, derived from the flag predicates
   and the rule registries, and the funnel reports what each stage DID rather
   than what the pipeline would score without it. Saying otherwise would be
   this repo's own *a control that computes the wrong thing*.
3. **It does not net a stage's moves.** CLAUDE.md's worked example is
   ADJUDICATE reading a note as a QUARTER against the detector's own class and
   EVALUATE's `reconcile_duration` correcting it back to a half — *"so
   ADJUDICATE was wrong and EVALUATE fixed it."* A funnel reporting only net
   change per stage shows EVALUATE contributing nothing there. So every
   supersession is classified by DIRECTION (`changed` / `restated` /
   `filled_an_abstention` / `collapsed_a_narrowing`) and the classes are
   reported apart. ⚠️ **Which direction was RIGHT is not answerable here** —
   it needs a truth this record has none of; see `WHAT_THIS_CANNOT_SEE`.

⚠️ **`DERIVED_CHECK = True`**, for the reason `capture.py` paid for: an
auditor NAMES the detail keys and reason words it reports on without CONSUMING
them, and it lives in the same tree as the real consumers, so without the
marker `wiring --check` would read live gap entries as STALE. `wiring --check`
exits 0 before and after this module — run both; *checks fail after a change*
and *checks were already failing* look identical in a terminal.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import adjudicate as A
from . import evaluate as E
from . import export as X
from . import infer as INF
from . import reach as RCH
from .record import ABSTAIN, Q, Subject

#: ⚠️ THIS MODULE NAMES REASON WORDS, DETAIL KEYS AND QUANTITIES WITHOUT
#: CONSUMING THEM. See the module docstring; the marker must be a bare
#: module-level assignment of the literal `True` or `wiring._declares_derived_check`
#: will not see it.
DERIVED_CHECK = True


# ─────────────────────────────────────────────────────────────────────────────
# The stage map — DERIVED, and total or loud
# ─────────────────────────────────────────────────────────────────────────────

#: Stages that WRITE ROWS, in pipeline order. ⚠️ Taken from `reach.ORDER`
#: rather than spelled here, so a new stage appears without an edit. EXPORT
#: and HARNESS write no rows and are dropped by `_ROW_WRITING`.
_NOT_ROW_WRITING = frozenset({"EXPORT", "HARNESS"})


def row_writing_stages() -> Tuple[str, ...]:
    """The stages a row in the record can have come from."""
    return tuple(s for s in RCH.ORDER if s not in _NOT_ROW_WRITING)


def deciders_by_stage() -> Dict[str, frozenset]:
    """Which `decider` strings belong to which stage — derived three ways.

    ⚠️ ADJUDICATE stamps `decider=spec.name` (`adjudicate.py:714`), so the set
    is `REGISTRY`'s own names. EVALUATE's `Rule` carries no name field, so the
    set is `rule.fn.__name__` — which matches the `decider=` literal at every
    consequence site today, and where it ever stops matching the decider lands
    in `UNATTRIBUTED` and `--check` fails. That is the derivation carrying its
    own falsifier rather than a hand-kept table.

    ⚠️ INFER is a PREFIX, not a set: `infer.py` stamps
    `decider=f"{DECIDER_PREFIX}{rule.value}"` so that no inference can reach
    the log unstamped, and a prefix test is the same claim the stage's own
    harness makes.
    """
    A._ensure_decisions()
    E._ensure_rules()
    return {
        "ADJUDICATE": frozenset(s.name for s in A.REGISTRY.values()),
        "EVALUATE": frozenset(r.fn.__name__ for r in E.RULES),
    }


def stage_of_decider(decider: str) -> str:
    """Which stage wrote a verdict — or `UNATTRIBUTED`, which is a finding.

    ⚠️ NO FALLBACK TO A GUESS. A decider nobody claims is reported by name;
    converting *cannot tell* into *probably ADJUDICATE* is the fallback this
    repo refuses everywhere else, and here it would silently mis-attribute a
    whole stage's work.
    """
    if decider and str(decider).startswith(INF.DECIDER_PREFIX):
        return "INFER"
    by = deciders_by_stage()
    for stage, names in by.items():
        if decider in names:
            return stage
    return "UNATTRIBUTED"


#: What can be genuinely SWITCHED OFF and re-run, as against only traced.
#: ⚠️ DERIVED from what actually has an off switch. Sean's *"add each step
#: progressively"* is not available for the rest, and pretending it is would
#: be the worst outcome of this job — see the module docstring.
def ablatable() -> Dict[str, str]:
    """Stage or rule -> how it is switched off. Everything else is TRACE-ONLY."""
    out: Dict[str, str] = {
        "INFER": f"{INF.INFER_ENV}=0 (default off; the stage is ABSENT, "
                 "not quiet)",
    }
    E._ensure_rules()
    for r in E.RULES:
        if r.stub:
            out[f"EVALUATE/{r.fn.__name__}"] = "declared stub: abstains already"
    return out


#: ⚠️ WHAT THIS INSTRUMENT CANNOT SEE, stated in the module rather than only in
#: a findings file, because the next reader runs the tool without reading the
#: write-up.
WHAT_THIS_CANNOT_SEE: Tuple[str, ...] = (
    "ACCURACY. Every direction here is a direction of CHANGE, never of "
    "CORRECTNESS: a stage that overturns a reading is reported as having "
    "overturned it, and whether it was right needs a truth the shared "
    "records have none of (both are SCANS; page_truth exists only for a page "
    "we RENDER).",
    "A GATHER CHANGE. The trace reads a SAVED record, so a quantity that was "
    "not gathered leaves no row and is indistinguishable from one gathered "
    "and empty -- which is the ABSENT/DECLINED collapse, one level up. Two "
    "full re-gathers are the only instrument for that.",
    "WHETHER A ROW IS RIGHT ABOUT THE INK. The empty-claims question uses "
    "Q.INK as an independent witness that ink is PRESENT; it says nothing "
    "about whether the ink is of the kind the refusing reader wanted.",
    "THE DETECTOR. Everything upstream of the first row is invisible: a "
    "notehead the detector never fired on produces no Q.GLYPH_BOX and so no "
    "step of any funnel below.",
)


# ─────────────────────────────────────────────────────────────────────────────
# Q1 — the per-subject trace
# ─────────────────────────────────────────────────────────────────────────────


def _rows_at(rec: X.Record, key: str) -> Dict[str, List[dict]]:
    """Every row filed AT this exact subject, bucketed by row type."""
    out: Dict[str, List[dict]] = {"observations": [], "abstentions": [],
                                  "verdicts": []}
    for o in rec.observations:
        if o["subject"] == key:
            out["observations"].append(o)
    for a in rec.abstentions:
        if a["subject"] == key:
            out["abstentions"].append(a)
    for v in rec.verdicts:
        if v["subject"] == key:
            out["verdicts"].append(v)
    return out


def trace(rec: X.Record, key: str, *,
          export_report: Optional[dict] = None) -> Dict[str, Any]:
    """One symbol's whole journey, in stage order, on one screen.

    ⚠️ The ANCESTORS are walked too, and that is not decoration: a glyph's
    duration is decided on the glyph, its meter on the SYSTEM and its bar
    count on the STAFF, so a trace that showed only the exact subject would
    report a note whose whole context was decided elsewhere as having had
    almost nothing done to it.
    """
    sub = Subject.from_key(key)
    own = _rows_at(rec, key)

    # Ancestors, nearest first -- `Subject.ancestors()` returns them and the
    # trace reports each separately rather than pooling, because "decided on
    # this glyph" and "inherited from its system" are different facts.
    context: List[Dict[str, Any]] = []
    for anc in sub.ancestors():
        akey = anc.to_key()
        rows = _rows_at(rec, akey)
        if any(rows.values()):
            context.append({"subject": akey, "kind": anc.kind.value,
                            **{k: len(v) for k, v in rows.items()},
                            "verdicts": [_verdict_line(v) for v in rows["verdicts"]]})

    by_id = {v["id"]: v for v in rec.verdicts}
    steps: List[Dict[str, Any]] = []

    # GATHER
    for o in sorted(own["observations"], key=lambda r: r["id"]):
        steps.append({
            "stage": "GATHER", "row": "observation", "id": o["id"],
            "quantity": o["quantity"], "reader": o["reader"],
            "frame": o["frame"], "score": o.get("score"),
            "value": _short(o["value"]),
            "detail_keys": sorted(o.get("detail") or {}),
        })
    for a in sorted(own["abstentions"], key=lambda r: r["id"]):
        steps.append({
            "stage": "GATHER", "row": "abstention", "id": a["id"],
            "quantity": a["quantity"], "reader": a["reader"],
            "frame": a["frame"], "reason": a["reason"],
            "detail_keys": sorted(a.get("detail") or {}),
        })

    # ADJUDICATE / EVALUATE / INFER -- one bucket per stage, ordered by the
    # stage order rather than by row id, so the screen reads downhill.
    per_stage: Dict[str, List[dict]] = collections.defaultdict(list)
    for v in own["verdicts"]:
        per_stage[stage_of_decider(v["decider"])].append(v)
    for stage in row_writing_stages():
        if stage == "GATHER":
            continue
        for v in sorted(per_stage.get(stage, []), key=lambda r: r["id"]):
            steps.append(_verdict_step(stage, v, by_id))
    for v in sorted(per_stage.get("UNATTRIBUTED", []), key=lambda r: r["id"]):
        steps.append(_verdict_step("UNATTRIBUTED", v, by_id))

    out: Dict[str, Any] = {
        "subject": key, "kind": sub.kind.value,
        "steps": steps, "context": context,
        "n_rows_at_subject": sum(len(v) for v in own.values()),
    }
    out["export"] = _export_outcome(rec, key, export_report)
    return out


def _verdict_step(stage: str, v: dict, by_id: Dict[str, dict]) -> Dict[str, Any]:
    """One verdict, with what it READ, what it MISSED, and what it OVERTURNED."""
    step: Dict[str, Any] = {
        "stage": stage, "row": "verdict", "id": v["id"],
        "quantity": v["quantity"], "decider": v["decider"],
        "outcome": v["outcome"], "reason": v["reason"],
        "value": _short(v.get("value")),
        "read": list(v.get("used") or ()) or list(v.get("considered") or ()),
        "considered": len(v.get("considered") or ()),
        "used": len(v.get("used") or ()),
        "missing": list(v.get("missing") or ()),
        "declined": list(v.get("declined") or ()),
        "excluded": [list(e) for e in (v.get("excluded") or ())],
        "correlated_groups": len(v.get("correlated") or ()),
        "basis": len(v.get("basis") or ()),
        "candidates": [c for c in (v.get("candidates") or ())],
        "margin": v.get("margin"),
        "detail_keys": sorted(v.get("detail") or {}),
    }
    sup = v.get("supersedes")
    if sup:
        prior = by_id.get(sup)
        step["supersedes"] = {
            "id": sup,
            "prior_outcome": prior["outcome"] if prior else None,
            "prior_value": _short(prior.get("value")) if prior else None,
            "prior_decider": prior["decider"] if prior else None,
            "direction": _direction(prior, v),
        }
    return step


def _direction(prior: Optional[dict], now: dict) -> str:
    """HOW a supersession moved the answer. ⚠️ NEVER whether it moved it RIGHT.

    Four classes, kept apart because the repairs differ and because netting
    them is how a stage that corrects an earlier stage reads as contributing
    nothing -- CLAUDE.md's own worked example.
    """
    if prior is None:
        return "prior_row_absent"
    po, no = prior["outcome"], now["outcome"]
    if po == "abstained" and no != "abstained":
        return "filled_an_abstention"
    if po == "narrowed" and no == "decided":
        return "collapsed_a_narrowing"
    if no == "abstained" and po != "abstained":
        return "withdrew_an_answer"
    if prior.get("value") == now.get("value"):
        return "restated_same_value"
    return "changed_the_value"


#: Reasons `_place_notes` refuses a note, DERIVED from the counter keys the
#: real exporter writes. ⚠️ NOT a list of the refusals: the funnel reads
#: whatever keys the exporter reports, so a refusal added later appears
#: without an edit here. This is only used to say which of them is ABOUT a
#: notehead rather than about an arc or a wedge.
_NOTE_DROP_PREFIXES = ("arc_", "wedge_", "artic_", "fermata_", "ornament_",
                       "kind_")


def _is_note_drop(reason: str) -> bool:
    return not reason.startswith(_NOTE_DROP_PREFIXES)


def _export_outcome(rec: X.Record, key: str,
                    report: Optional[dict]) -> Dict[str, Any]:
    """Did this subject reach the file — the EXPORTER's answer, never ours.

    ⚠️ ABSTAINS when no report was supplied. `"not written"` and `"nobody
    asked the exporter"` are different facts and a fallback that returned the
    first would be the exact conversion of *cannot tell* into a definite
    answer this project refuses.
    """
    if report is None:
        return {"state": "declined",
                "reason": "no export report supplied (--export to run it)"}
    # The exporter counts refusals BY REASON, not by subject, so a per-subject
    # answer is only available for the reasons whose test this module can
    # re-ask WITHOUT re-implementing the ladder: the verdicts the refusal
    # reads. Anything else is reported as unknown-for-this-subject.
    drops = report.get("notes_not_written") or {}
    return {"state": "report_is_by_reason_not_by_subject",
            "note": "the exporter counts refusals by REASON; per-subject "
                    "attribution would mean re-implementing the ladder, "
                    "which is the drift `_place_notes` documents",
            "note_drops": {k: v for k, v in drops.items() if _is_note_drop(k)}}


def _short(value: Any, limit: int = 90) -> Any:
    """A value small enough to print. ⚠️ Truncation is MARKED, never silent."""
    if isinstance(value, (list, tuple)) and len(value) > 8:
        return list(value[:8]) + [f"...+{len(value) - 8} more"]
    s = repr(value)
    if len(s) > limit:
        return s[:limit] + f"...(+{len(s) - limit} chars)"
    return value


def _verdict_line(v: dict) -> str:
    return (f"{v['quantity']}={_short(v.get('value'))} "
            f"[{v['outcome']}/{v['reason']}] by {v['decider']}")


# ─────────────────────────────────────────────────────────────────────────────
# Q2 — the per-family stage funnel
# ─────────────────────────────────────────────────────────────────────────────


def family_quantities(family: str) -> Dict[str, Any]:
    """Which quantities a family's journey runs through — DERIVED.

    ⚠️ From `export.FAMILIES` (the deciding quantity), then that decision's
    own `subjects_from` (its POPULATION, which is what makes the funnel's
    first step the family's ink rather than every glyph on the page), then
    every quantity any registered decision or consequence writes on the same
    subject KIND. A hand list would rot the way this repo's hand lists have.
    """
    A._ensure_decisions()
    E._ensure_rules()
    if family not in X.FAMILIES:
        raise KeyError(
            f"{family!r} is not a family. Known: {sorted(X.FAMILIES)} "
            "(derived from export.FAMILIES, never restated here)")
    quantity, prefixes, counters = X.FAMILIES[family]
    spec = A.REGISTRY.get(quantity) if quantity else None
    population: Tuple[str, ...] = ()
    if spec is not None and spec.subjects_from:
        sf = spec.subjects_from
        population = (sf,) if isinstance(sf, str) else tuple(sf)
    return {"family": family, "deciding_quantity": quantity,
            "detector_prefixes": list(prefixes), "counters": list(counters),
            "population_quantities": list(population),
            "scope": spec.scope.value if spec is not None else None}


def funnel(rec: X.Record, family: str, *,
           export_report: Optional[dict] = None) -> Dict[str, Any]:
    """Ink -> detections -> gathered -> decided -> consequences -> inferred ->
    written, with the loss attributed AT EACH STEP and the steps a PARTITION.

    ⚠️ EVERY STEP BALANCES OR SAYS IT DOES NOT. Each `stage` row carries
    `n_in`, its outcome buckets, and `unaccounted` -- and `balanced` is an
    EQUALITY, never a `<=`. CLAUDE.md records what a `<=` bought the last time
    one was written into a control here: ten decided hairpins accounted for
    NOWHERE while the report said `balanced: True`.
    """
    meta = family_quantities(family)
    pops = meta["population_quantities"]
    if not pops:
        return {**meta, "reach": 0, "dead": True,
                "why": "this family's decision names no `subjects_from`, so "
                       "its population is every subject at its scope and "
                       "this funnel has no first step to stand on"}

    # ── step 0: the POPULATION -- the family's own ink, as GATHER filed it.
    subjects: set = set()
    for q in pops:
        for o in rec.obs_of(q):
            subjects.add(o["subject"])
    reach = len(subjects)

    cells = {s: _cell_of(s) for s in subjects}

    # ── step -1: the INK under those cells, where the ink layer ran.
    ink_cells = {_cell_of(o["subject"]) for o in rec.obs_of(Q.INK)}
    ink_cells.discard(None)
    ink_rows = len(rec.obs_of(Q.INK))

    # ── the stage steps.
    by_id = {v["id"]: v for v in rec.verdicts}
    per_q: Dict[str, Dict[str, List[dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for v in rec.verdicts:
        if v["subject"] in subjects:
            per_q[v["quantity"]][stage_of_decider(v["decider"])].append(v)

    stages: List[Dict[str, Any]] = []
    for quantity in sorted(per_q):
        for stage in list(row_writing_stages()) + ["UNATTRIBUTED"]:
            rows = per_q[quantity].get(stage)
            if not rows:
                continue
            stages.append(_stage_row(stage, quantity, rows, by_id, reach))

    # ── GATHER's own refusals ON the population's subjects and their cells.
    gather_ab: Dict[str, int] = collections.Counter()
    for a in rec.abstentions:
        if a["subject"] in subjects:
            gather_ab[f"{a['quantity']}/{a['reason']}"] += 1

    out: Dict[str, Any] = {
        **meta,
        "reach": reach,
        "dead": reach == 0,
        "ink": {"rows": ink_rows, "cells_with_ink": len(ink_cells),
                "population_cells": len(set(cells.values()) - {None}),
                "population_cells_with_ink": len(
                    (set(cells.values()) - {None}) & ink_cells)},
        "stages": stages,
        "gather_abstentions_on_the_population": dict(
            sorted(gather_ab.items(), key=lambda kv: -kv[1])),
    }
    out["export"] = _export_step(rec, family, reach, export_report)
    return out


def _stage_row(stage: str, quantity: str, rows: List[dict],
               by_id: Dict[str, dict], n_population: int) -> Dict[str, Any]:
    """One (stage, quantity) step of the funnel, as a PARTITION."""
    out_by = collections.Counter(r["outcome"] for r in rows)
    reasons = collections.Counter(
        f"{r['outcome']}/{r['reason']}" for r in rows)
    directions = collections.Counter()
    for r in rows:
        sup = r.get("supersedes")
        if sup:
            directions[_direction(by_id.get(sup), r)] += 1
        else:
            directions["first_answer"] += 1
    known = {"decided", "narrowed", "abstained"}
    unaccounted = [r["id"] for r in rows if r["outcome"] not in known]
    row = {
        "stage": stage, "quantity": quantity,
        "n_in": len(rows),
        "decided": out_by.get("decided", 0),
        "narrowed": out_by.get("narrowed", 0),
        "abstained": out_by.get("abstained", 0),
        "unaccounted": unaccounted,
        "share_of_population": (round(len(rows) / n_population, 4)
                                if n_population else None),
        # ⚠️ BOTH DIRECTIONS, NEVER THE NET. See `_direction`.
        "directions": dict(directions.most_common()),
        "reasons": dict(reasons.most_common(10)),
    }
    row["balanced"] = (row["decided"] + row["narrowed"] + row["abstained"]
                       + len(unaccounted) == row["n_in"])
    return row


def _export_step(rec: X.Record, family: str, reach: int,
                 report: Optional[dict]) -> Dict[str, Any]:
    """The last step — and it is the EXPORTER's own count, or an abstention."""
    if report is None:
        return {"state": "declined",
                "reason": "no export report; pass --export to run the real "
                          "exporter. This step is NEVER re-derived here -- "
                          "see the module docstring."}
    counters = X.FAMILIES[family][2]
    written = {c: report.get(c) for c in counters}
    drops = report.get("notes_not_written") or {}
    note_drops = {k: v for k, v in drops.items() if _is_note_drop(k)}
    total = report.get("notes_not_written_total")
    out = {"state": "read_from_the_exporter",
           "written": written,
           "refused_by_reason": note_drops,
           "refused_total_all_families": total,
           "balance": report.get("balance") or report.get("accounting")}
    if family == "note":
        w = written.get("notes")
        refused = sum(note_drops.values())
        out["partition"] = {
            "population": reach, "written": w, "refused": refused,
            "unexplained": (None if w is None else reach - w - refused),
        }
    return out


def _cell_of(key: str) -> Optional[str]:
    """The CELL a glyph-or-cell subject belongs to, or None.

    ⚠️ A cell index RESTARTS on each system of a page, so the key must carry
    page AND system AND staff -- the `(page, cell)` defect that made a
    duration arm's bar figures wrong.
    """
    parts = key.split("/")
    if parts[0] in ("cell", "glyph") and len(parts) >= 5:
        return "cell/" + "/".join(parts[1:5])
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Q3 — a stage claims the page is EMPTY while a witness shows ink
# ─────────────────────────────────────────────────────────────────────────────

#: Reason words that make a claim about THE INK rather than about the reader.
#: ⚠️ DERIVED from the vocabulary by the word itself: a reason containing the
#: token `ink` claims something about ink. `no_mask` is excluded by that test
#: for the right reason -- it names the missing ERASED IMAGE, which is an
#: honest claim about the reader's input and not about the page.
def ink_claiming_reasons() -> frozenset:
    return frozenset(r for r in ABSTAIN.all() if "ink" in r.split("_"))


#: The rest of the vocabulary's *nothing to read* family, reported as CONTEXT
#: and never counted as a contradiction. ⚠️ `no_detections` is an HONEST claim
#: -- the detector fired nothing -- and folding it in would report a working
#: reader as a fault. Keeping them apart is the same move `NO_READING` was
#: added for.
_HONEST_EMPTY = (ABSTAIN.NO_DETECTIONS, ABSTAIN.NO_TEXT_LAYER,
                 ABSTAIN.READER_UNAVAILABLE, ABSTAIN.BUDGET_EXHAUSTED,
                 ABSTAIN.NO_MASK)


def empty_claims(rec: X.Record) -> Dict[str, Any]:
    """Where does a stage say *no ink* while an independent reader shows ink?

    ⚠️⚠️ **`Q.INK` IS THE WITNESS, AND IT IS INDEPENDENT BECAUSE NOTHING READS
    IT.** It is default-ON since 2026-09-17, one row per connected piece of a
    cell's staff-line-erased ink, with no size, shape or confidence filter --
    and no adjudicator, consequence, inference or exporter consumes it
    (checked). So it cannot have been tuned to agree with anything, and using
    it here is a legitimate first consumer of a producer-only quantity rather
    than a second opinion from the same machinery.

    ⚠️ `Q.INK`'s OWN `no_ink` is the one honest use of the word and is
    EXCLUDED from the contradicted set -- it measured the components and found
    none. Counting it would be the instrument contradicting itself.

    ⚠️ ONE-SIDED. Ink being present does not mean ink of the refusing
    reader's own kind is present. What this establishes is narrower and still
    load-bearing: the reason word says the page is empty, and the page is not.
    """
    claiming = ink_claiming_reasons()

    ink_cells: set = set()
    for o in rec.obs_of(Q.INK):
        c = _cell_of(o["subject"])
        if c:
            ink_cells.add(c)
    glyph_cells: set = set()
    for o in rec.obs_of(Q.GLYPH_BOX):
        c = _cell_of(o["subject"])
        if c:
            glyph_cells.add(c)

    contradicted: Dict[str, int] = collections.Counter()
    by_quantity: Dict[str, int] = collections.Counter()
    witness_mix: Dict[str, int] = collections.Counter()
    examples: Dict[str, List[str]] = collections.defaultdict(list)
    honest_ink_rows = 0
    all_claims = 0
    context: Dict[str, int] = collections.Counter()

    for a in rec.abstentions:
        reason, quantity = a["reason"], a["quantity"]
        if reason in _HONEST_EMPTY:
            context[f"{quantity}/{reason}"] += 1
            continue
        if reason not in claiming:
            continue
        all_claims += 1
        if quantity == Q.INK:
            honest_ink_rows += 1          # the one reader whose word is true
            continue
        c = _cell_of(a["subject"]) or (
            a["subject"] if a["subject"].startswith("cell/") else None)
        if c is None:
            continue
        wit = []
        if c in ink_cells:
            wit.append("Q.INK")
        if c in glyph_cells:
            wit.append("Q.GLYPH_BOX")
        if not wit:
            continue
        key = f"{quantity}/{reason}"
        contradicted[key] += 1
        by_quantity[quantity] += 1
        witness_mix["+".join(wit)] += 1
        if len(examples[key]) < 3:
            examples[key].append(a["subject"])

    return {
        "witness": {"quantity": Q.INK, "cells_with_ink": len(ink_cells),
                    "cells_with_a_detection": len(glyph_cells)},
        "ink_claiming_reasons": sorted(claiming),
        "claims_made": all_claims,
        "claims_by_the_ink_reader_itself": honest_ink_rows,
        "contradicted_total": sum(contradicted.values()),
        "contradicted_by_quantity": dict(by_quantity.most_common()),
        "contradicted": dict(contradicted.most_common()),
        "witness_mix": dict(witness_mix.most_common()),
        "examples": {k: v for k, v in examples.items()},
        "honest_empty_context": dict(context.most_common(12)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# The structural check, its controls, and its inventory
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️ AN INVENTORY, NEVER A SUPPRESSION LIST -- the `inventory`/`wiring`/
#: `capture` contract. Every key is a problem-line PREFIX with the reason the
#: gap EXISTS; an entry whose problem no longer appears is STALE and fails
#: `--check`, so a closed gap has to leave.
KNOWN_GAPS: Dict[str, str] = {
    "EXPORT-BY-REASON": (
        "the exporter counts refusals by REASON, not by subject, so a "
        "per-subject EXPORT outcome is unavailable. Closing it means either "
        "the exporter recording the refused subject keys, or this module "
        "re-implementing the ladder -- and the second is the drift "
        "`_place_notes` documents at 542-against-738. OPEN, and it is a "
        "decision for whoever owns export.py."),
    "NO-TRUTH": (
        "no direction of CORRECTNESS is reported, on either publisher, "
        "because both shared records are SCANS and `page_truth` exists only "
        "for a page we RENDER. OPEN: needs an engraved staged record."),
}


def _gap_key(problem: str) -> Optional[str]:
    for key in KNOWN_GAPS:
        if problem.startswith(key):
            return key
    return None


def problems() -> List[str]:
    """Everything this module can say is wrong WITHOUT a record."""
    out: List[str] = []
    A._ensure_decisions()
    E._ensure_rules()

    # ⚠️ THE STAGE MAP MUST BE TOTAL. A decider nobody claims means the
    # derivation has broken, and a broken derivation here silently
    # mis-attributes a whole stage.
    by = deciders_by_stage()
    overlap = by["ADJUDICATE"] & by["EVALUATE"]
    if overlap:
        out.append(f"STAGE-AMBIGUOUS decider(s) claimed by two stages: "
                   f"{sorted(overlap)}")
    for stage, names in by.items():
        for n in sorted(names):
            if stage_of_decider(n) != stage:
                out.append(f"STAGE-UNRESOLVED {n} belongs to {stage} and "
                           f"resolves to {stage_of_decider(n)}")

    # Every family must resolve to quantities, or say why it cannot.
    for fam in sorted(X.FAMILIES):
        try:
            meta = family_quantities(fam)
        except KeyError as exc:                             # pragma: no cover
            out.append(f"FAMILY-UNRESOLVED {fam}: {exc}")
            continue
        if meta["deciding_quantity"] is None:
            out.append(f"FAMILY-NO-QUANTITY {fam} names no deciding quantity")

    # The ink-claiming derivation must find something, or Q3 is dead.
    if not ink_claiming_reasons():
        out.append("VOCABULARY-EMPTY no ABSTAIN reason names ink, so the "
                   "empty-claims question cannot run")

    out.extend(_gap_problems())
    return out


def _gap_problems() -> List[str]:
    """The OPEN entries, restated as problems so `--check` sees them."""
    return [f"{k} {v.split('.')[0]}." for k, v in KNOWN_GAPS.items()]


def unaccounted(probs: List[str]) -> List[str]:
    return [p for p in probs if _gap_key(p) is None]


def stale_gaps(probs: List[str]) -> List[str]:
    return [k for k in KNOWN_GAPS if not any(_gap_key(p) == k for p in probs)]


def controls() -> Dict[str, int]:
    """⚠️ EVERY ONE MUST BE NON-ZERO OR THE QUESTION DID NOT RUN.

    `--check` exits 2 on any zero here, BEFORE it reports a finding. A check
    that cannot fail is worse than no check, and this repo emptied one of its
    own in one line by crediting a test that iterates the registry.
    """
    A._ensure_decisions()
    E._ensure_rules()
    by = deciders_by_stage()
    return {
        "row_writing_stages": len(row_writing_stages()),
        "adjudicate_deciders": len(by["ADJUDICATE"]),
        "evaluate_deciders": len(by["EVALUATE"]),
        "families": len(X.FAMILIES),
        "families_with_a_population": sum(
            1 for f in X.FAMILIES
            if family_quantities(f)["population_quantities"]),
        "ink_claiming_reasons": len(ink_claiming_reasons()),
        "ablatable_entries": len(ablatable()),
        "things_this_cannot_see": len(WHAT_THIS_CANNOT_SEE),
    }


def report() -> Dict[str, Any]:
    probs = problems()
    return {
        "stages": list(row_writing_stages()),
        "deciders_by_stage": {k: sorted(v)
                              for k, v in deciders_by_stage().items()},
        "infer_prefix": INF.DECIDER_PREFIX,
        "ablatable": ablatable(),
        "trace_only": [s for s in row_writing_stages()
                       if s not in ablatable()],
        "families": {f: family_quantities(f) for f in sorted(X.FAMILIES)},
        "cannot_see": list(WHAT_THIS_CANNOT_SEE),
        "problems": probs,
        "unaccounted": unaccounted(probs),
        "stale_gaps": stale_gaps(probs),
        "controls": controls(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────


def render_trace(t: Dict[str, Any]) -> str:
    L = [f"SUBJECT {t['subject']}  ({t['kind']}, {t['n_rows_at_subject']} "
         f"rows filed at it)", ""]
    stage = None
    for s in t["steps"]:
        if s["stage"] != stage:
            stage = s["stage"]
            L.append(f"── {stage} " + "─" * (66 - len(stage)))
        if s["row"] == "observation":
            sc = "" if s["score"] is None else f" score={s['score']}"
            L.append(f"  READ     {s['quantity']:26s} = {s['value']!r}")
            L.append(f"           by {s['reader']} in frame {s['frame']}{sc}"
                     + (f"  detail={s['detail_keys']}" if s["detail_keys"] else ""))
        elif s["row"] == "abstention":
            L.append(f"  DECLINED {s['quantity']:26s}   {s['reason']}")
            L.append(f"           by {s['reader']} in frame {s['frame']}")
        else:
            L.append(f"  {s['outcome'].upper():8s} {s['quantity']:26s} "
                     f"= {s['value']!r}")
            L.append(f"           by {s['decider']}  reason={s['reason']}")
            L.append(f"           read {s['used']} of {s['considered']} rows "
                     f"considered; basis {s['basis']}"
                     + (f"; {s['correlated_groups']} correlated group(s)"
                        if s["correlated_groups"] else ""))
            if s["missing"]:
                L.append(f"           MISSING  {s['missing']}")
            if s["declined"]:
                L.append(f"           DECLINED {s['declined']}")
            if s["excluded"]:
                L.append(f"           EXCLUDED {s['excluded']}")
            if s["candidates"]:
                L.append(f"           candidates {s['candidates']}"
                         + (f"  margin={s['margin']}" if s["margin"] else ""))
            sup = s.get("supersedes")
            if sup:
                L.append(f"           SUPERSEDES {sup['id']} "
                         f"({sup['prior_decider']}: {sup['prior_outcome']}"
                         f"={sup['prior_value']!r}) -> {sup['direction']}")
    L.append("")
    L.append("── CONTEXT (decided on an ANCESTOR, not on this subject) ──────")
    for c in t["context"]:
        L.append(f"  {c['subject']:22s} {c['observations']} read, "
                 f"{c['abstentions']} declined, {len(c['verdicts'])} verdicts")
        for line in c["verdicts"]:
            L.append(f"      {line}")
    L.append("")
    L.append("── EXPORT ──────────────────────────────────────────────────────")
    e = t["export"]
    L.append(f"  {e.get('state')}: {e.get('reason') or e.get('note')}")
    return "\n".join(L)


def render_funnel(f: Dict[str, Any]) -> str:
    L = [f"FAMILY {f['family']}   deciding quantity "
         f"{f['deciding_quantity']}  scope {f['scope']}"]
    L.append(f"POPULATION (its own ink, from `subjects_from`"
             f" {f['population_quantities']}): {f['reach']}")
    if f.get("dead"):
        L.append("⚠️  DEAD: " + str(f.get("why", "reach is zero")))
        return "\n".join(L)
    i = f["ink"]
    L.append(f"INK      Q.INK rows {i['rows']} over {i['cells_with_ink']} "
             f"cells; the population occupies {i['population_cells']} cells, "
             f"{i['population_cells_with_ink']} of which carry ink rows")
    L.append("")
    L.append(f"{'stage':12s} {'quantity':24s} {'n':>6s} {'dec':>6s} "
             f"{'narr':>6s} {'abst':>6s}  directions")
    for s in f["stages"]:
        L.append(f"{s['stage']:12s} {s['quantity']:24s} {s['n_in']:6d} "
                 f"{s['decided']:6d} {s['narrowed']:6d} {s['abstained']:6d}  "
                 f"{s['directions']}")
        if not s["balanced"]:
            L.append(f"   ⚠️ UNBALANCED: {s['unaccounted']}")
        top = list(s["reasons"].items())[:4]
        if top:
            L.append(f"   reasons: {top}")
    ab = f["gather_abstentions_on_the_population"]
    if ab:
        L.append("")
        L.append(f"GATHER declined ON these subjects: {ab}")
    L.append("")
    e = f["export"]
    L.append("EXPORT   " + str(e.get("state")))
    if e.get("reason"):
        L.append("         " + e["reason"])
    if e.get("written"):
        L.append(f"         written  {e['written']}")
    if e.get("partition"):
        L.append(f"         partition {e['partition']}")
    if e.get("refused_by_reason"):
        L.append(f"         refused  {e['refused_by_reason']}")
    return "\n".join(L)


def render_empty(e: Dict[str, Any]) -> str:
    L = ["A STAGE CLAIMS THE PAGE IS EMPTY WHILE A WITNESS SHOWS INK", ""]
    w = e["witness"]
    L.append(f"witness {w['quantity']}: {w['cells_with_ink']} cells carry an "
             f"ink row; {w['cells_with_a_detection']} carry a detection")
    L.append(f"reason words that claim ink is absent (derived): "
             f"{e['ink_claiming_reasons']}")
    L.append(f"such claims on the record: {e['claims_made']}, of which "
             f"{e['claims_by_the_ink_reader_itself']} are the ink reader's "
             f"own (the one honest use, excluded)")
    L.append("")
    L.append(f"⚠️  CONTRADICTED: {e['contradicted_total']}")
    for k, n in e["contradicted"].items():
        L.append(f"     {k:40s} {n}")
    L.append(f"   witness mix: {e['witness_mix']}")
    L.append("")
    L.append("HONEST empty claims, for contrast (a reader saying what it "
             "actually knows):")
    for k, n in e["honest_empty_context"].items():
        L.append(f"     {k:40s} {n}")
    return "\n".join(L)


def render(rep: Dict[str, Any]) -> str:
    L = ["STAGE TRACE — what each stage does to a symbol", ""]
    L.append(f"row-writing stages (derived from reach.ORDER): {rep['stages']}")
    for stage, names in rep["deciders_by_stage"].items():
        L.append(f"  {stage:12s} {len(names)} deciders")
    L.append(f"  INFER        by prefix {rep['infer_prefix']!r}")
    L.append("")
    L.append("GENUINELY ABLATABLE (everything else is TRACE-ONLY):")
    for k, v in rep["ablatable"].items():
        L.append(f"  {k:28s} {v}")
    L.append(f"TRACE-ONLY stages: {rep['trace_only']}")
    L.append("")
    L.append("WHAT THIS CANNOT SEE:")
    for c in rep["cannot_see"]:
        L.append(f"  - {c}")
    L.append("")
    L.append("CONTROLS (any zero => the question did not run):")
    for k, v in rep["controls"].items():
        L.append(f"  {k:34s} {v}")
    L.append("")
    L.append(f"PROBLEMS: {len(rep['problems'])}  "
             f"unaccounted: {len(rep['unaccounted'])}  "
             f"stale gaps: {len(rep['stale_gaps'])}")
    for p in rep["problems"]:
        mark = "OPEN " if _gap_key(p) else "⚠️ NEW"
        L.append(f"  {mark} {p}")
    return "\n".join(L)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _load(path: str) -> X.Record:
    data = json.loads(Path(path).read_text())
    if "record" not in data:
        # ⚠️ RAISES. A record whose envelope we do not recognise must not be
        # read as an empty one -- `wiring.with_run` learned the same lesson,
        # and a filter that silently empties a file looks exactly like a file
        # with nothing in it.
        raise KeyError(
            f"{path} has no 'record' key. A staged record is "
            "{'record': {'observations': [...], ...}}; refusing to guess.")
    return X.Record(data)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    ap.add_argument("--run", help="a saved staged record")
    ap.add_argument("--subject", help="trace ONE subject key, e.g. glyph/1/0/2/4/1")
    ap.add_argument("--family", help="funnel ONE family, e.g. note")
    ap.add_argument("--empty-claims", action="store_true",
                    help="where a stage says 'no ink' and a witness disagrees")
    ap.add_argument("--export", action="store_true",
                    help="run the REAL exporter so the EXPORT step is its "
                         "own answer rather than an abstention")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    if args.run:
        rec = _load(args.run)
        report_obj = None
        if args.export:
            data = json.loads(Path(args.run).read_text())
            _xml, rep = X.to_musicxml(data, with_report=True)
            report_obj = rep
        if args.subject:
            t = trace(rec, args.subject, export_report=report_obj)
            print(json.dumps(t, indent=2, default=str) if args.json
                  else render_trace(t))
            return 0
        if args.family:
            f = funnel(rec, args.family, export_report=report_obj)
            print(json.dumps(f, indent=2, default=str) if args.json
                  else render_funnel(f))
            # ⚠️ REACH BEFORE ACCURACY: a family with no population is a DEAD
            # question and says so with a non-zero exit, so a clean-looking
            # zero can never be read as a result.
            return 3 if f.get("dead") else 0
        if args.empty_claims:
            e = empty_claims(rec)
            print(json.dumps(e, indent=2, default=str) if args.json
                  else render_empty(e))
            return 0
        ap.error("--run needs one of --subject, --family or --empty-claims")

    rep = report()
    print(json.dumps(rep, indent=2, default=str) if args.json else render(rep))
    if args.check:
        zero = [k for k, v in rep["controls"].items() if not v]
        if zero:
            print(f"\n⚠️⚠️ DEAD QUESTION — control(s) at zero: {zero}")
            return 2
        if rep["unaccounted"] or rep["stale_gaps"]:
            print(f"\nunaccounted: {rep['unaccounted']}")
            print(f"stale gaps: {rep['stale_gaps']}")
            return 1
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    sys.exit(main())
