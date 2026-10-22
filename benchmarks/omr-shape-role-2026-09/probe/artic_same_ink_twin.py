"""ROADMAP 2.12f round 2 -- CHECK BEFORE BUILDING A CROSS-STAFF SEARCH.

A measure cell is padded ~4 staff spaces and reaches the neighbour staff's ink
(CLAUDE.md Sec.10). So a mark standing in the gap between two staves may already
have been detected a SECOND time in the neighbour staff's cell, as a separate
glyph on the SAME ink -- and DECIDED there. If so, the `no_notehead` in the first
cell is CORRECT, the mark is owned via the neighbour's cell, and the right fix
is to RECORD that and not to search across staves (Sec.10: a resolved
cross-staff contest DROPS the loser, it never relocates it).

    python3 benchmarks/omr-shape-role-2026-09/probe/artic_same_ink_twin.py \
        <readjudicate_artic_side output.json> [--probe <artic_side probe rows json>]

For every articulation mark whose owner ABSTAINED: is there another
`Q.ARTICULATION_MARK` glyph, in a DIFFERENT cell of the same page, whose page box
is the same ink (centre distance within half the larger box's size on each axis,
or IoU >= 0.3)? and is THAT glyph's owner DECIDED? Reported for every abstained
mark and, with `--probe`, for the subset whose declared-side head stands in
another staff within reach (the round-1 "127").

Page boxes are `bbox_page_px` on the rows -- the cross-staff frame; a canonical
cell coordinate cannot answer a cross-staff question.
"""
from __future__ import annotations

import argparse
import collections
import json


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _same_ink(a, b):
    if _iou(a, b) >= 0.3:
        return True
    ca = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
    cb = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    w = max(a[2] - a[0], b[2] - b[0])
    h = max(a[3] - a[1], b[3] - b[1])
    return abs(ca[0] - cb[0]) <= 0.5 * w and abs(ca[1] - cb[1]) <= 0.5 * h


def _cell(subj):
    return "/".join(subj.split("/")[1:5])


def analyse(rows, subset=None):
    by_page = collections.defaultdict(list)
    for r in rows:
        if r.get("mark_bbox_page"):
            by_page[r["page"]].append(r)
    out = collections.Counter()
    examples = []
    for r in rows:
        o = r["owner"]
        if not o or o["outcome"] == "decided":
            continue
        if subset is not None and r["subject"] not in subset:
            continue
        out["abstained marks"] += 1
        if not r.get("mark_bbox_page"):
            out["no page box"] += 1
            continue
        twins = [t for t in by_page[r["page"]]
                 if t["subject"] != r["subject"]
                 and _cell(t["subject"]) != _cell(r["subject"])
                 and _same_ink(r["mark_bbox_page"], t["mark_bbox_page"])]
        if not twins:
            out["no same-ink twin in another cell"] += 1
            continue
        out["has a same-ink twin in another cell"] += 1
        dec = [t for t in twins if t["owner"] and t["owner"]["outcome"] == "decided"]
        if dec:
            out["... and a twin is DECIDED (owned via the neighbour's cell)"] += 1
            same_side = [t for t in dec if t.get("suffix_side") == r.get("suffix_side")]
            out["...... same class side on the decided twin"] += int(bool(same_side))
            if len(examples) < 6:
                examples.append((r["subject"], dec[0]["subject"],
                                 dec[0]["owner"]["value"]))
        else:
            out["... but no twin is decided"] += 1
    return out, examples


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("harness_json")
    ap.add_argument("--probe", default=None)
    a = ap.parse_args(argv)
    rows = json.load(open(a.harness_json))["articulations"]
    out, ex = analyse(rows)
    print("ALL abstained marks:")
    for k, v in out.items():
        print("  %5d  %s" % (v, k))
    print("  examples (mark, twin, twin's owner):", ex[:4])
    if a.probe:
        pr = json.load(open(a.probe))["rows"]
        sub = {r["subject"] for r in pr
               if r.get("declared_side_head_elsewhere")
               and r.get("window") is not None
               and r["owner_reason"] == "no_notehead"}
        out2, _ = analyse(rows, subset=sub)
        print("SUBSET: abstained AND a declared-side head stands in another staff (n=%d):" % len(sub))
        for k, v in out2.items():
            print("  %5d  %s" % (v, k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
