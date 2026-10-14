"""ROADMAP 2.110 Step B data: the two arms' datasets from ONE filtered list.

  EXCLUSION (Sean 2026-10-13 "Yes leave them out"): every training/val cell narrower than 500 px (barline slivers, black blocks and
  fragments with no five-line staff in view, see out/print/2.110-staff-space-check) is dropped from BOTH arms. v24 is not in the mix.
  OLD     = the 2.4b CONTROL catalog (runs/2.110/cat-old, 2x dense) minus those cells; images/labels untouched; trained at imgsz 896.
  MATCHED = the same cells, each resized by 16/space (its OWN measured staff space, survey json / shown_space) so its staff space is 16 px,
            pasted centred on a white 640x640 canvas (a cell that is wider than 640 after the resize is cut into overlapping 640-wide tiles; a box
            is kept in a tile only if >= 50% of its area lies inside, and is clipped to it), trained at imgsz 640 so the loader's letterbox
            has r == 1 and rescales nothing.  Labels transformed with the image.
usage: build_arms.py   -> runs/2.110/old/{train.txt,val.txt,catalog.yaml}, runs/2.110/matched/{images,labels,train.txt,val.txt,catalog.yaml,manifest.json}
"""
import json, sys, re
from pathlib import Path
import cv2, numpy as np, yaml
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from shown_space import measure_space

CAT = Path("runs/2.110/cat-old").resolve()
S = 640
MIN_W = 500
TARGET = 16.0


def label_path(img):
    return Path(re.sub(r"/images/([^/]+)\.png$", r"/labels/\1.txt", str(img)))


def main():
    spaces = {r["path"]: r["space"] for r in json.load(open(HERE / "train-spaces-control.json"))}
    cat = yaml.safe_load(open(CAT / "catalog-2xdense.yaml"))
    lists = {"train": [l.strip() for l in open(cat["train"]) if l.strip()], "val": [l.strip() for l in open(cat["val"]) if l.strip()]}
    info = {}
    excluded = {"train": set(), "val": set()}
    for split, lines in lists.items():
        for p in sorted(set(lines)):
            im = cv2.imread(p)
            if im.shape[1] < MIN_W:
                excluded[split].add(p); continue
            sp = spaces.get(p) or (measure_space(im) or (None,))[0]
            if sp is None:
                excluded[split].add(p); continue
            info[p] = (im, sp)
    out_old = Path("runs/2.110/old"); out_old.mkdir(parents=True, exist_ok=True)
    out_m = Path("runs/2.110/matched"); (out_m / "images").mkdir(parents=True, exist_ok=True); (out_m / "labels").mkdir(exist_ok=True)
    manifest = {"min_w": MIN_W, "canvas": S, "target_space": TARGET, "cells": {}, "excluded": {k: sorted(v) for k, v in excluded.items()}}
    boxes_in = boxes_kept = boxes_dropped_tile = 0
    tiles_of = {}
    for p, (im, sp) in info.items():
        f = TARGET / sp
        h, w = im.shape[:2]
        nh, nw = max(1, round(h * f)), max(1, round(w * f))
        small = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA)
        lab = [l.split() for l in open(label_path(p)).read().splitlines() if l.strip()]
        # boxes in resized-pixel coords
        bx = [(int(c), (float(cx) - float(bw) / 2) * nw, (float(cy) - float(bh) / 2) * nh, (float(cx) + float(bw) / 2) * nw, (float(cy) + float(bh) / 2) * nh)
              for c, cx, cy, bw, bh in lab]
        boxes_in += len(bx)
        ver = re.search(r"/(v\d+)-", p).group(1)
        base = f"{ver}_{Path(p).stem}"
        oy = (S - nh) // 2 if nh <= S else 0
        x0s = [0] if nw <= S else list(range(0, nw - S + 1, S * 3 // 4)) + ([nw - S] if (nw - S) % (S * 3 // 4) else [])
        names = []
        for ti, x0 in enumerate(x0s):
            canvas = np.full((S, S, 3), 255, np.uint8)
            tw = min(S, nw - x0)
            ox = (S - nw) // 2 if nw <= S else 0
            crop = small[: min(nh, S), x0:x0 + tw]
            canvas[oy:oy + crop.shape[0], ox:ox + crop.shape[1]] = crop
            lines = []
            for c, a, b, a2, b2 in bx:
                ca, cb = max(a, x0), min(a2, x0 + tw)
                cy0, cy1 = max(b, 0), min(b2, min(nh, S))
                if cb <= ca or cy1 <= cy0:
                    continue
                if (cb - ca) * (cy1 - cy0) < 0.5 * (a2 - a) * (b2 - b):
                    boxes_dropped_tile += 1; continue
                X0, X1, Y0, Y1 = ca - x0 + ox, cb - x0 + ox, cy0 + oy, cy1 + oy
                lines.append(f"{c} {(X0 + X1) / 2 / S:.6f} {(Y0 + Y1) / 2 / S:.6f} {(X1 - X0) / S:.6f} {(Y1 - Y0) / S:.6f}")
                boxes_kept += 1
            nm = base + (f"_t{ti}" if len(x0s) > 1 else "")
            cv2.imwrite(str(out_m / "images" / f"{nm}.png"), canvas)
            (out_m / "labels" / f"{nm}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
            names.append(str(out_m / "images" / f"{nm}.png"))
        tiles_of[p] = names
        manifest["cells"][p] = {"space": sp, "factor": round(f, 4), "resized": [nw, nh], "tiles": len(names)}
    for split, lines in lists.items():
        old = [l for l in lines if l in info]
        (out_old / f"{split}.txt").write_text("\n".join(old) + "\n")
        (out_m / f"{split}.txt").write_text("\n".join(t for l in old for t in tiles_of[l]) + "\n")
    for d, tr in ((out_old, "train"), (out_m, "train")):
        y = dict(cat); y["path"] = str(d.resolve()); y["train"] = str((d / "train.txt").resolve()); y["val"] = str((d / "val.txt").resolve())
        yaml.safe_dump(y, open(d / "catalog.yaml", "w"), sort_keys=False)
    manifest["counts"] = {"train_lines_old": len((out_old / "train.txt").read_text().split()), "val_lines_old": len((out_old / "val.txt").read_text().split()),
                          "train_lines_matched": len((out_m / "train.txt").read_text().split()), "val_lines_matched": len((out_m / "val.txt").read_text().split()),
                          "excluded_train_unique": len(excluded["train"]), "excluded_val_unique": len(excluded["val"]),
                          "boxes_in": boxes_in, "boxes_kept_in_tiles": boxes_kept, "boxes_dropped_by_tiling": boxes_dropped_tile}
    (out_m / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest["counts"], indent=1))


if __name__ == "__main__":
    main()
