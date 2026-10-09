"""Per-crop readings and times for every stop/ordering policy, ONE page per run (2026-10-08).

    python3 direction_stop_experiment.py <pdf> <page> <tag> <outdir>

For every candidate (the CURRENT finder, erase-padded crops) it records: Tesseract's text and time; Surya with the
20 s guard and no token cap (the branch's current reader); Surya with a width-scaled cap (`cap = CAP_BASE + CAP_PER_SPACE * crop_width_in_spaces`)
and the same guard. Policies are then compared OFFLINE (direction_stop_analyze.py) on these rows, so no policy sees a different crop.
"""
from __future__ import annotations
import json, os, sys, time, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
os.environ.pop("OMR_DIRECTION_TEXT_SCAN_GATE", None)
import numpy as np

WEIGHTS = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
CAP_BASE = int(os.environ.get("CAP_BASE", "32"))
CAP_PER_SPACE = int(os.environ.get("CAP_PER_SPACE", "4"))
R: dict = {}


def main():
    pdf, page, tag, outdir = sys.argv[1:5]
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged import gather as G
    from tools.omr import staff_labels_surya as SU, staff_labels_tesseract as TE, direction_text as DT

    def hook(log, pws, cells, local, detections):
        pd = G._direction_page_dict(pws, cells, local, detections)
        cands = DT.find_candidates(pws, pd)
        sp = float(np.median([DT._spacing(s) for s in pws.staves]))
        raw = DT._page_ink(pws.page)
        erase = ((raw > 0) & (DT._blank_detections(raw, pd, sp, DT.DEFAULT_BAND_CONFIG) == 0)).astype(np.uint8) * 255
        crops = [DT.crop_for(pws.page, c, sp, erase=erase) for c in cands]
        rows = []
        for c, crop in zip(cands, crops):
            w_sp = crop.shape[1] / DT.MIN_CROP_SPACING_PX
            t = time.perf_counter(); te = TE.read_crops_text([crop])[0]; t_te = time.perf_counter() - t
            if SU._SESSION is None:
                SU._reopen_session()
            t = time.perf_counter(); sg = SU.read_crops_text([crop], crop_timeout_s=DT.DIRECTION_CROP_TIMEOUT_S)[0]; t_sg = time.perf_counter() - t
            if SU._SESSION is None:
                SU._reopen_session()
            cap = CAP_BASE + int(round(CAP_PER_SPACE * w_sp))
            t = time.perf_counter(); sc = SU.read_crops_text([crop], max_tokens=cap, crop_timeout_s=DT.DIRECTION_CROP_TIMEOUT_S)[0]; t_sc = time.perf_counter() - t
            if SU._SESSION is None:
                SU._reopen_session()
            rows.append(dict(staff=c.staff_index, measure=c.measure_index, x=c.x_page, bbox=c.bbox_page, w_sp=round(w_sp, 2), cap=cap,
                             tess=te, t_tess=round(t_te, 2), surya_guard=sg, t_surya_guard=round(t_sg, 2),
                             surya_cap=sc, t_surya_cap=round(t_sc, 2)))
            print("ROW", c.staff_index, c.x_page, repr(te), repr(sg), round(t_sg, 1), repr(sc), round(t_sc, 1), flush=True)
        R.update(tag=tag, rows=rows)
        (outdir / f"stop_{tag}.json").write_text(json.dumps(R, indent=1))

    G.gather_direction_words = hook
    cm = SU.worker_session(); cm.__enter__()
    try:
        from tools.omr.staged.__main__ import main as staged_main
        staged_main([pdf, "--pages", page, "--weights", WEIGHTS, "--through", "gather"])
    finally:
        cm.__exit__(None, None, None)


if __name__ == "__main__":
    main()
