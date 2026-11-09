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
    (`ownership._bind_detail`, the body of 2.223's `_page_binding`, MOVED not rewritten). The detector's class is a prior and is not an input (`arc_class` is empty);
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


def curve_detail(run_detail: Dict[str, Any], sp: float) -> Optional[Dict[str, Any]]:
    """A `Q.SYSTEM_ARC`-shaped detail for one `Q.PAGE_ARC` run (`ownership._bind_detail` reads this shape): `space_page_px`, `x_left_page` / `y_left_page` /
    `x_right_page` / `y_right_page` (the run's two ends, left then right) and `trace` (`[x, y_top, y_bottom]`, one row per filed point). No `pieces`: a run is already one
    arc, so the 2.223 junction guard has nothing to test."""
    ends = run_detail.get("ends")
    pts = run_detail.get("points")
    if not ends or len(ends) != 2 or not pts or sp <= 0:
        return None
    (xl, yl, _tl), (xr, yr, _tr) = ends
    half = 0.5 * float(run_detail.get("thickness_spaces") or 0.0) * sp
    return {"space_page_px": float(sp), "x_left_page": float(xl), "y_left_page": float(yl), "x_right_page": float(xr), "y_right_page": float(yr),
            "trace": [[float(x), float(y) - half, float(y) + half] for x, y in pts]}


def closest_binder(others: Dict[str, Sequence[Tuple[float, float]]]):
    """The `binder` `ownership._bind_detail` takes: 2.166's window first (`arc_claim.bind_curve`, unchanged), then, for an end that still has no head, the CLOSEST usable head
    beyond it (`bind_end(closest_ok=True)`, 2.271's rule), refusing the half of an arc (`others`: the facing ends of the staff's other runs)."""
    from . import arc_claim as AC

    def binder(heads: List[Dict[str, Any]], sp: float, usable: Any, end_pitch: bool, alt: Any, d: Dict[str, Any]) -> Dict[str, Any]:
        b = AC.bind_curve(d, heads, sp, usable, by_height=end_pitch, alt_ends=alt)
        for side, sgn, xk, yk in (("left", -1, "x_left_page", "y_left_page"), ("right", +1, "x_right_page", "y_right_page")):
            cur = b[side]
            if cur.get("unbound") != "no_head_at_end":
                continue
            got = AC.bind_end(float(d[xk]), float(d[yk]), sgn, heads, sp, b.get("side"), usable, end_pitch, True, others.get(side))
            if got.get("head") is not None or got.get("unbound") == "continues_in_another_curve":
                b[side] = got
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
