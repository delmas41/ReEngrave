"""Step A.5 -- measure the staff space of every training image (canonical cell) with shown_space.measure_space and
what ultralytics' load-time resize (BaseDataset.load_image, rect_mode: long side -> imgsz, INTER_LINEAR) makes of it.
usage: survey_train_spaces.py <catalog train list .txt> <out.json> [--also v24 dir]
Writes per unique image: path, h, w, space (canonical), long side. Shown spaces are computed in report_shown.py."""
import json, sys, cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shown_space import measure_space

lst, out = sys.argv[1], sys.argv[2]
paths = sorted(set(l.strip() for l in open(lst) if l.strip()))
extra = sys.argv[3:]
for d in extra:
    paths += sorted(str(p) for p in Path(d).glob("images/*.png"))
rows = []
for p in paths:
    im = cv2.imread(p)
    m = measure_space(im)
    rows.append({"path": p, "h": im.shape[0], "w": im.shape[1], "space": None if m is None else m[0],
                 "comb": None if m is None else m[1]})
json.dump(rows, open(out, "w"))
print(len(rows), "images;", sum(r["space"] is None for r in rows), "without a measurable staff")
