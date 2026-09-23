"""A review-actions sidecar, ingested into a staged record as WITNESSES.

    from tools.omr.staged.review import human_evidence as HE
    ing = HE.ingest(record_dict, sidecar_dict, sidecar_path="...")
    ing.record          # a NEW record dict; the input is never mutated
    ing.actions         # one outcome per sidecar action, including refusals

⚠️⚠️ THE HUMAN IS A READER, WITH ALL A READER'S OBLIGATIONS. His rows carry a
`reader` from the closed `record.READERS` vocabulary, a `frame`, a `detail`
naming the sidecar file and the action id, and — where they were computed
rather than drawn — a `basis`. Two rows from one reader on one crop are ONE
signal (`adjudicate.Evidence.correlated_groups`), and that is as true of a
person as of the detector.

⚠️⚠️ THE SUBJECT PROBLEM, AND THE ANSWER `Q.INK` ALREADY GAVE.
`record.Subject`'s last glyph coordinate is an INDEX INTO THE DETECTOR'S
OUTPUT for that cell (CLAUDE.md §4b), so a box the detector never drew has no
index and therefore no subject. `gather.py` has hit this four times already
and each time answered it the same way — an OFFSET ORDINAL past every other
reader's base (`_DIRECTION_GLYPH_BASE` 90,000, `_CV_GLYPH_BASE` 100,000,
`_INK_GLYPH_BASE` 200,000, `_VERTICAL_RUN_GLYPH_BASE` 300,000) so that two
readers can never collide in one cell's key space. A collision would not
raise; it would silently merge a human's box and a detection into one subject.
This module takes the fifth base, 400,000, and `test_stage_review.py` derives
gather's bases off the module and asserts no overlap rather than restating
them.

⚠️⚠️ WHAT A HUMAN BOX CANNOT GET, NAMED RATHER THAN INVENTED. GATHER files
five things about a detected notehead. A human box can be given three of them
and MUST NOT be given the other two:

  `Q.GLYPH_BOX`                 ✅ the box he drew, in the cell's canonical
                                   frame, recovered from the cell's own rows
                                   with a control that can fail.
  `Q.NOTEHEAD_CLASS`            ✅ when the category he chose is a notehead
                                   class — the same test `gather.py` applies.
  `Q.NOTEHEAD_STAFF_POSITION`   ✅ when the cell's grid can be recovered from
                                   its own rows, again with a control.
  `Q.GLYPH_CONF`                ❌ ABSENT. A person did not produce a softmax.
                                   Writing 1.0 would be a fallback converting
                                   "there is no such number" into a definite
                                   one — the standing refusal in CLAUDE.md
                                   rule 8 — and `adjudicate_notehead_is_not_a_
                                   notehead`'s `unladdered` signal reads it.
  `Q.GLYPH_BAND_DISTANCE`,      ❌ ABSENT, and this one is STRUCTURAL: both
  `Q.GLYPH_LADDER`                 are produced by `gather_ownership_evidence`
                                   from the cell RASTER (a same-class overlap
                                   search and a ledger-rung search). Neither is
                                   derivable from rows. A human box is
                                   therefore invisible to `glyph_owner`'s
                                   contest, which is reported, not hidden.

  Nothing gives a human box a BEAM, a FLAG or an AUG DOT either, all of which
  `adjudicate_duration` reads off the cell's own raster.

⚠️⚠️ AND THE CONSEQUENCE OF THAT LAST LINE IS NOT "no duration" — IT IS A
DURATION READ FROM THE HEAD ALONE, WHICH IS WORSE, because it is an answer.
Measured on the fixture: a human `noteheadBlackOnLine` comes back DECIDED
`written 1.0`, reason `head_and_marks`, with the marks half of that reason
contributing nothing. That is correct for a quarter note and wrong for every
beamed or flagged one, and NOTHING ON THE ROW SAYS WHICH — the human drew a
box, not a stem. A session reading a review pass must treat a human box's
duration as unmeasured rather than as read. `rerun.py` prints the honest
table per run rather than trusting this comment; closing the gap needs a
GATHER function that re-reads the cell raster around a human box, which is a
2.6-shaped change and is not this lane's.

⚠️ A HUMAN-AMENDED RECORD IS A NEW RECORD FILE. Its provenance names the
PARENT record's md5 and the sidecar's sha256, and `rerun.py` refuses to write
over the parent. CLAUDE.md §4b: a record that cannot name the tree that built
it is not a baseline — an amended one that cannot name what it was amended
FROM is worse, because it looks exactly like a gather.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ..record import Kind, Q, READERS, Subject, claim_of, glyph

# ─────────────────────────────────────────────────────────────────────────────
# The sidecar
# ─────────────────────────────────────────────────────────────────────────────

#: Every `kind` lane (B) may write. An unknown one is REFUSED, never ignored:
#: a viewer that grows a verb this module has not been taught would otherwise
#: have its actions silently dropped and the review would read as complete.
GATHER_KINDS = ("add_box", "delete_box", "redraw_box")
STANCE_KINDS = ("agree", "disagree")
STAGES = ("gather", "adjudicate", "evaluate", "infer", "export")

#: ⚠️ THE FIFTH BASE. See the module docstring; the four below it live in
#: `gather.py` and the test derives them from that module rather than copying
#: the numbers here.
HUMAN_GLYPH_BASE = 400_000

#: A `smufl_name` beginning with this is a notehead, exactly as
#: `gather._NOTEHEAD_PREFIX` says. Imported, not restated.
try:                                              # pragma: no cover - import
    from ..gather import _NOTEHEAD_PREFIX as NOTEHEAD_PREFIX
except Exception:                                 # pragma: no cover
    NOTEHEAD_PREFIX = "notehead"

#: How far two anchors may disagree before the recovered frame is REFUSED.
#: Relative on the scale, absolute page pixels on the offsets. Chosen so the
#: recovery of a well-formed cell passes and a cell whose rows were measured
#: in two different frames cannot.
FRAME_SCALE_TOLERANCE = 1e-3
FRAME_OFFSET_TOLERANCE_PX = 0.5
#: How far two anchor noteheads may disagree about where the staff's top line
#: sits, in canonical pixels, before the grid recovery is REFUSED.
GRID_TOP_TOLERANCE_C = 1.0


class SidecarError(ValueError):
    """The sidecar is not the contract. Never caught internally — a review
    pass that silently dropped half a human's clicks is worse than one that
    did not run."""


def load_sidecar(path: Union[str, Path]) -> dict:
    """Read and CHECK a sidecar file. See `SIDECAR.md` for the shape."""
    data = json.loads(Path(path).read_text())
    check_sidecar(data)
    return data


def check_sidecar(sc: Any) -> None:
    if not isinstance(sc, dict):
        raise SidecarError("a sidecar is a JSON object")
    actions = sc.get("actions")
    if not isinstance(actions, list):
        raise SidecarError("`actions` must be a list (an EMPTY list is legal "
                           "and is the control: it must change nothing)")
    seen: set = set()
    for i, a in enumerate(actions):
        if not isinstance(a, dict):
            raise SidecarError(f"action {i} is not an object")
        aid = a.get("id")
        if not isinstance(aid, str) or not aid:
            raise SidecarError(f"action {i} has no `id`")
        if aid in seen:
            raise SidecarError(
                f"action id {aid!r} appears twice. Ids are how a verdict's "
                f"basis is traced back to a click; two clicks sharing one is "
                f"a silently merged pair of findings.")
        seen.add(aid)
        kind = a.get("kind")
        if kind not in GATHER_KINDS + STANCE_KINDS:
            raise SidecarError(
                f"action {aid}: kind {kind!r} is not one of "
                f"{GATHER_KINDS + STANCE_KINDS}. A verb this module has not "
                f"been taught is REFUSED rather than dropped.")
        stage = a.get("stage")
        if stage is not None and stage not in STAGES:
            raise SidecarError(f"action {aid}: stage {stage!r} is not one of "
                               f"{STAGES}")
        if kind in STANCE_KINDS and not a.get("verdict"):
            raise SidecarError(f"action {aid}: a {kind} names no `verdict`")
        if kind in ("delete_box", "redraw_box") and not a.get("glyph"):
            raise SidecarError(f"action {aid}: a {kind} names no `glyph`")
        if kind in ("add_box", "redraw_box"):
            bb = a.get("bbox_page_px")
            if not (isinstance(bb, (list, tuple)) and len(bb) == 4):
                raise SidecarError(
                    f"action {aid}: a {kind} needs `bbox_page_px` "
                    f"[x0, y0, x1, y1] in PAGE pixels at the gather's own DPI")
        if kind == "add_box" and not a.get("category"):
            raise SidecarError(
                f"action {aid}: an add_box names no `category`. A box with no "
                f"name is `Q.INK`, which GATHER already files and this module "
                f"may not manufacture.")


def sidecar_digest(sc: dict) -> str:
    """sha256 over the canonical spelling — so two sidecars that differ only
    in key order or whitespace hash the SAME, and two that differ in one
    pixel hash differently."""
    return hashlib.sha256(
        json.dumps(sc, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode()).hexdigest()


def file_md5(path: Union[str, Path]) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Outcomes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActionOutcome:
    """What became of ONE click. ⚠️ `refused` is not a failure of the review;
    it is the finding. A human box in a cell whose frame cannot be recovered
    is a fact about the RECORD, and burying it would make the review read as
    complete when half of it never landed."""

    id: str
    kind: str
    stage: Optional[str]
    subject: Optional[str] = None
    rows: List[str] = field(default_factory=list)
    #: quantity -> why this row could NOT be filed. See the module docstring.
    absent: Dict[str, str] = field(default_factory=dict)
    refused: Optional[str] = None
    note: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"id": self.id, "kind": self.kind, "stage": self.stage,
                "subject": self.subject, "rows": list(self.rows),
                "absent": dict(self.absent), "refused": self.refused,
                "note": self.note, "detail": dict(self.detail)}


@dataclass
class Ingestion:
    """⚠️ RETURNS THE LEDGER BESIDE THE RECORD, DELIBERATELY. The brief's
    signature was `ingest(record, sidecar) -> record`; throwing the per-action
    ledger away would make `feedback.py` re-derive which row came from which
    click by matching detail fields and hoping — this repo's own standing bug
    class, *the value existed and nothing read it*. `.record` is that record."""

    record: dict
    actions: List[ActionOutcome]
    #: Everything the ingest measured about itself, so a reader can tell an
    #: ingest that did nothing because the sidecar was empty from one that did
    #: nothing because it was inert.
    controls: Dict[str, Any] = field(default_factory=dict)

    def rows_by_action(self) -> Dict[str, List[str]]:
        return {a.id: list(a.rows) for a in self.actions}

    def remap(self, id_map: Dict[str, str]) -> None:
        """Re-point every action's rows at the ids the REPLAY gave them.

        ⚠️⚠️ WITHOUT THIS THE FEEDBACK FILE LOOKS UP ROWS THAT ARE NOT THERE,
        AND SAYS SO BY WRITING `null`. `ingest` numbers a human row by
        continuing the SAVED record's counter, which is sparse (it is shared
        with the verdicts); `Log.observe` renumbers densely on the replay. The
        two disagree, and the disagreement is silent — `_row()` returns None
        and the file reports a disagreement against verdict `null`. Found by a
        test that asserted the verdict id; the original ids are KEPT beside
        the new ones rather than overwritten, because a reader of the ledger
        needs to be able to find the row in the AMENDED record too.
        """
        for a in self.actions:
            if not a.rows:
                continue
            a.detail["rows_before_replay"] = list(a.rows)
            a.rows = [id_map.get(r, r) for r in a.rows]

    def ledger(self) -> dict:
        """The per-action ledger, for the diff and the feedback file.

        ⚠️ DELIBERATELY NOT NAMED `to_json`, AND THE NAME IS THE CLAIM. This
        is not a serialisation of an `Ingestion`: `.record` is a whole staged
        record and is written to its OWN file by `rerun.py`. `wiring
        --check`'s ROUNDTRIP question asks whether a class's `to_json` drops a
        field its consumers read, and it would be RIGHT to fail a `to_json`
        here — so the method says what it is instead of quietly omitting the
        biggest field in the object.
        """
        return {"actions": [a.to_json() for a in self.actions],
                "controls": dict(self.controls)}


# ─────────────────────────────────────────────────────────────────────────────
# Reading the record's own frames back out
# ─────────────────────────────────────────────────────────────────────────────

def _row_ordinal(row_id: str) -> int:
    m = re.search(r"(\d+)$", str(row_id or ""))
    return int(m.group(1)) if m else 0


def _max_ordinal(record: dict) -> int:
    n = 0
    for key in ("observations", "abstentions", "verdicts"):
        for r in record.get(key) or ():
            n = max(n, _row_ordinal(r.get("id")))
    return n


@dataclass(frozen=True)
class CellFrame:
    """canonical -> page: `page = origin + canonical / upscale`.

    Exactly `gather._page_box`'s arithmetic, INVERTED, and recovered from the
    cell's own `Q.GLYPH_BOX` rows rather than from a `MeasureCell` object no
    record carries. One anchor determines it; two or more CHECK it.
    """

    upscale: float
    x0: float
    y0: float
    anchors: int
    max_deviation_px: Optional[float]

    def to_canonical(self, bbox_page: Sequence[float]) -> Tuple[float, ...]:
        px0, py0, px1, py1 = (float(v) for v in bbox_page)
        u = self.upscale
        return ((px0 - self.x0) * u, (py0 - self.y0) * u,
                (px1 - px0) * u, (py1 - py0) * u)


def _glyph_rows_of_cell(record: dict, cell: Subject) -> List[dict]:
    """Every `Q.GLYPH_BOX` row filed on a glyph OF THIS CELL.

    ⚠️ A string prefix on the subject key, which is exact: a glyph subject is
    its cell's key with `cell` -> `glyph` and one more coordinate, so
    `glyph/3/0/9/0/` matches every glyph of `cell/3/0/9/0` and nothing else.
    """
    prefix = "glyph/" + cell.to_key().split("/", 1)[1] + "/"
    return [o for o in (record.get("observations") or ())
            if o.get("quantity") == Q.GLYPH_BOX
            and str(o.get("subject") or "").startswith(prefix)]


def _cell_of(sub: Subject) -> Optional[Subject]:
    return sub.at(Kind.CELL)


def recover_cell_frame(cell_glyph_rows: Sequence[dict]) -> Tuple[
        Optional[CellFrame], Optional[str]]:
    """(frame, why-not). ⚠️ THE CONTROL IS THE SECOND ANCHOR AND IT CAN FAIL.

    Every glyph in a cell was mapped by ONE `upscale_factor` and ONE cell
    origin, so every anchor must agree. Where they do not, the cell's rows were
    not all measured in one frame and no human box may be converted into it —
    refused, named, and reported, because a box in the wrong frame is a
    measurement that looks exactly like a right one.
    """
    ests: List[Tuple[float, float, float]] = []
    for r in cell_glyph_rows:
        val = r.get("value")
        det = r.get("detail") or {}
        bb = det.get("bbox_page_px")
        if not (isinstance(val, (list, tuple)) and len(val) == 5):
            continue
        if not (isinstance(bb, (list, tuple)) and len(bb) == 4):
            continue
        _name, x_c, y_c, w_c, h_c = val
        px0, py0, px1, py1 = (float(v) for v in bb)
        if px1 - px0 <= 0 or py1 - py0 <= 0 or float(w_c) <= 0 \
                or float(h_c) <= 0:
            continue
        up_w = float(w_c) / (px1 - px0)
        up_h = float(h_c) / (py1 - py0)
        if abs(up_w - up_h) > FRAME_SCALE_TOLERANCE * max(up_w, up_h):
            # ⚠️ NOT SKIPPED QUIETLY: a cell whose x and y scales disagree is
            # not the frame `_page_box` describes, and one such anchor is
            # enough to refuse the cell.
            return None, (f"anchor {r.get('id')} disagrees with itself: "
                          f"x-scale {up_w:.6f} vs y-scale {up_h:.6f}")
        up = (up_w + up_h) / 2.0
        ests.append((up, px0 - float(x_c) / up, py0 - float(y_c) / up))
    if not ests:
        return None, ("no anchor: this cell holds no Q.GLYPH_BOX row carrying "
                      "BOTH a canonical box and detail.bbox_page_px, so the "
                      "cell's own page frame is not on the record")
    up = sum(e[0] for e in ests) / len(ests)
    x0 = sum(e[1] for e in ests) / len(ests)
    y0 = sum(e[2] for e in ests) / len(ests)
    dev = None
    if len(ests) > 1:
        dev = max(max(abs(e[1] - x0), abs(e[2] - y0)) for e in ests)
        sdev = max(abs(e[0] - up) for e in ests)
        if dev > FRAME_OFFSET_TOLERANCE_PX or sdev > FRAME_SCALE_TOLERANCE * up:
            return None, (f"{len(ests)} anchors disagree: origin spread "
                          f"{dev:.3f} px (tolerance "
                          f"{FRAME_OFFSET_TOLERANCE_PX}), scale spread "
                          f"{sdev:.3e}")
    return CellFrame(up, x0, y0, len(ests), dev), None


@dataclass(frozen=True)
class CellGrid:
    """The staff grid INSIDE one cell's canonical frame: where the top line
    sits and how tall a half step is.

    `gather_notehead_positions` divides a notehead's distance below the top
    line by the half-step height; this recovers both from the rows that
    computation already produced — the unit from `Q.CELL_STAFF_SPACE`'s own
    value, the origin from a notehead that carries both a canonical box and a
    recorded `Q.NOTEHEAD_STAFF_POSITION`.

    ⚠️ The half-step's detail key is deliberately NOT SPELLED ANYWHERE IN
    THIS FILE — code, docstring or comment. `wiring --check`'s mention test is
    a raw-text substring scan, so one occurrence would report a standing
    pipeline finding as CLOSED from a module that is not a stage. Same trap
    that module's own docstring records paying for four times.
    """

    top_y: float
    #: ONE STAFF STEP in canonical px — half a staff space, the unit
    #: `Q.NOTEHEAD_STAFF_POSITION` counts in.
    #:
    #: ⚠️ NOT NAMED AFTER THE DETAIL KEY `gather.py` writes beside
    #: `Q.CELL_STAFF_SPACE`, and not named anything CONTAINING it either:
    #: `wiring --check` looks for `.<key>` as a raw substring, so even a
    #: suffixed variant would report a standing pipeline finding as closed.
    #: See `recover_cell_grid`.
    step_c: float
    anchors: int
    max_deviation_c: Optional[float]

    def position_of(self, y_center_canonical: float) -> float:
        return (y_center_canonical - self.top_y) / self.step_c


def recover_cell_grid(record: dict, cell: Subject,
                      cell_glyph_rows: Sequence[dict]) -> Tuple[
        Optional[CellGrid], Optional[str]]:
    """(grid, why-not). The unit comes from `Q.CELL_STAFF_SPACE` — the one
    spelling of that measurement, never the nominal 100 px — and the origin
    from any notehead in the cell that carries both a canonical box and a
    recorded `Q.NOTEHEAD_STAFF_POSITION`. Two such noteheads CHECK each other.
    """
    half = None
    cell_key = cell.to_key()
    for o in record.get("observations") or ():
        if o.get("quantity") == Q.CELL_STAFF_SPACE \
                and o.get("subject") == cell_key:
            # ⚠️ THE VALUE, HALVED — NOT THE HALF-STEP DETAIL KEY THAT SITS
            # RIGHT BESIDE IT. The two are the same number by construction
            # (`gather_notehead_positions` files the value as twice the half
            # step), and `wiring --check` carries a standing finding that that
            # key is written and read by nobody. ⚠️⚠️ ITS MENTION TEST IS A
            # RAW-TEXT SUBSTRING SCAN, so writing the key anywhere in this
            # file — code, docstring OR COMMENT — reports the finding as
            # CLOSED and turns the check red. That is the trap `wiring`'s own
            # docstring records paying for four times (a gap list, a test, a
            # benchmark probe and an auditor, each closing a gap by naming
            # it); this is the fifth, and the answer is to read the VALUE,
            # which is what a consumer should have been reading anyway.
            # ⚠️ It is also the only correct read on a one-line percussion
            # cell, where that detail is not written at all and the value is
            # the line spacing.
            if o.get("value"):
                half = float(o["value"]) / 2.0
    if not half or half <= 0:
        return None, ("no unit: this cell has no Q.CELL_STAFF_SPACE "
                      "observation, so a distance cannot be turned into a "
                      "staff position at all")
    boxes = {r.get("subject"): r for r in cell_glyph_rows}
    tops: List[Tuple[str, float]] = []
    for o in record.get("observations") or ():
        if o.get("quantity") != Q.NOTEHEAD_STAFF_POSITION:
            continue
        box = boxes.get(o.get("subject"))
        if box is None:
            continue
        val = box.get("value")
        if not (isinstance(val, (list, tuple)) and len(val) == 5):
            continue
        _n, _x, y_c, _w, h_c = val
        y_center = float(y_c) + float(h_c) / 2.0
        tops.append((o.get("id"), y_center - float(o["value"]) * half))
    if not tops:
        return None, ("no anchor: this cell holds no notehead carrying BOTH a "
                      "canonical box and a Q.NOTEHEAD_STAFF_POSITION, so the "
                      "staff's top line has no recorded place in this frame")
    top = sum(t[1] for t in tops) / len(tops)
    dev = None
    if len(tops) > 1:
        dev = max(abs(t[1] - top) for t in tops)
        if dev > GRID_TOP_TOLERANCE_C:
            return None, (f"{len(tops)} anchors disagree about the top line by "
                          f"{dev:.3f} canonical px (tolerance "
                          f"{GRID_TOP_TOLERANCE_C}) — the cell's own line "
                          f"trace wanders, and a human box placed on the mean "
                          f"would be a measurement nobody made")
    return CellGrid(top, half, len(tops), dev), None


# ─────────────────────────────────────────────────────────────────────────────
# What the pipeline would DO with a human box — derived, never hand-listed
# ─────────────────────────────────────────────────────────────────────────────

#: The quantities a human box can be given. Consumed by `visibility()` and by
#: the tests; a change here changes the honest table rather than a comment.
HUMAN_BOX_QUANTITIES: Tuple[str, ...] = (
    Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.NOTEHEAD_STAFF_POSITION)

#: The quantities GATHER gives a detected notehead that a human box CANNOT
#: have, each with the reason. ⚠️ An inventory, never a suppression list.
HUMAN_BOX_ABSENT: Dict[str, str] = {
    Q.GLYPH_CONF: (
        "a person produced no softmax; writing a number here would convert "
        "'there is no such measurement' into a definite one"),
    Q.GLYPH_BAND_DISTANCE: (
        "produced by gather_ownership_evidence from the cell RASTER (a "
        "same-class overlap search); not derivable from rows, so a human box "
        "never enters glyph_owner's contest"),
    Q.GLYPH_LADDER: (
        "produced by gather_ownership_evidence from the cell RASTER (a "
        "ledger-rung search); not derivable from rows"),
    Q.BEAM_STROKE: "read off the cell raster by line_detection; not derivable",
    Q.FLAG: "read off the cell raster; not derivable from rows",
    Q.AUG_DOT: "read off the cell raster; not derivable from rows",
}


def visibility() -> dict:
    """WHICH STAGES SEE A HUMAN BOX — derived from the registry and the rules.

    ⚠️ TWO DIFFERENT QUESTIONS, AND CONFLATING THEM IS HOW A LANE REPORTS A
    QUANTITY AS LIVE THAT NOTHING EVER RECEIVES:

      `domain`   — decisions whose `subjects_from` names one of the human
                   box's quantities, i.e. decisions for which the human's
                   OFFSET-ORDINAL SUBJECT is a subject at all
                   (`adjudicate.subjects_for` walks `log.all_rows()`, so a row
                   at any ordinal creates one).
      `wants`    — decisions that DECLARE one of them as evidence. A decision
                   may want a quantity without the human's subject being in
                   its domain, in which case it sees the row only when it is
                   already looking at that glyph.

    EVALUATE and INFER are read off `evaluate.RULES` / `infer.RULES` the same
    way. EXPORT is not derived here: it walks `Q.GLYPH_BOX` rows directly and
    `rerun.py` MEASURES what reached the file instead of predicting it.
    """
    from .. import adjudicate, evaluate, infer
    from .. import adjudicators, consequences, inferences   # noqa: F401
    qs = set(HUMAN_BOX_QUANTITIES)
    domain, wants = {}, {}
    for quantity, spec in adjudicate.REGISTRY.items():
        d = set(adjudicate.domain_of(spec)) & qs
        if d:
            domain[spec.name] = sorted(d)
        w = set(spec.wants) & qs
        if w:
            wants[spec.name] = sorted(w)
    ev = {r.name: r.cause for r in getattr(evaluate, "RULES", ())
          if getattr(r, "cause", None) in qs}
    inf = {getattr(r, "name", str(r)): sorted(set(getattr(r, "reads", ())) & qs)
           for r in getattr(infer, "RULES", ())
           if set(getattr(r, "reads", ())) & qs}
    return {"quantities": sorted(qs),
            "absent": {k: HUMAN_BOX_ABSENT[k] for k in sorted(HUMAN_BOX_ABSENT)},
            "adjudicate_domain": domain, "adjudicate_wants": wants,
            "evaluate_cause": ev, "infer_reads": inf}


# ─────────────────────────────────────────────────────────────────────────────
# The ingest
# ─────────────────────────────────────────────────────────────────────────────

def _reader_of(sidecar: dict, action: dict) -> str:
    """⚠️ THE VOCABULARY STAYS CLOSED. A sidecar naming a reviewer nobody has
    declared is refused here rather than widening `record.READERS` at run
    time: two rows from one reader are one signal, and a vocabulary a JSON
    file can extend cannot carry that meaning."""
    name = action.get("reader") or sidecar.get("reader") or READERS.SEAN
    if name not in READERS.all():
        raise SidecarError(
            f"reader {name!r} is not a member of record.READERS. Add the "
            f"reviewer there — deliberately, in a reviewed change — or use "
            f"{READERS.SESSION_TEST!r} for a session standing in for a human.")
    return name


def _obs_json(row_id: str, subject: str, quantity: str, value: Any, *,
              reader: str, frame: str, detail: dict,
              basis: Sequence[str] = ()) -> dict:
    """An Observation in exactly `Observation.to_json`'s spelling.

    ⚠️ `claim_of` IS CALLED HERE, for the reason `Log.observe` calls it: a
    quantity (or a reader-split quantity's reader) with no declared claim kind
    must fail on the run that introduces it, not the first time somebody reads
    the field.
    """
    claim_of(quantity, reader)
    return {"id": row_id, "subject": subject, "quantity": quantity,
            "value": value, "reader": reader, "frame": frame,
            # ⚠️ score=None, not 0.0 and not 1.0. `Q.NOTEHEAD_STAFF_POSITION`
            # has carried None since it was written for exactly this reason:
            # a ruler reading is not a guess, and a human's reading of the
            # print is not a scored one either.
            "score": None, "detail": dict(detail), "basis": list(basis)}


def human_glyph_subject(cell: Subject, n: int) -> Subject:
    """The nth human box in this cell, at the human offset ordinal."""
    return glyph(cell.page, cell.system, cell.staff, cell.cell,
                 HUMAN_GLYPH_BASE + n)


def ingest(record: dict, sidecar: dict, *,
           sidecar_path: Optional[str] = None,
           parent_path: Optional[str] = None,
           parent_md5: Optional[str] = None,
           provenance: Optional[dict] = None) -> Ingestion:
    """Append the sidecar's actions to `record` as rows. NEVER mutates input.

    ⚠️ APPEND-ONLY, AND THE ORDINALS SAY SO. Human rows take ids continuing
    the record's own counter, so a replay in ordinal order puts every human
    row AFTER every machine row — which is what happened, and lets a human row
    cite a machine row in its `basis` without the replay having to reorder.
    """
    check_sidecar(sidecar)
    out = copy.deepcopy(record)
    obs: List[dict] = out.setdefault("observations", [])
    n = _max_ordinal(out)
    outcomes: List[ActionOutcome] = []
    digest = sidecar_digest(sidecar)
    per_cell_count: Dict[str, int] = {}
    frames_refused = 0
    grids_refused = 0

    def new_id() -> str:
        nonlocal n
        n += 1
        return f"obs:{n:06d}"

    def base_detail(a: dict) -> dict:
        d = {"review_action": a.get("id"), "review_kind": a.get("kind"),
             "sidecar_sha256": digest}
        if sidecar_path:
            d["sidecar"] = str(sidecar_path)
        if a.get("t"):
            d["reviewed_at"] = a["t"]
        if a.get("note"):
            d["note"] = a["note"]
        return d

    for a in sidecar["actions"]:
        aid, kind = a["id"], a["kind"]
        oc = ActionOutcome(id=aid, kind=kind, stage=a.get("stage"),
                           note=a.get("note"))
        reader = _reader_of(sidecar, a)
        oc.detail["reader"] = reader
        if kind in STANCE_KINDS:
            vid = a["verdict"]
            shown = verdict_by_id(out, vid)
            if shown is None:
                oc.refused = (f"no verdict {vid!r} in this record — a stance "
                              f"on a verdict that is not here is not filed, "
                              f"because it would name nothing")
                outcomes.append(oc)
                continue
            oc.subject = shown.get("subject")
            rid = new_id()
            obs.append(_obs_json(
                rid, oc.subject, Q.HUMAN_VERDICT_STANCE, kind, reader=reader,
                frame="review:verdict",
                detail={**base_detail(a), "verdict_id": vid,
                        **_what_he_was_shown(shown)}))
            oc.rows.append(rid)
            outcomes.append(oc)
            continue

        if kind == "delete_box":
            gsub = a["glyph"]
            if not _subject_exists(out, gsub):
                oc.refused = (f"no rows on {gsub!r} in this record — a human "
                              f"cannot delete a box the record does not hold")
                outcomes.append(oc)
                continue
            oc.subject = gsub
            rid = new_id()
            obs.append(_obs_json(
                rid, gsub, Q.HUMAN_BOX_VERDICT, "not_a_symbol", reader=reader,
                frame="review:box",
                detail={**base_detail(a),
                        "bbox_page_px": a.get("bbox_page_px")}))
            oc.rows.append(rid)
            outcomes.append(oc)
            continue

        # ── add_box / redraw_box: a BOX, which needs the cell's frame ───────
        anchor_sub = a.get("glyph") or a.get("cell") or a.get("staff")
        cell = _cell_for_box(out, a)
        if cell is None:
            oc.refused = (
                "no cell: an add_box must name the `cell` it was drawn in, or "
                "a `glyph`/`staff` this module can resolve one from — a box "
                "with no cell has no canonical frame and no subject")
            outcomes.append(oc)
            continue
        cell_rows = _glyph_rows_of_cell(out, cell)
        frame, why = recover_cell_frame(cell_rows)
        if frame is None:
            frames_refused += 1
            oc.refused = f"frame not recoverable for {cell.to_key()}: {why}"
            oc.detail["cell"] = cell.to_key()
            outcomes.append(oc)
            continue
        oc.detail.update(cell=cell.to_key(), frame_anchors=frame.anchors,
                         frame_max_deviation_px=frame.max_deviation_px,
                         upscale=frame.upscale)

        k = per_cell_count.get(cell.to_key(), 0)
        per_cell_count[cell.to_key()] = k + 1
        gsub = human_glyph_subject(cell, k)
        oc.subject = gsub.to_key()
        category = a.get("category") or _category_of(out, a.get("glyph")) or ""
        x_c, y_c, w_c, h_c = frame.to_canonical(a["bbox_page_px"])
        px0, py0, px1, py1 = (float(v) for v in a["bbox_page_px"])
        det = {**base_detail(a),
               "category": _category_word(category),
               "bbox_page_px": [px0, py0, px1, py1],
               "x_center_page": (px0 + px1) / 2.0,
               "y_center_page": (py0 + py1) / 2.0,
               "frame_recovered_from": [r["id"] for r in cell_rows[:8]],
               "frame_anchors": frame.anchors}
        if kind == "redraw_box":
            det["replaces_box_of"] = a["glyph"]
        rid = new_id()
        obs.append(_obs_json(
            rid, gsub.to_key(), Q.GLYPH_BOX,
            [category, x_c, y_c, w_c, h_c], reader=reader,
            frame=f"cell:{cell.cell}", detail=det))
        oc.rows.append(rid)
        box_row_id = rid

        if str(category).startswith(NOTEHEAD_PREFIX):
            rid = new_id()
            obs.append(_obs_json(
                rid, gsub.to_key(), Q.NOTEHEAD_CLASS, category, reader=reader,
                frame=f"cell:{cell.cell}", detail=base_detail(a),
                basis=[box_row_id]))
            oc.rows.append(rid)
            grid, why = recover_cell_grid(out, cell, cell_rows)
            if grid is None:
                grids_refused += 1
                oc.absent[Q.NOTEHEAD_STAFF_POSITION] = why or "unrecoverable"
            else:
                pos = grid.position_of(y_c + h_c / 2.0)
                rid = new_id()
                obs.append(_obs_json(
                    rid, gsub.to_key(), Q.NOTEHEAD_STAFF_POSITION, pos,
                    reader=reader, frame=f"cell:{cell.cell}",
                    detail={**base_detail(a),
                            "residual": abs(pos - round(pos)),
                            "rounded": int(round(pos)),
                            "grid_anchors": grid.anchors,
                            "grid_max_deviation_c": grid.max_deviation_c,
                            # ⚠️ DERIVED, and it says so. A human drew a box;
                            # he did not measure a staff position. The
                            # arithmetic is the record's own.
                            "derived": "position from the human box and the "
                                       "cell's own recovered grid"},
                    basis=[box_row_id]))
                oc.rows.append(rid)
        for q, why_absent in HUMAN_BOX_ABSENT.items():
            oc.absent.setdefault(q, why_absent)
        if kind == "redraw_box":
            rid = new_id()
            obs.append(_obs_json(
                rid, a["glyph"], Q.HUMAN_BOX_VERDICT, "redrawn", reader=reader,
                frame="review:box",
                detail={**base_detail(a), "replaced_by": gsub.to_key()}))
            oc.rows.append(rid)
        outcomes.append(oc)

    out["counts"] = {"observations": len(out.get("observations") or ()),
                     "abstentions": len(out.get("abstentions") or ()),
                     "verdicts": len(out.get("verdicts") or ())}
    ing = Ingestion(record=out, actions=outcomes, controls={
        "actions": len(sidecar["actions"]),
        "rows_filed": sum(len(o.rows) for o in outcomes),
        "actions_refused": sum(1 for o in outcomes if o.refused),
        "frames_refused": frames_refused,
        "grids_refused": grids_refused,
        "sidecar_sha256": digest,
        "first_human_row_ordinal": _max_ordinal(record) + 1,
    })
    ing.controls["provenance"] = _review_provenance(
        provenance, sidecar, digest, sidecar_path, parent_path, parent_md5,
        len(sidecar["actions"]))
    return ing


def _review_provenance(parent_prov, sidecar, digest, sidecar_path,
                       parent_path, parent_md5, n_actions) -> dict:
    """⚠️ A NEW RECORD NAMES ITS PARENT, OR IT IS NOT A DERIVED RECORD — it is
    an unexplained gather. CLAUDE.md §4b: a record that cannot name the tree
    that built it is not a baseline; the same argument, one level up."""
    out = {"parent": {"record": parent_path, "md5": parent_md5,
                      "provenance": copy.deepcopy(parent_prov)},
           "sidecar": {"path": (str(sidecar_path) if sidecar_path else None),
                       "sha256": digest, "actions": n_actions,
                       "staff": sidecar.get("staff"),
                       "record_named_by_sidecar": sidecar.get("record")},
           "amended_at": _dt.datetime.now().astimezone().isoformat()}
    if parent_md5 is None:
        out["parent"]["warning"] = (
            "⚠️ the parent record was not hashed, so this amended record "
            "cannot prove which record it was amended from. Do not compare it "
            "with another.")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Small lookups over the record dict
# ─────────────────────────────────────────────────────────────────────────────

def _what_he_was_shown(v: dict) -> dict:
    """The verdict as it stood WHEN THE HUMAN LOOKED, copied onto his row.

    ⚠️⚠️ THIS IS `factsheet.merge`'s `reader_said`, ONE LAYER DOWN, AND THE
    ARGUMENT IS THE SAME ONE. A disagreement is uninterpretable without what
    was disagreed WITH: *"a hand-typed publisher dropped an umlaut the catalog
    had right, and the sheet dutifully filed the CATALOG as the thing that was
    wrong"* — which side is correct is a further act of adjudication, and
    keeping the reader's answer beside the human's is what leaves that act
    possible.

    ⚠️ AND THERE IS A SECOND REASON, FOUND BY A TEST. A VERDICT ID IS NOT
    STABLE ACROSS A RE-DECISION: `rerun` re-runs ADJUDICATE from the GATHER
    rows, so `vrd:000029` in the arm is a DIFFERENT verdict from
    `vrd:000029` in the parent. Resolving the stance by id against the arm
    returned the wrong verdict, and it returned one that looked perfectly
    plausible (`group_symbol`/`bracket` where the clef was expected). The id
    is kept because it is what the viewer sent; the SNAPSHOT is what makes the
    row mean something, and (quantity, subject) is what a consumer re-resolves
    against the arm.
    """
    return {"verdict_quantity": v.get("quantity"),
            "verdict_outcome": v.get("outcome"),
            "verdict_value": v.get("value"),
            "verdict_reason": v.get("reason"),
            "verdict_decider": v.get("decider"),
            "verdict_margin": v.get("margin"),
            "verdict_rows_used": list(v.get("used") or ()),
            "verdict_rows_considered": len(v.get("considered") or ())}


def _verdict_subject(record: dict, verdict_id: str) -> Optional[str]:
    for v in record.get("verdicts") or ():
        if v.get("id") == verdict_id:
            return v.get("subject")
    return None


def verdict_by_id(record: dict, verdict_id: str) -> Optional[dict]:
    for v in record.get("verdicts") or ():
        if v.get("id") == verdict_id:
            return v
    return None


def _subject_exists(record: dict, subject: str) -> bool:
    for key in ("observations", "abstentions", "verdicts"):
        for r in record.get(key) or ():
            if r.get("subject") == subject:
                return True
    return False


def _category_of(record: dict, glyph_key: Optional[str]) -> Optional[str]:
    if not glyph_key:
        return None
    for o in record.get("observations") or ():
        if o.get("subject") == glyph_key and o.get("quantity") == Q.GLYPH_BOX:
            v = o.get("value")
            if isinstance(v, (list, tuple)) and v:
                return str(v[0])
    return None


def _category_word(smufl_name: str) -> str:
    """The detector's coarse `category` word beside the fine class name.

    ⚠️ Imported from the one place that spells it, never re-derived here: a
    second table of class -> category is how two readers of one record come to
    disagree about what a box is.
    """
    from ...yolo_detector import _class_name_to_category
    return _class_name_to_category(smufl_name) or "unknown"


def _cell_for_box(record: dict, action: dict) -> Optional[Subject]:
    """Which CELL a drawn box belongs to.

    ⚠️ NAMED BY THE VIEWER OR RESOLVED FROM A NAMED GLYPH — never guessed from
    geometry. Deciding which cell a page-pixel box falls in is exactly the
    padded-cell contest CLAUDE.md §10 says is resolved by `glyph_owner` and
    never by a bounding test, and a review tool inventing an answer there
    would put the human's evidence on the wrong staff.
    """
    for key in ("cell", "glyph"):
        raw = action.get(key)
        if not raw:
            continue
        try:
            sub = Subject.from_key(str(raw))
        except Exception:
            continue
        c = _cell_of(sub)
        if c is not None:
            return c
    return None
