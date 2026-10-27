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

import math
import os
from typing import (Any, Dict, Iterable, List, Optional, Sequence, Tuple)

from . import record as R
from . import one_ink as _one_ink
from . import accidental_shape as _acc_shape
from . import accidental_family as _acc_family
from .. import natural_candidate as _natural_candidate
from .geometry import standard_head_box as _standard_head_box_general
from .geometry import (STANDARD_HEAD_WIDTH_SPACES,
                       STANDARD_HEAD_HEIGHT_SPACES, is_regular_notehead)
from .record import ABSTAIN, Log, Q, READERS, Subject
from .record import STROKE_GLYPH_BASE as RECORD_STROKE_GLYPH_BASE

#: `OMR_RESEARCH` — the single umbrella docs/flags-2026-09.md's triage put
#: over every `research`-verdict flag (roadmap 0.2b): "moves behind the
#: single umbrella `OMR_RESEARCH=<name>[,<name>]`, may not be read by the
#: product path". A research flag's OWN switch still governs it — this is
#: ANDED with that switch, never a replacement for it — so a research
#: mechanism needs BOTH its own flag on AND its name listed here; naming it
#: here alone does nothing, and its own flag alone does not reach the product
#: path either. Only flags whose default is OFF are wired to this (a
#: default-ON research flag would change behaviour the moment this landed,
#: which a triage-enforcement lane may not do — see docs/flags-2026-09.md).
RESEARCH_ENV = "OMR_RESEARCH"


def research_enabled(name: str) -> bool:
    """Is `name` named in the comma-separated `OMR_RESEARCH` list?"""
    named = {n.strip() for n in os.environ.get(RESEARCH_ENV, "").split(",")
             if n.strip()}
    return name in named


# ─────────────────────────────────────────────────────────────────────────────
# Frames -- WHERE a reading was taken. Two readers of the same quantity on
# different crops are two signals; on the same crop they are one.
# ─────────────────────────────────────────────────────────────────────────────

FRAME_PAGE = "page"
FRAME_SYSTEM = "system"
FRAME_HEADER_WINDOW = "header_window"
FRAME_MARGIN = "system_margin"
#: ROADMAP 2.13: the crop directly above a SYSTEM's topmost staff, where the
#: printed bar number sits. Its own frame, not `FRAME_SYSTEM`, because two
#: readers sharing a frame word are declared ONE signal by
#: `adjudicate.Evidence.correlated_groups` -- and nothing else reads this box.
FRAME_BAR_NUMBER = "bar_number_crop"
#: ROADMAP 2.85: the band above a system's top staff where a 1st/2nd-ending
#: bracket is drawn; the crop inside its left hook where the numeral sits;
#: the window beside one barline on one staff where repeat dots sit. Three
#: frames, three crops -- the bracket and its numeral are TWO signals.
FRAME_VOLTA = "volta_band"
FRAME_VOLTA_NUMERAL = "volta_numeral_crop"
FRAME_REPEAT_DOTS = "repeat_dot_window"


def frame_cell(measure_index: int) -> str:
    return f"cell:{measure_index}"


def frame_bar_head(measure_index: int) -> str:
    """The first few staff spaces of a measure cell — where a meter CHANGE is
    printed, right after the barline.

    ⚠️ A DIFFERENT FRAME FROM `frame_cell`, deliberately. Two readers of the
    same quantity on different crops are two signals; on the same crop they
    are one, and this module's own header says so. A reading taken over four
    staff spaces of a bar's head and one taken over the whole bar are not the
    same observation and must never be pooled as if they were.
    """
    return f"bar_head:{measure_index}"


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

#: The incumbent admitted set, kept ONLY so the repair below can be read
#: against what it replaces -- and because the shape of it is the finding.
#:
#: ⚠️⚠️ IT ADMITS THE SPELLING THAT NEVER OCCURS AND DROPS THE TWO THAT DO.
#: `clefC` is the COARSE name (id 142), and `class_aliases` records the whole
#: coarse block firing ZERO times; measured over both shared records it fires
#: zero here too. The FINE C clefs `clefCAlto` (id 6) and `clefCTenor` (id 7)
#: are what the detector actually emits -- 16 detections over the two
#: documents, every one of them discarded here with no row, no abstention and
#: nothing anywhere to say it happened.
_CLEF_CLASSES_INCUMBENT = {"clefG", "clefF", "clefC", "clefUnpitchedPercussion"}


def _is_clef_class(name: Optional[str], category: Optional[str]) -> bool:
    """Is this detection a CLEF this staff-head pass should gather?

    ⚠️⚠️ THE CATEGORY TEST IS LOAD-BEARING AND IS NOT BELT-AND-BRACES.
    `clef_geometry.clef_family` reads the leading letter of the class name's
    core, and `class_aliases` already records the consequence in terms:
    `graceNoteAcciaccatura` "in isolation also reads as a treble clef ...
    harmless and unreachable: every caller filters `category != 'clef'`
    first". This call site did NOT filter -- it matched a literal set, so the
    trap was unreachable for a different reason. Measured over the committed
    208-name vocabulary, dropping the category test admits **27** classes as
    clefs, including every `flag*` (a `flag8thUp` would enter the contest as
    a BASS clef), every `fingering*`, `fermataAbove`/`Below`, `coda` and
    `caesura`. So the guard `class_aliases` says every caller keeps is
    written down here, where the family test is actually made.

    ⚠️ DERIVED FROM THE SHARED RULE, NOT RESTATED. `clef_family` is the one
    measured answer to "which clef family is this", it collapses BOTH
    spellings of the vocabulary (`clefCAlto` and DeepScoresV2's `cClefAlto`),
    and it is the same function `clef_geometry` and the legacy path already
    read. A second hand-written set here is exactly how this drop happened.

    ⚠️ `clef8` / `clef15` ARE NOT CLEFS AND STAY OUT -- deliberately, not by
    omission. They are octave markers that MODIFY a clef, so admitting them
    would let one compete as a clef in its own right. `_clef_core` names them
    explicitly and returns None, so this predicate excludes them by reading
    that rule rather than by restating it. They fire **0 times** on both
    shared records, so the exclusion costs nothing measured today; what it
    buys is that the day they do fire they cannot be mistaken for a reading.
    See `benchmarks/omr-staged-c-clef-2026-09/FINDINGS.md` §6.
    """
    if category != "clef":
        return False
    from ..clef_geometry import clef_family
    if clef_family(name) is not None:
        return True
    # Names a STAFF rather than a pitch, so `clef_family` is None by design.
    return "percussion" in (name or "").lower()



def _accepts_natural_candidates(detector) -> bool:
    """ROADMAP 2.193: does `detector.detect` take `natural_candidates` (or **kwargs)? A test double with a fixed signature does not."""
    import inspect
    try:
        ps = inspect.signature(detector.detect).parameters
    except (TypeError, ValueError):
        return False
    return "natural_candidates" in ps or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in ps.values())

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

        # ⚠️ THE CELL'S OWN RECTANGLE, filed BEFORE the detections and
        # independently of whether there are any. The arc merge asks where
        # this bar's boundary is; a bar we detected nothing in still HAS one,
        # and it is the neighbour of a bar that does. Declined rather than
        # defaulted, exactly as the glyph boxes below are: a cell whose page
        # rectangle is unknown must not be given a made-up one, because the
        # merge would then read a fabricated edge as a real barline.
        _cell_box = getattr(c, "bbox_page_px", None)
        if _cell_box and len(_cell_box) == 4:
            log.observe(cell_sub, Q.CELL_BOX, [float(v) for v in _cell_box],
                        reader=READERS.GEOMETRY, frame=frame)
        else:
            log.abstain(cell_sub, Q.CELL_BOX, reader=READERS.GEOMETRY,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        frame_note="cell carries no bbox_page_px")

        # ⚠️⚠️ THIS ASKS THE DETECTOR A DIFFERENT QUESTION FROM THE ONE THE
        # LEGACY PATH ASKS, AND EVERY MEASURED FIGURE IN THIS REPO IS THE
        # LEGACY ONE'S. `transcribe()` defaults to `iou_threshold=0.5,
        # agnostic_nms=True`; this call passes neither, so it takes
        # `YoloDetector.detect`'s own defaults, `0.7` and **False**. Class-wise
        # NMS never compares `noteheadHalfInSpace` with `noteheadBlackInSpace`
        # — the detector's own docstring names that as exactly what
        # `agnostic_nms` is for ("the same region can fire multiple
        # semantically-similar class predictions") — so one notehead survives
        # as three rows at IoU 0.91-0.96, each with its own duration verdict.
        # Measured on the committed Litolff Beethoven 5 p1-4 record: 284
        # same-cell notehead pairs and 143 same-cell dynamic-letter pairs.
        #
        # ⚠️ NOT CHANGED HERE, because changing it changes the DETECTION SET
        # and is therefore a GATHER change that only two full re-gathers can
        # price — see `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §6,
        # which ranks it first and gives the recipe. It is recorded rather
        # than quietly fixed so the next reader does not have to find it again.
        # ⚠️ ROADMAP 2.193 (flag `OMR_NATURAL_CANDIDATE`, default ON): also keep the detector's sub-floor NATURAL score on each accidental box
        # (`natural_score`), a candidate only; the kwarg is passed ONLY with the flag on AND to a detector whose `detect` takes it, so a detector double without it is unaffected.
        dets = detector.detect(c, conf_threshold=conf_threshold, imgsz=imgsz, **({"natural_candidates": True} if _natural_candidate.enabled() and _accepts_natural_candidates(detector) else {}))
        # ⚠️ ROADMAP 2.186 (flag `OMR_ONE_INK_ONE_MARK`, default OFF): the class-wise NMS above keeps two classes of one family on one ink;
        # merge them HERE, inside this cell, before any reader sees two boxes for one mark (`staged/one_ink.py` has the cause and the rules).
        if dets and _one_ink.enabled():
            dets = _one_ink.merge(dets)
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
            box_detail: Dict[str, Any] = {"category": d.category, **_one_ink.box_detail(d)}
            if "one_ink_absorbed_by_index" in box_detail:
                # ROADMAP 2.186: this box was absorbed by a stronger class on its ink; it keeps its glyph index and names its winner's key
                box_detail["one_ink_absorbed_by"] = R.glyph(p, sys_idx, st_idx, c.measure_index,
                                                            box_detail.pop("one_ink_absorbed_by_index")).to_key()
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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.55 — low-confidence rescue of a boxless, rest-less bar
# ─────────────────────────────────────────────────────────────────────────────

#: The confidence floor this reader re-runs the SAME detector at, on a
#: single cell, notehead/rest classes only. Named, never a bare literal
#: (CLAUDE.md §7): `OMR_CONF_THRESHOLD`'s 0.25 is the production floor every
#: other reader trusts; this is a SECOND, lower floor, read only here, and
#: only on a cell that already failed both the production pass and 2.52's
#: own ink search. ROADMAP 2.53 measured it: a `--conf 0.10` rerun recovered
#: a notehead/rest box in 24 of 29 Litolff p3 not-found cells, scoring
#: 0.10-0.25, under crossing ink (ties, ledgers, beams, slurs).
RESCUE_CONF_FLOOR = 0.10

#: ON since 2026-10-01 (Sean: "Do it all"), after he read the sheet of every
#: rescued head on Litolff pp.1-3 (24 rescued, 16 kept, the rest the same
#: head boxed twice). GATHER always files a rescued box's rows; this constant
#: governs only whether `adjudicate.subjects_for` admits a rescue-sourced
#: GLYPH subject into any decision's domain. No env flag (CLAUDE.md §9).
RESCUE_SHIPS = True


class GatherOrderError(RuntimeError):
    """A GATHER reader was called before a reader whose rows it reads.

    ⚠️ `Log.rows()` on a quantity nobody has filed returns EMPTY, not an
    error, so a reader placed above its input in `gather()` fails SILENTLY
    -- it reads "nothing there" and proceeds as if that were the answer.
    ROADMAP 2.58: the low-confidence rescue did exactly that for five days
    (reading `Q.EMPTY_BAR_REST_SEARCH` thirteen steps before it was filed,
    covered by a scratch re-run of the search). Raised by a reader that can
    tell, from the record, that its input never ran -- never by the record
    itself, which has no idea what a reader intends to read.
    """


#: ROADMAP 2.55 REFINEMENT (Sean, DECISIONS 2026-10-01, "rescue guided by
#: stems, ties and accidentals"): *"Every measure should have notes or
#: rests. If the bar shows ties then there are notes; if there are stems
#: then there are notes and the note heads will be connected to the stems.
#: If there are ties the notes will be close to the end of the ties. If
#: there are accidentals then there are notes."* A rescued box is accepted
#: ONLY within a tight window of a witness already on the record for this
#: bar; an unguided low-confidence box is rejected and recorded as such
#: (`ABSTAIN.RESCUE_UNGUIDED`), never accepted on score alone.
#:
#: Every window below is a half-width in STAFF SPACES (one staff space is
#: `2 * half_step`, `_cell_grid`'s own unit), named rather than a bare
#: literal (CLAUDE.md §7).
#:
#: ⚠️ A STEM'S DIRECTION (up/down) IS NOT RE-DERIVED HERE. Sean's rule ties
#: the head's SIDE of the stem to its direction (up -> bottom end, right
#: side; down -> top end, left side), but telling a stem's direction apart
#: needs the very head this search is looking for. Both ends of the stem
#: are therefore treated as candidate attachment points, and the window
#: straddles BOTH sides of the stem rather than committing to one --
#: looser than Sean's own rule, recorded here rather than silently assumed.
STEM_WITNESS_HALF_WIDTH_SPACES = 0.9   # either side of the stem
STEM_WITNESS_HALF_HEIGHT_SPACES = 0.6  # around the stem's own end
#: An arc is drawn OVER its notes (CLAUDE.md §10), so a tie/slur's own
#: bottom edge, at each horizontal end, is where a head hangs just below.
ARC_WITNESS_HALF_WIDTH_SPACES = 0.9    # just beyond each end of the arc
ARC_WITNESS_HALF_HEIGHT_SPACES = 0.9   # below the arc's own bottom edge
#: An accidental sits at the SAME staff position as its note, immediately
#: to the accidental's right.
ACCIDENTAL_WITNESS_HALF_WIDTH_SPACES = 1.3   # how far right to look
ACCIDENTAL_WITNESS_HALF_HEIGHT_SPACES = 0.6  # around the accidental's own y


def _lowconf_rescue_witnesses(c: Any, existing: Sequence[Any],
                              half_step: Optional[float], *,
                              log: Optional[Log] = None,
                              subject: Optional[Subject] = None,
                              frame: Optional[str] = None
                              ) -> List[Dict[str, Any]]:
    """Every witness already on the record for cell `c` that PREDICTS where
    a notehead must be: a stem end (classical-CV, re-run directly -- this
    cell has no `Q.STEM` row yet, since this reader runs before
    `gather_cv_lines` in the pipeline), a tie/slur end, or an accidental's
    right side (both read off `existing`, the production-floor detections
    already filed for this cell).

    Each witness is a half-open window: `kind`, `x_lo`/`x_hi`/`y_lo`/`y_hi`
    in the cell's own CANONICAL frame -- the same frame `d.x_canonical` etc.
    are measured in, so a candidate box's own centre can be compared
    directly, with no second conversion to agree with the raw boxes this
    reader also reads (CLAUDE.md §10: measure locally).

    ⚠️ ROADMAP 2.60: a stem reader that THROWS is filed on `log` (when the
    caller passes one) as the rescue's own `Q.GLYPH_BOX` abstention,
    `READER_UNAVAILABLE` with the exception class -- the witness set is then
    missing its stems, which is *cannot tell*, not *this bar has no stems*.
    """
    witnesses: List[Dict[str, Any]] = []
    if not half_step:
        return witnesses
    space = half_step * 2.0

    try:
        from ..line_detection import detect_lines, staged_stem_finder
        found = detect_lines(c, candidates_out=None, noteheads=None,
                             stem_finder=staged_stem_finder()) or {}
        stems = found.get("stems") or []
    except Exception as exc:                                  # noqa: BLE001
        if log is not None and subject is not None:
            log.abstain(subject, Q.GLYPH_BOX, reader=READERS.RESCUE_LOWCONF,
                        frame=frame or frame_cell(c.measure_index),
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=type(exc).__name__, witness_kind="stem_end")
        stems = []
    dx = STEM_WITNESS_HALF_WIDTH_SPACES * space
    dy = STEM_WITNESS_HALF_HEIGHT_SPACES * space
    for s in stems:
        x_c = s.x_canonical + s.width_canonical / 2.0
        y_top = s.y_canonical
        y_bot = s.y_canonical + s.height_canonical
        for end_y in (y_top, y_bot):
            witnesses.append({"kind": "stem_end",
                              "x_lo": x_c - dx, "x_hi": x_c + dx,
                              "y_lo": end_y - dy, "y_hi": end_y + dy})

    adx = ARC_WITNESS_HALF_WIDTH_SPACES * space
    ady = ARC_WITNESS_HALF_HEIGHT_SPACES * space
    for d0 in existing:
        name = str(getattr(d0, "smufl_name", "")).lower()
        if name not in ("tie", "slur"):
            continue
        x0 = d0.x_canonical
        x1 = x0 + d0.width_canonical
        y_bottom = d0.y_canonical + d0.height_canonical
        witnesses.append({"kind": f"{name}_end",
                          "x_lo": x0 - 2 * adx, "x_hi": x0,
                          "y_lo": y_bottom - ady, "y_hi": y_bottom + ady})
        witnesses.append({"kind": f"{name}_end",
                          "x_lo": x1, "x_hi": x1 + 2 * adx,
                          "y_lo": y_bottom - ady, "y_hi": y_bottom + ady})

    acdx = ACCIDENTAL_WITNESS_HALF_WIDTH_SPACES * space
    acdy = ACCIDENTAL_WITNESS_HALF_HEIGHT_SPACES * space
    for d0 in existing:
        if getattr(d0, "category", None) != "accidental":
            continue
        right_x = d0.x_canonical + d0.width_canonical
        cy = d0.y_canonical + d0.height_canonical / 2.0
        witnesses.append({"kind": "accidental_right",
                          "x_lo": right_x, "x_hi": right_x + 2 * acdx,
                          "y_lo": cy - acdy, "y_hi": cy + acdy})
    return witnesses


def _matching_witness(d: Any, witnesses: Sequence[Dict[str, Any]]
                      ) -> Optional[Dict[str, Any]]:
    cx = d.x_canonical + d.width_canonical / 2.0
    cy = d.y_canonical + d.height_canonical / 2.0
    for w in witnesses:
        if w["x_lo"] <= cx <= w["x_hi"] and w["y_lo"] <= cy <= w["y_hi"]:
            return w
    return None


def gather_lowconf_rescue(log: Log, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]], *,
                         detector: Any = None,
                         imgsz: Optional[int] = None,
                         progress: bool = False) -> None:
    """Re-run the SAME detector, on ONE cell, at `RESCUE_CONF_FLOOR` --
    notehead/rest classes ONLY -- for a bar `_empty_bar_candidate_cells`
    already calls boxless (no notehead/rest box at the production floor)
    and that 2.52's own ink search (`Q.EMPTY_BAR_REST_SEARCH`) did NOT find
    a whole rest in.

    ROADMAP 2.53 diagnosed this population by hand: 28 of 29 Litolff p3
    not-found cells already carry SOME detector box (ties, ledger lines,
    beams, slurs, fermatas, cautionary clefs) -- never a whole-cell miss,
    only the notehead/rest CLASS is missing under crossing ink. Sean,
    DECISIONS 2026-10-01, on that diagnosis: *"Yes"* to a second,
    lower-confidence pass restricted to those two classes, with every
    rescued box passing the usual ADJUDICATE checks and crop-checked before
    anything ships.

    ⚠️ GUIDED, NOT A BARE CONFIDENCE DROP (Sean's SAME-DAY refinement,
    DECISIONS 2026-10-01: *"Every measure should have notes or rests. If
    the bar shows ties then there are notes; if there are stems then there
    are notes ... If there are ties the notes will be close to the end of
    the ties. If there are accidentals then there are notes."*). A rescued
    box is kept only when it falls inside `_lowconf_rescue_witnesses`'s own
    window around a STEM end, a TIE/SLUR end, or an ACCIDENTAL's right side
    -- `_matching_witness`. An unguided low-confidence box (no witness)
    is rejected and recorded as such (`ABSTAIN.RESCUE_UNGUIDED`); a
    witness with no box near it, even at `RESCUE_CONF_FLOOR`, is OUR
    failure and is recorded too (`ABSTAIN.WITNESS_UNMET`) -- never read as
    "nothing to find here".

    ⚠️ NEVER TOUCHES A BAR THAT ALREADY HAS A NOTE OR REST. The candidate
    set is `_empty_bar_candidate_cells`'s own (identical to 2.52's), so a
    cell with ANY notehead/rest box at the production floor is invisible to
    this reader by construction -- it is never even considered, not merely
    declined.

    ⚠️ NEVER RESCUES A BAR 2.52 ALREADY READ. 2.52's own GATHER row
    (`Q.EMPTY_BAR_REST_SEARCH`) is the one true answer to "did the ink
    search already find a whole rest here", and this reader READS IT OFF
    `log` (rule 6: a connection, never a second copy of the test). Until
    2026-10-06 the search ran AFTER this reader in `gather()`, so this
    function re-ran it on a throwaway `Log` -- twice the work, and an
    answer the record never held. `gather()` now runs the search first.

    ⚠️ AND IT REFUSES TO RUN WHERE THE SEARCH HAS NOT FILED. With ink on,
    `gather_empty_bar_rest_search` files a row or a refusal for EVERY
    candidate cell, so a candidate with neither means this reader was
    called before the search -- the silent misorder `log.rows()` would
    otherwise turn into "not found, rescue everything". That raises
    (`GatherOrderError`) rather than proceeding: a control that can fail
    (rule 7). With ink OFF the search files nothing by design and the rescue
    proceeds on every candidate, exactly as it did against an empty scratch
    log before.

    ⚠️ FILED AS GLYPH BOXES, FROM THEIR OWN READER NAME
    (`READERS.RESCUE_LOWCONF`), NEVER `READERS.DETECTOR`. Every rescued box
    is appended to this cell's own `detections` list (mutated IN PLACE, at
    an index past every box the production pass already assigned) so every
    later GATHER reader that walks `detections[cell_key]` by index --
    notehead position, ownership evidence, rhythm marks, the ink/ledger/
    stem/stacked-head readers -- sees it exactly as it would see any other
    glyph. Every row this reader files carries `reader=RESCUE_LOWCONF` and
    `score`, so it is traceable and separable from a production-floor box
    without needing to read the score's own value.

    ⚠️ GATHER RECORDS THESE ROWS ALWAYS, REGARDLESS OF `RESCUE_SHIPS`.
    Whether ADJUDICATE may USE a rescued glyph in any decision's domain is
    `adjudicate.subjects_for`'s own question, not this function's.
    """
    if detector is None:
        return
    candidates = _empty_bar_candidate_cells(cells, local, detections)
    if not candidates:
        return
    search_ran = _ink_enabled()

    for c in candidates:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sys_idx, st_idx = key
        p = c.page_index
        cell_sub = R.cell(p, sys_idx, st_idx, c.measure_index)
        frame = frame_cell(c.measure_index)
        cell_key = cell_sub.to_key()

        # ⚠️ THE REAL LOG, not a scratch one -- see the docstring. The
        # candidate set is the search's own (both computed off the
        # pre-mutation `detections`), so with ink on every cell here holds
        # a row or a refusal from `READERS.CV_REST_SEARCH`, or the search
        # has not run yet.
        search_rows = log.rows(Q.EMPTY_BAR_REST_SEARCH, cell_sub)
        if search_ran and not search_rows \
                and not log.refusals(Q.EMPTY_BAR_REST_SEARCH, cell_sub):
            raise GatherOrderError(
                f"gather_lowconf_rescue ran before "
                f"gather_empty_bar_rest_search at {cell_key}: the rescue "
                f"reads Q.EMPTY_BAR_REST_SEARCH and it is not on the record")
        if any(bool(row.value) for row in search_rows):
            continue

        existing = detections.get(cell_key)
        if existing is None:
            existing = []
            detections[cell_key] = existing
        n_existing = len(existing)

        grid = _cell_grid(c)
        half_step = grid[1] if grid else None
        witnesses = _lowconf_rescue_witnesses(c, existing, half_step,
                                              log=log, subject=cell_sub,
                                              frame=frame)
        if not witnesses:
            # ⚠️ No witness at all -- "every measure should have notes or
            # rests" names stems/ties/accidentals as the witnesses; a bar
            # with none of them gives this reader nothing to be guided by,
            # and it must not fall back to accepting on score alone.
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.RESCUE_LOWCONF,
                        frame=frame, reason=ABSTAIN.NO_DETECTIONS,
                        witnesses_found=0)
            continue

        rerun = detector.detect(c, conf_threshold=RESCUE_CONF_FLOOR,
                                imgsz=imgsz)
        candidates_by_class = [
            d for d in rerun
            if str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)
            or str(d.smufl_name).lower().startswith(_REST_PREFIX)]

        matched_witness_ids = set()
        kept: List[Tuple[Any, Dict[str, Any]]] = []
        for d in candidates_by_class:
            w = _matching_witness(d, witnesses)
            if w is None:
                log.abstain(cell_sub, Q.GLYPH_BOX,
                            reader=READERS.RESCUE_LOWCONF, frame=frame,
                            reason=ABSTAIN.RESCUE_UNGUIDED,
                            smufl_name=d.smufl_name, score=float(d.confidence))
                continue
            kept.append((d, w))
            matched_witness_ids.add(id(w))

        for w in witnesses:
            if id(w) not in matched_witness_ids:
                log.abstain(cell_sub, Q.GLYPH_BOX,
                            reader=READERS.RESCUE_LOWCONF, frame=frame,
                            reason=ABSTAIN.WITNESS_UNMET,
                            witness_kind=w["kind"])

        for k, (d, w) in enumerate(kept):
            gi = n_existing + k
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, gi)
            page_box = _page_box(c, d)
            box_detail: Dict[str, Any] = {"category": d.category,
                                          "witness": w["kind"]}
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
                        reader=READERS.RESCUE_LOWCONF, frame=frame,
                        score=float(d.confidence), **box_detail)
            log.observe(g, Q.GLYPH_CONF, float(d.confidence),
                        reader=READERS.RESCUE_LOWCONF, frame=frame,
                        score=float(d.confidence))
            if d.smufl_name.startswith(_NOTEHEAD_PREFIX):
                log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name,
                            reader=READERS.RESCUE_LOWCONF, frame=frame,
                            score=float(d.confidence))
            existing.append(d)
        if progress:
            print(f"  gather lowconf rescue {cell_key}: "
                  f"{len(kept)} box(es) of {len(candidates_by_class)} "
                  f"candidate(s), {len(witnesses)} witness(es)")


#: ROADMAP 2.138 (`OMR_WEDGE_RESCUE`, default ON since 2026-10-15). Sean's four misses on the 2.109 crops of Brahms p24 (a staccatissimo wedge printed over
#: a head, never written) are not a reading fault: the production detector DID draw a box on each, at confidence 0.138-0.165 (one at
#: 0.05, as `augmentationDot`), under the 0.25 floor every reader trusts (`benchmarks/omr-staccatissimo-2026-10/FINDINGS.md` Sec.9).
#: This is the 2.53 pattern for marks: the SAME detector re-run on the cell at a lower floor, a box kept only where it is guided -- its
#: ink is a wedge by 2.131's own measurement and a head stands on the side its point faces (the head the mark would own).
#: CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a staccatissimo is a wedge whose point faces its head (Sean 2026-10-14,
#: 8 of 8 tiles); falsified by a Sean-read crop of a rescued box that is not a wedge over a head. The floor is a MEASUREMENT on one
#: score (Brahms p24), so it only NARROWS (flag OFF) until Sean's tiles.
WEDGE_RESCUE_ENV = "OMR_WEDGE_RESCUE"
WEDGE_RESCUE_FLOOR = 0.03
#: two boxes on one mark: centres within this many staff spaces, or boxes overlapping by this IoU
WEDGE_RESCUE_SAME_MARK_SPACES = 0.35
WEDGE_RESCUE_SAME_MARK_IOU = 0.2


def wedge_rescue_enabled() -> bool:
    """`OMR_WEDGE_RESCUE`, default ON (Sean 2026-10-15, ROADMAP 2.138, tiles 10/10); only an explicit off-word disables."""
    return os.environ.get(WEDGE_RESCUE_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


def _is_mark_class(name: str) -> bool:
    n = str(name)
    return (n.startswith("augmentationDot") or n in _STACCATO_CLASSES
            or n.startswith("articStaccatissimo"))


def _wedge_of_shape(m: Optional[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
    """2.131's wedge test (the adjudicator's own constants) on a `mark_shape_of_ink` dict -> (is_wedge, detail with the tip side)."""
    if not m:
        return False, {}
    from .adjudicators import rhythm as _rh
    top, bot = float(m["top"]), float(m["bot"])
    base = max(top, bot)
    taper = (min(top, bot) / base) if base else 1.0
    det = {"mark_hw": round(float(m["hw"]), 3), "mark_taper": round(taper, 3),
           "mark_tip": "bottom" if bot < top else "top",
           "mark_h_spaces": round(float(m["h_spaces"]), 3)}
    ok = (float(m["hw"]) >= _rh.WEDGE_MIN_HW and taper <= _rh.WEDGE_MAX_TAPER
          and _rh.WEDGE_MIN_HEIGHT_SPACES <= float(m["h_spaces"])
          <= _rh.WEDGE_MAX_HEIGHT_SPACES)
    return ok, det


def _canon_box(d: Any) -> Tuple[float, float, float, float]:
    return (float(d.x_canonical), float(d.y_canonical),
            float(d.x_canonical + d.width_canonical),
            float(d.y_canonical + d.height_canonical))


def _same_mark(a: Tuple[float, ...], b: Tuple[float, ...], space: float) -> bool:
    acx, acy = (a[0] + a[2]) / 2.0, (a[1] + a[3]) / 2.0
    bcx, bcy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
    if max(abs(acx - bcx), abs(acy - bcy)) <= WEDGE_RESCUE_SAME_MARK_SPACES * space:
        return True
    return _iou(a, b) >= WEDGE_RESCUE_SAME_MARK_IOU


def gather_wedge_rescue(log: Log, cells: Sequence[Any],
                        local: Dict[int, Tuple[int, int]],
                        detections: Dict[str, List[Any]], *,
                        detector: Any = None, imgsz: Optional[int] = None,
                        progress: bool = False) -> None:
    """ROADMAP 2.138, flag `OMR_WEDGE_RESCUE` (the caller gates). STAGED GATHER; decides nothing.

    For every cell holding a production notehead, re-run the SAME detector at `WEDGE_RESCUE_FLOOR` and keep a mark-class box (dot,
    staccato, staccatissimo) only if (a) it is not a second box on a mark production already boxed, (b) the ink in it is a wedge by
    2.131's cut, measured on the cell's staff-free raster, and (c) a production notehead stands in its staccato window on the side the
    point faces. A kept box is APPENDED to the cell's `detections` (the 2.53 pattern: every later reader walking by index sees it)
    under `READERS.RESCUE_WEDGE`, with the witness head's glyph index and the shape numbers; a refused one is an abstention carrying its
    score, class and the numbers that refused it (so a near-miss can be shown to Sean). Two kept boxes on one mark keep the higher score.
    """
    if detector is None:
        return
    for c in cells or ():
        key = local.get(c.staff_index)
        if key is None:
            continue
        sys_idx, st_idx = key
        p = c.page_index
        cell_sub = R.cell(p, sys_idx, st_idx, c.measure_index)
        cell_key = cell_sub.to_key()
        existing = detections.get(cell_key)
        if not existing:
            continue
        heads = [(gi, d) for gi, d in enumerate(existing)
                 if str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)]
        if not heads:
            continue
        grid = _cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        if grid is None or img is None:
            continue
        space = grid[1] * 2.0
        frame = frame_cell(c.measure_index)
        prod_marks = [_canon_box(d) for d in existing if _is_mark_class(d.smufl_name)]
        from .adjudicators import rhythm as _rh
        rerun = detector.detect(c, conf_threshold=WEDGE_RESCUE_FLOOR, imgsz=imgsz)
        kept: List[Tuple[Any, Dict[str, Any]]] = []
        for d in sorted((x for x in rerun if _is_mark_class(x.smufl_name)),
                        key=lambda x: -float(x.confidence)):
            box = _canon_box(d)
            if float(d.confidence) >= 0.25 or any(
                    _same_mark(box, pm, space) for pm in prod_marks):
                continue            # production already has this mark (or it is above the floor and was judged there)
            if any(_same_mark(box, _canon_box(k), space) for k, _ in kept):
                continue            # the same mark boxed twice below the floor: the higher score came first
            xywh = (box[0], box[1], box[2] - box[0], box[3] - box[1])
            m = mark_shape(img, xywh, space)
            is_wedge, wdet = _wedge_of_shape(m)
            refuse = None
            witness = None
            if not is_wedge:
                refuse = "not_a_wedge"
            else:
                tip_below = wdet["mark_tip"] == "bottom"
                mcy = (box[1] + box[3]) / 2.0
                best = None
                for gi, hd in heads:
                    hb = (float(hd.x_canonical), float(hd.y_canonical),
                          float(hd.width_canonical), float(hd.height_canonical))
                    if not _rh._in_staccato_window(xywh, hb, space):
                        continue
                    hcy = hb[1] + hb[3] / 2.0
                    if (hcy > mcy) != tip_below:
                        continue
                    dist = (hb[0] + hb[2] / 2.0 - (box[0] + box[2]) / 2.0) ** 2 + (hcy - mcy) ** 2
                    if best is None or dist < best[0]:
                        best = (dist, gi)
                if best is None:
                    refuse = "no_head_on_the_points_side"
                else:
                    witness = best[1]
            if refuse is not None:
                log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.RESCUE_WEDGE,
                            frame=frame, reason=ABSTAIN.RESCUE_UNGUIDED,
                            why=refuse, smufl_name=d.smufl_name,
                            score=float(d.confidence), **wdet)
                continue
            kept.append((d, {"witness_head": witness, **wdet}))
        n_existing = len(existing)
        for k, (d, info) in enumerate(kept):
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, n_existing + k)
            page_box = _page_box(c, d)
            box_detail: Dict[str, Any] = {"category": d.category, **info}
            if page_box is not None:
                px0, py0, px1, py1 = page_box
                box_detail.update(bbox_page_px=[px0, py0, px1, py1],
                                  x_center_page=(px0 + px1) / 2.0,
                                  y_center_page=(py0 + py1) / 2.0)
            log.observe(g, Q.GLYPH_BOX,
                        (d.smufl_name, d.x_canonical, d.y_canonical,
                         d.width_canonical, d.height_canonical),
                        reader=READERS.RESCUE_WEDGE, frame=frame,
                        score=float(d.confidence), **box_detail)
            log.observe(g, Q.GLYPH_CONF, float(d.confidence),
                        reader=READERS.RESCUE_WEDGE, frame=frame,
                        score=float(d.confidence))
            existing.append(d)
        if progress and kept:
            print(f"  gather wedge rescue {cell_key}: {len(kept)} box(es)")


def gather_detector_views(log: Log, cells: Sequence[Any],
                          local: Dict[int, Tuple[int, int]],
                          detections: Dict[str, List[Any]], *,
                          detector: Any = None, progress: bool = False) -> None:
    """ROADMAP 2.172 (flag `OMR_DETECTOR_VIEWS`, default OFF; the caller gates). The SAME detector on the SAME cell image at other staff-space
    sizes (`detector_views.VIEWS`), anti-aliased, read at a few sub-pixel phases with the median kept, only the families each view is for,
    merged family-aware into the cell's production boxes (`detector_views.merge_into_production`): a production box is never changed or
    dropped, a view box is appended only where no production box of its family stands and no production box of another family stands there
    with at least its confidence.

    Each kept box is appended to the cell's `detections` (the rescue's pattern, so every later reader and every ADJUDICATE gate sees it as any
    other glyph) with `Q.GLYPH_BOX` / `Q.GLYPH_CONF` (/ `Q.NOTEHEAD_CLASS`) under `READERS.DETECTOR_VIEW`, `score` the median confidence,
    and `view`, `staff_space_px`, `anti_alias`, `phases_found`, `n_phases`, `phase_confs`, `family` on the box row. A box a view found and the
    merge refused is filed as an abstention on the cell (`ABSTAIN.AMBIGUOUS`, `why` the merge's reason, candidate class and median) -- the
    near-miss is on the record, never invented. Runs AFTER the rescues (a rescued box is production's reading, so a view box over it is not
    "unseen") and BEFORE every reader that walks `detections`."""
    from . import detector_views as DV
    if detector is None or not hasattr(detector, "detect_view"):
        return
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sys_idx, st_idx = key
        p = c.page_index
        cell_sub = R.cell(p, sys_idx, st_idx, c.measure_index)
        frame = frame_cell(c.measure_index)
        cell_key = cell_sub.to_key()
        existing = detections.get(cell_key) or []
        try:
            out = DV.views_for_cell(detector, c, existing)
        except Exception as exc:                                  # noqa: BLE001
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.DETECTOR_VIEW, frame=frame,
                        reason=ABSTAIN.READER_UNAVAILABLE, error=type(exc).__name__)
            continue
        if out is None:
            continue
        for rf in out["refused"]:
            if rf["why"] == "production_same_family":
                continue        # production already boxed that symbol in that family: thousands of rows, no near-miss in them
            d = rf["det"]
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.DETECTOR_VIEW, frame=frame, reason=ABSTAIN.AMBIGUOUS,
                        why=rf["why"], view=rf["view"], candidate_class=d.smufl_name, score=float(rf["conf"]),
                        family=rf["family"], phases_found=rf["phases"],
                        box_canonical=[d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical])
        if not out["kept"]:
            continue
        lst = detections.get(cell_key)
        if lst is None:
            lst = []
            detections[cell_key] = lst
        n0 = len(lst)
        for k, kb in enumerate(out["kept"]):
            d = kb["det"]
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, n0 + k)
            page_box = _page_box(c, d)
            box_detail: Dict[str, Any] = {
                "category": d.category, "source": "detector_view", "view": kb["view"],
                "staff_space_px": kb["staff_space_px"], "anti_alias": kb["anti_alias"], "n_phases": kb["n_phases"],
                "phases_found": kb["phases"], "phase_confs": kb["phase_confs"], "family": kb["family"]}
            if page_box is None:
                box_detail["frame_note"] = "no page box: cell has no bbox_page_px/upscale_factor"
            else:
                px0, py0, px1, py1 = page_box
                box_detail.update(bbox_page_px=[px0, py0, px1, py1],
                                  x_center_page=(px0 + px1) / 2.0, y_center_page=(py0 + py1) / 2.0)
            log.observe(g, Q.GLYPH_BOX, (d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical),
                        reader=READERS.DETECTOR_VIEW, frame=frame, score=float(d.confidence), **box_detail)
            log.observe(g, Q.GLYPH_CONF, float(d.confidence), reader=READERS.DETECTOR_VIEW, frame=frame, score=float(d.confidence))
            if d.smufl_name.startswith(_NOTEHEAD_PREFIX):
                log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name, reader=READERS.DETECTOR_VIEW, frame=frame, score=float(d.confidence))
            lst.append(d)
        if progress:
            print(f"  gather detector views {cell_key}: {len(out['kept'])} box(es), {len(out['refused'])} refused, {out['calls']} view call(s)")


def gather_stem_end_heads(log: Log, cells: Sequence[Any],
                          local: Dict[int, Tuple[int, int]],
                          detections: Dict[str, List[Any]], *,
                          detector: Any = None, imgsz: Optional[int] = None,
                          progress: bool = False) -> None:
    """ROADMAP 2.179 (flag `OMR_STEM_END_HEADS`, default ON; the caller gates). STAGED GATHER; decides nothing.

    For every cell: its CV stems (the 2.55 rescue's call); a stem with no head box at either end is an orphan; for a cell holding one,
    the SAME detector is re-run at `stem_end_heads.FLOOR` and a head-class box (or a block rest box, re-read as a black head) whose
    centre stands at an orphan stem's end on the convention's side is APPENDED to the cell's `detections` under
    `READERS.RESCUE_STEM_HEAD`, with the stem, the end, the detector's own class (`read_from`) and score on the row. A candidate standing
    on a box of another family at least as confident is filed as an abstention (`ABSTAIN.AMBIGUOUS`). Production boxes are never changed.
    `stem_end_heads` holds the rule, the convention and what would falsify it."""
    from . import stem_end_heads as SEH
    if detector is None:
        return
    from ..line_detection import detect_lines, staged_stem_finder
    for c in cells or ():
        key = local.get(c.staff_index)
        if key is None:
            continue
        grid = _cell_grid(c)
        if grid is None:
            continue
        sys_idx, st_idx = key
        p = c.page_index
        cell_sub = R.cell(p, sys_idx, st_idx, c.measure_index)
        cell_key = cell_sub.to_key()
        frame = frame_cell(c.measure_index)
        existing = detections.get(cell_key) or []
        try:
            stems = (detect_lines(c, candidates_out=None, noteheads=None, stem_finder=staged_stem_finder()) or {}).get("stems") or []
        except Exception as exc:                                  # noqa: BLE001
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.RESCUE_STEM_HEAD, frame=frame,
                        reason=ABSTAIN.READER_UNAVAILABLE, error=type(exc).__name__)
            continue
        if not stems:
            continue
        heads = [SEH._box(d) for d in existing if SEH.is_head(d.smufl_name)]
        if not any(SEH.is_orphan(s, heads, 2.0 * grid[1]) for s in stems):
            continue
        rerun = detector.detect(c, conf_threshold=SEH.FLOOR, imgsz=imgsz)
        kept, refused, n_orph = SEH.candidates_for_cell(stems, existing, rerun, grid)
        for rf in refused:
            d = rf["det"]
            log.abstain(cell_sub, Q.GLYPH_BOX, reader=READERS.RESCUE_STEM_HEAD, frame=frame, reason=ABSTAIN.AMBIGUOUS,
                        why=rf["why"], candidate_class=d.smufl_name, score=float(rf["score"]), end=rf["end"],
                        box_canonical=[d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical])
        if not kept:
            continue
        lst = detections.get(cell_key)
        if lst is None:
            lst = []
            detections[cell_key] = lst
        n0 = len(lst)
        for k, kb in enumerate(kept):
            d = kb["det"]
            s = stems[kb["stem_index"]]
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, n0 + k)
            box_detail: Dict[str, Any] = {
                "category": d.category, "source": "stem_end_head", "read_from": kb["read_from"], "end": kb["end"],
                "from_record_box": bool(kb["from_record"]), "orphan_stems": n_orph,
                "stem_canonical": [s.x_canonical, s.y_canonical, s.width_canonical, s.height_canonical]}
            page_box = _page_box(c, d)
            if page_box is not None:
                px0, py0, px1, py1 = page_box
                box_detail.update(bbox_page_px=[px0, py0, px1, py1],
                                  x_center_page=(px0 + px1) / 2.0, y_center_page=(py0 + py1) / 2.0)
            log.observe(g, Q.GLYPH_BOX, (d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical),
                        reader=READERS.RESCUE_STEM_HEAD, frame=frame, score=float(d.confidence), **box_detail)
            log.observe(g, Q.GLYPH_CONF, float(d.confidence), reader=READERS.RESCUE_STEM_HEAD, frame=frame,
                        score=float(d.confidence))
            log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name, reader=READERS.RESCUE_STEM_HEAD, frame=frame,
                        score=float(d.confidence))
            lst.append(d)
        if progress:
            print(f"  gather stem-end heads {cell_key}: {len(kept)} box(es), {n_orph} orphan stem(s)")


def gather_second_hollow(log: Log, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]], *,
                         second_detector: Any = None,
                         conf_threshold: float = 0.25,
                         imgsz: Optional[int] = None,
                         progress: bool = False) -> None:
    """ROADMAP 2.114 (flag `OMR_SECOND_HOLLOW_DETECTOR`, default OFF; the caller gates). A SECOND detector -- 2.110's OLD arm, hollow
    classes ONLY (`second_hollow.HOLLOW_CLASSES`) -- run on the SAME cell at the SAME conf and imgsz production got, and recorded as a
    SEPARATE witness. It decides nothing, merges nothing, overwrites no production box and moves no production row.

      * a second box on a production NOTEHEAD box (IoU >= `SAME_HEAD_IOU`): `Q.SECOND_HOLLOW` on that glyph, `relation` `agrees`
        (production's class is hollow too) or `disagrees` (production boxed a black head);
      * a second box on a production box of ANOTHER class (a time-signature digit, a rest ...): production SAW something there -- an
        abstention (`ABSTAIN.AMBIGUOUS`, `relation` `over_other`), no glyph;
      * a second box on NOTHING: a glyph of its own, appended to this cell's `detections` (the rescue's pattern, so every later reader that
        walks `detections` by index sees it) with `Q.GLYPH_BOX` / `Q.GLYPH_CONF` / `Q.NOTEHEAD_CLASS` all under `READERS.SECOND_DETECTOR`
        and `Q.SECOND_HOLLOW` `relation` `second_only`.

    Runs AFTER the rescue (a rescued box is production's reading at a lower floor, so a second box over it is not "unseen") and BEFORE every
    reader that walks `detections` (the ink, ledger, stem and stacked-head readers). A detector that THROWS files `ABSTAIN.READER_UNAVAILABLE`
    with the exception class on the cell -- never read as "no hollow heads here"."""
    from . import second_hollow as SH
    if second_detector is None:
        return
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sys_idx, st_idx = key
        p = c.page_index
        cell_sub = R.cell(p, sys_idx, st_idx, c.measure_index)
        frame = frame_cell(c.measure_index)
        cell_key = cell_sub.to_key()
        try:
            second = second_detector.detect(c, conf_threshold=conf_threshold, imgsz=imgsz)
        except Exception as exc:                                  # noqa: BLE001
            log.abstain(cell_sub, Q.SECOND_HOLLOW, reader=READERS.SECOND_DETECTOR, frame=frame,
                        reason=ABSTAIN.READER_UNAVAILABLE, error=type(exc).__name__)
            continue
        if not second:
            continue
        existing = detections.get(cell_key)
        if existing is None:
            existing = []
            detections[cell_key] = existing
        plan = SH.plan_cell(existing, second)

        def _row_detail(d: Any, relation: str, **extra: Any) -> Dict[str, Any]:
            return dict(relation=relation, second_class=d.smufl_name, second_box=[float(v) for v in SH.box(d)],
                        second_score=float(d.confidence), **extra)

        for pi, d, overlap in plan["on_head"]:
            prod = existing[pi]
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, pi)
            relation = "agrees" if SH.is_hollow_family(prod.smufl_name) else "disagrees"
            log.observe(g, Q.SECOND_HOLLOW, d.smufl_name, reader=READERS.SECOND_DETECTOR, frame=frame,
                        score=float(d.confidence),
                        **_row_detail(d, relation, production_class=prod.smufl_name, iou=round(overlap, 4)))
        for pi, d, overlap in plan["over_other"]:
            log.abstain(cell_sub, Q.SECOND_HOLLOW, reader=READERS.SECOND_DETECTOR, frame=frame, reason=ABSTAIN.AMBIGUOUS,
                        production_class=existing[pi].smufl_name,
                        **_row_detail(d, "over_other", iou=round(overlap, 4)))
        n_existing = len(existing)
        for k, d in enumerate(plan["second_only"]):
            g = R.glyph(p, sys_idx, st_idx, c.measure_index, n_existing + k)
            page_box = _page_box(c, d)
            box_detail: Dict[str, Any] = {"category": d.category, "source": "second_detector"}
            if page_box is None:
                box_detail["frame_note"] = "no page box: cell has no bbox_page_px/upscale_factor"
            else:
                px0, py0, px1, py1 = page_box
                box_detail.update(bbox_page_px=[px0, py0, px1, py1],
                                  x_center_page=(px0 + px1) / 2.0, y_center_page=(py0 + py1) / 2.0)
            log.observe(g, Q.GLYPH_BOX, (d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical),
                        reader=READERS.SECOND_DETECTOR, frame=frame, score=float(d.confidence), **box_detail)
            log.observe(g, Q.GLYPH_CONF, float(d.confidence), reader=READERS.SECOND_DETECTOR, frame=frame,
                        score=float(d.confidence))
            log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name, reader=READERS.SECOND_DETECTOR, frame=frame,
                        score=float(d.confidence))
            log.observe(g, Q.SECOND_HOLLOW, d.smufl_name, reader=READERS.SECOND_DETECTOR, frame=frame,
                        score=float(d.confidence), **_row_detail(d, "second_only"))
            existing.append(d)
        if progress:
            print(f"  gather second hollow {cell_key}: {len(plan['on_head'])} on a head, "
                  f"{len(plan['second_only'])} second-only, {len(plan['over_other'])} over another class")


def _twin_head_members(c: Any, dets: Sequence[Any], half_step: float, cell_sub: Any) -> Dict[int, Dict[str, Any]]:
    """ROADMAP 2.212 (flag `OMR_TWIN_HEAD_MERGE`, default OFF) -- which notehead boxes are ONE head boxed more than once
    (`twin_head.twin_groups`): `{detection index: {"members": [glyph keys]}}`. It INVENTS NO POSITION (Sean 2026-10-01 /
    2026-10-27: the box centre is the hollow head's position, the ink ledgers place a head outside the staff): each member keeps
    the position its own reader gave it, and `export.twin_head_guess_of` marks the head GUESSED where the members' positions
    (far-head ledger read, else box centre) disagree."""
    from . import twin_head as _tw
    if not half_step or half_step <= 0:
        return {}
    idx = [gi for gi, d in enumerate(dets) if str(d.smufl_name).startswith(_NOTEHEAD_PREFIX)]
    if len(idx) < 2:
        return {}
    boxes = [(float(dets[gi].x_canonical), float(dets[gi].y_canonical), float(dets[gi].width_canonical),
              float(dets[gi].height_canonical)) for gi in idx]
    out: Dict[int, Dict[str, Any]] = {}
    for grp in _tw.twin_groups(boxes, float(half_step) * 2.0):
        mem = [idx[i] for i in grp]
        keys = [R.glyph(cell_sub.page, cell_sub.system, cell_sub.staff, cell_sub.cell, gi).to_key() for gi in mem]
        for gi in mem:
            out[gi] = {"members": keys}
    return out


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
            # ⚠️ A ONE-LINE PERCUSSION CELL HAS NO POSITION AND STILL HAS A
            # UNIT. `measure_extractor` writes `staff_line_spacing_canonical`
            # for exactly this case, in exactly this frame, because a consumer
            # deriving the unit from the GAPS between rows gets nothing from
            # one row and falls back to a constant written for another frame.
            one_line = getattr(c, "staff_line_spacing_canonical", None)
            if one_line:
                log.observe(sub, Q.CELL_STAFF_SPACE, float(one_line),
                            reader=READERS.GEOMETRY,
                            frame=frame_cell(sub.cell), lines=1)
            else:
                log.abstain(sub, Q.CELL_STAFF_SPACE, reader=READERS.GEOMETRY,
                            frame=frame_cell(sub.cell),
                            reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        top_y, half_step = grid
        # ⚠️ THE UNIT ITSELF, WRITTEN DOWN. `_cell_grid`'s own docstring
        # records that this arithmetic was computed inline and thrown away
        # once already; the half_step was then kept only INSIDE a notehead's
        # position, so a consumer asking "how many staff spaces is this
        # distance" had nothing to ask with -- and `adjudicate_duration`'s dot
        # window, expressed in staff spaces since 2026-09-01, could not be
        # evaluated at all. It is not a constant: see `Q.CELL_STAFF_SPACE`.
        log.observe(sub, Q.CELL_STAFF_SPACE, float(half_step) * 2.0,
                    reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                    half_step=float(half_step), lines=len(
                        list(getattr(c, "staff_line_ys_canonical", None) or [])))
        from . import twin_head as _tw
        twins = _twin_head_members(c, dets, half_step, sub) if _tw.enabled() else {}
        for gi, d in enumerate(dets):
            if not d.smufl_name.startswith(_NOTEHEAD_PREFIX):
                continue
            pos_float = (d.y_center - top_y) / half_step
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            # ⚠️ ROADMAP 2.73. A box that is half a hollow head cut by a line
            # centres half a head off the head: ITS centre reads a space where
            # the head sits ON the line. Where `gather_head_line_cut` found the
            # mirror hole in the ink, the head's own centre is the line, and
            # that is the position measured (the detector's own reading rides
            # on the row, so the move is visible and countable).
            cut_rows = log.rows(Q.HEAD_LINE_CUT, g)
            extra: Dict[str, Any] = {}
            if cut_rows:
                cut_pos = (cut_rows[-1].detail or {}).get("line_half_step_float")
                if cut_pos is not None:
                    extra = {"from_head_cut": cut_rows[-1].id,
                             "detector_position_float": round(pos_float, 3)}
                    pos_float = float(cut_pos)
            # ⚠️ ROADMAP 2.212 (flag `OMR_TWIN_HEAD_MERGE`, default OFF): boxes on ONE head name each other on the row; the
            # position stays each box's own (no new measurement). `export.twin_head_guess_of` compares them.
            tw = twins.get(gi)
            if tw is not None:
                extra["twin_head"] = {"members": tw["members"]}
            log.observe(g, Q.NOTEHEAD_STAFF_POSITION, pos_float,
                        reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                        residual=abs(pos_float - round(pos_float)),
                        rounded=int(round(pos_float)), **extra)


# ─────────────────────────────────────────────────────────────────────────────
# A far head's position, counted off its printed LEDGERS -- ROADMAP 2.56
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️ ROADMAP 2.56's own switch, DEFAULT ON for the overnight run (Sean's go,
#: 2026-10-04) and the ONLY way to put the geometry position back for every far
#: head. A DENY-LIST (CLAUDE.md §7): an empty value or a typo leaves it on.
FARHEAD_LEDGER_ENV = "OMR_FARHEAD_LEDGER"


def _farhead_ledger_enabled() -> bool:
    return os.environ.get(FARHEAD_LEDGER_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


#: ⚠️ ROADMAP 2.56b's own switch, DEFAULT OFF until Sean has seen the sheet: the
#: far-head note-first look is ALSO run toward each candidate staff (the head's
#: own and the next staff beyond it), filed as `Q.FAR_HEAD_OWNER_LEDGER`, and
#: `adjudicate_glyph_owner` reads it (Sean 2026-09-28: the ledgers name the
#: owner). A DENY-LIST (CLAUDE.md §7), default ON since 2026-10-07.
FARHEAD_OWNER_ENV = "OMR_FARHEAD_OWNER_LEDGERS"


def _farhead_owner_enabled() -> bool:
    """DEFAULT ON since 2026-10-07 (Sean). Deny-list."""
    return os.environ.get(FARHEAD_OWNER_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


class FarHeadState:
    """What the far-head reader carries ACROSS the pages of one gather.

    A page measures the head SIZE from its own clean on-line heads and, below
    `far_head_reader.MIN_PAGE_SHAPE_HEADS` of them (every page of the merging
    Litolff plate), falls back to the shape POOLED over the pages gathered so
    far -- the benchmark scorer's own document fallback. A page that has no
    shape yet is HELD (its raster with it) and read as soon as the pool
    reaches the minimum; `finish_far_head_ledger_positions` reads or abstains
    (`no_page_shape`) whatever is still held at the end of the run.
    """

    def __init__(self) -> None:
        self.pool: List[Dict[str, Any]] = []
        self.held: List[Tuple[Any, List[Dict[str, Any]]]] = []


def _far_head_not_a_note_evidence(log: Log, jobs: Sequence[Dict[str, Any]],
                                  cell_by_key: Dict[Any, Any]) -> Dict[str, Dict[str, Any]]:
    """lane-farhead-not-a-note (Sean 2026-10-05): what the record ALREADY holds about each far head that says its box
    may not be a notehead -- read, never measured here (CLAUDE.md rule 6). Per subject: the measure cell's page box,
    the measure cuts of its own staff (a cut is where `measure_partition` found a barline), 2.49's
    `Q.NOTEHEAD_STEM_CROSS_INK` detail. A verdict is never read here (GATHER precedes ADJUDICATE); a re-read of a
    FINISHED record may hand the reader its `Q.NOTEHEAD_IS_NOT_A_NOTEHEAD` verdict as `decided` itself.
    ⚠️ ORDER: this reads rows filed by `gather_notehead_stem_cross_ink`, so the far-head gather runs after it."""
    cuts: Dict[Tuple[int, int, int], set] = {}
    for (page, system, staff, _cell), c in cell_by_key.items():
        bb = getattr(c, "bbox_page_px", None)
        if bb:
            cuts.setdefault((page, system, staff), set()).update((float(bb[0]), float(bb[2])))
    out: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        g = R.glyph(job["page"], job["system"], job["staff"], job["cell"], job["glyph"])
        c = cell_by_key.get((job["page"], job["system"], job["staff"], job["cell"]))
        bb = getattr(c, "bbox_page_px", None) if c is not None else None
        ev: Dict[str, Any] = dict(
            cell_box=tuple(float(v) for v in bb) if bb else None,
            barline_xs=sorted(cuts.get((job["page"], job["system"], job["staff"]), ())))
        rows = log.rows(Q.NOTEHEAD_STEM_CROSS_INK, g)
        if rows:
            ev["cross"] = dict(rows[-1].detail or {})
        out[g.to_key()] = ev
    return out


def _file_far_head_reading(log: Log, job: Dict[str, Any], page_ctx: Any) -> bool:
    """Read one far head and FILE it: an Observation under `READERS.
    LEDGER_FARHEAD`, or an Abstention with a reason word. Returns whether a
    position was observed."""
    frame = job["frame"]
    # ⚠️ BUILT HERE, FROM ITS FIVE INTEGERS, so `wiring`'s AST walk can resolve
    # the observe site's subject kind (a subject handed in through a dict is an
    # UNRESOLVED gather site).
    g = R.glyph(job["page"], job["system"], job["staff"], job["cell"],
                job["glyph"])
    res = page_ctx.read(g.to_key(), job["box"], job["cls"], job["global_lines"])
    if res["pos"] is None:
        word = (ABSTAIN.NO_PAGE_SHAPE if res["reason"] == "no_page_shape"
                else ABSTAIN.LEDGER_NOT_READ)
        # lane-farhead-not-a-note: `ledger_reason` is `not_a_note:<why>` where the record's own evidence says the box
        # is something else; it abstains (never a position, never a deletion) and the reason is on the row
        log.abstain(g, Q.FAR_HEAD_LEDGER_POSITION, reader=READERS.LEDGER_FARHEAD,
                    frame=frame, reason=word, ledger_reason=res["reason"],
                    geometry_position=job["geometry_position"])
        _file_owner_ledger_readings(log, job, page_ctx, res)
        return False
    log.observe(g, Q.FAR_HEAD_LEDGER_POSITION, int(res["pos"]),
                reader=READERS.LEDGER_FARHEAD, frame=frame,
                ledger_reason=res["reason"], box_source=res["box_source"],
                shape_source=res.get("shape_source"),
                geometry_position=job["geometry_position"])
    _file_owner_ledger_readings(log, job, page_ctx, res)
    return True


def _file_owner_ledger_readings(log: Log, job: Dict[str, Any],
                                page_ctx: Any, own_res: Dict[str, Any]) -> None:
    """ROADMAP 2.56b: the note-first look toward EACH candidate staff, one
    `Q.FAR_HEAD_OWNER_LEDGER` row per candidate (an Observation where the
    ledgers toward it make a chain or none are needed, an Abstention where they
    do not). Runs only where the job carries `staves` (the flag was on)."""
    staves = job.get("staves")
    if not staves:
        return
    from ..annotate import far_head_owner as FO
    frame = job["frame"]
    own = job["own_key"]
    # ⚠️ BUILT HERE, FROM ITS FIVE INTEGERS, for `wiring`'s AST walk (see
    # `_file_far_head_reading`).
    g = R.glyph(job["page"], job["system"], job["staff"], job["cell"],
                job["glyph"])
    cands: List[Tuple[str, Dict[str, Any]]] = []
    # the head's own staff: the position read just made IS its reading
    cands.append((own, dict(
        fits=own_res["pos"] is not None, pos=own_res["pos"],
        reason=own_res["reason"], how="note_first",
        unread=FO.is_unread(own_res["reason"],
                            (own_res.get("detail") or {}).get("note_first")),
        geometry_position=job["geometry_position"])))
    nb = FO.neighbour_staff(job["box"], own, staves)
    if nb is not None:
        cands.append((nb["key"], FO.read_toward(
            page_ctx, g.to_key(), job["box"], job["cls"],
            FO.lines_at(nb, (job["box"][0] + job["box"][2]) / 2.0))))
    for key, rd in cands:
        if rd["fits"]:
            log.observe(g, Q.FAR_HEAD_OWNER_LEDGER, int(rd["pos"]),
                        reader=READERS.LEDGER_OWNER_NOTE_FIRST, frame=frame,
                        candidate=key,
                        ledger_reason=rd["reason"], how=rd["how"],
                        geometry_position=rd.get("geometry_position"))
        else:
            # ⚠️ "could not look" (`unread`: no head size, no staff lines) is
            # kept apart from "looked, and no chain of ledgers reaches this
            # staff": only the second is a refutation of that candidate.
            log.abstain(g, Q.FAR_HEAD_OWNER_LEDGER,
                        reader=READERS.LEDGER_OWNER_NOTE_FIRST, frame=frame,
                        reason=(ABSTAIN.NO_PAGE_SHAPE
                                if rd["reason"] == "no_page_shape"
                                else ABSTAIN.LEDGER_NOT_READ),
                        candidate=key,
                        unread=bool(rd.get("unread")),
                        ledger_reason=rd["reason"],
                        geometry_position=rd.get("geometry_position"))


def gather_far_head_ledger_positions(log: Log, pws: Any, cells: Sequence[Any],
                                     local: Dict[int, Tuple[int, int]],
                                     detections: Dict[str, List[Any]],
                                     state: Optional[FarHeadState] = None
                                     ) -> Dict[str, int]:
    """`Q.FAR_HEAD_LEDGER_POSITION` for every notehead OUTSIDE its staff's
    first space -- the position counted off the head's own printed ledgers.

    ⚠️ A SECOND WITNESS, NEVER AN OVERWRITE (CLAUDE.md rule 6). The geometry
    row `gather_notehead_positions` filed stays on the record untouched; this
    is a different quantity from a different reader, and
    `adjudicate_notehead_position` is what weighs them. A head the reader
    could not place is an ABSTENTION with a reason word, never a default.

    The reader is `tools.omr.annotate.far_head_reader` -- Sean's accepted arm
    E3 (round-8 ledgers + the exclusion rules + the template-sized head box).
    It reads the page's ORIGINAL raster (`pws.page.rgb`, the staff lines left
    in) and the staff lines AT THE HEAD'S OWN x (CLAUDE.md §10), in the page
    frame the boxes are already in. Returns a census `{far, observed,
    abstained, held}` for the caller and the tests.

    Pass the run's `FarHeadState` to share the size pool across pages; with
    none, this page stands alone and finishes itself.
    """
    census = {"far": 0, "observed": 0, "abstained": 0, "held": 0}
    if not _farhead_ledger_enabled():
        return census
    own_state = state is None
    state = state if state is not None else FarHeadState()
    rgb = getattr(getattr(pws, "page", None), "rgb", None)
    if rgb is None or getattr(rgb, "ndim", 0) < 2:
        return census
    from ..annotate import far_head_reader as FH
    import cv2

    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    # lane-farhead-per-bar-grid (Sean 2026-10-06): the lines a head is read
    # against start from the PER-BAR grid of ITS bar -- the very rows
    # `gather_notehead_positions` took its position from (`_cell_grid`'s
    # source) -- not the staff-wide raw lines, which sit off the ink by the
    # staff's tilt. Keyword `per_bar_grid` off = the raw lines, as before.
    per_bar = bool(FH.READER_KEYWORDS.get("per_bar_grid"))
    grid_by_staff: Dict[str, List[Tuple[float, float, List[float]]]] = {}
    if per_bar:
        for c in cells:
            key = local.get(c.staff_index)
            gl = FH.cell_grid_page_lines(c) if key is not None else None
            if gl is not None:
                grid_by_staff.setdefault(
                    R.staff(c.page_index, key[0], key[1]).to_key(), []
                ).append((float(c.bbox_page_px[0]), float(c.bbox_page_px[2]), gl))
    staff_lines: Dict[str, List[float]] = {}
    owner_on = _farhead_owner_enabled()
    owner_staves: List[Dict[str, Any]] = []
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is None:
            continue
        p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
        staff_lines[R.staff(p, key[0], key[1]).to_key()] = \
            [float(y) for y in st.line_ys]
        if owner_on and hasattr(st, "x_start"):   # a staff with no extent cannot be a candidate
            owner_staves.append(dict(
                key=R.staff(p, key[0], key[1]).to_key(),
                lines=[float(y) for y in st.line_ys],
                x0=float(st.x_start), x1=float(st.x_end),
                grid=grid_by_staff.get(R.staff(p, key[0], key[1]).to_key())))

    heads: List[Dict[str, Any]] = []
    page_boxes: List[Tuple[str, str, tuple]] = []
    jobs: List[Dict[str, Any]] = []
    used_staves: Dict[str, List[float]] = {}
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        own = R.staff(sub.page, sub.system, sub.staff).to_key()
        for gi, d in enumerate(dets):
            box = _page_box(c, d)
            if box is None:
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            page_boxes.append((g.to_key(), d.smufl_name, box))
            if not d.smufl_name.startswith(_NOTEHEAD_PREFIX):
                continue
            rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, g)
            lines = staff_lines.get(own)
            if not rows or lines is None:
                continue
            try:
                pos = int(round(float(rows[-1].value)))
            except (TypeError, ValueError):
                continue
            used_staves[own] = lines
            head_lines = (FH.cell_grid_page_lines(c) or lines) if per_bar else lines
            heads.append(dict(subject=g.to_key(), box=box, pos=pos,
                              cls=d.smufl_name, score=float(d.confidence),
                              global_lines=head_lines))
            if FH.lg.far_head_needs_ledger_read(pos):
                jobs.append(dict(page=sub.page, system=sub.system,
                                 staff=sub.staff, cell=sub.cell, glyph=gi,
                                 box=box, cls=d.smufl_name,
                                 global_lines=head_lines, geometry_position=pos,
                                 frame=frame_cell(sub.cell), own_key=own,
                                 staves=owner_staves if owner_on else None))
    if not jobs:
        return census
    census["far"] = len(jobs)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) if rgb.ndim == 3 else rgb
    ctx = FH.FarHeadPage(gray, heads, page_boxes, used_staves,
                         not_a_note=_far_head_not_a_note_evidence(log, jobs, cell_by_key))
    state.pool.extend(ctx.samples)
    pooled = FH.pooled_shape(state.pool)
    if ctx.shape is None and pooled is not None:
        ctx.adopt(pooled, f"document pool n={len(state.pool)}")
    if ctx.shape is None:
        state.held.append((ctx, jobs))
        census["held"] = len(jobs)
    else:
        for job in jobs:
            census["observed" if _file_far_head_reading(log, job, ctx)
                   else "abstained"] += 1
    # A pool that just reached the minimum frees every page held for want of it.
    if pooled is not None and state.held:
        still = []
        for hctx, hjobs in state.held:
            if hctx.shape is None and not hctx.adopt(
                    pooled, f"document pool n={len(state.pool)}"):
                still.append((hctx, hjobs))
                continue
            for job in hjobs:
                _file_far_head_reading(log, job, hctx)
        state.held = still
    if own_state:
        finish_far_head_ledger_positions(log, state)
    return census


def finish_far_head_ledger_positions(log: Log, state: FarHeadState) -> None:
    """End of the run: a page still held has no head size to read with -- it
    ABSTAINS (`no_page_shape`), and is counted, rather than borrow one."""
    from ..annotate import far_head_reader as FH
    pooled = FH.pooled_shape(state.pool)
    for hctx, hjobs in state.held:
        if hctx.shape is None and pooled is not None:
            hctx.adopt(pooled, f"document pool n={len(state.pool)}")
        for job in hjobs:
            _file_far_head_reading(log, job, hctx)
    state.held = []


# ─────────────────────────────────────────────────────────────────────────────
# The PRINTED in-bar accidental — ROADMAP 2.7
# ─────────────────────────────────────────────────────────────────────────────

#: The alteration each accidental CLASS states, in the vocabulary
#: `export._MXL_ACCIDENTAL` and `transcribe._parse_inline_accidental` already
#: share. ⚠️ KEYED ON THE CANONICAL NAME AND DERIVED FROM IT, never a
#: hand-copied class list: `class_aliases.canonicalize_names` is applied at
#: `gather_detections` (the one place the model's names are read), so what
#: arrives here is already canonical and `_alteration_of` tests the canonical
#: spelling. The double forms are FIRST because `doublesharp` contains
#: `sharp` and a prefix test in the other order reads every double sharp as a
#: single one -- which is the ordering `_parse_inline_accidental` has always
#: used and the reason it is copied rather than improved.
_ALTERATION_BY_NAME: Tuple[Tuple[str, str], ...] = (
    ("doublesharp", "##"),
    ("doubleflat", "bb"),
    ("sharp", "#"),
    ("flat", "b"),
    ("natural", "natural"),
)

#: ⚠️⚠️ `keyFlat` / `keySharp` / `keyNatural` ARE THE SIGNATURE'S OWN GLYPHS
#: AND ARE NOT IN-BAR ACCIDENTALS. The detector draws the distinction itself
#: and this honours it: 2,058 accidental-category boxes on the Litolff whole
#: movement, 527 of them `key*`, leaving exactly the **1,531** the roadmap
#: names. The legacy pair rule does NOT make this cut -- `keySharp`.lower()
#: contains `sharp`, so `_parse_inline_accidental` returns `#` for it and the
#: signature's own glyphs are offered a notehead -- and copying that here
#: would hand every staff's first note the last sharp of its key signature.
#: `Q.KEY_SIGNATURE` owns those glyphs; this owns the rest.
_KEY_SIGNATURE_PREFIX = "key"

#: Where in a glyph's box the pitch it names sits, as a fraction of the box
#: height from the TOP, by canonical class.
#:
#: ⚠️⚠️ FROM BRAVURA, WHICH IS AN EXTERNAL SOURCE AND NOT OUR OWN PAIRING.
#: `tools/omr/symbol_library/data/Bravura.otf` is the SMuFL reference font and
#: its glyph origin IS the staff position the accidental names, so the anchor
#: fraction is read off the outline's bounding box rather than fitted:
#: accidentalFlat 0.715, accidentalDoubleFlat 0.714 (both carry an ASCENDER
#: above the bowl), accidentalSharp 0.501, accidentalNatural 0.504,
#: accidentalDoubleSharp 0.504. Fitting it to our own accidental-to-notehead
#: pairs would be a default flipped on agreement with our own reading, which
#: rule 5 forbids -- so the font supplies the number and the measurement only
#: CORROBORATES it.
#:
#: ⚠️ AND THE CORROBORATION IS PARTIAL, WHICH IS WHY IT IS WRITTEN DOWN.
#: Estimated on accidentals with exactly ONE head in the x window (an
#: estimator that cannot select on the answer), the flat anchor measures
#: **0.692 on Breitkopf** -- within 0.023 of the font -- and **0.580 on
#: Litolff**, whose merging plate pulls the thin ascender out of the box.
#: Sharp and natural measure 0.495-0.505 on both, i.e. the font exactly. The
#: control: applying it collapses the second mode of the vertical-offset
#: histogram on both documents (Breitkopf 1,888 -> 724 glyphs in the 0.7-1.4
#: position band, Litolff 364 -> 234) and can therefore fail.
#:
#: ⚠️ A CLASS NOT NAMED HERE FALLS BACK TO THE BOX CENTRE, and that is the
#: honest default rather than a gap: a symmetric glyph's anchor IS its centre,
#: which is what the font says for three of the five.
_ANCHOR_FRACTION: Dict[str, float] = {
    "accidentalflat": 0.715,
    "accidentaldoubleflat": 0.714,
    "accidentalsharp": 0.501,
    "accidentalnatural": 0.504,
    "accidentaldoublesharp": 0.504,
}


def _alteration_of(name: str) -> Optional[str]:
    """The alteration a canonical accidental class states, or None."""
    s = (name or "").lower()
    if s.startswith(_KEY_SIGNATURE_PREFIX):
        return None
    for token, alteration in _ALTERATION_BY_NAME:
        if token in s:
            return alteration
    return None


def gather_accidental_positions(log: Log, cells: Sequence[Any],
                                local: Dict[int, Tuple[int, int]],
                                detections: Dict[str, List[Any]]) -> None:
    """The PRINTED accidental's own staff position, on the notehead's grid.

    ⚠️⚠️ THE LARGEST `FAMILY_Q_IS_ELSEWHERE` GAP IN THE TREE UNTIL 2026-09-23.
    1,531 accidental glyphs on the Litolff whole movement and 6,533 on the
    Breitkopf one reached `Q.GLYPH_BOX` and no typed row, so no adjudicator
    could be written about them, no abstention could be recorded, and every
    `<alter>` in every exported file came from the key signature alone --
    7,878 notes, 0 `<accidental>`.

    ⚠️ IT DECIDES NOTHING, and the split is the same one `gather_glyph_families`
    makes. WHICH notehead the glyph alters is a contest between heads with its
    own evidence and its own right to abstain (`adjudicate_accidental_owner`);
    what belongs here is only *this ink is an accidental of this kind, and here
    is the staff position it stands at*.

    ⚠️ THE CELL'S OWN CANONICAL FRAME IS CORRECT HERE, and the reason is the
    one `adjudicate_articulation_owner` states for itself: an accidental and
    the head it alters are cut from ONE cell, so they share a frame by
    construction. It is the CROSS-staff questions that need page pixels, and
    this is not one.

    ⚠️ NO ROW WHERE THE CELL HAS NO GRID. `gather_notehead_positions` abstains
    `no_staff_geometry` for the cell once, which speaks for every glyph in it;
    a second abstention per accidental would be the same reader filing the same
    silence twice, which `Evidence.correlated_groups` exists to stop counting.
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
            continue
        top_y, half_step = grid
        for gi, d in enumerate(dets):
            alteration = _alteration_of(d.smufl_name)
            fam = getattr(d, "accidental_family", None)        # ROADMAP 2.201 (flag OMR_ACCIDENTAL_FAMILY): one family, type from the strokes
            fam_detail: Dict[str, Any] = {}
            bx0, by0, bx1, by1 = float(d.x_canonical), float(d.y_canonical), float(d.x_canonical + d.width_canonical), float(d.y_canonical + d.height_canonical)
            if fam is not None:
                fam_alt = {"flat": "b", "natural": "natural", "sharp": "#"}.get(fam["type"])
                if fam_alt is not None:
                    alteration = fam_alt                      # the strokes name the type; the detector's label stays on the row as `detector_class`
                elif alteration is None and _acc_family.type_of_class(d.smufl_name) is not None:
                    alteration = {"flat": "b", "natural": "natural", "sharp": "#"}[_acc_family.type_of_class(d.smufl_name)]   # a key* box the strokes cannot type: its class as a candidate
                bx0, by0, bx1, by1 = [float(v) for v in fam["box"]]
                fam_detail = {"family": {k: fam[k] for k in ("type", "why", "margin", "features", "grown", "grown_sp", "detector_class", "detector_type",
                                                              "candidates", "agrees_with_detector", "head_right") if k in fam}}
            if alteration is None:
                continue
            if fam is not None and fam["type"] in _acc_family.TYPES:
                frac = float(fam["anchor_fraction"])
            else:
                frac = _ANCHOR_FRACTION.get(str(d.smufl_name).lower(), 0.5)
            anchor_y = by0 + (by1 - by0) * frac
            pos_float = (anchor_y - top_y) / half_step
            centre_pos = ((by0 + by1) / 2.0 - top_y) / half_step if fam is not None else (d.y_center - top_y) / half_step
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            shape_detail = _accidental_shape_detail(c, d, top_y, half_step) if _acc_shape.enabled() else {}
            log.observe(
                g, Q.ACCIDENTAL_STAFF_POSITION, pos_float,
                reader=READERS.GEOMETRY, frame=frame_cell(sub.cell),
                alteration=alteration,
                detector_class=str(d.smufl_name),
                anchor_fraction=frac,
                # ⚠️ THE UNCORRECTED READING, KEPT. The anchor is a claim about
                # the GLYPH SHAPE and the two documents disagree with the font
                # about it by 0.023 (Breitkopf) and 0.135 (Litolff) of a box
                # height; a consumer that wants to re-price that must not need
                # a re-gather to do it. Throwing the second reading away is
                # this project's own named anti-pattern.
                box_centre_position=centre_pos,
                residual=abs(pos_float - round(pos_float)),
                rounded=int(round(pos_float)),
                x0=bx0,
                x1=bx1,
                y0=by0,
                y1=by1,
                confidence=float(d.confidence),
                **({"one_ink_absorbed": True} if getattr(d, "one_ink_absorbed_by", None) is not None else _one_ink.box_detail(d)),
                **shape_detail, **fam_detail)


def _accidental_shape_detail(c: Any, d: Any, top_y: float, half_step: float) -> Dict[str, Any]:
    """ROADMAP 2.190 (flag `OMR_ACCIDENTAL_SHAPE`, default OFF): the shape of THIS accidental's own ink, measured on the cell's staff-erased
    raster (`staged/accidental_shape.py` has the rule, the cut-offs and why this is a second reader of the detector's raster, not a witness),
    plus the staff position the glyph would have under EACH class the detector offered for this ink (the winner and its merged rivals), so
    ADJUDICATE can pick among them without a re-gather. Measurement only: nothing here chooses. An absorbed box carries none (it is refused)."""
    if getattr(d, "one_ink_absorbed_by", None) is not None:
        return {}
    img = getattr(c, "image_no_staff", None)
    m = _acc_shape.measure(img, (float(d.x_canonical), float(d.y_canonical), float(d.width_canonical), float(d.height_canonical))) \
        if img is not None else None
    out: Dict[str, Any] = {"shape": {**(m or {}), **_acc_shape.classify(m)}}
    rivals = [str(r[0]) for r in (getattr(d, "one_ink_rivals", None) or ())]
    if _natural_candidate.enabled() and getattr(d, "natural_score", None) is not None \
            and not any(r.lower() == _natural_candidate.CLASS_NAME for r in [str(d.smufl_name)] + rivals):
        # ROADMAP 2.193: the sub-floor NATURAL candidate for this ink and the staff position a natural would anchor at on THIS box
        fr = _ANCHOR_FRACTION.get(_natural_candidate.CLASS_NAME, 0.5)
        out["natural_candidate"] = {"conf": float(d.natural_score), "alteration": "natural", "anchor_fraction": fr,
                                    "position": (d.y_canonical + d.height_canonical * fr - top_y) / half_step}
    pos: Dict[str, Dict[str, Any]] = {}
    for cls in [str(d.smufl_name)] + rivals:
        alt = _alteration_of(cls)
        if alt is None:
            continue
        fr = _ANCHOR_FRACTION.get(cls.lower(), 0.5)
        pos[cls] = {"alteration": alt, "position": (d.y_canonical + d.height_canonical * fr - top_y) / half_step, "anchor_fraction": fr}
    if rivals:
        out["position_by_class"] = pos
    return out


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

#: Two boxes are the same ink if they overlap MORE than this.
#:
#: ⚠️⚠️ IT RESTATED A MEASURED CONSTANT AT 0.5 WITH NO ASSUMPTION RECORD, AND
#: ROADMAP 2.6 PUT IT BACK. It cited `(A-OWN-3)`; `grep -rn A-OWN-3 tools/
#: benchmarks/ docs/` returned that line and nothing else. The same question is
#: answered on the legacy path — FROZEN, and the reference reader — by
#: `transcribe._CROSS_STAFF_DUPLICATE_IOU = 0.3`, SWEPT over three orchestral
#: works at 0.25/0.3/0.4/0.5 (`benchmarks/omr-orchestral-e2e/
#: DEDUPE_THRESHOLD.md`) and the LOWEST value costing no correctly-matched note
#: on any of them. The comparison is STRICT (`> CONTEST_IOU`) for the same
#: reason the value is 0.3: it is the legacy predicate, restored, not a new one.
#:
#: ⚠️ WHAT 0.5 COST, measured to the glyph before the change
#: (`benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §10): of the 161
#: near-neighbour noteheads on Litolff pp.1-4 that reached no contest at all,
#: 69 had a same-name twin overlapping on the near staff and 50 of those sat
#: ABOVE 0.3. Also measured earlier: 134 of 636 overlapping cross-staff groups
#: on the same record carried no `Q.GLYPH_OWNER` verdict at all, so both copies
#: were written with the ownership question never asked.
#:
#: ⚠️ IT MUST NOT GO BELOW 0.3. The sweep measured 0.25 merging genuinely
#: distinct neighbours, and it drops three correctly-matched notes on Brahms.
#: A clipped copy at IoU 0.1 is not a contest anyone can win, and a
#: clipping-tolerant overlap measure would be a new rule with no measurement
#: behind it.
CONTEST_IOU = 0.3

#: Expected ledger rungs between a notehead and its staff.
#: ⚠️ `+ 0.25` before truncation is NOT a fudge: a note sitting ON the first
#: ledger measures ~0.994 spacings, and plain truncation read that as needing
#: NO rung -- so the same note needed its ledger in one bar and not the next,
#: one pixel apart.
LEDGER_ROUND_UP = 0.25

#: ⚠️ lane-owner-from-staves (Sean, 2026-10-06), DEFAULT OFF until he has seen
#: `out/print/ledgers/owner_from_staves.png`. With it ON, GATHER (a) files the
#: head's LOCAL position against each candidate staff's own cell grid
#: (`local_position_in_candidate` on `Q.GLYPH_BAND_DISTANCE`) and (b) names a
#: staff whose band the head lies in -- or within `PAGE_EDGE_MARGIN_SPACES` of,
#: by the page-wide lines -- as a CANDIDATE even where it holds no box of this
#: ink; `adjudicate_glyph_owner` reads both (`ownership._owner_from_staves`).
#: DEFAULT ON since 2026-10-06 (Sean). A DENY-LIST (CLAUDE.md §7): a typo leaves it on.
OWNER_FROM_STAVES_ENV = "OMR_OWNER_FROM_STAVES"


def owner_from_staves_enabled() -> bool:
    return os.environ.get(OWNER_FROM_STAVES_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


#: ⚠️ MEASURED: how far a head's page-wide position can sit from its LOCAL one
#: (`Q.NOTEHEAD_STAFF_POSITION`, the cell's own grid) over every notehead on the
#: 10-06 records -- max 0.775 sp (Litolff) / 0.73 sp (Breitkopf), p99 0.64 / 0.36.
#: Inside the page-wide band by this much, a head is inside by any local grid;
#: nearer an edge only a local measure can say. One constant for both stages.
PAGE_EDGE_MARGIN_SPACES = 0.8


def _local_position_in_candidate(cells_of_staff, cand_key: str, cx: float,
                                 y: float) -> Optional[float]:
    """`y`'s position in half-steps from the TOP line of candidate `cand_key`'s
    own cell grid at the bar holding page x `cx` (`MeasureCell.
    staff_line_ys_canonical`, localized per cell -- CLAUDE.md §10: measure
    against the staff locally), or `None` -- DECLINED where no cell of that
    staff spans `cx` or the cell carries no five-line grid."""
    try:
        sub = Subject.from_key(cand_key)
    except ValueError:
        return None
    for c in cells_of_staff.get((sub.page, sub.system, sub.staff), ()):
        bb = getattr(c, "bbox_page_px", None)
        up = getattr(c, "upscale_factor", None)
        ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        if not bb or not up or len(ys) < 2 or not (bb[0] <= cx <= bb[2]):
            continue
        page_ys = [bb[1] + float(v) / up for v in ys]
        half = (page_ys[-1] - page_ys[0]) / (len(page_ys) - 1) / 2.0
        if half <= 0:
            return None
        return (y - page_ys[0]) / half
    return None


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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.58b -- ONE IDENTITY PER PHYSICAL MARK
# ─────────────────────────────────────────────────────────────────────────────

MARK_GROUPS_ENV = "OMR_MARK_GROUPS"
#: The overlap (page pixels) above which two boxes of one family are ONE mark.
#: The same figure the legacy `_CROSS_STAFF_DUPLICATE_IOU` was swept to (the
#: lowest value costing no matched note on three works) and the one
#: `export.SAME_INK_IOU` reads.
MARK_GROUP_IOU = 0.3
#: Families that are grouped. ⚠️ DYNAMICS ARE DELIBERATELY NOT HERE:
#: `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §6.3 measured the two `f`
#: of a printed `ff` at IoU 0.317 -- two real marks whose boxes overlap more
#: than the gate -- and the populations "do not separate"; a flat IoU rule
#: over them deletes real ink. Noteheads separate (§6.3), rests and
#: accidentals are single glyphs that cannot sit on one another.
MARK_GROUP_CATEGORIES = ("notehead", "rest", "accidental")


def mark_groups_enabled() -> bool:
    """`OMR_MARK_GROUPS` -- DEFAULT ON since 2026-10-07 (Sean). Deny-list."""
    return os.environ.get(MARK_GROUPS_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


def cluster_marks(items: Sequence[Dict[str, Any]]) -> List[List[int]]:
    """Connected components of `items` under IoU > `MARK_GROUP_IOU`.

    `items` carry `box` (page CORNERS), `category` and `scope` (page, system):
    only items with the same category AND scope are ever compared. Returns
    index lists, each sorted, ordered by the group's leftmost x then index, so
    the result is deterministic.
    """
    parent = list(range(len(items)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    buckets: Dict[Tuple[Any, Any], List[int]] = {}
    for i, it in enumerate(items):
        buckets.setdefault((it["category"], it["scope"]), []).append(i)
    for members in buckets.values():
        members.sort(key=lambda i: items[i]["box"][0])
        for a in range(len(members)):
            i = members[a]
            bi = items[i]["box"]
            for b in range(a + 1, len(members)):
                j = members[b]
                bj = items[j]["box"]
                if bj[0] >= bi[2]:
                    break
                if _iou(bi, bj) > MARK_GROUP_IOU:
                    parent[find(i)] = find(j)
    groups: Dict[int, List[int]] = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(i)
    return sorted((sorted(g) for g in groups.values()),
                  key=lambda g: (min(items[i]["box"][0] for i in g), g[0]))


def _file_mark_groups(log: Log, items: Sequence[Dict[str, Any]]) -> int:
    """One `Q.MARK_GROUP` row per item. Returns the number of groups."""
    seq: Dict[Tuple[int, int], int] = {}
    groups = cluster_marks(items)
    for g in groups:
        scope = items[g[0]]["scope"]
        n = seq[scope] = seq.get(scope, -1) + 1
        gid = f"mg/{scope[0]}/{scope[1]}/{n}"
        # the REPRESENTATIVE: the most confident member; ties go to the
        # lowest key so a rerun names the same one.
        rep = min(g, key=lambda i: (-(items[i]["conf"] or 0.0),
                                    items[i]["key"]))
        for i in g:
            it = items[i]
            extra: Dict[str, Any] = {}
            if len(g) > 1:
                extra["members"] = [items[j]["key"] for j in g]
            glyph = R.glyph(*it["coords"])
            log.observe(glyph, Q.MARK_GROUP, gid,
                        reader=READERS.GEOMETRY, frame=it["frame"],
                        family=it["category"], size=len(g),
                        rep=items[rep]["key"], **extra)
    return len(groups)


def gather_mark_groups(log: Log, cells: Sequence[Any],
                       local: Dict[int, Tuple[int, int]],
                       detections: Dict[str, List[Any]]) -> int:
    """ROADMAP 2.58b: file the physical-mark identity of every notehead, rest
    and accidental box of a page (`OMR_MARK_GROUPS`, default OFF).

    AFTER `gather_detections` and the low-confidence rescue (the box set is
    final), BEFORE every reader that could use the identity. It reads the
    detector's own PAGE boxes and decides nothing: no row is removed.
    """
    if not mark_groups_enabled():
        return 0
    by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    items: List[Dict[str, Any]] = []
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for gi, d in enumerate(dets):
            if d.category not in MARK_GROUP_CATEGORIES:
                continue
            box = _page_box(c, d)
            if box is None:
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            items.append({"coords": (sub.page, sub.system, sub.staff,
                                     sub.cell, gi),
                          "key": g.to_key(), "box": box,
                          "category": d.category,
                          "scope": (sub.page, sub.system),
                          "conf": float(d.confidence),
                          "frame": frame_cell(sub.cell)})
    return _file_mark_groups(log, items)


def mark_groups_from_log(log: Log) -> int:
    """The same grouping, off the `Q.GLYPH_BOX` rows already in an UNFROZEN
    log -- for a rebuilt record (`benchmarks/omr-local-staff-2026-09/
    mark_identity_rebuild.py`), which has no detector to re-run. One code
    path with `gather_mark_groups`: both end in `_file_mark_groups`."""
    items: List[Dict[str, Any]] = []
    for row in log.all_rows():
        if getattr(row, "quantity", None) != Q.GLYPH_BOX:
            continue
        if not hasattr(row, "detail") or not hasattr(row, "value"):
            continue
        cat = row.detail.get("category")
        box = row.detail.get("bbox_page_px")
        sub = row.subject
        if cat not in MARK_GROUP_CATEGORIES or not box:
            continue
        items.append({"coords": (sub.page, sub.system, sub.staff, sub.cell,
                                 sub.glyph),
                      "key": sub.to_key(), "box": tuple(box),
                      "category": cat, "scope": (sub.page, sub.system),
                      "conf": row.score, "frame": row.frame})
    return _file_mark_groups(log, items)


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
    # ⚠️ ROADMAP 2.6d: the staff's own measured line thickness, one dict
    # entry per candidate. ⚠️⚠️ `Staff.line_thickness_px` (what `gather_
    # geometry` files RAW under `Q.STAFF_SKEW.thickness_px`) is `list[float]
    # | None`, PER LINE top-to-bottom (`types.py:63`) -- `float()`ing it
    # crashed the first real gather this lane ran. `median_line_thickness_
    # px` (`types.py:73`) is the derived SCALAR `measure_extractor.py:1390`
    # already reuses for exactly this reason; read directly off `pws.staves`
    # rather than back through the record (GATHER decides nothing and reads
    # no verdict of its own).
    thickness_by_key: Dict[str, Optional[float]] = {}
    extent_by_key: Dict[str, Tuple[float, float]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is None:
            continue
        sub = R.staff(pws.page.page_index if hasattr(pws.page, "page_index")
                      else 0, key[0], key[1])
        sp = _spacing(st)
        if sp:
            geom[sub.to_key()] = ([float(y) for y in st.line_ys], float(sp))
            thickness_by_key[sub.to_key()] = getattr(
                st, "median_line_thickness_px", None)
            if owner_from_staves_enabled() and hasattr(st, "x_start") \
                    and hasattr(st, "x_end"):
                extent_by_key[sub.to_key()] = (float(st.x_start),
                                               float(st.x_end))

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

    # contests: same CATEGORY, different STAFF, same system, overlapping ink
    #
    # ⚠️⚠️ THE CLASS TEST READS `category`, NOT `smufl_name`, AND THAT IS
    # ROADMAP 2.6. `…OnLine` / `…InSpace` is the head's position RELATIVE TO A
    # STAFF -- the exact quantity a cross-staff contest exists to arbitrate --
    # so keying the identity test on the smufl NAME let one piece of ink be
    # ruled "not the same thing as itself" because the two cells disagreed
    # about the very fact in dispute. Measured on Litolff pp.1-4
    # (`benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §10): the name
    # test rejected 83 of the 161 never-contested near-neighbour noteheads, 38
    # of them the SAME head spelled two ways.
    #
    # ⚠️ IT CONNECTS, IT DOES NOT GUESS. `category` is already on every
    # `Q.GLYPH_BOX` row (`box_detail["category"] = d.category`, above) and this
    # is exactly the frozen reference reader's own predicate
    # (`transcribe._dedupe_cross_staff_detections`: `di["category"] !=
    # dj["category"]` and `IoU > 0.3`). The WINNER is still decided by
    # ladder -> range -> distance in `adjudicate_glyph_owner`, untouched.
    #
    # ⚠️ IT DOES NOT SETTLE THE HEAD TYPE. Two twins may be `noteheadBlack…`
    # and `noteheadHalf…`; both are `category="notehead"`, so the pair now
    # contests where it did not. The loser's row STAYS on the record -- export
    # refuses it, it is never deleted -- and `adjudicate_duration` reads
    # `Q.NOTEHEAD_CLASS` on the WINNER'S OWN subject (`rhythm._head_class`), so
    # the surviving duration is the reader's own reading of the surviving
    # detection and never the loser's type inherited in silence.
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
                if di.category != dj.category:
                    continue
                if _iou(bi, bj) <= CONTEST_IOU:
                    continue
                contests.setdefault(i, set()).add(gj.at(R.Kind.STAFF).to_key())
                contests.setdefault(j, set()).add(gi.at(R.Kind.STAFF).to_key())

    ledgers = _ledger_index(placed)

    # lane-owner-from-staves: with the flag ON, each candidate staff's cells
    # (for the head's LOCAL position) and the staves a head lies in or beside
    cells_of_staff: Optional[Dict[Tuple[int, int, int], List[Any]]] = None
    if owner_from_staves_enabled():
        cells_of_staff = {}
        for (page, system, staff, _m), c in cell_by_key.items():
            cells_of_staff.setdefault((page, system, staff), []).append(c)

    def _near_staves(g_: Subject, box_) -> set:
        """Other staves of this system whose band the head's centre lies in or
        within `PAGE_EDGE_MARGIN_SPACES` of (page-wide lines), x within the
        staff's extent plus a cell's pad. A CANDIDATE, never a verdict."""
        if cells_of_staff is None:
            return set()
        cx_, cy_ = (box_[0] + box_[2]) / 2.0, (box_[1] + box_[3]) / 2.0
        own_ = g_.at(R.Kind.STAFF).to_key()
        out_ = set()
        for k_, (ys_, sp_) in geom.items():
            if k_ == own_:
                continue
            s_ = Subject.from_key(k_)
            if (s_.page, s_.system) != (g_.page, g_.system):
                continue
            ext_ = extent_by_key.get(k_)
            if ext_ is None or not (ext_[0] - 2 * sp_ <= cx_ <= ext_[1] + 2 * sp_):
                continue
            if _band_distance_spaces(cy_, ys_, sp_) <= PAGE_EDGE_MARGIN_SPACES:
                out_.add(k_)
        return out_

    for i, others in sorted(contests.items()):
        _gather_owner_candidates(log, placed[i],
                                 others | _near_staves(placed[i][0], placed[i][1]),
                                 geom, ledgers, cell_by_key, thickness_by_key,
                                 cells_of_staff)

    # ─────────────────────────────────────────────────────────────────────
    # ROADMAP 2.37 (Sean, 2026-09-29 via the coordinator, quoted):
    # "there is no such thing as a far note with no ledger line" -- every
    # notehead beyond the space just outside the staff (not on the outer
    # line, not in the first space above/below it) ALWAYS has ledger lines
    # toward its own staff, standard engraving convention (Ross, "The Art
    # of Music Engraving", ledger-line practice; `docs/flags-2026-09.md`
    # carries no separate engraving-conventions file to cite instead).
    #
    # Before this, `_observe_ladder`/`_observe_ledger_rung_ink` ran ONLY
    # inside a cross-staff CONTEST (`contests`, above) -- a note the
    # padded cell reaches but with no overlapping same-category twin on a
    # neighbour staff never had its ladder walked at all, and was written
    # on its filed staff with the ownership question never raised (priced
    # 2026-09-29: 1,597 of 4,369 off-staff Litolff noteheads, 3,110 of
    # 9,110 Brahms -- roughly a third of the off-staff population on both
    # scans). A note with no rival candidate still gets its OWN ladder
    # walked, because Sean's convention is a claim about the PRINT, not
    # about whether a second box happens to exist: a clean (never
    # declined) absence at every one of its own required rungs is now
    # evidence the reader missed real ink, or that this is not really a
    # note at this position, or not really this far -- never silently
    # "fine because untested" (`adjudicators.ownership._ink_refutes_side`
    # reads it; CLAUDE.md rule 8, a fallback never converts "cannot tell"
    # into an answer, so the single-candidate case ABSTAINS rather than
    # guesses -- it never writes a different owner, there being none to
    # write).
    for i, (g, box, det) in enumerate(placed):
        if i in contests:
            continue                  # already walked above, with rivals
        if not det.smufl_name.startswith(_NOTEHEAD_PREFIX):
            continue                  # the ladder is a notehead-only question
        own = g.at(R.Kind.STAFF).to_key()
        lines_sp = geom.get(own)
        if lines_sp is None:
            continue                  # no geometry: nothing gathered before either
        line_ys, spacing = lines_sp
        y_center = (box[1] + box[3]) / 2.0
        if _ledger_expected(y_center, line_ys, spacing) <= 0:
            continue                  # on-staff or the exempt first space
        _gather_owner_candidates(log, (g, box, det), _near_staves(g, box), geom,
                                 ledgers, cell_by_key, thickness_by_key,
                                 cells_of_staff)


def _gather_owner_candidates(log: Log, placed_item, others: set,
                             geom: Dict[str, Tuple[List[float], float]],
                             ledgers, cell_by_key, thickness_by_key,
                             cells_of_staff=None) -> None:
    """The per-candidate GATHER body `gather_ownership_evidence` runs for one
    glyph, whether it came from a real cross-staff CONTEST (`others`
    non-empty) or ROADMAP 2.37's own-staff-only walk (`others` empty, a
    single candidate -- the glyph's own filed staff). One function so the
    two paths cannot drift apart -- see the call sites above."""
    g, box, det = placed_item
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
        extra: Dict[str, Any] = {}
        if cells_of_staff is not None:
            # lane-owner-from-staves: where the head sits against THIS
            # candidate's own cell grid at its x, not the page-wide fit
            lp = _local_position_in_candidate(
                cells_of_staff, cand_key, (box[0] + box[2]) / 2.0, y_center)
            if lp is not None:
                extra["local_position_in_candidate"] = lp
        log.observe(g, Q.GLYPH_BAND_DISTANCE,
                    _band_distance_spaces(y_center, line_ys, spacing),
                    reader=READERS.GEOMETRY, frame=FRAME_PAGE,
                    candidate=cand_key, own=(cand_key == own),
                    position_in_candidate=(y_center - min(line_ys)) / half,
                    **extra)
        if det.smufl_name.startswith(_NOTEHEAD_PREFIX):
            _observe_ladder(log, g, box, cand_key, line_ys, spacing,
                            ledgers)
            _observe_ledger_rung_ink(log, g, box, cand_key, line_ys,
                                     spacing, cell_by_key,
                                     thickness_by_key.get(cand_key),
                                     class_name=det.smufl_name)
            # ⚠️ ROADMAP 2.37 (Sean's redirect): the relative OWNERSHIP
            # witness, filed alongside the per-step ladder reader (still
            # gathered as a corroborating witness) rather than replacing
            # it -- `adjudicate_glyph_owner` decides which to trust.
            _observe_ledger_owner_density(log, g, box, cand_key, line_ys,
                                          spacing, cell_by_key,
                                          thickness_by_key.get(cand_key))


def _ledger_index(
    placed,
) -> Dict[Tuple[int, int], List[Tuple[float, float, float, str]]]:
    """Ledger-line detections per system, as (x0, x1, y_centre, glyph key).

    ⚠️ ROADMAP 2.14. The glyph key is `g.to_key()` -- THE SAME SUBJECT
    `adjudicate_ledger_is_not_a_ledger` decides on. Before this, the index
    carried only the rectangle and `_observe_ladder` filed `Q.GLYPH_LADDER`
    as an anonymous `found`/`expected` COUNT: a ledger refusal had nowhere to
    reach, because nothing on the record said WHICH ledger glyph a `found`
    rung was (`family_precision.adjudicate_ledger_is_not_a_ledger`'s own
    docstring names this as the finding 3.4g could not close). Carrying the
    key here is what lets `_observe_ladder` NAME the rungs it counted.
    """
    out: Dict[Tuple[int, int], List[Tuple[float, float, float, str]]] = {}
    for g, box, det in placed:
        if det.smufl_name != _LEDGER_CLASS:
            continue
        out.setdefault((g.page, g.system), []).append(
            (box[0], box[2], (box[1] + box[3]) / 2.0, g.to_key()))
    return out


def _ledger_expected(y: float, line_ys: Sequence[float],
                     spacing: float) -> int:
    """Ledger rungs required between `y` and the staff's outer line -- the
    ONE arithmetic every ladder reader in this file shares (`_observe_
    ladder`, `_observe_ledger_rung_ink`, and ROADMAP 2.37's own-staff-only
    walk in `gather_ownership_evidence`): 0 inside the staff or in the
    exempt first space just beyond it (Sean, 2026-09-29: standard
    engraving practice -- no ledger is printed there); `LEDGER_ROUND_UP`
    truncation for the rest, unchanged from before this function existed.

    ⚠️ 2026-09-29: a note past this boundary (`>= 1`) is Sean's *"there is
    no such thing as a far note with no ledger line"* -- the print ALWAYS
    carries every one of the `expected` rungs toward the note's TRUE
    staff. That claim is read in ADJUDICATE (`ownership._ink_refutes_
    side`), not here; this function only draws the SAME boundary GATHER
    already drew, factored so the new call site cannot compute it
    differently by a rounding slip.
    """
    if not spacing:
        return 0
    top, bottom = min(line_ys), max(line_ys)
    if top <= y <= bottom:
        return 0
    gap = (top - y) if y < top else (y - bottom)
    return int(gap / spacing + LEDGER_ROUND_UP)


def _observe_ladder(log: Log, g: Subject, box, cand_key: str,
                    line_ys: Sequence[float], spacing: float, ledgers) -> None:
    """⚠️ COMPLETENESS ONLY, NEVER COUNT.

    An unbroken run of rungs joins a note to its staff and outranks anything
    broken -- but TWO BROKEN LADDERS ARE NOT EVIDENCE EITHER WAY, because a
    found rung can belong to the other staff's note exactly as a gap can. On
    the Beethoven bassoon pair the ghost's single rung WAS the real C4's own
    ledger, and counting rungs beat the real note.

    ⚠️⚠️ ROADMAP 2.14 -- `rungs` NAMES THE GLYPH SUBJECT THAT MATCHED EACH
    COUNTED STEP, in the SAME ORDER `found` was counted in. `found` and
    `expected` are computed EXACTLY as before (same predicate, same
    iteration order, same first-match-wins semantics `any(...)` had) so this
    is a pure ADDITION to the row's detail, never a change to its `value`.
    The join this enables lives in ADJUDICATE
    (`adjudicators.ownership._ladder_complete`): a rung named here whose own
    `Q.LEDGER_IS_NOT_A_LEDGER` verdict is DECIDED `True` is discounted from
    `glyph_owner`'s completeness re-count; one that decision ABSTAINED on
    keeps its place, because CLAUDE.md rule 8 says *cannot tell* may never
    become *not a rung*.
    """
    y = (box[1] + box[3]) / 2.0
    top, bottom = min(line_ys), max(line_ys)
    expected = _ledger_expected(y, line_ys, spacing)
    if expected <= 0:
        return
    rungs = ledgers.get((g.page, g.system), [])
    x0, x1 = box[0], box[2]
    found = 0
    rung_keys: List[str] = []
    for k in range(1, expected + 1):
        want = (top - k * spacing) if y < top else (bottom + k * spacing)
        match_key = None
        for rx0, rx1, ry, rkey in rungs:
            if rx0 <= x1 and rx1 >= x0 and abs(ry - want) <= spacing * 0.5:
                match_key = rkey
                break
        if match_key is not None:
            found += 1
            rung_keys.append(match_key)
    log.observe(g, Q.GLYPH_LADDER, found == expected,
                reader=READERS.DETECTOR, frame=FRAME_PAGE,
                candidate=cand_key, expected=expected, found=found,
                rungs=rung_keys)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.6d -- ledger rungs the DETECTOR never boxed, read off the ink.
#
# `_observe_ladder` above counts a step as "found" only where a `ledgerLine`
# box landed on it. 2.6c.2's own crops (`benchmarks/omr-owner-domain-2026-09/
# FINDINGS.md` §2.6c.2) showed printed rungs in exactly that gap: on 2 of 8
# `far_no_rungs` crops the ledger lines ARE on the page and the detector drew
# no box at the step. This is a SECOND witness for the same fact --
# `Q.LEDGER_RUNG_INK`, one row per (head, candidate, step) -- read off the
# staff-erased raster the way `ledger_ink_under` already reads it for a
# BOXED rung (CLAUDE.md §9: erase for the CV consumer, never the detector).
# ─────────────────────────────────────────────────────────────────────────────

#: CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (2.6d). A
#: printed ledger line stands wider than the head it serves -- CLAUDE.md §10:
#: "a notehead is ~1.3 staff spaces wide" -- so the window tested is a
#: multiple of the HEAD's own measured width, not a fixed staff-space size:
#: falsified by a print-confirmed rung narrower than 1.5 head widths, or a
#: real gap (beam, stem, unrelated ink) this wide passing as one. NOT
#: CONFIRMED -- argued from CLAUDE.md's own notehead-width finding, never
#: measured against a ledger crop.
LEDGER_RUNG_INK_WIDTH_HEAD_MULT = 1.75
#: How far past the head's own edge, in HEAD WIDTHS, the CONTEXT window
#: reaches (used for the crop/background bands, not the overhang test
#: itself -- see `LEDGER_RUNG_INK_OVERHANG_TEST_FRAC` for why the two are
#: no longer the same span).
LEDGER_RUNG_INK_OVERHANG_HEAD_FRAC = 0.25
#: ⚠️⚠️ ROADMAP 2.6d CALIBRATION (2026-09-29). The overhang test used to
#: average density over the WHOLE span out to the context window's edge
#: (`head_w * 0.375`) -- and on the one real printed rung this lane found
#: on a positive-case re-gather (Breitkopf pdf idx 22, `glyph/22/1/6/10/2`
#: toward `staff/22/1/6`, step 2: a notehead with a ledger line visibly
#: crossing it, wings poking out both sides in the crop), that averaging
#: is what missed it -- `left=0.5126` against the `DENSE` floor of 0.55,
#: `right=0.6632` passing, on a rung whose wing is shorter than the window
#: tested. A NARROWER band anchored right at the head's edge (this
#: fraction of a head width, not the wider context span) tests where the
#: wing actually is instead of diluting it with the blank paper beyond a
#: short one. CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED:
#: 0.20 head widths is short enough to sit inside even a wing at the low
#: end of CLAUDE.md's "1.5-2 head widths" convention (0.25-0.5 each side)
#: without reaching the blank paper past a real one -- falsified by a
#: confirmed rung whose wing is shorter than 0.20 head widths, or by a
#: stem/serif this narrow a band now credits that the wider one refused.
LEDGER_RUNG_INK_OVERHANG_TEST_FRAC = 0.20
#: The thin band tested is the staff's own measured line thickness
#: (`Q.STAFF_SKEW`'s `thickness_px`, read here off the same `line_
#: thickness_px` attribute `gather_geometry` files it from -- one measurement,
#: two readers), padded this many spaces each side, mirroring `LEDGER_INK_
#: STROKE_PAD_SPACES`. NOT CONFIRMED: no staff on the two lanes' records
#: abstained its thickness, so the fallback below is UNTESTED.
LEDGER_RUNG_INK_THICKNESS_PAD_SPACES = 0.12
#: Where a staff's own thickness was never traced (`Q.STAFF_SKEW` abstained):
#: this fraction of a staff space stands in. CONVENTION ASSUMED, NOT
#: CONFIRMED -- no crop this lane read needed the fallback.
LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES = 0.09
#: A window at or above this ink fraction counts as "inked". NOT CONFIRMED
#: against a print; falsified by a real rung whose window reads under this on
#: a scan this bitonal (Litolff merges, Breitkopf shatters -- CLAUDE.md §10 --
#: so one threshold serving both plates is itself an assumption).
LEDGER_RUNG_INK_DENSE = 0.55
#: The GUARD AGAINST A BEAM OR A THICK BLOB: the same x-range one thickness-
#: band further up AND down must read BELOW this fraction, or the "thin"
#: stroke found is really a tall one. Does NOT guard a slanted beam crossing
#: at a shallow angle within the tested window -- NOT CONFIRMED, no crop
#: adjudicated a beam false positive.
LEDGER_RUNG_INK_ADJACENT_MAX = 0.35
#: ⚠️⚠️ ROADMAP 2.6d CALIBRATION (2026-09-29), THE COST OF THE OVERHANG FIX.
#: Narrowing the overhang test (above) to find a real short-wing rung ALSO
#: newly credited a slanted BEAM crossing a head on a positive-case re-
#: gather (Breitkopf pdf idx 22 -- `2.6d-cv-brk22-calibration-02/-03.png`):
#: the beam's own slope carries its ink out of the fixed-x `ADJACENT` bands
#: (the guard above tests the SAME x-range one thickness further up/down,
#: and a sloped stroke is not there any more), so 40 of 40 `found=True`
#: rows on that page needed a look and 2 were the same beam. A LEVEL guard:
#: the ink-weighted row centroid of the LEFT band and of the RIGHT band
#: must not differ by more than this fraction of the tested band's own
#: half-height, or the "horizontal" run is rising/falling across the head
#: -- exactly what a rung crossing perpendicular to a staff never does and
#: a beam crossing it at an angle always does. CONVENTION ASSUMED / WHAT
#: WOULD FALSIFY IT / NOT CONFIRMED: 0.6 clears the one real rung this lane
#: measured (centroids essentially level) and rejects the one beam crop
#: found by chance, not by a swept threshold -- falsified by a confirmed
#: rung on a wandering/skewed staff line this narrow, or a shallow beam
#: still passing. ⚠️ FIRST MEASURED AT 0.6 AND THAT DID NOT CLEAR THE BEAM
#: (slant 11.3-12.1 against a half-height around 26.7, i.e. ~0.42-0.45 --
#: comfortably under 0.6). Retuned to 0.2: still four times the real
#: rung's own measured slant (1.0) and well under half the beam's, the
#: only two data points this lane has.
LEDGER_RUNG_INK_SLANT_MAX_HALF_H = 0.2

#: ⚠️⚠️ ROADMAP 2.37 (manager print check, 2026-09-29). The detector's own
#: box is PADDED past the head's real ink -- confirmed on 33 of 39 Brahms /
#: 8 of 8 Litolff (head, candidate) pairs where the detector boxed EVERY
#: expected rung (`Q.GLYPH_LADDER` complete) yet this reader found none:
#: the crops (`out/print/beam-stem-ink-2.38/brahms_ledger_missed.png`) show
#: the window sitting ON the printed ledger, failing the OVERHANG test
#: only because it was anchored at the padded box edge -- measured left-
#: band density 0.19-0.33 against the 0.55 floor -- past where a
#: genuinely short Breitkopf wing (CLAUDE.md §10: "a little wider than the
#: head") already ends. A column at or above this ink fraction, in the
#: SAME row band the overhang test itself reads, still counts as the
#: head's own ink; walking in from each padded edge toward the centre
#: until a column crosses it finds where the padding ends and the real
#: ink begins.
LEDGER_RUNG_INK_TRUE_EDGE_DENSE = 0.5


def _true_ink_span(ink: Any, x0: float, x1: float, y0: float, y1: float,
                   W: int, H: int) -> Tuple[float, float]:
    """Shrink `[x0, x1)` to the actual ink run in row-band `[y0, y1)`: walk
    inward from each edge toward the centre while that column's own ink
    fraction is BELOW `LEDGER_RUNG_INK_TRUE_EDGE_DENSE` (padding), stopping
    at the first column that reads solid. Never WIDENS the span, and
    returns it UNCHANGED where nothing in it is solid at all (a blank box,
    or one already tight) -- the density test downstream is what declines
    that case, not this one guessing an edge back in."""
    ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
    iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
    if ix1 <= ix0 or iy1 <= iy0:
        return x0, x1
    region = ink[iy0:iy1, ix0:ix1]
    if region.size == 0:
        return x0, x1
    col_frac = region.mean(axis=0)
    n = len(col_frac)
    thr = LEDGER_RUNG_INK_TRUE_EDGE_DENSE
    li = 0
    while li < n and col_frac[li] < thr:
        li += 1
    ri = n - 1
    while ri >= 0 and col_frac[ri] < thr:
        ri -= 1
    if li > ri:
        return x0, x1
    return float(ix0 + li), float(ix0 + ri + 1)


#: ⚠️⚠️ ROADMAP 2.37 (manager print check, round 2, 2026-09-29). Tabulated
#: per failing `det_all` row (detector boxed every expected rung) which
#: named condition actually blocked it: `wide_adjacent` (the ORIGINAL,
#: head-centred `adjacent` guard) dominates -- 32 of 37 rows on Litolff
#: p3, 84 of 119 on Brahms p1, both re-gathered fresh with this branch.
#: Manager's hypothesis, confirmed: the guard's "one band above/below"
#: reaches into the HEAD'S OWN box for the rung nearest it (through the
#: head, or one space below/above it) -- the head is not a stray blob to
#: guard against, it is `ev.subject`, ALREADY KNOWN, and its own ink must
#: not count as "thick" evidence against its own rung. Excluded from every
#: adjacent test (wide AND per-side), never loosened.
def _exclude_head_box(y0: float, y1: float, head_y0: Optional[float],
                      head_y1: Optional[float]) -> Optional[Tuple[float, float]]:
    """`[y0, y1)` with the portion inside `[head_y0, head_y1)` removed --
    keeping whichever side survives (a band only ever overlaps the head on
    ONE side, since the head sits at `y_center`'s own row and a band is
    tested strictly above or strictly below it). `None` where the head
    covers the whole band (nothing left to test, never treated as "thick"
    -- see the call site). Passed through unchanged where the head's own
    box is not known (`head_y0`/`head_y1` `None`, an old caller)."""
    if head_y0 is None or head_y1 is None or head_y1 <= head_y0:
        return (y0, y1)
    if head_y1 <= y0 or head_y0 >= y1:
        return (y0, y1)
    if head_y0 <= y0 and head_y1 >= y1:
        return None
    if head_y0 > y0:
        return (y0, min(y1, head_y0))
    return (max(y0, head_y1), y1)


def ledger_rung_ink(img: Any, head_x0: float, head_x1: float, y_center: float,
                    space: float, thickness_px: Optional[float],
                    head_y0: Optional[float] = None,
                    head_y1: Optional[float] = None
                    ) -> Optional[Dict[str, Any]]:
    """Is there a thin horizontal ink run at `y_center`, crossing the head's
    `[head_x0, head_x1]` and reaching past it on AT LEAST ONE side? ROADMAP
    2.6d -- the same fact a boxed `ledgerLine` witnesses for `Q.GLYPH_
    LADDER`, asked here of the raster where the detector drew no box.
    ROADMAP 2.37 (manager print check, 2026-09-29) loosened BOTH sides to
    ONE, per-side stem-guarded -- see that constant's own note.

    All of `head_x0`, `head_x1`, `y_center`, `space` and `thickness_px` are in
    the SAME canonical pixels as `img` -- the caller's job, not this
    function's; it does no frame conversion. `img` is the cell's staff-
    ERASED raster, 0 = ink. Returns `None` -- declined, never defaulted --
    where the window (or a comparison band) falls entirely off the raster,
    AND (ROADMAP 2.37 round 3, manager print check) where density alone
    would pass but the adjacent evidence needed to clear or block it could
    not be read at all -- CLAUDE.md rule 8, *cannot tell* never becomes
    *clean*.

    Bins at the tested y: CENTER (over the head's own x-span, must be
    inked -- a rung passes under or over the notehead it serves), LEFT and
    RIGHT (the overhang past the head's edges -- at least ONE must be
    inked AND not tall in that same narrow x-range, the guard against the
    note's own STEM, which adds ink on the side it attaches to but does
    not reach past the head, so it fails ITS side's own adjacency test
    even where the OTHER side is a genuine wing). ADJACENT (the wider
    head-centred x-range, one band above and below) must NOT also be
    densely inked, or the stroke found is thick, not thin -- a guard
    against a beam.
    """
    import numpy as np
    if img is None or getattr(img, "ndim", 0) != 2 or not space \
            or space <= 0:
        return None
    ink = (img == 0)
    H, W = ink.shape
    head_w = head_x1 - head_x0
    if head_w <= 0:
        return None
    cx = (head_x0 + head_x1) / 2.0
    overhang = LEDGER_RUNG_INK_OVERHANG_HEAD_FRAC * head_w
    ww = max(head_w * LEDGER_RUNG_INK_WIDTH_HEAD_MULT, head_w + 2 * overhang)
    thickness = float(thickness_px) if thickness_px else \
        LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES * space
    pad = LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * space
    half_h = thickness / 2.0 + pad

    def frac(x0: float, x1: float, y0: float, y1: float) -> Optional[float]:
        ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
        iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
        if ix1 <= ix0 or iy1 <= iy0:
            return None
        region = ink[iy0:iy1, ix0:ix1]
        return float(region.sum()) / float(region.size)

    def row_centroid(x0: float, x1: float, y0: float, y1: float
                     ) -> Optional[float]:
        """The ink-weighted mean row (absolute y) in this band, or `None`
        with nothing to weigh. ROADMAP 2.6d: the slant guard's own ruler --
        a level rung's left and right bands centre on the SAME row; a
        beam crossing at an angle does not."""
        ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
        iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
        if ix1 <= ix0 or iy1 <= iy0:
            return None
        region = ink[iy0:iy1, ix0:ix1]
        weights = region.sum(axis=1).astype(float)
        total = weights.sum()
        if total <= 0:
            return None
        rows = np.arange(iy0, iy1, dtype=float)
        return float((rows * weights).sum() / total)

    def _within_band_level(x0: float, x1: float, y0: float, y1: float
                          ) -> Optional[bool]:
        """ROADMAP 2.37 (manager print check, round 3). Is the ink IN THIS
        ONE BAND level (a straight, PARALLEL stroke -- a beam, a second
        staff line) rather than curved or slanted (a slur passing
        through)? Splits the band at its own x-midpoint and compares the
        two halves' ink-weighted row centroids -- the SAME idea the
        existing left/right slant ruler uses across two SEPARATE bands,
        applied within one. `None` -- never guessed either way -- where a
        half has nothing to weigh.

        ⚠️ RECORDED ONLY, NOT YET A GATE. Measured against the one real
        positive control this lane has (`ledger_rung_ink_brk_p22_real.png`,
        step 1's own "below" band, the ROADMAP 2.6d fixture's own
        documented OPEN finding -- ink close enough to the staff that this
        guard already rejects it, and the rejection is deliberately NOT
        resolved): its within-band centroid gap is 0.30 half-heights,
        comfortably inside `LEDGER_RUNG_INK_SLANT_MAX_HALF_H` (0.2)'s own
        margin below the confirmed BEAM's cross-band ratio (~0.42-0.45,
        that constant's own note) -- i.e. reusing 0.2 here would call this
        ambiguous, deliberately-unresolved ink "confirmed curved" and
        credit it, which is exactly the guess CLAUDE.md rule 7 refuses
        without a real slur crop to calibrate the OTHER direction. NOT
        CONFIRMED against one: the value is computed and carried in
        `detail` for a future round's tabulation, but does not (yet)
        change `blocks` below."""
        if x1 <= x0 or y1 <= y0:
            return None
        mid = (x0 + x1) / 2.0
        lcy = row_centroid(x0, mid, y0, y1)
        rcy = row_centroid(mid, x1, y0, y1)
        if lcy is None or rcy is None:
            return None
        return abs(lcy - rcy) <= LEDGER_RUNG_INK_SLANT_MAX_HALF_H * half_h

    def _band_state(x0: float, x1: float,
                    span: Optional[Tuple[float, float]]
                    ) -> Tuple[Optional[float], bool, bool]:
        """`(density, blocks, off_raster)` for one adjacent band.
        `density` is `None` where the band cannot be read: either the
        head's OWN box covers it entirely (`_exclude_head_box` -- a KNOWN,
        SAFE exclusion, `off_raster=False`) or the raster genuinely has
        nothing there (`off_raster=True`) -- the distinction the decline
        logic below needs, because a rung genuinely THROUGH the head has
        its adjacent bands wholly excluded on purpose and must NOT decline
        over that, while a band that is simply unreadable is the rule-8
        hole. `blocks` is density-only (`> ADJACENT_MAX`) -- see
        `_within_band_level`'s own note on why levelness is not yet a
        gate here."""
        if span is None:
            return None, False, False
        d = frac(x0, x1, *span)
        if d is None:
            return None, False, True
        return d, d > LEDGER_RUNG_INK_ADJACENT_MAX, False

    def _side_state(x0: float, x1: float
                    ) -> Tuple[Optional[float], bool, bool]:
        """`(density, unreadable, blocks)` for one side's own adjacent
        test, over BOTH bands (above, below). `unreadable` is true only
        where NEITHER band gave a density AND at least one of them was a
        genuine raster gap -- a side wholly excluded by the head's own box
        (both bands `None` via `_exclude_head_box`) is NOT unreadable, it
        is a known, safe non-finding."""
        a_d, a_blocks, a_off = _band_state(x0, x1, above_span)
        b_d, b_blocks, b_off = _band_state(x0, x1, below_span)
        vals = [v for v in (a_d, b_d) if v is not None]
        unreadable = not vals and (a_off or b_off)
        return (max(vals) if vals else None), unreadable, (a_blocks or b_blocks)

    def _side_verdict(dense_val: Optional[float], unreadable: bool,
                      blocks: bool) -> str:
        """ROADMAP 2.37 round 3 (manager print check): `"not_dense"` is a
        genuine, fully-read NEGATIVE (never declined over -- CLAUDE.md
        rule 8 does not apply to a real measurement); `"blocked"` is a
        CONFIRMED thick parallel stroke, also a real negative; `"unknown"`
        is the rule-8 hole itself -- density passed but the evidence that
        would clear or block it could not be read at all, so the row must
        DECLINE rather than default to "clean"; `"clear"` is a real,
        fully-read positive."""
        if dense_val is None or dense_val < LEDGER_RUNG_INK_DENSE:
            return "not_dense"
        if blocks:
            return "blocked"
        if unreadable:
            return "unknown"
        return "clear"

    y0, y1 = y_center - half_h, y_center + half_h
    # ⚠️ ROADMAP 2.37: anchor on the TRUE ink edge in THIS row band, not
    # the (possibly padded) box edge -- see `_true_ink_span`'s own note.
    # Only ever shrinks `[head_x0, head_x1]`, never widens it, so a box
    # that was already tight is untouched.
    true_x0, true_x1 = _true_ink_span(ink, head_x0, head_x1, y0, y1, W, H)
    center = frac(true_x0, true_x1, y0, y1)
    # ⚠️ THE OVERHANG TEST IS A NARROW BAND AT THE EDGE, NOT THE WHOLE
    # CONTEXT WINDOW -- see `LEDGER_RUNG_INK_OVERHANG_TEST_FRAC`'s comment.
    overhang_w = LEDGER_RUNG_INK_OVERHANG_TEST_FRAC * head_w
    left_x0, left_x1 = true_x0 - overhang_w, true_x0
    right_x0, right_x1 = true_x1, true_x1 + overhang_w
    left = frac(left_x0, left_x1, y0, y1)
    right = frac(right_x0, right_x1, y0, y1)
    if center is None or left is None or right is None:
        return None
    # ⚠️⚠️ ROADMAP 2.37 (manager print check, round 2). Every adjacent test
    # below (wide AND per-side) excludes the HEAD'S OWN box from the band
    # it reads -- tabulated on a fresh re-gather of both plates with this
    # branch's own code: `wide_adjacent` (this wide, head-centred test) was
    # the dominant failing condition on 32 of 37 Litolff `det_all` rows and
    # 84 of 119 Brahms -- the rung nearest the head (through it, or one
    # space beyond) has the head's OWN solid ink sitting inside "one band
    # further away", read as a false "thick" signal against its own real,
    # thin rung. The head is not a stray blob to guard against: it is
    # `ev.subject`, already known, and `_exclude_head_box` removes exactly
    # its own rows, never any other ink, from the tested band.
    above_span = _exclude_head_box(y0 - 2 * half_h, y0, head_y0, head_y1)
    below_span = _exclude_head_box(y1, y1 + 2 * half_h, head_y0, head_y1)
    above, above_blocks, above_off = _band_state(
        cx - ww / 2.0, cx + ww / 2.0, above_span)
    below, below_blocks, below_off = _band_state(
        cx - ww / 2.0, cx + ww / 2.0, below_span)
    adjacent_vals = [v for v in (above, below) if v is not None]
    adjacent = max(adjacent_vals) if adjacent_vals else None
    # ⚠️ ROADMAP 2.37 round 3: unreadable only where NEITHER band gave a
    # density AND at least one was a genuine raster gap -- both wholly
    # excluded by the head's own box (a rung genuinely through it) is a
    # known, safe non-finding, not "cannot tell" -- see `_side_state`.
    wide_unreadable = not adjacent_vals and (above_off or below_off)
    wide_blocks = above_blocks or below_blocks
    # ⚠️⚠️ ROADMAP 2.37 (manager print check, 2026-09-29). Real Brahms p1
    # crops (`out/print/beam-stem-ink-2.38/brahms_ledger_missed.png`, 33 of
    # 39 `det_all` pairs -- the detector boxed EVERY expected rung, yet
    # this reader found none) measured BOTH sides required where only ONE
    # needed to be: a genuine short Breitkopf wing reads dense on the side
    # it actually extends (0.558-0.622, clearing `DENSE`) and weak on the
    # other (0.266-0.371) -- not because nothing is there, but because
    # engraved wings are not always symmetric and a short one can be
    # crowded by neighbouring ink on one side. The docstring's own
    # justification for BOTH sides was the STEM guard ("a vertical stroke
    # adds no horizontal ink past the head"), which is a claim about ONE
    # side lacking ink, not about the side that DOES having to match the
    # other -- so it is answered by a guard ON THE PASSING SIDE, not by
    # requiring both. Per-side: `left`/`right` must independently be DENSE
    # *and* not also tall (its own one-thickness-band above/below, not the
    # wide `ww`-centred one) -- a stem is vertical and reads dense one
    # thickness away in the SAME narrow x-range a wing does not.
    left_adjacent, left_unreadable, left_blocks = _side_state(left_x0, left_x1)
    right_adjacent, right_unreadable, right_blocks = _side_state(right_x0, right_x1)
    left_v = _side_verdict(left, left_unreadable, left_blocks)
    right_v = _side_verdict(right, right_unreadable, right_blocks)
    # ⚠️ THE LEVEL GUARD -- see `LEDGER_RUNG_INK_SLANT_MAX_HALF_H`'s comment.
    # A band with no ink to weigh (already failing DENSE) reports no slant;
    # `extends` fails on the density test regardless, so this never turns a
    # refusal into a guess in the other direction.
    left_cy = row_centroid(left_x0, left_x1, y0, y1)
    right_cy = row_centroid(right_x0, right_x1, y0, y1)
    slant = (abs(left_cy - right_cy)
            if left_cy is not None and right_cy is not None else None)
    level = slant is None or slant <= LEDGER_RUNG_INK_SLANT_MAX_HALF_H * half_h
    # ⚠️⚠️ ROADMAP 2.37 (manager print check, round 3): CLAUDE.md rule 8,
    # "cannot tell" may never become an answer. A side whose OWN density
    # clears DENSE but whose supporting adjacent evidence could not be
    # read AT ALL (off the raster, or wholly the head's own excluded box)
    # is `"unknown"`, not `"clean"` -- and where no OTHER side clears
    # outright, the whole STEP declines (`None`, the same signal a caller
    # already treats as "cannot tell") rather than asserting `found=True`
    # from missing evidence. Measured: this is exactly the shape of both
    # confound-control false positives round 2 introduced (`left_adjacent`/
    # `right_adjacent`/`adjacent` all `None` while density alone cleared).
    decline = False
    if center < LEDGER_RUNG_INK_DENSE:
        extends = False
    elif left_v == "clear" or right_v == "clear":
        if wide_unreadable:
            decline = True
            extends = False
        else:
            extends = (not wide_blocks) and level
    else:
        decline = left_v == "unknown" or right_v == "unknown"
        extends = False
    if decline:
        return None
    return {
        "found": bool(extends),
        "center": round(center, 4), "left": round(left, 4),
        "right": round(right, 4),
        "left_adjacent": None if left_adjacent is None else round(left_adjacent, 4),
        "right_adjacent": None if right_adjacent is None else round(right_adjacent, 4),
        "slant": None if slant is None else round(slant, 3),
        "adjacent": None if adjacent is None else round(adjacent, 4),
        # ⚠️ ROADMAP 2.37: the wide adjacent test's own two components,
        # named separately so a failure can be tabulated as `above` or
        # `below` rather than collapsed into one number -- exactly the
        # split the manager's own diagnosis needed.
        "adjacent_above": None if above is None else round(above, 4),
        "adjacent_below": None if below is None else round(below, 4),
        "window_canonical": [round(cx - ww / 2.0, 2), round(cx + ww / 2.0, 2),
                             round(y0, 2), round(y1, 2)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.37 (Sean's redirect, 2026-09-29, quoted via the coordinator,
# stopping the absolute-threshold width-test round where it stood):
#
# "pitch is geometric -- staff spacing tells line vs space for any note
# outside the staff; ledger lines always exist between the note and its
# own staff. Pitch already works that way (`restate_pitch` from `Q.
# NOTEHEAD_STAFF_POSITION`, no ledger read). So the ledger reader is ONLY
# needed for OWNERSHIP of a note between two staves, and for that we do
# not need to read every rung with absolute thresholds."
#
# One comparison per contested head: the ONE ledger position adjacent to
# the head on each candidate side, ink density read raw (no found/not-
# found threshold), the OWNER decided by `glyph_owner` from the RATIO
# between the two candidates' own readings -- self-calibrating per plate
# (merging vs shattering) because nothing is ever compared to a fixed
# floor across documents, only the two candidates against each other.
# ─────────────────────────────────────────────────────────────────────────────

#: A candidate's reading must beat the other's by at least this ratio to
#: decide ownership -- "clearly more", not merely more.
LEDGER_OWNER_RATIO_MIN = 2.0
#: ...and the WINNING side's own reading must clear this floor, or two
#: near-empty readings could satisfy the ratio by noise alone.
LEDGER_OWNER_FLOOR = 0.15
#: The tested x-span is the head's own true ink width (`_true_ink_span`),
#: widened by this fraction each side -- "the same x-span" both candidates
#: are read over, Sean's own words ("head ink width ± a little").
LEDGER_OWNER_WIDTH_PAD_FRAC = 0.15
#: A step whose position is within this many spaces of an INTEGER (the
#: head sits almost exactly ON that rung's own row) is the head's own ink,
#: not an independent witness -- sample one step further out instead.
LEDGER_OWNER_ON_TOLERANCE_SPACES = 0.15


#: ⚠️ ROADMAP 2.39 PROMOTED THIS. Sean, 2026-09-29, quoted: "All regular
#: noteheads are the same size so the box should be predictable." These
#: two names and `_standard_head_box` below are kept as ALIASES ONLY --
#: nothing in this file reads them back; every real definition now lives
#: in `geometry.py`, shared with the ADJUDICATE-stage consumer
#: (`adjudicators/notehead_precision.py`) so the two stages cannot size the
#: box differently. See `geometry`'s own module docstring for the
#: measurement, its scope, and the CONVENTION ASSUMED note.
LEDGER_OWNER_HEAD_WIDTH_SPACES = STANDARD_HEAD_WIDTH_SPACES
LEDGER_OWNER_HEAD_HEIGHT_SPACES = STANDARD_HEAD_HEIGHT_SPACES


def _standard_head_box(cx: float, cy: float, spacing: float
                       ) -> Tuple[float, float, float, float]:
    """Alias for `geometry.standard_head_box` -- kept so this file's own
    call sites (predating ROADMAP 2.39's promotion) need no rewrite. See
    `geometry.standard_head_box`'s own docstring."""
    return _standard_head_box_general(cx, cy, spacing)


def _ledger_owner_informative_step(gap: float, spacing: float, *,
                                   edge: Optional[float] = None,
                                   above: Optional[bool] = None,
                                   head_y0: Optional[float] = None,
                                   head_y1: Optional[float] = None,
                                   half_h: Optional[float] = None
                                   ) -> Optional[int]:
    """ROADMAP 2.37 (Sean's redirect; the overlap check added on manager
    review of `baaf3f23`). Which step (1-based, from the candidate's own
    outer line) is the ONE informative rung position toward this
    candidate: the rung immediately adjacent to the head -- UNLESS its
    OWN tested band (`half_h` either side, the SAME band `ledger_owner_
    ink_density` reads) overlaps the head's KNOWN box, in which case that
    row would read the head's own ink, not an independent witness; the
    step one further out (one more space toward the staff) is sampled
    instead. `None` where the candidate needs no ledger at all (within
    the staff or its exempt first space -- the SAME `LEDGER_ROUND_UP`
    boundary `_ledger_expected` itself uses), or where even the further
    step still overlaps the head and there is nowhere left to sample.

    ⚠️⚠️ MEASURED BUG (manager review): the geometry-only fallback below
    (used when `head_y0`/`head_y1`/`half_h` are not given -- every
    pre-existing pure test of this function) approximates "on the
    candidate's own ledger" by asking whether `gap/spacing` is close to
    an INTEGER (within `LEDGER_OWNER_ON_TOLERANCE_SPACES`, 0.15 spaces).
    On a real Brahms re-gather this under-shifted: a head whose OWN
    measured position was 3.36 spacings out (0.36 spaces short of the
    tolerance) still had its `half_h`-tall tested band overlap the
    head's real box, because a real notehead's own vertical extent is
    close to a FULL staff space tall -- much wider than a 0.15-space
    tolerance admits. The REAL call site (`_observe_ledger_owner_
    density`) now passes the head's own box and tests the ACTUAL overlap
    instead of approximating it."""
    if not spacing or spacing <= 0:
        return None
    expected = int(gap / spacing + LEDGER_ROUND_UP)
    if expected <= 0:
        return None
    if (edge is None or above is None or head_y0 is None
            or head_y1 is None or half_h is None):
        # geometry-only fallback -- NOT CONFIRMED against a real box;
        # kept for callers with no page geometry at all.
        steps = gap / spacing
        on_ledger = (abs(steps - round(steps))
                    <= LEDGER_OWNER_ON_TOLERANCE_SPACES)
        if on_ledger:
            return expected - 1 if expected >= 2 else None
        return expected
    # ⚠️⚠️ MEASURED (manager review, round 2): a single one-space shift
    # is not always enough. The FORBIDDEN zone a step must clear is the
    # standard head's own height PLUS the tested band reaching `half_h`
    # past each edge -- `LEDGER_OWNER_HEAD_HEIGHT_SPACES` (1.1) plus
    # `half_h`'s own two thickness-and-pad margins can exceed a single
    # full staff space, so `expected - 1` alone still overlapped on a
    # real Litolff re-gather. Walk OUTWARD (decreasing k) until a step
    # clears, or there is none.
    for k in range(expected, 0, -1):
        want = (edge - k * spacing) if above else (edge + k * spacing)
        if want + half_h <= head_y0 or want - half_h >= head_y1:
            return k
    return None


def ledger_owner_ink_density(img: Any, head_x0: float, head_x1: float,
                             y_center: float, space: float,
                             thickness_px: Optional[float]
                             ) -> Optional[float]:
    """ROADMAP 2.37 (Sean's redirect). The raw ink fraction in a thin band
    (the SAME `half_h` shape `ledger_rung_ink` itself uses) at `y_center`,
    over the head's OWN true ink width (`_true_ink_span`) widened by
    `LEDGER_OWNER_WIDTH_PAD_FRAC` each side. NO threshold, NO found/not-
    found verdict -- `adjudicate_glyph_owner` compares this number against
    the OTHER candidate's own reading, never a fixed floor across
    documents. `None` -- declined -- where the window falls off the
    raster."""
    if img is None or getattr(img, "ndim", 0) != 2 or not space \
            or space <= 0:
        return None
    ink = (img == 0)
    H, W = ink.shape
    head_w = head_x1 - head_x0
    if head_w <= 0:
        return None
    thickness = float(thickness_px) if thickness_px else \
        LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES * space
    pad = LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * space
    half_h = thickness / 2.0 + pad
    y0, y1 = y_center - half_h, y_center + half_h
    true_x0, true_x1 = _true_ink_span(ink, head_x0, head_x1, y0, y1, W, H)
    wpad = LEDGER_OWNER_WIDTH_PAD_FRAC * head_w
    x0, x1 = true_x0 - wpad, true_x1 + wpad
    ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
    iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    region = ink[iy0:iy1, ix0:ix1]
    return float(region.sum()) / float(region.size)


def _observe_ledger_owner_density(log: Log, g: Subject, box, cand_key: str,
                                  line_ys: Sequence[float], spacing: float,
                                  cell_by_key: Dict[Tuple[int, int, int, int], Any],
                                  thickness_px: Optional[float]) -> None:
    """`Q.LEDGER_OWNER_DENSITY` -- ROADMAP 2.37 (Sean's redirect): one row,
    the ONE informative rung position toward `cand_key`.

    ⚠️ ROADMAP 2.39b: the standard box below is RE-CENTRED on `g`'s own
    `Q.NOTEHEAD_RECENTRE` row where GATHER's matched-window search
    accepted one -- `gather_notehead_recentre` only ever files that row
    for a REGULAR notehead, so this reader needs no class-name gate of
    its own to stay inside item 5's boundary; a class the search never
    measures simply has no row to read and keeps the un-shifted detector
    centre, exactly as ROADMAP 2.37 shipped it (`benchmarks/omr-notehead-
    width-2026-09/FINDINGS.md` §18 names this reader as carrying the
    identical sliver exposure `gather_notehead_ink` did before item 2's
    reconnect).
    """
    g = R.glyph(g.page, g.system, g.staff, g.cell, g.glyph)
    # ⚠️⚠️ ROADMAP 2.37 (Sean, 2026-09-29): a STANDARD head extent centred
    # on the detector box's own CENTRE, never its raw width/height -- see
    # `LEDGER_OWNER_HEAD_WIDTH_SPACES`'s own note (a Brahms sliver
    # measured 0.28 sp wide; Litolff boxes grow with merged ink). `cy` is
    # the SAME centre used throughout below (the gap to the staff, the
    # step search) -- only the box's ASSUMED size changes, never its
    # location.
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    recentred = log.rows(Q.NOTEHEAD_RECENTRE, g)
    if recentred:
        dx_sp, dy_sp = recentred[-1].value
        cx = cx + dx_sp * spacing
        cy = cy + dy_sp * spacing
    shx0, shx1, shy0, shy1 = _standard_head_box(cx, cy, spacing)
    top, bottom = min(line_ys), max(line_ys)
    if top <= cy <= bottom:
        log.abstain(g, Q.LEDGER_OWNER_DENSITY, reader=READERS.CV_LEDGER,
                    frame=FRAME_PAGE, reason=ABSTAIN.OFF_STAFF,
                    candidate=cand_key,
                    note="within this candidate's own staff: no ledger question")
        return
    above = cy < top
    edge = top if above else bottom
    gap = (edge - cy) if above else (cy - edge)
    # ⚠️ ROADMAP 2.37 (manager review of `baaf3f23`): the SAME `half_h`
    # band `ledger_owner_ink_density` itself tests, computed here so the
    # step search can check the REAL overlap with the head's own STANDARD
    # box (never the raw detector one) rather than an approximate "close
    # to an integer" heuristic -- see `_ledger_owner_informative_step`'s
    # own note on the bug this replaces.
    thickness = float(thickness_px) if thickness_px else \
        LEDGER_RUNG_INK_DEFAULT_THICKNESS_SPACES * spacing
    pad = LEDGER_RUNG_INK_THICKNESS_PAD_SPACES * spacing
    half_h = thickness / 2.0 + pad
    step = _ledger_owner_informative_step(
        gap, spacing, edge=edge, above=above, head_y0=shy0,
        head_y1=shy1, half_h=half_h)
    if step is None:
        log.abstain(g, Q.LEDGER_OWNER_DENSITY, reader=READERS.CV_LEDGER,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                    candidate=cand_key,
                    note="no informative rung position clear of the "
                        "head's own box")
        return
    want = (edge - step * spacing) if above else (edge + step * spacing)
    cand = R.Subject.from_key(cand_key)
    cell = cell_by_key.get((g.page, g.system, cand.staff, g.cell))
    if cell is None or getattr(cell, "image_no_staff", None) is None:
        cell = cell_by_key.get((g.page, g.system, g.staff, g.cell))
    img = getattr(cell, "image_no_staff", None) if cell is not None else None
    cbox = getattr(cell, "bbox_page_px", None) if cell is not None else None
    up = getattr(cell, "upscale_factor", None) if cell is not None else None
    grid = _cell_grid(cell) if cell is not None else None
    if cell is None or img is None or getattr(img, "ndim", 0) != 2:
        log.abstain(g, Q.LEDGER_OWNER_DENSITY, reader=READERS.CV_LEDGER,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_MASK,
                    candidate=cand_key, step=step, note="no cell raster")
        return
    if not cbox or len(cbox) != 4 or not up or grid is None:
        log.abstain(g, Q.LEDGER_OWNER_DENSITY, reader=READERS.CV_LEDGER,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                    candidate=cand_key, step=step,
                    note="no page box, upscale factor or cell grid")
        return
    space_c = grid[1] * 2.0
    # ⚠️ ROADMAP 2.37 (Sean, 2026-09-29): the STANDARD head span, not the
    # raw detector box -- see `_standard_head_box`'s own note.
    hx0_c = (shx0 - cbox[0]) * up
    hx1_c = (shx1 - cbox[0]) * up
    want_c = (want - cbox[1]) * up
    thick_c = (float(thickness_px) * up) if thickness_px else None
    d = ledger_owner_ink_density(img, hx0_c, hx1_c, want_c, space_c, thick_c)
    if d is None:
        log.abstain(g, Q.LEDGER_OWNER_DENSITY, reader=READERS.CV_LEDGER,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                    candidate=cand_key, step=step, want_y_page=round(want, 2),
                    note="window off the raster")
        return
    log.observe(g, Q.LEDGER_OWNER_DENSITY, round(d, 4),
                reader=READERS.CV_LEDGER, frame=FRAME_PAGE,
                candidate=cand_key, step=step, want_y_page=round(want, 2))


def _observe_ledger_rung_ink(log: Log, g: Subject, box, cand_key: str,
                             line_ys: Sequence[float], spacing: float,
                             cell_by_key: Dict[Tuple[int, int, int, int], Any],
                             thickness_px: Optional[float],
                             class_name: Optional[str] = None) -> None:
    """`Q.LEDGER_RUNG_INK` -- one row per (head glyph, `cand_key`, step).

    ⚠️ THE SAME STEP ARITHMETIC AS `_observe_ladder` (same `LEDGER_ROUND_UP`,
    same "one step per staff space" walk), so a step this reader tests is the
    step the detector-box reader would have tested -- the two are the SAME
    LADDER, read by two readers.

    Samples the CANDIDATE's own cell at the head's own measure index (the
    pad that put the head in the candidate's contest put its ink there too
    -- CLAUDE.md §10), falling back to the head's OWN cell where the
    candidate's carries no raster (a system's outermost staff, say). ABSTAINS
    -- never guesses -- where neither cell has an erased raster or a staff
    unit, or a step's window falls off the raster.

    ⚠️ ROADMAP 2.39. The head's x-window (`hx0_c`/`hx1_c` below) and the
    y-band excluded from the adjacent-stroke guard (`hy0_c`/`hy1_c`) are
    this reader's sibling `_observe_ledger_owner_density`'s own STANDARD
    box (`geometry.standard_head_box`), not the raw detector extent --
    same reasoning: a Brahms sliver or a Litolff merged box is not the
    head's true ink width. Only for a REGULAR notehead
    (`geometry.is_regular_notehead(class_name)`) -- a whole note or a
    grace/cue head keeps the detector's own box, unmeasured this round.
    `class_name` is `None` for a caller that predates this change (the
    geometry-only fallback below), which keeps the raw box, same as
    before.

    ⚠️ ROADMAP 2.39b. The standard box above is RE-CENTRED on `g`'s own
    `Q.NOTEHEAD_RECENTRE` row (GATHER's matched-window search, read never
    re-run) where the search accepted one; where it declined, never ran,
    or `g` is outside the regular-head gate, the box stays centred on the
    detector's own centre, exactly as ROADMAP 2.39 shipped it.
    """
    # ⚠️ RECONSTRUCTED, NOT PASSED THROUGH -- `wiring._SubjectKinds` resolves
    # a subject's Kind from the CONSTRUCTOR EXPRESSION at the site
    # (`R.glyph(...)`), never from a parameter's static type; every other
    # gather site in this file rebuilds its own `g` the same way rather than
    # accepting one from a caller (`gather.py:518,658,1244` etc.), which is
    # what keeps THEIR `log.observe`/`log.abstain` calls resolved. This one
    # line is the fix, not a workaround: every `g` below is the SAME subject,
    # spelled so the static walk can tell.
    g = R.glyph(g.page, g.system, g.staff, g.cell, g.glyph)
    y = (box[1] + box[3]) / 2.0
    top, bottom = min(line_ys), max(line_ys)
    above = y < top
    edge = top if above else bottom
    expected = _ledger_expected(y, line_ys, spacing)
    if expected <= 0:
        return
    cand = R.Subject.from_key(cand_key)
    cell = cell_by_key.get((g.page, g.system, cand.staff, g.cell))
    if cell is None or getattr(cell, "image_no_staff", None) is None:
        cell = cell_by_key.get((g.page, g.system, g.staff, g.cell))
    frame = FRAME_PAGE
    # ⚠️ ONE ABSTAIN CALL SITE for every way the raster or its geometry can
    # be missing -- `reason`/`note` are computed first so the caller's
    # bound `g` (a runtime Subject, unresolvable by `wiring`'s static AST
    # walk the same way `_observe_ladder`'s own `g` already is) is not
    # multiplied into several distinct sites for one fact: *this cell
    # cannot be read*.
    img = getattr(cell, "image_no_staff", None) if cell is not None else None
    cbox = getattr(cell, "bbox_page_px", None) if cell is not None else None
    up = getattr(cell, "upscale_factor", None) if cell is not None else None
    grid = _cell_grid(cell) if cell is not None else None
    reason, note = None, None
    if cell is None:
        reason, note = ABSTAIN.NO_MASK, "no cell carries this ladder's ink"
    elif img is None or getattr(img, "ndim", 0) != 2:
        reason, note = ABSTAIN.NO_MASK, "cell carries no image_no_staff"
    elif not cbox or len(cbox) != 4 or not up or grid is None:
        reason = ABSTAIN.NO_STAFF_GEOMETRY
        note = "no page box, upscale factor or cell grid"
    if reason is not None:
        log.abstain(g, Q.LEDGER_RUNG_INK, reader=READERS.CV_LEDGER,
                    frame=frame, reason=reason, candidate=cand_key,
                    note=note)
        return
    space_c = grid[1] * 2.0
    # ⚠️ ROADMAP 2.39: a REGULAR notehead's ink window is the STANDARD box
    # (detector centre, staff-spacing extent), never the raw detector box
    # -- see this function's own docstring. Anything else (whole note,
    # grace/cue, or a caller with no class name) keeps the detector box,
    # unchanged from before this round. ⚠️ `box` is `(x0, y0, x1, y1)`;
    # `geometry.standard_head_box` returns `(x0, x1, y0, y1)` -- the two
    # are NOT the same tuple shape, so they are unpacked into named
    # variables immediately rather than indexed as one interchangeable
    # `ink_box` (the bug a first draft of this change shipped: `test_
    # regular_black_head_uses_the_standard_box_not_the_raw_one` caught it
    # red before this fix).
    if spacing and is_regular_notehead(class_name):
        cx = (box[0] + box[2]) / 2.0
        cy = (box[1] + box[3]) / 2.0
        # ⚠️ ROADMAP 2.39b: GATHER's own matched-window re-centre, read
        # (never re-run -- CLAUDE.md rule 6) off `g`'s own `Q.NOTEHEAD_
        # RECENTRE` row where the search accepted one. `dx_sp`/`dy_sp` are
        # frame-agnostic ratios, so multiplying by THIS call's own
        # `spacing` (page frame) carries them correctly from the canonical
        # frame the search ran in. A head whose search declined, never
        # ran, or is outside the regular-head gate keeps the un-shifted
        # detector centre, exactly as before this round.
        recentred = log.rows(Q.NOTEHEAD_RECENTRE, g)
        if recentred:
            dx_sp, dy_sp = recentred[-1].value
            cx = cx + dx_sp * spacing
            cy = cy + dy_sp * spacing
        bx0, bx1, by0, by1 = _standard_head_box(cx, cy, spacing)
    else:
        bx0, by0, bx1, by1 = box
    hx0_c = (bx0 - cbox[0]) * up
    hx1_c = (bx1 - cbox[0]) * up
    # ⚠️ ROADMAP 2.37 (manager print check, round 2): the head's OWN
    # canonical y-extent, so the adjacent guards can exclude its known box
    # rather than mistaking its own bulk for a thick, non-rung stroke.
    # ROADMAP 2.39: now the STANDARD box's y-extent for a regular head --
    # see above.
    hy0_c = (by0 - cbox[1]) * up
    hy1_c = (by1 - cbox[1]) * up
    thick_c = (float(thickness_px) * up) if thickness_px else None
    for k in range(1, expected + 1):
        want = (edge - k * spacing) if above else (edge + k * spacing)
        want_c = (want - cbox[1]) * up
        m = ledger_rung_ink(img, hx0_c, hx1_c, want_c, space_c, thick_c,
                           head_y0=hy0_c, head_y1=hy1_c)
        if m is None:
            # ⚠️ ROADMAP 2.37 (manager print check, round 3): `None` now
            # ALSO means "density passed but the adjacent evidence needed
            # to clear or block it could not be read at all" -- CLAUDE.md
            # rule 8, declined rather than defaulted to "clean". Both
            # causes share one reason word; `ledger_rung_ink` itself is
            # where the distinction is made, and it is not asked to carry
            # a reason string back through its plain `Optional[Dict]`
            # return.
            log.abstain(g, Q.LEDGER_RUNG_INK, reader=READERS.CV_LEDGER,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        candidate=cand_key, step=k,
                        note="window off the raster, or dense but the "
                             "adjacent band could not be read")
            continue
        found = m.pop("found")
        win = m.pop("window_canonical")
        wx0p = cbox[0] + win[0] / up
        wx1p = cbox[0] + win[1] / up
        wy0p = cbox[1] + win[2] / up
        wy1p = cbox[1] + win[3] / up
        log.observe(g, Q.LEDGER_RUNG_INK, found,
                    reader=READERS.CV_LEDGER, frame=frame,
                    candidate=cand_key, step=k, want_y_page=round(want, 2),
                    window_page_px=[round(wx0p, 2), round(wy0p, 2),
                                    round(wx1p, 2), round(wy1p, 2)],
                    **m)


# ─────────────────────────────────────────────────────────────────────────────
# Rhythm marks -- MEASUREMENTS. The duration they compose into is a VERDICT.
# ─────────────────────────────────────────────────────────────────────────────

_FLAG_PREFIX = "flag"
_DOT_CLASS = "augmentationDot"
#: ROADMAP 2.12c, DECISIONS 2026-09-23 "SHAPE FROM THE CLASS, ROLE FROM THE
#: GEOMETRY". A small filled dot arrives under one of these classes or
#: `_DOT_CLASS`, and the SHAPE the detector names (a dot, printed above/below
#: vs after a head) is not the ROLE (does it lengthen the note, or mark it
#: short) -- that is `adjudicate_dot_role`'s question, decided from where the
#: ink sits relative to a notehead, never from which of these names it wears.
#: The two fine spellings state a side; the coarse one
#: (`class_aliases.COARSER_THAN_CANONICAL["articulationStaccato"]`) does not,
#: which is irrelevant here since the role decision never reads the side
#: either.
_STACCATO_CLASSES = ("articStaccatoAbove", "articStaccatoBelow",
                     "articulationStaccato")
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

    ⚠️ ROADMAP 2.12c. `Q.AUG_DOT` now holds every `_STACCATO_CLASSES` box
    TOO, tagged `detail.detector_role`, because a staccato and an
    augmentation dot are the SAME shape claim (one small filled dot) and only
    their POSITION says which role they play -- `adjudicate_dot_role` is
    where that is decided, never here. This is the ONE quantity the ink is
    filed under; `gather_glyph_families` no longer files these classes into
    `Q.ARTICULATION_MARK` at all, so a staccato-class box cannot become two
    rows from one reader on one glyph (CLAUDE.md Sec.4b, `Evidence.
    correlated_groups`).
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
            elif name == _DOT_CLASS or name in _STACCATO_CLASSES:
                log.observe(g, Q.AUG_DOT, (d.x_center, d.y_center),
                            reader=READERS.DETECTOR, frame=frame,
                            score=float(d.confidence),
                            detector_role=("dot" if name == _DOT_CLASS
                                          else "staccato"),
                            detector_class=name)
            elif name in _TUPLET_CLASSES:
                log.observe(g, Q.TUPLET_MARKER, name,
                            reader=READERS.DETECTOR, frame=frame,
                            score=float(d.confidence),
                            x0=d.x_canonical,
                            x1=d.x_canonical + d.width_canonical,
                            x_center=d.x_center,
                            is_bracket=name.lower().endswith("bracket"))


# ─────────────────────────────────────────────────────────────────────────────
# A dot's STAFF POSITION -- ROADMAP 2.128
# ─────────────────────────────────────────────────────────────────────────────

#: The window of page columns the five lines are re-found in around a dot's own
#: x, each side, in staff spaces (>= `CELL_LINE_MIN_WIDTH_SPACES` / 2 so the
#: finder accepts it). A measurement scale, not a decision.
DOT_LINE_WINDOW_SPACES = 3.0

#: A dot more than this many half-steps clear of every staff is OFF the staff
#: (abstains `off_staff` with the signed distance). CONVENTION ASSUMED / WHAT
#: WOULD FALSIFY IT / NOT CONFIRMED: four spaces is more than any ledgered
#: note's dot stands from its staff; it is a cut-off on our plates, so the
#: abstention records the distance and a consumer may look at a nearer one.
DOT_OFF_STAFF_STEPS = 8.0


def dot_step_fields(cy: float, top_y: float, half_step: float
                    ) -> Dict[str, Any]:
    """The pure arithmetic: a dot's centre `cy` against a line grid.

    `pos` is `NOTEHEAD_STAFF_POSITION`'s unit (half-steps below the top line);
    an even rounded `step` is a LINE and an odd one a SPACE. `margin` is how
    far `pos` lies from the line/space boundary, in steps (0.5 = dead centre
    on a line or a space, 0 = on the boundary, which cannot be told). The
    `outside` distance is signed (negative above the staff, positive below).
    """
    pos = (float(cy) - float(top_y)) / float(half_step)
    step = int(round(pos))
    residual = abs(pos - step)
    outside = 0.0
    if pos < 0.0:
        outside = pos
    elif pos > 8.0:
        outside = pos - 8.0
    return {"pos": pos, "step": step,
            "on": "line" if step % 2 == 0 else "space",
            "residual": residual, "margin": 0.5 - residual,
            "steps_outside_staff": outside}


def _local_staff_lines(binary: Any, line_ys: Sequence[float], spacing: float,
                       cx: float, window_spaces: Optional[float] = None
                       ) -> Optional[List[float]]:
    """The five printed line rows IN THE COLUMNS AROUND `cx`, or `None`.

    CLAUDE.md Sec.5: a scanned staff tilts and ~1 px decides a near-boundary
    pitch, so the lines are re-found where the dot stands -- the SAME finder
    (`measure_extractor._find_five_lines`) that localises a bar's grid, run on
    a window of `DOT_LINE_WINDOW_SPACES` either side of the dot instead of the
    whole bar. `None` where the finder cannot place all five (declined, never
    defaulted: the caller then falls back to the bar's own grid and says so).
    """
    if binary is None or getattr(binary, "ndim", 0) != 2 or spacing <= 0 \
            or len(line_ys) < 5:
        return None
    from .. import measure_extractor as ME
    width = binary.shape[1]
    win = DOT_LINE_WINDOW_SPACES if window_spaces is None else window_spaces
    lo = max(0, int(round(cx - win * spacing)))
    hi = min(width, int(round(cx + win * spacing)))
    if hi - lo < max(2.0, ME.CELL_LINE_MIN_WIDTH_SPACES * spacing):
        return None
    try:
        rows = ME._find_five_lines(binary, [int(round(y)) for y in line_ys],
                                   float(spacing), lo, hi)
    except Exception:                                         # noqa: BLE001
        return None
    return [float(r) for r in rows] if rows and len(rows) == 5 else None


def gather_dot_positions(log: Log, pws: Any, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]]) -> None:
    """`Q.DOT_STAFF_POSITION` for every `Q.AUG_DOT` box. ROADMAP 2.128.

    ⚠️ A MEASUREMENT, NEVER A ROLE. Where a dot stands on the staff is the
    evidence `adjudicate_dot_role` weighs; the verdict stays its own. Filed on
    the dot's glyph, scoreless, in the notehead's unit, so a dot and the head
    it follows can be compared on one ruler.

    ⚠️ WHICH STAFF. A dot cut into one strip may stand on the next staff's
    lines (the foreign-cell dots of `benchmarks/omr-aug-dots-2026-10`), so the
    row is measured against the NEAREST staff of the page and says which
    (`detail.staff`, `detail.home`). Far from every staff, it abstains
    `off_staff` with the signed distance.

    ⚠️ LOCAL (CLAUDE.md Sec.5). The lines are re-found in the columns around the
    dot's x (`_local_staff_lines`); where that cannot be done and the staff is
    the cell's own, the bar's localised grid answers and `detail.basis` says
    `cell_grid`; otherwise the row is an ABSTENTION (`no_staff_geometry`).
    """
    page = getattr(pws, "page", None)
    binary = getattr(page, "binary", None)
    staves = []
    for st in getattr(pws, "staves", ()) or ():
        key = local.get(st.staff_index)
        ys = [float(y) for y in getattr(st, "line_ys", ()) or ()]
        if key is None or len(ys) < 5:
            continue
        sp = _spacing(st)
        if not sp:
            continue
        p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
        staves.append((st, R.staff(p, key[0], key[1]).to_key(), ys, float(sp)))
    cell_by_key = {}
    for c in cells or ():
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c

    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        frame = frame_cell(sub.cell)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        home_key = sub.at(R.Kind.STAFF).to_key()
        for gi, d in enumerate(dets):
            name = d.smufl_name
            if not (name == _DOT_CLASS or name in _STACCATO_CLASSES):
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            box = _page_box(c, d) if c is not None else None
            if box is None or not staves:
                log.abstain(g, Q.DOT_STAFF_POSITION, reader=READERS.GEOMETRY,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            why="no page box" if box is None else "no staves",
                            detector_class=name)
                continue
            cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
            # the nearest staff by distance to its five-line band; the cell's
            # own staff wins a tie
            def _band_gap(t):
                return max(min(t[2]) - cy, cy - max(t[2]), 0.0) / t[3]
            best = min(staves, key=lambda t: (_band_gap(t),
                                              0 if t[1] == home_key else 1))
            st, skey, ys, sp = best
            rows = _local_staff_lines(binary, ys, sp, cx)
            basis = None
            if rows is not None:
                top_y, half = rows[0], (rows[-1] - rows[0]) / 8.0
                basis = "local_ink"
            elif skey == home_key and c is not None:
                grid = _cell_grid(c)
                up = getattr(c, "upscale_factor", None)
                bb = getattr(c, "bbox_page_px", None)
                if grid is not None and up and bb:
                    top_y = bb[1] + grid[0] / up
                    half = grid[1] / up
                    basis = "cell_grid"
            if basis is None or half <= 0:
                log.abstain(g, Q.DOT_STAFF_POSITION, reader=READERS.GEOMETRY,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            why="the staff lines at the dot's x cannot be read",
                            staff=skey, detector_class=name)
                continue
            f = dot_step_fields(cy, top_y, half)
            if abs(f["steps_outside_staff"]) > DOT_OFF_STAFF_STEPS:
                # ⚠️ A REFUSAL SAYS HOW CLOSE IT CAME: `margin` is the signed
                # distance past the cut-off (always positive here), `side` which
                # edge of the nearest staff the dot lies beyond.
                log.abstain(g, Q.DOT_STAFF_POSITION, reader=READERS.GEOMETRY,
                            frame=frame, reason=ABSTAIN.OFF_STAFF,
                            margin=abs(f["steps_outside_staff"])
                            - DOT_OFF_STAFF_STEPS,
                            side=("above" if f["steps_outside_staff"] < 0
                                  else "below"),
                            staff=skey, detector_class=name)
                continue
            log.observe(g, Q.DOT_STAFF_POSITION, f["pos"],
                        reader=READERS.GEOMETRY, frame=frame,
                        step=f["step"], on=f["on"],
                        residual=f["residual"], margin=f["margin"],
                        basis=basis, staff=skey, home=(skey == home_key),
                        x_page=cx,
                        detector_role=("dot" if name == _DOT_CLASS
                                       else "staccato"),
                        detector_class=name)


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
#: ⚠️ `fermata` AND NOT `artic`. The 208-class space spells the pause sign
#: `fermataAbove` / `fermataBelow`, which share the detector's `ornament`
#: CATEGORY with all ten `artic*` classes, `ornamentTrill` and `arpeggiato` --
#: so a category-keyed router would file a fermata as an articulation, and an
#: articulation's own attach rule (nearest notehead on the side its class
#: names) is the wrong rule for a mark that most often hangs over a REST.
_FERMATA_PREFIX = "fermata"


def _ornament_kind(name: str):
    """`transcribe.ornament_kind`, CALLED and never copied.

    ⚠️ THE TABLE IS ASKED, NOT PREFIX-MATCHED, and the tremolos are why:
    `tremolo1`-`5` are ornaments whose class names do not begin `ornament`.
    `_ORNAMENT_KINDS` also carries the STROKE COUNT and the SIDE, both of
    which a prefix test would throw away.

    ⚠️ IMPORTED INSIDE THE FUNCTION, AND A FIRST DRAFT GOT THE REASON WRONG —
    recorded because the wrong reason was plausible and checkable in one line.
    It is NOT that `transcribe` is unimportable here: the first attempt wrote
    `from ... import transcribe`, which resolves to `tools.transcribe` from
    this package depth and fails; `from .. import transcribe` is correct and
    works. It stays inside the function because `gather.py` imports NOTHING
    from `tools.omr` at module level today (only `.record`), and `transcribe`
    pulls in the detector stack — so a module-level import would make every
    reader of this module pay for it.
    """
    from .. import transcribe as _legacy
    return _legacy.ornament_kind(name)


def _artic_side(name: str) -> Optional[str]:
    """The side an articulation's own class NAMES, or None where it does not.

    ⚠️ Not every class states one. `class_aliases.COARSER_THAN_CANONICAL`
    records `articulationAccent` / `Staccato` / `Tenuto` as coarser than the
    canonical spelling precisely because they carry no side, and the legacy
    attach pass requires the geometry to AGREE with the side when there is
    one. So this returns None rather than guessing, and the adjudicator gets a
    row that says "no side declared" instead of a wrong one.

    ⚠️ IT HAS A SECOND CALLER WITH DIFFERENT SEMANTICS, and saying so is the
    point. `Q.FERMATA_MARK` records the same suffix, but for a fermata the side
    is NOT an attach constraint -- a `fermataAbove` hangs over whatever sounds
    beneath it, including a whole-bar rest it stands well above. This function
    reads a NAME; what the side is allowed to MEAN belongs to each adjudicator.
    """
    if name.endswith("Above"):
        return "above"
    if name.endswith("Below"):
        return "below"
    return None


def gather_glyph_families(log: Log, detections: Dict[str, List[Any]],
                          cells: Sequence[Any] = (),
                          local: Optional[Dict[int, Tuple[int, int]]] = None
                          ) -> None:
    """Rests, arcs, articulation marks, fermatas and ornaments.

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
    # ⚠️⚠️ THE PAGE FRAME, AND WITHOUT IT `arc_owner` COULD NOT HAVE BEEN
    # WRITTEN. This function shipped 2026-09-09 emitting CANONICAL coordinates
    # only -- measured inside ONE cell rescaled so the staff span is constant,
    # so two staves' values are not the same quantity. `adjudicate_arc_owner`
    # asks "whose noteheads does this arc hug" of EVERY staff in the system,
    # which is a cross-staff comparison, so the stub's declared input was
    # present and in a frame that could not answer its own question.
    #
    # That is exactly the fault `Q.ONSET_COLUMN` paid for -- it reported 1,062
    # columns at 76.6% corroborated, 699 of them agreeing to the FLOAT, which
    # no scan does. ⚠️ And `coverage()` cannot see this shape: it reports the
    # family as `stub` (input gathered), not `starved`. A quantity can be
    # gathered in the WRONG FRAME and look fed.
    by_key = {}
    for c in (cells or ()):
        key = (local or {}).get(c.staff_index)
        if key is not None:
            by_key[R.cell(c.page_index, key[0], key[1],
                          c.measure_index).to_key()] = c

    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        frame = frame_cell(sub.cell)
        cell_obj = by_key.get(cell_key)
        for gi, d in enumerate(dets):
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            name = d.smufl_name
            box = dict(
                x0=d.x_canonical, x1=d.x_canonical + d.width_canonical,
                y0=d.y_canonical, y1=d.y_canonical + d.height_canonical,
                x_center=d.x_center, y_center=d.y_center,
            )
            # ⚠️ DECLINED, NEVER DEFAULTED TO THE CELL FRAME, the same rule
            # `gather_detections` and `gather_dynamic_letters` follow: a glyph
            # whose page position is unknown and one measured at page x 1841
            # are different facts, and only the second may reach a cross-staff
            # consumer.
            page_box = _page_box(cell_obj, d) if cell_obj is not None else None
            if page_box is None:
                box["frame_note"] = (
                    "no page box: cell has no bbox_page_px/upscale_factor")
            else:
                px0, py0, px1, py1 = page_box
                box.update(bbox_page_px=[px0, py0, px1, py1],
                           x_center_page=(px0 + px1) / 2.0,
                           y_center_page=(py0 + py1) / 2.0)
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
            # ⚠️ ROADMAP 2.12c. `_STACCATO_CLASSES` is EXCLUDED here even
            # though every one of them starts with `_ARTIC_PREFIX`, and the
            # exclusion is the fix: `gather_rhythm_marks` already files this
            # exact box into `Q.AUG_DOT` (tagged `detail.detector_role`), and
            # filing it AGAIN here would be two rows from one reader on one
            # glyph -- one signal wearing two hats (CLAUDE.md Sec.4b). A
            # staccato's role (does it lengthen the note, or mark it short)
            # is `adjudicate_dot_role`'s question now, never this router's.
            elif (name.startswith(_ARTIC_PREFIX)
                  and name not in _STACCATO_CLASSES):
                log.observe(g, Q.ARTICULATION_MARK, name, **common, **box,
                            side=_artic_side(name))
            elif name.lower().startswith(_REST_PREFIX):
                log.observe(g, Q.REST, name, **common, **box)
            elif _ornament_kind(name) is not None:
                # ⚠️ ASKED OF THE LEGACY TABLE, NOT MATCHED ON A PREFIX, and
                # the tremolos are why: `tremolo1`-`5` are ornaments whose
                # class names do not begin `ornament`. `_ORNAMENT_KINDS` is
                # the one place that mapping lives and it carries the STROKE
                # COUNT and the SIDE with it, both of which a prefix test
                # would throw away.
                kind, strokes, above = _ornament_kind(name)
                log.observe(g, Q.ORNAMENT_MARK, name, **common, **box,
                            kind=kind, strokes=strokes,
                            # ⚠️ `None` FOR A TREMOLO IS A FACT, NOT A GAP: it
                            # rides the STEM and sits on whichever side that
                            # is, so its class states no side and the geometry
                            # test is skipped rather than guessed.
                            side=("above" if above is True
                                  else "below" if above is False else None))
            elif name.lower().startswith(_FERMATA_PREFIX):
                # ⚠️ THE SIDE IS RECORDED AND NOTHING READS IT, deliberately.
                # `export._mxl_note` writes `<fermata type="upright"/>`
                # unconditionally, so `fermataBelow` has nowhere to go today --
                # and a reading thrown away at the gather site is how this
                # project's most-repeated bug starts. Written down here, read
                # later or never.
                log.observe(g, Q.FERMATA_MARK, name, **common, **box,
                            side=_artic_side(name))


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


#: The staves beside a dynamic letter's own that it can stand below or inside:
#: the staff above, its own, the staff beneath (offsets in the system's staff
#: ordinal). A letter cut from a padded cell reaches no further.
_LETTER_STAFF_OFFSETS = (-1, 0, 1)


def _letter_positions_in_staves(cells_of_staff, sub: Subject, cx: float,
                                cy: float) -> Dict[str, float]:
    """ROADMAP 2.68: the letter's centre, in half-steps from each neighbouring
    staff's TOP line (0 = the top line, 8 = the bottom line, negative = above
    the staff), keyed by the staff's offset from the cell's own as a string.

    ⚠️ LOCAL (CLAUDE.md §10): each staff's own CELL grid at the letter's x
    (`_local_position_in_candidate`), never the page-wide lines a tilted scan
    shifts by up to ~0.8 spaces. A staff with no cell at that x (no such staff,
    or the bar is cut differently) is LEFT OUT, not defaulted: a position that
    was never measured is not a position. Nothing is decided here -- which staff
    the letter belongs to is `adjudicate_dynamic`'s question."""
    out: Dict[str, float] = {}
    for off in _LETTER_STAFF_OFFSETS:
        st = sub.staff + off
        if st < 0:
            continue
        key = R.staff(sub.page, sub.system, st).to_key()
        lp = _local_position_in_candidate(cells_of_staff, key, cx, cy)
        if lp is not None:
            out[str(off)] = float(lp)
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
    # ROADMAP 2.68: the page's ink with EVERY detected glyph taken out, read
    # once per page, for `Q.DYNAMIC_LETTER_NEIGHBOURS`.
    other_ink = _ink_without_detections(pws, detections, cell_by_key,
                                        _page_staff_spacing(bands))
    page_letters = _dynamic_letter_boxes(detections, cell_by_key)
    # ROADMAP 2.68 (twins): the page's raw ink, for the letter's own HEIGHT.
    raw_ink = _raw_page_ink(pws)
    # ROADMAP 2.68 (Sean 2026-10-08/09: a dynamic belongs to the staff it is
    # printed BELOW): each cell's staff grid, for the letter's LOCAL position
    # against its own staff and the two beside it.
    cells_of_staff: Dict[Tuple[int, int, int], List[Any]] = {}
    for (pg_, sy_, st_, _m), c_ in cell_by_key.items():
        cells_of_staff.setdefault((pg_, sy_, st_), []).append(c_)

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
            # ⚠️ ROADMAP 2.107: a letter the SECOND LOOK read is attributed to
            # the look, not to the production detector (`_glyph_reader`).
            letter_reader = _glyph_reader(log, g)
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
                            reader=letter_reader, frame=frame,
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
            positions = _letter_positions_in_staves(
                cells_of_staff, sub, (x0 + x1) / 2.0, (y0 + y1) / 2.0)
            if positions:
                detail["local_position_in_staves"] = positions
            if band is not None and raw_ink is not None:
                # ROADMAP 2.68 (twins): how tall the INK in this box is, in
                # staff spaces -- the evidence that says which letter ONE ink
                # boxed as two classes is (an `f` rises above the x-height, a
                # `p` does not). Absent where there is nothing to measure.
                extent = letter_ink_extent(raw_ink, box, band[2])
                if extent is not None:
                    detail.update(ink_height_spaces=extent["height_spaces"],
                                  ink_width_spaces=extent["width_spaces"])
            log.observe(g, Q.DYNAMIC_LETTER, d.smufl_name,
                        reader=letter_reader, frame=FRAME_PAGE,
                        score=float(d.confidence), **detail)
            spacing = band[2] if band is not None else None
            if other_ink is None or not spacing:
                log.abstain(g, Q.DYNAMIC_LETTER_NEIGHBOURS,
                            reader=READERS.CV_LETTER_NEIGHBOURS, frame=FRAME_PAGE,
                            reason=ABSTAIN.READER_UNAVAILABLE,
                            note="no page raster" if other_ink is None
                            else "no staff spacing")
            else:
                sides = letter_ink_beside(other_ink, box, spacing,
                                          exclude=_same_ink_boxes(box, page_letters))
                log.observe(g, Q.DYNAMIC_LETTER_NEIGHBOURS,
                            {"left": sides["left"], "right": sides["right"],
                             "left_spaces": sides["left_spaces"],
                             "right_spaces": sides["right_spaces"]},
                            reader=READERS.CV_LETTER_NEIGHBOURS,
                            frame=FRAME_PAGE, gap_spaces=LETTER_GAP_SPACES)
        if n == 0:
            # ⚠️ NOT `NO_INK`. This loop is over `detections.items()`, so the
            # detector fired HERE and what it returned simply holds no
            # dynamic letter -- a bar of noteheads and a slur, not a blank
            # bar. Measured on Litolff Beethoven 5 pp.1-4, all 997 of these
            # stood on a cell with detections and ink: 997 of 997.
            log.abstain(sub, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR,
                        frame=frame, reason=ABSTAIN.NO_GLYPH_OF_THIS_KIND,
                        cell_n_detections=len(dets))

    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        if sub.to_key() not in seen_cells:
            log.abstain(sub, Q.DYNAMIC_LETTER, reader=READERS.DETECTOR,
                        frame=frame_cell(c.measure_index),
                        reason=ABSTAIN.NO_DETECTIONS)


def _raw_page_ink(pws: Any):
    """The page's ink (255) with NOTHING taken out, or None with no raster."""
    page = getattr(pws, "page", None)
    rgb = getattr(page, "rgb", None)
    if rgb is None:
        return None
    import cv2 as _cv2
    gray = _cv2.cvtColor(rgb, _cv2.COLOR_BGR2GRAY) if rgb.ndim == 3 else rgb
    _, mask = _cv2.threshold(gray, 180, 255, _cv2.THRESH_BINARY_INV)
    return mask


#: A horizontal run this long (staff spaces) is a staff or ledger line, not a
#: letter: no letter's stroke runs 2 spaces without bending.
LETTER_LINE_SPACES = 2.0
#: Ink under this share of a square staff space is a speck, not a part of the
#: letter.
LETTER_SPECK_SPACES2 = 0.08


def letter_ink_extent(ink, box, spacing: float) -> Optional[Dict[str, float]]:
    """How tall and how wide the INK inside a dynamic letter's box is, in staff
    spaces, with staff lines and tall strokes (barlines, stems) taken out. Pure;
    `ink` is 255 = ink. None where nothing but lines stood in the box.

    ROADMAP 2.68 (twins). One printed letter boxed as two classes (`dynamicP`
    and `dynamicF` on the same ink) can only be told apart by what the ink IS,
    and the cheapest measure that separates `f` from `p` is HEIGHT: an `f`
    rises above the x-height AND falls below it, a `p` only falls. Measured on
    Sean's 12 hand-labelled `f` boxes (Brahms 317803 pdf 0): 2.4 to 2.6 spaces;
    the `p`s on the same plate 1.4 to 2.1.

    The lines are taken out on a crop PADDED beyond the box (2 spaces either
    side, 3 above and below), because a staff line is only a line where its
    run is longer than the letter is wide and a barline only a barline where
    it is taller than the letter is tall; inside the box alone both look like
    ink of the letter. Everything outside the box (+2 px) is then discarded.
    """
    import cv2 as _cv2
    import numpy as _np
    sp = float(spacing)
    if sp <= 0:
        return None
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    px, py = int(round(2.0 * sp)), int(round(3.0 * sp))
    H, W = ink.shape[:2]
    cx0, cy0 = max(0, x0 - px), max(0, y0 - py)
    cx1, cy1 = min(W, x1 + px), min(H, y1 + py)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    crop = _np.array(ink[cy0:cy1, cx0:cx1], copy=True)
    kh = max(3, int(round(LETTER_LINE_SPACES * sp)))
    hl = _cv2.morphologyEx(crop, _cv2.MORPH_OPEN,
                           _cv2.getStructuringElement(_cv2.MORPH_RECT, (kh, 1)))
    hl = _cv2.dilate(hl, _cv2.getStructuringElement(_cv2.MORPH_RECT, (1, 3)))
    crop[hl > 0] = 0
    kv = max(3, int(round(VLINE_SPACES * sp)))
    vl = _cv2.morphologyEx(crop, _cv2.MORPH_OPEN,
                           _cv2.getStructuringElement(_cv2.MORPH_RECT, (1, kv)))
    vl = _cv2.dilate(vl, _cv2.getStructuringElement(_cv2.MORPH_RECT, (3, 1)))
    crop[vl > 0] = 0
    # keep only what stands in the box itself
    keep = _np.zeros_like(crop)
    bx0, by0 = max(0, x0 - 2 - cx0), max(0, y0 - 2 - cy0)
    bx1, by1 = min(crop.shape[1], x1 + 3 - cx0), min(crop.shape[0], y1 + 3 - cy0)
    keep[by0:by1, bx0:bx1] = crop[by0:by1, bx0:bx1]
    n, _lab, stats, _cen = _cv2.connectedComponentsWithStats(keep, connectivity=8)
    parts = [i for i in range(1, n)
             if stats[i, _cv2.CC_STAT_AREA] >= LETTER_SPECK_SPACES2 * sp * sp]
    if not parts:
        return None
    left = min(stats[i, _cv2.CC_STAT_LEFT] for i in parts)
    top = min(stats[i, _cv2.CC_STAT_TOP] for i in parts)
    right = max(stats[i, _cv2.CC_STAT_LEFT] + stats[i, _cv2.CC_STAT_WIDTH] for i in parts)
    bottom = max(stats[i, _cv2.CC_STAT_TOP] + stats[i, _cv2.CC_STAT_HEIGHT] for i in parts)
    return {"height_spaces": round(float(bottom - top) / sp, 3),
            "width_spaces": round(float(right - left) / sp, 3),
            "bbox_page_px": [float(cx0 + left), float(cy0 + top),
                             float(cx0 + right), float(cy0 + bottom)]}


#: How close letter ink must stand to a dynamic letter, on its own line, for
#: the letter to have a NEIGHBOUR: the space between two letters of one word.
#: A dynamic beside a word stands clear of it (`direction_text`: 1.7 spaces
#: measured; a letter inside `espr.` 0.5-0.9 with the dynamic boxes taken out).
LETTER_GAP_SPACES = 0.5


def _page_staff_spacing(bands: Dict[Any, Any]) -> Optional[float]:
    """The page's median staff spacing, from the per-staff bands."""
    vals = sorted(float(b[2]) for b in bands.values() if b and b[2])
    return vals[len(vals) // 2] if vals else None


def _dynamic_letter_boxes(detections: Dict[str, List[Any]],
                          cell_by_key: Dict[Any, Any]) -> List[Tuple[float, ...]]:
    """Every dynamic-letter box on the page, in page pixels, across cells."""
    out: List[Tuple[float, ...]] = []
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for d in dets:
            if d.smufl_name in _DYNAMIC_LETTER_CLASSES:
                b = _page_box(c, d)
                if b is not None:
                    out.append(tuple(b))
    return out


def _same_ink_boxes(box, page_letters, share: float = 0.5) -> List[Tuple[float, ...]]:
    """The dynamic-letter boxes that are THIS letter's own ink: its own box and
    every other detection of a dynamic letter overlapping it by at least `share`
    of the smaller area (the same printed `p` boxed as `dynamicP` and again as
    `dynamicF`, or once more from the neighbouring staff's cell). They are not
    neighbours: a letter is not its own neighbour."""
    x0, y0, x1, y1 = box
    area = max(1.0, (x1 - x0) * (y1 - y0))
    out = [tuple(box)]
    for b in page_letters:
        ix = max(0.0, min(x1, b[2]) - max(x0, b[0]))
        iy = max(0.0, min(y1, b[3]) - max(y0, b[1]))
        small = max(1.0, min(area, (b[2] - b[0]) * (b[3] - b[1])))
        if ix * iy >= share * small:
            out.append(b)
    return out


def _ink_without_detections(pws: Any, detections: Dict[str, List[Any]],
                            cell_by_key: Dict[Any, Any],
                            spacing: Optional[float] = None):
    """The page's ink (255) with every detected NOTATION glyph blanked -- what is
    left beside a dynamic letter is ink the detector did not name as notation:
    the other letters of a word. None if the page has no raster.

    ⚠️ WHICH BOXES MAY HIDE A WORD'S LETTERS IS ONE RULE, NOT TWO
    (`direction_text.letter_hiding_kind`, ROADMAP 2.68): a SPAN (slur, tie,
    beam, staff -- wider than 4 spaces), a clef/rest/time/ornament box and a
    DYNAMIC box are NOT blanked here. Measured on Brahms p0 `espr.` (2026-10-09)
    the old rule blanked every detection under 0.25 of the page width, and the
    slur box over the bar (843 px, 30 spaces) plus a `restWhole` box on the `r`
    erased the `s`, `p`, `r` of the word -- the `p` had NO letter neighbour and
    came back as piano -- and the detector's own boxes on `legato`'s letters
    (boxed as dynamics) were blanked too, so they never counted as one another's
    neighbours. Ink standing in a span's box is thin or enormous and the letter
    test (`letter_ink_beside`: size, fill, own line) refuses it."""
    page = getattr(pws, "page", None)
    rgb = getattr(page, "rgb", None)
    if rgb is None:
        return None
    import cv2 as _cv2
    from .. import direction_text as _DT
    if not spacing:
        spacing = float(sorted(_DT._spacing(s) for s in pws.staves)[len(pws.staves) // 2]) \
            if getattr(pws, "staves", None) else 0.0
    gray = _cv2.cvtColor(rgb, _cv2.COLOR_BGR2GRAY) if rgb.ndim == 3 else rgb
    _, mask = _cv2.threshold(gray, 180, 255, _cv2.THRESH_BINARY_INV)
    h, w = mask.shape
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for d in dets:
            box = _page_box(c, d)
            if box is None:
                continue
            x0, y0, x1, y1 = (int(round(v)) for v in box)
            if spacing and _DT.letter_hiding_kind(
                    getattr(d, "category", None), x1 - x0, spacing) is not None:
                continue
            if not spacing and x1 - x0 > 0.25 * w:
                continue    # no spacing: the old width cut
            mask[max(0, y0 - 2):min(h, y1 + 2), max(0, x0 - 2):min(w, x1 + 2)] = 0
    if spacing:
        # ⚠️ A BARLINE (or a stem) THROUGH A WORD: Brahms p0 prints `legato`
        # across a barline, the `t` touching the line and the `o` just past
        # it; the line's component is staves tall, so the `o` had no letter
        # neighbour (0.94 spaces to the `a`) and came back as piano. Vertical
        # strokes taller than `VLINE_SPACES` -- no letter is -- are taken out
        # of the mask, so what they touched is read as the pieces it is.
        k = max(3, int(round(VLINE_SPACES * spacing)))
        vlines = _cv2.morphologyEx(mask, _cv2.MORPH_OPEN,
                                   _cv2.getStructuringElement(_cv2.MORPH_RECT, (1, k)))
        vlines = _cv2.dilate(vlines, _cv2.getStructuringElement(_cv2.MORPH_RECT, (3, 1)))
        mask[vlines > 0] = 0
    return mask


#: Taller than any letter (an `f` is ~2.9 spaces): a barline, a stem.
VLINE_SPACES = 4.0


def letter_ink_beside(mask, box, spacing: float, exclude=()) -> Dict[str, Any]:
    """Is there a LETTER-sized, letter-dense piece of ink within
    `LETTER_GAP_SPACES` of this box, on its own line (overlapping its middle
    half), on the left and on the right? Pure; `mask` is 255 = ink. `exclude`
    are page boxes of this letter's OWN ink (`_same_ink_boxes`), blanked in the
    window so a sliver of the letter outside its box, or its twin box, is not a
    neighbour."""
    import cv2 as _cv2
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    hgt = max(1, y1 - y0)
    r0, r1 = y0 + hgt // 4, y1 - hgt // 4
    gap = LETTER_GAP_SPACES * spacing
    reach = int(round(gap + 2.0 * spacing))
    wy0, wy1 = max(0, y0 - hgt), min(mask.shape[0], y1 + hgt)
    out: Dict[str, Any] = {}
    for side, (a, b) in (("left", (max(0, x0 - reach), x0)),
                         ("right", (x1, min(mask.shape[1], x1 + reach)))):
        nearest = None
        if b > a:
            win = mask[wy0:wy1, a:b]
            if len(exclude):
                win = win.copy()
                for ex in exclude:
                    ex0, ey0, ex1, ey1 = (int(round(v)) for v in ex)
                    win[max(0, ey0 - 2 - wy0):max(0, ey1 + 2 - wy0),
                        max(0, ex0 - 2 - a):max(0, ex1 + 2 - a)] = 0
            n, _lab, st, _c = _cv2.connectedComponentsWithStats(win, 8)
            for i in range(1, n):
                cx, cy, cw, ch, area = (int(st[i, k]) for k in range(5))
                if not (0.25 * spacing <= ch <= 2.2 * spacing
                        and cw <= 2.0 * spacing and area >= 0.16 * cw * ch):
                    continue    # not a letter's size or fill (a stem, a slur)
                gy0, gy1 = wy0 + cy, wy0 + cy + ch
                if gy1 < r0 or gy0 > r1:
                    continue    # not on the letter's own line
                dist = (x0 - (a + cx + cw)) if side == "left" else ((a + cx) - x1)
                dist = max(0, dist)
                nearest = dist if nearest is None else min(nearest, dist)
        out[side] = nearest is not None and nearest <= gap
        out[f"{side}_spaces"] = (round(nearest / spacing, 2)
                                 if nearest is not None else None)
    return out


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


#: `OMR_VERTICAL_RUNS` -- file one `Q.VERTICAL_RUN` row per vertical candidate
#: the stem opening produced, ACCEPTED OR REFUSED.
#:
#: **Default OFF**, so the ON test is an ALLOW-LIST: a typo or an empty value
#: must not switch a document ONTO an unpriced GATHER change that adds rows to
#: every record (CLAUDE.md, *A flag's OFF test must follow its DEFAULT*, where
#: five shipped flags had it backwards in one direction or the other).
VERTICAL_RUNS_ENV = "OMR_VERTICAL_RUNS"

#: ⚠️ Glyph indices for vertical-run candidates, offset past the detector's
#: ordinals, past `_CV_GLYPH_BASE` and past `_INK_GLYPH_BASE`, so FOUR readers
#: can never collide in one cell's key space. A collision would not raise; it
#: would silently merge a candidate row and some other reader's row into one
#: subject -- and a subject's last coordinate being a positional index is
#: exactly how `omr-ink-extent-2026-09` got 11 of 26 subjects to "match" across
#: two different documents.
_VERTICAL_RUN_GLYPH_BASE = 300_000


def vertical_runs_enabled() -> bool:
    """Is the vertical-run candidate population gathered? Default OFF.

    `research` verdict (docs/flags-2026-09.md §1) — also requires
    `OMR_RESEARCH` to name `OMR_VERTICAL_RUNS` (roadmap 0.2b).
    """
    return (os.environ.get(VERTICAL_RUNS_ENV, "0").strip().lower() in (
        "1", "true", "yes", "on") and research_enabled(VERTICAL_RUNS_ENV))


def _emit_vertical_runs(log: Log, cell: Any, sub, frame, sys_idx: int,
                        st_idx: int, candidates: Sequence[Any],
                        erased: bool) -> None:
    """One row per vertical candidate, with its fate and its page box.

    ⚠️⚠️ THE PAGE FRAME IS THE WHOLE REASON THIS FUNCTION EXISTS RATHER THAN
    A WIDER `Q.STEM`. Sean's barline test -- *a barline's two ends sit ON the
    outer staff lines; a stem's do not* -- needs the run's endpoints and
    `Q.STAFF_LINES` in ONE coordinate system, and `Q.STAFF_LINES` is PAGE px
    while every `Q.STEM` row is CELL canonical with no page fields at all. A
    canonical y is measured inside one cell rescaled so the staff span is
    constant, so two staves' canonical y are not the same quantity --
    `Q.ONSET_COLUMN` reported 1,062 columns of nothing before page pixels
    arrived. A cell that cannot supply the page frame gets `frame_note` and NO
    page fields: DECLINED, never defaulted.

    ⚠️ THE STAFF-SPACE UNIT IS THE CELL'S OWN, from `_cell_grid` -- the one
    spelling of that measurement -- and never the nominal 100 px.
    `_upscale_to_canonical` scales a too-wide cell by WIDTH, so the nominal is
    wrong on a minority of cells and silently so.
    """
    from ..line_detection import RUN_DIMENSION_REASONS, RUN_ACCEPTED
    up = getattr(cell, "upscale_factor", None)
    cell_box = getattr(cell, "bbox_page_px", None)
    page_ok = bool(up) and bool(cell_box) and len(cell_box or ()) == 4
    for i, cand in enumerate(candidates):
        g = R.glyph(cell.page_index, sys_idx, st_idx, cell.measure_index,
                    _VERTICAL_RUN_GLYPH_BASE + i)
        optional: Dict[str, Any] = {}
        if cand.line_spacing > 0:
            optional.update(
                run_width_spaces=round(cand.width_spaces, 3),
                run_height_spaces=round(cand.height_spaces, 3),
                run_staff_space_px=round(cand.line_spacing, 2))
        else:
            optional["frame_note"] = "cell has no staff-space unit"
        if page_ok:
            px0 = cell_box[0] + cand.x / up
            py0 = cell_box[1] + cand.y / up
            px1 = cell_box[0] + (cand.x + cand.w) / up
            py1 = cell_box[1] + (cand.y + cand.h) / up
            optional.update(run_bbox_page_px=[px0, py0, px1, py1],
                            run_y_top_page=py0, run_y_bottom_page=py1,
                            run_x_center_page=(px0 + px1) / 2.0)
        else:
            optional["frame_note"] = (
                "no page box: cell has no bbox_page_px/upscale_factor")
        log.observe(
            g, Q.VERTICAL_RUN,
            # ⚠️ `[x, y, w, h]`, the `Q.STEM` spelling -- NOT corners. See
            # `Q.VERTICAL_RUN`'s own comment: three box conventions disagree
            # in one record and reading one as another gives a negative width.
            (cand.x, cand.y, cand.w, cand.h),
            reader=READERS.CV_LINES, frame=frame,
            # ⚠️ WHICH FILTER FIRED, NOT A NAME FOR THE INK.
            run_outcome=cand.outcome,
            run_accepted=(cand.outcome == RUN_ACCEPTED),
            # ⚠️ Derived from the vocabulary, never a hand-list at this site:
            # §9 of the boxing proposal asks how much of this population is
            # refused BY DIMENSION, and enumerating six words here is how the
            # answer drifts from the chain that produced it.
            run_refused_by_dimension=(cand.outcome in RUN_DIMENSION_REASONS),
            run_ink_area_px=int(cand.area),
            run_ink_fill=round(cand.area / float(max(1, cand.w * cand.h)), 4),
            run_n_candidates=len(candidates),
            image="no_staff" if erased else "original",
            staff_lines_erased=erased,
            **optional)


def _notehead_boxes_for_cell(detections: Optional[Dict[str, List[Any]]],
                             sub, cell: Any = None,
                             log: Optional[Log] = None) -> Optional[list]:
    """This cell's detected notehead boxes, in CANONICAL cell coordinates.

    ⚠️ `None` when the caller supplied no detection map at all (no gate) and
    `[]` when it did and this cell holds no notehead (the gate is on and has
    nothing to protect). `_drop_paired_strokes` treats those differently on
    purpose, so this must not collapse them.

    ⚠️ CANONICAL, not page pixels. `detect_stems` works inside one measure
    cell and a stroke's box is canonical; a page-pixel head box compared with
    a canonical stroke box is the frame error `Q.ONSET_COLUMN` already paid
    for — it would silently protect nothing and read as *the gate is inert*.

    ⚠️ ROADMAP 2.39, LAST OF THE FIVE CONNECTIONS AND ITS OWN COMMIT: this
    box GATES stem/beam detection (`OMR_STEM_NOTEHEAD_GATE`), so changing
    its extent can move stem/beam results (ROADMAP 2.38/2.38b), unlike the
    other four consumers, which only ever read the ink under a box. For a
    REGULAR notehead (`geometry.is_regular_notehead`) with `cell`'s own
    canonical staff spacing available (`_cell_grid`), the STANDARD box is
    used; otherwise (no `cell`, no staff-line geometry on it, or a whole
    note / grace-cue head) the raw detector box is unchanged from before
    this round -- never a new gate where none existed, never a default
    spacing.

    ⚠️ ROADMAP 2.39b: where `log` is supplied (the caller's own GATHER log,
    ALREADY carrying `gather_notehead_recentre`'s rows -- see the pipeline
    ordering comment at its call site), the standard box above is RE-
    CENTRED on the matched-window search's own winning offset for a regular
    head whose search accepted one; a head whose search declined, never ran,
    or is outside the regular-head gate keeps the un-shifted standard box,
    exactly as before this round. `log=None` (every existing caller, every
    existing test) is BYTE-IDENTICAL to before -- CONNECT, never guess.
    """
    if detections is None:
        return None
    grid = _cell_grid(cell) if cell is not None else None
    space_canonical = grid[1] * 2.0 if grid and grid[1] else None
    heads = []
    for gi, d in enumerate(detections.get(sub.to_key()) or ()):
        name = str(getattr(d, "smufl_name", ""))
        if "notehead" not in name.lower():
            continue
        if space_canonical and is_regular_notehead(name):
            cx, cy = d.x_center, d.y_center
            if log is not None:
                g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
                recentred = log.rows(Q.NOTEHEAD_RECENTRE, g)
                if recentred:
                    dx_sp, dy_sp = recentred[-1].value
                    cx = cx + dx_sp * space_canonical
                    cy = cy + dy_sp * space_canonical
            bx0, bx1, by0, by1 = _standard_head_box(cx, cy, space_canonical)
            heads.append((bx0, by0, bx1 - bx0, by1 - by0))
        else:
            heads.append((float(d.x_canonical), float(d.y_canonical),
                          float(d.width_canonical), float(d.height_canonical)))
    return heads


def _owner_marks_for_cell(detections: Optional[Dict[str, List[Any]]],
                          sub) -> Optional[list]:
    """This cell's detected clef / key / digit / accidental / flag / rest boxes,
    `(kind, (x, y, w, h))` in CANONICAL cell coordinates, for
    `OMR_STEM_FINDER=refuse_owned` and `pair_evidence`. `None` when no detection
    map was supplied (those repairs then do nothing, never an empty gate)."""
    if detections is None:
        return None
    from ..line_detection import mark_kind
    out = []
    for d in detections.get(sub.to_key()) or ():
        kind = mark_kind(getattr(d, "smufl_name", ""))
        if kind is not None:
            out.append((kind, (float(d.x_canonical), float(d.y_canonical),
                               float(d.width_canonical),
                               float(d.height_canonical))))
    return out


def gather_cv_lines(log: Log, cells: Sequence[Any],
                    local: Dict[int, Tuple[int, int]],
                    detections: Optional[Dict[str, List[Any]]] = None) -> None:
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
        from ..line_detection import detect_lines, staged_stem_finder
    except Exception as exc:                                  # noqa: BLE001
        _stub_cv_lines(log, cells, local, "line_detection unavailable",
                       error=type(exc).__name__)
        return

    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        frame = frame_cell(c.measure_index)
        erased = getattr(c, "image_no_staff", None) is not None
        # ⚠️⚠️ FLAG-OFF PASSES NOTHING, so `detect_stems` runs exactly as it
        # always has and this rung writes not one row -- a flag-off record is
        # byte-identical to a tree without this quantity, which is the
        # `OMR_INFER` discipline ("off means ABSENT, not quiet") applied to a
        # gather change. `None` rather than an empty list is load-bearing:
        # `detect_stems` tests `candidates_out is not None`.
        runs: Optional[list] = [] if vertical_runs_enabled() else None
        # ⚠️ THE NOTEHEAD GATE ON THE PAIR RULE (`OMR_STEM_NOTEHEAD_GATE`,
        # default OFF). The boxes are handed over unconditionally when the
        # caller supplied a detection map — the FLAG is read inside
        # `detect_stems`, which is the single decision point, and with it off
        # the boxes change nothing at all. ⚠️ `detections is None` (a run with
        # no detector, which `gather_detections` supports on purpose) gives
        # `None` and therefore no gate, never an empty one.
        heads = _notehead_boxes_for_cell(detections, sub, c, log=log)
        try:
            # ⚠️ ROADMAP 2.74: `rescue_tall_beams` -- a component refused only
            # for being too TALL is a beam fused to a hairpin's line or a
            # slur's tail (2.65 tile 1); it is re-opened with a kernel thicker
            # than a hairpin and read like any other. STAGED only: the legacy
            # callers of `detect_lines` leave it off and read exactly what they
            # always read.
            found = detect_lines(c, candidates_out=runs, noteheads=heads,
                                 rescue_tall_beams=True,
                                 marks=_owner_marks_for_cell(detections, sub),
                                 stem_finder=staged_stem_finder())
        except Exception as exc:                              # noqa: BLE001
            for quantity in (Q.BEAM_STROKE, Q.STEM):
                log.abstain(sub, quantity, reader=READERS.CV_LINES,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            error=type(exc).__name__)
            # ⚠️ AND THE CANDIDATE POPULATION ABSTAINS TOO, for the same
            # reason: a reader that threw and a page with no vertical ink must
            # not produce the same record. `runs` may hold a partial list here
            # and it is DISCARDED -- half a population reported as a
            # population is worse than an abstention.
            if runs is not None:
                log.abstain(sub, Q.VERTICAL_RUN, reader=READERS.CV_LINES,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            error=type(exc).__name__)
            continue
        if runs is not None:
            if runs:
                _emit_vertical_runs(log, c, sub, frame, key[0], key[1],
                                    runs, erased)
            else:
                # ⚠️ THE ONE PLACE `NO_INK` IS HONEST FOR THIS FAMILY: the
                # opening produced no component at all, so there genuinely is
                # no vertical run here. The `Q.STEM` abstention below says the
                # same words about a different fact -- a cell whose every
                # candidate was REFUSED -- and that is the collapse this
                # quantity exists to make visible rather than to fix.
                log.abstain(sub, Q.VERTICAL_RUN, reader=READERS.CV_LINES,
                            frame=frame, reason=ABSTAIN.NO_INK,
                            image="no_staff" if erased else "original",
                            staff_lines_erased=erased)

        # ⚠️⚠️ THE STEM SET IS THE BEAM READER'S INPUT, so it is read ONCE
        # here and the two families get different words. `detect_beams` takes
        # the strokes `detect_stems` returned; where there are fewer than two
        # of them no beam can be joined in this cell, whatever the page holds.
        n_stems = len(found.get("stems") or [])
        # ROADMAP 2.18c: (stem detection, its own `Q.STEM` row id), so the
        # tip-ink pass below can join back to the EXACT row it measured.
        # ROADMAP 2.38: the same for `Q.BEAM_STROKE` -- the beam-join pass
        # needs the EXACT row id of every candidate stroke too, for the same
        # reason.
        stem_rows_logged: List[Tuple[Any, str]] = []
        beam_rows_logged: List[Tuple[Any, str]] = []
        for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, "beams")):
            rows = found.get(kind) or []
            if not rows:
                # ⚠️ NOT `NO_INK`. `detect_stems` NAMES AND FILTERS IN ONE ACT
                # (`line_detection` says so at its own head), so this says
                # only what the reader knows: it ran and accepted nothing of
                # this kind. Whether candidates were FOUND AND REFUSED is on
                # the record only under `OMR_VERTICAL_RUNS`.
                reason = ABSTAIN.NO_LINE_ACCEPTED
                if quantity is Q.BEAM_STROKE and n_stems < 2:
                    reason = ABSTAIN.NO_STEMS_TO_JOIN
                log.abstain(sub, quantity, reader=READERS.CV_LINES,
                            frame=frame, reason=reason,
                            image="no_staff" if erased else "original",
                            staff_lines_erased=erased,
                            cell_n_stems=n_stems)
                continue
            for d in rows:
                row = log.observe(sub, quantity,
                            (d.x_canonical, d.y_canonical,
                             d.width_canonical, d.height_canonical),
                            reader=READERS.CV_LINES, frame=frame,
                            x0=d.x_canonical,
                            x1=d.x_canonical + d.width_canonical,
                            y_center=d.y_center,
                            image="no_staff" if erased else "original",
                            staff_lines_erased=erased)
                if quantity is Q.STEM:
                    stem_rows_logged.append((d, row.id))
                elif quantity is Q.BEAM_STROKE:
                    beam_rows_logged.append((d, row.id))

        # ROADMAP 2.18c: a second, CV witness for flag ink the detector
        # never boxed, at every stem this cell just filed. Blockers are
        # every beam stroke this SAME call already read plus every OTHER
        # LOCAL detection the detector drew in this cell (a neighbour's
        # head, an accidental, text, a slur/tie arc) -- ink the record can
        # already name is not this reader's to re-claim (CLAUDE.md rule 8).
        space_c = None
        if stem_rows_logged:
            grid = _cell_grid(c)
            space_c = grid[1] * 2.0 if grid is not None else None
            # ROADMAP 2.71: the tremolo slashes on these stems are named ONCE,
            # here, and the tip reader below is handed the raster with them
            # blanked -- a slash is not a hook.
            slashes = _observe_stem_slashes(log, sub, frame, c,
                                            stem_rows_logged, heads, space_c)
            for d, row_id in stem_rows_logged:
                stem_xywh = (float(d.x_canonical), float(d.y_canonical),
                             float(d.width_canonical),
                             float(d.height_canonical))
                # ⚠️ ROADMAP 2.75: blockers PER STEM, so a flag box hanging
                # off THIS stem's tip does not make its own tip occupied.
                blockers = _stem_tip_blockers(
                    found.get("beams") or (),
                    (detections or {}).get(sub.to_key()) or (), space_c,
                    own_stem=stem_xywh)
                if not stems_from_strokes_retires_scans():      # ROADMAP 2.204: the tip is read off the stem's stroke instead
                    _observe_stem_tip_ink(
                        log, sub, frame, c, row_id, stem_xywh,
                        blockers, space_c, heads=heads,
                        slashes=slashes.get(row_id))

        # ROADMAP 2.69 follow-up: is any `augmentationDot` box in this cell
        # really the tip of a flag? Needs the cell raster, not any stem.
        if space_c is None:
            _grid_d = _cell_grid(c)
            space_c = _grid_d[1] * 2.0 if _grid_d is not None else None
        _observe_dot_stroke_ink(log, sub, frame, c,
                                (detections or {}).get(sub.to_key()), space_c)

        # ROADMAP 2.131: is a dot-class box a round dot or a staccatissimo
        # wedge? Same raster, same detections.
        if mark_shape_enabled() and not mark_shape_line_removed_enabled():
            _observe_mark_shape(log, sub, frame, c,
                                (detections or {}).get(sub.to_key()), space_c)

        # ROADMAP 2.38: a second, independent witness for the beams_
        # ambiguous population -- does THIS stem's own ink run unbroken
        # into THIS candidate stroke's ink at the tip? One pair at a time,
        # both ends, every stem against every stroke this cell just filed.
        if stem_rows_logged and beam_rows_logged:
            if space_c is None:
                grid = _cell_grid(c)
                space_c = grid[1] * 2.0 if grid is not None else None
            _observe_beam_stem_join(
                log, sub, frame, c, stem_rows_logged, beam_rows_logged,
                space_c)


def _stub_cv_lines(log: Log, cells, local, note: str,
                   error: Optional[str] = None) -> None:
    """File the beam/stem abstentions for a rung that cannot run.

    ROADMAP 2.61b: `error` (an exception class name) means the reader EXISTS
    and its import failed -- a defect, filed `READER_UNAVAILABLE` with
    `detail["error"]`. With no `error` the reader is genuinely not written and
    the word stays `NOT_IMPLEMENTED` (build progress, to `gather_coverage`).
    """
    reason, detail = _stub_reason(error)
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
                        reason=reason, note=note, **detail)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.18c -- flag ink at a stem's tip the detector never boxed.
#
# `benchmarks/omr-missing-notes-2026-09/FINDINGS.md` SS11.4b: after 2.18b, 53
# stemmed black heads on Breitkopf p1 stand at their head value with no beam
# and no flag READ, and a by-eye pass found ~6 of them PRINT a flag nothing on
# the record witnesses -- `duration_narrowed`'s own missing-flag path, sized
# and left because no row said *ink hangs off this stem tip*. This is that
# row: a SECOND witness, off the raster, for exactly the population the
# detector's own flag boxes already witness for the other 106 (2.18b SS11.4a).
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️⚠️ ROADMAP 2.83 (Sean, 2026-10-10, DECISIONS) REPLACES 2.18c's WINDOW. 2.18c tested ink 1.0-2.5 staff spaces back from
#: the tip, 0.9 wide, at a density of 0.30, and called every one of those numbers CONVENTION ASSUMED / NOT CONFIRMED, falsified
#: by "a print-confirmed flag whose hook sits entirely inside 1.0 space of its tip". Sean: *"There are 8th note flags that are
#: not being seen. We need to make sure the reader box is big enough. Sometimes the flag stays closer to the stem at the tip but
#: the flag shape is undeniable."* MEASURED, on his hand-truth page (Brahms 317803 pdf 0, his 34 `flag8th*` boxes, FINDINGS
#: 2.83, `probe/l283_flag_geometry.py`), in LOCAL staff spaces along the stem from its tip (t = 0 at the tip, + toward the head)
#: and out from its right edge (u): a flag's box begins at t = 0.07 (median; -0.19 .. 0.43), ends at t = 3.12 (2.82 .. 3.76) and
#: stands out to u = 1.13 (0.84 .. 1.34); on the staff-ERASED raster the reader sees, its ink is a wedge ROOT at the tip and a thin
#: ARM 0.6-1.1 spaces out, and the arm alone is what 2.18c's window sampled: 20 of his 21 flags (the ones the CV rung found a stem
#: for) read 0.13-0.29 against 0.30. NUMBERS BELOW ARE THAT PAGE'S, chosen on it, each with its margin in FINDINGS 2.83; they are
#: CONVENTION ASSUMED beyond it (Litolff, any other plate) and WOULD BE FALSIFIED by a print-confirmed eighth flag this reads
#: as `None` or `False`, or by a print-confirmed non-flag it reads `True`.
#:
#: WHAT IS READ. Not a density: the ink CONNECTED to the stem near its tip (a flag hangs from it), from the tip itself back
#: toward the stem's own head, on the stem's RIGHT (a flag is printed on one side of its stem). Three answers, and only the
#: first two are claims:
#:   `found True`   the attached ink starts at the tip (<= `STEM_TIP_INK_ROOT_MAX_SPACES`), stands out between
#:                  `STEM_TIP_INK_OUT_MIN_SPACES` and `STEM_TIP_INK_OUT_MAX_SPACES` and has an arm of at least
#:                  `STEM_TIP_INK_ARM_MIN_SPACES` -- a hook.
#:   `found False`  NOTHING hangs from the tip (attached ink under `STEM_TIP_INK_EMPTY_AREA` square spaces).
#:   `found None`   ink hangs there that is not flag-shaped (a beam or a slur that runs on, ink on BOTH sides, a bar across the
#:                  tip, a stub that starts nowhere near it) or the tip cannot be read at all: CANNOT TELL. It is never turned
#:                  into `False` (CLAUDE.md rule 8): the bare-stem readers use `False` as a positive "nothing here".
STEM_TIP_INK_NEAR_SPACES = -0.3
STEM_TIP_INK_FAR_SPACES = 3.6
#: The window starts this far PAST the tip (a rounded tip, a flag root drawn over the stem's end) and runs back this far, but
#: never into the stem's own head (`head_edge`): the head's ink is attached to the stem too. A window shallower than
#: `STEM_TIP_INK_MIN_DEPTH_SPACES` (a head close to the tip) cannot say either way.
STEM_TIP_INK_MIN_DEPTH_SPACES = 1.2
#: The width of the density bands reported as `right` / `left` (the 2.18c numbers, kept as a MEASURE for the trace and the print
#: checks; they decide nothing now), and how far right the connected ink is followed, so a beam that runs on shows itself.
STEM_TIP_INK_WIDTH_SPACES = 0.9
STEM_TIP_INK_REACH_SPACES = 2.6
#: The stem's own ink in the first spaces from the tip seeds the connected ink. A stem box is a little thinner than its ink: ink
#: within this far of the box is the stem's own edge, not a mark.
STEM_TIP_INK_SEED_SPACES = 1.0
STEM_TIP_INK_EDGE_SPACES = 0.15
#: The shape. His 21 read flags: out 0.50 .. 1.34, arm 0.62 .. 2.5 spaces, first ink 0.42 .. 0.81 spaces from the tip; the nearest non-flags
#: (ledger-line stubs, a staff-line remnant) 0.31 .. 1.4 out with an arm of 0.06 .. 0.37 starting 1.1 .. 3.0 spaces in. The first
#: re-gathers then showed flags his page does not hold -- HUGGING flags whose arm stays within 0.33-0.45 spaces of the stem (Brahms pdf
#: 25: 8 of 82 stems the cuts declined, every one a flag on the print) and a big Litolff flag whose ink starts 1.33 spaces from the tip --
#: so a flag is read as EITHER a thin one (out >= `STEM_TIP_INK_OUT_MIN_SPACES`, arm >= `STEM_TIP_INK_ARM_MIN_SPACES`, root within
#: `STEM_TIP_INK_ROOT_MAX_SPACES`) OR a developed one (out >= `STEM_TIP_INK_BIG_OUT_SPACES`, arm >= `STEM_TIP_INK_BIG_ARM_SPACES`, root
#: within `STEM_TIP_INK_ROOT_BIG_SPACES`). ARM_MIN stands between the largest non-flag arm (0.37) and the smallest flag's (0.41).
STEM_TIP_INK_OUT_MIN_SPACES = 0.33
STEM_TIP_INK_OUT_MAX_SPACES = 1.5
STEM_TIP_INK_ARM_MIN_SPACES = 0.40
STEM_TIP_INK_ARM_U_SPACES = 0.35
STEM_TIP_INK_ROOT_MAX_SPACES = 1.2
STEM_TIP_INK_BIG_OUT_SPACES = 0.8
STEM_TIP_INK_BIG_ARM_SPACES = 1.0
STEM_TIP_INK_ROOT_BIG_SPACES = 1.6
#: ⚠️ ROADMAP 2.83 FIX ROUND (Sean's blind tile 2, Brahms pdf 16 `glyph/16/1/10/6/5`: a DOTTED QUARTER read as a flag, the narrowing {1,2} left
#: its answer out). A flag begins AT the tip: its root is the stem's own last row. Attached ink that begins more than this far PAST the tip is not
#: a flag but something the stem runs into -- there the letters of an `ff` printed against the stem's end (`t_first` -0.29, a box covering 0.028
#: square spaces of it, under `STEM_TIP_COVER_AREA_MIN`) -- or a stem whose CV box stops short of its printed end. CANNOT TELL, never a flag.
#: MEASURED: Sean's 21 flags with a stem start 0.42-0.81 spaces in and the Litolff reads that start 0.0 .. 0.1 are untouched; 5 of 79 flag reads on
#: the Litolff tile pages sat at the window's edge (-0.30); by eye none of the 3 stems among them looked at on the print was a clean eighth flag (a
#: dyad's other head, a slur, a cluster). Falsified by a print-confirmed flag whose ink starts more than 0.15 spaces beyond the stem's end.
STEM_TIP_INK_PAST_TIP_MIN_SPACES = -0.15
#: Attached ink on the stem's LEFT beyond its own edge (square spaces): a flag hangs from one side only. A speck under this is the
#: stem's own noise (Brahms pdf 21 `glyph/21/1/7/0/8`: a flag read `crosses_both_sides` at 0.05).
STEM_TIP_INK_LEFT_AREA_MAX = 0.08
STEM_TIP_INK_EMPTY_AREA = 0.02
#: A detection box explains the attached ink only where it COVERS at least this much of it (square spaces): detector boxes are loose, and
#: a neighbouring rest's box edge grazed a flag's outer arm by 0.001 (Brahms pdf 25 `glyph/25/0/13/1/3`).
STEM_TIP_COVER_AREA_MIN = 0.05
#: ⚠️ BROKEN FLAGS (ROADMAP 2.83, found by Sean's tile 04 and a by-eye scan of Brahms pdf 1 and 20). A scan and the staff-line eraser
#: often leave a hairline break between a flag's wedge at the tip and its arm, so the arm is a SEPARATE component and the attached ink
#: alone (a stub: out 0.3, no arm) is not flag-shaped. A component the reader would otherwise leave out is taken as part of the flag
#: where it stands within `STEM_TIP_FRAG_GAP_SPACES` of the stem-attached ink, wholly right of the stem's edge, starts within
#: `STEM_TIP_FRAG_T_MAX_SPACES` of the tip, holds at least `STEM_TIP_FRAG_AREA_MIN` square spaces and is at least
#: `STEM_TIP_FRAG_WIDTH_MIN_SPACES` wide (a neighbour's stem is a 0.2-wide line and is never taken). The union is then read by the
#: SAME shape test and covered by the SAME blockers, so a beam fragment runs on, a detection's ink makes the tip `occupied`, and a
#: ledger stub has no arm. MEASURED: of 34 + 14 + 1 stems on Brahms pdf 20, pdf 1 and Litolff pdf 3 the attached-only reader declined
#: and this reads as a flag, every one looked at on the print is a flag; on Sean's page it adds 1 of his 21 and reads none of the 131
#: non-flags.
STEM_TIP_FRAG_GAP_SPACES = 0.35
STEM_TIP_FRAG_T_MAX_SPACES = 1.6
STEM_TIP_FRAG_AREA_MIN = 0.25
STEM_TIP_FRAG_WIDTH_MIN_SPACES = 0.3
#: A fragment at least this share of which stands under ANOTHER mark's detection box (`blockers`; a rest, a beam stroke, a head) is that
#: mark's ink, not a piece of the flag, and is not taken in: the first v4 re-gather lost 7 flags (Brahms pdf 25 `glyph/25/0/4/0/7`, six on
#: Litolff) because a neighbouring `rest8th` or beam stroke standing 0.2-0.3 spaces from the flag was unioned with it and then made the
#: tip `occupied`. The stem's OWN flag boxes are not blockers, so a broken flag under its own box is still taken in.
STEM_TIP_FRAG_EXPLAINED = 0.5

#: ROADMAP 2.73, REWRITTEN AT 2.83. A ROW A LINE CROSSES: attached ink standing out on BOTH sides of the stem at one row (the
#: stem's side `STEM_TIP_LINE_NEAR_U` on each, and beyond it on at least one) is a staff- or ledger-line stub or a slur's belly,
#: never a flag. A run of such rows no thicker than `STEM_TIP_LINE_MAX_THICK_SPACES` is a line and is left out of every measure
#: (a ledger line is ~0.3 spaces thick; the legs of a tip standing ON a line are why 2.73 existed); a thicker run is a BAR (a beam
#: crossing the tip measures 0.46 .. 0.62) and the tip is not readable. Where lines take more than half the window the reading is
#: declined. The ledger line's far end reaches the stem's head side (it is centred on the head, not on the stem), so the two
#: sides are NOT symmetric: that is why the test is "both near, either far".
STEM_TIP_LINE_NEAR_U_SPACES = 0.30
STEM_TIP_LINE_FAR_U_SPACES = 0.90
STEM_TIP_LINE_FILL = 0.6
STEM_TIP_LINE_MAX_THICK_SPACES = 0.45

#: ROADMAP 2.73 (applied to the ink since 2.83). A detection box counts as explaining the ink at the tip only if it covers that ink
#: by more than this much (staff spaces) in BOTH axes. Detector box edges are good to about a tenth of a space; a box that merely
#: touches the ink's edge (Litolff p6, 2.70 tiles #4/#6: an `arpeggiato` box that IS the stem's own ink ending 1 px into the
#: window, a neighbour's head box ending 1-5 px into it) explains none of it.
STEM_TIP_BLOCKER_TOLERANCE_SPACES = 0.1

#: ROADMAP 2.104 (Sean 2026-10-13, 2.97 round-3 tile 3 and Brahms pdf 0 hand-truth `q1009`: a flagged eighth the tip reader
#: abstained `occupied` on). A detection box covering the ink at a tip made it `occupied` and the SHAPE was never read: on Brahms
#: pdf 0-1 the boxes were a mid-bar `clefF` the detector drew round the stem and its flag (score 0.31), a `ledgerLine` box over a
#: ledger line crossing the stem near its head, a `dynamicF` and two `arpeggiato` boxes. `OMR_TIP_UNBLOCKED=1`: where the tip is
#: `occupied` and the 2.18c window cannot say either, the SHAPE test is read ONCE MORE with the boxes set aside; only a flag-shaped
#: reading (`found True`) is filed (witness `shape_unblocked`). Any other result -- not
#: flag-shaped, runs on, ink past the tip, nothing -- leaves the `occupied` abstention exactly as before (rule 8: never a False).
#: DEFAULT ON since 2026-10-13 (Sean's 9/9 on `out/print/2.104-review/`: "go ahead switch on and land"); a DENY-LIST, so a typo or an
#: empty value leaves it RUNNING and only an explicit off-word turns it off. Measured on Sean's hand-truth page (FINDINGS 2.104).
TIP_UNBLOCKED_ENV = "OMR_TIP_UNBLOCKED"


def tip_unblocked_enabled() -> bool:
    return os.environ.get(TIP_UNBLOCKED_ENV, "1").strip().lower() not in ("0", "", "false", "no", "off")


def _tip_line_rows(right: Any, left: Any, us: Any, ul: Any, space: float
                   ) -> Tuple[Any, Optional[float]]:
    """`(on_line, bar)`: which rows of the attached ink a THIN LINE crosses, and the thickness (spaces) of the first run
    that is a BAR instead (`None` if none is). `right`/`left` are boolean masks (rows x columns) of the stem-attached ink
    on each side, `us`/`ul` the distance of each column from the stem's right/left edge in spaces. ROADMAP 2.83 (the
    one spelling both `stem_tip_ink` and `stem_tip_hooks` use, so the two readers drop the same rows)."""
    import numpy as np

    def fill(m: Any, u: Any, lo: float, hi: float) -> Any:
        cols = (u >= lo) & (u <= hi)
        return m[:, cols].mean(axis=1) if cols.any() else np.zeros(m.shape[0])
    near = (fill(right, us, 0.04, STEM_TIP_LINE_NEAR_U_SPACES) >= STEM_TIP_LINE_FILL) \
        & (fill(left, ul, 0.04, STEM_TIP_LINE_NEAR_U_SPACES) >= STEM_TIP_LINE_FILL)
    far = (fill(right, us, STEM_TIP_LINE_NEAR_U_SPACES, STEM_TIP_LINE_FAR_U_SPACES) >= STEM_TIP_LINE_FILL) \
        | (fill(left, ul, STEM_TIP_LINE_NEAR_U_SPACES, STEM_TIP_LINE_FAR_U_SPACES) >= STEM_TIP_LINE_FILL)
    on_line = near & far
    run = 0
    for v in list(on_line) + [False]:
        if v:
            run += 1
            continue
        if run > STEM_TIP_LINE_MAX_THICK_SPACES * space:
            return on_line, run / space
        run = 0
    # a stripe's rows one pixel either side belong to it
    return on_line | np.roll(on_line, 1) | np.roll(on_line, -1), None


def stem_tip_ink(img: Any, stem_x0: float, stem_x1: float, tip_y: float,
                 into_sign: float, space: float,
                 head_edge: Optional[float] = None,
                 blockers: Optional[Sequence[Tuple[float, float, float, float]]] = None
                 ) -> Optional[Dict[str, Any]]:
    """Does a FLAG hang from this stem's tip? ROADMAP 2.18c, REPLACED AT 2.83 (see the block above).

    `stem_x0`, `stem_x1`, `tip_y`, `head_edge` and `space` are all in the SAME canonical CELL pixels `Q.STEM`'s own box is
    in -- this function does no frame conversion, the same contract `ledger_rung_ink` states for itself. `into_sign` is
    `+1.0` to test the stem's TOP as its tip (walk DOWN, into the body -- an up-stem's shape) or `-1.0` to test the BOTTOM;
    GATHER does not know which end is the true tip -- that is `Q.STEM_DIRECTION`'s question, decided later in ADJUDICATE --
    so the caller asks both and files one row each. `head_edge` is where the stem's own head begins along the walk (the same
    value `stem_tip_hooks` takes): the window stops short of it. `blockers` are the corner boxes (`x0, y0, x1, y1`) of every
    OTHER mark the record already names here (`_stem_tip_blockers`): a box that covers INK ATTACHED TO THE STEM makes the tip
    `occupied` (`found None`, `why = "occupied"`) -- that ink is that mark's, not a flag's. ⚠️ A box that merely stands NEAR the
    tip does not: 2.18c abstained on any box overlapping its window, and the wider window this reader needs (a flag stands out
    to 1.34 spaces) then overlapped a flat 1.3 spaces from the stem and lost a flag the old reader had counted (Brahms pdf 1
    `glyph/1/0/3/3/0`, FINDINGS 2.83): what a box can explain is the ink it covers.

    Returns `None` where the raster or the window falls entirely off it. Otherwise a dict with `found` (`True` / `False` /
    `None`, see above) and `why` (the reason word), plus what was measured: `right` / `left` (ink density of the 0.9-space
    bands beside the stem, lines left out; a MEASURE, decides nothing), `area` (attached ink right of the stem, square
    spaces), `left_area`, `out`, `arm` and `t_first` (spaces), `line_rows_left_out` (rows) and `window_canonical`.
    """
    if img is None or getattr(img, "ndim", 0) != 2 or not space or space <= 0:
        return None
    import cv2
    import numpy as np
    ink = (img == 0)
    H, W = ink.shape
    far = STEM_TIP_INK_FAR_SPACES
    if head_edge is not None:
        far = min(far, (head_edge - tip_y) * into_sign / space - 0.1)
    far = max(far, STEM_TIP_INK_NEAR_SPACES)
    ya, yb = sorted((tip_y + into_sign * STEM_TIP_INK_NEAR_SPACES * space, tip_y + into_sign * far * space))
    xa = max(0, int(round(stem_x0 - 1.0 * space)))
    xb = min(W, int(round(stem_x1 + STEM_TIP_INK_REACH_SPACES * space)))
    ya, yb = max(0, int(round(ya))), min(H, int(round(yb)))
    if yb - ya < 4 or xb - xa < 4:
        return None
    out: Dict[str, Any] = {
        "found": None, "why": None,
        "window_canonical": [round(stem_x1, 2), round(ya, 2),
                             round(stem_x1 + STEM_TIP_INK_WIDTH_SPACES * space, 2), round(yb, 2)]}
    if far < STEM_TIP_INK_MIN_DEPTH_SPACES:
        out["why"] = "no_room"
        return out
    sub = ink[ya:yb, xa:xb].astype(np.uint8)
    k = max(1, int(round(0.06 * space)))
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n_lab, lab, lab_stats, _cent = cv2.connectedComponentsWithStats(sub, connectivity=8)
    sx0, sx1 = max(0, int(round(stem_x0)) - xa), min(sub.shape[1], int(round(stem_x1)) - xa + 1)
    ts = (np.arange(ya, yb) - tip_y) * into_sign / space           # spaces from the tip, + toward the head
    us = (np.arange(xa, xb) - stem_x1) / space                     # spaces right of the stem's right edge
    ul = (stem_x0 - np.arange(xa, xb)) / space                     # spaces left of its left edge
    seed_rows = (ts >= STEM_TIP_INK_NEAR_SPACES) & (ts <= STEM_TIP_INK_SEED_SPACES)
    seeds = set(np.unique(lab[np.ix_(seed_rows, np.arange(sx0, sx1))]).tolist()) - {0} if sx1 > sx0 else set()
    if not seeds:
        out["why"] = "no_stem_ink"
        return out
    comp = np.isin(lab, list(seeds))
    # BROKEN FLAGS: the fragments a hairline break leaves beside the attached ink (see `STEM_TIP_FRAG_*`)
    frag_labels = []
    for i in range(1, n_lab):
        if i in seeds:
            continue
        fx, fy, fw, fh, farea = (int(v) for v in lab_stats[i])
        if farea < STEM_TIP_FRAG_AREA_MIN * space * space or fw < STEM_TIP_FRAG_WIDTH_MIN_SPACES * space \
                or us[fx] < 0.05 or min(ts[fy], ts[fy + fh - 1]) > STEM_TIP_FRAG_T_MAX_SPACES:
            continue
        frag_labels.append(i)
    if frag_labels:
        dist = cv2.distanceTransform((~comp).astype(np.uint8), cv2.DIST_L2, 3)
        boxed = np.zeros(sub.shape, dtype=bool)          # the ink another mark's box explains (`blockers`, edges trimmed)
        tol = STEM_TIP_BLOCKER_TOLERANCE_SPACES * space
        for bx0, by0, bx1, by1 in (blockers or ()):
            c0, c1 = max(0, int(np.floor(bx0 + tol - xa))), min(sub.shape[1], int(np.ceil(bx1 - tol - xa)))
            r0, r1 = max(0, int(np.floor(by0 + tol - ya))), min(sub.shape[0], int(np.ceil(by1 - tol - ya)))
            if c1 > c0 and r1 > r0:
                boxed[r0:r1, c0:c1] = True
        for i in frag_labels:
            m = lab == i
            if float(dist[m].min()) > STEM_TIP_FRAG_GAP_SPACES * space:
                continue
            if float(boxed[m].mean()) >= STEM_TIP_FRAG_EXPLAINED:
                continue                                  # another mark's ink (a rest, a beam): a box explains the ink it covers
            comp = comp | m
    right = comp & (us[None, :] > 0.04)
    left = comp & (ul[None, :] > 0.04)
    on_line, bar = _tip_line_rows(right, left, us, ul, space)
    if bar is not None:
        out.update(why="crosses_both_sides", bar=round(bar, 2), line_rows_left_out=0)
        return out
    out["line_rows_left_out"] = int(on_line.sum())
    keep = ~on_line
    if keep.sum() < 0.5 * len(keep):
        out["why"] = "lines_take_the_window"
        return out
    # the density bands (a measure for the trace; 2.18c's numbers, read over the rows no line crosses)
    wcols_r = (us > 0.0) & (us <= STEM_TIP_INK_WIDTH_SPACES)
    wcols_l = (ul > 0.0) & (ul <= STEM_TIP_INK_WIDTH_SPACES)
    ink_sub = ink[ya:yb, xa:xb][keep]
    out["right"] = round(float(ink_sub[:, wcols_r].mean()), 4) if wcols_r.any() else 0.0
    out["left"] = round(float(ink_sub[:, wcols_l].mean()), 4) if wcols_l.any() else 0.0
    right, left, ts_kept = right[keep], left[keep], ts[keep]
    edge_r, edge_l = us >= STEM_TIP_INK_EDGE_SPACES, ul >= STEM_TIP_INK_EDGE_SPACES
    left_area = float(left[:, edge_l].sum()) / (space * space)
    right_far = right[:, edge_r]
    area = float(right_far.sum()) / (space * space)
    out.update(area=round(area, 3), left_area=round(left_area, 3))
    if left_area > STEM_TIP_INK_LEFT_AREA_MAX:
        out["why"] = "crosses_both_sides"
        return out
    if area < STEM_TIP_INK_EMPTY_AREA:
        out.update(found=False, why="empty")
        return out
    if blockers:
        tol = STEM_TIP_BLOCKER_TOLERANCE_SPACES * space
        keep_idx, far_cols = np.where(keep)[0], np.where(edge_r)[0]
        for bx0, by0, bx1, by1 in blockers:
            c0, c1 = int(np.floor(bx0 + tol - xa)), int(np.ceil(bx1 - tol - xa))
            r0, r1 = int(np.floor(by0 + tol - ya)), int(np.ceil(by1 - tol - ya))
            if c1 <= c0 or r1 <= r0:
                continue
            rsel = np.where((keep_idx >= r0) & (keep_idx < r1))[0]
            csel = np.where((far_cols >= c0) & (far_cols < c1))[0]
            if rsel.size and csel.size:
                covered = float(right_far[np.ix_(rsel, csel)].sum()) / (space * space)
                out["covered_area"] = max(out.get("covered_area", 0.0), round(covered, 3))
                if covered >= STEM_TIP_COVER_AREA_MIN:
                    out["why"] = "occupied"
                    return out
    reach = float(us[edge_r][np.where(right_far.any(axis=0))[0]].max())
    out["out"] = round(reach, 2)
    if reach > STEM_TIP_INK_OUT_MAX_SPACES:
        out["why"] = "runs_on"
        return out
    arm = float(right[:, us > STEM_TIP_INK_ARM_U_SPACES].any(axis=1).sum()) / space
    t_first = float(ts_kept[right_far.any(axis=1)].min())
    out.update(arm=round(arm, 2), t_first=round(t_first, 2))
    if t_first < STEM_TIP_INK_PAST_TIP_MIN_SPACES:
        out["why"] = "ink_past_the_tip"
        return out
    thin = reach >= STEM_TIP_INK_OUT_MIN_SPACES and arm >= STEM_TIP_INK_ARM_MIN_SPACES \
        and t_first <= STEM_TIP_INK_ROOT_MAX_SPACES
    developed = reach >= STEM_TIP_INK_BIG_OUT_SPACES and arm >= STEM_TIP_INK_BIG_ARM_SPACES \
        and t_first <= STEM_TIP_INK_ROOT_BIG_SPACES
    if thin or developed:
        out.update(found=True, why="shaped")
        return out
    out["why"] = "ink_not_flag_shaped"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.83 FIX ROUND -- the 2.18c density window, KEPT as the SECOND witness at the tip.
#
# Sean judged the 2.83 tiles 2026-10-11: tiles 4 and 8 (Litolff pdf 13, one cell) are EIGHTHS the 2.18c window counted (`hooks_counted{1}`) and
# the shape reader above could not tell (the flag's arm touches a neighbour: `runs_on`), so the head fell back to a decided quarter. The
# coordinator's rule (CLAUDE.md rule 8): the new reader may ADD a witness, never REMOVE one. The 2.18c reading -- ink density in a window
# 1.0 to 2.5 spaces back from the tip, 0.9 wide, against 0.30, with the mirrored left band as the background guard, and ANY detection box
# overlapping the window making it `occupied` -- is therefore still taken, unchanged, and `_observe_stem_tip_ink` combines the two:
#   shape True                     -> True (the shape reader's claim; unchanged)
#   shape cannot tell, window True -> True, `witness = "window"` (what the base said, and was right on tiles 4 and 8)
#   shape False, window True       -> a DISPUTE: a True row with `tip_disagree` -- the shape reader positively sees nothing hanging from
#                                     the tip and the window sees a hook. ADJUDICATE NARROWS {0, the counted level} and never decides 0.
#   shape False, window not True   -> False (as v5)
#   shape cannot tell, window not True -> an ambiguous abstention (as v5: a base `False` there was the wrong-halves of 2.70, tile 6)
# The end a notehead stands at (`head_at_this_end`) is a positive fact about the stem, not a cannot-tell: the window is not consulted there.
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT: the window's `True` is a witness of low recall (1 of Sean's 21 flags) but not of bad precision
# (0 of his 46 bare stems, 1 of 85 beam stems); where the shape reader is silent it is the only reading the base had. Falsified by an
# eighth-less stem on which the window is True and the shape reader cannot tell, that Sean reads as a quarter.
# ─────────────────────────────────────────────────────────────────────────────
STEM_TIP_WINDOW_NEAR_SPACES = 1.0
STEM_TIP_WINDOW_FAR_SPACES = 2.5
STEM_TIP_WINDOW_WIDTH_SPACES = 0.9
STEM_TIP_WINDOW_DENSE = 0.30
STEM_TIP_WINDOW_BACKGROUND_MAX = 0.20
STEM_TIP_WINDOW_LINE_PROBE_SPACES = 0.6
STEM_TIP_WINDOW_LINE_ROW_FILL = 0.7
STEM_TIP_WINDOW_LINE_ROWS_MAX_LOST = 0.5


def stem_tip_window(img: Any, stem_x0: float, stem_x1: float, tip_y: float,
                    into_sign: float, space: float) -> Optional[Dict[str, Any]]:
    """The 2.18c reading, byte for byte: is a 0.9-space window 1.0 to 2.5 spaces back from the tip, to the stem's RIGHT, at least 30%
    inked while the mirrored window on its LEFT is not (a flag hangs from one side only)? Staff and ledger line rows (ink in both probes
    just beyond the two bands) are left out (2.73); where they take more than half the window it is declined. `None` where the raster
    or a band falls off it. Same frame and contract as `stem_tip_ink` (canonical CELL pixels, `into_sign` +1 walks DOWN from a top tip).
    """
    if img is None or getattr(img, "ndim", 0) != 2 or not space or space <= 0:
        return None
    ink = (img == 0)
    H, W = ink.shape
    width = STEM_TIP_WINDOW_WIDTH_SPACES * space
    near = STEM_TIP_WINDOW_NEAR_SPACES * space
    far = STEM_TIP_WINDOW_FAR_SPACES * space
    y_near, y_far = tip_y + into_sign * near, tip_y + into_sign * far
    y0, y1 = (y_near, y_far) if y_near <= y_far else (y_far, y_near)
    iy0w, iy1w = max(0, int(round(y0))), min(H, int(round(y1)))
    keep_rows = None
    lost_rows = 0
    if iy1w > iy0w:
        probe = STEM_TIP_WINDOW_LINE_PROBE_SPACES * space
        lo_l, hi_l = int(round(stem_x0 - width - probe)), int(round(stem_x0 - width))
        lo_r, hi_r = int(round(stem_x1 + width)), int(round(stem_x1 + width + probe))
        keep_rows = []
        for yy in range(iy0w, iy1w):
            lft = ink[yy, max(0, lo_l):max(0, hi_l)]
            rgt = ink[yy, max(0, lo_r):min(W, max(0, hi_r))]
            on_line = bool(lft.size and rgt.size
                           and lft.mean() >= STEM_TIP_WINDOW_LINE_ROW_FILL
                           and rgt.mean() >= STEM_TIP_WINDOW_LINE_ROW_FILL)
            if not on_line:
                keep_rows.append(yy)
        lost_rows = (iy1w - iy0w) - len(keep_rows)
        if lost_rows > STEM_TIP_WINDOW_LINE_ROWS_MAX_LOST * (iy1w - iy0w) or not keep_rows:
            return None

    def frac(x0: float, x1: float) -> Optional[float]:
        ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
        iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
        if ix1 <= ix0 or iy1 <= iy0:
            return None
        region = ink[iy0:iy1, ix0:ix1]
        if keep_rows is not None and lost_rows:
            region = ink[keep_rows, ix0:ix1]
        return float(region.sum()) / float(region.size)

    right = frac(stem_x1, stem_x1 + width)
    left = frac(stem_x0 - width, stem_x0)
    if right is None or left is None:
        return None
    found = right >= STEM_TIP_WINDOW_DENSE and left <= STEM_TIP_WINDOW_BACKGROUND_MAX
    return {"found": bool(found), "right": round(right, 4), "left": round(left, 4),
            "line_rows_left_out": lost_rows,
            "window_canonical": [round(stem_x1, 2), round(y0, 2), round(stem_x1 + width, 2), round(y1, 2)]}


def stem_tip_window_blocked(blockers: Sequence[Tuple[float, float, float, float]], stem_x1: float, tip_y: float,
                            into_sign: float, space: float) -> bool:
    """2.18c's own guard: does ANY box in `blockers` overlap the density window (edges trimmed 0.1 spaces)? Then the window is not read."""
    near, far = STEM_TIP_WINDOW_NEAR_SPACES * space, STEM_TIP_WINDOW_FAR_SPACES * space
    width = STEM_TIP_WINDOW_WIDTH_SPACES * space
    wy0, wy1 = sorted((tip_y + into_sign * near, tip_y + into_sign * far))
    tol = STEM_TIP_BLOCKER_TOLERANCE_SPACES * space
    shrunk = (stem_x1 + tol, wy0 + tol, stem_x1 + width - tol, wy1 - tol)
    return any(_rects_overlap(shrunk, b) for b in blockers)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.69 -- COUNT the hooks at a stem tip (Sean, 2026-10-09).
#
# *"Count the hooks and if you can't count use the fact that there is a hook
# to help later deduction process."* `stem_tip_ink` says a hook is THERE; this
# says how many, off the same staff-erased raster, where the ink lets it, and
# says WHY NOT where it does not (a reason word in the row's detail, never a
# default). The adjudicator decides a counted level and NARROWS an uncounted
# one among flag levels >= 1 only; the bar's arithmetic settles the rest.
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED with Sean (rule
# 3): each hook of a flag is a separate stroke leaving the stem on ONE side
# (the right, whichever way the stem points) and the strokes are stacked
# along the stem, separated by paper, so a column read to the stem's right
# crosses as many separate runs of ink as there are hooks. Falsified by a
# print-confirmed two-hook flag whose strokes touch across that whole band.
# A tremolo SLASH (Sean 2026-10-09, ROADMAP 2.71) is a thick angled line
# crossing BOTH sides of one stem and joined to no other note: ink on both
# sides of the stem in the counted band is REFUSED, never counted.
# ─────────────────────────────────────────────────────────────────────────────

#: How far along the stem from its tip the hook band reaches, in spaces.
#: Three hooks fit with room to spare; the band is cut earlier at the first
#: notehead it would run into (`head_edge`), so the stem's OWN head is never
#: counted as a hook.
STEM_TIP_HOOKS_REACH_SPACES = 3.4
#: The counted band's distance from the stem's right edge, in spaces: far
#: enough out to skip the stem's own thickness, far enough in to hold a curl.
STEM_TIP_HOOKS_NEAR_SPACES = 0.1
STEM_TIP_HOOKS_FAR_SPACES = 0.4
#: The LEFT guard's own band: the mirrored 1.2 spaces beside the stem.
STEM_TIP_HOOKS_LEFT_SPACES = 1.2
#: Healing of the staff-erase's thin stripes (they split ONE stroke into
#: two), a run's minimum thickness and the minimum paper between two runs, in
#: spaces. NOT CONFIRMED beyond the Brahms p1 population (FINDINGS 2.69).
STEM_TIP_HOOKS_CLOSE_SPACES = 0.06
STEM_TIP_HOOKS_MIN_THICK_SPACES = 0.12
STEM_TIP_HOOKS_MIN_GAP_SPACES = 0.12
#: A count of k needs k runs in at least this fraction of the INKED columns;
#: more than this share of columns showing k+1 runs means the band is not
#: clean (a stroke touching its neighbour, a slur) and the count is refused.
STEM_TIP_HOOKS_SUPPORT = 0.40
STEM_TIP_HOOKS_GLITCH = 0.12
#: A band where fewer than this share of columns hold ANY attached ink is
#: too broken a stroke to say how many there are.
STEM_TIP_HOOKS_MIN_COVERAGE = 0.5
#: Component ink to the stem's LEFT above this density means the stroke
#: crosses the stem (a slash, a slur), which a flag hook never does.
STEM_TIP_HOOKS_LEFT_MAX = 0.05
#: Where stacked hooks stand: the first leaves the stem within this many
#: spaces of the tip, and consecutive hooks leave it this far apart (spaces).
#: NOT CONFIRMED against a two-hook print on this plate (Brahms p1 holds
#: none); argued from Bravura's flag spacing and checked on the rendered
#: engraved sixteenth and thirty-second flags (FINDINGS 2.69).
STEM_TIP_HOOKS_FIRST_MAX_SPACES = 0.8
STEM_TIP_HOOKS_SPACING_MIN = 0.4
STEM_TIP_HOOKS_SPACING_MAX = 1.1
#: The longest uncounted bracket this reader will name (levels), so a noisy
#: band never opens the narrowing to a 64th.
STEM_TIP_HOOKS_MAX_LEVEL = 3

HOOKS_UNCOUNTED_NO_ROOM = "no_room"
HOOKS_UNCOUNTED_HEAD_AT_END = "head_at_this_end"
HOOKS_UNCOUNTED_BOTH_SIDES = "crosses_both_sides"
HOOKS_UNCOUNTED_TOO_LITTLE = "too_little_ink"
HOOKS_UNCOUNTED_UNRESOLVED = "unresolved"


def _runs_true(col: Any) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    start = None
    for i, v in enumerate(col):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(col)))
    return out


def stem_tip_hooks(img: Any, stem_x0: float, stem_x1: float, tip_y: float,
                   into_sign: float, space: float,
                   head_edge: Optional[float] = None,
                   line_rows: Any = None
                   ) -> Optional[Dict[str, Any]]:
    """How many hooks hang from this stem tip? ROADMAP 2.69.

    Same frame and contract as `stem_tip_ink` (canonical CELL pixels, no
    frame conversion, `into_sign` +1 = walk DOWN from the top tip). Returns a
    dict, never a guess:

    - `hooks`: the counted level (int >= 1), or `None`;
    - `hooks_min`/`hooks_max`: the bracket the ink supports (equal when
      counted) -- what the adjudicator narrows over when `hooks` is `None`;
    - `hooks_reason`: the reason word when `hooks` is `None`;
    - `hooks_support`: the share of inked columns showing >= 1, 2, 3 runs.

    `None` where the raster or the band falls off it, so the caller files
    nothing rather than a default.

    ⚠️ ONLY INK ATTACHED TO THE STEM COUNTS (8-connected, after healing the
    erase's stripes), and ink attached on BOTH sides is refused whole -- the
    slash (ROADMAP 2.71) and a crossing slur are not hooks.
    """
    if img is None or getattr(img, "ndim", 0) != 2 or not space or space <= 0:
        return None
    import cv2
    import numpy as np
    H, W = img.shape
    ya = tip_y - into_sign * 0.2 * space
    yb = tip_y + into_sign * STEM_TIP_HOOKS_REACH_SPACES * space
    if head_edge is not None:
        lim = head_edge - into_sign * 0.1 * space
        yb = min(yb, lim) if into_sign > 0 else max(yb, lim)
    y0, y1 = (ya, yb) if ya <= yb else (yb, ya)
    iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
    bx0 = int(round(stem_x1 + STEM_TIP_HOOKS_NEAR_SPACES * space))
    bx1 = int(round(stem_x1 + STEM_TIP_HOOKS_FAR_SPACES * space))
    lx0 = max(0, int(round(stem_x0 - STEM_TIP_HOOKS_LEFT_SPACES * space)))
    lx1 = int(round(stem_x0 - STEM_TIP_HOOKS_NEAR_SPACES * space))
    bx1 = min(W, bx1)
    # ROADMAP 2.83: the attached ink is followed out to where a LINE's far end stands, so the rows a thin line crosses
    # can be told (`_tip_line_rows`, the one spelling `stem_tip_ink` uses too); the runs are still counted in the band.
    cx1 = min(W, max(bx1, int(round(stem_x1 + STEM_TIP_LINE_FAR_U_SPACES * space))))
    if iy1 - iy0 < 3 or bx1 - bx0 < 3 or lx1 <= lx0 or bx0 >= W:
        return None

    def verdict(hooks, lo, hi, reason, support=()):
        return {"hooks": hooks, "hooks_min": lo, "hooks_max": hi,
                "hooks_reason": reason,
                "hooks_support": [round(s, 3) for s in support]}

    # The head at THIS end means this end is not a flag's tip; a band too
    # short for even two hooks cannot say how many there are.
    if (iy1 - iy0) < 1.2 * space:
        return verdict(None, 1, 2, HOOKS_UNCOUNTED_NO_ROOM)
    ink = (img[iy0:iy1, lx0:cx1] == 0).astype(np.uint8)
    k = max(1, int(round(STEM_TIP_HOOKS_CLOSE_SPACES * space)))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    _n, lab = cv2.connectedComponents(ink, connectivity=8)
    sc0 = max(0, int(round(stem_x0)) - lx0)
    sc1 = min(ink.shape[1], int(round(stem_x1)) - lx0 + 1)
    seeds = set(np.unique(lab[:, sc0:sc1]).tolist()) - {0}
    if not seeds:
        return verdict(None, 1, 2, HOOKS_UNCOUNTED_TOO_LITTLE)
    comp = np.isin(lab, list(seeds))
    xs = np.arange(lx0, cx1)
    us, ul = (xs - stem_x1) / space, (stem_x0 - xs) / space
    on_line, bar = _tip_line_rows(comp & (us[None, :] > 0.04), comp & (ul[None, :] > 0.04), us, ul, space)
    if bar is not None:
        return verdict(None, 1, 2, HOOKS_UNCOUNTED_BOTH_SIDES)
    keep = ~on_line
    left = comp[:, :max(0, lx1 - lx0)] & keep[:, None]
    tmin = max(2, int(round(STEM_TIP_HOOKS_MIN_THICK_SPACES * space)))
    gmin = max(2, int(round(STEM_TIP_HOOKS_MIN_GAP_SPACES * space)))
    # Ink attached to the stem on its LEFT too: either dense over the whole
    # mirrored band, or a stroke thick enough to be a mark standing in most
    # of the columns right beside the stem (a thin slur or a slash crossing
    # it is thin in density and thick in a column).
    near_left = left[:, max(0, left.shape[1] - int(round(
        STEM_TIP_HOOKS_FAR_SPACES * space))):] if left.size else left
    left_cols = sum(1 for cx in range(near_left.shape[1])
                    if any(r[1] - r[0] >= tmin
                           for r in _runs_true(near_left[:, cx]))) \
        if near_left.size else 0
    if left.size and (float(left.sum()) / float(left.size) > STEM_TIP_HOOKS_LEFT_MAX
                      or left_cols > 0.3 * near_left.shape[1]):
        return verdict(None, 1, 2, HOOKS_UNCOUNTED_BOTH_SIDES)
    band = comp[:, bx0 - lx0:bx1 - lx0] & keep[:, None]
    ks: List[int] = []
    starts: List[List[float]] = []          # per column, run near-edges (spaces from the tip)
    for cx in range(band.shape[1]):
        merged: List[Tuple[int, int]] = []
        for r in _runs_true(band[:, cx]):
            if r[1] - r[0] < tmin:
                continue
            # ROADMAP 2.126 (`OMR_HOOKS_LINE_BRIDGE`, `line_rows` is passed only then): a run that is nothing but line rows -- a ledger
            # or staff line crossing the band -- is not a hook. A hook that merely CROSSES a line is mostly not line rows and stays.
            if line_rows is not None:
                ya, yb = iy0 + r[0], min(len(line_rows), iy0 + r[1])
                if yb > ya and float(line_rows[ya:yb].mean()) >= LINE_RUN_MIN_SHARE:
                    continue
            if merged and r[0] - merged[-1][1] < gmin:
                merged[-1] = (merged[-1][0], r[1])
            else:
                merged.append(r)
        ks.append(len(merged))
        if into_sign > 0:
            starts.append([(iy0 + a - tip_y) / space for a, _b in merged])
        else:
            starts.append(sorted((tip_y - (iy0 + b)) / space for _a, b in merged))
    inked = [n for n in ks if n > 0]
    if len(inked) < STEM_TIP_HOOKS_MIN_COVERAGE * len(ks):
        return verdict(None, 1, 2, HOOKS_UNCOUNTED_TOO_LITTLE)
    support = [sum(1 for n in inked if n >= j) / float(len(inked))
               for j in (1, 2, 3, 4)]
    count = max(j for j in (1, 2, 3, 4) if support[j - 1] >= STEM_TIP_HOOKS_SUPPORT)
    over = support[count] if count < 4 else 0.0
    shaped = True
    if count >= 2:
        # Hooks are STACKED strokes: the first leaves the stem at its tip
        # and each next one a hook-spacing further in. A second run far from
        # the first (a slur or a ledger line meeting the stem) is attached
        # ink, not a hook.
        cols = sorted((c for c in starts if len(c) >= count),
                      key=lambda c: c[0])
        firsts = sorted(c[0] for c in cols)
        gaps = sorted(c[j] - c[j - 1] for c in cols for j in range(1, count))
        mid = len(cols) // 2
        shaped = (firsts[mid] <= STEM_TIP_HOOKS_FIRST_MAX_SPACES
                  and STEM_TIP_HOOKS_SPACING_MIN <= gaps[len(gaps) // 2]
                  <= STEM_TIP_HOOKS_SPACING_MAX)
    if over > STEM_TIP_HOOKS_GLITCH or count >= STEM_TIP_HOOKS_MAX_LEVEL + 1 \
            or not shaped:
        # Not shaped like stacked hooks: it may be one hook plus attached
        # ink, or `count` real ones -- the bracket is 1..count. Clean but
        # over-supported at count+1: count..count+1.
        if not shaped:
            lo, hi = 1, min(count, STEM_TIP_HOOKS_MAX_LEVEL)
        else:
            lo = min(count, STEM_TIP_HOOKS_MAX_LEVEL)
            hi = min(count + 1, STEM_TIP_HOOKS_MAX_LEVEL)
        return verdict(None, lo, max(lo, hi), HOOKS_UNCOUNTED_UNRESOLVED,
                       support)
    return verdict(count, count, count, None, support)


def _head_edge_for_end(heads: Optional[Sequence[Tuple[float, float, float, float]]],
                       stem_x0: float, stem_x1: float, tip_y: float,
                       into_sign: float, space: float
                       ) -> Tuple[Optional[float], bool]:
    """`(edge_y, head_at_this_end)` -- where walking from this tip into the
    stem the first notehead beside it begins (`None` where none does or no
    detection map ran), and whether a head stands AT this end (then it is
    the head's end, not a flag's). ROADMAP 2.69."""
    if not heads:
        return None, False
    edge: Optional[float] = None
    for hx, hy, hw, hh in heads:
        if hx >= stem_x1 + 1.8 * space or hx + hw <= stem_x0 - 1.8 * space:
            continue
        near, far = (hy, hy + hh) if into_sign > 0 else (hy + hh, hy)
        t_near = (near - tip_y) * into_sign
        t_far = (far - tip_y) * into_sign
        if t_near <= 0.3 * space and t_far > -0.3 * space:
            return None, True
        if t_near > 0.3 * space and (edge is None or t_near < edge):
            edge = t_near
    return (None if edge is None else tip_y + into_sign * edge), False


def _rects_overlap(a: Tuple[float, float, float, float],
                   b: Tuple[float, float, float, float]) -> bool:
    """Two `(x0, y0, x1, y1)` CORNER boxes -- NOT `Q.STEM`'s own `[x, y, w,
    h]` convention, so a caller must convert before calling this."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


#: How far (staff spaces) a detected flag box's left edge may stand from the
#: stem it hangs off, and how far (spaces) its near edge may stand from that
#: stem's tip. Measured on Brahms p1 tile 15 (ROADMAP 2.65/2.69 leftover): the
#: detector's `flag8thUp`/`flag16thUp` boxes over one flag start a hair INSIDE
#: the stem (left edge +0.1 spaces from its left) and 0.2-0.3 spaces under the
#: tip. NOT CONFIRMED beyond that plate; a flag whose box starts farther out is
#: simply not set aside (it stays a blocker -- the old behaviour).
STEM_TIP_OWN_FLAG_X_SPACES = 0.6
STEM_TIP_OWN_FLAG_TIP_SPACES = 0.8


def _is_flag_detection(d: Any) -> bool:
    return str(getattr(d, "smufl_name", "") or "").startswith("flag")


def _flag_box_hangs_off_stem(dd: Any, stem_box: Tuple[float, float, float, float],
                             space: float) -> bool:
    """Is this detected FLAG box the flag of THIS stem (either tip)?

    A flag is drawn off its stem's tip, so its box starts at the stem's side
    (`STEM_TIP_OWN_FLAG_X_SPACES`) and its near edge stands within
    `STEM_TIP_OWN_FLAG_TIP_SPACES` of the top or the bottom tip. Anything else
    -- another stem's flag, a flag box starting mid-stem -- is not this
    stem's own.
    """
    sx, sy, sw, sh = stem_box
    bx0, by0 = float(dd.x_canonical), float(dd.y_canonical)
    bx1, by1 = bx0 + float(dd.width_canonical), by0 + float(dd.height_canonical)
    if not (sx - STEM_TIP_OWN_FLAG_X_SPACES * space <= bx0
            <= sx + sw + STEM_TIP_OWN_FLAG_X_SPACES * space):
        return False
    reach = STEM_TIP_OWN_FLAG_TIP_SPACES * space
    top, bottom = sy, sy + sh
    return (abs(by0 - top) <= reach and by1 > top) \
        or (abs(by1 - bottom) <= reach and by0 < bottom)


def _stem_tip_blockers(beams: Iterable[Any], other_dets: Iterable[Any],
                       space: Optional[float],
                       own_stem: Optional[Tuple[float, float, float, float]] = None
                       ) -> List[Tuple[float, float, float, float]]:
    """Every box (`x0, y0, x1, y1` corners) that already explains ink in
    THIS cell, for `_observe_stem_tip_ink`'s window guard.

    ⚠️⚠️ `_explaining_detections`'S OWN WIDTH CUT, BORROWED, NOT RESTATED --
    applied to `other_dets` (the detector's classification boxes) and NOT
    to `beams` (this reader's OWN CV strokes, already narrow by
    construction). A `staff` box spans the whole system's width and a wide
    `tie`/`slur` box is mostly paper (CLAUDE.md SS10); measured on a real
    Breitkopf p1 gather, EVERY ONE of the six confirmed missed-flag heads
    FINDINGS SS11.4b names sat under exactly such a box, and without this
    cut 1380 of 1584 window attempts abstained `occupied` before any of
    them was measured. A box this wide never "explains" one narrow window's
    ink -- it explains the whole page.

    ⚠️⚠️ ROADMAP 2.75 (Sean, 2026-10-09: the two flag boxes on Brahms p1
    tile 15, an eighth). `own_stem` (`x, y, w, h`, the stem the window will be
    read at): a detected FLAG box hanging off THAT stem's tip is not "other ink
    this record can already name" -- it is the mark the hook reader counts
    UNDER, and the detector often draws one flag twice (`flag8thUp` and
    `flag16thUp` over the same ink), which blocked the stem's own tip and kept
    the 2.69 hook count from ever being filed. It is set aside here and ONLY
    here: a flag of ANOTHER stem, a tie, a beam stroke, anything not a flag
    box still blocks, and a flag box is never evidence of a hook by itself --
    the window is still READ off the ink (`stem_tip_ink`). `own_stem=None` is
    the pre-2.75 call, byte for byte.
    """
    out = [
        (float(bd.x_canonical), float(bd.y_canonical),
         float(bd.x_canonical) + float(bd.width_canonical),
         float(bd.y_canonical) + float(bd.height_canonical))
        for bd in beams]
    if not space:
        return out
    from ..direction_text import DEFAULT_BAND_CONFIG
    cut = DEFAULT_BAND_CONFIG.max_blank_width_spaces * space
    out.extend(
        (float(dd.x_canonical), float(dd.y_canonical),
         float(dd.x_canonical) + float(dd.width_canonical),
         float(dd.y_canonical) + float(dd.height_canonical))
        for dd in other_dets if float(dd.width_canonical) <= cut
        and not (own_stem is not None and _is_flag_detection(dd)
                 and _flag_box_hangs_off_stem(dd, own_stem, space)))
    return out


def _observe_stem_tip_ink(log: Log, sub: Subject, frame: str, cell: Any,
                          stem_row_id: str,
                          stem_box: Tuple[float, float, float, float],
                          blockers: Sequence[Tuple[float, float, float, float]],
                          space: Optional[float],
                          heads: Optional[Sequence[Tuple[float, float, float, float]]] = None,
                          slashes: Optional[Sequence[Dict[str, Any]]] = None
                          ) -> None:
    """`Q.STEM_TIP_INK` -- one row per (`Q.STEM` row, end). ROADMAP 2.18c.

    ROADMAP 2.71: `slashes` is `stem_slashes`'s reading of THIS stem; the
    window and the hook counter read the raster with every passing slash
    blanked (`blank_slashes`), so a tremolo slash is neither flag-shaped ink
    nor a hook, and a real hook on the same stem is still found and counted.

    ROADMAP 2.69: where the ink IS found, the row's detail also carries the
    HOOK COUNT (`stem_tip_hooks`: `hooks`, `hooks_min`, `hooks_max`,
    `hooks_reason`, `hooks_support`). `heads` is this cell's notehead boxes
    (canonical), so the count stops short of the stem's own head. The value
    stays the 2.18c boolean -- *a hook is there* -- and the count is the
    reader's detail, `None` with a reason word where the ink cannot say.

    ROADMAP 2.83: the reading is `stem_tip_ink`'s SHAPE test over the ink
    connected to the stem (the module block above says what was measured and
    why 2.18c's density window missed Sean's flags), off the staff-ERASED
    raster (CLAUDE.md SS9 -- erase for the CV consumer, never the detector).
    Three outcomes, one row or one abstention per end: a flag-shaped hook is
    `True`; nothing hanging from the tip is `False`; ink that is not
    flag-shaped (or an unreadable tip) is an `ambiguous` ABSTENTION carrying
    what was measured -- never `False`. The end a notehead stands at has no
    tip (abstains `occupied`, `why = head_at_this_end`), and the window stops
    short of the stem's own head. `blockers` is every `Q.BEAM_STROKE` box
    already read in this cell PLUS every OTHER detection box the detector drew
    here (a neighbour's notehead, an accidental, text, a slur/tie arc, a
    second flag reading) -- ink this record can already name is not this
    quantity's to re-claim, so a window either overlaps is ABSTAINED, never
    measured.

    ROADMAP 2.83 FIX ROUND: the 2.18c density window (`stem_tip_window`, read
    only where no box overlaps it) is the SECOND witness -- the shape reading
    may ADD a witness, never REMOVE one (see the block above `stem_tip_window`
    for the table: shape True; shape cannot tell + window True is a True row
    with `witness = "window"`; shape False + window True is a DISPUTE row,
    `tip_disagree`). The end a notehead stands at is never given to the window.
    """
    x0, y0, w, h = stem_box
    x1, y1 = x0 + w, y0 + h
    img = getattr(cell, "image_no_staff", None)
    if img is None or getattr(img, "ndim", 0) != 2:
        for end in ("top", "bottom"):
            log.abstain(sub, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP,
                        frame=frame, reason=ABSTAIN.NO_MASK,
                        stem_row_id=stem_row_id, end=end,
                        note="cell carries no image_no_staff")
        return
    if not space or space <= 0:
        for end in ("top", "bottom"):
            log.abstain(sub, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        stem_row_id=stem_row_id, end=end,
                        note="no cell staff-space unit")
        return
    if slashes:
        img = blank_slashes(img, slashes)
    for end, tip_y, into_sign in (("top", y0, 1.0), ("bottom", y1, -1.0)):
        # ROADMAP 2.83: the stem's own head first -- the window stops short of it, and the end a head stands at has no tip.
        edge, head_here = _head_edge_for_end(heads, x0, x1, tip_y, into_sign,
                                             space)
        if head_here:
            log.abstain(sub, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP,
                        frame=frame, reason=ABSTAIN.OCCUPIED,
                        stem_row_id=stem_row_id, end=end,
                        why=HOOKS_UNCOUNTED_HEAD_AT_END,
                        note="a notehead stands at this end of the stem: its "
                             "ink is the head's own, not a hook's")
            continue
        m = stem_tip_ink(img, x0, x1, tip_y, into_sign, space,
                         head_edge=edge, blockers=blockers)
        if m is None:
            log.abstain(sub, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        stem_row_id=stem_row_id, end=end,
                        note="window off the raster")
            continue
        found = m.pop("found")
        # ROADMAP 2.83 FIX ROUND: the 2.18c density window is the SECOND witness (see `stem_tip_window`): read where no box overlaps it,
        # combined with the shape reading below -- the shape reader may ADD a witness, never REMOVE one.
        window = None
        if not stem_tip_window_blocked(blockers, x1, tip_y, into_sign, space):
            window = stem_tip_window(img, x0, x1, tip_y, into_sign, space)
        window_found = None if window is None else window["found"]
        window_detail: Dict[str, Any] = {} if window is None else {
            "window_found": window_found, "window_right": window["right"], "window_left": window["left"]}
        extra: Dict[str, Any] = {}
        if found is None and not window_found and m.get("why") == "occupied" and tip_unblocked_enabled():
            # ROADMAP 2.104: the boxes explain the ink, but a flag-shaped reading with them set aside is still the ink's own
            # evidence. Only `found True` is taken; anything else falls through to the unchanged `occupied` abstention below.
            m2 = stem_tip_ink(img, x0, x1, tip_y, into_sign, space, head_edge=edge, blockers=())
            if m2 is not None and m2.get("found") is True:
                m2.pop("found")
                counted = stem_tip_hooks(img, x0, x1, tip_y, into_sign, space, head_edge=edge,
                                         line_rows=_hook_line_rows(cell, x0, x1, space))
                log.observe(sub, Q.STEM_TIP_INK, True,
                            reader=READERS.CV_STEM_TIP, frame=frame,
                            stem_row_id=stem_row_id, end=end, **m2, **window_detail,
                            witness="shape_unblocked", **(counted or {}))
                continue
        if found is None and not window_found:
            if m.get("why") == "occupied":
                log.abstain(sub, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP,
                            frame=frame, reason=ABSTAIN.OCCUPIED,
                            stem_row_id=stem_row_id, end=end,
                            note="a beam stroke or another detection already "
                                 "explains the ink attached to this stem tip",
                            **m, **window_detail)
                continue
            # ROADMAP 2.83, RULE 8: ink hangs here that is not flag-shaped (or the tip cannot be read), and the density window does
            # not see a hook either. CANNOT TELL -- never filed as `False`, which the bare-stem readers take as a positive
            # "nothing hangs from this tip".
            log.abstain(sub, Q.STEM_TIP_INK, reader=READERS.CV_STEM_TIP,
                        frame=frame, reason=ABSTAIN.AMBIGUOUS,
                        stem_row_id=stem_row_id, end=end,
                        note="ink at this tip is not flag-shaped (or the tip "
                             "is unreadable): cannot tell, not 'no flag'",
                        **m, **window_detail)
            continue
        if found is None:
            # the shape reader cannot tell and the window SEES a hook: the base's claim stands (Sean's tiles 4 and 8)
            value, extra = True, {"witness": "window"}
        elif found is False and window_found:
            # the shape reader positively sees nothing hanging from the tip and the window sees a hook: a DISPUTE. A True row marked
            # `tip_disagree` -- ADJUDICATE narrows {0, the counted level}, it never decides 0 and never decides the hook.
            value, extra = True, {"witness": "disputed", "tip_disagree": True}
        else:
            value, extra = bool(found), {"witness": "shape"}
        hook_detail: Dict[str, Any] = {}
        if value:
            counted = stem_tip_hooks(img, x0, x1, tip_y, into_sign, space,
                                     head_edge=edge,
                                     line_rows=_hook_line_rows(cell, x0, x1, space))
            if counted is not None:
                hook_detail = counted
        log.observe(sub, Q.STEM_TIP_INK, value,
                    reader=READERS.CV_STEM_TIP, frame=frame,
                    stem_row_id=stem_row_id, end=end, **m, **window_detail,
                    **extra, **hook_detail)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.71 -- the TREMOLO SLASH, named once.
#
# Sean, 2026-10-09 (DECISIONS): *"The trem slash is very different from a
# beam. Beams have to be connected to other notes - slashes never are. The
# hook of a flag is very different from a slash. The slash crosses both sides
# of the stem with a thick line at an angle."* A slash is a THICK, ANGLED
# stroke that crosses BOTH sides of ONE stem and is joined to no other note's
# stem. It is its own mark (a tremolo): never a beam level, never a flag hook,
# never a rest, never a notehead, and it never shortens the written value.
#
# This is the ONE place a slash is named. `Q.STEM_SLASH` says how many a stem
# carries and where; the beam path (`rhythm._not_a_slash`), the hook and
# stem-tip readers (`blank_slashes`, below), the rest refusal
# (`family_precision`) and the notehead refusal (`notehead_precision`) all read
# it, so they refuse the same ink by the same rule.
#
# HOW IT IS READ. Each stroke that touches the stem is FOLLOWED OUTWARD from
# the stem's edge, column by column, on each side (a run of ink overlapping the
# previous column's, stopping where it merges into something taller than
# itself). A slash is a left track and a right track that meet at the stem
# (contact intervals within `STEM_SLASH_CONTACT_GAP_SPACES`), run
# `STEM_SLASH_MIN_REACH_SPACES` or more out from it on BOTH sides, lie on one
# straight line (a slur bows, a head does not continue), lean at least
# `STEM_SLASH_MIN_ANGLE_DEG` off horizontal (a ledger line through a stem is
# level), are at least `STEM_SLASH_MIN_THICKNESS_RATIO` staff-line thicknesses
# thick measured across the stroke (a slur's or hairpin's line is about one),
# and neither run on to another stem (a beam) nor stand on a head's end (a
# chord's head on each side). Each refusal is a reason word on the stroke, so
# `Q.STEM_SLASH` is a measurement with its own refusals, never a bare count.
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond Sean's
# two lines: the numbers. They are set on Litolff p6 (a bold MERGING plate:
# 7 slashed stems read, every one a slash by eye in the tiles looked at) and
# Brahms p0-1 (17 read; the two quarter rests the reader also passes are
# caught downstream by the rest's own height -- `family_precision`) and are
# untested on a plate whose slashes are steeper than ~55 degrees or shorter
# than 0.7 spaces. Falsified by a
# print-confirmed slash the reader refuses (a tremolo drawn level; one that
# reaches under 0.35 spaces from the stem) or a stroke it passes that Sean
# reads as something else.
# ─────────────────────────────────────────────────────────────────────────────

#: A stroke must reach at least this far out from the stem on BOTH sides.
STEM_SLASH_MIN_REACH_SPACES = 0.35
#: ... and no further than this before it is something longer than a slash
#: (a beam, a tie, a staff-line residue): the tracker stops here and the
#: stroke is refused `runs_on`.
STEM_SLASH_MAX_REACH_SPACES = 1.9
#: The left and right contact intervals (where the stroke meets the stem's
#: edges) must lie within this far of overlapping: a straight stroke at 30
#: degrees shifts ~0.2 spaces across a stem.
STEM_SLASH_CONTACT_GAP_SPACES = 0.35
#: A contact interval shorter than this is a speck; taller than this is a
#: head or a clump, never a slash's own thickness.
#:
#: ⚠️ 1.3 -> 1.6 (ROADMAP 2.78, 2026-10-09). Litolff p2 `cell/2/1/9/11` (2.78
#: tile 7, Sean: *"2 half notes with a trem slash"*): a bold slash's contact with
#: the stem measured 1.37 spaces on its left side and was refused here as a
#: clump, so `Q.STEM_SLASH` read a stem Sean reads as slashed as `one_sided`.
#: MEASURED across every stem of Litolff p1-3 and Brahms p0-1 (2,339 stems):
#: raising the cap changes the passing-slash count on ONE stem (tile 7's).
STEM_SLASH_MIN_CONTACT_SPACES = 0.10
STEM_SLASH_MAX_CONTACT_SPACES = 1.6
#: ⚠️ ROADMAP 2.78. The tracker starts at the column just outside the stem's
#: MEDIAN core, and on a stem that flares (a slash's root, a thicker top) that
#: column can already hold stem ink, so the first run is taller than the
#: stroke's own contact and the `swelled past 1.7x` stop fires on column ZERO
#: and returns nothing (Brahms p1 `cell/1/1/7/7`, 2.78 tile 8, Sean: *"Dotted
#: half with a trem slash"*, read `one_sided` with a left reach of 0.0). The
#: tracker may therefore start up to this far further out, in staff spaces,
#: before it gives up. It changes only a stroke that tracked NOTHING before
#: (the first column that works returns at once, byte-identical to before).
STEM_SLASH_START_SKIP_SPACES = 0.06
#: The tracked centre points of both sides lie on one line to within this.
STEM_SLASH_MAX_RESIDUAL_SPACES = 0.15
#: Off horizontal. A tremolo slash is drawn at an angle; a ledger line
#: through a stem is level (0-5 degrees on the plates read).
STEM_SLASH_MIN_ANGLE_DEG = 12.0
#: Thickness ACROSS the stroke over the staff line's thickness; a hairpin's
#: line or a slur's tapering end reads 1.0-1.3, a slash 2.0 and over.
STEM_SLASH_MIN_THICKNESS_RATIO = 1.4
#: A notehead box whose centre is this near the stem's end, and whose rows
#: hold the stroke, explains it (a chord's second puts a head on each side).
STEM_SLASH_HEAD_END_SPACES = 1.1

#: ⚠️ A QUARTER REST READ AS A "STEM" (the CV stem reader finds its own stroke --
#: 2.33b) HAS DIAGONAL STROKES THAT CROSS ITS AXIS EXACTLY AS A SLASH DOES, and
#: this reader passes two of them on Brahms p1 (FINDINGS 2.71). A test of "how
#: long is the plain thin stretch of the stem" (`bare_stem_spaces`, recorded on
#: every stroke) was built to refuse them and MEASURED AND REFUSED: the real
#: Litolff p6 slashes read 0.57-1.08 (a bold plate, a hollow head merged at one
#: end), the two Brahms rests 0.95 and 1.06 -- the populations overlap. So the
#: reader keeps what it measures, and the one decision that must tell a rest
#: from a slashed stem (`family_precision`) asks the box's own HEIGHT as well.
#: A row is "bare stem" where the ink run through the stem's centre is no wider
#: than the stem's own width times this, plus a little slack.
STEM_SLASH_BARE_WIDTH_FACTOR = 1.5

SLASH_REASONS = ("one_sided", "not_at_an_angle", "too_thin", "not_straight",
                 "joins_another_stem", "runs_on", "at_a_head", "too_short")


def _bare_stem_spaces(ink: Any, box: Tuple[float, float, float, float],
                      core: Tuple[int, int], space: float) -> float:
    """The longest stretch (in spaces) of consecutive rows of this stem box
    where the ink run through the stem's centre is no wider than the stem
    itself -- how long the stem is a plain line. ROADMAP 2.71."""
    H, W = ink.shape
    x, y, w, h = [int(round(v)) for v in box]
    c0, c1 = core
    mid = (c0 + c1) // 2
    limit = STEM_SLASH_BARE_WIDTH_FACTOR * max(1, c1 - c0) + 0.06 * space
    best = cur = 0
    for yy in range(max(0, y), min(H, y + h)):
        row = ink[yy]
        if not (0 <= mid < W) or not row[mid]:
            cur = 0
            continue
        a = mid
        while a > 0 and row[a - 1]:
            a -= 1
        b = mid
        while b < W - 1 and row[b + 1]:
            b += 1
        if (b - a + 1) <= limit:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best / float(space)


def _col_runs(col: Any) -> List[Tuple[int, int]]:
    import numpy as np
    d = np.diff(np.concatenate([[0], np.asarray(col, np.int8), [0]]))
    return list(zip(np.where(d == 1)[0].tolist(), np.where(d == -1)[0].tolist()))


def _stem_core(ink: Any, box: Tuple[float, float, float, float]
               ) -> Optional[Tuple[int, int]]:
    """The stem's OWN columns `(c0, c1)`: the median width and centre of the
    ink run through the stem box's middle three fifths. A CV stem box can be
    wider than the stem (it may swallow a slash's root); the median is not."""
    import numpy as np
    H, W = ink.shape
    x, y, w, h = [int(round(v)) for v in box]
    mid = x + w / 2.0
    lo = max(0, x - 6)
    ws, cs = [], []
    for yy in range(max(0, y + h // 5), min(H, y + h - h // 5)):
        best = None
        for s, e in _col_runs(ink[yy, lo:min(W, x + w + 6)]):
            s += lo
            e += lo
            if best is None or abs((s + e) / 2.0 - mid) < abs((best[0] + best[1]) / 2.0 - mid):
                best = (s, e)
        if best:
            ws.append(best[1] - best[0])
            cs.append((best[0] + best[1]) / 2.0)
    if not ws:
        return None
    wc, cc = float(np.median(ws)), float(np.median(cs))
    return int(round(cc - wc / 2.0)), int(round(cc + wc / 2.0))


def _track_stroke(ink: Any, start_x: int, direction: int,
                  interval: Tuple[int, int], space: float,
                  max_reach: int) -> List[Tuple[int, int, int]]:
    """`_track_stroke_from` at `start_x`, and where that tracks NOTHING at the
    next columns outward, up to `STEM_SLASH_START_SKIP_SPACES` of them. ROADMAP
    2.78: the first column sits beside a stem that may flare, and a stroke that
    works at its first column returns at once, exactly as before."""
    out = _track_stroke_from(ink, start_x, direction, interval, space,
                             max_reach)
    if out:
        return out
    for skip in range(1, int(round(STEM_SLASH_START_SKIP_SPACES * space)) + 1):
        out = _track_stroke_from(ink, start_x + direction * skip, direction,
                                 interval, space, max_reach)
        if out:
            return out
    return []


def _track_stroke_from(ink: Any, start_x: int, direction: int,
                       interval: Tuple[int, int], space: float,
                       max_reach: int) -> List[Tuple[int, int, int]]:
    """Follow one stroke outward from the stem: `[(x, y0, y1), ...]`, one per
    column, each the run that overlaps the previous column's the most. It
    STOPS where the stroke ends or swells past `1.7 x` its first thickness
    (it has merged into a head, a beam or a clump)."""
    H, W = ink.shape
    a, b = interval
    first = b - a
    pad = int(0.35 * space)
    out: List[Tuple[int, int, int]] = []
    for dx in range(0, max_reach):
        x = start_x + direction * dx
        if not (0 <= x < W):
            break
        lo = max(0, a - pad)
        best = None
        for s, e in _col_runs(ink[lo:min(H, b + pad), x]):
            s += lo
            e += lo
            ov = min(e, b) - max(s, a)
            if ov > 0 and (best is None or ov > best[2]):
                best = (s, e, ov)
        if best is None:
            break
        s, e, _ = best
        if (e - s) > 1.7 * first + 0.1 * space:
            break
        out.append((x, s, e))
        a, b = s, e
    return out


def stem_slashes(ink: Any, box: Tuple[float, float, float, float],
                 space: float, line_px: float,
                 other_stems: Sequence[Tuple[float, float, float, float]] = (),
                 heads: Sequence[Tuple[float, float, float, float]] = ()
                 ) -> List[Dict[str, Any]]:
    """Every stroke that crosses ONE stem, each with a `reason` (`None` = a
    tremolo slash; else one of `SLASH_REASONS`). ROADMAP 2.71.

    `ink` is the staff-ERASED raster as a bool array (True = ink), `box` the
    stem's `(x, y, w, h)`, all in the SAME canonical cell pixels; `space` the
    staff space and `line_px` the staff line's thickness in those pixels;
    `other_stems` and `heads` are `(x, y, w, h)` boxes in that frame. An
    empty list means the reader RAN and no stroke crosses this stem; it never
    returns `None`. Pure: it decides nothing about any glyph.
    """
    import math
    import numpy as np
    if ink is None or getattr(ink, "ndim", 0) != 2 or not space or space <= 0:
        return []
    H, W = ink.shape
    core = _stem_core(ink, box)
    if core is None:
        return []
    c0, c1 = core
    x, y, w, h = [float(v) for v in box]
    bare = _bare_stem_spaces(ink, box, core, space)
    near = max(2, int(round(0.12 * space)))
    max_reach = int(round(STEM_SLASH_MAX_REACH_SPACES * space))
    ya, yb = int(max(0, y)), int(min(H, y + h))
    contacts: Dict[str, list] = {"left": [], "right": []}
    for side, sx, d in (("left", c0 - 2, -1), ("right", c1 + 1, 1)):
        xa, xb = (sx - near, sx) if d < 0 else (sx, sx + near)
        band = ink[ya:yb, max(0, xa):max(0, xb)]
        if band.size == 0:
            continue
        occupied = band.mean(axis=1) >= 0.6
        for a, b in _col_runs(occupied):
            if b - a < STEM_SLASH_MIN_CONTACT_SPACES * space \
                    or b - a > STEM_SLASH_MAX_CONTACT_SPACES * space:
                continue
            a += ya
            b += ya
            contacts[side].append(
                ((a, b), _track_stroke(ink, sx, d, (a, b), space, max_reach)))
    strokes: List[Dict[str, Any]] = []
    used_right = set()
    for (la, lb), ltr in contacts["left"]:
        for ri, ((ra, rb), rtr) in enumerate(contacts["right"]):
            if ri in used_right:
                continue
            if max(la, ra) - min(lb, rb) > STEM_SLASH_CONTACT_GAP_SPACES * space:
                continue
            used_right.add(ri)
            lreach = (abs(ltr[-1][0] - (c0 - 2)) if ltr else 0)
            rreach = (abs(rtr[-1][0] - (c1 + 1)) if rtr else 0)
            half_core = (c1 - c0) / 2.0
            pts = ([(-(abs(px - (c0 - 2)) + half_core), (s + e) / 2.0)
                    for px, s, e in ltr]
                   + [((abs(px - (c1 + 1)) + half_core), (s + e) / 2.0)
                      for px, s, e in rtr])
            lens = [e - s for _x, s, e in ltr] + [e - s for _x, s, e in rtr]
            rec: Dict[str, Any] = {
                "reason": None,
                "left_reach": round(lreach / space, 3),
                "right_reach": round(rreach / space, 3),
                "contact": [[la, lb], [ra, rb]]}
            runs = list(ltr) + list(rtr)
            if len(pts) < 8:
                rec["reason"] = "too_short"
                strokes.append(rec)
                break
            X = np.array([p[0] for p in pts], float)
            Y = np.array([p[1] for p in pts], float)
            A = np.vstack([X, np.ones_like(X)]).T
            (m, k), *_ = np.linalg.lstsq(A, Y, rcond=None)
            resid = float(np.sqrt(np.mean((A @ np.array([m, k]) - Y) ** 2)))
            ang = math.degrees(math.atan(abs(m)))
            thick = float(np.median(lens)) * math.cos(math.atan(m))
            ratio = thick / float(line_px) if line_px and line_px > 0 else None
            cy = float(np.mean(Y))
            px0 = min(r[0] for r in runs)
            px1 = max(r[0] for r in runs)
            xc = (c0 + c1) / 2.0
            rec.update(
                angle_deg=round(ang, 1),
                thickness_ratio=(None if ratio is None else round(ratio, 3)),
                residual_spaces=round(resid / space, 3), y=round(cy, 1),
                bare_stem_spaces=round(bare, 2),
                box=[float(px0), float(min(r[1] for r in runs)),
                     float(px1 + 1), float(max(r[2] for r in runs))],
                # the stroke's own centre line `[x0, y0, x1, y1]` and its
                # thickness across, so a consumer asks whether a BOX covers
                # the stroke, never whether it covers a bounding rectangle
                # that is mostly paper at an angle
                centreline=[float(px0), round(float(m * (px0 - xc) + k), 1),
                            float(px1), round(float(m * (px1 - xc) + k), 1)],
                thickness_px=round(thick, 1),
                _runs=runs)
            reason = None
            if min(lreach, rreach) < STEM_SLASH_MIN_REACH_SPACES * space:
                reason = "one_sided"
            elif ang < STEM_SLASH_MIN_ANGLE_DEG:
                reason = "not_at_an_angle"
            elif resid > STEM_SLASH_MAX_RESIDUAL_SPACES * space:
                reason = "not_straight"
            elif ratio is not None and ratio < STEM_SLASH_MIN_THICKNESS_RATIO:
                reason = "too_thin"
            else:
                for sx0, sy0, sw, sh in other_stems:
                    if not (sy0 - 0.5 * space <= cy <= sy0 + sh + 0.5 * space):
                        continue
                    if (sx0 + sw <= c0 - 0.2 * space
                            and sx0 + sw >= c0 - lreach - 0.5 * space):
                        reason = "joins_another_stem"
                    if (sx0 >= c1 + 0.2 * space
                            and sx0 <= c1 + rreach + 0.5 * space):
                        reason = "joins_another_stem"
                if reason is None and max(lreach, rreach) >= max_reach - 2:
                    reason = "runs_on"
                if reason is None:
                    # A head box at one end of the stem explains a stroke at
                    # THAT end -- but only where the stem's OTHER end has no
                    # head box. A stem has its head at one end; with boxes at
                    # both ends the one on the stroke is the suspect, and the
                    # detector boxing a slash as a notehead (2.49) is how that
                    # happens (Litolff p6 `glyph/6/1/11/3/3`).
                    near_x = [(hx, hy, hw, hh) for hx, hy, hw, hh in heads or ()
                              if hx < x + w + 1.8 * space
                              and hx + hw > x - 1.8 * space]
                    at_top = any(abs(hy + hh / 2.0 - y) <= STEM_SLASH_HEAD_END_SPACES * space
                                 for _hx, hy, _hw, hh in near_x)
                    at_bot = any(abs(hy + hh / 2.0 - (y + h)) <= STEM_SLASH_HEAD_END_SPACES * space
                                 for _hx, hy, _hw, hh in near_x)
                    for hx, hy, hw, hh in near_x:
                        hcy = hy + hh / 2.0
                        end = ("top" if abs(hcy - y) <= STEM_SLASH_HEAD_END_SPACES * space
                               else "bottom" if abs(hcy - (y + h)) <= STEM_SLASH_HEAD_END_SPACES * space
                               else None)
                        if end is None or (at_top and at_bot):
                            continue
                        if (hy - 0.2 * space <= cy <= hy + hh + 0.2 * space
                                and hx < c1 + rreach and hx + hw > c0 - lreach):
                            reason = "at_a_head"
                            break
            rec["reason"] = reason
            strokes.append(rec)
            break
    return strokes


def blank_slashes(img: Any, strokes: Sequence[Dict[str, Any]],
                  pad_px: int = 2) -> Any:
    """`img` (uint8, 0 = ink) with every PASSING slash's own ink whitened,
    its tracked run in each column widened by `pad_px`. The stem is untouched
    (a track starts at its edge). Returns `img` itself where no slash passes,
    so a stem without one reads byte-identically to before. ROADMAP 2.71.

    One rule for every reader of the stem's neighbourhood: the hook counter
    and the tip-ink window are handed this, so a slash is not a hook, and a
    real hook beside one still counts."""
    runs = [r for s in strokes if s.get("reason") is None
            for r in (s.get("_runs") or ())]
    if not runs or img is None:
        return img
    out = img.copy()
    H, W = out.shape[:2]
    for px, s, e in runs:
        if 0 <= px < W:
            out[max(0, s - pad_px):min(H, e + pad_px), px] = 255
    return out


def _observe_stem_slashes(log: Log, sub: Subject, frame: str, cell: Any,
                          stem_rows: Sequence[Tuple[Any, str]],
                          heads: Optional[Sequence[Tuple[float, float, float, float]]],
                          space: Optional[float]
                          ) -> Dict[str, List[Dict[str, Any]]]:
    """`Q.STEM_SLASH` -- one row per `Q.STEM` row of this cell, value = how
    many tremolo slashes it carries (a READ zero where none), detail = every
    stroke that crossed it with its reason. ROADMAP 2.71. Returns
    `{stem row id: strokes}` (the strokes still carrying their ink runs) for
    the stem-tip reader that follows, which reads a raster with the slash
    blanked. ABSTAINS, filing no zero, where the cell has no erased raster or
    no staff-space unit."""
    img = getattr(cell, "image_no_staff", None)
    if img is None or getattr(img, "ndim", 0) != 2:
        log.abstain(sub, Q.STEM_SLASH, reader=READERS.CV_STEM_SLASH, frame=frame,
                    reason=ABSTAIN.NO_MASK, note="cell carries no image_no_staff")
        return {}
    if not space or space <= 0:
        log.abstain(sub, Q.STEM_SLASH, reader=READERS.CV_STEM_SLASH, frame=frame,
                    reason=ABSTAIN.NO_STAFF_GEOMETRY,
                    note="no cell staff-space unit")
        return {}
    ink = img == 0
    line_px = float(getattr(cell, "staff_line_thickness_canonical", 0) or 0)
    boxes = [(float(d.x_canonical), float(d.y_canonical),
              float(d.width_canonical), float(d.height_canonical))
             for d, _rid in stem_rows]
    out: Dict[str, List[Dict[str, Any]]] = {}
    for i, (d, rid) in enumerate(stem_rows):
        others = [b for j, b in enumerate(boxes) if j != i]
        strokes = stem_slashes(ink, boxes[i], space, line_px, others, heads or ())
        out[rid] = strokes
        x, y, w, h = boxes[i]
        head_at = {"top": False, "bottom": False}
        for hx, hy, hw, hh in heads or ():
            hcy = hy + hh / 2.0
            if hx < x + w + 1.8 * space and hx + hw > x - 1.8 * space:
                if abs(hcy - y) <= STEM_SLASH_HEAD_END_SPACES * space:
                    head_at["top"] = True
                if abs(hcy - (y + h)) <= STEM_SLASH_HEAD_END_SPACES * space:
                    head_at["bottom"] = True
        n = sum(1 for s in strokes if s["reason"] is None)
        filed = [{k: v for k, v in s.items() if not k.startswith("_")}
                 for s in strokes]
        log.observe(sub, Q.STEM_SLASH, n, reader=READERS.CV_STEM_SLASH,
                    frame=frame, stem_row_id=rid, strokes=filed,
                    head_at_end=head_at)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.69 follow-up -- is a "dot" box really the curled tip of a flag?
#
# Sean, 2026-10-09 (DECISIONS, on 2.65 tile 13: the detector's
# `augmentationDot` box sits on the TIP of the note's own flag and made a plain
# eighth a dotted one): *"a dot can not fully or mostly overlap a flag but it
# can touch it"*. OVERLAP, not contact. A real dot is a disc: no straight line
# longer than the disc fits inside it, whether or not it touches a flag. A
# flag tip, a stem or a beam is a stroke: a line three dot-widths long fits.
# The test opens the box's ink with such a line at 45/90/135 degrees (not 0:
# an erased staff line leaves horizontal stripes), grows the survivors back
# by 0.15 spaces within the ink, and reports the share of the box's ink that
# survived. CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond
# Sean's two lines: a printed dot standing mostly on a stroke (a dot jammed
# against a flag so hard the line fits through half its ink) would be read as
# stroke. On Brahms p1 every real dot reads 0.0 and the tile-13 tip 0.93.
# ─────────────────────────────────────────────────────────────────────────────

DOT_STROKE_LINE_DOT_WIDTHS = 3.0
DOT_STROKE_LINE_MIN_SPACES = 1.0
DOT_STROKE_GROW_SPACES = 0.15
DOT_STROKE_ANGLES = (45, 90, 135)


def dot_stroke_ink(img: Any, box: Tuple[float, float, float, float],
                   space: float) -> Optional[Dict[str, Any]]:
    """The share of the ink inside `box` (`x, y, w, h`, canonical cell px)
    that lies on an elongated stroke. `None` -- declined -- where the raster,
    the unit or the box is unusable; `ink_px` 0 says the box held no ink at
    all (then `fraction` is 0.0 and means nothing). ROADMAP 2.69 follow-up."""
    if img is None or getattr(img, "ndim", 0) != 2 or not space or space <= 0:
        return None
    x, y, w, h = [float(v) for v in box]
    if w <= 0 or h <= 0:
        return None
    import cv2
    import numpy as np
    H, W = img.shape
    L = int(round(max(DOT_STROKE_LINE_DOT_WIDTHS * max(w, h),
                      DOT_STROKE_LINE_MIN_SPACES * space)))
    L += 1 - L % 2
    pad = int(L // 2 + 2)
    x0, y0 = max(0, int(x) - pad), max(0, int(y) - pad)
    x1, y1 = min(W, int(x + w) + pad), min(H, int(y + h) + pad)
    bx0, by0 = int(x) - x0, int(y) - y0
    bx1, by1 = min(x1 - x0, bx0 + int(w)), min(y1 - y0, by0 + int(h))
    if x1 - x0 < 3 or y1 - y0 < 3 or bx1 <= bx0 or by1 <= by0 \
            or bx0 < 0 or by0 < 0:
        return None
    ink = (img[y0:y1, x0:x1] == 0).astype(np.uint8)
    keep = np.zeros_like(ink)
    c = L // 2
    for ang in DOT_STROKE_ANGLES:
        k = np.zeros((L, L), np.uint8)
        dx, dy = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        for t in np.linspace(-c, c, 4 * L):
            k[int(round(c + t * dy)), int(round(c + t * dx))] = 1
        keep |= cv2.morphologyEx(ink, cv2.MORPH_OPEN, k)
    r = max(1, int(round(DOT_STROKE_GROW_SPACES * space)))
    grow = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    keep = cv2.dilate(keep, grow) & ink
    inside = int(ink[by0:by1, bx0:bx1].sum())
    on_stroke = int(keep[by0:by1, bx0:bx1].sum())
    return {"fraction": round(on_stroke / float(inside), 4) if inside else 0.0,
            "ink_px": inside, "line_px": L}


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.131 -- a staccato dot and a staccatissimo triangle are different
# marks (Sean 2026-10-14). The detector boxes both with the same small box and
# often the same class; the ink says which. Measured on Brahms 317803 (14
# pages, 600 dpi, `benchmarks/omr-staccatissimo-2026-10/FINDINGS.md`): the
# detector's own `articStaccatissimo*` boxes read height/width 1.45 (IQR
# 1.36-1.55) with the narrow end at the head, its `articStaccato*` boxes 1.0
# (IQR 0.91-1.10) and equal ends. CONVENTION ASSUMED / WHAT WOULD FALSIFY IT /
# NOT CONFIRMED: the staccatissimo is a wedge pointing at its head (Bravura,
# Gould); falsified by a Sean-read crop of a wedge that is not one. The cut
# (1.3, 0.8) is a MEASUREMENT on one score (Breitkopf), so the adjudicator
# that reads it is behind a flag until Sean's tiles.
# ─────────────────────────────────────────────────────────────────────────────

MARK_SHAPE_ENV = "OMR_STACCATISSIMO_SHAPE"
MARK_SHAPE_LOCAL_ENV = "OMR_MARK_SHAPE_LINE_REMOVED"


def mark_shape_line_removed_enabled() -> bool:
    """`OMR_MARK_SHAPE_LINE_REMOVED` (ROADMAP 2.133), default OFF: measure
    the mark off the PAGE raster with the staff line under it bridged out,
    instead of the cell's `image_no_staff`. Measurement only until it is
    shown to separate (FINDINGS 2.133: it does not, cleanly)."""
    return os.environ.get(MARK_SHAPE_LOCAL_ENV, "").strip().lower() in (
        "1", "true", "yes", "on")


def mark_shape_enabled() -> bool:
    """`OMR_STACCATISSIMO_SHAPE`, default ON (2.131, landed 2026-10-14);
    `0/false/no/off` disables."""
    return os.environ.get(MARK_SHAPE_ENV, "1").strip().lower() \
        not in ("0", "false", "no", "off")


def line_band_beside(ink: Any, row: float, x_in0: int, x_in1: int,
                     half_fallback: int, reach: int = 4
                     ) -> Tuple[int, int]:
    """The rows `(lo, hi)` the staff line near window row `row` occupies
    BESIDE the mark -- in the `reach` columns just outside its box columns
    `x_in0:x_in1` -- so a scan's thick or wavering line is erased at its own
    thickness and not at the staff's median. Falls back to `row +- 
    half_fallback` where neither side shows a line. ROADMAP 2.133."""
    import numpy as np
    H, W = ink.shape
    r = int(round(row))
    tops, bots = [], []
    for cols in (range(max(0, x_in0 - reach), x_in0),
                 range(x_in1, min(W, x_in1 + reach))):
        for c in cols:
            if not (0 <= r < H) or not ink[r, c]:
                continue
            t = r
            while t - 1 >= 0 and ink[t - 1, c]:
                t -= 1
            b_ = r
            while b_ + 1 < H and ink[b_ + 1, c]:
                b_ += 1
            if b_ - t + 1 <= 3 * half_fallback + 3:      # a line, not a stem
                tops.append(t)
                bots.append(b_)
    if len(tops) >= 2:
        return int(np.median(tops)), int(np.median(bots))
    return r - half_fallback, r + half_fallback


def erase_staff_lines(ink: Any, bands: Sequence[Tuple[int, int]]) -> Any:
    """`ink` (bool, True = ink, a window) with each staff-line BAND `(lo, hi)`
    bridged out: the band keeps only the columns where ink stands both just
    above and just below it -- the mark's body crossing the line survives, the
    line does not. ROADMAP 2.133."""
    import numpy as np
    out = ink.copy()
    H = out.shape[0]
    for lo, hi in bands:
        if hi < 0 or lo >= H:
            continue
        above = out[lo - 1] if lo - 1 >= 0 else np.zeros(out.shape[1], bool)
        below = out[hi + 1] if hi + 1 < H else np.zeros(out.shape[1], bool)
        out[max(0, lo):min(H, hi + 1)] = (above & below)[None, :]
    return out


def mark_shape_of_ink(ink: Any, space: float, rows: bool = False
                      ) -> Optional[Dict[str, Any]]:
    """Height/width, the top/bottom third widths and the row-width profile of
    the ink in a bool window (True = ink). `None` under four ink pixels.
    ROADMAP 2.131 / 2.133."""
    import numpy as np
    ys, xs = np.where(ink)
    if len(ys) < 4 or not space or space <= 0:
        return None
    top, bot = int(ys.min()), int(ys.max())
    ih, iw = bot - top + 1, int(xs.max() - xs.min() + 1)
    thirds = np.array_split(np.arange(top, bot + 1), 3)
    wid = [int(ink[t].any(axis=0).sum()) if len(t) else 0 for t in thirds]
    out = {"hw": round(ih / float(iw), 4), "top": wid[0], "bot": wid[2],
           "h_spaces": round(ih / float(space), 4),
           "w_spaces": round(iw / float(space), 4),
           "fill": round(len(ys) / float(ih * iw), 4)}
    if rows:                    # the row-width profile, for the page reader
        out["rows"] = [int(ink[r].sum()) for r in range(top, bot + 1)]
    return out


def mark_shape(img: Any, box: Tuple[float, float, float, float],
               space: float) -> Optional[Dict[str, Any]]:
    """`mark_shape_of_ink` on the ink (0 = ink) inside `box` (`x, y, w, h`),
    padded by one pixel. `None` -- declined -- where the raster, unit or box
    is unusable. ROADMAP 2.131."""
    if img is None or getattr(img, "ndim", 0) != 2 or not space or space <= 0:
        return None
    x, y, w, h = [float(v) for v in box]
    if w <= 0 or h <= 0:
        return None
    H, W = img.shape
    x0, y0 = max(0, int(round(x)) - 1), max(0, int(round(y)) - 1)
    x1, y1 = min(W, int(round(x + w)) + 2), min(H, int(round(y + h)) + 2)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None
    return mark_shape_of_ink(img[y0:y1, x0:x1] == 0, space)


def gather_mark_shapes(log: Log, pws: Any, cells: Sequence[Any],
                       local: Dict[int, Tuple[int, int]],
                       detections: Dict[str, List[Any]]) -> None:
    """`Q.MARK_SHAPE` for every dot / staccato-class box, off the PAGE raster
    (`pws.page.binary`, 0 = ink, staff lines IN) with the staff line(s)
    under the mark bridged out at the mark's own x. ROADMAP 2.133.

    ⚠️ LOCAL (CLAUDE.md Sec.5): the line rows are the ones
    `_local_staff_lines` re-finds in the columns around the mark -- the same
    finder `gather_dot_positions` (2.128) uses; where they cannot be placed
    the staff's own `line_ys` are used and `detail.lines` says `staff_grid`,
    and where the mark crosses no line `detail.lines` is `none_under_mark`.
    """
    page = getattr(pws, "page", None)
    binary = getattr(page, "binary", None)
    if binary is None or getattr(binary, "ndim", 0) != 2:
        return
    staves = []
    for st in getattr(pws, "staves", ()) or ():
        key = local.get(st.staff_index)
        ys = [float(y) for y in getattr(st, "line_ys", ()) or ()]
        sp = _spacing(st) if len(ys) >= 5 else None
        if key is None or not sp:
            continue
        thick = getattr(st, "median_line_thickness_px", None)
        staves.append((ys, float(sp), float(thick) if thick else None))
    cell_by_key = {}
    for c in cells or ():
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    H, W = binary.shape
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        frame = frame_cell(sub.cell)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        for gi, d in enumerate(dets):
            name = d.smufl_name
            if not (name == _DOT_CLASS or name in _STACCATO_CLASSES):
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            box = _page_box(c, d) if c is not None else None
            if box is None or not staves:
                log.abstain(g, Q.MARK_SHAPE, reader=READERS.CV_MARK_SHAPE,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="no page box or no staves")
                continue
            cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
            ys, sp, thick = min(
                staves, key=lambda t: max(min(t[0]) - cy, cy - max(t[0]),
                                          0.0) / t[1])
            x0, y0 = max(0, int(round(box[0])) - 1), max(0, int(round(box[1])) - 1)
            x1, y1 = min(W, int(round(box[2])) + 2), min(H, int(round(box[3])) + 2)
            if x1 - x0 < 2 or y1 - y0 < 2:
                log.abstain(g, Q.MARK_SHAPE, reader=READERS.CV_MARK_SHAPE,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="box off the raster")
                continue
            half = int(math.ceil((thick or 0.12 * sp) / 2.0))
            rows = None
            for win_sp in (DOT_LINE_WINDOW_SPACES, 5.0, 8.0):
                # the SAME finder, a wider window where the near one cannot
                # place five lines (a stem or a barline beside the mark)
                rows = _local_staff_lines(binary, ys, sp, cx, win_sp)
                if rows is not None:
                    break
            basis = "local_ink" if rows is not None else "staff_grid"
            use = rows if rows is not None else ys
            under = [r for r in use if y0 - half - 1 <= r <= y1 + half + 1]
            # the window is read wider than the box: a line's own thickness is
            # taken from the columns beside the mark, a bridge needs ink above
            # and below the band
            px = 5
            wx0, wx1 = max(0, x0 - px), min(W, x1 + px)
            wy0, wy1 = max(0, y0 - 3 * half - 4), min(H, y1 + 3 * half + 4)
            win = binary[wy0:wy1, wx0:wx1] == 0
            bands = [line_band_beside(win, r - wy0, x0 - wx0, x1 - wx0, half)
                     for r in under]
            win = erase_staff_lines(win, bands)
            win = win[y0 - wy0:y1 - wy0, x0 - wx0:x1 - wx0]
            m = mark_shape_of_ink(win, sp, rows=True)
            if m is None:
                log.abstain(g, Q.MARK_SHAPE, reader=READERS.CV_MARK_SHAPE,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="no ink in the box")
                continue
            log.observe(g, Q.MARK_SHAPE, m.pop("hw"),
                        reader=READERS.CV_MARK_SHAPE, frame=frame,
                        lines=(basis if under else "none_under_mark"), **m)


def _observe_mark_shape(log: Log, sub: Subject, frame: str, cell: Any,
                        dets: Optional[Sequence[Any]],
                        space: Optional[float]) -> None:
    """`Q.MARK_SHAPE` -- one row per `augmentationDot` / `articStaccato*`
    detection in this cell, on its own glyph subject. ROADMAP 2.131."""
    img = getattr(cell, "image_no_staff", None)
    for gi, d in enumerate(dets or ()):
        name = str(getattr(d, "smufl_name", ""))
        if not (name.startswith("augmentationDot") or name in _STACCATO_CLASSES):
            continue
        g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
        if img is None or getattr(img, "ndim", 0) != 2:
            log.abstain(g, Q.MARK_SHAPE, reader=READERS.CV_MARK_SHAPE,
                        frame=frame, reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            continue
        if not space or space <= 0:
            log.abstain(g, Q.MARK_SHAPE, reader=READERS.CV_MARK_SHAPE,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        note="no cell staff-space unit")
            continue
        m = mark_shape(img, (float(d.x_canonical), float(d.y_canonical),
                             float(d.width_canonical),
                             float(d.height_canonical)), space)
        if m is None:
            log.abstain(g, Q.MARK_SHAPE, reader=READERS.CV_MARK_SHAPE,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        note="box off the raster or no ink")
            continue
        log.observe(g, Q.MARK_SHAPE, m.pop("hw"),
                    reader=READERS.CV_MARK_SHAPE, frame=frame, **m)


def _observe_dot_stroke_ink(log: Log, sub: Subject, frame: str, cell: Any,
                            dets: Optional[Sequence[Any]],
                            space: Optional[float]) -> None:
    """`Q.DOT_STROKE_INK` -- one row per `augmentationDot` detection in this
    cell, on that detection's own glyph subject (the index into the cell's
    detections, the same numbering `_notehead_boxes_for_cell` uses).
    ROADMAP 2.69 follow-up."""
    img = getattr(cell, "image_no_staff", None)
    for gi, d in enumerate(dets or ()):
        if not str(getattr(d, "smufl_name", "")).startswith("augmentationDot"):
            continue
        g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
        if img is None or getattr(img, "ndim", 0) != 2:
            log.abstain(g, Q.DOT_STROKE_INK, reader=READERS.CV_DOT_STROKE,
                        frame=frame, reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            continue
        if not space or space <= 0:
            log.abstain(g, Q.DOT_STROKE_INK, reader=READERS.CV_DOT_STROKE,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        note="no cell staff-space unit")
            continue
        m = dot_stroke_ink(img, (float(d.x_canonical), float(d.y_canonical),
                                 float(d.width_canonical),
                                 float(d.height_canonical)), space)
        if m is None:
            log.abstain(g, Q.DOT_STROKE_INK, reader=READERS.CV_DOT_STROKE,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        note="box off the raster")
            continue
        log.observe(g, Q.DOT_STROKE_INK, m.pop("fraction"),
                    reader=READERS.CV_DOT_STROKE, frame=frame, **m)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.38 -- a second witness for `beams_ambiguous`: does a stem's own
# ink run unbroken into a candidate stroke's ink at the tip?
#
# `benchmarks/omr-duration-narrowed-2026-09/FINDINGS.md` SS2: the single
# biggest `duration_narrowed` class -- certain=0/possible=1, "nothing
# certainly covers this note, but one stroke MIGHT" -- had no connection at
# all, because `rhythm._beam_levels`'s column test is the ONLY witness to the
# fact and it is a first-hand geometric judgement, not a second reading. This
# is that second reading: a pixel-continuity scan at the exact junction,
# independent of the stroke's own bounding box the way `Q.STEM_TIP_INK` is
# independent of `Q.FLAG`'s own detected box (2.18c).
# ─────────────────────────────────────────────────────────────────────────────

#: CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (2.38). A
#: beamed stem's own ink is continuous with its beam at the tip -- the two
#: are drawn as one connected mark on a clean plate. Litolff MERGES and
#: Breitkopf SHATTERS (CLAUDE.md SS10), so a shattered junction may show a
#: thin blank seam at the exact join even where the stem and the beam are
#: the SAME mark -- the tolerance below exists for exactly that seam, not
#: for a genuinely separate stroke standing apart. Falsified by a print-
#: confirmed join whose seam is wider than one measured staff-line
#: thickness, or a print-confirmed NON-join (an unrelated stroke) whose gap
#: is narrower than one. NOT CONFIRMED -- argued from CLAUDE.md's own
#: shattering/merging finding, never measured against a beam-junction crop.
#:
#: WHY A STAFF-LINE THICKNESS, AND NOT A MAGIC PIXEL COUNT: it is the one
#: linear measurement already made of THIS PLATE's own ink erosion --
#: `cell.staff_line_thickness_canonical` (`measure_extractor.py`, scaled by
#: `gather_geometry` into the SAME canonical frame `image_no_staff` is in) --
#: so the tolerance scales with the plate instead of being one number for
#: every scan at every DPI. A staff line and a beam stroke are drawn with
#: comparable engraving weight, so a break the width of ONE line is the
#: largest gap a shattering plate plausibly puts in a mark that is really
#: continuous; a break wider than that is a genuinely separate piece of ink.
BEAM_STEM_JOIN_GAP_TOLERANCE_THICKNESS_MULT = 1.0
#: Where a cell's own line thickness was never traced (mirrors `LEDGER_
#: RUNG_INK_DEFAULT_THICKNESS_SPACES` -- same fallback, same reason: no cell
#: on either of this lane's own documents needed it). NOT CONFIRMED.
BEAM_STEM_JOIN_DEFAULT_THICKNESS_SPACES = 0.09

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.126 -- a stem that crosses a staff or ledger line is ONE stroke
# ─────────────────────────────────────────────────────────────────────────────
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a stem is one continuous stroke through the staff lines it crosses (Sean,
# 2026-10-09: *"a beam never has an arc"* is the same family -- strokes are not cut by what they cross). The staff-line ERASE (`staff_line_
# removal`: a vertical ink run through a line row no taller than 2x the line's thickness is "the line" and is erased) wipes a short stem piece
# that sits between two thin spots of the scan, and the scan itself thins the stem on both flanks of a line. Brahms 317803 p0 q86/q93 (cell
# 0/0/0/4): the join walk saw ONE 46 px blank run against the 21.7 px tolerance (the line band 25 rows + two real breaks of 8 and 14 rows,
# both measured off the raw page); each flank alone is under the tolerance. WHAT WOULD FALSIFY IT: a beam whose stem has a real break wider
# than the tolerance on a flank of a line (not bridged: the flank rule keeps it NOT joined, tested), or a stroke other than a stem standing in
# the walked window (`_beam_stem_intervening_stroke` still runs first, on the erased image). Sean confirmed on 9 tiles (9/9); default ON 2026-10-15.
#
# A sibling row mask serves the hook counter (`stem_tip_hooks`, `OMR_HOOKS_LINE_BRIDGE`, `line_rows_past_flag`): a run of attached ink that is
# nothing but line rows is a ledger or staff line crossing the hook band, not a second hook (Brahms p0 q1009: a 28-row ledger line of which
# the shipped `_tip_line_rows` classed 5, counted as a second run in 36.7% of the band's columns against the 0.12 glitch cut). It asks the
# right side only, because that ledger line ends just LEFT of the stem (left flank 0.2-0.38) and runs 1.26 spaces out on the right.
BEAM_JOIN_LINE_BRIDGE_ENV = "OMR_BEAM_JOIN_LINE_BRIDGE"
HOOKS_LINE_BRIDGE_ENV = "OMR_HOOKS_LINE_BRIDGE"
#: A row is a LINE row at a stem where the RAW page inks both flanks of the stem: this wide, this far out (staff spaces), at least this much.
LINE_ROW_FLANK_NEAR_SPACES = 0.1
LINE_ROW_FLANK_FAR_SPACES = 0.5
LINE_ROW_FLANK_FILL = 0.7
#: A run of attached ink counts as a line when at least this share of its rows are line rows (a ledger line's soft edges are not).
LINE_RUN_MIN_SHARE = 0.75


def beam_join_line_bridge_enabled() -> bool:
    """Default ON (Sean 2026-10-15, ROADMAP 2.126): a deny-list -- only an explicit off-word restores the shipped reader."""
    return os.environ.get(BEAM_JOIN_LINE_BRIDGE_ENV, "1").strip().lower() not in ("0", "", "false", "no", "off")


def hooks_line_bridge_enabled() -> bool:
    """Default ON (Sean 2026-10-15, ROADMAP 2.126): a deny-list -- only an explicit off-word restores the shipped reader."""
    return os.environ.get(HOOKS_LINE_BRIDGE_ENV, "1").strip().lower() not in ("0", "", "false", "no", "off")


def line_rows_across_stem(raw_ink: Any, stem_x0: float, stem_x1: float, space: float,
                          y_lo: float, y_hi: float) -> Any:
    """Boolean per row of the raster: a LINE (staff or ledger) crosses this stem here -- the RAW page's ink fills at least
    `LINE_ROW_FLANK_FILL` of the flank on EACH side of the stem (`LINE_ROW_FLANK_NEAR_SPACES`..`FAR_SPACES` out). ROADMAP 2.126.

    ⚠️ Raw, never the erased image: the erase is what hid the line's pixels. Both flanks are required, so a flag, a head or a beam on ONE
    side of the stem is not a line; only rows in `[y_lo, y_hi)` are tested."""
    import numpy as np
    H, W = raw_ink.shape
    out = np.zeros(H, dtype=bool)
    a = max(0, int(round(stem_x0 - LINE_ROW_FLANK_FAR_SPACES * space)))
    b = max(0, int(round(stem_x0 - LINE_ROW_FLANK_NEAR_SPACES * space)))
    c = min(W, int(round(stem_x1 + LINE_ROW_FLANK_NEAR_SPACES * space)))
    d = min(W, int(round(stem_x1 + LINE_ROW_FLANK_FAR_SPACES * space)))
    if b <= a or d <= c:
        return out
    y0, y1 = max(0, int(round(y_lo))), min(H, int(round(y_hi)))
    if y1 <= y0:
        return out
    left = raw_ink[y0:y1, a:b].mean(axis=1) >= LINE_ROW_FLANK_FILL
    right = raw_ink[y0:y1, c:d].mean(axis=1) >= LINE_ROW_FLANK_FILL
    out[y0:y1] = left & right
    return out


#: Where a straight line leaves a stem's RIGHT edge far past any flag: a flag reaches about 0.85 space from its stem (Brahms p0), so ink
#: filling this flank, with the near flank, on the same rows is a horizontal stroke and not a hook. A ledger line can end just LEFT of the stem
#: (q1009: its left flank reads 0.2-0.38), which is why the hook counter asks the right side only.
LINE_ROW_PAST_FLAG_NEAR_SPACES = (0.1, 0.5)
LINE_ROW_PAST_FLAG_FAR_SPACES = (0.9, 1.2)
LINE_ROW_PAST_FLAG_FILL = 0.85


def line_rows_past_flag(raw_ink: Any, stem_x1: float, space: float, y_lo: float, y_hi: float) -> Any:
    """Boolean per row: the RAW page inks the right flank of this stem both beside it and `LINE_ROW_PAST_FLAG_FAR_SPACES` out -- a straight
    horizontal stroke runs through, past where any flag reaches. ROADMAP 2.126 (`OMR_HOOKS_LINE_BRIDGE`)."""
    import numpy as np
    H, W = raw_ink.shape
    out = np.zeros(H, dtype=bool)
    y0, y1 = max(0, int(round(y_lo))), min(H, int(round(y_hi)))
    if y1 <= y0:
        return out
    na, nb = (int(round(stem_x1 + v * space)) for v in LINE_ROW_PAST_FLAG_NEAR_SPACES)
    fa, fb = (int(round(stem_x1 + v * space)) for v in LINE_ROW_PAST_FLAG_FAR_SPACES)
    nb, fb = min(W, nb), min(W, fb)
    if nb <= na or fb <= fa or fa >= W:
        return out
    near = raw_ink[y0:y1, na:nb].mean(axis=1) >= LINE_ROW_PAST_FLAG_FILL
    far = raw_ink[y0:y1, fa:fb].mean(axis=1) >= LINE_ROW_PAST_FLAG_FILL
    out[y0:y1] = near & far
    return out


def _cell_raw_ink(cell: Any) -> Any:
    """The cell's UN-erased ink (True = ink), or `None`."""
    import numpy as np
    b = getattr(cell, "binary", None)
    if b is not None and getattr(b, "ndim", 0) == 2:
        return np.asarray(b) == 0
    img = getattr(cell, "image", None)
    if img is None:
        return None
    img = np.asarray(img)
    gray = img if img.ndim == 2 else img[..., :3].mean(axis=2)
    return gray < 128


def _hook_line_rows(cell: Any, x0: float, x1: float, space: float) -> Any:
    """`line_rows` for `stem_tip_hooks` -- `None` unless `OMR_HOOKS_LINE_BRIDGE` is on and the cell's raw and erased rasters agree."""
    if not hooks_line_bridge_enabled():
        return None
    raw_ink = _cell_raw_ink(cell)
    img = getattr(cell, "image_no_staff", None)
    if raw_ink is None or img is None or raw_ink.shape != img.shape:
        return None
    return line_rows_past_flag(raw_ink, x1, space, 0, raw_ink.shape[0])


def _beam_stem_beyond_tip(tip_y: float, end: str, stroke_y0: float,
                          stroke_y1: float) -> bool:
    """Is this candidate stroke resolvable relative to the tip -- either
    ending IN it, or standing CLEANLY past it -- rather than crossing the
    stem's own body somewhere in between? ROADMAP 2.38, post-review fix.

    ⚠️⚠️ THE THIRD CASE IS NOT "NOT JOINED", IT IS "CANNOT TELL" (manager
    review of 024bdc7c). A stroke whose near edge sits neither at-or-past
    the tip nor inside the stroke's own range is exactly the shape of THREE
    different real things, and ink position alone cannot separate them:
    (1) a SECONDARY beam (16th/32nd) attaching along the stem's body just
    inside the PRIMARY -- on a real `certain=1, possible=2` note this is
    usually the second level, not an intruder; (2) a `Q.STEM` box that
    overshoots its own beam (the CV stem read past the ink it should have
    stopped at), which puts the PRIMARY itself in this same position; (3) a
    slur/arc crossing the stem, which is the only one of the three this
    function's own name originally meant. The ink test cannot tell (1)/(2)
    from (3) -- reading it as "not joined" DROPPED a real secondary beam's
    only candidate stroke, which is the bug this fix closes. Shared by
    `beam_stem_join_ink`'s own gate and `_observe_beam_stem_join`'s abstain
    reason, so the two cannot drift apart.
    """
    if stroke_y0 <= tip_y <= stroke_y1:
        return True                  # ends IN it -- unambiguous
    if end == "top":
        return stroke_y1 <= tip_y
    return stroke_y0 >= tip_y


def _beam_stem_horizontally_reaches(stem_x0: float, stem_x1: float,
                                    stroke_x0: float, stroke_x1: float,
                                    tol: float) -> bool:
    """Does this candidate stroke's own horizontal extent COVER the stem's
    (within `tol`)? ROADMAP 2.38, second post-review fix.

    ⚠️⚠️ THE BUG (Brahms p1 print check, manager review of 3c748f45): the
    continuity scan below walks the STEM's OWN x-range vertically, and nowhere
    checked that the CANDIDATE stroke it was asked about is even horizontally
    near that stem. A stroke belonging to a DIFFERENT group -- 4-10 staff
    spaces to the side -- can share a y-height with THIS stem's own real
    beam (drawn directly above/below the tip, in the stem's own column); the
    scan then finds THAT ink, wrongly credits it to the far-away candidate,
    and reports JOINED for a stroke that never touches this stem at all. A
    stroke that does not reach the stem horizontally is NOT this stem's
    stroke BY CONSTRUCTION -- a fact about the two boxes, not the raster --
    so it is checked FIRST, before any pixel is read.
    """
    return stroke_x0 <= stem_x1 + tol and stroke_x1 >= stem_x0 - tol


def _beam_stem_intervening_stroke(ink: Any, ix0: int, ix1: int, iy0: int,
                                  iy1: int, stem_width_px: float,
                                  thickness_px: float) -> bool:
    """Between the tip and the candidate's own near edge, does the walked
    column pass through a DIFFERENT stroke first? ROADMAP 2.38, third
    post-review fix.

    ⚠️⚠️ THE BUG (Brahms p1 re-check, manager review of 3a5bbb67, seed 7):
    2 of 4 JOINED crops were still wrong -- the candidate is a long THIN
    line (a slur/hairpin the detector boxed as a beam stroke) lying just
    beyond the stem's OWN real beam. The blank-run scan measures only
    whether the column is UNBROKEN; it does not ask WHOSE ink that is, so
    the stem's own genuinely-attached beam (thick, immediate, right at the
    tip) reads as "continuing on" toward the far candidate, and the small
    gap between the beam's own far edge and the thin line's near edge
    passes the same tolerance meant for a shattered PLATE seam.

    ⚠️⚠️ THE PRINCIPLE (engraving, stated by the manager): a stem is
    joined to the FIRST stroke its column meets past the tip, never to one
    beyond another stroke. A beam is drawn far WIDER than the stem it
    serves (it reaches sideways to every note it covers); a stem's own ink
    is not. So: at each row in the walked window, does ink reach past the
    stem's own column by more than one STEM WIDTH on at least one side,
    sustained over a run of rows at least one measured staff-line
    thickness long (a single wide pixel is noise; a beam's own vertical
    stroke height is not)? That shape is a DIFFERENT stroke lying in the
    path, whatever it is -- the walk must not treat what lies past it as
    still reaching the stem.

    ⚠️ A KNOWN LIMITATION, NAMED NOT SOLVED: a genuinely continuous single
    beam that happens to be split into two adjacent CV-detected boxes (the
    "candidate" being the tail end of the SAME physical stroke the window
    itself is already wide with) would also trip this guard -- the check
    cannot distinguish "another stroke" from "the same stroke, re-boxed"
    by shape alone. Not measured against a real case of that shape; if one
    turns up, the fix is a subject-identity join, not a wider window here.
    """
    if iy1 <= iy0:
        return False
    H, W = ink.shape
    margin = max(1, int(round(stem_width_px)))
    probe = max(2, int(round(thickness_px)))
    left_x0, left_x1 = max(0, ix0 - margin - probe), max(0, ix0 - margin)
    right_x0, right_x1 = min(W, ix1 + margin), min(W, ix1 + margin + probe)
    min_run = max(1, int(round(thickness_px)))
    run = 0
    for y in range(iy0, iy1):
        wide = ((left_x1 > left_x0 and ink[y, left_x0:left_x1].any())
                or (right_x1 > right_x0 and ink[y, right_x0:right_x1].any()))
        if wide:
            run += 1
            if run >= min_run:
                return True
        else:
            run = 0
    return False


def beam_stem_join_ink(img: Any, stem_x0: float, stem_x1: float,
                       tip_y: float, end: str, stroke_x0: float,
                       stroke_x1: float, stroke_y0: float,
                       stroke_y1: float, gap_tolerance_px: float,
                       line_rows: Any = None
                       ) -> Optional[Dict[str, Any]]:
    """Does this stem's own ink, in its own x-range, run CONTINUOUSLY from
    `tip_y` into ink at or past the candidate stroke's near edge -- with no
    OTHER stroke lying in the path -- AND does that candidate stroke
    horizontally reach the stem at all? ROADMAP 2.38.

    All of `stem_x0`, `stem_x1`, `tip_y`, `stroke_x0`, `stroke_x1`,
    `stroke_y0`, `stroke_y1` and `gap_tolerance_px` are in the SAME
    canonical CELL pixels `Q.STEM`'s own box is in -- this function does no
    frame conversion, the same contract `stem_tip_ink`/`ledger_rung_ink`
    state for themselves. `end` is `"top"` (this stem's TOP is the tip
    under test, the stroke is expected ABOVE it) or `"bottom"` (the
    reverse) -- GATHER does not know which end is the true tip, so the
    caller asks both and files one row each.

    Outcomes:

    * the candidate's own x-range does not reach the stem's, within
      `gap_tolerance_px` -- NOT JOINED, a real answer settled by the two
      boxes alone: a stroke that does not cover the stem cannot be its
      beam, by construction (post-review fix, `_beam_stem_horizontally_
      reaches`'s own docstring has the argument);
    * the tip already sits INSIDE the stroke's own y-range -- the stem
      ends IN the beam, joined with no gap to walk;
    * the stroke stands cleanly past the tip (the whole stroke is on the
      tip's own far side) -- walk the stem's own x-range from the tip to
      the stroke's near edge: if a DIFFERENT, wider stroke lies in that
      path first, NOT JOINED (`_beam_stem_intervening_stroke`'s own
      docstring has the argument -- a stem joins the FIRST stroke its
      column meets, never one beyond another); otherwise look for the
      LONGEST unbroken blank run and join iff it never exceeds
      `gap_tolerance_px`.

    Returns `None` -- DECLINED, never defaulted -- where the raster or the
    stem's own x-range is missing, the scanned window falls entirely off
    the raster, OR the stroke neither reaches the tip nor stands cleanly
    past it (rule 8: cannot tell is never an answer, so the note stays
    NARROWED rather than losing this candidate outright).
    """
    if img is None or getattr(img, "ndim", 0) != 2:
        return None
    if stem_x1 <= stem_x0 or stroke_y1 < stroke_y0:
        return None
    ink = (img == 0)
    H, W = ink.shape
    ix0, ix1 = max(0, int(round(stem_x0))), min(W, int(round(stem_x1)))
    if ix1 <= ix0:
        return None
    if not _beam_stem_horizontally_reaches(stem_x0, stem_x1, stroke_x0,
                                           stroke_x1, gap_tolerance_px):
        # NOT JOINED -- a real answer, not a decline (rule 6: the two boxes
        # alone settle this, no ink need be read at all).
        return {"found": False, "gap_px": None, "max_blank_run_px": None,
                "gap_tolerance_px": round(float(gap_tolerance_px), 2),
                "window_canonical": None,
                "reason": "stroke_does_not_reach_stem_horizontally"}
    if not _beam_stem_beyond_tip(tip_y, end, stroke_y0, stroke_y1):
        return None

    # ⚠️ `gap_tolerance_px` IS ECHOED INTO EVERY RETURN, NEVER PASSED AS ITS
    # OWN NAMED KEYWORD AT THE CALL SITE -- the same shape `stem_tip_ink`'s
    # own diagnostic fields use (`**m`, not a hand-spelled kwarg), which is
    # what keeps a single detail key from needing its own `wiring.KNOWN_GAPS`
    # entry: `wiring.details`'s AST walk only tracks a LITERAL keyword at the
    # `log.observe`/`log.abstain` call, not a name inside a dict spread.
    if stroke_y0 <= tip_y <= stroke_y1:
        # The stem ends IN the beam -- no gap, nothing to walk.
        return {"found": True, "gap_px": 0.0, "max_blank_run_px": 0,
                "gap_tolerance_px": round(float(gap_tolerance_px), 2),
                "window_canonical": [round(stem_x0, 2), round(tip_y, 2),
                                     round(stem_x1, 2), round(tip_y, 2)]}

    near_edge = stroke_y1 if end == "top" else stroke_y0
    y0, y1 = sorted((tip_y, near_edge))
    iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
    if iy1 <= iy0:
        return None
    if _beam_stem_intervening_stroke(ink, ix0, ix1, iy0, iy1,
                                     stem_x1 - stem_x0, gap_tolerance_px):
        # NOT JOINED -- the walk meets a DIFFERENT, wider stroke (this
        # stem's own already-attached beam, most often) before it ever
        # reaches the candidate; a stem joins the FIRST stroke past its
        # tip, never one beyond another.
        return {"found": False, "gap_px": round(float(y1 - y0), 2),
                "max_blank_run_px": None,
                "gap_tolerance_px": round(float(gap_tolerance_px), 2),
                "window_canonical": [round(stem_x0, 2), round(y0, 2),
                                     round(stem_x1, 2), round(y1, 2)],
                "reason": "intervening_stroke"}
    region = ink[iy0:iy1, ix0:ix1]
    row_ink = region.any(axis=1)
    max_blank = 0
    run = 0
    for v in row_ink:
        if v:
            run = 0
        else:
            run += 1
            if run > max_blank:
                max_blank = run
    found = max_blank <= gap_tolerance_px
    out = {"found": bool(found), "gap_px": round(float(y1 - y0), 2),
           "max_blank_run_px": int(max_blank),
           "gap_tolerance_px": round(float(gap_tolerance_px), 2),
           "window_canonical": [round(stem_x0, 2), round(y0, 2),
                                round(stem_x1, 2), round(y1, 2)]}
    if not found and line_rows is not None:
        # ⚠️⚠️ ROADMAP 2.126 (`OMR_BEAM_JOIN_LINE_BRIDGE`, default ON since 2026-10-15; the caller passes `line_rows` only then): the walk's rows that a
        # staff or ledger line fills (the RAW page inks both flanks of the stem there) are where the erase took the stem's own pixels, so
        # they are set aside -- neither ink nor blank -- and each flank's blank run is measured alone against the SAME tolerance. A real
        # break wider than the tolerance on either side of the line, or a gap with no line in it, is still NOT joined.
        n_set, run, max_off = 0, 0, 0
        for k, v in enumerate(row_ink):
            y = iy0 + k
            if y < len(line_rows) and line_rows[y]:
                n_set += 1
                run = 0
            elif v:
                run = 0
            else:
                run += 1
                if run > max_off:
                    max_off = run
        bridged = n_set > 0 and max_off <= gap_tolerance_px
        out["line_bridge"] = {"rows_set_aside": int(n_set), "max_blank_off_line_px": int(max_off),
                              "margin_px": round(float(gap_tolerance_px) - float(max_off), 2)}
        out["found"] = bool(bridged)
    return out


def _observe_beam_stem_join(log: Log, sub: Subject, frame: str, cell: Any,
                            stem_rows_logged: Sequence[Tuple[Any, str]],
                            beam_rows_logged: Sequence[Tuple[Any, str]],
                            space: Optional[float]) -> None:
    """`Q.BEAM_STEM_JOIN` -- one row per (`Q.STEM` row, `Q.BEAM_STROKE` row,
    end). ROADMAP 2.38.

    Every stem in this cell against every candidate stroke in this cell,
    both ends -- the pairing ADJUDICATE needs is decided later (which end
    is the true tip, `Q.STEM_DIRECTION`; which stroke is even a candidate,
    `rhythm._beam_levels`'s own column test), so GATHER files the whole
    small cross product rather than guessing which pairs will matter.
    """
    img = getattr(cell, "image_no_staff", None)
    if img is None or getattr(img, "ndim", 0) != 2:
        for _sd, stem_id in stem_rows_logged:
            for _bd, beam_id in beam_rows_logged:
                for end in ("top", "bottom"):
                    log.abstain(sub, Q.BEAM_STEM_JOIN,
                                reader=READERS.CV_BEAM_JOIN, frame=frame,
                                reason=ABSTAIN.NO_MASK,
                                stem_row_id=stem_id, beam_row_id=beam_id,
                                end=end,
                                note="cell carries no image_no_staff")
        return
    thickness = getattr(cell, "staff_line_thickness_canonical", None)
    tol = ((float(thickness) if thickness else
           BEAM_STEM_JOIN_DEFAULT_THICKNESS_SPACES * space) *
          BEAM_STEM_JOIN_GAP_TOLERANCE_THICKNESS_MULT) if space else None
    for stem_d, stem_id in stem_rows_logged:
        sx0 = float(stem_d.x_canonical)
        sx1 = sx0 + float(stem_d.width_canonical)
        sy0 = float(stem_d.y_canonical)
        sy1 = sy0 + float(stem_d.height_canonical)
        no_x = sx1 <= sx0
        # ROADMAP 2.126 (`OMR_BEAM_JOIN_LINE_BRIDGE`): where a line crosses THIS stem, read off the RAW page; `None` with the flag off, so
        # `beam_stem_join_ink` runs exactly as shipped and files not one new key.
        line_rows = None
        if beam_join_line_bridge_enabled() and not no_x and space:
            raw_ink = _cell_raw_ink(cell)
            if raw_ink is not None and raw_ink.shape == img.shape:
                line_rows = line_rows_across_stem(raw_ink, sx0, sx1, space, 0, img.shape[0])
        for beam_d, beam_id in beam_rows_logged:
            bx0 = float(beam_d.x_canonical)
            bx1 = bx0 + float(beam_d.width_canonical)
            by0 = float(beam_d.y_canonical)
            by1 = by0 + float(beam_d.height_canonical)
            for end, tip_y in (("top", sy0), ("bottom", sy1)):
                if no_x:
                    log.abstain(sub, Q.BEAM_STEM_JOIN,
                                reader=READERS.CV_BEAM_JOIN, frame=frame,
                                reason=ABSTAIN.NO_STAFF_GEOMETRY,
                                stem_row_id=stem_id, beam_row_id=beam_id,
                                end=end, note="stem carries no x-range")
                    continue
                if tol is None:
                    log.abstain(sub, Q.BEAM_STEM_JOIN,
                                reader=READERS.CV_BEAM_JOIN, frame=frame,
                                reason=ABSTAIN.NO_STAFF_GEOMETRY,
                                stem_row_id=stem_id, beam_row_id=beam_id,
                                end=end, note="no cell staff-space unit")
                    continue
                m = beam_stem_join_ink(img, sx0, sx1, tip_y, end,
                                      bx0, bx1, by0, by1, tol, line_rows=line_rows)
                if m is None:
                    if _beam_stem_beyond_tip(tip_y, end, by0, by1):
                        reason = ABSTAIN.NO_STAFF_GEOMETRY
                        note = "window off the raster"
                    else:
                        # ⚠️ THE FIX (manager review of 024bdc7c): this
                        # candidate neither reaches the tip nor stands
                        # cleanly past it -- a secondary beam, an overshot
                        # stem box, or a slur can each put a stroke here,
                        # and position alone cannot tell them apart. Named,
                        # not silently folded into the raster-missing
                        # reason above.
                        reason = ABSTAIN.AMBIGUOUS
                        note = ("stroke neither reaches the tip nor stands "
                                "cleanly past it -- a mid-length crossing "
                                "(secondary beam, overshot stem box, or a "
                                "slur) cannot be told apart by position")
                    log.abstain(sub, Q.BEAM_STEM_JOIN,
                                reader=READERS.CV_BEAM_JOIN, frame=frame,
                                reason=reason,
                                stem_row_id=stem_id, beam_row_id=beam_id,
                                end=end, note=note)
                    continue
                found = m.pop("found")
                log.observe(sub, Q.BEAM_STEM_JOIN, found,
                            reader=READERS.CV_BEAM_JOIN, frame=frame,
                            stem_row_id=stem_id, beam_row_id=beam_id,
                            end=end, **m)


# ─────────────────────────────────────────────────────────────────────────────
# The ink — every connected piece of it, named or not
# ─────────────────────────────────────────────────────────────────────────────

#: `OMR_INK` -- gather one row per connected piece of a cell's ink.
#:
#: **Default ON since 2026-09-17 (Sean's call)**, written as a DENY-list:
#: CLAUDE.md's "A flag's OFF test must follow its DEFAULT", where five shipped
#: flags had it backwards. Turning it on ADDS ROWS TO EVERY RECORD the staged
#: pipeline writes, which is the widest blast radius a gather change has, and
#: every default here is Sean's.
INK_ENV = "OMR_INK"

#: ⚠️ Glyph indices for ink components, offset past both the detector's
#: ordinals and `_CV_GLYPH_BASE`, so three readers can never collide in one
#: cell's key space. A collision would not raise; it would silently merge a
#: component row and a detection row into one subject.
_INK_GLYPH_BASE = 200_000


def _ink_enabled() -> bool:
    #: ⚠️ A DENY-LIST, because this is now DEFAULT ON. An allow-list under a
    #: default-ON flag lets an empty value or a typo silently restore the old
    #: behaviour -- CLAUDE.md's "A flag's OFF test must follow its DEFAULT",
    #: where five shipped flags had it backwards. Only an explicit off word
    #: turns it off.
    return os.environ.get(INK_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


def _ink_components(cell: Any):
    """(x, y, w, h, area) for every connected piece of this cell's ink.

    Read off `cell.image_no_staff` -- the staff-line-erased variant, 0 = ink.
    NOT off `cell.image`: with the lines in, every mark a line passes through
    is one component with every other mark on that line, and the population
    would be five components a cell whatever the page prints.
    """
    import cv2
    import numpy as np
    img = getattr(cell, "image_no_staff", None)
    if img is None or getattr(img, "ndim", 0) != 2:
        return None
    # ROADMAP 2.191: five gather readers ask this of every cell; it is a pure function of the erased raster, so the
    # first answer is kept on the cell (checked against the raster itself) and each caller gets its own list.
    hit = getattr(cell, "_ink_components_191", None)
    if hit is not None and hit[0] is img:
        return list(hit[1])
    ink = (img == 0).astype(np.uint8)
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(ink, 8)
    comps = [tuple(int(stats[i, k]) for k in range(5)) for i in range(1, n)]
    try:
        cell._ink_components_191 = (img, comps)
    except Exception:                                  # noqa: BLE001  (a cell that takes no attribute is just not cached)
        pass
    return list(comps)


def _explaining_detections(dets: Sequence[Any], spacing: float
                           ) -> List[Tuple[float, float, float, float, str]]:
    """The detections whose BOX is a fair account of the ink inside it.

    ⚠️ A DETECTION WIDER THAN A GLYPH CAN BE IS EXCLUDED, and the constant is
    IMPORTED from `direction_text.BandConfig.max_blank_width_spaces` rather
    than restated -- the same rule, measured for the same reason, and this
    repo has paid twice for two copies of one number. A `staff` box is 26.6
    staff spaces wide and a `slur` box is the rectangle its arc travels
    through; both are mostly paper, so counting them as an account of the ink
    they enclose would report EVERY component of a cell as explained. Measured
    on Litolff p.62 cell 6 before the rule was applied: all seventeen staves'
    printed `3/4` read as fully covered, by the `staff` box.
    """
    from ..direction_text import DEFAULT_BAND_CONFIG
    cut = DEFAULT_BAND_CONFIG.max_blank_width_spaces * spacing
    out = []
    for d in dets:
        if d.width_canonical > cut:
            continue
        out.append((float(d.x_canonical), float(d.y_canonical),
                    float(d.x_canonical + d.width_canonical),
                    float(d.y_canonical + d.height_canonical),
                    d.smufl_name))
    return out


def _coverage(box: Tuple[int, int, int, int],
              boxes: Sequence[Tuple[float, float, float, float, str]]):
    """What share of this component's box the detections account for, and who.

    ⚠️ THE UNION, NOT A SUM. Two overlapping detections over one component
    must not add up to more than the component, and on a scan they routinely
    overlap -- the same notehead survives NMS as three rows at IoU 0.91-0.96
    on the staged path, which `gather_detections` records and does not fix.
    """
    import numpy as np
    x, y, w, h = box
    if w <= 0 or h <= 0:
        return 0.0, ()
    mask = np.zeros((h, w), dtype=bool)
    who: List[str] = []
    for (bx0, by0, bx1, by1, name) in boxes:
        ix0, iy0 = max(x, bx0), max(y, by0)
        ix1, iy1 = min(x + w, bx1), min(y + h, by1)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        mask[int(iy0) - y:int(iy1) - y, int(ix0) - x:int(ix1) - x] = True
        who.append(name)
    return float(mask.sum()) / float(w * h), tuple(sorted(set(who)))


def gather_ink(log: Log, cells: Sequence[Any],
               local: Dict[int, Tuple[int, int]],
               detections: Dict[str, List[Any]], *,
               component_rows: bool = False,
               progress: bool = False) -> None:
    """Every connected piece of ink in every cell, whether or not it is named.

    ⚠️⚠️ **`component_rows=False` (the DEFAULT since roadmap 1.1) FILES ONE
    SUMMARY ROW PER CELL, NOT ONE ROW PER COMPONENT.** Measured
    (`benchmarks/omr-ink-gather-2026-09/probe/byte_share.py` for content
    share, `record_slim.py` run on the two committed shared records for the
    realised effect): as COMPACT-JSON CONTENT, `Q.INK` observations are only
    3.5-4.9% of a record (8.5 MB of 244.2 MB compact on Breitkopf, 3.8 MB of
    77.7 MB compact on Beethoven -- `arc_owner`'s `considered` lists are
    57-75% of the same compact total, an unrelated finding, reported
    separately). ⚠️⚠️ **BUT THAT UNDERSTATES THE REALISED SAVING, AND THE GAP
    IS WORTH RECORDING: one pretty-printed (`indent=2`) `Q.INK` row measured
    924 bytes against its own ~540-byte compact form** -- a SHORT, FLAT
    record like one ink component costs proportionally more under
    `indent=2` than a deeply-nested one, because every leaf sits on its own
    line. Slimming 7,093 Litolff rows to 1,183 cells and 15,212 Breitkopf
    rows to 818 cells, WITH THE FORMAT HELD CONSTANT (compact-proxy before
    vs after), saves 3.4 MB / 4.4% and 8.1 MB / 3.3% respectively --
    consistent with the content-share figures, as it should be. Running
    `record_slim.py` on the same two files -- which also happens to
    re-serialise everything compactly, a SEPARATE and much larger effect --
    measures 146.4->75.0 MB and 461.1->237.3 MB (~48-51%, dominated by the
    format switch, NOT attributable to this schema change). See
    `record_slim.py`'s own docstring for the full breakdown. So slimming ink
    is real (Litolff 7,093 rows -> 1,183 cells; Breitkopf 15,212 -> 818) and
    is what the flag table names for roadmap 1.1 (`docs/flags-2026-09.md`:
    *"stays ON until roadmap 1.1 persists the summary instead of rows"*),
    but on its own, format held constant, it is NOT the lever that gets a
    whole-movement record under the 20 MB/page budget -- `arc_owner` is.

    Only TWO real record consumers exist, both checked by grep rather than
    assumed: `trace.empty_claims` (and its sibling family/subject report)
    reads `Q.INK` only to ask *which cells have ink at all* and *how many
    components did we see* -- both survive a per-cell summary exactly, and
    `trace.py` is patched to sum `ink_n_components` ONCE PER CELL rather than
    once per row so it reads either shape correctly. `positional_store.py`
    is the SECOND consumer -- one `Entry` per COMPONENT, each with its own
    position, shape and `ink_explained_by` membership -- and it is
    genuinely full-grain: Sean's own rule for that store is *"we may need
    shape... we may need location... don't limit... every dot of black"*,
    which a per-cell aggregate cannot honour. `component_rows=True`
    (`--ink-rows` on the CLI) reproduces the PRE-1.1 behaviour exactly, byte
    for byte, for exactly that consumer -- it is not a compatibility shim,
    it is the only correct input `positional_store.py` can be given.

    ⚠️ ABSTENTIONS ARE UNCHANGED EITHER WAY: `no_mask` / `no_ink` are already
    filed per CELL, so there was nothing to collapse there.

    ⚠️⚠️ THIS IS THE BASE LAYER, NOT A SUPPLEMENT, AND THE DISTINCTION IS
    SEAN'S. `A-DUR-5`, 2026-09-09: *"I really don't want to lose the 'here is
    a blob of ink but we don't know what it is' gather data point. It can be
    used in every decision point ... this is the same unrecognizable blob on
    every system at bar 51 ... or we know what this blob is in 3 of the 10
    systems and they all line up."* And 2026-09-17, on what the population
    is: *"ink is ink. There is nothing that should be classified as unseen -
    only unclassified."* Every other measurement in GATHER starts from a
    DETECTION, so until this rung the record's population was the detector's
    output and ink it did not fire on produced no row at all.
    THE POWER IS ALIGNMENT: unnamed ink at one column across many staves is a
    printed event whatever it is, and where a few staves classify it the
    minority names what the majority corroborates.

    ⚠️ IT DECIDES NOTHING AND IT FILTERS NOTHING. Staff-line residue,
    barlines, stems, page edges and scanner speckle all get a row, because a
    threshold applied here is a decision taken in the wrong stage and the one
    kind that cannot be revisited -- a row that was never created is evidence
    no later rule can reconsider. Sean, 2026-09-17: *"even staff residue
    should go through the process and hopefully our rules and measurements
    will determine at the appropriate stage that it is just that."* The row
    carries the shape and the detector coverage so a later rule can NAME the
    residue; naming it is that rule's job, not this one's.

    ⚠️ THE PAGE FRAME IS THE POINT. A canonical x is measured inside one cell
    rescaled so the staff span is constant, so two staves' canonical x are not
    the same quantity -- `Q.ONSET_COLUMN` reported 1,062 columns of nothing
    before page pixels arrived, and this quantity's whole purpose is a
    cross-staff column. A cell that cannot supply a page frame gets
    `frame_note` and NO page fields, declined rather than defaulted.

    ⚠️ A COMPONENT IS A PIECE OF INK, NOT A MARK. On a scan a notehead merges
    with its ledger line and a staff-line remnant bridges two glyphs. Measured
    over 221 cells of Litolff Beethoven 5 p.62, staff-line removal clears a
    median 55% of a cell's ink and the largest surviving component holds a
    median 46% of what is left, at 5.6 components per cell. That is reported
    on the row (`ink_n_components`, `ink_share_of_cell`) rather than
    repaired, so a consumer can see when it is looking at a merge.
    """
    if not _ink_enabled():
        return
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sys_idx, st_idx = key
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        frame = frame_cell(c.measure_index)

        comps = _ink_components(c)
        if comps is None:
            # ⚠️ The erased variant is missing, which `prepare_pages` calls
            # "not optional" -- and `line_detection` SILENTLY falls back to
            # `cell.image` in the same situation. Refusing by name is what
            # keeps a whole-rung failure from reading as a blank page.
            log.abstain(sub, Q.INK, reader=READERS.CV_INK, frame=frame,
                        reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            continue
        if not comps:
            log.abstain(sub, Q.INK, reader=READERS.CV_INK, frame=frame,
                        reason=ABSTAIN.NO_INK)
            continue

        # ⚠️ THE UNIT IS THE CELL'S OWN, NOT THE PAGE'S, and not the nominal
        # `CANONICAL_STAFF_SPAN_PX / 4`. `_upscale_to_canonical` scales a
        # too-wide cell by WIDTH, so on one engraved fixture 184 of 368 cells
        # read 100 px per space and the other 184 read 38.5-56 -- which is why
        # `Q.CELL_STAFF_SPACE` exists as a quantity at all. Taken from
        # `_cell_grid`, the one spelling of this measurement.
        grid = _cell_grid(c)
        spacing = grid[1] * 2.0 if grid else None
        dets = detections.get(sub.to_key(), ())
        boxes = _explaining_detections(dets, spacing) if spacing else []
        total_ink = float(sum(a for (_x, _y, _w, _h, a) in comps)) or 1.0
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        page_ok = bool(up) and bool(cell_box) and len(cell_box or ()) == 4

        if component_rows:
            for i, (x, y, w, h, area) in enumerate(comps):
                cov, who = _coverage((x, y, w, h), boxes)
                g = R.glyph(c.page_index, sys_idx, st_idx, c.measure_index,
                            _INK_GLYPH_BASE + i)
                # ⚠️ THE OPTIONAL HALF GOES THROUGH A SPLAT AND THE REST DOES
                # NOT, AND THAT IS DELIBERATE. `wiring.py`'s DETAIL question
                # reads the AST for LITERAL keyword names, so a key passed as
                # `**detail` is invisible to it -- which is why
                # `gather_detections`' own `bbox_page_px` has never been
                # reported. Every key this reader ALWAYS writes is spelled out
                # below so the tool can say that nothing reads it, because
                # nothing does at the PER-COMPONENT grain (see
                # `benchmarks/omr-ink-gather-2026-09`; `positional_store.py`
                # is the one real consumer, and only of this `--ink-rows`
                # form). The conditional keys stay in the splat because they
                # are DECLINED by omission, which is this module's rule and
                # cannot be expressed as a literal kwarg.
                optional: Dict[str, Any] = {}
                if spacing:
                    optional.update(width_spaces=round(w / spacing, 3),
                                    height_spaces=round(h / spacing, 3),
                                    cell_staff_space_px=round(spacing, 2))
                else:
                    optional["frame_note"] = "cell has no staff-space unit"
                if page_ok:
                    px0 = cell_box[0] + x / up
                    py0 = cell_box[1] + y / up
                    px1 = cell_box[0] + (x + w) / up
                    py1 = cell_box[1] + (y + h) / up
                    optional.update(bbox_page_px=[px0, py0, px1, py1],
                                    x_center_page=(px0 + px1) / 2.0,
                                    y_center_page=(py0 + py1) / 2.0)
                else:
                    optional["frame_note"] = (
                        "no page box: cell has no bbox_page_px/upscale_factor")
                log.observe(
                    g, Q.INK, "ink", reader=READERS.CV_INK, frame=frame,
                    ink_bbox_canonical=[x, y, x + w, y + h],
                    ink_area_px=int(area),
                    ink_fill=round(area / float(w * h), 4),
                    ink_n_components=len(comps),
                    ink_share_of_cell=round(area / total_ink, 4),
                    # ⚠️ The COVERAGE, never a verdict about it. `explained_by`
                    # names the classes whose boxes overlap; it does NOT claim
                    # the component IS one of them, and on this corpus it
                    # frequently is not -- `arpeggiato` fires 98 and 86 times
                    # on two pages as "a stem or a barline".
                    ink_detector_coverage=round(cov, 4),
                    ink_explained_by=list(who),
                    **optional)
        else:
            # ⚠️⚠️ THE SUMMARY FORM (default since roadmap 1.1). One row per
            # CELL, aggregating exactly the same per-component computation
            # above rather than skipping it -- the cost is unchanged, only the
            # representation is. `ink_n_components` and `ink_largest_share`
            # answer the two things the record's real consumer (`trace.py`)
            # asks: is there ink here at all, and how merged is it. Geometry
            # (`ink_bbox_canonical`, `bbox_page_px`, `width_spaces`, …) does
            # not survive aggregation and is dropped here on purpose -- it is
            # a per-COMPONENT fact, and `--ink-rows` is how a caller that
            # needs it (`positional_store.py`) gets it back.
            explained: set = set()
            cov_max = 0.0
            largest_area = 0.0
            for (x, y, w, h, area) in comps:
                cov, who = _coverage((x, y, w, h), boxes)
                explained.update(who)
                cov_max = max(cov_max, cov)
                largest_area = max(largest_area, area)
            # ⚠️ THE FIVE MANDATORY KEYS ARE LITERAL KWARGS, NOT A SPLAT --
            # matching this module's own rule two sections up
            # (`wiring.py`'s DETAIL question reads the AST for literal
            # keyword names, so a key passed as `**detail` is invisible to
            # it). Only `cell_staff_space_px`, which is genuinely
            # CONDITIONAL on the cell having a measured grid, stays in the
            # optional splat -- the same convention the component branch
            # above uses for its own conditional keys.
            optional_summary: Dict[str, Any] = {}
            if spacing:
                optional_summary["cell_staff_space_px"] = round(spacing, 2)
            log.observe(
                sub, Q.INK, "ink", reader=READERS.CV_INK, frame=frame,
                ink_n_components=len(comps),
                ink_total_area_px=int(total_ink),
                ink_largest_share=round(largest_area / total_ink, 4),
                ink_detector_coverage_max=round(cov_max, 4),
                ink_explained_by_union=sorted(explained),
                **optional_summary)
        if progress:
            print(f"  gather ink {sub.to_key()}: {len(comps)}"
                  f"{'' if component_rows else ' (summary row)'}")


# ─────────────────────────────────────────────────────────────────────────────
# The stroke map -- every stroke of a cell, measured once (ROADMAP 2.195, step 1)
# ─────────────────────────────────────────────────────────────────────────────

#: `OMR_STROKE_MAP` -- file one `Q.STROKE` row per stroke of each cell's staff-erased ink (`stroke_map.py`). **Default ON since 2026-10-26** (Sean "2.201 land on"; an explicit
#: 0/false/no/off disables). PRODUCER ONLY: nothing reads the rows, so
#: flag on writes a byte-identical exported file.
STROKE_MAP_ENV = "OMR_STROKE_MAP"
_STROKE_GLYPH_BASE = RECORD_STROKE_GLYPH_BASE          # 375_000, record.py; past the detector's ordinals and every other gather base, BELOW `human_evidence.HUMAN_GLYPH_BASE` (400,000: a first draft sat ON it)


def stroke_map_enabled() -> bool:
    return os.environ.get(STROKE_MAP_ENV, "1").strip().lower() not in ("0", "false", "no", "off")


#: ROADMAP 2.204 (`rhythm.STEMS_FROM_STROKES_ENV`, the same name). With BOTH this and `OMR_STROKE_MAP` on, GATHER does not file
#: `Q.HEAD_STEM_REACH` (`gather_head_stem_reach`) nor `Q.STEM_TIP_INK` (`_observe_stem_tip_ink`): every ADJUDICATE reader of them reads the
#: stroke map instead, so the two scans are unreachable. Either flag off: both scans run, as before.
STEMS_FROM_STROKES_ENV = "OMR_STEMS_FROM_STROKES"


def stems_from_strokes_retires_scans() -> bool:
    return (os.environ.get(STEMS_FROM_STROKES_ENV, "0").strip().lower() in ("1", "true", "yes", "on") and stroke_map_enabled())


def gather_stroke_map(log: Log, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], *, progress: bool = False) -> Dict[Tuple[int, int, int, int], Any]:
    """ROADMAP 2.195 step 1: every stroke of every cell, one `Q.STROKE` row each. Reads the erased raster (`READERS.CV_STROKE`) and the cell's
    raw raster for the local staff; reads no row and no detection, decides nothing. A cell that cannot be reduced (no erased variant, no
    staff spacing) ABSTAINS by name; a cell that holds ink but no stroke above the 0.05 sp^2 floor (it ABSTAINS `only_debris`).

    ROADMAP 2.198: the rows are SLIMMED (bytes a page; every field a later step of the plan names is kept) and the function returns what
    `gather_glyph_strokes` / the claimed register need and the rows cannot give them -- `{(page, system, staff, cell): CellStrokes}`, or
    the abstain reason (a string) for a cell with no strokes. Empty (and nothing filed) with the flag off.

    Slimmed away, each recoverable from a row that stays: `area_sp2` (= `fill` x the box area / the local space squared),
    `component_n_strokes` (the count of the cell's rows with the same `component`), `staff_lines_left` / `staff_lines_right` (the staff
    measured at the stroke's own x -- what a consumer takes from them is `end_steps_from_top` and `staff_space_local_px`, which stay),
    `profile_sixteenths` on a blob (a blob's named fields are `fill` and `hole_share`; the profile is kept for the vertical, horizontal and
    curve strokes whose thickness a consumer smooths), `staff_local` unless False (absent = the local lines were found), and the cell-level
    `cell_n_below_floor` (filed once, on the cell's FIRST stroke row). `ends` is one flat list [x0, y0, x1, y1]."""
    cache: Dict[Tuple[int, int, int, int], Any] = {}
    if not stroke_map_enabled():
        return cache
    from . import stroke_map as SM
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        ck = (c.page_index, key[0], key[1], c.measure_index)
        frame = frame_cell(c.measure_index)
        img = getattr(c, "image_no_staff", None)
        grid = _cell_grid(c)
        if img is None or getattr(img, "ndim", 0) != 2:
            log.abstain(sub, Q.STROKE, reader=READERS.CV_STROKE, frame=frame, reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            cache[ck] = ABSTAIN.NO_MASK
            continue
        if grid is None:
            log.abstain(sub, Q.STROKE, reader=READERS.CV_STROKE, frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY)
            cache[ck] = ABSTAIN.NO_STAFF_GEOMETRY
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None))
        if res is None:
            log.abstain(sub, Q.STROKE, reader=READERS.CV_STROKE, frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY)
            cache[ck] = ABSTAIN.NO_STAFF_GEOMETRY
            continue
        if not res.strokes:
            if res.n_below_floor == 0:
                log.abstain(sub, Q.STROKE, reader=READERS.CV_STROKE, frame=frame, reason=ABSTAIN.NO_INK)
                cache[ck] = ABSTAIN.NO_INK
            else:           # ink, but every piece under the floor: said, never read as "no ink"
                log.abstain(sub, Q.STROKE, reader=READERS.CV_STROKE, frame=frame, reason=ABSTAIN.ONLY_DEBRIS,
                            n_below_floor=res.n_below_floor)
                cache[ck] = ABSTAIN.ONLY_DEBRIS
            continue
        cache[ck] = res
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        page_ok = bool(up) and bool(cell_box) and len(cell_box or ()) == 4
        for i, st in enumerate(res.strokes):
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, _STROKE_GLYPH_BASE + i)
            optional: Dict[str, Any] = {}
            if st.sagitta_sp is not None:
                optional["sagitta_spaces"] = st.sagitta_sp
            if st.hole_share is not None:
                optional["hole_share"] = st.hole_share
            if st.kind != "blob":
                optional["profile_sixteenths"] = st.profile
            if not res.staff_local:                      # absent = the staff was measured at the stroke's own x
                optional["staff_local"] = False
            if i == 0:                                   # a CELL fact, said once
                optional["cell_n_below_floor"] = res.n_below_floor
            if page_ok:
                x, y, w, h = st.box
                optional["bbox_page_px"] = [round(cell_box[0] + x / up, 1), round(cell_box[1] + y / up, 1),
                                            round(cell_box[0] + (x + w) / up, 1), round(cell_box[1] + (y + h) / up, 1)]
            else:
                optional["frame_note"] = "no page box: cell has no bbox_page_px/upscale_factor"
            log.observe(
                g, Q.STROKE, st.kind, reader=READERS.CV_STROKE, frame=frame,
                stroke_box=list(st.box), length_spaces=st.length_sp, angle_deg=st.angle_deg,
                thickness_spaces=st.thickness_sp, thickness_spread_spaces=st.thickness_spread_sp, fill=st.fill,
                ends=[st.ends[0][0], st.ends[0][1], st.ends[1][0], st.ends[1][1]], end_steps_from_top=list(st.end_steps),
                touches=[[j, ct] for j, ct in st.touches], component=st.component,
                staff_space_local_px=st.staff_space_local, **optional)
        if progress:
            print(f"  gather strokes {sub.to_key()}: {len(res.strokes)}")
    return cache


def gather_glyph_strokes(log: Log, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]],
                         stroke_cells: Dict[Tuple[int, int, int, int], Any], *, progress: bool = False) -> None:
    """ROADMAP 2.198 step 2 (flag `OMR_STROKE_MAP`, default ON), STAGED GATHER: `Q.GLYPH_STROKES`, one row per detector box of every pass
    (the plan, `docs/plan-2026-10-22-shared-ink-map.md` §2.2: a box is a hypothesis over strokes). The row's value is the list of stroke
    ordinals (of the box's own cell; the stroke `i` is the glyph subject `_STROKE_GLYPH_BASE + i` of that cell) of which at least
    `stroke_map.COVER_SHARE_MIN` of the stroke's ink lies inside the box; `shares` are those strokes' shares, `partial` the strokes with
    some ink inside and less than that. An EMPTY list is a fact (the box stands on no filed stroke: 8 of 8 wide beam boxes in 2.195's
    crops); a cell whose strokes could not be mapped ABSTAINS per box, by the cell's reason, never filed as an empty list (rule 8).
    Decides nothing, reads only `detections` and `stroke_cells`; nothing reads the rows yet."""
    if not stroke_map_enabled() or not stroke_cells:
        return
    from . import stroke_map as SM
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        res = stroke_cells.get(ck)
        if res is None:
            continue
        dets = detections.get(R.cell(*ck).to_key(), ())
        frame = frame_cell(c.measure_index)
        for gi, d in enumerate(dets):
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            if isinstance(res, str):
                log.abstain(g, Q.GLYPH_STROKES, reader=READERS.CV_GLYPH_STROKES, frame=frame, reason=res)
                continue
            got = SM.strokes_in_box(res, (d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical,
                                          d.y_canonical + d.height_canonical))
            covered = [(i, sh) for i, sh in got if sh >= SM.COVER_SHARE_MIN]
            part = [[i, sh] for i, sh in got if sh < SM.COVER_SHARE_MIN]
            extra: Dict[str, Any] = {}
            if part:
                extra["partial"] = part
            log.observe(g, Q.GLYPH_STROKES, [i for i, _sh in covered], reader=READERS.CV_GLYPH_STROKES, frame=frame,
                        shares=[sh for _i, sh in covered], cover_min=SM.COVER_SHARE_MIN, **extra)
        if progress:
            print(f"  gather glyph strokes {R.cell(*ck).to_key()}: {len(dets)} boxes")


# ─────────────────────────────────────────────────────────────────────────────
# One accidental family -- the type from the mark's own strokes (ROADMAP 2.201)
# ─────────────────────────────────────────────────────────────────────────────

#: A notehead to the right of an accidental-family mark, at most this many staff spaces away (box edge to box edge), whose centre stands within
#: `FAMILY_HEAD_DY_STEPS` half-spaces of the mark's anchor: the mark is IN-BAR (an accidental belongs to the note on its right at its step, page-facts
#: §3). A key signature's last accidental is not followed that closely by a head at its own step (the meter and the gap of the run stand between).
FAMILY_HEAD_GAP_SPACES = 1.0
FAMILY_HEAD_DY_STEPS = 1.0


def family_head_right(heads: Sequence[Any], meters: Sequence[Any], gb: Sequence[float], apos: float, top_y: float, half_step: float,
                      sp: float) -> Optional[Dict[str, float]]:
    """The head directly right of a mark (`gb` = its grown box, `apos` = its anchor's staff position), or None: the role evidence "left of a head at its
    step" (page-facts §3). None where a METER box stands in the way -- a mark followed within 1.5 spaces by a time-signature digit is the key's last
    accidental, not an in-bar one -- or where the head is not at the mark's height."""
    for m in meters:
        if gb[2] - 0.25 * sp <= m.x_canonical <= gb[2] + 1.5 * sp:
            return None
    best = None
    for h in heads:
        gap = (h.x_canonical - gb[2]) / sp
        if gap < -0.25 or gap > FAMILY_HEAD_GAP_SPACES:
            continue
        dy = abs((h.y_canonical + h.height_canonical / 2.0 - top_y) / half_step - apos)
        if dy <= FAMILY_HEAD_DY_STEPS and (best is None or gap < best["gap_spaces"]):
            best = {"gap_spaces": round(gap, 2), "dy_steps": round(dy, 2)}
    return best


def gather_accidental_family(cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]],
                             stroke_cells: Dict[Tuple[int, int, int, int], Any]) -> int:
    """ROADMAP 2.201 (flag `OMR_ACCIDENTAL_FAMILY`, default ON; needs `OMR_STROKE_MAP`), STAGED GATHER: every accidental-family box -- `accidental*`
    AND `key*`, both series, one family (Sean 2026-10-22) -- gets `d.accidental_family`: its extent grown along its own accidental-shaped strokes,
    its TYPE read from those strokes, the detector's label kept as a recorded fact, and the role evidence by position (`head_right`: the notehead
    this mark stands directly left of, if any). The consumers read it off the detection (`gather_accidental_positions`, `_gather_keysig_markers`);
    it files no row of its own -- the detail rides on the rows that use it. Returns the number of boxes measured. Decides nothing."""
    if not (_acc_family.enabled() and stroke_map_enabled() and stroke_cells):
        return 0
    from . import stroke_map as SM
    n = 0
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        res = stroke_cells.get(ck)
        if res is None or isinstance(res, str):
            continue
        dets = detections.get(R.cell(*ck).to_key(), ())
        grid = _cell_grid(c)
        if grid is None:
            continue
        top_y, half_step = grid
        sp = half_step * 2.0
        heads = [d for d in dets if getattr(d, "category", None) == "notehead"]
        meters = [d for d in dets if str(d.smufl_name).lower().startswith("timesig")]
        # a notehead box that sits ON a meter digit (the detector boxes the 8 of 6/8 as a head) is not a note: it must not make the key's last accidental in-bar
        real_heads = [h for h in heads if not any(m.x_canonical <= h.x_canonical + h.width_canonical / 2.0 <= m.x_canonical + m.width_canonical
                                                  and m.y_canonical <= h.y_canonical + h.height_canonical / 2.0 <= m.y_canonical + m.height_canonical for m in meters)]
        blocked = set()
        for h in heads:
            for i, sh in SM.strokes_in_box(res, (h.x_canonical, h.y_canonical, h.x_canonical + h.width_canonical, h.y_canonical + h.height_canonical)):
                if sh >= SM.COVER_SHARE_MIN:
                    blocked.add(i)
        for d in dets:
            if not _acc_family.is_family_class(d.smufl_name) or getattr(d, "one_ink_absorbed_by", None) is not None:
                continue
            box = (float(d.x_canonical), float(d.y_canonical), float(d.x_canonical + d.width_canonical), float(d.y_canonical + d.height_canonical))
            shares = SM.strokes_in_box(res, box)
            fam = _acc_family.family_row(d.smufl_name, box, res.strokes, shares, sp, blocked=sorted(blocked),
                                         rivals=[r[0] for r in (getattr(d, "one_ink_rivals", None) or ())])
            # the role evidence: the nearest head to the right of the (grown) mark at about its own height
            gb = fam["box"]
            frac = _acc_family.anchor_fraction(fam["type"]) or _ANCHOR_FRACTION.get(str(d.smufl_name).lower(), 0.5)
            apos = (gb[1] + (gb[3] - gb[1]) * frac - top_y) / half_step
            fam["head_right"] = family_head_right(real_heads, meters, gb, apos, top_y, half_step, sp)
            fam["anchor_fraction"] = frac
            d.accidental_family = fam
            n += 1
    return n


# ─────────────────────────────────────────────────────────────────────────────
# The staff-sized ink of a bar, with its page box -- ROADMAP 2.80
# ─────────────────────────────────────────────────────────────────────────────

#: A piece smaller than this (staff spaces SQUARED) is speckle or a staff-line
#: crumb, not a head/rest/flag. Measured on Brahms pdf 1 s0 staff 13 bar 5: the
#: halves of an eighth rest are 0.48 and 0.51, speckle 0.004. 0.10 sits in the
#: empty band between them.
INK_PIECE_MIN_AREA_SP2 = 0.10
#: A piece wider than this is a slur, a tie, a beam, a stave remnant -- never
#: one symbol of a rest's or a head's size.
INK_PIECE_MAX_WIDTH_SPACES = 8.0
#: How far above/below the outer staff lines a piece's centre may lie and
#: still be a candidate (rests stand inside the staff; heads, flags and
#: ledger notes within a space or two of it).
INK_PIECE_BAND_SPACES = 1.5


def gather_cell_ink_pieces(log: Log, cells: Sequence[Any],
                           local: Dict[int, Tuple[int, int]],
                           detections: Dict[str, List[Any]], *,
                           progress: bool = False) -> None:
    """The staff-sized pieces of ink in every cell, with their PAGE boxes.

    ⚠️ ROADMAP 2.80. `reconcile_duration` lands a bar that is short by
    lengthening a note, and a bar short by a MISSED REST looks exactly the
    same. The witness that tells them apart is whether the bar holds ink no
    standing glyph explains -- and that needs the ink's geometry, which
    `Q.INK`'s default per-cell summary does not carry and its per-piece form
    (`--ink-rows`) carries at ~115 MB a page. This files only the pieces that
    could be a head, rest or flag (see the constants), in ONE row per cell.

    ⚠️ IT DECIDES NOTHING AND NAMES NOTHING. A piece is not a mark -- staff-line
    erasure splits an eighth rest into a blob and a tail -- so no rest shape
    is tested here; the consumer subtracts what standing glyphs explain.
    ⚠️ A cell that cannot supply a page frame or a staff unit is DECLINED
    (an abstention), never defaulted: "no row" must not read as "no ink".
    """
    if not _ink_enabled():
        return
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        frame = frame_cell(c.measure_index)
        comps = _ink_components(c)
        if comps is None:
            log.abstain(sub, Q.CELL_INK_PIECES, reader=READERS.CV_INK_PIECES,
                        frame=frame, reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            continue
        grid = _cell_grid(c)
        lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        if (grid is None or len(lines) < 5 or not up
                or not cell_box or len(cell_box) != 4):
            log.abstain(sub, Q.CELL_INK_PIECES, reader=READERS.CV_INK_PIECES,
                        frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        spacing = grid[1] * 2.0
        lo = lines[0] - INK_PIECE_BAND_SPACES * spacing
        hi = lines[-1] + INK_PIECE_BAND_SPACES * spacing
        pieces = []
        for (x, y, w, h, area) in comps:
            if w <= 0 or h <= 0:
                continue
            area_sp2 = area / (spacing * spacing)
            if area_sp2 < INK_PIECE_MIN_AREA_SP2:
                continue
            if w / spacing > INK_PIECE_MAX_WIDTH_SPACES:
                continue
            if not (lo <= y + h / 2.0 <= hi):
                continue
            pieces.append([round(cell_box[0] + x / up, 1),
                           round(cell_box[1] + y / up, 1),
                           round(cell_box[0] + (x + w) / up, 1),
                           round(cell_box[1] + (y + h) / up, 1),
                           round(area_sp2, 3)])
        log.observe(sub, Q.CELL_INK_PIECES, len(pieces),
                    reader=READERS.CV_INK_PIECES, frame=frame,
                    pieces=pieces,
                    staff_space_page_px=round(spacing / up, 2))
        if progress:
            print(f"  gather ink pieces {sub.to_key()}: {len(pieces)}")


# ─────────────────────────────────────────────────────────────────────────────
# What the ink under a NARROW notehead box looks like -- ROADMAP 2.80b
# ─────────────────────────────────────────────────────────────────────────────

#: A piece joins the ink under a narrow box when it lies within this many
#: staff spaces of what is already joined (staff-line erasure splits an eighth
#: rest into a blob and a tail with a hair of gap).
NARROW_BOX_JOIN_GAP_SPACES = 0.25
#: A piece taller than this is never joined (a stem, a beam, a slur): it is
#: not a rest's tail, and joining it would grow the ink without limit.
NARROW_BOX_JOIN_MAX_HEIGHT_SPACES = 3.5


def gather_narrow_box_shape(log: Log, cells: Sequence[Any],
                            local: Dict[int, Tuple[int, int]],
                            detections: Dict[str, List[Any]], *,
                            progress: bool = False) -> None:
    """`Q.NARROW_BOX_SHAPE` on every notehead-classed box narrower than a head.

    ⚠️ ROADMAP 2.80b. Sean, tile 1 of `out/print/2.80-review/`: the narrow
    "notehead" in Brahms Contrabass bar 13 *"is an 8th note rest"*. The
    detector boxed only the blob of the rest (0.67 spaces wide) and called it
    a head. This measures what that box's INK is -- the connected pieces it
    overlaps and the pieces stacked against them, in staff spaces, with the
    staff step of its centre (ruler, bottom line = 0) and the other
    detections that overlap it -- and names nothing. The domain is the narrow
    boxes only (`notehead_precision.TOO_NARROW_MIN_SPACES`, imported), so the
    record grows by a few rows a page, not one per head.

    ⚠️ NO BAR IS READ HERE OR BY THE DECISION THAT CONSUMES THIS ROW.
    ⚠️ DECLINED, NOT DEFAULTED: no raster, staff unit or page frame is an
    abstention, never a row that looks like "no ink".
    """
    if not _ink_enabled():
        return
    from .adjudicators.notehead_precision import TOO_NARROW_MIN_SPACES
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        narrow = []
        grid = _cell_grid(c)
        space = grid[1] * 2.0 if grid and grid[1] else None
        for gi, d in enumerate(dets):
            if not str(d.smufl_name).lower().startswith("notehead"):
                continue
            if space and d.width_canonical / space < TOO_NARROW_MIN_SPACES:
                narrow.append(gi)
        if not narrow:
            continue
        frame = frame_cell(c.measure_index)
        comps = _ink_components(c)
        lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        img = getattr(c, "image_no_staff", None)
        width_px = getattr(img, "shape", (0, 0))[1] if img is not None else 0
        for gi in narrow:
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            if comps is None:
                log.abstain(g, Q.NARROW_BOX_SHAPE,
                            reader=READERS.CV_NARROW_BOX_SHAPE, frame=frame,
                            reason=ABSTAIN.NO_MASK,
                            note="cell carries no image_no_staff")
                continue
            if (not space or len(lines) < 5 or not up or not cell_box
                    or len(cell_box) != 4):
                log.abstain(g, Q.NARROW_BOX_SHAPE,
                            reader=READERS.CV_NARROW_BOX_SHAPE, frame=frame,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY)
                continue
            d = dets[gi]
            bx0, by0 = float(d.x_canonical), float(d.y_canonical)
            bx1 = bx0 + float(d.width_canonical)
            by1 = by0 + float(d.height_canonical)

            def overlaps(x, y, w, h):
                return (min(x + w, bx1) - max(x, bx0) > 0
                        and min(y + h, by1) - max(y, by0) > 0)

            # ⚠️ NO RESIDUE: a piece wider than any rest/head or taller than a
            # tail can be (a staff-erasure remnant that merged a whole bar
            # into one component) is not a seed either -- measured on Brahms
            # p1 s0 bar 13, where one 22 x 8 space component under the box
            # swallowed every other mark of the bar.
            usable = [cm for cm in comps
                      if cm[4] / (space * space) >= INK_PIECE_MIN_AREA_SP2
                      and cm[2] / space <= INK_PIECE_MAX_WIDTH_SPACES
                      and cm[3] / space <= NARROW_BOX_JOIN_MAX_HEIGHT_SPACES]
            joined = [cm for cm in usable
                      if overlaps(cm[0], cm[1], cm[2], cm[3])]
            grew = bool(joined)
            gap = NARROW_BOX_JOIN_GAP_SPACES * space
            while grew:
                grew = False
                ux0 = min(q[0] for q in joined)
                uy0 = min(q[1] for q in joined)
                ux1 = max(q[0] + q[2] for q in joined)
                uy1 = max(q[1] + q[3] for q in joined)
                for cm in usable:
                    if cm in joined or                             cm[3] / space > NARROW_BOX_JOIN_MAX_HEIGHT_SPACES:
                        continue
                    gx = max(0.0, max(cm[0], ux0) - min(cm[0] + cm[2], ux1))
                    gy = max(0.0, max(cm[1], uy0) - min(cm[1] + cm[3], uy1))
                    if gx <= gap and gy <= gap:
                        joined.append(cm)
                        grew = True
            if not joined:
                log.observe(g, Q.NARROW_BOX_SHAPE, 0.0,
                            reader=READERS.CV_NARROW_BOX_SHAPE, frame=frame,
                            n_pieces=0)
                continue
            ux0 = min(q[0] for q in joined)
            uy0 = min(q[1] for q in joined)
            ux1 = max(q[0] + q[2] for q in joined)
            uy1 = max(q[1] + q[3] for q in joined)
            step = (lines[-1] - (uy0 + uy1) / 2.0) / (space / 2.0)
            area = float(sum(q[4] for q in joined))
            others = []
            for oi, od in enumerate(dets):
                if oi == gi:
                    continue
                ox0, oy0 = float(od.x_canonical), float(od.y_canonical)
                ox1 = ox0 + float(od.width_canonical)
                oy1 = oy0 + float(od.height_canonical)
                if (ox1 - ox0) / space > 8.0:
                    continue                       # a staff / slur rectangle
                ix = min(ux1, ox1) - max(ux0, ox0)
                iy = min(uy1, oy1) - max(uy0, oy0)
                if ix > 0 and iy > 0 and ix * iy >= 0.3 * min(
                        (ux1 - ux0) * (uy1 - uy0), (ox1 - ox0) * (oy1 - oy0)):
                    others.append({"glyph": oi, "class": str(od.smufl_name)})
            log.observe(
                g, Q.NARROW_BOX_SHAPE, round((uy1 - uy0) / space, 3),
                reader=READERS.CV_NARROW_BOX_SHAPE, frame=frame,
                n_pieces=len(joined),
                width_spaces=round((ux1 - ux0) / space, 3),
                height_spaces=round((uy1 - uy0) / space, 3),
                staff_step=round(step, 3),
                fill=round(area / float((ux1 - ux0) * (uy1 - uy0)), 3),
                touches_cell_edge=bool(
                    ux0 <= 2 or (width_px and ux1 >= width_px - 2)),
                overlapping_detections=others,
                bbox_page_px=[round(cell_box[0] + ux0 / up, 1),
                              round(cell_box[1] + uy0 / up, 1),
                              round(cell_box[0] + ux1 / up, 1),
                              round(cell_box[1] + uy1 / up, 1)])
            if progress:
                print(f"  gather narrow-box shape {g.to_key()}")


# ─────────────────────────────────────────────────────────────────────────────
# Does a rest box's ink run on into a head? -- ROADMAP 2.150b
# ─────────────────────────────────────────────────────────────────────────────

_REST_CLASS_PREFIX = "rest"


def gather_rest_ink_contact(log: Log, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                            detections: Dict[str, List[Any]], *, progress: bool = False) -> None:
    """`Q.REST_INK_CONTACT` on every rest-classed box, off the staff-erased raster (`rest_ink.measure`).

    Sean, 2026-10-16: "a rest box whose stroke runs on into a notehead is a stem; a real rest stands free". This
    only MEASURES (thin stroke length, solid blob length, ink of the dominant piece in a standing head's box outside
    the rest box); `family_precision._rest_stroke_into_head_refusal` weighs it. Filed only while the flag is ON.
    ⚠️ It reads `image_no_staff`, NOT `Q.STEM`: `refuse_owned` deletes the strokes inside a rest box before
    `Q.STEM` exists, so a stem boxed as a rest has no stem row.
    ⚠️ DECLINED, NOT DEFAULTED: no raster, staff unit or page frame is an abstention, never "no contact".
    """
    from . import rest_ink
    if not rest_ink.enabled():
        return
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        rests = [gi for gi, d in enumerate(dets) if str(d.smufl_name).lower().startswith(_REST_CLASS_PREFIX)]
        if not rests:
            continue
        frame = frame_cell(c.measure_index)
        grid = _cell_grid(c)
        space = grid[1] * 2.0 if grid and grid[1] else None
        img = getattr(c, "image_no_staff", None)
        for gi in rests:
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            if img is None or getattr(img, "ndim", 0) != 2:
                log.abstain(g, Q.REST_INK_CONTACT, reader=READERS.CV_REST_INK_CONTACT, frame=frame,
                            reason=ABSTAIN.NO_MASK, note="cell carries no image_no_staff")
                continue
            if not space:
                log.abstain(g, Q.REST_INK_CONTACT, reader=READERS.CV_REST_INK_CONTACT, frame=frame,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY)
                continue
            d = dets[gi]
            box = (float(d.x_canonical), float(d.y_canonical),
                   float(d.x_canonical) + float(d.width_canonical), float(d.y_canonical) + float(d.height_canonical))
            heads = [(oi, str(od.smufl_name), float(od.x_canonical), float(od.y_canonical),
                      float(od.x_canonical) + float(od.width_canonical),
                      float(od.y_canonical) + float(od.height_canonical))
                     for oi, od in enumerate(dets)
                     if oi != gi and str(od.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)]
            got = rest_ink.measure(img == 0, box, heads, space)
            if got is None:
                log.abstain(g, Q.REST_INK_CONTACT, reader=READERS.CV_REST_INK_CONTACT, frame=frame,
                            reason=ABSTAIN.NO_MASK, note="no ink under the box, or the box is off the raster")
                continue
            log.observe(g, Q.REST_INK_CONTACT, got["thin_run_sp"], reader=READERS.CV_REST_INK_CONTACT, frame=frame,
                        **{k: v for k, v in got.items()})
            if progress:
                print(f"  gather rest ink contact {g.to_key()}")


# ─────────────────────────────────────────────────────────────────────────────
# Does a head box at a bar's left edge hold a head-shaped oval? -- ROADMAP 2.164
# ─────────────────────────────────────────────────────────────────────────────

def gather_head_oval(log: Log, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                     detections: Dict[str, List[Any]], *, progress: bool = False) -> None:
    """`Q.HEAD_OVAL` on every notehead-classed box that starts within `head_oval.LEFT_EDGE_SPACES` of its bar's left
    edge, off the PAGE raster (`pws.page.binary`, staff lines in; `head_oval.oval_width` leaves bare line rows out).

    Sean, 2026-10-17 (ROADMAP 2.164): head boxes at a bar's left edge are "almost entirely tie ends ... or a bar
    line". The detector reads one bar's crop at a time, so a tie crossing the barline is cut there and its tail is
    boxed as a head. This only MEASURES whether the box holds head-tall ink across a head's width;
    `notehead_precision._arc_tail_refusal` weighs it with the arc the previous bar's crop cut. Filed only while the
    flag is ON. ⚠️ The PAGE raster, not the cell's: the tail runs to the crop edge, and the box may sit on it.
    ⚠️ DECLINED, NOT DEFAULTED: no raster, staff unit or page frame is an abstention, never "no oval".
    """
    from . import head_oval
    if not head_oval.enabled():
        return
    page_binary = getattr(getattr(pws, "page", None), "binary", None)
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        heads = [gi for gi, d in enumerate(dets) if str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)]
        if not heads:
            continue
        frame = frame_cell(c.measure_index)
        grid = _cell_grid(c)
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        space_page = (grid[1] * 2.0 / float(up)) if grid and grid[1] and up else None
        for gi in heads:
            page_box = _page_box(c, dets[gi])
            if page_box is None or not cell_box or len(cell_box) != 4 or not space_page:
                continue
            if not head_oval.box_at_left_edge(page_box, cell_box, space_page):
                continue
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            got = head_oval.oval_width(page_binary, page_box, space_page) if page_binary is not None else None
            if got is None:
                log.abstain(g, Q.HEAD_OVAL, reader=READERS.CV_HEAD_OVAL, frame=frame, reason=ABSTAIN.NO_MASK,
                            note="no page raster, or the box is off it")
                continue
            log.observe(g, Q.HEAD_OVAL, got["oval_width_sp"], reader=READERS.CV_HEAD_OVAL, frame=frame,
                        left_gap_sp=round((float(page_box[0]) - float(cell_box[0])) / space_page, 3),
                        space_page_px=round(space_page, 3), **{k: v for k, v in got.items()})
            if progress:
                print(f"  gather head oval {g.to_key()}")


# ─────────────────────────────────────────────────────────────────────────────
# Rest-sized ink the detector never boxed -- ROADMAP 2.99
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️ Glyph indices for unboxed-rest clusters, past the detector's ordinals,
#: `_CV_GLYPH_BASE` (100k), `_INK_GLYPH_BASE` (200k) and
#: `_VERTICAL_RUN_GLYPH_BASE` (300k) and BELOW the human-evidence base (400k):
#: `test_stage_review_evidence` holds every gather base under it (the first
#: draft used 400k and failed there). A collision would not raise; it would
#: merge a cluster row into some other reader's subject.
_UNBOXED_REST_GLYPH_BASE = 350_000

#: The window a cluster must fall in to be a CANDIDATE (staff spaces). An
#: eighth rest measures 1.2-1.4 x 1.9-2.4 and a quarter rest about 1 x 2.6-3,
#: a head is ~1.3 x 1, a stem-and-head or a beam group is far taller or wider.
#: Wider than the decision's own windows on purpose: the decision, not the
#: gather, says what is NOT a rest.
UNBOXED_REST_WIDTH_SPACES = (0.5, 2.4)
UNBOXED_REST_HEIGHT_SPACES = (1.2, 3.8)
#: A candidate's centre lies between these staff steps (bottom line = 0, top
#: line = 8). A rest hangs in the middle of the staff; anything found past the
#: outer lines is a letter, a dynamic or a ledger note.
UNBOXED_REST_STEP_RANGE = (1.0, 7.0)
#: How far right of a cluster a notehead is still reported as its neighbour.
UNBOXED_REST_NEIGHBOUR_SPACES = 3.0
UNBOXED_REST_HEADER_PREFIXES = ("gclef", "fclef", "cclef", "clef", "keysig",
                                "timesig")


def gather_unboxed_rest_ink(log: Log, cells: Sequence[Any],
                            local: Dict[int, Tuple[int, int]],
                            detections: Dict[str, List[Any]], *,
                            progress: bool = False) -> None:
    """`Q.UNBOXED_REST_SHAPE` on every rest-sized cluster of staff-erased ink.

    ⚠️ ROADMAP 2.99 (2.96's third item: 448 held bars hold eighth/quarter-rest
    shaped ink no box accounts for). CLAUDE.md §9: *a box the detector never
    drew has no subject* -- `gather_narrow_box_shape` (2.80b) starts from a box
    it DID draw and refused, and 2.52 only searches a bar with no box at all.
    This is the third population: ink in a bar that has other boxes, none of
    them over this.

    It clusters the cell's staff-sized pieces across the hair of gap staff-line
    erasure leaves (an eighth rest is a blob and a tail), keeps the clusters in
    a rest's size window, and MEASURES each: width, height, the local staff
    step of its centre, the detector coverage and which classes cover it, the
    share of its height one pixel column fills (a flat or sharp is a stem with
    a bowl; a rest has no vertical stroke), and the nearest notehead to its
    right (an accidental stands just left of its head). The COVERED clusters
    are filed too, on purpose: a standing rest box over its own ink is the
    positive control and a standing accidental box is the negative one, so the
    decision's windows are read off ink the detector already named.

    ⚠️ IT NAMES NOTHING AND CONSULTS NO BAR. CLAUDE.md §10: two witnesses off
    one raster fall silent together, and a bar's sum is built from the same
    reading the missing mark was lost from.
    ⚠️ DECLINED, NOT DEFAULTED: no raster, staff unit or page frame is an
    abstention, never a row that looks like "no ink".
    """
    if not _ink_enabled():
        return
    import numpy as np
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        frame = frame_cell(c.measure_index)
        comps = _ink_components(c)
        grid = _cell_grid(c)
        space = grid[1] * 2.0 if grid and grid[1] else None
        lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        img = getattr(c, "image_no_staff", None)
        if comps is None:
            log.abstain(sub, Q.UNBOXED_REST_SHAPE,
                        reader=READERS.CV_UNBOXED_REST_SHAPE, frame=frame,
                        reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            continue
        if (not space or len(lines) < 5 or not up or not cell_box
                or len(cell_box) != 4):
            log.abstain(sub, Q.UNBOXED_REST_SHAPE,
                        reader=READERS.CV_UNBOXED_REST_SHAPE, frame=frame,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        width_px = getattr(img, "shape", (0, 0))[1]
        usable = [cm for cm in comps
                  if cm[4] / (space * space) >= INK_PIECE_MIN_AREA_SP2
                  and cm[2] / space <= INK_PIECE_MAX_WIDTH_SPACES
                  and cm[3] / space <= NARROW_BOX_JOIN_MAX_HEIGHT_SPACES]
        gap = NARROW_BOX_JOIN_GAP_SPACES * space
        explainers = _explaining_detections(dets, space)
        header_right = 0.0
        for d in dets:
            if str(d.smufl_name).lower().startswith(
                    UNBOXED_REST_HEADER_PREFIXES):
                header_right = max(header_right, float(d.x_canonical)
                                   + float(d.width_canonical))
        seen = [False] * len(usable)
        ordinal = 0
        for i0 in range(len(usable)):
            if seen[i0]:
                continue
            seen[i0] = True
            joined = [usable[i0]]
            grew = True
            while grew:
                grew = False
                ux0 = min(q[0] for q in joined)
                uy0 = min(q[1] for q in joined)
                ux1 = max(q[0] + q[2] for q in joined)
                uy1 = max(q[1] + q[3] for q in joined)
                for j, cm in enumerate(usable):
                    if seen[j]:
                        continue
                    gx = max(0.0, max(cm[0], ux0) - min(cm[0] + cm[2], ux1))
                    gy = max(0.0, max(cm[1], uy0) - min(cm[1] + cm[3], uy1))
                    if gx <= gap and gy <= gap:
                        seen[j] = True
                        joined.append(cm)
                        grew = True
            ux0 = min(q[0] for q in joined)
            uy0 = min(q[1] for q in joined)
            ux1 = max(q[0] + q[2] for q in joined)
            uy1 = max(q[1] + q[3] for q in joined)
            w_sp, h_sp = (ux1 - ux0) / space, (uy1 - uy0) / space
            if not (UNBOXED_REST_WIDTH_SPACES[0] <= w_sp
                    <= UNBOXED_REST_WIDTH_SPACES[1]
                    and UNBOXED_REST_HEIGHT_SPACES[0] <= h_sp
                    <= UNBOXED_REST_HEIGHT_SPACES[1]):
                continue
            cy = (uy0 + uy1) / 2.0
            step = (lines[-1] - cy) / (space / 2.0)
            if not (UNBOXED_REST_STEP_RANGE[0] <= step
                    <= UNBOXED_REST_STEP_RANGE[1]):
                continue
            box = (int(ux0), int(uy0), int(ux1 - ux0), int(uy1 - uy0))
            cover, who = _coverage(box, explainers)
            crop = (img[int(uy0):int(uy1), int(ux0):int(ux1)] == 0) \
                if img is not None else None
            max_col = mass_y = fill = profile = None
            if crop is not None and crop.size and crop.sum() > 0:
                colfrac = crop.sum(axis=0) / float(crop.shape[0])
                max_col = round(float(colfrac.max()), 3)
                ys, xs = np.nonzero(crop)
                mass_y = round(float(ys.mean()) / crop.shape[0], 3)
                nb = 6
                edges = np.linspace(0, crop.shape[1], nb + 1).astype(int)
                profile = [round(float(colfrac[edges[i]:max(edges[i] + 1,
                                                            edges[i + 1])]
                                       .max()), 2) for i in range(nb)]
                fill = round(float(crop.sum()) / crop.size, 3)
            head = None
            for d in dets:
                if not str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX):
                    continue
                dx = (float(d.x_canonical) - ux1) / space
                if dx < -0.3 or dx > UNBOXED_REST_NEIGHBOUR_SPACES:
                    continue
                dy = (float(d.y_canonical) + float(d.height_canonical) / 2.0
                      - cy) / space
                if head is None or dx < head["dx_spaces"]:
                    head = {"class": str(d.smufl_name),
                            "dx_spaces": round(dx, 3),
                            "dy_spaces": round(dy, 3)}
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index,
                        _UNBOXED_REST_GLYPH_BASE + ordinal)
            ordinal += 1
            log.observe(
                g, Q.UNBOXED_REST_SHAPE, round(h_sp, 3),
                reader=READERS.CV_UNBOXED_REST_SHAPE, frame=frame,
                n_pieces=len(joined), width_spaces=round(w_sp, 3),
                height_spaces=round(h_sp, 3), staff_step=round(step, 3),
                fill=fill, max_column_share=max_col, mass_y=mass_y,
                column_profile=profile, coverage=round(cover, 3),
                covered_by=list(who), right_head=head,
                first_cell=(c.measure_index == 0),
                left_of_header=bool(header_right and ux0 < header_right),
                header_known=bool(header_right),
                touches_cell_edge=bool(
                    ux0 <= 2 or (width_px and ux1 >= width_px - 2)),
                bbox_canonical=[int(ux0), int(uy0), int(ux1), int(uy1)],
                bbox_page_px=[round(cell_box[0] + ux0 / up, 1),
                              round(cell_box[1] + uy0 / up, 1),
                              round(cell_box[0] + ux1 / up, 1),
                              round(cell_box[1] + uy1 / up, 1)])
            if progress:
                print(f"  gather unboxed-rest ink {g.to_key()}")


# ─────────────────────────────────────────────────────────────────────────────
# A targeted search for a whole rest the detector never boxed -- ROADMAP 2.52
# ─────────────────────────────────────────────────────────────────────────────

#: Fraction of a bar's own width searched FIRST. Sean/DECISIONS 2026-10-01:
#: "look in the middle of the bar first" -- a whole rest is centred in the
#: bar, so the middle third is where the engraving puts it; `_widened`
#: below covers the rest of the bar's interior only if nothing is found here.
EMPTY_BAR_MIDDLE_FRACTION: Tuple[float, float] = (1.0 / 3.0, 2.0 / 3.0)


def _empty_bar_candidate_cells(
        cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
        detections: Dict[str, List[Any]]) -> List[Any]:
    """Every cell with NO notehead- or rest-class detection box at all --
    not one refused, one never drawn. `Q.REST` and the notehead-class rows
    both start from a detector box in this bar; this search exists for the
    population neither of them can see (CLAUDE.md §9: "a box it never drew
    has no subject")."""
    out = []
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        if any(str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)
               or str(d.smufl_name).lower().startswith(_REST_PREFIX)
               for d in dets):
            continue
        out.append(c)
    return out


def gather_empty_bar_rest_search(log: Log, cells: Sequence[Any],
                                 local: Dict[int, Tuple[int, int]],
                                 detections: Dict[str, List[Any]], *,
                                 progress: bool = False) -> None:
    """A targeted ink search, in a bar with no notehead/rest box at all, for
    a whole rest the detector never drew.

    ⚠️⚠️ SEAN / DECISIONS 2026-10-01: *"If a bar has no notes it should
    expect to find a whole note rest and look in the middle of the bar
    first. If it finds it then the bar is complete."* The unboxed-ink lane
    (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §14,
    `out/print/2.51/litolff-p3-uncovered-contact-sheet.png`) found ~3
    whole-rest-shaped blobs with NO detector box at all on Litolff p3 --
    invisible to `Q.REST`, `Q.NOTEHEAD_IS_A_WHOLE_REST` and `size_measure_
    rest` alike, because every one of them starts from a box the detector
    drew. This reader does not wait for a box: it re-measures the cell's own
    connected components directly, exactly as `gather_ink`'s
    `_ink_components` does, over `cell.image_no_staff` (the staff-erased
    canonical raster).

    ⚠️ LOCAL, NOT GLOBAL (CLAUDE.md §10: *"anything that uses geometry
    compared to the staff needs to be measuring locally"*). The shape and
    position test below reads `cell.staff_line_ys_canonical` -- the SAME
    per-cell, locally-corrected line positions `_cell_grid` already exposes
    to every other canonical-frame reader (`OMR_CELL_LINE_TRACE`, ON by
    default since 2026-09-04) -- never the page-wide `Q.STAFF_LINES` row a
    scanned staff's tilt and bow can put a half-step off at this bar's own x.

    ⚠️ THE SHAPE TEST IS IMPORTED, NOT RESTATED. `adjudicators.rhythm.
    _rest_shaped` / `WHOLE_REST_INK_MAX_HEIGHT_SPACES` / `_MIN_ASPECT` /
    `_MAX_ASPECT` already measure "is this ink the size and proportion of a
    whole rest" for `Q.NOTEHEAD_IS_A_WHOLE_REST`, in staff-space ratios --
    frame-independent, so the same test applies unchanged to a canonical-
    frame component. `WHOLE_REST_STEP` / `_STEP_TOLERANCE` (hangs under the
    4th line from the bottom) are imported the same way; `HALF_REST_STEP` /
    `REST_SLOT_TOLERANCE_HALF` are imported too, as the GUARD against the
    other filled rest shape this search must not confuse: a half rest sits
    ON the 3rd line (the middle line), not hanging under the 4th, and is
    excluded before the whole-rest position test ever sees it.

    ⚠️ MIDDLE FIRST, THEN THE WHOLE BAR'S INTERIOR. A measure cell carries no
    horizontal padding (`measure_extractor` cuts it at the adjacent
    barlines), so "the bar" and "the cell's own canonical width" are the
    same quantity. `EMPTY_BAR_MIDDLE_FRACTION` is searched first and a match
    there is `witness="middle"`; only if nothing in the middle third
    matches is the rest of the bar's interior searched, `witness="widened"`.

    ⚠️ IT DECIDES NOTHING. `found=True`/`False` is this reader's own test
    result, not a verdict about what the bar IS --
    `adjudicate_empty_bar_whole_rest` (ADJUDICATE) is what turns a match
    into "this bar is a whole-bar rest" and a miss into "this bar stays
    unread" (CLAUDE.md §2 rule 8: a fallback never converts "cannot tell"
    into an answer).
    """
    if not _ink_enabled():
        return
    from .adjudicators import rhythm as _rhythm

    for c in _empty_bar_candidate_cells(cells, local, detections):
        key = local[c.staff_index]
        sys_idx, st_idx = key
        sub = R.cell(c.page_index, sys_idx, st_idx, c.measure_index)
        frame = frame_cell(c.measure_index)

        comps = _ink_components(c)
        if comps is None:
            log.abstain(sub, Q.EMPTY_BAR_REST_SEARCH,
                        reader=READERS.CV_REST_SEARCH, frame=frame,
                        reason=ABSTAIN.NO_MASK,
                        note="cell carries no image_no_staff")
            continue

        lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
        grid = _cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        width_px = getattr(img, "shape", (0, 0))[1] if img is not None else 0
        if len(lines) < 5 or grid is None or width_px <= 0:
            log.abstain(sub, Q.EMPTY_BAR_REST_SEARCH,
                        reader=READERS.CV_REST_SEARCH, frame=frame,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        _top_y, half_step = grid
        bottom_line = lines[-1]
        target_line = lines[1]  # 4th line from the bottom, 2nd from the top

        if not comps:
            log.observe(sub, Q.EMPTY_BAR_REST_SEARCH, False,
                        reader=READERS.CV_REST_SEARCH, frame=frame,
                        found=False, reason="no_ink", bar_width_px=width_px)
            continue

        def step_of(y_center: float) -> float:
            return (bottom_line - y_center) / half_step

        mid_lo = width_px * EMPTY_BAR_MIDDLE_FRACTION[0]
        mid_hi = width_px * EMPTY_BAR_MIDDLE_FRACTION[1]

        candidates = []  # (deviation, witness, component, detail)
        for (x, y, w, h, _area) in comps:
            if w <= 0 or h <= 0:
                continue
            spacing = half_step * 2.0
            width_spaces = w / spacing
            height_spaces = h / spacing
            aspect = width_spaces / height_spaces
            x_center = x + w / 2.0
            y_center = y + h / 2.0
            step = step_of(y_center)

            if not _rhythm._rest_shaped(height_spaces, aspect):
                continue
            # ⚠️ THE HALF-REST GUARD, BEFORE THE WHOLE-REST POSITION TEST.
            # A half rest sits ON the 3rd line (the middle line) -- closer
            # to `HALF_REST_STEP` than to `WHOLE_REST_STEP` -- and must not
            # be read as a whole rest one line away.
            dev_whole = abs(step - _rhythm.WHOLE_REST_STEP)
            dev_half = abs(step - _rhythm.HALF_REST_STEP)
            if (dev_half <= _rhythm.REST_SLOT_TOLERANCE_HALF
                    and dev_half < dev_whole):
                continue
            if dev_whole > _rhythm.WHOLE_REST_STEP_TOLERANCE:
                continue

            witness = ("middle" if mid_lo <= x_center <= mid_hi
                       else "widened")
            detail = {
                "ink_bbox_canonical": [x, y, x + w, y + h],
                "width_spaces": round(width_spaces, 3),
                "height_spaces": round(height_spaces, 3),
                "staff_step": round(step, 3),
                "target_line_canonical_y": round(target_line, 2),
                "witness": witness,
            }
            candidates.append((dev_whole, witness, detail))

        middle_hits = [c for c in candidates if c[1] == "middle"]
        pool = middle_hits or candidates
        if not pool:
            log.observe(sub, Q.EMPTY_BAR_REST_SEARCH, False,
                        reader=READERS.CV_REST_SEARCH, frame=frame,
                        found=False, reason="not_rest_shaped_or_positioned",
                        bar_width_px=width_px, n_components=len(comps))
            continue

        pool.sort(key=lambda t: t[0])
        _dev, witness, detail = pool[0]
        # ⚠️ PAGE-FRAME BOX, SAME DERIVATION `gather_ink`'s per-component
        # branch uses -- so a crop pass can draw the found box without a
        # second canonical-to-page conversion living in two places.
        up = getattr(c, "upscale_factor", None)
        cell_box = getattr(c, "bbox_page_px", None)
        if up and cell_box and len(cell_box) == 4:
            x0, y0, x1, y1 = detail["ink_bbox_canonical"]
            detail["bbox_page_px"] = [cell_box[0] + x0 / up,
                                      cell_box[1] + y0 / up,
                                      cell_box[0] + x1 / up,
                                      cell_box[1] + y1 / up]
        log.observe(sub, Q.EMPTY_BAR_REST_SEARCH, True,
                    reader=READERS.CV_REST_SEARCH, frame=frame,
                    found=True, bar_width_px=width_px, **detail)
        if progress:
            print(f"  gather empty-bar rest search {sub.to_key()}: "
                  f"found ({witness})")


#: ⚠️ THE WINDOW IS A NOTEHEAD, (width, height) in STAFF SPACES. 1.3 is the
#: notehead width `notehead_precision` measured (the width floor costs 0 of
#: 103 confirmed heads -- CLAUDE.md §10); 1.0 is one space, a head's height.
LEDGER_INK_WINDOW_SPACES = (1.3, 1.0)
#: Where a head can stand relative to its rung, in spaces (+ = down the
#: raster): ON it (the rung through its middle) or hanging HALF A SPACE
#: above or below it (the head in the space beside the rung).
LEDGER_INK_OFFSETS_SPACES = (("on", 0.0), ("above", -0.5), ("below", 0.5))
#: The BACKGROUND control: the same window one full space away, both sides.
LEDGER_INK_BACKGROUND_SPACES = (-1.0, 1.0)
#: ⚠️ THE RUNG'S OWN STROKE: the box's rows, padded by this many spaces each
#: side, across the WHOLE window width -- a rung is a horizontal stroke wider
#: than any head, and a detector box drawn a pixel short of its ink would
#: otherwise let every rung vouch for itself.
LEDGER_INK_STROKE_PAD_SPACES = 0.1


def ledger_ink_under(img: Any, box: Tuple[float, float, float, float],
                     space: float) -> Optional[Dict[str, Any]]:
    """The ink under one rung, in the cell's own units. ROADMAP 3.4g-3.

    `img` is a cell raster with 0 = ink (the staff-ERASED one in GATHER),
    `box` the rung's `(x, y, w, h)` in that raster's frame, `space` one staff
    space in its pixels. Returns `None` without a unit -- declined, never
    defaulted.

    Every window is a notehead (`LEDGER_INK_WINDOW_SPACES`) centred on the
    rung's centre x; the rung's stroke rows (`LEDGER_INK_STROKE_PAD_SPACES`)
    are removed from both the ink count AND the area, so a fraction is "of
    the paper that is not the rung". A window clipped by the raster's edge
    is measured over what remains of it; one with nothing left reads `None`.

      `under`          the best of the three head windows (`on`, `above`,
                       `below`) -- the value GATHER files
      `windows`        all three
      `background`     the SMALLER of the two windows one full space above
                       and below: the paper beside the rung. The smaller,
                       because one side of a first rung is the staff (erased,
                       but a chord's note may stand there) and one side of an
                       inner rung is the next rung and its note.
      `background_windows`  both
    """
    import numpy as np
    if img is None or getattr(img, "ndim", 0) != 2 or not space \
            or space <= 0:
        return None
    ink = (img == 0)
    H, W = ink.shape
    x, y, w, h = (float(v) for v in box)
    cx, cy = x + w / 2.0, y + h / 2.0
    ww, wh = (LEDGER_INK_WINDOW_SPACES[0] * space,
              LEDGER_INK_WINDOW_SPACES[1] * space)
    pad = LEDGER_INK_STROKE_PAD_SPACES * space
    s0 = int(np.floor(y - pad))
    s1 = int(np.ceil(y + h + pad))

    def frac(dy_spaces: float) -> Optional[float]:
        yc = cy + dy_spaces * space
        x0 = max(0, int(round(cx - ww / 2.0)))
        x1 = min(W, int(round(cx + ww / 2.0)))
        y0 = max(0, int(round(yc - wh / 2.0)))
        y1 = min(H, int(round(yc + wh / 2.0)))
        if x1 <= x0 or y1 <= y0:
            return None
        rows = np.arange(y0, y1)
        keep = (rows < s0) | (rows >= s1)
        if not keep.any():
            return None
        region = ink[y0:y1, x0:x1][keep]
        return float(region.sum()) / float(region.size)

    windows = {name: frac(dy) for name, dy in LEDGER_INK_OFFSETS_SPACES}
    back = {f"{dy:+.1f}": frac(dy) for dy in LEDGER_INK_BACKGROUND_SPACES}
    measured = {k: v for k, v in windows.items() if v is not None}
    if not measured:
        return None
    best = max(measured, key=lambda k: measured[k])
    bvals = [v for v in back.values() if v is not None]
    return {
        "under": round(measured[best], 4),
        "best_window": best,
        "windows": {k: (None if v is None else round(v, 4))
                    for k, v in windows.items()},
        "background": None if not bvals else round(min(bvals), 4),
        "background_windows": {k: (None if v is None else round(v, 4))
                               for k, v in back.items()},
    }


def gather_ledger_ink(log: Log, cells: Sequence[Any],
                      local: Dict[int, Tuple[int, int]],
                      detections: Dict[str, List[Any]]) -> None:
    """`Q.LEDGER_INK_UNDER` on every `ledgerLine` glyph. ROADMAP 3.4g-3.

    ⚠️ THE SECOND WITNESS FOR `[C91]`, AND IT HAS TO BE GATHERED. Sean's
    convention -- a rung exists only where a note stands on it -- was read in
    ADJUDICATE off the detector's notehead boxes alone, and on a merging
    plate the heads the detector loses are precisely the ones fused with
    their rungs (his crops 1 and 3, 2026-09-27). The raster is gone by
    ADJUDICATE, so the paper has to be read here or not at all.

    ⚠️ OFF THE ERASED RASTER, beside `gather_ink` and for its reason: with
    the staff lines in, a window near the staff reads the line, not a head.
    CLAUDE.md §9 -- erase for the CV consumer, never for the detector; this
    is a CV consumer.

    ⚠️ A MEASUREMENT, FILED ON THE GLYPH, NAMING NOTHING. The thresholds
    that read it live in the decision (`family_precision`), measured.
    Declined, never defaulted: no erased raster -> `no_mask`; no staff unit
    -> `no_staff_geometry`.
    """
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        idx = [gi for gi, d in enumerate(dets)
               if d.smufl_name == _LEDGER_CLASS]
        if not idx:
            continue
        frame = frame_cell(c.measure_index)
        img = getattr(c, "image_no_staff", None)
        grid = _cell_grid(c)
        space = grid[1] * 2.0 if grid else None
        for gi in idx:
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            if img is None or getattr(img, "ndim", 0) != 2:
                log.abstain(g, Q.LEDGER_INK_UNDER, reader=READERS.CV_INK,
                            frame=frame, reason=ABSTAIN.NO_MASK,
                            note="cell carries no image_no_staff")
                continue
            if not space:
                log.abstain(g, Q.LEDGER_INK_UNDER, reader=READERS.CV_INK,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY)
                continue
            d = dets[gi]
            m = ledger_ink_under(img, (d.x_canonical, d.y_canonical,
                                       d.width_canonical,
                                       d.height_canonical), space)
            if m is None:
                log.abstain(g, Q.LEDGER_INK_UNDER, reader=READERS.CV_INK,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="window off the raster")
                continue
            log.observe(g, Q.LEDGER_INK_UNDER, m["under"],
                        reader=READERS.CV_INK, frame=frame,
                        ink_best_window=m["best_window"],
                        ink_windows=m["windows"],
                        ink_background=m["background"],
                        ink_background_windows=m["background_windows"])


#: ROADMAP 2.60 -- what makes a column of an arc box "curve-shaped": its
#: ink's longest vertical run is no longer than this many staff spaces. A
#: tie/slur stroke is 0.1-0.35 sp thick and, even on a steep end, stays under
#: it; a stem, a barline and a notehead are all longer. Fixed BEFORE any
#: count was taken (lane-arc-not-a-line).
ARC_INK_CURVE_RUN_SPACES = 0.8
#: A column is part of a TALL VERTICAL STROKE when one run covers this share
#: of the box's height (a barline, a stem).
ARC_INK_TALL_RUN_SHARE = 0.8
#: A staff line "passes through" the box within this many spaces of its rows,
#: and its stroke is taken to be this many spaces either side of its ink row.
ARC_INK_LINE_PAD_SPACES = 0.15
ARC_INK_LINE_STROKE_SPACES = 0.1
#: A staff line is SNAPPED to the page's own ink row (local, never the staff's
#: global value) only where this share of the box's columns are ink there.
ARC_INK_LINE_SNAP_SPACES = 0.3
ARC_INK_LINE_SNAP_MIN_FILL = 0.5
#: ...and a line's stroke is grown at most this far either side of the row.
ARC_INK_LINE_MAX_HALF_STROKE_SPACES = 0.4
#: A column holds ink only with at least this many ink pixels in it.
ARC_INK_MIN_COLUMN_PX = 2


def arc_ink_shape(binary: Any, box: Tuple[float, float, float, float],
                  space: float, line_ys: Sequence[float]
                  ) -> Optional[Dict[str, Any]]:
    """What is inside one arc box once EVERY staff line is taken out of it.
    ROADMAP 2.60.

    `binary` is the PAGE's own raster (0 = ink, the staff lines left in),
    `box` the arc's `(x0, y0, x1, y1)` in page pixels, `space` one staff
    space in pixels, `line_ys` EVERY staff line of the page that can cross the
    box -- the neighbouring staff's as well as the owner's: an arc box cut
    from one staff's cell routinely sits on the next staff's lines, which the
    owner's own erasure never touched. Each line is snapped to the ink row
    beside the box (LOCAL: a scanned staff tilts across a system) and its
    stroke removed. `None` where the box is off the raster or there is no
    unit -- declined, never defaulted.

      `coverage`      share of the box's columns holding CURVE-SHAPED ink
                      once the line strokes are removed (longest vertical run
                      <= `ARC_INK_CURVE_RUN_SPACES`)
      `tall_cols`     share of columns whose remaining ink run covers
                      `ARC_INK_TALL_RUN_SHARE` of the box height
      `lines_in_box`  how many staff lines pass through the box
      `width_spaces`, `height_spaces`   the box, in spaces
    """
    import numpy as np
    if binary is None or getattr(binary, "ndim", 0) != 2 or not space \
            or space <= 0:
        return None
    H, W = binary.shape
    x0, y0, x1, y1 = (float(v) for v in box)
    ix0, ix1 = max(0, int(round(x0))), min(W, int(round(x1)))
    iy0, iy1 = max(0, int(round(y0))), min(H, int(round(y1)))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    ink = (binary[iy0:iy1, ix0:ix1] == 0)
    h, w = ink.shape
    pad = ARC_INK_LINE_PAD_SPACES * space
    snap = int(round(ARC_INK_LINE_SNAP_SPACES * space))
    stroke = max(1, int(round(ARC_INK_LINE_STROKE_SPACES * space)))
    n_lines = 0
    removed = np.zeros(h, dtype=bool)
    for ly in line_ys:
        ly = float(ly)
        if not (y0 - pad <= ly <= y1 + pad):
            continue
        n_lines += 1
        r0 = int(round(ly)) - iy0
        best, best_fill = r0, 0.0
        for r in range(max(0, r0 - snap), min(h, r0 + snap + 1)):
            fill = float(ink[r].mean())
            if fill > best_fill + 1e-9 or (abs(fill - best_fill) < 1e-9
                                           and abs(r - r0) < abs(best - r0)):
                best, best_fill = r, fill
        if best_fill >= ARC_INK_LINE_SNAP_MIN_FILL:
            # the stroke is as thick as the ink row is: grow while the row is
            # still mostly ink (a scan's staff line is 3 px or 12), one pixel
            # of margin beyond it.
            top = bot = best
            cap = int(round(ARC_INK_LINE_MAX_HALF_STROKE_SPACES * space))
            while top - 1 >= 0 and best - (top - 1) <= cap \
                    and ink[top - 1].mean() >= ARC_INK_LINE_SNAP_MIN_FILL:
                top -= 1
            while bot + 1 < h and (bot + 1) - best <= cap \
                    and ink[bot + 1].mean() >= ARC_INK_LINE_SNAP_MIN_FILL:
                bot += 1
            removed[max(0, top - 1):min(h, bot + 2)] = True
        else:
            removed[max(0, r0 - stroke):min(h, r0 + stroke + 1)] = True
    ink = ink & ~removed[:, None]
    max_curve = ARC_INK_CURVE_RUN_SPACES * space
    curve = tall = 0
    for c in range(w):
        col = ink[:, c]
        if col.sum() < ARC_INK_MIN_COLUMN_PX:
            continue
        padded = np.concatenate(([0], col.astype(np.int8), [0]))
        d = np.diff(padded)
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        longest = int((ends - starts).max())
        if longest <= max_curve:
            curve += 1
        if longest >= ARC_INK_TALL_RUN_SHARE * h:
            tall += 1
    return {"coverage": round(curve / w, 4), "tall_cols": round(tall / w, 4),
            "lines_in_box": n_lines,
            "width_spaces": round((x1 - x0) / space, 3),
            "height_spaces": round((y1 - y0) / space, 3)}


def gather_arc_ink(log: Log, pws: Any, cells: Sequence[Any],
                   local: Dict[int, Tuple[int, int]],
                   detections: Dict[str, List[Any]]) -> None:
    """`Q.ARC_INK_SHAPE` on every detector `slur`/`tie` box. ROADMAP 2.60.

    ⚠️ OFF THE PAGE'S OWN RASTER (`pws.page.binary`, the staff lines left in)
    and the lines of EVERY staff of the page, in page pixels: the first
    version read the owner cell's erased raster and its own lines, and a box
    that sat on the NEXT staff's line read as a full curve (the three tiles
    Sean called barlines, 2026-10-07). A MEASUREMENT filed on the glyph,
    naming nothing; the thresholds live in the decision. Declined, never
    defaulted: no page raster -> `no_mask`; no staff unit ->
    `no_staff_geometry`.
    """
    binary = getattr(getattr(pws, "page", None), "binary", None)
    all_lines: List[float] = []
    for st in getattr(pws, "staves", ()) or ():
        all_lines.extend(float(y) for y in st.line_ys)
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        idx = [gi for gi, d in enumerate(dets)
               if d.smufl_name in _ARC_CLASSES]
        if not idx:
            continue
        frame = frame_cell(c.measure_index)
        grid = _cell_grid(c)
        space = grid[1] * 2.0 / float(getattr(c, "upscale_factor", 1.0) or 1.0) \
            if grid else None
        for gi in idx:
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            if binary is None or getattr(binary, "ndim", 0) != 2:
                log.abstain(g, Q.ARC_INK_SHAPE, reader=READERS.CV_ARC_INK,
                            frame=frame, reason=ABSTAIN.NO_MASK,
                            note="page carries no binary raster")
                continue
            page_box = _page_box(c, dets[gi])
            if not space or page_box is None:
                log.abstain(g, Q.ARC_INK_SHAPE, reader=READERS.CV_ARC_INK,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY)
                continue
            m = arc_ink_shape(binary, page_box, space, all_lines)
            if m is None:
                log.abstain(g, Q.ARC_INK_SHAPE, reader=READERS.CV_ARC_INK,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="box off the raster")
                continue
            log.observe(g, Q.ARC_INK_SHAPE, m["coverage"],
                        reader=READERS.CV_ARC_INK, frame=frame,
                        tall_cols=m["tall_cols"],
                        lines_in_box=m["lines_in_box"],
                        width_spaces=m["width_spaces"],
                        height_spaces=m["height_spaces"])


#: ROADMAP 2.39b — the bounded search around the detector's own centre, in
#: staff spaces (Sean's own bound: "at most +-0.6 sp vertically and +-0.4 sp
#: horizontally"). Not grown past what a measured sliver needs
#: (`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §18: the 8-of-8
#: sampled slivers are 0.29-0.4 sp wide against the standard 1.4, so their
#: true centre is at most a fraction of a space from the detector's own).
RECENTRE_MAX_DY_SPACES = 0.6
RECENTRE_MAX_DX_SPACES = 0.4
#: The search grid's own step. Fine enough that a real head's peak fill is
#: not skipped between two tested offsets; coarse enough that the ~2,347-
#: 3,337 regular noteheads per count page stay cheap (13 x 9 = 117 windows
#: per head, each one array-slice-and-sum).
RECENTRE_STEP_SPACES = 0.1
#: A winning window's own ink fill must clear this to be "clearly a head" —
#: CLAUDE.md rule 7, a control must be able to fail. Below it, DECLINE
#: rather than guess (rule 8): a thin stem fills a head-sized window only
#: ~15-20%, and a hollow head's own interior reads comparably sparse, so
#: neither should be read as "the standard box found its head" just because
#: it was the best of a bad set.
RECENTRE_MIN_FILL = 0.55
#: The winning window's own lead over the best NON-OVERLAPPING rival window
#: — so a tie between two chord noteheads' own windows (each a real, dense
#: head) DECLINES rather than picking one arbitrarily.
RECENTRE_MIN_MARGIN = 0.08
#: Two candidate windows are the "same" head once their boxes share more
#: than this fraction of the smaller one's own area — the runner-up search
#: skips these so it is not comparing the winner against a one-pixel shift
#: of itself.
RECENTRE_OVERLAP_FRAC = 0.30


def _recentre_window_fill(ink: Any, x0: float, x1: float, y0: float,
                          y1: float) -> Optional[float]:
    """Ink fraction inside `(x0, x1, y0, y1)` (canonical px, corners) on a
    `True == ink` boolean raster. `None` off the raster or a degenerate box
    — declined, never defaulted."""
    H, W = ink.shape
    ix0 = max(0, int(round(x0)))
    iy0 = max(0, int(round(y0)))
    ix1 = min(W, int(round(x1)))
    iy1 = min(H, int(round(y1)))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    region = ink[iy0:iy1, ix0:ix1]
    if region.size == 0:
        return None
    return float(region.sum()) / float(region.size)


def _recentre_boxes_overlap(a: Tuple[float, float, float, float],
                            b: Tuple[float, float, float, float],
                            frac: float) -> bool:
    """`True` where `a` and `b` (each `(x0, x1, y0, y1)`) share more than
    `frac` of the SMALLER box's own area."""
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b
    ix0, ix1 = max(ax0, bx0), min(ax1, bx1)
    iy0, iy1 = max(ay0, by0), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    inter = (ix1 - ix0) * (iy1 - iy0)
    a_area = max(1e-9, (ax1 - ax0) * (ay1 - ay0))
    b_area = max(1e-9, (bx1 - bx0) * (by1 - by0))
    return (inter / min(a_area, b_area)) > frac


def recentre_notehead(img: Any, cx: float, cy: float, spacing: float
                      ) -> Optional[Dict[str, Any]]:
    """The matched-window re-centre search — ROADMAP 2.39b (`Q.NOTEHEAD_
    RECENTRE`'s own docstring has the full design). `img` is a cell's
    `image_no_staff` (0 == ink); `cx`, `cy`, `spacing` are the detector's
    own centre and this staff's own measured spacing, all in `img`'s frame.

    `None` off the raster or a degenerate spacing — the caller abstains
    `no_mask`/`no_staff_geometry`. Otherwise a dict carrying the WINNING
    offset (in staff spaces, from the detector's own centre), its fill and
    its margin over the best non-overlapping rival, and `decline_reason`
    (`None` where the search accepts its own winner).
    """
    if img is None or getattr(img, "ndim", 0) != 2 or not spacing \
            or spacing <= 0:
        return None
    ink = (img == 0)
    n_dy = int(round(RECENTRE_MAX_DY_SPACES / RECENTRE_STEP_SPACES))
    n_dx = int(round(RECENTRE_MAX_DX_SPACES / RECENTRE_STEP_SPACES))
    candidates: List[Tuple[float, float, float,
                          Tuple[float, float, float, float]]] = []
    for iy in range(-n_dy, n_dy + 1):
        dy_sp = iy * RECENTRE_STEP_SPACES
        for ix in range(-n_dx, n_dx + 1):
            dx_sp = ix * RECENTRE_STEP_SPACES
            ncx = cx + dx_sp * spacing
            ncy = cy + dy_sp * spacing
            box = _standard_head_box(ncx, ncy, spacing)
            fill = _recentre_window_fill(ink, *box)
            if fill is None:
                continue
            candidates.append((dx_sp, dy_sp, fill, box))
    if not candidates:
        return None
    best = max(candidates, key=lambda c: c[2])
    rivals = [c for c in candidates
             if not _recentre_boxes_overlap(c[3], best[3],
                                            RECENTRE_OVERLAP_FRAC)]
    runner_up = max((c[2] for c in rivals), default=0.0)
    margin = best[2] - runner_up
    decline_reason = None
    if best[2] < RECENTRE_MIN_FILL:
        decline_reason = ABSTAIN.BELOW_THRESHOLD
    elif margin < RECENTRE_MIN_MARGIN:
        decline_reason = ABSTAIN.AMBIGUOUS
    return {
        "dx_sp": round(best[0], 3), "dy_sp": round(best[1], 3),
        "fill": round(best[2], 4), "runner_up": round(runner_up, 4),
        "margin": round(margin, 4), "decline_reason": decline_reason,
    }


#: ROADMAP 2.39b (manager review of `fa700001`, commit `fa700001`'s own
#: crops caught this): `litolff-glyph-owner-far-no-rungs.png` showed the
#: search moving a box that was ALREADY ON THE HEAD down into stem/beam
#: junction ink below it -- a Litolff box 1.84x the standard WIDTH and
#: 0.79x the standard HEIGHT, not a sliver, and the "densest window near
#: a head" on a MERGING plate is routinely the stem/beam junction, not
#: the head itself. The rule the crops support: a box already close to
#: the standard head's own size has a TRUSTWORTHY centre (CLAUDE.md's own
#: convention -- distrust the box's SIZE, never its CENTRE, unless the
#: box is too small to BE a head). Only a box clearly SMALLER than the
#: standard extent, in width OR height, is a candidate for re-centring.
#:
#: 0.7 chosen from this round's own box-size distribution (`width_
#: canonical / (STANDARD_HEAD_WIDTH_SPACES * spacing)`, `height_canonical
#: / (STANDARD_HEAD_HEIGHT_SPACES * spacing)`, the smaller of the two,
#: over every REGULAR notehead the un-gated search had accepted): the
#: population's own median sits at ~1.0 (a box already head-sized) on
#: both count pages, and only the bottom decile -- 7.5% of Litolff's 451,
#: 11.2% of Brahms's 765 -- falls under 0.7. That decile is where the
#: genuine slivers CLAUDE.md §10 names live (a confirmed Brahms sliver
#: measured 0.24 sp tall against a 1.1 sp standard height, ratio 0.22);
#: the flagged head above (ratio 0.79) sits well clear of it.
RECENTRE_BOX_SIZE_GATE = 0.7


def gather_notehead_recentre(log: Log, cells: Sequence[Any],
                             local: Dict[int, Tuple[int, int]],
                             detections: Dict[str, List[Any]]) -> None:
    """`Q.NOTEHEAD_RECENTRE` — ROADMAP 2.39b, one row per REGULAR notehead
    (`geometry.is_regular_notehead`) — a whole note, grace/cue head or any
    other class this round did not measure gets NO ROW AT ALL, the same
    gate every other `geometry.standard_head_box` consumer uses; never a
    guessed re-centre for a shape this round never measured.

    ⚠️ ROADMAP 2.39b (manager review, `RECENTRE_BOX_SIZE_GATE`'s own
    comment): the search runs ONLY where the detector's OWN box is
    clearly smaller than the standard extent (width OR height under the
    gate) -- a box already close to head-sized keeps the detector centre
    UNCONDITIONALLY, abstained `box_already_head_sized`, and the search
    never even runs on it.

    Reads `cell.image_no_staff` — the SAME staff-erased raster `Q.INK`/
    `Q.LEDGER_RUNG_INK`/`Q.STEM_TIP_INK`/`Q.BEAM_STEM_JOIN` read — so it is
    not an independent witness of any of them (`READERS.CV_NOTEHEAD_
    RECENTRE`'s own entry says so); it asks a different question (a bounded
    matched-window search for peak fill) with a different test.
    """
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        frame = frame_cell(c.measure_index)
        grid = _cell_grid(c)
        space_canonical = grid[1] * 2.0 if grid and grid[1] else None
        img = getattr(c, "image_no_staff", None)
        for gi, d in enumerate(dets):
            name = str(getattr(d, "smufl_name", ""))
            if not is_regular_notehead(name):
                continue
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            if space_canonical is None:
                log.abstain(g, Q.NOTEHEAD_RECENTRE,
                           reader=READERS.CV_NOTEHEAD_RECENTRE, frame=frame,
                           reason=ABSTAIN.NO_STAFF_GEOMETRY,
                           note="cell carries no measured line grid")
                continue
            std_w = STANDARD_HEAD_WIDTH_SPACES * space_canonical
            std_h = STANDARD_HEAD_HEIGHT_SPACES * space_canonical
            w_ratio = float(d.width_canonical) / std_w if std_w else None
            h_ratio = float(d.height_canonical) / std_h if std_h else None
            if (w_ratio is not None and h_ratio is not None
                    and w_ratio >= RECENTRE_BOX_SIZE_GATE
                    and h_ratio >= RECENTRE_BOX_SIZE_GATE):
                log.abstain(g, Q.NOTEHEAD_RECENTRE,
                           reader=READERS.CV_NOTEHEAD_RECENTRE, frame=frame,
                           reason=ABSTAIN.BOX_ALREADY_HEAD_SIZED,
                           note=f"detector box is already close to the "
                                f"standard head's own size "
                                f"(width_ratio={w_ratio:.3f}, "
                                f"height_ratio={h_ratio:.3f}); its centre "
                                f"is trusted unconditionally, never "
                                f"searched")
                continue
            if img is None or getattr(img, "ndim", 0) != 2:
                log.abstain(g, Q.NOTEHEAD_RECENTRE,
                           reader=READERS.CV_NOTEHEAD_RECENTRE, frame=frame,
                           reason=ABSTAIN.NO_MASK,
                           note="cell carries no image_no_staff")
                continue
            result = recentre_notehead(img, float(d.x_center),
                                       float(d.y_center), space_canonical)
            if result is None:
                log.abstain(g, Q.NOTEHEAD_RECENTRE,
                           reader=READERS.CV_NOTEHEAD_RECENTRE, frame=frame,
                           reason=ABSTAIN.NO_STAFF_GEOMETRY,
                           note="search window off the raster")
                continue
            if result["decline_reason"] is not None:
                log.abstain(g, Q.NOTEHEAD_RECENTRE,
                           reader=READERS.CV_NOTEHEAD_RECENTRE, frame=frame,
                           reason=result["decline_reason"],
                           fill=result["fill"], margin=result["margin"],
                           runner_up=result["runner_up"],
                           note="best window is not clearly a head, or not "
                                "clearly ahead of a rival window")
                continue
            log.observe(g, Q.NOTEHEAD_RECENTRE,
                       [result["dx_sp"], result["dy_sp"]],
                       reader=READERS.CV_NOTEHEAD_RECENTRE, frame=frame,
                       fill=result["fill"], margin=result["margin"],
                       runner_up=result["runner_up"])


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.115 -- a notehead box drawn on only PART of the head is re-centred
# before its inside is read (2.114 round 2, Sean's tile 13: Litolff
# glyph/1/0/9/11/1, a half note with the top staff line through its middle).
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED:
#   ASSUMED: a notehead is a roughly symmetric blob, so the vertical centroid of
#   its ink (the staff/ledger line's rows and any stem's columns left out) is its
#   centre; and the detector's box is TRUSTED sideways (a sliver is wrong in
#   height and size, not in x -- CLAUDE.md 5 "distrust the SIZE, never the
#   CENTRE" is kept for x). The head is read in a standard head box at that
#   centre, so a hollow head cut in two slits by a line is read where its
#   white is.
#   FALSIFIED BY: a print-confirmed BLACK head whose re-centred reading falls
#   below the hollow band, or a head moved to another pitch step (neither seen on
#   Brahms 317803 pdf 0 or Litolff 984073 idx 1 -- FINDINGS
#   `omr-head-recentre-2026-10`).
#   NOT CONFIRMED: the two cut-offs below are measured on two plates only (rule:
#   they NARROW until Sean's tiles / another publisher). Flag default OFF.
#
# WHY NOT RAISE `RECENTRE_BOX_SIZE_GATE` (2.39b): that search maximises window
# FILL, which a hollow head cannot win (12 of 39 Brahms hollow boxes decline
# `below_threshold`; tile 13 itself declines at 0.54 against 0.55 and lands
# 0.2 sp from the head), and a wider gate moves `Q.NOTEHEAD_RECENTRE`'s four
# other consumers (ledger owner, nearer staff, stem mask, rung ink). This
# reader moves ONLY the window `Q.NOTEHEAD_INK` reads and files the move in that
# row's detail; no row another reader consumes changes.
# ─────────────────────────────────────────────────────────────────────────────

#: A box is a candidate only where it is clearly short of a head in width OR
#: height (the smaller of the two ratios to the standard head under this).
RECENTRE_PART_SIZE_GATE = 0.9
#: ... and only where the head's ink centre sits at least this far (staff
#: spaces, vertical) from the box's centre; closer is a box already on its head.
RECENTRE_PART_MIN_SHIFT_SPACES = 0.15
#: ... and not further than 2.39b's own search bound (a farther "centre" is
#: another mark's ink).
RECENTRE_PART_MAX_SHIFT_SPACES = RECENTRE_MAX_DY_SPACES
#: The ink window the centroid is taken over: half-height/half-width in staff
#: spaces around the box centre (a head is ~1.1 x 1.4; 0.7 keeps a neighbouring
#: line or head out; MEASURED against Sean's boxes, FINDINGS).
RECENTRE_PART_HALF_WINDOW_SPACES = 0.8
#: Ink in a column whose vertical run is longer than this is a STEM, left out.
RECENTRE_PART_STEM_RUN_SPACES = 1.7
#: Ink needed in the window (staff-space squares) before a centroid is trusted.
RECENTRE_PART_MIN_INK_SPACES2 = 0.15
#: ... and only where the box as drawn does NOT already read hollow: its
#: smaller centre reading (raw / line rows left out) is above this. Restates
#: `rhythm.HEAD_FILL_HOLLOW_CENTER_MAX` (2.23/2.73; `rhythm` imports this
#: module, so the reverse import would be a cycle -- `test_staged_part_boxed_
#: recentre_2_115` pins the two equal).
RECENTRE_PART_ONLY_ABOVE_CENTRE = 0.75
#: ... and a BLANK window is not a hollow reading (2.88's `HEAD_RAW_CENTER_FLOOR`, restated
#: for the same reason): under this the box is not on a head at all and may be moved.
RECENTRE_PART_HOLLOW_FLOOR = 0.2
#: The estimate must not depend on the window: it is taken at each of these
#: half-sizes (staff spaces; `RECENTRE_PART_HALF_WINDOW_SPACES` is the one
#: used) and refused `unstable` where they disagree by more than the spread cut.
#: ROUND 2 (page raster): on tile 13 the centroid is a function of the window
#: below 0.75 sp (shift -0.17 / 0.01 / 0.26 / 0.38 at 0.5 / 0.6 / 0.7 / 0.75; by
#: eye 0.27-0.30) because a window smaller than the head clips the ring
#: asymmetrically once the line rows are left out, and settles from 0.75 up
#: (0.38 / 0.36 / 0.36 at 0.75 / 0.8 / 0.9). Windows 0.75-0.9 are the ones that
#: contain a whole head; MEASURED, not derived: five window sets x two spread cuts
#: on Sean's truth pages are in the 2.115 FINDINGS (round 2). Same guard, same
#: spread cut; only the windows moved.
RECENTRE_PART_WINDOWS = (0.75, 0.8, 0.85, 0.9)
RECENTRE_PART_MAX_SPREAD_SPACES = 0.1
RECENTRE_PART_ITERATIONS = 40
RECENTRE_PART_CONVERGED_SPACES = 0.01


def part_boxed_recentre_enabled() -> bool:
    """`OMR_RECENTRE_PART_BOXED` -- ROADMAP 2.115. **Default ON** (Sean,
    2026-10-14, "Land 2.115 on"); `OMR_RECENTRE_PART_BOXED=0` turns it off."""
    return os.environ.get("OMR_RECENTRE_PART_BOXED", "1").strip().lower() \
        not in ("0", "false", "no", "off", "")


def recentre_part_boxed(raw: Any, box: Tuple[float, float, float, float],
                        spacing: float) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.115 -- where a head's ink centre sits against its detector box.

    `raw` is the UNERASED raster (0 == ink) and `box` the detector's own
    `(x, y, w, h)`, both in that raster's frame; `spacing` the staff space.
    `None` off the raster or with no spacing. Otherwise a dict:
    `accepted` (bool), `dy_sp` (centre shift to apply, staff spaces, + = down),
    `reason` (None when accepted, else why the box keeps its reading:
    `box_head_sized`, `centred_enough`, `no_ink`, `not_converged`, `too_far`),
    and the numbers it came close with (`size_ratio`, `size_margin`,
    `shift_sp`, `shift_margin`, `max_shift_margin`, `ink_spaces2`,
    `line_rows`). Sideways the detector's centre is kept. Pure.
    """
    import numpy as np
    if raw is None or getattr(raw, "ndim", 0) != 2 or not spacing \
            or spacing <= 0:
        return None
    x, y, w, h = (float(v) for v in box)
    ratio = min(w / (STANDARD_HEAD_WIDTH_SPACES * spacing),
                h / (STANDARD_HEAD_HEIGHT_SPACES * spacing))
    out: Dict[str, Any] = {
        "accepted": False, "reason": None, "dy_sp": 0.0,
        "size_ratio": round(ratio, 3),
        "size_margin": round(RECENTRE_PART_SIZE_GATE - ratio, 3)}
    if ratio >= RECENTRE_PART_SIZE_GATE:
        out["reason"] = "box_head_sized"
        return out
    # A box whose own interior already reads hollow (raw or line-rows-left-out
    # centre at or under 2.88's cut) keeps that reading: the question here is a
    # box that reads FILLED or unclear while covering only part of its head. A
    # move can then only ever turn a filled/unclear reading into the head's own,
    # never lose a hollow one found by a window that happened to land well.
    drawn = [m["windows"]["center"] for m in
             (notehead_ink_under(raw, (x, y, w, h)),
              notehead_ink_off_line(raw, (x, y, w, h), spacing))
             if m is not None and m["windows"]["center"] is not None]
    if drawn:
        out["drawn_centre"] = round(min(drawn), 4)
        if RECENTRE_PART_HOLLOW_FLOOR <= min(drawn) <= RECENTRE_PART_ONLY_ABOVE_CENTRE:
            out["reason"] = "already_reads_hollow"
            out["drawn_margin"] = round(min(drawn) - RECENTRE_PART_ONLY_ABOVE_CENTRE, 4)
            return out
    cx, cy = x + w / 2.0, y + h / 2.0
    ink = (np.asarray(raw) == 0)
    H, W = ink.shape
    rad = int(3.2 * spacing)
    X0, X1 = max(0, int(cx - rad)), min(W, int(cx + rad))
    Y0, Y1 = max(0, int(cy - rad)), min(H, int(cy + rad))
    if X1 <= X0 or Y1 <= Y0:
        return None
    sub = ink[Y0:Y1, X0:X1]
    # a STEM: ink in a vertical run longer than the cut (a head is ~1.1 sp)
    stem = np.zeros(sub.shape, dtype=bool)
    cut = RECENTRE_PART_STEM_RUN_SPACES * spacing
    for xi in range(sub.shape[1]):
        col = sub[:, xi]
        if not col.any():
            continue
        d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
        for s0, e0 in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if e0 - s0 > cut:
                stem[s0:e0, xi] = True
    # a LINE row: ink past the head on both sides (2.73's own definition)
    lo_l = int(round(cx - HEAD_LINE_ROW_BAND_SPACES[1] * spacing)) - X0
    hi_l = int(round(cx - HEAD_LINE_ROW_BAND_SPACES[0] * spacing)) - X0
    lo_r = int(round(cx + HEAD_LINE_ROW_BAND_SPACES[0] * spacing)) - X0
    hi_r = int(round(cx + HEAD_LINE_ROW_BAND_SPACES[1] * spacing)) - X0
    left = sub[:, max(0, lo_l):max(0, hi_l)]
    right = sub[:, max(0, lo_r):max(0, hi_r)]
    if left.shape[1] and right.shape[1]:
        line_rows = (left.mean(axis=1) >= HEAD_LINE_ROW_FILL) \
            & (right.mean(axis=1) >= HEAD_LINE_ROW_FILL)
    else:
        line_rows = np.zeros(sub.shape[0], dtype=bool)
    out["line_rows"] = int(line_rows.sum())
    ys, xs = np.mgrid[0:sub.shape[0], 0:sub.shape[1]]

    def settle(half_sp: float):
        """The centroid's fixed point for one window size: `(shift in spaces,
        ink in space squares)`, or `(None, ink)` where it did not settle."""
        half = half_sp * spacing
        keep = sub & ~stem & ~line_rows[:, None] \
            & (np.abs(xs + X0 - cx) <= half)
        ey, n = cy, 0
        for _ in range(RECENTRE_PART_ITERATIONS):
            pts = keep & (np.abs(ys + Y0 - ey) <= half)
            n = int(pts.sum())
            if n < RECENTRE_PART_MIN_INK_SPACES2 * spacing * spacing:
                return None, n / (spacing * spacing), "no_ink"
            ny = float(ys[pts].mean() + Y0)
            step = abs(ny - ey) / spacing
            ey = ny
            if step < RECENTRE_PART_CONVERGED_SPACES:
                return (ey - cy) / spacing, n / (spacing * spacing), None
        return None, n / (spacing * spacing), "not_converged"

    results = [settle(hw) for hw in RECENTRE_PART_WINDOWS]
    main = results[RECENTRE_PART_WINDOWS.index(RECENTRE_PART_HALF_WINDOW_SPACES)]
    if main[2] is not None:
        out["reason"] = main[2]
        out["ink_spaces2"] = round(main[1], 3)
        return out
    shift = main[0]
    shifts = [r[0] for r in results if r[0] is not None]
    spread = (max(shifts) - min(shifts)) if len(shifts) == len(results) \
        else float("inf")
    out.update(shift_sp=round(shift, 3),
               shift_margin=round(abs(shift) - RECENTRE_PART_MIN_SHIFT_SPACES, 3),
               max_shift_margin=round(RECENTRE_PART_MAX_SHIFT_SPACES - abs(shift), 3),
               ink_spaces2=round(main[1], 3),
               window_spread_sp=(round(spread, 3) if spread != float("inf") else None),
               spread_margin=(round(RECENTRE_PART_MAX_SPREAD_SPACES - spread, 3)
                              if spread != float("inf") else None))
    if abs(shift) < RECENTRE_PART_MIN_SHIFT_SPACES:
        out["reason"] = "centred_enough"
    elif spread > RECENTRE_PART_MAX_SPREAD_SPACES:
        out["reason"] = "unstable"
    elif abs(shift) > RECENTRE_PART_MAX_SHIFT_SPACES:
        out["reason"] = "too_far"
    else:
        out["accepted"] = True
        out["dy_sp"] = round(shift, 3)
    return out


def recentre_part_boxed_on_page(cell: Any, det: Any, page_binary: Any,
                                space_canonical: float
                                ) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.115 round 2 -- `recentre_part_boxed` run on the PAGE raster.

    `cell` is the `MeasureCell` (its `bbox_page_px` and `upscale_factor` are
    the canonical->page map `_page_box` and `Q.GLYPH_BOX` already use), `det`
    the detection, `page_binary` `pws.page.binary` (0 == ink, staff lines in)
    and `space_canonical` the cell's staff space. Returns `recentre_part_boxed`'s
    dict with `frame: "page"` and the page-frame space; where it ACCEPTS, also
    `_page_reads`: the interior of the standard head box at the moved centre
    read off the page raster, `(notehead_ink_under, notehead_ink_off_line)` --
    the caller pops it. `reason: "no_page_raster"` where the page raster, the
    mapping or the staff unit is missing: DECLINED, never read from the cell.
    """
    declined = {"accepted": False, "reason": "no_page_raster", "dy_sp": 0.0,
                "frame": "page"}
    up = getattr(cell, "upscale_factor", None)
    page_box = _page_box(cell, det)
    if (page_binary is None or getattr(page_binary, "ndim", 0) != 2
            or page_box is None or not up or not space_canonical):
        return declined
    space_page = float(space_canonical) / float(up)
    px0, py0, px1, py1 = page_box
    out = recentre_part_boxed(page_binary, (px0, py0, px1 - px0, py1 - py0),
                              space_page)
    if out is None:
        return declined
    out["frame"] = "page"
    out["space_page"] = round(space_page, 3)
    if out["accepted"]:
        bx0, bx1, by0, by1 = _standard_head_box(
            (px0 + px1) / 2.0, (py0 + py1) / 2.0 + out["dy_sp"] * space_page,
            space_page)
        std = (bx0, by0, bx1 - bx0, by1 - by0)
        out["_page_reads"] = (
            notehead_ink_under(page_binary, std),
            notehead_ink_off_line(page_binary, std, space_page))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.73 -- a hollow head CUT BY A LINE.
#
# Sean (2026-10-09): *"In many of the hand label cells I have found that half
# notes, especially ones that are on lines or ledger lines, get split up into
# two smaller boxes instead of one large box around the notehead."* Measured
# on his 27 hand-labelled half heads (`data/hand-truth/pages/imslp317803/0.
# json`): a head on a line is printed as a ring with a line through its hole,
# so the ring shows TWO white holes, one either side of the line, and the
# detector boxes ONE of them (a box about half a head tall whose top or bottom
# edge is on the line, class `noteheadHalfInSpace`), or both. See
# `Q.HEAD_LINE_CUT`'s own docstring in `record.py` and
# `benchmarks/omr-head-fill-2026-09/FINDINGS.md` Sec.8.
#
# ⚠️ THE EVIDENCE IS THE INK, NOT AN ASSUMPTION (Sean: look where it must be,
# never infer): the mirror half is accepted only where the raster HOLDS a
# second enclosed hole, of like size, standing point-symmetrically with the
# first about the line's own centre. A head in a space has one hole, a black
# head none, a notehead whose hole a tremolo slash splits has no line at the
# box edge -- none of them can carry the row.
# ─────────────────────────────────────────────────────────────────────────────

#: A box at most this tall (staff spaces) can be HALF a head. A whole head is
#: `STANDARD_HEAD_HEIGHT_SPACES` (1.1); the cut halves measured on Brahms
#: 317803 pdf 0 are 0.58-0.89 sp, and the detector's whole boxes on Sean's
#: space heads 1.06-1.31. Between 0.89 and 1.06 nothing was measured: 0.95
#: sits in that gap, so a whole box is never a candidate.
HEAD_CUT_MAX_BOX_HEIGHT_SPACES = 0.95
#: ... and at least this wide: a half-ring is as wide as the head.
HEAD_CUT_MIN_BOX_WIDTH_SPACES = 0.9
#: The box edge must lie within this of the line's centre (staff spaces).
HEAD_CUT_EDGE_ON_LINE_SPACES = 0.3
#: The search window around the box's centre, in staff spaces.
HEAD_CUT_WINDOW_HALF_WIDTH_SPACES = 0.9
HEAD_CUT_WINDOW_HALF_HEIGHT_SPACES = 1.0
#: A half-hole: enclosed white, between these areas (staff spaces squared) and
#: no bigger than this in either extent (a head's whole hole is ~0.2 sp^2).
HEAD_CUT_HOLE_AREA_SPACES2 = (0.02, 0.45)
HEAD_CUT_HOLE_MAX_WIDTH_SPACES = 0.95
HEAD_CUT_HOLE_MAX_HEIGHT_SPACES = 0.7
#: The two holes are alike in size ...
HEAD_CUT_AREA_RATIO = (0.4, 2.5)
#: ... stand this far apart vertically (their centres) ...
HEAD_CUT_HOLE_SEPARATION_SPACES = (0.25, 1.1)
#: ... and their common centre lies this near the detector box's own centre
#: horizontally.
HEAD_CUT_MAX_DX_SPACES = 0.5
#: The line is read beside the head: ink in these x-bands either side of the
#: pair's centre (staff spaces from it), on the line's own rows. A ledger line
#: runs past the head; a slash or a stem does not. The longer side must read at
#: least the first fill, the shorter side at least the second (a stem, a dot
#: or a neighbouring note may stand on one side).
HEAD_CUT_LINE_BAND_SPACES = (0.78, 0.98)
HEAD_CUT_LINE_FILL = (0.75, 0.4)


def _enclosed_holes(ink: Any, x0: int, y0: int, x1: int, y1: int
                    ) -> List[Dict[str, float]]:
    """Every white region of `ink[y0:y1, x0:x1]` (True == ink) that does not
    touch the window's own border: enclosed by ink on every side (4-connected
    white, so a gap one pixel wide at a corner is a leak and an honest "not
    enclosed"). Each carries its area, centre and extent, page-of-the-raster
    coordinates."""
    import cv2
    import numpy as np
    H, W = ink.shape
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W, int(x1)), min(H, int(y1))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return []
    white = (~ink[y0:y1, x0:x1]).astype(np.uint8)
    n, _lab, stats, cents = cv2.connectedComponentsWithStats(white, 4)
    h, w = white.shape
    out = []
    for i in range(1, n):
        sx, sy, sw, sh, area = (int(v) for v in stats[i])
        if sx == 0 or sy == 0 or sx + sw >= w or sy + sh >= h:
            continue
        out.append({"area": float(area), "cx": float(cents[i][0]) + x0,
                    "cy": float(cents[i][1]) + y0, "w": float(sw),
                    "h": float(sh)})
    return out


def head_cut_by_line(ink: Any, box: Tuple[float, float, float, float],
                     spacing: float) -> Optional[Dict[str, Any]]:
    """Is this about-half-a-head box one half of a hollow head a LINE cuts?
    ROADMAP 2.73. `ink` is a cell raster as a boolean array (True == ink, the
    UNERASED one), `box` the detector's `(x0, y0, x1, y1)` and `spacing` the
    staff space, all in that raster's frame.

    Returns `None` unless EVERY test holds: the box is about half a head
    (`HEAD_CUT_MAX_BOX_HEIGHT_SPACES` tall, at least `..._MIN_BOX_WIDTH_...`
    wide); the window around it holds two enclosed holes (`_enclosed_holes`),
    one above the other, alike in size and standing the stated distance apart;
    their common centre is the line row, within `HEAD_CUT_EDGE_ON_LINE_SPACES`
    of the box's top or bottom edge and near the box's own centre in x; and a
    horizontal line stands on that row, past the head on either side. Otherwise
    the dict names the rebuilt centre `(cx, line_y)`, which edge was on the
    line, both holes and the line's own ink.
    """
    if ink is None or getattr(ink, "ndim", 0) != 2 or not spacing \
            or spacing <= 0:
        return None
    bx0, by0, bx1, by1 = (float(v) for v in box)
    w, h = bx1 - bx0, by1 - by0
    if h > HEAD_CUT_MAX_BOX_HEIGHT_SPACES * spacing \
            or w < HEAD_CUT_MIN_BOX_WIDTH_SPACES * spacing:
        return None
    xc0, yc0 = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
    holes = [hl for hl in _enclosed_holes(
        ink, xc0 - HEAD_CUT_WINDOW_HALF_WIDTH_SPACES * spacing,
        yc0 - HEAD_CUT_WINDOW_HALF_HEIGHT_SPACES * spacing,
        xc0 + HEAD_CUT_WINDOW_HALF_WIDTH_SPACES * spacing,
        yc0 + HEAD_CUT_WINDOW_HALF_HEIGHT_SPACES * spacing)
        if (HEAD_CUT_HOLE_AREA_SPACES2[0] * spacing * spacing
            <= hl["area"] <= HEAD_CUT_HOLE_AREA_SPACES2[1] * spacing * spacing
            and hl["w"] <= HEAD_CUT_HOLE_MAX_WIDTH_SPACES * spacing
            and hl["h"] <= HEAD_CUT_HOLE_MAX_HEIGHT_SPACES * spacing)]
    best = None
    for a in holes:
        for b in holes:
            if not a["cy"] < b["cy"]:
                continue
            line_y = (a["cy"] + b["cy"]) / 2.0
            xc = (a["cx"] + b["cx"]) / 2.0
            ratio = a["area"] / b["area"]
            sep = b["cy"] - a["cy"]
            if not (HEAD_CUT_AREA_RATIO[0] <= ratio <= HEAD_CUT_AREA_RATIO[1]
                    and HEAD_CUT_HOLE_SEPARATION_SPACES[0] * spacing <= sep
                    <= HEAD_CUT_HOLE_SEPARATION_SPACES[1] * spacing
                    and abs(xc - xc0) <= HEAD_CUT_MAX_DX_SPACES * spacing):
                continue
            d_top, d_bot = abs(by0 - line_y), abs(by1 - line_y)
            if min(d_top, d_bot) > HEAD_CUT_EDGE_ON_LINE_SPACES * spacing:
                continue
            ly = int(round(line_y))
            fills = []
            for sgn in (-1, 1):
                lo = int(round(xc + sgn * HEAD_CUT_LINE_BAND_SPACES[0]
                               * spacing))
                hi = int(round(xc + sgn * HEAD_CUT_LINE_BAND_SPACES[1]
                               * spacing))
                zone = ink[max(0, ly - 1):ly + 2,
                           max(0, min(lo, hi)):max(0, max(lo, hi))]
                fills.append(float(zone.mean()) if zone.size else 0.0)
            if not (max(fills) >= HEAD_CUT_LINE_FILL[0]
                    and min(fills) >= HEAD_CUT_LINE_FILL[1]):
                continue
            score = -abs(math.log(ratio))
            if best is None or score > best[0]:
                best = (score, xc, line_y, a, b, ratio, fills,
                        "top" if d_top <= d_bot else "bottom")
    if best is None:
        return None
    _s, xc, line_y, a, b, ratio, fills, edge = best
    return {"cx": xc, "line_y": line_y, "edge": edge, "area_ratio": ratio,
            "holes": [a, b], "line_ink": fills}


def gather_head_line_cut(log: Log, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]]) -> None:
    """`Q.HEAD_LINE_CUT` -- ROADMAP 2.73, one row per notehead-classed glyph
    whose box is half a head cut by a line (see `head_cut_by_line`). A second
    reading BESIDE the detector's box, never an edit of it; no row where the
    test does not apply (the `Q.STACKED_HEAD_FIT` convention). Runs before
    `gather_notehead_positions`, which reads it, and `gather_notehead_ink`.

    Reads `cell.binary`, the UNERASED canonical raster: the line through the
    head is the evidence, and erasing it first would join the two half-holes
    into one hole and leave nothing to find.
    """
    import numpy as np
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        raw = getattr(c, "binary", None)
        grid = _cell_grid(c)
        if raw is None or getattr(raw, "ndim", 0) != 2 or grid is None:
            continue
        top_y, half_step = grid
        spacing = half_step * 2.0
        ink = None
        frame = frame_cell(c.measure_index)
        for gi, d in enumerate(dets):
            name = str(getattr(d, "smufl_name", ""))
            if not name.lower().startswith(_NOTEHEAD_PREFIX) \
                    or not is_regular_notehead(name):
                continue
            h_sp = float(d.height_canonical) / spacing
            if h_sp > HEAD_CUT_MAX_BOX_HEIGHT_SPACES:
                continue                       # already head-sized
            if ink is None:
                ink = (np.asarray(raw) == 0)
            box = (float(d.x_canonical), float(d.y_canonical),
                   float(d.x_canonical) + float(d.width_canonical),
                   float(d.y_canonical) + float(d.height_canonical))
            cut = head_cut_by_line(ink, box, spacing)
            if cut is None:
                continue
            hx0, hx1, hy0, hy1 = _standard_head_box(cut["cx"], cut["line_y"],
                                                    spacing)
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            log.observe(
                g, Q.HEAD_LINE_CUT,
                [round(hx0, 2), round(hy0, 2), round(hx1 - hx0, 2),
                 round(hy1 - hy0, 2)],
                reader=READERS.CV_HEAD_LINE_CUT, frame=frame,
                line_y=round(cut["line_y"], 2),
                line_half_step=int(round((cut["line_y"] - top_y) / half_step)),
                line_half_step_float=round((cut["line_y"] - top_y)
                                           / half_step, 3),
                edge=cut["edge"], area_ratio=round(cut["area_ratio"], 3),
                holes=[{k: round(v, 2) for k, v in hl.items()}
                       for hl in cut["holes"]],
                line_ink=[round(v, 3) for v in cut["line_ink"]],
                detector_box=[round(v, 2) for v in box])


#: The interior of a notehead's OWN box is shrunk by this fraction on every
#: side to make the `center` window. Dense for a filled BLACK head; near-
#: empty for a HOLLOW one (half/whole) by construction — which is exactly
#: why `center` alone must never gate a refusal (`ring` is the hollow
#: head's own witness). ROADMAP 2.23 (ported, GATHER half, from
#: `claude/no-ink-head-2.6h`, commit `a8394476`).
NOTEHEAD_INK_CENTER_SHRINK = 0.30


def head_interior_white(img: Any, box: Tuple[float, float, float, float]) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.148 (Sean 2026-10-16: the notehead is determined FIRST as black or hollow -- "containing white"). Does the
    head hold white INSIDE its ink, wherever and however thin? `img` is a cell raster with 0 = ink, `box` the detector's own
    `(x, y, w, h)` in that frame. Two readings, scale-free (fractions of the box), never collapsed:
      `rows_share`  of the box's middle rows (20-80% of its height) holding ink, the share with a white run strictly between
                    two ink pixels inside the middle columns (12-88% of its width) -- a half's slit counts even where it
                    opens out of a broken rim (Litolff's thin diagonal slit, which 2.23's centred window reads as ink);
      `hole_share`  the largest white component enclosed by ink, centred in the box's middle half, as a share of the box.
    Measured before the build on Sean's Brahms 317803 pdf 0 hand truth (page raster, 600 dpi): filled heads rows_share
    <= 0.06 (378), hollow >= 0.18 (33); hole_share 0 on every filled head, > 0 on every hollow one. `None` off the raster."""
    if img is None:
        return None
    import numpy as _np
    x, y, w, h = (float(v) for v in box)
    H, W = img.shape[:2]
    x0, y0, x1, y1 = int(round(x)), int(round(y)), int(round(x + w)), int(round(y + h))
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H or x1 - x0 < 4 or y1 - y0 < 4:
        return None
    ink = _np.asarray(img[y0:y1, x0:x1]) == 0
    hh, ww = ink.shape
    a, b = int(0.12 * ww), max(int(0.12 * ww) + 1, int(0.88 * ww))
    minrun = max(1, int(round(0.05 * ww)))
    n = hit = 0
    for yy in range(int(0.2 * hh), max(int(0.2 * hh) + 1, int(0.8 * hh))):
        r = ink[yy, a:b]
        xs = _np.nonzero(r)[0]
        if len(xs) == 0:
            continue
        n += 1
        seg = r[xs[0]:xs[-1] + 1]
        run = best = 0
        for v in seg:
            run = run + 1 if not v else 0
            best = max(best, run)
        hit += best >= minrun
    rows_share = hit / n if n else 0.0
    from scipy import ndimage as _nd
    lab, k = _nd.label(~ink)
    hole = 0.0
    if k:
        border = set(_np.unique(_np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
        for i in range(1, k + 1):
            if i in border:
                continue
            ys, xs = _np.nonzero(lab == i)
            if len(ys) < 3:
                continue
            cy, cx = ys.mean() / hh, xs.mean() / ww
            if 0.25 <= cy <= 0.75 and 0.25 <= cx <= 0.75:
                hole = max(hole, len(ys) / float(ink.size))
    return {"rows_share": round(rows_share, 4), "hole_share": round(hole, 4), "rows_read": n, "box": [x0, y0, x1 - x0, y1 - y0]}


def head_interior_white_located(cell: Any, box_cell: Tuple[float, float, float, float], page_binary: Any,
                                located_by: str) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.159. `head_interior_white` on the head box an earlier GATHER reader LOCATED (`box_cell`, canonical cell
    frame: the 2.39b re-centred / 2.73 line-cut / 2.115 part-boxed standard head box), read off the PAGE raster at that
    box's page position (the cell raster is the page resized, and there a part-boxed head merges with its stem and the
    next line: Sean 2026-10-14, 2.115 round 2). Measured on the 20261016-night records: the detector box of 95/114
    Litolff and 223/231 Brahms `head_fill_from_ink` heads is not one head's size, most often only PART of the head, so its
    own reading is of a rim. Returns the reading plus `box_cell` (the located box, for the same-head check ADJUDICATE
    makes) and `located_by`; `None` where the page raster or the canonical->page map is missing (declined, never read
    from the cell)."""
    bbox = getattr(cell, "bbox_page_px", None)
    up = getattr(cell, "upscale_factor", None)
    if page_binary is None or getattr(page_binary, "ndim", 0) != 2 or not bbox or not up:
        return None
    x, y, w, h = (float(v) for v in box_cell)
    r = head_interior_white(page_binary, (bbox[0] + x / up, bbox[1] + y / up, w / up, h / up))
    if r is None:
        return None
    return {**r, "frame": "page", "box_cell": [round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
            "located_by": located_by}


def notehead_ink_under(img: Any, box: Tuple[float, float, float, float]
                       ) -> Optional[Dict[str, Any]]:
    """The ink fraction inside a notehead's OWN detected box, two ways.
    ROADMAP 2.23 (ported, GATHER half only, from `claude/no-ink-head-2.6h`).

    `img` is a cell raster with 0 = ink; `box` the glyph's own
    `(x, y, w, h)` in THAT raster's frame (canonical, the exact box the
    detector drew). ⚠️ NO STAFF-SPACE UNIT IS NEEDED — unlike
    `ledger_ink_under`, which places OFFSET windows in staff spaces around a
    rung, every window here is a FRACTION of the box's own area, scale-free
    by construction. Returns `None` off the raster or a degenerate box —
    declined, never defaulted.

      `center`   ink fraction in the box's own interior, shrunk
                 `NOTEHEAD_INK_CENTER_SHRINK` on every side — dense for a
                 filled (BLACK) head, near-empty for a HOLLOW one.
      `ring`     ink fraction in the band BETWEEN the interior and the full
                 box — a hollow head's own border, present on both kinds,
                 and this rule's positive control for one.
      `best`     the larger of the two — the value GATHER files.

    ⚠️ NOT A THIRD "densest row" WINDOW, DELIBERATELY — see `a8394476`'s
    own docstring (this function's source): a single row's own ink fraction
    reads FULL for any thin mark spanning the box's width, whether it is a
    hollow head's cap or one page-wide staff/ledger line — the two are the
    SAME single-row reading, and `ring` already keeps the hollow-head
    positive control without that confusion.

    A box with no ink AT ALL under it reads `best == 0.0` on every window —
    a box standing on blank paper is exactly this record's claim, never a
    lower number fitted to one document after the fact.
    """
    if img is None or getattr(img, "ndim", 0) != 2:
        return None
    ink = (img == 0)
    H, W = ink.shape
    x, y, w, h = (float(v) for v in box)
    x0 = max(0, int(round(x)))
    y0 = max(0, int(round(y)))
    x1 = min(W, int(round(x + w)))
    y1 = min(H, int(round(y + h)))
    if x1 <= x0 or y1 <= y0:
        return None
    region = ink[y0:y1, x0:x1]
    if region.size == 0:
        return None

    def frac(arr) -> Optional[float]:
        return float(arr.sum()) / float(arr.size) if arr.size else None

    dx = int(round(NOTEHEAD_INK_CENTER_SHRINK * (x1 - x0)))
    dy = int(round(NOTEHEAD_INK_CENTER_SHRINK * (y1 - y0)))
    cx0, cx1 = x0 + dx, x1 - dx
    cy0, cy1 = y0 + dy, y1 - dy
    center: Optional[float] = None
    ring: Optional[float] = None
    if cx1 > cx0 and cy1 > cy0:
        core = ink[cy0:cy1, cx0:cx1]
        center = frac(core)
        core_area = core.size
        total_area = region.size
        ring_area = total_area - core_area
        if ring_area > 0:
            ring = float(int(region.sum()) - int(core.sum())) / float(ring_area)
    # ⚠️ TOO SHORT/NARROW FOR AN INTERIOR — the box's own dimension is under
    # the shrink, so `center` and `ring` would degenerate to the same
    # pixels: both stay `None` rather than faked.
    windows = {"center": center, "ring": ring}
    measured = {k: v for k, v in windows.items() if v is not None}
    if not measured:
        return None
    best_key = max(measured, key=lambda k: measured[k])
    return {
        "best": round(measured[best_key], 4),
        "best_window": best_key,
        "windows": {k: (None if v is None else round(v, 4))
                    for k, v in windows.items()},
    }


#: ROADMAP 2.73. A row of a head's box is a LINE row where a horizontal line
#: stands on it past the head on BOTH sides: ink in the two x-bands this many
#: staff spaces either side of the head's centre, at least this fraction in
#: each. A staff or ledger line through a hollow head's hole reads as fill on
#: every window that includes it (Brahms 317803 pdf 0: raw centre 0.93 against
#: 0.60 on the staff-erased raster, a ledger line being erased by neither).
HEAD_LINE_ROW_BAND_SPACES = (0.78, 0.98)
HEAD_LINE_ROW_FILL = 0.6
#: ... and a head whose box loses more than this fraction of its rows to lines
#: has no window left to read: declined, never defaulted.
HEAD_LINE_ROWS_MAX_LOST = 0.5


def notehead_ink_off_line(img: Any, box: Tuple[float, float, float, float],
                          spacing: float) -> Optional[Dict[str, Any]]:
    """`notehead_ink_under`'s reading of a head's own box with the LINE ROWS
    left out -- ROADMAP 2.73 (Sean: the hollow test must be measured off the
    line's rows, so a line through the hole cannot read as fill).

    `img` is the UNERASED canonical raster (0 == ink), `box` a head's
    `(x, y, w, h)` and `spacing` the staff space, all in that frame. A row
    counts as a line row where `HEAD_LINE_ROW_FILL` of both bands beyond the
    head (`HEAD_LINE_ROW_BAND_SPACES` either side of its centre) is ink. The
    `center` and `ring` windows are `notehead_ink_under`'s own (the same
    `NOTEHEAD_INK_CENTER_SHRINK` interior), taken over the remaining rows.
    `None` where the box is off the raster, `spacing` is unknown, or the lines
    took more than `HEAD_LINE_ROWS_MAX_LOST` of its rows.
    """
    import numpy as np
    if img is None or getattr(img, "ndim", 0) != 2 or not spacing \
            or spacing <= 0:
        return None
    ink = (np.asarray(img) == 0)
    H, W = ink.shape
    x, y, w, h = (float(v) for v in box)
    x0, y0 = max(0, int(round(x))), max(0, int(round(y)))
    x1, y1 = min(W, int(round(x + w))), min(H, int(round(y + h)))
    if x1 <= x0 or y1 <= y0:
        return None
    xc = (x + x + w) / 2.0
    lo_l = int(round(xc - HEAD_LINE_ROW_BAND_SPACES[1] * spacing))
    hi_l = int(round(xc - HEAD_LINE_ROW_BAND_SPACES[0] * spacing))
    lo_r = int(round(xc + HEAD_LINE_ROW_BAND_SPACES[0] * spacing))
    hi_r = int(round(xc + HEAD_LINE_ROW_BAND_SPACES[1] * spacing))
    keep = np.ones(y1 - y0, dtype=bool)
    for i, yy in enumerate(range(y0, y1)):
        left = ink[yy, max(0, lo_l):max(0, hi_l)]
        right = ink[yy, max(0, lo_r):min(W, hi_r)]
        if left.size and right.size \
                and left.mean() >= HEAD_LINE_ROW_FILL \
                and right.mean() >= HEAD_LINE_ROW_FILL:
            keep[i] = False
    lost = int((~keep).sum())
    if lost > HEAD_LINE_ROWS_MAX_LOST * keep.size or keep.sum() < 3:
        return None
    region = ink[y0:y1, x0:x1]
    dx = int(round(NOTEHEAD_INK_CENTER_SHRINK * (x1 - x0)))
    dy = int(round(NOTEHEAD_INK_CENTER_SHRINK * (y1 - y0)))
    cx0, cx1 = dx, (x1 - x0) - dx
    cy0, cy1 = dy, (y1 - y0) - dy
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    rows = np.arange(y1 - y0)
    in_core_rows = (rows >= cy0) & (rows < cy1) & keep
    core = region[in_core_rows][:, cx0:cx1]
    outer_rows = region[keep]
    if core.size == 0:
        return None
    center = float(core.sum()) / float(core.size)
    ring_area = outer_rows.size - core.size
    ring = (float(int(outer_rows.sum()) - int(core.sum())) / float(ring_area)
            if ring_area > 0 else None)
    windows = {"center": center, "ring": ring}
    measured = {k: v for k, v in windows.items() if v is not None}
    best_key = max(measured, key=lambda k: measured[k])
    return {"best": round(measured[best_key], 4), "best_window": best_key,
            "windows": {k: (None if v is None else round(v, 4))
                        for k, v in windows.items()},
            "line_rows_left_out": lost}


#: ROADMAP 2.161: a head with its ink bridge to a stem stays one head wide -- 2.148's own head-sized width ceiling
#: (`rhythm.HEAD_BOX_MAX_WIDTH_SPACES`), restated here and pinned equal by a test, not a new number.
STEM_BRIDGE_MAX_HEAD_WIDTH_SPACES = 1.9
#: Detector boxes that, lying in the gap between a head box and a stem, make the ink there someone else's.
_STEM_BRIDGE_BLOCKERS = ("notehead", "accidental", "flag", "rest")


def head_stem_bridge(ink: Any, head_box: Tuple[float, float, float, float], stems: Sequence[Any], space: float,
                     others: Sequence[Tuple[str, Tuple[float, float, float, float]]] = ()) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.161 (Sean 2026-10-17: "I'm not sure why it doesn't see simple half notes"). Does THIS head's own ink reach a
    stem that stands beside its detector box without touching it?

    CONVENTION (CLAUDE.md §5, page-facts): a stem stands flush with its head's edge (up -> right, down -> left), so the
    head's ink runs into the stem. MEASURED on the 20261016-night records: 9 of the 32 Litolff real-note heads the fill
    reader left unread with no stem had a stem the stem finder FOUND standing 0.13-0.27 sp beside a detector box that
    stops short of the head's stem side (the slanted Litolff half's thin tip), so `stem_touches_head` (box overlap) saw
    no stem.

    `ink`: the cell's ERASED raster as a stem-finder mask (255/True = ink: `line_detection._binary_ink(image_no_staff)`,
    the raster the stems were read on, so an erased staff line cannot bridge); `head_box`, `stems` (x, y, w, h) canonical
    cell boxes; `others`: `(name, box)` of the cell's OTHER detections. A stem qualifies when it does not touch the box,
    its rows overlap the box's rows, and the head with the gap stays one head wide (`STEM_BRIDGE_MAX_HEAD_WIDTH_SPACES`);
    the gap is BRIDGED when, on at least one row of the box, every pixel between the box edge and the stem's near edge is
    ink, and no other notehead / accidental / flag / rest box lies in the gap. The nearest bridged stem is returned with
    the box extended to it (`bridged_box`); `None` when no stem qualifies. A ruler reading: whether it is the head's own
    stem is ADJUDICATE's."""
    import numpy as _np
    if ink is None or getattr(ink, "ndim", 0) != 2 or not space or space <= 0:
        return None
    from .geometry import stem_touches_head
    hx, hy, hw, hh = (float(v) for v in head_box)
    if hw <= 0 or hh <= 0:
        return None
    H, W = ink.shape
    best = None
    for st in stems:
        sx, sy, sw, sh = (float(v) for v in st)
        if stem_touches_head((sx, sy, sw, sh), (hx, hy, hw, hh)):
            continue
        if not (sy < hy + hh and sy + sh > hy):
            continue
        if sx + sw / 2.0 < hx + hw / 2.0:
            side, g0, g1 = "left", sx + sw, hx
        else:
            side, g0, g1 = "right", hx + hw, sx
        gap = g1 - g0
        if gap <= 0 or hw + gap > STEM_BRIDGE_MAX_HEAD_WIDTH_SPACES * space:
            continue
        if any(str(n).lower().startswith(_STEM_BRIDGE_BLOCKERS)
               and b[0] < g1 and b[0] + b[2] > g0 and b[1] < hy + hh and b[1] + b[3] > hy for n, b in others):
            continue
        c0, c1 = int(_np.floor(g0)), int(_np.ceil(g1))
        r0, r1 = int(round(hy)), int(round(hy + hh))
        if c0 < 0 or c1 > W or r0 < 0 or r1 > H or c1 <= c0 or r1 <= r0:
            continue
        strip = _np.asarray(ink[r0:r1, c0:c1]) > 0
        rows = int(strip.all(axis=1).sum())
        if rows < 1:
            continue
        stem_below = sy + sh > hy + hh
        stem_above = sy < hy
        cand = {"side": side, "gap_sp": round(gap / space, 3), "bridge_rows": rows, "rows_read": r1 - r0,
                "stem_box": [round(sx, 2), round(sy, 2), round(sw, 2), round(sh, 2)],
                "stem_below": bool(stem_below), "stem_above": bool(stem_above),
                "bridged_box": ([round(g0, 2), round(hy, 2), round(hx + hw - g0, 2), round(hh, 2)] if side == "left"
                                else [round(hx, 2), round(hy, 2), round(g1 - hx, 2), round(hh, 2)])}
        if best is None or gap < best["gap_sp"] * space:
            best = cand
    return best


def gather_notehead_ink(log: Log, cells: Sequence[Any],
                        local: Dict[int, Tuple[int, int]],
                        detections: Dict[str, List[Any]],
                        pws: Any = None) -> None:
    """`Q.NOTEHEAD_INK` on every notehead-classed glyph. ROADMAP 2.23
    (ported, GATHER half only, from `claude/no-ink-head-2.6h`, `a8394476`).

    ⚠️ THE WITNESS FOR THE HEAD'S OWN FILL, NOT ONLY WHETHER IT EXISTS.
    `a8394476` built this measurement to ask "is there ink at all under this
    box" (`no_ink_under_box`, refused as dead-at-zero and NOT ported here).
    `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §17b asks a
    different question of the SAME measurement: on Litolff 1/i the single
    biggest minimal-fix class over the whole movement's held bars is `F`
    (300 bars) — a hollow (half/whole) notehead read as BLACK on this
    MERGING plate (CLAUDE.md §10). `rhythm.adjudicate_duration` reads this
    row to NARROW a head's fill where the ink disagrees decisively with the
    detector's class.

    ⚠️ BOTH RASTERS, ON PURPOSE, AND NEITHER ONE ALONE IS SAFE:

      - `cell.binary` — the UNERASED canonical raster (0 = ink, the SAME
        side-channel `staff_line_removal.remove_staff_lines_from_cell`
        reuses rather than re-binarizing) — is read because a REAL head
        standing ON a staff line must not read as blank because the line
        was erased.
      - `cell.image_no_staff` — the ERASED raster `gather_ink`/
        `gather_ledger_ink` already read — is the CHECK: staff-line pixels
        ALONE, crossing an otherwise blank box, must not read as ink.

    `detail["ink_raw"]`/`detail["ink_net"]` carry each `notehead_ink_under`
    reading whole, never collapsed to one number.

    ⚠️ NO STAFF UNIT NEEDED FOR THE RAW BOX, so this reader never abstains
    `no_staff_geometry` — only `no_mask` where BOTH rasters are missing.

    ⚠️⚠️ ROADMAP 2.39b — THE WINDOW IS THE RE-CENTRED STANDARD BOX WHERE ONE
    EXISTS. `gather_notehead_recentre` runs earlier in this same GATHER pass
    and files `Q.NOTEHEAD_RECENTRE` for every REGULAR notehead whose
    matched-window search found (not merely assumed) where the head's own
    ink actually peaks; this reader READS that row (CLAUDE.md rule 6 —
    connect, never re-derive) rather than calling the search a second time.
    Falls back to the RAW detector box — never the un-re-centred standard
    box `benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §18 measured
    reading a solid Brahms head as hollow — wherever the re-centre declined,
    never ran (no measured line grid) or does not apply (a whole note,
    grace/cue head, or any class outside `geometry.is_regular_notehead`).
    """
    page_binary = getattr(getattr(pws, "page", None), "binary", None)
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        idx = [gi for gi, d in enumerate(dets)
               if str(d.smufl_name).lower().startswith("notehead")]
        if not idx:
            continue
        frame = frame_cell(c.measure_index)
        raw_img = getattr(c, "binary", None)
        net_img = getattr(c, "image_no_staff", None)
        grid = _cell_grid(c)
        space_canonical = grid[1] * 2.0 if grid and grid[1] else None
        # ROADMAP 2.161: the cell's stems (`gather_cv_lines` ran earlier in this pass) and its erased raster as the stem
        # finder's own mask, for `head_stem_bridge`; built once per cell, only where a head has no stem touching its box.
        bridge_stems = [tuple(float(v) for v in r.value) for r in log.rows(Q.STEM, sub)
                        if isinstance(r.value, (list, tuple)) and len(r.value) == 4]
        bridge_ink = None
        bridge_space = space_canonical      # = `Q.CELL_STAFF_SPACE` (half_step x 2), the unit ADJUDICATE reads
        for gi in idx:
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            d = dets[gi]
            box = (d.x_canonical, d.y_canonical,
                  d.width_canonical, d.height_canonical)
            stem_bridge = None
            if bridge_stems and net_img is not None and bridge_space:
                from .geometry import stem_touches_head as _touches
                det_box = tuple(float(v) for v in box)
                if not any(_touches(st, det_box) for st in bridge_stems):
                    if bridge_ink is None:
                        from ..line_detection import _binary_ink
                        bridge_ink = _binary_ink(net_img)
                    others = [(str(o.smufl_name), (float(o.x_canonical), float(o.y_canonical), float(o.width_canonical),
                                                   float(o.height_canonical))) for oi, o in enumerate(dets) if oi != gi]
                    stem_bridge = head_stem_bridge(bridge_ink, det_box, bridge_stems, bridge_space, others)
                    if stem_bridge is not None:
                        stem_bridge["interior_white_bridged"] = head_interior_white(raw_img, stem_bridge["bridged_box"]) \
                            if raw_img is not None else None
            interior = head_interior_white(raw_img, box) if raw_img is not None else None   # 2.148: the DETECTOR's own box
            located_by = None   # 2.159: the earlier reader that LOCATED the head, so the window below is not the detector's
            if space_canonical and is_regular_notehead(str(d.smufl_name)):
                recentred = log.rows(Q.NOTEHEAD_RECENTRE, g)
                if recentred:
                    located_by = "notehead_recentre"
                    dx_sp, dy_sp = recentred[-1].value
                    ncx = float(d.x_center) + dx_sp * space_canonical
                    ncy = float(d.y_center) + dy_sp * space_canonical
                    bx0, bx1, by0, by1 = _standard_head_box(
                        ncx, ncy, space_canonical)
                    box = (bx0, by0, bx1 - bx0, by1 - by0)
            # ⚠️ ROADMAP 2.73. A box that is half a head cut by a line reads
            # the ink of HALF a ring; where `gather_head_line_cut` found the
            # mirror hole, the head is the standard box centred on the line
            # and that is the box whose fill is read (the row is cited in the
            # detail, the detector's own box untouched on `Q.GLYPH_BOX`).
            cut_rows = log.rows(Q.HEAD_LINE_CUT, g)
            box_source = None
            if cut_rows:
                cv = cut_rows[-1].value
                if isinstance(cv, (list, tuple)) and len(cv) == 4:
                    box = tuple(float(v) for v in cv)
                    box_source = cut_rows[-1].id
                    located_by = "head_line_cut"
            # ⚠️ ROADMAP 2.115 (flag `OMR_RECENTRE_PART_BOXED`, default ON): a
            # box that is only PART of its head (2.39b's search declined it or
            # never ran: it is not under 0.7) is moved vertically onto its
            # head's own ink before the inside is read. Only THIS reader's window
            # moves; no `Q.NOTEHEAD_RECENTRE` row is filed, so no other reader
            # sees a different box. The reading is filed in the detail, taken or
            # declined, with the margins.
            #
            # ⚠️ ROUND 2 (Sean 2026-10-14): THE PAGE'S OWN RASTER, NOT THE CELL.
            # The cell's canonical `binary` is the page slice resized, and there
            # a part-boxed head merges with its stem and the next staff line (tile
            # 13: centroid shift 0.00/0.15/0.57 sp across windows -> `unstable`,
            # nothing moved). The decision AND the interior it feeds are read off
            # `pws.page.binary` at the head's page box (`_page_box`, the mapping
            # `Q.GLYPH_BOX` files), the staff lines at the head's own x left out
            # as rows (2.73). Declined `no_page_raster` where the page, its
            # mapping or its staff unit is missing -- never read from the cell.
            part_boxed = None
            page_reads = None
            if (part_boxed_recentre_enabled() and box_source is None
                    and space_canonical and is_regular_notehead(str(d.smufl_name))
                    and not log.rows(Q.NOTEHEAD_RECENTRE, g)):
                part_boxed = recentre_part_boxed_on_page(
                    c, d, page_binary, space_canonical)
                if part_boxed is not None and part_boxed["accepted"]:
                    ncx = box[0] + box[2] / 2.0
                    ncy = box[1] + box[3] / 2.0 \
                        + part_boxed["dy_sp"] * space_canonical
                    bx0, bx1, by0, by1 = _standard_head_box(
                        ncx, ncy, space_canonical)
                    box = (bx0, by0, bx1 - bx0, by1 - by0)
                    box_source = "part_boxed_recentre"
                    located_by = "part_boxed_recentre"
                    page_reads = part_boxed.pop("_page_reads")
            m_raw = notehead_ink_under(raw_img, box) \
                if raw_img is not None else None
            m_net = notehead_ink_under(net_img, box) \
                if net_img is not None else None
            if page_reads is not None and page_reads[0] is not None:
                m_raw = page_reads[0]
            # ⚠️ ROADMAP 2.73: the same reading with the LINE ROWS left out --
            # a line through a hollow head's hole must not read as fill. A
            # third reading beside the other two, never a replacement.
            m_off = (notehead_ink_off_line(raw_img, box, space_canonical)
                     if raw_img is not None and space_canonical else None)
            if page_reads is not None and page_reads[1] is not None:
                m_off = page_reads[1]
            if m_raw is None and m_net is None:
                log.abstain(g, Q.NOTEHEAD_INK, reader=READERS.CV_NOTEHEAD_INK,
                           frame=frame, reason=ABSTAIN.NO_MASK,
                           note="cell carries no binary/image_no_staff")
                continue
            value = max(m["best"] for m in (m_raw, m_net) if m is not None)
            extra: Dict[str, Any] = {}
            if m_off is not None:
                extra["ink_off_line"] = m_off
            if box_source is not None:
                extra["box_source"] = box_source
            if page_reads is not None:
                extra["ink_frame"] = "page"
            if part_boxed is not None and part_boxed["reason"] != "box_head_sized":
                extra["part_boxed"] = part_boxed
            if interior is not None:
                extra["interior_white"] = interior
            if located_by is not None:
                located = head_interior_white_located(c, box, page_binary, located_by)
                if located is not None:
                    extra["interior_white_located"] = located
            if stem_bridge is not None:
                extra["stem_bridge"] = stem_bridge
            log.observe(g, Q.NOTEHEAD_INK, round(value, 4),
                       reader=READERS.CV_NOTEHEAD_INK, frame=frame,
                       ink_raw=m_raw, ink_net=m_net, **extra)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.42 -- stacked heads on one stem: how many, and where.
#
# Supersedes 2.40's pair-wise `same_side_second` rule (which could refuse a
# duplicate box but had no way to answer "how many heads does this whole
# group hold" -- `cell/3/1/2/9`, four overlapping boxes on one stem, two real
# heads) and absorbs 2.41's measurement-only two-head fit
# (`benchmarks/omr-notehead-width-2026-09/probe/measure_2.41.py`'s
# `two_head_fit`), generalised to 1/2/3 heads and wired for real. See
# `Q.STACKED_HEAD_FIT`'s own docstring in `record.py` for the full design.
# ─────────────────────────────────────────────────────────────────────────────

#: A third or more (2 half-step position units) -- Sean, 2026-09-30: "a
#: second is always on opposite sides of the stem", so two heads on the
#: SAME side of one stem are never a second; the smallest real interval
#: same-side is a third. `notehead_precision.NOTEHEAD_SAME_SIDE_MAX_DY_
#: STAFF_SPACES` (0.75 sp = 1.5 position units) is the SAME boundary stated
#: in staff spaces; this is the position-unit form the fit's integer grid
#: needs, restated (not imported -- `notehead_precision` imports THIS
#: module, so the reverse import would be a cycle, the same reason
#: `notehead_precision._stem_xywh` restates `rhythm._xywh`).
STACKED_HEAD_MIN_GAP_POSITIONS = 2

#: The fit does not move to `k+1` heads unless the MEAN per-head ink score at
#: `k+1` beats the mean score at `k` by more than this. Sean set the
#: same-side/opposite-side boundary by convention (DECISIONS 2026-09-30),
#: not a fitted margin on this population; this number is the SAME stated
#: margin discipline `Q.NOTEHEAD_RECENTRE`'s own `RECENTRE_MIN_MARGIN` uses
#: for an analogous "is the winner clearly ahead" test, not independently
#: fitted here. Where two counts are within this margin of each other, the
#: fit ABSTAINS `ambiguous` (CLAUDE.md §4a) rather than guessing.
STACKED_HEAD_FIT_MARGIN = 0.05

#: An additional head's own fitted slot must score above this absolute fill
#: fraction to count as real ink, not blank paper -- `benchmarks/omr-
#: notehead-width-2026-09/probe/measure_2.41.py`'s `two_head_fit`'s own
#: `0.4` floor for `supports_two_heads`, cited rather than re-measured here
#: (this item did not re-run that probe's own calibration).
STACKED_HEAD_MIN_SLOT_FILL = 0.4

#: How many candidate half-step positions the search adds on EITHER side of
#: the group's own observed box span -- a bounded search around the group's
#: own ink, never an unbounded scan of the staff (the same discipline
#: `reading_c`'s own comment gives for the identical reason: an unbounded
#: search reaches a different note entirely).
STACKED_HEAD_SEARCH_MARGIN_POSITIONS = 1


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.129 -- a second head the MEAN test turned away, kept where the INK
# is two heads tall. `OMR_STACKED_SECOND_HEAD`, default ON (landed 2026-10-14).
#
# Brahms 20261013-night, pdf 0 (Sean's every-head truth): 5 of 5 notes lost to
# `stacked_head_duplicate` were the second head of a chord of THIRDS on one side
# of one stem (two heads one staff space apart, touching). The fit read k=1 for
# all five: the slots scored 1.00 / 1.00 / 0.86 (the middle slot saturates on the
# blob; the lower head's own slot loses its centre to staff-line removal), so the
# pair's mean (0.93) fell 0.068 under the lone best score and the "adding it cost
# explanatory power" gate (`STACKED_HEAD_FIT_MARGIN`) refused it. The mean is a
# bad witness for two heads that TOUCH: a saturated blob scores the same wherever
# the second slot goes. The ink height is not -- two touching heads are 2.0
# spaces tall, one head 1.0-1.3.
# ─────────────────────────────────────────────────────────────────────────────

#: Half width of the column band read for the blob's height, in staff spaces
#: either side of the heads' x -- 0.2 of the standard head width, the middle of
#: the head, clear of the stem (at the head's edge) and of an augmentation dot.
STACKED_BLOB_HALF_WIDTH_SPACES = 0.28

#: A row is blob ink where this fraction of the band's pixels are ink.
STACKED_BLOB_ROW_FILL = 0.3

#: A gap of this many spaces inside the blob is bridged (the tangent between two
#: touching ellipses; a staff-line removal that cut a head across).
STACKED_BLOB_BRIDGE_SPACES = 0.2

#: The blob must reach this fraction of the height two heads at the pair's own
#: spacing would have (`gap/2 + 1` spaces: 2.0 for a third, so 1.6). Measured IN
#: THE CELL (the staff-line-removed raster the fit reads) on Brahms pdf 0: the 5
#: twins read 1.74-2.23 spaces -- SHORTER than on the page raster (2.17-2.39),
#: so a 1.8 cut calibrated on the page lost 3 of the 5 -- and the pairs that are
#: not two heads read 0.6-1.3 on the page. A head with a ledger line or a slur
#: touching it reads up to 1.76 in the cell (Brahms pdf 1), so the blob is the
#: SECOND witness, never the first: see `STACKED_BOX_SPREAD_MIN_POSITIONS`.
STACKED_BLOB_MIN_FRACTION = 0.8

#: The detector's OWN boxes must stand at two heads' distance: the lowest and
#: highest box of the group at least this many half-steps apart (a third is 2;
#: the twins' boxes read 1.89-2.12 apart, the two false near-misses on Brahms
#: pdf 1 -- one head boxed twice, plus a ledger line -- 0.38 and 0.40). The first
#: witness: the fit never adds a head the detector did not box at a second
#: head's place.
STACKED_BOX_SPREAD_MIN_POSITIONS = 1.5

#: Each of the pair's two slots must hold this much ink (the existing floor is
#: 0.4 + margin; the twins' weaker slot reads 0.81-0.89, a head on blank paper
#: or a neighbour's edge well under).
STACKED_BLOB_MIN_SLOT_FILL = 0.75

#: How far above and below the pair's midpoint the column is read (spaces).
STACKED_BLOB_WINDOW_SPACES = 2.5


def stacked_second_head_enabled() -> bool:
    """`OMR_STACKED_SECOND_HEAD` -- ROADMAP 2.129. **Default ON** (landed
    2026-10-14, Sean: "1 land"); an explicit `0/false/no/off` turns it off."""
    return os.environ.get("OMR_STACKED_SECOND_HEAD", "1").strip().lower() \
        not in ("0", "false", "no", "off")


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.132 -- a HOLLOW second head a third apart. `OMR_STACKED_HOLLOW_PAIR`,
# default OFF until Sean sees `out/print/2.132-review/`.
#
# 2.129's blob test reads a solid column, which a hollow head's hole is not, so
# two half notes a third apart on one stem (Sean's 2.129 tile 9) were refused
# `stacked_head_duplicate`. 19 such chords stand refused on Brahms. The two-holes
# reading that would keep them ALSO passes the "8" of a printed 9/8 (two white
# loops, 1.0 space apart, ring 0.71 / 0.62: Brahms glyph/0/0/11/7/1 -- the 2.129
# FINDINGS called it a bass clef; it is the numeral, a crop settles it). What
# tells the numeral from two heads is the STEM: a chord's stem runs 2.2-4.0
# spaces PAST the pair (the engraving convention is 3.5 from the far head), and
# the numeral's "stem" row is the numeral's own height (0.15 past). Two
# witnesses, two sources: the PAGE RASTER (each slot a hollow head: an empty
# interior inside an inked ring, the staff-line rows left out, 2.73/2.88) and
# the STEM READER. Never the bar sum.
# ─────────────────────────────────────────────────────────────────────────────

#: `rhythm.HEAD_FILL_HOLLOW_CENTER_MAX` / `HEAD_FILL_HOLLOW_RING_GAP_MIN` (2.23),
#: restated (`rhythm` imports this module): a slot reads hollow where the
#: interior is no denser than this and the ring stands this far above it.
STACKED_HOLLOW_CENTER_MAX = 0.75
STACKED_HOLLOW_RING_GAP_MIN = 0.10
#: ... and the ring is real ink, not paper: the 19 pairs read 0.58-0.78 at their
#: slots, a slot moved a half-step reads 0.2-0.5.
STACKED_HOLLOW_RING_MIN = 0.55
#: The stem must run at least this many spaces past the OUTER edge of the pair's
#: slots (either end). Real chords 2.22-3.98 (Brahms, 19 pairs), the "8" 0.15,
#: a bass clef 0.13.
STACKED_HOLLOW_STEM_EXT_MIN_SPACES = 1.5
#: The group's own boxes: lowest to highest at most this many half-steps apart
#: (a third is 2; a chord of THREE heads is 4 and is not a pair).
STACKED_HOLLOW_MAX_SPREAD_POSITIONS = 3.0
#: Two placements of the pair that both read hollow must differ by this much in
#: (ring - centre) to choose between them; otherwise the slots are ambiguous.
STACKED_HOLLOW_SLOT_MARGIN = 0.10


def stacked_hollow_pair_enabled() -> bool:
    """`OMR_STACKED_HOLLOW_PAIR` -- ROADMAP 2.132. **Default OFF** (Sean has not
    seen the tiles); `1/true/yes/on` turns it on."""
    return os.environ.get("OMR_STACKED_HOLLOW_PAIR", "0").strip().lower() \
        in ("1", "true", "yes", "on")


def _stacked_hollow_slot_ok(win: Optional[Tuple[float, float]]) -> bool:
    if win is None:
        return False
    center, ring = win
    if center is None or ring is None:
        return False
    return (center <= STACKED_HOLLOW_CENTER_MAX
            and ring - center >= STACKED_HOLLOW_RING_GAP_MIN
            and ring >= STACKED_HOLLOW_RING_MIN)


def fit_hollow_stacked_pair(slot_reader: Any, candidates: Sequence[int],
                            stem_extension_fn: Any) -> Dict[str, Any]:
    """PURE -- ROADMAP 2.132. Is this a pair of hollow heads a third apart?

    `candidates` are the lower-slot positions `p` (the pair is `p`, `p+2`) the
    detector's own boxes allow. `slot_reader(p)` returns `(centre, ring)` of the
    standard head box at slot `p` read off the PAGE raster with the line rows
    left out, or `None`. `stem_extension_fn(p)` the spaces the group's stem runs
    past the pair's outer edge, or `None` (no stem / no unit).

    Returns `{"accepted": bool, "positions": (p, p+2) | None, "margin": float |
    None, "near_miss": {...}}` -- a refusal says how close it came (2.106)."""
    scored = []
    reads = {}
    for p in candidates:
        lo, hi = slot_reader(p), slot_reader(p + 2)
        reads[p] = (lo, hi)
        if _stacked_hollow_slot_ok(lo) and _stacked_hollow_slot_ok(hi):
            scored.append((min(lo[1] - lo[0], hi[1] - hi[0]), p))
    if not scored:
        best = None
        for p in candidates:
            lo, hi = reads[p]
            if lo is None or hi is None or lo[0] is None or hi[0] is None:
                continue
            g = min(lo[1] - lo[0], hi[1] - hi[0])
            if best is None or g > best[0]:
                best = (g, p, lo, hi)
        nm: Dict[str, Any] = {"hollow_pair": "slots are not both hollow",
                              "candidates": len(candidates)}
        if best is not None:
            nm["best_positions"] = [best[1], best[1] + 2]
            nm["best_windows"] = [[round(v, 3) for v in best[2]],
                                  [round(v, 3) for v in best[3]]]
        return {"accepted": False, "positions": None, "margin": None,
                "near_miss": nm}
    scored.sort(reverse=True)
    top_gap, top_p = scored[0]
    if len(scored) > 1 and top_gap - scored[1][0] < STACKED_HOLLOW_SLOT_MARGIN:
        return {"accepted": False, "positions": None, "margin": None,
                "near_miss": {"hollow_pair": "slot placement ambiguous",
                              "placements": [[p, p + 2] for _, p in scored[:2]],
                              "gap_margin": round(top_gap - scored[1][0], 3)}}
    ext = stem_extension_fn(top_p)
    lo, hi = reads[top_p]
    nm = {"hollow_pair": "both slots hollow", "positions": [top_p, top_p + 2],
          "windows": [[round(v, 3) for v in lo], [round(v, 3) for v in hi]],
          "stem_extension_spaces": (round(ext, 3) if ext is not None else None),
          "stem_needed_spaces": STACKED_HOLLOW_STEM_EXT_MIN_SPACES}
    if ext is None or ext < STACKED_HOLLOW_STEM_EXT_MIN_SPACES:
        nm["hollow_pair"] = ("no stem stands at the pair's edge" if ext is None
                             else "stem does not run past the pair")
        return {"accepted": False, "positions": None, "margin": None,
                "near_miss": nm}
    return {"accepted": True, "positions": (top_p, top_p + 2),
            "margin": round(min(top_gap, ext - STACKED_HOLLOW_STEM_EXT_MIN_SPACES), 4),
            "near_miss": nm}


def stacked_blob_height_spaces(img: Any, cx: float, mid_y: float,
                               spacing: float) -> Optional[float]:
    """PURE -- the height, in staff spaces, of the one inked column that runs
    through `mid_y` at the heads' own x. `img` is a cell raster (0 == ink),
    `cx`/`mid_y` in that raster's frame, `spacing` its staff space.

    The column is `STACKED_BLOB_HALF_WIDTH_SPACES` either side of `cx`; a row is
    ink where `STACKED_BLOB_ROW_FILL` of it is; the run through `mid_y` bridges
    gaps up to `STACKED_BLOB_BRIDGE_SPACES`. `None` where the band cannot be cut
    from the raster (off it, or too thin) -- declined, never defaulted. 0.0 where
    there is no ink at `mid_y` at all."""
    if img is None or getattr(img, "ndim", 0) != 2 or spacing <= 0:
        return None
    H, W = img.shape
    hw = STACKED_BLOB_HALF_WIDTH_SPACES * spacing
    x0, x1 = int(round(cx - hw)), int(round(cx + hw))
    y0 = int(round(mid_y - STACKED_BLOB_WINDOW_SPACES * spacing))
    y1 = int(round(mid_y + STACKED_BLOB_WINDOW_SPACES * spacing))
    if x0 < 0 or x1 > W or y0 < 0 or y1 > H or x1 - x0 < 2 or y1 - y0 < 2:
        return None
    rows = (img[y0:y1, x0:x1] == 0).mean(axis=1) >= STACKED_BLOB_ROW_FILL
    bridge = max(1, int(round(STACKED_BLOB_BRIDGE_SPACES * spacing)))
    n = len(rows)
    ym = min(n - 1, max(0, int(round(mid_y)) - y0))
    # the nearest ink row to the midpoint, within the bridge
    start = None
    for d in range(0, bridge + 1):
        for yy in (ym - d, ym + d):
            if 0 <= yy < n and rows[yy]:
                start = yy
                break
        if start is not None:
            break
    if start is None:
        return 0.0
    top = bot = start
    gap = 0
    for yy in range(start - 1, -1, -1):
        if rows[yy]:
            top, gap = yy, 0
        else:
            gap += 1
            if gap > bridge:
                break
    gap = 0
    for yy in range(start + 1, n):
        if rows[yy]:
            bot, gap = yy, 0
        else:
            gap += 1
            if gap > bridge:
                break
    return (bot - top + 1) / float(spacing)


def _stacked_slots_have_boxes(positions: Sequence[int],
                              observed: Sequence[float]) -> bool:
    """The detector drew a box at each of the pair's two heads -- the group's
    lowest box (smallest position) within one half-step of the lower slot, its
    highest within one of the upper, and the two at least
    `STACKED_BOX_SPREAD_MIN_POSITIONS` apart. One head boxed twice (spread
    ~0.4) can never pass, whatever the ink says."""
    if len(observed) < 2 or len(positions) != 2:
        return False
    lo, hi = min(observed), max(observed)
    return (hi - lo >= STACKED_BOX_SPREAD_MIN_POSITIONS
            and abs(lo - positions[0]) <= 1.0
            and abs(hi - positions[1]) <= 1.0)


def _stacked_stem_xywh(value: Any) -> Optional[Tuple[float, float, float, float]]:
    """`Q.STEM`'s own value shape, `[x, y, w, h]` -- restated (not imported)
    from `notehead_precision._stem_xywh` for the same reason that module
    restates `rhythm._xywh`: the reverse import would be a cycle
    (`notehead_precision` imports `gather`, inline, already)."""
    if not isinstance(value, (list, tuple)) or len(value) < 4:
        return None
    return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))


def _stacked_boxes_overlap(a: Tuple[float, float, float, float],
                          b: Tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw and ax + aw >= bx
            and ay <= by + bh and ay + ah >= by)


def _stacked_side(stem_xywh: Tuple[float, float, float, float],
                  box_xywh: Tuple[float, float, float, float]) -> str:
    """Which side of the stem's OWN centre x this box's centre sits on --
    `notehead_precision._same_side_candidates`'s exact test, restated."""
    scx = stem_xywh[0] + stem_xywh[2] / 2.0
    cx = box_xywh[0] + box_xywh[2] / 2.0
    return "right" if cx >= scx else "left"


#: ⚠️⚠️ MANAGER REVIEW (real Litolff p3 ruler measurement, `glyph/3/0/0/2/4`
#: + `/9`): a floating-point score comparison (`>`) is not the same test as
#: "equal within rounding", and the gap between them was the whole bug. On a
#: MERGING plate (CLAUDE.md §10) a chord's ink is often one continuous
#: blob, and `notehead_ink_under` rounds its `best` fill to 4 decimals, so
#: SEVERAL adjacent candidate positions score EXACTLY 1.0 -- on this real
#: cell, -8/-7/-6/-5 all did. `itertools.combinations` enumerates pairs
#: lexicographically (every pair starting `-9,-8,...` before any starting
#: `-7,...`), so `total > best[1]` (strict) kept the FIRST-GENERATED tied
#: pair, `(-8, -6)`, not the print-true `(-7, -5)` -- both are real
#: THIRDS (gap 2), so the bug was invisible to the gap/margin tests and
#: silently shifted BOTH heads up one diatonic step (F6/D6 -> G6/E6). The
#: raw DETECTOR centres for this exact cell (`Q.NOTEHEAD_STAFF_POSITION`
#: -7.4 / -5.56) were already close to the truth -- the fit's own tie-break
#: is what threw them off, not the ink measurement or the gap logic.
TIE_SCORE_EPS = 1e-6


def _closest_assignment_cost(positions: Tuple[int, ...],
                             observed: Sequence[float]) -> float:
    """Sum, over every OBSERVED (raw detector) position in this group, of
    its distance to the nearest position in `positions` -- a real-evidence
    tie-break (CLAUDE.md rule 6: connect to what the detector already
    localised, never guess) for combos that score identically."""
    if not observed:
        return 0.0
    return sum(min(abs(o - p) for p in positions) for o in observed)


def _stacked_best_combo(scored: Dict[int, float], k: int,
                        observed: Sequence[float] = ()
                        ) -> Optional[Tuple[Tuple[int, ...], float]]:
    """The best `k` positions from `scored`'s own keys, pairwise at least
    `STACKED_HEAD_MIN_GAP_POSITIONS` apart, maximising total score. Brute
    force over `itertools.combinations` -- safe here because a stacked
    group's own candidate-position window is small (bounded by
    `STACKED_HEAD_SEARCH_MARGIN_POSITIONS` around a handful of overlapping
    boxes, never the whole staff) and `k` never exceeds 3.

    ⚠️ EVERY COMBO WITHIN `TIE_SCORE_EPS` OF THE TOP SCORE IS COLLECTED,
    not just the first found -- see `TIE_SCORE_EPS`'s own comment. Among
    those tied, the one whose positions sit CLOSEST to `observed` (the
    group's own raw detector-box positions, real evidence, never a guess)
    wins; with no `observed` given, or only one tied candidate, the
    lexicographically-first stands (unchanged behaviour where there is no
    tie to break).
    """
    import itertools
    keys = sorted(scored)
    best_total: Optional[float] = None
    tied: List[Tuple[int, ...]] = []
    for combo in itertools.combinations(keys, k):
        if any(combo[i + 1] - combo[i] < STACKED_HEAD_MIN_GAP_POSITIONS
               for i in range(len(combo) - 1)):
            continue
        total = sum(scored[p] for p in combo)
        if best_total is None or total > best_total + TIE_SCORE_EPS:
            best_total = total
            tied = [combo]
        elif abs(total - best_total) <= TIE_SCORE_EPS:
            tied.append(combo)
    if not tied or best_total is None:
        return None
    if len(tied) == 1 or not observed:
        return (tied[0], best_total)
    chosen = min(tied, key=lambda c: _closest_assignment_cost(c, observed))
    return (chosen, best_total)


def fit_stacked_head_count(img: Any, cx: float, positions: List[int],
                          top_y: float, half_step: float, spacing: float,
                          n_boxes: int, observed: Sequence[float] = (),
                          blob_height_fn: Optional[Any] = None,
                          hollow_pair_fn: Optional[Any] = None
                          ) -> Optional[Dict[str, Any]]:
    """PURE -- score a standard head-box template at every candidate
    position (an integer half-step grid, `Q.NOTEHEAD_STAFF_POSITION`'s own
    units), then pick the FEWEST head count (1, 2 or 3, never more than
    `n_boxes`) that explains the ink.

    ⚠️ NOT "does k+1's MEAN beat k's mean" -- that test is measured WRONG
    on a real two-head fixture (kept as `test_staged_stacked_head_fit.
    TestFitStackedHeadCountPure`'s own comment): the single BEST-scoring
    position is, by construction, one member of whatever pair a genuine
    dyad's own two heads form, so the pair's mean is never CLEARLY better
    than the lone best score, only AS good -- a "k+1 beats k" test would
    never fire on a real dyad. The working test is 2.41's own `two_head_
    fit.supports_two_heads` (`benchmarks/omr-notehead-width-2026-09/probe/
    measure_2.41.py`), cited and generalised to a third head: an
    additional head is real where ITS OWN fitted slot clears an absolute
    fill floor (`STACKED_HEAD_MIN_SLOT_FILL` -- real ink, not blank paper)
    AND the group's new mean has not dropped by more than the stated
    margin (adding it did not cost real explanatory power). Both gates
    must clear the SAME margin on either side of their own threshold
    before the fit commits to the extra head; inside that band it
    ABSTAINS `ambiguous` rather than guessing (CLAUDE.md rule 8).

    Returns `None` where no candidate position scores at all -- the window
    itself was off the raster (the caller abstains `no_mask`); a real,
    on-raster window over blank paper scores a genuine `0.0`, which is a
    valid answer here (k=1, zero fill), not a `None`. Otherwise a dict:
    `scored` (every candidate position's own score), `k` (the chosen
    count), `positions` (that count's own chosen head positions,
    ascending), `margin` (how far the LAST accepted head cleared its own
    gates, or `None` at k=1 with no second head considered), `ambiguous`
    (True where the next head's own evidence sits inside the margin band
    -- the caller abstains rather than choosing a count).

    ⚠️⚠️ MANAGER REVIEW (real Litolff p3 ruler measurement): `observed` is
    the group's own RAW detector-box positions (`Q.NOTEHEAD_STAFF_
    POSITION`'s own units, one per member box) -- real evidence, passed
    through to `_stacked_best_combo`'s own tie-break and used here too,
    NEVER to choose a count or a score, only to break an EXACT tie among
    positions/combos that already scored identically (see `TIE_SCORE_EPS`).
    Omitted, ties resolve to the lexicographically/numerically first
    candidate, exactly as before this fix -- which is what silently shifted
    a real pair by one whole diatonic step on a MERGING-plate chord whose
    ink saturates across several adjacent candidate slots.
    """
    scored: Dict[int, float] = {}
    for p in positions:
        ccy = top_y + p * half_step
        box = _standard_head_box(cx, ccy, spacing)
        box_xywh = (box[0], box[2], box[1] - box[0], box[3] - box[2])
        m = notehead_ink_under(img, box_xywh)
        if m is not None:
            scored[p] = m["best"]
    if not scored:
        return None

    # ⚠️⚠️ NOT "does k+1's MEAN beat k's mean" -- measured WRONG on a
    # synthetic two-head fixture before this comment was written: the
    # single BEST position is, by construction, one member of whatever
    # pair a real dyad's own two heads form, so a genuine second head's
    # mean is never CLEARLY better than the lone best score, only AS good.
    # The test that actually works is 2.41's own `two_head_fit.
    # supports_two_heads` (`benchmarks/omr-notehead-width-2026-09/probe/
    # measure_2.41.py`), cited and generalised to a third head here: an
    # additional head is real where its own slot clears an absolute FILL
    # FLOOR (this is genuine ink, not a blank-paper guess) AND the group's
    # mean does not drop by more than the margin (adding it did not cost
    # real explanatory power). Both gates must clear the SAME stated
    # margin on EITHER side of their own threshold before the fit commits;
    # inside that band it is `ambiguous` rather than guessed (rule 8).
    top_score = max(scored.values())
    tied1 = [p for p, v in scored.items() if abs(v - top_score) <= TIE_SCORE_EPS]
    if len(tied1) == 1 or not observed:
        best1_pos = tied1[0]
    else:
        mean_obs = sum(observed) / len(observed)
        best1_pos = min(tied1, key=lambda p: abs(p - mean_obs))
    best1 = scored[best1_pos]
    chosen_k, chosen_positions, chosen_mean = 1, (best1_pos,), best1
    margin: Optional[float] = None
    ambiguous = False
    prev_mean = best1
    second_head_by: Optional[str] = None
    near_miss: Optional[Dict[str, Any]] = None
    for k, n_needed in ((2, 2), (3, 3)):
        if ambiguous or n_boxes < n_needed or chosen_k != k - 1:
            break
        combo = _stacked_best_combo(scored, k, observed)
        if combo is None:
            break
        positions_k, total_k = combo
        mean_k = total_k / k
        min_slot = min(scored[p] for p in positions_k)
        fill_gap = min_slot - STACKED_HEAD_MIN_SLOT_FILL
        mean_gap = mean_k - prev_mean
        if (fill_gap > STACKED_HEAD_FIT_MARGIN
                and mean_gap > -STACKED_HEAD_FIT_MARGIN):
            chosen_k, chosen_positions, chosen_mean = k, positions_k, mean_k
            margin = min(fill_gap, mean_gap if mean_gap < fill_gap else fill_gap)
            prev_mean = mean_k
        elif (blob_height_fn is not None and k == 2
              and fill_gap > STACKED_HEAD_FIT_MARGIN
              and min_slot >= STACKED_BLOB_MIN_SLOT_FILL
              and mean_gap <= -STACKED_HEAD_FIT_MARGIN
              and positions_k[1] - positions_k[0] == STACKED_HEAD_MIN_GAP_POSITIONS
              and _stacked_slots_have_boxes(positions_k, observed)):
            # ⚠️ ROADMAP 2.129 -- the MEAN test refused a pair whose slots both
            # hold real ink and whose boxes are the detector's own. Two heads a
            # third apart TOUCH, so the mean is no witness (see the section
            # comment above); the blob's height is.
            blob = blob_height_fn(positions_k)
            need = ((positions_k[1] - positions_k[0]) * 0.5 + 1.0) \
                * STACKED_BLOB_MIN_FRACTION
            if blob is not None and blob >= need:
                chosen_k, chosen_positions, chosen_mean = k, positions_k, mean_k
                margin = min(fill_gap, blob - need)
                second_head_by = "blob_height"
                near_miss = {"blob_spaces": round(blob, 3),
                             "needed_spaces": round(need, 3)}
                prev_mean = mean_k
            else:
                # REFUSED, and says how close it came (ROADMAP 2.106).
                near_miss = {"positions": list(positions_k),
                             "blob_spaces": (round(blob, 3)
                                             if blob is not None else None),
                             "needed_spaces": round(need, 3),
                             "mean_gap": round(mean_gap, 4),
                             "fill_gap": round(fill_gap, 4)}
                break
        elif (abs(fill_gap) <= STACKED_HEAD_FIT_MARGIN
              or (fill_gap > 0 and abs(mean_gap) <= STACKED_HEAD_FIT_MARGIN)):
            ambiguous = True
            margin = fill_gap
        else:
            break   # clearly not a real additional head -- stop at k-1
    if (hollow_pair_fn is not None and chosen_k == 1 and not ambiguous
            and near_miss is None and n_boxes >= 2 and len(observed) >= 2
            and max(observed) - min(observed) <= STACKED_HOLLOW_MAX_SPREAD_POSITIONS):
        # ⚠️ ROADMAP 2.132 -- HOLLOW groups. The mean test and the blob test are
        # both for filled heads; this is its own pair test (see the section
        # comment), run only where the fit read k=1 and nothing else spoke.
        cands = [p for p in sorted(scored)
                 if p + STACKED_HEAD_MIN_GAP_POSITIONS in scored
                 and _stacked_slots_have_boxes(
                     (p, p + STACKED_HEAD_MIN_GAP_POSITIONS), observed)]
        hp = hollow_pair_fn(cands) if cands else {
            "accepted": False, "near_miss": {
                "hollow_pair": "no slot pair under the boxes"}}
        near_miss = hp["near_miss"]
        if hp["accepted"]:
            chosen_k, chosen_positions = 2, tuple(hp["positions"])
            chosen_mean = sum(scored[p] for p in chosen_positions) / 2.0
            margin = hp["margin"]
            second_head_by = "hollow_pair"
    return {
        "scored": scored, "k": chosen_k,
        "positions": tuple(sorted(chosen_positions)),
        "mean": chosen_mean, "margin": margin, "ambiguous": ambiguous,
        "second_head_by": second_head_by, "near_miss": near_miss,
    }


#: How far (staff spaces) a stem row's centre may stand from the head's edge on
#: the stem's own side and still be THE pair's stem (a stem stands on the head's
#: edge, half a head width from its centre).
STACKED_HOLLOW_STEM_EDGE_TOL_SPACES = 0.5


def _stacked_pair_stems(stems: Sequence[Tuple[float, float, float, float]],
                        cx: float, spacing: float,
                        outer_top: float, outer_bot: float
                        ) -> List[Tuple[float, float, float, float]]:
    """ROADMAP 2.132 -- the stem rows that can be THIS pair's: of the cell's own
    `Q.STEM` rows, those that reach both heads (their y-range covers the middle
    third of the pair's outer span) and stand at EITHER edge of the heads (half a
    head width from the centre, within `STACKED_HOLLOW_STEM_EDGE_TOL_SPACES`).

    ⚠️ Not the group's first overlapping row, and not the group's `side`: on a
    busy Litolff cell a wide box overlaps a NEIGHBOUR's stem first (Litolff p3
    `glyph/3/0/1/5`: the first row is the next note's stem, 235 tall, and the
    group's side is read off it; the pair's own, 521 tall, is its `rival`), and
    two stems can stand at the two edges (`glyph/3/1/2/15`: the pair's own on the
    left, the next voice's on the right). The extension read off the nearer or
    first of them refused real pairs, so the caller takes the longest reach of the
    stems that touch the pair at an edge."""
    half_w = STANDARD_HEAD_WIDTH_SPACES * spacing / 2.0
    span = outer_bot - outer_top
    lo, hi = outer_top + span / 3.0, outer_bot - span / 3.0
    out = []
    for st in stems:
        if st[1] > lo or st[1] + st[3] < hi:
            continue
        mid = st[0] + st[2] / 2.0
        d = min(abs(mid - (cx - half_w)), abs(mid - (cx + half_w)))
        if d <= STACKED_HOLLOW_STEM_EDGE_TOL_SPACES * spacing:
            out.append(st)
    return out


def _hollow_pair_from_page(pws: Any, cell: Any, cx: float, top_y: float,
                           half_step: float, spacing: float,
                           stems: Sequence[Tuple[float, float, float, float]],
                           cands: Sequence[int]) -> Dict[str, Any]:
    """ROADMAP 2.132 -- `fit_hollow_stacked_pair` wired to the PAGE raster and
    this group's stem. Canonical cell frame in, page frame for the ink
    (`bbox_page_px` + `upscale_factor`, the map `_page_box` uses); the stem
    extension stays in the cell frame, where `Q.STEM` is filed. Declined (a
    refusal that says so), never read from the cell, where the page raster or its
    mapping is missing."""
    page_binary = getattr(getattr(pws, "page", None), "binary", None)
    bbox = getattr(cell, "bbox_page_px", None)
    up = getattr(cell, "upscale_factor", None)
    if (page_binary is None or getattr(page_binary, "ndim", 0) != 2
            or not bbox or not up or spacing <= 0):
        return {"accepted": False, "positions": None, "margin": None,
                "near_miss": {"hollow_pair": "no page raster"}}
    sp_page = spacing / float(up)

    def reader(p: int) -> Optional[Tuple[float, float]]:
        px = bbox[0] + cx / float(up)
        py = bbox[1] + (top_y + p * half_step) / float(up)
        bx = _standard_head_box(px, py, sp_page)
        m = notehead_ink_off_line(
            page_binary, (bx[0], bx[2], bx[1] - bx[0], bx[3] - bx[2]), sp_page)
        if m is None:
            return None
        w = m["windows"]
        if w.get("center") is None or w.get("ring") is None:
            return None
        return (w["center"], w["ring"])

    def stem_ext(p: int) -> Optional[float]:
        outer_top = top_y + p * half_step - 0.5 * STANDARD_HEAD_HEIGHT_SPACES * spacing
        outer_bot = top_y + (p + 2) * half_step + 0.5 * STANDARD_HEAD_HEIGHT_SPACES * spacing
        near = _stacked_pair_stems(stems, cx, spacing, outer_top, outer_bot)
        if not near:
            return None
        return max(max((outer_top - st[1]) / spacing,
                       (st[1] + st[3] - outer_bot) / spacing) for st in near)

    return fit_hollow_stacked_pair(reader, cands, stem_ext)


def gather_stacked_head_fit(log: Log, cells: Sequence[Any],
                            local: Dict[int, Tuple[int, int]],
                            detections: Dict[str, List[Any]],
                            pws: Any = None) -> None:
    """`Q.STACKED_HEAD_FIT` -- ROADMAP 2.42. GATHER's half only: how many
    heads does a stem's own overlapping-box GROUP hold, and where -- never a
    keep/refuse decision (`notehead_precision._stacked_head_duplicate_
    refusal` owns that, reading this row rather than re-measuring anything).

    ⚠️ ONE GROUP = ONE STEM'S OWN BOX + ONE SIDE OF IT. Two notehead-classed
    boxes (any class, black or hollow -- ROADMAP 2.42's own brief) that both
    overlap the SAME `Q.STEM` row and stand on the SAME side of its centre x
    are one candidate group; a box with no stem reaching it, or alone on its
    own side, gets no row at all (2.40's own "no_stem_read"/lone-head
    convention, restated here rather than re-derived).

    ⚠️ WHOLE NOTES (no stem) ARE NOT BUILT. Every fixed proof case this
    roadmap item measured is a stemmed group; see the roadmap row.
    """
    import math
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        nh_idx = [gi for gi, d in enumerate(dets)
                 if str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)]
        if len(nh_idx) < 2:
            continue
        frame = frame_cell(c.measure_index)
        grid = _cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        stem_rows = log.rows(Q.STEM, sub)
        if grid is None or img is None or getattr(img, "ndim", 0) != 2 \
                or not stem_rows:
            # ⚠️ NO ROW AT ALL -- not an abstention. No unit, no raster or no
            # stem read in this cell means this quantity has NOTHING to say
            # about any glyph here; every consumer's fallback to the raw
            # detector centre is the honest default, not a guess this rule
            # made and hid.
            continue
        top_y, half_step = grid
        spacing = half_step * 2.0

        # ⚠️ GROUP BY (stem row id, side) -- `notehead_precision._same_side_
        # candidates`'s exact filter chain (shared stem box overlap, same
        # side of its centre x), restated here because GATHER has no
        # `Evidence` object to read that decision's helper through (the
        # reverse import would be a cycle -- `notehead_precision` already
        # imports THIS module inline).
        groups: Dict[Tuple[str, str], List[int]] = {}
        stem_xywh_of: Dict[str, Tuple[float, float, float, float]] = {}
        all_stems: List[Tuple[float, float, float, float]] = []
        for _sr in stem_rows:
            _row = _stacked_stem_xywh(_sr.value)
            if _row is not None:
                all_stems.append(_row)
        for gi in nh_idx:
            d = dets[gi]
            box_xywh = (float(d.x_canonical), float(d.y_canonical),
                       float(d.width_canonical), float(d.height_canonical))
            my_stem = None
            for sr in stem_rows:
                srow = _stacked_stem_xywh(sr.value)
                if srow is not None and _stacked_boxes_overlap(srow, box_xywh):
                    my_stem = (sr, srow)
                    break
            if my_stem is None:
                continue
            sr, srow = my_stem
            side = _stacked_side(srow, box_xywh)
            groups.setdefault((sr.id, side), []).append(gi)
            stem_xywh_of[sr.id] = srow

        for (stem_id, side), members in groups.items():
            if len(members) < 2:
                continue  # a lone head on its own side -- no row, unchanged
            # ⚠️ NO SEPARATE HOLLOW/BLACK TEMPLATE: `notehead_ink_under`'s
            # own `best = max(center, ring)` already picks whichever window
            # actually holds the ink (a filled head's dense centre, or a
            # hollow head's ring) -- the SAME reader every other notehead-ink
            # consumer in this file already trusts, restated here rather
            # than adding a second, class-gated scoring path.
            xs = [float(dets[gi].x_center) for gi in members]
            positions_seen = [(float(dets[gi].y_center) - top_y) / half_step
                              for gi in members]
            cx = sum(xs) / len(xs)
            lo = int(math.floor(min(positions_seen))) \
                - STACKED_HEAD_SEARCH_MARGIN_POSITIONS
            hi = int(math.ceil(max(positions_seen))) \
                + STACKED_HEAD_SEARCH_MARGIN_POSITIONS

            blob_fn = None
            # ⚠️ ROADMAP 2.129 -- FILLED HEADS ONLY. The blob test reads a solid
            # column through the heads' middle; a hollow head's middle is its
            # hole, and a tremolo slash boxed beside a half note is no head at
            # all (Litolff pdf 2: the first draft kept a slash as a second
            # half note, 1.78 spaces of ink). Two black-class boxes or no test.
            filled_group = all(str(dets[gi].smufl_name).startswith("noteheadBlack")
                               for gi in members)
            if stacked_second_head_enabled() and filled_group:
                def blob_fn(pos, _img=img, _cx=cx, _top=top_y, _hs=half_step,
                            _sp=spacing):
                    return stacked_blob_height_spaces(
                        _img, _cx, _top + (pos[0] + pos[1]) / 2.0 * _hs, _sp)
            hollow_fn = None
            # ⚠️ ROADMAP 2.132 -- a HOLLOW group (a half/whole class among its
            # boxes), flag `OMR_STACKED_HOLLOW_PAIR`, default OFF. Read off the
            # PAGE raster (the cell's own raster is the page slice resized, and
            # the page is the print), the stem from this cell's own `Q.STEM` row.
            if (stacked_hollow_pair_enabled() and not filled_group):
                def hollow_fn(cands, _c=c, _cx=cx, _top=top_y, _hs=half_step,
                              _sp=spacing, _stems=list(all_stems), _pws=pws):
                    return _hollow_pair_from_page(
                        _pws, _c, _cx, _top, _hs, _sp, _stems, cands)
            fit = fit_stacked_head_count(
                img, cx, list(range(lo, hi + 1)), top_y, half_step, spacing,
                len(members), observed=positions_seen,
                blob_height_fn=blob_fn, hollow_pair_fn=hollow_fn)
            if fit is None:
                for gi in members:
                    g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
                    log.abstain(g, Q.STACKED_HEAD_FIT,
                               reader=READERS.CV_STACKED_HEAD_FIT, frame=frame,
                               reason=ABSTAIN.NO_MASK,
                               note="no ink score at any candidate slot")
                continue

            candidates_detail = {"scores": {str(p): round(v, 4)
                                            for p, v in fit["scored"].items()}}
            if fit.get("second_head_by"):
                candidates_detail["second_head_by"] = fit["second_head_by"]
            if fit.get("near_miss"):
                candidates_detail["near_miss"] = fit["near_miss"]
            elif (stacked_second_head_enabled() and not filled_group
                  and fit["k"] == 1 and len(members) >= 2):
                # ⚠️ ROADMAP 2.129, Sean's tile 9: a hollow third IS two heads and
                # is still refused. Not kept: a hollow "two holes" test passes the
                # two halves of a bass clef on pdf 0 (both decisively hollow, 1.0
                # space apart, truth: no head), so it cannot yet be told from
                # a real pair. The refusal says so instead (2.106).
                candidates_detail["near_miss"] = {
                    "not_tested": "hollow-class group: the blob test is for filled heads",
                    "boxes": len(members)}
            margin = fit["margin"]
            if fit["ambiguous"]:
                for gi in members:
                    g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
                    log.abstain(g, Q.STACKED_HEAD_FIT,
                               reader=READERS.CV_STACKED_HEAD_FIT, frame=frame,
                               reason=ABSTAIN.AMBIGUOUS,
                               margin=round(margin, 4) if margin is not None
                               else None,
                               **candidates_detail,
                               note="two head-counts are within the margin "
                                    "of each other")
                continue

            chosen_sorted = fit["positions"]
            chosen_k = fit["k"]
            for gi in members:
                d = dets[gi]
                g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
                pos_float = (float(d.y_center) - top_y) / half_step
                slot_idx = min(range(len(chosen_sorted)),
                              key=lambda i: abs(chosen_sorted[i] - pos_float))
                slot_pos = float(chosen_sorted[slot_idx])
                box_xywh = (d.x_canonical, d.y_canonical,
                           d.width_canonical, d.height_canonical)
                my_ink = notehead_ink_under(img, box_xywh)
                log.observe(g, Q.STACKED_HEAD_FIT,
                           [chosen_k, slot_idx, slot_pos,
                            round(margin, 4) if margin is not None else None],
                           reader=READERS.CV_STACKED_HEAD_FIT, frame=frame,
                           side=side, stem=stem_id,
                           ink=(my_ink["best"] if my_ink else None),
                           **candidates_detail)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.49 -- a notehead-classed box whose own ink crosses BOTH sides of
# the one stem it overlaps is a TREMOLO SLASH, never a notehead (Sean,
# DECISIONS 2026-10-01: a notehead's ink lies on ONE side of its stem). This
# is GATHER's half only, the measurement: how much ink stands on each side,
# split at the stem's own centre x. `notehead_precision._tremolo_slash_
# crosses_stem` owns the floor and the refusal.
# ─────────────────────────────────────────────────────────────────────────────

#: Pixels of clearance kept beyond the stem's OWN half-width on either side
#: of the split -- the stem stroke's own ink must never be mistaken for ink
#: on "the other side" of itself. A whole pixel, not a fraction of the stem
#: width: `Q.STEM` boxes run 2-4 canonical px wide on both acceptance
#: documents, and a sub-pixel guard would leave the split line sitting
#: inside the stem's own anti-aliased edge.
NOTEHEAD_STEM_CROSS_GUARD_PX = 1.0


def _stem_cross_regions(box: Tuple[float, float, float, float],
                        stem_xywh: Tuple[float, float, float, float],
                        guard_px: float = NOTEHEAD_STEM_CROSS_GUARD_PX
                        ) -> Optional[Tuple[Tuple[float, float, float, float],
                                            Tuple[float, float, float, float]]]:
    """The LEFT and RIGHT sub-boxes of `box` on either side of `stem_xywh`'s
    own centre x, each stopped short of the stem's own half-width plus
    `guard_px` -- so the stem's own stroke is never counted as "ink on the
    other side" of itself. `None` where either side has no area left at all
    (the box does not reach past the stem far enough on that side to ask the
    question, e.g. a normal head whose box runs only from the stem's own
    edge outward)."""
    x, y, w, h = box
    sx, sy, sw, sh = stem_xywh
    scx = sx + sw / 2.0
    half = sw / 2.0 + guard_px
    left_x1 = scx - half
    right_x0 = scx + half
    if left_x1 <= x or right_x0 >= x + w:
        return None
    return (x, y, left_x1 - x, h), (right_x0, y, (x + w) - right_x0, h)


def _region_ink_fraction(img: Any, box: Tuple[float, float, float, float],
                         exclude_boxes: Sequence[Tuple[float, float, float,
                                                       float]] = ()
                         ) -> Optional[float]:
    """The plain ink fraction of `box` in `img` (0 = ink) -- NO sub-window
    shrink, unlike `notehead_ink_under`'s `center`/`ring` windows: those are
    sized against a WHOLE head's own box and degenerate to `None` on the
    narrow left/right strips `_stem_cross_regions` produces. This is the
    same `ink.sum() / ink.size` arithmetic `notehead_ink_under`'s own
    preamble computes, restated at the region's own full extent because
    that preamble has no unshrunk-whole-region mode to call instead.

    ⚠️ ROADMAP 2.49, MANAGER REVIEW (real Litolff re-gather, pages 1-3):
    `exclude_boxes` blanks out every pixel under a `Q.BEAM_STROKE` box
    BEFORE the fraction is taken -- Sean's own convention states it ("a beam
    may cross, but only joined to another stem at the stem's end"), and a
    real beam box runs far WIDER than a notehead's own (measured ~500 px vs
    ~150 px on this plate), so it trivially reaches BOTH sides of a stem
    whenever its own y-range overlaps the head's box at all. Without this,
    3 of 4 sampled false positives on the real re-gather were beamed groups,
    not tremolo slashes -- crops in `out/print/2.49/`."""
    region = _box_ink_mask(img, box, exclude_boxes)
    if region is None:
        return None
    return round(float(region.sum()) / float(region.size), 4)


def _box_ink_mask(img: Any, box: Tuple[float, float, float, float],
                  exclude_boxes: Sequence[Tuple[float, float, float,
                                                float]] = ()
                  ) -> Optional[Any]:
    """The boolean ink mask (0 = ink in `img`) of `box`'s own interior, with
    every `exclude_boxes` rectangle blanked out first -- `_region_ink_
    fraction`'s own preamble, extracted so a caller that needs the MASK
    itself (not just its fraction) -- `_ink_shape_descriptors`, ROADMAP
    2.49's shape test -- reads the identical pixels rather than a second,
    possibly-diverging crop."""
    if img is None or getattr(img, "ndim", 0) != 2:
        return None
    ink = (img == 0)
    H, W = ink.shape
    x, y, w, h = (float(v) for v in box)
    x0 = max(0, int(round(x)))
    y0 = max(0, int(round(y)))
    x1 = min(W, int(round(x + w)))
    y1 = min(H, int(round(y + h)))
    if x1 <= x0 or y1 <= y0:
        return None
    region = ink[y0:y1, x0:x1].copy()
    for ex, ey, ew, eh in exclude_boxes:
        ex0 = max(x0, int(round(ex)))
        ey0 = max(y0, int(round(ey)))
        ex1 = min(x1, int(round(ex + ew)))
        ey1 = min(y1, int(round(ey + eh)))
        if ex1 > ex0 and ey1 > ey0:
            region[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0] = False
    if region.size == 0:
        return None
    return region


#: A shape read on fewer ink pixels than this is not trustworthy (a
#: handful of anti-aliased edge pixels has no stable principal axis) --
#: `None`, not a guessed angle/elongation.
SHAPE_MIN_INK_PX = 12


def _ink_shape_descriptors(mask: Any) -> Optional[Dict[str, float]]:
    """ROADMAP 2.49 REDESIGN (Sean, DECISIONS 2026-10-01: "it should first
    be recognized as a thick diagonal line ... not round"): the PRINCIPAL-
    AXIS shape of an ink mask, by image moments -- no detector box, no
    class, only the pixels.

      `angle_deg`   the major axis's angle off HORIZONTAL, folded into
                    [0, 90] (0 = horizontal, like a ledger; 90 = vertical,
                    like a stem). A diagonal slash sits well inside that
                    range; a round blob's "major axis" is noise and its
                    elongation below will say so first.
      `elongation`  sqrt(major variance / minor variance) -- 1.0 for a
                    circle, large for a thin line. A filled oval notehead
                    is close to round; a tremolo stroke is a thin rectangle.
      `fill`        ink pixels / mask area -- a solid filled oval fills
                    most of its own bounding box; a thin diagonal stroke
                    fills much less of the SAME box even where the stroke
                    itself is thick, because the box is sized to the
                    GLYPH's detected extent, not to the stroke's own width.

    `None` where there are too few ink pixels to read a shape at all
    (`SHAPE_MIN_INK_PX`) -- CLAUDE.md rule 8, a shape this rule cannot read
    is not a shape it clears.
    """
    import math
    import numpy as np
    if mask is None:
        return None
    total = int(mask.sum())
    if total < SHAPE_MIN_INK_PX:
        return None
    ys, xs = np.nonzero(mask)
    cx, cy = float(xs.mean()), float(ys.mean())
    dx, dy = xs - cx, ys - cy
    cov = np.array([[float(np.mean(dx * dx)), float(np.mean(dx * dy))],
                    [float(np.mean(dx * dy)), float(np.mean(dy * dy))]])
    evals, evecs = np.linalg.eigh(cov)
    minor_var, major_var = float(evals[0]), float(evals[1])
    major_vec = evecs[:, 1]
    angle = math.degrees(math.atan2(float(major_vec[1]), float(major_vec[0])))
    angle = angle % 180.0
    if angle > 90.0:
        angle = 180.0 - angle
    elongation = math.sqrt(major_var / minor_var) if minor_var > 1e-6 else 50.0
    fill = total / mask.size
    return {"angle_deg": round(angle, 1), "elongation": round(elongation, 2),
            "fill": round(fill, 4), "ink_px": total}


def gather_notehead_stem_cross_ink(log: Log, cells: Sequence[Any],
                                   local: Dict[int, Tuple[int, int]],
                                   detections: Dict[str, List[Any]]) -> None:
    """`Q.NOTEHEAD_STEM_CROSS_INK` -- ROADMAP 2.49. See the quantity's own
    docstring in `record.py`. Reads `cell.image_no_staff` (the SAME erased
    raster `gather_notehead_ink`/`gather_stacked_head_fit` already read) and
    this cell's own `Q.STEM`/`Q.BEAM_STROKE` rows (filed earlier by
    `gather_cv_lines`) -- nothing here is re-detected.

    ⚠️ BEAM INK IS EXCLUDED FROM THE SPLIT (manager review, real re-gather):
    a `Q.BEAM_STROKE` box runs far wider than a notehead's own and reaches
    both sides of a stem whenever it overlaps the head's box at all, which
    is the common case for any head under a beam -- see `_region_ink_
    fraction`'s own docstring. Sean's own convention carves this out
    directly ("a beam may cross, but only joined to another stem at the
    stem's end"); excluding beam-classed ink is how that exception is kept
    without re-deriving which beam joins which stem a second time here.

    ⚠️⚠️ ROADMAP 2.49 REDESIGN (Sean, DECISIONS 2026-10-01, on manager crop
    `glyph/3/0/8/6/12`, a plain filled head whose own round oval pokes
    slightly past its own attached stem): an AREA fraction of a narrow edge
    sliver is not evidence -- a tiny curve of a real head's own ink can
    fill a thin sliver almost completely while being a negligible SHARE of
    the glyph's own total ink. `detail["left_share"]`/`["right_share"]` are
    each side's ink pixel count divided by the WHOLE box's own total ink
    pixel count (beam-excluded) -- "each side a real fraction of the
    stroke" (Sean) -- and `detail["angle_deg"]`/`["elongation"]`/`["fill"]`
    (`_ink_shape_descriptors`, over the WHOLE box, beam-excluded) are the
    shape read ADJUDICATE's shape gate needs. `value` keeps its original
    `[left, right]` AREA fractions (the per-side density, still a useful
    ruler reading) unchanged; every new field is additive, in `detail`.
    """
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        dets = detections.get(sub.to_key(), ())
        nh_idx = [gi for gi, d in enumerate(dets)
                 if str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX)]
        if not nh_idx:
            continue
        frame = frame_cell(c.measure_index)
        img = getattr(c, "image_no_staff", None)
        stem_rows = log.rows(Q.STEM, sub)
        if img is None or getattr(img, "ndim", 0) != 2 or not stem_rows:
            continue
        beam_boxes = [bb for bb in (_stacked_stem_xywh(br.value)
                                    for br in log.rows(Q.BEAM_STROKE, sub))
                     if bb is not None]
        for gi in nh_idx:
            d = dets[gi]
            box = (float(d.x_canonical), float(d.y_canonical),
                  float(d.width_canonical), float(d.height_canonical))
            my_stem = None
            for sr in stem_rows:
                srow = _stacked_stem_xywh(sr.value)
                if srow is not None and _stacked_boxes_overlap(srow, box):
                    my_stem = (sr, srow)
                    break
            if my_stem is None:
                continue
            sr, srow = my_stem
            regions = _stem_cross_regions(box, srow)
            if regions is None:
                continue
            left_box, right_box = regions
            left_ink = _region_ink_fraction(img, left_box, beam_boxes)
            right_ink = _region_ink_fraction(img, right_box, beam_boxes)

            # ⚠️ ROADMAP 2.49 REDESIGN -- each side's SHARE of the glyph's
            # own total ink, and that ink's own SHAPE (angle/elongation/
            # fill) -- both measured over the box with the STEM'S OWN
            # COLUMN blanked out too, not only beam boxes.
            #
            # ⚠️⚠️ MANAGER REVIEW, FIRST BUILD OF THIS REDESIGN (page-13
            # re-gather): computing these over the WHOLE box (stem column
            # included) read the real slash `glyph/13/1/10/2/0` at
            # elongation 1.5 / fill 0.62 -- indistinguishable from a round
            # head -- because the stem's own thick, near-vertical stroke
            # runs straight through the box's centre and dominates the
            # moment calculation. The stem is not the stroke being asked
            # about; `_stem_cross_regions`'s own LEFT/RIGHT boxes already
            # exclude it, so the shape/share mask is their UNION (the box
            # with that same centre column blanked), never the raw box.
            full_mask = _box_ink_mask(img, box, beam_boxes)
            left_share = right_share = total_ink_px = None
            shape = None
            if full_mask is not None:
                bx = box[0]
                lx1 = max(0, int(round(left_box[0] + left_box[2] - bx)))
                rx0 = max(0, int(round(right_box[0] - bx)))
                rx1 = max(0, int(round(right_box[0] + right_box[2] - bx)))
                lx1 = min(lx1, full_mask.shape[1])
                rx1 = min(rx1, full_mask.shape[1])
                stem_excluded = full_mask.copy()
                if rx0 > lx1:
                    stem_excluded[:, lx1:rx0] = False
                total_ink_px = int(stem_excluded.sum())
                shape = _ink_shape_descriptors(stem_excluded)
                if total_ink_px > 0:
                    left_px = int(stem_excluded[:, :lx1].sum()) if lx1 > 0 else 0
                    right_px = int(stem_excluded[:, rx0:].sum()) \
                        if rx0 < stem_excluded.shape[1] else 0
                    left_share = round(left_px / total_ink_px, 4)
                    right_share = round(right_px / total_ink_px, 4)

            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            detail: Dict[str, Any] = {
                "stem": sr.id, "left": left_ink, "right": right_ink,
                "left_share": left_share, "right_share": right_share,
                "total_ink_px": total_ink_px}
            if shape is not None:
                detail.update(shape)
            log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [left_ink, right_ink],
                       reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK, frame=frame,
                       **detail)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.58d -- `Q.HEAD_STEM_REACH`: which way a contested head's stem runs.
# ─────────────────────────────────────────────────────────────────────────────

#: A vertical run beside a head must stand this far (staff spaces) past the
#: head's own edge to count as a stem. A head is ~1.0-1.5 sp tall and a stem is
#: at least ~2.5 sp, so 0.8 sp clears the head's own outline and the thickness
#: of a staff line crossing the column, and is short of any real stem.
HEAD_STEM_MIN_EXT_SPACES = 0.8
#: The column the run is read in: a stem is ~0.15-0.25 sp wide and its OUTER
#: edge is flush with the head's edge (down -> left, up -> right, CLAUDE.md
#: §10), so the window slides this far each side of the edge and keeps the
#: position that gives the longest run.
HEAD_STEM_WINDOW_SPACES = 0.18
HEAD_STEM_SLIDE_OUT_SPACES = 0.15
HEAD_STEM_SLIDE_IN_SPACES = 0.30
#: a run bridges a white gap this long (a staff line erased or thinned, a
#: broken scan) but NO longer: the gap between two staff lines is a whole space
HEAD_STEM_GAP_SPACES = 0.30
HEAD_STEM_ROW_FRACTION = 0.85
HEAD_STEM_MAX_RUN_SPACES = 9.0


def _stem_run(ink: Any, x_lo: int, x_hi: int, y_from: int, step: int,
              gap_px: int, max_px: int) -> Tuple[int, bool]:
    """`(last inked row, hit the image edge)` walking from `y_from` in `step`
    (+1 down, -1 up) over columns `[x_lo, x_hi)`; a row is inked when at least
    `HEAD_STEM_ROW_FRACTION` of the window is. Stops at a gap of more than
    `gap_px` blank rows."""
    h, w = ink.shape
    x_lo, x_hi = max(0, x_lo), min(w, x_hi)
    if x_hi <= x_lo:
        return y_from - step, False
    last = y_from - step
    r = y_from
    n = 0
    while 0 <= r < h and n <= max_px:
        if float(ink[r, x_lo:x_hi].mean()) >= HEAD_STEM_ROW_FRACTION:
            last = r
        elif abs(r - last) > gap_px:
            return last, False
        r += step
        n += 1
    return last, not (0 <= r < h)


def measure_head_stem(ink: Any, box: Tuple[float, float, float, float],
                      sp: float) -> Dict[str, Any]:
    """Which way a head's stem runs, off a boolean ink image (True = ink) in the
    SAME frame as `box = (x0, y0, x1, y1)` and `sp` pixels per staff space.

    ⚠️ A RULER READING, NOT AN IDENTIFICATION. It reports vertical ink beside
    the head; that the ink is a stem and which staff it points at are
    ADJUDICATE's. `direction`: `down` (a run beneath the head along its left
    edge), `up` (above, along its right edge), `both` (through-ink: a barline
    or a through-stem -- claims nothing), `none` (no run of
    `HEAD_STEM_MIN_EXT_SPACES`). Pixels in, pixels out."""
    x0, y0, x1, y1 = (float(v) for v in box)
    hh = y1 - y0
    out: Dict[str, Any] = {"sp": float(sp)}
    if sp <= 0 or hh <= 0:
        return dict(out, direction="none", down_ext=0.0, up_ext=0.0,
                    down_tip_y=None, up_tip_y=None)
    win = max(2, int(round(HEAD_STEM_WINDOW_SPACES * sp)))
    gap = max(1, int(round(HEAD_STEM_GAP_SPACES * sp)))
    mx = int(round(HEAD_STEM_MAX_RUN_SPACES * sp))
    ys_dn = int(round(y1 - 0.25 * hh))
    ys_up = int(round(y0 + 0.25 * hh))
    best = {}
    lo_out = HEAD_STEM_SLIDE_OUT_SPACES * sp
    lo_in = HEAD_STEM_SLIDE_IN_SPACES * sp
    through = {}
    for side in ("down", "up"):
        ext_best, tip_best, clip_best, xs_best = -1e9, None, False, None
        if side == "down":
            starts = range(int(round(x0 - lo_out)), int(round(x0 + lo_in)) + 1)
        else:
            starts = range(int(round(x1 - lo_in)) - win,
                           int(round(x1 + lo_out)) - win + 1)
        for xs in starts:
            if side == "down":
                tip, clip = _stem_run(ink, xs, xs + win, ys_dn, 1, gap, mx)
                ext = tip - y1
            else:
                tip, clip = _stem_run(ink, xs, xs + win, ys_up, -1, gap, mx)
                ext = y0 - tip
            if ext > ext_best:
                ext_best, tip_best, clip_best, xs_best = ext, tip, clip, xs
        best[side] = (ext_best / sp, tip_best, clip_best)
        # THROUGH-INK: the SAME columns also run the OTHER way past the head -- a
        # barline touching the head, or a stem that is another head's. Not a stem
        # that leaves THIS head one way.
        if ext_best / sp >= HEAD_STEM_MIN_EXT_SPACES and xs_best is not None:
            if side == "down":
                t2, _c = _stem_run(ink, xs_best, xs_best + win, ys_up, -1, gap, mx)
                through[side] = (y0 - t2) / sp >= HEAD_STEM_MIN_EXT_SPACES
            else:
                t2, _c = _stem_run(ink, xs_best, xs_best + win, ys_dn, 1, gap, mx)
                through[side] = (t2 - y1) / sp >= HEAD_STEM_MIN_EXT_SPACES
    d_ok = best["down"][0] >= HEAD_STEM_MIN_EXT_SPACES
    u_ok = best["up"][0] >= HEAD_STEM_MIN_EXT_SPACES
    direction = ("both" if (d_ok and u_ok) or any(through.values())
                 else "down" if d_ok else "up" if u_ok else "none")
    return dict(out, direction=direction,
                down_ext=round(best["down"][0], 3),
                up_ext=round(best["up"][0], 3),
                down_tip_y=(float(best["down"][1]) if d_ok else None),
                up_tip_y=(float(best["up"][1]) if u_ok else None),
                down_clipped=bool(best["down"][2]) if d_ok else False,
                up_clipped=bool(best["up"][2]) if u_ok else False)


def _is_second_only_head(log: Log, g: Any) -> bool:
    """ROADMAP 2.114 round 2: a head ONLY the second detector boxed (`Q.SECOND_HOLLOW` `relation` `second_only`; empty unless
    `OMR_SECOND_HOLLOW_DETECTOR` is on). It is not contested, but ADJUDICATE needs the ruler's stem reading as the witness of a note that
    is not the second box itself (`rhythm._second_only_evidence`)."""
    return any((r.detail or {}).get("relation") == "second_only" for r in log.rows(Q.SECOND_HOLLOW, g))


def gather_head_stem_reach(log: Log, pws: Any, cells: Sequence[Any],
                           local: Dict[int, Tuple[int, int]],
                           detections: Dict[str, List[Any]]) -> Dict[str, int]:
    """`Q.HEAD_STEM_REACH` for every CONTESTED notehead (one with
    `Q.GLYPH_BAND_DISTANCE` rows -- the `glyph_owner` domain). ROADMAP 2.58d.

    ⚠️ READS THE PAGE'S ORIGINAL RASTER (`pws.page.rgb`), in the page frame the
    boxes are already in, so a head cut from one staff's padded cell and the
    same ink cut from its neighbour's get the SAME reading (a cell frame could
    not answer a cross-staff question). Runs after `gather_ownership_evidence`
    (it filters on its rows). Returns a census `{heads, down, up, both, none}`."""
    census = {"heads": 0, "down": 0, "up": 0, "both": 0, "none": 0}
    rgb = getattr(getattr(pws, "page", None), "rgb", None)
    if rgb is None or getattr(rgb, "ndim", 0) < 2:
        return census
    gray = rgb if rgb.ndim == 2 else rgb[..., :3].mean(axis=2)
    ink = gray < 128
    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    sp_by_staff: Dict[Tuple[int, int], float] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        ys = [float(y) for y in st.line_ys]
        if key is not None and len(ys) >= 2:
            sp_by_staff[(key[0], key[1])] = (ys[-1] - ys[0]) / (len(ys) - 1)
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        sp = sp_by_staff.get((sub.system, sub.staff))
        if c is None or not sp:
            continue
        for gi, d in enumerate(dets):
            if not str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX):
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            if not log.rows(Q.GLYPH_BAND_DISTANCE, g) and not _is_second_only_head(log, g):
                continue
            box = _page_box(c, d)
            if box is None:
                continue
            res = measure_head_stem(ink, box, sp)
            census["heads"] += 1
            census[res["direction"]] += 1
            log.observe(g, Q.HEAD_STEM_REACH, res["direction"],
                        reader=READERS.CV_HEAD_STEM_REACH, frame="page",
                        head_box_page=[round(float(v), 2) for v in box],
                        **{k: v for k, v in res.items() if k != "direction"})
    return census


# ─────────────────────────────────────────────────────────────────────────────
# dynamic-not-a-head -- is a head that lies on a dynamic letter's box a filled
# head of its own, or the letter's stroke?
# ─────────────────────────────────────────────────────────────────────────────

#: A head box is measured against a letter only where at least this fraction of
#: the HEAD box's area lies inside the letter's box. Below it the two boxes
#: merely touch; ADJUDICATE's own floor (0.4) is higher, and this lower one only
#: keeps the touching cases on the record.
HEAD_ON_LETTER_FILE_FLOOR = 0.2


def _strip_lines_and_stems(crop: Any, sp: float) -> Any:
    """`crop` (255 = ink) with the staff and ledger lines (horizontal runs of
    `LETTER_LINE_SPACES`) and the long stems/barlines (vertical runs of
    `VLINE_SPACES`) taken out -- `letter_ink_extent`'s own two removals, in
    its own order, restated so a measurement of a LETTER's ink and of a HEAD
    on it read the same cleaned ink."""
    import cv2 as _cv2
    out = crop.copy()
    kh = max(3, int(round(LETTER_LINE_SPACES * sp)))
    hl = _cv2.morphologyEx(out, _cv2.MORPH_OPEN,
                           _cv2.getStructuringElement(_cv2.MORPH_RECT, (kh, 1)))
    hl = _cv2.dilate(hl, _cv2.getStructuringElement(_cv2.MORPH_RECT, (1, 3)))
    out[hl > 0] = 0
    kv = max(3, int(round(VLINE_SPACES * sp)))
    vl = _cv2.morphologyEx(out, _cv2.MORPH_OPEN,
                           _cv2.getStructuringElement(_cv2.MORPH_RECT, (1, kv)))
    vl = _cv2.dilate(vl, _cv2.getStructuringElement(_cv2.MORPH_RECT, (3, 1)))
    out[vl > 0] = 0
    return out


def head_letter_ink(ink: Any, head_box: Sequence[float],
                    letter_box: Sequence[float], sp: float
                    ) -> Optional[Dict[str, float]]:
    """Two ruler readings for a head box that lies on a dynamic letter's box.
    Pure; `ink` is the page's ink (255 = ink), boxes are page pixels
    `(x0, y0, x1, y1)`, `sp` is the staff space in page pixels.

    * `disc_spaces`: the diameter, in staff spaces, of the widest filled disc
      inside the HEAD box, off the RAW ink (the staff lines left in: a head
      on a line is one blob with it, and a line is only ~0.3 spaces wide). A
      notehead is a filled blob (measured 1.13-1.27 on every real head near
      a letter); an `f`'s hook or top is a stroke (0.74-0.84).
    * `letter_ink_share`: the fraction of the LETTER box's ink (lines and
      long stems taken out) that lies inside the head box. A `p`'s bowl is
      most of the `p` (0.60-0.62); a note printed beside an `sf` is a sliver
      of that wide box (0.11-0.22); an `f`'s hook is also a sliver (0.08-0.14),
      which is why the disc reading exists.

    None where the crop is empty or `sp` is not positive."""
    import cv2 as _cv2
    import numpy as _np
    if sp <= 0:
        return None
    H, W = ink.shape[:2]
    hx0, hy0, hx1, hy1 = (int(round(v)) for v in head_box)
    lx0, ly0, lx1, ly1 = (int(round(v)) for v in letter_box)
    pad = int(round(2.0 * sp))
    cx0 = max(0, min(hx0, lx0) - pad)
    cy0 = max(0, min(hy0, ly0) - pad)
    cx1 = min(W, max(hx1, lx1) + pad)
    cy1 = min(H, max(hy1, ly1) + pad)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    crop = _np.array(ink[cy0:cy1, cx0:cx1], copy=True)
    dist = _cv2.distanceTransform((crop > 0).astype(_np.uint8),
                                  _cv2.DIST_L2, 5)

    def window(a, b):
        x0, y0, x1, y1 = b
        return a[max(0, y0 - cy0):max(0, y1 - cy0),
                 max(0, x0 - cx0):max(0, x1 - cx0)]

    head_dist = window(dist, (hx0, hy0, hx1, hy1))
    if head_dist.size == 0:
        return None
    clean = _strip_lines_and_stems(crop, sp)
    letter_ink = int((window(clean, (lx0, ly0, lx1, ly1)) > 0).sum())
    ix0, iy0 = max(hx0, lx0), max(hy0, ly0)
    ix1, iy1 = min(hx1, lx1), min(hy1, ly1)
    inside = (int((window(clean, (ix0, iy0, ix1, iy1)) > 0).sum())
              if ix1 > ix0 and iy1 > iy0 else 0)
    return {"disc_spaces": round(2.0 * float(head_dist.max()) / sp, 3),
            "letter_ink_share": round(inside / max(1, letter_ink), 3),
            "letter_ink_px": letter_ink}


def gather_notehead_letter_ink(log: Log, pws: Any, cells: Sequence[Any],
                               local: Dict[int, Tuple[int, int]],
                               detections: Dict[str, List[Any]]
                               ) -> Dict[str, int]:
    """`Q.NOTEHEAD_LETTER_INK` for every notehead box lying at least
    `HEAD_ON_LETTER_FILE_FLOOR` inside a detected dynamic letter's box, filed
    on the HEAD's glyph against the letter it overlaps most. Runs after
    `gather_detections` only (it reads the detections and the page raster).

    ⚠️ THE LETTERS ARE SEARCHED PAGE-WIDE, across cells and staves: the detector
    files a letter under the cell it was cut from, which on a condensed page is
    often the next staff's (Litolff `glyph/2/0/3/1/6`, the `p` whose bowl is
    the head `glyph/2/0/2/1/12`). A population of tens per page, so the double
    loop is cheap.

    Reads the page's RAW raster (`_raw_page_ink`, threshold 180, the one the
    letter's own ink height reads). A page with no raster files nothing."""
    census = {"heads": 0, "on_a_letter": 0}
    raw = _raw_page_ink(pws)
    if raw is None:
        return census
    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    sp_by_staff: Dict[Tuple[int, int], float] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        ys = [float(y) for y in st.line_ys]
        if key is not None and len(ys) >= 2:
            sp_by_staff[(key[0], key[1])] = (ys[-1] - ys[0]) / (len(ys) - 1)
    letters: List[Tuple[Any, str, Tuple[float, ...]]] = []
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for gi, d in enumerate(dets):
            if d.smufl_name in _DYNAMIC_LETTER_CLASSES:
                b = _page_box(c, d)
                if b is not None:
                    letters.append((R.glyph(sub.page, sub.system, sub.staff,
                                            sub.cell, gi), d.smufl_name,
                                    tuple(float(v) for v in b)))
    if not letters:
        return census
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        sp = sp_by_staff.get((sub.system, sub.staff))
        if c is None or not sp:
            continue
        for gi, d in enumerate(dets):
            if not str(d.smufl_name).lower().startswith(_NOTEHEAD_PREFIX):
                continue
            box = _page_box(c, d)
            if box is None:
                continue
            census["heads"] += 1
            hx0, hy0, hx1, hy1 = (float(v) for v in box)
            area = max(1e-9, (hx1 - hx0) * (hy1 - hy0))
            best = None
            for lg, cls, lb in letters:
                ix = max(0.0, min(hx1, lb[2]) - max(hx0, lb[0]))
                iy = max(0.0, min(hy1, lb[3]) - max(hy0, lb[1]))
                frac = ix * iy / area
                if frac >= HEAD_ON_LETTER_FILE_FLOOR and (
                        best is None or frac > best[0]):
                    best = (frac, lg, cls, lb)
            if best is None:
                continue
            frac, lg, cls, lb = best
            res = head_letter_ink(raw, box, lb, sp)
            if res is None:
                continue
            census["on_a_letter"] += 1
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            log.observe(g, Q.NOTEHEAD_LETTER_INK, res["disc_spaces"],
                        reader=READERS.CV_NOTEHEAD_LETTER_INK,
                        frame=FRAME_PAGE,
                        letter_ink_share=res["letter_ink_share"],
                        head_in_letter=round(frac, 3),
                        letter=lg.to_key(), letter_class=cls,
                        letter_w_spaces=round((lb[2] - lb[0]) / sp, 3),
                        letter_h_spaces=round((lb[3] - lb[1]) / sp, 3),
                        head_box_page=[round(v, 2) for v in box],
                        sp=round(float(sp), 3))
    return census


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.107 — the second look at head/rest ink that is really dynamic letters
# ─────────────────────────────────────────────────────────────────────────────

#: A head or rest box needs at least this share of its own ink inside the read
#: letters' boxes to get a `Q.LETTER_LOOK_COVER` row (ADJUDICATE refuses at its
#: own, higher bar -- the row is the measurement, the bar is the decision's).
LETTER_COVER_FILE_FLOOR = 0.2


def _glyph_reader(log: Log, g: Subject) -> str:
    """The reader that FILED this glyph's box: `DETECTOR` for the production
    pass, another name for the rescue or the letter look. A letter row must be
    attributed to the reader that read the letter."""
    rows = log.rows(Q.GLYPH_BOX, g)
    return rows[-1].reader if rows else READERS.DETECTOR


def gather_letter_look(log: Log, pws: Any, cells: Sequence[Any],
                       local: Dict[int, Tuple[int, int]],
                       detections: Dict[str, List[Any]], *,
                       detector: Any = None,
                       progress: bool = False) -> Dict[str, int]:
    """ROADMAP 2.107 (Sean 2026-10-13: *"sf should be read as a dynamic - it is
    letters"*; *"we added a whole library of text to be checked"*). A SECOND
    LOOK, by the same detector, at the ink under a head or rest box that looks
    like letters; see `letter_look` for the method and for what each reader did
    with this ink before.

    GATHER decides nothing. This reads: where a group's ink spells a string the
    TERMS LIBRARY holds as a dynamic, it APPENDS the letters to the cell's own
    `detections` (at indices past every production box, the rescue's pattern)
    as `dynamic*` boxes under `READERS.LETTER_LOOK`, files
    `Q.LETTER_LOOK_COVER` on every head/rest box whose ink they explain, and
    leaves the REFUSAL of those boxes to ADJUDICATE. A group it could not read
    is a `Q.GLYPH_BOX` abstention on the cell with how close it came (the best
    letter it saw, the strings the library refused, the best note/rest class it
    competed with) -- never silence.

    ⚠️ NEVER DOUBLES A DETECTED DYNAMIC (a read letter lying on a letter box the
    production pass drew is skipped) and NEVER READS A LETTER ALONE INTO A
    DYNAMIC: an unread letter beside a read one is an OPEN SLOT (twins of every
    letter the library can complete), so the dynamic is NARROWED, not guessed.

    ⚠️ ONE PAGE RASTER, the raw threshold-180 ink (`_raw_page_ink`) -- staff
    lines erased locally per system strip by `letter_look.erase_staff_lines`.
    A page with no raster, or a detector with no `detect_image`, files nothing.
    """
    census = {"seeds": 0, "groups": 0, "read": 0, "narrowed": 0, "rejected": 0,
              "skipped": 0, "letters_added": 0, "boxes_covered": 0}
    if detector is None or not hasattr(detector, "detect_image"):
        return census
    raw = _raw_page_ink(pws)
    if raw is None:
        return census
    import numpy as _np
    from . import letter_look as LL
    from ..template_matcher import SymbolDetection

    cell_by_key: Dict[Tuple[int, int, int, int], Any] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    page_no = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    sp_by_sys: Dict[Tuple[int, int], List[float]] = {}
    ys_by_sys: Dict[Tuple[int, int], List[float]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        ys = [float(y) for y in st.line_ys]
        if key is None or len(ys) < 2:
            continue
        sp_by_sys.setdefault((page_no, key[0]), []).append(
            (ys[-1] - ys[0]) / (len(ys) - 1))
        ys_by_sys.setdefault((page_no, key[0]), []).extend(ys)
    if not sp_by_sys:
        return census

    def detect(img, imgsz):
        return detector.detect_image(img, LL.LOOK_CONF_FLOOR, imgsz)

    dyn_boxes = [tuple(float(v) for v in b)
                 for b in _dynamic_letter_boxes(detections, cell_by_key)]
    by_sys: Dict[Tuple[int, int], List[Tuple[str, Tuple[float, ...]]]] = {}
    where: Dict[str, Tuple[Subject, Any, str, Tuple[int, ...]]] = {}
    for cell_key, dets in list(detections.items()):
        sub = Subject.from_key(cell_key)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for gi, d in enumerate(dets):
            if not LL.is_seed_class(d.smufl_name):
                continue
            box = _page_box(c, d)
            if box is None:
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            by_sys.setdefault((sub.page, sub.system), []).append(
                (g.to_key(), tuple(float(v) for v in box)))
            where[g.to_key()] = (g, c, str(d.smufl_name),
                                 (sub.page, sub.system, sub.staff, sub.cell, gi))
            census["seeds"] += 1

    for (pg, sysn), members in by_sys.items():
        spl = sorted(sp_by_sys.get((pg, sysn), []))
        ys = ys_by_sys.get((pg, sysn), [])
        if not spl or not ys:
            continue
        sp = spl[len(spl) // 2]
        y0 = int(max(0, min(ys) - 8 * sp))
        y1 = int(min(raw.shape[0], max(ys) + 8 * sp))
        clean = _np.zeros(raw.shape[:2], dtype=_np.uint8)
        clean[y0:y1] = LL.erase_staff_lines(raw[y0:y1], sp)
        clean_alt = _np.zeros(raw.shape[:2], dtype=_np.uint8)
        clean_alt[y0:y1] = LL.erase_staff_lines(
            raw[y0:y1], sp, slack_px=LL.ERASE_SLACK_TIGHT_PX)
        seed_boxes = {k: b for k, b in members}
        for grp in LL.find_groups(clean, members, sp):
            census["groups"] += 1
            gr = LL.read_page_group(clean, grp, seed_boxes, sp, detect,
                                    dyn_boxes, clean_alt=clean_alt)
            census[gr.status] = census.get(gr.status, 0) + 1
            ub = [float(v) for v in gr.box]
            first_g, first_c, _n, _ix = where[grp.seeds[0]]
            if gr.status not in ("read", "narrowed"):
                reason = {"already_boxed_as_a_dynamic": ABSTAIN.ALREADY_BOXED,
                          "not_in_library": ABSTAIN.NOT_IN_LIBRARY}.get(
                    gr.reason, ABSTAIN.NO_LETTER_READ)
                log.abstain(first_g.at(R.Kind.CELL), Q.GLYPH_BOX,
                            reader=READERS.LETTER_LOOK,
                            frame=frame_cell(first_c.measure_index),
                            reason=reason, why=gr.reason, group_box_page=ub,
                            seeds=[(k, where[k][2]) for k in grp.seeds],
                            best_letters=[list(t) for t in gr.near],
                            probe_only=gr.probe_only,
                            unstable_across_erasures=[
                                [list(l), c] for l, c in gr.unstable],
                            best_note_or_rest=list(gr.rival) if gr.rival else None,
                            library_tried=(list(gr.spelling.tried)
                                           if gr.spelling else None))
                continue
            sp_ = gr.spelling

            def _overlap(k):
                b = seed_boxes[k]
                ix = max(0.0, min(ub[2], b[2]) - max(ub[0], b[0]))
                iy = max(0.0, min(ub[3], b[3]) - max(ub[1], b[1]))
                return ix * iy

            home_key = max(gr.seed_ids or grp.seeds, key=_overlap)
            g0, c0, _n0, _ix0 = where[home_key]
            cell_key0 = g0.at(R.Kind.CELL).to_key()
            existing = detections.setdefault(cell_key0, [])
            frame0 = frame_cell(c0.measure_index)
            up = float(getattr(c0, "upscale_factor", 0) or 0)
            bbox0 = getattr(c0, "bbox_page_px", None)
            if not up or not bbox0:
                continue
            added: List[str] = []
            for reg in sp_.regions:
                bx0, by0, bx1, by1 = reg.box
                for letter in (reg.letters or ()):
                    cls = LL.CLASS_OF_LETTER[letter]
                    # a slot twin's confidence IS the letter reader's own
                    # evidence for that letter over the ink (both erasures,
                    # `letter_look.slot_evidence`), floored so a letter nothing
                    # scored still has a row; never the document's frequency.
                    conf = (reg.conf if reg.how == "read" else
                            max(LL.LOOK_CONF_FLOOR,
                                reg.evidence.get(letter, 0.0)))
                    det = SymbolDetection(
                        cell=c0, smufl_name=cls, category="dynamic",
                        x_canonical=int(round((bx0 - bbox0[0]) * up)),
                        y_canonical=int(round((by0 - bbox0[1]) * up)),
                        width_canonical=max(1, int(round((bx1 - bx0) * up))),
                        height_canonical=max(1, int(round((by1 - by0) * up))),
                        confidence=float(conf))
                    gi = len(existing)
                    existing.append(det)
                    g = R.glyph(g0.page, g0.system, g0.staff, g0.cell, gi)
                    added.append(g.to_key())
                    detail: Dict[str, Any] = {
                        "category": "dynamic", "how": reg.how,
                        "read_as": sp_.text, "candidates": list(sp_.candidates),
                        "library_term": sp_.term, "looks_seen": reg.scales_seen,
                        "evidence": dict(reg.evidence),
                        "group_box_page": ub,
                        "region_letters": list(reg.letters)}
                    page_box = _page_box(c0, det)
                    if page_box is not None:
                        px0, py0, px1, py1 = page_box
                        detail.update(bbox_page_px=[px0, py0, px1, py1],
                                      x_center_page=(px0 + px1) / 2.0,
                                      y_center_page=(py0 + py1) / 2.0)
                    log.observe(g, Q.GLYPH_BOX,
                                (cls, det.x_canonical, det.y_canonical,
                                 det.width_canonical, det.height_canonical),
                                reader=READERS.LETTER_LOOK, frame=frame0,
                                score=float(conf), **detail)
                    log.observe(g, Q.GLYPH_CONF, float(conf),
                                reader=READERS.LETTER_LOOK, frame=frame0,
                                score=float(conf))
                    census["letters_added"] += 1
            for k, share in zip(gr.seed_ids, gr.cover):
                if share < LETTER_COVER_FILE_FLOOR:
                    continue
                census["boxes_covered"] += 1
                sp_pg, sp_sy, sp_st, sp_ce, sp_gi = where[k][3]
                seed_g = R.glyph(sp_pg, sp_sy, sp_st, sp_ce, sp_gi)
                log.observe(seed_g, Q.LETTER_LOOK_COVER, float(share),
                            reader=READERS.LETTER_LOOK, frame=FRAME_PAGE,
                            letters=added, read_as=sp_.text,
                            candidates=list(sp_.candidates),
                            status=gr.status, group_box_page=ub,
                            library_term=sp_.term)
            if progress:
                print(f"  gather letter look {cell_key0}: {gr.status} "
                      f"{sp_.text or list(sp_.candidates)} "
                      f"({len(added)} letter box(es))")
    return census


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
# ROADMAP 2.74 -- is a stroke the detector or the CV opening called a BEAM
# really one? Thick, straight, and standing on at least two stems.
#
# Sean, 2026-10-09 (DECISIONS), on 2.65 tiles 1, 4, 15 and 21 -- *"A beam must
# not only connect to its note but also to another note."* / *"A beam never
# has an arc."* / *"The thickness on a beam is always more than a hairpin."*
# Strokes that a slur, a tie, a hairpin or a second reading of one beam put
# in a cell were counted as one more beam LEVEL of every note whose column
# they cover (tile 21: a slur's two tapering arcs read a sixteenth). This is
# the INK half of the test: three rulers per candidate stroke, filed under
# `Q.BEAM_STROKE_INK` and read by `rhythm.adjudicate_duration`.
#
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond Sean's
# three lines: that a beam's thickness is a multiple of THIS plate's staff
# line thickness measured AT the stroke's own columns (CLAUDE.md §10: measure
# against the staff locally; scans change weight and tilt across a system), a
# hairpin's line being about one. Falsified by a print-confirmed beam whose
# median thickness is under `BEAM_THICKNESS_RATIO_MIN` lines, or a hairpin
# line or slur over it.
# ─────────────────────────────────────────────────────────────────────────────

#: How far past the stroke's own band a vertical run must reach to be a stem
#: standing at that end, in staff spaces. A beam's stems run at least this far
#: from it (a stem is ~3.5 spaces); a slur's or hairpin's end meets no such
#: run.
BEAM_INK_END_STEM_SPACES = 1.5
#: How wide an end window is searched for that stem, in staff spaces either
#: side of the stroke's end.
BEAM_INK_END_WINDOW_SPACES = 0.4
#: A stroke needs ink in at least this share of its own columns to be measured.
BEAM_INK_MIN_COVER = 0.5
#: The curvature fit ignores this many spaces at each end, where a stem or
#: head can bulge the run.
BEAM_INK_END_TRIM_SPACES = 0.5
BEAM_INK_THRESHOLD = 180
#: How far either side of a stroke the staff lines are read, in staff spaces,
#: so a beam lying ON a line does not set the line's own thickness.
BEAM_INK_LINE_FLANK_SPACES = 3.0

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.82 -- the CORE of a stroke: where its ink is beam-thick.
#
# `thickness_ratio` is the MEDIAN of the ink run through every column of the stroke's
# box. A detector box that runs past its beam reads the ink that is NOT the beam in
# those columns: Brahms 317803 pdf 0 (Sean's hand truth) staff 0 bar 3, a real beam
# 0.6 spaces thick in a box 362 px wide over a 152 px beam, 58% of its columns a bare
# staff line -- median 1.3 lines, refused `too_thin`, and six beamed heads read
# "eighth or quarter". The cut is not wrong (every beam stroke that fits its beam
# measures 2.5-3.9 lines on that page); the reading was taken over columns that are
# not the beam's. `FINDINGS.md` 2.82.
#
# The CORE is the longest stretch of consecutive columns (median-smoothed over
# `BEAM_INK_CORE_SMOOTH_SPACES` so one white speck does not break a beam) whose ink run
# is at least `BEAM_INK_CORE_RATIO` staff lines, at least `BEAM_INK_CORE_MIN_SPACES`
# long, with the thickness it holds there and whether a stem stands at EACH END of the
# core -- off the same ink. A reading; the verdict on it is `rhythm`'s.
#
# ⚠️ `BEAM_INK_CORE_RATIO` IS `rhythm.BEAM_THICKNESS_RATIO_MIN` AND A TEST PINS THEM
# EQUAL: gather may not import an adjudicator, and two spellings of one number drift.
# ─────────────────────────────────────────────────────────────────────────────

BEAM_INK_CORE_RATIO = 1.75
#: A stretch shorter than this is a head, a stem's foot or a blot. A notehead is ~1.3
#: spaces wide, and the beam between two stems of the closest-set group is longer.
BEAM_INK_CORE_MIN_SPACES = 2.0
BEAM_INK_CORE_SMOOTH_SPACES = 0.3


def _ink_runs(col: Any) -> List[Tuple[int, int]]:
    """`(start, end_exclusive)` of every run of True in a 1-D bool array."""
    import numpy as np
    # ROADMAP 2.191: the same runs as `np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))`,
    # without np.diff / concatenate's per-call overhead (this is called millions of times a page).
    c = np.zeros(len(col) + 2, np.int8)
    c[1:-1] = col
    d = c[1:] - c[:-1]
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def _best_overlap_runs(slab: Any, off: float, lo_v: float, hi_v: float):
    """For every column of the 2-D bool `slab` (row 0 is page row `off`): the run of True whose overlap with
    `[lo_v, hi_v]` is the largest and positive (the FIRST of equals), as `(columns, starts, ends_exclusive)` int arrays
    in column order, columns with no overlapping run absent. ROADMAP 2.191: the per-column python loop of
    `_ink_runs` + max-overlap that `beam_stroke_ink` and `local_line_thickness` ran, done for all columns at once;
    it picks exactly the run that loop picked (same float arithmetic, strict `>` = first of equals)."""
    import numpy as np
    n_rows, n_cols = slab.shape
    e0 = np.zeros(0, np.int64)
    if n_rows == 0 or n_cols == 0:
        return e0, e0, e0
    pad = np.zeros((n_cols, n_rows + 2), np.int8)
    pad[:, 1:-1] = slab.T
    d = pad[:, 1:] - pad[:, :-1]
    sc, sr = np.nonzero(d == 1)
    _ec, er = np.nonzero(d == -1)
    if len(sc) == 0:
        return e0, e0, e0
    ov = np.minimum(er + off, hi_v) - np.maximum(sr + off, lo_v)
    good = ov > 0.0
    if not good.any():
        return e0, e0, e0
    c, o, s_, e_ = sc[good], ov[good], sr[good], er[good]
    first = np.flatnonzero(np.concatenate([[True], c[1:] != c[:-1]]))
    mx = np.maximum.reduceat(o, first)
    counts = np.diff(np.concatenate([first, [len(c)]]))
    sel = np.flatnonzero(o == np.repeat(mx, counts))
    cs = c[sel]
    sel = sel[np.concatenate([[True], cs[1:] != cs[:-1]])]
    return c[sel], s_[sel], e_[sel]


def _median_filter_1d(a: Any, k: int) -> Any:
    import numpy as np
    k |= 1
    h = k // 2
    pad = np.pad(a, h, mode="edge")
    if len(a) == 0:
        return np.array([])
    # ROADMAP 2.191: every window's median at once (k is odd: the middle element, no averaging), same values as the
    # per-window `np.median` loop.
    from numpy.lib.stride_tricks import sliding_window_view
    return np.median(sliding_window_view(pad, k)[:len(a)], axis=1)


def local_line_thickness(ink: Any, line_ys: Sequence[float], x0: int, x1: int,
                         space: float) -> Optional[float]:
    """The thickness, in canonical px, of this cell's staff lines AT columns
    `x0..x1` (and `BEAM_INK_LINE_FLANK_SPACES` either side) -- read off the
    UNERASED ink, `None` where fewer than two lines show one. ROADMAP 2.74.
    LOCAL on purpose (CLAUDE.md §10: measure against the staff where the
    subject is, never staff-wide).

    ⚠️ A BEAM LYING ON A STAFF LINE MERGES WITH IT, and ink only ever ADDS to
    a line's run, so the lines this reads are the lower bound of their own
    columns: each line's 25th percentile over the columns it is read at (a
    cell dense with stems and heads covers a line over most of a bar), then
    the SECOND-thinnest line (the thinnest where only three are readable).
    The pooled median was measured and refused: a two-level beam standing on
    two of a staff's five lines pooled to 54 px against a true 23 and read a
    real beam as a hairpin; on Litolff p3 a bar of merged stems read 58-63 px
    on its top lines against a true 29.
    """
    import numpy as np
    H, W = ink.shape
    half = 0.2 * space
    flank = BEAM_INK_LINE_FLANK_SPACES * space
    cx0, cx1 = max(0, int(x0 - flank)), min(W, int(x1 + flank))
    per_line: List[float] = []
    for ly in line_ys:
        lo, hi = max(0, int(ly - 0.5 * space)), min(H, int(ly + 0.5 * space) + 1)
        if hi <= lo:
            continue
        # the run that sits on the line's own row, measured over a wider
        # slice so a line thicker than the window is not clipped to it
        _c, _s, _e = _best_overlap_runs(ink[lo:hi, cx0:cx1], lo, ly - half, ly + half)
        vals = (_e - _s)
        if len(vals) >= 8:
            per_line.append(float(np.percentile(vals, 25)))
    if len(per_line) < 3:
        return min(per_line) if len(per_line) >= 1 else None
    per_line.sort()
    return per_line[1] if len(per_line) >= 4 else per_line[0]


def _stem_at_end(ink: Any, x_end: float, band: Tuple[float, float],
                 space: float) -> Dict[str, Any]:
    """Is there a vertical run at one END of a stroke that leaves its band by
    `BEAM_INK_END_STEM_SPACES` or more? `inside` is +1 for the left end (the
    ROADMAP 2.74."""
    H, W = ink.shape
    reach = BEAM_INK_END_STEM_SPACES * space
    half = max(2, int(round(BEAM_INK_END_WINDOW_SPACES * space)))
    xs = [int(round(x_end)) + o for o in range(-half, half + 1)]
    xs = [x for x in xs if 0 <= x < W]
    if not xs:
        return {"found": None, "x": None}
    top, bot = band
    ymid = int(round((top + bot) / 2.0))
    hits = []
    thru = []
    ups = []
    downs = []
    for cx in xs:
        col = ink[:, cx]
        if not (0 <= ymid < H):
            continue
        # the run through the stroke's own band at this column
        rs = _ink_runs(col)
        for s, e in rs:
            if s <= ymid < e or (s <= bot and e >= top):
                if (top - s) >= reach or (e - bot) >= reach:
                    hits.append(cx)
                    if (top - s) >= reach and (e - bot) >= reach:
                        thru.append(cx)
                    elif (top - s) >= reach:
                        ups.append(cx)
                    else:
                        downs.append(cx)
                break
    need = max(2, int(round(0.08 * space)))
    if len(hits) >= need:
        # ⚠️ ROADMAP 2.82: `through` -- the run leaves the band by `reach` on BOTH sides.
        # A stem hangs from its beam on ONE side (the beam is flush at the stem's far
        # end); a run that goes both ways through the band is a BARLINE or a lattice of
        # merged staff-line ink. `side` -- WHICH side the stem runs to ("up": above
        # the band, "down": below), so a consumer can look for the head at its far end.
        side = ("both" if len(thru) >= need else
                "up" if len(ups) >= len(downs) else "down")
        return {"found": True, "x": round(float(sum(hits)) / len(hits), 1),
                "through": len(thru) >= need, "side": side}
    return {"found": False, "x": None, "through": False, "side": None}


def _beam_core(ink: Any, xs: Any, th: Any, tops: Sequence[float],
               bots: Sequence[float], line: Optional[float], space: float
               ) -> Optional[Dict[str, Any]]:
    """The core of one stroke (see the 2.82 block above), or `None` where no stretch of
    `BEAM_INK_CORE_MIN_SPACES` is `BEAM_INK_CORE_RATIO` lines thick, or where no staff
    line was measurable (never a pixel default). `xs`/`th` are the per-column x and ink
    run length `beam_stroke_ink` already read; columns with no ink are absent from
    them, so a stretch is only consecutive where `xs` is."""
    import numpy as np
    if not line or line <= 0 or len(xs) < 3:
        return None
    k = max(3, int(round(BEAM_INK_CORE_SMOOTH_SPACES * space)))
    sm = _median_filter_1d(th, k)
    thick = sm >= BEAM_INK_CORE_RATIO * line
    best = None                                  # (length in columns, first, last)
    i, n = 0, len(xs)
    while i < n:
        if not thick[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and thick[j + 1] and xs[j + 1] == xs[j] + 1:
            j += 1
        length = int(xs[j] - xs[i] + 1)
        if best is None or length > best[0]:
            best = (length, i, j)
        i = j + 1
    if best is None or best[0] < BEAM_INK_CORE_MIN_SPACES * space:
        return None
    _, a, b = best
    x0, x1 = float(xs[a]), float(xs[b])
    core_th = float(np.median(th[a:b + 1]))
    band = (float(np.median(np.asarray(tops[a:b + 1], float))),
            float(np.median(np.asarray(bots[a:b + 1], float))))
    return {"x0": x0, "x1": x1, "spaces": round((x1 - x0 + 1) / space, 3),
            "thickness_px": round(core_th, 2),
            "thickness_ratio": round(core_th / line, 3),
            "end_stems": [_stem_at_end(ink, x0, band, space),
                          _stem_at_end(ink, x1, band, space)],
            "band": [round(band[0], 1), round(band[1], 1)]}


def beam_stroke_ink(gray: Any, box: Tuple[float, float, float, float],
                    space: float, line_ys: Sequence[float]
                    ) -> Optional[Dict[str, Any]]:
    """Three rulers over one candidate beam stroke's own ink, off the
    UNERASED cell raster (`gray`, uint8, 2-D). `None` -- declined -- where
    the stroke has ink in fewer than `BEAM_INK_MIN_COVER` of its columns or
    the unit is missing. ROADMAP 2.74.

    * `thickness_px` / `thickness_spaces` / `thickness_ratio`: the median
      length of the ink run through the stroke at each of its columns, against
      the staff lines' own thickness AT those columns (`None` ratio where no
      line was measurable).
    * `sagitta_spaces`: how far the stroke's centre line bows from straight,
      from a parabola fitted to the median-filtered centres (`None` where the
      stroke is shorter than one space).
    * `end_stems`: for each end (left, right) whether a vertical run leaves
      the band there -- `found` True/False, `x` the column.
    * `core` (ROADMAP 2.82): the longest stretch where the run is
      `BEAM_INK_CORE_RATIO` lines thick or more, with its own `x0`/`x1`, `spaces`,
      `thickness_ratio` and `end_stems` read at ITS ends; `None` where there is none.

    ⚠️ THE UNERASED raster, not `image_no_staff`: the staff-erase thins a beam
    that crosses a line (a beam read 34 px thick on the erased image and 49 on
    the original, same stroke).
    """
    import numpy as np
    if gray is None or getattr(gray, "ndim", 0) != 2 or not space or space <= 0:
        return None
    ink = gray < BEAM_INK_THRESHOLD
    H, W = ink.shape
    x, y, w, h = [float(v) for v in box]
    xi0, xi1 = max(0, int(round(x))), min(W, int(round(x + w)))
    if xi1 - xi0 < 8:
        return None
    pad = int(round(0.5 * space))
    y0, y1 = max(0, int(round(y)) - pad), min(H, int(round(y + h)) + pad)
    if y1 <= y0:
        return None
    _c, _s, _e = _best_overlap_runs(ink[y0:y1, xi0:xi1], y0, y, y + h)
    xs: List[int] = (_c + xi0).tolist()
    th: List[int] = (_e - _s).tolist()
    cs: List[float] = (y0 + (_s + _e) / 2.0).tolist()
    tops: List[float] = (_s + y0).astype(float).tolist()
    bots: List[float] = (_e + y0).astype(float).tolist()
    if len(xs) < BEAM_INK_MIN_COVER * (xi1 - xi0):
        return None
    xs_a, th_a, cs_a = (np.array(xs, float), np.array(th, float),
                        np.array(cs, float))
    thick = float(np.median(th_a))
    line = local_line_thickness(ink, line_ys, xi0, xi1, space)
    # ⚠️ THE BOW IS THE STRAIGHTEST OF THREE LINES -- the centre and the two
    # edges. A beam fused to a slur's tapering tail or a hairpin's line has a
    # ragged centre but one clean straight edge; an ARC is curved on every
    # one of them. Taking the smallest bow refuses an arc and keeps a beam
    # with something stuck to it (a real Brahms p1 beam fused to a slur
    # read 0.53 spaces by its centre line and 0.01 by its upper edge).
    k = max(5, int(round(0.6 * space)))
    trim = min(len(xs) // 6, int(round(BEAM_INK_END_TRIM_SPACES * space)))
    sag = None
    for edge in (cs_a, np.array(tops, float), np.array(bots, float)):
        sm = _median_filter_1d(edge, k)
        xx, yy = xs_a[trim:len(xs) - trim], sm[trim:len(xs) - trim]
        if len(xx) >= 12 and (xx[-1] - xx[0]) >= space:
            t = (xx - xx.mean()) / max(1.0, (xx[-1] - xx[0]) / 2.0)
            bow = abs(float(np.polyfit(t, yy, 2)[0])) / space
            sag = bow if sag is None else min(sag, bow)
    # the stroke's own band, for the end-stem test: its median top/bottom
    band = (float(np.median(cs_a - th_a / 2.0)), float(np.median(cs_a + th_a / 2.0)))
    ends = [_stem_at_end(ink, xs_a[0], band, space),
            _stem_at_end(ink, xs_a[-1], band, space)]
    return {"thickness_px": round(thick, 2),
            "line_px": None if line is None else round(line, 2),
            "thickness_ratio": (None if not line else round(thick / line, 3)),
            "thickness_spaces": round(thick / space, 3),
            "sagitta_spaces": None if sag is None else round(sag, 4),
            "end_stems": ends,
            "columns": int(len(xs)),
            "cover": round(len(xs) / float(xi1 - xi0), 3),
            "band": [round(band[0], 1), round(band[1], 1)],
            # ROADMAP 2.82: where the ink is beam-thick, and whether a stem stands at
            # each end of THAT -- `None` where nothing is (or no line was measurable).
            "core": _beam_core(ink, xs_a, th_a, tops, bots, line, space)}


def gather_beam_stroke_ink(log: Log, cells: Sequence[Any],
                           local: Dict[int, Tuple[int, int]]) -> None:
    """`Q.BEAM_STROKE_INK` -- one row per `Q.BEAM_STROKE` row in each cell, CV
    and detector alike, keyed by `beam_row_id`. ROADMAP 2.74.

    ⚠️ AFTER `gather_cv_lines` AND `gather_detector_beams`, because it reads
    the strokes both filed. Each stroke is measured on ITS OWN box; no stem
    set is needed (the end-stem test reads the raster, not `Q.STEM`).
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
        rows = log.rows(Q.BEAM_STROKE, sub)
        if not rows:
            continue
        frame = frame_cell(c.measure_index)
        img = getattr(c, "image", None)
        gray = None
        if img is not None and getattr(img, "ndim", 0) >= 2:
            if img.ndim == 3:
                import cv2
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
        grid = _cell_grid(c)
        space = grid[1] * 2.0 if grid is not None else None
        line_ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        for r in rows:
            v = r.value
            if gray is None:
                log.abstain(sub, Q.BEAM_STROKE_INK, reader=READERS.CV_BEAM_SHAPE,
                            frame=frame, reason=ABSTAIN.NO_MASK,
                            beam_row_id=r.id, note="cell carries no image")
                continue
            if not space or space <= 0 or not isinstance(v, (list, tuple)) \
                    or len(v) < 4:
                log.abstain(sub, Q.BEAM_STROKE_INK, reader=READERS.CV_BEAM_SHAPE,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            beam_row_id=r.id, note="no cell staff-space unit")
                continue
            m = beam_stroke_ink(gray, tuple(float(t) for t in v[:4]), space,
                                line_ys)
            if m is None:
                log.abstain(sub, Q.BEAM_STROKE_INK, reader=READERS.CV_BEAM_SHAPE,
                            frame=frame, reason=ABSTAIN.NO_READING,
                            beam_row_id=r.id,
                            note="too little ink under the stroke's own box")
                continue
            log.observe(sub, Q.BEAM_STROKE_INK, m["thickness_spaces"],
                        reader=READERS.CV_BEAM_SHAPE, frame=frame,
                        beam_row_id=r.id, **m)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.140 -- how many beam strokes stand AT A STEM'S TIP (flag `OMR_BEAM_STEM_LEVELS`, default ON since 2026-10-16)
#
# Brahms p18 sys1 staff12 cell7 (2.136 control tile 4, Sean: "16,16"): three sixteenths under a double beam were decided
# plain eighths. STAGED GATHER found one `cv_lines` stroke over them (a staff line at the gap between the two beams ate the
# second one in the staff-erased image) and `rhythm._kept_beams` dropped the detector's box (it bounds the stack) because the
# CV stroke overlaps it in x; `levels_certain` = `levels_possible` = 1. The page shows two strokes at each stem.
#
# This reads them where a musician does: down a column just BESIDE each stem, at the stem's tip, on the UNERASED cell raster.
# A stroke = a vertical ink run at least `BEAM_STEM_RUN_MIN_SPACES` thick whose ink continues sideways at least
# `BEAM_STEM_RUN_REACH_MIN_SPACES` (a beam runs on to the next stem; a notehead is about a space and a quarter wide). A staff
# line is erased from the column unless ink stands outside it and runs unbroken across it, so a lone line is never a stroke
# and a beam crossing a line is one. Both ends of the stem and both sides are filed (which end is the tip is a later stage's
# question, as in `Q.BEAM_STEM_JOIN`); each run carries its thickness in staff spaces so the consumer counts a run that is
# twice one beam as two (the gap between two beams can fill in on a scan: this plate's does).
# CONVENTION ASSUMED: a beam level is a full-width stroke at the stem's tip and further levels lie inward of it; WHAT WOULD
# FALSIFY IT: a head, a slur end, a hairpin or a stem of another voice that passes the 0.45 space column and has the reach
# (the reach test is what keeps a head out); NOT CONFIRMED beyond one Brahms cell and a Litolff sample (FINDINGS 2.140).
# ─────────────────────────────────────────────────────────────────────────────

BEAM_STEM_LEVELS_ENV = "OMR_BEAM_STEM_LEVELS"
#: Distance of the read column from the stem's centre line, staff spaces (clear of the stem's own width, inside a beam).
BEAM_STEM_COLUMN_OFFSET_SPACES = 0.45
#: The tip window, staff spaces: this far from the tip toward the head, and this far past it.
BEAM_STEM_WINDOW_IN_SPACES = 2.4
BEAM_STEM_WINDOW_OUT_SPACES = 0.3
#: A stroke is at least this thick (a staff line is ~0.2; a beam ~0.5-0.7 on the plates measured).
BEAM_STEM_RUN_MIN_SPACES = 0.36
#: ...and its ink continues sideways, away from the stem, at least this far (a notehead is ~1.2 wide).
BEAM_STEM_RUN_REACH_MIN_SPACES = 1.6
#: ...and at least this many staff-line thicknesses (measured locally, `local_line_thickness`): the existing convention that a beam is
#: thicker than a line (`rhythm.BEAM_THICKNESS_RATIO_MIN`, 1.75, Sean 2026-10-09, measured on both plates). 2.140 tiles 3 and 5
#: (Litolff): the "second stroke" was 0.38 sp = one staff line (Sean: eighths). Skipped where no line thickness was measurable.
BEAM_STEM_RUN_LINE_RATIO_MIN = 1.75


def beam_stem_levels_gather_enabled() -> bool:
    import os
    return os.environ.get(BEAM_STEM_LEVELS_ENV, "1").strip().lower() not in ("0", "", "false", "no", "off")


def _column_ink_without_lines(ink: Any, x: int, y0: int, y1: int, line_ys: Sequence[float], half: int) -> Any:
    """Bool ink down column `x` (3 px wide, majority), rows `y0..y1`, each staff-line BAND (line +- `half` px) kept as ink only
    where ink stands outside the band on a side and the raw ink is unbroken from that side across the band."""
    import numpy as np
    W = ink.shape[1]
    xa, xb = max(0, x - 1), min(W, x + 2)
    if xb <= xa or y1 <= y0:
        return np.zeros(max(0, y1 - y0), bool)
    raw = ink[y0:y1, xa:xb].mean(axis=1) >= 0.5
    col = raw.copy()
    n = len(col)
    for ly in line_ys:
        i = int(round(float(ly))) - y0
        lo, hi = i - half, i + half
        if hi < 0 or lo >= n:
            continue
        above = lo - 1 >= 0 and bool(raw[lo - 1])
        below = hi + 1 < n and bool(raw[hi + 1])
        for r in range(max(lo, 0), min(hi, n - 1) + 1):
            col[r] = bool((above and raw[max(lo, 0):r + 1].all()) or (below and raw[r:min(hi, n - 1) + 1].all()))
    return col


def beam_runs_at_stem_end(ink: Any, stem_x: float, tip_y: float, end: str, space: float,
                          line_ys: Sequence[float], line_px: float) -> Dict[str, Any]:
    """`{"left": [[y0, y1, spaces, reach_spaces], ...], "right": [...], "x": {"left": x, "right": x}}`: the strokes down the column
    `BEAM_STEM_COLUMN_OFFSET_SPACES` beside the stem on each side at the `end` ("top"/"bottom") of the stem, outermost (at the
    tip) first. Pure: `ink` is a bool raster (cell canonical px), geometry in the same px. ROADMAP 2.140."""
    H, W = ink.shape
    half = max(1, int(round(line_px / 2.0)) + 1) if line_px and line_px > 0 else max(1, int(round(0.12 * space)) + 1)
    if end == "top":
        y0, y1 = int(tip_y - BEAM_STEM_WINDOW_OUT_SPACES * space), int(tip_y + BEAM_STEM_WINDOW_IN_SPACES * space)
    else:
        y0, y1 = int(tip_y - BEAM_STEM_WINDOW_IN_SPACES * space), int(tip_y + BEAM_STEM_WINDOW_OUT_SPACES * space)
    y0, y1 = max(0, y0), min(H, y1)
    out: Dict[str, Any] = {"x": {}}
    for name, sgn in (("left", -1), ("right", 1)):
        x = int(round(stem_x + sgn * BEAM_STEM_COLUMN_OFFSET_SPACES * space))
        out["x"][name] = x
        if not (0 <= x < W) or y1 - y0 < 4:
            out[name] = []
            continue
        col = _column_ink_without_lines(ink, x, y0, y1, line_ys, half)
        runs = []
        for a, b in _ink_runs(col):
            th = (b - a) / space
            if th < BEAM_STEM_RUN_MIN_SPACES:
                continue
            if line_px and line_px > 0 and (b - a) < BEAM_STEM_RUN_LINE_RATIO_MIN * line_px:
                continue
            # how far the ink goes on sideways from the column, along the run's middle row (away from the stem)
            ym = y0 + (a + b) // 2
            reach, xx = 0, x
            while 0 <= xx + sgn < W and ink[ym - 1:ym + 2, xx + sgn].any() and reach < 3 * space:
                xx += sgn
                reach += 1
            if reach / space >= BEAM_STEM_RUN_REACH_MIN_SPACES:
                runs.append([y0 + a, y0 + b, round(th, 3), round(reach / space, 2)])
        runs.sort(key=lambda r: r[0] if end == "top" else -r[1])
        out[name] = runs
    return out


def gather_beam_stem_levels(log: Log, cells: Sequence[Any], local: Dict[int, Tuple[int, int]]) -> None:
    """`Q.BEAM_STEM_LEVELS` -- one row per `Q.STEM` row (CV) of each cell, keyed by `stem_row_id`: value = the larger of the two
    ends' best-side stroke counts (a stroke counted once however thick); `detail.ends` = `{top, bottom}` each with the strokes
    on its left and right (`beam_runs_at_stem_end`). A ruler: how much ink in how many strokes stands at a stem's tip; it names
    neither a level nor a beam. Off unless `OMR_BEAM_STEM_LEVELS` (ROADMAP 2.140). Abstains where the cell has no raster or
    unit. AFTER `gather_cv_lines` (it reads the stems)."""
    if not beam_stem_levels_gather_enabled():
        return
    import numpy as np
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        stems = [r for r in log.rows(Q.STEM, sub) if r.reader == READERS.CV_LINES]
        if not stems:
            continue
        frame = frame_cell(c.measure_index)
        img = getattr(c, "image", None)
        gray = None
        if img is not None and getattr(img, "ndim", 0) >= 2:
            if img.ndim == 3:
                import cv2
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
        grid = _cell_grid(c)
        space = grid[1] * 2.0 if grid is not None else None
        line_ys = list(getattr(c, "staff_line_ys_canonical", None) or [])
        if gray is None or not space or space <= 0:
            for r in stems:
                log.abstain(sub, Q.BEAM_STEM_LEVELS, reader=READERS.CV_BEAM_LEVELS, frame=frame,
                            reason=ABSTAIN.NO_MASK if gray is None else ABSTAIN.NO_STAFF_GEOMETRY,
                            stem_row_id=r.id, note="no cell raster" if gray is None else "no cell staff-space unit")
            continue
        ink = np.asarray(gray < BEAM_INK_THRESHOLD)
        line_px = None
        try:
            line_px = local_line_thickness(ink, line_ys, 0, ink.shape[1], space)
        except Exception:
            line_px = None
        for r in stems:
            v = r.value
            if not isinstance(v, (list, tuple)) or len(v) < 4:
                continue
            x, y, w, h = [float(t) for t in v[:4]]
            ends = {}
            for end, tip in (("top", y), ("bottom", y + h)):
                ends[end] = beam_runs_at_stem_end(ink, x + w / 2.0, tip, end, space, line_ys, line_px or 0.0)
            best = max(len(e[side]) for e in ends.values() for side in ("left", "right"))
            log.observe(sub, Q.BEAM_STEM_LEVELS, best, reader=READERS.CV_BEAM_LEVELS, frame=frame,
                        stem_row_id=r.id, ends=ends)


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
        clefs = [d for d in dets
                 if _is_clef_class(d.smufl_name, d.category)]
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
    except Exception as exc:                                  # noqa: BLE001
        _stub_per_staff(log, cells, local, Q.CLEF_LOCATED, READERS.CV_LOCATOR,
                        FRAME_HEADER_WINDOW, "clef_locator unavailable",
                        error=type(exc).__name__)
        return

    # ⚠️ ROADMAP 2.60: a header cutter that THREW is not a staff with no
    # header geometry. The crop is still `None` (control flow unchanged), but
    # the row says the reader could not run and names the exception.
    header_error: Optional[str] = None
    try:
        header_cells = header_cells_for_page(pws)
    except Exception as exc:                                  # noqa: BLE001
        header_cells = {}
        header_error = type(exc).__name__

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
                if header_error is not None and frame == FRAME_HEADER_WINDOW:
                    log.abstain(sub, Q.CLEF_LOCATED,
                                reader=READERS.CV_LOCATOR, frame=frame,
                                reason=ABSTAIN.READER_UNAVAILABLE,
                                error=header_error,
                                note="header_cells_for_page raised")
                    continue
                log.abstain(sub, Q.CLEF_LOCATED, reader=READERS.CV_LOCATOR,
                            frame=frame, reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            note="no crop of this kind for this staff")
                continue
            occupied, occ_classes, occ_subjects = _occupied_notehead_rows(
                detections, p, key)
            # ⚠️ ROADMAP 2.11, THE FOURTH CONDITION, AND THE MEASUREMENT PUT
            # IT HERE. Brahms 1 p.6 `staff/6/1/3`: the detector reads `clefG`
            # at 0.688 on this very ink, and the first build of the override
            # took the staff to `tenor` -- a READ clef changed, which the
            # roadmap's gate forbids. A clef box on the cluster means the ink
            # is already CLAIMED by a clef, so "the notehead box is too small"
            # is not the complaint and which clef it is belongs to the clef
            # contest. It refuses the override and is never a veto of its own.
            clef_claimed = _clef_boxes(detections, p, key)
            trace: Dict[str, Any] = {}
            try:
                found = locate_clef(crop, occupied_boxes=occupied,
                                    occupied_classes=occ_classes,
                                    clef_boxes=clef_claimed, trace=trace)
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
            # ⚠️ ROADMAP 2.11 -- THE OVERRIDDEN BOXES ARE NAMED ON THE ROW,
            # and that is the whole of the connection. `notehead_precision`
            # refuses exactly these glyphs `is_a_clef`; it reads them off this
            # detail rather than re-deriving which box the clef sat on, so the
            # refusal cannot disagree with the read that caused it. A read
            # that overrode nothing carries neither key, so every ordinary
            # row is byte-identical to a pre-2.11 one.
            extra: Dict[str, Any] = {}
            if found.overrode_occupied:
                extra["overrides_notehead_box"] = True
                extra["overrode_glyph_subjects"] = [
                    occ_subjects[i] for i in found.overrode_occupied
                    if i < len(occ_subjects)]
            for k in ("w_spaces", "h_spaces"):
                if trace.get(k) is not None:
                    extra[k] = trace[k]
            log.observe(sub, Q.CLEF_LOCATED, found.read.name,
                        reader=READERS.CV_LOCATOR, frame=frame,
                        score=float(found.symmetry),
                        family=found.read.family, line=found.read.line,
                        line_source=found.read.source,
                        x_center=int(x0 + w / 2), bbox=list(found.bbox),
                        **extra)


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


def _occupied_notehead_rows(detections, page: int, key):
    """The same boxes, WITH the class and the glyph subject of each.

    ⚠️ ROADMAP 2.11. `_occupied_boxes` hands the locator four numbers and
    nothing to name them by, so a read that survives a box cannot say WHICH
    box it survived and the downstream refusal would have to re-derive the
    overlap -- a second, drifting copy of the intersection test. The subject
    key is exact rather than reconstructed: `gather_detections` files
    `R.glyph(p, s, st, cell, gi)` with `gi` the index into this same
    `detections[cell_key]` list, so the ordinal IS the identity.

    Returns `(boxes, classes, subjects)`, aligned by index. The class list is
    what opts this call site in to 2.11; callers that pass `_occupied_boxes`
    alone keep the pre-2.11 behaviour exactly.
    """
    cell_key = R.cell(page, key[0], key[1], 0).to_key()
    boxes, classes, subjects = [], [], []
    for gi, d in enumerate(detections.get(cell_key, ())):
        if d.smufl_name.startswith(_NOTEHEAD_PREFIX):
            boxes.append((d.x_canonical, d.y_canonical,
                          d.width_canonical, d.height_canonical))
            classes.append(d.smufl_name)
            subjects.append(R.glyph(page, key[0], key[1], 0, gi).to_key())
    return boxes, classes, subjects


def _clef_boxes(detections, page: int, key):
    """The boxes the detector already called a CLEF, in this staff's cell 0.

    ⚠️ ROADMAP 2.11's fourth condition, and it is NOT a widening of the veto:
    these boxes never enter `occupied_boxes`, so nothing that used to be read
    stops being read. They only REFUSE the override, which is strictly more
    conservative than the first build.

    ⚠️ `_is_clef_class` is the SAME predicate `gather_clef` uses to decide
    what a clef detection is. A second spelling of "is this a clef" would let
    the two disagree about the same box -- which is the exact shape of fault
    this file's own `_occupied_boxes` comment warns about one function up.
    """
    cell_key = R.cell(page, key[0], key[1], 0).to_key()
    return [(d.x_canonical, d.y_canonical,
             d.width_canonical, d.height_canonical)
            for d in detections.get(cell_key, ())
            if _is_clef_class(d.smufl_name, d.category)]


# ─────────────────────────────────────────────────────────────────────────────
# Declared stubs -- present, addressed, and honest about being empty
# ─────────────────────────────────────────────────────────────────────────────


def _stub_reason(error: Optional[str]) -> Tuple[str, Dict[str, Any]]:
    """The (reason, detail) a stub files (ROADMAP 2.61b): an import that FAILED
    is `READER_UNAVAILABLE` naming the exception class; no `error` is a reader
    that is genuinely not written, `NOT_IMPLEMENTED`."""
    if error:
        return ABSTAIN.READER_UNAVAILABLE, {"error": error}
    return ABSTAIN.NOT_IMPLEMENTED, {}


def _stub_per_staff(log: Log, cells: Sequence[Any],
                    local: Dict[int, Tuple[int, int]], quantity: str,
                    reader: str, frame: str, note: str,
                    error: Optional[str] = None) -> None:
    """One staff-level abstention per staff. `error`: see `_stub_cv_lines`."""
    reason, detail = _stub_reason(error)
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
                    reason=reason, note=note, **detail)


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
    # ⚠️⚠️ KEYED PER SYSTEM (`{"p1/s0": {staff_index: clef}}`), because a
    # printed score SUPPRESSES tacet staves: index 6 is the Timpani on a full
    # system and Violino I on one that drops it, so a single index-keyed dict
    # seeds the timpani's `bass` onto a violin. That is the 12-of-75 graft.
    # ⚠️ No dossier file carries this key at all -- it is the OUTPUT of the
    # part-to-staff join, supplied by a CONFIRMED fact sheet
    # (`factsheet.clef_by_staff`). A raw dossier still seeds nothing, which is
    # what it has always silently done.
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.staff(c.page_index, key[0], key[1])
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        per_system = clefs.get(f"p{c.page_index}/s{key[0]}") or {}
        value = per_system.get(key[1]) or per_system.get(str(key[1]))
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

#: The IN-BAR accidental classes, and the KEY class each one SHARES A SHAPE
#: with.
#:
#: ⚠️⚠️ **THE DETECTOR'S CLASS IS TWO CLAIMS AND ONLY ONE OF THEM IS ITS
#: BUSINESS** (Sean, 2026-09-23). The SHAPE — flat, sharp, natural — is what
#: it is good at. The ROLE — *is this a key signature member or an in-bar
#: accidental?* — is GEOMETRY: a key member stands between the clef and the
#: first barline, on the ladder; an accidental stands left of a head inside
#: the bar. Until this line `_KEYSIG_CLASSES` was used as a FILTER, so a flat
#: the detector labelled with the in-bar class was dropped from the header run
#: before any reader saw it — silently, at GATHER, where no derived check can
#: see it (CLAUDE.md §4d).
#:
#: ⚠️ MEASURED on the two whole-movement records, over cell 0 of every staff:
#: Litolff **437 `keyFlat` against 174 `accidentalFlat`** (+35 natural, 21
#: sharp), with **53 header cells carrying an accidental-class box and NO
#: key-class box at all**; Breitkopf **1,150 against 660**, 84 accidental-only
#: header cells. That is the under-count §6a blamed on the plate, and a
#: sizeable part of it is a class name.
#:
#: ⚠️ DOUBLE sharps and flats are NOT here. They cannot stand in a standard
#: signature (`[C21]`'s ladder has one accidental per slot), so a
#: `accidentalDoubleFlat` in a header is either a misdetection or music, and
#: admitting it would be widening the reader rather than un-filtering it.
_ACCIDENTAL_SHAPE = {"accidentalFlat": "keyFlat",
                     "accidentalSharp": "keySharp",
                     "accidentalNatural": "keyNatural"}

#: Seven slots, about a staff space apart — `[C21]`, and the same bound
#: `adjudicators/header.MAX_FIFTHS` states one stage on. Written here rather
#: than imported because `adjudicators` imports this module's stage, not the
#: other way round.
_MAX_KEYSIG_SLOTS = 7.0


def _keysig_header_limit() -> float:
    """How far into cell 0 an accidental-SHAPED box may sit and still be a
    member of the header's signature, in the CELL's own staff spaces.

    ⚠️ DERIVED FROM BOUNDS THAT WERE ALREADY MEASURED, never typed here: the
    locator's `clef_anchor_max_start_spaces` (5.50, swept over 42
    ground-truth staves plus WTC p.17 — *"every real clef stands between 1.2
    and 4.3 spaces from the window's left edge"*), its
    `max_start_after_clef_spaces` (2.00 — *"a key signature is printed hard
    against its clef"*), and seven slots a space apart (`[C21]`). A box past
    that sum is in the BAR, and this is the geometry half of the role the
    detector's class name was being trusted for.

    ⚠️ IT BOUNDS ONLY THE NEWLY ADMITTED CLASS. A `keyFlat` box is admitted
    wherever the detector drew it, exactly as before, so this cannot remove a
    row any shipped record holds — `_marker_run`'s ladder still decides which
    of them form a RUN, and that is the test that has been measured.
    """
    from ..key_signature_locator import DEFAULT_LOCATOR_CONFIG as _cfg
    return (_cfg.clef_anchor_max_start_spaces
            + _cfg.max_start_after_clef_spaces + _MAX_KEYSIG_SLOTS)


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
    except Exception as exc:                                  # noqa: BLE001
        _stub_per_staff(log, cells, local, Q.KEYSIG_RUN_POSITION,
                        READERS.CV_HEADER, FRAME_HEADER_WINDOW,
                        "key_signature_locator unavailable",
                        error=type(exc).__name__)
        return

    # ⚠️ ROADMAP 2.60: a header cutter that THREW abstains
    # `READER_UNAVAILABLE` with the exception class, not `NO_STAFF_GEOMETRY`.
    header_error: Optional[str] = None
    try:
        header_cells = header_cells_for_page(pws)
    except Exception as exc:                                  # noqa: BLE001
        header_cells = {}
        header_error = type(exc).__name__

    for staff_index, key in sorted(local.items()):
        sub = R.staff(p, key[0], key[1])
        _gather_keysig_markers(log, sub, detections, p, key, geometry=_marker_geometry(pws, cells, staff_index))

        crop = header_cells.get(staff_index)
        if crop is None:
            if header_error is not None:
                log.abstain(sub, Q.KEYSIG_RUN_POSITION,
                            reader=READERS.CV_HEADER,
                            frame=FRAME_HEADER_WINDOW,
                            reason=ABSTAIN.READER_UNAVAILABLE,
                            error=header_error,
                            note="header_cells_for_page raised")
                continue
            log.abstain(sub, Q.KEYSIG_RUN_POSITION, reader=READERS.CV_HEADER,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue

        occupied = _occupied_boxes(detections, p, key, FRAME_HEADER_WINDOW)
        positions = None
        fitted_any = False
        fit_errors: List[str] = []
        for candidate in _SLOT_TABLE_CLEFS:
            try:
                found = locate_key_signature(crop, candidate,
                                             occupied_boxes=occupied)
            except Exception as exc:                          # noqa: BLE001
                # ⚠️ ROADMAP 2.60: a fit that THREW is not a fit that failed.
                log.abstain(sub, Q.KEYSIG_CLEF_FIT, reader=READERS.CV_HEADER,
                            frame=FRAME_HEADER_WINDOW,
                            reason=ABSTAIN.READER_UNAVAILABLE,
                            error=type(exc).__name__, candidate=candidate)
                fit_errors.append(type(exc).__name__)
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

        _gather_keysig_template(log, sub, crop)

        if not fitted_any and fit_errors:
            # ⚠️ ROADMAP 2.60: a candidate that threw might have fitted, so
            # "no candidate clef's slot table fits" is not ours to say.
            log.abstain(sub, Q.KEYSIG_RUN_POSITION, reader=READERS.CV_HEADER,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=fit_errors[0],
                        note="locate_key_signature raised on a candidate "
                             "clef and none fitted",
                        clefs_tried=list(_SLOT_TABLE_CLEFS))
            continue
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


def _gather_keysig_template(log: Log, sub: Subject, crop: Any) -> None:
    """The SECOND key-signature reader — `key_signature_template`.

    ⚠️ WHY A SECOND ONE AT ALL. `ASSUMPTIONS.md` D20 records that GATHER read
    key signatures with `key_signature_locator` alone, *"the weaker of the two
    readers this repo has, by a margin measured on the very page the first
    shadow run used"* -- `transcribe.py:1521` puts the locator at 2 of 12
    staves on Beethoven 5 p.1 given the correct clef and this reader at 11.
    Measured on pdf pages 1-4 of that edition against a hand-read print
    truth, over 75 printed staves: the locator decides 16 correctly and this
    reader 28, and they are COMPLEMENTARY rather than ranked -- on page 1 the
    template reads all twelve staves right and the locator two, and on page 2
    system 0 the locator reads five right and the template four different
    ones.

    ⚠️ IT IS ASKED ONCE PER CANDIDATE CLEF, exactly as the locator is, and for
    the same reason: the slot table is chosen by the clef, and a reader given
    a guessed clef is guessing twice.

    ⚠️ IT IS NOT ASKED FOR `positions`, AND NOT FILED UNDER
    `Q.KEYSIG_CLEF_FIT`. See that quantity's note: `adjudicate_clef` weighs
    those rows, so pooling the two readers there would move the CLEF decision,
    which nothing has measured.

    ⚠️ A `fifths` OF 0 FROM THIS READER IS A POSITIVE CLAIM, not an
    abstention -- `read_key_signature`'s own docstring says so: *"`fifths` 0
    when the window between clef and meter is clean -- that is a positive
    reading of 'no signature here'."* It is exactly the claim the locator
    cannot make, which is why it reaches the horns, trumpets and timpani that
    genuinely print none; and it is exactly the claim that is WRONG when the
    window is empty for some other reason, which is why the header-window
    repair in `staff_header.measure_header_window` had to land first.
    """
    # ⚠️ ROADMAP 2.60: a reader that cannot import, or THROWS on a candidate,
    # abstains `READER_UNAVAILABLE` with the exception class.
    try:
        from ..key_signature_template import read_key_signature
    except Exception as exc:                                  # noqa: BLE001
        log.abstain(sub, Q.KEYSIG_TEMPLATE_FIT, reader=READERS.TEMPLATE,
                    frame=FRAME_HEADER_WINDOW,
                    reason=ABSTAIN.READER_UNAVAILABLE,
                    error=type(exc).__name__)
        return
    for candidate in _SLOT_TABLE_CLEFS:
        try:
            read = read_key_signature(crop, candidate)
        except Exception as exc:                              # noqa: BLE001
            log.abstain(sub, Q.KEYSIG_TEMPLATE_FIT, reader=READERS.TEMPLATE,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=type(exc).__name__, candidate=candidate)
            continue
        if read is None:
            continue
        log.observe(sub, Q.KEYSIG_TEMPLATE_FIT, candidate,
                    reader=READERS.TEMPLATE, frame=FRAME_HEADER_WINDOW,
                    n_accidentals=abs(read.fifths),
                    accidental=read.accidental,
                    fifths=read.fifths)


def _spacing_from_lines(lines) -> float:
    """The median distance between a staff's five lines (page px)."""
    d = sorted(float(b) - float(a) for a, b in zip(lines, lines[1:]))
    return d[len(d) // 2] if d else 0.0


def _marker_geometry(pws: Any, cells: Sequence[Any], staff_index: int):
    """`(cell, staff line ys, page binary)` for the key markers' staff step (ROADMAP 2.187b, flag `OMR_KEY_PER_SYSTEM`), else None."""
    from . import key_object as KO
    if not KO.enabled():
        return None
    st = next((x for x in pws.staves if x.staff_index == staff_index), None)
    c = next((x for x in cells if x.staff_index == staff_index and x.measure_index == 0), None)
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if st is None or c is None or binary is None or len(list(st.line_ys)) < 5:
        return None
    return c, [float(v) for v in st.line_ys], binary


def _family_marker_shape(d: Any) -> Optional[str]:
    """ROADMAP 2.201 (flag `OMR_ACCIDENTAL_FAMILY`; a box carries `accidental_family` only then): a key marker's SHAPE -- the TYPE its own strokes read,
    else the detector's class shape (exactly what the marker gatherer always took). The key*/accidental* label stays on the row as `detector_class`."""
    fam = getattr(d, "accidental_family", None)
    if fam is not None and fam["type"] in _acc_family.TYPES:
        return _acc_family.KEY_SHAPE_OF_TYPE[fam["type"]]
    return d.smufl_name if d.smufl_name in _KEYSIG_CLASSES else _ACCIDENTAL_SHAPE.get(d.smufl_name)


def _family_in_bar(d: Any) -> bool:
    """ROADMAP 2.201: `head_right` (a mark directly left of a notehead at its own height) is RECORDED on the family row as role evidence, and it is NOT used to
    leave a mark out of the key run: measured on Litolff it removed 4 genuine key flats (x 517-730, the first or last flat of a mid-piece signature, which no
    meter follows, so a head stands within a space of it) and moved 59 of 126 staves' key verdicts. False until a role test that cannot take a key flat exists."""
    return False


def _gather_keysig_markers(log: Log, sub: Subject, detections, p: int,
                           key, geometry=None) -> None:
    """The DETECTOR's accidental SHAPES in the staff's header, with its own
    class recorded beside them as an opinion about the ROLE.

    ⚠️⚠️ THE VALUE IS THE SHAPE, AND THAT IS WHAT MAKES THE WIDENING SAFE FOR
    EVERY READER DOWNSTREAM. A flat boxed `accidentalFlat` is filed as
    `keyFlat` with `detector_class="accidentalFlat"` and
    `detector_role="accidental"`, so `_marker_run` — which abstains
    `mixed_marker_kinds` on a run of two KINDS — sees one kind, and a record
    written before this change reads identically. The detector's role-claim is
    on the row as one witness's opinion and is never the filter (Sean,
    2026-09-23).

    ⚠️ THE ROLE THE **RECORD** SETTLES IS STILL GEOMETRY, and it is
    `_marker_run`'s ladder, one stage on: slots within 0.5 spaces are one
    slot, a gap wider than 2.0 spaces ends the run. This function only stops
    admitting the detector's class name as a veto, and bounds the newly
    admitted class by `_keysig_header_limit`.

    ⚠️ NO SCALE, NO WIDENING. Without a measured `Q.CELL_STAFF_SPACE` the
    limit has no unit, so the accidental-class boxes are refused and the
    behaviour is exactly the shipped one — the same refusal `_marker_run`
    makes under `no_cell_scale`, and for the same reason: guessing the scale
    is how three flats become five.
    """
    cell = R.cell(p, key[0], key[1], 0)
    cell_key = cell.to_key()
    space = 0.0
    for row in log.rows(Q.CELL_STAFF_SPACE, cell):
        try:
            space = float(row.value)
        except (TypeError, ValueError):
            space = 0.0
    limit = _keysig_header_limit() * space if space > 0 else 0.0

    here = list(detections.get(cell_key, ()))
    # ⚠️⚠️ THE WIDENING IS ONE-SIDED IN ITS **SHAPE** TOO, AND THE FIRST DRAFT
    # WAS NOT — IT COST 84 RUNS ON BREITKOPF, 35 OF THEM READING THE RIGHT
    # ANSWER. `_gather_keysig_markers` reads `R.cell(p, s, i, 0)`, the whole
    # first MEASURE, so a natural or a sharp printed INSIDE bar 1 sits in this
    # population; admitting it turned a clean three-flat run into
    # `mixed_marker_kinds` on the shattering plate. `[C21]`: a standard
    # signature carries ONE kind. So where the detector's own KEY-class boxes
    # say which kind this header is, an accidental-shaped box of a DIFFERENT
    # kind is not a member of it — it is the in-bar accidental the detector
    # said it was. Where there is no key-class box at all (53 header cells on
    # Litolff, 81 on Breitkopf) nothing says which kind, so they are all
    # admitted and `_marker_run` abstains if they disagree.
    # ⚠️ ROADMAP 2.201 (flag `OMR_ACCIDENTAL_FAMILY`; a box carries `accidental_family` only then): the marker's SHAPE is the TYPE its own strokes read
    # (the detector's key*/accidental* label is a recorded fact and the role claim it always was), and a mark standing directly left of a notehead at its
    # own height (`head_right`) is IN-BAR by position, not a member of the signature.
    key_shapes = {_family_marker_shape(d) for d in here
                  if d.smufl_name in _KEYSIG_CLASSES and not _family_in_bar(d)}
    marks = []
    for d in here:
        if _family_in_bar(d):
            continue
        if d.smufl_name in _KEYSIG_CLASSES:
            marks.append((d, _family_marker_shape(d), "key"))
            continue
        if d.smufl_name not in _ACCIDENTAL_SHAPE:
            continue
        if limit <= 0 or float(d.x_canonical) > limit:
            continue
        shape = _family_marker_shape(d)
        if key_shapes and shape not in key_shapes:
            continue
        marks.append((d, shape, "accidental"))
    if not marks:
        log.abstain(sub, Q.KEYSIG_MARKER, reader=READERS.DETECTOR,
                    frame=frame_cell(0), reason=ABSTAIN.NO_DETECTIONS)
        return
    for d, shape, role in sorted(marks, key=lambda m: m[0].x_canonical):
        step_kw = {}
        if geometry is not None and space > 0:
            # ROADMAP 2.187b: the box centre's STEP below the staff's top line, against the lines at its own x (page-facts §3): the measurement
            # `header._in_fixed_order` judges the marker's slot against. Only with the flag on: a record without it reads as it always did.
            from . import key_object as KO
            gc, glines, gbin = geometry
            pb = _page_box(gc, d)
            if pb is not None:
                sp_page = _spacing_from_lines(glines)
                shift = KO.local_line_shift(gbin, glines, sp_page, pb[0], pb[2])
                step_kw["step"] = round(((pb[1] + pb[3]) / 2.0 - (glines[0] + shift)) / (sp_page / 2.0), 2)
        log.observe(sub, Q.KEYSIG_MARKER, shape,
                    reader=READERS.DETECTOR, frame=frame_cell(0),
                    score=float(d.confidence), x=d.x_canonical,
                    y_center=d.y_center, **step_kw,
                    # ⚠️ THE DISAGREEMENT, ON THE RECORD. A run read from two
                    # roles is exactly the case this change exists for, and a
                    # reader of the record can count them without re-running
                    # the detector.
                    detector_class=d.smufl_name, detector_role=role,
                    cell_staff_space=space,
                    **({"family_type": d.accidental_family["type"]} if getattr(d, "accidental_family", None) is not None else {}))


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
    except Exception as exc:                                  # noqa: BLE001
        _stub_per_staff(log, cells, local, Q.METER_TEMPLATE, READERS.TEMPLATE,
                        FRAME_HEADER_WINDOW, "time_signature_locator missing",
                        error=type(exc).__name__)
        return
    # ⚠️ ROADMAP 2.60: a header cutter that THREW abstains
    # `READER_UNAVAILABLE` with the exception class, not `NO_STAFF_GEOMETRY`.
    header_error: Optional[str] = None
    try:
        header_cells = header_cells_for_page(pws)
    except Exception as exc:                                  # noqa: BLE001
        header_cells = {}
        header_error = type(exc).__name__

    for staff_index, key in sorted(local.items()):
        sub = R.staff(p, key[0], key[1])
        _gather_meter_glyphs(log, sub, detections, p, key)

        crop = header_cells.get(staff_index)
        if crop is None and header_error is not None:
            log.abstain(sub, Q.METER_TEMPLATE, reader=READERS.TEMPLATE,
                        frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=header_error,
                        note="header_cells_for_page raised")
            continue
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

        _gather_meter_ocr_header(log, sub, crop)


def _gather_meter_ocr_header(log: Log, sub: Subject, crop: Any) -> None:
    """ROADMAP 2.29. `Q.METER_OCR` — Tesseract, on the SAME header crop
    `locate_time_signature` just read, split at the crop's own MIDDLE staff
    line (`crop.staff_line_ys_canonical[2]` of 5 -- see `meter_digit_ocr`'s
    own CONVENTION-ASSUMED note on the split). ⚠️ No flag: like
    `bar_number_text` (ROADMAP 2.13) this is Tesseract-only, always
    attempted, and abstains cleanly where Tesseract is unavailable -- there
    is nothing to gate.
    """
    try:
        from .. import meter_digit_ocr
    except Exception:                                         # noqa: BLE001
        log.abstain(sub, Q.METER_OCR, reader=READERS.TESSERACT,
                    frame=FRAME_HEADER_WINDOW,
                    reason=ABSTAIN.READER_UNAVAILABLE)
        return
    if not meter_digit_ocr.available():
        log.abstain(sub, Q.METER_OCR, reader=READERS.TESSERACT,
                    frame=FRAME_HEADER_WINDOW,
                    reason=ABSTAIN.READER_UNAVAILABLE)
        return
    image = getattr(crop, "image", None)
    line_ys = getattr(crop, "staff_line_ys_canonical", None) or []
    if image is None or image.size == 0 or len(line_ys) < 5:
        log.abstain(sub, Q.METER_OCR, reader=READERS.TESSERACT,
                    frame=FRAME_HEADER_WINDOW,
                    reason=ABSTAIN.NO_STAFF_GEOMETRY)
        return
    split_row = int(round(line_ys[2]))
    trace: Dict[str, Any] = {}
    try:
        found = meter_digit_ocr.read_meter_digits(
            image, split_row=split_row, trace=trace)
    except Exception:                                         # noqa: BLE001
        log.abstain(sub, Q.METER_OCR, reader=READERS.TESSERACT,
                    frame=FRAME_HEADER_WINDOW,
                    reason=ABSTAIN.READER_UNAVAILABLE)
        return
    if found is None:
        # ⚠️ THE COMMON CASE, exactly as `Q.METER_TEMPLATE`'s own abstention
        # says: a header window prints no meter almost everywhere a system
        # is not the movement's opening.
        log.abstain(sub, Q.METER_OCR, reader=READERS.TESSERACT,
                    frame=FRAME_HEADER_WINDOW,
                    reason=ABSTAIN.BELOW_THRESHOLD, **trace)
        return
    # ⚠️ SCORE, NOT JUST DETAIL — the same convention `Q.PRINTED_BAR_NUMBER`
    # (ROADMAP 2.13) uses for its own Tesseract mean confidence
    # (`conf / 100.0`). The WEAKER of the two halves, because a stack read
    # confidently on top and poorly on the bottom is only as sure as its
    # worst half.
    log.observe(sub, Q.METER_OCR, (found.numerator, found.denominator),
                reader=READERS.TESSERACT, frame=FRAME_HEADER_WINDOW,
                score=min(found.numerator_confidence,
                         found.denominator_confidence) / 100.0,
                numerator_confidence=found.numerator_confidence,
                denominator_confidence=found.denominator_confidence)


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


# ─────────────────────────────────────────────────────────────────────────────
# The template reader, aimed at a mid-staff BAR HEAD — a printed meter CHANGE
# ─────────────────────────────────────────────────────────────────────────────
#
# `gather_meter` hands `locate_time_signature` nothing but the HEADER window,
# one crop per staff, so a time signature printed anywhere else on the staff is
# read by the DETECTOR alone — which is the weak reader on exactly the ink it
# is worst at. Measured on Beethoven 5 / Litolff p.62, where a change is
# printed on every staff mid-system, `_meter_from_digits` gets it from a
# handful of staves and the same page's scan twin produces five spurious `4/4`
# changes just over the floor. The template reader is the best thing this
# project has for this family — 12 correct / 0 wrong / 3 missed / 40 correct
# abstentions across 11 sources — and it was never asked.
#
# ⚠️⚠️ THE HAZARD IS THE ONE THE KEY-SIGNATURE FAMILY ALREADY PAID FOR: *the
# reader that can say "zero" is the one that must never be given an empty
# window*. A mid-staff crop is an empty window almost everywhere, and
# `min_score` was calibrated on HEADER windows where a meter is usually
# present. So the acceptance question was MEASURED before the search was
# written, over 1,612 mid-staff bar-head windows on ten real scanned pages of
# two publishers (`benchmarks/omr-meter-template-changes-2026-09/`):
#
#   staves that must AGREE      false readings      false COLUMNS
#   ------------------------    --------------      -------------
#   1 (no consensus at all)     16                  16
#   2                            -                   2
#   3                            -                   0
#
# ⚠️ NOTHING HERE MOVES `min_score`, AND THAT IS A DECISION. Raising it looked
# tempting — the false answers thin out from 16 to 1 between 0.50 and 0.55 —
# but they thin out SMOOTHLY (16 / 7 / 2 / 1 at 0.50 / 0.52 / 0.54 / 0.55),
# with no gap anywhere, and a constant read off a smooth slope is fitted to a
# wish. It is also shared with the legacy path and set on an 11-source corpus.
# The safety is the CONSENSUS, which is a structural claim about how an
# engraver prints a meter change and not a number read off this corpus.

#: Flag. DEFAULT ON since ROADMAP 2.72 (it was default OFF and `research`
#: from 2.12i until then). Its off-switch is kept so one tree can A/B it.
#:
#: ⚠️ WHY IT CAME OUT OF `research`. 2.12i left it OFF because its own gate --
#: *state Brahms 1/i's printed `6/8` at bar 9 with a quorum* -- FAILED: the
#: whole-stack reader named `9/8` and `6/4` on two staves of fourteen. 2.72
#: found the cause (the stack's one correlation under-reads a heavy scan's
#: digits; read from each half the same ink gives `6/8` on all fourteen,
#: `time_signature_locator.locate_meter_by_halves`) and re-measured the hazard
#: that kept it unpriced: over 1,830 empty bar-head windows on ten real scanned
#: pages of two publishers the halves reader answered 3 (0.16%) and no column
#: had even TWO staves agree on one meter
#: (`benchmarks/omr-meter-digits-2026-09/FINDINGS.md`, ROADMAP 2.72). A GATHER
#: change still cannot be priced without a full re-gather -- the default is
#: flipped here on the PRINT (Sean's tiles 3 and 4, the held-bar sample) and
#: on that empty-window count, and the flag stays so the arm and the base can
#: be run on one tree.
#:
#: ⚠️ A DENY-LIST, BECAUSE THE DEFAULT IS ON. See CLAUDE.md, *A flag's OFF test
#: must follow its DEFAULT*: written as an allow-list a typo (`=ON!`) would
#: silently restore the bug the default exists to fix.
METER_TEMPLATE_AT_BAR_ENV = "OMR_METER_TEMPLATE_AT_BAR"

#: How wide the bar-head window is, in staff spaces.
#:
#: ⚠️ MEASURED, AND IT IS THE ONE LEVER THAT IS NOT A THRESHOLD. NCC's maximum
#: over a strip grows with the strip, so window width IS false-positive rate:
#: over the same 1,612 windows the answer rate at the shipped floor runs
#: **0.59% at 4 spaces, 1.34% at 6, 2.19% at 8**. Four spaces is also more
#: than a meter needs — a digit stack is 2-3 spaces wide — and the positive
#: control answers 225 of 225 inside it.
METER_TEMPLATE_AT_BAR_WINDOW_SPACES = 4.0

#: How many staves of one system must the column be meter-shaped on before the
#: template reader is asked there at all.
#:
#: ⚠️ ONE, DELIBERATELY, AND IT IS NOT WHERE THE SAFETY LIVES. The whole point
#: of this pass is to ask the staves that detected NOTHING — Sean's framing,
#: *"if something is seen but undetermined we still need that ... that would
#: still likely happen across all staves in the system for that measure"* — so
#: narrowing candidacy is narrowing the thing being built. ⚠️ The COST is
#: real and is measured rather than hoped: on Brahms 1 / Breitkopf pp.1-3
#: **38 of 51 columns (74.5%)** carry a meter-shaped detection somewhere, so
#: this pass asks 525 windows where the header pass asks 83. At 20 ms a window
#: that is ~11 s for a three-page document. **The briefed assumption that a
#: detection names a handful of candidate bars is FALSE on a scan**, which is
#: why the consensus below, and not this number, is what makes it safe.
METER_TEMPLATE_AT_BAR_MIN_CANDIDATE_STAVES = 1


def _meter_template_at_bar_enabled() -> bool:
    """Default ON (ROADMAP 2.72); `OMR_METER_TEMPLATE_AT_BAR=0` turns it off."""
    return (os.environ.get(METER_TEMPLATE_AT_BAR_ENV, "1").strip().lower()
            not in ("0", "", "false", "no", "off"))


def _bar_head_window(cell: Any, spaces: float):
    """`cell`, sliced to the first `spaces` staff spaces of its own width.

    ⚠️ A SLICE OF THE CELL THE PIPELINE ALREADY CUT, not a new extraction. The
    measure cell starts at the barline and a meter change is printed directly
    after one, so the crop this reader needs is already on disk — and building
    a fresh one would put this pass on a second, unpriced cutting path with its
    own padding and its own canonical scale.

    Returns None where the cell has no five-line geometry to measure against,
    which is an ABSTENTION and not a zero.
    """
    import dataclasses

    from ..header_ink import staff_metrics

    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing = metrics[0]
    image = getattr(cell, "image", None)
    if image is None or image.size == 0:
        return None
    width = int(round(spaces * spacing))
    if width < 8:
        return None
    width = min(int(image.shape[1]), width)
    no_staff = getattr(cell, "image_no_staff", None)
    return dataclasses.replace(
        cell,
        image=image[:, :width],
        image_no_staff=(no_staff[:, :width] if no_staff is not None else None),
    )


def _meter_candidate_columns(detections: Dict[str, List[Any]], p: int,
                             local: Dict[int, Tuple[int, int]],
                             spacing_of: Optional[Dict[int, float]] = None
                             ) -> Dict[int, Dict[int, int]]:
    """`{system_index: {cell_index: how many staves saw meter-shaped ink}}`.

    ⚠️ CELL 0 IS EXCLUDED, exactly as `_meter_changes` excludes it: a glyph at
    the head of the staff states the OPENING and is the header reader's
    business, not a change.

    ⚠️ ROADMAP 2.72: "METER-SHAPED INK" IS EITHER A DETECTOR `timeSig*` BOX OR
    THE STACKED PAIR OF HEADS `_meter_digit_pair_box` TESTS. On a scan the
    detector more often boxes a printed change's two digits as two NOTEHEADS
    than as a time signature (ROADMAP 2.12l: 13 of 14 staves on Brahms 1/i's
    bar 9 print `6/8` and the detector boxes `timeSig1` on one), so a column
    gated on `timeSig*` alone is a column the detector happened to name, and
    the change the page prints there is never asked about. The pair test is
    the SAME geometry `notehead_precision.is_a_meter_digit` later holds the
    boxes to (imported there, not restated here), applied loosely -- firing
    here only spends a reader call, never decides anything; the safety is the
    agreement of the system's staves, as it always was
    (`rhythm.METER_TEMPLATE_AT_BAR_MIN_STAVES`).
    """
    per_system: Dict[int, Dict[int, int]] = {}
    for staff_index, key in sorted(local.items()):
        sys_idx = key[0]
        spacing = (spacing_of or {}).get(staff_index)
        for cell_index, cell_dets in _meter_cells(detections, p, key):
            if cell_index == 0:
                continue
            seen = any(d.smufl_name.startswith("timeSig") for d in cell_dets)
            if not seen and spacing:
                seen = _meter_digit_pair_box(cell_dets, spacing) is not None
            if not seen:
                continue
            per_system.setdefault(sys_idx, {})
            per_system[sys_idx][cell_index] = (
                per_system[sys_idx].get(cell_index, 0) + 1)
    return per_system


def gather_meter_at_bars(log: Log, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]]) -> None:
    """Ask the template reader at every candidate mid-staff BAR HEAD.

    One staff's detection names the COLUMN; the reader is then asked of EVERY
    staff of that system at that same bar, **including the staves that
    detected nothing** — which is the only part of this that the detector
    cannot already do, and the reason a column is the unit rather than a cell.

    ⚠️ FLAG OFF WRITES NOTHING AT ALL, not even an abstention, so the record is
    byte-identical with the flag off. An `OUT_OF_SCOPE` row per staff per
    candidate column would be the direction reader's convention and would cost
    a few hundred rows a page to say *"a flag is off"* — a fact the flag
    already knows. The trade is stated rather than hidden: with the flag off a
    record cannot distinguish this pass from one that ran and found nothing,
    and for an unpriced default-OFF mechanism that is the right side to err on.
    """
    if not _meter_template_at_bar_enabled():
        return
    try:
        from ..time_signature_locator import locate_meter_by_halves
    except Exception:                                         # noqa: BLE001
        for staff_index, key in sorted(local.items()):
            log.abstain(R.staff(0, key[0], key[1]), Q.METER_TEMPLATE_AT_BAR,
                        reader=READERS.TEMPLATE, frame=FRAME_HEADER_WINDOW,
                        reason=ABSTAIN.READER_UNAVAILABLE)
        return

    by_staff_cell: Dict[Tuple[int, int], Any] = {}
    page_index = 0
    for c in cells:
        if c.staff_index in local:
            by_staff_cell[(c.staff_index, c.measure_index)] = c
            page_index = c.page_index

    from ..header_ink import staff_metrics as _staff_metrics
    spacing_of: Dict[int, float] = {}
    for (st, _m), c in by_staff_cell.items():
        if st not in spacing_of:
            m = _staff_metrics(c)
            if m is not None:
                spacing_of[st] = m[0]
    columns = _meter_candidate_columns(detections, page_index, local,
                                       spacing_of)
    for staff_index, key in sorted(local.items()):
        sys_idx, st_idx = key
        sub = R.staff(page_index, sys_idx, st_idx)
        for cell_index, n_seen in sorted(columns.get(sys_idx, {}).items()):
            if n_seen < METER_TEMPLATE_AT_BAR_MIN_CANDIDATE_STAVES:
                continue
            frame = frame_bar_head(cell_index)
            cell = by_staff_cell.get((staff_index, cell_index))
            if cell is None:
                # This staff has no bar there at all — a shorter staff, or a
                # partition that disagrees. Recorded, because "this staff was
                # not asked" and "this staff was asked and said nothing" are
                # different facts about the same column.
                log.abstain(sub, Q.METER_TEMPLATE_AT_BAR,
                            reader=READERS.TEMPLATE, frame=frame,
                            reason=ABSTAIN.NO_BARLINE, cell=cell_index)
                continue
            window = _bar_head_window(
                cell, METER_TEMPLATE_AT_BAR_WINDOW_SPACES)
            if window is None:
                log.abstain(sub, Q.METER_TEMPLATE_AT_BAR,
                            reader=READERS.TEMPLATE, frame=frame,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY, cell=cell_index)
                continue
            trace: Dict[str, Any] = {}
            try:
                # ⚠️ ROADMAP 2.72: THE HALVES READER, NOT THE WHOLE-STACK ONE.
                # See `time_signature_locator.locate_meter_by_halves`.
                found = locate_meter_by_halves(window, trace=trace)
            except Exception:                                 # noqa: BLE001
                log.abstain(sub, Q.METER_TEMPLATE_AT_BAR,
                            reader=READERS.TEMPLATE, frame=frame,
                            reason=ABSTAIN.READER_UNAVAILABLE, cell=cell_index)
                continue
            if found is None:
                # ⚠️ THE COMMON AND CORRECT OUTCOME. A bar that prints no meter
                # is almost every bar, and this abstention is the reader doing
                # its job — 1,596 of 1,612 measured windows.
                log.abstain(sub, Q.METER_TEMPLATE_AT_BAR,
                            reader=READERS.TEMPLATE, frame=frame,
                            reason=ABSTAIN.BELOW_THRESHOLD, cell=cell_index,
                            **{k: v for k, v in trace.items()
                               if k in ("floor", "best")})
                continue
            log.observe(sub, Q.METER_TEMPLATE_AT_BAR,
                        (int(found.numerator), int(found.denominator)),
                        reader=READERS.TEMPLATE, frame=frame,
                        cell=cell_index, score=float(found.score),
                        raw=found.raw, runner_up=found.runner_up_raw,
                        runner_up_score=found.runner_up_score,
                        score_margin=found.score_margin,
                        # ⚠️ ROADMAP 2.72: this score is the WEAKER of the
                        # two halves' correlations (`locate_meter_by_halves`),
                        # not a whole-stack one.
                        candidate_staves=n_seen)


#: ROADMAP 2.29's mid-bar OCR reader. DEFAULT OFF, its OWN flag rather than
#: `METER_TEMPLATE_AT_BAR_ENV` -- this is a GATHER change with no pricing run
#: behind it yet (Sean 2026-09-29: microscopic wiring, proved by RED->GREEN
#: tests, no gathers), and 2.12i's own flag stays exactly as that item
#: measured and left it. An allow-list, because the default is OFF.
METER_OCR_AT_BAR_ENV = "OMR_METER_OCR_AT_BAR"


def _meter_ocr_at_bar_enabled() -> bool:
    return (os.environ.get(METER_OCR_AT_BAR_ENV, "0").strip().lower()
            in ("1", "true", "yes", "on")
            and research_enabled(METER_OCR_AT_BAR_ENV))


def _meter_digit_pair_box(cell_dets, spacing: float
                          ) -> Optional[Tuple[float, float, float, float]]:
    """This staff's own stacked notehead PAIR near the barline, as a page-
    canonical `(x0, y0, x1, y1)` bounding box over BOTH boxes, or `None`.

    ⚠️ THE SAME GEOMETRY `notehead_precision._meter_digit_pair_partner` /
    `_has_a_stacked_pair` TEST — cited, not imported: that module reads it
    back off `Q.GLYPH_BOX` ROWS at ADJUDICATE time (after the cross-staff
    quorum is knowable); this runs at GATHER time, directly off the
    detector's own boxes, before any quorum exists to ask. Firing here is
    deliberately LOOSER than `is_a_meter_digit` (no cross-staff repetition
    required) — it only decides whether it is worth SPENDING an OCR call,
    never whether the pair IS a meter digit. That verdict stays
    `notehead_precision`'s alone; a false hit here costs one wasted crop and
    files nothing else.
    """
    # ⚠️ IMPORTED, NOT RESTATED — the exact thresholds ROADMAP 2.12l measured
    # (`notehead_precision.METER_DIGIT_X_MAX_SPACES` et al.), so this pass
    # can never drift from what `is_a_meter_digit` will later test the same
    # boxes against. A lazy import: `gather.py` is the GATHER layer and this
    # module lives under `adjudicators/`, imported only where this one
    # function needs its constants.
    from .adjudicators import notehead_precision as _np
    notes = [d for d in cell_dets
             if str(getattr(d, "smufl_name", "")).lower().startswith(
                 _NOTEHEAD_PREFIX.lower())]
    candidates = []
    for d in notes:
        x_sp = d.x_canonical / spacing
        if not (0.0 <= x_sp <= _np.METER_DIGIT_X_MAX_SPACES):
            continue
        yc = (d.y_canonical + d.height_canonical / 2.0) / spacing
        candidates.append((x_sp, yc, d))
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            x0, yc0, d0 = candidates[i]
            x1, yc1, d1 = candidates[j]
            if abs(x1 - x0) > _np.METER_DIGIT_PAIR_X_TOL_SPACES:
                continue
            y_gap = abs(yc1 - yc0)
            if not (_np.METER_DIGIT_PAIR_Y_GAP_MIN_SPACES <= y_gap
                    <= _np.METER_DIGIT_PAIR_Y_GAP_MAX_SPACES):
                continue
            bx0 = min(d0.x_canonical, d1.x_canonical)
            by0 = min(d0.y_canonical, d1.y_canonical)
            bx1 = max(d0.x_canonical + d0.width_canonical,
                      d1.x_canonical + d1.width_canonical)
            by1 = max(d0.y_canonical + d0.height_canonical,
                      d1.y_canonical + d1.height_canonical)
            return (bx0, by0, bx1, by1)
    return None


def gather_meter_ocr_at_bars(log: Log, cells: Sequence[Any],
                             local: Dict[int, Tuple[int, int]],
                             detections: Dict[str, List[Any]]) -> None:
    """ROADMAP 2.29. `Q.METER_OCR_AT_BAR` — the OCR reader, aimed at a
    mid-staff bar head from EITHER of two starting points: a detector
    `timeSig*` box at that cell (the SAME window `gather_meter_at_bars`
    builds, `_bar_head_window`), or — where the detector boxed the change's
    digits as noteheads instead — this staff's own stacked notehead pair
    near the barline (`_meter_digit_pair_box`, ROADMAP 2.12l's own
    geometry). Filed on the CELL subject: `_meter_digit_witness_cells`
    (`rhythm.py`) reads it back at the exact cell it already found a
    cross-staff witness at, as a CANDIDATE for the carry to weigh — never a
    decision made here.

    ⚠️ Off by default (`METER_OCR_AT_BAR_ENV`): unlike the header reading
    (always on, like `Q.PRINTED_BAR_NUMBER`), this pass has no pricing run
    behind it, per Sean 2026-09-29's own instruction to wire conceptually
    rather than spend a run on it.
    """
    if not _meter_ocr_at_bar_enabled():
        return
    # ⚠️ ROADMAP 2.60: the per-cell `READER_UNAVAILABLE` row below now names
    # the exception when the import THREW, so it can be told from a machine
    # with no Tesseract.
    import_error: Dict[str, Any] = {}
    try:
        from .. import meter_digit_ocr
    except Exception as exc:                                  # noqa: BLE001
        meter_digit_ocr = None                                # type: ignore
        import_error = {"error": type(exc).__name__}

    by_staff_cell: Dict[Tuple[int, int], Any] = {}
    page_index = 0
    for c in cells:
        if c.staff_index in local:
            by_staff_cell[(c.staff_index, c.measure_index)] = c
            page_index = c.page_index

    for staff_index, key in sorted(local.items()):
        sys_idx, st_idx = key
        for (s_idx, cell_index), cell in sorted(by_staff_cell.items()):
            if s_idx != staff_index or cell_index == 0:
                continue
            sub = R.cell(page_index, sys_idx, st_idx, cell_index)
            frame = frame_bar_head(cell_index)
            if meter_digit_ocr is None or not meter_digit_ocr.available():
                log.abstain(sub, Q.METER_OCR_AT_BAR, reader=READERS.TESSERACT,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            cell=cell_index, **import_error)
                continue
            cell_key = R.cell(page_index, sys_idx, st_idx, cell_index).to_key()
            cell_dets = detections.get(cell_key, [])
            image = None
            split_row = None
            origin = None
            metrics_error: Optional[str] = None
            if any(str(getattr(d, "smufl_name", "")).startswith("timeSig")
                  for d in cell_dets):
                window = _bar_head_window(cell, METER_TEMPLATE_AT_BAR_WINDOW_SPACES)
                if window is not None:
                    image = getattr(window, "image", None)
                    line_ys = getattr(window, "staff_line_ys_canonical", None) or []
                    if len(line_ys) >= 5:
                        split_row = int(round(line_ys[2]))
                    origin = "timesig_box"
            if image is None:
                metrics = None
                try:
                    from ..header_ink import staff_metrics
                    metrics = staff_metrics(cell)
                except Exception as exc:                          # noqa: BLE001
                    metrics = None
                    metrics_error = type(exc).__name__
                if metrics is not None:
                    spacing = metrics[0]
                    box = _meter_digit_pair_box(cell_dets, spacing)
                    if box is not None:
                        bx0, by0, bx1, by1 = box
                        full = getattr(cell, "image", None)
                        if full is not None and full.size:
                            x0i, y0i = max(0, int(bx0)), max(0, int(by0))
                            x1i = min(full.shape[1], int(bx1) + 1)
                            y1i = min(full.shape[0], int(by1) + 1)
                            if x1i > x0i and y1i > y0i:
                                image = full[y0i:y1i, x0i:x1i]
                                split_row = (y1i - y0i) // 2
                                origin = "digit_pair_witness"
            if (image is None or image.size == 0) \
                    and metrics_error is not None:
                # ⚠️ ROADMAP 2.60: the staff-metrics reader THREW, so the
                # digit-pair witness was never looked for -- not "the
                # detector fired nothing here".
                log.abstain(sub, Q.METER_OCR_AT_BAR, reader=READERS.TESSERACT,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            cell=cell_index, error=metrics_error,
                            note="header_ink.staff_metrics raised")
                continue
            if image is None or image.size == 0:
                log.abstain(sub, Q.METER_OCR_AT_BAR, reader=READERS.TESSERACT,
                            frame=frame, reason=ABSTAIN.NO_DETECTIONS,
                            cell=cell_index)
                continue
            trace: Dict[str, Any] = {}
            try:
                found = meter_digit_ocr.read_meter_digits(
                    image, split_row=split_row, trace=trace)
            except Exception:                                     # noqa: BLE001
                log.abstain(sub, Q.METER_OCR_AT_BAR, reader=READERS.TESSERACT,
                            frame=frame, reason=ABSTAIN.READER_UNAVAILABLE,
                            cell=cell_index, origin=origin)
                continue
            if found is None:
                log.abstain(sub, Q.METER_OCR_AT_BAR, reader=READERS.TESSERACT,
                            frame=frame, reason=ABSTAIN.BELOW_THRESHOLD,
                            cell=cell_index, origin=origin, **trace)
                continue
            log.observe(sub, Q.METER_OCR_AT_BAR,
                        (found.numerator, found.denominator),
                        reader=READERS.TESSERACT, frame=frame,
                        cell=cell_index, origin=origin,
                        score=min(found.numerator_confidence,
                                 found.denominator_confidence) / 100.0,
                        numerator_confidence=found.numerator_confidence,
                        denominator_confidence=found.denominator_confidence)


def _label_rung_state(surya_fallback: bool, ocr_fallback: bool) -> Dict[str, Any]:
    """Which margin-label rungs were ASKED FOR, and which of those can run.

    ⚠️ `available()` IS THE WHOLE POINT. Both free rungs self-disable where
    their install is missing -- Surya wants a Python 3.10 venv and llama.cpp,
    Tesseract wants a brew binary -- and they do it SILENTLY, which is exactly
    right for the reader and exactly wrong for the record. A machine with
    neither reads zero labels on every page, identically to a page that prints
    none, and nothing anywhere said which. Asking here, once, before the
    cascade runs, is what lets the rows below name the difference.
    """
    requested, available, unavailable = [], ["text_layer"], []
    #: ROADMAP 2.60: a rung whose availability probe THREW, by exception
    #: class -- read back onto that rung's `READER_UNAVAILABLE` row.
    errors: Dict[str, str] = {}
    if surya_fallback:
        requested.append("surya")
        try:
            from ..staff_labels_surya import available as _surya_available
            ok = bool(_surya_available())
        except Exception as exc:                              # noqa: BLE001
            ok = False
            errors["surya"] = type(exc).__name__
        (available if ok else unavailable).append("surya")
    if ocr_fallback:
        requested.append("tesseract")
        try:
            from ..staff_labels_tesseract import available as _tess_available
            ok = bool(_tess_available())
        except Exception as exc:                              # noqa: BLE001
            ok = False
            errors["tesseract"] = type(exc).__name__
        (available if ok else unavailable).append("tesseract")
    return {"requested": requested, "available": available,
            "unavailable": unavailable, "errors": errors}


def gather_printed_bar_numbers(log: Log, pws: Any, surya: bool = False) -> None:
    """ROADMAP 2.13. The small numeral an engraver prints above a SYSTEM's
    first bar, read off a crop directly above the system's topmost staff.

    ⚠️ ROADMAP 2.13b: SURYA FIRST WHEN `surya` (the run's `--no-surya` is
    off), on an 8-staff-space crop, filed under `READERS.SURYA`; Tesseract
    otherwise, on its own 6-space crop, filed under `READERS.TESSERACT`,
    byte-for-byte the reader below. Where Surya reads nothing the system is
    `NO_INK` and Tesseract is NOT asked -- measured 5 right / 7 wrong on
    exactly those systems (`bar_number_text`'s Surya block). Where Surya
    cannot run, a `READER_UNAVAILABLE` row says so and Tesseract reads.

    ⚠️ ONE ROW PER SYSTEM, ON THE SYSTEM SUBJECT -- not per staff, because
    the numeral is printed once per system regardless of how many staves it
    carries. The topmost staff of a system is `min(members, key=top_y)`,
    the same ordering `_system_local` uses to assign ordinal 0 -- no second
    geometry pass is needed to find it.

    ⚠️ THE TESSERACT RUNG IS UNCHANGED BY 2.13b: same crop, same config,
    same rows, so a `--no-surya` run reads exactly what it read before.

    ⚠️⚠️ FOUR STATES, THE SAME CONTRACT `gather_direction_words` DECLARES
    FOR ITS OWN READER:

    | what happened | what is written |
    |---|---|
    | Tesseract is not installed here | `READER_UNAVAILABLE` |
    | this system's geometry could not be measured | `NO_STAFF_GEOMETRY` |
    | the rung ran and read no text at all | `NO_INK` |
    | the rung read something | an OBSERVATION |

    ⚠️ WHETHER THAT TEXT IS ACTUALLY A NUMBER is not decided here -- GATHER
    decides nothing. A rehearsal letter, or noise, arrives as an Observation
    like any other reading; `adjudicate_printed_bar_number`
    (`adjudicators/text.py`) is where a non-numeric read is told apart from
    a numeric one.

    CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: the numeral
    sits 0.8-6.2 staff spaces above the top staff's own top line, within
    about six staff spaces right of `Staff.x_start` (already past the
    clef/key/meter margin) -- MEASURED against both of this item's gate
    pages (Litolff Beethoven 5 p.3: reads 49 and 65; Breitkopf Brahms 1 p.2:
    reads 8 and 15 -- FINDINGS.md §1). A plate that boxes the number above
    the BARLINE rather than the margin, or prints it further from the top
    line than this band, would be missed by this crop and would read
    `NO_INK` rather than a wrong number -- CLAUDE.md rule 8, a fallback
    never turns "cannot tell" into an answer.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_system: Dict[int, List[Any]] = {}
    for st in pws.staves:
        by_system.setdefault(st.system_index, []).append(st)

    try:
        from .. import bar_number_text as BNT
    except Exception as exc:                                  # noqa: BLE001
        for sys_idx in sorted(by_system):
            log.abstain(R.system(p, sys_idx), Q.PRINTED_BAR_NUMBER,
                        reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=type(exc).__name__, note=str(exc)[:200])
        return

    if surya and _printed_bar_numbers_surya(log, pws, by_system, BNT):
        return

    if not BNT.available():
        for sys_idx in sorted(by_system):
            log.abstain(R.system(p, sys_idx), Q.PRINTED_BAR_NUMBER,
                        reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        note="tesseract is not installed here")
        return

    image = getattr(pws.page, "rgb", None)
    w = int(image.shape[1]) if image is not None else 0

    for sys_idx, members in sorted(by_system.items()):
        sys_sub = R.system(p, sys_idx)
        top = min(members, key=lambda s: s.top_y)
        # ⚠️ `_spacing`, NOT `Staff.line_spacing_px`. This module's other
        # geometry readers (`gather_geometry`) go through the same helper
        # rather than the dataclass property, and a test fixture built as a
        # plain `FakeStaff` (`test_staged_pipeline.py`) has `line_ys` but no
        # derived property -- the helper is the one thing both can answer.
        space = _spacing(top)
        if image is None or not space or space <= 0:
            log.abstain(sys_sub, Q.PRINTED_BAR_NUMBER,
                        reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue

        # ⚠️ ABOVE the top staff, starting at `x_start` -- see the module
        # docstring's CONVENTION note for what this assumes and how it fails.
        # ⚠️ THE BAND IS 0.8-6.2 STAFF SPACES ABOVE THE TOP LINE, measured
        # against both gate pages (FINDINGS.md §1): a tighter band clipped
        # the numeral's own top on Litolff p3 ("49" read as blank, "65" read
        # as "9" -- the top half of each digit was outside the crop).
        x0 = max(0, int(top.x_start))
        x1 = min(w, int(top.x_start + 6.0 * space))
        y1 = max(0, int(top.top_y - 0.8 * space))
        y0 = max(0, int(top.top_y - 6.2 * space))
        if x1 <= x0 or y1 <= y0:
            log.abstain(sys_sub, Q.PRINTED_BAR_NUMBER,
                        reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        crop = image[y0:y1, x0:x1]

        try:
            found = BNT.read_crop(crop)
        except Exception as exc:                              # noqa: BLE001
            log.abstain(sys_sub, Q.PRINTED_BAR_NUMBER,
                        reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.READER_UNAVAILABLE,
                        error=type(exc).__name__, note=str(exc)[:200])
            continue

        if found is None:
            log.abstain(sys_sub, Q.PRINTED_BAR_NUMBER,
                        reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.NO_INK,
                        bbox_page_px=[float(x0), float(y0), float(x1), float(y1)])
            continue

        text, conf = found
        log.observe(sys_sub, Q.PRINTED_BAR_NUMBER, text,
                    reader=READERS.TESSERACT, frame=FRAME_BAR_NUMBER,
                    score=conf / 100.0,
                    bbox_page_px=[float(x0), float(y0), float(x1), float(y1)])


def _page_gray(pws: Any) -> Any:
    """The page's ORIGINAL raster as 2-D grey, or None."""
    image = getattr(pws.page, "rgb", None)
    if image is None:
        return None
    import numpy as np
    arr = np.asarray(image)
    if arr.ndim == 3:
        import cv2
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return arr


def gather_volta_brackets(log: Log, pws: Any) -> None:
    """ROADMAP 2.85. Every hooked horizontal stroke above a system's top
    staff -- a 1st/2nd-ending (volta) bracket candidate -- one row per
    stroke on the SYSTEM subject.

    ⚠️ CV, BECAUSE THE DETECTOR HAS NO VOLTA CLASS (208 classes, `repeatDot`
    the only repeat symbol). On Brahms p10 its cell crop clips the stroke's
    top and it boxes the 1st-ending line as an `ottavaBracket` in one cell
    only; nothing reached the record as an ending, and the exporter counted
    the 1st-ending bars straight through (+2 to every later bar number).

    ⚠️ ONE ROW PER SYSTEM SUBJECT, READ OFF THE TOP STAFF ONLY: the bracket
    is printed above the system (Breitkopf repeats it above the strings, a
    second copy of the same fact, not read). Which bars it covers and which
    ending it is are ADJUDICATE's (`adjudicate_endings`); this decides
    nothing. A system with no candidate gets `NO_INK`, so "the reader looked
    and found none" stays apart from "no reader ran".
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_system: Dict[int, List[Any]] = {}
    for st in pws.staves:
        by_system.setdefault(st.system_index, []).append(st)
    gray = _page_gray(pws)
    from .. import volta_bracket as VB
    for sys_idx, members in sorted(by_system.items()):
        sys_sub = R.system(p, sys_idx)
        top = min(members, key=lambda s: s.top_y)
        space = _spacing(top)
        if gray is None or not space or space <= 0:
            log.abstain(sys_sub, Q.VOLTA_BRACKET, reader=READERS.CV_VOLTA,
                        frame=FRAME_VOLTA, reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        found = VB.find_brackets(gray, top.line_ys, top.x_start, top.x_end)
        if not found:
            log.abstain(sys_sub, Q.VOLTA_BRACKET, reader=READERS.CV_VOLTA,
                        frame=FRAME_VOLTA, reason=ABSTAIN.NO_INK)
            continue
        for k, b in enumerate(found):
            log.observe(sys_sub, Q.VOLTA_BRACKET, b.as_value(),
                        reader=READERS.CV_VOLTA, frame=FRAME_VOLTA,
                        bracket=k, space=float(space))


#: ROADMAP 2.85. Surya reads the numeral on a crop padded and doubled --
#: measured on Brahms p10: unpadded native-size crops read "" for both
#: brackets, padded 60 px and 2x upscaled read "1." and "2." (deterministic
#: over repeat runs). The token cap is measured too: 8 read "" on both, 16
#: reads both.
_VOLTA_SURYA_PAD = 60
_VOLTA_SURYA_SCALE = 2
_VOLTA_SURYA_MAX_TOKENS = 16
_VOLTA_SURYA_TIMEOUT_S = 60.0


def gather_volta_numerals(log: Log, pws: Any, *,
                          surya_fallback: bool = False) -> None:
    """ROADMAP 2.85. The numeral inside each bracket's left hook, OCRed.

    ⚠️ READS `Q.VOLTA_BRACKET` OFF THIS LOG, so it runs after
    `gather_volta_brackets` (a forced GATHER edge -- `log.rows` on a quantity
    nobody filed yet answers EMPTY, not an error).

    ⚠️ SURYA FIRST, TESSERACT ONLY WHERE SURYA CANNOT RUN. Measured on
    Breitkopf 317803: Tesseract reads this plate's bold "1" as "4" every time
    it was asked -- the ending's "1." as "4." (conf 83), and the 2.13 bar
    numbers 188/194 as 488/494 -- while Surya reads "1." and "2.". Tesseract
    stays as the rung for a `--no-surya` run, under its own reader name so a
    consumer can see which one spoke.

    Four states per bracket: `READER_UNAVAILABLE`, `NO_STAFF_GEOMETRY`,
    `NO_INK` (read nothing), or an OBSERVATION of the raw text. Whether the
    text IS an ending number is ADJUDICATE's.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    systems = sorted({st.system_index for st in pws.staves})
    gray = _page_gray(pws)
    from .. import volta_bracket as VB
    jobs: List[Tuple[int, int, Tuple[int, int, int, int]]] = []
    for sys_idx in systems:
        sys_sub = R.system(p, sys_idx)
        for row in log.rows(Q.VOLTA_BRACKET, sys_sub):
            det = row.detail or {}
            k = int(det.get("bracket", 0))
            space = float(det.get("space") or 0.0)
            v = row.value or {}
            if gray is None or space <= 0:
                log.abstain(sys_sub, Q.VOLTA_NUMERAL, reader=READERS.CV_VOLTA,
                            frame=FRAME_VOLTA_NUMERAL,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY, bracket=k)
                continue
            b = VB.Bracket(x0=int(v["x0"]), x1=int(v["x1"]), y=int(v["y"]),
                           thickness=int(v["thickness"]),
                           left_hook=float(v["left_hook"]),
                           right_hook=float(v["right_hook"]))
            jobs.append((sys_idx, k, VB.numeral_crop_box(b, space)))
    if not jobs:
        return

    use_surya = False
    if surya_fallback:
        try:
            from ..staff_labels_surya import available as _surya_available
            use_surya = bool(_surya_available())
        except Exception:                                     # noqa: BLE001
            use_surya = False
    if use_surya:
        import cv2
        crops = []
        for _sub, _k, (x0, y0, x1, y1) in jobs:
            c = gray[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
            c = cv2.copyMakeBorder(c, _VOLTA_SURYA_PAD, _VOLTA_SURYA_PAD,
                                   _VOLTA_SURYA_PAD, _VOLTA_SURYA_PAD,
                                   cv2.BORDER_CONSTANT, value=255)
            c = cv2.resize(c, None, fx=_VOLTA_SURYA_SCALE,
                           fy=_VOLTA_SURYA_SCALE)
            crops.append(cv2.cvtColor(c, cv2.COLOR_GRAY2BGR))
        try:
            from ..staff_labels_surya import read_crops_text
            texts = read_crops_text(crops, max_tokens=_VOLTA_SURYA_MAX_TOKENS,
                                    crop_timeout_s=_VOLTA_SURYA_TIMEOUT_S)
        except Exception as exc:                              # noqa: BLE001
            for sys_idx, k, box in jobs:
                log.abstain(R.system(p, sys_idx), Q.VOLTA_NUMERAL, reader=READERS.SURYA,
                            frame=FRAME_VOLTA_NUMERAL,
                            reason=ABSTAIN.READER_UNAVAILABLE, bracket=k,
                            error=type(exc).__name__, note=str(exc)[:200])
            return
        for (sys_idx, k, box), text in zip(jobs, texts):
            text = (text or "").strip()
            if not text:
                log.abstain(R.system(p, sys_idx), Q.VOLTA_NUMERAL, reader=READERS.SURYA,
                            frame=FRAME_VOLTA_NUMERAL, reason=ABSTAIN.NO_INK,
                            bracket=k, bbox_page_px=[float(v) for v in box])
                continue
            log.observe(R.system(p, sys_idx), Q.VOLTA_NUMERAL, text, reader=READERS.SURYA,
                        frame=FRAME_VOLTA_NUMERAL, bracket=k,
                        bbox_page_px=[float(v) for v in box])
        return

    try:
        from .. import bar_number_text as BNT
        tess_ok = BNT.available()
    except Exception:                                         # noqa: BLE001
        tess_ok = False
    for sys_idx, k, box in jobs:
        if not tess_ok:
            log.abstain(R.system(p, sys_idx), Q.VOLTA_NUMERAL, reader=READERS.TESSERACT,
                        frame=FRAME_VOLTA_NUMERAL,
                        reason=ABSTAIN.READER_UNAVAILABLE, bracket=k)
            continue
        try:
            found = VB.read_numeral(gray, box)
        except Exception as exc:                              # noqa: BLE001
            log.abstain(R.system(p, sys_idx), Q.VOLTA_NUMERAL, reader=READERS.TESSERACT,
                        frame=FRAME_VOLTA_NUMERAL,
                        reason=ABSTAIN.READER_UNAVAILABLE, bracket=k,
                        error=type(exc).__name__, note=str(exc)[:200])
            continue
        if found is None:
            log.abstain(R.system(p, sys_idx), Q.VOLTA_NUMERAL, reader=READERS.TESSERACT,
                        frame=FRAME_VOLTA_NUMERAL, reason=ABSTAIN.NO_INK,
                        bracket=k, bbox_page_px=[float(v) for v in box])
            continue
        text, conf = found
        log.observe(R.system(p, sys_idx), Q.VOLTA_NUMERAL, text, reader=READERS.TESSERACT,
                    frame=FRAME_VOLTA_NUMERAL, score=conf / 100.0, bracket=k,
                    bbox_page_px=[float(v) for v in box])


def gather_repeat_dots(log: Log, pws: Any, cells: Sequence[Any],
                       local: Dict[int, Tuple[int, int]]) -> None:
    """ROADMAP 2.85. The two dots of a repeat sign beside each barline the
    measure extractor cut, one staff at a time, filed on the SYSTEM.

    ⚠️ CV, BECAUSE THE DETECTOR MISSES THEM: on Brahms p10-11 `repeatDot`
    fired twice, both spurious, and none of the 28 dots of the backward
    repeat closing the 1st ending (`repeat_dots`' own docstring). Read on
    the ORIGINAL raster (the dots sit in spaces 2 and 3, between lines that
    must stay to place them).

    `edge="end"`: dots left of the cell's RIGHT barline (`:||`); `"start"`:
    dots right of its LEFT barline (`||:`). Which barlines ARE repeats is
    voted across the staves by `adjudicate_repeat_barlines`. A system where
    no staff holds a pair gets one `NO_INK` row.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    gray = _page_gray(pws)
    from .. import repeat_dots as RD
    staves = {st.staff_index: st for st in pws.staves}
    found: Dict[int, int] = {}
    systems = set()
    binary = None if gray is None else (gray < 128).astype("uint8")
    for c in cells:
        key = local.get(c.staff_index)
        st = staves.get(c.staff_index)
        if key is None or st is None:
            continue
        sys_idx, st_idx = key
        systems.add(sys_idx)
        box = getattr(c, "bbox_page_px", None)
        if binary is None or not box or len(box) != 4:
            continue
        for edge, side, bx in (("end", "left", box[2]),
                               ("start", "right", box[0])):
            pair = RD.find_pair(binary, st.line_ys, float(bx), side)
            if pair is None:
                continue
            log.observe(R.system(p, sys_idx), Q.REPEAT_DOTS, edge,
                        reader=READERS.CV_REPEAT_DOTS,
                        frame=FRAME_REPEAT_DOTS, staff=st_idx,
                        cell=int(c.measure_index), barline_x=float(bx))
            found[sys_idx] = found.get(sys_idx, 0) + 1
    for sys_idx in sorted(systems):
        if found.get(sys_idx):
            continue
        log.abstain(R.system(p, sys_idx), Q.REPEAT_DOTS,
                    reader=READERS.CV_REPEAT_DOTS, frame=FRAME_REPEAT_DOTS,
                    reason=(ABSTAIN.NO_STAFF_GEOMETRY if binary is None
                            else ABSTAIN.NO_INK))


def _printed_bar_numbers_surya(log: Log, pws: Any,
                               by_system: Dict[int, List[Any]],
                               BNT: Any) -> bool:
    """ROADMAP 2.13b: the Surya rung of `gather_printed_bar_numbers`.

    Returns True when Surya ran (every system then has exactly one Surya
    row: an Observation, `NO_INK`, or `NO_STAFF_GEOMETRY`), False when it
    could not -- having filed a `READER_UNAVAILABLE` row per system first,
    so the Tesseract rows that follow are visibly a fallback, not a choice.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    image = getattr(pws.page, "rgb", None)
    w = int(image.shape[1]) if image is not None else 0

    def _unavailable(**detail: Any) -> bool:
        for sys_idx in sorted(by_system):
            log.abstain(R.system(p, sys_idx), Q.PRINTED_BAR_NUMBER,
                        reader=READERS.SURYA, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.READER_UNAVAILABLE, **detail)
        return False

    if not BNT.surya_available():
        return _unavailable(note="surya is not installed here")

    # The same vertical band as the Tesseract crop (0.8-6.2 spaces above the
    # top line); only the width differs -- see `SURYA_CROP_WIDTH_SPACES`.
    boxes: Dict[int, Optional[Tuple[int, int, int, int]]] = {}
    for sys_idx, members in sorted(by_system.items()):
        top = min(members, key=lambda s: s.top_y)
        space = _spacing(top)
        box = None
        if image is not None and space and space > 0:
            x0 = max(0, int(top.x_start))
            x1 = min(w, int(top.x_start + BNT.SURYA_CROP_WIDTH_SPACES * space))
            y1 = max(0, int(top.top_y - 0.8 * space))
            y0 = max(0, int(top.top_y - 6.2 * space))
            if x1 > x0 and y1 > y0:
                box = (x0, y0, x1, y1)
        boxes[sys_idx] = box

    readable = [k for k, b in boxes.items() if b is not None]
    try:
        texts = BNT.read_crops_surya(
            [image[b[1]:b[3], b[0]:b[2]]
             for b in (boxes[k] for k in readable)]) if readable else []
        if len(texts) != len(readable):
            raise RuntimeError(
                f"surya returned {len(texts)} texts for {len(readable)} crops")
    except Exception as exc:                                  # noqa: BLE001
        return _unavailable(error=type(exc).__name__, note=str(exc)[:200])

    read = dict(zip(readable, texts))
    for sys_idx, box in sorted(boxes.items()):
        sys_sub = R.system(p, sys_idx)
        if box is None:
            log.abstain(sys_sub, Q.PRINTED_BAR_NUMBER,
                        reader=READERS.SURYA, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY)
            continue
        bbox = [float(v) for v in box]
        text = read[sys_idx]
        if not text:
            log.abstain(sys_sub, Q.PRINTED_BAR_NUMBER,
                        reader=READERS.SURYA, frame=FRAME_BAR_NUMBER,
                        reason=ABSTAIN.NO_INK, bbox_page_px=bbox)
            continue
        # ⚠️ `score=None`: Surya's text path returns no confidence, and a
        # made-up one would be read as a measurement.
        log.observe(sys_sub, Q.PRINTED_BAR_NUMBER, text,
                    reader=READERS.SURYA, frame=FRAME_BAR_NUMBER,
                    score=None, bbox_page_px=bbox)
    return True


#: `_credit_labels`'s rung words -> the reader vocabulary. Written out rather
#: than derived from the string, because `READERS` is a vocabulary a row is
#: validated against and a silent `getattr` miss would file a real reading
#: under a name no consumer knows.
_RUNG_READER = {
    "text_layer": READERS.TEXT_LAYER,
    "surya": READERS.SURYA,
    "tesseract": READERS.TESSERACT,
    "vision": READERS.VISION,
    "human": READERS.VISION,
}


#: ⚠️ THESE TWO DEFAULT **OFF** HERE WHILE THE PIPELINE AND THE CLI DEFAULT
#: THEM **ON** (2026-09-16), AND THE ASYMMETRY IS DELIBERATE. `run_staged`
#: always passes both explicitly, so this default is reached only by a DIRECT
#: caller -- which in practice means a test, and a test must never spawn a
#: 650M-parameter OCR subprocess by accident. What makes the asymmetry safe
#: is the four-state contract below: a direct caller that does not ask now
#: gets `OUT_OF_SCOPE` on every staff, which SAYS it was never asked. Before
#: that contract existed this default was a silent blinding, which is exactly
#: why it could not have been left this way.
# ─────────────────────────────────────────────────────────────────────────────
# The printed meter as ONE claimed area -- ROADMAP 2.177 (2.178 step 1)
# ─────────────────────────────────────────────────────────────────────────────

def _digit_of(name: str) -> Optional[int]:
    if name.startswith("timeSig") and len(name) == 8 and name[7:].isdigit():
        return int(name[7:])
    return None


def _cover_of_smaller(a, b) -> float:
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return (iw * ih) / small if small > 0 else 0.0


def _meter_numbers(area, dets_pg, read_pairs) -> Dict[str, Any]:
    """The two numbers of ONE object, from sources already on the record: the detector's digit boxes inside the area (upper half =
    numerator, lower = denominator) and the readers' (numerator, denominator) pairs. Agreeing sources -> `read`; one -> `one_reader`;
    disagreeing or none -> `abstain` with every candidate. Never a guess."""
    mid = (area[1] + area[3]) / 2.0
    top, bot = [], []
    for name, pb in dets_pg:
        dg = _digit_of(name)
        cx, cy = (pb[0] + pb[2]) / 2.0, (pb[1] + pb[3]) / 2.0
        if dg is None or not (area[0] <= cx <= area[2] and area[1] <= cy <= area[3]):
            continue
        (top if cy < mid else bot).append((cx, dg))
    cand: Dict[str, Dict[str, int]] = {"numerator": {}, "denominator": {}}
    if top:
        cand["numerator"]["detector"] = int("".join(str(d) for _x, d in sorted(top)))
    if bot:
        cand["denominator"]["detector"] = int("".join(str(d) for _x, d in sorted(bot)))
    for src, pair in read_pairs:
        cand["numerator"][src] = pair[0]
        cand["denominator"][src] = pair[1]
    out: Dict[str, Any] = {}
    for half, c in cand.items():
        vals = set(c.values())
        if len(vals) == 1:
            out[half] = {"value": next(iter(vals)), "state": "read" if len(c) >= 2 else "one_reader", "sources": sorted(c)}
        else:
            out[half] = {"value": None, "state": "abstain", "candidates": c}
    return out


def gather_meter_object(log: Log, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                        detections: Dict[str, List[Any]], *, progress: bool = False) -> None:
    """`Q.CLAIMED_AREA` (owner `meter`) per printed time signature per staff -- ROADMAP 2.177, Sean 2026-10-20 ("sees the meter as 2
    numbers and blocks the whole thing out ... and doesnt allow anything else to box that area"). Flag `OMR_METER_OBJECT`, default ON.

    PATH: STAGED GATHER, PAGE raster (`pws.page.binary`). `meter_object.find_column` draws the area from the two numerals' own ink and
    keeps only the pairs that stand in ONE column on a share of the system's staves; the column is claimed only where a witness stands
    (a detector `timeSig*` box on it, or a template/OCR read on the staff -- the header's, or a `*_AT_BAR` read for that bar). The
    numbers are READ from the object's halves by agreement of sources already on the log, or abstained with candidates. The area is
    the numerals' measured box only (never a column read off sibling staves). AFTER `gather_meter_ocr_at_bars` (reads its rows).
    ⚠️ DECLINED, NOT DEFAULTED: no raster / no staff geometry / no pair is an abstention, never "no meter"."""
    from . import meter_object as MO
    if not MO.enabled():
        return
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_sys: Dict[int, Dict[int, Any]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is not None:
            by_sys.setdefault(key[0], {})[key[1]] = st
    cell_of = {(c.staff_index, c.measure_index): c for c in cells}
    for sys_idx, members in sorted(by_sys.items()):
        idxs = sorted({c.measure_index for c in cells if local.get(c.staff_index, (None,))[0] == sys_idx})
        for k in idxs:
            staves, info = [], {}
            witness_seen = k == 0
            for li, st in sorted(members.items()):
                c = cell_of.get((st.staff_index, k))
                sp = _spacing(st)
                bx = getattr(c, "bbox_page_px", None) if c is not None else None
                if c is None or not bx or not sp or len(list(st.line_ys)) < 5:
                    continue
                sub = R.cell(p, sys_idx, li, k)
                dets = detections.get(sub.to_key(), ())
                ts = [(gi, d, _page_box(c, d)) for gi, d in enumerate(dets) if str(d.smufl_name).startswith("timeSig")]
                ssub = R.staff(p, sys_idx, li)
                if k > 0 and (ts or any((r.detail or {}).get("cell") == k for r in
                                        log.rows(Q.METER_TEMPLATE_AT_BAR, ssub) + log.rows(Q.METER_OCR_AT_BAR, ssub))):
                    witness_seen = True
                common = [pb for _gi, d, pb in ts if d.smufl_name in _METER_CLASSES and pb]
                staves.append({"key": li, "lines": list(st.line_ys), "spacing": sp, "x_lo": bx[0],
                               "x_hi": bx[2] if k == 0 else min(bx[2], bx[0] + 7 * sp), "common_box": common[0] if common else None,
                               "hint_x": [(pb[0] + pb[2]) / 2.0 for _gi, _d, pb in ts[:1] if pb],
                               "avoid": [pb for pb in (_page_box(c, d) for d in dets
                                                       if str(d.smufl_name).startswith(("clef", "gClef", "fClef", "cClef", "key"))) if pb]})
                info[li] = (c, sub, ssub, dets, ts, sp, st)
            if len(staves) < 2 or not witness_seen:
                continue
            col = MO.find_column(binary, staves)
            if col["column_x"] is None:
                continue
            frame = frame_cell(k)
            claims = {}
            for li, r in col["by_staff"].items():
                c, sub, ssub, dets, ts, sp, st = info[li]
                if not r.get("found") or not r.get("in_column"):
                    log.abstain(ssub, Q.CLAIMED_AREA, reader=READERS.CV_CLAIMED_AREA, frame=frame, reason=ABSTAIN.NO_INK,
                                cell=k, owner="meter", why=r.get("reason") or "pair_outside_the_column", column_x=col["column_x"])
                    continue
                area = r["area"]
                wit = []
                for gi, d, pb in ts:
                    if pb and _cover_of_smaller(area, pb) >= 0.3:
                        g = log.rows(Q.GLYPH_BOX, R.glyph(p, sys_idx, li, k, gi))
                        wit.append(("detector", g[0].id if g else None))
                if k == 0:
                    reads = ([("template", r0) for r0 in log.rows(Q.METER_TEMPLATE, ssub)]
                             + [("ocr", r0) for r0 in log.rows(Q.METER_OCR, ssub)])
                else:
                    reads = ([("template", r0) for r0 in log.rows(Q.METER_TEMPLATE_AT_BAR, ssub) if (r0.detail or {}).get("cell") == k]
                             + [("ocr", r0) for r0 in log.rows(Q.METER_OCR_AT_BAR, ssub) if (r0.detail or {}).get("cell") == k])
                for src, r0 in reads:
                    wit.append((src, r0.id))
                claims[li] = (r, area, wit, reads)
            # THE WITNESS GATE: a column of ink is a meter only where at least two of its staves also have a detector `timeSig*` box on it (or,
            # for a bar's head, a `*_AT_BAR` read for that bar); a header's template/OCR read exists on every staff of every system and
            # witnesses nothing alone (a tutti chord that aligns across staves passes the ink test, not this one).
            if sum(1 for v in claims.values() if any(w[0] == "detector" or (k > 0 and w[0] in ("template", "ocr")) for w in v[2])) < 2:
                for li in claims:
                    ssub = info[li][2]
                    log.abstain(ssub, Q.CLAIMED_AREA, reader=READERS.CV_CLAIMED_AREA, frame=frame, reason=ABSTAIN.NO_DETECTIONS,
                                cell=k, owner="meter", why="column_without_a_witness", column_x=col["column_x"])
                continue
            for li, (r, area, wit, reads) in sorted(claims.items()):
                c, sub, ssub, dets, ts, sp, st = info[li]
                pairs = []
                for src, r0 in reads:
                    v = r0.value
                    if isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, int) for x in v):
                        pairs.append((src, (v[0], v[1])))
                dets_pg = [(str(d.smufl_name), pb) for _gi, d, pb in ts if pb]
                numbers = _meter_numbers(area, dets_pg, pairs)
                inside = {}
                scan = [(k, dets, c)]
                prev = cell_of.get((st.staff_index, k - 1))
                if prev is not None:
                    scan.append((k - 1, detections.get(R.cell(p, sys_idx, li, k - 1).to_key(), ()), prev))
                for ck, cdets, cc in scan:
                    for gi, d in enumerate(cdets):
                        nm = str(d.smufl_name)
                        if nm.startswith(("timeSig", "clef", "gClef", "fClef", "cClef", "key")):
                            continue
                        pb = _page_box(cc, d)
                        if pb is None or _cover_of_smaller(area, pb) <= 0.0:
                            continue
                        got = MO.ink_inside(binary, pb, area, list(st.line_ys), sp)
                        if got is not None:
                            inside[R.glyph(p, sys_idx, li, ck, gi).to_key()] = dict(got, cls=nm)
                owner_row = next((w[1] for w in wit if w[1]), None)
                log.observe(ssub, Q.CLAIMED_AREA, list(area), reader=READERS.CV_CLAIMED_AREA, frame=frame, cell=k, owner="meter",
                            owner_row=owner_row, unit="area", standing="READ", witnesses=[list(w) for w in wit], form=r["form"],
                            pieces=r["pieces"], thickness_px=r["thickness_px"], column_x=col["column_x"], n_staves=col["n_staves"],
                            n_in_column=col["n_in_column"], numbers=numbers, boxes_inside=inside, space_page_px=round(sp, 3))
                if progress:
                    print(f"  gather claimed area (meter) {ssub.to_key()} cell {k}")


# ─────────────────────────────────────────────────────────────────────────────
# The claimed-area register: clefs and the header column -- ROADMAP 2.181 (plan 2026-10-20 §7 step 2)
# ─────────────────────────────────────────────────────────────────────────────

def _claim_boxes_inside(binary, area, dets, cell, sub_of, line_ys, sp, *, skip=(), named=(), through=False) -> Dict[str, Any]:
    """`boxes_inside` of ONE claim: every non-owner box of the cell whose box meets the area, with the share of its own ink inside
    (`meter_object.ink_inside`), the owner's own naming, and (header column) the line test on its own ink. Measured; decides nothing."""
    from . import claims as CL
    from . import meter_object as MO
    out: Dict[str, Any] = {}
    for gi, d in enumerate(dets):
        key = sub_of(gi)
        nm = str(d.smufl_name)
        if gi in skip or (CL.is_owner_class(nm) and key not in named):
            continue
        pb = _page_box(cell, d)
        if pb is None or not CL.overlaps(area, pb):
            continue
        got = MO.ink_inside(binary, pb, area, line_ys, sp)
        if got is None and key not in named:
            continue
        e = dict(got or {}, cls=nm)
        # ROADMAP 2.181 v2: the two 2.176 tests Sean confirmed (9/9), measured here so the consult can keep them as refusals --
        # the share of the BOX inside the area (2.176's cover) and, for the header column, the box's left edge from the staff's start
        bw, bh = pb[2] - pb[0], pb[3] - pb[1]
        iw, ih = min(pb[2], area[2]) - max(pb[0], area[0]), min(pb[3], area[3]) - max(pb[1], area[1])
        e["box_cover"] = round(iw * ih / (bw * bh), 4) if iw > 0 and ih > 0 and bw > 0 and bh > 0 else 0.0
        if through and getattr(cell, "bbox_page_px", None):
            e["left_edge_spaces"] = round((pb[0] - cell.bbox_page_px[0]) / sp, 3)
        if key in named:
            e["named"] = True
        if through:
            t = CL.through_stroke(binary, pb, sp)
            if t is not None:
                e["through"] = t
        out[key] = e
    return out


def _file_ink_claim(log: Log, ssub: Any, *, strokes: Optional[List[Tuple[int, float]]], why: Optional[str], cell: int,
                    owner: str, owner_row: Any, owner_glyph: Any, standing: str, source: str, **extra: Any) -> None:
    """ROADMAP 2.198: the register's `ink` branch (plan §2.3) -- ONE `Q.CLAIMED_AREA` row, `unit: ink`, whose value is the list of stroke
    ordinals (of `cell`) the owner stands on, filed BESIDE the owner's area claim (which stays). An owner that stands on no filed stroke
    or whose cell has no stroke map ABSTAINS (`why` says which), never claims an empty list. Decides nothing."""
    if not strokes:
        log.abstain(ssub, Q.CLAIMED_AREA, reader=READERS.CV_CLAIMED_REGISTER, frame=frame_cell(cell), reason=ABSTAIN.NO_INK,
                    cell=cell, owner=owner, unit="ink", why=why or "owner_stands_on_no_filed_stroke", source=source)
        return
    log.observe(ssub, Q.CLAIMED_AREA, [i for i, _sh in strokes], reader=READERS.CV_CLAIMED_REGISTER, frame=frame_cell(cell), cell=cell,
                owner=owner, owner_row=owner_row, owner_glyph=owner_glyph, unit="ink", standing=standing, source=source,
                shares=[sh for _i, sh in strokes], **extra)


def gather_claimed_register(log: Log, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                            detections: Dict[str, List[Any]], *, progress: bool = False,
                            stroke_cells: Optional[Dict[Tuple[int, int, int, int], Any]] = None) -> None:
    """`Q.CLAIMED_AREA` rows of owner `clef` and `leading_column` -- ROADMAP 2.181, flag `OMR_CLAIMED_REGISTER` (default OFF).

    PATH: STAGED GATHER, PAGE raster (`pws.page.binary`). AFTER `gather_clef_locator` (reads its rows) and beside
    `gather_meter_object` (whose `meter` rows the same consult reads). Per staff:

    * `clef`, READ: each `Q.CLEF_LOCATED` row -- its fitted box where it was read on cell 0 (the header-window crop has no page frame:
      the union of the boxes it names), and the head boxes it overrode NAMED as its ink (2.11's connection, carried over).
    * `clef`, from the detector: each clef-sized `clef*` box of any cell; READ in a system's first bar within `claims.CLEF_WINDOW_SPACES`
      of its left edge (a system opens with a clef), NARROWED anywhere else (the detector's word alone: 2.144's case).
    * `leading_column`, a PRIOR (Sean 2026-10-20 "idk possibly but not normally"): cell 0, from just left of the staff's start to the
      first clef's left edge on THIS staff; where this staff shows no clef, the narrowest clef offset of its system's other staves
      (`right_edge="system"`); no clef on the system -> abstain. Each box carries the line test on its own ink.

    ⚠️ DECLINED, NOT DEFAULTED: no raster / no staff geometry is no row, never "nothing claimed"."""
    from . import claims as CL
    if not CL.enabled():
        return
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_sys: Dict[int, Dict[int, Any]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is not None:
            by_sys.setdefault(key[0], {})[key[1]] = st
    cells_of: Dict[int, Dict[int, Any]] = {}
    for c in cells:
        cells_of.setdefault(c.staff_index, {})[c.measure_index] = c
    for sys_idx, members in sorted(by_sys.items()):
        clef_left: Dict[int, Tuple[float, float]] = {}       # staff -> (clef left x, cell-0 left x)
        pending_columns = []
        for li, st in sorted(members.items()):
            sp = _spacing(st)
            lines = list(st.line_ys)
            ssub = R.staff(p, sys_idx, li)
            mycells = cells_of.get(st.staff_index, {})
            if not sp or len(lines) < 5 or not mycells:
                continue
            c0 = mycells.get(0)
            # -- clef claims, from the located clef (READ)
            for r0 in log.rows(Q.CLEF_LOCATED, ssub):
                d0 = r0.detail or {}
                if c0 is None or not getattr(c0, "bbox_page_px", None):
                    continue
                named = list(d0.get("overrode_glyph_subjects") or ())
                dets0 = detections.get(R.cell(p, sys_idx, li, 0).to_key(), ())
                area = None
                bb, up = d0.get("bbox"), getattr(c0, "upscale_factor", None)
                if r0.frame == frame_cell(0) and isinstance(bb, (list, tuple)) and len(bb) == 4 and up:
                    cx0, cy0 = c0.bbox_page_px[0], c0.bbox_page_px[1]
                    area = [cx0 + bb[0] / up, cy0 + bb[1] / up, cx0 + (bb[0] + bb[2]) / up, cy0 + (bb[1] + bb[3]) / up]
                if area is None and named:
                    boxes = [_page_box(c0, dets0[int(k.rsplit("/", 1)[1])]) for k in named
                             if int(k.rsplit("/", 1)[1]) < len(dets0)]
                    boxes = [b for b in boxes if b]
                    if boxes:
                        area = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
                if area is None:
                    continue
                inside = _claim_boxes_inside(binary, area, dets0, c0, lambda gi: R.glyph(p, sys_idx, li, 0, gi).to_key(),
                                             lines, sp, named=set(named))
                log.observe(ssub, Q.CLAIMED_AREA, [round(v, 1) for v in area], reader=READERS.CV_CLAIMED_REGISTER, frame=frame_cell(0),
                            cell=0, owner=CL.OWNER_CLEF, owner_row=r0.id, owner_glyph=None, unit="area", standing="READ",
                            source="clef_locator", locator_frame=r0.frame, boxes_inside=inside, space_page_px=round(sp, 3))
                if stroke_cells:               # ROADMAP 2.198 (OMR_STROKE_MAP): the same clef as a list of strokes
                    from . import stroke_map as SM
                    res0 = stroke_cells.get((p, sys_idx, li, 0))
                    upc = getattr(c0, "upscale_factor", None)
                    if res0 is None or isinstance(res0, str) or not upc:
                        _file_ink_claim(log, ssub, strokes=None, why="no stroke map for the cell" if res0 is None or isinstance(res0, str)
                                        else "no upscale factor", cell=0, owner=CL.OWNER_CLEF, owner_row=r0.id, owner_glyph=None,
                                        standing="READ", source="clef_locator")
                    else:
                        cb0 = c0.bbox_page_px
                        canon = [(area[0] - cb0[0]) * upc, (area[1] - cb0[1]) * upc, (area[2] - cb0[0]) * upc, (area[3] - cb0[1]) * upc]
                        _file_ink_claim(log, ssub, strokes=[(i, sh) for i, sh in SM.strokes_in_box(res0, canon) if sh >= SM.COVER_SHARE_MIN],
                                        why=None, cell=0, owner=CL.OWNER_CLEF, owner_row=r0.id, owner_glyph=None, standing="READ",
                                        source="clef_locator", cover_min=SM.COVER_SHARE_MIN)
                if r0.frame == frame_cell(0):
                    prev = clef_left.get(li)
                    clef_left[li] = (min(area[0], prev[0]) if prev else area[0], c0.bbox_page_px[0])
            # -- clef claims, from the detector's clef-sized boxes
            for k, c in sorted(mycells.items()):
                cb = getattr(c, "bbox_page_px", None)
                if not cb:
                    continue
                dets = detections.get(R.cell(p, sys_idx, li, k).to_key(), ())
                for gi, d in enumerate(dets):
                    pb = _page_box(c, d)
                    if not CL.is_clef_box(d.smufl_name, pb, sp):
                        continue
                    standing = CL.clef_box_standing(pb, cb, sp, k)
                    gsub = R.glyph(p, sys_idx, li, k, gi)
                    g = log.rows(Q.GLYPH_BOX, gsub)
                    inside = _claim_boxes_inside(binary, pb, dets, c, lambda j, k=k: R.glyph(p, sys_idx, li, k, j).to_key(),
                                                 lines, sp, skip=(gi,))
                    log.observe(ssub, Q.CLAIMED_AREA, [round(v, 1) for v in pb], reader=READERS.CV_CLAIMED_REGISTER,
                                frame=frame_cell(k), cell=k, owner=CL.OWNER_CLEF, owner_row=g[0].id if g else None,
                                owner_glyph=gsub.to_key(), unit="area", standing=standing, source="detector",
                                start_spaces=round((pb[0] - cb[0]) / sp, 3),
                                cls=str(d.smufl_name), boxes_inside=inside, space_page_px=round(sp, 3))
                    if stroke_cells:           # ROADMAP 2.198 (OMR_STROKE_MAP): the owner box's strokes, read off its `Q.GLYPH_STROKES` row
                        from . import stroke_map as SM
                        gs = log.rows(Q.GLYPH_STROKES, gsub)
                        mine = [(int(i), float(sh)) for i, sh in zip(gs[0].value or (), (gs[0].detail or {}).get("shares") or ())] if gs else None
                        _file_ink_claim(log, ssub, strokes=mine, why=None if gs else "no GLYPH_STROKES row (the cell has no stroke map)",
                                        cell=k, owner=CL.OWNER_CLEF, owner_row=g[0].id if g else None, owner_glyph=gsub.to_key(),
                                        standing=standing, source="detector", cls=str(d.smufl_name), cover_min=SM.COVER_SHARE_MIN)
                    if k == 0 and standing == "READ":
                        prev = clef_left.get(li)
                        clef_left[li] = (min(pb[0], prev[0]) if prev else pb[0], cb[0])
            if c0 is not None and getattr(c0, "bbox_page_px", None):
                pending_columns.append((li, st, sp, lines, ssub, c0))
        offsets = [(x - x0) for x, x0 in clef_left.values() if x > x0]
        for li, st, sp, lines, ssub, c0 in pending_columns:
            cb = c0.bbox_page_px
            if li in clef_left and clef_left[li][0] > cb[0]:
                right, src = clef_left[li][0], "own_clef"
            elif offsets:
                right, src = cb[0] + min(offsets), "system"
            else:
                log.abstain(ssub, Q.CLAIMED_AREA, reader=READERS.CV_CLAIMED_REGISTER, frame=frame_cell(0), reason=ABSTAIN.NO_DETECTIONS,
                            cell=0, owner=CL.OWNER_COLUMN, why="no_clef_on_the_system")
                continue
            area = CL.leading_column(cb, right, sp)
            if area is None:
                continue
            dets0 = detections.get(R.cell(p, sys_idx, li, 0).to_key(), ())
            inside = _claim_boxes_inside(binary, area, dets0, c0, lambda gi: R.glyph(p, sys_idx, li, 0, gi).to_key(),
                                         lines, sp, through=True)
            log.observe(ssub, Q.CLAIMED_AREA, area, reader=READERS.CV_CLAIMED_REGISTER, frame=frame_cell(0), cell=0,
                        owner=CL.OWNER_COLUMN, owner_row=None, owner_glyph=None, unit="area", standing="READ", prior=True,
                        right_edge=src, boxes_inside=inside, space_page_px=round(sp, 3))
            if progress:
                print(f"  gather claimed area (register) {ssub.to_key()}")


def gather_key_signature_claim(log: Log, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                               detections: Dict[str, List[Any]], *, progress: bool = False) -> None:
    """`Q.CLAIMED_AREA` rows of owner `key_signature` -- ROADMAP 2.183 (claimed-area step 3), flag `OMR_KEY_SIGNATURE_CLAIM` (default ON;
    needs `OMR_CLAIMED_REGISTER`, which it files into).

    PATH: STAGED GATHER, PAGE raster. AFTER `gather_claimed_register`. Per staff and cell: the key run (`key_slots.claim_window` -- the
    existing 2.100 window, plus a run that opens with CANCELLING NATURALS, Sean 2026-10-20) drawn as one area in page px, from the clef's
    right edge to the run's last slot, level with it. The detector's boxes are the run's members (a window is only ever drawn around
    what the detector boxed as a key accidental); this reader decides nothing about any other box -- it files, for every other box of the
    cell that meets the area, whether it STANDS in the window (the 2.100 centre rule, `named`: Sean 2026-10-12 "only clefs appear before
    key accidentals") and the share of its own ink inside (`meter_object.ink_inside`).

    * cell 0 (the header): standing READ -- the convention Sean confirmed.
    * a later cell (a key change in mid-system): always NARROWED, the staves drawing a window there at one x are recorded as
      `witness_staves` (a key change is printed on every staff at one bar, page-facts §2) but do not make it READ: on Litolff 16 of 69
      such windows had a witness and one refused a real eighth note.

    ⚠️ DECLINED, NOT DEFAULTED: no raster / no staff geometry / no window is no row."""
    from . import claims as CL
    from . import meter_object as MO
    from .adjudicators import key_slots as KS
    if not CL.key_active():
        return
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_sys: Dict[int, Dict[int, Any]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is not None:
            by_sys.setdefault(key[0], {})[key[1]] = st
    cells_of: Dict[int, Dict[int, Any]] = {}
    for c in cells:
        cells_of.setdefault(c.staff_index, {})[c.measure_index] = c
    for sys_idx, members in sorted(by_sys.items()):
        drawn = []                                   # (staff li, cell k, window, boxes, st, sp, lines, cell, dets)
        for li, st in sorted(members.items()):
            sp = _spacing(st)
            lines = list(st.line_ys)
            if not sp or len(lines) < 5:
                continue
            for k, c in sorted(cells_of.get(st.staff_index, {}).items()):
                dets = detections.get(R.cell(p, sys_idx, li, k).to_key(), ())
                boxes = []
                for gi, d in enumerate(dets):
                    pb = _page_box(c, d)
                    if pb is not None:
                        boxes.append(KS.KeyBox(R.glyph(p, sys_idx, li, k, gi).to_key(), str(d.smufl_name), pb[0], pb[1],
                                               pb[2] - pb[0], pb[3] - pb[1]))
                win = KS.claim_window(boxes, sp)
                if win is not None:
                    drawn.append((li, k, win, boxes, st, sp, lines, c, dets))
        for li, k, win, boxes, st, sp, lines, c, dets in drawn:
            if k == 0:
                standing, witnesses = "READ", None
            else:
                # a later cell is NEVER read: a second staff's window at the same x did not make it real (Litolff replay: 69 mid-system
                # windows, a real eighth NOTE refused in one with a witness; neither plate changes key, so no change is confirmed)
                witnesses = sorted({lj for lj, kj, wj, *_ in drawn if kj == k and lj != li and abs(wj.lo - win.lo) <= 1.5 * sp})
                standing = "NARROWED"
            area = [round(win.lo, 1), round(win.y_lo, 1), round(win.hi, 1), round(win.y_hi, 1)]
            by_id = {b.row_id: b for b in boxes}
            inside: Dict[str, Any] = {}
            for gi, d in enumerate(dets):
                key = R.glyph(p, sys_idx, li, k, gi).to_key()
                b = by_id.get(key)
                if b is None or key in win.members or str(d.smufl_name).startswith(("clef", "key")):
                    continue
                stands = KS.stands_in_the_window(win, b) and KS.is_refusable_class(b.cls)
                pb = (b.x, b.y, b.x + b.w, b.y + b.h)
                if not CL.overlaps(area, pb) and not stands:
                    continue
                got = MO.ink_inside(binary, pb, area, lines, sp)
                if got is None and not stands:
                    continue
                e = dict(got or {}, cls=b.cls)
                if stands:
                    e["named"] = True
                    e["stand_margin_spaces"] = KS.stand_margin_spaces(win, b, sp)
                inside[key] = e
            ssub = R.staff(p, sys_idx, li)
            log.observe(ssub, Q.CLAIMED_AREA, area, reader=READERS.CV_KEY_SIGNATURE_CLAIM, frame=frame_cell(k), cell=k,
                        owner=CL.OWNER_KEY, owner_row=win.members[0], owner_glyph=win.members[0], unit="area", standing=standing,
                        source="detector_key_run", members=list(win.members), clef=win.clef, slots=win.slots,
                        witness_staves=witnesses, boxes_inside=inside, space_page_px=round(sp, 3))
            if progress:
                print(f"  gather claimed area (key signature) {ssub.to_key()} cell {k}")


def gather_key_object(log: Log, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                      detections: Dict[str, List[Any]], *, dossier: Any = None, written_counts: Any = None,
                      progress: bool = False) -> None:
    """`Q.CLAIMED_AREA` rows of owner `key_signature` read ONCE PER SYSTEM -- ROADMAP 2.187, flag `OMR_KEY_PER_SYSTEM` (default ON; needs
    `OMR_KEY_SIGNATURE_CLAIM` and `OMR_CLAIMED_REGISTER`, which it files into).

    PATH: STAGED GATHER, PAGE raster. AFTER `gather_key_signature_claim` and `gather_meter_object` (reads the meter's left edge). 2.183 drew
    each staff's key window from that staff's own detector boxes, so a flat the detector boxed as a rest, beyond the last drawn slot, was
    never inside any window. The page prints ONE signature per system: `key_object.find_object` reads every staff of the system (raster
    pieces + detector key/accidental boxes), takes the run's COUNT from the staves' agreement (the largest count two staves read in full)
    and checks it against the dossier's parts (a different source; admitted by the confirmed sheet only -- `dossier` or the log's
    `Q.DOSSIER_FACT` row; silent otherwise), and files, per staff, the area of N slots placed from THAT staff's clef edge:
    standing READ where the staff read at least one slot itself, NARROWED where it read none (a transposing staff -- never forced).
    The 2.183 consult refuses a box standing in a READ area and narrows the rest. Mid-system key changes: cell 0 only here (no change on
    either plate); `find_object` is bar-agnostic and tested on constructed rasters.

    ⚠️ DECLINED, NOT DEFAULTED: no raster / no clef edge / no count / a count the dossier does not print is an ABSTENTION on every staff
    of the system, counted, never a key."""
    from . import claims as CL
    from . import key_object as KO
    from . import meter_object as MO
    from .adjudicators import key_slots as KS
    if not CL.key_active() or not KO.enabled():
        return
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    if dossier is None:
        rows = log.rows(Q.DOSSIER_FACT, R.DOCUMENT)
        dossier = rows[0].value if rows else None
    allowed = KO.allowed_counts(dossier)
    by_sys: Dict[int, Dict[int, Any]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is not None:
            by_sys.setdefault(key[0], {})[key[1]] = st
    cell_of = {(c.staff_index, c.measure_index): c for c in cells}
    for sys_idx, members in sorted(by_sys.items()):
        info, staves = {}, []
        for li, st in sorted(members.items()):
            c = cell_of.get((st.staff_index, 0))
            sp = _spacing(st)
            if c is None or not getattr(c, "bbox_page_px", None) or not sp or len(list(st.line_ys)) < 5:
                continue
            dets = detections.get(R.cell(p, sys_idx, li, 0).to_key(), ())
            clef_x, kb, clef_box = None, [], None
            for gi, d in enumerate(dets):
                pb = _page_box(c, d)
                nm = str(d.smufl_name)
                if pb is None:
                    continue
                if nm.startswith(("clef", "gClef", "fClef", "cClef")) and (pb[3] - pb[1]) / sp >= CL.CLEF_BOX_MIN_HEIGHT_SPACES:
                    if clef_x is None or pb[2] < clef_x:
                        clef_box = (nm, pb)
                    clef_x = pb[2] if clef_x is None else min(clef_x, pb[2])
                elif nm.startswith(("key", "accidental")):
                    kb.append(list(pb))
            meter_left = None
            for r0 in log.rows(Q.CLAIMED_AREA, R.staff(p, sys_idx, li)):
                d0 = r0.detail or {}
                if d0.get("owner") == CL.OWNER_METER and d0.get("cell") == 0:
                    meter_left = float(r0.value[0])
            info[li] = (c, dets, sp, st, meter_left)
            staves.append({"key": li, "lines": list(st.line_ys), "spacing": sp, "x_start": clef_x, "x_hi": None, "boxes": kb,
                           "clef_measured": KO.clef_of_box(clef_box, list(st.line_ys)) if clef_box else None})
        known = sorted(s0["x_start"] for s0 in staves if s0["x_start"] is not None)
        med = known[len(known) // 2] if known else None
        for s0 in staves:
            sp = s0["spacing"]
            fb = s0["x_start"] is None
            s0["clef_edge"] = "fallback_median" if fb else "detector_clef_box"
            if fb:
                s0["x_start"] = med
            if s0["x_start"] is None:
                continue
            reach = s0["x_start"] + KO.WINDOW_REACH_SPACES * sp
            ml = info[s0["key"]][4]
            s0["x_hi"] = min(ml, reach) if ml is not None and ml > s0["x_start"] else reach
            s0["kb_in"] = [b for b in s0["boxes"]]
        ok = [s0 for s0 in staves if s0["x_start"] is not None and s0["x_hi"] is not None]
        if len(ok) < 2:
            continue
        obj = KO.find_object(binary, ok, allowed_counts=allowed)
        if obj["status"] != "found":
            for s0 in ok:
                log.abstain(R.staff(p, sys_idx, s0["key"]), Q.CLAIMED_AREA, reader=READERS.CV_KEY_OBJECT, frame=frame_cell(0),
                            reason=ABSTAIN.NO_COLUMN_EVIDENCE, cell=0, owner=CL.OWNER_KEY, why=obj["status"], counts=obj["counts"],
                            dossier=obj["dossier"])
            continue
        for s0 in ok:
            li = s0["key"]
            c, dets, sp, st, _ml = info[li]
            cl = KO.claim_for_staff(obj, li, s0["lines"], sp, written_count=(written_counts or {}).get(li))
            ssub = R.staff(p, sys_idx, li)
            if cl is None:
                continue
            ko = {"system_count": obj["N"], "basis": obj["basis"], "dossier": obj["dossier"], "allowed_counts": allowed,
                  "system_counts": obj["counts"], "pitch_spaces": obj["pitch_spaces"], "clef_edge": s0["clef_edge"],
                  "clef_measured": s0.get("clef_measured"), "own_slots": cl["own"], "placed_slots": cl["placed"], "more_than_system": obj["by_staff"][li]["more_than_system"],
                  # 2.187b: what each slot the staff READ is (shape, step against the lines there): ADJUDICATE / the report check the fixed order
                  "read_pieces": [dict(KO.measure_tail_box(binary, list(st.line_ys), sp, [q["x0"], q["y0"], q["x1"], q["y1"]]) or {}, slot=qi + 1)
                                  for qi, q in enumerate(obj["by_staff"][li]["pieces"][:obj["N"]])]}
            for part in cl["parts"]:
                area = part["area"]
                win = KS.KeySlotWindow(lo=area[0], hi=area[2], y_lo=area[1], y_hi=area[3], members=(), clef=None, slots=cl["slots"],
                                       next_x=None, next_tol=0.0)
                inside: Dict[str, Any] = {}
                # ROADMAP 2.187b: the TAIL (slots this staff did not read) reaches out to the staff's window bound, and each box in it carries
                # what its own ink IS (shape, staff step against the lines locally, a solid head) -- measurements; ADJUDICATE judges them.
                tail_part = part["kind"] in ("placed", "none_read")
                wide = [area[0], area[1], max(area[2], float(s0["x_hi"])), area[3]] if tail_part else area
                for gi, d in enumerate(dets):
                    pb = _page_box(c, d)
                    nm = str(d.smufl_name)
                    if pb is None or nm.startswith(("clef", "key")):
                        continue
                    b = KS.KeyBox(R.glyph(p, sys_idx, li, 0, gi).to_key(), nm, pb[0], pb[1], pb[2] - pb[0], pb[3] - pb[1])
                    stands = KS.stands_in_the_window(win, b) and KS.is_refusable_class(nm)
                    if not CL.overlaps(wide, pb) and not stands:
                        continue
                    got = MO.ink_inside(binary, pb, area, list(st.line_ys), sp)
                    if got is None and not stands:
                        continue
                    e = dict(got or {}, cls=nm)
                    if tail_part:
                        e["tail"] = KO.measure_tail_box(binary, list(st.line_ys), sp, pb) or {}
                    if stands:
                        e["named"] = True
                        e["stand_margin_spaces"] = KS.stand_margin_spaces(win, b, sp)
                    inside[b.row_id] = e
                log.observe(ssub, Q.CLAIMED_AREA, area, reader=READERS.CV_KEY_OBJECT, frame=frame_cell(0), cell=0, owner=CL.OWNER_KEY,
                            owner_row=None, unit="area", standing=part["standing"], source="system_key_object", slots=cl["slots"],
                            part=part["kind"], key_object=ko, boxes_inside=inside, space_page_px=round(sp, 3),
                            tail_info=({"slot_cx": {str(k): round(v, 1) for k, v in KO.slot_centres(obj, li, sp).items()}, "spacing": round(sp, 3),
                                        "own": cl["own"], "N": obj["N"]} if tail_part else None))
            if progress:
                print(f"  gather claimed area (key object) {ssub.to_key()}")


def gather_clef_slot_claim(log: Log, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                           detections: Dict[str, List[Any]], *, progress: bool = False,
                           stroke_cells: Optional[Dict[Tuple[int, int, int, int], Any]] = None) -> None:
    """`Q.CLAIMED_AREA` rows of owner `clef` for a staff that has NO clef claim of its own -- ROADMAP 2.208, flag `OMR_CLEF_SLOT_CLAIM`
    (default OFF; needs `OMR_CLAIMED_REGISTER`).

    PATH: STAGED GATHER, PAGE raster. AFTER `gather_key_object` (reads the key claim's left edge). WHY (2.205 tile 5, Litolff p4 staff 8,
    measured): `gather_claimed_register` files a clef claim only from a located clef (cell 0 frame, or a header-window read that
    overrode a head box) or a clef-sized detector box. A staff whose clef nothing located and the detector never boxed has its clef
    DECIDED only by carry from other systems (EVALUATE) -- and the ink is still there, claimed by nobody: the header column stops at the
    system's clef offset, the key claim starts later, and a detector head drawn on the clef's body stands unopposed.

    CONVENTION ASSUMED: a system opens with a clef on every staff (page-facts), so the space between the system's clef offset and the key
    claim is that clef's. WHAT WOULD FALSIFY IT: a print-confirmed note whose ink lies in the slot. NOT CONFIRMED beyond the two plates.

    Per staff with a `leading_column` claim drawn from the SYSTEM's clef offset (`right_edge == "system"`: this staff showed no clef) and no
    cell-0 clef area claim of any standing: ONE `clef` area claim, standing READ, `source: clef_slot` -- from that offset to the staff's key
    claim (cell 0), never past the widest clef a sibling staff shows plus `claims.CLEF_SLOT_PAD_SPACES`. With the stroke map, the strokes
    >= `COVER_SHARE_MIN` inside the slot are filed beside it as an `ink` claim, as for a located clef. No sibling clef, no column, no
    raster or a slot narrower than one space files nothing and says so (rule 8): never "no clef here".

    ⚠️ This reader draws the claim and measures `boxes_inside`; it decides nothing about any box (the consult is `claimed_by`)."""
    from . import claims as CL
    if not CL.clef_slot_enabled():
        return
    binary = getattr(getattr(pws, "page", None), "binary", None)
    if binary is None:
        return
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    by_sys: Dict[int, Dict[int, Any]] = {}
    for st in pws.staves:
        key = local.get(st.staff_index)
        if key is not None:
            by_sys.setdefault(key[0], {})[key[1]] = st
    cells_of: Dict[int, Dict[int, Any]] = {}
    for c in cells:
        cells_of.setdefault(c.staff_index, {})[c.measure_index] = c

    def _cell0(rows: Sequence[Any], owner: str, unit: str = "area") -> List[Any]:
        return [r for r in rows if (r.detail or {}).get("owner") == owner and (r.detail or {}).get("unit") == unit
                and (r.detail or {}).get("cell") == 0]

    for sys_idx, members in sorted(by_sys.items()):
        rows_of = {li: list(log.rows(Q.CLAIMED_AREA, R.staff(p, sys_idx, li))) for li in members}
        sibling_right = [float(r.value[2]) for li in members for r in _cell0(rows_of[li], CL.OWNER_CLEF)
                         if (r.detail or {}).get("standing") == "READ" and isinstance(r.value, list) and len(r.value) == 4]
        for li, st in sorted(members.items()):
            rows = rows_of[li]
            cols = [r for r in _cell0(rows, CL.OWNER_COLUMN) if (r.detail or {}).get("right_edge") == "system"]
            if not cols or _cell0(rows, CL.OWNER_CLEF):
                continue                                   # the staff showed its own clef (or no system clef offset exists)
            sp = _spacing(st)
            lines = list(st.line_ys)
            ssub = R.staff(p, sys_idx, li)
            c0 = cells_of.get(st.staff_index, {}).get(0)
            if not sp or len(lines) < 5 or c0 is None or not getattr(c0, "bbox_page_px", None):
                continue
            if not sibling_right:
                log.abstain(ssub, Q.CLAIMED_AREA, reader=READERS.CV_CLEF_SLOT_CLAIM, frame=frame_cell(0), reason=ABSTAIN.NO_DETECTIONS,
                            cell=0, owner=CL.OWNER_CLEF, unit="area", why="no_clef_on_the_system", source="clef_slot")
                continue
            left = float(cols[0].value[2])
            keys = [float(r.value[0]) for r in _cell0(rows, CL.OWNER_KEY) if isinstance(r.value, list) and len(r.value) == 4]
            key_lo = min(keys) if keys else None
            area = CL.clef_slot(left, key_lo, max(sibling_right), lines, sp)
            if area is None:
                log.abstain(ssub, Q.CLAIMED_AREA, reader=READERS.CV_CLEF_SLOT_CLAIM, frame=frame_cell(0), reason=ABSTAIN.NO_INK,
                            cell=0, owner=CL.OWNER_CLEF, unit="area", why="slot_narrower_than_a_space", source="clef_slot")
                continue
            located = list(log.rows(Q.CLEF_LOCATED, ssub))
            dets0 = detections.get(R.cell(p, sys_idx, li, 0).to_key(), ())
            inside = _claim_boxes_inside(binary, area, dets0, c0, lambda gi: R.glyph(p, sys_idx, li, 0, gi).to_key(), lines, sp)
            owner_row = located[0].id if located else None
            log.observe(ssub, Q.CLAIMED_AREA, area, reader=READERS.CV_CLEF_SLOT_CLAIM, frame=frame_cell(0), cell=0,
                        owner=CL.OWNER_CLEF, owner_row=owner_row, owner_glyph=None, unit="area", standing="READ", source="clef_slot",
                        boxes_inside=inside, space_page_px=round(sp, 3))
            if stroke_cells:                               # the same slot as a list of strokes (2.198 ink claim)
                from . import stroke_map as SM
                res0 = stroke_cells.get((p, sys_idx, li, 0))
                upc = getattr(c0, "upscale_factor", None)
                if res0 is None or isinstance(res0, str) or not upc:
                    _file_ink_claim(log, ssub, strokes=None, why="no stroke map for the cell" if res0 is None or isinstance(res0, str)
                                    else "no upscale factor", cell=0, owner=CL.OWNER_CLEF, owner_row=owner_row, owner_glyph=None,
                                    standing="READ", source="clef_slot")
                else:
                    cb0 = c0.bbox_page_px
                    canon = [(area[0] - cb0[0]) * upc, (area[1] - cb0[1]) * upc, (area[2] - cb0[0]) * upc, (area[3] - cb0[1]) * upc]
                    _file_ink_claim(log, ssub, strokes=[(i, sh) for i, sh in SM.strokes_in_box(res0, canon) if sh >= SM.COVER_SHARE_MIN],
                                    why=None, cell=0, owner=CL.OWNER_CLEF, owner_row=owner_row, owner_glyph=None, standing="READ",
                                    source="clef_slot", cover_min=SM.COVER_SHARE_MIN)
            if progress:
                print(f"  gather claimed area (clef slot) {ssub.to_key()}")


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

    ⚠️⚠️ FOUR STATES FOR AN EMPTY STAFF, NOT ONE, AND UNTIL 2026-09-16 THIS
    FUNCTION COULD SPELL ONLY THE LAST OF THEM:

    | what happened | what is written |
    |---|---|
    | a requested rung is not installed here | `READER_UNAVAILABLE` |
    | a requested rung was installed and threw | `READER_UNAVAILABLE` |
    | no OCR rung was requested at all | `OUT_OF_SCOPE` |
    | every requested rung ran and read nothing here | `NO_INK` |

    The first three used to be written as the fourth. That is the fallback
    converting *cannot tell* into a definite answer -- here into "this page
    prints no instrument name" -- which CLAUDE.md names as never the safe
    default, and it is live on the staged path's OWN DEFAULT: `--surya` and
    `--ocr` are opt-in, so every staged run this repo has made records 75 of
    75 scanned staves as printing no label, when in truth no rung that could
    read a scan was ever asked. `gather_direction_words` already makes this
    exact distinction for the word reader and says why; this is that contract
    for the label reader.

    ⚠️ A REQUESTED-BUT-MISSING RUNG POISONS THE WHOLE PAGE, not only the
    staves that rung would have read, and that is the WEAKER claim on
    purpose. Where Surya is absent and Tesseract ran, a staff Tesseract found
    nothing on is still one Surya might have read -- so the row says
    "cannot tell" and carries `rungs_ran` / `rungs_unavailable` beside it, and
    the split stays recoverable. Same reasoning as the direction reader
    filing `NO_READING` rather than guessing which of two refusals a crop hit.

    ⚠️ AND THE READER NAMED ON AN OBSERVATION IS NOW THE RUNG THAT READ IT.
    Every label used to be filed under `READERS.TEXT_LAYER` whatever produced
    it -- on a 19th-century scan the text layer reads NOTHING, so all 50
    labels the cascade found were attributed to the one rung that certainly
    did not find them. Two rows from one reader are ONE signal
    (`adjudicate.Evidence.independent`), so a mis-named reader is a
    mis-counted witness, not a cosmetic slip.
    """
    if pdf_path is None:
        _stub_per_staff(log, cells, local, Q.MARGIN_LABEL, READERS.TEXT_LAYER,
                        FRAME_MARGIN, "no pdf_path supplied to gather()")
        return

    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    page_sub = R.page(p)
    rungs = _label_rung_state(surya_fallback, ocr_fallback)

    # One PAGE row per rung that was asked for and cannot run. The reader
    # named is the ABSENT one, so `gather_coverage` and any census can see
    # which install is missing without parsing a note.
    for name in rungs["unavailable"]:
        probe_error = rungs["errors"].get(name)
        log.abstain(page_sub, Q.MARGIN_LABEL, reader=_RUNG_READER[name],
                    frame=FRAME_MARGIN, reason=ABSTAIN.READER_UNAVAILABLE,
                    note=(f"{name} was requested and is not installed here"
                          if probe_error is None else
                          f"{name} was requested and its availability "
                          f"probe raised"),
                    rungs_requested=list(rungs["requested"]),
                    rungs_available=list(rungs["available"]),
                    rungs_unavailable=list(rungs["unavailable"]),
                    **({} if probe_error is None
                       else {"error": probe_error}))

    tiers: List[int] = [0, 0, 0, 0, 0]
    sources: Dict[int, str] = {}
    failures: List[Dict[str, Any]] = []
    try:
        from pathlib import Path as _Path
        from ..assist import Assist
        from ..contextual import _labels_for_page
        labels = _labels_for_page(
            pws, _Path(str(pdf_path)), p, assist=Assist("none"), budget=[0],
            surya_fallback=surya_fallback, ocr_fallback=ocr_fallback,
            tiers=tiers, sources=sources, failures=failures)
    except Exception as exc:                                  # noqa: BLE001
        # ⚠️ An optional reader that cannot run ABSTAINS -- it does not lose
        # the page. But it abstains LOUDLY enough to be told from a reader
        # that ran and found nothing: the exception class goes in the detail.
        # ⚠️ AND THE REASON IS `READER_UNAVAILABLE`, NOT `NOT_IMPLEMENTED`.
        # A cascade that threw is not a declared stub, and filing it as one
        # put a real defect in the bucket reserved for unwritten code --
        # where `gather_coverage` reports it as build progress.
        log.abstain(page_sub, Q.MARGIN_LABEL, reader=READERS.TEXT_LAYER,
                    frame=FRAME_MARGIN, reason=ABSTAIN.READER_UNAVAILABLE,
                    error=type(exc).__name__, note=str(exc)[:200],
                    rungs_requested=list(rungs["requested"]))
        _labels_abstain_per_staff(
            log, cells, local, ABSTAIN.READER_UNAVAILABLE,
            note=f"the label cascade failed: {type(exc).__name__}",
            error=type(exc).__name__)
        return

    # A rung that was installed, was asked, and threw. The cascade swallows
    # it by design; without this row the page reads as one that prints no
    # labels. Routed out of `contextual._read_labels_for_page`.
    for f in failures:
        log.abstain(page_sub, Q.MARGIN_LABEL,
                    reader=_RUNG_READER.get(str(f.get("rung")),
                                            READERS.TEXT_LAYER),
                    frame=FRAME_MARGIN, reason=ABSTAIN.READER_UNAVAILABLE,
                    error=str(f.get("error") or ""),
                    note=str(f.get("note") or "")[:200],
                    rung_failed=str(f.get("rung")))

    census = {"text_layer": tiers[0], "surya": tiers[1],
              "tesseract": tiers[2], "vision": tiers[3], "human": tiers[4]}
    # ⚠️ THE WEAKER CLAIM WINS. Only where every rung that was asked for
    # actually ran can an empty staff mean "nothing is printed here".
    if rungs["unavailable"] or failures:
        empty_reason = ABSTAIN.READER_UNAVAILABLE
    elif not rungs["requested"]:
        empty_reason = ABSTAIN.OUT_OF_SCOPE
    else:
        empty_reason = ABSTAIN.NO_INK

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
                        frame=FRAME_MARGIN, reason=empty_reason,
                        rungs_requested=list(rungs["requested"]),
                        rungs_ran=list(rungs["available"]),
                        rungs_unavailable=list(rungs["unavailable"]),
                        rungs_failed=[str(f.get("rung")) for f in failures],
                        label_tiers=dict(census))
            continue
        rung = sources.get(int(lab.staff_index), "text_layer")
        log.observe(sub, Q.MARGIN_LABEL, lab.text,
                    reader=_RUNG_READER.get(rung, READERS.TEXT_LAYER),
                    frame=FRAME_MARGIN,
                    reader_confidence=lab.confidence, reader_alias=lab.alias,
                    y_center_px=lab.y_center_px,
                    rung=rung, label_tiers=dict(census),
                    # ROADMAP 2.95: present only where the text was completed
                    # with the word printed between two braced staves.
                    **({"shared_word": lab.shared_word}
                       if getattr(lab, "shared_word", "") else {}))


def _labels_abstain_per_staff(log: Log, cells: Sequence[Any],
                              local: Dict[int, Tuple[int, int]],
                              reason: str, **detail: Any) -> int:
    """One margin-label abstention per staff, with an EXPLICIT reason.

    ⚠️ NOT `_stub_per_staff`, which hardcodes `NOT_IMPLEMENTED`. That word
    means "this decision is not written"; a reader that was asked and could
    not run is a different fact, and `gather_coverage` reads the two
    differently -- one is build progress, the other is a blind page.
    """
    n = 0
    seen = set()
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.staff(c.page_index, key[0], key[1])
        if sub.to_key() in seen:
            continue
        seen.add(sub.to_key())
        log.abstain(sub, Q.MARGIN_LABEL, reader=READERS.TEXT_LAYER,
                    frame=FRAME_MARGIN, reason=reason, **detail)
        n += 1
    return n


#: Glyph indices for direction-word CANDIDATES, offset far past any detector
#: index so the OCR rung and the detector can never collide in one cell's key
#: space. Same guard and same reason as `_CV_GLYPH_BASE`: a collision would
#: not raise -- it would silently merge two readers' rows into one subject,
#: which is precisely the "two rows from one reader are ONE signal" mistake
#: made by accident.
_DIRECTION_GLYPH_BASE = 90000


def _direction_page_dict(pws: Any, cells: Sequence[Any],
                         local: Dict[int, Tuple[int, int]],
                         detections: Dict[str, List[Any]]) -> Dict[str, Any]:
    """The page shape `direction_text` reads, built from what GATHER holds.

    ⚠️ THE SHIM IS THE ALTERNATIVE TO REBUILDING THE READER, and that is why
    it exists rather than a re-implementation. `find_candidates` wants a
    `page_dict` because it was written against `transcribe`'s output: the
    measure SPANS say which bar a word falls in, and the DETECTIONS are
    subtracted from the page's ink so "find the text" becomes "find the ink".
    Both facts are already in GATHER's hands; only their spelling differs.

    ⚠️⚠️ `bbox_page` IS `(x, y, w, h)` AND `bbox_page_px` IS `(x0, y0, x1, y1)`.
    Both conventions live in this repo, `_page_box` returns CORNERS and
    `_blank_detections` reads WIDTHS -- and confusing them does not raise, it
    blanks the wrong rectangle and leaves the word standing as unaccounted
    ink. Converted here, once, explicitly, exactly as `gather_wedge_boxes`
    converts for `blank_point_detections`.
    """
    page_staff_of = {v: k for k, v in local.items()}

    by_staff: Dict[int, Dict[str, Any]] = {}
    for c in cells:
        staff = by_staff.setdefault(int(c.staff_index),
                                    {"staff_index": int(c.staff_index),
                                     "measures": {}})
        box = getattr(c, "bbox_page_px", None)
        staff["measures"][int(c.measure_index)] = {
            "measure_index": int(c.measure_index),
            "bbox_page_px": [int(v) for v in box] if box else None,
            "detections": [],
            "_cell": c,
        }

    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        page_staff = page_staff_of.get((sub.system, sub.staff))
        if page_staff is None:
            continue
        staff = by_staff.get(int(page_staff))
        if staff is None:
            continue
        m = staff["measures"].get(int(sub.cell))
        if m is None:
            continue
        cell = m["_cell"]
        for det_index, d in enumerate(dets):
            box = _page_box(cell, d)
            if box is None:
                continue
            x0, y0, x1, y1 = box
            m["detections"].append({
                "class": d.smufl_name,
                "category": d.category,
                "cell_key": cell_key,
                "detector_index": det_index,
                "bbox_page": [int(x0), int(y0),
                              int(round(x1 - x0)), int(round(y1 - y0))],
            })

    staves = []
    for k in sorted(by_staff):
        st = by_staff[k]
        measures = [dict(m) for _i, m in sorted(st["measures"].items())]
        for m in measures:
            m.pop("_cell", None)
        staves.append({"staff_index": st["staff_index"], "measures": measures})
    return {"systems": [{"staves": staves}]}


def _direction_cells_abstain(log: Log, cells: Sequence[Any],
                             local: Dict[int, Tuple[int, int]],
                             reason: str, **detail: Any) -> int:
    """File this page-wide state on EVERY cell, and say why that is needed.

    ⚠️ A DECISION'S SUBJECTS ARE THE ROWS IN THE LOG. `adjudicate_direction`
    takes its domain from `Q.DIRECTION_WORD`, so a page whose OCR rung could
    not run would have NO `Q.DIRECTION` subject at all -- and a family that is
    never ASKED reports `decided: 0, abstained: {}`, which is
    indistinguishable from a family that was asked and had nothing to say.
    That is the ABSENT/DECLINED collapse the record exists to prevent, and it
    would collapse the one distinction this gatherer is built around.

    So the page-level reason is also written per cell, which is exactly what
    `gather_dynamic_letters` does and for a related reason. The page row is
    kept as well: it carries the counts (`n_candidates`, `readers`) that are
    properties of the PAGE and would be repeated N times here.
    """
    n = 0
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        log.abstain(sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=frame_cell(c.measure_index), reason=reason,
                    page_state=True, **detail)
        n += 1
    return n


def _scan_gate_enabled() -> bool:
    """`OMR_DIRECTION_TEXT_SCAN_GATE` -- skip the word reader on a proven scan.

    **Default OFF**, and written as an ALLOW-list so a typo leaves it off:
    CLAUDE.md's "A flag's OFF test must follow its DEFAULT". Turning it on
    changes what reaches a file, and every default here is Sean's.
    """
    return os.environ.get("OMR_DIRECTION_TEXT_SCAN_GATE", "0").strip().lower() \
        in ("1", "true", "yes", "on")


def _direction_lexicon_scope(log: Log, roster: Any,
                             work_id: Optional[str] = None) -> Any:
    """ROADMAP 2.67b: the languages this work's direction words are read in.

    The composer's from the work id (a CATALOG fact, `--work-id`), the
    edition's from the instrument labels gathered so far in this document.
    ⚠️ READS `Q.MARGIN_LABEL`, so it runs after `gather_margin_labels` --
    which `gather()` already does, page by page. The labels are a reading of
    the page; they can only WIDEN the languages, never narrow them, so a
    misread label costs at most a word of noise, never a real word.
    """
    try:
        from .. import direction_lexicon as DL
    except Exception:                                         # noqa: BLE001
        return None
    # ⚠️ THE WORK ID STANDS WITHOUT A ROSTER. Mahler 5 is not in the
    # catalog's works, so `--work-id mahler--symphony-5` finds no roster --
    # and the composer is still in the id (Peters p6, 2026-10-12: the scope
    # read `unknown_work` until this fallback).
    work_id = ((roster.get("work_id") if isinstance(roster, dict)
                else getattr(roster, "work_id", None)) or work_id)
    labels = [str(r.value) for r in log.rows(
        Q.MARGIN_LABEL, R.DOCUMENT, scope=R.Scope.SELF_AND_DESCENDANTS)
        if r.value]
    return DL.scope_for(work_id, labels)


def direction_text_enabled() -> bool:
    """`OMR_DIRECTION_TEXT` -- the ONE reader of this flag (ROADMAP 2.61b);
    `pipeline.py` calls this rather than re-reading the environment. DEFAULT
    ON; a DENY-LIST (CLAUDE.md §7): a typo leaves it on.

    CONVENTION AND NOT A PREFERENCE. `test_flag_default_direction.py` walks
    the AST for `os.environ.get(<FLAG>, <default>)` compared to a literal
    word set and decides default-ON by EVALUATING THE PREDICATE ON ITS OWN
    DEFAULT -- so the equivalent `... in (off words)` spelled as a refusal
    reads to that guard as a default-OFF deny-list and is reported as "a typo
    would turn it ON". The two spellings are logically identical and only one
    is checkable. Caught by that guard on the full suite, not by review.
    """
    return os.environ.get("OMR_DIRECTION_TEXT", "1").strip().lower() not in (
        "0", "", "false", "no", "off")


def gather_direction_words(log: Log, pws: Any, cells: Sequence[Any],
                           local: Dict[int, Tuple[int, int]],
                           detections: Dict[str, List[Any]], *,
                           roster: Any = None,
                           work_id: Optional[str] = None) -> None:
    """The printed words inside a system -- `legato`, `Allegro con brio`.

    ⚠️ IT SITS BEHIND ONE OF THE THREE HARD EDGES.
    `direction_text._blank_detections` erases every detected glyph from the
    mask before it looks for words, so this cannot run before detection, and
    `gather()` orders it last for that reason.

    ⚠️⚠️ THE LEXICON GATE IS THE READER'S, IT IS LOAD-BEARING, AND NOTHING
    HERE TOUCHES IT. `direction_text.read_directions` subtracts the
    detections, refuses the curves by fill ratio, OCRs the residue with Surya
    and Tesseract and accepts only what `direction_lexicon.lookup` names. That
    gate is what stops every smudge on a scan becoming a word, and CLAUDE.md
    records it as never to be loosened. This gathers what that reader says.

    ⚠️⚠️ FOUR STATES, NOT TWO, AND THE WHOLE POINT OF THIS FUNCTION IS THAT
    THEY ARE DISTINGUISHABLE:

    | what happened | what is written |
    |---|---|
    | no OCR rung exists on this machine | `READER_UNAVAILABLE`, on the PAGE |
    | the CV found no word-shaped ink | `NO_INK`, on the PAGE |
    | a rung read a crop and returned nothing | `NO_READING`, on the CANDIDATE |
    | a rung read it and the lexicon refused | `NOT_IN_LEXICON`, on the CANDIDATE |
    | the lexicon accepted it | an OBSERVATION, on the CANDIDATE |

    The first two look identical in the legacy output and in every figure
    derived from it -- a machine with no `.venv-surya` and no Tesseract reads
    zero directions on every page, exactly as a page with no directions
    printed on it does. `read_directions` says so in its own docstring ("the
    only way to tell a page with no text from a reader that could not run")
    and returns the counts to say it with; nothing consumed them. A GATHER
    that recorded the zero and not the reason would be the fallback converting
    *cannot tell* into a definite answer -- into "this page prints no words" --
    which CLAUDE.md names as never the safe default. So the reason is written
    down, the consumer refuses on it, and a `None` is never spelled as a fact.

    ⚠️ THE CANDIDATES ARE GATHERED SEPARATELY FROM THE READINGS, AND THAT
    COSTS A SECOND CV PASS, DELIBERATELY. `read_directions` returns only the
    words the lexicon ACCEPTED; the ink it refused has no position in that
    return, so a refusal could only be filed on the page as a count. Calling
    `find_candidates` -- which is pure CV, no OCR, no subprocess, and is split
    out of the reader precisely so its recall can be measured on its own --
    gives every refusal a subject of its own. The denominator is the number
    this family's reach is measured in: a word the CV never proposes is a word
    no reader can find, and that is a different failure from one the OCR got
    wrong.

    ⚠️ NO OWNERSHIP QUESTION IS ASKED HERE, unlike the dynamic letters.
    `_bands_for_page` splits the gap between two systems at its midpoint and
    gives the whole within-system gap to the upper staff, so it "guarantees
    that no word is ever offered to two staves" -- the ownership answer is
    geometric and already made, in page pixels, before any cell padding is
    involved. A letter needs `Q.GLYPH_OWNER` because it arrives through a
    per-measure cell whose padding reaches into the neighbour; a direction
    word never does.
    """
    p = pws.page.page_index if hasattr(pws.page, "page_index") else 0
    page_sub = R.page(p)

    try:
        from .. import direction_text as DT
    except Exception as exc:                                  # noqa: BLE001
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.READER_UNAVAILABLE,
                    error=type(exc).__name__, note=str(exc)[:200])
        _direction_cells_abstain(log, cells, local,
                                 ABSTAIN.READER_UNAVAILABLE,
                                 note="direction_text did not import")
        return

    # ⚠️ A DEFAULT-ON FLAG, READ AS A DENY-LIST, so a typo leaves the reader ON
    # rather than silently blinding the page. See CLAUDE.md, "A flag's OFF test
    # must follow its DEFAULT".
    # ⚠️⚠️ AND THE PREDICATE IS THE *ON* TEST, NOT THE OFF TEST, WHICH IS A
    if not direction_text_enabled():
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="OMR_DIRECTION_TEXT is off")
        _direction_cells_abstain(log, cells, local, ABSTAIN.OUT_OF_SCOPE,
                                 note="OMR_DIRECTION_TEXT is off")
        return

    # ⚠️⚠️ THE DOMAIN GATE. On a page PROVED to be a photograph of paper this
    # reader is the most expensive thing in a staged run and returns almost
    # nothing: measured 2026-09-16 on Litolff Beethoven 5 p1-4 at **~267
    # s/page** -- against 93 s/page for the margin-label rungs it shares a
    # model with -- for **six `<words>`, all of them `cresc.` in three
    # casings**, with the exported file BYTE-IDENTICAL once those and the
    # `<direction>` wrappers they emptied are removed. ~178 seconds per word.
    # See `benchmarks/omr-surya-staged-cost-2026-09/FINDINGS.md`.
    #
    # ⚠️ IT GATES ON A POSITIVE PROOF OF SCAN, never on "not proven
    # engraved". `page_is_engraved` answers False on any doubt, so its
    # negation is also true of a hybrid, a blank page, a PDF that will not
    # open and a page with no `pdf_path` -- and skipping on those would look
    # exactly like a document that prints no words. `page_is_scanned` proves
    # its own side; the ambiguous band between them keeps the reader ON,
    # which is the direction that costs money rather than evidence.
    #
    # ⚠️ AND IT IS `OUT_OF_SCOPE`, NOT `READER_UNAVAILABLE`. The rungs are
    # installed and would run; we declined to spend them. Filing that as an
    # absent reader would say this machine cannot read directions, which is
    # false and is exactly the confusion the four-state contract exists to
    # prevent.
    #
    # ⚠️ STAGED ONLY, because that is where it was measured. `transcribe`
    # pays the same cost and is untouched: its 144 engraved edits are the
    # figure that makes this reader worth having, and nothing here re-measures
    # the legacy path.
    if _scan_gate_enabled():
        try:
            scanned = DT.page_is_scanned(pws.page)
        except Exception:                                     # noqa: BLE001
            scanned = False
        if scanned:
            log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                        frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                        note="OMR_DIRECTION_TEXT_SCAN_GATE: this page is "
                             "provably a scan, where the reader measured "
                             "~267 s/page for ~6 words",
                        gate="scan")
            _direction_cells_abstain(log, cells, local, ABSTAIN.OUT_OF_SCOPE,
                                     note="scan gate", gate="scan")
            return

    page_dict = _direction_page_dict(pws, cells, local, detections)
    page_staff_of = {v: k for k, v in local.items()}
    key_of_page_staff = {v: k for k, v in page_staff_of.items()}

    try:
        candidates = DT.find_candidates(pws, page_dict, refine_boxes=True)
        readers = DT.default_readers(pws.page)
    except Exception as exc:                                  # noqa: BLE001
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.READER_UNAVAILABLE,
                    error=type(exc).__name__, note=str(exc)[:200])
        _direction_cells_abstain(log, cells, local,
                                 ABSTAIN.READER_UNAVAILABLE,
                                 error=type(exc).__name__)
        return

    if not readers:
        # ⚠️ WRITTEN EVEN WHERE THERE ARE NO CANDIDATES, and that is the case
        # this whole branch exists for. A machine with neither `.venv-surya`
        # nor Tesseract produces the same zero on every page; without this row
        # the record would carry the zero and not the blindness.
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.READER_UNAVAILABLE,
                    note="no OCR rung available: neither .venv-surya nor "
                         "tesseract",
                    n_candidates=len(candidates))
        _direction_cells_abstain(log, cells, local,
                                 ABSTAIN.READER_UNAVAILABLE,
                                 note="no OCR rung available")
        return

    if not candidates:
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_INK,
                    note="the CV proposed no word-shaped ink in any band",
                    readers=[n for n, _f in readers])
        _direction_cells_abstain(log, cells, local, ABSTAIN.NO_INK,
                                 note="no word-shaped ink on this page")
        return

    scope = _direction_lexicon_scope(log, roster, work_id)
    try:
        found, info = DT.read_directions(pws, page_dict, readers=readers,
                                         scan_order=True,
                                         lexicon_scope=scope)
    except Exception as exc:                                  # noqa: BLE001
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.READER_UNAVAILABLE,
                    error=type(exc).__name__, note=str(exc)[:200],
                    n_candidates=len(candidates))
        _direction_cells_abstain(log, cells, local,
                                 ABSTAIN.READER_UNAVAILABLE,
                                 error=type(exc).__name__)
        return

    # ⚠️ JOINED ON THE THREE FIELDS A `DirectionText` COPIES STRAIGHT OFF ITS
    # CANDIDATE (`read_directions`: `staff_index`, `measure_index`,
    # `x_page=candidate.x_page`), never on list position. The two calls run
    # the same pure-CV function on the same inputs so the orders do agree
    # today -- but an index join would be silently wrong the day either side
    # filters, and a wrong join here attributes one word's reading to another
    # word's ink.
    # The reader may have proposed candidates the CV pass above did not (the
    # sibling windows); file against ITS list so those words have a subject.
    candidates = list(info.get("candidates") or candidates)
    accepted: Dict[Tuple[int, int, int], List[Any]] = {}
    by_candidate: Dict[int, List[Any]] = {}
    for d in found:
        accepted.setdefault(
            (int(d.staff_index), int(d.measure_index), int(d.x_page)),
            []).append(d)
        # ⚠️ ROADMAP 2.68: the reader now stamps the candidate it read each
        # word from, and the list above IS that reader's list, so the index is
        # the join. The three-field key filed ONE reading on TWO candidates
        # that share staff, bar and left x (Brahms p3 staff 12: a word's own
        # box and a sibling window, both at x 4777) -- a duplicate word.
        ci = int(getattr(d, "candidate_index", -1))
        if ci >= 0:
            by_candidate.setdefault(ci, []).append(d)

    n_read = int(info.get("n_read") or 0)
    n_obs = 0
    touched = set()
    for ci, cand in enumerate(candidates):
        key = key_of_page_staff.get(int(cand.staff_index))
        if key is None:
            continue
        g = R.glyph(p, key[0], key[1], int(cand.measure_index),
                    _DIRECTION_GLYPH_BASE + ci)
        touched.add(g.at(R.Kind.CELL).to_key())
        x0, y0, x1, y1 = (float(v) for v in cand.bbox_page)
        shared: Dict[str, Any] = {
            "bbox_page_px": [x0, y0, x1, y1],
            "x_center_page": (x0 + x1) / 2.0,
            "y_center_page": (y0 + y1) / 2.0,
            "x_page": int(cand.bbox_page[0]),
            "placement": cand.placement,
            "n_components": int(cand.n_components),
            "page_staff_index": int(cand.staff_index),
        }
        hits = (by_candidate.get(ci) if by_candidate else accepted.get(
            (int(cand.staff_index), int(cand.measure_index),
             int(cand.x_page))))
        if not hits:
            # ⚠️ TWO REFUSALS, NOT ONE, AND THE RECORD CANNOT TELL THEM APART
            # PER CANDIDATE. `read_directions` reports `n_read` and `rejected`
            # for the PAGE, not per crop, so the split between "the decoder
            # returned nothing" and "the lexicon refused what it returned" is
            # a page-level fact here. Rather than guess which one this crop
            # was, every unaccepted candidate is filed `NO_READING` -- the
            # weaker claim -- with the page's own counts beside it so the
            # split is recoverable. ⚠️ Making it per-crop means returning the
            # per-rung readings from `read_directions`, which is a change to
            # the reader and is NOT a wiring change.
            log.abstain(g, Q.DIRECTION_WORD, reader=READERS.SURYA,
                        frame=FRAME_PAGE, reason=ABSTAIN.NO_READING,
                        page_n_read=n_read,
                        page_n_candidates=len(candidates),
                        page_n_rejected_by_lexicon=len(
                            info.get("rejected") or ()),
                        split_is_page_level=True, **shared)
            continue
        for d in hits:
            reader = (READERS.TESSERACT if d.reader == "tesseract"
                      else READERS.SURYA)
            log.observe(g, Q.DIRECTION_WORD, d.text, reader=reader,
                        frame=FRAME_PAGE,
                        category=d.category, terms=list(d.terms),
                        winning_reader=d.reader,
                        dynamics=list(d.dynamics),
                        # ROADMAP 2.67b: what the terms library added, and
                        # the languages this work's words were read in.
                        library=list(getattr(d, "library", ()) or ()),
                        other_language=bool(getattr(d, "other_language",
                                                    False)),
                        lexicon_scope=(scope.to_json() if scope is not None
                                       else None),
                        # ONE marking: the word and the dynamic it includes.
                        # The glyph subjects below are the detector's own
                        # dynamic boxes, exported once, inside this marking.
                        includes_dynamic_glyphs=[
                            R.glyph(p, Subject.from_key(ck).system,
                                    Subject.from_key(ck).staff,
                                    Subject.from_key(ck).cell, int(di)).to_key()
                            for ck, di, _b in d.dynamic_links if ck],
                        readers_run=[n for n, _f in readers],
                        # ⚠️ RECORDED, NOT RE-ASKED. Where the two rungs read
                        # one crop differently the reader takes Surya by a
                        # documented precedence and counts the disagreement.
                        # That arbitration stays inside the reader in a wiring
                        # pass; moving the two rungs into the record as two
                        # independent rows is the obvious next step and is
                        # deliberately not taken here.
                        page_conflicts=len(info.get("conflicts") or ()),
                        **shared)
            n_obs += 1

    # ⚠️ EVERY CELL ENDS WITH EXACTLY ONE STATE, so `coverage()`'s `abstained`
    # dict is a partition over the page's bars rather than a selection. A bar
    # the CV proposed no ink in is a MEASUREMENT ("the rungs ran, this bar
    # prints no word") and is not the same fact as a bar nobody looked at.
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        if sub.to_key() in touched:
            continue
        log.abstain(sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=frame_cell(c.measure_index), reason=ABSTAIN.NO_INK,
                    readers=[n for n, _f in readers])

    if n_obs == 0:
        # ⚠️ A PAGE the rungs RAN over and accepted nothing on is a
        # MEASUREMENT, not an absence -- the `0 accepted of N candidates`
        # half of the reading. A consumer that cannot tell it from "no rung
        # ran" cannot tell silence from blindness, which is the distinction
        # this whole function is built around.
        log.abstain(page_sub, Q.DIRECTION_WORD, reader=READERS.SURYA,
                    frame=FRAME_PAGE, reason=ABSTAIN.NOT_IN_LEXICON,
                    n_candidates=len(candidates), n_read=n_read,
                    readers=[n for n, _f in readers])


#: ⚠️⚠️ DEFAULT **ON** SINCE 2026-09-22, AND IT IS SEAN'S OWN INSTRUCTION:
#: *"if a page is engraved or a scan along with the publisher info and year --
#: whatever we have -- should be gathered in the first stage."* It shipped OFF
#: on 2026-09-17 under the `Q.INK` discipline (a producer and its first
#: consumer landing together makes the reach measurement circular); the
#: consumer now exists behind its OWN flag, so the two evidential weights are
#: separate -- the INFER lane's lesson, where one switch over two rules of
#: unequal evidence held the verified one back for four days.
#:
#: ⚠️ THE OFF TEST IS A **DENY-LIST** BECAUSE THE DEFAULT IS ON. CLAUDE.md's
#: *"A flag's OFF test must follow its DEFAULT"*, under which five shipped
#: flags had it backwards: under a default-ON flag an allow-list would let an
#: empty value or a typo silently RESTORE the old silence.
#: `test_flag_default_direction.py` derives this and will check it.
DOCUMENT_IDENTITY_ENV = "OMR_DOCUMENT_IDENTITY"


def _document_identity_enabled() -> bool:
    return os.environ.get(DOCUMENT_IDENTITY_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


def gather_document_identity(log: Log, pdf_path: Any) -> None:
    """WHICH PRINTING THIS IS, on the DOCUMENT.

    ⚠️⚠️ **THE CONDITIONING VARIABLE HAD NO PRODUCER.** `grep publisher
    tools/omr/staged/gather.py` returned exactly ONE COMMENT before this rung,
    so a record could not say which plate it came from -- while the catalog
    that knows has been COMMITTED all along, holds 234 editions, and the
    library filename itself carries the IMSLP id. That is the *value existed
    and nothing read it* shape from the producer side, and it is the same
    class of fault `no_producer.py` was written to catch: `pdf_path` reaches
    `gather()` already and was used only to rasterise.

    ⚠️ `source_kind` IS THE REASON IT IS ADMISSIBLE. These facts come from
    IMSLP's work page through the catalog, NOT from reading the plate, so they
    do not fall silent when the raster is bad -- the property this repo
    requires of any second witness, and why the catalog's `editions` tier (an
    OMR output of the same raster) would not be usable here.

    ⚠️ IT DECIDES NOTHING AND NOTHING READS IT YET. It is producer-only, the
    discipline `Q.INK` shipped under: a fact and its first consumer landing
    together makes the reach measurement circular.
    """
    if not _document_identity_enabled():
        # ⚠️ SILENT, and that is the point of a default-OFF flag: writing an
        # abstention would change every record in the tree, which is the
        # "perturbs upstream by existing" hazard. Flag-off must be
        # byte-identical to a tree without this rung.
        return
    # ⚠️⚠️ ONCE PER DOCUMENT, AND `gather()` CALLS THIS ONCE PER PAGE. Measured
    # rather than assumed: a four-page run filed FOUR identical
    # `document_identity` rows on the one DOCUMENT subject, so a consumer
    # counting rows would over-count the plate fourfold. The guard lives in the
    # function rather than at the call site so it holds wherever this is
    # called from, and it CAN fire -- which is the test this repo requires of
    # an idempotence guard, having once deleted one whose rule could not.
    # ⚠️ `gather_external` has the same shape and files its dossier/roster rows
    # per page too; that is PRE-EXISTING and is not changed here.
    # ⚠️ BOTH ROW TYPES, and the test caught this: a first call on an UNHELD
    # pdf writes an ABSTENTION, which `rows()` does not return, so a guard
    # asking only for observations let four abstentions through -- the
    # ABSENT/DECLINED distinction biting the guard that was written to respect
    # it.
    if log.rows(Q.DOCUMENT_IDENTITY, R.DOCUMENT) \
            or log.refusals(Q.DOCUMENT_IDENTITY, R.DOCUMENT):
        return
    if not pdf_path:
        log.abstain(R.DOCUMENT, Q.DOCUMENT_IDENTITY, reader=READERS.CATALOG,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no pdf_path supplied to gather()")
        return
    try:
        from tools.omr.positional_store import edition_for_pdf
        facts = edition_for_pdf(pdf_path)
    except Exception as exc:     # catalog absent/unreadable  # noqa: BLE001
        facts = {}
        # ⚠️ ROADMAP 2.60: a catalog that THREW cannot say the PDF is not in
        # it. `NOT_IN_CATALOG` is a reading of the catalog; this is none.
        log.abstain(R.DOCUMENT, Q.DOCUMENT_IDENTITY, reader=READERS.CATALOG,
                    frame=FRAME_PAGE, reason=ABSTAIN.READER_UNAVAILABLE,
                    error=type(exc).__name__, note=str(exc)[:200])
        return
    if not facts:
        # ⚠️ A PDF THE STORE DOES NOT HOLD ABSTAINS. It is NOT defaulted to
        # "unknown publisher": a fallback that converts *cannot tell* into a
        # definite answer is the failure this file records at four sites.
        log.abstain(R.DOCUMENT, Q.DOCUMENT_IDENTITY, reader=READERS.CATALOG,
                    frame=FRAME_PAGE, reason=ABSTAIN.NOT_IN_CATALOG,
                    note="no catalog edition matches %s"
                         % os.path.basename(str(pdf_path)))
        return
    # ⚠️⚠️ `image_type` IS IMSLP'S CROWD-SOURCED LABEL AND IT IS FILED AS ONE.
    # The MEASURED engraved/scan verdict is a SEPARATE quantity from a
    # SEPARATE reader (`gather_input_domain` below) and neither overwrites the
    # other, which is the `Q.INK` discipline for `ink_detector_coverage`: a
    # disagreement between two witnesses is a fact worth having.
    #
    # ⚠️ MEASURED 2026-09-22 OVER ALL 289 COMMITTED EDITIONS, AND THE LABEL IS
    # NOT WRONG -- IT IS ABSENT. Where it exists the two agree 279 of 279
    # (272/272 `Normal Scan` measure scanned, 7/7 `Typeset` measure engraved);
    # the 10 editions carrying NO label split 7 scanned / 3 engraved, and all
    # three engraved ones are locally-made typesets rather than IMSLP scans.
    # So *"the catalog claims only 7 engraved, which cannot be right"* is
    # REFUTED: the library really is almost all scans, because it is almost
    # all IMSLP. `benchmarks/omr-document-identity-2026-09/FINDINGS.md`.
    log.observe(R.DOCUMENT, Q.DOCUMENT_IDENTITY,
                facts.get("publisher"), reader=READERS.CATALOG,
                frame=FRAME_PAGE, tier="catalog",
                edition_path=facts.get("path"),
                publisher=facts.get("publisher"),
                # ⚠️ SEAN ASKED FOR THE YEAR BY NAME. Present on 195 of 289.
                publisher_year=facts.get("publisher_year"),
                # A plate number identifies a PRINTING more sharply than a
                # house: Litolff 2765-2773 is one series across the whole
                # Beethoven cycle. Present on 177 of 289.
                plate=facts.get("plate"),
                work_id=facts.get("work_id"),
                composer=facts.get("composer"),
                image_type=facts.get("image_type"),
                # The only field present on all 289, and the one that says
                # whether the free margin-label rung can read anything here.
                has_text_layer=facts.get("has_text_layer"),
                imslp_id=facts.get("imslp_id"),
                source_kind="catalog")


def gather_input_domain(log: Log, pdf_path: Any,
                        page_indices: Any = None, *,
                        classification: Any = None) -> None:
    """SCANNED or ENGRAVED, MEASURED off the PDF's own container.

    `classification` (roadmap 3.2): a caller who already classified this
    document -- weight routing must, since it picks a checkpoint BEFORE
    `gather()` runs at all -- passes the `DomainClassification` it already
    computed so this files the SAME verdict rather than a second,
    independently re-run one. `prefer one classification, filed once` is the
    explicit brief; without this, a `--route-weights` run would classify the
    document twice, and a bug that made the two calls disagree would be
    invisible (the routed weights and the recorded `Q.INPUT_DOMAIN` could
    silently name different domains). Passing `None` (every call site before
    3.2) is unchanged: classify here, as before.

    ⚠️⚠️ **IT IS A SEPARATE QUANTITY FROM `Q.DOCUMENT_IDENTITY` AND THE
    MEASUREMENT IS WHY, NOT THE TAXONOMY.** The catalog answers by BASENAME
    out of the committed score library, and the engraved fixture the
    key-signature failure is measured on is a RENDER -- a build product under
    `benchmarks/`, in no catalog -- so `gather_document_identity` abstains
    `not_in_catalog` on it. A domain filed as a FIELD of that row would have a
    reach of ZERO on the one input where the rule it conditions is proven.
    Measured 2026-09-22: that fixture classifies `engraved` on all 3 pages
    (raster coverage 0.000, 1188-1655 drawings) while the catalog holds
    nothing about it at all.

    ⚠️ `source_kind: "container"` IS A FOURTH KIND, NAMED RATHER THAN
    BORROWED. It is not `catalog` (no external authority speaks here), not
    `encoding`, and emphatically not `page` -- which means *an OMR output of
    the same raster* and is refused as a second witness because it falls
    silent exactly when the reading it would arbitrate does. This counts
    vector drawing operations against full-page raster coverage, so a bad scan
    is still unambiguously a raster: it has `catalog`'s independence from
    print quality without `catalog`'s dependence on somebody having catalogued
    the file.

    ⚠️ IT ABSTAINS ON DOUBT AND THE ABSTENTION HAS ITS OWN WORD.
    `input_domain`'s two populations have an EMPTY gap over 147 probed pages
    (0 drawings / 0.95+ coverage against 428-2058 drawings / 0.000), and a
    page with neither -- a blank leaf, a text-only title page -- returns
    `unknown`. That is `ABSTAIN.NO_DOMAIN_SIGNAL`, not `AMBIGUOUS`: the reader
    is doing what it was built to do, and a consumer that could not tell those
    apart would read a cover sheet as a close call.

    ⚠️ IT CLASSIFIES THE PAGES THIS RUN IS READING, not a fixed prefix, and
    records how many it probed. `classify_pdf_domain`'s own document rule is
    ANY-SCAN-WINS, so probing more pages can only ever move the verdict toward
    `scanned` -- the asymmetry matching the measured cost of misrouting.
    """
    if not _document_identity_enabled():
        return
    if log.rows(Q.INPUT_DOMAIN, R.DOCUMENT) \
            or log.refusals(Q.INPUT_DOMAIN, R.DOCUMENT):
        return
    if not pdf_path:
        log.abstain(R.DOCUMENT, Q.INPUT_DOMAIN, reader=READERS.CONTAINER,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no pdf_path supplied to gather()")
        return
    try:
        from tools.omr.input_domain import SCANNED, ENGRAVED
        if classification is not None:
            cls = classification
        else:
            from tools.omr.input_domain import classify_pdf_domain
            cls = classify_pdf_domain(pdf_path, page_indices)
    except Exception as exc:   # pragma: no cover - PyMuPDF absent/unreadable
        log.abstain(R.DOCUMENT, Q.INPUT_DOMAIN, reader=READERS.CONTAINER,
                    frame=FRAME_PAGE, reason=ABSTAIN.READER_UNAVAILABLE,
                    note="could not classify: %s" % exc)
        return

    detail = {
        "pages_probed": [p.page_index for p in cls.pages],
        "page_verdicts": [p.verdict for p in cls.pages],
        "max_raster_coverage": round(
            max((p.total_raster_coverage for p in cls.pages), default=0.0), 4),
        "max_drawings": max((p.n_drawings for p in cls.pages), default=-1),
        "ms": round(cls.ms, 1),
        "source_kind": "container",
    }
    if cls.verdict not in (SCANNED, ENGRAVED):
        # ⚠️ NOT DEFAULTED TO `scanned`. A fallback that converts *cannot
        # tell* into a definite answer is the failure this file records at
        # four sites, and here it would hand the key-signature consumer a
        # domain nobody measured.
        log.abstain(R.DOCUMENT, Q.INPUT_DOMAIN, reader=READERS.CONTAINER,
                    frame=FRAME_PAGE, reason=ABSTAIN.NO_DOMAIN_SIGNAL,
                    note=cls.reason or "neither raster-dominant nor "
                                       "drawing-rich on any page probed",
                    **detail)
        return
    log.observe(R.DOCUMENT, Q.INPUT_DOMAIN, cls.verdict,
                reader=READERS.CONTAINER, frame=FRAME_PAGE,
                tier="container", **detail)


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
        # ⚠️ A PLAIN DICT, NOT THE `WorkRoster` OBJECT, and the record is why.
        # `staged/__main__.py` serialises with `default=str`, so a frozen
        # dataclass reaches the file as its own `repr()` — a value a reader
        # can look at and a consumer cannot parse. A quantity that survives
        # the round trip only as prose is one step from being unread.
        #
        # ⚠️ `source_kind` TRAVELS WITH IT AND IS LOAD-BEARING. `work_roster`
        # already refuses anything that is not `catalog`, but a consumer must
        # be able to see the tier on the ROW: the `editions` tier is `page`,
        # an OMR output of the same raster, and the whole reason a roster is
        # admissible evidence here is that it does NOT fall silent when the
        # scan is bad. Recording it is what lets a later reader check that.
        value = {
            "work_id": getattr(roster, "work_id", None),
            "instruments": sorted(getattr(roster, "instruments", ()) or ()),
            "families": sorted(getattr(roster, "families", ()) or ()),
            "complete": bool(getattr(roster, "complete", False)),
            "source_kind": getattr(roster, "source_kind", None),
        } if not isinstance(roster, dict) else dict(roster)
        row = log.observe(R.DOCUMENT, Q.ROSTER_ENTRY, value,
                          reader=READERS.CATALOG, frame=FRAME_PAGE,
                          tier="roster",
                          n_instruments=len(value["instruments"]),
                          n_families=len(value["families"]))
        sources["roster"] = row.id
    return sources


def gather_movements(log: Log, movements: Any) -> None:
    """ROADMAP 4.2: the `--movements` spec, filed as `Q.MOVEMENT_SPANS` on
    the DOCUMENT -- once, however many pages this run holds.

    `movements` is already a tuple of parsed spans
    (`tools.omr.staged.movements.parse_movement_spec`'s own shape) by the
    time it reaches here; this function does no parsing of its own. `None`
    (no `--movements` given) abstains rather than filing an empty list, the
    same `ABSTAIN.OUT_OF_SCOPE` word `gather_external` uses for "no dossier
    supplied" -- a record with nothing here reads as the single-movement
    default everywhere `tools.omr.staged.movements.same_movement` is asked.

    ⚠️ ONCE PER DOCUMENT, THE SAME GUARD `gather_document_identity` USES.
    `gather()` calls this once per page in the batch; without the guard a
    four-page run would file four identical rows on the one DOCUMENT
    subject.
    """
    if log.rows(Q.MOVEMENT_SPANS, R.DOCUMENT) \
            or log.refusals(Q.MOVEMENT_SPANS, R.DOCUMENT):
        return
    if not movements:
        log.abstain(R.DOCUMENT, Q.MOVEMENT_SPANS, reader=READERS.CLI,
                    frame=FRAME_PAGE, reason=ABSTAIN.OUT_OF_SCOPE,
                    note="no --movements supplied")
        return
    spans = list(movements)
    log.observe(R.DOCUMENT, Q.MOVEMENT_SPANS, spans, reader=READERS.CLI,
               frame=FRAME_PAGE, tier="movements")


# ─────────────────────────────────────────────────────────────────────────────
# The stage
# ─────────────────────────────────────────────────────────────────────────────


def _run_page_indices(pws_and_cells: Sequence[Tuple[Any, Sequence[Any]]]):
    """Which PDF pages this gather is reading, or None if they cannot be told.

    ⚠️ `None` FALLS BACK TO THE CLASSIFIER'S OWN DEFAULT PREFIX rather than to
    an empty list, because an empty `page_indices` classifies NOTHING and
    returns `unknown` -- a clean, believable abstention that would mean *this
    document has no domain* when it means *we could not name its pages*.
    """
    idx = []
    for pws, _cells in pws_and_cells:
        page = getattr(pws, "page", None)
        i = getattr(page, "page_index", None)
        if isinstance(i, int):
            idx.append(i)
    return sorted(set(idx)) or None


def gather(pws_and_cells: Sequence[Tuple[Any, Sequence[Any]]], *,
           detector: Any = None, conf_threshold: float = 0.25,
           imgsz: Optional[int] = None, dossier: Any = None,
           roster: Any = None, pdf_path: Any = None,
           work_id: Optional[str] = None,
           surya_fallback: bool = False, ocr_fallback: bool = False,
           ink_component_rows: bool = False,
           input_domain_classification: Any = None,
           movements: Any = None,
           log: Optional[Log] = None,
           progress: bool = False) -> Log:
    """Run every reader over already-prepared pages and return a frozen Log.

    ⚠️ THE RULE FOR ORDER IS ONE SENTENCE: a reader runs after every reader
    whose rows it reads (`log.rows(Q.X, ...)`) and after every reader that
    mutates state it walks (`detections`). GATHER decides nothing, so
    anything else about the order is kinship, not dependency, and a step
    that reads only the raster and `detections` could sit anywhere after
    detection without changing a byte of the record. ⚠️ `log.rows()` on a
    quantity nobody has filed yet returns EMPTY rather than raising, so a
    reader placed above its input fails SILENTLY -- the one misorder that
    bit (the rescue, below) now raises `GatherOrderError` instead.

    The forced edges, as of 2026-10-06 (A-GATHER-1 said THREE until this
    date; the count is derivable -- every `Q.X` inside a `log.rows(...)`
    call in a reader or its helpers -- and should be re-derived, not
    inherited):

      geometry        -> everything (a cell is DEFINED by `staff.line_ys`)
      detection       -> everything after it (`detections`)
      rest search     -> lowconf rescue           (`Q.EMPTY_BAR_REST_SEARCH`)
      lowconf rescue  -> every `detections` walker (mutates it in place)
      recentre        -> ownership evidence, CV lines, notehead ink
                                                  (`Q.NOTEHEAD_RECENTRE`)
      notehead pos.   -> far-head ledgers         (`Q.NOTEHEAD_STAFF_POSITION`)
      CV lines        -> stacked-head fit, stem cross-ink
                                                  (`Q.STEM`, `Q.BEAM_STROKE`)
      stem cross-ink  -> far-head ledgers         (`Q.NOTEHEAD_STEM_CROSS_INK`)
      geometry        -> key signature            (`Q.CELL_STAFF_SPACE`)
      detection       -> direction words (erases every detection from the mask)
      hairpins, direction words -> family positions (promoted off their rows)

    ⚠️ What is NOT an edge, because nothing in GATHER reads it: the CLEF.
    Notehead positions are clef-free by design (the point of
    `gather_notehead_positions`), and the key-signature reader fits every
    clef's slot table rather than asking. The header readers' consumers are
    all in ADJUDICATE; moving them earlier would reorder the record and
    change nothing. ⚠️ A further edge found during the build is an
    ADJUDICATION edge, not a gathering one: the meter vote consumes
    committed durations. See ASSUMPTIONS.md A-DUR-1.

    `ink_component_rows` forwards to `gather_ink` (roadmap 1.1): False (the
    default) files one aggregated `Q.INK` row per cell; True reproduces the
    pre-1.1 one-row-per-component form, which `positional_store.py` needs.

    `input_domain_classification` (roadmap 3.2): a caller that already
    classified this document for weight routing passes its
    `DomainClassification` through here so `gather_input_domain` files that
    SAME verdict instead of reclassifying -- see that function's docstring.
    """
    # ⚠️ IMPORTED HERE, NOT AT MODULE LEVEL, AND THE REASON IS A CYCLE RATHER
    # THAN A COST. `positions` reads THIS module's routing predicates --
    # `_ARC_CLASSES`, `_REST_PREFIX`, `_ornament_kind`, `_band_offset_spaces`
    # -- because a second spelling of "which family is this glyph" would file
    # a mark under the wrong family and attribute every position row for it to
    # ink it does not measure. Importing it back at module level would close
    # that cycle at import time. Deferred, it resolves cleanly, and the
    # direction of the dependency stays the honest one: positions depend on
    # gathering, not the other way round.
    from . import positions as _positions

    log = log if log is not None else Log()
    far_head_state = FarHeadState()          # ROADMAP 2.56: the size pool

    for pws, cells in pws_and_cells:
        # ⚠️ EXTERNAL FACTS FIRST. Not an ordering preference: anything
        # DERIVED from a dossier or roster must be able to name that row in
        # its `derived_from`, and `Log.observe` refuses a `derived_from` that
        # is not already in the log -- deliberately, because a dangling
        # reference would silently restore the double-counting this ordering
        # exists to prevent.
        sources = gather_external(log, pws, dossier=dossier, roster=roster)
        gather_document_identity(log, pdf_path)
        # ⚠️ ROADMAP 4.2. Once-per-document, guarded the same way
        # `gather_document_identity` is -- see `gather_movements`.
        gather_movements(log, movements)
        # ⚠️ THE PAGES THIS RUN IS READING, derived from the batch rather than
        # from the first 12 of the file: a gather of pages 60-63 of an 88-page
        # scan must not be classified on its cover sheet. Both calls are
        # once-per-DOCUMENT and guard themselves, so passing the whole list on
        # every page is correct and costs nothing after the first.
        gather_input_domain(log, pdf_path, _run_page_indices(pws_and_cells),
                           classification=input_domain_classification)
        local = gather_geometry(log, pws)
        gather_systems(log, pws, getattr(pws, "used_bridging", True))
        gather_measures(log, pws, cells, local)
        # ⚠️ ROADMAP 2.13. Pure geometry + OCR, no detections needed --
        # placed here rather than beside `gather_margin_labels` because it
        # needs nothing detection produces and there is no reason to make it
        # wait. 2.13b: Surya first unless the run said `--no-surya`.
        gather_printed_bar_numbers(log, pws, surya=surya_fallback)
        # ⚠️ ROADMAP 2.85. Raster + the cut cells only, no detections. The
        # numeral reader READS `Q.VOLTA_BRACKET`'s rows, so it is after the
        # bracket reader -- a forced edge.
        gather_volta_brackets(log, pws)
        gather_volta_numerals(log, pws, surya_fallback=surya_fallback)
        gather_repeat_dots(log, pws, cells, local)

        detections = gather_detections(
            log, cells, local, detector=detector,
            conf_threshold=conf_threshold, imgsz=imgsz, progress=progress)

        # ⚠️ ROADMAP 2.52, IMMEDIATELY AFTER DETECTION (it needs this cell's
        # own boxes to tell whether it has NO notehead/rest box at all) AND
        # BEFORE THE RESCUE BELOW, which reads its row. This is the order
        # Sean gave (DECISIONS 2026-10-01: look for the whole rest in the
        # middle of the bar FIRST; only a bar that has none is rescued).
        # Until 2026-10-06 this call sat beside `gather_ink` and the rescue
        # re-ran it on a throwaway `Log` to get an answer it could not yet
        # read off the record -- the search ran twice on every candidate bar
        # and the rescue read a scratch copy. It reads the SAME erased raster
        # `gather_ink`/`gather_notehead_ink` read (`READERS.CV_REST_SEARCH`
        # says so); its position here is a dependency, not a kinship.
        gather_empty_bar_rest_search(log, cells, local, detections,
                                     progress=progress)

        # ⚠️ ROADMAP 2.55, AFTER THE REST SEARCH (it reads `Q.EMPTY_BAR_REST_
        # SEARCH` off THIS log and refuses to run where the search has not
        # filed -- see the function) AND BEFORE EVERY ONE OF `detections`'s
        # OTHER CONSUMERS: a rescued box is appended to THIS cell's own
        # `detections` list in place, so every reader below that walks it by
        # index -- notehead position, ownership evidence, rhythm marks, the
        # ink/ledger/stem/stacked-head readers -- sees it exactly as it would
        # see any production-floor box. A rescued bar therefore carries BOTH
        # its `found=False` search row and its rescued boxes: the record says
        # the search looked and did not find a whole rest, then the rescue
        # found heads. `adjudicate_empty_bar_whole_rest` abstains on the
        # former (additive, never a gate), so the two do not contest.
        gather_lowconf_rescue(log, cells, local, detections,
                              detector=detector, imgsz=imgsz,
                              progress=progress)
        # ⚠️ ROADMAP 2.138 (`OMR_WEDGE_RESCUE`, default ON since 2026-10-15): AFTER the 2.53 rescue (a rescued head can be the witness) and BEFORE every
        # `detections` walker, for the same reason: a rescued wedge is appended in place so the dot-role / articulation readers see it.
        if wedge_rescue_enabled():
            gather_wedge_rescue(log, cells, local, detections,
                                detector=detector, imgsz=imgsz, progress=progress)

        # ⚠️ ROADMAP 2.172 (flag `OMR_DETECTOR_VIEWS`, default OFF): other-size, phase-median views of the same cell; AFTER both rescues, BEFORE every
        # `detections` walker, for the rescue's reason: a kept view box is appended in place so the dot-role / flag / head readers see it.
        from . import detector_views as _DV
        if detector is not None and _DV.enabled():
            gather_detector_views(log, cells, local, detections, detector=detector, progress=progress)

        # ROADMAP 2.179 (flag `OMR_STEM_END_HEADS`, default ON): a head looked for again at the end of a stem that carries none. AFTER the
        # views (a view's box counts as seen), BEFORE every `detections` walker, for the rescue's reason: a kept box is appended in place.
        from . import stem_end_heads as _SEH
        if detector is not None and _SEH.enabled():
            gather_stem_end_heads(log, cells, local, detections, detector=detector, imgsz=imgsz, progress=progress)

        # ⚠️ ROADMAP 2.114 (flag `OMR_SECOND_HOLLOW_DETECTOR`, default OFF). After the rescue, BEFORE every reader that walks `detections`.
        # No parameter: the flag alone builds the detector (`second_hollow.default_detector`), so the CLI, the web app and the tests
        # reach it one way.
        from . import second_hollow as _SH
        if detector is not None and _SH.enabled():
            second_detector = _SH.default_detector()
            if second_detector is None:
                raise RuntimeError("OMR_SECOND_HOLLOW_DETECTOR is on but " + _SH.DEFAULT_WEIGHTS + " is not on this machine")
            gather_second_hollow(log, cells, local, detections, second_detector=second_detector,
                                 conf_threshold=conf_threshold, imgsz=imgsz, progress=progress)

        # ⚠️ ROADMAP 2.107, AFTER the rescue (a rescued head can be a letter's
        # ink too) and BEFORE every reader that walks `detections` by index:
        # the dynamic letters it reads are APPENDED to their cell's list, the
        # rescue's pattern, so `gather_dynamic_letters`, the ownership evidence
        # and `gather_notehead_letter_ink` see them exactly as they see a
        # production-pass letter.
        gather_letter_look(log, pws, cells, local, detections,
                           detector=detector, progress=progress)

        # ROADMAP 2.166 (flag OMR_SYSTEM_ARCS, default ON; erase OMR_SYSTEM_ARCS_ERASE, default OFF): ties/slurs read once per staff across the system on page
        # pixels, then their own stroke erased from `cell.image_no_staff`. AFTER every detector call (the box set is
        # final, so every head is protected; the detector never sees the erase), BEFORE every ink reader below.
        from . import arcs_system as _arcs_system
        _arcs_system.gather_system_arcs(log, pws, cells, local, detections, progress=progress)
        # ROADMAP 2.195 (flag OMR_STROKE_MAP, default ON; producer only, nothing reads it): the strokes of each cell, AFTER the arc erase (the
        # raster the CV readers read) and before every ink reader. Reads the raster alone, so its place is fixed by that, not by a row.
        stroke_cells = gather_stroke_map(log, cells, local, progress=progress)
        # ROADMAP 2.198 (same flag): each detector box linked to the strokes it covers. The box set is final here (every pass has run), so
        # it sits right after the map; it files rows only and decides nothing.
        gather_glyph_strokes(log, cells, local, detections, stroke_cells, progress=progress)
        # ROADMAP 2.201 (flag OMR_ACCIDENTAL_FAMILY, default ON; needs OMR_STROKE_MAP): every accidental-family box (accidental* and key*) measured as
        # ONE family -- extent along its own strokes, type from them -- before the two readers of it (`gather_accidental_positions`, the key markers).
        gather_accidental_family(cells, local, detections, stroke_cells)

        # ⚠️ ROADMAP 2.39b, IMMEDIATELY AFTER DETECTION AND BEFORE EVERY ONE
        # OF ITS FOUR CONSUMERS: the matched-window re-centre search files
        # `Q.NOTEHEAD_RECENTRE` per regular notehead, and `gather_ownership_
        # evidence` (the ledger-rung-ink and ledger-owner-density readers),
        # `gather_cv_lines` (the stem/beam notehead gate) and `gather_
        # notehead_ink` (the fill test) below all READ that row (CLAUDE.md
        # rule 6, connect never guess) rather than re-deriving it -- so this
        # position is load-bearing, not cosmetic.
        # ⚠️ ROADMAP 2.58b, BEFORE EVERY READER THAT COULD USE THE IDENTITY and
        # after the last thing that changes the box set (the rescue above).
        # A grouping over the detector's page boxes; flag-gated inside.
        gather_mark_groups(log, cells, local, detections)
        gather_notehead_recentre(log, cells, local, detections)
        # ⚠️ ROADMAP 2.73, AFTER detection and the rescue (it walks `detections`
        # by index) and BEFORE `gather_notehead_positions` and
        # `gather_notehead_ink`, which both read its row.
        gather_head_line_cut(log, cells, local, detections)
        gather_notehead_positions(log, cells, local, detections)
        # ⚠️ BESIDE THE NOTEHEAD'S POSITION AND NOT WITH THE OTHER GLYPH
        # FAMILIES, because it is the SAME measurement off the SAME cell grid
        # and its consumer's whole rule is a comparison between the two. Filed
        # apart from `gather_glyph_families` for the reason that function
        # states about the wedges: a second row from one reader on one crop is
        # one signal, and the position is a measurement OVER the mark rather
        # than a naming of it.
        gather_accidental_positions(log, cells, local, detections)
        gather_ownership_evidence(log, pws, cells, local, detections)
        gather_rhythm_marks(log, cells, local, detections)
        gather_dot_positions(log, pws, cells, local, detections)
        if mark_shape_enabled() and mark_shape_line_removed_enabled():
            gather_mark_shapes(log, pws, cells, local, detections)
        gather_glyph_families(log, detections, cells, local)
        # ⚠️ AFTER detection (the letters ARE detections, and the CV wedge
        # search blanks the point detections out of the ink first) and BEFORE
        # direction text, which subtracts every detection from the page: these
        # two read the SAME band and the ordering between them is real.
        gather_dynamic_letters(log, pws, cells, local, detections)
        gather_wedge_boxes(log, pws, cells, local, detections)
        # ⚠️ AFTER detection, and now WITH it: the notehead gate on the pair
        # rule needs this cell's heads, and `gather_detections` above already
        # holds them. The order was always right; what was missing is that
        # `gather_cv_lines` was never handed the map.
        gather_cv_lines(log, cells, local, detections)
        # ⚠️ AFTER detection, because a component's row records how much of it
        # the detections account for -- the same edge `gather_direction_words`
        # has and for the same reason. BESIDE `gather_cv_lines` because the
        # two read the SAME erased image, which `READERS.CV_INK` states so a
        # consumer cannot mistake them for independent witnesses. Off by
        # default -- see `INK_ENV`.
        gather_ink(log, cells, local, detections,
                  component_rows=ink_component_rows, progress=progress)
        # ⚠️ ROADMAP 2.80, BESIDE `gather_ink` (the SAME erased raster; reads
        # no row and no detection, so its place is kinship, not dependency).
        gather_cell_ink_pieces(log, cells, local, detections,
                               progress=progress)
        # ⚠️ ROADMAP 2.80b: reads `detections` and the erased raster only.
        gather_narrow_box_shape(log, cells, local, detections,
                                progress=progress)
        # ⚠️ ROADMAP 2.99: reads `detections` and the erased raster only.
        gather_unboxed_rest_ink(log, cells, local, detections,
                                progress=progress)
        # ⚠️ ROADMAP 2.150b (flag OMR_REST_STROKE_INTO_HEAD, default ON): same raster, rest-classed boxes only.
        gather_rest_ink_contact(log, cells, local, detections,
                                progress=progress)
        # ⚠️ ROADMAP 3.4g-3, BESIDE `gather_ink` because it reads the SAME
        # erased raster (and says so: `READERS.CV_INK`). The second witness
        # for Sean's `[C91]` -- see the function.
        gather_ledger_ink(log, cells, local, detections)
        # ⚠️ ROADMAP 2.60, beside `gather_ledger_ink` for the same reason:
        # what is inside each slur/tie box once every staff line is taken out.
        gather_arc_ink(log, pws, cells, local, detections)
        # ⚠️ ROADMAP 2.23 (ported, GATHER half, from `claude/no-ink-head-
        # 2.6h`), BESIDE `gather_ledger_ink` for the same reason: the
        # sibling witness for the notehead's OWN box rather than its rung,
        # reading `cell.image_no_staff` in common with it and `cell.binary`
        # besides.
        gather_notehead_ink(log, cells, local, detections, pws=pws)
        # (ROADMAP 2.52's `gather_empty_bar_rest_search` ran directly after
        # detection, above, since 2026-10-06 -- the rescue reads its row.)
        # ⚠️ ROADMAP 2.42, AFTER `gather_notehead_ink` AND `gather_cv_lines`:
        # the stacked-head fit reads THIS cell's own `Q.STEM` rows (already
        # filed by `gather_cv_lines`, above) and re-derives the same
        # standard-head-box ink test `gather_notehead_ink` uses (CLAUDE.md
        # rule 6 would prefer reading `Q.NOTEHEAD_INK` directly, but that
        # quantity is filed at each box's OWN centre, never at a candidate
        # SLOT a stacked fit is testing, which is a different position this
        # rule must score for itself).
        gather_stacked_head_fit(log, cells, local, detections, pws=pws)
        # ⚠️ ROADMAP 2.49, BESIDE `gather_stacked_head_fit` for the same
        # reason it sits beside `gather_notehead_ink`: the sibling witness
        # for a tremolo slash boxed as a notehead, reading the SAME erased
        # raster and this cell's own `Q.STEM` rows, already filed by
        # `gather_cv_lines` above.
        gather_notehead_stem_cross_ink(log, cells, local, detections)
        # ROADMAP 2.164 (flag OMR_ARC_TAIL_NOT_A_HEAD, default ON): head boxes at a bar's left edge, page raster.
        gather_head_oval(log, pws, cells, local, detections)
        # ⚠️ ROADMAP 2.56, AFTER `gather_notehead_positions` (a far head is
        # one whose GEOMETRY position lies outside the first space -- it reads
        # that row) and after the ownership evidence, which does not feed it.
        # A second witness under its own reader, never an overwrite.
        # ⚠️ lane-farhead-not-a-note: MOVED HERE from beside the ownership
        # evidence, because the gate reads `Q.NOTEHEAD_STEM_CROSS_INK` (2.49's
        # tremolo-slash rows) and `Q.STEM`-era evidence that did not exist yet.
        gather_far_head_ledger_positions(log, pws, cells, local, detections,
                                         far_head_state)
        # ⚠️ ROADMAP 2.58d, AFTER `gather_ownership_evidence` (it files only
        # for a contested head, read off that evidence's own rows).
        if not stems_from_strokes_retires_scans():      # ROADMAP 2.204: the head's stem is the stroke its blob touches (ADJUDICATE)
            gather_head_stem_reach(log, pws, cells, local, detections)
        # dynamic-not-a-head: AFTER the detections (it reads them) -- a head box
        # lying on a dynamic letter's box, measured against the raw raster.
        gather_notehead_letter_ink(log, pws, cells, local, detections)
        gather_detector_beams(log, detections)
        # ⚠️ ROADMAP 2.74, AFTER BOTH beam readers (it measures the strokes each
        # filed): thickness, straightness and end stems per `Q.BEAM_STROKE`.
        gather_beam_stroke_ink(log, cells, local)
        # ⚠️ ROADMAP 2.140 (flag, default OFF): beam strokes AT each stem's tip, read beside the stem.
        gather_beam_stem_levels(log, cells, local)
        gather_clef(log, cells, local, detections)
        gather_clef_locator(log, pws, cells, local, detections)
        gather_clef_seed(log, cells, local, dossier=dossier, sources=sources)
        gather_key_signature(log, pws, cells, local, detections)
        gather_meter(log, pws, cells, local, detections)
        # ⚠️ AFTER `gather_meter`, because it reads the SAME reader on a
        # DIFFERENT crop and the header reading is the one a consumer reaches
        # for first. On by default since ROADMAP 2.72 — see `METER_TEMPLATE_AT_BAR_ENV`.
        gather_meter_at_bars(log, cells, local, detections)
        # ⚠️ ROADMAP 2.29, BESIDE `gather_meter_at_bars` for the same reason
        # `_bar_head_window` is shared: a second reader of the SAME mid-bar
        # region, off by default (`METER_OCR_AT_BAR_ENV`) until priced.
        gather_meter_ocr_at_bars(log, cells, local, detections)
        # ROADMAP 2.177 (flag OMR_METER_OBJECT, default OFF): AFTER every meter reader (reads their rows); page raster.
        gather_meter_object(log, pws, cells, local, detections)
        # ROADMAP 2.181 (flag OMR_CLAIMED_REGISTER, default ON): AFTER the clef locator (reads its rows); page raster.
        gather_claimed_register(log, pws, cells, local, detections, stroke_cells=stroke_cells)
        # ROADMAP 2.183 (flag OMR_KEY_SIGNATURE_CLAIM, default ON): AFTER the register; page raster.
        gather_key_signature_claim(log, pws, cells, local, detections)
        # ROADMAP 2.187 (flag OMR_KEY_PER_SYSTEM, default ON): AFTER the key claim and the meter object; page raster.
        gather_key_object(log, pws, cells, local, detections)
        # ROADMAP 2.208 (flag OMR_CLEF_SLOT_CLAIM, default OFF): AFTER the key claim (reads its left edge); page raster.
        gather_clef_slot_claim(log, pws, cells, local, detections, stroke_cells=stroke_cells)
        gather_margin_labels(log, pws, cells, local, pdf_path=pdf_path,
                             surya_fallback=surya_fallback,
                             ocr_fallback=ocr_fallback)
        gather_direction_words(log, pws, cells, local, detections,  # hard edge: last
                               roster=roster, work_id=work_id)
        # ⚠️ AFTER EVERYTHING, AND THAT IS A HARD EDGE OF ITS OWN. Two of the
        # ten position rows are PROMOTED off rows already on the record -- the
        # CV hairpins and the direction words, whose ink no detection carries
        # -- so this must run after both of those readers. It is last rather
        # than merely after them because a position is a measurement OVER the
        # marks, and running it last means a mark gathered in future gets one
        # by being gathered rather than by someone remembering to reorder.
        # Off by default -- see `positions.POSITIONS_ENV`.
        _positions.gather_family_positions(log, pws, cells, local, detections)

    finish_far_head_ledger_positions(log, far_head_state)
    log.freeze()
    return log
