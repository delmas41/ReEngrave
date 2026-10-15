"""The inference rules. Two so far, and they are two on purpose.

⚠️ Registered by importing this module, which `infer._ensure_rules` does
LAZILY -- so a tree carrying INFER imports nothing extra until the stage is
actually asked to run. That is part of the bypass: off means ABSENT, not
quiet.

⚠️⚠️ BOTH RULES MAKE ONE CLAIM AND DIFFER IN THEIR ENDPOINT. *An onset column
is an instant; if this note and a neighbour span the same two instants, they
are the same length.* `COLLAPSE_DURATION_BY_COLUMN` takes the case where the
second instant is another onset column; `COLLAPSE_DURATION_TO_BARLINE` takes
the case where it is the BARLINE. They share `_walk` and `_propose` so the
guards cannot drift apart, and they are nonetheless two registered rules
rather than one with a branch, because:

  * the barline case needs a guard the column case does not (a witness whose
    length came from the METER is refused), and a guard hidden behind a
    branch is a guard a later reader will not know is there; and
  * `Report.reach` is per rule, so one bucket would hide what the second
    claim actually bought.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .adjudicators.rhythm import ONSET_COLUMN_TOLERANCE_SPACES, _page_x_of
from .infer import (ALWAYS_ON, ARC_INK_NOT_BEAM_SWITCH, carried_meter_fix_enabled, ledger_owner_heads_enabled, BARE_STEM_BAR_SWITCH, NARROWED_BAR_SWITCH, DYNAMIC_INK_PICK_SWITCH, Inference, PART_KEY_SWITCH, Proposal, independent_groups, rule)
# ⚠️ PRIVATE, SAME MODULE FAMILY (matches `log._next_id` elsewhere in this
# stage, the SLF001 case): `_admit`'s own candidate-membership check for a
# NARROWED prior is exactly the test roadmap 2.10b's declines need to make
# BEFORE proposing, so a value the reader never admitted reads as a named
# decline here rather than a `ValueNotAdmitted` crash in the harness.
from .infer import _candidate_values, _same_value  # noqa: SLF001,E501
from . import record as R
from .record import Kind, Log, Outcome, Q, Scope, Subject, Verdict

# ─────────────────────────────────────────────────────────────────────────────
# Collapse a narrowed duration by the COLUMN — the sideways rule
# ─────────────────────────────────────────────────────────────────────────────

#: How many INDEPENDENT witnesses must agree before a narrowing is collapsed.
#:
#: ⚠️ INDEPENDENT, counted by `infer.independent_groups`, never merely
#: DISTINCT. Two staves whose duration verdicts reach a shared provenance row
#: are one signal, and hazard (b) is precisely that counting them as two is
#: invisible unless somebody computes it.
#:
#: ⚠️⚠️ THIS CONSTANT IS NOT MEASURED AND SAYS SO. It is 2 because one
#: witness is not corroboration -- the same floor `ONSET_COLUMN_MIN_WITNESSES`
#: uses for forming a column at all, and imported nowhere from because it is a
#: different question (forming vs believing). What carries the weight here is
#: not the floor but the UNANIMITY requirement below: a single dissenting
#: witness refuses the whole inference. Do not raise this to buy precision
#: without measuring what it costs in reach.
COLUMN_MIN_INDEPENDENT_WITNESSES = 2


def _events_with_x(log: Log, system: Subject) -> Dict[Tuple[int, int], List[dict]]:
    """(staff, cell) -> that bar's events, sorted by page x, each with `x`.

    ⚠️ `Q.EVENT` IS CONSUMED, NOT REDONE. Within-staff simultaneity is already
    decided per cell under a tolerance measured off that bar's own noteheads;
    re-clustering the glyphs here would answer the same question twice and let
    the two answers disagree -- which is `adjudicate_onset_column`'s own stated
    discipline, inherited rather than re-derived.

    ⚠️ A glyph with no PAGE frame is dropped, never fallen back to its
    canonical x. A canonical x is measured inside one rescaled cell, so two
    staves' canonical frames coincide BY CONSTRUCTION and agreeing there is
    evidence of nothing -- the fault that made `Q.ONSET_COLUMN` report 1,062
    columns of nothing.
    """
    boxes = _page_x_of(log.rows(Q.GLYPH_BOX, system,
                                scope=Scope.SELF_AND_DESCENDANTS))

    # ⚠️⚠️ A CELL IS A CROP, AND ITS INK IS NOT ALL ITS OWN. The measure cell
    # is padded 4 staff spaces (6 where the neighbour is far), and on a
    # conductor's page that pad reaches the next staff's ink, so the detector
    # fires on the neighbour's notes inside this staff's crop. `glyph/p/s/9/c/5`
    # means "the 5th detection in staff 9's cell-c crop", never "a note
    # belonging to staff 9" -- and `adjudicate_glyph_owner` is the decision
    # that settles which. Until 2026-09-23 these rules did not ask: they took
    # every glyph in the crop as the staff's own and borrowed a length from
    # that staff's neighbours for ink another staff owns.
    #
    # Measured on the Litolff shared record: of 16 inferences, 2 stood on a
    # glyph ownership had already awarded elsewhere. On `glyph/4/0/9/5/7` the
    # record says `staff/4/0/10` (Basso) and the rule inferred 0.25 from
    # VIOLONCELLO's column structure; Sean read the print as a Basso eighth and
    # the reference encoding agrees (`[0.5, 0.5, 0.5]`).
    #
    # ⚠️ THE LOSER IS DROPPED, NOT RELOCATED (CLAUDE.md §10: "a resolved
    # contest DROPS the loser -- it never relocates it"). Moving the glyph into
    # the winner's bar would be a second ownership decision taken by a
    # duration rule, which is not its to take.
    #
    # ⚠️ SILENCE IS NOT A VERDICT. A glyph with NO `Q.GLYPH_OWNER` verdict was
    # never contested -- `adjudicate_glyph_owner`'s domain is the CONTESTED
    # population -- so the detection cell is the only claim there is and the
    # glyph is kept. 13 of the same 16 are in that state; widening the domain
    # is `subjects_from`'s question and not this rule's.
    owner_of: Dict[str, str] = {}
    for ov in log.verdicts(Q.GLYPH_OWNER, system,
                           scope=Scope.SELF_AND_DESCENDANTS):
        if isinstance(ov.value, str):
            owner_of[ov.subject.to_key()] = ov.value

    def _owned_here(staff: int, cell: int, g: int) -> bool:
        sub = R.glyph(system.page, system.system, staff, cell, g)
        owner = owner_of.get(sub.to_key())
        if owner is None:
            return True                       # never contested: keep
        return owner == R.staff(system.page, system.system, staff).to_key()

    out: Dict[Tuple[int, int], List[dict]] = {}
    for v in log.verdicts(Q.EVENT, system, scope=Scope.SELF_AND_DESCENDANTS):
        sub = v.subject
        if sub.cell is None or sub.staff is None or not isinstance(v.value, dict):
            continue
        for e in v.value.get("events", ()):
            glyphs = [g for g in e.get("glyphs", ())
                      if (sub.staff, sub.cell, g) in boxes
                      and _owned_here(sub.staff, sub.cell, g)]
            if not glyphs:
                continue
            xs = [boxes[(sub.staff, sub.cell, g)] for g in glyphs]
            out.setdefault((sub.staff, sub.cell), []).append(
                {"x": sum(xs) / len(xs), "glyphs": glyphs})
    for key in out:
        out[key].sort(key=lambda e: e["x"])
    return out


def _column_index(columns: Sequence[dict], x: float,
                  tol_px: float) -> Optional[int]:
    """Which column an event stands in, or None.

    ⚠️ A LOOKUP INTO A PARTITION SOMEBODY ELSE MADE, NOT A RE-CLUSTERING.
    The columns were built from exactly these points, so every point lies
    within `tol` of its own column's centre; nearest-centre-within-tolerance
    recovers that assignment. A point that matches NOTHING is returned as None
    rather than snapped to the closest column -- if the two disagree, that is
    a fact worth reporting, not one to paper over. `probe/reach.py` counts
    them.
    """
    best, best_d = None, None
    for i, c in enumerate(columns):
        d = abs(x - float(c["x_page"]))
        if d <= tol_px and (best_d is None or d < best_d):
            best, best_d = i, d
    return best


def _event_beats(log: Log, staff: int, cell: int, system: Subject,
                 glyphs: Sequence[int]) -> Tuple[Optional[float], Tuple[str, ...]]:
    """The DECIDED sounding length of one event, and the verdicts behind it.

    ⚠️ Every glyph of the event must be DECIDED and they must agree. A chord
    whose members disagree about their own length is not a witness to
    anything, and taking a majority inside it here would be a tie-break --
    which is the one thing the stage boundary says belongs in a rule that
    declares it, not in a helper.
    """
    beats: Optional[float] = None
    ids: List[str] = []
    for g in glyphs:
        sub = Subject(Kind.GLYPH, page=system.page, system=system.system,
                      staff=staff, cell=cell, glyph=g)
        v = log.verdict(Q.DURATION, sub)
        if v is None or v.outcome is not Outcome.DECIDED:
            return None, ()
        if not isinstance(v.value, dict):
            return None, ()
        b = v.value.get("beats")
        if b is None:
            return None, ()
        b = float(b)
        if beats is None:
            beats = b
        elif abs(beats - b) > 1e-9:
            return None, ()
        ids.append(v.id)
    return beats, tuple(ids)

# ─────────────────────────────────────────────────────────────────────────────
# The walk — ONE traversal, shared by both rules
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Span:
    """One NARROWED note, the stretch of time it occupies, and its bar.

    ⚠️ `end` IS THE WHOLE DIFFERENCE BETWEEN THE TWO RULES. An integer is the
    column index of this staff's own next onset; `None` means there is no
    further onset in the bar, so the note runs to the BARLINE. Everything
    else about the two claims is identical, which is why one walk serves both
    and the endpoint is a field rather than a fork in the traversal.
    """

    sub: Subject
    prior: Verdict
    staff: int
    cell: int
    k: int
    #: This note's endpoint, as `(next_column, no_events_follow)`.
    #:
    #: ⚠️⚠️ THREE STATES, NOT TWO, AND THE THIRD IS WHY THIS IS A PAIR.
    #:   `(m, False)`     -> it ends at onset column m.
    #:   `(None, True)`   -> nothing follows it in the bar: the BARLINE.
    #:   `(None, False)`  -> something follows it and that something landed
    #:                       in NO column, so where this note ends is
    #:                       UNKNOWN and both rules must decline.
    #: The first draft collapsed the last two, because it derived "runs to
    #: the barline" from *no later COLUMNED event* rather than from *no later
    #: event*. An event that misses every column centre by more than the
    #: tolerance is dropped by `_column_index` -- `probe/reach.py` counts
    #: them on the real page -- so that draft would have called a note
    #: barline-bound while an undetected-column event sat after it, and then
    #: borrowed a neighbour's whole-bar length for a note that is not whole.
    endpoint: Tuple[Optional[int], bool]
    at_col: Dict[int, Dict[int, dict]]
    #: (staff, column) -> that staff's endpoint pair, same three states.
    endpoints: Dict[Tuple[int, int], Tuple[Optional[int], bool]]
    col_v: Verdict
    bar: dict

    @property
    def end(self) -> Optional[int]:
        """The column this note ends at, or None for the barline/unknown."""
        return self.endpoint[0]

    @property
    def runs_to_barline(self) -> bool:
        return self.endpoint == (None, True)

    @property
    def endpoint_is_unknown(self) -> bool:
        """Something follows, and it landed in no column."""
        return self.endpoint == (None, False)


def _walk(log: Log, system: Subject) -> List[_Span]:
    """Every narrowed duration on this system that stands in a known column.

    ⚠️ IT DECIDES NOTHING AND REFUSES NOTHING ABOUT THE ENDPOINT. Both
    endpoints come back and each rule filters for its own, so the two reach
    numbers are taken from one population and are therefore comparable --
    which they would not be if each rule did its own traversal.
    """
    col_v = log.verdict(Q.ONSET_COLUMN, system)
    if col_v is None or col_v.outcome is not Outcome.DECIDED:
        return []
    spacing = (col_v.detail or {}).get("staff_spacing_px")
    if not spacing:
        return []
    # ⚠️ The unit is the COLUMN VERDICT'S OWN, read off its detail rather than
    # re-measured, so the lookup cannot drift from the partition it looks into.
    tol_px = float(spacing) * ONSET_COLUMN_TOLERANCE_SPACES

    bars = {int(b["measure"]): b for b in (col_v.value or {}).get("bars", ())
            if "columns" in b}
    if not bars:
        return []

    events = _events_with_x(log, system)
    out: List[_Span] = []

    for (staff, cell), evs in sorted(events.items()):
        bar = bars.get(cell)
        if bar is None:
            continue
        columns = sorted(bar["columns"], key=lambda c: float(c["x_page"]))
        # every staff's events in this bar, keyed by column index
        at_col: Dict[int, Dict[int, dict]] = {}
        endpoints: Dict[Tuple[int, int], Tuple[Optional[int], bool]] = {}
        for (st2, c2), evs2 in events.items():
            if c2 != cell:
                continue
            idx = [(_column_index(columns, e["x"], tol_px), e) for e in evs2]
            for pos, (ci, e) in enumerate(idx):
                if ci is None:
                    continue
                at_col.setdefault(ci, {})[st2] = e
                # Where THIS staff's note ends, in three states -- see
                # `_Span.endpoint`. `follow` is the next COLUMNED event;
                # `nothing_follows` is the stronger fact that there is no
                # further event of any kind, which is the only thing that
                # licenses calling this note barline-bound.
                later = idx[pos + 1:]
                follow = next((ci2 for ci2, _e in later if ci2 is not None),
                              None)
                endpoints[(st2, ci)] = (follow, not later)

        for e in evs:
            k = _column_index(columns, e["x"], tol_px)
            if k is None:
                continue
            # ⚠️⚠️ THE NEXT ONSET, NOT THE NEXT COLUMN, AND THE FIRST DRAFT HAD
            # IT WRONG. A column is an instant on the SYSTEM, so a staff
            # playing a half note while its neighbours play eighths SKIPS
            # several columns — and requiring `k + 1` therefore only ever
            # admitted the staff with the finest subdivision in the bar, which
            # is the staff least likely to have been narrowed in the first
            # place. Measured on Litolff Beethoven 5 p1-4: **335 of 356
            # narrowed durations stopped here**, and only 191 of those had no
            # next onset at all — the other 144 simply jumped.
            #
            # The claim never needed adjacency. It needs the WITNESS TO END
            # WHERE THIS NOTE ENDS: if both go from column k to column m, the
            # stretch of time is the same one for both, whatever lies between.
            # `k + 1` is just the special case m == k + 1.
            endpoint = endpoints.get((staff, k), (None, False))
            for g in e["glyphs"]:
                sub = Subject(Kind.GLYPH, page=system.page,
                              system=system.system, staff=staff, cell=cell,
                              glyph=g)
                prior = log.verdict(Q.DURATION, sub)
                if prior is None or prior.outcome is not Outcome.NARROWED:
                    continue
                out.append(_Span(sub=sub, prior=prior, staff=staff,
                                 cell=cell, k=k, endpoint=endpoint,
                                 at_col=at_col, endpoints=endpoints,
                                 col_v=col_v, bar=bar))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1 — the second instant is another ONSET COLUMN
# ─────────────────────────────────────────────────────────────────────────────


@rule(
    inference=Inference.COLLAPSE_DURATION_BY_COLUMN,
    target=Q.DURATION,
    # ⚠️⚠️ THE READS LIST IS LOAD-BEARING FOR THE SELF-CHECK, not decoration.
    # `Q.METER` is NOT here and must not be: the moment this rule reads the
    # meter or a bar sum, `probe/bar_fill.py` stops being an independent
    # invariant and becomes the quantity this rule optimises -- the fault
    # CLAUDE.md records against the tie-pairing repair. `infer.scoring_conflict`
    # computes the overlap and `probe/self_check.py` REFUSES to print a score
    # when it is non-empty.
    reads=(Q.ONSET_COLUMN, Q.EVENT, Q.DURATION, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    scope=Kind.SYSTEM,
    sideways=True,
    bound=(
        "It collapses a NARROWED duration to one of that reader's OWN "
        "candidates and nothing else; it acts only on an event that stands in "
        "a corroborated onset column k and has a next onset at some column m "
        "IN THE SAME BAR, and only on witnesses that span that same k to m; "
        "every independent witness must agree on one length, and one dissenter "
        "refuses the whole inference; where two candidates carry that length "
        "it refuses rather than choosing. It writes at most one verdict per "
        "glyph and reads no value it has written."),
    why_witnesses_are_independent=(
        "Each witness is a DIFFERENT STAFF's reading of DIFFERENT INK, and "
        "that is checked rather than asserted: `independent_groups` "
        "partitions the witness verdicts by whether their provenance closures "
        "intersect, so two staves resting on a shared row count once. ⚠️ It "
        "is ONE-SIDED -- disjoint closures prove the rows differ, they do NOT "
        "prove the readings fail independently, and two staves of one badly "
        "printed page share no row and still degrade together."),
)
def collapse_duration_by_column(log: Log, system: Subject) -> List[Proposal]:
    """A narrowed duration, settled by what the OTHER staves say.

    ⚠️⚠️ THIS IS THE THING `EVALUATE` STRUCTURALLY CANNOT DO. Every
    consequence is `cause -> effect`, vertical, from a settled decision down
    to what depends on it -- so a bar sitting in a system with eleven other
    staves playing the same stretch of time has eleven readings of it that no
    consequence may look at. Sean's efficiency argument (*"we don't need much
    info from a particular symbol because we have what we need elsewhere"*) is
    entirely horizontal, and until this rule there was nowhere for it to live.

    **The claim, stated so it can be argued with.** An onset column is an
    instant. If this staff's event stands at column k and its own next event
    stands at column m, then this note sounds for exactly the gap between
    those two instants. If a NEIGHBOURING staff also goes k -> m and its note
    there is DECIDED at d, then the gap IS d -- so this note is d too.

    ⚠️ **m, NOT k+1**, and the first draft got that wrong in a way worth
    keeping: a column is an instant on the SYSTEM, so a staff playing a half
    note while its neighbours play eighths skips columns, and adjacency
    admitted only the finest-subdivided staff in each bar. Measured, that cost
    335 of 356. See the comment at the `end` lookup in `_walk`.

    ⚠️ IT IS NOT ENTAILMENT AND THAT IS WHY IT IS HERE AND NOT IN EVALUATE.
    Three ways it can be wrong, all real: the note may be followed by a rest
    the detector never read, so its own next EVENT is not its end; the column
    grouping may have merged two instants; and a tie or a held note can cross
    a column without a new onset. Each makes the answer BEST rather than
    FORCED, which is this stage's whole remit -- and each is why the verdict
    is labelled.

    ⚠️ IT NEVER READS THE METER OR A BAR SUM. Not an accident: a bar-sum
    arbiter falls silent exactly where the reading is worst (*the bars are not
    an independent umpire over a bad reading*), and it would also make
    `bar_fill.py` -- the only self-check this stage has that needs no truth
    file -- a measurement of the quantity the rule optimises.
    """
    out: List[Proposal] = []
    for span in _walk(log, system):
        if span.end is None:
            # Either it runs to the BARLINE -- which is
            # `collapse_duration_to_barline`'s population, and needs a guard
            # this rule does not carry -- or its endpoint is UNKNOWN, which
            # is nobody's population.
            continue
        p = _propose(log, system, span,
                     reason="the_neighbours_name_this_gap")
        if p is not None:
            out.append(p)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2 — the second instant is the BARLINE
# ─────────────────────────────────────────────────────────────────────────────


@rule(
    inference=Inference.COLLAPSE_DURATION_TO_BARLINE,
    target=Q.DURATION,
    # ⚠️⚠️ `Q.METER` IS ABSENT HERE TOO, AND FOR THIS RULE THAT IS A CLAIM
    # THAT HAD TO BE EARNED RATHER THAN DECLARED. A note running to the
    # barline has the BAR's length, and the bar's length is the meter -- so
    # the obvious way to reach this population is to read `Q.METER`, and that
    # is exactly what would make `probe/bar_fill.py` a measurement of the
    # quantity this rule optimises. This rule never reads it. It borrows a
    # NEIGHBOUR'S READING of the same stretch of time, and refuses any
    # neighbour whose own reading came from the meter -- see
    # `_witness_is_meter_derived`. `infer.scoring_conflict` stays empty and
    # the self-check stays legitimate.
    reads=(Q.ONSET_COLUMN, Q.EVENT, Q.DURATION, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    scope=Kind.SYSTEM,
    sideways=True,
    bound=(
        "It collapses a NARROWED duration to one of that reader's OWN "
        "candidates and nothing else; it acts only on an event that stands in "
        "a corroborated onset column k and has NO further onset in its bar, "
        "so it runs to the barline; its witnesses are the other staves "
        "standing at that same column k that ALSO have no further onset, so "
        "they run to the SAME barline; a witness whose own length reaches "
        "`Q.METER` through its provenance closure is REFUSED, so no borrowed "
        "length is one the meter handed out; every independent witness must "
        "agree on one length, one dissenter refuses the whole inference, and "
        "where two candidates carry that length it refuses rather than "
        "choosing. It writes at most one verdict per glyph and reads no value "
        "it has written."),
    why_witnesses_are_independent=(
        "Each witness is a DIFFERENT STAFF's reading of DIFFERENT INK, "
        "checked by `independent_groups` against the provenance closures -- "
        "plus a SECOND refusal this rule needs and the column rule does not: "
        "a witness whose closure contains `Q.METER` is dropped, because a "
        "length the meter handed out is not a reading and borrowing it would "
        "launder the meter into an answer this rule claims not to read. "
        "⚠️ BOTH TESTS ARE ONE-SIDED, and here there is a NAMED correlation "
        "neither can see: the subject and its witness take their barline from "
        "the SAME CELL SEGMENTATION, so a bar cut in the wrong place is wrong "
        "for both together. That is the CONVENTION correlation CLAUDE.md "
        "records as real and unquantified, and it is one of the reasons this "
        "answer is BEST rather than FORCED."),
)
def collapse_duration_to_barline(log: Log, system: Subject) -> List[Proposal]:
    """The last note of a bar, settled by a neighbour that ends where it ends.

    ⚠️⚠️ THIS IS THE BIGGEST BUCKET IN THE FIRST RULE'S FUNNEL, AND IT WAS
    OUT OF REACH BY DESIGN RATHER THAN BY ACCIDENT. Measured on Litolff
    Beethoven 5 p1-4, **191 of 357 narrowed durations have no next onset in
    their bar** -- more than half the population, and the first rule declines
    every one of them with a comment saying why: *"its length is the bar's --
    which is the meter, which this rule may not read"*.

    **That reasoning is right about the METER and wrong about the NEIGHBOUR.**
    The note's length is indeed the gap from column k to the barline. But we
    do not have to compute that gap from the meter to know it: if a
    neighbouring staff ALSO stands at column k, ALSO has no further onset in
    the bar, and its note there is DECIDED at d, then that staff has already
    measured the same gap and called it d. The barline is a system-wide
    event, so both notes end at the same instant. The claim is the first
    rule's, with the barline standing in for column m.

    ⚠️⚠️ THE GUARD THAT MAKES IT LEGAL. A witness's length is only evidence
    if the witness READ it. Two consequences in this pipeline hand a duration
    out FROM the meter -- `size_measure_rest` (a lone whole rest takes the
    bar's length) and `reconcile_duration` (a bar that does not sum is
    re-read until it does) -- and both put the meter row in their `basis`.
    Borrowing such a length would be reading `Q.METER` through a proxy: the
    value would be meter-derived while `reads` truthfully said it was not,
    `infer.scoring_conflict` would report clean, and `bar_fill.py` would
    quietly become a measurement of this rule's own output. So a witness
    whose provenance closure contains `Q.METER` is refused, by
    `Log.quantities_in_closure` -- the same primitive `adjudicate.py` already
    uses for circularity, not a new mechanism.

    ⚠️ IT IS STILL NOT ENTAILMENT. Every hazard the first rule lists applies
    -- an unread rest, a merged column, a tie crossing without a new onset --
    and this rule adds one of its own: **the two staves share a barline
    because they share a cell segmentation**, so a mis-cut bar is mis-cut for
    witness and subject alike. That correlation is invisible to the closure
    test, is declared in `why_witnesses_are_independent`, and is why the
    answer is labelled.
    """
    out: List[Proposal] = []
    for span in _walk(log, system):
        if not span.runs_to_barline:
            # ⚠️ Two different exclusions and only one of them is rule 1's.
            # `span.end is not None` is the column case; `endpoint_is_unknown`
            # is a note followed by an event that landed in NO column, where
            # nobody knows when this note stops. Declining it is the whole
            # reason the endpoint is a pair.
            continue
        p = _propose(log, system, span,
                     reason="the_neighbours_run_to_the_same_barline",
                     meter_free_witnesses=True)
        if p is not None:
            out.append(p)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The witness gathering — ONE path, both rules
# ─────────────────────────────────────────────────────────────────────────────


def _witness_is_meter_derived(log: Log, verdict_ids: Sequence[str]) -> bool:
    """True if any of these duration verdicts reached its value via the METER.

    ⚠️⚠️ THE GUARD THAT LETS `collapse_duration_to_barline` EXIST WITHOUT
    READING `Q.METER`. `size_measure_rest` and `reconcile_duration` both put
    the meter verdict in their `basis`, so a length they handed out carries
    `Q.METER` in its provenance closure and a length the reader READ does
    not. Borrowing the former would put a meter-derived number into an answer
    whose `reads` list truthfully says it never read the meter -- the value
    would be laundered, `infer.scoring_conflict` would report clean, and
    `probe/bar_fill.py` would silently become a measurement of this rule's
    own output rather than an independent invariant.

    ⚠️ `Log.quantities_in_closure` IS BORROWED, NOT INVENTED: `adjudicate.py`
    already uses exactly this primitive for its circularity filter. A second
    implementation of provenance-walking would be a second thing to keep in
    agreement with the first.
    """
    return any(Q.METER in log.quantities_in_closure(vid) for vid in verdict_ids)


def _propose(log: Log, system: Subject, span: _Span, *, reason: str,
             meter_free_witnesses: bool = False) -> Optional[Proposal]:
    """Gather the witnesses for one narrowed glyph and propose, or not.

    ⚠️ A witness must begin at column `k` AND END WHERE THIS NOTE ENDS -- the
    same two instants. `span.end` carries the endpoint for both rules: a
    column index, or `None` for the barline. A witness that ends anywhere
    else is measuring a different stretch of time and is not a witness to
    this note's length at all.

    ⚠️ ONE FUNCTION FOR BOTH RULES ON PURPOSE. Every guard below -- unanimity,
    independence, the single-candidate requirement -- then runs for both
    claims with no chance of one rule's version drifting from the other's.
    The only difference either rule may express is `meter_free_witnesses`,
    and it is a refusal, so it can only ever make a rule speak LESS.
    """
    prior = span.prior
    votes: Dict[float, List[str]] = {}
    witness_ids: List[str] = []
    refused_meter_derived = 0

    for st2, e2 in sorted(span.at_col.get(span.k, {}).items()):
        if st2 == span.staff:
            continue
        if span.endpoints.get((st2, span.k)) != span.endpoint:
            # ⚠️ THE WHOLE PAIR, not just the column, so a witness that runs
            # to the barline is never matched against one that stops at a
            # column and vice versa.
            #
            # ⚠️⚠️ IT DOES NOT ALSO EXCLUDE THE UNKNOWN-ENDPOINT CASE, AND AN
            # EARLIER COMMENT HERE CLAIMED IT DID. Two unknown endpoints
            # compare EQUAL as `(None, False)`, so this test would happily
            # pair them. What actually keeps them apart is one layer up:
            # BOTH rules exclude an unknown SUBJECT before calling this, so
            # `_propose` is never reached with one. The exclusion is real and
            # this line is not where it lives -- and a comment claiming a
            # guard that sits elsewhere is how an unreachable branch gets
            # read as a live one.
            continue
        beats, ids = _event_beats(log, st2, span.cell, system, e2["glyphs"])
        if beats is None:
            continue
        if meter_free_witnesses and _witness_is_meter_derived(log, ids):
            # ⚠️ Its length came from the meter, so it is not a READING of
            # this gap and borrowing it would read `Q.METER` by proxy.
            refused_meter_derived += 1
            continue
        votes.setdefault(beats, []).extend(ids)
        witness_ids.extend(ids)

    if not votes:
        return None
    if len(votes) > 1:
        # ⚠️ ONE DISSENTER REFUSES THE WHOLE INFERENCE. A majority here would
        # be a tie-break on an uncalibrated count, and the disagreement is
        # itself the more useful fact: it says these staves did not read the
        # same bar.
        return None

    beats = next(iter(votes))
    groups = independent_groups(log, tuple(witness_ids))
    if len(groups) < COLUMN_MIN_INDEPENDENT_WITNESSES:
        return None

    matching = [c for c in (prior.candidates or ())
                if isinstance(c.value, dict)
                and c.value.get("beats") is not None
                and abs(float(c.value["beats"]) - beats) < 1e-9]
    if len(matching) != 1:
        # ⚠️ NONE: the neighbours name a length this reader never admitted, so
        # the reader and the neighbours disagree and the narrowing stands.
        # MORE THAN ONE: two spellings of one length, and choosing between
        # them would be a tie-break -- `reconcile_duration`'s own uniqueness
        # rule, arriving one stage later.
        return None

    return Proposal(
        subject=span.sub,
        value=matching[0].value,
        reason=reason,
        basis=(span.col_v.id,) + tuple(witness_ids),
        witnesses=tuple(witness_ids),
        detail={
            "beats": beats,
            "column": span.k,
            "measure": span.cell,
            # ⚠️ `None` HERE MEANS THE BARLINE and is not a missing value.
            # Reported so a reader of the record can tell the two claims
            # apart without consulting the rule name.
            "ends_at_column": span.end,
            "runs_to_barline": span.runs_to_barline,
            "witness_staves": sorted(
                st for st in span.at_col.get(span.k, {}) if st != span.staff),
            # ⚠️⚠️ THE FLAG AND THE COUNT, BECAUSE A LONE ZERO IS AMBIGUOUS
            # IN EXACTLY THE WAY THIS REPOSITORY KEEPS PAYING FOR. "this rule
            # checked and refused nobody" and "this rule does not check" are
            # different facts and both render as 0. The flag separates them;
            # the count is written even when zero so an absent key never
            # stands for either. Same lesson as
            # `empty_bars_padded_without_meter`, which was incremented only
            # on the bad branch and so vanished from the report exactly when
            # everything was fine.
            "refuses_meter_derived_witnesses": meter_free_witnesses,
            "witnesses_refused_meter_derived": refused_meter_derived,
            "n_candidates_before": len(prior.candidates or ()),
            # ⚠️ REPORTED, NEVER THE REASON. See hazard (a): `support` is in
            # the reader's own units and is not a probability. It is here so a
            # human can see whether the inference agreed with the reader's own
            # ordering -- which is a diagnostic, not a justification.
            "chosen_candidate_support": matching[0].support,
            "was_readers_top_candidate": bool(
                prior.candidates and prior.candidates[0].value
                is matching[0].value),
            "events_per_space": span.bar.get("events_per_space"),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3 — the unnamed block at the foot of a system
# ─────────────────────────────────────────────────────────────────────────────

#: The glyph a detected clef names, imported rather than restated.
#:
#: ⚠️ THE FIRST DRAFT OF THE PROBE THAT MEASURED THIS RULE SPELLED THEM
#: `gClef`/`fClef`/`cClef` AND MATCHED NOTHING, so it reported *"0 of 0
#: spoke"* on a document holding 91 clef rows -- a corroboration that was
#: silent because of the map rather than because of the page, and which reads
#: exactly like a plate that prints no clef. `adjudicators.clef` already holds
#: the one true map; taking a copy is how the two would drift into that
#: failure a second time.
from .adjudicators.clef import _clef_of as _clef_named_by  # noqa: E402

#: The two canonical instrument NAMES a condensed low-string staff can be.
#: ⚠️ NAMES, NOT A WORD LIST OVER MARGIN TEXT. `Q.INSTRUMENT.value["name"]`
#: is already `instruments.Instrument.name` -- the canonical spelling
#: `_reference_instruments` (identity.py) reads off the reference's OWN
#: `Q.INSTRUMENT` verdicts -- so this is a comparison of two already-resolved
#: facts, never a second lexicon.
_CELLO_NAME = "Cello"
_CONTRABASS_NAME = "Contrabass"


def _reference_instrument_names(log: Log, ref_system: Subject) -> Dict[int, str]:
    """`{staff ordinal on ref_system: instrument name}`.

    ⚠️ THE SAME READ `identity._reference_instruments` MAKES, over a `Log`
    rather than an `Evidence`, because `_place_in_family_block` already ran
    in ADJUDICATE and this rule never gets an `Evidence` for that system's
    subject. Re-deriving the name from a label string here would be a second
    resolution of a question `adjudicate_instrument` already answered --
    exactly the drift `_reference_instruments`'s own docstring is written to
    avoid.
    """
    out: Dict[int, str] = {}
    for v in log.verdicts(Q.INSTRUMENT, ref_system,
                          scope=Scope.SELF_AND_DESCENDANTS):
        sub = v.subject
        if sub.kind is not Kind.STAFF or not isinstance(v.value, dict):
            continue
        name = v.value.get("name")
        if isinstance(name, str):
            out[sub.staff] = name
    return out


def _cello_and_contrabass_slots(names: Dict[int, str], a: int,
                                b: int) -> Optional[Tuple[int, int]]:
    """`(cello slot, contrabass slot)` if `{a, b}` is exactly that pair.

    Order-independent: the reference's own listing order names which is
    which, never the position of `a` and `b` in the narrowing.
    """
    na, nb = names.get(a), names.get(b)
    if na == _CELLO_NAME and nb == _CONTRABASS_NAME:
        return a, b
    if nb == _CELLO_NAME and na == _CONTRABASS_NAME:
        return b, a
    return None


def _block_members(log: Log, system: Subject) -> Dict[int, List[Verdict]]:
    """`{block_first_ordinal: [narrowed slot verdicts, by block index]}`.

    One entry per unnamed block of this system -- in practice one, because a
    block is by definition the system's own trailing run, but keyed rather
    than assumed so that a record holding something else is reported instead
    of silently merged.
    """
    out: Dict[int, List[Verdict]] = {}
    for v in log.verdicts(Q.SLOT_INDEX, system,
                          scope=Scope.SELF_AND_DESCENDANTS):
        # ⚠️⚠️ A MEMBER THE PAGE ALREADY FORCED IS NOT A HOLE IN THE BLOCK.
        # `adjudicate_slot_index`'s constraint filter can settle some members
        # of a block outright (`forced_by_constraints`), and until 2026-09-22
        # this saw only NARROWED ones -- so a partly-settled block failed the
        # `0..k-1` cover below, the rule skipped it whole, and TWO Violas the
        # shipped path places correctly came out narrowed instead. Measured by
        # a per-staff base-vs-arm control; invisible in every aggregate.
        #
        # A decided member is admitted purely so the block RECONSTRUCTS. It is
        # never proposed for: `infer.INFERABLE` is `{NARROWED, ABSTAINED}`, so
        # the stage cannot overturn a decided verdict whatever this returns,
        # and the front-alignment below already skips `members[-1]`.
        if v.outcome is Outcome.DECIDED:
            if v.reason != "forced_by_constraints":
                continue
        elif v.outcome is not Outcome.NARROWED \
                or v.reason != "family_block_not_forced":
            continue
        d = v.detail or {}
        b0 = d.get("block_first_ordinal")
        k = d.get("block_size")
        i = d.get("block_index")
        if not isinstance(b0, int) or not isinstance(k, int) \
                or not isinstance(i, int):
            continue
        row = out.setdefault(b0, [None] * k)          # type: ignore[list-item]
        if i < len(row):
            row[i] = v
    return out


def _clef_read_on(log: Log, staff: Subject) -> Tuple[Optional[str], Tuple[str, ...]]:
    """`(the clef this staff's glyphs name, the row ids)`, or `(None, ())`.

    ⚠️ ONE ANSWER OR NONE, NEVER A VOTE. Where a staff's glyph rows name two
    different clefs this returns None: a staff that cannot agree with itself
    is not a witness, and picking its majority here would be a second clef
    DECISION sitting outside `adjudicate_clef` and disagreeing with it.

    ⚠️ THESE ARE `Q.CLEF_GLYPH` OBSERVATIONS AND NOT THE `Q.CLEF` VERDICT.
    The verdict weights the INSTRUMENT at 1.0, so consuming it to place a
    staff's instrument would close a loop; the raw detection is a reading of
    ink and closes nothing. It is also why this term lives here rather than
    in ADJUDICATE, where `Q.CLEF` is ORDER 9 against `slot_index`'s 6 and
    would simply have read `None`.
    """
    named: Dict[str, List[str]] = {}
    for o in log.rows(Q.CLEF_GLYPH, staff):
        name = _clef_named_by(str(o.value))
        if name is not None:
            named.setdefault(name, []).append(o.id)
    if len(named) != 1:
        return None, ()
    (name, ids), = named.items()
    return name, tuple(ids)


def _clef_located_on(log: Log, staff: Subject) -> Optional[str]:
    """The clef the CV LOCATOR names on this staff, or None.

    ROADMAP 2.93. ONE ANSWER OR NONE, like `_clef_read_on`: a staff whose
    locator rows name two clefs, or none, is silent here. The locator is a
    DIFFERENT reader from the detector's `Q.CLEF_GLYPH` (shape, line and
    symmetry on the ink rather than a box class), and it is consulted only to
    say whether a glyph reading that CONTRADICTS the block's expected clef
    stands alone or is itself contradicted -- never to choose a slot.
    """
    named = {str(o.value) for o in log.rows(Q.CLEF_LOCATED, staff) if o.value}
    return next(iter(named)) if len(named) == 1 else None


@rule(
    inference=Inference.COLLAPSE_SLOT_INDEX_TO_FAMILY_BLOCK,
    # ⚠️⚠️ NO FLAG (promoted 2026-10-07, roadmap 0.2c; was
    # `OMR_SLOT_FAMILY_BLOCK`) -- the one rule in this stage that has been
    # put to the PRINT most thoroughly. 25 of 25 placements correct,
    # ZERO grafts, `staff_not_identified` 783 -> 141, 562 pitched notes
    # joining the parts they belong to rather than inventing any. The two
    # duration rules below now default ON too (`OMR_INFER`, Sean 2026-09-23,
    # roadmap 2.3 -- three subjects checked against the print, all three
    # corrected by the `Q.GLYPH_OWNER` fix; see
    # `benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §7-§9). They
    # keep their OWN flag (`OMR_INFER`) rather than sharing this rule's
    # absence of one, because the duration rules are not equally evidenced.
    switch=ALWAYS_ON,
    target=Q.SLOT_INDEX,
    # ⚠️ `Q.CLEF` IS NOT HERE AND MUST NOT BE. The raw glyph is a reading of
    # ink; the verdict is an argument that already weighs the instrument this
    # rule is placing, and consuming it would close exactly the loop
    # `clef_correction.py:566` exists to prevent.
    reads=(Q.SLOT_INDEX, Q.INSTRUMENT, Q.CLEF_GLYPH),
    scope=Kind.SYSTEM,
    sideways=True,
    bound=(
        "It collapses a NARROWED slot index to one of that reader's OWN "
        "candidates and nothing else; it acts only on a staff inside a "
        "bottom-contiguous unnamed block that `adjudicate_slot_index` has "
        "already matched to the reference's trailing family run and found "
        "SHORT by exactly one slot, and only on the members ABOVE the last, "
        "since the last is where the missing slot is claimed to be. The "
        "last member is collapsed too, ONLY where its own two candidates "
        "are exactly the reference's Cello and Contrabass slots (Sean, "
        "2026-09-22: a condensed `Violoncello e Basso` staff), and never "
        "onto any other pair -- it is placed on the Cello slot and its "
        "detail names the Contrabass slot it also belongs to "
        "(`condensed_with_slot`), for EXPORT to double, never this rule. It "
        "proposes nothing at all for the whole block if any member's own "
        "clef glyph contradicts the alignment. It can move a staff onto "
        "another slot of the same family and can never move one out of the "
        "block, because every candidate the reader admitted is inside the "
        "run."),
    why_witnesses_are_independent=(
        "The witnesses are the block members' own `Q.CLEF_GLYPH` "
        "observations, one per staff. An observation's provenance closure is "
        "itself, so two staves' clef detections share no row and "
        "`independent_groups` returns one group each -- they are separate "
        "detections of separate ink. ⚠️ THEY ARE NOT INDEPENDENT OF THE "
        "PLACEMENT in the stronger sense a reader might hope: they corroborate "
        "the ALIGNMENT, which is one claim, so agreeing clefs raise "
        "confidence in that claim and do not independently establish each "
        "staff's slot. ⚠️ AND THE CORROBORATION IS HALF-BLIND ON THE ONE "
        "DOCUMENT IT IS MEASURED ON: the record holds 74 `clefG`, 17 `clefF` "
        "and ZERO `clefC`, so the ALTO clef -- the only clef that uniquely "
        "names a member of a string block -- is never read. What the bass "
        "clef still catches is a block shifted by one, which is the failure "
        "this term is here for."),
)
def collapse_slot_index_to_family_block(log: Log,
                                        system: Subject) -> List[Proposal]:
    """The missing slot of a short block is the CONDENSED PAIR at its foot.

    Sean, 2026-09-17: *"If we had 4 or 5 staves that showed up last in the
    system without a name in the margin they are almost surely strings. If
    the first 2 clefs are treble the 3rd is alto and the 4th is bass clef it
    is further reinforcement."*

    `adjudicate_slot_index` does the first half of that and stops where the
    page stops forcing it: a block that exactly fills the reference's
    trailing family run is DECIDED there, and a block one slot short is
    NARROWED, because four staves can sit on five slots five ways and
    position alone cannot choose. This rule chooses, and says so.

    **The claim.** A string section printed on four staves rather than five
    is short because the bottom two parts share one -- `Violoncello e Basso`,
    the condensation this plate prints on six systems of seven. So the
    deficit is at the FOOT of the block: every member above the last is
    front-aligned, and the last one covers both remaining slots and is left
    exactly as the reader left it.

    ⚠️⚠️ IT IS A CLAIM ABOUT ENGRAVING PRACTICE AND NOT ABOUT THIS PAGE, which
    is why it is here and not one stage earlier. Two ways it is wrong, both
    real: a tacet Violino II would put the deficit at the TOP and shift three
    staves, and a plate that condenses a DIFFERENT pair would put it in the
    middle. Neither is refuted by anything the record holds, so the answer is
    BEST rather than FORCED -- and it is labelled, and the narrowing stays in
    the log underneath it with every candidate it admitted.

    ⚠️ THE CLEF IS A TERM THAT CAN PULL INTO ABSTENTION AND IS NEVER A GATE.
    It is not consulted to CHOOSE a slot -- the alignment does that -- it is
    consulted to CONTRADICT one, and a block with no clef readings at all is
    inferred exactly as before. That asymmetry is deliberate: a clef that
    agrees adds nothing the alignment did not already claim, while a clef
    that disagrees is the one signal here that is not downstream of the
    margin labels.

    ⚠️ THE REFUSAL IS WHOLE-BLOCK. One contradicting clef withdraws the
    inference from every member, because the alignment is ONE claim: if the
    third staff is in bass clef where the run says alto, the block is shifted
    and the two staves above it are wrong too. Refusing only the
    contradicting member would keep the two errors the contradiction is
    evidence for.
    """
    out: List[Proposal] = []
    for b0, members in sorted(_block_members(log, system).items()):
        if any(m is None for m in members):
            # A block whose narrowings do not cover `0..k-1` is not the shape
            # this rule reasons about. Reported by absence rather than
            # guessed around.
            continue
        # ⚠️ THE RUN COMES FROM WHICHEVER MEMBER STILL CARRIES IT, not from
        # `members[0]`. Every member's detail holds the same run -- they are
        # one claim about one block -- but a member the constraint filter
        # decided carries it only when it was narrowed first, so keying on the
        # first member would reintroduce exactly the hole this admits.
        detail = next((m.detail for m in members
                       if (m.detail or {}).get("run")), None) or {}
        run = list(detail.get("run") or ())
        run_clefs = list(detail.get("run_clefs") or ())
        if len(run) != len(members) + 1:
            # The reader admitted a deficit this rule does not claim to
            # resolve. `FAMILY_BLOCK_MAX_DEFICIT` already holds it to one;
            # this is the same statement made where the value is used.
            continue

        reads = [_clef_read_on(log, m.subject) for m in members]
        conflict = None
        overruled: List[str] = []
        witnesses: List[str] = []
        for i, (name, ids) in enumerate(reads):
            if name is None:
                continue
            want = run_clefs[i] if i < len(run_clefs) else None
            if want is None:
                continue
            if name != want:
                # ⚠️⚠️ ROADMAP 2.93. A DETECTOR GLYPH THE LOCATOR CONTRADICTS
                # IS NOT A WITNESS. On Litolff the detector files `clefG` on
                # the VIOLA staff (the printed C clef, mis-classed) of five
                # systems; the CV locator reads `alto` there and so does
                # `Q.CLEF`. Taking the glyph alone as "a contradicting clef"
                # withdrew the WHOLE block -- five bottom string staves held
                # out as `staff_not_identified` while 15 identical systems
                # were doubled. Two readers disagreeing is "cannot tell"
                # (rule 8): this staff speaks neither for nor against, exactly
                # as a staff carrying two glyph names does. Where the locator
                # does NOT name the expected clef (agrees with the glyph, names a
                # third clef, or is silent) the contradiction stands as before.
                located = _clef_located_on(log, members[i].subject)
                if located == want:
                    overruled.append(members[i].subject.to_key())
                    continue
                conflict = {"block_index": i, "read": name, "expected": want,
                            "staff": members[i].subject.to_key()}
                break
            witnesses.extend(ids)
        if conflict is not None:
            continue

        for i, m in enumerate(members[:-1]):
            d = m.detail or {}
            if d.get("front_aligned") is None:
                # a member already settled carries no front-aligned slot to
                # propose, and must not be proposed for in any case.
                continue
            out.append(Proposal(
                subject=m.subject,
                value=int(d.get("front_aligned")),
                reason="the_short_block_is_condensed_at_its_foot",
                basis=tuple(witnesses),
                witnesses=tuple(witnesses),
                detail={
                    "block_size": d.get("block_size"),
                    "block_index": i,
                    "family": d.get("family"),
                    "instrument": d.get("instrument"),
                    "run": run,
                    # ⚠️ WRITTEN EVEN WHEN ZERO, and the flag beside it, for
                    # the reason rule 2 records: "checked and found nothing
                    # to contradict me" and "did not check" both render as 0.
                    "clefs_read_in_block": sum(1 for n, _ in reads
                                               if n is not None),
                    "clefs_agreeing": len(witnesses),
                    "refuses_on_a_contradicting_clef": True,
                    # ROADMAP 2.93: staves whose glyph contradicted the run
                    # and was itself contradicted by the CV locator (the
                    # locator named the EXPECTED clef) -- not witnesses.
                    "clef_glyph_overruled_by_locator": list(overruled),
                    # ⚠️ The member this rule DECLINES, named so a reader of
                    # the record can see the condensed pair was left alone
                    # rather than missed.
                    "member_left_narrowed": members[-1].subject.to_key(),
                }))

        # ⚠️⚠️ THE LAST MEMBER -- SEAN, 2026-09-22, AFTER THE PRINT
        # (`benchmarks/omr-cello-bass-convention-2026-09/FINDINGS.md`): "the
        # string family always includes all five; if there are only four
        # lines the bass is doubling the celli or it comes in later." A block
        # short by one is short at its FOOT (the front-aligning claim just
        # above), and the two slots the deficit leaves the FOOT staff
        # standing on are therefore adjacent in the reference -- when that
        # pair is exactly [Cello, Contrabass] the staff is not merely one OF
        # them, it is the condensed line BOTH sections play. That is still a
        # claim about engraving practice and not about this page, so it is
        # collapsed here, labelled, exactly like every other member -- and
        # placed on the CELLO slot, never invented as a third option, because
        # `Ruling.narrow` never admitted one. `condensed_with_slot` names the
        # Contrabass slot it also belongs to; EXPORT reads that detail to
        # double the line, not this rule -- see `staged/export.py`'s
        # `_condensed_doubling`.
        #
        # ⚠️ NO NEW EVIDENCE IS CONSULTED. The pair comes from `run`, already
        # read off the SAME reference this block's clef witnesses were
        # checked against, so a document whose reference prints no Contrabass
        # at all -- or condenses a different pair -- proposes nothing here,
        # exactly as `_cello_and_contrabass_slots` refuses any other pair.
        last = members[-1]
        if len(run) >= 2:
            names = _reference_instrument_names(
                log, Subject.from_key(str((last.detail or {}).get("reference"))))
            slots = _cello_and_contrabass_slots(names, run[-2], run[-1])
            if slots is not None:
                cello_slot, contrabass_slot = slots
                d = last.detail or {}
                out.append(Proposal(
                    subject=last.subject,
                    value=int(cello_slot),
                    reason="a_condensed_violoncello_e_basso_staff_takes_the_cello_slot",
                    basis=tuple(witnesses),
                    witnesses=tuple(witnesses),
                    detail={
                        "block_size": d.get("block_size"),
                        "block_index": d.get("block_index"),
                        "family": d.get("family"),
                        "instrument": names.get(cello_slot),
                        "run": run,
                        "clefs_read_in_block": sum(1 for n, _ in reads
                                                   if n is not None),
                        "clefs_agreeing": len(witnesses),
                        "refuses_on_a_contradicting_clef": True,
                        "clef_glyph_overruled_by_locator": list(overruled),
                        # ⚠️ THE ONE DETAIL EXPORT READS. A staff placed here
                        # is doubled onto this slot too, an octave down,
                        # with `condensed_from` naming the source staff in
                        # the doubled part's own report entry.
                        "condensed_with_slot": int(contrabass_slot),
                    }))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4 — the clef nobody could read, on a part the record has already placed
# ─────────────────────────────────────────────────────────────────────────────

#: The prior outcomes this rule will speak into.
#:
#: ⚠️⚠️ ROADMAP 2.10b WIDENED THIS FROM ABSTAINED-ONLY (`benchmarks/omr-no-
#: pitch-2026-09/FINDINGS.md` §2: `staff/6/1/9` on the Litolff whole-movement
#: record narrowed to a genuine 3-way tie under 2.11b and stayed `no_pitch`
#: forever, because the old exclusion below gave it nowhere to go). A
#: NARROWED clef means `adjudicate_clef` READ the staff, scored two or more
#: candidates and could not separate them under `MARGIN_FLOOR` -- that
#: contest, and its own floor, are NOT re-argued here. This rule still never
#: overturns it by re-scoring; it only asks whether the SAME evidence ladder
#: as the abstained case -- (2) the same part's clef DECIDED on other
#: systems, (3) the instrument's conventional header clef -- lands on a value
#: the contest ITSELF already kept as a candidate. Where it does not, the
#: narrowing is declined exactly as before (CLAUDE.md §4a: INFER may collapse
#: a NARROWED verdict only to one of that reader's OWN candidates, never
#: overturn a DECIDED one, and never widen the field -- `infer._admit`
#: enforces the second half by raising `ValueNotAdmitted`; this rule enforces
#: the first half itself, by name, so a decline reads as a decline rather
#: than crashing the stage).
_CLEF_GAP_PRIORS: Tuple[Outcome, ...] = (Outcome.ABSTAINED, Outcome.NARROWED)


@dataclass(frozen=True)
class _ClefGap:
    """What this rule concluded about ONE staff, proposed or not.

    ⚠️ A RECORD OF THE DECLINES AS WELL AS THE FILLS, because the roadmap
    gate is *"inferred by (2) / by (3) / still abstained, with reasons"* and a
    rule that returns only its proposals cannot answer the third column. The
    probe reads THIS rather than re-deriving the population beside the rule,
    which is how a benchmark's own copy of a refusal table came to report 542
    where the exporter refused 738.
    """

    staff: Subject
    #: `clef_from_other_systems` | `clef_from_instrument_convention` |
    #: a decline word
    outcome: str
    value: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    basis: Tuple[str, ...] = ()
    witnesses: Tuple[str, ...] = ()


def _part_of(log: Log, staff: Subject) -> Tuple[Optional[int], Optional[str],
                                                Tuple[str, ...]]:
    """`(slot, instrument name, the verdict ids that said so)` for one staff.

    ⚠️⚠️ THE SLOT IS THE PART AND THE NAME IS ONLY A LABEL ON IT. Sean's rule
    says *"a part whose instrument is decided"*, and on the document this was
    built for `Q.INSTRUMENT` ABSTAINS on all 9 staves whose clef abstained --
    the Viola prints no margin label on those systems, which is the same fault
    twice over. What IS decided there is `Q.SLOT_INDEX`, which is the
    document-wide part the staff sits on, and its detail carries the
    reference's own name for that slot. So the identity this rule requires is
    the SLOT, and the name is read off whichever verdict carries one.

    A staff with no decided slot has no part, and this returns `(None, ...)`.
    """
    slot = log.verdict(Q.SLOT_INDEX, staff)
    if slot is None or slot.outcome is not Outcome.DECIDED \
            or not isinstance(slot.value, int):
        return None, None, ()
    used = [slot.id]
    name = None
    inst = log.verdict(Q.INSTRUMENT, staff)
    if inst is not None and inst.outcome is Outcome.DECIDED \
            and isinstance(inst.value, dict):
        name = inst.value.get("name")
        used.append(inst.id)
    if not name:
        name = (slot.detail or {}).get("instrument")
    return int(slot.value), (str(name) if name else None), tuple(used)


def _clef_reads_by_slot(log: Log) -> Dict[int, List[Verdict]]:
    """`{slot: [the DECIDED clef verdicts of every staff on that slot]}`.

    ⚠️ DECIDED ONLY. A narrowed or abstained clef is not a read, and a rule
    that tallied them would be counting the very silence it exists to fill.
    """
    out: Dict[int, List[Verdict]] = {}
    for staff in log.subjects(Kind.STAFF):
        clef = log.verdict(Q.CLEF, staff)
        if clef is None or clef.outcome is not Outcome.DECIDED \
                or not isinstance(clef.value, str):
            continue
        slot = log.verdict(Q.SLOT_INDEX, staff)
        if slot is None or slot.outcome is not Outcome.DECIDED \
                or not isinstance(slot.value, int):
            continue
        out.setdefault(int(slot.value), []).append(clef)
    return out


def clef_gap_census(log: Log) -> List[_ClefGap]:
    """Every staff whose clef ABSTAINED or NARROWED, and what this rule
    makes of it (roadmap 2.10b widened this from abstained-only).

    ⚠️ THE RULE'S WHOLE BODY LIVES HERE and the rule below is only the part
    that turns fills into `Proposal`s. One function, so the probe and the rule
    cannot disagree about the population, the tally or the tier -- the fault
    `omr-cleanup-count-2026-09/build_sheet.py` paid for by keeping its own
    copy of "the three refusals" and reporting 542 where the exporter refused
    738.
    """
    from ..instruments import instrument_named

    reads = _clef_reads_by_slot(log)
    out: List[_ClefGap] = []
    for staff in log.subjects(Kind.STAFF):
        clef = log.verdict(Q.CLEF, staff)
        if clef is None:
            continue
        if clef.outcome not in _CLEF_GAP_PRIORS:
            # ⚠️ A DECIDED clef is a READING and is never overruled (rule 3 of
            # the stage, enforced again by `_admit`). DECLINED here rather
            # than left to the harness, so the census can name it.
            out.append(_ClefGap(
                staff, f"declined_prior_is_{clef.outcome.value}"))
            continue

        # ⚠️⚠️ ROADMAP 2.10b. A NARROWED clef carries its own surviving
        # candidates, and EVERY value this rule proposes below for such a
        # staff must be one of them -- `admitted` is empty for an ABSTAINED
        # prior (it kept none), which is exactly why the checks below only
        # fire `if narrowed`.
        narrowed = clef.outcome is Outcome.NARROWED
        admitted = _candidate_values(clef) if narrowed else ()

        slot, name, part_rows = _part_of(log, staff)
        if slot is None:
            out.append(_ClefGap(staff, "declined_part_not_decided"))
            continue

        # ── (2) the same part, read on OTHER systems of this document ───────
        others = [v for v in reads.get(slot, ())
                  if v.subject.to_key() != staff.to_key()]
        tally: Dict[str, int] = {}
        for v in others:
            tally[str(v.value)] = tally.get(str(v.value), 0) + 1
        if tally:
            ranked = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
            if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
                # ⚠️ SEAN: *"a split abstains"*. Not the alphabetical winner,
                # not the closest system, and NOT the instrument's convention
                # either -- a part the document disagrees with itself about is
                # not a part this rule knows the clef of, and falling through
                # to tier (3) would answer a contested question with a weaker
                # kind of evidence than the one that failed to settle it.
                out.append(_ClefGap(staff, "split", None,
                                    {"slot": slot, "instrument": name,
                                     "tally": tally}))
                continue
            won = ranked[0][0]
            if narrowed and not any(_same_value(won, v) for v in admitted):
                # ⚠️⚠️ ROADMAP 2.10b, RULE 4 OF THE STAGE, ENFORCED HERE BY
                # NAME rather than by letting `_admit` raise. The other
                # systems agree on a clef this staff's OWN contest never kept
                # as a candidate -- proposing it would be widening the field,
                # which CLAUDE.md §4a reserves for ADJUDICATE. The narrowing
                # stands, exactly as `declined_prior_is_narrowed` used to
                # leave EVERY narrowed staff, except now it is named WHY.
                out.append(_ClefGap(
                    staff, "declined_not_a_candidate", won,
                    {"slot": slot, "instrument": name, "tally": tally,
                     "tier": "other_systems", "candidates": list(admitted)}))
                continue
            witnesses = tuple(v.id for v in others if str(v.value) == won)
            out.append(_ClefGap(
                staff, "clef_from_other_systems", won,
                {"slot": slot, "instrument": name, "tally": tally,
                 "n_systems_read": len(others),
                 "n_agreeing": ranked[0][1],
                 # ⚠️ WRITTEN EVEN WHEN THE SLOT ITSELF WAS INFERRED. On
                 # Litolff p3 the Viola's `Q.SLOT_INDEX` is
                 # `infer:collapse_slot_index_to_family_block`, so this clef
                 # rests on another inference -- legible from the basis, and
                 # named here so it does not have to be walked for.
                 "part_from_an_inference": any(
                     str(getattr(log.row(r), "decider", "") or "").startswith(
                         "infer:") for r in part_rows)},
                basis=part_rows + witnesses, witnesses=witnesses))
            continue

        # ── (3) the instrument's conventional header clef ───────────────────
        inst = instrument_named(name) if name else None
        if inst is None:
            out.append(_ClefGap(staff, "declined_no_instrument_name",
                                None, {"slot": slot, "name": name}))
            continue
        conv = str(inst.default_clef)
        if narrowed and not any(_same_value(conv, v) for v in admitted):
            # ⚠️ Same guard as tier (2), roadmap 2.10b: a bare convention with
            # no witness on the page is weaker evidence than the reader's own
            # contest and may not widen it either.
            out.append(_ClefGap(
                staff, "declined_not_a_candidate", conv,
                {"slot": slot, "instrument": inst.name,
                 "tier": "instrument_convention", "candidates": list(admitted)}))
            continue
        out.append(_ClefGap(
            staff, "clef_from_instrument_convention", conv,
            {"slot": slot, "instrument": inst.name,
             # ⚠️ NAMED AS A CONVENTION AND NOT AS A WITNESS. Nothing on this
             # page was read to reach this answer; the `instrument_header_clef`
             # entry in `tools/omr/conventions.py` is the claim being made.
             "convention": "instrument_header_clef",
             "n_systems_read": 0},
            basis=part_rows, witnesses=()))
    return out


@rule(
    inference=Inference.FILL_CLEF_GAP,
    # ⚠️ NO FLAG (promoted 2026-10-07, roadmap 0.2c; was `OMR_CLEF_GAP`):
    # this rule's evidence is neither the duration rules' nor the family
    # block's, and it stays registered apart from `OMR_INFER`.
    switch=ALWAYS_ON,
    target=Q.CLEF,
    # ⚠️ `Q.CLEF` IS IN `reads` AND THAT IS THE POINT: tier (2) is other
    # staves' CLEF VERDICTS, which is the sideways read EVALUATE structurally
    # cannot make. It is not a loop -- `Log.record`'s `UphillConsequence`
    # guard refuses a verdict that reaches its own prior, and no staff is ever
    # its own witness (`v.subject != staff` above).
    reads=(Q.CLEF, Q.SLOT_INDEX, Q.INSTRUMENT),
    scope=Kind.DOCUMENT,
    sideways=True,
    bound=(
        "It speaks ONLY where `adjudicate_clef` ABSTAINED or NARROWED and "
        "the staff's `Q.SLOT_INDEX` is DECIDED. A DECIDED clef is never "
        "touched. A NARROWED clef's own contest is never re-argued -- "
        "roadmap 2.10b bounds this rule's answer to that contest's OWN "
        "surviving candidates (CLAUDE.md §4a); a tier's answer that is not "
        "one of them is declined `declined_not_a_candidate` and the "
        "narrowing stands. The value is either (2) the MAJORITY of the "
        "clefs DECIDED on the same slot on OTHER systems of this document "
        "-- a tie for top abstains, and no other-system read means no "
        "tier-(2) answer -- or, where no other system decided one, (3) the "
        "`default_clef` of the instrument the record already named for "
        "that slot, read from `tools/omr/instruments.py` and never typed "
        "here. It proposes one clef per staff, invents no value, moves no "
        "glyph and writes no pitch: the pitches are `restate_pitch`'s, "
        "reached by `evaluate.run_over` over this verdict alone."),
    why_witnesses_are_independent=(
        "Tier (2)'s witnesses are OTHER STAVES' `Q.CLEF` verdicts, one per "
        "system, each resting on that system's own header ink -- so "
        "`independent_groups` normally returns one group per system and the "
        "count is recorded on the verdict as `n_independent_witnesses`. "
        "⚠️⚠️ AND THIS IS EXACTLY WHERE HAZARD (b) BITES, SO THE NUMBER IS "
        "COMPUTED RATHER THAN CLAIMED: `adjudicate_clef` has a CARRY term, so "
        "a clef read once and carried down a document is one signal wearing "
        "N hats, and the closure partition is what says which. This rule does "
        "NOT gate on that count, because Sean's rule is stated over the "
        "READS ('the majority of those decided reads; a split abstains') and "
        "adding an independence floor he did not ask for would silently "
        "refuse the Viola this item exists to repair. The partition and the "
        "full tally both ride on the verdict, so a reader can see whether 14 "
        "witnesses were 14 or 1. ⚠️ Tier (3) has NO witness at all and says "
        "so: `witnesses=()`, `n_systems_read: 0`, and a `convention` key "
        "naming the registry entry. It is a claim about engraving practice, "
        "which is what this stage is for and what the label is for."),
)
def fill_clef_gap(log: Log, document: Subject) -> List[Proposal]:
    """An unread clef on a placed part: other systems first, then convention.

    Sean, 2026-09-23: *"yes — viola staff with unreadable clef reads as alto
    and it should check other systems if the alto clef can be found"*.

    ⚠️⚠️ ROADMAP 2.10b, `benchmarks/omr-no-pitch-2026-09/FINDINGS.md` §2. The
    Litolff whole-movement `no_pitch` diagnosis found a NARROWED clef
    (`staff/6/1/9`, a genuine 3-way tie under 2.11b's off-staff discount)
    that this rule had never been ABLE to fill, structurally, because
    `_CLEF_GAP_PRIORS` used to admit only an abstention. That staff's other
    systems settle it outright, so the ladder now speaks to a NARROWED prior
    too -- bounded, per `clef_gap_census`, to that contest's OWN surviving
    candidates. A clef that could not be read AT ALL (abstained) and a clef
    that was read into an unresolved tie (narrowed) reach the SAME two-tier
    ladder here; only the bound they are each checked against differs.

    **Why it is an inference and not a reading.** On Litolff page 3 the alto
    C-clef is MERGED into the staff lines by the plate and the detector boxed
    it as two noteheads, so `adjudicate_clef` ends with no candidate at all
    and abstains `no_candidates`. `restate_pitch` then produces nothing for
    the staff -- correctly, because a positional default is right about half
    the time -- and all 48 detected heads die at EXPORT, 40 of them under
    `no_pitch`. That is the whole of the page's `no_pitch` refusals on ONE
    staff (`benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md`).

    **What makes the answer available.** §10: *a clef is printed at the start
    of every system*, and a part's clef is stable across systems unless a
    change is printed. The same part one system down reads its alto clef and
    writes 24 of 27 boxes. So the document already holds a reading of this
    part's clef; nothing read it.

    ⚠️⚠️ IT IS A CLAIM AND NOT A DEDUCTION, WHICH IS WHY IT IS HERE. A clef
    CHANGE is printed, and a part that changes clef mid-movement -- a bassoon
    going to tenor, a cello to treble -- is exactly the case where the other
    systems say the wrong thing with a large majority. Nothing the record
    holds refutes that here, so the answer is BEST rather than FORCED; it is
    labelled, and the abstention stays in the log underneath it.

    ⚠️ IT MUST RUN AFTER `collapse_slot_index_to_family_block`, and it does
    because `infer.run` walks `RULES` in REGISTRATION order and this file is
    read top to bottom. On Litolff all 9 of the staves it repairs are placed
    by that rule; registered first, this one would find no decided slot and
    report a clean, false zero. `test_infer_clef_gap` pins the order.
    """
    return [Proposal(subject=g.staff, value=g.value, reason=g.outcome,
                     basis=g.basis, witnesses=g.witnesses,
                     detail=dict(g.detail or {}))
            for g in clef_gap_census(log)
            if g.outcome in ("clef_from_other_systems",
                             "clef_from_instrument_convention")]


# ─────────────────────────────────────────────────────────────────────────────
# Rule 5 — the key the document reads, on a staff whose own reading is a gap
# ─────────────────────────────────────────────────────────────────────────────

#: The prior outcomes this rule will speak into.
#:
#: ⚠️ ABSTAINED ONLY, and `NARROWED` is absent because `adjudicate_key_
#: signature` never narrows: a key is read or it is not. The constant is
#: written out anyway, beside `_CLEF_GAP_PRIOR`, so that a future narrowing
#: reader has to come here and decide rather than inherit an answer.
_PART_KEY_PRIOR = Outcome.ABSTAINED


@dataclass(frozen=True)
class _KeyGap:
    """What this rule concluded about ONE staff, proposed or not.

    ⚠️ A RECORD OF THE DECLINES TOO, for `clef_gap_census`' reason: a rule
    that returns only its proposals cannot answer *"and what about the rest"*,
    and the benchmark then grows its own copy of the population, which is how
    one reported 542 where the exporter refused 738.
    """

    staff: Subject
    #: `key_from_document_majority` | `key_from_other_systems` | a decline word
    outcome: str
    value: Optional[int] = None
    detail: Optional[Dict[str, Any]] = None
    basis: Tuple[str, ...] = ()
    witnesses: Tuple[str, ...] = ()


def _staff_offset(log: Log, staff: Subject) -> Optional[int]:
    """This staff's `fifths_offset`, but only where a LABEL stated it.

    ⚠️⚠️ THE TRANSPOSITION MUST BE **READ**, NEVER DEFAULTED, and the test is
    `key_consensus.resolve_label`'s third value, imported rather than
    restated: comparing the matched offset against the instrument's default
    cannot tell *named B-flat* from *defaulted to B-flat*, the default
    clarinet being the B-flat one. `adjudicators/header._transposition` runs
    the identical test off `Evidence`; this is the `Log` side of the same
    question and both call `resolve_label`, so the two cannot diverge on
    which staves may be spoken for.
    """
    from ..key_consensus import (MAY_DIFFER_NOT_A_WITNESS,
                                 NO_SIGNATURE_CONVENTION, resolve_label)
    rows = log.rows(Q.MARGIN_LABEL, staff)
    if not rows:
        return None
    name, offset, known = resolve_label(str(rows[-1].value))
    if name is None or offset is None or not known:
        return None
    if name in NO_SIGNATURE_CONVENTION or name in MAY_DIFFER_NOT_A_WITNESS:
        return None
    return int(offset)


def _key_witnesses(log: Log, want: int, *, slot: Optional[int],
                   concert: bool) -> Tuple[str, ...]:
    """The DECIDED key verdicts that read `want`, as verdict ids.

    ⚠️⚠️ THE WITNESSES ARE THE OTHER STAVES' OWN VERDICTS, not a number this
    rule computed. Hazard (b) is live here and the partition is what answers
    it: `independent_groups` will merge any two of these that rest on a
    shared row, so `n_independent_witnesses` can come back far below
    `n_witnesses` and a reader can see it. ⚠️ And it rules out only the
    correlation the RECORD can see: a plate that merges its flats merges them
    on every system, and two staves of one bad plate share no row while
    failing together. That is CLAUDE.md §10's unquantified correlation and
    this rule cannot repair it — it is named on the verdict rather than
    argued away.
    """
    out = []
    for staff in log.subjects(Kind.STAFF):
        key = log.verdict(Q.KEY_SIGNATURE, staff)
        if key is None or key.outcome is not Outcome.DECIDED \
                or not isinstance(key.value, int):
            continue
        if concert:
            offset = _staff_offset(log, staff)
            if offset is None or int(key.value) - offset != want:
                continue
        else:
            sv = log.verdict(Q.SLOT_INDEX, staff)
            if sv is None or sv.outcome is not Outcome.DECIDED \
                    or sv.value != slot or int(key.value) != want:
                continue
        out.append(key.id)
    return tuple(out)


def part_key_census(log: Log) -> List[_KeyGap]:
    """Every staff whose key ABSTAINED, and what this rule makes of it.

    ⚠️ THE RULE'S WHOLE BODY LIVES HERE and the rule below only turns fills
    into `Proposal`s — `clef_gap_census`' discipline, so the probe and the
    rule cannot disagree about the population, the tally or the tier.

    ⚠️⚠️ AND THE VALUE IS `header.expected_fifths`', NOT A SECOND COPY OF THE
    TIER ORDER. `adjudicate_key_signature` abstained this staff because its
    reading disagreed with what that function returned; computing the fill a
    second way here would let the check abstain on one value and the
    inference write another — a contradiction with nothing in the file to
    show for it. One function, two stages.
    """
    from .adjudicators.header import effective_offset, expected_fifths

    part_key = log.verdict(Q.PART_KEY, R.DOCUMENT)
    out: List[_KeyGap] = []
    for staff in log.subjects(Kind.STAFF):
        key = log.verdict(Q.KEY_SIGNATURE, staff)
        if key is None:
            continue
        if key.outcome is not _PART_KEY_PRIOR:
            out.append(_KeyGap(staff, f"declined_prior_is_{key.outcome.value}"))
            continue
        if part_key is None or part_key.outcome is not Outcome.DECIDED:
            out.append(_KeyGap(staff, "declined_no_document_key"))
            continue
        slot_v = log.verdict(Q.SLOT_INDEX, staff)
        slot = (int(slot_v.value)
                if slot_v is not None and slot_v.outcome is Outcome.DECIDED
                and isinstance(slot_v.value, int) else None)
        # ⚠️ THE EFFECTIVE OFFSET, NOT THIS STAFF'S OWN LABEL. The check used
        # the part's where the staff printed none, and an inference computing
        # it differently would fill a staff with a value the check never
        # abstained it for.
        offset = effective_offset(part_key.value, slot,
                                  _staff_offset(log, staff))
        sys_key = (staff.page or 0, staff.system or 0)
        want, tier = expected_fifths(part_key.value, slot, offset, sys_key)
        if want is None:
            out.append(_KeyGap(staff, "declined_" + tier,
                               None, {"slot": slot, "offset": offset}))
            continue
        basis = [part_key.id]
        if slot_v is not None:
            basis.append(slot_v.id)
        if tier == "document_majority":
            witnesses = _key_witnesses(log, want - int(offset), slot=None,
                                       concert=True)
            outcome = "key_from_document_majority"
        else:
            witnesses = _key_witnesses(log, want, slot=slot, concert=False)
            outcome = "key_from_other_systems"
        out.append(_KeyGap(
            staff, outcome, int(want),
            {"slot": slot, "fifths_offset": offset, "tier": tier,
             "abstained_because": key.reason,
             # ⚠️ WHAT THE STAFF ITSELF READ, carried onto the inference so a
             # reader sees the dissent beside the value that replaced it
             # without walking back to the superseded row.
             "staff_read": (key.detail or {}).get("written_fifths"),
             "document_segments": (part_key.value or {}).get("document"),
             "part_from_an_inference": bool(
                 slot_v is not None
                 and str(getattr(slot_v, "decider", "") or "").startswith(
                     "infer:"))},
            basis=tuple(basis) + witnesses, witnesses=witnesses))
    return out


@rule(
    inference=Inference.FILL_PART_KEY,
    # ⚠️ ITS OWN FLAG, DEFAULT ON. See `infer.PART_KEY_ENV`.
    switch=PART_KEY_SWITCH,
    target=Q.KEY_SIGNATURE,
    # ⚠️ `Q.KEY_SIGNATURE` IS IN `reads` AND THAT IS THE POINT, exactly as
    # `Q.CLEF` is for the clef-gap rule: the witnesses are OTHER staves' key
    # verdicts, which is the sideways read EVALUATE structurally cannot make.
    # Not a loop — `Log.record`'s `UphillConsequence` guard refuses a verdict
    # that reaches its own prior, and no staff is ever its own witness (a
    # witness must be DECIDED and this rule only speaks where it is not).
    reads=(Q.KEY_SIGNATURE, Q.PART_KEY, Q.SLOT_INDEX, Q.MARGIN_LABEL),
    scope=Kind.DOCUMENT,
    sideways=True,
    bound=(
        "It speaks ONLY where `adjudicate_key_signature` ABSTAINED. A DECIDED "
        "key is never touched. The value is `header.expected_fifths`' and no "
        "other: (2) the DOCUMENT-WIDE majority of the concert keys the record "
        "DECIDED over this stretch of systems, re-transposed by THIS staff's "
        "own READ `fifths_offset` — unavailable to a staff whose margin label "
        "never stated one — or (3) the majority of the WRITTEN keys the same "
        "PART's other systems decided. A tie abstains at both tiers and the "
        "stretch boundaries are `Q.PART_KEY`'s, so a corroborated key CHANGE "
        "is never flattened. It proposes one key per staff, invents no value, "
        "moves no glyph and writes no accidental: the re-spellings are "
        "`respell_accidental`'s, reached by `evaluate.run_over` over this "
        "verdict alone."),
    why_witnesses_are_independent=(
        "The witnesses are OTHER STAVES' `Q.KEY_SIGNATURE` verdicts, each "
        "resting on its own system's header ink and its own detector cell — "
        "so `independent_groups` normally returns one group per staff and the "
        "count rides on the verdict as `n_independent_witnesses`. ⚠️⚠️ AND "
        "HAZARD (b) BITES HERE IN A FORM THE PARTITION CANNOT SEE, so it is "
        "stated rather than computed away: a plate that MERGES its flats "
        "merges them on every system, and two staves of one bad plate share "
        "no row while failing together (CLAUDE.md §10, measured on Litolff in "
        "`benchmarks/omr-key-majority-2026-09/FINDINGS.md` §6a, where three "
        "staves of one system corroborated the same wrong −1). What makes "
        "the DOCUMENT tier survivable where the SYSTEM tier did not is "
        "population: it tallies every readable staff of every system of the "
        "movement, so a correlated misreading has to hold across pages and "
        "not merely across one header. The rule does NOT gate on the "
        "independent count — Sean's rule is stated over the reads — and the "
        "full tally rides on `Q.PART_KEY` so a reader can see whether a "
        "majority of 200 was 200 or 3."),
)
def fill_part_key(log: Log, document: Subject) -> List[Proposal]:
    """The document's own key, on a staff whose reading was a gap or a dissent.

    Sean, 2026-09-23, adjudicating 2.9's four system-header crops: *"all 4 of
    those crops are pieces with 3 flats and the staffs that have fewer flats
    are transposing clefs."* Both works are in C minor and both count pages
    print three flats on every non-transposing staff — and the 2.9 reader is
    wrong on 20 of 46 of them, with the wrong values scattered (+2, −4, +1)
    while the right one repeats.

    **Why it is an inference and not a reading.** Nothing on this staff's own
    header was read differently by this rule; the answer comes from OTHER
    staves, on other systems, whose ink this staff's reader never saw. It is
    BEST rather than FORCED, and a movement that really does change key on
    some parts and not others would make it wrong — which is why the stretch
    boundaries come from `Q.PART_KEY`'s corroborated changes and not from
    this rule, and why the abstention stays in the log underneath the fill.

    ⚠️ IT MUST RUN AFTER `collapse_slot_index_to_family_block`, and it does
    because `infer.run` walks `RULES` in REGISTRATION order and this file is
    read top to bottom: tier (3) needs a decided `Q.SLOT_INDEX`, and on
    Litolff 28 of them are that rule's. Registered first, this one would find
    fewer parts and report a clean, false number. `test_infer_part_key` pins
    the order.
    """
    return [Proposal(subject=g.staff, value=g.value, reason=g.outcome,
                     basis=g.basis, witnesses=g.witnesses,
                     detail=dict(g.detail or {}))
            for g in part_key_census(log)
            if g.outcome in ("key_from_document_majority",
                             "key_from_other_systems")]



# ─────────────────────────────────────────────────────────────────────────────
# Rule 6 -- ROADMAP 2.81 PHASE 2: a bare stem, settled only by the bar's sum
# ─────────────────────────────────────────────────────────────────────────────

#: The `adjudicate_duration` reason this rule speaks into -- and ONLY this one.
BARE_STEM_REASON = "beam_discounted_uncertain"

#: How many unknown events one bar may hold before the rule declines. The DP
#: below is linear in it; the cap is not for speed, it is that a bar with more
#: than this many undecided events is a bar nobody read.
BARE_STEM_MAX_UNKNOWNS = 24


def _frac(x: Any):
    from fractions import Fraction
    return Fraction(float(x)).limit_denominator(1000)


def bar_has_tuplet(log: Log, cell: Subject) -> Tuple[str, ...]:
    """Does this bar PRINT a tuplet? The reasons we know, or `()`.

    ROADMAP 2.102 (Sean's tiles 2026-10-12: a quarter in a 3-quarter tuplet
    settled as an eighth). EVERY bar-sum settlement counts a tuplet note at its
    written length -- a third too long -- so a bar that prints one is not a
    sum the arithmetic can speak for (rule 8: the answer is "cannot tell").
    Any bar-sum rule calls this first and declines on a non-empty answer.

    ⚠️ IT ONLY SEES WHAT THE READERS SAW, and that is the rule (Sean
    2026-10-13): a tuplet exists only where its printed marking (the 3 /
    bracket) is seen; an unmarked triplet is never inferred. The detector filed
    no `tuplet*`/`fingering3` box anywhere on Dvorak 8 pdf p4, where tile 6 is
    a real triplet, so there this returns `()`.

    Reasons: `tuplet_marker` (a `Q.TUPLET_MARKER` row under the cell that no
    human struck out) and `tuplet_ratio` (`adjudicate_tuplet` DECIDED a ratio
    on the cell).
    """
    reasons: List[str] = []
    for m in log.rows(Q.TUPLET_MARKER, cell, scope=Scope.SELF_AND_DESCENDANTS):
        refusal = log.verdict(Q.TUPLET_MARKER_IS_NOT_A_MARKER, m.subject)
        if (refusal is not None and refusal.outcome is Outcome.DECIDED
                and refusal.value is True):
            continue
        reasons.append("tuplet_marker")
        break
    ratio = log.verdict(Q.TUPLET_RATIO, cell)
    if ratio is not None and ratio.outcome is Outcome.DECIDED:
        reasons.append("tuplet_ratio")
    return tuple(reasons)


def _simultaneous_heads(log: Log, cell: Subject,
                        events: Sequence[Dict[str, Any]]) -> bool:
    """Do two heads of DIFFERENT events stand in one column?

    ROADMAP 2.102, tile 10 (Schumann 2, Peters p3): six dyads whose two heads
    sit 3-13 px apart in x were grouped as 12 events, so the bar sum counted
    every column twice and "landed" 6/4 on twelve eighths where the print has
    six quarters. A voice is a sequence: two heads whose centres are less
    than half a head apart cannot follow each other.
    """
    boxes = []
    for e in events:
        if e.get("kind") == "rest":
            continue
        for g in e.get("glyphs", ()):
            rows = log.rows(Q.GLYPH_BOX, Subject(
                Kind.GLYPH, cell.page, cell.system, cell.staff, cell.cell, g))
            if not rows:
                continue
            v = rows[0].value
            try:
                boxes.append((float(v[1]) + float(v[3]) / 2.0, float(v[3]),
                              id(e)))
            except (TypeError, ValueError, IndexError):
                continue
    boxes.sort()
    for (xa, wa, ea), (xb, wb, eb) in zip(boxes, boxes[1:]):
        if ea != eb and (xb - xa) < 0.5 * min(wa, wb):
            return True
    return False


@dataclass
class BarOutcome:
    """What `solve_bare_stem_bar` found in one bar. A probe's whole surface."""

    #: why the bar yielded nothing, or None when it was solved (even if no
    #: member was forced -- see `ambiguous`)
    decline: Optional[str] = None
    members: int = 0            # bare-stem narrowings in the bar
    unknowns: int = 0           # events with more than one admitted length
    landings: int = 0           # assignments of the unknowns that land the bar
    forced: int = 0             # bare-stem members the arithmetic forces
    ambiguous: int = 0          # members two landings disagree about
    lengthening_unwitnessed: int = 0   # 2.97: forced, but longer than the reader's best and the bar's ink is not wholly explained
    shortened_refused: int = 0  # forced to the shorter length, refused (Sean 2026-10-12)
    tip_not_clean: int = 0      # members the arithmetic forces but whose tip was not SEEN clean
    proposals: Optional[List[Proposal]] = None


#: The `adjudicate_meter` reasons whose value IS a printed reading (or an
#: unchanged carry of one that the bars did not overturn).
_PRINTED_METER_REASONS = ("voted", "carried", "carried_uncontested")


def _printed_meter_roots(log: Log, meter: Verdict, cell: Subject,
                         _depth: int = 0) -> Optional[Tuple[str, ...]]:
    """The printed time-signature READINGS a meter verdict ultimately used.

    `None` where the meter does not reach the print by `used` alone: a reason
    outside `_PRINTED_METER_REASONS`, a bar AT OR AFTER a printed CHANGE in its
    system (a different reading is the evidence there, and this rule does not
    guess which), or a chain that never reaches a template/glyph/OCR row.

    ⚠️ A SYSTEM WITH A PRINTED CHANGE STILL SERVES ITS BARS BEFORE IT. Brahms
    1's count page prints 9/8 at bar 8 and a return to 6/8 at bar 9; the first
    draft declined every bar of that system (all 45 narrowings on the page).
    The opening segment's evidence is the system's opening readings (or the
    carried meter), and a bar before the change is in force under exactly that.
    """
    if _depth > 40 or meter.outcome is not Outcome.DECIDED \
            or meter.reason not in _PRINTED_METER_REASONS:
        return None
    if _depth == 0:
        segs = (meter.value or {}).get("segments") or ()
        if len(segs) > 1 and cell.cell is not None \
                and int(cell.cell) >= int(segs[1].get("from_cell") or 0):
            return None
    if meter.reason == "voted":
        rows = [r for r in meter.used
                if (log.row(r) is not None
                    and log.row(r).quantity in (Q.METER_TEMPLATE, Q.METER_GLYPH,
                                                Q.METER_OCR))]
        return tuple(rows) or None
    for r in meter.used:
        src = log.row(r)
        if isinstance(src, Verdict) and src.quantity == Q.METER:
            # ROADMAP 2.136 W1 (flag `OMR_INFER_CARRIED_METER_FIX`, default ON): what a
            # carry carries is the meter in force at the END of the source system, not
            # its opening segment (2.79). Brahms 1/i opens 9/8, prints a return to 6/8
            # at bar 1, and every later system carries 6/8.
            sv = src.value or {}
            if carried_meter_fix_enabled():
                sv = (sv.get("segments") or [sv])[-1] or sv
            if sv.get("numerator") != (meter.value or {}).get(
                    "numerator") or sv.get(
                        "denominator") != (meter.value or {}).get("denominator"):
                return None
            return _printed_meter_roots(log, src, cell, _depth + 1)
    return None


def solve_bare_stem_bar(log: Log, cell: Subject, *,
                        any_reason: bool = False) -> BarOutcome:
    """One staff's bar: which bare-stem members does the arithmetic force?

    ⚠️⚠️ THE CLAIM, AND WHERE IT IS WEAK. Every DECIDED duration in the bar is
    held fixed; every NARROWED one may take any of its OWN candidates; the bar
    must land EXACTLY on the meter in force at it. A bare-stem member is
    settled only if EVERY landing gives it the same length, and the bar has at
    least one landing. It is NOT entailment: a missed note, a note the reader
    invented, a wrong DECIDED neighbour, a second voice on the staff or a
    mis-read meter each move the sum, and a unique landing through any of them
    is a confident wrong answer (rule 8). That is why the verdict is labelled
    INFERRED, why the flag is default OFF, and why the only legitimate score
    is the print.

    ⚠️ IT DOES NOT USE THE RANKING. The quarter-first order `adjudicate_
    duration` carries where the bare-stem evidence holds is a likelihood;
    nothing here reads `support` (rule (a) of `infer.py`). Where two landings
    exist the member stays narrowed -- choosing between them by the prior
    would be Sean's 0.76-0.80 laundered into an answer.
    """
    from collections import Counter
    from .consequences import (WITNESS_CLEAR, _bar_beats_at, _is_rest,
                               _left_the_bar, _missed_rest_witness,
                               _on_one_stem, _standing,
                               _bar_heads_are_clean, _bar_has_tuplet,
                               _shortens_without_evidence, _eighth_evidence)
    out = BarOutcome(proposals=[])
    notes = []
    for v in _standing(log, cell, Q.DURATION):
        if v.outcome not in (Outcome.DECIDED, Outcome.NARROWED):
            continue
        if _left_the_bar(log, v.subject) is not None:
            continue
        notes.append(v)
    # ⚠️ ROADMAP 2.97 (`any_reason`): the SAME bar arithmetic over every
    # narrowed note of the bar, whatever refused its beams. The bare-stem rule
    # (2.81) keeps its own reading of the word; this widening is the second
    # rule's, and it is what `collapse_narrowed_by_bar` passes.
    def _is_member(v):
        if v.reason == BARE_STEM_REASON:
            return True
        return bool(any_reason and v.candidates and not _is_rest(v))

    members = [v for v in notes if v.outcome is Outcome.NARROWED
               and _is_member(v)]
    out.members = len(members)
    if not members:
        return out
    # ROADMAP 2.102 (a): a bar that prints a tuplet is not a sum this
    # arithmetic can speak for.
    seen = bar_has_tuplet(log, cell)
    if "tuplet_marker" in seen and "tuplet_ratio" not in seen:
        # a tuplet is printed here but no ratio was decided, so the members'
        # lengths are not scaled and the sum is not the bar's
        out.decline = "tuplet_in_bar"
        return out
    meter = log.verdict(Q.METER, cell.at(Kind.SYSTEM))
    if meter is None or meter.outcome is not Outcome.DECIDED:
        out.decline = "no_decided_meter"
        return out
    expected = _bar_beats_at(meter, cell)
    if expected is None:
        out.decline = "no_meter_in_force"
        return out
    grouping = log.verdict(Q.EVENT, cell)
    if grouping is None or grouping.outcome is not Outcome.DECIDED:
        out.decline = "no_event_grouping"
        return out
    # ROADMAP 2.102, tile 10: heads standing in one column that the grouping
    # left as separate events are counted as successive in time.
    if _simultaneous_heads(log, cell, (grouping.value or {}).get("events", ())):
        out.decline = "simultaneous_heads_not_grouped"
        return out

    # ⚠️⚠️ THE METER MAY NOT BE THE BARS' OWN. `adjudicate_meter` weighs the
    # carry by the bars (its verdict's `basis` holds every duration of the
    # system), so reading its verdict would make the bar an umpire of itself
    # -- measured on both count pages: EVERY meter verdict has `Q.DURATION` in
    # its closure, and the first draft of this rule declined 99 of 102 Brahms
    # members and 24 of 26 Litolff ones for exactly that. What the meter
    # verdict USED is narrower: a `voted` meter used the template/glyph/OCR
    # readings of the printed time signature, a `carried` one used the earlier
    # system's meter verdict. Follow `used` to the printed readings and take
    # THOSE as the basis; a meter that does not reach the print that way (a
    # change, a meter derived from the bars) is declined by name.
    roots = _printed_meter_roots(log, meter, cell)
    if roots is None:
        out.decline = "meter_not_from_the_print"
        return out
    meter_closure = set()
    for rid in roots:
        meter_closure |= log.closure(rid)
    if any(v.id in meter_closure for v in members):
        out.decline = "meter_rests_on_these_bars"
        return out

    _witness: List[str] = []

    def _ink_witness(c):
        if not _witness:
            _witness.append(_missed_rest_witness(log, c)[0])
        return _witness[0]

    if any_reason and not _bar_heads_are_clean(
            log, cell, notes, ledger_owner_aware=ledger_owner_heads_enabled()):
        out.decline = "heads_not_this_staffs_own"
        return out
    if any_reason and (_bar_has_tuplet(log, cell, notes)
                       or bar_has_tuplet(log, cell)):
        out.decline = "bar_holds_tuplet_evidence"
        return out
    by_glyph = {v.subject.glyph: v for v in notes}
    fixed = _frac(0)
    unknown_events: List[Tuple[List[Verdict], List[Any]]] = []
    seen = set()
    basis: List[str] = list(roots) + [grouping.id]
    for ev in (grouping.value or {}).get("events", ()):
        ms = [by_glyph[g] for g in ev.get("glyphs", ()) if g in by_glyph]
        if not ms:
            continue
        seen.update(m.id for m in ms)
        narrowed = [m for m in ms if m.outcome is Outcome.NARROWED]
        if not narrowed:
            beats = Counter(_frac(m.value.get("beats") or 0.0) for m in ms)
            fixed = fixed + beats.most_common(1)[0][0]
            basis.extend(m.id for m in ms)
            continue
        if len(narrowed) != len(ms):
            out.decline = "event_mixes_decided_and_narrowed"
            return out
        if any_reason and len(ms) >= 2 and not _on_one_stem(log, ms):
            out.decline = "chord_not_on_one_decided_stem"
            return out
        # ⚠️ SEAN'S RULE (2026-10-12): the widened rule never chooses a
        # shorter reading for a stem with no flag or beam read on it.
        opts = [tuple(sorted({_frac(c.value.get("beats")) for c in m.candidates
                              if isinstance(c.value, dict)
                              and c.value.get("beats") is not None
                              and not (any_reason
                                       and _shortens_without_evidence(m, c.value))}))
                for m in ms]
        if len(set(opts)) != 1 or not opts[0]:
            out.decline = "event_members_admit_different_lengths"
            return out
        unknown_events.append((ms, list(opts[0])))
    for v in notes:
        if v.id in seen:
            continue
        if v.outcome is Outcome.NARROWED:
            out.decline = "narrowed_note_outside_every_event"
            return out
        fixed = fixed + _frac(v.value.get("beats") or 0.0)
        basis.append(v.id)
    # the bar rests on the decided neighbours' verdicts; none of them may rest
    # on a narrowing it is about to collapse
    reach = set()
    for rid in basis:
        reach |= log.closure(rid)
    if any(m.id in reach for m in members):
        out.decline = "decided_neighbour_rests_on_the_narrowing"
        return out

    n = len(unknown_events)
    out.unknowns = n
    if n > BARE_STEM_MAX_UNKNOWNS:
        out.decline = "too_many_unknowns"
        return out
    target = _frac(expected)
    # prefix[i]: sum -> ways, using the unknowns before i, on top of `fixed`;
    # suffix[i]: sum -> ways, using the unknowns from i on
    prefix: List[Dict[Any, int]] = [{fixed: 1}]
    for _ms, opts in unknown_events:
        nxt: Dict[Any, int] = {}
        for s_, c_ in prefix[-1].items():
            for o in opts:
                nxt[s_ + o] = nxt.get(s_ + o, 0) + c_
        prefix.append(nxt)
    out.landings = prefix[-1].get(target, 0)
    if out.landings == 0:
        out.decline = "bar_does_not_add_up"
        return out
    suffix: List[Dict[Any, int]] = [dict() for _ in range(n + 1)]
    suffix[n] = {_frac(0): 1}
    for i in range(n - 1, -1, -1):
        cur: Dict[Any, int] = {}
        for s_, c_ in suffix[i + 1].items():
            for o in unknown_events[i][1]:
                cur[s_ + o] = cur.get(s_ + o, 0) + c_
        suffix[i] = cur
    # SEAN 2026-10-13: a tuplet exists only where its printed marking is SEEN
    # (the 3 / bracket); three unread stems never imply a hidden 3:2 group. A
    # bar that would add up only under an unmarked triplet gives no
    # confirmation (`bar_does_not_add_up`), and the written value stays what
    # the shape says (quarter: no flag or beam read).
    for i, (ms, opts) in enumerate(unknown_events):
        feasible = [o for o in opts
                    if any((target - s_ - o) in suffix[i + 1]
                           for s_ in prefix[i])]
        for m in ms:
            if not (m.outcome is Outcome.NARROWED and _is_member(m)):
                continue
            if len(feasible) != 1:
                out.ambiguous += 1
                continue
            # ⚠️ SEAN'S OWN CONDITION (2026-10-10): *a tip SEEN clean*. A head
            # whose stem-tip window was occupied, held flag ink, or was never
            # read is not that head, and a bar that "adds up" through a missed
            # note settles it wrongly -- the one wrong decision on Sean's hand
            # truth page (Brahms pdf 0, a flagged eighth) was exactly this: the
            # arithmetic landed through a note nobody read, and the tip window
            # was occupied. The 33 right ones all had a clean window.
            # ⚠️ 2.97: the bare-stem rule keeps Sean's tip condition as it
            # was. The widened rule (`any_reason`) asks for the OTHER
            # evidence the tip window stood in for -- that no mark was missed
            # -- instead: a head on a bare stem whose tip was not seen clean
            # is settled only if the bar's ink is wholly explained by the
            # standing glyphs (2.80's witness), and ANY lengthening past the
            # reader's own best candidate needs that witness too (a missed
            # rest or note fills the same gap: 2.80).
            if m.reason == BARE_STEM_REASON \
                    and (m.detail or {}).get(
                        "bare_stem_tip_window_clean") is not True:
                if not any_reason or _ink_witness(cell) != WITNESS_CLEAR:
                    out.tip_not_clean += 1
                    continue
            top = next((c for c in m.candidates if isinstance(c.value, dict)
                        and c.value.get("beats") is not None), None)
            if any_reason and top is not None \
                    and feasible[0] > _frac(top.value["beats"]) \
                    and _ink_witness(cell) != WITNESS_CLEAR:
                out.lengthening_unwitnessed += 1
                continue
            hit = [c for c in m.candidates if isinstance(c.value, dict)
                   and c.value.get("beats") is not None
                   and _frac(c.value["beats"]) == feasible[0]]
            if len(hit) != 1:
                out.ambiguous += 1
                continue
            # ⚠️ SEAN 2026-10-12 (CLAUDE.md §10): *"only when we see evidence of
            # an eighth should it be called that"*, refined: the bar sum may
            # CONFIRM a value the ink supports, never SUPPLY one. A shorter
            # candidate (more beam levels than the longest) is settled only
            # where the member's OWN reading holds a stroke at least that deep
            # (`levels_certain` / `levels_possible`, refused-but-present
            # strokes included); a bare stem is never shortened by arithmetic
            # (tiles 6 and 10).
            levels = int(hit[0].value.get("beam_levels") or 0)
            floor = min(int(c.value.get("beam_levels") or 0)
                        for c in m.candidates if isinstance(c.value, dict))
            if levels > floor and not any_reason:
                d_ = m.detail or {}
                seen_levels = max(int(d_.get("levels_certain") or 0),
                                  int(d_.get("levels_possible") or 0))
                if seen_levels < levels:
                    out.shortened_refused += 1
                    continue
            out.forced += 1
            out.proposals.append(Proposal(
                subject=m.subject, value=hit[0].value,
                reason="the_bars_arithmetic_forces_this_length",
                basis=tuple(dict.fromkeys(basis)), witnesses=(),
                detail={
                    "expected_beats": float(target),
                    "bar_landings": out.landings,
                    "bar_unknown_events": n,
                    "bare_stem_likelihood": (m.detail or {}).get(
                        "bare_stem_likelihood"),
                    "chosen_candidate_support": hit[0].support,
                    # ⚠️ REPORTED, NEVER THE REASON (infer.py rule (a))
                    "was_readers_top_candidate": bool(
                        m.candidates and m.candidates[0].value is hit[0].value),
                    "reads_meter": True,
                    "eighth_evidence": (
                        list(_eighth_evidence(m)) if int(
                            hit[0].value.get("beam_levels") or 0) > 0 else None),
                }))
    return out


@rule(
    inference=Inference.COLLAPSE_BARE_STEM_BY_BAR,
    target=Q.DURATION,
    reads=(Q.METER, Q.EVENT, Q.DURATION, Q.GLYPH_OWNER,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST),
    scope=Kind.CELL,
    sideways=False,
    switch=BARE_STEM_BAR_SWITCH,
    bound=(
        "It collapses a NARROWED duration whose reason is "
        "`beam_discounted_uncertain` to one of that reader's OWN candidates "
        "and nothing else; only inside one staff's bar whose meter is DECIDED "
        "and was not voted out of these bars, whose events are grouped, whose "
        "decided notes are held fixed and whose every unknown is a narrowing "
        "with identical candidate lengths per chord; the bar must land "
        "EXACTLY on the meter under at least one assignment of the unknowns, "
        "and a member is collapsed only if EVERY landing gives it the same "
        "length, and only if that member's stem-tip window was READ clean "
        "(Sean's condition). Where two landings disagree it declines. It "
        "never reads `support` and never uses the bare-stem likelihood as a "
        "reason."),
    why_witnesses_are_independent=(
        "It counts no witnesses: the evidence is arithmetic over the bar's "
        "other durations and the meter, which are NOT independent of the "
        "ink being summed -- a missed note, a second voice or a mis-read "
        "meter move the sum and the rule cannot see them. That correlation "
        "is declared here rather than hidden behind a witness count, which "
        "is why the verdict is labelled and the rule default OFF."),
)
def collapse_bare_stem_by_bar(log: Log, cell: Subject) -> List[Proposal]:
    """A bare stem's narrowing, settled by the bar's sum alone.

    See `solve_bare_stem_bar`. Roadmap 2.81 phase 2, Sean 2026-10-10: *"if it
    is lower ... send it on to the other stages with a high likelihood of
    being a quarter note and make sure the bar math adds up"*.
    """
    return solve_bare_stem_bar(log, cell).proposals or []


@rule(
    inference=Inference.COLLAPSE_NARROWED_BY_BAR,
    target=Q.DURATION,
    reads=(Q.METER, Q.EVENT, Q.DURATION, Q.GLYPH_OWNER,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST),
    scope=Kind.CELL,
    sideways=False,
    switch=NARROWED_BAR_SWITCH,
    bound=(
        "It collapses a NARROWED duration -- a head, or every head of a "
        "chord together (one stem, one value) -- to one of that reader's OWN "
        "candidates and nothing else; only inside one staff's bar whose "
        "meter is DECIDED and reaches the PRINTED time signature by `used` "
        "(never a meter the bars themselves chose), whose events are grouped, "
        "whose decided notes are held fixed, and where the bar lands EXACTLY "
        "on the meter under at least one assignment of the narrowed events "
        "and EVERY landing gives the member the same length. Two landings "
        "that disagree leave it narrowed. A member whose reason is a bare "
        "stem needs its tip seen clean (Sean's 2.81 condition) or the bar's "
        "ink wholly explained by the standing glyphs; any lengthening past "
        "the reader's best-supported candidate needs that ink witness too "
        "(a missed rest or note fills the same gap, 2.80). It never reads "
        "`support` and never overturns a DECIDED verdict."),
    why_witnesses_are_independent=(
        "It counts no witnesses: the evidence is arithmetic over the bar's "
        "other durations and the printed meter, which are NOT independent "
        "of the ink being summed -- a missed note, a second voice or a "
        "wrong decided neighbour move the sum and the rule cannot see them. "
        "That correlation is declared here rather than hidden behind a "
        "witness count, which is why the verdict is labelled and the rule "
        "is gated."),
)
def collapse_narrowed_by_bar(log: Log, cell: Subject) -> List[Proposal]:
    """A narrowed head's (or chord's) value, settled by the bar's sum alone.

    ROADMAP 2.97. Which stage, and why: the answer does not FOLLOW (a missed
    rest, a spurious head or a wrong decided neighbour each move the sum), it
    is merely BEST -- so it is INFER's, labelled, gated, and bounded to the
    reader's own candidates. See `solve_bare_stem_bar(any_reason=True)`.
    """
    return solve_bare_stem_bar(log, cell, any_reason=True).proposals or []


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.121 -- a bare stem whose every refused "beam" is a slur's or tie's ink
# ─────────────────────────────────────────────────────────────────────────────

#: Why a refused stroke counts as POSITIVELY not a beam. `arc`: inside a DECIDED slur/tie glyph (2.25b). `ink:too_thin` /
#: `ink:bowed`: 2.74's ink test measured it thinner than any beam / bowed (Sean 2026-10-09: *"a beam never has an arc"*, thicker
#: than a hairpin's line). NOT here, on purpose: `ink:one_stem` (2.82: a real beam whose other stem the stem finder missed is
#: refused this way), `ink:through_heads`, `neighbour_staff`, `far_side`, `beyond_stem` -- each says the stroke may belong to
#: something else or to a stem nobody read, which is "cannot tell", not "a slur".
ARC_INK_NOT_BEAM_POSITIVE = ("arc", "ink:too_thin", "ink:bowed")


def arc_ink_not_beam_decline(v: Any) -> Optional[str]:
    """Why a narrowed duration verdict is NOT settled by this rule, or `None` where it is. One place so the tests and the rule agree."""
    d = v.detail or {}
    if v.reason != BARE_STEM_REASON:
        return "not_beam_discounted_uncertain"
    if d.get("beam_evidence") != "none_over_this_note":
        return "a_beam_or_flag_was_read"
    if int(d.get("stems_attached") or 0) < 1:
        return "no_own_stem_seen"
    if d.get("bare_stem_tip_window_clean") is not True:
        return "tip_not_read_clean"
    if int(d.get("flags_attached") or 0) or int(d.get("flag_levels") or 0) \
            or int(d.get("levels_certain") or 0) or int(d.get("levels_possible") or 0):
        return "a_mark_stands_on_the_stem"
    strokes = d.get("refused_strokes")
    if not isinstance(strokes, (list, tuple)) or not strokes:
        return "no_refused_stroke_facts"
    for st in strokes:
        why = st.get("why")
        if why not in ARC_INK_NOT_BEAM_POSITIVE:
            return "a_refusal_that_is_not_a_slur_reading:%s" % why
        # a stroke AT the tip is where a refused real beam would stand (2.81); only a decided slur/tie glyph may stand there
        # (a slur starts at the stem end), never a bare ink-shape refusal.
        if st.get("at_tip") is not False and why != "arc":
            return "ink_shape_refusal_at_the_tip"
    return None


@rule(
    inference=Inference.COLLAPSE_ARC_INK_NOT_BEAM,
    target=Q.DURATION,
    reads=(Q.DURATION, Q.GLYPH_OWNER, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.REST_IS_NOT_A_REST),
    scope=Kind.CELL,
    sideways=False,
    switch=ARC_INK_NOT_BEAM_SWITCH,
    bound=(
        "It collapses a NARROWED duration whose reason is `beam_discounted_uncertain` to that reader's OWN unbeamed candidate and "
        "nothing else, only where the head's own stem was seen, nothing was read on it (no beam, no flag, no level), its stem-tip "
        "window was READ clean, and EVERY stroke the reader refused is on file as a decided slur/tie's own ink or as measured thinner "
        "or more bowed than any beam (a refusal for one stem, through the heads, another staff's or the far side's is not enough). A "
        "stroke refused by ink shape alone and standing at the tip declines. It uses no bar arithmetic, never reads `support` and "
        "never overturns a DECIDED verdict; it never shortens a note (the unbeamed value is the head's own)."),
    why_witnesses_are_independent=(
        "ONE witness, declared: the arc reader's decided slur/tie glyph and the CV ink test (thickness, bow) read the SAME ink, so "
        "they fall together and count once (CLAUDE.md §4); the stem-tip window is a separate reading of a different region but "
        "answers a different question (no hook). One witness cannot READ, so the verdict is GUESSED (blue, with both candidates) and "
        "the rule is default OFF until Sean's blind tiles."),
)
def collapse_arc_ink_not_beam(log: Log, cell: Subject) -> List[Proposal]:
    """A bare stem under a slur is a quarter -- GUESSED, not read.

    ROADMAP 2.121. Which stage, and why: 2.119's twins split A (24 pairs) read as "the beam reader missed a beam"; Sean's own boxes
    (Brahms 317803 pdf 0) say otherwise -- 19 of the 24 stems carry no beam and no flag, the detector's `beam` boxes beside them are
    his slurs and ties. The ink reader was RIGHT to refuse them; the narrowing stood because 2.74's rule 8 will not turn a refusal
    into an unmarked note. Whether "every refused stroke is a slur" FOLLOWS is not forced (the ink is one witness), so it is INFER's:
    best, labelled, bounded to the reader's own candidates.
    """
    from .consequences import _left_the_bar, _standing
    out: List[Proposal] = []
    for v in _standing(log, cell, Q.DURATION):
        if v.outcome is not Outcome.NARROWED or not v.candidates:
            continue
        if _left_the_bar(log, v.subject) is not None:
            continue
        declined = arc_ink_not_beam_decline(v)
        if declined is not None:
            continue
        unbeamed = [c for c in v.candidates if isinstance(c.value, dict)
                    and int(c.value.get("beam_levels") or 0) == 0]
        if len(unbeamed) != 1:
            continue
        strokes = (v.detail or {}).get("refused_strokes") or []
        out.append(Proposal(
            subject=v.subject, value=unbeamed[0].value,
            reason="refused_strokes_are_slurs_or_too_thin_for_a_beam",
            basis=(v.id,), witnesses=(),
            detail={"refused_strokes": [dict(st) for st in strokes],
                    "n_refused_strokes": len(strokes),
                    "n_decided_arc": sum(1 for st in strokes if st.get("why") == "arc"),
                    "tip_window_clean": True,
                    "margin_axis": "no_margin: a conjunction of readings, not a score",
                    "witness_count": 1}))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Rule 9 -- a NARROWED dynamic, collapsed to the candidate the INK scores closest
# ─────────────────────────────────────────────────────────────────────────────

#: The letter reader must have scored the winning completion at least this well
#: (its confidence over the open letter's ink, the lower of two erasures), and
#: its lead over the runner-up must be at least `INK_PICK_MARGIN`. Both are
#: CONVENTION ASSUMED -- not measured on a corpus -- and NOT CONFIRMED by Sean;
#: WHAT WOULD FALSIFY THEM: a blue dynamic that is the wrong letter on a print
#: the margin would have refused. Each pick records its scores and winning
#: margin (ROADMAP 2.106), so the near calls are countable.
INK_PICK_MIN_SCORE = 0.3
INK_PICK_MARGIN = 0.15


@rule(
    inference=Inference.COLLAPSE_DYNAMIC_BY_INK,
    switch=DYNAMIC_INK_PICK_SWITCH,
    target=Q.DYNAMIC,
    reads=(Q.DYNAMIC, Q.DYNAMIC_LETTER),
    scope=Kind.CELL,
    sideways=False,
    bound=(
        "It collapses a NARROWED `dynamic` -- a bar whose only dynamic run has "
        "an unread letter beside the letters that were read -- to one of that "
        "reader's OWN completions and nothing else, only where the cell holds "
        "exactly one unspellable run, the winning completion's ink score "
        f"(`completion_support`: the letter reader's own confidence for the "
        f"letter it puts in each open slot, the lower of two staff-line "
        f"erasures) is at least {INK_PICK_MIN_SCORE} and leads the runner-up "
        f"by at least {INK_PICK_MARGIN}. A tie, or an open letter nobody "
        "scored, leaves it narrowed (EXPORT then writes `dyn.`). It reads no "
        "word frequency from the document and never overturns a DECIDED "
        "verdict."),
    why_witnesses_are_independent=(
        "It counts no witnesses: the evidence is ONE reader's scores for the "
        "open letter over the same ink (two erasures of it), so it is one "
        "signal and is labelled a guess; a second witness would have to come "
        "from a different source, and the document's own dynamics are not "
        "evidence about THIS mark's letter (Sean 2026-10-13)."),
)
def collapse_dynamic_by_ink(log: Log, cell: Subject) -> List[Proposal]:
    """The closest dynamic the ink can name, for a dynamic with an unread letter.

    ROADMAP 2.107. Which stage, and why: the letter reader saw the letters and
    could not read one; the answer does not FOLLOW, it is merely BEST -- so it
    is INFER's, labelled (blue in the file), bounded to the reader's own
    completions, and recorded with the margin it won by."""
    prior = log.verdict(Q.DYNAMIC, cell)
    if prior is None or prior.outcome is not Outcome.NARROWED:
        return []
    detail = prior.detail or {}
    unspellable = [w for w in (detail.get("words") or [])
                   if isinstance(w, dict) and not w.get("spelled")]
    if len(unspellable) != 1:
        return []
    ranked = sorted(((float(c.support), str(c.value))
                     for c in (prior.candidates or ())), reverse=True)
    if len(ranked) < 2:
        return []
    (top, word), (second, runner) = ranked[0], ranked[1]
    if top < INK_PICK_MIN_SCORE or (top - second) < INK_PICK_MARGIN:
        return []
    return [Proposal(
        subject=cell, value=word, reason="ink_evidence", basis=(), witnesses=(),
        detail={"ink_scores": {w: s for s, w in ranked},
                "margin": round(top - second, 4), "margin_axis": "ink_score_gap",
                "margin_unit": "letter-reader confidence, lower of two erasures",
                "runner_up": runner, "min_score": INK_PICK_MIN_SCORE,
                "required_margin": INK_PICK_MARGIN})]

