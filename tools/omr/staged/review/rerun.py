"""RE-DECIDE a saved record with a human's corrections in it, and DIFF.

    python3 -m tools.omr.staged.review.rerun <record.json> <sidecar.json> \
        --out <dir> [--staff staff/3/0/9]

Writes, into `<dir>`: the amended record, its MusicXML, the diff, and the
feedback file (`feedback.py`). Prints the diff.

⚠️⚠️ THE CONTROL COMES FIRST AND IT CAN FAIL. An EMPTY sidecar must reproduce
the record's own verdicts N/N and write the identical MusicXML. Run
`--control` on any record before reading a single number off an arm: a rebuild
that does not reproduce the record makes every figure here a measurement of
this harness. It was run RED first — `--break-control` perturbs one replayed
GATHER row and the control then exits 1 naming the verdicts that moved.

⚠️⚠️ WHAT THIS IS BLIND TO, stated because the next person runs the tool
without reading the write-up. It replays ADJUDICATE→EXPORT over a FIXED
GATHER, exactly as `benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py`
and `benchmarks/omr-infer-stage-2026-09/reinfer.py` do, and inherits their
blind spot: **a GATHER change never enters the rebuild**, so a green control
across one proves nothing. A human's box is not a GATHER change in that sense
— it is a row appended to the saved record, which the rebuild DOES carry —
but a change to `gather.py` that would alter what a human box is compared
against is invisible here and needs two full re-gathers.

⚠️ THE REPLAY IS ITS OWN, NOT AN IMPORT FROM A BENCHMARK. `readjudicate.py`
lives in a directory whose name is not an identifier and is not importable;
copying the twenty lines is cheaper than a `spec_from_file_location` coupling
`tools/` to `benchmarks/`. The ONE DIFFERENCE is named: this replay returns an
OLD-ID -> NEW-ID map, because `Log.observe` assigns dense ids and the saved
record's are sparse (its counter is shared with the verdicts). Without the map
a human row could not be found again in the rebuilt log, and a verdict's
`basis` could not be traced back to the click that produced it.

⚠️ A HUMAN ROW THAT CHANGED NOTHING IS REPORTED, NEVER HIDDEN. Roadmap 3.4's
gate says so in as many words, and it is the more likely outcome: the honest
table in `human_evidence.visibility()` says what a human box can and cannot
reach, and this tool MEASURES it per run instead of trusting that table.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dataclasses import replace as _dc_replace

from .. import adjudicate, evaluate, export as EXPORT, groups, infer
from .. import adjudicators, consequences, inferences      # noqa: F401
from ..record import (Candidate, Log, Outcome, Q, Subject, UphillConsequence,
                      Verdict)
from ..record_io import load_record
from . import human_evidence as HE


# ─────────────────────────────────────────────────────────────────────────────
# 1. The replay
# ─────────────────────────────────────────────────────────────────────────────

def _row_no(row_id: str) -> int:
    try:
        return int(str(row_id).split(":")[-1])
    except (TypeError, ValueError):
        return 0


def rebuild_gather(rec: dict) -> Tuple[Log, Dict[str, str]]:
    """One `Log` holding exactly this record's GATHER rows, in emission order.

    Returns `(log, old_id -> new_id)`. Verdicts are NOT replayed: the point is
    to re-decide them.

    ⚠️ `basis` IS REMAPPED, NOT DROPPED. `readjudicate.py` drops it, which is
    safe there because nothing it replays has one; a human's derived row cites
    the human box it came from, and dropping that would make the correlation
    filter see two independent witnesses where there is one person and one
    click — the exact double-counting `Observation`'s own docstring records
    paying for in 2026-09-07.
    """
    log = Log()
    rows = [(r, "obs") for r in rec.get("observations") or ()]
    rows += [(r, "abs") for r in rec.get("abstentions") or ()]
    rows.sort(key=lambda t: _row_no(t[0]["id"]))
    id_map: Dict[str, str] = {}
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            basis = tuple(id_map[b] for b in (r.get("basis") or ())
                          if b in id_map)
            new = log.observe(sub, r["quantity"], r["value"],
                              reader=r["reader"], frame=r["frame"],
                              score=r.get("score"), derived_from=basis,
                              **detail)
        else:
            new = log.abstain(sub, r["quantity"], reader=r["reader"],
                              frame=r["frame"], reason=r["reason"], **detail)
        id_map[r["id"]] = new.id
    return log, id_map


def run_stages(log: Log, *, progress: bool = False) -> dict:
    """ADJUDICATE → GROUPS → EVALUATE → INFER, in `pipeline.run_staged`'s own
    order. ⚠️ The order is the claim, not a convenience: INFER may only see a
    log whose consequences have been drawn (CLAUDE.md §4a), and `infer.run`
    takes EVALUATE's report as an argument so that stays structural."""
    verdicts = adjudicate.run(log, progress=progress)
    agreement = groups.run(log, progress=progress)
    report = evaluate.run(log, progress=progress)
    inference = None
    if infer.stage_should_run():
        inference = infer.run(log, report, progress=progress)
    return {"verdicts": verdicts, "agreement": agreement,
            "evaluation": report, "inference": inference}


# ─────────────────────────────────────────────────────────────────────────────
# 2. The exporter's refusals, per SUBJECT
#
# ⚠️ THE REFUSAL BUCKETS ARE NOT RESTATED HERE. `export._place_notes` holds
# the rule; this wraps it at run time, exactly as
# `benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py` does and for the
# same reason — the repo has paid once already for a second copy
# (`omr-cleanup-count-2026-09/build_sheet.py` reported 542 where the exporter
# refused 738). The CONTROL is that the per-subject tallies sum back to the
# exporter's own totals, and it can fail.
# ─────────────────────────────────────────────────────────────────────────────

class _LoggingCounter(collections.Counter):
    def __init__(self, sink, last, *a, **kw):
        super().__init__(*a, **kw)
        self._sink, self._last = sink, last

    def __setitem__(self, key, value):
        if value > self.get(key, 0):
            self._sink.append((self._last["sub"], key))
        super().__setitem__(key, value)


class _ProbeBySystem(dict):
    def __init__(self, sink, last):
        super().__init__()
        self._sink, self._last = sink, last

    def setdefault(self, key, default=None):
        if key not in self:
            dict.__setitem__(self, key, _LoggingCounter(self._sink, self._last))
        return self[key]


def export_with_subjects(result: dict) -> Tuple[str, dict, List[Tuple[str, str]],
                                                List[Tuple[str, str]]]:
    """`to_musicxml`, plus (subject, refusal) and (subject, category) lists."""
    refusals: List[Tuple[str, str]] = []
    placed: List[Tuple[str, str]] = []
    last = {"sub": None}
    orig_parse, orig_place = EXPORT._parse_subject, EXPORT._place_notes

    def parse(key):
        s = orig_parse(key)
        last["sub"] = key
        return s

    def place(rec, runs, by_system=None, held_out=None):
        probe = _ProbeBySystem(refusals, last)
        dropped = orig_place(rec, runs, by_system=probe, held_out=held_out)
        for run in runs.values():
            for cell in run.cells.values():
                for det in cell.detections:
                    placed.append((det.get("glyph"), det.get("category")))
        if by_system is not None:
            by_system.update(probe)
        return dropped

    EXPORT._parse_subject, EXPORT._place_notes = parse, place
    try:
        xml, report = EXPORT.to_musicxml(result)
    finally:
        EXPORT._parse_subject, EXPORT._place_notes = orig_parse, orig_place

    # ── the control: our per-subject tallies must equal the exporter's own ──
    mine = collections.Counter(r for _s, r in refusals)
    theirs = collections.Counter(report.get("notes_not_written") or {})
    if mine != theirs:
        raise RuntimeError(
            "the per-subject refusal log does not sum to the exporter's own "
            f"notes_not_written: mine {dict(mine)} vs {dict(theirs)}. Every "
            "per-staff number below would be a measurement of this wrapper.")
    return xml, report, refusals, placed


def staff_census(refusals: Sequence[Tuple[str, str]],
                 placed: Sequence[Tuple[str, str]],
                 staff_key: Optional[str]) -> dict:
    """Refused-by-reason and written, for the glyphs of ONE staff.

    ⚠️ A PARTITION AND IT SAYS SO. `written + refused` is reported beside the
    notehead-box population so a reader can see the balance rather than take
    a coverage number on trust — `export.status_census`'s own discipline.
    """
    def on(sub: Optional[str]) -> bool:
        return bool(staff_key) and bool(sub) and _staff_of(sub) == staff_key

    ref = collections.Counter(r for s, r in refusals if on(s))
    wrote = collections.Counter(c for s, c in placed if on(s))
    return {"staff": staff_key, "refused": dict(ref), "written": dict(wrote),
            "refused_total": sum(ref.values()),
            "written_total": sum(wrote.values())}


def _staff_of(subject: str) -> Optional[str]:
    try:
        s = Subject.from_key(subject)
    except Exception:
        return None
    from ..record import Kind
    st = s.at(Kind.STAFF)
    return st.to_key() if st is not None else None


# ─────────────────────────────────────────────────────────────────────────────
# 3. The diff
# ─────────────────────────────────────────────────────────────────────────────

def _verdict_index(verdicts: Sequence[dict]) -> Dict[Tuple[str, str], dict]:
    """(quantity, subject) -> the STANDING verdict, resolved exactly as
    `export.Record` resolves it: drop every row a later one supersedes."""
    superseded = {v["supersedes"] for v in verdicts if v.get("supersedes")}
    out: Dict[Tuple[str, str], dict] = {}
    fallback: Dict[Tuple[str, str], dict] = {}
    for v in verdicts:
        key = (v["quantity"], v["subject"])
        fallback[key] = v
        if v["id"] not in superseded:
            out[key] = v
    for key, v in fallback.items():
        out.setdefault(key, v)
    return out


def _shape(v: dict) -> tuple:
    return (v["outcome"], json.dumps(v.get("value"), sort_keys=True,
                                     default=str), v.get("reason"))


@dataclass
class Diff:
    control_same: int = 0
    control_differ: int = 0
    control_absent: int = 0
    control_extra: int = 0
    changed: List[dict] = field(default_factory=list)
    basis_names_human: List[dict] = field(default_factory=list)
    human_rows_unread: List[dict] = field(default_factory=list)
    human_rows_read: List[dict] = field(default_factory=list)
    census_before: dict = field(default_factory=dict)
    census_after: dict = field(default_factory=dict)
    notes_before: int = 0
    notes_after: int = 0
    #: ⚠️ THE SECOND HALF OF THE CONTROL. Reproducing the VERDICTS is not
    #: reproducing the FILE: the exporter reads rows the verdict comparison
    #: never touches, so an empty sidecar must also write a byte-identical
    #: MusicXML. `--control` fails on either half.
    musicxml_identical: bool = True
    stage_summary: Dict[str, dict] = field(default_factory=dict)

    def to_json(self) -> dict:
        # ⚠️ SPELLED OUT, not a comprehension over a name list. `wiring
        # --check`'s ROUNDTRIP question reads this method's AST and compares
        # the keys it writes against the class's declared fields — a
        # comprehension emits nothing it can see, so every field would report
        # as DROPPED. The check is right to insist: a field a consumer reads
        # and a projection silently omits is the `works.json` `lines` fault,
        # which four separate projections dropped.
        return {"control_same": self.control_same,
                "control_differ": self.control_differ,
                "control_absent": self.control_absent,
                "control_extra": self.control_extra,
                "changed": self.changed,
                "basis_names_human": self.basis_names_human,
                "human_rows_read": self.human_rows_read,
                "human_rows_unread": self.human_rows_unread,
                "census_before": self.census_before,
                "census_after": self.census_after,
                "notes_before": self.notes_before,
                "notes_after": self.notes_after,
                "musicxml_identical": self.musicxml_identical,
                "stage_summary": self.stage_summary}


def _stage_of_verdict(v: dict) -> str:
    """Which STAGE wrote a verdict — DERIVED, never guessed from the name.

    ⚠️ `infer.is_inferred` is the tree's own test for an INFER verdict and is
    asked first. An EVALUATE verdict's `decider` is the consequence FUNCTION's
    name, so the set is read off `evaluate.RULES[*].fn.__name__`. ⚠️ The first
    cut read `getattr(rule, "name")`, which `evaluate.Rule` does not have — it
    returned `None` for all seven and every consequence reported as
    ADJUDICATE. Caught because `restate_pitch` filed a pitch under the wrong
    stage in the very first arm; a derivation off a field that does not exist
    fails silently and plausibly, which is the whole reason this is asserted
    in `test_stage_review.py` against the registry rather than reviewed.
    """
    if infer.is_inferred(v):
        return "INFER"
    if v.get("decider") in _EVALUATE_DECIDERS:
        return "EVALUATE"
    return "ADJUDICATE"


def _evaluate_deciders() -> frozenset:
    out = set()
    for rule in getattr(evaluate, "RULES", ()):
        fn = getattr(rule, "fn", None)
        if fn is not None and getattr(fn, "__name__", None):
            out.add(fn.__name__)
    if not out:
        raise RuntimeError(
            "no EVALUATE rule names could be derived — every consequence "
            "would be filed under ADJUDICATE and the per-stage table would be "
            "a measurement of this function")
    return frozenset(out)


_EVALUATE_DECIDERS = _evaluate_deciders()


def diff_records(before: dict, after: dict, *, human_rows: Dict[str, List[str]],
                 id_map: Dict[str, str], staff: Optional[str],
                 census_before: dict, census_after: dict,
                 notes_before: int, notes_after: int,
                 musicxml_identical: bool = True) -> Diff:
    """What the human's rows did — and did not do."""
    d = Diff(census_before=census_before, census_after=census_after,
             notes_before=notes_before, notes_after=notes_after,
             musicxml_identical=musicxml_identical)
    b = _verdict_index(before.get("verdicts") or ())
    a = _verdict_index(after.get("verdicts") or ())
    for key, bv in b.items():
        av = a.get(key)
        if av is None:
            d.control_absent += 1
            continue
        if _shape(av) == _shape(bv):
            d.control_same += 1
        else:
            d.control_differ += 1
            d.changed.append({
                "subject": key[1], "quantity": key[0],
                "stage": _stage_of_verdict(av),
                "before": {"outcome": bv["outcome"], "value": bv.get("value"),
                           "reason": bv.get("reason")},
                "after": {"outcome": av["outcome"], "value": av.get("value"),
                          "reason": av.get("reason"), "id": av.get("id")},
            })
    d.control_extra = len(set(a) - set(b))

    # ── which verdicts NAME a human row, and which human rows nothing read ──
    # ⚠️ `id_map` DEFAULTS TO IDENTITY PER ROW, not to "drop it". `rerun`
    # remaps the ledger before calling this, so the ids arriving here are
    # already the replay's; a caller that has not remapped passes the map and
    # gets the same answer. Silently dropping an unmapped row would report a
    # human row as unread when it was merely unfindable.
    wanted = {}
    for action_id, ids in human_rows.items():
        for old in ids:
            wanted[id_map.get(old, old)] = (action_id, old)
    seen: set = set()
    # ⚠️ A SINGLE PASS WITH A SMALL-SET MEMBERSHIP TEST, not three sets per
    # verdict. `wanted` holds a handful of ids; a whole-movement record holds
    # ~100,000 verdicts and `adjudicate_arc_owner` alone cites ~1,800 rows in
    # each of `basis`, `considered` and `correlated` (roadmap 1.1b measured
    # that as 99 % of an arc verdict's bytes). Building three sets per verdict
    # allocates that volume all over again for an answer that never needs the
    # set. Same result, and it is the difference between a diff that finishes
    # and one that looks like a hang.
    for key, av in a.items():
        hit = set()
        for fld in ("used", "basis", "considered"):
            for rid in av.get(fld) or ():
                if rid in wanted:
                    hit.add(rid)
        if not hit:
            continue
        seen |= hit
        in_used = sorted(h for h in hit if h in (av.get("used") or ()))
        in_basis = sorted(h for h in hit if h in (av.get("basis") or ()))
        # ⚠️⚠️ `used` IS NOT `basis` IS NOT `considered`, AND REPORTING THEM
        # AS ONE WOULD OVERSTATE EVERY REVIEW. `Verdict.used` is what the
        # DECISION says it weighed; `considered` is what the HARNESS handed
        # it; `basis` is that plus every ancestor. A human row in the third
        # and not the first means the decision was OFFERED his reading and did
        # not use it — which is precisely the structural finding roadmap 3.4
        # is collecting, and it is the opposite of a row that did work.
        d.basis_names_human.append({
            "subject": key[1], "quantity": key[0],
            "stage": _stage_of_verdict(av),
            "how": "used" if in_used else ("basis" if in_basis
                                           else "considered"),
            "verdict": av.get("id"), "outcome": av["outcome"],
            "value": av.get("value"), "reason": av.get("reason"),
            "decider": av.get("decider"),
            "human_rows": sorted(
                f"{wanted[h][0]}:{wanted[h][1]}->{h}" for h in hit),
            "in_basis": in_basis, "in_used": in_used,
            "other_rows_used": sorted(set(av.get("used") or ()) - hit)[:12],
        })
    for new, (action_id, old) in sorted(wanted.items()):
        entry = {"action": action_id, "row": old, "replayed_as": new}
        (d.human_rows_read if new in seen else d.human_rows_unread).append(entry)

    # ⚠️ `used` FIRST. A reader skimming this list must meet the verdicts that
    # WEIGHED the human's reading before the ones that were merely handed it.
    order = {"used": 0, "basis": 1, "considered": 2}
    d.basis_names_human.sort(key=lambda r: (order[r["how"]], r["quantity"],
                                            r["subject"]))

    per_stage: Dict[str, dict] = {}
    for row in d.basis_names_human:
        st = per_stage.setdefault(row["stage"], {
            "verdicts": 0, "used": 0, "rows": set(), "rows_used": set()})
        st["verdicts"] += 1
        st["rows"].update(row["human_rows"])
        if row["how"] == "used":
            st["used"] += 1
            st["rows_used"].update(row["human_rows"])
    d.stage_summary = {
        k: {"verdicts_naming_a_human_row": v["verdicts"],
            "verdicts_that_WEIGHED_one": v["used"],
            "distinct_human_rows_named": len(v["rows"]),
            "distinct_human_rows_weighed": len(v["rows_used"])}
        for k, v in sorted(per_stage.items())}
    d.stage_summary["_unread"] = {
        "human_rows_no_stage_read": len(d.human_rows_unread),
        "human_rows_read": len(d.human_rows_read)}
    return d


# ─────────────────────────────────────────────────────────────────────────────
# 4. The run
# ─────────────────────────────────────────────────────────────────────────────

def _to_result(log: Log, parent_result: dict, review_prov: Optional[dict]
               ) -> dict:
    prov = dict(parent_result.get("provenance") or {})
    if review_prov is not None:
        prov = {**prov, "review": review_prov}
    out = {"record": log.to_json(), "summary": log.summary()}
    if prov:
        out["provenance"] = prov
    return out


def rerun(record_path: str, sidecar_path: Optional[str],
          out_record_path: Optional[str], *, staff: Optional[str] = None,
          musicxml_path: Optional[str] = None,
          progress: bool = False,
          break_control: bool = False) -> Tuple[Diff, dict, dict]:
    """Load, ingest, re-decide, export, diff. Returns `(diff, arm, ingestion)`.

    ⚠️ REFUSES TO WRITE OVER THE PARENT. A human-amended record is a NEW file:
    overwriting the parent would destroy the only thing the amended record's
    provenance can be checked against.
    """
    if out_record_path is not None and \
            Path(out_record_path).resolve() == Path(record_path).resolve():
        raise ValueError(
            "the amended record may not overwrite its parent — its provenance "
            "names the parent's md5, and a file that has eaten its own parent "
            "cannot be checked against anything")
    doc = load_record(record_path)
    rec = doc["record"] if "record" in doc else doc

    prov = doc.get("provenance")
    print(f"record provenance: {json.dumps(prov, default=str)[:300]}")
    if not prov or prov.get("commit") is None or prov.get("dirty") is None:
        print("⚠️ this record does not fully name the tree that built it; do "
              "not compare it with another unnamed record.", file=sys.stderr)

    sidecar = (HE.load_sidecar(sidecar_path) if sidecar_path
               else {"actions": []})
    parent_md5 = HE.file_md5(record_path)
    ing = HE.ingest(rec, sidecar, sidecar_path=sidecar_path,
                    parent_path=str(record_path), parent_md5=parent_md5,
                    provenance=prov)
    amended = ing.record
    if break_control:
        # ⚠️ THE CONTROL, SEEN FAILING. Perturbs ONE replayed GATHER row so
        # the re-decision must differ; a control that has never been watched
        # to fail is a computation.
        for o in amended.get("observations") or ():
            if o.get("quantity") == Q.NOTEHEAD_STAFF_POSITION:
                o["value"] = float(o["value"]) + 3.0
                print(f"⚠️ --break-control: perturbed {o['id']}")
                break

    log, id_map = rebuild_gather(amended)
    # ⚠️ THE LEDGER FOLLOWS THE REPLAY'S IDS. Everything downstream — the
    # diff, the feedback file — describes the ARM record, whose rows were
    # renumbered; see `Ingestion.remap`.
    ing.remap(id_map)
    if progress:
        print(f"replayed {len(id_map)} gather rows")
    run_stages(log, progress=progress)
    arm = _to_result(log, doc, ing.controls.get("provenance"))

    xml_after, rep_after, ref_after, placed_after = export_with_subjects(arm)
    xml_before, rep_before, ref_before, placed_before = export_with_subjects(
        {"record": rec, "summary": doc.get("summary") or {}})

    d = diff_records(
        rec, arm["record"], human_rows=ing.rows_by_action(), id_map={},
        staff=staff,
        census_before=staff_census(ref_before, placed_before, staff),
        census_after=staff_census(ref_after, placed_after, staff),
        notes_before=xml_before.count("<note"),
        notes_after=xml_after.count("<note"),
        musicxml_identical=(xml_before == xml_after))
    d.stage_summary["_export"] = {
        "status_census_before": rep_before.get("status_census"),
        "status_census_after": rep_after.get("status_census")}

    # ⚠️ `out_record_path=None` WRITES NO RECORD, and that is for the CONTROL
    # rather than for speed in general. A control's amended record is BY
    # DEFINITION the parent's gather rows re-decided — there is nothing in it
    # to keep, and on a whole-movement record `record_io.pool_id_lists` has to
    # intersect ~1,800-id lists across every arc verdict of every system and
    # then expand its own output to prove the spelling lossless. That is the
    # right price for an arm and pure waste for a comparison.
    if out_record_path is not None:
        Path(out_record_path).parent.mkdir(parents=True, exist_ok=True)
        from ..record_io import dumps_for_file
        Path(out_record_path).write_text(
            dumps_for_file(arm, indent=1, default=str))
    if musicxml_path:
        Path(musicxml_path).write_text(xml_after)
    return d, arm, ing


def print_diff(d: Diff, ing: HE.Ingestion) -> None:
    print("\n═══ CONTROL — did the replay reproduce the record? ══════════════")
    print(f"   {d.control_same} of {d.control_same + d.control_differ} "
          f"standing verdicts identical, {d.control_differ} differ, "
          f"{d.control_absent} absent from the rebuild, "
          f"{d.control_extra} new")
    if ing.controls.get("actions") == 0 and (d.control_differ or d.control_extra
                                             or d.control_absent):
        print("⚠️⚠️ THE SIDECAR WAS EMPTY AND THE RECORD DID NOT REPRODUCE. "
              "Every number from this tool would be a measurement of the "
              "harness.", file=sys.stderr)

    print("\n═══ THE SIDECAR ═════════════════════════════════════════════════")
    for k in ("actions", "rows_filed", "actions_refused", "frames_refused",
              "grids_refused"):
        print(f"   {k:20} {ing.controls.get(k)}")
    for a in ing.actions:
        if a.refused:
            print(f"   ⚠️ REFUSED {a.id} ({a.kind}): {a.refused}")

    print("\n═══ VERDICTS THAT CHANGED ═══════════════════════════════════════")
    if not d.changed:
        print("   none")
    for c in d.changed[:60]:
        print(f"   [{c['stage']}] {c['quantity']:26} {c['subject']}")
        print(f"        {c['before']['outcome']}/{c['before']['value']!r} "
              f"({c['before']['reason']})  ->  "
              f"{c['after']['outcome']}/{c['after']['value']!r} "
              f"({c['after']['reason']})")
    if len(d.changed) > 60:
        print(f"   ... {len(d.changed) - 60} more")

    print("\n═══ VERDICTS WHOSE EVIDENCE NAMES A HUMAN ROW ═══════════════════")
    if not d.basis_names_human:
        print("   none")
    print("   ⚠️ `used` = the decision WEIGHED it; `basis`/`considered` = it "
          "was handed it and did not say it weighed it.")
    for r in d.basis_names_human[:40]:
        print(f"   [{r['stage']}|{r['how']}] {r['quantity']:26} {r['subject']}")
        print(f"        {r['outcome']}/{str(r['value'])[:90]!r} "
              f"({r['reason']}) by {r['decider']}; "
              f"human rows {r['human_rows']}")

    print("\n═══ HUMAN ROWS THAT REACHED NO VERDICT ══════════════════════════")
    print("   ⚠️ reported, never hidden — a witness that changed nothing is "
          "the finding, not a gap in the report.")
    if not d.human_rows_unread:
        print("   none")
    for r in d.human_rows_unread:
        print(f"   {r['action']:12} {r['row']} (replayed as {r['replayed_as']})")

    print("\n═══ EXPORT ══════════════════════════════════════════════════════")
    print(f"   <note> elements  {d.notes_before} -> {d.notes_after} "
          f"({d.notes_after - d.notes_before:+d})")
    print(f"   MusicXML identical to the parent's: {d.musicxml_identical}")
    print(f"   staff census before {json.dumps(d.census_before, default=str)}")
    print(f"   staff census after  {json.dumps(d.census_after, default=str)}")

    print("\n═══ PER STAGE ═══════════════════════════════════════════════════")
    print(json.dumps(d.stage_summary.get("_unread"), indent=1))
    for k, v in sorted(d.stage_summary.items()):
        if k.startswith("_"):
            continue
        print(f"   {k:12} {v}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("record")
    ap.add_argument("sidecar", nargs="?", default=None,
                    help="omit for the CONTROL: an empty sidecar")
    ap.add_argument("--out", required=True, help="output DIRECTORY")
    ap.add_argument("--staff", default=None,
                    help="the staff the review pass was about, e.g. staff/3/0/9")
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--control", action="store_true",
                    help="ignore the sidecar and prove the replay reproduces "
                         "the record; exit 1 if it does not")
    ap.add_argument("--break-control", action="store_true",
                    help="perturb one gather row so the control MUST fail")
    ap.add_argument("--record", dest="record_out", action="store_true",
                    help="write the amended record even under --control")
    a = ap.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sidecar = None if a.control else a.sidecar
    staff = a.staff
    if staff is None and sidecar:
        staff = (json.loads(Path(sidecar).read_text()) or {}).get("staff")

    # ⚠️ A CONTROL WRITES NO AMENDED RECORD (see `rerun`). `--record` forces
    # one anyway, for a session that wants the replayed record in hand.
    out_record = (None if (a.control and not a.record_out)
                  else str(out / "amended.record.json"))
    d, arm, ing = rerun(a.record, sidecar, out_record,
                        staff=staff, musicxml_path=str(out / "arm.musicxml"),
                        progress=a.progress, break_control=a.break_control)
    print_diff(d, ing)
    (out / "diff.json").write_text(json.dumps(
        {"diff": d.to_json(), "ingestion": ing.ledger(),
         "visibility": HE.visibility()}, indent=1, default=str))

    from . import feedback
    fb = feedback.export_feedback(
        arm["record"], ing, d, str(out / "feedback.json"),
        record_path=a.record, sidecar_path=sidecar)
    print(f"\nwrote {out/'diff.json'}, {out/'feedback.json'} "
          f"({fb['counts']})")

    if a.control:
        ok = (d.control_differ == 0 and d.control_absent == 0
              and d.control_extra == 0 and d.musicxml_identical)
        print("CONTROL " + ("PASSED" if ok else "FAILED"))
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
