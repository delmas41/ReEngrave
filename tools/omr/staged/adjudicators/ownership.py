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
from ..record import ABSTAIN, Kind, Q, Scope, State

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


@decision(
    quantity=Q.ARC_KIND,
    checkable=Checkable.MIXED,
    checked_by=(
        "a TIE joins two heads of the SAME staff step; an arc whose flanked heads sit on different steps is a SLUR",
    ),
    implicates=(Q.ARC_KIND, Q.NOTEHEAD_STAFF_POSITION, Q.CLEF),
    composed_from=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    # ⚠️ `Q.GLYPH_BOX` is declared because a notehead's STEP row carries no x:
    # the step is joined to a position through the box on the SAME glyph. The
    # harness refused the read until it was declared (`UndeclaredEvidence`),
    # which is `Evidence` doing its job -- a decision may only read what it
    # says it reads, so `missing` and `declined` can mean something.
    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX),
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
    pad = max(float(arc.detail.get("y1", 0)) - float(arc.detail.get("y0", 0)),
              1.0)
    x0 = float(arc.detail.get("x0", 0)) - pad
    x1 = float(arc.detail.get("x1", 0)) + pad

    cell = ev.subject.at(Kind.CELL)
    boxes = {r.subject.to_key(): r for r in
             ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell)}
    flanked = []
    for row in ev.rows(Q.NOTEHEAD_STAFF_POSITION,
                       scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        box = boxes.get(row.subject.to_key())
        if box is None:
            continue
        value = box.value
        if not isinstance(value, (list, tuple)) or len(value) < 5:
            continue
        xc = float(value[1]) + float(value[3]) / 2.0
        if x0 <= xc <= x1:
            flanked.append((xc, row.detail.get("rounded"), row.id))
    flanked.sort()

    grammar = {"flanked_heads": len(flanked), "reading": kind}
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


@decision(
    quantity=Q.WEDGE_ANCHOR,
    composed_from=(Q.WEDGE_BOX, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    wants=(Q.WEDGE_BOX, Q.GLYPH_BOX),
    subjects_from=Q.WEDGE_BOX,
    reasons=("nearest_either_side", "no_anchor", "no_evidence"),
    mode=Mode.ADDITIVE,
    stub=True,
)
def adjudicate_wedge_anchor(ev: Evidence) -> Ruling:
    """⚠️ DECLARED STUB. A slur is drawn OVER its notes; a hairpin BETWEEN
    them, so an overlap test scores 0 of 4 and the edges must be read as
    POINTERS. Nearest-either-side pairs 4 of 8 truth hairpins and gets all 4
    right; "the last note at or before the edge" pairs 1, because the ink
    begins slightly BEFORE the note it starts on.
    """
    return Ruling.abstain(ABSTAIN.NOT_IMPLEMENTED)
