"""Align one measure's truth notes to one measure's predicted events, and
say which DETECTION each match lands on.

`end_to_end_eval.align` scores a whole part with a longest-common-subsequence
over pitch names and returns counts. The pre-fill needs the pairs themselves:
which truth note matched which predicted notehead, so the verdict can be
written on the box that notehead came from. This module is that aligner,
kept free of music21 and of the transcription stack so it runs wherever the
JSON can be opened.

The unit is the TOKEN — one notehead or one rest — because that is the unit
the labeling UI boxes. A chord contributes one token per notehead, lowest
pitch first on both sides (`voicing.group_chords_in_measure` already orders
them that way; truth chords are sorted here to match).

Matching is on the STEP by default (`E4` for E4, Eb4 and E#4 alike): the
notehead box is the same whichever accidental precedes it, and a scan whose
key signature was misread spells every note on the staff wrong while placing
every notehead right. `match="exact"` demands the spelling too.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

from .musicxml_truth import TruthNote

# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------


@dataclass
class Token:
    key: str                 # what the aligner compares
    pitch: str | None        # spelled pitch, None for a rest
    is_rest: bool
    duration_ql: float | None
    type: str | None         # "half", "eighth", … (truth) or duration_type (pred)
    dots: int
    onset_ql: float | None   # truth only; None on the predicted side
    ref: Any                 # TruthNote, or the detection dict the token came from
    index: int               # position in its own sequence


def _pitch_key(pitch: str | None, match: str) -> str:
    if not pitch:
        return "X"
    if match == "exact":
        return pitch
    # step + octave: strip accidental characters between the letter and the number
    m = re.match(r"^([A-G])[#b]*(-?\d+)$", pitch)
    return f"{m.group(1)}{m.group(2)}" if m else pitch


def truth_tokens(notes: list[TruthNote], *, match: str = "step",
                 include_rests: bool = True, include_grace: bool = False) -> list[Token]:
    """Tokens for one truth measure, in onset order, chords lowest-first.

    Rests are kept only when the measure is not a mix of parts (the caller
    decides — see `merge_truth_parts`). Grace notes are skipped by default:
    the detector labels them `*Small` and the rhythm layer does not place
    them, so a match there would be luck rather than evidence.
    """
    out: list[Token] = []
    for n in notes:
        if n.grace and not include_grace:
            continue
        if n.rest and not include_rests:
            continue
        if n.rest:
            key = "R"
        elif n.unpitched:
            key = "X"
        else:
            key = _pitch_key(n.pitch, match)
        out.append(Token(key=key, pitch=n.pitch, is_rest=n.rest,
                         duration_ql=n.duration_ql, type=n.type, dots=n.dots,
                         onset_ql=n.onset_ql, ref=n, index=len(out)))
    return out


def merge_truth_parts(measures: list[list[TruthNote]]) -> list[TruthNote]:
    """Notes of several parts (or voices) printed on ONE staff, as one
    onset-ordered list with unisons collapsed.

    Two flutes on one staff print `a2` as ONE notehead, and a divisi viola
    prints a two-note chord where the reference holds two voices. Notes at
    the same onset with the same written pitch are one printed head. Rests
    are dropped when more than one part contributes, because "one part rests
    while the other plays" prints no rest the detector would box in the same
    place the reference puts it.
    """
    if len(measures) == 1:
        return sorted(measures[0], key=lambda n: (n.onset_ql, n.rest, n.octave or 0, n.step or ""))
    seen: set[tuple[float, str | None]] = set()
    merged: list[TruthNote] = []
    for notes in measures:
        for n in notes:
            if n.rest:
                continue
            k = (round(n.onset_ql, 6), n.pitch)
            if k in seen:
                continue
            seen.add(k)
            merged.append(n)
    merged.sort(key=lambda n: (n.onset_ql, n.octave or 0, n.step or ""))
    return merged


def event_tokens(events: list[dict[str, Any]], *, match: str = "step",
                 include_rests: bool = True) -> list[Token]:
    """Tokens for one predicted measure from `voicing.group_chords_in_measure`
    output. `ref` is the notehead or rest DETECTION DICT itself — the same
    object that sits in `measure["detections"]`, so identity maps it back."""
    out: list[Token] = []
    for ev in events:
        if ev.get("kind") == "rest":
            if not include_rests:
                continue
            r = ev.get("rest")
            out.append(Token(key="R", pitch=None, is_rest=True,
                             duration_ql=ev.get("duration_beats"),
                             type=ev.get("duration_type"), dots=ev.get("dots", 0),
                             onset_ql=None, ref=r, index=len(out)))
            continue
        for nh in ev.get("noteheads", []):
            out.append(Token(key=_pitch_key(nh.get("pitch"), match), pitch=nh.get("pitch"),
                             is_rest=False, duration_ql=ev.get("duration_beats"),
                             type=ev.get("duration_type"), dots=ev.get("dots", 0),
                             onset_ql=None, ref=nh, index=len(out)))
    return out


# --------------------------------------------------------------------------
# Alignment
# --------------------------------------------------------------------------


@dataclass
class Alignment:
    pairs: list[tuple[int, int]] = field(default_factory=list)
    truth_unmatched: list[int] = field(default_factory=list)
    pred_unmatched: list[int] = field(default_factory=list)
    n_truth: int = 0
    n_pred: int = 0

    @property
    def matched(self) -> int:
        return len(self.pairs)

    @property
    def strength(self) -> float | None:
        """Matched share of the LONGER side — None when both are empty."""
        denom = max(self.n_truth, self.n_pred)
        if denom == 0:
            return None
        return self.matched / denom


def align_tokens(truth: list[Token], pred: list[Token]) -> Alignment:
    """Longest common subsequence over token keys. Order-preserving, so a
    note can only match a note the reading placed in the same relative
    position — a transposed bar or a bar from the wrong measure matches
    little and the strength gate in the caller refuses it."""
    matcher = difflib.SequenceMatcher(a=[t.key for t in truth],
                                      b=[p.key for p in pred], autojunk=False)
    pairs: list[tuple[int, int]] = []
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            pairs.append((block.a + k, block.b + k))
    tm = {a for a, _ in pairs}
    pm = {b for _, b in pairs}
    return Alignment(
        pairs=pairs,
        truth_unmatched=[i for i in range(len(truth)) if i not in tm],
        pred_unmatched=[j for j in range(len(pred)) if j not in pm],
        n_truth=len(truth),
        n_pred=len(pred),
    )


# --------------------------------------------------------------------------
# What class the truth says a matched box should carry
# --------------------------------------------------------------------------

_HEAD_RE = re.compile(r"^notehead(Black|Half|Whole|DoubleWhole)(OnLine|InSpace)(Small)?$")

_KIND_BY_TYPE = {
    "maxima": "DoubleWhole", "long": "DoubleWhole", "breve": "DoubleWhole",
    "whole": "Whole", "half": "Half",
}

REST_CLASS_BY_TYPE = {
    "long": "restDoubleWhole", "breve": "restDoubleWhole",
    "whole": "restWhole", "half": "restHalf", "quarter": "restQuarter",
    "eighth": "rest8th", "16th": "rest16th", "32nd": "rest32nd",
    "64th": "rest64th", "128th": "rest128th",
}


def head_kind_for_type(ntype: str | None) -> str:
    """The notehead KIND a written `<type>` prints: whole and longer are
    hollow without a stem, half is hollow with one, everything shorter is a
    black head."""
    if ntype is None:
        return "Black"
    return _KIND_BY_TYPE.get(ntype, "Black")


def parse_head_class(cls: str | None) -> tuple[str, str, bool] | None:
    """`noteheadHalfOnLineSmall` → ("Half", "OnLine", True); None if not a head."""
    if not cls:
        return None
    m = _HEAD_RE.match(cls)
    if not m:
        return None
    return m.group(1), m.group(2), bool(m.group(3))


def expected_head_class(ntype: str | None, current_class: str | None) -> str | None:
    """The class the truth says a matched notehead box carries, keeping the
    position (`OnLine`/`InSpace`) and size the detector read — only the KIND
    is something the reference can vouch for. None when the current class is
    not a notehead class at all."""
    parsed = parse_head_class(current_class)
    if parsed is None:
        return None
    _, position, small = parsed
    return f"notehead{head_kind_for_type(ntype)}{position}{'Small' if small else ''}"


def expected_rest_class(note: TruthNote) -> str | None:
    if note.measure_rest:
        return "restWhole"
    if note.type is None:
        # No <type>: infer from the length, whole-measure rests are the
        # common case here.
        ql = note.duration_ql
        for t, length in (("whole", 4.0), ("half", 2.0), ("quarter", 1.0),
                          ("eighth", 0.5), ("16th", 0.25), ("32nd", 0.125)):
            if abs(ql - length) < 1e-6:
                return REST_CLASS_BY_TYPE[t]
        return None
    return REST_CLASS_BY_TYPE.get(note.type)


# --------------------------------------------------------------------------
# Where on the staff a pitch sits — for the ghost markers
# --------------------------------------------------------------------------

_PITCH_CYCLE = "CDEFGAB"
_FAMILY_REFERENCE_PITCH = {"G": ("G", 4), "C": ("C", 4), "F": ("F", 3)}
_OCTAVE_SUFFIX_SHIFT = {"_8va": 1, "_8vb": -1, "_15ma": 2, "_15mb": -2}


def _diatonic_index(step: str, octave: int) -> int:
    return octave * 7 + _PITCH_CYCLE.index(step)


def _clef_anchor(clef: str | None) -> tuple[str, int] | None:
    """(step, octave) on the TOP line for a clef name, the same arithmetic
    `pitch_resolver._anchor_for` does, from the same table."""
    if not clef:
        return None
    from ..clef_geometry import CLEF_TO_FAMILY_LINE  # dataclass-only module

    shift = 0
    base = clef
    for suffix, s in _OCTAVE_SUFFIX_SHIFT.items():
        if clef.endswith(suffix):
            base, shift = clef[: -len(suffix)], s
            break
    fl = CLEF_TO_FAMILY_LINE.get(base)
    if fl is None:
        return None
    family, line = fl
    pc, octave = _FAMILY_REFERENCE_PITCH[family]
    idx = _PITCH_CYCLE.index(pc) + 2 * (5 - line)
    return _PITCH_CYCLE[idx % 7], octave + idx // 7 + shift


def staff_y_for_pitch(pitch: str | None, clef: str | None,
                      line_ys: list[float]) -> float | None:
    """Canonical y of a written pitch's notehead centre on a staff whose five
    line positions are `line_ys` (top first). None when the clef is unknown
    or the pitch does not parse."""
    if not pitch or not line_ys or len(line_ys) < 5:
        return None
    m = re.match(r"^([A-G])[#b]*(-?\d+)$", pitch)
    if not m:
        return None
    anchor = _clef_anchor(clef)
    if anchor is None:
        return None
    half = (line_ys[-1] - line_ys[0]) / 8.0
    position = _diatonic_index(*anchor) - _diatonic_index(m.group(1), int(m.group(2)))
    return line_ys[0] + position * half


def on_line_or_in_space(pitch: str | None, clef: str | None) -> str | None:
    """Whether a written pitch sits ON a line or IN a space for this clef —
    even half-steps from the top line are lines, odd are spaces, and the
    parity keeps working through the ledger positions."""
    if not pitch:
        return None
    m = re.match(r"^([A-G])[#b]*(-?\d+)$", pitch)
    anchor = _clef_anchor(clef)
    if not m or anchor is None:
        return None
    position = _diatonic_index(*anchor) - _diatonic_index(m.group(1), int(m.group(2)))
    return "OnLine" if position % 2 == 0 else "InSpace"
