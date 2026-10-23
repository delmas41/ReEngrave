"""2.197 C6 (GATHER-side, whole movement, NO truth): where the accidental-family and key-family boxes of the saved 20261020-night record sit.
Streams the record's observations once (judged.iter_array); per plate: class x cell-index table, key-class boxes beyond the header, staff marker
runs by detector_role. usage: c6_whole.py PLATE OUT.json  (PLATE brahms|litolff)"""
import json, sys, os, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.judged import iter_array
from tools.omr.staged.lane_report import record_path, record_lock
plate, out = sys.argv[1], sys.argv[2]
rp = record_path(plate, "20261020-night")
cellbox, space = {}, {}
boxes = []      # (page,system,staff,cell,cls,conf,x0,x1,reader)
markers = collections.defaultdict(list)
n = 0
with record_lock():
    for o in iter_array(rp, "observations"):
        q = o.get("quantity")
        if q == "cell_box":
            s = o["subject"].split("/"); cellbox[tuple(int(x) for x in s[1:])] = o["value"]
        elif q == "cell_staff_space":
            s = o["subject"].split("/")
            try: space[tuple(int(x) for x in s[1:])] = float(o["value"])
            except Exception: pass
        elif q == "glyph_box" and o.get("reader") == "detector":
            c = o["value"][0]; cl = c.lower()
            if cl.startswith("accidental") or (cl.startswith("key") and not cl.startswith("keyboard")):
                s = o["subject"].split("/")
                b = (o.get("detail") or {}).get("bbox_page_px")
                boxes.append((int(s[1]), int(s[2]), int(s[3]), int(s[4]), c, o.get("score"), b[0], b[2], b[1], b[3]))
        elif q == "keysig_marker":
            d = o.get("detail") or {}
            markers[o["subject"]].append((o["value"], d.get("detector_class"), d.get("detector_role"), d.get("x"), d.get("cell_staff_space")))
        n += 1
json.dump(dict(plate=plate, boxes=boxes, markers={k: v for k, v in markers.items()}, cellbox={"/".join(map(str, k)): v for k, v in cellbox.items()},
               space={"/".join(map(str, k)): v for k, v in space.items()}), open(out, "w"))
print(plate, "obs", n, "acc/key boxes", len(boxes), "marker staves", len(markers))
