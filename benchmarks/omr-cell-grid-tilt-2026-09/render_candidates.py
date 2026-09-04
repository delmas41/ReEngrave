"""Zoom renders for the 3 silent-miss candidates: stored grid (orange),
measured bands at label x (red), label centre (green), measured half-step
slots (cyan ticks: solid=line, faint=space)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from audit_labels_vs_measured_grid import (  # noqa: E402
    MAIN, SHAMIR, bands_at_x, find_image, load_json_either,
)

CANDS = [
    ("benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1",
     "brahms1-p2-sys1-s20-m6", "noteheadHalfInSpace"),
    ("benchmarks/omr-labeling-hollow3-2026-09-durand-lamer",
     "lamer-p5-sys0-s2-m0", "noteheadWholeOnLine"),
    ("benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1",
     "mahler1-p4-sys0-s0-m9", "noteheadHalfInSpace"),
]

outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "cand")
outdir.mkdir(parents=True, exist_ok=True)

for batch, cell_id, want_cls in CANDS:
    man = {e["cell_id"]: e for e in load_json_either(f"{batch}/cells.json")}
    entry = man[cell_id]
    ys = sorted(entry["staff_line_ys_canonical"])
    spacing = float(np.median(np.diff(ys)))
    vdir = None
    for root in (MAIN, SHAMIR):
        for name in ("verdicts-merged", "verdicts"):
            d = root / batch / name
            if d.is_dir():
                vdir = d
                break
        if vdir:
            break
    v = json.loads((vdir / f"{cell_id}.verdict.json").read_text())
    labels = [a for a in v.get("added_detections", [])
              if a.get("human_class") == want_cls]
    img_path = find_image(batch, cell_id)
    gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    _, ib = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = ib > 0
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for sy in ys:
        cv2.line(img, (0, int(sy)), (img.shape[1], int(sy)), (0, 140, 255), 2)
    for i, a in enumerate(labels):
        bbox = a["bbox"]
        cx = bbox["x"] + bbox["w"] / 2.0
        cy = bbox["y"] + bbox["h"] / 2.0
        # inside-staff filter same as audit
        if cy < ys[0] - 0.25 * spacing or cy > ys[-1] + 0.25 * spacing:
            continue
        bb = bands_at_x(ink, cx, spacing)
        meas = []
        for sy in ys:
            cands = [c for c in bb if abs(c - sy) <= 0.55 * spacing]
            meas.append(min(cands, key=lambda c: abs(c - sy)) if cands else None)
        disp = float(np.median([m - s for m, s in zip(meas, ys) if m is not None]))
        grid = [m if m is not None else s + disp for m, s in zip(meas, ys)]
        for gy in grid:
            cv2.line(img, (int(cx - 2.5 * spacing), int(gy)),
                     (int(cx + 2.5 * spacing), int(gy)), (0, 0, 255), 2)
        for j in range(len(grid) - 1):
            my = (grid[j] + grid[j + 1]) / 2.0
            cv2.line(img, (int(cx - 1.2 * spacing), int(my)),
                     (int(cx + 1.2 * spacing), int(my)), (200, 200, 0), 1)
        cv2.rectangle(img, (int(bbox["x"]), int(bbox["y"])),
                      (int(bbox["x"] + bbox["w"]), int(bbox["y"] + bbox["h"])),
                      (0, 200, 0), 2)
        cv2.circle(img, (int(cx), int(cy)), 5, (0, 200, 0), -1)
        x0 = int(max(0, cx - 4 * spacing)); x1 = int(min(img.shape[1], cx + 4 * spacing))
        y0 = int(max(0, ys[0] - 2 * spacing)); y1 = int(min(img.shape[0], ys[-1] + 2 * spacing))
        crop = img[y0:y1, x0:x1].copy()
        cv2.putText(crop, want_cls.replace("notehead", ""), (6, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 120, 0), 2)
        cv2.imwrite(str(outdir / f"{cell_id}__{i}.png"), crop)
        print("wrote", cell_id, i, f"cy={cy:.0f} disp={disp:+.1f}")
