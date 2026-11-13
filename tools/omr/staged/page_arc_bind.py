"""ROADMAP 2.274 step 2 -- THE WITNESSED PAGE-INK ARC RUNS BOUND TO NOTES AND WRITTEN, ONE ARC EACH. PATH: STAGED. PURE helpers: no pipeline import, no row filed,
nothing decided by itself. The callers are `adjudicators/ownership.adjudicate_page_arc_binding` (ADJUDICATE, flag ON) and `export._pair_arcs` / `_place_arcs`
(EXPORT, flag ON). Registered in `reach.NOT_A_STAGE`.

Sean 2026-11-08 ("Try 1"): take ONLY the page-ink runs a detector arc box agrees with (WITNESSED: 0 fakes of 20 seeded on the round-4 hold-out), bind each run's two ends to
notes, and write each as ONE arc. A run no detector box witnesses (about 4.8 fakes a page, step 1) is NOT written in this step.

`OMR_PAGE_ARC_WRITE` (default OFF, allow-list). It also turns the step-1 reader on in GATHER (`page_arcs.enabled`): the flag needs the `Q.PAGE_ARC` rows. OFF, every
stage is what it was: the decision files nothing, EXPORT reads nothing, and the exported file is byte-identical to main's (tests + the gates in FINDINGS).

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


def write_enabled() -> bool:
    """`OMR_PAGE_ARC_WRITE`, default OFF (allow-list)."""
    return _on(ENV_WRITE)


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
END_REACH_SPACES = 4.0
#: arcs-r2 fix 1 (an end binds where the ink is): a head in the END'S OWN BAR (the cell its ink end stands in) up to this far behind the end is a candidate beside the closest head outward across a
#: barline; two columns about equally near then abstain (`two_columns_at_end`, the binder's own margin) instead of the outward head silently winning (Litolff p5 run 104: the chord before the barline
#: 1.44 sp out, the half note the ink starts over 1.8 behind). It only ever adds a rival, so it can only turn a binding into an abstention or leave it. (2.166's `ANCHOR_OUT_SPACES`, no new number.)
OWN_BAR_BEHIND_SPACES = 2.5


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
    core = run_detail.get("core_ends")
    if core and len(core) == 2:
        # where the arc's OWN ink stops (step-1 `core_ends`), not where the extension carried the run on: the extension runs through marks that claim before an arc, up to 4 spaces,
        # and can pass the note the arc stops at (Brahms p0 staff 9: a short tie carried on through an augmentation dot into a ledger stub). Page-facts: an arc often stops SHORT
        # of its note and binds to the closest one -- measured from the ink's own end.
        (xl, yl), (xr, yr) = core
    half = 0.5 * float(run_detail.get("thickness_spaces") or 0.0) * sp
    return {"space_page_px": float(sp), "x_left_page": float(xl), "y_left_page": float(yl), "x_right_page": float(xr), "y_right_page": float(yr),
            "trace": [[float(x), float(y) - half, float(y) + half] for x, y in pts]}


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


def closest_binder(others: Dict[str, Sequence[Tuple[float, float]]], cells: Optional[Dict[Any, Tuple[float, float]]] = None):
    """The `binder` `ownership._page_binding(page_run=...)` takes. Each end binds to the CLOSEST usable head (`arc_claim.bind_end(closest_only=True)`, 2.271's rule with no window: a run's end
    can stand a little PAST its note: heads up to 2.166's own `ANCHOR_IN_SPACES` behind the end are candidates too), refusing the half of an arc (`others`: the facing
    ends of the staff's other runs) and two columns about equally near. An end with NO usable head ahead of it anywhere on the staff (the 2.223 window's own edge test) is the
    SYSTEM'S EDGE, whatever stands behind it: the arc may run on to the next system, so it is not ended at the last note (`{"edge": True}`; EXPORT may join it)."""
    from . import arc_claim as AC
    from .arcs_system import ANCHOR_DY_SPACES, ANCHOR_IN_SPACES, ANCHOR_OUT_SPACES

    def binder(heads: List[Dict[str, Any]], sp: float, usable: Any, end_pitch: bool, alt: Any, d: Dict[str, Any]) -> Dict[str, Any]:
        side = AC.curve_side(d.get("trace"), sp)
        b = {"left": None, "right": None, "side": side}
        for s_, sgn, xk, yk in (("left", -1, "x_left_page", "y_left_page"), ("right", +1, "x_right_page", "y_right_page")):
            ex = float(d[xk])
            if not any((h["cx"] - ex) * sgn > -HEAD_BEHIND_END_SPACES * sp and (usable is None or usable(h["key"])) for h in heads):
                b[s_] = {"edge": True}
                continue
            usable_ = usable
            behind_ = HEAD_BEHIND_END_SPACES
            if cells:
                # arcs-r2 fix 1: heads of the end's own bar join the candidates up to OWN_BAR_BEHIND_SPACES behind it; every other head keeps the 1.6 look-behind
                # the bar the ink REACHES: the outermost TRACED point (the trace crosses a barline for a tie across it; Brahms p11 runs 33/37: own ink starts 7 px after the barline, the traced ink before it)
                tx = [float(t[0]) for t in (d.get("trace") or ())]
                ink_x = (min(tx) if sgn < 0 else max(tx)) if tx else ex
                own = next((c for c, (cx0, cx1) in cells.items() if cx0 <= ink_x <= cx1), None)
                if own is not None:
                    behind_ = max(HEAD_BEHIND_END_SPACES, OWN_BAR_BEHIND_SPACES)
                    by_key = {h["key"]: h for h in heads}

                    def usable_(k, _u=usable, _own=own, _sgn=sgn, _ex=ex, _by=by_key):
                        h = _by.get(k)
                        if h is not None and (h["cx"] - _ex) * _sgn < -HEAD_BEHIND_END_SPACES * sp and h.get("cell") != _own:
                            return False
                        return _u is None or _u(k)
            b[s_] = AC.bind_end(float(d[xk]), float(d[yk]), sgn, heads, sp, side, usable_, end_pitch, True, others.get(s_), closest_only=True,
                                behind_spaces=behind_)
            hd = next((h for h in heads if h["key"] == b[s_].get("head")), None)
            if hd is not None and side in ("above", "below") and not hd.get("tip") and not b[s_].get("via_stem_tip"):
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
                if out_by > END_REACH_SPACES * sp:
                    b[s_] = {"unbound": "end_far_from_head", "candidates": [hd["key"]], "margin_spaces": round(END_REACH_SPACES - out_by / sp, 3)}
                    continue
                b[s_]["out_by_spaces"] = round(out_by / sp, 2)          # round 2 (cause d): how far past the ink's own end the bound head stands (negative: behind it)
                # round 2 (cause d): the end stands far on the arc's own side of the head it bound to: a nearer head was never boxed (or is another member). An arc's end sits beside its note;
                # a stem's tip (the 2.75 rule) is a candidate in its own right and is exempt.
                beyond = ((ey - hd["cy"]) if side == "below" else (hd["cy"] - ey) if side == "above" else abs(ey - hd["cy"])) / sp
                if beyond > END_BEYOND_HEAD_SPACES and not hd.get("tip") and not b[s_].get("via_stem_tip"):
                    b[s_] = {"unbound": "end_far_beyond_head", "candidates": [hd["key"]], "margin_spaces": round(END_BEYOND_HEAD_SPACES - beyond, 3)}
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
        # bound OR abstained on writes nothing through the fallback. Every run with a witness was decided here (written / abstained / kind unread).
        return r.get("status") in (WRITTEN, ABSTAINED)

    for box, rs in box_runs.items():
        if any(settled(r) for r in rs):
            if all(settled(r) for r in rs):
                replaced.add(box)
            else:
                shared_kept.add(box)
    edges = [r for r in runs if r.get("status") == ABSTAINED and r.get("edge")]
    counts: Dict[str, int] = {}
    for r in runs:
        counts[str(r.get("status"))] = counts.get(str(r.get("status")), 0) + 1
        if r.get("kind_unread"):
            counts["kind_unread"] = counts.get("kind_unread", 0) + 1
    return {"written": written, "replaced": replaced, "shared_kept": shared_kept, "edges": edges, "counts": counts, "runs": runs}
