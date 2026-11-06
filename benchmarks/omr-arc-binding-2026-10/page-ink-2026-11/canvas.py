"""PAGE-INK ARCS feasibility (measure only; STAGED; docs/plan-2026-11-06-page-ink-arcs.md §7). Step 1: the page raster the page map is built on.

    python3 canvas.py PLATE PAGE OUTDIR

Renders the page, cuts the cells and erases the staff lines exactly as GATHER does (`pipeline.prepare_pages`), assembles the M2 page raster
(`page_strokes.assemble`: each staff's own erased band + page.binary outside) and carves the tilted barline columns out of it
(`barline_columns.fit_columns` + `page_strokes.carve_columns`). No detector, no OCR, no tools/ code changed. Writes OUTDIR/PLATE-pPAGE.canvas.png
(0 = ink), the raw page raster, and the staff lines (page px) to a json.
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged import pipeline as P  # noqa: E402
from tools.omr.staged import page_strokes as PS  # noqa: E402
from tools.omr.staged import barline_columns as BC  # noqa: E402


def main():
    plate, page, out = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    pdf = str(L.LIB / L.PLATES[plate]["pdf"])
    t0 = time.time()
    (pws, cells), = P.prepare_pages(pdf, [page])
    t1 = time.time()
    asm = PS.assemble(pws, cells)
    sp = PS.page_spacing(pws)
    cols = BC.fit_columns(pws)
    bars = PS.carve_columns(asm.canvas, cols, sp)
    stem = "%s-p%d" % (plate, page)
    cv2.imwrite(str(out / (stem + ".canvas.png")), asm.canvas)
    cv2.imwrite(str(out / (stem + ".raw.png")), pws.page.binary)
    staves = [dict(index=int(s.staff_index), system=int(getattr(s, "system_index", -1)), lines=[float(y) for y in s.line_ys],
                   sp=float(s.line_spacing_px), x0=int(getattr(s, "x_start", 0) or 0), x1=int(getattr(s, "x_end", 0) or 0)) for s in pws.staves]
    json.dump(dict(plate=plate, page=page, sp=sp, shape=list(asm.canvas.shape), staves=staves,
                   barlines=[dict(box=list(b["box"]), system=b["system"]) for b in bars], stats={k: v for k, v in asm.stats.items() if k != "per_staff"},
                   seconds=dict(prepare=round(t1 - t0, 1), assemble_carve=round(time.time() - t1, 1))),
              open(out / (stem + ".page.json"), "w"), indent=1)
    print(stem, "sp", sp, "shape", asm.canvas.shape, "staves", len(staves), "barline rules", len(bars), "prepare %.0fs" % (t1 - t0))


if __name__ == "__main__":
    main()
