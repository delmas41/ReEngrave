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
    #: ROADMAP 3.5. None for a bar we READ as silent -- a TACET bar, or the
    #: lone-measure-rest branch below (a DECIDED whole-bar rest; the
    #: control this roadmap item names). One of `SX.UNREAD_BAR_MARK_WORDS`'s
    #: keys for a bar this reader REFUSES to vouch for: `_render_bar` reads
    #: it to colour the rest and stamp the naming word above the staff, the
    #: SAME table `staged.export._marked_empty_measure` reads for MusicXML,
    #: so the two files can never print a different word for one bar.
    reason: Optional[str] = None
    #: ROADMAP 2.12k. True on the ONE bar (first staff of the system only --
    #: `SX._meter_return_marker`'s own gate) where a corroborated cautionary
    #: confirmed a printed meter change this system's own bars could not
    #: sustain, and whose printed RETURN was never read. Kept apart from
    #: `reason` on purpose: this bar is `"single"` or `"two_voice"`, never
    #: `"empty"` -- it is NOT a bar this reader refuses to vouch for, its
    #: notes are written exactly as read (CLAUDE.md rule 8: cannot-tell is
    #: never converted into an answer, including "empty").
    meter_return: bool = False


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
                  counters: Dict[str, int],
                  divisions: int
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

    ⚠️⚠️ ROADMAP 3.5, AND IT WAS FOUND HANDING THIS BRIEF: before this,
    NOTHING in this module read `staged.export._bar_holds_out` at all --
    roadmap 2.8's hold-out existed only on the MusicXML side, so a bar whose
    durations do not add up to the meter was written here as its own
    (possibly wrong) notes, unmarked, the exact gap this roadmap item exists
    to close. `divisions` (`SX._divisions(parts)`, the SAME function and the
    SAME `parts` the MusicXML exporter calls it over) exists ONLY so this
    arithmetic check can share MusicXML's ruler; it names no duration in the
    `.ly` text LilyPond itself never needs one.

    ⚠️ `in_force` IS THE LILYPOND TWIN OF `_part_xml`'s OWN VARIABLE: the
    meter the ASSEMBLED SCORE is currently declaring, which a bar whose own
    system never settled one is judged and SIZED against -- never the 4.0
    fallback `_lily_measure_rest(None)`/`_mxl_empty_measure(None, ...)` both
    reach for. It is updated on EVERY bar (tacet included: a part's leading
    system can be tacet, and `_staff_block` writes `\\time` for a tacet bar
    exactly as it does for a real one), never only where the emitted
    `\\time` actually changes -- the two are equivalent in the end (a
    `\\time` re-stated at an unchanged value is silent noise, never a wrong
    answer) and this is the simpler rule to read back.
    """
    bars: List[_Bar] = []
    lane0: List[Dict[str, Any]] = []
    lane1: List[Dict[str, Any]] = []
    in_force: Optional[Dict[str, Any]] = None
    for sys_key, maybe_run, sys_bars in SX._tacet_walk(part, offsets, spans):
        if maybe_run is None:
            sys_meter = meters.get(sys_key)
            for i in range(sys_bars):
                meter = SX._meter_dict(meter_at(sys_meter, i))
                if meter is None:
                    # ⚠️ NOT WRITTEN, exactly as `staged.export._pad_tacet_
                    # span` refuses: a MusicXML rest -- and a LilyPond one --
                    # needs a LENGTH, and inventing 4.0 quarters for a bar we
                    # never read a meter on is a guess dressed as silence.
                    counters["tacet_bars_not_padded_without_meter"] += 1
                    continue
                bars.append(_Bar("tacet", meter))
                counters["tacet_bars_padded"] += 1
                in_force = meter
            continue

        run = maybe_run
        key = SX._key_dict(run.fifths)
        condensed = bool(run.condensed_from)
        # ⚠️ ROADMAP 2.12k. Computed ONCE per run, the SAME call MusicXML's
        # `_part_xml` makes -- `None` on every staff but the system's own
        # first and on every system whose meter was not abstained this way.
        meter_return_cell = SX._meter_return_marker(rec, run)
        for i in range(run.n_measures):
            meter = SX._meter_dict(meter_at(run.meter, i))
            # ⚠️⚠️ ROADMAP 2.8/3.5: THE METER A READER OF THIS FILE SEES, not
            # always the one this bar's own system filed -- see the
            # docstring's `in_force` paragraph. Computed BEFORE the branches
            # below so every one of them judges and sizes against the same
            # answer `_part_xml` would.
            judged = meter if meter is not None else in_force
            if meter is not None:
                in_force = meter
            cell = run.cells.get(i)
            directions = tuple(cell.directions) if cell else ()
            events = SX._events(cell)
            _hoist_fermata(events)

            if not events:
                # ⚠️ AN EVENTLESS BAR IS A BAR WE READ NOTHING IN, not a bar
                # we read silence in. Sized by `judged`, NOT `meter` --
                # `_lily_measure_rest(None)` falls back to 4.0 quarters, and
                # a part whose own system never settled a meter but whose
                # file has already declared 3/4 must not contradict its own
                # declaration by writing a whole rest there (the identical
                # repair 2.8 made on the MusicXML side).
                counters["empty_bars_padded"] += 1
                counters["empty_bars_padded_without_meter"] += (
                    1 if judged is None else 0)
                bars.append(_Bar("empty", judged, run.clef, key,
                                 directions=directions, condensed=condensed,
                                 reason=SX.UNREAD_BAR_MARK_REASON_UNREAD))
                continue

            # ⚠️⚠️ ROADMAP 2.8/3.5: COMPUTED BEFORE THE LONE-MEASURE-REST
            # CHECK BELOW, AND THAT ORDER IS SAFE RATHER THAN INCIDENTAL.
            # `_bar_holds_out` treats a lone measure rest as automatically
            # filling the bar (CLAUDE.md §10: a whole rest means the BAR) —
            # it can never itself be held out — so testing it first cannot
            # change which bars take that branch; it only adds the ONE
            # check `_part_xml` already makes for every bar with events,
            # single- or two-voice alike. `streams` is computed once here
            # and reused below rather than asking `_voice_split` twice.
            streams = SX._voice_split(rec, run, i, events)
            held = SX._bar_holds_out(events, streams, divisions, judged)
            if held is not None:
                # ⚠️ THE SAME BRANCH SHAPE AS THE EVENTLESS CASE ABOVE, AND
                # FOR THE SAME REASON (CLAUDE.md rule 8): a bar we could not
                # read to its meter is a bar we could not read. Nothing pads,
                # trims or re-times it.
                counters["bars_held_out_sum"] += 1
                if condensed:
                    # ⚠️ MIRRORS `staged.export`'s own condensed case: a
                    # doubled Contrabass copy holds ink the log recorded
                    # once, so counting a second refusal for it would charge
                    # the balance for a row that does not exist.
                    counters["bars_held_out_sum_on_a_doubled_staff"] += 1
                else:
                    counters["notes_held_out_sum"] += SX._bar_event_rows(events)
                bars.append(_Bar("empty", judged, run.clef, key,
                                 directions=directions, condensed=condensed,
                                 reason=SX._BAR_SUM_REFUSAL))
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

            # ⚠️ `streams` IS ALREADY COMPUTED, ABOVE, FOR THE HOLD-OUT CHECK
            # -- reused here rather than asking `_voice_split` a second time
            # over the same bar.
            # ⚠️ ROADMAP 2.12k. `is` comparison against `None`, not truthy --
            # cell 0 must be able to carry the marker too if a future rule
            # ever names it (`METER_RETURN_MARK_CELL` is 1 today, not 0, but
            # nothing here should assume that).
            meter_return = (meter_return_cell is not None
                           and i == meter_return_cell)
            if meter_return:
                counters["meter_returns_not_read"] += 1

            if streams is None:
                lane0.extend(events)
                bars.append(_Bar("single", meter, run.clef, key,
                                 events=events, directions=directions,
                                 condensed=condensed,
                                 meter_return=meter_return))
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
                             condensed=condensed, meter_return=meter_return))
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
        if bar.reason is not None:
            # ⚠️⚠️ ROADMAP 3.5. THE MUSICXML TWIN: `staged.export.
            # _marked_empty_measure` colours the `<note>` and prepends a
            # `<direction>`; this colours the REST GROB and appends a
            # `^\markup` naming the same word, off the SAME table
            # (`SX.UNREAD_BAR_MARK_WORDS`) so the two files can never
            # disagree on the wording. `_lily_measure_rest` can return
            # EITHER a plain rest ("r2.", the `Rest` grob) or LilyPond's own
            # multi-measure notation ("R1*5/4", a DIFFERENT `MultiMeasureRest`
            # grob) depending on whether the bar's length reduces to a single
            # dotted value -- overriding the wrong one is silently a no-op,
            # so which grob applies is read off the token itself rather than
            # guessed from the meter a second time. CONVENTION ASSUMED: `red`
            # approximates MusicXML's `#D00000`, and Sean may rename either.
            grob = "MultiMeasureRest" if rest.startswith("R") else "Rest"
            word = SX.UNREAD_BAR_MARK_WORDS.get(bar.reason, bar.reason)
            counters["unread_bar_marks_written"] += 1
            return (f"\\once \\override {grob}.color = #red "
                   f'{rest}^\\markup {{ "{_ly_escape(word)}" }} |')
        return rest + " |"
    prefix = _meter_return_prefix(bar, counters)
    if bar.kind == "single":
        _tally(bar.events, counters, bar.condensed)
        return prefix + _legacy._lily_measure(bar.events, wedges) + " |"
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
    return f"{prefix}<< {{ {inner1} }} \\\\ {{ {inner2} }} >> |"


def _meter_return_prefix(bar: _Bar, counters: Dict[str, int]) -> str:
    """ROADMAP 2.12k's marker, or `""`.

    ⚠️ `\\mark \\markup {...}`, NOT `^\\markup` ATTACHED TO A NOTE. This bar's
    own notes are written exactly as read (`_render_bar`'s `"single"`/
    `"two_voice"` branches, never `_lily_measure_rest`) -- there is no rest
    token to hang a postfix `^` marking off, and `bar.events`/`bar.streams`
    are `_legacy._lily_measure`'s own frozen renderer's business, not this
    module's to splice into. `\\mark` is a complete, self-contained musical
    event that reads above the staff at the point it is written -- LilyPond's
    own rehearsal-mark idiom -- so it is simply PREPENDED, exactly like
    `\\once \\override ... .color` is for the empty-bar branch above, and
    needs nothing from the bar's own rendered content.
    """
    if not bar.meter_return:
        return ""
    word = SX.UNREAD_BAR_MARK_WORDS[SX.METER_RETURN_NOT_READ_REASON]
    counters["meter_returns_not_read_written"] += 1
    return f'\\mark \\markup {{ \\with-color #red "{_ly_escape(word)}" }} '


def _staff_block(rec: SX.Record, part: Sequence[SX.StaffRun], name: str,
                 offsets: Optional[Dict[Tuple[int, int], int]],
                 spans: Optional[Sequence[Tuple[Tuple[int, int], int]]],
                 meters: Dict[Tuple[int, int], Any],
                 counters: Dict[str, int], divisions: int,
                 indent: str = "    ") -> str:
    bars, lane0, lane1 = _collect_bars(rec, part, offsets, spans, meters,
                                       counters, divisions)
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
     fermatas_dropped, ornaments_dropped, notes_dropped_by_system,
     _dot_role_report) = SX.build(rec)

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
    # ⚠️⚠️ ROADMAP 2.8/3.5: THE SAME RULER THE MUSICXML EXPORTER USES, over
    # the SAME `parts` -- `_divisions` is a pure function of the document's
    # own tuplet ratios, so calling it a second time here can never disagree
    # with `to_musicxml`'s own value. LilyPond's own duration syntax never
    # reads this number; it exists only so `_bar_holds_out`'s integer
    # arithmetic has one to share.
    divisions = SX._divisions(parts)

    part_blocks: List[str] = []
    for part in parts:
        name = next((r.name for r in part if r.name), None) or SX._default_name(part)
        part_blocks.append(
            _staff_block(rec, part, name, offsets, spans, meters, counters,
                        divisions))

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
    # ⚠️⚠️ ROADMAP 3.5, THE LILYPOND TWIN OF `staged.export.to_musicxml`'s
    # OWN `report["unread_bar_marks"]`. `held_out_unread_mark` is not wired
    # here (roadmap 2.4c's hold-out is OFF everywhere,
    # `SX.UNREAD_MARK_HOLDS_OUT` is False, and this brief's own test list
    # never asks for it on this side) -- only the two reasons this module
    # can actually produce are summed. `written` is `_render_bar`'s own
    # count of bars it actually coloured, asserted equal to the reasons
    # summed so a marking bug cannot silently miss or double-mark a bar.
    report["unread_bar_marks"] = {
        "words": dict(SX.UNREAD_BAR_MARK_WORDS),
        "color": SX.UNREAD_BAR_MARK_COLOR,
        "unread": int(counters.get("empty_bars_padded", 0)),
        "held_out_sum": int(counters.get("bars_held_out_sum", 0)),
        "written": int(counters.get("unread_bar_marks_written", 0)),
    }
    _ubm = report["unread_bar_marks"]
    _ubm_expected = _ubm["unread"] + _ubm["held_out_sum"]
    if _ubm["written"] != _ubm_expected:
        raise SX.Unbalanced(
            "lilypond unread-bar marks written (%d) do not equal unread "
            "(%d) + held-out-by-sum (%d) = %d -- a bar was refused without "
            "being marked, or marked without being refused" % (
                _ubm["written"], _ubm["unread"], _ubm["held_out_sum"],
                _ubm_expected))
    report["bars_held_out_sum"] = {
        "bars": int(counters.get("bars_held_out_sum", 0)),
        "bars_on_a_doubled_staff": int(
            counters.get("bars_held_out_sum_on_a_doubled_staff", 0)),
        "noteheads_and_rests": int(counters.get("notes_held_out_sum", 0)),
    }
    # ⚠️ ROADMAP 2.12k, THE LILYPOND TWIN OF `staged.export.to_musicxml`'s
    # OWN `report["meter_returns_not_read"]`. DELIBERATELY NOT FOLDED INTO
    # `unread_bar_marks` ABOVE, for the identical reason: this bar is not one
    # this file emptied, so it does not belong in that equality. `written` is
    # `_meter_return_prefix`'s own count of bars it actually prefixed,
    # asserted equal to `_collect_bars`'s own count of bars it found this
    # true of, so a marking bug here cannot silently miss or double-mark one
    # either.
    _mrn_found = int(counters.get("meter_returns_not_read", 0))
    _mrn_written = int(counters.get("meter_returns_not_read_written", 0))
    if _mrn_written != _mrn_found:
        raise SX.Unbalanced(
            "lilypond meter-return marks written (%d) do not equal bars "
            "found (%d) -- a bar was found without being marked, or marked "
            "without being found" % (_mrn_written, _mrn_found))
    report["meter_returns_not_read"] = _mrn_found
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

    from .record_io import load_record
    result = load_record(args.staged_json)
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
