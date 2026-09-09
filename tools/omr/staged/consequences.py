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

from collections import Counter
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


def _standing(log: Log, subject: Subject, quantity: str) -> List[Verdict]:
    """The verdicts of `quantity` under `subject` that a LATER one has not
    superseded.

    ⚠️ `Log.verdicts` returns every ROW; `Log.verdict` resolves `supersedes`
    but answers for ONE subject. A rule that walks a cell's descendants needs
    both, and using the plural alone DOUBLE-COUNTS anything an earlier
    consequence restated. That could not happen while `reconcile_duration`
    was the only writer of `Q.DURATION` in EVALUATE; `size_measure_rest` makes
    it two, so the resolution is written once here rather than twice badly.
    """
    rows = log.verdicts(quantity, subject, scope=Scope.SELF_AND_DESCENDANTS)
    superseded = {v.supersedes for v in rows if v.supersedes}
    return [v for v in rows if v.id not in superseded]


def _is_rest(v: Verdict) -> bool:
    return bool(isinstance(v.value, dict) and v.value.get("is_rest"))


@rule(consequence=Consequence.SIZE_MEASURE_REST,
      cause=Q.METER, effect=Q.DURATION, scope=Kind.CELL,
      bound="Fires only on a bar whose ONLY standing duration is ONE rest, "
            "whose glyph is `restWhole`, with no dots, and only where the "
            "meter is DECIDED. Rewrites that one duration to the bar's "
            "length and marks it. Adds no event, deletes none, and touches "
            "no bar holding anything else.")
def size_measure_rest(log: Log, subject: Subject, meter: Verdict) -> List[Verdict]:
    """A whole-rest glyph means the BAR, not four quarters of silence.

    ⚠️ THE CONVENTION IS THE OTHER WAY ROUND FROM THE ARITHMETIC. An engraver
    fills an otherwise silent bar with ONE centred whole-rest glyph whatever
    the meter, and the glyph stands for the bar -- so its duration is the
    BAR's length and MusicXML says so with `<rest measure="yes"/>` and NO
    `<type>` at all. Measured over the seven scan-gate rows whose part join
    resolves: **558 of 618 wrong rest durations -- 90.3% -- are exactly this
    bar**, 543 of them a `whole`/4.0 against a truth of 2.0.

    ⚠️ THE GLYPH IS PART OF THE RULE, and leaving it out cost 34 edits on
    `brahms-sym4-mvt1`. The first cut of the legacy fix accepted ANY lone rest
    and inflated bars holding a single detected QUARTER rest into full bars.
    Those bars are not silent -- they are bars we read one symbol of.

    ⚠️ IT FIRES EVEN WHEN THE NUMBER DOES NOT MOVE, and that is deliberate: in
    4/4 the bar length IS 4.0, so nothing changes arithmetically and the
    MARKING still has to be made. `measure_rest` is what tells the exporter to
    write `measure="yes"` and omit `<type>`; without it a correct 4.0 is
    exported as an ordinary whole rest, which is a different claim about the
    engraving.

    ⚠️ AND IT IS A CONSEQUENCE RATHER THAN PART OF THE DURATION DECISION
    BECAUSE ITS EVIDENCE IS NOT THE GLYPH'S. It needs the CELL's other
    contents and the SETTLED meter, neither of which `adjudicate_duration`
    has when it reads one rest. Putting it here is what lets the bound be
    stated and the meter be known.
    """
    value = meter.value or {}
    num, den = value.get("numerator"), value.get("denominator")
    if not num or not den:
        # ⚠️ NO METER, NO ASSERTION. Sizing a bar we never read the meter of
        # would be a guess dressed as a fact, and the legacy exporter withholds
        # `measure="yes"` for the same reason.
        return []

    standing = _standing(log, subject, Q.DURATION)
    if len(standing) != 1:
        return []
    only = standing[0]
    if only.outcome is not Outcome.DECIDED or not _is_rest(only):
        return []
    if only.detail.get("rest") != "restWhole" or only.value.get("dots"):
        return []

    beats = float(num) * 4.0 / float(den)
    out = Verdict(
        id=log._next_id("vrd"), subject=only.subject, quantity=Q.DURATION,
        outcome=Outcome.DECIDED,
        value={**only.value, "beats": beats, "written": beats,
               "measure_rest": True},
        decider="size_measure_rest", reason="whole_rest_means_the_bar",
        considered=(only.id, meter.id), basis=(only.id, meter.id),
        detail={**only.detail, "bar_beats": beats},
        supersedes=only.id)
    return [log.record(out)]


def _event_totals(log: Log, subject: Subject, notes, current) -> Optional[float]:
    """The bar's length, counting each EVENT once, or None if unknowable.

    One event contributes ONE duration. Where a chord's members disagree about
    their value the MODE is taken -- which is `voicing.group_chords_in_measure`'s
    own definition of an event's duration, so the record and the exporter
    answer this question the same way.
    """
    grouping = log.verdict(Q.EVENT, subject)
    if grouping is None or grouping.outcome is not Outcome.DECIDED:
        return None
    by_glyph = {v.subject.glyph: v for v in notes}
    total = 0.0
    seen = set()
    for event in (grouping.value or {}).get("events", ()):
        members = [by_glyph[g] for g in event.get("glyphs", ())
                   if g in by_glyph]
        if not members:
            continue
        beats = Counter(float(current[m.id].get("beats") or 0.0)
                        for m in members)
        total += beats.most_common(1)[0][0]
        seen.update(m.id for m in members)
    # ⚠️ A duration the grouping does not mention is still time in the bar.
    # Dropping it would understate the total as silently as the double-count
    # overstated it.
    for v in notes:
        if v.id not in seen:
            total += float(current[v.id].get("beats") or 0.0)
    return total


@rule(consequence=Consequence.RECONCILE_DURATION,
      cause=Q.METER, effect=Q.DURATION, scope=Kind.CELL,
      bound="Searches only the levels a note ADMITS -- its own narrowed "
            "candidates, or +/-1 for a note that decided. Changes at most ONE "
            "note. The corrected bar must land EXACTLY on the meter. The "
            "answer must be UNIQUE. Never adds, deletes or re-pitches a note. "
            "Tuplet members are excluded -- re-deriving a level would "
            "silently drop the ratio.")
def reconcile_duration(log: Log, subject: Subject, meter: Verdict) -> List[Verdict]:
    """The meter settles, so a bar that does not fit it is re-read -- ONCE.

    ⚠️ THIS IS THE ONLY LOOP IN THE PIPELINE AND THE BOUND REPLACES A FIXPOINT.
    Durations vote the meter; the meter then re-reads the durations. The
    existing pipeline breaks it by ORDERING -- vote once, repair once -- and
    the bound stops the repair laundering a guess.

    ⚠️⚠️ SINCE CANDIDATE SETS IT SEARCHES WHAT THE NOTE ADMITS, NOT ARITHMETIC.
    A NARROWED duration already says *"two levels, possibly three"*, so the
    meter is choosing among readings the beams actually support rather than
    among numbers one step away. That is a strictly better bound: a +/-1 that
    the strokes do not support is no longer reachable, and the uniqueness test
    now runs over REAL alternatives.

    ⚠️ AND IT STILL REFUSES WHEN THE ANSWER IS NOT UNIQUE. That is
    "certain about the GROUP, silent about the MEMBER" implemented: a failed
    bar sum implicates the meter, every duration, a spurious note, a missing
    one and a mis-owned glyph, so where more than one re-reading lands the bar
    exactly, NOTHING changes and the warning stands. It must never condemn the
    cheapest member.
    """
    value = meter.value or {}
    num, den = value.get("numerator"), value.get("denominator")
    if not num or not den:
        return []
    expected = float(num) * 4.0 / float(den)

    notes = [v for v in _standing(log, subject, Q.DURATION)
             if v.outcome in (Outcome.DECIDED, Outcome.NARROWED)]
    if not notes:
        return []

    # A narrowed note contributes its BEST-SUPPORTED reading to the running
    # total -- the same reading the exporter would take today.
    def _current(v: Verdict):
        if v.outcome is Outcome.DECIDED:
            return v.value
        return v.candidates[0].value if v.candidates else None

    current = {v.id: _current(v) for v in notes}
    if any(c is None for c in current.values()):
        return []

    # ⚠️ A BAR IS SUMMED OVER EVENTS, NOT OVER NOTEHEADS. A chord's members
    # sound together and advance time ONCE, so summing each of them was a
    # double-count -- and it was silent, because an inflated total simply
    # never equals the meter and this rule then does nothing. Measured on
    # Beethoven 5 / Litolff p.17: 38.2% of bars hold a chord, and ungrouped
    # the bars landing exactly on the printed meter fell 18 -> 13. The
    # inflation is not a constant to subtract either: 13 distinct values from
    # 0.125 to 6.0 quarter-lengths.
    #
    # ⚠️ NO EVENT VERDICT MEANS NO REPAIR, rather than a fall back to the old
    # per-notehead sum. A bar whose grouping is unknown is a bar whose sum is
    # unknown, and repairing against a total that may be inflated is exactly
    # the laundered guess `bound` exists to prevent.
    grouped = _event_totals(log, subject, notes, current)
    if grouped is None:
        return []
    total = grouped
    if abs(total - expected) < 1e-6:
        return []                       # the bar already fits

    landings = []
    for note in notes:
        # ⚠️ A REST IS NOT RE-READ HERE, and the case is concrete rather than
        # tidy. `_admitted` offers a DECIDED event its own level +/-1, so a
        # lone 4.0 whole rest in a 2/4 bar would "land exactly" at 2.0 and be
        # UNIQUE -- the right number by the wrong reasoning, reported as a
        # HALF rest with `<type>half</type>` where the engraving prints a
        # measure rest with no type at all. A rest carries no beam to re-read;
        # the bar-length convention is `size_measure_rest`'s, and it has
        # already run.
        if _is_rest(note):
            continue
        now = current[note.id]
        # ⚠️ A tuplet member's `beats` is already scaled by the ratio, so
        # re-deriving a level would silently drop it.
        if float(now.get("beats") or 0.0) != float(now.get("written") or -1.0):
            continue
        for option in _admitted(note):
            if option.get("beam_levels") == now.get("beam_levels"):
                continue
            moved = total - float(now.get("beats") or 0.0) \
                + float(option.get("beats") or 0.0)
            if abs(moved - expected) < 1e-6:
                landings.append((note, option))

    if len(landings) != 1:
        # ⚠️ Zero: no admitted reading of any single note explains the bar, so
        # the fault is elsewhere in the group. More than one: the evidence does
        # not distinguish them. BOTH refuse, and the bar keeps its warning.
        return []

    note, option = landings[0]
    out = Verdict(
        id=log._next_id("vrd"), subject=note.subject, quantity=Q.DURATION,
        outcome=Outcome.DECIDED,
        value={**option, "reconciled": True},
        decider="reconcile_duration", reason="meter_reconciliation",
        considered=(note.id, meter.id), basis=(note.id, meter.id),
        supersedes=note.id)
    return [log.record(out)]


def _admitted(note: Verdict) -> List[dict]:
    """The readings this note allows.

    ⚠️ A NARROWED note offers exactly its candidates -- readings the BEAMS
    support. A DECIDED note keeps the old arithmetic +/-1, because a note whose
    strokes were unambiguous can still have had a stroke missed entirely, and
    that is the case the original bound was built for.
    """
    if note.outcome is Outcome.NARROWED:
        return [c.value for c in note.candidates if isinstance(c.value, dict)]
    out = []
    written = float(note.value.get("written") or 0.0)
    old = int(note.value.get("beam_levels") or 0)
    base = written * (2 ** old)
    for level in (old - 1, old + 1):
        if level < 0:
            continue
        beats = base / (2 ** level)
        out.append({**note.value, "beats": beats, "written": beats,
                    "beam_levels": level})
    return out


@rule(consequence=Consequence.MOVE_GLYPH,
      cause=Q.GLYPH_OWNER, effect=Q.PITCH, scope=Kind.GLYPH,
      bound="Restates one glyph's pitch against the staff that won it. Emits "
            "no detection and destroys none -- a losing copy is SUPERSEDED, "
            "not deleted, so the contest stays on the record.")
def move_glyph(log: Log, subject: Subject, owner: Verdict) -> List[Verdict]:
    """Ownership settles, so the glyph's pitch is restated on its NEW staff.

    ⚠️ THE LOSING COPY IS SUPERSEDED, NOT DELETED. A contest resolved by
    deleting the loser leaves nothing to re-examine when the identity that
    decided it turns out to be wrong -- and identity is exactly the evidence
    this arbitration was starved of until the split. `supersedes` keeps both.
    """
    if not isinstance(owner.value, str):
        return []
    winner = Subject.from_key(owner.value)
    if winner.to_key() == subject.at(Kind.STAFF).to_key():
        return []                       # it stayed where it was cut

    clef = log.verdict(Q.CLEF, winner)
    if clef is None or clef.value is None:
        # ⚠️ No clef on the winning staff means no pitch, exactly as
        # `restate_pitch` refuses. A moved glyph must not acquire a pitch the
        # staff it moved to could not have given it.
        return []

    band = [r for r in log.rows(Q.GLYPH_BAND_DISTANCE, subject)
            if r.detail.get("candidate") == owner.value]
    if not band:
        return []
    pos = band[0].detail.get("position_in_candidate")
    if pos is None:
        return []

    from ..pitch_resolver import _pitch_from_position
    name = _pitch_from_position(int(round(float(pos))), str(clef.value))
    if name is None:
        return []

    prior = log.verdict(Q.PITCH, subject)
    out = Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=Q.PITCH,
        outcome=Outcome.DECIDED, value=name, decider="move_glyph",
        reason="reowned", considered=(owner.id, clef.id, band[0].id),
        basis=(owner.id, clef.id, band[0].id),
        supersedes=prior.id if prior is not None else None)
    return [log.record(out)]


@rule(consequence=Consequence.RESPELL_ACCIDENTAL,
      cause=Q.KEY_SIGNATURE, effect=Q.ACCIDENTAL, scope=Kind.STAFF,
      bound="Re-spells the LETTER of an existing pitch only. Never changes a "
            "staff position, never adds or removes a note, and NEVER "
            "re-derives the key from the new spelling -- which is what keeps "
            "the edge downhill.")
def respell_accidental(log: Log, subject: Subject, key: Verdict) -> List[Verdict]:
    """The key settles, so the notes on this staff carry its alterations.

    ⚠️ IT MUST NEVER RE-DERIVE THE KEY FROM THE NEW SPELLING. That is the one
    move that would turn this edge uphill, and `key_signature_corroboration`
    -- the pattern this ports -- pointedly does not make it: it re-spells the
    notes AND their candidates, and reads the restored key back rather than
    recomputing it.

    ⚠️ SCOPE, AND SEAN STATES BOTH IN ONE SENTENCE: *"a key signature applies
    to all of the notes after until there is another accidental, which will
    affect all the same notes in that bar only."* The signature is
    part-scoped and until-revoked; an inline accidental is bar-scoped AND
    pitch-scoped and OVERRIDES it. This rule may only supply the DEFAULT --
    a note carrying its own accidental is left alone.
    """
    fifths = key.value if isinstance(key.value, int) else None
    if not fifths:
        return []                       # C major alters nothing

    sharps = ("F", "C", "G", "D", "A", "E", "B")
    altered = set(sharps[:fifths] if fifths > 0
                  else list(reversed(sharps))[:abs(fifths)])
    accidental = "#" if fifths > 0 else "b"

    out: List[Verdict] = []
    for pitch in log.verdicts(Q.PITCH, subject,
                              scope=Scope.SELF_AND_DESCENDANTS):
        if pitch.outcome is not Outcome.DECIDED or not isinstance(pitch.value, str):
            continue
        letter = pitch.value[0]
        if letter not in altered:
            continue
        # ⚠️ An inline accidental OVERRIDES the signature, so a note that
        # already carries one is not touched.
        if log.verdict(Q.ACCIDENTAL, pitch.subject) is not None:
            continue
        out.append(_verdict(
            log, pitch.subject, Q.ACCIDENTAL, accidental,
            decider="respell_accidental", reason="from_key_signature",
            basis=(pitch.id, key.id)))
    return out


@rule(consequence=Consequence.NAME_PART,
      cause=Q.INSTRUMENT, effect=Q.PART_NAME, scope=Kind.STAFF,
      bound="Writes a name onto a staff. Changes no note, no clef and no "
            "structure.")
def name_part(log: Log, subject: Subject, instrument: Verdict) -> List[Verdict]:
    """The instrument settles, so the part gets its name.

    ⚠️ INVISIBLE TO EVERY STANDING MEASUREMENT -- musicdiff does not score
    `<part-name>` at all -- so this consequence cannot be checked by the
    metric and must be checked by the label-contradiction audit instead: a
    staff whose OWN margin label was read on THIS page, exported under a
    different name. Adjudicated over 158 firings, 0.873 the EXPORT is wrong.

    ⚠️ AND ONE WRONG SLOT RENAMES A PART ACROSS A WHOLE DOCUMENT, because a
    name is stamped per SLOT and written onto every staff of that slot on
    every page -- 93 `Tp.` staves once exported as Trumpet on one Beethoven
    run. That is why the name's `basis` carries the slot: the blast radius is
    traceable rather than merely large.
    """
    if not isinstance(instrument.value, dict):
        return []
    name = instrument.value.get("name")
    if not name:
        return []
    slot = log.verdict(Q.SLOT_INDEX, subject)
    basis = (instrument.id,) + ((slot.id,) if slot is not None else ())
    return [_verdict(log, subject, Q.PART_NAME, name,
                     decider="name_part", reason="from_instrument",
                     basis=basis)]


@rule(consequence=Consequence.JOIN_PARTS,
      cause=Q.PART_PARTITION, effect=Q.PART_NAME, scope=Kind.DOCUMENT,
      bound="Decides which staves are the same part. Emits no music and moves "
            "no note between staves.",
      stub=True)
def join_parts(log, subject, partition) -> List[Verdict]:
    """⚠️ DECLARED STUB, and deliberately the last one.

    It is the consequence of the decision a pre-registered gate already
    falsified once: where the ordinal join REFUSES, the slot join succeeded
    and was wrong on 3 of 27 staves, grafting a horn's continuation onto a
    genuinely-tacet trumpet's slot. `adjudicate_part_partition` abstains there
    rather than joining, so there is nothing for this rule to carry -- and
    wiring it before that abstention is priced would be building on the one
    result we know to be wrong.
    """
    return []
