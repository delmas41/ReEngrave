"""The record — three row types and one append-only log.

Stdlib only, and it imports nothing from `tools.omr`. Every other module may
import this one without a cycle.

⚠️ THE POINT OF THIS MODULE IS THAT ABSENCE IS A VALUE.

Four mechanisms, and none of them is a convention someone has to remember:

  1. A measurement is a ROW, not a key on a dict, so there is no
     `.get(key, default)` to write. `Log.rows()` returns a tuple and `()` is
     not a reading.
  2. `Abstention` is a distinct row type, so THREE states are distinguishable:
     READ (a reader spoke), DECLINED (a reader looked and refused, with a
     reason), ABSENT (no reader ran). A sentinel collapses all three.
  3. The harness -- not the decision -- fills `Verdict.missing` / `.declined`
     from the difference between what was declared and what the log held.
  4. `Observation.value` has no sentinel. `score=None` means "this reader
     produces no score", which is NOT `score=0.0`.

The live faults that motivate it, all in the existing tree:

  * `system_grouping._assign_groups` writes `group_index = 0` on FOUR
    branches -- three abstentions (`:596` system too small, `:611` no column
    evidence, `:672` no system) and one real reading (`:620`). On the record
    "I declined to partition" and "I read one family" are byte-identical.
  * The three carry dicts (`transcribe.py:4851/4873/4885` read, `:5232-5234`
    written) can never hit, and nothing noticed because a dead `.get()` with
    a good default is indistinguishable from a live one that agrees.
  * `contextual.py:1298` and `:1451` read the provenance tag that guards all
    three circularity refusals as `instrument_source.get(slot, "label")` --
    defaulting to the one tier the refusals admit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import (Any, Dict, Iterator, List, Mapping, Optional, Sequence,
                    Set, Union)

# ─────────────────────────────────────────────────────────────────────────────
# Addressing
# ─────────────────────────────────────────────────────────────────────────────


class Kind(str, Enum):
    """What a row is ABOUT. Ordered coarse to fine."""

    DOCUMENT = "document"
    PAGE = "page"
    SYSTEM = "system"
    STAFF = "staff"
    CELL = "cell"
    GLYPH = "glyph"


_KIND_DEPTH = {
    Kind.DOCUMENT: 0,
    Kind.PAGE: 1,
    Kind.SYSTEM: 2,
    Kind.STAFF: 3,
    Kind.CELL: 4,
    Kind.GLYPH: 5,
}

# The field that each depth consumes, in order.
_KIND_FIELDS = ("page", "system", "staff", "cell", "glyph")


@dataclass(frozen=True, order=True)
class Subject:
    """The address a row is filed under.

    ⚠️ `staff` is the index WITHIN ITS SYSTEM, never the page-wide running
    index. The project has been bitten by exactly that ambiguity:
    `draft_windows` records that `staff_index` is numbered across the PAGE
    (system 1's staves continue the count) while every join must be by
    position within the system. One number, two meanings, and the wrong one
    joins a staff to another instrument's part.
    """

    kind: Kind
    page: int | None = None
    system: int | None = None
    staff: int | None = None
    cell: int | None = None
    glyph: int | None = None

    def __post_init__(self) -> None:
        depth = _KIND_DEPTH[self.kind]
        for i, name in enumerate(_KIND_FIELDS):
            value = getattr(self, name)
            if i < depth and value is None:
                raise ValueError(
                    f"{self.kind.value} subject needs {name}; got None")
            if i >= depth and value is not None:
                raise ValueError(
                    f"{self.kind.value} subject must not carry {name}={value}")

    # ── navigation ──────────────────────────────────────────────────────────

    def parent(self) -> "Subject | None":
        depth = _KIND_DEPTH[self.kind]
        if depth == 0:
            return None
        parent_kind = [k for k, d in _KIND_DEPTH.items() if d == depth - 1][0]
        kw = {name: getattr(self, name) for name in _KIND_FIELDS[: depth - 1]}
        return Subject(parent_kind, **kw)

    def ancestors(self) -> tuple["Subject", ...]:
        out: list[Subject] = []
        node = self.parent()
        while node is not None:
            out.append(node)
            node = node.parent()
        return tuple(out)

    def contains(self, other: "Subject") -> bool:
        """True if `other` is this subject or lies underneath it."""
        if _KIND_DEPTH[other.kind] < _KIND_DEPTH[self.kind]:
            return False
        depth = _KIND_DEPTH[self.kind]
        return all(getattr(other, n) == getattr(self, n)
                   for n in _KIND_FIELDS[:depth])

    def at(self, kind: Kind) -> "Subject | None":
        """This subject's ancestor at `kind`, or itself, or None if finer."""
        if _KIND_DEPTH[kind] > _KIND_DEPTH[self.kind]:
            return None
        if kind == self.kind:
            return self
        kw = {n: getattr(self, n) for n in _KIND_FIELDS[: _KIND_DEPTH[kind]]}
        return Subject(kind, **kw)

    # ── serialisation ───────────────────────────────────────────────────────

    def to_key(self) -> str:
        parts = [self.kind.value] + [
            str(getattr(self, n)) for n in _KIND_FIELDS[:_KIND_DEPTH[self.kind]]
        ]
        return "/".join(parts)

    @staticmethod
    def from_key(key: str) -> "Subject":
        head, *rest = key.split("/")
        kind = Kind(head)
        kw = {n: int(v) for n, v in zip(_KIND_FIELDS, rest)}
        return Subject(kind, **kw)


def meter_at(value, cell_index):
    """The meter in force at one BAR, out of a `Q.METER` verdict's value.

    ⚠️⚠️ A METER IS A PROPERTY OF A RANGE OF BARS, NOT OF A SYSTEM, and this
    helper is where that is expressed. The value carries `segments` -- one
    entry per stretch, each with the `from_cell` it starts at -- so a system
    holding a printed meter CHANGE says so in ONE fact rather than in two that
    can drift apart. Sean, 2026-09-09: *"I don't want the dichotomy of it's a
    system or a group of notes surrounding it. It is both."*

    ⚠️ THE ALTERNATIVE WAS REFUSED ON THIS PROJECT'S OWN HISTORY. Keeping the
    system meter as it was and adding a separate "there is a change at bar N"
    fact is less work and leaves TWO RECORDS OF ONE THING that nothing forces
    to agree -- the shape that let one accuracy figure go stale in three of
    four places, and that made an `instrument_label` audit unable to disagree
    with itself.

    ⚠️ Top-level `numerator`/`denominator` remain and describe the FIRST
    segment, so an unchanged single-meter system serialises exactly as before.
    They are deliberately NOT the thing consumers should read -- a bar past a
    change would get the wrong answer -- which is why every consumer goes
    through here and a test asserts it.
    """
    if not value:
        return None
    segments = value.get("segments")
    if not segments:
        return value
    chosen = None
    for seg in segments:
        if int(seg.get("from_cell") or 0) <= int(cell_index or 0):
            chosen = seg
    # ⚠️ None where NO segment covers this bar, which is a real answer and not
    # a gap: a system may print a meter change at bar 8 while never stating
    # what bars 0-7 were in. "3/4 from bar 8, unknown before" is exactly what
    # a range-scoped fact can say and a system-scoped one cannot.
    return chosen


DOCUMENT = Subject(Kind.DOCUMENT)


def page(p: int) -> Subject:
    return Subject(Kind.PAGE, page=p)


def system(p: int, s: int) -> Subject:
    return Subject(Kind.SYSTEM, page=p, system=s)


def staff(p: int, s: int, st: int) -> Subject:
    return Subject(Kind.STAFF, page=p, system=s, staff=st)


def cell(p: int, s: int, st: int, c: int) -> Subject:
    return Subject(Kind.CELL, page=p, system=s, staff=st, cell=c)


def glyph(p: int, s: int, st: int, c: int, g: int) -> Subject:
    return Subject(Kind.GLYPH, page=p, system=s, staff=st, cell=c, glyph=g)


class Scope(str, Enum):
    """How wide a query reaches from its subject."""

    EXACT = "exact"
    SELF_AND_ANCESTORS = "self_and_ancestors"
    SELF_AND_DESCENDANTS = "self_and_descendants"


class State(str, Enum):
    """⚠️ THREE states, not two. This is the module's reason to exist."""

    READ = "read"          # >= 1 Observation
    DECLINED = "declined"  # 0 Observations, >= 1 Abstention -- a reader looked
    ABSENT = "absent"      # nothing at all -- no reader ran on this subject


class Outcome(str, Enum):
    DECIDED = "decided"
    #: ⚠️ "It is one of these, and I cannot choose between them."
    #:
    #: The state most of a reading is in most of the time, and the one a
    #: decide-or-abstain pipeline cannot express. Narrowing five candidates to
    #: two IS progress, and until this existed it was indistinguishable from
    #: knowing nothing.
    NARROWED = "narrowed"
    ABSTAINED = "abstained"


@dataclass(frozen=True)
class Candidate:
    """One surviving possibility, with the support the decision found for it.

    ⚠️⚠️ `support` IS NOT A PROBABILITY AND MUST NEVER BE TREATED AS ONE.

    It is a sum of signed terms in the deciding function's OWN units. It is not
    normalised, it does not sum to 1 across candidates, and a value of 3.0 does
    not mean "twice as likely" as 1.5. **The ORDER is the claim; the numbers
    are how the order was reached.**

    This project measured what happens when an uncalibrated number is treated
    as evidence: ECE 0.1277, with the top bin promising 0.989 and delivering
    0.692 — failing WORST exactly where a consumer would set its bar. An
    uncalibrated probability is worse than none, because it launders a guess
    into something that reads as evidence.

    ⚠️ If you find yourself wanting `P(correct)` here, stop. Relative support,
    ordered, is enough for every consumer written so far.
    """

    value: Any
    support: float

    def to_json(self) -> dict:
        return {"value": self.value, "support": self.support}


# ─────────────────────────────────────────────────────────────────────────────
# The closed vocabularies
#
# ⚠️ Closed on purpose. An open string space reintroduces exactly the typo
# class that a `.get(key, default)` hides: a quantity nobody emits and a
# quantity misspelled look identical to a consumer, and both read as ABSENT.
# `Log.observe` raises on an unknown quantity.
# ─────────────────────────────────────────────────────────────────────────────


class _Vocab:
    """A closed set of string constants, with membership derived from the
    class body so the list cannot drift from the constants."""

    @classmethod
    def all(cls) -> frozenset[str]:
        return frozenset(
            v for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str))

    @classmethod
    def check(cls, value: str, what: str) -> str:
        if value not in cls.all():
            raise ValueError(
                f"{value!r} is not a known {what}. "
                f"Add it to {cls.__name__} deliberately -- an open vocabulary "
                f"makes a typo indistinguishable from an absent reading.")
        return value


class Q(_Vocab):
    """Every quantity the staged pipeline knows about.

    ⚠️ The distinction that runs through this list is MEASUREMENT vs VERDICT,
    and it is not cosmetic -- it decides which stage owns the quantity.

    A MEASUREMENT's only ancestor is the raster. A VERDICT has other facts in
    its ancestry, which is what the circularity filter reads.
    """

    # ── page geometry (measurements) ────────────────────────────────────────
    STAFF_LINES = "staff_lines"              # 5 y positions, page px
    STAFF_SPACING = "staff_spacing"          # px between lines
    #: One staff SPACE in a CELL's own canonical frame, in that frame's px.
    #:
    #: ⚠️⚠️ IT IS NOT A CONSTANT AND ASSUMING IT IS WOULD BE WRONG ON HALF THE
    #: CELLS OF A CONDUCTOR'S PAGE. `CANONICAL_STAFF_SPAN_PX / 4 = 100` is the
    #: NOMINAL, but `_upscale_to_canonical` scales a too-wide cell by WIDTH
    #: instead, so its staff stays smaller than canonical. Measured over the
    #: engraved Beethoven 5 iv fixture, the half-step reads **50 px on 84 cells
    #: and 28, 23 or 19 px on 67 more** -- less than half the nominal.
    #:
    #: ⚠️ It is a DIFFERENT FACT from `STAFF_SPACING`, which is the page's, and
    #: is kept apart rather than folded in for the reason `Q.GLYPH_BOX`'s
    #: canonical x had to be: two frames under one name is how a consumer comes
    #: to compare lengths that were never in the same units.
    CELL_STAFF_SPACE = "cell_staff_space"
    #: One measure CELL's own rectangle on the page, `[x0, y0, x1, y1]` in
    #: page pixels -- CORNERS, like every other `bbox_page_px` here.
    #:
    #: ⚠️⚠️ IT IS THE FRAME THE ARC MERGE HAPPENS IN, AND NOTHING ELSE CAN
    #: STAND IN FOR IT. Cells are cut per measure, so a slur crossing a
    #: barline is DETECTED AS TWO ARCS, and the join asks whether an arc ends
    #: ON its cell's right edge and the next begins on its left. That question
    #: is about the CELL's boundary, not about its contents -- deriving the
    #: box from the glyphs inside it would put the edge wherever the outermost
    #: detection happens to fall, so an arc that genuinely reaches the barline
    #: would test as ending in open space, and the wider the empty margin the
    #: more certainly the two halves stay two slurs.
    #:
    #: ⚠️ `gather_detections` has read this off the cell since the day page
    #: boxes arrived (`_page_box` opens with `getattr(cell, "bbox_page_px")`)
    #: and threw it away after converting one glyph -- the value existed and
    #: nothing carried it, this project's own named anti-pattern, and it is
    #: why `Q.ARC_KIND` and `Q.ARC_OWNER` could decide 199 arcs a page with no
    #: route to a file.
    CELL_BOX = "cell_box"
    STAFF_EXTENT = "staff_extent"            # (x_start, x_end)
    STAFF_SKEW = "staff_skew"                # measured tilt/bow
    GAP_BRIDGING = "gap_bridging"            # ink crossing an inter-staff gap
    SYSTEMIC_COLUMN = "systemic_column"      # a column crossing every gap
    BRACKET_BLOCK = "bracket_block"          # the block index _assign_groups read
    BARLINE_COLUMN = "barline_column"        # a fitted barline, x per staff
    LEFT_EDGE_INK = "left_edge_ink"          # the narrow left-edge scan

    # ── detection (measurements) ────────────────────────────────────────────
    GLYPH_BOX = "glyph_box"                  # class + bbox, one row per detection
    GLYPH_CONF = "glyph_conf"                # the detector's own score
    GLYPH_BAND_DISTANCE = "glyph_band_distance"   # to each candidate staff
    GLYPH_LADDER = "glyph_ladder"            # ledger rung completeness
    NOTEHEAD_STAFF_POSITION = "notehead_staff_position"   # pos_float, CLEF-FREE
    NOTEHEAD_CLASS = "notehead_class"        # black/half/whole, before duration
    #: ⚠️ The REST GLYPH's class -- whole/half/quarter/8th -- before duration,
    #: the exact parallel of `NOTEHEAD_CLASS`.
    #:
    #: ⚠️⚠️ IT WAS ABSENT FROM THIS VOCABULARY UNTIL 2026-09-09, and that made
    #: rests the worst case of the family this architecture exists to kill.
    #: The four starved stubs at least ABSTAIN `not_implemented` and are
    #: therefore accounted for; a rest was detected -- 838 of them over four
    #: real pages, 460 of them `restWhole` -- reached `GLYPH_BOX`, and NOTHING
    #: ANYWHERE DECLARED THE ABSENCE. No gather site, no adjudicator, no stub,
    #: no `wants`. `tools/omr/staged/export.py` found it by asking, per
    #: notation family, which of four different zeros was true.
    #:
    #: ⚠️ `restHBar` / `restHNr` are MULTI-MEASURE REST INDICATORS and carry no
    #: single duration; they are observed here like any other rest and the
    #: adjudicator abstains on them by name. Recording the ink and declining
    #: to read it is the honest pair; dropping it at the gather site is how
    #: this quantity came to be missing in the first place.
    REST = "rest"
    STEM = "stem"                            # CV stem: x, y, w, h (NOT x,y0,y1)
    #: ⚠⚠ THE VALUE IS `[x, y, w, h]`, AND THIS COMMENT SAID `x, y0, y1`
    #: until 2026-09-18. Verified against the record: `detail.x0 == value[0]`
    #: and `detail.x1 - detail.x0 == value[2]` on 400 of 400 rows, and the
    #: h/w distributions land inside the shipped filters exactly (h p05 2.14
    #: / median 3.93 / p95 6.78 spaces against `min_height` 2.0 and
    #: `max_height` 8.0; w median 0.32 against `max_width` 0.6).
    #:
    #: ⚠ THIRD BOX-CONVENTION TRAP IN ONE RECORD, and they disagree:
    #: `Q.GLYPH_BOX.value` is `[name, x, y, w, h]`, `Q.INK.detail.
    #: ink_bbox_canonical` is `[x0, y0, x1, y1]` CORNERS, and this is
    #: `[x, y, w, h]`. Reading one as another gives a NEGATIVE width and a
    #: clean believable zero -- it cost `benchmarks/omr-ink-extent-2026-09`
    #: a run that reported `NO_INK_UNDER_BOX` on 100 of 106 rows. ASSERT
    #: the convention against the row's own stated spans before comparing.
    BEAM_STROKE = "beam_stroke"              # CV beam stroke centre
    #: EVERY vertical run the stem opening produced -- ACCEPTED OR REFUSED --
    #: with which filter first refused it and its extent in page pixels.
    #:
    #: ⚠️⚠️ IT EXISTS BECAUSE `Q.STEM` IS THE SURVIVORS ONLY, AND SEAN ASKED A
    #: QUESTION THE RECORD COULD NOT ANSWER. Asked whether the stages hold what
    #: is needed to tell one kind of vertical line from another, the answer was
    #: no, for two reasons this quantity closes:
    #:
    #:   1. **There was no quantity for "a vertical run."** `detect_stems`
    #:      finds every vertical candidate, applies SIX filters and emits only
    #:      the survivors, so a candidate the pipeline FOUND AND DISCARDED left
    #:      no row at all and the population arrived at every stage already
    #:      named `stem`. Naming and filtering are fused inside GATHER, against
    #:      its own charter that it *decides nothing* --
    #:      `docs/breakthrough-2026-09-18-the-unit-of-enquiry.md`, and Sean
    #:      unprompted: *"NO_INK shows me that we are discarding information
    #:      that should be black and white."*
    #:   2. **The strongest discriminator could not be computed.** Sean's
    #:      barline test is *a barline's two ends sit ON the outer staff lines;
    #:      a stem's do not*, which needs the run's endpoints and the staff
    #:      lines in ONE coordinate system. `Q.STEM` is CELL canonical and its
    #:      row carries no page coordinates at all, while `Q.STAFF_LINES` is
    #:      PAGE px. The two could not be compared, so the test could not be
    #:      asked. Every row here carries `run_bbox_page_px`.
    #:
    #: ⚠️ `run_outcome` IS A FACT ABOUT WHICH FILTER FIRED, NOT A NAME FOR THE
    #: INK. A refused run is not thereby "not a stem" -- the crop pass
    #: adjudicated the width cap's discards **33 of 33 REAL** -- and an accepted
    #: one is not thereby a stem. Recording the fate without asserting the
    #: identity is the whole point; asserting it is what `Q.STEM` already does
    #: and what §9 of `docs/proposal-2026-09-18-boxing-is-a-decision.md` argues
    #: it cannot do by dimension, because *"length is helpful in all of them
    #: except stems."*
    #:
    #: ⚠️ THE UNIT IS THE CELL'S OWN STAFF SPACE, never a flat 100 px.
    #: `_upscale_to_canonical` scales a too-wide cell by WIDTH, which is why
    #: `Q.CELL_STAFF_SPACE` exists -- measured here, 1,167 of 1,180 Litolff
    #: cells sit at exactly 100 and 13 do not, so the flat constant is right
    #: 98.9% of the time and silently wrong on the rest.
    #:
    #: ⚠ THE BOX IS `[x, y, w, h]` CANONICAL, matching `Q.STEM.value` and NOT
    #: `Q.INK.detail.ink_bbox_canonical`, which is `[x0, y0, x1, y1]` CORNERS.
    #: Three conventions disagree in one record (see `STEM` above); reading one
    #: as another gives a NEGATIVE width and a clean believable zero. The page
    #: box is corners, like `Q.INK`'s and `Q.GLYPH_BOX`'s, and is spelled
    #: `run_bbox_page_px` so the two cannot be confused at a read site.
    #:
    #: ⚠️ PRODUCER ONLY, default OFF (`OMR_VERTICAL_RUNS`). Nothing reads it,
    #: deliberately -- the `Q.INK` discipline: a producer and its first consumer
    #: landing together makes the reach measurement circular. Its first
    #: intended consumer is named in `wiring.KNOWN_GAPS`.
    VERTICAL_RUN = "vertical_run"
    FLAG = "flag"                            # detected flag
    AUG_DOT = "aug_dot"                      # dot offset from its notehead
    TUPLET_MARKER = "tuplet_marker"          # digit or bracket, with its span
    ARC_BOX = "arc_box"                      # slur/tie ink, before attribution
    ARTICULATION_MARK = "articulation_mark"  # mark + the side its class names
    #: A FERMATA glyph -- the pause sign, `fermataAbove` / `fermataBelow`.
    #:
    #: ⚠️ IT IS ITS OWN FAMILY AND NOT AN ARTICULATION, and the separation is
    #: the engraving's, not a taxonomy preference. An articulation is printed
    #: against ONE NOTEHEAD on the side its class names; a fermata hangs over
    #: whatever is SOUNDING beneath it, which on a conductor's page is most
    #: often a whole-bar REST. `export._mxl_note` already keeps them apart for
    #: exactly that reason -- `<fermata>` is emitted outside the
    #: `<articulations>` block precisely because a rest can carry one and a
    #: staccato cannot.
    #:
    #: ⚠️ The class names a SIDE (`Above` / `Below`) and this quantity records
    #: it, but nothing reads it yet: `_mxl_note` writes `<fermata
    #: type="upright"/>` unconditionally. Recorded rather than dropped, so the
    #: day the renderer learns `inverted` the reading is already on the
    #: record. ⚠️ It is NOT the articulation side test either -- that side
    #: says which notehead a mark may name, and a fermata's does not: a
    #: `fermataAbove` over a bar's only rest stands above ink it belongs to.
    FERMATA_MARK = "fermata_mark"
    #: A TRILL, TURN, INVERTED TURN, MORDENT or TREMOLO glyph.
    #:
    #: ⚠️ THE TENTH EXPORT GAP'S FAMILY, and the one that does NOT close with
    #: this quantity. `export_coverage.KNOWN_GAPS` records the engraved count
    #: as a DETECTION problem: the eleven-work truth's only ornaments are
    #: twelve `<tremolo>`, and the detector produces ZERO `tremolo1`-`5`
    #: detections against a positive control of 34,115 detections over 11
    #: committed transcriptions. So this names the ink where there IS ink and
    #: says nothing about the ink there is not.
    #:
    #: ⚠️ `strokes` IS RECORDED AND IS A TREMOLO'S ONLY. The class states it
    #: (`tremolo3`), no other ornament carries one, and `_mxl_ornament_elements`
    #: needs it -- so it travels on the row rather than being re-derived from
    #: the class name by a second reader.
    #:
    #: ⚠️ THE SIDE IS `None` FOR A TREMOLO, and that is not a gap: a tremolo
    #: rides the STEM and sits on whichever side that is, so its class states
    #: no side and the geometry test is SKIPPED rather than guessed. The other
    #: four are printed above.
    ORNAMENT_MARK = "ornament_mark"
    WEDGE_BOX = "wedge_box"                  # hairpin ink
    DYNAMIC_LETTER = "dynamic_letter"        # one letter, before spelling
    #: ONE CONNECTED PIECE OF INK in a measure cell, named or not.
    #:
    #: ⚠️⚠️ IT IS THE POPULATION THE OTHER MEASUREMENTS ARE A CLASSIFICATION
    #: OF, AND THAT IS THE WHOLE POINT. Every other row in this section starts
    #: from a DETECTION, so GATHER's population has always been the detector's
    #: output rather than the page's ink -- and ink the detector did not fire
    #: on produced no row at all. Sean, 2026-09-17: *"We can only gather what
    #: we see. We may or may not be able to classify it correctly initially -
    #: or at all - but ink is ink. There is nothing that should be classified
    #: as unseen - only unclassified."* A record that holds no row where the
    #: page holds ink says ABSENT where the truth is DECLINED, which is the
    #: one collapse this module exists to prevent, happening to the ink itself.
    #:
    #: ⚠️ MEASURED, AND IT IS NOT REACHABLE FROM THE DETECTION RECORD.
    #: Litolff Beethoven 5 p.62 prints a `3/4` on all seventeen staves at one
    #: bar; the detector fires no `timeSig*` glyph there on ANY of them. There
    #: is no unclassified DETECTION to re-weight -- the ink was never detected
    #: -- so this is a raster pass, and the precedent it reuses is
    #: `direction_text._blank_detections`, which already subtracts every
    #: detection from a page's ink so "find the text" becomes "find the ink".
    #:
    #: ⚠️ A PIECE OF INK IS NOT A MARK, and the row says so rather than
    #: pretending otherwise. Print bleeds: on a scan a notehead merges with
    #: its ledger line and a staff-line remnant can bridge two glyphs, so one
    #: component may be several marks and one mark may be several components.
    #: Which it is belongs to a later stage; GATHER decides nothing.
    #:
    #: ⚠️ NOTHING IS FILTERED. No size gate, no shape gate, no confidence cut
    #: -- staff-line residue, barlines, stems and scanner speckle all get a
    #: row. A threshold here is a DECISION taken in the wrong stage and it is
    #: the one kind that cannot be revisited: a row that was never created is
    #: evidence no later rule can reconsider. `detail` carries the shape and
    #: the detector coverage so a rule can weigh them; this reader applies
    #: neither.
    INK = "ink"

    # ── EVERY FAMILY'S OWN POSITION (measurements, scoreless) ───────────────
    #
    # ⚠️⚠️ ELEVEN FAMILIES HAD NO POSITION FACT AT ALL, and `capture.py`'s
    # table is what made that sayable: only `note`, `clef` and `key` graded
    # `MEASURED`. Sean, 2026-09-17 -- *"give the families real position
    # information - or if it should be symbol specific then make it so"* --
    # and the second clause is why these are TEN quantities rather than one
    # field. A rest's position is WHICH SIDE OF WHICH LINE it hangs from; a
    # meter's is TWO MARKS, one in each half of the staff; a dynamic's is HOW
    # FAR BELOW the bottom line, because it is not on the grid at all. One
    # schema wide enough for all of those would hold none of them well.
    #
    # ⚠️ ITS OWN QUANTITY, NEVER A FIELD ON THE SHAPE ROW, for the reason
    # `CLEF_POSITION` states below at length: `correlated_groups` treats one
    # reader's rows on one crop as ONE SIGNAL, so a position hung off the
    # glyph's row is absorbed into that glyph's detector term. The `band*`
    # grades `capture.py` reports for `dynamic` and `wedge` are that mistake
    # already made -- a measured, scoreless, staff-relative offset living as
    # a DETAIL of a scored row. Those two are PROMOTED here, not invented.
    #
    # ⚠️⚠️ EVERY ONE OF THESE IS EVIDENCE, NOT A RULE. Sean, 2026-09-17:
    # *"position is an option for helping us determine something but will
    # rarely be a clear rule that determines by itself... Quick rules will
    # give us quick results that could be poor."* They are `Mode.ADDITIVE`
    # inputs to be weighed against the ink, the other staves and whatever
    # else a consumer holds -- never a veto, never a gate. Where a
    # measurement is ambiguous the AMBIGUITY is recorded (`attach_margin`,
    # `centre_steps_from_middle`, `opens: None`) rather than resolved, because
    # a mark that could be one thing or two is precisely what a later stage
    # exists to weigh.
    #
    # ⚠️ TWO UNITS ON PURPOSE. `unit` is on every row: marks ON the grid are
    # in STAFF STEPS from the top line (the `NOTEHEAD_STAFF_POSITION` unit);
    # marks in the row of the page BELOW the staff are in STAFF SPACES below
    # the bottom line (the `_band_offset_spaces` / `hairpin_detection` unit).
    # Giving a `ff` a step coordinate would report it at step 14, a number
    # that composes across documents and means nothing.
    #
    # Produced by `positions.py` behind `OMR_FAMILY_POSITIONS`, default OFF.
    # ⚠️ READ BY NOTHING, DELIBERATELY -- see `reach.KNOWN_GAPS`. A producer
    # and its first consumer landing together makes the reach measurement
    # circular, which is the discipline `gather_ink` shipped under one day
    # earlier.

    #: A rest's attachment: whole and half rests are THE SAME SHAPE and differ
    #: only in which line they touch and on which side. No shape fact can
    #: separate them, which is why the phantom-note census could not and why
    #: `OMR_WHOLE_REST_INK` -- the one staged rule that DELETES notes -- leans
    #: on a shape window plus a slot witness instead.
    REST_POSITION = "rest_position"

    #: The arc's OWN ink. ⚠️ `adjudicate_arc_kind` declares
    #: `notehead_staff_position`: the NOTES' positions, which is the right
    #: evidence for the tie/slur grammar and says nothing about where the
    #: CURVE is. `depth_steps` is what a tie (shallow, hugging its two heads)
    #: and a slur (arcing clear) differ in.
    ARC_POSITION = "arc_position"

    #: Measured above/below/inside for an articulation -- the ruler beside the
    #: class name's own suffix, which is not an independent witness because it
    #: fails together with the classification it is read off.
    ARTICULATION_POSITION = "articulation_position"

    #: The same for a fermata. ⚠️ A DIFFERENT QUANTITY FROM THE ARTICULATION'S
    #: and for the reason `FERMATA_MARK` already gives: an articulation is
    #: printed against ONE notehead on the side its class names, a fermata
    #: hangs over whatever sounds beneath it -- most often a whole-bar rest.
    #: Two populations, two distributions, and pooling them would average
    #: a mark that attaches with one that does not.
    FERMATA_POSITION = "fermata_position"

    #: The same for an ornament. ⚠️ Apart again: a tremolo rides the STEM and
    #: its class states no side at all, so its position is the only thing that
    #: ever says which side it is on.
    ORNAMENT_POSITION = "ornament_position"

    #: ⚠️⚠️ WHERE THE DIGIT STANDS, WHICH FOR A TUPLET IS THE WHOLE QUESTION.
    #: One `numeral` class covers time signatures, tuplet digits, fingerings
    #: AND measure numbers -- a POSITIONAL distinction made by where the digit
    #: stands, which DSv2 splits into `tuplet3` / `fingering3` and reproduces
    #: badly on orchestral pages. `TUPLET_MARKER` records `x0`, `x1`,
    #: `x_center` and NO `y` AT ALL, so a tuplet's vertical position is
    #: nowhere on the record today.
    TUPLET_MARKER_POSITION = "tuplet_marker_position"

    #: Where a meter glyph sits relative to the staff's own middle line. A
    #: printed meter is TWO marks, one in each half, centred on each other,
    #: and nothing anywhere measures that today: `_meter_from_digits` asks
    #: only for two `timeSig*` glyphs at two different `y_center` values, with
    #: no width, height, x or half test -- which is how the Litolff p.62 `3/4`
    #: this project cited for weeks came to be ONE BARLINE BROKEN INTO TWO
    #: FRAGMENTS at the cell's left edge.
    #:
    #: ⚠️⚠️ IT CONTRIBUTES; IT DOES NOT DECIDE. Ink bleed fuses a numerator
    #: and a denominator into one stroke, so `spans` is compatible with a real
    #: meter -- and two fragments in two halves are what a broken barline also
    #: looks like. **Neither reading settles anything alone**, and a rule
    #: treating either as decisive is the quick rule with the poor result.
    #: `centre_steps_from_middle` is recorded FOR that ambiguity, not to
    #: resolve it.
    #:
    #: ⚠️ FILED ON THE STAFF with the bar in `detail["cell"]`, exactly as
    #: `METER_GLYPH` is -- a fixture that files it on a GLYPH tests the test.
    METER_GLYPH_POSITION = "meter_glyph_position"

    #: PROMOTED from `DYNAMIC_LETTER.band_offset_spaces`: the same number, on
    #: a row of its own so it can be a second witness.
    DYNAMIC_BAND_POSITION = "dynamic_band_position"

    #: PROMOTED from the `CV_HAIRPINS` half of `WEDGE_BOX.band_offset_spaces`,
    #: and MEASURED for the detector half, which never carried one.
    WEDGE_BAND_POSITION = "wedge_band_position"

    #: ⚠️ THE ONE THAT IS GENUINELY NEW, and the family `capture.py` also
    #: grades `shape: NO` -- a direction word is not in the 208-class space,
    #: so it has no detector row to hang a detail off. Its only staff-relative
    #: fact is `placement`, an above/below the reader derives from the band it
    #: searched, graded `coarse_band_only`: too coarse to carry a
    #: distribution. The OFFSET separates a `cresc.` standing in the dynamics
    #: row from an `Allegro con brio` printed clear above the system.
    DIRECTION_BAND_POSITION = "direction_band_position"

    #: ⚠️ THE REFUSAL, NOT A POSITION. A cell with no five-line grid -- a
    #: one-line percussion staff -- can measure nothing, and the abstention is
    #: filed ONCE for the cell rather than once per mark, so the record says
    #: "this cell has no ruler" instead of reporting one fault twenty times.
    CELL_POSITION_BASIS = "cell_position_basis"

    #: WHICH PRINTING THIS IS -- the edition, its publisher, its work and its
    #: scan type, on the DOCUMENT.
    #:
    #: ⚠️⚠️ THE CONDITIONING VARIABLE THAT NEVER REACHED THIS STAGE. Sean,
    #: 2026-09-17: *"it might be helpful to have general information based on
    #: publisher or common practice of where a certain things fall so if we
    #: have an undiagnosed blob or dot, we have gathered a lot of information
    #: on what sorts of things are more likely where."* Where a mark falls is
    #: a property of the PLATE -- this repo has already measured two houses
    #: disagreeing about nearly everything, from ledger pitch (Litolff ~1.10x
    #: the staff spacing, Peters/Breitkopf/Simrock ~0.975x) to dot density
    #: (35 against 656) to whether a family bracket is printed at all. Until
    #: this row, `grep publisher tools/omr/staged/gather.py` returned ONE
    #: COMMENT: the variable everything would be conditioned on was not on the
    #: record.
    #:
    #: ⚠️ `source_kind` IS WHY IT IS ADMISSIBLE. It comes from the COMMITTED
    #: catalog, which reads IMSLP's own work page -- not from the plate -- so
    #: it does not fall silent when the raster is bad. That is the property
    #: `A-INK` and the `source_kind` doctrine both require of a second
    #: witness, and it is the reason the `editions` tier (an OMR output of the
    #: same raster) would NOT be admissible here.
    DOCUMENT_IDENTITY = "document_identity"

    # ── header readings (measurements) ──────────────────────────────────────
    CLEF_GLYPH = "clef_glyph"                # detector's clef, with frame
    CLEF_LOCATED = "clef_located"            # CV locator: shape, line, symmetry
    CLEF_REFUSAL_BRANCH = "clef_refusal_branch"   # which veto the locator hit
    #: ⚠️ WHERE A CLEF GLYPH STANDS ON THIS STAFF, in half-spaces measured DOWN
    #: from the top line -- the same measurement a notehead gets, from the same
    #: grid, and for the same reason.
    #:
    #: ⚠️⚠️ IT IS A SEPARATE ROW FROM A SEPARATE READER BECAUSE A DETAIL FIELD
    #: ON THE GLYPH ROW CANNOT WORK, and that is structural rather than
    #: stylistic. Every `CLEF_GLYPH` row on a staff shares a reader, a frame
    #: and a quantity, so `Evidence.correlated_groups` calls them ONE SIGNAL
    #: and `tally` counts the group once, taking its strongest term. A term
    #: citing a glyph row is therefore absorbed by that glyph's own detector
    #: term -- measured: a 1.5 added beside a 3.0 left the contest at 3.0
    #: against 3.0. **No refinement of the DETECTOR's evidence can break a
    #: clef contest**; a tie-breaker has to come from another reader, and the
    #: staff's measured line grid is one.
    CLEF_POSITION = "clef_position"
    CLEF_SEED = "clef_seed"                  # the dossier's clef
    KEYSIG_RUN_POSITION = "keysig_run_position"   # accidental positions, NO clef
    KEYSIG_MARKER = "keysig_marker"          # detector keySharp/keyFlat
    #: ⚠️ Which candidate CLEF the measured accidental run fits.
    #:
    #: This is the clef implication test that needs NO identity (ideal-reader
    #: Part 4.6). The run's POSITIONS are clef-free geometry; the SLOT TABLE is
    #: chosen by the clef -- so a run that fits treble's slots and not bass's
    #: is evidence about the CLEF. The evidence that it discriminates is the
    #: documented bug: three flats fitted against a GUESSED clef came back as
    #: TWO SHARPS. A fit that changes that much with the clef is a sensor for
    #: it. Vacuous where no accidentals were found, and a 0-accidental key fits
    #: every clef -- so it covers different staves from the range test.
    KEYSIG_CLEF_FIT = "keysig_clef_fit"
    #: ⚠️ The TEMPLATE reader's answer to the same question, and it is a
    #: SEPARATE quantity rather than more rows under `KEYSIG_CLEF_FIT` for two
    #: reasons, only one of which is tidiness.
    #:
    #: The load-bearing one: `adjudicate_clef` reads `KEYSIG_CLEF_FIT` and
    #: raises one `Term` per row, so filing a second reader's fits there would
    #: silently double the weight of this evidence in the CLEF contest — a
    #: reading change leaking into a decision it was never measured against.
    #: Two readers on one crop are also not two independent signals in the
    #: sense `Evidence.independent` means.
    #:
    #: The second: the two readers fail in opposite directions and this repo
    #: has paid to know it. `key_signature_locator` loses accidentals to
    #: broken ink and under-counts; `key_signature_template` can match
    #: spurious ink and OVER-count, which is why `key_signature_template`
    #: refuses to infer a slot at all. Reported apart, a consumer can express
    #: the measured precedence; pooled, it cannot.
    KEYSIG_TEMPLATE_FIT = "keysig_template_fit"
    METER_GLYPH = "meter_glyph"              # timeSig digits / C / cut-C
    METER_TEMPLATE = "meter_template"        # the template reader's score
    #: The SAME template reader, aimed at a mid-staff BAR HEAD rather than at
    #: the header window — a printed meter CHANGE.
    #:
    #: ⚠️⚠️ A SEPARATE QUANTITY, AND THAT IS THE WHOLE POINT. `adjudicate_meter`
    #: takes every `Q.METER_TEMPLATE` row as a vote on the system's OPENING, so
    #: filing a mid-staff reading there would make a change at bar 9 argue
    #: about what bar 1 prints. The precedent is `Q.KEYSIG_TEMPLATE_FIT`, which
    #: is separate from `Q.KEYSIG_CLEF_FIT` for exactly the same reason:
    #: pooling two readings of two different questions moves the decision that
    #: reads the pool.
    #:
    #: ⚠️ The BAR is in `detail["cell"]`, filed on the STAFF subject, which is
    #: how `Q.METER_GLYPH` already carries it — a mid-staff reading whose bar
    #: is unknown is not a change, it is noise.
    METER_TEMPLATE_AT_BAR = "meter_template_at_bar"

    # ── text (measurements) ─────────────────────────────────────────────────
    MARGIN_LABEL = "margin_label"            # the STRING, before the lexicon
    DIRECTION_WORD = "direction_word"        # an OCRed word inside a system
    TEXT_LAYER = "text_layer"                # the PDF's own text, if any

    # ── external facts (measurements, but not from THIS raster) ─────────────
    ROSTER_ENTRY = "roster_entry"            # the catalog's instrumentation
    DOSSIER_FACT = "dossier_fact"            # the work's own meter/clef/key
    INPUT_DOMAIN = "input_domain"            # scan vs engraved, for weights

    # ── verdicts ────────────────────────────────────────────────────────────
    SYSTEM_MEMBERSHIP = "system_membership"  # which staves are one system
    STAFF_GROUP = "staff_group"              # which staves are one FAMILY
    GROUP_SYMBOL = "group_symbol"            # brace | bracket | none
    MEASURE_PARTITION = "measure_partition"  # where the bars are
    CLEF = "clef"
    KEY_SIGNATURE = "key_signature"
    METER = "meter"
    DURATION = "duration"                    # ⚠️ a VERDICT, not a measurement
    #: Which glyphs of a bar sound TOGETHER — one event, N noteheads.
    #: ⚠️ A VERDICT, and the distinction matters: the x POSITION is a
    #: measurement (`GLYPH_BOX` carries it), but "these are simultaneous" is
    #: an interpretation of those positions under a tolerance.
    EVENT = "event"
    #: ⚠️ Which events of DIFFERENT STAVES sound at the same instant — the
    #: column through a system. `Q.EVENT` is the same question one scope down
    #: and stops at the staff (`Kind.CELL`); a conductor's page is many staves
    #: reading one stretch of time, so a column is the only place the record
    #: holds REDUNDANT evidence about the same moment.
    #:
    #: ⚠️⚠️ AND THE ALIGNMENT IS ONLY PARTLY INFORMATION — the rest is DENSITY.
    #: Measured through this decision on 51 real bars (Brahms 1 / Breitkopf,
    #: 3,006 events) against a CIRCULAR-SHIFT null that keeps every
    #: within-staff interval and destroys only the phase: the page needs
    #: **1,483 columns where the null needs 2,409** (1.62x) and leaves 744
    #: events standing alone against 1,706 (2.29x). But the corroboration
    #: RATE rises with density while the information falls — sparse bars
    #: 0.437 vs 0.212 (2.06x), dense bars 0.530 vs 0.348 (1.52x) — so the
    #: verdict carries `events_per_space` on every bar: a consumer reading
    #: corroboration without it cannot tell evidence from crowding.
    #:
    #: ⚠️ DO NOT READ THE RESIDUAL AS EVIDENCE. It does not separate (0.0734
    #: real vs 0.0704 null) and cannot: a column is BUILT to lie within the
    #: tolerance. An earlier draft of this docstring said it separated at
    #: every density — that figure came from the nearest-neighbour probe,
    #: which measures an unbounded quantity, and was carried across
    #: definitions. It is a diagnostic only, and a good one: a residual of
    #: exactly 0.0 is what exposed the glyph-ordinal collision bug.
    ONSET_COLUMN = "onset_column"
    GLYPH_OWNER = "glyph_owner"
    ARC_OWNER = "arc_owner"
    ARC_KIND = "arc_kind"                    # tie | slur
    #: Which way a notehead's STEM points -- up | down.
    #:
    #: ⚠️ IT BELONGS TO THE STEM AND IS FILED ON THE NOTEHEAD, which is not a
    #: contradiction but the paid-for lesson. `transcribe._stem_direction`
    #: takes ALL the noteheads on one stem at once, because a double stop is
    #: two heads on one physical stem: comparing each head's centre against
    #: the stem's midpoint hands the two members of one chord OPPOSITE
    #: directions for any interval wider than the stem is long, which reads
    #: as divisi and splits the chord into two voices. Measured on Brahms's
    #: Viola, where `C4/C5` came out as `C4` then `C5` at the end of the bar.
    #: The consumers want it per notehead, so it is decided per notehead from
    #: the whole group hanging on the stem.
    #:
    #: ⚠️ `Q.STEM` carries the stem's BOX and says NOTHING about which way it
    #: points -- which is why `gather_coverage.q_covering` is deliberately not
    #: a substring test, and why this is a separate name rather than a detail
    #: field on that row.
    STEM_DIRECTION = "stem_direction"
    #: Whether a glyph the DETECTOR called a notehead is in fact the ink of a
    #: WHOLE REST -- `True`, `False`, or an abstention where it cannot be told.
    #:
    #: ⚠️ IT EXISTS BECAUSE SEAN READ THE FILE AGAINST THE PRINT AND SAID SO
    #: (2026-09-11): *"in bars where it should be just whole note rest in two
    #: four. It's showing an actual quarter note, not a quarter note rest."*
    #: A pitched note standing where the page prints silence is the worst
    #: SHAPE of error this pipeline makes -- a missing note leaves a visible
    #: gap, an invented one has to be hunted down and deleted -- and that
    #: asymmetry, not the count, is why it is a decision rather than a
    #: tolerated misread. The count is small: 25 of 2,347 noteheads on the
    #: four pages measured.
    #:
    #: ⚠️⚠️ IT IS NOT THE WHOLE OF SEAN'S OBSERVATION AND MUST NOT BE QUOTED
    #: AS IF IT WERE. Of the 26 bars whose entire exported content is one
    #: lone quarter in a 2/4 bar, **5 are this fault and 18 are REAL NOTES**
    #: whose bar-mates were never detected -- a reading shortfall wearing the
    #: costume of an invented note -- with 3 more spurious heads on slur and
    #: stem ink. A rule that emptied all 26 bars would delete real music.
    #:
    #: ⚠️ TWO WITNESSES, AND NEITHER IS ADMISSIBLE ALONE. This is the
    #: structure `_drop_unladdered_noteheads` already states for the same
    #: family of problem, and here it is measured rather than asserted:
    #:   * SHAPE alone fires on 148 of 2,347 noteheads. Most are not whole
    #:     rests -- bled heads, beam residue, letters of the word *cresc.* --
    #:     so shape alone would delete real music.
    #:   * POSITION alone fires on 310 and is nearly uninformative: the band a
    #:     whole rest hangs in is where C5 and D5 live in treble, i.e. where
    #:     ordinary music is.
    #:   * Together they fire on 25, and all 25 were cropped and looked at
    #:     against the print. All 25 are whole rests.
    #:
    #: ⚠️ POSITION IS ESTABLISHED TWO WAYS AND THE SECOND ONE MATTERS. A whole
    #: rest HANGS UNDER THE FOURTH STAFF LINE FROM THE BOTTOM whatever the
    #: clef, key or music -- the engraver has no freedom about it -- so its
    #: centre sits at one staff step. But that step is measured against the
    #: staff's RECORDED lines, and on a warped scan those are up to a step out
    #: (the document's own correctly-read whole rests spread over steps
    #: 2.5-5.9). So a NEIGHBOURING BAR of the same staff holding a detected
    #: `restWhole` at nearly the same height counts too: a tacet part prints
    #: one in EVERY bar, and a shared registration error cancels between two
    #: rows of one staff. It caught `P1 m85`, which the absolute slot missed.
    #:
    #: ⚠️ THE NEIGHBOUR WITNESS IS NOT INDEPENDENT OF THE DETECTOR, only of
    #: THIS GLYPH. That is weaker than CLAUDE.md's *"a second witness must not
    #: come off the same raster"* and it is the strongest thing available
    #: here; it is stated rather than dressed up.
    #:
    #: ⚠️ THE VALUE IS NOT A RECLASSIFICATION. A `True` verdict stops the
    #: exporter writing a NOTE there and is counted; nothing manufactures a
    #: `Q.REST` row, because what ink is on the page is a GATHER fact and this
    #: is an ADJUDICATE decision. The bar then falls to the exporter's padded
    #: measure rest, which says *we read nothing in this bar* -- weaker than
    #: *we read silence*, and true.
    #:
    #: ⚠️ A LOWER BOUND ON THE FAULT, NOT A MEASUREMENT OF IT. Scored against
    #: the document's own correctly-read whole rests these cuts re-describe
    #: only the middle of that population, so a phantom note whose rest is
    #: shaped unlike the median is not caught here.
    NOTEHEAD_IS_A_WHOLE_REST = "notehead_is_a_whole_rest"
    #: A bar's 1-2 VOICE STREAMS, as a partition of its glyphs.
    #:
    #: ⚠️ MUSICXML PAIRS `<slur>` WITHIN A `<voice>`, so this is not a
    #: presentation detail: an arc whose ends land in different streams is
    #: UNPAIRED at both, which makes the file invalid rather than merely
    #: wrong. `export._paired_spans` takes a `voice_of` map for exactly that
    #: test, and the staged exporter passed it an EMPTY dict -- so the rule
    #: was present, inert, and indistinguishable from a rule that had been
    #: applied and found nothing.
    #:
    #: ⚠️ A REST IS IN BOTH STREAMS, and that is the engraving's convention
    #: rather than a modelling choice: each voice needs its own bar to sum, so
    #: `<rest>` is written once per voice with its own `<voice>` tag. It makes
    #: this a COVER of the bar's glyphs and not a partition of them, which is
    #: why the exporter's note-accounting control has to count the duplicate.
    VOICES = "voices"
    TUPLET_RATIO = "tuplet_ratio"
    ARTICULATION_OWNER = "articulation_owner"
    #: Which EVENT -- notehead or rest -- a fermata hangs over.
    #:
    #: ⚠️ THE VALUE IS A GLYPH SUBJECT AND THE CONSUMER MUST HOIST IT. A
    #: fermata over a chord is ONE pause over the whole chord, so the exporter
    #: writes it on the chord's FIRST `<note>` (MusicXML's representative for a
    #: span) rather than on each member -- the opposite of
    #: `Q.ARTICULATION_OWNER`, where every member of a chord wears its own
    #: staccato. Naming one glyph and hoisting is how a per-glyph decision
    #: stays a per-glyph decision.
    FERMATA_OWNER = "fermata_owner"
    #: Which NOTEHEAD an ornament is printed against.
    #:
    #: ⚠️ A NOTEHEAD, NEVER A REST -- the one place this differs from
    #: `Q.FERMATA_OWNER`, which shares its shape. A trill is played ON a note;
    #: a pause hangs over whatever is sounding, most often a whole-bar rest.
    #: `_mxl_note` says the same thing from the other side: it refuses
    #: `<ornaments>` on a rest (`if not is_rest`) and emits `<fermata>`
    #: regardless.
    ORNAMENT_OWNER = "ornament_owner"
    WEDGE_ANCHOR = "wedge_anchor"
    DYNAMIC = "dynamic"                      # the spelled word
    DIRECTION = "direction"                  # the accepted direction text
    INSTRUMENT = "instrument"
    SLOT_INDEX = "slot_index"
    PART_PARTITION = "part_partition"
    STAFF_ORDINAL = "staff_ordinal"
    SYSTEM_STAFF_COUNT = "system_staff_count"

    # ── evaluate-stage consequences ─────────────────────────────────────────
    PITCH = "pitch"                          # position + clef + key
    ACCIDENTAL = "accidental"                # respelled when the key settles
    PART_NAME = "part_name"


# ─────────────────────────────────────────────────────────────────────────────
# WHAT KIND OF CLAIM DOES A QUANTITY'S VALUE MAKE?
#
# Sean, 2026-09-17: "yes every fact should carry what kind of claim."
#
# ⚠️⚠️ THE AXIS IS *WHAT WOULD MAKE THIS ROW WRONG*, and it is chosen that way
# because the one fault this field is known to have cost anything is a POOLING
# fault. `positional_store.PositionIndex` pooled a detector's
# `noteheadBlackOnLine` box with the INK BLOB that box merely overlaps and
# reported Litolff's notehead at mean height **3.646 staff spaces**; split on
# the claim, the same rows read `detector_class` **1.316 ± 0.133** and
# `overlaps` **6.872 ± 2.346**, and the two publishers then AGREE on all four
# shared classes. Nothing was re-measured -- the store had been recording the
# distinction all along and the index was not reading it.
#
# ⚠️⚠️ IT IS A SECOND AXIS, NOT A REFINEMENT OF `capture.UNSCORED`, AND THAT IS
# MEASURED RATHER THAN ASSERTED. `UNSCORED` partitions the SCORELESS quantities
# by what kind of scoreless FACT the value is (a unit, a page geometry, a
# staff-grid position). Neither table determines the other:
#
#   * `UNSCORED`'s `not_a_mark` holds `DOCUMENT_IDENTITY`, `ROSTER_ENTRY`,
#     `DOSSIER_FACT` and `CLEF_SEED` -- which come from a CATALOG or a DOSSIER
#     and cannot fall silent when the plate is bad -- BESIDE `MARGIN_LABEL` and
#     `DIRECTION_WORD`, which are OCR readings of this raster and fail exactly
#     when it degrades. That is the `source_kind` doctrine's own distinction,
#     pooled under one word.
#   * `MEASUREMENT` here spans four of `UNSCORED`'s seven words.
#
# So they are kept APART and made unable to CONTRADICT: `CLAIM_OF_UNSCORED`
# below states which claim kinds each `UNSCORED` word admits, and
# `capture.unaccounted()` fails on a violation. One rule, two tables, checked --
# never a fifth hand-written copy.
#
# ⚠️ A CLAIM KIND CONTRIBUTES; IT NEVER DECIDES (`A-INK-4`). Nothing here
# vetoes, gates or thresholds anything. It is a LABEL, so that a consumer that
# wants to weigh an identity claim differently from a coverage claim is able to
# see the difference at all -- which today it is not.
# ─────────────────────────────────────────────────────────────────────────────


class CLAIM(_Vocab):
    """What kind of claim a quantity's value makes -- i.e. what would make it
    wrong. Five words, each naming a distinct failure mode.

    ⚠️ The test for membership is the FAILURE MODE, never the stage that
    produced the value and never the reader. `READERS.DETECTOR` yields a CLASS
    (an argmax, scored) and a BOX (a ruler reading) on one row, so the reader
    cannot tell you which this is -- measured before this vocabulary was
    written, and it is why the declaration is keyed on the QUANTITY.
    """

    #: A ruler applied to THIS raster. A length, a coordinate, a box.
    #:
    #: ⚠️ It asserts NO identity, so it cannot be wrong about what the ink is
    #: -- only about where the ruler was laid (wrong frame, wrong grid, wrong
    #: unit). `score is None` follows from that rather than being a separate
    #: rule: a ruler reading is not a guess, and `Q.NOTEHEAD_STAFF_POSITION`
    #: has carried `score=None` for exactly this reason since it was written.
    MEASUREMENT = "measurement"

    #: THIS raster's ink named from a vocabulary -- an argmax, a template
    #: match, an OCR decode.
    #:
    #: ⚠️ It CAN be wrong about what the ink is, which is the whole of the
    #: difference from `COVERAGE`. It is also the claim that falls silent with
    #: the plate: an identification and a bar-sum arbitration of it are read
    #: off the same ink, which is CLAUDE.md's "the bars are not an independent
    #: umpire over a bad reading".
    IDENTIFICATION = "identification"

    #: One piece of ink OVERLAPS, ENCLOSES or is EXPLAINED BY another.
    #:
    #: ⚠️⚠️ EXPLICITLY NOT AN ASSERTION OF IDENTITY, and this is the word the
    #: measured fault crossed. `positional_store.Membership.kind`'s own
    #: docstring already said so -- "`overlaps` is `ink_explained_by`, which
    #: its own docstring says is coverage and NOT an assertion of identity" --
    #: and the index pooled it with `detector_class` anyway. A coverage claim
    #: is wrong only if the two things do not in fact overlap; it is NOT wrong
    #: when the name is wrong, because it never made the name its own.
    COVERAGE = "coverage"

    #: Asserted by a document that is NOT this raster -- a catalog, a dossier,
    #: the encoding a page was rendered from.
    #:
    #: ⚠️ It is wrong if the external document is wrong or was joined to the
    #: wrong subject, and it CANNOT be wrong because the plate is bad. That is
    #: exactly the property CLAUDE.md's `source_kind` doctrine turns on -- "if
    #: you want a second witness that does not fall silent exactly when it is
    #: needed, it must not come off the same raster" -- and it is why pooling
    #: these with OCR readings under one word loses the distinction the
    #: doctrine is made of. `Observation.derived_from` is the structural half
    #: of the same fact and stays exactly as it is.
    EXTERNAL = "external"

    #: The outcome of weighing other facts already on the record -- a fit, a
    #: vote, an adjudication, a consequence.
    #:
    #: ⚠️ Its ancestry is other rows, not the raster, so it is wrong if the
    #: weighing was wrong OR if anything under it was. It is the one kind
    #: whose error is inherited.
    INTERPRETATION = "interpretation"


#: ⚠️⚠️ EVERY MEMBER OF `Q` DECLARES ONE, and `claims_unaccounted()` fails when
#: a new quantity does not -- so a quantity cannot enter the vocabulary without
#: its author saying what sort of claim it makes. The table lives HERE, beside
#: `Q`, so it cannot drift from the thing it describes.
#:
#: ⚠️ A quantity declares the claim its VALUE makes, not every claim its
#: producer makes in passing. `Q.GLYPH_BOX`'s value is a class AND a box; the
#: class is what a consumer reads it for and what can be wrong about the ink,
#: so it is an IDENTIFICATION -- and its box being a ruler reading is precisely
#: why `Q.GLYPH_CONF` and the family POSITION facts are separate quantities at
#: all. That is `capture`'s own argument for why a position may not be a field
#: on the shape row, arriving here from the other side.
CLAIMS: "dict[str, str]" = {
    # ── page and cell geometry: rulers, all of them ────────────────────────
    "STAFF_LINES": CLAIM.MEASUREMENT,
    "STAFF_SPACING": CLAIM.MEASUREMENT,
    "CELL_STAFF_SPACE": CLAIM.MEASUREMENT,
    "CELL_BOX": CLAIM.MEASUREMENT,
    "CELL_POSITION_BASIS": CLAIM.MEASUREMENT,
    "STAFF_EXTENT": CLAIM.MEASUREMENT,
    "STAFF_SKEW": CLAIM.MEASUREMENT,
    "BARLINE_COLUMN": CLAIM.MEASUREMENT,
    #: ⚠️ A JUDGEMENT CALL, NAMED — a narrow scan at a system's shared left
    #: edge, filed MEASUREMENT because its value is *how much ink stands
    #: there*. `OMR_LEFT_EDGE_SPLIT` then reads it as evidence of a system
    #: break, which is the INTERPRETATION built ON it and not this row.
    "LEFT_EDGE_INK": CLAIM.MEASUREMENT,
    "STAFF_ORDINAL": CLAIM.MEASUREMENT,
    "SYSTEM_STAFF_COUNT": CLAIM.MEASUREMENT,

    #: ⚠️ A JUDGEMENT CALL, NAMED — COVERAGE, not measurement, though both are
    #: counts and `UNSCORED` files them as page geometry.
    #: `gap_bridging_counts` is ink CROSSING a
    #: gap and `Q.SYSTEMIC_COLUMN` a column crossing EVERY gap. Both say that
    #: something spans something else and neither says what the something IS
    #: -- `OMR_BRACKET_COLUMNS` exists because that count was read as though
    #: it named brackets, and CLAUDE.md records that nothing detects a bracket
    #: at all.
    "GAP_BRIDGING": CLAIM.COVERAGE,
    "SYSTEMIC_COLUMN": CLAIM.COVERAGE,
    #: ⚠️ A JUDGEMENT CALL, NAMED — INTERPRETATION against `UNSCORED`'s
    #: `page_geometry`. It is the block index `_assign_groups` READ, i.e. the
    #: output of the grouping rule rather than a property of the page, and
    #: CLAUDE.md records that NOTHING DETECTS A BRACKET at all: family
    #: boundaries are INFERRED from where the interior barlines stop.
    "BRACKET_BLOCK": CLAIM.INTERPRETATION,

    # ── detection: the ink, and what we call it ────────────────────────────
    "GLYPH_BOX": CLAIM.IDENTIFICATION,
    "NOTEHEAD_CLASS": CLAIM.IDENTIFICATION,
    "REST": CLAIM.IDENTIFICATION,
    "FLAG": CLAIM.IDENTIFICATION,
    "AUG_DOT": CLAIM.IDENTIFICATION,
    "TUPLET_MARKER": CLAIM.IDENTIFICATION,
    "ARC_BOX": CLAIM.IDENTIFICATION,
    "ARTICULATION_MARK": CLAIM.IDENTIFICATION,
    "FERMATA_MARK": CLAIM.IDENTIFICATION,
    "ORNAMENT_MARK": CLAIM.IDENTIFICATION,
    "DYNAMIC_LETTER": CLAIM.IDENTIFICATION,
    "WEDGE_BOX": CLAIM.IDENTIFICATION,
    "BEAM_STROKE": CLAIM.IDENTIFICATION,
    "CLEF_GLYPH": CLAIM.IDENTIFICATION,
    "CLEF_LOCATED": CLAIM.IDENTIFICATION,
    "KEYSIG_MARKER": CLAIM.IDENTIFICATION,
    "METER_GLYPH": CLAIM.IDENTIFICATION,
    #: ⚠️ A JUDGEMENT CALL, NAMED, for both template rows: an NCC match
    #: produces a SCORE, which reads like a fit, and `UNSCORED` files the
    #: key-signature template's fit as `derived_fit`. These are filed
    #: IDENTIFICATION because the VALUE is the meter the ink is read AS, and
    #: a template reading `9/4` where the plate prints `9/8` is wrong about
    #: ink — which is the scan-side blocker CLAUDE.md records at length. The
    #: score is how confident that naming is, not a second claim.
    "METER_TEMPLATE": CLAIM.IDENTIFICATION,
    "METER_TEMPLATE_AT_BAR": CLAIM.IDENTIFICATION,
    #: ⚠️ A JUDGEMENT CALL, NAMED. A CV stem is scoreless and is a pair of
    #: endpoints, which reads like a ruler -- but the rung has already decided
    #: the run of ink IS a stem, and `_stem_joined` consumes it as one. It is
    #: filed with the thing it can be wrong about.
    "STEM": CLAIM.IDENTIFICATION,
    #: ⚠️ A MEASUREMENT WHERE `STEM` IS AN IDENTIFICATION, AND THE PAIR IS THE
    #: POINT. `Q.STEM` has already decided the run of ink IS a stem and
    #: `_stem_joined` consumes it as one; this row asserts no identity at all
    #: -- it is a box, an area, and a note of which filter fired. So it cannot
    #: be wrong about what the ink is, only about where the ruler was laid.
    #: `score is None` follows, as it does for `NOTEHEAD_STAFF_POSITION`.
    "VERTICAL_RUN": CLAIM.MEASUREMENT,
    #: ⚠️⚠️ THE ONE QUANTITY WHOSE CLAIM DEPENDS ON ITS READER, and the only
    #: one in the vocabulary. `gather_margin_labels` resolves the rung at
    #: RUNTIME (`_RUNG_READER.get(rung, READERS.TEXT_LAYER)`), and the rungs
    #: do not make the same kind of claim: the PDF's own TEXT LAYER reads no
    #: ink at all, so it cannot be wrong because the plate is bad, while
    #: Surya, Tesseract and the paid Vision rung are OCR of this raster and
    #: fail exactly when it degrades. `MARGIN_LABEL` reading `Tr. Alt.` as a
    #: SINGER is the OCR half being wrong about ink; the text-layer half
    #: cannot make that mistake.
    #:
    #: ⚠️ Declaring one word for both would have to pick the WEAKER claim
    #: (IDENTIFICATION) to stay safe, which silently denies the free rung the
    #: standing `source_kind` doctrine gives it -- exactly the pooling this
    #: whole axis exists to stop, one layer down from the notehead height.
    #:
    #: ⚠️⚠️ IT WAS MISSED BY MEASUREMENT FIRST. A walk of `gather.py`'s AST
    #: reported only TWO reader-split quantities (`BEAM_STROKE`, `WEDGE_BOX`)
    #: and both split on SCORE rather than on claim -- so the first draft of
    #: this table retired the per-reader form as unnecessary. The walker sees
    #: LITERAL reader arguments and this site has none. **An AST measurement
    #: of a runtime-resolved value is a measurement of the AST.**
    "MARGIN_LABEL": {
        "text_layer": CLAIM.EXTERNAL,
        "surya": CLAIM.IDENTIFICATION,
        "tesseract": CLAIM.IDENTIFICATION,
        "vision": CLAIM.IDENTIFICATION,
    },
    #: ⚠️ Reader-split too (`READERS.TESSERACT` / `READERS.SURYA`, resolved at
    #: runtime) and NOT claim-split: both rungs are OCR of this raster, so one
    #: word is the honest answer rather than a simplification.
    "DIRECTION_WORD": CLAIM.IDENTIFICATION,
    #: ⚠️ A JUDGEMENT CALL, NAMED.
    #: ⚠️ THE PDF'S OWN TEXT OBJECTS, not a reading of ink -- "the PDF's own
    #: text, if any", the FREE rung of the identity cascade. It reads no
    #: raster, so it does not degrade with the print, which is the property
    #: `CLAIM.EXTERNAL` names. Filed IDENTIFICATION in this table's first
    #: draft by its neighbours rather than by its source; corrected by
    #: reading the producer.
    "TEXT_LAYER": CLAIM.EXTERNAL,
    #: ⚠️ A JUDGEMENT CALL, NAMED — a SCORE, not a second claim about ink. It
    #: is the detector's own confidence in an identification, carried apart so
    #: a consumer can read it without reading the class, and its failure mode
    #: is that identification's. Filed with the claim it is a confidence IN
    #: rather than given a word of its own, because a claim kind is about what
    #: would make a row WRONG and this row is wrong exactly when the class is.
    "GLYPH_CONF": CLAIM.IDENTIFICATION,

    #: ⚠️ A JUDGEMENT CALL, NAMED, AND THE ONE THE QUANTITY GRAIN CANNOT HOLD.
    #: ⚠️⚠️ RAW INK IS NOT AN IDENTIFICATION AND THAT IS THE POINT OF THE
    #: LAYER. `Q.INK` is one connected piece of ink with a box and no name;
    #: Sean, 2026-09-17: "ink is ink. There is nothing that should be
    #: classified as unseen - only unclassified." Its detector coverage is an
    #: ATTRIBUTE that may be zero -- a COVERAGE claim riding on a MEASUREMENT
    #: row, which is the DETAIL-GRAIN limit `claims_unaccounted` records.
    "INK": CLAIM.MEASUREMENT,

    # ── relations between things already located ───────────────────────────
    #: ⚠️ A JUDGEMENT CALL, NAMED — MEASUREMENT and not COVERAGE, though
    #: `UNSCORED` files both this and `GLYPH_LADDER` as `relation`. A distance
    #: to each candidate staff is a ruler reading between two things already
    #: located; it asserts no overlap and no identity, which is why CLAUDE.md
    #: can say of it that "distance is nearly a coin flip" without that being
    #: a claim about what the glyph IS.
    "GLYPH_BAND_DISTANCE": CLAIM.MEASUREMENT,
    #: ⚠️ A JUDGEMENT CALL, NAMED — COVERAGE against the same `relation` word.
    #: Whether an unbroken run of ledger rungs JOINS a notehead to a staff. It
    #: names nothing; it says one thing reaches another.
    "GLYPH_LADDER": CLAIM.COVERAGE,

    # ── the family POSITION facts: rulers on their own ink ─────────────────
    "NOTEHEAD_STAFF_POSITION": CLAIM.MEASUREMENT,
    "REST_POSITION": CLAIM.MEASUREMENT,
    "ARC_POSITION": CLAIM.MEASUREMENT,
    "ARTICULATION_POSITION": CLAIM.MEASUREMENT,
    "FERMATA_POSITION": CLAIM.MEASUREMENT,
    "ORNAMENT_POSITION": CLAIM.MEASUREMENT,
    "TUPLET_MARKER_POSITION": CLAIM.MEASUREMENT,
    "METER_GLYPH_POSITION": CLAIM.MEASUREMENT,
    "CLEF_POSITION": CLAIM.MEASUREMENT,
    "KEYSIG_RUN_POSITION": CLAIM.MEASUREMENT,
    "DYNAMIC_BAND_POSITION": CLAIM.MEASUREMENT,
    "DIRECTION_BAND_POSITION": CLAIM.MEASUREMENT,
    "WEDGE_BAND_POSITION": CLAIM.MEASUREMENT,

    # ── facts from a document that is not this raster ──────────────────────
    "DOCUMENT_IDENTITY": CLAIM.EXTERNAL,
    "ROSTER_ENTRY": CLAIM.EXTERNAL,
    "DOSSIER_FACT": CLAIM.EXTERNAL,
    "CLEF_SEED": CLAIM.EXTERNAL,
    #: ⚠️ A JUDGEMENT CALL, NAMED. `Q.INPUT_DOMAIN` is scanned-vs-engraved, and
    #: `input_domain._classify_page` reads the PDF's own object graph -- vector
    #: drawings against one full-page raster -- not the rendered pixels. It is
    #: a fact about the FILE, and like the other externals it does not degrade
    #: with the print.
    "INPUT_DOMAIN": CLAIM.EXTERNAL,

    # ── fits, votes, adjudications and consequences ────────────────────────
    "KEYSIG_CLEF_FIT": CLAIM.INTERPRETATION,
    "KEYSIG_TEMPLATE_FIT": CLAIM.INTERPRETATION,
    "CLEF_REFUSAL_BRANCH": CLAIM.INTERPRETATION,
    "SYSTEM_MEMBERSHIP": CLAIM.INTERPRETATION,
    "STAFF_GROUP": CLAIM.INTERPRETATION,
    "MEASURE_PARTITION": CLAIM.INTERPRETATION,
    "GROUP_SYMBOL": CLAIM.INTERPRETATION,
    "CLEF": CLAIM.INTERPRETATION,
    "KEY_SIGNATURE": CLAIM.INTERPRETATION,
    "METER": CLAIM.INTERPRETATION,
    "DURATION": CLAIM.INTERPRETATION,
    "EVENT": CLAIM.INTERPRETATION,
    "ONSET_COLUMN": CLAIM.INTERPRETATION,
    "VOICES": CLAIM.INTERPRETATION,
    "STEM_DIRECTION": CLAIM.INTERPRETATION,
    "TUPLET_RATIO": CLAIM.INTERPRETATION,
    "GLYPH_OWNER": CLAIM.INTERPRETATION,
    "NOTEHEAD_IS_A_WHOLE_REST": CLAIM.INTERPRETATION,
    "ARC_KIND": CLAIM.INTERPRETATION,
    "ARC_OWNER": CLAIM.INTERPRETATION,
    "ARTICULATION_OWNER": CLAIM.INTERPRETATION,
    "FERMATA_OWNER": CLAIM.INTERPRETATION,
    "ORNAMENT_OWNER": CLAIM.INTERPRETATION,
    "WEDGE_ANCHOR": CLAIM.INTERPRETATION,
    "DYNAMIC": CLAIM.INTERPRETATION,
    "DIRECTION": CLAIM.INTERPRETATION,
    "INSTRUMENT": CLAIM.INTERPRETATION,
    "SLOT_INDEX": CLAIM.INTERPRETATION,
    "PART_PARTITION": CLAIM.INTERPRETATION,
    "PITCH": CLAIM.INTERPRETATION,
    "ACCIDENTAL": CLAIM.INTERPRETATION,
    "PART_NAME": CLAIM.INTERPRETATION,
}


#: ⚠️⚠️ THE RECONCILIATION WITH `capture.UNSCORED`, STATED AS A CONSTRAINT
#: RATHER THAN AS A FIFTH COPY OF THE RULE. Each `UNSCORED` word admits only
#: these claim kinds; `capture.unaccounted()` imports this and fails on a
#: violation, so the two tables can disagree about a quantity for exactly as
#: long as it takes a derived check to run.
#:
#: ⚠️ It is a CONSTRAINT and not a mapping, because the relation is genuinely
#: many-to-many: `not_a_mark` admits two claim kinds, and `MEASUREMENT` is
#: admitted by four `UNSCORED` words. Writing it as a function in either
#: direction would have forced a merge the evidence refuses.
CLAIM_OF_UNSCORED: "dict[str, tuple]" = {
    "staff_grid_position": (CLAIM.MEASUREMENT,),
    "page_geometry": (CLAIM.MEASUREMENT, CLAIM.COVERAGE,
                      CLAIM.INTERPRETATION),
    "unit": (CLAIM.MEASUREMENT,),
    "raw_ink": (CLAIM.MEASUREMENT, CLAIM.IDENTIFICATION),
    "relation": (CLAIM.MEASUREMENT, CLAIM.COVERAGE),
    "not_a_mark": (CLAIM.EXTERNAL, CLAIM.IDENTIFICATION),
    "derived_fit": (CLAIM.INTERPRETATION,),
}


#: value -> NAME, so `claim_of` takes either spelling and the two cannot
#: drift. Derived from `Q` itself; never hand-listed.
_QNAME: "dict[str, str]" = {
    v: k for k, v in vars(Q).items()
    if not k.startswith("_") and isinstance(v, str)}
_QNAME.update({k: k for k in list(_QNAME.values())})


def claim_of(quantity: str, reader: "str | None" = None) -> str:
    """The kind of claim `quantity`'s value makes.

    ⚠️ Raises on an undeclared quantity rather than returning a default. A
    fallback here would convert "nobody said" into a definite answer, which is
    the failure this repo has paid for at three levels in one day -- and the
    whole value of the field is that it cannot be wrong by omission.

    ⚠️⚠️ AND IT RAISES ON A READER-SPLIT QUANTITY ASKED WITHOUT A READER,
    rather than picking one. `Q.MARGIN_LABEL` is EXTERNAL off the PDF's text
    layer and IDENTIFICATION off an OCR rung; answering with either where the
    caller did not say would be this repo's own "a fallback must never convert
    cannot-tell into a definite answer", in the one place the whole field
    exists to prevent it.
    """
    try:
        declared = CLAIMS[_QNAME[quantity]]
    except KeyError:
        raise ValueError(
            f"{quantity!r} declares no claim kind. Add it to record.CLAIMS "
            f"beside Q -- say whether its value is a ruler reading, a naming "
            f"of ink, a statement of coverage, an external document's "
            f"assertion, or the outcome of weighing other facts.") from None
    if isinstance(declared, str):
        return declared
    if reader is None:
        raise ValueError(
            f"{quantity!r} makes a different kind of claim depending on which "
            f"reader produced the row ({'/'.join(sorted(set(declared.values())))}"
            f"), so it cannot be answered without one. Pass the row's reader.")
    try:
        return declared[reader]
    except KeyError:
        raise ValueError(
            f"{quantity!r} is reader-split and declares no claim for reader "
            f"{reader!r}. Add it to record.CLAIMS -- a reader missing from a "
            f"split declaration is a row nobody has said anything about."
        ) from None


def claims_of(quantity: str) -> "tuple":
    """Every claim kind `quantity` can make, over all its readers.

    For the cross-table constraint, which asks about a QUANTITY and has no
    row in hand.
    """
    declared = CLAIMS[_QNAME[quantity]]
    if isinstance(declared, str):
        return (declared,)
    return tuple(sorted(set(declared.values())))


def claims_unaccounted() -> "list[str]":
    """Every `Q` member with no declared claim kind, and every declaration
    that names no `Q` member.

    ⚠️ THE HARD TIER, AND IT IS AT ZERO WHEN THIS LANDS -- so it CAN be a
    gate, which `no_producer --check` notoriously cannot. There is
    deliberately NO gap list beside this one: a claim kind costs one word, so
    an "accounted" tier here could only ever record that somebody declined to
    think.

    ⚠️ The entries that genuinely need a REASON are the DISAGREEMENTS between
    this table and `capture.UNSCORED`, and they live on `capture.KNOWN_GAPS`
    with the rest -- one gap machinery, not a second one, so closing an entry
    removes it and the existing stale-entry test enforces the removal. The
    JUDGEMENT CALLS inside this table are marked at their own entries above
    with `⚠️ A JUDGEMENT CALL, NAMED`, because a judgement is a decision with
    a reason and not a gap waiting to close.
    """
    qs = {k for k, v in vars(Q).items()
          if not k.startswith("_") and isinstance(v, str)}
    out = [f"Q.{q} declares no claim kind" for q in sorted(qs - set(CLAIMS))]
    out += [f"CLAIMS names {q!r}, which is not a member of Q"
            for q in sorted(set(CLAIMS) - qs)]
    for q, c in sorted(CLAIMS.items()):
        # ⚠️ A reader-split declaration is checked PER READER. A dict whose
        # values are fine but which is empty, or which maps a reader to a
        # non-word, would otherwise walk past the same guard the plain form
        # gets.
        words = [c] if isinstance(c, str) else list(c.values())
        if not words:
            out.append(f"CLAIMS[{q!r}] is a reader-split declaration naming "
                       f"no reader at all")
        for w in words:
            if w not in CLAIM.all():
                out.append(f"CLAIMS[{q!r}] is {w!r}, which is not a CLAIM "
                           f"word")
        if isinstance(c, dict) and len(set(c.values())) == 1:
            out.append(
                f"CLAIMS[{q!r}] is split by reader and every reader makes the "
                f"SAME claim -- say it once, or the split implies a "
                f"distinction the pipeline does not have")
    return out


class READERS(_Vocab):
    """Who produced a row. Named, because two rows from the same reader on
    the same crop are ONE signal (see `adjudicate.Evidence.independent`)."""

    DETECTOR = "detector"                    # the production YOLO weights
    DETECTOR_HEADER = "detector_header"      # the same weights on a header crop
    SPECIALIST = "specialist"                # OMR_CLEF_WEIGHTS
    CV_LOCATOR = "cv_locator"                # clef_locator
    CV_LINES = "cv_lines"                    # line_detection: stems, beams
    #: `hairpin_detection` -- a SEPARATE reader from CV_LINES, not a mode of
    #: it. Two rows from one reader on one crop are ONE signal
    #: (`adjudicate.Evidence.independent`), and this rung reads the WHOLE page
    #: with staff lines INTACT while `line_detection` reads an ERASED cell.
    #: Filing them together would collapse two genuinely independent readings
    #: of the same band into one.
    CV_HAIRPINS = "cv_hairpins"              # hairpin_detection: wedge ink
    #: `gather_ink` -- connected components of a cell's ink.
    #:
    #: ⚠️⚠️ IT IS NOT INDEPENDENT OF `CV_LINES` AND A CONSUMER MUST NOT COUNT
    #: THEM AS TWO WITNESSES. This rung reads the SAME image `line_detection`
    #: reads -- `cell.image_no_staff`, the staff-line-erased cell -- so a stem
    #: this reader reports as a tall thin component and a stem `CV_LINES`
    #: reports are ONE reading of ONE crop wearing two names. It is a separate
    #: READER name only because it answers a different question (where is the
    #: ink) from a different algorithm (components, not morphology), which is
    #: what makes the rows separately interpretable; it is emphatically NOT
    #: the `CV_HAIRPINS` case one line up, where the two rungs read different
    #: images and the independence is real.
    CV_INK = "cv_ink"                        # gather_ink: connected components
    CV_HEADER = "cv_header"                  # header_ink
    TEMPLATE = "template"                    # symbol_library NCC matching
    GEOMETRY = "geometry"                    # staff_detector / measure_extractor
    TEXT_LAYER = "text_layer"                # the PDF's own text
    SURYA = "surya"                          # local OCR
    TESSERACT = "tesseract"
    VISION = "vision"                        # the paid rung
    DOSSIER = "dossier"                      # the work's MusicXML
    CATALOG = "catalog"                      # IMSLP work page
    CARRY = "carry"                          # this fact, read on another system


class ABSTAIN(_Vocab):
    """Why a reader that RAN produced nothing.

    ⚠️ Every one of these is information. `ABSENT` -- no row at all -- is the
    only state that carries none.
    """

    # geometry
    SYSTEM_TOO_SMALL = "system_too_small"        # _assign_groups :596
    NO_COLUMN_EVIDENCE = "no_column_evidence"    # _assign_groups :611
    NO_SYSTEM = "no_system"                      # assign_systems :672
    NO_STAFF_GEOMETRY = "no_staff_geometry"
    NO_BARLINE = "no_barline"

    # ⚠️ The CV clef locator's own rejecting branches, spelled EXACTLY as the
    # reader spells them (`clef_locator._note`). Keeping the reader's own word
    # is the difference between "the reader told us why" and "we bucketed it".
    # `locate_clef(trace=...)` has always been able to say this and NEITHER
    # pipeline call site passes a trace, so today every one of these is lost.
    OCCUPIED = "occupied"
    CLUSTER_TOO_BIG = "cluster_too_big"
    NO_CLUSTERS = "no_clusters"
    DOT_VETO = "dot_veto"
    OFF_STAFF = "off_staff"
    STAFF_LEFT_UNMEASURABLE = "staff_left_unmeasurable"
    AMBIGUOUS_SNAP = "ambiguous_snap"
    ASYMMETRIC = "asymmetric"
    F_CLEF_DOTS = "f_clef_dots"
    MEZZOSOPRANO_SYMMETRY = "mezzosoprano_symmetry"
    NO_MASK = "no_mask"
    ONLY_DEBRIS = "only_debris"
    TOO_FAR_RIGHT = "too_far_right"
    OFF_STAFF_ONLY = "off_staff_only"

    # readers with nothing to read
    NO_INK = "no_ink"
    NO_DETECTIONS = "no_detections"
    NO_TEXT_LAYER = "no_text_layer"
    READER_UNAVAILABLE = "reader_unavailable"    # no .venv-surya, no tesseract
    BUDGET_EXHAUSTED = "budget_exhausted"

    # readers that will not guess
    BELOW_THRESHOLD = "below_threshold"
    AMBIGUOUS = "ambiguous"
    NOT_IN_LEXICON = "not_in_lexicon"
    #: An OCR rung ran over a crop and returned NO CHARACTERS AT ALL. ⚠️ A
    #: DIFFERENT FACT FROM `NOT_IN_LEXICON`, and the direction reader is why:
    #: Surya "either reads a crop or says nothing", and on one 1870 Beethoven
    #: 5 page it said nothing about 53 of 74 crops a person reads at a glance,
    #: while Tesseract read 72 of 74 and the LEXICON refused most of them.
    #: Folding the two together would report a silent decoder and a refused
    #: reading as one number and hide which rung is the limit.
    NO_READING = "no_reading"
    NEEDS_CLEF = "needs_clef"                    # key_signature_locator :310
    NO_TEMPLATE = "no_template"                  # e.g. 4/8 has none
    OUT_OF_SCOPE = "out_of_scope"
    #: We LOOKED IN THE CATALOG and it does not hold this document.
    #:
    #: ⚠️ A DIFFERENT FACT FROM `OUT_OF_SCOPE`, which means we declined to
    #: look, and the document-identity rung is why both are needed: flag-off
    #: and *this PDF is not in the score library* are different situations
    #: with different repairs (flip the flag; or name the work with
    #: `OMR_WORK_ID`). Folding them together would report a disabled reader
    #: and an unknown plate as one number -- the shape `NO_READING` was added
    #: to prevent one family over.
    NOT_IN_CATALOG = "not_in_catalog"

    # the build itself
    NOT_IMPLEMENTED = "not_implemented"           # ⚠️ a declared stub


# ─────────────────────────────────────────────────────────────────────────────
# The three row types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Observation:
    """A quantity read off the raster. NEVER a name, NEVER an interpretation.

    ⚠️ THE INVARIANT, REFINED 2026-09-07 AFTER IT WAS FOUND TOO STRONG:

        A row read off THIS RASTER has no ancestors.
        A row DERIVED FROM AN EXTERNAL DOCUMENT carries that document's row.

    The first draft said `basis` is empty "by definition", and that was a
    modelling error with a live consequence. A dossier does not observe this
    page: it supplies a fact about the WORK, which is then joined to a staff.
    So `Q.CLEF_SEED` and a dossier-derived `Q.INSTRUMENT` are both DERIVED
    FROM ONE SOURCE -- and with empty bases they share no ancestor, so the
    correlation check saw two independent witnesses where there is one.

    That is the dossier hazard in its second form. It stops being
    self-reference (the clef reading back its own seed, which the staged split
    really does dissolve) and becomes DOUBLE-COUNTING, which is more insidious
    because it looks like two independent pieces of evidence agreeing.

    `derived_from` is how an external fact's descendants carry it. The closure
    is still finite and cheap: it terminates at the external row, which has no
    ancestors of its own.
    """

    id: str
    subject: Subject
    quantity: str
    value: Any
    reader: str
    frame: str
    score: float | None = None
    detail: Mapping[str, Any] = field(default_factory=dict)

    #: An Observation has no ancestors. Present so evidence of either kind can
    #: be walked uniformly by the circularity filter.
    basis: tuple[str, ...] = ()

    @property
    def claim(self) -> str:
        """What kind of claim this row makes -- see `CLAIM`.

        ⚠️⚠️ DERIVED, NOT STORED, AND THAT IS THE STRONGER FORM OF "no row can
        carry a wrong one by omission". A field with a default can be left
        unset by any of the construction paths `Log.observe` does not own --
        `dataclasses.replace`, a test fixture, a record rebuilt by
        `readjudicate` -- and would then read as a definite answer nobody
        gave. A property cannot be omitted, cannot be set to the wrong word,
        and cannot go stale when `CLAIMS` is corrected.

        ⚠️ It is also why every committed record stays BYTE-IDENTICAL: no
        field means nothing new in `to_json`. Serialising it would change
        every record this repo has written, which is the hazard CLAUDE.md
        already records paying for `Verdict.single_pass_revision` -- that key
        was left out of `to_json` for exactly this reason. Whether to pay it
        here is a separate decision and it is Sean's, not this change's; a
        JSON-only consumer derives the claim from the `quantity` and `reader`
        the row already carries, which is what `claim_of` takes.

        ⚠️ The READER is passed because one quantity's claim depends on it:
        `Q.MARGIN_LABEL` is EXTERNAL off the PDF's own text layer and
        IDENTIFICATION off an OCR rung. A row knows its own reader, so the
        right answer is always available here -- which is exactly why the
        split belongs on the row and not on the quantity alone.
        """
        return claim_of(self.quantity, self.reader)

    def to_json(self) -> dict:
        return {"id": self.id, "subject": self.subject.to_key(),
                "quantity": self.quantity, "value": self.value,
                "reader": self.reader, "frame": self.frame,
                "score": self.score, "detail": dict(self.detail),
                "basis": list(self.basis)}


@dataclass(frozen=True)
class Abstention:
    """A reader RAN on this subject and declined.

    ⚠️ Not the same as never running, and that difference is the whole of
    `State`. `system_grouping` knows which of its branches it took and today
    throws that away by writing the same 0 from all four.
    """

    id: str
    subject: Subject
    quantity: str
    reader: str
    frame: str
    reason: str
    detail: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"id": self.id, "subject": self.subject.to_key(),
                "quantity": self.quantity, "reader": self.reader,
                "frame": self.frame, "reason": self.reason,
                "detail": dict(self.detail)}


@dataclass(frozen=True)
class Verdict:
    """An adjudicated fact. Produced only in ADJUDICATE. Reads no raster.

    Every field below `reason` is filled by the HARNESS, not by the decision.
    That is mechanism 3: the decision is not asked to be honest about what it
    was missing, it is not consulted.
    """

    id: str
    subject: Subject
    quantity: str
    outcome: Outcome
    value: Any | None
    decider: str
    reason: str

    # ── harness-filled ──────────────────────────────────────────────────────
    considered: tuple[str, ...] = ()
    #: What the DECISION says it actually weighed, as against `considered`,
    #: which is what the harness handed it.
    #:
    #: ⚠️ ADDED 2026-09-07 BY THE SECOND FIND OF THE SAME SWEEP. `Ruling.used`
    #: was filled by five decisions and dropped by the harness, exactly as
    #: `Ruling.detail` was. The two are NOT the same fact: a decision handed
    #: ten rows may weigh three, and "what was available" and "what counted"
    #: are different questions -- the gap between them is where a decision
    #: quietly ignores evidence it declared.
    used: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()      # declared, and the log held NOTHING
    declined: tuple[str, ...] = ()     # declared, and a reader ABSTAINED
    excluded: tuple[tuple[str, str], ...] = ()   # (row_id, why)
    correlated: tuple[frozenset[str], ...] = ()  # groups counted once
    basis: tuple[str, ...] = ()

    #: Every value still admitted, ordered by support, best first.
    #:
    #: Present on a NARROWED verdict by definition, and OPTIONAL on a DECIDED
    #: one — where it carries the contest the winner won, which is what lets a
    #: later consumer see that a decision was close without re-deriving it.
    candidates: tuple = ()

    margin: float | None = None
    supersedes: str | None = None

    #: This revision's cause DEPENDS ON the value being revised, and that is
    #: declared, bounded and single-pass. (Sean's call, 2026-09-09.)
    #:
    #: ⚠️⚠️ THE ONE EXEMPTION FROM THE FIXPOINT GUARD, AND IT IS PER-VERDICT
    #: RATHER THAN GLOBAL SO IT CANNOT SPREAD BY ACCIDENT.
    #:
    #: The guard refuses any revision reachable from its own cause. That is
    #: right for a genuine fixpoint and too strict for the pipeline's ONE
    #: sanctioned loop: durations vote the meter, then the meter re-reads the
    #: durations. UNROLLED that is a straight line -- `duration_v1 -> meter ->
    #: duration_v2` -- and it runs once and stops; `transcribe` has run
    #: exactly this loop for as long as the meter has been read, on the stated
    #: rule "vote once, repair once".
    #:
    #: ⚠️ WHAT MAKES IT SAFE IS THE BOUND, NOT THIS FLAG. `reconcile_duration`
    #: searches only the levels a note ADMITS, changes at most ONE note, the
    #: corrected bar must land EXACTLY on the meter, and the answer must be
    #: UNIQUE -- so it cannot iterate even in principle. A rule that cannot
    #: state such a bound must not set this.
    single_pass_revision: bool = False

    #: What the decision computed on its way to the answer -- the clef's per
    #: candidate scores, the meter's agreement share, ownership's
    #: `would_win_on_distance`.
    #:
    #: ⚠️ ADDED 2026-09-07 AFTER A TEST FOUND IT MISSING. `Ruling.detail` was
    #: filled by three decisions and DROPPED by the harness, so every one of
    #: those numbers was computed and thrown away -- the exact failure this
    #: architecture exists to stop, occurring inside it. Found because a test
    #: asserted on a field that did not exist; fixed in the code rather than
    #: the test.
    detail: Mapping[str, Any] = field(default_factory=dict)

    @property
    def claim(self) -> str:
        """What kind of claim this verdict's VALUE makes -- see `CLAIM`.

        ⚠️ A verdict is not automatically `CLAIM.INTERPRETATION`. The claim is
        a property of the QUANTITY, and the two questions come apart: an
        INTERPRETATION is a value whose ancestry is other rows, while "this
        row was produced in ADJUDICATE" is already on the record structurally
        (it is a `Verdict` and not an `Observation`). Keying the field on the
        row type would have made it a second, weaker copy of that fact.

        ⚠️ Derived and not serialised, for the reason `Observation.claim`
        gives at length.
        """
        return claim_of(self.quantity)

    def __post_init__(self) -> None:
        if self.outcome is Outcome.ABSTAINED:
            if self.value is not None:
                raise ValueError(
                    "an ABSTAINED verdict must carry value=None; "
                    "a decision that has a value has not abstained")
            if self.candidates:
                raise ValueError(
                    "an ABSTAINED verdict may not carry candidates -- a "
                    "decision holding survivors has NARROWED, not abstained, "
                    "and collapsing the two throws away the narrowing")
        if self.outcome is Outcome.DECIDED and self.value is None:
            raise ValueError(
                "a DECIDED verdict must carry a value; "
                "use Outcome.ABSTAINED to say 'I have no answer'")
        if self.outcome is Outcome.NARROWED:
            if self.value is not None:
                raise ValueError(
                    "a NARROWED verdict must carry value=None -- if one "
                    "candidate won, the outcome is DECIDED")
            if len(self.candidates) < 2:
                raise ValueError(
                    "a NARROWED verdict needs at least two candidates; with "
                    "one it has DECIDED and with none it has ABSTAINED")

    def to_json(self) -> dict:
        return {"id": self.id, "subject": self.subject.to_key(),
                "quantity": self.quantity, "outcome": self.outcome.value,
                "value": self.value, "decider": self.decider,
                "reason": self.reason, "considered": list(self.considered),
                "used": list(self.used),
                "missing": list(self.missing), "declined": list(self.declined),
                "excluded": [list(e) for e in self.excluded],
                "correlated": [sorted(g) for g in self.correlated],
                "candidates": [c.to_json() for c in self.candidates],
                "basis": list(self.basis), "margin": self.margin,
                "supersedes": self.supersedes, "detail": dict(self.detail)}


Row = Union[Observation, Abstention, Verdict]


# ─────────────────────────────────────────────────────────────────────────────
# The log
# ─────────────────────────────────────────────────────────────────────────────


class AlreadyAdjudicated(RuntimeError):
    """A second verdict on one (subject, quantity) without `revises=`.

    This is how the single-pass regime becomes a property of the machine
    rather than a promise. All three of the existing pipeline's propagations
    are single-pass -- no `while`, no repeat-until-stable -- and this design
    keeps that. A decision that genuinely must revise an earlier one declares
    `revises=` and carries a bound, on the model of
    `_reconcile_measure_to_meter`: re-read a beam level by +/-1 ONLY, the bar
    must land EXACTLY on the meter, the answer must be UNIQUE, single-voice
    measures only, and never add, delete or re-pitch a note.
    """


class UphillConsequence(RuntimeError):
    """A verdict tried to supersede one that is in its own `basis`.

    That is the fixpoint, refused mechanically. This project has twice
    declined to build a convergence argument; the harness makes declining the
    default. If you hit this, do not build a fixpoint -- record the tension.
    """


class Log:
    """Append-only. There is no `update`, no `set`, and no `del`.

    "The current clef" is a QUERY over this log, never a stored field, which
    is why nothing here can go stale the way `clef_final` (9 of 20 stale),
    `key_signature_final` (19 of 26) and `time_signature_final` (no keeper at
    all) did. A value must be re-maintained by every later writer; an event
    describes a moment and cannot be wrong later.
    """

    __slots__ = ("_obs", "_abs", "_vrd", "_by_subject", "_n", "_frozen")

    def __init__(self) -> None:
        self._obs: dict[str, Observation] = {}
        self._abs: dict[str, Abstention] = {}
        self._vrd: dict[str, Verdict] = {}
        # (quantity, subject_key) -> list of row ids, in emission order
        self._by_subject: dict[tuple[str, str], list[str]] = {}
        self._n = 0
        self._frozen = False

    # ── writing ─────────────────────────────────────────────────────────────

    def _next_id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}:{self._n:06d}"

    def _index(self, quantity: str, subject: Subject, row_id: str) -> None:
        self._by_subject.setdefault((quantity, subject.to_key()), []).append(row_id)

    def observe(self, subject: Subject, quantity: str, value: Any, *,
                reader: str, frame: str, score: float | None = None,
                derived_from: Sequence[str] = (),
                **detail: Any) -> Observation:
        """Record a measurement.

        ⚠️ `value` is required and positional. There is deliberately no
        `observe_if(...)` and no default: a reader that has nothing to say
        calls `abstain`, which forces it to say WHY.

        ⚠️ `derived_from` is for rows that come from an EXTERNAL document
        rather than from this raster -- a dossier's clef, a catalog roster's
        instrument. It is what stops one external source being counted twice
        when two of its descendants both reach a decision. A row read off the
        page leaves it empty.
        """
        if self._frozen:
            raise RuntimeError("the log is frozen; GATHER is over")
        Q.check(quantity, "quantity")
        READERS.check(reader, "reader")
        # ⚠️ THE CLAIM KIND IS CHECKED AT THE WRITE, not at serialisation.
        # `Observation.claim` derives it, so a quantity with no declaration --
        # or a reader missing from a split one -- would otherwise raise the
        # first time somebody READ the field, arbitrarily far from the gather
        # site that produced the row and quite possibly never. Asking here
        # makes it fail on the run that introduces it, with the reader in
        # hand.
        claim_of(quantity, reader)
        for rid in derived_from:
            if self.row(rid) is None:
                raise ValueError(
                    f"derived_from names {rid!r}, which is not in this log. "
                    f"An external fact's descendants must carry the row they "
                    f"came from, or the correlation check cannot see them as "
                    f"one signal.")
        row = Observation(self._next_id("obs"), subject, quantity, value,
                          reader, frame, score, dict(detail),
                          tuple(derived_from))
        self._obs[row.id] = row
        self._index(quantity, subject, row.id)
        return row

    def abstain(self, subject: Subject, quantity: str, *, reader: str,
                frame: str, reason: str, **detail: Any) -> Abstention:
        """Record that a reader looked and declined. `reason` is required."""
        if self._frozen:
            raise RuntimeError("the log is frozen; GATHER is over")
        Q.check(quantity, "quantity")
        READERS.check(reader, "reader")
        ABSTAIN.check(reason, "abstention reason")
        row = Abstention(self._next_id("abs"), subject, quantity, reader,
                         frame, reason, dict(detail))
        self._abs[row.id] = row
        self._index(quantity, subject, row.id)
        return row

    def record(self, verdict: Verdict) -> Verdict:
        """Append a verdict. Enforces the single-pass regime."""
        prior = self.verdict(verdict.quantity, verdict.subject)
        if prior is not None and verdict.supersedes != prior.id:
            raise AlreadyAdjudicated(
                f"{verdict.quantity} on {verdict.subject.to_key()} is already "
                f"decided by {prior.decider} ({prior.id}). A second "
                f"adjudication must declare revises= and carry a bound.")
        if verdict.supersedes is not None:
            # ⚠️ THE SUPERSEDED VERDICT IS EXCLUDED FROM ITS OWN CHECK, and
            # getting this wrong made the guard forbid the one thing the
            # architecture explicitly permits.
            #
            # A REVISION READS WHAT IT REVISES -- `reconcile_duration` takes
            # the old duration's `written` value and re-reads its beam level,
            # so the old verdict is necessarily in the new one's basis. The
            # first version of this check refused exactly that, which meant
            # the single bounded loop in the pipeline could never fire.
            #
            # THE REAL FIXPOINT is deriving the new value through something
            # that itself DEPENDS ON the old one: if the meter had been voted
            # out of these very durations, then meter -> duration -> meter is
            # a cycle and no bound saves it. So the test is whether the
            # superseded verdict reappears in the closure of the OTHER inputs.
            others = tuple(b for b in verdict.basis if b != verdict.supersedes)
            reachable = set()
            for rid in others:
                reachable |= self.closure(rid)
            if verdict.supersedes in reachable and \
                    not verdict.single_pass_revision:
                raise UphillConsequence(
                    f"{verdict.id} supersedes {verdict.supersedes}, and reaches "
                    f"it again through its other inputs. That is a fixpoint -- "
                    f"the new value was derived through something that depends "
                    f"on the value it replaces. Do not build one; record the "
                    f"tension and escalate. If the loop is genuinely SINGLE "
                    f"PASS and the rule's bound makes iteration impossible, "
                    f"the rule may declare single_pass=True -- deliberately, "
                    f"and per rule.")
        self._vrd[verdict.id] = verdict
        self._index(verdict.quantity, verdict.subject, verdict.id)
        return verdict

    def freeze(self) -> None:
        """End GATHER. After this no measurement may be added, so every
        decision in ADJUDICATE sees the same frozen record -- which is what
        makes 'the info flows in any direction' safe rather than merely
        permitted, and what makes adjudication order free."""
        self._frozen = True

    @property
    def frozen(self) -> bool:
        return self._frozen

    # ── reading ─────────────────────────────────────────────────────────────

    def _ids(self, quantity: str, subject: Subject,
             scope: Scope) -> Iterator[str]:
        if scope is Scope.EXACT:
            yield from self._by_subject.get((quantity, subject.to_key()), ())
            return
        if scope is Scope.SELF_AND_ANCESTORS:
            wanted = (subject,) + subject.ancestors()
            for sub in wanted:
                yield from self._by_subject.get((quantity, sub.to_key()), ())
            return
        # SELF_AND_DESCENDANTS -- scan, because descendants are not enumerable
        for (q, key), ids in self._by_subject.items():
            if q != quantity:
                continue
            if subject.contains(Subject.from_key(key)):
                yield from ids

    def rows(self, quantity: str, subject: Subject, *,
             scope: Scope = Scope.EXACT) -> tuple[Observation, ...]:
        return tuple(self._obs[i] for i in self._ids(quantity, subject, scope)
                     if i in self._obs)

    def refusals(self, quantity: str, subject: Subject, *,
                 scope: Scope = Scope.EXACT) -> tuple[Abstention, ...]:
        return tuple(self._abs[i] for i in self._ids(quantity, subject, scope)
                     if i in self._abs)

    def verdicts(self, quantity: str, subject: Subject, *,
                 scope: Scope = Scope.EXACT) -> tuple[Verdict, ...]:
        return tuple(self._vrd[i] for i in self._ids(quantity, subject, scope)
                     if i in self._vrd)

    def verdict(self, quantity: str, subject: Subject) -> Verdict | None:
        """The CURRENT verdict: the last one not superseded by a later one.

        There is no cached copy of this anywhere, which is the point.
        """
        found = self.verdicts(quantity, subject)
        if not found:
            return None
        superseded = {v.supersedes for v in found if v.supersedes}
        live = [v for v in found if v.id not in superseded]
        return live[-1] if live else found[-1]

    def state(self, quantity: str, subject: Subject, *,
              scope: Scope = Scope.EXACT) -> State:
        """⚠️ The three-state answer. A consumer that treats DECLINED and
        ABSENT alike has thrown away the reason a reader gave."""
        if self.rows(quantity, subject, scope=scope):
            return State.READ
        if self.refusals(quantity, subject, scope=scope):
            return State.DECLINED
        return State.ABSENT

    def row(self, row_id: str) -> Row | None:
        return self._obs.get(row_id) or self._abs.get(row_id) or self._vrd.get(row_id)

    def all_verdicts(self) -> tuple[Verdict, ...]:
        """Every verdict in the log, superseded ones included.

        ⚠️ Unlike `verdict()` this does NOT resolve supersession -- it is for
        asking what the log CONTAINS (coverage, blind spots), not what it
        currently concludes. A consumer that wants the live answer per subject
        must go through `verdict()`.
        """
        return tuple(self._vrd.values())

    def all_rows(self) -> tuple[Row, ...]:
        return tuple(self._obs.values()) + tuple(self._abs.values()) + \
            tuple(self._vrd.values())

    def subjects(self, kind: Kind) -> tuple[Subject, ...]:
        seen: dict[str, Subject] = {}
        for _q, key in self._by_subject:
            sub = Subject.from_key(key)
            anc = sub.at(kind)
            if anc is not None:
                seen[anc.to_key()] = anc
        return tuple(sorted(seen.values()))

    # ── provenance ──────────────────────────────────────────────────────────

    def closure(self, row_id: str) -> frozenset[str]:
        """Every row id `row_id` transitively rests on, including itself.

        Cheap because an Observation's basis is empty by definition, so the
        walk always terminates at the raster.
        """
        out: set[str] = set()
        stack = [row_id]
        while stack:
            rid = stack.pop()
            if rid in out:
                continue
            out.add(rid)
            row = self.row(rid)
            if row is not None:
                stack.extend(row.basis)
        return frozenset(out)

    def quantities_in_closure(self, row_id: str) -> frozenset[str]:
        return frozenset(
            r.quantity for r in (self.row(i) for i in self.closure(row_id))
            if r is not None)

    # ── serialisation ───────────────────────────────────────────────────────

    def to_json(self) -> dict:
        return {
            "observations": [o.to_json() for o in self._obs.values()],
            "abstentions": [a.to_json() for a in self._abs.values()],
            "verdicts": [v.to_json() for v in self._vrd.values()],
            "counts": {"observations": len(self._obs),
                       "abstentions": len(self._abs),
                       "verdicts": len(self._vrd)},
        }

    def summary(self) -> dict:
        """Per-quantity counts, for a human skimming a run.

        Deliberately reports abstentions BESIDE observations rather than as a
        shortfall: a quantity with 0 observations and 400 abstentions is a
        reader working correctly on material it cannot read, and a quantity
        with 0 of both is a reader that never ran. Those are different
        problems and a single "coverage" number hides which one you have.
        """
        out: dict[str, dict[str, int]] = {}
        for o in self._obs.values():
            out.setdefault(o.quantity, {}).setdefault("read", 0)
            out[o.quantity]["read"] += 1
        for a in self._abs.values():
            out.setdefault(a.quantity, {}).setdefault("declined", 0)
            out[a.quantity]["declined"] += 1
        for v in self._vrd.values():
            key = "decided" if v.outcome is Outcome.DECIDED else "abstained"
            out.setdefault(v.quantity, {}).setdefault(key, 0)
            out[v.quantity][key] += 1
        return {k: out[k] for k in sorted(out)}
