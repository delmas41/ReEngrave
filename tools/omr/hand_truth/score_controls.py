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

THE STEM CONTROLS (ROADMAP 1.7, ``score_stems``), on the same synthetic record plus a CV stem reader's rows in
a cell frame that is NOT the page frame:

``stems_self``      the truth's stems filed as the CV reader's: recall = precision = 1, every stemmed head on its
                    own stem with the right direction, the detector-class number untouched.
``stems_shift``     every CV stem moved ONE HEAD WIDTH sideways: recall and precision collapse (to <= 0.05) and no
                    head keeps its stem, while the detector-class recall does not move.
``stems_drop_and_add`` 20% of the CV stems dropped / stems nobody drew added: neither number is a function of
                    the other.
``stems_attach_swap`` every head names the NEXT stem: stem recall stays 1.0, the per-head number collapses.
``stems_direction_flip`` every direction reversed: direction accuracy collapses, attachment does not move.
``stems_reader_not_run`` no ``Q.STEM`` row and no abstention is REFUSED, not scored as zero found.

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
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS, Verdict

#: A measuring instrument, not a consumer -- see ``score.DERIVED_CHECK`` (``wiring`` matches ``.owner`` as a
#: read of the detail key ``own``).
DERIVED_CHECK = True

#: How near (staff spaces, box to box) a truth stem must stand for the synthetic record to file a head on it --
#: restated, never read from ``score_stems`` (see ``_own_stem``).
STEM_CONTROL_TOUCH_SPACES = 0.30

SYNTH_WEIGHTS ="/synthetic/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"


def _verdict(log: Log, subject, quantity, outcome, value, decider, reason) -> None:
    log.record(Verdict(id=log._next_id("vrd"), subject=subject, quantity=quantity, outcome=outcome,
                       value=value, decider=decider, reason=reason))


def synthetic_result(page: PageTruth, items: Sequence[S.TruthItem], *, dx: float = 0.0, dy: float = 0.0,
                     cell_dx: float = 0.0, dpi: Optional[int] = None, drop: Sequence[int] = (),
                     spurious: Sequence[Tuple[str, S.Rect, int, int, int]] = (),
                     headers: bool = True, position_shift: int = 0, header_wrong: bool = False,
                     refile: Optional[Dict[int, Tuple[int, bool]]] = None,
                     cv_stems: bool = True, cv_dx: float = 0.0, cv_drop: Sequence[int] = (),
                     cv_spurious: Sequence[Tuple[S.Rect, int, int, int]] = (), attach: str = "own",
                     direction_flip: bool = False, up: float = 1.0, stem_reader_ran: bool = True) -> Dict[str, Any]:
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

    THE CV STEM READER (ROADMAP 1.7, stems): every truth stem is also filed as a ``Q.STEM`` row on its cell in the
    cell's CANONICAL frame (``up`` canonical px per page px, so the scorer must read the factor back from the
    detector boxes, which carry both); each head standing on a truth stem gets a ``Q.HEAD_STEM`` and a
    ``Q.STEM_DIRECTION`` verdict. ``cv_dx`` shifts only the CV stems (page px); ``cv_drop`` omits truth stem
    indices; ``cv_spurious`` adds ``(rect, system, staff, cell)`` stems nobody drew; ``attach`` is ``own`` (each head
    names its own stem), ``swap`` (the NEXT stem) or ``none`` (no verdict); ``direction_flip`` writes the opposite
    direction; ``stem_reader_ran=False`` files no ``Q.STEM`` row and no abstention (the reader never ran).
    """
    log = Log()
    cells = {c.id: c for c in page.cells if c.kind == "measure" and c.system is not None}
    per_cell: Dict[str, int] = {}
    for c in cells.values():
        sub = R.cell(0, c.system, c.staff, c.measure or 0)
        x0, y0, x1, y1 = c.rect
        log.observe(sub, Q.CELL_BOX, [x0 + cell_dx, y0, x1 + cell_dx, y1], reader=READERS.GEOMETRY,
                    frame=f"cell:{c.measure}")

    # ── the CV stem reader: one Q.STEM row per truth stem, in the cell's CANONICAL frame (`up` per page px) ──
    cv_dropped = set(cv_drop)
    stem_order: List[Tuple[int, str]] = []          # (truth idx, Q.STEM row id), in truth order
    stem_row_of: Dict[int, str] = {}
    truth_stems = [it for it in items if it.family == "stem"]
    stem_sp = (S.statistics.median([b.space for b in S.staff_bands(page)]) if S.staff_bands(page) else 20.0)
    if stem_reader_ran and cv_stems:
        for it in truth_stems:
            c = cells.get(it.cell_id or "")
            if c is None or it.idx in cv_dropped:
                continue
            x0, y0, x1, y1 = it.rect
            row = log.observe(R.cell(0, c.system, c.staff, c.measure or 0), Q.STEM,
                              [(x0 + cv_dx - c.rect[0]) * up, (y0 - c.rect[1]) * up, (x1 - x0) * up, (y1 - y0) * up],
                              reader=READERS.CV_LINES, frame=f"cell:{c.measure}")
            stem_order.append((it.idx, row.id))
            stem_row_of[it.idx] = row.id
        for rect, system, staff, cell in cv_spurious:
            x0, y0, x1, y1 = rect
            cc = next(c for c in cells.values() if (c.system, c.staff, c.measure or 0) == (system, staff, cell))
            log.observe(R.cell(0, system, staff, cell), Q.STEM,
                        [(x0 - cc.rect[0]) * up, (y0 - cc.rect[1]) * up, (x1 - x0) * up, (y1 - y0) * up],
                        reader=READERS.CV_LINES, frame=f"cell:{cell}")
    elif stem_reader_ran:                           # it ran and accepted nothing: an abstention per cell
        for c in cells.values():
            log.abstain(R.cell(0, c.system, c.staff, c.measure or 0), Q.STEM, reader=READERS.CV_LINES,
                        frame=f"cell:{c.measure}", reason=ABSTAIN.NO_LINE_ACCEPTED)

    def _own_stem(it: S.TruthItem) -> Optional[S.TruthItem]:
        """The truth stem a head stands on -- by a plain box test with its OWN restated window, NOT by the scorer's
        rule, so a bug in that rule cannot hide in both the record and the scoring. (A head and the stem box Sean
        drew beside it are rarely in exact contact: 8 of 321 on the first Brahms page stand 0.05-0.25 spaces off.)"""
        hx0, hy0, hx1, hy1 = it.rect
        slack = STEM_CONTROL_TOUCH_SPACES * stem_sp
        for t in truth_stems:
            if (t.rect[0] <= hx1 + slack and t.rect[2] >= hx0 - slack
                    and t.rect[1] <= hy1 + slack and t.rect[3] >= hy0 - slack):
                return t
        return None

    def put(cls: str, rect, system: int, staff: int, cell: int, it: Optional[S.TruthItem]) -> None:
        g = R.glyph(0, system, staff, cell, per_cell.setdefault(f"{system}.{staff}.{cell}", 0))
        per_cell[f"{system}.{staff}.{cell}"] += 1
        x0, y0, x1, y1 = rect
        rect = [x0 + dx, y0 + dy, x1 + dx, y1 + dy]
        log.observe(g, Q.GLYPH_BOX, [cls, 0.0, 0.0, (rect[2] - rect[0]) * up, (rect[3] - rect[1]) * up],
                    reader=READERS.DETECTOR, frame=f"cell:{cell}", score=0.9, bbox_page_px=rect)
        if it is None or it.family != "notehead":
            return
        mine = _own_stem(it)
        if mine is not None and stem_reader_ran and attach != "none":
            if attach == "swap" and stem_order:
                k = next((i for i, (ti, _r) in enumerate(stem_order) if ti == mine.idx), None)
                row_id = stem_order[((k if k is not None else -1) + 1) % len(stem_order)][1]
            else:
                row_id = stem_row_of.get(mine.idx)
            if row_id is None:
                _verdict(log, g, Q.HEAD_STEM, Outcome.ABSTAINED, None, "adjudicate_head_stem", "no_stem")
                _verdict(log, g, Q.STEM_DIRECTION, Outcome.ABSTAINED, None, "adjudicate_stem_direction", "no_stem")
            else:
                _verdict(log, g, Q.HEAD_STEM, Outcome.DECIDED, row_id, "adjudicate_head_stem", "one_stem")
                ext_up, ext_down = it.rect[1] - mine.rect[1], mine.rect[3] - it.rect[3]
                way = "up" if ext_up > ext_down else "down"
                if direction_flip:
                    way = "down" if way == "up" else "up"
                _verdict(log, g, Q.STEM_DIRECTION, Outcome.DECIDED, way, "adjudicate_stem_direction",
                         "stem_projection")
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


# ── the stem controls (ROADMAP 1.7, stems): the CV source and the per-head attachment ─────────────────────

#: A canonical-px-per-page-px factor that is NOT 1, so a scorer that forgets to convert the cell's canonical
#: frame to page pixels reads every CV stem in the wrong place and the control goes red.
STEM_CONTROL_UP = 2.5
#: One notehead's width, in staff spaces (CLAUDE.md §10): the distance the shift control moves every CV stem.
HEAD_WIDTH_SPACES = 1.3
#: The shift control's own clearance window (spaces) and the share of stems it tolerates landing inside it. Restated
#: here, not read from ``score_stems``: see ``clear_stem_shift``.
STEM_CONTROL_CLEAR_SPACES = 0.30
STEM_CONTROL_MAX_COLLIDING = 0.02


def _stem_views(rep: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    st = rep["stems"]
    return st["cv_stem"], st["heads"], st["detector_class"]


def _stem_score(page: PageTruth, items: Sequence[S.TruthItem], derive: bool, **kw: Any) -> Dict[str, Any]:
    kw.setdefault("up", STEM_CONTROL_UP)
    return S.score(page, run_of(synthetic_result(page, items, **kw)), derive=derive, items=items, trained_cells=())


def clear_stem_shift(items: Sequence[S.TruthItem], sp: float) -> float:
    """A shift of every stem, about a head width, that lands (almost) NO truth stem on another one's column (found
    by search, as ``clear_displacement`` is: a head width can put a stem on its neighbour's column on a crowded
    page -- beamed stems stand 1.57 spaces apart on the first Brahms page, so 1.3 clears the 0.25 tolerance by
    0.02 spaces only -- and the control would then pass for the wrong reason). Judged with its OWN restated
    window (``STEM_CONTROL_CLEAR_SPACES``, never the scorer's constant: a scorer whose tolerance was widened
    must not widen the control's), and a shift is accepted when at most ``STEM_CONTROL_MAX_COLLIDING`` of the
    stems would land on a neighbour: those few can legitimately still pair, so the control's bar allows for them."""
    stems = [it for it in items if it.family == "stem"]
    for k in (HEAD_WIDTH_SPACES, -HEAD_WIDTH_SPACES, 1.2, -1.2, 1.5, -1.5, 2.0, -2.0, 3.0, -3.0, 5.0):
        dx = k * sp
        n = sum(1 for a in stems if any(a is not b and abs(S._cx(a.rect) + dx - S._cx(b.rect))
                                        <= STEM_CONTROL_CLEAR_SPACES * sp
                                        and min(a.rect[3], b.rect[3]) - max(a.rect[1], b.rect[1]) > 0
                                        for b in stems))
        if n <= STEM_CONTROL_MAX_COLLIDING * len(stems):
            return dx
    raise RuntimeError("no shift clears the truth stems: the control cannot be built on this page")


def control_stems_self(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """The truth's own stems filed as the CV reader's, in a cell frame that is NOT the page frame: every stem found,
    none invented, every stemmed head attached to its own stem with the right direction, and the detector-class
    number (which the same record also carries) untouched."""
    items = S.truth_items(page, derive=derive)
    cv, hd, det = _stem_views(_stem_score(page, items, derive))
    ok = (cv.get("status") == "scored" and cv["recall"] == 1.0 and cv["precision"] == 1.0
          and hd["truth_heads_with_a_truth_stem"] > 0
          and hd["attach"].get("right", 0) == hd["truth_heads_with_a_truth_stem"]
          and hd["direction"].get("wrong", 0) == 0 and hd["direction"].get("right", 0) > 0
          and det["gather"]["recall"] == 1.0)
    return {"name": "stems_self", "passes": ok,
            "expect": "CV stems recall = precision = 1 through a canonical frame (x%.1f); every stemmed head attached "
                      "to its own stem, direction right; detector class unchanged" % STEM_CONTROL_UP,
            "got": {"cv": {k: cv.get(k) for k in ("status", "truth", "read", "found", "recall", "precision")},
                    "attach": hd.get("attach"), "direction": hd.get("direction"),
                    "detector_class_recall": det["gather"]["recall"]}}


def control_stems_shift(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """Every CV stem moved one head width sideways: recall AND precision collapse (a matcher that ignores the
    column would still pair them), the heads lose their stems, and the detector-class number does not move (so
    the collapse is the CV source's)."""
    items = S.truth_items(page, derive=derive)
    sp = S.statistics.median([b.space for b in S.staff_bands(page)]) if S.staff_bands(page) else 20.0
    dx = clear_stem_shift(items, sp)
    good_rep = _stem_score(page, items, derive)
    bad_rep = _stem_score(page, items, derive, cv_dx=dx)
    gcv, _gh, gdet = _stem_views(good_rep)
    bcv, bh, bdet = _stem_views(bad_rep)
    ok = (gcv["recall"] == 1.0 and bcv["recall"] is not None and bcv["recall"] <= 0.05
          and bcv["precision"] is not None and bcv["precision"] <= 0.05
          and bh["attach"].get("right", 0) == 0 and bdet["gather"]["recall"] == gdet["gather"]["recall"])
    return {"name": "stems_shift", "passes": ok,
            "expect": "recall 1.0 unshifted; <= 0.05 (recall and precision) with every CV stem moved one head "
                      "width; no head keeps its right stem; the detector-class recall unchanged",
            "got": {"shift_px": round(dx, 1), "recall_unshifted": gcv["recall"], "recall_shifted": bcv["recall"],
                    "precision_shifted": bcv["precision"], "heads_right_shifted": bh["attach"].get("right", 0),
                    "detector_recall_unchanged": bdet["gather"]["recall"] == gdet["gather"]["recall"]}}


def _spurious_stem_rects(page: PageTruth, items: Sequence[S.TruthItem], n: int) -> List[Tuple[S.Rect, int, int, int]]:
    """``n`` stems of 3 spaces standing where no truth stem is (checked against the truth's own columns)."""
    sp = S.statistics.median([b.space for b in S.staff_bands(page)]) if S.staff_bands(page) else 20.0
    stems = [it for it in items if it.family == "stem"]
    out: List[Tuple[S.Rect, int, int, int]] = []
    for c in S.fully_labeled(page):
        if c.kind != "measure" or c.system is None or len(out) >= n:
            continue
        for k in range(1, 40):
            x = c.rect[0] + k * 0.45 * sp
            r = (x, c.rect[1] + 2 * sp, x + 0.2 * sp, c.rect[1] + 5 * sp)
            if x + 0.2 * sp >= c.rect[2]:
                break
            if not any(abs(S._cx(t.rect) - S._cx(r)) <= 0.8 * sp and min(t.rect[3], r[3]) - max(t.rect[1], r[1]) > 0
                       for t in stems):
                out.append((r, c.system, c.staff, c.measure or 0))
                break
    return out[:n]


def control_stems_drop_and_add(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    items = S.truth_items(page, derive=derive)
    stems = [it for it in items if it.family == "stem" and S.Scope(S.fully_labeled(page)).holds(it.rect)]
    rng = random.Random(11)
    drop = {it.idx for it in rng.sample(stems, max(1, len(stems) // 5))} if stems else set()
    spur = _spurious_stem_rects(page, items, max(1, len(stems) // 5))
    base = _stem_score(page, items, derive)["stems"]["cv_stem"]
    dropped = _stem_score(page, items, derive, cv_drop=drop)["stems"]["cv_stem"]
    added = _stem_score(page, items, derive, cv_spurious=spur)["stems"]["cv_stem"]
    ok = (bool(drop) and bool(spur) and dropped["recall"] < base["recall"] and dropped["precision"] == 1.0
          and added["precision"] < base["precision"] and added["recall"] == 1.0)
    return {"name": "stems_drop_and_add", "passes": ok,
            "expect": "dropping 20% of the CV stems lowers recall and leaves precision 1; adding stems nobody "
                      "drew lowers precision and leaves recall 1",
            "got": {"dropped": len(drop), "recall_after_drop": dropped["recall"],
                    "precision_after_drop": dropped["precision"], "spurious_added": len(spur),
                    "precision_after_add": added["precision"], "recall_after_add": added["recall"]}}


def control_stems_attach_swap(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """Every head attached to the NEXT stem: the CV source still finds every stem (recall unchanged), but no head has
    its right stem -- so the per-head number is not a function of the stem recall."""
    items = S.truth_items(page, derive=derive)
    good = _stem_score(page, items, derive)
    bad = _stem_score(page, items, derive, attach="swap")
    gcv, gh, _ = _stem_views(good)
    bcv, bh, _ = _stem_views(bad)
    n = gh["truth_heads_with_a_truth_stem"]
    ok = (gcv["recall"] == bcv["recall"] == 1.0 and gh["attach"].get("right", 0) == n
          and bh["attach"].get("right", 0) <= 0.05 * n and bh["attach"].get("wrong_other_stem", 0) >= 0.95 * n)
    return {"name": "stems_attach_swap", "passes": ok,
            "expect": "stem recall 1.0 in both; heads with their right stem: all unswapped, <= 5% when every head "
                      "names the next stem (and they read as ANOTHER stem, not as no stem)",
            "got": {"stemmed_heads": n, "right_unswapped": gh["attach"].get("right", 0),
                    "right_swapped": bh["attach"].get("right", 0), "other_stem_swapped": bh["attach"].get(
                        "wrong_other_stem", 0), "recall": [gcv["recall"], bcv["recall"]]}}


def control_stems_direction_flip(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    items = S.truth_items(page, derive=derive)
    good = _stem_score(page, items, derive)
    bad = _stem_score(page, items, derive, direction_flip=True)
    _, gh, _ = _stem_views(good)
    _, bh, _ = _stem_views(bad)
    base, flipped = gh["direction_right_of_judged"], bh["direction_right_of_judged"]
    ok = (base == 1.0 and flipped is not None and flipped <= 0.05 and gh["attach"] == bh["attach"])
    return {"name": "stems_direction_flip", "passes": ok,
            "expect": "direction right 1.0 as filed, <= 0.05 when every direction is the opposite; attachment unchanged",
            "got": {"direction_right_as_filed": base, "direction_right_flipped": flipped,
                    "attach_unchanged": gh["attach"] == bh["attach"]}}


def control_stems_reader_not_run(page: PageTruth, derive: bool = True) -> Dict[str, Any]:
    """A record the CV stem reader never reached (no ``Q.STEM`` row and no abstention) is REFUSED, not scored as
    zero stems found -- with its positive control: the reader RAN and accepted nothing, which scores recall 0."""
    items = S.truth_items(page, derive=derive)
    never = _stem_score(page, items, derive, stem_reader_ran=False)["stems"]["cv_stem"]
    ran = _stem_score(page, items, derive, cv_stems=False)["stems"]["cv_stem"]
    ok = str(never.get("status", "")).startswith("REFUSED") and ran.get("status") == "scored" and ran["recall"] == 0.0
    return {"name": "stems_reader_not_run", "passes": ok,
            "expect": "no Q.STEM row and no abstention -> REFUSED; an abstention in every cell -> scored, recall 0.0",
            "got": {"never_ran": never.get("status"), "ran_found_none": {k: ran.get(k) for k in ("status", "recall")}}}


CONTROLS: Tuple[Callable[..., Dict[str, Any]], ...] = (
    control_self_score, control_owner_shift, control_position_shift, control_header_wrong, control_frame,
    control_drop_and_add, control_no_overlap_no_match, control_refusal,
    control_stems_self, control_stems_shift, control_stems_drop_and_add, control_stems_attach_swap,
    control_stems_direction_flip, control_stems_reader_not_run)


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
