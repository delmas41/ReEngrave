"""
MusicXML builder — converts structured JSON from Claude Vision OMR into valid MusicXML.

Accepts a ScoreHeader (instruments, initial attributes) and a list of PageAnalysis
objects (measures with notes per staff per voice), and assembles a complete
<score-partwise> MusicXML document.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

# ---------------------------------------------------------------------------
# Data classes — mirror the JSON schema Claude Vision returns
# ---------------------------------------------------------------------------

DIVISIONS = 1024  # divisions per quarter note — high for fine granularity


@dataclass
class PitchData:
    step: str          # A-G
    octave: int        # 0-9
    alter: int = 0     # -2 to +2 (flats/sharps)


@dataclass
class NoteElement:
    """A single note, rest, or chord member."""
    type: str                       # "note", "rest", "chord"
    duration: str                   # "whole", "half", "quarter", "eighth", "16th", "32nd", "64th"
    dots: int = 0
    pitch: Optional[PitchData] = None       # None for rests
    pitches: list[PitchData] = field(default_factory=list)  # for chords
    tie: Optional[str] = None       # "start", "stop", "continue"
    articulations: list[str] = field(default_factory=list)  # "staccato", "accent", etc.
    fermata: bool = False
    beam: Optional[str] = None      # "begin", "continue", "end"
    grace: bool = False


@dataclass
class VoiceData:
    voice: int
    elements: list[NoteElement]


@dataclass
class DirectionData:
    type: str           # "dynamic", "tempo", "wedge"
    value: str          # "mf", "Allegro", "crescendo"
    bpm: Optional[int] = None


@dataclass
class StaffMeasure:
    staff_id: int
    voices: list[VoiceData]
    directions: list[DirectionData] = field(default_factory=list)
    clef_change: Optional[dict] = None      # {"sign": "G", "line": 2}
    key_change: Optional[dict] = None       # {"fifths": -1, "mode": "major"}
    time_change: Optional[dict] = None      # {"beats": 3, "beat_type": 4}


@dataclass
class MeasureData:
    number: int
    staves: list[StaffMeasure]
    barline: Optional[str] = None   # "light-heavy", "repeat-forward", etc.


@dataclass
class StaffHeader:
    staff_id: int
    instrument_name: str
    clef_sign: str = "G"
    clef_line: int = 2
    key_fifths: int = 0
    key_mode: str = "major"
    time_beats: int = 4
    time_beat_type: int = 4


@dataclass
class ScoreHeader:
    title: str
    composer: str
    staves: list[StaffHeader]


@dataclass
class PageAnalysis:
    page_number: int
    measures: list[MeasureData]


# ---------------------------------------------------------------------------
# Duration lookup
# ---------------------------------------------------------------------------

DURATION_MAP: dict[str, int] = {
    "whole": DIVISIONS * 4,
    "half": DIVISIONS * 2,
    "quarter": DIVISIONS,
    "eighth": DIVISIONS // 2,
    "16th": DIVISIONS // 4,
    "32nd": DIVISIONS // 8,
    "64th": DIVISIONS // 16,
}

TYPE_NAMES = {v: k for k, v in DURATION_MAP.items()}


def _calc_duration(dur_name: str, dots: int = 0) -> int:
    base = DURATION_MAP.get(dur_name, DIVISIONS)
    total = base
    add = base
    for _ in range(dots):
        add //= 2
        total += add
    return total


# ---------------------------------------------------------------------------
# Accidental name from alter value
# ---------------------------------------------------------------------------

_ALTER_TO_ACCIDENTAL = {
    -2: "flat-flat",
    -1: "flat",
    0: None,
    1: "sharp",
    2: "double-sharp",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_musicxml(header: ScoreHeader, pages: list[PageAnalysis]) -> str:
    """Build a complete MusicXML document from structured data.

    Returns the XML as a UTF-8 string.
    """
    root = Element("score-partwise", version="4.0")

    # Work
    work_el = SubElement(root, "work")
    SubElement(work_el, "work-title").text = header.title

    # Identification
    ident = SubElement(root, "identification")
    creator = SubElement(ident, "creator", type="composer")
    creator.text = header.composer
    encoding = SubElement(ident, "encoding")
    SubElement(encoding, "software").text = "ReEngrave Claude Vision OMR"

    # Collect all measures across pages
    all_measures: list[MeasureData] = []
    for page in sorted(pages, key=lambda p: p.page_number):
        all_measures.extend(page.measures)

    # Part list — try header staves first, fall back to auto-discovery from pages
    part_list = SubElement(root, "part-list")

    if header.staves:
        parts = _group_staves_into_parts(header.staves)
    else:
        parts = []

    # Auto-discover staves from page data if header is empty or incomplete
    if not parts and all_measures:
        discovered_ids: dict[int, str] = {}
        for m in all_measures:
            for sm in m.staves:
                if sm.staff_id not in discovered_ids:
                    discovered_ids[sm.staff_id] = f"Staff {sm.staff_id}"
        auto_staves = [
            StaffHeader(
                staff_id=sid,
                instrument_name=name,
                clef_sign="G" if sid == 1 else "F",
                clef_line=2 if sid == 1 else 4,
            )
            for sid, name in sorted(discovered_ids.items())
        ]
        parts = _group_staves_into_parts(auto_staves)

    for part_id, part_staves in parts:
        sp = SubElement(part_list, "score-part", id=part_id)
        SubElement(sp, "part-name").text = part_staves[0].instrument_name

    # Build each part
    for part_id, part_staves in parts:
        part_el = SubElement(root, "part", id=part_id)
        staff_ids = [s.staff_id for s in part_staves]
        num_staves = len(staff_ids)

        for i, measure in enumerate(all_measures):
            measure_el = SubElement(part_el, "measure", number=str(measure.number))

            # First measure: emit full attributes
            if i == 0:
                _add_attributes(
                    measure_el, part_staves, num_staves, is_first=True
                )

            # Check for mid-score attribute changes
            for sm in measure.staves:
                if sm.staff_id in staff_ids:
                    if sm.key_change or sm.time_change or sm.clef_change:
                        _add_attribute_changes(measure_el, sm, staff_ids)
                        break

            # Add notes for each staff in this part
            first_staff = True
            for staff_idx, sid in enumerate(staff_ids):
                staff_measure = _find_staff_measure(measure, sid)
                staff_num = staff_idx + 1

                if staff_measure:
                    # Add directions (dynamics, tempo) for this staff
                    for direction in staff_measure.directions:
                        _add_direction(measure_el, direction, staff_num)

                    if not first_staff:
                        # backup to start of measure for second staff
                        backup = SubElement(measure_el, "backup")
                        SubElement(backup, "duration").text = str(
                            _measure_duration(all_measures, i, sid, staff_ids)
                        )

                    for voice_data in staff_measure.voices:
                        _add_voice_notes(
                            measure_el, voice_data, staff_num, num_staves
                        )

                first_staff = False

            # Barline
            if measure.barline:
                bl = SubElement(measure_el, "barline", location="right")
                SubElement(bl, "bar-style").text = measure.barline

    # Serialize
    indent(root, space="  ")
    tree = ElementTree(root)
    import io
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    xml_str = buf.getvalue().decode("utf-8")

    # Add DOCTYPE
    xml_str = xml_str.replace(
        "<?xml version='1.0' encoding='utf-8'?>",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"\n'
        '  "http://www.musicxml.org/dtds/partwise.dtd">',
    )
    return xml_str


def write_musicxml(xml_str: str, output_path: str) -> str:
    """Write MusicXML string to file. Returns the path."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
    return output_path


# ---------------------------------------------------------------------------
# Part grouping
# ---------------------------------------------------------------------------


def _group_staves_into_parts(
    staves: list[StaffHeader],
) -> list[tuple[str, list[StaffHeader]]]:
    """Group staves into parts. Piano gets 2 staves per part.

    Returns list of (part_id, [staves]).
    """
    if not staves:
        return []

    # Simple heuristic: consecutive staves with the same instrument name
    # are grouped into one part.
    parts: list[tuple[str, list[StaffHeader]]] = []
    current_group: list[StaffHeader] = [staves[0]]

    for s in staves[1:]:
        if s.instrument_name == current_group[0].instrument_name:
            current_group.append(s)
        else:
            parts.append((f"P{len(parts)+1}", current_group))
            current_group = [s]

    parts.append((f"P{len(parts)+1}", current_group))
    return parts


# ---------------------------------------------------------------------------
# Attribute builders
# ---------------------------------------------------------------------------


def _add_attributes(
    measure_el: Element,
    staves: list[StaffHeader],
    num_staves: int,
    is_first: bool,
) -> None:
    attrs = SubElement(measure_el, "attributes")
    SubElement(attrs, "divisions").text = str(DIVISIONS)

    key = SubElement(attrs, "key")
    SubElement(key, "fifths").text = str(staves[0].key_fifths)
    SubElement(key, "mode").text = staves[0].key_mode

    time = SubElement(attrs, "time")
    SubElement(time, "beats").text = str(staves[0].time_beats)
    SubElement(time, "beat-type").text = str(staves[0].time_beat_type)

    if num_staves > 1:
        SubElement(attrs, "staves").text = str(num_staves)

    for i, s in enumerate(staves):
        clef = SubElement(attrs, "clef")
        if num_staves > 1:
            clef.set("number", str(i + 1))
        SubElement(clef, "sign").text = s.clef_sign
        SubElement(clef, "line").text = str(s.clef_line)


def _add_attribute_changes(
    measure_el: Element, sm: StaffMeasure, staff_ids: list[int]
) -> None:
    attrs = SubElement(measure_el, "attributes")
    staff_num = staff_ids.index(sm.staff_id) + 1

    if sm.key_change:
        key = SubElement(attrs, "key")
        SubElement(key, "fifths").text = str(sm.key_change.get("fifths", 0))
        SubElement(key, "mode").text = sm.key_change.get("mode", "major")

    if sm.time_change:
        time = SubElement(attrs, "time")
        SubElement(time, "beats").text = str(sm.time_change.get("beats", 4))
        SubElement(time, "beat-type").text = str(
            sm.time_change.get("beat_type", 4)
        )

    if sm.clef_change:
        clef = SubElement(attrs, "clef", number=str(staff_num))
        SubElement(clef, "sign").text = sm.clef_change.get("sign", "G")
        SubElement(clef, "line").text = str(sm.clef_change.get("line", 2))


# ---------------------------------------------------------------------------
# Direction (dynamics, tempo)
# ---------------------------------------------------------------------------


def _add_direction(
    measure_el: Element, direction: DirectionData, staff_num: int
) -> None:
    dir_el = SubElement(measure_el, "direction", placement="below")
    dt = SubElement(dir_el, "direction-type")

    if direction.type == "dynamic":
        dynamics = SubElement(dt, "dynamics")
        SubElement(dynamics, direction.value)
    elif direction.type == "tempo":
        words = SubElement(dt, "words")
        words.text = direction.value
        if direction.bpm:
            sound = SubElement(dir_el, "sound", tempo=str(direction.bpm))

    SubElement(dir_el, "staff").text = str(staff_num)


# ---------------------------------------------------------------------------
# Note builders
# ---------------------------------------------------------------------------


def _add_voice_notes(
    measure_el: Element,
    voice_data: VoiceData,
    staff_num: int,
    num_staves: int,
) -> None:
    for i, elem in enumerate(voice_data.elements):
        if elem.type == "rest":
            _add_rest(measure_el, elem, voice_data.voice, staff_num, num_staves)
        elif elem.type == "note":
            _add_note(measure_el, elem, voice_data.voice, staff_num, num_staves)
        elif elem.type == "chord":
            _add_chord(measure_el, elem, voice_data.voice, staff_num, num_staves)


def _add_note(
    parent: Element,
    elem: NoteElement,
    voice: int,
    staff_num: int,
    num_staves: int,
    is_chord: bool = False,
) -> None:
    note_el = SubElement(parent, "note")

    if is_chord:
        SubElement(note_el, "chord")

    if elem.grace:
        SubElement(note_el, "grace")

    pitch = elem.pitch
    if pitch:
        p = SubElement(note_el, "pitch")
        SubElement(p, "step").text = pitch.step
        if pitch.alter != 0:
            SubElement(p, "alter").text = str(pitch.alter)
        SubElement(p, "octave").text = str(pitch.octave)

    dur = _calc_duration(elem.duration, elem.dots)
    if not elem.grace:
        SubElement(note_el, "duration").text = str(dur)

    SubElement(note_el, "voice").text = str(voice)
    SubElement(note_el, "type").text = elem.duration

    for _ in range(elem.dots):
        SubElement(note_el, "dot")

    if pitch and pitch.alter != 0:
        acc_name = _ALTER_TO_ACCIDENTAL.get(pitch.alter)
        if acc_name:
            SubElement(note_el, "accidental").text = acc_name

    if num_staves > 1:
        SubElement(note_el, "staff").text = str(staff_num)

    # Tie
    if elem.tie in ("start", "continue"):
        SubElement(note_el, "tie", type="start")
    if elem.tie in ("stop", "continue"):
        SubElement(note_el, "tie", type="stop")

    # Notations (articulations, fermata, tied)
    notations_needed = (
        elem.articulations or elem.fermata
        or elem.tie in ("start", "stop", "continue")
    )
    if notations_needed:
        notations = SubElement(note_el, "notations")
        if elem.tie in ("start", "continue"):
            SubElement(notations, "tied", type="start")
        if elem.tie in ("stop", "continue"):
            SubElement(notations, "tied", type="stop")
        if elem.fermata:
            SubElement(notations, "fermata", type="upright")
        if elem.articulations:
            artic = SubElement(notations, "articulations")
            for a in elem.articulations:
                SubElement(artic, a)


def _add_rest(
    parent: Element,
    elem: NoteElement,
    voice: int,
    staff_num: int,
    num_staves: int,
) -> None:
    note_el = SubElement(parent, "note")
    SubElement(note_el, "rest")
    dur = _calc_duration(elem.duration, elem.dots)
    SubElement(note_el, "duration").text = str(dur)
    SubElement(note_el, "voice").text = str(voice)
    SubElement(note_el, "type").text = elem.duration
    for _ in range(elem.dots):
        SubElement(note_el, "dot")
    if num_staves > 1:
        SubElement(note_el, "staff").text = str(staff_num)


def _add_chord(
    parent: Element,
    elem: NoteElement,
    voice: int,
    staff_num: int,
    num_staves: int,
) -> None:
    """Add a chord — first pitch as normal note, subsequent with <chord/>."""
    for i, pitch in enumerate(elem.pitches):
        single = NoteElement(
            type="note",
            duration=elem.duration,
            dots=elem.dots,
            pitch=pitch,
            tie=elem.tie,
            articulations=elem.articulations if i == 0 else [],
            fermata=elem.fermata if i == 0 else False,
        )
        _add_note(parent, single, voice, staff_num, num_staves, is_chord=(i > 0))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_staff_measure(
    measure: MeasureData, staff_id: int
) -> Optional[StaffMeasure]:
    for sm in measure.staves:
        if sm.staff_id == staff_id:
            return sm
    return None


def _measure_duration(
    all_measures: list[MeasureData],
    measure_idx: int,
    staff_id: int,
    staff_ids: list[int],
) -> int:
    """Calculate the total duration of the previous staff's notes in this measure,
    for the <backup> element."""
    measure = all_measures[measure_idx]
    # Use the first staff's total duration
    first_sid = staff_ids[0]
    sm = _find_staff_measure(measure, first_sid)
    if not sm or not sm.voices:
        # Default: 4 beats
        return DIVISIONS * 4

    # Sum duration of the first voice
    total = 0
    for voice in sm.voices[:1]:  # just voice 1
        for elem in voice.elements:
            total += _calc_duration(elem.duration, elem.dots)
    return total if total > 0 else DIVISIONS * 4


# ---------------------------------------------------------------------------
# JSON → dataclass conversion
# ---------------------------------------------------------------------------


# Maps a clef name (as emitted by Claude Vision, e.g. "treble") or a bare
# sign letter ("G"/"F"/"C") to the (sign, line) pair MusicXML expects.
# Unknown/missing values fall back to treble (G, line 2).
CLEF_NAME_TO_SIGN_LINE: dict[str, tuple[str, int]] = {
    "treble": ("G", 2),
    "bass": ("F", 4),
    "alto": ("C", 3),
    "tenor": ("C", 4),
    "g": ("G", 2),
    "f": ("F", 4),
    "c": ("C", 3),
}


def _resolve_clef(clef: Optional[str]) -> tuple[str, int]:
    """Resolve a clef name/sign string to a valid (sign, line) pair."""
    if not clef:
        return ("G", 2)
    return CLEF_NAME_TO_SIGN_LINE.get(clef.strip().lower(), ("G", 2))


def parse_header_json(data: dict) -> ScoreHeader:
    """Convert Claude's header JSON to a ScoreHeader dataclass."""
    staves = []
    for s in data.get("staves", []):
        ks = s.get("key_signature", {})
        ts = s.get("time_signature", {})
        clef_sign, clef_line = _resolve_clef(s.get("clef"))
        staves.append(StaffHeader(
            staff_id=s.get("staff_id", len(staves) + 1),
            instrument_name=s.get("instrument_name", "Piano"),
            clef_sign=clef_sign,
            clef_line=clef_line,
            key_fifths=ks.get("fifths", 0),
            key_mode=ks.get("mode", "major"),
            time_beats=ts.get("beats", 4),
            time_beat_type=ts.get("beat_type", 4),
        ))

    return ScoreHeader(
        title=data.get("title", "Untitled"),
        composer=data.get("composer", "Unknown"),
        staves=staves,
    )


def parse_page_json(data: dict) -> PageAnalysis:
    """Convert Claude's page JSON to a PageAnalysis dataclass."""
    measures = []
    for m in data.get("measures", []):
        staff_measures = []
        for sm in m.get("staves", []):
            voices = []
            for v in sm.get("voices", []):
                elements = []
                for e in v.get("elements", []):
                    pitch = None
                    if e.get("pitch"):
                        p = e["pitch"]
                        pitch = PitchData(
                            step=p.get("step", "C"),
                            octave=p.get("octave", 4),
                            alter=p.get("alter", 0),
                        )
                    pitches = []
                    for p in e.get("pitches", []):
                        pitches.append(PitchData(
                            step=p.get("step", "C"),
                            octave=p.get("octave", 4),
                            alter=p.get("alter", 0),
                        ))
                    elements.append(NoteElement(
                        type=e.get("type", "note"),
                        duration=e.get("duration", "quarter"),
                        dots=e.get("dots", 0),
                        pitch=pitch,
                        pitches=pitches,
                        tie=e.get("tie"),
                        articulations=e.get("articulations", []),
                        fermata=e.get("fermata", False),
                    ))
                voices.append(VoiceData(voice=v.get("voice", 1), elements=elements))
            staff_measures.append(StaffMeasure(
                staff_id=sm.get("staff_id", 1),
                voices=voices,
                directions=[
                    DirectionData(
                        type=d.get("type", "dynamic"),
                        value=d.get("value", ""),
                        bpm=d.get("bpm"),
                    )
                    for d in sm.get("directions", [])
                ],
                clef_change=sm.get("clef_change"),
                key_change=sm.get("key_change"),
                time_change=sm.get("time_change"),
            ))
        measures.append(MeasureData(
            number=m.get("number", len(measures) + 1),
            staves=staff_measures,
            barline=m.get("barline"),
        ))

    return PageAnalysis(
        page_number=data.get("page_number", 1),
        measures=measures,
    )
