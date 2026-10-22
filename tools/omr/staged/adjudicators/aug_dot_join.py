"""ROADMAP 2.127 -- a dot that was SEEN beside a note must not leave that note
written plain and unmarked (STAGED ADJUDICATE, `OMR_AUG_DOT_JOIN`, default ON).

WHAT THE BRAHMS RECORD SAID, AND WHAT IT WAS. `augmentation_decided_but_
unattached` counted 1,108 dots DECIDED augmentation that reach no duration, and
2.124 guessed "~390 of them beside a decided note: dotted notes written
undotted". `benchmarks/omr-aug-dots-2026-10/FINDINGS.md` takes the 1,108 apart:
555 name a ghost head another staff owns, 377 are the same physical dot a head
already carries from its OWN cell, 149 sit beside a note whose duration is not
decided (so the note is not written), and **16** sit beside a note whose
duration IS decided with no dot -- 8 of those a flag's curl boxed as a dot
(Brahms `1/0/5/1/14`, the neighbouring staff's flag tip in this strip's pad).
The second population is the dot the role decision never placed
(`dot_role_ambiguous`, ~65 beside a decided-plain head): 4 of Sean's 7 such
dots on page 0 of Brahms 317803 are dotted halves and quarters written plain.

THE RULE (CLAUDE.md §4, rule 8). A decided plain duration beside dot ink that
was SEEN and never placed is not "plain", it is "cannot tell". This module
does NOT lengthen the note: a flag's curl, a staccato of the next staff and a
real dot are one box to the geometry (the box sits level with the head in all
three), so lengthening would let a guess in. It NARROWS the note to
{as read, dotted} -- the reader's own two candidates, equal support, the order
claims nothing -- and INFER's existing bar collapse may then choose and label
it blue. A dot whose centre lies inside a DETECTED flag box is the flag's own
tip and narrows nothing.

CONNECT, NEVER GUESS: it reads the dot's DECIDED role (`Q.DOT_ROLE`) and the
head's live `Q.DURATION` and supersedes the latter with a narrowed verdict.
"""
from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .. import record as R
from ..record import Kind, Outcome, Q, Scope

AUG_DOT_JOIN_ENV = "OMR_AUG_DOT_JOIN"


def aug_dot_join_enabled() -> bool:
    """DEFAULT ON (Sean, 2026-10-14: "Yes"): an explicit `0`/`false`/`no`/`off`
    turns it off."""
    return os.environ.get(AUG_DOT_JOIN_ENV, "").strip().lower() not in (
        "0", "false", "no", "off")


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.128 -- a dot carries its staff position, and the join may use it
# ─────────────────────────────────────────────────────────────────────────────

DOT_POSITION_JOIN_ENV = "OMR_DOT_POSITION_JOIN"
_OFF_WORDS = ("0", "false", "no", "off")


def dot_position_join_enabled() -> bool:
    """`OMR_DOT_POSITION_JOIN`, DEFAULT ON (Sean, 2026-10-14: "Yes"; only an
    explicit off word turns it off, back to the box-geometry window alone)."""
    return os.environ.get(DOT_POSITION_JOIN_ENV, "").strip().lower() \
        not in _OFF_WORDS


#: A dot is read as ON A LINE only within `DOT_LINE_BAND` half-steps of a line
#: centre, and as IN A SPACE only beyond `DOT_SPACE_BAND`; between, it has not
#: told us (rule 8). CONVENTION CONFIRMED by Sean, 2026-10-14: *"Always in a
#: space"* -- an augmentation dot never stands on a line. So a reading near a
#: line is a measurement near the boundary or not a dot at all, and only a
#: reading CLEARLY on the line may refuse one. Measured on Brahms 317803 p.0
#: against Sean's labels: every one of 120 truth dots lies >= 0.31 steps from
#: a line centre (the nearest, `0/0/3/1/6`, is a dotted quarter's dot Sean
#: confirmed, standing 0.31 from the ledger line above its head); detected
#: dot-class boxes lie as close as 0.004. A cut-off is a measurement: one score.
DOT_LINE_BAND = 0.2
DOT_SPACE_BAND = 0.3
HEAD_MAX_RESIDUAL = 0.25
#: A head standing further than this many half-steps off the five lines has a
#: geometry position that is a long extrapolation (`Q.NOTEHEAD_POSITION`'s
#: ledger-counted verdict owns it), so its step is not read here. Measured on
#: Brahms 317803 p.0 against Sean's OnLine/InSpace labels: parity of the
#: geometry position agrees 205/206 inside the staff, 137/138 up to 4 steps
#: outside, 34/36 beyond 6.
HEAD_MAX_OUTSIDE_STEPS = 4.0


def expected_dot_steps(head_step: int) -> Tuple[int, ...]:
    """The steps an augmentation dot may stand at after a head at `head_step`
    (an even step is a LINE, an odd one a SPACE; 0 is the top line).

    THE CONVENTION (`docs/page-facts.md`: *a dot sits a space higher on a line
    note*; registered nowhere else): a dot stands in a SPACE, never on a line --
    after a note in a space, in that SAME space; after a note on a line, in the
    space ABOVE (`step - 1`, the usual) or, less often, BELOW (`step + 1`).
    Measured against Sean's labels on Brahms 317803 p.0: line heads 41 above /
    19 below / 1 two-above (of 61), space heads 54 of 56 in the same space.
    """
    return (head_step,) if head_step % 2 else (head_step - 1, head_step + 1)


def _clean_step(pos: float, margin_floor: float) -> Optional[int]:
    """A HEAD's step: the nearest integer, or None within `margin_floor` of the
    line/space boundary."""
    step = int(round(pos))
    return step if 0.5 - abs(pos - step) >= margin_floor else None


def _dot_cell(pos: float) -> Tuple[str, Optional[int]]:
    """`("line", even step)`, `("space", odd step)` or `("unclear", None)`.

    A space is the interval between two line centres, so a dot 0.31 steps off
    the line above its head is IN the space above it (step -1), not "on" the
    line: the nearest-integer step of 2.128's first cut read it as the line
    (-2) and vetoed a real dotted quarter.
    """
    line = 2 * int(round(pos / 2.0))
    off = abs(pos - line)
    if off <= DOT_LINE_BAND:
        return "line", line
    if off >= DOT_SPACE_BAND:
        return "space", line + (1 if pos > line else -1)
    return "unclear", None


def dot_head_compatible(dot_row: Optional[R.Observation],
                        head_row: Optional[R.Observation],
                        head_staff_key: Optional[str]) -> Optional[bool]:
    """Is this dot where an augmentation dot of this head stands?

    `True` / `False`, or `None` -- CANNOT TELL (rule 8: unknown is never
    "compatible" and never "incompatible"). `None` when either position is
    missing, the dot was measured against a staff other than the head's, the
    head stands far off the five lines (its step there is a ledger reading
    this fact does not own), or either reading sits on the line/space boundary.
    """
    if dot_row is None or head_row is None or not head_staff_key:
        return None
    dd = dot_row.detail or {}
    if dd.get("staff") != head_staff_key:
        return None
    hp = head_row.value
    if not isinstance(hp, (int, float)) or not \
            -HEAD_MAX_OUTSIDE_STEPS <= float(hp) <= 8.0 + HEAD_MAX_OUTSIDE_STEPS:
        return None
    h = _clean_step(float(hp), 0.5 - HEAD_MAX_RESIDUAL)
    kind, d = _dot_cell(float(dot_row.value))
    if h is None or kind == "unclear":
        return None
    # on a line: never an augmentation dot (Sean: always in a space);
    # in a space: only the head's own, or the one above/below its line
    return kind == "space" and d in expected_dot_steps(h)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.151 -- a dot is a dot whatever class the detector gave it
# ─────────────────────────────────────────────────────────────────────────────
#
# THE RULE (engraving convention, docs/page-facts.md: a dot stands to the RIGHT
# of its head, in a SPACE -- the head's own, or the one above/below its line).
# The detector boxes some printed dots as NOTEHEADS (Brahms: 39 held cells of
# the 20261014-night record, 15 of 16 crops a real augmentation dot; Sean's
# 2.146 tiles 23 and 34). The notehead gate already says so -- it refuses the
# box `too_narrow` / `is_a_dot` -- and NOTHING READ IT AS A DOT ("the value
# existed and nothing read it"). With the flag on:
#   * `rhythm._attached_dots` counts such a box as THIS head's dot where it
#     stands right of the head, in its augmentation window, the head is the
#     box's best kept head, and its staff position is the head's dot step
#     (`mark_head_compatible` True) -- the same position evidence 2.128 admits
#     a dot-class box on;
#   * a box the gate refused never OWNS a dot (`_attached_dots`): a refused
#     duplicate of a head (`head_cut_piece`) took Brahms p0 `0/0/4/3/0`'s dot
#     from the real head, which was then written plain;
#   * `reconcile_unjoined_dots` narrows a decided-plain head {as read, dotted}
#     beside such a box whose position cannot tell (rule 8) -- never where the
#     position says it is NOT this head's dot step.
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a dot-sized
# (<= `notehead_precision.DOT_SIZED_MAX_SPACES` both sides) notehead-class box
# the gate refused, at a head's dot step, is that head's augmentation dot;
# falsified by Sean's tiles showing such a box is ink of something else (a
# tie end, a letter tip, a staccato of the next staff). Default ON (Sean 2026-10-16).
DOT_BOXED_AS_A_HEAD_ENV = "OMR_DOT_BOXED_AS_A_HEAD"

#: The notehead gate's refusals that say "this box is dot-shaped ink".
DOT_SHAPED_REFUSALS = ("too_narrow", "is_a_dot")
#: A refused box no larger than this on BOTH sides, in staff spaces, is
#: dot-sized (`notehead_precision.DOT_SIZED_MAX_SPACES`; restated as a literal
#: so this light module does not import the notehead adjudicator, and pinned
#: equal to it by a test, `test_staged_dot_boxed_as_head_2_151`).
DOT_SHAPED_MAX_SPACES = 0.75
#: A dot-shaped refused box whose centre lies within this of a dot-class box's
#: is the same ink boxed twice (`rhythm.DOT_TWIN_MAX_SPACES`, 2.127).
TWIN_DOT_MAX_SPACES = 0.3


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.180 -- a "wedge" with no head it points to, standing beside a head
# in that head's dot space, is the head's augmentation dot (POSITION BEFORE SHAPE)
# ─────────────────────────────────────────────────────────────────────────────
# Measured on the 20261018-night Brahms record
# (`benchmarks/omr-augmentation-dots-2026-10/FINDINGS.md`): notes written PLAIN
# (read, not flagged) with a dot box beside them that the 2.131 wedge test called
# a wedge and then refused (`wedge_without_a_head`: no head above or below for it
# to point at); in the crops nearly all are a round augmentation dot whose box the
# staff line it touches has stretched (h/w >= 1.3 is the line's ink, the 2.133
# finding). The engraving rule decides it, the shape cut only narrows: a dot
# stands in a SPACE right of its head (Sean 2026-10-14, "Always in a space").
# Only the case the 2.131 ruling left open is touched: a wedge that POINTS at a
# head is still that head's staccatissimo and never a dot.
# CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a dot-family mark
# right of a head, in the augmentation window AND at that head's own dot step
# (2.128 staff position, both positions known), with no head above or below it,
# is that head's augmentation dot; falsified by Sean's blind tiles
# (`out/print/2.180-review/`) showing such a mark is a staccatissimo or other ink.
DOT_POSITION_OVER_WEDGE_ENV = "OMR_DOT_POSITION_OVER_WEDGE"


def dot_position_over_wedge_enabled() -> bool:
    """`OMR_DOT_POSITION_OVER_WEDGE`, default ON since 2026-10-20 (ROADMAP 2.180;
    Sean: "Let's land these."); only an explicit off-word disables."""
    return os.environ.get(DOT_POSITION_OVER_WEDGE_ENV, "").strip().lower() not in (
        "0", "false", "no", "off")


def dot_boxed_as_a_head_enabled() -> bool:
    """`OMR_DOT_BOXED_AS_A_HEAD`, default ON since 2026-10-16 (ROADMAP 2.151;
    Sean: "Land 2.151 ON."); only an explicit off-word disables."""
    return os.environ.get(DOT_BOXED_AS_A_HEAD_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


def head_box_is_dot_shaped(refusal: Optional[R.Verdict], w: float, h: float,
                           space: Optional[float]) -> bool:
    """A notehead-class box the gate REFUSED as dot-shaped ink, dot-sized on
    both sides (w, h and space in one unit)."""
    if refusal is None or refusal.outcome is not Outcome.DECIDED \
            or refusal.value is not True \
            or refusal.reason not in DOT_SHAPED_REFUSALS or not space:
        return False
    return w / space <= DOT_SHAPED_MAX_SPACES and h / space <= DOT_SHAPED_MAX_SPACES


def mark_head_compatible(mark_pos: Any, head_pos: Any) -> Optional[bool]:
    """`dot_head_compatible` for a mark measured as a NOTEHEAD (its
    `Q.NOTEHEAD_STAFF_POSITION`, the head's unit, against the same staff):
    True / False, or None where either reading cannot tell."""
    if not isinstance(mark_pos, (int, float)) \
            or not isinstance(head_pos, (int, float)):
        return None
    for p in (mark_pos, head_pos):
        if not -HEAD_MAX_OUTSIDE_STEPS <= float(p) <= 8.0 + HEAD_MAX_OUTSIDE_STEPS:
            return None
    h = _clean_step(float(head_pos), 0.5 - HEAD_MAX_RESIDUAL)
    kind, d = _dot_cell(float(mark_pos))
    if h is None or kind == "unclear":
        return None
    return kind == "space" and d in expected_dot_steps(h)


#: A dot with no decided role counts as "beside" a head when its left edge is
#: no more than this far right of the head's right edge, and no more than
#: `UNRESOLVED_MAX_DY_SPACES` above or below its centre. CONVENTION ASSUMED /
#: WHAT WOULD FALSIFY IT / NOT CONFIRMED: measured over Brahms
#: `overnight-20261013-night` (the role window itself is gap <= ~0.7 sp,
#: 0.75 above / 0.25 below; the 596 refused dots lie mostly in -0.75..-0.25
#: and 0.75..1.0, the two near-misses on Sean's page 0), so the window here
#: only has to include them. A cut-off is a measurement: Sean's tiles decide.
UNRESOLVED_MAX_GAP_SPACES = 1.2
UNRESOLVED_MIN_GAP_SPACES = -0.1
UNRESOLVED_MAX_DY_SPACES = 1.3

#: The role decision's own staccato window (`rhythm.STACCATO_*`), in spaces.
STACCATO_CENTRED_MAX_SPACES = 0.5
STACCATO_OFFSET_MIN_SPACES = 0.75
STACCATO_MAX_GAP_SPACES = 2.0

#: A dot's page box centre inside a flag glyph's page box is the flag's tip.
FLAG_CLASS_PREFIX = "flag"

NARROWED_REASON = "dot_seen_beside_a_plain_note"


def _box(log: R.Log, sub: R.Subject):
    """`(class, value, page bbox)` of a glyph's last `Q.GLYPH_BOX` row."""
    rows = log.rows(Q.GLYPH_BOX, sub)
    if not rows:
        return None
    r = rows[-1]
    v = r.value
    bb = (r.detail or {}).get("bbox_page_px")
    if not isinstance(v, (list, tuple)) or len(v) < 5 or not bb or len(bb) != 4:
        return None
    return str(v[0]), v, tuple(float(x) for x in bb), r


def _undotted_narrowing(v: Optional[R.Verdict]) -> bool:
    """A NARROWED note none of whose candidates carries a dot (Brahms
    `0/0/11/0/4`, `0/0/11/0/9`: candidates {eighth, quarter}, and INFER chose
    the plain quarter where Sean reads a DOTTED quarter)."""
    return (v is not None and v.outcome is Outcome.NARROWED
            and bool(v.candidates)
            and all(isinstance(c.value, dict) and not c.value.get("is_rest")
                    and c.value.get("dots") == 0 for c in v.candidates))


def _plain_note(v: Optional[R.Verdict]) -> bool:
    return (v is not None and v.outcome is Outcome.DECIDED
            and isinstance(v.value, dict) and not v.value.get("is_rest")
            and v.value.get("dots") == 0)


def _dotted_candidate(value: Dict[str, Any]) -> Dict[str, Any]:
    """The same note with one dot: every length scaled by 1.5."""
    out = dict(value)
    out["dots"] = 1
    for k in ("beats", "written"):
        if isinstance(value.get(k), (int, float)):
            out[k] = value[k] * 1.5
    return out


def reconcile_unjoined_dots(log: R.Log) -> Dict[str, int]:
    """Narrow every decided-plain note that has a dot seen beside it.

    Run after `Q.DURATION`. `{}` when `OMR_AUG_DOT_JOIN` is switched off. Returns the
    census (also what the tests read): `narrowed_decided_dot_named_this_head`,
    `narrowed_unplaced_dot_beside_this_head`, `dot_is_a_flag_tip`,
    `head_already_dotted_or_not_a_decided_note`, `no_head_beside_the_dot`.
    """
    if not aug_dot_join_enabled():
        return {}
    census: Counter = Counter()

    # --- page index: flag boxes, and every live non-refused notehead --------
    flags: Dict[Tuple[int, int], List[Tuple[float, float, float, float]]] = \
        defaultdict(list)
    heads: Dict[Tuple[int, int], List[Tuple[str, Tuple[float, ...]]]] = \
        defaultdict(list)
    dots: List[Tuple[R.Subject, R.Verdict]] = []
    # ROADMAP 2.151 (`OMR_DOT_BOXED_AS_A_HEAD`): notehead boxes the gate refused
    # as dot-shaped ink -- (subject, refusal verdict, `_box` tuple)
    as_head = dot_boxed_as_a_head_enabled()
    marks: List[Tuple[R.Subject, R.Verdict, Any]] = []
    dot_centres: Dict[Tuple[int, int], List[Tuple[float, float]]] = \
        defaultdict(list)
    for sub in log.subjects(Kind.GLYPH):
        role = log.verdict(Q.DOT_ROLE, sub)
        if role is not None:
            dots.append((sub, role))
        b = _box(log, sub)
        if b is None:
            continue
        cls, _v, bb, _r = b
        if role is not None:
            dot_centres[(sub.page, sub.system)].append(
                ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0))
        if cls.startswith(FLAG_CLASS_PREFIX):
            flags[(sub.page, sub.system)].append(bb)
        elif cls.startswith("notehead"):
            refused = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
            if refused is not None and refused.outcome is Outcome.DECIDED \
                    and refused.value is True:
                if as_head and refused.reason in DOT_SHAPED_REFUSALS:
                    marks.append((sub, refused, b))
                continue
            heads[(sub.page, sub.system)].append((sub.to_key(), bb))

    # head key -> (dot subject, kind) first claim wins, one narrowing per head
    claims: Dict[str, Tuple[R.Subject, R.Verdict, str]] = {}
    for dsub, role in dots:
        named = (role.detail or {}).get("head")
        if role.outcome is Outcome.DECIDED and role.value == "augmentation":
            if not named:
                continue
            kind = "narrowed_decided_dot_named_this_head"
            target = named
        elif role.outcome is Outcome.ABSTAINED \
                and role.reason == "dot_role_ambiguous":
            target = None
            kind = "narrowed_unplaced_dot_beside_this_head"
        else:
            continue
        db = _box(log, dsub)
        if db is None:
            continue
        _c, dval, dpb, _drow = db
        # a flag's own curl is not a dot
        cx, cy = (dpb[0] + dpb[2]) / 2.0, (dpb[1] + dpb[3]) / 2.0
        if any(f[0] <= cx <= f[2] and f[1] <= cy <= f[3]
               for f in flags[(dsub.page, dsub.system)]):
            census["dot_is_a_flag_tip"] += 1
            continue
        if target is None:
            cell = dsub.at(Kind.CELL)
            sp = log.rows(Q.CELL_STAFF_SPACE, cell,
                          scope=Scope.SELF_AND_ANCESTORS)
            if not sp or not dval[3]:
                continue
            k = (dpb[2] - dpb[0]) / float(dval[3])   # page px per cell px
            space = float(sp[-1].value) * k
            if space <= 0:
                continue
            # a mark centred over some OTHER head, above or below it, is that
            # head's staccato (the role decision's own staccato window)
            if any(abs(cx - (hb[0] + hb[2]) / 2.0) <= STACCATO_CENTRED_MAX_SPACES
                   * space and STACCATO_OFFSET_MIN_SPACES * space
                   <= abs((hb[1] + hb[3]) / 2.0 - cy) <= STACCATO_MAX_GAP_SPACES
                   * space for _k, hb in heads[(dsub.page, dsub.system)]):
                census["staccato_like_over_another_head"] += 1
                continue
            best, best_score = None, float("inf")
            for key, hb in heads[(dsub.page, dsub.system)]:
                gap = (dpb[0] - hb[2]) / space
                dy = ((hb[1] + hb[3]) / 2.0 - cy) / space
                if gap < UNRESOLVED_MIN_GAP_SPACES \
                        or gap > UNRESOLVED_MAX_GAP_SPACES \
                        or abs(dy) > UNRESOLVED_MAX_DY_SPACES:
                    continue
                score = gap + 2.0 * abs(dy)
                if score < best_score:
                    best, best_score = key, score
            if best is None:
                census["no_head_beside_the_dot"] += 1
                continue
            target = best
        claims.setdefault(target, (dsub, role, kind))

    for msub, refusal, mb in marks:
        _c, mval, mpb, _mrow = mb
        if not mval[3]:
            continue
        sp = log.rows(Q.CELL_STAFF_SPACE, msub.at(Kind.CELL),
                      scope=Scope.SELF_AND_ANCESTORS)
        if not sp:
            continue
        space = float(sp[-1].value) * (mpb[2] - mpb[0]) / float(mval[3])
        if not head_box_is_dot_shaped(refusal, mpb[2] - mpb[0],
                                      mpb[3] - mpb[1], space):
            continue
        cx, cy = (mpb[0] + mpb[2]) / 2.0, (mpb[1] + mpb[3]) / 2.0
        if any(f[0] <= cx <= f[2] and f[1] <= cy <= f[3]
               for f in flags[(msub.page, msub.system)]):
            census["dot_boxed_as_a_head_is_a_flag_tip"] += 1
            continue
        # the same ink as a dot-class box: that box's role speaks for it
        if any(abs(cx - x) <= TWIN_DOT_MAX_SPACES * space
               and abs(cy - y) <= TWIN_DOT_MAX_SPACES * space
               for x, y in dot_centres[(msub.page, msub.system)]):
            census["dot_boxed_as_a_head_twin_of_a_dot_box"] += 1
            continue
        if any(abs(cx - (hb[0] + hb[2]) / 2.0) <= STACCATO_CENTRED_MAX_SPACES
               * space and STACCATO_OFFSET_MIN_SPACES * space
               <= abs((hb[1] + hb[3]) / 2.0 - cy) <= STACCATO_MAX_GAP_SPACES
               * space for _k, hb in heads[(msub.page, msub.system)]):
            census["dot_boxed_as_a_head_staccato_like"] += 1
            continue
        mpos = log.rows(Q.NOTEHEAD_STAFF_POSITION, msub)
        best, best_score = None, float("inf")
        for key, hb in heads[(msub.page, msub.system)]:
            gap = (mpb[0] - hb[2]) / space
            dy = ((hb[1] + hb[3]) / 2.0 - cy) / space
            if gap < UNRESOLVED_MIN_GAP_SPACES \
                    or gap > UNRESOLVED_MAX_GAP_SPACES \
                    or abs(dy) > UNRESOLVED_MAX_DY_SPACES:
                continue
            hsub = R.Subject.from_key(key)
            if hsub.staff == msub.staff and hsub.cell == msub.cell:
                hpos = log.rows(Q.NOTEHEAD_STAFF_POSITION, hsub)
                if mpos and hpos and mark_head_compatible(
                        mpos[-1].value, hpos[-1].value) is False:
                    continue        # the position says: not this head's dot
            score = gap + 2.0 * abs(dy)
            if score < best_score:
                best, best_score = key, score
        if best is None:
            census["dot_boxed_as_a_head_beside_no_head"] += 1
            continue
        claims.setdefault(best, (msub, refusal, "narrowed_dot_boxed_as_a_head"))

    for head_key, (dsub, role, kind) in claims.items():
        hsub = R.Subject.from_key(head_key)
        hv = log.verdict(Q.DURATION, hsub)
        if _undotted_narrowing(hv):
            # the reader's own candidates plus each one with a dot, in the
            # reader's order and support; nothing is chosen here
            cands = list(hv.candidates) + [
                R.Candidate(value=_dotted_candidate(dict(c.value)),
                            support=c.support) for c in hv.candidates]
            basis = tuple(x for x in (hv.id, role.id) if x)
            log.record(R.Verdict(
                id=log._next_id("vrd"), subject=hsub, quantity=Q.DURATION,
                outcome=Outcome.NARROWED, value=None,
                decider="reconcile_unjoined_dots",
                reason=NARROWED_REASON, considered=basis, basis=basis,
                used=tuple(hv.used or ()), candidates=tuple(cands),
                supersedes=hv.id,
                detail={"dot": dsub.to_key(), "dot_role": role.reason,
                        "dot_role_outcome": role.outcome.value,
                        "kind": kind, "was_reason": hv.reason,
                        "extended_narrowing": True}))
            census["extended_a_narrowing_with_dotted_candidates"] += 1
            continue
        if not _plain_note(hv):
            census["head_already_dotted_or_not_a_decided_note"] += 1
            continue
        arow = log.rows(Q.AUG_DOT, dsub)
        if arow and arow[-1].id in (hv.used or ()):
            census["already_joined"] += 1
            continue
        plain = dict(hv.value)
        basis = tuple(x for x in (hv.id, role.id) if x)
        out = R.Verdict(
            id=log._next_id("vrd"), subject=hsub, quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="reconcile_unjoined_dots", reason=NARROWED_REASON,
            considered=basis, basis=basis, used=tuple(hv.used or ()),
            candidates=(R.Candidate(value=plain, support=1.0),
                        R.Candidate(value=_dotted_candidate(plain),
                                    support=1.0)),
            supersedes=hv.id,
            detail={"dot": dsub.to_key(), "dot_role": role.reason,
                    "dot_role_outcome": role.outcome.value,
                    "kind": kind, "was": plain})
        log.record(out)
        census[kind] += 1
    return dict(census)
