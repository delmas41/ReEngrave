"""Build a corrected clef fine-tune dataset that fixes the dense-page notehead
collapse of the first clef fine-tune.

Diagnosis (see benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md):
  * the 62 clef cells' notehead boxes were ~1.6x too loose (0.047 vs 0.029
    normalized width) -> the model learned oversized notehead boxes;
  * several clef cells had noteheads present but NONE labeled -> unlabeled
    noteheads trained as background;
  * 30 epochs on sparse m0 cells biased the neck/head toward sparse scenes ->
    notehead detection collapsed on dense orchestral pages (Mahler 2506 -> 123).

Fix — keep the human CLEF labels (the whole point), but make every non-clef
symbol label correct and complete by self-distilling from the trusted production
model, and add dense "anti-forgetting" cells so the model keeps a dense-scene
signal:

  clef cells (v5+v6):  human clef boxes  +  production non-clef detections
  anti-forgetting:     interior (non-m0) orchestral cells, production non-clef
                       detections only (no clef -> no clef contamination)

Output: an ultralytics dataset dir (images/ labels/ data.yaml train.txt val.txt),
nc=208, ready for train_yolo.py --data <out>/data.yaml.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
from pathlib import Path

CLEF_PREFIX = "clef"


def is_clef(name: str) -> bool:
    return name.lower().startswith(CLEF_PREFIX)


def read_label(path: str) -> list[tuple[int, float, float, float, float]]:
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        p = line.split()
        if len(p) >= 5:
            out.append((int(p[0]), float(p[1]), float(p[2]), float(p[3]), float(p[4])))
    return out


def iou_norm(a, b) -> float:
    # a,b = (cx,cy,w,h) normalized
    ax0, ay0 = a[0] - a[2] / 2, a[1] - a[3] / 2
    ax1, ay1 = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx0, by0 = b[0] - b[2] / 2, b[1] - b[3] / 2
    bx1, by1 = b[0] + b[2] / 2, b[1] + b[3] / 2
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def production_labels(model, img_path: str, conf: float, keep_clef: bool):
    """Return list of (cls, cx, cy, w, h) normalized for NON-clef (and optionally
    clef) detections from the production model."""
    names = {int(i): n for i, n in model.names.items()}
    r = model.predict(img_path, imgsz=1280, conf=conf, device="cpu", verbose=False)[0]
    W, H = r.orig_shape[1], r.orig_shape[0]
    out = []
    for b in r.boxes:
        c = int(b.cls)
        nm = names[c]
        if is_clef(nm) and not keep_clef:
            continue
        x0, y0, x1, y1 = (float(v) for v in b.xyxy[0])
        cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
        w, h = (x1 - x0) / W, (y1 - y0) / H
        out.append((c, cx, cy, w, h))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prod-weights", default="omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")
    ap.add_argument("--clef-globs", nargs="+",
                    default=["data/user-labeled/v5-2026-07-12-clef",
                             "data/user-labeled/v6-2026-07-13-clef-diverse"])
    ap.add_argument("--dense-globs", nargs="+",
                    default=["data/user-labeled/v1-2026-05-18-orchestral",
                             "data/user-labeled/v2-2026-06-08-beet5",
                             "data/user-labeled/v3-2026-06-09-mahler5",
                             "data/user-labeled/v4-2026-06-10-la-mer"])
    ap.add_argument("--out", default="data/user-labeled-clef-fix")
    ap.add_argument("--conf", type=float, default=0.4, help="production pseudo-label conf")
    ap.add_argument("--dense-min-noteheads", type=int, default=8,
                    help="only use interior cells where production finds >= this many noteheads")
    ap.add_argument("--val-frac", type=float, default=0.12)
    args = ap.parse_args(argv)

    from ultralytics import YOLO
    import warnings
    warnings.filterwarnings("ignore")
    model = YOLO(args.prod_weights)
    names = {int(i): n for i, n in model.names.items()}

    out = Path(args.out)
    for sub in ("images", "labels"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    written = []  # (stem, is_clef_cell)
    n_clef_boxes = n_pseudo_boxes = 0

    # ── clef cells: human clefs + production non-clef ────────────────────────
    for root in args.clef_globs:
        for img in sorted(glob.glob(os.path.join(root, "images", "*.png"))):
            stem = Path(img).stem
            human = read_label(img.replace("/images/", "/labels/").replace(".png", ".txt"))
            clef_lbls = [t for t in human if is_clef(names.get(t[0], ""))]
            pseudo = production_labels(model, img, args.conf, keep_clef=False)
            # drop pseudo boxes that overlap a human clef box (avoid double-labeling clef area)
            pseudo = [p for p in pseudo
                      if all(iou_norm(p[1:], c[1:]) < 0.4 for c in clef_lbls)]
            lbls = clef_lbls + pseudo
            n_clef_boxes += len(clef_lbls)
            n_pseudo_boxes += len(pseudo)
            _emit(out, stem, img, lbls)
            written.append((stem, True))

    n_clef_cells = len(written)

    # ── anti-forgetting dense interior cells: production non-clef only ───────
    dense_written = 0
    for root in args.dense_globs:
        for img in sorted(glob.glob(os.path.join(root, "images", "*.png"))):
            stem = Path(img).stem
            if stem.endswith("-m0"):
                continue  # skip m0 (may contain a clef)
            pseudo = production_labels(model, img, args.conf, keep_clef=False)
            n_nh = sum(1 for p in pseudo if names[p[0]].lower().startswith("notehead"))
            if n_nh < args.dense_min_noteheads:
                continue
            n_pseudo_boxes += len(pseudo)
            _emit(out, stem, img, pseudo)
            written.append((stem, False))
            dense_written += 1

    # ── split + data.yaml ────────────────────────────────────────────────────
    # deterministic split: every ~1/val_frac-th item to val
    step = max(2, round(1 / args.val_frac))
    train, val = [], []
    for i, (stem, _) in enumerate(written):
        (val if i % step == 0 else train).append(str((out / "images" / f"{stem}.png").resolve()))
    (out / "train.txt").write_text("\n".join(train) + "\n")
    (out / "val.txt").write_text("\n".join(val) + "\n")

    names_yaml = "\n".join(f"- {names[i]}" for i in range(len(names)))
    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\n"
        f"train: {(out / 'train.txt').resolve()}\n"
        f"val: {(out / 'val.txt').resolve()}\n"
        f"nc: {len(names)}\n"
        f"names:\n{names_yaml}\n")

    print(f"clef cells:            {n_clef_cells}")
    print(f"anti-forgetting cells: {dense_written}")
    print(f"total cells:           {len(written)}  (train {len(train)} / val {len(val)})")
    print(f"human clef boxes:      {n_clef_boxes}")
    print(f"production pseudo boxes:{n_pseudo_boxes}")
    print(f"wrote dataset -> {out}/data.yaml")
    return 0


def _emit(out: Path, stem: str, img_src: str, lbls) -> None:
    shutil.copy(img_src, out / "images" / f"{stem}.png")
    (out / "labels" / f"{stem}.txt").write_text(
        "".join(f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n" for c, cx, cy, w, h in lbls))


if __name__ == "__main__":
    raise SystemExit(main())
