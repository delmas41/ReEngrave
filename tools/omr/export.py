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
import sys
from pathlib import Path
from typing import Any

from .voicing import group_chords_in_measure, split_events_into_voices


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

    `dots` here is the augmentation dot count we stored on the event.
    If the duration_type happens to also start with "dotted_" we add
    those too — but in practice transcribe.py only sets ONE source.
    """
    base, prefix_dots = _strip_dotted(duration_type)
    total_dots = dots + prefix_dots
    lily_base, xml_base = _DURATION_TABLE.get(base, ("4", "quarter"))
    return lily_base, xml_base, total_dots


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


def _lily_event(event: dict[str, Any]) -> str:
    """Render one chord/rest event in LilyPond syntax."""
    lily_suffix, _, dots = _duration_to_lily_xml(
        event["duration_type"], event.get("dots", 0)
    )
    dot_str = "." * dots

    if event["kind"] == "rest":
        return f"r{lily_suffix}{dot_str}"

    # Chord
    pitches = []
    for nh in event["noteheads"]:
        ly = _pitch_to_lily(nh["pitch"])
        if ly is not None:
            pitches.append(ly)
    if not pitches:
        return f"r{lily_suffix}{dot_str}"  # fallback if all pitches unparsable
    if len(pitches) == 1:
        return f"{pitches[0]}{lily_suffix}{dot_str}"
    return f"<{' '.join(pitches)}>{lily_suffix}{dot_str}"


def _lily_staff_block(staff: dict[str, Any], indent: str = "    ") -> str:
    """Render one OMR staff as a LilyPond `\\new Staff { ... }` block.

    If the staff has events with mixed stem directions (both up and
    down on the same measure), emits a `<<` simultaneous-music block
    with `\\new Voice { \\voiceOne ... }` + `\\voiceTwo`.
    """
    clef = staff.get("clef") or "treble"
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

    # Decide once for the whole staff whether to render as one-voice
    # or two-voice. Two-voice only if any measure has BOTH stem-up and
    # stem-down chords — otherwise it's overkill.
    needs_two_voices = False
    per_measure_events: list[list[dict[str, Any]]] = []
    for measure in staff.get("measures", []):
        events = group_chords_in_measure(measure.get("detections", []))
        per_measure_events.append(events)
        voices = split_events_into_voices(events)
        if len(voices) > 1:
            needs_two_voices = True

    if needs_two_voices:
        # Two-voice block.
        v1_lines: list[str] = [f"{indent}    \\voiceOne"]
        v2_lines: list[str] = [f"{indent}    \\voiceTwo"]
        for events in per_measure_events:
            voices = split_events_into_voices(events)
            v1_events = voices[0] if voices else []
            v2_events = voices[1] if len(voices) >= 2 else voices[0] if voices else []
            v1_lines.append(
                f"{indent}    " + " ".join(_lily_event(ev) for ev in v1_events)
                + " |" if v1_events else f"{indent}    r1 |"
            )
            v2_lines.append(
                f"{indent}    " + " ".join(_lily_event(ev) for ev in v2_events)
                + " |" if v2_events else f"{indent}    r1 |"
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
        for events in per_measure_events:
            if not events:
                lines.append(f"{indent}  r1 |")
                continue
            rendered = " ".join(_lily_event(ev) for ev in events)
            lines.append(f"{indent}  {rendered} |")

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


_MXL_CLEF_SIGN = {
    "treble": ("G", 2),
    "bass":   ("F", 4),
    "alto":   ("C", 3),
    "tenor":  ("C", 4),
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


def _compute_divisions(result: dict[str, Any]) -> int:
    """Choose a `divisions` value (durations per quarter note) that makes
    every event's duration a whole-number multiple of 1/divisions.

    We assume the shortest duration we see is 1/64th (1/16 quarter), so
    divisions=16 covers most music. If we detect 128th notes (1/32 quarter)
    we go to 32. Always at least 4 (sixteenth-note resolution).
    """
    divisions = 4
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for measure in staff.get("measures", []):
                    for det in measure.get("detections", []):
                        beats = det.get("duration_beats")
                        if beats is None:
                            continue
                        # Find the smallest D such that beats * D is an int
                        for D in (4, 8, 16, 32, 64, 128):
                            if abs(beats * D - round(beats * D)) < 1e-6:
                                divisions = max(divisions, D)
                                break
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
        lines.append(f"{indent}  <time>")
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
              is_rest: bool, indent: str, voice: int = 1) -> str:
    """Render one <note> for MusicXML — used for both chord members and rests."""
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
    lines.append(f"{indent}  <voice>{voice}</voice>")
    lines.append(f"{indent}  <type>{xml_type}</type>")
    for _ in range(dots):
        lines.append(f"{indent}  <dot/>")
    lines.append(f"{indent}</note>")
    return "\n".join(lines)


def _mxl_voice_events(
    events: list[dict[str, Any]],
    voice: int,
    divisions: int,
    indent: str,
) -> tuple[list[str], int]:
    """Render an ordered list of events as MusicXML <note> elements with
    the given voice number. Returns (lines, total_duration_units) where
    total_duration_units is the sum of CHORD-LEADING + REST durations
    (chord members past the first don't advance the cursor).
    """
    lines: list[str] = []
    total_dur = 0
    for event in events:
        _, xml_type, dots = _duration_to_lily_xml(
            event["duration_type"], event.get("dots", 0)
        )
        beats = event["duration_beats"]
        dur_units = max(1, int(round(beats * divisions)))
        if event["kind"] == "rest":
            lines.append(_mxl_note(
                None, "", xml_type, dots, beats, divisions,
                is_chord=False, is_rest=True, indent=indent, voice=voice,
            ))
            total_dur += dur_units
        else:
            for ni, nh in enumerate(event["noteheads"]):
                lines.append(_mxl_note(
                    nh.get("pitch"), "", xml_type, dots, beats, divisions,
                    is_chord=(ni > 0), is_rest=False,
                    indent=indent, voice=voice,
                ))
            # Only the chord's first note advances the time cursor; chord
            # members past the first share its onset.
            total_dur += dur_units
    return lines, total_dur


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
    divisions = _compute_divisions(result)

    parts_xml: list[str] = []
    part_list: list[str] = []
    part_idx = 0
    pg_number = 0  # part-group number — increment per piano pair

    for page in result.get("pages", []):
        for sys_idx, sys_ in enumerate(page.get("systems", [])):
            staves = sys_.get("staves", [])
            is_piano = len(staves) == 2
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
                part_name = (
                    f"Staff p{page['page_index']}-s{sys_idx}-"
                    f"{staff_idx_in_sys}"
                )
                part_list.append(
                    f"  <score-part id=\"{part_id}\">\n"
                    f"    <part-name>{_xml_escape(part_name)}</part-name>\n"
                    f"  </score-part>"
                )

                clef = staff.get("clef")
                key_sig = staff.get("key_signature")
                time_sig = staff.get("time_signature")

                measures_xml: list[str] = []
                last_clef = None
                last_key_sig = None
                last_time_sig = None
                for m_idx, measure in enumerate(staff.get("measures", [])):
                    m_clef = measure.get("clef") or clef
                    m_key = measure.get("key_signature") or key_sig
                    m_time = measure.get("time_signature") or time_sig

                    # Decide what attributes to emit. First measure always
                    # gets the full block. Later measures only when the
                    # value changes.
                    attrs_clef = m_clef if (m_clef != last_clef) else None
                    attrs_key = m_key if (m_key != last_key_sig) else None
                    attrs_time = m_time if (m_time != last_time_sig) else None
                    include_divisions = (m_idx == 0)
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

                    events = group_chords_in_measure(
                        measure.get("detections", [])
                    )
                    voices = split_events_into_voices(events)

                    if not events:
                        # Empty measure — emit a whole rest as a placeholder.
                        inner.append(_mxl_note(
                            None, "", "whole", 0, 4.0, divisions,
                            is_chord=False, is_rest=True,
                            indent="      ", voice=1,
                        ))
                    elif len(voices) == 1:
                        v1_lines, _ = _mxl_voice_events(
                            voices[0], voice=1, divisions=divisions,
                            indent="      ",
                        )
                        inner.extend(v1_lines)
                    else:
                        v1_lines, v1_dur = _mxl_voice_events(
                            voices[0], voice=1, divisions=divisions,
                            indent="      ",
                        )
                        inner.extend(v1_lines)
                        if v1_dur > 0:
                            inner.append(
                                "      <backup>\n"
                                f"        <duration>{v1_dur}</duration>\n"
                                "      </backup>"
                            )
                        v2_lines, _ = _mxl_voice_events(
                            voices[1], voice=2, divisions=divisions,
                            indent="      ",
                        )
                        inner.extend(v2_lines)

                    measures_xml.append(
                        f"    <measure number=\"{m_idx + 1}\">\n"
                        + "\n".join(inner)
                        + "\n    </measure>"
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
