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

Matching is on STAFF POSITION by default: the reference note's position
comes from its pitch and the WRITTEN CLEF the reference file carries, and
the detection's from its box against the staff lines — neither side uses
the pipeline's clef reading. On a scan the pipeline often calls a bass or
alto staff treble, which spells every pitch on that staff wrong while placing
every notehead right; matched this way the boxes still confirm. `match="step"`
compares step + octave (accidental ignored) and `match="exact"` the spelling
too — both need the pipeline's clef to have been right.
"""

from __future__ import annotations

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


def _position_key(position: int | None, fallback: str) -> str:
    return f"P{position}" if position is not None else fallback


def truth_tokens(notes: list[TruthNote], *, match: str = "position",
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
        elif match == "position":
            # Falls back to the step key where the reference names no clef.
            key = _position_key(staff_position(n.pitch, n.clef), _pitch_key(n.pitch, "step"))
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


def detection_position(det: dict[str, Any], line_ys: list[float] | None) -> int | None:
    """Half-steps from the top line, down positive, of a detection's box
    centre on a staff whose canonical line positions are `line_ys` — the
    same arithmetic `pitch_resolver` used, without its clef."""
    if not line_ys or len(line_ys) < 5 or line_ys[-1] <= line_ys[0]:
        return None
    bbox = det.get("bbox")
    if not bbox or len(bbox) < 4:
        return None
    cy = bbox[1] + bbox[3] / 2.0
    half = (line_ys[-1] - line_ys[0]) / 8.0
    return int(round((cy - line_ys[0]) / half))


def tremolo_runs(notes: list[TruthNote], *, min_len: int = 3,
                 min_total_ql: float = 2.0) -> dict[int, tuple[int, int, float, int]]:
    """Runs of repeated notes an engraver may print as ONE hollow head with
    tremolo strokes: at least `min_len` consecutive notes of the same pitch
    and value, no rest or other pitch between them, adding up to at least a
    half note. The reference spells them out (six eighths); the Breitkopf
    Brahms prints a dotted half with two slashes, which the detector — and a
    labeler — sees as one hollow head. Returns `id(note)` → (index in run,
    run length, total quarter-length) for every note in such a run; the fourth element is the run id — the
    first note's `id`, shared by every member."""
    out: dict[int, tuple[int, int, float, int]] = {}
    seq = [n for n in notes if not n.grace]
    i = 0
    while i < len(seq):
        n = seq[i]
        j = i + 1
        if not n.rest and n.pitch and n.duration_ql > 0:
            while (j < len(seq) and not seq[j].rest and seq[j].pitch == n.pitch
                   and abs(seq[j].duration_ql - n.duration_ql) < 1e-6
                   and not seq[j].chord):
                j += 1
        length = j - i
        total = length * n.duration_ql if not n.rest else 0.0
        if length >= min_len and total >= min_total_ql:
            for k in range(length):
                out[id(seq[i + k])] = (k, length, total, id(seq[i]))
        i = j if j > i else i + 1
    return out


def abbreviation_type(total_ql: float) -> tuple[str, int] | None:
    """The written value a tremolo of `total_ql` quarter-lengths would take:
    (type, dots). None where no single note value fits."""
    table = {2.0: ("half", 0), 3.0: ("half", 1), 4.0: ("whole", 0), 6.0: ("whole", 1),
             8.0: ("breve", 0)}
    for ql, tv in table.items():
        if abs(total_ql - ql) < 1e-6:
            return tv
    return None


def event_tokens(events: list[dict[str, Any]], *, match: str = "position",
                 include_rests: bool = True,
                 line_ys: list[float] | None = None) -> list[Token]:
    """Tokens for one predicted measure from `voicing.group_chords_in_measure`
    output. `ref` is the notehead or rest DETECTION DICT itself — the same
    object that sits in `measure["detections"]`, so identity maps it back.
    `line_ys` (the measure's canonical staff lines) is what `position`
    matching reads the box against; without it the step key is used."""
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
            if match == "position":
                key = _position_key(detection_position(nh, line_ys),
                                    _pitch_key(nh.get("pitch"), "step"))
            else:
                key = _pitch_key(nh.get("pitch"), match)
            out.append(Token(key=key, pitch=nh.get("pitch"),
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
    # Pairs matched only within the position tolerance (never on an exact key).
    near_pairs: list[tuple[int, int]] = field(default_factory=list)

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


def _position_of_key(key: str) -> int | None:
    if key.startswith("P"):
        try:
            return int(key[1:])
        except ValueError:
            return None
    return None


def _match_weight(a: str, b: str, tolerance: int) -> int:
    """2 for an exact key match, 1 for two positions within `tolerance`
    half-steps, 0 otherwise. A head's box centre on a scan can round half a
    space off — `P6` read as `P5` — and an exact key would lose the whole
    note; the lower weight keeps an exact match preferred wherever one
    exists."""
    if a == b:
        return 2
    if tolerance <= 0:
        return 0
    pa, pb = _position_of_key(a), _position_of_key(b)
    if pa is None or pb is None:
        return 0
    return 1 if abs(pa - pb) <= tolerance else 0


def align_tokens(truth: list[Token], pred: list[Token], *, tolerance: int = 1) -> Alignment:
    """Weighted longest common subsequence over token keys — order-
    preserving, so a note can only match a note the reading placed in the
    same relative position: a transposed bar or a bar from the wrong measure
    matches little and the caller's gate refuses it. An exact key match
    scores 2, a position within `tolerance` scores 1, so the alignment
    takes the exact pairing when one exists."""
    n, m = len(truth), len(pred)
    if n == 0 or m == 0:
        return Alignment(pairs=[], truth_unmatched=list(range(n)),
                         pred_unmatched=list(range(m)), n_truth=n, n_pred=m)
    ta = [t.key for t in truth]
    pb = [p.key for p in pred]
    score = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        row, prev = score[i], score[i - 1]
        for j in range(1, m + 1):
            best = prev[j] if prev[j] >= row[j - 1] else row[j - 1]
            w = _match_weight(ta[i - 1], pb[j - 1], tolerance)
            if w and prev[j - 1] + w > best:
                best = prev[j - 1] + w
            row[j] = best
    pairs: list[tuple[int, int]] = []
    near: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        w = _match_weight(ta[i - 1], pb[j - 1], tolerance)
        if w and score[i][j] == score[i - 1][j - 1] + w:
            pairs.append((i - 1, j - 1))
            if w == 1:
                near.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif score[i - 1][j] >= score[i][j - 1]:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    near.reverse()
    tm = {a for a, _ in pairs}
    pm = {b for _, b in pairs}
    return Alignment(
        pairs=pairs,
        truth_unmatched=[i for i in range(len(truth)) if i not in tm],
        pred_unmatched=[j for j in range(len(pred)) if j not in pm],
        n_truth=len(truth),
        n_pred=len(pred),
        near_pairs=near,
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


def staff_position(pitch: str | None, clef: str | None) -> int | None:
    """Half-steps from the TOP line, down positive, where a written pitch
    sits in this clef: 0 is the top line, 8 the bottom line, negative is
    above the staff. None when the clef is unknown or the pitch unparseable."""
    if not pitch:
        return None
    m = re.match(r"^([A-G])[#b]*(-?\d+)$", pitch)
    anchor = _clef_anchor(clef)
    if not m or anchor is None:
        return None
    return _diatonic_index(*anchor) - _diatonic_index(m.group(1), int(m.group(2)))


def staff_y_for_pitch(pitch: str | None, clef: str | None,
                      line_ys: list[float]) -> float | None:
    """Canonical y of a written pitch's notehead centre on a staff whose five
    line positions are `line_ys` (top first). None when the clef is unknown
    or the pitch does not parse."""
    if not line_ys or len(line_ys) < 5:
        return None
    position = staff_position(pitch, clef)
    if position is None:
        return None
    half = (line_ys[-1] - line_ys[0]) / 8.0
    return line_ys[0] + position * half


def on_line_or_in_space(pitch: str | None, clef: str | None) -> str | None:
    """Whether a written pitch sits ON a line or IN a space for this clef —
    even half-steps from the top line are lines, odd are spaces, and the
    parity keeps working through the ledger positions."""
    position = staff_position(pitch, clef)
    if position is None:
        return None
    return "OnLine" if position % 2 == 0 else "InSpace"
