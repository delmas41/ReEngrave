"""ROADMAP 2.274 step 2 -- THE WITNESSED PAGE-INK ARC RUNS BOUND TO NOTES AND WRITTEN, ONE ARC EACH. PATH: STAGED. PURE helpers: no pipeline import, no row filed,
nothing decided by itself. The callers are `adjudicators/ownership.adjudicate_page_arc_binding` (ADJUDICATE, flag ON) and `export._pair_arcs` / `_place_arcs`
(EXPORT, flag ON). Registered in `reach.NOT_A_STAGE`.

Sean 2026-11-08 ("Try 1"): take ONLY the page-ink runs a detector arc box agrees with (WITNESSED: 0 fakes of 20 seeded on the round-4 hold-out), bind each run's two ends to
notes, and write each as ONE arc. A run no detector box witnesses (about 4.8 fakes a page, step 1) is NOT written in this step.

`OMR_PAGE_ARC_WRITE` (default ON since 2.305's landing, deny-list; `=0` opts out). It also turns the step-1 reader on in GATHER (`page_arcs.enabled`): the flag needs the
`Q.PAGE_ARC` rows. Opted out, the decision files nothing and EXPORT reads nothing (the pre-2.274 file; tests + the gates in FINDINGS).

THE RULE THAT OWNS EACH VALUE (CLAUDE §6, "name the rule that owns the value"):
  * the arc and its extent: page-facts "Arcs and hairpins are READ PAGE-WIDE ... a detector box is only a witness" (2026-10-30) -- the run, never the box;
  * END -> NOTE: page-facts "An arc often stops short of its note; it binds to the CLOSEST note" (2026-11-05). `arc_claim.bind_end`: a head inside the 2.166 window binds as
    it always did; an end with none binds to the closest usable head beyond it (`closest_ok=True`, 2.271's code, the staff's own heads, no fixed distance); two columns
    about equally near (`BIND_COLUMN_MARGIN_SPACES`) or a chord end that cannot choose ABSTAIN with both candidates and the signed margin; a run that is HALF of an arc (another run
    BEGINS nearer its end than the closest head stands) leaves that end unbound (`continues_in_another_curve`);
  * KIND: page-facts s1 "A tie joins exactly TWO ADJACENT notes of the SAME pitch; anything else is a slur", same pitch read from POSITION measured locally at each head
    (`ownership._page_binding` with `page_run`: 2.223's body, not a copy). The detector's class is a prior and is not an input (`arc_class` is empty);
  * a run off a system's edge joins the run that picks up on the next system (page-facts, Sean 2026-11-05): 2.271 step 3's `export._across_system_spans`, REUSED, one candidate
    only, fed by this binding's `edge` ends;
  * ONE MARK, ONE ARC: a written run REPLACES the detector arcs of every box that witnesses it (and only a box all of whose witnessed runs are written: a box shared with an
    abstained run keeps its OFF arc, rule 8 -- nothing the old path wrote is lost to an abstention);
  * UNCERTAINTY (CLAUDE §4): an end that cannot bind, a kind that cannot be read, a head in the other voice: abstain and COUNT it; the old path then writes whatever it wrote.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: that an arc whose ink a detector arc box agrees with is the arc, and its ends belong to the closest notes; Sean's
blind tiles ("Does the arc start and end on the right notes?") are the judge. NOT CONFIRMED: the witness share (`page_arcs.WITNESS_SHARE`, 0.5 of a box's width) and the closest-head
rule beyond the pages measured; the join across systems beyond 2.271's pages.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ENV_WRITE = "OMR_PAGE_ARC_WRITE"

#: statuses of one run in the verdict's `detail["runs"]`
WRITTEN = "written"
ABSTAINED = "abstained"
NOT_WITNESSED = "not_witnessed"


def _on(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _flag_on(name: str) -> bool:
    """Default ON, deny-list: off only for an explicit 0 / false / no / off."""
    return os.environ.get(name, "1").strip().lower() not in ("0", "false", "no", "off")


def write_enabled() -> bool:
    """`OMR_PAGE_ARC_WRITE`, default ON since ROADMAP 2.305's landing (deny-list; `=0` opts out)."""
    return _flag_on(ENV_WRITE)


# ── ROADMAP 2.338: AN ARC BELONGS TO THE NOTE ITS INK REACHES ─────────────────────────────────────────────────────────────────────────────────
#
# THE RULE (our wording, put to Sean as the lane's brief; it joins page-facts "An arc ends at the notes standing where its ink ends", Sean 2026-11-15, and
# CLAUDE §4 "joining and separating go by ink", Sean 2026-11-18): a slur or tie starts and stops at a note -- its end points at that note's head or, on the
# stem side, at that note's stem. The end belongs to the note whose HEAD INK or STEM INK it reaches. Where two notes are both reached, or neither, we do not
# choose. A tie sits beside the ONE head it ties; an end that reaches a chord member nobody read is no tie's end and reads no kind off another member (unread,
# marked, never a tie). NEVER: an end over blank paper (no head or stem ink at it) binds nothing; another staff's note is never a candidate (the caller's).
#
# THE CAUSE it answers (2026-11-23 small test, FINDINGS): the binder measured how far an end stands from its note's BOX CENTRE (`END_BEYOND_HEAD_SPACES`,
# r2's 2.0) and refused slurs that end at a stem (2-4 spaces from the head's centre, beside the stem's ink) and an end on a chord's outer member when the
# member nearer it was not read (Sean's r8 tile 10, Brahms p0 run 76, 2.017 against 2.0). With the flag ON the refusals of the old binder -- and ONLY those --
# are asked again by ink: an end the old binder bound is never moved (every arc written today stays exactly as written).
ENV_END_BY_INK = "OMR_ARC_END_BY_INK"
#: an end REACHES a note's ink when the gap from where the arc's ink ends to the head's ink box (its page-head ink centre, its box size) or to the line of
#: its stem (head to free end) is at most this many spaces. Both sides measured (FINDINGS 2.338): written-right ends and Sean's judged arcs below it,
#: ends at a barline the tracker stopped at / over blank paper above it. A cut-off: it only ever lets a REFUSED end bind where it holds, never moves a binding.
INK_REACH_SPACES = 1.0


def end_by_ink_enabled() -> bool:
    """`OMR_ARC_END_BY_INK` (ROADMAP 2.338), default OFF."""
    return _on(ENV_END_BY_INK)


# ── ROADMAP 2.358 (i): AN ARC ENDS AT A NOTE THE PAGE INK READ ───────────────────────────────────────────────────────────────────────────────
#
# THE RULE (ours, put in a musician's words): an arc's end rests on the note it reaches, and a note the file writes is a note an arc may end at --
# also one read from its ink alone at the end of a stem (written blue, GUESSED). NEVER: an arc bound across a separate note nobody read (the unread-ink
# guard for every other ink stands unchanged); never a note refused or held in doubt for any other reason (a key's claim, a duplicate box).
#
# THE CAUSE (step 0, 20261123-night, Litolff 43 / Brahms 13 ends refused `unread_ink_at_end`): the "unread" ink is most often NOT a piece of the tied head
# but a second notehead box, added where the page ink alone read a head at a stem end (`notehead_precision`, NARROWED `stem_end_ink_only`) -- Litolff 20
# of 43, Brahms 2 of 13; EXPORT writes 21 of those 22 (blue). ADJUDICATE's arc binder held such a head "not read" (2.305 r7, `ownership._head_read`) and
# then refused the arc as "cannot tell" -- although the note is in the file and, in most of the 20, IS the arc's note (a chord member it ends on, or the
# next note). Sean's own judged case for the r7 guard (r6 tile 2, Litolff p13 `13/0/3/13/5 -> 13/0/3/14/7`, stop note narrowed `stem_end_ink_only`)
# was answered "half notes with a tie" -- RIGHT: the arc to that note was the true reading. No number.
ENV_END_AT_INK_HEAD = "OMR_ARC_END_AT_INK_HEAD"
#: the ADJUDICATE reason of a head the page ink alone read at a stem end (`notehead_precision`; `export.STEM_END_INK_ONLY_REASON` writes it blue)
STEM_END_INK_ONLY = "stem_end_ink_only"


def end_at_ink_head_enabled() -> bool:
    """`OMR_ARC_END_AT_INK_HEAD` (ROADMAP 2.358 (i)), default ON (landed 2026-11-26)."""
    return _flag_on(ENV_END_AT_INK_HEAD)


# ── ROADMAP 2.358 (iii): THE TWO PIECES OF AN ARC ACROSS A SYSTEM BREAK, BY STAFF AND HEIGHT ─────────────────────────────────────────────────
#
# THE RULE (Sean 2026-11-13, page-facts: "An arc across a system break is ONE arc in two pieces"; 2026-11-05 "Anything that needs to be done to connect
# arc separated by systems is fine"): the piece that leaves a system and the piece that enters the next system on the same instrument's staff, curved the
# same way (both over their notes, or both under) at the same height on the staff, are one arc. Where an instrument has more than one piece on either side
# of the break, each piece is joined to the ONE piece across the break that matches it so, and only where that one matches it alone. NEVER: two pieces
# curved opposite ways; two pieces at different heights; a piece with two equally good partners (stacked arcs) -- not joined, counted. The tie-or-slur
# choice and every other check of the join (`export._across_system_spans`) are unchanged.
#
# THE CAUSE (step 0): the join wrote a pair only where the instrument had EXACTLY ONE piece on each side of the break; two arcs crossing one break on one
# staff (a slur over a tie, two voices) were all "ambiguous" (20261123-night sample: Litolff 2, Brahms 8). Height and curve were never compared.
# MEASURED BOTH SIDES (sample, same staff index across the break, both ends of each piece read): the pieces of one arc stand 0.02-1.43 spaces apart in
# height (18 pairs); pieces curved the same way that are NOT one arc 3.35 spaces and more (the next, 7.2+); a cup against a cap 2.89 and more. The cut
# sits in that gap. NOT CONFIRMED beyond Litolff 984073 / Brahms 317803; it only ever joins where the old rule joined nothing.
ENV_JOIN_BY_HEIGHT = "OMR_ARC_JOIN_BY_HEIGHT"
JOIN_HEIGHT_SPACES = 2.0


def join_by_height_enabled() -> bool:
    """`OMR_ARC_JOIN_BY_HEIGHT` (ROADMAP 2.358 (iii)), default ON (landed 2026-11-26)."""
    return _flag_on(ENV_JOIN_BY_HEIGHT)


def pair_by_height(rights: Sequence[Dict[str, Any]], lefts: Sequence[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """ROADMAP 2.358 (iii): `(i, j)` for each right-edge piece `rights[i]` and left-edge piece `lefts[j]` that are each other's ONLY match: the same
    `shape` (`above` / `below`, the binder's curve side) and `y_end_spaces` (the end's height below its own staff's top line) within `JOIN_HEIGHT_SPACES`.
    A piece missing either value matches nothing."""
    def ok(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        sa, sb, ya, yb = a.get("shape"), b.get("shape"), a.get("y_end_spaces"), b.get("y_end_spaces")
        return sa in ("above", "below") and sa == sb and ya is not None and yb is not None and abs(float(ya) - float(yb)) <= JOIN_HEIGHT_SPACES
    m = [[ok(a, b) for b in lefts] for a in rights]
    out = []
    for i in range(len(rights)):
        js = [j for j in range(len(lefts)) if m[i][j]]
        if len(js) == 1 and sum(1 for k in range(len(rights)) if m[k][js[0]]) == 1:
            out.append((i, js[0]))
    return out


def _seg_gap(px: float, py: float, x: float, y0: float, y1: float) -> float:
    lo, hi = min(y0, y1), max(y0, y1)
    dy = 0.0 if lo <= py <= hi else min(abs(py - lo), abs(py - hi))
    return ((px - x) ** 2 + dy ** 2) ** 0.5


def ink_reach(key: str, heads: Sequence[Dict[str, Any]], points: Sequence[Tuple[float, float]], sp: float,
              usable: Any = None) -> Tuple[float, Optional[str], Optional[str]]:
    """ROADMAP 2.338: how near (spaces) the arc's ink end comes to the INK of the note whose head box is `key`: the note is the head's column (every head
    box standing over it, a chord's members; `arc_claim.BIND_COLUMN_DX_WIDTHS`), its ink each member's head ink box (`arc_claim._to_head`: the head's ink
    centre where the page head found one, its box size) and each member's STEM, the line from the head to the stem's free end (the stem-tip entries the
    caller built, `arc_claim.stem_tips`). `points`: where the ink ends -- the run's own end and the traced ink's last point; the nearer counts.
    Returns `(gap_spaces, how, member)`: `how` is `head` (a read head's ink), `stem` (a stem's ink) or `unread_member` (the ink of a member no reader
    read as a note -- the chord is reached, its head is not)."""
    from . import arc_claim as AC
    ok = usable or (lambda _k: True)
    by = {h["key"]: h for h in heads if not h.get("tip")}
    hd = by.get(key)
    if hd is None or sp <= 0:
        return float("inf"), None, None
    col = [h for h in by.values() if abs(h["cx"] - hd["cx"]) <= AC.BIND_COLUMN_DX_WIDTHS * max(h["w"], hd["w"])]
    keys = {h["key"] for h in col}
    best: Tuple[float, Optional[str], Optional[str]] = (float("inf"), None, None)
    for ex, ey in points:
        for h in col:
            g = AC._to_head(h, ex, ey) / sp
            if g < best[0]:
                best = (g, "head" if ok(h["key"]) else "unread_member", h["key"])
        for t in heads:
            if t.get("tip") and t["key"] in keys:
                g = _seg_gap(ex, ey, float(t["cx"]), float(by[t["key"]]["cy"]), float(t["cy"])) / sp
                if g < best[0]:
                    best = (g, "stem", t["key"])
    return best


def _end_points(d: Dict[str, Any], side: str) -> List[Tuple[float, float]]:
    pts = [(float(d["x_%s_page" % side]), float(d["y_%s_page" % side]))]
    if d.get("x_%s_ext" % side) is not None:
        pts.append((float(d["x_%s_ext" % side]), float(d["y_%s_ext" % side])))
    return pts


def settle_by_ink(e: Dict[str, Any], heads: Sequence[Dict[str, Any]], d: Dict[str, Any], side: str, sp: float, usable: Any,
                  unread: Optional[Sequence[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.338: an end the binder REFUSED as two notes about equally near (`two_columns_at_end`) or as unread head ink at the end
    (`unread_ink_at_end`), asked again by ink. Two columns: exactly ONE of them reached -> that note (its member nearest the end); both or neither -> None
    (we do not choose). Unread ink: the bound note is reached and the unread ink is NOT -> that note; else None (cannot tell stands). Returns the new
    end, `{"head", "by_ink", "reach_spaces", "reached", "was"}`, or None."""
    from . import arc_claim as AC
    why = e.get("unbound")
    pts = _end_points(d, side)
    ok = usable or (lambda _k: True)

    def pick(col_keys: Sequence[str], r: Tuple[float, Optional[str], Optional[str]]) -> Optional[Dict[str, Any]]:
        by = {h["key"]: h for h in heads if not h.get("tip")}
        mem = [by[k] for k in dict.fromkeys(col_keys) if k in by and ok(k)]
        if not mem:
            return None
        ex, ey = pts[0]
        h = min(mem, key=lambda m: AC._to_head(m, ex, ey))
        return {"head": h["key"], "column": len(mem), "by_rule": True, "by_ink": True, "reach_spaces": round(r[0], 3), "reached": r[1],
                "reached_member": r[2], "was": why}
    if why == "two_columns_at_end":
        cols = [c if isinstance(c, list) else [c] for c in (e.get("candidates") or ())]
        rs = [min((ink_reach(k, heads, pts, sp, usable) for k in c), key=lambda t: t[0]) if c else (float("inf"), None, None) for c in cols]
        hit = [i for i, r in enumerate(rs) if r[0] <= INK_REACH_SPACES]
        # ... and the other note's ink stands clearly farther (the binder's own "about equally near" margin, `BIND_COLUMN_MARGIN_SPACES`, no new number):
        # a reach just inside the cut against one just outside it is still two notes about equally near (Litolff p11 run 26: 0.79 against 1.0)
        if len(hit) == 1 and all(r[0] - rs[hit[0]][0] >= AC.BIND_COLUMN_MARGIN_SPACES for i, r in enumerate(rs) if i != hit[0]):
            got = pick(cols[hit[0]], rs[hit[0]])
            if got is not None:
                got["was_two_columns"] = cols
            return got
        return None
    if why == AC.UNREAD_INK_AT_END:
        cands = e.get("candidates") or ()
        col = cands[0] if cands and isinstance(cands[0], list) else []
        if not col:
            return None
        r = min((ink_reach(k, heads, pts, sp, usable) for k in col), key=lambda t: t[0])
        xy = e.get("unread_xy")
        ub = None
        if xy:
            ub = min((u for u in (unread or ()) if not u.get("other_staff")), key=lambda u: abs(u["cx"] - xy[0]) + abs(u["cy"] - xy[1]), default=None)
        ru = min(AC._to_head(ub, x, y) for x, y in pts) / sp if ub is not None else 0.0
        if r[0] <= INK_REACH_SPACES and ru > INK_REACH_SPACES and ru - r[0] >= AC.BIND_COLUMN_MARGIN_SPACES:
            return pick(col, r)
        return None
    return None


#: ROADMAP 2.274 step 2 round 2 (cause b, measured on the develop pages before this was written; FINDINGS "2.274 step 2 round 2"): the tracker BRIDGES stretches of columns where it saw no
#: ink (a blanked head, a stem, a barline, a dynamic); a run's thinned points then jump in x. Across the 370 written runs the OFF file already wrote whole, the largest bridge is under 2
#: spaces but for one (3.1); a bridge of 2 spaces or more is where two arcs meet at a note (a tie A->B, then an arc B->C) or where a tail of the next arc was carried on through the
#: blanked head. NOT CONFIRMED beyond the pages measured; it only ever shortens a run or abstains, never invents an end.
GAP_SPLIT_SP = 2.0
#: (cause d, FINDINGS) the end stands more than this many spaces on the arc's own side of the head it bound to (Litolff p4 runs 1, 12, 20, 99: the head nearest the ink was never boxed and
#: the bound one stood 4.5-5.2 spaces off). A stem is 3.5 spaces long (Gould; `arc_claim.TIP_MAX_SPACES` 4.5): beyond 3 a stem tip does not reach it. NOT CONFIRMED beyond the develop pages;
#: it only ever DECLINES a binding.
END_BEYOND_HEAD_SPACES = 2.0          # arcs-r2 fix 3: 3.0 -> 2.0 (r2 "what would move it" (ii); a cup's end beside its head sits within ~1.5; Brahms p20 run 18 stands 2.5 below). Only declines.
#: (cause d, FINDINGS) the ink of an arc often ends PAST its note's centre (on the head's far edge, a stem): Brahms p5 runs 14 and 86 ended 1.1 spaces past the centre of the head they belong to, outside
#: 2.166's 0.8-space look-behind, so the binder took the next head 6.5-7.1 spaces on. A head up to this far behind the end is a candidate; the closest by distance still wins.
HEAD_BEHIND_END_SPACES = 1.6
#: (cause c) three or more members: the end's own height may name an inner member only within this many spaces of it.
INNER_MEMBER_DY_SPACES = 1.2
#: a stretch of tracked ink shorter than this (spaces of x) between a bridge and the run's end is a TAIL, not an arc: dropped. Two longer stretches are two arcs (each bound alone).
MIN_PIECE_SP = 3.0
#: arcs-r2 fix 2 (an end binds only a head the ink REACHES): an arc's end stands beside its note; a stem is 3.5 spaces (Gould) and `arc_claim.TIP_MAX_SPACES` 4.5. A head farther than this from the end
#: (measured on the 1552 written ends of the ten pages: 99% stand within 4.02) means the head the ink really ends at was never boxed (Litolff p13 run 80: 6.49; Brahms p11 run 3: 83). The end is
#: `end_far_from_head` (UNREAD, the old path keeps its arc). A number that only ever DECLINES a binding (CLAUDE 4: a cut-off tuned on two plates may only narrow).
#: ⚠️ ROADMAP 2.305 r6: RETIRED from the binder (Sean 2026-11-15: no reach number in the arc rule; `arc_claim.unread_head_ink` guards the failure it stood for). Still
#: read by `ownership.adjudicate_page_arc_binding`'s arcs-r2 fix 4 (`staff_ink_vs_owner`: which STAFF, when the run's own staff and the box owner disagree) -- not this lane's.
END_REACH_SPACES = 4.0
#: (arcs-r2 fix 1's `OWN_BAR_BEHIND_SPACES` own-bar window was retired by 2.305 r6: every note of the staff is a candidate, the closest wins, two about equally near abstain.)


def pieces_of(detail: Dict[str, Any], sp: float) -> List[Dict[str, Any]]:
    """The run cut at every bridged gap of `GAP_SPLIT_SP` or more; stretches under `MIN_PIECE_SP` wide are tails and dropped. Returns one detail per piece (`points`, `ends`,
    `core_ends` = where the piece's own ink stops; an end that is the run's own end keeps the run's `core_ends`), `piece` = its index and `trimmed` = whether anything was cut off.
    A run with no such gap returns itself unchanged (a list of one, `trimmed` False)."""
    pts = detail.get("points") or []
    if len(pts) < 2 or sp <= 0:
        return [dict(detail, piece=0, trimmed=False)]
    cuts = [i + 1 for i in range(len(pts) - 1) if pts[i + 1][0] - pts[i][0] >= GAP_SPLIT_SP * sp]
    if not cuts:
        return [dict(detail, piece=0, trimmed=False)]
    bounds = [0] + cuts + [len(pts)]
    segs = [pts[a:b] for a, b in zip(bounds, bounds[1:])]
    core = detail.get("core_ends") or [pts[0][:2], pts[-1][:2]]
    out: List[Dict[str, Any]] = []
    for k, seg in enumerate(segs):
        if (seg[-1][0] - seg[0][0]) < MIN_PIECE_SP * sp:
            continue
        left = core[0] if k == 0 else [seg[0][0], seg[0][1]]
        right = core[1] if k == len(segs) - 1 else [seg[-1][0], seg[-1][1]]
        out.append(dict(detail, points=seg, core_ends=[[float(left[0]), float(left[1])], [float(right[0]), float(right[1])]],
                        ends=[[float(left[0]), float(left[1]), 0.0], [float(right[0]), float(right[1]), 0.0]], piece=len(out), trimmed=True))
    return out


#: ROADMAP 2.305 r2 (two arcs MEETING at a head, Sean's r1 tile 8 "it's two ties"): how deep (spaces) the traced ink must dip toward its notes at a head between its
#: ends, below the higher hump on EACH side, to be two arcs, and how near (spaces) the dip must come to that head's box. Only ever CUTS a run (each piece binds alone,
#: or abstains); NOT CONFIRMED beyond the real case (Litolff p5 run 76), measured there: dip 0.9 sp, 0.2 sp from the head's top.
MEET_DIP_SPACES = 0.5
MEET_NEAR_HEAD_SPACES = 1.0
#: a meeting head stands at least this far (spaces) inside both ends of the run (an end at a head is the arc's own end, not a meeting)
MEET_INSIDE_SPACES = 2.0


def split_at_meeting_heads(piece: Dict[str, Any], heads: Sequence[Sequence[float]], sp: float) -> List[Dict[str, Any]]:
    """ROADMAP 2.305 r2 (page-facts: an arc is OVER its notes; two arcs that MEET at a note each end there -- 2.281). One traced run that dips to a notehead box
    BETWEEN its ends, the ink on both sides rising at least `MEET_DIP_SPACES` higher (a cap; lower, a cup), is two arcs meeting at that head: cut there, each piece's
    end at the dip (the head then binds both). `heads` = page boxes `[x0, y0, x1, y1]`. A run with no such head returns `[piece]` unchanged."""
    pts = piece.get("points") or []
    if len(pts) < 5 or sp <= 0:
        return [piece]
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    mid_y = ys[len(ys) // 2]
    cap = mid_y < (ys[0] + ys[-1]) / 2.0          # the ink bows UP: its notes are below it
    cuts = []
    for hb in heads:
        cx = (hb[0] + hb[2]) / 2.0
        if not (xs[0] + MEET_INSIDE_SPACES * sp < cx < xs[-1] - MEET_INSIDE_SPACES * sp):
            continue
        i = min(range(len(xs)), key=lambda k: abs(xs[k] - cx))
        if abs(xs[i] - cx) > 0.5 * sp:
            continue          # the trace has no point over this head
        yi = ys[i]
        near = (hb[1] - yi) if cap else (yi - hb[3])          # the ink stands just over (cap) / under (cup) the head
        if not (-0.5 * sp <= near <= MEET_NEAR_HEAD_SPACES * sp):
            continue
        left, right = ys[:i], ys[i + 1:]
        if not left or not right:
            continue
        if cap:
            depth = min(yi - min(left), yi - min(right))
        else:
            depth = min(max(left) - yi, max(right) - yi)
        if depth >= MEET_DIP_SPACES * sp:
            cuts.append(i)
    if not cuts:
        return [piece]
    cuts = sorted(set(cuts))
    bounds = [0] + cuts + [len(pts) - 1]
    core = piece.get("core_ends") or [pts[0][:2], pts[-1][:2]]
    out = []
    for k, (a, z) in enumerate(zip(bounds, bounds[1:])):
        seg = pts[a:z + 1]
        if (seg[-1][0] - seg[0][0]) < MIN_PIECE_SP * sp:
            continue
        left = core[0] if k == 0 else [seg[0][0], seg[0][1]]
        right = core[1] if k == len(bounds) - 2 else [seg[-1][0], seg[-1][1]]
        out.append(dict(piece, points=seg, core_ends=[[float(left[0]), float(left[1])], [float(right[0]), float(right[1])]],
                        ends=[[float(left[0]), float(left[1]), 0.0], [float(right[0]), float(right[1]), 0.0]], trimmed=True, met_at_head=True))
    return out or [piece]


def inked_witness(box: Sequence[float], runs_points: Sequence[Sequence[Sequence[float]]], sp: float, share: float) -> Optional[int]:
    """ROADMAP 2.305 r2 (`ownership._witness_by_ink`): the index of the ONE run that covers `share` of a detector arc box's INKED width (the union of every run's
    points inside the box, grown 0.5 sp in y), or None. An inked width under `MIN_PIECE_SP` spaces, or two runs that each cover the share, name none."""
    if sp <= 0:
        return None
    x0, y0, x1, y1 = box
    g = 0.5 * sp
    spans: Dict[int, Tuple[float, float]] = {}
    for i, pts in enumerate(runs_points):
        inside = [float(p[0]) for p in pts if x0 <= float(p[0]) <= x1 and y0 - g <= float(p[1]) <= y1 + g]
        if len(inside) >= 2:
            spans[i] = (min(inside), max(inside))
    if not spans:
        return None
    inked, cur = 0.0, None
    for a, z in sorted(spans.values()):
        if cur is None or a > cur[1]:
            if cur is not None:
                inked += cur[1] - cur[0]
            cur = [a, z]
        else:
            cur[1] = max(cur[1], z)
    inked += cur[1] - cur[0]
    if inked < MIN_PIECE_SP * sp:
        return None
    best = [i for i, (a, z) in spans.items() if (z - a) >= share * inked]
    return best[0] if len(best) == 1 else None


def curve_detail(run_detail: Dict[str, Any], sp: float) -> Optional[Dict[str, Any]]:
    """A `Q.SYSTEM_ARC`-shaped detail for one `Q.PAGE_ARC` run (`ownership._page_binding(page_run=...)` reads this shape): `space_page_px`, `x_left_page` / `y_left_page` /
    `x_right_page` / `y_right_page` (the run's two ends, left then right) and `trace` (`[x, y_top, y_bottom]`, one row per filed point). No `pieces`: a run is already one
    arc, so the 2.223 junction guard has nothing to test."""
    ends = run_detail.get("ends")
    pts = run_detail.get("points")
    if not ends or len(ends) != 2 or not pts or sp <= 0:
        return None
    (xl, yl, _tl), (xr, yr, _tr) = ends
    ext = {"x_left_ext": float(xl), "y_left_ext": float(yl), "x_right_ext": float(xr), "y_right_ext": float(yr)}          # r10: where the traced ink itself stops
    core = run_detail.get("core_ends")
    if core and len(core) == 2:
        # where the arc's OWN ink stops (step-1 `core_ends`), not where the extension carried the run on: the extension runs through marks that claim before an arc, up to 4 spaces,
        # and can pass the note the arc stops at (Brahms p0 staff 9: a short tie carried on through an augmentation dot into a ledger stub). Page-facts: an arc often stops SHORT
        # of its note and binds to the closest one -- measured from the ink's own end.
        (xl, yl), (xr, yr) = core
    half = 0.5 * float(run_detail.get("thickness_spaces") or 0.0) * sp
    return {"space_page_px": float(sp), "x_left_page": float(xl), "y_left_page": float(yl), "x_right_page": float(xr), "y_right_page": float(yr),
            "trace": [[float(x), float(y) - half, float(y) + half] for x, y in pts], **ext}


#: ROADMAP 2.305 r2: the gap (spaces) between the traced ink's near side and a head's near edge within which the ink LANDS on that head
LAND_GAP_SPACES = 0.5
#: ... and only in the outer share of the run's width at that end (the landing is the arc's END, not a note it passes over)
LAND_OUTER_SHARE = 0.25


def lands_on(trace: Sequence[Sequence[float]], heads: Sequence[Dict[str, Any]], hd: Dict[str, Any], sgn: int, ex: float, side: str, sp: float,
             usable: Any = None) -> Optional[Dict[str, Any]]:
    """The head INWARD of `hd` (the closest head to the end at `ex`; `sgn` -1 left end, +1 right) that the traced ink lands on within `HEAD_BEHIND_END_SPACES`
    of the end: a trace row over the head's x-span whose near side (bottom of a cap's stroke, top of a cup's) stands 0 .. `LAND_GAP_SPACES` from the head's
    near edge (top for a cap, bottom for a cup). The landed head nearest the end wins; None if there is none."""
    best = None
    # the end already sits OVER the closest head (a cap's end at or above its top, a cup's at or below its bottom, within `LAND_GAP_SPACES`): that head IS its
    # note and nothing is looked for (Brahms p0 run 21, Sean's P247: a long slur whose ink passes low over the 16th before its last note). Only an end that
    # stands beside or under the closest head -- not over it -- may have landed earlier (Litolff p5 run 76: the end 1.3 sp below the chord head's top).
    ey = None
    for t in trace:
        if ey is None or abs(float(t[0]) - ex) < abs(ey[0] - ex):
            ey = (float(t[0]), float(t[1]), float(t[2]))
    if ey is not None:
        over = (hd["cy"] - hd["h"] / 2.0) - ey[2] if side == "above" else ey[1] - (hd["cy"] + hd["h"] / 2.0)
        if over >= -LAND_GAP_SPACES * sp:
            return None
    xs = [float(t[0]) for t in trace]
    width = (max(xs) - min(xs)) if xs else 0.0
    for h in heads:
        if h["key"] == hd["key"] or h.get("tip") or (usable is not None and not usable(h["key"])):
            continue
        if not (0 < (hd["cx"] - h["cx"]) * sgn and 0 <= (ex - h["cx"]) * sgn <= min(HEAD_BEHIND_END_SPACES * sp, LAND_OUTER_SHARE * width)):
            continue          # only the run's OUTER quarter: a head further in is a note the arc passes over (r2: Litolff p15 runs 60, 66, two-note slurs)
        hx0, hx1 = h["cx"] - h["w"] / 2.0, h["cx"] + h["w"] / 2.0
        top, bot = h["cy"] - h["h"] / 2.0, h["cy"] + h["h"] / 2.0
        for t in trace:
            if not (hx0 <= float(t[0]) <= hx1):
                continue
            gap = (top - float(t[2])) if side == "above" else (float(t[1]) - bot)
            if 0 <= gap <= LAND_GAP_SPACES * sp:
                if best is None or abs(h["cx"] - ex) < abs(best["cx"] - ex):
                    best = h
                break
    return best


def ink_ends_on(d: Dict[str, Any], side: str, cands: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.305 r10. THE RULE (page-facts, Sean 2026-11-15: "an arc ends at the notes standing where its ink ends"): where two notes are about equally
    near the arc's own end, but the traced ink itself runs ON INTO one of them -- its last traced point lies inside that note's head, and inside no other
    candidate's -- the ink ends at that note. NEVER: a point inside two heads, or inside none (then "we don't choose" stands). No number.
    Evidence: Sean's r9 tile 9, Brahms p0 staff 12: the slur 12/0/4 -> 12/1/1 whose ink runs onto 12/1/1's head (and the next tie starts there) abstained
    `two_columns_at_end` against the chord 12/1/2 / 12/1/15 to its left."""
    x, y = d.get("x_%s_ext" % side), d.get("y_%s_ext" % side)
    if x is None or y is None:
        return None
    inside = [h for h in cands if abs(float(h["cx"]) - float(x)) <= float(h["w"]) / 2.0 and abs(float(h["cy"]) - float(y)) <= float(h["h"]) / 2.0]
    keys = {h.get("head_id") or h["key"] for h in inside}
    return inside[0] if len(keys) == 1 else None


def far_side_ends(b: Dict[str, Any], d: Dict[str, Any], box_of: Any) -> List[str]:
    """ROADMAP 2.305 r9. THE RULE (page-facts, Sean: "an arc is OVER its notes"; a cup's notes stand above its ends, a cap's below): the ends of one bound run
    (`b`, the binder's result on one staff) that name no note of that staff because its notes stand on the arc's FAR side. An end is such an end when
      * the binder found the closest note wholly on the far side (`head_on_the_arcs_far_side`), or
      * the binder found a note of the neighbouring staff on the arc's OWN side nearer than any of this staff's (`nearer_note_on_another_staff`), or
      * the end was left as "half of another arc" (`continues_in_another_curve`) and the closest note it names stands wholly on the far side of the end
        (a cup: the head's top below the end; a cap: its foot above it).
    NEVER: an end whose closest note stands beside or on the notes' side of the end (a cup under its own note) -- that is this staff's end. No number.
    Where BOTH ends are far-side ends the caller binds the run once more on the neighbouring staff on the arc's own side (`adjudicate_page_arc_binding`).
    Evidence: Brahms p0 staff 5 cups (Sean's ties P184, P186, P195) lie nearer staff 6, whose notes stand below them; staff 9 caps (his slurs P205, P209)
    lie nearer staff 8. `box_of(key)` -> the head's page box `[x0, y0, x1, y1]` or None."""
    side = b.get("side")
    far = [s_ for s_ in ("left", "right") if (b.get(s_) or {}).get("unbound") == "head_on_the_arcs_far_side"]
    if len(far) == 2 or side not in ("above", "below"):
        return far
    for s_ in ("left", "right"):
        e_ = b.get(s_) or {}
        if s_ in far:
            continue
        if e_.get("unbound") == "nearer_note_on_another_staff":
            far.append(s_)
            continue
        if e_.get("unbound") != "continues_in_another_curve" or not e_.get("candidates"):
            continue
        hb = box_of(e_["candidates"][0])
        ey = d.get("y_%s_page" % s_)
        if hb and len(hb) == 4 and ey is not None and (
                (side == "below" and float(hb[1]) > float(ey)) or (side == "above" and float(hb[3]) < float(ey))):
            far.append(s_)
    return far


def closest_binder(others: Dict[str, Sequence[Tuple[float, float]]], cells: Optional[Dict[Any, Tuple[float, float]]] = None):
    """The `binder` `ownership._page_binding(page_run=...)` takes. Each end binds by Sean's rule (2026-11-15; `arc_claim._bind_end_by_rule`, ROADMAP 2.305 r6): the CLOSEST
    usable note of the staff, measured from where the ink ends, in either direction and with no reach number; two columns about equally near abstain; head-shaped ink no
    reader has read standing at the end at least about as near -> `unread_ink_at_end`; the half of an arc (`others`: the facing ends of the staff's other runs) stays
    unbound. An end with NO usable head ahead of it anywhere on the staff is the SYSTEM'S EDGE, whatever stands behind it: the arc may run on to the next system, so it is
    not ended at the last note (`{"edge": True}`; EXPORT may join it). `cells` is no longer read (r2's own-bar window retired by r6); kept for the caller's signature."""
    from . import arc_claim as AC
    from .arcs_system import ANCHOR_DY_SPACES, ANCHOR_IN_SPACES, ANCHOR_OUT_SPACES

    def binder(heads: List[Dict[str, Any]], sp: float, usable: Any, end_pitch: bool, alt: Any, d: Dict[str, Any],
               unread: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
        by_ink = end_by_ink_enabled()          # ROADMAP 2.338
        side = AC.curve_side(d.get("trace"), sp)
        b = {"left": None, "right": None, "side": side, "by_rule": True}
        for s_, sgn, xk, yk in (("left", -1, "x_left_page", "y_left_page"), ("right", +1, "x_right_page", "y_right_page")):
            ex = float(d[xk])
            if not any((h["cx"] - ex) * sgn > -HEAD_BEHIND_END_SPACES * sp and (usable is None or usable(h["key"])) for h in heads) \
                    and not any((u["cx"] - ex) * sgn > -HEAD_BEHIND_END_SPACES * sp for u in (unread or ()) if not u.get("other_staff")):
                # r8 (Sean's r7b tile 4, Brahms p0 `0/0/9/0/7`: a real note ADJUDICATE narrowed under a word's claim): note-like ink nobody could read standing
                # ahead of the end is a note there, not the system's edge -- the end says "cannot tell", never "edge" (which hands it to the join across systems)
                b[s_] = {"edge": True}
                continue
            # ROADMAP 2.305 r6 (`arc_claim._bind_end_by_rule`; Sean 2026-11-15, "An arc ends at the notes standing where its ink ends"): the closest note of the
            # staff in either direction, with no look-behind, own-bar window or reach number (r2's `OWN_BAR_BEHIND_SPACES` window and `END_REACH_SPACES` reach,
            # both retired here); unread head ink at the end -> cannot tell. The edge test above, the landing, chord and far-side tests below are unchanged.
            b[s_] = AC.bind_end(ex, float(d[yk]), sgn, heads, sp, side, usable, end_pitch, others=others.get(s_), by_rule=True, unread=unread,
                                behind_spaces=HEAD_BEHIND_END_SPACES)          # (`behind_spaces`: 2.281's meeting test only, never which note)
            if b[s_].get("unbound") == "two_columns_at_end" and side in ("above", "below"):
                # two notes about equally near the traced end, and the ink LANDS on one of them (r2's landing rule, Sean's r1 tile 8: the tracker carried the end on
                # past the note the ink came down onto): the ink's own end is at that note -- the closest of the notes standing where its ink ends (Litolff p5 run 76
                # piece 1, Sean's r2 tile 7, a tie). Otherwise the abstention stands.
                cand = {k for c in (b[s_].get("candidates") or ()) for k in (c if isinstance(c, list) else [c])}
                by_k = {h["key"]: h for h in heads}
                outer = max((by_k[k] for k in cand if k in by_k), key=lambda h: (h["cx"] - ex) * sgn, default=None)
                land = lands_on(d.get("trace") or (), heads, outer, sgn, ex, side, sp, usable) if outer is not None else None
                if land is not None and land["key"] in cand:
                    b[s_] = {"head": land["key"], "column": 1, "by_rule": True, "lands_on": True, "was_two_columns": sorted(cand),
                             "distance_spaces": round(AC._to_head(land, ex, float(d[yk])) / sp, 3)}
                else:
                    on = ink_ends_on(d, s_, [by_k[k] for k in cand if k in by_k])
                    if on is not None:
                        b[s_] = {"head": on["key"], "column": 1, "by_rule": True, "ink_ends_on": True, "was_two_columns": sorted(cand),
                                 "distance_spaces": round(AC._to_head(on, ex, float(d[yk])) / sp, 3)}
            if by_ink and b[s_].get("unbound") in ("two_columns_at_end", AC.UNREAD_INK_AT_END):
                # ROADMAP 2.338: the refusal asked again by ink -- exactly one note's head or stem ink reached (two columns), or the note reached and the
                # unread ink not (unread ink at the end); otherwise the refusal stands
                got = settle_by_ink(b[s_], heads, d, s_, sp, usable, unread)
                if got is not None:
                    b[s_] = got
            hd = next((h for h in heads if h["key"] == b[s_].get("head")), None)
            if hd is not None and side in ("above", "below") and not hd.get("tip") and not b[s_].get("via_stem_tip") and not b[s_].get("by_ink"):
                # ROADMAP 2.305 r2 (Sean's r1 tile 8, "it goes one extra note too far"; page-facts: an arc ends AT its note): the traced ink LANDS on a head
                # INWARD of the one closest to its end -- it passes within `LAND_GAP_SPACES` of that head's near edge (a cap over its top, a cup under its
                # bottom), within the look-behind of the end -- and the tracker then carried the end on to the next note. The head the ink lands on is the end's.
                land = lands_on(d.get("trace") or (), heads, hd, sgn, ex, side, sp, usable)
                if land is not None:
                    b[s_] = dict(b[s_], head=land["key"], lands_on=True, was=hd["key"])
                    hd = land
            if hd is not None:
                ey = float(d[yk])
                # round 2 (cause c): a CHORD end. Page-facts: an arc is OVER its notes, and of stacked arcs the nearer is the tie -- the arc's side names the member: a cap (`above`) ends on the
                # TOP head of the chord, a cup (`below`) on the BOTTOM one. Measured: the end's own height picked the wrong member where the ink end rises or falls past the chord
                # (stacked arcs; a tail). Two members: the arc's side decides. Three or more: the end's own height decides only where it stands within `INNER_MEMBER_DY_SPACES` of that member,
                # else the end abstains (the middle of a stack is not read from the side).
                col_ = {}
                # ROADMAP 2.305: a head boxed twice is ONE member (`head_id`, 2.290's one identity, set by `ownership._page_head_groups`); the bound box stands for its head
                col_[hd.get("head_id") or hd["key"]] = hd
                for h in heads:
                    if h.get("tip") or abs(h["cx"] - hd["cx"]) > 0.5 * max(h["w"], hd["w"]) or (usable is not None and not usable(h["key"])):
                        continue
                    col_.setdefault(h.get("head_id") or h["key"], h)
                col_ = list(col_.values())
                if len(col_) > 1 and side in ("above", "below") and not b[s_].get("via_stem_tip") and not hd.get("tip"):
                    outer = min(col_, key=lambda h: h["cy"]) if side == "above" else max(col_, key=lambda h: h["cy"])
                    b[s_]["chord"] = len(col_)
                    b[s_]["outer_on_side"] = outer["key"] == hd["key"]
                    if outer["key"] != hd["key"]:
                        if len(col_) == 2:
                            b[s_] = dict(b[s_], head=outer["key"], chord_by_side=True, was=hd["key"], distance_spaces=round((abs(outer["cx"] - ex) + abs(outer["cy"] - ey)) / sp, 3))
                            hd = outer
                        elif abs(hd["cy"] - ey) > INNER_MEMBER_DY_SPACES * sp:
                            b[s_] = {"unbound": "chord_member_unclear", "candidates": [h["key"] for h in col_], "margin_spaces": round(INNER_MEMBER_DY_SPACES - abs(hd["cy"] - ey) / sp, 3)}
                            continue
                out_by = (hd["cx"] - ex) * sgn
                b[s_]["out_by_spaces"] = round(out_by / sp, 2)          # round 2 (cause d): how far past the ink's own end the bound head stands (negative: behind it)
                # round 2 (cause d): the end stands far on the arc's own side of the head it bound to: a nearer head was never boxed (or is another member). An arc's end sits beside its note;
                # a stem's tip (the 2.75 rule) is a candidate in its own right and is exempt.
                beyond = ((ey - hd["cy"]) if side == "below" else (hd["cy"] - ey) if side == "above" else abs(ey - hd["cy"])) / sp
                if beyond > END_BEYOND_HEAD_SPACES and not hd.get("tip") and not b[s_].get("via_stem_tip"):
                    reach = ink_reach(hd["key"], heads, _end_points(d, s_), sp, usable) if by_ink else None
                    if reach is not None and reach[0] <= INK_REACH_SPACES:
                        # ROADMAP 2.338: far from the head's box centre, but the ink reaches the note -- its stem (a slur at the stem side), its head's ink,
                        # or a member of its chord nobody read (the chord is reached; `adjudicate_page_arc_binding` never lets such an end make a tie)
                        b[s_] = dict(b[s_], by_ink=True, reach_spaces=round(reach[0], 3), reached=reach[1], reached_member=reach[2], was="end_far_beyond_head",
                                     beyond_spaces=round(beyond, 3))
                    else:
                        b[s_] = {"unbound": "end_far_beyond_head", "candidates": [hd["key"]], "margin_spaces": round(END_BEYOND_HEAD_SPACES - beyond, 3)}
                        if reach is not None:
                            b[s_]["reach_spaces"] = round(reach[0], 3) if reach[0] != float("inf") else None
                        continue
                # ROADMAP 2.305 (page-facts: an arc is OVER its notes -- a cap stands above the heads it joins, a cup below): the head stands on the arc's FAR side of
                # its end, as far as `END_BEYOND_HEAD_SPACES` (r2's own number, only declines): the ink is not this head's arc (Litolff p5 run 99: a cap over the lower
                # staff bound to the upper staff's heads 5 sp above its ends). A stem tip, which stands on the far side by design, is exempt.
                if side in ("above", "below") and -beyond > END_BEYOND_HEAD_SPACES and not hd.get("tip") and not b[s_].get("via_stem_tip"):
                    b[s_] = {"unbound": "head_on_the_arcs_far_side", "candidates": [hd["key"]], "margin_spaces": round(END_BEYOND_HEAD_SPACES + beyond, 3)}
                    continue
                if out_by > ANCHOR_OUT_SPACES * sp or out_by < -ANCHOR_IN_SPACES * sp or abs(hd["cy"] - float(d[yk])) > ANCHOR_DY_SPACES * sp:
                    b[s_]["outside_window"] = True          # the head stands outside 2.166's window: the end "stops short" (or overshoots) and the closest-note rule bound it
        if b["left"].get("head") is not None and b["left"].get("head") == b["right"].get("head"):
            b["left"] = b["right"] = {"unbound": "one_head_both_ends", "candidates": [b["left"]["head"]], "margin_spaces": None}
        return b
    return binder


def facing_ends(runs: Sequence[Dict[str, Any]], mine: int, staff: Sequence[int]) -> Dict[str, List[Tuple[float, float]]]:
    """For `closest_binder`: `left` = the RIGHT ends of the other runs of this staff (an arc ending near this one's left end), `right` = their LEFT ends -- exactly the
    shape 2.271's `_closest_sides` builds from the detector curves."""
    out: Dict[str, List[Tuple[float, float]]] = {"left": [], "right": []}
    for i, r in enumerate(runs):
        if i == mine or list(r.get("staff") or ()) != list(staff):
            continue
        e = r.get("ends")
        if not e or len(e) != 2:
            continue
        out["left"].append((float(e[1][0]), float(e[1][1])))
        out["right"].append((float(e[0][0]), float(e[0][1])))
    return out


# ───────────────────────────── EXPORT side: read the verdict ─────────────────────────────

def plan_of(details: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """The export's plan from the standing verdicts' `detail["runs"]` (one verdict per page): `written` (`[{kind, start, stop, witnesses, ...}]`), `replaced` (the detector
    arc-box subjects a written run replaces: a box all of whose witnessed runs are written), `shared_kept` (boxes that witness a written and an unwritten run: kept),
    `edges` (the ends a join across systems may pick up) and the counts by status."""
    runs: List[Dict[str, Any]] = []
    for d in details:
        runs.extend(d.get("runs") or ())
    box_runs: Dict[str, List[Dict[str, Any]]] = {}
    for r in runs:
        for w in r.get("witnesses") or ():
            box_runs.setdefault(str(w), []).append(r)
    written = [r for r in runs if r.get("status") == WRITTEN]
    replaced: Set[str] = set()
    shared_kept: Set[str] = set()

    def settled(r):
        # ROADMAP 2.305 r3 (ink is read and claimed ONCE; Sean's r2 tile 10, Litolff p5: boxes 5/0/5/3/0 and 4/11 witnessed both pieces of a cut run -- one written as a
        # tie, one abstained -- so they were "shared" and their old-path slur was written over the tie, one note too late): a box whose ink the page pass has
        # BOUND (a written run, or a run whose two heads are bound and whose kind is unread) writes nothing through the fallback, whatever else it witnesses.
        # MEASURED (2305 r3, the 8 pages): the wider rule -- a box of ANY decided run, abstentions included -- removed 43 fallback arcs a plate and 11 of Sean's
        # 98 Brahms p0 arcs that were right; a box that only witnesses abstained runs keeps its old arc until the fallback is retired (Sean's call).
        return r.get("status") == WRITTEN or bool(r.get("kind_unread"))

    for box, rs in box_runs.items():
        if any(settled(r) for r in rs):
            replaced.add(box)
    edges = [r for r in runs if r.get("status") == ABSTAINED and r.get("edge")]
    counts: Dict[str, int] = {}
    for r in runs:
        counts[str(r.get("status"))] = counts.get(str(r.get("status")), 0) + 1
        if r.get("kind_unread"):
            counts["kind_unread"] = counts.get("kind_unread", 0) + 1
    return {"written": written, "replaced": replaced, "shared_kept": shared_kept, "edges": edges, "counts": counts, "runs": runs}
