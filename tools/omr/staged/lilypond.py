"""LILYPOND — a `.ly` source for the staged pipeline, over the SAME positions
`staged/export.py` builds for MusicXML.

⚠️ THIS IS NOT A PORT OF `tools/omr/export.py:to_lilypond`, and it is not a
second copy of `staged/export.py` either. `staged/export.py:build()` already
turns a staged record into `parts` — a list of `StaffRun`s in reading order,
each carrying its own bars — because MusicXML needs exactly that shape: one
`<part>` per instrument, spanning every system it appears on. This module
calls that SAME `build()`, the SAME `_pair_arcs`/`_place_wedges` cross-bar
merge passes, and the SAME `_events()`/`_voice_split()` per-bar readers, so
the two exporters can never disagree about which staff is which part, which
bar is tacet, or which two notes a slur binds — and it renders the result
with the legacy exporter's own PURE per-note/per-measure renderers
(`_lily_event`, `_lily_measure`, `_lily_measure_rest`, `_lily_key_name`,
`_clef_to_lily`, `_lily_wedge_plan`), because those already ARE the paid-for
positions in executable form (`_pair_arcs`, `_place_wedges` and `_events` are
built on `tools.omr.export`'s own CHORD-GROUPING SHAPE from `voicing.group_
chords_in_measure` in the first place — the staged and legacy paths already
agree on what an "event" dict looks like; only the WALK that turns a record
into a part differs, and that walk is `build()`'s, reused rather than
restated).

⚠️⚠️ ONE STRUCTURAL DEPARTURE FROM `tools.omr.export.to_lilypond`, DELIBERATE
AND NAMED HERE ONCE. The legacy renderer emits one `\\new Staff` per
(page, system, staff) — `_lily_wedge_plan`'s own docstring says so, and the
consequence is that a hairpin or slur crossing a SYSTEM BREAK is dropped by
construction, because the lane it is handed never spans one. That shape is
right for a page rendered one system at a time and wrong for a whole
document: stacking every system's staves as *simultaneous* `\\new Staff`
blocks would play every system of the piece at once. Since staged's `build()`
already produces one `StaffRun` list PER PART spanning every system — the
same object MusicXML's `<part>` is built from — this module emits one
`\\new Staff` per PART instead, in document order, and gets the cross-system
merge for free from the SAME `_pair_arcs`/`_place_wedges` passes MusicXML
already runs. So a hairpin or slur crossing a system break is NOT a
documented drop here; only what the legacy `_lily_event` family itself has no
syntax for is (see `_LILY_ONLY_DROPS` below).

    python3 -m tools.omr.staged.lilypond staged.json --out score.ly
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import export as _legacy
from . import export as SX
from .record import meter_at

#: The two things the legacy `_lily_event` family has no syntax for, named
#: once rather than scattered across the render loop. Neither is new: the
#: legacy exporter's OWN `to_lilypond` drops both, for the same reason —
#: `_LILY_ORNAMENT` excludes tremolo (it "carries its stroke count as well as
#: a name", the one mark `_mxl_ornament_elements` handles specially and
#: `_lily_event` does not), and `_lily_staff_block` never calls anything
#: resembling `_mxl_direction` for a dynamic word or a `cresc.` — LilyPond
#: would want `\\mf` / `^"cresc."` markup this reader does not build. Both are
#: COUNTED, never silently absorbed: see `report["lilypond"]`.
_LILY_ONLY_DROPS = ("ornaments_not_renderable", "direction_words_not_renderable")


def _lilypond_version() -> str:
    """The installed `lilypond --version`'s own number, or a safe floor.

    ⚠️ A `.ly` file's `\\version` is a compatibility DECLARATION, read by
    `convert-ly` to decide whether syntax has to be upgraded — writing a
    number the installed binary predates would make every compile warn about
    a file from the future. Asking the binary itself is the only way to say
    the right thing on both this machine and a CI image with a different
    release; `2.24.0` is the floor because nothing here uses syntax newer
    than that series.
    """
    try:
        out = subprocess.run(["lilypond", "--version"], capture_output=True,
                             text=True, timeout=10, check=False)
        first_line = (out.stdout or "").splitlines()[0] if out.stdout else ""
        # "GNU LilyPond 2.24.4 (running Guile 3.0)" -- the FIRST dotted
        # number, not the last token (which is "3.0)", the Guile runtime's
        # own version, wearing a trailing paren).
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", first_line)
        if match:
            return match.group(1)
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return "2.24.0"


def _ly_escape(text: str) -> str:
    """LilyPond string escaping: `"` and `\\` inside a `"..."` literal."""
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def _hoist_fermata(events: List[Dict[str, Any]]) -> None:
    """Give each event the `fermata` bool `_lily_event`/`_mxl_note` both read.

    ⚠️ `voicing.group_chords_in_measure` hoists `articulations`, `ornaments`,
    `slur_states`, `wedge_states` and the tie flags onto the EVENT already —
    see its own docstring — but NOT `fermata`: a pause is set on the raw
    notehead/rest dict by `staged.export._place_fermatas` (`carrier["fermata"]
    = True`), and BOTH exporters compute `any(h.get("fermata") for h in
    heads)` at render time rather than in the shared grouping step. This does
    the identical hoist so `_lily_event`'s `event.get("fermata")` reads the
    same answer `staged.export._measure_events_xml`'s `ev_fermata` does.
    """
    for ev in events:
        if ev.get("kind") == "rest":
            ev["fermata"] = bool((ev.get("rest") or {}).get("fermata"))
        else:
            ev["fermata"] = any(h.get("fermata")
                                for h in (ev.get("noteheads") or ()))


@dataclass
class _Bar:
    """One bar of one part, already decided into exactly what to render.

    ⚠️ A BAR IS RENDERED, NOT RE-DECIDED, one screen away from where it was
    built — `_collect_bars` is the only place that reads the record; a
    `_Bar` carries plain data so `_render_bar` cannot accidentally ask the
    record a second question the first pass already answered differently.
    """
    kind: str                      # "tacet" | "empty" | "single" | "two_voice"
    meter: Optional[Dict[str, Any]]
    clef: Optional[str] = None
    key: Optional[Dict[str, int]] = None
    events: Optional[List[Dict[str, Any]]] = None
    streams: Optional[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]] = None
    directions: Sequence[Tuple[float, str, str]] = ()
    condensed: bool = False
    #: A fermata standing over a WHOLE-BAR measure rest (`kind == "empty"`
    #: by way of the lone-measure-rest branch below). `_lily_measure_rest`
    #: builds its own bare rest dict from the METER, discarding whatever the
    #: original event carried, so a fermata over that rest has nowhere to
    #: attach unless it is carried here and appended at render time.
    fermata: bool = False


def _tally(events: Sequence[Dict[str, Any]], counters: Dict[str, int],
          condensed: bool) -> None:
    """Count what THIS render wrote, in the same counter names the MusicXML
    exporter uses (`SX.coverage`'s `FAMILIES` table reads them), so the two
    reports are directly comparable family by family.
    """
    for ev in events:
        if ev.get("kind") == "rest":
            if (ev.get("rest") or {}).get("measure_rest"):
                counters["measure_rests_read"] += 1
            else:
                counters["rests"] += 1
            if condensed:
                counters["notes_doubled_to_condensed_slot"] += 1
            if ev.get("fermata"):
                counters["fermatas"] += 1
            for _num, kind in (ev.get("wedge_states") or ()):
                if kind != "stop":
                    counters["wedges"] += 1
            continue
        heads = ev.get("noteheads") or ()
        for head in heads:
            counters["notes"] += 1
            if condensed:
                counters["notes_doubled_to_condensed_slot"] += 1
            if head.get("tied_to_next"):
                counters["ties"] += 1
            # ⚠️⚠️ THE MUSICXML SIDE'S OWN COUNTER, NOT REUSED HERE, FOR A
            # REASON WORTH RECORDING RATHER THAN HIDING. `staged.export.
            # _measure_events_xml` counts `len(head.get("articulations"))`
            # PER HEAD, because `_mxl_note` writes one `<articulations>`
            # block per NOTEHEAD of a chord -- "each member of a chord
            # wears its own staccato", its own comment says. `_legacy.
            # _lily_event`'s chord branch instead appends ONE suffix to the
            # WHOLE `<...>` bracket, built from `event.get("articulations")`
            # -- the DEDUPLICATED, event-level list `voicing.group_chords_
            # in_measure` hoists. So where two or more members of one chord
            # carry the SAME (or overlapping) mark, MusicXML writes several
            # elements and LilyPond writes one -- a real, inherited
            # limitation of the reused renderer, not a counting bug, and
            # `report["lilypond"]["articulation_marks_collapsed_per_chord"]`
            # is where it is surfaced rather than silently swallowed.
            counters["articulation_marks_on_chord_members"] += len(
                head.get("articulations") or ())
        counters["articulations"] += len(ev.get("articulations") or ())
        for orn in (ev.get("ornaments") or ()):
            kind = (orn or {}).get("kind")
            if kind in _legacy._LILY_ORNAMENT:
                counters["ornaments"] += 1
            else:
                # ⚠️ THE ONE MARK `_lily_event` HAS NO SYNTAX FOR. Counted
                # here rather than swallowed inside `_legacy._lily_event`,
                # which silently skips any ornament kind not in its own
                # table — see `_LILY_ONLY_DROPS`.
                counters["ornaments_not_renderable"] += 1
        if ev.get("fermata"):
            counters["fermatas"] += 1
        for _num, kind in (ev.get("slur_states") or ()):
            if kind != "stop":
                counters["slurs"] += 1
        for _num, kind in (ev.get("wedge_states") or ()):
            if kind != "stop":
                counters["wedges"] += 1


def _collect_bars(rec: SX.Record, part: Sequence[SX.StaffRun],
                  offsets: Optional[Dict[Tuple[int, int], int]],
                  spans: Optional[Sequence[Tuple[Tuple[int, int], int]]],
                  meters: Dict[Tuple[int, int], Any],
                  counters: Dict[str, int]
                  ) -> Tuple[List[_Bar], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """This part's bars in DOCUMENT order, plus the two LilyPond "lanes" a
    hairpin plan is built over.

    ⚠️ `_tacet_walk`, NOT A SECOND JOIN. It is `staged.export`'s own function,
    called on the SAME `offsets`/`spans` the MusicXML exporter computed —
    reusing rather than re-deriving is what keeps a tacet span's bar COUNT
    identical between the two files (ROADMAP.md 3.1's own requirement: the
    two note sequences must agree, and a part with a different bar count in
    each file could never satisfy that even if every pitch matched).

    Reach — a LANE is the sequence of events one LilyPond `Voice` context
    will see: `lane0` is every single-voice bar's events plus every
    two-voice bar's FIRST stream, `lane1` is every two-voice bar's SECOND
    stream. `_lily_wedge_plan` is later run once per lane, exactly as
    `tools.omr.export._lily_staff_block` runs it once per lane across a
    whole staff — the difference is that a lane here spans the whole PART,
    not one system.
    """
    bars: List[_Bar] = []
    lane0: List[Dict[str, Any]] = []
    lane1: List[Dict[str, Any]] = []
    segments_on = SX.meter_segments_enabled()
    for sys_key, maybe_run, sys_bars in SX._tacet_walk(part, offsets, spans):
        if maybe_run is None:
            sys_meter = meters.get(sys_key)
            for i in range(sys_bars):
                meter = SX._meter_dict(
                    meter_at(sys_meter, i) if segments_on else sys_meter)
                if meter is None:
                    # ⚠️ NOT WRITTEN, exactly as `staged.export._pad_tacet_
                    # span` refuses: a MusicXML rest -- and a LilyPond one --
                    # needs a LENGTH, and inventing 4.0 quarters for a bar we
                    # never read a meter on is a guess dressed as silence.
                    counters["tacet_bars_not_padded_without_meter"] += 1
                    continue
                bars.append(_Bar("tacet", meter))
                counters["tacet_bars_padded"] += 1
            continue

        run = maybe_run
        key = SX._key_dict(run.fifths)
        condensed = bool(run.condensed_from)
        for i in range(run.n_measures):
            meter = SX._meter_dict(
                meter_at(run.meter, i) if segments_on else run.meter)
            cell = run.cells.get(i)
            directions = tuple(cell.directions) if cell else ()
            events = SX._events(cell)
            _hoist_fermata(events)

            if not events:
                # ⚠️ AN EVENTLESS BAR IS A BAR WE READ NOTHING IN, not a bar
                # we read silence in -- `_lily_measure_rest(None)` falls back
                # to 4.0 quarters exactly as `_mxl_empty_measure` does, so the
                # two files make the identical guess where the meter is
                # unread.
                counters["empty_bars_padded"] += 1
                counters["empty_bars_padded_without_meter"] += (
                    1 if meter is None else 0)
                bars.append(_Bar("empty", meter, run.clef, key,
                                 directions=directions, condensed=condensed))
                continue

            if (len(events) == 1 and events[0].get("kind") == "rest"
                    and (events[0].get("rest") or {}).get("measure_rest")):
                # ⚠️ THE WHOLE-REST-MEANS-THE-BAR CONVENTION, READ OFF THE
                # SAME FLAG `staged.export._rest_xml` READS -- not re-derived
                # from bar SHAPE the way `tools.omr.export._is_lone_measure_
                # rest` does. `adjudicate_duration` / `consequences.size_
                # measure_rest` already decided this rest stands for the
                # bar; a shape heuristic here would be a second, independent
                # opinion the two files could disagree about.
                counters["measure_rests_read"] += 1
                if condensed:
                    counters["notes_doubled_to_condensed_slot"] += 1
                bars.append(_Bar("empty", meter, run.clef, key,
                                 directions=directions, condensed=condensed,
                                 fermata=bool(events[0].get("fermata"))))
                continue

            streams = SX._voice_split(rec, run, i, events)
            if streams is None:
                lane0.extend(events)
                bars.append(_Bar("single", meter, run.clef, key,
                                 events=events, directions=directions,
                                 condensed=condensed))
                continue

            counters["two_voice_bars"] += 1
            v1, v2 = streams
            lane0.extend(v1)
            lane1.extend(v2)
            shared_rests = [e for e in v2 if e.get("kind") == "rest"
                            and any(e is other for other in v1)]
            counters["rests_duplicated_across_voices"] += len(shared_rests)
            counters["fermatas_duplicated_across_voices"] += sum(
                1 for e in shared_rests if e.get("fermata"))
            bars.append(_Bar("two_voice", meter, run.clef, key,
                             streams=(v1, v2), directions=directions,
                             condensed=condensed))
    return bars, lane0, lane1


def _render_bar(bar: _Bar, wedges: Dict[int, str],
                counters: Dict[str, int]) -> str:
    if bar.kind in ("tacet", "empty"):
        rest = _legacy._lily_measure_rest(bar.meter)
        # ⚠️ `_lily_measure_rest` BUILDS A BARE REST DICT FROM THE METER
        # ALONE, so a fermata standing over a whole-bar measure rest (the
        # commonest carrier on an orchestral page, per CLAUDE.md's own
        # `_rest_xml` docstring) has nowhere to attach unless appended here
        # -- `_mxl_note`'s equivalent path takes `fermata=` directly.
        if bar.fermata:
            rest += "\\fermata"
            counters["fermatas"] += 1
        return rest + " |"
    if bar.kind == "single":
        _tally(bar.events, counters, bar.condensed)
        return _legacy._lily_measure(bar.events, wedges) + " |"
    # two_voice
    v1, v2 = bar.streams
    _tally(v1, counters, bar.condensed)
    _tally(v2, counters, bar.condensed)
    inner1 = _legacy._lily_measure(v1, wedges)
    inner2 = _legacy._lily_measure(v2, wedges)
    # ⚠️ PLAIN `<< {...} \\ {...} >>`, NOT `\\voiceOne`/`\\voiceTwo`. Legacy
    # picks the physical voice a lone stream belongs to from its STEM
    # DIRECTION (`_lone_voice_is_the_second`) — and `staged.export._place_
    # notes` never writes `stem_direction` onto a detection at all, so that
    # signal does not exist on this path. `Q.VOICES` names TWO STREAMS, not
    # an up/down convention, and forcing one would be a stem direction this
    # exporter has no evidence for. This is a per-bar polyphony block (valid
    # LilyPond inside a plain sequential expression) rather than the
    # STAFF-WIDE `<< \\new Voice {...} \\new Voice {...} >>` legacy builds,
    # because staged decides two-voice PER BAR (`Q.VOICES` is a `Kind.CELL`
    # verdict) and not per staff.
    return f"<< {{ {inner1} }} \\\\ {{ {inner2} }} >> |"


def _staff_block(rec: SX.Record, part: Sequence[SX.StaffRun], name: str,
                 offsets: Optional[Dict[Tuple[int, int], int]],
                 spans: Optional[Sequence[Tuple[Tuple[int, int], int]]],
                 meters: Dict[Tuple[int, int], Any],
                 counters: Dict[str, int], indent: str = "    ") -> str:
    bars, lane0, lane1 = _collect_bars(rec, part, offsets, spans, meters,
                                       counters)
    wedges: Dict[int, str] = {}
    wedges.update(_legacy._lily_wedge_plan(lane0))
    wedges.update(_legacy._lily_wedge_plan(lane1))

    for bar in bars:
        for _x, kind, _text in bar.directions:
            if kind == "words":
                counters["direction_words_not_renderable"] += 1
            elif kind == "dynamics":
                counters["dynamics_not_renderable"] += 1

    lines = [f'{indent}\\new Staff \\with {{',
            f'{indent}  instrumentName = "{_ly_escape(name)}"',
            f'{indent}}} {{']
    # ⚠️ ROADMAP 2.1b. `\\transposition c,` -- the double bass's own
    # convention, written pitch an OCTAVE above sounding -- is the LilyPond
    # equivalent of `_insert_transpose`'s MusicXML `<transpose>` block
    # (diatonic 0, chromatic 0, octave-change -1). `run.condensed_from` is
    # truthy on EVERY run of a doubled part (`_condensed_double` sets it on
    # the run it builds, and `build()` never mixes a doubled and an ordinary
    # run inside one part), so testing the first run speaks for the whole
    # part.
    if part and part[0].condensed_from:
        lines.append(f'{indent}  \\transposition c,')

    prev_clef: Any = object()
    prev_key: Any = object()
    prev_meter: Any = object()
    for bar in bars:
        if bar.kind != "tacet":
            # ⚠️ `prev` IS NOT TOUCHED FOR A TACET BAR, matching `staged.
            # export._pad_tacet_span`'s own rule exactly: a padded bar states
            # no clef and no key because this part is not printed there, so
            # the next REAL bar's directive change is computed against
            # whatever the LAST REAL bar left standing.
            if bar.clef != prev_clef:
                lines.append(f'{indent}  \\clef '
                            f'{_legacy._clef_to_lily(bar.clef or "treble")}')
                prev_clef = bar.clef
            if bar.key != prev_key:
                lines.append(f'{indent}  \\key '
                            f'{_legacy._lily_key_name(bar.key or {})} \\major')
                prev_key = bar.key
        if bar.meter != prev_meter:
            if bar.meter is not None:
                n = bar.meter.get("numerator", 4)
                d = bar.meter.get("denominator", 4)
                lines.append(f'{indent}  \\time {n}/{d}')
            prev_meter = bar.meter
        lines.append(f'{indent}  ' + _render_bar(bar, wedges, counters))
    lines.append(f'{indent}}}')
    return "\n".join(lines)


def to_lilypond(result: Dict[str, Any], *, out: Optional[str] = None
               ) -> Tuple[str, Dict[str, Any]]:
    """The `.ly` source, and the record of what did not reach it.

    ⚠️⚠️ RETURNS `(str, dict)`, NOT `str` ALONE. The brief for this item
    specified `to_lilypond(result, *, out=None) -> str`; this deviates on
    purpose, for the same reason `staged.export.to_musicxml` returns a
    report beside its text — "a documented drop is counted in a `lilypond`
    block of the report" is a requirement this signature has to carry, and a
    module-level side channel for it would be the exact "value existed and
    nothing read it" shape this project keeps finding. `out`, when given,
    still writes the file, matching the requested convenience.
    """
    rec = SX.Record(result)
    (parts, provenance, dropped, arcs_dropped, artics_dropped,
     fermatas_dropped, ornaments_dropped, notes_dropped_by_system
     ) = SX.build(rec)

    counters: Dict[str, int] = collections.Counter()
    arcs_dropped = collections.Counter(arcs_dropped) + collections.Counter(
        SX._pair_arcs(rec, parts, counters))
    wedges_dropped = collections.Counter(SX._place_wedges(rec, parts, counters))

    offsets, numbering = SX._document_bar_offsets(parts)
    spans = None if offsets is None else SX._spans_from_numbering(numbering)
    meters: Dict[Tuple[int, int], Any] = {}
    for p in parts:
        for r in p:
            meters[(r.page, r.system)] = r.meter

    part_blocks: List[str] = []
    for part in parts:
        name = next((r.name for r in part if r.name), None) or SX._default_name(part)
        part_blocks.append(
            _staff_block(rec, part, name, offsets, spans, meters, counters))

    version = _lilypond_version()
    # ⚠️ THE SAME FALLBACK `_legacy._score_partwise` USES, over the SAME
    # (currently empty, producer-less) `result["source"]` field, so a title
    # that appears on one exported file appears on the other.
    src = (result.get("source") or {}).get("source_pdf")
    work_title = pathlib.Path(src).name if src else "OMR transcription"

    lines = [f'\\version "{version}"', "",
            "\\header {",
            f'  title = "{_ly_escape(work_title)}"',
            "  tagline = ##f",
            "}", "",
            "\\score {",
            "  <<"]
    lines.extend(part_blocks)
    lines.extend(["  >>", "  \\layout { }", "}"])
    text = "\n".join(lines) + "\n"

    report = SX.coverage(result, written=dict(counters))
    report["written"] = dict(counters)
    report["written"]["parts"] = len(parts)
    report["part_join"] = provenance
    report["notes_not_written"] = dict(dropped)
    report["notes_not_written_total"] = sum(dropped.values())
    report["arcs_not_written"] = dict(arcs_dropped)
    report["arcs_not_written_total"] = sum(arcs_dropped.values())
    report["wedges_not_written"] = dict(wedges_dropped)
    report["wedges_not_written_total"] = sum(wedges_dropped.values())
    report["articulations_not_written"] = dict(artics_dropped)
    report["fermatas_not_written"] = dict(fermatas_dropped)
    report["ornaments_not_written"] = dict(ornaments_dropped)
    report["lilypond"] = {
        # ⚠️ THE TWO MARKS `_lily_event` HAS NO SYNTAX FOR, COUNTED AT THE
        # RENDER -- see `_LILY_ONLY_DROPS` and `_tally`/`_staff_block`. Both
        # are documented drops in the LEGACY `to_lilypond` too (its own
        # `_LILY_ORNAMENT` table excludes tremolo; `_lily_staff_block` never
        # emits a dynamic-word directive), so this is not a new limitation,
        # only the first time it is COUNTED rather than merely true.
        "ornaments_not_renderable": int(counters.get("ornaments_not_renderable", 0)),
        "direction_words_not_renderable": int(counters.get("direction_words_not_renderable", 0)),
        "dynamics_not_renderable": int(counters.get("dynamics_not_renderable", 0)),
        # ⚠️⚠️ A THIRD, INHERITED LIMITATION, MEASURED ON THE BREITKOPF
        # SHARED RECORD: `_lily_event` writes ONE articulation suffix per
        # CHORD (from the event-level deduplicated list), while `_mxl_note`
        # writes one PER NOTEHEAD -- so a chord whose members share a mark
        # collapses in this file where MusicXML's holds several. See
        # `_tally`'s own comment. Positive on Breitkopf (112 MusicXML marks
        # on chord members, 106 event-level marks written here); 0 on every
        # fixture with no such chord.
        "articulation_marks_collapsed_per_chord": max(
            0, int(counters.get("articulation_marks_on_chord_members", 0))
            - int(counters.get("articulations", 0))),
        # ⚠️ NOT a documented drop, and said so explicitly: unlike
        # `tools.omr.export.to_lilypond` (one `\\new Staff` per SYSTEM, so a
        # hairpin or slur crossing a system break has nowhere to live), this
        # module's staff spans the whole PART, and `_pair_arcs`/`_place_
        # wedges` already merge across a system break for MusicXML -- the
        # same merged `slur_states`/`wedge_states` reach this renderer too.
        "cross_system_arcs_and_wedges": "handled, not dropped -- see module docstring",
        "two_voice_bars": int(counters.get("two_voice_bars", 0)),
        "version": version,
    }
    if out:
        pathlib.Path(out).write_text(text)
    return text, report


def _report(report: Dict[str, Any]) -> None:
    print("\n── LILYPOND EXPORT ───────────────────────────────────────",
         file=sys.stderr)
    if "written" in report:
        print(f"  written: {report['written']}", file=sys.stderr)
    if report.get("lilypond"):
        print(f"  lilypond-only: {report['lilypond']}", file=sys.stderr)
    if report.get("notes_not_written_total"):
        print(f"  ⚠️ notes the record holds and the file does not: "
              f"{report['notes_not_written_total']} "
              f"{report['notes_not_written']}", file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("staged_json", help="a `python3 -m tools.omr.staged --out` file")
    ap.add_argument("--out", default=None, help="write the .ly here")
    ap.add_argument("--coverage", default=None, help="write the report here")
    args = ap.parse_args(argv)

    result = json.loads(pathlib.Path(args.staged_json).read_text())
    text, report = to_lilypond(result)
    if args.out:
        pathlib.Path(args.out).write_text(text)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    if args.coverage:
        pathlib.Path(args.coverage).write_text(json.dumps(report, indent=2,
                                                          default=str))
        print(f"wrote {args.coverage}", file=sys.stderr)
    _report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
