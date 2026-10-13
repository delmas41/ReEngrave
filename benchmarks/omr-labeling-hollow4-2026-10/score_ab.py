"""ROADMAP 2.4b step 3 -- score GATHER+ADJUDICATE records of production vs each graft on Sean's hollow truth.

  python3 benchmarks/omr-labeling-hollow4-2026-10/score_ab.py \
      --litolff prod=rec.json graftA=rec.json ... --brahms prod=rec.json graftA=rec.json ... [--out score.json]

LITOLFF TEST (never trained on): Sean's 104 cells of the gate page (idx 1), truth in each cell's CANONICAL frame, matched
against the record's glyphs of the same (system, staff, cell) in the same frame (`Glyph.box_canon`) -- no page-pixel
mapping is invented. hollow recall = truth heads with a hollow-class box on them / truth heads. hollow precision = hollow
boxes matching a truth head / all hollow boxes in those cells (Sean did not box tempo-mark notes on purpose, so a few
true-but-unboxed boxes count against precision on every arm alike).
BRAHMS HAND TRUTH (pdf idx 0, page frame): 27 hollow heads (must stay 27/27), filled heads called hollow, and what the
extra hollow boxes sit on (time-signature 8s, tremolo slashes, dynamics, black heads).
Controls (rule 7): the truth matched against ITSELF finds all; shifted by 3 head-widths finds ~none. Exit 1 otherwise.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from tools.omr.hand_truth import score as SC  # noqa: E402
from tools.omr.hand_truth import store as ST  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

HOLLOW = ("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")
REPO = Path.cwd()
TESTB = REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10"


def is_h(c):
    return c.startswith(HOLLOW)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    if i <= 0:
        return 0.0
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


def same(t, r):
    if iou(t, r) >= 0.3:
        return True
    cx, cy = (t[0] + t[2]) / 2, (t[1] + t[3]) / 2
    return r[0] <= cx <= r[2] and r[1] <= cy <= r[3] and area(r) <= 2.0 * area(t)


def litolff_truth():
    """{(system, staff, cell): [rect x0y0x1y1 canonical, ...]} + the cells' count."""
    cells = {c["cell_id"]: c for c in json.loads((TESTB / "cells.json").read_text())}
    out = {}
    n = 0
    for vf in sorted((TESTB / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        c = cells[v["cell_id"]]
        key = (c["system_index"], c["staff_index"], c["measure_index"])
        for d in v["added_detections"]:
            if d["human_class"].startswith(HOLLOW):
                b = d["bbox"]
                out.setdefault(key, []).append((b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]))
                n += 1
    return out, n, set((c["system_index"], c["staff_index"], c["measure_index"]) for c in cells.values())


def score_litolff(run, truth, cellset, page=1, shift=0.0):
    by_cell = collections.defaultdict(list)
    for g in run.glyphs.values():
        if g.page == page and g.box_canon is not None and (g.system, g.staff, g.cell) in cellset:
            by_cell[(g.system, g.staff, g.cell)].append(g)
    n_t = found = 0
    miss_kind = collections.Counter()
    hol_boxes = hol_match = kept = kept_match = 0
    extra = []
    for key in cellset:
        ts = truth.get(key, [])
        hs = [g for g in by_cell.get(key, []) if is_h(g.cls or "")]
        for t in ts:
            t2 = (t[0] + shift, t[1], t[2] + shift, t[3])
            n_t += 1
            if any(same(t2, g.box_canon) for g in hs):
                found += 1
            else:
                cs = [g for g in by_cell.get(key, []) if same(t2, g.box_canon)]
                miss_kind["a BLACK head box sits on it" if any((g.cls or "").startswith("noteheadBlack") for g in cs)
                          else ("another class sits on it" if cs else "no box at all")] += 1
        for g in hs:
            st, _ = RO.adjudicate_status(run, g)
            m = any(same((t[0] + shift, t[1], t[2] + shift, t[3]), g.box_canon) for t in ts)
            hol_boxes += 1
            hol_match += m
            if st not in (RO.REFUSED, RO.GIVEN_AWAY):
                kept += 1
                kept_match += m
            if not m:
                extra.append((key, g.cls, round(g.score or 0, 2), st))
    return {"truth_heads": n_t, "found": found, "recall": found / max(1, n_t),
            "hollow_boxes": hol_boxes, "hollow_boxes_on_a_truth_head": hol_match,
            "precision": hol_match / max(1, hol_boxes),
            "kept_hollow_boxes": kept, "kept_on_a_truth_head": kept_match,
            "kept_precision": kept_match / max(1, kept), "missed_truth_heads_by": dict(miss_kind),
            "extra_boxes": extra}


def score_brahms(run, page):
    boxes = list(page.boxes)
    heads = [b for b in boxes if is_h(b.cls)]
    blacks = [b for b in boxes if b.cls.startswith("noteheadBlack")]
    gl = SC.read_glyphs(run, page.pdf_page_index)
    hol = [g for g in gl if is_h(g.cls)]
    found = sum(1 for t in heads if any(same(t.rect, g.rect) for g in hol))
    # filled truth heads called half/whole: a hollow read box on it and NO black read box on it
    black_as_hollow = 0
    for t in blacks:
        c = [g for g in gl if same(t.rect, g.rect) and g.cls.startswith("notehead")]
        if c and any(is_h(g.cls) for g in c) and not any(g.cls.startswith("noteheadBlack") for g in c):
            black_as_hollow += 1
    sits = collections.Counter()
    extra = 0
    for g in hol:
        if any(same(t.rect, g.rect) for t in heads):
            continue
        extra += 1
        where = "other"
        for t in boxes:
            if t.cls.startswith("timeSig") and g.rect[0] < t.rect[2] and t.rect[0] < g.rect[2] and g.rect[1] < t.rect[3] and t.rect[1] < g.rect[3]:
                where = "timeSig digit"; break
            if t.cls.startswith("tremolo") and g.rect[0] < t.rect[2] and t.rect[0] < g.rect[2] and g.rect[1] < t.rect[3] and t.rect[1] < g.rect[3]:
                where = "tremolo slash"; break
            if t.cls.startswith("dynamic") and g.rect[0] < t.rect[2] and t.rect[0] < g.rect[2] and g.rect[1] < t.rect[3] and t.rect[1] < g.rect[3]:
                where = "dynamic (ff bowl)"; break
        else:
            if any(same(t.rect, g.rect) for t in blacks):
                where = "on a filled head"
        sits[where] += 1
    kept_extra = sum(1 for g in hol if g.status not in (RO.REFUSED, RO.GIVEN_AWAY) and not any(same(t.rect, g.rect) for t in heads))
    return {"truth_hollow": len(heads), "found_hollow": found, "hollow_boxes": len(hol),
            "extra_hollow_boxes": extra, "extra_surviving_adjudicate": kept_extra,
            "extra_sits_on": dict(sits), "filled_heads_called_hollow": black_as_hollow}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--litolff", nargs="+", required=True, help="label=record.json ...")
    ap.add_argument("--brahms", nargs="+", required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    truth, n_truth, cellset = litolff_truth()
    page = ST.load(REPO / "data/hand-truth/pages/imslp317803/0.json")
    heads = [b for b in page.boxes if is_h(b.cls)]
    ok = True
    # controls ---------------------------------------------------------------------------
    first = RO.load_run(a.litolff[0].split("=", 1)[1])
    wmed = statistics.median([t[2] - t[0] for ts in truth.values() for t in ts])
    class FakeG:
        def __init__(s, r):
            s.page, s.system, s.staff, s.cell, s.box_canon, s.cls, s.score = 1, 0, 0, 0, r, "noteheadHalfInSpace", 1.0
    # self-match / shift control on the matcher itself (same() on truth vs truth)
    c1 = sum(1 for ts in truth.values() for t in ts if same(t, t))
    c2 = sum(1 for ts in truth.values() for t in ts if same(t, (t[0] + 3 * wmed, t[1], t[2] + 3 * wmed, t[3])))
    print(f"controls: truth self-match {c1}/{n_truth} (all)   shifted 3 head-widths {c2}/{n_truth} (~0)")
    ok &= (c1 == n_truth and c2 <= max(1, n_truth // 10))
    sh = score_litolff(first, truth, cellset, shift=3 * wmed)
    print(f"control: first arm's recall with truth SHIFTED 3 head-widths {sh['found']}/{sh['truth_heads']} (must collapse)")
    ok &= sh["recall"] < 0.25
    if not ok:
        print("CONTROL FAILED -- numbers withheld")
        return 1
    res = {"litolff_truth_heads": n_truth, "litolff_cells": len(cellset), "brahms_truth_hollow": len(heads),
           "litolff": {}, "brahms": {}}
    for spec in a.litolff:
        lab, p = spec.split("=", 1)
        r = score_litolff(RO.load_run(p), truth, cellset)
        res["litolff"][lab] = r
        print(f"[litolff {lab}] hollow recall {r['found']}/{r['truth_heads']} = {100*r['recall']:.1f}%   "
              f"precision {r['hollow_boxes_on_a_truth_head']}/{r['hollow_boxes']} = {100*r['precision']:.1f}%   "
              f"surviving ADJUDICATE {r['kept_on_a_truth_head']}/{r['kept_hollow_boxes']} = {100*r['kept_precision']:.1f}%   "
              f"missed: {r['missed_truth_heads_by']}")
    for spec in a.brahms:
        lab, p = spec.split("=", 1)
        r = score_brahms(RO.load_run(p), page)
        res["brahms"][lab] = r
        print(f"[brahms {lab}] hollow found {r['found_hollow']}/{r['truth_hollow']}  hollow boxes {r['hollow_boxes']} "
              f"(extra {r['extra_hollow_boxes']}, surviving ADJ {r['extra_surviving_adjudicate']}) sitting on {r['extra_sits_on']}  "
              f"filled heads called hollow {r['filled_heads_called_hollow']}")
    if a.out:
        a.out.write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
