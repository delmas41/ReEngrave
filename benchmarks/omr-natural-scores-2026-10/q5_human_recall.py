"""ROADMAP 2.196 Q4 on HUMAN truth. READ-ONLY. The 101 target inks are selected by 'production offered no natural', so production-vs-base on them is biased.
The unbiased population is the accidentals Sean's labeling passes boxed BY HAND (data/user-labeled v1-v4 [nc208 labels], v14-v22: "round-3 passes added ...
accidentals by hand"; v24 is excluded - its accidentals are production-teacher output, not human). For every such box, every weights file is run on the cell
PNG at imgsz 896 (the training size), and the RAW head scores (pre-NMS) of the box's own class rows are read on every anchor with IoU >= 0.5 with the human box.
usage: q5_human_recall.py DATA_ROOT VARIANT_DIR OUT.json [native|prod]
  native = imgsz 896 (the fine-tune's training size; staff space ~35 px on these cells). prod = the imgsz production uses (staff space 16 px,
  tools/omr/yolo_detector.imgsz_for_cell), the staff space measured here by autocorrelation of the row-ink profile (lag 24..250 px; lag 8 gave noise peaks on half the cells - first prod-scale attempt, kept as q5_human_recall_attempt2.json).
  FIRST RUN (native) FAILED ITS OWN CONTROL: flats/sharps - the classes production reads well - scored ~0 on their own labels, because the cells are
  hi-res crops (staff space ~85 px) shown at a scale production never uses. Kept in q5_human_recall_native.json as that evidence."""
import glob, json, pathlib, sys
import numpy as np
from PIL import Image
ROOT, VAR, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
MODE = sys.argv[4] if len(sys.argv) > 4 else "native"
W = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights")
MODELS = {"prod": W / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt", "hollowft": W / "deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt",
          "dsv2base": W / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt", "prod_baseNatRows": VAR / "prod_with_dsv2base_natural_rows.pt"}
ROWSET = {"natural": [61, 62, 171], "flat": [59, 60, 170], "sharp": [63, 64, 172]}
G = {r: g for g, rs in ROWSET.items() for r in rs}
VERS = [("_nc208", "v1-2026-05-18-orchestral"), ("_nc208", "v2-2026-06-08-beet5"), ("_nc208", "v3-2026-06-09-mahler5"), ("_nc208", "v4-2026-06-10-la-mer"),
        (None, "v14-2026-09-03-complete-litolff"), (None, "v15-2026-09-03-complete-peters"), (None, "v16-2026-09-03-complete-eulenburg"),
        (None, "v17-2026-09-03-complete-simrock"), (None, "v18-2026-09-03-complete-breitkopf"), (None, "v19-2026-09-03-complete-mahler1"),
        (None, "v20-2026-09-03-complete-elgar1"), (None, "v21-2026-09-03-complete-lamer"), (None, "v22-2026-09-04-simrock-dense")]


def iou(a, B):
    ix0 = np.maximum(a[0], B[:, 0]); iy0 = np.maximum(a[1], B[:, 1]); ix1 = np.minimum(a[2], B[:, 2]); iy1 = np.minimum(a[3], B[:, 3])
    inter = np.clip(ix1 - ix0, 0, None) * np.clip(iy1 - iy0, 0, None)
    return inter / np.maximum((a[2] - a[0]) * (a[3] - a[1]) + (B[:, 2] - B[:, 0]) * (B[:, 3] - B[:, 1]) - inter, 1e-9)


cells = []
for d, v in VERS:
    vd = ROOT / d / v if d else ROOT / v
    for lf in sorted((vd / "labels").glob("*.txt")):
        rows = [l.split() for l in open(lf) if len(l.split()) >= 5]
        acc = [(int(p[0]), [float(x) for x in p[1:5]]) for p in rows if int(p[0]) in G]
        if not acc:
            continue
        img = next(iter((vd / "images").glob(lf.stem + ".*")), None) or next(iter((ROOT / v / "images").glob(lf.stem + ".*")), None)
        if img:
            cells.append((v, lf.stem, img, acc))
print("cells with a human accidental box", len(cells), "boxes", sum(len(c[3]) for c in cells), flush=True)

def staff_space(gray):
    prof = (gray < 128).sum(1).astype(float); prof -= prof.mean()
    ac = np.correlate(prof, prof, "full")[len(prof) - 1:]
    lo, hi = 24, min(250, len(ac) - 1)
    return int(lo + np.argmax(ac[lo:hi]))


def pick_imgsz(im_bgr):
    if MODE == "native":
        return 896
    h, w = im_bgr.shape[:2]
    sp = staff_space(im_bgr.mean(2))
    return max(64, min(2048, int(round(16 * max(h, w) / sp / 32)) * 32))


from ultralytics import YOLO
from ultralytics.utils import nms as NMS
import torch
rec = {}
orig = NMS.non_max_suppression
def hook(prediction, *a, **k):
    p = prediction[0] if isinstance(prediction, (list, tuple)) else prediction
    rec["pred"] = p.detach().clone().float().cpu()
    return orig(prediction, *a, **k)
NMS.non_max_suppression = hook
import ultralytics.models.yolo.detect.predict as DP
res = []
import os
ONLY = os.environ.get("ONLY_MODELS")
for mn, mp in MODELS.items():
    if ONLY and mn not in ONLY.split(","):
        continue
    model = YOLO(str(mp))
    for i, (v, stem, img, acc) in enumerate(cells):
        im = np.asarray(Image.open(img).convert("RGB"))[:, :, ::-1]
        h, w = im.shape[:2]
        isz = pick_imgsz(im)
        model.predict(im, imgsz=isz, conf=0.25, verbose=False)
        pred = rec["pred"][0]
        # letterbox geometry: ultralytics scales the long side to imgsz, pads centre (rect=False -> square pad for predict? read from model output size)
        xywh = pred[:4].T
        scale = min(isz / h, isz / w)
        # use ops.scale_boxes with the actual letterbox shape (pred coordinates are in the letterboxed input frame)
        from ultralytics.utils import ops
        nh, nw = round(h * scale), round(w * scale)
        ish = (((nh + 31) // 32) * 32, ((nw + 31) // 32) * 32)   # rect letterbox, stride 32 (predict uses auto=True)
        xyxy = torch.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2, xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], 1)
        xyxy = ops.scale_boxes(ish, xyxy, (h, w)).numpy()
        sc = pred[4:].numpy()
        for c, (x, y, bw, bh) in acc:
            box = np.array([(x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h])
            ov = iou(box, xyxy) >= 0.5
            g = G[c]
            own = max((float(sc[r][ov].max()) if ov.any() else 0.0) for r in ROWSET[g])
            nat = max((float(sc[r][ov].max()) if ov.any() else 0.0) for r in ROWSET["natural"])
            fl = max((float(sc[r][ov].max()) if ov.any() else 0.0) for r in ROWSET["flat"]); sh = max((float(sc[r][ov].max()) if ov.any() else 0.0) for r in ROWSET["sharp"])
            res.append(dict(model=mn, flat_row=round(fl, 4), sharp_row=round(sh, 4), ver=v, cell=stem, grp=g, label_cls=c, own=round(own, 4), nat=round(nat, 4), n_anchors=int(ov.sum()), imgsz=isz))
        if i % 50 == 0:
            print(mn, i, "/", len(cells), flush=True)
    json.dump(res, open(OUT, "w"))
print("done", len(res))
