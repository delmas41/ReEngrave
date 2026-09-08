"""The EVALUATE stage's rules — what a settled fact forces to be restated.

⚠️ EVERY RULE MUST DECLARE ITS `bound`. Every propagation in the existing
tree that works is bounded, and the boundedness is what makes it safe rather
than the direction alone. `_reconcile_measure_to_meter` is the model: re-read
a beam level by +/-1 ONLY, the bar must land EXACTLY on the meter, the answer
must be UNIQUE, single-voice measures only, and it never adds, deletes or
re-pitches a note.

⚠️ AND EVERY RULE IS CHECKED DOWNHILL AT IMPORT. `evaluate.rule` raises
`UphillRule` if `effect` sits at or above `cause` in `DOWNHILL`, so a loop is
a startup failure rather than a run that does not terminate.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import record as R
from .evaluate import Consequence, rule
from .record import ABSTAIN, Kind, Log, Outcome, Q, READERS, Scope, Subject, Verdict


def _verdict(log: Log, subject: Subject, quantity: str, value: Any,
             *, decider: str, reason: str, basis) -> Verdict:
    """Append a consequence as an EVENT.

    ⚠️ Note what is NOT here: no `*_final` field is written anywhere. The
    value-shaped summaries in the existing pipeline went stale precisely
    because each had to be re-maintained by every later writer -- `clef_final`
    9 of 20, `key_signature_final` 19 of 26, and `time_signature_final` with
    no keeper at all. A consequence recorded as an event describes a moment
    and cannot be made wrong by a later one.
    """
    v = Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=quantity,
        outcome=Outcome.DECIDED if value is not None else Outcome.ABSTAINED,
        value=value, decider=decider, reason=reason,
        considered=tuple(basis), basis=tuple(basis))
    return log.record(v)


# ─────────────────────────────────────────────────────────────────────────────
# A clef settles, so pitches restate. THE canonical consequence.
# ─────────────────────────────────────────────────────────────────────────────


@rule(consequence=Consequence.RESTATE_PITCH,
      cause=Q.CLEF, effect=Q.PITCH, scope=Kind.STAFF,
      bound="One pitch per notehead that already has a POSITION row. Adds no "
            "notehead, deletes none, and re-reads no geometry. A staff whose "
            "clef ABSTAINED produces no pitches at all -- it does not fall "
            "back to treble.")
def restate_pitch(log: Log, subject: Subject, clef: Verdict) -> List[Verdict]:
    """position + clef -> pitch. The interpretation, made explicit.

    ⚠️ THIS IS WHERE THE ARCHITECTURE PAYS. In the existing pipeline the
    pitch is computed at the moment the notehead is measured
    (`pitch_resolver.py:180-183`) and the clef-free position is rounded away
    one line later, so a later decision that wants to reconsider the clef has
    nothing clef-free to reconsider it with. Here the POSITION is a gathered
    row that survives, the CLEF is an adjudicated verdict, and the PITCH is
    a consequence with both in its basis.

    ⚠️ A staff whose clef abstained gets NO PITCHES, deliberately. The
    existing behaviour is a positional default that is right about half the
    time and indistinguishable from a reading. Producing nothing is worse for
    a naive metric and better for a reader who needs to know what we do not
    know.
    """
    from ..pitch_resolver import _pitch_from_position

    out: List[Verdict] = []
    rows = log.rows(Q.NOTEHEAD_STAFF_POSITION, subject,
                    scope=Scope.SELF_AND_DESCENDANTS)
    for row in rows:
        pos = int(round(float(row.value)))
        name = _pitch_from_position(pos, str(clef.value))
        if name is None:
            # ⚠️ An unknown clef anchor is an ABSTENTION, not a default. The
            # clef vocabulary here is wider than `_CLEF_ANCHORS` knows.
            continue
        out.append(_verdict(
            log, row.subject, Q.PITCH, name,
            decider="restate_pitch", reason="position_and_clef",
            basis=(row.id, clef.id)))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The rest — declared stubs, present so the stage is complete
# ─────────────────────────────────────────────────────────────────────────────


@rule(consequence=Consequence.RESPELL_ACCIDENTAL,
      cause=Q.KEY_SIGNATURE, effect=Q.ACCIDENTAL, scope=Kind.STAFF,
      bound="Re-spells the LETTER of an existing pitch only. Never changes a "
            "staff position, never adds or removes a note, and never "
            "re-derives the key from the new spelling.",
      stub=True)
def respell_accidental(log, subject, key) -> List[Verdict]:
    """⚠️ DECLARED STUB. `key_signature_corroboration` already does this
    correctly and is the pattern to port: it re-spells the notes AND their
    pitch candidates, and pointedly does NOT re-derive the key from the new
    spelling -- which is what keeps the edge downhill."""
    return []


@rule(consequence=Consequence.RECONCILE_DURATION,
      cause=Q.METER, effect=Q.DURATION, scope=Kind.CELL,
      bound="Re-reads a beam level by +/-1 ONLY. The corrected bar must land "
            "EXACTLY on the meter. The answer must be UNIQUE. Single-voice "
            "measures only. Never adds, deletes or re-pitches a note. "
            "Tuplet notes are EXCLUDED -- the level re-derivation would "
            "silently drop the ratio.")
def reconcile_duration(log: Log, subject: Subject, meter: Verdict) -> List[Verdict]:
    """The meter settles, so a bar that does not fit it is re-read -- ONCE.

    ⚠️ THIS IS THE ONLY LOOP IN THE PIPELINE AND THE BOUND IS WHAT REPLACES A
    FIXPOINT. Durations vote the meter; the meter then re-reads the durations.
    The existing pipeline breaks it by ORDERING -- vote once, repair once --
    and the bound is what stops the repair laundering a guess.

    ⚠️ IT MAY ONLY MOVE THE BEAM LEVEL, and that is not arbitrary: durations
    come from clustering beam y-positions, so one extra or missing cluster
    HALVES OR DOUBLES a note. The beam level is the one input fragile enough
    to be worth arbitrating, and everything else -- how many notes there are,
    what pitch they carry -- is left alone. It cannot paper over a detection
    fault because it cannot add or remove a note.

    ⚠️ AND IT REFUSES WHEN THE ANSWER IS NOT UNIQUE. That is the
    "certain about the GROUP, silent about the MEMBER" rule, implemented: a
    failed bar sum implicates the meter, every duration, a spurious note, a
    missing one and a mis-owned glyph, so where more than one re-reading
    lands the bar exactly on the meter, NOTHING is changed and the warning
    stands. It must never condemn the cheapest member to change.
    """
    value = meter.value or {}
    num, den = value.get("numerator"), value.get("denominator")
    if not num or not den:
        return []
    expected = float(num) * 4.0 / float(den)

    notes = [v for v in log.verdicts(Q.DURATION, subject,
                                     scope=Scope.SELF_AND_DESCENDANTS)
             if v.outcome is Outcome.DECIDED and isinstance(v.value, dict)]
    if not notes:
        return []

    total = sum(float(n.value.get("beats") or 0.0) for n in notes)
    if abs(total - expected) < 1e-6:
        return []                       # the bar already fits

    # ⚠️ Tuplet members are excluded: `beats` there is already scaled by the
    # ratio, and re-deriving a level would silently drop it.
    candidates = [n for n in notes
                  if float(n.value.get("beats") or 0.0)
                  == float(n.value.get("written") or -1.0)]

    landings = []
    for note in candidates:
        for delta in (-1, +1):
            level = int(note.value.get("beam_levels") or 0) + delta
            if level < 0:
                continue
            written = float(note.value.get("written") or 0.0)
            old_level = int(note.value.get("beam_levels") or 0)
            base = written * (2 ** old_level)
            new_beats = base / (2 ** level)
            if abs(total - written + new_beats - expected) < 1e-6:
                landings.append((note, level, new_beats))

    if len(landings) != 1:
        # ⚠️ Zero landings: no single beam level explains the bar, so the
        # fault is elsewhere in the group. More than one: the evidence does
        # not distinguish them. BOTH refuse, and the bar keeps its warning.
        return []

    note, level, new_beats = landings[0]
    out = Verdict(
        id=log._next_id("vrd"), subject=note.subject, quantity=Q.DURATION,
        outcome=Outcome.DECIDED,
        value={**note.value, "beats": new_beats, "written": new_beats,
               "beam_levels": level, "reconciled": True},
        decider="reconcile_duration", reason="meter_reconciliation",
        considered=(note.id, meter.id), basis=(note.id, meter.id),
        supersedes=note.id)
    return [log.record(out)]


@rule(consequence=Consequence.MOVE_GLYPH,
      cause=Q.GLYPH_OWNER, effect=Q.PITCH, scope=Kind.GLYPH,
      bound="Moves a detection from one staff to another. Emits no new "
            "detection and destroys none -- a losing copy is superseded, not "
            "deleted, so the contest stays on the record.",
      stub=True)
def move_glyph(log, subject, owner) -> List[Verdict]:
    """⚠️ DECLARED STUB. Ownership settles, so the glyph's pitch is restated
    against its NEW staff's clef and lines."""
    return []


@rule(consequence=Consequence.NAME_PART,
      cause=Q.INSTRUMENT, effect=Q.PART_NAME, scope=Kind.STAFF,
      bound="Writes a name onto a part. Changes no note, no clef and no "
            "structure -- musicdiff does not score <part-name> at all, so "
            "this consequence is invisible to the metric and must be checked "
            "by the label-contradiction audit instead.",
      stub=True)
def name_part(log, subject, instrument) -> List[Verdict]:
    """⚠️ DECLARED STUB. And a warning attached to it: a name is stamped per
    SLOT and written onto every staff of that slot on every page, so ONE
    wrong slot assignment renames a part across a whole document -- 93 `Tp.`
    staves exported as Trumpet on one Beethoven run. The check that catches
    it needs no truth file: a staff whose OWN margin label was read on THAT
    page, exported under a different name."""
    return []


@rule(consequence=Consequence.JOIN_PARTS,
      cause=Q.PART_PARTITION, effect=Q.PART_NAME, scope=Kind.DOCUMENT,
      bound="Joins staves into parts. Emits no music and moves no note "
            "between staves; it decides only which staves are the same part.",
      stub=True)
def join_parts(log, subject, partition) -> List[Verdict]:
    """⚠️ DECLARED STUB."""
    return []
