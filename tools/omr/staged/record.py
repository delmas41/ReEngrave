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
    STEM = "stem"                            # CV stem: x, y0, y1
    BEAM_STROKE = "beam_stroke"              # CV beam stroke centre
    FLAG = "flag"                            # detected flag
    AUG_DOT = "aug_dot"                      # dot offset from its notehead
    TUPLET_MARKER = "tuplet_marker"          # digit or bracket, with its span
    ARC_BOX = "arc_box"                      # slur/tie ink, before attribution
    ARTICULATION_MARK = "articulation_mark"  # mark + the side its class names
    WEDGE_BOX = "wedge_box"                  # hairpin ink
    DYNAMIC_LETTER = "dynamic_letter"        # one letter, before spelling

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
    METER_GLYPH = "meter_glyph"              # timeSig digits / C / cut-C
    METER_TEMPLATE = "meter_template"        # the template reader's score

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
    GLYPH_OWNER = "glyph_owner"
    ARC_OWNER = "arc_owner"
    ARC_KIND = "arc_kind"                    # tie | slur
    TUPLET_RATIO = "tuplet_ratio"
    ARTICULATION_OWNER = "articulation_owner"
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


class READERS(_Vocab):
    """Who produced a row. Named, because two rows from the same reader on
    the same crop are ONE signal (see `adjudicate.Evidence.independent`)."""

    DETECTOR = "detector"                    # the production YOLO weights
    DETECTOR_HEADER = "detector_header"      # the same weights on a header crop
    SPECIALIST = "specialist"                # OMR_CLEF_WEIGHTS
    CV_LOCATOR = "cv_locator"                # clef_locator
    CV_LINES = "cv_lines"                    # line_detection: stems, beams
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
    NEEDS_CLEF = "needs_clef"                    # key_signature_locator :310
    NO_TEMPLATE = "no_template"                  # e.g. 4/8 has none
    OUT_OF_SCOPE = "out_of_scope"

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
