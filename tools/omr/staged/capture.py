"""What do we CAPTURE about a piece of ink? — its shape, its position, the
raster it was measured on and the resolution it was handed, per family.

    python3 -m tools.omr.staged.capture            # the per-family table
    python3 -m tools.omr.staged.capture --json
    python3 -m tools.omr.staged.capture --check    # non-zero on anything not
                                                   # on KNOWN_GAPS

⚠️⚠️ **THE QUESTION, AND WHY IT IS THREE.** Sean, 2026-09-17: *"when we gather
information are we collecting both the ink shape as well as the location of
the ink on the page? ... How do we currently use the geometry to determine
pitch for a note? It seems that a similar process should be used for the
numbers. I also wonder, since we are removing fine lines like the staff, at
which stage we are reading the ink of what will become the numbers. Should we
read them before the staff is removed or after, or both? I think these
questions should be applied to every bit of ink we are trying to capture and
classify."*

So, per family:

**1. SHAPE** — is the ink's appearance recorded, WITH a confidence? A class
name is a guess and must carry its score, or a consumer cannot weigh it.

**2. POSITION** — is where it sits against the STAFF GRID recorded, as a
SEPARATE row carrying NO confidence? ⚠️ The separateness is not tidiness:
`Q.CLEF_POSITION`'s own docstring records that a detail field on the glyph row
**cannot work**, because `Evidence.correlated_groups` calls every row from one
reader on one crop ONE SIGNAL and `tally` takes the group's strongest term —
so a term citing the glyph row is absorbed by that glyph's own detector term.
A position refined onto the shape row is not a second witness. It has to be a
different reader.

**3. IMAGE** — which raster answered: staff lines INTACT, or ERASED? A digit is
broken by erasure where the lines crossed it and merged INTO the lines if they
are kept, so the two rasters do not agree about thin ink — and today a row
mostly cannot say which one it came from.

**4. RESOLUTION** (`A-INK-2`) — is the consumer getting the resolution the
SOURCE actually has? `OMR_DPI` is a CONSTANT applied to every document, and the
two kinds of source want opposite things from it: a SCANNED plate has a native
resolution fixed at scan time, so rendering above it is pure upsampling and
below it discards plate; a VECTOR page has none and genuinely renders sharper.
⚠️⚠️ **The classifier that would route them is already shipped and already
opens the dictionary that carries the answer** — `input_domain._classify_page`
reads `bbox` and `Filter` out of it and leaves `width`/`height` untouched.
⚠️ **The measured `OMR_IMGSZ` result must not be quoted against this**: *larger
is NOT better* is a fact about the DETECTOR's letterboxing and anchors, and the
`resolution` column exists so a direct-pixel reader cannot be tarred with it.

## The exemplar, which exists for exactly one family

`Q.GLYPH_BOX` carries the class and the detector's `score`; `Q.NOTEHEAD_STAFF_
POSITION` carries `2.9591836734693877` with **`score=None`**, from a DIFFERENT
reader (`READERS.GEOMETRY`); `adjudicate_clef` settles the clef without either;
and `consequences.restate_pitch` combines position + clef into the pitch with
both in its basis. Read that rule's docstring — it states the whole argument,
including why the legacy habit of computing the pitch at the moment of
measurement and rounding the clef-free position away *"one line later"* left
later decisions with nothing to reconsider the clef with.

⚠️ **A RULER READING IS NOT A GUESS, and `score=None` is how the record says
so.** That is the mechanical signature this module keys on: a position fact is
an observation with no score, from a geometry reader, whose value is a staff-
grid coordinate.

## ⚠️ THE MOTIVATING FAILURE — a barline read as a time signature

`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §6.2. On Litolff Beethoven 5
p.62 the pipeline reads a `3/4` that is **one barline broken into two
fragments**: `timeSig3` and `timeSig4`, both at `x = 0.00` — the cell's LEFT
EDGE — **0.35 and 0.40 staff spaces wide**. `_meter_from_digits` needs two
stacked digits and a broken barline supplies exactly that.

⚠️⚠️ **A POSITION FACT DOES NOT REFUSE IT, AND AN EARLIER DRAFT OF THIS
PARAGRAPH SAID IT DID — *"refuses it on geometry alone"*. THAT IS WITHDRAWN.**
Sean, 2026-09-17: *"position is an option for helping us determine something
but will rarely be a clear rule that determines by itself. 2 numbers not
connected, one in the upper half and one in the lower half, could be a time
signature. Due to ink bleed they may appear connected, or other things that we
can't determine... Quick rules will give us quick results that could be poor."*
On a bitonal plate bleed fuses two digits into one stroke, so a stroke crossing
the staff does not disprove a meter — and two fragments in two halves are
exactly what this broken barline looks like, so that shape does not prove one
either. **Geometry alone settles neither direction.**

What a position fact DOES is CONTRIBUTE. A time signature's placement is rigid
— *numerator in the upper two spaces, denominator in the lower two, centred on
each other* — and the project already knows it, which is why
`time_signature_locator` exists. But the geometry lives INSIDE a template
search as a constraint and is thrown away: nothing records where the ink
stood, so no later stage can weigh it against the ink, the other staves of the
system, or anything else. The `time` family has a SHAPE fact and no POSITION
fact, and this is what that costs — **one path missing, not one rule
missing.**

## ⚠️ DERIVED WHERE IT CAN BE, DECLARED WHERE IT CANNOT — and the split is stated

Two things here are hand-written, and both are GUARDED so that a new one is a
loud failure rather than a silent omission — the `class_aliases.unaccounted()`
contract this repo already trusts:

* `UNSCORED` partitions every scoreless quantity by WHAT KIND of fact it is.
  Only a human can say that `Q.CELL_STAFF_SPACE` is a unit and
  `Q.CLEF_POSITION` is a staff-grid position; the tool cannot read intent. But
  it CAN insist that every scoreless quantity is in the table, so a fourth
  position fact cannot be added without this module noticing.
* `READER_RASTER` maps each `READERS` member to the function that actually
  touches a raster. There is no mechanical link from the name `"cv_lines"` to
  `line_detection.detect_stems`. ⚠️ **What is NOT declared is the ANSWER**: the
  variant is read out of that function's own AST, so the day a reader changes
  which image it measures, this table changes with it and no entry has to be
  edited.

⚠️ **AND THE DERIVATION HAS A TRAP THE SHIPPED TOOL FELL INTO.**
`gather_glyph_families` passes `reader`, `frame` and `score` through a
`**common` dict built one line above the call. A visitor that reads only
literal keywords sees none of them — and `gather_coverage.gathered()` reports
**`ARC_BOX`, `ARTICULATION_MARK`, `FERMATA_MARK`, `ORNAMENT_MARK` and `REST`
as having NO READER** for exactly that reason. All five carry
`READERS.DETECTOR` and a confidence. Had this module copied that walker it
would have reported five families as capturing no shape confidence, which is
the reverse of the truth. `_unpacked` resolves a `**name` bound to a `dict(...)`
in the same function, and `test_staged_capture.py` pins it.

⚠️ **EVERY QUESTION CARRIES A POSITIVE CONTROL** and `--check` exits non-zero
on a control at zero, BEFORE it looks at a finding. A question that can only
ever answer "nothing wrong" is not a question — the flag-direction guard's
first version descended THROUGH `environ.get` onto `os.environ`, matched
nothing, and both its real assertions passed vacuously.

⚠️ **A fallback here never converts "cannot tell" into a definite answer.** An
unresolvable reader, quantity or raster is `None`, lands in `unresolved`, and
`--check` fails on it. It is never spelled "intact" or "fine".
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

#: ⚠️ IMPORTED, NEVER RESTATED. `record.py` owns what kind of claim each
#: quantity makes; this module owns only the CONSTRAINT between that table and
#: `UNSCORED`. Aliased on the way in so a reader of `claim_consistency` can see
#: at a glance that the answer comes from elsewhere.
from .record import (CLAIM, CLAIM_OF_UNSCORED, CLAIMS,
                     claim_of as record_claim_of,
                     claims_of as record_claims_of,
                     claims_unaccounted as record_claims_unaccounted)

_HERE = pathlib.Path(__file__).resolve().parent
_OMR = _HERE.parent
_ROOT = _OMR.parent.parent

#: ⚠️⚠️ THIS MODULE NAMES DETAIL KEYS IN ORDER TO AUDIT THEM AND IS NOT A
#: CONSUMER OF ANY OF THEM. It asks whether a row records which raster it was
#: measured on, so `"staff_lines_erased"` has to appear in its own source —
#: and `wiring`'s DETAIL question, which reports a key written and read by
#: nobody, counted that as a read. Committing this module turned the two
#: `staff_lines_erased` entries in `wiring.KNOWN_GAPS` STALE and took
#: `wiring --check` from 0 to 1 on a key still consumed by nothing.
#:
#: It is the FOURTH member of a family `wiring` already documents — a gap
#: list, a test and a benchmark probe are not consumers either — and the
#: first that lives in the same tree as the real consumers, which is why a
#: tree test cannot separate it and a declaration can.
DERIVED_CHECK = True


# ─────────────────────────────────────────────────────────────────────────────
# 1. WHAT KIND OF FACT IS EACH SCORELESS QUANTITY?
#
# ⚠️ A DECLARED PARTITION, GUARDED. `score is None` is derived; what the value
# MEANS is not readable from the code. The guard is `unaccounted()`: a
# scoreless quantity in neither this table nor KNOWN_GAPS fails `--check`, so
# the fourth staff-grid position fact announces itself.
# ─────────────────────────────────────────────────────────────────────────────

#: A measurement of WHERE ink sits against the staff line grid, in half-spaces.
#: ⚠️ THIS IS THE ANSWER TO QUESTION 2 and the population is deliberately tiny.
STAFF_GRID_POSITION = "staff_grid_position"

#: Page or cell geometry — where a STAFF or a CELL is, not where a MARK is.
PAGE_GEOMETRY = "page_geometry"

#: A unit or a scale: how big a staff space is, in some frame.
UNIT = "unit"

#: A relation between two things already located (a distance, an overlap).
RELATION = "relation"

#: Ink with a box and no class — the population the classifications are OF.
RAW_INK = "raw_ink"

#: A reading whose value is a NAME or a STRUCTURE, where a staff-grid
#: coordinate would say nothing (a label's text, a work's roster).
NOT_A_MARK = "not_a_mark"

#: A fit or a vote whose value is already an interpretation of position.
DERIVED_FIT = "derived_fit"

#: ⚠️⚠️ A POSITION FACT NAMES THE FAMILY WHOSE INK IT MEASURES, AND WITHOUT
#: THAT THIRD FIELD THE JOIN IS WRONG IN THE MOST FLATTERING DIRECTION.
#: `adjudicate_arc_kind` declares `notehead_staff_position` in `wants` — the
#: NOTES' positions, which is the right evidence for the tie/slur grammar and
#: says NOTHING about where the curve is. Keyed on "does this decision read a
#: position fact", `slur` and `tie` came out **MEASURED**, and this module's
#: own KNOWN_GAPS text (*"the NOTES' positions, not the arc's"*) contradicted
#: its own table. A position is a fact about ONE population of ink; reading
#: someone else's is not having your own.
#:
#: Guarded: every family named here must be in `export.FAMILIES`, and a
#: position declared for a family whose decision cannot READ it is reported.
#:
#: ⚠️ THE THIRD FIELD TAKES A TUPLE, AND `Q.ARC_POSITION` IS WHY. `slur` and
#: `tie` are two rows of `export.FAMILIES` reading ONE quantity (`Q.ARC_KIND`)
#: over ONE piece of ink, and the split between them is an ADJUDICATION. Two
#: position quantities for one arc would put **two rows from one reader on one
#: glyph**, which `gather_glyph_families`' own comment names as *"the 'two rows
#: from one reader are ONE signal' mistake, made by accident"*. So one
#: quantity names both families it measures. `_families_of` normalises.
UNSCORED: Dict[str, Tuple[str, str, Any]] = {
    # ── the document's own identity, from the CATALOG rather than the raster ─
    "DOCUMENT_IDENTITY": (
        NOT_A_MARK,
        "⚠️ NOT A MEASUREMENT OF INK, so it is scoreless for a DIFFERENT "
        "reason from the position facts: edition / publisher / work / "
        "scan-type, filed once per document by `gather_document_identity` at "
        "`source_kind: catalog`. Admissible as a conditioning variable "
        "precisely BECAUSE it does not come off the raster and cannot fall "
        "silent when the plate is bad (CLAUDE.md's `source_kind` doctrine). "
        "It is the key the positional store conditions on, and it is what "
        "CLOSED this tool's own CROSS-DOCUMENT finding on 2026-09-17.",
        None),
    # ── the three that answer question 2 ────────────────────────────────────
    "NOTEHEAD_STAFF_POSITION": (
        STAFF_GRID_POSITION,
        "THE EXEMPLAR. `(y_center - top_y) / half_step` off the cell's own "
        "measured line grid, carrying `residual` and `rounded`. Consumed by "
        "`consequences.restate_pitch` together with the clef.",
        "note"),
    "CLEF_POSITION": (
        STAFF_GRID_POSITION,
        "the same measurement from the same grid for a clef glyph, and a "
        "SEPARATE row from a separate reader because a detail field on the "
        "glyph row is absorbed by that glyph's own detector term.",
        "clef"),
    "KEYSIG_RUN_POSITION": (
        STAFF_GRID_POSITION,
        "the accidental run's positions, CLEF-FREE — so a run that fits "
        "treble's slots and not bass's is evidence about the CLEF.",
        "key"),

    # ── the eleven that answered it, 2026-09-17 ─────────────────────────────
    # ⚠️ SYMBOL-SPECIFIC BY INSTRUCTION, not one schema eleven times. Produced
    # by `positions.py` behind `OMR_FAMILY_POSITIONS` (default OFF) and READ
    # BY NOTHING — every one is `position_declared_but_unread` below, which is
    # the honest state of a producer whose first consumer deliberately has not
    # landed. See `reach.KNOWN_GAPS`.
    "REST_POSITION": (
        STAFF_GRID_POSITION,
        "WHICH SIDE OF WHICH LINE this rest hangs from. A whole rest and a "
        "half rest are the SAME SHAPE and differ only in that: a whole hangs "
        "BELOW the second line from the top, a half SITS ON the middle one. "
        "The attachment is COMPARATIVE (which edge is nearer a line) with "
        "both residuals recorded, so it carries no threshold.",
        "rest"),
    "ARC_POSITION": (
        STAFF_GRID_POSITION,
        "the ARC's own ink — `depth_steps` and which side of the staff it "
        "stands on. ⚠️ Curvature is NOT claimed: a bounding box is identical "
        "for an arc opening up and one opening down.",
        ("slur", "tie")),
    "ARTICULATION_POSITION": (
        STAFF_GRID_POSITION,
        "measured above/below/inside — the ruler beside the class name's own "
        "suffix, recorded so it CAN contradict it.",
        "articulation"),
    "FERMATA_POSITION": (
        STAFF_GRID_POSITION,
        "the same measurement, APART from the articulation's: a fermata hangs "
        "over whatever sounds beneath it (most often a whole-bar rest) while "
        "an articulation attaches to one notehead, so they are two "
        "distributions and pooling them would average them.",
        "fermata"),
    "ORNAMENT_POSITION": (
        STAFF_GRID_POSITION,
        "the same again, apart for its own reason: a tremolo rides the STEM "
        "and its class states no side at all, so position is the only thing "
        "that ever says which side it is on.",
        "ornament"),
    "TUPLET_MARKER_POSITION": (
        STAFF_GRID_POSITION,
        "WHERE THE DIGIT STANDS, which for a tuplet is the whole question — "
        "one `numeral` class covers meters, tuplet digits, fingerings and "
        "measure numbers, a POSITIONAL distinction. ⚠️ `Q.TUPLET_MARKER` "
        "records `x0`, `x1`, `x_center` and NO `y` at all.",
        "tuplet"),
    "METER_GLYPH_POSITION": (
        STAFF_GRID_POSITION,
        "a meter is TWO MARKS, one in each half of the staff, centred on each "
        "other. `half` is `upper`/`lower`/`spans`/`outside` against the "
        "staff's own middle line — a pure predicate, no constant. ⚠️ Filed on "
        "the STAFF with the bar in `detail['cell']`, exactly as `METER_GLYPH` "
        "is.",
        "time"),
    "DYNAMIC_BAND_POSITION": (
        STAFF_GRID_POSITION,
        "PROMOTED, not invented: `DYNAMIC_LETTER.band_offset_spaces` is the "
        "same measurement living as a DETAIL of a SCORED row, which is the "
        "`band*` grade this table gives it. Staff SPACES below the bottom "
        "line, because a dynamic is not on the grid at all.",
        "dynamic"),
    "WEDGE_BAND_POSITION": (
        STAFF_GRID_POSITION,
        "PROMOTED from the `CV_HAIRPINS` half of `WEDGE_BOX`, and MEASURED "
        "for the DETECTOR half, which never carried one.",
        "wedge"),
    "DIRECTION_BAND_POSITION": (
        STAFF_GRID_POSITION,
        "the one that is genuinely new — this family has no detector row to "
        "hang a detail off (`shape: NO`), and its only staff-relative fact is "
        "`placement`, graded `coarse_band_only` here. The OFFSET separates a "
        "`cresc.` in the dynamics row from an `Allegro` above the system.",
        "direction"),
    "CELL_POSITION_BASIS": (
        UNIT,
        "⚠️ NOT A POSITION — the REFUSAL. A cell with no five-line grid (a "
        "one-line percussion staff) can measure nothing, and the abstention "
        "is filed ONCE per cell rather than once per mark.",
        None),

    # ── geometry of PLACES, not of marks ────────────────────────────────────
    "STAFF_LINES": (PAGE_GEOMETRY, "the five y positions the grid IS.", None),
    "STAFF_SPACING": (UNIT, "px between lines, on the page.", None),
    "STAFF_EXTENT": (PAGE_GEOMETRY, "a staff's x span.", None),
    "STAFF_SKEW": (PAGE_GEOMETRY, "measured tilt/bow of a staff.", None),
    "STAFF_ORDINAL": (PAGE_GEOMETRY, "a staff's index in its system.", None),
    "SYSTEM_STAFF_COUNT": (PAGE_GEOMETRY, "staves a system prints.", None),
    "CELL_BOX": (PAGE_GEOMETRY, "a measure cell's own rectangle.", None),
    "CELL_STAFF_SPACE": (UNIT, "a staff space in a CELL's frame.", None),
    "BARLINE_COLUMN": (PAGE_GEOMETRY, "a fitted barline, x per staff.", None),
    "BRACKET_BLOCK": (PAGE_GEOMETRY, "which bracket group a staff is in.", None),
    "GAP_BRIDGING": (PAGE_GEOMETRY, "ink crossing an inter-staff gap.", None),

    # ── the ink of a MARK, with a box and no staff-grid slot ────────────────
    "STEM": (
        RAW_INK,
        "a CV stem: `[x, y, w, h]` in the cell's frame, scoreless because "
        "morphology returns no confidence. ⚠⚠ THIS ENTRY SAID `x`, `y0`, "
        "`y1` UNTIL 2026-09-21, which is the spelling `record.py:381` "
        "records as REFUTED against the record itself — `detail.x0 == "
        "value[0]` and `detail.x1 - detail.x0 == value[2]` on 400 of 400 "
        "rows. It is the THIRD box convention in one record and they "
        "disagree (`Q.GLYPH_BOX.value` is `[name, x, y, w, h]`, "
        "`Q.INK.detail.ink_bbox_canonical` is `[x0, y0, x1, y1]` CORNERS, "
        "this is `[x, y, w, h]`), and reading one as another gives a "
        "NEGATIVE width and a clean believable zero — it cost "
        "`benchmarks/omr-ink-extent-2026-09` a run reporting "
        "`NO_INK_UNDER_BOX` on 100 of 106 rows. ⚠️ It is also the classic "
        "case of the repo's own anti-pattern — 916 rows found unread THREE "
        "separate times — and its extent IS a staff-grid measurement "
        "waiting to be made: a stem runs from its notehead to a beam, so "
        "`y` and `y + h` against the grid would say which end is which. "
        "Nothing converts them.",
        None),

    "VERTICAL_RUN": (
        RAW_INK,
        "EVERY component the stem opening produced, accepted AND refused, "
        "scoreless for the same reason `STEM` is: morphology returns no "
        "confidence, and this row asserts no identity to be confident about. "
        "⚠️ It is `STEM`'s own population BEFORE the six filters cut it, which "
        "is why the two sit under one word rather than one being a refinement "
        "of the other. ⚠️ AND IT ANSWERS HALF OF `STEM`'s ENTRY ABOVE: that "
        "entry says a stem's endpoints ARE a staff-grid measurement waiting to "
        "be made and that NOTHING CONVERTS THEM — these rows carry the "
        "endpoints in PAGE PIXELS, which is the frame `Q.STAFF_LINES` is in, "
        "so the conversion is now possible. ⚠️ It does NOT itself carry a "
        "staff-grid position, and that is the same gap `INK` reports below: "
        "the position would be an ADJUDICATED reading of the run against the "
        "lines, and putting it on the gather row would put the decision in "
        "GATHER, which is the fault this quantity exists to expose.",
        None),

    # ── relations between things already placed ─────────────────────────────
    "GLYPH_BAND_DISTANCE": (
        RELATION,
        "a glyph's distance to each candidate staff band. ⚠️ It DOES carry "
        "`position_in_candidate`, a staff-grid coordinate — as a DETAIL of a "
        "relation row, which is the shape `Q.CLEF_POSITION`'s docstring "
        "argues cannot act as an independent witness.",
        None),
    "GLYPH_LADDER": (RELATION, "ledger rung completeness for a contest.", None),

    # ── ink with no class ───────────────────────────────────────────────────
    "INK": (
        RAW_INK,
        "one connected component, named or not. ⚠️ It carries a BOX and a "
        "shape (`width_spaces`, `height_spaces`) and NO staff-grid position "
        "— see KNOWN_GAPS; this is the newest gather site and it did not get "
        "one either.",
        None),

    # ── values a staff-grid coordinate would say nothing about ──────────────
    "CLEF_SEED": (NOT_A_MARK, "the dossier's clef; no ink.", None),
    "DOSSIER_FACT": (NOT_A_MARK, "a fact about the WORK.", None),
    "ROSTER_ENTRY": (NOT_A_MARK, "the catalog's instrument list.", None),
    "MARGIN_LABEL": (
        NOT_A_MARK,
        "an instrument name in the margin. It carries `y_center_px` for the "
        "staff join; a staff-GRID position is meaningless outside the staff.",
        None),
    "DIRECTION_WORD": (
        NOT_A_MARK,
        "a word printed inside the system. It carries `placement` "
        "(above/below) and a page box — see KNOWN_GAPS for the band.",
        None),
    "WEDGE_BOX": (
        RELATION,
        "⚠️ SPLIT BY READER. The `CV_HAIRPINS` rows carry "
        "`band_offset_spaces` — a staff-relative position, measured, with no "
        "score — which is the closest thing outside the three above. The "
        "`DETECTOR` rows carry a score and are a SHAPE fact.",
        None),

    # ── a fit: position already interpreted ─────────────────────────────────
    "KEYSIG_CLEF_FIT": (DERIVED_FIT, "which clef's slot table fits.", None),
    "KEYSIG_TEMPLATE_FIT": (DERIVED_FIT, "the template reader's answer.", None),
}


def _families_of(quantity: str) -> Tuple[str, ...]:
    """Which families a position quantity measures the ink OF. `()` for none.

    ⚠️ ONE ACCESSOR, because the third field is `str | tuple | None` and three
    separate call sites read it. A fourth reader that unpacked it its own way
    is exactly how a table grows two meanings.
    """
    fam = UNSCORED.get(quantity, ("", "", None))[2]
    if fam is None:
        return ()
    return (fam,) if isinstance(fam, str) else tuple(fam)


def _is_position(quantity: str) -> bool:
    return UNSCORED.get(quantity, ("", "", None))[0] == STAFF_GRID_POSITION


# ─────────────────────────────────────────────────────────────────────────────
# 2. WHICH RASTER DOES EACH READER MEASURE?
#
# ⚠️ THE MAP IS DECLARED; THE ANSWER IS DERIVED. There is no mechanical link
# from the vocabulary word `"cv_lines"` to `line_detection.detect_stems`, so
# the entry point is named here. What is NOT named is which image it reads —
# that is read out of the function's own AST by `_raster_of`, so a reader that
# changes rasters changes this table without anyone editing it.
#
# ⚠️ AND THE PATH MATTERS, NOT JUST THE MODULE. `key_signature_locator` never
# touches a cell image: it goes through `header_ink.header_ink_mask`. Naming
# the module would answer for the wrong code, so the entry names the function
# that actually reads pixels and the comment records how it is reached.
# ─────────────────────────────────────────────────────────────────────────────

#: ── QUESTION 4: RESOLUTION ──────────────────────────────────────────────────
#:
#: What the render DPI MEANS to a reader, and the distinction must not be
#: flattened. ⚠️⚠️ THE MEASURED *"larger is NOT better"* RESULT IS ABOUT
#: `OMR_IMGSZ` AND IS A FACT ABOUT THE DETECTOR, NOT ABOUT THE IMAGE:
#: ultralytics letterboxes to `imgsz²` whatever the cell's size, so a bigger
#: value buys anchors and false noteheads. A geometry or CV consumer has no
#: letterboxing and no anchors, measures the raster's own pixels, and that
#: finding says nothing about it. These two values are how the table refuses
#: to flatten them.
LETTERBOXED = "letterboxed"
DIRECT_PIXELS = "direct_pixels"

#: Rasters a reader can measure. ⚠️ `OWN_ERASURE` is a THIRD image and not a
#: synonym for `ERASED`: `header_ink_mask` starts from the INTACT cell and
#: erases the lines ITSELF, by its own algorithm, because *"on the material
#: this exists for that variant is the problem"*. A row saying
#: `staff_lines_erased=True` would not distinguish the two.
INTACT = "intact"
ERASED = "erased"
ERASED_ELSE_INTACT = "erased_else_intact"
OWN_ERASURE = "own_erasure"
PAGE_RASTER = "page_raster"
NO_RASTER = "no_raster"

#: `READERS` member -> (module relative to tools/omr, function) or None.
READER_RASTER: Dict[str, Optional[Tuple[str, str]]] = {
    "DETECTOR": ("yolo_detector.py", "detect"),
    # ⚠️ The same weights on a header crop — the same function, so the same
    # raster. Kept as its own reader because two rows from one reader on one
    # crop are ONE signal and the crops differ.
    "DETECTOR_HEADER": ("yolo_detector.py", "detect"),
    "SPECIALIST": ("yolo_detector.py", "detect"),
    "CV_LOCATOR": ("clef_locator.py", "_ink_mask"),
    "CV_LINES": ("line_detection.py", "detect_stems"),
    "CV_HAIRPINS": ("hairpin_detection.py", "detect_hairpins"),
    # ⚠️ In `gather.py` itself, not in a reader module.
    "CV_INK": ("staged/gather.py", "_ink_components"),
    # ⚠️ Reached as `key_signature_locator.locate_key_signature` ->
    # `header_ink.header_ink_mask`; the locator never touches a cell image.
    "CV_HEADER": ("header_ink.py", "header_ink_mask"),
    "TEMPLATE": ("key_signature_template.py", "read_key_signature"),
    # ⚠️ NO RASTER, and that is the point of the exemplar: the position facts
    # are computed off line positions the geometry stage already measured.
    "GEOMETRY": None,
    "TEXT_LAYER": None,
    "SURYA": ("direction_text.py", "_page_ink"),
    "TESSERACT": ("direction_text.py", "_page_ink"),
    "VISION": None,
    "DOSSIER": None,
    "CATALOG": None,
    "CARRY": None,
}

#: A second raster the same reader name reaches, where the gather site calls a
#: different entry point. ⚠️ REPORTED APART, NEVER FOLDED IN: `TEMPLATE` reads
#: the key signature through `key_signature_template` and the meter through
#: `time_signature_locator`, and a single answer for the name would be a
#: guess about which one a given row came from.
READER_RASTER_ALSO: Dict[str, List[Tuple[str, str]]] = {
    "TEMPLATE": [("time_signature_locator.py", "locate_time_signature")],
    "CV_LINES": [("line_detection.py", "detect_beams")],
    "CV_LOCATOR": [("clef_locator.py", "_staff_left_column")],
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. THE STANDING GAPS — an INVENTORY with reasons, not a suppression list
#
# ⚠️ Same contract as `wiring.KNOWN_GAPS` and `export_coverage.KNOWN_GAPS`:
# every problem the derivation finds TODAY is here WITH ITS REASON, `--check`
# fails on anything NOT here, and ⚠️ AN ENTRY THAT IS CLOSED MUST LEAVE IT or
# the list stops describing the pipeline and starts describing its history.
# `test_staged_capture.py` enforces both directions.
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_GAPS: Dict[str, str] = {
    # ── the claim kind against UNSCORED: ONE disagreement, and it is real ──
    "CLAIM-DISAGREES Q.WEDGE_BOX": (
        "⚠️⚠️ THE ONE ENTRY IN `UNSCORED` THAT IS NOT SCORELESS, and the "
        "constraint found it on its first run rather than being written "
        "around it. `Q.WEDGE_BOX` is observed by TWO readers — `DETECTOR` "
        "with a score at gather.py:1131 and `CV_HAIRPINS` without one at "
        ":1212 — so it is the only member of a table of scoreless quantities "
        "that is scored, measured over all 38 entries. `UNSCORED` filed it "
        "'relation' as the least-bad fit for a quantity only half of which "
        "its axis can see, and its own reason text says so: *'SPLIT BY "
        "READER … the DETECTOR rows carry a score and are a SHAPE fact.'* "
        "`record.CLAIMS` calls it IDENTIFICATION because BOTH halves assert "
        "the same thing about ink — *there is a hairpin here* — and a "
        "hairpin that is not there is how either half is wrong. "
        "⚠️ NOT REPAIRED HERE, deliberately, and in neither direction: "
        "widening 'relation' to admit an identification is widening a "
        "control until it passes, and re-filing `Q.WEDGE_BOX` is a judgement "
        "about `UNSCORED`'s OWN axis, which this change does not own. "
        "⚠️ It is also the case the brief expected to force per-reader "
        "declarations and did NOT: `Q.BEAM_STROKE` and `Q.WEDGE_BOX` are the "
        "only two reader-split quantities in the vocabulary and both split "
        "on SCORE, not on CLAIM, so the claim stayed a property of the "
        "quantity alone. Closing this means one of the two tables moving, "
        "and the entry leaves when it does."),

    # ── POSITION: EVERY family with no staff-grid position of its own ──────
    #
    # ⚠️⚠️ THERE ARE NO EXEMPTIONS IN THIS BLOCK AND THAT IS SEAN'S RULING,
    # 2026-09-17: *"Theoretically every position can at some point contribute
    # even if that is not with our current pipeline. We are still discovering
    # what works best and for testing we need to hold on to everything because
    # we can't yet know all of what will be helpful."*
    #
    # So the test is NOT *does this family need a position to read itself*, and
    # NOT *does recording it compose into a useful prior*. It is: **we cannot
    # yet know, therefore yes.** Two earlier framings of this list were
    # withdrawn — one exempting families whose CLASS NAME states a side, one
    # allowing an exemption argued from the aggregate — and every entry below
    # is a reason a gap EXISTS, never a reason it is acceptable.
    #
    # ⚠️ THE SCOPE IS DISCOVERY AND A LATER READER MUST NOT TAKE IT AS
    # PERMANENT. Sean scoped it to *"for testing"* — a phase-appropriate call
    # about a pipeline still being figured out, not a standing claim that the
    # record may grow without bound. The cost to watch is measured in
    # `benchmarks/omr-ink-gather-2026-09/FINDINGS.md`: the ink layer alone adds
    # **0.6 MB per Litolff page and 3.1 MB per Breitkopf page**, against
    # records already measured in the hundreds of MB. Noted as the thing to
    # watch, NOT as an argument against.
    #
    # ⚠️⚠️ THESE ELEVEN WERE `POSITION <family>` — *"has no staff-grid
    # position fact of its own"* — UNTIL 2026-09-17, AND THEY CLOSED. Eleven
    # families now have one (`positions.py`, `OMR_FAMILY_POSITIONS`, default
    # OFF), so the old entries went STALE and `--check` said so; a closed gap
    # must LEAVE the list or the list stops describing the pipeline and starts
    # describing its history. What replaces them is the WEAKER, TRUER finding:
    # the fact exists and the family's deciding rule does not read it. The
    # repair changed from *write a reader* to *wire the input you already
    # have*, and each entry below keeps the reason its predecessor gave for
    # WHY the position matters, because that argument did not close.
    #
    # ⚠️ NOT READING THEM IS DELIBERATE, NOT AN OVERSIGHT. A producer and its
    # first consumer landing together makes the reach measurement circular —
    # `gather_ink`'s discipline, one day older. The table's `position` column
    # therefore still reads NONE for all eleven, and that grading is correct:
    # nothing has reached a decision.
    "UNREAD-POSITION Q.METER_GLYPH_POSITION": (
        "⚠️⚠️ THE MOTIVATING CASE, and the fact now exists. A time "
        "signature's placement is RIGID — numerator in the upper two spaces, "
        "denominator in the lower two, centred on each other — and "
        "`time_signature_locator` already relies on it INSIDE a template "
        "search, as a constraint thrown away. `Q.METER_GLYPH_POSITION` "
        "records `half` (upper/lower/spans/outside) against the staff's own "
        "middle line. ⚠️ `adjudicate_meter` does not read it, so the Litolff "
        "p.62 fragments are STILL not refused: `_meter_from_digits` asks for "
        "two digit glyphs at two different `y_center` values and nothing "
        "else. Wiring that is the repair, and it is an ADJUDICATE change."),
    "UNREAD-POSITION Q.REST_POSITION": (
        "a rest's vertical slot is its IDENTITY, not decoration: a whole rest "
        "hangs UNDER the 4th line and a half rest sits ON the 3rd, same "
        "rectangle, different duration. The fact is now recorded — "
        "`attached_line`, `hangs`, both edge residuals — and "
        "`adjudicate_duration` still reads the class name and nothing else. "
        "⚠️ `OMR_WHOLE_REST_INK` remains the shipped workaround, and its own "
        "findings record the cost this would remove: on Breitkopf its "
        "position witness INVERTS (`slot 20 / neighbour 5` -> `slot 1 / "
        "neighbour 11`) because it is reconstructed per-document from the "
        "detector's boxes instead of read once from the grid."),
    "UNREAD-POSITION Q.DYNAMIC_BAND_POSITION": (
        "PROMOTED out of the unusable place and not yet read. `benchmarks/"
        "omr-dynamics-band-2026-09` reports 73% of letters in their own "
        "staff's band and 24% in the band of the staff immediately ABOVE, "
        "distance exactly 1, no exceptions, with a measured empty interval "
        "(-3.04..-0.52 spaces). The number was always computed; what it "
        "lacked was a row of its own, so `correlated_groups` folded it into "
        "the glyph's detector term. It now has one. `adjudicate_dynamic` "
        "still does not read it."),
    "UNREAD-POSITION Q.DIRECTION_BAND_POSITION": (
        "the only one of the eleven that is genuinely NEW rather than "
        "promoted or measured-from-a-box-already-on-the-record — this family "
        "has no detector row at all (`shape: NO`). Its band offset is what "
        "separates a `cresc.` standing in the dynamics row from an `Allegro "
        "con brio` printed clear above the system, which `placement` cannot. "
        "⚠️ Its REACH is bounded by the OCR rungs: on a machine with neither "
        "Surya nor Tesseract it is zero, and that zero is the reader's "
        "absence rather than the page's silence."),
    "UNREAD-POSITION Q.WEDGE_BAND_POSITION": (
        "⚠️ WAS HALF-ANSWERED BY THE READER THAT WAS NOT ASKED TO. The "
        "`CV_HAIRPINS` rows already carried `band_offset_spaces` against the "
        "staff's own bottom line with NO score — the exemplar's shape, by "
        "accident of that rung working in page pixels per staff — while the "
        "`DETECTOR` rows carried a score and no position, so the family's "
        "answer depended on which rung fired. Both now produce the same row "
        "under `READERS.GEOMETRY`. `adjudicate_wedge_anchor` does not read "
        "it."),
    "UNREAD-POSITION Q.ARC_POSITION": (
        "covers BOTH `slur` and `tie`, because they are two families reading "
        "ONE quantity over ONE piece of ink and two position rows on one "
        "glyph would be the *two rows from one reader are ONE signal* fault "
        "made by accident. `adjudicate_arc_kind` reads "
        "`notehead_staff_position` — the NOTES' positions, the right evidence "
        "for the grammar and silent about where the curve is. ⚠️ The tie half "
        "is the sharper one: a tie's two ends are at ONE STAFF POSITION BY "
        "DEFINITION, `_pair_ties_in_cell`'s own docstring says so, and the "
        "repair that finally used it (`TIE_SAME_POSITION_MAX_SPACES`) reads "
        "the flanking NOTEHEADS' boxes because the arc had no position row. "
        "⚠️ CURVATURE IS STILL MISSING and is not claimed here: a bounding "
        "box is identical for an arc opening up and one opening down, so "
        "which end is an END and which the APEX needs the ink."),
    "UNREAD-POSITION Q.ARTICULATION_POSITION": (
        "⚠️⚠️ THE CLASS NAME STATES A SIDE AND THAT IS NOT A POSITION — an "
        "earlier draft of this list exempted this family on those grounds and "
        "the exemption was WITHDRAWN. `side` is DERIVED FROM THE CLASS so it "
        "fails together with the classification, and above/below is a BIT "
        "where the question is a distribution. `measured_side` and "
        "`steps_clear_of_staff` are now recorded beside it and can contradict "
        "it. ⚠️ Whether they DO is unmeasured: nothing compares them, because "
        "that comparison is a decision with a right to abstain."),
    "UNREAD-POSITION Q.FERMATA_POSITION": (
        "as `articulation`, and apart from it on purpose — CLAUDE.md records "
        "that a fermata's side is not even the articulation side test, since "
        "a `fermataAbove` over a bar's only rest stands above ink it belongs "
        "to. Two populations, two distributions; pooling them into one "
        "quantity would average a mark that attaches to a notehead with one "
        "that does not."),
    "UNREAD-POSITION Q.ORNAMENT_POSITION": (
        "as `articulation`, with a hole the side field cannot cover at all: a "
        "TREMOLO's side is `None` because it rides the stem, so for that "
        "class the class name carries no position of any kind and the ruler "
        "is the only thing that does."),
    "UNREAD-POSITION Q.TUPLET_MARKER_POSITION": (
        "⚠️ `Q.TUPLET_MARKER` carries `x0`/`x1`/`x_center` — a HORIZONTAL "
        "span, which is what group membership needs — and NO `y` AT ALL, so "
        "the position is read from the detections rather than from that row. "
        "That is reported and NOT silently patched: adding `y` to a shape row "
        "would change a row this flag must leave byte-identical. ⚠️ The "
        "family matters more than its size suggests: one `numeral` class "
        "covers meters, tuplet digits, fingerings AND measure numbers — *a "
        "POSITIONAL distinction, made by where the digit stands* — and "
        "`adjudicate_tuplet` fired ZERO times across 286 runs of the "
        "plumbing matrix."),
    # ── THE WALKER CANNOT DERIVE A QUANTITY PASSED AS A PARAMETER ──────────
    #
    # ⚠️⚠️ REPORTED RATHER THAN DESIGNED AROUND, AND THE ALTERNATIVE WAS
    # WORSE. `positions.py` funnels its ten quantities through two helpers
    # (`_observe_step`, `_observe_band`) so that *scoreless, `READERS.
    # GEOMETRY`, no `derived_from`* is written ONCE — the contract that would
    # otherwise be restated at ten call sites and drift at one of them. The
    # cost is that `_ObserveWalker` reads the quantity ARGUMENT and finds a
    # name rather than a literal, so it cannot attribute the site.
    #
    # Inlining `log.observe(g, Q.REST_POSITION, ...)` six times inside one
    # data-driven loop would make this walker happy and the code worse, which
    # is BUILDING TO THE INSTRUMENT. The same shape is already accepted one
    # module over: `wiring` reports `Q.<loop-bound>.promoted_from` for the
    # same reason and that entry is in ITS gap list.
    #
    # ⚠️ WHAT IS LOST, STATED: `by_quantity` cannot confirm that the ten
    # position quantities are OBSERVED, only that they are DECLARED. What
    # covers that instead is a measurement on real pages —
    # `benchmarks/omr-family-positions-2026-09/probe/position_reach.py`,
    # which counts the rows each family actually produces and exits non-zero
    # at zero.
    "UNRESOLVED observe site _observe_step": (
        "⚠️ `positions.py` — the quantity is a PARAMETER, not a literal. See "
        "the block comment above this entry: the helper exists so the "
        "scoreless/GEOMETRY/no-ancestors contract is written once, and the "
        "reach probe is what confirms the rows exist."),
    "UNRESOLVED observe site _observe_band": (
        "as `_observe_step` — the band-frame half of the same helper pair."),

    # ⚠️⚠️ `CROSS-DOCUMENT` LEFT THIS LIST ON 2026-09-17, AND IT LEFT BECAUSE
    # IT WAS CLOSED. The finding was *nothing accumulates measured geometry
    # across documents, and `publisher` — the conditioning variable — appears
    # in NO code in gather.py*. `Q.DOCUMENT_IDENTITY` and
    # `tools/omr/positional_store.py` closed both halves, and this tool's own
    # `--check` reported the entry STALE the moment the two branches met. A
    # closed gap must LEAVE the list or the list stops describing the pipeline
    # and starts describing its history.

    # ── RESOLUTION: a constant DPI over sources of two different kinds ──────
    "RESOLUTION nothing reads the source's native": (
        "⚠️⚠️ `A-INK-2`. `OMR_DPI` is a CONSTANT — 300 on the backend, 600 on "
        "the CLI — and `render_page(..., dpi=dpi)` takes it from an argument "
        "NO call site derives from the PDF. A SCANNED plate has a native "
        "resolution fixed at scan time, so rendering ABOVE it is pure "
        "upsampling and rendering BELOW it discards plate that is there; a "
        "VECTOR page has none and genuinely renders sharper. One constant, "
        "two sources that want opposite things. "
        "⚠️⚠️ THE CLASSIFIER ALREADY EXISTS AND ALREADY OPENS THE DICTIONARY: "
        "`input_domain._classify_page` is `OMR_WEIGHT_ROUTING`'s shipped, "
        "measured domain test (0 vector drawings = scan) and it reads `bbox` "
        "for coverage and `Filter` for compression while `width` and `height` "
        "sit in the same dicts untouched — *the value existed and nothing "
        "read it*, in the one module already asking the adjacent question. "
        "⚠️ THE `OMR_IMGSZ` RESULT MUST NOT BE QUOTED AGAINST THIS: *larger "
        "is NOT better* is a fact about the DETECTOR, whose letterboxing to "
        "`imgsz²` buys anchors and false noteheads; the `resolution` column "
        "separates that reader from the direct-pixel ones, which have neither "
        "letterboxing nor anchors and about which it says nothing. "
        "⚠️ WHAT WOULD FALSIFY A PER-DOCUMENT DPI: on Litolff `984073` p.62 — "
        "1-bit, 600 dpi native — components carrying a HOLE number 31 at 300 "
        "dpi and the same 31 at 1200, so 16x the pixels bought zero new "
        "structure THERE. That is one page of one publisher and it cuts both "
        "ways: it is evidence that rendering above native is free of benefit, "
        "and NOT evidence about a plate whose native resolution is below what "
        "we render. ⚠️ NOTHING HERE IS MEASURED BY THIS TOOL — the reach "
        "figure (how many held editions render above or below native) needs "
        "the library and has not been taken."),

    # ── IMAGE: a silent fallback the row does not record ────────────────────
    "IMAGE TEMPLATE": (
        "⚠️ TWO ENTRY POINTS, BOTH `erased_else_intact`, NEITHER RECORDED. "
        "`key_signature_template.read_key_signature:142` and "
        "`time_signature_locator.locate_time_signature:429` both spell "
        "`cell.image_no_staff if ... is not None else cell.image`, so which "
        "raster answered is a RUNTIME fact and no row carries it. On a header "
        "crop the erased variant is present, so in practice it is the erased "
        "one — but `in practice` is not a fact the record states."),
    "IMAGE CV_LOCATOR": (
        "`clef_locator._ink_mask:417` is `erased_else_intact` and unrecorded. "
        "⚠️ The same module's `_staff_left_column:453` is INTACT-ONLY and "
        "says so in its docstring (*'here the lines ARE the measurement'*), "
        "so one reader name covers two rasters by design."),

    # ── IMAGE: raw ink, the newest site, with no variant on the row ─────────
    "IMAGE CV_INK": (
        "`gather._ink_components` is the ONE rung that REFUSES rather than "
        "falling back (`if img is None or ndim != 2: return None`, then "
        "`abstain(note='cell carries no image_no_staff')`) — so its raster is "
        "not ambiguous and this is the weakest of the image findings. It is "
        "listed because `Q.INK` is the population every other family's ink is "
        "a classification OF, and a consumer joining an INK row to a DETECTOR "
        "row is joining two different rasters with nothing on either saying "
        "so."),
}


# ─────────────────────────────────────────────────────────────────────────────
# 3b. THE CLAIM KIND — reconciled with `UNSCORED`, never restated beside it
#
# ⚠️⚠️ `record.CLAIMS` IS THE ONLY TABLE AND IT IS IMPORTED, NOT COPIED. On
# 2026-09-17 this repo repaired FOUR separate hand-written copies of one rule
# and THREE of the four had silently gone stale, so a fifth copy of "what kind
# of claim is this" was the one outcome this job was told to avoid.
#
# What lives here is the CONSTRAINT between the two tables, not a second
# answer. `record.CLAIM_OF_UNSCORED` says which claim kinds each `UNSCORED`
# word admits; this asks whether every entry obeys it. The two tables can
# therefore disagree about a quantity for exactly as long as it takes a
# derived check to run — and they are NOT merged, because the evidence refuses
# it: `UNSCORED`'s `not_a_mark` holds a catalog fact and an OCR reading, which
# is the `source_kind` doctrine's own distinction, while `CLAIM.MEASUREMENT`
# spans four of `UNSCORED`'s seven words. Neither determines the other.
# ─────────────────────────────────────────────────────────────────────────────


def claim_consistency() -> List[str]:
    """Where `UNSCORED` and `record.CLAIMS` disagree about one quantity.

    ⚠️ A finding here is NEVER repaired by widening `CLAIM_OF_UNSCORED` until
    it passes. That is "widening a control while teaching it about a
    legitimate-sounding exception", which this file's own history records as
    how a control stops being one. A genuine disagreement goes on
    `KNOWN_GAPS` with its reason, and closing it removes the entry.
    """
    out: List[str] = []
    for q, (word, _reason, _fam) in sorted(UNSCORED.items()):
        admits = CLAIM_OF_UNSCORED.get(word)
        if admits is None:
            out.append(f"CLAIM-WORD UNSCORED word '{word}' (on Q.{q}) is in "
                       f"no record.CLAIM_OF_UNSCORED entry — say which claim "
                       f"kinds it admits")
            continue
        # ⚠️ THE UNION OVER READERS, because the constraint asks about a
        # QUANTITY and has no row in hand. `Q.MARGIN_LABEL` is EXTERNAL off
        # the text layer and IDENTIFICATION off an OCR rung, and `not_a_mark`
        # admits both -- which is the constraint doing its job rather than
        # being loose: it was written to admit exactly that pair BEFORE the
        # reader split was found, from the four catalog facts sitting beside
        # the two OCR ones.
        got = record_claims_of(q)
        bad = [g for g in got if g not in admits]
        if bad:
            out.append(
                f"CLAIM-DISAGREES Q.{q} is UNSCORED '{word}' (admitting "
                f"{'/'.join(admits)}) and record.CLAIMS calls it "
                f"'{'/'.join(got)}'")
    return out


def _gap_key(problem: str) -> Optional[str]:
    for key in KNOWN_GAPS:
        if problem.startswith(key):
            return key
    return None


def unaccounted(problems: Sequence[str]) -> List[str]:
    """Problems on no KNOWN_GAPS entry. These are what `--check` fails on."""
    return [p for p in problems if _gap_key(p) is None]


def stale_gaps(problems: Sequence[str]) -> List[str]:
    """KNOWN_GAPS entries nothing reports any more. A CLOSED gap must LEAVE."""
    hit = {_gap_key(p) for p in problems}
    return sorted(k for k in KNOWN_GAPS if k not in hit)


# ─────────────────────────────────────────────────────────────────────────────
# 4. The gather walk — every `log.observe`, with its score resolved
# ─────────────────────────────────────────────────────────────────────────────

def _q_name(node: ast.AST) -> Optional[str]:
    """`Q.GLYPH_BOX` -> "GLYPH_BOX". Anything else -> None."""
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "Q"):
        return node.attr
    return None


def _attr_tail(node: ast.AST) -> Optional[str]:
    """`READERS.DETECTOR` -> "DETECTOR"."""
    return node.attr if isinstance(node, ast.Attribute) else None


def _dict_literals(fn: ast.AST) -> Dict[str, Set[str]]:
    """Names bound to a `dict(...)` call in this function -> its keyword names.

    ⚠️⚠️ THIS IS THE `**common` RESOLUTION, AND IT IS THE ONE THING THIS
    MODULE COULD NOT COPY. `gather_glyph_families` writes

        common = dict(reader=READERS.DETECTOR, frame=frame,
                      score=float(d.confidence))
        log.observe(g, Q.ARC_BOX, name, **common, **box)

    and `gather_coverage`'s walker, which reads literal keywords only, reports
    `ARC_BOX`, `ARTICULATION_MARK`, `FERMATA_MARK`, `ORNAMENT_MARK` and `REST`
    as having **no reader at all**. Five families, every one of them carrying
    `READERS.DETECTOR` and a real confidence. Without this, the SHAPE column
    of this module's own table would have read `no` for all five — the exact
    reverse of the truth, and a finding manufactured by the instrument.
    """
    out: Dict[str, Set[str]] = {}
    for node in ast.walk(fn):
        # ⚠️⚠️ AN ANNOTATED ASSIGNMENT IS STILL AN ASSIGNMENT, and missing it
        # is the `**common` trap recurring in a second form. `gather.py` binds
        # `shared: Dict[str, Any] = {...}` and `detail: Dict[str, Any] = {...}`
        # as `ast.AnnAssign`, so an `ast.Assign`-only walk resolved neither —
        # and `Q.DIRECTION_WORD` came back without `bbox_page_px`/`placement`
        # and `Q.DYNAMIC_LETTER` without `band_offset_spaces`. The location
        # grading then reported both families as carrying NO page location,
        # which is the reverse of the truth. Found by reading the emitted
        # detail lists against the source, not by any assertion.
        if isinstance(node, ast.AnnAssign):
            tgt, val = node.target, node.value
            if val is None or not isinstance(tgt, ast.Name):
                continue
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if not isinstance(tgt, ast.Name):
                continue
            val = node.value
        else:
            continue
        if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) \
                and val.func.id == "dict":
            out.setdefault(tgt.id, set()).update(
                kw.arg for kw in val.keywords if kw.arg)
        elif isinstance(val, ast.Dict):
            out.setdefault(tgt.id, set()).update(
                k.value for k in val.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str))
    # ⚠️ `box.update(bbox_page_px=...)` adds keys after the binding. A walk
    # that stopped at the assignment would under-report the detail keys.
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "update"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in out):
            out[node.func.value.id].update(
                kw.arg for kw in node.keywords if kw.arg)
        # `box["frame_note"] = ...`
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Subscript)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id in out
                and isinstance(node.targets[0].slice, ast.Constant)
                and isinstance(node.targets[0].slice.value, str)):
            out[node.targets[0].value.id].add(node.targets[0].slice.value)
    return out


class _ObserveWalker(ast.NodeVisitor):
    """Every `log.observe(...)`, with loop-bound quantities resolved.

    ⚠️ THE LOOP BINDING IS REAL AND NOT DEFENSIVE. `gather_cv_lines` writes
    `for quantity, kind in ((Q.STEM, "stems"), (Q.BEAM_STROKE, "beams")):` and
    observes on the loop variable, so a visitor reading only `Q.X` literals at
    the call site misses BOTH. `gather_coverage` records the same fault and
    the same repair; this is the second implementation because importing that
    walker would also import its `**kwargs` blindness.
    """

    def __init__(self) -> None:
        self.sites: List[Dict[str, Any]] = []
        self.unresolved: List[Dict[str, Any]] = []
        self._fn: List[str] = []
        self._bound: List[Dict[str, List[str]]] = [{}]
        self._dicts: List[Dict[str, Set[str]]] = [{}]

    # -- scopes ----------------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._fn.append(node.name)
        self._bound.append(dict(self._bound[-1]))
        self._dicts.append(_dict_literals(node))
        self.generic_visit(node)
        self._dicts.pop()
        self._bound.pop()
        self._fn.pop()

    def visit_For(self, node: ast.For) -> None:
        frame = dict(self._bound[-1])
        targets = (node.target.elts
                   if isinstance(node.target, ast.Tuple) else [node.target])
        rows = (node.iter.elts
                if isinstance(node.iter, (ast.Tuple, ast.List)) else [])
        for pos, tgt in enumerate(targets):
            if not isinstance(tgt, ast.Name):
                continue
            found: List[str] = []
            for row in rows:
                cells = (row.elts if isinstance(row, (ast.Tuple, ast.List))
                         else [row])
                if pos < len(cells):
                    q = _q_name(cells[pos])
                    if q and q not in found:
                        found.append(q)
            if found:
                frame[tgt.id] = found
        self._bound.append(frame)
        self.generic_visit(node)
        self._bound.pop()

    # -- the call --------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        self.generic_visit(node)
        if not (isinstance(node.func, ast.Attribute)
                and node.func.attr == "observe"):
            return
        if len(node.args) < 2:
            return

        quantities = self._quantities(node.args[1])
        kw_names, has_score, reader = self._keywords(node)

        if not quantities:
            self.unresolved.append({
                "where": self._fn[-1] if self._fn else "<module>",
                "line": node.lineno, "shape": "quantity"})
            return
        for q in quantities:
            self.sites.append({
                "quantity": q,
                "where": self._fn[-1] if self._fn else "<module>",
                "line": node.lineno,
                "reader": reader,
                "scored": has_score,
                "detail": sorted(kw_names),
            })

    def _quantities(self, node: ast.AST) -> List[str]:
        q = _q_name(node)
        if q:
            return [q]
        if isinstance(node, ast.Name):
            return list(self._bound[-1].get(node.id, ()))
        return []

    def _keywords(self, node: ast.Call) -> Tuple[Set[str], bool, Optional[str]]:
        """Keyword names, whether `score=` is among them, and the reader.

        ⚠️ `**name` IS FOLLOWED. See `_dict_literals` for what it costs not to.
        A `**expr` that is not a resolvable name contributes nothing and is
        NOT silently treated as empty — the caller reports the site's detail
        as partial rather than asserting the keys are absent.
        """
        names: Set[str] = set()
        reader: Optional[str] = None
        for kw in node.keywords:
            if kw.arg is None:
                if isinstance(kw.value, ast.Name):
                    names.update(self._dicts[-1].get(kw.value.id, ()))
                    if "reader" in self._dicts[-1].get(kw.value.id, ()):
                        reader = reader or self._unpacked_reader(kw.value.id)
                continue
            names.add(kw.arg)
            if kw.arg == "reader":
                reader = _attr_tail(kw.value)
        return names, ("score" in names), reader

    def _unpacked_reader(self, _name: str) -> Optional[str]:
        """The reader inside a `**common`-style dict.

        ⚠️ Resolved by re-reading the binding rather than guessed. Today the
        only such dict in `gather.py` binds `READERS.DETECTOR`; a second one
        would need this to walk the value, and until one exists inventing that
        walk would be untested code. It returns `None` — which lands the site
        in `unresolved` — rather than a default, because a fallback that
        converts *cannot tell* into a definite answer is this repo's most
        expensive recurring bug.
        """
        return self._RESOLVED.get(_name)

    #: ⚠️ ONE ENTRY, DERIVED BY A TEST, NEVER BY MEMORY.
    #: `test_staged_capture.py::test_the_common_dict_binds_the_detector`
    #: re-reads `gather.py` and fails if this stops being true.
    _RESOLVED = {"common": "DETECTOR"}


def _gather_stage_sources() -> List[str]:
    """The source of every GATHER-stage module. ⚠️ DERIVED, NOT `gather.py`.

    ⚠️⚠️ **THE SECOND INSTRUMENT IN ONE DAY TO HARD-CODE `gather.py` AND GO
    BLIND WHEN A SECOND GATHER MODULE LANDED.** `wiring.details()` had it as
    its write-site exclusion, where the consequence was that a second module
    WRITING a detail key registered as a READ and silently closed a live gap.
    Here the consequence is the mirror: `positions.py` observes ten quantities
    and this walk could not see one of them, so `UNSCORED` declared ten
    position facts that the tool reported as *declared and never observed*.

    Both are the same root — *the set of files that GATHER is a fact about the
    pipeline, not a constant* — and both now read it from
    `reach.STAGE_OF_FILE`, which `reach.unaccounted_modules()` already forces
    to be complete. ⚠️ The import is local because `reach` imports this
    package too, and both are instruments rather than stages.
    """
    from .reach import STAGE_OF_FILE
    names = sorted(n for n, stage in STAGE_OF_FILE.items()
                   if stage == "GATHER")
    out = []
    for name in names:
        path = _HERE / name
        if path.is_file():
            out.append(path.read_text())
    return out


def observe_sites(source: Optional[str] = None) -> Dict[str, Any]:
    """Every `log.observe` in a GATHER-stage module, keyed by quantity."""
    sources = ([source] if source is not None else _gather_stage_sources())
    w = _ObserveWalker()
    for src in sources:
        w.visit(ast.parse(src))

    by_q: Dict[str, Dict[str, Any]] = {}
    for s in w.sites:
        row = by_q.setdefault(s["quantity"], {
            "sites": [], "scored": False, "readers": [], "detail": set()})
        row["sites"].append({"where": s["where"], "line": s["line"],
                             "reader": s["reader"], "scored": s["scored"]})
        row["scored"] = row["scored"] or s["scored"]
        if s["reader"] and s["reader"] not in row["readers"]:
            row["readers"].append(s["reader"])
        row["detail"].update(s["detail"])
    for row in by_q.values():
        row["detail"] = sorted(row["detail"])
        row["readers"] = sorted(row["readers"])
    return {"by_quantity": by_q, "unresolved": w.unresolved,
            "n_sites": len(w.sites)}


# ─────────────────────────────────────────────────────────────────────────────
# 5. The raster walk — which image does a reader actually measure?
# ─────────────────────────────────────────────────────────────────────────────

def _fn_node(path: pathlib.Path, name: str) -> Optional[ast.AST]:
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError, UnicodeDecodeError):       # noqa: BLE001
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name == name:
            return node
    return None


def _raster_of(rel: str, fn_name: str) -> Dict[str, Any]:
    """Which raster `rel::fn_name` measures — DERIVED from its own AST.

    ⚠️ The four cases are distinguishable and the distinction matters:

    * `x.image_no_staff if ... is not None else x.image` -> ERASED_ELSE_INTACT.
      **A SILENT FALLBACK**: which raster answered is a runtime fact and
      nothing on the return value says which.
    * only `image_no_staff` -> ERASED.
    * only `.image` -> INTACT, unless the function calls `erase_staff_lines`
      itself, which makes it OWN_ERASURE — a THIRD raster, produced by a
      different algorithm from `staff_line_removal`'s.
    * neither -> PAGE_RASTER if it names a page ink array, else NO_RASTER.
    """
    path = _OMR / rel
    fn = _fn_node(path, fn_name)
    if fn is None:
        return {"variant": None, "why": f"{rel}::{fn_name} not found"}

    attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    calls = {n.func.id for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}

    # ⚠️⚠️ `getattr(cell, "image_no_staff", None)` IS NOT AN `ast.Attribute`,
    # and missing it reported `gather._ink_components` — the one rung that
    # reads ONLY the erased raster — as touching NO RASTER AT ALL. An
    # attribute-only walk answers confidently and wrongly for exactly the
    # readers careful enough to use `getattr`.
    attrs |= {c.args[1].value for c in ast.walk(fn)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
              and c.func.id == "getattr" and len(c.args) > 1
              and isinstance(c.args[1], ast.Constant)
              and isinstance(c.args[1].value, str)}

    has_erased = "image_no_staff" in attrs
    has_intact = "image" in attrs

    # The fallback is an IfExp whose orelse is `.image` and whose body is
    # `.image_no_staff` (or a `getattr(..., "image_no_staff", None)`).
    fallback = any(
        isinstance(n, ast.IfExp)
        and "image_no_staff" in {a.attr for a in ast.walk(n.body)
                                 if isinstance(a, ast.Attribute)}
        | {c.args[1].value for c in ast.walk(n.body)
           if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
           and c.func.id == "getattr" and len(c.args) > 1
           and isinstance(c.args[1], ast.Constant)}
        and "image" in {a.attr for a in ast.walk(n.orelse)
                        if isinstance(a, ast.Attribute)}
        for n in ast.walk(fn))

    if fallback:
        variant, why = ERASED_ELSE_INTACT, "a silent `no_staff else image`"
    elif has_erased and not has_intact:
        variant, why = ERASED, "reads `image_no_staff` and refuses otherwise"
    elif has_intact and not has_erased:
        if "erase_staff_lines" in calls:
            variant, why = OWN_ERASURE, "reads `.image` and erases lines ITSELF"
        else:
            variant, why = INTACT, "reads `.image`"
    elif has_intact and has_erased:
        variant, why = ERASED_ELSE_INTACT, "names both images"
    elif {"page_ink", "page", "binary", "rgb"} & names:
        variant, why = PAGE_RASTER, "measures a whole-page array"
    else:
        variant, why = NO_RASTER, "names no raster"
    return {"variant": variant, "why": why,
            "at": f"{rel}::{fn_name}", "line": getattr(fn, "lineno", None)}


#: Calls that hand back a PDF image's own dictionary — the one place the
#: SOURCE's native pixel dimensions are available.
_IMAGE_INFO_CALLS = ("get_image_info", "get_images")

#: Keys on that dictionary which ARE a native resolution.
_NATIVE_KEYS = ("width", "height", "xres", "yres", "bpc")


#: Directories under `data/` that would hold an accumulated store if one
#: existed. ⚠️ DERIVED BY LISTING, not asserted: the check reports what IS
#: there, so the claim *"no store of measured geometry"* is falsifiable by
#: anyone adding one.
def across_documents() -> Dict[str, Any]:
    """Does anything accumulate MEASURED GEOMETRY across documents — and is the
    obvious conditioning variable even reachable where it would be populated?

    ⚠️⚠️ SEAN, 2026-09-17: *"We need every bit of information gathered and
    stored in one place where the different stages can continue to learn how to
    better identify as it processes all of the information."* The aggregate is
    the point — recording where fermatas fall is what later lets an unnamed
    blob three spaces above the top staff at a bar end be scored as
    fermata-shaped. A per-run record cannot do that; only a store can.

    ⚠️ AND `publisher` IS THE NATURAL CONDITIONING VARIABLE AND IS UNREACHABLE
    AT GATHER. The catalog holds it — but on `entries`, NOT on the `editions`
    map, so a reader that went to `editions` would find nothing and conclude
    it was absent. This reports both, with counts, so neither half is taken on
    trust.
    """
    data = _ROOT / "data"
    dirs = sorted(p.name for p in data.iterdir()
                  if p.is_dir() and not p.name.startswith(".")) \
        if data.is_dir() else []

    # Is `publisher` read anywhere GATHER can see?
    gather_src = (_HERE / "gather.py").read_text()
    tree = ast.parse(gather_src)
    code_hits = sum(1 for n in ast.walk(tree)
                    if (isinstance(n, ast.Constant)
                        and isinstance(n.value, str)
                        and "publisher" in n.value.lower())
                    or (isinstance(n, (ast.Name, ast.Attribute))
                        and "publisher" in (getattr(n, "id", "")
                                            or getattr(n, "attr", "")).lower()))

    cat = _ROOT / "data/score-library/catalog.json"
    catalog: Dict[str, Any] = {"present": cat.is_file()}
    if cat.is_file():
        try:
            doc = json.loads(cat.read_text())
            eds = [e for e in doc.get("entries", [])
                   if e.get("kind") == "edition"]
            catalog.update(
                editions=len(eds),
                with_publisher=sum(1 for e in eds if e.get("publisher")),
                distinct_publishers=len({e["publisher"] for e in eds
                                         if e.get("publisher")}),
                with_image_type=sum(1 for e in eds if e.get("image_type")),
                # ⚠️ The field is on `entries`; the `editions` MAP does not
                # carry it, and that is where a reader would look first.
                on_editions_map=sorted(
                    (list(doc.get("editions", {}).values()) or [{}])[0].keys()),
            )
        except (OSError, ValueError):                        # noqa: BLE001
            catalog["present"] = False
    return {"data_dirs": dirs, "publisher_in_gather_code": code_hits,
            "catalog": catalog}


def native_resolution() -> Dict[str, Any]:
    """Does anything read the SOURCE's native pixel dimensions?

    ⚠️⚠️ `OMR_DPI` IS A CONSTANT — 300 on the backend, 600 on the CLI — applied
    to every document, and `render_page(..., dpi=dpi)` takes it from an
    argument no call site derives from the PDF. A SCANNED plate has a native
    resolution fixed at scan time: rendering above it is pure upsampling, and
    rendering below it discards plate that is there. A VECTOR page has none and
    genuinely renders sharper. **The two want opposite things from one
    constant.** (`A-INK-2`.)

    ⚠️⚠️ AND THE CLASSIFIER THAT WOULD ROUTE THEM ALREADY EXISTS AND ALREADY
    OPENS THE DICTIONARY. `input_domain._classify_page` — `OMR_WEIGHT_ROUTING`'s
    shipped, measured domain test — calls `get_image_info()` and reads only
    `bbox` (for coverage), and `get_images(full=True)` to fetch the `Filter`.
    `width` and `height` sit in the same dicts, untouched. *The value existed
    and nothing read it*, in the one module already asking the adjacent
    question.

    ⚠️ THE POSITIVE CONTROL IS THE POINT: this walk reports the keys that ARE
    read. A walker that could not see a subscript would report every key as
    unread and its zero for `width` would mean nothing — so the answer is a
    zero BESIDE a non-empty list, never a bare zero.

    ⚠️ THE CONTROL IS MODULE-SCOPED, NOT DICT-SCOPED, AND SAYING SO IS PART OF
    IT. `keys_they_read` is every string-constant subscript ANYWHERE in a
    module that opens the image dictionary, so it includes keys belonging to
    other dicts entirely (`direction_text` subscripts its own reader report).
    Narrowing it to *keys of THIS dict* would need a hand list of what a
    PyMuPDF image dict carries — a hand list inside a derivation, which is the
    thing this repo has been bitten by. The looser control still does its one
    job: it proves the walker can SEE a subscript, so the zero for `width` is
    the absence of a read and not the absence of a walker.
    """
    read: Dict[str, List[str]] = {}
    callers: List[str] = []
    for path in sorted(_OMR.rglob("*.py")):
        rel = str(path.relative_to(_OMR))
        if "__pycache__" in rel or "/tests/" in rel or rel.startswith("tests/"):
            continue
        try:
            tree = ast.parse(path.read_text())
        except (OSError, SyntaxError, UnicodeDecodeError):    # noqa: BLE001
            continue
        calls = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)}
        if not (set(_IMAGE_INFO_CALLS) & calls):
            continue
        callers.append(rel)
        # Every string-constant subscript and `xref_get_key` literal in the
        # module: what it actually asks the image dictionary for.
        for n in ast.walk(tree):
            if (isinstance(n, ast.Subscript)
                    and isinstance(n.slice, ast.Constant)
                    and isinstance(n.slice.value, str)):
                read.setdefault(n.slice.value, []).append(rel)
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "xref_get_key"):
                for a in n.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        read.setdefault(a.value, []).append(rel)
    return {
        "modules_opening_the_image_dict": sorted(callers),
        "keys_they_read": {k: sorted(set(v)) for k, v in sorted(read.items())},
        "native_keys_read": sorted(k for k in _NATIVE_KEYS if k in read),
        "native_keys_unread": sorted(k for k in _NATIVE_KEYS if k not in read),
    }


def _resolution_of(rel: str, fn_name: str) -> str:
    """`LETTERBOXED` when the reader renormalises to its own input size.

    ⚠️ DERIVED from the entry point's own signature and body — a reader that
    names `imgsz` resizes whatever it is handed, so the render DPI is NOT what
    it measures. Everything else measures the raster's own pixels.
    """
    fn = _fn_node(_OMR / rel, fn_name)
    if fn is None:
        return NO_RASTER
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    names |= {a.arg for a in getattr(fn.args, "args", ())}
    names |= {a.arg for a in getattr(fn.args, "kwonlyargs", ())}
    return LETTERBOXED if "imgsz" in names else DIRECT_PIXELS


def rasters() -> Dict[str, Any]:
    """Per READERS member: the raster(s) it measures, derived."""
    try:
        from .record import READERS
        members = sorted(n for n in dir(READERS) if n.isupper())
    except Exception:                                        # noqa: BLE001
        members = sorted(READER_RASTER)

    out: Dict[str, Any] = {}
    missing: List[str] = []
    for m in members:
        if m not in READER_RASTER:
            missing.append(m)
            continue
        entry = READER_RASTER[m]
        if entry is None:
            out[m] = {"variants": [{"variant": NO_RASTER,
                                    "why": "declared: touches no raster",
                                    "at": None}],
                      "resolution": NO_RASTER}
            continue
        found = [_raster_of(*entry)]
        found += [_raster_of(*e) for e in READER_RASTER_ALSO.get(m, ())]
        res = {_resolution_of(*e)
               for e in (entry, *READER_RASTER_ALSO.get(m, ()))}
        # ⚠️ A reader whose entry points DISAGREE is reported as letterboxed —
        # the stronger claim — rather than averaged into a word that is true
        # of neither.
        out[m] = {"variants": found,
                  "resolution": (LETTERBOXED if LETTERBOXED in res
                                 else DIRECT_PIXELS)}
    return {"by_reader": out, "undeclared_readers": missing,
            "native": native_resolution()}


# ─────────────────────────────────────────────────────────────────────────────
# 6. The join — the three questions, per notation family
# ─────────────────────────────────────────────────────────────────────────────

#: A detail key that states a side or a band. ⚠️ SEPARATE FROM A POSITION FACT
#: AND THE SEPARATION IS THE FINDING — see `side_is_not_a_ruler`.
#: ⚠️ `side` ONLY, and `placement` is deliberately NOT here. A `side` is read
#: off the CLASS NAME (`fermataBelow`) and therefore fails together with the
#: classification; a `placement` is DERIVED FROM THE BAND by measurement, so it
#: has the opposite provenance. Folding them made the `direction` family report
#: "the class name states a SIDE" about a word that is not in the class space
#: at all — a confident wrong label produced by the instrument.
_SIDE_KEYS = ("side",)
_BAND_KEYS = ("band_offset_spaces", "position_in_candidate")
#: A band-derived above/below. Real evidence, and far too coarse to carry a
#: distribution — reported apart from both of the above.
_COARSE_BAND_KEYS = ("placement",)

# ─────────────────────────────────────────────────────────────────────────────
# LOCATION vs POSITION — a grading of what is there, NEVER an exemption
#
# ⚠️⚠️ A LOCATION IS NOT A POSITION, and the difference is whether it COMPOSES
# ACROSS DOCUMENTS. Sean's aggregate question — *where do things fall on THIS
# publisher's plates* — can only be asked of a quantity that means the same
# thing on two different pages. A staff-space float does; a raw page pixel does
# not, because pages differ in size and in render DPI; a CANONICAL CELL box
# does not either, and worse: `Q.ONSET_COLUMN` already paid for that one —
# canonical x is measured inside ONE cell rescaled so the staff span is
# constant, so **two staves' canonical frames coincide by construction** and
# agreeing there is evidence of nothing.
#
# ⚠️ This grades a family that HAS something; it never excuses one that has
# nothing. Every family without a staff-grid position is a finding regardless
# of what it scores here.
# ─────────────────────────────────────────────────────────────────────────────

#: A staff-space float. Comparable across staves, pages and documents.
COMPOSES = "staff_relative"
#: Page pixels. A LOCATION on one raster; not comparable to another page's.
PAGE_ONLY = "page_pixels"
#: A canonical-cell box. Not comparable across staves, let alone documents.
CELL_ONLY = "canonical_cell"

_STAFF_RELATIVE_KEYS = ("band_offset_spaces", "position_in_candidate",
                        "width_spaces", "height_spaces", "open_spaces",
                        "outline_rms_spaces", "half_step")
_PAGE_KEYS = ("bbox_page_px", "x_center_page", "y_center_page", "y_center_px")
_CELL_KEYS = ("x0", "x1", "y0", "y1", "x_center", "y_center")


def _location_grade(detail: Sequence[str]) -> List[str]:
    """What FRAMES this row's location is expressed in — all of them."""
    d = set(detail)
    out: List[str] = []
    if d & set(_STAFF_RELATIVE_KEYS):
        out.append(COMPOSES)
    if d & set(_PAGE_KEYS):
        out.append(PAGE_ONLY)
    if d & set(_CELL_KEYS):
        out.append(CELL_ONLY)
    return out

#: Rows `gather_detections` emits for EVERY detection, with no class guard —
#: so any family whose ink comes from the detector has a shape fact whether or
#: not its own decision declares one.
#:
#: ⚠️⚠️ WITHOUT THIS THE EXEMPLAR FAMILY REPORTS `shape: NO`, and the reason is
#: worth keeping: `consequences.restate_pitch` reads a RULER and a CLEF and
#: never a class, which is precisely the property this module exists to
#: celebrate. Following only the decision chain therefore answers *"the note
#: family captures no shape"* — true of the pitch rule and false of the
#: pipeline, because `adjudicate_duration` reads the class on a different
#: quantity under a different family.
#:
#: ⚠️ DECLARED, and the unconditionality is what makes it safe. A test
#: (`test_the_universal_detector_rows_have_no_class_guard`) re-reads
#: `gather.py` and fails if either row ever grows an `if` on the class —
#: `Q.NOTEHEAD_CLASS` sits three lines below them and HAS one, which is the
#: positive control that the test can tell the two apart.
UNIVERSAL_DETECTOR_ROWS = ("GLYPH_BOX", "GLYPH_CONF")


def _family_quantities() -> Dict[str, Dict[str, Any]]:
    """Family -> the quantities its deciding rule is DRIVEN BY and READS.

    ⚠️ DERIVED FROM THE DECLARATIONS, not from a list: `export.FAMILIES` names
    the family's deciding quantity, `adjudicate.REGISTRY` gives that decision's
    `subjects_from` (the ink population it decides OVER) and `wants`
    (everything it declares it reads).

    ⚠️⚠️ AND TWO FAMILIES CANNOT BE ANSWERED THAT WAY, WHICH IS ITSELF THE
    REGISTER'S §3.3 ARRIVING FROM A NEW DIRECTION. `note`'s quantity is
    `Q.PITCH`, produced by an EVALUATE consequence — and **EVALUATE declares
    only `cause` and `effect`**, never what it reads. So the exemplar family,
    the one whose position fact this whole module is named after, is the one
    whose declaration chain structurally cannot state it. Its reads are taken
    from the rule's BODY instead, and the report says so rather than quietly
    presenting a body-read as a declaration.
    """
    from . import pipeline                     # noqa: F401  (fills REGISTRY)
    from . import adjudicate as A
    from . import consequences as C
    from . import evaluate as EV
    from . import export as E

    # EVALUATE rule bodies: `Q.X` anywhere inside the decorated function.
    body_reads: Dict[str, Set[str]] = {}
    try:
        tree = ast.parse((_HERE / "consequences.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                qs = {q for n in ast.walk(node) if (q := _q_name(n))}
                if qs:
                    body_reads[node.name] = qs
    except (OSError, SyntaxError):                           # noqa: BLE001
        pass

    # ⚠️⚠️ EVERY RULE WITH THIS EFFECT, NOT THE LAST ONE SEEN. `restate_pitch`
    # and `move_glyph` BOTH have `effect=Q.PITCH`, and a dict keyed on the
    # effect silently kept whichever was declared second — so the `note`
    # family, the exemplar this module is named after, reported its reads as
    # `move_glyph`'s (`Q.GLYPH_BAND_DISTANCE`) and came out with **no shape
    # fact and no position fact**. The first run of this module did exactly
    # that, and the table looked entirely plausible.
    effect_to_rules: Dict[str, List[str]] = {}
    for r in EV.RULES:
        fn = getattr(r, "fn", None)
        name = (getattr(fn, "__name__", None)
                or str(getattr(r, "consequence", "")))
        effect_to_rules.setdefault(str(getattr(r, "effect", "")), []).append(name)

    out: Dict[str, Dict[str, Any]] = {}
    for family, (q, _prefixes, _counters) in sorted(E.FAMILIES.items()):
        qname = str(q)
        dec = A.REGISTRY.get(qname)
        if dec is not None:
            reads = {str(w).upper() for w in (dec.wants or ())}
            if dec.subjects_from:
                reads.add(str(dec.subjects_from).upper())
            out[family] = {"quantity": qname, "via": "declared",
                           "decision": qname, "reads": sorted(reads)}
            continue
        rule_fns = [f for f in effect_to_rules.get(qname, ()) if f in body_reads]
        if rule_fns:
            reads = set()
            for f in rule_fns:
                reads |= body_reads[f]
            out[family] = {"quantity": qname, "via": "rule_body",
                           "decision": "+".join(sorted(rule_fns)),
                           "reads": sorted(reads)}
            continue
        # A family whose quantity IS a gather quantity (`rest`): the ink row
        # is the whole answer and there is nothing declared to follow.
        out[family] = {"quantity": qname, "via": "gather_only",
                       "decision": None, "reads": [qname.upper()]}
    return out


def families() -> Dict[str, Any]:
    """The per-family answer to all three questions."""
    obs = observe_sites()
    ras = rasters()
    fams = _family_quantities()
    by_q = obs["by_quantity"]

    from . import export as E

    rows: List[Dict[str, Any]] = []
    for family, info in sorted(fams.items()):
        reads = [q for q in info["reads"] if q in by_q]
        # ⚠️ Detector-sourced families get the universal rows. `FAMILIES`'
        # own prefix column is what says a family HAS detector ink; the
        # `direction` family declares none, deliberately (a direction word is
        # not in the 208-class space at all), so it gains nothing here and
        # its `shape: NO` stands as a real finding rather than an artefact.
        prefixes = E.FAMILIES.get(family, (None, (), ()))[1]
        if prefixes:
            reads += [q for q in UNIVERSAL_DETECTOR_ROWS
                      if q in by_q and q not in reads]

        shape = [q for q in reads if by_q[q]["scored"]]
        # ⚠️ ITS OWN INK, NOT SOMEBODY ELSE'S. See `UNSCORED`'s header: keyed
        # on "does this decision read A position fact", `slur` and `tie` came
        # out MEASURED off the NOTEHEADS' positions.
        position = [q for q in reads
                    if _is_position(q) and family in _families_of(q)]
        # A position declared for this family that its decision cannot reach.
        position_unread = [q for q in UNSCORED
                           if _is_position(q) and family in _families_of(q)
                           and q not in reads]

        # ⚠️ REPORTED APART FROM `position`, NEVER FOLDED IN.
        in_class = sorted({q for q in reads
                           if set(by_q[q]["detail"]) & set(_SIDE_KEYS)})
        band = sorted({q for q in reads
                       if set(by_q[q]["detail"]) & set(_BAND_KEYS)})
        coarse = sorted({q for q in reads
                         if set(by_q[q]["detail"]) & set(_COARSE_BAND_KEYS)})

        variants: Dict[str, List[str]] = {}
        for q in reads:
            for r in by_q[q]["readers"]:
                for v in ras["by_reader"].get(r, {}).get("variants", ()):
                    variants.setdefault(v["variant"] or "UNRESOLVED",
                                        []).append(f"{q}/{r}")
        records_image = sorted({q for q in reads
                                if "staff_lines_erased" in by_q[q]["detail"]
                                or "image" in by_q[q]["detail"]})

        rows.append({
            "family": family, "quantity": info["quantity"],
            "via": info["via"], "decision": info["decision"],
            "reads_gathered": sorted(reads),
            "shape": shape,
            "position": position,
            "position_declared_but_unread": position_unread,
            "side_in_class_name": in_class,
            "band_as_a_detail": band,
            "coarse_band_only": coarse,
            "rasters": {k: sorted(set(v)) for k, v in sorted(variants.items())},
            "records_its_raster": records_image,
            # ⚠️ A GRADING OF WHAT IS THERE, NEVER AN EXEMPTION.
            #
            # ⚠️ A POSITION QUANTITY'S *VALUE* IS THE STAFF-RELATIVE FACT, and
            # grading only its DETAIL keys got `clef` and `key` wrong: both
            # carry a staff-grid float as the value and cell-frame keys beside
            # it, so they read as `canonical/page` — *"does not compose"* about
            # the two families that do.
            "location_frames": sorted(
                {g for q in reads for g in _location_grade(by_q[q]["detail"])}
                | ({COMPOSES} if position else set())),
        })
    return {"rows": rows, "observe": obs, "rasters": ras}


def report() -> Dict[str, Any]:
    rep = families()
    by_q = rep["observe"]["by_quantity"]

    # Every scoreless observed quantity must be classified.
    scoreless = sorted(q for q, v in by_q.items() if not v["scored"])
    rep["unclassified_scoreless"] = [q for q in scoreless if q not in UNSCORED]
    rep["scoreless"] = scoreless

    # ⚠️ THE ONE-SIDED WARNING, COMPUTED RATHER THAN ASSERTED. A side read off
    # the class name is NOT an independent witness: if the classification is
    # wrong the side is wrong with it, which is this repo's correlated-
    # witnesses hazard with the correlation running through the class name.
    rep["side_is_not_a_ruler"] = sorted(
        {q for q, v in by_q.items() if set(v["detail"]) & set(_SIDE_KEYS)})

    rep["across_documents"] = across_documents()
    rep["controls"] = controls(rep)
    rep["problems"] = problems(rep)
    rep["unaccounted"] = unaccounted(rep["problems"])
    rep["stale_gaps"] = stale_gaps(rep["problems"])
    return rep


def controls(rep: Dict[str, Any]) -> Dict[str, int]:
    """⚠️⚠️ THE POSITIVE CONTROLS — why a clean run means anything.

    Each is a count of cases the question found HEALTHY. A zero does not mean
    the pipeline is clean; it means the question never reached its subject.
    `--check` exits non-zero on any zero here BEFORE it reads a finding.
    """
    by_q = rep["observe"]["by_quantity"]
    ras = rep["rasters"]["by_reader"]
    return {
        # Q1: quantities observed WITH a confidence.
        "shape_quantities_with_a_score":
            sum(1 for v in by_q.values() if v["scored"]),
        "families_with_a_shape_fact":
            sum(1 for r in rep["rows"] if r["shape"]),
        # Q2: the exemplar has to be found, or the join is broken.
        "staff_grid_position_quantities":
            sum(1 for k, (kind, _r, _f) in UNSCORED.items()
                if kind == STAFF_GRID_POSITION and k in by_q),
        "families_with_a_position_fact":
            sum(1 for r in rep["rows"] if r["position"]),
        # Q3: rasters actually resolved out of reader source.
        "readers_whose_raster_resolved":
            sum(1 for v in ras.values()
                if all(x["variant"] for x in v["variants"])),
        "readers_that_touch_a_raster":
            sum(1 for v in ras.values()
                if any(x["variant"] not in (NO_RASTER, None)
                       for x in v["variants"])),
        # Q4: the walk has to be able to SEE a key, or its zero for `width`
        # means nothing. This is the count of keys it DID find being read.
        "image_dict_keys_seen_being_read":
            len(rep["rasters"]["native"]["keys_they_read"]),
        "modules_that_open_the_image_dict":
            len(rep["rasters"]["native"]["modules_opening_the_image_dict"]),
        "readers_whose_resolution_resolved":
            sum(1 for v in ras.values() if v.get("resolution")),
        # the walk itself
        "observe_sites_walked": rep["observe"]["n_sites"],
    }


def problems(rep: Dict[str, Any]) -> List[str]:
    out: List[str] = []

    # ⚠️⚠️ THE HARD TIER FIRST, AND IT IS NOT ON `KNOWN_GAPS`. A `Q` member
    # with no declared claim kind is `record.claims_unaccounted()`'s finding,
    # not this table's, and it has no accounted tier by design: a claim kind
    # costs one word, so an entry excusing one could only ever record that
    # somebody declined to think. It is at ZERO when this lands, which is what
    # lets `--check` be a gate — the thing `no_producer --check` cannot be.
    out += [f"CLAIM-UNDECLARED {p}" for p in record_claims_unaccounted()]

    # The CONSTRAINT between the two tables. A real disagreement lands on
    # KNOWN_GAPS with its reason; it is never fixed by widening the constraint.
    out += claim_consistency()

    for r in rep["rows"]:
        if r["position"]:
            continue
        # ⚠️⚠️ "THERE IS NONE" AND "THERE IS ONE AND NOTHING READS IT" ARE
        # DIFFERENT FINDINGS AND DIFFERENT REPAIRS — write the adjudicator's
        # input against wire the input it already has. Until 2026-09-17 they
        # could not be different, because no family had a position its
        # decision did not read; `positions.py` landed ten producers with no
        # consumers and this branch would have gone on reporting *"has no
        # staff-grid position fact of its own"* about eleven families that now
        # have one. That is `fixed-then-kept-open-in-prose`, the failure this
        # repo has recorded three times, arriving inside the instrument built
        # to catch it. The UNREAD-POSITION finding below is the accurate
        # report for these rows, so this one stands down rather than
        # double-counting one fact in two vocabularies.
        if r["position_declared_but_unread"]:
            continue
        # ⚠️ THE SHARPEST CASE FIRST, because it is the one that reads as
        # healthy: a family that reads SOMEBODY ELSE'S position fact has the
        # word "position" all over its declaration and still has no ruler on
        # its own ink.
        borrowed = [q for q in r["reads_gathered"] if _is_position(q)]
        if borrowed:
            whose = ", ".join(
                f"Q.{q} (the `{'/'.join(_families_of(q))}` family's)"
                for q in borrowed)
            extra = f" — it reads {whose}, which is not a fact about its OWN ink"
        elif r["side_in_class_name"]:
            extra = (" — the class name states a SIDE "
                     f"({', '.join(r['side_in_class_name'])}), which is NOT "
                     "an independent witness: it fails together with the "
                     "classification it is read off")
        elif r["band_as_a_detail"]:
            extra = (" — a band offset exists as a DETAIL of a scored row "
                     f"({', '.join(r['band_as_a_detail'])})")
        elif r["coarse_band_only"]:
            extra = (" — its only staff-relative fact is a band-derived "
                     f"above/below ({', '.join(r['coarse_band_only'])}), which "
                     "is far too coarse to carry a distribution")
        else:
            extra = ""
        # ⚠️ THE GRADING RIDES ALONG AND DOES NOT SOFTEN THE FINDING. A family
        # whose ink is located only in page pixels or only in a canonical cell
        # has a LOCATION and not a POSITION, and neither composes across
        # documents — which is a second, distinct fact about the same row.
        frames = r["location_frames"]
        if frames and COMPOSES not in frames:
            extra += (f" — and its ink is located only in {'/'.join(frames)}, "
                      f"which does not compose across documents")
        out.append(f"POSITION {r['family']} has no staff-grid position fact of "
                   f"its own{extra}")

    # ⚠️ ONE PROBLEM PER READER, NOT PER ROW. A silent fallback is one repair
    # wherever it is read from; reporting it per quantity would inflate the
    # list and read as several separate faults.
    for reader, v in sorted(rep["rasters"]["by_reader"].items()):
        used = any(reader in q["readers"]
                   for q in rep["observe"]["by_quantity"].values())
        if not used:
            continue
        ambiguous = [x for x in v["variants"]
                     if x["variant"] == ERASED_ELSE_INTACT]
        if not ambiguous:
            continue
        recorded = all(
            "staff_lines_erased" in q["detail"]
            for q in rep["observe"]["by_quantity"].values()
            if reader in q["readers"])
        if recorded:
            continue
        out.append(f"IMAGE {reader} falls back silently "
                   f"({'; '.join(x['at'] for x in ambiguous)}) and its rows do "
                   f"not record which raster answered")

    # `CV_INK` is not a fallback but is reported for the reason in KNOWN_GAPS.
    for reader, v in sorted(rep["rasters"]["by_reader"].items()):
        if reader != "CV_INK":
            continue
        recorded = all(
            "staff_lines_erased" in q["detail"]
            for q in rep["observe"]["by_quantity"].values()
            if reader in q["readers"])
        if not recorded:
            out.append("IMAGE CV_INK measures the erased raster and its rows "
                       "do not say so, so an INK row and a DETECTOR row of the "
                       "same ink cannot be told apart by raster")

    for r in rep["rows"]:
        for q in r["position_declared_but_unread"]:
            out.append(f"UNREAD-POSITION Q.{q} is the `{r['family']}` "
                       f"family's own staff-grid position and its deciding "
                       f"rule ({r['decision']}) does not read it")

    # Every family a position fact names must exist.
    known = {r["family"] for r in rep["rows"]}
    for q in sorted(UNSCORED):
        if not _is_position(q):
            continue
        # ⚠️ A POSITION QUANTITY NAMING NO FAMILY IS ALSO A FINDING. The third
        # field is what makes "does this decision read A position" into "does
        # it read ITS OWN", and an empty one silently restores the weaker
        # question this table grew the field to stop asking.
        fams = _families_of(q)
        if not fams:
            out.append(f"UNRESOLVED Q.{q} is a staff-grid position naming NO "
                       f"family — say whose ink it measures")
        for fam in fams:
            if fam not in known:
                out.append(f"UNRESOLVED Q.{q} names family '{fam}', which is "
                           f"not in export.FAMILIES")

    # ⚠️ ONE FINDING, NOT ONE PER READER. Every reader is handed the same
    # constant, so this is one repair at the render, not fourteen.
    nat = rep["rasters"]["native"]
    if nat["native_keys_unread"] and nat["modules_opening_the_image_dict"]:
        out.append(
            f"RESOLUTION nothing reads the source's native "
            f"{'/'.join(nat['native_keys_unread'])} anywhere in tools/omr — "
            f"{', '.join(nat['modules_opening_the_image_dict'])} already open "
            f"the image dictionary, and the same walk sees "
            f"{len(nat['keys_they_read'])} other string keys read in those "
            f"modules (including `bbox` and `Filter`, which ARE taken from "
            f"it), so the zero is the walker working. Every reader is handed "
            f"a CONSTANT render DPI whatever the plate holds")

    # ⚠️ ONE FINDING. There is no store, so there is one repair, not one per
    # family — and the conditioning variable being unreachable is part of the
    # same fact rather than a second gap.
    xd = rep["across_documents"]
    cat = xd["catalog"]
    if not xd["publisher_in_gather_code"] and cat.get("present"):
        out.append(
            f"CROSS-DOCUMENT nothing accumulates measured geometry across "
            f"documents — `data/` holds {', '.join(xd['data_dirs'])} and no "
            f"store of positions — and `publisher`, the conditioning variable "
            f"the aggregate would need, appears in NO code in gather.py while "
            f"the catalog carries it on {cat.get('with_publisher')} of "
            f"{cat.get('editions')} editions "
            f"({cat.get('distinct_publishers')} distinct)")

    for q in rep["unclassified_scoreless"]:
        out.append(f"UNCLASSIFIED Q.{q} is observed with no score and is in "
                   f"neither UNSCORED nor KNOWN_GAPS — say what kind of fact "
                   f"it is (a fourth staff-grid position would land here)")
    for u in rep["observe"]["unresolved"]:
        out.append(f"UNRESOLVED observe site {u['where']}:{u['line']} — its "
                   f"{u['shape']} could not be derived")
    for m in rep["rasters"]["undeclared_readers"]:
        out.append(f"UNRESOLVED READERS.{m} is not in READER_RASTER — say "
                   f"which raster it measures, or that it measures none")
    for reader, v in sorted(rep["rasters"]["by_reader"].items()):
        for x in v["variants"]:
            if x["variant"] is None:
                out.append(f"UNRESOLVED READERS.{reader} -> {x['why']}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 7. The report
# ─────────────────────────────────────────────────────────────────────────────

_SHORT = {INTACT: "intact", ERASED: "erased",
          ERASED_ELSE_INTACT: "erased?intact", OWN_ERASURE: "own-erase",
          PAGE_RASTER: "page", NO_RASTER: "-"}


def render(rep: Dict[str, Any]) -> str:
    lines: List[str] = []
    A = lines.append
    A("SHAPE · POSITION · IMAGE · RESOLUTION — what we capture about ink")
    A("=" * 78)
    A("")
    A(f"{'family':14s} {'shape':>5s}  {'position':>8s}  {'location':>9s}  "
      f"{'side':>4s}  rasters")
    A("-" * 78)
    for r in rep["rows"]:
        shape = "yes" if r["shape"] else "NO"
        if r["position"]:
            pos = "MEASURED"
        elif r["band_as_a_detail"]:
            pos = "band*"
        else:
            pos = "NONE"
        loc = ("composes" if COMPOSES in r["location_frames"]
               else "/".join({"canonical_cell": "cell", "page_pixels": "page"}.get(f, f)
                            for f in r["location_frames"])
               or "-")
        side = "cls" if r["side_in_class_name"] else "-"
        ras = ",".join(_SHORT.get(k, k) for k in r["rasters"]
                       if k != NO_RASTER) or "-"
        A(f"{r['family']:14s} {shape:>5s}  {pos:>8s}  {loc:>9s}  "
          f"{side:>4s}  {ras}")
    A("")
    A("  shape    = an observed quantity carrying the detector's confidence")
    A("  position = a staff-grid coordinate, scoreless, from its own reader")
    A("  band*    = a staff-relative offset, but as a DETAIL of a SCORED row")
    A("  location = does the ink's frame COMPOSE across documents? page")
    A("             pixels and canonical-cell boxes do not — pages differ in")
    A("             size and dpi, and two staves' canonical frames coincide")
    A("             BY CONSTRUCTION. A grading of what is there, NEVER an")
    A("             exemption.")
    A("  side     = above/below read off the CLASS NAME — not a ruler, and")
    A("             not independent of the classification it comes from")
    A("")
    A("  ⚠️⚠️ EVERY `NONE` IS A FINDING AND THERE ARE NO EXEMPTIONS. Sean,")
    A("     2026-09-17: the test is not whether a family needs a position or")
    A("     whether one would compose — it is that we cannot yet know, so we")
    A("     hold on to everything. ⚠️ SCOPED TO DISCOVERY, not a standing")
    A("     claim that the record may grow for ever; the cost to watch is")
    A("     0.6 MB/page (Litolff) and 3.1 MB/page (Breitkopf) for the ink")
    A("     layer alone — `benchmarks/omr-ink-gather-2026-09/FINDINGS.md`.")
    A("")

    A("── THE POSITION FACTS THAT EXIST ───────────────────────────────────")
    for q, (kind, reason, _fam) in sorted(UNSCORED.items()):
        if kind == STAFF_GRID_POSITION:
            A(f"  Q.{q}")
            A(f"      {reason}")
    A("")

    A("── WHICH RASTER EACH READER MEASURES (derived from its own source) ──")
    for reader, v in sorted(rep["rasters"]["by_reader"].items()):
        used = any(reader in q["readers"]
                   for q in rep["observe"]["by_quantity"].values())
        if not used:
            continue
        for x in v["variants"]:
            mark = "⚠️" if x["variant"] == ERASED_ELSE_INTACT else "  "
            res = "letterbox" if v.get("resolution") == LETTERBOXED else "px"
            A(f"  {mark} {reader:16s} {_SHORT.get(x['variant'], '?'):13s} "
              f"{res:9s} {x['at'] or ''}")
    A("")
    A("  ⚠️ `letterbox` vs `px` is QUESTION 4 and must not be flattened: the")
    A("     measured `OMR_IMGSZ` result (*larger is NOT better*) is a fact")
    A("     about the DETECTOR's letterboxing and anchors. A `px` reader has")
    A("     neither, and that finding says nothing about it.")
    A("  ⚠️ `erased?intact` is a SILENT FALLBACK: which raster answered is a")
    A("     runtime fact, and only `Q.STEM`/`Q.BEAM_STROKE` record it.")
    A("  ⚠️ `own-erase` is a THIRD raster — the reader erases the lines")
    A("     itself, by a different algorithm from `staff_line_removal`'s.")
    A("")

    A("── POSITIVE CONTROLS (a zero means the question did not run) ────────")
    for k, v in rep["controls"].items():
        A(f"  {v:6d}  {k}")
    A("")

    A(f"── FINDINGS ({len(rep['problems'])}) ─────────────────────────────")
    for p in rep["problems"]:
        A(f"  {'' if _gap_key(p) else '⚠️ NEW '}{p}")
    if rep["unaccounted"]:
        A("")
        A(f"⚠️⚠️ {len(rep['unaccounted'])} NOT ON KNOWN_GAPS")
    if rep["stale_gaps"]:
        A("")
        A(f"⚠️⚠️ {len(rep['stale_gaps'])} STALE KNOWN_GAPS entries "
          f"(closed, must be deleted): {rep['stale_gaps']}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    rep = report()
    print(json.dumps(rep, indent=2, default=str) if args.json else render(rep))

    if not args.check:
        return 0
    dead = [k for k, v in rep["controls"].items() if not v]
    if dead:
        print(f"\n⚠️⚠️ DEAD QUESTION — control(s) at zero: {dead}. The tool "
              f"did not reach its subject; a clean run means NOTHING.",
              file=sys.stderr)
        return 2
    if rep["unaccounted"] or rep["stale_gaps"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
