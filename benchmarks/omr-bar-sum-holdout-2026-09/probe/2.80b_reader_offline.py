"""2.80b: run `gather_narrow_box_shape` OFFLINE on a saved record's detections.

    python3 .../2.80b_reader_offline.py REC.json PDF PAGE[,PAGE...]

No detector, no Surya: the page is re-cut (`prepare_pages`, the same code the
gather uses), the detections are rebuilt from the record's own `glyph_box`
rows (canonical boxes), and the reader runs into a fresh Log. For iterating
the reader without a 12-minute re-gather. Prints, per narrow box, the shape
the reader filed, and the decision a fresh `Q.NARROW_BOX_SHAPE` row would get
from the shape windows.
"""
import collections
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")
from tools.omr.staged import gather as G, pipeline  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, pdf = sys.argv[1], sys.argv[2]
pages = [int(p) for p in sys.argv[3].split(",")]
rec = load_record(rec_path)
rec = rec["record"] if "record" in rec else rec

boxes = collections.defaultdict(dict)
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and o["reader"] == "detector":
        p = o["subject"].split("/")
        gi = int(p[5])
        if gi >= 90000:
            continue
        name, x, y, w, h = o["value"]
        boxes["cell/" + "/".join(p[1:5])][gi] = SimpleNamespace(
            smufl_name=name, x_canonical=x, y_canonical=y,
            width_canonical=w, height_canonical=h)

log = R.Log()
n = 0
for pws, cells in pipeline.prepare_pages(pdf, pages):
    local = G._system_local(pws.staves)
    dets = {}
    for key, d in boxes.items():
        if int(key.split("/")[1]) == cells[0].page_index:
            dets[key] = [d[i] for i in sorted(d)]
            assert sorted(d) == list(range(len(d))), key
    G.gather_narrow_box_shape(log, cells, local, dets)
rows = [r for r in log.rows_of(Q.NARROW_BOX_SHAPE)] if hasattr(log, "rows_of") else \
    [r for r in log.all_rows() if getattr(r, "quantity", None) == Q.NARROW_BOX_SHAPE]
print("narrow boxes with a shape row:", len(rows))
for r in sorted(rows, key=lambda r: r.subject.to_key()):
    d = r.detail or {}
    if not d.get("n_pieces"):
        continue
    w, h, st = d["width_spaces"], d["height_spaces"], d["staff_step"]
    shaped = (0.9 <= w <= 1.6 and 1.6 <= h <= 2.6 and d["n_pieces"] <= 3
              and abs(st - 4.0) <= 1.0 and not d["touches_cell_edge"])
    others = [o["class"] for o in d["overlapping_detections"]]
    if shaped or "rest8th" in others:
        print("  ", r.subject.to_key(), "w %.2f h %.2f step %.2f pieces %d edge %s others %s -> %s" % (
            w, h, st, d["n_pieces"], d["touches_cell_edge"], others,
            "REST-SHAPED" if shaped else ""))
