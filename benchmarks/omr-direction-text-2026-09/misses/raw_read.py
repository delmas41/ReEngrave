"""Raw OCR text for EVERY candidate (accepted or not): python3 raw_read.py tag...  -> /private/tmp/dtmiss/raw_<tag>.json"""
import json, os, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
import numpy as np
from tools.omr import direction_text as DT
from tools.omr import staff_labels_surya as SU
cm = SU.worker_session(); cm.__enter__()
try:
    for tag in sys.argv[1:]:
        pws, pd = pickle.load(open(f"/private/tmp/dtmiss/{tag}.pkl", "rb"))
        cands = DT.find_candidates(pws, pd)
        readers = DT.default_readers(pws.page)
        sp = float(np.median([DT._spacing(s) for s in pws.staves]))
        raw = DT._page_ink(pws.page)
        erase = ((raw > 0) & (DT._blank_detections(raw, pd, sp, DT.DEFAULT_BAND_CONFIG) == 0)).astype(np.uint8) * 255
        crops = [DT.crop_for(pws.page, c, sp, erase=erase) for c in cands]
        res = {}
        t = time.perf_counter()
        for name, fn in readers:
            res[name] = list(fn(crops))
        dt = time.perf_counter() - t
        out = [dict(staff=c.staff_index, measure=c.measure_index, bbox=list(map(int, c.bbox_page)), placement=c.placement,
                    **{n: res[n][i] for n in res}) for i, c in enumerate(cands)]
        json.dump(dict(read_s=dt, cands=out), open(f"/private/tmp/dtmiss/raw_{tag}.json", "w"), indent=1)
        print(tag, len(cands), round(dt, 1), "s")
finally:
    cm.__exit__(None, None, None)
