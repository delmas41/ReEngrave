"""ROADMAP 2.12, Part 2(c) — SIZING, not building.

Sean's description of where the staged model points: *"look at all the blobs
and come up with a list of potential ways it could be labeled with boxes,
yolo/CV choices all connected to the ink, and then allow the other stages to
decide."* That makes the INK COMPONENT the subject and every detector box a
reading attached to it. The first question anyone sizing it has to answer is
whether that join is one-to-one, and on which plate.

So this probe counts, on the two scan plates and per detector box:

  * how many connected ink components the box COVERS (0, 1, >1);
  * and per ink component, how many boxes cover IT (0, 1, >1).

⚠️ IT NEEDS THE `--ink-rows` FORM OF THE RECORD. Roadmap 1.1 made the default
one SUMMARY row per cell (`ink_n_components`, `ink_largest_share`), which
aggregates away the per-component geometry this question is about. The three
acceptance records are all in the summary form, so this probe runs on the two
committed `--ink-rows` records instead — a FOUR-PAGE sample of each plate, not
the whole movement, and every number below says so.

⚠️ THE OVERLAP TEST IS THE ONE THE GATHERER ALREADY USES. `gather._coverage`
asks what fraction of a component's area a box covers; this asks the same
intersection both ways so the two cannot drift, and prints the threshold.

Run:

    python3 benchmarks/omr-shape-role-2026-09/probe/ink_vs_boxes.py --all
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))

from tools.omr.staged import record_io          # noqa: E402

#: A box COVERS a component when it holds at least this much of the
#: component's area. ⚠️ Not a new constant: `gather._coverage` computes
#: exactly this fraction for `ink_detector_coverage`, and the ink gather's own
#: `ink_explained_by` list is built from a NON-ZERO overlap. Both are reported
#: so the choice is visible rather than embedded.
_COVER = 0.5

#: CV-only classes that box a REGION rather than a mark (CLAUDE.md §9:
#: "`stem` and `staff` are CV-only and cost nothing"). A `staff` box covers
#: every component in its cell, so it is not a competing reading of any of
#: them.
_STRUCTURAL = {"staff", "stem"}

#: The `--ink-rows` records. ⚠️ FOUR PAGES OF EACH PLATE, not a movement.
_RECORDS = [
    ("beethoven5-litolff-p1-p4  (MERGING plate)",
     "_shared-records/beethoven5-p1-p4-ink-identity.record.json"),
    ("brahms1-breitkopf-p0-p3   (SHATTERING plate)",
     "_shared-records/brahms1-breitkopf-p0-p3-ink.record.json"),
]


def _cell_of(key: str):
    bits = key.split("/")
    if bits[0] == "glyph" and len(bits) >= 6:
        return "/".join(["cell"] + bits[1:5])
    return None


def _inter(a, b) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def run(path: Path, label: str) -> dict:
    data = record_io.load_record(path)
    rec = data["record"]
    prov = data.get("provenance") or {}

    ink_by_cell = collections.defaultdict(list)   # cell -> [(bbox, id)]
    box_by_cell = collections.defaultdict(list)   # cell -> [(bbox, name, id)]
    n_ink = n_box = 0
    ink_no_geometry = 0

    for o in rec.get("observations") or ():
        q = o["quantity"]
        if q == "ink":
            d = o.get("detail") or {}
            bb = d.get("ink_bbox_canonical")
            if not bb:
                ink_no_geometry += 1
                continue
            c = _cell_of(o["subject"])
            if c is None:
                ink_no_geometry += 1
                continue
            n_ink += 1
            ink_by_cell[c].append((tuple(float(v) for v in bb), o["id"]))
        elif q == "glyph_box":
            v = o["value"]
            if not (isinstance(v, (list, tuple)) and len(v) >= 5):
                continue
            c = _cell_of(o["subject"])
            if c is None:
                continue
            n_box += 1
            x, y, w, h = (float(v[1]), float(v[2]), float(v[3]), float(v[4]))
            box_by_cell[c].append(((x, y, x + w, y + h), str(v[0]), o["id"]))

    if not n_ink:
        return {"label": label, "record": str(path),
                "error": ("no per-component ink rows -- this record is in the "
                          "roadmap 1.1 SUMMARY form; re-gather with "
                          "--ink-rows")}

    boxes_per_comp = collections.Counter()
    comps_per_box = collections.Counter()
    classes_per_comp = collections.Counter()
    notation_classes_per_comp = collections.Counter()
    multi_class_examples = collections.Counter()
    notation_contest = collections.Counter()
    box_covers_nothing_by_class = collections.Counter()

    for cell, comps in ink_by_cell.items():
        boxes = box_by_cell.get(cell) or []
        # component -> boxes covering it
        for bb, _cid in comps:
            area = max((bb[2] - bb[0]) * (bb[3] - bb[1]), 1.0)
            hits = [name for box, name, _ in boxes
                    if _inter(bb, box) / area >= _COVER]
            boxes_per_comp[min(len(hits), 5)] += 1
            classes_per_comp[min(len(set(hits)), 5)] += 1
            if len(set(hits)) > 1:
                multi_class_examples["|".join(sorted(set(hits))[:3])] += 1
            # ⚠️ `staff` AND `stem` ARE CV-ONLY OVERLAYS AND CO-COVER
            # EVERYTHING. A `staff` box is the whole staff, so counting it as
            # a competing READING would say every piece of ink on the page is
            # contested. CLAUDE.md §9 records both as CV-only and costing
            # nothing; they are excluded here and the raw figure is kept
            # beside this one so the exclusion is visible.
            notation = {h for h in hits if h not in _STRUCTURAL}
            notation_classes_per_comp[min(len(notation), 5)] += 1
            if len(notation) > 1:
                notation_contest["|".join(sorted(notation)[:3])] += 1
        # box -> components inside it
        for box, name, _bid in boxes:
            n = 0
            for bb, _cid in comps:
                area = max((bb[2] - bb[0]) * (bb[3] - bb[1]), 1.0)
                if _inter(bb, box) / area >= _COVER:
                    n += 1
            comps_per_box[min(n, 5)] += 1
            if n == 0:
                box_covers_nothing_by_class[name] += 1

    for cell, boxes in box_by_cell.items():
        if cell in ink_by_cell:
            continue
        for _box, name, _bid in boxes:
            comps_per_box[0] += 1
            box_covers_nothing_by_class[name] += 1

    def _pct(counter, key):
        tot = sum(counter.values()) or 1
        return round(100.0 * counter.get(key, 0) / tot, 1)

    return {
        "label": label,
        "record": str(path),
        "provenance": {"commit": prov.get("commit"), "dirty": prov.get("dirty")},
        "cover_threshold": _COVER,
        "counts": {"ink_components": n_ink, "detector_boxes": n_box,
                   "ink_rows_without_geometry": ink_no_geometry,
                   "cells_with_ink": len(ink_by_cell)},
        "boxes_per_ink_component": {
            "0": boxes_per_comp.get(0, 0), "1": boxes_per_comp.get(1, 0),
            "2": boxes_per_comp.get(2, 0), "3": boxes_per_comp.get(3, 0),
            "4": boxes_per_comp.get(4, 0), "5+": boxes_per_comp.get(5, 0),
            "pct_unexplained": _pct(boxes_per_comp, 0),
            "pct_exactly_one": _pct(boxes_per_comp, 1),
        },
        "distinct_classes_per_ink_component": {
            "0": classes_per_comp.get(0, 0), "1": classes_per_comp.get(1, 0),
            "2": classes_per_comp.get(2, 0), "3+": sum(
                classes_per_comp.get(k, 0) for k in (3, 4, 5)),
            "pct_more_than_one_class": round(
                100.0 * sum(classes_per_comp.get(k, 0) for k in (2, 3, 4, 5))
                / (sum(classes_per_comp.values()) or 1), 1),
        },
        "ink_components_per_box": {
            "0": comps_per_box.get(0, 0), "1": comps_per_box.get(1, 0),
            "2": comps_per_box.get(2, 0), "3": comps_per_box.get(3, 0),
            "4": comps_per_box.get(4, 0), "5+": comps_per_box.get(5, 0),
            "pct_covering_no_whole_component": _pct(comps_per_box, 0),
            "pct_exactly_one": _pct(comps_per_box, 1),
        },
        "notation_classes_per_ink_component": {
            "0": notation_classes_per_comp.get(0, 0),
            "1": notation_classes_per_comp.get(1, 0),
            "2": notation_classes_per_comp.get(2, 0),
            "3+": sum(notation_classes_per_comp.get(k, 0) for k in (3, 4, 5)),
            "pct_more_than_one_class": round(
                100.0 * sum(notation_classes_per_comp.get(k, 0)
                            for k in (2, 3, 4, 5))
                / (sum(notation_classes_per_comp.values()) or 1), 1),
            "excluded": sorted(_STRUCTURAL),
        },
        "top_contested_components": dict(multi_class_examples.most_common(15)),
        "top_contested_components_excluding_structural":
            dict(notation_contest.most_common(20)),
        "top_classes_covering_no_whole_component":
            dict(box_covers_nothing_by_class.most_common(15)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record")
    ap.add_argument("--label", default="?")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    outdir = _REPO / "benchmarks/omr-shape-role-2026-09/out"
    outdir.mkdir(parents=True, exist_ok=True)

    if a.all:
        from tools.library.score_library import library_root
        root = Path(library_root())
        results = []
        for label, rel in _RECORDS:
            p = root / rel
            dst = outdir / ("ink-vs-boxes--%s.json" % rel.split("/")[-1]
                            .split(".")[0])
            print("===", label, p, flush=True)
            if not p.exists():
                print("   MISSING", flush=True)
                continue
            # one subprocess per record: these are 146 MB and 461 MB
            rc = subprocess.call(
                [sys.executable, __file__, "--record", str(p),
                 "--label", label, "--out", str(dst)],
                env={**os.environ, "PYTHONPATH": str(_REPO)})
            if rc != 0:
                print("   FAILED rc=%d" % rc, flush=True)
                continue
            results.append(json.loads(dst.read_text()))
        (outdir / "ink-vs-boxes--all.json").write_text(
            json.dumps(results, indent=1))
        for r in results:
            print()
            print(r["label"], r["provenance"])
            print("  ink components %d, detector boxes %d"
                  % (r["counts"]["ink_components"], r["counts"]["detector_boxes"]))
            print("  boxes per ink component  ", r["boxes_per_ink_component"])
            print("  classes per ink component", r["distinct_classes_per_ink_component"])
            print("  notation classes per comp", r["notation_classes_per_ink_component"])
            print("  ink components per box   ", r["ink_components_per_box"])
        return 0

    if not a.record:
        ap.error("--record or --all")
    res = run(Path(a.record), a.label)
    text = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(text)
        print("wrote", a.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
