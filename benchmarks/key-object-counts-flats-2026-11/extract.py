"""2.302 -- pull, from a saved lane-report slice, what `gather_key_object` read for each staff of cell 0:
the detector's clef box + key/accidental boxes (page px), the meter claim's left edge, and the saved `key_object` row.
    PYTHONPATH=. python3 benchmarks/key-object-counts-flats-2026-11/extract.py PLATE TAG OUT.json PAGE [PAGE...]
The replay (replay.py) feeds these to the production `gather_key_object` on a rebuilt page (cell map), no detector."""
import collections
import json
import sys

from tools.omr.staged import lane_report as LR

plate, tag, out = sys.argv[1], sys.argv[2], sys.argv[3]
pages = set(int(p) for p in sys.argv[4:])
d = LR.slice_dir(plate, tag)
res = collections.defaultdict(lambda: {"dets": [], "meter_left": None, "saved": []})
with open(d / "observations.jsonl") as fh:
    for line in fh:
        if '"glyph_box"' not in line and '"claimed_area"' not in line:
            continue
        it = json.loads(line)
        sub = it["subject"]
        pg = LR.page_of(sub)
        if pg not in pages:
            continue
        parts = sub.split("/")
        if it["quantity"] == "glyph_box" and parts[0] == "glyph" and parts[4] == "0":
            nm = str(it["value"][0])
            bb = it["detail"].get("bbox_page_px")
            if bb:
                key = "%s/%s/%s" % (parts[1], parts[2], parts[3])
                res[key]["dets"].append({"gid": sub, "name": nm, "box": bb})
        elif it["quantity"] == "claimed_area" and parts[0] == "staff":
            dt = it.get("detail") or {}
            key = "%s/%s/%s" % (parts[1], parts[2], parts[3])
            if dt.get("cell") != 0:
                continue
            if dt.get("owner") == "meter":
                res[key]["meter_left"] = float(it["value"][0])
            if dt.get("source") == "system_key_object":
                res[key]["saved"].append({"area": it["value"], "part": dt.get("part"), "standing": dt.get("standing"),
                                          "ko": dt.get("key_object"), "space": dt.get("space_page_px")})
json.dump(res, open(out, "w"))
print(len(res), "staves")
