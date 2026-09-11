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


def _staff_key(page: int, system: int, staff: int) -> str:
    return f"staff/{page}/{system}/{staff}"


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

    dropped = _place_notes(rec, runs)
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
        for s in systems:
            for run in by_system[s]:
                slot = rec.value(Q.SLOT_INDEX, run.key)
                if not isinstance(slot, int):
                    stranded += 1
                    parts.append([run])
                    continue
                by_slot[slot].append(run)
        for slot in sorted(by_slot):
            parts.append(by_slot[slot])
        provenance_extra = {"slots": sorted(by_slot), "stranded": stranded}
    else:
        # ⚠️ THE FRAGMENT FALLBACK IS THE LEGACY BEHAVIOUR AND IS KEPT.
        # One part per system-staff. It pairs with nothing in a reference and
        # scores badly, and it is still right: the alternative is grafting.
        used = "fragments"
        for s in systems:
            for run in by_system[s]:
                parts.append([run])

    provenance = {
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
            fermatas_dropped, ornaments_dropped)


def _place_notes(rec: Record, runs: Dict[str, StaffRun]) -> Dict[str, int]:
    """Every decided note, in the cell its OWNER puts it in.

    ⚠️ THE OWNER, NOT THE SUBJECT. A measure cell is cut with padding above
    and below so ledger notes are not sliced off, so on a conductor's page the
    same ink is detected once per staff and `glyph_owner` arbitrates. The
    subject coordinate records where the glyph was FOUND; the verdict records
    whose it IS. Exporting by subject would put Violin 1's high A on the
    timpani — the documented failure that cost 263 edits.
    """
    dropped: Dict[str, int] = collections.Counter()
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = _parse_subject(sub)
        if s["glyph"] is None:
            continue
        is_rest = bool(rec.obs(Q.REST, sub))
        if not is_rest and not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue                 # neither a notehead nor a rest
        # ⚠️ A REST HAS NO PITCH AND MUST NOT BE ASKED FOR ONE. Requiring a
        # pitch is what kept rests out of the file for as long as they had no
        # quantity at all; asking for one now would keep them out for a
        # second, subtler reason.
        pitch = None if is_rest else rec.value(Q.PITCH, sub)
        dur_v = rec.verdict(Q.DURATION, sub)
        dur = dur_v["value"] if dur_v and dur_v["outcome"] == "decided" else None

        if pitch is None and not is_rest:
            # ⚠️ NO POSITIONAL DEFAULT. A staff whose clef abstained produces
            # no pitches at all (`consequences.restate_pitch`), deliberately,
            # and the exporter must not undo that by writing treble.
            dropped["no_pitch"] += 1
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
            dropped[("rest_" if is_rest else "")
                    + "duration_"
                    + (dur_v["outcome"] if dur_v else "absent")] += 1
            continue

        owner = rec.value(Q.GLYPH_OWNER, sub)
        home = owner if isinstance(owner, str) else _staff_key(
            s["page"] or 0, s["system"] or 0, s["staff"] or 0)
        run = runs.get(home)
        if run is None:
            # The owner names a staff with no `measure_partition` verdict, so
            # there is no bar to put the note in. Counted, not swallowed.
            dropped["owner_staff_has_no_measures"] += 1
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
            dropped["written_value_fits_no_note"] += 1
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
            "accidental": rec.value(Q.ACCIDENTAL, sub),
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
    for part in parts:
        measures, per_measure_arcs, kinds, spacings, tops, breaks = \
            _flatten_part(part)
        if not measures or not any(per_measure_arcs):
            continue
        voice_of = _voice_of_notehead(rec, part)
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
                                          breaks, voice_of)
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

    ⚠️ OWNERSHIP IS NOT RE-ASKED HERE, unlike `_place_notes`. A dynamic letter
    cut from the cell above is moved by `adjudicate_dynamic` itself, which
    queries `Q.GLYPH_OWNER` across the system and keeps only the letters this
    staff owns — both directions of the move. So the CELL the verdict is filed
    on is already the answer, and asking again would be a second, differently
    spelled ownership rule.

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


def _part_xml(rec: Record, part: Sequence[StaffRun], pid: str,
              divisions: int, counters: Dict[str, int]) -> str:
    """One `<part>`: every measure of every system this part appears on."""
    lines = [f'  <part id="{pid}">']
    number = 0
    prev = {"clef": object(), "key": object(), "time": object()}
    first = True
    segments_on = meter_segments_enabled()
    for run in part:
        key = _key_dict(run.fifths)
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
            lines.append(f'    <measure number="{number}">')
            changed = (run.clef != prev["clef"] or key != prev["key"]
                       or meter != prev["time"])
            if first or changed:
                lines.append(_legacy._mxl_attributes_block(
                    run.clef, key, meter, divisions, "      ",
                    include_divisions=first))
                prev = {"clef": run.clef, "key": key, "time": meter}
                first = False
            cell_here = run.cells.get(i)
            directions = list(cell_here.directions) if cell_here else []
            events = _events(cell_here)
            if not events:
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
                if meter is None:
                    counters["empty_bars_padded_without_meter"] += 1
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
                    meter, divisions, directions or None, "      "))
                counters["dynamics"] += len(directions)
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
                counters["dynamics"] += len(directions)
                lines.extend(_measure_xml(rec, run, i, events, divisions,
                                          counters))
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


def _measure_xml(rec: Record, run: StaffRun, cell_index: int,
                 events: List[Dict[str, Any]], divisions: int,
                 counters: Dict[str, int]) -> List[str]:
    """One bar's notes — one voice, or two separated by a `<backup>`.

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
    why: List[str] = []
    streams = _voice_split(rec, run, cell_index, events, why)
    if streams is None:
        for reason in why:
            counters["two_voice_bars_refused_" + reason] += 1
        lines, _units = _measure_events_xml(events, divisions, counters)
        return lines
    counters["two_voice_bars"] += 1
    out, units = _measure_events_xml(streams[0], divisions, counters, voice=1)
    if units > 0:
        out.append("      <backup>\n"
                   f"        <duration>{units}</duration>\n"
                   "      </backup>")
    second, _ = _measure_events_xml(streams[1], divisions, counters, voice=2)
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


def _measure_events_xml(events: List[Dict[str, Any]], divisions: int,
                        counters: Dict[str, int], voice: int = 1
                        ) -> Tuple[List[str], int]:
    """`(lines, duration units this voice consumed)`.

    ⚠️ THE SECOND RETURN IS WHAT `<backup>` IS WRITTEN FROM, and it counts
    CHORD-LEADING notes and rests only -- a chord member past the first does
    not advance the cursor. `_mxl_voice_events` computes the identical number
    for the legacy path; getting it wrong does not produce a wrong-looking
    file, it produces a second voice offset from the first by a beat.
    """
    out: List[str] = []
    units = 0
    for ev in events:
        if ev.get("kind") == "rest":
            out.extend(_rest_xml(ev, divisions, counters, voice=voice))
            units += max(1, int(round(float(ev["duration_beats"]) * divisions)))
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
                accidental=head.get("accidental")))
            counters["notes"] += 1
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
            if head.get("accidental"):
                counters["accidentals"] += 1
            if n == 0:
                units += max(1, int(round(beats * divisions)))
        # ⚠️ AFTER the chord's notes, for the reason above: the `stop` binds
        # to the last note music21 parsed, which is this event.
        for _number, _kind in (ev.get("wedge_states") or ()):
            if _kind == "stop":
                out.append(_legacy._mxl_wedge(_number, _kind, "      "))
    return out, units


def _rest_xml(ev: Dict[str, Any], divisions: int,
              counters: Dict[str, int], voice: int = 1) -> List[str]:
    """One `<rest>`, and the one place the BAR convention is written out.

    ⚠️ `measure="yes"` CARRIES NO `<type>`, and the two go together. The glyph
    stands for the bar, so there is no note value to name -- `_mxl_note`
    already refuses to write `<type>` when `measure_rest` is set, which is why
    this passes the flag rather than choosing a type of its own.
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
     fermatas_dropped, ornaments_dropped) = build(rec)
    divisions = _divisions(parts)
    counters: Dict[str, int] = collections.Counter()
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

    part_list: List[str] = []
    parts_xml: List[str] = []
    for i, part in enumerate(parts):
        pid = f"P{i + 1}"
        name = next((r.name for r in part if r.name), None) or _default_name(part)
        part_list.append(
            f'    <score-part id="{pid}">\n'
            f'      <part-name>{_legacy._xml_escape(name)}</part-name>\n'
            f'    </score-part>')
        parts_xml.append(_part_xml(rec, part, pid, divisions, counters))

    xml = _legacy._score_partwise(result.get("source", {}) or {},
                                  part_list, parts_xml)
    report = coverage(result, written=dict(counters))
    report["written"] = dict(counters)
    report["written"]["parts"] = len(parts)
    report["written"]["divisions"] = divisions
    report["part_join"] = provenance
    # ⚠️ A NOTE THE RECORD HOLDS AND THE FILE DOES NOT. Reported beside the
    # families for the same reason: a shortfall that is not counted is
    # indistinguishable from ink that was never read.
    report["notes_not_written"] = dropped
    report["notes_not_written_total"] = sum(dropped.values())
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
    for fam, mark in (("slurs", "slur_spans_marked"),
                      ("ties", "tie_spans_marked")):
        lost = int(counters.get(mark, 0)) - int(counters.get(fam, 0))
        if lost > 0:
            arcs_dropped["arc_ends_in_one_chord"] += lost
    report["arcs_not_written"] = dict(arcs_dropped)
    report["arcs_not_written_total"] = sum(arcs_dropped.values())
    # ⚠️ A THIRD PARTITION, AND IT IS ASSERTED RATHER THAN HOPED FOR. Every
    # gathered articulation mark is either written onto a note or counted here
    # -- the same control the notes get, on a family whose whole population is
    # small enough that one silent loss would be a large share of it.
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
    fermata_marks = len(rec.obs_of(Q.FERMATA_MARK))
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
    written = (int(counters["notes"]) + int(counters["rests"])
               + int(counters["measure_rests_read"]) - duplicated)
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
    "direction": (Q.DIRECTION, (), ()),
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
    "accidental": "consumed into `pitch` and `accidental`",
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
    ap.add_argument("--coverage", default=None, help="write the report here")
    ap.add_argument("--coverage-only", action="store_true")
    args = ap.parse_args(argv)

    result = json.loads(pathlib.Path(args.staged_json).read_text())
    if args.coverage_only:
        report = coverage(result)
    else:
        xml, report = to_musicxml(result)
        if args.out:
            pathlib.Path(args.out).write_text(xml)
            print(f"wrote {args.out}", file=sys.stderr)
        else:
            print(xml)

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
