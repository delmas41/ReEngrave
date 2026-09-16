"""The inference rules. One so far.

⚠️ Registered by importing this module, which `infer._ensure_rules` does
LAZILY -- so a tree carrying INFER imports nothing extra until the stage is
actually asked to run. That is part of the bypass: off means ABSENT, not
quiet.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .adjudicators.rhythm import ONSET_COLUMN_TOLERANCE_SPACES, _page_x_of
from .infer import Inference, Proposal, independent_groups, rule
from .record import Kind, Log, Outcome, Q, Scope, Subject

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
    out: Dict[Tuple[int, int], List[dict]] = {}
    for v in log.verdicts(Q.EVENT, system, scope=Scope.SELF_AND_DESCENDANTS):
        sub = v.subject
        if sub.cell is None or sub.staff is None or not isinstance(v.value, dict):
            continue
        for e in v.value.get("events", ()):
            glyphs = [g for g in e.get("glyphs", ())
                      if (sub.staff, sub.cell, g) in boxes]
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
    reads=(Q.ONSET_COLUMN, Q.EVENT, Q.DURATION, Q.GLYPH_BOX),
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
    335 of 356. See the comment at the `end` lookup.

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
    out: List[Proposal] = []

    for (staff, cell), evs in sorted(events.items()):
        bar = bars.get(cell)
        if bar is None:
            continue
        columns = sorted(bar["columns"], key=lambda c: float(c["x_page"]))
        # every staff's events in this bar, keyed by column index
        at_col: Dict[int, Dict[int, dict]] = {}
        nxt_col: Dict[Tuple[int, int], Optional[int]] = {}
        for (st2, c2), evs2 in events.items():
            if c2 != cell:
                continue
            idx = [(_column_index(columns, e["x"], tol_px), e) for e in evs2]
            for pos, (ci, e) in enumerate(idx):
                if ci is None:
                    continue
                at_col.setdefault(ci, {})[st2] = e
                # The column index of THIS staff's own next event, which is
                # what says where its note ends.
                follow = None
                for ci2, _e2 in idx[pos + 1:]:
                    if ci2 is not None:
                        follow = ci2
                        break
                nxt_col[(st2, ci)] = follow

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
            end = nxt_col.get((staff, k))
            if end is None:
                # No next onset in this bar, so this note runs to the BARLINE
                # and its length is the bar's — which is the meter, which this
                # rule may not read (it would make `bar_fill` a measurement of
                # the quantity the rule optimises). 191 of 357 land here and
                # they are out of reach BY DESIGN, not by accident.
                continue
            for g in e["glyphs"]:
                sub = Subject(Kind.GLYPH, page=system.page,
                              system=system.system, staff=staff, cell=cell,
                              glyph=g)
                prior = log.verdict(Q.DURATION, sub)
                if prior is None or prior.outcome is not Outcome.NARROWED:
                    continue
                p = _propose(log, system, prior, sub, cell, staff, k, end,
                             at_col, nxt_col, col_v, bar)
                if p is not None:
                    out.append(p)
    return out


def _propose(log, system, prior, sub, cell, staff, k, end, at_col, nxt_col,
             col_v, bar) -> Optional[Proposal]:
    """Gather the witnesses for one narrowed glyph and propose, or not.

    ⚠️ A witness must begin at column `k` AND END AT COLUMN `end` — the same
    two instants this note spans. A witness that ends anywhere else is
    measuring a different stretch of time and is not a witness to this note's
    length at all.
    """
    votes: Dict[float, List[str]] = {}
    witness_ids: List[str] = []
    for st2, e2 in sorted(at_col.get(k, {}).items()):
        if st2 == staff:
            continue
        if nxt_col.get((st2, k)) != end:
            continue                # it ends elsewhere: a different stretch
        beats, ids = _event_beats(log, st2, cell, system, e2["glyphs"])
        if beats is None:
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
        subject=sub,
        value=matching[0].value,
        reason="the_neighbours_name_this_gap",
        basis=(col_v.id,) + tuple(witness_ids),
        witnesses=tuple(witness_ids),
        detail={
            "beats": beats,
            "column": k,
            "measure": cell,
            "witness_staves": sorted(
                st for st in at_col.get(k, {}) if st != staff),
            "n_candidates_before": len(prior.candidates or ()),
            # ⚠️ REPORTED, NEVER THE REASON. See hazard (a): `support` is in
            # the reader's own units and is not a probability. It is here so a
            # human can see whether the inference agreed with the reader's own
            # ordering -- which is a diagnostic, not a justification.
            "chosen_candidate_support": matching[0].support,
            "was_readers_top_candidate": bool(
                prior.candidates and prior.candidates[0].value
                is matching[0].value),
            "events_per_space": bar.get("events_per_space"),
        },
    )
