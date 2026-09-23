"""THE FEEDBACK FILE — what a review pass hands the next session.

Sean, 2026-09-23, on why this file and not a corrected score:

    *"I mainly want this information so that we can then use it to determine
    how to refine the build, rules and decisions — structurally. All of the
    info would be given to you to turn into fixes."*

So the unit here is not a note. It is: **a human said X; the stage did Y;
here is the rule that did it, the rows it weighed, and the constraint it
declares it is checked by.** A session reads this file and writes a roadmap
item.

⚠️⚠️ IT MUST BE SELF-EXPLAINING WITHOUT THE RECORD. The record is 300 MB and
lives outside git; the feedback file is committed beside the sidecar. So every
verdict named here carries its own reason, its decider, the decider's declared
`checked_by` / `implicates` / `conventions`, and the OTHER rows it used — not
just an id that would need the record to resolve. A file that can only be read
with the artefact it describes is a pointer, not a finding.

⚠️ A DISAGREEMENT IS NOT AN ERROR COUNT. `factsheet.report` settled this once
already, with the case that proved it: a hand-typed publisher dropped an
umlaut the catalog had right, and the sheet filed the CATALOG as wrong. Which
side is correct is a further act of adjudication that nothing here performs —
the verdict's own value and reason sit beside the human's stance precisely so
that act stays possible.

⚠️ EVERY ACTION APPEARS, INCLUDING THE ONES THAT REACHED NOTHING. A human row
no stage read is the most useful row in the file: it names a place where the
pipeline cannot hear him, which is exactly the structural fix he asked for.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import adjudicate, evaluate, infer
from .. import adjudicators, consequences, inferences      # noqa: F401
from ..record import Q
from . import human_evidence as HE


def _decider_declaration(decider: str) -> dict:
    """What the rule that wrote a verdict DECLARES about itself.

    ⚠️ Read off `adjudicate.REGISTRY` and `conventions.py`, never restated
    here: a second copy of a decision's `checked_by` is how a feedback file
    comes to describe a rule the tree no longer has.
    """
    for quantity, spec in adjudicate.REGISTRY.items():
        if spec.name != decider:
            continue
        out = {"stage": "ADJUDICATE", "quantity": quantity,
               "wants": list(spec.wants), "reasons": list(spec.reasons),
               "checkable": spec.checkable.value,
               "checked_by": list(spec.checked_by),
               "implicates": list(spec.implicates),
               "composed_from": list(spec.composed_from),
               "subjects_from": list(adjudicate.domain_of(spec)),
               "mode": spec.mode.value, "stub": spec.stub}
        out["conventions"] = _conventions_for(quantity)
        return out
    for rule in getattr(evaluate, "RULES", ()):
        if getattr(rule, "name", None) == decider:
            return {"stage": "EVALUATE", "cause": getattr(rule, "cause", None),
                    "effect": getattr(rule, "effect", None),
                    "why": (getattr(rule, "__doc__", None) or "").strip()
                           .splitlines()[:1]}
    for rule in getattr(infer, "RULES", ()):
        if getattr(rule, "name", None) == decider:
            return {"stage": "INFER", "reads": list(getattr(rule, "reads", ())),
                    "writes": getattr(rule, "writes", None),
                    "default_on": bool(getattr(rule, "default_on", False))}
    return {"stage": "UNKNOWN", "decider": decider}


def _conventions_for(quantity: str) -> List[dict]:
    """The engraving conventions the registry says this decision claims."""
    try:
        from ... import conventions as CONV
    except Exception:                                   # pragma: no cover
        return []
    out = []
    for name in dir(CONV):
        if name.startswith("_"):
            continue
        obj = getattr(CONV, name)
        entries = obj.values() if isinstance(obj, dict) else None
        if entries is None:
            continue
        for e in entries:
            fields = e if isinstance(e, dict) else getattr(e, "__dict__", {})
            claimed = str(fields.get("quantity") or fields.get("decision")
                          or "")
            if claimed and claimed == quantity:
                out.append({k: v for k, v in fields.items()
                            if isinstance(v, (str, int, float, bool,
                                              type(None)))})
    return out[:8]


def _standing(record: dict) -> Dict[tuple, dict]:
    """(quantity, subject) -> the standing verdict, superseded rows dropped —
    `export.Record`'s own resolution, reached through `rerun` so there is one
    spelling of it in this package rather than two."""
    from .rerun import _verdict_index
    return _verdict_index(record.get("verdicts") or ())


def _row(record: dict, row_id: str) -> Optional[dict]:
    for key in ("observations", "abstentions"):
        for r in record.get(key) or ():
            if r.get("id") == row_id:
                return r
    for v in record.get("verdicts") or ():
        if v.get("id") == row_id:
            return v
    return None


def _describe_row(record: dict, row_id: str) -> dict:
    r = _row(record, row_id)
    if r is None:
        return {"id": row_id, "resolved": False}
    out = {"id": row_id, "subject": r.get("subject"),
           "quantity": r.get("quantity"), "reader": r.get("reader"),
           "frame": r.get("frame")}
    if "value" in r:
        out["value"] = r.get("value")
    if r.get("reason"):
        out["reason"] = r.get("reason")
    if r.get("score") is not None:
        out["score"] = r.get("score")
    return out


def export_feedback(record_after: dict, ingestion: "HE.Ingestion", diff: Any,
                    out_json: str, *, record_path: Optional[str] = None,
                    sidecar_path: Optional[str] = None) -> dict:
    """Write the session-readable feedback file. Returns it."""
    by_action: Dict[str, dict] = {}
    for a in ingestion.actions:
        by_action[a.id] = {
            "action": a.to_json(),
            "human_rows": [_describe_row(record_after, r) for r in a.rows],
            "verdicts_that_named_it": [],
            "reached_nothing": True,
        }

    # ── which verdicts named which action ──────────────────────────────────
    for hit in getattr(diff, "basis_names_human", ()):
        entry = {
            "verdict": hit["verdict"], "subject": hit["subject"],
            "quantity": hit["quantity"], "stage": hit["stage"],
            "outcome": hit["outcome"], "value": hit["value"],
            "reason": hit["reason"], "decider": hit["decider"],
            "how_the_human_row_reached_it": hit["how"],
            "declares": _decider_declaration(hit["decider"]),
            "in_basis": hit["in_basis"], "in_used": hit["in_used"],
            "other_rows_it_used": [_describe_row(record_after, r)
                                   for r in hit["other_rows_used"]],
        }
        for tag in hit["human_rows"]:
            aid = tag.split(":", 1)[0]
            if aid in by_action:
                by_action[aid]["verdicts_that_named_it"].append(entry)
                by_action[aid]["reached_nothing"] = False

    # ── the disagreements, each with the verdict it disagrees WITH ─────────
    disagreements: List[dict] = []
    after_index = _standing(record_after)
    for a in ingestion.actions:
        if a.kind not in HE.STANCE_KINDS:
            continue
        shown = None
        for rid in a.rows:
            r = _row(record_after, rid)
            if r and r.get("quantity") == Q.HUMAN_VERDICT_STANCE:
                shown = r.get("detail") or {}
        entry = {"action": a.id, "stance": a.kind, "note": a.note,
                 "verdict": (shown or {}).get("verdict_id"),
                 "refused": a.refused}
        if shown:
            # ⚠️⚠️ READ OFF THE HUMAN'S OWN ROW, not by resolving the verdict
            # id against the arm. A verdict id is NOT STABLE across a
            # re-decision (`human_evidence._what_he_was_shown`), so the id
            # resolves to a different verdict in the arm — plausibly, which is
            # worse. What he disagreed with travels on his row.
            decider = shown.get("verdict_decider") or ""
            entry.update({
                "subject": a.subject,
                "quantity": shown.get("verdict_quantity"),
                "outcome": shown.get("verdict_outcome"),
                "value": shown.get("verdict_value"),
                "reason": shown.get("verdict_reason"),
                "decider": decider,
                "margin": shown.get("verdict_margin"),
                "declares": _decider_declaration(decider),
                "rows_it_used": [_describe_row(record_after, r)
                                 for r in (shown.get("verdict_rows_used")
                                           or [])[:20]],
                "rows_it_was_handed": shown.get("verdict_rows_considered"),
            })
            # ⚠️ THE VERDICT IS UNCHANGED AND THE FILE SAYS SO — and it says
            # it by RE-RESOLVING against the arm by (quantity, subject) rather
            # than by asserting it. A stance is filed against a verdict and
            # never applied, so this must read False on every run; if it ever
            # reads True, a stance moved a decision and that is the finding.
            now = after_index.get((shown.get("verdict_quantity"), a.subject))
            entry["verdict_now"] = None if now is None else {
                "outcome": now.get("outcome"), "value": now.get("value"),
                "reason": now.get("reason"), "decider": now.get("decider")}
            entry["verdict_was_changed_by_this"] = bool(
                now is not None and (
                    now.get("outcome") != shown.get("verdict_outcome")
                    or now.get("value") != shown.get("verdict_value")
                    or now.get("reason") != shown.get("verdict_reason")))
        disagreements.append(entry)

    reached_nothing = [k for k, v in by_action.items()
                       if v["reached_nothing"] and not v["action"]["refused"]]
    refused = [k for k, v in by_action.items() if v["action"]["refused"]]

    per_stage: Dict[str, dict] = {}
    for entry in by_action.values():
        for v in entry["verdicts_that_named_it"]:
            s = per_stage.setdefault(v["stage"], {
                "verdicts": 0, "weighed": 0, "deciders": {}})
            s["verdicts"] += 1
            if v["how_the_human_row_reached_it"] == "used":
                s["weighed"] += 1
            s["deciders"][v["decider"]] = s["deciders"].get(v["decider"], 0) + 1
    for stage in ("ADJUDICATE", "EVALUATE", "INFER"):
        per_stage.setdefault(stage, {"verdicts": 0, "weighed": 0,
                                     "deciders": {}})

    out = {
        "what_this_is": (
            "Roadmap 3.4, the stage review. One entry per review action: the "
            "human row it became, every verdict whose evidence names that "
            "row, and what the rule that wrote each verdict declares about "
            "itself. A human row that reached nothing is listed under "
            "`reached_nothing` — that is a finding about the pipeline, not a "
            "gap in this file. A disagreement NEVER changes a verdict."),
        "record": record_path,
        "sidecar": sidecar_path,
        "provenance": ingestion.controls.get("provenance"),
        "counts": {
            "actions": len(ingestion.actions),
            "human_rows": sum(len(a.rows) for a in ingestion.actions),
            "actions_refused": len(refused),
            "actions_that_reached_nothing": len(reached_nothing),
            "verdicts_naming_a_human_row": sum(
                len(v["verdicts_that_named_it"]) for v in by_action.values()),
            "verdicts_changed": len(getattr(diff, "changed", ())),
            "notes_before": getattr(diff, "notes_before", None),
            "notes_after": getattr(diff, "notes_after", None),
        },
        "per_stage": {
            k: {"verdicts_naming_a_human_row": v["verdicts"],
                "verdicts_that_WEIGHED_one": v["weighed"],
                "by_decider": v["deciders"]}
            for k, v in sorted(per_stage.items())},
        "what_a_human_box_can_and_cannot_reach": HE.visibility(),
        "actions": by_action,
        "reached_nothing": reached_nothing,
        "refused": refused,
        "disagreements": disagreements,
        "verdicts_changed": list(getattr(diff, "changed", ())),
        "export": {
            "notes_before": getattr(diff, "notes_before", None),
            "notes_after": getattr(diff, "notes_after", None),
            "staff_census_before": getattr(diff, "census_before", None),
            "staff_census_after": getattr(diff, "census_after", None),
        },
        "control": {
            "standing_verdicts_identical": getattr(diff, "control_same", None),
            "standing_verdicts_differ": getattr(diff, "control_differ", None),
            "absent_from_the_rebuild": getattr(diff, "control_absent", None),
            "new_in_the_rebuild": getattr(diff, "control_extra", None),
            "⚠️": ("with an EMPTY sidecar `differ`, `absent` and `new` must "
                   "all be 0; anything else makes every number here a "
                   "measurement of the harness"),
        },
    }
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(out, indent=1, default=str))
    return out
