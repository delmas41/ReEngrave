"""Ownership — which staff a contested glyph belongs to, and the arcs.

⚠️ THE CHANGE HERE IS NOT A BETTER RULE. IT IS THAT THE DECISION MOVES.

Today `_dedupe_cross_staff_detections` runs 309 lines BEFORE identity, so its
strongest tier -- the instrument's written range -- is unavailable when it
decides. On a scan the tier is additionally vacuous: `_staff_written_ranges`
returns `{}` with no dossier and the scan gate runs dossier-free by protocol,
so all 4,256 duplicates resolve on ladder or distance. Under the split,
ownership is adjudicated AFTER identity and that costs nothing, because
adjudication reads a frozen record.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ... import transcribe as _legacy_articulation
from ..adjudicate import Checkable, Evidence, Mode, Ruling, Term, decision, tally
from .. import record as R
from ..record import ABSTAIN, Kind, Outcome, Q, Scope, State

# ⚠️ ASSUMED WEIGHTS (A-OWN-1). Ordered to match the tiers the existing code
# already applies in this order; none is measured.
W_LADDER_COMPLETE = 4.0     # an unbroken run of ledger rungs
W_RANGE_IMPOSSIBLE = -6.0   # a veto on the IMPOSSIBLE, never on the unlikely
W_DISTANCE = 0.5            # the tie-break, and only that


@decision(
    quantity=Q.GLYPH_OWNER,
    checkable=Checkable.MIXED,
    checked_by=(
        "a spurious or missing notehead breaks the OWNING bar's duration sum -- so rhythm_sum_warning's group includes OWNERSHIP, not only duration and meter",
        "the owned glyph's implied pitch must fall in the owner's written range",
    ),
    implicates=(Q.GLYPH_OWNER, Q.DURATION, Q.METER, Q.INSTRUMENT),
    composed_from=(Q.GLYPH_BAND_DISTANCE, Q.GLYPH_LADDER, Q.INSTRUMENT, Q.CLEF),
    scope=Kind.GLYPH,
    wants=(Q.GLYPH_LADDER, Q.GLYPH_BAND_DISTANCE, Q.GLYPH_CONF,
           Q.NOTEHEAD_STAFF_POSITION, Q.INSTRUMENT, Q.CLEF),
    reasons=("ladder", "range_veto", "distance", "no_contest", "no_evidence",
             "tied"),
    mode=Mode.ADDITIVE,
    # ⚠️ The domain is the CONTESTED population. A glyph nobody disputes has
    # nothing to arbitrate, and a verdict per detection would bury 4,521 real
    # contests under tens of thousands of no-ops.
    subjects_from=Q.GLYPH_BAND_DISTANCE,
)
def adjudicate_glyph_owner(ev: Evidence) -> Ruling:
    """Which staff owns a contested glyph.

    ⚠️ THE CHANGE IS NOT A BETTER RULE. IT IS THAT THE DECISION MOVES. Today
    this runs 309 lines BEFORE identity, so its strongest tier -- the
    instrument's written range -- is structurally unavailable; on a scan it is
    doubly so, because `_staff_written_ranges` returns `{}` with no dossier
    and the scan gate is dossier-free by protocol. All 4,256 duplicates
    resolve on ladder or distance, 94.1% of them on distance alone.

    Here identity is ALREADY DECIDED when this runs, and that costs nothing,
    because adjudication reads a frozen record. This function is the test of
    the architecture's central ordering claim (A-ORDER-2).
    """
    bands = ev.rows(Q.GLYPH_BAND_DISTANCE)
    if not bands:
        # Uncontested: the glyph belongs to the staff whose cell it was cut
        # from, and there is nothing to arbitrate.
        own = ev.subject.at(Kind.STAFF)
        return Ruling(value=own.to_key(), reason="no_contest")

    ladders = {r.detail.get("candidate"): r for r in ev.rows(Q.GLYPH_LADDER)}

    scored = []
    for row in bands:
        cand_key = row.detail.get("candidate")
        if cand_key is None:
            continue
        terms = []

        # ── tier 1: the ledger ladder ───────────────────────────────────────
        lad = ladders.get(cand_key)
        if lad is not None and bool(lad.value):
            terms.append(Term("ladder_complete", W_LADDER_COMPLETE, (lad.id,)))
        # ⚠️ A BROKEN ladder contributes NOTHING -- not a negative. Two broken
        # ladders are not evidence either way: a found rung can belong to the
        # other staff's note exactly as a gap can, and on the Beethoven
        # bassoon pair the ghost's one rung WAS the real C4's own ledger.

        # ── tier 2: the written range, a veto on the IMPOSSIBLE ────────────
        veto = _range_veto(ev, cand_key, row)
        if veto is not None:
            terms.append(veto)

        # ── tier 3: distance, and ONLY as the tie-break ────────────────────
        try:
            spaces = float(row.value)
        except (TypeError, ValueError):
            spaces = 0.0
        terms.append(Term("distance", -W_DISTANCE * spaces, (row.id,)))

        # ⚠️ CONFIDENCE IS DECLARED AND DELIBERATELY NOT WEIGHTED. Measured
        # over 4,521 contested pairs: P(winner conf > loser conf) = 0.545
        # against a 0.500 null, and a |Δconf| > 0 tie-break would OVERTURN
        # DISTANCE ON 45.5% OF CONTESTS. It is in `wants` so a future hand has
        # to decline it deliberately rather than never see it.

        distance_only = [t for t in terms if t.name == "distance"]
        scored.append((tally(terms, correlated=ev.correlated_groups()),
                       cand_key, terms, tally(distance_only)))

    if not scored:
        return Ruling.abstain("no_evidence")

    scored.sort(key=lambda t: (-t[0], t[1]))
    top_score, top_key, top_terms, _d = scored[0]
    runner = scored[1][0] if len(scored) > 1 else None

    # ⚠️ THE REASON MUST NAME WHAT MADE THE DIFFERENCE, NOT WHAT THE WINNER
    # HAPPENS TO CARRY. A veto acts on the LOSER, so the winning candidate
    # holds no veto term -- reading the reason off the winner's own terms
    # reported "distance" for a contest that distance would have lost. The
    # honest test is whether the distance-only ranking disagrees with the
    # final one.
    by_distance = max(scored, key=lambda t: (t[3], [-ord(c) for c in t[1]]))
    vetoed = any(t.name == "range_impossible"
                 for _s, _k, ts, _d2 in scored for t in ts)

    if runner is not None and top_score == runner:
        # ⚠️ Two equal-cost mappings that disagree carry literally zero
        # information. Saying so beats breaking the tie on something measured
        # to be a coin flip.
        return Ruling.abstain("tied")

    if any(t.name == "ladder_complete" for t in top_terms):
        reason = "ladder"
    elif vetoed and by_distance[1] != top_key:
        reason = "range_veto"
    else:
        reason = "distance"

    return Ruling(value=top_key, reason=reason,
                  margin=(top_score - runner) if runner is not None else None,
                  used=tuple(r.id for r in bands),
                  detail={"scores": {k: sc for sc, k, _t, _d2 in scored},
                          "would_win_on_distance": by_distance[1]})


def _range_veto(ev: Evidence, cand_key: str, band_row):
    """A veto on the IMPOSSIBLE, never on the unlikely.

    ⚠️ ITS INPUT IS POSITION + CLEF, NOT A RESOLVED PITCH (A-OWN-2). Today the
    tier reads `det["pitch"]`, which is downstream of the clef -- fine while
    nothing feeds ownership back into the clef, and a cycle the moment
    anything does. Reading the position and the clef VERDICT separately means
    the basis records both, so the harness can SEE the loop if it is ever
    closed.
    """
    from ...pitch_resolver import _pitch_from_position, pitch_to_midi
    from ..record import Subject

    cand = Subject.from_key(cand_key)
    instrument = ev.verdict(Q.INSTRUMENT, subject=cand)
    if instrument is None or not isinstance(instrument.value, dict):
        return None                     # no identity: the tier cannot speak
    lo_hi = instrument.value.get("written_range")
    if not lo_hi or instrument.value.get("unpitched"):
        return None

    clef = ev.verdict(Q.CLEF, subject=cand)
    if clef is None or clef.value is None:
        # ⚠️ A staff whose clef abstained gets NO veto. Vetoing on a guessed
        # clef would be the "guessing twice" fault the key-signature reader
        # already refuses -- and it would be worse here, because a veto
        # DISCARDS ink.
        return None

    pos = band_row.detail.get("position_in_candidate")
    if pos is None:
        return None
    name = _pitch_from_position(int(round(float(pos))), str(clef.value))
    midi = pitch_to_midi(name) if name else None
    if midi is None:
        return None

    lo, hi = int(lo_hi[0]), int(lo_hi[1])
    if lo <= midi <= hi:
        return None                     # possible: the veto says nothing
    return Term("range_impossible", W_RANGE_IMPOSSIBLE,
                (instrument.id, clef.id, band_row.id))
@decision(
    quantity=Q.ARC_OWNER,
    composed_from=(Q.ARC_BOX, Q.GLYPH_BOX, Q.STAFF_SPACING),
    scope=Kind.GLYPH,
    # ⚠️ `Q.NOTEHEAD_STAFF_POSITION` is NOT declared: this decision needs each
    # head's page BOX, not its step, and a declaration nothing reads is inert
    # -- `Evidence` fills `missing`/`declined` only for quantities actually
    # queried, so it would record nothing and could not be told from one that
    # is read and always present. Ten decisions in this pipeline carry such a
    # declaration; this one does not add an eleventh.
    wants=(Q.ARC_BOX, Q.GLYPH_OWNER, Q.GLYPH_BOX, Q.STAFF_SPACING),
    # ⚠️ THE DOMAIN IS THE ARCS, NOT EVERY GLYPH ON THE PAGE. Until the arc
    # rows existed there was nothing to name here, so this stub abstained once
    # per DETECTION -- 2,728 rows on one page, burying its own 199 real
    # subjects in 2,529 no-ops. `subjects_from` is what makes an abstention
    # mean "I could not read THIS arc".
    subjects_from=Q.ARC_BOX,
    reasons=("hugs_noteheads", "no_better_staff", "no_page_frame",
             "no_rival_staff", "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_arc_owner(ev: Evidence) -> Ruling:
    """Which staff does this arc belong to — the one whose NOTEHEADS IT HUGS.

    `OMR_ARC_ATTRIBUTION`'s rule, moved, with its measured constants IMPORTED
    from `tools/omr/export.py` rather than restated so the two cannot drift.

    ⚠️ AN ARC NEED NOT BE DETECTED TWICE FOR THIS TO MATTER, which is what
    makes it different from the notehead contest. A measure cell is padded
    above and below, so where two staves are far apart the upper cell reaches
    ink the lower one does not and the arc exists ONLY in the wrong staff --
    no duplicate-resolution rule can see it. On `brahms-sym1-mvt1` the Timpani
    exported 4 slurs and 1 tie against a truth of ZERO; they are Violin 1's,
    drawn over ITS four-ledger-line notes in the 7.7-space gap.

    ⚠️ DISTANCE TO THE STAFF LINES IS THE TRAP, exactly as it was for notes:
    an engraver opens the gap above a staff *precisely so* its ledger notes
    and their slurs can live there, which puts them nearer the staff above.
    The evidence is the arc's own job instead — it binds a run of noteheads
    and is drawn just clear of them. Measured over the 11-work engraved
    benchmark, 204 of 237 arcs on arc-bearing parts sit under HALF A SPACE
    from the nearest head they cover.

    ⚠️ THE RULE IS COMPARATIVE, and that is not a detail: the clearance tail
    is not clean enough to threshold on. An arc leaves a staff only where
    another staff of the same system explains it BETTER, so this cannot fire
    at all on a one-staff page.

    ⚠️ IT MOVES, IT NEVER DELETES. `drop` was measured at 2,388 edits against
    `move`'s 2,371 -- better arm-for-arm -- and REFUSED, because it gets there
    by emitting 20 fewer slurs, 12 of them REAL: the metric's under-prediction
    reward. Keeping the loser addressable is what lets a later identity
    correction reach it.

    ⚠️ PAGE PIXELS, and the input was in the wrong frame until 2026-09-09.
    `gather_glyph_families` emitted canonical coordinates only -- measured
    inside ONE cell -- so this decision's declared input was present and could
    not answer its own cross-staff question. A row with no page box ABSTAINS
    `no_page_frame`; it is never compared in the cell frame.
    """
    from ...export import (_ARC_RIVAL_MARGIN_SPACES, _ARC_RIVAL_MIN_COVERED,
                           _ARC_RIVAL_NEAR_SPACES, _SLUR_ARC_PAD_NOTEHEADS)

    arcs = ev.rows(Q.ARC_BOX)
    if not arcs:
        return Ruling.abstain("no_evidence")
    arc = arcs[0]
    arc_box = arc.detail.get("bbox_page_px")
    own = ev.subject.at(Kind.STAFF).to_key()
    if not arc_box or len(arc_box) != 4:
        return Ruling.abstain("no_page_frame",
                              frame_note=arc.detail.get("frame_note"))

    system = ev.subject.at(Kind.SYSTEM)
    heads: Dict[str, List[Tuple[float, float, float, float]]] = {}
    for row in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=system):
        if row.detail.get("category") != "notehead":
            continue
        box = row.detail.get("bbox_page_px")
        if not box or len(box) != 4:
            continue
        # ⚠️⚠️ GROUPED BY THE HEAD'S OWNER, NOT BY THE STAFF ITS CELL WAS CUT
        # FROM, and the legacy rule says why in one line: the noteheads "have
        # already been arbitrated across staves and each staff's head set is
        # the one a READER would see". A cross-staff duplicate is filed on the
        # staff that DETECTED it, so grouping by subject would ask "whose
        # heads does this arc hug" against head sets that ownership has
        # already corrected -- comparing the arc against a page nobody sees.
        #
        # This is also what makes A-ORDER-2 pay here: `glyph_owner` is decided
        # BEFORE this runs, so its answer is simply available. On the legacy
        # path the same information exists only because `_dedupe_cross_staff_
        # detections` has already physically moved the detection.
        owner = ev.verdict(Q.GLYPH_OWNER, subject=row.subject)
        staff_key = (owner.value if owner is not None and owner.value
                     else row.subject.at(Kind.STAFF).to_key())
        heads.setdefault(str(staff_key), []).append(
            (float(box[0]), float(box[1]), float(box[2]), float(box[3])))

    spacing: Dict[str, float] = {}
    for row in ev.rows(Q.STAFF_SPACING, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=system):
        try:
            spacing[row.subject.at(Kind.STAFF).to_key()] = float(row.value)
        except (TypeError, ValueError):
            continue

    def clearance(staff_key):
        """`(spaces to the nearest covered head, n covered)` for one staff."""
        hs = heads.get(staff_key) or []
        sp = spacing.get(staff_key)
        if not hs or not sp:
            return None, 0
        # ⚠️ THE SAME PADDED x TEST the pairing makes, for the same reason: the
        # arc is drawn BETWEEN its outer heads, so its ink stops inside both
        # centres and an unpadded test loses the note at each end.
        pad = _SLUR_ARC_PAD_NOTEHEADS * (
            sum(h[2] - h[0] for h in hs) / len(hs))
        covered = [h for h in hs
                   if arc_box[0] - pad <= (h[0] + h[2]) / 2.0 <= arc_box[2] + pad]
        if not covered:
            return None, 0
        gaps = [max(arc_box[1] - h[3], h[1] - arc_box[3], 0.0) for h in covered]
        return min(gaps) / sp, len(covered)

    own_gap, own_n = clearance(own)
    rivals = []
    for staff_key in heads:
        if staff_key == own:
            continue
        gap, n = clearance(staff_key)
        if gap is None or n < _ARC_RIVAL_MIN_COVERED:
            continue
        rivals.append((gap, n, staff_key))
    rivals.sort()

    detail = {"own_clearance_spaces": own_gap, "own_covered": own_n,
              "rivals": [{"staff": k, "clearance_spaces": g, "covered": n}
                         for g, n, k in rivals[:4]]}

    if not rivals:
        # ⚠️ NOT AN ABSTENTION. "No other staff of this system explains this
        # arc better" is a DECISION that it stays where it was found, and the
        # comparative rule cannot say more than that. A one-staff page always
        # lands here, by construction.
        return Ruling(value=own, reason="no_rival_staff",
                      used=(arc.id,), detail=detail)

    best_gap, _best_n, best_key = rivals[0]
    if best_gap > _ARC_RIVAL_NEAR_SPACES:
        return Ruling(value=own, reason="no_better_staff",
                      used=(arc.id,), detail=detail)
    # ⚠️ An arc covering NOTHING in this staff is claimed outright: it binds no
    # note here, so there is nothing for it to be.
    if own_gap is not None and (own_gap - best_gap) < _ARC_RIVAL_MARGIN_SPACES:
        return Ruling(value=own, reason="no_better_staff",
                      used=(arc.id,), detail=detail)
    return Ruling(value=best_key, reason="hugs_noteheads", used=(arc.id,),
                  detail={**detail, "moved_from": own})


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _boxes_overlap(a, b) -> bool:
    """`rhythm._boxes_overlap`, IMPORTED — the measured attachment rule.

    ⚠️ IT IS IMPORTED AND NOT RESTATED. Box overlap with NO tolerance is not
    a choice here: 819 heads take exactly one stem and where none overlaps the
    nearest is 94 px away but for three pairs at 1-2 px. Two spellings of that
    number is how the two drift.
    """
    from .rhythm import _boxes_overlap as _impl
    return _impl(a, b)


def _s4_stem_view(arc_box, heads, stems):
    """S4: where along its STEM does this arc's near edge sit? — RECORDED.

    Sean, 2026-09-11: *"if it connects to the stem near the note it could be
    either but if it is connected to the stems edge away from the notehead
    then it is a slur."*

    ⚠️⚠️ IT READS GEOMETRY AND NEVER A RESOLVED PITCH, and that is the whole
    reason it is allowed here at all. The pitch-reading half of this grammar
    is `OMR_ARC_RECLASS`, measured on both families and REFUSED at +149 scan
    edits *because a scan's resolved pitch at an arc's ends is downstream of
    exactly what scans get wrong*. A stem's box and an arc's box are read off
    the same ink the arc itself is. If this function ever grows a pitch, it
    has become the refused thing.

    ⚠️ AN ARC BOX DOES NOT SAY WHICH EDGE ITS ENDPOINTS ARE ON, and assuming
    is how a frame error looks like a result. A slur drawn OVER its notes is a
    `∩` whose endpoints sit at the bbox's LOWER edge; one drawn under is a `∪`
    whose endpoints sit at the UPPER edge. The side is read off the flanked
    heads.

    ⚠️ NO CONSTANT, BY CONSTRUCTION. `t` is the fraction along the stem from
    the HEAD end (0.0) to the FAR end (1.0) — unit-free, so there is nothing
    here to tune. `same_side` is the test Sean's words actually name: an arc
    on the far side of the head from its stem is CONNECTED TO NO STEM and his
    rule is silent about it. Both are RECORDED, never thresholded, so a later
    session can price any cut from the record alone.

    ⚠️⚠️ AND THE MEASUREMENT SAYS IT SHOULD NOT BE PROMOTED — **NARROW AND
    WIDE, WHICH ARE TWO SEPARATE REFUTATIONS AND THE WIDE ONE IS THE REAL
    ONE.** NARROW (`t`, endpoint on stem ink, 137-143 of 779): the two
    readings' distributions overlap completely (tie 0.057-1.044, slur
    0.213-1.048, widest empty interval **-0.83**, i.e. none) and the one-sided
    sweep is non-monotonic at n=30. That could have been a POWER problem, so
    the rule was re-measured at full width (Sean, 2026-09-15: *the convention
    is not the operationalisation*). WIDE (`t_axis`, contact dropped, **420 of
    779**, one-sided with an explicit abstain population of 359):

      * **SIDE ALONE IS FLAT.** 225 arcs lie on the stem's side and read slur
        **0.4933** against a base of 0.5571 — a lift of **-0.064**. Within
        confidence band, where the detector's class mix cannot confound it,
        the lift is **-0.001** (low) and **-0.030** (high). Sean's cleanest
        binary reading of his own sentence carries no signal on this document.
      * **The distance sweep never reaches significance.** Within band the
        best cell is 13 of 13 at `t_axis >= 2.0`, p = **0.079** — an arc whose
        near edge sits more than twice the head-to-tip distance beyond the
        head, which is barely a stem-connected arc at all.
      * **And conditioned on either other witness S4 adds nothing**: the
        difference in slur share between firing and silent is **negative in
        all four strata** at `t_axis >= 0` and changes sign thereafter.

    ⚠️ Worse, the availability gradient INVERTS the one this family already
    records: the arcs the NARROW form can speak about sit at median confidence
    **0.4196** against **0.5409** for the ones it cannot — so where the
    grammar merely goes quiet on bad ink, S4 goes quiet on GOOD ink and speaks
    preferentially about the weakest readings.
    """
    if not heads:
        return None
    ax0, ay0, ax1, ay1 = arc_box
    head_yc = _median([h[2] for h in heads])
    above = (ay0 + ay1) / 2.0 < head_yc
    near_edge = ay1 if above else ay0

    out = []
    for (_xc, head_box, h_yc, _step), ex in ((heads[0], ax0), (heads[-1], ax1)):
        for sx, sy, sw, sh in [s for s in stems
                               if _boxes_overlap(s, head_box)]:
            sy1 = sy + sh
            head_end, far_end = ((sy, sy1) if abs(sy - h_yc) < abs(sy1 - h_yc)
                                 else (sy1, sy))
            span = far_end - head_end
            if abs(span) < 1e-6:
                continue
            # ⚠️ `t_axis` IS THE WIDENED FORM AND IS RECORDED BESIDE `t`, not
            # instead of it, because they answer different questions and the
            # narrow one was measured first. `t` is the fraction along the
            # STEM's own span and needs the arc's endpoint to lie on stem ink;
            # `t_axis` runs from the NOTEHEAD CENTRE (0.0) to the STEM TIP
            # (1.0) with NO contact requirement, so it is defined for every
            # stemmed head — 420 arcs against 137. A scan breaks ink
            # constantly, and demanding contact is our limitation rather than
            # the engraver's (Sean, 2026-09-15). ⚠️ SIDE is `sign(t_axis)`, so
            # the two widenings are ONE quantity rather than two rules that
            # could drift.
            axis_span = far_end - h_yc
            out.append(dict(
                t=round((near_edge - head_end) / span, 4),
                t_axis=(round((near_edge - h_yc) / axis_span, 4)
                        if abs(axis_span) > 1e-6 else None),
                # `far_end < head_end` in canonical (y-down) coordinates is a
                # stem pointing UP.
                same_side=bool(above == (far_end < head_end)),
                dx_widths=round(abs(ex - (sx + sw / 2.0))
                                / max(head_box[2], 1.0), 4)))
    if not out:
        return None
    # ⚠️ `t_axis` GETS NO SUMMARY FIELD, DELIBERATELY, where `t` has
    # `t_median`. An arc has TWO ends and *"connected to the stem's edge away
    # from the notehead"* is EXISTENTIAL, so `max` and `median` are different
    # readings of Sean's sentence — both were scored (`probe/widen.py`) and
    # neither is chosen. Recording a summary would be this function making
    # that choice for every consumer; the per-endpoint values are raw and a
    # consumer aggregates them the way it can defend.
    return {"endpoints": out, "arc_above_heads": bool(above),
            "t_median": round(_median([e["t"] for e in out]), 4),
            "any_endpoint_on_a_stem": any(
                e["same_side"] and 0.0 <= e["t"] <= 1.0 for e in out)}


def _s6_stack_view(arc_id, arc_box, siblings):
    """S6: is a SECOND arc stacked over or under this one? — RECORDED.

    Sean, 2026-09-11: *"If there are 2 arcs on top of each other then the
    lower is a tie and the upper is a slur."*

    ⚠️ A STACK IS NOT A DUPLICATE, and this document is recorded as full of
    the second: `_place_arcs` has no dedupe and 48 pairs sit in one cell at
    IoU >= 0.7, several disagreeing about their own kind. So the pair's OWN
    geometry travels with it — `y_gap`, `x_overlap_frac`, `iou` — and NOTHING
    here thresholds any of them. A consumer separates the populations by
    measurement; this only says what was seen.

    ⚠️ IT READS ONLY BOXES — no pitch, no step, no duration.

    ⚠️⚠️ AND UNLIKE S4 THE MEASUREMENT SUPPORTS IT, on a narrow and thin
    population. Litolff Beethoven 5 p1-4: **502 arcs get a row here** (any
    x-overlapping sibling, duplicates included), of which 442 have a sibling
    that is also DISJOINT IN Y — a stack candidate; **181 pairs read DIFFERENT
    kinds**, which is the
    only population S6 addresses. Over those, *the lower one is the tie*
    agrees with the detector **0.630** (p = 3e-4) and the agreement is a
    clean DOSE-RESPONSE in the pair's separation — **0.889 / 0.750 / 0.708**
    at 0-1 / 1-2 / 2-3 staff spaces (**0.740 pooled over the 73 pairs inside
    3 spaces, p = 3e-5**) decaying to 0.561 and 0.548 beyond, exactly as an
    engraving rule must. ⚠️ The informative end is the THIN end (n = 9 and
    16) and the numbers are quoted with their n for that reason.

    ⚠️ IT IS NOT THE HUGGING RULE RESTATED — checked, because on arcs above
    the staff the lower arc is also the nearer one. An independent arm
    predicting *the arc nearer the noteheads is the tie* scores **0.517** on
    the same 3-space band where S6 scores 0.740, and the two arms make the
    same prediction on only **43.7%** of pairs. ⚠️ A first version of that
    control was DEGENERATE — it classified each arc against its cell's median
    arc height, which for a same-cell pair IS S6 restricted to an easier
    subset — and reported a flattering 0.702; recorded rather than quietly
    replaced.

    ⚠️ The `arc_owner` split is the positive control that could have failed
    and did not: pairs whose two arcs the record gives to the SAME staff score
    0.655, and the 10 pairs given to DIFFERENT staves score **0.200** — the
    measure-cell padding reaching into the neighbour, which is not a stack.

    ⚠️⚠️ **IT SURVIVED EVERY RELAXATION OF WHAT COUNTS AS A STACK** (2026-09-15,
    `probe/widen_s6.py`): an x GAP of up to 1.0 arc widths, a y OVERLAP of up
    to half the shallower box, and `arc_owner` as the pairing rather than
    geometry. Candidate pairs move only **428 -> 463 (+8%)** and agreement
    holds at **0.62-0.66**; the tight band is **73 -> 77 pairs at 0.740**, and
    the dose-response is if anything sharper on the loosest relaxation (0-1
    space **10 of 11**, p = 0.006). So the widening buys almost no reach and
    costs no agreement — the result is robust to how a stack is defined rather
    than fitted to one definition. **Restricting to a shared `arc_owner` is
    the one relaxation that IMPROVES it (0.663, p = 1e-5).**

    ⚠️⚠️ **AND THE JOINT RESULT IS BIGGER THAN EITHER WITNESS.** Over the 83
    arcs where S6 and the position grammar (S2/S5) both speak they CONCUR on
    only 40 — near-independent — and where they concur, agreement with the
    reading is **0.750** against S2/S5 alone at 0.602 and S6 alone at 0.639 on
    that same population. ⚠️ **Conditioning on two noisy predictors agreeing
    raises measured accuracy even when one is pure noise**, so a permutation
    null was run before this was believed: shuffling S2/S5's labels 20,000
    times within the joint population gives a median of 0.625 and a p95 of
    0.711, and the observed 0.750 lands at **p = 0.010**. ⚠️ The finding is
    stranger than it looks — S2/S5 is MARGINALLY UNINFORMATIVE (0.5043 over
    345 arcs, against a majority-class baseline of 0.5275, i.e. worse than
    always saying slur) and JOINTLY informative.
    """
    ax0, ay0, ax1, ay1 = arc_box
    out = []
    for sid, box in siblings:
        if sid == arc_id:
            continue
        bx0, by0, bx1, by1 = box
        ox = min(ax1, bx1) - max(ax0, bx0)
        if ox <= 0:
            continue
        oy = min(ay1, by1) - max(ay0, by0)
        inter = max(0.0, ox) * max(0.0, oy)
        union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
        out.append(dict(
            other=sid,
            x_overlap_frac=round(ox / max(1.0, min(ax1 - ax0, bx1 - bx0)), 4),
            y_gap=round(-oy, 2),
            iou=round(inter / union, 4) if union > 0 else 0.0,
            # ⚠️ `this_is_upper` is the fact S6 turns on, and it is stated
            # about THIS arc so the row reads without the sibling's own row.
            this_is_upper=bool((ay0 + ay1) < (by0 + by1))))
    return out


@decision(
    quantity=Q.ARC_KIND,
    checkable=Checkable.MIXED,
    checked_by=(
        "a TIE joins two heads of the SAME staff step; an arc whose flanked heads sit on different steps is a SLUR",
        "of two arcs STACKED over the same notes the lower is a tie and the upper a slur (Sean, 2026-09-11) -- recorded, never acted on",
    ),
    implicates=(Q.ARC_KIND, Q.NOTEHEAD_STAFF_POSITION, Q.CLEF),
    composed_from=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.STEM),
    scope=Kind.GLYPH,
    # ⚠️ `Q.GLYPH_BOX` is declared because a notehead's STEP row carries no x:
    # the step is joined to a position through the box on the SAME glyph. The
    # harness refused the read until it was declared (`UndeclaredEvidence`),
    # which is `Evidence` doing its job -- a decision may only read what it
    # says it reads, so `missing` and `declined` can mean something.
    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.STEM),
    subjects_from=Q.ARC_BOX,
    reasons=("tie", "slur", "no_arc_box", "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_arc_kind(ev: Evidence) -> Ruling:
    """Is this arc a TIE or a SLUR — the reading decides, the grammar RECORDS.

    ⚠️⚠️ THIS DECISION SHIPS WITH A MEASURED REFUSAL ATTACHED AND MUST NOT
    QUIETLY UNDO IT. The position-grammar veto exists as `OMR_ARC_RECLASS`
    and is default-OFF for a priced reason: engraved 0.1306 -> 0.1306
    (+2 edits, 24 firings) but scan 0.8387 -> 0.8391, **+130 edits, ALL of
    them in the tie->slur half** -- because a scan's resolved pitch at an
    arc's ends is downstream of exactly what scans get wrong. Turning the
    grammar into a GATE here would enable half a refused flag by the back
    door, on the path with the least measurement behind it.

    So the DETECTOR'S CLASS DECIDES and the grammar is recorded beside it.
    That is this project's governing principle applied literally -- additive
    evidence, never a gate (A-GROUP-3) -- and it is the strictly more useful
    of the two, because until now NOTHING on this path recorded either. The
    disagreement rate between reading and grammar is a number no arm has ever
    produced; `detail["grammar"]` is where it accumulates, and a later session
    can price the veto on this path from the record alone.

    ⚠️ STAFF STEPS, NEVER SPELLED PITCHES. The far head of a cross-barline tie
    does not restate its accidental and the resolver spells it plain, so a
    spelled-pitch key breaks truth-matched ties (+21 engraved edits, every
    loss a same-step `F#4 -> F4` pair). `Q.NOTEHEAD_STAFF_POSITION` is a
    STEP -- measured off the staff lines, clef-free -- which is why it and not
    `Q.PITCH` is the input.

    ⚠️ THE FLANKED HEADS ARE READ IN THE CELL'S OWN CANONICAL FRAME, and here
    that is CORRECT rather than a lapse: both the arc and the heads it flanks
    were cut from ONE cell, so they share a frame by construction. It is
    `arc_owner` -- which asks about OTHER staves -- that needs page pixels.
    """
    arcs = ev.rows(Q.ARC_BOX)
    if not arcs:
        return Ruling.abstain("no_arc_box")
    arc = arcs[0]
    kind = "tie" if str(arc.value).lower().startswith("tie") else "slur"

    # ⚠️ AN ARC IS NARROWER THAN THE RUN IT BINDS -- it is drawn BETWEEN its
    # outer noteheads, so its ink stops inside both outer centres. The legacy
    # pairing pads the box by a notehead width for exactly this reason;
    # unpadded, the Contrabass read `n1 -> n4` in every bar whose truth is
    # `n0 -> n5`. Here the pad is expressed in the arc's own height, which is
    # the only size this row carries.
    arc_y0 = float(arc.detail.get("y0", 0))
    arc_y1 = float(arc.detail.get("y1", 0))
    pad = max(arc_y1 - arc_y0, 1.0)
    x0 = float(arc.detail.get("x0", 0)) - pad
    x1 = float(arc.detail.get("x1", 0)) + pad

    cell = ev.subject.at(Kind.CELL)
    boxes = {r.subject.to_key(): r for r in
             ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell)}
    flanked = []
    #: `(x_centre, (x, y, w, h), y_centre, step)` for S4 — the SAME heads, in
    #: the SAME order, so the two witnesses can never be reading different
    #: populations of one arc.
    geom = []
    for row in ev.rows(Q.NOTEHEAD_STAFF_POSITION,
                       scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        box = boxes.get(row.subject.to_key())
        if box is None:
            continue
        value = box.value
        if not isinstance(value, (list, tuple)) or len(value) < 5:
            continue
        hx, hy = float(value[1]), float(value[2])
        hw, hh = float(value[3]), float(value[4])
        xc = hx + hw / 2.0
        if x0 <= xc <= x1:
            flanked.append((xc, row.detail.get("rounded"), row.id))
            geom.append((xc, (hx, hy, hw, hh), hy + hh / 2.0,
                         row.detail.get("rounded")))
    flanked.sort()
    geom.sort(key=lambda g: g[0])

    grammar = {"flanked_heads": len(flanked), "reading": kind}

    # ⚠️ TWO MORE WITNESSES, RECORDED AND NEVER ACTED ON — Sean's S4 and S6.
    # Both read BOXES ONLY. The docstring says why that distinction is what
    # lets them be here at all while `OMR_ARC_RECLASS`'s pitch half stays
    # refused, and each helper carries its own measurement.
    stems = [tuple(float(v) for v in r.value[:4])
             for r in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS,
                              subject=cell)
             if isinstance(r.value, (list, tuple)) and len(r.value) >= 4]
    s4 = _s4_stem_view((x0 + pad, arc_y0, x1 - pad, arc_y1), geom, stems)
    if s4 is not None:
        grammar["s4_stem_position"] = s4
    siblings = [(r.subject.to_key(),
                 (float(r.detail.get("x0", 0)), float(r.detail.get("y0", 0)),
                  float(r.detail.get("x1", 0)), float(r.detail.get("y1", 0))))
                for r in ev.rows(Q.ARC_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                 subject=cell)]
    s6 = _s6_stack_view(ev.subject.to_key(),
                        (x0 + pad, arc_y0, x1 - pad, arc_y1), siblings)
    if s6:
        grammar["s6_stacked_with"] = s6

    if len(flanked) >= 2:
        first, last = flanked[0], flanked[-1]
        same_step = (first[1] is not None and first[1] == last[1])
        grammar.update(
            first_step=first[1], last_step=last[1],
            says="tie" if same_step else "slur",
            # ⚠️ RECORDED, NOT ACTED ON. See the docstring: the tie->slur
            # half of this comparison measured +130 edits on a scan.
            agrees_with_reading=((kind == "tie") == bool(same_step)))
    else:
        grammar["says"] = None
        grammar["why"] = ("fewer than two noteheads under the arc's padded "
                          "span -- no pair to compare steps across")

    return Ruling(value=kind, reason=kind,
                  used=(arc.id,) + tuple(f[2] for f in flanked),
                  detail={"grammar": grammar,
                          "detector_class": str(arc.value),
                          "confidence": arc.score})


@decision(
    quantity=Q.ARTICULATION_OWNER,
    composed_from=(Q.ARTICULATION_MARK, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    wants=(Q.ARTICULATION_MARK, Q.GLYPH_BOX),
    subjects_from=Q.ARTICULATION_MARK,
    reasons=("nearest_on_declared_side", "no_notehead", "no_side_declared",
             "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_articulation_owner(ev: Evidence) -> Ruling:
    """Which notehead a staccato, accent, marcato, tenuto or staccatissimo is
    printed against.

    The rule is the one the engraving makes true and it is NOT re-derived here:
    a mark is printed directly above or below its notehead, so it goes to the
    notehead nearest it in X **on the side its own class names**, within
    `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS`. `transcribe._attach_articulations_in_cell`
    has said that since the seventh export gap was closed, and its constant is
    IMPORTED rather than restated -- it was swept over eight engraved works and
    sits on a flat plateau (0.50 through 2.50 identical, 197 placed at
    precision 0.980) with a cliff below at 0.30, so this project has paid for
    that number once.

    ⚠️ THE UNIT IS A NOTEHEAD WIDTH, NOT THE MARK'S OWN BOX. That is the
    mistake the augmentation-dot gate made and paid 193 edits for: a mark's
    bounding box is small and mostly detector noise, so a threshold derived
    from it moves with the noise rather than with the engraving.

    ⚠️ A MARK WITH NO NOTEHEAD ON THE CORRECT SIDE ABSTAINS rather than taking
    the nearest thing available. 21 of 218 across the legacy corpus do, and
    abstaining there is why that precision is 0.980 -- a mark labelled `Above`
    sitting below every notehead in the cell belongs to none of them.

    ⚠️ THE CELL'S OWN CANONICAL FRAME IS CORRECT HERE, and saying so matters
    because the sibling decision one function up needs the opposite. An
    articulation and the notehead it names were cut from ONE cell, so they
    share a frame by construction; it is `arc_owner`, which asks about OTHER
    staves, that needs page pixels. A canonical x compared across two staves
    is meaningless -- the fault that made `Q.ONSET_COLUMN` report 1,062
    columns of nothing.

    ⚠️ `no_side_declared` HAS ZERO REACH ON THE DOCUMENT THIS LANDED WITH and
    is here anyway. `class_aliases.COARSER_THAN_CANONICAL` records
    `articulationAccent` / `Staccato` / `Tenuto` as coarser spellings that
    carry no side, and `_artic_side` returns None for them rather than
    guessing. All 24 marks on Litolff `984073` p1-3 name a side, so that branch
    is unexercised by the page and is tested directly instead.
    """
    marks = ev.rows(Q.ARTICULATION_MARK)
    if not marks:
        return Ruling.abstain("no_evidence")
    mark = marks[0]
    kind = _legacy_articulation.articulation_kind(str(mark.value))
    if kind is None:
        # The class names no side, or names a mark outside the five MusicXML
        # articulations the legacy rule exports. Recorded as its own reason:
        # "I could not read this mark" and "there was no notehead for it" send
        # the next reader to different places.
        return Ruling.abstain("no_side_declared",
                              detector_class=str(mark.value))
    name, above = kind

    cell = ev.subject.at(Kind.CELL)
    heads = [r for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                subject=cell)
             if (r.detail or {}).get("category") == "notehead"
             and isinstance(r.value, (list, tuple)) and len(r.value) >= 5]
    if not heads:
        return Ruling.abstain("no_notehead", articulation=name)

    # ⚠️ THE MEDIAN NOTEHEAD WIDTH, exactly as the legacy pass takes it -- one
    # clipped or merged detection must not set the limit for the whole cell.
    widths = sorted(float(h.value[3]) for h in heads)
    nh_width = widths[len(widths) // 2] or 1.0
    limit = nh_width * _legacy_articulation._ARTIC_MAX_DX_NOTEHEAD_WIDTHS

    mx = (float(mark.detail.get("x0", 0.0))
          + float(mark.detail.get("x1", 0.0))) / 2.0
    my = (float(mark.detail.get("y0", 0.0))
          + float(mark.detail.get("y1", 0.0))) / 2.0

    best: Optional[Tuple[float, object]] = None
    for h in heads:
        _cls, hx, hy, hw, hh = h.value[:5]
        hyc = float(hy) + float(hh) / 2.0
        # ⚠️ LARGER CANONICAL y IS LOWER ON THE PAGE, so a mark printed ABOVE
        # its notehead has the SMALLER y of the two. Stated because the sign
        # is the whole of the side test and reads backwards.
        if above and my >= hyc:
            continue
        if not above and my <= hyc:
            continue
        dx = abs(mx - (float(hx) + float(hw) / 2.0))
        if dx > limit:
            continue
        if best is None or dx < best[0]:
            best = (dx, h)
    if best is None:
        return Ruling.abstain("no_notehead", articulation=name,
                              side="above" if above else "below",
                              notehead_width=nh_width,
                              limit_canonical_px=limit)

    dx, head = best
    return Ruling(
        value=head.subject.to_key(), reason="nearest_on_declared_side",
        used=(mark.id, head.id),
        # ⚠️ THE KIND TRAVELS WITH THE OWNER. The quantity names the NOTEHEAD,
        # and an exporter holding only that would have to re-read the mark's
        # class to know whether to write `<staccato/>` or `<accent/>` -- which
        # is the re-derivation this stage exists to remove.
        detail={"articulation": name,
                "side": "above" if above else "below",
                "dx_canonical_px": dx,
                "dx_notehead_widths": (dx / nh_width) if nh_width else None,
                "detector_class": str(mark.value),
                "confidence": mark.score})


#: ── ROADMAP 2.7, the printed in-bar accidental ──────────────────────────────
#:
#: How far to the RIGHT of an accidental its notehead may stand, in STAFF
#: SPACES, measured from the glyph's right edge to the head's left edge.
#:
#: ⚠️⚠️ MEASURED, NOT INHERITED. The legacy pair rule
#: (`transcribe._pair_accidentals_to_noteheads`) puts NO bound on x at all --
#: it scores `x_dist + 3 * y_dist` over every head in the cell and takes the
#: argmax -- so a glyph whose own head the detector missed claims a note four
#: beats away and calls it a reading. The geometry is copied; the missing
#: bound is not.
#:
#: The window is the histogram's own MINIMUM, on both documents
#: (`benchmarks/omr-accidental-2026-09/probe/gap_histogram.py`, run over the
#: two whole-movement records). Litolff, per 0.25-space bin from 0:
#: 500 · 519 · 116 · 30 · 15 · 14 · 14 · **4** · 8 · 6 · 9 · 4 · 15 …
#: Breitkopf: 2269 · 2949 · 212 · 74 · 77 · 117 · 76 · **51** · 54 · 69 · 41 …
#: Both fall to their lowest bin at **[1.75, 2.0)** and then flatten onto a
#: roughly uniform background -- the population with no accidental of its own,
#: which has no window because it is not a pairing. 1.75 keeps 89 % of the
#: Litolff pairs and cuts at the gap rather than at a round number.
_ACC_MAX_DX_SPACES = 1.75

#: How far in STAFF POSITIONS (half-spaces) the head's centre may sit from the
#: accidental's own anchored position.
#:
#: ⚠️ THE UNIT IS THE POSITION AND NOT THE GLYPH'S OWN BOX, which is the
#: correction `adjudicate_articulation_owner` states one function up: a mark's
#: bounding box is small and mostly detector noise, so a threshold derived
#: from it moves with the noise. The legacy rule's `0.6 * the accidental's own
#: height` is exactly that mistake, and one diatonic step is 1.0 of THIS unit
#: -- so this is the number that says whether the next step could also fit.
#:
#: Measured inside the x window above, per 0.1-position bin, the offset falls
#: off a cliff at the same place on both plates: Litolff … 1.2:58 · 1.3:32 ·
#: **1.4:10** · 1.5:12; Breitkopf … 1.2:277 · 1.3:189 · **1.4:67** · 1.5:25.
#: A 3.2x and a 2.8x drop at the same bin, on two publishers whose failure
#: modes are opposite (Litolff MERGES, Breitkopf SHATTERS).
_ACC_MAX_DY_POSITIONS = 1.4

#: Two heads are INDISTINGUISHABLE in height when their offsets differ by less
#: than this, in staff positions.
#:
#: ⚠️ HALF A DIATONIC STEP, AND IT IS DERIVED RATHER THAN SWEPT: two heads one
#: step apart differ by 1.0 position, so a glyph standing exactly between them
#: is 0.5 from each and the difference is 0 -- the case this abstention exists
#: for. A glyph sitting ON one of them is 0.0 and 1.0, a difference of 1.0.
#: Anything under half a step means the geometry does not separate them, and
#: an argmax there would be a coin flip recorded as a reading.
_ACC_AMBIGUOUS_MARGIN_POSITIONS = 0.5


@decision(
    quantity=Q.ACCIDENTAL_OWNER,
    composed_from=(Q.ACCIDENTAL_STAFF_POSITION, Q.NOTEHEAD_STAFF_POSITION,
                   Q.GLYPH_BOX, Q.CELL_STAFF_SPACE),
    scope=Kind.GLYPH,
    wants=(Q.ACCIDENTAL_STAFF_POSITION, Q.NOTEHEAD_STAFF_POSITION,
           Q.GLYPH_BOX, Q.CELL_STAFF_SPACE),
    subjects_from=Q.ACCIDENTAL_STAFF_POSITION,
    reasons=("immediately_right_same_position", "ambiguous_height",
             "no_candidate", "no_unit", "no_evidence"),
    checked_by=(
        "L32: an accidental stands BEFORE its note, at the same staff "
        "position -- SIDE and HEIGHT, two constraints and not one",
        "C21: the alteration it states holds for that letter and octave to "
        "the end of the bar, so a glyph owned by the wrong head is wrong for "
        "every later note of that pitch in the bar and not only for one",
    ),
    # ⚠️ THE GROUP CONTAINS THIS DECISION ITSELF. A check that implicates only
    # its inputs has quietly decided the reading is innocent and the ruler is
    # to blame -- which is exactly the move `implicates` exists to forbid.
    implicates=(Q.ACCIDENTAL_OWNER, Q.ACCIDENTAL_STAFF_POSITION,
                Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.CELL_STAFF_SPACE,
                Q.MEASURE_PARTITION),
    checkable=Checkable.MIXED,
    mode=Mode.ADDITIVE,
)
def adjudicate_accidental_owner(ev: Evidence) -> Ruling:
    """Which notehead a PRINTED sharp, flat, natural or double alters.

    The rule is the engraving's, and it is TWO constraints rather than one
    (L32): the head stands to the accidental's RIGHT, and it stands at the
    accidental's own HEIGHT. `docs/engraving-conventions.md` puts the reason
    in one sentence -- *"the height constraint alone rules out most
    mis-attachments in a dense chord"* -- and a chord is exactly where the
    side constraint alone has nothing to say, because every member of it is to
    the right of the glyph.

    ⚠️⚠️ THE GEOMETRY IS THE LEGACY PAIR RULE'S AND THE BOUNDS ARE NOT.
    `transcribe._pair_accidentals_to_noteheads` is copied rather than imported
    (the legacy path is FROZEN and its flags may not be read from here), and
    what is copied is the shape: candidates reach to or past the glyph's right
    edge, and the nearer in height wins. What is NOT copied is its unbounded x
    and its `0.6 * the accidental's own height` -- an argmax over the whole
    cell against a threshold taken from the mark's own box. Both bounds here
    are measured off the two whole-movement records and both are stated with
    the histogram they came from.

    ⚠️ IT ABSTAINS WHERE TWO HEADS FIT, and that is the difference between
    this and the rule it replaces. The legacy pass always answers: its score
    orders every head in the cell and something always wins. Here, two heads
    whose offsets differ by less than half a diatonic step are not separated
    by the geometry, and `ambiguous_height` says so. An accidental with no
    head in the window at all is `no_candidate` -- which on these plates is
    not rare and is not a defect: 195 of the 1,531 Litolff glyphs have no
    notehead to their right in their own cell at all.

    ⚠️ A CHORD'S UNISON IS NOT AN AMBIGUITY. Two heads at ONE x and one
    position are one note detected twice, or two voices sounding it; the
    accidental governs the pitch either way, so the test for ambiguity also
    requires the two heads to stand in DIFFERENT COLUMNS -- more than a
    notehead's width apart in x. Without that clause every doubled detection
    on a scan would abstain, which is a refusal manufactured by the detector
    rather than by the page.

    ⚠️ THE CELL IS THE BAR AND THE SCOPE STOPS THERE. This decision names one
    head; C21's carry to the end of the bar is an EVALUATE consequence
    (`apply_printed_accidental`) and not this rule's business, because what
    FOLLOWS from an owned glyph is forced and what a glyph OWNS is weighed.
    """
    rows = ev.rows(Q.ACCIDENTAL_STAFF_POSITION)
    if not rows:
        return Ruling.abstain("no_evidence")
    acc = rows[0]
    detail = acc.detail or {}
    alteration = detail.get("alteration")
    if alteration is None:
        return Ruling.abstain("no_evidence")

    cell = ev.subject.at(Kind.CELL)
    unit_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                        subject=cell)
    if not unit_rows or not unit_rows[0].value:
        # ⚠️ THE UNIT IS NOT DEFAULTED. `_ACC_MAX_DX_SPACES` is expressed in
        # staff spaces precisely so it survives a rescaled cell; substituting
        # a constant would make the bound mean a different distance on every
        # staff, which is the frame fault `Q.ONSET_COLUMN` paid for.
        return Ruling.abstain("no_unit")
    space = float(unit_rows[0].value)

    heads = {}
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if (r.detail or {}).get("category") != "notehead":
            continue
        if not isinstance(r.value, (list, tuple)) or len(r.value) < 5:
            continue
        heads[r.subject.to_key()] = r
    if not heads:
        return Ruling.abstain("no_candidate", alteration=alteration,
                              why="no notehead in this cell")

    # ⚠️ THE HEAD'S POSITION IS READ, NOT RE-DERIVED. `Q.NOTEHEAD_STAFF_POSITION`
    # is the same measurement off the same grid that this glyph's own row was
    # taken from, so comparing them is a subtraction. Re-deriving it here from
    # the box and a line list would be a second spelling of one arithmetic --
    # the fault `positions.py` imports `gather.py`'s predicates to avoid.
    pos_of = {}
    for r in ev.rows(Q.NOTEHEAD_STAFF_POSITION, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if isinstance(r.value, (int, float)):
            pos_of[r.subject.to_key()] = (float(r.value), r)

    ax1 = float(detail.get("x1", 0.0))
    apos = float(acc.value)

    cands = []
    for key, row in heads.items():
        _cls, hx, hy, hw, hh = row.value[:5]
        if float(hx) + float(hw) < ax1:
            continue                    # the head does not reach past the glyph
        dx = max(0.0, float(hx) - ax1) / space
        if dx > _ACC_MAX_DX_SPACES:
            continue
        got = pos_of.get(key)
        if got is None:
            continue                    # no clef-free position: nothing to compare
        hpos, hrow = got
        dpos = abs(hpos - apos)
        if dpos > _ACC_MAX_DY_POSITIONS:
            continue
        cands.append((dpos, dx, key, row, hrow, float(hx), float(hw), hpos))

    if not cands:
        return Ruling.abstain(
            "no_candidate", alteration=alteration,
            detector_class=detail.get("detector_class"),
            heads_in_cell=len(heads),
            max_dx_spaces=_ACC_MAX_DX_SPACES,
            max_dy_positions=_ACC_MAX_DY_POSITIONS)

    cands.sort(key=lambda t: (t[0], t[1]))
    best = cands[0]
    widths = sorted(float(r.value[3]) for r in heads.values())
    nh_width = widths[len(widths) // 2] or 1.0
    for other in cands[1:]:
        if other[0] - best[0] >= _ACC_AMBIGUOUS_MARGIN_POSITIONS:
            break
        # ⚠️ THE ONE EXEMPTION, AND IT IS NARROW ON PURPOSE: the two boxes are
        # THE SAME NOTE -- one column AND one staff position -- so they are a
        # unison in two voices, or one head the detector drew twice. The
        # accidental governs that pitch either way. A CHORD whose two heads
        # share an x and stand a STEP apart is NOT exempt and must abstain,
        # which is the case the first draft of this clause swallowed.
        same_column = abs((other[5] + other[6] / 2.0)
                          - (best[5] + best[6] / 2.0)) <= nh_width
        same_position = abs(other[7] - best[7]) < 0.5
        if same_column and same_position:
            continue
        return Ruling.abstain(
            "ambiguous_height", alteration=alteration,
            candidates=[best[2], other[2]],
            offsets_positions=[round(best[0], 3), round(other[0], 3)],
            margin_positions=_ACC_AMBIGUOUS_MARGIN_POSITIONS)

    dpos, dx, key, _row, hrow, _hx, _hw, _hp = best
    return Ruling(
        value=key, reason="immediately_right_same_position",
        used=(acc.id, hrow.id),
        # ⚠️ THE ALTERATION TRAVELS WITH THE OWNER, the rule
        # `Q.ARTICULATION_OWNER` states: a consumer holding only the notehead
        # would have to re-read the glyph's class to know what to write.
        detail={"alteration": alteration,
                "detector_class": detail.get("detector_class"),
                "dx_spaces": round(dx, 3),
                "dy_positions": round(dpos, 3),
                "accidental_position": round(apos, 3),
                "anchor_fraction": detail.get("anchor_fraction"),
                "confidence": detail.get("confidence")})


#: How far either side of a hairpin's own cell a notehead may stand and still
#: anchor it. ⚠️ NOT A NEW CONSTANT: it is `_wedge_anchors`' own `+1` measure
#: window, which that function's docstring justifies ("the truth's own
#: crescendo on that page runs `m5 -> m6`, ending on the next bar's downbeat")
#: and which is enforced there by `lo, hi = first_m - 1, last_m + 1`. Stated
#: as a name here because the staged path has no `measures` list to slice.
_WEDGE_WINDOW_CELLS = 1


@decision(
    quantity=Q.WEDGE_ANCHOR,
    composed_from=(Q.WEDGE_BOX, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    wants=(Q.WEDGE_BOX, Q.GLYPH_BOX, Q.GLYPH_OWNER, Q.VOICES),
    subjects_from=Q.WEDGE_BOX,
    reasons=("nearest_either_side", "no_anchor", "no_page_frame",
             "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_wedge_anchor(ev: Evidence) -> Ruling:
    """The two notes one hairpin opens and closes on.

    ⚠️ A SLUR IS DRAWN OVER ITS NOTES; A HAIRPIN BETWEEN THEM, which is where
    these two spanners stop being one problem. `_noteheads_under` -- the
    obvious reuse, and the first thing tried when the legacy rule was built --
    returns NOTHING: measured on the Mahler 5 fixture, the Trumpet's
    diminuendo spans page x 5922-6068 in a bar whose only notehead spans
    5817-5897, not one pixel of overlap, and an overlap test scores 0 of 4. So
    the edges are POINTERS, and `_WEDGE_START_RULE` is `nearest` rather than
    the "last note at or before the edge" that looks right -- measured, the
    ink begins 26 px LEFT of the note it starts on, so `before` reaches back
    past the answer and pairs 1 of 8 against `nearest`'s 4 of 4 exact.

    ⚠️⚠️ THE RULE IS `export._wedge_anchors_from_candidates`, IMPORTED AND
    CALLED, NOT PORTED -- and that was the one design decision this wiring
    needed. Its three constants (`_WEDGE_ANCHOR_PAD_NOTEHEADS`,
    `_WEDGE_START_RULE`, `_WEDGE_STOP_REACH_NOTEHEADS`) are each MEASURED and
    each carries a paragraph of justification; restating them here would give
    this project two copies of numbers it paid to measure once, which is the
    drift `LETTER_METERS`, `rhythm._REST_DURATIONS` and the arc-attribution
    constants are all imported to prevent. The alternative -- calling the
    whole legacy function from the EXPORTER, the `_pair_arcs` precedent --
    was refused for a different reason: it would leave this decision with
    nothing to decide, and the point of the stage is that the answer and the
    evidence for it are on the record. So the legacy function was SPLIT: the
    half that knows about `measures` shims stayed, the RULE moved into a pure
    core taking page-pixel candidates, and the legacy path is byte-identical
    (`benchmarks/omr-staged-wedge-2026-09/probe/legacy_identity.py`).

    ⚠️ PAGE PIXELS, AND A ROW WITHOUT THEM ABSTAINS. `gather_wedge_boxes`
    emits from two readers: `cv_hairpins`, which searches one staff's band at
    a time in page pixels and carries `bbox_page_px`, and the DETECTOR, whose
    row carries a cell-frame box and no page box at all. Two staves' canonical
    frames coincide by construction, so comparing a cell-frame wedge against a
    page-frame notehead is the frame error that made `Q.ONSET_COLUMN` report
    1,062 columns of nothing. `no_page_frame` is therefore a REAL branch and
    not a defensive one -- on the Breitkopf Brahms 1 record it is exactly 1 row
    of 47.

    ⚠️ NO MERGE ACROSS BARLINES, and that is a property of the READER rather
    than a simplification. `_merge_arcs_across_barlines` exists because cells
    are cut per measure and an arc crossing a barline is DETECTED AS TWO;
    `hairpin_detection` reads the WHOLE PAGE one staff-band at a time, so a CV
    hairpin is never cut. One row is one hairpin, and `segments` collapses to
    the single box this subject carries.

    ⚠️ THE HEADS ARE THE OWNER'S, NOT THE CELL'S -- `arc_owner`'s rule, for
    its reason: a cross-staff duplicate is filed on the staff that DETECTED
    it, so grouping by subject would anchor a hairpin against a page nobody
    sees. `glyph_owner` is decided before this runs (A-ORDER-2), so its answer
    is simply available.

    ⚠️ A NOTE NO `Q.VOICES` VERDICT MENTIONS IS VOICE 0, which is not a guess:
    it is the identical default `_paired_spans` and `_voice_of_notehead`
    already apply, so a bar whose voices were never decided behaves exactly as
    the legacy path does. `voices_read` is recorded on the verdict so a reader
    can tell "one voice" from "voices unknown" -- the two are the same NUMBER
    and different FACTS.
    """
    from ...export import _wedge_anchors_from_candidates

    wedges = ev.rows(Q.WEDGE_BOX)
    if not wedges:
        return Ruling.abstain("no_evidence")
    wedge = wedges[0]
    box = wedge.detail.get("bbox_page_px")
    if not box or len(box) != 4:
        return Ruling.abstain("no_page_frame",
                              reader=wedge.reader,
                              kind=str(wedge.value),
                              note=("this reader files a cell-frame box; "
                                    "comparing it to a page-frame notehead "
                                    "is the Q.ONSET_COLUMN frame error"))
    # ⚠️ CORNERS, NOT WIDTH. `bbox_page_px` is `[x0, y0, x1, y1]` and the
    # legacy `segments` are `[x, y, w, h]`; both conventions live in this repo
    # and confusing them does not raise -- it silently reads a 140px hairpin
    # as a 1190px one, which is the mutation that survived every assertion in
    # the arc export's first battery. The pure core takes `left` and `right`
    # outright so neither caller has to spell a width.
    left, right = float(box[0]), float(box[2])

    cell = ev.subject.at(Kind.CELL)
    here = cell.cell if cell is not None else None
    own = ev.subject.at(Kind.STAFF).to_key()
    system = ev.subject.at(Kind.SYSTEM)

    candidates: List[Tuple[int, float, str]] = []
    widths: List[float] = []
    voice_of: Dict[str, int] = {}
    for row in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=system):
        if row.detail.get("category") != "notehead":
            continue
        hbox = row.detail.get("bbox_page_px")
        if not hbox or len(hbox) != 4:
            continue
        head_cell = row.subject.at(Kind.CELL)
        if head_cell is None or here is None:
            continue
        if abs(int(head_cell.cell) - int(here)) > _WEDGE_WINDOW_CELLS:
            continue
        owner = ev.verdict(Q.GLYPH_OWNER, subject=row.subject)
        staff_key = (owner.value if owner is not None and owner.value
                     else row.subject.at(Kind.STAFF).to_key())
        if str(staff_key) != str(own):
            continue
        x0, _y0, x1, _y1 = (float(v) for v in hbox)
        candidates.append((int(head_cell.cell), (x0 + x1) / 2.0,
                           row.subject.to_key()))
        widths.append(x1 - x0)

    if not candidates:
        return Ruling.abstain("no_anchor", kind=str(wedge.value),
                              window_cells=_WEDGE_WINDOW_CELLS,
                              note="no notehead this staff owns in the "
                                   "hairpin's own bar or either neighbour")

    voices_read = 0
    seen_cells = {c[0] for c in candidates}
    for c_index in sorted(seen_cells):
        sub = R.cell(ev.subject.page, ev.subject.system,
                     ev.subject.staff, c_index)
        v = ev.verdict(Q.VOICES, subject=sub)
        if not v or v.outcome != Outcome.DECIDED:
            continue
        value = v.value or {}
        if int(value.get("n_voices") or 1) < 2:
            continue
        voices_read += 1
        in_both = set(value.get("rests_in_every_voice") or ())
        for number, glyphs in enumerate(value.get("voices") or (), start=1):
            for gi in set(glyphs) - in_both:
                voice_of[R.glyph(ev.subject.page, ev.subject.system,
                                 ev.subject.staff, c_index, gi).to_key()] = \
                    number

    anchors = _wedge_anchors_from_candidates(
        candidates, widths, left, right, lambda key: voice_of.get(key, 0))
    if anchors is None:
        # ⚠️ The core returns None only where the stop would precede the
        # start, which its own comment calls impossible; reported as
        # `no_anchor` with the reason named rather than silently.
        return Ruling.abstain("no_anchor", kind=str(wedge.value),
                              note="the rule found a stop before its start")

    (start_cell, start_x), (stop_cell, stop_x), start_key, stop_key = anchors
    return Ruling(
        value=[str(start_key), str(stop_key)],
        reason="nearest_either_side",
        used=(wedge.id,),
        # ⚠️ THE KIND TRAVELS WITH THE ANCHOR, as it does for an articulation:
        # `<wedge type="crescendo">` needs the direction, and an exporter
        # holding only the two note keys would have to re-read the hairpin's
        # class to get it -- the re-derivation this stage exists to remove.
        detail={"kind": str(wedge.value),
                "start_cell": int(start_cell), "stop_cell": int(stop_cell),
                "start_x_page": float(start_x), "stop_x_page": float(stop_x),
                "left_page": left, "right_page": right,
                "n_candidates": len(candidates),
                "reader": wedge.reader,
                # ⚠️ "one voice" and "voices unknown" are the same number and
                # different facts; the second is what a later reader needs to
                # know before trusting a cross-voice refusal that never fired.
                "voices_read": voices_read,
                "degenerate": (start_cell, start_x) == (stop_cell, stop_x)})


#: Detector categories a fermata can hang over. ⚠️ BOTH, AND THE REST IS THE
#: POINT: on a conductor's page the commonest carrier of a pause is a
#: whole-bar rest, not a note. `export.annotate_fermatas` says so in its own
#: docstring and pairs against notes and rests alike; a notehead-only rule
#: would miss the case the mark exists for.
_FERMATA_CARRIERS = ("notehead", "rest")


@decision(
    quantity=Q.FERMATA_OWNER,
    composed_from=(Q.FERMATA_MARK, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    wants=(Q.FERMATA_MARK, Q.GLYPH_BOX),
    subjects_from=Q.FERMATA_MARK,
    reasons=("contains_the_mark", "nearest_in_bar", "no_carrier",
             "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_fermata_owner(ev: Evidence) -> Ruling:
    """What a fermata hangs over — a notehead or a rest, in its own bar.

    ⚠️ THE RULE IS `export.annotate_fermatas`'s AND IS NOT RE-DERIVED. A
    fermata belongs to whatever is SOUNDING under it, so the pairing is BY X
    ALONE and never by pitch: the mark's centre inside a carrier's x-span, or
    failing that the nearest carrier centre in the bar. That reading was paid
    for when the sixth export gap was closed -- Beethoven 5 detects 36
    fermatas against a truth of 36 -- and the `<fermata>` element it produces
    is already emitted by `_mxl_note`.

    ⚠️ THE FALLBACK IS LOAD-BEARING, NOT SLOPPY, and the legacy docstring says
    why: a fermata over a bar's only rest is engraved at the BAR's middle
    while the rest glyph sits at its own centre, so a containment-only rule
    misses the commonest case of all. The two branches are reported APART
    (`contains_the_mark` / `nearest_in_bar`) so a reader can tell a mark that
    stood over its carrier from one that merely stood nearest it -- the
    distinction a single reason would destroy.

    ⚠️ IT IS NOT AN ARTICULATION AND THE SIDE IS NOT A CONSTRAINT. The sibling
    decision above requires the notehead to be on the side the mark's own class
    names; that rule is wrong here, because a `fermataAbove` over a whole-bar
    rest stands above ink it belongs to. The side is recorded on
    `Q.FERMATA_MARK` and read by nothing -- `_mxl_note` writes
    `type="upright"` unconditionally -- rather than being pressed into service
    as a test it cannot pass.

    ⚠️ THE CELL'S CANONICAL FRAME IS CORRECT HERE, for the same reason it is
    correct for an articulation and WRONG for `arc_owner`: the mark and its
    carrier were cut from ONE cell, so they share a frame by construction.
    This decision never looks at another staff -- ⚠️ which is also its known
    limit. A fermata is printed above the staff and a measure cell is padded
    above, so a mark can land in the cell of the staff ABOVE the one that
    prints it, exactly as a hairpin does. Nothing arbitrates that here; it is
    recorded as a limit rather than guessed at.

    ⚠️ NO DISTANCE CONSTANT, deliberately. The legacy rule has none -- the bar
    bounds the search -- and inventing one would be tuning a family on its
    first day against one document, which is what the wiring pass exists to
    avoid. What the record gets instead is `dx_canonical_px` on every verdict,
    so a constant can be read off a measured population later.
    """
    marks = ev.rows(Q.FERMATA_MARK)
    if not marks:
        return Ruling.abstain("no_evidence")
    mark = marks[0]

    cell = ev.subject.at(Kind.CELL)
    carriers = [r for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                   subject=cell)
                if (r.detail or {}).get("category") in _FERMATA_CARRIERS
                and isinstance(r.value, (list, tuple)) and len(r.value) >= 5]
    if not carriers:
        # ⚠️ A REAL POPULATION, NOT A DEFENSIVE BRANCH: 9 of the 46 cells
        # holding a fermata on Litolff `984073` p1-3 carry neither a notehead
        # nor a rest. The mark was read and there is nothing in that bar for it
        # to hang on, which is a gap in the READING and is reported as one.
        return Ruling.abstain("no_carrier", detector_class=str(mark.value))

    mx = (float(mark.detail.get("x0", 0.0))
          + float(mark.detail.get("x1", 0.0))) / 2.0

    def _span(row):
        _cls, x, _y, w, _h = row.value[:5]
        return float(x), float(x) + float(w)

    # ⚠️ DETERMINISTIC ORDER. A chord's members share an x by definition, so
    # several carriers can contain the mark; the exporter HOISTS a fermata to
    # its event's first note either way, but a verdict that moved between runs
    # would make every A/B on this family unreadable.
    carriers.sort(key=lambda r: (_span(r)[0], r.subject.glyph or 0))

    hit = next((r for r in carriers
                if _span(r)[0] <= mx <= _span(r)[1]), None)
    if hit is not None:
        reason = "contains_the_mark"
    else:
        hit = min(carriers,
                  key=lambda r: (abs(sum(_span(r)) / 2.0 - mx),
                                 r.subject.glyph or 0))
        reason = "nearest_in_bar"

    lo, hi = _span(hit)
    return Ruling(
        value=hit.subject.to_key(), reason=reason,
        used=(mark.id, hit.id),
        # ⚠️ THE CARRIER'S KIND TRAVELS WITH THE OWNER, the same rule
        # `articulation_owner` follows for its mark's kind: an exporter holding
        # only a subject key would have to re-read the glyph to know whether it
        # is hanging the pause on a note or on a rest.
        detail={"carrier": (hit.detail or {}).get("category"),
                "carrier_class": str(hit.value[0]),
                "dx_canonical_px": abs((lo + hi) / 2.0 - mx),
                "n_carriers": len(carriers),
                "side": (mark.detail or {}).get("side"),
                "detector_class": str(mark.value),
                "confidence": mark.score})


@decision(
    quantity=Q.ORNAMENT_OWNER,
    composed_from=(Q.ORNAMENT_MARK, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    wants=(Q.ORNAMENT_MARK, Q.GLYPH_BOX),
    subjects_from=Q.ORNAMENT_MARK,
    reasons=("nearest_on_declared_side", "nearest_either_side", "no_notehead",
             "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_ornament_owner(ev: Evidence) -> Ruling:
    """Which notehead a trill, turn, mordent or tremolo is printed against.

    ⚠️ THE RULE IS `transcribe._attach_ornaments_in_cell`'S AND THE CONSTANT
    IS IMPORTED: the nearest notehead in x on the side the mark's class names,
    within `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS`. The unit is a NOTEHEAD WIDTH and
    not the mark's own box, which is the mistake the augmentation-dot gate paid
    193 edits for.

    ⚠️⚠️ THAT CONSTANT IS DECLARED UNMEASURED BY ITS OWN AUTHOR AND IS
    IMPORTED ANYWAY. Unlike the articulation limit it sits on no swept
    plateau, because there is no corpus to sweep it on -- across 7,090
    committed artifacts there is not ONE `tremolo1`-`5` detection and the 33
    trill/turn/mordent detections carry no per-mark truth. Importing it keeps
    ONE unmeasured number in the tree instead of two that can drift; it does
    not make it measured, and a sweep is still owed.

    ⚠️ A NOTEHEAD, NEVER A REST -- the one place this differs from
    `fermata_owner`, whose shape it otherwise shares. A trill is played ON a
    note. `_mxl_note` says the same from the other side: it refuses
    `<ornaments>` on a rest (`if not is_rest`) while emitting `<fermata>`
    regardless.

    ⚠️ A TREMOLO'S SIDE IS `None` AND THE GEOMETRY TEST IS THEN SKIPPED, not
    guessed -- it rides the STEM and sits on whichever side that is, which the
    legacy rule states explicitly (`above is None`). The two branches are
    reported apart (`nearest_on_declared_side` / `nearest_either_side`) so a
    reader can tell a placement that satisfied a side constraint from one that
    had none to satisfy.

    ⚠️ ZERO REACH ON BOTH DOCUMENTS IN HAND at the time of writing, and this
    quantity closes NO detection gap: `export_coverage.KNOWN_GAPS` records the
    eleven-work truth's only ornaments as twelve `<tremolo>` against a detector
    that produces ZERO tremolo detections. Measure REACH before accuracy.
    """
    marks = ev.rows(Q.ORNAMENT_MARK)
    if not marks:
        return Ruling.abstain("no_evidence")
    mark = marks[0]
    detail = mark.detail or {}
    kind = detail.get("kind")
    side = detail.get("side")

    cell = ev.subject.at(Kind.CELL)
    heads = [r for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                subject=cell)
             if (r.detail or {}).get("category") == "notehead"
             and isinstance(r.value, (list, tuple)) and len(r.value) >= 5]
    if not heads:
        return Ruling.abstain("no_notehead", ornament=kind)

    widths = sorted(float(h.value[3]) for h in heads)
    nh_width = widths[len(widths) // 2] or 1.0
    limit = nh_width * _legacy_articulation._ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS

    mx = (float(detail.get("x0", 0.0)) + float(detail.get("x1", 0.0))) / 2.0
    my = (float(detail.get("y0", 0.0)) + float(detail.get("y1", 0.0))) / 2.0

    best: Optional[Tuple[float, object]] = None
    for h in heads:
        _cls, hx, hy, hw, hh = h.value[:5]
        hyc = float(hy) + float(hh) / 2.0
        # ⚠️ LARGER CANONICAL y IS LOWER ON THE PAGE, so a mark printed ABOVE
        # its notehead has the SMALLER y. Stated because the sign is the whole
        # of the side test and reads backwards.
        if side == "above" and my >= hyc:
            continue
        if side == "below" and my <= hyc:
            continue
        dx = abs(mx - (float(hx) + float(hw) / 2.0))
        if dx > limit:
            continue
        if best is None or dx < best[0]:
            best = (dx, h)
    if best is None:
        return Ruling.abstain("no_notehead", ornament=kind, side=side,
                              notehead_width=nh_width,
                              limit_canonical_px=limit)

    dx, head = best
    return Ruling(
        value=head.subject.to_key(),
        reason=("nearest_on_declared_side" if side
                else "nearest_either_side"),
        used=(mark.id, head.id),
        # ⚠️ THE KIND AND THE STROKE COUNT TRAVEL WITH THE OWNER, so an
        # exporter holding only the subject key need not re-read the mark's
        # class to know whether to write `<trill-mark/>` or a `<tremolo>` of
        # three strokes -- the re-derivation this stage exists to remove.
        detail={"ornament": kind, "strokes": detail.get("strokes"),
                "side": side, "dx_canonical_px": dx,
                "dx_notehead_widths": (dx / nh_width) if nh_width else None,
                "detector_class": str(mark.value),
                "confidence": mark.score})
