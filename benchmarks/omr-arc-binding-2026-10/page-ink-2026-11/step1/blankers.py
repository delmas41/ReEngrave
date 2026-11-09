"""2.274 step 1: which detector classes' blanked rectangles lie over detector curves that have no whole run, versus over curves a run covers whole?
python3 blankers.py WORKDIR   (reads the rows of the saved slice, no canvas)"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measure as M  # noqa: E402
from tools.omr.staged import page_arcs as PA  # noqa: E402

wd = pathlib.Path(sys.argv[1])
miss, ok = collections.Counter(), collections.Counter()
n_miss = n_ok = 0
for p in sorted(wd.glob("*.step1.json")):
    stem = p.name.replace(".step1.json", "")
    plate, page = stem.split("-p")
    J = json.load(open(p))
    rows, _c, _r = M.slice_rows(plate, int(page), "20261104-night")
    boxes, areas, arcs = PA.inputs_from_rows(rows)
    for c in J["curves"]:
        if c["refused"]:
            continue
        x0, y0, x1, y1 = c["box"]
        cls = set()
        for k, b in boxes:
            if b[2] > x0 and b[0] < x1 and b[3] > y0 and b[1] < y1:
                cls.add(k)
        if c["best"] >= 0.8:
            n_ok += 1
            ok.update(cls)
        else:
            n_miss += 1
            miss.update(cls)
print("curves with no whole run:", n_miss, dict(miss.most_common(14)))
print("curves covered whole    :", n_ok, dict(ok.most_common(14)))
