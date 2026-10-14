"""ROADMAP 2.110 Step B, arm MATCHED-PACKED: the same cells at staff space 16 (same resize, same >640 tiling and >=50% box rule as
build_arms.py) but SHELF-PACKED several to a 640x640 white canvas instead of one cell centred on a mostly-white canvas.
Why: the first MATCHED arm (one cell per canvas, ~80% white) changes the image statistics as well as the scale (white pad -> BatchNorm
stats; mosaic of white canvases), so it cannot say what scale alone does. Packing keeps ~70% of the canvas ink-bearing like the OLD cells.
Same cell presentations (each cell of the train list once, 2x-dense duplicates packed separately), seed 0. train_2110.sh ARM=packed uses
batch 2 + nbs 14 so the iteration count (75 = 600/8, the OLD arm's) and the optimizer-step count (~10) match the OLD arm.
usage: build_packed.py -> runs/2.110/packed/{images,labels,train.txt,val.txt,catalog.yaml,manifest.json}
"""
import json, random, re, sys
from pathlib import Path
import cv2, numpy as np, yaml
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from build_arms import S, TARGET, label_path

def pieces_of(p, sp):
    im = cv2.imread(p); h, w = im.shape[:2]; f = TARGET / sp
    nh, nw = max(1, round(h * f)), max(1, round(w * f))
    small = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA)
    lab = [l.split() for l in open(label_path(p)).read().splitlines() if l.strip()]
    bx = [(int(c), (float(cx) - float(bw) / 2) * nw, (float(cy) - float(bh) / 2) * nh, (float(cx) + float(bw) / 2) * nw, (float(cy) + float(bh) / 2) * nh) for c, cx, cy, bw, bh in lab]
    step = S * 3 // 4
    x0s = [0] if nw <= S else list(range(0, nw - S + 1, step)) + ([nw - S] if (nw - S) % step else [])
    out = []
    for x0 in x0s:
        tw = min(S, nw - x0); crop = small[:S, x0:x0 + tw]; hh = crop.shape[0]
        keep = []
        for c, a, b, a2, b2 in bx:
            ca, cb, cy0, cy1 = max(a, x0), min(a2, x0 + tw), max(b, 0), min(b2, hh)
            if cb <= ca or cy1 <= cy0 or (cb - ca) * (cy1 - cy0) < 0.5 * (a2 - a) * (b2 - b):
                continue
            keep.append((c, ca - x0, cy0, cb - x0, cy1))
        out.append((crop, keep, Path(p).stem))
    return out

def main():
    man = json.load(open("runs/2.110/matched/manifest.json"))
    old_train = [l.strip() for l in open("runs/2.110/old/train.txt") if l.strip()]
    pieces = [pc for p in old_train for pc in pieces_of(p, man["cells"][p]["space"])]
    random.Random(0).shuffle(pieces)
    out = Path("runs/2.110/packed"); (out / "images").mkdir(parents=True, exist_ok=True); (out / "labels").mkdir(exist_ok=True)
    canvases, cur = [], None  # cur = dict(img, lines, x, y, rowh)
    def new():
        return {"img": np.full((S, S, 3), 255, np.uint8), "lines": [], "x": 0, "y": 0, "rowh": 0, "n": 0}
    cur = new()
    for crop, keep, nm in pieces:
        h, w = crop.shape[:2]
        if cur["x"] + w > S:
            cur["y"] += cur["rowh"]; cur["x"] = 0; cur["rowh"] = 0
        if cur["y"] + h > S:
            canvases.append(cur); cur = new()
        x, y = cur["x"], cur["y"]
        cur["img"][y:y + h, x:x + w] = crop
        for c, a, b, a2, b2 in keep:
            X0, X1, Y0, Y1 = a + x, a2 + x, b + y, b2 + y
            cur["lines"].append(f"{c} {(X0 + X1) / 2 / S:.6f} {(Y0 + Y1) / 2 / S:.6f} {(X1 - X0) / S:.6f} {(Y1 - Y0) / S:.6f}")
        cur["x"] += w; cur["rowh"] = max(cur["rowh"], h); cur["n"] += 1
    canvases.append(cur)
    names = []
    for i, cv in enumerate(canvases):
        nm = f"pack{i:04d}"
        cv2.imwrite(str(out / "images" / f"{nm}.png"), cv["img"]); (out / "labels" / f"{nm}.txt").write_text("\n".join(cv["lines"]) + "\n")
        names.append(str((out / "images" / f"{nm}.png").resolve()))
    (out / "train.txt").write_text("\n".join(names) + "\n")
    (out / "val.txt").write_text(Path("runs/2.110/matched/val.txt").read_text())
    y = yaml.safe_load(open("runs/2.110/matched/catalog.yaml")); y["path"] = str(out.resolve()); y["train"] = str((out / "train.txt").resolve()); y["val"] = str((out / "val.txt").resolve())
    yaml.safe_dump(y, open(out / "catalog.yaml", "w"), sort_keys=False)
    fill = [float((c["img"] < 250).any(axis=2).mean()) for c in canvases]
    info = {"pieces": len(pieces), "canvases": len(canvases), "cells_per_canvas_mean": round(len(pieces) / len(canvases), 2), "canvas_ink_bbox_fraction_not_white_mean": round(float(np.mean(fill)), 3)}
    (out / "manifest.json").write_text(json.dumps(info)); print(info)

if __name__ == "__main__":
    main()
