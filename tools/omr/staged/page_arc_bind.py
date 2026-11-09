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
END_BEYOND_HEAD_SPACES = 3.0
#: (cause d, FINDINGS) the ink of an arc often ends PAST its note's centre (on the head's far edge, a stem): Brahms p5 runs 14 and 86 ended 1.1 spaces past the centre of the head they belong to, outside
#: 2.166's 0.8-space look-behind, so the binder took the next head 6.5-7.1 spaces on. A head up to this far behind the end is a candidate; the closest by distance still wins.
HEAD_BEHIND_END_SPACES = 1.6
#: (cause c) three or more members: the end's own height may name an inner member only within this many spaces of it.
INNER_MEMBER_DY_SPACES = 1.2
#: a stretch of tracked ink shorter than this (spaces of x) between a bridge and the run's end is a TAIL, not an arc: dropped. Two longer stretches are two arcs (each bound alone).
MIN_PIECE_SP = 3.0


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


def closest_binder(others: Dict[str, Sequence[Tuple[float, float]]]):
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
            b[s_] = AC.bind_end(float(d[xk]), float(d[yk]), sgn, heads, sp, side, usable, end_pitch, True, others.get(s_), closest_only=True,
                                behind_spaces=HEAD_BEHIND_END_SPACES)
            hd = next((h for h in heads if h["key"] == b[s_].get("head")), None)
            if hd is not None:
                ey = float(d[yk])
                # round 2 (cause c): a CHORD end. Page-facts: an arc is OVER its notes, and of stacked arcs the nearer is the tie -- the arc's side names the member: a cap (`above`) ends on the
                # TOP head of the chord, a cup (`below`) on the BOTTOM one. Measured: the end's own height picked the wrong member where the ink end rises or falls past the chord
                # (stacked arcs; a tail). Two members: the arc's side decides. Three or more: the end's own height decides only where it stands within `INNER_MEMBER_DY_SPACES` of that member,
                # else the end abstains (the middle of a stack is not read from the side).
                col_ = {}
                for h in heads:
                    if h.get("tip") or abs(h["cx"] - hd["cx"]) > 0.5 * max(h["w"], hd["w"]) or (usable is not None and not usable(h["key"])):
                        continue
                    col_.setdefault(h["key"], h)
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
                    b[s_] = {"unbound": "end_far_beyond_head", "candidates": [hd["key"]], "margin_spaces": round(END_BEYOND_HEAD_SPACES - beyond, 3)}
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
    for box, rs in box_runs.items():
        if any(r.get("status") == WRITTEN for r in rs):
            if all(r.get("status") == WRITTEN for r in rs):
                replaced.add(box)
            else:
                shared_kept.add(box)
    edges = [r for r in runs if r.get("status") == ABSTAINED and r.get("edge")]
    counts: Dict[str, int] = {}
    for r in runs:
        counts[str(r.get("status"))] = counts.get(str(r.get("status")), 0) + 1
    return {"written": written, "replaced": replaced, "shared_kept": shared_kept, "edges": edges, "counts": counts, "runs": runs}
