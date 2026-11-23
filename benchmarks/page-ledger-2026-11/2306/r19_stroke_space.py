"""2.306 r19 step 5 (read-only): page strokes whose `staff_space_local_px` (stroke_map's line fit at the stroke) is more than 10% off the
spacing of the staff it is read against (the staff's own line spacing from the cell grid, `Q.CELL_STAFF_SPACE` / upscale, median over its
cells). Usage: r19_stroke_space.py REC PAGES"""
import collections
import os
import statistics
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402

rec = load_record(sys.argv[1])
rec = rec.get("record", rec)
pages = {int(x) for x in sys.argv[2].split(",")}
strokes = [o for o in rec["observations"] if o["quantity"] == "page_stroke" and int(o["subject"].split("/")[1]) in pages]
by_page = collections.defaultdict(list)
for o in strokes:
    d = o["detail"]
    if d.get("staff_space_local_px"):
        by_page[int(o["subject"].split("/")[1])].append(o)
for p, os_ in sorted(by_page.items()):
    med = statistics.median(float(o["detail"]["staff_space_local_px"]) for o in os_)
    off = [o for o in os_ if abs(float(o["detail"]["staff_space_local_px"]) / med - 1.0) > 0.10]
    where = collections.Counter(tuple(o["detail"].get("staff") or ()) for o in off)
    kinds = collections.Counter(o["value"] for o in off)
    vals = collections.Counter(round(float(o["detail"]["staff_space_local_px"]), 1) for o in off)
    print("p%d: %d of %d strokes off >10%% of the page's %.2f px; by (system, staff) %s; kinds %s; values %s" % (
        p, len(off), len(os_), med, dict(where.most_common(8)), dict(kinds), dict(vals.most_common(5))))
