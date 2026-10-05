#!/usr/bin/env python3
"""lane-ledger-edge-census (2026-10-04) -- MEASURE ONLY.

How many of round 8's Litolff far-head misses are "a printed ledger
touching the head's top or bottom edge, dropped as the head's own outline"?

Nothing in `tools/` is edited. The reader's intermediate results are read
by wrapping three module-level functions of `ledger_grid` at run time
(`_rung_row_clears_box`, `collapse_head_edge_rungs_to_middle`,
`measure_ledger_rungs`) and by REPLAYING `derive_far_head_step`'s loop in
this file (checked equal to the real function on every head). A single
"undo" (one drop reversed) is a state flag the wrappers consult; with no
undo and no recording the wrappers are pass-throughs.

    python3 benchmarks/omr-local-staff-2026-09/edge_census.py [--json out.json]

Controls (printed first): tallies with recording OFF and ON equal
`score_four_causes_cd.py`'s (Litolff 25/14/5, Brahms 11/0/0), and the
replayed derive equals the real one on every head.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

_ORIG_CLEARS = lg._rung_row_clears_box
_ORIG_COLLAPSE = lg.collapse_head_edge_rungs_to_middle
_ORIG_MEASURE = lg.measure_ledger_rungs
_ORIG_DERIVE = lg.derive_far_head_step

# ---------------------------------------------------------------- state
ST: Dict[str, Any] = dict(
    record=False,      # recording on/off
    main=False,        # inside the subject's own measure call (not a partner's)
    box=None,          # subject's box (x0,y0,x1,y1)
    trace=None,        # dict being filled
    undo=None,         # None | ("clears", y) | ("collapse",) | ("pop", k)
                       #  | ("blanket", set(rule names))
)


def _near(a: float, b: float, tol: float = 0.75) -> bool:
    return abs(a - b) <= tol


def _rel_numbers(y, box, spacing, sign):
    """(rn, rf, rm): signed distance in staff spaces of y from the box's
    near edge, far edge and middle; + = farther from the staff."""
    x0, y0, x1, y1 = box
    near_y, far_y = (y1, y0) if sign < 0 else (y0, y1)
    return (sign * (y - near_y) / spacing, sign * (y - far_y) / spacing,
            sign * (y - (y0 + y1) / 2.0) / spacing)


def _near_band(y, box, spacing, sign):
    """Edge-band, near side: rung within 0.5 sp of the box edge nearest the
    staff and farther than 0.30 sp from the box middle (those are 'through'
    candidates, not edge candidates)."""
    rn, rf, rm = _rel_numbers(y, box, spacing, sign)
    return abs(rm) > 0.30 and -0.5 <= rn <= 0.5


def _is_edge_related(y: float, box, spacing: float, sign: float) -> Optional[str]:
    """Relation of a rung row y to the head's own box: 'near' (rung within
    0.35 sp of, or up to 0.45 sp inside, the box edge nearest the staff),
    'far' (same at the edge farthest from the staff), 'mid' (within 0.25 sp
    of the box middle), else None. Tolerances are this script's and are
    printed with the table."""
    x0, y0, x1, y1 = box
    if sign < 0:   # head above the staff: near edge is the BOTTOM (y1)
        near_y, far_y = y1, y0
    else:
        near_y, far_y = y0, y1
    mid = (y0 + y1) / 2.0
    if abs(y - mid) <= 0.25 * spacing:
        return "mid"
    # inward from the near edge, outward past it
    rn = sign * (y - near_y) / spacing    # + = farther from staff than near edge
    rf = sign * (y - far_y) / spacing     # + = beyond the far edge
    if -0.35 <= rn <= 0.45:
        return "near"
    if -0.45 <= rf <= 0.35:
        return "far"
    return None


# --------------------------------------------------------------- wrappers
def _clears(img_gray, y, x, head_box_x, spacing, exclude_boxes=None):
    res = _ORIG_CLEARS(img_gray, y, x, head_box_x, spacing, exclude_boxes)
    if ST["record"] and ST["main"] and ST["trace"] is not None:
        ST["trace"]["clears"].append(dict(y=float(y), passed=bool(res)))
    u = ST["undo"]
    if not res and u is not None and ST["main"]:
        if u[0] == "clears" and _near(u[1], y):
            return True
        if u[0] == "blanket" and "clears_edge" in u[1]:
            box, sp = ST["box"], spacing
            sign = -1.0 if (box[1] + box[3]) / 2.0 < ST["top"] else 1.0
            if _is_edge_related(y, box, sp, sign) in ("near", "far"):
                return True
    return res


def _collapse(rungs_y, sign, head_box, img_gray, spacing, exclude_boxes=None,
              head_center_y=None):
    out = _ORIG_COLLAPSE(rungs_y, sign, head_box, img_gray, spacing,
                         exclude_boxes, head_center_y)
    if ST["record"] and ST["main"] and ST["trace"] is not None and rungs_y:
        ST["trace"]["collapse"].append(dict(
            before=[float(v) for v in rungs_y], after=[float(v) for v in out]))
    u = ST["undo"]
    if (u is not None and ST["main"] and list(out) != list(rungs_y)
            and (u[0] == "collapse"
                 or (u[0] == "blanket" and "collapse" in u[1]))):
        return list(rungs_y)
    return out


def _measure(img_gray, staff_line_ys, x, head_y=None, exclude_boxes=None,
             head_box_x=None, head_box_y=None, collapse_edges_box=None,
             head_center_y=None, restore_masked_staff_side_rungs=False):
    main = collapse_edges_box is not None
    prev_main = ST["main"]
    ST["main"] = main
    if main:
        ST["box"] = tuple(collapse_edges_box)
        ys = sorted(float(v) for v in staff_line_ys)
        ST["top"], ST["bottom"] = ys[0], ys[-1]
    u = ST["undo"]
    if main and u is not None and (
            u[0] == "excl" or (u[0] == "blanket" and "excl" in u[1])):
        exclude_boxes = None      # undo: no other-head / accidental masking
    try:
        res = _ORIG_MEASURE(
            img_gray, staff_line_ys, x, head_y=head_y,
            exclude_boxes=exclude_boxes, head_box_x=head_box_x,
            head_box_y=head_box_y, collapse_edges_box=collapse_edges_box,
            head_center_y=head_center_y,
            restore_masked_staff_side_rungs=restore_masked_staff_side_rungs)
        if main and u is not None and u[0] == "blanket" and (
                "inject_near" in u[1] or "inject_band" in u[1]):
            res = _inject_edge_band(img_gray, staff_line_ys, x, head_y,
                                    head_box_x, collapse_edges_box, res,
                                    near_only="inject_near" in u[1])
        return res
    finally:
        ST["main"] = prev_main


def _inject_edge_band(img_gray, staff_line_ys, x, head_y, head_box_x, box,
                      res, near_only):
    """UNDO of the other-head/accidental masking for ONE class of candidate:
    rungs the bare ink offers (no masking) that sit in the head's near-edge
    band (rn in [-0.5, 0.5]; `inject_band` also the far-edge band) and have
    no kept rung within 0.35 sp are put back into the kept list."""
    ys = sorted(float(v) for v in staff_line_ys)
    sp = (ys[-1] - ys[0]) / 4.0
    sign = -1.0 if (box[1] + box[3]) / 2.0 < ys[0] else 1.0
    side = "above" if sign < 0 else "below"
    bare = _ORIG_MEASURE(img_gray, ys, x, head_y=head_y, exclude_boxes=None,
                         head_box_x=None).get(side, [])
    kept = list(res.get(side, []))
    for y in bare:
        if any(abs(y - k) <= 0.35 * sp for k in kept):
            continue
        rn, rf, rm = _rel_numbers(y, box, sp, sign)
        if abs(rm) <= 0.30:
            continue
        if -0.5 <= rn <= 0.5 or (not near_only and -0.5 <= rf <= 0.5):
            kept.append(float(y))
    kept.sort(key=lambda v: sign * v)
    out = dict(res)
    out[side] = kept
    return out


def derive_replay(rungs_y, edge_y, sign, head_near_y, spacing, img_gray=None,
                  head_box=None, exclude_boxes=None, head_center_y=None,
                  undo=None, trace=None):
    """`derive_far_head_step`'s loop, replayed (verified equal to the real
    one with undo=None). `undo` = ("pop", k) keeps the k-th rung (0-based,
    nearest-staff-first) when the real loop would pop it, counting it as a
    real ledger the head sits beyond (offset 2n+1, 'space'); or
    ("blanket", {"pop_edge"}) for every pop of a near-edge-related rung."""
    if not rungs_y or spacing <= 0:
        return dict(offset=None, kind=None, reason="no_rungs")
    evidenced = lg.head_middle_rung_evidence(
        img_gray, head_box, spacing, exclude_boxes, head_center_y)
    if trace is not None:
        trace["evidenced"] = bool(evidenced)
        trace["pops"] = []
    remaining = list(rungs_y)
    while remaining:
        last = remaining[-1]
        k = len(remaining) - 1
        half = 2 * len(remaining)
        gap = (sign * (head_near_y - last)) / spacing
        if gap <= -lg.TOUCH_TOL_SPACES:
            if evidenced:
                return dict(offset=half, kind="line", reason="through")
            rel = _is_edge_related(last, head_box, spacing, sign) if head_box else None
            if (undo is not None and undo[0] == "blanket"
                    and "pop_mid_through" in undo[1] and head_box is not None
                    and abs(_rel_numbers(last, head_box, spacing, sign)[2]) <= 0.30):
                return dict(offset=half, kind="line",
                            reason="UNDO pop: counted as a ledger through the head")
            if trace is not None:
                trace["pops"].append(dict(k=k, y=float(last), gap=float(gap),
                                          rel=rel))
            if undo is not None and (
                    (undo[0] == "pop" and undo[1] == k)
                    or (undo[0] == "blanket" and "pop_edge" in undo[1]
                        and rel in ("near", "far"))
                    or (undo[0] == "blanket" and "pop_near" in undo[1]
                        and head_box is not None
                        and _near_band(last, head_box, spacing, sign))):
                return dict(offset=half + 1, kind="space",
                            reason="UNDO pop: counted as ledger, head beyond it")
            remaining.pop()
            continue
        if evidenced:
            return dict(offset=half + 2, kind="line", reason="line beyond")
        return dict(offset=half + 1, kind="space", reason="space beyond")
    return dict(offset=None, kind=None, reason="no_rung_before_the_head")


def _derive(rungs_y, edge_y, sign, head_near_y, spacing, img_gray=None,
            head_box=None, exclude_boxes=None, head_center_y=None,
            near_edge_ledgers=False):
    real = _ORIG_DERIVE(rungs_y, edge_y, sign, head_near_y, spacing, img_gray,
                        head_box, exclude_boxes, head_center_y,
                        near_edge_ledgers=near_edge_ledgers)
    if not ST["record"] and ST["undo"] is None:
        return real
    tr = ST["trace"]
    undo = ST["undo"]
    u = undo if (undo and undo[0] in ("pop", "blanket")) else None
    rep = derive_replay(rungs_y, edge_y, sign, head_near_y, spacing, img_gray,
                        head_box, exclude_boxes, head_center_y, undo=u,
                        trace=tr if ST["record"] else None)
    if tr is not None and ST["record"]:
        tr["final_ladder"] = [float(v) for v in rungs_y]
        tr["derive_real"] = real
        tr["derive_replay_equal"] = (rep["offset"] == real["offset"]) \
            if u is None else None
        tr["near_y"] = float(head_near_y)
    if u is not None:
        return rep
    return real


def install():
    lg._rung_row_clears_box = _clears
    lg.collapse_head_edge_rungs_to_middle = _collapse
    lg.measure_ledger_rungs = _measure
    lg.derive_far_head_step = _derive


def uninstall():
    lg._rung_row_clears_box = _ORIG_CLEARS
    lg.collapse_head_edge_rungs_to_middle = _ORIG_COLLAPSE
    lg.measure_ledger_rungs = _ORIG_MEASURE
    lg.derive_far_head_step = _ORIG_DERIVE


# ---------------------------------------------------------------- driver
def load_heads(doc_id: str) -> List[Dict[str, Any]]:
    """`score.score_doc`'s own setup and filters, reproduced field for field
    (so the population is the one the 25/14/5 and 11/0/0 are counted on)."""
    loaded = ts.load_doc(doc_id)
    rows = score._far_head_rows(doc_id, loaded)
    rec = loaded["rec"]
    pages = score.PageCache(loaded["cfg"])
    boxes_by_page = score._notehead_boxes_by_page(rec)
    acc_by_page = score._accidental_boxes_by_page(rec)
    heads = []
    for row in rows:
        if row["subject"] == "glyph/1/0/10/14/1":
            continue
        truth_p = row["truth_pitches"]
        if not truth_p:
            continue
        staff_key = row["staff_key"]
        clef_v = rec.value(Q.CLEF, staff_key)
        if clef_v is None:
            continue
        truth_pos = set(score.truth_positions(truth_p, str(clef_v)))
        if not truth_pos or not row["page_box"]:
            continue
        line_rows = rec.obs(Q.STAFF_LINES, staff_key)
        if not line_rows:
            continue
        global_lines = [float(y) for y in line_rows[-1]["value"]]
        gray = pages.get(row["page"])
        lines = score.frame_lines_for_head(gray, global_lines, row["page_box"])
        heads.append(dict(
            doc=doc_id, subject=row["subject"], page=row["page"],
            box=tuple(row["page_box"]), gray=gray, lines=lines,
            boxes=boxes_by_page.get(row["page"], []),
            acc=acc_by_page.get(row["page"], []),
            truth=sorted(truth_pos), geom_pos=int(round(row["raw_pos"])),
        ))
    return heads


def read(h: Dict[str, Any], undo=None, record=False):
    ST.update(record=record, undo=undo, main=False, box=None)
    ST["trace"] = (dict(clears=[], collapse=[]) if record else None)
    pos, reason = score.reader_absolute_position(
        h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
        page_accidental_boxes=h["acc"], four_causes_cd=True)
    tr = ST["trace"]
    ST.update(record=False, undo=None, trace=None)
    return pos, reason, tr


def verdict(pos, truth):
    return "abstain" if pos is None else ("right" if pos in truth else "wrong")


def tally(vs):
    return {k: vs.count(k) for k in ("right", "wrong", "abstain")}


def stage0_candidates(h):
    """The walk with NO other-head exclusion, no clears-box filter, no
    collapse -- every rung the ink alone offers at this column."""
    x0, y0, x1, y1 = h["box"]
    ys = sorted(float(v) for v in h["lines"])
    cy = (y0 + y1) / 2.0
    side = "above" if cy < ys[0] else "below"
    r = _ORIG_MEASURE(h["gray"], ys, (x0 + x1) / 2.0, head_y=cy,
                      exclude_boxes=None, head_box_x=None)
    return side, [float(v) for v in r.get(side, [])]


def census_row(h, base_pos, base_reason, tr):
    x0, y0, x1, y1 = h["box"]
    ys = sorted(float(v) for v in h["lines"])
    spacing = (ys[-1] - ys[0]) / 4.0
    top, bottom = ys[0], ys[-1]
    cy = (y0 + y1) / 2.0
    side, sign = ("above", -1.0) if cy < top else ("below", 1.0)
    edge = top if sign < 0 else bottom
    on_side = (lambda y: (y < top) if sign < 0 else (y > bottom))
    drops = []
    for c in tr["clears"]:
        if on_side(c["y"]) and not c["passed"]:
            drops.append(dict(rule="clears_box", y=c["y"],
                              rel=_is_edge_related(c["y"], h["box"], spacing, sign)))
    for c in tr["collapse"]:
        if not any(on_side(v) for v in c["before"] + c["after"]):
            continue
        gone = [v for v in c["before"] if not any(_near(v, a, 0.01) for a in c["after"])]
        for v in gone:
            drops.append(dict(rule="collapse_edges", y=v,
                              rel=_is_edge_related(v, h["box"], spacing, sign)))
    for p in tr.get("pops", []):
        drops.append(dict(rule="derive_pop", y=p["y"], k=p["k"], gap=p["gap"],
                          rel=p["rel"]))
    # other-head / accidental exclusion: rungs the bare ink offers that are
    # absent from the walk's own (post-exclusion) candidate list
    s0_side, s0 = stage0_candidates(h)
    walked = [c["y"] for c in tr["clears"] if on_side(c["y"])]
    for y in s0:
        if not any(_near(y, w, 0.35 * spacing) for w in walked):
            drops.append(dict(rule="exclusion_or_cascade", y=y,
                              rel=_is_edge_related(y, h["box"], spacing, sign)))
    for dr in drops:
        dr["rn"], dr["rf"], dr["rm"] = _rel_numbers(dr["y"], h["box"], spacing, sign)
    n_ref = [(abs(t - (0 if sign < 0 else 8))) for t in h["truth"]]
    return dict(
        subject=h["subject"], doc=h["doc"], side=side, spacing=spacing,
        box=list(h["box"]), edge=edge, truth=h["truth"], answer=base_pos,
        reason=base_reason, stage0=s0,
        walked=walked, final_ladder=tr.get("final_ladder"),
        evidenced=tr.get("evidenced"), drops=drops, ref_halfsteps_out=n_ref,
        derive_replay_equal=tr.get("derive_replay_equal"),
    )


# Causes for the heads with NO edge-band drop, named from the crops
# (out/print/ledgers/edge_census/) -- manual, one line each.
OTHER_CAUSE = {
    "glyph/1/0/10/7/1": "through-ledger sits 0.19 sp from the box's near edge (box rides high): "
                        "counted as the ledger BEFORE the head, then a jut at box middle -> one too far",
    "glyph/3/0/0/2/4": "missed middle ledger: 2.15 sp gap between found rungs (no ink found there)",
    "glyph/3/0/0/7/1": "5 rungs found for 4 ledgers: one thick ledger counted twice "
                       "(merge-close / half-spacing dedupe are off)",
    "glyph/3/0/0/7/2": "rungs BEYOND the head (neighbour heads' ledgers) counted: derive's "
                       "through-branch takes the last rung however far past the head",
    "glyph/3/0/7/2/4": "through-line not evidenced at the box-middle row (rung 0.26 sp above it)",
    "glyph/3/0/7/3/1": "through-line not evidenced at the box-middle row -> popped",
    "glyph/3/0/7/3/2": "through-line not evidenced at the box-middle row -> popped",
    "glyph/3/0/7/3/4": "through-ledger dropped by other-head masking AND not evidenced (two faults)",
    "glyph/3/0/7/4/3": "through-ledger dropped by clears-box / masking AND not evidenced (two faults)",
    "glyph/3/0/7/6/1": "through-line not evidenced at the box-middle row -> popped",
    "glyph/3/0/7/7/0": "through-line not evidenced at the box-middle row -> popped",
    "glyph/3/0/8/6/10": "through-line not evidenced at the box-middle row -> popped",
    "glyph/3/1/0/6/0": "first ledger dropped by clears-box AND through-line not evidenced (two faults)",
}


def _in_edge_band(d):
    """A dropped candidate 'touches a head edge': within 0.5 sp of the box edge
    nearest the staff (rn) or farthest from it (rf), and farther than 0.30 sp
    from the box middle (nearer than that it is a THROUGH candidate)."""
    return abs(d["rm"]) > 0.30 and (-0.5 <= d["rn"] <= 0.5 or -0.5 <= d["rf"] <= 0.5)


def classify(rows, blanket):
    """E / E? / other for every non-right head; for every right head, the
    edge-band drops and every single undo that breaks it."""
    out = {}
    for doc, rs in rows.items():
        for r in rs:
            band = [d for d in r["drops"] if _in_edge_band(d)]
            band_u = [next((u for u in r["undo"]
                            if u["rule"] == d["rule"] and abs(u["y"] - d["y"]) < 1.5), None)
                      for d in band]
            entry = dict(doc=doc, subject=r["subject"], verdict=r["verdict"],
                         answer=r["answer"], truth=r["truth"],
                         edge_drops=[dict(rule=d["rule"], y=d["y"], rn=d["rn"],
                                          rf=d["rf"], rm=d["rm"]) for d in band],
                         edge_undos=[dict(pos=u["pos"], verdict=u["verdict"],
                                          rule=u["rule"]) if u else None
                                     for u in band_u])
            if r["verdict"] != "right":
                if any(u and u["verdict"] == "right" for u in band_u):
                    entry["cls"] = "E"
                elif band:
                    entry["cls"] = "E?"
                else:
                    entry["cls"] = "other"
                    entry["cause"] = OTHER_CAUSE.get(r["subject"], "?")
                thr = blanket["pop_mid_through"][doc]["pos"].get(r["subject"])
                entry["through_undo_pos"] = thr
                entry["through_undo_right"] = (thr in r["truth"]) if thr is not None else False
            else:
                entry["breaks"] = [dict(rule=u["rule"], y=u["y"], pos=u["pos"])
                                   for u in r["undo"] if u["verdict"] != "right"]
                entry["cls"] = "right"
            out[r["subject"]] = entry
    return out


def report(rows, blanket, classes):
    from collections import Counter
    wrong = [c for c in classes.values() if c["cls"] in ("E", "E?", "other")]
    print("\n=== the non-right heads ===")
    print(f"{'head':20} {'v':6} {'cls':5} {'r8':>5} {'undo':>6} {'ref':>5}  cause / dropping rule")
    order = {"E": 0, "E?": 1, "other": 2}
    for c in sorted(wrong, key=lambda c: (order[c["cls"]], c["subject"])):
        und = "-"
        why = c.get("cause", "")
        if c["edge_drops"]:
            und = ",".join(str(u["pos"]) for u in c["edge_undos"] if u)
            why = "; ".join(f"{d['rule']} y={d['y']:.0f} (near{d['rn']:+.2f} far{d['rf']:+.2f} mid{d['rm']:+.2f})"
                            for d in c["edge_drops"])
        if c["cls"] == "other" and c.get("through_undo_right"):
            why += f"   [through-undo -> {c['through_undo_pos']} = ref]"
        print(f"{c['subject']:20} {c['verdict'][:6]:6} {c['cls']:5} {str(c['answer']):>5} "
              f"{und:>6} {str(c['truth']):>5}  {why}")
    print("counts:", dict(Counter(c["cls"] for c in wrong)), "of", len(wrong))
    print("\n=== right heads: edge-band drops, and every undo that breaks one ===")
    for c in classes.values():
        if c["cls"] == "right" and (c["edge_drops"] or c["breaks"]):
            print(c["subject"], "edge_drops:",
                  [(d["rule"], round(d["y"]), round(d["rn"], 2), round(d["rf"], 2)) for d in c["edge_drops"]],
                  "breaks:", c["breaks"])
    nright = sum(1 for c in classes.values() if c["cls"] == "right")
    broken_band = [c["subject"] for c in classes.values() if c["cls"] == "right" and any(
        u and u["verdict"] != "right" for u in c["edge_undos"])]
    broken_any = [c["subject"] for c in classes.values() if c["cls"] == "right" and c["breaks"]]
    print(f"right heads (both docs) = {nright}; with an edge-band drop whose undo breaks them: "
          f"{len(broken_band)} {broken_band}; broken by ANY single undo: {len(broken_any)} {broken_any}")


def main() -> int:
    out_json = None
    if "--json" in sys.argv:
        out_json = sys.argv[sys.argv.index("--json") + 1]
    docs = list(ts.DOCS)
    heads = {d: load_heads(d) for d in docs}

    # CONTROL 1: recording OFF (wrappers not installed) == shipped tallies
    base = {}
    for d in docs:
        vs = []
        for h in heads[d]:
            pos, _r, _t = read(h)
            vs.append(verdict(pos, h["truth"]))
        base[d] = tally(vs)
        print(f"control A (no wrappers) {d}: {base[d]} n={len(vs)}")

    install()
    rows: Dict[str, List[Dict[str, Any]]] = {}
    try:
        # CONTROL 2: wrappers installed, recording ON == control A
        for d in docs:
            rows[d] = []
            vs = []
            for h in heads[d]:
                pos, reason, tr = read(h, record=True)
                vs.append(verdict(pos, h["truth"]))
                r = census_row(h, pos, reason, tr)
                r["verdict"] = verdict(pos, h["truth"])
                rows[d].append(r)
            t = tally(vs)
            print(f"control B (wrappers+recording) {d}: {t} "
                  f"{'== A' if t == base[d] else '!= A  <-- BROKEN'}")
        eq = [r["derive_replay_equal"] for d in docs for r in rows[d]
              if r["derive_replay_equal"] is not None]
        print(f"replayed derive == real derive on {sum(eq)}/{len(eq)} heads")

        # per-head single-drop undo
        for d in docs:
            for h, r in zip(heads[d], rows[d]):
                r["undo"] = []
                for dr in r["drops"]:
                    if dr["rule"] == "exclusion_or_cascade":
                        u = ("excl",)
                    elif dr["rule"] == "clears_box":
                        u = ("clears", dr["y"])
                    elif dr["rule"] == "collapse_edges":
                        u = ("collapse",)
                    else:
                        u = ("pop", dr["k"])
                    pos, _rs, _t = read(h, undo=u)
                    r["undo"].append(dict(
                        rule=dr["rule"], y=dr["y"], rel=dr["rel"], pos=pos,
                        verdict=verdict(pos, h["truth"])))
        # blanket undo of a rule class, over the whole population
        blanket_sets = {
            "pop_near": {"pop_near"},
            "pop_edge": {"pop_edge"},
            "clears_edge": {"clears_edge"},
            "collapse": {"collapse"},
            "excl": {"excl"},
            "inject_near": {"inject_near"},
            "inject_band": {"inject_band"},
            "pop_mid_through": {"pop_mid_through"},
            "near_fix": {"pop_near", "inject_near"},
            "all_edge": {"pop_edge", "clears_edge", "collapse"},
        }
        blanket = {}
        for name, rs in blanket_sets.items():
            blanket[name] = {}
            for d in docs:
                vs, flips, poss = [], [], {}
                for h, r in zip(heads[d], rows[d]):
                    pos, _rs, _t = read(h, undo=("blanket", rs))
                    v = verdict(pos, h["truth"])
                    vs.append(v)
                    poss[h["subject"]] = pos
                    if v != r["verdict"]:
                        flips.append((h["subject"], r["verdict"], v, pos))
                blanket[name][d] = dict(tally=tally(vs), flips=flips, pos=poss)
    finally:
        uninstall()

    classes = classify(rows, blanket)
    report(rows, blanket, classes)
    if out_json:
        Path(out_json).write_text(json.dumps(
            dict(rows=rows, blanket=blanket, classes=classes), indent=1,
            default=str))
    for name, per in blanket.items():
        print(f"\nBLANKET undo '{name}':")
        for d, v in per.items():
            print(f"  {d}: {v['tally']}")
            for f in v["flips"]:
                print(f"     {f[0]}  {f[1]} -> {f[2]} (pos {f[3]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
