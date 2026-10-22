"""Non-clef forgetting audit on the Bach WTC verdict set.

The clef fine-tune (deepscoresv2-yolov8l-clef-ft-*) must not have damaged the
model's ability to detect the symbols it was already good at (noteheads, rests,
flags…). This eval quantifies that directly.

Method — score both models against the SAME human-confirmed ground truth:

  Ground truth per cell is reconstructed from the ported verdicts:
    * every detection the human marked TP   → a real symbol at its logged box
    * every fn_noteheads entry              → a real notehead the model missed
                                              (point only; box synthesized from
                                               the median TP-notehead size)
  FP and un-verdicted ("pending") detections are NOT ground truth.

  Each model is then run fresh on the cell PNG (imgsz/conf configurable) and its
  detections are matched to GT by category + IoU>=0.5 (boxed GT) or center
  proximity (point GT). We report, per model:
    * recall on confirmed-real symbols  ← the forgetting signal (a drop = damage)
    * precision / F1                    ← deflated equally for both models by
                                          un-verdicted real symbols; the DELTA is
                                          the fair comparison
    * category distribution of raw detections (over/under-detection)

The absolute F1 here is not comparable to historical numbers (different scoring);
what matters is production-vs-fine-tuned parity.

CLI:
    python3 -m tools.omr.training.wtc_forgetting_eval \
        --prod omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
        --ft   omr-weights/deepscoresv2-yolov8l-clef-ft-2026-07-13.pt \
        --cells-dir benchmarks/omr-phase2.5/cells \
        --detections-dir benchmarks/omr-phase3.4/detections-yolo-realft \
        --verdicts-dir benchmarks/omr-phase3.4/verdicts-yolo-realft-ported \
        --imgsz 1280 --conf 0.25 --prefix wtc
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import Counter
from pathlib import Path
from statistics import median


# ── coarse category from a SMuFL/DSv2 class name ─────────────────────────────
def category_of(name: str | None) -> str | None:
    if not name:
        return None
    n = name.lower()
    for pref, cat in (
        ("notehead", "notehead"), ("rest", "rest"), ("accidental", "accidental"),
        ("flag", "flag"), ("dynamic", "dynamic"), ("clef", "clef"),
        ("articulation", "articulation"), ("artic", "articulation"),
        ("time", "time"), ("key", "key"), ("beam", "beam"), ("slur", "slur"),
        ("tie", "tie"), ("tuplet", "tuplet"), ("fermata", "fermata"),
        ("ornament", "ornament"), ("tremolo", "tremolo"), ("augmentation", "aug"),
    ):
        if n.startswith(pref):
            return cat
    return "other"


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ax1, ay1 = ax0 + aw, ay0 + ah
    bx1, by1 = bx0 + bw, by0 + bh
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


# ── ground-truth reconstruction ──────────────────────────────────────────────
def build_gt(cell_id: str, detections_dir: str, verdicts_dir: str) -> list[dict]:
    """Return list of GT symbols: {cat, box=(x,y,w,h), point:bool}."""
    det_path = os.path.join(detections_dir, cell_id + ".json")
    vpath = os.path.join(verdicts_dir, cell_id + ".verdict.json")
    if not (os.path.exists(det_path) and os.path.exists(vpath)):
        return []
    dets = {d["id"]: d for d in json.load(open(det_path))["detections"]}
    v = json.load(open(vpath))

    gt: list[dict] = []
    nh_sizes: list[tuple[float, float]] = []
    for ver in v.get("verdicts", []):
        if ver.get("verdict") == "TP":
            d = dets.get(ver["detection_id"])
            if not d:
                continue
            box = (float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]))
            cat = category_of(d.get("smufl_name")) or d.get("category")
            gt.append({"cat": cat, "box": box, "point": False})
            if cat == "notehead":
                nh_sizes.append((box[2], box[3]))

    # median notehead box for synthesizing FN boxes
    if nh_sizes:
        mw = median(s[0] for s in nh_sizes)
        mh = median(s[1] for s in nh_sizes)
    else:
        mw, mh = 80.0, 68.0
    for fn in v.get("fn_noteheads", []):
        cx = float(fn.get("x_canonical", fn.get("x_center", 0)))
        cy = float(fn.get("y_canonical", fn.get("y_center", 0)))
        gt.append({"cat": category_of(fn.get("tm_smufl_name")) or "notehead",
                   "box": (cx - mw / 2, cy - mh / 2, mw, mh), "point": True,
                   "half": (mw, mh)})
    return gt


# ── per-model scoring against GT ─────────────────────────────────────────────
def _center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return box[0] + box[2] / 2, box[1] + box[3] / 2


def score_model(model, cell_png: str, gt: list[dict], imgsz: int, conf: float,
                device: str, iou_thr: float, match: str = "center") -> dict:
    """match='center' scores by center-distance (fair to box-size drift — the
    honest 'did it detect the symbol' test); match='iou' is stricter localization.
    """
    names = {int(i): n for i, n in model.names.items()}
    r = model.predict(cell_png, imgsz=imgsz, conf=conf, device=device,
                       verbose=False)[0]
    preds = []
    for b in r.boxes:
        x0, y0, x1, y1 = (float(v) for v in b.xyxy[0])
        preds.append({"cat": category_of(names[int(b.cls)]),
                      "box": (x0, y0, x1 - x0, y1 - y0),
                      "conf": float(b.conf), "matched": False})
    preds.sort(key=lambda p: -p["conf"])

    gt_matched = [False] * len(gt)
    tp = 0
    for p in preds:
        best_j, best_score = -1, 0.0
        for j, g in enumerate(gt):
            if gt_matched[j] or g["cat"] != p["cat"]:
                continue
            if match == "center" or g["point"]:
                # match by center proximity, tolerance scaled to GT symbol size
                gcx, gcy = _center(g["box"])
                pcx, pcy = _center(p["box"])
                dist = ((gcx - pcx) ** 2 + (gcy - pcy) ** 2) ** 0.5
                thr = 0.6 * max(g["box"][2], g["box"][3], 40.0)
                score = 1.0 - dist / thr if dist <= thr else 0.0
            else:
                score = iou(g["box"], p["box"])
                score = score if score >= iou_thr else 0.0
            if score > best_score:
                best_score, best_j = score, j
        if best_j >= 0:
            gt_matched[best_j] = True
            p["matched"] = True
            tp += 1

    fp = sum(1 for p in preds if not p["matched"])
    fn = sum(1 for m in gt_matched if not m)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    # recall broken out by GT category
    rec_by_cat: dict[str, list[int]] = {}
    for g, m in zip(gt, gt_matched):
        s = rec_by_cat.setdefault(g["cat"], [0, 0])
        s[1] += 1
        if m:
            s[0] += 1
    return {"tp": tp, "fp": fp, "fn": fn, "prec": prec, "rec": rec, "f1": f1,
            "n_pred": len(preds), "pred_cats": Counter(p["cat"] for p in preds),
            "rec_by_cat": rec_by_cat}


def evaluate(weights: str, cells: list[str], cells_dir: str, detections_dir: str,
             verdicts_dir: str, imgsz: int, conf: float, device: str,
             iou_thr: float, match: str = "center") -> dict:
    from ultralytics import YOLO
    import warnings
    warnings.filterwarnings("ignore")
    model = YOLO(weights)
    agg = {"tp": 0, "fp": 0, "fn": 0}
    pred_cats: Counter = Counter()
    rec_by_cat: dict[str, list[int]] = {}
    per_cell = []
    for cid in cells:
        png = os.path.join(cells_dir, cid + ".png")
        gt = build_gt(cid, detections_dir, verdicts_dir)
        if not gt:
            continue
        s = score_model(model, png, gt, imgsz, conf, device, iou_thr, match)
        for k in ("tp", "fp", "fn"):
            agg[k] += s[k]
        pred_cats.update(s["pred_cats"])
        for cat, (ok, tot) in s["rec_by_cat"].items():
            r = rec_by_cat.setdefault(cat, [0, 0])
            r[0] += ok
            r[1] += tot
        per_cell.append({"cell": cid, **{k: s[k] for k in ("tp", "fp", "fn", "rec", "prec")}})
    tp, fp, fn = agg["tp"], agg["fp"], agg["fn"]
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"weights": Path(weights).name, "n_cells": len(per_cell),
            "tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec,
            "f1": f1, "pred_cats": dict(pred_cats), "rec_by_cat": rec_by_cat,
            "per_cell": per_cell}


def render(prod: dict, ft: dict) -> str:
    L = ["=" * 72, "  WTC non-clef forgetting audit — production vs fine-tuned", "=" * 72,
         f"cells scored: {prod['n_cells']}   (human-confirmed GT: TP boxes + FN noteheads)", ""]
    hdr = f"{'':<14}{'TP':>5}{'FP':>5}{'FN':>5}{'prec':>8}{'recall':>8}{'F1':>8}"
    L.append(hdr)
    for tag, r in (("production", prod), ("fine-tuned", ft)):
        L.append(f"{tag:<14}{r['tp']:>5}{r['fp']:>5}{r['fn']:>5}"
                 f"{r['precision']:>8.3f}{r['recall']:>8.3f}{r['f1']:>8.3f}")
    L.append("")
    L.append(f"recall DELTA (ft - prod): {ft['recall'] - prod['recall']:+.3f}"
             "   ← the forgetting signal (near 0 = no forgetting)")
    L.append("")
    cats = sorted(set(prod["rec_by_cat"]) | set(ft["rec_by_cat"]))
    L.append("recall on confirmed-real symbols, by category (matched/total):")
    L.append(f"    {'category':<12}{'production':>16}{'fine-tuned':>16}")
    for c in cats:
        p = prod["rec_by_cat"].get(c, [0, 0])
        f = ft["rec_by_cat"].get(c, [0, 0])
        pstr = f"{p[0]}/{p[1]}"
        fstr = f"{f[0]}/{f[1]}"
        L.append(f"    {c:<12}{pstr:>16}{fstr:>16}")
    L.append("")
    L.append("raw detection category distribution (over/under-detection):")
    allc = sorted(set(prod["pred_cats"]) | set(ft["pred_cats"]))
    L.append(f"    {'category':<12}{'production':>16}{'fine-tuned':>16}")
    for c in allc:
        L.append(f"    {c:<12}{prod['pred_cats'].get(c, 0):>16}{ft['pred_cats'].get(c, 0):>16}")
    L.append("=" * 72)
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prod", required=True, help="production weights .pt")
    ap.add_argument("--ft", required=True, help="fine-tuned weights .pt")
    ap.add_argument("--cells-dir", required=True)
    ap.add_argument("--detections-dir", required=True)
    ap.add_argument("--verdicts-dir", required=True)
    ap.add_argument("--prefix", default="", help="only score cells whose id starts with this")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--match", choices=["center", "iou"], default="center",
                    help="center: fair to box-size drift (headline); iou: strict localization")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    verdicts = glob.glob(os.path.join(args.verdicts_dir, "*.verdict.json"))
    cells = sorted(Path(v).name.replace(".verdict.json", "") for v in verdicts)
    if args.prefix:
        cells = [c for c in cells if c.startswith(args.prefix)]
    # only cells that actually have a PNG
    cells = [c for c in cells if os.path.exists(os.path.join(args.cells_dir, c + ".png"))]

    prod = evaluate(args.prod, cells, args.cells_dir, args.detections_dir,
                    args.verdicts_dir, args.imgsz, args.conf, args.device, args.iou, args.match)
    ft = evaluate(args.ft, cells, args.cells_dir, args.detections_dir,
                  args.verdicts_dir, args.imgsz, args.conf, args.device, args.iou, args.match)
    print(f"[match mode: {args.match}]")
    print(render(prod, ft))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"production": prod, "fine_tuned": ft}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
