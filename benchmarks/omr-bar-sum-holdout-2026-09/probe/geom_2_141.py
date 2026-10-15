"""ROADMAP 2.141 helper: cell_box, staff_lines and glyph page boxes for a list of cells, read once from a
record via record_io.load_record (never raw).  python3 geom_2_141.py RECORD CELLS.json OUT.json"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, cells_path, out_path = sys.argv[1:4]
cells = {tuple(j["cell"]) for j in json.load(open(cells_path))}
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
geo = {"box": {}, "lines": {}, "glyph": {}}
for o in rec["observations"]:
    p = o["subject"].split("/")
    if len(p) < 4:
        continue
    if o["quantity"] == "cell_box" and p[0] == "cell" and len(p) > 4:
        k = tuple(int(x) for x in p[1:5])
        if k in cells:
            geo["box"][",".join(map(str, k))] = o["value"]
    elif o["quantity"] == "staff_lines" and p[0] == "staff":
        geo["lines"][",".join(p[1:4])] = o["value"]
    elif o["quantity"] == "glyph_box" and p[0] == "glyph" and len(p) > 5 \
            and tuple(int(x) for x in p[1:5]) in cells:
        bp = (o.get("detail") or {}).get("bbox_page_px")
        if bp:
            geo["glyph"][o["subject"]] = [bp, o["value"][0] if isinstance(o["value"], list) else o["value"]]
need = {",".join(map(str, c[:3])) for c in cells}
geo["lines"] = {k: v for k, v in geo["lines"].items() if k in need}
json.dump(geo, open(out_path, "w"))
print("cells", len(geo["box"]), "staves", len(geo["lines"]), "glyphs", len(geo["glyph"]))
