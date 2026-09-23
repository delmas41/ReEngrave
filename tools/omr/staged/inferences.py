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
from .infer import (FAMILY_BLOCK_SWITCH, Inference, Proposal,
                    independent_groups, rule)
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


@rule(
    inference=Inference.COLLAPSE_SLOT_INDEX_TO_FAMILY_BLOCK,
    # ⚠️⚠️ ITS OWN FLAG, DEFAULT ON -- the one rule in this stage that has
    # been put to the PRINT most thoroughly. 25 of 25 placements correct,
    # ZERO grafts, `staff_not_identified` 783 -> 141, 562 pitched notes
    # joining the parts they belong to rather than inventing any. The two
    # duration rules below now default ON too (`OMR_INFER`, Sean 2026-09-23,
    # roadmap 2.3 -- three subjects checked against the print, all three
    # corrected by the `Q.GLYPH_OWNER` fix; see
    # `benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §7-§9). They
    # keep their OWN flag rather than sharing this one, because bundling
    # would make one flag two decisions of unequal evidential weight, and
    # the same reasoning that separated them in the first place stands.
    switch=FAMILY_BLOCK_SWITCH,
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
        witnesses: List[str] = []
        for i, (name, ids) in enumerate(reads):
            if name is None:
                continue
            want = run_clefs[i] if i < len(run_clefs) else None
            if want is None:
                continue
            if name != want:
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
                        # ⚠️ THE ONE DETAIL EXPORT READS. A staff placed here
                        # is doubled onto this slot too, an octave down,
                        # with `condensed_from` naming the source staff in
                        # the doubled part's own report entry.
                        "condensed_with_slot": int(contrabass_slot),
                    }))
    return out
