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
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import export as _legacy
from . import export as SX
from .record import Q, meter_at

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


#: ROADMAP 2.125 (Sean 2026-10-14 "another that does 24 and 25"), DEFAULT OFF.
#: A decided whole-bar rest on a bar whose OWN system declared no meter was
#: sized by that bar's own `meter` (None -> `_lily_measure_rest`'s 4.0-quarter
#: fallback, `r1`), not by the meter IN FORCE (`judged`) the way every other
#: branch here and the MusicXML twin size it. In 6/8 or 3/4 `r1` overflows the
#: bar: LilyPond reports `barcheck failed` there and `mid-measure time
#: signature without \partial` at the next `\time`, and every later barline
#: of that staff is out of step (Brahms 20261013: 199 + 120 of 445 warnings;
#: the red brackets caused none). ON (default, Sean 2026-10-14) writes `r2.` where 6/8 is in force.
CARRIED_METER_REST_ENV = "OMR_LILY_CARRIED_METER_REST"


def carried_meter_rest_enabled() -> bool:
    """Default ON (Sean 2026-10-14): an explicit off-word turns it off."""
    return os.environ.get(CARRIED_METER_REST_ENV, "").strip().lower() not in (
        "0", "false", "no", "off")


@dataclass
class _Bar:
    """One bar of one part, already decided into exactly what to render.

    ⚠️ A BAR IS RENDERED, NOT RE-DECIDED, one screen away from where it was
    built — `_collect_bars` is the only place that reads the record; a
    `_Bar` carries plain data so `_render_bar` cannot accidentally ask the
    record a second question the first pass already answered differently.
    """
    kind: str            # "tacet" | "empty" | "single" | "two_voice" | "partial"
    meter: Optional[Dict[str, Any]]
    clef: Optional[str] = None
    key: Optional[Dict[str, int]] = None
    events: Optional[List[Dict[str, Any]]] = None
    streams: Optional[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]] = None
    #: ROADMAP 2.117 (`kind == "partial"`): per voice, a list of pieces, each
    #: `("events", [event, ...])` or `("gap", lilypond_text)`.
    pieces: Optional[List[List[Tuple[str, Any]]]] = None
    #: `(page, system, staff, cell)` of a partial bar, for the report/crops.
    where: Optional[Tuple[int, int, int, int]] = None
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


def _lily_gap_text(gap_units: int, divisions: int,
                   word: Optional[str] = None) -> str:
    """The unread span: an invisible skip of its length under a red `unread`
    bracket (a text spanner) -- NO rest glyph (rule 8; Sean 2026-10-14). The
    zero-length skip ends the spanner at the span's end, even at the barline."""
    return _lily_gap_text_quarters(Fraction(gap_units, divisions), word)


def _lily_gap_text_quarters(quarters: Fraction,
                            word: Optional[str] = None) -> str:
    frac = Fraction(quarters) / 4
    dur = ("%d" % frac.numerator if frac.denominator == 1
           else "%d/%d" % (frac.numerator, frac.denominator))
    word = word or SX.UNREAD_BAR_MARK_WORDS[SX._GAP_REFUSAL]
    tick = "\\markup { \\with-color #red \\draw-line #'(0 . -0.9) } "
    return (
        "\\once \\override TextSpanner.style = #'line "
        "\\once \\override TextSpanner.color = #red "
        "\\once \\override TextSpanner.direction = #UP "
        "\\once \\override TextSpanner.bound-details.left.text = " + tick
        + "\\once \\override TextSpanner.bound-details.right.text = " + tick
        + "\\once \\override TextSpanner.bound-details.left-broken.text = ##f "
        "s1*%s\\startTextSpan^\\markup { \\with-color #red \"%s\" } "
        "s1*0\\stopTextSpan" % (dur, _ly_escape(word)))


#: ROADMAP 2.109. The LilyPond twin of the marks the MusicXML carries. Every
#: mark is counted on BOTH sides of a ledger (`report["marks_ledger"]`):
#: `in_musicxml` is what `staged.export.to_musicxml` writes for the same bars
#: (one `<articulations>` child per HEAD, merged with the 2.12c dot-role
#: staccato; one `<dynamics>` per decided/guessed dynamic), `written` is
#: MEASURED off the `.ly` text actually produced, and `dropped` names every
#: remainder by reason. `_assert_ledger` raises `Unbalanced` otherwise.
_ARTIC_TOKEN = re.compile(r"-[.!>^-]")
_DYN_LETTERS = frozenset("fmprsz")


def _assert_ledger(family: str, led: Dict[str, Any]) -> None:
    dropped = sum(led["dropped"].values())
    if led["in_musicxml"] != led["written"] + dropped:
        raise SX.Unbalanced(
            "lilypond %s ledger: %d in the MusicXML, %d written and %d "
            "dropped (%s) -- a mark went nowhere" % (
                family, led["in_musicxml"], led["written"], dropped,
                led["dropped"]))


def _ledger(counters: Dict[str, int], family: str) -> Dict[str, Any]:
    pre = family + "_"
    return {
        "in_musicxml": int(counters.get(pre + "in_musicxml", 0)),
        "written": int(counters.get(pre + "written", 0)),
        "dropped": {k.split(":", 1)[1]: int(v) for k, v in counters.items()
                    if k.startswith(pre + "dropped:") and v},
    }


def _merge_dot_role_marks(events: Sequence[Dict[str, Any]]) -> None:
    """Put each head's 2.12c dot-role staccato (`head["dot_role_articulations"]`)
    on the EVENT's `articulations`, which is the only list `_lily_event` reads.

    ⚠️ `voicing.group_chords_in_measure` hoists `head["articulations"]` only;
    `staged.export._merged_articulations` merges the dot-role list at the
    point the MusicXML is written, so the same merge is made here, where the
    LilyPond is. `_lily_artic_event_level` keeps the PRE-merge count so
    `counters["articulations"]` keeps meaning what it always meant.
    """
    for ev in events:
        if ev.get("kind") == "rest":
            continue
        marks = list(ev.get("articulations") or ())
        ev["_lily_artic_event_level"] = len(marks)
        for head in ev.get("noteheads") or ():
            for k in head.get("dot_role_articulations") or ():
                if k not in marks:
                    marks.append(k)
        if marks:
            ev["articulations"] = marks


def _note_unwritten_marks(counters: Dict[str, int], held: Dict[str, int],
                          reason: str) -> None:
    """Articulation marks of events this file does NOT write as music
    (`SX._held_bar_marks`, the MusicXML side's own count), on the ledger."""
    n = int(held.get("articulations", 0)) + int(
        held.get("dot_role_articulations", 0))
    counters["articulations_in_musicxml"] += n
    counters["articulations_dropped:" + reason] += n


def _head_mark_count(ev: Dict[str, Any]) -> int:
    """What MusicXML writes for this event: one element per mark per HEAD."""
    return sum(len(SX._merged_articulations(h) or ())
               for h in (ev.get("noteheads") or ()))


def _dyn_token(word: str, guessed: bool = False,
               script_ok: bool = True) -> Optional[str]:
    """LilyPond for one dynamic word, or None where it cannot be spelled.

    ⚠️ `script_ok` False once the event already carries a dynamic SCRIPT: two
    on one moment make LilyPond warn `conflict with event:
    absolute-dynamic-event` and DISCARD one (Brahms: 14 pairs, 28 warnings),
    so the later ones are written as a `\\dynamic` markup -- the same letters,
    not discarded."""
    if script_ok and word in _legacy._DYNAMIC_ELEMENTS:
        return ("-\\tweak color #guessedColor " if guessed else "") + "\\" + word
    if word and set(word) <= _DYN_LETTERS:
        inner = "\\dynamic " + word
        if guessed:
            inner = "\\with-color #guessedColor " + inner
        return "-\\markup { %s }" % inner
    return None


def _direction_suffix(directions: Sequence[Tuple[float, str, str]],
                      counters: Dict[str, int], writable: bool,
                      why_not: str = "") -> str:
    """The post-events for a bar's dynamics, counted on the ledger.

    ⚠️ AT THE HEAD OF THE BAR, exactly where MusicXML writes them (a `<direction>`
    at offset 0): the marks carry a PAGE x and the noteheads a canonical one,
    so a finer placement would be a guess. A bar this file does not write as
    music (`writable` False) drops them, by `why_not`, counted.
    """
    out: List[str] = []
    led = "dynamics_"
    scripts = 0

    def drop(reason: str, n: int = 1) -> None:
        counters[led + "dropped:" + reason] += n
        counters["dynamics_not_renderable"] += n

    for _x, kind, text in directions:
        if kind == "words":
            counters["direction_words_not_renderable"] += 1
            continue
        if kind == "dynamics_guess":
            payload = json.loads(text)
            counters[led + "in_musicxml"] += 1
            if not writable:
                drop(why_not)
                counters["guessed_dynamics_not_renderable"] += 1
                continue
            shown = payload["text"]
            if shown == "dyn.":
                out.append('_\\markup { \\with-color #guessedColor '
                           '\\italic "dyn." }')
            else:
                tok = _dyn_token(shown, guessed=True, script_ok=scripts == 0)
                if tok is not None and tok.startswith(("\\", "-\\tweak")):
                    scripts += 1
                if tok is None:
                    drop("dynamic_text_not_spellable")
                    counters["guessed_dynamics_not_renderable"] += 1
                    continue
                out.append(tok)
            counters[led + "written"] += 1
            counters["dynamics"] += 1
            counters["guessed_dynamics"] += 1
            counters["guessed_by_rule:" + payload["guess"]["rule"]] += 1
        elif kind == "marking":
            m = json.loads(text)
            dyns = list(m.get("dynamics") or ())
            counters[led + "in_musicxml"] += len(dyns)
            if not writable:
                drop(why_not, len(dyns))
                counters["direction_words_not_renderable"] += 1
                continue
            word = ('\\italic "%s"' % _ly_escape(m.get("word") or ""))
            ok = [d for d in dyns if d and set(d) <= _DYN_LETTERS]
            for d in dyns:
                if d not in ok:
                    drop("dynamic_text_not_spellable")
            parts = ["\\dynamic " + d for d in ok]
            parts = ([word] + parts) if m.get("word_first", True) else (
                parts + [word])
            out.append("_\\markup { %s }" % " ".join(parts))
            counters["direction_words"] += 1
            counters[led + "written"] += len(ok)
            counters["dynamics"] += len(ok)
        else:
            counters[led + "in_musicxml"] += 1
            if not writable:
                drop(why_not)
                continue
            tok = _dyn_token(str(text), script_ok=scripts == 0)
            if tok is not None and tok.startswith("\\"):
                scripts += 1
            if tok is None:
                drop("dynamic_text_not_spellable")
                continue
            out.append(tok)
            counters[led + "written"] += 1
            counters["dynamics"] += 1
    return "".join(out)


def _tally(events: Sequence[Dict[str, Any]], counters: Dict[str, int],
          condensed: bool) -> None:
    """Count what THIS render wrote, in the same counter names the MusicXML
    exporter uses (`SX.coverage`'s `FAMILIES` table reads them), so the two
    reports are directly comparable family by family.
    """
    for ev in events:
        if ev.get("kind") == "rest":
            SX._count_guess(counters, (ev.get("rest") or {}).get("guess"), True)
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
            SX._count_guess(counters, head.get("guess"), False)
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
        counters["articulations"] += ev.get(
            "_lily_artic_event_level", len(ev.get("articulations") or ()))
        # ROADMAP 2.109: the marks ledger, per rendered event.
        _heads_marks = _head_mark_count(ev)
        _event_marks = list(ev.get("articulations") or ())
        _unspelled = [k for k in _event_marks
                      if k not in _legacy._LILY_ARTICULATION]
        counters["articulations_in_musicxml"] += _heads_marks
        counters["articulations_expected_written"] += (
            len(_event_marks) - len(_unspelled))
        counters["articulations_dropped:one_mark_per_chord_in_lilypond"] += (
            _heads_marks - len(_event_marks))
        counters["articulations_dropped:kind_without_lilypond_syntax"] += len(
            _unspelled)
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
                  divisions: int,
                  drops: Optional[Any] = None,
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
    partial_mode = SX.partial_bars_mode()
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
            # ROADMAP 2.98: the same lone-whole-rest-is-the-bar sizing the
            # MusicXML path makes, from the ONE copy, so the two files cannot
            # disagree about which bars were held.
            if events:
                _sized = SX._lone_whole_rest_is_the_bar(events, judged)
                if _sized is not None:
                    events = _sized
            _hoist_fermata(events)
            _merge_dot_role_marks(events)

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
            # ⚠️ ROADMAP 2.117, THE LILYPOND TWIN of `_part_xml`'s branch: the
            # SAME planner (`SX._partial_bar_plan`), so the two files cannot
            # disagree about which bars were kept in part.
            partial = None
            if held is not None and partial_mode != "off" and not condensed:
                partial = SX._partial_bar_plan(
                    events, streams, divisions, judged,
                    cell.unplaced if cell else ())
                counters["partial_plan_ok" if partial["ok"]
                         else "partial_plan_held:" + str(partial["why"])] += 1
            if partial is not None and partial["ok"] and partial_mode == "on":
                counters["bars_partial"] += 1
                counters["notes_in_partial_gaps"] += partial["gap_rows"]
                counters["notes_written_in_partial_bars"] += (
                    partial["written_rows"])
                counters["unread_bar_marks_written"] += 1
                if drops is not None:
                    for _ in range(partial["gap_rows"]):
                        drops(SX._GAP_REFUSAL, run.page, run.system)
                SX._mark_kept_onsets(partial)
                _note_unwritten_marks(
                    counters, SX._held_bar_marks(partial["unwritten"]),
                    "unread_gap_in_partial_bar")
                pieces = []
                for p in partial["streams"]:
                    if p["status"] == "complete":
                        pieces.append([("events", p["events"])])
                        continue
                    pieces.append([
                        ("events", p["pre"]),
                        ("gap", _lily_gap_text(p["gap_units"], divisions)),
                        ("events", p["suf"])])
                    counters["unread_gaps_written"] += 1
                written_by_voice = [
                    [e for kind_, v in pc if kind_ == "events" for e in v]
                    for pc in pieces]
                lane0.extend(written_by_voice[0])
                if len(written_by_voice) > 1:
                    lane1.extend(written_by_voice[1])
                    counters["two_voice_bars"] += 1
                    shared_rests = [
                        e for e in written_by_voice[1]
                        if e.get("kind") == "rest"
                        and any(e is other for other in written_by_voice[0])]
                    counters["rests_duplicated_across_voices"] += len(
                        shared_rests)
                    counters["fermatas_duplicated_across_voices"] += sum(
                        1 for e in shared_rests if e.get("fermata"))
                bars.append(_Bar("partial", meter, run.clef, key,
                                 directions=directions, pieces=pieces,
                                 condensed=condensed,
                                 where=(run.page, run.system, run.staff, i)))
                continue
            if held is not None:
                # ⚠️ THE SAME BRANCH SHAPE AS THE EVENTLESS CASE ABOVE, AND
                # FOR THE SAME REASON (CLAUDE.md rule 8): a bar we could not
                # read to its meter is a bar we could not read. Nothing pads,
                # trims or re-times it.
                counters["bars_held_out_sum"] += 1
                _note_unwritten_marks(counters, SX._held_bar_marks(events),
                                      "bar_held_out_by_sum")
                if condensed:
                    # ⚠️ MIRRORS `staged.export`'s own condensed case: a
                    # doubled Contrabass copy holds ink the log recorded
                    # once, so counting a second refusal for it would charge
                    # the balance for a row that does not exist.
                    counters["bars_held_out_sum_on_a_doubled_staff"] += 1
                else:
                    n_rows = SX._bar_event_rows(events)
                    counters["notes_held_out_sum"] += n_rows
                    # ⚠️ ROADMAP 2.64: THE SAME `_drop` DISCIPLINE THE
                    # MUSICXML RENDER USES (`export._part_xml`, `drops=`).
                    # Until 2026-10-07 the notes a held bar refused were
                    # counted here and reached `dropped` NOWHERE, so this
                    # exporter's `notes_not_written_total` was the
                    # build-time figure alone -- smaller than the MusicXML
                    # sidecar's for the same record -- and no equality
                    # noticed. A caller passing None gets the hold-out
                    # without the accounting, as `_part_xml` says of its
                    # own default: right only for a test not reading it.
                    if drops is not None:
                        for _ in range(n_rows):
                            drops(SX._BAR_SUM_REFUSAL, run.page, run.system)
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
                bars.append(_Bar(
                    "empty",
                    judged if carried_meter_rest_enabled() else meter,
                    run.clef, key, directions=directions,
                    condensed=condensed,
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


_TWEAK = "\\tweak color #guessedColor "


def _retouch_marks(ev: Dict[str, Any], dyn: str,
                   wedges: Dict[int, str]) -> str:
    """`_legacy._lily_event` plus ROADMAP 2.109's two changes to it: the bar's
    dynamics (inserted BEFORE the hairpin suffix -- `c4\\p\\<`, never
    `c4\\<\\p`) and a BLUE articulation where the head carrying it is a
    GUESS (the MusicXML colours the whole `<note>`). An event with neither is
    the legacy text byte for byte."""
    wsuf = wedges.get(id(ev), "")
    marks = [k for k in (ev.get("articulations") or ())
             if k in _legacy._LILY_ARTICULATION]
    guessed = any(h.get("guess") for h in (ev.get("noteheads") or ())
                  if SX._merged_articulations(h))
    if not marks or not guessed or ev.get("kind") == "rest":
        if not dyn:
            return _legacy._lily_event(ev, wedges)
        return _legacy._lily_event(ev, None) + dyn + wsuf
    core = _legacy._lily_event(ev, None)
    bare = _legacy._lily_event(dict(ev, articulations=[]), None)
    i = 0
    while i < len(bare) and core[i] == bare[i]:
        i += 1
    a_len = len(core) - len(bare)
    plain = "".join(_legacy._LILY_ARTICULATION[k] for k in marks)
    if a_len != len(plain) or core[i:i + a_len] != plain:
        return core + dyn + wsuf
    blue = "".join("-\\tweak color #guessedColor " + _legacy._LILY_ARTICULATION[k]
                   for k in marks)
    return core[:i] + blue + core[i + a_len:] + dyn + wsuf


def _lily_event_marked(ev: Dict[str, Any], wedges: Dict[int, str],
                       dyns: Optional[Dict[int, str]] = None,
                       counters: Optional[Dict[str, int]] = None) -> str:
    """`_legacy._lily_event`, with a GUESSED symbol drawn in the guess colour.

    ROADMAP 2.103. The frozen legacy renderer is called UNCHANGED and its
    text is only prefixed: a rest takes `\\once \\override Rest.color`, a
    single note `\\tweak color` (which reaches the NoteHead only), and a
    chord tweaks just the GUESSED heads inside the `<...>`, so a read head
    beside a guessed one stays black. A READ event returns the legacy text
    byte for byte.
    """
    text = _retouch_marks(ev, (dyns or {}).get(id(ev), ""), wedges)
    if counters is not None:
        counters["articulations_written"] += len(_ARTIC_TOKEN.findall(
            text.replace((dyns or {}).get(id(ev), "") or "\0", "", 1)))
    if ev.get("kind") == "rest":
        if (ev.get("rest") or {}).get("guess"):
            return "\\once \\override Rest.color = #guessedColor " + text
        return text
    heads = [h for h in (ev.get("noteheads") or ())
             if _legacy._pitch_to_lily(h["pitch"]) is not None]
    if not any(h.get("guess") for h in heads) or text.startswith("r"):
        return text
    if len(heads) == 1:
        return _TWEAK + text
    close = text.index(">")
    toks = text[1:close].split(" ")
    if len(toks) != len(heads):
        return text
    toks = [(_TWEAK + t) if h.get("guess") else t for t, h in zip(toks, heads)]
    return "<" + " ".join(toks) + text[close:]


def _lily_measure_marked(events: List[Dict[str, Any]],
                         wedges: Dict[int, str],
                         dyns: Optional[Dict[int, str]] = None,
                         counters: Optional[Dict[str, int]] = None) -> str:
    """`_legacy._lily_measure` with `_lily_event_marked` -- the same tuplet
    run walk, the same join. Equal to the legacy text where nothing is
    guessed."""
    runs = {first: (last, ratio)
            for first, last, ratio in _legacy._tuplet_runs(events)}
    out: List[str] = []
    i = 0
    while i < len(events):
        run = runs.get(i)
        if run is None:
            out.append(_lily_event_marked(events[i], wedges, dyns, counters))
            i += 1
            continue
        last, ratio = run
        inner = " ".join(_lily_event_marked(ev, wedges, dyns, counters)
                         for ev in events[i:last + 1])
        out.append(f"\\tuplet {ratio['actual']}/{ratio['normal']} {{ {inner} }}")
        i = last + 1
    return " ".join(out)


def _render_bar(bar: _Bar, wedges: Dict[int, str],
                counters: Dict[str, int]) -> str:
    # ROADMAP 2.109: the bar's dynamics, once, counted on the ledger. Written
    # on the first event of a bar this file writes as music (or on a decided
    # whole-bar rest), dropped -- by name -- from a bar it marks unread.
    if bar.kind in ("single", "two_voice"):
        dyn = _direction_suffix(bar.directions, counters, True)
    elif bar.kind == "empty" and bar.reason is None:
        dyn = _direction_suffix(bar.directions, counters, True)
    elif bar.kind == "partial":
        dyn = _direction_suffix(bar.directions, counters, False,
                                "bar_partly_unread")
    else:
        dyn = _direction_suffix(bar.directions, counters, False,
                                "bar_unread_or_held_out")
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
        rest += dyn
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
            # ⚠️ SEAN, 2026-10-14 (ROADMAP 2.117): *"use the bracket for held
            # bars too"* -- an invisible skip of the bar's length under a red
            # text-spanner bracket, NO rest glyph (a rest, even red, reads as
            # silence). The rest token above only sized the bar.
            word = SX.UNREAD_BAR_MARK_WORDS.get(bar.reason, bar.reason)
            counters["unread_bar_marks_written"] += 1
            beats = Fraction(_legacy._measure_rest_beats(bar.meter)
                             ).limit_denominator(64)
            return _lily_gap_text_quarters(beats, word) + " |"
        return rest + " |"
    prefix = _meter_return_prefix(bar, counters)
    if bar.kind == "partial":
        voices = []
        for pc in bar.pieces:
            txt = []
            for kind_, v in pc:
                if kind_ == "gap":
                    txt.append(v)
                elif v:
                    _tally(v, counters, bar.condensed)
                    txt.append(_lily_measure_marked(v, wedges, None, counters))
            voices.append(" ".join(txt))
        if len(voices) == 1:
            return prefix + voices[0] + " |"
        return f"{prefix}<< {{ {voices[0]} }} \\\\ {{ {voices[1]} }} >> |"
    if bar.kind == "single":
        _tally(bar.events, counters, bar.condensed)
        return prefix + _lily_measure_marked(
            bar.events, wedges, {id(bar.events[0]): dyn}, counters) + " |"
    # two_voice
    v1, v2 = bar.streams
    _tally(v1, counters, bar.condensed)
    _tally(v2, counters, bar.condensed)
    inner1 = _lily_measure_marked(v1, wedges, {id(v1[0]): dyn}, counters)
    inner2 = _lily_measure_marked(v2, wedges, None, counters)
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
                 indent: str = "    ", drops: Optional[Any] = None) -> str:
    bars, lane0, lane1 = _collect_bars(rec, part, offsets, spans, meters,
                                       counters, divisions, drops=drops)
    wedges: Dict[int, str] = {}
    wedges.update(_legacy._lily_wedge_plan(lane0))
    wedges.update(_legacy._lily_wedge_plan(lane1))

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
    # ⚠️ ROADMAP 2.64. `dropped` arrives from `build` as the build-time
    # refusals; the render adds the bar-sum hold-outs through `_drop_at_
    # render`, by reason AND by system at once, exactly as `to_musicxml`
    # does -- and the same two equalities are asserted below. Until
    # 2026-10-07 this exporter reported the build-time figure as if it were
    # the whole, and asserted no notes balance at all.
    dropped = collections.Counter(dropped)

    def _drop_at_render(reason: str, page: int, system: int) -> None:
        dropped[reason] += 1
        notes_dropped_by_system.setdefault(
            (page, system), collections.Counter())[reason] += 1

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
                        divisions, drops=_drop_at_render))

    version = _lilypond_version()
    # ⚠️ THE SAME FALLBACK `_legacy._score_partwise` USES, over the SAME
    # (currently empty, producer-less) `result["source"]` field, so a title
    # that appears on one exported file appears on the other.
    src = (result.get("source") or {}).get("source_pdf")
    work_title = pathlib.Path(src).name if src else "OMR transcription"

    n_guessed = int(counters.get("guessed_notes", 0)
                    + counters.get("guessed_rests", 0)
                    + counters.get("guessed_dynamics", 0))
    lines = [f'\\version "{version}"', ""]
    if n_guessed:
        lines += [f"guessedColor = #{SX.GUESS_COLOR_LILY}", ""]
    lines += ["\\header {",
            f'  title = "{_ly_escape(work_title)}"']
    if n_guessed:
        lines.append(
            '  subtitle = "Blue symbols are GUESSED, not read: '
            f'{n_guessed} in this file. Check these first."')
    lines += ["  tagline = ##f",
            "}", "",
            "\\score {",
            "  <<"]
    lines.extend(part_blocks)
    lines.extend(["  >>", "  \\layout { }", "}"])
    text = "\n".join(lines) + "\n"

    report = SX.coverage(result, written=dict(counters))
    report["written"] = dict(counters)
    report["written"]["parts"] = len(parts)
    report["guessed"] = SX.guessed_report(counters)
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
    # ROADMAP 2.109: the marks ledger. `written` is MEASURED off the text.
    # Both families raise `Unbalanced` rather than flag.
    report["marks_ledger"] = {
        "articulations": _ledger(counters, "articulations"),
        "dynamics": _ledger(counters, "dynamics"),
    }
    for _fam, _led in report["marks_ledger"].items():
        _assert_ledger(_fam, _led)
    _artic_expected = int(counters.get("articulations_expected_written", 0))
    if _artic_expected != report["marks_ledger"]["articulations"]["written"]:
        raise SX.Unbalanced(
            "lilypond: %d articulation marks were meant to be written and %d "
            "are in the text" % (
                _artic_expected,
                report["marks_ledger"]["articulations"]["written"]))
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
        "guessed_dynamics_not_renderable": int(
            counters.get("guessed_dynamics_not_renderable", 0)),
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
        "partial": int(counters.get("bars_partial", 0)),
        "written": int(counters.get("unread_bar_marks_written", 0)),
    }
    _ubm = report["unread_bar_marks"]
    _ubm_expected = _ubm["unread"] + _ubm["held_out_sum"] + _ubm["partial"]
    if _ubm["written"] != _ubm_expected:
        raise SX.Unbalanced(
            "lilypond unread-bar marks written (%d) do not equal unread "
            "(%d) + held-out-by-sum (%d) = %d -- a bar was refused without "
            "being marked, or marked without being refused" % (
                _ubm["written"], _ubm["unread"], _ubm["held_out_sum"],
                _ubm_expected))
    report["partial_bars"] = {
        "mode": SX.partial_bars_mode(),
        "written": int(counters.get("bars_partial", 0)),
        "rows_written_in_partial_bars": int(
            counters.get("notes_written_in_partial_bars", 0)),
        "rows_in_gaps": int(counters.get("notes_in_partial_gaps", 0)),
        "unread_gaps": int(counters.get("unread_gaps_written", 0)),
        "planned_ok": int(counters.get("partial_plan_ok", 0)),
        "stay_held_by_reason": {
            k.split(":", 1)[1]: int(v) for k, v in counters.items()
            if k.startswith("partial_plan_held:")},
    }
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
    # ⚠️⚠️ ROADMAP 2.64: THE TWO NOTE EQUALITIES `to_musicxml` ASSERTS,
    # ASSERTED HERE TOO, over the SAME counters and the SAME formula -- a
    # second spelling of either would be a second thing to keep in step.
    # (1) per-system refusals sum to per-reason refusals, after the render;
    # (2) noteheads+rests in the log = written + not-written. `raise`, never
    # a flag: a control nobody consults is not a control (`to_musicxml`'s
    # own words, learnt from `symbol_ledger.coverage_check`).
    report["notes_not_written"] = dict(dropped)
    report["notes_not_written_total"] = sum(dropped.values())
    report["notes_not_written_by_system"] = {
        f"{p}/{s}": dict(c)
        for (p, s), c in sorted(notes_dropped_by_system.items())}
    _by_sys_total = sum(sum(c.values())
                        for c in notes_dropped_by_system.values())
    if _by_sys_total != sum(dropped.values()):
        raise SX.Unbalanced(
            "lilypond: notes refused per system (%d) do not sum to the "
            "per-reason total (%d) after rendering -- a refusal reaches one "
            "counter and not the other" % (_by_sys_total, sum(dropped.values())))
    events_in_log = (len(rec.obs_of(Q.NOTEHEAD_CLASS)) + len(rec.obs_of(Q.REST)))
    # ⚠️ ROADMAP 2.116. The STAGED twin of `staged.export.to_musicxml`'s own
    # `unboxed_placed`: a rest read off unboxed ink (2.99) is placed in a bar
    # and written, but no detector row announced it, so it joins the log side
    # BY NAME. Without it every record holding one raised `Unbalanced` here
    # (20261013-night: 125 on Litolff, 450 on Brahms) while MusicXML balanced.
    unboxed_placed = int(provenance.get("unboxed_rests_placed", 0))
    duplicated = int(counters.get("rests_duplicated_across_voices", 0))
    doubled_to_condensed = int(
        counters.get("notes_doubled_to_condensed_slot", 0))
    written = (int(counters.get("notes", 0)) + int(counters.get("rests", 0))
               + int(counters.get("measure_rests_read", 0)) - duplicated
               - doubled_to_condensed)
    report["balance"] = {
        "events_in_log": events_in_log,
        "unboxed_rests_placed": unboxed_placed,
        "noteheads_in_log": len(rec.obs_of(Q.NOTEHEAD_CLASS)),
        "rests_in_log": len(rec.obs_of(Q.REST)),
        "events_written": written,
        "rests_duplicated_across_voices": duplicated,
        "notes_doubled_to_condensed_slot": doubled_to_condensed,
        "events_not_written": report["notes_not_written_total"],
        "balanced": (events_in_log + unboxed_placed
                     == written + report["notes_not_written_total"]),
    }
    if not report["balance"]["balanced"]:
        raise SX.Unbalanced(
            f"lilypond: {events_in_log} noteheads+rests in the log (+"
            f"{unboxed_placed} read off unboxed ink), {written} "
            f"written and {report['notes_not_written_total']} accounted as "
            f"dropped -- the difference went nowhere. "
            f"{report['notes_not_written']}")
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
