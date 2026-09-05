"""Export transcribe.py JSON to LilyPond (.ly) or MusicXML (.musicxml).

Phase 4d. Reads the structured detection-JSON produced by
`tools.omr.transcribe`, groups noteheads into chords via
`tools.omr.voicing.group_chords_in_measure`, and serializes the resulting
musical events into a notation file the rest of the world can consume.

Two formats are supported:

  * **LilyPond** (`.ly`) — text-based notation language used by the
    ReEngrave web app's existing exporter. Easy to read and edit by
    hand. Render with `lilypond foo.ly` → `foo.pdf`.

  * **MusicXML** (`.musicxml`) — the universal notation interchange
    format. Opens in MuseScore, Sibelius, Dorico, Finale; plays back
    in DAWs that import MusicXML; round-trips through the web app's
    existing LilyPond / PDF pipeline via `musicxml2ly`.

CLI:

    # Transcribe → export to LilyPond:
    python3 -m tools.omr.transcribe score.pdf --pages 0 --out r.json
    python3 -m tools.omr.export r.json --format lilypond --out r.ly

    # Or to MusicXML:
    python3 -m tools.omr.export r.json --format musicxml --out r.musicxml

V1 caveats (documented in tools/omr/README.md):
  - Single voice per staff. Two-voice piano writing is collapsed.
  - Chord grouping by x-position only — no stem-direction inference.
  - Per-measure durations frequently don't sum exactly to the time
    signature (the rhythm detector is approximate).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

from .voicing import group_chords_in_measure, split_events_into_voices
from .rhythm import backfill_page_time_signatures


def _ensure_inferred_time_signatures(result: dict[str, Any]) -> None:
    """Back-fill inferred time signatures onto any measures/staves the OMR
    left as None, so the exporters emit a sensible `\\time` / bar-rest length
    instead of hardcoding 4/4. Idempotent — a result already back-filled by
    transcribe (the normal path) has no nulls left to fill, so this is a
    no-op there; it matters when export runs on a JSON produced before this
    inference existed. Conservative: only fires where a page's meter vote is
    confident (see rhythm.backfill_page_time_signatures)."""
    for page in result.get("pages", []):
        backfill_page_time_signatures(page)


# ---------------------------------------------------------------------------
# Shared duration tables
# ---------------------------------------------------------------------------


# Map our internal duration_type → (LilyPond suffix, MusicXML <type>)
_DURATION_TABLE: dict[str, tuple[str, str]] = {
    "double_whole":     ("\\breve", "breve"),
    "whole":            ("1",       "whole"),
    "half":             ("2",       "half"),
    "quarter":          ("4",       "quarter"),
    "eighth":           ("8",       "eighth"),
    "sixteenth":        ("16",      "16th"),
    "thirty_second":    ("32",      "32nd"),
    "sixty_fourth":     ("64",      "64th"),
    "hundred_twenty_eighth": ("128", "128th"),
}


def _strip_dotted(duration_type: str) -> tuple[str, int]:
    """Pull the dotted_ prefix off so we can look up the base in the
    duration table. Returns (base_type, n_dots_implied_by_prefix).
    """
    if duration_type.startswith("dotted_"):
        return duration_type[len("dotted_"):], 1
    for n in range(2, 5):
        prefix = f"{n}dotted_"
        if duration_type.startswith(prefix):
            return duration_type[len(prefix):], n
    return duration_type, 0


def _duration_to_lily_xml(duration_type: str, dots: int) -> tuple[str, str, int]:
    """Return (lily_suffix, musicxml_type, total_dots).

    THE TWO SOURCES ARE THE SAME FACT, NOT TWO FACTS TO ADD UP. This used to
    sum them, on a stated assumption that "in practice transcribe.py only sets
    ONE source". That assumption stopped being true: `rhythm._name_for_dots`
    builds `duration_type` FROM the dot count, so a dotted quarter arrives as
    `duration_type="dotted_quarter"` AND `dots=1`, and summing wrote a
    DOUBLE-dotted quarter for every single-dotted one.

    Measured on the engraved Brahms 1 fixture: 197 `<dot/>` elements against
    the truth's 116, and 82 of musicdiff's edits were exactly this —
    `pred [D6]4** | gt [D6]4*`, an extra dot on a note that was already right.
    The count LOOKED like under-dotting (108 dotted notes against 126) which is
    why it read as a detection problem for a while; it is neither, it is one
    fact counted twice.

    `max` rather than either source alone, because the Vision OMR path and older
    JSON can populate `dots` with a plain `duration_type`.
    """
    base, prefix_dots = _strip_dotted(duration_type)
    total_dots = max(dots, prefix_dots)
    lily_base, xml_base = _DURATION_TABLE.get(base, ("4", "quarter"))
    return lily_base, xml_base, total_dots


# ---------------------------------------------------------------------------
# Empty-measure padding — time-signature-aware full-measure rests
# ---------------------------------------------------------------------------
#
# Both exporters need to pad a measure with zero resolved events (nothing
# YOLO detected, or nothing survived pitch/rhythm resolution) with a rest
# spanning the whole bar. Sizing that rest to the measure's time signature
# (rather than always assuming 4/4) avoids emitting a bar that's the wrong
# length in 3/4, 6/8, etc.

# duration_type -> un-dotted length in quarter-note beats (mirrors the
# keys of _DURATION_TABLE).
_DURATION_BASE_BEATS: dict[str, float] = {
    "double_whole":            8.0,
    "whole":                   4.0,
    "half":                    2.0,
    "quarter":                 1.0,
    "eighth":                  0.5,
    "sixteenth":               0.25,
    "thirty_second":           0.125,
    "sixty_fourth":            0.0625,
    "hundred_twenty_eighth":   0.03125,
}


def _measure_rest_beats(time_sig: dict[str, Any] | None) -> float:
    """Total quarter-note beats for a rest spanning an entire measure,
    sized to `time_sig`. Falls back to 4.0 (a whole rest) when no time
    signature is known.
    """
    if not time_sig:
        return 4.0
    num = time_sig.get("numerator")
    den = time_sig.get("denominator")
    if not num or not den:
        return 4.0
    return num * 4.0 / den


def _dotted_duration_for_beats(beats: float) -> tuple[str, int] | None:
    """Find a (duration_type, dots) pair whose length equals `beats`
    quarter-note beats, trying 0-2 augmentation dots against each base
    duration. Returns None when no exact match exists — irregular meters
    like 5/4 or 7/8 don't reduce to a single (possibly dotted) note value.
    """
    for duration_type, base_beats in _DURATION_BASE_BEATS.items():
        for dots in (0, 1, 2):
            if abs(base_beats * (2.0 - 2.0 ** -dots) - beats) < 1e-6:
                return duration_type, dots
    return None


def _lily_measure_rest(time_sig: dict[str, Any] | None) -> str:
    """LilyPond text for a rest spanning an entire empty measure, sized to
    `time_sig` (e.g. 3/4 -> 'r2.'). Falls back to the whole rest 'r1' when
    no time signature is known. Meters that don't reduce to a single
    (possibly dotted) note value (5/4, 7/8, ...) use LilyPond's full-
    measure rest 'R' with a duration multiplier over the whole note (e.g.
    'R1*5/4'), which compiles regardless of how the beat count reduces.
    """
    beats = _measure_rest_beats(time_sig)
    fit = _dotted_duration_for_beats(beats)
    if fit is not None:
        duration_type, dots = fit
        return _lily_event({"kind": "rest", "duration_type": duration_type, "dots": dots})
    frac = Fraction(beats).limit_denominator(64) / 4
    if frac.denominator == 1:
        return f"R1*{frac.numerator}"
    return f"R1*{frac.numerator}/{frac.denominator}"


def _mxl_measure_rest(time_sig: dict[str, Any] | None) -> tuple[float, str, int]:
    """(beats, xml_type, dots) for a MusicXML rest spanning an entire
    empty measure, sized to `time_sig`. `beats` (the semantic <duration>
    value) is always exact; `xml_type`/`dots` (the cosmetic <type>/<dot>
    tags) fall back to a plain whole note when the beat count doesn't
    reduce to a single dotted duration (e.g. 5/4) — the <duration> value
    still keeps the measure the correct length either way.
    """
    beats = _measure_rest_beats(time_sig)
    fit = _dotted_duration_for_beats(beats)
    if fit is not None:
        duration_type, dots = fit
        xml_type = _DURATION_TABLE[duration_type][1]
        return beats, xml_type, dots
    return beats, "whole", 0


# ---------------------------------------------------------------------------
# Pitch helpers
# ---------------------------------------------------------------------------


def _parse_pitch(pitch: str) -> tuple[str, str, int] | None:
    """'F#4' → ('F', '#', 4).  'A2' → ('A', '', 2).  Returns None if it
    can't parse.
    """
    if not pitch or pitch[0] not in "ABCDEFG":
        return None
    letter = pitch[0]
    i = 1
    while i < len(pitch) and pitch[i] in "#b":
        i += 1
    accidental = pitch[1:i]
    try:
        octave = int(pitch[i:])
    except ValueError:
        return None
    return letter, accidental, octave


# ---------------------------------------------------------------------------
# LilyPond serialization
# ---------------------------------------------------------------------------


# LilyPond accidental suffixes.
_LILY_ACCIDENTAL = {
    "":   "",
    "#":  "is",
    "##": "isis",
    "b":  "es",
    "bb": "eses",
}

#: `transcribe`'s alteration strings -> the MusicXML `<accidental>` vocabulary.
#:
#: This is the PRINTED GLYPH, not the pitch. `<alter>` inside `<pitch>` already
#: carries what sounds, and the two are independent: a natural has `<alter>0</>`
#: and a drawn natural sign, which is why the element cannot be recovered from
#: the pitch downstream. All 65 accidentals in the benchmark truth are one of
#: the first three; the doubles are here because `_parse_inline_accidental`
#: emits them and a silent drop would be the same bug in miniature.
_MXL_ACCIDENTAL = {
    "#":       "sharp",
    "b":       "flat",
    "natural": "natural",
    "##":      "double-sharp",
    "bb":      "flat-flat",
}


def _pitch_to_lily(pitch: str) -> str | None:
    """'F#4' → "fis'", 'A2' → 'a,', 'C5' → "c''"."""
    parsed = _parse_pitch(pitch)
    if parsed is None:
        return None
    letter, accidental, octave = parsed
    lily_acc = _LILY_ACCIDENTAL.get(accidental, "")
    # LilyPond octave convention: c = C3 ish... actually:
    #   c   = C3
    #   c'  = C4 (middle C)
    #   c'' = C5
    #   c,  = C2
    #   c,, = C1
    # So octave 4 = one apostrophe, 5 = two, 3 = no marks, 2 = one comma, etc.
    if octave >= 3:
        marks = "'" * (octave - 3)
    else:
        marks = "," * (3 - octave)
    return f"{letter.lower()}{lily_acc}{marks}"


def _lily_key_for_sig(sharps: int, flats: int) -> str | None:
    """Map a key signature (count of sharps OR flats) to a LilyPond key.
    Assumes the major-key spelling for the count. Returns None for empty.
    """
    if sharps > 0:
        # Circle of fifths: 1=G, 2=D, 3=A, 4=E, 5=B, 6=F#, 7=C#
        return ["g", "d", "a", "e", "b", "fis", "cis"][sharps - 1]
    if flats > 0:
        # 1=F, 2=Bb, 3=Eb, 4=Ab, 5=Db, 6=Gb, 7=Cb
        return ["f", "bes", "ees", "aes", "des", "ges", "ces"][flats - 1]
    return None  # C major / no signature


def _clef_to_lily(clef: str) -> str:
    """Translate a pitch_resolver clef key to its LilyPond `\\clef` argument.

    pitch_resolver uses "treble_8vb" (suffix style); LilyPond's clef
    names are quoted-string variants like "treble_8" (down an octave)
    or "treble^8" (up an octave). The base clefs need no quoting.
    """
    suffix_map = {
        "_8va": "^8",
        "_8vb": "_8",
        "_15ma": "^15",
        "_15mb": "_15",
    }
    for suffix, lily_suffix in suffix_map.items():
        if clef.endswith(suffix):
            base = clef[: -len(suffix)]
            return f'"{base}{lily_suffix}"'
    return clef


def _lily_slur_suffix(event: dict[str, Any]) -> str:
    """`(` / `)` for a note that opens or closes a slur.

    LilyPond needs no help to carry a slur across a barline — `c8( d | e f)`
    is one slur — so the same staff-level pairing that MusicXML uses serves
    here unchanged. Simultaneous slurs are distinguished by `\\=N`, which is
    LilyPond's equivalent of the MusicXML slur number; the common single-slur
    case stays plain `(` … `)`.
    """
    out = ""
    # Stops before starts: a note that ends one slur and begins the next is
    # written `d)(`, closing what arrived before opening what leaves.
    for number, kind in sorted(event.get("slur_states") or [],
                               key=lambda s: (s[1] != "stop", s[0])):
        prefix = "" if number == 1 else f"\\={number}"
        out += prefix + (")" if kind == "stop" else "(")
    return out


#: LilyPond post-events for a hairpin. `\\!` closes either kind.
_LILY_WEDGE = {"crescendo": "\\<", "diminuendo": "\\>"}


def _lily_wedge_plan(lane: list[dict[str, Any]]) -> dict[int, str]:
    """`id(event) -> post-event string` for the hairpins ONE LilyPond voice can
    render.

    LilyPond is stricter than MusicXML here in two ways, and both are enforced
    by dropping rather than by approximating — an unterminated `\\<` is a
    compile-time warning and a hairpin drawn to the wrong place.

    1. **A hairpin lives inside one Voice context.** `annotate_wedges_in_slot`
       already refuses to pair across the transcription's voices, but LilyPond's
       lanes are not those: `_lone_voice_is_the_second` routes a measure's lone
       voice to `\\voiceTwo` when its stems point down, PER MEASURE, so a wedge
       spanning two measures can find its ends in different lanes. Such a wedge
       is dropped, which is why this takes a lane and not a staff.

    2. **One hairpin at a time.** LilyPond has no equivalent of the MusicXML
       `number=` level; a second `\\<` before the first `\\!` is an error. Spans
       are accepted greedily in start order and an overlapping one is dropped.
       Touching is not overlapping: a note that ends one hairpin and begins the
       next takes `\\!\\<`, which is ordinary LilyPond.

    A wedge crossing a SYSTEM break is dropped by construction rather than by
    rule — `to_lilypond` emits one `\\new Staff` per system, so the lane it is
    given never spans one. That is the same limit `annotate_slurs_in_slot`
    records for slurs.
    """
    opens: list[tuple[int, int, str]] = []          # (position, number, kind)
    stops: list[tuple[int, int]] = []               # (position, number)
    for i, event in enumerate(lane):
        for number, kind in (event.get("wedge_states") or []):
            if kind == "stop":
                stops.append((i, number))
            elif kind in _LILY_WEDGE:
                opens.append((i, number, kind))

    used: set[int] = set()
    spans: list[tuple[int, int, str]] = []          # (start, stop, kind)
    for start, number, kind in sorted(opens):
        match = next((j for j, (pos, num) in enumerate(stops)
                      if num == number and pos > start and j not in used), None)
        if match is None:
            continue
        used.add(match)
        spans.append((start, stops[match][0], kind))

    out: dict[int, str] = {}
    starts_at: dict[int, str] = {}
    stops_at: set[int] = set()
    last_end = -1
    for start, stop, kind in sorted(spans):
        if start < last_end:
            continue
        starts_at[start] = _LILY_WEDGE[kind]
        stops_at.add(stop)
        last_end = stop
    for i, event in enumerate(lane):
        # `\\!` before `\\<`: the note closes what arrived before it opens what
        # leaves, the same ordering `_lily_slur_suffix` uses for `)` and `(`.
        suffix = ("\\!" if i in stops_at else "") + starts_at.get(i, "")
        if suffix:
            out[id(event)] = suffix
    return out


def _lily_event(event: dict[str, Any],
                wedges: dict[int, str] | None = None) -> str:
    """Render one chord/rest event in LilyPond syntax.

    Appends `~` to a chord whose `tied_to_next` flag is set — LilyPond
    parses `c4~ c4` as a single sustained half-note worth of c.

    `wedges` is `_lily_wedge_plan`'s answer for the voice this event is being
    rendered into; `None` means no hairpins, which is what every caller outside
    `_lily_staff_block` wants.
    """
    lily_suffix, _, dots = _duration_to_lily_xml(
        event["duration_type"], event.get("dots", 0)
    )
    dot_str = "." * dots
    tie_suffix = "~" if event.get("tied_to_next") else ""
    # A slur closes on the note it reaches and opens after it, so a stop
    # precedes a start on the same note — `sorted` puts "start" first, hence
    # the ordering is handled in `_lily_slur_suffix`.
    slur_suffix = _lily_slur_suffix(event)
    # Articulations attach to the note they follow, and go INSIDE the slur
    # marks — LilyPond wants `c4-.(` not `c4(-.`. A rest carries none: the
    # attach pass only ever gives a mark to a notehead.
    artic_suffix = "".join(_LILY_ARTICULATION[k]
                           for k in (event.get("articulations") or [])
                           if k in _LILY_ARTICULATION)
    # `\fermata` is an articulation in LilyPond and attaches to a rest exactly
    # as it does to a note, which is the case that matters on an orchestral
    # page — the mark usually sits over a whole-bar rest.
    fermata_suffix = "\\fermata" if event.get("fermata") else ""
    # A hairpin is a dynamic mark, so it goes OUTSIDE the slur marks, last of
    # the post-events — `c4-.(\\<`. A rest can carry one: LilyPond attaches
    # `\\<` to a rest happily, and a hairpin over a rest is ordinary printing.
    wedge_suffix = (wedges or {}).get(id(event), "")

    if event["kind"] == "rest":
        return f"r{lily_suffix}{dot_str}{fermata_suffix}{wedge_suffix}"

    # Chord
    pitches = []
    for nh in event["noteheads"]:
        ly = _pitch_to_lily(nh["pitch"])
        if ly is not None:
            # `!` forces the accidental into print where a glyph was READ.
            # LilyPond re-derives most of them from the pitch stream on its
            # own — measured on the fresh benchmark JSONs, 62 of the 65
            # recorded glyphs re-print from pitch alone — but a COURTESY
            # accidental restates what the key signature already implies and
            # is exactly what the derivation drops (the 3: A-flats restating
            # the key on three Brahms staves). The page prints them plain, so
            # `!`, not `?` (which parenthesizes).
            if nh.get("accidental"):
                ly += "!"
            pitches.append(ly)
    if not pitches:
        return f"r{lily_suffix}{dot_str}"  # fallback if all pitches unparsable
    if len(pitches) == 1:
        return (f"{pitches[0]}{lily_suffix}{dot_str}{tie_suffix}"
                f"{artic_suffix}{fermata_suffix}{slur_suffix}{wedge_suffix}")
    return (f"<{' '.join(pitches)}>{lily_suffix}{dot_str}{tie_suffix}"
            f"{artic_suffix}{fermata_suffix}{slur_suffix}{wedge_suffix}")


def _lily_measure(events: list[dict[str, Any]],
                  wedges: dict[int, str] | None = None) -> str:
    """One measure of events as LilyPond, with tuplet runs wrapped.

    `\\tuplet 3/2 { c8 c8 c8 }` — the notes keep their WRITTEN value (`8`),
    which is what `_lily_event` already emits, and the wrapper supplies the
    ratio. Defined here rather than inside `_lily_event` because a tuplet is a
    property of a RUN of events and `_lily_event` renders one.
    """
    runs = {first: (last, ratio) for first, last, ratio in _tuplet_runs(events)}
    out: list[str] = []
    i = 0
    while i < len(events):
        run = runs.get(i)
        if run is None:
            out.append(_lily_event(events[i], wedges))
            i += 1
            continue
        last, ratio = run
        inner = " ".join(_lily_event(ev, wedges) for ev in events[i:last + 1])
        out.append(f"\\tuplet {ratio['actual']}/{ratio['normal']} {{ {inner} }}")
        i = last + 1
    return " ".join(out)


def _lily_measure_spacer(time_sig: dict[str, Any] | None) -> str:
    """An invisible full measure (`s2.`, `s1*5/4`), for the voice of a
    two-voice staff that has no music in this bar.

    A PRINTED rest (`r`/`R`) would put a symbol on the page that the source
    never shows — the bar isn't resting, it simply has one voice — so the
    spacer keeps the voice's timeline aligned while drawing nothing.
    Derived from `_lily_measure_rest` because the duration arithmetic is
    identical and `s` accepts every duration form `r`/`R` does, multiplier
    included.
    """
    rest = _lily_measure_rest(time_sig)
    return "s" + rest[1:]


def _lone_voice_is_the_second(events: list[dict[str, Any]]) -> bool:
    """A single-voice measure on a two-voice staff belongs to \\voiceTwo when
    its stems say so.

    `split_events_into_voices` only splits when BOTH directions appear, so a
    measure where the lower voice plays alone arrives as one voice of
    stem-down chords — and rendering it in \\voiceOne forces its stems up,
    the opposite of the page. All chords must agree; a measure with any
    stem-up, unknown-direction or no chords at all stays in voice 1, which is
    the pre-2026-09-02 routing for everything.
    """
    chords = [e for e in events if e["kind"] == "chord"]
    if not chords:
        return False
    return all(e.get("stem_direction") == "down" for e in chords)


def _lily_staff_block(staff: dict[str, Any], indent: str = "    ") -> str:
    """Render one OMR staff as a LilyPond `\\new Staff { ... }` block.

    If the staff has events with mixed stem directions (both up and
    down on the same measure), emits a `<<` simultaneous-music block
    with `\\new Voice { \\voiceOne ... }` + `\\voiceTwo`.
    """
    clef = staff.get("clef") or "treble"
    # `\clef` is emitted once for the whole staff here, so a leading furniture
    # cell costs LilyPond the clef outright — there is no later measure to
    # recover it the way MusicXML's clef-change does. Same rule, same reason:
    # see `_first_clef_bearing_measure`. `lead == 0` leaves this untouched.
    lead = _first_clef_bearing_measure(staff.get("measures", []))
    if lead:
        clef = staff["measures"][lead].get("clef") or clef
    key_sig = staff.get("key_signature") or {}
    time_sig = staff.get("time_signature")

    lines: list[str] = [f"{indent}\\new Staff {{"]
    lines.append(f"{indent}  \\clef {_clef_to_lily(clef)}")
    lily_key = _lily_key_for_sig(
        key_sig.get("sharps", 0), key_sig.get("flats", 0)
    )
    if lily_key is not None:
        lines.append(f"{indent}  \\key {lily_key} \\major")
    else:
        lines.append(f"{indent}  \\key c \\major")
    if time_sig is not None:
        n = time_sig.get("numerator", 4)
        d = time_sig.get("denominator", 4)
        lines.append(f"{indent}  \\time {n}/{d}")
    else:
        lines.append(f"{indent}  \\time 4/4")

    # Slurs are paired over the whole staff, before any measure is rendered:
    # the arc that crosses a barline is cut in two by the cell boundary and
    # only page coordinates can rejoin it. A hairpin is cut the same way.
    annotate_slurs_in_staff(staff)
    annotate_wedges_in_staff(staff)

    # Decide once for the whole staff whether to render as one-voice
    # or two-voice. Two-voice only if any measure has BOTH stem-up and
    # stem-down chords — otherwise it's overkill.
    needs_two_voices = False
    per_measure_events: list[list[dict[str, Any]]] = []
    per_measure_time_sig: list[dict[str, Any] | None] = []
    for measure in staff.get("measures", []):
        events = group_chords_in_measure(measure.get("detections", []))
        annotate_fermatas(events, measure.get("detections", []))
        per_measure_events.append(events)
        per_measure_time_sig.append(measure.get("time_signature") or time_sig)
        voices = split_events_into_voices(events)
        if len(voices) > 1:
            needs_two_voices = True

    # Which LilyPond lane each measure's events are rendered into, decided ONCE
    # so the hairpin planner can see the same lanes the renderer will use — a
    # wedge whose two ends fall in different lanes cannot be written and has to
    # be dropped, and only the lane assignment can say which those are.
    lanes: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
    for events in per_measure_events:
        if not needs_two_voices:
            lanes.append((events, []))
            continue
        voices = split_events_into_voices(events)
        one = voices[0] if voices else []
        two = voices[1] if len(voices) >= 2 else []
        if len(voices) == 1 and _lone_voice_is_the_second(voices[0]):
            one, two = [], voices[0]
        lanes.append((one, two))
    wedges: dict[int, str] = {}
    for lane_index in (0, 1):
        wedges.update(_lily_wedge_plan(
            [event for measure_lanes in lanes
             for event in measure_lanes[lane_index]]))

    if needs_two_voices:
        # Two-voice block. The block spans the whole staff, so every measure
        # must feed BOTH voices — but a measure where the split found only one
        # voice has no second music to feed, and repeating voice 1 into voice 2
        # (as this did from Phase 4h until 2026-09-02) prints every note in the
        # measure TWICE, once per voice, each copy with its voice's forced stem.
        # The absent voice takes a SPACER (`s`, invisible) rather than a
        # printed rest, because the page shows nothing there — the music never
        # had a second voice in that bar.
        #
        # A lone voice whose stems all point DOWN is the SECOND voice playing
        # alone (13 of the Brahms benchmark page's 23 such measures), so it is
        # routed to \voiceTwo — which is what keeps its printed stem direction
        # — and voice 1 takes the spacer. Mixed or unknown directions stay in
        # voice 1, as before.
        v1_lines: list[str] = [f"{indent}    \\voiceOne"]
        v2_lines: list[str] = [f"{indent}    \\voiceTwo"]
        for (v1_events, v2_events), m_time in zip(lanes, per_measure_time_sig):
            empty_rest = _lily_measure_rest(m_time)
            spacer = _lily_measure_spacer(m_time)
            # An entirely empty measure prints ONE whole-bar rest, so it goes
            # in voice 1 and voice 2 stays invisible — two stacked printed
            # rests were the same duplication in rest form.
            v1_lines.append(
                f"{indent}    " + _lily_measure(v1_events, wedges) + " |"
                if v1_events
                else f"{indent}    {spacer if v2_events else empty_rest} |"
            )
            v2_lines.append(
                f"{indent}    " + _lily_measure(v2_events, wedges)
                + " |" if v2_events else f"{indent}    {spacer} |"
            )
        lines.append(f"{indent}  <<")
        lines.append(f"{indent}    \\new Voice {{")
        lines.extend(v1_lines)
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}    \\new Voice {{")
        lines.extend(v2_lines)
        lines.append(f"{indent}    }}")
        lines.append(f"{indent}  >>")
    else:
        # Single voice (the normal case).
        for events, m_time in zip(per_measure_events, per_measure_time_sig):
            if not events:
                lines.append(f"{indent}  {_lily_measure_rest(m_time)} |")
                continue
            lines.append(f"{indent}  {_lily_measure(events, wedges)} |")

    lines.append(f"{indent}}}")
    return "\n".join(lines)


def to_lilypond(result: dict[str, Any]) -> str:
    """Serialize a transcribe.py result to a LilyPond .ly source string.

    Layout:
      * Each system's staves are wrapped in `\\new PianoStaff << ... >>`
        when the system has exactly 2 staves (treble + bass, the piano
        grand-staff case).
      * Otherwise each staff is its own `\\new Staff` block.
      * Within a staff, if any measure has both stem-up AND stem-down
        chords, the staff renders as a two-voice block (`\\voiceOne` +
        `\\voiceTwo`). Otherwise single voice.
    """
    _ensure_inferred_time_signatures(result)
    arbitrate_arcs_across_staves(result)
    lines: list[str] = []
    lines.append('\\version "2.20.0"')
    lines.append("")
    lines.append("\\header {")
    lines.append(f'  title = "OMR transcription"')
    src = result.get("source_pdf")
    if src:
        lines.append(f'  subtitle = "From: {Path(src).name}"')
    lines.append("  tagline = ##f")
    lines.append("}")
    lines.append("")

    system_blocks: list[str] = []
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            staves = sys_.get("staves", [])
            if len(staves) == 2:
                # PianoStaff grouping
                block_lines = ["  \\new PianoStaff <<"]
                for staff in staves:
                    block_lines.append(_lily_staff_block(staff, indent="    "))
                block_lines.append("  >>")
                system_blocks.append("\n".join(block_lines))
            else:
                for staff in staves:
                    system_blocks.append(_lily_staff_block(staff, indent="  "))

    lines.append("\\score {")
    lines.append("  <<")
    lines.extend(system_blocks)
    lines.append("  >>")
    lines.append("  \\layout { }")
    lines.append("  \\midi { }")
    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# MusicXML serialization
# ---------------------------------------------------------------------------


# clef key → MusicXML (<sign>, <line>). This is exactly what a clef IS — a
# family glyph on a staff line — so it comes straight from the clef table in
# clef_geometry rather than being restated here, and the five C clefs and the
# rare G/F variants export correctly without a second list to keep in sync.
# MusicXML numbers staff lines from the bottom, the same way the table does.
def _build_mxl_clef_signs() -> dict[str, tuple[str, int]]:
    from .clef_geometry import CLEF_BY_FAMILY_LINE

    return {
        name: (family, line)
        for family, lines in CLEF_BY_FAMILY_LINE.items()
        for line, name in lines.items()
    }


_MXL_CLEF_SIGN = _build_mxl_clef_signs()

#: `transcribe.articulation_kind` -> the MusicXML element inside
#: `<notations><articulations>`. Five marks, and DSv2's ten `artic*` classes are
#: these five on two sides — the side says which notehead the mark belongs to
#: and is consumed there, not here: MusicXML places the mark by `placement`,
#: which is engraving, and the pipeline has no opinion about it.
_MXL_ARTICULATION = {
    "staccato": "staccato",
    "staccatissimo": "staccatissimo",
    "accent": "accent",
    "marcato": "strong-accent",
    "tenuto": "tenuto",
}

#: The same five in LilyPond. Both exporters carry every other mark the
#: pipeline reads (beams, dots, dynamics, tuplets, slurs), so articulations go
#: to both; `-.` etc. attach to the note they follow.
_LILY_ARTICULATION = {
    "staccato": "-.",
    "staccatissimo": "-!",
    "accent": "->",
    "marcato": "-^",
    "tenuto": "--",
}


# Suffix → MusicXML <clef-octave-change> value
# (positive = sounds higher than written; negative = lower)
_MXL_CLEF_OCT_SHIFT = {
    "_8va":  1,
    "_8vb":  -1,
    "_15ma": 2,
    "_15mb": -2,
}


def _split_clef_octave(clef: str) -> tuple[str, int]:
    """Strip a "_8va"/"_8vb"/"_15ma"/"_15mb" suffix off a pitch_resolver
    clef key, returning (base, octave_change). Returns (clef, 0) for
    plain base clefs.
    """
    for suffix, shift in _MXL_CLEF_OCT_SHIFT.items():
        if clef.endswith(suffix):
            return clef[: -len(suffix)], shift
    return clef, 0


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _lcm(a: int, b: int) -> int:
    return a * b // _gcd(a, b)


#: Any denominator past this is noise rather than a note value, and letting
#: one through would blow `divisions` up for the whole score.
_MAX_DURATION_DENOMINATOR = 64


def _compute_divisions(result: dict[str, Any]) -> int:
    """Choose a `divisions` value (durations per quarter note) that makes
    every event's duration a whole-number multiple of 1/divisions.

    LCM, NOT MAX, and that is what tuplets need. The old version searched a
    power-of-two ladder and took the largest, which cannot represent a third:
    a triplet eighth is 1/3 of a quarter, `max(16, 12)` is 16, and 16 thirds
    is not an integer, so every triplet would be rounded to the wrong
    `<duration>`. Taking the LCM of each duration's own denominator is exact.

    **Output is unchanged for music without tuplets.** Every plain note value
    has a power-of-two denominator, and the LCM of a set of powers of two is
    their maximum — the same number the old ladder returned.

    Durations arrive as floats (`round(beats, 6)`), so the denominator comes
    from `Fraction.limit_denominator` rather than from a tolerance comparison:
    0.333333 is 1/3 and no float tolerance small enough to be safe would say so.
    """
    divisions = 4
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for measure in staff.get("measures", []):
                    for det in measure.get("detections", []):
                        beats = det.get("duration_beats")
                        if beats is None or beats <= 0:
                            continue
                        denom = Fraction(beats).limit_denominator(
                            _MAX_DURATION_DENOMINATOR).denominator
                        divisions = _lcm(divisions, denom)
    return divisions


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _mxl_pitch_block(pitch: str, indent: str) -> str | None:
    """Render the <pitch>...</pitch> block for a MusicXML <note>."""
    parsed = _parse_pitch(pitch)
    if parsed is None:
        return None
    letter, accidental, octave = parsed
    alter = {"#": 1, "##": 2, "b": -1, "bb": -2}.get(accidental, 0)
    lines = [
        f"{indent}<pitch>",
        f"{indent}  <step>{letter}</step>",
    ]
    if alter != 0:
        lines.append(f"{indent}  <alter>{alter}</alter>")
    lines.append(f"{indent}  <octave>{octave}</octave>")
    lines.append(f"{indent}</pitch>")
    return "\n".join(lines)


def _mxl_attributes_block(
    clef: str | None,
    key_sig: dict[str, Any] | None,
    time_sig: dict[str, Any] | None,
    divisions: int,
    indent: str,
    include_divisions: bool,
) -> str:
    """First measure of every part needs <attributes> with divisions,
    key, time, clef. Subsequent measures can include partial attributes
    when something changes.
    """
    lines = [f"{indent}<attributes>"]
    if include_divisions:
        lines.append(f"{indent}  <divisions>{divisions}</divisions>")
    if key_sig is not None:
        n_sharps = key_sig.get("sharps", 0)
        n_flats = key_sig.get("flats", 0)
        fifths = n_sharps - n_flats  # positive = sharps, negative = flats
        lines.append(f"{indent}  <key>")
        lines.append(f"{indent}    <fifths>{fifths}</fifths>")
        lines.append(f"{indent}    <mode>major</mode>")
        lines.append(f"{indent}  </key>")
    if time_sig is not None:
        # THE GLYPH IS PART OF THE METER, and dropping it was worth 270 edits.
        # `4/4` and a common-time `C` are the same bar length and different
        # engravings; MusicXML says so with `symbol=`, and musicdiff charges
        # `extrainfoedit` at a flat 3 edits per staff when they disagree —
        # 25 staves of Bruckner 5 alone is 75. The detector reads the two
        # glyphs well (conf 0.89-0.96 on the works measured), so this is the
        # eighth case of a signal detected and thrown away at the export.
        # Only `symbol`, never `raw`: see the warning in
        # `rhythm.parse_time_signature` for why the two are not the same fact.
        symbol = time_sig.get("symbol")
        attr = f' symbol="{symbol}"' if symbol in ("common", "cut") else ""
        lines.append(f"{indent}  <time{attr}>")
        lines.append(f"{indent}    <beats>{time_sig.get('numerator', 4)}</beats>")
        lines.append(f"{indent}    <beat-type>{time_sig.get('denominator', 4)}</beat-type>")
        lines.append(f"{indent}  </time>")
    if clef is not None:
        base, octave_change = _split_clef_octave(clef)
        sign, line = _MXL_CLEF_SIGN.get(base, ("G", 2))
        lines.append(f"{indent}  <clef>")
        lines.append(f"{indent}    <sign>{sign}</sign>")
        lines.append(f"{indent}    <line>{line}</line>")
        if octave_change != 0:
            lines.append(
                f"{indent}    <clef-octave-change>{octave_change}</clef-octave-change>"
            )
        lines.append(f"{indent}  </clef>")
    lines.append(f"{indent}</attributes>")
    return "\n".join(lines)


def _mxl_note(event_pitch: str | None, lily_suffix: str, xml_type: str,
              dots: int, beats: float, divisions: int, is_chord: bool,
              is_rest: bool, indent: str, voice: int = 1,
              tied_to_next: bool = False,
              tied_from_prev: bool = False,
              beam_states: dict[int, str] | None = None,
              slur_states: list[tuple[int, str]] | None = None,
              time_modification: dict[str, int] | None = None,
              tuplet_state: str | None = None,
              articulations: list[str] | None = None,
              fermata: bool = False,
              accidental: str | None = None) -> str:
    """Render one <note> for MusicXML — used for both chord members and rests.

    Tie semantics (per MusicXML 3.x):
      - `<tie type="start"/>` + `<notations><tied type="start"/></notations>`
        marks a note as starting a tie
      - `<tie type="stop"/>` + `<notations><tied type="stop"/></notations>`
        marks the second note (the one being tied INTO)
      - A note that's both tied-from-prev AND tied-to-next (a middle note
        in a chain of three) gets both
    """
    duration_units = max(1, int(round(beats * divisions)))
    lines = [f"{indent}<note>"]
    if is_chord:
        lines.append(f"{indent}  <chord/>")
    if is_rest:
        lines.append(f"{indent}  <rest/>")
    elif event_pitch is not None:
        pblock = _mxl_pitch_block(event_pitch, indent + "  ")
        if pblock is None:
            lines.append(f"{indent}  <rest/>")
        else:
            lines.append(pblock)
    lines.append(f"{indent}  <duration>{duration_units}</duration>")
    # <tie> elements (sound-related; must come before <voice>)
    if tied_from_prev:
        lines.append(f'{indent}  <tie type="stop"/>')
    if tied_to_next:
        lines.append(f'{indent}  <tie type="start"/>')
    lines.append(f"{indent}  <voice>{voice}</voice>")
    lines.append(f"{indent}  <type>{xml_type}</type>")
    for _ in range(dots):
        lines.append(f"{indent}  <dot/>")
    # <accidental> sits after <dot> and before <time-modification>. It is what
    # the engraver DREW; `<alter>` inside <pitch> is what sounds. The two are
    # independent — a natural has alter 0 and a printed glyph — which is why
    # this cannot be derived from the pitch on the way out.
    # Guarded on is_rest even though no caller passes one for a rest today —
    # a glyph on a rest is meaningless and the guard keeps that a fact about
    # the element rather than about the current call sites.
    _acc = _MXL_ACCIDENTAL.get(accidental or "") if not is_rest else None
    if _acc:
        lines.append(f"{indent}  <accidental>{_acc}</accidental>")
    # <time-modification> sits after <dot> and before <beam>, per the MusicXML
    # DTD's element order. It carries the tuplet RATIO; the <tuplet> in
    # <notations> below is the bracket that draws it, and a reader needs the
    # ratio even where no bracket is printed.
    if time_modification:
        lines.append(f"{indent}  <time-modification>")
        lines.append(f"{indent}    <actual-notes>"
                     f"{time_modification['actual']}</actual-notes>")
        lines.append(f"{indent}    <normal-notes>"
                     f"{time_modification['normal']}</normal-notes>")
        lines.append(f"{indent}  </time-modification>")
    # <beam> sits after <type>/<dot> and before <notations>, per the MusicXML
    # DTD's element order. Levels ascend, 1 being the primary beam.
    for level in sorted(beam_states or {}):
        lines.append(f'{indent}  <beam number="{level}">{beam_states[level]}</beam>')
    # <notations> holds ties AND slurs, so they share one block — emitting a
    # second <notations> per note is invalid MusicXML.
    notations: list[str] = []
    if tied_from_prev:
        notations.append(f'{indent}    <tied type="stop"/>')
    if tied_to_next:
        notations.append(f'{indent}    <tied type="start"/>')
    for number, kind in (slur_states or []):
        notations.append(f'{indent}    <slur number="{number}" type="{kind}"/>')
    # <tuplet> follows <slur> in the <notations> content model.
    if tuplet_state:
        notations.append(f'{indent}    <tuplet type="{tuplet_state}" number="1"/>')
    # <articulations> follows <tuplet>, and is one element wrapping all of the
    # marks on this note rather than one block each.
    marks = [_MXL_ARTICULATION[k] for k in (articulations or [])
             if k in _MXL_ARTICULATION]
    if marks:
        notations.append(f"{indent}    <articulations>")
        notations.extend(f"{indent}      <{m}/>" for m in marks)
        notations.append(f"{indent}    </articulations>")
    # A fermata hangs off the note OR the rest — the commonest carrier on an
    # orchestral page is a whole-bar rest, which is why this is not folded in
    # with the articulations.
    if fermata:
        notations.append(f'{indent}    <fermata type="upright"/>')
    if notations:
        lines.append(f"{indent}  <notations>")
        lines.extend(notations)
        lines.append(f"{indent}  </notations>")
    lines.append(f"{indent}</note>")
    return "\n".join(lines)


def annotate_fermatas(events: list[dict[str, Any]],
                      detections: list[dict[str, Any]]) -> int:
    """Mark the event under each detected fermata, in place. Returns how many.

    The sixth instance of the shape this file keeps finding: `fermataAbove` is
    in the DSv2 class space, the detector reads it on the engraved Beethoven
    page at confidence 0.90-0.95, and `grep -c fermata export.py` returned 0 —
    every one was dropped on the way out.

    A fermata belongs to whatever is sounding under it, which on an orchestral
    page is usually a WHOLE-BAR REST rather than a note; pairing is therefore by
    x alone, against notes and rests alike, and never by pitch. The mark goes to
    the event whose x-span contains the fermata's centre, or failing that to the
    nearest event centre in the bar — a fermata over a bar's only rest is
    engraved at the bar's middle, while the rest glyph sits at its own centre,
    so requiring containment alone would miss the commonest case of all.
    """
    marks = [
        d["bbox_page"] for d in detections
        if "fermata" in (d.get("class") or "").lower()
        and len(d.get("bbox_page") or ()) == 4
    ]
    if not marks or not events:
        return 0

    def span(event: dict[str, Any]) -> tuple[float, float] | None:
        boxes = [
            h.get("bbox_page") for h in (event.get("noteheads") or [])
            if h.get("bbox_page") and len(h["bbox_page"]) == 4
        ]
        rest = event.get("rest") or {}
        if rest.get("bbox_page") and len(rest["bbox_page"]) == 4:
            boxes.append(rest["bbox_page"])
        if not boxes:
            return None
        return (min(b[0] for b in boxes),
                max(b[0] + b[2] for b in boxes))

    spans = [(i, span(e)) for i, e in enumerate(events)]
    spans = [(i, s) for i, s in spans if s is not None]
    if not spans:
        return 0

    marked = 0
    for box in marks:
        centre = box[0] + box[2] / 2.0
        hit = next((i for i, (lo, hi) in spans if lo <= centre <= hi), None)
        if hit is None:
            hit = min(spans, key=lambda p: abs((p[1][0] + p[1][1]) / 2.0 - centre))[0]
        if not events[hit].get("fermata"):
            events[hit]["fermata"] = True
            marked += 1
    return marked


def _collapse_beam_stacks(raw: list) -> list:
    """Merge boxes that describe ONE beamed group into their union.

    Two readings of a group agree on most of their x-span: a sixteenth
    group's primary and secondary strokes (a beam pitch apart in y), and a
    divisi staff's two rows over the same double stops (Mozart 40's Viola:
    the lower voice's stems-down beam at 1088-1304 and the upper's stems-up
    beam at 1137-1352 are the SAME four notes, offset one head width). The
    test is x-overlap >= 0.6 of the smaller box, deliberately with NO y
    term: the group id is the box id, so any per-note choice between two
    boxes over one group fractures it — a y-banded per-note preference
    turned Mozart 40's chords into runs broken at every flip of which head
    came first, and a narrowest-box rule cost Mozart 41 138 edits.

    The caller must EXCLUDE suspect boxes (see `_suspect_beam_boxes`)
    before collapsing: a spurious bar-wide box overlaps every real group
    at 1.0 of the smaller and would union the whole bar.
    """
    boxes = [list(b) for b in raw]
    merged = True
    while merged:
        merged = False
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                ax, ay, aw, ah = boxes[a]
                bx, by, bw, bh = boxes[b]
                overlap = min(ax + aw, bx + bw) - max(ax, bx)
                if overlap < 0.6 * min(aw, bw):
                    continue
                lo, hi = min(ax, bx), max(ax + aw, bx + bw)
                top, bot = min(ay, by), max(ay + ah, by + bh)
                boxes[a] = [lo, top, hi - lo, bot - top]
                del boxes[b]
                merged = True
                break
            if merged:
                break
    return sorted((tuple(b) for b in boxes), key=lambda b: b[0])


def _suspect_beam_boxes(boxes: list) -> set[int]:
    """Indices of boxes that x-contain >= 2 mutually disjoint other boxes.

    Two real beams at one y level cannot overlap in x, so a box spanning two
    disjoint groups' boxes is almost surely not a beam (Brahms 1's hairpin).
    It is deprioritized, not dropped — a note nothing honest claims may still
    take it.
    """
    out: set[int] = set()
    for i, (ix, _iy, iw, _ih) in enumerate(boxes):
        inside = [
            (jx, jw) for j, (jx, _jy, jw, _jh) in enumerate(boxes)
            if j != i and jx >= ix and jx + jw <= ix + iw]
        inside.sort()
        disjoint = 0
        reach = None
        for jx, jw in inside:
            if reach is None or jx >= reach:
                disjoint += 1
                reach = jx + jw
            else:
                reach = max(reach, jx + jw)
        if disjoint >= 2:
            out.add(i)
    return out


def _pick_beam_box(c: tuple[float, float], boxes: list, suspect: set[int],
                   nh_width: float) -> int | None:
    """The box a notehead at centre `c` beams under, or None.

    Candidates cover x exactly or within one notehead width. Honest boxes
    beat suspects, an exact x-cover beats a padded one, then nearer in x and
    x-order. Deliberately no y term — see `_collapse_beam_stacks` for why a
    per-note y preference fractures groups.
    """
    x, _y = c
    cands = []  # (bi, exact, xdist)
    for bi, (bx, _by, bw, _bh) in enumerate(boxes):
        exact = bx <= x <= bx + bw
        padded = nh_width > 0 and bx - nh_width <= x <= bx + bw + nh_width
        if not (exact or padded):
            continue
        xdist = 0.0 if exact else max(bx - x, x - (bx + bw))
        cands.append((bi, exact, xdist))
    if not cands:
        return None
    cands.sort(key=lambda cand: (
        cand[0] in suspect, not cand[1], cand[2], boxes[cand[0]][0]))
    return cands[0][0]


def annotate_beams(events: list[dict[str, Any]],
                   detections: list[dict[str, Any]]) -> None:
    """Attach MusicXML beam states to each event, in place.

    Phase 4f detects beams with classical CV and `transcribe` writes the result
    onto every notehead as `beam_levels` (1 for an eighth, 2 for a sixteenth),
    plus a `structural`/`beam` detection carrying the group's bounding box. None
    of it reached the exporter: `export.py` did not contain the string "beam"
    at all, so every beamed group was written out as flagged notes. Measured on
    an engraved Beethoven 5 page — 48 `<beam>` elements in the truth, 0 in our
    MusicXML, and 10.1% of the whole OMR-NED edit budget
    (`benchmarks/omr-ned-2026-08/FINDINGS.md`).

    TWO SIGNALS, AND THEY DO DIFFERENT JOBS. The beam BOX says which notes form
    one group — the CV merges a group's primary and secondary beams into a
    single box, so it gives extent, not level. `beam_levels` on each note then
    gives the level structure inside that extent. Grouping by adjacency instead
    would merge two beat-groups in one bar into a single run, which is wrong on
    exactly the dense music this exists for.

    Must be called PER VOICE. Two voices interleave in x, so a run computed
    across both would be broken by the other voice's notes.

    THE BOX IS PADDED BY A NOTEHEAD WIDTH, the correction `rhythm._beamed_groups`
    already makes and for the same reason: the box bounds beam INK, and a beam
    runs from stem to stem — with stems up the first notehead's centre sits a
    head's width left of the ink, with stems down the last sits right of it.
    Unpadded, that edge note fell out of its group: it exported as a flag and
    the group's begin/end landed one note early, which was the single largest
    `wrong flag/beam` mechanism on the 11-work benchmark (430 of 449 edits are
    `editbeam`, and the top signature on every beam-heavy work is an edge note
    at `partial` where the truth beams it). A 2-note group lost BOTH notes: the
    orphan formed a synthetic run of one, and the survivor was alone under its
    box — both "a lone note is flagged".

    THREE MORE RULES ABOUT WHICH BOX A NOTE BELONGS TO, each paid for by a
    measured failure (benchmarks/omr-beam-gap-2026-09/FINDINGS.md):

    - SAME-STACK BOXES ARE COLLAPSED FIRST. A sixteenth group's primary and
      secondary strokes arrive as two boxes over the same x-span at a beam
      pitch apart in y. A per-note choice between them FRACTURES the group —
      the group id is the box id, so two notes picking different strokes of
      the same beam land in different groups even though the spans agree.
      (A "narrowest covering box wins" rule did exactly that: Mozart 41 went
      7 -> 145 beam edits.) Boxes with x-overlap >= 0.6 of the smaller within
      3 notehead widths in y merge into their union.
    - A BOX THAT CONTAINS TWO DISJOINT BOXES IS SUSPECT. Brahms 1, Contrabass
      m4: a spurious 685px "beam" (a hairpin's ink) at the real beams' own y
      spans the whole bar and, first-by-x, swallowed all six notes into one
      run where the page prints two groups of three. Real beams at one y level
      cannot overlap in x, so a box x-containing >= 2 mutually disjoint boxes
      is tried only when no honest box claims the note.
    - A DIVISI STAFF'S TWO BEAM ROWS ARE ONE GROUP, NOT A TIE TO BREAK.
      Mozart 40's Viola prints double stops under two beams (lower voice's
      stems-down box 1088-1304, upper's stems-up 1137-1352, 354px apart in
      y) — the same four notes offset one head width, so the rows collapse
      by x-overlap like a stack's strokes. A per-note y preference was
      measured instead and REFUSED: chord events flip which head is first,
      so notes of one run picked different rows and the run fractured
      (Mozart 40 47 -> 54 while it was supposed to fall).
    """
    raw_boxes = [
        d["bbox_page"] for d in detections
        if d.get("category") == "structural" and d.get("class") == "beam"
        and len(d.get("bbox_page") or ()) == 4]

    def centre(event: dict[str, Any]) -> tuple[float, float] | None:
        heads = event.get("noteheads") or []
        if not heads:
            return None
        box = heads[0].get("bbox_page")
        if not box or len(box) != 4:
            return None
        return (box[0] + box[2] / 2.0, box[1] + box[3] / 2.0)

    def levels(event: dict[str, Any]) -> int:
        heads = event.get("noteheads") or []
        return int(heads[0].get("beam_levels") or 0) if heads else 0

    # One notehead width, from the events' own heads — the same unit
    # `rhythm._beamed_groups` pads with (a length in the cell's frame, never
    # the detection's own noisy bbox height).
    head_widths = sorted(
        h["bbox_page"][2]
        for e in events for h in (e.get("noteheads") or [])
        if len(h.get("bbox_page") or ()) == 4)
    nh_width = head_widths[len(head_widths) // 2] if head_widths else 0.0

    suspect_raw = _suspect_beam_boxes(raw_boxes)
    honest = [b for i, b in enumerate(raw_boxes) if i not in suspect_raw]
    boxes = _collapse_beam_stacks(honest)
    suspect = set(range(len(boxes), len(boxes) + len(suspect_raw)))
    boxes = list(boxes) + [tuple(raw_boxes[i]) for i in sorted(suspect_raw)]

    # Group id per event: the beam box covering it, or a synthetic run for
    # events that carry a level but sit under no detected box.
    group_of: dict[int, object] = {}
    synthetic = 0
    prev_beamed = False
    for i, event in enumerate(events):
        if event.get("kind") == "rest" or levels(event) < 1:
            prev_beamed = False
            continue
        c = centre(event)
        hit = None
        if c is not None:
            bi = _pick_beam_box(c, boxes, suspect, nh_width)
            if bi is not None:
                hit = ("box", bi)
        if hit is None:
            if not prev_beamed:
                synthetic += 1
            hit = ("run", synthetic)
        group_of[i] = hit
        prev_beamed = True

    # Within each group, each level's consecutive run becomes begin/continue/end.
    by_group: dict[object, list[int]] = {}
    for i, g in group_of.items():
        by_group.setdefault(g, []).append(i)

    for members in by_group.values():
        members.sort()
        if len(members) < 2:
            continue                      # a lone note is flagged, not beamed
        top = max(levels(events[i]) for i in members)
        for level in range(1, top + 1):
            run: list[int] = []
            for i in members + [None]:
                if i is not None and levels(events[i]) >= level:
                    run.append(i)
                    continue
                if run:
                    _mark_run(events, run, level, members)
                run = []


def _mark_run(events: list[dict[str, Any]], run: list[int], level: int,
              members: list[int]) -> None:
    """Write begin/continue/end — or a hook for a run of one — over `run`."""
    if len(run) == 1:
        # A single note at this level is a hook: it points back toward the note
        # it shares the lower beam with, forward only at the group's start.
        value = "forward hook" if run[0] == members[0] else "backward hook"
        events[run[0]].setdefault("beam_states", {})[level] = value
        return
    for pos, i in enumerate(run):
        value = "begin" if pos == 0 else ("end" if pos == len(run) - 1 else "continue")
        events[i].setdefault("beam_states", {})[level] = value


# DSv2 spells a dynamic out as separate letter glyphs, so "ff" arrives as two
# `dynamicF` detections side by side and has to be reassembled. Letters that do
# not form a dynamic word are dropped rather than guessed at.
_DYNAMIC_LETTER = {
    "dynamicF": "f", "dynamicP": "p", "dynamicM": "m",
    "dynamicS": "s", "dynamicZ": "z", "dynamicR": "r",
}
# Only words MusicXML has an element for. `sf`/`sfz`/`fp` are <other-dynamics>.
_DYNAMIC_WORDS = {
    "p", "pp", "ppp", "pppp", "f", "ff", "fff", "ffff",
    "mp", "mf", "sf", "sfz", "fp", "rf", "rfz", "sfp", "fz",
}
_DYNAMIC_ELEMENTS = {
    "p", "pp", "ppp", "pppp", "f", "ff", "fff", "ffff", "mp", "mf",
    "sf", "sfz", "fp", "rf", "rfz", "sfp", "fz",
}


def measure_dynamics(detections: list[dict[str, Any]]) -> list[tuple[float, str, str]]:
    """`(x, "dynamic", word)` for each dynamic marking in a measure, left to right.

    The detector emits one glyph per LETTER, so adjacent letters are joined
    into a word before it means anything: two `dynamicF` a notehead apart are
    one "ff", not two "f". Measured on the Brahms fixture, 31 letter glyphs
    across 7 bars against 19 dynamics in the truth.
    """
    letters = []
    for det in detections:
        letter = _DYNAMIC_LETTER.get(det.get("class") or "")
        box = det.get("bbox")
        if letter and box and len(box) == 4:
            letters.append((box[0], box[1], box[2], letter))
    if not letters:
        return []
    letters.sort()
    width = max(w for _x, _y, w, _l in letters) or 1

    out: list[tuple[float, str, str]] = []
    run_x, run_y, word = letters[0][0], letters[0][1], letters[0][3]
    prev_right = letters[0][0] + letters[0][2]
    for x, y, w, letter in letters[1:]:
        # Same word: touching horizontally and on the same line vertically.
        if x - prev_right <= width and abs(y - run_y) <= width:
            word += letter
        else:
            if word in _DYNAMIC_WORDS:
                out.append((run_x, "dynamic", word))
            run_x, run_y, word = x, y, letter
        prev_right = x + w
    if word in _DYNAMIC_WORDS:
        out.append((run_x, "dynamic", word))
    return out


def measure_direction_words(measure: dict[str, Any]) -> list[tuple[float, str, str]]:
    """`(x_canonical, "words", text)` for each direction word on a measure.

    Read from `direction_texts`, which `direction_text.attach_to_page` writes
    and which is absent from every result produced without that post-pass — so
    a transcription that did not read text exports exactly as it did before.

    The x is converted here rather than stored converted, because the reader
    works in PAGE pixels (it cuts crops out of the page) and the exporter works
    in the cell's CANONICAL frame (that is what `x_position` is). The cell is
    rescaled uniformly, so `upscale_factor` — defined on the height — is the
    x scale too.
    """
    entries = measure.get("direction_texts") or []
    if not entries:
        return []
    box = measure.get("bbox_page_px") or [0, 0, 0, 0]
    scale = float(measure.get("upscale_factor") or 1.0)
    out = []
    for entry in entries:
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        x_canonical = (float(entry.get("x_page", box[0])) - float(box[0])) * scale
        out.append((x_canonical, "words", text))
    return out


def measure_directions(measure: dict[str, Any]) -> list[tuple[float, str, str]]:
    """Every `<direction>` on a measure, as `(x_canonical, kind, text)`.

    Two sources with nothing in common but where they end up: the DYNAMICS the
    detector drew as glyphs, and the WORDS `direction_text` read with OCR. One
    entry point for both so a caller asks "what marks does this measure carry"
    rather than assembling the answer itself — there is more than one place in
    this file that emits a measure, and they must not drift.

    ⚠️ HAIRPINS ARE NOT HERE, and that is a design choice rather than a gap:
    a wedge is a SPAN, so `annotate_wedges_in_staff` attaches it to the notes it
    covers, the way slurs are done. See `KNOWN_GAPS["wedge"]` for what that
    costs on a bar with no detected events.
    """
    return (measure_dynamics(measure.get("detections", []))
            + measure_direction_words(measure))


def _mxl_direction(item: tuple[str, str], indent: str) -> str:
    """One `<direction>`: a dynamic marking, or a word.

    `<dynamics>` and `<words>` are different `<direction-type>` children and
    musicdiff scores them as different KINDS — a word emitted as an
    `<other-dynamics>` would not pair with the truth's direction at all, and
    would be charged twice over. So the kind travels with the text.
    """
    kind, word = item
    if kind == "words":
        return (f'{indent}<direction placement="below">\n'
                f"{indent}  <direction-type>\n"
                f"{indent}    <words>{_xml_escape(word)}</words>\n"
                f"{indent}  </direction-type>\n"
                f"{indent}</direction>")
    inner = (f"<{word}/>" if word in _DYNAMIC_ELEMENTS
             else f'<other-dynamics>{_xml_escape(word)}</other-dynamics>')
    return (f'{indent}<direction placement="below">\n'
            f"{indent}  <direction-type>\n"
            f"{indent}    <dynamics>{inner}</dynamics>\n"
            f"{indent}  </direction-type>\n"
            f"{indent}</direction>")


def measure_has_fermata(detections: list[dict[str, Any]]) -> bool:
    """Does this measure carry a fermata the whole-measure rest should wear?

    THE SAME BRANCH AS `_mxl_empty_measure`, ONE LAYER DOWN. A fermata attaches
    to an EVENT, and a measure with no detected events emits only a
    whole-measure rest — which was built without one, so the mark was read and
    dropped exactly as the directions were before that function existed.

    ⚠️ `annotate_fermatas` already documents that a fermata on an orchestral
    page is usually over a whole-bar rest rather than a note. That is precisely
    the case this branch handles, so it is the likeliest fermata of all, not an
    edge case. Found by `score_translation`: Beethoven 5 detects 36, its truth
    has 36, and 35 reached the file — the missing one is P7 m5, whose staff
    detects a `restWhole` that `group_chords_in_measure` does not turn into an
    event, so the bar falls to this branch while its neighbours do not.
    """
    return any((d.get("class") or "").lower().startswith("fermata")
               for d in detections)


#: The two hairpin classes, and the `<wedge>` type each one opens with.
_HAIRPIN_TYPES = {
    "dynamicCrescendoHairpin": "crescendo",
    "dynamicDiminuendoHairpin": "diminuendo",
}


def eventless_wedges(
    detections: list[dict[str, Any]]
) -> list[tuple[float, int, str]]:
    """`(x, number, type)` for the hairpins of a measure with NO events.

    ⚠️ A wedge is normally attached to the NOTES it covers —
    `annotate_wedges_in_staff` writes `wedge_states` onto events, the way slurs
    are done — and that is right, because a hairpin is a span OVER music. A bar
    the detector found no events in has nothing to attach to, so the hairpin was
    dropped.

    ⚠️ AND IT FIRES NOWHERE IN THE CURRENT CORPUS, which is stated rather than
    hidden. 8 of the 60 CV-read hairpins on the scan benchmark do not become
    wedges, and all four of Dvorak 9 p5's sit in bars the pipeline reads as a
    single `restWhole` — but this branch is not why, and the reason took two
    wrong answers to find:

      * "the staves are densely playing and the rest is a misdetection" — WRONG,
        and it was asserted here from a crop taken at the RIGHT-HAND side of the
        page, which shows the later bars where those staves do play. The trimmed
        truth says Flauti and Oboi have **0 sounding notes in bars 1-5** and
        play only in 6-8, and the pipeline's counts for the bars they do play
        (4, 5, 9) sit against a truth of (5, 5, 6). The resting reading is
        RIGHT.
      * what is actually broken there is MEASURE SEGMENTATION: staff 0's measure
        boxes overlap massively and the last runs to x=9055 on a 5084-wide page,
        so which bar a hairpin falls in is not reliably answerable on that staff.

    So the 8 are not evidence for anchoring a wedge to a rest — if those bars
    genuinely rest, a hairpin filed there is MISATTRIBUTED, and anchoring it
    would cement the error. That is the same conclusion the convention reaches
    from the other side: a hairpin belongs to sounding music.

    This stays because the hole is real — a bar with genuinely no events would
    otherwise drop a hairpin the reader can see — and because
    `_mxl_empty_measure` already carries dynamics and words for exactly that
    case. It is guarded by unit tests rather than by the corpus.

    With no events the span degenerates — there is nothing to span — so the
    opening and the stop go at the hairpin's own x positions. That is the same
    reasoning `_mxl_empty_measure` already uses for a direction: no event to
    place it against, so its own position is the only defensible answer.

    The `number` is the smallest not currently open, which is what MusicXML uses
    it for; within one bar overlapping hairpins are rare but not impossible.
    """
    spans = []
    for det in detections:
        kind = _HAIRPIN_TYPES.get(det.get("class") or "")
        box = det.get("bbox")
        if kind and box and len(box) == 4 and box[2] > 0:
            spans.append((float(box[0]), float(box[0]) + float(box[2]), kind))
    if not spans:
        return []
    out: list[tuple[float, int, str]] = []
    open_until: dict[int, float] = {}
    for x0, x1, kind in sorted(spans):
        for n in range(1, len(spans) + 2):
            if open_until.get(n, -1.0) <= x0:
                break
        open_until[n] = x1
        out.append((x0, n, kind))
        out.append((x1, n, "stop"))
    return sorted(out)


def _mxl_empty_measure(time_sig: dict[str, Any] | None, divisions: int,
                       directions: list[tuple[float, str, str]] | None,
                       indent: str, fermata: bool = False,
                       wedges: list[tuple[float, int, str]] | None = None) -> list[str]:
    """A whole-measure rest, WITH whatever marks that measure carries.

    ⚠️ **A BAR WITH NO NOTES STILL CARRIES ITS MARKS**, and this is the one
    place in the exporter where that was not true. A measure the detector found
    no events in takes the whole-measure-rest path, which appends the rest
    directly and never calls `_mxl_voice_events` — the only thing that emits
    `<direction>`. The dynamics and words were computed one line above the
    branch and silently discarded, in BOTH export sites.

    It had been dropping DYNAMICS since they shipped, a month before the
    direction reader existed. **Engraved pages cannot show it**, which is why
    sixteen benchmark rounds did not: they put an event in every bar and never
    take the branch. It takes a scan, where a staff genuinely rests through a
    bar that still carries a `sempre` — 2 measures across the five verified
    rows of `benchmarks/omr-scan-e2e-2026-09`, and 0 across every engraved
    work.

    ⚠️ This fix is DESCRIBED by commit `a907e41` (and its duplicate `46e42a4`,
    2026-09-02) and is NOT IN EITHER: both commits contain one file, a Surya
    determinism probe. The message says "Both export sites had it" and "Both
    are covered by tests now" and neither was true of the tree. The defect is
    live on main, which is how this was found — by looking, because a hairpin
    over a resting staff would have hit the same branch. **The tree outranks
    the ledger.**

    The marks go BEFORE the rest, so they land at offset 0 of the bar. There is
    no event to place them against — that is what makes the bar empty — so
    `_direction_slots`' nearest-note rule has nothing to say here, and the
    start of the bar is the only defensible answer.
    """
    marks: list[tuple[float, str]] = [
        (x, _mxl_direction((kind, text), indent))
        for x, kind, text in (directions or [])
    ]
    marks += [(x, _mxl_wedge(number, kind, indent))
              for x, number, kind in (wedges or [])]
    lines = [xml for _x, xml in sorted(marks, key=lambda m: m[0])]
    r_beats, r_type, r_dots = _mxl_measure_rest(time_sig)
    lines.append(_mxl_note(
        None, "", r_type, r_dots, r_beats, divisions,
        is_chord=False, is_rest=True, indent=indent, voice=1,
        fermata=fermata,
    ))
    return lines


def _mxl_wedge(number: int, kind: str, indent: str) -> str:
    """One `<wedge>`, wrapped in the `<direction>` MusicXML requires.

    `spread` is deliberately NOT written. It is the printed WIDTH of the open
    end in tenths, a fact about the engraving rather than about the music; the
    truth files carry it because LilyPond emits it, and music21 does not read a
    hairpin's identity from it.
    """
    return (f'{indent}<direction placement="below">\n'
            f"{indent}  <direction-type>\n"
            f'{indent}    <wedge number="{number}" type="{kind}"/>\n'
            f"{indent}  </direction-type>\n"
            f"{indent}</direction>")


# A slur clipped by a cell boundary ends EXACTLY on it. Measured over the
# Brahms fixture (`benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`): the facing
# edges of a split pair sit 0.00-0.10 staff spaces from the boundary, and the
# nearest consecutive-measure arc pair that is NOT a split sits at 1.58. The
# constant is read off that gap rather than tuned into it — every value between
# 0.10 and 1.58 gives the same 16 merges.
_SLUR_BOUNDARY_SPACES = 0.5
# Two halves of one slur cross the barline at the same height: 0.02-1.14 staff
# spaces apart on the same fixture. The next-nearest pair is 8.04 — an arc
# ABOVE the staff against one BELOW it, which is two different slurs, not one.
# The exported score is IDENTICAL for anything from 1.0 to 6.0, so this is a
# plateau rather than a peak; the single pair between 0.53 and 1.14 that a
# tighter value would drop changes no note.
_SLUR_CONTINUATION_DY_SPACES = 2.0
# MusicXML numbers simultaneous slurs 1-6.
_MAX_SLUR_NUMBER = 6
# How far past an arc's edge a notehead centre may sit and still be under it,
# in notehead widths. See `_noteheads_under` for the measurement.
_SLUR_ARC_PAD_NOTEHEADS = 0.25


# ---------------------------------------------------------------------------
# Cross-staff ARC attribution — the arbitration noteheads already have
# ---------------------------------------------------------------------------
# A measure cell is cut with padding above and below so ledger notes are not
# sliced off (`measure_extractor.PAD_*_STAFF_LINES`), and on a conductor's page
# that padding reaches the neighbouring staff's ink. For NOTEHEADS the
# duplicate is arbitrated by `transcribe._dedupe_cross_staff_detections`
# (ledger ladder, then the instrument's written range, then distance). For ARCS
# nothing arbitrated at all, so a slur printed over one staff's music could be
# paired and exported on ANOTHER staff — and, worse, the arc need not be
# detected twice for this to happen: where the gap between two staves is wide
# the upper staff's cell reaches ink the lower staff's cell does not, so the
# arc exists ONLY in the wrong staff and no duplicate-resolution rule can see
# it.
#
# WORKED EXAMPLE, and it corrects the hypothesis this work started from. On
# `brahms-sym1-mvt1` the Timpani exports 4 slurs and 1 tie against a truth of
# ZERO. The beam-gap findings guessed these were "the staff BELOW's arcs";
# rendering the page shows what they actually are — Violin 1 plays four ledger
# lines above its staff there, so ITS slurs are drawn high in the 7.7-space gap
# between Timpani and Violin 1, inside the Timpani's grown padding and above
# the top of Violin 1's own cell.
#
# THE EVIDENCE IS THE ARC'S OWN JOB: an arc binds a run of noteheads and is
# drawn just clear of them, on the side away from the stems. So the staff an
# arc belongs to is the one whose NOTEHEADS IT HUGS — and that question can be
# asked of a staff that never detected the arc, because the noteheads have
# already been arbitrated across staves and each staff's head set is the one a
# reader would see. Distance to the staff LINES is the trap it was for notes:
# an engraver opens the gap above a staff precisely so the ledger notes and
# their slurs can live there, which puts them nearer the staff above.
#
# Measured over the 11-work engraved benchmark, clearance in staff spaces from
# an arc's box to the nearest notehead it covers in its own staff, counting
# only arcs covering >= 2 heads (fewer never becomes a slur):
#
#     own clearance     part whose truth       part whose truth
#     (staff spaces)    has NO arc at all      does have arcs
#     [0.00, 0.25)              5                    165
#     [0.25, 0.50)              0                     31
#     [0.50, 0.75)              1                      8
#     [0.75, 1.00)              1                      0
#     [1.00, 1.50)              2                      1
#     [1.50, 2.00)              0                      2
#     [2.00, 3.00)              6                      0
#     [3.00,  inf)              2                     30
#
# A real slur hugs its notes: 204 of 237 arcs on arc-bearing parts sit under
# half a space. That tail is NOT clean enough to threshold on its own, so the
# rule is COMPARATIVE — an arc leaves a staff only when another staff of the
# same system explains it better — which is the same shape as the notehead
# arbitration and cannot fire at all on a page with one staff.
#: A rival staff must itself hug the arc this closely for the arc to move.
#: On the Brahms Timpani every rival reading is 0.00-0.52 spaces; the value
#: is a plateau, see FINDINGS.md.
_ARC_RIVAL_NEAR_SPACES = 0.75
#: ...and must beat the incumbent by this much. A PLATEAU, not a tuned value:
#: swept over the eleven works, every margin from 0.25 to 0.75 reattributes the
#: SAME arcs (8 on parts whose truth has none, 15 elsewhere), and the answer
#: first moves at 0.90. 0.5 is the middle of that plateau.
_ARC_RIVAL_MARGIN_SPACES = 0.5
#: A rival staff must cover at least this many of its own noteheads with the
#: arc, so a single stray head cannot claim one.
_ARC_RIVAL_MIN_COVERED = 2


def _arc_attribution_mode() -> str:
    """`OMR_ARC_ATTRIBUTION` = `move` (default) / `drop` / `off`."""
    mode = os.environ.get("OMR_ARC_ATTRIBUTION", "move").strip().lower()
    return mode if mode in ("move", "drop", "off") else "move"


def _arcs_in_measure(measure: dict[str, Any]) -> list[dict[str, Any]]:
    return [d for d in measure.get("detections", [])
            if d.get("category") == "structural"
            and d.get("class") in ("slur", "tie")
            and len(d.get("bbox_page") or ()) == 4]


def _vertical_gap(a: list[int], b: list[int]) -> float:
    """Vertical clearance between two page boxes in px; 0 where they overlap."""
    a0, a1 = a[1], a[1] + a[3]
    b0, b1 = b[1], b[1] + b[3]
    if a1 < b0:
        return b0 - a1
    if b1 < a0:
        return a0 - b1
    return 0.0


def _arc_clearance(
    arc_box: list[int],
    heads: list[dict[str, Any]],
) -> tuple[float | None, int]:
    """`(px clearance to the nearest covered notehead, n covered)`.

    Coverage is the same padded x test `_noteheads_under` makes, for the same
    reason: the arc is drawn BETWEEN its outer heads, so its ink stops inside
    both centres and an unpadded test loses the note at each end.
    """
    if not heads:
        return None, 0
    pad = _SLUR_ARC_PAD_NOTEHEADS * (
        sum(h["bbox_page"][2] for h in heads) / len(heads))
    ax, _ay, aw, _ah = arc_box
    covered = [h for h in heads
               if ax - pad <= h["bbox_page"][0] + h["bbox_page"][2] / 2.0
               <= ax + aw + pad]
    if not covered:
        return None, 0
    return min(_vertical_gap(arc_box, h["bbox_page"]) for h in covered), len(covered)


def _staff_noteheads(staff: dict[str, Any]) -> list[dict[str, Any]]:
    heads: list[dict[str, Any]] = []
    for measure in staff.get("measures", []):
        heads.extend(_measure_noteheads(measure))
    return heads


def _measure_holding_x(
    staff: dict[str, Any], x: float,
) -> dict[str, Any] | None:
    """The staff's measure whose cell contains this page x, else the nearest."""
    best = None
    for measure in staff.get("measures", []):
        box = measure.get("bbox_page_px")
        if not box or len(box) != 4:
            continue
        if box[0] <= x <= box[2]:
            return measure
        d = min(abs(box[0] - x), abs(box[2] - x))
        if best is None or d < best[0]:
            best = (d, measure)
    return best[1] if best else None


def arbitrate_arcs_across_staves(result: dict[str, Any]) -> int:
    """Give every arc to the staff of its system whose noteheads it hugs.

    Returns the number of arcs reattributed. Idempotent — the result is
    stamped, so a second export of the same dict is a no-op, and re-running is
    a fixed point anyway (a moved arc's new staff is the one that hugs it).
    """
    if _arc_attribution_mode() == "off" or result.get("_arc_attribution"):
        return 0
    moved = 0
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            moved += _arbitrate_arcs_in_system(system.get("staves") or [])
    result["_arc_attribution"] = {"mode": _arc_attribution_mode(),
                                  "n_reattributed": moved}
    return moved


def _arbitrate_arcs_in_system(staves: list[dict[str, Any]]) -> int:
    if len(staves) < 2:
        return 0
    spacings: list[float | None] = []
    heads: list[list[dict[str, Any]]] = []
    for staff in staves:
        geom = staff.get("staff_geometry") or {}
        spacings.append(geom.get("line_spacing_px") or None)
        heads.append(_staff_noteheads(staff))
    mode = _arc_attribution_mode()
    moved = 0
    for s_idx, staff in enumerate(staves):
        sp = spacings[s_idx]
        if not sp:
            continue
        for measure in staff.get("measures", []):
            for arc in list(_arcs_in_measure(measure)):
                own_px, _own_n = _arc_clearance(arc["bbox_page"], heads[s_idx])
                own = None if own_px is None else own_px / sp
                best: tuple[float, int] | None = None
                for o_idx in range(len(staves)):
                    o_sp = spacings[o_idx]
                    if o_idx == s_idx or not o_sp:
                        continue
                    gap_px, n = _arc_clearance(arc["bbox_page"], heads[o_idx])
                    if gap_px is None or n < _ARC_RIVAL_MIN_COVERED:
                        continue
                    rival = gap_px / o_sp
                    if best is None or rival < best[0]:
                        best = (rival, o_idx)
                if best is None or best[0] > _ARC_RIVAL_NEAR_SPACES:
                    continue
                # An arc covering nothing in this staff is claimed outright:
                # it binds no note here, so there is nothing for it to be.
                if own is not None and (own - best[0]) < _ARC_RIVAL_MARGIN_SPACES:
                    continue
                measure["detections"].remove(arc)
                moved += 1
                if mode != "move":
                    continue
                ax, _ay, aw, _ah = arc["bbox_page"]
                target = _measure_holding_x(staves[best[1]], ax + aw / 2.0)
                if target is None:
                    continue
                arc = dict(arc)
                arc["arc_reattributed_from_staff"] = s_idx
                target.setdefault("detections", []).append(arc)
    return moved


def _staff_boxes_by_measure(
    measures: list[dict[str, Any]],
    wanted: Any,
) -> list[list[list[int]]]:
    """Each measure's matching detection boxes, in page pixels, left to right.

    `wanted(detection) -> bool` picks the family. One collector for slurs and
    hairpins because the barline merge below it, and the numbering below that,
    are shared. ⚠️ What is NOT shared is the step between them — which notes the
    curve is about — because a slur is drawn OVER its notes and a hairpin
    BETWEEN them. See `_wedge_anchors`.
    """
    out = []
    for measure in measures:
        out.append(sorted(
            (d["bbox_page"] for d in measure.get("detections", [])
             if wanted(d) and len(d.get("bbox_page") or ()) == 4),
            key=lambda b: b[0],
        ))
    return out


def _staff_arcs_by_measure(
    measures: list[dict[str, Any]],
    cls: str = "slur",
) -> list[list[list[int]]]:
    """Each measure's arcs of one class, in page pixels, left to right."""
    return _staff_boxes_by_measure(
        measures,
        lambda d: (d.get("category") == "structural"
                   and d.get("class") == cls),
    )


# ---------------------------------------------------------------------------
# Arc reclassification (OMR_ARC_RECLASS, default OFF) — tie vs slur is
# POSITION, not shape
# ---------------------------------------------------------------------------
# A tie and a slur are the SAME GLYPH; what separates them is the notes they
# connect (docs/position-grammar-confusables-2026-09-04.md §2 ARC). The
# detector's class is therefore a prior, and two configurations refute it
# outright:
#
#   * an arc classed `slur` whose ends land on exactly two ADJACENT
#     SAME-PITCH noteheads is a tie — the duration-semantic reading, and the
#     safer error where the print alone cannot decide (a two-note phrasing
#     slur on a repeated pitch is undecidable; default to tie);
#   * an arc classed `tie` that spans MORE than two note events, or whose two
#     heads carry DIFFERENT pitches, cannot be a tie — a tie joins two
#     adjacent notes of one pitch by definition.
#
# R3 shape (veto the impossible, reclass only when decisive, abstain
# otherwise): everything not in those two configurations keeps the
# detector's class. Off by default until priced on BOTH benchmark families.

#: Every veto fired since the last `reset_arc_reclass_stats()`, by rule.
#: A debug surface for benchmarks and tests, not part of the export result.
ARC_RECLASS_STATS: Counter = Counter()


def reset_arc_reclass_stats() -> None:
    ARC_RECLASS_STATS.clear()


def _arc_reclass_enabled() -> bool:
    """`OMR_ARC_RECLASS=1` turns the veto on; anything else leaves it off."""
    return os.environ.get("OMR_ARC_RECLASS", "0").strip().lower() in (
        "1", "true", "yes", "on")


def _event_order_of_noteheads(
    measures: list[dict[str, Any]],
) -> dict[int, tuple[int, int]]:
    """`id(notehead) -> (voice index, event ordinal)` over a whole staff run.

    The ordinal counts EVERY event in the voice — rests included — in playing
    order across the flattened measure sequence, so two heads are ADJACENT
    exactly when nothing (note or rest) sounds between them in their voice:
    ordinals one apart. A tie cannot cross a rest, which is why the rest has
    to spend an ordinal. The one thing this cannot see is a measure the
    detector left EMPTY between the two heads — no event, no ordinal — and a
    same-pitch pair straddling one would read as adjacent; such a measure
    exports as a whole rest, so the conversion there is wrong but rare, and
    it is priced by the A/B rather than guarded against.

    Same per-measure voice-index assumption as `_voice_of_notehead`, of which
    this is the ordered variant.
    """
    order: dict[int, tuple[int, int]] = {}
    counters: dict[int, int] = {}
    for measure in measures:
        events = group_chords_in_measure(measure.get("detections", []))
        for v_idx, voice_events in enumerate(split_events_into_voices(events)):
            for event in voice_events:
                ordinal = counters.get(v_idx, 0)
                counters[v_idx] = ordinal + 1
                for head in event.get("noteheads") or []:
                    order[id(head)] = (v_idx, ordinal)
    return order


def _pitch_step(pitch: str | None) -> str | None:
    """`"F4"` for `"F#4"` — the staff POSITION, spelling stripped.

    The tie→slur veto compares steps and never spelled pitches, measured
    rather than assumed: on the engraved A/B every losing veto was a
    same-step pair differing only in accidental — `F#4 -> F4`, `C#5 -> C5` —
    which is the accidental-EXPIRY artifact, not a different note. The
    canonical tie crosses a barline, the far head does not restate its
    accidental (the tie carries it), and `pitch_resolver` spells that head
    from the key signature alone. Vetoing on the spelling inherits that
    limitation; the step is what the flanked position actually says. Same
    key the pre-fill alignment moved to for the same reason (CLAUDE.md:
    "the alignment key is STAFF POSITION, not pitch"). The winning vetoes
    were all genuinely step-apart (`F#5 -> G5`, `B5 -> C6`) and survive.
    """
    if not pitch:
        return None
    octave = pitch.rstrip()
    letter = octave[0]
    digits = "".join(ch for ch in octave if ch.isdigit() or ch == "-")
    return f"{letter}{digits}"


def _tie_flank_pair(
    arc_bp: list[int],
    staff_heads: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The (start, stop) noteheads this tie arc flanks, or None.

    A MIRROR of `transcribe._pair_ties_in_staff`'s pairing relation, on the
    same `bbox_page` data: start = the head whose x-centre sits at or left of
    the arc's left edge, nearest, within 3 of its own widths; stop likewise on
    the right; both within a y-tolerance of 3 average head heights. Mirrored
    rather than imported because `transcribe` drags the whole detection stack
    in with it, and pinned against the original by
    `test_export.TestArcReclass.test_flank_pair_mirrors_transcribes_pairing`.

    A tie arc FLANKS its heads — it spans the gap between them — which is why
    slur coverage (`_noteheads_under`, centres inside the box) is the wrong
    question for finding them.
    """
    if not staff_heads:
        return None
    tx0, ty0, tw, th = arc_bp
    tie_left, tie_right = tx0, tx0 + tw
    tie_yc = ty0 + th / 2.0
    avg_h = sum(h["bbox_page"][3] for h in staff_heads) / len(staff_heads)
    y_tol = max(avg_h * 3, 30)
    best_left = best_right = None
    best_left_dx = best_right_dx = float("inf")
    for det in staff_heads:
        bp = det["bbox_page"]
        xc = bp[0] + bp[2] / 2.0
        yc = bp[1] + bp[3] / 2.0
        if abs(yc - tie_yc) > y_tol:
            continue
        dx_left = tie_left - xc
        if 0 <= dx_left < bp[2] * 3 and dx_left < best_left_dx:
            best_left, best_left_dx = det, dx_left
        dx_right = xc - tie_right
        if 0 <= dx_right < bp[2] * 3 and dx_right < best_right_dx:
            best_right, best_right_dx = det, dx_right
    if best_left is None or best_right is None or best_left is best_right:
        return None
    return best_left, best_right


def _tie_arc_impossibility(
    arc: list[int],
    staff_heads: list[dict[str, Any]],
    order: dict[int, tuple[int, int]],
) -> tuple[str, tuple[dict[str, Any], dict[str, Any]] | None] | None:
    """Why this tie arc cannot be a tie, or None to let it stand.

    Returns `(reason, flanked_pair_or_None)`. Vetoing a PAIRED arc also
    clears the tie flags its pairing set — recorded in `arc_reclass_removed`
    so the next annotate pass can restore them — or the reclassed slur would
    export beside a residual tie. Only the mirror pair's flags are touched: a
    chained tie shares heads with its neighbours, and clearing any wider
    would damage arcs this veto never looked at.
    """
    ax, _ay, aw, _ah = arc
    under = [h for h in staff_heads
             if ax <= h["bbox_page"][0] + h["bbox_page"][2] / 2.0 <= ax + aw]
    pair = _tie_flank_pair(arc, staff_heads)
    if pair is not None:
        left, right = pair
        reason = None
        sl, sr = _pitch_step(left.get("pitch")), _pitch_step(right.get("pitch"))
        if sl and sr and sl != sr:
            reason = "tie_to_slur_flagged_diff_pitch"
        else:
            ol, orr = order.get(id(left)), order.get(id(right))
            if ol and orr and ol[0] == orr[0]:
                between = {order[id(h)][1] for h in under
                           if id(h) in order and order[id(h)][0] == ol[0]}
                between -= {ol[1], orr[1]}
                if between:
                    reason = "tie_to_slur_flagged_span"
        if reason:
            for det, key in ((left, "tied_to_next"), (right, "tied_from_prev")):
                if det.get(key):
                    det.pop(key, None)
                    det.setdefault("arc_reclass_removed", []).append(key)
            return reason, pair
        return None
    # The arc never paired, so no tie exports for it today; reclass only where
    # its own span is decisively slur-shaped. A real tie spans a GAP and
    # covers nothing.
    by_voice: dict[int, set[int]] = {}
    for h in under:
        vo = order.get(id(h))
        if vo is not None:
            by_voice.setdefault(vo[0], set()).add(vo[1])
    if any(len(events) > 2 for events in by_voice.values()):
        return "tie_to_slur_unpaired_span", None
    if len(under) == 2:
        a, b = under
        sa, sb = _pitch_step(a.get("pitch")), _pitch_step(b.get("pitch"))
        va, vb = order.get(id(a)), order.get(id(b))
        if (sa and sb and sa != sb and va is not None and vb is not None
                and va[0] == vb[0] and va[1] != vb[1]):
            return "tie_to_slur_unpaired_diff_pitch", None
    return None


def _slur_pieces_for_vetoed_tie(
    arc: list[int],
    pair: tuple[dict[str, Any], dict[str, Any]] | None,
    m_idx: int,
    measures: list[dict[str, Any]],
    staff_of: list[int],
) -> list[tuple[int, list[int]]]:
    """The slur arc(s) a vetoed tie arc becomes, as (measure, bbox) pieces.

    A tie arc FLANKS its two heads — it spans the gap between them — while
    slur coverage (`_noteheads_under`) asks which head centres sit UNDER the
    ink. Moved unchanged, a vetoed flanking arc covers nothing and the
    promised slur silently degrades to a bare deletion. So a PAIRED arc is
    widened to reach both flanked centres; and because coverage is read per
    measure, a widened arc crossing a cell boundary is split AT that boundary
    into the two fragments the engraver would have printed had it been a slur
    — which the ordinary barline merge then rejoins. An UNPAIRED arc keeps
    its own span: its covered run is already what the slur should bind.

    Pieces are fresh lists, never the detection's own `bbox_page` — that is
    the pipeline's output and must not be widened in place.
    """
    ax, ay, aw, ah = arc
    if pair is None:
        return [(m_idx, [ax, ay, aw, ah])]
    centres = [h["bbox_page"][0] + h["bbox_page"][2] / 2.0 for h in pair]
    wx0 = min(ax, min(centres))
    wx1 = max(ax + aw, max(centres))
    home = staff_of[m_idx]
    pieces: list[tuple[int, list[int]]] = []
    for j, measure in enumerate(measures):
        if staff_of[j] != home:
            continue
        box = measure.get("bbox_page_px")
        if not box or len(box) != 4:
            continue
        x0 = max(wx0, float(box[0]))
        x1 = min(wx1, float(box[2]))
        if x1 > x0:
            pieces.append((j, [x0, ay, x1 - x0, ah]))
    # A staff whose cells the span never intersects (no usable bbox_page_px)
    # still gets the widened arc in its own measure, uncut.
    return pieces or [(m_idx, [wx0, ay, wx1 - wx0, ah])]


def _reclass_tie_arcs_in_run(
    measures: list[dict[str, Any]],
    staff_of: list[int],
    per_measure_arcs: list[list[list[int]]],
    order: dict[int, tuple[int, int]],
) -> int:
    """Move impossibly-configured tie arcs into the slur pool, in place.

    A moved arc then rides the ordinary slur machinery — barline merging,
    voice constraint, numbering — exactly as if the detector had classed it
    `slur`. Flank pairing is bounded to each arc's OWN staff, the way
    `_pair_ties_in_staff` is: page x overlaps between systems, and a head
    from another system inside the dx window would alias.
    """
    tie_arcs = _staff_arcs_by_measure(measures, cls="tie")
    if not any(tie_arcs):
        return 0
    heads_by_staff: dict[int, list[dict[str, Any]]] = {}
    for m_idx, measure in enumerate(measures):
        s = staff_of[m_idx]
        for det in measure.get("detections", []):
            bp = det.get("bbox_page")
            if det.get("category") == "notehead" and bp and len(bp) == 4:
                heads_by_staff.setdefault(s, []).append(det)
    n = 0
    dirty: set[int] = set()
    for m_idx, arcs in enumerate(tie_arcs):
        staff_heads = heads_by_staff.get(staff_of[m_idx], [])
        for arc in arcs:
            verdict = _tie_arc_impossibility(arc, staff_heads, order)
            if verdict is None:
                continue
            reason, pair = verdict
            ARC_RECLASS_STATS[reason] += 1
            for j, piece in _slur_pieces_for_vetoed_tie(
                    arc, pair, m_idx, measures, staff_of):
                per_measure_arcs[j].append(piece)
                dirty.add(j)
            n += 1
    for j in dirty:
        per_measure_arcs[j].sort(key=lambda b: b[0])
    return n


def _slur_covers_a_tie(
    covered: list[tuple[int, float, dict[str, Any]]],
    order: dict[int, tuple[int, int]],
) -> bool:
    """Is this slur-classed arc the tie configuration — exactly two covered
    heads, adjacent events of one voice, one pitch? Chords defend themselves:
    a covered chord member brings its mates into `covered` (they share x), so
    the count passes two and the answer is False."""
    if len(covered) != 2:
        return False
    a, b = covered[0][2], covered[1][2]
    if a is b:
        return False
    pa, pb = a.get("pitch"), b.get("pitch")
    if not pa or pa != pb:
        return False
    oa, ob = order.get(id(a)), order.get(id(b))
    return (oa is not None and ob is not None
            and oa[0] == ob[0] and abs(oa[1] - ob[1]) == 1)


def _convert_slur_to_tie(
    covered: list[tuple[int, float, dict[str, Any]]],
    order: dict[int, tuple[int, int]],
) -> None:
    """Mark the two covered heads as a tied pair, earlier event first.

    Only flags actually ADDED are recorded in `arc_reclass_added`, so the
    restore in `annotate_slurs_in_slot` can take the export back to what the
    transcription said — a pair the transcription had already tied loses
    nothing either way.
    """
    a, b = covered[0][2], covered[1][2]
    if order[id(a)][1] > order[id(b)][1]:
        a, b = b, a
    for det, key in ((a, "tied_to_next"), (b, "tied_from_prev")):
        if not det.get(key):
            det[key] = True
            det.setdefault("arc_reclass_added", []).append(key)
    ARC_RECLASS_STATS["slur_to_tie"] += 1


def _resumes_after_system_break(
    measure: dict[str, Any], arc: list[int], spacing: float,
) -> bool:
    """Is this arc the far half of a slur cut by a SYSTEM break?

    A BARLINE cuts one arc in two and both halves end exactly on the cut, so
    each is found by its distance to a cell edge. A SYSTEM break does not work
    that way on the resuming side: the new system's first cell opens with a
    CLEF and a KEY SIGNATURE, so the resuming arc begins well inside it —
    measured at 5.28 staff spaces on the `systems` fixture, and further on any
    score with more accidentals. A constant for that would be a constant for
    how wide a clef is.

    So the anchor is the FIRST NOTE instead, which is what the fragment
    actually attaches to and is independent of the header's width. A resuming
    fragment lies entirely BEFORE that note — it runs in from the margin and
    ends on it (measured: arc x[400,503] against a first notehead centred at
    504). A slur that merely BEGINS on the first note runs the other way, from
    the note rightwards, so the two are told apart by which side of the note
    the ink is on rather than by a threshold.
    """
    heads = _measure_noteheads(measure)
    if not heads:
        return False
    pad = _SLUR_ARC_PAD_NOTEHEADS * (
        sum(h["bbox_page"][2] for h in heads) / len(heads))
    first_centre = min(h["bbox_page"][0] + h["bbox_page"][2] / 2.0 for h in heads)
    ax, _ay, aw, _ah = arc
    return ax < first_centre and (ax + aw) <= first_centre + pad


def _merge_arcs_across_barlines(
    measures: list[dict[str, Any]],
    per_measure_arcs: list[list[list[int]]],
    spacings: list[float],
    tops: list[float | None],
    system_breaks: frozenset[int] = frozenset(),
) -> list[list[tuple[int, list[int]]]]:
    """Chain arcs split by a barline — or by a system break — into one slur each.

    Returns one entry per slur: the `(measure_index, arc_bbox_page)` segments
    it is made of. A slur inside one measure has a single segment; one crossing
    a barline has two; one spanning a whole measure has three.

    The join is geometric and local: an arc that ends ON its cell's right
    boundary is left open, and an arc in the NEXT measure that begins on that
    cell's left boundary at the same height closes it.

    `system_breaks` holds the indices of measures that OPEN a new system, where
    the resuming half is recognised by `_resumes_after_system_break` instead —
    see there for why a cell edge cannot be used on that side. `spacings` and
    `tops` give each measure its own staff's line spacing and top line, because
    a slot spans systems and the two staves are not the same object; a height is
    only comparable between them once it is relative to each one's own lines.
    """
    slurs: list[list[tuple[int, list[int]]]] = []
    # Slurs left hanging at the junction just passed: (slur index, arc y-centre,
    # height above that staff's top line — the only comparable one across a
    # break, where absolute page y differs by a whole system).
    pending: list[tuple[int, float, float]] = []
    for m_idx, (measure, arcs) in enumerate(zip(measures, per_measure_arcs)):
        box = measure.get("bbox_page_px")
        sp = spacings[m_idx]
        if not box or len(box) != 4 or not sp:
            pending = []
            continue
        edge_tol = _SLUR_BOUNDARY_SPACES * sp
        dy_tol = _SLUR_CONTINUATION_DY_SPACES * sp
        cell_x0, _, cell_x1, _ = box
        top = tops[m_idx]
        at_break = m_idx in system_breaks
        still_open: list[tuple[int, float, float]] = []
        for arc in arcs:
            ax, ay, aw, ah = arc
            y_centre = ay + ah / 2.0
            y_rel = (y_centre - top) / sp if top is not None else None
            resumes = (_resumes_after_system_break(measure, arc, sp) if at_break
                       else (ax - cell_x0) <= edge_tol)
            joined = None
            if pending and resumes:
                if at_break:
                    # Across a break the two halves sit at comparable heights
                    # ABOVE OR BELOW THEIR OWN staves; page y says nothing.
                    usable = [p for p in pending if p[2] is not None
                              and y_rel is not None
                              and (p[2] < 0) == (y_rel < 0)]
                    key = lambda p: abs(p[2] - y_rel)          # noqa: E731
                else:
                    usable = pending
                    key = lambda p: abs(p[1] - y_centre)       # noqa: E731
                if usable:
                    nearest = min(usable, key=key)
                    close = (abs(nearest[2] - y_rel) <= _SLUR_CONTINUATION_DY_SPACES
                             if at_break else
                             abs(nearest[1] - y_centre) <= dy_tol)
                    if close:
                        joined = nearest[0]
                        pending.remove(nearest)
            if joined is None:
                slurs.append([])
                joined = len(slurs) - 1
            slurs[joined].append((m_idx, arc))
            if (cell_x1 - (ax + aw)) <= edge_tol:
                still_open.append((joined, y_centre, y_rel))
        # Only the junction just crossed can continue a slur; an arc two
        # measures later is a different slur however well it lines up.
        pending = still_open
    return slurs


def _measure_noteheads(measure: dict[str, Any]) -> list[dict[str, Any]]:
    """The pitched noteheads of one measure — the ones that become notes.

    An unpitched or duration-less detection never survives into an event, so
    anchoring a slur to one would silently drop the slur.
    """
    return [d for d in measure.get("detections", [])
            if d.get("category") == "notehead"
            and d.get("pitch") is not None
            and d.get("duration_beats") is not None
            and len(d.get("bbox_page") or ()) == 4]


def _noteheads_under(
    measures: list[dict[str, Any]],
    segments: list[tuple[int, list[int]]],
    pad_notehead_widths: float = _SLUR_ARC_PAD_NOTEHEADS,
) -> list[tuple[int, float, dict[str, Any]]]:
    """`(measure_index, x_centre, detection)` for the noteheads a slur covers,
    in playing order.

    THE ARC IS NARROWER THAN THE RUN IT BINDS, so its box is padded — the same
    correction `rhythm._beamed_groups` makes to a beam box, for the same kind of
    reason. A slur is drawn from just above (or below) its first notehead to
    just above its last, so the ink stops a hair inside both centres and an
    unpadded test drops the outer note at each end. Measured on the Brahms
    fixture: of the 75 notehead centres lying just outside an arc, 54 sit within
    0.19 notehead widths of its edge and the next is at 0.32 — so the pad is
    read off that gap. Before it, the Contrabass read `n1 -> n4` in bars where
    the truth slurs `n0 -> n5`.

    The position travels with the detection because slur NUMBERS are allocated
    by overlap, which needs to know where each slur starts and stops.
    """
    covered: list[tuple[int, float, dict[str, Any]]] = []
    for m_idx, (ax, _ay, aw, _ah) in segments:
        heads = _measure_noteheads(measures[m_idx])
        if not heads:
            continue
        pad = pad_notehead_widths * (
            sum(h["bbox_page"][2] for h in heads) / len(heads))
        for det in heads:
            box = det["bbox_page"]
            x_centre = box[0] + box[2] / 2.0
            if ax - pad <= x_centre <= ax + aw + pad:
                covered.append((m_idx, x_centre, det))
    covered.sort(key=lambda t: (t[0], t[1]))
    return covered


def _voice_of_notehead(measures: list[dict[str, Any]]) -> dict[int, int]:
    """`id(notehead) -> voice index`, over a whole staff.

    A slur lives inside ONE voice: MusicXML pairs `<slur>` within a `<voice>`
    stream, so a start in voice 1 closed by a stop in voice 2 leaves both ends
    unpaired and the file malformed rather than merely wrong. Measured on the
    Brahms fixture, 3 of 75 slurs did exactly that.
    """
    voice_of: dict[int, int] = {}
    for measure in measures:
        events = group_chords_in_measure(measure.get("detections", []))
        for v_idx, voice_events in enumerate(split_events_into_voices(events)):
            for event in voice_events:
                for head in event.get("noteheads") or []:
                    voice_of[id(head)] = v_idx
    return voice_of


def annotate_slurs_in_staff(staff: dict[str, Any]) -> int:
    """Pair slurs on ONE staff. See `annotate_slurs_in_slot`, of which this is
    the single-staff case — a staff that is not stitched to any other is a part
    one system long."""
    return annotate_slurs_in_slot([staff])


def annotate_slurs_in_slot(staves: list[dict[str, Any]]) -> int:
    """Mark the noteheads that open and close each slur on one PART, in place.

    `staves` is that part's staff on each system, in order — a slot, as
    `_stitch_slots` builds it. Returns the number of slurs marked.

    WHY THIS IS A STAFF PASS AND NOT A MEASURE ONE. Cells are cut per measure,
    so a slur crossing a barline is DETECTED AS TWO ARCS — 120 arcs on the
    Brahms fixture against 82 slurs in the truth. Annotating per measure writes
    two slurs where the music has one, which is what kept an implemented and
    tested `annotate_slurs` out of the exporter until now:

        dynamics only        pooled 0.2595   1811 edits
        dynamics + slurs     pooled 0.2598   1835 edits   `wrong slur` 76 -> 97

    Page pixels are the only frame shared across cells, so the merge is done
    there — the same reason `transcribe._pair_ties_in_staff` works in page
    coordinates to catch ties across a barline. The arc-to-note mapping is the
    part that was always right and is kept.

    NOTHING IN THE EXPORTER NEEDS TO LEARN ABOUT MEASURES. A MusicXML slur is
    already free to open in one measure and close in another; all it needs is a
    number that means the same thing at both ends. So the pass allocates
    numbers over the whole STAFF, releasing one only when its slur has closed,
    and marks the notehead detections — which `group_chords_in_measure` already
    carries into events, the way it carries the tie flags.
    """
    # Idempotent: exporting a result twice must not stack two marks per note.
    # The same sweep takes back whatever an earlier ARC-RECLASS pass changed —
    # tie flags it added come off, tie flags it removed go back on — so a
    # flag-off export after a flag-on one (or a re-export under either) starts
    # from what the transcription itself said.
    for staff in staves:
        for measure in staff.get("measures", []):
            for det in measure.get("detections", []):
                det.pop("slur_states", None)
                for key in det.pop("arc_reclass_added", None) or ():
                    det.pop(key, None)
                for key in det.pop("arc_reclass_removed", None) or ():
                    det[key] = True
    # Without a staff's own line spacing there is no unit to measure a boundary
    # in, and a rule in raw pixels would mean a different thing on every page.
    # Such a staff is skipped, and it also ENDS the chain — nothing is joined
    # across a staff that cannot be measured — so the slot is paired in
    # contiguous runs rather than being abandoned whole.
    runs: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for staff in staves:
        geom = staff.get("staff_geometry") or {}
        if staff.get("measures") and geom.get("line_spacing_px"):
            current.append(staff)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return sum(_pair_slurs_in_run(run) for run in runs)


def _flatten_run(staves: list[dict[str, Any]]) -> tuple[
        list[dict[str, Any]], list[float], list[float | None], frozenset[int]]:
    """One measure sequence for a run of staves, with each measure's geometry.

    Returns `(measures, spacings, tops, system_breaks)`. `system_breaks` holds
    the indices of measures that OPEN a new system — those junctions are system
    breaks and not barlines, and the two are recognised differently (see
    `_resumes_after_system_break`).

    The per-measure geometry is carried BESIDE the measures rather than stashed
    on them: the result dict is the pipeline's output and export must not leave
    private keys in it.
    """
    measures: list[dict[str, Any]] = []
    spacings: list[float] = []
    tops: list[float | None] = []
    staff_of: list[int] = []
    breaks: set[int] = set()
    for s_idx, staff in enumerate(staves):
        geom = staff["staff_geometry"]
        lines = geom.get("line_ys_page")
        if measures:
            breaks.add(len(measures))
        for measure in staff["measures"]:
            measures.append(measure)
            spacings.append(float(geom["line_spacing_px"]))
            tops.append(float(min(lines)) if lines else None)
            staff_of.append(s_idx)
    return measures, spacings, tops, staff_of, frozenset(breaks)


def _paired_spans(
    measures: list[dict[str, Any]],
    per_measure_boxes: list[list[list[int]]],
    spacings: list[float],
    tops: list[float | None],
    breaks: frozenset[int],
    voice_of: dict[int, int],
    reclass: bool = False,
    order: dict[int, tuple[int, int]] | None = None,
) -> list[tuple[tuple[int, float], tuple[int, float],
                dict[str, Any], dict[str, Any]]]:
    """`(start_key, stop_key, first_notehead, last_notehead)` per SLUR.

    Split out of `_pair_slurs_in_run` when hairpins arrived, on the expectation
    that the two would share it — a hairpin is also a curve over several notes,
    cut into pieces by the same crop and rejoined in the same page pixels. They
    share everything on either side of this and NOT this: `_noteheads_under`
    asks which noteheads the ink COVERS, and a hairpin covers none of the notes
    it applies to (0 of 4 measured). The wedge pass has `_wedge_anchors`
    instead. Kept factored out because the two halves it does share — the
    two-note minimum and the one-voice rule — are stated here once, and
    `_wedge_anchors` cites them rather than restating them.
    """
    spans = []
    for segments in _merge_arcs_across_barlines(
            measures, per_measure_boxes, spacings, tops, breaks):
        covered = _noteheads_under(measures, segments)
        # Two adjacent same-pitch heads and nothing else under the (merged)
        # arc: the tie configuration, whatever the detector called it — the
        # OMR_ARC_RECLASS slur->tie veto, applied before the span filters
        # because the canonical tie crosses a barline and arrives here as two
        # slur fragments (the merge above is what makes it one arc again).
        if reclass and _slur_covers_a_tie(covered, order or {}):
            _convert_slur_to_tie(covered, order or {})
            continue
        # A span needs two notes to join. One or none leaves an unpaired
        # <slur type="start"> — or a hairpin that never stops — which makes the
        # file invalid rather than merely wrong.
        if len(covered) < 2 or covered[0][2] is covered[-1][2]:
            continue
        # Both ends must belong to the same voice, for the same reason: the
        # two halves of a span split across voices are each unpaired. Prefer
        # the longest run the curve covers WITHIN one voice over dropping it.
        voice = voice_of.get(id(covered[0][2]), 0)
        in_voice = [c for c in covered if voice_of.get(id(c[2]), 0) == voice]
        if len(in_voice) < 2 or in_voice[0][2] is in_voice[-1][2]:
            continue
        start_m, start_x, first = in_voice[0]
        stop_m, stop_x, last = in_voice[-1]
        spans.append(((start_m, start_x), (stop_m, stop_x), first, last))
    return spans


def _number_spans(
    spans: list[tuple],
    max_number: int,
) -> list[tuple[int, tuple]]:
    """Allocate MusicXML `number=` levels, reusing one as soon as it closes.

    A staff of ordinary non-overlapping spans is numbered 1, 1, 1 … and only
    genuine overlap spends a second number. Spans past the level ceiling are
    DROPPED rather than renumbered — six open at once is already pathological
    and a seventh would have to reuse a live number, which is worse than
    silence.

    Shared by slurs and hairpins; each caller numbers its own kind, because a
    `<slur number="1">` and a `<wedge number="1">` name different things and
    cannot collide.
    """
    spans = sorted(spans, key=lambda s: s[0])
    open_spans: dict[int, tuple[int, float]] = {}   # number -> where it stops
    out: list[tuple[int, tuple]] = []
    for span in spans:
        start_key, stop_key = span[0], span[1]
        # STRICTLY before: a span that begins exactly where another ends takes
        # a fresh number, so no note ever carries the same number twice and a
        # stop-then-start on one note stays two readable spans rather than an
        # ambiguous pair.
        for number, open_stop in list(open_spans.items()):
            if open_stop < start_key:
                del open_spans[number]
        number = next((n for n in range(1, max_number + 1)
                       if n not in open_spans), None)
        if number is None:
            continue
        out.append((number, span))
        open_spans[number] = stop_key
    return out


def _pair_slurs_in_run(staves: list[dict[str, Any]]) -> int:
    """`annotate_slurs_in_slot` over staves that all carry five-line geometry."""
    measures, spacings, tops, staff_of, breaks = _flatten_run(staves)
    if not measures:
        return 0

    per_measure_arcs = _staff_arcs_by_measure(measures)
    reclass = _arc_reclass_enabled()
    order: dict[int, tuple[int, int]] = {}
    if reclass:
        order = _event_order_of_noteheads(measures)
        # Tie arcs the grammar refutes join the slur pool BEFORE merging, so
        # a reclassed arc gets the same barline treatment a slur-classed one
        # would have had.
        _reclass_tie_arcs_in_run(measures, staff_of, per_measure_arcs, order)
    if not any(per_measure_arcs):
        return 0

    spans = _paired_spans(measures, per_measure_arcs, spacings, tops,
                          breaks, _voice_of_notehead(measures),
                          reclass=reclass, order=order)
    n_marked = 0
    for number, (_start, _stop, first, last) in _number_spans(
            spans, _MAX_SLUR_NUMBER):
        first.setdefault("slur_states", []).append((number, "start"))
        last.setdefault("slur_states", []).append((number, "stop"))
        n_marked += 1
    return n_marked


# A hairpin arrives under one class per direction. Nothing else in the
# `dynamic` category is a span — the letter glyphs are points — so the two are
# named rather than pattern-matched.
_WEDGE_CLASSES = {
    "dynamicCrescendoHairpin": "crescendo",
    "dynamicDiminuendoHairpin": "diminuendo",
}
# MusicXML numbers simultaneous wedges 1-6, exactly as it does slurs. A
# `<wedge number="1">` and a `<slur number="1">` name different things, so the
# two families are numbered independently.
_MAX_WEDGE_NUMBER = 6
# How far past a hairpin's edge a notehead centre may sit and still count as
# ON that edge, in notehead widths. Inherited from `_SLUR_ARC_PAD_NOTEHEADS`
# and NOT independently measured — it softens a boundary rather than deciding
# one, because the anchor rule below falls back to the nearest note on the
# other side rather than abstaining. Sweep it when a corpus of read hairpins
# exists; there are four in the fixture set today.
_WEDGE_ANCHOR_PAD_NOTEHEADS = 0.25
#: Which note a hairpin STARTS on, out of the two readings its left edge admits.
#:
#:   "nearest"  the note whose centre is nearest the edge, either side of it.
#:   "before"   the last note at or before the edge.
#:
#: ⚠️ MEASURED, and "before" is the one that looks right and is not. A hairpin
#: is drawn in the space AROUND its note rather than after it: on the
#: Tchaikovsky 6 fixture the ink begins 26 px LEFT of the note it starts on and
#: 105 px right of the previous one, so "before" reaches back past the answer
#: every time. Scored against the truth's own spans over the 11-work benchmark
#: (`benchmarks/omr-hairpins-2026-09/probe_stop_rule.py`): "before" pairs 1 of
#: 8 truth hairpins and gets 1 exactly right; "nearest" pairs 4 and gets all 4
#: exactly right, at every stop reach below the cliff.
_WEDGE_START_RULE = "nearest"
#: How far past a hairpin's right edge the note it is AIMING AT may stand, in
#: notehead widths — see `_wedge_anchors` for what this decides.
#:
#: ⚠️ THIS IS THE MIDDLE OF A PLATEAU THAT NOTHING IN THE CORPUS EXERCISES, and
#: that is a weaker claim than the constants around it. Every value from 0.0 to
#: 1.5 scores identically (4 exact) and 2.0 breaks Mahler's — but it scores
#: identically because the branch never FIRES: all five hairpins we export end
#: under a note still sounding, so 0.0 would do as well. The other shape is
#: real — the Mahler truth's own `m5 -> m6` crescendo ends on the next bar's
#: downbeat — and it is unmeasurable here because that hairpin's detection
#: landed on the empty staff below (see `_dedupe_cross_staff_detections`). So
#: this is chosen to handle that shape when it arrives, inside a range known
#: not to hurt, rather than read off a gap in a population.
_WEDGE_STOP_REACH_NOTEHEADS = 1.0


def _wedge_anchors(
    measures: list[dict[str, Any]],
    segments: list[tuple[int, list[int]]],
    voice_of: dict[int, int],
) -> tuple[tuple[int, float], tuple[int, float],
           dict[str, Any], dict[str, Any]] | None:
    """The notes one hairpin opens and closes on, or None if it has none.

    ⚠️ **A SLUR IS DRAWN OVER ITS NOTES; A HAIRPIN IS DRAWN BETWEEN THEM.**
    That is the one place these two spanners stop being the same problem, and
    reusing `_noteheads_under` here — the obvious move, and the first one
    tried — returns NOTHING on real hairpins. Measured on the engraved Mahler
    5 fixture, the only page in the benchmark set whose hairpins the detector
    reads: its Trumpet staff prints a diminuendo at page x 5922-6068 in a bar
    whose only notehead spans 5817-5897. The hairpin does not overlap the note
    it applies to by a single pixel, because the engraver drew it in the gap
    the note leaves. Every one of the four detections behaves that way, and an
    overlap test scores 0 of 4.

    So the edges are read as POINTERS rather than as a cover: the start is the
    last note at or before the left edge, the stop the first note at or after
    the right edge. Where there is none on the wanted side — a hairpin drawn
    entirely before its staff's first note — the nearest note on the other side
    stands in, which is why the pad above softens a boundary rather than
    deciding one.

    The search is bounded to the measures the hairpin's own ink touches, PLUS
    ONE either side. The `+1` is not slack: the truth's own crescendo on that
    page runs `m5 -> m6`, ending on the next bar's downbeat, which is where
    hairpins ordinarily end. Anything wider would let a staff that rests for
    four bars donate an anchor from the far side of them.
    """
    first_m, last_m = segments[0][0], segments[-1][0]
    left = segments[0][1][0]
    right = segments[-1][1][0] + segments[-1][1][2]
    lo, hi = max(0, first_m - 1), min(len(measures) - 1, last_m + 1)

    candidates: list[tuple[int, float, dict[str, Any]]] = []
    widths: list[float] = []
    for m_idx in range(lo, hi + 1):
        for det in _measure_noteheads(measures[m_idx]):
            box = det["bbox_page"]
            candidates.append((m_idx, box[0] + box[2] / 2.0, det))
            widths.append(float(box[2]))
    # ⚠️ ONE ANCHOR IS ENOUGH — Sean's rule, 2026-09-05. This required TWO
    # candidate noteheads, which throws the hairpin away in exactly the case a
    # scan produces most: the ink is read correctly, the bar it belongs to is
    # found, and the detector recovered only one of the notes under it. The
    # start is the anchor that matters — it says which measure and which voice
    # the wedge opens in — and the stop already tolerates landing on the SAME
    # note (see the equal-is-allowed note below), which is the shape a hairpin
    # drawn under one long note has anyway. Requiring a second note asked the
    # page for a fact the wedge does not need.
    #
    # Measured on the eleven scored scan pages: 116 -> 118 exported `<wedge>`
    # of 198, entirely from Mahler 5 p2, which goes 4 -> 6 against a truth of
    # exactly 6. The six pages that carry no hairpin stay at 0 — the abstention
    # that makes the CV reader trustworthy is untouched. All ELEVEN engraved
    # orchestral exports are byte-identical (sha1), so OMR-NED cannot move.
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))
    pad = _WEDGE_ANCHOR_PAD_NOTEHEADS * (sum(widths) / len(widths))

    if _WEDGE_START_RULE == "before":
        before = [c for c in candidates if c[1] <= left + pad]
        start = before[-1] if before else candidates[0]
    else:
        start = min(candidates, key=lambda c: (abs(c[1] - left), c[0], c[1]))
    # Both ends in ONE voice, for the reason `_paired_spans` gives: MusicXML
    # pairs a wedge within a `<voice>` stream, and LilyPond within a Voice
    # context. The stop is chosen from the start's voice rather than the two
    # being compared afterwards, so a staff with a second voice loses coverage
    # rather than losing the hairpin.
    voice = voice_of.get(id(start[2]), 0)
    same_voice = [c for c in candidates if voice_of.get(id(c[2]), 0) == voice]
    # ⚠️ THE RIGHT EDGE ADMITS TWO READINGS AND THE PAGE CANNOT BE ASKED WHICH.
    # A hairpin can END ON a note — `... \\!` on the next attack, which is where
    # a crescendo into a downbeat stops — or it can END UNDER one, drawn in the
    # space a long note leaves, in which case the note it started on is also the
    # note it stops on. Both shapes are in the Mahler 5 truth: two of its three
    # hairpins span ONE note and the third runs `m5 -> m6`.
    #
    # What separates them is how close the next attack stands to the ink's end.
    # A hairpin aiming at a note is drawn up to it; one decaying under a held
    # note stops in open space. So the next note is taken as the stop only if it
    # is within reach, and otherwise the hairpin closes on the note still
    # sounding.
    after = [c for c in same_voice if c[1] >= right - pad]
    under = [c for c in same_voice if c[1] <= right + pad]
    width = sum(widths) / len(widths)
    aimed = (after[0] if after
             and (after[0][1] - right) <= _WEDGE_STOP_REACH_NOTEHEADS * width
             else None)
    stop = aimed or (under[-1] if under
                     else (after[0] if after else same_voice[-1]))
    # EQUAL is allowed: a hairpin under one long note starts and stops on the
    # same notehead, and MusicXML says so with a start, a note and a stop. Only
    # a stop BEFORE its start is impossible.
    if (start[0], start[1]) > (stop[0], stop[1]):
        return None
    return (start[0], start[1]), (stop[0], stop[1]), start[2], stop[2]


def _staff_hairpins_by_measure(
    measures: list[dict[str, Any]], kind: str,
) -> list[list[list[int]]]:
    """Each measure's hairpins OF ONE KIND, in page pixels, left to right.

    Split by kind before the barline merge, so a crescendo whose ink ends on a
    cell boundary can never be continued by the diminuendo that starts the next
    bar at the same height. That pair is a hairpin turning around — the
    commonest shape there is — and joining them would report one long
    crescendo where the page prints `<` then `>`.
    """
    return _staff_boxes_by_measure(
        measures,
        lambda d: (d.get("category") == "dynamic"
                   and _WEDGE_CLASSES.get(d.get("class") or "") == kind),
    )


def annotate_wedges_in_staff(staff: dict[str, Any]) -> int:
    """Pair hairpins on ONE staff. See `annotate_wedges_in_slot`."""
    return annotate_wedges_in_slot([staff])


def annotate_wedges_in_slot(staves: list[dict[str, Any]]) -> int:
    """Mark the noteheads a crescendo or diminuendo opens and closes, in place.

    The NINTH export gap, and the same shape as the eight before it: the
    detector fires `dynamicCrescendoHairpin` / `dynamicDiminuendoHairpin`
    freely and nothing downstream ever mentioned either class, so `<wedge>` was
    absent from every file the exporter has ever written. Unlike the first
    eight, detection here is PARTIAL rather than complete — Mahler's truth has
    6 hairpins and the detector finds 4 — so closing it cannot make the reading
    complete, only present.

    WHY THIS IS A STAFF PASS AND NOT A MEASURE ONE — the same reason as
    `annotate_slurs_in_slot`, which see. Cells are cut per measure, so a
    hairpin crossing a barline is detected as two boxes, and page pixels are
    the only frame in which the halves can be rejoined.

    WHY THE ANCHORS ARE NOTEHEADS RATHER THAN AN x POSITION. A `<wedge>` is a
    `<direction>` and could be placed by x the way a dynamic letter is — but
    music21 reads a wedge as a SPANNER: the `crescendo` element attaches to the
    next note parsed and the `stop` to the last note parsed before it, and
    musicdiff then scores the wedge by that pair's offset and duration. So what
    the metric compares is WHICH NOTES the hairpin runs between, and anchoring
    to notes answers exactly that question. It is also what LilyPond needs,
    where `\\<` and `\\!` are post-events on notes. Which notes those are is
    `_wedge_anchors`, and it is NOT the slur rule — see there.

    Consequently a hairpin printed over a staff the detector found NO notes in
    cannot be exported: it has nothing to attach to at either end. That is a
    ceiling of the anchoring rather than a bug in it — a wedge start with no
    note after it is silently dropped by music21 too.
    """
    # Idempotent, like the slur pass: exporting twice must not stack marks.
    for staff in staves:
        for measure in staff.get("measures", []):
            for det in measure.get("detections", []):
                det.pop("wedge_states", None)
    runs: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for staff in staves:
        geom = staff.get("staff_geometry") or {}
        if staff.get("measures") and geom.get("line_spacing_px"):
            current.append(staff)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return sum(_pair_wedges_in_run(run) for run in runs)


def _pair_wedges_in_run(staves: list[dict[str, Any]]) -> int:
    """`annotate_wedges_in_slot` over staves that all carry five-line geometry."""
    measures, spacings, tops, _staff_of, breaks = _flatten_run(staves)
    if not measures:
        return 0

    per_kind = {kind: _staff_hairpins_by_measure(measures, kind)
                for kind in sorted(set(_WEDGE_CLASSES.values()))}
    if not any(any(boxes) for boxes in per_kind.values()):
        return 0

    voice_of = _voice_of_notehead(measures)
    # The kind travels WITH the span rather than in a lookup keyed on its first
    # notehead: a diminuendo and a crescendo can legitimately open on the same
    # note, and a lookup would give one of them the other's direction.
    spans: list[tuple] = []
    for kind, boxes in per_kind.items():
        if not any(boxes):
            continue
        for segments in _merge_arcs_across_barlines(
                measures, boxes, spacings, tops, breaks):
            anchors = _wedge_anchors(measures, segments, voice_of)
            if anchors is not None:
                spans.append(anchors + (kind,))

    # Numbered across BOTH kinds together: a diminuendo that overlaps a
    # crescendo is a second open wedge and needs its own level, whichever way
    # round the two are drawn.
    n_marked = 0
    for number, (_start, _stop, first, last, kind) in _number_spans(
            spans, _MAX_WEDGE_NUMBER):
        first.setdefault("wedge_states", []).append((number, kind))
        last.setdefault("wedge_states", []).append((number, "stop"))
        n_marked += 1
    return n_marked


def _event_tuplet(event: dict[str, Any]) -> tuple[dict[str, int], int] | None:
    """`({"actual": 3, "normal": 2}, group_id)` for a tuplet event, else None.

    Read off the event's FIRST notehead, the same way `annotate_beams` reads
    `beam_levels`, so nothing in `voicing` has to learn about tuplets. A rest
    never carries one — see the note in `rhythm.resolve_rhythms_for_cell`.
    """
    heads = event.get("noteheads") or []
    if not heads:
        return None
    ratio = heads[0].get("tuplet")
    if not ratio:
        return None
    return ratio, int(heads[0].get("tuplet_group") or 0)


def _tuplet_runs(events: list[dict[str, Any]]) -> list[tuple[int, int, dict[str, int]]]:
    """Maximal runs of consecutive events sharing one tuplet group.

    Consecutive matters: two triplets in a row are two brackets, and a run
    broken by a plain note is two runs even inside one group id.
    """
    runs: list[tuple[int, int, dict[str, int]]] = []
    start = None
    current: tuple[dict[str, int], int] | None = None
    for i, event in enumerate(events):
        info = _event_tuplet(event)
        key = info[1] if info else None
        prev_key = current[1] if current else None
        if key is None or key != prev_key:
            if current is not None and start is not None:
                runs.append((start, i - 1, current[0]))
            start, current = (i, info) if info else (None, None)
    if current is not None and start is not None:
        runs.append((start, len(events) - 1, current[0]))
    return runs


def _direction_slots(
    events: list[dict[str, Any]],
    directions: list[tuple[float, str, str]] | None,
) -> dict[int, list[tuple[str, str]]]:
    """Which event each direction is emitted before: `{event_index: [(kind, text)]}`.

    The rule has three clauses, and each one is a case the other two get wrong.
    Scored against the truth's own offsets for all 47 marks on the benchmark
    (`benchmarks/omr-direction-text-2026-09/score_placement_rules.py`):

        rule                                     misplaced   direction edits
        first event at or past x  (was shipped)      4              54
        nearest event                               12              54
        nearest NOTE                                 4              40
        nearest note, keeping the tail               3              40   <-

    1. **A mark to the right of every event keeps the past-the-end position.**
       It is the only clause that survived from the previous rule, and it earns
       its place on a bar where a note was MISSED: Brahms's Bassoon 2 detects
       one note where the truth has two, and its `legato` — printed under the
       second — falls past everything. Landing after what we did detect puts it
       at beat 1.5, which is right. Snapping it back to the one note we have
       puts it at 0.0, which is not.

    2. **Otherwise, the NEAREST event.** A mark is printed at the note it
       applies to, and its left edge sits on either side of that note with no
       consistent bias: measured in canonical pixels on one Brahms page,
       `legato` begins 48 px LEFT of its note and `pesante` 47 px RIGHT of its
       own. A mark is set against its own width, and a word's width has nothing
       to do with the music. Taking the first note at or past the left edge
       therefore overshoots whenever a mark starts right of its note — which is
       what sent `pesante` to beat 1.5 where the truth says 1.0, and musicdiff
       charges the whole word twice for that: deleted where we put it, inserted
       where it belongs.

    3. **Rests are not candidates.** This is what a plain nearest rule gets
       wrong, and it is worth 14 edits on its own. A rest occupies x-space, so
       nearness can reach BACKWARDS onto one: Beethoven 5's `ff` belongs to the
       note at beat 0.5 and is printed after an eighth rest at 0.0, standing
       nearer the rest than the note. You do not mark a rest `ff` or `legato`,
       so a rest is never the answer — unless the bar is nothing but rests, in
       which case nearness among everything is all there is.

    Ties go FORWARD, to the later event, which is the direction the mark's own
    text runs in.

    An index of `len(events)` means "after everything" — clause 1's answer, and
    also where a mark goes when `events` is empty.

    ⚠️ That last case is NOT how an empty bar is exported, and reading it that
    way is what let the bug live: a measure with no events never reaches this
    function at all, because it takes the whole-measure-rest path. See
    `_mxl_empty_measure`, which is where an empty bar's marks are actually
    written.

    ⚠️ **What this rule CANNOT fix, and do not try to make it.** Two of the
    three remaining misplaced words on the benchmark are not misplaced at all:
    they sit on the correct EVENT, and the event sits at the wrong time because
    an earlier note in the bar lost its augmentation dot. Brahms staff 2 reads
    `[1.0, 1.5]` where the truth has `[1.5, 1.5]`, and staff 16 `[1.0, 1.0, 0.5]`
    against `[1.5, 1.0, 0.5]` — both 6/8 bars summing to 2.5. That is the lost-dot
    half of the rhythm budget (`_reconcile_measure_to_meter` moves a beam level
    and not a dot), surfacing here. Correcting the OFFSET while the note keeps
    its wrong duration would put the direction at a time no note in the bar
    occupies, which is worse than being consistently wrong.
    """
    slots: dict[int, list[tuple[str, str]]] = {}
    if not directions:
        return slots
    xs = [event.get("x_position") for event in events]
    placed = [i for i, x in enumerate(xs) if x is not None]
    notes = [i for i in placed if events[i].get("kind") != "rest"]
    last_x = max((xs[i] for i in placed), default=None)

    for x, kind, text in sorted(directions):
        if last_x is None or x > last_x:
            index = len(events)
        else:
            # `-i` breaks a tie towards the LATER event.
            candidates = notes or placed
            index = min(candidates, key=lambda i: (abs(xs[i] - x), -i))
        slots.setdefault(index, []).append((kind, text))
    return slots


def _mxl_voice_events(
    events: list[dict[str, Any]],
    voice: int,
    divisions: int,
    indent: str,
    directions: list[tuple[float, str, str]] | None = None,
) -> tuple[list[str], int]:
    """Render an ordered list of events as MusicXML <note> elements with
    the given voice number. Returns (lines, total_duration_units) where
    total_duration_units is the sum of CHORD-LEADING + REST durations
    (chord members past the first don't advance the cursor).

    For chord events with tie flags set, only the FIRST notehead carries
    the <tie>/<tied> markers — MusicXML treats a chord's first note as
    its representative for tie/articulation marks.
    """
    lines: list[str] = []
    total_dur = 0
    # Tuplet bracket ends, by event index, so `type="start"`/`"stop"` land on
    # the run's outer notes rather than on every note in it.
    tuplet_state_at: dict[int, str] = {}
    for first, last, _ratio in _tuplet_runs(events):
        tuplet_state_at[first] = "start"
        tuplet_state_at[last] = "stop"
    # `<direction>` carries no duration, so it applies where it SITS in the
    # element order — before the note it belongs to.
    direction_at = _direction_slots(events, directions)
    for event_index, event in enumerate(events):
        for item in direction_at.get(event_index, ()):
            lines.append(_mxl_direction(item, indent))
        # A hairpin OPENS before the note it covers and CLOSES after it, and
        # that is not a stylistic choice: music21 attaches a `crescendo` to the
        # next note it parses and a `stop` to the last note it parsed, so the
        # element order IS the pair of notes the wedge spans.
        for number, kind in (event.get("wedge_states") or []):
            if kind != "stop":
                lines.append(_mxl_wedge(number, kind, indent))
        _, xml_type, dots = _duration_to_lily_xml(
            event["duration_type"], event.get("dots", 0)
        )
        beats = event["duration_beats"]
        dur_units = max(1, int(round(beats * divisions)))
        tuplet_info = _event_tuplet(event)
        time_modification = tuplet_info[0] if tuplet_info else None
        tuplet_state = tuplet_state_at.get(event_index)
        tied_to_next = bool(event.get("tied_to_next"))
        tied_from_prev = bool(event.get("tied_from_prev"))
        if event["kind"] == "rest":
            lines.append(_mxl_note(
                None, "", xml_type, dots, beats, divisions,
                is_chord=False, is_rest=True, indent=indent, voice=voice,
                fermata=bool(event.get("fermata")),
            ))
            total_dur += dur_units
        else:
            beam_states = event.get("beam_states")
            for ni, nh in enumerate(event["noteheads"]):
                lines.append(_mxl_note(
                    nh.get("pitch"), "", xml_type, dots, beats, divisions,
                    is_chord=(ni > 0), is_rest=False,
                    indent=indent, voice=voice,
                    tied_to_next=(tied_to_next and ni == 0),
                    tied_from_prev=(tied_from_prev and ni == 0),
                    # A chord is beamed and slurred once, through its first note.
                    beam_states=(beam_states if ni == 0 else None),
                    slur_states=(event.get("slur_states") if ni == 0 else None),
                    # The ratio applies to every chord member — it is what the
                    # note is worth — but the bracket is drawn once.
                    time_modification=time_modification,
                    tuplet_state=(tuplet_state if ni == 0 else None),
                    # Printed once against the chord, like the beam and the
                    # slur, and hung off its first <note>.
                    articulations=(event.get("articulations") if ni == 0
                                   else None),
                    # A chord takes one fermata, through its first note.
                    fermata=(bool(event.get("fermata")) and ni == 0),
                    # ...but an accidental belongs to the NOTEHEAD. A chord can
                    # carry one on any subset of its members, so this is the
                    # one per-note mark here that must not be first-note-only.
                    accidental=nh.get("accidental"),
                ))
            # Only the chord's first note advances the time cursor; chord
            # members past the first share its onset.
            total_dur += dur_units
        for number, kind in (event.get("wedge_states") or []):
            if kind == "stop":
                lines.append(_mxl_wedge(number, kind, indent))
    # Anything with no note to attach to still belongs to this measure.
    for item in direction_at.get(len(events), ()):
        lines.append(_mxl_direction(item, indent))
    return lines, total_dur


def _first_clef_bearing_measure(measures: list[dict[str, Any]]) -> int:
    """Index of the measure whose clef speaks for the part's OPENING.

    A measure's `clef` field is the clef in EFFECT there, and on the staff's
    leading cells that can be nothing but the positional default: `transcribe`
    reads a clef where one is printed, and system furniture caught as a measure
    — a brace, a courtesy meter after the final barline — prints none. Taking
    the opening clef from measure 0 regardless is what exported Dvorak 9's
    bassoon, both trombones, the timpani, the viola, the cello and the
    contrabass as G2 on a page whose per-measure clefs are right from measure 1
    onwards: measure 0 is a 56-px cell holding one `brace` detection.

    Brahms 1 is the control that names the mechanism. Its spurious cell is at
    the END of the system, so measure 0 is genuine, and it exports all fourteen
    clefs correctly including an alto and a tenor. Same pipeline, same page
    shape, opposite end — the only difference is which measure the export asked.

    So the answer is the first measure that could have READ a clef or could
    have USED one:

      - it holds a `clef` detection, so its clef is a reading rather than an
        inheritance; or
      - it holds music, so whatever clef was in effect there is the clef the
        exported pitches were resolved under.

    **Both conditions are load-bearing.** Without the first, this would
    overrule a genuine clef printed at a system head. Without the second, it
    could claim an opening clef under which notes already written out were not
    resolved — the measures it skips emit a whole-measure rest either way, so
    skipping them cannot move a single pitch.

    Returns 0 — today's behaviour exactly — when no measure qualifies.
    """
    for index, measure in enumerate(measures):
        dets = measure.get("detections") or []
        if any(d.get("category") == "clef" for d in dets):
            return index
        if group_chords_in_measure(dets):
            return index
    return 0


def _staff_measures_xml(
    staff: dict[str, Any],
    divisions: int,
    start_number: int,
    state: dict[str, Any],
    pair_spanners: bool = True,
) -> list[str]:
    """One staff's measures as `<measure>` blocks.

    `state` carries the clef, key and time last written, and whether the
    `<divisions>` have been emitted yet, so that a part stitched from several
    systems restates an attribute only where it actually CHANGES — which is what
    MusicXML means by an attribute — instead of once per system. Pass a fresh
    dict for a part that begins here.
    """
    # A slur is a fact about the PART, because the arc crossing a barline — or a
    # system break — is cut in two and only page coordinates can rejoin it. The
    # marks land on the notehead detections, which `group_chords_in_measure`
    # lifts onto events below the way it lifts the tie flags.
    #
    # `pair_spanners=False` is for the STITCHED caller, which has the whole slot
    # and has already paired it. Re-pairing here would see one system at a time
    # and, because the pass clears before it marks, would erase exactly the
    # cross-system slurs the slot pass just found. A hairpin is paired the same
    # way and for the same reason, so the two travel together.
    if pair_spanners:
        annotate_slurs_in_staff(staff)
        annotate_wedges_in_staff(staff)

    clef = staff.get("clef")
    key_sig = staff.get("key_signature")
    time_sig = staff.get("time_signature")
    measures = staff.get("measures", [])

    # The part's opening clef, and every measure before the one that supplied
    # it. `not state` is what says this staff BEGINS the part: a later system's
    # staff continues one, and its own first measure is a genuine continuation
    # rather than an opening. The whole leading RUN is overridden, not just
    # measure 0 — leaving the second furniture cell on the default would emit a
    # clef change back to it and another one away again.
    lead = _first_clef_bearing_measure(measures) if not state else 0
    lead_clef = (measures[lead].get("clef") or clef) if lead else None

    out: list[str] = []
    for m_idx, measure in enumerate(measures):
        m_clef = lead_clef if m_idx < lead else (measure.get("clef") or clef)
        m_key = measure.get("key_signature") or key_sig
        m_time = measure.get("time_signature") or time_sig

        attrs_clef = m_clef if (m_clef != state.get("clef")) else None
        attrs_key = m_key if (m_key != state.get("key")) else None
        attrs_time = m_time if (m_time != state.get("time")) else None
        include_divisions = not state.get("divisions_written")
        has_attrs = include_divisions or attrs_clef or attrs_key or attrs_time

        inner = []
        if has_attrs:
            inner.append(_mxl_attributes_block(
                attrs_clef, attrs_key, attrs_time, divisions,
                "      ", include_divisions,
            ))
        state["clef"] = m_clef
        state["key"] = m_key
        state["time"] = m_time
        state["divisions_written"] = True

        events = group_chords_in_measure(measure.get("detections", []))
        voices = split_events_into_voices(events)
        # Per voice: interleaved voices would break each other's runs.
        for _voice_events in voices:
            annotate_beams(_voice_events, measure.get("detections", []))
            annotate_fermatas(_voice_events, measure.get("detections", []))
        # Marks belong to the staff, not to a voice, so they go on voice 1
        # rather than being emitted once per voice. The dynamics the detector
        # drew and the words `direction_text` read are both `<direction>`
        # elements placed by x, and belong to the staff for the same reason.
        _dyn = measure_directions(measure)

        if not events:
            inner.extend(_mxl_empty_measure(
                m_time, divisions, _dyn, "      ",
                fermata=measure_has_fermata(measure.get("detections", [])),
                wedges=eventless_wedges(measure.get("detections", []))))
        elif len(voices) == 1:
            v1_lines, _ = _mxl_voice_events(
                voices[0], voice=1, divisions=divisions, indent="      ",
                directions=_dyn,
            )
            inner.extend(v1_lines)
        else:
            v1_lines, v1_dur = _mxl_voice_events(
                voices[0], voice=1, divisions=divisions, indent="      ",
                directions=_dyn,
            )
            inner.extend(v1_lines)
            if v1_dur > 0:
                inner.append(
                    "      <backup>\n"
                    f"        <duration>{v1_dur}</duration>\n"
                    "      </backup>"
                )
            v2_lines, _ = _mxl_voice_events(
                voices[1], voice=2, divisions=divisions, indent="      ",
            )
            inner.extend(v2_lines)

        out.append(
            f"    <measure number=\"{start_number + m_idx}\">\n"
            + "\n".join(inner)
            + "\n    </measure>"
        )
    return out


def _is_fragmented_row(staves: list[dict[str, Any]]) -> bool:
    """The layout detector sometimes splits one melodic line into many
    "staves" of a single measure each (vertically-stacked single-line music).
    Emitting those as parallel parts would be wrong; they are one part."""
    return (
        len(staves) > 2
        and all(len(s.get("measures", [])) == 1 for s in staves)
    )


def _stitch_slots(result: dict[str, Any]) -> list[list[dict[str, Any]]] | None:
    """Group every system's staves into continuous parts, or return None.

    A part is not a staff on a system, it is the same staff on every system of
    the piece — and until this existed the exporter emitted one `<part>` per
    (page, system, staff), so a two-page piano prelude came out as twenty-four
    parts rather than two, and `orchestral_eval` had to keep its excerpts down
    to a single page to stay scoreable at all.

    The join is by ORDINAL: the second staff of one system is the second staff
    of the next. That is only sound while every system agrees on how many
    staves it has, so this returns None the moment they do not — which is a
    real case, not a corner one. Printed orchestral scores suppress tacet
    staves, and on the Beethoven 5 scan the two systems of a single page hold
    11 and 8. Joining those by position would silently graft the horn's music
    onto the trumpet's, so the exporter keeps its old per-system parts there and
    the caller can see it did from the part names.
    """
    systems = [
        system
        for page in result.get("pages", [])
        for system in page.get("systems", [])
        if system.get("staves")
    ]
    if not systems:
        return None
    # One system stitches to itself: the measures come out the same and the
    # per-system path keeps its richer coordinate part names, piano grouping
    # and fragmented-row handling. Only engage where stitching changes anything.
    if len(systems) == 1:
        return None
    sizes = {len(system["staves"]) for system in systems}
    if len(sizes) != 1:
        return None
    if any(_is_fragmented_row(system["staves"]) for system in systems):
        return None
    slots: list[list[dict[str, Any]]] = [[] for _ in range(sizes.pop())]
    for system in systems:
        for ordinal, staff in enumerate(system["staves"]):
            slots[ordinal].append(staff)
    return slots


def to_musicxml(result: dict[str, Any]) -> str:
    """Serialize a transcribe.py result to a MusicXML score-partwise XML
    string. One <part> per (page, system, position-within-system) staff.

    Systems with exactly 2 staves are wrapped in a `<part-group>` with
    `<group-symbol>brace</group-symbol>` so they render as a piano
    grand-staff.

    Voice handling: when a measure has both stem-up and stem-down chord
    events (per `voicing.split_events_into_voices`), voice 1 emits first,
    then a `<backup>` element rewinds the time cursor by voice 1's total
    duration, then voice 2 emits. This matches what the LilyPond exporter
    does with `\\voiceOne` / `\\voiceTwo`.
    """
    _ensure_inferred_time_signatures(result)
    arbitrate_arcs_across_staves(result)
    divisions = _compute_divisions(result)

    parts_xml: list[str] = []
    part_list: list[str] = []
    part_idx = 0
    pg_number = 0  # part-group number — increment per piano pair
    global_measure_num = 0  # cumulative measure counter across systems on every page

    # Stitched path: one part per SLOT, carrying that slot's staff from every
    # system of the piece. See `_stitch_slots` for when this is not safe.
    slots = _stitch_slots(result)
    if slots is not None:
        systems = [
            system
            for page in result.get("pages", [])
            for system in page.get("systems", [])
            if system.get("staves")
        ]
        is_piano = len(slots) == 2
        if is_piano:
            part_list.append(
                "  <part-group type=\"start\" number=\"1\">\n"
                "    <group-symbol>brace</group-symbol>\n"
                "    <group-barline>yes</group-barline>\n"
                "  </part-group>"
            )
        # Where each system's measures begin, so numbering runs on through the
        # piece rather than restarting per system.
        starts: list[int] = []
        running = 1
        for system in systems:
            starts.append(running)
            running += max(len(s.get("measures", [])) for s in system["staves"])
        for ordinal, slot in enumerate(slots):
            part_idx += 1
            part_id = f"P{part_idx}"
            # Prefer the instrument the contextual pass named, as the
            # per-system path below does — a slot is the same staff on every
            # system, so any system's reading names the whole part.
            instrument = next(
                (s.get("instrument") for s in slot if s.get("instrument")), None
            )
            part_name = instrument if instrument else f"Staff {ordinal}"
            part_list.append(
                f"  <score-part id=\"{part_id}\">\n"
                f"    <part-name>{_xml_escape(part_name)}</part-name>\n"
                f"  </score-part>"
            )
            # The slot is ONE part, so its slurs are paired across every system
            # it spans before any of its measures are written — that is what
            # lets a slur opened in the last bar of one system close in the
            # first bar of the next.
            annotate_slurs_in_slot(slot)
            annotate_wedges_in_slot(slot)
            state: dict[str, Any] = {}
            measures_xml: list[str] = []
            for staff, start in zip(slot, starts):
                measures_xml += _staff_measures_xml(
                    staff, divisions, start, state, pair_spanners=False)
            parts_xml.append(
                f"  <part id=\"{part_id}\">\n"
                + "\n".join(measures_xml)
                + "\n  </part>"
            )
        if is_piano:
            part_list.append("  <part-group type=\"stop\" number=\"1\"/>")
        return _score_partwise(result, part_list, parts_xml)

    for page in result.get("pages", []):
        for sys_idx, sys_ in enumerate(page.get("systems", [])):
            staves = sys_.get("staves", [])
            if not staves:
                continue
            is_piano = len(staves) == 2
            # "Fragmented row" pattern: OMR layout detector sometimes splits
            # a single melodic line on a page into many "staves" with one
            # measure each (typically vertically-stacked single-line music).
            # When that happens, MusicXML semantics would emit those as
            # parallel parts — which is wrong. Merge them into a single
            # part with sequential measure numbers.
            is_fragmented_row = not is_piano and _is_fragmented_row(staves)

            if is_fragmented_row:
                part_idx += 1
                part_id = f"P{part_idx}"
                part_name = f"Page{page['page_index']}-System{sys_idx}-merged"
                part_list.append(
                    f"  <score-part id=\"{part_id}\">\n"
                    f"    <part-name>{_xml_escape(part_name)}</part-name>\n"
                    f"  </score-part>"
                )

                measures_xml: list[str] = []
                last_clef = None
                last_key_sig = None
                last_time_sig = None
                first_in_part = True
                # Each "staff" here holds one measure of one melodic line, so
                # a slur — or a hairpin — has no barline to cross within it.
                for staff in staves:
                    annotate_slurs_in_staff(staff)
                    annotate_wedges_in_staff(staff)
                    # By construction, each staff has exactly 1 measure.
                    measure = staff["measures"][0]
                    m_clef = measure.get("clef") or staff.get("clef")
                    m_key = measure.get("key_signature") or staff.get("key_signature")
                    m_time = measure.get("time_signature") or staff.get("time_signature")

                    attrs_clef = m_clef if (m_clef != last_clef) else None
                    attrs_key = m_key if (m_key != last_key_sig) else None
                    attrs_time = m_time if (m_time != last_time_sig) else None
                    include_divisions = first_in_part
                    has_attrs = (
                        include_divisions or attrs_clef or attrs_key or attrs_time
                    )

                    inner: list[str] = []
                    if has_attrs:
                        inner.append(_mxl_attributes_block(
                            attrs_clef, attrs_key, attrs_time, divisions,
                            "      ", include_divisions,
                        ))
                    last_clef = m_clef
                    last_key_sig = m_key
                    last_time_sig = m_time
                    first_in_part = False

                    events = group_chords_in_measure(measure.get("detections", []))
                    voices = split_events_into_voices(events)
                    # Per voice: interleaved voices would break each other's runs.
                    for _voice_events in voices:
                        annotate_beams(_voice_events, measure.get("detections", []))
                        annotate_fermatas(_voice_events, measure.get("detections", []))
                    # Marks belong to the staff, not to a voice, so they go on
                    # voice 1 rather than being emitted once per voice. The
                    # dynamics the detector drew and the words `direction_text`
                    # read are both `<direction>` elements placed by x, and
                    # belong to the staff for the same reason.
                    _dyn = measure_directions(measure)

                    if not events:
                        inner.extend(_mxl_empty_measure(
                            m_time, divisions, _dyn, "      ",
                            fermata=measure_has_fermata(
                                measure.get("detections", [])),
                            wedges=eventless_wedges(
                                measure.get("detections", []))))
                    elif len(voices) == 1:
                        v1_lines, _ = _mxl_voice_events(
                            voices[0], voice=1, divisions=divisions, indent="      ",
                            directions=_dyn,
                        )
                        inner.extend(v1_lines)
                    else:
                        v1_lines, v1_dur = _mxl_voice_events(
                            voices[0], voice=1, divisions=divisions, indent="      ",
                            directions=_dyn,
                        )
                        inner.extend(v1_lines)
                        if v1_dur > 0:
                            inner.append(
                                "      <backup>\n"
                                f"        <duration>{v1_dur}</duration>\n"
                                "      </backup>"
                            )
                        v2_lines, _ = _mxl_voice_events(
                            voices[1], voice=2, divisions=divisions, indent="      ",
                        )
                        inner.extend(v2_lines)

                    global_measure_num += 1
                    measures_xml.append(
                        f"    <measure number=\"{global_measure_num}\">\n"
                        + "\n".join(inner)
                        + "\n    </measure>"
                    )

                parts_xml.append(
                    f"  <part id=\"{part_id}\">\n"
                    + "\n".join(measures_xml)
                    + "\n  </part>"
                )
                continue  # done with this system

            # Normal path: each staff becomes a part. Measures share numbers
            # across staves within the system (parallel parts). The page-
            # global counter advances by the system's max-measures so the
            # next system continues numbering correctly.
            sys_start_num = global_measure_num + 1
            sys_max_measures = max(len(s.get("measures", [])) for s in staves)

            if is_piano:
                pg_number += 1
                part_list.append(
                    f"  <part-group type=\"start\" number=\"{pg_number}\">\n"
                    f"    <group-symbol>brace</group-symbol>\n"
                    f"    <group-barline>yes</group-barline>\n"
                    f"  </part-group>"
                )
            for staff_idx_in_sys, staff in enumerate(staves):
                part_idx += 1
                part_id = f"P{part_idx}"
                # Prefer the instrument the contextual pass named. Until it was
                # wired into `transcribe` nothing here HAD a name to use, so
                # every part came out as its own grid reference — the complaint
                # CLAUDE.md records under "no persistent part identity". A staff
                # the pass could not name still falls back to the coordinates,
                # so a run with `--no-contextual` is byte-identical to before.
                instrument = staff.get("instrument")
                part_name = instrument if instrument else (
                    f"Staff p{page['page_index']}-s{sys_idx}-"
                    f"{staff_idx_in_sys}"
                )
                part_list.append(
                    f"  <score-part id=\"{part_id}\">\n"
                    f"    <part-name>{_xml_escape(part_name)}</part-name>\n"
                    f"  </score-part>"
                )

                measures_xml = _staff_measures_xml(
                    staff, divisions, sys_start_num, {},
                )

                parts_xml.append(
                    f"  <part id=\"{part_id}\">\n"
                    + "\n".join(measures_xml)
                    + "\n  </part>"
                )
            # After all staves in this piano system are listed, close
            # the part-group.
            if is_piano:
                part_list.append(
                    f"  <part-group type=\"stop\" number=\"{pg_number}\"/>"
                )
            global_measure_num += sys_max_measures

    return _score_partwise(result, part_list, parts_xml)


def _score_partwise(
    result: dict[str, Any], part_list: list[str], parts_xml: list[str]
) -> str:
    src = result.get("source_pdf") or "OMR transcription"
    work_title = Path(src).name if src else "OMR transcription"

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<!DOCTYPE score-partwise PUBLIC '
        '"-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
        '"http://www.musicxml.org/dtds/partwise.dtd">\n'
        '<score-partwise version="3.1">\n'
        f'  <work>\n    <work-title>{_xml_escape(work_title)}</work-title>\n  </work>\n'
        '  <part-list>\n'
        + "\n".join(part_list)
        + '\n  </part-list>\n'
        + "\n".join(parts_xml)
        + '\n</score-partwise>\n'
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=("Export a transcribe.py JSON result to LilyPond (.ly) "
                     "or MusicXML (.musicxml)."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "    python3 -m tools.omr.transcribe score.pdf --pages 0 --out r.json\n"
            "    python3 -m tools.omr.export r.json --format lilypond --out r.ly\n"
            "    python3 -m tools.omr.export r.json --format musicxml --out r.musicxml\n"
        ),
    )
    ap.add_argument("json", type=Path,
                    help="Input: transcribe.py JSON file (or '-' for stdin)")
    ap.add_argument("--format", choices=("lilypond", "musicxml"), required=True,
                    help="Output format")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output file (default: stdout)")
    args = ap.parse_args(argv)

    if str(args.json) == "-":
        result = json.loads(sys.stdin.read())
    else:
        if not args.json.exists():
            print(f"ERROR: JSON not found: {args.json}", file=sys.stderr)
            return 2
        result = json.loads(args.json.read_text())

    if args.format == "lilypond":
        out_str = to_lilypond(result)
    else:
        out_str = to_musicxml(result)

    if args.out is None:
        sys.stdout.write(out_str)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(out_str)
        n_lines = out_str.count("\n")
        print(f"wrote {args.out}  ({len(out_str)} bytes, {n_lines} lines)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
