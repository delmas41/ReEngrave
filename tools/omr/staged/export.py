"""EXPORT — a MusicXML file, and a record of what did not reach it.

⚠️ **THIS IS NOT A PORT OF `tools/omr/export.py`.** It takes that module's
POSITIONS — nine "detected then dropped on the way out" bugs were paid for
there and each is a rule stated below — and it reuses its pure renderers
(`_mxl_note`, `_mxl_attributes_block`, `_mxl_measure_rest`, `_score_partwise`,
`voicing.group_chords_in_measure`), because those ARE the positions in
executable form. What it does not take is the structure: the legacy exporter
walks nested page dicts and infers what it can; this reads a record in which
every fact was decided by a named decision that also recorded its evidence.

⚠️⚠️ **AND IT EMITS A COVERAGE RECORD BESIDE THE FILE, WHICH IS THE POINT.**
The bug class this project has paid for nine times is a signal recognised and
then lost between the reader and the file. `export_coverage.py` catches it
after the fact by comparing our output against a truth file. Here the exporter
says it itself: for every notation family MusicXML can carry, `coverage()`
reports how many were written and — when that is zero — WHICH of four
different things is true.

    emitted       we wrote them
    abstained     the decision ran and declined, with its reasons
    stub          the decision is declared `stub=True`
    starved       ...and its input is never gathered either
    NO_QUANTITY   ⚠️ the staged vocabulary has no such quantity AT ALL

⚠️⚠️⚠️ **`NO_QUANTITY` IS THE ONE THAT MATTERS AND RESTS ARE IN IT.** There is
no `Q.REST`, no rest adjudicator, no rest stub and no `wants` naming one —
`grep -rn 'rest' tools/omr/staged/record.py` finds three matches and all three
are the word "rest" inside `*rest` unpacking and "rests on". Meanwhile the
detector puts them in the log: **228 rest glyphs on Beethoven 5 / Litolff p.3,
350 on Brahms 1 p.2, 118 on Mahler 5 p.2**, every one of them in `glyph_box`
and read by nothing. That is the detected-then-dropped family occurring inside
the architecture built to stop it, and it is worse than the four starved
stubs, because a stub at least abstains 2,728 times and says
`not_implemented`. Nothing anywhere declares the rests.

So `coverage()` counts the DETECTIONS for each unrepresented family and prints
them beside the zero — a zero is a suspect, not a result, and this is its
positive control.

    python3 -m tools.omr.staged.export staged.json --out score.musicxml
    python3 -m tools.omr.staged.export staged.json --coverage-only
"""

from __future__ import annotations

import argparse
import collections
import copy
import os
import json
import pathlib
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import export as _legacy
from ..voicing import group_chords_in_measure
from . import adjudicate as A
from .record import Q, meter_at


METER_SEGMENTS_ENV = "OMR_METER_SEGMENTS"
#: `OMR_HOLD_OUT_UNIDENTIFIED` -- a staff the join could not NAME is held out
#: of the file rather than emitted as a part of its own.
#:
#: **Default ON since 2026-09-17 (Sean's call: *"hold out - I want truth"*),**
#: written as a DENY-list because it is default-ON.
#:
#: ⚠️⚠️ EMITTING A PART IS A POSITIVE CLAIM, AND THAT IS THE BUG. A `<part>`
#: says *"here is an instrument"*; what we know about an unnamed staff is
#: *"this music belongs to a part we could not name"*. Turning the second
#: into the first is CANNOT TELL converted into a definite answer -- the
#: failure this file forbids at four other sites -- and it is the loudest
#: one, because on Litolff Beethoven 5 pp.1-4 it invented **25 instruments**
#: on top of the 12 the page prints, and a human opening the artefact could
#: not read it.
#:
#: ⚠️ THE MUSIC IS COUNTED, NEVER SWALLOWED: every note on a held-out staff
#: is dropped under `staff_not_identified` and the accounting control stays
#: an EQUALITY, so the file is smaller and the record still says exactly what
#: was lost and why. That is the whole of *"I want truth"*: the shortfall is
#: visible instead of being dressed as an orchestra.
#:
#: ⚠️ SCOPED TO THE `slot` JOIN, deliberately. On the `fragments` fallback
#: NOTHING is named, so holding out the unidentified would hold out the whole
#: document and write an empty file -- a rule that turns a bad page into no
#: page. There, one part per staff remains the honest answer.
HOLD_OUT_UNIDENTIFIED_ENV = "OMR_HOLD_OUT_UNIDENTIFIED"


def hold_out_unidentified_enabled() -> bool:
    return os.environ.get(HOLD_OUT_UNIDENTIFIED_ENV, "1").strip().lower() \
        not in ("0", "", "false", "no", "off")


WHOLE_REST_INK_ENV = "OMR_WHOLE_REST_INK"


def meter_segments_enabled() -> bool:
    """`OMR_METER_SEGMENTS` — export the meter in force at each BAR.

    **DEFAULT ON since 2026-09-09 (Sean's call.)** `Q.METER` carries
    `segments`, and this exporter used to read only the system's OPENING — so
    a printed mid-system meter change could not reach a MusicXML file at all,
    and `record.meter_at`, whose own docstring says it *is* how a bar's meter
    is read, was called by nothing but its own tests.

    ⚠️ WHAT IT GATES IS A BUG FIX OF THE `computed-and-unread` FAMILY, which
    is why the shipped default is on. Measured strictly better on every
    ENGRAVED fixture: Brahms 1 iv's `¢` — read on 24 staves of 24 at support
    74.0 — went from reaching NO file to reaching all 24 parts, and Beethoven
    5 / Litolff's printed `3/4` moved from the first bar of its system to the
    ninth, which is where the hand-read truth puts it. The boundary tally goes
    ENGRAVED 4 printed / 4 found / 1 -> 0 false.

    ⚠️⚠️ THE STANDING OBJECTION, WHICH THE FLIP OVERRIDES RATHER THAN
    RESOLVES: the boundary benchmark's SCANNED arm still proposes seven false
    segments on one page of one publisher — five spurious `4/4` changes at
    support 3.5-4.0 against a floor of 3.0, read on ONE staff of twenty — and
    with this on, every one of them RE-SIZES BARS IN THE FILE instead of
    sitting inertly on the record. FINDINGS §4b attributes that fixture's
    failure to the meter GLYPH readers rather than to the weighing, and the
    left-fractions confirm it from the other side: each of those segments
    reads 0.000, at the head of its bar where a real change stands, so they
    are misreads and no placement rule can reach them. **The lever is the
    glyph readers (`_meter_from_digits`, `time_signature_locator`), and until
    that lands a scan can export a meter change its page does not print.**

    ⚠️ PRICED, so the cost is a number rather than a worry. On that page —
    Brahms 1 / Breitkopf p.1-2, 14 parts — the flip takes `<time>` elements
    from **41 to 138**: `4/4` declarations 13 -> 96, plus 14 spurious `9/8`
    from the courtesy signature this rule cannot reach there. Every ENGRAVED
    fixture gains only correct changes, and four of the nine committed
    boundary records are byte-identical either way.

    ⚠️ Set `0` to restore the per-run meter exactly. Flag-off is byte-identical
    to the pre-2026-09-09 exporter and is asserted so, per page and per
    fixture; a system that prints no change is byte-identical either way BY
    CONSTRUCTION, which is what bounds the blast radius to pages carrying a
    read change.

    ⚠️⚠️ THE TEST IS A DENY-LIST, NOT AN ALLOW-LIST, AND THE DIRECTION FLIPPED
    WITH THE DEFAULT. `_carry_meter` reads *"anything but an explicit 1 is
    off"* because a typo must not switch a document ONTO a mechanism whose
    hazard is a whole wrong movement. On by default the hazard runs the other
    way: with an allow-list (`in ("1", "true", "yes", "on")`, which is what
    `OMR_SLOT_STITCH` and the other default-on flags here use) an empty value
    or a typo silently RESTORES the bug, and a flag that fails closed on a
    misspelling is a flag nobody can trust in an environment file. Only an
    explicit off word turns it off. ⚠️ Worth knowing: the default-on flags
    that use the allow-list form have this hazard today — this one does not
    copy it.

    See `benchmarks/omr-staged-meter-segments-2026-09/FINDINGS.md`.
        ⚠️ `""` COUNTS AS OFF, matching `OMR_LEFT_EDGE_SPLIT` and
    `OMR_DIRECTION_TEXT` — the repo's existing idiom for a `"1"`-defaulted
    flag, and what `test_roster.py::test_flag_parsing` already pins. It is a
    genuinely ambiguous value (`OMR_X=` may be a deliberate blank or an
    expanded-but-unset variable) and this does NOT settle that; it declines to
    fork a third convention over it. A flag whose DEFAULT is `""` — choir
    grouping, bracket columns, keysig corroboration, cell line trace — must of
    course read empty as ON, or its default would be off.
"""
    return os.environ.get(METER_SEGMENTS_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


def whole_rest_ink_enabled() -> bool:
    """`OMR_WHOLE_REST_INK` — refuse to write a NOTE where the record says the
    ink is a whole rest (`Q.NOTEHEAD_IS_A_WHOLE_REST`).

    **DEFAULT ON, which is the behaviour that shipped on 2026-09-15.** The flag
    exists so the decision to keep it is Sean's and reversible in one word, not
    because anything measured against it. Off restores the pre-2026-09-15
    exporter exactly: the verdict is still DECIDED and still on the record, and
    only the refusal — and its `ink_is_a_whole_rest` count — goes away.

    ⚠️⚠️ **WHY IT IS FLAGGED AT ALL WHEN NOTHING ELSE IN THIS FAMILY IS: IT
    DELETES NOTES.** Every other staged repair adds an element or withholds one
    the record never decided; this one removes 22 pitched `<note>` elements
    from a file a human would otherwise clean up by hand. The evidence for it
    is strong and it is the right kind — 25 of 25 fires cropped and read
    against the print, zero of them a real note — but it is **one document, one
    publisher, four pages of ~16**, on the *low-res bitonal* end of the corpus,
    and `benchmarks/omr-note-where-silence-2026-09/FINDINGS.md` §3 records that
    **two of the six cuts sit on a plateau one step wide or less**. A
    behaviour that deletes music on evidence that thin belongs behind a switch.

    ⚠️ **THE CUTS ARE A DERIVATION, NOT A FIT, AND THAT IS NOT THE SAME AS
    GENERALISING.** They are the p05/p95 of the document's OWN 395 correctly
    detected `restWhole` glyphs, so they were not chosen to fit the suspects —
    but they are percentiles of one plate's rests. A print whose whole rests
    are thinner, or whose staves are cleaner, gives a different band, and two
    of the cuts have no plateau to absorb it. **Breitkopf Brahms 1 p0-3 is
    where this should be re-measured**, the same second document the meter
    floors and the dotted rest both need.

    ⚠️ **NO OMR-NED FIGURE CAN SETTLE IT.** The metric is symmetric and rewards
    under-prediction, so it would pay for these deletions whether or not they
    were right — which is why the evidence is crops, and why a score must never
    be quoted as the reason to leave this on.

    ⚠️ **A DENY-LIST, BECAUSE THE DEFAULT IS ON.** With an allow-list
    (`in ("1", "true", "yes", "on")`) an empty value or a typo would silently
    restore the pre-flag behaviour — here that means silently putting the
    phantom notes back — and `tools/omr/tests/test_flag_default_direction.py`
    derives this from the source and fails on the wrong direction. Only an
    explicit off word turns it off. ⚠️ `""` counts as OFF, matching
    `OMR_METER_SEGMENTS` and `OMR_LEFT_EDGE_SPLIT`, the repo's idiom for a
    `"1"`-defaulted flag.

    See `benchmarks/omr-note-where-silence-2026-09/FINDINGS.md`.
    """
    return os.environ.get(WHOLE_REST_INK_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


# ─────────────────────────────────────────────────────────────────────────────
# Reading the record
# ─────────────────────────────────────────────────────────────────────────────


def _parse_subject(key: str) -> Dict[str, Optional[int]]:
    """`"glyph/2/0/1/4/9"` -> page/system/staff/cell/glyph.

    Mirrors `record.Subject.from_key`'s field order without importing a Log:
    the exporter's input is the SERIALISED record, so it works equally on a
    live run and on a file somebody saved a week ago.
    """
    head, *rest = key.split("/")
    fields = ("page", "system", "staff", "cell", "glyph")
    out: Dict[str, Optional[int]] = {f: None for f in fields}
    out["kind"] = head                                    # type: ignore[assignment]
    for name, value in zip(fields, rest):
        out[name] = int(value)
    return out


class Unbalanced(RuntimeError):
    """A notehead the log holds reached neither the file nor the drop count.

    ⚠️ An exception rather than a flag, because the flag has been tried:
    `symbol_ledger.coverage_check` computed this same control, wrote
    `balanced=False` on 9 of 20 rows, and nothing read it.
    """


class Record:
    """An index over one `run_staged` result. No opinions, just lookups."""

    def __init__(self, result: Dict[str, Any]):
        self.result = result
        rec = result["record"]
        self.observations = rec["observations"]
        self.verdicts = rec["verdicts"]
        self.abstentions = rec["abstentions"]

        # ⚠️ THE STANDING VERDICT, resolved the way `Log.verdict` resolves
        # it: drop every row a later one SUPERSEDES, then take the last of
        # what is left, falling back to the last row when everything was
        # superseded. A consequence may RESTATE a value (`move_glyph`
        # re-pitches a glyph whose owner changed), so taking the first would
        # export what a later decision overturned.
        #
        # On an append-only log this is the same answer as "last wins", and
        # it is written out anyway: the rule lives in `record.py` and a second
        # spelling of it here is how the two drift.
        superseded = {v["supersedes"] for v in self.verdicts if v.get("supersedes")}
        self._v: Dict[Tuple[str, str], Dict[str, Any]] = {}
        _fallback: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for v in self.verdicts:
            key = (v["quantity"], v["subject"])
            _fallback[key] = v
            if v["id"] not in superseded:
                self._v[key] = v
        for key, v in _fallback.items():
            self._v.setdefault(key, v)

        self._o: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for o in self.observations:
            self._o.setdefault((o["quantity"], o["subject"]), []).append(o)

        self._by_q: Dict[str, List[Dict[str, Any]]] = {}
        for v in self.verdicts:
            self._by_q.setdefault(v["quantity"], []).append(v)

    def verdict(self, quantity: str, subject: str) -> Optional[Dict[str, Any]]:
        return self._v.get((quantity, subject))

    def value(self, quantity: str, subject: str) -> Any:
        v = self._v.get((quantity, subject))
        if v is None or v["outcome"] != "decided":
            return None
        return v["value"]

    def obs(self, quantity: str, subject: str) -> List[Dict[str, Any]]:
        return self._o.get((quantity, subject), [])

    def obs_of(self, quantity: str) -> List[Dict[str, Any]]:
        return [o for o in self.observations if o["quantity"] == quantity]

    def verdicts_of(self, quantity: str) -> List[Dict[str, Any]]:
        return self._by_q.get(quantity, [])


# ─────────────────────────────────────────────────────────────────────────────
# The score model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Cell:
    """One measure of one staff, and the notes decided into it."""
    page: int
    system: int
    staff: int
    index: int
    detections: List[Dict[str, Any]] = field(default_factory=list)
    #: `(x_page, kind, text)` -- EXACTLY the shape `_mxl_empty_measure` and
    #: `_mxl_direction` already take, so the renderers are reused rather than
    #: re-spelled. `kind` is "dynamics" or "words".
    directions: List[Tuple[float, str, str]] = field(default_factory=list)
    #: `(kind, [x, y, w, h])` per arc this bar holds, in PAGE pixels and in
    #: the WIDTH form `_merge_arcs_across_barlines` reads -- see `_place_arcs`
    #: for why the record's own corner form is converted here and not there.
    arcs: List[Tuple[str, List[float]]] = field(default_factory=list)


@dataclass
class StaffRun:
    """One staff of one system: its header facts and its measures."""
    key: str
    page: int
    system: int
    staff: int
    clef: Optional[str] = None
    fifths: Optional[int] = None
    meter: Optional[Dict[str, Any]] = None
    n_measures: int = 0
    #: Whether `measure_partition` DECIDED this staff's bar count, as opposed
    #: to abstaining. ⚠️ `n_measures` collapses the two — an abstention and a
    #: decided zero both read 0 — and the document-wide numbering needs them
    #: apart: an abstaining staff says NOTHING about its system's bar count
    #: and must not be counted as a dissenting vote for zero, while a system
    #: on which NO staff decided is a system whose length we cannot tell.
    n_measures_decided: bool = False
    name: Optional[str] = None
    cells: Dict[int, Cell] = field(default_factory=dict)
    #: This staff's own page geometry, read for the arc merge. ⚠️ BOTH ARE
    #: PER STAFF AND NOT PER PAGE: a part spans systems, and the staff it is
    #: printed on in system 0 is not the same object as the one in system 1.
    #: A height is only comparable across a system break once it is relative
    #: to each staff's OWN top line, which is why `tops` exists at all.
    spacing: Optional[float] = None
    top_line: Optional[float] = None
    #: `{cell index: [x0, y0, x1, y1]}` -- each bar's own page rectangle,
    #: CORNERS. Absent where `Q.CELL_BOX` abstained, and that absence BREAKS
    #: the merge chain rather than being skipped over (see `_flatten_part`).
    cell_boxes: Dict[int, List[float]] = field(default_factory=dict)
    #: The staff key this run DOUBLES, or `None` for a run built the usual
    #: way from `Q.MEASURE_PARTITION`.
    #:
    #: ⚠️⚠️ ROADMAP 2.1b. Sean, 2026-09-22, on a condensed `Violoncello e
    #: Basso` staff narrowed to exactly [Cello, Contrabass]: "the string
    #: family always includes all five; if there are only four lines the
    #: bass is doubling the celli or it comes in later." `_condensed_double`
    #: builds this run from the CELLO copy's own cells, once, at the join --
    #: the record holds the staff's music ONCE, this field is what says the
    #: file writes it twice. See `docs/DECISIONS.md` 2026-09-22 and
    #: `benchmarks/omr-cello-bass-convention-2026-09/FINDINGS.md`.
    condensed_from: Optional[str] = None


def _staff_key(page: int, system: int, staff: int) -> str:
    return f"staff/{page}/{system}/{staff}"


#: Detail keys stripped off a doubled copy's noteheads and rests, because
#: each names a mark this staff carries ONCE and the print does not repeat
#: it for the second section reading the line -- `Q.ARTICULATION_MARK`,
#: `Q.FERMATA_MARK` and `Q.ORNAMENT_MARK` are all filed against the
#: notehead's OWN glyph, so a copy that kept them would be a second decided
#: mark the log never recorded. `glyph` is stripped too, and for a sharper
#: reason: `_place_wedges` and `_pair_arcs` (in `to_musicxml`, after the
#: join) find a note by scanning EVERY part for `det["glyph"]` -- keeping it
#: would let a wedge or slur anchored to the Cello copy be found a second
#: time through the doubled one, in whichever part the scan visits last.
#: Stripping it makes the doubled copy invisible to that scan by
#: construction, which is what keeps `wedge_balance` and `arcs_not_written`
#: an EQUALITY over the Cello copy alone.
_CONDENSED_STRIP_KEYS = ("glyph", "articulations", "fermata", "ornaments")


def _condensed_double(source: StaffRun) -> StaffRun:
    """The staff's own music, a second time, for the Contrabass slot.

    ⚠️⚠️ ROADMAP 2.1b -- ONE STAFF'S INK, WRITTEN TWICE, NEVER READ TWICE.
    Sean's rule (`docs/DECISIONS.md` 2026-09-22) is that a condensed
    `Violoncello e Basso` staff is not a guess between two instruments, it is
    the line BOTH play -- so this is not a placement, it is a COPY, taken
    once the Cello slot's own cells hold every note `_place_notes` decided
    for this staff. It runs LAST in the join, after `_place_notes`,
    `_place_articulations`, `_place_fermatas` and `_place_ornaments` have all
    already mutated `source`'s own detections in place, and BEFORE the
    post-join arc and wedge passes in `to_musicxml` -- so what it copies is
    exactly the note/rest content those four functions decided, and none of
    what the two after it have not yet written.
    #
    ⚠️ `directions` AND `arcs` ARE LEFT EMPTY, DELIBERATELY. A direction word
    or a hairpin printed once over a condensed staff is one mark on one line,
    not two; doubling it would need a second, independent accounting for
    every family that already has one over the Cello copy, for a case this
    plate does not exercise (`benchmarks/omr-cello-bass-convention-2026-09/
    FINDINGS.md` §2: neither held plate prints one on a condensed system).
    ⚠️ `_CONDENSED_STRIP_KEYS` says why the notes themselves are stripped of
    marks and a glyph reference.
    """
    cells: Dict[int, Cell] = {}
    for idx, cell in source.cells.items():
        dets = []
        for det in cell.detections:
            copied = copy.deepcopy(det)
            for k in _CONDENSED_STRIP_KEYS:
                copied.pop(k, None)
            dets.append(copied)
        cells[idx] = Cell(source.page, source.system, source.staff, idx,
                          detections=dets)
    return StaffRun(
        key=source.key, page=source.page, system=source.system,
        staff=source.staff, clef=source.clef, fifths=source.fifths,
        meter=source.meter, n_measures=source.n_measures,
        n_measures_decided=source.n_measures_decided,
        # ⚠️ NO NAME OF ITS OWN. The Contrabass part is named from whichever
        # of its runs DOES carry one (`next((r.name for r in part if
        # r.name), None)`, `to_musicxml`'s own rule) -- a system where the
        # plate prints the two apart, or the catalog roster, if either
        # exists anywhere in the document. Stamping a name here would be
        # this rule inventing evidence the page did not give it.
        name=None, cells=cells, spacing=source.spacing,
        top_line=source.top_line, cell_boxes=dict(source.cell_boxes),
        condensed_from=source.key)


#: `<transpose><diatonic>0</diatonic><chromatic>0</chromatic>
#: <octave-change>-1</octave-change></transpose>` -- the double bass's own
#: convention, never written (`benchmarks/omr-cello-bass-convention-2026-09/
#: FINDINGS.md` §1): the WRITTEN pitch is the Cello's, and this is the one
#: MusicXML element that says so sounds an octave lower.
#:
#: ⚠️⚠️ TWO DRAFTS OF THIS BLOCK EACH RAISED IN music21'S OWN READER, AND
#: THE SECOND FAILURE IS THE MORE INSTRUCTIVE ONE. Draft 1 wrote
#: `<octave-change>` alone; the MusicXML 3.1 schema makes `<chromatic>` a
#: REQUIRED child of `<transpose>`, so that was invalid on its own terms.
#: Draft 2 added `<chromatic>0</chromatic>` and STILL raised the identical
#: `TypeError` -- `music21.musicxml.xmlToM21.MeasureParser.
#: xmlTransposeToInterval` seeds `diatonicStep = None` and only ever sets it
#: from a `<diatonic>` element, never from `<chromatic>`, then does
#: `diatonicStep += 7 * octave_change` unconditionally whenever
#: `<octave-change>` is present -- so an octave-only transpose needs
#: `<diatonic>0</diatonic>` too, or that reader cannot compute it, however
#: schema-valid the file is without it. Its own doctest literally names this
#: shape ("doubled one octave down ... mixed cello / bass parts in
#: orchestral literature") and still requires the field. Found by parsing
#: the export back with music21 both times, not by validating the XML
#: against nothing.
#:
#: ⚠️ TEXT SURGERY ON PURPOSE, NEVER A NEW PARAMETER ON THE REUSED RENDERER.
#: `_legacy._mxl_attributes_block` (`tools/omr/export.py`) is LEGACY and
#: FROZEN -- bug fixes only, no new mechanisms (CLAUDE.md §3) -- and this is
#: the one call site in the whole staged path that ever needs `<transpose>`.
#: Widening the shared renderer would make every OTHER caller pass a `None`
#: it will never use.
#:
#: ⚠️ THE INSERTION POINT IS SCHEMA-CORRECT, NOT INCIDENTAL: MusicXML orders
#: `<attributes>` children divisions, key, time, staves, part-symbol,
#: instruments, clef, staff-details, THEN transpose -- and the renderer's own
#: last line before `</attributes>` is always the clef block (or nothing, for
#: a staff whose clef abstained), so appending immediately before the closing
#: tag lands transpose exactly where clef leaves off.
def _insert_transpose(attrs_xml: str, indent: str) -> str:
    closing = f"{indent}</attributes>"
    block = (f"{indent}  <transpose>\n"
             f"{indent}    <diatonic>0</diatonic>\n"
             f"{indent}    <chromatic>0</chromatic>\n"
             f"{indent}    <octave-change>-1</octave-change>\n"
             f"{indent}  </transpose>\n")
    if attrs_xml.endswith(closing):
        return attrs_xml[:-len(closing)] + block + closing
    # ⚠️ Never reached by `_mxl_attributes_block`'s own two return paths, but
    # a fallback that raises on a future third path would fail loud where a
    # silent no-op would fail quiet -- and quiet is what let ten hairpins go
    # uncounted for a day (CLAUDE.md's own `wedge_balance` history).
    return attrs_xml + "\n" + block.rstrip("\n")


def build(rec: Record) -> Tuple[List[List[StaffRun]], Dict[str, Any],
                               Dict[str, int], Dict[str, int]]:
    """The staged record -> parts, each a list of staff-runs in reading order.

    ⚠️ A PART IS THE SAME STAFF ON EVERY SYSTEM, and `part_partition` is the
    decision that says so. The legacy exporter re-derives this in
    `_stitch_slots` and REFUSES when systems disagree about staff count,
    because joining by position would graft one instrument's music onto
    another; here the refusal already happened, upstream, with its reasons
    recorded — `join: "ordinal"` when the counts agree, `deduced_anchor` when
    the slots were excluded as circular. This function consumes the verdict
    and adds no join of its own.
    """
    runs: Dict[str, StaffRun] = {}
    for v in rec.verdicts_of(Q.MEASURE_PARTITION):
        s = _parse_subject(v["subject"])
        key = v["subject"]
        run = runs.setdefault(key, StaffRun(
            key=key, page=s["page"] or 0, system=s["system"] or 0,
            staff=s["staff"] or 0))
        run.n_measures = int(v["value"]) if v["outcome"] == "decided" else 0
        run.n_measures_decided = v["outcome"] == "decided"

    for key, run in runs.items():
        run.clef = rec.value(Q.CLEF, key)
        ks = rec.value(Q.KEY_SIGNATURE, key)
        run.fifths = int(ks) if isinstance(ks, int) else None
        run.meter = rec.value(Q.METER, f"system/{run.page}/{run.system}")
        name = rec.value(Q.PART_NAME, key)
        run.name = name if isinstance(name, str) else None
        # ⚠️ `obs`, NOT `value`. Both are MEASUREMENTS -- a staff's lines and
        # its spacing come off the raster in GATHER and no decision adjudicates
        # them -- so `rec.value`, which reads VERDICTS, returns None for both.
        # It did, silently, and the merge then saw a spacing of 0 and refused
        # every bar: a rule that needs a unit, handed no unit, correctly
        # declining to guess. The tests caught it; nothing in the shape of the
        # output would have.
        sp_rows = rec.obs(Q.STAFF_SPACING, key)
        sp = sp_rows[-1]["value"] if sp_rows else None
        run.spacing = float(sp) if isinstance(sp, (int, float)) else None
        line_rows = rec.obs(Q.STAFF_LINES, key)
        lines = line_rows[-1]["value"] if line_rows else None
        # ⚠️ `min`, not `lines[0]`. The five y positions are a MEASUREMENT and
        # nothing in `Q.STAFF_LINES`'s contract promises they arrive sorted;
        # asking for the smallest says what "the top line" means.
        if isinstance(lines, (list, tuple)) and lines:
            try:
                run.top_line = min(float(y) for y in lines)
            except (TypeError, ValueError):
                run.top_line = None

    # ⚠️ INDEXED ONCE, not re-scanned per staff. `obs_of` is a linear filter
    # over every observation on the record, so asking it inside the loop above
    # makes this quadratic in a page's detections -- ~10,500 of them on three
    # scanned pages.
    for o in rec.obs_of(Q.CELL_BOX):
        cs = _parse_subject(o["subject"])
        if cs["cell"] is None:
            continue
        run = runs.get(_staff_key(cs["page"] or 0, cs["system"] or 0,
                                  cs["staff"] or 0))
        box = o["value"]
        if (run is not None and isinstance(box, (list, tuple))
                and len(box) == 4):
            run.cell_boxes[cs["cell"]] = [float(v) for v in box]

    # ⚠️ PER-SYSTEM AS WELL AS PER-REASON, because the cleanup artefact asks
    # its question one PRINTED SYSTEM at a time and used to re-derive these
    # refusals itself. See `_place_notes._drop`.
    notes_dropped_by_system: Dict[Tuple[int, int], Any] = {}
    # ⚠️⚠️ COMPUTED HERE, BEFORE PLACEMENT, AND ONCE. `build` places notes
    # before it joins parts, so the hold-out set cannot be a by-product of the
    # join loop below -- and deriving it twice is the duplicated-rule fault
    # this file spent 2026-09-17 removing four copies of. The join loop
    # CONSUMES this set rather than re-asking.
    held_out_runs: set = set()
    if hold_out_unidentified_enabled() \
            and (rec.value(Q.PART_PARTITION, "document") or {}).get("join") \
            == "slot":
        for _k in runs:
            if not isinstance(rec.value(Q.SLOT_INDEX, _k), int):
                held_out_runs.add(_k)
    dropped = _place_notes(rec, runs, by_system=notes_dropped_by_system,
                           held_out=held_out_runs)
    # ⚠️ AN EQUALITY, and it is not decoration: it is the only thing that
    # catches a refusal added later at one call site and not the other, which
    # is precisely how the arm's copy went stale in the first place.
    _by_sys_total = sum(sum(c.values())
                        for c in notes_dropped_by_system.values())
    if _by_sys_total != sum(dropped.values()):
        raise Unbalanced(
            "notes refused per system (%d) do not sum to the per-reason total "
            "(%d) -- a refusal reaches one counter and not the other"
            % (_by_sys_total, sum(dropped.values())))
    _place_directions(rec, runs)
    # ⚠️⚠️ THE ARC SHORTFALL IS KEPT APART FROM `dropped`, AND THIS IS NOT
    # TIDINESS. `dropped` feeds `notes_not_written`, which feeds the ACCOUNTING
    # CONTROL: every notehead and rest in the log is either written or counted
    # here, and the two must sum to the log's own rows exactly. Folding arc
    # drops into it would inflate that total by symbols the control does not
    # count on the other side, so `to_musicxml` would raise `Unbalanced` for a
    # reason that has nothing to do with notes -- a control reporting a defect
    # it was not built to see, which is worse than one that stays silent.
    arcs_dropped = collections.Counter(_place_arcs(rec, runs))
    # ⚠️ AFTER `_place_notes`, because a mark hangs on a notehead that has
    # already reached a cell -- and reported in its OWN bucket for the same
    # reason the arcs are: an articulation is not a note, and folding it into
    # `dropped` would make the note balance raise on a different family.
    artics_dropped = _place_articulations(rec, runs)
    # ⚠️ ITS OWN BUCKET, for the same reason the arcs and articulations have
    # one: a fermata is not a note, and folding its shortfall into `dropped`
    # would make the note-accounting control raise about a different family.
    fermatas_dropped = _place_fermatas(rec, runs)
    ornaments_dropped = _place_ornaments(rec, runs)

    # ── the join ────────────────────────────────────────────────────────────
    join = rec.value(Q.PART_PARTITION, "document") or {}
    systems = sorted({(r.page, r.system) for r in runs.values()})
    by_system: Dict[Tuple[int, int], List[StaffRun]] = collections.defaultdict(list)
    for run in runs.values():
        by_system[(run.page, run.system)].append(run)
    for group in by_system.values():
        group.sort(key=lambda r: r.staff)

    counts = {len(by_system[s]) for s in systems}
    kind = join.get("join")
    ordinal_ok = kind == "ordinal" and len(counts) == 1

    parts: List[List[StaffRun]] = []
    # ⚠️⚠️ THE PARTS WE COULD NOT NAME. A part built from a run with no
    # `Q.SLOT_INDEX` is a staff the join REFUSED to identify, not an
    # instrument. The distinction is invisible in the finished `<part>` list
    # and is load-bearing for the tacet padding: padding a fragment asserts
    # *"this instrument is silent on that system"* when what we actually know
    # is *"we could not identify this staff"* -- a fallback converting CANNOT
    # TELL into a definite answer, which this file forbids at four other
    # sites. Measured on Litolff Beethoven 5 pp.1-4: 30 of 37 parts are on
    # exactly ONE system, and padding them wrote 2,924 empty bars and put 25
    # blank staves under every printed system of the artefact a human then
    # could not count.
    unidentified: set = set()
    provenance_extra: Dict[str, Any] = {}
    used = kind
    if ordinal_ok and systems:
        width = len(by_system[systems[0]])
        for i in range(width):
            parts.append([by_system[s][i] for s in systems])
    elif kind == "slot":
        # ⚠️ THE SLOT JOIN IS THE VERDICT'S, AND HONOURING IT IS THE WHOLE
        # POINT OF READING A RECORD. `adjudicate_part_partition` reaches this
        # branch only where the ordinal join REFUSED — systems printing
        # different staff counts — and only where the slot verdicts survived
        # the circularity filter; where they were excluded as a deduced
        # identity it returns `deduced_anchor` instead and this exporter takes
        # the fragment path below.
        #
        # ⚠️ AND THE VERDICT IS KNOWN TO BE WRONG ON 3 OF 27 STAVES ON THE
        # ONE PAGE IT IS MEASURED ON. `adjudicate_part_partition`'s own
        # docstring records it: the slot join fails to continue "4 Hörner in
        # Es" across a tacet break and grafts the tacet "2 Trompeten in C"
        # slot onto the horn. That is not a reason for the EXPORTER to
        # second-guess it — an exporter that overrides a decision it does not
        # like is how a measured judgement goes missing — it is a reason the
        # provenance block says which join was used, so a reader of the FILE
        # can find out without reading this code.
        by_slot: Dict[int, List[StaffRun]] = collections.defaultdict(list)
        stranded = 0
        # ⚠️⚠️ ROADMAP 2.1b. One entry per condensed staff DOUBLED, never per
        # note -- `to_musicxml`'s `Unbalanced` control counts the individual
        # notes under `notes_doubled_to_condensed_slot`; this is the human
        # -readable side of the same fact, kept in `provenance` so a reader
        # of the FILE's report finds it without reading this code.
        condensed_doubling: List[Dict[str, Any]] = []
        for s in systems:
            for run in by_system[s]:
                slot_v = rec.verdict(Q.SLOT_INDEX, run.key)
                slot = slot_v["value"] if slot_v and slot_v["outcome"] == "decided" else None
                if not isinstance(slot, int):
                    stranded += 1
                    if run.key in held_out_runs:
                        # ⚠️ NO PART. See `HOLD_OUT_UNIDENTIFIED_ENV`: the
                        # staff is held out and its music counted, rather
                        # than asserted to be an instrument of its own.
                        held_out_runs.add(run.key)
                        continue
                    # ⚠️⚠️ FLAG OFF -- the pre-2026-09-17 behaviour exactly.
                    # The part is emitted, and the tacet padding must still
                    # not write silence for it on systems it is absent from.
                    unidentified.add(len(parts))
                    parts.append([run])
                    continue
                by_slot[slot].append(run)
                # ⚠️ `condensed_with_slot` IS `collapse_slot_index_to_
                # family_block`'s OWN DETAIL (`inferences.py`), read here and
                # nowhere earlier -- this is the ONE place a Cello-slot
                # placement is turned into a SECOND part, and it is EXPORT's
                # act, not INFER's: the record still holds this staff's music
                # once. A staff placed WITHOUT the detail (named normally, or
                # printed apart from its neighbour) is untouched.
                cwslot = (slot_v.get("detail") or {}).get("condensed_with_slot")
                if isinstance(cwslot, int):
                    by_slot[cwslot].append(_condensed_double(run))
                    condensed_doubling.append({
                        "condensed_from": run.key,
                        "cello_slot": slot,
                        "contrabass_slot": cwslot,
                    })
        for slot in sorted(by_slot):
            parts.append(by_slot[slot])
        provenance_extra = {"slots": sorted(by_slot), "stranded": stranded,
                            "condensed_doubling": condensed_doubling}
    else:
        # ⚠️ THE FRAGMENT FALLBACK IS THE LEGACY BEHAVIOUR AND IS KEPT.
        # One part per system-staff. It pairs with nothing in a reference and
        # scores badly, and it is still right: the alternative is grafting.
        used = "fragments"
        for s in systems:
            for run in by_system[s]:
                # ⚠️ EVERY part on this path is an unidentified staff, by the
                # definition of the fallback: the join refused, so no part
                # here is known to be an instrument that is merely silent
                # elsewhere.
                unidentified.add(len(parts))
                parts.append([run])

    provenance = {
        # ⚠️ THE PART INDICES WE COULD NOT NAME, carried so the tacet padding
        # can decline them. It is on `provenance` rather than a new return
        # value because a reader of the FILE's coverage report should be able
        # to see which parts are fragments without reading this code.
        "unidentified_parts": sorted(unidentified),
        "held_out_staves": len(held_out_runs),
        "join_decided": kind,
        "join_used": used,
        "join_reason": (rec.verdict(Q.PART_PARTITION, "document") or {}).get("reason"),
        "systems": [f"{p}/{s}" for p, s in systems],
        "staves_per_system": sorted(counts),
        "parts": len(parts),
        "fragmented": used == "fragments",
        **provenance_extra,
    }
    # ⚠️ ITS OWN SLOT, not folded into `arcs_dropped`. Two families' drops in
    # one counter is the shape `_claims` was made longest-prefix-wins to
    # prevent: a hairpin claimed by both `dynamic` and `wedge` was counted
    # twice, and a reader cannot unpick one number into two afterwards.
    return (parts, provenance, dropped, arcs_dropped, artics_dropped,
            fermatas_dropped, ornaments_dropped, notes_dropped_by_system)


#: The alterations `respell_accidental` can write, and what each does to a
#: pitch STRING. ⚠️ Derived-checked against the legacy parser rather than
#: restated: `_legacy._parse_pitch` accepts `#`/`b` runs and
#: `_legacy._mxl_pitch_block` maps them to `<alter>`, so a spelling this table
#: invents that the parser cannot read would silently produce a note with no
#: `<pitch>` block at all. `test_sounding_pitch.py` asserts the round trip.
_ALTERATION_SPELLING: Dict[str, str] = {"#": "#", "b": "b"}


def _sounding_pitch(pitch: str, alteration: str) -> str:
    """Fold a key-derived alteration into a pitch string: `E4` + `b` -> `Eb4`.

    ⚠️ WHY A STRING AND NOT AN `<alter>` ARGUMENT. `_legacy._mxl_note` takes
    ONE pitch and derives `<alter>` inside `_mxl_pitch_block` by parsing it,
    which is also how the legacy path has always carried an alteration. Adding
    a second, parallel channel would give the two paths different spellings of
    one fact and leave nothing forcing them to agree.

    ⚠️ IT REFUSES RATHER THAN GUESSES. `_pitch_from_position` -- the only
    producer of `Q.PITCH` -- returns a BARE letter+octave, so a pitch that
    already carries an accidental is not a pitch this function has ever been
    handed, and doubling one (`Eb4` + `b` -> `Ebb4`) would quietly lower a
    note a whole tone. An unparseable pitch, an unknown alteration, or a pitch
    that is already altered is returned UNCHANGED: the caller then writes the
    note it read, which is wrong in the way it was already wrong rather than
    wrong in a new way this function invented.
    """
    spelled = _ALTERATION_SPELLING.get(alteration)
    if spelled is None:
        return pitch
    parsed = _legacy._parse_pitch(pitch)
    if parsed is None:
        return pitch
    letter, existing, octave = parsed
    if existing:
        # Already altered -- an inline accidental would have to come from a
        # reader that does not exist yet. Leave it alone rather than stack.
        return pitch
    return f"{letter}{spelled}{octave}"


def _place_notes(rec: Record, runs: Dict[str, StaffRun],
                 by_system: Optional[Dict[Tuple[int, int], Any]] = None,
                 held_out: Optional[set] = None) -> Dict[str, int]:
    """Every decided note, ONCE PER PIECE OF INK.

    ⚠️ A measure cell is cut with padding above and below so ledger notes are
    not sliced off, so on a conductor's page the same ink is detected once per
    staff and `glyph_owner` arbitrates. The subject coordinate records where
    the glyph was FOUND; the verdict records whose it IS.

    ⚠️⚠️ AND UNTIL 2026-09-11 THIS FUNCTION HONOURED THAT VERDICT BY MOVING
    THE COPY, WHICH DOUBLED IT. Both members of a contest name the same owner
    (measured: 245 of 248 cross-staff notehead pairs on Litolff Beethoven 5
    p1-4), so relocating each of them put two `<note>` elements at one pitch
    into one bar — 688 relocations on four pages. The legacy
    `_dedupe_cross_staff_detections` DELETES the loser; the staged path had
    the same decision and consumed it as a move. It is now a refusal, counted
    under `owned_by_another_staff`; see `A.is_relocated_copy` for why dropping
    can never lose ink the owner's staff does not already hold, and for the
    one exception (a swap) that it can.

    ⚠️ THE OLD DOCSTRING'S WARNING STILL STANDS AND IS EASY TO LOSE HERE.
    It read: *exporting by SUBJECT would put Violin 1's high A on the timpani
    — the documented failure that cost 263 edits.* That is still true of
    placing by subject ALONE. This places by subject AND REFUSES the copy the
    owner disowns, so the timpani's copy is never written and Violin 1's own
    copy — which a contest guarantees exists — is. Delete the refusal and keep
    the subject placement and the 263-edit failure comes straight back.
    """
    dropped: Dict[str, int] = collections.Counter()

    def _drop(reason: str, s: Dict[str, Any]) -> None:
        """Count one refused note, BY REASON and BY SYSTEM at once.

        ⚠️⚠️ `by_system` EXISTS BECAUSE A SECOND COPY OF THESE REFUSALS WENT
        STALE. `benchmarks/omr-cleanup-count-2026-09/build_sheet.py` held its
        own decomposition -- its docstring said *"mirrors `_place_notes`' three
        refusals in order"* -- and by 2026-09-17 there were FIVE: it had never
        heard of `ink_is_a_whole_rest` (2026-09-15) or `owned_by_another_staff`
        (2026-09-11), so it reported 542 held-back notes where this function
        refuses 738. Its own control caught it and refused to write, which is
        the control working; the repair is to stop holding the rule twice, the
        same move `system_map` already made for `_document_bar_offsets`.

        ⚠️ ONE CALL SITE PER REFUSAL, so a refusal added later cannot reach
        the flat total and miss the per-system one. Asserted by the caller:
        the per-system counts must SUM to this function's own return.
        """
        dropped[reason] += 1
        if by_system is not None:
            key = (s["page"], s["system"])
            by_system.setdefault(key, collections.Counter())[reason] += 1

    # ⚠️ READ ONCE, NOT PER NOTEHEAD. It is 2,347 environment lookups on a
    # four-page record, and a flag re-read inside the loop could in principle
    # split one export between two behaviours — which is exactly the kind of
    # half-applied change no count would show.
    refuse_whole_rest_ink = whole_rest_ink_enabled()
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = _parse_subject(sub)
        if s["glyph"] is None:
            continue
        is_rest = bool(rec.obs(Q.REST, sub))
        if not is_rest and not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue                 # neither a notehead nor a rest
        if not is_rest:
            # ⚠️⚠️ ROADMAP 2.4a. FIRST, before the whole-rest question and
            # everything after it, for the same reason `ink_is_a_whole_rest`
            # is checked before pitch and duration: the count should say the
            # load-bearing thing about the row -- *this is not a notehead at
            # all* -- rather than a downstream reason that happens to also be
            # true. `adjudicate_notehead_is_not_a_notehead` ports the legacy
            # path's two notehead-precision filters
            # (`transcribe._drop_clipped_notehead_fragments`,
            # `transcribe._drop_unladdered_noteheads`, neither called from
            # `staged/`) plus the measured-and-never-shipped width floor
            # (`benchmarks/omr-notehead-width-2026-09/FINDINGS.md`).
            #
            # ⚠️ REFUSED, NOT DELETED. The legacy filters call `dets.remove`;
            # this leaves the `Q.GLYPH_BOX` row on the record and refuses to
            # WRITE it, counted under `not_a_notehead:<reason>` so the reason
            # a human would want -- "this box is a barline sliver, not a
            # note" -- survives to the report rather than reading as a
            # generic `no_pitch` or `duration_narrowed` shortfall.
            npv = rec.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
            if (npv is not None and npv["outcome"] == "decided"
                    and npv["value"] is True):
                _drop(f"not_a_notehead:{npv.get('reason', '?')}", s)
                continue
        if (not is_rest and refuse_whole_rest_ink
                and rec.value(Q.NOTEHEAD_IS_A_WHOLE_REST, sub) is True):
            # ⚠️⚠️ SEAN'S OWN OBSERVATION, AND THE ASYMMETRY IS THE REASON.
            # *"in bars where it should be just whole note rest in two four.
            # It's showing an actual quarter note, not a quarter note rest."*
            # `adjudicate_notehead_is_a_whole_rest` has two witnesses saying
            # this ink is a whole rest -- its outline, and the slot an
            # engraver is obliged to hang one in (or a neighbouring bar of
            # this same staff holding one at the same height). Writing a
            # PITCHED NOTE here puts music where the page prints silence, and
            # a wrong note has to be hunted down while a missing one is
            # visible as a gap.
            #
            # ⚠️ REFUSED, NOT CONVERTED. No `<rest>` is written from here: the
            # bar falls to `_mxl_empty_measure`'s padded measure rest, which
            # says *we read nothing in this bar* rather than *we read
            # silence*. Claiming the second needs a `Q.REST` row, and what ink
            # is on the page is a GATHER fact this stage may not manufacture.
            #
            # ⚠️ FIRST, before the pitch and duration tests, so the count says
            # the load-bearing thing about the row -- *this is not a note* --
            # rather than filing it under `no_pitch`, which would be true and
            # beside the point.
            #
            # ⚠️ AND IT IS THE ONE STAGED REPAIR BEHIND A FLAG, because it is
            # the one that DELETES music: `OMR_WHOLE_REST_INK=0` restores the
            # pre-2026-09-15 exporter exactly, leaving the verdict decided and
            # on the record. See `whole_rest_ink_enabled` for why the evidence
            # is strong and still thin -- n = 1 document, and two of the six
            # cuts have no plateau.
            _drop("ink_is_a_whole_rest", s)
            continue
        # ⚠️ A REST HAS NO PITCH AND MUST NOT BE ASKED FOR ONE. Requiring a
        # pitch is what kept rests out of the file for as long as they had no
        # quantity at all; asking for one now would keep them out for a
        # second, subtler reason.
        pitch = None if is_rest else rec.value(Q.PITCH, sub)
        # ⚠️⚠️ THE ALTERATION IS PART OF THE PITCH, NOT A GLYPH ON IT, AND
        # ROUTING IT TO THE GLYPH WAS THIS EXPORTER'S LARGEST SILENT FAULT.
        # `Q.ACCIDENTAL` is declared "respelled when the key settles" and its
        # ONLY producer is `consequences.respell_accidental`, which reads the
        # key signature -- so the row says *this note is altered by the key*,
        # a fact about what SOUNDS. It was handed to `_mxl_note(accidental=)`,
        # which renders `<accidental>`, the glyph the engraver DREW. The
        # renderer's own comment in `export.py` states the distinction and
        # this path inverted it.
        #
        # Measured on Litolff Beethoven 5 pp.1-4: `<alter>` 0, `<accidental>`
        # 334, and all 269 `Q.ACCIDENTAL` verdicts key-derived. Put through
        # Verovio (`probe/renderer_semantics.py`) an E in three flats written
        # that way carries NO `accid.ges` -- it sounds E natural -- AND draws
        # a redundant flat on the note, 4 glyphs where the page prints 3.
        # Wrong in both directions at once.
        #
        # ⚠️ `applied` is set only where the spelling actually MOVED the
        # pitch, so the counter downstream means *notes the key altered* and
        # not *notes that carried a row*. The distinction is real and already
        # has a fixture: `test_staged_duration` injects a `"natural"`
        # accidental to exercise the override guard, and a natural is alter 0
        # -- the bare letter -- so it must fall through here AND must not be
        # counted as an alteration.
        alteration = None if is_rest else rec.value(Q.ACCIDENTAL, sub)
        applied = None
        if pitch is not None and alteration:
            sounding = _sounding_pitch(pitch, alteration)
            if sounding != pitch:
                pitch, applied = sounding, alteration
        dur_v = rec.verdict(Q.DURATION, sub)
        dur = dur_v["value"] if dur_v and dur_v["outcome"] == "decided" else None

        if pitch is None and not is_rest:
            # ⚠️ NO POSITIONAL DEFAULT. A staff whose clef abstained produces
            # no pitches at all (`consequences.restate_pitch`), deliberately,
            # and the exporter must not undo that by writing treble.
            _drop("no_pitch", s)
            continue
        if not isinstance(dur, dict):
            # ⚠️⚠️ THE EXPORTER DOES NOT DECIDE, AND THIS IS THE PLACE IT
            # WOULD BE TEMPTING TO. A NARROWED duration carries its
            # candidates and each candidate's `support`, so collapsing by
            # argmax is one line away — and it would overturn, in the
            # exporter and silently, a decision `adjudicate_duration`
            # explicitly declined to make. That is an argmax with no floor,
            # which is exactly what `Mode.COMPETITIVE`'s mandatory
            # `margin_floor` exists to forbid one stage earlier.
            #
            # A `<note>` needs ONE duration, so a note whose duration is
            # narrowed cannot be written. It is dropped and COUNTED: the
            # shortfall belongs in the record, not in the silence.
            _drop(("rest_" if is_rest else "") + "duration_"
                  + (dur_v["outcome"] if dur_v else "absent"), s)
            continue

        owner = rec.value(Q.GLYPH_OWNER, sub)
        if A.is_relocated_copy(sub, owner):
            # ⚠️⚠️ THE CONTEST IS RESOLVED BY REFUSING THE COPY, NOT BY
            # MOVING IT. See `A.is_relocated_copy`: `glyph_owner`'s domain is
            # the CONTESTED population, so a verdict naming another staff
            # means that staff holds this ink too — and writing this row as
            # well put BOTH copies in the owner's bar, at one pitch, on one
            # stem. That is Sean's *"2 of the same note next to each other
            # connected to the same stem"*, and it is what the legacy
            # `_dedupe_cross_staff_detections` achieves by DELETING the loser
            # rather than relocating it.
            _drop("owned_by_another_staff", s)
            continue
        home = _staff_key(s["page"] or 0, s["system"] or 0, s["staff"] or 0)
        if held_out and home in held_out:
            # ⚠️ THE STAFF IS HELD OUT, so this note has no part to go in.
            # COUNTED, never swallowed -- the shortfall belongs in the record.
            _drop("staff_not_identified", s)
            continue
        run = runs.get(home)
        if run is None:
            # The owner names a staff with no `measure_partition` verdict, so
            # there is no bar to put the note in. Counted, not swallowed.
            _drop("owner_staff_has_no_measures", s)
            continue

        cell_index = s["cell"] or 0
        cell = run.cells.setdefault(
            cell_index, Cell(run.page, run.system, run.staff, cell_index))

        name, x, y, w, h = o["value"]
        written = float(dur.get("written") or dur.get("beats") or 0.0)
        # ⚠️ A MEASURE REST NEEDS NO NOTE VALUE, and demanding one would
        # refuse the bar the convention exists for. `<rest measure="yes"/>`
        # carries NO `<type>` at all -- there is no note value to name -- so a
        # bar length that reduces to nothing (5/4, 7/8) is exportable here
        # while the same number on a NOTE is not.
        if dur.get("measure_rest"):
            cell = run.cells.setdefault(
                cell_index, Cell(run.page, run.system, run.staff, cell_index))
            cell.detections.append({
                "category": "rest", "class": name,
                "bbox": [int(x), int(y), int(w), int(h)],
                "duration_beats": written, "duration_type": "whole", "dots": 0,
                "measure_rest": True, "glyph": sub,
            })
            continue
        fit = _legacy._dotted_duration_for_beats(written)
        if fit is None:
            # ⚠️ NO GUESS. A written value that reduces to no note value is
            # not a note we read; emitting a nearest match would put a wrong
            # rhythm in the file and call it a reading.
            _drop("written_value_fits_no_note", s)
            continue
        dtype, derived_dots = fit
        cell.detections.append({
            "category": "rest" if is_rest else "notehead",
            "class": name,
            "bbox": [int(x), int(y), int(w), int(h)],
            **({} if is_rest else {"pitch": pitch}),
            # ⚠️ THE DOTS ARE ONE FACT, NOT TWO. `_duration_to_lily_xml`
            # takes `max` of the type's prefix and the dot count for exactly
            # this reason: summing them wrote a double-dotted quarter for
            # every single-dotted one, 82 edits on one fixture. The staged
            # `duration` verdict carries both, so the same `max` applies.
            "duration_beats": float(dur.get("beats") or written),
            "duration_type": dtype,
            "dots": max(int(dur.get("dots") or 0), derived_dots),
            # ⚠️ THE BEAM LEVEL IS ALREADY ON THE RECORD and was read by
            # nothing on this path -- `adjudicate_duration` puts it in the
            # verdict's own VALUE, beside the beats it derived FROM it. It is
            # carried here under the name `annotate_beams` expects, so the
            # legacy grouping rule can be called rather than restated. A rest
            # carries 0 and is never beamed.
            "beam_levels": int(dur.get("beam_levels") or 0),
            # ⚠️ THE ALTERATION IS CARRIED, AND IT IS NOT THE DRAWN GLYPH.
            # It has already been folded into `pitch` above, so this entry
            # exists only so the counter can report how many notes the key
            # altered. It is deliberately NOT named `accidental` any more:
            # the old key wrote `<accidental>`, and a name that still says
            # "glyph" is how the next reader re-wires it back.
            "key_alteration": applied,
            # ⚠️ THE RATIO NAMES ITS MEMBERS, AND ONLY THEY ARE SCALED. A
            # tuplet is a fact of a GROUP inside the bar, not of the bar:
            # `adjudicate_tuplet` records `members` (the glyph indices its
            # marker covers) precisely so a consumer need not re-derive the
            # span from the beam box. Scaling every note in the cell would
            # shorten every untupleted note in it by a third.
            "tuplet": _tuplet_for(rec, run, cell_index, s["glyph"]),
            "glyph": sub,
            # ⚠️⚠️ THE PAGE BOX, IN THE *WIDTH* FORM, AND THE TWO FRAMES HERE
            # ARE A RECORDED TRAP. `bbox` above is CANONICAL -- measured
            # inside one cell, rescaled so the staff span is constant -- and
            # is the right frame for everything that stays inside a bar.
            # An arc is cut in two by the barline and rejoined in PAGE pixels,
            # the only frame two cells share, so `_noteheads_under` needs this
            # one. ⚠️ The record spells a page box in CORNERS
            # (`[x0, y0, x1, y1]`, as `_page_box` builds it and `arc_owner`
            # reads it); every legacy DETECTION box is `(x, y, w, h)`. The two
            # are indistinguishable on a fixture whose boxes start at 0, which
            # is how this project has already paid for the confusion once.
            "bbox_page": _corners_to_wh(_page_box_of(o)),
        })
    return dict(dropped)


def _page_box_of(o: Dict[str, Any]) -> Optional[List[float]]:
    """One observation's page rectangle, CORNERS, or None.

    ⚠️ None is a real answer and must stay one: `gather` DECLINES a page box
    for a cell it cannot place (`frame_note`) rather than defaulting to the
    cell frame, and a consumer that substituted a canonical box here would be
    comparing lengths that were never in the same units -- the fault that made
    `Q.ONSET_COLUMN` report 1,062 columns of nothing.
    """
    box = (o.get("detail") or {}).get("bbox_page_px")
    if not box or len(box) != 4:
        return None
    return [float(v) for v in box]


def _corners_to_wh(box: Optional[Sequence[float]]) -> Optional[List[float]]:
    """`[x0, y0, x1, y1]` -> `[x, y, w, h]`. The one place the two spellings
    of a rectangle meet, so no second reader can get the conversion wrong."""
    if box is None:
        return None
    x0, y0, x1, y1 = (float(v) for v in box)
    return [x0, y0, x1 - x0, y1 - y0]


def _place_arcs(rec: Record, runs: Dict[str, StaffRun]) -> Dict[str, int]:
    """Every decided arc, in the cell its OWNER puts it in.

    ⚠️ THE OWNER, NOT THE SUBJECT -- the same rule `_place_notes` states and
    for a sharper reason. A notehead detected on the wrong staff is at least
    detected twice, so a duplicate rule can see the contest; an arc need not
    be. Where two staves sit far apart the upper cell reaches ink the lower
    one does not, so on `brahms-sym1-mvt1` the Timpani exported 4 slurs and 1
    tie against a truth of ZERO and every one of them was Violin 1's, drawn
    over ITS ledger notes in the gap between the two staves.
    `adjudicate_arc_owner` has already settled this; the exporter honours it.

    ⚠️ AND IT WAS DECIDING FOR A DAY WITH NO ROUTE TO A FILE. `arc_kind` and
    `arc_owner` decide 199 arcs on one page, `arc_owner` moves 12 of them, and
    `grep '<slur' staged/export.py` returned ZERO -- the value existed and
    nothing read it, inside the architecture built to stop exactly that.
    """
    dropped: Dict[str, int] = collections.Counter()
    for o in rec.obs_of(Q.ARC_BOX):
        sub = o["subject"]
        s = _parse_subject(sub)
        if s["glyph"] is None:
            continue
        kind_v = rec.verdict(Q.ARC_KIND, sub)
        if not kind_v or kind_v["outcome"] != "decided":
            # ⚠️ COUNTED BY ITS REASON, not lumped together. "I could not read
            # this arc" and "there was no page box to read it in" send the
            # next reader to different places.
            dropped["kind_" + (kind_v["reason"] if kind_v else "absent")] += 1
            continue
        kind = str(kind_v["value"])
        if kind not in ("slur", "tie"):
            dropped["kind_not_an_arc"] += 1
            continue

        page_box = _corners_to_wh(_page_box_of(o))
        if page_box is None:
            # An arc with no page rectangle cannot be merged across a barline
            # and cannot be compared with a notehead: both happen in page
            # pixels. Dropped rather than placed in the wrong frame.
            dropped["arc_no_page_frame"] += 1
            continue

        owner = rec.value(Q.ARC_OWNER, sub)
        home = owner if isinstance(owner, str) else _staff_key(
            s["page"] or 0, s["system"] or 0, s["staff"] or 0)
        run = runs.get(home)
        if run is None:
            dropped["arc_owner_staff_has_no_measures"] += 1
            continue
        cell_index = s["cell"] or 0
        cell = run.cells.setdefault(
            cell_index, Cell(run.page, run.system, run.staff, cell_index))
        cell.arcs.append((kind, page_box))
    return dict(dropped)


def _voice_of_notehead(rec: Record, part: Sequence[StaffRun]
                       ) -> Dict[int, int]:
    """`id(detection) -> voice number`, for every note of this part.

    ⚠️⚠️ THE STAGED EXPORTER PASSED `_paired_spans` AN EMPTY DICT UNTIL
    2026-09-10, so its one-voice rule was inert -- and an inert rule is
    indistinguishable from one that ran and found nothing. MusicXML pairs
    `<slur>` WITHIN a `<voice>`, so an arc whose ends land in different
    streams is unpaired at BOTH and makes the file invalid rather than merely
    wrong; the legacy rule prefers the longest run the curve covers inside one
    voice over dropping it, and that preference cannot operate without this
    map.

    ⚠️ KEYED BY `id()`, which is what `_paired_spans` looks up, and safe only
    because `_flatten_part` passes the exporter's OWN detection dicts by
    reference. Keying by glyph would need a second lookup inside the legacy
    function.

    ⚠️ A NOTE THE VERDICT DOES NOT MENTION IS VOICE 0, the same default
    `_paired_spans` already applies to an unmapped note -- so a bar whose
    voices were never decided behaves exactly as it did before.
    """
    out: Dict[int, int] = {}
    for run in part:
        for cell_index, cell in run.cells.items():
            v = rec.verdict(Q.VOICES, R_cell_key(run, cell_index))
            if not v or v["outcome"] != "decided":
                continue
            value = v["value"] or {}
            if int(value.get("n_voices") or 1) < 2:
                continue
            # ⚠️ A REST IS IN EVERY STREAM and is deliberately NOT given a
            # voice here: this map exists to refuse an arc crossing streams,
            # and a rest binds no arc. Assigning it one would make it look
            # like a member of whichever stream was listed last.
            in_both = set(value.get("rests_in_every_voice") or ())
            for number, glyphs in enumerate(value.get("voices") or (), start=1):
                wanted = set(glyphs) - in_both
                for det in cell.detections:
                    idx = _glyph_index(det.get("glyph") or "")
                    if idx is not None and idx in wanted:
                        out[id(det)] = number
    return out


def _stem_boxes_by_cell(rec: Record) -> Dict[str, List[Tuple[float, ...]]]:
    """`cell subject -> [(x, y, w, h)]`, in the CELL's own canonical frame.

    ⚠️ `Q.STEM` is filed on the CELL, in canonical coordinates, and carries NO
    page box -- `gather_cv_lines` reads an ERASED cell image and never
    converts. That is the *gathered in a frame that cannot answer* shape this
    file already records for `gather_glyph_families`, and it is why
    `_stem_probes` converts through the HEAD rather than asking for a page box
    that is not there.
    """
    out: Dict[str, List[Tuple[float, ...]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.STEM):
        v = o["value"]
        if isinstance(v, (list, tuple)) and len(v) >= 4:
            out[o["subject"]].append(tuple(float(x) for x in v[:4]))
    return dict(out)


def _beam_boxes_by_cell(rec: Record) -> Dict[str, List[Tuple[float, ...]]]:
    """`cell subject -> [(x, y, w, h)]`, in the CELL's own canonical frame.

    ⚠️ `Q.BEAM_STROKE` is filed on the CELL by `gather_cv_lines`, which reads
    an ERASED cell image and never converts -- exactly as `Q.STEM` is, and
    for the same reason. The conversion is `_beam_detections_page`'s job.
    """
    out: Dict[str, List[Tuple[float, ...]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.BEAM_STROKE):
        v = o["value"]
        if isinstance(v, (list, tuple)) and len(v) >= 4:
            out[o["subject"]].append(tuple(float(x) for x in v[:4]))
    return dict(out)


def _beam_detections_page(cell: "Cell", boxes: Sequence[Tuple[float, ...]]
                          ) -> List[Dict[str, Any]]:
    """Beam strokes as the `structural`/`beam` detections `annotate_beams` reads.

    ⚠️⚠️ THE FRAME IS THE WHOLE RISK HERE, AND IT IS THE ONE THIS REPO KEEPS
    PAYING FOR. `annotate_beams` compares a beam box against a notehead's
    CENTRE, and it reads both out of `bbox_page`. The strokes arrive in the
    cell's CANONICAL frame -- measured inside one cell and rescaled so the
    staff span is constant -- so handing them over unconverted would compare
    two different rulers and group notes by coincidence. That is
    `Q.ONSET_COLUMN`'s recorded fault, and a wrong grouping does not raise:
    it writes a beam over the wrong notes.

    ⚠️ THE CONVERSION USES THE HEAD AS ITS OWN RULER, the method `_stem_probes`
    already established and measured (a per-cell affine fit gives the identical
    answer at residual 0.00 px). A notehead carries BOTH boxes -- canonical
    (`bbox`) and page (`bbox_page`) -- so one head fixes the scale and the
    origin for every stroke in its cell.

    ⚠️ IT REFUSES RATHER THAN GUESSES. A cell with no head carrying both boxes
    has no ruler, so it yields NOTHING and its notes stay flagged -- which is
    what they were before this rung existed. Inventing a scale from the cell's
    nominal width would be a guess about geometry, and a wiring pass may
    connect a decision and may not let one guess.
    """
    ruler = None
    for det in cell.detections:
        if det.get("category") != "notehead":
            continue
        page, canon = det.get("bbox_page"), det.get("bbox")
        if (page and canon and len(page) == 4 and len(canon) == 4
                and float(canon[2]) > 0):
            ruler = (tuple(float(v) for v in canon),
                     tuple(float(v) for v in page))
            break
    if ruler is None:
        return []
    canon, page = ruler
    scale = page[2] / canon[2]
    out: List[Dict[str, Any]] = []
    for (bx, by, bw, bh) in boxes:
        out.append({
            "category": "structural", "class": "beam",
            "bbox_page": [page[0] + (bx - canon[0]) * scale,
                          page[1] + (by - canon[1]) * scale,
                          bw * scale, bh * scale],
        })
    return out


def _stem_probes(rec: Record, part: Sequence[StaffRun],
                 stems: Dict[str, List[Tuple[float, ...]]]
                 ) -> Dict[int, List[float]]:
    """`id(detection) -> [the page x of this note's STEM]`.

    ⚠️⚠️ AN ARC OVER STEMMED NOTES IS DRAWN FROM STEM TOP TO STEM TOP, AND A
    STEM STANDS AT THE SIDE OF ITS NOTEHEAD -- so the curve's ink stops about
    half a notehead width INSIDE both outer head CENTRES, which is the only
    position `_noteheads_under` measures. This project has already paid for
    exactly this mechanism once, one family over: `_beam_levels` tested a
    head's centre against a beam stroke that *"runs from the FIRST stem it
    joins to the LAST"*, the overshoot clustered at **0.35-0.47 notehead
    widths**, and the repair was not a tolerance -- it was to join the note to
    the beam BY ITS STEM. Measured here on Litolff Beethoven 5 p1-4 the same
    quantity has median **0.52** notehead widths.

    ⚠️ AND THE OBVIOUS ALTERNATIVE -- WIDENING THE PAD -- IS MEASURED AND
    REFUSED. `_SLUR_ARC_PAD_NOTEHEADS` sits in an interval the Brahms engraved
    fixture left EMPTY (54 of 75 within 0.19, the next at 0.32). On this
    document the same distribution is a smooth slope with no gap anywhere
    (`probe/pad_gap.py`), so a pad chosen here would be fitted to a wish
    rather than read off the ink. The stem is not a wider tolerance; it is the
    position the arc is actually drawn to.

    ⚠️ ADDITIVE, NEVER SUBTRACTIVE, in the shape `_stem_joined` and the ledger
    ladder already have: a probe can only make a head REACHABLE, so a page
    whose stems the CV never read behaves exactly as before, and the span's
    own endpoints stay the notehead centres.

    ⚠️ THE FRAME CONVERSION USES THE HEAD AS ITS OWN RULER and needs no fit.
    The head carries BOTH boxes -- canonical (`Q.GLYPH_BOX`) and page
    (`bbox_page`, which `_place_notes` already put on the detection) -- so the
    stem's canonical offset from the head scales by that head's own
    width ratio. A per-cell affine fit over the glyph rows gives the identical
    answer (residual 0.00 px, `probe/stem_reach.py`); this is the same number
    without a second reader that could drift.

    ⚠️ THE ATTACHMENT RULE IS `_stem_joined`'S, IMPORTED. A head takes the
    stem whose box overlaps its own -- measured, not chosen: 819 heads take
    exactly one stem and the nearest miss is 94 px.
    """
    from .adjudicators.rhythm import _boxes_overlap
    probes: Dict[int, List[float]] = {}
    for run in part:
        for cell_index, cell in run.cells.items():
            key = f"cell/{run.page}/{run.system}/{run.staff}/{cell_index}"
            pool = stems.get(key)
            if not pool:
                continue
            for det in cell.detections:
                if det.get("category") != "notehead":
                    continue
                page = det.get("bbox_page")
                canon = det.get("bbox")
                if not page or not canon or len(page) != 4 or len(canon) != 4:
                    continue
                hw = float(canon[2])
                if hw <= 0:
                    continue
                head_box = tuple(float(v) for v in canon)
                mine = [s for s in pool if _boxes_overlap(s, head_box)]
                if not mine:
                    continue
                scale = float(page[2]) / hw
                head_cx_canon = float(canon[0]) + hw / 2.0
                head_cx_page = float(page[0]) + float(page[2]) / 2.0
                probes[id(det)] = [
                    head_cx_page + (s[0] + s[2] / 2.0 - head_cx_canon) * scale
                    for s in mine]
    return probes


def _pair_arcs(rec: Record, parts: Sequence[Sequence[StaffRun]],
               counters: Dict[str, int]) -> Dict[str, int]:
    """Join each part's arcs across its barlines and mark the notes they bind.

    ⚠️⚠️ THIS IS A PART PASS AND NOT A MEASURE ONE, AND THE NUMBER SAYS WHY.
    Cells are cut per measure, so an arc crossing a barline is DETECTED AS TWO
    -- **32 of 199 arcs on one page (16.1%) begin at their cell's left edge**,
    the cross-barline signature. Emitting each half as its own `<slur>` writes
    two where the music has one, which is what kept an implemented and tested
    `annotate_slurs` out of the LEGACY exporter until 2026-09-01.

    ⚠️ AND OMR-NED WOULD NOT HAVE CAUGHT IT. The metric is symmetric, so
    emitting MORE symbols is rewarded: the legacy slur work's first cut
    LOWERED pooled OMR-NED while RAISING the edit count. That is why this
    lands with the merge rather than after it.

    ⚠️ `_merge_arcs_across_barlines`, `_noteheads_under` and `_number_spans`
    are IMPORTED AND CALLED, not ported. Their three measured constants
    (`_SLUR_BOUNDARY_SPACES` 0.5, `_SLUR_CONTINUATION_DY_SPACES` 2.0,
    `_SLUR_ARC_PAD_NOTEHEADS` 0.25) each sit in a gap the measurement found,
    and each is a PLATEAU rather than a peak. Restating them here would give
    this project two copies of a number it paid to measure once -- the drift
    `LETTER_METERS` and the arc-attribution constants are both imported to
    prevent.
    """
    dropped: Dict[str, int] = collections.Counter()
    stems = _stem_boxes_by_cell(rec)
    for part in parts:
        measures, per_measure_arcs, kinds, spacings, tops, breaks = \
            _flatten_part(part)
        if not measures or not any(per_measure_arcs):
            continue
        voice_of = _voice_of_notehead(rec, part)
        # ⚠️ An arc is drawn to a note's STEM, not to its head. See
        # `_stem_probes`: this is the `_beam_levels` fault one family over,
        # and the pad that would otherwise have to grow sits in an interval
        # this document leaves FULL.
        x_probes = _stem_probes(rec, part, stems)
        counters["arc_notes_reachable_at_a_stem"] += len(x_probes)
        # ⚠️⚠️ A BAR WHOSE GEOMETRY IS MISSING SWALLOWS ITS ARCS SILENTLY, and
        # counting them is the whole difference between a gap and a hole.
        # `_merge_arcs_across_barlines` opens each bar with "no box, or no
        # spacing, then break the chain and move on" -- which is right, since
        # there is no unit to measure a boundary in -- but its `continue`
        # skips that bar's arcs entirely. They are not merged, not emitted,
        # and without this line not counted either: the exact shape of
        # `measure_dynamics` discarding a letter run, or the eventless-measure
        # branch computing directions and never using them.
        for i, cell_arcs in enumerate(per_measure_arcs):
            if cell_arcs and not (measures[i]["bbox_page_px"] and spacings[i]):
                dropped["arc_bar_has_no_geometry"] += len(cell_arcs)
        # ⚠️⚠️ THE ARCS ARE PARTITIONED BY KIND AND EACH POOL IS PAIRED ON ITS
        # OWN, and the first cut did NOT do this -- it paired everything at
        # once and then asked each span's first notehead which kind it was.
        # That is wrong wherever two spans share a note: a tie and a slur
        # starting on the same head are one entry in a head-keyed map, so the
        # later one silently renames the earlier. Overlapping spans are not
        # exotic -- `_number_spans` exists precisely because they happen.
        #
        # ⚠️ THE PARTITION IS EXACT, WHICH IS WHY IT IS SAFE. The merge is
        # GEOMETRIC and knows nothing about kind, so a group's arcs all carry
        # one kind into one pool, and the merge inside `_paired_spans`
        # re-derives that group exactly. Nothing is split by moving it.
        by_kind, merged = _arcs_by_kind(measures, per_measure_arcs, kinds,
                                        spacings, tops, breaks)
        n_spans = 0
        for kind, pools in by_kind.items():
            spans = _legacy._paired_spans(measures, pools, spacings, tops,
                                          breaks, voice_of,
                                          x_probes=x_probes)
            n_spans += len(spans)
            if kind == "tie":
                # ⚠️⚠️ THE CHAIN IS COUNTED HERE BECAUSE THIS IS THE ONLY
                # PLACE THAT KNOWS IT. `tied_to_next` / `tied_from_prev` are
                # the last two entries in `gather_coverage.NO_VOCABULARY`: no
                # `Q` names the chain, because a chain is a fact about a PART
                # -- it crosses barlines and system breaks -- and the part is
                # built HERE, after `Q.PART_PARTITION` is read. So the record
                # cannot say how many ties this document has; the exporter
                # can, and until this counter it did not say either.
                #
                # ⚠️ A CHAIN IS NOT A LINK AND THE NUMBERS DIFFER: on
                # Breitkopf Brahms 1 p0-3 632 links make 275 chains, 82 of
                # them longer than two notes. A report quoting links as
                # "ties" over-counts every chain of three or more.
                links: List[Tuple[int, int]] = []
                for (sm, _sx), (tm, _tx), first, last in spans:
                    counters["tie_links_marked"] += 1
                    if sm != tm:
                        counters["tie_links_crossing_a_barline"] += 1
                    if any(b in range(sm + 1, tm + 1) for b in breaks):
                        counters["tie_links_crossing_a_system_break"] += 1
                    links.append((id(first), id(last)))
                for n in _chain_sizes(links).values():
                    counters["tie_chains_marked"] += 1
                    if n > 2:
                        counters["tie_chains_over_two_notes"] += 1
                for (_a, _b, first, last) in spans:
                    # ⚠️ A TIE IS NOT NUMBERED. MusicXML `<tie>`/`<tied>` join
                    # the two notes they name and carry no `number=`, so there
                    # is nothing to allocate and no ceiling to drop past -- the
                    # one place a tie and a slur are genuinely different
                    # spanners rather than the same one under two names.
                    first["tied_to_next"] = True
                    last["tied_from_prev"] = True
                    counters["tie_spans_marked"] += 1
                continue
            # ⚠️ THE THIRD PLACE AN ARC CAN VANISH. `_number_spans` DROPS a
            # span past the level ceiling rather than renumbering it -- six
            # open at once is already pathological and a seventh would have to
            # reuse a live number, which is worse than silence. Silence in the
            # FILE; not silence in the report.
            numbered = _legacy._number_spans(spans, _legacy._MAX_SLUR_NUMBER)
            if len(numbered) < len(spans):
                dropped["arc_past_the_slur_number_ceiling"] += (
                    len(spans) - len(numbered))
            for number, (_a, _b, first, last) in numbered:
                first.setdefault("slur_states", []).append((number, "start"))
                last.setdefault("slur_states", []).append((number, "stop"))
                counters["slur_spans_marked"] += 1
        # ⚠️ A merged arc that binds fewer than two noteheads of one voice is
        # REFUSED by `_paired_spans` -- one end leaves an unpaired
        # `<slur type="start">` and an INVALID file. On a scan the usual cause
        # is that the notes under the arc were never detected, which is a
        # READING shortfall and belongs in the record, not in the silence.
        if merged > n_spans:
            dropped["arc_binds_fewer_than_two_notes"] += merged - n_spans
    return dict(dropped)


def _part_cells_in_order(part: Sequence[StaffRun]
                         ) -> List[Tuple[StaffRun, int]]:
    """`(run, cell_index)` for each bar of a part, in `_flatten_part`'s order.

    ⚠️ IT EXISTS TO GIVE A BAR A PART-WIDE ORDINAL, which a cell index is
    NOT: a cell index RESTARTS AT 0 on every system, so system 0's third bar
    and system 1's third bar share the number 3. That is not a hypothetical --
    it is the defect that made the duration arm's bar-level figures wrong when
    first published (`(page, cell)` merged two bars into one pseudo-bar), and
    a wedge numbered against it would let a hairpin in system 1 close a
    hairpin still open in system 0.

    ⚠️ THE ORDER MUST MATCH `_flatten_part`'S AND IS ASSERTED TO, rather than
    trusted: `test_staged_wedges` checks that this list is exactly as long as
    that function's measure sequence, so the two cannot drift apart silently.
    """
    out: List[Tuple[StaffRun, int]] = []
    for run in part:
        for i in range(run.n_measures):
            out.append((run, i))
    return out


def _place_wedges(rec: Record, parts: Sequence[Sequence[StaffRun]],
                  counters: Dict[str, int]) -> Dict[str, int]:
    """Every decided hairpin, onto the two notes its ANCHOR names.

    ⚠️⚠️ IT LANDS WITH THE ADJUDICATOR, NEVER AFTER IT, which is now this
    file's own repeated lesson rather than a preference: `adjudicate_dynamic`
    and `arc_kind` each spent a day deciding into no file, and the day
    `articulation_owner`'s docstring called its repair "write the
    adjudicator" the tree said THREE — adjudicator, emission, counter.

    ⚠️ NO GEOMETRY HERE, UNLIKE `_pair_arcs`, AND THE READER IS WHY. An arc is
    cut in two by the per-measure crop, so the exporter has to merge it across
    barlines before it can be paired; `hairpin_detection` reads the whole page
    one staff-band at a time, so a CV hairpin is never cut and
    `adjudicate_wedge_anchor` has already named both ends. What is left here
    is serialisation: give each hairpin a `number=` and mark its two notes.

    ⚠️ A PART PASS, NOT A MEASURE ONE, because `number=` is allocated against
    what else is OPEN — two hairpins overlapping in one part need two levels,
    and a per-measure pass cannot see the overlap.

    ⚠️ `_number_spans` IS IMPORTED AND CALLED, with `_MAX_WEDGE_NUMBER` rather
    than the slur ceiling: a `<slur number="1">` and a `<wedge number="1">`
    name different things, so the two families are numbered independently and
    that function's docstring says so.

    ⚠️ NOTHING IS COUNTED HERE. The count happens where the ELEMENT is
    written, in `_measure_events_xml` — the `FAMILIES` rule, and the one the
    arc export learned by reporting 55 slurs into a file holding 23. A mark
    set on a note that `voicing` then folds into a chord is set and not
    necessarily written.

    ⚠️⚠️ THE HEAD INDEX IS BUILT OVER EVERY PART AT ONCE, AND THE FIRST CUT
    BUILT IT PER PART AND LOST TEN HAIRPINS SILENTLY. Inside a per-part loop,
    "this anchor is not in `heads`" has two meanings — *it belongs to another
    part* and *`_place_notes` never wrote it* — and a hairpin whose BOTH ends
    were unwritten looked like the first to EVERY part, so no part counted it
    and none reported it. Measured on Breitkopf Brahms 1 p0-3: 46 decided, 20
    written, 16 counted as dropped and **10 accounted for nowhere**, sitting in
    `wedge_balance`'s `absorbed_by_a_shared_event` residue while its `<=`
    stayed True. Indexing globally collapses the two meanings into one, so a
    hairpin is accounted for exactly once — *a shortfall that is not counted is
    indistinguishable from ink that was never read*, and this file says so in
    three other places.
    """
    dropped: Dict[str, int] = collections.Counter()
    heads: Dict[str, Tuple[Dict[str, Any], int, int]] = {}
    for pi, part in enumerate(parts):
        for n, (run, i) in enumerate(_part_cells_in_order(part)):
            cell = run.cells.get(i)
            if cell is None:
                continue
            for det in cell.detections:
                if det.get("category") == "notehead" and det.get("glyph"):
                    heads[str(det["glyph"])] = (det, n, pi)

    by_part: Dict[int, List[Tuple[Any, ...]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.WEDGE_BOX):
        sub = o["subject"]
        v = rec.verdict(Q.WEDGE_ANCHOR, sub)
        if not v or v["outcome"] != "decided":
            continue
        value = v["value"] or []
        if len(value) != 2:
            dropped["wedge_verdict_names_no_pair"] += 1
            continue
        first = heads.get(str(value[0]))
        last = heads.get(str(value[1]))
        if first is None and last is None:
            # ⚠️ THE TEN. Both anchors are notes `_place_notes` never wrote —
            # no pitch, or a duration `adjudicate_duration` narrowed and the
            # exporter refuses to argmax. The hairpin was READ and DECIDED and
            # has nothing left to hang on; reported under its own name rather
            # than the one-end case, because the repairs differ.
            dropped["wedge_neither_anchor_written"] += 1
            continue
        if first is None or last is None:
            dropped["wedge_anchor_note_not_written"] += 1
            continue
        if first[2] != last[2]:
            # ⚠️ A hairpin cannot open in one `<part>` and close in another:
            # MusicXML pairs it within one part's stream. Counted, not bent.
            dropped["wedge_ends_in_two_parts"] += 1
            continue
        detail = v.get("detail") or {}
        kind = detail.get("kind")
        if kind not in ("crescendo", "diminuendo"):
            dropped["wedge_verdict_names_no_kind"] += 1
            continue
        by_part[first[2]].append((
            (first[1], float(detail.get("start_x_page") or 0.0)),
            (last[1], float(detail.get("stop_x_page") or 0.0)),
            first[0], last[0], str(kind)))

    for pi in sorted(by_part):
        spans = by_part[pi]

        # ⚠️ NO IDEMPOTENCE GUARD HERE, UNLIKE `annotate_wedges_in_staff`, and
        # the difference is whose dicts these are. The legacy pass mutates the
        # PIPELINE'S OWN result, so it clears `wedge_states` first or a second
        # run stacks marks; `build()` constructs fresh `Cell` objects and
        # fresh detection dicts on every call, so there is nothing to clear.
        # A clearing loop was written here, a mutation arm DELETED it and the
        # suite stayed green — the rule could not fire, so the code went
        # rather than acquiring a test that could not reach it. Idempotence is
        # still asserted, at the level where it is real: two exports of one
        # record are byte-identical.
        numbered = _legacy._number_spans(spans, _legacy._MAX_WEDGE_NUMBER)
        if len(numbered) < len(spans):
            # ⚠️ The third place a spanner can vanish, and it is SILENCE IN
            # THE FILE, not silence in the report: `_number_spans` DROPS a
            # span past the ceiling rather than reusing a live number.
            dropped["wedge_past_the_number_ceiling"] += len(spans) - len(numbered)
        for number, (_a, _b, first_det, last_det, kind) in numbered:
            # ⚠️ THE OPENING MARK CARRIES THE KIND AND THE CLOSING ONE THE
            # WORD "stop" — MusicXML's own spelling, and what
            # `voicing._chord_span_states` tests for when it decides which
            # marks a chord carries ("an opening mark is anything that is not
            # a stop").
            first_det.setdefault("wedge_states", []).append((number, kind))
            last_det.setdefault("wedge_states", []).append((number, "stop"))
    return dict(dropped)
def _chain_sizes(links: Sequence[Tuple[int, int]]) -> Dict[int, int]:
    """`{chain root: how many NOTES it joins}` — union-find over shared ends.

    ⚠️ NOT A `start -> stop` DICT, AND THE DIFFERENCE IS MEASURABLE. A
    notehead can begin two links — a chord member tied onward in one voice
    while the head beside it starts another — so keying on the start silently
    drops the second and reports every chain as a pair. The first cut of the
    reach probe did exactly that and read `{2: 50}` on a page whose chains run
    to four notes.

    ⚠️ A chain of N notes is N-1 links, so the value is the member COUNT and
    never the link count; the two differ by one per chain and quoting the
    wrong one is how "ties" and "tie links" drift apart.
    """
    parent: Dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return dict(collections.Counter(find(x) for x in parent))


def _flatten_part(part: Sequence[StaffRun]):
    """One measure sequence for a whole part, with each measure's geometry.

    Returns `(measures, arcs, kinds, spacings, tops, breaks)` -- the shape
    `_legacy._paired_spans` takes, plus `kinds`, which is this path's own.

    ⚠️ A BAR WITH NO PAGE RECTANGLE IS PASSED THROUGH AS `None`, NOT SKIPPED,
    AND THE BREAKING IS `_merge_arcs_across_barlines`'S — said here because
    that is where a reader will look for it and it is not in this function.
    Keeping the bar in the sequence is what makes the merge break the chain
    there (it clears `pending` on a bar it cannot measure); DROPPING the bar
    would close the gap and let an arc pair with one two measures away that
    happens to line up. `annotate_slurs_in_slot` reaches the same outcome from
    the other side, splitting a slot into contiguous runs where a staff has no
    line spacing.

    ⚠️ The geometry travels BESIDE the measures and not on them. These shim
    dicts hold the exporter's OWN detection dicts by reference -- that is how
    a mark set on a span's first note reaches `group_chords_in_measure` -- so
    anything stashed on them would be stashed on the pipeline's output.
    """
    measures: List[Dict[str, Any]] = []
    arcs: List[List[List[float]]] = []
    kinds: Dict[int, str] = {}
    spacings: List[float] = []
    tops: List[Optional[float]] = []
    breaks = set()
    for run in part:
        # ⚠️ `if measures`, NOT `if run.n_measures` -- the FIRST staff's
        # opening bar is not a system BREAK, it is the beginning. The legacy
        # `_flatten_run` spells it the same way and the two must agree: a
        # spurious break at index 0 sends bar 0 down `_resumes_after_system_
        # break` instead of the cell-edge test, which is a different reading
        # of the same ink.
        if measures:
            breaks.add(len(measures))
        for i in range(run.n_measures):
            cell = run.cells.get(i)
            dets = cell.detections if cell else []
            measures.append({"bbox_page_px": run.cell_boxes.get(i),
                             "detections": dets})
            cell_arcs = []
            for kind, box in (cell.arcs if cell else []):
                cell_arcs.append(box)
                kinds[id(box)] = kind
            arcs.append(cell_arcs)
            spacings.append(run.spacing or 0.0)
            tops.append(run.top_line)
    return measures, arcs, kinds, spacings, tops, frozenset(breaks)


def _arcs_by_kind(measures, arcs, kinds, spacings, tops, breaks
                  ) -> Tuple[Dict[str, List[List[List[float]]]], int]:
    """`({"slur" | "tie": per-measure arc lists}, n merged arcs)`.

    ⚠️ THE KIND BELONGS TO AN ARC AND THE MERGE JOINS TWO OF THEM, so the
    split has to happen after merging: before it, the two halves of one
    cross-barline curve are two arcs, and half a curve is not a thing that has
    a kind. The merge is pure and cheap, so it runs here to learn which arcs
    became one group and again inside `_paired_spans` for the spans -- cheaper
    than a second copy of the merge that could drift from the first.

    ⚠️ A MERGED ARC CAN HOLD BOTH KINDS -- one half read `tie`, the other
    `slur` -- and `tie` wins, deliberately. The halves are ONE printed curve,
    so a disagreement is a reading error whichever way it is taken; the tie
    keeps the pair joined at one pitch, where the slur would emit a span the
    grammar could then contradict. ⚠️ It is NOT re-litigated here:
    `OMR_ARC_RECLASS` measured the position grammar on both families and was
    REFUSED (scan +130 edits), and `arc_kind` RECORDS the grammar's opinion
    rather than acting on it. This picks between two readings we already have;
    it does not form a third.
    """
    out: Dict[str, List[List[List[float]]]] = {}
    # ⚠️ THE GROUP COUNT IS RETURNED, NOT DERIVED FROM `out`. `out[kind]` is a
    # list per MEASURE, so `len()` on it is the number of bars and not the
    # number of merged arcs -- which is what the first version summed, making
    # the accounting control read 2 of 3 on a two-bar fixture. The control
    # caught it; nothing in the exported file would have.
    n_groups = 0
    for segments in _legacy._merge_arcs_across_barlines(
            measures, arcs, spacings, tops, breaks):
        n_groups += 1
        seen = {kinds.get(id(box)) for _m, box in segments}
        kind = "tie" if "tie" in seen else "slur"
        pool = out.setdefault(kind, [[] for _ in measures])
        for m_idx, box in segments:
            pool[m_idx].append(box)
    return out, n_groups


def _place_articulations(rec: Record, runs: Dict[str, StaffRun]) -> Dict[str, int]:
    """Every decided articulation, onto the notehead its OWNER names.

    ⚠️⚠️ THIS FUNCTION LANDS WITH THE ADJUDICATOR, NOT AFTER IT, AND THAT IS
    THE WHOLE POINT. `adjudicate_dynamic` stopped being a stub and nothing read
    it for a day; `arc_kind` decided 199 arcs a page with `grep '<slur'`
    returning zero. Both were found by forensics inside the architecture built
    to stop exactly that. A stub whose adjudicator lands alone is not progress,
    it is a fresh `decided_and_unwritten` row.

    ⚠️ THE JOIN IS THE NOTEHEAD'S SUBJECT KEY, which `_place_notes` already
    stamps on every detection as `glyph`. Joining on canonical coordinates
    instead would re-derive, approximately, a fact the record states exactly.

    ⚠️ A MARK WHOSE OWNING NOTEHEAD NEVER REACHED A CELL IS COUNTED, not
    swallowed -- a note can be decided and still be dropped by `_place_notes`
    (no pitch, a narrowed duration), and the mark then has nothing to hang on.
    That is a shortfall, and a shortfall that is not counted is
    indistinguishable from ink that was never read.
    """
    dropped: Dict[str, int] = collections.Counter()
    heads: Dict[str, Dict[str, Any]] = {}
    for run in runs.values():
        for cell in run.cells.values():
            for det in cell.detections:
                if det.get("category") == "notehead" and det.get("glyph"):
                    heads[str(det["glyph"])] = det
    for o in rec.obs_of(Q.ARTICULATION_MARK):
        sub = o["subject"]
        v = rec.verdict(Q.ARTICULATION_OWNER, sub)
        if not v or v["outcome"] != "decided":
            dropped["artic_" + (v["reason"] if v else "absent")] += 1
            continue
        head = heads.get(str(v["value"]))
        if head is None:
            dropped["artic_owning_notehead_not_written"] += 1
            continue
        name = (v.get("detail") or {}).get("articulation")
        if not name:
            dropped["artic_verdict_names_no_kind"] += 1
            continue
        head.setdefault("articulations", []).append(str(name))
    return dict(dropped)


def _place_fermatas(rec: Record, runs: Dict[str, StaffRun]) -> Dict[str, int]:
    """Every decided fermata, onto the notehead or rest its OWNER names.

    ⚠️⚠️ IT LANDS WITH THE ADJUDICATOR, NEVER AFTER IT. `articulation_owner`
    established the cost of the other order in this file's own history: the
    stub's docstring called the repair "write the adjudicator" and the tree
    said THREE -- adjudicator, emission, and the `FAMILIES` counter -- so an
    adjudicator alone would have produced a fresh `decided_and_unwritten` row,
    the bucket the arc session had just emptied. `adjudicate_dynamic` and
    `arc_kind` both spent a day deciding into no file.

    ⚠️ THE JOIN IS THE SUBJECT KEY, which `_place_notes` stamps on every
    detection -- rests included -- as `glyph`. Joining on coordinates would
    re-derive, approximately, a fact the record states exactly.

    ⚠️ A MARK IS SET ON THE CARRIER, NOT COUNTED HERE. The count happens where
    the ELEMENT is written, which is the rule `FAMILIES` states and the arc
    export learned by reporting 55 slurs into a file holding 23: a fermata set
    on the third member of a chord is HOISTED to that chord's first note, so
    marks set and elements written are genuinely different numbers.
    """
    dropped: Dict[str, int] = collections.Counter()
    carriers: Dict[str, Dict[str, Any]] = {}
    for run in runs.values():
        for cell in run.cells.values():
            for det in cell.detections:
                if det.get("glyph"):
                    carriers[str(det["glyph"])] = det
    for o in rec.obs_of(Q.FERMATA_MARK):
        sub = o["subject"]
        v = rec.verdict(Q.FERMATA_OWNER, sub)
        if not v or v["outcome"] != "decided":
            dropped["fermata_" + (v["reason"] if v else "absent")] += 1
            continue
        carrier = carriers.get(str(v["value"]))
        if carrier is None:
            # The owner names a glyph `_place_notes` never wrote — no pitch, a
            # narrowed duration — so the pause has nothing to hang on. A
            # shortfall that is not counted is indistinguishable from ink that
            # was never read.
            dropped["fermata_owning_glyph_not_written"] += 1
            continue
        carrier["fermata"] = True
    return dict(dropped)


def _place_ornaments(rec: Record, runs: Dict[str, StaffRun]) -> Dict[str, int]:
    """Every decided ornament, onto the notehead its OWNER names.

    ⚠️ PER HEAD, LIKE AN ARTICULATION AND UNLIKE A FERMATA -- and the split is
    the engraving's. One pause hangs over a whole chord, so a fermata is
    HOISTED to the chord's first `<note>`; a trill is played on a NOTE, and a
    chord can carry one on any subset of its members. `_mxl_note` takes
    `ornaments=` per note for exactly that reason.

    ⚠️ THE SHAPE IS `_place_articulations`'s and the shortfalls are counted the
    same way: a mark whose owning notehead never reached a cell is COUNTED, not
    swallowed, because a shortfall that is not counted is indistinguishable
    from ink that was never read.
    """
    dropped: Dict[str, int] = collections.Counter()
    heads: Dict[str, Dict[str, Any]] = {}
    for run in runs.values():
        for cell in run.cells.values():
            for det in cell.detections:
                if det.get("category") == "notehead" and det.get("glyph"):
                    heads[str(det["glyph"])] = det
    for o in rec.obs_of(Q.ORNAMENT_MARK):
        sub = o["subject"]
        v = rec.verdict(Q.ORNAMENT_OWNER, sub)
        if not v or v["outcome"] != "decided":
            dropped["ornament_" + (v["reason"] if v else "absent")] += 1
            continue
        head = heads.get(str(v["value"]))
        if head is None:
            dropped["ornament_owning_notehead_not_written"] += 1
            continue
        detail = v.get("detail") or {}
        kind = detail.get("ornament")
        if not kind:
            dropped["ornament_verdict_names_no_kind"] += 1
            continue
        entry: Dict[str, Any] = {"kind": str(kind)}
        # ⚠️ A TREMOLO'S STROKE COUNT, AND ONLY A TREMOLO'S. The legacy entry
        # omits the key entirely for every other mark rather than writing a
        # null, and `_mxl_ornament_elements` reads it that way.
        if detail.get("strokes") is not None:
            entry["strokes"] = int(detail["strokes"])
        head.setdefault("ornaments", []).append(entry)
    return dict(dropped)


def _count_directions(counters: Dict[str, int],
                      directions: Sequence[Tuple[float, str, str]]) -> None:
    """One counter per KIND, at the place the element is written.

    ⚠️⚠️ IT WAS ONE COUNTER AND THAT WOULD HAVE MIS-REPORTED BOTH FAMILIES THE
    DAY WORDS ARRIVED. `counters["dynamics"] += len(directions)` counted every
    entry of the list -- so a `<words>` would have been billed to the
    `dynamic` family, `dynamic` would have read as emitting more than it does,
    and `direction` would have read `decided_but_unwritten` while its elements
    were in the file. `FAMILIES`'s own rule is that only the counter says what
    reached the FILE; a counter that cannot tell two families apart says it of
    neither.

    ⚠️ `_mxl_direction` takes `(kind, text)` and `kind` is already the
    MusicXML child name (`dynamics` / `words`), so the key is DERIVED from the
    kind rather than from a second hand-written table that could drift from
    it.
    """
    for _x, kind, _text in directions:
        counters["dynamics" if kind == "dynamics" else "direction_words"] += 1


def _place_directions(rec: Record, runs: Dict[str, StaffRun]) -> None:
    """Every decided dynamic word, in the cell its DECISION filed it on.

    ⚠️⚠️ THIS FUNCTION EXISTS BECAUSE `adjudicate_dynamic` STOPPED BEING A
    STUB AND NOTHING READ IT. The decision landed 2026-09-09, decides, and
    files a verdict per cell — and `grep '<dynamics' staged/export.py`
    returned ZERO, as did the same grep for every other `<notations>` and
    `<direction>` child. *The value existed and nothing read it*, this
    project's highest-yield pattern, occurring inside the architecture built
    to stop it.

    ⚠️ AND THE COVERAGE HEADLINE HID IT RATHER THAN SHOWING IT.
    `detected_and_unrepresented_total` counts only NO_QUANTITY / starved /
    stub, so the day `dynamic` started deciding, ~284 glyphs (beet5-p3) and
    ~205 (brahms-p2) LEFT the headline with nothing reaching a file. The
    status that carried them is `decided_but_unwritten`, which `coverage()`
    already computes. A headline that improves when the file does not change
    is the shape this repo has paid for repeatedly; read that status beside
    it.

    ⚠️ OWNERSHIP IS NOT RE-ASKED HERE, unlike `_place_notes`.
    `adjudicate_dynamic` queries `Q.GLYPH_OWNER` across the system and keeps a
    letter only where the owner names this staff AND the letter was cut from
    it — so the CELL the verdict is filed on is already the answer, and asking
    again would be a second, differently spelled ownership rule. The two
    decisions apply ONE rule (`A.is_relocated_copy`) at two stages, which is
    why the rule and its argument live in `adjudicate.py` rather than twice.

    ⚠️ A NARROWED VERDICT WRITES NOTHING, DELIBERATELY. An unspellable run
    (`Ruling.narrow`, "there is a mark here and I cannot spell it") is not
    `decided`, so `rec.value` returns None and it never reaches the file. That
    is `OMR_PARTIAL_DYNAMICS`, which was built, measured over the 20-row scan
    gate and REFUSED: `complete` costs +15 edits with NOT ONE ROW BETTER,
    `other` +30. Do not resurrect it on this path without re-pricing it here.
    """
    for key, run in runs.items():
        for cell_index in range(run.n_measures):
            sub = f"cell/{run.page}/{run.system}/{run.staff}/{cell_index}"
            words = rec.value(Q.DYNAMIC, sub)
            if not isinstance(words, list) or not words:
                continue
            verdict = rec.verdict(Q.DYNAMIC, sub) or {}
            detail = verdict.get("detail") or {}
            # ⚠️ THE X IS THE DECISION'S OWN, IN PAGE PIXELS, and it is only
            # used to ORDER marks within one bar. It is NOT compared against a
            # notehead box: `Q.GLYPH_BOX` carries a CANONICAL x, measured
            # inside one cell rescaled so the staff span is constant, and
            # mixing the two frames is exactly the fault that made
            # `Q.ONSET_COLUMN` unreachable until a page frame was added.
            by_text = {w.get("text"): w for w in (detail.get("words") or [])
                       if isinstance(w, dict)}
            cell = run.cells.setdefault(
                cell_index, Cell(run.page, run.system, run.staff, cell_index))
            for text in words:
                w = by_text.get(text) or {}
                x = w.get("x_page")
                cell.directions.append(
                    (float(x) if x is not None else 0.0, "dynamics", str(text)))
            cell.directions.sort()
    _place_direction_words(rec, runs)


def _place_direction_words(rec: Record, runs: Dict[str, StaffRun]) -> None:
    """Every decided direction word, in the cell its DECISION filed it on.

    ⚠️⚠️ WRITTEN IN THE SAME CHANGE AS ITS ADJUDICATOR, DELIBERATELY. Three
    separate sessions on this path each shipped a decision that decided into
    no file for a day -- `adjudicate_dynamic` decided for a day with
    `grep '<dynamics' staged/export.py` returning zero, and `Q.ARC_KIND`
    likewise. `direction` was the LAST declared stub, so there is nowhere left
    for that pattern to hide; the gatherer, the adjudicator, the emission and
    the counter land together or the family is not done.

    ⚠️ IT REUSES `Cell.directions` AND `_legacy._mxl_direction` UNCHANGED.
    That renderer has always taken `(x, kind, text)` with `kind` either
    `dynamics` or `words`, and the legacy path has always emitted words
    through it (`export.measure_direction_words`). Nothing new is rendered
    here -- the staged path stops being the only one that could not say them.

    ⚠️ AT THE HEAD OF THE BAR, the same DECLARED simplification the dynamics
    take, and the same reason: these carry a PAGE x and the noteheads a
    CANONICAL one. ⚠️ AND THE FRAMES HAVE NOT CONVERGED, CHECKED RATHER THAN
    ASSUMED: `gather_detections` does now carry `bbox_page_px` on a glyph row,
    but `_place_notes` indexes its heads by GLYPH INDEX out of the voicing,
    not by a box, and `Cell.directions` is consumed by a renderer that takes
    no note argument. Placing a word against its nearest note is therefore a
    real change to two functions and a separate, measurable question -- not a
    drive-by inside a wiring pass. The legacy path's own placement
    (`_direction_slots`) is where the measured rule lives if it is taken up.

    ⚠️ AN ABSTAINING CELL WRITES NOTHING, WHICH IS THE POINT. `rec.value`
    returns None for a `reader_unavailable` refusal and for a `no_words`
    DECISION it returns `[]` -- and both write nothing, so the FILE cannot
    distinguish them and is not asked to. The record can, which is where that
    distinction belongs: MusicXML has no way to say "a reader could not run
    over this bar", and inventing one would be the fabrication this family is
    built to avoid.
    """
    for key, run in runs.items():
        for cell_index in range(run.n_measures):
            sub = f"cell/{run.page}/{run.system}/{run.staff}/{cell_index}"
            words = rec.value(Q.DIRECTION, sub)
            if not isinstance(words, list) or not words:
                continue
            verdict = rec.verdict(Q.DIRECTION, sub) or {}
            detail = verdict.get("detail") or {}
            by_text: Dict[str, Any] = {}
            for w in (detail.get("words") or []):
                if isinstance(w, dict):
                    by_text.setdefault(w.get("text"), w)
            cell = run.cells.setdefault(
                cell_index, Cell(run.page, run.system, run.staff, cell_index))
            for text in words:
                w = by_text.get(text) or {}
                x = w.get("x_page")
                cell.directions.append(
                    (float(x) if x is not None else 0.0, "words", str(text)))
            cell.directions.sort()


def _tuplet_for(rec: Record, run: StaffRun, cell_index: int,
                glyph_index: Optional[int]) -> Optional[Dict[str, Any]]:
    ratio = rec.value(
        Q.TUPLET_RATIO, f"cell/{run.page}/{run.system}/{run.staff}/{cell_index}")
    if not isinstance(ratio, dict):
        return None
    members = ratio.get("members")
    if isinstance(members, (list, tuple)) and glyph_index not in members:
        return None
    return ratio


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────


def _divisions(parts: Sequence[Sequence[StaffRun]]) -> int:
    """LCM, NOT MAX, and that is what tuplets need.

    A triplet eighth is 1/3 of a quarter; the power-of-two ladder returns 16
    and 16 thirds is not a whole number, so every triplet would round to the
    wrong `<duration>` and shorten its bar. The LCM of powers of two IS their
    maximum, so music without tuplets gets exactly the same number.

    ⚠️ It is computed over the STAGED durations rather than over page dicts —
    the same rule, a different input — and it must include the tuplet ratio,
    because that is where a third comes from.
    """
    divisions = 4
    for part in parts:
        for run in part:
            for cell in run.cells.values():
                for det in cell.detections:
                    beats = det.get("duration_beats")
                    if not beats or beats <= 0:
                        continue
                    denom = Fraction(beats).limit_denominator(
                        _legacy._MAX_DURATION_DENOMINATOR).denominator
                    divisions = _legacy._lcm(divisions, denom)
    return divisions


def _key_dict(fifths: Optional[int]) -> Optional[Dict[str, int]]:
    """`_mxl_attributes_block` speaks sharps/flats; the verdict speaks fifths."""
    if fifths is None:
        return None
    return {"sharps": max(fifths, 0), "flats": max(-fifths, 0)}


def _meter_dict(meter: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The meter, with `symbol=` where a LETTER GLYPH was matched.

    ⚠️ `symbol` COMES FROM THE GLYPH, NEVER FROM THE NUMBERS, and dropping it
    was worth 270 edits on five works — `4/4` and a common-time `C` are one
    bar length and two engravings. The legacy exporter reads only the
    `symbol` field and refuses `raw`, because `rhythm._propagated_meter`
    SYNTHESISES `raw` (`"C"` for any 4/4) so a `raw` of `"C"` there is not
    evidence a C was printed.

    ⚠️ HERE THE PROVENANCE IS DIFFERENT AND THE RULE MUST BE RESTATED, NOT
    COPIED. The staged `raw` comes from `Q.METER_TEMPLATE`, whose reader
    matched a Bravura letter TEMPLATE against the header — so `raw` IS the
    matched glyph. The mapping used is `time_signature_locator`'s own
    (`LETTER_METERS`, and `C|` is cut), imported rather than restated so the
    two cannot drift.
    """
    if not meter:
        return None
    out = dict(meter)
    raw = meter.get("raw")
    try:
        from ..time_signature_locator import LETTER_METERS
    except Exception:                                       # noqa: BLE001
        return out
    if raw in LETTER_METERS:
        out["symbol"] = "cut" if raw == "C|" else "common"
    return out


def _events(cell: Optional[Cell]) -> List[Dict[str, Any]]:
    if cell is None or not cell.detections:
        return []
    return group_chords_in_measure(cell.detections)


def _document_bar_offsets(
        parts: Sequence[Sequence[StaffRun]]
) -> Tuple[Optional[Dict[Tuple[int, int], int]], Dict[str, Any]]:
    """Where in the DOCUMENT's bar sequence each printed system begins.

    ⚠️⚠️ A `<measure number=>` MUST NAME ONE INSTANT IN EVERY PART, AND UNTIL
    2026-09-14 IT DID NOT. `_part_xml` counted 1, 2, 3 … down each part from
    its own first bar, so a part whose staff is SUPPRESSED on a system — which
    a printed orchestral score does constantly — simply skipped those bars and
    every later number in that part was short by the skipped system's length.
    Measured on Litolff Beethoven 5 pp.1-4 (7 systems, 12 parts): eight parts
    hold 111 measures, three hold 93 (missing p3/s1's 18) and one holds 16, so
    page 4's first system opened at measure **64 or 82 depending on which part
    you read**. Verovio said `Mismatching measure number 87` out loud.

    The bar sequence is a fact about the DOCUMENT: systems are read in order,
    each contributes its own bars, and a system's offset is the sum of every
    system before it. A part that is tacet on a system writes no measures for
    it — that stretch of the number line is simply absent from that part — but
    the bars it does write are named by where they stand in the document.

    ⚠️ THIS WRITES NO MUSIC. It changes one attribute on `<measure>` and
    nothing else. Padding the tacet spans is a SEPARATE job and must stay
    separate: padding first would make the numbers line up while the wrong
    notes stayed put, and a graft counted as a note error ranks the work into
    the wrong module.

    **Where the offset comes from.** Only from the record. A system's bar
    count is the count its own staves agree on — the single value shared by
    every staff whose `measure_partition` DECIDED. An ABSTAINING staff is not
    a dissenting vote for zero; it says nothing and is not counted.

    ⚠️⚠️ **AND WHERE IT CANNOT BE DETERMINED, NOTHING IS FABRICATED.** Three
    conditions leave a document unnumberable, each reported by name:

      * `no_staff_decided_its_bar_count` — nothing on that system read a bar
        count, so its length is unknown. Taking it as zero would be a guess
        about a system the page certainly prints bars on.
      * `staves_disagree_about_the_bar_count` — two staves of one system read
        different lengths. A majority vote is available and is REFUSED: *"what
        is most LIKELY, given everything at once"* is INFER-stage work, and a
        wiring pass may connect a decision, never let one guess.
      * `a_part_holds_two_runs_on_one_system` — then two of its runs share an
        offset and would emit the same number twice inside one part. Reachable
        only through the slot join, where two staves could carry one slot.

    ⚠️ **The refusal is WHOLE-FILE, and that is the load-bearing choice.** A
    file numbered document-wide up to the bad system and part-wise after it is
    a file in which `<measure number=N>` means two different things with
    nothing saying where the boundary lies — *"cannot tell"* converted into a
    definite answer by the shape of the output, which is the thing the refusal
    exists to prevent. Refusing returns the exporter to EXACTLY its previous
    behaviour, so this change can never leave a file worse numbered than the
    one it replaces; what it can do is leave it unimproved, out loud.

    Returns `(offsets, report)` — `offsets` is `{(page, system): bars standing
    before it}` or None when refused, and `report` is what coverage says.
    """
    # ⚠️ TALLIED OVER `parts`, NOT OVER `runs`. A run belongs to exactly one
    # part, so this cannot double-count — and it is `parts` that gets
    # numbered, so a run the join left out of every part is also out of the
    # file and has no business setting the number line.
    votes: Dict[Tuple[int, int], "collections.Counter[int]"] = {}
    collisions: List[str] = []
    for part in parts:
        seen: "collections.Counter[Tuple[int, int]]" = collections.Counter()
        for run in part:
            key = (run.page, run.system)
            seen[key] += 1
            tally = votes.setdefault(key, collections.Counter())
            if run.n_measures_decided:
                tally[int(run.n_measures)] += 1
        for key, n in sorted(seen.items()):
            if n > 1:
                collisions.append(f"{key[0]}/{key[1]}")

    rows: List[Dict[str, Any]] = []
    undetermined: List[Dict[str, Any]] = []
    offsets: Dict[Tuple[int, int], int] = {}
    offset = 0
    determined = True
    for key in sorted(votes):
        tally = votes[key]
        bars = next(iter(tally)) if len(tally) == 1 else None
        rows.append({
            "system": f"{key[0]}/{key[1]}",
            # ⚠️ THE INT KEY BESIDE THE DISPLAY STRING, and it is here so that
            # the ONE tally above serves both consumers. The tacet padding
            # needs each system's own bar count — `spans` in `to_musicxml` is
            # built from these rows — and re-tallying it would give this file
            # two copies of a number it counts once, which is the drift shape
            # `_document_bar_offsets`' own docstring exists to prevent.
            "page": key[0],
            "system_index": key[1],
            "bars": bars,
            "staves_deciding": sum(tally.values()),
            "readings": sorted(tally),
            "offset": offset if (bars is not None and determined) else None})
        if bars is None:
            determined = False
            undetermined.append({
                "system": f"{key[0]}/{key[1]}",
                "reason": ("no_staff_decided_its_bar_count" if not tally
                           else "staves_disagree_about_the_bar_count"),
                "readings": sorted(tally)})
            continue
        if determined:
            offsets[key] = offset
        offset += bars

    report: Dict[str, Any] = {
        "systems": rows,
        "document_bars": offset if (determined and not collisions) else None,
    }
    if collisions:
        report["scheme"] = "per_part"
        report["refused"] = "a_part_holds_two_runs_on_one_system"
        report["colliding_systems"] = sorted(set(collisions))
        return None, report
    if not determined:
        report["scheme"] = "per_part"
        report["refused"] = "a_system_bar_count_could_not_be_determined"
        report["undetermined_systems"] = undetermined
        return None, report
    report["scheme"] = "document"
    return offsets, report


def _spans_from_numbering(
        numbering: Dict[str, Any]) -> List[Tuple[Tuple[int, int], int]]:
    """The document's systems in order, each with its own bar count.

    ⚠️⚠️ ONE PROJECTION, TWO CALLERS, AND THAT IS THE POINT. `to_musicxml`
    pads tacet spans with it, and `benchmarks/omr-cleanup-count-2026-09/
    export_arm.py` must name the SAME bars or the system map sends a human to
    the wrong music -- the one failure that map exists to prevent. Held twice
    it would drift, which is the `works.json` arity shape and the
    `_segment_from_change` lesson: a projection with two hand-written copies
    is a defect waiting for one of them to be edited.

    ⚠️ Read off `numbering["systems"]`, never re-counted, so a padded span and
    the number written on it answer to the same tally.
    """
    return [((r["page"], r["system_index"]), int(r["bars"]))
            for r in numbering["systems"] if r["bars"] is not None]


def _tacet_walk(
        part: Sequence[StaffRun],
        offsets: Optional[Dict[Tuple[int, int], int]],
        spans: Optional[Sequence[Tuple[Tuple[int, int], int]]],
) -> List[Tuple[Tuple[int, int], Optional[StaffRun], int]]:
    """This part's systems in DOCUMENT order, with a hole where it is tacet.

    `[(system key, the part's run there or None, that system's bar count)]`.

    ⚠️ WITHOUT THE NUMBER LINE THERE IS NO WALK, and the `None` guard is that
    statement rather than defensiveness. A tacet span has to be written at a
    definite place in the document's bar sequence; when `_document_bar_offsets`
    REFUSED there is no such sequence, and padding anyway would put invented
    bars at numbers chosen by this function — *"cannot tell"* converted into a
    definite answer by a second route. So the walk falls back to the part's own
    runs, which is exactly the file this exporter writes today.
    """
    if offsets is None or spans is None:
        return [((r.page, r.system), r, r.n_measures) for r in part]
    by_system: Dict[Tuple[int, int], StaffRun] = {
        (r.page, r.system): r for r in part}
    return [(key, by_system.get(key), bars) for key, bars in spans]


def _tacet_report(parts: Sequence[Sequence[StaffRun]],
                  offsets: Optional[Dict[Tuple[int, int], int]],
                  spans: Optional[Sequence[Tuple[Tuple[int, int], int]]],
                  counters: Dict[str, int]) -> Dict[str, Any]:
    """What the padding reached, what it wrote, and what it refused.

    ⚠️ IT IS A PARTITION AND IT IS ASSERTED, not three numbers side by side:
    every tacet bar the document holds is padded, refused for want of a meter,
    or refused for want of a number, and `balanced` says whether they sum. The
    controls in this file that were allowed to be inequalities are the ones
    that hid ten hairpins and 595 notes.
    """
    total = 0
    rows: List[Dict[str, Any]] = []
    if spans is not None:
        for pi, part in enumerate(parts):
            here = {(r.page, r.system) for r in part}
            missing = [(k, n) for k, n in spans if k not in here]
            total += sum(n for _k, n in missing)
            if missing:
                rows.append({
                    "part": f"P{pi + 1}",
                    "systems": [f"{k[0]}/{k[1]}" for k, _n in missing],
                    "bars": sum(n for _k, n in missing)})
    padded = int(counters.get("tacet_bars_padded", 0))
    no_meter = int(counters.get("tacet_bars_not_padded_without_meter", 0))
    no_number = int(counters.get("tacet_bars_not_padded_without_a_number", 0))
    out: Dict[str, Any] = {
        "tacet_bar_total": total,
        "parts_tacet_somewhere": len(rows),
        "bars_padded": padded,
        "bars_not_padded_without_meter": no_meter,
        "bars_not_padded_without_a_number": no_number,
        "balanced": padded + no_meter + no_number == total,
        "spans": rows,
    }
    if offsets is None:
        # ⚠️ NOT A ZERO. With no number line nothing was even LOOKED at, and
        # the two must not read alike.
        out["refused"] = "the_document_bar_sequence_was_refused"
        out["tacet_bar_total"] = None
        out["balanced"] = None
    return out


def _pad_tacet_span(lines: List[str], sys_key: Tuple[int, int], sys_bars: int,
                    offsets: Dict[Tuple[int, int], int],
                    meters: Dict[Tuple[int, int], Any],
                    divisions: int, counters: Dict[str, int],
                    segments_on: bool, first: bool
                    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """The bars of one system this part does not print.

    Returns `(the new first, the meter this span DECLARED into the file)`.

    ⚠️⚠️ THE SECOND RETURN IS ROADMAP 2.8 AND IT IS NOT BOOKKEEPING. A LEADING
    pad emits the only `<attributes>` block this part may ever carry, so the
    meter IN FORCE for every later bar of the part can have been declared
    HERE — and 2.8 judges a bar against the meter a reader of the FILE sees,
    not against the one the record happened to file on that bar's own system.
    Without this, a part tacet on the document's first system would have its
    later bars judged unassessable while the file was quietly asserting a
    length for every one of them.

    ⚠️ ONE BAR AT A TIME, AND THE METER IS ASKED PER BAR, because a system can
    print a meter CHANGE part-way through (`Q.METER`'s `segments`). A span that
    took one meter for the whole system would be the same fault
    `_part_xml` carried for a year, reintroduced in a new branch.

    ⚠️ `prev` IS DELIBERATELY NOT TOUCHED, and that is what makes the change
    checkable. A padded bar states no clef and no key — this part is not
    printed here, so we have neither — so leaving the attribute state alone
    means the next REAL run emits exactly the attributes it emits today, and
    the file is byte-identical outside the inserted `<measure>` blocks. A
    control that strong is worth more than a tidier-looking attribute stream.

    ⚠️ THE ONE EXCEPTION IS `divisions`, WHICH IS A FACT ABOUT THE FILE AND NOT
    ABOUT THE STAFF. A part tacet on the document's FIRST system would
    otherwise open with a measure carrying no `<attributes>` at all, so a
    LEADING pad emits the divisions block (and the meter it just proved it
    knows) and hands `first=False` on. `prev` still holds its sentinels, so the
    first real run's `changed` test fires and its clef and key are written as
    usual.
    """
    base = offsets.get(sys_key)
    sys_meter = meters.get(sys_key)
    declared: Optional[Dict[str, Any]] = None
    if base is None:
        # Unreachable while `offsets` and `spans` come from one tally, and a
        # refusal rather than a fabricated number if that ever stops being so.
        counters["tacet_bars_not_padded_without_a_number"] += sys_bars
        return first, None
    for i in range(sys_bars):
        meter = _meter_dict(meter_at(sys_meter, i) if segments_on
                            else sys_meter)
        if meter is None:
            # ⚠️⚠️ THE REFUSAL, AND IT IS THE POINT OF THE WHOLE FUNCTION.
            # `_mxl_measure_rest(None)` returns 4.0 quarters — a whole rest —
            # and on this document's 2/4 that is twice the bar. An eventless
            # bar of a PRESENT part has to be written somehow and takes that
            # fallback with `measure="yes"` withheld; a tacet bar does not
            # have to be written at all, so inventing one at a length nobody
            # read buys alignment with fiction. Counted, and visible in
            # `report["tacet_padding"]`.
            counters["tacet_bars_not_padded_without_meter"] += 1
            continue
        lines.append(f'    <measure number="{base + i + 1}">')
        if first:
            lines.append(_legacy._mxl_attributes_block(
                None, None, meter, divisions, "      ",
                include_divisions=True))
            first = False
            declared = meter
        # ⚠️ NO DIRECTIONS AND NO WEDGES, unlike the eventless branch. Those
        # come off THIS STAFF's cells and a tacet part has no staff here; a
        # mark printed in the gap belongs to whichever staff `glyph_owner`
        # gave it, which is never this one.
        lines.extend(_legacy._mxl_empty_measure(
            meter, divisions, None, "      "))
        lines.append("    </measure>")
        counters["tacet_bars_padded"] += 1
    return first, declared


def _part_xml(rec: Record, part: Sequence[StaffRun], pid: str,
              divisions: int, counters: Dict[str, int],
              offsets: Optional[Dict[Tuple[int, int], int]] = None,
              spans: Optional[Sequence[Tuple[Tuple[int, int], int]]] = None,
              meters: Optional[Dict[Tuple[int, int], Any]] = None,
              drops: Optional[Any] = None,
              held_bars: Optional[List[Dict[str, Any]]] = None,
              marks: Optional[Dict[str, int]] = None) -> str:
    """One `<part>`: every measure of every system this part appears on.

    ⚠️⚠️ `drops` AND `held_bars` ARE ROADMAP 2.8, AND `drops` IS NOT OPTIONAL
    IN PRACTICE. It is `_place_notes._drop`'s discipline reaching the render:
    one callable that counts a refused note BY REASON and BY SYSTEM at once,
    so a refusal cannot reach one counter and miss the other — the equality
    `build` asserts, and `to_musicxml` re-asserts after this function has run.
    A caller passing None gets the hold-out WITHOUT the accounting, which is
    only ever right for a test that is not reading the balance; the default is
    None so the three test modules that call `_part_xml` positionally keep
    working, not because counting is discretionary.

    ⚠️ `offsets` is `_document_bar_offsets`'s answer: with it, a measure is
    named by its place in the DOCUMENT's bar sequence, so one number means one
    instant in every part. Without it — the refusal — the count runs down the
    part from 1, which is this exporter's own previous behaviour and is
    demonstrably wrong across parts; the coverage report says which happened
    and why, because a number that means two different things in two files
    must never be silent about which one it is.

    ⚠️⚠️ `spans` AND `meters` ARE THE TACET PADDING, AND IT WRITES SILENCE
    ONLY WHERE IT KNOWS HOW LONG THE SILENCE IS. A printed orchestral score
    suppresses a tacet staff, so a part absent from a system held no measures
    for it at all and came out SHORT — 93 against 111 on Litolff Beethoven 5
    pp.1-4, and one part that simply stopped after bar 16. With the number
    line settled those bars have a definite place, so they can be written as
    full-measure rests: the instrument really is silent there, which is what
    suppression MEANS, and this is the one padding case where the rest is
    musically right rather than a stand-in for ink we failed to read.

    ⚠️ ITS LENGTH IS A DIFFERENT QUESTION, AND IT IS REFUSED RATHER THAN
    GUESSED. A MusicXML rest must carry a `<duration>`, and
    `_measure_rest_beats` falls back to 4.0 for an unknown meter — so padding
    a 2/4 bar with no meter read writes a rest twice too long, *"cannot tell"*
    converted into a definite answer. Nothing forces these bars to exist: they
    are ours to invent or not. So a tacet bar whose system has no meter is
    NOT WRITTEN and is COUNTED (`tacet_bars_not_padded_without_meter`), and
    the lever on that count is the meter — `OMR_METER_CARRY` — not this rule.

    ⚠️ AND THIS IS *NOT* THE EVENTLESS-BAR BRANCH BELOW, THOUGH BOTH EMIT A
    RESTING BAR. That one is a bar THE PAGE PRINTS for this staff and we read
    nothing in; this one is a bar the page prints for this part not at all.
    The repairs differ — one is a reading gap, the other a join fact — so the
    counters are separate, and `empty_bars_padded` must never absorb a padded
    tacet bar.
    """
    lines = [f'  <part id="{pid}">']
    number = 0
    prev = {"clef": object(), "key": object(), "time": object()}
    first = True
    segments_on = meter_segments_enabled()
    # ⚠️⚠️ ROADMAP 2.8: THE METER A READER OF THIS FILE SEES, which is NOT
    # always the one `Q.METER` filed on this bar's own system. `<time>` is
    # written only where it CHANGES, so once a part has declared one it stays
    # in force for every later bar until another is written — a bar whose own
    # system never settled a meter is, to music21 or to Verovio, in the last
    # meter this part declared. Judging such a bar as UNASSESSABLE would let
    # the file assert a length for it that nothing ever checked: on Breitkopf
    # Brahms 1 that is 3,826 of 5,803 bars with events, and the independent
    # control found 3,132 of them not adding up while the exporter believed
    # it had assessed nothing. So the hold-out reads what the FILE claims.
    #
    # ⚠️ None until the part declares its first `<time>`, and then a bar
    # really is unassessable — there is no claim to hold it to.
    in_force: Optional[Dict[str, Any]] = None
    for sys_key, maybe_run, sys_bars in _tacet_walk(part, offsets, spans):
        if maybe_run is None:
            first, _declared = _pad_tacet_span(
                lines, sys_key, sys_bars, offsets or {}, meters or {},
                divisions, counters, segments_on, first)
            # ⚠️ ROADMAP 2.8: a LEADING pad can be the only place this part
            # ever declares a `<time>`, and every later bar is read against
            # it. See `_pad_tacet_span`'s second return value.
            if _declared is not None:
                in_force = _declared
            continue
        run = maybe_run
        key = _key_dict(run.fifths)
        # ⚠️ `.get`, and a MISSING key falls back rather than raising — but
        # it cannot be missing on the document scheme, because the offsets are
        # tallied over these same `parts`. The fallback is here so that a
        # future caller passing a partial map degrades to the old numbering
        # instead of crashing mid-file, which is the loud-but-recoverable end
        # of the same choice the whole-file refusal makes.
        base = None if offsets is None else offsets.get((run.page, run.system))
        for i in range(run.n_measures):
            # ⚠️⚠️ THE METER IS READ PER BAR, AND FOR A LONG TIME IT WAS NOT.
            # This line used to sit outside the loop, one meter for the whole
            # run — so `Q.METER`'s `segments`, the field the last three
            # sessions built to say *"6/8, then 9/8 from bar 6"*, reached no
            # file at all and `record.meter_at` was called by nothing but its
            # own tests. Measured on Brahms 1 iv: the `¢` sat on the record at
            # `from_cell 6` on 24 staves of 24 at support 74.0, and the export
            # declared `<time>` once per part, `4/4 symbol="common"`, at
            # measure 1.
            #
            # ⚠️ `meter_at` MAY RETURN None FOR A BAR NO SEGMENT COVERS, and
            # that is a real answer rather than a gap: a system can print a
            # change at bar 8 while never stating what bars 0-7 were in. The
            # `meter is None` branch below already withholds `measure="yes"`
            # for exactly that reason, so an unknown opening stays unknown
            # instead of inheriting the meter that follows it.
            meter = _meter_dict(meter_at(run.meter, i) if segments_on
                                else run.meter)
            number += 1
            lines.append(
                f'    <measure number="{number if base is None else base + i + 1}">')
            # ⚠️ ROADMAP 2.1b. `condensed` joins the attributes-change test
            # so a run entering or leaving a doubled span always forces a
            # fresh `<attributes>` block -- `<transpose>` has nowhere else to
            # be written, and a part that starts on a doubled run needs it
            # from its very first measure regardless of whether clef/key/
            # time happen to match whatever `prev` already held.
            condensed = bool(run.condensed_from)
            changed = (run.clef != prev["clef"] or key != prev["key"]
                       or meter != prev["time"]
                       or condensed != prev.get("condensed", False))
            if first or changed:
                attrs = _legacy._mxl_attributes_block(
                    run.clef, key, meter, divisions, "      ",
                    include_divisions=first)
                if condensed:
                    attrs = _insert_transpose(attrs, "      ")
                lines.append(attrs)
                prev = {"clef": run.clef, "key": key, "time": meter,
                       "condensed": condensed}
                first = False
                # ⚠️ ROADMAP 2.8, and it is INSIDE the branch that actually
                # emits: `_mxl_attributes_block` writes `<time>` only for a
                # non-None meter, so this is the one line where the file's
                # claim about bar length changes. Updating it outside would
                # track what we KNEW rather than what we WROTE.
                if meter is not None:
                    in_force = meter
            cell_here = run.cells.get(i)
            directions = list(cell_here.directions) if cell_here else []
            events = _events(cell_here)
            # ⚠️⚠️ ROADMAP 2.8, AND IT IS DECIDED BEFORE ANYTHING IS WRITTEN.
            # A held-out bar takes `_mxl_empty_measure`, which writes the
            # bar's directions itself — so the test cannot sit after the
            # `<direction>` lines have already been appended.
            # ⚠️⚠️ ONE `why` LIST, HANDED ON WITH THE STREAMS. The first draft
            # of this passed a throwaway `[]` to `_voice_split` and a SECOND
            # `[]` to `_measure_xml`, which silently pinned every
            # `two_voice_bars_refused_*` counter at zero — a split refusal
            # that reached nobody. Caught by `test_the_refusals_are_counted_
            # APART`, which is in the SLOW tier and therefore not by the fast
            # one: the reasons are the diagnosis, not decoration.
            _why: List[str] = []
            split = ((_voice_split(rec, run, i, events, _why), _why)
                     if events else None)
            # ⚠️ THE METER THE FILE CLAIMS, not the one this bar's own system
            # filed — see `in_force` above. `meter` is still what gets WRITTEN
            # and what sizes a held-out bar's rest; this is only what the bar
            # is JUDGED against.
            judged = meter if meter is not None else in_force
            held = (_bar_holds_out(events, split[0], divisions, judged)
                    if events else None)
            if events:
                counters["bars_with_events"] += 1
                counters["bars_with_events_without_a_meter"] += (
                    1 if _bar_quarters(judged) is None else 0)
                counters["bars_judged_by_a_carried_meter"] += (
                    1 if meter is None and judged is not None else 0)
            if held is not None:
                # ⚠️⚠️ THE HOLD-OUT, AND IT IS NOT A MARK ON A KEPT BAR.
                # Sean, 2026-09-23: *"hold out — I don't care about print
                # right now — I want to know what we are getting correct."*
                # The bar takes EXACTLY the branch a bar we read nothing in
                # takes, because that is what it is: a bar we could not read
                # to its meter is a bar we could not read (rule 8). Nothing
                # pads it, trims it, or re-times it to fit.
                #
                # ⚠️ ITS OWN COUNTER, NEVER `empty_bars_padded`. That figure
                # means *the detector found no event here*; this one means
                # *we found events and they do not add up*. The repairs are
                # opposite — recall against rhythm — and the tacet/eventless
                # split one branch down was made for the same reason.
                counters["bars_held_out_sum"] += 1
                if split[0] is not None:
                    # ⚠️ THE FIFTH PLACE A TWO-VOICE VERDICT CAN GO, and it is
                    # named for the same reason `two_voice_bars_in_an_unread_
                    # bar` is: without it the split's own accounting is a
                    # FILTER rather than a PARTITION, because this bar reaches
                    # `_measure_xml` not at all and neither of its counters
                    # sees it.
                    counters["two_voice_bars_held_out_by_sum"] += 1
                if run.condensed_from is None:
                    n_rows = _bar_event_rows(events)
                    counters["notes_held_out_sum"] += n_rows
                    if drops is not None:
                        for _ in range(n_rows):
                            drops(_BAR_SUM_REFUSAL, run.page, run.system)
                    if marks is not None:
                        for _fam, _n in _held_bar_marks(events).items():
                            marks[_fam] += _n
                    if held_bars is not None:
                        held_bars.append({
                            "page": run.page, "system": run.system,
                            "staff": run.staff, "cell": i,
                            "measure": number if base is None else base + i + 1,
                            "part": pid, "events": len(events),
                            "noteheads_and_rests": n_rows,
                            # ⚠️ Whether the length this bar was judged
                            # against was DECLARED at it or CARRIED to it by
                            # the file. A reader chasing a held bar needs to
                            # know which, because the repair differs: one is
                            # rhythm, the other is `Q.METER`'s reach.
                            "meter_carried_in_file": meter is None,
                            **held})
                else:
                    # ⚠️⚠️ ROADMAP 2.1b MEETS 2.8, AND THE EQUALITY DEPENDS
                    # ON THIS. A condensed staff's doubled Contrabass copy
                    # holds a SECOND copy of ink the log recorded ONCE
                    # (`_condensed_double`), and the written side subtracts
                    # it under `notes_doubled_to_condensed_slot`. Counting a
                    # refusal for it too would charge the balance for a row
                    # that does not exist, so the copy is held out and NOT
                    # counted. ⚠️ The two copies can genuinely disagree: the
                    # copy is stripped of `glyph` (see
                    # `_CONDENSED_STRIP_KEYS`), so `_voice_split` cannot
                    # place its notes into streams and judges it as one
                    # voice. That is recorded here rather than papered over.
                    counters["bars_held_out_sum_on_a_doubled_staff"] += 1
                # ⚠️ SIZED BY `judged`, THE METER IN FORCE IN THE FILE, and
                # NOT by this bar's own — the one that is None here is the one
                # that would make `_measure_rest_beats` fall back to 4.0 and
                # write a whole rest into a 6/8 bar the file has already
                # declared as three quarters. A bar can only be HELD OUT where
                # a length is known, so this is never the fallback.
                lines.extend(_legacy._mxl_empty_measure(
                    judged, divisions, directions or None, "      "))
                _count_directions(counters, directions)
            elif not events:
                # ⚠️ COUNTED AS `empty_bars_padded`, NOT AS A MEASURE REST.
                # We read NOTHING in this bar; a bar where we actually read a
                # whole rest is `measure_rests_read`, and conflating the two
                # would report a page as full of measure rests when what it is
                # full of is unread bars. Beethoven p3: 48 padded against 19
                # read.
                #
                # ⚠️ AN EVENTLESS BAR IS A BAR WE READ NOTHING IN, AND SAYING
                # SO IS NOT THE SAME AS SAYING IT IS SILENT. `measure="yes"`
                # is withheld where the meter is unknown, exactly as the
                # legacy exporter withholds it: `_measure_rest_beats` falls
                # back to 4.0 there, and asserting "this bar is 4.0 long" on a
                # page whose meter we never read is a guess dressed as a fact.
                #
                # ⚠️ AND ON THE STAGED PATH THIS BRANCH IS ALSO WHERE THE
                # WHOLE-REST CONVENTION WOULD LIVE — a whole-rest glyph means
                # the BAR, not four quarters of silence. It cannot live here
                # yet, because NOTHING IN THE STAGED RECORD READS A REST AT
                # ALL: see this module's header and `coverage()`. The position
                # is stated here so that the day a rest quantity lands, the
                # rule has a home rather than being rediscovered.
                counters["empty_bars_padded"] += 1
                # ⚠️ WRITTEN EVEN WHEN IT IS ZERO, and the `+= 0` is the whole
                # point rather than a clumsy `if`. This counter is a QUALIFIED
                # SUBSET of the one above it, so while it was incremented only
                # on the bad branch it was simply ABSENT from the report when
                # every padded bar had a meter — and a reader could not tell
                # *"we sized all 184 of them correctly"* from *"this figure was
                # never computed"*. Measured: on Litolff `984073` p1-4 it reads
                # 168 with the meter unsettled and VANISHES once it is settled,
                # which is exactly the run whose success it was supposed to
                # report. Same lesson as `decided_uncounted` — "the report
                # cannot tell" is a different fact from "wrote zero" — arriving
                # in the rest path.
                # ⚠️⚠️ `judged`, NOT `meter`, AND THE CHANGE IS ROADMAP 2.8's
                # DOING RATHER THAN ITS SUBJECT. `_measure_rest_beats(None)`
                # is 4.0, so an eventless bar whose own system never settled a
                # meter was written as a FOUR-QUARTER whole rest — into a part
                # whose `<time>` the file had already declared as 6/8. The
                # bar then contradicts the file's own claim about its length:
                # 232 such bars on Breitkopf Brahms 1, every one of them
                # `rest:whole` 4.0 against a 3.0 bar, and they were the entire
                # residue left after the hold-out. Sizing the rest by the
                # meter IN FORCE IN THE FILE is not inventing one — it is
                # refusing to write a length that contradicts the one already
                # written. Where the part has declared no `<time>` at all,
                # `judged` is None, the 4.0 fallback stands and `measure="yes"`
                # is still withheld, exactly as before.
                counters["empty_bars_padded_without_meter"] += (
                    1 if judged is None else 0)
                counters["empty_bars_sized_by_a_carried_meter"] += (
                    1 if meter is None and judged is not None else 0)
                # ⚠️ THE FOURTH PLACE A TWO-VOICE VERDICT CAN GO, and without
                # it the split's accounting is a FILTER rather than a
                # PARTITION. The record read two streams among notes the
                # exporter then wrote none of, so this bar never reaches
                # `_measure_xml` at all and neither refusal counter sees it.
                # Measured on Litolff `984073` p1-3: 19 two-voice verdicts =
                # 11 written + 5 straddled + 1 empty stream + **2 here**.
                vv = rec.verdict(Q.VOICES, R_cell_key(run, i))
                if (vv and vv["outcome"] == "decided"
                        and int((vv["value"] or {}).get("n_voices") or 1) > 1):
                    counters["two_voice_bars_in_an_unread_bar"] += 1
                # ⚠️ A BAR WITH NO NOTES STILL CARRIES ITS MARKS. The legacy
                # exporter dropped dynamics on exactly this branch for a month
                # (`_mxl_empty_measure`'s own docstring), and it takes a SCAN
                # to see it -- an engraved page puts an event in every bar. The
                # staged path is fed the marks from the start rather than
                # rediscovering that.
                lines.extend(_legacy._mxl_empty_measure(
                    judged, divisions, directions or None, "      "))
                _count_directions(counters, directions)
            else:
                # ⚠️ AT THE HEAD OF THE BAR, AND THAT IS A DECLARED
                # SIMPLIFICATION, NOT AN OVERSIGHT. The legacy events path
                # places a dynamic against its NEAREST NOTE
                # (`_direction_slots`); this path cannot, because the marks
                # carry a PAGE x and the noteheads a CANONICAL one, and
                # comparing the two is precisely the frame error that made
                # `Q.ONSET_COLUMN` report 1,062 columns of nothing. A
                # `<direction>` carries no duration and is legal at offset 0,
                # so the bar head is the honest answer until the record
                # carries one frame for both. ⚠️ Placement is also exactly
                # what stops a correctly recovered `sf` from PAIRING with a
                # truth, so do not read a flat metric here as this being free.
                lines.extend(_legacy._mxl_direction((kind, text), "      ")
                             for _x, kind, text in directions)
                _count_directions(counters, directions)
                lines.extend(_measure_xml(rec, run, i, events, divisions,
                                          counters, split=split))
            lines.append("    </measure>")
    lines.append("  </part>")
    return "\n".join(lines)


def _voice_split(rec: Record, run: StaffRun, cell_index: int,
                 events: List[Dict[str, Any]],
                 why: Optional[List[str]] = None
                 ) -> Optional[List[List[Dict[str, Any]]]]:
    """This bar's events partitioned into voices, or None for one stream.

    ⚠️ THE RECORD'S DECISION, NOT A SECOND SPLIT. `adjudicate_voices` calls
    `voicing.split_events_into_voices` and records the answer as GLYPH lists;
    re-running the splitter here would be a second copy of a rule nothing
    forces to agree with the first, which is how the staged and legacy
    `<backup>` arithmetic would come apart.

    ⚠️ AN EVENT GOES WHERE ITS GLYPHS GO, and a REST goes in EVERY stream --
    that is the convention the verdict names in `rests_in_every_voice`, and
    it is why this is a cover rather than a partition. An event whose glyphs
    the verdict does not mention (the exporter writes only the notes it
    could) falls to voice 1, which is where `split_events_into_voices` puts
    an unknown-direction event too.
    """
    why = [] if why is None else why
    v = rec.verdict(Q.VOICES, R_cell_key(run, cell_index))
    if not v or v["outcome"] != "decided":
        return None
    value = v["value"] or {}
    if int(value.get("n_voices") or 1) < 2:
        return None
    streams = [set(vs) for vs in (value.get("voices") or [])]
    if len(streams) < 2:
        why.append("the_verdict_names_fewer_than_two_streams")
        return None
    # ⚠️⚠️ A REST MAY BE IN EVERY STREAM. NOTHING ELSE MAY, AND THIS BAR IS
    # REFUSED WHERE SOMETHING ELSE IS -- found by the accounting control on the
    # second document this ran against, not by review.
    #
    # `Q.VOICES` partitions `Q.EVENT`'s groups, and `Q.EVENT` groups every
    # notehead the record READ; this function's `events` come from
    # `group_chords_in_measure`, which groups only the ones the exporter can
    # WRITE. So the two groupings need not agree, and a chord the exporter
    # formed can span two of the record's streams -- writing every one of its
    # notes TWICE. Measured on Litolff `984073` p1-3: **7 chord events**, three
    # of three notes and four of two, which is the 17 extra the balance
    # reported to the unit (1880 written against 1863 in the log).
    #
    # ⚠️ THE REFUSAL IS THE POINT, NOT A MAJORITY VOTE. Picking the stream
    # holding most of the chord's notes would be the EXPORTER deciding a
    # question the record did not answer -- the same overreach as collapsing a
    # narrowed duration by argmax, which this module refuses one screen up. A
    # bar it cannot place is written as one voice and COUNTED.
    in_both = set(value.get("rests_in_every_voice") or ())
    out: List[List[Dict[str, Any]]] = [[] for _ in streams]
    for ev in events:
        glyphs = {d.get("glyph") for d in (ev.get("noteheads") or [])}
        rest = ev.get("rest") or {}
        if rest.get("glyph"):
            glyphs.add(rest["glyph"])
        indices = {_glyph_index(g) for g in glyphs if g}
        hit = [i for i, s in enumerate(streams) if indices & s]
        if len(hit) > 1 and not indices <= in_both:
            why.append("event_straddles_two_streams")
            return None
        for i in hit:
            out[i].append(ev)
        if not hit:
            out[0].append(ev)
    if any(not s for s in out):
        # ⚠️ A STREAM THE EXPORTER COULD NOT FILL IS NO SPLIT AT ALL. The
        # verdict saw two voices among the notes it READ; if every note of
        # one of them was dropped on the way out, writing an empty
        # `<backup>`-separated voice puts a `<backup>` in the file for
        # nothing.
        why.append("a_stream_has_no_written_note")
        return None
    return out


def _glyph_index(key: str) -> Optional[int]:
    try:
        return int(str(key).rsplit("/", 1)[-1])
    except (TypeError, ValueError):
        return None


def R_cell_key(run: StaffRun, cell_index: int) -> str:
    return f"cell/{run.page}/{run.system}/{run.staff}/{cell_index}"


def _annotate_beams_for(rec: Record, run: StaffRun, cell_index: int,
                        stream: List[Dict[str, Any]],
                        counters: Dict[str, int]) -> None:
    """Give one voice's events their `beam_states`, in place.

    ⚠️⚠️ WHY THIS IS A WIRE AND NOT A RULE. `_legacy.annotate_beams` is
    IMPORTED AND CALLED, never ported: its docstring records FOUR grouping
    rules, each paid for by a measured failure (the notehead-width pad, the
    same-stack collapse that took Mozart 41 from 7 to 145 beam edits, the
    box-containing-two-disjoint-boxes guard, the divisi two-row case).
    Restating any of them here would give this project two copies of numbers
    it paid to measure once -- the drift `LETTER_METERS` and the arc constants
    are both imported to prevent.

    ⚠️ ADDITIVE BY CONSTRUCTION. A cell with no beam stroke, or with no
    notehead carrying both frames, produces no boxes -- so `annotate_beams`
    sets nothing and every note stays exactly as it was. That is why this
    needs no flag: where the CV read no beam, the file does not move.
    """
    cell = run.cells.get(cell_index)
    if cell is None or not stream:
        return
    # ⚠️ `R_cell_key`, not a third copy of the f-string. It is defined
    # directly above this function and `_stem_probes` already restates it --
    # the "imported rather than restated" rule this file applies to
    # `LETTER_METERS` and the arc constants, applied to a key format.
    key = R_cell_key(run, cell_index)
    # ⚠️ The per-record map is built ONCE and cached on the Record, not
    # rebuilt per bar: `obs_of` walks every observation, and doing that inside
    # a loop over 1,183 bars is quadratic in the record.
    # ⚠️ `is None`, NOT falsiness: an empty map is a legitimate answer for a
    # record with no beam strokes, and `if not cache` would rebuild it on
    # every bar of exactly that document. The `{}` is falsy but is not None
    # hazard this repo records for `_carry_meter`.
    cache = getattr(rec, "_beam_box_cache", None)
    if cache is None:
        cache = _beam_boxes_by_cell(rec)
        setattr(rec, "_beam_box_cache", cache)
    boxes = cache.get(key)
    if not boxes:
        return
    dets = _beam_detections_page(cell, boxes)
    if not dets:
        counters["beam_cells_without_a_frame_ruler"] += 1
        return
    _legacy.annotate_beams(stream, dets)


def _measure_xml(rec: Record, run: StaffRun, cell_index: int,
                 events: List[Dict[str, Any]], divisions: int,
                 counters: Dict[str, int],
                 split: Optional[Tuple[Optional[List[List[Dict[str, Any]]]],
                                       List[str]]] = None) -> List[str]:
    """One bar's notes — one voice, or two separated by a `<backup>`.

    ⚠️ `split` IS `_voice_split`'s ANSWER, COMPUTED ONCE BY THE CALLER, and it
    exists because ROADMAP 2.8 has to know the voices BEFORE it knows whether
    to render the bar at all — a bar is held out per VOICE. Re-running the
    split here would be a second call of a function whose `why` list feeds
    counters, i.e. two chances to disagree about one bar. Passing None keeps
    the old self-contained behaviour for a caller that has not split yet.

    ⚠️⚠️ THE STAGED PATH WROTE `<voice>1</voice>` ON EVERYTHING UNTIL
    2026-09-10, and that was not merely a simplification: `_paired_spans` takes
    a `voice_of` map to refuse an arc whose ends land in different streams —
    because such an arc is UNPAIRED at both ends and makes the file invalid —
    and this exporter passed it an EMPTY dict. The rule was present, inert,
    and indistinguishable from one that had run and found nothing.
    """
    # ⚠️ THE REASONS ARE COUNTED APART, because their repairs differ: an
    # event straddling two streams is two GROUPINGS disagreeing, while a
    # stream with no written note is a bar whose notes the exporter dropped.
    # A single "refused" total would send the next reader to the wrong place.
    if split is None:
        why: List[str] = []
        streams = _voice_split(rec, run, cell_index, events, why)
    else:
        streams, why = split
    # ⚠️⚠️ PER VOICE, AND THAT IS NOT A DETAIL. `annotate_beams`' own docstring
    # says it "must be called PER VOICE": two voices interleave in x, so a run
    # computed across both is broken by the other voice's notes. The split is
    # already done here, which is why the call belongs at this seam and not in
    # `_place_notes`.
    for stream in (streams if streams is not None else [events]):
        _annotate_beams_for(rec, run, cell_index, stream, counters)
    # ⚠️ ROADMAP 2.1b. Whether this bar's notes are the doubled Contrabass
    # copy of a condensed staff, so the render sites below can count each
    # written note under `notes_doubled_to_condensed_slot` as well as under
    # its own family -- the note is written TWICE and the accounting
    # EQUALITY (`to_musicxml`'s `Unbalanced` control) needs the extra copy
    # named, not merely absorbed.
    doubled = bool(run.condensed_from)
    if streams is None:
        for reason in why:
            counters["two_voice_bars_refused_" + reason] += 1
        lines, _units = _measure_events_xml(events, divisions, counters,
                                            doubled=doubled)
        return lines
    counters["two_voice_bars"] += 1
    out, units = _measure_events_xml(streams[0], divisions, counters,
                                     voice=1, doubled=doubled)
    if units > 0:
        out.append("      <backup>\n"
                   f"        <duration>{units}</duration>\n"
                   "      </backup>")
    second, _ = _measure_events_xml(streams[1], divisions, counters, voice=2,
                                    doubled=doubled)
    out.extend(second)
    # ⚠️ THE DUPLICATED RESTS ARE COUNTED, because the note-accounting control
    # is an EQUALITY and a rest written once per voice would break it for
    # correct behaviour. Naming the duplicate is what keeps the control able
    # to fail for the right reason.
    shared = [ev for ev in streams[1] if ev.get("kind") == "rest"
              and any(ev is other for other in streams[0])]
    counters["rests_duplicated_across_voices"] += len(shared)
    # ⚠️ AND THE MARKS ON IT, for the same reason. A fermata on a shared rest
    # produces TWO `<fermata>` elements from ONE mark, which would make
    # `fermata_balance` -- `written + not_written <= marks_in_log` -- go False
    # for correct behaviour. Counting the duplicate is what keeps that control
    # able to fail for the RIGHT reason. Found by predicting it and writing
    # the test, not by a page: no bar of the measured document holds one.
    counters["fermatas_duplicated_across_voices"] += sum(
        1 for ev in shared if (ev.get("rest") or {}).get("fermata"))
    return out


#: ROADMAP 2.8's refusal. A notehead or rest in a bar whose durations do not
#: sum to the meter in force: the bar is HELD OUT (Sean, 2026-09-23 --
#: *"hold out -- I want to know what we are getting correct"*) and every event
#: in it is counted here, so the accounting EQUALITY still balances.
_BAR_SUM_REFUSAL = "bar_does_not_add_up"


def _event_units(ev: Dict[str, Any], divisions: int) -> int:
    """How far ONE event advances this voice's cursor, in `<duration>` units.

    ⚠️⚠️ THE ONE COPY, AND THAT IS THE WHOLE REASON IT IS A FUNCTION.
    `_measure_events_xml` accumulates the figure `<backup>` is written from by
    calling this, and ROADMAP 2.8's bar-sum test (`_bar_holds_out`) compares
    the SAME number against the meter -- so the arithmetic the file holds and
    the arithmetic the check reasons about cannot come apart. Two spellings
    would be two rules nothing forces to agree, which is the duplicated-rule
    fault `build_sheet.py`'s stale copy of `_place_notes`' refusals already
    cost this project once.

    ⚠️⚠️ A CHORD IS ONE EVENT -- CLAUDE.md §10's double-counting trap. Its
    members share one x and one stem and only the first `<note>` advances
    MusicXML's cursor; summing per NOTEHEAD is exactly the fault that made the
    old bar-sum check silently double-count every chord. That is why this
    takes an EVENT and never a head.

    ⚠️ A TUPLET SCALES THE TIME AND LEAVES THE WRITTEN VALUE ALONE, so the
    ratio is applied here exactly as it is applied to the `<duration>` written
    below: three triplet eighths occupy one quarter, not three. `_divisions`
    is an LCM for this reason, so the scaled value is a whole number of units.

    ⚠️ `max(1, ...)`, copied from the render rather than improved on: a
    `<duration>` of 0 is not legal, and the check must reason about the number
    the file WILL hold, not the one the arithmetic would prefer.
    """
    if ev.get("kind") == "rest":
        return max(1, int(round(float(ev["duration_beats"]) * divisions)))
    heads = ev.get("noteheads") or []
    if not heads:
        return 0
    beats = float(heads[0]["duration_beats"])
    tup = next((h["tuplet"] for h in heads
                if isinstance(h.get("tuplet"), dict)), None)
    if tup:
        beats = beats * int(tup.get("normal", 2)) / int(tup.get("actual", 3))
    return max(1, int(round(beats * divisions)))


def _bar_quarters(meter: Optional[Dict[str, Any]]) -> Optional[float]:
    """The bar's length in quarter notes, or None where the meter is UNKNOWN.

    ⚠️ `_legacy._measure_rest_beats` is IMPORTED rather than restated -- it is
    the function that sizes the measure rest `_mxl_empty_measure` writes, so a
    held-out bar and the length it is judged against come from one arithmetic.

    ⚠️⚠️ AND ITS 4.0 FALLBACK IS REFUSED HERE. That fallback exists so a rest
    can still be written where the meter never settled; reading it as *"this
    bar is four quarters long"* and then holding out every 2/4 bar that is not
    would be CANNOT TELL converted into a definite answer -- rule 8, and the
    one conversion this file forbids at five other sites. No meter, no
    verdict: the bar is UNASSESSABLE and is written exactly as before.
    """
    if not meter or not meter.get("numerator") or not meter.get("denominator"):
        return None
    return float(_legacy._measure_rest_beats(meter))


def _bar_holds_out(events: List[Dict[str, Any]],
                   streams: Optional[List[List[Dict[str, Any]]]],
                   divisions: int, meter: Optional[Dict[str, Any]]
                   ) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.8: the detail of a bar that does not add up, else None.

    Sean, 2026-09-23 (`docs/DECISIONS.md`): *"hold out -- I don't care about
    print right now -- I want to know what we are getting correct"*. A bar we
    could not read to its meter is a bar we could not read. Nothing here pads,
    trims or re-times it: the only outcomes are WRITE IT AS READ and HOLD IT
    OUT.

    The rule, stated once:

    * **PER VOICE, and every voice must fill.** `<backup>` returns the cursor
      to the head of the bar, so a MusicXML reader sees each voice's own
      timeline; a bar whose second voice runs out early is a bar we did not
      read. This is STRICTER than the acceptance proxy's `bar_fill.bar_total`,
      which takes the MAX over voices -- deliberately, because the strict side
      is the one that cannot let a wrong bar through the control.
    * **a chord is one event** (`_event_units`, CLAUDE.md §10).
    * **a LONE measure rest IS the bar, whatever the meter** (CLAUDE.md §10:
      a whole rest means the BAR). It is the one event that is not measured
      against the meter at all -- `<rest measure="yes"/>` carries no note
      value to compare. ⚠️ LONE: a measure rest sharing its voice with
      anything else is NOT the bar, and that voice is summed and judged like
      any other, because two events cannot both occupy the whole bar.
    * **no meter, no verdict** (`_bar_quarters`).

    ⚠️ IT NEVER LOOKS AT WHERE THE BAR IS. A pickup bar and a final bar are
    legitimately short, and NOTHING in the record marks either one -- not the
    dossier (`data/dossiers/*.json` carries `total_measures`,
    `starting_meter`, `meter_changes`, and no anacrusis field), not the works
    row, not any `Q.*`. Special-casing the first or last bar BY POSITION would
    be the exporter deciding, from arithmetic alone, that a short bar it
    cannot read is a short bar the engraver printed. So a genuine pickup is
    held out with the rest, it is named in the report like the rest, and the
    repair is a quantity that says *this bar is a pickup* -- not a rule here.
    """
    want_q = _bar_quarters(meter)
    if want_q is None:
        return None
    want = int(round(want_q * divisions))
    voices: List[Dict[str, Any]] = []
    bad = False
    for stream in (streams if streams is not None else [events]):
        lone_measure_rest = (
            len(stream) == 1
            and bool((stream[0].get("rest") or {}).get("measure_rest")))
        if lone_measure_rest:
            voices.append({"units": want, "is_the_bar": True})
            continue
        units = sum(_event_units(ev, divisions) for ev in stream)
        voices.append({"units": units, "is_the_bar": False})
        if units != want:
            bad = True
    if not bad:
        return None
    return {"want_units": want, "want_quarters": want_q,
            "divisions": divisions,
            "voices": voices,
            "quarters": [round(v["units"] / divisions, 6) for v in voices]}


def _held_bar_marks(events: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """What a held-out bar's MARKS would have written, family by family.

    ⚠️⚠️ WITHOUT THIS, ROADMAP 2.8 SILENTLY FALSIFIES FIVE OTHER CONTROLS.
    `articulation_balance`, `ornament_balance` and `wedge_balance` are
    EQUALITIES over `written + not_written`; `fermata_balance` and the arc
    residue are partitions of the same shape. A held-out bar writes none of
    its marks, so every one of them has to arrive in a NAMED bucket or the
    control goes False for correct behaviour — the *"widen it and teach it
    about a legitimate exception"* failure `wedge_balance`'s own docstring
    records this file committing once already.

    ⚠️ EACH LINE MIRRORS ITS RENDER SITE AND NOTHING ELSE. `fermatas` is per
    EVENT because `_measure_events_xml` hoists a chord's fermata onto the
    first `<note>`; `articulations` and `ornaments` are per HEAD because they
    are not spans; `ornaments` goes through `_mxl_ornament_elements` because
    the written counter counts ELEMENTS THE RENDERER CAN SPELL, not marks;
    `slurs` and `wedges` count the non-`stop` end only, exactly as the render
    does. Counting any of them by a rule of its own would be a second opinion
    about what the file would have held.
    """
    out: Dict[str, int] = collections.Counter()
    for ev in events:
        heads = ev.get("noteheads") or []
        for head in heads:
            out["articulations"] += len(head.get("articulations") or ())
            out["ornaments"] += len(
                _legacy._mxl_ornament_elements(head.get("ornaments") or []))
            if head.get("tied_to_next"):
                out["ties"] += 1
        if any(h.get("fermata") for h in heads):
            out["fermatas"] += 1
        rest = ev.get("rest") or {}
        if rest.get("fermata"):
            out["fermatas"] += 1
        for _n, kind in (ev.get("slur_states") or ()):
            if kind != "stop":
                out["slurs"] += 1
        for _n, kind in (ev.get("wedge_states") or ()):
            if kind != "stop":
                out["wedges"] += 1
    return dict(out)


def _bar_event_rows(events: Sequence[Dict[str, Any]]) -> int:
    """Log rows this bar would have written: noteheads + rests, chords flat.

    ⚠️ COUNTED OFF THE EVENTS AND NOT OFF `cell.detections`, because the
    accounting equality's other side (`counters["notes"]`, `["rests"]`,
    `["measure_rests_read"]`) is also counted off the events -- one per
    notehead and one per rest. A detection `group_chords_in_measure` does not
    turn into an event is written by nobody today, and counting it here would
    make `to_musicxml` raise for a shortfall that predates this refusal.
    """
    n = 0
    for ev in events:
        n += len(ev.get("noteheads") or ())
        if ev.get("rest"):
            n += 1
    return n


def _measure_events_xml(events: List[Dict[str, Any]], divisions: int,
                        counters: Dict[str, int], voice: int = 1,
                        doubled: bool = False
                        ) -> Tuple[List[str], int]:
    """`(lines, duration units this voice consumed)`.

    ⚠️ THE SECOND RETURN IS WHAT `<backup>` IS WRITTEN FROM, and it counts
    CHORD-LEADING notes and rests only -- a chord member past the first does
    not advance the cursor. `_mxl_voice_events` computes the identical number
    for the legacy path; getting it wrong does not produce a wrong-looking
    file, it produces a second voice offset from the first by a beat.

    ⚠️ `doubled`: ROADMAP 2.1b. True while rendering a condensed staff's
    SECOND copy (`StaffRun.condensed_from`), so every note and rest this
    call writes is one the log counted once and this file now writes twice.
    """
    out: List[str] = []
    units = 0
    for ev in events:
        if ev.get("kind") == "rest":
            out.extend(_rest_xml(ev, divisions, counters, voice=voice,
                                 doubled=doubled))
            # ⚠️ ROADMAP 2.8. `_event_units` rather than the arithmetic
            # inline: the bar-sum hold-out reasons about this same number, and
            # a second spelling of it would be a rule nothing forces to agree
            # with the file it is judging.
            units += _event_units(ev, divisions)
            continue
        heads = ev.get("noteheads") or []
        tup = next((h["tuplet"] for h in heads
                    if isinstance(h.get("tuplet"), dict)), None)
        # ⚠️ HOISTED TO THE EVENT, UNLIKE AN ARTICULATION. One fermata hangs
        # over a whole chord, so it goes on the chord's FIRST `<note>` --
        # MusicXML's representative for anything spanning the chord, the same
        # place the slur and tie marks go. Each member wearing its own would
        # write three pause signs where the page prints one. `any` and not
        # "the first head that carries it": `adjudicate_fermata_owner` names
        # ONE carrier and a chord's members share an x, so which member it
        # named is an artefact of glyph order and must not decide anything.
        ev_fermata = any(h.get("fermata") for h in heads)
        # ⚠️⚠️ A HAIRPIN OPENS BEFORE THE NOTE IT COVERS AND CLOSES AFTER IT,
        # and that element ORDER is the pairing rather than a style: music21
        # attaches a `crescendo` to the next note it PARSES and a `stop` to
        # the last note it parsed, so writing both on one side of the note
        # would silently change which notes the wedge spans. The legacy
        # `_mxl_voice_events` splits them the same way for the same reason.
        for _number, _kind in (ev.get("wedge_states") or ()):
            if _kind != "stop":
                out.append(_legacy._mxl_wedge(_number, _kind, "      "))
                # ⚠️ COUNTED HERE, AT THE RENDER, where the ELEMENT is
                # written -- the `FAMILIES` rule, and the one the arc export
                # learned by reporting 55 slurs into a file holding 23. A mark
                # SET on a notehead that `voicing` then drops is attached and
                # not written; only this site can tell.
                counters["wedges"] += 1
        for n, head in enumerate(heads):
            # ⚠️ LOWEST NOTE FIRST — `group_chords_in_measure` already sorts
            # the group that way and the order is load-bearing: MusicXML takes
            # a chord's FIRST `<note>` as its representative, so ties, beams
            # and slurs all hang off it. Written bottom-up is how a chord is
            # read.
            beats = float(head["duration_beats"])
            time_mod = None
            state = None
            if tup:
                # ⚠️ A TUPLET SCALES THE TIME AND LEAVES THE WRITTEN VALUE
                # ALONE. `<type>` stays the printed note value; the ratio goes
                # in `<time-modification>`, which is why `divisions` has to be
                # an LCM.
                time_mod = {"actual": int(tup.get("actual", 3)),
                            "normal": int(tup.get("normal", 2))}
                beats = beats * time_mod["normal"] / time_mod["actual"]
                counters["tuplet_notes"] += 1
            _lily, xml_type, dots = _legacy._duration_to_lily_xml(
                head["duration_type"], int(head.get("dots") or 0))
            out.append(_legacy._mxl_note(
                head["pitch"], "", xml_type, dots, beats, divisions,
                is_chord=(n > 0), is_rest=False, indent="      ",
                voice=voice,
                time_modification=time_mod, tuplet_state=state,
                # ⚠️ ON THE CHORD'S FIRST NOTE ONLY, which is the same rule
                # `_mxl_voice_events` follows: MusicXML takes a chord's first
                # `<note>` as its representative, so a span hung off every
                # member would open one slur per notehead and close none of
                # them. `group_chords_in_measure` has already sorted the group
                # LOWEST FIRST and carried the marks up onto the EVENT, which
                # is why they are read from `ev` here and not from `head`.
                slur_states=(ev.get("slur_states") if n == 0 else None),
                # ⚠️ THE BEAM IS PER EVENT AND GOES ON THE CHORD'S FIRST NOTE,
                # exactly as the slur does and for the same reason -- the
                # legacy renderer writes `beam_states if ni == 0 else None` at
                # its own call site. A `<beam>` on every member of a chord
                # draws one beam per notehead.
                beam_states=(ev.get("beam_states") if n == 0 else None),
                # ⚠️⚠️ ...BUT THE TIE IS PER HEAD, AND IS THE ONE SPANNER MARK
                # THAT IS. `<slur>` carries a `number=` and hangs off the
                # chord's representative note; `<tied>` carries none and joins
                # THE TWO NOTES IT NAMES, which is why `_pair_arcs` calls this
                # "the one place a tie and a slur are genuinely different
                # spanners". Reading `ev` and writing at `n == 0` put the mark
                # on the chord's LOWEST note whenever an upper member was the
                # tied one. See `benchmarks/omr-chord-tie-2026-09/FINDINGS.md`.
                tied_to_next=bool(head.get("tied_to_next")),
                tied_from_prev=bool(head.get("tied_from_prev")),
                # ⚠️ PER HEAD, NOT PER EVENT -- unlike the slur and tie marks
                # just above, which sit on the chord's FIRST note because
                # MusicXML takes that note as the chord's representative for a
                # SPAN. An articulation is not a span: each member of a chord
                # wears its own staccato, and hoisting them onto the first
                # would write one dot where the page prints three.
                articulations=(head.get("articulations") or None),
                # ⚠️ PER HEAD, like the articulations and unlike the fermata:
                # a trill is played on a NOTE, so a chord can carry one on any
                # subset of its members.
                ornaments=(head.get("ornaments") or None),
                fermata=(ev_fermata if n == 0 else False),
                # ⚠️⚠️ NO `accidental=`, AND THE ABSENCE IS AN ABSTENTION WE
                # COUNT RATHER THAN A FIELD WE FORGOT. `<accidental>` is the
                # glyph the engraver PRINTED, and the record holds no reading
                # of one: the in-bar accidental is filed as an anonymous
                # `Q.GLYPH_BOX` and reaches no quantity (`gather_coverage`'s
                # `FAMILY_Q_IS_ELSEWHERE["accidental"]` says so in terms --
                # 256 such glyphs detected on Litolff pp.1-4 and not one of
                # them becomes a verdict). The only thing that WAS being
                # passed here was the key-derived alteration, which is now in
                # the pitch where it belongs. Emitting nothing is the honest
                # answer; `printed_accidentals_not_read` is the count.
                ))
            counters["notes"] += 1
            if doubled:
                # ⚠️ ROADMAP 2.1b. Subtracted back out of `written` in
                # `to_musicxml`'s balance, the same shape as `rests_
                # duplicated_across_voices` two paragraphs down in that
                # function -- a note the log counted ONCE that this file
                # legitimately writes twice must not read as ink from
                # nowhere.
                counters["notes_doubled_to_condensed_slot"] += 1
            # ⚠️ COUNTED AT THE RENDER, where the ELEMENT is written, and not
            # where the mark was ATTACHED. The two numbers are different: a
            # mark attached to a notehead that `_place_notes` then dropped is
            # attached and not written, and a counter at the attach would
            # report the first while claiming the second. The arc export
            # learned this by reporting 55 slurs into a file holding 23.
            counters["articulations"] += len(head.get("articulations") or ())
            # ⚠️ COUNTED AT THE RENDER, where the ELEMENT is written, and only
            # for the kinds `_mxl_ornament_elements` can spell -- the counter
            # says what reached the FILE, which is the `FAMILIES` rule.
            counters["ornaments"] += len(
                _legacy._mxl_ornament_elements(head.get("ornaments") or []))
            if n == 0:
                # ⚠️ COUNTED AT THE RENDER, where the ELEMENT is written, and
                # ONCE PER EVENT rather than once per mark. Two fermatas
                # decided onto two members of one chord produce ONE
                # `<fermata>`, and a counter at the attach site would claim
                # two. That gap is what `fermata_balance` reports.
                if ev_fermata:
                    counters["fermatas"] += 1
                # ⚠️⚠️ COUNTED HERE, AT THE RENDER, AND NOT WHERE THE MARK WAS
                # SET -- because the two numbers are DIFFERENT and the first
                # cut reported the wrong one. `voicing._chord_span_states`
                # DROPS a span whose start and stop landed in the SAME chord
                # ("a slur from a note to itself is a curve to nowhere"), and
                # `_paired_spans` cannot catch those: it refuses two ends on
                # one DETECTION, while a chord is several detections at one x.
                # On one real page that is 32 of 55 marked spans, so the
                # report claimed 55 slurs where 23 reached the file.
                #
                # This is the rule the FAMILIES table already states one
                # screen down: "only the counter says what reached the FILE".
                for _num, kind in (ev.get("slur_states") or ()):
                    if kind != "stop":
                        counters["slurs"] += 1
            # ⚠️⚠️ OUTSIDE `if n == 0`, AND THAT IS THE FIX RATHER THAN A
            # TIDY-UP. A TIE IS NOT A SPAN. `<slur>` carries a `number=` and
            # hangs off the chord's representative `<note>`; `<tied>` carries
            # none and joins THE TWO NOTES IT NAMES — `_pair_arcs` calls this
            # "the one place a tie and a slur are genuinely different
            # spanners". `voicing.group_chords_in_measure` hoists the flag
            # onto the EVENT with `any()`, and reading THAT here wrote the
            # mark at the chord's LOWEST note whenever an upper member was the
            # tied one: 17 of 48 written ties on Litolff `984073` p1-3 and 103
            # of 349 on Breitkopf Brahms 1 p0-3, two publishers agreeing to
            # within six points. Repaired 2026-09-11 and priced on both
            # families — `benchmarks/omr-chord-tie-2026-09/FINDINGS.md`.
            #
            # ⚠️ COUNTED AT THE RENDER, once per WRITTEN `<tie type="start">`,
            # which is now once per tied HEAD and no longer once per event.
            # That is the `FAMILIES` rule — only the counter says what reached
            # the FILE — and it is why the number can legitimately exceed the
            # old one on a chord with two tied members.
            if head.get("tied_to_next"):
                counters["ties"] += 1
            # ⚠️ THE DEFECT'S OWN COUNTERS ARE REPLACED RATHER THAN KEPT AT
            # ZERO. `tie_starts_written_on_an_untied_note` counted an element
            # the exporter wrote; after the repair no such element exists, so
            # keeping the name would be a counter that reports something the
            # file does not contain — the "control that computes the wrong
            # thing" family this repo has already recorded four times. What
            # replaces it is a POSITIVE figure about the file: a tie written
            # on a chord member that is NOT the first note, which is exactly
            # the population the old hoist misplaced and is impossible to
            # write at all under the old rule.
            if n > 0:
                for key, name in (("tied_to_next", "tie_starts"),
                                  ("tied_from_prev", "tie_stops")):
                    if head.get(key):
                        counters[name + "_on_an_upper_chord_note"] += 1
            # ⚠️ RENAMED, NOT PINNED AT ZERO. The old `accidentals` counted
            # `<accidental>` elements; after this repair the exporter writes
            # none, so a counter still carrying that name would report an
            # element the file does not contain -- the "control that computes
            # the wrong thing" family, which this file already records the
            # chord-tie work hitting. What replaces it is a POSITIVE figure
            # about the file: notes whose PITCH the key signature altered.
            if head.get("key_alteration"):
                counters["pitches_altered_by_the_key"] += 1
            # ⚠️ COUNTED AT THE RENDER, where the ELEMENT is written, and not
            # where `annotate_beams` attached it -- the rule the arc export
            # learned by reporting 55 slurs into a file holding 23. The two
            # figures differ whenever an event is dropped between the two.
            if n == 0:
                counters["beams"] += len(ev.get("beam_states") or ())
                if ev.get("beam_states"):
                    counters["beamed_events"] += 1
            if n == 0:
                # ⚠️ ROADMAP 2.8, and the same reason as the rest branch: ONE
                # copy of the arithmetic, shared with the bar-sum hold-out.
                units += _event_units(ev, divisions)
        # ⚠️ AFTER the chord's notes, for the reason above: the `stop` binds
        # to the last note music21 parsed, which is this event.
        for _number, _kind in (ev.get("wedge_states") or ()):
            if _kind == "stop":
                out.append(_legacy._mxl_wedge(_number, _kind, "      "))
    return out, units


def _rest_xml(ev: Dict[str, Any], divisions: int,
              counters: Dict[str, int], voice: int = 1,
              doubled: bool = False) -> List[str]:
    """One `<rest>`, and the one place the BAR convention is written out.

    ⚠️ `measure="yes"` CARRIES NO `<type>`, and the two go together. The glyph
    stands for the bar, so there is no note value to name -- `_mxl_note`
    already refuses to write `<type>` when `measure_rest` is set, which is why
    this passes the flag rather than choosing a type of its own.

    ⚠️ `doubled`: ROADMAP 2.1b, the same fact `_measure_events_xml` passes in
    for a note -- this rest is the condensed staff's SECOND copy.
    """
    det = ev.get("rest") or {}
    measure_rest = bool(det.get("measure_rest"))
    beats = float(ev["duration_beats"])
    if measure_rest:
        counters["measure_rests_read"] += 1
        xml_type, dots = "whole", 0
    else:
        counters["rests"] += 1
        _lily, xml_type, dots = _legacy._duration_to_lily_xml(
            ev.get("duration_type") or "quarter", int(ev.get("dots") or 0))
    if doubled:
        counters["notes_doubled_to_condensed_slot"] += 1
    # ⚠️ A REST CARRIES A FERMATA AND AN ARTICULATION DOES NOT, which is why
    # `_mxl_note` keeps `<fermata>` outside the `<articulations>` block. On a
    # conductor's page the whole-bar rest is the COMMONEST carrier of a pause.
    fermata = bool(det.get("fermata"))
    if fermata:
        counters["fermatas"] += 1
    return [_legacy._mxl_note(
        None, "", xml_type, dots, beats, divisions, is_chord=False,
        is_rest=True, indent="      ", voice=voice,
        measure_rest=measure_rest,
        fermata=fermata)]


def to_musicxml(result: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """The file, and the record of what did not reach it."""
    rec = Record(result)
    (parts, provenance, dropped, arcs_dropped, artics_dropped,
     fermatas_dropped, ornaments_dropped,
     notes_dropped_by_system) = build(rec)
    divisions = _divisions(parts)
    counters: Dict[str, int] = collections.Counter()
    # ⚠️⚠️ ROADMAP 2.8. `build` refuses a note it cannot PLACE; this refuses a
    # note whose BAR does not add up, and a bar is only known to be a bar once
    # the meter in force at it is known — which is `_part_xml`'s own per-bar
    # read of `Q.METER`'s segments. So the refusal is filed from the render,
    # through the same two counters `_place_notes._drop` writes, and the
    # equality between them is asserted again below after every part is
    # rendered. `dropped` arrives from `build` as a plain dict; a Counter is
    # what lets `+=` on a new key work at all.
    dropped = collections.Counter(dropped)

    def _drop_at_render(reason: str, page: int, system: int) -> None:
        dropped[reason] += 1
        notes_dropped_by_system.setdefault(
            (page, system), collections.Counter())[reason] += 1

    #: Every bar 2.8 held out, named by (page, system, staff, cell) — the
    #: roadmap's own requirement, and the only place a human can find out
    #: WHICH bars the file is missing without re-deriving the rule.
    held_bars: List[Dict[str, Any]] = []
    #: The MARKS a held-out bar would have written, by family. See
    #: `_held_bar_marks`: every one of them has to reach its family's own
    #: not-written bucket or that family's balance control goes False for
    #: correct behaviour.
    held_marks: Dict[str, int] = collections.Counter()
    # ⚠️ AFTER the parts are joined and BEFORE any measure is rendered. A part
    # is what an arc is merged along -- the junction between two systems is a
    # junction of one PART, not of two staves -- so this cannot run inside
    # `build`'s per-staff loop, and it must not run after `_part_xml`, which is
    # where the marks are read.
    # ⚠️ `+=`, not `update`. A Counter's `update` ADDS and a dict's REPLACES,
    # and the two spellings are one character apart -- an arc counted in both
    # halves would be silently overwritten rather than summed.
    arcs_dropped += collections.Counter(_pair_arcs(rec, parts, counters))
    # ⚠️ A PART PASS TOO, and for the `number=` half of the same reason: two
    # hairpins overlapping in one part need two levels, which no per-measure
    # pass can see. Unlike the arcs it needs no merge -- see `_place_wedges`.
    wedges_dropped = collections.Counter(_place_wedges(rec, parts, counters))

    # ⚠️ BEFORE any measure is rendered and AFTER the join, because the number
    # line is a fact about the DOCUMENT's systems while what gets written on it
    # is a fact about a PART — and only the join says which runs are one part.
    offsets, numbering = _document_bar_offsets(parts)
    # ⚠️ BOTH DERIVED FROM THAT ONE TALLY, never re-counted. `spans` is the
    # document's systems in order with each one's own bar count — the tacet
    # padding's whole input — and reading it off `numbering["systems"]` is what
    # keeps a padded span and the number written on it answering to the same
    # arithmetic. When the numbering REFUSED there is no bar sequence to pad
    # into, so `spans` is None and `_tacet_walk` falls back to the part's runs.
    spans: Optional[List[Tuple[Tuple[int, int], int]]] = (
        None if offsets is None else _spans_from_numbering(numbering))
    # ⚠️ THE METER OF A SYSTEM THIS PART IS NOT ON, taken off the runs that ARE
    # on it. `Q.METER` is scoped to `system/<page>/<system>`, so every run of a
    # system carries the same object and there is no second read of the record
    # here — a tacet bar is sized by exactly the meter a present part's
    # eventless bar on that system is sized by.
    meters: Dict[Tuple[int, int], Any] = {}
    for _p in parts:
        for _r in _p:
            meters[(_r.page, _r.system)] = _r.meter
    # ⚠️ WRITTEN EVEN WHEN ZERO. A `Counter` holds only the keys something
    # touched, so a document with no tacet part would report neither figure at
    # all and *"nothing needed padding"* would read exactly like *"this was
    # never computed"* — the `empty_bars_padded_without_meter` lesson, in the
    # branch next door.
    # ⚠️ OFF THE JOIN'S OWN PROVENANCE, not recomputed: `build` knows which
    # runs had no `Q.SLOT_INDEX` and a second derivation here would be a
    # fifth copy of a rule this session spent the day deleting copies of.
    unnamed_parts = set(provenance.get("unidentified_parts") or ())
    counters["tacet_bars_padded"] += 0
    counters["tacet_bars_not_padded_without_meter"] += 0
    # ⚠️ WRITTEN EVEN WHEN ZERO, same reason as the two above: a document
    # whose join named every staff must report *"declined none"* rather than
    # reporting nothing, or *"nothing was declined"* reads exactly like
    # *"this was never computed"*.
    counters["tacet_spans_declined_unidentified_part"] += 0

    part_list: List[str] = []
    parts_xml: List[str] = []
    for i, part in enumerate(parts):
        pid = f"P{i + 1}"
        name = next((r.name for r in part if r.name), None) or _default_name(part)
        part_list.append(
            f'    <score-part id="{pid}">\n'
            f'      <part-name>{_legacy._xml_escape(name)}</part-name>\n'
            f'    </score-part>')
        # ⚠️⚠️ A FRAGMENT IS NOT PADDED, AND THAT IS THE WHOLE OF THIS FIX.
        # Padding a part the join could not identify asserts *"this
        # instrument is silent on that system"*; what we know is *"we could
        # not identify this staff"*. Converting the second into the first is
        # the CANNOT-TELL-into-a-definite-answer failure this file forbids at
        # four other sites -- and composed with the 2026-09-15 join it put 25
        # blank staves under every printed system, so the first system of the
        # cleanup artefact showed 37 staves against the print's 12 and a human
        # could not count it. ⚠️ Each repair was measured ALONE and neither in
        # the presence of the other: when the padding landed it reached ZERO
        # bars on this document, because the meter was not yet carried.
        pad = spans if i not in unnamed_parts else None
        if i in unnamed_parts:
            counters["tacet_spans_declined_unidentified_part"] += 1
        parts_xml.append(_part_xml(rec, part, pid, divisions, counters,
                                   offsets, pad, meters,
                                   drops=_drop_at_render,
                                   held_bars=held_bars, marks=held_marks))

    # ⚠️ WRITTEN EVEN WHEN ZERO, the `empty_bars_padded_without_meter` lesson
    # again: on a document where every bar adds up, *"we held out none"* must
    # not read like *"this figure was never computed"*.
    for _k in ("bars_with_events", "bars_with_events_without_a_meter",
               "bars_held_out_sum", "notes_held_out_sum",
               "bars_judged_by_a_carried_meter",
               "empty_bars_sized_by_a_carried_meter",
               "bars_held_out_sum_on_a_doubled_staff"):
        counters[_k] += 0

    xml = _legacy._score_partwise(result.get("source", {}) or {},
                                  part_list, parts_xml)
    report = coverage(result, written=dict(counters))
    report["written"] = dict(counters)
    report["written"]["parts"] = len(parts)
    report["written"]["divisions"] = divisions
    report["part_join"] = provenance
    # ⚠️ REPORTED WHETHER OR NOT IT FIRED, and the `refused` key is the whole
    # point rather than an afterthought. *"we numbered the document"* and
    # *"this figure was never computed"* must not read alike — the same lesson
    # `empty_bars_padded_without_meter` was fixed for, in the numbering path.
    report["measure_numbering"] = numbering
    # ⚠️ REPORTED WHETHER OR NOT IT FIRED, and the `refused` key carries the
    # reason rather than leaving a zero to be read as a success. A tacet span
    # is a bar the page prints for no staff of this part; `tacet_bar_total` is
    # how many exist, `bars_padded` how many we could size, and the difference
    # is bars this file still does not hold — which is a METER shortfall, not
    # a padding one, and the report must say so or the next reader will come
    # back to this function.
    report["tacet_padding"] = _tacet_report(parts, offsets, spans, counters)
    # ⚠️ A NOTE THE RECORD HOLDS AND THE FILE DOES NOT. Reported beside the
    # families for the same reason: a shortfall that is not counted is
    # indistinguishable from ink that was never read.
    report["notes_not_written"] = dict(dropped)
    report["notes_not_written_total"] = sum(dropped.values())
    # ⚠️⚠️ ROADMAP 2.8, AND THE EQUALITY `build` ASSERTS IS ASSERTED AGAIN
    # HERE BECAUSE A SECOND CALL SITE NOW EXISTS. `build`'s own check ran
    # before any bar was rendered, so it cannot see `_drop_at_render`; without
    # this line a refusal that reached the flat total and missed the
    # per-system one would be invisible until the cleanup artefact
    # disagreed with the report — which is exactly how `build_sheet.py`'s copy
    # went stale for six days.
    _by_sys_total = sum(sum(c.values())
                        for c in notes_dropped_by_system.values())
    if _by_sys_total != sum(dropped.values()):
        raise Unbalanced(
            "notes refused per system (%d) do not sum to the per-reason total "
            "(%d) after rendering -- a refusal reaches one counter and not "
            "the other" % (_by_sys_total, sum(dropped.values())))
    # ⚠️⚠️ ROADMAP 2.8: EVERY HELD BAR BY NAME. The roadmap asks for (page,
    # system, cell, staff) and this carries the measure number and part id
    # too, because the file a human opens is numbered by the DOCUMENT's bar
    # sequence and a coordinate alone cannot be found in it.
    #
    # ⚠️ A LIST AND NOT A COUNT, deliberately: a count says how much was lost
    # and can only be argued about, while the list says WHERE and can be
    # opened against the plate. On the Litolff whole movement it is a few
    # thousand rows, which is the honest size of the fact.
    report["bars_held_out_sum"] = {
        "bars": int(counters.get("bars_held_out_sum", 0)),
        "bars_on_a_doubled_staff": int(
            counters.get("bars_held_out_sum_on_a_doubled_staff", 0)),
        "of_bars_with_events": int(counters.get("bars_with_events", 0)),
        "bars_with_events_without_a_meter": int(
            counters.get("bars_with_events_without_a_meter", 0)),
        "bars_judged_by_a_carried_meter": int(
            counters.get("bars_judged_by_a_carried_meter", 0)),
        "fraction": ((counters.get("bars_held_out_sum", 0)
                      / counters["bars_with_events"])
                     if counters.get("bars_with_events") else None),
        "noteheads_and_rests": int(counters.get("notes_held_out_sum", 0)),
        "held": held_bars,
    }
    # ⚠️ THE SAME REFUSALS, KEYED BY PRINTED SYSTEM. Written so the cleanup
    # artefact can ask its question one system at a time without holding a
    # second copy of the rule -- which is how `build_sheet.py`'s own
    # decomposition came to be three repairs out of date. `build()` asserts
    # these sum to the flat total.
    report["notes_not_written_by_system"] = {
        f"{p}/{s}": dict(c)
        for (p, s), c in sorted(notes_dropped_by_system.items())}
    # ⚠️ REPORTED APART FROM THE NOTES, and deliberately NOT inside the
    # balance below: an arc is not a note, and a control that counts two
    # different families on one side of an equation cannot say which one it
    # lost. This is the `detected_and_unrepresented` / `decided_and_unwritten`
    # split, arriving one family further down.
    # ⚠️ THE GAP BETWEEN MARKED AND WRITTEN IS ITSELF A DROP, and naming it
    # is what keeps `arcs_not_written` a partition rather than a sample. A
    # span both of whose ends land in one chord is discarded by
    # `voicing._chord_span_states`, correctly and silently, two modules away
    # from anything that knows an arc was involved.
    # ⚠️⚠️ ROADMAP 2.8 IS SUBTRACTED OUT OF `lost` BEFORE IT IS NAMED, and
    # that is the whole reason this loop changed. `lost` is a DIFFERENCE, so a
    # slur the bar-sum hold-out refused would otherwise be filed under
    # `arc_ends_in_one_chord` — a real bucket, a real number, and the wrong
    # cause — and the next reader would go looking at `voicing.
    # _chord_span_states` for an arc that was never near a chord. Naming it
    # here keeps `arcs_not_written` a partition AND keeps each bucket's name
    # true.
    for fam, mark in (("slurs", "slur_spans_marked"),
                      ("ties", "tie_spans_marked")):
        held = int(held_marks.get(fam, 0))
        if held:
            arcs_dropped[_BAR_SUM_REFUSAL] += held
        lost = int(counters.get(mark, 0)) - int(counters.get(fam, 0)) - held
        if lost > 0:
            arcs_dropped["arc_ends_in_one_chord"] += lost
    report["arcs_not_written"] = dict(arcs_dropped)
    report["arcs_not_written_total"] = sum(arcs_dropped.values())
    # ⚠️ A THIRD PARTITION, AND IT IS ASSERTED RATHER THAN HOPED FOR. Every
    # gathered articulation mark is either written onto a note or counted here
    # -- the same control the notes get, on a family whose whole population is
    # small enough that one silent loss would be a large share of it.
    # ⚠️ ROADMAP 2.8: the marks a held-out bar would have written reach
    # this family's own bucket, or its balance control goes False for
    # correct behaviour. See `_held_bar_marks`.
    if held_marks.get("articulations"):
        artics_dropped = collections.Counter(artics_dropped)
        artics_dropped[_BAR_SUM_REFUSAL] += held_marks["articulations"]
    report["articulations_not_written"] = dict(artics_dropped)
    report["articulations_not_written_total"] = sum(artics_dropped.values())
    marks_in_log = len(rec.obs_of(Q.ARTICULATION_MARK))
    report["articulation_balance"] = {
        "marks_in_log": marks_in_log,
        "written": int(counters.get("articulations", 0)),
        "not_written": report["articulations_not_written_total"],
        "balanced": marks_in_log == (int(counters.get("articulations", 0))
                                     + report["articulations_not_written_total"]),
    }
    # ⚠️ THE FERMATA BALANCE IS A PARTITION AND DELIBERATELY NOT AN EQUALITY,
    # which is the one place it differs from the articulation control above. A
    # fermata is HOISTED to its chord's first note, so two marks decided onto
    # two members of one chord write ONE `<fermata>` -- `written + not_written`
    # is then legitimately SHORT of `marks_in_log`, and an equality control
    # would report an instrument defect for correct behaviour. What is
    # asserted instead is that nothing goes missing UNACCOUNTED: every mark is
    # written, counted as not-written, or absorbed into an element another mark
    # on the same event already wrote.
    # ⚠️ PER HEAD, so this IS an equality -- unlike the fermata control one
    # paragraph down, where the hoist collapses several marks into one element.
    # ⚠️ ROADMAP 2.8: the marks a held-out bar would have written reach
    # this family's own bucket, or its balance control goes False for
    # correct behaviour. See `_held_bar_marks`.
    if held_marks.get("ornaments"):
        ornaments_dropped = collections.Counter(ornaments_dropped)
        ornaments_dropped[_BAR_SUM_REFUSAL] += held_marks["ornaments"]
    report["ornaments_not_written"] = dict(ornaments_dropped)
    report["ornaments_not_written_total"] = sum(ornaments_dropped.values())
    orn_marks = len(rec.obs_of(Q.ORNAMENT_MARK))
    report["ornament_balance"] = {
        "marks_in_log": orn_marks,
        "written": int(counters.get("ornaments", 0)),
        "not_written": report["ornaments_not_written_total"],
        "balanced": orn_marks == (int(counters.get("ornaments", 0))
                                  + report["ornaments_not_written_total"]),
    }
    # ⚠️ THE WEDGE CONTROL IS A PARTITION OF THE HAIRPIN ROWS, NOT AN
    # EQUALITY OF WRITTEN-PLUS-DROPPED, and the difference is the ABSTENTIONS.
    # Unlike an ornament, most of this family never reaches `_place_wedges` at
    # all: `adjudicate_wedge_anchor` abstains `no_anchor` on a staff whose
    # notes the detector missed and `no_page_frame` on the detector's own
    # box-less row. Those are decisions, not export drops, and folding them
    # into `not_written` would report a reading limit as an exporter gap --
    # the exact confusion `coverage()`'s two headlines exist to keep apart.
    wedge_rows = len(rec.obs_of(Q.WEDGE_BOX))
    w_decided = len([v for v in rec.verdicts_of(Q.WEDGE_ANCHOR)
                     if v["outcome"] == "decided"])
    # ⚠️ ROADMAP 2.8: the marks a held-out bar would have written reach
    # this family's own bucket, or its balance control goes False for
    # correct behaviour. See `_held_bar_marks`.
    if held_marks.get("wedges"):
        wedges_dropped = collections.Counter(wedges_dropped)
        wedges_dropped[_BAR_SUM_REFUSAL] += held_marks["wedges"]
    report["wedges_not_written"] = dict(wedges_dropped)
    report["wedges_not_written_total"] = sum(wedges_dropped.values())
    report["wedge_balance"] = {
        "rows_in_log": wedge_rows,
        "decided": w_decided,
        "abstained": wedge_rows - w_decided,
        "written": int(counters.get("wedges", 0)),
        "not_written": report["wedges_not_written_total"],
        # ⚠️⚠️ AN EQUALITY, AND IT WAS A `<=` FOR ONE AFTERNOON. Written as an
        # inequality with a named `absorbed_by_a_shared_event` residue, it
        # reported `balanced: True` while TEN decided hairpins on the Brahms
        # record were accounted for NOWHERE — a per-part head index made "not
        # in this part" and "never written" indistinguishable, so a hairpin
        # with both ends unwritten was skipped by every part and counted by
        # none. **The `<=` is what let it pass.** The fermata control needs an
        # inequality because its hoist genuinely collapses several marks into
        # one element; nothing collapses here, one hairpin is one decision, so
        # every decided hairpin is written or counted and the control says so.
        # The wider lesson is this file's own: the cheapest way to make a
        # control unable to fail is to widen it while teaching it about a
        # legitimate-sounding exception.
        "balanced": (int(counters.get("wedges", 0))
                     + report["wedges_not_written_total"]) == w_decided,
    }
    # ⚠️⚠️ THE DIRECTION CONTROL IS AN EXACT EQUALITY AND ITS RESIDUE HAS A
    # NAME. The session before last warned in writing that a `<=` balance
    # cannot fail; the session after it read that warning and still shipped a
    # `<=`, which reported `balanced: True` while ten decided hairpins were
    # counted by nobody. So this is `==`, and the gap between the words a
    # verdict DECIDED and the words the FILE holds is a counted bucket rather
    # than slack in an inequality.
    #
    # ⚠️ The only way a decided word can fail to be written is that its cell
    # is not in the export at all -- its staff belongs to no part, or its
    # index is past the run's `n_measures`. That is a PART-JOIN fact, not a
    # direction fact, and naming it here is what stops it being read as one.
    d_decided = 0
    for v in rec.verdicts_of(Q.DIRECTION):
        if v["outcome"] != "decided":
            continue
        d_decided += len(v["value"] or ())
    d_placed = 0
    for _part in parts:
        for _run in _part:
            for _cell in _run.cells.values():
                d_placed += sum(1 for _x, _kind, _t in _cell.directions
                                if _kind == "words")
    d_written = int(counters.get("direction_words", 0))
    report["direction_words_not_written"] = {
        # ⚠️ TWO DIFFERENT LOSSES, REPORTED APART, because the repairs differ.
        # The first is a verdict whose cell no part carries; the second would
        # be a word placed on a cell the renderer never emitted.
        "cell_not_in_any_part": d_decided - d_placed,
        "placed_but_not_rendered": d_placed - d_written,
    }
    report["direction_words_not_written_total"] = d_decided - d_written
    report["direction_balance"] = {
        "words_decided": d_decided,
        "placed": d_placed,
        "written": d_written,
        "not_written": report["direction_words_not_written_total"],
        # ⚠️ A KNOWN EQUIVALENT MUTANT, named rather than chased: as written,
        # `written + not_written` is `d_decided` by construction, so `==` and
        # `<=` agree on every input this code can produce today. The `==` is
        # the guard against a future emission path that drops a word silently
        # -- exactly what the `<=` failed to catch for the wedges -- and the
        # two RESIDUE buckets above are what actually go red, because they are
        # differences rather than a sum.
        "balanced": (d_written + report["direction_words_not_written_total"]
                     == d_decided),
    }
    fermata_marks = len(rec.obs_of(Q.FERMATA_MARK))
    # ⚠️ ROADMAP 2.8: the marks a held-out bar would have written reach
    # this family's own bucket, or its balance control goes False for
    # correct behaviour. See `_held_bar_marks`.
    if held_marks.get("fermatas"):
        fermatas_dropped = collections.Counter(fermatas_dropped)
        fermatas_dropped[_BAR_SUM_REFUSAL] += held_marks["fermatas"]
    report["fermatas_not_written"] = dict(fermatas_dropped)
    report["fermatas_not_written_total"] = sum(fermatas_dropped.values())
    f_written = int(counters.get("fermatas", 0))
    f_dup = int(counters.get("fermatas_duplicated_across_voices", 0))
    f_elements = f_written - f_dup        # ...one per MARK, not per element
    report["fermata_balance"] = {
        "marks_in_log": fermata_marks,
        "written": f_written,
        "duplicated_across_voices": f_dup,
        "not_written": report["fermatas_not_written_total"],
        "absorbed_by_a_shared_event": (
            fermata_marks - f_elements - report["fermatas_not_written_total"]),
        "balanced": (f_elements + report["fermatas_not_written_total"]
                     <= fermata_marks),
    }
    # ⚠️⚠️ THE ACCOUNTING CONTROL, AND IT IS READ. Every notehead the log
    # holds is either written or counted as not-written; the two must sum to
    # the `notehead_class` rows exactly. An unbalanced export is an
    # INSTRUMENT DEFECT and nothing downstream may quote a figure from it.
    #
    # This is the lesson of `symbol_ledger.coverage_check`, which computed
    # exactly this control, wrote it into its summary, reported
    # `balanced=False` on 9 of 20 rows and WAS READ BY NOTHING for as long as
    # it existed. So `to_musicxml` raises rather than returning an unbalanced
    # report: a control nobody consults is not a control.
    events_in_log = (len(rec.obs_of(Q.NOTEHEAD_CLASS)) + len(rec.obs_of(Q.REST)))
    # ⚠️ A REST IN A TWO-VOICE BAR IS WRITTEN ONCE PER VOICE, and subtracting
    # the duplicate is what keeps this an EQUALITY rather than an inequality
    # that can no longer fail. The convention is the engraving's — each voice
    # needs its own bar to sum — and `Q.VOICES` names it in
    # `rests_in_every_voice` rather than leaving the exporter to discover it.
    duplicated = int(counters.get("rests_duplicated_across_voices", 0))
    # ⚠️⚠️ ROADMAP 2.1b. A note or rest the log counted ONCE is written
    # TWICE onto a condensed staff's doubled Contrabass copy
    # (`_condensed_double`) — subtracted here for exactly the reason
    # `duplicated` is: the equality must stay an equality, never widen to
    # `<=`, and the residue must be NAMED rather than absorbed. See
    # `docs/DECISIONS.md` 2026-09-22 and CLAUDE.md's own rule that a note
    # written twice needs a named bucket, not a weaker control.
    doubled_to_condensed = int(
        counters.get("notes_doubled_to_condensed_slot", 0))
    written = (int(counters["notes"]) + int(counters["rests"])
               + int(counters["measure_rests_read"]) - duplicated
               - doubled_to_condensed)
    report["balance"] = {
        # ⚠️ RESTS ARE IN THE CONTROL NOW. They were outside it while they had
        # no quantity, which is exactly how 838 glyphs stayed invisible: a
        # balance that does not count a family cannot be unbalanced by losing
        # one.
        "events_in_log": events_in_log,
        "noteheads_in_log": len(rec.obs_of(Q.NOTEHEAD_CLASS)),
        "rests_in_log": len(rec.obs_of(Q.REST)),
        "events_written": written,
        "rests_duplicated_across_voices": duplicated,
        "notes_doubled_to_condensed_slot": doubled_to_condensed,
        "events_not_written": report["notes_not_written_total"],
        "balanced": events_in_log == written + report["notes_not_written_total"],
    }
    if not report["balance"]["balanced"]:
        raise Unbalanced(
            f"{events_in_log} noteheads+rests in the log, {written} written "
            f"and {report['notes_not_written_total']} accounted as dropped — "
            f"the difference went nowhere. {report['notes_not_written']}")
    return xml, report


def _default_name(part: Sequence[StaffRun]) -> str:
    """⚠️ A COORDINATE, NOT A GUESS. A staff whose instrument abstained keeps
    the old coordinate form rather than being named from its position — the
    same rule `contextual` follows, and the reason `--no-contextual` output is
    unchanged."""
    r = part[0]
    return f"Staff p{r.page}-s{r.system}-{r.staff}"


# ─────────────────────────────────────────────────────────────────────────────
# The coverage record
# ─────────────────────────────────────────────────────────────────────────────

#: MusicXML family -> the staged quantity it would come from, and the detector
#: classes that would feed it.
#:
#: ⚠️ THIS TABLE IS THE ONE HAND-WRITTEN THING IN THIS MODULE, and it has to
#: be: no derivation maps a SMuFL class name onto a MusicXML element. Every
#: other column of the report — whether the quantity exists, whether its
#: decision is a stub, whether its input is gathered, how many rows the run
#: holds — is read out of the registry and the record.
#: ⚠️ The third slot is the EXPORTER'S OWN COUNTER for the family, where one
#: exists. A family's quantity says what must be DECIDED; only the counter
#: says what reached the FILE, and for a measurement-shaped quantity like
#: `Q.REST` -- which is observed, never adjudicated, its value settled by
#: `duration` -- there is no decided verdict to count and the record alone
#: would report a family that came out fine as `abstained`.
FAMILIES: Dict[str, Tuple[Optional[str], Tuple[str, ...], Tuple[str, ...]]] = {
    "note": (Q.PITCH, ("notehead",), ("notes",)),
    "rest": (Q.REST, ("rest",), ("rests", "measure_rests_read")),
    "slur": (Q.ARC_KIND, ("slur",), ("slurs",)),
    "tie": (Q.ARC_KIND, ("tie",), ("ties",)),
    "articulation": (Q.ARTICULATION_OWNER, ("artic",), ("articulations",)),
    "dynamic": (Q.DYNAMIC, ("dynamic",), ("dynamics",)),
    "wedge": (Q.WEDGE_ANCHOR, ("dynamicCrescendoHairpin",
                               "dynamicDiminuendoHairpin"), ("wedges",)),
    # ⚠️ NO DETECTOR PREFIX, AND THAT IS CORRECT RATHER THAN AN OMISSION: a
    # direction word is not in the 208-class space at all. `textDynamic` is the
    # class that would have supplied one and it is the class Phase 3.4's
    # expansion collapsed on, so the words are read by OCR over the ink the
    # detections are SUBTRACTED from. `detector_glyphs` is therefore 0 by
    # construction and `cv_glyphs` -- derived from `subjects_from` -- is where
    # this family's reach is reported.
    "direction": (Q.DIRECTION, (), ("direction_words",)),
    "ornament": (Q.ORNAMENT_OWNER, ("ornament", "tremolo"), ("ornaments",)),
    "fermata": (Q.FERMATA_OWNER, ("fermata",), ("fermatas",)),
    "clef": (Q.CLEF, ("clef",), ()),
    "key": (Q.KEY_SIGNATURE, ("key",), ()),
    "time": (Q.METER, ("timeSig",), ()),
    "tuplet": (Q.TUPLET_RATIO, ("tuplet", "fingering3"), ()),
}


#: Detected classes that are NOT a notation family of their own, with the
#: reason. ⚠️ A DENY-LIST, NOT AN ALLOW-LIST, and the direction is the point:
#: the default for a class nobody has thought about is *reported*, not
#: *silently unchecked*. `export_coverage` learned this the hard way -- its
#: hand-written `VISIBLE` allow-list was blind to fifteen elements including
#: the tenth export gap -- so the same inversion is used here.
NOT_NOTATION: Dict[str, str] = {
    "notehead": "the note itself; counted as the `note` family",
    "rest": "counted as the `rest` family",
    "beam": "consumed by `duration` as a beam stroke",
    "stem": "CV-only; `Q.STEM` is gathered and no exporter writes a stem",
    "staff": "the staff lines: page geometry, not a symbol",
    "ledgerLine": "consumed by `glyph_owner`'s ladder arbitration",
    "brace": "grouping; `group_symbol` decides the symbol",
    "bracket": "as brace",
    "augmentationDot": "consumed by `duration` as a dot",
    "flag": "consumed by `duration`: a flag says what a beam says for an "
            "unbeamed note (`Q.FLAG`)",
    # ⚠️⚠️ THIS ENTRY READ "consumed into `pitch` and `accidental`" UNTIL
    # 2026-09-21 AND BOTH HALVES WERE FALSE. `restate_pitch` derives the pitch
    # from POSITION + CLEF and never looks at an accidental glyph; and
    # `Q.ACCIDENTAL`'s only producer is `respell_accidental`, which reads the
    # KEY SIGNATURE -- so no detected accidental reaches either. The tree said
    # so in the other direction all along:
    # `gather_coverage.FAMILY_Q_IS_ELSEWHERE["accidental"]` states that the
    # in-bar accidental "is still filed only as an anonymous `Q.GLYPH_BOX`",
    # and the two documents contradicted each other for as long as both
    # existed. 256 such glyphs on Litolff pp.1-4 reach nothing.
    "accidental": "NOT consumed: the key-derived alteration reaches `pitch` "
                  "via `Q.ACCIDENTAL`, but the PRINTED glyph is read by "
                  "nothing and is filed only as an anonymous `Q.GLYPH_BOX`. "
                  "Counted in coverage()'s `accidental_reading` block, which "
                  "is the abstention rather than a family row.",
    "key": "consumed by `key_signature`",
    "clef": "counted as the `clef` family",
    "timeSig": "counted as the `time` family",
    "tuplet": "counted as the `tuplet` family",
    "fingering": "a performance marking, not a notation family we export",
    "repeatDot": "repeat barlines are a KNOWN GAP of the legacy exporter too",
    "barline": "structure; `measure_partition` decides the bars",
}


#: Families whose value reaches the file inside `<attributes>` rather than as
#: an element of their own, so no per-family counter can see them.
_IN_ATTRIBUTES = frozenset({"clef", "key", "time", "tuplet"})


#: Every status `coverage()` can assign. ⚠️ A CLOSED SET, asserted: a status
#: not listed here lands in the census's `unaccounted` bucket, which a test
#: requires to be empty. That is what stops a future status from being
#: invented and quietly belonging to no headline.
_STATUSES = ("emitted", "decided_but_unwritten", "decided_uncounted",
             "abstained", "stub", "starved", "NO_QUANTITY")


def _census(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Every family row, filed under its status — a PARTITION, not a filter.

    ⚠️ The two headlines are selections and therefore cannot say where a
    family WENT. This can: the counts sum to the number of rows, so a family
    that leaves one bucket has to appear in another.
    """
    out: Dict[str, Any] = {s: [] for s in _STATUSES}
    out["unaccounted"] = []
    for r in rows:
        # ⚠️ EXACTLY ONE BUCKET PER ROW. The first draft of this used
        # `setdefault(status, unaccounted).append(...)` and THEN appended
        # again inside an `if status not in _STATUSES` guard, so an unknown
        # status was filed twice and `n_filed` over-counted -- a balance
        # check that lies is worse than none, which is this module's own
        # lesson about `symbol_ledger.coverage_check`.
        bucket = r["status"] if r["status"] in _STATUSES else "unaccounted"
        out[bucket].append(r["family"])
    out["n_families"] = len(rows)
    out["n_filed"] = sum(len(v) for v in out.values() if isinstance(v, list))
    out["balanced"] = out["n_filed"] == len(rows)
    return out


def _claims(family: str, cls: str) -> bool:
    """Does `family` claim this detector class — LONGEST PREFIX WINS.

    ⚠️⚠️ A PLAIN PREFIX TEST DOUBLE-COUNTS THE HAIRPINS, AND `gather.py`
    ALREADY SAYS WHY. `dynamicCrescendoHairpin` and
    `dynamicDiminuendoHairpin` carry a name starting with `dynamic`, so under
    a plain test they were counted by BOTH the `dynamic` family (prefix
    `dynamic`) and the `wedge` family (which names them exactly) — and where
    both were unrepresented the headline total charged the same ink twice.
    `gather_glyph_families` is routed by CLASS "never by the detector's
    `category`" for precisely this glyph, and the coverage table had the fault
    that finding exists to prevent, one module over.

    Longest prefix wins, so `wedge`'s 23-character exact name beats
    `dynamic`'s 7. Derived, so a future family that overlaps an existing one
    resolves the same way without a hand-written exclusion.
    """
    low = cls.lower()
    best, owner = 0, None
    for name, (_q, prefixes, _c) in FAMILIES.items():
        for pre in prefixes:
            pl = pre.lower()
            if low.startswith(pl) and len(pl) > best:
                best, owner = len(pl), name
    return owner == family


def _unclaimed(detected: Dict[str, int]) -> Dict[str, int]:
    """Detected classes that no family claims and no reason excuses.

    ⚠️ DERIVED, so it cannot go stale by my forgetting a class. Every family's
    prefixes claim what they claim; `NOT_NOTATION` excuses the rest with a
    written reason; and whatever is left is reported by name and count. A
    class nobody has decided about shows up here the first time the detector
    emits one.
    """
    claimed = tuple(p.lower() for _q, prefixes, _c in FAMILIES.values()
                    for p in prefixes)
    excused = tuple(k.lower() for k in NOT_NOTATION)
    out: Dict[str, int] = {}
    for cls, n in detected.items():
        low = cls.lower()
        if any(low.startswith(p) for p in claimed + excused):
            continue
        out[cls] = n
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


#: Readers whose rows the `Q.GLYPH_BOX` census ALREADY counts. ⚠️ Derived
#: from nothing and hand-written on purpose, and it is two names rather than
#: one: `gather_detections` files `Q.GLYPH_BOX` under `DETECTOR`, and the
#: header crop's rows under `DETECTOR_HEADER`. A row from either would be
#: double-counted if it were added again below.
_DETECTOR_READERS = frozenset({"detector", "detector_header"})


def _non_detector_ink(rec: "Record", quantity: Optional[str]) -> int:
    """Rows of this family's OWN ink that the detector never produced.

    ⚠️ DERIVED FROM THE REGISTRY, never a hand-written list of families. A
    decision's `subjects_from` names the quantity whose rows ARE its
    population -- that is what `subjects_from` means and why `arc_owner`
    stopped abstaining 2,728 times a page -- so the family's ink is exactly
    that quantity's observations. Counting the ones whose `reader` is not the
    detector adds each CV reading once and no detector reading twice.

    ⚠️ A FAMILY WITH NO `subjects_from` RETURNS ZERO, which is correct rather
    than defensive: its population is the detector's own glyphs, already
    counted. Returning "unknown" here and letting the caller guess would be
    the fallback converting *cannot tell* into a definite answer that this
    repo has now paid for three times in one day -- so the case that cannot
    be answered is the case that genuinely has nothing to add.
    """
    if quantity is None:
        return 0
    spec = A.REGISTRY.get(quantity)
    source = getattr(spec, "subjects_from", None) if spec is not None else None
    if not source:
        return 0
    return sum(1 for o in rec.obs_of(source)
               if str(o.get("reader")) not in _DETECTOR_READERS)


def coverage(result: Dict[str, Any],
             written: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """For every notation family: did it come out, and if not, WHY NOT.

    ⚠️ FOUR DIFFERENT ZEROS, REPORTED APART. The legacy `export_coverage`
    reports one — "the truth has some, we emit zero" — and needs a truth file
    to say it. This needs none, because the record already knows which
    decision was asked and what it answered. The four are not
    interchangeable: `abstained` is the system working, `stub` is scheduled
    work, `starved` is TWO pieces of scheduled work wearing one name, and
    `NO_QUANTITY` is a family nobody has decided exists.
    """
    A._ensure_decisions()
    rec = Record(result)

    # the positive control: what the DETECTOR put in the log
    detected: Dict[str, int] = collections.Counter()
    for o in rec.obs_of(Q.GLYPH_BOX):
        value = o["value"]
        name = value[0] if isinstance(value, (list, tuple)) else str(value)
        detected[str(name)] += 1

    from . import inventory
    sites, indirect = inventory._gather_sites()

    # ⚠️⚠️ TWO FAMILIES CAN SHARE ONE QUANTITY, AND UNTIL THIS LINE BOTH ROWS
    # REPORTED THE WHOLE POPULATION. `tie` and `slur` are both `Q.ARC_KIND`,
    # so on Litolff `984073` p1-3 each row read `decided: 514` — the arcs of
    # BOTH kinds, stated twice — against a real split of **270 ties and 244
    # slurs**, which `detector_glyphs` had right all along (270 / 244) one
    # column to the left. A reader comparing `decided 514` against `written
    # 49` would conclude the exporter drops 465 ties.
    #
    # ⚠️ THE SPLIT IS DERIVED FROM `FAMILIES` ITSELF, never a second table: a
    # quantity claimed by more than one family is attributed by VALUE, and the
    # family names ARE the values `adjudicate_arc_kind` returns. A fourth
    # hand-written column here would be one more thing to keep in step.
    shared = collections.Counter(q for q, _p, _c in FAMILIES.values() if q)
    # ⚠️ AN ABSTENTION ON A SHARED QUANTITY NAMES NO FAMILY, and that is the
    # honest reading rather than a shortcut: `arc_kind` abstains `no_arc_box`
    # precisely when it could not say WHICH kind, so filing it under `tie` and
    # again under `slur` is the same double count one row up. Reported ONCE,
    # at the top of the report, keyed by the quantity it belongs to.
    unattributed: Dict[str, Dict[str, int]] = {}

    rows: List[Dict[str, Any]] = []
    for family, (quantity, prefixes, counter_keys) in sorted(FAMILIES.items()):
        n_detected = sum(n for cls, n in detected.items()
                         if _claims(family, cls))
        n_cv = _non_detector_ink(rec, quantity)
        row: Dict[str, Any] = {
            "family": family,
            "quantity": quantity,
            "detector_glyphs": n_detected,
            # ⚠️⚠️ INK THE DETECTOR NEVER SAW, AND THE HEADLINE MUST READ THIS.
            # `detected` above is built from `Q.GLYPH_BOX`, which is the
            # DETECTOR's class space -- so a family a CLASSICAL-CV rung reads
            # is invisible to it. Measured on the Breitkopf Brahms 1 p0-3
            # record: `wedge` reported `detector_glyphs: 1` while the record
            # held **47** `Q.WEDGE_BOX` rows, 46 of them from `cv_hairpins`.
            # Anyone sizing the wedge work off the coverage headline read its
            # reach as 1 instead of 47 -- a 47x under-report of the only
            # family whose ink comes from a CV reader.
            #
            # Reported APART rather than folded in, because "the detector
            # found this" and "a CV rung found this" are different facts about
            # the page: `gather_wedge_boxes` emits both readers precisely so a
            # consumer can decide which to believe, and a single merged number
            # would destroy that on the way to the report.
            "cv_glyphs": n_cv,
            "ink_rows": n_detected + n_cv,
            "written": sum((written or {}).get(k, 0) for k in counter_keys),
        }
        if quantity is None:
            row["status"] = "NO_QUANTITY"
            row["why"] = (
                "the staged vocabulary has no quantity for this family: no "
                "gather site, no adjudicator, no stub and no `wants` naming "
                "it. Nothing in the record declares the absence.")
            rows.append(row)
            continue

        spec = A.REGISTRY.get(quantity)
        verdicts = list(rec.verdicts_of(quantity))
        is_shared = shared[quantity] > 1
        if is_shared:
            decided = len([v for v in verdicts if v["outcome"] == "decided"
                           and str(v["value"]) == family])
            abstained = collections.Counter()
            # ⚠️⚠️ AN ASSIGNMENT, NOT AN ACCUMULATION, AND THE FIRST CUT WAS
            # THE OTHER ONE. This loop runs once per FAMILY, so a
            # `setdefault(...).update(...)` adds the same quantity's
            # abstentions once for `tie` and again for `slur` -- the exact
            # double count this key exists to end, reappearing one level up.
            # A test asserting the whole map caught it.
            #
            # ⚠️ Written as an assignment rather than guarded by an
            # `if quantity not in unattributed`, because that guard cannot
            # change the outcome of an assignment: it is a check that cannot
            # fail, and a mutation arm deleting it SURVIVED. Making the double
            # count unrepresentable beats testing for it.
            unattributed[quantity] = dict(collections.Counter(
                v["reason"] for v in verdicts if v["outcome"] != "decided"))
            # ⚠️ SAID ON THE ROW, not left to be inferred from an empty dict:
            # `abstained: {}` on a shared quantity means "reported elsewhere",
            # which is a different fact from "none".
            row["abstentions_name_no_family"] = True
        else:
            decided = len([v for v in verdicts if v["outcome"] == "decided"])
            abstained = collections.Counter(
                v["reason"] for v in verdicts if v["outcome"] != "decided")
        row["decided"] = decided
        row["abstained"] = dict(abstained)
        # ⚠️ WHO produces it is a separate column from WHETHER it came out.
        # `pitch` and `accidental` are EVALUATE consequences and have no entry
        # in the adjudication registry at all; folding that into `status`
        # would report a family that reached the file as though it had not.
        row["produced_by"] = "adjudicate" if spec is not None else "evaluate"
        if spec is None:
            row["status"] = "emitted" if decided else "abstained"
        elif spec.stub:
            starved = [w for w in spec.wants
                       if w not in sites and w not in indirect
                       and w not in A.REGISTRY]
            row["status"] = "starved" if starved else "stub"
            if starved:
                row["why"] = (
                    f"declared stub AND its input is never gathered "
                    f"({', '.join(starved)}) — writing the adjudicator alone "
                    f"would still produce nothing")
        elif row["written"]:
            row["status"] = "emitted"
        elif decided and family in _IN_ATTRIBUTES:
            # ⚠️ These reach the file inside `<attributes>`, which has no
            # per-family counter to read. Named apart so they are not
            # mistaken for the unwritten case below.
            row["status"] = "emitted"
        elif decided and counter_keys:
            # ⚠️⚠️ THE STATUS THIS REPORT EXISTS FOR, AND IT WAS UNREACHABLE
            # UNTIL 2026-09-09. The branch order was `elif decided: ... elif
            # written is not None: "decided_but_unwritten" if decided`, so the
            # third branch consumed every decided family and the fourth could
            # only ever see `decided == 0` — the guard on a dead branch. A
            # decision that decided and reached no file was reported as
            # `decided`, which reads like success.
            #
            # It was found by the controlled A/B for the dynamics wiring: the
            # BEFORE arm wrote zero `<dynamics>` and still reported
            # `decided_but_unwritten: []`. *A check that cannot fail is worse
            # than no check* — `health.py` learned the same lesson from a
            # clause that emptied its own EMPTY CELLS list in one line.
            row["status"] = "decided_but_unwritten"
            row["why"] = (
                f"`{quantity}` decided {decided} times and the exporter wrote "
                f"none of this family — the record carries it and the FILE "
                f"does not, which is an exporter gap, not a reading one")
        elif decided:
            # ⚠️ NO COUNTER EXISTS, so this row cannot say whether the family
            # reached the file. Reported as its own state rather than folded
            # into `decided`: an unmeasurable family must not read as a
            # measured success.
            row["status"] = "decided_uncounted"
            row["why"] = (
                "decided, but this family has no exporter counter, so whether "
                "it reached the file is UNKNOWN to this report")
        else:
            row["status"] = "abstained"
        rows.append(row)

    # ⚠️ `ink_rows`, NOT `detector_glyphs`, since 2026-09-10 — see the column's
    # own note. The headlines are about INK THE PAGE HOLDING that nothing
    # carries, and which reader found it is irrelevant to that question while
    # being decisive for the number: on `wedge` the two differ 1 against 47.
    unread = {r["family"]: r["ink_rows"] for r in rows
              if r["status"] in ("NO_QUANTITY", "starved", "stub")
              and r["ink_rows"]}
    unwritten = {r["family"]: r["ink_rows"] for r in rows
                 if r["status"] == "decided_but_unwritten"
                 and r["ink_rows"]}
    uncounted = [r["family"] for r in rows
                 if r["status"] == "decided_uncounted"]
    return {
        "families": rows,
        # ⚠️⚠️ THE ACCIDENTAL IS TWO FACTS AND WE HOLD ONLY ONE, SO THE OTHER
        # IS COUNTED RATHER THAN GUESSED. `<alter>` is what the note SOUNDS
        # and comes from `Q.ACCIDENTAL`, which `respell_accidental` derives
        # from the key. `<accidental>` is the glyph the engraver PRINTED and
        # nothing reads one: the in-bar accidental is filed as an anonymous
        # `Q.GLYPH_BOX` and reaches no quantity at all. So the exporter writes
        # no `<accidental>`, and this is the size of that abstention -- every
        # one is a note that may carry a printed alteration we did not read.
        #
        # ⚠️ IT IS NOT A FAMILY ROW, deliberately: `accidental` is on
        # `NOT_NOTATION`, and promoting it would put a family in the census
        # whose quantity is an EVALUATE consequence rather than a reading.
        # Reported at the top instead, where a zero cannot be mistaken for a
        # family that came out fine.
        "accidental_reading": {
            "printed_glyphs_detected": sum(
                n for cls, n in detected.items()
                if cls.lower().startswith("accidental")),
            # ⚠️ DERIVED, NEVER A LITERAL ZERO. `respell_accidental` is the
            # only producer today, so this is 0 -- but a hardcoded 0 would
            # STILL read 0 the day a reader of the printed glyph lands, which
            # is the "control that computes the wrong thing" this repo has
            # recorded five times. Counting the verdicts some OTHER decider
            # wrote makes the figure move on its own.
            "printed_glyphs_read_into_a_verdict": sum(
                1 for v in rec.verdicts_of(Q.ACCIDENTAL)
                if v.get("decider") != "respell_accidental"),
            "pitches_altered_by_the_key": int(
                (written or {}).get("pitches_altered_by_the_key", 0)),
        },
        # ⚠️ Ink of a kind no family and no reason accounts for. Derived, so a
        # class nobody has thought about appears here the first time the
        # detector emits one.
        "unclaimed_classes": _unclaimed(detected),
        # ⚠️ THE HEADLINE: ink the detector found and the record cannot carry.
        "detected_and_unrepresented": unread,
        "detected_and_unrepresented_total": sum(unread.values()),
        # ⚠️⚠️ THE SECOND HEADLINE, AND IT MEASURES A DIFFERENT FAULT.
        # The first is a RECORD gap: no quantity, a stub, or a stub whose
        # input is not gathered. This is an EXPORT gap: the decision decided,
        # the record carries the answer, and no file received it. They must be
        # reported apart because the repair differs — one is "write an
        # adjudicator", the other is "read the verdict you already have".
        #
        # ⚠️ AND KEEPING THEM APART IS WHY THE FIRST FELL BY ~284 GLYPHS ON
        # beet5-p3 THE DAY `dynamic` STOPPED BEING A STUB, WITH NOTHING
        # REACHING A FILE. A headline that improves because a family changed
        # BUCKET is the shape this repo has paid for repeatedly; quote both.
        "decided_and_unwritten": unwritten,
        "decided_and_unwritten_total": sum(unwritten.values()),
        "decided_uncounted": uncounted,
        # ⚠️ The abstentions of a quantity two families share, reported ONCE.
        # See the note beside `shared` above: an abstention says the decision
        # could not name a kind, so it belongs to neither family's row and
        # counting it in both is the conflation this key exists to end.
        "abstained_without_a_family": {
            q: c for q, c in unattributed.items() if c},
        # ⚠️⚠️ THE CENSUS EXISTS BECAUSE BOTH HEADLINES ARE STATUS FILTERS,
        # AND A FILTER CANNOT SAY WHERE A FAMILY WENT. Raised by the
        # meter/boundary session against this very fix: `dynamic` left
        # `detected_and_unrepresented` silently the day it stopped being a
        # stub, and adding a SECOND filtered headline reproduces that surprise
        # one level up -- the next family to change status moves between the
        # two, or out of both, with no line anywhere saying so.
        #
        # A census over EVERY row cannot do that: a family that leaves one
        # bucket must appear in another, because the buckets partition the
        # rows rather than selecting from them. `_STATUSES` is the closed set
        # and `unaccounted` is the escape hatch that must always be empty --
        # the same inversion `NOT_NOTATION` uses, where the default for
        # something nobody has thought about is *reported*.
        "status_census": _census(rows),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("staged_json", help="a `python3 -m tools.omr.staged --out` file")
    ap.add_argument("--out", default=None, help="write the MusicXML here")
    # ⚠️ ROADMAP 3.1. `--lilypond` is a SIBLING output, not a `--format`
    # switch: both can be requested from one `staged_json` in one call, the
    # same way `staged/__main__.py --musicxml` already sits beside `--out`.
    # Wired here (and NOT into `to_musicxml`/`coverage` above) because
    # `tools.omr.staged.lilypond.to_lilypond` is a separate module reusing
    # `build()`/`_pair_arcs`/`_place_wedges` from THIS one — importing it at
    # module load would make `export.py` depend on its own consumer.
    ap.add_argument("--lilypond", default=None, help="also write a .ly here")
    ap.add_argument("--coverage", default=None, help="write the report here")
    ap.add_argument("--coverage-only", action="store_true")
    args = ap.parse_args(argv)

    from .record_io import load_record
    result = load_record(args.staged_json)
    if args.coverage_only:
        report = coverage(result)
    else:
        xml, report = to_musicxml(result)
        if args.out:
            pathlib.Path(args.out).write_text(xml)
            print(f"wrote {args.out}", file=sys.stderr)
        else:
            print(xml)

    if args.lilypond:
        from . import lilypond as _lily
        ly_text, ly_report = _lily.to_lilypond(result)
        pathlib.Path(args.lilypond).write_text(ly_text)
        print(f"wrote {args.lilypond}", file=sys.stderr)
        _lily._report(ly_report)

    if args.coverage:
        pathlib.Path(args.coverage).write_text(json.dumps(report, indent=2))
        print(f"wrote {args.coverage}", file=sys.stderr)

    _report(report)
    return 0


def _report(report: Dict[str, Any]) -> None:
    print("\n── EXPORT ─────────────────────────────────────────────", file=sys.stderr)
    if "written" in report:
        print(f"  written: {report['written']}", file=sys.stderr)
        print(f"  part join: {report['part_join']}", file=sys.stderr)
    if report.get("notes_not_written_total"):
        print(f"  ⚠️ notes the record holds and the file does not: "
              f"{report['notes_not_written_total']} "
              f"{report['notes_not_written']}", file=sys.stderr)
    print("── WHAT DID NOT REACH THE FILE ────────────────────────", file=sys.stderr)
    for row in report["families"]:
        if row["status"] in ("emitted", "decided", "CONSEQUENCE"):
            continue
        detected = row["detector_glyphs"]
        print(f"  {row['family']:14s} {row['status']:12s} "
              f"detector found {detected}", file=sys.stderr)
    total = report["detected_and_unrepresented_total"]
    print(f"  ⚠️ {total} detected glyphs the record cannot carry: "
          f"{report['detected_and_unrepresented']}", file=sys.stderr)
    unclaimed = report.get("unclaimed_classes") or {}
    if unclaimed:
        print(f"  ⚠️ {sum(unclaimed.values())} detected glyphs of a kind NO "
              f"family and no reason accounts for: {unclaimed}",
              file=sys.stderr)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
