"""Read a reference MusicXML / MXL into per-part, per-measure note lists.

Standard library only. Every other truth loader in this repository goes
through music21 (`end_to_end_eval.part_sequences`, `scan_eval._pitches`,
`build_dossiers.dossier_from_score`), which lives in a separate venv on the
host and is absent from a fresh worktree or a remote session. This reader
needs nothing, so the pre-fill (`mxl_verdicts.py`) can run anywhere the
transcription JSON can be opened.

What it reads, and what it deliberately does not:

- `<part>` order and `<part-name>` from the part list.
- Every `<measure>`'s `number` attribute (kept as printed: a pickup is
  usually `0`, an `implicit="yes"` measure is flagged) and the notes inside
  it in ONSET order, with the onset tracked through `<chord/>`, `<backup>`
  and `<forward>` the way a MusicXML reader must.
- Per note: written pitch as the pipeline spells it (`F#4`, `Bb3`), rest /
  chord / grace / tie / tuplet flags, `<type>`, dots, voice, duration in
  quarter lengths.
- It does NOT apply `<transpose>`: MusicXML `<pitch>` is WRITTEN pitch, and
  written pitch is what the page shows and what the pipeline reads.

Timewise MusicXML is not handled; every reference in the score library is
partwise.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

# `<type>` values in order, and their length in quarter notes.
TYPE_QUARTER_LENGTH: dict[str, float] = {
    "maxima": 32.0,
    "long": 16.0,
    "breve": 8.0,
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "16th": 0.25,
    "32nd": 0.125,
    "64th": 0.0625,
    "128th": 0.03125,
    "256th": 0.015625,
}

_ALTER_TEXT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}


@dataclass
class TruthNote:
    onset_ql: float
    duration_ql: float
    pitch: str | None            # "F#4" — None for a rest or an unpitched note
    step: str | None
    alter: int
    octave: int | None
    type: str | None             # "half", "eighth", … or None when absent
    dots: int
    rest: bool
    chord: bool                  # carried a <chord/> — same onset as the previous note
    grace: bool
    voice: str
    tuplet_actual: int | None    # <time-modification> actual-notes
    tuplet_normal: int | None
    tie_start: bool
    tie_stop: bool
    unpitched: bool
    measure_rest: bool           # <rest measure="yes"/>

    @property
    def step_key(self) -> str:
        """`E4` for E4, Eb4 and E#4 alike — the notehead sits in the same place."""
        if self.rest:
            return "R"
        if self.step is None or self.octave is None:
            return "X"
        return f"{self.step}{self.octave}"

    @property
    def exact_key(self) -> str:
        if self.rest:
            return "R"
        return self.pitch or "X"


@dataclass
class TruthMeasure:
    number_raw: str
    number: int | None
    implicit: bool
    notes: list[TruthNote] = field(default_factory=list)
    divisions: int = 1

    @property
    def sounding(self) -> list[TruthNote]:
        return [n for n in self.notes if not n.rest and not n.grace]


@dataclass
class TruthPart:
    index: int
    part_id: str
    name: str
    measures: list[TruthMeasure]

    def by_number(self) -> dict[int, TruthMeasure]:
        out: dict[int, TruthMeasure] = {}
        for m in self.measures:
            if m.number is not None and m.number not in out:
                out[m.number] = m
        return out


@dataclass
class TruthScore:
    path: str
    parts: list[TruthPart]

    def part(self, index: int) -> TruthPart:
        return self.parts[index]


# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------


def _read_xml_bytes(path: Path) -> bytes:
    if path.suffix.lower() == ".mxl" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            root = None
            if "META-INF/container.xml" in names:
                container = ET.fromstring(zf.read("META-INF/container.xml"))
                for rf in container.iter():
                    if rf.tag.endswith("rootfile") and rf.get("full-path"):
                        root = rf.get("full-path")
                        break
            if root is None or root not in names:
                candidates = [n for n in names
                              if n.lower().endswith((".xml", ".musicxml"))
                              and not n.startswith("META-INF/")]
                if not candidates:
                    raise ValueError(f"{path}: no MusicXML inside the archive")
                root = candidates[0]
            return zf.read(root)
    return path.read_bytes()


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(el: ET.Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _int(el: ET.Element | None, default: int = 0) -> int:
    try:
        return int(_text(el, str(default)))
    except ValueError:
        return default


def _parse_number(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        # "X1", "12a" — keep the digits if there are any leading ones.
        digits = ""
        for ch in raw:
            if ch.isdigit():
                digits += ch
            elif digits:
                break
        return int(digits) if digits else None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _part_names(root: ET.Element) -> dict[str, str]:
    names: dict[str, str] = {}
    part_list = root.find("part-list")
    if part_list is None:
        return names
    for sp in part_list:
        if _strip_ns(sp.tag) != "score-part":
            continue
        pid = sp.get("id", "")
        names[pid] = _text(sp.find("part-name"))
    return names


def _parse_note(el: ET.Element, onset_div: float, divisions: int) -> TruthNote:
    rest_el = el.find("rest")
    pitch_el = el.find("pitch")
    unp_el = el.find("unpitched")
    grace = el.find("grace") is not None
    chord = el.find("chord") is not None
    dur_div = _int(el.find("duration"), 0)
    duration_ql = dur_div / divisions if divisions else 0.0
    type_el = el.find("type")
    ntype = _text(type_el) or None
    dots = len(el.findall("dot"))
    voice = _text(el.find("voice"), "1")
    tm = el.find("time-modification")
    ta = _int(tm.find("actual-notes")) if tm is not None else None
    tn = _int(tm.find("normal-notes")) if tm is not None else None
    tie_start = any(t.get("type") == "start" for t in el.findall("tie"))
    tie_stop = any(t.get("type") == "stop" for t in el.findall("tie"))

    step = octave = None
    alter = 0
    pitch = None
    src = pitch_el if pitch_el is not None else unp_el
    if src is not None:
        step = _text(src.find("step") if pitch_el is not None else src.find("display-step")) or None
        octave_el = src.find("octave") if pitch_el is not None else src.find("display-octave")
        octave = _int(octave_el, 0) if octave_el is not None else None
        alter_el = src.find("alter")
        if alter_el is not None:
            try:
                alter = int(round(float(_text(alter_el, "0"))))
            except ValueError:
                alter = 0
        if step is not None and octave is not None and pitch_el is not None:
            pitch = f"{step}{_ALTER_TEXT.get(alter, '')}{octave}"

    return TruthNote(
        onset_ql=onset_div / divisions if divisions else 0.0,
        duration_ql=duration_ql,
        pitch=pitch,
        step=step,
        alter=alter,
        octave=octave,
        type=ntype,
        dots=dots,
        rest=rest_el is not None,
        chord=chord,
        grace=grace,
        voice=voice,
        tuplet_actual=ta,
        tuplet_normal=tn,
        tie_start=tie_start,
        tie_stop=tie_stop,
        unpitched=unp_el is not None,
        measure_rest=(rest_el is not None and rest_el.get("measure") == "yes"),
    )


def _parse_measure(el: ET.Element, divisions: int) -> tuple[TruthMeasure, int]:
    """Parse one <measure>. Returns the measure and the divisions in force
    at its end (a <divisions> change persists into later measures)."""
    raw = el.get("number", "")
    measure = TruthMeasure(
        number_raw=raw,
        number=_parse_number(raw),
        implicit=(el.get("implicit") == "yes"),
        divisions=divisions,
    )
    cursor = 0.0        # in divisions
    last_onset = 0.0    # onset of the previous non-chord note, for <chord/>
    for child in el:
        tag = _strip_ns(child.tag)
        if tag == "attributes":
            d = child.find("divisions")
            if d is not None:
                divisions = max(1, _int(d, divisions))
                measure.divisions = divisions
        elif tag == "backup":
            cursor -= _int(child.find("duration"), 0)
        elif tag == "forward":
            cursor += _int(child.find("duration"), 0)
        elif tag == "note":
            is_chord = child.find("chord") is not None
            onset = last_onset if is_chord else cursor
            note = _parse_note(child, onset, divisions)
            measure.notes.append(note)
            if not is_chord:
                last_onset = cursor
                if not note.grace:
                    cursor += _int(child.find("duration"), 0)
    measure.notes.sort(key=lambda n: (n.onset_ql, n.rest, n.octave or 0, n.step or ""))
    return measure, divisions


def load_truth(path: str | Path) -> TruthScore:
    """Parse a .musicxml / .xml / .mxl file into a `TruthScore`."""
    path = Path(path)
    root = ET.fromstring(_read_xml_bytes(path))
    if _strip_ns(root.tag) == "score-timewise":
        raise ValueError(f"{path}: timewise MusicXML is not supported")
    if _strip_ns(root.tag) != "score-partwise":
        raise ValueError(f"{path}: not a MusicXML score (root <{root.tag}>)")
    names = _part_names(root)
    parts: list[TruthPart] = []
    for pi, part_el in enumerate(e for e in root if _strip_ns(e.tag) == "part"):
        pid = part_el.get("id", f"P{pi + 1}")
        divisions = 1
        measures: list[TruthMeasure] = []
        for m_el in part_el:
            if _strip_ns(m_el.tag) != "measure":
                continue
            m, divisions = _parse_measure(m_el, divisions)
            measures.append(m)
        parts.append(TruthPart(index=pi, part_id=pid, name=names.get(pid, pid),
                               measures=measures))
    return TruthScore(path=str(path), parts=parts)


def iter_measure_numbers(score: TruthScore) -> Iterator[int]:
    seen: set[int] = set()
    for p in score.parts:
        for m in p.measures:
            if m.number is not None and m.number not in seen:
                seen.add(m.number)
                yield m.number
