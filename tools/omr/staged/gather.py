"""GATHER — the readers, wired in as they are, emitting measurements.

⚠️ CHANGE FROM THE DESIGN, AND WHY. The design specified that each reader
gains a keyword-only `log` out-parameter and emits its own rows, on the
tree's own convention that widening a RETURN to carry a record is how a
recording change acquires a blast radius (`transcribe.py:1744-1746`,
`:1492-1495`).

That is still the right end state. It is the wrong thing to do FIRST, because
the instruction is to build alongside with the existing pipeline untouched,
and adding an out-parameter to a dozen readers touches a dozen files that the
old path also runs through. So GATHER is a TRANSLATING layer: it calls the
existing readers unchanged and turns what they return into rows.

⚠️ THE COST OF THAT CHOICE IS REAL AND IS NOT HIDDEN. A translating layer can
only record what a reader RETURNS, so a reader whose refusal reason lives in
a local variable cannot be quoted -- it can only be MIRRORED, by re-deriving
the same condition from the same inputs. Every mirror below is marked
`mirror=True` in its detail, so nothing downstream can mistake our
re-derivation for the reader's own word. Where a reader already exposes its
reasoning (`locate_clef(trace=...)`) the trace is used and there is no mirror.
Converting the mirrors into real emissions is the follow-on, and it is the
one place this build knowingly owes the design something.

⚠️ NOTHING HERE IS MEASURED. Which readers run, in what order, and what each
emits are ASSUMPTIONS -- see ASSUMPTIONS.md.
"""

from __future__ import annotations

import os
from typing import (Any, Dict, Iterable, List, Optional, Sequence, Tuple)

from . import record as R
from .record import ABSTAIN, Log, Q, READERS, Subject

# ─────────────────────────────────────────────────────────────────────────────
# Frames -- WHERE a reading was taken. Two readers of the same quantity on
# different crops are two signals; on the same crop they are one.
# ─────────────────────────────────────────────────────────────────────────────

FRAME_PAGE = "page"
FRAME_SYSTEM = "system"
FRAME_HEADER_WINDOW = "header_window"
FRAME_MARGIN = "system_margin"


def frame_cell(measure_index: int) -> str:
    return f"cell:{measure_index}"


# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ Staff index normalisation -- a real ambiguity, resolved here once
# ─────────────────────────────────────────────────────────────────────────────


def _system_local(staves: Sequence[Any]) -> Dict[int, Tuple[int, int]]:
    """Map each staff's PAGE-WIDE index to (system_index, index within system).

    ⚠️ `Staff.staff_index` and `MeasureCell.staff_index` are both documented
    "0-based within the PAGE" -- system 1's staves continue system 0's count.
    Every join in this project must be by position WITHIN THE SYSTEM
    (`draft_windows` says so explicitly, and joining by the page-wide number
    puts a staff on another instrument's part). One number, two meanings.

    So the staged pipeline addresses staves system-locally and normalises
    here, once, at the boundary. The page-wide index is kept in every row's
    detail as `page_staff_index` so nothing is lost -- this is a translation,
    not a discard.
    """
    by_system: Dict[int, List[Any]] = {}
    for s in staves:
        by_system.setdefault(s.system_index, []).append(s)
    out: Dict[int, Tuple[int, int]] = {}
    for sys_idx, members in by_system.items():
        for local, s in enumerate(sorted(members, key=lambda x: x.top_y)):
            out[s.staff_index] = (sys_idx, local)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Geometry
# ─────────────────────────────────────────────────────────────────────────────


def gather_geometry(log: Log, pws: Any) -> Dict[int, Tuple[int, int]]:
    """Staff lines, spacing, extent, and the bracket-block reading.

    Returns the page-wide -> system-local staff map, which every later
    emitter needs.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    local = _system_local(pws.staves)

    for st in pws.staves:
        sys_idx, st_idx = local[st.staff_index]
        sub = R.staff(p, sys_idx, st_idx)
        log.observe(sub, Q.STAFF_LINES, list(st.line_ys),
                    reader=READERS.GEOMETRY, frame=FRAME_PAGE,
                    page_staff_index=st.staff_index)
        spacing = _spacing(st)
        if spacing is None:
            log.abstain(sub, Q.STAFF_SPACING, reader=READERS.GEOMETRY,
                        frame=FRAME_PAGE, reason=ABSTAIN.NO_STAFF_GEOMETRY)
        else:
            log.observe(sub, Q.STAFF_SPACING, spacing,
                        reader=READERS.GEOMETRY, frame=FRAME_PAGE)
        log.observe(sub, Q.STAFF_EXTENT, (st.x_start, st.x_end),
                    reader=READERS.GEOMETRY, frame=FRAME_PAGE)
        thickness = getattr(st, "line_thickness_px", None)
        wander = getattr(st, "line_wander_px", None)
        if wander is None:
            # ⚠️ DECLINED, not zero. A staff whose wander was never traced and
            # a staff measured to be perfectly straight are different facts,
            # and `OMR_CELL_LINE_TRACE` exists because the difference matters
            # (a scanned staff tilts 8-17 page px across its width).
            log.abstain(sub, Q.STAFF_SKEW, reader=READERS.GEOMETRY,
                        frame=FRAME_PAGE, reason=ABSTAIN.NO_STAFF_GEOMETRY)
        else:
            log.observe(sub, Q.STAFF_SKEW, wander, reader=READERS.GEOMETRY,
                        frame=FRAME_PAGE, thickness_px=thickness)

    _gather_bracket_blocks(log, pws, local)
    return local


def _spacing(staff: Any) -> Optional[float]:
    ys = list(staff.line_ys)
    if len(ys) < 2:
        return None
    gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    return sum(gaps) / len(gaps) if gaps else None


def _gather_bracket_blocks(log: Log, pws: Any,
                           local: Dict[int, Tuple[int, int]]) -> None:
    """The bracket-block reading, and the three branches that DECLINE it.

    ⚠️ THIS IS THE CANONICAL SENTINEL FAULT AND THE REASON THE RECORD HAS AN
    `Abstention` TYPE AT ALL. `system_grouping._assign_groups` writes
    `group_index = 0` on FOUR branches: `:596` (fewer than 3 staves -- too
    small to partition), `:611` (no column evidence to take a ratio of),
    `:672` (`assign_systems`, fewer than 2 staves), and `:620` (a real
    assignment). On the record "I declined to partition" and "I read one
    family" are byte-identical, and a fifth case -- the gap-heuristic fallback
    path, which never calls `_assign_groups` at all -- leaves the dataclass
    default 0 with no branch having run. That last one is ABSENT rather than
    DECLINED, and the distinction is the whole of `State`.

    ⚠️ MIRROR. The branch conditions are re-derived here from the same staff
    list, not quoted from the reader, because `_assign_groups` returns
    nothing. Every row is stamped `mirror=True`.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_system: Dict[int, List[Any]] = {}
    for st in pws.staves:
        by_system.setdefault(st.system_index, []).append(st)

    for sys_idx, members in sorted(by_system.items()):
        sys_sub = R.system(p, sys_idx)
        if len(members) < 3:
            # mirrors _assign_groups :596
            for st in members:
                _, st_idx = local[st.staff_index]
                log.abstain(R.staff(p, sys_idx, st_idx), Q.BRACKET_BLOCK,
                            reader=READERS.GEOMETRY, frame=FRAME_SYSTEM,
                            reason=ABSTAIN.SYSTEM_TOO_SMALL,
                            mirror=True, n_staves=len(members))
            log.abstain(sys_sub, Q.SYSTEMIC_COLUMN, reader=READERS.GEOMETRY,
                        frame=FRAME_SYSTEM, reason=ABSTAIN.SYSTEM_TOO_SMALL,
                        mirror=True)
            continue

        blocks = {st.staff_index: getattr(st, "group_index", None)
                  for st in members}
        distinct = {b for b in blocks.values() if b is not None}
        if not distinct or (len(distinct) == 1 and 0 in distinct):
            # ⚠️ AMBIGUOUS BY CONSTRUCTION: an all-zero reading is either
            # "one family" (:620 with no split found) or one of the two
            # declining branches. The reader does not say which, so neither
            # do we -- this abstains rather than inventing a reading, and the
            # honest label is that the evidence is not separable.
            for st in members:
                _, st_idx = local[st.staff_index]
                log.abstain(R.staff(p, sys_idx, st_idx), Q.BRACKET_BLOCK,
                            reader=READERS.GEOMETRY, frame=FRAME_SYSTEM,
                            reason=ABSTAIN.NO_COLUMN_EVIDENCE,
                            mirror=True,
                            note="all-zero: reading and refusal are "
                                 "indistinguishable on the old record")
            continue

        for st in members:
            _, st_idx = local[st.staff_index]
            log.observe(R.staff(p, sys_idx, st_idx), Q.BRACKET_BLOCK,
                        blocks[st.staff_index], reader=READERS.GEOMETRY,
                        frame=FRAME_SYSTEM, mirror=True,
                        n_blocks=len(distinct))


def gather_systems(log: Log, pws: Any, used_bridging: bool) -> None:
    """What system grouping SAW, apart from what it concluded."""
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    if not used_bridging:
        # the gap-heuristic fallback: connectivity evidence was unusable
        log.abstain(R.page(p), Q.GAP_BRIDGING, reader=READERS.GEOMETRY,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_INK, mirror=True)
        return
    log.observe(R.page(p), Q.GAP_BRIDGING, True, reader=READERS.GEOMETRY,
                frame=FRAME_PAGE, mirror=True)


def gather_measures(log: Log, pws: Any, cells: Sequence[Any],
                    local: Dict[int, Tuple[int, int]]) -> None:
    """Barline columns and the per-staff measure count."""
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    per_staff: Dict[Tuple[int, int], int] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        per_staff[key] = max(per_staff.get(key, -1), c.measure_index)

    for (sys_idx, st_idx), last in sorted(per_staff.items()):
        log.observe(R.staff(p, sys_idx, st_idx), Q.BARLINE_COLUMN, last + 1,
                    reader=READERS.GEOMETRY, frame=FRAME_PAGE,
                    note="n_cells cut for this staff")

    by_system: Dict[int, set] = {}
    for (sys_idx, st_idx) in per_staff:
        by_system.setdefault(sys_idx, set()).add(st_idx)
    for sys_idx, members in sorted(by_system.items()):
        log.observe(R.system(p, sys_idx), Q.SYSTEM_STAFF_COUNT, len(members),
                    reader=READERS.GEOMETRY, frame=FRAME_SYSTEM)
        for st_idx in sorted(members):
            log.observe(R.staff(p, sys_idx, st_idx), Q.STAFF_ORDINAL, st_idx,
                        reader=READERS.GEOMETRY, frame=FRAME_SYSTEM)


# ─────────────────────────────────────────────────────────────────────────────
# Detection
# ─────────────────────────────────────────────────────────────────────────────

_NOTEHEAD_PREFIX = "notehead"
_CLEF_CLASSES = {"clefG", "clefF", "clefC", "clefUnpitchedPercussion"}


def gather_detections(log: Log, cells: Sequence[Any],
                      local: Dict[int, Tuple[int, int]], *,
                      detector: Any = None, conf_threshold: float = 0.25,
                      imgsz: Optional[int] = None,
                      progress: bool = False) -> Dict[str, List[Any]]:
    """Run the detector cell by cell and emit one row per detection.

    ⚠️ `detector=None` is a supported mode, not a failure: every cell emits
    `Abstention(READER_UNAVAILABLE)` and the pipeline runs end to end with no
    weights. That is what lets the whole staged path be exercised in a unit
    test, and it is also the honest behaviour on a machine with no weights
    file -- which today fails the run.
    """
    found: Dict[str, List[Any]] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sys_idx, st_idx = key
        p = c.page_index
        cell_sub = R.cell(p, sys_idx, st_idx, c.measure_index)
        frame = frame_cell(c.measure_index)

        if detector is None:
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.DETECTOR,
                        frame=frame, reason=ABSTAIN.READER_UNAVAILABLE)
            continue

        dets = detector.detect(c, conf_threshold=conf_threshold, imgsz=imgsz)
        if not dets:
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.DETECTOR,
                        frame=frame, reason=ABSTAIN.NO_DETECTIONS)
            continue

        found[cell_sub.to_key()] = list(dets)
        for gi, d in enumerate(dets):
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, gi)
            # ⚠️⚠️ THE PAGE FRAME IS CARRIED BESIDE THE CANONICAL ONE, AND
            # ITS ABSENCE IS WHY CROSS-STAFF SIMULTANEITY WAS UNREACHABLE.
            # A canonical x is measured inside ONE cell, rescaled so the staff
            # span is constant -- so two staves' canonical x are not the same
            # quantity and comparing them is meaningless. `Q.EVENT` groups
            # glyphs WITHIN a bar and is right to use canonical; a column
            # through a SYSTEM is an instant of music and needs page pixels.
            # Same fault CLAUDE.md records for the dynamics: the hairpin
            # reader works in page pixels per staff and is right by
            # construction, the letters go through per-measure cells and lose
            # 24% to the staff above.
            #
            # ⚠️ DECLINED, never defaulted to the cell frame, exactly as
            # `gather_dynamic_letters` declines: a glyph whose page position
            # is unknown and one measured at page x 1841 are different facts,
            # and only the second may reach a cross-staff consumer.
            page_box = _page_box(c, d)
            box_detail: Dict[str, Any] = {"category": d.category}
            if page_box is None:
                box_detail["frame_note"] = (
                    "no page box: cell has no bbox_page_px/upscale_factor")
            else:
                px0, py0, px1, py1 = page_box
                box_detail.update(bbox_page_px=[px0, py0, px1, py1],
                                  x_center_page=(px0 + px1) / 2.0,
                                  y_center_page=(py0 + py1) / 2.0)
            log.observe(g, Q.GLYPH_BOX,
                        (d.smufl_name, d.x_canonical, d.y_canonical,
                         d.width_canonical, d.height_canonical),
                        reader=READERS.DETECTOR, frame=frame,
                        score=float(d.confidence), **box_detail)
            # ⚠️ Emitted SEPARATELY from the box, deliberately. `export.py`
            # contains exactly one occurrence of the word `confidence` and it
            # is a comment: the exporter treats a notehead detected at 0.26
            # and one at 0.98 as equally true. Confidence being its own row
            # means a consumer has to decline it explicitly rather than never
            # see it.
            log.observe(g, Q.GLYPH_CONF, float(d.confidence),
                        reader=READERS.DETECTOR, frame=frame,
                        score=float(d.confidence))
            if d.smufl_name.startswith(_NOTEHEAD_PREFIX):
                log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name,
                            reader=READERS.DETECTOR, frame=frame,
                            score=float(d.confidence))
        if progress:
            print(f"  gather detections {cell_sub.to_key()}: {len(dets)}")
    return found


def gather_notehead_positions(log: Log, cells: Sequence[Any],
                              local: Dict[int, Tuple[int, int]],
                              detections: Dict[str, List[Any]]) -> None:
    """The notehead's fractional STAFF POSITION -- clef-free, and kept.

    ⚠️ THIS IS THE THESIS OF THE WHOLE ARCHITECTURE IN ONE FUNCTION.
    `pitch_resolver.py:180` computes `pos_float = (y_center - top_y) /
    half_step` and `:181` immediately rounds it away, and the clef is not in
    either expression -- it enters at `:183`. The POSITION is a measurement
    (geometry against this staff's own lines); the PITCH is an interpretation
    (it required a clef). Today we keep the interpretation and throw away the
    measurement, so every later decision that would like to reconsider the
    clef has nothing clef-free to reconsider it with.

    The fraction is kept too: a residual near 0.5 says "this note sat exactly
    between two positions", which on a warped scan is the population
    `OMR_CELL_LINE_TRACE` exists for.
    """
    by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        by_key[(c.page_index, key[0], key[1], c.measure_index)] = c

    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        grid = _cell_grid(c)
        if grid is None:
            log.abstain(sub, Q.NOTEHEAD_STAFF_POSITION,
                        reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        top_y, half_step = grid
        for gi, d in enumerate(dets):
            if not d.smufl_name.startswith(_NOTEHEAD_PREFIX):
                continue
            pos_float = (d.y_center - top_y) / half_step
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            log.observe(g, Q.NOTEHEAD_STAFF_POSITION, pos_float,
                        reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                        residual=abs(pos_float - round(pos_float)),
                        rounded=int(round(pos_float)))


# ─────────────────────────────────────────────────────────────────────────────
# Cross-staff ownership evidence
#
# ⚠️ THIS IS THE EVIDENCE THE EXISTING PIPELINE DECIDES ON AND DOES NOT WRITE
# DOWN. `OMR_CONTEST_DUMP` records both confidences and the deciding tier, and
# NOT the band distances or the ladder rung counts -- i.e. the one quantity
# documented as a coin flip is the one quantity not on the record. And it is
# off by default, so today it records nothing at all.
# ─────────────────────────────────────────────────────────────────────────────

_LEDGER_CLASS = "ledgerLine"

#: Two boxes are the same ink if they overlap this much. (A-OWN-3)
CONTEST_IOU = 0.5

#: Expected ledger rungs between a notehead and its staff.
#: ⚠️ `+ 0.25` before truncation is NOT a fudge: a note sitting ON the first
#: ledger measures ~0.994 spacings, and plain truncation read that as needing
#: NO rung -- so the same note needed its ledger in one bar and not the next,
#: one pixel apart.
LEDGER_ROUND_UP = 0.25


def _page_box(cell: Any, det: Any) -> Optional[Tuple[float, float, float, float]]:
    """Canonical cell coordinates -> page pixels."""
    bbox = getattr(cell, "bbox_page_px", None)
    up = getattr(cell, "upscale_factor", None)
    if not bbox or not up:
        return None
    x0, y0 = bbox[0], bbox[1]
    return (x0 + det.x_canonical / up, y0 + det.y_canonical / up,
            x0 + (det.x_canonical + det.width_canonical) / up,
            y0 + (det.y_canonical + det.height_canonical) / up)


def _iou(a, b) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _band_distance_spaces(y: float, line_ys: Sequence[float],
                          spacing: float) -> float:
    """Distance from `y` to the staff's five-line band, in staff spaces.

    Zero inside the band. ⚠️ This is the quantity measured to be very nearly a
    coin flip -- the misattributed hairpins sat 5-62 px nearer the wrong staff
    against 25 px the other way for the one kept correctly -- so it is
    gathered so a decision can WEIGH it, never so a decision can trust it.
    """
    top, bottom = min(line_ys), max(line_ys)
    if top <= y <= bottom:
        return 0.0
    gap = (top - y) if y < top else (y - bottom)
    return gap / spacing if spacing else gap


def gather_ownership_evidence(log: Log, pws: Any, cells: Sequence[Any],
                              local: Dict[int, Tuple[int, int]],
                              detections: Dict[str, List[Any]]) -> None:
    """Every cross-staff contest, with the evidence for BOTH candidates.

    A measure cell is the staff plus four to six staff spaces of air, so on a
    conductor's page the same ink lands in two staves' cells and is detected
    twice. Today `_dedupe_cross_staff_detections` resolves 94.1% of 4,521 such
    contests BY DISTANCE, because its strongest tier needs an instrument that
    arrives 309 lines later -- and on a scan that tier is vacuous anyway.

    This writes the contest down instead of deciding it.
    """
    geom: Dict[str, Tuple[List[float], float]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is None:
            continue
        sub = R.staff(pws.page.page_index if hasattr(pws.page, "page_index")
                      else 0, key[0], key[1])
        sp = _spacing(st)
        if sp:
            geom[sub.to_key()] = ([float(y) for y in st.line_ys], float(sp))

    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c

    # every detection in page space, with its glyph subject
    placed: List[Tuple[Subject, Tuple[float, float, float, float], Any]] = []
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for gi, d in enumerate(dets):
            box = _page_box(c, d)
            if box is None:
                continue
            placed.append(
                (R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi), box, d))

    if not placed:
        return

    # contests: same class, different STAFF, same system, overlapping ink
    by_system: Dict[Tuple[int, int], List[int]] = {}
    for i, (g, _b, _d) in enumerate(placed):
        by_system.setdefault((g.page, g.system), []).append(i)

    contests: Dict[int, set] = {}
    for members in by_system.values():
        for ai in range(len(members)):
            i = members[ai]
            for j in members[ai + 1:]:
                gi, bi, di = placed[i]
                gj, bj, dj = placed[j]
                if gi.staff == gj.staff:
                    continue
                if di.smufl_name != dj.smufl_name:
                    continue
                if _iou(bi, bj) < CONTEST_IOU:
                    continue
                contests.setdefault(i, set()).add(gj.at(R.Kind.STAFF).to_key())
                contests.setdefault(j, set()).add(gi.at(R.Kind.STAFF).to_key())

    ledgers = _ledger_index(placed)

    for i, others in sorted(contests.items()):
        g, box, det = placed[i]
        own = g.at(R.Kind.STAFF).to_key()
        y_center = (box[1] + box[3]) / 2.0
        for cand_key in sorted({own} | others):
            lines_sp = geom.get(cand_key)
            if lines_sp is None:
                log.abstain(g, Q.GLYPH_BAND_DISTANCE, reader=READERS.GEOMETRY,
                            frame=FRAME_PAGE, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            candidate=cand_key)
                continue
            line_ys, spacing = lines_sp
            # ⚠️ The staff POSITION this glyph would have IF this candidate
            # owned it -- clef-free, measured in the candidate's own frame.
            # Emitted here so the range veto never has to reach across to the
            # twin copy's row, and never has to touch a resolved pitch:
            # today the veto reads `det["pitch"]` (transcribe.py:3153-3154),
            # an interpretation, which is not a cycle yet but becomes one the
            # moment a clef adjudicator reads ownership.
            half = spacing / 2.0 if spacing else 1.0
            log.observe(g, Q.GLYPH_BAND_DISTANCE,
                        _band_distance_spaces(y_center, line_ys, spacing),
                        reader=READERS.GEOMETRY, frame=FRAME_PAGE,
                        candidate=cand_key, own=(cand_key == own),
                        position_in_candidate=(y_center - min(line_ys)) / half)
            if det.smufl_name.startswith(_NOTEHEAD_PREFIX):
                _observe_ladder(log, g, box, cand_key, line_ys, spacing,
                                ledgers)


def _ledger_index(placed) -> Dict[Tuple[int, int], List[Tuple[float, float, float]]]:
    """Ledger-line detections per system, as (x0, x1, y_centre) in page px."""
    out: Dict[Tuple[int, int], List[Tuple[float, float, float]]] = {}
    for g, box, det in placed:
        if det.smufl_name != _LEDGER_CLASS:
            continue
        out.setdefault((g.page, g.system), []).append(
            (box[0], box[2], (box[1] + box[3]) / 2.0))
    return out


def _observe_ladder(log: Log, g: Subject, box, cand_key: str,
                    line_ys: Sequence[float], spacing: float, ledgers) -> None:
    """⚠️ COMPLETENESS ONLY, NEVER COUNT.

    An unbroken run of rungs joins a note to its staff and outranks anything
    broken -- but TWO BROKEN LADDERS ARE NOT EVIDENCE EITHER WAY, because a
    found rung can belong to the other staff's note exactly as a gap can. On
    the Beethoven bassoon pair the ghost's single rung WAS the real C4's own
    ledger, and counting rungs beat the real note.
    """
    y = (box[1] + box[3]) / 2.0
    top, bottom = min(line_ys), max(line_ys)
    if top <= y <= bottom:
        return                       # inside the staff: no ladder to have
    gap = (top - y) if y < top else (y - bottom)
    expected = int(gap / spacing + LEDGER_ROUND_UP)
    if expected <= 0:
        return
    rungs = ledgers.get((g.page, g.system), [])
    x0, x1 = box[0], box[2]
    found = 0
    for k in range(1, expected + 1):
        want = (top - k * spacing) if y < top else (bottom + k * spacing)
        if any(rx0 <= x1 and rx1 >= x0 and abs(ry - want) <= spacing * 0.5
               for rx0, rx1, ry in rungs):
            found += 1
    log.observe(g, Q.GLYPH_LADDER, found == expected,
                reader=READERS.DETECTOR, frame=FRAME_PAGE,
                candidate=cand_key, expected=expected, found=found)


# ─────────────────────────────────────────────────────────────────────────────
# Rhythm marks -- MEASUREMENTS. The duration they compose into is a VERDICT.
# ─────────────────────────────────────────────────────────────────────────────

_FLAG_PREFIX = "flag"
_DOT_CLASS = "augmentationDot"
#: ⚠️ DSv2's `tuplet3` / `fingering3` distinction is POSITIONAL -- a `3` over a
#: beamed group vs a `3` beside a notehead -- and the detector reproduces it
#: badly on orchestral pages: 33 `fingering3` against 16 `tuplet3` over twelve
#: works, and ALL 33 sit in a cell holding a real triplet. Both are read; the
#: positional gate in the adjudicator is what keeps that safe.
_TUPLET_CLASSES = ("tuplet3", "fingering3", "tupletBracket", "tupleBracket")


def gather_rhythm_marks(log: Log, cells: Sequence[Any],
                        local: Dict[int, Tuple[int, int]],
                        detections: Dict[str, List[Any]]) -> None:
    """Flags, augmentation dots, tuplet markers -- per glyph, as measurements.

    ⚠️ WHAT IS NOT HERE: `Q.BEAM_STROKE` and `Q.STEM`. Those come from the
    CLASSICAL CV rung (`line_detection`), not the detector, because YOLO
    bounding boxes are structurally bad at thin lines -- that is why Phase 4f
    moved them. They are gathered by `gather_cv_lines` and are a DECLARED STUB
    until that rung is wired.

    ⚠️ AND A DOT IS NOT MEASURED AGAINST ITS OWN BOX. The gate that decides
    which notehead a dot belongs to is expressed in STAFF SPACES, asymmetric
    (0.75 above, 0.25 below), because a dot goes above its note or level with
    it and NEVER under -- a symmetric window ties on Brahms's double stops and
    double-dots the upper note while the lower loses its dot. That arithmetic
    is the adjudicator's; this only records where the ink is.
    """
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        frame = frame_cell(sub.cell)
        for gi, d in enumerate(dets):
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            name = d.smufl_name
            if name.startswith(_FLAG_PREFIX):
                log.observe(g, Q.FLAG, name, reader=READERS.DETECTOR,
                            frame=frame, score=float(d.confidence),
                            y_center=d.y_center, x_center=d.x_center)
            elif name == _DOT_CLASS:
                log.observe(g, Q.AUG_DOT, (d.x_center, d.y_center),
                            reader=READERS.DETECTOR, frame=frame,
                            score=float(d.confidence))
            elif name in _TUPLET_CLASSES:
                log.observe(g, Q.TUPLET_MARKER, name,
                            reader=READERS.DETECTOR, frame=frame,
                            score=float(d.confidence),
                            x0=d.x_canonical,
                            x1=d.x_canonical + d.width_canonical,
                            x_center=d.x_center,
                            is_bracket=name.lower().endswith("bracket"))


#: Which detected class belongs to which notation family.
#:
#: ⚠️ ROUTED BY CLASS, NOT BY THE DETECTOR'S `category`, and the hairpins are
#: why. `dynamicDiminuendoHairpin` carries category `dynamic` and is a WEDGE,
#: not a letter -- so a category-keyed router would spell it into a dynamic
#: word. Articulations are the mirror: all ten `artic*` classes carry category
#: `ornament`, which they share with `ornamentTrill`, `fermataAbove` and
#: `arpeggiato`, so the category cannot separate them either.
_ARC_CLASSES = ("tie", "slur")
_ARTIC_PREFIX = "artic"
_REST_PREFIX = "rest"


def _artic_side(name: str) -> Optional[str]:
    """The side an articulation's own class NAMES, or None where it does not.

    ⚠️ Not every class states one. `class_aliases.COARSER_THAN_CANONICAL`
    records `articulationAccent` / `Staccato` / `Tenuto` as coarser than the
    canonical spelling precisely because they carry no side, and the legacy
    attach pass requires the geometry to AGREE with the side when there is
    one. So this returns None rather than guessing, and the adjudicator gets a
    row that says "no side declared" instead of a wrong one.
    """
    if name.endswith("Above"):
        return "above"
    if name.endswith("Below"):
        return "below"
    return None


def gather_glyph_families(log: Log, detections: Dict[str, List[Any]]) -> None:
    """Rests, arcs and articulation marks.

    ⚠️ EVERY ONE OF THESE WAS DETECTED AND READ BY NOTHING until 2026-09-09.
    Measured over four real conductor's pages, the ink that reached
    `GLYPH_BOX` and no typed row: **838 rests, 755 ties, 291 slurs, 542
    dynamic letters, 40 articulation marks, 1 hairpin** -- 2,467 glyphs. Four
    of the five quantities existed in `Q` and in a stub's `wants` and were
    OBSERVED BY NOTHING, so writing those adjudicators would have produced
    nothing; the fifth, `Q.REST`, did not exist at all.

    ⚠️ THIS FUNCTION DECIDES NOTHING, and the split is the point. A rest's
    DURATION, an arc's OWNER and KIND, a hairpin's ANCHORS, the spelling of
    `f`+`f` into `ff` -- each is an interpretation with its own evidence and
    its own right to abstain. What belongs here is only "this ink is of this
    kind, and here is where it is".

    ⚠️ The extents are recorded because the consumers need them and the box
    alone is not enough: an arc is PAIRED across a barline by its ends, a
    hairpin is anchored by its edges (its ink does not overlap the notes it
    binds at all -- 0 of 4 on Mahler), and `f`+`f` becomes `ff` by x-adjacency.
    """
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        frame = frame_cell(sub.cell)
        for gi, d in enumerate(dets):
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            name = d.smufl_name
            box = dict(
                x0=d.x_canonical, x1=d.x_canonical + d.width_canonical,
                y0=d.y_canonical, y1=d.y_canonical + d.height_canonical,
                x_center=d.x_center, y_center=d.y_center,
            )
            common = dict(reader=READERS.DETECTOR, frame=frame,
                          score=float(d.confidence))

            # ⚠️ WEDGES AND DYNAMIC LETTERS ARE NOT GATHERED HERE, and the
            # omission is deliberate. `gather_wedge_boxes` and
            # `gather_dynamic_letters` own `Q.WEDGE_BOX` and
            # `Q.DYNAMIC_LETTER`: they read the same ink in the STAFF's own
            # frame (the band offset a per-cell frame cannot express) and the
            # wedge rung also reads the CV hairpins. Emitting them here too
            # would put two rows from ONE reader on one glyph, which is the
            # "two rows from one reader are ONE signal" fault made by accident.
            if name in _ARC_CLASSES:
                log.observe(g, Q.ARC_BOX, name, **common, **box)
            elif name.startswith(_ARTIC_PREFIX):
                log.observe(g, Q.ARTICULATION_MARK, name, **common, **box,
                            side=_artic_side(name))
            elif name.lower().startswith(_REST_PREFIX):
                log.observe(g, Q.REST, name, **common, **box)


# ─────────────────────────────────────────────────────────────────────────────
# Dynamics — the letters and the wedges, gathered in ONE frame on purpose
# ─────────────────────────────────────────────────────────────────────────────

#: The six letter glyphs a dynamic is spelled from. ⚠️ CANONICAL spellings
#: only: the 208-class space carries `dynamicLetterF` at id 192 as well as
#: `dynamicF` at its fine id, and `class_aliases` renames the coarse block at
#: the one place the model's `names` are read -- so by the time a detection
#: reaches here it is spelled the fine way. Listing both would not be harmless
#: duplication, it would hide a regression in that renaming.
_DYNAMIC_LETTER_CLASSES = frozenset({
    "dynamicF", "dynamicP", "dynamicM", "dynamicS", "dynamicZ", "dynamicR",
})

#: The wedge classes the DETECTOR can fire, and the kind each names.
_WEDGE_CLASSES = {
    "dynamicCrescendoHairpin": "crescendo",
    "dynamicDiminuendoHairpin": "diminuendo",
}

#: ⚠️ Glyph indices for wedges the CV rung read, offset far past any detector
#: index so the two readers can never collide in one cell's key space. A
#: collision here would not raise -- it would silently merge a CV reading and
#: a detector reading into one subject, which is precisely the "two rows from
#: one reader are ONE signal" mistake, made by accident.
_CV_GLYPH_BASE = 100_000


def _band_offset_spaces(y: float, bottom_line: float,
                        spacing: float) -> Optional[float]:
    """Staff spaces BELOW this staff's own bottom line. Negative means above.

    ⚠️ THE FRAME IS THE POINT OF THIS FUNCTION. A dynamic letter reaches the
    exporter today through a per-MEASURE cell whose padding is 4 to 6 staff
    spaces depending on how crowded the staff's neighbours are
    (`measure_extractor.PAD_*_STAFF_LINES` grows where the next staff is more
    than 6 spaces off). Measuring a letter's height against that frame moves
    the number when the page's crowding changes and the ink does not. Against
    the staff's own bottom line and its own spacing, it does not.

    This is also the frame `hairpin_detection` already works in
    (`BAND_TOP_SPACES = 0.3` / `BAND_BOTTOM_SPACES = 6.0` below the bottom
    line), which is why the letters and the wedges become comparable at all:
    they are two readings of ONE row of the page, and only the wedge reader
    has ever measured it that way. The dynamics-band study measured the letter
    population at +0.0 to +5.6 spaces -- the same band, arrived at
    independently.
    """
    if not spacing:
        return None
    return (y - bottom_line) / spacing


def _staff_bands(pws: Any, local: Dict[int, Tuple[int, int]]
                 ) -> Dict[str, Tuple[float, float, float]]:
    """Per staff subject key -> (top_line, bottom_line, spacing), page px."""
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    out: Dict[str, Tuple[float, float, float]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is None:
            continue
        sp = _spacing(st)
        ys = [float(y) for y in st.line_ys]
        if not sp or len(ys) < 2:
            continue
        out[R.staff(p, key[0], key[1]).to_key()] = (min(ys), max(ys), float(sp))
    return out


def gather_dynamic_letters(log: Log, pws: Any, cells: Sequence[Any],
                           local: Dict[int, Tuple[int, int]],
                           detections: Dict[str, List[Any]]) -> None:
    """One row per dynamic LETTER glyph, in page pixels, before any spelling.

    ⚠️ A LETTER IS NOT A DYNAMIC, and keeping them apart is the whole reason
    this is a separate quantity from `Q.DYNAMIC`. The detector emits one glyph
    per letter -- `ff` arrives as two `dynamicF` -- so joining them into a word
    is an INTERPRETATION over these rows and belongs to `adjudicate_dynamic`.
    Emitting a spelled word here would put the arbitration in the gathering
    phase, the fault the whole split exists to remove.

    ⚠️ AND THE PLACEMENT EVIDENCE IS NOT GATHERED HERE EITHER. Which staff a
    contested letter belongs to is `Q.GLYPH_OWNER`'s question, and
    `gather_ownership_evidence` already writes the contest down for EVERY
    class, letters included -- it needs no per-family code. What this adds is
    the band offset in the staff's OWN frame, which the ownership rows do not
    carry and which is what makes a letter comparable to a wedge.

    ⚠️ NOTHING IS FILTERED BY BAND. A band GATE was measured and REFUSED: it
    under-emits on both families (0.63 engraved, 0.59 scanned) because a mark
    whose only surviving detection sits in the neighbour's cell is DELETED
    rather than moved. The offset is recorded so a decision can weigh it.

    ⚠️ EVERY CELL GETS A ROW, including one with no dynamic letter in it, and
    that is LOAD-BEARING rather than tidy. A decision's subjects come from the
    rows in the log, so a staff carrying no letter of its own would have no
    `Q.DYNAMIC` subject -- and a letter that ownership moves ONTO it would be
    silently lost. `test_staged_dynamics` pins exactly that.
    """
    bands = _staff_bands(pws, local)
    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c

    seen_cells = set()
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        seen_cells.add(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        frame = frame_cell(sub.cell)
        band = bands.get(sub.at(R.Kind.STAFF).to_key())
        n = 0
        for gi, d in enumerate(dets):
            if d.smufl_name not in _DYNAMIC_LETTER_CLASSES:
                continue
            n += 1
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            box = _page_box(c, d) if c is not None else None
            detail: Dict[str, Any] = {
                "letter": d.smufl_name.replace("dynamic", "").lower(),
                "cell_frame": frame,
            }
            if box is None:
                # ⚠️ DECLINED, not defaulted to the cell frame. A letter whose
                # page position is unknown and a letter measured at +2.1
                # spaces are different facts, and the second is the only one a
                # band consumer may read.
                detail["frame_note"] = "no page box: cell has no bbox/upscale"
                log.observe(g, Q.DYNAMIC_LETTER, d.smufl_name,
                            reader=READERS.DETECTOR, frame=frame,
                            score=float(d.confidence), **detail)
                continue
            x0, y0, x1, y1 = box
            detail.update(bbox_page_px=[x0, y0, x1, y1],
                          x_center_page=(x0 + x1) / 2.0,
                          y_center_page=(y0 + y1) / 2.0)
            if band is not None:
                top, bottom, spacing = band
                detail.update(
                    staff_bottom_line_page=bottom,
                    staff_spacing_px=spacing,
                    band_offset_spaces=_band_offset_spaces(
                        (y0 + y1) / 2.0, bottom, spacing),
                    # the same window `hairpin_detection` searches, so a
                    # letter and a wedge can be said to share a row
                    in_hairpin_band=_in_hairpin_band((y0 + y1) / 2.0,
                                                     bottom, spacing))
            log.observe(g, Q.DYNAMIC_LETTER, d.smufl_name,
                        reader=READERS.DETECTOR, frame=FRAME_PAGE,
                        score=float(d.confidence), **detail)
        if n == 0:
            log.abstain(sub, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR,
                        frame=frame, reason=ABSTAIN.NO_INK)

    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        if sub.to_key() not in seen_cells:
            log.abstain(sub, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR,
                        frame=frame_cell(c.measure_index),
                        reason=ABSTAIN.NO_DETECTIONS)


def _in_hairpin_band(y: float, bottom_line: float, spacing: float) -> bool:
    try:
        from ..hairpin_detection import BAND_TOP_SPACES, BAND_BOTTOM_SPACES
    except Exception:                                         # noqa: BLE001
        return False
    off = (y - bottom_line) / spacing if spacing else 0.0
    return BAND_TOP_SPACES <= off <= BAND_BOTTOM_SPACES


def gather_wedge_boxes(log: Log, pws: Any, cells: Sequence[Any],
                       local: Dict[int, Tuple[int, int]],
                       detections: Dict[str, List[Any]]) -> None:
    """Hairpin ink, from BOTH readers, in page pixels per staff.

    ⚠️ TWO READERS, AND THEY ARE NOT INTERCHANGEABLE. The detector fires on a
    hairpin ~never on a scan -- 1 across eleven scanned pages against a truth
    of 198 `<wedge>`, and the symbol ledger reads `hairpin matched_exact = 0`
    with ZERO spurious beside it over the 20-row gate, which is silence rather
    than error. `hairpin_detection` reads 96 across the same 20 rows. Both are
    emitted, tagged by reader, because a wedge the detector DID see is a
    genuinely independent second reading and the whole point of the log is
    that a consumer decides which to believe.

    ⚠️ THE CV RUNG IS GATHERED WHATEVER `OMR_CV_HAIRPINS` SAYS. That flag
    guards what the legacy EXPORTER does with a hairpin; this is the
    observation phase, whose job is to write down what the page shows. A
    reader silenced by an export-side flag would make the log a record of a
    configuration rather than of the page -- and the flag's own docstring says
    its cost is under-attributed, which is a question only a record can
    settle.

    ⚠️ AND IT NEEDS THE RASTER, so it abstains loudly where there is none.
    `read_hairpins_for_page` takes `PageImage.binary` (0 = ink) and asserts the
    polarity rather than trusting it, because the wrong polarity does not
    crash -- it searches the paper and reports a clean zero.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    bands = _staff_bands(pws, local)

    # ── reader 1: the detector ───────────────────────────────────────────────
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        for gi, d in enumerate(dets):
            kind = _WEDGE_CLASSES.get(d.smufl_name)
            if kind is None:
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            log.observe(g, Q.WEDGE_BOX, kind, reader=READERS.DETECTOR,
                        frame=frame_cell(sub.cell),
                        score=float(d.confidence),
                        detector_class=d.smufl_name)

    # ── reader 2: classical CV over the whole page ───────────────────────────
    binary = getattr(getattr(pws, "page", None), "binary", None)
    staff_rows = []
    by_page_index = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        band = bands.get(R.staff(p, key[0], key[1]).to_key()) if key else None
        if key is None or band is None:
            continue
        top, bottom, spacing = band
        staff_rows.append({"index": st.staff_index, "top": top,
                           "bottom": bottom, "spacing": spacing})
        by_page_index[st.staff_index] = (key, band)

    if binary is None or not staff_rows:
        for st_key in sorted(bands):
            log.abstain(Subject.from_key(st_key), Q.WEDGE_BOX,
                        reader=READERS.CV_HAIRPINS, frame=FRAME_PAGE,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        note=("no page raster" if binary is None
                              else "no staff geometry"))
        return

    try:
        import numpy as np
        from ..hairpin_detection import (blank_point_detections,
                                         detect_hairpins)
        page_ink = (binary == 0).astype(np.uint8) * 255
        spacings = sorted(s["spacing"] for s in staff_rows)
        # ⚠️ `blank_point_detections` takes (x, y, W, H) while `_page_box`
        # returns CORNERS. Both conventions live in this repo and confusing
        # them does not raise -- it blanks the wrong rectangle. Converted here,
        # once, explicitly.
        boxes = []
        cell_by_key = {}
        for c in cells:
            key = local.get(c.staff_index)
            if key is not None:
                cell_by_key[(c.page_index, key[0], key[1],
                             c.measure_index)] = c
        for cell_key, dets in detections.items():
            sub = Subject.from_key(cell_key)
            c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
            if c is None:
                continue
            for d in dets:
                box = _page_box(c, d)
                if box is None:
                    continue
                x0, y0, x1, y1 = box
                boxes.append((x0, y0, x1 - x0, y1 - y0, d.smufl_name))
        blanked = blank_point_detections(
            page_ink, boxes, spacings[len(spacings) // 2])
        found = detect_hairpins(page_ink, staff_rows, blanked)
    except Exception as exc:                                  # noqa: BLE001
        for st_key in sorted(bands):
            log.abstain(Subject.from_key(st_key), Q.WEDGE_BOX,
                        reader=READERS.CV_HAIRPINS, frame=FRAME_PAGE,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=type(exc).__name__, note=str(exc)[:200])
        return

    per_staff: Dict[int, int] = {}
    for h in found:
        entry = by_page_index.get(h.staff_index)
        if entry is None:
            continue
        (sys_idx, st_idx), (_top, bottom, spacing) = entry
        n = per_staff.get(h.staff_index, 0)
        per_staff[h.staff_index] = n + 1
        # ⚠️ Attributed to the staff whose BAND it was found in, which is right
        # BY CONSTRUCTION here: this reader searches one staff's band at a
        # time in page pixels, so it never inherits the per-measure cell's
        # padding and never needs the distance arbitration the letters do.
        g = R.glyph(p, sys_idx, st_idx, _cell_of(cells, local, h),
                    _CV_GLYPH_BASE + n)
        log.observe(g, Q.WEDGE_BOX, h.kind, reader=READERS.CV_HAIRPINS,
                    frame=FRAME_PAGE,
                    bbox_page_px=[float(h.x), float(h.y),
                                  float(h.x + h.width), float(h.y + h.height)],
                    x_center_page=float(h.x + h.width / 2.0),
                    y_center_page=float(h.y + h.height / 2.0),
                    staff_bottom_line_page=bottom,
                    staff_spacing_px=spacing,
                    band_offset_spaces=_band_offset_spaces(
                        float(h.y + h.height / 2.0), bottom, spacing),
                    open_spaces=float(h.open_spaces),
                    outline_rms_spaces=float(h.outline_rms_spaces),
                    page_staff_index=int(h.staff_index))

    for page_st, (key, _band) in sorted(by_page_index.items()):
        if per_staff.get(page_st):
            continue
        # ⚠️ A staff the reader RAN over and found nothing under is a
        # measurement, not an absence -- it is the `0 spurious` half of the
        # ledger's reading, and a consumer that cannot tell it from "the rung
        # never ran" cannot tell silence from blindness.
        log.abstain(R.staff(p, key[0], key[1]), Q.WEDGE_BOX,
                    reader=READERS.CV_HAIRPINS, frame=FRAME_PAGE,
                    reason=ABSTAIN.NO_INK, page_staff_index=int(page_st))


def _cell_of(cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
             h: Any) -> int:
    """Which measure cell of its own staff a CV hairpin's centre falls in.

    ⚠️ Falls back to the staff's FIRST cell rather than refusing, and says so
    in the row: the wedge's page coordinates are the load-bearing fact and the
    cell is an addressing convenience. Refusing here would drop a real reading
    over a bookkeeping question.
    """
    x = h.x + h.width / 2.0
    best, best_dx = None, None
    for c in cells:
        if c.staff_index != h.staff_index:
            continue
        box = getattr(c, "bbox_page_px", None)
        if not box:
            continue
        if box[0] <= x <= box[2]:
            return int(c.measure_index)
        dx = min(abs(x - box[0]), abs(x - box[2]))
        if best_dx is None or dx < best_dx:
            best, best_dx = int(c.measure_index), dx
    return best if best is not None else 0


def gather_cv_lines(log: Log, cells: Sequence[Any],
                    local: Dict[int, Tuple[int, int]]) -> None:
    """Stems and beams from the classical-CV rung, on the ERASED image.

    ⚠️ THE TWO READERS SEE DIFFERENT IMAGES OF THE SAME PAGE, DELIBERATELY.
    `line_detection` prefers `cell.image_no_staff`; the detector reads
    `cell.image`. Erasing for the detector costs 7-13 pooled reading points
    and MANUFACTURES beam confusion -- YOLO beams 46 -> 105 at precision
    0.783 -> 0.343, firing on staff-line residue. Every row here records WHICH
    image it came from, so a later reader can never assume they agree.

    ⚠️ AND THE FALLBACK IS SILENT, so it is checked. `line_detection` degrades
    to `cell.image` when the erased variant is missing rather than refusing,
    which would make a whole-rung failure look like a thin page.

    ⚠️ THESE ARE STROKES, NOT LEVELS. How many beams a NOTE carries is an
    interpretation over these rows and belongs to `adjudicate_duration` --
    emitting a level here would put the arbitration in the gathering phase,
    which is the fault the whole split exists to remove.
    """
    try:
        from ..line_detection import detect_lines
    except Exception:                                         # noqa: BLE001
        _stub_cv_lines(log, cells, local, "line_detection unavailable")
        return

    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        frame = frame_cell(c.measure_index)
        erased = getattr(c, "image_no_staff", None) is not None
        try:
            found = detect_lines(c)
        except Exception as exc:                              # noqa: BLE001
            for quantity in (Q.BEAM_STROKE, Q.STEM):
                log.abstain(sub, quantity, reader=READERS.CV_LINES,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            error=type(exc).__name__)
            continue

        for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, "beams")):
            rows = found.get(kind) or []
            if not rows:
                log.abstain(sub, quantity, reader=READERS.CV_LINES,
                            frame=frame, reason=ABSTAIN.NO_INK,
                            image="no_staff" if erased else "original",
                            staff_lines_erased=erased)
                continue
            for d in rows:
                log.observe(sub, quantity,
                            (d.x_canonical, d.y_canonical,
                             d.width_canonical, d.height_canonical),
                            reader=READERS.CV_LINES, frame=frame,
                            x0=d.x_canonical,
                            x1=d.x_canonical + d.width_canonical,
                            y_center=d.y_center,
                            image="no_staff" if erased else "original",
                            staff_lines_erased=erased)


def _stub_cv_lines(log: Log, cells, local, note: str) -> None:
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        for quantity in (Q.BEAM_STROKE, Q.STEM):
            log.abstain(sub, quantity, reader=READERS.CV_LINES,
                        frame=frame_cell(c.measure_index),
                        reason=ABSTAIN.NOT_IMPLEMENTED, note=note)


def gather_detector_beams(log: Log, detections: Dict[str, List[Any]]) -> None:
    """The DETECTOR's beam boxes, kept as rows beside the CV strokes.

    ⚠️ A YOLO BEAM BOX BOUNDS THE STACK, NOT A STROKE. A box spanning two
    strokes contributes a centre in the GAP between them, and the run then has
    no gap wide enough to cluster: on Brahms's Violin 2 the CV strokes sit 60px
    apart against a 35px tolerance -- two levels -- and the YOLO box adds a
    third centre between them, so three sixteenths read as three eighths.

    ⚠️ SO THE ARBITRATION IS THE ADJUDICATOR'S, NOT A FILTER HERE. Both
    readers emit; `adjudicate_duration` keeps a YOLO beam only where NO CV
    beam overlaps its x-range. Unioning them was worth pooled 0.1917 -> 0.1861
    to fix; REPLACING outright scores five edits BETTER and is REFUSED,
    because it throws real beams away and takes the notes that lose every beam
    they had from 4 to 7.
    """
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        for d in dets:
            if d.smufl_name != "beam":
                continue
            log.observe(sub, Q.BEAM_STROKE,
                        (d.x_canonical, d.y_canonical,
                         d.width_canonical, d.height_canonical),
                        reader=READERS.DETECTOR, frame=frame_cell(sub.cell),
                        score=float(d.confidence),
                        x0=d.x_canonical,
                        x1=d.x_canonical + d.width_canonical,
                        y_center=d.y_center, image="original",
                        staff_lines_erased=False)


# ─────────────────────────────────────────────────────────────────────────────
# The clef -- every reader, and BOTH crops
# ─────────────────────────────────────────────────────────────────────────────


def _cell_grid(cell: Any) -> Optional[Tuple[float, float]]:
    """`(top_y, half_step)` for a cell, in its own canonical frame.

    ⚠️ ONE SPELLING, USED TWICE. `gather_notehead_positions` computed this
    inline and threw it away, so the only thing on the record in cell
    coordinates was a notehead's position -- and a consumer asking "where is
    this OTHER glyph, in staff steps" had nothing to ask with. That is the
    pattern this architecture exists to kill, one layer down from where it was
    already caught (`pitch_resolver` rounding `pos_float` away).
    """
    lines = list(getattr(cell, "staff_line_ys_canonical", None) or [])
    if len(lines) < 2:
        return None
    gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    half_step = (sum(gaps) / len(gaps)) / 2.0
    if half_step <= 0:
        return None
    return float(lines[0]), float(half_step)


def gather_clef(log: Log, cells: Sequence[Any],
                local: Dict[int, Tuple[int, int]],
                detections: Dict[str, List[Any]]) -> None:
    """The detector's clef opinion, per staff, from the staff's first cell.

    ⚠️ ONE ROW PER ACTUAL INFERENCE. The design said the header pre-pass and
    the measure-pass argmax "share a basis, so tally counts them once". The
    correct build is simpler: THEY ARE THE SAME CALL ON THE SAME LIST OBJECT
    -- measured divergent on exactly 0 of 396 staves -- so the staged pipeline
    does not emit the reading twice and there is nothing to de-duplicate. The
    correlation machinery stays for the cases where two rows really are one
    signal; this particular duplicate simply ceases to exist.
    """
    by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            by_key[(c.page_index, key[0], key[1], c.measure_index)] = c

    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        if sub.cell != 0:
            continue          # a clef is read at the head of the staff
        staff_sub = R.staff(sub.page, sub.system, sub.staff)
        frame = frame_cell(0)
        grid = _cell_grid(by_key.get((sub.page, sub.system, sub.staff, 0)))
        clefs = [d for d in dets if d.smufl_name in _CLEF_CLASSES]
        if not clefs:
            log.abstain(staff_sub, Q.CLEF_GLYPH, reader=READERS.DETECTOR,
                        frame=frame, reason=ABSTAIN.NO_DETECTIONS)
            continue
        # ⚠️ EVERY candidate is emitted, not just the argmax. Today the losing
        # candidates ARE recorded (`clef_evidence["contest"]`, 29 writer
        # references) and read by nobody, and the winner takes the staff at
        # any confidence because there is no floor anywhere.
        # ⚠️ WHERE THE GLYPH SITS ON *THIS* STAFF, IN STAFF STEPS -- the same
        # measurement a notehead gets, and for the same reason. A measure cell
        # is the staff plus four staff spaces of air, so on a conductor's page
        # a NEIGHBOURING staff's clef lands in this staff's cell: measured on
        # Brahms 1 p.2, five staves each detect one `clefG` AND one `clefF`,
        # at nearly the same x and 250-350 canonical px apart in y, and the
        # adjudicator scores them 3.0 against 3.0 and abstains
        # `margin_below_floor`. Sixty-seven notes on Beethoven p.3 have no
        # pitch for exactly that reason.
        #
        # ⚠️ RECORDED, NOT ACTED ON. Which of the two is this staff's is an
        # arbitration with its own evidence and its own right to abstain, and
        # a filter here would make that decision invisibly. `position_steps`
        # is measured DOWN FROM THE TOP LINE in half-spaces, so a five-line
        # staff spans 0..+8 and anything far outside that is standing off the
        # staff.
        for d in clefs:
            log.observe(staff_sub, Q.CLEF_GLYPH, d.smufl_name,
                        reader=READERS.DETECTOR, frame=frame,
                        score=float(d.confidence),
                        y_center=d.y_center, x_center=d.x_center)

        # ⚠️ A SEPARATE ROW FROM A SEPARATE READER, and it has to be. Every
        # `CLEF_GLYPH` row here shares a reader, a frame and a quantity, so
        # the correlation rule calls them ONE SIGNAL and `tally` counts the
        # group once -- a term citing a glyph row is absorbed by that glyph's
        # own detector term. Measured: 1.5 beside 3.0 left the contest at 3.0
        # against 3.0. The GRID is a different reader and its evidence stands
        # on its own.
        if grid is None:
            log.abstain(staff_sub, Q.CLEF_POSITION, reader=READERS.GEOMETRY,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY)
        else:
            top_y, half_step = grid
            for d in clefs:
                log.observe(staff_sub, Q.CLEF_POSITION,
                            (d.y_center - top_y) / half_step,
                            reader=READERS.GEOMETRY, frame=frame,
                            glyph=d.smufl_name, y_center=d.y_center)


#: The locator's own branch names -> our abstention vocabulary. Where a name
#: is identical it is kept identical, deliberately.
_LOCATOR_REASON = {
    "no_staff_metrics": ABSTAIN.NO_STAFF_GEOMETRY,
    "no_mask": ABSTAIN.NO_MASK,
    "no_clusters": ABSTAIN.NO_CLUSTERS,
    "occupied": ABSTAIN.OCCUPIED,
    "off_staff_only": ABSTAIN.OFF_STAFF_ONLY,
    "only_debris": ABSTAIN.ONLY_DEBRIS,
    "too_far_right": ABSTAIN.TOO_FAR_RIGHT,
    "asymmetric": ABSTAIN.ASYMMETRIC,
    "ambiguous_snap": ABSTAIN.AMBIGUOUS_SNAP,
    "f_clef_dots": ABSTAIN.F_CLEF_DOTS,
    "mezzosoprano_symmetry": ABSTAIN.MEZZOSOPRANO_SYMMETRY,
}


def gather_clef_locator(log: Log, pws: Any, cells: Sequence[Any],
                        local: Dict[int, Tuple[int, int]],
                        detections: Dict[str, List[Any]]) -> None:
    """The CV C-clef locator, on BOTH crops, with its own refusal reason.

    ⚠️ TWO GATES ARE DELETED HERE AND THAT IS THE POINT OF THE STAGE.

    1. `transcribe.py:1953` runs the locator only `if clef_source is None` --
       silenced by PRESENCE, not by score, so a detector clef at 0.11
       permanently mutes it.
    2. `_header_cell_beats_measure_cell` (`:1669`, called `:4940`) is a
       BOOLEAN that picks ONE crop for the locator to read. Measured: on 14 of
       14 divergent staves it chose the MEASURE CELL -- the crop the reader
       could not read -- while the other crop had already been read and thrown
       away in the same run. 13 of those 14 are the header crop reading a C
       clef at symmetry 0.78-0.97 that the measure cell refused for
       `occupied` / `too_big` / `no_clusters`: too much other ink.

    Here both crops are read unconditionally, both are recorded, and the
    choice becomes a scoring term in ADJUDICATE where it can be seen.

    ⚠️ AND `trace` IS PASSED. `locate_clef` has always been able to say which
    branch ended it, and NEITHER pipeline call site passes a trace -- so today
    every refusal is an indistinguishable `None`. That is a Class-A fault
    (the score is never formed) sitting one keyword argument away from fixed.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    try:
        from ..clef_locator import locate_clef
        from ..staff_header import header_cells_for_page
    except Exception:                                         # noqa: BLE001
        _stub_per_staff(log, cells, local, Q.CLEF_LOCATED, READERS.CV_LOCATOR,
                        FRAME_HEADER_WINDOW, "clef_locator unavailable")
        return

    try:
        header_cells = header_cells_for_page(pws)
    except Exception as exc:                                  # noqa: BLE001
        header_cells = {}

    first_cell = {}
    for c in cells:
        if c.measure_index == 0:
            first_cell.setdefault(c.staff_index, c)

    for staff_index, key in sorted(local.items()):
        sub = R.staff(p, key[0], key[1])
        crops = ((FRAME_HEADER_WINDOW, header_cells.get(staff_index)),
                 (frame_cell(0), first_cell.get(staff_index)))
        for frame, crop in crops:
            if crop is None:
                log.abstain(sub, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="no crop of this kind for this staff")
                continue
            occupied = _occupied_boxes(detections, p, key, frame)
            trace: Dict[str, Any] = {}
            try:
                found = locate_clef(crop, occupied_boxes=occupied, trace=trace)
            except Exception as exc:                          # noqa: BLE001
                log.abstain(sub, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            error=type(exc).__name__)
                continue
            if found is None:
                branch = str(trace.get("reason", "no_clusters"))
                log.abstain(
                    sub, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                    frame=frame,
                    reason=_LOCATOR_REASON.get(branch, ABSTAIN.NO_CLUSTERS),
                    locator_branch=branch, **{k: v for k, v in trace.items()
                                              if k != "reason"})
                continue
            # ⚠️ THE X IS RECORDED BECAUSE WITHOUT IT NOTHING DOWNSTREAM CAN
            # SAY WHERE ON THE STAFF THIS CLEF WAS FOUND. `clef_glyph` has
            # carried `x_center` all along; this reader recorded
            # `family`/`line`/`line_source` and no position at all.
            #
            # ⚠️⚠️ AN EARLIER VERSION OF THIS COMMENT TOLD THE STORY BACKWARDS
            # AND WAS WRONG. It said the locator "read the mid-staff C clef
            # correctly" on Beethoven 5 / Litolff p.2. It did not, and it could
            # not: this loop examines the HEADER WINDOW and `frame_cell(0)`
            # only, and on that page the C clef stands at page x≈755, past the
            # first barline at ≈700, i.e. in measure 1 — a region no arm here
            # ever looks at. The claim came from matching the value `tenor`
            # against a human's "it goes to a C clef" without checking WHICH
            # CROP produced it.
            #
            # What actually happened, with its own control on the same page:
            # the Fagotti staff of system 1 detects `clefF` and the locator
            # abstains `asymmetric` on BOTH arms — correctly declining to call
            # a bass clef a C clef. The Fagotti staff of system 2 prints the
            # same bass clef, the detector finds NOTHING, and the locator fires
            # `tenor` on cell 0. That is a FALSE POSITIVE of the family
            # CLAUDE.md tracks at length (48 → 21 → 13 → 5), and with no
            # detector reading to contest it it became the staff's clef
            # unopposed at support 2.0, single candidate.
            #
            # Two separate facts, and neither excuses the other:
            #   * the locator misread a bass clef as a C clef here;
            #   * and the page prints two mid-staff clef changes (to C at ≈755,
            #     back to bass at ≈930, adjudicated against the print by Sean)
            #     that this pipeline cannot express AT ALL, because `Q.CLEF` is
            #     staff-scoped and no arm reads past cell 0.
            #
            # ⚠️ NOTHING CONSUMES THIS POSITION YET, deliberately rather than
            # by omission: expressing a clef CHANGE needs a cell-scoped
            # quantity and a change-position redundancy — the shape D18 already
            # describes for key signatures — which is a design step. Recording
            # where a reading came from is the half that is free and unblocks
            # it.
            x0, _y0, w, _h = found.bbox
            log.observe(sub, Q.CLEF_LOCATED, found.read.name,
                        reader=READERS.CV_LOCATOR, frame=frame,
                        score=float(found.symmetry),
                        family=found.read.family, line=found.read.line,
                        line_source=found.read.source,
                        x_center=int(x0 + w / 2), bbox=list(found.bbox))


def _occupied_boxes(detections, page: int, key, frame: str):
    """The noteheads the detector is already sure about.

    A clef never overlaps one, so a candidate that does is rejected -- which
    matters where a cell begins PAST its clef, because the first cluster is
    then real notation and a stacked chord is tall, glyph-sized and vertically
    symmetric enough to pass for a C clef.
    """
    cell_key = R.cell(page, key[0], key[1], 0).to_key()
    out = []
    for d in detections.get(cell_key, ()):
        if d.smufl_name.startswith(_NOTEHEAD_PREFIX):
            out.append((d.x_canonical, d.y_canonical,
                        d.width_canonical, d.height_canonical))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Declared stubs -- present, addressed, and honest about being empty
# ─────────────────────────────────────────────────────────────────────────────


def _stub_per_staff(log: Log, cells: Sequence[Any],
                    local: Dict[int, Tuple[int, int]], quantity: str,
                    reader: str, frame: str, note: str) -> None:
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.staff(c.page_index, key[0], key[1])
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        log.abstain(sub, quantity, reader=reader, frame=frame,
                    reason=ABSTAIN.NOT_IMPLEMENTED, note=note)


def gather_clef_seed(log: Log, cells, local, *, dossier: Any,
                     sources: Dict[str, str]) -> None:
    """The dossier's clef for each staff, DERIVED FROM the dossier fact.

    ⚠️ THE `derived_from` IS THE WHOLE POINT OF THIS FUNCTION.

    A dossier that supplies a clef seed AND an instrument has supplied ONE
    source twice. With both rows carrying the dossier fact in their basis, the
    correlation check sees them as one signal and `tally` counts them once.
    Without it they look like two independent witnesses agreeing -- which is
    the more insidious form of the dossier hazard, and the form the staged
    split does NOT dissolve.
    """
    if dossier is None or "dossier" not in sources:
        return
    clefs = {}
    if isinstance(dossier, dict):
        clefs = dossier.get("clef_by_staff") or {}
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.staff(c.page_index, key[0], key[1])
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        value = clefs.get(key[1]) or clefs.get(str(key[1]))
        if value is None:
            log.abstain(sub, Q.CLEF_SEED, reader=READERS.DOSSIER,
                        frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                        note="the dossier names no clef for this staff")
            continue
        log.observe(sub, Q.CLEF_SEED, value, reader=READERS.DOSSIER,
                    frame=FRAME_PAGE, tier="dossier",
                    derived_from=(sources["dossier"],))


#: The clefs whose slot tables `key_signature_geometry` covers.
#: ⚠️ Six more (soprano, mezzo, baritone, french, varbaritone, subbass) have no
#: table, so a key signature on one of those is UNSATISFIABLE, not merely
#: unread. Recorded so an abstention there is not read as a reader failure.
_SLOT_TABLE_CLEFS = ("treble", "bass", "alto", "tenor")

_KEYSIG_CLASSES = ("keySharp", "keyFlat", "keyNatural")


def gather_key_signature(log: Log, pws: Any, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]]) -> None:
    """The accidental run's POSITIONS -- and which clefs the run fits.

    ⚠️ THE GUARD IS NOT DELETED. `key_signature_locator.py:310` is
    `if not clef: return None`, and it is deliberate and paid for: fitting
    three flats against a GUESSED clef once returned TWO SHARPS, a different
    accidental type fitting a different prefix well inside tolerance.
    `transcribe.py:4670-4679` says it in the code's own words -- *"reading a key
    signature against a guessed clef is guessing twice."*

    ⚠️ SO THE READER IS ASKED THE QUESTION ONCE PER CANDIDATE CLEF instead of
    once with a guess. That is not a workaround for the guard, it is the
    honest form of the question: the run's POSITIONS are clef-free geometry
    and the SLOT TABLE is what the clef chooses, so *which clefs the run fits*
    is evidence about the CLEF (`Q.KEYSIG_CLEF_FIT`) and the positions are a
    measurement in their own right.

    ⚠️ AND IT IS WHY THE POSITIONS CANNOT BE TAKEN FROM ONE CALL. The reader
    returns `None` when the FIT fails, discarding the boxes it already found --
    so a single call with a wrong clef loses exactly the staff whose clef is
    wrong, which is the population that matters.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    try:
        from ..key_signature_locator import locate_key_signature
        from ..staff_header import header_cells_for_page
    except Exception:                                         # noqa: BLE001
        _stub_per_staff(log, cells, local, Q.KEYSIG_RUN_POSITION,
                        READERS.CV_HEADER, FRAME_HEADER_WINDOW,
                        "key_signature_locator unavailable")
        return

    try:
        header_cells = header_cells_for_page(pws)
    except Exception:                                         # noqa: BLE001
        header_cells = {}

    for staff_index, key in sorted(local.items()):
        sub = R.staff(p, key[0], key[1])
        _gather_keysig_markers(log, sub, detections, p, key)

        crop = header_cells.get(staff_index)
        if crop is None:
            log.abstain(sub, Q.KEYSIG_RUN_POSITION, reader=READERS.CV_HEADER,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue

        occupied = _occupied_boxes(detections, p, key, FRAME_HEADER_WINDOW)
        positions = None
        fitted_any = False
        for candidate in _SLOT_TABLE_CLEFS:
            try:
                found = locate_key_signature(crop, candidate,
                                             occupied_boxes=occupied)
            except Exception:                                 # noqa: BLE001
                continue
            if found is None:
                continue
            fitted_any = True
            log.observe(sub, Q.KEYSIG_CLEF_FIT, candidate,
                        reader=READERS.CV_HEADER, frame=FRAME_HEADER_WINDOW,
                        n_accidentals=len(found.boxes),
                        accidental=found.accidental,
                        decided_by=found.decided_by,
                        fifths=getattr(found.read, "fifths", None))
            if positions is None:
                positions = [b[0] for b in found.boxes]

        if not fitted_any:
            # ⚠️ Two different states collapse here and the detail says which:
            # a run that fits NO slot table, and a header with no run at all.
            log.abstain(sub, Q.KEYSIG_RUN_POSITION, reader=READERS.CV_HEADER,
                        frame=FRAME_HEADER_WINDOW, reason=ABSTAIN.NO_CLUSTERS,
                        note="no candidate clef's slot table fits this header",
                        clefs_tried=list(_SLOT_TABLE_CLEFS))
            continue

        log.observe(sub, Q.KEYSIG_RUN_POSITION, positions or [],
                    reader=READERS.CV_HEADER, frame=FRAME_HEADER_WINDOW,
                    n_accidentals=len(positions or []))


def _gather_keysig_markers(log: Log, sub: Subject, detections, p: int,
                           key) -> None:
    """The DETECTOR's own key accidentals, from the staff's first cell."""
    cell_key = R.cell(p, key[0], key[1], 0).to_key()
    marks = [d for d in detections.get(cell_key, ())
             if d.smufl_name in _KEYSIG_CLASSES]
    if not marks:
        log.abstain(sub, Q.KEYSIG_MARKER, reader=READERS.DETECTOR,
                    frame=frame_cell(0), reason=ABSTAIN.NO_DETECTIONS)
        return
    for d in sorted(marks, key=lambda m: m.x_canonical):
        log.observe(sub, Q.KEYSIG_MARKER, d.smufl_name,
                    reader=READERS.DETECTOR, frame=frame_cell(0),
                    score=float(d.confidence), x=d.x_canonical,
                    y_center=d.y_center)


_METER_CLASSES = ("timeSigCommon", "timeSigCutCommon")


def gather_meter(log: Log, pws: Any, cells: Sequence[Any],
                 local: Dict[int, Tuple[int, int]],
                 detections: Dict[str, List[Any]]) -> None:
    """The meter, read per STAFF. The vote is an adjudication, not a reading.

    ⚠️ ONE ROW PER STAFF, NOT PER MEASURE. A meter is carried onto every later
    measure of its staff, so counting measures counts one reading many times:
    a single `timeSig4` at confidence 0.42, on one staff of nineteen, once
    arrived at a page vote as EIGHTEEN unanimous votes for common time.

    ⚠️ AND THE TEMPLATE READER ALREADY CARRIES ITS OWN CONTEST -- `raw`,
    `runner_up_raw`, `runner_up_score`, `score_margin` -- which is the shape
    this architecture asks every decision for, sitting on a dataclass since
    before it. All four are recorded.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    try:
        from ..staff_header import header_cells_for_page
        from ..time_signature_locator import locate_time_signature
    except Exception:                                         # noqa: BLE001
        _stub_per_staff(log, cells, local, Q.METER_TEMPLATE, READERS.TEMPLATE,
                        FRAME_HEADER_WINDOW, "time_signature_locator missing")
        return
    try:
        header_cells = header_cells_for_page(pws)
    except Exception:                                         # noqa: BLE001
        header_cells = {}

    for staff_index, key in sorted(local.items()):
        sub = R.staff(p, key[0], key[1])
        _gather_meter_glyphs(log, sub, detections, p, key)

        crop = header_cells.get(staff_index)
        if crop is None:
            log.abstain(sub, Q.METER_TEMPLATE, reader=READERS.TEMPLATE,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        trace: Dict[str, Any] = {}
        try:
            found = locate_time_signature(crop, trace=trace)
        except Exception:                                     # noqa: BLE001
            log.abstain(sub, Q.METER_TEMPLATE, reader=READERS.TEMPLATE,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.READER_UNAVAILABLE)
            continue
        if found is None:
            # ⚠️ A page that prints no meter at all is the COMMON case -- a
            # meter is printed at the start of a movement and nowhere else --
            # so this abstention is usually correct, not a miss.
            log.abstain(sub, Q.METER_TEMPLATE, reader=READERS.TEMPLATE,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.BELOW_THRESHOLD,
                        **{k: v for k, v in trace.items() if k != "reason"})
            continue
        log.observe(sub, Q.METER_TEMPLATE,
                    (int(found.numerator), int(found.denominator)),
                    reader=READERS.TEMPLATE, frame=FRAME_HEADER_WINDOW,
                    score=float(found.score), raw=found.raw,
                    runner_up=found.runner_up_raw,
                    runner_up_score=found.runner_up_score,
                    score_margin=found.score_margin)


def _gather_meter_glyphs(log: Log, sub: Subject, detections, p: int,
                         key) -> None:
    """The detector's own meter glyphs. ⚠️ `timeSigCommon` and
    `timeSigCutCommon` are the two the detector reads WELL and the template
    library has no digits for -- so the two readers are complementary, not
    redundant, and both belong on the record."""
    # ⚠️⚠️ EVERY CELL, NOT CELL 0 — and the hardcoded `0` this replaces is what
    # made a printed METER CHANGE invisible. A meter is printed at the head of
    # a staff AND wherever it changes, and both readers were looking only at
    # the header: this one at cell 0 and the template reader at the header
    # crop. Measured on Beethoven 5 / Litolff p.62, whose print carries a
    # double barline, "Tempo I." and a new time signature on every staff
    # mid-system: the detector fired `timeSig3` + five `timeSig4` in CELL 8,
    # those detections sat on the record as ordinary `glyph_box` rows, and
    # `meter_glyph` abstained `no_detections` on all 17 staves.
    #
    # ⚠️ The CELL is recorded on every row, because WHERE a meter glyph stands
    # is the whole of its meaning here: at cell 0 it states the staff's meter,
    # anywhere else it announces a change at that bar.
    marks = []
    for cell_index, cell_dets in _meter_cells(detections, p, key):
        for d in cell_dets:
            if d.smufl_name.startswith("timeSig"):
                marks.append((cell_index, d))
    if not marks:
        log.abstain(sub, Q.METER_GLYPH, reader=READERS.DETECTOR,
                    frame=frame_cell(0), reason=ABSTAIN.NO_DETECTIONS)
        return
    for cell_index, d in sorted(marks, key=lambda m: (m[0], m[1].x_canonical,
                                                      m[1].y_canonical)):
        log.observe(sub, Q.METER_GLYPH, d.smufl_name,
                    reader=READERS.DETECTOR, frame=frame_cell(cell_index),
                    score=float(d.confidence), x=d.x_canonical,
                    y_center=d.y_center, cell=cell_index,
                    letter=(d.smufl_name in _METER_CLASSES))


def _meter_cells(detections, p: int, key):
    """(cell_index, detections) for every cell of this staff, in bar order."""
    prefix = R.cell(p, key[0], key[1], 0).to_key().rsplit("/", 1)[0] + "/"
    out = []
    for cell_key, dets in detections.items():
        if not cell_key.startswith(prefix):
            continue
        try:
            out.append((int(cell_key.rsplit("/", 1)[1]), dets))
        except ValueError:
            continue
    return sorted(out)


def gather_margin_labels(log: Log, pws: Any, cells, local, *,
                         pdf_path: Any = None, surya_fallback: bool = False,
                         ocr_fallback: bool = False) -> None:
    """The printed instrument name, as a STRING, before the lexicon.

    ⚠️ IT CALLS THE CASCADE, NOT THE READERS. `contextual._labels_for_page`
    goes PDF text layer -> Surya -> Tesseract -> whoever `assist` names, and
    it only pays for the next rung when the free one comes back empty.
    Calling the three readers separately -- or in parallel -- spends the money
    the cascade exists to save.

    ⚠️ AND THE SPLIT THIS FUNCTION EXISTS TO MAKE: `StaffLabel` already
    carries BOTH the raw text AND a resolved `instrument`, because the reader
    runs the lexicon itself. GATHER emits ONLY `text`. The lexicon lookup is
    an INTERPRETATION and belongs to `adjudicators.identity`; keeping it here
    would be the same fusion the whole architecture is against -- and it is
    exactly the fusion that let `Tr. Alt.` become a singer at high confidence
    while the raw string sat right beside it.

    The reader's own `confidence` and `alias` are kept in `detail` as its
    annotation, deliberately NOT as the row's value or score: they describe
    a lexicon match this row is not making.
    """
    if pdf_path is None:
        _stub_per_staff(log, cells, local, Q.MARGIN_LABEL, READERS.TEXT_LAYER,
                        FRAME_MARGIN, "no pdf_path supplied to gather()")
        return

    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    try:
        from pathlib import Path as _Path
        from ..assist import Assist
        from ..contextual import _labels_for_page
        labels = _labels_for_page(
            pws, _Path(str(pdf_path)), p, assist=Assist("none"), budget=[0],
            surya_fallback=surya_fallback, ocr_fallback=ocr_fallback)
    except Exception as exc:                                  # noqa: BLE001
        # ⚠️ An optional reader that cannot run ABSTAINS -- it does not lose
        # the page. But it abstains LOUDLY enough to be told from a reader
        # that ran and found nothing: the exception class goes in the detail.
        _stub_per_staff(log, cells, local, Q.MARGIN_LABEL, READERS.TEXT_LAYER,
                        FRAME_MARGIN, f"reader failed: {type(exc).__name__}")
        return

    by_staff = {lab.staff_index: lab for lab in labels}
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.staff(c.page_index, key[0], key[1])
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        lab = by_staff.get(c.staff_index)
        if lab is None or not (lab.text or "").strip():
            log.abstain(sub, Q.MARGIN_LABEL, reader=READERS.TEXT_LAYER,
                        frame=FRAME_MARGIN, reason=ABSTAIN.NO_INK)
            continue
        log.observe(sub, Q.MARGIN_LABEL, lab.text,
                    reader=READERS.TEXT_LAYER, frame=FRAME_MARGIN,
                    reader_confidence=lab.confidence, reader_alias=lab.alias,
                    y_center_px=lab.y_center_px)


def gather_direction_text(log: Log, pws, cells, local) -> None:
    """⚠️ DECLARED STUB, and it sits behind one of the three HARD edges:
    `direction_text._blank_detections` (`:301`) erases every detected glyph
    from the mask before looking for words, so this cannot run before
    detection. It is ordered last in `gather()` for that reason."""
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    log.abstain(R.page(p), Q.DIRECTION_WORD, reader=READERS.SURYA,
                frame=FRAME_PAGE, reason=ABSTAIN.NOT_IMPLEMENTED,
                note="hard edge: must run AFTER detection")


def gather_external(log: Log, pws, *, dossier: Any = None,
                    roster: Any = None) -> Dict[str, str]:
    """Facts that are not read off THIS raster.

    ⚠️ They are still Observations -- their ancestor is not our page, so they
    can close no loop with anything we read -- but they carry a `tier` so a
    consumer can hold them out on QUALITY grounds, which is a different
    question from circularity and is kept separate on purpose.
    """
    sources: Dict[str, str] = {}
    if dossier is None:
        log.abstain(R.DOCUMENT, Q.DOSSIER_FACT, reader=READERS.DOSSIER,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no dossier supplied")
    else:
        row = log.observe(R.DOCUMENT, Q.DOSSIER_FACT, dossier,
                          reader=READERS.DOSSIER, frame=FRAME_PAGE,
                          tier="dossier")
        sources["dossier"] = row.id
    if roster is None:
        log.abstain(R.DOCUMENT, Q.ROSTER_ENTRY, reader=READERS.CATALOG,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no work id / roster supplied")
    else:
        row = log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, roster,
                          reader=READERS.CATALOG, frame=FRAME_PAGE,
                          tier="roster")
        sources["roster"] = row.id
    return sources


# ─────────────────────────────────────────────────────────────────────────────
# The stage
# ─────────────────────────────────────────────────────────────────────────────


def gather(pws_and_cells: Sequence[Tuple[Any, Sequence[Any]]], *,
           detector: Any = None, conf_threshold: float = 0.25,
           imgsz: Optional[int] = None, dossier: Any = None,
           roster: Any = None, pdf_path: Any = None,
           surya_fallback: bool = False, ocr_fallback: bool = False,
           log: Optional[Log] = None,
           progress: bool = False) -> Log:
    """Run every reader over already-prepared pages and return a frozen Log.

    ⚠️ THE ORDER BELOW IS THE ASSUMED ONE AND ONLY THREE STEPS OF IT ARE
    FORCED (A-GATHER-1):

      1. page geometry before everything -- a cell is DEFINED by
         `staff.line_ys` and nothing has coordinates before it;
      2. detection before direction text -- it subtracts every detection from
         the page's ink;
      3. detection before notehead positions -- the position is measured from
         a detection's y-centre.

    Everything else is free to reorder. ⚠️ A FOURTH edge was found during the
    build and does NOT appear here because it is an ADJUDICATION edge, not a
    gathering one: the meter vote consumes committed durations. See
    ASSUMPTIONS.md A-DUR-1.
    """
    log = log if log is not None else Log()

    for pws, cells in pws_and_cells:
        # ⚠️ EXTERNAL FACTS FIRST. Not an ordering preference: anything
        # DERIVED from a dossier or roster must be able to name that row in
        # its `derived_from`, and `Log.observe` refuses a `derived_from` that
        # is not already in the log -- deliberately, because a dangling
        # reference would silently restore the double-counting this ordering
        # exists to prevent.
        sources = gather_external(log, pws, dossier=dossier, roster=roster)
        local = gather_geometry(log, pws)
        gather_systems(log, pws, getattr(pws, "used_bridging", True))
        gather_measures(log, pws, cells, local)

        detections = gather_detections(
            log, cells, local, detector=detector,
            conf_threshold=conf_threshold, imgsz=imgsz, progress=progress)

        gather_notehead_positions(log, cells, local, detections)
        gather_ownership_evidence(log, pws, cells, local, detections)
        gather_rhythm_marks(log, cells, local, detections)
        gather_glyph_families(log, detections)
        # ⚠️ AFTER detection (the letters ARE detections, and the CV wedge
        # search blanks the point detections out of the ink first) and BEFORE
        # direction text, which subtracts every detection from the page: these
        # two read the SAME band and the ordering between them is real.
        gather_dynamic_letters(log, pws, cells, local, detections)
        gather_wedge_boxes(log, pws, cells, local, detections)
        gather_cv_lines(log, cells, local)
        gather_detector_beams(log, detections)
        gather_clef(log, cells, local, detections)
        gather_clef_locator(log, pws, cells, local, detections)
        gather_clef_seed(log, cells, local, dossier=dossier, sources=sources)
        gather_key_signature(log, pws, cells, local, detections)
        gather_meter(log, pws, cells, local, detections)
        gather_margin_labels(log, pws, cells, local, pdf_path=pdf_path,
                             surya_fallback=surya_fallback,
                             ocr_fallback=ocr_fallback)
        gather_direction_text(log, pws, cells, local)   # hard edge: last

    log.freeze()
    return log
