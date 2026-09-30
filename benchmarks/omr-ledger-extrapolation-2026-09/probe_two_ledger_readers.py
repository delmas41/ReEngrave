"""Run ONE page's gather on the 2.44 branch, then read every far regular
notehead with BOTH ledger readers on the SAME cell:

  A = 2.44  `_observe_ledger_printed_position` (its own row, from the log)
  B = ledger_grid.measure_ledger_rungs + server.snap_to_staff (the labeling
      UI's reader), on cell.image (staff lines present -- its native input)
      and on cell.image_no_staff (A's input), as two variants.

Dumps per-head JSON + a pickle of the cell rasters needed to cut crops.
"""
import json, pickle, sys, time
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab56d1d321c30c4bd")
import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged.pipeline import prepare_pages
from tools.omr.staged.record import Q, Subject
from tools.omr.annotate.ledger_grid import measure_ledger_rungs
from tools.omr.annotate.server import snap_to_staff
from tools.omr.yolo_detector import YoloDetector

pdf, page, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"

captured = {}
orig = G.gather_ledger_printed_position
def spy(log, cells, local, detections):
    captured["cells"], captured["local"], captured["dets"] = cells, local, detections
    return orig(log, cells, local, detections)
G.gather_ledger_printed_position = spy

t = time.time()
prepared = prepare_pages(pdf, [page], dpi=600)
log = G.gather(prepared, detector=YoloDetector(W), pdf_path=pdf)
print("gather", round(time.time() - t), "s", file=sys.stderr)

cells, local, dets = captured["cells"], captured["local"], captured["dets"]
by_key = {}
for c in cells:
    k = local.get(c.staff_index)
    if k is not None:
        by_key[(c.page_index, k[0], k[1], c.measure_index)] = c

out, rasters = [], {}
for cell_key, ds in dets.items():
    sub = Subject.from_key(cell_key)
    c = by_key.get((sub.page, sub.system, sub.staff, sub.cell))
    if c is None:
        continue
    lines = list(c.staff_line_ys_canonical or [])
    if len(lines) < 2:
        continue
    for gi, d in enumerate(ds):
        g = G.R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi)
        rows = log.rows(Q.LEDGER_PRINTED_POSITION, g)
        refs = log.refusals(Q.LEDGER_PRINTED_POSITION, g)
        if not rows and not refs:
            continue            # A did not consider it far (or not regular)
        spacing = (lines[-1] - lines[0]) / (len(lines) - 1)
        cx = d.x_canonical + d.width_canonical / 2
        cy = d.y_canonical + d.height_canonical / 2
        rc = log.rows(Q.NOTEHEAD_RECENTRE, g)
        if rc:
            cx += rc[-1].value[0] * spacing; cy += rc[-1].value[1] * spacing
        nsp = log.rows(Q.NOTEHEAD_STAFF_POSITION, g)
        rec = dict(subject=g.to_key(),
                   cx=cx, cy=cy, spacing=spacing, lines=lines,
                   side="above" if cy < lines[0] else "below",
                   staff_pos=float(nsp[-1].value) if nsp else None,
                   A=int(rows[-1].value) if rows else None,
                   A_bracket=rows[-1].detail.get("bracket") if rows else None,
                   A_note=rows[-1].detail.get("note") if rows else None,
                   A_reason=refs[-1].reason if refs and not rows else None,
                   name=d.smufl_name)
        for var, img in (("B", c.image), ("Bns", c.image_no_staff)):
            if img is None:
                rec[var] = None; continue
            gray = img if img.ndim == 2 else img.mean(axis=2).astype(np.uint8)
            r = measure_ledger_rungs(gray, lines, cx)
            s = snap_to_staff(lines, cy, r)
            s0 = snap_to_staff(lines, cy, None)
            rec[var] = dict(rungs=r, step=s["step"] if s else None,
                            grid_step=s0["step"] if s0 else None)
        out.append(rec)
        rasters[rec["subject"]] = (c.image, c.image_no_staff,
                                    getattr(c, "bbox_page_px", None))

json.dump(out, open(f"{tag}.json", "w"), indent=1, default=str)
pickle.dump(rasters, open(f"{tag}.pkl", "wb"))
print(len(out), "far heads", file=sys.stderr)
