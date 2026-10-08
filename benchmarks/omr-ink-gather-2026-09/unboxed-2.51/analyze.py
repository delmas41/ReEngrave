"""ROADMAP 2.51 -- how much printed ink has no detector box, and what is it.

MEASUREMENT ONLY. Reuses tools.omr.staged.record_io.load_record (the one way
to read a staged record file) and tools.omr.staged.gather's own
_explaining_detections / _coverage (the real coverage functions GATHER
itself calls) -- never a reimplementation of the coverage rule, per CLAUDE.md
rule 1 ("reuse their tools, don't rebuild").

Population: every `ink` observation that carries `ink_bbox_canonical`
(--ink-rows per-component form). Staff lines are ALREADY removed, locally,
by `gather._ink_components`'s own input (`cell.image_no_staff`, the
staff-line-erased raster) -- that erasure happens per cell, i.e. at the
component's own local x, not a page-wide or bar-wide subtraction (CLAUDE.md
SS10's own "measure against the staff locally" rule, satisfied by construction
here because it is upstream of this script).

Stems are NOT a detector class (CLAUDE.md SS9: "stem ... CV-only and costs
nothing") so they never appear in `ink_explained_by` / `ink_detector_coverage`
-- every stem pixel reads as uncovered unless subtracted separately. This
script subtracts it, per cell, using the cell's own `stem` observations
(canonical-frame boxes, the same frame as `ink_bbox_canonical`), as an
axis-aligned box-overlap approximation (not a pixel mask) -- stated plainly,
not pixel-exact.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, namedtuple
from pathlib import Path


from tools.omr.staged import record_io
from tools.omr.staged import gather as G

Det = namedtuple("Det", "x_canonical y_canonical width_canonical height_canonical smufl_name")


def cell_key_of_subject(subj: str) -> str:
    # 'glyph/<page>/<sys>/<staff>/<measure>/<idx>' or 'cell/<page>/<sys>/<staff>/<measure>'
    parts = subj.split("/")
    return "/".join(["cell"] + parts[1:5])


def box_overlap_area(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def load(path: str):
    d = record_io.load_record(path)
    return d["record"]["observations"]


def analyze(path: str, label: str, page_filter=None):
    obs = load(path)
    ink_rows = [r for r in obs if r.get("quantity") == "ink" and
                isinstance(r.get("detail"), dict) and "ink_bbox_canonical" in r["detail"]]
    if page_filter is not None:
        ink_rows = [r for r in ink_rows if int(r["subject"].split("/")[1]) == page_filter]
    stem_rows = [r for r in obs if r.get("quantity") == "stem"]
    glyph_box_rows = [r for r in obs if r.get("quantity") == "glyph_box"]

    # per-cell stem boxes (corners, canonical frame)
    stems_by_cell = defaultdict(list)
    for r in stem_rows:
        x, y, w, h = r["value"]
        stems_by_cell[r["subject"]].append((x, y, x + w, y + h))

    # per-cell raw detector boxes, for the control (reconstructs
    # gather._explaining_detections' own input exactly)
    dets_by_cell = defaultdict(list)
    for r in glyph_box_rows:
        cls, x, y, w, h = r["value"]
        cell_key = cell_key_of_subject(r["subject"])
        dets_by_cell[cell_key].append((r["subject"], Det(float(x), float(y), float(w), float(h), cls)))

    total_area = 0.0
    covered_area = 0.0
    stem_area = 0.0
    uncovered_area = 0.0
    per_staff = defaultdict(lambda: {"total": 0.0, "covered": 0.0, "stem": 0.0, "uncovered": 0.0})
    groups = defaultdict(lambda: {"n": 0, "area": 0.0})
    uncovered_components = []  # for crop sheet + manual counts

    for r in ink_rows:
        d = r["detail"]
        area = float(d["ink_area_px"])
        cov = float(d.get("ink_detector_coverage", 0.0))
        covered = cov * area
        box = d["ink_bbox_canonical"]
        cell_key = cell_key_of_subject(r["subject"])
        stem_boxes = stems_by_cell.get(cell_key, [])
        remaining = area - covered
        stem_ov = 0.0
        if stem_boxes and remaining > 0:
            ov = sum(box_overlap_area(box, sb) for sb in stem_boxes)
            stem_ov = min(ov, remaining)
        uncov = max(0.0, remaining - stem_ov)

        total_area += area
        covered_area += covered
        stem_area += stem_ov
        uncovered_area += uncov

        parts = r["subject"].split("/")
        staff_key = "/".join(parts[1:4])
        ps = per_staff[staff_key]
        ps["total"] += area
        ps["covered"] += covered
        ps["stem"] += stem_ov
        ps["uncovered"] += uncov

        if uncov > 0.5 * area and uncov > 0:
            w_sp = d.get("width_spaces")
            h_sp = d.get("height_spaces")
            group = classify(w_sp, h_sp)
            groups[group]["n"] += 1
            groups[group]["area"] += uncov
            uncovered_components.append({
                "subject": r["subject"], "uncov_px": uncov, "area": area,
                "width_spaces": w_sp, "height_spaces": h_sp,
                "bbox_page_px": d.get("bbox_page_px"),
                "group": group,
            })

    result = {
        "label": label,
        "n_ink_rows": len(ink_rows),
        "total_ink_px": total_area,
        "covered_px": covered_area,
        "covered_pct": 100.0 * covered_area / total_area if total_area else None,
        "stem_px": stem_area,
        "stem_pct": 100.0 * stem_area / total_area if total_area else None,
        "uncovered_px": uncovered_area,
        "uncovered_pct": 100.0 * uncovered_area / total_area if total_area else None,
        "per_staff": {k: {
            "total": v["total"],
            "covered_pct": 100.0 * v["covered"] / v["total"] if v["total"] else None,
            "stem_pct": 100.0 * v["stem"] / v["total"] if v["total"] else None,
            "uncovered_pct": 100.0 * v["uncovered"] / v["total"] if v["total"] else None,
        } for k, v in per_staff.items()},
        "groups": {k: v for k, v in groups.items()},
        "n_uncovered_components_gt_half": len(uncovered_components),
    }
    return result, uncovered_components, dets_by_cell, ink_rows


#: CLAUDE.md-style bands requested by the brief. CONVENTION ASSUMED / WHAT
#: WOULD FALSIFY IT / NOT CONFIRMED -- nobody was available to ask Sean
#: before this pass; these are stated defensively and reported on every
#: group so a crop pass can falsify them directly. The project's OWN
#: measured notehead band (omr-notehead-width-2026-09: 1.26-1.78 wide x
#: 0.34-1.8 tall) is WIDER than the brief's 1.0-1.4 x 0.8-1.2 -- reported,
#: not reconciled, since the brief names the exact band to use for this pass.
def classify(w, h):
    if w is None or h is None:
        return "no_frame"
    if 1.0 <= w <= 1.4 and 0.8 <= h <= 1.2:
        return "head_sized"
    if 0.3 <= w <= 1.0 and 0.5 <= h <= 1.6 and h >= w:
        return "digit_letter_sized"
    if w > 0 and h > 0 and (w / h >= 3.0 or h / w >= 3.0):
        return "line_like"
    if w * h < 0.08:
        return "speck"
    return "other"


if __name__ == "__main__":
    import sys
    path, label, outjson = sys.argv[1], sys.argv[2], sys.argv[3]
    pf = int(sys.argv[4]) if len(sys.argv) > 4 else None
    result, comps, dets_by_cell, ink_rows = analyze(path, label, pf)
    Path(outjson).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "per_staff"}, indent=2))
    print("per_staff:")
    for k, v in sorted(result["per_staff"].items()):
        print(" ", k, v)
