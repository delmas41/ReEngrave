"""Render annotated crops for snap-eval failures so a human can see why.

Blue = measured staff lines. Yellow dashes = the OLD constant-spacing grid
(lines solid-ish, spaces faint). Red = measured ledger rungs at the note's x.
Green dot = the stored box centre. Cyan text = Sean's final class.

    python3 benchmarks/omr-snap-ledger-2026-09/diag_render_rows.py OUTDIR [filter]

filter: substring of "<batch>/<cell_id>"; default renders every row where
ink-snap and baseline disagree with each other or with the labeled class.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from probe_snap_ledger import BATCHES, collect_rows, find_cell_image  # noqa: E402

from tools.omr.annotate.ledger_grid import measure_ledger_rungs  # noqa: E402
from tools.omr.annotate.server import snap_to_staff  # noqa: E402


def main() -> None:
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    want = sys.argv[2] if len(sys.argv) > 2 else None

    rows = collect_rows(BATCHES)
    manifests = {
        b: {e["cell_id"]: e for e in json.loads((REPO / b / "cells.json").read_text())}
        for b in BATCHES
    }
    n = 0
    for r in rows:
        tag = f"{r['batch'].split('/')[-1]}/{r['cell_id']}"
        entry = manifests[r["batch"]][r["cell_id"]]
        ys = sorted(entry["staff_line_ys_canonical"])
        img_path = find_cell_image(r["cell_id"], r["png_rel"])
        if img_path is None:
            continue
        gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if gray is None or gray.shape[0] != entry.get("cell_canonical_h"):
            continue
        rungs = measure_ledger_rungs(gray, ys, r["cx"])
        base = snap_to_staff(ys, r["cy"])
        ink = snap_to_staff(ys, r["cy"], ledger_rungs=rungs)
        interesting = (
            base["position"] != r["truth"]
            or ink["position"] != r["truth"]
            or base["position"] != ink["position"]
        )
        if want is not None:
            if want not in tag:
                continue
        elif not interesting or r["zone"] == "inside":
            continue

        spacing = r["spacing"]
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        x0 = int(max(0, r["cx"] - 4 * spacing))
        x1 = int(min(gray.shape[1], r["cx"] + 4 * spacing))
        y0 = int(max(0, ys[0] - 7 * spacing))
        y1 = int(min(gray.shape[0], ys[-1] + 7 * spacing))

        for ly in ys:  # measured staff lines
            cv2.line(img, (x0, int(ly)), (x1, int(ly)), (255, 128, 0), 2)
        for k in range(1, 13):  # old extrapolated grid, above and below
            for yy in (ys[0] - k * spacing / 2.0, ys[-1] + k * spacing / 2.0):
                color = (0, 200, 200) if k % 2 == 0 else (0, 90, 90)
                cv2.line(img, (int(r["cx"] - 1.6 * spacing), int(yy)),
                         (int(r["cx"] + 1.6 * spacing), int(yy)), color, 1)
        for side in ("above", "below"):  # measured rungs
            for ry in rungs[side]:
                cv2.line(img, (int(r["cx"] - 2.2 * spacing), int(ry)),
                         (int(r["cx"] + 2.2 * spacing), int(ry)), (0, 0, 255), 2)
        cv2.circle(img, (int(r["cx"]), int(r["cy"])), 6, (0, 200, 0), -1)
        label = (f"{r['class']} d={r['d_out_spaces']} base={base['position']}"
                 f" ink={ink['position']}")
        cv2.putText(img, label, (x0 + 4, max(20, y0 + 24)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 120, 0), 2)
        crop = img[y0:y1, x0:x1]
        name = tag.replace("/", "__") + f"__{int(r['cx'])}x{int(r['cy'])}.png"
        cv2.imwrite(str(outdir / name), crop)
        n += 1
    print(f"wrote {n} crops to {outdir}")


if __name__ == "__main__":
    main()
