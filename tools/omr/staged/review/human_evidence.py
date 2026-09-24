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

from ..record import (ABSTAIN, Kind, Q, READERS, Subject, claim_of, glyph,
                      staff as _staff_subject)

# ─────────────────────────────────────────────────────────────────────────────
# The sidecar
# ─────────────────────────────────────────────────────────────────────────────

#: Every `kind` lane (B) may write. An unknown one is REFUSED, never ignored:
#: a viewer that grows a verb this module has not been taught would otherwise
#: have its actions silently dropped and the review would read as complete.
GATHER_KINDS = ("add_box", "delete_box", "redraw_box", "relabel_box",
                "own_box", "dup_box", "unsure_box", "confirm_box")
STANCE_KINDS = ("agree", "disagree")
STAGES = ("gather", "adjudicate", "evaluate", "infer", "export")

#: ⚠️⚠️ THE ONE TABLE OF "WHAT IS THIS?" ANSWERS, AND EVERYTHING ELSE DERIVES
#: FROM IT — `check_sidecar`'s required fields, the server's `/api/labels`,
#: the viewer's panel, `SIDECAR.md`'s table and `visibility()`'s report. Sean,
#: 2026-09-23: *"and to label boxes as nothing or belongs to another staff
#: etc."* — the *etc.* is his, so the set must be extensible in ONE place.
#:
#: `reaches` is a CLAIM THIS MODULE MAKES AND `rerun.py` MEASURES. It is not
#: how the answer is routed; it is what a reader should expect, and a run that
#: contradicts it is the finding, not a bug in the table.
HUMAN_BOX_LABELS: Tuple[Dict[str, Any], ...] = (
    {"label": "a symbol of class …", "kind": "relabel_box",
     "needs": ("glyph", "category"), "key": "category",
     "value": "is_a:<class>", "row": "observation",
     "reaches": "adjudicate_notehead_is_not_a_notehead (refuses the head "
                "where the class is OUTSIDE the notehead family); the new "
                "class is filed as a HUMAN BOX of its own, which every "
                "decision whose domain that class enters then decides on",
     "keys": "l"},
    {"label": "nothing — not a symbol", "kind": "delete_box",
     "needs": ("glyph",), "key": None,
     "value": "not_a_symbol", "row": "observation",
     "reaches": "adjudicate_notehead_is_not_a_notehead, reason "
                "`human_not_a_symbol`",
     "keys": "0 / d"},
    {"label": "belongs to another staff", "kind": "own_box",
     "needs": ("glyph", "staff"), "key": "staff",
     "value": "owner:<staff subject>", "row": "observation",
     "reaches": "adjudicate_glyph_owner, reason `human_owner` — but ONLY on a "
                "glyph already in that decision's domain (`subjects_from="
                "Q.GLYPH_BAND_DISTANCE`, the CONTESTED population). On an "
                "uncontested glyph the row is filed and reaches nothing, and "
                "the feedback file says so.",
     "keys": "↑ / ↓"},
    {"label": "a duplicate of another box", "kind": "dup_box",
     "needs": ("glyph", "of"), "key": "of",
     "value": "duplicate_of:<glyph subject>", "row": "observation",
     "reaches": "adjudicate_notehead_is_not_a_notehead, reason "
                "`human_not_a_symbol`, `detail.human_says` naming the twin — "
                "one piece of ink, one note",
     "keys": "="},
    {"label": "I can't tell", "kind": "unsure_box",
     "needs": ("glyph",), "key": None,
     "value": None, "row": "abstention",
     "reaches": "NOTHING, deliberately. An Abstention with reason "
                "`human_unsure`: a place the PRINT is ambiguous, reported by "
                "review/feedback.py and read by no stage.",
     "keys": "u"},
    # ⚠️ ROADMAP 3.4d — AN ADDITION, AND IT IS NOT A STANCE ON A VERDICT.
    # Sean types the class he sees; where that is the class the detector
    # already gave the box, he has AGREED with a GATHER row, and `agree` in
    # this contract is a stance on a VERDICT (`verdict_by_id` refuses an id
    # that names no verdict, and `Q.GLYPH_BOX` is an Observation). So the
    # agreement is its own verb rather than a second meaning for `agree`.
    # ⚠️ IT REACHES NOTHING AND IS NOT MEANT TO: `human_says` returns the
    # verb `confirmed`, which neither `notehead_precision._human_not_a_symbol`
    # nor `ownership._human_owner` acts on. What it buys is the distinction
    # the record exists for — a reader who LOOKED and agreed is not a reader
    # who never looked, and only the first of those two leaves a row.
    {"label": "yes, that is what it is", "kind": "confirm_box",
     "needs": ("glyph", "category"), "key": "category",
     "value": "confirmed:<class>", "row": "observation",
     "reaches": "NOTHING, by design. It is a READ row where there would "
                "otherwise be no row at all, so `review/feedback.py` can say "
                "which boxes a human went over and agreed with — the "
                "denominator every other label is a numerator of.",
     "keys": "Enter on the class already shown"},
)

#: kind -> the sidecar fields that kind cannot do without. DERIVED from the
#: table above plus the two box verbs that predate it.
KIND_REQUIRES: Dict[str, Tuple[str, ...]] = {
    **{e["kind"]: tuple(e["needs"]) for e in HUMAN_BOX_LABELS},
    "add_box": ("bbox_page_px", "category"),
    "redraw_box": ("glyph", "bbox_page_px"),
}

#: The `Q.HUMAN_BOX_VERDICT` values that carry an argument after a colon.
_PREFIXED = ("is_a", "owner", "duplicate_of", "confirmed")


def human_says(value: Any) -> Tuple[str, Optional[str]]:
    """`"is_a:clefCAlto"` -> `("is_a", "clefCAlto")`; `"not_a_symbol"` ->
    `("not_a_symbol", None)`.

    ⚠️ THE ONE PARSER, imported by every consumer. A second `split(":", 1)`
    somewhere in an adjudicator is how a value spelling comes to mean two
    things; `notehead_precision._human_not_a_symbol` and
    `ownership._human_owner` both call this.
    """
    s = str(value or "")
    for pre in _PREFIXED:
        if s.startswith(pre + ":"):
            return pre, s[len(pre) + 1:]
    return s, None

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

#: ⚠️ GATHER'S OWN CLEF TEST, IMPORTED WITH ITS CATEGORY HALF. See
#: `gather._is_clef_class`: dropping the category argument admits 27 classes
#: as clefs, `flag8thUp` among them as a BASS clef.
from ..gather import _is_clef_class            # noqa: E402


def R_staff_of(cell: Subject) -> Subject:
    """The STAFF a cell belongs to. ⚠️ Through `record.staff`, not by string
    surgery on the key: a subject's spelling is the record's business."""
    return _staff_subject(cell.page, cell.system, cell.staff)

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
        # ⚠️ DERIVED FROM `KIND_REQUIRES`, never re-listed per verb: a label
        # added to `HUMAN_BOX_LABELS` is validated the moment it exists, which
        # is the only way an extensible set stays checked.
        for fld in KIND_REQUIRES.get(kind, ()):
            if not a.get(fld):
                raise SidecarError(
                    f"action {aid}: a {kind} names no `{fld}`"
                    + (". A box with no name is `Q.INK`, which GATHER already "
                       "files and this module may not manufacture."
                       if fld == "category" else ""))
        if kind in ("add_box", "redraw_box"):
            bb = a.get("bbox_page_px")
            if not (isinstance(bb, (list, tuple)) and len(bb) == 4):
                raise SidecarError(
                    f"action {aid}: a {kind} needs `bbox_page_px` "
                    f"[x0, y0, x1, y1] in PAGE pixels at the gather's own DPI")


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
    Q.GLYPH_BOX, Q.NOTEHEAD_CLASS, Q.NOTEHEAD_STAFF_POSITION,
    # ⚠️ ON THE STAFF SUBJECT, NOT THE GLYPH'S — filed only for a clef-class
    # box in CELL 0, the one place `gather_clefs` looks. A human box of a
    # notehead class never carries these and a clef-class box in cell 7 does
    # not either; both facts are reported per action in `absent`.
    Q.CLEF_GLYPH, Q.CLEF_POSITION)

#: The `Q.HUMAN_BOX_VERDICT` values (and the one abstention) a LABEL files.
#: Derived from the table so a new label appears in `visibility()` the moment
#: it exists rather than the next time somebody remembers this list.
HUMAN_LABEL_QUANTITIES: Tuple[str, ...] = (Q.HUMAN_BOX_VERDICT,)

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

    def _over(qs: set) -> dict:
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
        # ⚠️ `Rule` HAS NO `.name` — the first cut's `getattr(r, "name",
        # str(r))` fell through to the dataclass repr, so this table's INFER
        # half printed a 2,000-character `Rule(...)` blob as the rule's name.
        # The rule's own `Inference` enum is the spelling `infer.py` uses.
        inf = {r.inference.value: sorted(set(getattr(r, "reads", ())) & qs)
               for r in getattr(infer, "RULES", ())
               if set(getattr(r, "reads", ())) & qs}
        return {"quantities": sorted(qs), "adjudicate_domain": domain,
                "adjudicate_wants": wants, "evaluate_cause": ev,
                "infer_reads": inf}

    out = _over(set(HUMAN_BOX_QUANTITIES))
    out["absent"] = {k: HUMAN_BOX_ABSENT[k] for k in sorted(HUMAN_BOX_ABSENT)}
    # ⚠️ THE LABELS ARE A SECOND, DIFFERENT QUESTION AND ARE REPORTED APART.
    # A human BOX is a subject the stages decide ON; a human LABEL is a row
    # filed on a subject the MACHINE already owns, and a decision reaches it
    # only if it DECLARES `Q.HUMAN_BOX_VERDICT` in `wants` — which two do.
    # Folding the two tables into one is how a lane reports a quantity as
    # live that nothing ever receives.
    out["labels"] = {
        "table": [dict(e) for e in HUMAN_BOX_LABELS],
        "on_the_machines_own_subject": _over(set(HUMAN_LABEL_QUANTITIES)),
        "⚠️": ("`unsure_box` files an ABSTENTION, so it appears in no "
               "`wants` list and reaches nothing by design — "
               "ABSTAIN.HUMAN_UNSURE says why."),
    }
    return out


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


def _abs_json(row_id: str, subject: str, quantity: str, *, reader: str,
              frame: str, reason: str, detail: dict) -> dict:
    """An Abstention in exactly `Abstention.to_json`'s spelling.

    ⚠️ `ABSTAIN.check` IS CALLED HERE for `Log.abstain`'s reason: a reason
    word outside the closed vocabulary must fail on the run that introduces
    it, not on the replay, where it would surface as a `_Vocab` error from
    inside `rebuild_gather` with no sidecar in sight.
    """
    ABSTAIN.check(reason, "abstention reason")
    claim_of(quantity, reader)
    return {"id": row_id, "subject": subject, "quantity": quantity,
            "reader": reader, "frame": frame, "reason": reason,
            "detail": dict(detail)}


def _page_box_of(record: dict, glyph_key: Optional[str]
                 ) -> Optional[Sequence[float]]:
    """The PAGE rectangle on a glyph's own `Q.GLYPH_BOX` row, or None.

    ⚠️ DECLINED, NEVER DEFAULTED. A canonical cell frame cannot answer a page
    question (CLAUDE.md §10), so a row without `detail.bbox_page_px` has no
    page rectangle and a relabel of it is refused rather than placed.
    """
    if not glyph_key:
        return None
    for o in record.get("observations") or ():
        if o.get("subject") == glyph_key and o.get("quantity") == Q.GLYPH_BOX:
            bb = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(bb, (list, tuple)) and len(bb) == 4:
                return [float(v) for v in bb]
    return None


def _twin_on(record: dict, glyph_key: str, staff_key: str) -> Optional[str]:
    """Does the staff he named hold the SAME ink, boxed on its own side?

    ⚠️⚠️ THIS IS NOT A REPAIR AND MUST NOT BECOME ONE. A cross-staff contest
    is resolved by DROPPING the loser, never by relocating it (CLAUDE.md §10),
    so awarding a glyph to a staff whose own detector never boxed that ink
    removes a note and adds none. The answer is recorded on the human's row so
    the feedback file can say which of the two happened, and `rerun.py`
    MEASURES the note count either way.

    The test is the record's own: a `Q.GLYPH_BAND_DISTANCE` row on this glyph
    whose `detail.candidate` is that staff means GATHER already found the
    same-category ink there and opened the contest. Anything else is None.

    Whether that staff is the glyph's OWN is carried too, because the
    commonest `own_box` is a human pulling a glyph BACK to the staff it was
    cut from — and there the "twin" IS the glyph itself. A bare row id would
    let a reader of the feedback file conclude that a second copy exists
    somewhere when it does not.

    ⚠️⚠️ AND IT IS DERIVED FROM THE SUBJECT, NOT READ OFF THE BAND ROW'S OWN
    DETAIL — which carries exactly that flag and would have been the obvious
    read. `wiring --check`'s DETAIL question is a RAW-TEXT SUBSTRING SCAN over
    everything under `tools/`, so one mention of that key in this file
    reported a standing pipeline finding as CLOSED and turned the check red
    (seen: 69 problems, 1 STALE gap entry). A review instrument reading a
    detail key does not make a STAGE consume it, which is the same argument
    `recover_cell_grid` records paying for one function along. The glyph's own
    staff is in its subject; nothing else is needed.
    """
    try:
        mine = Subject.from_key(glyph_key).at(Kind.STAFF)
    except Exception:
        mine = None
    is_own = bool(mine is not None and mine.to_key() == staff_key)
    for o in record.get("observations") or ():
        if o.get("subject") != glyph_key:
            continue
        if o.get("quantity") != Q.GLYPH_BAND_DISTANCE:
            continue
        if str((o.get("detail") or {}).get("candidate") or "") == staff_key:
            return {"band_row": o.get("id"),
                    "is_the_glyphs_own_staff": is_own,
                    "means": ("this glyph was CUT from that staff's own cell"
                              if is_own else
                              "GATHER opened a contest for this ink on that "
                              "staff, so the ink is boxed there too")}
    return None


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

        # ── the LABEL verbs: one row on the box he was looking at ──────────
        # ⚠️ ONE BRANCH FOR ALL OF THEM, KEYED OFF `HUMAN_BOX_LABELS`. A
        # per-verb branch is how the fifth label added next month gets filed
        # with a subtly different frame or a missing `basis`.
        if kind in ("delete_box", "own_box", "dup_box", "unsure_box",
                    "confirm_box"):
            gsub = a["glyph"]
            if not _subject_exists(out, gsub):
                oc.refused = (f"no rows on {gsub!r} in this record — a human "
                              f"cannot label a box the record does not hold")
                outcomes.append(oc)
                continue
            oc.subject = gsub
            det = {**base_detail(a), "bbox_page_px": a.get("bbox_page_px")}
            if kind == "unsure_box":
                # ⚠️⚠️ AN ABSTENTION, NOT A VALUE. See `ABSTAIN.HUMAN_UNSURE`:
                # a reader who declined and a reader who answered are what
                # `State.DECLINED` and `State.READ` exist to keep apart, and
                # this is the record's first chance to say that of a PERSON.
                rid = new_id()
                out.setdefault("abstentions", []).append(_abs_json(
                    rid, gsub, Q.HUMAN_BOX_VERDICT, reader=reader,
                    frame="review:box", reason=ABSTAIN.HUMAN_UNSURE,
                    detail=det))
                oc.rows.append(rid)
                oc.detail["row_kind"] = "abstention"
                outcomes.append(oc)
                continue
            if kind == "own_box":
                target = str(a["staff"])
                try:
                    tsub = Subject.from_key(target)
                except Exception:
                    tsub = None
                if tsub is None or tsub.at(Kind.STAFF) is None:
                    oc.refused = (
                        f"`staff` {target!r} is not a staff subject — an "
                        f"owner must be named as `staff/<page>/<system>/"
                        f"<ordinal>`, never as a part name")
                    outcomes.append(oc)
                    continue
                target = tsub.at(Kind.STAFF).to_key()
                value = f"owner:{target}"
                det["owner_named"] = target
                # ⚠️ REPORTED, NEVER REPAIRED. CLAUDE.md §10: a resolved
                # contest DROPS the loser and never relocates it. If the named
                # staff holds no twin of this ink, awarding it there removes a
                # note and adds none — which is what `rerun.py` will measure.
                det["twin_on_the_named_staff"] = _twin_on(out, gsub, target)
            elif kind == "dup_box":
                other = str(a["of"])
                if not _subject_exists(out, other):
                    oc.refused = (f"`of` {other!r} holds no rows in this "
                                  f"record — a duplicate names the box it "
                                  f"duplicates, and that box must be here")
                    outcomes.append(oc)
                    continue
                value = f"duplicate_of:{other}"
                det["duplicate_of"] = other
            elif kind == "confirm_box":
                # ⚠️ WHAT HE AGREED WITH, NOT JUST THAT HE AGREED. The class
                # travels in the value, so a confirmation filed against one
                # reading of a box cannot be read as confirming a later,
                # different one. The machine's own class is recorded beside
                # it, and where the two differ THAT is the finding.
                said = str(a["category"])
                value = f"confirmed:{said}"
                det["confirmed_class"] = said
                det["machine_called_it"] = _category_of(out, gsub)
            else:
                value = "not_a_symbol"
            rid = new_id()
            obs.append(_obs_json(
                rid, gsub, Q.HUMAN_BOX_VERDICT, value, reader=reader,
                frame="review:box", detail=det))
            oc.rows.append(rid)
            outcomes.append(oc)
            continue

        # ── add_box / redraw_box / relabel_box: a BOX, which needs the
        #    cell's frame ────────────────────────────────────────────────────
        if kind == "relabel_box":
            # ⚠️ A RELABEL IS TWO CLAIMS AND FILES BOTH: *that box is not what
            # you called it* (on the machine's own subject, so the refusal can
            # read it) and *there is a <class> HERE* (a human box of its own,
            # so the new class enters the pipeline as a subject rather than as
            # a note in a file). Neither half is an edit of a machine row.
            gsub_old = a["glyph"]
            if not _subject_exists(out, gsub_old):
                oc.refused = (f"no rows on {gsub_old!r} in this record — a "
                              f"human cannot relabel a box the record does "
                              f"not hold")
                outcomes.append(oc)
                continue
            if not a.get("bbox_page_px"):
                # ⚠️ THE MACHINE'S OWN PAGE RECTANGLE, or nothing. He said
                # *this box is a clef*, not *a clef is somewhere near here*;
                # inventing a rectangle would be a measurement nobody made.
                page = _page_box_of(out, gsub_old)
                if page is None:
                    oc.refused = (
                        f"{gsub_old!r} carries no `detail.bbox_page_px`, so "
                        f"the box he relabelled has no page rectangle and the "
                        f"new class cannot be filed as a box of its own "
                        f"(DECLINED, not defaulted). The `is_a:` row is not "
                        f"filed either, because half a relabel is worse than "
                        f"none.")
                    outcomes.append(oc)
                    continue
                a = dict(a, bbox_page_px=list(page))

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
        if kind == "relabel_box":
            det["relabel_of"] = a["glyph"]
            det["machine_called_it"] = _category_of(out, a["glyph"])
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
        elif _is_clef_class(category, _category_word(category)):
            # ⚠️⚠️ THE CLEF CONNECT, AND IT IS A CONNECT RATHER THAN A GUESS
            # BECAUSE IT FILES THE SAME TWO ROWS GATHER FILES, MEASURED THE
            # SAME WAY. `gather_clefs` gives a detected clef a `Q.CLEF_GLYPH`
            # row on the STAFF (not on the glyph) and a `Q.CLEF_POSITION` row
            # beside it from the cell's own grid; both come out of the cell's
            # rows here, with the grid control that can fail. The class test
            # is `gather._is_clef_class`, imported — including its CATEGORY
            # half, which that function's own docstring records as
            # load-bearing (without it 27 classes read as clefs).
            #
            # ⚠️ CELL 0 ONLY, and that is gather's rule, not a convenience:
            # *a clef is read at the head of the staff*. A human box of a clef
            # class in cell 7 is a MID-STAFF CLEF CHANGE, which gather does
            # not gather and this module may not invent a reading of.
            # ⚠️ AND THE SCORE IS None. `clef._detector_terms` weights by
            # `row.score`, reading None as 0.0 and therefore as
            # `W_DETECTOR_LOW` — so a human's clef enters the contest as the
            # WEAKEST kind of witness. That is wrong and it is REPORTED here
            # rather than repaired by inventing a confidence: fixing it is a
            # change to `clef.py`'s weighting, with its own measurement.
            staff_sub = R_staff_of(cell)
            if cell.cell != 0:
                oc.absent[Q.CLEF_GLYPH] = (
                    f"a clef is gathered at the HEAD of the staff (cell 0) "
                    f"and this box is in cell {cell.cell}; a mid-staff clef "
                    f"change is a reading GATHER does not make and this "
                    f"module may not invent")
            else:
                rid = new_id()
                obs.append(_obs_json(
                    rid, staff_sub.to_key(), Q.CLEF_GLYPH, category,
                    reader=reader, frame=f"cell:{cell.cell}",
                    detail={**base_detail(a),
                            "y_center": y_c + h_c / 2.0,
                            "x_center": x_c + w_c / 2.0,
                            "human_box": gsub.to_key(),
                            "score_is_None": (
                                "a person produced no softmax; "
                                "clef._detector_terms reads None as 0.0 and "
                                "weights it W_DETECTOR_LOW")},
                    basis=[box_row_id]))
                oc.rows.append(rid)
                grid, why = recover_cell_grid(out, cell, cell_rows)
                if grid is None:
                    grids_refused += 1
                    oc.absent[Q.CLEF_POSITION] = why or "unrecoverable"
                else:
                    rid = new_id()
                    obs.append(_obs_json(
                        rid, staff_sub.to_key(), Q.CLEF_POSITION,
                        grid.position_of(y_c + h_c / 2.0), reader=reader,
                        frame=f"cell:{cell.cell}",
                        detail={**base_detail(a), "glyph": category,
                                "y_center": y_c + h_c / 2.0,
                                "grid_anchors": grid.anchors,
                                "grid_max_deviation_c": grid.max_deviation_c,
                                "derived": "position from the human box and "
                                           "the cell's own recovered grid"},
                        basis=[box_row_id]))
                    oc.rows.append(rid)
        for q, why_absent in HUMAN_BOX_ABSENT.items():
            oc.absent.setdefault(q, why_absent)
        if kind == "relabel_box":
            rid = new_id()
            obs.append(_obs_json(
                rid, a["glyph"], Q.HUMAN_BOX_VERDICT, f"is_a:{category}",
                reader=reader, frame="review:box",
                detail={**base_detail(a), "is_a": category,
                        "machine_called_it": _category_of(out, a["glyph"]),
                        "filed_as": gsub.to_key()}))
            oc.rows.append(rid)
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
