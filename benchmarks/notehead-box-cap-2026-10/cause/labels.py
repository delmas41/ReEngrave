"""2.222 cause: how big are the notehead boxes in the TRAINING LABELS (data/user-labeled, Sean's corpus)?

Staff space per image is MEASURED on the image (horizontal ink projection: the five staff-line rows nearest the
image's vertical middle, spacing = median gap), not assumed from the canonical 400 px span. Sizes in staff spaces.
    python3 benchmarks/notehead-box-cap-2026-10/cause/labels.py
"""
import collections, glob, os, pathlib
import cv2, numpy as np, yaml

ROOT = pathlib.Path(os.environ.get("LABELS_ROOT", "/Users/seanjohnson/Desktop/ReEngrave/data/user-labeled"))
names = yaml.safe_load(pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/data/user-labeled/catalog.yaml").read_text())["names"]
HEAD = {i for i, n in enumerate(names) if n.startswith("noteheadBlack")}
HALF = {i for i, n in enumerate(names) if n.startswith("noteheadHalf")}


def spacing(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    ink = (g < 128).mean(axis=1)
    rows = np.where(ink > 0.5)[0]
    if len(rows) < 5:
        return None
    runs, cur = [], [rows[0]]
    for r in rows[1:]:
        if r - cur[-1] <= 2:
            cur.append(r)
        else:
            runs.append(np.mean(cur)); cur = [r]
    runs.append(np.mean(cur))
    if len(runs) < 5:
        return None
    mid = img.shape[0] / 2
    runs = sorted(runs, key=lambda y: abs(y - mid))[:5]
    runs.sort()
    gaps = np.diff(runs)
    if gaps.max() > 1.3 * gaps.min():
        return None
    return float(np.median(gaps))


out = collections.defaultdict(lambda: collections.defaultdict(list))
nosp = collections.Counter()
for v in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("v")):
    for lab in sorted((v / "labels").glob("*.txt")):
        rows = [l.split() for l in lab.read_text().splitlines() if l.strip()]
        rows = [r for r in rows if int(r[0]) in HEAD or int(r[0]) in HALF]
        if not rows:
            continue
        im = None
        for ext in (".png", ".jpg"):
            p = v / "images" / (lab.stem + ext)
            if p.exists():
                im = cv2.imread(str(p)); break
        if im is None:
            continue
        s = spacing(im)
        if not s:
            nosp[v.name] += 1; continue
        H, W = im.shape[:2]
        for r in rows:
            c = int(r[0]); w = float(r[3]) * W / s; h = float(r[4]) * H / s
            out[v.name]["black" if c in HEAD else "half"].append((w, h))

print("version  kind  n  w p50/p95/p99  h p50/p95/p99  share w>1.9  share h>1.8")
allb = []
for vn, kinds in out.items():
    for k, L in kinds.items():
        a = np.array(L)
        if k == "black":
            allb.append(a)
        print(vn, k, len(a), np.percentile(a[:, 0], [50, 95, 99]).round(2), np.percentile(a[:, 1], [50, 95, 99]).round(2),
              round(float((a[:, 0] > 1.9).mean()), 3), round(float((a[:, 1] > 1.8).mean()), 3))
a = np.concatenate(allb)
print("ALL black", len(a), "w p50/p95/p99", np.percentile(a[:, 0], [50, 95, 99]).round(2), "h", np.percentile(a[:, 1], [50, 95, 99]).round(2),
      "w>1.9", round(float((a[:, 0] > 1.9).mean()), 4), "h>1.8", round(float((a[:, 1] > 1.8).mean()), 4))
print("images with no measurable spacing", dict(nosp))
