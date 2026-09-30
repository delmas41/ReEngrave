import pickle, sys, json, random
from pathlib import Path
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0af1ab57763853aa")
import numpy as np
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page

PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
OUTDIR = Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0af1ab57763853aa/out/print/dyads")

PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))
abox = {o["subject"]: o for o in d["by_q_page"]["arc_box"]}
kind = {x["subject"]: x["value"] for x in d["verd_by_q_page"]["arc_kind"]}
tp = {x["subject"]: x for x in d["verd_by_q_page"]["tie_pair"]}
ties = [s for s, k in kind.items() if k == "tie"]

boxes = {s: abox[s]["detail"].get("bbox_page_px") for s in ties if abox[s]["detail"].get("bbox_page_px")}

def iou(a, b):
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0

keys = list(boxes.keys())
parent = {k: k for k in keys}
def find(x):
    while parent[x] != x:
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        if iou(boxes[keys[i]], boxes[keys[j]]) > 0.05:
            union(keys[i], keys[j])
clusters = {}
for k in keys:
    clusters.setdefault(find(k), []).append(k)

random.seed(7)
cluster_list = list(clusters.values())
sample = random.sample(cluster_list, 10)

print("rendering ...")
pi = render_page(PDF, 3, dpi=600)
arr = getattr(pi, "rgb", None)
if arr is None:
    arr = getattr(pi, "binary")
arr_np = np.asarray(arr)
base_rgb = arr_np if arr_np.ndim == 3 else np.stack([arr_np]*3, axis=-1)
img_full = Image.fromarray(base_rgb.astype(np.uint8)).convert("RGB")

manifest = []
for i, members in enumerate(sample):
    tag = f"D{i+1:02d}"
    allboxes = [boxes[m] for m in members]
    x0 = min(b[0] for b in allboxes); y0 = min(b[1] for b in allboxes)
    x1 = max(b[2] for b in allboxes); y1 = max(b[3] for b in allboxes)
    pad = 250
    cx0, cy0 = max(0, int(x0-pad)), max(0, int(y0-pad))
    cx1, cy1 = min(img_full.width, int(x1+pad)), min(img_full.height, int(y1+pad))
    crop = img_full.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    draw = ImageDraw.Draw(crop)
    for b in allboxes:
        draw.rectangle([b[0]-cx0, b[1]-cy0, b[2]-cx0, b[3]-cy0], outline=(220, 20, 20), width=2)
    paired_info = [tp.get(m, {}).get("reason") for m in members]
    label = f"{tag} n_members={len(members)} paired_reason={paired_info}"
    draw.rectangle([0, 0, crop.width, 20], fill=(255, 255, 255))
    draw.text((4, 4), label, fill=(0, 0, 0))
    fname = f"{tag}-tie-cluster.png"
    crop.save(OUTDIR / fname)
    manifest.append(dict(tag=tag, file=fname, members=members, paired_info=paired_info))
    print(tag, fname, members, paired_info)

json.dump(manifest, open(OUTDIR / "manifest-d.json", "w"), indent=1, default=str)
