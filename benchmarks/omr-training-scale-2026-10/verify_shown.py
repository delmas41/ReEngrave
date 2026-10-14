"""ROADMAP 2.110 Step A.5 -- the staff space the model is SHOWN, one tool (shown_space.measure_space), three places:
  (a) TRAINING, OLD   : cells after the REAL ultralytics loader (YOLODataset.load_image, imgsz 896, augment off) -- long side -> imgsz
  (b) TRAINING, MATCHED: the pre-resized 640 canvases after the same loader (must be r == 1: nothing rescaled again)
  (c) INFERENCE: the product path's own cells of the two test pages, resized to `yolo_detector.imgsz_for_cell` (stride-32 rounded)
The mosaic/affine augmentation (ultralytics default scale=0.5: x U(0.5, 1.5) per sample, mosaic=1.0) then multiplies (a) and (b) alike.
Measured on the ink columns of the image (a 640 canvas is mostly white pad, which would dilute the row profile).
usage: verify_shown.py -> verify_shown.json + printed percentiles
"""
import json, sys
from pathlib import Path
import cv2, numpy as np, yaml
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(Path.cwd()))
from shown_space import measure_space
from ultralytics.data import YOLODataset


def ink_cols(img):
    g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cols = np.where((g < 128).any(axis=0))[0]
    return img[:, cols[0]: cols[-1] + 1] if len(cols) else img


def loaded(yaml_path, imgsz):
    y = yaml.safe_load(open(yaml_path))
    y["names"] = {i: n for i, n in enumerate(y["names"])} if isinstance(y["names"], list) else y["names"]
    ds = YOLODataset(img_path=y["train"], imgsz=imgsz, augment=False, data={**y, "nc": len(y["names"])}, task="detect", batch_size=8)
    out, seen = [], set()
    for i, f in enumerate(ds.im_files):
        if f in seen:
            continue
        seen.add(f)
        im, hw0, hw = ds.load_image(i)
        m = measure_space(ink_cols(im))
        out.append({"file": f, "orig_hw": list(hw0), "loaded_hw": list(hw), "rescaled_again": list(hw0) != list(hw), "space": None if m is None else m[0]})
    return out


def pct(v):
    v = np.array([x for x in v if x is not None])
    return {"n": int(len(v)), "p10": round(float(np.percentile(v, 10)), 1), "median": round(float(np.percentile(v, 50)), 1),
            "p90": round(float(np.percentile(v, 90)), 1), "frac_8_22": round(float(((v >= 8) & (v <= 22)).mean()), 3)}


def inference():
    from tools.omr.yolo_detector import imgsz_for_cell, TARGET_STAFF_SPACE_PX
    res = {}
    for tag in ("brahms317803_p0", "litolff984073_p1"):
        d = Path("runs/2.110/test-cells") / tag
        vals = []
        for m in json.load(open(d / "cells.json")):
            im = cv2.imread(str(d / f"{m['cell_id']}.png"))
            ys = m["staff_line_ys_canonical"]
            if im is None or len(ys) < 5:
                continue
            ns = type("C", (), {"staff_line_ys_canonical": ys, "image": im})()
            isz = imgsz_for_cell(ns)
            r = isz / max(im.shape[:2])
            sm = cv2.resize(im, None, fx=r, fy=r, interpolation=cv2.INTER_LINEAR)
            mm = measure_space(sm)
            vals.append(None if mm is None else mm[0])
        res[tag] = pct(vals)
    return res


if __name__ == "__main__":
    out = {}
    old = loaded("runs/2.110/old/catalog.yaml", 896)
    mat = loaded("runs/2.110/matched/catalog.yaml", 640)
    out["OLD_896"] = pct([r["space"] for r in old])
    out["MATCHED_640"] = pct([r["space"] for r in mat])
    out["MATCHED_rescaled_again_by_loader"] = sum(r["rescaled_again"] for r in mat)
    out["OLD_rescaled_by_loader"] = sum(r["rescaled_again"] for r in old)
    out["INFERENCE"] = inference()
    # no cell the survey could not measure
    out["OLD_unmeasurable"] = sum(r["space"] is None for r in old); out["MATCHED_unmeasurable"] = sum(r["space"] is None for r in mat)
    json.dump({"summary": out, "old": old, "matched": mat}, open(HERE / "verify_shown.json", "w"))
    print(json.dumps(out, indent=1))
