"""ROADMAP 2.51 control (CLAUDE.md rule 7: a control must be able to fail).

Reuses the REAL coverage functions GATHER itself calls
(`tools.omr.staged.gather._explaining_detections`, `._coverage`) -- never a
reimplementation -- fed a detection list reconstructed EXACTLY from the
record's own `glyph_box` rows (class, x, y, w, h, all canonical-frame,
written at GATHER time by the same detector run). Picks N real notehead
detections on the count page, recomputes each one's own ink component's
coverage with that ONE detection box removed from its cell's detection list,
and reports before/after. A component whose coverage does NOT drop after its
sole explaining detection is removed is the control's own failure mode
(another detection, or a merged neighbour, also explains it) -- reported,
not hidden.
"""
from __future__ import annotations
import sys
from collections import namedtuple, defaultdict

from tools.omr.staged import record_io
from tools.omr.staged import gather as G

Det = namedtuple("Det", "x_canonical y_canonical width_canonical height_canonical smufl_name")


def cell_key_of(subj):
    parts = subj.split("/")
    return "/".join(["cell"] + parts[1:5])


def run(record_path, page_index, n=5):
    d = record_io.load_record(record_path)
    obs = d["record"]["observations"]
    ink = [r for r in obs if r.get("quantity") == "ink" and isinstance(r.get("detail"), dict)
           and "ink_bbox_canonical" in r["detail"]]
    gb = [r for r in obs if r.get("quantity") == "glyph_box"]
    gb_by_cell = defaultdict(list)
    for r in gb:
        gb_by_cell[cell_key_of(r["subject"])].append(r)

    ink_by_cell = defaultdict(list)
    for r in ink:
        ink_by_cell[cell_key_of(r["subject"])].append(r)

    # real notehead detections on this page, isolated (one detection
    # explains one ink component at ~full coverage -- so deleting it is a
    # clean test, not confounded by a merge with a neighbour)
    candidates = []
    for r in gb:
        cls = r["value"][0]
        if not cls.startswith("notehead"):
            continue
        sub_parts = r["subject"].split("/")
        if int(sub_parts[1]) != page_index:
            continue
        cell_key = cell_key_of(r["subject"])
        gx, gy, gw, gh = r["value"][1:5]
        gbox = (gx, gy, gx + gw, gy + gh)
        # find the ink component this detection mostly explains
        best = None
        for ir in ink_by_cell.get(cell_key, ()):
            ibox = ir["detail"]["ink_bbox_canonical"]
            ix0, iy0, ix1, iy1 = ibox
            iarea = max(1.0, (ix1 - ix0) * (iy1 - iy0))
            ov = _overlap(gbox, ibox)
            if ov <= 0:
                continue
            ratio = ov / iarea  # fraction of the INK COMPONENT this detection covers
            if best is None or ratio > best[1]:
                best = (ir, ratio)
        if best is None:
            continue
        ir, ratio = best
        cov = ir["detail"].get("ink_detector_coverage", 0.0)
        explained_by = ir["detail"].get("ink_explained_by", [])
        if ratio > 0.6 and cov > 0.5 and explained_by == [cls]:
            candidates.append((r, ir, cell_key))
        if len(candidates) >= n:
            break

    print(f"found {len(candidates)} isolated real-head candidates")
    for det_row, ink_row, cell_key in candidates:
        cls, gx, gy, gw, gh = det_row["value"]
        spacing = ink_row["detail"].get("cell_staff_space_px")
        # rebuild the cell's detection list minus this one
        cell_dets = []
        for r in gb_by_cell.get(cell_key, ()):
            if r["id"] == det_row["id"]:
                continue
            c2, x2, y2, w2, h2 = r["value"]
            cell_dets.append(Det(float(x2), float(y2), float(w2), float(h2), c2))
        boxes = G._explaining_detections(cell_dets, spacing) if spacing else []
        ib = ink_row["detail"]["ink_bbox_canonical"]
        x0, y0, x1, y1 = ib
        box = (int(x0), int(y0), int(x1 - x0), int(y1 - y0))
        cov_after, who_after = G._coverage(box, boxes)
        before = ink_row["detail"].get("ink_detector_coverage")
        w_sp, h_sp = ink_row["detail"].get("width_spaces"), ink_row["detail"].get("height_spaces")
        head_sized = w_sp is not None and h_sp is not None and 1.0 <= w_sp <= 1.8 and 0.3 <= h_sp <= 1.8
        print(f"  {det_row['subject']} ink={ink_row['subject']} "
              f"before_cov={before:.3f} after_cov={cov_after:.3f} "
              f"w_sp={w_sp} h_sp={h_sp} head_sized_window={head_sized} "
              f"PASS={'yes' if cov_after < 0.1 else 'FAIL (still explained by ' + str(who_after) + ')'}")


def _overlap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("page", type=int)
    ap.add_argument("--n", type=int, default=5)
    args = ap.parse_args()
    run(args.record, args.page, args.n)
