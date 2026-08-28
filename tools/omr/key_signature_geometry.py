"""Read a key signature from WHERE its accidentals sit, not from how many were
detected.

A key signature is the most positional object on the page. It is N copies of a
single glyph, printed at staff positions that are fixed once you know the clef
and N — there is no other information in it. Yet the reading this pipeline has
done until now (`transcribe._detect_key_sig_from_cell`) is to *count*
`keySharp` / `keyFlat` detections anywhere in the cell and take the count as the
answer. Counting throws away the one thing that is certain and keeps the one
thing that is fragile:

  * Four flats printed, three detected, and the staff reads E♭ major instead of
    A♭ major. Every B, E and A on that staff is now a semitone wrong, silently.
  * One inline accidental inside the header cell, and three flats read as four.
  * Nothing ever checks the result against the clef, so no reading is too
    absurd to emit.

Fitting positions fixes all three, and fixes the first one in the strong sense:
flats observed at slots 1, 2 and 4 do not mean "three flats", they mean **four
flats with the third missed** — the gap in the pattern says so. The count is
recovered from a partial observation rather than being corrupted by it.

## The slot tables

Positions are measured the way `pitch_resolver` measures them: `pos` = diatonic
steps below the TOP staff line, so pos 0 is the top line, pos 8 the bottom line,
negative is above the staff. The tables below are written as the pitches an
engraver actually prints, because that is the form in which they can be checked
against a score by eye; `_slot_positions` converts them through the clef anchor.

Two conventions in these tables are worth naming, because both look like
mistakes and neither is:

  * In treble clef the third sharp, G♯5, sits ABOVE the top line (pos −1).
    That is standard engraving, not an error.
  * In bass clef the seventh flat, F♭2, sits BELOW the bottom line (pos 9).
    Also standard.
  * Tenor clef breaks the octave pattern outright: its first sharp is F♯3, an
    octave below the F♯4 the other clefs would imply, because F♯4 in tenor clef
    would sit above the staff. This is why the tables are written out per clef
    instead of derived by transposition — the derivation would be wrong here.

Clefs without a table (the rare C clefs — soprano, mezzo-soprano, baritone —
and the rare G/F variants) return None, and the caller keeps whatever the count
gave it. Inventing a table for a clef whose convention has not been checked
would re-pitch a whole staff on a guess, which is the trade `clef_geometry`
already refuses to make.

## Fitting

The glyph's vertical anchor — where inside its bounding box the pitch actually
falls — differs by glyph: a sharp and a natural are centred on their pitch, but
a flat's bowl is centred while its ascender rises a full space above, so a
flat's box centre sits well above the note it alters. Rather than calibrate an
anchor fraction per glyph (measurable, but one more number to get wrong), the
fit solves for a single constant offset shared by every accidental in the run.
That works because a key signature is one glyph repeated: whatever the anchor
error is, it is identical for all of them, so it falls out of the RELATIVE
pattern, which is the part that identifies the signature. The offset is then
sanity-checked for size, not trusted blindly.

Two rules keep the fit honest:

  * **Prefix only.** A key signature is always the first N accidentals of the
    order — no signature omits an earlier one. So the observed accidentals must
    map to a prefix of the slot list, in x-order.
  * **Never extend past the last observation.** N is the index of the last slot
    that was actually matched. Interior slots may be inferred (that is the
    recovery this module exists for), trailing ones never are — otherwise a
    clean 3-flat signature could be "recovered" into a 4-flat one on no
    evidence at all.
  * **The first slot must be seen, and inference must not outvote observation.**
    Without this, two accidentals can be assigned to slots 4 and 5 and the fit
    reports a five-accidental signature off two glyphs, inventing the three it
    never saw — measured, on a page of three-flat staves reading as five sharps.
    The first accidental is the one printed hard against the clef and the one a
    locator finds first, so an assignment that skips it is describing something
    other than a key signature. `max_inferred_ratio` then keeps the recovery
    honest: it may fill gaps in what was observed, never outnumber it.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from .pitch_resolver import _CLEF_ANCHORS, _PITCH_CYCLE


# The order accidentals are added in. Fixed for all music.
SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]

# The pitch printed at each slot, per clef. Written out rather than derived —
# see the module docstring on tenor clef.
SHARP_PITCHES: dict[str, list[str]] = {
    "treble": ["F5", "C5", "G5", "D5", "A4", "E5", "B4"],
    "bass":   ["F3", "C3", "G3", "D3", "A2", "E3", "B2"],
    "alto":   ["F4", "C4", "G4", "D4", "A3", "E4", "B3"],
    "tenor":  ["F3", "C4", "G3", "D4", "A3", "E4", "B3"],
}
FLAT_PITCHES: dict[str, list[str]] = {
    "treble": ["B4", "E5", "A4", "D5", "G4", "C5", "F4"],
    "bass":   ["B2", "E3", "A2", "D3", "G2", "C3", "F2"],
    "alto":   ["B3", "E4", "A3", "D4", "G3", "C4", "F3"],
    "tenor":  ["B3", "E4", "A3", "D4", "G3", "C4", "F3"],
}


@dataclass(frozen=True)
class KeySignatureFitConfig:
    """Knobs for the positional fit. Distances are in diatonic steps (half a
    staff space each), the unit the slot tables are written in.

    max_residual:
        How far an accidental may sit from its slot, after the shared offset is
        removed, before the fit is rejected. Adjacent slots are never closer
        than one step, so half a step is the point where an accidental is
        equidistant between the slot claimed and its neighbour.
    max_offset:
        How large the shared glyph-anchor offset may be. A flat's box centre
        legitimately sits about a step above its pitch; much more than that
        means the boxes are not key-signature accidentals at all. Kept tight
        because a loose offset lets a single stray glyph slide onto whichever
        slot happens to be nearest and "fit" perfectly.
    max_inferred_ratio:
        How many slots the fit may fill in for each one it actually saw.
    """

    max_residual: float = 0.5
    max_offset: float = 1.25
    # At most this many inferred slots per observed one. 1.0 lets a run of two
    # recover two gaps but never describe a signature it mostly did not see.
    max_inferred_ratio: float = 1.0


DEFAULT_CONFIG = KeySignatureFitConfig()


@dataclass(frozen=True)
class KeySignatureRead:
    """The outcome of fitting a run of accidentals to a key signature.

    fifths:        circle-of-fifths position — +N for N sharps, −N for N flats,
                   0 for no key signature. The form `transcribe`'s cross-staff
                   consistency check already speaks.
    accidental:    "#", "b", or None when the signature is empty.
    matched_slots: 1-based slot numbers an observed accidental was assigned to.
    inferred_slots:1-based slots the pattern says are there but nothing was
                   detected at — the recovered glyphs.
    offset:        the shared glyph-anchor offset the fit solved for, in steps.
    residual:      mean distance from observation to slot after removing the
                   offset, in steps. 0.0 for an empty signature.
    """

    fifths: int
    accidental: str | None
    matched_slots: tuple[int, ...]
    inferred_slots: tuple[int, ...]
    offset: float
    residual: float

    @property
    def count(self) -> int:
        return abs(self.fifths)


def _pitch_position(pitch: str, clef: str) -> float | None:
    """Diatonic steps from the top staff line down to `pitch` under `clef`.

    The inverse of `pitch_resolver._pitch_from_position`, and it reads the same
    anchor table, so the two can never disagree about what a clef means.
    """
    anchor = _CLEF_ANCHORS.get(clef)
    if anchor is None or len(pitch) < 2:
        return None
    letter, octave_text = pitch[0], pitch[1:]
    if letter not in _PITCH_CYCLE:
        return None
    try:
        octave = int(octave_text)
    except ValueError:
        return None
    anchor_pc, anchor_octave = anchor
    # Steps are counted downward, and pitch decreases downward.
    anchor_index = _PITCH_CYCLE.index(anchor_pc) + 7 * anchor_octave
    pitch_index = _PITCH_CYCLE.index(letter) + 7 * octave
    return float(anchor_index - pitch_index)


def _base_clef(clef: str | None) -> str | None:
    """Strip an octave-transposition suffix. An `8va` / `8vb` marker changes
    what a staff SOUNDS, never where its key signature is PRINTED, so the
    written positions are the base clef's.
    """
    if not clef:
        return None
    for suffix in ("_8va", "_8vb", "_15ma", "_15mb"):
        if clef.endswith(suffix):
            return clef[: -len(suffix)]
    return clef


def slot_positions(clef: str | None, accidental: str) -> list[float] | None:
    """The seven slot positions for `accidental` ("#" or "b") under `clef`, in
    steps below the top staff line. None when the clef has no table — the
    caller must then fall back rather than guess.
    """
    base = _base_clef(clef)
    table = SHARP_PITCHES if accidental == "#" else FLAT_PITCHES
    pitches = table.get(base or "")
    if pitches is None:
        return None
    out = []
    for pitch in pitches:
        pos = _pitch_position(pitch, base)
        if pos is None:
            return None
        out.append(pos)
    return out


def fit_key_signature(
    observed: list[float],
    clef: str | None,
    accidental: str,
    config: KeySignatureFitConfig = DEFAULT_CONFIG,
) -> KeySignatureRead | None:
    """Fit accidentals observed at `observed` staff positions (in x-order, in
    steps below the top staff line) to a key signature under `clef`.

    Returns None when the clef has no slot table, when there are more
    accidentals than slots, or when nothing fits within tolerance — abstaining
    so the caller can fall back to the count rather than accept a bad reading.
    """
    if accidental not in ("#", "b"):
        return None
    slots = slot_positions(clef, accidental)
    if slots is None:
        return None
    if not observed:
        return KeySignatureRead(0, None, (), (), 0.0, 0.0)
    if len(observed) > len(slots):
        return None

    best: tuple[float, tuple[int, ...]] | None = None
    best_offset = 0.0
    # An assignment is a choice of which slots the observations landed on,
    # keeping x-order. `combinations` enumerates them already in order, so the
    # k-th observation goes to the k-th chosen slot.
    for assignment in combinations(range(len(slots)), len(observed)):
        # A signature starts at slot 1. An assignment that begins later is
        # describing something else — see the module docstring.
        if assignment[0] != 0:
            continue
        n_inferred = (assignment[-1] + 1) - len(observed)
        if n_inferred > config.max_inferred_ratio * len(observed):
            continue
        deltas = [observed[k] - slots[s] for k, s in enumerate(assignment)]
        offset = sum(deltas) / len(deltas)
        if abs(offset) > config.max_offset:
            continue
        residuals = [abs(d - offset) for d in deltas]
        if max(residuals) > config.max_residual:
            continue
        mean_residual = sum(residuals) / len(residuals)
        if best is None or mean_residual < best[0]:
            best = (mean_residual, assignment)
            best_offset = offset

    if best is None:
        return None
    mean_residual, assignment = best
    # N is the LAST matched slot: interior gaps are recovered, trailing slots
    # are never invented. See the module docstring.
    count = assignment[-1] + 1
    matched = tuple(s + 1 for s in assignment)
    inferred = tuple(s for s in range(1, count + 1) if s not in matched)
    fifths = count if accidental == "#" else -count
    return KeySignatureRead(
        fifths=fifths,
        accidental=accidental,
        matched_slots=matched,
        inferred_slots=inferred,
        offset=best_offset,
        residual=mean_residual,
    )


def alterations_for_fifths(fifths: int) -> dict[str, str]:
    """{letter: '#'|'b'} for a circle-of-fifths position — the map the pitch
    pass applies to noteheads. Empty for 0.
    """
    if fifths > 0:
        return {letter: "#" for letter in SHARP_ORDER[:fifths]}
    if fifths < 0:
        return {letter: "b" for letter in FLAT_ORDER[:-fifths]}
    return {}
