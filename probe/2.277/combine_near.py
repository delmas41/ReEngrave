import json, os, pathlib, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import lane_report as LR
items = []
for d in ("out/2.277/near-barline-litolff", "out/2.277/near-barline-brahms"):
    for k in json.load(open(d + "/key.json")):
        k = {a: b for a, b in k.items() if a not in ("tile", "crop_origin", "position", "cell_map")}
        items.append(k)
print(len(items), LR.cut_tiles(items, pathlib.Path("out/print/2.277-near-barline"),
      readme_extra="\n**Question for 2.277 (the 0.3-0.5 barline-share heads we keep today):** is the boxed mark a note? (yes / no)\n"))
for n, it in enumerate(items, 1):
    print(n, it["subject"], it["share"], it["reaches_file"])
