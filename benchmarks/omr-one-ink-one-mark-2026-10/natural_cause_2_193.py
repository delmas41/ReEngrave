"""ROADMAP 2.193 cause step (rule 3). STAGED GATHER, measurement only.

On the frozen sample pages, for every cell that holds a non-key accidental box in the 20261020-night record, re-run the PRODUCTION detector
(same weights routing, same `imgsz_for_cell`, conf 0.25, class-wise NMS iou 0.7) and keep the RAW head tensor `(1, 4+nc, N)` that NMS receives.
For every accidental ink (a merged group as 2.186 merges it, or a single box) read:
  * the shape (staff-erased raster, `accidental_shape`),
  * the NATURAL class score over every anchor whose box overlaps the ink (IoU >= 0.5 with the winner box), whatever that anchor's best class,
  * why natural was or was not offered: NOT in the head at all (< floor everywhere) / BEATEN by argmax (>= floor but another class is the
    anchor's best) / PRESENT but not merged (a natural box survives NMS with IoU < 0.5).
usage: natural_cause_2_193.py OUT.json   (stdout: counts)"""
import collections, json, pathlib, sys
import numpy as np
from tools.omr.staged import lane_report as LR, one_ink as OI, accidental_shape as AS, gather as G
from tools.omr.staged.pipeline import prepare_pages
from tools.omr.staged import weight_routing as WR
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

OUT = pathlib.Path(sys.argv[1])


class Cap:
    """Capture the pre-NMS head tensor and the letterboxed input shape of the next predict call."""
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


def iou_xyxy(a, B):
    ix0 = np.maximum(a[0], B[:, 0]); iy0 = np.maximum(a[1], B[:, 1]); ix1 = np.minimum(a[2], B[:, 2]); iy1 = np.minimum(a[3], B[:, 3])
    inter = np.clip(ix1 - ix0, 0, None) * np.clip(iy1 - iy0, 0, None)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1]) - inter
    return inter / np.maximum(ua, 1e-9)


def main():
    from ultralytics.utils import ops
    import torch
    sample = LR.load_sample()
    result = {}
    for plate in ("litolff", "brahms"):
        src = LR.slice_dir(plate, sample["record_tag"])
        pages = LR.loaded_pages(sample, plate)
        obs = [json.loads(l) for l in open(src / "observations.jsonl")]
        cellbox = {tuple(o["subject"].split("/")[1:5]): o["value"] for o in obs if o["quantity"] == "cell_box"}
        want = set()
        for o in obs:
            if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "accidental" and not str(o["value"][0]).lower().startswith("key"):
                want.add(tuple(o["subject"].split("/")[1:5]))
        pdf = str(LR.LIB / LR.PLATES[plate]["pdf"])
        wpath, _, _ = WR.resolve_staged_weights(pdf, pages, weights="auto", route_weights=True)
        det = YoloDetector(wpath)
        det._ensure_loaded()
        names = det._class_names
        nat_id = [k for k, v in names.items() if v.lower() == "accidentalnatural"][0]
        print(plate, "weights", pathlib.Path(wpath).name, "natural id", nat_id, "cells wanted", len(want), flush=True)
        prep = prepare_pages(pdf, pages)
        rows = []
        ndone = 0
        for pws, cells in prep:
            for c in cells:
                bb = getattr(c, "bbox_page_px", None)
                if not bb:
                    continue
                key = next((k for k, v in cellbox.items() if int(k[0]) == c.page_index and all(abs(a - b) < 1.5 for a, b in zip(v, bb))), None)
                if key is None or key not in want:
                    continue
                with Cap() as cap:
                    dets = det.detect(c, conf_threshold=0.25, imgsz=imgsz_for_cell(c))
                ndone += 1
                dets = OI.merge(dets) if dets else []
                pred = cap.rec["pred"][0]                       # (4+nc, N)
                ishape, oshape = cap.rec["ishape"], cap.rec["oshape"]
                xywh = pred[:4].T.clone()
                xyxy = torch.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2, xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], 1)
                xyxy = ops.scale_boxes(ishape, xyxy, oshape[:2]).numpy()
                sc = pred[4:].numpy()                           # (nc, N)
                best = sc.argmax(0); bsc = sc.max(0)
                nat = sc[nat_id]
                for gi, d in enumerate(dets):
                    if d.category != "accidental" or d.smufl_name.lower().startswith("key") or getattr(d, "one_ink_absorbed_by", None) is not None:
                        continue
                    box = np.array([d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical, d.y_canonical + d.height_canonical], float)
                    ov = iou_xyxy(box, xyxy) >= OI.ONE_INK_IOU_MIN
                    img = getattr(c, "image_no_staff", None)
                    m = AS.measure(img, (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)) if img is not None else None
                    shp = AS.classify(m)["shape"]
                    offered = [d.smufl_name] + [r[0] for r in (getattr(d, "one_ink_rivals", None) or ())]
                    has_nat = any(o.lower() == "accidentalnatural" for o in offered)
                    nat_max = float(nat[ov].max()) if ov.any() else 0.0
                    loose = iou_xyxy(box, xyxy) > 0.1
                    nat_box_loose = bool(((best == nat_id) & (bsc > 0.25) & loose).any())
                    wid = [k for k, v in names.items() if v == d.smufl_name][0]
                    win_anchor_nat = float(nat[ov][np.argmax(sc[wid][ov])]) if ov.any() else 0.0
                    n_ov_best_nat = int(((best == nat_id) & ov).sum())
                    rows.append(dict(plate=plate, page=int(key[0]), cell=list(key), gi=gi, cls=d.smufl_name, conf=round(float(d.confidence), 4),
                                     offered=offered, has_natural=has_nat, shape=shp, nat_max=round(nat_max, 4), nat_at_winner_anchor=round(win_anchor_nat, 4),
                                     n_overlap_anchors=int(ov.sum()), n_anchor_best_is_nat=n_ov_best_nat, nat_box_loose=nat_box_loose,
                                     bbox=[float(v) for v in box], bbox_page_px=list(bb), merged=len(offered) > 1))
                if ndone % 10 == 0:
                    print(plate, "cells done", ndone, "rows", len(rows), flush=True)
        result[plate] = rows
        json.dump(result, open(OUT, "w"))
    for plate, rows in result.items():
        tgt = [r for r in rows if r["shape"] == "natural" and not r["has_natural"]]
        print("==", plate, "accidental inks", len(rows), "shape natural", sum(r["shape"] == "natural" for r in rows), "of which natural NOT offered", len(tgt),
              "(merged %d, single %d)" % (sum(r["merged"] for r in tgt), sum(not r["merged"] for r in tgt)))
        cause = collections.Counter()
        for r in tgt:
            if r["nat_max"] >= 0.25 and r["n_anchor_best_is_nat"] == 0:
                cause["beaten_by_argmax (natural >= .25 on an overlapping anchor, another class is that anchor's best)"] += 1
            elif r["nat_max"] >= 0.25:
                cause["natural_best_anchor_but_not_offered"] += 1
            elif r["nat_box_loose"]:
                cause["natural box survives nearby, iou<.5"] += 1
            else:
                cause["below_floor_everywhere"] += 1
        print(" ", dict(cause))
        v = sorted(r["nat_max"] for r in tgt)
        if v:
            q = lambda f: round(v[int(f * (len(v) - 1))], 3)
            print("  natural max score on the ink: min %.3f p10 %.3f p25 %.3f med %.3f p75 %.3f p90 %.3f max %.3f" % (v[0], q(.1), q(.25), q(.5), q(.75), q(.9), v[-1]))
        ctl = [r for r in rows if r["shape"] == "natural" and r["has_natural"]]
        w = sorted(r["nat_max"] for r in ctl)
        if w:
            print("  control (natural offered, shape natural) n=%d nat_max p10 %.3f med %.3f" % (len(w), w[int(.1 * (len(w) - 1))], w[len(w) // 2]))
        oth = [r for r in rows if r["shape"] in ("flat", "sharp") and not r["has_natural"]]
        w = sorted(r["nat_max"] for r in oth)
        if w:
            print("  control (shape flat/sharp, natural not offered) n=%d nat_max p50 %.3f p90 %.3f p99 %.3f max %.3f" % (len(w), w[len(w) // 2], w[int(.9 * (len(w) - 1))], w[int(.99 * (len(w) - 1))], w[-1]))


main()
