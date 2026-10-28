"""ROADMAP 2.217 -- the shared ink map, STEP 7: a head's LEDGER RUNGS from the stroke map (flag `OMR_LEDGERS_FROM_STROKES`, default OFF; needs
`OMR_STROKE_MAP`, and `OMR_STROKE_OWNER` for the ownership test).

STAGED ADJUDICATE, PURE: this module imports nothing from the pipeline. `adjudicators/ownership.py::_note_first_ledger_owner` (who owns the head)
and `adjudicators/position.py::adjudicate_notehead_position` (where it sits) are the only callers; they build `RungView`s from the cell's
`Q.STROKE` rows (page frame, the stroke's own local staff step) and hand them here with the head's page box. ONE reading replaces four
(`glyph_ladder`, `ledger_rung_ink`, `ledger_owner_density`, the walk of `far_head_reader`): they disagreed on 43% / 37% of the heads of the
frozen sample (FINDINGS), because two of them asked "is there ink where the staff spacing says a ledger should be" and two "what is printed
beside this head". The page says (page-facts section 3): ledgers are HAND-DRAWN, placed only by an ink read beside the head, never by
extending the staff spacing. This reads only the ink.

THE RULE (page-facts section 3 / CLAUDE section 5) --
  * a rung is a thin horizontal stroke wholly OUTSIDE the staff that no other mark owns (`Q.STROKE_OWNER`: an accidental's bar, a slur, a
    letter, a beam is not a rung; a stroke two marks contest is no witness either way, it can only make the answer `contested_ink`);
  * only rungs that span the head's x count, on the side the head lies on; they are counted OUTWARD from the staff edge in the order the ink
    has them, each placed by the staff measured at the stroke's own x -- NEVER by a spacing extended from the staff. A gap wider than one
    missing rung could hide is `gap_in_chain` (never assume a line you cannot see);
  * a rung through the head's centre (stubs on both sides) means the head is ON it; a head in the space just beyond the nearest rung on the
    staff side is in that space; a head in the first space outside the staff counts as on the staff and needs no ledger;
  * a head with no rung near it, farther than a space from the last one, is `head_beyond_last_rung`: abstained and counted, never a position.
THE CUTS are engraving sizes in half-steps, not tuned to a count; they may only NARROW until a third plate or Sean's tiles confirm them
(CLAUDE section 4). CONVENTION ASSUMED: the first rung stands about one space outside the staff and rungs are 0.5 to 1.8 spaces apart by
hand. WHAT WOULD FALSIFY IT: a print-confirmed head whose ledgers stand wider than `MAX_GAP_STEPS`. NOT CONFIRMED by Sean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

ENV = "OMR_LEDGERS_FROM_STROKES"

RUNG_MAX_THICK_SP = 0.35        # = stroke_owner.LEDGER_MAX_THICK_SP
RUNG_MAX_LEN_SP = 3.5           # = stroke_owner.LEDGER_MAX_LEN_SP
RUNG_MIN_LEN_SP = 0.9
RUNG_MAX_SLOPE_STEPS = 0.8      # a rung is level: its two ends differ by at most this many half-steps
OUTSIDE_MIN_STEPS = 0.9         # wholly outside the staff: both ends at least this far (half-steps) beyond the outer line
FIRST_RUNG_STEPS = (1.0, 3.3)   # the first rung's distance beyond the outer line
MAX_GAP_STEPS = 3.6             # consecutive rungs no further apart than this (a rung may hide in a wider gap)
MIN_SEPARATION_STEPS = 1.0      # two filings closer than this are one printed rung
SPAN_SLACK_HEAD_W = 0.25        # the rung spans the head when its x-extent holds the head's centre, with this slack
ON_TOL_STEPS = 0.65             # the head's centre is ON a rung within this many half-steps
SPACE_BEYOND_STEPS = (0.65, 1.7)  # ... and IN THE SPACE beyond the nearest staff-side rung within this window
RUNG_FAMILIES = ("ledger", "head")   # owners that leave a stroke a rung (the ledger's own; a head's lens a thin rung runs through)


@dataclass(frozen=True)
class RungView:
    """One `Q.STROKE` row in the PAGE frame. `ends` = (x0, y0, x1, y1) page px; `steps` = the staff step (from the top line) of each end,
    measured by the map at that end's own x."""
    ordinal: int
    row_id: str
    kind: str
    state: str                                   # "" | unclaimed | decided | merged | refused_claims | contested  (the owner verdict)
    family: Optional[str]
    ends: Tuple[float, float, float, float]
    steps: Tuple[float, float]
    space_px: float                              # page px per staff space AT the stroke
    length_sp: float
    thickness_sp: float


@dataclass(frozen=True)
class Rung:
    ordinal: int
    row_id: str
    y_at_head: float
    step: float                                  # mean step from the top line (negative above the staff)
    space_px: float


@dataclass
class Reading:
    """One head's ledger reading toward ONE candidate staff."""
    fits: bool
    pos: Optional[int]                           # integer half-steps from that staff's top line (0 top line, 8 bottom line)
    reason: str
    unread: bool = False                         # "could not look": no stroke map for the candidate's cell
    how: str = "strokes"
    rungs: Tuple[str, ...] = ()                  # stroke row ids counted
    contested: Tuple[str, ...] = ()
    geometry_position: Optional[float] = None
    agrees_with_geometry: Optional[bool] = None
    detail: Dict[str, object] = field(default_factory=dict)


def is_rung_shape(v: RungView) -> Tuple[bool, str]:
    if v.kind != "horizontal":
        return False, "kind:" + v.kind
    if v.thickness_sp > RUNG_MAX_THICK_SP:
        return False, "thick"
    if not (RUNG_MIN_LEN_SP <= v.length_sp <= RUNG_MAX_LEN_SP):
        return False, "length"
    if abs(v.steps[0] - v.steps[1]) > RUNG_MAX_SLOPE_STEPS:
        return False, "slope"
    return True, "ok"


def _side_of(s0: float, s1: float) -> Optional[str]:
    if max(s0, s1) <= -OUTSIDE_MIN_STEPS:
        return "above"
    if min(s0, s1) >= 8.0 + OUTSIDE_MIN_STEPS:
        return "below"
    return None


def _out(step: float, side: str) -> float:
    """Half-steps beyond the staff's outer line."""
    return -step if side == "above" else step - 8.0


def rungs_for_head(views: Sequence[RungView], head: Tuple[float, float, float, float], side: str
                   ) -> Tuple[List[Rung], List[RungView]]:
    """The rungs on `side` that span the head's x, outward order; and the contested strokes of that shape (not a witness, said apart)."""
    xc = (head[0] + head[2]) / 2.0
    slack = SPAN_SLACK_HEAD_W * (head[2] - head[0])
    out: List[Rung] = []
    contested: List[RungView] = []
    for v in views:
        ok, _why = is_rung_shape(v)
        if not ok or _side_of(*v.steps) != side:
            continue
        x0, y0, x1, y1 = v.ends
        if x1 < x0:
            x0, y0, x1, y1 = x1, y1, x0, y0
        if not (x0 - slack <= xc <= x1 + slack):
            continue
        if v.state == "contested":
            contested.append(v)
            continue
        if v.state in ("decided", "merged") and v.family not in RUNG_FAMILIES:
            continue                              # an accidental's bar, a hairpin line, a letter: another mark's ink
        t = 0.0 if x1 == x0 else min(1.0, max(0.0, (xc - x0) / (x1 - x0)))
        out.append(Rung(v.ordinal, v.row_id, y0 + t * (y1 - y0), (v.steps[0] + v.steps[1]) / 2.0, v.space_px))
    out.sort(key=lambda r: _out(r.step, side))
    kept: List[Rung] = []
    for r in out:      # one printed rung can be filed twice (cut by a stem): keep the first of any two closer than a rung can be
        if kept and _out(r.step, side) - _out(kept[-1].step, side) < MIN_SEPARATION_STEPS:
            continue
        kept.append(r)
    return kept, contested


def read_head(views: Optional[Sequence[RungView]], head: Optional[Tuple[float, float, float, float]],
              geometry_position: Optional[float]) -> Reading:
    """The head's position on the candidate staff, from the ink only; or a refusal with a reason word and its numbers.

    `views` None = the candidate's cell has no stroke map (`unread`). `head` = page box (x0, y0, x1, y1). `geometry_position` = the
    candidate-relative geometry position in half-steps from the top line, used ONLY to know which side the head lies on and whether it is in
    the first space outside the staff (no ledger needed) -- never as the position."""
    if geometry_position is None or head is None:
        return Reading(False, None, "no_geometry", unread=True)
    g = float(geometry_position)
    gr = int(round(g))
    if -1 <= gr <= 9:
        return Reading(True, gr, "no_ledger_needed (geometry %.2f)" % g, how="geometry", geometry_position=g, agrees_with_geometry=True)
    if views is None:
        return Reading(False, None, "no_stroke_map", unread=True, geometry_position=g)
    side = "above" if g < 0 else "below"
    sgn = -1 if side == "above" else 1
    edge = 0 if side == "above" else 8
    rungs, contested = rungs_for_head(views, head, side)
    cids = tuple(v.row_id for v in contested)
    if not rungs:
        why = ("contested_ink (%d contested stroke(s) could be the rung)" % len(contested)) if contested else "no_rung_beside_head (%s)" % side
        return Reading(False, None, why, contested=cids, geometry_position=g)
    half = sum(r.space_px for r in rungs) / len(rungs) / 2.0
    if half <= 0:
        return Reading(False, None, "no_local_spacing", unread=True, geometry_position=g)
    d1 = _out(rungs[0].step, side)
    if not (FIRST_RUNG_STEPS[0] <= d1 <= FIRST_RUNG_STEPS[1]):
        return Reading(False, None, "first_rung_off_the_staff (%.1f half-steps out)" % d1, rungs=(rungs[0].row_id,), geometry_position=g)
    yc = (head[1] + head[3]) / 2.0
    # signed distance of each rung from the head's centre in half-steps, positive = the rung lies BEYOND the head (away from the staff)
    outs = [((r.y_at_head - yc) / half) * (-1.0 if side == "above" else 1.0) for r in rungs]
    on = [i for i, o in enumerate(outs) if abs(o) <= ON_TOL_STEPS]
    if on:
        k = on[0] + 1
    else:
        behind = [i for i, o in enumerate(outs) if o < 0]
        if not behind:
            return Reading(False, None, "head_nearer_the_staff_than_every_rung", geometry_position=g)
        i = max(behind)
        gap = -outs[i]
        if not (SPACE_BEYOND_STEPS[0] <= gap <= SPACE_BEYOND_STEPS[1]):
            return Reading(False, None, "head_beyond_last_rung (%.1f half-steps past rung %d)" % (gap, i + 1),
                           rungs=tuple(r.row_id for r in rungs[:i + 1]), geometry_position=g,
                           detail=dict(gap_steps=round(gap, 2), rungs_seen=i + 1))
        k = i + 1
    chain = rungs[:k]
    prev = 0.0
    for r in chain:
        cur = _out(r.step, side)
        if cur - prev > MAX_GAP_STEPS:
            return Reading(False, None, "gap_in_chain (%.1f half-steps between rungs: a rung may be missing)" % (cur - prev),
                           rungs=tuple(x.row_id for x in chain), geometry_position=g)
        prev = cur
    pos = edge + sgn * (2 * k if on else 2 * k + 1)
    word = ("on ledger %d (%s; counted by ink)" % (k, side)) if on else ("in the space beyond ledger %d (%s)" % (k, side))
    return Reading(True, pos, word, rungs=tuple(x.row_id for x in chain), contested=cids, geometry_position=g,
                   agrees_with_geometry=(pos == gr), detail=dict(rungs_counted=k, on=bool(on)))
