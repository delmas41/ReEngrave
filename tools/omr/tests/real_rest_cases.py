"""Test support (ROADMAP 2.288 round 4): load a REAL case dumped by `benchmarks/rests-claim-first-2026-11/dump_real_cases.py` -- the page strokes (kind, size, what they touch,
their pixel masks) and the page raster crop round one of Sean's answered rest tiles -- and rebuild the `page_map` / `raw` the gather had, so the rest reader's own function
(`page_claim_names.rest_box_verdict`) is replayed on the real pixels with no gather. No synthetic drawing: every number is the page's."""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from typing import Any, Dict, List

import numpy as np

CASE_DIR = pathlib.Path(__file__).resolve().parents[3] / "benchmarks" / "rests-claim-first-2026-11" / "real_cases"
CASES_JSON = CASE_DIR.parent / "real_cases.json"


class CropRaw:
    """The page raster seen through a crop: `raw[y, a:b]` with PAGE coordinates (what the page raster answers), 255 (paper) outside the crop."""

    def __init__(self, crop: np.ndarray, origin, shape):
        self.crop, self.ox, self.oy, self.shape = crop, int(origin[0]), int(origin[1]), tuple(shape)

    def __getitem__(self, key):
        y, sl = key
        a, b = sl.start or 0, sl.stop if sl.stop is not None else self.shape[1]
        out = np.full(max(0, b - a), 255, dtype=np.uint8)
        cy = int(y) - self.oy
        if 0 <= cy < self.crop.shape[0]:
            lo, hi = max(a, self.ox), min(b, self.ox + self.crop.shape[1])
            if hi > lo:
                out[lo - a:hi - a] = self.crop[cy, lo - self.ox:hi - self.ox]
        return out


def case_ids() -> List[str]:
    return sorted(p.stem for p in CASE_DIR.glob("*.npz"))


def load(case_id: str) -> Dict[str, Any]:
    """`dict(meta, page_map, raw, index, box, cls, owner, detail)` for one case."""
    from tools.omr.staged import page_claim_names as PCN
    z = np.load(CASE_DIR / (case_id + ".npz"), allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    ords = sorted(int(k) for k in meta["strokes"])
    n = max(ords) + 1
    strokes: List[Any] = [None] * n
    masks: List[Any] = [None] * n
    far = SimpleNamespace(kind="none", box=(-10 ** 6, -10 ** 6, 1, 1), area_sp2=0.0, length_sp=0.0, angle_deg=0.0, thickness_sp=0.0, thickness_spread_sp=0.0, staff_space_local=None,
                          touches=[], joined_to=[], fill=0.0, component=-1)
    for i in range(n):
        strokes[i], masks[i] = far, (np.zeros((1, 1), bool), 0, 0)
    for k, d in meta["strokes"].items():
        i = int(k)
        strokes[i] = SimpleNamespace(**{a: (tuple(b) if a == "box" else b) for a, b in d.items() if a != "mask_xy"})
        strokes[i].touches = [tuple(t) for t in d["touches"]]
        strokes[i].joined_to = [tuple(t) for t in d["joined_to"]]
        masks[i] = (np.asarray(z["m_%d" % i], dtype=bool), d["mask_xy"][0], d["mask_xy"][1])
    pm = SimpleNamespace(strokes=strokes, masks=masks, scale=meta["scale"], sp=meta["sp"], barlines=[])
    index = PCN.StrokeIndex(*PCN._boxes_of(pm))
    return dict(meta=meta, page_map=pm, raw=CropRaw(z["raw"], meta["raw_origin"], meta["page_shape"]), index=index, box=tuple(meta["box"]), cls=meta["cls"], owner=meta["owner"],
                detail=meta["detail"])


def verdict(c: Dict[str, Any]) -> Dict[str, Any]:
    from tools.omr.staged import page_claim_names as PCN
    return PCN.rest_box_verdict(c["page_map"], c["index"], c["raw"], c["box"], c["cls"], c["owner"], c["detail"])
