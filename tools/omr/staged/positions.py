"""A POSITION fact for every notation family — symbol-specific, by design.

    OMR_FAMILY_POSITIONS=1 python3 -m tools.omr.staged <pdf> ...

⚠️⚠️ **THE JOB, AND THE SECOND HALF OF THE INSTRUCTION IS AS LOAD-BEARING AS
THE FIRST.** Sean, 2026-09-17:

> *"send an agent out to give the families real position information — or if
> it should be symbol specific then make it so"*

So this module does **not** force one schema onto fourteen families.
`capture.py`'s table reports eleven families with `position: NONE`, and the
reason they have none is not that nobody got round to it — it is that *a
notehead's position* and *a dynamic's position* are not the same kind of
measurement, and a field wide enough to hold both would hold neither well. A
notehead's position is a STEP on the grid. A rest's is *which side of which
line it hangs from*. A meter's is *two marks, one in each half of the staff,
centred on each other*. A dynamic's is *how far below the bottom line it
stands* — it has no step at all, because it is not on the grid.

Flattening those into one number would throw away exactly what makes each one
diagnostic, which is the fault this whole architecture exists to stop.

## THE THREE CONSTRAINTS EVERY ROW HERE OBEYS

1. **STAFF-RELATIVE, or it composes with nothing.** Every value is expressed
   against *this staff's own measured lines*, so it means the same thing on
   any page, publisher or dpi. A `bbox_page_px` does not: pages differ in
   size and resolution, and `capture.py`'s `location` column grades a family
   reading `cell/page` as having a LOCATION and not a POSITION.
2. **SCORELESS.** `score=None`, like `Q.NOTEHEAD_STAFF_POSITION`. A ruler
   reading is not a guess, and recording it with a confidence invites a
   consumer to weigh it as one.
3. ⚠️⚠️ **ITS OWN QUANTITY — NEVER A FIELD ON THE SHAPE ROW.** This is the
   structural constraint and the reason a quick fix is wrong.
   `groups.correlated_groups` treats one reader's rows on one crop as **ONE
   SIGNAL**, so a position hung off the glyph's own row is absorbed into that
   glyph's detector term and stops being independent evidence.
   `Q.CLEF_POSITION` already says this in its own docstring, and the `band*`
   entries `capture.py` reports for `dynamic` and `wedge` are exactly that
   mistake already made: a staff-relative offset that EXISTS, measured, with
   no score — living as a DETAIL of a SCORED row. **Those two are PROMOTED
   here, not invented.**

## TWO FRAMES, TWO UNITS, AND THAT IS THE SYMBOL-SPECIFIC PART

  STEP frame  — staff steps off the cell's own line grid, top line `0.0`,
                bottom line `8.0`, one step = half a staff space. The same
                unit as `Q.NOTEHEAD_STAFF_POSITION`, because these marks sit
                ON the grid and a step is what the grid measures.
                Outside the staff the number keeps working and keeps meaning
                the same thing: `-3.0` is a step and a half above the top
                line.

  BAND frame  — staff SPACES below this staff's own bottom line, positive
                downwards. The same unit `_band_offset_spaces` and
                `hairpin_detection`'s `BAND_TOP_SPACES` / `BAND_BOTTOM_SPACES`
                already use. A dynamic, a hairpin and a direction word live in
                a ROW OF THE PAGE, not on the staff grid; giving one a step
                coordinate would report a `ff` at step 14, which is a number
                that composes and means nothing.

⚠️ Two units is a cost and it is paid deliberately. The alternative — one
unit for everything — is what makes a band mark's position uninterpretable.
Each row names its own frame in `frame` and its unit in `unit`, so a consumer
cannot mix them by accident.

## WHERE THE BOXES COME FROM, AND WHY IT IS NOT ONE SOURCE

**The detector-sourced families are read from the DETECTIONS, routed by the
SAME predicates `gather_glyph_families` and `gather_rhythm_marks` route by** —
imported from `gather`, never restated, so the two cannot drift. That also
makes the glyph INDEX coincide exactly: both walk `enumerate(dets)` over the
same list, so position row `glyph/p/s/t/c/7` measures the ink shape row
`glyph/p/s/t/c/7` names. `test_family_positions.py` asserts that partition
rather than assuming it.

**Two rows are read from the LOG instead, because no detection carries their
ink**: the `CV_HAIRPINS` half of `Q.WEDGE_BOX` (a classical-CV reading, not a
detection) and `Q.DIRECTION_WORD` (OCR over the ink the detections were
SUBTRACTED from). Both already carry `bbox_page_px`, which is the frame the
BAND measurement wants.

⚠️ **`Q.TUPLET_MARKER` RECORDS `x0`, `x1`, `x_center` AND NO `y` AT ALL** —
so a tuplet's vertical position is nowhere on the record, which is why this
module reads the detections rather than the log for it. That is a finding
about that row and is **reported, not silently patched**: adding `y` to a
shape row would change a row this flag is supposed to leave byte-identical.

## WHAT THIS MODULE DELIBERATELY DOES NOT DO

⚠️ **NO CONSUMER IS WIRED, AND THAT IS THE POINT.** `gather_ink` landed the
same way one day earlier and for the same reason: a producer and its first
consumer landing together makes the reach measurement circular. Every
quantity here is UNREAD and is recorded as such in `reach.KNOWN_GAPS`.

⚠️ **NO INVENTED CONSTANT.** Every discriminator below is either a pure
geometric predicate (does this box's span cross the middle line?) or a
COMPARATIVE choice with its residual recorded (which EDGE sits nearer a line?
— and how near). Nothing here thresholds a distance, because a threshold read
off one document is a constant fitted to a wish, and a threshold in GATHER is
the one decision no later stage can revisit.

⚠️ **NO CLASS NAME IS READ AS A POSITION.** `capture.py`'s `side` column
grades `above`/`below` taken off a class name as *not a ruler, and not
independent of the classification it comes from*. `measured_side` here is the
ruler, and it is recorded so that it CAN disagree with `fermataAbove`.

## THE ONE CORRELATION THIS DOES NOT ESCAPE, STATED PLAINLY

A position row carries no `derived_from`, following
`Q.NOTEHEAD_STAFF_POSITION` exactly: it is read off THIS raster, against the
staff's own lines, so by `Observation`'s own invariant it has no ancestors.
**But the BOX it measures is the detector's.** If the detector mis-localises
a glyph, its class and its position are wrong together — the grid is
independent, the localisation is not. So a consumer counting a shape row and
a position row as two independent witnesses is right about the GRID and wrong
about the BOX. This is the same one-sidedness `independent_groups` already
carries (*disjoint closures prove the ROWS differ, not that the READINGS fail
independently*), and it is UNMEASURED here.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import gather as G
from . import record as R
from .record import ABSTAIN, Log, Observation, Q, READERS, Subject

#: `OMR_FAMILY_POSITIONS` — gather one staff-relative position row per mark.
#:
#: ⚠️ AN ALLOW-LIST, because this is DEFAULT OFF. CLAUDE.md's *"A flag's OFF
#: test must follow its DEFAULT"*: under a default-OFF flag a deny-list is
#: switched ON by a typo, which is the mirror of the five shipped flags that
#: had it backwards. Only an explicit on word turns it on.
POSITIONS_ENV = "OMR_FAMILY_POSITIONS"

_ON_WORDS = ("1", "true", "yes", "on")


def positions_enabled() -> bool:
    return os.environ.get(POSITIONS_ENV, "0").strip().lower() in _ON_WORDS


# ─────────────────────────────────────────────────────────────────────────────
# The two frames
# ─────────────────────────────────────────────────────────────────────────────

#: Staff steps of the BOTTOM line, in the STEP frame. Five lines, four gaps,
#: two steps per gap. ⚠️ DERIVED FROM THE GRID, not a convention: `_cell_grid`
#: returns the mean gap halved, so the bottom line is always eight of those
#: away from the top one whatever the staff's spacing is.
BOTTOM_LINE_STEP = 8.0

#: The middle line, which is what separates a meter's two halves.
MIDDLE_LINE_STEP = 4.0

UNIT_STEP = "staff_steps_from_top_line"
UNIT_BAND = "staff_spaces_below_bottom_line"


def _steps(y: float, top_y: float, half_step: float) -> float:
    """`(y - top_y) / half_step` — the exemplar's own arithmetic, one spelling.

    ⚠️ NOT re-derived: this is `gather_notehead_positions`' expression, and
    `pitch_resolver.py:180` computes the identical thing before `:181` rounds
    it away. Keeping one spelling is what stops a second copy drifting.
    """
    return (float(y) - top_y) / half_step


def _nearest_line(step: float) -> Tuple[int, float]:
    """`(line_index, signed residual)` for the nearest of the five lines.

    Line 0 is the TOP line at step 0.0; line 4 the bottom at step 8.0. The
    residual is signed and in STEPS: positive means the ink sits below the
    line it is nearest.
    """
    idx = int(round(step / 2.0))
    idx = 0 if idx < 0 else 4 if idx > 4 else idx
    return idx, step - (idx * 2.0)


def _outside(top: float, bottom: float) -> float:
    """Signed steps the box lies OUTSIDE the staff; 0.0 if it overlaps at all.

    Negative above the top line, positive below the bottom line. ⚠️ A pure
    predicate with no tolerance: a mark that merely touches the staff reads
    0.0, and the magnitude is what a consumer thresholds — not this module.
    """
    if bottom < 0.0:
        return bottom
    if top > BOTTOM_LINE_STEP:
        return top - BOTTOM_LINE_STEP
    return 0.0


def _measured_side(top: float, bottom: float) -> str:
    """`above` / `below` / `inside`, from the RULER and never from a class name.

    ⚠️ THE WHOLE REASON THIS FIELD EXISTS. `capture.py` reports `articulation`,
    `fermata` and `ornament` with `side: cls` — the side read off the class
    name, which *fails together with the classification it is read off*. This
    is the independent witness, and it is recorded so it can CONTRADICT a
    `fermataAbove` standing under its staff.
    """
    o = _outside(top, bottom)
    return "inside" if o == 0.0 else ("above" if o < 0.0 else "below")


def _step_core(y0: float, y1: float, top_y: float,
               half_step: float) -> Dict[str, Any]:
    """The fields EVERY step-frame row carries, before its own discriminator."""
    top = _steps(min(y0, y1), top_y, half_step)
    bottom = _steps(max(y0, y1), top_y, half_step)
    centre = (top + bottom) / 2.0
    line, resid = _nearest_line(centre)
    return {
        "unit": UNIT_STEP,
        "top": top,
        "bottom": bottom,
        "height_steps": bottom - top,
        "nearest_line": line,
        "line_residual": resid,
        "steps_outside_staff": _outside(top, bottom),
        "measured_side": _measured_side(top, bottom),
        "_centre": centre,
    }


def _band_core(y0: float, y1: float, bottom_line: float,
               spacing: float) -> Optional[Dict[str, Any]]:
    """The fields every band-frame row carries. `None` where the unit is absent.

    ⚠️ `_band_offset_spaces` IS IMPORTED, not restated, for the same reason
    `_steps` mirrors the exemplar: the letters and the hairpins became
    comparable at all because they are measured in ONE frame, and a second
    spelling of that frame is how they stop being.
    """
    top = G._band_offset_spaces(min(y0, y1), bottom_line, spacing)
    bot = G._band_offset_spaces(max(y0, y1), bottom_line, spacing)
    ctr = G._band_offset_spaces((y0 + y1) / 2.0, bottom_line, spacing)
    if top is None or bot is None or ctr is None:
        return None
    return {
        "unit": UNIT_BAND,
        "top_spaces": top,
        "bottom_spaces": bot,
        "height_spaces": bot - top,
        # the window `hairpin_detection` itself searches, so a letter, a
        # hairpin and a word can be said to share one row of the page
        "in_hairpin_band": G._in_hairpin_band((y0 + y1) / 2.0,
                                              bottom_line, spacing),
        "staff_bottom_line_page": bottom_line,
        "staff_spacing_px": spacing,
        "_centre": ctr,
    }


# ─────────────────────────────────────────────────────────────────────────────
# The per-family discriminators — one paragraph of music each
# ─────────────────────────────────────────────────────────────────────────────

def _rest_discriminator(core: Dict[str, Any]) -> Dict[str, Any]:
    """WHICH SIDE OF WHICH LINE THIS REST HANGS FROM.

    ⚠️⚠️ A WHOLE REST AND A HALF REST ARE THE SAME SHAPE. Both are a filled
    rectangle half a staff space tall living in the space between the second
    and third lines from the top — and they differ ONLY in which line they
    touch: a whole rest HANGS BELOW the second line, a half rest SITS ABOVE
    the middle one. There is no shape fact that separates them, which is why
    the phantom-note census recorded that *"the census cannot tell a whole
    rest from a half rest"*, and why `OMR_WHOLE_REST_INK` — the one staged
    rule that DELETES notes — rests on a shape window plus a slot witness
    instead of on the one measurement that actually decides it.

    ⚠️ THE ATTACHMENT IS COMPARATIVE AND CARRIES NO THRESHOLD. Which edge is
    "on" a line is decided by which edge is NEARER one, with both residuals
    recorded, so a consumer can see how near and this module never has to
    invent a tolerance it measured on one document.
    """
    top, bottom = core["top"], core["bottom"]
    t_line, t_res = _nearest_line(top)
    b_line, b_res = _nearest_line(bottom)
    if abs(t_res) < abs(b_res):
        edge, line, resid, hangs = "top", t_line, t_res, "below"
    elif abs(b_res) < abs(t_res):
        edge, line, resid, hangs = "bottom", b_line, b_res, "above"
    else:
        # ⚠️ A TIE IS RECORDED AS A TIE. A rest exactly centred between two
        # lines attaches to neither, and picking one would be this module
        # deciding — which belongs downstream.
        edge, line, resid, hangs = None, None, None, None
    return {
        "attached_edge": edge,
        "attached_line": line,
        "attach_residual": resid,
        "hangs": hangs,
        "top_line": t_line, "top_residual": t_res,
        "bottom_line": b_line, "bottom_residual": b_res,
    }


def _meter_discriminator(core: Dict[str, Any]) -> Dict[str, Any]:
    """A METER IS TWO MARKS, ONE IN EACH HALF OF THE STAFF.

    ⚠️⚠️ THE MOTIVATING FAILURE. The Litolff p.62 `3/4` this project cited for
    weeks is **one barline broken into two fragments** — a stroke at the
    cell's left edge — accepted because `_meter_from_digits` asks only for
    "two stacked digits" and nothing measures what a digit's position has to
    be. A numerator stands in the upper half, a denominator in the lower, and
    the two are centred on each other; a single stroke CROSSES the middle
    line and belongs to neither half.

    `half` is a pure geometric predicate against the staff's own middle line
    and needs no constant: a box is `upper` if it lies wholly above the middle
    line, `lower` if wholly below, `spans` if it crosses. `outside` is the
    fourth answer and is not a digit either.
    """
    top, bottom = core["top"], core["bottom"]
    if core["steps_outside_staff"] != 0.0:
        half = "outside"
    elif bottom <= MIDDLE_LINE_STEP:
        half = "upper"
    elif top >= MIDDLE_LINE_STEP:
        half = "lower"
    else:
        half = "spans"
    return {
        "half": half,
        "crosses_middle_line": top < MIDDLE_LINE_STEP < bottom,
        # how much of the staff's own height this mark occupies. A digit is
        # about a quarter of it; a stroke that crosses all five lines is 1.0.
        "staff_height_fraction": (bottom - top) / BOTTOM_LINE_STEP,
    }


def _tuplet_discriminator(core: Dict[str, Any]) -> Dict[str, Any]:
    """WHERE THE DIGIT STANDS — and for a tuplet that is the ONLY question.

    ⚠️⚠️ THE CLASS SPACE CANNOT ANSWER THIS AND CLAUDE.md SAYS SO IN ITS OWN
    WORDS: one `numeral` class covers time signatures, tuplet digits,
    fingerings AND measure numbers — *"a POSITIONAL distinction, made by where
    the digit stands"*. DSv2 splits `tuplet3` from `fingering3` by exactly
    that, and reproduces the split badly on orchestral pages, which is why
    both classes are read and the positional gate is what keeps it safe.

    A tuplet digit stands OUTSIDE the staff over its beam. A time signature
    digit stands INSIDE it. A fingering sits beside its notehead. Shape cannot
    tell them apart; this can. ⚠️ `adjudicate_tuplet` fired **zero times
    across 286 runs** of the plumbing matrix, on fixtures printing explicit
    `\\tuplet 3/2`, so the reach measured below is the first number anyone has
    had for this family at all.
    """
    return {
        "over_staff": core["steps_outside_staff"] != 0.0,
        "staff_height_fraction": core["height_steps"] / BOTTOM_LINE_STEP,
    }


def _arc_discriminator(core: Dict[str, Any]) -> Dict[str, Any]:
    """THE ARC'S OWN INK — and `capture.py`'s sharpest finding is why.

    ⚠️⚠️ `adjudicate_arc_kind` DECLARES `notehead_staff_position` IN `wants`.
    That is the NOTES' positions: the right evidence for the tie/slur grammar,
    and it says NOTHING about where the CURVE is. Keyed on *"does this
    decision read a position fact"*, `slur` and `tie` graded **MEASURED** off
    somebody else's ruler, and `capture.py` had to grow a third field naming
    the family a position measures to stop reporting that. This is the arc's
    own.

    `depth_steps` is the fact worth having: a TIE is drawn shallow and close
    to the two heads it binds, a SLUR arcs clear of the notes under it. That
    is the geometric half of the `OMR_ARC_RECLASS` grammar, which today
    decides on class and step-equality alone.

    ⚠️ **CURVATURE IS NOT DERIVABLE FROM A BOX AND IS NOT CLAIMED.** Which way
    an arc opens decides whether its ENDS are the box's bottom corners or its
    top ones, and a bounding rectangle is identical either way. `opens` is
    recorded as `None` rather than guessed, and reading it needs the ink —
    which `Q.INK` now gathers and nothing yet joins.
    """
    top, bottom = core["top"], core["bottom"]
    if bottom < 0.0:
        side = "above"
    elif top > BOTTOM_LINE_STEP:
        side = "below"
    elif top < 0.0 or bottom > BOTTOM_LINE_STEP:
        side = "crosses_edge"
    else:
        side = "inside"
    return {
        "depth_steps": bottom - top,
        "arc_side": side,
        "opens": None,
        "opens_note": ("a bounding box is identical for an arc opening up "
                       "and one opening down; reading it needs the ink"),
    }


def _mark_discriminator(core: Dict[str, Any]) -> Dict[str, Any]:
    """An articulation / fermata / ornament: the ruler beside the class name.

    ⚠️ These three grade `side: cls` in `capture.py` — above/below taken off
    the class NAME. `_artic_side` reads a suffix and `gather_glyph_families`
    records it honestly as what it is, but a suffix is not a witness: a
    mis-classified glyph carries a confidently wrong side. `measured_side` in
    the core is the independent reading, and the only thing this adds is how
    FAR, because *how far outside the staff* is what separates a mark attached
    to a notehead from one standing clear of the system.

    ⚠️ It does NOT record whether the two agree. That comparison is a
    decision — it has a right to abstain and a right to say which is wrong —
    and decisions do not belong in GATHER.
    """
    return {"steps_clear_of_staff": abs(core["steps_outside_staff"])}


# ─────────────────────────────────────────────────────────────────────────────
# Emission
# ─────────────────────────────────────────────────────────────────────────────

def _observe_step(log: Log, subject: Subject, quantity: str, frame: str,
                  core: Dict[str, Any], extra: Dict[str, Any],
                  **more: Any) -> Observation:
    detail = {k: v for k, v in core.items() if k != "_centre"}
    detail.update(extra)
    detail.update(more)
    # ⚠️ SCORELESS AND WITH NO `derived_from`. See the module docstring: the
    # grid is read off this raster so the row has no ancestors, and the one
    # correlation it does NOT escape — the detector's own localisation — is
    # stated there rather than encoded as a false ancestor.
    return log.observe(subject, quantity, float(core["_centre"]),
                       reader=READERS.GEOMETRY, frame=frame, **detail)


def _cell_grids(cells: Sequence[Any],
                local: Dict[int, Tuple[int, int]]) -> Dict[str, Any]:
    """`cell subject key -> (cell, grid_or_None)`, over every cut cell."""
    out: Dict[str, Any] = {}
    for c in (cells or ()):
        key = (local or {}).get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        out[sub.to_key()] = (c, G._cell_grid(c))
    return out


#: family -> (quantity, discriminator). ⚠️ DERIVED ROUTING, DECLARED HERE ONCE
#: so the walk below cannot grow a second spelling of "which family is this".
_STEP_FAMILIES = {
    "rest": (Q.REST_POSITION, _rest_discriminator),
    "arc": (Q.ARC_POSITION, _arc_discriminator),
    "articulation": (Q.ARTICULATION_POSITION, _mark_discriminator),
    "fermata": (Q.FERMATA_POSITION, _mark_discriminator),
    "ornament": (Q.ORNAMENT_POSITION, _mark_discriminator),
    "tuplet": (Q.TUPLET_MARKER_POSITION, _tuplet_discriminator),
}


def _family_of(name: str) -> Optional[str]:
    """Which step-frame family a class belongs to — `gather`'s OWN predicates.

    ⚠️⚠️ IMPORTED, NEVER RESTATED, and the ORDER is `gather_glyph_families`'
    order because that order is load-bearing: all ten `artic*` classes carry
    the detector's `ornament` CATEGORY, `_ornament_kind` answers for
    `tremolo1`-`5` whose names do not begin `ornament`, and a fermata shares
    that category too. A second copy of this routing that drifted by one
    branch would file a mark under the wrong family and every position row for
    it would be attributed to ink it does not measure.
    """
    if name in G._ARC_CLASSES:
        return "arc"
    if name.startswith(G._ARTIC_PREFIX):
        return "articulation"
    if name.lower().startswith(G._REST_PREFIX):
        return "rest"
    if G._ornament_kind(name) is not None:
        return "ornament"
    if name.lower().startswith(G._FERMATA_PREFIX):
        return "fermata"
    # ⚠️ AFTER the glyph families, because `gather_rhythm_marks` is a SEPARATE
    # walk over the same detections and its classes do not overlap these.
    if name in G._TUPLET_CLASSES:
        return "tuplet"
    return None


def gather_step_positions(log: Log, cells: Sequence[Any],
                          local: Dict[int, Tuple[int, int]],
                          detections: Dict[str, List[Any]]) -> None:
    """One step-frame position row per mark, keyed on the SHAPE row's glyph.

    ⚠️ THE INDEX COINCIDENCE IS THE CONTRACT. `gather_glyph_families` and
    `gather_rhythm_marks` both walk `enumerate(dets)` over this same list, so
    `glyph/p/s/t/c/7` here measures the ink `glyph/p/s/t/c/7` there names.
    `test_family_positions.py` asserts the partition rather than trusting it.
    """
    grids = _cell_grids(cells, local)
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        frame = G.frame_cell(sub.cell)
        cell_and_grid = grids.get(cell_key)
        grid = cell_and_grid[1] if cell_and_grid else None
        wanted = [(gi, d) for gi, d in enumerate(dets)
                  if _family_of(d.smufl_name) is not None]
        if grid is None:
            # ⚠️ ABSTAIN ONCE PER CELL, NOT PER GLYPH. A one-line percussion
            # staff has no grid at all, and `gather_notehead_positions` files
            # the same refusal in the same words for the same reason. Filing
            # it per glyph would report the cell's single fault as twenty.
            if wanted:
                log.abstain(sub, Q.CELL_POSITION_BASIS,
                            reader=READERS.GEOMETRY, frame=frame,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            marks_unmeasured=len(wanted))
            continue
        top_y, half_step = grid
        for gi, d in wanted:
            fam = _family_of(d.smufl_name)
            quantity, discriminate = _STEP_FAMILIES[fam]
            core = _step_core(d.y_canonical,
                              d.y_canonical + d.height_canonical,
                              top_y, half_step)
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            _observe_step(log, g, quantity, frame, core, discriminate(core),
                          detector_class=d.smufl_name)


def gather_meter_positions(log: Log, cells: Sequence[Any],
                           local: Dict[int, Tuple[int, int]],
                           detections: Dict[str, List[Any]]) -> None:
    """The meter glyph's position — filed on the STAFF, exactly as its shape is.

    ⚠️⚠️ THE SUBJECT IS THE STAFF AND THAT IS NOT A CHOICE. `_gather_meter_glyphs`
    files `Q.METER_GLYPH` on the STAFF with the bar in `detail["cell"]`, and
    CLAUDE.md records a whole day lost to a fixture that filed it on a GLYPH
    instead: `subject.at(Kind.CELL)` returns `None` for a staff, so the rule
    read no boxes on any real page while five unit tests stayed green. *A
    fixture that does not match GATHER tests the test.* This row is filed the
    same way, with the same `cell` and `x` keys, so the two join.
    """
    grids = _cell_grids(cells, local)
    p = None
    for c in (cells or ()):
        p = c.page_index
        break
    if p is None:
        return
    for st_index, key in sorted((local or {}).items()):
        staff_sub = R.staff(p, key[0], key[1])
        marks = []
        for cell_index, cell_dets in G._meter_cells(detections, p, key):
            for d in cell_dets:
                if d.smufl_name.startswith("timeSig"):
                    marks.append((cell_index, d))
        if not marks:
            continue
        for cell_index, d in sorted(
                marks, key=lambda m: (m[0], m[1].x_canonical, m[1].y_canonical)):
            cg = grids.get(R.cell(p, key[0], key[1], cell_index).to_key())
            grid = cg[1] if cg else None
            if grid is None:
                log.abstain(staff_sub, Q.METER_GLYPH_POSITION,
                            reader=READERS.GEOMETRY,
                            frame=G.frame_cell(cell_index),
                            reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            cell=cell_index, x=d.x_canonical)
                continue
            top_y, half_step = grid
            core = _step_core(d.y_canonical,
                              d.y_canonical + d.height_canonical,
                              top_y, half_step)
            _observe_step(log, staff_sub, Q.METER_GLYPH_POSITION,
                          G.frame_cell(cell_index), core,
                          _meter_discriminator(core),
                          cell=cell_index, x=d.x_canonical,
                          detector_class=d.smufl_name)


def _observe_band(log: Log, subject: Subject, quantity: str,
                  core: Dict[str, Any], **more: Any) -> Observation:
    detail = {k: v for k, v in core.items() if k != "_centre"}
    detail.update(more)
    return log.observe(subject, quantity, float(core["_centre"]),
                       reader=READERS.GEOMETRY, frame=G.FRAME_PAGE, **detail)


def gather_band_positions(log: Log, pws: Any, cells: Sequence[Any],
                          local: Dict[int, Tuple[int, int]],
                          detections: Dict[str, List[Any]]) -> None:
    """Dynamics, wedges and direction words: PROMOTED, mostly not invented.

    ⚠️⚠️ TWO OF THESE THREE ALREADY EXIST AS A MEASUREMENT AND ARE NOT
    INDEPENDENT EVIDENCE. `Q.DYNAMIC_LETTER` and the `CV_HAIRPINS` half of
    `Q.WEDGE_BOX` both carry `band_offset_spaces` — staff-relative, measured,
    scoreless — as a DETAIL of a row that carries the DETECTOR's confidence.
    `capture.py` grades them `band*` for exactly that: the offset is there and
    `correlated_groups` folds it into the glyph's own detector term, so it can
    never act as a second witness. This promotes them to rows of their own
    under `READERS.GEOMETRY`. **The number does not change; what changes is
    that it becomes sayable on its own.**

    ⚠️ `direction` IS genuinely new, and it is the one family `capture.py`
    reports with `shape: NO` as well — a direction word is not in the
    208-class space at all, so it has no detector row to hang a detail off.
    Its only staff-relative fact today is `placement`, an above/below the
    reader derives from the band it searched, which `capture.py` grades
    `coarse_band_only`: *far too coarse to carry a distribution*. A word's
    OFFSET separates a `cresc.` standing in the dynamics row from an
    `Allegro con brio` printed clear above the system, and `placement` cannot.
    """
    bands = G._staff_bands(pws, local)
    cell_by_key: Dict[Tuple[int, int, int, int], Any] = {}
    for c in (cells or ()):
        key = (local or {}).get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c

    # ── the two detector-sourced ones, from the detections ──────────────────
    for cell_key, dets in detections.items():
        sub = Subject.from_key(cell_key)
        band = bands.get(sub.at(R.Kind.STAFF).to_key())
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        for gi, d in enumerate(dets):
            if d.smufl_name in G._DYNAMIC_LETTER_CLASSES:
                quantity = Q.DYNAMIC_BAND_POSITION
            elif d.smufl_name in G._WEDGE_CLASSES:
                quantity = Q.WEDGE_BAND_POSITION
            else:
                continue
            g = R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
            box = G._page_box(c, d) if c is not None else None
            if box is None or band is None:
                # ⚠️ DECLINED, NEVER DEFAULTED TO THE CELL FRAME — the rule
                # `gather_dynamic_letters` states in its own comment: a mark
                # whose page position is unknown and one measured at +2.1
                # spaces are different facts.
                log.abstain(g, quantity, reader=READERS.GEOMETRY,
                            frame=G.FRAME_PAGE,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            why=("no page box" if box is None
                                 else "no staff band"),
                            detector_class=d.smufl_name)
                continue
            bottom, spacing = band[1], band[2]
            core = _band_core(box[1], box[3], bottom, spacing)
            if core is None:
                log.abstain(g, quantity, reader=READERS.GEOMETRY,
                            frame=G.FRAME_PAGE,
                            reason=ABSTAIN.NO_STAFF_GEOMETRY,
                            why="staff spacing is zero",
                            detector_class=d.smufl_name)
                continue
            _observe_band(log, g, quantity, core,
                          detector_class=d.smufl_name)

    # ── the two read from the LOG, because no detection carries their ink ───
    _promote_from_log(log, bands, Q.WEDGE_BOX, Q.WEDGE_BAND_POSITION,
                      only_reader=READERS.CV_HAIRPINS)
    _promote_from_log(log, bands, Q.DIRECTION_WORD,
                      Q.DIRECTION_BAND_POSITION, only_reader=None)


def _promote_from_log(log: Log, bands: Dict[str, Tuple[float, float, float]],
                      source: str, quantity: str,
                      only_reader: Optional[str]) -> None:
    """Measure a band position off a row already on the record.

    ⚠️ THE SOURCE DIFFERS BECAUSE THE READER DOES. A CV hairpin is found by
    morphology over the page and an OCR word by a reader working on the ink
    the detections were SUBTRACTED from — neither is in `detections`, and
    inventing a second path to their pixels would be a second spelling of a
    reading that already happened. Both rows already carry `bbox_page_px`,
    which is the frame the band measurement wants.

    ⚠️ `all_rows()` returns a TUPLE — a snapshot — so appending to the log
    while walking it is safe. That is not incidental: `Log` is append-only
    with no update and no delete, which is what makes a snapshot meaningful.
    """
    for row in log.all_rows():
        if not isinstance(row, Observation) or row.quantity != source:
            continue
        if only_reader is not None and row.reader != only_reader:
            continue
        box = row.detail.get("bbox_page_px")
        staff = row.subject.at(R.Kind.STAFF)
        band = bands.get(staff.to_key()) if staff is not None else None
        if not box or len(box) != 4 or band is None:
            log.abstain(row.subject, quantity, reader=READERS.GEOMETRY,
                        frame=G.FRAME_PAGE,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        why=("no page box" if not box else "no staff band"),
                        promoted_from=row.id)
            continue
        core = _band_core(float(box[1]), float(box[3]), band[1], band[2])
        if core is None:
            log.abstain(row.subject, quantity, reader=READERS.GEOMETRY,
                        frame=G.FRAME_PAGE,
                        reason=ABSTAIN.NO_STAFF_GEOMETRY,
                        why="staff spacing is zero", promoted_from=row.id)
            continue
        # ⚠️ `promoted_from` NAMES THE ROW AND IS NOT `derived_from`. The
        # distinction is the whole point of the promotion: `derived_from`
        # makes the two ONE signal in `Log.closure`, which is the state this
        # change exists to leave. The id is recorded so a human can follow the
        # join; the CLOSURE stays disjoint because the GRID is an independent
        # input. See the module docstring for the half of that which is true
        # and the half that is not.
        _observe_band(log, row.subject, quantity, core,
                      promoted_from=row.id, source_reader=row.reader)


def gather_family_positions(log: Log, pws: Any, cells: Sequence[Any],
                            local: Dict[int, Tuple[int, int]],
                            detections: Dict[str, List[Any]]) -> None:
    """Every family's own position fact. Off by default — see `POSITIONS_ENV`.

    ⚠️ ONE FLAG, ONE CALL SITE, AND FLAG-OFF WRITES NOTHING AT ALL — not an
    abstention, not a page-level note. `test_family_positions.py` proves the
    record is byte-identical with the flag off, with a positive control that
    the comparison can fail.
    """
    if not positions_enabled():
        return
    gather_step_positions(log, cells, local, detections)
    gather_meter_positions(log, cells, local, detections)
    gather_band_positions(log, pws, cells, local, detections)
