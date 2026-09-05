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

1. **No reader read this staff's clef** — `staff["clef_source"]` is absent, so
   the staff carries an inherited clef or the position default. Same "speak only
   when the detector is silent" rule the C-clef locator follows: a staff whose
   clef was genuinely read is left alone, and only flagged if it disagrees.
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


def clef_was_read(staff: dict[str, Any]) -> bool:
    """Whether any reader actually read this staff's clef, as opposed to the
    staff carrying an inherited clef or the position default.

    `staff_dict["clef_source"]` is the authority: present means one of the
    readers supplied the clef ("detector", "specialist", or "cv_locator"),
    absent means nothing did. **This must not be replaced by scanning for a
    `category == "clef"` detection.** The clef-geometry layer reads a clef by
    SHAPE and by which staff line it sits on (`clef_locator`, `clef_geometry`)
    and emits no clef detection at all, so a detection scan reports "silent" for
    a staff whose clef was confidently read — and this pass would then overwrite
    it.

    The detection scan is still OR-ed in, for two reasons: it covers JSON
    produced before `clef_source` existed, and `clef_source` reflects only the
    staff's FIRST cell, so a mid-staff clef change detected later would
    otherwise go unseen. Erring toward "it was read" is the safe direction —
    the cost is a flag instead of a fix, rather than a good clef overwritten.
    """
    if staff.get("clef_source"):
        return True
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


def _restate_measure(measure: dict[str, Any], delta: int,
                     staff_key_sig: dict[str, Any] | None,
                     staff_alterations: dict[str, int] | None = None) -> int:
    """Restate one measure's notehead pitches by `delta` diatonic steps.

    The same rules `apply_proposal` always used, factored so a per-measure
    caller (the mid-staff change veto) shares them: an explicitly engraved
    accidental is kept as written, everything else takes the key signature's
    alteration for its NEW letter, and `pitch_candidates` are dropped because
    they were ranked against the old clef's reading.

    `staff_alterations`, when given, replaces the staff-level alteration
    source (see `_restatement_alterations`); a measure whose own key signature
    differs from the staff's — a genuine mid-staff key change — still uses its
    own.
    """
    detections = measure.get("detections", [])
    explicit = _explicit_accidentals(detections)
    m_ks = measure.get("key_signature")
    if staff_alterations is not None and (m_ks is None or m_ks == staff_key_sig):
        alterations = staff_alterations
    else:
        alterations = _key_alterations(m_ks or staff_key_sig)
    changed = 0
    for i, det in enumerate(detections):
        if det.get("category") != "notehead" or det.get("pitch") is None:
            continue
        restated = restate_pitch(det["pitch"], delta, alterations, explicit.get(i))
        if restated is not None:
            det["pitch"] = restated
            det.pop("pitch_candidates", None)
            changed += 1
    return changed


def _restatement_alterations(
    staff: dict[str, Any],
    system_staves: list[dict[str, Any]] | None,
    instrument: Instrument | None,
) -> dict[str, int] | None:
    """The alteration source a RESTATEMENT should use for this staff.

    Measured on 575951-p1's viola: the override restated every letter
    correctly and OMR-NED still rose by 2, because the staff's own signature
    was read as 1 flat, REJECTED by the cross-page vote ("differs from the
    system's 3 flats"), and carried as zero — so every restated E/A/B lost
    the flat C minor gives it. The staff's own reading is trusted where it
    was READ (`key_signature_read`); where it was not, a CONCERT-PITCH,
    non-percussion instrument takes the majority signature among the
    system's staves that WERE read — the same fact the vote's rejection
    reason already cites. Transposing staves (clarinet in B, horns) are
    excluded because their written key legitimately differs from the
    system's, and timpani because the convention writes them unsigned.

    Returns None to mean "no opinion — use the old sourcing".
    """
    if staff.get("key_signature_read"):
        return None
    if instrument is None or instrument.chromatic != 0 \
            or instrument.family == "percussion":
        return None
    if not system_staves:
        return None
    tally: dict[str, tuple[int, dict[str, Any]]] = {}
    for other in system_staves:
        if other is staff or not other.get("key_signature_read"):
            continue
        ks = other.get("key_signature")
        if not isinstance(ks, dict):
            continue
        key = f"{ks.get('sharps', 0)}#{ks.get('flats', 0)}b"
        n, _ = tally.get(key, (0, ks))
        tally[key] = (n + 1, ks)
    if not tally:
        return None
    _, majority_ks = max(tally.values(), key=lambda t: t[0])
    return _key_alterations(majority_ks)


def apply_proposal(staff: dict[str, Any], proposal: ClefProposal, *,
                   system_staves: list[dict[str, Any]] | None = None,
                   instrument: Instrument | None = None) -> int:
    """Restate every pitch on the staff under the proposed clef, in place.

    Returns the number of noteheads restated. `pitch_candidates` are dropped
    rather than shifted: they exist for M4 re-ranking against the OLD clef's
    reading and would be misleading once the clef changes.

    `system_staves` + `instrument`, when given, let an UNREAD key signature be
    replaced by the system majority for the restatement — see
    `_restatement_alterations`. Callers that omit them get the old sourcing.
    """
    delta = clef_diatonic_shift(proposal.from_clef, proposal.to_clef)
    if delta is None:
        return 0
    staff_alts = _restatement_alterations(staff, system_staves, instrument)
    changed = 0
    for measure in staff.get("measures", []):
        changed += _restate_measure(
            measure, delta, staff.get("key_signature"), staff_alts)
        if measure.get("clef") == proposal.from_clef:
            measure["clef"] = proposal.to_clef
    staff["clef"] = proposal.to_clef
    return changed


# ── The two mechanisms behind OMR_INSTRUMENT_CLEF_DEFAULT (2026-09-04) ──────
#
# Verified against the widened scan pool's `shift` damage
# (benchmarks/omr-clef-string-staves-2026-09/FINDINGS.md): the constant-offset
# staves are NOT positional defaults — they are (a) header clefs MISREAD as
# treble on staves whose margin label names a non-treble instrument, and
# (b) spurious mid-staff clef-change detections (clefF at 0.32-0.68) flipping
# the rest of a correctly-opened staff. Both act only on identity a reader
# actually READ off the page (never score-order deductions — measured to close
# the loop on its own mistake, Beethoven 5 p.15), and both are off unless the
# caller opts in.

# (a) Instruments for which a DETECTED treble may be overridden by the
# instrument's own default clef. Strictly the instruments with a verified
# damage site in the scan pool — Viola (575951-p1 s9, alto glyph read as
# clefG 0.72; whole staff +6), Bassoon and Timpani (brahms-p2 s4/s18/s8, all
# read treble over register fits of 0.926/0.571/0.000 against bass's 1.0).
# Treble-only is load-bearing: brahms-p1's cello reads TENOR correctly while
# the instrument convention says bass (fit ties 1.0/1.0), so overriding any
# detected non-treble clef with the convention is measured-unsafe. It is also
# the measured asymmetry `score_layouts` already encodes
# (SCORE_TREBLE_CONFLICT −0.3 vs −1.5): an all-treble read is the documented
# failure mode of clef detection on degraded prints, so "this staff reads
# treble" is weak evidence in a way "this staff reads tenor" is not.
# Cello/Contrabass are deliberately absent: no verified treble-misread site,
# and the pool's one cello clef error (dvorak-p5, tenor lost to bass 0.92 vs
# 0.88) is a case the convention AGREES with the wrong reading on.
# ⚠️ Contrabassoon added 2026-09-05, and the reason it was MISSING is the
# interesting part: this table is keyed on instrument NAMES and was written when
# "Contrabassoon" could not occur. `K-Fag.` resolved to **Bassoon** — which IS
# in this table — until another session's derived contra- cross product fixed
# the lexicon the same day. So a correct lexicon fix silently moved two Brahms
# p4 staves OUT of this tier's reach: the right label got less help than the
# wrong one had. Nothing changed in practice (the tier is off by default), which
# is exactly why it would have gone unnoticed.
# It meets this table's own admission standard — a verified treble-misread site
# with register evidence: both Kontrafagott staves propose treble->bass at fit
# 1.000 against a **current_fit of 0.000**, i.e. the clef in effect places not
# one of their 13 and 18 noteheads inside the instrument's written range.
# (`benchmarks/omr-staff-identity-labels-2026-09/`, probe_clef_consumer.py)
TREBLE_OVERRIDE_INSTRUMENTS = ("Viola", "Bassoon", "Contrabassoon", "Timpani")

# ⚠️ A confidence ceiling on the treble read was measured and REFUSED: the
# misread trebles score 0.34 and 0.72 while a CORRECT label-named treble
# (mahler-p3 s11, Violin) scores 0.61 — no threshold separates them. The
# guards are identity + the instrument's default + register fit, not the
# detector's own confidence in the glyph it misread.

# (b) Mid-staff clef CHANGES that are implausible for the named instrument.
# (instrument name, clef in effect, detected new clef) triples, strictly the
# verified sites: a violin staff never changes to bass (brahms-p1 s9, clefF
# 0.32 at m3 → −12 for three bars; 575951-p2 s8, clefF 0.68 at m7 → −12 for
# seven), and a viola staff never changes to bass (984073-p1 s9, clefF 0.59
# at m4 → −6 for the rest of the staff). Viola→treble is deliberately NOT
# vetoed — a viola goes to treble for high passages in real engraving — and
# cello changes (tenor/treble) are real and never touched.
MID_STAFF_CHANGE_VETOES = {
    ("Violin", "treble", "bass"),
    ("Viola", "alto", "bass"),
}


def _measure_clefs_uniform(staff: dict[str, Any], clef: str) -> bool:
    """Every measure of this staff is in `clef` — i.e. no mid-staff change.

    The treble-override tier requires this: a staff whose clef state changes
    mid-line is the change-veto's business, and restating ALL its measures by
    one header delta would also shift the measures resolved under the other
    clef."""
    return all(m.get("clef") == clef for m in staff.get("measures", []))


def veto_implausible_clef_changes(
    pages: list[dict[str, Any]],
    instrument_by_slot: dict[int, Instrument],
    slot_by_staff: dict[tuple[int, int, int], int],
    instrument_source_by_slot: dict[int, str],
) -> list[dict[str, Any]]:
    """Undo mid-staff clef changes that are implausible for the named part.

    Walks each staff's measures carrying the clef in effect; where the state
    changes and (instrument, from, to) is in `MID_STAFF_CHANGE_VETOES`, the
    change is treated as a spurious detection: that measure is restated back
    under the carried clef, and the walk continues as if the change never
    happened (so every following measure the bogus clef reached is restated
    too, up to the next change). A change NOT in the table is accepted and
    becomes the new carried clef — a cello stepping to tenor keeps its step.

    Identity gate: only staves whose instrument came from a READ margin label
    (`instrument_source == "label"`). Score-order deductions are exactly the
    staves this repertoire gets wrong (the p2 violas are named "Violin" by the
    prior), and the recorded rule stands: position-deduced identity must not
    drive clef correction.

    ⚠️ THAT PREDICTION WAS CONFIRMED INDEPENDENTLY, TWICE OVER, IN 2026-09.
    A held-out identity arm — margin labels hidden, prediction from clef and
    score order alone — reproduced this exact failure without knowing the
    sentence above existed: **Viola read as Violin, three times**, the largest
    single error family it produced
    (`benchmarks/omr-staff-identity-layer-2026-09/probe_heldout_identity.py`).
    And when a score-order identity supply was admitted to the UNGATED fill
    path next door, it regressed a row by NAMING a staff wrongly rather than
    abstaining (`price_clef_consumer.py`, mahler p5 +2 edits). A wrong derived
    identity is not merely uncertain: where the score-order prior is wrong, the
    truth is in its candidate set only 20% of the time, so it is confidently
    elsewhere. **Do not widen this gate on the strength of a precision figure
    alone** — precision is not what makes an override safe, calibration at the
    threshold is, and no calibrated probability exists for this yet
    (`probe_calibration.py`: neither P(name) nor P(set) calibrates, and the top
    bin promises 0.989 while delivering 0.692).

    Returns one record per staff acted on.
    """
    records: list[dict[str, Any]] = []
    for page in pages:
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                key = (page.get("page_index"), system.get("system_index"),
                       staff.get("staff_index"))
                slot = slot_by_staff.get(key)
                if slot is None:
                    continue
                if instrument_source_by_slot.get(slot) != "label":
                    continue
                instrument = instrument_by_slot.get(slot)
                if instrument is None:
                    continue
                measures = staff.get("measures", [])
                if len(measures) < 2:
                    continue
                carried = measures[0].get("clef")
                if carried not in _CLEF_ANCHORS:
                    continue
                staff_alts = _restatement_alterations(
                    staff, system.get("staves"), instrument)
                vetoed: list[dict[str, Any]] = []
                restated = 0
                for m_idx in range(1, len(measures)):
                    measure = measures[m_idx]
                    m_clef = measure.get("clef")
                    if m_clef == carried or m_clef not in _CLEF_ANCHORS:
                        continue
                    if (instrument.name, carried, m_clef) in MID_STAFF_CHANGE_VETOES:
                        delta = clef_diatonic_shift(m_clef, carried)
                        if delta is None:
                            carried = m_clef
                            continue
                        restated += _restate_measure(
                            measure, delta, staff.get("key_signature"),
                            staff_alts)
                        measure["clef"] = carried
                        vetoed.append({"measure_index": m_idx,
                                       "from_clef": carried, "to_clef": m_clef})
                    else:
                        carried = m_clef
                if not vetoed:
                    continue
                # The staff-level "final" clef may now be wrong about the end
                # of the staff; recompute it the way transcribe defines it
                # (present only when the end differs from the staff clef).
                end_clef = measures[-1].get("clef")
                if end_clef == staff.get("clef"):
                    staff.pop("clef_final", None)
                elif staff.get("clef_final") is not None:
                    staff["clef_final"] = end_clef
                record = {
                    "page_index": key[0], "system_index": key[1],
                    "staff_index": key[2], "slot": slot,
                    "instrument": instrument.name,
                    "changes_vetoed": vetoed,
                    "noteheads_restated": restated,
                }
                staff["clef_change_veto"] = record
                records.append(record)
    return records


def correct_clefs_from_instruments(
    pages: list[dict[str, Any]],
    instrument_by_slot: dict[int, Instrument],
    slot_by_staff: dict[tuple[int, int, int], int],
    *,
    apply: bool = True,
    treble_override: bool = False,
    instrument_source_by_slot: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Propose (and optionally apply) clef corrections across built page dicts.

    `slot_by_staff` maps `(page_index, system_index, staff_index)` to slot.
    Returns one record per proposal, whether or not it was applied — a staff
    whose clef the detector actually READ is reported with `applied: False`, so
    a disagreement is surfaced without being acted on.

    `treble_override` (default off — the `OMR_INSTRUMENT_CLEF_DEFAULT` tier)
    additionally applies a proposal on a staff whose clef WAS read, when every
    one of these holds:

    - the clef in effect is **treble, uniformly** across the staff's measures
      (a mid-staff change belongs to `veto_implausible_clef_changes`, and a
      one-delta restatement of a mixed staff would shift the other clef's
      measures too);
    - the instrument was named by a READ margin label
      (`instrument_source_by_slot[slot] == "label"`) — never by score order;
    - the instrument is in `TREBLE_OVERRIDE_INSTRUMENTS`, and the proposal is
      exactly its `default_clef` (which the table guarantees is not treble);
    - the register fit does not worsen (already enforced by `propose_clef`).
    """
    records: list[dict[str, Any]] = []
    sources = instrument_source_by_slot or {}
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
                detected = clef_was_read(staff)
                do_apply = apply and not detected
                overridden = False
                if (apply and detected and not do_apply and treble_override
                        and proposal.from_clef == "treble"
                        and instrument.name in TREBLE_OVERRIDE_INSTRUMENTS
                        and proposal.to_clef == instrument.default_clef
                        and sources.get(slot) == "label"
                        and _measure_clefs_uniform(staff, "treble")):
                    do_apply = True
                    overridden = True
                record = {
                    "page_index": key[0], "system_index": key[1],
                    "staff_index": key[2], "slot": slot,
                    "instrument": proposal.instrument,
                    "from_clef": proposal.from_clef, "to_clef": proposal.to_clef,
                    "fit": proposal.fit, "current_fit": proposal.current_fit,
                    "margin": proposal.margin, "n_noteheads": proposal.n_noteheads,
                    "confidence_label": proposal.confidence_label,
                    "clef_was_read": detected,
                    "clef_source": staff.get("clef_source"),
                    "applied": do_apply,
                }
                if overridden:
                    record["override"] = "treble_misread"
                if do_apply:
                    record["noteheads_restated"] = apply_proposal(
                        staff, proposal,
                        system_staves=(system.get("staves")
                                       if treble_override else None),
                        instrument=(instrument if treble_override else None))
                staff["clef_proposal"] = record
                records.append(record)
    return records
