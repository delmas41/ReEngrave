"""Measure the ANCHOR populations behind the round-9 hypothesis.

For every adjudicated arc box on the gauntlet — 176 human-real, 260
certified-fake — and both of its ENDS, record where the cell's own detected
noteheads sit relative to that end: dx in notehead widths (positive =
OUTSIDE the arc span, the tie-pairing direction; negative = inside, under
the arc), dy in staff spaces (vertical distance from the notehead centre to
the arc box's y-interval, 0 when level with it). Also each end's distance
to the cell's left/right crop edge (the cut-exemption side).

The analysis script (`analyze_anchor_populations.py`) sweeps windows over
these raw records; no constant is chosen here.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

B = Path("benchmarks/omr-queue-arcs-2026-09")
A = Path("benchmarks/omr-arc-anchor-2026-09")


def load_truth_fakes():
    truth, fakes = {}, {}
    for vf in sorted((B / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        t, f = [], []
        for d in v.get("detections", []):
            cls = d.get("human_corrected_class") or d.get("model_predicted_class")
            bb = d.get("human_bbox") or d.get("model_bbox")
            if not bb:
                continue
            box = (bb["x"], bb["y"], bb["w"], bb["h"])
            if d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ("tie", "slur"):
                t.append((cls, box))
            elif d.get("verdict") == "FP" and d.get("model_predicted_class") in ("tie", "slur"):
                f.append((d["model_predicted_class"], box))
        for a in v.get("added_detections", []):
            if a.get("human_class") in ("tie", "slur"):
                bb = a["bbox"]
                t.append((a["human_class"], (bb["x"], bb["y"], bb["w"], bb["h"])))
        truth[v["cell_id"]], fakes[v["cell_id"]] = t, f
    return truth, fakes


def end_records(box, noteheads, nh_w, sp, cell_w, n_keep=8):
    """Per-end: (edge_dist_spaces, [(dx_nhw, dy_sp), ...nearest noteheads])."""
    x, y, w, h = box
    out = []
    for end_x, left in ((x, True), (x + w, False)):
        edge = (end_x if left else cell_w - end_x) / sp
        cands = []
        for nb in noteheads:
            nx, ny, nw, nh_ = nb
            nxc, nyc = nx + nw / 2.0, ny + nh_ / 2.0
            dx = (end_x - nxc) if left else (nxc - end_x)   # + = outside
            dy = max(0.0, y - nyc, nyc - (y + h))
            cands.append((round(dx / nh_w, 2), round(dy / sp, 2)))
        cands.sort(key=lambda t: abs(t[0]) + t[1])
        out.append({"edge_sp": round(edge, 2), "nh": cands[:n_keep]})
    return out


def main():
    truth, fakes = load_truth_fakes()
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    cache = json.load(open(A / "yolo_dets_cache.json"))
    rows = []
    for cid in truth:
        e, c = mans.get(cid), cache.get(cid)
        if e is None or c is None:
            continue
        ys = e.get("staff_line_ys_canonical") or []
        if len(ys) < 2:
            continue
        sp = (max(ys) - min(ys)) / (len(ys) - 1)
        cell_w = e["cell_canonical_w"]
        nhs = [n["box"] for n in c["noteheads"]]
        widths = sorted(n[2] for n in nhs) or [sp]
        nh_w = widths[len(widths) // 2] or sp
        for kind, group in (("real", truth[cid]), ("fake", fakes.get(cid, []))):
            for cls, box in group:
                yc = box[1] + box[3] / 2.0
                in_band = min(ys) <= yc <= max(ys)
                rows.append({
                    "cell": cid, "kind": kind, "cls": cls, "box": list(box),
                    "family": "jag" if (kind == "fake" and in_band) else
                              ("bleed" if kind == "fake" else ""),
                    "n_nh": len(nhs),
                    "ends": end_records(box, nhs, nh_w, sp, cell_w),
                })
    json.dump(rows, open(A / "anchor_populations.json", "w"))
    n_real = sum(r["kind"] == "real" for r in rows)
    n_fake = len(rows) - n_real
    n_jag = sum(r["family"] == "jag" for r in rows)
    print(f"{len(rows)} boxes: {n_real} real, {n_fake} fake "
          f"({n_jag} jag / {n_fake - n_jag} bleed)")


if __name__ == "__main__":
    main()
