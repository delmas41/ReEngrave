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
from typing import Any, Dict, List, Optional, Sequence, Tuple

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

    ⚠️⚠️ ROADMAP 2.42 (Sean, scope change): NO STACKED-HEAD CONNECTION HERE,
    AND THERE WILL NOT BE ONE FROM THIS ITEM. The ink-fit position
    (`Q.STACKED_HEAD_FIT`) was briefly read here via a withdrawn
    `Q.STACKED_HEAD_POSITION`, then replaced with a narrow same-side-second
    rounding-residual rule -- BOTH withdrawn. The real cause of the wrong
    pitches above the staff is that printed LEDGER LINES are not evenly
    spaced (measured: Litolff p3 staff/3/0/0's own ledgers sit 18/13/20 px
    apart against a 15.75 px staff spacing -- extrapolating the staff's own
    spacing drifts ~4 px by the third ledger). Fixing that needs positions
    read from the printed ledgers themselves, a SEPARATE roadmap item
    (2.44), not this one. This function reads the raw `Q.NOTEHEAD_STAFF_
    POSITION` centre for EVERY notehead, exactly as before ROADMAP 2.42 ever
    existed.
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


def _stem_ids_used(log: Log, v: Verdict) -> "set":
    """The `Q.STEM` observation ids THIS duration verdict actually attached
    to, read from its own `used` -- ROADMAP 2.36.

    ⚠️ `used`, NEVER `considered`/`basis`. `adjudicate_duration` reads
    `ev.rows(Q.STEM, scope=SELF_AND_ANCESTORS, subject=cell)` -- EVERY stem
    in the cell -- so `considered` (and the `basis` closure over it) holds
    every stem the cell has, the same set for every note in the bar and
    useless for telling one chord's stem from the next. `used` is narrower
    by construction (`rhythm.py`'s `Ruling.used`, filled by
    `used.extend(s.id for s in attached)` where `attached` is
    `_stem_joined`'s own overlap test between THIS head's box and the
    stem rows) -- the exact id or ids this glyph's own box touched.
    """
    out: set = set()
    for rid in v.used:
        row = log.row(rid)
        if row is not None and row.quantity == Q.STEM:
            out.add(rid)
    return out


def _chord_duration_also_reads(log: Log, subject: Subject,
                               meter: Verdict) -> List[str]:
    """Declared for `run_over`, exactly as `size_measure_rest`/
    `reconcile_duration` declare their own extra reads: every OTHER
    standing `Q.DURATION` verdict in this cell, since this rule's real
    cause -- a chord mate's own decided reading -- is not the meter this
    quantity is registered under."""
    return [v.id for v in _standing(log, subject, Q.DURATION)]


@rule(consequence=Consequence.RECONCILE_CHORD_DURATION,
      cause=Q.METER, effect=Q.DURATION, scope=Kind.CELL,
      reads_beyond_cause=_chord_duration_also_reads,
      bound="Fires on a NARROWED note only where exactly ONE other glyph in "
            "the same cell is DECIDED and its duration verdict's `used` "
            "names the exact SAME `Q.STEM` observation id (not merely an "
            "overlapping box -- the identical row `_stem_joined` attached to "
            "both heads), and only where that mate's OWN `beam_levels` is "
            "one of the narrowed note's OWN candidates -- never a value it "
            "did not already offer. Two or more decided stem-mates that "
            "disagree, or a level the narrowing does not carry, refuse "
            "rather than choose. Touches no rest (`_is_rest` excludes them --"
            " a rest carries no stem) and revises at most the glyphs this "
            "cell's narrowed notes name, one each.")
def reconcile_chord_duration(log: Log, subject: Subject,
                             meter: Verdict) -> List[Verdict]:
    """A chord's heads are struck on ONE stem, so they carry ONE duration.

    ⚠️⚠️ ROADMAP 2.36. `duration_narrowed` is EXPORT's second-largest
    refusal (Brahms ~2,559, Litolff ~902 on the 2026-09-29 acceptance
    records), and its single biggest reason is `beams_ambiguous` -- a
    stroke only POSSIBLY covers this note, so its own beam count is a
    range (`benchmarks/omr-duration-narrowed-2026-09/FINDINGS.md`). Most of
    that ambiguity is genuinely undecidable from what is filed (measured:
    the biggest single class, "no certain beam, one possible", has no
    other reader's row to connect to and would need a NEW one -- not built
    here, rule 6). But where the SAME notehead's stem also carries another
    head the record has already DECIDED, the note is not ambiguous on its
    own terms at all: the two glyphs are one note EVENT, struck together,
    and the sibling's already-settled beam count is what this note's own
    ink was always going to agree with -- this FOLLOWS from two facts
    already on the record (two `Q.DURATION` verdicts sharing one `Q.STEM`
    row), not a guess (rule 6).

    ⚠️ MEASURED, NOT ASSUMED, AND THE REACH IS MODEST: `chord_reach.py`
    against both 2026-09-29 acceptance records finds 32 of 1,149 narrowed
    Litolff notes and 37 of 3,200 narrowed Brahms notes qualify (a decided
    stem-mate whose level the narrowing already admits) -- about 2% and
    1%. This is the connection that FOLLOWS, not the biggest bucket; the
    biggest bucket needs a reader this roadmap item does not build (see
    the module docstring above and `FINDINGS.md`).

    ⚠️ NEVER GUESSES PAST ITS OWN NARROWING, same discipline as
    `reconcile_duration`'s own meter search: the mate's beam level only
    settles this note when that EXACT level is one of the narrowing's own
    candidates. A `head_fill_from_ink` narrowing (three candidates that
    all carry `beam_levels: 0`) is a case in point -- more than one of its
    own candidates would match a beam_levels-0 mate, so `len(admitted) !=
    1` and this refuses rather than picking one: the mate speaks to BEAM
    COUNT, not to notehead fill, and conflating the two would be exactly
    the guess rule 6 forbids.
    """
    notes = [v for v in _standing(log, subject, Q.DURATION) if not _is_rest(v)]
    decided = [v for v in notes if v.outcome is Outcome.DECIDED]
    narrowed = [v for v in notes if v.outcome is Outcome.NARROWED]
    if not decided or not narrowed:
        return []

    decided_stems = [(v, _stem_ids_used(log, v)) for v in decided]
    decided_stems = [(v, s) for v, s in decided_stems if s]
    if not decided_stems:
        return []

    out: List[Verdict] = []
    for n in narrowed:
        n_stems = _stem_ids_used(log, n)
        if not n_stems:
            continue
        mates = [v for v, s in decided_stems if s & n_stems]
        if len(mates) != 1:
            # zero: no decided stem-mate yet. more than one: which stem is
            # this note's own is no longer a single fact -- refuse (rule 8).
            continue
        mate = mates[0]
        mate_levels = (mate.value or {}).get("beam_levels")
        if mate_levels is None:
            continue
        admitted = [c for c in n.candidates
                   if isinstance(c.value, dict)
                   and c.value.get("beam_levels") == mate_levels]
        if len(admitted) != 1:
            continue
        option = admitted[0].value
        out.append(log.record(Verdict(
            id=log._next_id("vrd"), subject=n.subject, quantity=Q.DURATION,
            outcome=Outcome.DECIDED,
            value={**option, "reconciled_by_chord_mate": True},
            decider="reconcile_chord_duration",
            reason="chord_mate_shares_the_stem",
            considered=(n.id, mate.id), used=(n.id, mate.id),
            basis=(n.id, mate.id),
            supersedes=n.id)))
    return out


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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.45. A rest refused on BOTH staves it was detected on belongs to
# whichever staff's own bar is missing it. Sean, DECISIONS 2026-09-30 (found
# on Brahms 1/i Breitkopf p1, bar 5, three printed eighth rests between
# staves 2 and 3 of system 0, `glyph/1/0/2/5/{0,3,10}` and
# `glyph/1/0/3/5/{1,0,2}`, all six refused `rest_outside_its_staff`):
#
#   *"They belong to the lower staff. I was able to determine that based on
#   the amount of voices in each of the staffs. The one above has 2 voices
#   and both the voices are accounted for. The one below has a voice that
#   crosses as they both jump up higher. If the 8th note rests didn't belong
#   to the lower staff then it would be missing a voice."*
#
# ⚠️⚠️ MANAGER CORRECTION 2026-09-30, after the first build's A/B fired zero
# times on Sean's own case. Three faults, all in the FIRST build, all fixed
# here:
#
#   1. **A staff's expected total is VOICES × bar length, not one bar
#      length.** Sean reasons per VOICE ("the one above has 2 voices and
#      both are accounted for"): a staff carrying two simultaneous voices
#      must sum to TWICE the bar, because each voice independently spans the
#      whole bar. `_voice_count` (below) reads `Q.VOICES` where decided, else
#      counts by stem direction exactly as `adjudicate_voices` (ROADMAP 2.21)
#      does at its own first rule -- two DECIDED `Q.STEM_DIRECTION`s that
#      disagree is two voices; one direction only is one voice; neither
#      decided is UNDECIDED, and this rule then abstains (rule 8) rather
#      than assume one.
#   2. **The contested rests are ONE GROUP per bar, not six independent
#      0.5-beat tests.** `_contest_group` (below) collects every glyph in
#      one cell that is ALSO refused `rest_outside_its_staff` against the
#      SAME neighbour staff, and the group's own total length (not one
#      rest's own `Q.DURATION`) is what a staff's shortfall must equal.
#      Sean's three eighth rests are one group of 1.5 beats, not three
#      separate 0.5-beat questions -- his own reasoning is about the VOICE
#      being short, not about any one rest in isolation.
#   3. **The meter it reads is whatever `Q.METER` DECIDED, never a better
#      guess.** ROADMAP 2.12h records this exact system (Brahms 1/i
#      Breitkopf p1, `system/1/0`) misreading its opening meter as `9/4`
#      where the plate prints `6/8` (with one `9/8` hemiola bar, m. 8) --
#      and on the record this item measures against, the misread persists
#      for the bar in question (§21c in FINDINGS names the bar, the printed
#      meter and the DECIDED verdict). This rule may not repair that; it is
#      a BLOCKER on this specific bar, named not built, and is why the tests
#      below exercise the mechanism with a CORRECT meter injected directly
#      (Sean's process convention: microscopic fixtures, no re-gather) rather
#      than only against the mis-metered real record.
#
# ⚠️⚠️ MANAGER CORRECTION 2026-09-30, SECOND ROUND, after the first fix's A/B
# still fired zero times -- this time correctly diagnosed as blocked by the
# meter (§21c), but the manager caught a FOURTH fault the meter blocker was
# masking: the candidate staff was required to be COMPLETE (shortfall zero),
# when it only needs to be UNABLE TO EXPLAIN THIS GROUP (its own shortfall
# not equal to the group's length). Sean's upper staff carries its own
# unrelated ~1-beat gap in the same bar; that gap must never block the lower
# staff's own exact match. Fixed: the candidate test now compares its own
# shortfall to the GROUP's length, not to zero -- see the comment at the
# call site below. Both staves matching the group (genuinely ambiguous) or
# neither matching still refuses (rule 8); one match and one unrelated
# non-match does not.
#
# ⚠️ WHY THIS READS THE BAR SUM AND NOT `Q.VOICES`'S OWN GROUPING. `Q.VOICES`
# (`adjudicators/rhythm.py`) is decided from `Q.EVENT`'s grouping, and
# `adjudicate_event` reads `Q.REST` -- a GATHER-level class fact -- never
# `Q.REST_IS_NOT_A_REST`. So a rest's own ADJUDICATE-time refusal never
# removes it from its cell's `Q.EVENT`/`Q.VOICES` computation at all: BOTH
# staves' voice splits already "see" their own local copy of the ink,
# refused or not, and the grouping cannot tell a staff that NEEDS the rest
# from one that does not. `Q.VOICES`'s own `n_voices` COUNT is still read
# (fault 1's fix) -- it is only the per-bar TOTAL that must come from
# `_bar_total_excluding_refused` (below, built from `reconcile_duration`'s
# own `_standing`/`_left_the_bar`/`_event_totals`), because that is the one
# reader in the tree that DOES respect a DECIDED `Q.REST_IS_NOT_A_REST`.
# ─────────────────────────────────────────────────────────────────────────────

#: Two floating-point bar sums (target vs. standing total) are compared
#: exactly, the same tolerance `reconcile_duration`'s own landing test uses.
REST_BAR_SUM_EPS = 1e-6


def _bar_total_excluding(log: Log, cell_subject: Subject,
                        force_exclude: frozenset) -> Optional[float]:
    """This bar's own length, RIGHT NOW: every standing duration under
    `cell_subject`, excluding anything `_left_the_bar` already took out (a
    DECIDED not-a-notehead, not-a-rest or another-staff verdict) OR named in
    `force_exclude` -- `None` where the bar cannot be summed at all (no
    standing duration, an undecided `Q.EVENT`, or a still-NARROWED note with
    no candidates).

    ⚠️ `force_exclude` EXISTS SO A GROUP IS EXCLUDED AS ONE GROUP, ORDER
    -INDEPENDENTLY. This rule runs once per GLYPH (`evaluate.run`'s own
    loop), so a group's members are visited one at a time within the same
    EVALUATE pass; `_left_the_bar` alone would report a DIFFERENT total for
    the second member visited than the first, once the first has already
    been reinstated (superseded) -- the total would silently grow mid-pass
    and the second member's own equality test would be answering a different
    question than the first member's. Naming every group member here, once,
    up front (computed from the group's members as GATHER/ADJUDICATE left
    them, never from what THIS rule has written so far this pass) keeps the
    same bar total for every member's own test regardless of visiting order.

    ⚠️ THE SAME QUESTION `reconcile_duration` ASKS, ANSWERED THE SAME WAY,
    on purpose: its own preamble (this function's body, before the landing
    search) is not restated here, it is CALLED — `_standing`, `_left_the_bar`
    and `_event_totals` are each already paid for and each already correct
    about which boxes a bar still holds.
    """
    notes = []
    for v in _standing(log, cell_subject, Q.DURATION):
        if v.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
            continue
        if v.subject in force_exclude:
            continue
        if _left_the_bar(log, v.subject) is not None:
            continue
        notes.append(v)
    if not notes:
        return None

    def _current(v: Verdict):
        if v.outcome is Outcome.DECIDED:
            return v.value
        return v.candidates[0].value if v.candidates else None

    current = {v.id: _current(v) for v in notes}
    if any(c is None for c in current.values()):
        return None
    return _event_totals(log, cell_subject, notes, current)


def _contest_group(log: Log, cell_subject: Subject, partner_key: str
                   ) -> List[Subject]:
    """Every glyph under `cell_subject` that is ITSELF refused
    `rest_outside_its_staff` (its ORIGINAL ADJUDICATE verdict, never a
    verdict this rule already wrote — `decider` excludes this rule's own
    name, so a group computed mid-pass, after an earlier sibling in the
    SAME group has already been reinstated, still names the whole original
    group) AND contests THIS SAME neighbour staff (`Q.GLYPH_BAND_DISTANCE`
    naming `partner_key`). Sean's three eighth rests are one call to this
    function, not three.
    """
    out = []
    for v in log.verdicts(Q.REST_IS_NOT_A_REST, cell_subject,
                         scope=Scope.SELF_AND_DESCENDANTS):
        if (v.outcome is not Outcome.DECIDED or v.value is not True
                or v.reason != "rest_outside_its_staff"
                or v.decider == "reinstate_rest_between_staves"):
            continue
        bands = log.rows(Q.GLYPH_BAND_DISTANCE, v.subject)
        keys = {str(r.detail.get("candidate")) for r in bands
               if r.detail and r.detail.get("candidate") is not None}
        if partner_key in keys:
            out.append(v.subject)
    return out


def _group_length(log: Log, group: Sequence[Subject]) -> Optional[float]:
    """The group's own total length, from each member's OWN `Q.DURATION` --
    `None` if any member's length is not itself settled."""
    total = 0.0
    for g in group:
        dur = log.verdict(Q.DURATION, g)
        if dur is None or dur.outcome is not Outcome.DECIDED:
            return None
        beats = (dur.value or {}).get("beats")
        if beats is None:
            return None
        total += float(beats)
    return total


def _voice_count(log: Log, cell_subject: Subject) -> Optional[int]:
    """How many voices this bar carries, read `Q.VOICES` first (2.21's own
    decision), else counted by stem direction exactly as `adjudicate_voices`
    counts it at its own first rule -- two DECIDED `Q.STEM_DIRECTION`s that
    disagree is two voices, one direction only (at least one DECIDED) is
    one voice. `None` where neither is decided (rule 8 -- this rule must
    never assume a voice count it was not given).
    """
    voices = log.verdict(Q.VOICES, cell_subject)
    if voices is not None and voices.outcome is Outcome.DECIDED:
        n = (voices.value or {}).get("n_voices")
        if isinstance(n, int) and n > 0:
            return n

    directions = set()
    for v in log.verdicts(Q.STEM_DIRECTION, cell_subject,
                         scope=Scope.SELF_AND_DESCENDANTS):
        if v.outcome is Outcome.DECIDED and _left_the_bar(log, v.subject) is None:
            directions.add(v.value)
    if "up" in directions and "down" in directions:
        return 2
    if directions:
        return 1
    return None


@rule(consequence=Consequence.REINSTATE_REST_BETWEEN_STAVES,
      cause=Q.METER, effect=Q.REST_IS_NOT_A_REST, scope=Kind.GLYPH,
      bound="Fires only on a glyph DECIDED `rest_outside_its_staff` that is "
            "also in a genuine cross-staff contest (`Q.GLYPH_BAND_DISTANCE` "
            "rows naming another staff), as part of a GROUP of such glyphs "
            "against the same neighbour. Reinstates the WHOLE GROUP on ITS "
            "OWN staff only, never moves it, and only where that staff's "
            "own (VOICE COUNT x bar length) shortfall EQUALS the group's "
            "own total length once every currently-refused glyph is "
            "excluded, AND the other contested staff's own shortfall does "
            "NOT also equal the group's length -- the other staff need not "
            "be COMPLETE, only unable to explain the SAME group. Any other "
            "shape -- no contest, an undecided voice count or candidate, "
            "a shortfall that does not match on the own staff, BOTH "
            "staves' shortfalls matching the group (ambiguous) or NEITHER "
            "matching -- changes nothing (rule 8).")
def reinstate_rest_between_staves(log: Log, subject: Subject,
                                  meter: Verdict) -> List[Verdict]:
    """A GROUP of rests doubly refused `rest_outside_its_staff` is
    reinstated on the one staff whose voice it completes.

    ⚠️ NEVER RELOCATED, NEVER DUPLICATED. Every glyph in the group already
    sits on its own staff's own cell -- the neighbour staff's padded cell
    independently detected its own twin copies, separate glyph subjects with
    their own verdicts, untouched here. Superseding each of THIS staff's own
    group members is the entire repair; the sibling copies on the other
    staff stay refused because nothing about THEM changed (that staff's own
    total is not short by this amount).

    ⚠️ SYMMETRIC BY CONSTRUCTION, NOT BY A SPECIAL CASE. This rule runs once
    per glyph, so every member of both staves' copies of one group is
    offered the same test independently, and each recomputes the SAME group
    (`_contest_group`) and the SAME two bar totals regardless of visit
    order (`_bar_total_excluding`'s `force_exclude`). Only the staff whose
    total is actually short by the group's own length reinstates; the other
    staff's own equality fails and the function returns `[]` for it.
    """
    refusal = log.verdict(Q.REST_IS_NOT_A_REST, subject)
    if (refusal is None or refusal.outcome is not Outcome.DECIDED
            or refusal.value is not True
            or refusal.reason != "rest_outside_its_staff"):
        return []

    own_key = subject.at(Kind.STAFF).to_key()
    bands = log.rows(Q.GLYPH_BAND_DISTANCE, subject)
    others = sorted({str(r.detail.get("candidate")) for r in bands
                     if r.detail and r.detail.get("candidate") is not None
                     and str(r.detail.get("candidate")) != own_key})
    if not others:
        return []          # not a cross-staff contest at all -- an ordinary
                            # off-staff refusal, untouched

    value = meter.value or {}
    num, den = value.get("numerator"), value.get("denominator")
    if not num or not den:
        return []
    bar_len = float(num) * 4.0 / float(den)

    own_cell = subject.at(Kind.CELL)
    own_voices = _voice_count(log, own_cell)
    if own_voices is None:
        return []           # this staff's own voice count is undecided
    own_expected = own_voices * bar_len

    for partner_key in others:
        group = _contest_group(log, own_cell, partner_key)
        if subject not in group:
            continue        # this glyph's own contest partner, not this one
        group_len = _group_length(log, group)
        if group_len is None:
            return []
        own_total = _bar_total_excluding(log, own_cell, frozenset(group))
        if own_total is None:
            return []
        own_shortfall = own_expected - own_total
        if abs(own_shortfall - group_len) > REST_BAR_SUM_EPS:
            # Zero (already complete without the group), negative (already
            # over -- something ELSE is wrong here), or a shortfall that does
            # not match the GROUP's own length: not this group's own gap.
            continue

        cand_staff = Subject.from_key(partner_key)
        cand_cell = R.cell(cand_staff.page, cand_staff.system,
                          cand_staff.staff, subject.cell)
        cand_voices = _voice_count(log, cand_cell)
        if cand_voices is None:
            return []
        cand_expected = cand_voices * bar_len
        cand_group = _contest_group(log, cand_cell, own_key)
        cand_total = _bar_total_excluding(log, cand_cell, frozenset(cand_group))
        if cand_total is None:
            return []
        cand_shortfall = cand_expected - cand_total
        # ⚠️⚠️ MANAGER CORRECTION 2026-09-30 (second round). The other staff
        # does NOT have to be COMPLETE -- it only has to be UNABLE to take
        # the group itself, i.e. ITS OWN shortfall must not also equal the
        # group's length. An unrelated gap of some OTHER size on the other
        # staff (Sean's own upper-staff ~1-beat gap, unconnected to these
        # rests) is not evidence either way and must never block the one
        # staff whose shortfall DOES match. Only when BOTH staves' own
        # shortfalls equal the group's length (genuinely ambiguous -- the
        # group could belong to either) or NEITHER does is this refused
        # (rule 8 -- a fallback never converts "cannot tell" into an
        # answer); one match and one non-match is not ambiguous.
        if abs(cand_shortfall - group_len) <= REST_BAR_SUM_EPS:
            continue

        out = Verdict(
            id=log._next_id("vrd"), subject=subject,
            quantity=Q.REST_IS_NOT_A_REST,
            outcome=Outcome.DECIDED, value=False,
            decider="reinstate_rest_between_staves",
            reason="rest_reinstated_missing_voice",
            considered=(refusal.id, meter.id),
            basis=(refusal.id, meter.id),
            detail={"own_shortfall_beats": round(own_shortfall, 6),
                    "candidate_shortfall_beats": round(cand_shortfall, 6),
                    "group_len_beats": round(group_len, 6),
                    "own_voices": own_voices, "candidate_voices": cand_voices,
                    "group": [g.to_key() for g in group],
                    "candidate": partner_key},
            supersedes=refusal.id)
        return [log.record(out)]
    return []
