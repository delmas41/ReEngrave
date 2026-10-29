import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import pops
from tools.omr.staged import lane_report as LR
P = pops.load()
W, H = 2.6, 2.8
out = pathlib.Path(sys.argv[1])
items = []
for plate in ("litolff", "brahms"):
    A = sorted(P[plate]["A"].values(), key=lambda g: -max(g["w"] / W, g["h"] / H))
    for g in A[:12 if plate == "litolff" else 8]:
        items.append(dict(role="case", plate=plate, page=g["page"], box=g["box"], key=g["key"], w=round(g["w"], 2), h=round(g["h"], 2)))
LR.cut_tiles(items, out, "tiles")
json.dump(items, open(out / "key.json", "w"), indent=1)
