"""Per-candidate raw OCR texts + lexicon verdict for ONE page (diagnosis; Surya capped at 64 tokens here ONLY to keep it fast).

    python3 direction_cand_texts.py <pdf> <page> <out.json>
"""
import os, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"; os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)
import numpy as np
pdf, page, out = sys.argv[1:4]
from tools.omr.staged import gather as G
from tools.omr import staff_labels_surya as SU, staff_labels_tesseract as TE, direction_text as DT
from tools.omr.direction_lexicon import lookup


def hook(log, pws, cells, local, detections):
    pd = G._direction_page_dict(pws, cells, local, detections)
    cands = DT.find_candidates(pws, pd)
    sp = float(np.median([DT._spacing(s) for s in pws.staves]))
    crops = [DT.crop_for(pws.page, c, sp) for c in cands]
    su = SU.read_crops_text(crops, max_tokens=64) if crops else []
    te = TE.read_crops_text(crops) if crops else []
    rows = []
    for c, a, b in zip(cands, su, te):
        la, lb = lookup(a), lookup(b)
        rows.append(dict(staff=c.staff_index, measure=c.measure_index, bbox=c.bbox_page, w_sp=round((c.bbox_page[2] - c.bbox_page[0]) / sp, 1),
                         h_sp=round((c.bbox_page[3] - c.bbox_page[1]) / sp, 1), n=c.n_components, placement=c.placement,
                         surya=a, tess=b, surya_ok=la.text if la else None, tess_ok=lb.text if lb else None))
    json.dump(rows, open(out, "w"), indent=1)
    for r in rows:
        print("CAND", r["staff"], r["bbox"][:2], r["w_sp"], r["h_sp"], "S=%r T=%r -> %s" % (r["surya"], r["tess"], r["surya_ok"] or r["tess_ok"]))


G.gather_direction_words = hook
cm = SU.worker_session(); cm.__enter__()
from tools.omr.staged.__main__ import main
main([pdf, "--pages", page, "--weights", "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt", "--through", "gather"])
cm.__exit__(None, None, None)
