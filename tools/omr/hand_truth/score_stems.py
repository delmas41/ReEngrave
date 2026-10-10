"""STEMS in the hand-truth scorer: the CV reader as a second SOURCE, and the per-head attachment
(ROADMAP 1.7; Sean 2026-10-10, *"How reliably are we finding stems?"*). STAGED, GATHER + ADJUDICATE only.

``score.py`` scored the stem family against the detector's ``stem`` CLASS alone (recall 0.057, 13 of 227): the
product does not read stems from the detector, it reads them with CV (``Q.STEM``, ``line_detection.detect_stems``)
and attaches them to heads in ADJUDICATE (``Q.HEAD_STEM``, ``Q.STEM_DIRECTION``). This module scores those, beside
the detector-class number, never instead of it:

* SOURCE 1 (``detector_class``): ``families["stem"]`` exactly as ``score.score_families`` computed it.
* SOURCE 2 (``cv_stem``): every ``Q.STEM`` row of the page, converted from the cell's canonical frame to PAGE pixels
  and matched to Sean's stem boxes by COLUMN and vertical overlap -- not by box IoU, which a 7-pixel-wide mark makes a
  function of the x-jitter of a hand-drawn rectangle.
* PER HEAD: for each of Sean's heads that has a stem box of his, did ADJUDICATE attach a stem (decided / narrowed /
  abstained), is it the RIGHT stem, and is the direction right.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md rule 3 -- nobody could be asked):

* ASSUMED: Sean's stem box is the stem's ink, so a CV stem is "the same stem" when its column (centre x) is within
  ``STEM_MATCH_DX_SPACES`` of his and they share half of the shorter's length. The tolerance is read off the data
  (the widest empty interval of the centre-offset distribution, both directions; see the constant) and is NOT a
  tuning knob. FALSIFIED by the shift control: moving every CV stem one head width must collapse recall.
* ASSUMED: a head has a stem of Sean's when a stem box of his lies within ``HEAD_STEM_TOUCH_SPACES`` of the head's
  box; a head with none is NOT scored as "stemless": about 18 heads on the first page lack a stem box that is printed
  (the 2.81 lane), so "no truth stem" is ``no_truth``, never a false positive (rule 8).
* ASSUMED, DERIVED FROM SEAN'S OWN BOXES: the truth direction of a stem is where it extends beyond its head (up where
  it reaches further above the head than below). It is checked against the engraving's side rule (up -> right, down ->
  left, CLAUDE.md §10) and a head on which the two disagree (a displaced head of a second) is ``ambiguous``, not judged.
* NOT CONFIRMED: that ``upscale_factor`` (canonical -> page) is uniform in x and y per cell. The reader is refused,
  not scored, where a cell's factor cannot be measured (``Q.STEM`` rows with no frame are counted and declined).
"""
from __future__ import annotations

import collections
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from tools.omr.hand_truth import score as S
from tools.omr.hand_truth.store import Rect
from tools.omr.staged import readout as RO
from tools.omr.staged.record import Q

#: ⚠️ A MEASURING INSTRUMENT, NOT A CONSUMER -- see ``score.DERIVED_CHECK``. Must stay a bare literal ``True``.
DERIVED_CHECK = True

#: A CV stem is Sean's stem when their centre columns differ by at most this many LOCAL staff spaces. MEASURED on
#: Brahms 317803 pdf 0 against Sean's 227 stems (``benchmarks/hand-truth-score-2026-10/FINDINGS.md`` section 8): of
#: the truth stems with a vertically-overlapping CV stem, 173 sit within 0.15 spaces and the next nearest is 0.40;
#: from the CV side 175 within 0.15, then 0.40. The widest empty interval of the distribution is 0.15-0.40 in BOTH
#: directions, and two neighbouring truth stems are never closer than 1.57 spaces, so any value in the gap pairs
#: every stem with itself and never with a neighbour. 0.25 is the middle of the gap, not a fitted constant.
STEM_MATCH_DX_SPACES = 0.25
#: Linked = they share at least this much of the SHORTER one's length (the repo's own duplicate-row rule,
#: ``stem_value.STEM_DUPLICATE_MIN_OVERLAP``, is the same half).
STEM_MIN_OVERLAP = 0.5
#: Found = the CV stems linked to a truth stem cover at least this share of ITS length. "Whole" (the strict column) = this.
STEM_FOUND_COVER = 0.5
STEM_WHOLE_COVER = 0.8
#: A head HAS a stem of Sean's when a stem box of his lies within this many spaces (Euclidean gap between the boxes).
#: Measured: 321 of 338 heads sit at gap <= 0.25; the next is 1.4 (the 17 with no stem box, section 8): the empty
#: interval is 0.25-1.4 spaces.
HEAD_STEM_TOUCH_SPACES = 0.30
#: Two derivations of a stem's truth direction (vertical extension vs the side rule) must agree to be judged.
DIRECTIONS = ("up", "down")

Frame = Tuple[int, int, int]  # (system, staff, cell) on one page


# ═════════════════════════════════════════════════════════════════════════════
# The record side: Q.STEM -> page pixels
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class CvStem:
    idx: int
    row_id: str
    frame: Frame
    rect: Rect                      # PAGE pixel corners (x0, y0, x1, y1)
    canon: Tuple[float, float, float, float]  # the row's own [x, y, w, h]
    up: float                       # canonical px per page px of its cell
    sp: float                       # the cell's own staff space, page px

    @property
    def staff(self) -> Tuple[int, int]:
        return (self.frame[0], self.frame[1])


@dataclass
class CvRead:
    """What the CV stem reader left on one page of a record, in page pixels."""
    ran: bool
    stems: List[CvStem] = field(default_factory=list)
    declined: int = 0                 # Q.STEM rows whose cell has no measurable frame
    frame_agreement: Dict[str, Any] = field(default_factory=dict)
    by_row: Dict[str, CvStem] = field(default_factory=dict)


def _subject_frame(key: str, page_index: int) -> Optional[Frame]:
    parts = key.split("/")
    if len(parts) != 5 or parts[0] != "cell" or int(parts[1]) != page_index:
        return None
    return (int(parts[2]), int(parts[3]), int(parts[4]))


def cell_frames(run: RO.Run, page_index: int
                ) -> Tuple[Dict[Frame, Tuple[float, str]], Dict[str, Any], Dict[Frame, float]]:
    """The canonical-px-per-page-px factor of every cell, MEASURED rather than assumed.

    Primary: the median over the cell's detector boxes of canonical width / page width (both are on the record, so
    this reads the cutter's own factor back). Cross-check, and the fallback where a cell has no box wide enough:
    ``Q.CELL_STAFF_SPACE`` over the staff's page spacing (``Q.STAFF_SPACING``). The two must agree; the worst
    relative disagreement is reported, and a cell on which they differ by over 1% is NOT trusted.
    """
    from_boxes: Dict[Frame, List[float]] = collections.defaultdict(list)
    for g in run.glyphs.values():
        if g.page != page_index or g.box_canon is None or g.box_page is None:
            continue
        pw = g.box_page[2] - g.box_page[0]
        ph = g.box_page[3] - g.box_page[1]
        if pw > 5 and ph > 5:
            from_boxes[(g.system, g.staff, g.cell)].append((g.box_canon[2] - g.box_canon[0]) / pw)
    spacing: Dict[Tuple[int, int], float] = {}
    cell_space: Dict[Frame, float] = {}
    for key, rows in run.by_subject.items():
        parts = key.split("/")
        if len(parts) < 4 or parts[1] != str(page_index):
            continue
        for _stage, kind, r in rows:
            if kind != "observation":
                continue
            if r["quantity"] == Q.STAFF_SPACING and parts[0] == "staff":
                try:
                    spacing[(int(parts[2]), int(parts[3]))] = float(r["value"])
                except (TypeError, ValueError):
                    pass
            elif r["quantity"] == Q.CELL_STAFF_SPACE and parts[0] == "cell":
                try:
                    cell_space[(int(parts[2]), int(parts[3]), int(parts[4]))] = float(r["value"])
                except (TypeError, ValueError):
                    pass
    out: Dict[Frame, Tuple[float, str]] = {}
    worst = 0.0
    both = 0
    distrusted: List[Frame] = []
    for fr in set(from_boxes) | set(cell_space):
        a = statistics.median(from_boxes[fr]) if from_boxes.get(fr) else None
        sp = spacing.get((fr[0], fr[1]))
        b = (cell_space[fr] / sp) if (fr in cell_space and sp) else None
        if a is not None and b is not None:
            both += 1
            rel = abs(a - b) / b
            worst = max(worst, rel)
            if rel > 0.01:
                distrusted.append(fr)
                continue
        if a is not None:
            out[fr] = (a, "boxes")
        elif b is not None:
            out[fr] = (b, "staff_space")
    return out, {"cells_with_a_factor": len(out), "cells_checked_two_ways": both,
                 "worst_relative_disagreement": round(worst, 5), "cells_distrusted": len(distrusted)}, cell_space


def read_cv_stems(run: RO.Run, page_index: int) -> CvRead:
    """Every ``Q.STEM`` row on a page, in PAGE pixels. ``ran`` says whether the reader left ANY row or
    abstention on the page: a record the reader never reached reports ``ran=False`` and is REFUSED, not scored
    as zero stems found (rule 8)."""
    frames, agreement, cell_space = cell_frames(run, page_index)
    cell_box: Dict[Frame, Tuple[float, ...]] = {}
    for key, rows in run.by_subject.items():
        fr = _subject_frame(key, page_index)
        if fr is None:
            continue
        for _stage, kind, r in rows:
            if kind == "observation" and r["quantity"] == Q.CELL_BOX:
                cell_box[fr] = tuple(float(v) for v in r["value"])
    out = CvRead(ran=False, frame_agreement=agreement)
    for a in run.abstentions:
        if a["quantity"] == Q.STEM and _subject_frame(a["subject"], page_index) is not None:
            out.ran = True
            break
    for o in run.observations:
        if o["quantity"] != Q.STEM:
            continue
        fr = _subject_frame(o["subject"], page_index)
        if fr is None:
            continue
        out.ran = True
        v = o.get("value")
        if fr not in frames or fr not in cell_box or not isinstance(v, (list, tuple)) or len(v) < 4:
            out.declined += 1
            continue
        up, _how = frames[fr]
        x, y, w, h = (float(t) for t in v[:4])
        cb = cell_box[fr]
        st = CvStem(idx=len(out.stems), row_id=o["id"], frame=fr,
                    rect=(cb[0] + x / up, cb[1] + y / up, cb[0] + (x + w) / up, cb[1] + (y + h) / up),
                    canon=(x, y, w, h), up=up, sp=cell_space.get(fr, 100.0) / up)
        out.stems.append(st)
        out.by_row[st.row_id] = st
    return out


# ═════════════════════════════════════════════════════════════════════════════
# Matching: column + vertical overlap
# ═════════════════════════════════════════════════════════════════════════════


def _y_len(r: Sequence[float]) -> float:
    return max(0.0, r[3] - r[1])


def _y_overlap(a: Sequence[float], b: Sequence[float]) -> float:
    return max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _same_column(t: Sequence[float], c: Sequence[float], sp: float) -> bool:
    """The seam the shift control is red against: a matcher that ignores the column is the bug."""
    return abs(S._cx(t) - S._cx(c)) <= STEM_MATCH_DX_SPACES * sp


def _linked(t: Sequence[float], c: Sequence[float], sp: float) -> bool:
    ov = _y_overlap(t, c)
    if ov <= 0 or not _same_column(t, c, sp):
        return False
    return ov >= STEM_MIN_OVERLAP * min(_y_len(t), _y_len(c))


def _union_cover(target: Sequence[float], others: Iterable[Sequence[float]]) -> float:
    """The share of ``target``'s length covered by the union of ``others``' vertical spans."""
    ln = _y_len(target)
    if ln <= 0:
        return 0.0
    spans = sorted((max(target[1], o[1]), min(target[3], o[3])) for o in others if _y_overlap(target, o) > 0)
    covered, end = 0.0, None
    for a, b in spans:
        if end is None or a > end:
            covered += b - a
            end = b
        elif b > end:
            covered += b - end
            end = b
    return covered / ln


@dataclass
class StemMatch:
    truth: List[S.TruthItem]
    cv: List[CvStem]
    sp_of: Dict[int, float]                 # truth idx -> local staff space (page px)
    links: Dict[int, List[int]]             # truth idx -> linked cv idx
    cover_t: Dict[int, float]               # truth idx -> share of its length covered by linked CV stems
    cover_c: Dict[int, float]               # cv idx -> share of its length covered by linked truth stems
    in_column: Dict[int, List[int]]         # truth idx -> cv idx in its column with ANY vertical overlap
    found: List[int] = field(default_factory=list)
    missed: List[int] = field(default_factory=list)
    valid: List[int] = field(default_factory=list)
    invented: List[int] = field(default_factory=list)


def match_stems(truth: Sequence[S.TruthItem], cv: Sequence[CvStem], sp_of: Dict[int, float]) -> StemMatch:
    links: Dict[int, List[int]] = {}
    in_col: Dict[int, List[int]] = {}
    for t in truth:
        sp = sp_of[t.idx]
        links[t.idx] = [c.idx for c in cv if _linked(t.rect, c.rect, sp)]
        in_col[t.idx] = [c.idx for c in cv if _y_overlap(t.rect, c.rect) > 0 and _same_column(t.rect, c.rect, sp)]
    cv_by = {c.idx: c for c in cv}
    cover_t = {t.idx: _union_cover(t.rect, (cv_by[i].rect for i in links[t.idx])) for t in truth}
    t_by = {t.idx: t for t in truth}
    linked_to: Dict[int, List[int]] = collections.defaultdict(list)
    for ti, cis in links.items():
        for ci in cis:
            linked_to[ci].append(ti)
    cover_c = {c.idx: _union_cover(c.rect, (t_by[i].rect for i in linked_to.get(c.idx, ()))) for c in cv}
    m = StemMatch(list(truth), list(cv), dict(sp_of), links, cover_t, cover_c, in_col)
    m.found = [t.idx for t in truth if cover_t[t.idx] >= STEM_FOUND_COVER]
    m.missed = [t.idx for t in truth if cover_t[t.idx] < STEM_FOUND_COVER]
    m.valid = [c.idx for c in cv if cover_c[c.idx] >= STEM_FOUND_COVER]
    m.invented = [c.idx for c in cv if cover_c[c.idx] < STEM_FOUND_COVER]
    return m


def _rate(n: int, d: int) -> Optional[float]:
    return S._rate(n, d)


def view(m: StemMatch) -> Dict[str, Any]:
    nt, nc = len(m.truth), len(m.cv)
    whole = sum(1 for t in m.truth if m.cover_t[t.idx] >= STEM_WHOLE_COVER)
    fragment = [ti for ti in m.missed if m.in_column[ti]]
    dup = sum(1 for t in m.truth if len(m.links[t.idx]) > 1)
    return {"truth": nt, "read": nc, "found": len(m.found), "found_whole": whole,
            "recall": _rate(len(m.found), nt), "recall_whole": _rate(whole, nt),
            "valid": len(m.valid), "invented": len(m.invented),
            "precision": _rate(len(m.valid), nc),
            "truth_stems_with_more_than_one_cv_row": dup,
            "missed_with_a_fragment_in_the_column": len(fragment),
            "missed_with_nothing_in_the_column": len(m.missed) - len(fragment)}


# ═════════════════════════════════════════════════════════════════════════════
# The truth side: which heads have a stem, and which way it points
# ═════════════════════════════════════════════════════════════════════════════


def _box_gap(a: Sequence[float], b: Sequence[float]) -> float:
    gx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    gy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return (gx * gx + gy * gy) ** 0.5


def truth_direction(head: Sequence[float], stem: Sequence[float]) -> Tuple[Optional[str], Optional[str], str]:
    """``(direction, side-rule direction, verdict)``. The truth direction is where Sean's stem box extends
    beyond the head; the side rule (stem right of the head = up) is the independent check. They agree -> judged;
    they disagree -> ``ambiguous`` (a displaced head of a second stands on the wrong side of its own stem)."""
    ext_up = head[1] - stem[1]
    ext_down = stem[3] - head[3]
    if ext_up == ext_down:
        return None, None, "ambiguous"
    vert = "up" if ext_up > ext_down else "down"
    side = "up" if S._cx(stem) > S._cx(head) else "down"
    return vert, side, ("judged" if vert == side else "ambiguous")


def head_has_stem(head_rect: Sequence[float], stems: Sequence[S.TruthItem], sp: float) -> List[S.TruthItem]:
    return [s for s in stems if _box_gap(head_rect, s.rect) <= HEAD_STEM_TOUCH_SPACES * sp]


# ═════════════════════════════════════════════════════════════════════════════
# Per head: attachment and direction (ADJUDICATE's own verdicts)
# ═════════════════════════════════════════════════════════════════════════════


def _verdict_candidates(v: Dict[str, Any]) -> List[str]:
    out = []
    for c in v.get("candidates") or ():
        val = c.get("value") if isinstance(c, dict) else c
        if isinstance(val, str):
            out.append(val)
    return out


def _same_stem_judge(named: CvStem, truth_stems: Sequence[S.TruthItem], m: StemMatch) -> str:
    """The seam the attach-swap control is red against. ``right`` = the named CV stem is linked to one of THIS
    head's truth stems; ``other`` = linked to a different truth stem; ``invented`` = to none."""
    mine = {t.idx for t in truth_stems}
    linked = {ti for ti, cis in m.links.items() if named.idx in cis}
    if linked & mine:
        return "right"
    return "other" if linked else "invented"


def _direction_judge(read: str, truth: str) -> bool:
    return read == truth


def score_heads(items: Sequence[S.TruthItem], glyph_match: Dict[str, Dict[str, S.FamilyMatch]], run: RO.Run,
                cv: CvRead, m: StemMatch, scope: S.Scope, sp_by_cell: Dict[Optional[str], float],
                stem_cause: Dict[int, str], invented_why: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    invented_why = invented_why or {}
    heads = [it for it in items if it.family == "notehead" and scope.holds(it.rect)]
    stems = [it for it in items if it.family == "stem" and scope.holds(it.rect)]
    if "notehead" not in glyph_match:
        return {"status": "REFUSED: notehead family not scored"}
    fg = glyph_match["notehead"]["gather"]
    fa = glyph_match["notehead"]["adjudicate"]
    glyph_by = {g.idx: g for g in fg.read}
    rows: List[Dict[str, Any]] = []
    for h in heads:
        sp = sp_by_cell.get(h.cell_id) or statistics.median(sp_by_cell.values())
        mine = head_has_stem(h.rect, stems, sp)
        row: Dict[str, Any] = {"truth_id": h.id, "cell": h.cell_id, "cls": h.cls,
                               "staff": f"{h.staff_by_cell[0]}.{h.staff_by_cell[1]}" if h.staff_by_cell else None,
                               "truth_stems": [t.id for t in mine]}
        if not mine:
            row["has_truth_stem"] = False
            rows.append(row)
            continue
        row["has_truth_stem"] = True
        row["stem_found_by_cv"] = any(t.idx in m.found for t in mine)
        row["stem_miss_cause"] = None if row["stem_found_by_cv"] else stem_cause.get(mine[0].idx)
        dirs = [truth_direction(h.rect, t.rect) for t in mine]
        kinds = {d[0] for d in dirs if d[2] == "judged"}
        row["direction_truth"] = next(iter(kinds)) if len(kinds) == 1 and all(d[2] == "judged" for d in dirs) else None
        row["direction_truth_state"] = "judged" if row["direction_truth"] else "ambiguous"
        row["read_as_head_at_adjudicate"] = h.idx in fa.pairs
        if h.idx not in fg.pairs:
            row["attach"] = "head_missed"
            rows.append(row)
            continue
        g = glyph_by[fg.pairs[h.idx][0]]
        row["read_key"] = g.key
        dv = run.standing(g.key, Q.DURATION, "ADJUDICATE")
        row["duration_state"] = "none" if dv is None else dv["outcome"]
        reach = run.obs_at(g.key, Q.HEAD_STEM_REACH)
        row["reach"] = reach[-1]["value"] if reach else "absent"
        v = run.standing(g.key, Q.HEAD_STEM, "ADJUDICATE")
        if v is None:
            row["attach"], row["attach_state"] = "no_verdict", "none"
        elif v["outcome"] == "decided":
            row["attach_state"], row["attach_reason"] = "decided", v.get("reason")
            named = cv.by_row.get(v.get("value"))
            if named is None:
                row["attach"] = "wrong_stem_frameless"
            else:
                j = _same_stem_judge(named, mine, m)
                row["attach"] = {"right": "right", "other": "wrong_other_stem", "invented": "wrong_invented_stem"}[j]
                if j != "right":
                    row["named_stem_on"] = invented_why.get(named.idx, "a stem of Sean's (another)")
        elif v["outcome"] == "narrowed":
            row["attach_state"], row["attach_reason"] = "narrowed", v.get("reason")
            cands = [cv.by_row[c] for c in _verdict_candidates(v) if c in cv.by_row]
            has = any(_same_stem_judge(c, mine, m) == "right" for c in cands)
            row["attach"] = "narrowed_with_the_right_stem" if has else "narrowed_without_the_right_stem"
        else:
            row["attach_state"], row["attach_reason"] = "abstained", v.get("reason")
            row["attach"] = ("abstained_stem_was_found" if row["stem_found_by_cv"]
                             else "abstained_stem_not_found")
            if row["stem_found_by_cv"]:
                linked = [c for t in mine for c in cv.stems if c.idx in m.links[t.idx]]
                row["gap_to_found_stem_spaces"] = round(min(_box_gap(g.rect, c.rect) for c in linked) / sp, 2)
        d = run.standing(g.key, Q.STEM_DIRECTION, "ADJUDICATE")
        if d is None:
            row["direction"] = "none"
        elif d["outcome"] != "decided" or d.get("value") not in DIRECTIONS:
            row["direction"] = "abstained"
            row["direction_reason"] = d.get("reason")
        elif row["direction_truth"] is None:
            row["direction"] = "no_truth"
            row["direction_read"] = d["value"]
        else:
            row["direction_read"] = d["value"]
            row["direction"] = "right" if _direction_judge(d["value"], row["direction_truth"]) else "wrong"
        rows.append(row)
    stemmed = [r for r in rows if r["has_truth_stem"]]
    c_att = collections.Counter(r["attach"] for r in stemmed)
    c_dir = collections.Counter(r.get("direction", "head_missed") for r in stemmed)
    judged_dir = c_dir["right"] + c_dir["wrong"]
    read_heads = [r for r in stemmed if r["read_as_head_at_adjudicate"]]
    return {
        "status": "scored", "truth_heads_in_scored_cells": len(heads),
        "truth_heads_with_a_truth_stem": len(stemmed),
        "truth_heads_without_a_truth_stem": len(heads) - len(stemmed),
        "note_no_truth_stem": ("a head with no stem box of Sean's is NOT a false positive: ~18 printed stems lack a "
                               "box (2.81), and a whole note has none"),
        "attach": dict(c_att),
        "attach_right_of_stemmed": _rate(c_att["right"], len(stemmed)),
        "attach_right_of_heads_read_at_adjudicate": _rate(sum(1 for r in read_heads if r["attach"] == "right"),
                                                          len(read_heads)),
        "heads_read_at_adjudicate": len(read_heads),
        "attach_state": dict(collections.Counter(r.get("attach_state", "n/a") for r in stemmed)),
        "attach_abstain_reasons": dict(collections.Counter(
            r.get("attach_reason") for r in stemmed if r.get("attach_state") == "abstained")),
        "direction": dict(c_dir),
        "direction_right_of_judged": _rate(c_dir["right"], judged_dir),
        "direction_truth_ambiguous": sum(1 for r in stemmed if r["direction_truth_state"] == "ambiguous"),
        "heads_without_the_right_stem_by_cause": dict(collections.Counter(
            _no_right_stem_cause(r) for r in stemmed if r["attach"] != "right")),
        "found_not_attached_gap_spaces": sorted(r["gap_to_found_stem_spaces"] for r in stemmed
                                                if "gap_to_found_stem_spaces" in r),
        "wrongly_attached_to": dict(collections.Counter(r["named_stem_on"] for r in stemmed if "named_stem_on" in r)),
        "duration_standing_by_attach": {
            ("right stem" if right else "no right stem"): dict(collections.Counter(
                r.get("duration_state", "head not gathered") for r in stemmed if (r["attach"] == "right") == right))
            for right in (True, False)},
        "reach_beside_the_head": _reach_summary(stemmed),
        "_rows": rows,
    }


def _reach_summary(stemmed: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """``Q.HEAD_STEM_REACH`` (ROADMAP 2.58d): a second raster reader of the stem beside a CONTESTED head, filed on
    page pixels. It exists only where the head was contested, so most heads have none; where it does, is its
    direction the truth's?"""
    have = [r for r in stemmed if r.get("reach") not in (None, "absent")]
    judged = [r for r in have if r["reach"] in DIRECTIONS and r.get("direction_truth")]
    return {"heads_with_a_reach_row": len(have), "values": dict(collections.Counter(r["reach"] for r in have)),
            "up_or_down_against_a_judged_truth_direction": len(judged),
            "agrees": sum(1 for r in judged if r["reach"] == r["direction_truth"])}


def _no_right_stem_cause(r: Dict[str, Any]) -> str:
    if r["attach"] == "head_missed":
        return "the head itself was never gathered"
    if r["attach"] in ("abstained_stem_not_found", "no_verdict") or not r.get("stem_found_by_cv", True):
        return f"stem not found by CV ({r.get('stem_miss_cause') or 'cause unknown'})"
    return {"abstained_stem_was_found": "stem found, not attached to the head",
            "wrong_other_stem": "attached to another stem",
            "wrong_invented_stem": "attached to a CV stem that is not one of Sean's",
            "wrong_stem_frameless": "attached to a CV stem with no page frame",
            "narrowed_with_the_right_stem": "narrowed between stems (the right one among them)",
            "narrowed_without_the_right_stem": "narrowed between stems (the right one not among them)"
            }.get(r["attach"], r["attach"])


# ═════════════════════════════════════════════════════════════════════════════
# What the CV stems that are not Sean's sit on
# ═════════════════════════════════════════════════════════════════════════════


def explain_invented(m: StemMatch, items: Sequence[S.TruthItem], heads_without_stem: Sequence[S.TruthItem]
                     ) -> Dict[int, str]:
    """For each invented CV stem, what of Sean's boxes it lies on: the family of the truth box covering the most of
    it, or ``a head of Sean's with no stem box`` or ``no truth box``. Facts about where the ink is, not a verdict
    that the CV stem is wrong: a head with no stem box is a truth gap (2.81), and Sean has not boxed everything."""
    out: Dict[int, str] = {}
    for ci in m.invented:
        c = next(x for x in m.cv if x.idx == ci)
        best, best_cov = None, 0.0
        ln = max(1e-9, (c.rect[2] - c.rect[0]) * (c.rect[3] - c.rect[1]))
        for it in items:
            if it.family == "stem":
                continue
            ix = max(0.0, min(c.rect[2], it.rect[2]) - max(c.rect[0], it.rect[0]))
            iy = max(0.0, min(c.rect[3], it.rect[3]) - max(c.rect[1], it.rect[1]))
            cov = ix * iy / ln
            if cov > best_cov:
                best, best_cov = it, cov
        near_head = any(_box_gap(c.rect, h.rect) <= HEAD_STEM_TOUCH_SPACES * c.sp for h in heads_without_stem)
        if near_head:
            out[ci] = "touches a head of Sean's that has no stem box"
        elif best is not None and best_cov >= 0.3:
            out[ci] = f"lies on a truth {best.family}"
        else:
            out[ci] = "no truth box under it"
    return out


# ═════════════════════════════════════════════════════════════════════════════
# The whole stem score
# ═════════════════════════════════════════════════════════════════════════════


def per_staff(m: StemMatch, items: Sequence[S.TruthItem]) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    for t in m.truth:
        k = f"{t.staff_by_cell[0]}.{t.staff_by_cell[1]}" if t.staff_by_cell else "?"
        rows[k]["truth"] += 1
        rows[k]["found"] += t.idx in m.found
    for c in m.cv:
        k = f"{c.staff[0]}.{c.staff[1]}"
        rows[k]["read"] += 1
        rows[k]["valid"] += c.idx in m.valid
    out = {}
    for k, d in sorted(rows.items(), key=lambda kv: tuple(int(x) if x.isdigit() else 99 for x in kv[0].split("."))):
        out[k] = {"truth": d["truth"], "found": d["found"], "missed": d["truth"] - d["found"],
                  "recall": _rate(d["found"], d["truth"]), "read": d["read"], "invented": d["read"] - d["valid"],
                  "precision": _rate(d["valid"], d["read"])}
    return out


def score_stems(page, items: Sequence[S.TruthItem], glyphs: Sequence[S.ReadGlyph],
                matches: Dict[str, Dict[str, S.FamilyMatch]], run: RO.Run, page_index: int,
                families: Dict[str, Any], *, cause_inputs: Optional[Dict[str, Any]] = None,
                cv_override: Optional[CvRead] = None) -> Dict[str, Any]:
    """The stem family's SECOND source and the per-head attachment. ``families['stem']`` (the detector class) is
    handed in and reported unchanged, beside the CV source."""
    detector = {k: families.get("stem", {}).get(k) for k in ("status", "gather", "adjudicate")}
    cv = cv_override if cv_override is not None else read_cv_stems(run, page_index)
    out: Dict[str, Any] = {"detector_class": detector}
    if not cv.ran:
        out["cv_stem"] = {"status": "REFUSED: the record holds no Q.STEM row or abstention on this page -- the CV "
                                    "stem reader did not run, which is not the same as finding none"}
        return out
    full = S.fully_labeled(page)
    scope = S.Scope(full)
    bands = {b.cell_id: b.space for b in S.staff_bands(page)}
    t_stems = [it for it in items if it.family == "stem" and scope.holds(it.rect)]
    sp_all = statistics.median(bands.values()) if bands else 1.0
    sp_of = {t.idx: bands.get(t.cell_id, sp_all) for t in t_stems}
    cv_in = [c for c in cv.stems if scope.holds(c.rect)]
    # re-index the in-scope CV stems 0..n-1 so the match tables are dense
    remap = {c.idx: i for i, c in enumerate(cv_in)}
    cv_idx = [CvStem(remap[c.idx], c.row_id, c.frame, c.rect, c.canon, c.up, c.sp) for c in cv_in]
    by_row = {c.row_id: c for c in cv_idx}
    m = match_stems(t_stems, cv_idx, sp_of)
    cv_view = view(m)
    heads_no_stem = [h for h in items if h.family == "notehead" and scope.holds(h.rect)
                     and not head_has_stem(h.rect, t_stems, bands.get(h.cell_id, sp_all))]
    inv_why = explain_invented(m, items, heads_no_stem)
    cause_in = cause_inputs or {}
    causes = explain_missed(m, items, cause_in)
    cv_for_heads = CvRead(True, cv_idx, cv.declined, cv.frame_agreement, by_row)
    out["cv_stem"] = {
        "status": "scored", **cv_view,
        "q_stem_rows_on_page": len(cv.stems) + cv.declined, "rows_declined_no_frame": cv.declined,
        "rows_outside_scored_cells": len(cv.stems) - len(cv_in),
        "frame": cv.frame_agreement,
        "tolerance": {"dx_spaces": STEM_MATCH_DX_SPACES, "min_overlap_of_shorter": STEM_MIN_OVERLAP,
                      "found_cover": STEM_FOUND_COVER, "whole_cover": STEM_WHOLE_COVER},
        "invented_on": dict(collections.Counter(inv_why.values())),
        "per_staff": per_staff(m, items),
        "missed_by_cause": causes["by_cause"],
        "missed_facts": causes["facts"],
    }
    # either source: a truth stem is found if the CV reader or the detector class boxed it
    det_found = {ti for ti in (matches.get("stem", {}).get("adjudicate").pairs if "stem" in matches else {})}
    any_found = set(m.found) | det_found
    out["either_source"] = {"truth": len(t_stems), "found": len([t for t in t_stems if t.idx in any_found]),
                            "recall": _rate(len([t for t in t_stems if t.idx in any_found]), len(t_stems)),
                            "found_by_detector_class_only": len([t for t in t_stems
                                                                if t.idx in det_found and t.idx not in m.found])}
    out["heads"] = score_heads(items, matches, run, cv_for_heads, m, scope,
                               {c.id: bands.get(c.id, sp_all) for c in page.cells},
                               causes["by_truth_idx"], inv_why)
    out["_match"] = m
    out["_cv"] = cv_for_heads
    out["_invented_why"] = inv_why
    out["_miss_cause"] = causes["by_truth_idx"]
    return out


# ═════════════════════════════════════════════════════════════════════════════
# The misses, by cause -- FACTS, each tied to the constant and code path that decides it
# ═════════════════════════════════════════════════════════════════════════════

def read_vertical_runs(rec: Dict[str, Any], page_index: int) -> List[Dict[str, Any]]:
    """Every vertical run the stem opening produced on a page, accepted or refused, in PAGE pixels, from a RAW
    record dict (``record_io.load_record``) gathered with ``OMR_VERTICAL_RUNS``. Each carries the FIRST filter
    that refused it (``line_detection.RUN_OUTCOMES``). ``readout.load_run`` cannot be used on such a record when
    it was gathered with no detector."""
    out: List[Dict[str, Any]] = []
    for o in rec["record"]["observations"]:
        if o["quantity"] != Q.VERTICAL_RUN:
            continue
        parts = o["subject"].split("/")
        if len(parts) < 6 or parts[0] != "glyph" or int(parts[1]) != page_index:
            continue
        d = o.get("detail") or {}
        box = d.get("run_bbox_page_px")
        if not box:
            continue
        out.append({"rect": tuple(float(v) for v in box), "outcome": str(d.get("run_outcome")),
                    "frame": (int(parts[2]), int(parts[3]), int(parts[4]))})
    return out


def stem_sets_equal(run: RO.Run, rec: Dict[str, Any], page_index: int) -> Tuple[bool, int, int]:
    """Do two records hold the SAME ``Q.STEM`` rows on a page? The vertical-run record is only evidence about the
    scored record's stems if its own ``Q.STEM`` set is identical (the flag adds rows, it must change none)."""
    def sets(rows: Iterable[Dict[str, Any]]) -> List[Tuple[str, Tuple[float, ...]]]:
        return sorted((o["subject"], tuple(float(v) for v in o["value"][:4])) for o in rows
                      if o["quantity"] == Q.STEM and o["subject"].startswith(f"cell/{page_index}/"))
    a, b = sets(run.observations), sets(rec["record"]["observations"])
    return a == b, len(a), len(b)


class InkColumns:
    """The page raster read at a truth stem's column. ``ink`` is a boolean array (True = ink) in the PAGE frame.

    Two facts about the ink itself, independent of any stem reader: the longest UNBROKEN vertical run in the stem's
    column (the vertical opening keeps a column only where an unbroken run is at least ``kernel`` spaces), and the
    share of the stem's length on which the best column is inked at all. The best column within +-``BAND_SPACES`` of
    Sean's box centre is taken: his rectangle is hand-drawn and a stem is 6-9 px wide."""

    BAND_SPACES = 0.15

    def __init__(self, ink: Any):
        self.ink = ink

    def _columns(self, rect: Sequence[float], sp: float) -> Tuple[int, int, int, int]:
        h, w = self.ink.shape
        cx = S._cx(rect)
        x0 = max(0, int(round(cx - self.BAND_SPACES * sp)))
        x1 = min(w, int(round(cx + self.BAND_SPACES * sp)) + 1)
        y0, y1 = max(0, int(round(rect[1]))), min(h, int(round(rect[3])))
        return x0, x1, y0, y1

    def longest_run_spaces(self, rect: Sequence[float], sp: float) -> float:
        x0, x1, y0, y1 = self._columns(rect, sp)
        best = 0
        for x in range(x0, x1):
            col = self.ink[y0:y1, x]
            run = 0
            for v in col:
                run = run + 1 if v else 0
                best = max(best, run)
        return best / sp

    def ink_share(self, rect: Sequence[float], sp: float) -> float:
        x0, x1, y0, y1 = self._columns(rect, sp)
        if y1 <= y0 or x1 <= x0:
            return 0.0
        return max(float(self.ink[y0:y1, x].mean()) for x in range(x0, x1))


#: Where each refusal comes from, so a count names its code path (``line_detection.detect_stems``).
RUN_REFUSALS = {
    "too SHORT": ("h < min_height_lines (2.0 spaces)", "line_detection.detect_stems min_height_lines"),
    "too TALL": ("h > STEM_MAX_HEIGHT_LINES (8.0 spaces)", "line_detection.STEM_MAX_HEIGHT_LINES"),
    "too WIDE": ("w > max_width_lines (0.6 spaces)", "line_detection.detect_stems max_width_lines"),
    "at a CELL EDGE": ("x within 0.8 spaces of the cell edge", "line_detection.detect_stems edge_margin"),
    "too little AREA": ("area < max(4, 0.5 * spacing)", "line_detection.detect_stems area floor"),
    "ASPECT": ("h / w < 3", "line_detection.detect_stems aspect"),
    "PAIRED": ("a neighbour within 0.9 spaces overlapping 0.6 (the accidental rule)",
               "line_detection._drop_paired_strokes accidental_pair_gap_lines/_overlap"),
}


def run_refusal_word(outcome: str) -> str:
    for k in RUN_REFUSALS:
        if outcome.startswith(k) or k in outcome:
            return k
    return outcome


def runs_at(rect: Sequence[float], sp: float, runs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The vertical runs that CONTAIN a truth stem's column: the run's x-extent, widened by the match tolerance,
    holds the stem's centre, and they share vertical extent. (Not the run's CENTRE: a stem fused with the head
    beside it is a run a space wide whose centre is half a space from the stem.)"""
    cx = S._cx(rect)
    tol = STEM_MATCH_DX_SPACES * sp
    return [r for r in runs if r["rect"][0] - tol <= cx <= r["rect"][2] + tol and _y_overlap(rect, r["rect"]) > 0]


#: ``line_detection.detect_stems`` ``accidental_pair_gap_lines`` / ``accidental_pair_overlap``: the partner of a
#: PAIRED run is another run within this many spaces (centre to centre) sharing this much of the shorter's length.
PAIR_GAP_SPACES = 0.9
PAIR_OVERLAP = 0.6


def paired_partners(t: S.TruthItem, sp: float, near: Sequence[Dict[str, Any]], runs: Sequence[Dict[str, Any]],
                    truth: Sequence[S.TruthItem]) -> List[Dict[str, Any]]:
    """For a stem refused as PAIRED: the strokes the pair rule saw beside it, and whether each is one of Sean's stems."""
    out: List[Dict[str, Any]] = []
    for q in (r for r in near if run_refusal_word(r["outcome"]) == "PAIRED"):
        qc = S._cx(q["rect"])
        for r in runs:
            if r is q or r["frame"] != q["frame"] or run_refusal_word(r["outcome"]) not in ("PAIRED", "accepted"):
                continue
            if abs(S._cx(r["rect"]) - qc) > PAIR_GAP_SPACES * sp:
                continue
            ov = _y_overlap(q["rect"], r["rect"])
            if ov <= 0 or ov / max(1e-9, min(_y_len(q["rect"]), _y_len(r["rect"]))) < PAIR_OVERLAP:
                continue
            is_stem = any(x.family == "stem" and _y_overlap(x.rect, r["rect"]) > 0
                          and abs(S._cx(x.rect) - S._cx(r["rect"])) <= STEM_MATCH_DX_SPACES * sp for x in truth)
            out.append({"centre_offset_spaces": round((S._cx(r["rect"]) - qc) / sp, 2),
                        "height_spaces": round(_y_len(r["rect"]) / sp, 2), "is_a_truth_stem": is_stem,
                        "lies_on": _lies_on(r["rect"], truth)})
    return out


def _lies_on(rect: Sequence[float], truth: Sequence[S.TruthItem]) -> str:
    """The family of the truth box (not a stem) that covers most of ``rect``, or ``no truth box``."""
    area = max(1e-9, (rect[2] - rect[0]) * (rect[3] - rect[1]))
    best, best_cov = "no truth box", 0.3
    for it in truth:
        if it.family == "stem":
            continue
        ix = max(0.0, min(rect[2], it.rect[2]) - max(rect[0], it.rect[0]))
        iy = max(0.0, min(rect[3], it.rect[3]) - max(rect[1], it.rect[1]))
        if ix * iy / area > best_cov:
            best, best_cov = it.family, ix * iy / area
    return best


def explain_missed(m: StemMatch, items: Sequence[S.TruthItem], inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Every missed truth stem, with the facts about it. ``inputs`` may hold ``runs`` (every vertical run the stem
    opening produced, accepted or refused, in page pixels with the first filter that refused it -- from a record
    gathered with ``OMR_VERTICAL_RUNS``) and ``ink`` (an object with ``longest_run_spaces(rect)``). Absent, the
    cause is only what the record itself says: a CV fragment in the column or nothing."""
    runs: Sequence[Dict[str, Any]] = inputs.get("runs") or ()
    ink = inputs.get("ink")
    heads = [it for it in items if it.family == "notehead"]
    beams = [it for it in items if it.family == "beam"]
    arcs = [it for it in items if it.family in ("slur", "tie")]
    by_cause: collections.Counter = collections.Counter()
    by_truth: Dict[int, str] = {}
    facts_rows: List[Dict[str, Any]] = []
    for ti in m.missed:
        t = next(x for x in m.truth if x.idx == ti)
        sp = m.sp_of[ti]
        facts = stem_facts(t, sp, heads, beams, arcs)
        cause = None
        if m.in_column[ti]:
            cause = "a CV stem covers only a fragment of it"
        elif runs:
            near = runs_at(t.rect, sp, runs)
            facts["vertical_runs_at_its_column"] = [
                {"outcome": r["outcome"], "width_spaces": round((r["rect"][2] - r["rect"][0]) / sp, 2),
                 "height_spaces": round(_y_len(r["rect"]) / sp, 2),
                 "centre_offset_spaces": round((S._cx(r["rect"]) - S._cx(t.rect)) / sp, 2)} for r in near]
            if near:
                words = sorted({run_refusal_word(r["outcome"]) for r in near})
                facts["run_refused_for"] = words
                cause = "stem opening produced a run and refused it: " + " + ".join(words)
                if "PAIRED" in words:
                    facts["paired_with"] = paired_partners(t, sp, near, runs, items)
            else:
                cause = "the stem opening produced no run at its column"
        else:
            cause = "no CV stem in its column (refusing filter not on the record: no --stem-runs)"
        if ink is not None:
            facts["ink_longest_unbroken_run_spaces"] = round(ink.longest_run_spaces(t.rect, sp), 2)
            facts["ink_share_of_length_in_column"] = round(ink.ink_share(t.rect, sp), 3)
        by_cause[cause] += 1
        by_truth[ti] = cause
        facts["id"], facts["cell"], facts["cause"] = t.id, t.cell_id, cause
        facts_rows.append(facts)
    found_facts = [stem_facts(next(x for x in m.truth if x.idx == ti), m.sp_of[ti], heads, beams, arcs)
                   for ti in m.found]
    return {"by_cause": dict(by_cause), "by_truth_idx": by_truth,
            "facts": {"missed": facts_rows, "found_rates": feature_table(facts_rows, found_facts)}}


def stem_facts(t: S.TruthItem, sp: float, heads: Sequence[S.TruthItem], beams: Sequence[S.TruthItem],
               arcs: Sequence[S.TruthItem]) -> Dict[str, Any]:
    """Facts about one truth stem, each a measurement of Sean's boxes in this stem's own staff space."""
    r = t.rect
    mine = [h for h in heads if _box_gap(h.rect, r) <= HEAD_STEM_TOUCH_SPACES * sp]
    stacked = False
    for i, a in enumerate(mine):
        for b in mine[i + 1:]:
            if abs(S._cy(a.rect) - S._cy(b.rect)) <= 1.3 * sp:   # a step or a second apart: the heads touch
                stacked = True
    touch = lambda boxes: any(_box_gap(b.rect, r) <= 0.5 * sp for b in boxes)  # noqa: E731
    steps = sorted(round(abs(S._cy(a.rect) - S._cy(b.rect)) / (sp / 2.0))
                   for i, a in enumerate(mine) for b in mine[i + 1:])
    sides = {S._cx(h.rect) > S._cx(r) for h in mine}
    return {"length_spaces": round(_y_len(r) / sp, 2), "width_spaces": round((r[2] - r[0]) / sp, 3),
            "heads_on_it": len(mine), "chord": len(mine) >= 2, "stacked_heads": stacked,
            "closest_heads_apart_in_steps": steps[0] if steps else None,
            "heads_on_both_sides_of_the_stem": len(sides) == 2,
            "touches_a_beam_box": touch(beams), "touches_a_slur_or_tie_box": touch(arcs)}


def feature_table(missed: Sequence[Dict[str, Any]], found: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """For each yes/no fact: of the truth stems that HAVE it, how many were found. A fact that is common
    among the found is not what loses a stem."""
    tests: Dict[str, Callable[[Dict[str, Any]], bool]] = {
        "short (< 2.5 spaces)": lambda f: f["length_spaces"] < 2.5,
        "long (>= 4.5 spaces)": lambda f: f["length_spaces"] >= 4.5,
        "chord (2+ heads on it)": lambda f: f["chord"],
        "stacked heads (a step or a second apart)": lambda f: f["stacked_heads"],
        "closest two heads a second apart (1 step)": lambda f: f["closest_heads_apart_in_steps"] == 1,
        "closest two heads a third apart (2 steps)": lambda f: f["closest_heads_apart_in_steps"] == 2,
        "closest two heads a fourth or more apart": lambda f: (f["closest_heads_apart_in_steps"] or 0) >= 3,
        "heads on both sides of the stem": lambda f: f["heads_on_both_sides_of_the_stem"],
        "one head on it": lambda f: f["heads_on_it"] == 1,
        "touches a beam box": lambda f: f["touches_a_beam_box"],
        "touches a slur or tie box": lambda f: f["touches_a_slur_or_tie_box"],
        "no head box on it": lambda f: f["heads_on_it"] == 0,
    }
    out = {}
    for name, fn in tests.items():
        a, b = sum(1 for f in missed if fn(f)), sum(1 for f in found if fn(f))
        out[name] = {"missed": a, "found": b, "found_share": _rate(b, a + b)}
    return out


def public(st: Dict[str, Any]) -> Dict[str, Any]:
    """The JSON-safe part of a stem score (underscore keys hold objects; the per-head rows are kept as ``rows``)."""
    out = {k: v for k, v in st.items() if not k.startswith("_")}
    h = out.get("heads")
    if isinstance(h, dict):
        out["heads"] = {("rows" if k == "_rows" else k): v for k, v in h.items()}
    return out


# ═════════════════════════════════════════════════════════════════════════════
# Text
# ═════════════════════════════════════════════════════════════════════════════


def render(st: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("STEMS  two sources for the stem family (the detector CLASS, and the CV reader the product uses)")
    d = st["detector_class"]
    if d.get("status") == "scored":
        g, a = d["gather"], d["adjudicate"]
        L.append(f"  detector class `stem`   truth {g['truth']:>4}  read {g['read']:>4}  GATHER recall {S._fmt(g['recall'])}"
                 f" precision {S._fmt(g['precision'])}  ADJUDICATE recall {S._fmt(a['recall'])}")
    c = st["cv_stem"]
    if c.get("status") != "scored":
        L.append(f"  CV stems (Q.STEM)       {c['status']}")
        return "\n".join(L) + "\n"
    L.append(f"  CV stems (Q.STEM)       truth {c['truth']:>4}  read {c['read']:>4}  found {c['found']} "
             f"(whole {c['found_whole']})  recall {S._fmt(c['recall'])}  precision {S._fmt(c['precision'])} "
             f"({c['invented']} not Sean's)")
    e = st["either_source"]
    L.append(f"  either source           found {e['found']} of {e['truth']}  recall {S._fmt(e['recall'])}  "
             f"({e['found_by_detector_class_only']} only the detector class boxed)")
    tol = c["tolerance"]
    L.append(f"    match: column within {tol['dx_spaces']} local space, sharing {tol['min_overlap_of_shorter']} of the "
             f"shorter's length; found = {tol['found_cover']} of the truth stem covered")
    L.append(f"    Q.STEM rows on the page {c['q_stem_rows_on_page']}, declined (no frame) {c['rows_declined_no_frame']}, "
             f"outside scored cells {c['rows_outside_scored_cells']}; frame {c['frame']}")
    L.append(f"    CV stems that are not Sean's, by what lies under them: {c['invented_on']}")
    L.append(f"    per staff (system.staff: found/truth, valid/read):")
    for k, v in c["per_staff"].items():
        L.append(f"      {k:<5} found {v['found']:>3}/{v['truth']:<3} recall {S._fmt(v['recall'])}   "
                 f"valid {v['read'] - v['invented']:>3}/{v['read']:<3} precision {S._fmt(v['precision'])}")
    L.append(f"    missed stems by cause: {c['missed_by_cause']}")
    L.append("    how often a stem WITH each fact was found (a fact common among the found is not what loses a stem):")
    for k, v in c["missed_facts"]["found_rates"].items():
        L.append(f"      {k:<42} missed {v['missed']:>3}  found {v['found']:>3}  found share {S._fmt(v['found_share'])}")
    h = st.get("heads") or {}
    if h.get("status") == "scored":
        L.append("")
        L.append(f"STEMS PER HEAD  {h['truth_heads_with_a_truth_stem']} of {h['truth_heads_in_scored_cells']} heads "
                 f"have a stem box of Sean's; {h['truth_heads_without_a_truth_stem']} have none "
                 "(unjudged: a truth gap or a whole note, never a false positive)")
        L.append(f"  attached the RIGHT stem {h['attach'].get('right', 0)} of {h['truth_heads_with_a_truth_stem']} "
                 f"= {S._fmt(h['attach_right_of_stemmed'])}   (of the {h['heads_read_at_adjudicate']} also read as a head "
                 f"at ADJUDICATE: {S._fmt(h['attach_right_of_heads_read_at_adjudicate'])})")
        L.append(f"  Q.HEAD_STEM standing: {h['attach_state']}  abstain reasons {h['attach_abstain_reasons']}")
        L.append(f"  every outcome: {h['attach']}")
        L.append(f"  heads WITHOUT the right stem, by cause: {h['heads_without_the_right_stem_by_cause']}")
        if h["found_not_attached_gap_spaces"]:
            L.append(f"  found but not attached: the found stem stands this far (spaces) from the head box: "
                     f"{h['found_not_attached_gap_spaces']}")
        if h["wrongly_attached_to"]:
            L.append(f"  attached to a stem that is not the head's: {h['wrongly_attached_to']}")
        L.append(f"  Q.DURATION standing at ADJUDICATE, by whether the head got its right stem: "
                 f"{h['duration_standing_by_attach']}")
        L.append(f"  Q.HEAD_STEM_REACH beside the head (contested heads only): {h['reach_beside_the_head']}")
        L.append(f"  Q.STEM_DIRECTION {h['direction']}  right of judged {S._fmt(h['direction_right_of_judged'])} "
                 f"(truth direction ambiguous on {h['direction_truth_ambiguous']} heads)")
    return "\n".join(L) + "\n"
