"""Visual-check sheet #1 (Sean, 2026-09-29, before/alongside training): "I will
want to visual check some of these also to verify." Revised per Sean's
follow-up on a DIFFERENT audit's crops confusing him: every crop here is the
FULL cell (>= 1200 px wide after upscaling, so the whole bar and the staff
above/below are always shown, staff shaded as a band), boxes drawn thick with
a legend on the image, and ONE plain question with exact Y/N codes at the top
-- see crop_common.py.

Two contact sheets, cut directly from the cell PNGs (no page re-render needed
-- these are already-cut training cells with `staff_line_ys_canonical` in the
same pixel frame):

  crop-b-additions/   ~16 crops of the teacher rest boxes arm B ADDS as
                       labels, stratified by class and confidence. ORANGE =
                       the candidate box. GRAY = every OTHER human box already
                       in this cell (any class), for context only -- nothing
                       to judge there.

  crop-c-painted/      ~8 crops of regions arm C erases, BEFORE/AFTER pair
                       side by side, same RED box on both.

Reads data/rest-exp-B-completed/additions.json and
data/rest-exp-C-painted/painted.json (written by
build_rest_experiment_corpora.py) -- run that first for both arms.

    python3 .../crop_visual_check_corpora.py
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from crop_common import render_cell, render_pair
from rest_experiment_lib import load_manifest_staff_lines, load_full_labels

REPO = Path.cwd()
SURVEY = REPO / "benchmarks" / "omr-labeling-survey-2026-09"
OUT = SURVEY / "out" / "rest-experiment"
ADDITIONS = REPO / "data" / "rest-exp-B-completed" / "additions.json"
PAINTED = REPO / "data" / "rest-exp-C-painted" / "painted.json"
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"
SEED = 20260929

ORANGE = (230, 120, 0)
RED = (220, 0, 0)
GRAY = (140, 140, 140)


def stratified_sample(records, n, rng, class_key="cls"):
    """Spread n picks evenly across classes present, and within each class
    evenly across its confidence range (low/mid/high)."""
    by_class = defaultdict(list)
    for r in records:
        by_class[r[class_key]].append(r)
    for v in by_class.values():
        v.sort(key=lambda r: r["conf"])
    classes = sorted(by_class)
    if not classes:
        return []
    base, extra = divmod(n, len(classes))
    quota = {c: base + (1 if i < extra else 0) for i, c in enumerate(classes)}
    picked = []
    for c in classes:
        pool = by_class[c]
        k = min(quota[c], len(pool))
        if k <= 0:
            continue
        idxs = sorted({int(round(j * (len(pool) - 1) / max(1, k - 1))) for j in range(k)})
        picked.extend(pool[j] for j in idxs)
    rng.shuffle(picked)
    return picked[:n] if len(picked) > n else picked


def _other_human_boxes_px(cid: str, version: str, versions: list[str], names: list[str],
                          img_shape, exclude_bbox) -> list:
    """Every human box in this cell OTHER than the one being highlighted, in
    pixel coords -- drawn GRAY, for context only."""
    H, W = img_shape[:2]
    out = []
    for (cls, cx, cy, w, h) in load_full_labels(cid, versions, names):
        x0, y0 = (cx - w / 2) * W, (cy - h / 2) * H
        x1, y1 = (cx + w / 2) * W, (cy + h / 2) * H
        ex0, ey0, ex1, ey1 = exclude_bbox
        if abs(x0 - ex0) < 2 and abs(y0 - ey0) < 2 and abs(x1 - ex1) < 2 and abs(y1 - ey1) < 2:
            continue
        out.append((x0, y0, x1, y1, GRAY, cls))
    return out


def build_additions_sheet(n: int = 16):
    if not ADDITIONS.exists():
        print(f"missing {ADDITIONS} -- build arm B first")
        return []
    records = json.loads(ADDITIONS.read_text())
    if not records:
        print("no additions recorded for arm B")
        return []
    versions = [l.strip() for l in
                (REPO / "data" / "specialist-rests" / "catalog-versions.txt").read_text().splitlines()
                if l.strip()]
    names = json.loads(CLASS_NAMES_JSON.read_text())
    rng = random.Random(SEED)
    picked = stratified_sample(records, n, rng)
    out_dir = OUT / "crop-b-additions"
    manifest = []
    for i, r in enumerate(picked, 1):
        import cv2
        img = cv2.imread(r["image_path"])
        if img is None:
            continue
        ys = load_manifest_staff_lines(r["cell_id"])
        x0, y0, x1, y1 = r["bbox_px"]
        others = _other_human_boxes_px(r["cell_id"], r["version"], versions, names, img.shape,
                                       (x0, y0, x1, y1))
        boxes = others + [(x0, y0, x1, y1, ORANGE, f"{r['cls']} conf={r['conf']:.2f}")]
        name = f"b-add-{i:02d}.png"
        title = f"{name}   cell {r['cell_id']}   class {r['cls']}   teacher conf {r['conf']:.2f}"
        question = (f"Is the ORANGE box a real {r['cls']}?  "
                    f"Y = yes, add it as a label   N = no, do not add it")
        legend = [(ORANGE, f"candidate to ADD ({r['cls']})"),
                  (GRAY, "other existing human boxes (context only, not to judge)")]
        ok = render_cell(r["image_path"], ys, boxes, title, question, legend, out_dir / name)
        if not ok:
            continue
        manifest.append({
            "n": i, "file": name, "cell_id": r["cell_id"], "version": r["version"],
            "cls": r["cls"], "conf": round(r["conf"], 3),
            "question": question, "answer_codes": {"Y": "real rest, add label",
                                                    "N": "not a real rest, do not add"},
            "VERDICT_none_yet": None,
        })
    (out_dir / "manifest.json").write_text(json.dumps({
        "sheet": "arm B additions -- teacher rest boxes about to be added as labels",
        "source": str(ADDITIONS), "seed": SEED, "n": len(manifest), "crops": manifest,
    }, indent=2))
    print(f"wrote {len(manifest)} crops -> {out_dir}")
    return manifest


def build_painted_sheet(n: int = 8):
    if not PAINTED.exists():
        print(f"missing {PAINTED} -- build arm C first")
        return []
    records = json.loads(PAINTED.read_text())
    if not records:
        print("no painted regions recorded for arm C")
        return []
    rng = random.Random(SEED + 1)
    picked = stratified_sample(records, n, rng)
    out_dir = OUT / "crop-c-painted"
    manifest = []
    for i, r in enumerate(picked, 1):
        ys = load_manifest_staff_lines(r["cell_id"])
        x0, y0, x1, y1 = r["bbox_px"]
        name = f"c-paint-{i:02d}.png"
        title = f"{name}   cell {r['cell_id']}   class {r['cls']}   teacher conf {r['conf']:.2f}"
        question = ("Was erasing the RED region correct?  "
                    "Y = yes, it was noise/not a real symbol   N = no, it erased something real")
        legend = [(RED, f"region ERASED to paper color (was: {r['cls']}, unmatched to any human box)")]
        ok = render_pair(r["orig_image_path"], r["painted_image_path"], ys,
                         (x0, y0, x1, y1, RED, r["cls"]), title, question, legend, out_dir / name)
        if not ok:
            continue
        manifest.append({
            "n": i, "file": name, "cell_id": r["cell_id"], "version": r["version"],
            "cls": r["cls"], "conf": round(r["conf"], 3),
            "question": question, "answer_codes": {"Y": "correctly erased noise",
                                                    "N": "erased something real"},
            "VERDICT_none_yet": None,
        })
    (out_dir / "manifest.json").write_text(json.dumps({
        "sheet": "arm C paint-outs -- unmatched teacher rest regions erased to paper color",
        "source": str(PAINTED), "seed": SEED + 1, "n": len(manifest), "crops": manifest,
    }, indent=2))
    print(f"wrote {len(manifest)} crops -> {out_dir}")
    return manifest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    build_additions_sheet(16)
    build_painted_sheet(8)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
