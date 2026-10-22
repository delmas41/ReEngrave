"""The hand-truth SCORER, first version: one STAGED record against one hand-labeled page
(ROADMAP 1.7, plan Phase D, items D1 and D2), at GATHER + ADJUDICATE only.

    python3 -m tools.omr.hand_truth.score --page data/hand-truth/pages/imslp317803/0.json \
        --record <record.json> --derive [--pdf <score.pdf>] [--out report.json] \
        [--crops-dir DIR --crop-cells s0-st3-m0 --crop-ink "x,y;x,y"]
    python3 -m tools.omr.hand_truth.score --controls --derive --page ...     # the D2 controls, no record needed

Exit 0 = scored; 3 = the frame control failed and nothing was printed (``--force`` prints anyway);
1 = a control failed (``--controls``).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md rule 3 -- nobody could be
asked before the build):

* ASSUMED: a truth notehead's ``staff_position`` is "steps from the middle line, UP positive"
  (``TRUTH_POSITION_UP_POSITIVE``). The store's docstring says only "steps from the middle line
  (0 = middle line)". FALSIFIED by the first box in which Sean enters a position -- NO TOOL WRITES
  ``owner_staff`` OR ``staff_position`` YET (0 of 1,342 boxes on the first page carry either).
* ASSUMED: the record's ``Q.NOTEHEAD_STAFF_POSITION`` is "half-steps DOWN from the top line"
  (``record.py``), so the middle line is 4. FALSIFIED by the self-score control (a truth box moved
  one step must read as one step wrong).
* ASSUMED: a head with NO ``glyph_owner`` verdict is on the staff its cell was cut from (the verdict's
  domain is the contested population; the export reads its absence the same way). An ABSTAINED or
  NARROWED owner is counted as abstained, never as the filed staff (rule 8).
* NOT CONFIRMED: that Sean's page-pixel frame is the gather's. The scorer MEASURES it (the frame
  control) and refuses to print a score when it fails; it does not assume it.

WHAT IT SCORES, AND WHAT IT REFUSES.

* A family is scored only over the cells that were INSPECTED for it (``completeness.families_covered``).
  A family no cell was inspected for is REFUSED -- not scored as zero (plan Phase B, rule 8). A truth
  box or a record glyph whose centre lies in no such cell is UNSCORED and counted, never a miss and
  never a false positive. A header (clef / key / meter) is scored from a staff's first measure cell
  only if that cell was fully labeled; "no box there" then means "not printed", not "not looked at".
* Matching is ``readout.match_glyphs`` -- the matcher ``readout diff`` uses -- imported, not rewritten.
  It is handed both sides FLATTENED into one bar (it groups by cell/staff, and a truth box has no
  cell in the record's sense), once per family, so a box matches by overlap alone, never by the
  staff or cell the record happened to file it under. Owner is judged AFTER the match, which is
  what lets a wrong owner be a wrong owner rather than a miss.
* Two stage views of the same record: GATHER (every detector box) and ADJUDICATE (boxes ADJUDICATE did
  not refuse as "not a <family>" and did not give to another staff's contest; an arc is filed under
  the kind ``Q.ARC_KIND`` decided, not the detector's first guess).
* Recall is split by how the truth box got onto the page. A ``prefill-confirmed`` box IS the
  production detector's own box (Sean confirmed it), so a record made with the same weights
  re-finds it by construction -- that column is ~1.0 for every family and says nothing. The recall of
  the detector is on the ``drawn`` boxes (what it did not supply), and precision is the unmatched
  record boxes of a fully labeled cell, split into duplicate / other family / spurious.
* Owner and staff position are judged against Sean's ``owner_staff`` / ``staff_position`` WHERE HE
  HAS WRITTEN THEM. Where he has not, ``--derive`` fills a DERIVED reference from his box and the
  cutter's staff lines, for heads inside their staff only, and every number built on it is labelled
  ``derived``: it is NOT Sean's label (rule 7: "Sean, the print or the reference encoding is
  evidence"), and the cutter's lines are the same staff detector the record used, so agreement is
  weaker evidence than it looks. Without ``--derive`` those noteheads are ``no_truth``. A head
  outside its staff is derived only from Sean's own ledger-line boxes (``derived:ledger``); one with
  none, or whose ledgers lead to two staves, stays ``no_truth``.
* The truth's OWN completeness is bounded with the repo's ink-coverage control (``--pdf``), but on a
  thick-lined scan that control also lists staff-line slivers and unboxed barlines, so it is a
  warning about precision, not a count of missed marks (see the FINDINGS and the ``ink-uncovered``
  crops).

STEMS (ROADMAP 1.7, Sean 2026-10-10 *"How reliably are we finding stems?"*): the stem family has TWO sources,
shown side by side -- the detector's ``stem`` class (``families["stem"]``, unchanged) and the CV reader the product
uses (``Q.STEM``, scored in ``score_stems`` into ``report["stems"]``: found / missed / invented per staff, the
per-head ``Q.HEAD_STEM`` attachment and ``Q.STEM_DIRECTION``, and the misses by cause). ``--stem-runs`` and
``--stem-ink`` tie a miss to the filter that refused it.

NOT YET (next steps, each a decision for Sean or a lane): the other CV readers as a source (beams, barlines,
braces are not detector classes; the record holds them as ``Q.BEAM_STROKE`` /
``Q.BARLINE_COLUMN`` rows in a cell frame); instrument names; the far-head position
from the ledgers rather than extrapolated lines; the third ``acceptance_quick`` view (the count page
must be labeled first); Sean's own ``owner_staff`` / ``staff_position`` for far heads.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from tools.omr import class_aliases
from tools.omr.hand_truth import store
from tools.omr.hand_truth.completeness import families_covered, family_of
from tools.omr.hand_truth.store import Cell, PageTruth, Rect
from tools.omr.staged import readout as RO
from tools.omr.staged.record import Q, Subject, meter_at

#: ⚠️ A MEASURING INSTRUMENT, NOT A CONSUMER. This module reads a record's rows to SCORE them against a
#: hand-labeled page; it decides nothing and feeds no stage. ``wiring``'s DETAIL question counts any text
#: containing ``.own`` as a read of the detail key ``own`` -- and ``rg.owner`` does -- so without this marker
#: the scorer would silently close a ``KNOWN_GAPS`` entry no stage reads (the same instrument family as
#: ``readout`` / ``trace`` / ``capture``, and the reason they declare it). Must stay a bare module-level
#: literal ``True``.
DERIVED_CHECK = True

REPO = Path(__file__).resolve().parents[3]
INVENTORY_PATH = REPO / "data" / "hand-truth" / "INVENTORY.json"

#: The matcher's own threshold (``readout.match_glyphs`` default), stated so a report names it.
MIN_IOU = 0.3
#: "A tile centred near zero": the frame control fails when the MEDIAN offset of matched DRAWN boxes
#: is more than this many staff spaces, or when any cell the two sides both cut differs by more than
#: ``FRAME_CELL_TOL_PX``. A shift of a quarter of a space already moves a near-boundary head a step.
FRAME_MEDIAN_TOL_SPACES = 0.15
FRAME_CELL_TOL_PX = 2.0
#: A head is "inside its staff" for the DERIVED reference when its centre is within this many
#: spaces of the outer lines (the first ledger line stands 1.0 beyond; farther heads need Sean's
#: owner -- CLAUDE.md §10: ledger lines name the owner, and nearness never does).
DERIVE_REACH_SPACES = 1.1
#: ASSUMED -- see the module docstring.
TRUTH_POSITION_UP_POSITIVE = True

KEPT_STATUSES_DROPPED = (RO.REFUSED, RO.GIVEN_AWAY)
#: Families whose truth is not a box. Staff lines are CONFIRMED per staff (``StaffCheck.lines_right``,
#: plan §5 Q1), never drawn, so the detector's ``staff`` boxes have nothing to be scored against.
NOT_BOXED_IN_TRUTH = {"staff_line": "staff lines are confirmed per staff (lines_right), not boxed in the truth"}


# ═════════════════════════════════════════════════════════════════════════════
# Geometry helpers
# ═════════════════════════════════════════════════════════════════════════════


def _cx(r: Sequence[float]) -> float:
    return (r[0] + r[2]) / 2.0


def _cy(r: Sequence[float]) -> float:
    return (r[1] + r[3]) / 2.0


def canonical_cls(cls: str) -> str:
    return class_aliases.canonical(cls) if cls else cls


def family(cls: str) -> str:
    """The family a class is scored under: the hand-truth completeness vocabulary
    (``score_reading.detector_family`` plus the whole-ink extras), after the repo's own alias fold."""
    return family_of(canonical_cls(cls))


def pos_truth_to_top(p: int) -> int:
    """Truth steps-from-middle -> the record's half-steps down from the top line (middle = 4)."""
    return 4 - p if TRUTH_POSITION_UP_POSITIVE else 4 + p


@dataclass
class StaffBand:
    """One measure cell's view of one staff: where its five lines are on the PAGE, locally."""
    system: int
    staff: int
    cell_id: str
    rect: Rect
    lines: List[float]  # five page-pixel ys, ascending

    @property
    def space(self) -> float:
        return (self.lines[-1] - self.lines[0]) / 4.0


def staff_bands(page: PageTruth) -> List[StaffBand]:
    out: List[StaffBand] = []
    for c in page.cells:
        if c.kind != "measure" or c.system is None or c.staff is None:
            continue
        if not c.staff_line_ys or len(c.staff_line_ys) < 5:
            continue
        ys = sorted(c.to_page((0, y, 1, y + 1))[1] for y in c.staff_line_ys[:5])
        out.append(StaffBand(c.system, c.staff, c.id, c.rect, ys))
    return out


def locate(bands: Sequence[StaffBand], cx: float, cy: float,
           reach: float = DERIVE_REACH_SPACES) -> List[Tuple[StaffBand, float]]:
    """Every staff whose cell holds ``cx`` and whose outer lines are within ``reach`` spaces of
    ``cy``, as ``(band, distance in spaces beyond the outer lines; 0 inside)``. One band per staff
    (the cell holding ``cx`` that is nearest)."""
    best: Dict[Tuple[int, int], Tuple[StaffBand, float]] = {}
    for b in bands:
        if not (b.rect[0] <= cx <= b.rect[2]):
            continue
        d = max(b.lines[0] - cy, cy - b.lines[-1], 0.0) / b.space
        if d > reach:
            continue
        k = (b.system, b.staff)
        if k not in best or d < best[k][1]:
            best[k] = (b, d)
    return list(best.values())


def position_on(band: StaffBand, cy: float) -> float:
    """Half-steps DOWN from the top line at this band's lines -- the record's unit."""
    return (cy - band.lines[0]) / (band.space / 2.0)


# ═════════════════════════════════════════════════════════════════════════════
# The truth side
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class TruthItem:
    idx: int
    id: str
    cls: str
    family: str
    rect: Rect
    origin: str
    cell_id: Optional[str]
    text: Optional[str] = None
    #: Sean's, or None. NEVER filled from geometry.
    owner: Optional[Tuple[int, int]] = None
    position: Optional[int] = None  # steps from the middle line, the store's unit
    #: The DERIVED reference (``derive=True`` only) -- labelled as such wherever it is used.
    derived_owner: Optional[Tuple[int, int]] = None
    derived_position_top: Optional[int] = None  # half-steps down from the top line
    derived_how: Optional[str] = None  # "staff" (inside its staff) | "ledger" (Sean's ledger-line boxes)
    #: The staff whose cell holds the box, by geometry. For headers only (clef/key/meter);
    #: never an owner claim.
    staff_by_cell: Optional[Tuple[int, int]] = None


@dataclass
class Scope:
    """Which cells a family was inspected in, and the rectangles that test a centre against them."""
    cells: List[Cell]

    def holds(self, r: Sequence[float]) -> bool:
        x, y = _cx(r), _cy(r)
        return any(c.rect[0] <= x < c.rect[2] and c.rect[1] <= y < c.rect[3] for c in self.cells)


def cells_inspected_for(page: PageTruth, fam: str) -> List[Cell]:
    """The cells a family was inspected in. ``families_covered`` returns None for the whole-ink pass."""
    out = []
    for c in page.cells:
        cov = families_covered(c.inspected)
        if cov is None or fam in cov:
            out.append(c)
    return out


def fully_labeled(page: PageTruth) -> List[Cell]:
    return [c for c in page.cells if families_covered(c.inspected) is None]


def truth_items(page: PageTruth, *, derive: bool = False) -> List[TruthItem]:
    bands = staff_bands(page)
    ledgers = [b.rect for b in page.boxes if family(b.cls) == "ledger_line"]
    items: List[TruthItem] = []
    for i, b in enumerate(page.boxes):
        it = TruthItem(idx=i, id=b.id, cls=canonical_cls(b.cls), family=family(b.cls), rect=b.rect,
                       origin=b.origin, cell_id=b.cell_id, text=b.text,
                       owner=tuple(b.owner_staff) if b.owner_staff else None,
                       position=b.staff_position)
        loc = locate(bands, _cx(b.rect), _cy(b.rect), reach=3.0)
        if loc:
            band, _ = min(loc, key=lambda t: t[1])
            it.staff_by_cell = (band.system, band.staff)
        if derive and it.family == "notehead":
            near = locate(bands, _cx(b.rect), _cy(b.rect))
            if len(near) == 1:  # exactly one staff within reach: no contest to decide
                band, _ = near[0]
                it.derived_owner, it.derived_how = (band.system, band.staff), "staff"
                it.derived_position_top = int(round(position_on(band, _cy(b.rect))))
            elif not near:
                far = _ledger_owner(bands, ledgers, b.rect)
                if far is not None:
                    band = far
                    it.derived_owner, it.derived_how = (band.system, band.staff), "ledger"
                    it.derived_position_top = int(round(position_on(band, _cy(b.rect))))
        items.append(it)
    return items


def _ledger_owner(bands: Sequence[StaffBand], ledgers: Sequence[Rect], head: Rect,
                  reach: float = 8.0) -> Optional[StaffBand]:
    """The staff a FAR head's own ledger-line boxes lead to (Sean 2026-09-28: the ledger lines name the
    owner; nearness never does). A staff qualifies when at least one of Sean's ledger boxes stands
    under the head between it and that staff, the first of them within 1.4 spaces of the staff's
    outer line (a rung chain that starts at the staff). Exactly one staff must qualify -- two, or none,
    and the head stays unlabeled: a clean empty reading is OUR failure, not an owner (rule 8)."""
    cx, cy = _cx(head), _cy(head)
    ok = []
    for band, _d in locate(bands, cx, cy, reach=reach):
        sp = band.space
        edge = band.lines[0] if cy < band.lines[0] else band.lines[-1]
        lo, hi = min(cy, edge) - 0.3 * sp, max(cy, edge) + 0.3 * sp
        rungs = [l for l in ledgers if l[2] >= head[0] - 0.5 * sp and l[0] <= head[2] + 0.5 * sp
                 and lo <= _cy(l) <= hi]
        if rungs and min(abs(_cy(l) - edge) for l in rungs) <= 1.4 * sp:
            ok.append(band)
    return ok[0] if len(ok) == 1 else None


def truth_owner(it: TruthItem) -> Tuple[Optional[Tuple[int, int]], str]:
    if it.owner is not None:
        return it.owner, "sean"
    if it.derived_owner is not None:
        return it.derived_owner, f"derived:{it.derived_how}"
    return None, "none"


def truth_position_top(it: TruthItem) -> Tuple[Optional[int], str]:
    if it.position is not None:
        return pos_truth_to_top(int(it.position)), "sean"
    if it.derived_position_top is not None:
        return it.derived_position_top, f"derived:{it.derived_how}"
    return None, "none"


# ═════════════════════════════════════════════════════════════════════════════
# The record side
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class ReadGlyph:
    idx: int
    key: str
    cls: str
    family: str
    rect: Rect
    page: int
    system: int
    staff: int
    cell: int
    status: str
    #: The family ADJUDICATE leaves the box in. Only an arc differs from ``family``: ``Q.ARC_KIND`` decides
    #: tie or slur, and the detector's class is only its first guess.
    adj_family: str = ""
    #: notehead only
    owner: Optional[Tuple[int, int]] = None
    #: decided | narrowed | abstained | uncontested. ``uncontested`` = ADJUDICATE filed NO owner verdict on
    #: the head: ``glyph_owner``'s domain is the contested population (``adjudicate.is_relocated_copy``),
    #: so the head stays on the staff its cell was cut from -- the export's own reading of the absence.
    owner_outcome: str = "uncontested"
    owner_reason: Optional[str] = None
    position_top: Optional[int] = None
    position_state: str = "none"  # observed | far_decided | abstained | none

    @property
    def filed_staff(self) -> Tuple[int, int]:
        return (self.system, self.staff)


def _staff_of_key(key: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(key, str):
        return None
    try:
        s = Subject.from_key(key)
    except (ValueError, KeyError):
        return None
    return (s.system, s.staff) if s.staff is not None else None


def read_glyphs(run: RO.Run, page_index: int) -> List[ReadGlyph]:
    """The record's detector boxes on one page, with ADJUDICATE's standing on each.

    Everything is read through ``readout``'s own ``Run``/``adjudicate_status`` -- nothing is
    re-derived from the file -- and what the record does not say stays unsaid (rule 8).
    """
    where = RO.Where(page=page_index)
    out: List[ReadGlyph] = []
    for g in run.glyphs.values():
        if not where.admits(g.key) or g.box_page is None:
            continue
        status, _ = RO.adjudicate_status(run, g)
        rg = ReadGlyph(idx=len(out), key=g.key, cls=canonical_cls(g.cls or ""),
                       family=family(g.cls or ""), rect=tuple(g.box_page), page=g.page,
                       system=g.system, staff=g.staff, cell=g.cell, status=status)
        rg.adj_family = rg.family
        if rg.family in ("tie", "slur"):
            kind = run.standing(g.key, Q.ARC_KIND, "ADJUDICATE")
            if kind is not None and kind["outcome"] == "decided" and kind.get("value") in ("tie", "slur"):
                rg.adj_family = kind["value"]
        if rg.family == "notehead":
            owner_v = run.standing(g.key, Q.GLYPH_OWNER, "ADJUDICATE")
            if owner_v is None:
                rg.owner = rg.filed_staff
            else:
                rg.owner_outcome = owner_v["outcome"]
                rg.owner_reason = owner_v.get("reason")
                if owner_v["outcome"] == "decided":
                    rg.owner = _staff_of_key(owner_v.get("value"))
            far = run.standing(g.key, Q.NOTEHEAD_POSITION, "ADJUDICATE")
            if far is not None and far["outcome"] == "decided" and far.get("value") is not None:
                rg.position_top, rg.position_state = int(far["value"]), "far_decided"
            elif far is not None:
                rg.position_state = "abstained"  # a far head the ledgers could not place: no geometry substitute
            else:
                obs = run.obs_at(g.key, Q.NOTEHEAD_STAFF_POSITION)
                if obs:
                    rg.position_top, rg.position_state = int(round(float(obs[0]["value"]))), "observed"
                else:
                    rg.position_state = "abstained"
        out.append(rg)
    return out


# ═════════════════════════════════════════════════════════════════════════════
# Matching (readout.match_glyphs, flattened per family)
# ═════════════════════════════════════════════════════════════════════════════


def _flat_run(rects: Sequence[Tuple[int, Sequence[float], str]]) -> RO.Run:
    glyphs = {}
    for i, rect, cls in rects:
        k = f"glyph/0/0/0/0/{i}"
        glyphs[k] = RO.Glyph(key=k, page=0, system=0, staff=0, cell=0, index=i, cls=cls, family=None,
                             score=None, box_canon=None, box_page=tuple(float(v) for v in rect))
    return RO.Run(path="<flat>", result={}, observations=[], abstentions=[], verdicts=[], glyphs=glyphs)


def match_boxes(truth: Sequence[Tuple[int, Sequence[float], str]],
                read: Sequence[Tuple[int, Sequence[float], str]],
                *, min_iou: float = MIN_IOU) -> Tuple[Dict[int, Tuple[int, float]], List[int], List[int]]:
    """Pair truth boxes with record boxes by overlap, with ``readout.match_glyphs``.

    Each side is ``(index, page-pixel rect, class)``. Returns ``({truth idx: (read idx, iou)},
    unmatched truth idx, unmatched read idx)``.
    """
    a, b = _flat_run(truth), _flat_run(read)
    pairs, only_a, only_b = RO.match_glyphs(a, b, min_iou=min_iou)
    idx = lambda k: int(k.rsplit("/", 1)[1])  # noqa: E731
    return ({idx(ka): (idx(kb), iou) for ka, kb, iou, _ in pairs},
            sorted(idx(k) for k in only_a), sorted(idx(k) for k in only_b))


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    return RO._iou(a, b)


@dataclass
class FamilyMatch:
    family: str
    truth: List[TruthItem]
    read: List[ReadGlyph]
    pairs: Dict[int, Tuple[int, float]]  # truth idx -> (read idx, iou)
    missed: List[int]
    extra: List[int]


def match_family(fam: str, truth: Sequence[TruthItem], read: Sequence[ReadGlyph]) -> FamilyMatch:
    t = [(it.idx, it.rect, it.cls) for it in truth]
    r = [(g.idx, g.rect, g.cls) for g in read]
    pairs, only_t, only_r = match_boxes(t, r)
    return FamilyMatch(fam, list(truth), list(read), pairs, only_t, only_r)


# ═════════════════════════════════════════════════════════════════════════════
# The scoring
# ═════════════════════════════════════════════════════════════════════════════


def _rate(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def _on_ink(rect: Sequence[float], uncovered: Sequence[Sequence[float]], frac: float = 0.3) -> bool:
    """Does at least ``frac`` of the box lie over ink that NO truth box covers?"""
    area = max(1e-9, (rect[2] - rect[0]) * (rect[3] - rect[1]))
    for u in uncovered:
        ix = max(0.0, min(rect[2], u[2]) - max(rect[0], u[0]))
        iy = max(0.0, min(rect[3], u[3]) - max(rect[1], u[1]))
        if ix * iy / area >= frac:
            return True
    return False


def _explain_unmatched(fm: FamilyMatch, all_truth: Sequence[TruthItem], all_read: Sequence[ReadGlyph],
                       uncovered: Sequence[Sequence[float]] = (), fam_attr: str = "family"
                       ) -> Tuple[Dict[int, str], Dict[int, str]]:
    """Why each unmatched box is unmatched. Truth: ``other_family`` (a record box of another family
    sits on it) / ``near_miss`` (a same-family box overlaps below the threshold) / ``missed`` (nothing
    does). Record: ``duplicate`` (it overlaps a truth box of its own family that another box took) /
    ``other_family`` (it sits on a truth box of another family) / ``spurious`` (nothing of the truth
    is there). With the ink-coverage control run (``uncovered``), a spurious box over ink no truth box
    covers is ``spurious_on_unboxed_ink``: either a detector false positive on a mark the truth never
    boxed, or a mark Sean did not box -- a truth gap the detector may be RIGHT about."""
    why_t: Dict[int, str] = {}
    for ti in fm.missed:
        it = next(x for x in fm.truth if x.idx == ti)
        why = "missed"
        for g in all_read:
            ov = _iou(it.rect, g.rect)
            if ov >= MIN_IOU and getattr(g, fam_attr) != fm.family:
                why = "other_family"
                break
            if 0.05 <= ov < MIN_IOU and getattr(g, fam_attr) == fm.family:
                why = "near_miss"
        why_t[ti] = why
    why_r: Dict[int, str] = {}
    for ri in fm.extra:
        g = next(x for x in fm.read if x.idx == ri)
        why = "spurious"
        for it in all_truth:
            if _iou(it.rect, g.rect) >= MIN_IOU:
                why = "duplicate" if it.family == fm.family else "other_family"
                if why == "duplicate":
                    break
        if why == "spurious" and _on_ink(g.rect, uncovered):
            why = "spurious_on_unboxed_ink"
        why_r[ri] = why
    return why_t, why_r


def stage_view(fm: FamilyMatch, all_truth: Sequence[TruthItem], all_read: Sequence[ReadGlyph],
               uncovered: Sequence[Sequence[float]] = (), fam_attr: str = "family") -> Dict[str, Any]:
    why_t, why_r = _explain_unmatched(fm, all_truth, all_read, uncovered, fam_attr)
    n_t, n_r, n_m = len(fm.truth), len(fm.read), len(fm.pairs)
    by_origin: Dict[str, Dict[str, int]] = {}
    for it in fm.truth:
        d = by_origin.setdefault(it.origin, {"truth": 0, "matched": 0})
        d["truth"] += 1
        d["matched"] += it.idx in fm.pairs
    class_agree = sum(1 for ti, (ri, _) in fm.pairs.items()
                      if next(x for x in fm.truth if x.idx == ti).cls
                      == next(g for g in fm.read if g.idx == ri).cls)
    dup = sum(1 for v in why_r.values() if v == "duplicate")
    return {
        "truth": n_t, "read": n_r, "matched": n_m,
        "recall": _rate(n_m, n_t), "precision": _rate(n_m, n_r),
        "precision_without_duplicates": _rate(n_m, n_r - dup),
        "recall_by_origin": {o: {**d, "recall": _rate(d["matched"], d["truth"])}
                             for o, d in sorted(by_origin.items())},
        "class_agree_on_matched": _rate(class_agree, n_m),
        "missed_because": dict(collections.Counter(why_t.values())),
        "unmatched_read_because": dict(collections.Counter(why_r.values())),
    }


def score_families(page: PageTruth, items: Sequence[TruthItem], glyphs: Sequence[ReadGlyph],
                   uncovered: Sequence[Sequence[float]] = ()
                   ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, FamilyMatch]]]:
    """Per family, over the cells inspected for it, at the GATHER and ADJUDICATE views."""
    fams = sorted({it.family for it in items} | {g.family for g in glyphs} | {g.adj_family for g in glyphs})
    kept = [g for g in glyphs if g.status not in KEPT_STATUSES_DROPPED]  # what ADJUDICATE hands on
    out: Dict[str, Any] = {}
    matches: Dict[str, Dict[str, FamilyMatch]] = {}
    for fam in fams:
        if fam in NOT_BOXED_IN_TRUTH:
            out[fam] = {"status": "NOT SCORED: " + NOT_BOXED_IN_TRUTH[fam],
                        "truth_boxes": sum(1 for it in items if it.family == fam),
                        "read_boxes": sum(1 for g in glyphs if g.family == fam)}
            continue
        cells = cells_inspected_for(page, fam)
        if not cells:
            out[fam] = {"status": "REFUSED: no cell was inspected for this family -- not scored as zero",
                        "truth_boxes": sum(1 for it in items if it.family == fam),
                        "read_boxes": sum(1 for g in glyphs if g.family == fam)}
            continue
        scope = Scope(cells)
        t_all = [it for it in items if it.family == fam]
        t = [it for it in t_all if scope.holds(it.rect)]
        r_g = [g for g in glyphs if g.family == fam and scope.holds(g.rect)]
        r_a = [g for g in glyphs if g.adj_family == fam and scope.holds(g.rect)
               and g.status not in KEPT_STATUSES_DROPPED]
        fm_g, fm_a = match_family(fam, t, r_g), match_family(fam, t, r_a)
        matches[fam] = {"gather": fm_g, "adjudicate": fm_a}
        out[fam] = {
            "status": "scored", "cells_inspected": len(cells),
            "unscored_truth_boxes": len(t_all) - len(t),
            "unscored_read_boxes": sum(1 for g in glyphs if g.family == fam) - len(r_g),
            "gather": stage_view(fm_g, items, glyphs, uncovered),
            "adjudicate": stage_view(fm_a, items, kept, uncovered, "adj_family"),
            "lost_by_adjudicate": sum(1 for ti in fm_g.pairs if ti not in fm_a.pairs),
        }
    return out, matches


def never_produced(items: Sequence[TruthItem], glyphs: Sequence[ReadGlyph]) -> Dict[str, Any]:
    t = collections.Counter(it.cls for it in items)
    r = collections.Counter(g.cls for g in glyphs)
    return {"truth_classes_the_detector_never_produced": {k: v for k, v in sorted(t.items()) if k not in r},
            "detector_classes_the_truth_never_has": {k: v for k, v in sorted(r.items()) if k not in t}}


# ── notehead: owner and staff position ───────────────────────────────────────


def score_noteheads(page: PageTruth, items: Sequence[TruthItem], glyphs: Sequence[ReadGlyph],
                    matches: Dict[str, Dict[str, FamilyMatch]], *, trained_cells: Sequence[str] = ()
                    ) -> Dict[str, Any]:
    if "notehead" not in matches:
        return {"status": "REFUSED: notehead family not scored"}
    fm = matches["notehead"]["adjudicate"]
    fg = matches["notehead"]["gather"]
    glyph_by = {g.idx: g for g in fm.read}
    cell_rects = {c.id: c.rect for c in page.cells}
    trained = [cell_rects[c] for c in trained_cells if c in cell_rects]

    def split_of(it: TruthItem) -> str:
        return "trained" if any(r[0] <= _cx(it.rect) < r[2] and r[1] <= _cy(it.rect) < r[3]
                                for r in trained) else "not_trained"

    rows: List[Dict[str, Any]] = []
    for it in fm.truth:
        row: Dict[str, Any] = {"truth_id": it.id, "cell": it.cell_id, "split": split_of(it)}
        if it.idx not in fm.pairs:
            row["match"] = "missed_at_adjudicate" if it.idx in fg.pairs else "missed"
            rows.append(row)
            continue
        g = glyph_by[fm.pairs[it.idx][0]]
        row["match"] = "matched"
        row["read_key"] = g.key
        o, o_src = truth_owner(it)
        row["owner_truth"], row["owner_source"] = o, o_src
        row["owner_read"], row["owner_outcome"] = g.owner, g.owner_outcome
        row["owner_reason"] = g.owner_reason
        if o is None:
            row["owner"] = "no_truth"
        elif g.owner_outcome not in ("decided", "uncontested") or g.owner is None:
            row["owner"] = "abstained"
        else:
            row["owner"] = "right" if _same_owner(g.owner, o) else "wrong"
        p, p_src = truth_position_top(it)
        row["position_truth_top"], row["position_source"] = p, p_src
        row["position_read_top"], row["position_state"] = g.position_top, g.position_state
        if p is None:
            row["position"] = "no_truth"
        elif g.position_top is None:
            row["position"] = "abstained"
        else:
            row["position"] = "right" if _same_position(g.position_top, p) else "wrong"
            row["position_delta"] = g.position_top - p
        rows.append(row)

    def tally(sel: Iterable[Dict[str, Any]], key: str) -> Dict[str, Any]:
        sel = list(sel)
        c = collections.Counter(r[key] for r in sel if key in r)
        judged = c["right"] + c["wrong"]
        return {"right": c["right"], "wrong": c["wrong"], "abstained": c["abstained"],
                "no_truth": c["no_truth"],
                "accuracy_of_judged": _rate(c["right"], judged),
                "accuracy_of_matched": _rate(c["right"], c["right"] + c["wrong"] + c["abstained"])}

    def block(sel: List[Dict[str, Any]]) -> Dict[str, Any]:
        matched = [r for r in sel if r["match"] == "matched"]
        srcs = collections.Counter(r.get("owner_source") for r in matched)
        psrcs = collections.Counter(r.get("position_source") for r in matched)
        deltas = collections.Counter(r["position_delta"] for r in matched if "position_delta" in r)
        basis = collections.Counter(r.get("owner_outcome") for r in matched)
        return {"truth_noteheads": len(sel), "matched": len(matched),
                "missed": sum(1 for r in sel if r["match"] != "matched"),
                "owner": tally(matched, "owner"), "owner_truth_source": dict(srcs),
                "owner_read_basis": dict(basis),
                "position": tally(matched, "position"), "position_truth_source": dict(psrcs),
                "position_delta_read_minus_truth": {str(k): v for k, v in sorted(deltas.items())}}

    out = {"status": "scored", "stage": "adjudicate",
           "unit_of_position": "half-steps down from the top line (middle line = 4)",
           "all": block(rows),
           "trained_cells": block([r for r in rows if r["split"] == "trained"]),
           "not_trained_cells": block([r for r in rows if r["split"] == "not_trained"]),
           "trained_cells_named": list(trained_cells)}
    out["_rows"] = rows
    return out


def _same_owner(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return tuple(a) == tuple(b)


def _same_position(a: int, b: int) -> bool:
    return int(a) == int(b)


# ── per staff: clef, key, meter ──────────────────────────────────────────────

_CLEF_NAMES = {"clefg": "treble", "cleff": "bass", "clefcalto": "alto", "clefctenor": "tenor",
               "clefc": "alto"}


def _clef_name(cls: str) -> Optional[str]:
    low = "".join(ch for ch in cls.lower() if ch.isalnum())
    for k in sorted(_CLEF_NAMES, key=len, reverse=True):
        if low.startswith(k):
            return _CLEF_NAMES[k]
    return None


def _header_boxes(page: PageTruth, items: Sequence[TruthItem], system: int, staff: int, *, last: bool = False
                  ) -> Tuple[Optional[Cell], List[TruthItem]]:
    """The staff's FIRST (or LAST) measure cell and the truth boxes in it that belong to this staff."""
    cells = [c for c in page.cells if c.kind == "measure" and (c.system, c.staff) == (system, staff)]
    if not cells:
        return None, []
    cell = (max if last else min)(cells, key=lambda c: c.measure or 0)
    return cell, [it for it in items if it.staff_by_cell == (system, staff)
                  and cell.rect[0] <= _cx(it.rect) < cell.rect[2]
                  and cell.rect[1] <= _cy(it.rect) < cell.rect[3]]


def truth_header(page: PageTruth, items: Sequence[TruthItem], system: int, staff: int) -> Dict[str, Any]:
    """What the hand boxes say the staff's header is: clef name, key (fifths), meter (n, d).

    Each is ``None`` when the first cell was not fully labeled (UNSCORED, not "none printed"), and
    ``{"printed": False}`` for a key / meter with no box in a fully labeled cell.
    """
    first, here = _header_boxes(page, items, system, staff)
    out: Dict[str, Any] = {"system": system, "staff": staff, "cell": first.id if first else None,
                           "cautionary": _truth_cautionary(page, items, system, staff)}
    if first is None or families_covered(first.inspected) is not None:
        out["scored"] = False
        out["why"] = "first measure cell is not fully labeled" if first else "no measure cell"
        return out
    out["scored"] = True
    clefs = sorted((it for it in here if it.family == "clef"), key=lambda it: it.rect[0])
    out["clef"] = _clef_name(clefs[0].cls) if clefs else None
    out["clef_class"] = clefs[0].cls if clefs else None
    keys = [it for it in here if it.family == "key_accidental"]
    flats = sum(1 for it in keys if it.cls.lower().startswith("keyflat"))
    sharps = sum(1 for it in keys if it.cls.lower().startswith("keysharp"))
    out["key_fifths"] = None if (flats and sharps) else (sharps - flats)
    digits = [it for it in here if it.family == "time_signature_digit"]
    out["meter"] = _meter_of(digits, page, system, staff)
    out["meter_boxes"] = sorted(it.cls for it in digits)
    return out


#: The last cell of a staff holds NO bar when it is narrower than this many staff spaces: it is the sliver
#: after the final barline, where a CAUTIONARY meter stands (CLAUDE.md §10: it governs no bar).
CAUTIONARY_CELL_MAX_SPACES = 6.0


def _truth_cautionary(page: PageTruth, items: Sequence[TruthItem], system: int, staff: int
                      ) -> Dict[str, Any]:
    last, here = _header_boxes(page, items, system, staff, last=True)
    if last is None:
        return {"scored": False, "why": "no measure cell"}
    if families_covered(last.inspected) is not None:
        return {"scored": False, "why": "last measure cell is not fully labeled", "cell": last.id}
    sp = next((b.space for b in staff_bands(page) if b.cell_id == last.id), None)
    if sp is None or (last.rect[2] - last.rect[0]) >= CAUTIONARY_CELL_MAX_SPACES * sp:
        return {"scored": False, "why": "last cell holds a bar, not a cautionary sliver", "cell": last.id}
    digits = [it for it in here if it.family == "time_signature_digit"]
    return {"scored": True, "cell": last.id, "meter": _meter_of(digits, page, system, staff)}


def _meter_of(digits: Sequence[TruthItem], page: PageTruth, system: int, staff: int
              ) -> Optional[Dict[str, Any]]:
    if not digits:
        return {"printed": False}
    bands = [b for b in staff_bands(page) if (b.system, b.staff) == (system, staff)]
    if not bands:
        return None
    mid = statistics.median((b.lines[0] + b.lines[-1]) / 2 for b in bands)  # the staff's middle line, page y

    def num(cls: str) -> Optional[str]:
        tail = "".join(ch for ch in cls if ch.isdigit())
        return tail or None

    top = sorted((it for it in digits if _cy(it.rect) < mid), key=lambda it: it.rect[0])
    bot = sorted((it for it in digits if _cy(it.rect) >= mid), key=lambda it: it.rect[0])
    if any(num(it.cls) is None for it in digits):
        return {"printed": True, "raw": sorted(it.cls for it in digits), "numerator": None, "denominator": None}
    n = "".join(num(it.cls) for it in top)
    d = "".join(num(it.cls) for it in bot)
    return {"printed": True, "numerator": int(n) if n else None, "denominator": int(d) if d else None,
            "raw": f"{n}/{d}"}


def read_header(run: RO.Run, page_index: int, system: int, staff: int) -> Dict[str, Any]:
    sk = f"staff/{page_index}/{system}/{staff}"
    out: Dict[str, Any] = {}
    clef = run.standing(sk, Q.CLEF, "ADJUDICATE")
    out["clef"] = ({"outcome": clef["outcome"], "value": clef.get("value")} if clef
                   else {"outcome": "none", "value": None})
    key = run.standing(sk, Q.KEY_SIGNATURE, "ADJUDICATE")
    out["key"] = ({"outcome": key["outcome"], "value": key.get("value")} if key
                  else {"outcome": "none", "value": None})
    m = run.standing(f"system/{page_index}/{system}", Q.METER, "ADJUDICATE")
    seg = meter_at(m.get("value"), 0) if m and m.get("outcome") == "decided" else None
    out["meter"] = ({"outcome": m["outcome"], "numerator": (seg or {}).get("numerator"),
                     "denominator": (seg or {}).get("denominator")} if m
                    else {"outcome": "none", "numerator": None, "denominator": None})
    caut = ((m or {}).get("value") or {}).get("cautionary") if m and m.get("outcome") == "decided" else None
    out["cautionary"] = ({"outcome": "decided", "numerator": caut.get("numerator"),
                          "denominator": caut.get("denominator"), "from_cell": caut.get("from_cell")}
                         if caut else {"outcome": "none", "numerator": None, "denominator": None,
                                       "from_cell": None})
    return out


def _key_fifths(v: Any) -> Optional[int]:
    """A ``Q.KEY_SIGNATURE`` verdict's fifths, whatever shape carries them."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, dict):
        for k in ("fifths", "value", "key"):
            if isinstance(v.get(k), (int, float)) and not isinstance(v.get(k), bool):
                return int(v[k])
    return None


def judge_clef(read: Dict[str, Any], truth_clef: Optional[str]) -> str:
    if truth_clef is None:
        return "no_truth"
    if read["outcome"] != "decided":
        return "abstained"
    return "right" if read["value"] == truth_clef else "wrong"


def judge_key(read: Dict[str, Any], truth_fifths: Optional[int]) -> str:
    if truth_fifths is None:
        return "no_truth"
    if read["outcome"] != "decided":
        return "abstained"
    return "right" if _key_fifths(read["value"]) == truth_fifths else "wrong"


def judge_meter(read: Dict[str, Any], truth_meter: Dict[str, Any]) -> str:
    """No digits boxed in a fully labeled first cell means the meter is CARRIED, not printed there:
    nothing to judge (``no_truth``), never "right"."""
    if not truth_meter.get("printed") or truth_meter.get("numerator") is None \
            or truth_meter.get("denominator") is None:
        return "no_truth"
    if read["outcome"] != "decided":
        return "abstained"
    return ("right" if (read["numerator"], read["denominator"])
            == (truth_meter["numerator"], truth_meter["denominator"]) else "wrong")


def judge_cautionary(read: Dict[str, Any], truth_meter: Dict[str, Any]) -> str:
    """The cautionary meter after a system's last barline. The record keeps ONE per system; the truth has
    one per staff. A staff printing none, in a fully labeled sliver, is ``no_truth`` here (the record
    printing one anyway is a finding of its own, not a ``wrong``)."""
    return judge_meter(read, truth_meter)


def score_headers(page: PageTruth, items: Sequence[TruthItem], run: RO.Run, page_index: int
                  ) -> Dict[str, Any]:
    staves = sorted({(c.system, c.staff) for c in page.cells if c.kind == "measure"})
    rows = []
    tally = {k: collections.Counter() for k in ("clef", "key", "meter", "cautionary")}
    for system, staff in staves:
        t = truth_header(page, items, system, staff)
        r = read_header(run, page_index, system, staff)
        row = {"staff": f"{system}.{staff}", "truth": t, "read": r}
        caut = t.get("cautionary") or {}
        row["cautionary"] = (judge_cautionary(r["cautionary"], caut["meter"] or {}) if caut.get("scored")
                             else "unscored")
        tally["cautionary"][row["cautionary"]] += 1
        if not t.get("scored"):
            for k in ("clef", "key", "meter"):
                tally[k]["unscored"] += 1
            row["clef"] = row["key"] = row["meter"] = "unscored"
            rows.append(row)
            continue
        row["clef"] = judge_clef(r["clef"], t.get("clef"))
        row["key"] = judge_key(r["key"], t.get("key_fifths"))
        row["meter"] = judge_meter(r["meter"], t.get("meter") or {})
        for k in ("clef", "key", "meter"):
            tally[k][row[k]] += 1
        rows.append(row)
    summary = {}
    for k, c in tally.items():
        judged = c["right"] + c["wrong"]
        summary[k] = {**dict(c), "accuracy_of_judged": _rate(c["right"], judged)}
    return {"summary": summary, "staves": rows}


# ═════════════════════════════════════════════════════════════════════════════
# D2: the frame control
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class FrameVerdict:
    ok: bool
    reasons: List[str]
    detail: Dict[str, Any] = field(default_factory=dict)


def record_cell_boxes(run: RO.Run, page_index: int) -> Dict[Tuple[int, int, int], Rect]:
    out: Dict[Tuple[int, int, int], Rect] = {}
    for key, rows in run.by_subject.items():
        if not key.startswith(f"cell/{page_index}/"):
            continue
        for stage, kind, r in rows:
            if kind == "observation" and r["quantity"] == Q.CELL_BOX:
                s = Subject.from_key(key)
                out[(s.system, s.staff, s.cell)] = tuple(float(v) for v in r["value"])
                break
    return out


def frame_control(page: PageTruth, run_dpi: Optional[int], cell_boxes: Dict[Tuple[int, int, int], Rect],
                  matches: Dict[str, Dict[str, FamilyMatch]], items: Sequence[TruthItem],
                  glyphs: Sequence[ReadGlyph]) -> FrameVerdict:
    """Are the record's page pixels and the truth's page pixels the same frame?

    Three independent looks, and it FAILS on any of them (run the control on a shifted record: it must).
    1. DPI: the record's gather dpi is the page's dpi.
    2. CELLS: every cell both sides cut (same ``s<sys>-st<staff>-m<n>`` id) has the same rectangle.
       Same cutter + same render => identical to the pixel; a deskew, a DPI or a staff-numbering
       difference shows here and cannot hide behind the matcher's IoU slack.
    3. BOXES: the offset of the record's box centre from the truth's, over matched pairs, split by how the
       truth box got there. ``drawn`` boxes are Sean's own strokes on the image -- the only offsets that can
       differ from zero by a frame, since a ``prefill-confirmed`` box IS the detector's box.
    """
    reasons: List[str] = []
    detail: Dict[str, Any] = {}
    if run_dpi is not None and run_dpi != page.dpi:
        reasons.append(f"dpi: record {run_dpi} != truth {page.dpi}")
    detail["dpi"] = {"record": run_dpi, "truth": page.dpi}
    diffs: List[float] = []
    compared = 0
    for c in page.cells:
        if c.kind != "measure" or c.system is None:
            continue
        rb = cell_boxes.get((c.system, c.staff, c.measure or 0))
        if rb is None:
            continue
        compared += 1
        diffs.append(max(abs(a - b) for a, b in zip(rb, c.rect)))
    detail["cells"] = {"compared": compared, "of": sum(1 for c in page.cells if c.kind == "measure"),
                       "max_abs_diff_px": round(max(diffs), 2) if diffs else None,
                       "median_abs_diff_px": round(statistics.median(diffs), 2) if diffs else None}
    if not compared:
        reasons.append("cells: no record cell box to compare with any truth cell -- frame UNPROVEN")
    elif max(diffs) > FRAME_CELL_TOL_PX:
        reasons.append(f"cells: rectangles differ by up to {max(diffs):.1f}px (> {FRAME_CELL_TOL_PX})")
    spaces = [b.space for b in staff_bands(page)]
    sp = statistics.median(spaces) if spaces else 1.0
    glyph_by = {g.idx: g for g in glyphs}
    item_by = {it.idx: it for it in items}
    offs: Dict[str, List[Tuple[float, float]]] = collections.defaultdict(list)
    for fam, views in matches.items():
        for ti, (ri, _) in views["gather"].pairs.items():
            it, g = item_by[ti], glyph_by[ri]
            offs[it.origin].append((_cx(g.rect) - _cx(it.rect), _cy(g.rect) - _cy(it.rect)))
    box = {}
    for origin, v in sorted(offs.items()):
        dx = [a for a, _ in v]
        dy = [b for _, b in v]
        box[origin] = {"n": len(v), "median_dx_px": round(statistics.median(dx), 2),
                       "median_dy_px": round(statistics.median(dy), 2),
                       "p10_dx": round(_pct(dx, 10), 2), "p90_dx": round(_pct(dx, 90), 2),
                       "p10_dy": round(_pct(dy, 10), 2), "p90_dy": round(_pct(dy, 90), 2)}
    detail["box_offsets"] = box
    detail["staff_space_px"] = round(sp, 2)
    drawn = box.get("drawn")
    if drawn is None or drawn["n"] < 10:
        reasons.append("boxes: fewer than 10 matched DRAWN boxes -- the offset distribution cannot test the frame")
    else:
        for axis in ("dx", "dy"):
            m = drawn[f"median_{axis}_px"]
            if abs(m) > FRAME_MEDIAN_TOL_SPACES * sp:
                reasons.append(f"boxes: median {axis} of matched drawn boxes is {m}px "
                               f"(> {FRAME_MEDIAN_TOL_SPACES} staff space = {FRAME_MEDIAN_TOL_SPACES * sp:.1f}px)")
    return FrameVerdict(ok=not reasons, reasons=reasons, detail=detail)


def _pct(xs: Sequence[float], q: float) -> float:
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ═════════════════════════════════════════════════════════════════════════════
# The whole score
# ═════════════════════════════════════════════════════════════════════════════


def trained_cells_for(page: PageTruth, weights_name: Optional[str], inventory_path: Path = INVENTORY_PATH
                      ) -> Tuple[List[str], str]:
    """The cells of this page the weights under test trained on, from the generated inventory.

    Only the PRODUCTION scan weights have a known training set here; any other weights' split is
    UNKNOWN and the scorer says so rather than calling every cell "not trained".
    """
    try:
        inv = json.loads(Path(inventory_path).read_text())
    except (OSError, ValueError):
        return [], "split unavailable: no readable INVENTORY.json"
    prod = inv.get("production_scan_weights")
    if not weights_name or prod is None or Path(weights_name).name != Path(prod).name:
        return [], (f"split not applied: weights under test ({weights_name!r}) are not the production "
                    f"scan weights ({prod!r}), so which cells they trained on is not known")
    key = f"{page.edition}:{page.pdf_page_index}"
    cells = inv.get("held_out_cells_trained_by_production", {}).get(key, [])
    return list(cells), f"production scan weights; {len(cells)} cell(s) of this page in their training set"


def record_weights(run: RO.Run) -> Optional[str]:
    routing = run.result.get("weight_routing") or {}
    return routing.get("weights") or (run.settings_args or {}).get("weights")


def score(page: PageTruth, run: RO.Run, *, page_index: Optional[int] = None, derive: bool = False,
          inventory_path: Path = INVENTORY_PATH, trained_cells: Optional[Sequence[str]] = None,
          items: Optional[Sequence[TruthItem]] = None, ink: Any = None,
          stem_cause_inputs: Optional[Dict[str, Any]] = None, cv_override: Any = None) -> Dict[str, Any]:
    """``items`` lets a control hand in a TRANSFORMED truth (an owner shift); the real call leaves it None.
    ``stem_cause_inputs`` / ``cv_override`` feed ``score_stems`` (the vertical runs and ink raster that tie a
    missed stem to a filter; a transformed ``CvRead`` for a control).
    ``ink`` is a ``completeness.InkReport`` for the page (needs the PDF): with it, the scorer also reports
    how much ink inside the SCORED cells has no truth box -- the truth's own completeness control, which
    bounds every precision figure -- and separates a spurious record box over unboxed ink from one over
    paper."""
    pi = page.pdf_page_index if page_index is None else page_index
    items = list(items) if items is not None else truth_items(page, derive=derive)
    glyphs = read_glyphs(run, pi)
    full_scope = Scope(fully_labeled(page))
    uncovered = ([tuple(float(v) for v in u["rect"]) for u in ink.uncovered if full_scope.holds(u["rect"])]
                 if ink is not None else [])
    fam_scores, matches = score_families(page, items, glyphs, uncovered)
    split_note = "explicit"
    if trained_cells is None:
        trained_cells, split_note = trained_cells_for(page, record_weights(run), inventory_path)
    fv = frame_control(page, run.dpi, record_cell_boxes(run, pi), matches, items, glyphs)
    full = fully_labeled(page)
    report: Dict[str, Any] = {
        "page": f"{page.edition}:{page.pdf_page_index}", "truth_state": page.state,
        "record": {"path": run.path, "weights": record_weights(run), "dpi": run.dpi,
                   "commit": run.provenance.get("commit"), "dirty": run.provenance.get("dirty"),
                   "page_index": pi, "glyphs_on_page": len(glyphs)},
        "stage": "GATHER + ADJUDICATE only",
        "scope": {"cells": len(page.cells), "cells_fully_labeled": len(full),
                  "unscored_cells_by_kind": dict(collections.Counter(
                      c.kind for c in page.cells if c not in full)),
                  "truth_boxes": len(items),
                  "truth_boxes_in_fully_labeled_cells": sum(1 for it in items if Scope(full).holds(it.rect)),
                  "read_boxes_in_fully_labeled_cells": sum(1 for g in glyphs if Scope(full).holds(g.rect)),
                  "truth_box_origin": dict(collections.Counter(it.origin for it in items)),
                  "owner_or_position_written_by_sean": sum(1 for it in items
                                                           if it.owner is not None or it.position is not None),
                  "derive": derive},
        "frame_control": {"ok": fv.ok, "reasons": fv.reasons, **fv.detail},
        "truth_completeness": (
            {"ink_control": "NOT RUN (no --pdf): precision figures cannot be separated into detector false "
                            "positives and marks the truth has no box on"} if ink is None else
            {"ink_control": "run", "components": ink.components,
             "uncovered_in_scored_cells": len(uncovered),
             "uncovered_area_px_in_scored_cells": sum(int(u["area"]) for u in ink.uncovered
                                                      if full_scope.holds(u["rect"])),
             "uncovered_listed": [list(u) for u in uncovered[:12]]}),
        "split": split_note,
        "families": fam_scores,
        "classes": never_produced([it for it in items if Scope(full).holds(it.rect)],
                                  [g for g in glyphs if Scope(full).holds(g.rect)]),
        "noteheads": score_noteheads(page, items, glyphs, matches, trained_cells=trained_cells),
        "headers": score_headers(page, items, run, pi),
    }
    from tools.omr.hand_truth import score_stems as SS  # lazy: score_stems imports this module

    stems = SS.score_stems(page, items, glyphs, matches, run, pi, fam_scores,
                           cause_inputs=stem_cause_inputs, cv_override=cv_override)
    report["stems"] = SS.public(stems)
    report["_stems"] = stems
    report["_uncovered"] = uncovered
    report["_matches"] = matches
    report["_page"] = page
    report["_run"] = run
    report["_items"] = items
    report["_glyphs"] = glyphs
    return report


def public(report: Dict[str, Any]) -> Dict[str, Any]:
    """The JSON-safe part of a report (the underscore keys hold objects)."""
    out = {k: v for k, v in report.items() if not k.startswith("_")}
    if "noteheads" in out and isinstance(out["noteheads"], dict):
        out["noteheads"] = {("rows" if k == "_rows" else k): v for k, v in out["noteheads"].items()}
    return out


# ═════════════════════════════════════════════════════════════════════════════
# Misses: the commonest kinds, with one example cell each
# ═════════════════════════════════════════════════════════════════════════════


def miss_kinds(report: Dict[str, Any], top: int = 5) -> List[Dict[str, Any]]:
    """Group the ADJUDICATE-stage misses by (family, truth class, why) and rank them."""
    items = {it.idx: it for it in report["_items"]}
    kinds: Dict[Tuple[str, str, str], List[TruthItem]] = collections.defaultdict(list)
    for fam, views in report["_matches"].items():
        fm = views["adjudicate"]
        fg = views["gather"]
        why_t, _ = _explain_unmatched(fg, report["_items"], report["_glyphs"])
        glyph_by = {g.idx: g for g in fg.read}
        run = report["_run"]
        for ti in fm.missed:
            it = items[ti]
            cause = "lost_by_adjudicate" if ti in fg.pairs else why_t.get(ti, "missed")
            if ti in fg.pairs:  # ADJUDICATE took a box the detector had: say which verdict took it
                g = run.glyphs.get(glyph_by[fg.pairs[ti][0]].key)
                _, why = RO.adjudicate_status(run, g)
                cause = f"lost_by_adjudicate: {why[0][:90]}" if why else cause
            kinds[(fam, it.cls, cause)].append(it)
    ranked = sorted(kinds.items(), key=lambda kv: -len(kv[1]))[:top]
    produced = {g.cls for g in report["_glyphs"]}
    return [{"family": f, "truth_class": c, "cause": w, "count": len(v),
             "detector_produces_this_class": c in produced,
             "example_cell": v[0].cell_id, "example_box": v[0].id, "example_rect": list(v[0].rect),
             "origins": dict(collections.Counter(x.origin for x in v))}
            for (f, c, w), v in ranked]


# ═════════════════════════════════════════════════════════════════════════════
# Text rendering
# ═════════════════════════════════════════════════════════════════════════════


def _fmt(x: Optional[float]) -> str:
    return "  n/a" if x is None else f"{x:5.3f}"


def render(report: Dict[str, Any]) -> str:
    r = report
    L: List[str] = []
    s = r["scope"]
    L.append(f"HAND-TRUTH SCORE  {r['page']} (state {r['truth_state']})  --  {r['stage']}")
    L.append(f"record {r['record']['path']}")
    L.append(f"  weights {r['record']['weights']}  dpi {r['record']['dpi']}  commit "
             f"{str(r['record']['commit'])[:10]}  dirty {r['record']['dirty']}")
    L.append("")
    L.append(f"SCOPE  {s['cells_fully_labeled']} of {s['cells']} cells fully labeled "
             f"(unscored: {s['unscored_cells_by_kind']}); truth boxes {s['truth_boxes']}, "
             f"{s['truth_boxes_in_fully_labeled_cells']} in scored cells; record boxes in scored cells "
             f"{s['read_boxes_in_fully_labeled_cells']} of {r['record']['glyphs_on_page']} on the page")
    L.append(f"  truth boxes by origin {s['truth_box_origin']}  --  a prefill-confirmed box IS the production "
             "detector's box")
    L.append(f"  owner_staff / staff_position written by Sean: {s['owner_or_position_written_by_sean']} of "
             f"{s['truth_boxes']} boxes; derived reference {'ON' if s['derive'] else 'off'}")
    L.append(f"  trained/not-trained split: {r['split']}")
    tc = r["truth_completeness"]
    if tc["ink_control"] == "run":
        L.append(f"  TRUTH COMPLETENESS (the repo's ink control over the scored cells): "
                 f"{tc['uncovered_in_scored_cells']} ink component(s) of {tc['components']} on the page are under "
                 f"half covered by truth boxes ({tc['uncovered_area_px_in_scored_cells']} px). On a thick-lined scan "
                 "that count includes staff-line slivers and unboxed barlines as well as missed marks, so it WARNS that "
                 "precision is a lower bound; it does not count missed marks")
    else:
        L.append(f"  TRUTH COMPLETENESS: {tc['ink_control']}")
    fc = r["frame_control"]
    L.append("")
    L.append(f"FRAME CONTROL  {'OK' if fc['ok'] else 'FAILED'}  dpi {fc['dpi']}  cells {fc['cells']}  "
             f"staff space {fc.get('staff_space_px')}px")
    for o, d in fc.get("box_offsets", {}).items():
        L.append(f"    {o:<18} n {d['n']:>4}  median dx {d['median_dx_px']:>6}  dy {d['median_dy_px']:>6}  "
                 f"(p10..p90 dx {d['p10_dx']}..{d['p90_dx']}, dy {d['p10_dy']}..{d['p90_dy']})")
    for why in fc["reasons"]:
        L.append(f"    !! {why}")
    L.append("")
    L.append("FAMILIES   recall / precision at GATHER (every detector box) and at ADJUDICATE (boxes it kept)")
    L.append(f"{'family':<24}{'truth':>6}{'read':>6} | {'G rec':>6}{'G prec':>7} | {'A rec':>6}{'A prec':>7}"
             f" | {'drawn m/n':>9}{'conf rec':>9}  lost@A")
    for fam, d in sorted(r["families"].items(), key=lambda kv: -(kv[1].get("gather") or {}).get("truth", 0)):
        if d["status"] != "scored":
            L.append(f"{fam:<24}{d['truth_boxes']:>6}{d['read_boxes']:>6} | {d['status']}")
            continue
        g, a = d["gather"], d["adjudicate"]
        org = g["recall_by_origin"]
        dr = org.get("drawn")
        drawn = f"{dr['matched']}/{dr['truth']}" if dr else "-"
        L.append(f"{fam:<24}{g['truth']:>6}{g['read']:>6} | {_fmt(g['recall']):>6}{_fmt(g['precision']):>7} | "
                 f"{_fmt(a['recall']):>6}{_fmt(a['precision']):>7} | {drawn:>9}"
                 f"{_fmt((org.get('prefill-confirmed') or {}).get('recall')):>9}  {d['lost_by_adjudicate']}")
        cvs = ((r.get("stems") or {}).get("cv_stem") or {}) if fam == "stem" else {}
        if cvs.get("status") == "scored":  # the second source of the stem family, beside the detector class
            L.append(f"{'  stem (CV Q.STEM)':<24}{cvs['truth']:>6}{cvs['read']:>6} | {_fmt(cvs['recall']):>6}"
                     f"{_fmt(cvs['precision']):>7} | {'-':>6}{'-':>7} | {'-':>9}{'-':>9}  (Q.STEM is not adjudicated)")
    c = r["classes"]
    L.append("")
    L.append(f"classes the truth has and the detector never produced: {c['truth_classes_the_detector_never_produced']}")
    L.append(f"classes the detector produced and the truth never has: {c['detector_classes_the_truth_never_has']}")
    n = r["noteheads"]
    L.append("")
    if n.get("status") != "scored":
        L.append(f"NOTEHEADS  {n.get('status')}")
    else:
        L.append(f"NOTEHEADS (ADJUDICATE)  position unit: {n['unit_of_position']}")
        for name in ("all", "trained_cells", "not_trained_cells"):
            b = n[name]
            L.append(f"  {name:<18} truth {b['truth_noteheads']:>4}  matched {b['matched']:>4}  missed {b['missed']:>4}")
            if not b["matched"]:
                continue
            for k in ("owner", "position"):
                t = b[k]
                L.append(f"      {k:<9} right {t['right']:>4}  wrong {t['wrong']:>4}  abstained {t['abstained']:>4}  "
                         f"no_truth {t['no_truth']:>4}  accuracy of judged {_fmt(t['accuracy_of_judged'])}"
                         f"  truth source {b[k + '_truth_source']}")
            L.append(f"      owner read from {b['owner_read_basis']}  (uncontested = no glyph_owner verdict: "
                     "the head stays on the staff it was cut from)")
            L.append(f"      position delta (read - truth) {b['position_delta_read_minus_truth']}")
    if r.get("stems"):
        from tools.omr.hand_truth import score_stems as SS

        L.append("")
        L.append(SS.render(r["stems"]).rstrip())
    h = r["headers"]
    L.append("")
    L.append("PER STAFF (system header)  clef / key / meter against the first cell, cautionary meter against the last")
    for k, d in h["summary"].items():
        L.append(f"  {k:<6} {dict((a, b) for a, b in d.items() if a != 'accuracy_of_judged')}  "
                 f"accuracy of judged {_fmt(d['accuracy_of_judged'])}")
    for row in h["staves"]:
        t, rd = row["truth"], row["read"]
        ct = t.get("cautionary") or {}
        cline = ("" if not ct.get("scored") else
                 f"   cautionary truth {(ct['meter'] or {}).get('raw')} read "
                 f"{rd['cautionary']['numerator']}/{rd['cautionary']['denominator']} {row['cautionary']}")
        if not t.get("scored"):
            L.append(f"  staff {row['staff']:<5} UNSCORED ({t.get('why')}){cline}")
            continue
        L.append(f"  staff {row['staff']:<5} clef truth {str(t.get('clef')):<7} read {str(rd['clef']['value']):<7}"
                 f"[{rd['clef']['outcome']}] {row['clef']:<9} key truth {str(t.get('key_fifths')):>4} read "
                 f"{str(_key_fifths(rd['key']['value'])):>4}[{rd['key']['outcome']}] {row['key']:<9} meter truth "
                 f"{(t.get('meter') or {}).get('raw')} read {rd['meter']['numerator']}/{rd['meter']['denominator']}"
                 f"[{rd['meter']['outcome']}] {row['meter']}{cline}")
    return "\n".join(L) + "\n"


# ═════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--page", required=True, type=Path, help="the page-truth store file (read, never written)")
    ap.add_argument("--record", type=Path, help="a staged record (read through record_io.load_record)")
    ap.add_argument("--page-index", type=int, default=None)
    ap.add_argument("--derive", action="store_true",
                    help="fill a DERIVED owner/position reference for in-staff heads Sean has not labeled")
    ap.add_argument("--controls", action="store_true", help="run the D2 controls on the real page and exit")
    ap.add_argument("--pdf", type=Path, help="the score PDF, only to cut print crops of the commonest misses")
    ap.add_argument("--crops-dir", type=Path)
    ap.add_argument("--crop-cells", default="", help="comma-separated cell ids to cut whole, truth + record drawn")
    ap.add_argument("--crop-ink", default="", help="'x,y;x,y' page points to cut ink-control diagnostic windows at")
    ap.add_argument("--stem-runs", type=Path,
                    help="a record of the same page gathered with OMR_VERTICAL_RUNS: names the filter that refused each "
                         "missed stem (refused if its Q.STEM rows differ from --record's)")
    ap.add_argument("--stem-ink", action="store_true",
                    help="with --pdf: read the raster at each missed stem's column (longest unbroken ink run)")
    ap.add_argument("--out", type=Path, help="write the report as JSON")
    ap.add_argument("--force", action="store_true", help="print the numbers even if the frame control failed")
    a = ap.parse_args(list(argv) if argv is not None else None)
    page = store.load(a.page)
    if a.controls:
        from tools.omr.hand_truth import score_controls

        return score_controls.main_controls(page, a.record, derive=a.derive)
    if a.record is None:
        ap.error("--record is required unless --controls")
    run = RO.load_run(str(a.record))
    ink = None
    if a.pdf:
        from tools.omr.hand_truth.session import _ink_report

        ink = _ink_report(page, str(a.pdf))
    cause: Dict[str, Any] = {}
    if a.stem_runs:
        from tools.omr.hand_truth import score_stems as SS
        from tools.omr.staged import record_io

        other = record_io.load_record(str(a.stem_runs))
        pi = page.pdf_page_index if a.page_index is None else a.page_index
        same, n_a, n_b = SS.stem_sets_equal(run, other, pi)
        if not same:
            ap.error(f"--stem-runs holds {n_b} Q.STEM rows on page {pi} against --record's {n_a}, and they differ: "
                     "its vertical runs are not evidence about this record's stems")
        cause["runs"] = SS.read_vertical_runs(other, pi)
    if a.stem_ink:
        if not a.pdf:
            ap.error("--stem-ink needs --pdf")
        from tools.omr.hand_truth import score_stems as SS
        from tools.omr.hand_truth.session import _render

        cause["ink"] = SS.InkColumns(_render(a.pdf, page.pdf_page_index, page.dpi).binary < 128)
    rep = score(page, run, page_index=a.page_index, derive=a.derive, ink=ink, stem_cause_inputs=cause or None)
    if not rep["frame_control"]["ok"] and not a.force:
        print(render({**rep, "families": {}, "noteheads": {"status": "withheld"}, "stems": None,
                      "headers": {"summary": {}, "staves": []}}))
        print("FRAME CONTROL FAILED: the record and the truth are not in one page frame, so every number "
              "below it would be fiction. Re-run with --force to print them anyway.")
        return 3
    print(render(rep))
    kinds = miss_kinds(rep, top=10)
    print("COMMONEST MISSES (ADJUDICATE view; 'CV-only' = a class the detector never produced on this page)")
    for k in kinds:
        print(f"  {k['count']:>4}  {k['family']}/{k['truth_class']}{'' if k['detector_produces_this_class'] else ' [CV-only]'}"
              f"  because {k['cause']}  e.g. cell {k['example_cell']} box {k['example_box']}  origins {k['origins']}")
    kinds_all, kinds = kinds, kinds[:5]
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({**public(rep), "miss_kinds": kinds_all}, indent=1, sort_keys=True,
                                    default=str) + "\n")
    if a.crops_dir and a.pdf:
        from tools.omr.hand_truth import score_crops

        # the commonest kinds, plus the commonest way a NOTEHEAD is missed (the pipeline's core symbol)
        extra = [k for k in miss_kinds(rep, top=100) if k["family"] == "notehead" and k not in kinds][:1]
        for p in score_crops.cut(rep, a.pdf, a.crops_dir, list(kinds) + extra):
            print("crop", p)
        cells = [c for c in a.crop_cells.split(",") if c]
        for p in score_crops.cut_cells(rep, a.pdf, a.crops_dir, cells):
            print("crop", p)
        pts = [tuple(float(v) for v in pt.split(",")) for pt in a.crop_ink.split(";") if pt]
        for p in score_crops.cut_ink(rep, a.pdf, a.crops_dir, pts):
            print("crop", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
