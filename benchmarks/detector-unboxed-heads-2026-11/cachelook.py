"""ROADMAP 2.267 -- read the detector cache's RAW candidates (pre-NMS) for a master cell.

MEASUREMENT ONLY. Loads a cell from the master cell map (never re-cuts), builds the same cache key
`YoloDetector.detect` builds, and looks it up read-only in the shared detector caches. It never calls the
detector. A cell with no entry at a conf is reported as MISSING, never re-run.

Candidate boxes are in NETWORK pixels (letterboxed `img_shape`); `to_cell` maps them to cell pixels with the
same `ops.scale_boxes` the serve path uses. The cell pixel frame is `cell.image` (canonical image).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

R = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
CACHES = [R / "detector-cache", R / "detector-cache-gt1030"]
WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
if not WEIGHTS.exists():
    WEIGHTS = Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
PDF = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
CONFS = (0.25, 0.2, 0.15, 0.1, 0.05, 0.03, 0.01, 0.02, 0.04)


def cell_source(cell):
    import cv2
    img = cell.image
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    return img if img.shape[2] == 3 else cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)


def lookup(cell, confs=CONFS, imgsz=None):
    """-> {conf: (meta, arrays, path)} for every conf that has an entry (production imgsz for the cell)."""
    from tools.omr import detector_cache as dc
    from tools.omr.yolo_detector import imgsz_for_cell
    src = cell_source(cell)
    isz = imgsz or imgsz_for_cell(cell)
    out = {}
    for conf in confs:
        key = dc.make_key(weights_path=str(WEIGHTS), source=src, conf=conf, imgsz=isz, device=None)
        dg = dc.key_digest(key)
        for root in CACHES:
            hit = dc._load(root, dg, key)
            if hit is not None:
                out[conf] = (hit[0], hit[1], str(dc._path(root, dg)))
                break
    return isz, out


def candidates_cell_px(meta, arrays, cell_shape):
    """-> list of dict(cls, score, x0, y0, x1, y1) in CELL pixels, from the stored candidates (best class only)."""
    import torch
    from ultralytics.utils import ops
    ishape = tuple(meta["img_shape"])
    box = arrays["box0"]            # cx, cy, w, h in network px
    if len(box) == 0:
        return []
    cx, cy, w, h = box[:, 0], box[:, 1], box[:, 2], box[:, 3]
    xyxy = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 1)
    sc = ops.scale_boxes(ishape, torch.from_numpy(xyxy.astype(np.float32)).clone(), cell_shape).numpy()
    return [dict(cls=int(c), score=float(s), x0=float(b[0]), y0=float(b[1]), x1=float(b[2]), y1=float(b[3]), idx=int(i))
            for b, c, s, i in zip(sc, arrays["cls0"], arrays["score0"], arrays["idx0"])]


# --------------------------------------------------------------------------- serve (reproduce the production boxes)

def serve(cell, meta, arrays, conf=0.25, iou=0.7, agnostic=False):
    """The detector's boxes for a cell as the cache would serve them: list of (cls, score, x0, y0, x1, y1) in CELL px."""
    from tools.omr import detector_cache as dc
    res = dc._serve(meta, arrays, [cell_source(cell)], conf, iou, agnostic)
    b = res[0].boxes
    xy = b.xyxy.cpu().numpy(); cf = b.conf.cpu().numpy(); cl = b.cls.cpu().numpy()
    return [(int(c), float(s), *map(float, x)) for x, s, c in zip(xy, cf, cl)]


def to_page(cell, x, y):
    x0, y0 = cell.bbox_page_px[0], cell.bbox_page_px[1]
    return x0 + x / cell.upscale_factor, y0 + y / cell.upscale_factor


def to_cell(cell, px, py):
    x0, y0 = cell.bbox_page_px[0], cell.bbox_page_px[1]
    return (px - x0) * cell.upscale_factor, (py - y0) * cell.upscale_factor


_NAMES = None


def class_names():
    global _NAMES
    if _NAMES is None:
        from ultralytics import YOLO
        _NAMES = YOLO(str(WEIGHTS)).names
    return _NAMES
