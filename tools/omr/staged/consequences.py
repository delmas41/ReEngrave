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
from typing import Any, Dict, List, Optional, Tuple

from . import record as R
from .evaluate import Consequence, rule
from .record import (ABSTAIN, Kind, Log, Outcome, Q, READERS, Scope, Subject,
                     Verdict, meter_at)


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
      bound="One pitch per notehead that already has a POSITION row and does "
            "NOT already carry a pitch. Adds no notehead, deletes none, and "
            "re-reads no geometry. A staff whose clef ABSTAINED produces no "
            "pitches at all -- it does not fall back to treble.")
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
        if log.verdict(Q.PITCH, row.subject) is not None:
            # ⚠️⚠️ IT NEVER OVERTURNS A PITCH THAT ALREADY STANDS, and the
            # guard is a PROVABLE NO-OP ON THE FIRST PASS: this rule is the
            # first writer of `Q.PITCH` in DOWNHILL order, and on the Litolff
            # whole-movement record the only two deciders of the quantity are
            # this one (10,618) and `move_glyph` (2,686), which runs after.
            #
            # It exists for the BOUNDED SECOND PASS (roadmap 2.10). A glyph
            # cut in this staff's cells but awarded to a NEIGHBOUR was
            # re-pitched by `move_glyph` in the first pass, on the winner's
            # clef. When INFER later fills THIS staff's clef, `run_over`
            # brings this rule back over the staff's position rows -- which
            # still include that glyph, because a contest DROPS the loser
            # rather than removing the row. Without this guard the rule
            # re-pitches a note that left, on the clef of the staff it left,
            # and `Log.record` refuses it outright (`AlreadyAdjudicated`),
            # which is how this was found: the whole arm died on
            # `glyph/2/1/9/6/2`.
            continue
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
    """⚠️ A NARROWED verdict has no `value`; its candidates say what it is
    (2.22: without this a narrowed REST read as "not a rest", and the
    re-reading loop that now offers every candidate of a narrowed note would
    have re-read a rest -- the control test caught it)."""
    if isinstance(v.value, dict):
        return bool(v.value.get("is_rest"))
    return any(isinstance(c.value, dict) and c.value.get("is_rest")
               for c in (v.candidates or ()))


@rule(consequence=Consequence.SIZE_MEASURE_REST,
      cause=Q.METER, effect=Q.DURATION, scope=Kind.CELL,
      reads_beyond_cause=lambda log, subject, meter:
          _size_measure_rest_also_reads(log, subject, meter),
      bound="Fires only on a bar whose ONLY standing duration still IN the "
            "bar (not taken out by a DECIDED not-a-notehead, not-a-rest or "
            "another-staff verdict) is ONE rest, whose glyph is `restWhole`, "
            "with no dots, and only where the meter is DECIDED. Rewrites "
            "that one duration to the bar's length and marks it. Adds no "
            "event, deletes none, and touches no bar holding anything else.")
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

    # ⚠️⚠️ ROADMAP 2.19: "ANYTHING ELSE" MEANS ANYTHING STILL IN THE BAR.
    # `_standing` returns a duration for every glyph box the cell was cut
    # with, including boxes a DECIDED verdict has already taken OUT of the bar
    # -- a notehead box refused by the width floor, a second box on the very
    # rest being sized (2.15), a head the contest gave to the next staff.
    # EXPORT writes none of those, so the bar holds ONE whole rest; counting
    # them here left it unmarked, 2.8 summed it as four quarters and held it
    # out. Breitkopf p1: every whole-rest bar of system 0 (FINDINGS §15).
    # Only a DECIDED removal counts: an abstained refusal, a narrowed head or
    # an abstained rest is still something we could not rule out (rule 8).
    set_aside, cleared_by = [], []
    kept = []
    for v in _standing(log, subject, Q.DURATION):
        why = _left_the_bar(log, v.subject)
        if why is None:
            kept.append(v)
        else:
            set_aside.append(v.subject.to_key())
            cleared_by.append(why.id)
    if len(kept) != 1:
        return []
    only = kept[0]
    if only.outcome is not Outcome.DECIDED or not _is_rest(only):
        return []
    if only.detail.get("rest") != "restWhole" or only.value.get("dots"):
        return []

    beats = float(num) * 4.0 / float(den)
    detail = {**only.detail, "bar_beats": beats}
    if set_aside:
        detail["set_aside"] = set_aside
    out = Verdict(
        id=log._next_id("vrd"), subject=only.subject, quantity=Q.DURATION,
        outcome=Outcome.DECIDED,
        value={**only.value, "beats": beats, "written": beats,
               "measure_rest": True},
        decider="size_measure_rest", reason="whole_rest_means_the_bar",
        considered=(only.id, meter.id, *cleared_by),
        basis=(only.id, meter.id, *cleared_by),
        detail=detail,
        supersedes=only.id)
    return [log.record(out)]


#: The DECIDED verdicts that take a glyph box out of its bar, each exactly as
#: `export._place_notes` honours it: the box is not a notehead, the box is not
#: a rest (2.15's duplicate among them), or the ink belongs to another staff.
_LEAVES_THE_BAR = (Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST)


def _left_the_bar(log: Log, glyph: Subject) -> Optional[Verdict]:
    """The DECIDED verdict that took this glyph out of its bar, else None."""
    for q in _LEAVES_THE_BAR:
        v = log.verdict(q, glyph)
        if v is not None and v.outcome is Outcome.DECIDED and v.value is True:
            return v
    owner = log.verdict(Q.GLYPH_OWNER, glyph)
    if owner is not None and owner.outcome is Outcome.DECIDED:
        # ⚠️ IMPORTED, NOT RESTATED: the one test EXPORT applies to drop a
        # contest's losing copy (`owned_by_another_staff`).
        from .adjudicate import is_relocated_copy
        if is_relocated_copy(glyph, owner.value):
            return owner
    return None


def _size_measure_rest_also_reads(log: Log, subject: Subject,
                                  meter: Verdict) -> List[str]:
    """The removals `size_measure_rest` reads besides its cause (2.19),
    declared for `evaluate.run_over`: a bar INFER or a later pass clears of
    its last stray box has a new consequence and an unchanged meter."""
    out: List[str] = []
    for v in _standing(log, subject, Q.DURATION):
        for q in (*_LEAVES_THE_BAR, Q.GLYPH_OWNER):
            got = log.verdict(q, v.subject)
            if got is not None:
                out.append(got.id)
    return out


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
            "silently drop the ratio. Sums only what is still IN the bar "
            "(a DECIDED not-a-notehead, not-a-rest or another-staff verdict "
            "sets a box aside), and a narrowed note's every candidate is a "
            "re-reading.",
      # ⚠️ 2.22: the removals it reads besides its cause, declared exactly as
      # `size_measure_rest` declares the same ones (the same helper).
      reads_beyond_cause=lambda log, subject, meter:
          _size_measure_rest_also_reads(log, subject, meter),
      # ⚠️⚠️ THE PIPELINE'S ONE SANCTIONED LOOP, DECLARED. Since the meter
      # carry is corroborated by the bars, the meter now DEPENDS ON the very
      # durations this rule revises -- and the fixpoint guard refuses that by
      # default, correctly, because it cannot see that the loop terminates.
      # This one does: `duration_v1 -> meter -> duration_v2` is a straight
      # line unrolled, run once and stopped, which is the rule `transcribe`
      # has always stated as "vote once, repair once". The BOUND above is what
      # makes it safe -- at most one note, an exact landing, a unique answer,
      # so it cannot iterate even in principle. Sean's call, 2026-09-09, after
      # the guard escalated it exactly as its message says to.
      single_pass=True)
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

    # ⚠️⚠️ ROADMAP 2.22: "THE BAR" MEANS WHAT IS STILL IN IT -- 2.19's fault,
    # found again in the second EVALUATE rule that sums a cell. `_standing`
    # returns a duration for every box the cell was cut with, including boxes
    # a DECIDED verdict already took OUT of the bar (not a notehead, not a
    # rest, a contest's losing copy). EXPORT writes none of them, so summing
    # them measured a bar nobody will write: on Litolff 1/i (whole movement)
    # 48 held bars had exactly one landing once they were set aside, and
    # none before. `_left_the_bar` is `size_measure_rest`'s own helper, and
    # only a DECIDED removal counts (rule 8).
    notes, set_aside, cleared_by = [], [], []
    for v in _standing(log, subject, Q.DURATION):
        if v.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
            continue
        why = _left_the_bar(log, v.subject)
        if why is None:
            notes.append(v)
        else:
            set_aside.append(v.subject.to_key())
            cleared_by.append(why.id)
    if not notes:
        return []

    # A narrowed note contributes its BEST-SUPPORTED reading to the running
    # total. ⚠️ That is NOT what the exporter does with it (2.22): EXPORT
    # refuses to argmax a narrowing (`duration_narrowed`), so a bar that
    # "already fits" only through a narrowed note's best candidate is a bar
    # EXPORT writes without that note and then holds out. See the landing
    # loop below.
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
    fits = abs(total - expected) < 1e-6
    if fits and not any(n.outcome is Outcome.NARROWED and not _is_rest(n)
                        for n in notes):
        return []                       # the bar already fits, all DECIDED

    # ⚠️⚠️ ROADMAP 2.22: A NARROWED NOTE HAS NO READING OF ITS OWN, SO EVERY
    # CANDIDATE IS A RE-READING -- INCLUDING THE ONE THE TOTAL USED. The old
    # loop skipped the candidate sharing the current `beam_levels`, which is
    # right for a DECIDED note (its own reading is not a repair) and wrong
    # for a narrowed one: where the bar fits ONLY through that candidate, the
    # meter has already chosen it, and the rule returned "already fits" and
    # left the note NARROWED -- which EXPORT then refused, holding the bar
    # (Litolff 1/i: 36 held bars whose only unwritten head is one narrowed
    # note the meter settles). The bound is unchanged: one note, an exact
    # landing, a UNIQUE answer -- two narrowed notes that both fit at their
    # best candidate are two landings and the rule refuses.
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
            if note.outcome is Outcome.DECIDED \
                    and option.get("beam_levels") == now.get("beam_levels"):
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
    detail = {}
    if set_aside:
        detail["set_aside"] = set_aside
    if fits:
        detail["bar_fit_only_through_this_narrowing"] = True
    out = Verdict(
        id=log._next_id("vrd"), subject=note.subject, quantity=Q.DURATION,
        outcome=Outcome.DECIDED,
        value={**option, "reconciled": True},
        decider="reconcile_duration", reason="meter_reconciliation",
        considered=(note.id, meter.id, *cleared_by),
        basis=(note.id, meter.id, *cleared_by),
        detail=detail,
        supersedes=note.id,
        # ⚠️ MUST MATCH THIS RULE'S OWN `single_pass=` DECLARATION, and
        # `test_the_single_pass_flag_matches_its_rule` asserts that it does --
        # a verdict claiming the exemption its rule does not declare would be
        # the guard disabled by a typo.
        single_pass_revision=True)
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


# ─────────────────────────────────────────────────────────────────────────────
# REST BEAT-SLOT -- ROADMAP 2.35. Sean, 2026-09-29 (`docs/DECISIONS.md`,
# quoted in full at ROADMAP 2.33 / `benchmarks/omr-bar-sum-holdout-2026-09/
# FINDINGS.md` §20d): *"based upon the other notes in a measure there will be
# a limited space geometrically where the rest can be."* A half-or-smaller
# rest occupies the horizontal GAP between its voice's neighbouring events, at
# the onset its own preceding durations imply within that voice.
#
# ⚠️⚠️ WHY EVALUATE AND NOT `adjudicate_rest_is_not_a_rest`. The three
# quantities this needs -- `Q.EVENT` (which glyphs sound together), `Q.VOICES`
# (which voice this glyph is in) and `Q.DURATION` (the neighbours' onsets) --
# are all decided AFTER `Q.REST_IS_NOT_A_REST` in `adjudicate.ORDER`
# (`family_precision.py`'s own module docstring states the same fact for
# EVERY refusal in that file). A question that needs a NOT-YET-DECIDED fact
# cannot honestly be asked in ADJUDICATE; EVALUATE exists precisely for a
# consequence of a fact that settles LATER, so this is `size_measure_rest`'s
# shape (cause=meter, a CELL-scoped fact) applied to a GLYPH-scoped effect
# that happens to revise an ADJUDICATE verdict -- the same shape
# `apply_printed_accidental` already uses to supersede `Q.ACCIDENTAL`.
#
# ⚠️ TWO FORCED SUB-RULES, NOT THE FULL DESIGN. §20d's design also covers a
# conductor's page lining up against `Q.ONSET_COLUMN` (cross-staff, already
# gathered and voted) and an INFER-shaped "best explanation" choice between
# competing readings -- CLAUDE.md §4a: EVALUATE goes silent where the answer
# is merely BEST, never where it must choose between two that both fit, and
# `Q.ONSET_COLUMN`/an argmax over candidates is exactly that choice. What
# FOLLOWS without choosing, from `Q.EVENT`/`Q.VOICES`/`Q.DURATION` alone:
#
#   (A) this glyph's own ink cannot occupy a horizontal span another event of
#       the SAME VOICE already occupies -- no gap exists there, so the "rest"
#       reading is contradicted by the print itself, not by a preference
#       between readings (`rest_shares_a_beat_slot`).
#   (B) the events of this voice strictly BEFORE this rest (by print
#       position) already sum, in DECIDED beats, to the bar's own METER --
#       so by the time this rest is reached there is no time left in the bar
#       for it to occupy, which is what "the onset order its events imply"
#       forces once every input is DECIDED (`rest_after_the_bar_ends`).
#
# ⚠️ SCOPE: SINGLE-VOICE BARS ONLY, AND THAT IS A LINE DRAWN, NOT A GAP LEFT
# OPEN. A multi-voice bar's rest placement is ROADMAP 2.27c's own convention
# (`_rest_voice_side` in `adjudicators/rhythm.py`, ADJUDICATE-side, decided
# WITHIN `Q.VOICES` itself) -- a displaced voice-2 rest legitimately sits
# beside a voice-1 note, which is exactly the shape (A) must not condemn, and
# re-adjudicating which VOICE a rest belongs to is not this item's brief.
# `_rest_beat_slot_context` returns `None` -- no verdict, the rest stands --
# wherever `Q.VOICES` decided more than one stream, rather than trying to
# pick the "right" voice's neighbours to check against.
#
# ⚠️ CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: excluding
# `restDoubleWhole`/`restHNr`/`restHBar` alongside `restWhole` (ROADMAP 2.33's
# own scope) is READ OFF Sean's words -- "a whole rest = the bar, centred" --
# rather than separately measured: these three mean "the whole bar" in a
# longer or shorter meter exactly as `restWhole` does, so a bar holding one of
# them beside OTHER notes of the same voice is not a case this project has
# seen. Falsified by a print crop showing one of the three sharing a bar with
# other same-voice notes, which is the one case this scoping would wrongly
# admit to the beat-slot check instead of leaving it to a `size_measure_rest`
# -style rule.
# ─────────────────────────────────────────────────────────────────────────────

#: See the CONVENTION ASSUMED note above.
REST_BEAT_SLOT_WHOLE_LIKE_CLASSES = frozenset((
    "restWhole", "restDoubleWhole", "restHNr", "restHBar",
))

#: The same float slack `reconcile_duration` uses for "landed exactly".
REST_BEAT_SLOT_EPSILON_QUARTERS = 1e-6


def _rest_beat_slot_box(log: Log, subject: Subject) -> Optional[Tuple[float, float]]:
    """This glyph's own `Q.GLYPH_BOX` as `(x0, x1)` in its cell's canonical
    frame, or `None` -- the same shape `family_precision._glyph_box_row`
    reads, duplicated rather than imported across an ADJUDICATE/EVALUATE
    module boundary for the same reason `_cell_box_page_px` already is there.
    """
    rows = log.rows(Q.GLYPH_BOX, subject)
    if not rows:
        return None
    v = rows[-1].value
    if not isinstance(v, (list, tuple)) or len(v) != 5:
        return None
    try:
        x0 = float(v[1])
        return x0, x0 + float(v[3])
    except (TypeError, ValueError):
        return None


def _rest_beat_slot_event_extent(log: Log, cell: Subject, glyphs
                                 ) -> Optional[Tuple[float, float]]:
    """The union `(x0, x1)` of every named glyph's own box, in `cell` -- a
    chord's own horizontal footprint, or a rest's. `None` where none of the
    named glyphs has a box (rule 8: no measurement, no verdict)."""
    x0s: List[float] = []
    x1s: List[float] = []
    for g in glyphs:
        sub = Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                      staff=cell.staff, cell=cell.cell, glyph=g)
        box = _rest_beat_slot_box(log, sub)
        if box is None:
            continue
        x0s.append(box[0])
        x1s.append(box[1])
    if not x0s:
        return None
    return min(x0s), max(x1s)


def _rest_beat_slot_context(log: Log, subject: Subject) -> Optional[dict]:
    """Every fact `rest_beat_slot` needs, gathered ONCE -- shared with its own
    `reads_beyond_cause` declaration so the two can never disagree about what
    was read (the same discipline `_size_measure_rest_also_reads` follows
    with `_standing`/`_left_the_bar`).

    `None` wherever the connection cannot run at all: not a rest, a
    whole-bar-filling class, already refused (or not yet DECIDED-false),
    outside a single-voice bar, or `Q.EVENT` has not grouped this cell --
    CLAUDE.md rule 8, silence rather than a guess.
    """
    if subject.glyph is None:
        return None
    if not log.rows(Q.REST, subject):
        return None
    box_rows = log.rows(Q.GLYPH_BOX, subject)
    if not box_rows or not isinstance(box_rows[-1].value, (list, tuple)) \
            or len(box_rows[-1].value) != 5:
        return None
    cls = str(box_rows[-1].value[0])
    if cls in REST_BEAT_SLOT_WHOLE_LIKE_CLASSES:
        return None

    cur = log.verdict(Q.REST_IS_NOT_A_REST, subject)
    if cur is None or cur.outcome is not Outcome.DECIDED or cur.value is not False:
        # ⚠️ NEVER RE-DECIDES ONE ALREADY REFUSED, and never touches one whose
        # own verdict has not settled -- there is nothing to supersede safely.
        return None

    cell = subject.at(Kind.CELL)
    if cell is None:
        return None
    voices = log.verdict(Q.VOICES, cell)
    if voices is None or voices.outcome is not Outcome.DECIDED \
            or not isinstance(voices.value, dict):
        return None
    streams = voices.value.get("voices") or []
    if voices.value.get("n_voices") != 1 or len(streams) != 1:
        # ⚠️ SCOPE, NOT AN ABSTENTION -- see the module note above: a
        # multi-voice bar's rest placement is ROADMAP 2.27c's own question.
        return None
    voice_glyphs = set(streams[0])
    if subject.glyph not in voice_glyphs:
        # ⚠️ A COVERING REST (`rests_in_every_voice`) never reaches here in a
        # single-voice bar -- `n_voices == 1` means there is no cover to be
        # in -- but the check stays explicit rather than assumed.
        return None

    grouping = log.verdict(Q.EVENT, cell)
    if grouping is None or grouping.outcome is not Outcome.DECIDED \
            or not isinstance(grouping.value, dict):
        return None
    raw_events = grouping.value.get("events") or []
    events = sorted(
        (e for e in raw_events if set(e.get("glyphs") or ()) & voice_glyphs),
        key=lambda e: (float(e.get("x") or 0.0), min(e.get("glyphs") or (0,))))
    rest_idx = None
    for i, e in enumerate(events):
        if subject.glyph in (e.get("glyphs") or ()):
            rest_idx = i
            break
    if rest_idx is None:
        return None

    return {"cell": cell, "cls": cls, "cur": cur, "voices": voices,
            "grouping": grouping, "events": events, "rest_idx": rest_idx}


def _rest_beat_slot_overlap(log: Log, ctx: dict, rest_box: Tuple[float, float]
                            ) -> bool:
    """(A): does this rest's own box share horizontal space with ANOTHER
    event of the same voice -- no gap exists there, whatever the meter says.
    """
    rx0, rx1 = rest_box
    for i, e in enumerate(ctx["events"]):
        if i == ctx["rest_idx"]:
            continue
        extent = _rest_beat_slot_event_extent(log, ctx["cell"],
                                              e.get("glyphs") or ())
        if extent is None:
            continue
        ex0, ex1 = extent
        if min(rx1, ex1) - max(rx0, ex0) > 0.0:
            return True
    return False


def _rest_beat_slot_onset(log: Log, ctx: dict
                          ) -> Optional[Tuple[bool, float, float, Verdict,
                                              List[Verdict]]]:
    """(B): the running onset, in DECIDED beats, of every event of this voice
    strictly BEFORE this rest (by print position) -- and whether it already
    reaches or passes the bar's own METER, in which case the print order
    contradicts what those durations imply: there is no time left for this
    rest to occupy. `None` wherever a prerequisite (a neighbour's duration,
    or the meter in force) is not DECIDED -- rule 8, cannot-tell is never an
    answer.
    """
    cell = ctx["cell"]
    onset = 0.0
    used: List[Verdict] = []
    for e in ctx["events"][:ctx["rest_idx"]]:
        glyphs = sorted(e.get("glyphs") or ())
        if not glyphs:
            return None
        rep = glyphs[0]
        sub = Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                      staff=cell.staff, cell=cell.cell, glyph=rep)
        d = log.verdict(Q.DURATION, sub)
        if d is None or d.outcome is not Outcome.DECIDED \
                or not isinstance(d.value, dict):
            return None
        beats = d.value.get("beats")
        if beats is None:
            return None
        onset += float(beats)
        used.append(d)

    meter_v = log.verdict(Q.METER, cell.at(Kind.SYSTEM))
    if meter_v is None or meter_v.outcome is not Outcome.DECIDED:
        return None
    segment = meter_at(meter_v.value, cell.cell)
    if not segment:
        return None
    num, den = segment.get("numerator"), segment.get("denominator")
    if not num or not den:
        return None
    try:
        target = float(num) * 4.0 / float(den)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    overflow = onset >= target - REST_BEAT_SLOT_EPSILON_QUARTERS
    return overflow, onset, target, meter_v, used


def _rest_beat_slot_also_reads(log: Log, subject: Subject,
                               voices: Verdict) -> List[str]:
    """Declared for `evaluate.run_over`, exactly as `_size_measure_rest_also_
    reads` is: `Q.EVENT`'s grouping, and -- where (B)'s prerequisites are met
    at all -- the meter and every neighbour's duration it actually reads.
    Shares `_rest_beat_slot_context`/`_rest_beat_slot_onset` with the rule
    body so the two can never disagree about what was read."""
    ctx = _rest_beat_slot_context(log, subject)
    if ctx is None:
        return []
    out = [ctx["grouping"].id]
    onset = _rest_beat_slot_onset(log, ctx)
    if onset is not None:
        _overflow, _onset, _target, meter_v, used = onset
        out.append(meter_v.id)
        out.extend(d.id for d in used)
    return out


@rule(consequence=Consequence.REST_BEAT_SLOT,
      cause=Q.VOICES, effect=Q.REST_IS_NOT_A_REST, scope=Kind.GLYPH,
      reads_beyond_cause=_rest_beat_slot_also_reads,
      bound="Fires on at most the one glyph it is called for, and only where "
            "that glyph carries a Q.REST row, is not a whole-bar-filling "
            "class, and its Q.REST_IS_NOT_A_REST verdict is still DECIDED "
            "false -- it never re-decides one already refused. Restricted to "
            "a SINGLE-VOICE bar (a multi-voice bar's rest placement is "
            "ROADMAP 2.27c's own question, left untouched). Reads only "
            "DECIDED verdicts for the neighbours it sums or measures -- a "
            "NARROWED or ABSTAINED Q.EVENT/Q.VOICES/Q.METER/Q.DURATION along "
            "the way makes it return [] rather than guess. Adds no glyph, "
            "deletes none, and touches no OTHER glyph's verdict.")
def rest_beat_slot(log: Log, subject: Subject, voices: Verdict) -> List[Verdict]:
    """Sean's beat-slot convention, the two sub-rules that FOLLOW without
    waiting on INFER -- see the module note above for the full design and
    what is deliberately NOT built here (`Q.ONSET_COLUMN`, a multi-voice bar,
    an argmax between competing readings).

    ⚠️ IT SUPERSEDES, IT DOES NOT DELETE -- exactly `apply_printed_accidental`'s
    own shape for revising an ADJUDICATE verdict from EVALUATE. The refused
    verdict's `basis` names the ADJUDICATE verdict it replaces plus every row
    this rule actually read, so a reviewer can see the contest rather than a
    changed number with no history.
    """
    ctx = _rest_beat_slot_context(log, subject)
    if ctx is None:
        return []
    rest_box = _rest_beat_slot_box(log, subject)
    if rest_box is None:
        return []

    cur = ctx["cur"]
    grouping = ctx["grouping"]

    if _rest_beat_slot_overlap(log, ctx, rest_box):
        basis = (cur.id, voices.id, grouping.id)
        out = Verdict(
            id=log._next_id("vrd"), subject=subject,
            quantity=Q.REST_IS_NOT_A_REST, outcome=Outcome.DECIDED,
            value=True, decider="rest_beat_slot",
            reason="rest_shares_a_beat_slot",
            considered=basis, basis=basis,
            detail={"class": ctx["cls"], "rest_idx": ctx["rest_idx"]},
            supersedes=cur.id)
        return [log.record(out)]

    onset = _rest_beat_slot_onset(log, ctx)
    if onset is not None:
        overflow, onset_beats, target, meter_v, used = onset
        if overflow:
            basis = (cur.id, voices.id, grouping.id, meter_v.id,
                     *(d.id for d in used))
            out = Verdict(
                id=log._next_id("vrd"), subject=subject,
                quantity=Q.REST_IS_NOT_A_REST, outcome=Outcome.DECIDED,
                value=True, decider="rest_beat_slot",
                reason="rest_after_the_bar_ends",
                considered=basis, basis=basis,
                detail={"class": ctx["cls"], "rest_idx": ctx["rest_idx"],
                       "onset_before_rest": round(onset_beats, 4),
                       "bar_beats": target},
                supersedes=cur.id)
            return [log.record(out)]

    return []


def _move_glyph_also_reads(log: Log, subject: Subject,
                           owner: Verdict) -> List[str]:
    """The WINNING STAFF'S CLEF -- the verdict this rule reads that is not its
    cause.

    ⚠️ DECLARED BECAUSE `evaluate.run_over` CANNOT GUESS IT. A glyph awarded
    to a staff whose clef abstained gets no pitch (`move_glyph` returns []
    rather than inventing one). When INFER later fills that clef, the glyph
    has a NEW consequence and its OWNERSHIP has not changed -- so a bounded
    second pass keyed on the cause alone would skip it, silently, and the
    heads a contest moved onto the repaired staff would stay unwritten while
    the heads cut on it were restated. That is a half-repair that reads as a
    whole one.
    """
    if not isinstance(owner.value, str):
        return []
    clef = log.verdict(Q.CLEF, Subject.from_key(owner.value))
    return [clef.id] if clef is not None else []


@rule(consequence=Consequence.MOVE_GLYPH,
      cause=Q.GLYPH_OWNER, effect=Q.PITCH, scope=Kind.GLYPH,
      reads_beyond_cause=_move_glyph_also_reads,
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
        # ⚠️⚠️ AN INLINE ACCIDENTAL OVERRIDES THE SIGNATURE, AND IN THE FIRST
        # PASS THIS GUARD IS NOT THE PLACE THAT ENFORCES IT -- roadmap 2.7
        # measured the ordering. `evaluate.run` orders rules by the DOWNHILL
        # index of their CAUSE, this rule's cause is `Q.KEY_SIGNATURE` and
        # `apply_printed_accidental`'s is `Q.ACCIDENTAL_OWNER`, below it, so
        # in the first pass the key-derived row is always written FIRST and
        # the override is done by SUPERSESSION, exactly as `move_glyph`
        # supersedes `Q.PITCH` for the same ordering reason.
        #
        # ⚠️⚠️ IN THE BOUNDED SECOND PASS IT IS THE ENFORCEMENT, and that is
        # what changed when 2.7 was merged onto 2.9b (2026-09-27). The 2.7
        # branch called this guard unreachable; it was, on a tree where the
        # key was only ever READ. `fill_part_key` now INFERS a key where the
        # reader abstained, and `evaluate.run_over` brings this rule back
        # over that staff AFTER `apply_printed_accidental` wrote the page's
        # alterations in the first pass -- so without this line an inferred
        # key would overwrite every printed natural and every carried
        # alteration on the staff. Pinned by
        # `test_staged_accidental.py::test_an_inferred_key_does_not_overwrite_a_printed_accidental`.
        if log.verdict(Q.ACCIDENTAL, pitch.subject) is not None:
            continue
        out.append(_verdict(
            log, pitch.subject, Q.ACCIDENTAL, accidental,
            decider="respell_accidental", reason="from_key_signature",
            basis=(pitch.id, key.id)))
    return out


def _letter_octave(pitch_value: Any) -> Optional[Tuple[str, int]]:
    """`'F4'` -> `('F', 4)`, through the LEGACY parser and not a slice.

    ⚠️ NOT `value[0]` AND `int(value[1:])`. `_legacy._parse_pitch` is what
    `_mxl_pitch_block` uses on the way out, so a spelling it cannot read is a
    note that reaches the file with no `<pitch>` block at all; asking it here
    means the two cannot come to disagree about what a pitch string is.
    """
    if not isinstance(pitch_value, str):
        return None
    from .. import export as _legacy
    parsed = _legacy._parse_pitch(pitch_value)
    if parsed is None:
        return None
    letter, _existing, octave = parsed
    return letter, int(octave)


def _apply_printed_also_reads(log: Log, subject: Subject,
                              owner: Verdict) -> List[str]:
    """The OWNED HEAD'S STAFF'S CLEF -- the verdict this rule reads besides
    its cause, declared for `evaluate.run_over` (roadmap 2.10's mechanism,
    which 2.7 was merged onto on 2026-09-27).

    ⚠️ WITHOUT IT A FILLED CLEF LEAVES EVERY PRINTED ACCIDENTAL ON THAT STAFF
    UNWRITTEN, SILENTLY. The rule needs the head's PITCH (C21 is keyed on
    letter and octave), and a staff whose clef abstained has no pitches, so
    the first pass returns [] for every glyph on it. When INFER then fills the
    clef (`fill_clef_gap`), `restate_pitch` fires again over that staff in the
    bounded second pass -- and a rule keyed on its cause alone, the OWNER,
    which did not change, would be skipped as `not_downstream_of_an_
    inference`. That is `_move_glyph_also_reads`' failure one rule down.
    """
    if not isinstance(owner.value, str):
        return []
    head = Subject.from_key(owner.value)
    staff = head.at(Kind.STAFF)
    if staff is None:
        return []
    clef = log.verdict(Q.CLEF, staff)
    return [clef.id] if clef is not None else []


@rule(consequence=Consequence.APPLY_PRINTED_ACCIDENTAL,
      cause=Q.ACCIDENTAL_OWNER, effect=Q.ACCIDENTAL, scope=Kind.GLYPH,
      reads_beyond_cause=_apply_printed_also_reads,
      bound="Writes an alteration onto the owned notehead and onto later "
            "noteheads IN THE SAME CELL at the SAME letter and octave that "
            "carry no printed glyph of their own. Never leaves the cell, "
            "never adds, deletes, moves or re-pitches a note, never touches a "
            "note that stands to the LEFT of the glyph, and never overrules "
            "another printed accidental.")
def apply_printed_accidental(log: Log, subject: Subject,
                             owner: Verdict) -> List[Verdict]:
    """The engraver drew it, so it governs -- to the end of the bar (C21).

    ⚠️⚠️ THIS FOLLOWS, IT IS NOT A GUESS, and that is why it is EVALUATE and
    not INFER. Given that this glyph alters that head, nothing about which
    notes in the bar carry the alteration is open: C21 is a closed rule of
    the notation -- *"an accidental is not a property of one notehead: once
    printed it governs later notes at the same letter and octave until the
    barline"* -- and the ABSENCE of a glyph on a later note is a positive
    statement about its pitch rather than a gap. A reader attaching the
    alteration only to its immediate note reads every later note of that
    pitch in the bar a semitone wrong.

    ⚠️⚠️ IT SUPERSEDES RATHER THAN DEFERS, AND THE ORDER IS THE REASON.
    `evaluate.run` sorts the rules by the DOWNHILL index of their CAUSE.
    `respell_accidental` is caused by `Q.KEY_SIGNATURE` (index 8) and this by
    `Q.ACCIDENTAL_OWNER` (index 11), so the key-derived row is ALWAYS already
    on the record when this runs and `respell_accidental`'s own "leave a note
    that carries one alone" guard can never see this rule's output. Deferring
    would therefore be silent no-op. `move_glyph` supersedes `Q.PITCH` for
    exactly this reason and this mirrors it, `supersedes=` and all, so the
    record shows the key's answer AND the page's answer with the page's
    winning visibly.

    ⚠️ A NATURAL CANCELS, AND THE CANCELLATION IS BAR-SCOPED LIKE ANY OTHER
    ACCIDENTAL. A `natural` verdict is written exactly as a sharp is, and it
    carries to the end of the bar in exactly the same way; the exporter turns
    it into `<alter>0</alter>` plus a drawn `<accidental>natural</accidental>`
    because the two facts are independent. Writing nothing instead -- letting
    the note fall back to the key -- would put the key's flat back on a note
    the engraver explicitly cancelled, which is the whole of what a natural is
    for.

    ⚠️ THE CARRY IS ORDER-FREE, and it has to be: this rule fires once per
    accidental glyph and the firing order within a cell is the subject
    iteration order, not the page's left-to-right. So a later note is written
    only where THIS glyph is the LAST printed accidental at that (letter,
    octave) standing at or before it -- a question asked of the record rather
    than of the sequence, which gives the same answer whichever glyph fired
    first. `explicit_in_measure` gets this from its left-to-right walk; a
    rule that cannot walk must ask instead.

    ⚠️ THE CELL IS THE BAR. `Q.MEASURE_PARTITION` cut it, and CLAUDE.md §10's
    *"a cell index restarts per system"* is why the carry is keyed on the CELL
    subject and never on a bar NUMBER.
    """
    if not isinstance(owner.value, str):
        return []
    head = Subject.from_key(owner.value)
    alteration = (owner.detail or {}).get("alteration")
    if not isinstance(alteration, str) or not alteration:
        return []

    pitch = log.verdict(Q.PITCH, head)
    if pitch is None or pitch.outcome is not Outcome.DECIDED:
        # ⚠️ NO PITCH, NO ALTERATION. A staff whose clef abstained produces no
        # pitches (`restate_pitch`), and an alteration written onto a note
        # whose letter nobody read would be an alteration of nothing. The
        # glyph stays DECIDED on the record and the exporter counts it.
        return []
    target = _letter_octave(pitch.value)
    if target is None:
        return []

    cell = head.at(Kind.CELL)
    if cell is None:
        return []

    # ⚠️⚠️ TWO GLYPHS THAT CLAIM ONE HEAD WITH DIFFERENT ALTERATIONS: NOTHING
    # FOLLOWS, SO NOTHING IS WRITTEN. Measured on the MERGED tree
    # (2026-09-27), not foreseen by the branch: on the Litolff whole movement
    # 100 heads are owned by more than one decided glyph, and 79 of them by
    # glyphs that DISAGREE -- flat vs natural 45, sharp vs natural 23 (the
    # merging plate boxes one piece of ink twice under two classes, or two
    # glyphs stand within the window of one head). `accidental_owner` decides
    # per GLYPH and cannot see the other claim; this rule is where both are
    # on the record at once. Before this guard the rule fired once per glyph
    # and the LAST to fire superseded the first, so the written alteration
    # depended on subject iteration order -- exactly what the order-free
    # docstring above says this rule must not do. Two claims that agree are
    # one fact read twice and are written (the second supersedes the first
    # with the same value); two that disagree are a contradiction, and a
    # contradiction is not converted into an answer (CLAUDE.md §2 rule 8).
    # The head keeps whatever the key gave it, and `accidental_reading`
    # counts it under `heads_contradicted`.
    for other in _standing(log, cell, Q.ACCIDENTAL_OWNER):
        if (other.id != owner.id and other.outcome is Outcome.DECIDED
                and other.value == owner.value
                and (other.detail or {}).get("alteration") != alteration):
            return []

    x_of = {}
    for row in log.rows(Q.GLYPH_BOX, cell, scope=Scope.SELF_AND_DESCENDANTS):
        v = row.value
        if isinstance(v, (list, tuple)) and len(v) >= 5:
            x_of[row.subject.to_key()] = float(v[1])
    own_x = x_of.get(head.to_key())
    if own_x is None:
        return []

    # Every OTHER printed accidental in this bar, so the carry can ask which
    # of them governs a later note rather than depending on firing order.
    # ⚠️ `_standing`, NOT `log.verdicts`, and the module's own note says why:
    # the plural returns every ROW including ones a later consequence
    # superseded, and `move_glyph` restates `Q.PITCH` on exactly the glyphs
    # this rule then reads. Walking the raw rows would let a re-pitched note
    # be governed by the letter it used to have.
    rivals = []
    for other in _standing(log, cell, Q.ACCIDENTAL_OWNER):
        if other.id == owner.id or other.outcome is not Outcome.DECIDED:
            continue
        if not isinstance(other.value, str):
            continue
        rival_head = Subject.from_key(other.value)
        rx = x_of.get(rival_head.to_key())
        rp = log.verdict(Q.PITCH, rival_head)
        if rx is None or rp is None or rp.outcome is not Outcome.DECIDED:
            continue
        if _letter_octave(rp.value) != target:
            continue
        rivals.append(rx)

    out: List[Verdict] = []
    owned_keys = {head.to_key()}
    out.append(_supersede(log, head, alteration,
                          reason="printed_glyph", owner=owner,
                          basis=(owner.id, pitch.id), printed=True))

    for later in _standing(log, cell, Q.PITCH):
        if later.outcome is not Outcome.DECIDED:
            continue
        key = later.subject.to_key()
        if key in owned_keys:
            continue
        lx = x_of.get(key)
        if lx is None or lx <= own_x:
            continue                    # standing to the LEFT: not governed
        if _letter_octave(later.value) != target:
            continue
        # ⚠️ A HEAD THE CONTEST AWARDED TO ANOTHER STAFF IS NOT IN THIS BAR.
        # Its `Q.PITCH` was restated by `move_glyph` on the WINNER's clef, so
        # a letter match here compares this staff's accidental against
        # another staff's note; the exporter drops it from this staff
        # (`owned_by_another_staff`), and the carry must not reach it either.
        moved = log.verdict(Q.GLYPH_OWNER, later.subject)
        if (moved is not None and isinstance(moved.value, str)
                and moved.value != head.at(Kind.STAFF).to_key()):
            continue
        # ⚠️ A NOTE THAT CARRIES ITS OWN PRINTED GLYPH IS LEFT ALONE. That
        # glyph's own firing writes it, with `printed=True`; overwriting it
        # here would turn a drawn natural back into the sharp it cancelled.
        if log.verdict(Q.ACCIDENTAL_OWNER, later.subject) is not None:
            continue
        if any(own_x < rx <= lx for rx in rivals):
            continue                    # a nearer printed accidental governs
        out.append(_supersede(log, later.subject, alteration,
                              reason="carried_in_bar", owner=owner,
                              basis=(owner.id, later.id), printed=False))
    return out


def _supersede(log: Log, subject: Subject, alteration: str, *, reason: str,
               owner: Verdict, basis: Tuple[str, ...],
               printed: bool) -> Verdict:
    """One `Q.ACCIDENTAL` write that displaces the key-derived one visibly.

    ⚠️ `printed` IS THE WHOLE OF THE `<accidental>` DECISION AND IT IS A FACT
    ABOUT THIS NOTE, not about the alteration. The owned head carries a glyph
    the engraver drew; the notes it carries to in the bar carry the same
    SOUND and no glyph at all, because the engraver did not draw one on them.
    `e8cf5b26` fixed the inverse of this -- the key-derived alteration emitted
    as a printed glyph, 334 `<accidental>` elements against 0 `<alter>` on
    Litolff pp.1-4 -- and the two must never be re-joined.
    """
    prior = log.verdict(Q.ACCIDENTAL, subject)
    out = Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=Q.ACCIDENTAL,
        outcome=Outcome.DECIDED, value=alteration,
        decider="apply_printed_accidental", reason=reason,
        considered=tuple(basis), basis=tuple(basis),
        detail={"printed": printed, "accidental_glyph": owner.subject.to_key(),
                "from": (prior.value if prior is not None else None),
                "from_decider": (prior.decider if prior is not None else None)},
        supersedes=prior.id if prior is not None else None)
    return log.record(out)


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
