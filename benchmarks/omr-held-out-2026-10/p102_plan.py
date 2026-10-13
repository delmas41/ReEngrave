"""ROADMAP 2.102: build the blind-tile plan for make_tiles.py.

    python3 benchmarks/omr-held-out-2026-10/p102_plan.py OUT_PLAN.json SPEC.json
SPEC.json = {"docs": {doc: {"pdf":..., "record":...}},
             "tiles": [{"doc","subject","purpose","rule","our_reading"}]}
Fills each tile's page box from the record's own glyph_box row.
"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

spec = json.load(open(sys.argv[2]))
recs = {}
tiles = []
for t in spec["tiles"]:
    d = t["doc"]
    if d not in recs:
        recs[d] = load_record(spec["docs"][d]["record"])["record"]
    box = None
    for o in recs[d]["observations"]:
        if o["subject"] == t["subject"] and o["quantity"] == "glyph_box":
            box = (o.get("detail") or {}).get("bbox_page_px")
    if box is None:
        print("no box for", t["subject"])
        continue
    tiles.append({**t, "kind": "note", "box": box})
json.dump({"docs": spec["docs"], "tiles": tiles}, open(sys.argv[1], "w"), indent=1)
print("planned", len(tiles))
