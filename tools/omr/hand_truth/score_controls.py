"""D2: the scorer's controls, each of which can FAIL (CLAUDE.md rule 7; plan Phase D2).

    python3 -m tools.omr.hand_truth.score --controls --page <page.json> [--derive]

A scorer that has only ever printed a good number has proved nothing. Each control here builds a
SYNTHETIC record from the truth boxes themselves -- through the real ``Log``, round-tripped through
JSON, and read back through ``readout.run_from_result`` and the scorer's own adapter, so a field the
adapter drops is invisible here exactly as it would be on a real record -- and states what the
scorer MUST say about it:

``self_score``      the truth scored against itself is perfect: every family recall = precision = 1,
                    every judged owner / position / clef / key / meter right, no frame complaint.
``owner_shift``     the same record against a truth whose owners are all moved ONE staff over:
                    owner accuracy collapses (and the position and match numbers do not move, so
                    the collapse is the owner's, not the matcher's).
``position_shift``  a record whose every head reads one step off: position accuracy collapses and
                    owner accuracy does not move.
``header_wrong``    a record reading the wrong clef, key and meter scores all-wrong on each.
``frame_*``         a record whose boxes (or cells, or dpi) are off by a fraction of a staff space is
                    REFUSED by the frame control; the unshifted record passes it.
``no_overlap``      a record whose boxes are all moved off their marks matches nothing.
``drop`` / ``add``  a record missing 10% of its boxes loses recall and keeps precision; a record with
                    spurious boxes added loses precision and keeps recall -- so neither number is
                    a function of the other.
``refusal``         a family no cell was inspected for is REFUSED, not scored as zero -- with its
                    positive control, the same family in an inspected cell, scored.

A control that passes is only trusted because ``tests/test_hand_truth_score.py`` also runs each one
against a scorer with the matching bug seeded in (an owner comparison that always says "right", a
matcher that never matches, a frame check that never trips) and requires it to go RED.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from tools.omr.hand_truth import score as S
from tools.omr.hand_truth.store import PageTruth
from tools.omr.staged import readout as RO
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

#: A measuring instrument, not a consumer -- see ``score.DERIVED_CHECK`` (``wiring`` matches ``.owner`` as a
#: read of the detail key ``own``).
DERIVED_CHECK = True

SYNTH_WEIGHTS = "/synthetic/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"


def _verdict(log: Log, subject, quantity, outcome, value, decider, reason) -> None:
    log.record(Verdict(id=log._next_id("vrd"), subject=subject, quantity=quantity, outcome=outcome,
                       value=value, decider=decider, reason=reason))


def synthetic_result(page: PageTruth, items: Sequence[S.TruthItem], *, dx: float = 0.0, dy: float = 0.0,
                     cell_dx: float = 0.0, dpi: Optional[int] = None, drop: Sequence[int] = (),
                     spurious: Sequence[Tuple[str, S.Rect, int, int, int]] = (),
                     headers: bool = True, position_shift: int = 0, header_wrong: bool = False,
                     refile: Optional[Dict[int, Tuple[int, bool]]] = None) -> Dict[str, Any]:
    """A record that read exactly what the truth says, optionally with the stated faults.

    ``dx, dy``  shift every glyph box (page px); ``cell_dx`` shifts every cell box; ``dpi`` overrides the
    record's gather dpi; ``drop`` omits truth item indices; ``spurious`` adds ``(class, rect, system,
    staff, cell)`` boxes the truth has no mark under; ``position_shift`` moves every notehead position that
    many steps; ``header_wrong`` writes a different clef, key and meter than the truth's; ``refile`` files a
    truth item's glyph in ANOTHER staff's cell: ``{idx: (staff, with_verdict)}`` -- with a ``glyph_owner``
    verdict naming the true owner (a contest resolved) or without one (a head filed on the wrong staff that
    nobody contested).

    A head on its own staff gets NO ``glyph_owner`` verdict, as in a real record (the verdict's domain is
    the contested population); only a head filed elsewhere gets one, naming its owner.
    """
    log = Log()
    cells = {c.id: c for c in page.cells if c.kind == "measure" and c.system is not None}
    per_cell: Dict[str, int] = {}
    for c in cells.values():
        sub = R.cell(0, c.system, c.staff, c.measure or 0)
        x0, y0, x1, y1 = c.rect
        log.observe(sub, Q.CELL_BOX, [x0 + cell_dx, y0, x1 + cell_dx, y1], reader=READERS.GEOMETRY,
                    frame=f"cell:{c.measure}")

    def put(cls: str, rect, system: int, staff: int, cell: int, it: Optional[S.TruthItem]) -> None:
        g = R.glyph(0, system, staff, cell, per_cell.setdefault(f"{system}.{staff}.{cell}", 0))
        per_cell[f"{system}.{staff}.{cell}"] += 1
        x0, y0, x1, y1 = rect
        rect = [x0 + dx, y0 + dy, x1 + dx, y1 + dy]
        log.observe(g, Q.GLYPH_BOX, [cls, 0.0, 0.0, rect[2] - rect[0], rect[3] - rect[1]],
                    reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9, bbox_page_px=rect)
        if it is None or it.family != "notehead":
            return
        truth_staff, _ = S.truth_owner(it)
        truth_staff = truth_staff or (system, staff)
        with_verdict = (refile or {}).get(it.idx, (None, True))[1]
        if with_verdict and tuple(truth_staff) != (system, staff):
            _verdict(log, g, Q.GLYPH_OWNER, Outcome.DECIDED, R.staff(0, truth_staff[0], truth_staff[1]).to_key(),
                     "adjudicate_glyph_owner", "ledger")
        pos, _ = S.truth_position_top(it)
        if pos is not None:
            log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(pos + position_shift), reader=READERS.GEOMETRY,
                        frame=f"cell:{cell}")

    dropped = set(drop)
    for it in items:
        c = cells.get(it.cell_id or "")
        if c is None or it.idx in dropped:
            continue
        filed = (refile or {}).get(it.idx)
        put(it.cls, it.rect, c.system, filed[0] if filed else c.staff, c.measure or 0, it)
    for cls, rect, system, staff, cell in spurious:
        put(cls, rect, system, staff, cell, None)

    if headers:
        meter_done: set = set()
        for system, staff in sorted({(c.system, c.staff) for c in cells.values()}):
            t = S.truth_header(page, items, system, staff)
            if not t.get("scored"):
                continue
            st = R.staff(0, system, staff)
            if t.get("clef"):
                clef = ("bass" if t["clef"] == "treble" else "treble") if header_wrong else t["clef"]
                _verdict(log, st, Q.CLEF, Outcome.DECIDED, clef, "adjudicate_clef", "scored")
            if t.get("key_fifths") is not None:
                _verdict(log, st, Q.KEY_SIGNATURE, Outcome.DECIDED,
                         t["key_fifths"] + (1 if header_wrong else 0), "adjudicate_key_signature", "markers")
            m = t.get("meter") or {}
            if m.get("printed") and m.get("numerator") and m.get("denominator") and system not in meter_done:
                meter_done.add(system)
                num = m["numerator"] + (1 if header_wrong else 0)
                value = {"numerator": num, "denominator": m["denominator"],
                         "segments": [{"numerator": num, "denominator": m["denominator"], "from_cell": 0}]}
                ct = (t.get("cautionary") or {}).get("meter") or {}
                if ct.get("printed") and ct.get("numerator") and ct.get("denominator"):
                    value["cautionary"] = {"numerator": ct["numerator"] + (1 if header_wrong else 0),
                                           "denominator": ct["denominator"], "from_cell": 99}
                _verdict(log, R.system(0, system), Q.METER, Outcome.DECIDED, value, "adjudicate_meter", "read")
    return json.loads(json.dumps({
        "record": log.to_json(), "stopped_after": "adjudicate",
        "weight_routing": {"weights": SYNTH_WEIGHTS},
        "provenance": {"commit": "synthetic", "dirty": False, "settings": {
            "env_overrides": {}, "args": {"pdf": "synthetic", "pages": str(page.pdf_page_index),
                                          "dpi": dpi if dpi is not None else page.dpi,
                                          "weights": "auto", "through": "adjudicate", "conf": 0.25}}},
    }, default=str))


def run_of(result: Dict[str, Any]) -> RO.Run:
    return RO.run_from_result(result)


# ── the controls ─────────────────────────────────────────────────────────────


def _families_perfect(rep: Dict[str, Any]) -> Tuple[bool, List[str]]:
    bad = []
    for fam, d in rep["families"].items():
        if d["status"] != "scored" or not d["gather"]["truth"]:
            continue
        for view in ("gather", "adjudicate"):
            v = d[view]
            if v["recall"] != 1.0 or v["precision"] != 1.0:
                bad.append(f"{fam}/{view} recall {v['recall']} precision {v['precision']}")
    return not bad, bad


def _judged_all_right(block: Dict[str, Any]) -> bool:
    return block["wrong"] == 0 and block["right"] > 0


def control_self_score(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    items = S.truth_items(page, derive=derive)
    rep = S.score(page, run_of(synthetic_result(page, items)), derive=derive, items=items, trained_cells=())
    fams_ok, bad = _families_perfect(rep)
    n = rep["noteheads"]["all"]
    h = rep["headers"]["summary"]
    ok = (fams_ok and rep["frame_control"]["ok"] and n["owner"]["wrong"] == 0 and n["position"]["wrong"] == 0
          and n["missed"] == 0 and all(h[k].get("wrong", 0) == 0 for k in h))
    return {"name": "self_score", "passes": ok,
            "expect": "every family recall = precision = 1; no wrong owner/position/clef/key/meter; frame OK",
            "got": {"imperfect_families": bad, "frame_ok": rep["frame_control"]["ok"],
                    "frame_reasons": rep["frame_control"]["reasons"], "notehead_missed": n["missed"],
                    "owner": {k: n["owner"][k] for k in ("right", "wrong", "abstained", "no_truth")},
                    "position": {k: n["position"][k] for k in ("right", "wrong", "abstained", "no_truth")},
                    "headers": {k: {a: b for a, b in v.items() if a != "accuracy_of_judged"}
                                for k, v in h.items()}}}


def shifted_owner_items(items: Sequence[S.TruthItem], by: int = 1) -> List[S.TruthItem]:
    """The truth with every owner moved ``by`` staves over (Sean's and the derived reference alike)."""
    out = []
    for it in items:
        o = replace(it)
        if o.owner is not None:
            o.owner = (o.owner[0], o.owner[1] + by)
        if o.derived_owner is not None:
            o.derived_owner = (o.derived_owner[0], o.derived_owner[1] + by)
        out.append(o)
    return out


def control_owner_shift(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    items = S.truth_items(page, derive=derive)
    run = run_of(synthetic_result(page, items))
    good = S.score(page, run, derive=derive, items=items, trained_cells=())["noteheads"]["all"]
    bad_rep = S.score(page, run, derive=derive, items=shifted_owner_items(items, 1), trained_cells=())
    bad = bad_rep["noteheads"]["all"]
    base, shifted = good["owner"]["accuracy_of_judged"], bad["owner"]["accuracy_of_judged"]
    same_match = (good["matched"] == bad["matched"]
                  and good["position"]["accuracy_of_judged"] == bad["position"]["accuracy_of_judged"])
    ok = base is not None and shifted is not None and base >= 0.99 and shifted <= 0.05 and same_match
    return {"name": "owner_shift", "passes": ok,
            "expect": "owner accuracy ~1.0 unshifted, ~0 after the truth is moved one staff; matches and "
                      "positions unchanged",
            "got": {"owner_accuracy_unshifted": base, "owner_accuracy_shifted": shifted,
                    "matched_unchanged": same_match}}


def control_position_shift(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """A record whose every head reads one step off: position accuracy collapses, owner does not move."""
    items = S.truth_items(page, derive=derive)
    good = S.score(page, run_of(synthetic_result(page, items)), derive=derive, items=items,
                   trained_cells=())["noteheads"]["all"]
    bad = S.score(page, run_of(synthetic_result(page, items, position_shift=1)), derive=derive, items=items,
                  trained_cells=())["noteheads"]["all"]
    base, shifted = good["position"]["accuracy_of_judged"], bad["position"]["accuracy_of_judged"]
    owner_same = good["owner"]["accuracy_of_judged"] == bad["owner"]["accuracy_of_judged"]
    ok = base is not None and shifted is not None and base >= 0.99 and shifted <= 0.05 and owner_same
    return {"name": "position_shift", "passes": ok,
            "expect": "position accuracy ~1.0 as read, ~0 when every head reads one step off; owner unchanged",
            "got": {"position_accuracy_exact": base, "position_accuracy_one_step_off": shifted,
                    "owner_unchanged": owner_same}}


def control_header_wrong(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """A record that reads the wrong clef, key and meter: every judged one is WRONG, none right."""
    items = S.truth_items(page, derive=derive)
    rep = S.score(page, run_of(synthetic_result(page, items, header_wrong=True)), derive=derive, items=items,
                  trained_cells=())
    h = rep["headers"]["summary"]
    ok = all(h[k].get("right", 0) == 0 and h[k].get("wrong", 0) > 0 for k in ("clef", "key", "meter"))
    if h["cautionary"].get("right", 0) + h["cautionary"].get("wrong", 0):  # only where the page has one
        ok = ok and h["cautionary"].get("right", 0) == 0
    return {"name": "header_wrong", "passes": ok,
            "expect": "a record reading the wrong clef / key / meter scores all-wrong on each, none right",
            "got": {k: {a: b for a, b in v.items() if a != "accuracy_of_judged"} for k, v in h.items()}}


def clear_displacement(items: Sequence[S.TruthItem], sp: float, fam: str = "notehead") -> Tuple[float, float]:
    """A shift that lands NO ``fam`` truth box on another one (IoU >= the matcher's threshold), found by
    search (noteheads: long arcs and beams cannot be moved clear of each other on a real page): a fixed shift can drop a head onto its neighbour -- the first version of the control
    used 8 spaces and failed on the real page for exactly that reason."""
    for dx, dy in ((8, 0), (0, 8), (13, 7), (-9, 5), (21, 0), (0, 17), (30, 13)):
        dx, dy = dx * sp, dy * sp
        heads = [it for it in items if it.family == fam]
        if not any(S._iou((a.rect[0] + dx, a.rect[1] + dy, a.rect[2] + dx, a.rect[3] + dy), b.rect) >= S.MIN_IOU
                   for a in heads for b in heads):
            return dx, dy
    raise RuntimeError("no displacement clears every truth box: the control cannot be built on this page")


def control_no_overlap_no_match(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """A record whose boxes are all moved off the marks matches NOTHING (a matcher that pairs by order
    or by count, not by overlap, would still score it)."""
    items = S.truth_items(page, derive=derive)
    sp = S.statistics.median([b.space for b in S.staff_bands(page)]) if S.staff_bands(page) else 20.0
    dx, dy = clear_displacement(items, sp)
    rep = S.score(page, run_of(synthetic_result(page, items, dx=dx, dy=dy)), derive=derive, items=items,
                  trained_cells=())
    matched = rep["families"]["notehead"]["gather"]["matched"]
    ok = matched == 0
    return {"name": "no_overlap_no_match", "passes": ok,
            "expect": "noteheads moved to where no truth notehead stands match nothing",
            "got": {"shift_px": [round(dx), round(dy)], "noteheads_matched": matched}}


def control_frame(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    items = S.truth_items(page, derive=derive)
    sp = S.statistics.median([b.space for b in S.staff_bands(page)]) if S.staff_bands(page) else 20.0
    cases = {
        "unshifted": dict(),
        "boxes_down_0.35_space": dict(dy=0.35 * sp),
        "boxes_right_0.35_space": dict(dx=0.35 * sp),
        "cells_right_6px": dict(cell_dx=6.0),
        "dpi_300": dict(dpi=300),
    }
    got = {}
    for name, kw in cases.items():
        rep = S.score(page, run_of(synthetic_result(page, items, **kw)), derive=derive, items=items,
                      trained_cells=())
        got[name] = rep["frame_control"]["ok"]
    ok = got["unshifted"] and not any(v for k, v in got.items() if k != "unshifted")
    return {"name": "frame", "passes": ok,
            "expect": "frame OK unshifted; FAILED for each of: boxes off by 0.35 space (x, y), cells off by "
                      "6px, wrong dpi",
            "got": got}


def control_drop_and_add(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    items = S.truth_items(page, derive=derive)
    full = S.fully_labeled(page)
    scope = S.Scope(full)
    measured = [it for it in items if it.family == "notehead" and scope.holds(it.rect)]
    rng = random.Random(7)
    drop = {it.idx for it in rng.sample(measured, max(1, len(measured) // 10))} if measured else set()
    base = S.score(page, run_of(synthetic_result(page, items)), derive=derive, items=items, trained_cells=())
    dropped = S.score(page, run_of(synthetic_result(page, items, drop=drop)), derive=derive, items=items,
                      trained_cells=())
    anchor = next((c for c in full if c.kind == "measure"), None)
    spur = []
    if anchor is not None:
        x0, y0, x1, y1 = anchor.rect
        for k in range(max(1, len(measured) // 10)):
            r = (x0 + 5 + 3 * k, y0 + 5, x0 + 25 + 3 * k, y0 + 25)
            if not any(S._iou(r, it.rect) > 0 for it in items):
                spur.append(("noteheadBlackInSpace", r, anchor.system, anchor.staff, anchor.measure or 0))
    added = S.score(page, run_of(synthetic_result(page, items, spurious=spur)), derive=derive, items=items,
                    trained_cells=())
    g = lambda rep, k: rep["families"]["notehead"]["gather"][k]  # noqa: E731
    ok = (bool(drop) and bool(spur)
          and g(dropped, "recall") < g(base, "recall") and g(dropped, "precision") == 1.0
          and g(added, "precision") < g(base, "precision") and g(added, "recall") == 1.0)
    return {"name": "drop_and_add", "passes": ok,
            "expect": "dropping 10% of heads lowers recall and leaves precision 1; adding spurious heads "
                      "lowers precision and leaves recall 1",
            "got": {"dropped": len(drop), "recall_after_drop": g(dropped, "recall"),
                    "precision_after_drop": g(dropped, "precision"), "spurious_added": len(spur),
                    "precision_after_add": g(added, "precision"), "recall_after_add": g(added, "recall")}}


def control_refusal(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """A family no cell was inspected for is REFUSED; the same family inspected is scored."""
    uninspected = copy.deepcopy(page)
    for c in uninspected.cells:
        c.inspected = ["slur"]  # swept for slurs only: every other family has no truth to score
    items = S.truth_items(uninspected, derive=derive)
    rep = S.score(uninspected, run_of(synthetic_result(uninspected, items)), derive=derive, items=items,
                  trained_cells=())
    nh = rep["families"].get("notehead", {})
    positive = S.score(page, run_of(synthetic_result(page, S.truth_items(page, derive=derive))), derive=derive,
                       trained_cells=())["families"].get("notehead", {})
    ok = str(nh.get("status", "")).startswith("REFUSED") and positive.get("status") == "scored"
    return {"name": "refusal", "passes": ok,
            "expect": "noteheads REFUSED where only slurs were inspected; scored where all-ink was",
            "got": {"uninspected": nh.get("status"), "inspected": positive.get("status")}}


CONTROLS: Tuple[Callable[..., Dict[str, Any]], ...] = (
    control_self_score, control_owner_shift, control_position_shift, control_header_wrong, control_frame,
    control_drop_and_add, control_no_overlap_no_match, control_refusal)


def run_controls(page: PageTruth, derive: bool = True) -> List[Dict[str, Any]]:
    return [c(page, derive) for c in CONTROLS]


def main_controls(page: PageTruth, record: Optional[Path] = None, *, derive: bool = True) -> int:
    res = run_controls(page, derive)
    for r in res:
        print(f"{'PASS' if r['passes'] else 'FAIL'}  {r['name']:<14} expects: {r['expect']}")
        print(f"      got: {json.dumps(r['got'], default=str)}")
    return 0 if all(r["passes"] for r in res) else 1


if __name__ == "__main__":
    sys.exit("run: python3 -m tools.omr.hand_truth.score --controls --page <page.json>")
