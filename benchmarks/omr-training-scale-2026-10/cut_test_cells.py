"""Cut the TEST pages' cells with the product path's own cutter (hand_truth.session.measure_cells -- staff detect +
barlines + extract_measures, 600 dpi like the CLI) and save PNG + metadata under runs/2.110/test-cells/<tag>/.
Used by the leakage check (pixel hashes) and the inference side of the shown-staff-space measurement."""
import json, sys
from pathlib import Path
import cv2
sys.path.insert(0, str(Path.cwd()))
from tools.omr.hand_truth.session import measure_cells, _render

E = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")
PAGES = {
    "brahms317803_p0": (E / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 0),
    "litolff984073_p1": (E / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 1),
}
for tag, (pdf, pg) in PAGES.items():
    out = Path("runs/2.110/test-cells") / tag
    out.mkdir(parents=True, exist_ok=True)
    img = _render(pdf, pg, 600)
    pws, cells = measure_cells(img)
    meta = []
    for c in cells:
        cid = f"s{c.system_index}-st{c.staff_index}-m{c.measure_index}"
        cv2.imwrite(str(out / f"{cid}.png"), c.image)
        meta.append({"cell_id": cid, "system_index": c.system_index, "staff_index": c.staff_index,
                     "measure_index": c.measure_index, "h": int(c.image.shape[0]), "w": int(c.image.shape[1]),
                     "bbox_page_px": list(c.bbox_page_px), "staff_line_ys_canonical": list(c.staff_line_ys_canonical)})
    (out / "cells.json").write_text(json.dumps(meta))
    print(tag, len(cells), "cells")
