"""ROADMAP 2.196 Q4 + row check. READ-ONLY measurement; no code under tools/ is touched.

Re-runs several weight files over the SAME cells the 2.193 cause step used and reads the RAW per-class head scores (pre-NMS)
on every anchor that overlaps each accidental ink (IoU >= 0.5 with the production winner box, the 2.193 definition).
Rows read: BOTH natural rows (61 and 171, the model spells the class twice), plus flat/sharp rows, per weights.
usage: PYTHONPATH=<src checkout of origin/main> python3 q4_scores.py CAUSE.json OUT.json
  CAUSE.json = 2.193 lane-report-2.193/cause_2_193.json (every accidental ink of the sample)."""
import json, pathlib, random, sys
import numpy as np
from tools.omr.staged import lane_report as LR
from tools.omr.staged.pipeline import prepare_pages
from tools.omr.staged import weight_routing as WR
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

CAUSE, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
W = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights")
WEIGHTS = {"prod": W / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt",
           "hollowft": W / "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt",
           "d25_epoch0": W / "round5-sweep/distill25/epoch0.pt",
           "dsv2base": W / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"}
ROWS = {"flat59": 59, "nat61": 61, "natS62": 62, "sharp63": 63, "flat170": 170, "nat171": 171, "sharp172": 172, "keynat68": 68}
N_CTRL_NAT, N_CTRL_OTHER = 100, 60


class Cap:
    def __enter__(self):
        from ultralytics.models.yolo.detect.predict import DetectionPredictor
        from ultralytics.utils import nms
        self.rec = {}
        self.nms, self.cr = nms.non_max_suppression, DetectionPredictor.construct_results
        rec, o_nms, o_cr = self.rec, self.nms, self.cr

        def w_nms(prediction, *a, **k):
            p = prediction[0] if isinstance(prediction, (list, tuple)) else prediction
            rec["pred"] = p.detach().clone().float().cpu()
            return o_nms(prediction, *a, **k)

        def w_cr(s, preds, img, orig_imgs, *a, **k):
            rec["ishape"] = tuple(int(v) for v in img.shape[2:])
            rec["oshape"] = tuple(orig_imgs[0].shape) if isinstance(orig_imgs, (list, tuple)) else tuple(orig_imgs.shape[-2:])
            return o_cr(s, preds, img, orig_imgs, *a, **k)
        nms.non_max_suppression, DetectionPredictor.construct_results = w_nms, w_cr
        return self

    def __exit__(self, *e):
        from ultralytics.models.yolo.detect.predict import DetectionPredictor
        from ultralytics.utils import nms
        nms.non_max_suppression, DetectionPredictor.construct_results = self.nms, self.cr


def iou(a, B):
    ix0 = np.maximum(a[0], B[:, 0]); iy0 = np.maximum(a[1], B[:, 1]); ix1 = np.minimum(a[2], B[:, 2]); iy1 = np.minimum(a[3], B[:, 3])
    inter = np.clip(ix1 - ix0, 0, None) * np.clip(iy1 - iy0, 0, None)
    return inter / np.maximum((a[2] - a[0]) * (a[3] - a[1]) + (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1]) - inter, 1e-9)


def main():
    from ultralytics.utils import ops
    import torch
    cause = json.load(open(CAUSE))
    rng = random.Random(196)
    chosen = {}
    for plate, rows in cause.items():
        tgt = [r for r in rows if r["shape"] == "natural" and not r["has_natural"]]
        cn = [r for r in rows if r["shape"] == "natural" and r["has_natural"]]
        co = [r for r in rows if r["shape"] in ("flat", "sharp") and not r["has_natural"]]
        k = N_CTRL_NAT // 2
        chosen[plate] = ([dict(r, grp="target") for r in tgt] + [dict(r, grp="ctrl_natural_read") for r in rng.sample(cn, min(k, len(cn)))]
                         + [dict(r, grp="ctrl_flat_sharp") for r in rng.sample(co, min(N_CTRL_OTHER // 2, len(co)))])
    sample = LR.load_sample()
    result = {"weights": {k: str(v) for k, v in WEIGHTS.items()}, "rows": ROWS, "inks": []}
    for plate in ("litolff", "brahms"):
        src = LR.slice_dir(plate, sample["record_tag"])
        pages = LR.loaded_pages(sample, plate)
        obs = [json.loads(l) for l in open(src / "observations.jsonl")]
        cellbox = {tuple(o["subject"].split("/")[1:5]): o["value"] for o in obs if o["quantity"] == "cell_box"}
        bycell = {}
        for r in chosen[plate]:
            bycell.setdefault(tuple(r["cell"]), []).append(r)
        pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
        dets = {k: YoloDetector(str(v)) for k, v in WEIGHTS.items()}
        for d in dets.values():
            d._ensure_loaded()
        prep = prepare_pages(pdf, pages)
        n = 0
        for pws, cells in prep:
            for c in cells:
                bb = getattr(c, "bbox_page_px", None)
                if not bb:
                    continue
                key = next((k for k, v in cellbox.items() if int(k[0]) == c.page_index and all(abs(a - b) < 1.5 for a, b in zip(v, bb))), None)
                if key is None or key not in bycell:
                    continue
                n += 1
                per = {}
                for wn, det in dets.items():
                    with Cap() as cap:
                        det.detect(c, conf_threshold=0.25, imgsz=imgsz_for_cell(c))
                    pred = cap.rec["pred"][0]
                    xywh = pred[:4].T.clone()
                    xyxy = torch.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2, xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], 1)
                    xyxy = ops.scale_boxes(cap.rec["ishape"], xyxy, cap.rec["oshape"][:2]).numpy()
                    per[wn] = (xyxy, pred[4:].numpy())
                for r in bycell[key]:
                    box = np.array(r["bbox"], float)
                    out = dict(plate=plate, grp=r["grp"], cell=r["cell"], gi=r["gi"], cls=r["cls"], shape=r["shape"], has_natural=r["has_natural"],
                               nat_max_2193=r["nat_max"], scores={})
                    for wn, (xyxy, sc) in per.items():
                        ov = iou(box, xyxy) >= 0.5
                        s = {rn: (round(float(sc[ri][ov].max()), 4) if ov.any() else None) for rn, ri in ROWS.items()}
                        s["n_anchors"] = int(ov.sum())
                        s["any_cls_max"] = round(float(sc[:, ov].max()), 4) if ov.any() else None
                        out["scores"][wn] = s
                    result["inks"].append(out)
                if n % 10 == 0:
                    print(plate, "cells", n, "inks", len(result["inks"]), flush=True)
                    json.dump(result, open(OUT, "w"))
        json.dump(result, open(OUT, "w"))
    print("done", len(result["inks"]))


main()
