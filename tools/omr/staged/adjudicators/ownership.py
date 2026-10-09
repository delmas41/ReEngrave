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

import os
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

from ... import transcribe as _legacy_articulation
from ..adjudicate import Checkable, Evidence, Mode, Ruling, Term, decision, tally
from .. import record as R
from ..gather import (CONTEST_IOU, LEDGER_ROUND_UP,
                      PAGE_EDGE_MARGIN_SPACES, _iou,
                      owner_from_staves_enabled)
from ..record import Kind, Outcome, Q, Scope
# ⚠️ ROADMAP 2.27d: the shared "is this staff one half of a decided brace
# pair" query -- see `structure.grand_staff_partner_staff`'s own docstring.
from . import structure as _structure

# ⚠️ ASSUMED WEIGHTS (A-OWN-1). Ordered to match the tiers the existing code
# already applies in this order; none is measured.
W_LADDER_COMPLETE = 4.0     # an unbroken run of ledger rungs
W_RANGE_IMPOSSIBLE = -6.0   # a veto on the IMPOSSIBLE, never on the unlikely
W_DISTANCE = 0.5            # the tie-break, and only that

# ⚠️ ASSUMED WEIGHT (A-OWN-3), ROADMAP 2.6c (Sean, DECISIONS 2026-09-28: "a
# hairpin sits under its staff"). Sized to be decisive against the range veto
# alone (`7.0 > abs(W_RANGE_IMPOSSIBLE)`), not measured, same as A-OWN-1.
#
# ⚠️⚠️ THERE IS NO `W_LEDGER_DIRECTION` ANY MORE, AND THAT IS THE CHANGE.
# 2.6c's first half made the ledger direction an ADDITIVE +8.0 term; Sean then
# ruled it AUTHORITATIVE ("nearer to the staff is not always going to be right
# but ledger lines will be"), so it is now a GATE ahead of every weight:
# `ledger_direction` below returns before a single term is summed, and no
# accumulation of hairpin + veto + distance can outvote it
# (`test_staged_ledger_direction.TestTheHardGate` pins the case that did).
W_HAIRPIN_SEPARATES = 7.0   # a hairpin sits under its own staff

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.6c (second half) — WHICH STAFF DO THE RUNGS POINT TO, ANSWERED ONCE
#
# `ledger_direction` is the ONE helper both `glyph_owner` and 2.7b's
# `notehead_precision._belongs_to_a_nearer_staff` ask, so the two decisions
# cannot credit a rung differently. Its inputs are geometry every record
# carries (the head's page box, each candidate staff's lines and spacing, the
# `ledgerLine` boxes with their 3.4g-2 refusal verdicts); GATHER's anonymous
# `Q.GLYPH_LADDER` count is the fallback only where that geometry is absent.
#
# CONVENTION (Sean, 2026-09-28, stated): the ledger lines between a far note
# and a staff name its owner; nearness never overrides them; a far note with
# no rungs either way is a reading gap. The three thresholds below are how a
# LADDER is told from a stray rung, and they are NOT Sean's:
#
#   CONVENTION ASSUMED: a ledger ladder runs from the staff to the note and
#     stops AT the note -- the note stands on its outermost rung or in the
#     space just beyond it (`LADDER_REACH_SPACES`); the detector may miss ONE
#     rung of a real ladder (`LADDER_MAX_MISSING`); a rung within half a space
#     of the head is its own line and names no staff (`OWN_LINE_MAX_SPACES`).
#   WHAT WOULD FALSIFY IT: a print-confirmed far note whose own ladder has two
#     or more rungs missing, or ends a space or more short of it; or a
#     chord-mate's own ledger that is contiguous with and reaches the head
#     from the WRONG staff.
#   NOT CONFIRMED by Sean. Measured on the six 2.7b.8 heads he adjudicated
#     (FINDINGS §2.6c.2): his three G heads have 0 / 1 / 0 missing and reach
#     0.78 / 0.06 / 0.03 spaces; the two wrongly-credited O heads have 2 and 4
#     missing; the `s` of *sempre* (N) ends 1.37 spaces short.
# ─────────────────────────────────────────────────────────────────────────────

#: A kept rung this close to the head's own centre is the head's OWN ledger
#: line: it says the note stands on a ledger, not whose. MOVED here from
#: `notehead_precision.OWN_LEDGER_MAX_SPACES` (2.7b, measured there: of 79 far
#: heads the first cut kept on a rung, 43 were kept by a rung 0.00-0.37 spaces
#: from the head and the rest stood at 0.63+; 0.5 is the empty interval's
#: middle), which now re-exports it -- one number, two readers.
OWN_LINE_MAX_SPACES = 0.5
#: GATHER's own grid tolerance (`gather._observe_ladder`: `abs(ry - want) <=
#: spacing * 0.5`), so a rung this walk matches at step k is the rung GATHER
#: would have counted there.
RUNG_GRID_TOLERANCE_SPACES = 0.5
#: A ladder may be ONE rung short and still be a ladder. Breitkopf brk-02
#: (`glyph/9/0/11/0/1`, Sean: the filed staff) has rungs 2 and 3 and not 1.
LADDER_MAX_MISSING = 1
#: ... and must END at the note: the head within this many spaces of the
#: outermost rung found (0 on the rung, 0.5 in the space beyond it; 1.0 would
#: be the NEXT line, whose rung is then missing between them). Litolff #1
#: (Sean: the filed staff) reaches at 0.78; the `s` at 1.37 does not.
LADDER_REACH_SPACES = 1.0
#: A contest is FAR -- and abstains `far_no_rungs` when no rung is found
#: toward any candidate -- only where EVERY candidate needs at least this many
#: rungs (GATHER's arithmetic: gap >= 1.75 spaces). A candidate needing 0 or 1
#: is a near miss, a hint rather than a claim, and keeps today's tiers.
FAR_MIN_RUNGS = 2

# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.6f -- A RUNG THAT IS ANOTHER CANDIDATE'S OWN STRUCTURE NEVER
# COUNTS TOWARD A FARTHER ONE (Sean, via §2.6c.2/§2.6c.3: "if a ledger answer
# disagrees with the print, the RUNG FINDING is wrong, not the rule")
#
# FINDINGS §2.6c.3 read all 9 Breitkopf `ledger_direction`/`range_veto`
# reversals §2.6c.2 left unadjudicated by eye: 7 of 9 share one shape. The
# note stands right at its NEAR candidate's own first ledger (`anchor_y` within
# 0.003-0.111 spaces of `head_y` in all seven); every one also has a SECOND
# real `ledgerLine` box exactly one more space out, on the far side of the
# head from that near candidate -- §2.7b's own docstring already names this
# shape for its OWN two prior instances (#4/#22, 2026-09-28): "a CHORD-MATE's
# own ledger (the near staff's second rung, beyond the head)". The FAR
# candidate's own multi-step walk (needing 2-3 steps from ITS OWN, much more
# distant edge) reaches that same box too, inside `RUNG_GRID_TOLERANCE_SPACES`
# (0.5 sp -- loose by construction, CLAUDE.md rule 5 and 2.6c.2's own six-head
# fixture reach up to 0.42 sp on a genuine ladder), and because
# `ledger_direction` is a HARD GATE, that one coincidental match decides the
# whole contest before hairpin/ladder/range/distance are ever weighed.
#
# CONVENTION ASSUMED: a rung is toward the candidate whose OWN established
# own-line it continues by an INTEGER number of staff spaces, not the
# candidate whose independent, longer walk merely happens to also reach it.
# Measured against the SAME rung: the near candidate's own-line-anchored
# residual is 0.003-0.111 spaces (mean 0.041) on the seven; the far
# candidate's own edge-anchored residual for the identical box is 0.015-0.39
# spaces -- #1/#2 (0.36/0.39) are not reachable by simply tightening
# `RUNG_GRID_TOLERANCE_SPACES`, which would also refuse real far-note ladders
# elsewhere (2.6c.2's fixture needs up to 0.42). `OWN_STRUCTURE_TOLERANCE_
# SPACES` below is set at 0.2 -- roughly double the worst of the seven
# residuals (0.111) and still well inside the loosest false match (0.36) it
# must catch, while leaving room the tightest TRUE far-ladder step measured
# so far (0.42, 2.6c.2's fixture) does not fall inside.
#
# WHAT WOULD FALSIFY IT, AND WHAT ALREADY DID (repaired, not merely noted):
# Litolff #14 (2.6c.2's own fixture, a positive control) is EXACTLY this
# falsifying shape -- a COMPLETE 3-of-3 ladder from the true far staff whose
# own outermost rung sits 0.08 px from a different, nearer candidate's
# own-line. The guard added because of it: the check never fires on a side
# that is ALREADY complete (`missing >= 1` required first) -- every one of
# the seven §2.6c.3 candidates this lane fixes has `missing == 1`, so the
# guard costs the fix nothing. What would STILL falsify it: an INCOMPLETE
# far ladder (missing >= 1) whose one remaining `toward` rung is genuinely
# its own, print-confirmed, yet also lands within 0.2 spaces of an integer
# number of staff-spaces beyond a nearer candidate's own-line -- none of the
# nine §2.6c.3 contests or the six §2.6c.2/2.7b.8 fixture heads is this; NOT
# CONFIRMED beyond them. This check never compares a side against ITS OWN
# `anchor_y` (a candidate that genuinely needs two rungs for THIS SAME note
# keeps both -- the positive control this lane's tests pin).
OWN_STRUCTURE_TOLERANCE_SPACES = 0.2

#: `glyph_owner` abstentions that mean *we could not read whose this is*.
#: EXPORT refuses such a head under `owner_not_read` rather than writing it on
#: the staff it was cut from (CLAUDE.md rule 8: a fallback never converts
#: "cannot tell" into an answer).
#:
#: ⚠️⚠️ ROADMAP 2.6e. `tied` (line ~306: two candidates score exactly equal)
#: predated this lane and was deliberately left off -- FINDINGS
#: §2.6c.2's open item. Left off, it was worse than `far_no_rungs` ever was:
#: a contested head is detected TWICE, once from each staff's own cell, so
#: BOTH of a `tied` contest's two subjects abstain independently and BOTH
#: fell through `is_relocated_copy(None) == False` to be WRITTEN -- the same
#: printed note on two staves, not one guess but two. `no_evidence` (line
#: ~276, `if not scored`) is the same fall-through by the same construction
#: and is fixed alongside it, though it was measured to occur zero times on
#: the Litolff acceptance record (`benchmarks/omr-owner-domain-2026-09/
#: FINDINGS.md` §2.6e) -- CLAUDE.md rule 8 draws no line at "rare".
#: ROADMAP 2.37 adds `ledger_all_refuted` (Sean, 2026-09-29): every
#: candidate's ladder was cleanly refuted by the ink, not merely unread --
#: a reader failure, held out exactly like a reading gap, but counted
#: apart from `far_no_rungs` so the two are never conflated.
#: ROADMAP 2.37 (Sean's redirect) adds `ledger_witnesses_disagree`: the
#: relative density comparison and the detector-based ladder each have an
#: opinion and they DISAGREE -- neither is trusted alone, held out exactly
#: like a reading gap.
#: ROADMAP 2.58d adds `stem_disagrees`: the stem witness and a ledger
#: witness name DIFFERENT staves -- held out like `ledger_witnesses_disagree`.
OWNER_NOT_READ_REASONS = ("far_no_rungs", "tied", "no_evidence",
                          "ledger_all_refuted", "ledger_witnesses_disagree",
                          "stem_disagrees")

#: A candidate's `Q.LEDGER_OWNER_DENSITY` reading must beat the OTHER
#: candidate's own reading by at least this ratio to decide ownership --
#: "clearly more", not merely more. Self-calibrating per plate: the ratio
#: is between the two candidates' OWN readings, never a fixed floor
#: compared across documents (Sean's redirect, 2026-09-29).
LEDGER_OWNER_RATIO_MIN = 2.0
#: ...and the WINNING side's own reading must clear this floor, or two
#: near-empty readings could satisfy the ratio by noise alone.
LEDGER_OWNER_FLOOR = 0.15


def _ledger_owner_comparison(ev: Evidence, cand_keys: Sequence[Optional[str]]
                             ) -> Optional[Tuple[str, Dict[str, Any]]]:
    """ROADMAP 2.37 (Sean's redirect, 2026-09-29, quoted at `gather.
    gather_ownership_evidence`'s own note): `Q.LEDGER_OWNER_DENSITY`
    readings for this contest's candidates -- a RATIO comparison, never
    an absolute floor. Returns `(winner_staff, detail)`, or `None` where
    fewer than exactly two candidates have a reading (this mechanism is
    Sean's own two-candidate case, "staff A above, B below"; a contest
    with more sides is left to the existing tiers), where the winning
    side does not clear `LEDGER_OWNER_FLOOR`, or where the two are not
    CLEARLY different (`LEDGER_OWNER_RATIO_MIN`) -- comparable or both
    near-empty is a genuine reading gap, not a guess either way."""
    readings: Dict[str, float] = {}
    for row in ev.rows(Q.LEDGER_OWNER_DENSITY):
        cand = (row.detail or {}).get("candidate")
        if cand in cand_keys and cand not in readings:
            try:
                readings[cand] = float(row.value)
            except (TypeError, ValueError):
                continue
    if len(readings) != 2:
        return None
    (ka, da), (kb, db) = sorted(readings.items())
    if da >= db:
        hi_k, hi_v, lo_v = ka, da, db
    else:
        hi_k, hi_v, lo_v = kb, db, da
    if hi_v < LEDGER_OWNER_FLOOR:
        return None
    ratio = float("inf") if lo_v <= 0 else hi_v / lo_v
    if ratio < LEDGER_OWNER_RATIO_MIN:
        return None
    return hi_k, {
        "readings": {k: round(v, 4) for k, v in readings.items()},
        "ratio": None if ratio == float("inf") else round(ratio, 3),
    }


def _note_first_ledger_owner(ev: Evidence) -> Optional[Tuple[str, Tuple[str, ...], Dict[str, Any]]]:
    """ROADMAP 2.56b. The far head read toward EACH candidate staff by the
    note-first look (`gather._file_owner_ledger_readings`): the note's own line
    first, then the ledgers counted from it to that staff's edge. Sean
    (2026-09-28, CLAUDE.md §10): the ledgers name the owner, nearness is only a
    hint. Returns `(owner staff key, row ids, detail)` where EXACTLY ONE
    candidate's ladder fits, `None` (the witness is silent, the older tiers run
    as they did) where

      * no such row was filed (the flag was off, or the head is not far),
      * a candidate could not be looked at (`unread`: no head size, no staff
        lines) -- it could be the owner, so nothing is concluded, or
      * both fit or neither does -- two answers both fit, or none: a tie is
        never broken by distance here (rule 8).

    A candidate the ledgers did not reach is refuted by an ABSTENTION row
    (`ledger_not_read`, `unread` False); the rows that fit are Observations.
    """
    rows = ev.rows(Q.FAR_HEAD_OWNER_LEDGER)
    refusals = ev.refusals(Q.FAR_HEAD_OWNER_LEDGER)
    if not rows and not refusals:
        return None
    if any((r.detail or {}).get("unread") for r in refusals):
        return None
    fitting = {}
    for r in rows:
        fitting[(r.detail or {}).get("candidate")] = r
    if len(fitting) != 1:
        return None
    owner, row = next(iter(fitting.items()))
    if owner is None:
        return None
    return owner, tuple(r.id for r in rows) + tuple(r.id for r in refusals), {
        "fits": {k: dict(position=v.value, how=(v.detail or {}).get("how"),
                         ledger_reason=(v.detail or {}).get("ledger_reason"))
                 for k, v in fitting.items()},
        "not_fitting": {
            (r.detail or {}).get("candidate"):
                (r.detail or {}).get("ledger_reason") for r in refusals}}



# ─────────────────────────────────────────────────────────────────────────────
# lane-owner-from-staves (Sean, 2026-10-06) -- OWNERSHIP STARTS FROM THE STAVES
# WE KNOW. A notehead lying ON or BETWEEN a known staff's five lines belongs to
# that staff: decided, no contest. Only a head in the GAP between two staves is
# contested and goes on to the ledger witness and the older tiers.
#
# WHY THIS WAS NOT ALREADY SO (measured on the 10-06 records, FINDINGS in
# `benchmarks/omr-local-staff-2026-09/`): `glyph_owner` is only ever asked about
# a head that has `Q.GLYPH_BAND_DISTANCE` rows -- a twin on another staff, or a
# far head walked against its OWN staff alone -- and it then SCORES: a complete
# ladder +4.0, a range veto -6.0, a hairpin +7.0, distance only as a tie-break
# (-0.5 per space; a head INSIDE a band has distance 0 and so no term at all).
# "Inside the band" was therefore never a tier: it was the absence of a penalty,
# and any of the other terms, or the note-first witness's own reading, could
# outvote it. And a head in B's band filed on A with no twin on B had no B
# candidate row, so B was never even asked about.
# ─────────────────────────────────────────────────────────────────────────────

#: `OMR_OWNER_FROM_STAVES` (DEFAULT ON since 2026-10-06, Sean) has ONE reader,
#: `owner_from_staves_enabled` in GATHER (ROADMAP 2.61b); this module imports
#: it and calls it at ADJUDICATE time.


#: ROADMAP 2.58d (lane-stem-owner) -- DEFAULT OFF until Sean has adjudicated
#: `out/print/stem_owner/`; an allow-list (CLAUDE.md §7), so a typo leaves it
#: off. Read at ADJUDICATE time. The GATHER row (`Q.HEAD_STEM_REACH`) is filed
#: either way: evidence is recorded, this flag only says whether it is read.
STEM_OWNER_ENV = "OMR_STEM_OWNER"


def stem_owner_enabled() -> bool:
    """DEFAULT ON since 2026-10-08 (Sean: "if they pass then implement them"). Deny-list."""
    return os.environ.get(STEM_OWNER_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


#: A stem "reaches" a staff when its tip stands within this many of THAT
#: staff's spaces of its outer line (or past it): INTO the lines, or ending in
#: the band a space either side of them.
STEM_REACH_BAND_SPACES = 1.0
#: The stem speaks only for a head that is CLEARLY outside every candidate's
#: five lines: its centre at least this many of that staff's spaces beyond the
#: staff's outer line (a head on the first ledger line stands at ~1.0). A head
#: on or between the lines, or in the first space, is `staff_band`'s; its stem
#: may point at the neighbour for reasons that have nothing to do with
#: ownership (a beamed group, a second voice), and the replay found ten such
#: heads on the first draft of this rule -- every one a head sitting ON an edge
#: line -- which the owner-from-staves control forbids to move.
STEM_MIN_OUTSIDE_SPACES = 0.9


def _stem_owner(ev: Evidence, cand_keys: Sequence[Optional[str]]):
    """ROADMAP 2.58d. The STEM witness: `(owner staff key, row ids, detail)`
    or `None` (silent).

    THE RULE (stated before any count; Sean, 2026-10-08: *"the stem should make
    it obvious"*; CLAUDE.md §10 stems: up -> right, down -> left, and the
    middle-line convention: a head far below its staff stems UP toward it, a
    head far above stems DOWN toward it):

      * the head's stem leaves it `down` or `up` (`Q.HEAD_STEM_REACH`; `both`
        and `none` are silent -- a barline, a hidden stem and a whole note are
        not an answer);
      * a candidate staff is POINTED AT when it lies on the stem's side of the
        head (its near edge beyond the head's centre in that direction) and
        the stem's tip stands in its band: at or past its outer line less
        `STEM_REACH_BAND_SPACES` of that staff's spaces;
      * exactly ONE candidate pointed at -> it owns the head. Toward neither
        or toward both -> silent.

    It does not decide against a ledger witness: `adjudicate_glyph_owner`
    abstains (`stem_disagrees`) where the two name different staves.
    """
    rows = ev.rows(Q.HEAD_STEM_REACH)
    if not rows:
        return None
    row = rows[-1]
    way = row.value
    if way not in ("down", "up"):
        return None
    det = row.detail or {}
    tip = det.get(f"{way}_tip_y")
    box = det.get("head_box_page")
    if tip is None or not box or len(box) != 4:
        return None
    cy = (float(box[1]) + float(box[3])) / 2.0
    sign = 1.0 if way == "down" else -1.0
    pointed, per, used = [], {}, [row.id]
    for k in cand_keys:
        if k is None:
            continue
        st = R.Subject.from_key(k)
        geo = staff_geometry(ev, st)
        if geo is None:
            continue
        ys, sp, ids = geo
        top, bot = min(ys), max(ys)
        if max(top - cy, cy - bot) < STEM_MIN_OUTSIDE_SPACES * sp:
            return None            # on, between or beside a staff's lines: not a far head
        near, far_edge = (top, bot) if sign > 0 else (bot, top)
        on_side = (near - cy) * sign >= 0.0
        reach = float(tip) * sign >= (near - sign * STEM_REACH_BAND_SPACES * sp) * sign
        per[k] = dict(on_the_stems_side=on_side, tip_reaches=bool(reach))
        if on_side and reach:
            pointed.append(k)
            used += list(ids)
    if len(pointed) != 1:
        return None
    return pointed[0], tuple(used), {
        "stem": {"direction": way, "tip_y": float(tip), "head_cy": cy,
                 "ext_spaces": det.get(f"{way}_ext"), "per_candidate": per}}


#: ROADMAP 2.59 (lane-dot-not-a-note, Sean 2026-10-07) -- DEFAULT OFF, so a
#: typo leaves it off (allow-list, CLAUDE.md §7). One switch for the three
#: dot rules: (a) a notehead-class box of dot size is refused as a dot, (b) a
#: dot belongs to the note immediately to its LEFT and so to THAT note's
#: owner (never to the strip that happened to box it), (c) a dot-sized box
#: sharing ink with a dot takes that dot's owner. Read at ADJUDICATE time.
DOT_FOLLOWS_NOTE_ENV = "OMR_DOT_FOLLOWS_NOTE"


def dot_follows_note_enabled() -> bool:
    """DEFAULT ON since 2026-10-07 (Sean: "switch it on"). Deny-list."""
    return os.environ.get(DOT_FOLLOWS_NOTE_ENV, "1").strip().lower() not in (
        "0", "", "false", "no", "off")


#: `gather.PAGE_EDGE_MARGIN_SPACES` (0.8, MEASURED: the page-wide position of a
#: head can sit up to 0.775 sp (Litolff) / 0.73 sp (Breitkopf) from its local
#: one). Where a head's position against a staff is known only from the
#: page-wide `Q.STAFF_LINES`, it counts as inside only this far INSIDE the
#: band; nearer an edge that reading is not evidence and the tier is silent.

#: a staff's x extent, plus this many spaces for a cell's pad, is "beside" it
STAFF_BESIDE_SLACK_SPACES = 2.0


def _staff_band(geo, skew_rows):
    """`(top, bottom, spacing, half_thickness_px, row ids)` of a staff in page
    pixels from its `staff_geometry` and its `Q.STAFF_SKEW` rows (read by the
    caller, at the staff, where they are filed); `None` -- DECLINED, never
    defaulted -- without geometry."""
    if geo is None:
        return None
    ys, sp, ids = geo
    th = 0.0
    if skew_rows:
        t = (skew_rows[-1].detail or {}).get("thickness_px")
        if isinstance(t, (list, tuple)):
            t = sorted(float(v) for v in t)[len(t) // 2] if t else None
        try:
            th = float(t) if t else 0.0
        except (TypeError, ValueError):
            th = 0.0
        ids = ids + [skew_rows[-1].id]
    return min(ys), max(ys), sp, th / 2.0, ids


def _head_page_box(ev: Evidence):
    """This head's own page box `(x0, y0, x1, y1)` and its row id, or `None`."""
    rows = ev.rows(Q.GLYPH_BOX)
    if not rows:
        return None
    bb = (rows[0].detail or {}).get("bbox_page_px")
    if not bb or len(bb) != 4:
        return None
    return tuple(float(v) for v in bb), rows[0].id


def _twin_on(ev: Evidence, staff: R.Subject, box):
    """The notehead box on `staff` that is the SAME ink as `box` -- the
    contest's own test (`gather.CONTEST_IOU`, strict) over the same bar's cell
    on that staff. `(glyph subject, row id, iou)` or `None`."""
    me = ev.subject
    cell = R.cell(me.page, me.system, staff.staff, me.cell)
    best = None
    for row in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                       subject=cell):
        v = row.value
        if not isinstance(v, (list, tuple)) or not v \
                or not str(v[0]).startswith("notehead"):
            continue
        bb = (row.detail or {}).get("bbox_page_px")
        if not bb or len(bb) != 4:
            continue
        iou = _iou(box, tuple(float(x) for x in bb))
        if iou > CONTEST_IOU and (best is None or iou > best[2]):
            best = (row.subject, row.id, iou)
    return best


def _holds(ev: Evidence, staff: R.Subject, box, cy: float, own: bool, band):
    """Does `staff`'s five-line band hold this head? `(True|False|None, how,
    row ids, detail)`; `None` = cannot tell (rule 8), never "no".

    The band is the top line to the bottom line plus half a line thickness
    (Sean, 2026-10-06). The head's centre is measured, in this order, by

      1. its OWN `Q.NOTEHEAD_STAFF_POSITION` against its own staff's local grid
         (`own`), or the SAME INK's position in the candidate's own cell (the
         twin's) -- both LOCAL, in that cell's own canonical frame (CLAUDE.md
         §10: measure against the staff locally);
      2. the page-wide lines, only where the head is at least
         `PAGE_EDGE_MARGIN_SPACES` inside the band -- nearer an edge the
         page-wide reading is silent, because a scanned staff wanders more
         than that."""
    if band is None:
        return None, "no_staff_geometry", (), {}
    top, bottom, sp, half_th, ids = band
    half = sp / 2.0
    tol = half_th / half if half else 0.0
    pos_rows = ev.rows(Q.NOTEHEAD_STAFF_POSITION) if own else ()
    how, pos, used = None, None, tuple(ids)
    if own and pos_rows:
        pos, how, used = float(pos_rows[-1].value), "local_own_cell", used + (pos_rows[-1].id,)
    elif not own:
        twin = _twin_on(ev, staff, box)
        if twin is not None:
            tp = ev.rows(Q.NOTEHEAD_STAFF_POSITION, subject=twin[0])
            if tp:
                pos, how = float(tp[-1].value), "local_twin_cell"
                used = used + (tp[-1].id, twin[1])
    if pos is None and not own:
        # GATHER's own measure of the head against THIS candidate's cell grid
        # at its x (flag ON): `local_position_in_candidate`, same unit
        for row in ev.rows(Q.GLYPH_BAND_DISTANCE):
            if (row.detail or {}).get("candidate") == staff.to_key() \
                    and (row.detail or {}).get("local_position_in_candidate") is not None:
                pos, how = float(row.detail["local_position_in_candidate"]), "local_candidate_grid"
                used = used + (row.id,)
                break
    if pos is not None:
        return (-tol <= pos <= 8.0 + tol), how, used, {"position": round(pos, 3)}
    # page-wide, with the measured margin
    m = PAGE_EDGE_MARGIN_SPACES * sp
    if top + m <= cy <= bottom - m:
        return True, "page_wide_margin", used, {
            "inside_by_spaces": round(min(cy - top, bottom - cy) / sp, 3)}
    if cy < top - m or cy > bottom + m:
        return False, "page_wide_margin", used, {}
    return None, "page_wide_edge", used, {}


def _owner_from_staves(ev: Evidence):
    """Ruling for a head lying in a known staff's band, or `None` where it
    does not (the gap, an edge the page-wide lines cannot settle, two staves
    claiming it): then the older tiers run as before."""
    hb = _head_page_box(ev)
    if hb is None:
        return None
    box, box_id = hb
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    me = ev.subject
    own_staff = me.at(Kind.STAFF)
    holders, undecided, used, per = [], [], [box_id], {}
    for st in ev.subjects(Kind.STAFF):
        if st.page != me.page or st.system != me.system:
            continue
        ext = ev.rows(Q.STAFF_EXTENT, subject=st)
        geo = staff_geometry(ev, st)
        if not ext or geo is None:
            continue
        x0, x1 = float(ext[-1].value[0]), float(ext[-1].value[1])
        slack = STAFF_BESIDE_SLACK_SPACES * geo[1]
        if not (x0 - slack <= cx <= x1 + slack):
            continue
        band = _staff_band(geo, ev.rows(Q.STAFF_SKEW, subject=st))
        ok, how, ids, det = _holds(ev, st, box, cy, st.to_key() == own_staff.to_key(), band)
        per[st.to_key()] = dict(holds=ok, how=how, **det)
        if ok:
            holders.append(st)
            used += list(ids)
        elif ok is None:
            undecided.append(st)
    # exactly one staff holds the head and no other staff is undecided about it
    if len(holders) != 1 or undecided:
        return None
    owner = holders[0]
    detail = {"staff_band": per, "measured": per[owner.to_key()]["how"]}
    if owner.to_key() == own_staff.to_key():
        return Ruling(value=owner.to_key(), reason="staff_band",
                      used=tuple(used), detail=detail)
    # ⚠️ A COPY OF THE SAME HEAD found by a NEIGHBOUR's padded cell (Sean,
    # 2026-10-06). If the owning staff has its own box of this ink the copy is a
    # duplicate and EXPORT drops it (`owned_by_another_staff`); if it has none,
    # the head is NAMED here (`staff_band_no_box`) and no box is invented --
    # relocation is Sean's call, never this tier's.
    twin = _twin_on(ev, owner, box)
    detail["owner_box"] = twin[0].to_key() if twin else None
    return Ruling(value=owner.to_key(),
                  reason="staff_band" if twin else "staff_band_no_box",
                  used=tuple(used), detail=detail)


@decision(
    quantity=Q.GLYPH_OWNER,
    checkable=Checkable.MIXED,
    checked_by=(
        "a spurious or missing notehead breaks the OWNING bar's duration sum -- so rhythm_sum_warning's group includes OWNERSHIP, not only duration and meter",
        "the owned glyph's implied pitch must fall in the owner's written range",
    ),
    implicates=(Q.GLYPH_OWNER, Q.DURATION, Q.METER, Q.INSTRUMENT),
    # ⚠️ ROADMAP 2.14. `Q.LEDGER_IS_NOT_A_LEDGER` joins the composition: the
    # ladder tier's reliability now depends on a rung's own refusal verdict,
    # not only on GATHER's anonymous count.
    # ⚠️ ROADMAP 2.6c adds `Q.GLYPH_BOX` (this glyph's own page box) and
    # `Q.WEDGE_BOX`/`Q.STAFF_LINES` (a candidate's hairpins and staff lines,
    # both read off ITS subject) for the hairpin-separator term.
    # ⚠️ ROADMAP 2.6c (second half) adds `Q.STAFF_SPACING`: the ledger walk
    # (`ladder_side`) steps one staff space at a time off each candidate's
    # own outer line, and the `ledgerLine` boxes it walks are `Q.GLYPH_BOX`
    # rows of the head's cell and each candidate's same-index cell.
    # ⚠️ ROADMAP 2.6d adds `Q.LEDGER_RUNG_INK`: a SECOND reader of the same
    # ladder, for a step the detector drew no `ledgerLine` box on
    # (`cv_rungs`).
    # ⚠️ ROADMAP 2.37 (Sean's redirect) adds `Q.LEDGER_OWNER_DENSITY`: the
    # RELATIVE ownership witness (`_ledger_owner_comparison`), read BEFORE
    # the completeness-based `ledger_direction` -- see that function's own
    # note on how the two combine.
    composed_from=(Q.GLYPH_BAND_DISTANCE, Q.GLYPH_LADDER, Q.INSTRUMENT, Q.CLEF,
                   Q.HUMAN_BOX_VERDICT, Q.LEDGER_IS_NOT_A_LEDGER, Q.GLYPH_BOX,
                   Q.WEDGE_BOX, Q.STAFF_LINES, Q.STAFF_SPACING,
                   Q.LEDGER_RUNG_INK, Q.LEDGER_OWNER_DENSITY,
                   Q.FAR_HEAD_OWNER_LEDGER, Q.STAFF_EXTENT, Q.STAFF_SKEW,
                   Q.HEAD_STEM_REACH),
    scope=Kind.GLYPH,
    # ⚠️ ROADMAP 2.56b adds `Q.FAR_HEAD_OWNER_LEDGER`: the note-first ledger
    # look toward each candidate staff, read AHEAD of distance and of the older
    # ladder tiers (`_note_first_ledger_owner`).
    wants=(Q.GLYPH_LADDER, Q.GLYPH_BAND_DISTANCE, Q.GLYPH_CONF,
           Q.NOTEHEAD_STAFF_POSITION, Q.INSTRUMENT, Q.CLEF,
           Q.HUMAN_BOX_VERDICT, Q.LEDGER_IS_NOT_A_LEDGER, Q.GLYPH_BOX,
           Q.WEDGE_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.LEDGER_RUNG_INK,
           Q.LEDGER_OWNER_DENSITY, Q.FAR_HEAD_OWNER_LEDGER, Q.STAFF_EXTENT,
           Q.STAFF_SKEW, Q.HEAD_STEM_REACH),
    reasons=("human_owner", "staff_band", "staff_band_no_box",
             "ledger_note_first", "ledger_owner_density", "ledger_witnesses_disagree",
             "stem_toward_staff", "stem_disagrees",
             "ledger_direction", "ledger_refuted", "hairpin_separates",
             "far_no_rungs", "ledger_all_refuted", "ladder", "range_veto",
             "distance", "no_contest", "no_evidence", "tied"),
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
    # ⚠️⚠️ ROADMAP 3.4c, AND IT IS FIRST — BEFORE THE CONTEST IS EVEN READ.
    # Ladder, range and distance are three ways of GUESSING which staff a
    # piece of ink stands on; a human read the plate. Putting this test after
    # the contest would make his answer a fourth term beside three that are
    # assumed weights (A-OWN-1, none of them measured), which is exactly the
    # inversion `notehead_precision._human_not_a_symbol` refuses one file
    # along.
    human = _human_owner(ev)
    if human is not None:
        row, owner = human
        return Ruling(value=owner, reason="human_owner", used=(row.id,),
                      detail={"human_reader": row.reader,
                              "human_row": row.id,
                              "human_says": row.value,
                              # ⚠️ REPORTED, NEVER REPAIRED. CLAUDE.md §10: a
                              # resolved contest DROPS the loser and never
                              # relocates it, so if the staff he named holds
                              # no box of this ink, this refuses the note HERE
                              # and adds none THERE. `ingest` measured whether
                              # the twin exists; the answer travels on his row.
                              "twin_on_the_named_staff":
                                  (row.detail or {}).get(
                                      "twin_on_the_named_staff"),
                              **{k: (row.detail or {})[k]
                                 for k in ("sidecar", "review_action", "note")
                                 if k in (row.detail or {})}})

    bands = ev.rows(Q.GLYPH_BAND_DISTANCE)
    if not bands:
        # Uncontested: the glyph belongs to the staff whose cell it was cut
        # from, and there is nothing to arbitrate.
        own = ev.subject.at(Kind.STAFF)
        return Ruling(value=own.to_key(), reason="no_contest")

    # ⚠️⚠️ lane-owner-from-staves (Sean, 2026-10-06), AHEAD OF EVERY LEDGER
    # TIER. A head ON or BETWEEN a known staff's five lines belongs to that
    # staff -- decided, no contest. Only a head in the GAP goes on. Default OFF.
    if owner_from_staves_enabled():
        banded = _owner_from_staves(ev)
        if banded is not None:
            return banded

    ladders = {r.detail.get("candidate"): r for r in ev.rows(Q.GLYPH_LADDER)}

    # ⚠️⚠️ ROADMAP 2.56b, AHEAD OF EVERY OLDER LEDGER TIER AND OF DISTANCE.
    # Sean (2026-09-28): the ledger lines name the owner and are
    # authoritative; nearness never overrides them. The note-first look reads
    # the NOTE'S OWN line and counts the ledgers from it to each candidate's
    # edge, so it needs no complete walk from the staff outward. A resolved
    # contest DROPS the loser (the exporter refuses the copy), it never
    # relocates it.
    # ⚠️ ROADMAP 2.58d, THE STEM WITNESS (read here, applied below). Where it
    # and a ledger witness name DIFFERENT staves the head ABSTAINS
    # (`stem_disagrees`) -- neither is trusted alone, rule 8 -- and the
    # group rule (`reconcile_group_owners`) takes the owner from the copy that
    # did not abstain.
    stem = None
    if stem_owner_enabled():
        stem = _stem_owner(ev, [r.detail.get("candidate") for r in bands])

    def _stem_clash(owner):
        return Ruling.abstain("stem_disagrees",
                              stem_owner=stem[0], ledger_owner=owner,
                              **stem[2])

    nf = _note_first_ledger_owner(ev)
    if nf is not None:
        owner, used, detail = nf
        if stem is not None and stem[0] != owner:
            return _stem_clash(owner)
        return Ruling(value=owner, reason="ledger_note_first", used=used,
                      detail={"ledger_note_first": detail,
                              **({"stem_agrees": True} if stem is not None else {})})

    # ⚠️⚠️ ROADMAP 2.37 (Sean's redirect, 2026-09-29, quoted): pitch is
    # already geometric and never reads a ledger; the ledger reader is
    # needed ONLY for OWNERSHIP, and for that one RELATIVE comparison
    # (which candidate has more ink at the ONE informative rung position)
    # is enough -- self-calibrating per plate, never an absolute floor
    # read against every rung. Asked FIRST: the detector-based ladder
    # (`ledger_direction`, below) is kept as a CORROBORATING witness --
    # where it also has an opinion and DISAGREES, that is not evidence
    # either way and this glyph declines outright, rather than trusting
    # either witness alone.
    ledger = _contest_ledger_reading(ev, bands, ladders)
    density = _ledger_owner_comparison(
        ev, [r.detail.get("candidate") for r in bands])
    if density is not None:
        winner, detail = density
        if (ledger is not None and ledger.winner is not None
                and ledger.winner != winner):
            return Ruling.abstain("ledger_witnesses_disagree",
                                  ledger_owner_density=detail,
                                  ledger=ledger.summary())
        if stem is not None and stem[0] != winner:
            return _stem_clash(winner)
        return Ruling(value=winner, reason="ledger_owner_density",
                      used=tuple(r.id for r in bands),
                      detail={"ledger_owner_density": detail})
    if ledger is not None and ledger.winner is not None:
        # ⚠️ ROADMAP 2.37: an ELIMINATED winner (every rival's ladder
        # cleanly refuted, never merely broken) is named apart from a
        # completeness-decided one -- the two are different evidence and
        # `trace`/a count must be able to tell them apart.
        reason = ("ledger_refuted" if ledger.word == "ledger_refuted"
                  else "ledger_direction")
        if stem is not None and stem[0] != ledger.winner:
            return _stem_clash(ledger.winner)
        return Ruling(value=ledger.winner, reason=reason,
                      used=tuple(r.id for r in bands) + ledger.row_ids,
                      detail={"ledger": ledger.summary()})

    # ⚠️ ROADMAP 2.6c, this glyph's own PAGE box. `Q.GLYPH_BAND_DISTANCE`
    # carries only the CANDIDATE-relative position (`position_in_candidate`),
    # never a page coordinate, so the hairpin term -- which compares this
    # head against a candidate's hairpins in the SAME page frame -- needs its
    # own read of `Q.GLYPH_BOX`, the one row that carries `y_center_page`.
    head_box = _own_glyph_box(ev)
    head_y = head_box.get("y_center_page") if head_box else None

    scored = []
    hairpins = 0
    ladder_discounts: Dict[str, Tuple[str, ...]] = {}
    for row in bands:
        cand_key = row.detail.get("candidate")
        if cand_key is None:
            continue
        terms = []

        # ── tier 0: a hairpin under this staff (2.6c, additive) ─────────────
        # ⚠️ KEPT ADDITIVE, NOT A GATE (FINDINGS §2.6c.2): it can no longer
        # override a ledger answer (that returned above), its 7.0 beats a
        # lone range veto and any distance, and the one mix that outvotes it
        # -- a veto on its side PLUS a rival's genuinely complete ladder --
        # pits it against ledger evidence no crop has adjudicated.
        hairpin = _hairpin_separates(ev, cand_key, head_y)
        if hairpin is not None:
            terms.append(hairpin)
            hairpins += 1

        # ── tier 1: the ledger ladder ───────────────────────────────────────
        lad = ladders.get(cand_key)
        if lad is not None:
            complete, discounted = _ladder_complete(ev, lad)
            if discounted:
                ladder_discounts[cand_key] = discounted
            if complete:
                terms.append(Term("ladder_complete", W_LADDER_COMPLETE,
                                  (lad.id,)))
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

    # ⚠️ ROADMAP 2.58d, THE STEM WHERE NO LEDGER WITNESS DECIDED. It stands in
    # for the three places the sum below ends on NOTHING a witness decided --
    # `far_no_rungs`, `ledger_all_refuted`, `tied` -- and for `distance`, which
    # is the tie-break and nothing more (`distance` is "before" it, the brief's
    # words). It never overrules a hairpin or a complete ladder: where the sum
    # was decided by one of those and the stem names the OTHER staff, the head
    # abstains (`stem_disagrees`). A candidate the written range calls
    # IMPOSSIBLE cannot be named by a stem: the stem is then SILENT (`None`) and
    # the sum stands as it did -- the first draft abstained here and turned 185
    # decided Litolff heads into unread ones.
    def _stem_ruling():
        owner, used, detail = stem
        if any(t.name == "range_impossible"
               for _s, k, ts, _d2 in scored if k == owner for t in ts):
            return None
        return Ruling(value=owner, reason="stem_toward_staff",
                      used=tuple(r.id for r in bands) + used, detail=detail)

    # ⚠️⚠️ ROADMAP 2.6c (second half): A FAR NOTE WITH NO RUNGS EITHER WAY IS
    # A READING GAP, NOT A DISTANCE TIE-BREAK (Sean, 2026-09-28). Every
    # candidate needs `FAR_MIN_RUNGS` or more and not one rung was found
    # toward any: the ladder that would name the owner was not read, and
    # nearness may not stand in for it. A hairpin is a witness of its own
    # and still speaks. EXPORT counts the head `owner_not_read`
    # (`OWNER_NOT_READ_REASONS`) and never writes it at a guess.
    if ledger is not None and ledger.word == "far_no_rungs" and not hairpins:
        if stem is not None and _stem_ruling() is not None:
            return _stem_ruling()
        return Ruling.abstain("far_no_rungs", ledger=ledger.summary())

    # ⚠️ ROADMAP 2.37 (Sean, 2026-09-29): every candidate this glyph could
    # belong to had its ladder CLEANLY refuted (not merely unread) -- a
    # READER FAILURE (a missed rung, a misread head, or a note that is not
    # really this far), never a legitimate "no ledger printed" gap. Kept
    # apart from `far_no_rungs` in `OWNER_NOT_READ_REASONS` so the count
    # never conflates the two.
    if ledger is not None and ledger.word == "ledger_all_refuted" \
            and not hairpins:
        if stem is not None and _stem_ruling() is not None:
            return _stem_ruling()
        return Ruling.abstain("ledger_all_refuted", ledger=ledger.summary())

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
        if stem is not None and _stem_ruling() is not None:
            return _stem_ruling()
        return Ruling.abstain("tied")

    # ⚠️ ROADMAP 2.6c: checked FIRST because it can carry a contest a
    # genuinely complete ladder's own +4.0 cannot (`W_LADDER_COMPLETE` alone
    # does not outweigh a range veto's -6.0).
    if any(t.name == "hairpin_separates" for t in top_terms):
        reason = "hairpin_separates"
    elif any(t.name == "ladder_complete" for t in top_terms):
        reason = "ladder"
    elif vetoed and by_distance[1] != top_key:
        reason = "range_veto"
    else:
        reason = "distance"

    stem_says = _stem_ruling() if stem is not None else None   # None: silent or vetoed
    if stem_says is not None:
        if reason == "distance":
            return stem_says
        if stem[0] != top_key:
            return Ruling.abstain("stem_disagrees", stem_owner=stem[0],
                                  against=reason, **stem[2])

    detail = {"scores": {k: sc for sc, k, _t, _d2 in scored},
              "would_win_on_distance": by_distance[1]}
    if ledger is not None:
        # ⚠️ FOR `trace`: what the rungs said where they did not decide.
        detail["ledger"] = ledger.summary()
    if ladder_discounts:
        # ⚠️ ROADMAP 2.14, FOR `trace`. Per candidate, the rung glyph keys a
        # refused `Q.LEDGER_IS_NOT_A_LEDGER` verdict removed from this
        # contest's ladder count -- present whether or not that candidate
        # won, so a losing candidate's discount is visible too.
        detail["ladder_discounted_rungs"] = ladder_discounts

    return Ruling(value=top_key, reason=reason,
                  margin=(top_score - runner) if runner is not None else None,
                  used=tuple(r.id for r in bands),
                  detail=detail)


def _ladder_complete(ev: Evidence, lad_row) -> Tuple[bool, Tuple[str, ...]]:
    """`(is the ladder complete, the named rungs a refusal discounted)`.

    ⚠️⚠️ ROADMAP 2.14 — THE JOIN `adjudicate_ledger_is_not_a_ledger`'s OWN
    DOCSTRING SAYS DOES NOT EXIST, BUILT. `gather._observe_ladder` now names,
    in `detail["rungs"]`, the ledger glyph subject that matched each counted
    step, in the same order `found` was counted — so a rung's OWN refusal
    verdict can be read back and discounted from THIS contest's completeness,
    which GATHER's anonymous `found`/`expected` count never allowed.

    A named rung whose `Q.LEDGER_IS_NOT_A_LEDGER` verdict is DECIDED `True`
    (refused — a staff-line fragment, a barline, ink with no boxed head) no
    longer counts. One the ledger decision ABSTAINED on (`rung_without_
    boxed_head` — CLAUDE.md rule 8, *cannot tell* may never become *not a
    rung*), one it never ran on at all, or one it DECIDED `False` (a real
    rung) all keep their place.

    ⚠️ NO CYCLE: `adjudicate_ledger_is_not_a_ledger` runs BEFORE `glyph_owner`
    in `adjudicate.ORDER`, and its own declared evidence is `Q.GLYPH_BOX`,
    `Q.STAFF_LINES`, `Q.STAFF_SPACING`, `Q.CELL_STAFF_SPACE`,
    `Q.HUMAN_BOX_VERDICT`, `Q.GLYPH_BAND_DISTANCE` and `Q.LEDGER_INK_UNDER` —
    `Q.GLYPH_OWNER` is nowhere in its ancestry, so reading its verdict back
    here closes nothing.

    ⚠️ AN OLD RECORD (no `rungs` named, pre-2.14) IS UNCHANGED: falls back to
    the row's own `value`, exactly as `glyph_owner` read it before this lane.
    An EMPTY `rungs` list (a genuinely named ladder with `found == 0`) has
    nothing to discount either, so it takes the same path.
    """
    detail = lad_row.detail or {}
    names = detail.get("rungs")
    expected = detail.get("expected")
    if not names or not isinstance(expected, int):
        return bool(lad_row.value), ()

    kept = 0
    discounted: List[str] = []
    for key in names:
        try:
            subject = R.Subject.from_key(key)
        except ValueError:
            kept += 1                # cannot even ask -- never guess a refusal
            continue
        verdict = ev.verdict(Q.LEDGER_IS_NOT_A_LEDGER, subject=subject)
        if verdict is not None and verdict.outcome == Outcome.DECIDED \
                and verdict.value is True:
            discounted.append(key)
            continue
        kept += 1
    return kept == expected, tuple(discounted)


@dataclass(frozen=True)
class Rung:
    """One `ledgerLine` box in PAGE pixels, with its 3.4g-2 verdict.

    `refused` is the refusal REASON where `ledger_is_not_a_ledger` DECIDED
    `True` (a staff-line fragment, a barline...), else `None` -- an
    ABSTAINED verdict, or none at all, keeps the rung (CLAUDE.md rule 8:
    *cannot tell* may never become *not a rung*)."""
    key: str
    x0: float
    x1: float
    y: float
    refused: Optional[str] = None
    row_id: str = ""
    #: ROADMAP 2.6d. `"detector"` (a boxed `ledgerLine`, `Q.GLYPH_BOX`) or
    #: `"cv_ink"` (`Q.LEDGER_RUNG_INK`, a step the detector never boxed) --
    #: two readers of the SAME fact, named so `trace` can say which one
    #: spoke for a step.
    source: str = "detector"


@dataclass(frozen=True)
class LadderSide:
    """What the rungs say about ONE candidate staff.

    `frame` is `page` when read off geometry, `count` when only GATHER's
    anonymous `Q.GLYPH_LADDER` count was available (an old record, or a
    fixture with no page box) -- then the own line cannot be told apart and
    only a COMPLETE ladder points, exactly the pre-2.6c `ladder_complete`."""
    staff: str
    expected: int
    found: int                          # kept rungs matched, own line included
    toward: Tuple[str, ...] = ()        # found rungs that are NOT the own line
    n_toward: int = 0
    stands_on: Optional[str] = None     # the rung the head stands on
    reach: bool = True
    #: spaces from the head to the outermost rung found (or the staff's outer
    #: line if none): what `reach` thresholds, kept for `trace`
    reach_spaces: Optional[float] = None
    refused: Tuple[Tuple[str, int], ...] = ()
    frame: str = "page"
    row_ids: Tuple[str, ...] = ()
    #: ROADMAP 2.6d. `{rung key: "detector" | "cv_ink"}` for every rung
    #: counted TOWARD this side (never the own line) -- so `trace` can say
    #: which reader named a step that decided a contest.
    sources: Tuple[Tuple[str, str], ...] = ()
    #: ROADMAP 2.6f. This side's own staff spacing and the head's own line's
    #: Y (page pixels), carried so a DIFFERENT side can ask "is this rung an
    #: integer number of MY spaces beyond MY own line" without re-querying
    #: geometry -- `None` unless `frame == "page"`.
    spacing: Optional[float] = None
    anchor_y: Optional[float] = None
    #: ROADMAP 2.6f. `(rung key, y)` for every `toward` rung (own line
    #: excluded), so a cross-candidate check can ask the same question
    #: without redoing the walk.
    toward_ys: Tuple[Tuple[str, float], ...] = ()
    #: ROADMAP 2.6f. `toward` rungs this side's SECOND walk excluded because
    #: another candidate's own-line explains them more precisely (`trace`).
    discounted: Tuple[str, ...] = ()

    @property
    def missing(self) -> int:
        return max(0, self.expected - self.found)

    @property
    def points(self) -> bool:
        """Do the ledger lines join the note to THIS staff?

        A note needing no rung at all (within 0.75 spaces of the band) is
        joined by nearness the convention does not dispute. Otherwise: at
        least one rung that is not the note's own line, no more than
        `LADDER_MAX_MISSING` missing, and the ladder ENDS at the note."""
        if self.expected <= 0:
            return True
        return (self.n_toward >= 1 and self.missing <= LADDER_MAX_MISSING
                and self.reach)

    def summary(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "expected": self.expected, "found": self.found,
            "toward": self.n_toward, "missing": self.missing,
            "reach": self.reach, "points": self.points, "frame": self.frame}
        if self.reach_spaces is not None:
            out["reach_spaces"] = round(self.reach_spaces, 3)
        if self.stands_on:
            out["stands_on"] = self.stands_on
        if self.refused:
            out["refused"] = dict(self.refused)
        if self.sources:
            out["sources"] = dict(self.sources)
        if self.discounted:
            out["discounted_own_structure"] = list(self.discounted)
        return out


@dataclass(frozen=True)
class LedgerReading:
    """`ledger_direction`'s answer: a `winner` staff key, or `None` with
    `word` saying why -- `silent` (not evidence either way) or
    `far_no_rungs` (every candidate far, no rung toward any: a reading gap)."""
    winner: Optional[str]
    word: str
    sides: Tuple[LadderSide, ...]

    def summary(self) -> Dict[str, Any]:
        return {"winner": self.winner, "word": self.word,
                "sides": {s.staff: s.summary() for s in self.sides}}

    @property
    def row_ids(self) -> Tuple[str, ...]:
        return tuple(dict.fromkeys(i for s in self.sides for i in s.row_ids))


def ladder_side(staff: str, head_y: float, head_x0: float, head_x1: float,
                line_ys: Sequence[float], spacing: float,
                rungs: Iterable[Rung],
                excluded_keys: FrozenSet[str] = frozenset()) -> LadderSide:
    """Walk the ladder from `staff`'s outer line toward the head, one step
    per staff space, exactly as `gather._observe_ladder` does (same
    `LEDGER_ROUND_UP`, same half-space grid tolerance, same x-overlap test)
    -- but on NAMED, verdict-carrying rungs, so it can say which rung is the
    head's own line and whether the ladder reaches it.

    ⚠️ ONE RUNG PER STEP, NEAREST FIRST, KEPT BEFORE REFUSED. A refused box
    at a step is reported (`refused`) and never counted; a physical rung
    boxed in two cells is two boxes at one step and counts once.

    `excluded_keys` (ROADMAP 2.6f, `ladder_sides_with_discount`'s second
    pass): rungs dropped from the pool entirely, as if the detector never
    drew them -- a full re-walk, so `missing`/`reach`/`reach_spaces` all
    recompute honestly rather than being patched after the fact.
    """
    ys = [float(v) for v in line_ys]
    sp = float(spacing)
    top, bottom = min(ys), max(ys)
    if top <= head_y <= bottom:
        return LadderSide(staff=staff, expected=0, found=0)
    above = head_y < top
    edge = top if above else bottom
    gap = (edge - head_y) if above else (head_y - edge)
    expected = int(gap / sp + LEDGER_ROUND_UP)
    if expected <= 0:
        return LadderSide(staff=staff, expected=0, found=0)
    tol = RUNG_GRID_TOLERANCE_SPACES * sp
    pool = [r for r in rungs if r.x0 <= head_x1 and r.x1 >= head_x0
            and r.key not in excluded_keys]
    used: set = set()
    found: List[Rung] = []
    refused: Counter = Counter()
    outer = edge
    for k in range(1, expected + 1):
        want = edge - k * sp if above else edge + k * sp
        here = [r for r in pool
                if r.key not in used and abs(r.y - want) <= tol]
        if not here:
            continue
        kept = [r for r in here if r.refused is None]
        if kept:
            best = min(kept, key=lambda r: abs(r.y - want))
            # the same physical rung boxed in another cell is the same rung
            used.update(x.key for x in here if abs(x.y - best.y) <= tol / 2)
            found.append(best)
            outer = best.y
        else:
            for r in here:
                used.add(r.key)
                refused[str(r.refused)] += 1
    own = next((r for r in found
                if abs(r.y - head_y) <= OWN_LINE_MAX_SPACES * sp), None)
    toward = tuple(r.key for r in found if r is not own)
    sources = tuple((r.key, r.source) for r in found if r is not own)
    discounted = tuple(k for k in excluded_keys
                       if any(r.key == k for r in rungs))
    return LadderSide(
        staff=staff, expected=expected, found=len(found), toward=toward,
        n_toward=len(toward), stands_on=own.key if own else None,
        reach=abs(head_y - outer) / sp < LADDER_REACH_SPACES,
        reach_spaces=abs(head_y - outer) / sp,
        refused=tuple(sorted(refused.items())),
        row_ids=tuple(r.row_id for r in found if r.row_id),
        sources=sources, spacing=sp, anchor_y=(own.y if own else None),
        toward_ys=tuple((r.key, r.y) for r in found if r is not own),
        discounted=discounted)


def ladder_side_from_count(staff: str, expected: int, found: int,
                           row_ids: Tuple[str, ...] = ()) -> LadderSide:
    """GATHER's anonymous count, where no geometry can be read. The own line
    cannot be told apart, so only a COMPLETE ladder points (`reach` is
    completeness) -- 2.6c's first-half `clean` reading, unchanged."""
    expected = max(0, int(expected))
    found = max(0, min(int(found), expected))
    return LadderSide(staff=staff, expected=expected, found=found,
                      n_toward=found, reach=(found >= expected),
                      frame="count", row_ids=row_ids)


def _shared_own_structure_exclusions(
        sides: Sequence[LadderSide]) -> Dict[str, FrozenSet[str]]:
    """ROADMAP 2.6f. Per candidate STAFF, which of its OWN `toward` rung
    keys are better read as a DIFFERENT candidate's own ledger structure --
    within `OWN_STRUCTURE_TOLERANCE_SPACES` of an INTEGER number of that
    other candidate's own staff-spaces beyond ITS `anchor_y`.

    Never checked against a side's own `anchor_y` (only `other.staff !=
    s.staff`): a candidate that genuinely needs two rungs for THIS note
    keeps both -- this is the exclusion set `ladder_sides_with_discount`
    re-walks with, not a verdict on its own.

    ⚠️ ONLY where `s` is not ALREADY complete (`s.missing >= 1`). Litolff
    #14 (`test_staged_ledger_direction.py`, positive control) is the
    falsifying case this guard exists for: staff/12/0/11's ladder is
    COMPLETE (3 of 3, tight residuals) and its OWN outermost rung happens
    to sit within 0.08 px of staff/12/0/10's own-line -- without this
    guard the discount fires on staff/12/0/11's genuine 2nd/3rd rungs and
    breaks a real far note. All seven §2.6c.3 candidates this lane fixes
    have `missing == 1` (never 0) at the point of discount, so the guard
    costs the fix nothing.
    """
    out: Dict[str, set] = {}
    for s in sides:
        if s.spacing is None or s.missing < 1:
            continue
        for key, y in s.toward_ys:
            for other in sides:
                if other.staff == s.staff or other.anchor_y is None \
                        or other.spacing is None:
                    continue
                steps = abs(y - other.anchor_y) / other.spacing
                k = round(steps)
                if k < 1:
                    continue
                if abs(steps - k) <= OWN_STRUCTURE_TOLERANCE_SPACES:
                    out.setdefault(s.staff, set()).add(key)
                    break
    return {staff: frozenset(keys) for staff, keys in out.items()}


#: One build spec per candidate: the exact positional args `ladder_side`
#: takes, before its trailing `excluded_keys`.
LadderSpec = Tuple[str, float, float, float, Sequence[float], float,
                   Sequence[Rung]]


def ladder_sides_with_discount(specs: Sequence[LadderSpec]
                               ) -> Tuple[LadderSide, ...]:
    """Build one `LadderSide` per spec (`ladder_side(*spec)`), then re-walk
    any side whose `toward` rung is §2.6f's shared-structure shape, with
    that rung excluded.

    `glyph_owner` and 2.7b's `belongs_to_a_nearer_staff` both call this
    instead of `ladder_side` directly -- the SAME two-pass discount, so the
    two decisions cannot discount a rung differently (the property 2.6c
    itself was built to hold, ROADMAP 2.6c.2/§4c)."""
    sides = tuple(ladder_side(*spec) for spec in specs)
    excluded = _shared_own_structure_exclusions(sides)
    if not excluded:
        return sides
    rebuilt = []
    for spec, side in zip(specs, sides):
        keys = excluded.get(spec[0])
        if not keys:
            rebuilt.append(side)
            continue
        # ⚠️ ROADMAP 2.6f: the SAME physical rung is routinely boxed TWICE --
        # once per cell the pad reaches (`cell_rungs`'s own precedent) -- and
        # the first walk's own dedup (`ladder_side`'s `used.update`, radius
        # `tol / 2`) only picks ONE of the two as `best` to report. Excluding
        # only that reported key leaves its physical twin, under a different
        # subject id, still in the pool for the second walk to re-find at
        # the SAME step -- widen the exclusion to every rung within the same
        # dedup radius of each discounted rung's Y, not only its own key.
        y_by_key = dict(side.toward_ys)
        spacing = spec[5]
        dedup_tol = RUNG_GRID_TOLERANCE_SPACES / 2.0 * spacing
        full = set(keys)
        for key in keys:
            y = y_by_key.get(key)
            if y is None:
                continue
            full.update(r.key for r in spec[6] if abs(r.y - y) <= dedup_tol)
        rebuilt.append(ladder_side(*spec, excluded_keys=frozenset(full)))
    return tuple(rebuilt)


def ledger_direction(sides: Sequence[LadderSide],
                     refuted: Optional[Dict[str, bool]] = None
                     ) -> LedgerReading:
    """Sean's convention (DECISIONS 2026-09-28): the ledger lines name the
    owner -- *rungs toward one staff, none toward the other*.

    `winner` is the ONE side the ledger lines join the note to, when no
    other side's do. Two sides both joined (a vacuous near staff and a
    complete ladder from the far one, say) is not evidence either way:
    `silent`, and the caller's own tiers decide. Every side FAR
    (`FAR_MIN_RUNGS`) with no rung toward any: `far_no_rungs`, a reading
    gap the caller must not paper over with distance.

    `refuted` (ROADMAP 2.37, Sean 2026-09-29, optional -- `None` reproduces
    every caller from before this parameter existed, byte for byte):
    `{staff: is this side REFUTED}`, from `_ink_refutes_side`. Asked only
    where completeness left the reading unresolved (never overrides
    `points`, which a refuted side can never itself satisfy -- see that
    function's own note): where it eliminates every side but one, that
    side FOLLOWS (`ledger_refuted`, a DECIDED winner, not a guess); where
    it eliminates every side, that is a READER FAILURE, not a legitimate
    gap (`ledger_all_refuted`) -- kept apart from `far_no_rungs` so the two
    are never confused in a count."""
    sides = tuple(sides)
    if len(sides) < 2:
        return _eliminate(sides, refuted, LedgerReading(None, "silent", sides))
    pointing = [s for s in sides if s.points]
    if len(pointing) == 1:
        return LedgerReading(pointing[0].staff, "points", sides)
    if (not pointing and all(s.expected >= FAR_MIN_RUNGS for s in sides)
            and all(s.n_toward == 0 for s in sides)):
        return _eliminate(sides, refuted,
                          LedgerReading(None, "far_no_rungs", sides))
    return _eliminate(sides, refuted, LedgerReading(None, "silent", sides))


def _eliminate(sides: Sequence[LadderSide], refuted: Optional[Dict[str, bool]],
              fallback: LedgerReading) -> LedgerReading:
    """ROADMAP 2.37. `fallback` unless `refuted` narrows the field to
    exactly one survivor (decide it) or none (abstain, a reader failure) --
    see `ledger_direction`'s own note for the two new words. A side with
    `expected == 0` needs no rung at all and cannot be tested either way
    (and would already have satisfied `points` above, so it never reaches
    here with company still undecided); it is left out of the count."""
    if not refuted:
        return fallback
    testable = [s for s in sides if s.expected >= 1]
    if not testable:
        return fallback
    survivors = [s for s in testable if not refuted.get(s.staff, False)]
    if len(testable) == 1:
        # No rival at all (ROADMAP 2.37's own-staff-only walk). Refuted:
        # a reader failure with nothing else to decide TO. Not refuted:
        # nothing new to say -- the caller's ordinary (no-contest) scoring
        # already decides this the way it always has.
        return (LedgerReading(None, "ledger_all_refuted", sides)
                if not survivors else fallback)
    if len(survivors) == 1:
        return LedgerReading(survivors[0].staff, "ledger_refuted", sides)
    if not survivors:
        return LedgerReading(None, "ledger_all_refuted", sides)
    return fallback


def cell_rungs(ev: Evidence, cells: Iterable[R.Subject],
               extra_keys: Iterable[str] = ()) -> List[Rung]:
    """Every `ledgerLine` box with a PAGE frame in `cells` (and at the named
    subjects `extra_keys`), with its refusal verdict.

    ⚠️ THE SAME CELL INDEX ON EVERY STAFF IS THE SAME BAR (a cell index
    restarts per system, CLAUDE.md §10), so the head's own cell plus each
    candidate's same-index cell holds every rung a ladder between them can
    have -- the pad that put the head in two cells put its rungs there too.
    A box with no `bbox_page_px` is DECLINED, never placed at a guess."""
    out: Dict[str, Rung] = {}

    def _take(row) -> None:
        v = row.value
        if not isinstance(v, (list, tuple)) or not v \
                or str(v[0]) != "ledgerLine":
            return
        lb = (row.detail or {}).get("bbox_page_px")
        if not lb or len(lb) != 4:
            return
        key = row.subject.to_key()
        if key in out:
            return
        lv = ev.verdict(Q.LEDGER_IS_NOT_A_LEDGER, subject=row.subject)
        why = (str(lv.reason) if lv is not None
               and lv.outcome is Outcome.DECIDED and lv.value is True
               else None)
        out[key] = Rung(key=key, x0=float(lb[0]), x1=float(lb[2]),
                        y=(float(lb[1]) + float(lb[3])) / 2.0,
                        refused=why, row_id=row.id)

    for cell in cells:
        for row in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                           subject=cell):
            _take(row)
    for key in extra_keys:
        try:
            sub = R.Subject.from_key(key)
        except ValueError:
            continue
        if sub.to_key() in out:
            continue
        for row in ev.rows(Q.GLYPH_BOX, subject=sub):
            _take(row)
    return list(out.values())


def cv_rungs(ev: Evidence) -> List[Rung]:
    """ROADMAP 2.6d. `Q.LEDGER_RUNG_INK` rows on THIS glyph (the contested
    head, `ev.subject`) as `Rung`s -- the SECOND reader `cell_rungs` above
    has none of, for a step the detector drew no `ledgerLine` box on.

    Each found row already carries the exact window `gather.
    _observe_ledger_rung_ink` tested, in PAGE pixels, so it needs no lookup
    of its own: `ladder_side`'s step arithmetic will match it to the SAME
    step the GATHER-side reader tested it at, by construction (the window is
    centred on the head's own x-span, which is what the x-overlap test in
    `ladder_side` asks for). A row the CV reader ABSTAINED on, or one that
    tested and found nothing, contributes no `Rung` -- `cannot tell` and
    `not there` are both silent here, exactly as a missing `ledgerLine` box
    is silent to `cell_rungs`."""
    out: List[Rung] = []
    for row in ev.rows(Q.LEDGER_RUNG_INK):
        if row.value is not True:
            continue
        d = row.detail or {}
        win = d.get("window_page_px")
        y = d.get("want_y_page")
        if not win or len(win) != 4 or y is None:
            continue
        out.append(Rung(key=f"cv:{row.id}", x0=float(win[0]),
                        x1=float(win[2]), y=float(y), refused=None,
                        row_id=row.id, source="cv_ink"))
    return out


def _ink_clean_negative_ys(ev: Evidence, cand_key: str) -> List[float]:
    """ROADMAP 2.37. Every `want_y_page` `Q.LEDGER_RUNG_INK` read as a
    CLEAN `False` (an OBSERVATION, never a decline) for `cand_key` -- CV's
    own definite *no thin run here*, never a *cannot tell*. Used both to
    veto a detector box at the same Y (`_ink_overridden_rungs`) and to
    test a whole side for Sean's elimination (`_ink_refutes_side`)."""
    out: List[float] = []
    for row in ev.rows(Q.LEDGER_RUNG_INK):
        d = row.detail or {}
        if d.get("candidate") != cand_key or row.value is not False:
            continue
        y = d.get("want_y_page")
        if y is not None:
            out.append(float(y))
    return out


def _ink_overridden_rungs(rungs: Sequence[Rung], ev: Evidence, cand_key: str,
                          spacing: float) -> List[Rung]:
    """ROADMAP 2.37 (Sean, 2026-09-29): *"where a box landed but the ink
    says no thin run, the ink wins"*. `rungs` with every DETECTOR-sourced
    entry dropped that sits within one grid step (`RUNG_GRID_TOLERANCE_
    SPACES`, the SAME tolerance `ladder_side` itself matches a step with)
    of a Y this candidate's own ink cleanly read as NOT a thin run --
    regardless of what `Q.LEDGER_IS_NOT_A_LEDGER` said or never ran. A
    `cv_ink`-sourced Rung is never dropped here: it is ALREADY only ever
    built from a clean `True` (`cv_rungs`), so it cannot contradict
    itself."""
    refuted = _ink_clean_negative_ys(ev, cand_key)
    if not refuted:
        return list(rungs)
    tol = RUNG_GRID_TOLERANCE_SPACES * spacing
    return [r for r in rungs
            if r.source != "detector"
            or all(abs(r.y - ry) > tol for ry in refuted)]


def _ink_refutes_side(ev: Evidence, cand_key: str, expected: int) -> bool:
    """ROADMAP 2.37 (Sean, 2026-09-29, quoted at `gather.
    gather_ownership_evidence`): every notehead past the exempt first
    space ALWAYS has every one of its `expected` rungs printed toward its
    TRUE staff -- so `cand_key` is REFUTED as that staff only when EVERY
    step 1..`expected` was read CLEANLY (an observation, never a decline)
    and NONE of them found a rung. A missing or declined step leaves the
    question open (CLAUDE.md rule 8: *cannot tell* never becomes *not
    there*) -- refutation needs FULL coverage of the ladder, not merely no
    hits among however much of it happened to be asked, or an untested
    step would count as proof of absence."""
    if expected <= 0:
        return False
    read: Dict[int, bool] = {}
    for row in ev.rows(Q.LEDGER_RUNG_INK):
        d = row.detail or {}
        if d.get("candidate") != cand_key:
            continue
        step = d.get("step")
        if isinstance(step, int):
            read[step] = bool(row.value)
    if any(read.get(k) for k in range(1, expected + 1)):
        return False
    return all(k in read for k in range(1, expected + 1))


def staff_geometry(ev: Evidence, staff: R.Subject
                   ) -> Optional[Tuple[List[float], float, List[str]]]:
    """`(line ys, spacing, row ids)` in page pixels, or `None` -- DECLINED,
    never defaulted."""
    lines = ev.rows(Q.STAFF_LINES, subject=staff)
    spacing = ev.rows(Q.STAFF_SPACING, subject=staff)
    if not lines or not spacing:
        return None
    try:
        ys = sorted(float(v) for v in lines[-1].value)
        sp = float(spacing[-1].value)
    except (TypeError, ValueError):
        return None
    if len(ys) < 2 or sp <= 0:
        return None
    return ys, sp, [lines[-1].id, spacing[-1].id]


def _contest_ledger_reading(ev: Evidence, bands, ladders: Dict[str, Any]
                            ) -> Optional[LedgerReading]:
    """The ledger reading for `glyph_owner`'s contest, or `None` where the
    contested glyph is not a notehead (a ledger line joins a NOTE to a
    staff; an accidental or a dynamic has no ladder to read).

    Per candidate: off the page geometry where the head's page box and that
    staff's lines are on the record (`ladder_side`; rungs from the head's
    cell, each candidate's same-index cell, and every rung GATHER's own
    ladder rows named); off GATHER's count otherwise
    (`ladder_side_from_count`; a candidate with no `Q.GLYPH_LADDER` row is
    one GATHER asked nothing of -- no crossing needed)."""
    box_rows = ev.rows(Q.GLYPH_BOX)
    box = box_rows[-1] if box_rows else None
    if box is not None:
        v = box.value
        if not (isinstance(v, (list, tuple)) and v
                and str(v[0]).startswith("notehead")):
            return None
    elif not ladders:
        return None

    head = None
    if box is not None:
        bb = (box.detail or {}).get("bbox_page_px")
        if bb and len(bb) == 4:
            head = (float(bb[0]), float(bb[2]),
                    (float(bb[1]) + float(bb[3])) / 2.0)

    cands = [r.detail.get("candidate") for r in bands
             if r.detail.get("candidate") is not None]
    rungs: Optional[List[Rung]] = None
    # ⚠️ ROADMAP 2.6f: page-frame candidates are built TOGETHER via
    # `ladder_sides_with_discount` (its second pass needs every side's
    # `anchor_y` at once), so their specs are collected first and the
    # anonymous-count sides are slotted back in afterward, in order.
    sides: List[Optional[LadderSide]] = []
    page_specs: List[LadderSpec] = []
    page_positions: List[int] = []
    for cand_key in cands:
        geo = (staff_geometry(ev, R.Subject.from_key(cand_key))
               if head is not None else None)
        lad = ladders.get(cand_key)
        if geo is not None:
            if rungs is None:
                me = ev.subject
                cells = [me.at(Kind.CELL)] + [
                    R.cell(me.page, me.system, R.Subject.from_key(k).staff,
                           me.cell) for k in cands]
                named = [k for r in ladders.values()
                         for k in ((r.detail or {}).get("rungs") or ())]
                # ⚠️ ROADMAP 2.6d: `cv_rungs` is the SECOND reader of this
                # same fact -- a step the detector never boxed, read off the
                # ink instead. One pool, both readers; `ladder_side`'s own
                # step arithmetic decides which candidate and step a rung
                # (of either source) speaks to.
                rungs = (cell_rungs(ev, list(dict.fromkeys(cells)), named)
                        + cv_rungs(ev))
            page_positions.append(len(sides))
            # ⚠️⚠️ ROADMAP 2.37 (manager review of `baaf3f23`): "ink wins"
            # (`_ink_overridden_rungs`, ROADMAP 2.37 round 2) is UNWIRED
            # here, not merely unused -- kept defined for a future round
            # with a reader that has earned the veto, per CLAUDE.md rule
            # 7. The absolute-threshold ink reader (`ledger_rung_ink`)
            # this override trusted to overrule a DETECTOR box was
            # measured (this same branch, rounds 2-4) to MISS roughly half
            # of Sean-CONFIRMED real ledgers on Brahms and ~90% on
            # Litolff -- a reader that wrong that often has not earned a
            # veto over a detector-boxed rung; wiring it dropped real
            # ledgers on the strength of a false "clean negative". A
            # detector-sourced `Rung` now survives an ink clean-negative
            # unconditionally (`test_staged_ledger_cv_first_2_37.py::
            # TestInkOverrideIsUnwired`).
            page_specs.append((cand_key, head[2], head[0], head[1],
                               geo[0], geo[1], rungs))
            sides.append(None)
        elif lad is None:
            sides.append(LadderSide(staff=cand_key, expected=0, found=0,
                                    frame="count"))
        else:
            d = lad.detail or {}
            complete, discounted = _ladder_complete(ev, lad)
            exp = d.get("expected")
            if not isinstance(exp, int):
                exp, fnd = 1, (1 if complete else 0)
            else:
                fnd = int(d.get("found") or 0) - len(discounted)
            sides.append(ladder_side_from_count(cand_key, exp, fnd, (lad.id,)))
    if page_specs:
        for pos, built in zip(page_positions,
                              ladder_sides_with_discount(page_specs)):
            sides[pos] = built
    # ⚠️⚠️ ROADMAP 2.37 (Sean's redirect, 2026-09-29): the all-rungs
    # elimination rule (`_ink_refutes_side`, built in an earlier round on
    # this same branch) is left OFF/unwired here -- `refuted` is not
    # computed and not passed, so `_eliminate` (still defined below, for a
    # future round) never fires (`if not refuted: return fallback`). Sean's
    # own redirect: the ledger reader is needed for OWNERSHIP only, and for
    # that a RELATIVE comparison (`_ledger_owner_comparison`, asked earlier
    # in `adjudicate_glyph_owner`) replaces reading every rung against an
    # absolute floor.
    return ledger_direction(sides)


def _own_glyph_box(ev: Evidence) -> Optional[Dict[str, float]]:
    """This contested glyph's own box, in PAGE pixels.

    ⚠️ DECLINED, NEVER DEFAULTED, exactly as `adjudicate_wedge_anchor` and
    `gather_glyph_families` already refuse a canonical-only box: a glyph
    whose page position is unknown and one measured at page y 1841 are
    different facts, and only the second may answer a cross-staff question
    (CLAUDE.md §10). Returns `None` if `Q.GLYPH_BOX` has no page frame for
    this subject.
    """
    rows = ev.rows(Q.GLYPH_BOX)
    if not rows:
        return None
    y = (rows[0].detail or {}).get("y_center_page")
    if y is None:
        return None
    return {"y_center_page": float(y)}


def _hairpin_separates(ev: Evidence, cand_key: str,
                       head_y: Optional[float]) -> Optional[Term]:
    """Sean's second convention (DECISIONS 2026-09-28): a hairpin always
    sits UNDER its staff, so a note between a staff and the hairpin beneath
    it belongs to that staff — *"if the note is above the hairpin ... it
    belongs to the staff that's between the hairpin and that staff"*.

    A witness from a different glyph family than the notehead reading it
    arbitrates, so it is never correlated with the notehead's own band-
    distance or ladder rows (`Evidence.correlated_groups` buckets by
    `(reader, frame, quantity)`, and a `Q.WEDGE_BOX` row shares none of the
    three with a `Q.GLYPH_BAND_DISTANCE` or `Q.GLYPH_LADDER` row) — it forms
    its own correlated group and is never discounted against them.

    ⚠️ PAGE PIXELS ONLY. `gather_wedge_boxes`' DETECTOR reader files a
    cell-frame box with no page coordinate at all (CLAUDE.md §10: a
    canonical cell frame cannot answer a cross-staff question); only the
    `cv_hairpins` reader, which searches one staff's band in page pixels,
    carries `y_center_page`. A wedge row without it is DECLINED, not
    defaulted to the candidate's own frame.

    ⚠️ DIRECTIONAL BY CONSTRUCTION, and that is why this never has to ask
    which staff sits above which. `gather._band_offset_spaces` and
    `_in_hairpin_band` search only BELOW a staff's own bottom line for its
    hairpins, so "a hairpin filed under `cand_key`" and "a hairpin further
    down the page than `cand_key`'s own bottom line" are the same fact by
    construction, and the only geometry this needs is: is the head below
    `cand_key`'s bottom line, and above that hairpin's own centre.
    """
    if head_y is None:
        return None
    cand = R.Subject.from_key(cand_key)
    lines = ev.rows(Q.STAFF_LINES, subject=cand)
    if not lines or not lines[0].value:
        return None
    bottom = max(float(y) for y in lines[0].value)
    if head_y <= bottom:
        return None                         # the head is not below cand
    for w in ev.rows(Q.WEDGE_BOX, subject=cand, scope=Scope.SELF_AND_DESCENDANTS):
        wy = (w.detail or {}).get("y_center_page")
        if wy is None:
            continue                        # DECLINED: no page frame here
        if bottom < head_y < float(wy):
            return Term("hairpin_separates", W_HAIRPIN_SEPARATES, (w.id,))
    return None


def _human_owner(ev: Evidence):
    """`(row, staff key)` where a human said this ink belongs to that staff.

    ⚠️⚠️ ROADMAP 3.4c — THE SECOND PLACE IN THE PIPELINE THAT ACTS ON A REVIEW
    ROW, and the first that acts on one by DECIDING rather than refusing.
    `review/human_evidence.py` files `Q.HUMAN_BOX_VERDICT = owner:<staff>` on
    the glyph subject the detector already owns; the machine's own rows stay
    exactly where they were and this reads his beside them.

    ⚠️ DELIBERATELY ITS OWN FUNCTION AND NOT A BRANCH IN THE BODY, for the
    reason `_human_not_a_symbol` is one: the three measured-or-assumed tiers
    below it are a contest, and a human's reading of the print is not a term
    in a contest. It is the ground the contest is trying to approximate.

    ⚠️ IT WEIGHS NOTHING AND IT CHECKS NOTHING. In particular it does NOT ask
    whether the named staff is one of the contest's own candidates: a human
    who names a staff the contest never offered is telling us the contest's
    candidate set is wrong, which is a finding, not an error to swallow.
    `review/rerun.py` measures what the award did to the note count.

    ⚠️ ONLY THE LAST ROW COUNTS if he labelled the same box twice — the same
    rule `_human_not_a_symbol` applies, because a sidecar is append-only and
    the later click is the later reading.

    ⚠️⚠️ `owner:other` IS SKIPPED BY NAME, AND THAT IS NOT A GAP. ROADMAP
    3.4g adds the answer *another staff, and I cannot say which* (Sean,
    2026-09-23: *"'belongs to violin' were about the fact that they belonged
    to a different staff"*). This decision's value is a STAFF KEY — every
    consumer parses it as one — so awarding `other` would put a word where a
    subject belongs and `A.is_relocated_copy` would compare it against real
    staff keys forever after. The claim is a REFUSAL, not an award, and it is
    read where refusals live: `notehead_precision._human_not_a_symbol` and
    every per-family refusal in `family_precision.py`, reason
    `human_other_staff`. Dropped here, relocated nowhere — CLAUDE.md §10.
    """
    from ..review.human_evidence import (OWNER_OTHER as _OTHER,
                                         human_says as _says)
    hit = None
    for row in ev.rows(Q.HUMAN_BOX_VERDICT):
        verb, arg = _says(getattr(row, "value", None))
        if verb == "owner" and arg and arg != _OTHER:
            hit = (row, arg)
    return hit


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
             "no_rival_staff", "no_evidence", "ends_on_noteheads"),
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
    all_heads: List[Tuple[str, float, float, float, float]] = []
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
        all_heads.append((str(staff_key), float(box[0]), float(box[1]),
                          float(box[2]), float(box[3])))

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
    ends = _arc_end_owner(arc_box, all_heads, spacing)
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

    ruling = _comparative_arc_ruling(arc, own, own_gap, rivals, detail,
                                     _ARC_RIVAL_MARGIN_SPACES,
                                     _ARC_RIVAL_NEAR_SPACES)
    # ⚠️ THE ARC IS DRAWN OVER THE TWO NOTES IT CONNECTS (CLAUDE.md §10; Sean,
    # 2026-10-07, `brahms 5/0/6/5/11`: *"both arcs belong to the horn"*). When
    # the nearest head at each END belongs to ONE staff, that staff owns the
    # arc -- whatever else lies under its middle. The comparative rule counts
    # EVERY covered head, so one head in the middle owned by another staff
    # tied the clearance at 0.0 and the arc stayed on the staff it was cut
    # from. It speaks only where it DISAGREES with the comparative answer;
    # ends that disagree with each other, or no two end heads near the arc,
    # leave that answer exactly as it was.
    if ends is not None and ends != ruling.value:
        return Ruling(value=ends, reason="ends_on_noteheads", used=(arc.id,),
                      detail={**detail, "end_owner": ends,
                              "comparative": {"value": ruling.value,
                                              "reason": ruling.reason},
                              **({"moved_from": own} if ends != own else {})})
    return ruling


def _comparative_arc_ruling(arc, own, own_gap, rivals, detail, margin, near):
    if not rivals:
        # ⚠️ NOT AN ABSTENTION. "No other staff of this system explains this
        # arc better" is a DECISION that it stays where it was found, and the
        # comparative rule cannot say more than that. A one-staff page always
        # lands here, by construction.
        return Ruling(value=own, reason="no_rival_staff",
                      used=(arc.id,), detail=detail)

    best_gap, _best_n, best_key = rivals[0]
    if best_gap > near:
        return Ruling(value=own, reason="no_better_staff",
                      used=(arc.id,), detail=detail)
    # ⚠️ An arc covering NOTHING in this staff is claimed outright: it binds no
    # note here, so there is nothing for it to be.
    if own_gap is not None and (own_gap - best_gap) < margin:
        return Ruling(value=own, reason="no_better_staff",
                      used=(arc.id,), detail=detail)
    return Ruling(value=best_key, reason="hugs_noteheads", used=(arc.id,),
                  detail={**detail, "moved_from": own})


def _arc_end_owner(arc_box, heads, spacing):
    """The staff that owns the heads at BOTH ends of an arc, or None.

    `heads` is `[(owner key, x0, y0, x1, y1)]` for the whole system, already
    grouped by the OWNER `glyph_owner` decided. An end head is one whose
    centre lies under the arc's x extent (the same padded test the clearance
    makes), whose box is at least `TOO_NARROW_MIN_SPACES` wide (an edge sliver
    is not a note: on `brahms 5/0/6/5/11` the right end held two 7 px slivers
    of the NEXT bar's heads, one for each staff) and that sits within
    `_ARC_RIVAL_NEAR_SPACES` of the arc's box in its owner's staff spaces. The
    left end is the leftmost such head and the right end the rightmost, a
    half head width of slack for a duplicated mark. ONE owner at each end, the
    SAME owner at both, or nothing: it never picks between two.
    """
    from ...export import _ARC_RIVAL_NEAR_SPACES, _SLUR_ARC_PAD_NOTEHEADS
    from .notehead_precision import TOO_NARROW_MIN_SPACES

    if not heads:
        return None
    mean_w = sum(h[3] - h[1] for h in heads) / len(heads)
    pad = _SLUR_ARC_PAD_NOTEHEADS * mean_w
    near = []
    for owner, x0, y0, x1, y1 in heads:
        sp = spacing.get(owner)
        if not sp or (x1 - x0) < TOO_NARROW_MIN_SPACES * sp:
            continue
        cx = (x0 + x1) / 2.0
        if not (arc_box[0] - pad <= cx <= arc_box[2] + pad):
            continue
        gap = max(arc_box[1] - y1, y0 - arc_box[3], 0.0)
        if gap / sp > _ARC_RIVAL_NEAR_SPACES:
            continue
        near.append((cx, owner, x1 - x0))
    if len(near) < 2:      # one head cannot be both ends of an arc
        return None
    lo = min(c for c, _o, _w in near)
    hi = max(c for c, _o, _w in near)
    slack = 0.5 * mean_w
    left = {o for c, o, _w in near if c <= lo + slack}
    right = {o for c, o, _w in near if c >= hi - slack}
    if hi - lo > slack and len(left) == 1 and left == right:
        return next(iter(left))
    return None


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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.75 -- TIE OR SLUR BY SEAN'S TWO-NOTE RULE (2026-10-09)
#
#   *"If an arc only goes from one note to the next and they are both on the
#   same pitch it can only be a tie - never a slur. A slur requires different
#   notes if only 2 are involved."*
#   *"If there are 2 arcs - one over the other - then the tie will always be
#   the bottom and the slur on top."*
#
# THE HISTORY THIS MUST RESPECT. The same comparison existed as
# `OMR_ARC_RECLASS` (an export-time veto) and was REFUSED on OMR-NED: +130 scan
# edits, ALL in the tie->slur half, because a scan's pitch at an arc's ends
# was unreliable. OMR-NED is retired as evidence (DECISIONS 2026-09-08) and
# positions are now read LOCALLY, but the risk is the same: a misread end
# position turns a real tie into a slur. So the rule below DECIDES only where
# every fact it needs was READ, and says what it could not read:
#
#   * the arc's two END HEADS are the ones `_flank_search` finds (the pairing
#     `adjudicate_tie_pair` uses) -- a single head at each end, none between;
#   * each end's staff step is `Q.NOTEHEAD_POSITION` where GATHER read a far
#     head's ledgers (an abstained far head is UNREAD, never its geometry), the
#     geometry step for a head on or beside the staff -- and the step must
#     AGREE with the heads' vertical offset in the page (two instruments, one
#     question; a disagreement is `conflict`, not an answer);
#   * "the same sounding accidental" is proved only as "no printed accidental
#     on the stop head" (same bar) -- an arc whose stop head wears a printed
#     accidental, or has an unclaimed accidental glyph beside it, is not
#     proved a tie;
#   * a tie across a barline is two half-arcs; each is judged by the heads
#     across the barline it names (the last head before it, the first after)
#     -- and the far head does not restate its accidental, so a crossing
#     pair is "unchanged" only when NEITHER end wears one;
#   * an arc cut at BOTH barlines, a chord or second voice at an end, or an
#     end with no head near it is not judged (`why` says which).
# ─────────────────────────────────────────────────────────────────────────────

#: Two stacked arcs are "one over the other" only if the gap between their
#: boxes is under this many staff spaces. NOT swept; the S6 dose-response
#: (benchmarks/omr-arc-grammar-2026-09) decays past 3 spaces, and the number
#: is recorded with every decision so it can be priced from the record.
STACK_MAX_GAP_SPACES = 4.0

#: How much arc there must be to say what it joins: an arc that is not cut by
#: a barline must be at least this many head widths wide, and each of its two
#: ends within `ARC_END_MAX_DX_HEADS` head widths of the head it is read as
#: leaving / reaching. NOT swept: chosen by eye on the two small re-gathers'
#: slivers (0.45 and 0.66 widths -- staff-line ink, not arcs) and recorded with
#: every decision (`arc_width_widths`, `start_dx_widths`, `stop_dx_widths`).
ARC_MIN_WIDTH_HEADS = 1.5

#: A head box taller than this many average head heights is two heads fused
#: (a second a step apart, merged by a thick scan): its centre is neither
#: head's, so its two head-sized ends are offered as candidate partners.
#: NOT swept; the two tiles Sean judged (litolff_02 / litolff_03) have boxes
#: 1.5 and 1.65 head heights tall, single heads 0.9-1.1.
TALL_BOX_HEAD_HEIGHTS = 1.4
ARC_END_MAX_DX_HEADS = 1.5

#: A printed accidental glyph with no owner counts as "possibly this head's"
#: when its right edge stands within this many head widths LEFT of the head and
#: within this many head heights of its centre -- a looser READ of "something
#: stands there" than the owner decision's own window, on purpose: an
#: unclaimed accidental is an UNREAD one, and unread must not read as absent.
ACC_NEAR_DX_HEAD_WIDTHS = 3.0
ACC_NEAR_DY_HEAD_HEIGHTS = 1.5

_ACC_NOT_AN_ACCIDENTAL = ("refused_not_an_accidental",
                          "is_a_key_signature_marker",
                          "head_belongs_to_a_nearer_staff")


def _head_step(ev: Evidence, head_row: Any) -> Tuple[Optional[int], str]:
    """`(half-step from the top line, how it was read)` or `(None, why not)`.

    A far head's position is its LEDGER reading (`Q.NOTEHEAD_POSITION`, ROADMAP
    2.56) and nothing else: where that reader abstained the geometry's
    extrapolation is NOT substituted (CLAUDE.md rule 8) -- the head is unread.
    """
    from ...annotate.ledger_grid import far_head_needs_ledger_read
    v = ev.verdict(Q.NOTEHEAD_POSITION, subject=head_row.subject)
    if v is not None:
        if v.outcome is Outcome.DECIDED and v.value is not None:
            return int(v.value), "ledger"
        return None, "far_head_ledger_unread"
    for p in ev.rows(Q.NOTEHEAD_STAFF_POSITION, subject=head_row.subject):
        r = (p.detail or {}).get("rounded")
        if r is None:
            continue
        if far_head_needs_ledger_read(float(r)):
            return None, "far_head_no_ledger_reading"
        return int(r), "geometry"
    return None, "no_position"


def _accidental_state(ev: Evidence, head: Tuple) -> str:
    """`printed` / `unknown` / `none` -- is a printed accidental on this head?

    `printed`: an accidental glyph's owner verdict DECIDED this head. `unknown`:
    an accidental glyph the owner decision did NOT place stands where this
    head's would (an unread accidental is not an absent one). `none`: neither.
    """
    row, _i, xc, yc, w, h = head
    key = row.subject.to_key()
    cell = row.subject.at(Kind.CELL)
    state = "none"
    for a in ev.rows(Q.ACCIDENTAL_STAFF_POSITION,
                     scope=Scope.SELF_AND_DESCENDANTS, subject=cell):
        ow = ev.verdict(Q.ACCIDENTAL_OWNER, subject=a.subject)
        if ow is not None and ow.outcome is Outcome.DECIDED:
            if ow.value == key:
                return "printed"
            continue
        if ow is not None and ow.reason in _ACC_NOT_AN_ACCIDENTAL:
            continue
        for b in ev.rows(Q.GLYPH_BOX, subject=a.subject):
            pb = (b.detail or {}).get("bbox_page_px")
            if not pb or len(pb) != 4:
                continue
            bx1, bc = float(pb[2]), (float(pb[1]) + float(pb[3])) / 2.0
            if (xc - ACC_NEAR_DX_HEAD_WIDTHS * w <= bx1 <= xc
                    and abs(bc - yc) <= ACC_NEAR_DY_HEAD_HEIGHTS * h):
                state = "unknown"
    return state


def _two_note_reading(ev: Evidence, arc: Any, fs: "_Flank") -> Dict[str, Any]:
    """What the arc JOINS: its two end heads, their steps, and the accidental
    state -- or why that could not be read. Records only; `_two_note_verdict`
    says what Sean's rule makes of it."""
    if fs.abstain is not None:
        return {"evaluated": False, "why": fs.abstain[0]}
    cut_l, cut_r = fs.counts["cut_left"], fs.counts["cut_right"]
    if cut_l and cut_r:
        return {"evaluated": False, "why": "arc_cut_at_both_barlines"}
    # ⚠️ A HALF-ARC OF A TIE CUT BY A BARLINE (the canonical tie): one end is
    # the barline, so its head is the NEAREST head across it -- the last head
    # of the bar before / the first of the bar after -- and the flank search
    # has offered every head of that bar. The other half of the same tie
    # names the same two heads, so both halves get one answer.
    lefts = ([t for t in fs.lefts if t[3] == fs.cell_index - 1]
             if cut_l else fs.lefts)
    rights = ([t for t in fs.rights if t[3] == fs.cell_index + 1]
              if cut_r else fs.rights)
    if not lefts or not rights:
        return {"evaluated": False, "why": "no_head_across_the_barline"}
    S = min(lefts, key=lambda t: abs(t[0]))
    E = min(rights, key=lambda t: abs(t[0]))
    head_of = {h[0].id: h for h in fs.heads}
    hs, he = head_of[S[2].id], head_of[E[2].id]
    out: Dict[str, Any] = {"evaluated": True, "start": S[2].subject.to_key(),
                           "stop": E[2].subject.to_key(),
                           "crosses_barline": S[3] != E[3],
                           "half_arc": ("left" if cut_l else
                                        "right" if cut_r else None)}
    # ⚠️ AN END IS A COLUMN, AND THE ARC JOINS ITS EXTREME NOTE ON ITS OWN SIDE
    # (Sean, 2026-10-09, twice). First, on the litolff_02 / litolff_03 tiles --
    # two-note chords tied across a barline that the first version read as
    # slurs -- *"if they are close to note heads that are the same it is a
    # tie"*; the version that took ANY same-pitch pairing in the two columns
    # was REJECTED: *"It is possible for the notes to switch up and have a tie
    # on one end and a slur on another ... if the arc is above it needs to
    # match the notes at the top; if it is below it needs to match the notes
    # on the bottom."* So: an arc ABOVE the chords joins the TOP note of each
    # end, an arc BELOW joins the BOTTOM note of each, and tie vs slur is
    # decided on THAT pair only. The column machinery only FINDS those notes
    # where the detector fused a chord into one tall box (its top / bottom
    # head-sized end) or refused a member as a duplicate of a head; an extreme
    # note with no staff step (a tall box's end) is unreadable and the rule
    # has no opinion -- the detector's class stands.
    def _column(chosen):
        """Every candidate partner at one end: the usable heads in its column
        (`head`), the boxes refused as a DUPLICATE of a head (`dup` -- the ink
        is a real head's, only its box was a second drawing of it), and the
        two head-sized ends of a box TALLER than a head (`half` -- two heads
        a step apart fused into one box, so its centre is neither head's).
        A `dup` carries its own position row; a `half` has none, so it can
        PROVE a same-pitch pairing (by height alone) and never a different
        one."""
        tol = chosen[4] * TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS
        out_c = []
        for t in fs.heads:
            if t[1] != chosen[1] or abs(t[2] - chosen[2]) > tol * 1.5:
                continue
            if t[0].id == chosen[0].id or fs.usable(t[0]):
                if abs(t[2] - chosen[2]) <= tol:
                    out_c.append((t, "head"))
                if t[5] > TALL_BOX_HEAD_HEIGHTS * fs.avg_h:
                    for yc in (t[3] - t[5] / 2.0 + fs.avg_h / 2.0,
                               t[3] + t[5] / 2.0 - fs.avg_h / 2.0):
                        out_c.append(((t[0], t[1], t[2], yc, t[4], fs.avg_h),
                                      "half"))
                continue
            nv = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=t[0].subject)
            if (nv is not None and nv.outcome is Outcome.DECIDED
                    and nv.value is True
                    and nv.reason in ("stacked_head_duplicate",
                                      "notehead_is_a_duplicate_box")):
                out_c.append((t, "dup"))
        # ⚠️ A DUPLICATE THAT SITS ON A USABLE HEAD IS THAT HEAD, DRAWN TWICE
        # (litolff_06: two boxes 2 px apart on one head, the refused one
        # lower, read as a lower NOTE a step below the head across the
        # barline). Only a refused box standing clear of every usable head is
        # a member of its own -- the stacked second note of a chord.
        heads_ = [c[0] for c in out_c if c[1] == "head"]
        kept = []
        for c in out_c:
            if c[1] == "dup":
                t = c[0]
                if any(min(t[3] + t[5] / 2.0, u[3] + u[5] / 2.0)
                       - max(t[3] - t[5] / 2.0, u[3] - u[5] / 2.0)
                       >= 0.5 * min(t[5], u[5]) for u in heads_):
                    continue
            kept.append(c)
        return kept

    col_s, col_e = _column(hs), _column(he)
    out["start_column"] = sum(1 for c in col_s if c[1] == "head")
    out["stop_column"] = sum(1 for c in col_e if c[1] == "head")
    out["start_dx_widths"] = (None if cut_l else round(S[0] / hs[4], 2))
    out["stop_dx_widths"] = (None if cut_r else round(E[0] / he[4], 2))
    out["arc_width_widths"] = round((fs.ax1 - fs.ax0) / hs[4], 2)
    # ⚠️ THE ARC MUST ACTUALLY REACH ITS HEADS. The flank windows are the tie
    # pairing's (a head up to 3 widths past an end), loose enough to find a
    # tie's partner and far too loose to say what an arc JOINS: a sliver of
    # ink 0.5 head widths long, or an arc ending 2 widths from the nearest
    # head, joins nothing. A cut end is the barline's and is not measured.
    if not cut_l and not cut_r and out["arc_width_widths"] < ARC_MIN_WIDTH_HEADS:
        out.update(evaluated=False, why="arc_narrower_than_a_head_and_a_half")
        return out
    for name, dx, cut in (("start", out["start_dx_widths"], cut_l),
                          ("stop", out["stop_dx_widths"], cut_r)):
        if not cut and abs(dx) > ARC_END_MAX_DX_HEADS:
            out.update(evaluated=False, why="arc_end_far_from_its_head")
            return out
    out["between"] = bool(fs.head_between(S[3], hs[2], E[3], he[2],
                                          (S[2].id, E[2].id)))
    limit = _legacy_articulation.TIE_SAME_POSITION_MAX_SPACES

    def _step_of(c):
        return ((None, "tall_box_end") if c[1] == "half"
                else _head_step(ev, c[0][0]))

    def _side(col):
        ys = [c[0][3] for c in col]
        if fs.arc_yc < min(ys):
            return "above"
        if fs.arc_yc > max(ys):
            return "below"
        return "between"

    side_s, side_e = _side(col_s), _side(col_e)
    out["chord"] = len(col_s) > 1 or len(col_e) > 1
    if side_s != side_e or "between" in (side_s, side_e):
        # an arc inside a chord's extent, or above one end and below the
        # other, joins no extreme note the rule can name
        out.update(relation="side_unclear", arc_side=[side_s, side_e],
                   dy_spaces=None)
        out["_heads"] = (hs[3], he[3], hs[4])
        return out
    side = side_s
    pick = min if side == "above" else max
    ca = pick(col_s, key=lambda c: c[0][3])
    cb = pick(col_e, key=lambda c: c[0][3])
    a, b = ca[0], cb[0]
    sa, sb = _step_of(ca)[0], _step_of(cb)[0]
    dy = abs(a[3] - b[3]) / fs.avg_h
    near = dy <= limit
    if sa is None or sb is None:
        relation = "unread"
    elif sa == sb:
        relation = "same" if near else "conflict"
    else:
        relation = "different" if not near else "conflict"
    out.update(start=a[0].subject.to_key(), stop=b[0].subject.to_key(),
               start_step=sa, stop_step=sb,
               start_step_source=_step_of(ca)[1],
               stop_step_source=_step_of(cb)[1],
               start_candidate=ca[1], stop_candidate=cb[1], arc_side=side,
               dy_spaces=round(dy, 3), relation=relation)
    if relation == "same":
        acc_b = _accidental_state(ev, b)
        acc_a = acc_b if a[1] == b[1] else _accidental_state(ev, a)
        if a[1] == b[1]:
            out["accidental"] = ("unchanged" if acc_b == "none" else
                                 "printed" if acc_b == "printed" else "unknown")
        else:
            out["accidental"] = ("unchanged" if acc_b == acc_a == "none" else
                                 "printed" if "printed" in (acc_b, acc_a)
                                 else "unknown")
        out["stop_accidental"] = acc_b
    out["_heads"] = (a[3], b[3], a[4])
    return out


def _two_note_verdict(kind: str, tn: Dict[str, Any]
                      ) -> Tuple[Optional[str], Optional[str]]:
    """Sean's two-note rule on one arc: `(kind | "abstain" | None, rule)`.
    `None` = the rule has no opinion and the detector's class stands."""
    if not tn.get("evaluated"):
        return None, None
    rel = tn["relation"]
    if tn["between"]:
        # ⚠️ THREE OR MORE ONSETS. Different ends make a tie impossible
        # (a tie joins one pitch); SAME ends prove nothing -- C D C under a
        # slur, or a tie with another voice's note between -- so the detector
        # stands. A slur over three notes is a slur already.
        if rel == "different" and kind == "tie":
            return "slur", "three_or_more_notes_ends_differ"
        return None, None
    if rel == "different":
        return "slur", "two_notes_different_pitch"
    if rel == "same":
        if tn["accidental"] == "unchanged":
            return "tie", "two_notes_same_pitch"
        if tn["accidental"] == "unknown" and kind == "slur":
            # ⚠️ RULE 8. Two notes at one step cannot be a slur, and whether
            # they are one PITCH needs an accidental nobody could read.
            return "abstain", "same_pitch_accidental_unread"
    return None, None


def _stack_reading(ev: Evidence, arc: Any, fs: "_Flank",
                   tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Is exactly ONE other arc stacked over/under this one's two notes?

    Same staff, same two end heads (ends within a head width), the boxes
    DISJOINT in y (overlapping boxes are a duplicate detection, not a stack),
    both on the same side of the heads. `role` is `nearer` / `farther` than the
    other arc to the heads. Sean: above the notes the lower is the tie; below
    them the tie is the one nearer the heads (CONFIRMED by Sean 2026-10-09 on
    the two stacked-below tiles: "A tie, B slur" -- the arc NEARER the
    noteheads is the tie, the other the slur).

    A chord at either end is not a stack (tied chords print one arc per note,
    each its own tie).
    """
    if not tn.get("evaluated") or tn.get("chord"):
        return None
    y_s, y_e, w = tn["_heads"]
    head_yc = (y_s + y_e) / 2.0
    mine_above = fs.arc_yc < head_yc
    cell = ev.subject.at(Kind.CELL)
    sibs = []
    for r in ev.rows(Q.ARC_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if r.subject == ev.subject:
            continue
        pb = (r.detail or {}).get("bbox_page_px")
        if not pb or len(pb) != 4:
            continue
        nv = ev.verdict(Q.ARC_IS_NOT_AN_ARC, subject=r.subject)
        if (nv is not None and nv.outcome is Outcome.DECIDED
                and nv.value is True):
            continue
        # ⚠️ THE SIBLING MUST BE THIS STAFF'S, AND SAID SO. A measure cell is
        # padded into the neighbour (CLAUDE.md §10), so the cell holds the
        # next staff's arcs too -- the first crops of "stacked below" pairs
        # were an arc under one staff and the arc over the staff beneath it.
        # No owner verdict is not "same staff"; it is not a stack partner.
        ow = ev.verdict(Q.ARC_OWNER, subject=r.subject)
        if (ow is None or ow.outcome is not Outcome.DECIDED
                or ow.value != fs.home):
            continue
        bx0, by0, bx1, by1 = (float(v) for v in pb)
        if abs(bx0 - fs.ax0) > w or abs(bx1 - fs.ax1) > w:
            continue
        gap = max(by0 - fs.ay1, fs.ay0 - by1)
        if gap <= 0 or gap / fs.avg_h > STACK_MAX_GAP_SPACES:
            continue
        sib_c = (by0 + by1) / 2.0
        if (sib_c < head_yc) != mine_above:
            continue
        # the arc's own window (`_flank_search`): within 3 head heights of
        # the heads it joins, with the legacy pixel floor
        if abs(sib_c - head_yc) > max(
                fs.avg_h * TIE_FLANK_MAX_DY_HEAD_HEIGHTS,
                TIE_FLANK_MIN_DY_PX):
            continue
        sibs.append((r, sib_c, gap))
    if not sibs:
        return None
    if len(sibs) > 1:
        return {"role": None, "why": "more_than_two_arcs_stacked",
                "n_siblings": len(sibs)}
    r, sib_c, gap = sibs[0]
    nearer = abs(fs.arc_yc - head_yc) < abs(sib_c - head_yc)
    return {"role": "nearer" if nearer else "farther",
            "side": "above" if mine_above else "below",
            "gap_spaces": round(gap / fs.avg_h, 3),
            "other": r.subject.to_key()}


def _kind_with_rules(kind: str, tn: Dict[str, Any],
                     stack: Optional[Dict[str, Any]]
                     ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """`(kind | None for abstain, rule, conflict)` -- the detector's class
    `kind` after Sean's two rules. Positions outrank the stack: "can only be a
    tie / never a slur" is stated as a law, the stack as the usual layout."""
    pos_kind, rule = _two_note_verdict(kind, tn)
    if pos_kind == "abstain":
        return None, rule, None
    role = (stack or {}).get("role")
    if role is None:
        return (pos_kind or kind), rule, None
    want = "tie" if role == "nearer" else "slur"
    if pos_kind is None:
        if want == "tie" and (not tn.get("evaluated") or tn.get("between")):
            return kind, None, "stacked_nearer_but_not_a_two_note_arc"
        return want, ("stacked_nearer_is_tie" if want == "tie"
                      else "stacked_farther_is_slur"), None
    if pos_kind == want:
        return want, rule, None
    # the two rules disagree
    if pos_kind == "slur":
        return "slur", rule, "stack_says_tie_notes_differ"
    # positions say tie (two notes, one pitch), the stack says slur
    if kind == "tie":
        return "tie", rule, "stack_says_slur_two_same_pitch_notes"
    return (None, "stack_slur_over_two_same_pitch_notes",
            "stack_says_slur_two_same_pitch_notes")


@decision(
    quantity=Q.ARC_KIND,
    checkable=Checkable.MIXED,
    checked_by=(
        "a TIE joins two heads of the SAME staff step; an arc whose flanked heads sit on different steps is a SLUR (Sean, 2026-10-09: two notes of one pitch can only be a tie, two of different pitch only a slur) -- decided where both ends' steps were READ",
        "of two arcs STACKED over the same notes the lower is a tie and the upper a slur (Sean, 2026-09-11 and 2026-10-09)",
    ),
    implicates=(Q.ARC_KIND, Q.NOTEHEAD_STAFF_POSITION, Q.NOTEHEAD_POSITION,
                Q.ACCIDENTAL_OWNER, Q.CLEF),
    composed_from=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.STEM,
                   Q.NOTEHEAD_POSITION, Q.ACCIDENTAL_OWNER),
    scope=Kind.GLYPH,
    # ⚠️ `Q.GLYPH_BOX` is declared because a notehead's STEP row carries no x:
    # the step is joined to a position through the box on the SAME glyph. The
    # harness refused the read until it was declared (`UndeclaredEvidence`),
    # which is `Evidence` doing its job -- a decision may only read what it
    # says it reads, so `missing` and `declined` can mean something.
    #
    # ROADMAP 2.75 adds what `_flank_search` (the tie pairing's own head
    # search) reads, plus the two verdicts the two-note rule needs that were
    # decided AFTER this one until `adjudicate.ORDER` moved them up:
    # `Q.NOTEHEAD_POSITION` (a far head's ledger-read position) and
    # `Q.ACCIDENTAL_OWNER` (which head a printed accidental alters).
    wants=(Q.ARC_BOX, Q.NOTEHEAD_STAFF_POSITION, Q.GLYPH_BOX, Q.STEM,
           Q.ARC_OWNER, Q.ARC_IS_NOT_AN_ARC, Q.GLYPH_OWNER,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.CELL_BOX, Q.NOTEHEAD_POSITION,
           Q.ACCIDENTAL_STAFF_POSITION, Q.ACCIDENTAL_OWNER),
    subjects_from=Q.ARC_BOX,
    # ⚠️ A DECIDED arc's reason stays `tie` / `slur`; WHICH rule decided it
    # (`two_notes_same_pitch`, `two_notes_different_pitch`,
    # `three_or_more_notes_ends_differ`, `stacked_nearer_is_tie`,
    # `stacked_farther_is_slur`, or None where the detector's class stood) is
    # `detail["grammar"]["tie_slur_rule"]["rule"]`. Only the two ABSTENTIONS
    # carry a reason of their own, as literals at their Ruling sites, so
    # `brakes` can still resolve this decision's vocabulary.
    reasons=("tie", "slur", "no_arc_box", "no_evidence",
             "same_pitch_accidental_unread",
             "stack_slur_over_two_same_pitch_notes"),
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

    # ⚠️ ROADMAP 2.75 -- SEAN'S TWO-NOTE AND STACK RULES (see the block
    # above `_head_step`). A box the arc-not-an-arc decision refused (a staff
    # line, a barline) is not judged: the refusal stands, the class is the
    # detector's and no rule runs on it.
    detector = kind
    rule = None
    extra_used: Tuple[str, ...] = ()
    refused = ev.verdict(Q.ARC_IS_NOT_AN_ARC)
    if (refused is not None and refused.outcome is Outcome.DECIDED
            and refused.value is True):
        grammar["tie_slur_rule"] = {
            "two_note": {"evaluated": False, "why": "refused_not_an_arc"},
            "rule": None, "detector_class": detector}
    else:
        fs = _flank_search(ev, arc)
        two_note = _two_note_reading(ev, arc, fs)
        stack = _stack_reading(ev, arc, fs, two_note)
        final, rule, conflict = _kind_with_rules(kind, two_note, stack)
        if two_note.get("evaluated"):
            extra_used = tuple(
                t[2].id for t in list(fs.lefts) + list(fs.rights)
                if t[2].subject.to_key() in (two_note["start"],
                                             two_note["stop"]))
        grammar["tie_slur_rule"] = {
            "two_note": {k: v for k, v in two_note.items() if k != "_heads"},
            "stack": stack, "rule": rule, "conflict": conflict,
            "detector_class": detector}
        if final is None:
            if rule == "same_pitch_accidental_unread":
                return Ruling(value=None, reason="same_pitch_accidental_unread",
                              used=(arc.id,) + extra_used,
                              detail={"grammar": grammar,
                                      "detector_class": str(arc.value)})
            return Ruling(value=None,
                          reason="stack_slur_over_two_same_pitch_notes",
                          used=(arc.id,) + extra_used,
                          detail={"grammar": grammar,
                                  "detector_class": str(arc.value)})
        kind = final

    return Ruling(value=kind, reason=kind,
                  used=(arc.id,) + tuple(f[2] for f in flanked) + extra_used,
                  detail={"grammar": grammar,
                          "detector_class": str(arc.value),
                          "confidence": arc.score})


#: How far past an arc's end a flanking head's CENTRE may sit, in that head's
#: own widths. RESTATED from `transcribe._pair_ties_in_staff` (the legacy
#: reference reader), whose "3x notehead width" window is what lets a tie
#: crossing a barline reach the first head of the next bar. Not re-measured
#: here: it is the window the legacy tie count has always been produced under.
TIE_FLANK_MAX_DX_HEAD_WIDTHS = 3.0

#: How far INSIDE an arc's end a flanking head's centre may sit, in that
#: head's own widths. ⚠️ THE ONE NUMBER THE LEGACY RULE DOES NOT HAVE, and it
#: is a SCAN fact: the legacy window starts at the arc's edge (`0 <= dx`),
#: which holds on an engraved page (7 of 7 heads outside) and fails on a scan,
#: where the detector's tie box begins OVER the start head -- measured on
#: Litolff `984073` p3: start-head centres 0.37-0.54 widths inside the box.
#: One width admits those with room and cannot admit the far head of any arc
#: longer than two widths. NOT swept; recorded in
#: `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §3.2b as assumed.
TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS = 1.0

#: How far a flanking head's centre may sit from the arc's own y-centre, in
#: average notehead heights (one staff space), with the legacy floor of 30 px.
#: RESTATED from the same function (`y_tol = max(avg_nh_h * 3, 30)`).
TIE_FLANK_MAX_DY_HEAD_HEIGHTS = 3.0
TIE_FLANK_MIN_DY_PX = 30.0


@dataclass
class _Flank:
    """The heads an arc's two ends reach -- ONE search, read by both
    `adjudicate_tie_pair` (which heads a tie joins) and `adjudicate_arc_kind`
    (ROADMAP 2.75: how many notes an arc joins, and at what pitch).

    MOVED, NOT REWRITTEN, out of `adjudicate_tie_pair` so the kind decision
    and the pairing can never be reading different heads of one arc (the
    reason `geom` exists inside `adjudicate_arc_kind` for S4). `abstain` is
    `(reason, detail)` when the search cannot run; otherwise every field is
    the tie pairing's own local of the same name.
    """
    abstain: Optional[Tuple[str, Dict[str, Any]]] = None
    ax0: float = 0.0
    ay0: float = 0.0
    ax1: float = 0.0
    ay1: float = 0.0
    arc_yc: float = 0.0
    home: str = ""
    cell_index: int = 0
    heads: Any = None
    avg_h: float = 0.0
    lefts: Any = None
    rights: Any = None
    counts: Any = None
    head_between: Any = None
    usable: Any = None


def _flank_search(ev: Evidence, arc: Any) -> "_Flank":
    """The flank search of `adjudicate_tie_pair`, unchanged (its docstring
    carries the reasoning for every window)."""
    box = arc.detail.get("bbox_page_px")
    if not box or len(box) != 4:
        return _Flank(abstain=("no_page_frame", {}))
    ax0, ay0, ax1, ay1 = (float(v) for v in box)
    arc_yc = (ay0 + ay1) / 2.0

    owner = ev.verdict(Q.ARC_OWNER)
    home = (owner.value if owner is not None and isinstance(owner.value, str)
            and owner.value else ev.subject.at(Kind.STAFF).to_key())
    staff = R.Subject.from_key(home)
    cell_index = ev.subject.cell or 0

    def cell_subject(i: int) -> "R.Subject":
        return R.Subject(Kind.CELL, page=staff.page, system=staff.system,
                         staff=staff.staff, cell=i)

    def cell_box(i: int):
        if i < 0:
            return None
        for row in ev.rows(Q.CELL_BOX, subject=cell_subject(i)):
            v = row.value
            if isinstance(v, (list, tuple)) and len(v) == 4:
                return tuple(float(x) for x in v)
        return None

    own_box = cell_box(cell_index)
    has_prev = cell_box(cell_index - 1) is not None
    has_next = cell_box(cell_index + 1) is not None

    heads = []
    for i in (cell_index - 1, cell_index, cell_index + 1):
        if i < 0:
            continue
        for row in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                           subject=cell_subject(i)):
            if (row.detail or {}).get("category") != "notehead":
                continue
            b = row.detail.get("bbox_page_px")
            if not b or len(b) != 4:
                continue
            x0, y0, x1, y1 = (float(v) for v in b)
            if x1 <= x0 or y1 <= y0:
                continue
            heads.append((row, i, (x0 + x1) / 2.0, (y0 + y1) / 2.0,
                          x1 - x0, y1 - y0))
    if not heads:
        return _Flank(abstain=("no_start_head", {"heads_in_reach": 0}))
    avg_h = sum(h[5] for h in heads) / len(heads)
    y_tol = max(avg_h * TIE_FLANK_MAX_DY_HEAD_HEIGHTS, TIE_FLANK_MIN_DY_PX)

    # ⚠️ A TIE CUT BY A BARLINE IS DETECTED AS TWO ARCS, and the half that
    # begins AT the barline has its start head a whole first-half away -- past
    # any fixed reach. `_legacy._SLUR_BOUNDARY_SPACES` (0.5 spaces, IMPORTED,
    # measured for the legacy merge) says when an arc's end sits ON its bar's
    # edge; such an end searches the WHOLE adjacent bar instead of 3 widths.
    # Where there is no adjacent bar the arc is cut by the SYSTEM's edge.
    from ...export import _SLUR_BOUNDARY_SPACES
    edge_tol = _SLUR_BOUNDARY_SPACES * avg_h
    cut_left = own_box is not None and abs(ax0 - own_box[0]) <= edge_tol
    cut_right = own_box is not None and abs(ax1 - own_box[2]) <= edge_tol
    # ⚠️ DECISIONS 2026-10-01 (Sean, on the 2.52 sheet): "the notes have to be
    # next to each other regardless of measures/barlines" -- a tied whole or
    # half note that FILLS its own bar, tying to the next bar's first note,
    # is drawn edge-to-edge of its own bar and is a REAL tie, not a refusal.
    # The earlier rule ("can never cross a whole bar") conflated two
    # different things: an arc cut at both of ITS OWN bar's edges with a note
    # of its own inside that bar (the filled-whole-note case, real) and an
    # arc cut at both edges of a bar that holds NO notehead AT ALL (the
    # staff-line-read-as-a-tie case the first Litolff crop found, `3.2b`
    # FINDINGS). Only the second is refused here; the first falls through to
    # the ordinary flank search below, which already extends across a cut
    # edge into the adjacent bar.
    if cut_left and cut_right and not any(h[1] == cell_index for h in heads):
        return _Flank(abstain=("spans_a_whole_bar",
                                {"own_bar_heads": 0}))

    def usable(row) -> bool:
        # ⚠️ Asked only of a head already inside a window, so the verdicts
        # this decision reads -- and the ids it files as considered -- are the
        # handful that could matter, not every head of three bars.
        own = ev.verdict(Q.GLYPH_OWNER, subject=row.subject)
        if own is not None and _is_relocated_copy(row.subject, own.value):
            return False
        np_ = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=row.subject)
        return not (np_ is not None and np_.outcome is Outcome.DECIDED
                    and np_.value is True)

    lefts, rights = [], []
    for row, i, xc, yc, w, _h in heads:
        if abs(yc - arc_yc) > y_tol:
            continue
        reach = w * TIE_FLANK_MAX_DX_HEAD_WIDTHS
        inside = -w * TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS
        dxl = ax0 - xc
        dxr = xc - ax1
        # ⚠️ A head can be a start only LEFT of the arc's middle and a stop
        # only right of it, so one head is never both ends of one arc.
        mid = (ax0 + ax1) / 2.0
        if xc < mid and dxl >= inside and (
                dxl < reach or (cut_left and i == cell_index - 1)) \
                and usable(row):
            lefts.append((dxl, yc, row, i))
        if xc > mid and dxr >= inside and (
                dxr < reach or (cut_right and i == cell_index + 1)) \
                and usable(row):
            rights.append((dxr, yc, row, i))

    counts = {"lefts": len(lefts), "rights": len(rights),
              "cut_left": cut_left, "cut_right": cut_right}
    # ⚠️ "THE SYSTEM STARTS/ENDS HERE" IS A FACT ABOUT THE STAFF, NOT ABOUT
    # THE ARC: nothing on this staff precedes the arc in the system's first
    # bar (a continuation is engraved after the clef and key, which are not
    # heads), or nothing follows it in the system's last bar. It bounds the
    # cross-system population from above; the partner is on another system
    # and this decision cannot see it.
    starts_system = not has_prev and not any(
        h[1] == cell_index and h[2] < ax0 for h in heads)
    ends_system = not has_next and not any(
        h[1] == cell_index and h[2] > ax1 for h in heads)
    if not lefts and starts_system:
        return _Flank(abstain=("enters_from_previous_system", dict(counts)))
    if not rights and ends_system:
        return _Flank(abstain=("runs_off_the_system", dict(counts)))
    if not lefts and not rights:
        # ⚠️ Usually the TWIN of a tie filed on the NEXT staff: a measure
        # cell is padded into its neighbour, and `arc_owner` asks which heads
        # an arc COVERS -- a tie covers none, so it cannot move one. Its twin
        # on the right staff pairs there; this copy says so and stops.
        return _Flank(abstain=("no_head_near_the_arc", dict(counts)))
    if not lefts:
        return _Flank(abstain=("no_start_head", dict(counts)))
    if not rights:
        return _Flank(abstain=("no_stop_head", dict(counts)))

    # ⚠️ DECISIONS 2026-10-01: "the notes have to be next to each other" --
    # ADJACENT in time, nothing of the arc's own voice/staff between them,
    # whichever position it sits at. `_between` reads the full three-bar
    # head population (not just the ones already windowed into `lefts`/
    # `rights`) because the intervening note may sit at a THIRD position,
    # outside either flank window, and still break adjacency.
    def order_key(i: int, xc: float) -> Any:
        return (i, xc)

    def head_between(il: int, xl: float, ir: int, xr: float,
                      exclude_ids: tuple) -> bool:
        lo, hi = order_key(il, xl), order_key(ir, xr)
        if lo > hi:
            lo, hi = hi, lo
        for row, i, xc, _yc, w, _h in heads:
            if row.id in exclude_ids or not usable(row):
                continue
            if not (lo < order_key(i, xc) < hi):
                continue
            # ⚠️ A head at (near enough) the SAME x as one of the pair's own
            # endpoints is that endpoint's OWN CHORD -- a simultaneous note,
            # not one "between" it in time. Same overlap tolerance the flank
            # search itself uses (`TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS`), so a
            # chord's stacked onsets never read as intervening notes. Found
            # on Litolff p3 (`glyph/3/0/0/0/5`): the stop head's own chord
            # partners, ~1-2 px apart in x, were read as notes between it
            # and the start before this exemption.
            tol = w * TIE_FLANK_MAX_OVERLAP_HEAD_WIDTHS
            if i == il and abs(xc - xl) <= tol:
                continue
            if i == ir and abs(xc - xr) <= tol:
                continue
            return True
        return False

    return _Flank(ax0=ax0, ay0=ay0, ax1=ax1, ay1=ay1, arc_yc=arc_yc,
                  home=home, cell_index=cell_index, heads=heads, avg_h=avg_h,
                  lefts=lefts, rights=rights, counts=counts,
                  head_between=head_between, usable=usable)

@decision(
    quantity=Q.TIE_PAIR,
    checkable=Checkable.MIXED,
    checked_by=(
        "a TIE's two heads sound ONE pitch -- EXPORT compares the two placed "
        "pitches and refuses (and counts) a pair that differs",
    ),
    implicates=(Q.TIE_PAIR, Q.PITCH, Q.ACCIDENTAL, Q.ARC_KIND),
    composed_from=(Q.ARC_BOX, Q.GLYPH_BOX),
    scope=Kind.GLYPH,
    wants=(Q.ARC_BOX, Q.ARC_KIND, Q.ARC_OWNER, Q.ARC_IS_NOT_AN_ARC,
           Q.GLYPH_BOX, Q.GLYPH_OWNER, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
           Q.CELL_BOX),
    subjects_from=Q.ARC_BOX,
    reasons=("paired", "more_than_one_pair", "not_a_tie", "not_an_arc",
             "no_page_frame", "no_start_head", "no_stop_head",
             "no_head_near_the_arc", "spans_a_whole_bar",
             "enters_from_previous_system", "runs_off_the_system",
             "no_pair_at_one_position", "not_adjacent", "no_evidence"),
    mode=Mode.ADDITIVE,
)
def adjudicate_tie_pair(ev: Evidence) -> Ruling:
    """WHICH two noteheads this tie joins -- ROADMAP 3.2b.

    CONVENTION (CLAUDE.md §10, measured): *a tie's two heads are at one staff
    position* (empty interval 0.168 vs 0.435 spaces over every paired link of
    the eleven engraved fixtures), and a tie FLANKS its heads -- it spans the
    gap between them -- so it is found by the heads just OUTSIDE its two ends,
    not by the heads under it (which is slur coverage, `_noteheads_under`, and
    the wrong question: the staged exporter asked it of ties until this
    decision existed and bound 1 of 22 decided ties on the engraved page).

    The rule is `transcribe._pair_ties_in_staff`'s, the legacy reference
    reader: a start head whose centre sits at or left of the arc's left edge
    within 3 of its own widths, a stop head likewise on the right, both within
    3 average head heights of the arc in y; and among the pairs those windows
    admit, the ones whose two heads sit at ONE STAFF POSITION
    (`transcribe.TIE_SAME_POSITION_MAX_SPACES`, IMPORTED).

    ⚠️⚠️ TWO DELIBERATE DIFFERENCES FROM THE LEGACY RULE, BOTH REFUSALS TO
    GUESS (CLAUDE.md rule 6):

    * where NO admitted pair sits at one position the legacy rule falls
      through to the nearest heads in x and ties two different notes. Here it
      ABSTAINS `no_pair_at_one_position`: a tie between two positions is not
      a tie, and which of the arc, the class or a head is wrong is not
      something this decision can tell;
    * where MORE THAN ONE pair sits at one position (a tied chord's members,
      a duplicate detection) the legacy rule takes the nearest in x. Here it
      NARROWS to all of them (`more_than_one_pair`) and EXPORT refuses to
      argmax a narrowing.

    CONVENTION (Sean, DECISIONS 2026-10-01, on the 2.52 sheet): *"whenever
    there are 2 notes of the same pitch next to each other in a bar or
    across barlines and there is an arched line between them it is a tie.
    The notes have to be next to each other regardless of measures/
    barlines and they have to have the same pitch."* Two consequences,
    both measured against the OLD rule below and fixed under 2.54:

    * ADJACENCY is in TIME, not in x-reach alone: a candidate pair is
      refused `not_adjacent` if any OTHER usable head of this bar/voice --
      at ANY staff position, not only the pair's own -- sits strictly
      between the two paired heads. A tie never skips a note;
    * an arc cut at BOTH edges of its own bar is a real tie when that bar
      HOLDS a note of its own (a tied whole/half note filling the bar,
      flanked by the next bar's first head) -- `spans_a_whole_bar` now
      abstains only when the own bar holds NO notehead at all (the
      staff-line-read-as-a-tie case the first Litolff crop found).

    ⚠️ ACROSS A BARLINE, NEVER ACROSS A SYSTEM. The search runs over the
    arc's own bar and the one on either side, on the arc's OWNER staff, in
    page pixels -- the only frame two cells share. A tie cut in two by a
    barline is detected as two arcs and each half names the SAME pair; EXPORT
    writes it once. A half whose search runs into the edge of the system
    abstains `runs_off_the_system` / `enters_from_previous_system`: the other
    head is on another system and this decision cannot see it (the chain
    FINDINGS measured 2 of 632 Breitkopf links crossing a system break).

    ⚠️ THE HEAD SET IS THE ONE EXPORT WRITES: heads filed on the owner staff,
    minus a copy `glyph_owner` gives to another staff (it has a twin there by
    construction -- `adjudicate.is_relocated_copy`) and minus a box a human
    refused as a notehead. Its pitch is NOT read here: the same-position test
    reads BOXES, and the pitch check is EXPORT's, after EVALUATE has restated
    every pitch (see `checked_by`).
    """
    arcs = ev.rows(Q.ARC_BOX)
    if not arcs:
        return Ruling.abstain("no_evidence")
    arc = arcs[0]
    refused = ev.verdict(Q.ARC_IS_NOT_AN_ARC)
    if (refused is not None and refused.outcome is Outcome.DECIDED
            and refused.value is True):
        return Ruling.abstain("not_an_arc")
    kind = ev.verdict(Q.ARC_KIND)
    if kind is None or kind.outcome is not Outcome.DECIDED \
            or kind.value != "tie":
        return Ruling.abstain("not_a_tie",
                              kind=None if kind is None else kind.value)
    fs = _flank_search(ev, arc)
    if fs.abstain is not None:
        # ⚠️ ONE LITERAL `Ruling.abstain` SITE PER REASON, as before the search
        # moved into `_flank_search`: `brakes` resolves a decision's declared
        # vocabulary by finding each reason as a literal at a Ruling site, and
        # a reason passed through a variable made `tie_pair` UNRESOLVED (a new
        # open finding) for no change in what it returns.
        why, extra = fs.abstain
        if why == "no_page_frame":
            return Ruling.abstain("no_page_frame", **extra)
        if why == "no_start_head":
            return Ruling.abstain("no_start_head", **extra)
        if why == "no_stop_head":
            return Ruling.abstain("no_stop_head", **extra)
        if why == "spans_a_whole_bar":
            return Ruling.abstain("spans_a_whole_bar", **extra)
        if why == "enters_from_previous_system":
            return Ruling.abstain("enters_from_previous_system", **extra)
        if why == "runs_off_the_system":
            return Ruling.abstain("runs_off_the_system", **extra)
        return Ruling.abstain("no_head_near_the_arc", **extra)
    ax0, ay0, ax1, ay1, arc_yc = fs.ax0, fs.ay0, fs.ax1, fs.ay1, fs.arc_yc
    home, heads, avg_h = fs.home, fs.heads, fs.avg_h
    lefts, rights, counts = fs.lefts, fs.rights, fs.counts
    head_between = fs.head_between

    limit = _legacy_articulation.TIE_SAME_POSITION_MAX_SPACES

    def one_position(ya: float, yb: float) -> bool:
        return abs(ya - yb) / avg_h <= limit

    # ⚠️ A TIE JOINS CONSECUTIVE NOTES. Of two heads at the partner's position
    # on one side, the nearer is the tied one -- a farther one has the nearer
    # between it and the arc -- so only the nearest at that position is a
    # candidate. That is forced, not preferred; what remains ambiguous (two
    # DIFFERENT positions each with a pair -- a tied chord -- or two heads at
    # one x) is NARROWED, never argmaxed.
    #
    pairs = []
    blocked_by_intervening = 0
    for dxl, yl, rl, il in lefts:
        for dxr, yr, rr, ir in rights:
            if rl.subject == rr.subject or not one_position(yl, yr):
                continue
            if any(d < dxl for d, y, r, _i in lefts
                   if r is not rl and one_position(y, yr)):
                continue
            if any(d < dxr for d, y, r, _i in rights
                   if r is not rr and one_position(y, yl)):
                continue
            xl_c, xr_c = ax0 - dxl, ax1 + dxr
            if head_between(il, xl_c, ir, xr_c, (rl.id, rr.id)):
                blocked_by_intervening += 1
                continue
            pairs.append(((dxl + dxr) / avg_h, abs(yl - yr) / avg_h,
                          rl, rr, il, ir, yl, yr))
    if not pairs:
        nearest = min(((abs(yl - yr) / avg_h) for _a, yl, _b, _c in lefts
                       for _d, yr, _e, _f in rights), default=None)
        if blocked_by_intervening:
            return Ruling.abstain(
                "not_adjacent", **counts,
                candidates_blocked=blocked_by_intervening)
        return Ruling.abstain(
            "no_pair_at_one_position", **counts,
            nearest_dy_spaces=None if nearest is None else round(nearest, 3))
    pairs.sort(key=lambda p: (p[0], p[1]))

    # ⚠️ NOT a tied-chord disambiguator by the arc's own y-centre: `3.2c`
    # (ROADMAP) already tried resolving a stacked-tie chord this way and
    # measured it DEAD AT ZERO on both scan corpora -- real stacked ties
    # are two SEPARATE arcs each already outside the other's `y_tol` flank
    # band in practice, not one arc ambiguous between two close positions.
    # Where this decision genuinely cannot tell (two positions equally
    # plausible for ONE arc) it still narrows, unchanged from 3.2b.

    def value_of(p) -> Dict[str, Any]:
        return {"start": p[2].subject.to_key(), "stop": p[3].subject.to_key()}

    if len(pairs) > 1:
        return Ruling.narrow(
            [R.Candidate(value_of(p), -round(p[0], 3)) for p in pairs],
            "more_than_one_pair", used=(arc.id,), **counts,
            pairs_at_one_position=len(pairs))
    dx, dy, rl, rr, il, ir, _yl, _yr = pairs[0]
    return Ruling(
        value=value_of(pairs[0]), reason="paired",
        used=(arc.id, rl.id, rr.id),
        detail={**counts, "dy_spaces": round(dy, 3),
                "dx_spaces": round(dx, 3),
                # ⚠️ RECORDED, NOT GATED: how far the arc sits from its pair
                # in y. The window is the legacy 3 head heights; the Litolff
                # crops show false `tie` boxes on a staff line 2-3 spaces from
                # the pair they flank, so this is what a tighter window would
                # be priced from.
                "arc_dy_spaces": round(abs(
                    arc_yc - (_head_yc(heads, rl) + _head_yc(heads, rr)) / 2)
                    / avg_h, 3),
                "crosses_barline": il != ir,
                "home_staff": home})


def _head_yc(heads, row) -> float:
    return next(h[3] for h in heads if h[0] is row)


def _is_relocated_copy(subject, owner_value) -> bool:
    from ..adjudicate import is_relocated_copy
    return is_relocated_copy(subject, owner_value)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.27 — a candidate `glyph_owner` has already handed to the
# neighbour is not this staff's to attach a mark to.
#
# The measure cell is padded 4-6 staff spaces (CLAUDE.md §10) and on a
# conductor's page that reaches the next staff's ink, so `articulation_
# owner`, `fermata_owner` and `ornament_owner` each pick their carrier from
# EVERY `Q.GLYPH_BOX` row in the mark's own cell -- including a notehead (or
# rest) whose ink is really the neighbour staff's, caught in this cell's pad.
# `adjudicate_glyph_owner` already asks "whose is this" for exactly that
# population (`subjects_from=Q.GLYPH_BAND_DISTANCE`, the CONTESTED glyphs
# only) and stamps a DECIDED verdict on it -- these three decisions simply
# never read it (`grep GLYPH_OWNER` on their old `wants=` returned nothing).
# That is CLAUDE.md's "value existed and nothing read it" class, not a new
# rule: `adjudicate_dynamic` (`adjudicators/text.py`) already reads
# `Q.GLYPH_OWNER` this same way for a margin-label letter, and this mirrors
# its exact test (`owned_by` compared against `home`, an uncontested
# candidate's missing verdict falling through unchanged).
# ─────────────────────────────────────────────────────────────────────────────


def _owned_by_a_different_staff(ev: Evidence, row: Any, home: str) -> bool:
    """A DECIDED `Q.GLYPH_OWNER` verdict on this candidate names a staff
    other than `home`.

    NEVER relocates a glyph and never decides ownership from pad position
    alone (CLAUDE.md §10) -- it only refuses to treat a candidate `glyph_
    owner` has already DECIDED belongs elsewhere as if it were this staff's.
    Only a DECIDED value moves a candidate out of consideration (CLAUDE.md
    rule 6, connect never guess): a NARROWED or ABSTAINED ownership contest,
    or a candidate never contested at all (no verdict, `owner is None`), is
    left exactly as before -- `owned_by` then falls back to `home`, the same
    fallback `adjudicate_dynamic` uses.
    """
    owner = ev.verdict(Q.GLYPH_OWNER, subject=row.subject)
    owned_by = owner.value if owner is not None and owner.value else home
    return owned_by != home


@decision(
    quantity=Q.ARTICULATION_OWNER,
    composed_from=(Q.ARTICULATION_MARK, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    scope=Kind.GLYPH,
    wants=(Q.ARTICULATION_MARK, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    subjects_from=Q.ARTICULATION_MARK,
    reasons=("nearest_on_declared_side", "no_notehead", "no_side_declared",
             "no_evidence", "owned_by_another_staff"),
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
    home = ev.subject.at(Kind.STAFF).to_key()
    all_heads = [r for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                    subject=cell)
                 if (r.detail or {}).get("category") == "notehead"
                 and isinstance(r.value, (list, tuple)) and len(r.value) >= 5]
    if not all_heads:
        return Ruling.abstain("no_notehead", articulation=name)
    # ⚠️ ROADMAP 2.27: a candidate `glyph_owner` already DECIDED belongs to
    # the neighbour staff is dropped BEFORE the side/distance test ever sees
    # it -- reported apart from `no_notehead` so a mark with nothing of its
    # own in this cell can be told from one whose only candidates are the
    # neighbour's ink.
    heads = [r for r in all_heads if not _owned_by_a_different_staff(ev, r, home)]
    if not heads:
        return Ruling.abstain("owned_by_another_staff", articulation=name,
                              n_candidates=len(all_heads))

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
                   Q.GLYPH_BOX, Q.CELL_STAFF_SPACE,
                   Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL,
                   Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.GLYPH_OWNER,
                   Q.KEYSIG_MARKER),
    scope=Kind.GLYPH,
    # ⚠️ THREE VERDICTS BESIDE THE FOUR GATHER ROWS, added when 2.7 was
    # MERGED onto the tree that had grown them overnight (2026-09-27). Each is
    # a fact the ADJUDICATE order has already settled by the time this runs
    # (`adjudicate.ORDER` puts the per-family refusals and `glyph_owner`
    # first), so reading them is connecting a decision, never guessing one.
    wants=(Q.ACCIDENTAL_STAFF_POSITION, Q.NOTEHEAD_STAFF_POSITION,
           Q.GLYPH_BOX, Q.CELL_STAFF_SPACE,
           Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL,
           Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.GLYPH_OWNER,
           Q.KEYSIG_MARKER),
    subjects_from=Q.ACCIDENTAL_STAFF_POSITION,
    reasons=("immediately_right_same_position", "ambiguous_height",
             "no_candidate", "no_unit", "no_evidence",
             "refused_not_an_accidental", "is_a_key_signature_marker",
             "head_belongs_to_a_nearer_staff"),
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

    # ⚠️⚠️ A REFUSED ACCIDENTAL OWNS NOTHING (roadmap 3.4g, merged before this
    # item landed). `adjudicate_accidental_is_not_an_accidental` refuses a box
    # a human marked *nothing* or *belongs to another staff*; once it has, the
    # ink is not an accidental of THIS staff, and handing it a notehead here
    # would put the alteration Sean struck out back into the file one stage
    # later. An ABSTENTION and not a decision of "no owner": the glyph's
    # meaning was settled elsewhere, and this decision says so by name
    # rather than filing it under `no_candidate`, which would read as a
    # geometry failure.
    refusal = ev.verdict(Q.ACCIDENTAL_IS_NOT_AN_ACCIDENTAL)
    if (refusal is not None and refusal.outcome is Outcome.DECIDED
            and refusal.value is True):
        return Ruling.abstain("refused_not_an_accidental",
                              alteration=alteration,
                              refusal=refusal.id,
                              refusal_reason=refusal.reason)

    # ⚠️⚠️ ROADMAP 2.7b — A KEY-SIGNATURE MARKER IS NEVER AN IN-BAR
    # ACCIDENTAL, AND THAT IS NOW A STATED RULE RATHER THAN A GEOMETRY
    # ACCIDENT. 2.9/2.12a admit accidental-SHAPED header boxes into the key
    # signature's marker run (`gather._gather_keysig_markers`: the detector
    # does not always spell a signature flat `keyFlat`), so one box is read
    # twice — once as a marker, once here. Sean's crop 7 (2026-09-27) is
    # exactly that box: *"the glyph is a KEY-SIGNATURE flat"*; the reader
    # abstained on it, but for `no_candidate`, a geometry reason that would
    # have become a pairing the day a head stood at its height. Only a
    # marker the key reader COUNTED in its run is one (see
    # `_keysig_marker_row`: a marker past the run's gap is Sean's confirmed
    # in-bar natural of crop 12, boxed twice). Checked BEFORE the pairing
    # geometry: it says what the glyph IS.
    marker = _keysig_marker_row(ev)
    if marker is not None:
        return Ruling.abstain("is_a_key_signature_marker",
                              alteration=alteration,
                              marker=marker.id,
                              marker_shape=marker.value,
                              marker_role=(marker.detail or {}).get(
                                  "detector_role"))

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

    own_staff = ev.subject.at(Kind.STAFF).to_key()
    heads = {}
    elsewhere = {}
    excluded: Dict[str, str] = {}
    for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                     subject=cell):
        if (r.detail or {}).get("category") != "notehead":
            continue
        if not isinstance(r.value, (list, tuple)) or len(r.value) < 5:
            continue
        # ⚠️⚠️ A HEAD THE RECORD HAS ALREADY SAID IS NOT A HEAD OF THIS STAFF
        # IS NOT A CANDIDATE (merge onto 3.4A/C + 2.6, 2026-09-27). Two
        # settled facts, both upstream in `adjudicate.ORDER`:
        #   * `notehead_is_not_a_notehead` DECIDED True -- a clef fragment, a
        #     barline sliver, a box a human struck out. The exporter refuses
        #     to write it; an accidental owned onto it would be decided and
        #     never written, and worse, it would have WON the height contest
        #     against the real head beside it.
        #   * `glyph_owner` names ANOTHER staff -- the contest DROPS the loser
        #     here (CLAUDE.md §10) and the note is written from the winner's
        #     own detection, never from this cell.
        # This is not a fallback converting "cannot tell" into an answer: the
        # excluded boxes are not noteheads of this staff by a verdict, and the
        # ambiguity test below runs over what is left exactly as before.
        sub = r.subject
        npv = ev.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, subject=sub)
        if (npv is not None and npv.outcome is Outcome.DECIDED
                and npv.value is True):
            if npv.reason == "belongs_to_a_nearer_staff":
                # ⚠️ ROADMAP 2.7b: a NOTE, and another staff's. Kept aside,
                # not dropped from sight: see `elsewhere` below.
                excluded[sub.to_key()] = "belongs_to_a_nearer_staff"
                elsewhere[sub.to_key()] = r
                continue
            excluded[sub.to_key()] = "not_a_notehead"
            continue
        owner = ev.verdict(Q.GLYPH_OWNER, subject=sub)
        if (owner is not None and owner.outcome is Outcome.DECIDED
                and isinstance(owner.value, str)
                and owner.value != own_staff):
            excluded[sub.to_key()] = "owned_by_another_staff"
            continue
        heads[sub.to_key()] = r
    if not heads and not elsewhere:
        return Ruling.abstain("no_candidate", alteration=alteration,
                              why="no notehead in this cell",
                              heads_excluded=excluded or None)

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
    for key, row in list(heads.items()) + list(elsewhere.items()):
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
            heads_excluded=excluded or None,
            max_dx_spaces=_ACC_MAX_DX_SPACES,
            max_dy_positions=_ACC_MAX_DY_POSITIONS)

    cands.sort(key=lambda t: (t[0], t[1]))
    # ⚠️⚠️ ROADMAP 2.7b — THE ACCIDENTAL FOLLOWS ITS HEAD. A head refused
    # `belongs_to_a_nearer_staff` is still a NOTE, and the glyph printed at
    # its height immediately left of it is that note's accidental — on the
    # other staff, with it. Where it is this glyph's BEST candidate the glyph
    # abstains by name rather than falling through to the next head in the
    # cell: the other refusals (`clipped_fragment`, `too_narrow`, a human's
    # *nothing*) say the ink is no note at all, so a second-best head may
    # well be the glyph's own; this one says the glyph's note is elsewhere.
    if cands[0][2] in elsewhere:
        return Ruling.abstain("head_belongs_to_a_nearer_staff",
                              alteration=alteration, head=cands[0][2],
                              heads_excluded=excluded or None)
    cands = [c for c in cands if c[2] not in elsewhere]
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
                "confidence": detail.get("confidence"),
                "heads_excluded": excluded or None})


def _keysig_marker_row(ev: Evidence):
    """The `Q.KEYSIG_MARKER` row this accidental glyph IS, or None.

    ⚠️ ONLY A ROW THE KEY READER COUNTED (`header.marker_run_members`): a
    marker past the run's gap, or in a run of mixed kinds the reader refused,
    is not a signature member and the glyph is judged on its geometry.

    ⚠️ A JOIN BY FRAME, CLASS AND POINT, because the marker row names no
    glyph (`gather._gather_keysig_markers` files it on the STAFF with the
    detection's `detector_class`, canonical `x` and `y_center`, frame
    `cell:N`). The glyph's own `Q.GLYPH_BOX` is the same detection, so the
    class and the integer `x` agree exactly and `y + h/2` to the detector's
    rounding. The CLASS is not optional: Litolff p3 Violino I boxes one ink
    twice at x 1007/1008, once `accidentalFlat` (admitted as a marker) and
    once `accidentalNatural` (Sean's crop 12, a confirmed in-bar natural).
    """
    from .header import marker_run_members
    boxes = ev.rows(Q.GLYPH_BOX)
    if not boxes or not isinstance(boxes[-1].value, (list, tuple)) \
            or len(boxes[-1].value) != 5:
        return None
    name, x, y, _w, h = boxes[-1].value
    frame = f"cell:{ev.subject.cell}"
    marks = [r for r in ev.rows(Q.KEYSIG_MARKER,
                                scope=Scope.SELF_AND_ANCESTORS)
             if str(r.frame) == frame]
    if not marks:
        return None
    unit = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                   subject=ev.subject.at(Kind.CELL))
    try:
        space = float(unit[0].value) if unit else 0.0
    except (TypeError, ValueError):
        space = 0.0
    for r in marker_run_members(marks, space):
        d = r.detail or {}
        try:
            mx, my = float(d["x"]), float(d["y_center"])
        except (KeyError, TypeError, ValueError):
            continue
        cls = d.get("detector_class")
        if cls is not None and str(cls) != str(name):
            continue
        if abs(mx - float(x)) < 0.5 \
                and abs(my - (float(y) + float(h) / 2.0)) <= 1.0:
            return r
    return None


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
    composed_from=(Q.FERMATA_MARK, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    scope=Kind.GLYPH,
    wants=(Q.FERMATA_MARK, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    subjects_from=Q.FERMATA_MARK,
    reasons=("contains_the_mark", "nearest_in_bar", "no_carrier",
             "no_evidence", "owned_by_another_staff"),
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
    home = ev.subject.at(Kind.STAFF).to_key()
    all_carriers = [r for r in ev.rows(Q.GLYPH_BOX,
                                       scope=Scope.SELF_AND_DESCENDANTS,
                                       subject=cell)
                    if (r.detail or {}).get("category") in _FERMATA_CARRIERS
                    and isinstance(r.value, (list, tuple)) and len(r.value) >= 5]
    if not all_carriers:
        # ⚠️ A REAL POPULATION, NOT A DEFENSIVE BRANCH: 9 of the 46 cells
        # holding a fermata on Litolff `984073` p1-3 carry neither a notehead
        # nor a rest. The mark was read and there is nothing in that bar for it
        # to hang on, which is a gap in the READING and is reported as one.
        return Ruling.abstain("no_carrier", detector_class=str(mark.value))
    # ⚠️ ROADMAP 2.27: the notehead-side sibling above says why this is
    # dropped before the containment/nearest test, not folded into
    # `no_carrier` -- a bar whose only ink is the neighbour staff's is not
    # the same reading gap as a bar with nothing in it at all.
    carriers = [r for r in all_carriers
                if not _owned_by_a_different_staff(ev, r, home)]
    if not carriers:
        return Ruling.abstain("owned_by_another_staff",
                              detector_class=str(mark.value),
                              n_candidates=len(all_carriers))

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
    composed_from=(Q.ORNAMENT_MARK, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    scope=Kind.GLYPH,
    wants=(Q.ORNAMENT_MARK, Q.GLYPH_BOX, Q.GLYPH_OWNER),
    subjects_from=Q.ORNAMENT_MARK,
    reasons=("nearest_on_declared_side", "nearest_either_side", "no_notehead",
             "no_evidence", "owned_by_another_staff"),
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
    home = ev.subject.at(Kind.STAFF).to_key()
    all_heads = [r for r in ev.rows(Q.GLYPH_BOX, scope=Scope.SELF_AND_DESCENDANTS,
                                    subject=cell)
                 if (r.detail or {}).get("category") == "notehead"
                 and isinstance(r.value, (list, tuple)) and len(r.value) >= 5]
    if not all_heads:
        return Ruling.abstain("no_notehead", ornament=kind)
    # ⚠️ ROADMAP 2.27, same connection as `articulation_owner`/`fermata_
    # owner` above.
    heads = [r for r in all_heads if not _owned_by_a_different_staff(ev, r, home)]
    if not heads:
        return Ruling.abstain("owned_by_another_staff", ornament=kind,
                              n_candidates=len(all_heads))

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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.27d — pedal marks and octave brackets, gated on a decided brace.
#
# Neither family has a `record.Q` of its own to gather into
# (`gather_coverage.FAMILY_TO_Q["keyboard"] = None`, `["ottava"] = None`), so
# each declares its domain the way `family_precision.py`'s ledger/accidental/
# arpeggiato decisions already do for the same reason: `subjects_from=
# Q.GLYPH_BOX` narrowed by `subjects_classed`, the raw detector class rather
# than a named quantity. Both are OWNERSHIP questions, not "is this real"
# questions, so they belong here beside `articulation_owner`/`fermata_
# owner`/`ornament_owner` rather than in `family_precision.py`.
#
# ⚠️ EXPORT DOES NOT YET READ EITHER VERDICT -- see `Q.PEDAL_OWNER`/
# `Q.OTTAVA_OWNER`'s own docstrings in `record.py` and FINDINGS SS2.27d in
# `benchmarks/omr-owner-domain-2026-09/FINDINGS.md`. Neither family fires on
# this project's acceptance set (no keyboard/harp movement, no ottava
# bracket measured yet), so leaving the `<pedal>`/`<octave-shift>` emission
# unbuilt costs nothing there; building the OWNERSHIP half now means the
# export gap is the ONLY thing left when a keyboard work enters the corpus,
# rather than a fresh nearest-staff guess as well.
# ─────────────────────────────────────────────────────────────────────────────


@decision(
    quantity=Q.PEDAL_OWNER,
    checkable=Checkable.UNCHECKABLE,
    # ⚠️ `Q.GLYPH_BOX` IS NOT HERE. It sets this decision's DOMAIN
    # (`subjects_from`/`subjects_classed`, below) but its content -- the
    # box's own x/y/w/h -- answers no question this decision asks; unlike
    # `adjudicate_ottava_owner`, a pedal mark's OWN geometry is not read,
    # only which staff it was filed on.
    composed_from=(Q.GROUP_SYMBOL, Q.STAFF_GROUP),
    scope=Kind.GLYPH,
    subjects_from=Q.GLYPH_BOX,
    subjects_classed=("keyboardpedal",),
    wants=(Q.GROUP_SYMBOL, Q.STAFF_GROUP),
    reasons=("grand_staff_lower_staff", "no_brace"),
    mode=Mode.ADDITIVE,
)
def adjudicate_pedal_owner(ev: Evidence) -> Ruling:
    """A `keyboardPedalPed`/`keyboardPedalUp` glyph belongs to the LOWER
    staff of the grand-staff pair it was detected on -- never to whichever
    cell's pad happened to catch the ink, because the mark sits BELOW the
    whole pair, not between its two hands (`PLACEMENT-CONVENTIONS.md`,
    "Pedal marks": *"below the entire grand staff... never attributed to
    the nearer one by distance"*).

    Off a decided brace this ABSTAINS `no_brace` rather than guessing a
    staff -- inert on every orchestral system, where no group's own
    instrument family is ever keyboard/harp and `Q.GROUP_SYMBOL` never
    decides "brace" at all.
    """
    home_sub = ev.subject.at(Kind.STAFF)
    home = home_sub.to_key()
    # ⚠️ ROADMAP 2.27d, READ DIRECTLY (not only through `structure`'s own
    # query) so `wants`' declaration of both quantities is true of THIS
    # body -- see `text._canonical_grand_staff_owner`'s identical note.
    brace = ev.verdict(Q.GROUP_SYMBOL, subject=home_sub.at(Kind.SYSTEM))
    if brace is None or brace.value != "brace":
        return Ruling.abstain("no_brace")
    own_group = ev.verdict(Q.STAFF_GROUP, subject=home_sub)
    if own_group is None or own_group.value is None:
        return Ruling.abstain("no_brace")
    partner = _structure.grand_staff_partner_staff(ev, home)
    if partner is None:
        return Ruling.abstain("no_brace")
    a, b = R.Subject.from_key(home), R.Subject.from_key(partner)
    lower = home if a.staff >= b.staff else partner
    return Ruling(value=lower, reason="grand_staff_lower_staff",
                  used=(brace.id, own_group.id),
                  detail={"pair": sorted([home, partner])})


@decision(
    quantity=Q.OTTAVA_OWNER,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.GLYPH_BOX, Q.STAFF_LINES),
    scope=Kind.GLYPH,
    subjects_from=Q.GLYPH_BOX,
    subjects_classed=("ottavabracket",),
    wants=(Q.GLYPH_BOX, Q.STAFF_LINES),
    reasons=("above", "below", "no_staff_lines"),
    mode=Mode.ADDITIVE,
)
def adjudicate_ottava_owner(ev: Evidence) -> Ruling:
    """Which staff an `ottavaBracket` shifts, and which direction: the
    bracket belongs to the staff it hugs, never to a neighbour across the
    gap it is drawn in (`PLACEMENT-CONVENTIONS.md`, "Brace, bracket, ottava
    bracket": *"an ottava bracket sits above (8va) or below (8vb) the
    staff whose octave it shifts"*).

    Geometry only, off THIS glyph's OWN cell -- an `ottavaBracket` box
    whose vertical centre stands above this staff's own top line is an
    8va for THIS staff (`"above"`); below the bottom line is an 8vb
    (`"below"`). A box that falls inside the five-line band (a misread,
    the class this decision's own domain never expects) abstains rather
    than guessing a side.

    ⚠️ THE MusicXML SIDE IS NOT THE SAME WORD AS THIS VALUE. An `above`
    bracket is written `<octave-shift type="down" size="8">` and a
    `below` one `type="up"` -- MusicXML's `type` names the direction of
    the shift AWAY FROM the true (sounding) pitch, which is the OPPOSITE
    of the printed line's side (verified 2026-09-29,
    `usermanuals.musicxml.com/MusicXML/Content/EL-MusicXML-octave-
    shift.htm`: *"up: ... such as 8va bassa"*, *"down: ... such as
    8va"*). Written pitch is untouched: an `<octave-shift>` is a
    `<direction>`, not a pitch rewrite, so nothing here or at EXPORT may
    change a note's `<pitch>` for this reason -- see `Q.OTTAVA_OWNER`'s
    own docstring in `record.py`.
    """
    # ⚠️ `ev.rows(Q.GLYPH_BOX)` DEFAULTS TO `subject=ev.subject`, so every
    # row returned already names THIS glyph -- the last is taken as the
    # freshest reading, the same convention `adjudicate_system_membership`
    # and its siblings in `structure.py` use for a single-reader quantity.
    rows = ev.rows(Q.GLYPH_BOX)
    if not rows or not isinstance(rows[-1].value, (list, tuple)) or len(rows[-1].value) < 5:
        return Ruling.abstain("no_staff_lines")
    _cls, _x, y, _w, h = rows[-1].value[:5]
    yc = float(y) + float(h) / 2.0

    home = ev.subject.at(Kind.STAFF)
    lines = ev.rows(Q.STAFF_LINES, scope=Scope.SELF_AND_ANCESTORS,
                    subject=home)
    if not lines or not lines[-1].value:
        return Ruling.abstain("no_staff_lines")
    ys = [float(v) for v in lines[-1].value]
    top, bottom = min(ys), max(ys)

    if yc < top:
        return Ruling(value={"staff": home.to_key(), "direction": "above",
                             "musicxml_type": "down"}, reason="above",
                      used=(rows[-1].id, lines[-1].id),
                      detail={"y_center": yc, "staff_top": top})
    if yc > bottom:
        return Ruling(value={"staff": home.to_key(), "direction": "below",
                             "musicxml_type": "up"}, reason="below",
                      used=(rows[-1].id, lines[-1].id),
                      detail={"y_center": yc, "staff_bottom": bottom})
    return Ruling.abstain("no_staff_lines", y_center=yc, staff_top=top,
                          staff_bottom=bottom)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.58b -- ONE OWNERSHIP RULING PER PHYSICAL MARK
# ─────────────────────────────────────────────────────────────────────────────


#: ROADMAP 2.58c (Sean, 2026-10-08 brief; the rule is CLAUDE.md §10 as Sean
#: stated it on 2026-09-28: *"the ledger lines name the owner, and they are
#: authoritative ... nearness is only a hint and never overrides them"*).
#: The reasons a `glyph_owner` verdict rests on the LEDGER witness, and the one
#: that rests on nearness alone. Every other deciding reason (`staff_band`,
#: `range_veto`, `ladder`, `hairpin_separates`) is neither and is never ranked.
LEDGER_OWNER_REASONS = ("ledger_note_first", "ledger_direction",
                        "ledger_owner_density")
NEARNESS_ONLY_OWNER_REASONS = ("distance",)


def _refused_as_a_note(log: R.Log, sub: R.Subject) -> bool:
    v = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
    return bool(v is not None and v.outcome is Outcome.DECIDED
                and v.value is True)


def reconcile_group_owners(log: R.Log) -> Dict[str, int]:
    """`glyph_owner` rules ONCE per `Q.MARK_GROUP` (Sean, 2026-10-06).

    Every box of one mark gets the SAME owner. The members were ruled one by
    one from their own cells -- each looked at a different padded crop -- and
    the measured outcomes disagree in a way that loses ink: one copy decided
    and the other abstained (the abstained copy was then written NOWHERE as
    `owner_not_read`), or no copy was contested at all.

    ⚠️ IT CONNECTS A DECISION AND NEVER LETS ONE GUESS (CLAUDE.md rule 6).
    THE RULES, in the order they are tried (ROADMAP 2.58c states 3-5):

      1. every member that DECIDED names the same staff -> the members that
         abstained, or that never entered the contest, take that staff; the
         new verdict names the decided members' verdicts as its BASIS and
         SUPERSEDES the member's own, so both stay on the record;
      2. no member decided -> nothing is filed. The census says WHY, because
         the two cases are not the same thing: `owned_by_filing_staff` (no
         member was ever contested and all were cut from ONE staff -- nobody
         disputes it, there is no verdict to file) is an owner;
         `unowned_abstained` (a contested copy looked and could not tell:
         `far_no_rungs`, `tied`) and `unowned_split_uncontested` (never
         contested but filed on DIFFERENT staves) are not, and stay counted
         under `owner_not_read`, never silently assigned (rule 8);
      3. A REFUSED BOX DOES NOT VOTE. A member whose
         `notehead_is_not_a_notehead` verdict is DECIDED True is not a note;
         its `glyph_owner` is not evidence about the mark's staff (that
         decision does not read the refusal), so it neither supplies an owner
         nor blocks one (`refused_ignored`);
      4. the decided members DISAGREE and exactly ONE staff rests on the
         LEDGER witness (`LEDGER_OWNER_REASONS`) while every dissenter rests
         on nearness alone (`NEARNESS_ONLY_OWNER_REASONS`) -> the ledger
         staff is the group's owner and the nearness verdicts are SUPERSEDED
         (`conflict_resolved_by_ledger`). Ledger lines name the owner; a
         silent ledger look from the other copy's crop is the absence of
         evidence, not a refutation;
      5. any other disagreement -- two ledger readings, a ledger reading
         against `staff_band`/`ladder`/`range_veto`, a swap -- files nothing
         and is counted (`conflict`); each member keeps its own ruling. A swap
         is not resolved by a vote.
    A DECIDED verdict is overturned ONLY by rule 4.

    Returns the census. Runs only where `Q.MARK_GROUP` rows exist, so a record
    gathered without `OMR_MARK_GROUPS` is untouched.
    """
    groups: Dict[str, List[R.Subject]] = {}
    for sub in log.subjects(Kind.GLYPH):
        for row in log.rows(Q.MARK_GROUP, sub):
            groups.setdefault(row.value, []).append(sub)
    census: Counter = Counter()
    for gid in sorted(groups):
        members = groups[gid]
        if len(members) < 2:
            continue
        census["groups"] += 1
        verdicts = {m: log.verdict(Q.GLYPH_OWNER, m) for m in members}
        refused = {m for m in members if _refused_as_a_note(log, m)}
        decided_all = {m: v for m, v in verdicts.items()
                       if v is not None and v.outcome is Outcome.DECIDED
                       and isinstance(v.value, str)}
        decided = {m: v for m, v in decided_all.items() if m not in refused}
        if len(decided) != len(decided_all):
            census["refused_ignored"] += 1
        owners = {v.value for v in decided.values()}
        if not decided:
            census["all_silent"] += 1
            if any(v is not None for v in verdicts.values()):
                census["unowned_abstained"] += 1
            else:
                homes = {m.at(Kind.STAFF).to_key() for m in members
                         if m.at(Kind.STAFF) is not None}
                census["owned_by_filing_staff" if len(homes) == 1
                       else "unowned_split_uncontested"] += 1
            continue
        if len(owners) > 1:
            ledger_owners = {v.value for v in decided.values()
                             if v.reason in LEDGER_OWNER_REASONS}
            dissent_is_nearness = len(ledger_owners) == 1 and all(
                v.reason in NEARNESS_ONLY_OWNER_REASONS
                for v in decided.values() if v.value not in ledger_owners)
            if not dissent_is_nearness:
                census["conflict"] += 1
                continue
            owners = ledger_owners
            decided = {m: v for m, v in decided.items()
                       if v.value in ledger_owners}
            census["conflict_resolved_by_ledger"] += 1
        owner = next(iter(owners))
        basis = tuple(sorted(v.id for v in decided.values()))
        for m in members:
            if m in decided:
                continue
            prior = verdicts[m]
            own = m.at(Kind.STAFF)
            if prior is None and own is not None and own.to_key() == owner:
                continue                 # never contested and already home
            if prior is not None and prior.outcome is Outcome.DECIDED \
                    and (m in refused or prior.value == owner):
                continue                 # a refused box's ruling is left alone
            out = R.Verdict(
                id=log._next_id("vrd"), subject=m, quantity=Q.GLYPH_OWNER,
                outcome=Outcome.DECIDED, value=owner,
                decider="reconcile_group_owners",
                reason="group_owner", considered=basis, basis=basis,
                supersedes=prior.id if prior is not None else None,
                detail=({"overruled": prior.value, "by": "ledger"}
                        if prior is not None
                        and prior.outcome is Outcome.DECIDED else {}))
            log.record(out)
            census["adopted_after_abstaining" if prior is not None
                   and prior.outcome is not Outcome.DECIDED
                   else "overruled_by_ledger" if prior is not None
                   else "adopted_uncontested"] += 1
    return dict(census)


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.59 -- A DOT BELONGS TO THE NOTE TO ITS LEFT (Sean, 2026-10-07)
# ─────────────────────────────────────────────────────────────────────────────

#: A box of notehead class counts as THE SAME INK as a dot box where at least
#: this share of the SMALLER box lies inside the other, and it is no larger
#: than DOT_TWIN_MAX_RATIO x the dot box on either side. ⚠️ Containment, not
#: the group rule's IoU 0.3: a dot clipped by the cell edge is a fragment of
#: the whole dot (Brahms `7/1/0/9/9` against `7/1/1/9/10`: 54% of the
#: fragment inside the dot, IoU 0.295 -- under the group rule's bar by 0.005).
DOT_TWIN_OVERLAP_MIN = 0.5
DOT_TWIN_MAX_RATIO = 1.35


#: ROADMAP 2.59 round 2 (Sean, 2026-10-07). THE GEOMETRIC TESTS, stated before
#: any count, in staff spaces (sp), all in the PAGE frame.
#:
#: STACKED UNDER A NOTE (a staccato-placed dot): the dot's centre x lies within
#: DOT_STACK_CENTRED_MAX_SPACES of the centre of a notehead -- of ANY staff,
#: owned by anyone (the staccato window's own centring figure) -- and the dot's
#: centre y lies OUTSIDE that head's y-extent, no farther from its nearest
#: edge than DOT_STACK_MAX_SPACES. MEASURED on the 10-07 night records before
#: it was fixed: the dots this separated from true staccati sit at 0.0-0.5 sp
#: from the centre (99% under 0.42), while a lengthening dot beside the
#: shifted head of a chord's second sits at 0.5-0.76 sp -- the span's EDGE. A lengthening dot sits to the RIGHT of its
#: head at the head's own height (in the space, or the space above for a line
#: note: CLAUDE.md §10); a staccato sits directly above or below a head,
#: within its x span. A dot that fits the second is never read as the first.
DOT_STACK_MAX_SPACES = 2.0
DOT_STACK_CENTRED_MAX_SPACES = 0.5
#: ON A BARLINE: a mark's page x-extent reaches the barline column, i.e. comes
#: within BARLINE_COLUMN_TOL_SPACES of its cell's left or right page edge --
#: cells are cut AT the barlines (`Q.CELL_BOX` edges; the cells of a staff
#: are contiguous, Brahms p5 staff 1: 1330 | 1804 | 2271), the precedent is
#: `unread_mark._touches_a_barline`. Tighter than that rule's 0.5 sp so a dot
#: printed close before a barline is not taken for ink on it.
BARLINE_COLUMN_TOL_SPACES = 0.15


def dot_stacked_under_a_note(dot_page, notes_page, sp_page) -> bool:
    if not dot_page or not sp_page:
        return False
    cx, cy = (dot_page[0] + dot_page[2]) / 2.0, (dot_page[1] + dot_page[3]) / 2.0
    for b in notes_page:
        if abs(cx - (b[0] + b[2]) / 2.0) > DOT_STACK_CENTRED_MAX_SPACES * sp_page:
            continue
        if b[1] <= cy <= b[3]:
            continue
        gap = (b[1] - cy) if cy < b[1] else (cy - b[3])
        if gap <= DOT_STACK_MAX_SPACES * sp_page:
            return True
    return False


def mark_on_a_barline(mark_page, cell_page, sp_page) -> bool:
    if not mark_page or not cell_page or not sp_page:
        return False
    tol = BARLINE_COLUMN_TOL_SPACES * sp_page
    return any(mark_page[0] <= edge + tol and mark_page[2] >= edge - tol
               for edge in (cell_page[0], cell_page[2]))


def _decided_str(v) -> Optional[str]:
    if v is not None and v.outcome is Outcome.DECIDED \
            and isinstance(v.value, str):
        return v.value
    return None


def reconcile_dot_owners(log: R.Log) -> Dict[str, int]:
    """A dot's owner is its NOTE's owner (`OMR_DOT_FOLLOWS_NOTE`, default OFF).

    Run after `Q.DOT_ROLE`, whose augmentation verdict names the note the dot
    trails (`detail.head`). CONNECTS, NEVER GUESSES (rule 6): it only reads
    two verdicts that already exist and files the dot's owner as the note's
    -- the note's DECIDED `glyph_owner`, or, where the note was never
    contested, its own filing staff. A note whose owner is not decided files
    nothing (`head_owner_undecided`). The dot's own verdict is superseded,
    never overwritten.

    Second half: a notehead-class box that is the SAME INK as such a dot (a
    dot clipped by the cell edge and boxed as a head -- Brahms `glyph/7/1/0/
    9/9`) takes the dot's final owner; it was given to whichever strip cut it.
    """
    if not dot_follows_note_enabled():
        return {}
    census: Counter = Counter()
    dots: Dict[str, Tuple[R.Subject, str]] = {}
    for sub in log.subjects(Kind.GLYPH):
        role = log.verdict(Q.DOT_ROLE, sub)
        if role is None or role.outcome is not Outcome.DECIDED \
                or role.value != "augmentation":
            continue
        head = (role.detail or {}).get("head")
        if not head:
            census["no_head_named"] += 1
            continue
        if (role.detail or {}).get("head_refused"):
            census["head_is_a_refused_fragment"] += 1
            continue
        hsub = R.Subject.from_key(head)
        hv = log.verdict(Q.GLYPH_OWNER, hsub)
        target = _decided_str(hv)
        if target is None and hv is None:
            hs = hsub.at(Kind.STAFF)
            target = hs.to_key() if hs is not None else None
        if target is None:
            census["head_owner_undecided"] += 1
            continue
        census["dots"] += 1
        dv = log.verdict(Q.GLYPH_OWNER, sub)
        home = sub.at(Kind.STAFF)
        cur = _decided_str(dv) if dv is not None else (
            home.to_key() if home is not None else None)
        dots[sub.to_key()] = (sub, target)
        if cur == target:
            census["already_with_its_note"] += 1
            continue
        basis = tuple(x.id for x in (role, hv, dv) if x is not None)
        out = R.Verdict(
            id=log._next_id("vrd"), subject=sub, quantity=Q.GLYPH_OWNER,
            outcome=Outcome.DECIDED, value=target,
            decider="reconcile_dot_owners", reason="dot_follows_note",
            considered=basis, basis=basis,
            supersedes=dv.id if dv is not None else None,
            detail={"head": head, "was": cur})
        log.record(out)
        census["moved_to_its_note" if cur else "filed"] += 1
    # --- the dot-shaped notehead-class box that is a dot's own ink ----------
    page_dots: Dict[Tuple[int, int], List[Tuple[Any, str]]] = {}
    for key, (sub, target) in dots.items():
        for r in log.rows(Q.GLYPH_BOX, sub):
            bb = (r.detail or {}).get("bbox_page_px")
            if bb and len(bb) == 4:
                page_dots.setdefault((sub.page, sub.system), []).append(
                    (tuple(bb), target))
    if page_dots:
        for sub in log.subjects(Kind.GLYPH):
            npv = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
            if npv is None or npv.outcome is not Outcome.DECIDED \
                    or npv.value is not True:
                continue
            for r in log.rows(Q.GLYPH_BOX, sub):
                bb = (r.detail or {}).get("bbox_page_px")
                cls = (r.value[0] if isinstance(r.value, (list, tuple))
                       and r.value else "")
                if not bb or len(bb) != 4 \
                        or not str(cls).lower().startswith("notehead"):
                    continue
                for db, target in page_dots.get((sub.page, sub.system), ()):
                    if _box_overlap_of_smaller(tuple(bb), db) < DOT_TWIN_OVERLAP_MIN:
                        continue
                    if (bb[2] - bb[0]) > DOT_TWIN_MAX_RATIO * (db[2] - db[0]) \
                            or (bb[3] - bb[1]) > DOT_TWIN_MAX_RATIO \
                            * (db[3] - db[1]):
                        continue
                    census["dot_twin_boxes"] += 1
                    ov = log.verdict(Q.GLYPH_OWNER, sub)
                    ohome = sub.at(Kind.STAFF)
                    cur = _decided_str(ov) if ov is not None else (
                        ohome.to_key() if ohome is not None else None)
                    if cur == target:
                        break
                    basis = tuple(x.id for x in (npv, ov) if x is not None)
                    log.record(R.Verdict(
                        id=log._next_id("vrd"), subject=sub,
                        quantity=Q.GLYPH_OWNER, outcome=Outcome.DECIDED,
                        value=target, decider="reconcile_dot_owners",
                        reason="dot_follows_note", considered=basis,
                        basis=basis,
                        supersedes=ov.id if ov is not None else None,
                        detail={"twin_of_a_dot": True, "was": cur}))
                    census["dot_twin_moved"] += 1
                    break
    return dict(census)


def _box_overlap_of_smaller(a, b) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ((ix1 - ix0) * (iy1 - iy0)) / small if small > 0 else 0.0
