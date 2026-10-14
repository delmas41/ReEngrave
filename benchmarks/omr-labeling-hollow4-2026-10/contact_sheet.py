"""Print check for a built batch: a contact sheet of cells with the ranker's counters (red) and the
production detector's hollow boxes at conf >= 0.10 (blue) drawn, so a reader can see by eye whether the
chosen cells hold hollow heads and what the detector already finds.

    python3 benchmarks/omr-labeling-hollow4-2026-10/contact_sheet.py BATCH_DIR OUT.png [--n 12] [--stratum MISSED]
"""
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "omr-labeling-hollow2-2026-09"))
from hollow_score import score_cell  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--stratum", default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cols", type=int, default=3)
    a = ap.parse_args()
    cells = json.loads((a.batch / "cells.json").read_text())
    if a.stratum:
        cells = [c for c in cells if c.get("stratum") == a.stratum]
    random.Random(a.seed).shuffle(cells)
    cells = cells[: a.n]
    tiles = []
    W = 640
    for c in cells:
        img = cv2.imread(str(Path.cwd() / c["cell_png_path"]))
        if img is None:
            continue
        _, boxes = score_cell(c, Path.cwd())
        for (x, y, w, h) in boxes:
            cv2.rectangle(img, (x - 4, y - 4), (x + w + 4, y + h + 4), (0, 0, 255), 3)
        det_p = a.batch / "pool-dets" / f"{c['cell_id']}.json"
        if det_p.exists():
            for d in json.loads(det_p.read_text()):
                cv2.rectangle(img, (int(d["x"]), int(d["y"])), (int(d["x"] + d["w"]), int(d["y"] + d["h"])), (255, 80, 0), 3)
        s = W / img.shape[1]
        img = cv2.resize(img, (W, max(1, int(img.shape[0] * s))))
        cv2.putText(img, f"{c['cell_id']} [{c.get('stratum')}] ctr={c.get('hollow_candidates')} "
                         f"p10={c.get('prod_hollow_conf10')}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 120, 0), 1)
        tiles.append(img)
    rows = []
    for i in range(0, len(tiles), a.cols):
        row = tiles[i:i + a.cols]
        hmax = max(t.shape[0] for t in row)
        row = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in row]
        while len(row) < a.cols:
            row.append(np.full((hmax, W + 4, 3), 255, np.uint8))
        rows.append(np.hstack(row))
    cv2.imwrite(str(a.out), np.vstack(rows))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
