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


def gather_clef_locator(log: Log, cells: Sequence[Any],
                        local: Dict[int, Tuple[int, int]], *,
                        enabled: bool = True) -> None:
    """The CV C-clef locator, on BOTH crops.

    ⚠️ TWO GATES ARE DELETED HERE AND THAT IS THE POINT OF THE STAGE.

    1. `transcribe.py:1953` runs the locator only `if clef_source is None` --
       it is silenced by PRESENCE, not by score, so a detector clef at 0.11
       permanently mutes it.
    2. `_header_cell_beats_measure_cell` (`:1669`, called `:4940`) is a
       boolean that picks ONE crop for the locator to read. On 14 of 14
       divergent staves it chose the MEASURE CELL -- the crop the reader could
       not read -- while the other crop had already been read and thrown away
       in the same run.

    Under the split both crops are read unconditionally and both are
    recorded, and the choice becomes a scoring term in ADJUDICATE where it
    can be seen and can abstain.

    ⚠️ DECLARED STUB. The locator's own call needs a header crop built by
    `staff_header.header_cells_for_page` plus the occupied-box list, and
    wiring that faithfully is a follow-on. It abstains with
    NOT_IMPLEMENTED so the stage is present and its absence is on the record
    rather than silent.
    """
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None or c.measure_index != 0:
            continue
        sub = R.staff(c.page_index, key[0], key[1])
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        for frame in (FRAME_HEADER_WINDOW, frame_cell(0)):
            log.abstain(sub, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                        frame=frame, reason=ABSTAIN.NOT_IMPLEMENTED,
                        note="both crops are addressed; the reader is not "
                             "wired yet -- see gather.gather_clef_locator")


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


def gather_key_signature(log: Log, cells, local) -> None:
    """⚠️ DECLARED STUB, and the one that needs a reader CHANGED rather than
    called.

    `key_signature_locator.py:310` is `if not clef: return None` -- the reader
    refuses to run without a clef. For GATHER it must emit the accidental
    RUN's positions with NO clef, because those positions are pure geometry:
    `:322-337` finds components and clusters them, `:347-368` locates where
    the clef ended by HEIGHT IN STAFF SPACES without consulting the clef
    argument, and the clef enters only at `:398-399` in `fit_key_signature`.

    ⚠️ THE GUARD IS NOT DELETED WHEN THIS IS DONE. It MOVES to the fit. It is
    deliberate and paid for: fitting against a guessed clef once read three
    flats as TWO SHARPS. After the move the reader still refuses to NAME a
    key without a clef; what changes is that the positions survive to the
    adjudicator, which has the clef verdict in hand and can abstain instead
    of guessing.
    """
    _stub_per_staff(log, cells, local, Q.KEYSIG_RUN_POSITION,
                    READERS.CV_HEADER, FRAME_HEADER_WINDOW,
                    "needs key_signature_locator's clef guard moved to the fit")


def gather_meter(log: Log, cells, local) -> None:
    """⚠️ DECLARED STUB. `time_signature_locator.locate_time_signature` and
    the template reader both return a reading that would translate directly;
    the vote (`vote_system_time_signature`) is an ADJUDICATION and belongs in
    the next stage, not here."""
    _stub_per_staff(log, cells, local, Q.METER_GLYPH, READERS.DETECTOR,
                    FRAME_HEADER_WINDOW, "locate_time_signature not wired")


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
                    roster: Any = None) -> None:
    """Facts that are not read off THIS raster.

    ⚠️ They are still Observations -- their ancestor is not our page, so they
    can close no loop with anything we read -- but they carry a `tier` so a
    consumer can hold them out on QUALITY grounds, which is a different
    question from circularity and is kept separate on purpose.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    if dossier is None:
        log.abstain(R.DOCUMENT, Q.DOSSIER_FACT, reader=READERS.DOSSIER,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no dossier supplied")
    else:
        log.observe(R.DOCUMENT, Q.DOSSIER_FACT, dossier,
                    reader=READERS.DOSSIER, frame=FRAME_PAGE, tier="dossier")
    if roster is None:
        log.abstain(R.DOCUMENT, Q.ROSTER_ENTRY, reader=READERS.CATALOG,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no work id / roster supplied")
    else:
        log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, roster,
                    reader=READERS.CATALOG, frame=FRAME_PAGE, tier="roster")


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
        local = gather_geometry(log, pws)
        gather_systems(log, pws, getattr(pws, "used_bridging", True))
        gather_measures(log, pws, cells, local)

        detections = gather_detections(
            log, cells, local, detector=detector,
            conf_threshold=conf_threshold, imgsz=imgsz, progress=progress)

        gather_notehead_positions(log, cells, local, detections)
        gather_clef(log, cells, local, detections)
        gather_clef_locator(log, cells, local)
        gather_key_signature(log, cells, local)
        gather_meter(log, cells, local)
        gather_margin_labels(log, pws, cells, local, pdf_path=pdf_path,
                             surya_fallback=surya_fallback,
                             ocr_fallback=ocr_fallback)
        gather_direction_text(log, pws, cells, local)   # hard edge: last
        gather_external(log, pws, dossier=dossier, roster=roster)

    log.freeze()
    return log
