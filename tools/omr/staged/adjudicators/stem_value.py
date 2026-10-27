"""One stem, one value -- ROADMAP 2.78 (Sean, DECISIONS 2026-10-09, "no exceptions").

Every notehead on ONE stem has the SAME written value. Sean's ruling, on the 14
blind tiles of `out/print/2.78-review/` (FINDINGS `omr-head-fill-2026-09` Sec.11):
the value belongs to the STEM; it is read from the stem's OWN evidence -- the
beams and flags at its tip, the hollow heads, the dots -- and a head that
disagrees TAKES the stem's value. A head is never refused for its fill alone
(`notehead_precision` refuses a box that is a slash or a duplicate, each with
its own per-box witness); what this module does is give every head that stands
on a shared stem the stem's value, or narrow/abstain where the stem's own
evidence cannot say.

TWO DECISIONS, IN THIS ORDER, BOTH AFTER `Q.DURATION`:

  `Q.HEAD_STEM`   (per head)  which stem a notehead box stands on, filed ONCE.
                  Until now nothing on the record said "these heads share a
                  stem": ADJUDICATE re-derived a bare box overlap with `Q.STEM`
                  privately in `rhythm._stems_on`, `notehead_precision.
                  _stem_rows_on` and `gather._stacked_boxes_overlap`, `Q.EVENT`
                  is an x-cluster and EXPORT mode-votes a chord's duration.
                  DECIDED where the head's box touches exactly one stem (rows
                  that are the same physical stem collapse into one), DECIDED by
                  the engraving's own side rule where two stems touch it and
                  only one is FLUSH with a side of the head (a stem stands at the
                  SIDE of its head, CLAUDE.md §10), NARROWED where two are
                  equally plausible, ABSTAINED where none touches.

  `Q.STEM_VALUE`  (per head)  the written value of the stem this head stands on,
                  as it applies to THIS head. Read from the heads' own duration
                  verdicts by component, never a vote:

    BASE   a HOLLOW head decided on the stem makes the stem a half note
           (Sean: "a stem carrying a hollow head cannot also carry a filled
           one"); no hollow head -> the filled heads' base; nothing decided ->
           the narrowed heads' common base. A hollow head under a beam that
           reads CERTAIN at the stem's TIP is the tie nothing breaks: NARROWED
           between the two readings (a genuine hollow head plus a beam), never
           picked (rule 8).
    LEVELS the beams and flags belong to the stem's TIP, so they are read from
           the member nearest the tip (the stem's direction names which end);
           a head far from the tip also sees strokes BETWEEN the heads, which
           are not beams (tile 1: one head 16th, the other 8th, Sean: 8th). An
           open head is never beamed (2.43), so a hollow stem is level 0.
    DOTS   the stem's: a dot read for a head of a stem is the chord's (tile 13:
           one head lacked its dot, Sean: "2 dotted half notes"). On a HOLLOW
           stem only the hollow (and whole-class) heads' dots count: a filled box
           on a hollow stem is the slash or a duplicate in every one of Sean's
           non-note cases, and a dot near it belongs to something else.

    RULE, CONFIRMED (Sean, DECISIONS 2026-10-09, on tiles 5 and 9): **"Whole
    notes never have stems."** A box standing on a stem is never a whole note.
    A whole-class box on a shared stem therefore casts no vote for the stem's
    base or levels and takes the stem's value, and a whole VALUE (base >= 4) is
    not among the values a stem can have: it is dropped from a narrowing. There
    is no switch for it. (It was an assumption until Sean confirmed it; a test
    holds the control that can fail -- with `_stands_on_a_stem_so_not_whole`
    removed, tile 9's stem is decided a half.)

WHAT IT DOES NOT DO. It never refuses a box (a refusal needs a per-box witness
and is `notehead_precision`'s), never overturns the head's own `Q.DURATION`
verdict (it files its own beside it), and never writes where the stem has one
head (`lone_head`). A stem none of whose members is read is `stem_unread`.

WHO READS IT. EVALUATE's `consequences.share_stem_value` (cause `Q.STEM_VALUE`,
effect `Q.DURATION`, single pass, ranked before `Q.METER` in `evaluate.DOWNHILL`
so it runs before every meter rule) restates a head's standing duration to
its stem's value where the stem's value is DECIDED and the head's differs, or
settles a head's narrowed duration to it. A NARROWED stem value fires nothing.
The restatement is there, not here, because a decision never overturns another
decision's verdict in its own quantity -- EVALUATE is the stage for what
follows necessarily.

⚠️ NOT BUILT, AND STILL OPEN: where the stem value is NARROWED (levels unread,
two dot counts, a hollow head under a certain beam) this rule fires nothing, so
the heads keep their own, possibly disagreeing, durations and
`export._events` (-> `voicing.group_chords_in_measure`) still takes a chord's
duration as the MODE of its heads' durations -- an argmax over a disagreement.
The right behaviour there is to HOLD THE STEM OUT AND COUNT IT, never to write
a mode; it is an EXPORT change and belongs to a roadmap item of its own. For a
DECIDED stem value the heads agree by the time EXPORT runs and the vote has
nothing to decide.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from ..adjudicate import Evidence, Mode, Ruling, decision, is_relocated_copy
from ..record import Candidate, Kind, Outcome, Q, Scope, STROKE_GLYPH_BASE, Subject

# ─────────────────────────────────────────────────────────────────────────────
# Constants -- each one a convention or a measurement, never a tuning knob
# ─────────────────────────────────────────────────────────────────────────────

#: Two `Q.STEM` rows are ONE physical stem when each overlaps the other by at
#: least this share of the NARROWER extent on both axes. ⚠️ MEASURED, not
#: assumed: on Litolff p1-3 and Brahms p0-1, 12 and 5 multi-head stems were the
#: same head-set reached through two duplicate rows
#: (`benchmarks/omr-head-fill-2026-09/FINDINGS.md` Sec.11.1).
STEM_DUPLICATE_MIN_OVERLAP = 0.5

#: A stem belongs to a head only if it REACHES OUT of the head's own height: a
#: stem is at least ~2.5 staff spaces, a head ~1.3, so a vertical stroke that
#: stays inside the head's box (a slash's root, the edge of a neighbour's ring,
#: a stem fragment) is not its stem. The number is `gather.
#: HEAD_STEM_MIN_EXT_SPACES` (0.8), MEASURED there (*"a head is ~1.0-1.5 sp tall
#: and a stem is at least ~2.5 sp, so 0.8 sp clears the head's own outline"*),
#: restated here only because ADJUDICATE may not import a GATHER constant's
#: module-level name into a decision's behaviour without saying so. Used ONLY to
#: break a tie between two stems that both touch a box (Litolff p2 `glyph/2/1/9/
#: 11/3`, tile 7: a long stem at its right and a 0.37 sp fragment at its left).
STEM_MIN_REACH_SPACES = 0.8

#: A stem is FLUSH with a head when its centre line stands within this share of
#: the head's width of one of the head's sides (CLAUDE.md §10: "a stem stands
#: at the SIDE of its head"). Used ONLY to break a tie between two stems that
#: both touch a head; a stem through the MIDDLE of a box (a slash box, a
#: through-stem) is still that box's stem when it is the only one.
STEM_FLUSH_MAX = 0.3

#: The head base (beats, before any beam, flag or dot) at or above which a head
#: is HOLLOW: a half note is 2.0, a whole 4.0, a black head 1.0.
HOLLOW_BASE_MIN = 2.0

#: The head base of a WHOLE note. RULE, CONFIRMED (Sean, DECISIONS 2026-10-09,
#: tiles 5 and 9: *"Whole notes never have stems"*): no stem carries a head of
#: this base or more, so a whole VALUE is never a stem's value.
WHOLE_BASE = 4.0


def _stands_on_a_stem_so_not_whole(cls: str) -> bool:
    """A detector class that names a WHOLE note (or a double whole) on a box that
    stands on a stem: by Sean's rule (*"Whole notes never have stems"*) it is not
    one, so it casts no vote for the stem's base or levels. Spelled as a function
    so the rule has ONE place -- and a control that can fail (a test replaces it)."""
    return cls.lower().startswith(("noteheadwhole", "noteheaddoublewhole"))


# ─────────────────────────────────────────────────────────────────────────────
# Geometry -- the same overlap test every other reader of a head and a stem uses
# ─────────────────────────────────────────────────────────────────────────────


def _xywh(value: Any) -> Optional[Tuple[float, float, float, float]]:
    """`Q.STEM`'s value, `[x, y, w, h]` (canonical cell pixels)."""
    if not isinstance(value, (list, tuple)) or len(value) < 4:
        return None
    return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))


def _head_xywh(value: Any) -> Optional[Tuple[float, float, float, float]]:
    """`Q.GLYPH_BOX`'s value, `(smufl_name, x, y, w, h)`."""
    if not isinstance(value, (list, tuple)) or len(value) < 5:
        return None
    return (float(value[1]), float(value[2]), float(value[3]), float(value[4]))


def _overlap(a: Tuple[float, ...], b: Tuple[float, ...]) -> bool:
    """`rhythm._boxes_overlap`: share any area, no tolerance (measured there:
    heads take exactly one stem and where none overlaps the nearest is 94 px
    away)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw and ax + aw >= bx
            and ay <= by + bh and ay + ah >= by)


def _span_share(a0: float, a1: float, b0: float, b1: float) -> float:
    """How much of the NARROWER of two intervals the other covers."""
    inter = min(a1, b1) - max(a0, b0)
    narrower = min(a1 - a0, b1 - b0)
    if narrower <= 0:
        return 1.0 if inter >= 0 else 0.0
    return max(0.0, inter) / narrower


def _same_stem_row(a: Tuple[float, ...], b: Tuple[float, ...]) -> bool:
    """Two CV stem rows that are one physical stem."""
    return (_span_share(a[0], a[0] + a[2], b[0], b[0] + b[2])
            >= STEM_DUPLICATE_MIN_OVERLAP
            and _span_share(a[1], a[1] + a[3], b[1], b[1] + b[3])
            >= STEM_DUPLICATE_MIN_OVERLAP)


def _x_frac(stem: Tuple[float, ...], head: Tuple[float, ...]) -> Optional[float]:
    """Where the stem's centre line stands across the head's width: 0 is the
    head's left edge, 1 its right. A real stem is flush (~0 or ~1)."""
    if head[2] <= 0:
        return None
    return ((stem[0] + stem[2] / 2.0) - head[0]) / head[2]


def _flush_distance(frac: Optional[float]) -> float:
    return 9.0 if frac is None else min(abs(frac), abs(1.0 - frac))


def _flush_word(frac: Optional[float]) -> str:
    if frac is None:
        return "unknown"
    if frac < STEM_FLUSH_MAX:
        return "left"
    if frac > 1.0 - STEM_FLUSH_MAX:
        return "right"
    return "through"


# ─────────────────────────────────────────────────────────────────────────────
# Q.STEM_HEAD_CONTACT -- does each stroke the finder calls a stem touch a head?
# ─────────────────────────────────────────────────────────────────────────────


def _cell_heads(ev: Evidence, cell: Subject) -> List[Tuple[Subject, Tuple[float, ...]]]:
    """Every notehead-classed detector box of this cell, `(glyph subject, xywh)`."""
    heads = []
    for row in ev.rows(Q.NOTEHEAD_CLASS, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=cell):
        boxes = ev.rows(Q.GLYPH_BOX, subject=row.subject)
        box = _head_xywh(boxes[-1].value) if boxes else None
        if box is not None:
            heads.append((row.subject, box))
    return heads


@decision(
    quantity=Q.STEM_HEAD_CONTACT,
    scope=Kind.CELL,
    # ⚠️ GATHER ROWS ONLY: the detector's own notehead boxes (kept or not -- whether
    # a box is a head is another decision's question, and counting a refused box
    # can only KEEP a stroke) and the cell's strokes. So it can stand anywhere in
    # ORDER; it stands ahead of every consumer.
    wants=(Q.STEM, Q.NOTEHEAD_CLASS, Q.GLYPH_BOX, Q.CELL_BOX),
    subjects_from=Q.STEM,
    reasons=("all_touch_a_head", "some_touch_no_head", "no_heads_read",
             "no_stem"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.STEM, Q.NOTEHEAD_CLASS, Q.GLYPH_BOX, Q.CELL_BOX),
)
def adjudicate_stem_head_contact(ev: Evidence) -> Ruling:
    """ROADMAP 2.87, `OMR_STEM_FINDER=head_contact`.

    CONVENTION (Sean 2026-10-11): *"All stems should be connected to a notehead"*,
    to be used *"to verify later in the stages"*. Per `Q.STEM` row of this cell:
    does it touch a detected notehead box (within `geometry.
    STEM_CONTACT_TOLERANCE_HEADS` of the head's own height)? The value is the
    list of ids that touch none. ABSTAINED where the cell has strokes and no
    notehead box at all -- heads unread says nothing about the stroke (rule 8).

    A unison head (two voices on one head: an up stem at its right, a down stem
    at its left) keeps both stems by construction: both touch the one head.
    WHAT WOULD FALSIFY IT: a real stem whose head the detector never boxed.
    """
    cell = ev.subject
    stems = []
    for row in ev.rows(Q.STEM, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        b = _xywh(row.value)
        if b is not None:
            stems.append((row, b))
    if not stems:
        return Ruling.abstain("no_stem")
    heads = _cell_heads(ev, cell)
    if not heads:
        return Ruling.abstain("no_heads_read",
                              stems=sorted(r.id for r, _b in stems))
    from ..geometry import STEM_CONTACT_TOLERANCE_HEADS as TOL

    def touches(sb, hb) -> bool:
        t = TOL * hb[3]
        return (sb[0] <= hb[0] + hb[2] + t and sb[0] + sb[2] >= hb[0] - t
                and sb[1] <= hb[1] + hb[3] + t and sb[1] + sb[3] >= hb[1] - t)

    # ⚠️ A STEM CUT BY THE CELL'S CROP HAS ITS HEAD OUTSIDE IT. The cell is padded
    # into the neighbouring staff, so a beamed group of the staff below arrives as
    # stems running off the crop's edge whose heads are in the OTHER cell (Brahms
    # 317803 p1 cell/1/0/10/0: 4 such stems; refusing them dropped a real beam's
    # eighth to a quarter). Where a stroke reaches the crop edge, contact is
    # unknowable HERE, so it is neither met nor refused (rule 8). The edge is read
    # off `Q.CELL_BOX` through the cell's own dual-frame box; no frame, no edge, and
    # then NO stroke is refused for want of a head (it cannot be told from a cut one).
    bounds = _crop_bounds(ev, cell)
    cut: List[str] = []

    def at_edge(sb) -> bool:
        if bounds is None:
            return True
        e = bounds[2]
        return sb[1] <= bounds[0] + e or sb[1] + sb[3] >= bounds[1] - e

    meets, none = [], []
    for r, sb in stems:
        if any(touches(sb, hb) for _s, hb in heads):
            meets.append(r.id)
        elif at_edge(sb):
            cut.append(r.id)
        else:
            none.append(r.id)
    none.sort()
    detail = {"meets": sorted(meets), "meets_none": none,
              "cut_by_the_crop": sorted(cut), "heads": len(heads),
              "crop_bounds_known": bounds is not None}
    if none:
        return Ruling(value=none, reason="some_touch_no_head", detail=detail)
    return Ruling(value=none, reason="all_touch_a_head", detail=detail)


def _crop_bounds(ev: Evidence, cell: Subject) -> Optional[Tuple[float, float, float]]:
    """`(top, bottom, edge_margin)` of this cell's crop in canonical y, or None.
    `Q.CELL_BOX` (page) carried through the cell's frame (`rhythm._cell_frame`)."""
    from .rhythm import _cell_frame
    cb = ev.rows(Q.CELL_BOX, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
    frame = _cell_frame(ev, cell)
    if not cb or frame is None:
        return None
    try:
        y0, y1 = float(cb[-1].value[1]), float(cb[-1].value[3])
    except (TypeError, ValueError, IndexError):
        return None
    _ox, oy, up = frame
    return ((y0 - oy) * up, (y1 - oy) * up, CROP_EDGE_PX)


#: A stroke end within this many canonical px of the crop's top or bottom edge is cut
#: by it. MEASURED: on Brahms 317803 p0-1 the cut stems' ends stand within 1 px of the
#: edge (cell/1/0/10/0: bottoms 654, 654, 654, 654 against 654.3).
CROP_EDGE_PX = 3.0


def stems_connected_to_a_head(verdict: Any, stems: Sequence[Any]):
    """`stems` (`Q.STEM` rows) without the ones a DECIDED `Q.STEM_HEAD_CONTACT`
    `verdict` (the cell's, read by the CONSUMER where it is declared, so `wiring` and
    `inventory` see the read) says touch no notehead. The same sequence, unchanged,
    unless `OMR_STEM_FINDER` names `head_contact` and the verdict is DECIDED and names
    one: an absent or abstained verdict (heads unread) refuses nothing (rule 8)."""
    from ..geometry import stem_finder_repair_on
    if (verdict is None or verdict.outcome is not Outcome.DECIDED
            or not verdict.value or not stem_finder_repair_on("head_contact")):
        return stems
    none = frozenset(verdict.value)
    return tuple(s for s in stems if s.id not in none)


# ─────────────────────────────────────────────────────────────────────────────
# Q.HEAD_STEM -- the join, filed once
# ─────────────────────────────────────────────────────────────────────────────


@decision(
    quantity=Q.HEAD_STEM,
    scope=Kind.GLYPH,
    # ⚠️ GATHER ROWS ONLY. A notehead's box and the cell's stems are the whole
    # evidence; no other decision's verdict is read, so this can stand
    # anywhere in ORDER -- it stands beside its one consumer.
    wants=(Q.GLYPH_BOX, Q.STEM, Q.CELL_STAFF_SPACE, Q.STEM_DIRECTION,
           Q.NOTEHEAD_CLASS, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
    subjects_from=Q.NOTEHEAD_CLASS,
    reasons=("one_stem", "stem_by_reach", "stem_by_side", "stem_by_flush",
             "stem_by_one_per_head", "unison_two_voices",
             "two_stems", "no_stem", "no_evidence"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.GLYPH_BOX, Q.STEM, Q.CELL_STAFF_SPACE, Q.STEM_DIRECTION,
                   Q.NOTEHEAD_CLASS, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD),
)
def adjudicate_head_stem(ev: Evidence) -> Ruling:
    """Which stem does this notehead box stand on?

    ⚠️ THE JOIN IS DECIDED FOR EVERY HEAD, KEPT OR REFUSED. Whether the box is
    a head at all is another decision's question (`Q.NOTEHEAD_IS_NOT_A_NOTEHEAD`);
    which stem it touches is geometry, and a consumer that wants only kept heads
    filters by that verdict, as `adjudicate_stem_value` does.

    The value is the canonical `Q.STEM` row id of the stem (the tallest row of
    a set of rows that are the same physical stem, the lowest id on a tie), so
    two heads of one chord carry the SAME string. `detail` holds the stem's
    box, every row id of that stem, and where its centre line stands across the
    head.
    """
    boxes = ev.rows(Q.GLYPH_BOX)
    head = _head_xywh(boxes[-1].value) if boxes else None
    if head is None:
        return Ruling.abstain("no_evidence")
    cell = ev.subject.at(Kind.CELL)
    stems = []
    for row in ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell):
        b = _xywh(row.value)
        if b is not None:
            stems.append((row, b))
    from ..geometry import stem_touches_head
    touching = [(r, b) for r, b in stems if stem_touches_head(b, head)]
    if not touching:
        return Ruling.abstain("no_stem", used=(boxes[-1].id,))

    # one entry per PHYSICAL stem: rows that are the same stem collapse onto
    # their tallest member (ties: lowest id), so every head of a chord names the
    # same row
    physical: Dict[str, Dict[str, Any]] = {}
    for row, b in touching:
        cluster = [(r2, b2) for r2, b2 in stems
                   if r2 is row or _same_stem_row(b, b2)]
        rep_row, rep_box = min(cluster, key=lambda t: (-t[1][3], t[0].id))
        slot = physical.setdefault(rep_row.id, {
            "box": rep_box, "rows": set(), "rep": rep_row})
        slot["rows"].update(r2.id for r2, _b in cluster)

    def detail_of(rep_id: str) -> Dict[str, Any]:
        s = physical[rep_id]
        frac = _x_frac(s["box"], head)
        return {"stem": rep_id, "stem_rows": sorted(s["rows"]),
                "stem_box": [round(v, 2) for v in s["box"]],
                "x_frac": None if frac is None else round(frac, 3),
                "flush": _flush_word(frac)}

    used = (boxes[-1].id,) + tuple(sorted(
        i for s in physical.values() for i in s["rows"]))
    if len(physical) == 1:
        rep_id = next(iter(physical))
        return Ruling(value=rep_id, reason="one_stem", used=used,
                      detail=detail_of(rep_id))

    # two or more distinct stems touch this box. First, physics: a head's stem
    # REACHES OUT of the head's own height. Without a staff-space unit this test
    # is skipped (rule 6), never defaulted.
    space_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                         subject=cell)
    space = None
    if space_rows:
        try:
            space = float(space_rows[-1].value)
        except (TypeError, ValueError):
            space = None
        if space is not None and space > 0:
            used = used + (space_rows[-1].id,)
        else:
            space = None
    candidates_ = list(physical)
    if space is not None:
        def reach(i: str) -> float:
            sx, sy, sw, sh = physical[i]["box"]
            hx, hy, hw, hh = head
            return max(0.0, hy - sy, (sy + sh) - (hy + hh))
        long_enough = [i for i in physical
                       if reach(i) >= STEM_MIN_REACH_SPACES * space]
        if len(long_enough) == 1:
            d = detail_of(long_enough[0])
            d["rivals"] = [i for i in physical if i != long_enough[0]]
            return Ruling(value=long_enough[0], reason="stem_by_reach",
                          used=used, detail=d)
        if long_enough:
            candidates_ = long_enough
    # then the engraving's side rule (CLAUDE.md §10, *"up -> right, down -> left;
    # right-and-down does not exist (96 of 96 against print)"*): a stem pointing
    # UP stands at the RIGHT of its head, one pointing DOWN at its LEFT. The
    # direction is this head's own `Q.STEM_DIRECTION`, read where it is DECIDED;
    # a direction nobody read names no side (rule 6, never defaulted).
    dirv = ev.verdict(Q.STEM_DIRECTION)
    if (dirv is not None and dirv.outcome is Outcome.DECIDED
            and dirv.value in ("up", "down")):
        side = "right" if dirv.value == "up" else "left"
        on_side = [i for i in candidates_ if _flush_word(
            _x_frac(physical[i]["box"], head)) == side]
        if len(on_side) == 1:
            d = detail_of(on_side[0])
            d["rivals"] = [i for i in candidates_ if i != on_side[0]]
            d["direction"] = dirv.value
            return Ruling(value=on_side[0], reason="stem_by_side",
                          used=used + (dirv.id,), detail=d)
    # last, the bare flush test: where exactly one of those that remain is
    # flush with a side of the head, it is this head's.
    ranked = sorted(candidates_, key=lambda i: _flush_distance(
        _x_frac(physical[i]["box"], head)))
    flush = [i for i in ranked if _flush_distance(
        _x_frac(physical[i]["box"], head)) <= STEM_FLUSH_MAX]
    if len(flush) == 1:
        d = detail_of(flush[0])
        d["rivals"] = [i for i in ranked if i != flush[0]]
        return Ruling(value=flush[0], reason="stem_by_flush", used=used,
                      detail=d)
    cands = tuple(Candidate(value=i, support=float(len(ranked) - n))
                  for n, i in enumerate(ranked))
    from ..geometry import stem_finder_repair_on
    if stem_finder_repair_on("one_stem_per_head"):
        forced = _one_stem_per_head(ev, cell, head, stems, physical, ranked,
                                    space)
        if forced is not None:
            kind, rep_id, extra = forced
            if kind == "collapse":
                d = detail_of(rep_id)
                d["rivals"] = [i for i in ranked if i != rep_id]
                d.update(extra)
                return Ruling(value=rep_id, reason="stem_by_one_per_head",
                              used=used, detail=d)
            return Ruling.narrow(cands, "unison_two_voices", used=used,
                                 stems={i: detail_of(i) for i in ranked},
                                 **extra)
    return Ruling.narrow(cands, "two_stems", used=used,
                         stems={i: detail_of(i) for i in ranked})


#: ROADMAP 2.175: how many times further than its touch past the head a unison stem must run away from it.
UNISON_TOUCH_RATIO = 2.0


def unison_two_notes_enabled() -> bool:
    """`OMR_UNISON_TWO_NOTES`, default ON (ROADMAP 2.175)."""
    from .unison_two import enabled
    return enabled()


#: Another head stands at a DIFFERENT staff position (so it is a second note, not the
#: same note boxed twice) when its centre is at least this many of the head's own
#: heights from this head's centre. A third apart is ~1.0; a stacked duplicate box
#: sits within a fraction of a pixel to a few.
ONE_STEM_PER_HEAD_MIN_APART_HEADS = 0.5


def _rep_ids_touching(stems, head, physical_of) -> Set[str]:
    """The canonical (representative) ids of the physical stems `head` touches."""
    from ..geometry import stem_touches_head
    out: Set[str] = set()
    for row, b in stems:
        if stem_touches_head(b, head):
            out.add(physical_of(row, b))
    return out


def _one_stem_per_head(ev: Evidence, cell: Subject, head, stems, physical,
                       ranked, space):
    """ROADMAP 2.87, `OMR_STEM_FINDER=one_stem_per_head`. For a head narrowed
    between stems: `("collapse", stem id, detail)`, `("unison", None, detail)` or
    `None` (today's plain narrowing).

    CONVENTION (Sean 2026-10-11): every stem touches a notehead; every black
    notehead has exactly ONE stem, unless two voices share it -- a UNISON, which
    goes in DIFFERENT directions (*"They would go in different directions"*): an up
    stem at the head's right and a down stem at its left, on one head with no other
    head under the stems. WHAT WOULD FALSIFY IT: a black head that truly carries two
    same-direction stems; a second head box that is a duplicate of this one (it must
    stand at a different staff position to claim a stem). NOT CONFIRMED beyond tile 10
    (Brahms 317803 pdf 0, `q1322` over `q1319`).

    COLLAPSE (it FOLLOWS, so it only ever picks one of this head's OWN candidates and
    never overturns a decided one): a candidate stem is CLAIMED when another kept
    head, at a different staff position, touches it and touches no other stem -- that
    head needs it. If exactly one candidate is unclaimed, this head needs it
    (every stem touches a head) and may not take a claimed one (one stem per head).
    UNISON: ONE head -- no other kept head at a different position touches either
    stem -- with exactly two candidates, one pointing up at the right and one down at
    the left -> `unison_two_voices`, both kept, NEVER collapsed. Two stems the same way
    are not a unison: `None`. Two heads a third apart that BOTH touch both strokes (the
    strokes merge into both) are not a unison either and not forced: `None`.
    """
    from ..geometry import stem_touches_head

    def rep_of(row, b):
        cluster = [(r2, b2) for r2, b2 in stems
                   if r2 is row or _same_stem_row(b, b2)]
        return min(cluster, key=lambda t: (-t[1][3], t[0].id))[0].id

    hcy = head[1] + head[3] / 2.0
    claimed: Dict[str, List[str]] = {}
    shared_with_another_head = False
    for row in ev.rows(Q.NOTEHEAD_CLASS, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=cell):
        k = row.subject
        if k == ev.subject:
            continue
        refusal = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=k)
        if (refusal is not None and refusal.outcome is Outcome.DECIDED
                and refusal.value is True):
            continue
        boxes = ev.rows(Q.GLYPH_BOX, subject=k)
        kb = _head_xywh(boxes[-1].value) if boxes else None
        if kb is None:
            continue
        if abs((kb[1] + kb[3] / 2.0) - hcy) < ONE_STEM_PER_HEAD_MIN_APART_HEADS * head[3]:
            continue
        theirs = _rep_ids_touching(stems, kb, rep_of)
        if theirs & set(ranked):
            shared_with_another_head = True
        if len(theirs) == 1:
            (only,) = tuple(theirs)
            if only in ranked:
                claimed.setdefault(only, []).append(k.to_key())
    unclaimed = [i for i in ranked if i not in claimed]
    if claimed and len(unclaimed) == 1:
        return ("collapse", unclaimed[0],
                {"claimed_by": {i: claimed[i] for i in claimed}})
    if (not claimed and not shared_with_another_head and len(ranked) == 2
            and space is not None):
        hx, hy, hw, hh = head
        need = STEM_MIN_REACH_SPACES * space
        kinds = {}
        for i in ranked:
            sx, sy, sw, sh = physical[i]["box"]
            above, below = max(0.0, hy - sy), max(0.0, (sy + sh) - (hy + hh))
            side = _flush_word(_x_frac(physical[i]["box"], head))
            if above >= need and below < need and side == "right":
                kinds[i] = "up"
            elif below >= need and above < need and side == "left":
                kinds[i] = "down"
            elif unison_two_notes_enabled():
                # ROADMAP 2.175 (flag `OMR_UNISON_TWO_NOTES`, ON): two strokes that touch at the head merge, so the up
                # stem's row also runs below the head (and the down stem's above it; Litolff p13 tile 3: 1.0 space).
                # The stem's DIRECTION is the side it stands on (up -> right, down -> left, CLAUDE.md §5) and it must
                # run mostly away from the head that way: more than twice as far as the touch below it. A barline
                # (as long each way) or a stem through a chord fails this.
                if side == "right" and above >= need and above >= UNISON_TOUCH_RATIO * below:
                    kinds[i] = "up"
                elif side == "left" and below >= need and below >= UNISON_TOUCH_RATIO * above:
                    kinds[i] = "down"
        if sorted(kinds.values()) == ["down", "up"]:
            return ("unison", None, {"voices": kinds})
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Q.STEM_VALUE -- the stem's value, per head
# ─────────────────────────────────────────────────────────────────────────────


BEAM_END_ENV = "OMR_STEM_BEAM_END"

#: A stem runs about 3.5 staff spaces past its OUTERMOST head (the engraving standard; CONVENTION ASSUMED, not yet confirmed by Sean -- a
#: lane report cannot confirm it: tiles can). MEASURED on the 2.202strokes records, every stem with >= 2 heads whose direction is decided
#: (Brahms pp.0,4,5,8,12,14,19,25; 1,230 stems): the distance from the tip to the member nearest it is 2.5-4.0 sp for 1,123 of them and under
#: 2.0 sp for 57. A box within `BEAM_END_TIP_MAX_SP` of the tip with another head `BEAM_END_OTHER_MIN_SP` or more from it contradicts that:
#: the tip is a beam's place. The pair of numbers sits in the valley (1.0 and 2.5), so it only NARROWS WHO MAY VOTE and names its margin.
BEAM_END_TIP_MAX_SP = 1.0
BEAM_END_OTHER_MIN_SP = 2.5


def beam_end_enabled() -> bool:
    """ROADMAP 2.209, flag `OMR_STEM_BEAM_END`, default OFF: a detector "notehead" that stands on a BEAM's ink and on no ink of its own is
    not a member of the stem (`_on_beam_ink`)."""
    import os
    return os.environ.get(BEAM_END_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _owner_mask(verdict: Any) -> Dict[int, str]:
    """`{ordinal: "owned" | "contested"}` from a cell's `Q.STROKE_OWNER` verdict (`stroke_owner.masked`: {} with the flag off or no verdict)."""
    from . import stroke_owner as _SOA
    return _SOA.masked(verdict)


def _on_beam_ink(ev: Evidence, sub: Subject) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.209 (Brahms p0 `glyph/0/0/12/1/15`, 2.206b tile 5). STAGED ADJUDICATE. Is this "notehead" the END OF A BEAM?

    CAUSE. A beam's thick end at a stem's foot is a dark block about a head's size, and the detector sometimes boxes it as a notehead (score
    0.25-0.30 on both Brahms cases). `Q.HEAD_STEM` joins any notehead-classed box that touches a stem, so the box became a MEMBER of the
    stem; the levels of a stem are read from the member nearest its tip (the beams hang there), and that member is the box ON the beam, whose
    own `Q.DURATION` counts the one beam level it sits in. It outvotes the real head's two decided levels, `share_stem_value` rewrites the
    real head (a decided sixteenth becomes an eighth), the bar then fills, and the blue flag goes: a wrong value written plain.

    ONE WITNESS, THE INK (this function). A notehead stands on a blob of ink of its own (2.205: tier 1 claims the blob strokes). A box that
    covers NO blob and stands on a stroke the 2.202 reader reads as a BEAM (horizontal, thick as a beam, joins >= 2 stems; not owned by
    another mark) is ON BEAM INK. ⚠️ That alone is NOT enough: on a MERGING plate (Litolff) and on Brahms beamed groups a real head fuses
    with its beam and covers no blob either (measured: with the ink alone 101 Litolff and 12 Brahms heads of 0.4-0.9 score were excluded,
    among them whole chords). The SECOND WITNESS, from another source, is the stem's own geometry (`_beam_end_boxes`): the box is at the TIP,
    where a stem has no head.

    Returns `{"beam_strokes": [...], "covered": [...]}` for a box on beam ink, else None. None where the map cannot speak (no `Q.GLYPH_STROKES` row, no
    strokes in the cell): a box is a member as before (rule 8: "cannot tell" is not "beam end")."""
    rows = ev.rows(Q.GLYPH_STROKES, subject=sub)
    if not rows or not isinstance(rows[-1].value, (list, tuple)):
        return None
    covered = [int(o) for o in rows[-1].value]
    partial = [int(p[0]) for p in ((rows[-1].detail or {}).get("partial") or ()) if len(p) >= 2]
    from .. import beam_strokes as BS
    cell = sub.at(Kind.CELL)
    # the cell's stroke map as `StrokeView`s -- the construction `rhythm._stroke_views` does, read HERE so this decision's `wants` are its own
    # reads; a stroke another mark owns (or two contest) has kind `owned` / `contested`, never a beam (2.205)
    mask = _owner_mask(ev.verdict(Q.STROKE_OWNER, subject=cell))
    views = []
    for r in ev.rows(Q.STROKE, scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        g = getattr(r.subject, "glyph", None)
        d = r.detail or {}
        box = d.get("stroke_box")
        if g is None or not (STROKE_GLYPH_BASE <= g < 400_000) or not box or len(box) < 4:
            continue
        views.append(BS.StrokeView(
            ordinal=g - STROKE_GLYPH_BASE, kind=mask.get(g - STROKE_GLYPH_BASE, str(r.value)), box=tuple(float(v) for v in box[:4]),
            length=float(d.get("length_spaces") or 0.0), thickness=float(d.get("thickness_spaces") or 0.0),
            sagitta=d.get("sagitta_spaces"), angle=float(d.get("angle_deg") or 0.0),
            touches=tuple((int(a), float(b)) for a, b in (d.get("touches") or ())),
            space_px=float(d.get("staff_space_local_px") or 0.0), row_id=r.id))
    if not views:
        return None
    role = BS.roles(views)
    beam = [o for o in covered + partial if o in role and role[o]["role"] == "beam"]
    own = [o for o in covered if o in role and role[o]["role"] != "beam"
           and next(v.kind for v in views if v.ordinal == o) in ("blob", "owned")]
    if beam and not own:
        return {"beam_strokes": sorted(set(beam)), "covered": covered}
    return None


def _beam_end_boxes(ev: Evidence, members: Sequence["_Member"], stem_box: Sequence[float],
                    direction: Optional[str], space: Optional[float]) -> Dict[str, Dict[str, Any]]:
    """ROADMAP 2.209. The members that are a BEAM'S END, not a head, keyed by their glyph key, each with the facts that say so. A member is one
    when BOTH witnesses hold (module constants): (1) `_on_beam_ink` (the stroke map: the box covers no blob of its own and stands on beam
    ink) and (2) the stem's geometry: it is the member nearest the tip, within `BEAM_END_TIP_MAX_SP` of it, while another member stands
    `BEAM_END_OTHER_MIN_SP` or more from the tip. Unknown direction, no staff-space unit or no stroke map names nobody (rule 8: cannot tell
    is not a beam end). Repeated while the tip-most member qualifies (a beam end can be boxed twice)."""
    out: Dict[str, Dict[str, Any]] = {}
    if direction not in ("up", "down") or not stem_box or not space or space <= 0:
        return out
    tip_y = stem_box[1] if direction == "up" else stem_box[1] + stem_box[3]
    live = [m for m in members if m.cy is not None]
    while len(live) >= 2:
        live.sort(key=lambda m: abs(m.cy - tip_y))
        first, rest = live[0], live[1:]
        d0 = abs(first.cy - tip_y) / space
        far = max(abs(m.cy - tip_y) for m in rest) / space
        if d0 > BEAM_END_TIP_MAX_SP or far < BEAM_END_OTHER_MIN_SP:
            break
        ink = _on_beam_ink(ev, first.sub)
        if ink is None:
            break
        out[first.key] = {"tip_distance_sp": round(d0, 2), "farthest_member_sp": round(far, 2), **ink}
        live = rest
    return out


MEMBER_INK_ENV = "OMR_STEM_MEMBER_INK"

#: ROADMAP 2.210. A synthesized `stem_end_head` box (GATHER reads a head at an orphan stem's end) can swallow the ink beside it. MEASURED on the
#: 2.202strokes records (frozen pages): 213 such members, 4 are larger than `MERGED_MIN_W_SP` x `MERGED_MIN_H_SP` AND cover >= `MERGED_MIN_STROKES`
#: strokes; all 4 are a clef, an "ff" or an accidental cluster (crops). The largest real open head among the other 209 is 2.2 x 2.0 sp. NARROWS who may vote.
MERGED_MIN_W_SP = 2.6
MERGED_MIN_H_SP = 2.2
MERGED_MIN_STROKES = 8
#: a tremolo slash sits ON the stem BETWEEN two of its heads, or at its tip with a head 2.5 sp or more away (page-facts section 1, Sean 2026-10-15 "never
#: oval - always thick diagonal lines"). The ownership layer's shape rule alone is NOT enough (measured: 5 of 8 boxes it refused as a slash look like a
#: real head beside a sharp / flat and a dot), so this is the second witness: where on the stem the box stands.
TREMOLO_BETWEEN_MIN_SP = 0.5


def member_ink_enabled() -> bool:
    """ROADMAP 2.210, flag `OMR_STEM_MEMBER_INK`, default OFF: a box counts as a member of a stem only if its own ink can be a notehead. ON includes
    the 2.209 beam-end test (`_beam_end_boxes`), which this generalises."""
    import os
    return os.environ.get(MEMBER_INK_ENV, "0").strip().lower() in ("1", "true", "yes", "on")


def _box_facts(ev: Evidence, sub: Subject) -> Dict[str, Any]:
    rows = ev.rows(Q.GLYPH_BOX, subject=sub)
    src = ((rows[-1].detail or {}).get("source") if rows else None)
    g = ev.rows(Q.GLYPH_STROKES, subject=sub)
    n = len(g[-1].value) if g and isinstance(g[-1].value, (list, tuple)) else None
    return {"source": src, "covered": n}


def _tremolo_boxes(ev: Evidence, cell: Subject, members: Sequence["_Member"], stem_box: Sequence[float],
                   direction: Optional[str], space: Optional[float], exclude: Set[str]) -> Dict[str, Dict[str, Any]]:
    """KIND tremolo. Witness 1 (ink-owner, 2.205): the stroke-owner box verdict REFUSED this box with `tremolo_slash_across_a_stem` (a thick diagonal
    stroke crossing a vertical). Witness 2 (stem geometry): it stands between two other members (>= 0.5 sp each side), or is the tip-most member,
    within `BEAM_END_TIP_MAX_SP` of the tip, with another member >= `BEAM_END_OTHER_MIN_SP` from it (2.209's pair)."""
    out: Dict[str, Dict[str, Any]] = {}
    if not space or space <= 0:
        return out
    v = ev.verdict(Q.STROKE_OWNER, subject=cell)
    boxes = ((getattr(v, "detail", None) or {}).get("boxes") or {}) if v is not None else {}
    live = [m for m in members if m.cy is not None and m.key not in exclude]
    for m in live:
        b = boxes.get(m.key)
        if not b or b[0] != "refused" or not any(str(l[3]).startswith("tremolo_slash_across_a_stem") for l in b[1]):
            continue
        others = [o for o in live if o is not m]
        above = [o for o in others if o.cy < m.cy - TREMOLO_BETWEEN_MIN_SP * space]
        below = [o for o in others if o.cy > m.cy + TREMOLO_BETWEEN_MIN_SP * space]
        between = bool(above and below)
        at_tip = False
        if direction in ("up", "down") and stem_box and others:
            tip_y = stem_box[1] if direction == "up" else stem_box[1] + stem_box[3]
            at_tip = (abs(m.cy - tip_y) == min(abs(o.cy - tip_y) for o in live)
                      and abs(m.cy - tip_y) / space <= BEAM_END_TIP_MAX_SP
                      and max(abs(o.cy - tip_y) for o in others) / space >= BEAM_END_OTHER_MIN_SP)
        if between or at_tip:
            out[m.key] = {"kind": "tremolo", "between": between, "at_tip": at_tip}
    return out


def _merged_ink_boxes(ev: Evidence, members: Sequence["_Member"], space: Optional[float]) -> Dict[str, Dict[str, Any]]:
    """KIND merged_ink. A synthesized `stem_end_head` box bigger than any head in both directions that covers `MERGED_MIN_STROKES` or more strokes
    is a clef / dynamic / accidental cluster. Witness 1: the box (reader + size); witness 2: the stroke map (how many strokes it stands on)."""
    out: Dict[str, Dict[str, Any]] = {}
    if not space or space <= 0:
        return out
    for m in members:
        if not m.box:
            continue
        f = _box_facts(ev, m.sub)
        w, h = m.box[2] / space, m.box[3] / space
        if (f["source"] == "stem_end_head" and w > MERGED_MIN_W_SP and h > MERGED_MIN_H_SP
                and (f["covered"] or 0) >= MERGED_MIN_STROKES):
            out[m.key] = {"kind": "merged_ink", "w_sp": round(w, 2), "h_sp": round(h, 2), "strokes": f["covered"]}
    return out


def _non_head_boxes(ev: Evidence, cell: Subject, members: Sequence["_Member"], stem_box: Sequence[float],
                    direction: Optional[str], space: Optional[float]) -> Dict[str, Dict[str, Any]]:
    """ROADMAP 2.210. The members whose own ink cannot be a notehead, keyed by glyph key, each with its kind and witnesses: beam_end (2.209),
    tremolo, merged_ink. Every kind needs two witnesses from different sources; a box nothing can speak for stays a member (rule 8)."""
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in _beam_end_boxes(ev, members, stem_box, direction, space).items():
        out[k] = {"kind": "beam_end", **v}
    out.update(_merged_ink_boxes(ev, [m for m in members if m.key not in out], space))
    out.update(_tremolo_boxes(ev, cell, members, stem_box, direction, space, set(out)))
    return out


class _Member:
    """One kept notehead of a stem, with what its own duration verdict says."""

    __slots__ = ("sub", "key", "verdict", "box", "cls", "whole_class",
                 "outcome", "options", "direction", "cy")

    def __init__(self, sub: Subject, verdict: Any, box: Any, cls: str,
                 direction: Optional[str]):
        self.sub = sub
        self.key = sub.to_key()
        self.verdict = verdict
        self.box = box
        self.cls = cls
        self.whole_class = _stands_on_a_stem_so_not_whole(cls)
        self.outcome = "none" if verdict is None else verdict.outcome.value
        self.options = _options(verdict)
        self.direction = direction
        self.cy = (box[1] + box[3] / 2.0) if box else None

    @property
    def decided(self) -> bool:
        return self.outcome == "decided" and len(self.options) == 1

    @property
    def narrowed(self) -> bool:
        return self.outcome == "narrowed" and len(self.options) >= 2

    @property
    def read(self) -> bool:
        return self.decided or self.narrowed

    @property
    def counts_for_base(self) -> bool:
        """A whole-class box on a stem casts no vote for base or levels
        ("Whole notes never have stems", Sean, DECISIONS 2026-10-09)."""
        return not self.whole_class


def _parts(value: Dict[str, Any]) -> Optional[Tuple[float, int, int]]:
    """`(head base, beam/flag levels, dots)` of a duration value -- the base is
    the head's own beats before any beam, flag or dot: 4 whole, 2 half, 1
    black."""
    try:
        written = float(value["written"])
        dots = int(value.get("dots") or 0)
        levels = int(value.get("beam_levels") or 0)
    except (KeyError, TypeError, ValueError):
        return None
    dot_factor = 2.0 - 2.0 ** (-dots)
    return (round(written * (2 ** levels) / dot_factor, 3), levels, dots)


def _options(verdict: Any) -> List[Tuple[float, int, int]]:
    """Every `(base, levels, dots)` a duration verdict admits: one for a
    DECIDED verdict, several for a NARROWED one, none for an abstention."""
    if verdict is None:
        return []
    if verdict.outcome is Outcome.DECIDED and isinstance(verdict.value, dict):
        p = _parts(verdict.value)
        return [p] if p else []
    if verdict.outcome is Outcome.NARROWED:
        out = []
        for c in verdict.candidates:
            p = _parts(c.value) if isinstance(c.value, dict) else None
            if p and p not in out:
                out.append(p)
        return out
    return []


def _written(base: float, levels: int, dots: int) -> float:
    """The arithmetic `rhythm._at_level_value` spells: a level halves the head
    value, each dot adds half of what stands so far."""
    t = base / (2 ** levels) if levels else base
    add = t
    for _ in range(dots):
        add /= 2.0
        t += add
    return t


def _scale_of(verdict: Any) -> float:
    """This head's OWN tuplet scale (`beats / written`): the stem's written
    value is the stem's, the tuplet it sits in is the head's."""
    cands = []
    if verdict is not None:
        if verdict.outcome is Outcome.DECIDED and isinstance(verdict.value, dict):
            cands = [verdict.value]
        else:
            cands = [c.value for c in verdict.candidates
                     if isinstance(c.value, dict)]
    for v in cands:
        try:
            w, b = float(v["written"]), float(v["beats"])
        except (KeyError, TypeError, ValueError):
            continue
        if w > 0:
            return b / w
    return 1.0


def _value(base: float, levels: int, dots: int, scale: float,
           stem: str) -> Dict[str, Any]:
    t = _written(base, levels, dots)
    fill = ("whole" if base >= 4.0 else "half" if base >= HOLLOW_BASE_MIN
            else "black")
    return {"beats": t * scale, "written": t, "dots": dots,
            "beam_levels": levels, "head_fill": fill, "stem": stem}


def _member_of(ev: Evidence, join: Any) -> Optional[_Member]:
    """The kept notehead a `Q.HEAD_STEM` verdict is about, or None where it is
    refused, another staff's copy, or a whole rest wearing a head's label."""
    sub = join.subject
    refusal = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=sub)
    if (refusal is not None and refusal.outcome is Outcome.DECIDED
            and refusal.value is True):
        return None
    rest = ev.verdict(Q.NOTEHEAD_IS_A_WHOLE_REST, subject=sub)
    if (rest is not None and rest.outcome is Outcome.DECIDED
            and rest.value is True):
        return None
    owner = ev.verdict(Q.GLYPH_OWNER, subject=sub)
    if (owner is not None and owner.outcome is Outcome.DECIDED
            and is_relocated_copy(sub, owner.value)):
        return None
    boxes = ev.rows(Q.GLYPH_BOX, subject=sub)
    box = _head_xywh(boxes[-1].value) if boxes else None
    cls = str(boxes[-1].value[0]) if boxes else ""
    dirv = ev.verdict(Q.STEM_DIRECTION, subject=sub)
    direction = (dirv.value if dirv is not None
                 and dirv.outcome is Outcome.DECIDED
                 and dirv.value in ("up", "down") else None)
    dur = ev.verdict(Q.DURATION, subject=sub)
    return _Member(sub, dur, box, cls, direction)


def _tip_order(members: Sequence[_Member], stem_box: Sequence[float],
               direction: Optional[str]) -> List[_Member]:
    """The members nearest the stem's TIP first. The tip is the end opposite
    the heads: the TOP of a stem pointing up, the BOTTOM of one pointing down.
    ⚠️ An unknown direction names no tip, so it returns NOTHING ordered rather
    than a guess."""
    if direction not in ("up", "down") or not stem_box:
        return []
    tip_y = stem_box[1] if direction == "up" else stem_box[1] + stem_box[3]
    ranked = [m for m in members if m.cy is not None]
    ranked.sort(key=lambda m: abs(m.cy - tip_y))
    return ranked


@decision(
    quantity=Q.STEM_VALUE,
    scope=Kind.GLYPH,
    wants=(Q.HEAD_STEM, Q.DURATION, Q.STEM_DIRECTION, Q.GLYPH_BOX,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.NOTEHEAD_IS_A_WHOLE_REST,
           Q.GLYPH_OWNER, Q.GLYPH_STROKES, Q.STROKE, Q.STROKE_OWNER,
           Q.CELL_STAFF_SPACE),
    subjects_from=Q.HEAD_STEM,
    reasons=("stem_agrees", "stem_value_from_evidence",
             "hollow_head_on_a_beamed_stem", "stem_levels_unread",
             "stem_dots_disagree", "stem_values_open", "stem_unread",
             "lone_head", "not_a_member", "ambiguous_stem", "no_stem"),
    mode=Mode.ADDITIVE,
    composed_from=(Q.HEAD_STEM, Q.DURATION, Q.STEM_DIRECTION, Q.GLYPH_BOX),
)
def adjudicate_stem_value(ev: Evidence) -> Ruling:
    """The written value of the stem this notehead stands on.

    ⚠️ THE STEM'S, NOT THE HEAD'S. Every kept notehead that stands on one stem
    gets the SAME `beats` / `written` / `dots` / `beam_levels` (a head's own
    tuplet scale aside). Components are decided by the stem's own evidence, in
    the order the module docstring gives, and DECIDED evidence outranks
    NARROWED evidence: a head whose own reading excludes the stem's value
    (tile 4: a black box narrowed to eighth|quarter beside a decided dotted
    half) takes the stem's value, because the box is a slash, a duplicate or a
    misread -- Sean's tiles 3, 4, 6, 8, 14.

    ⚠️ NEVER A VOTE. Where the evidence cannot say which of several readings is
    the stem's, the answer is a NARROWING over exactly those readings, with a
    reason word that names the cause; where no member is read it ABSTAINS.
    """
    mine = ev.verdict(Q.HEAD_STEM)
    if mine is None or mine.outcome is Outcome.ABSTAINED:
        return Ruling.abstain("no_stem")
    if mine.outcome is Outcome.NARROWED:
        return Ruling.abstain("ambiguous_stem")
    stem_id = mine.value
    stem_box = list((mine.detail or {}).get("stem_box") or ())
    cell = ev.subject.at(Kind.CELL)
    joins = [v for v in ev.verdicts(Q.HEAD_STEM,
                                    scope=Scope.SELF_AND_DESCENDANTS,
                                    subject=cell)
             if v.outcome is Outcome.DECIDED and v.value == stem_id]
    members: List[_Member] = []
    for j in joins:
        m = _member_of(ev, j)
        if m is not None:
            members.append(m)
    beam_ends: Dict[str, Dict[str, Any]] = {}
    if member_ink_enabled() and len(members) >= 2:
        dirs = {m.direction for m in members if m.direction}
        sp_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        try:
            space = float(sp_rows[-1].value) if sp_rows else None
        except (TypeError, ValueError):
            space = None
        beam_ends = _non_head_boxes(ev, cell, members, stem_box, next(iter(dirs)) if len(dirs) == 1 else None, space)
        if beam_ends:
            members = [m for m in members if m.key not in beam_ends]
    elif beam_end_enabled() and len(members) >= 2:
        dirs = {m.direction for m in members if m.direction}
        sp_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        try:
            space = float(sp_rows[-1].value) if sp_rows else None
        except (TypeError, ValueError):
            space = None
        beam_ends = _beam_end_boxes(ev, members, stem_box, next(iter(dirs)) if len(dirs) == 1 else None, space)
        if beam_ends:
            members = [m for m in members if m.key not in beam_ends]
    if all(m.sub != ev.subject for m in members):
        return Ruling.abstain("not_a_member")
    if len(members) < 2:
        return Ruling.abstain("lone_head")

    me = next(m for m in members if m.sub == ev.subject)
    scale = _scale_of(me.verdict)
    directions = {m.direction for m in members if m.direction}
    direction = next(iter(directions)) if len(directions) == 1 else None
    used = tuple(m.verdict.id for m in members if m.verdict is not None)

    strong = [m for m in members if m.counts_for_base]
    hollow = [m for m in strong if m.decided and m.options[0][0] >= HOLLOW_BASE_MIN]
    filled = [m for m in strong if m.decided and m.options[0][0] < HOLLOW_BASE_MIN]
    narrowed = [m for m in strong if m.narrowed]
    why: Dict[str, Any] = {"hollow": [m.key for m in hollow],
                           "filled": [m.key for m in filled],
                           "narrowed": [m.key for m in narrowed],
                           "direction": direction}

    # ── BASE ────────────────────────────────────────────────────────────────
    base_opts: List[float]
    if hollow:
        base_opts = [2.0]
        why["base_from"] = "hollow_head"
    elif filled:
        base_opts = [filled[0].options[0][0]]
        why["base_from"] = "filled_head"
    elif narrowed:
        sets = [{o[0] for o in m.options} for m in narrowed]
        common = set.intersection(*sets)
        base_opts = sorted(common) if common else sorted(set.union(*sets))
        why["base_from"] = "narrowed_common" if common else "narrowed_union"
        # "Whole notes never have stems": a whole base is not among a stem's
        # options. Where EVERY option was a whole, the hollow reading that is
        # left is the half (an open head on a stem is a half note, 2.70).
        no_whole = [b for b in base_opts if b < WHOLE_BASE]
        if len(no_whole) != len(base_opts):
            why["whole_excluded"] = True
        base_opts = no_whole or [2.0]
    elif any(m.whole_class for m in members):
        # nothing else on the stem is read, and the only open head is a box
        # classed as a whole: on a stem that box is a half
        base_opts = [2.0]
        why["base_from"] = "whole_class_box_on_a_stem_is_a_half"
    else:
        return Ruling.abstain("stem_unread")

    # ── LEVELS: the beams and flags hang at the stem's TIP ──────────────────
    tipwards = _tip_order(strong, stem_box, direction)
    why["tip_member"] = tipwards[0].key if tipwards else None
    conflict = False
    levels_opts: Set[int]
    if base_opts == [2.0]:
        levels_opts = {0}
        # a hollow head is never beamed (2.43): the tie nothing breaks is a
        # beam that reads CERTAIN at the tip. Unknown direction names no tip,
        # so ANY decided beamed filled member is then the same suspicion.
        tip_set = tipwards[:1] if tipwards else filled
        beamed = [m for m in tip_set if m.decided and m.options[0][0] < HOLLOW_BASE_MIN
                  and m.options[0][1] >= 1]
        if hollow and beamed:
            conflict = True
            why["beam_at_tip"] = [m.key for m in beamed]
    else:
        readers = [m for m in tipwards if m.read and m not in hollow]
        if readers:
            first = readers[0]
            levels_opts = {o[1] for o in first.options}
            why["levels_from"] = first.key
        elif not tipwards:
            pool = [m for m in strong if m.read and m not in hollow]
            levels_opts = {o[1] for m in pool for o in m.options} or {0}
            why["levels_from"] = "all_members_direction_unread"
        else:
            levels_opts = {0}
            why["levels_from"] = "none_read"

    # ── DOTS: the stem's ────────────────────────────────────────────────────
    # On a HOLLOW stem a dot read for a decided FILLED box is not the stem's
    # (that box is the slash or a duplicate in every non-note case Sean judged):
    # only the hollow heads' and whole-class boxes' dots count there.
    dot_voters = ([m for m in members if m not in filled]
                  if base_opts == [2.0] else members)
    decided_dots = {m.options[0][2] for m in dot_voters if m.decided}
    positive = {d for d in decided_dots if d > 0}
    if not positive:
        for m in dot_voters:
            if m.narrowed and all(o[2] > 0 for o in m.options):
                positive |= {o[2] for o in m.options}
    dots_opts = sorted(positive) if positive else [0]
    why["dots"] = dots_opts

    # ── the stem's value, or what it still admits ───────────────────────────
    combos: List[Tuple[float, int, int]] = []
    for b in base_opts:
        for lv in (sorted(levels_opts) if b < HOLLOW_BASE_MIN else [0]):
            for d in dots_opts:
                combos.append((b, lv, d))
    if conflict:
        beam_lv = sorted({o[1] for m in (tipwards[:1] if tipwards else filled)
                          if m.decided for o in m.options if o[1] >= 1})
        combos = [(2.0, 0, d) for d in dots_opts] + [
            (1.0, lv, d) for lv in beam_lv for d in dots_opts]
    combos = list(dict.fromkeys(combos))

    own = _options(me.verdict)
    detail = {"stem": stem_id, "members": [m.key for m in members],
              "head_reading": {"outcome": me.outcome,
                               "values": [list(o) for o in own]},
              "evidence": why}
    if beam_ends:
        detail["beam_end_boxes"] = beam_ends

    if len(combos) == 1:
        b, lv, d = combos[0]
        value = _value(b, lv, d, scale, stem_id)
        agrees = (me.decided and own and own[0] == combos[0]
                  and all(m.decided and m.options[0] == combos[0]
                          for m in members if m.counts_for_base))
        detail["changed"] = not (me.decided and own and own[0] == combos[0])
        # ⚠️ LITERAL REASONS AT EVERY RETURN, NOT A COMPUTED ONE: `brakes.
        # vocabulary_gap` resolves a decision's reasons by reading the string
        # literals in its `Ruling(...)` calls.
        if agrees:
            return Ruling(value=value, reason="stem_agrees", used=used,
                          detail=detail)
        return Ruling(value=value, reason="stem_value_from_evidence",
                      used=used, detail=detail)

    own_set = set(own)
    cands = tuple(Candidate(
        value=_value(b, lv, d, scale, stem_id),
        support=2.0 if (b, lv, d) in own_set else 1.0)
        for b, lv, d in combos)
    if conflict:
        return Ruling.narrow(cands, "hollow_head_on_a_beamed_stem", used=used,
                             **detail)
    if len(dots_opts) > 1:
        return Ruling.narrow(cands, "stem_dots_disagree", used=used, **detail)
    if len(levels_opts) > 1 and base_opts and base_opts[0] < HOLLOW_BASE_MIN:
        return Ruling.narrow(cands, "stem_levels_unread", used=used, **detail)
    return Ruling.narrow(cands, "stem_values_open", used=used, **detail)
