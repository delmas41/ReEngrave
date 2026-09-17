"""Which cell does the pipeline put p.62's meter CHANGE at, and off what ink?

⚠️ THIS IS A SIDE FINDING OF THE A-DUR-5 WORK AND IT IS CHECKED, NOT ASSERTED.
`ASSUMPTIONS.md` A-DUR-5, the 2026-09-09 handoff and
`omr-staged-meter-boundary-2026-09/FINDINGS.md` all place Litolff Beethoven 5
p.62's printed `3/4` at CELL 8. Cropping the plate puts it at the head of CELL
6. The two claims cannot both be right, and the difference matters beyond this
job: p.62 is the ONE true scan-side meter change this project has ever found,
and the cautionary/placement rules were measured against its cell index.

So this runs the shipped readers and prints, without interpretation: every
`timeSig*` detection on the page with its box, and the meter verdict.
"""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from tools.omr.staged import gather as G                       # noqa: E402
from tools.omr.staged import record as R                       # noqa: E402
from tools.omr.staged.record import Log, Q                     # noqa: E402

WEIGHTS = str(ROOT / "omr-weights"
              / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


def main() -> int:
    pdf, page = sys.argv[1], int(sys.argv[2])
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.yolo_detector import YoloDetector
    pws, cells = prepare_pages(pdf, [page], dpi=600)[0]
    det = YoloDetector(WEIGHTS)
    log = Log()
    local = G.gather_geometry(log, pws)
    G.gather_systems(log, pws, getattr(pws, "used_bridging", True))
    G.gather_measures(log, pws, cells, local)
    dets = G.gather_detections(log, cells, local, detector=det)
    G.gather_meter(log, pws, cells, local, dets)
    log.freeze()

    # every meter-shaped detection on the page, with the shape of its box
    print("timeSig* detections, with the box SHAPE in staff spaces:")
    by_cell = {}
    for key, ds in dets.items():
        sub = R.Subject.from_key(key)
        c = next((c for c in cells if c.staff_index in local
                  and local[c.staff_index] == (sub.system, sub.staff)
                  and c.measure_index == sub.cell), None)
        if c is None:
            continue
        ys = list(c.staff_line_ys_canonical or [])
        sp = (ys[-1] - ys[0]) / 4.0 if len(ys) >= 2 else 100.0
        for d in ds:
            if not d.smufl_name.startswith("timeSig"):
                continue
            by_cell.setdefault(sub.cell, []).append(
                (sub.staff, d.smufl_name, round(d.confidence, 3),
                 round(d.x_canonical / sp, 2), round(d.width_canonical / sp, 2),
                 round(d.height_canonical / sp, 2)))
    for cell in sorted(by_cell):
        print(f"  cell {cell}:")
        for (st, name, conf, x, w, h) in sorted(by_cell[cell]):
            flag = "  <-- at the cell's LEFT EDGE, barline-shaped" if (
                x < 0.1 and w < 0.6 and h > 1.0) else ""
            print(f"    staff {st:2d} {name:12s} conf={conf:.3f} "
                  f"x={x:5.2f} w={w:5.2f} h={h:5.2f} sp{flag}")
    if not by_cell:
        print("  none")

    print("\nQ.METER verdicts is an ADJUDICATE question; this arm reports the "
          "GATHERED glyph rows only:")
    for row in log.all_rows():
        if getattr(row, "quantity", None) != Q.METER_GLYPH:
            continue
        d = row.detail or {}
        if d.get("cell") is None:
            continue
        print(f"  {row.subject.to_key()}  cell={d.get('cell')} "
              f"value={getattr(row, 'value', None)} letter={d.get('letter')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
