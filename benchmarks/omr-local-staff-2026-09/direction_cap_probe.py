"""Probe ONE candidate crop: Surya uncapped / cap 64 (x3) / cap 64 + guard / Tesseract.

    python3 direction_cap_probe.py <pdf> <page> <staff> <x_page> [crop_out.png]
"""
import os, sys, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"; os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)
import numpy as np
pdf, page, staff, xp = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
from tools.omr.staged import gather as G
from tools.omr import staff_labels_surya as SU, staff_labels_tesseract as TE, direction_text as DT
OUT = {}


def hook(log, pws, cells, local, detections):
    pd = G._direction_page_dict(pws, cells, local, detections)
    cands = DT.find_candidates(pws, pd)
    c = [c for c in cands if c.staff_index == staff and c.x_page == xp][0]
    sp = float(np.median([DT._spacing(s) for s in pws.staves]))
    crop = DT.crop_for(pws.page, c, sp)
    if len(sys.argv) > 5:
        import cv2; cv2.imwrite(sys.argv[5], crop)
    OUT["tess"] = TE.read_crops_text([crop])
    for name, kw in [("uncapped", {}), ("cap64_a", {"max_tokens": 64}), ("cap64_b", {"max_tokens": 64}),
                     ("cap64_c", {"max_tokens": 64}), ("cap64_guard", {"max_tokens": 64, "crop_timeout_s": 20}),
                     ("uncapped_b", {})]:
        t = time.perf_counter(); r = SU.read_crops_text([crop], **kw); OUT[name] = (r, round(time.perf_counter() - t, 1))
    print("PROBE", json.dumps(OUT, default=str))


G.gather_direction_words = hook
cm = SU.worker_session(); cm.__enter__()
from tools.omr.staged.__main__ import main
main([pdf, "--pages", page, "--weights", "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt", "--through", "gather"])
cm.__exit__(None, None, None)
