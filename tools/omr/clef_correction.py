"""Propose a staff's clef from its instrument's written range.

## Why this can work now, when the tonal version could not

`benchmarks/omr-clef-key-fit-2026-08` measured four ways to recover a clef from
the music itself and none beat guessing "treble" (68.7%). The reason is
structural: **a staff's note geometry is clef-invariant.** Rereading a staff
under another clef shifts every note by one constant interval and preserves
every interval between notes, so contour, interval content and key-profile
statistics all move with the hypothesis. Nothing internal to the staff breaks
the symmetry.

What breaks it is an **absolute register anchor**, which is exactly what
instrument identity supplies. A bassoon staff resolving around MIDI 60-90 under
a defaulted treble clef is wrong, and reading it as bass clef drops it 12
diatonic steps into the bassoon's written range of 34-72. That is a fact about
the instrument, not about the notes, so the clef-invariance argument does not
apply to it.

The chain that makes it available: `system_grouping` gives correct systems ->
`slots` gives each staff a stable part identity -> `staff_labels` / `instruments`
give that part a written range.

## Why it is a post-pass

`pitch_resolver.clef_diatonic_shift` makes a clef hypothesis pure arithmetic on
already-resolved pitches — no image, no re-detection. So this runs over the
built page dicts and restates a staff's pitches in place, rather than
re-entering the detection pipeline.

## Gating — this must not touch a staff the detector actually read

Three conditions, all required:

1. **The detector never saw a clef glyph on this staff.** Same "speak only when
   the detector is silent" rule the C-clef locator follows: a staff whose clef
   was genuinely detected is left alone, and only flagged if it disagrees.
2. **The instrument label is high confidence.** A wrong instrument would
   propagate a wrong range and "correct" a correct staff.
3. **One candidate clef fits and the alternatives do not**, by a clear margin.
   A staff whose register is ambiguous between two clefs is left alone — the
   surrounding layer abstains rather than guesses, as the other checks do.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .instruments import Instrument
from .pitch_resolver import (
    NOTE_SEMITONE,
    _CLEF_ANCHORS,
    clef_diatonic_shift,
    diatonic_index,
    parse_pitch,
    pitch_from_diatonic_index,
    pitch_to_midi,
)

# Clefs a staff may be re-read as. Octave-displaced variants are excluded: they
# leave the letters unchanged and differ only in register, so admitting them
# would let the range fit slide a staff by an octave to chase its own anchor.
CANDIDATE_CLEFS = ("treble", "bass", "alto", "tenor")

MIN_NOTEHEADS = 12          # below this a register estimate is not worth acting on
MIN_FIT = 0.75              # a clef must place this fraction of notes in range
MIN_FIT_MARGIN = 0.25       # margin required when choosing on range fit alone
HIGH_CONFIDENCE_FIT = 0.9   # ...and the margin over the current clef for "high"

_SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
_FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]
_INLINE_ALT = {"accidentalsharp": 1, "accidentalflat": -1, "accidentalnatural": 0,
               "accidentaldoublesharp": 2, "accidentaldoubleflat": -2}


@dataclass(frozen=True)
class ClefProposal:
    """A clef the register evidence prefers over the one in effect."""

    staff_index: int
    from_clef: str
    to_clef: str
    instrument: str
    fit: float                  # fraction of noteheads inside the written range
    current_fit: float
    margin: float               # fit advantage over the runner-up
    n_noteheads: int
    confidence_label: str


def _key_alterations(key_sig: dict[str, Any] | None) -> dict[str, int]:
    """{letter: alteration} for a staff dict's `key_signature` summary."""
    if not key_sig:
        return {}
    alterations = key_sig.get("alterations")
    if isinstance(alterations, dict) and alterations:
        return {k: (1 if v == "#" else -1) for k, v in alterations.items()}
    sharps, flats = key_sig.get("sharps", 0), key_sig.get("flats", 0)
    if sharps:
        return {letter: 1 for letter in _SHARP_ORDER[:sharps]}
    if flats:
        return {letter: -1 for letter in _FLAT_ORDER[:flats]}
    return {}


def _explicit_accidentals(detections: list[dict[str, Any]]) -> dict[int, int]:
    """`{index of notehead detection: alteration}` for noteheads carrying an
    inline accidental glyph, by the same geometry rule the pipeline uses when it
    resolves pitch (`transcribe._pair_accidentals_to_noteheads`).

    Needed because restating a staff under a new clef must re-apply the KEY
    SIGNATURE to the new letter names, while leaving an explicitly written
    accidental exactly as engraved.
    """
    accidentals, noteheads = [], []
    for i, det in enumerate(detections):
        cls = (det.get("class") or "").lower()
        if det.get("category") == "accidental" and cls in _INLINE_ALT:
            accidentals.append((det, _INLINE_ALT[cls]))
        elif det.get("category") == "notehead":
            noteheads.append((i, det))

    out: dict[int, int] = {}
    for acc, alt in accidentals:
        ax, ay, aw, ah = acc.get("bbox", (0, 0, 0, 0))
        a_right, a_yc, a_h = ax + aw, ay + ah // 2, max(1, ah)
        best, best_score = None, float("inf")
        for i, nh in noteheads:
            nx, ny, nw, nh_h = nh.get("bbox", (0, 0, 0, 0))
            if nx + nw < a_right:
                continue
            y_dist = abs(ny + nh_h // 2 - a_yc)
            if y_dist > a_h * 0.6:
                continue
            score = max(0, nx - a_right) + 3 * y_dist
            if score < best_score:
                best_score, best = score, i
        if best is not None:
            out[best] = alt
    return out


def restate_pitch(pitch: str, delta: int, key_alterations: dict[str, int],
                  explicit_alt: int | None) -> str | None:
    """This pitch as it reads under a clef `delta` diatonic steps away.

    The letter moves by `delta`; the accidental is re-derived — an explicitly
    engraved accidental is kept as written, everything else takes the key
    signature's alteration for its NEW letter.
    """
    parsed = parse_pitch(pitch)
    if parsed is None:
        return None
    letter, _alt, octave = parsed
    new_letter, new_octave = pitch_from_diatonic_index(
        diatonic_index(letter, octave) + delta)
    alteration = explicit_alt if explicit_alt is not None else \
        key_alterations.get(new_letter, 0)
    suffix = "#" * alteration if alteration > 0 else "b" * -alteration
    return f"{new_letter}{suffix}{new_octave}"


def staff_has_detected_clef(staff: dict[str, Any]) -> bool:
    """Whether any clef glyph was detected anywhere on this staff."""
    return any(det.get("category") == "clef"
               for measure in staff.get("measures", [])
               for det in measure.get("detections", []))


def _midis_under(staff: dict[str, Any], delta: int) -> list[int]:
    out = []
    for measure in staff.get("measures", []):
        for det in measure.get("detections", []):
            if det.get("category") != "notehead":
                continue
            parsed = parse_pitch(det.get("pitch"))
            if parsed is None:
                continue
            letter, alt, octave = parsed
            new_letter, new_octave = pitch_from_diatonic_index(
                diatonic_index(letter, octave) + delta)
            out.append(12 * (new_octave + 1) + NOTE_SEMITONE[new_letter] + alt)
    return out


def range_fit(midis: list[int], lo: int, hi: int) -> float:
    """Fraction of notes inside the instrument's written range."""
    if not midis:
        return 0.0
    return sum(1 for m in midis if lo <= m <= hi) / len(midis)


def propose_clef(staff: dict[str, Any], instrument: Instrument) -> ClefProposal | None:
    """The clef this staff should carry, or None to leave it alone.

    Range fit alone is often not decisive, because a written range generous
    enough not to false-flag admits more than one shift: a bassoon staff fits
    bass at 1.00 and tenor at 0.95 (both are real bassoon clefs), and a viola
    staff fits alto at 1.00 and treble at 0.98. So the instrument's OWN default
    clef leads, and the range's job is to veto it — which is the same reasoning a
    reader uses ("violas read alto, unless what I see says otherwise").

    That is sound precisely where this pass is allowed to act. The caller only
    applies a proposal when the detector saw no clef glyph at all, and in that
    case the clef in effect is `_default_clef_for_position` — a positional guess
    carrying no evidence. Replacing a guess with the instrument's own convention,
    checked against the register, is strictly better information.
    """
    current = staff.get("clef")
    if current not in _CLEF_ANCHORS:
        return None
    lo, hi = instrument.written_range

    fits: dict[str, float] = {}
    n = 0
    for candidate in CANDIDATE_CLEFS:
        delta = clef_diatonic_shift(current, candidate)
        if delta is None:
            continue
        midis = _midis_under(staff, delta)
        n = max(n, len(midis))
        fits[candidate] = range_fit(midis, lo, hi)
    if n < MIN_NOTEHEADS or not fits:
        return None

    current_fit = fits.get(current, 0.0)
    ranked = sorted(fits.items(), key=lambda kv: -kv[1])
    runner_up_fit = ranked[1][1] if len(ranked) > 1 else 0.0

    default = instrument.default_clef
    if fits.get(default, 0.0) >= MIN_FIT:
        chosen, chosen_fit = default, fits[default]
        margin = chosen_fit - current_fit
    else:
        # The instrument's convention is contradicted by the register, so fall
        # back to the best-fitting clef — and then demand a real margin, since
        # nothing but the range is speaking.
        chosen, chosen_fit = ranked[0]
        margin = chosen_fit - runner_up_fit
        if chosen_fit < MIN_FIT or margin < MIN_FIT_MARGIN:
            return None

    # Never make the register worse, and never propose what is already in effect.
    if chosen == current or chosen_fit < current_fit:
        return None

    if chosen_fit >= HIGH_CONFIDENCE_FIT and (chosen_fit - current_fit) >= MIN_FIT_MARGIN:
        label = "high"
    elif chosen_fit >= MIN_FIT:
        label = "medium"
    else:
        label = "low"
    return ClefProposal(
        staff_index=staff.get("staff_index", -1), from_clef=current, to_clef=chosen,
        instrument=instrument.name, fit=round(chosen_fit, 3),
        current_fit=round(current_fit, 3), margin=round(margin, 3),
        n_noteheads=n, confidence_label=label,
    )


def apply_proposal(staff: dict[str, Any], proposal: ClefProposal) -> int:
    """Restate every pitch on the staff under the proposed clef, in place.

    Returns the number of noteheads restated. `pitch_candidates` are dropped
    rather than shifted: they exist for M4 re-ranking against the OLD clef's
    reading and would be misleading once the clef changes.
    """
    delta = clef_diatonic_shift(proposal.from_clef, proposal.to_clef)
    if delta is None:
        return 0
    changed = 0
    for measure in staff.get("measures", []):
        detections = measure.get("detections", [])
        explicit = _explicit_accidentals(detections)
        alterations = _key_alterations(measure.get("key_signature")
                                       or staff.get("key_signature"))
        for i, det in enumerate(detections):
            if det.get("category") == "clef":
                continue
            if det.get("category") != "notehead" or det.get("pitch") is None:
                continue
            restated = restate_pitch(det["pitch"], delta, alterations, explicit.get(i))
            if restated is not None:
                det["pitch"] = restated
                det.pop("pitch_candidates", None)
                changed += 1
        if measure.get("clef") == proposal.from_clef:
            measure["clef"] = proposal.to_clef
    staff["clef"] = proposal.to_clef
    return changed


def correct_clefs_from_instruments(
    pages: list[dict[str, Any]],
    instrument_by_slot: dict[int, Instrument],
    slot_by_staff: dict[tuple[int, int, int], int],
    *,
    apply: bool = True,
) -> list[dict[str, Any]]:
    """Propose (and optionally apply) clef corrections across built page dicts.

    `slot_by_staff` maps `(page_index, system_index, staff_index)` to slot.
    Returns one record per proposal, whether or not it was applied — a staff
    whose clef the detector actually READ is reported with `applied: False`, so
    a disagreement is surfaced without being acted on.
    """
    records: list[dict[str, Any]] = []
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                instrument = instrument_by_slot.get(slot) if slot is not None else None
                if instrument is None or instrument.unpitched:
                    continue
                proposal = propose_clef(staff, instrument)
                if proposal is None:
                    continue
                detected = staff_has_detected_clef(staff)
                do_apply = apply and not detected
                record = {
                    "page_index": key[0], "system_index": key[1],
                    "staff_index": key[2], "slot": slot,
                    "instrument": proposal.instrument,
                    "from_clef": proposal.from_clef, "to_clef": proposal.to_clef,
                    "fit": proposal.fit, "current_fit": proposal.current_fit,
                    "margin": proposal.margin, "n_noteheads": proposal.n_noteheads,
                    "confidence_label": proposal.confidence_label,
                    "detector_saw_a_clef": detected,
                    "applied": do_apply,
                }
                if do_apply:
                    record["noteheads_restated"] = apply_proposal(staff, proposal)
                staff["clef_proposal"] = record
                records.append(record)
    return records
