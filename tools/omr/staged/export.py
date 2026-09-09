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
import json
import pathlib
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import export as _legacy
from ..voicing import group_chords_in_measure
from . import adjudicate as A
from .record import Q


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


def _staff_key(page: int, system: int, staff: int) -> str:
    return f"staff/{page}/{system}/{staff}"


def build(rec: Record) -> Tuple[List[List[StaffRun]], Dict[str, Any],
                               Dict[str, int]]:
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

    dropped = _place_notes(rec, runs)

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
    return parts, provenance, dropped


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
        })
    return dict(dropped)


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


def _part_xml(part: Sequence[StaffRun], pid: str, divisions: int,
              counters: Dict[str, int]) -> str:
    """One `<part>`: every measure of every system this part appears on."""
    lines = [f'  <part id="{pid}">']
    number = 0
    prev = {"clef": object(), "key": object(), "time": object()}
    first = True
    for run in part:
        key = _key_dict(run.fifths)
        meter = _meter_dict(run.meter)
        for i in range(run.n_measures):
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
            events = _events(run.cells.get(i))
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
                lines.extend(_legacy._mxl_empty_measure(
                    meter, divisions, None, "      "))
            else:
                lines.extend(_measure_events_xml(events, divisions, counters))
            lines.append("    </measure>")
    lines.append("  </part>")
    return "\n".join(lines)


def _measure_events_xml(events: List[Dict[str, Any]], divisions: int,
                        counters: Dict[str, int]) -> List[str]:
    out: List[str] = []
    for ev in events:
        if ev.get("kind") == "rest":
            out.extend(_rest_xml(ev, divisions, counters))
            continue
        heads = ev.get("noteheads") or []
        tup = next((h["tuplet"] for h in heads
                    if isinstance(h.get("tuplet"), dict)), None)
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
                is_chord=(n > 0), is_rest=False, indent="      ", voice=1,
                time_modification=time_mod, tuplet_state=state,
                accidental=head.get("accidental")))
            counters["notes"] += 1
            if head.get("accidental"):
                counters["accidentals"] += 1
    return out


def _rest_xml(ev: Dict[str, Any], divisions: int,
              counters: Dict[str, int]) -> List[str]:
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
    return [_legacy._mxl_note(
        None, "", xml_type, dots, beats, divisions, is_chord=False,
        is_rest=True, indent="      ", voice=1, measure_rest=measure_rest)]


def to_musicxml(result: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """The file, and the record of what did not reach it."""
    rec = Record(result)
    parts, provenance, dropped = build(rec)
    divisions = _divisions(parts)
    counters: Dict[str, int] = collections.Counter()

    part_list: List[str] = []
    parts_xml: List[str] = []
    for i, part in enumerate(parts):
        pid = f"P{i + 1}"
        name = next((r.name for r in part if r.name), None) or _default_name(part)
        part_list.append(
            f'    <score-part id="{pid}">\n'
            f'      <part-name>{_legacy._xml_escape(name)}</part-name>\n'
            f'    </score-part>')
        parts_xml.append(_part_xml(part, pid, divisions, counters))

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
    written = (int(counters["notes"]) + int(counters["rests"])
               + int(counters["measure_rests_read"]))
    report["balance"] = {
        # ⚠️ RESTS ARE IN THE CONTROL NOW. They were outside it while they had
        # no quantity, which is exactly how 838 glyphs stayed invisible: a
        # balance that does not count a family cannot be unbalanced by losing
        # one.
        "events_in_log": events_in_log,
        "noteheads_in_log": len(rec.obs_of(Q.NOTEHEAD_CLASS)),
        "rests_in_log": len(rec.obs_of(Q.REST)),
        "events_written": written,
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
    "slur": (Q.ARC_KIND, ("slur",), ()),
    "tie": (Q.ARC_KIND, ("tie",), ()),
    "articulation": (Q.ARTICULATION_OWNER, ("artic",), ()),
    "dynamic": (Q.DYNAMIC, ("dynamic",), ()),
    "wedge": (Q.WEDGE_ANCHOR, ("dynamicCrescendoHairpin",
                               "dynamicDiminuendoHairpin"), ()),
    "direction": (Q.DIRECTION, (), ()),
    "ornament": (None, ("ornament", "tremolo"), ()),
    "fermata": (None, ("fermata",), ()),
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

    rows: List[Dict[str, Any]] = []
    for family, (quantity, prefixes, counter_keys) in sorted(FAMILIES.items()):
        n_detected = sum(n for cls, n in detected.items()
                         if any(cls.lower().startswith(p.lower())
                                for p in prefixes))
        row: Dict[str, Any] = {
            "family": family,
            "quantity": quantity,
            "detector_glyphs": n_detected,
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
        decided = len([v for v in rec.verdicts_of(quantity)
                       if v["outcome"] == "decided"])
        abstained = collections.Counter(
            v["reason"] for v in rec.verdicts_of(quantity)
            if v["outcome"] != "decided")
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
        elif decided:
            row["status"] = "emitted" if family in (
                "clef", "key", "time", "tuplet") else "decided"
        elif written is not None:
            # the exporter ran and wrote none of this family
            row["status"] = "decided_but_unwritten" if decided else "abstained"
        else:
            row["status"] = "abstained"
        rows.append(row)

    unread = {r["family"]: r["detector_glyphs"] for r in rows
              if r["status"] in ("NO_QUANTITY", "starved", "stub")
              and r["detector_glyphs"]}
    return {
        "families": rows,
        # ⚠️ Ink of a kind no family and no reason accounts for. Derived, so a
        # class nobody has thought about appears here the first time the
        # detector emits one.
        "unclaimed_classes": _unclaimed(detected),
        # ⚠️ THE HEADLINE: ink the detector found and the record cannot carry.
        "detected_and_unrepresented": unread,
        "detected_and_unrepresented_total": sum(unread.values()),
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
