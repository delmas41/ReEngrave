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
            log.observe(g, Q.GLYPH_BOX,
                        (d.smufl_name, d.x_canonical, d.y_canonical,
                         d.width_canonical, d.height_canonical),
                        reader=READERS.DETECTOR, frame=frame,
                        score=float(d.confidence), category=d.category)
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
        lines = list(c.staff_line_ys_canonical or [])
        if len(lines) < 2:
            log.abstain(sub, Q.NOTEHEAD_STAFF_POSITION,
                        reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
        half_step = (sum(gaps) / len(gaps)) / 2.0
        top_y = lines[0]
        if half_step <= 0:
            log.abstain(sub, Q.NOTEHEAD_STAFF_POSITION,
                        reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
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


def gather_cv_lines(log: Log, cells: Sequence[Any],
                    local: Dict[int, Tuple[int, int]]) -> None:
    """⚠️ DECLARED STUB -- the classical-CV stem and beam rung.

    `line_detection` reads these off the STAFF-LINE-REMOVED cell variant while
    the detector reads the ORIGINAL. That split is deliberate and measured:
    erasing staff lines before YOLO costs 7-13 pooled reading points and up to
    a third of the noteheads, and MANUFACTURES beam confusion (46 -> 105
    detections at precision 0.783 -> 0.343 on residue). **Erase for the CV
    consumer, never for the detector.**

    ⚠️ And when this is wired, a YOLO beam box must be KEPT ONLY where no CV
    beam overlaps its x-range. A YOLO box bounds the STACK, not a stroke, so
    unioning them contributes a centre in the GAP between two strokes and
    three sixteenths read as three eighths.
    """
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
                        reason=ABSTAIN.NOT_IMPLEMENTED,
                        note="line_detection not wired; erase for the CV "
                             "consumer, never for the detector")


# ─────────────────────────────────────────────────────────────────────────────
# The clef -- every reader, and BOTH crops
# ─────────────────────────────────────────────────────────────────────────────


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
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        if sub.cell != 0:
            continue          # a clef is read at the head of the staff
        staff_sub = R.staff(sub.page, sub.system, sub.staff)
        frame = frame_cell(0)
        clefs = [d for d in dets if d.smufl_name in _CLEF_CLASSES]
        if not clefs:
            log.abstain(staff_sub, Q.CLEF_GLYPH, reader=READERS.DETECTOR,
                        frame=frame, reason=ABSTAIN.NO_DETECTIONS)
            continue
        # ⚠️ EVERY candidate is emitted, not just the argmax. Today the losing
        # candidates ARE recorded (`clef_evidence["contest"]`, 29 writer
        # references) and read by nobody, and the winner takes the staff at
        # any confidence because there is no floor anywhere.
        for d in clefs:
            log.observe(staff_sub, Q.CLEF_GLYPH, d.smufl_name,
                        reader=READERS.DETECTOR, frame=frame,
                        score=float(d.confidence),
                        y_center=d.y_center, x_center=d.x_center)


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
            log.observe(sub, Q.CLEF_LOCATED, found.read.name,
                        reader=READERS.CV_LOCATOR, frame=frame,
                        score=float(found.symmetry),
                        family=found.read.family, line=found.read.line,
                        line_source=found.read.source)


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
    cell_key = R.cell(p, key[0], key[1], 0).to_key()
    marks = [d for d in detections.get(cell_key, ())
             if d.smufl_name.startswith("timeSig")]
    if not marks:
        log.abstain(sub, Q.METER_GLYPH, reader=READERS.DETECTOR,
                    frame=frame_cell(0), reason=ABSTAIN.NO_DETECTIONS)
        return
    for d in sorted(marks, key=lambda m: (m.x_canonical, m.y_canonical)):
        log.observe(sub, Q.METER_GLYPH, d.smufl_name,
                    reader=READERS.DETECTOR, frame=frame_cell(0),
                    score=float(d.confidence), x=d.x_canonical,
                    y_center=d.y_center,
                    letter=(d.smufl_name in _METER_CLASSES))


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
        gather_cv_lines(log, cells, local)
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
