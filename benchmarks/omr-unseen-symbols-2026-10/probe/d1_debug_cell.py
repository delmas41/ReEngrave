"""ROADMAP 2.179 -- debug `stem_end_heads` on named cells: stems, orphans, sub-floor head/rest boxes and where they stand.
usage: python3 .../d1_debug_cell.py PDF PAGE CELLKEY [CELLKEY ...]   (CELLKEY = page/system/staff/measure as in the record)"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged import pipeline as P  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import stem_end_heads as SEH  # noqa: E402
from tools.omr.line_detection import detect_lines, staged_stem_finder  # noqa: E402
from tools.omr.yolo_detector import YoloDetector  # noqa: E402

pdf, page = sys.argv[1], int(sys.argv[2])
want = set(sys.argv[3:])
[(pws, cells)] = P.prepare_pages(pdf, [page])
from tools.omr.staged.record import Log  # noqa: E402
log = Log()
local = G.gather_geometry(log, pws)
det = YoloDetector("omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
for c in cells:
    key = local.get(c.staff_index)
    if key is None:
        continue
    ck = "%d/%d/%d/%d" % (page, key[0], key[1], c.measure_index)
    if ck not in want:
        continue
    grid = G._cell_grid(c)
    sp = 2 * grid[1]
    prod = det.detect(c, conf_threshold=0.25)
    stems = (detect_lines(c, candidates_out=None, noteheads=None, stem_finder=staged_stem_finder()) or {}).get("stems") or []
    heads = [SEH._box(d) for d in prod if SEH.is_head(d.smufl_name)]
    print("==", ck, "space", sp, "stems", len(stems))
    for s in stems:
        print("  stem x %.0f y %.0f-%.0f orphan %s" % (*SEH.stem_ends(s), SEH.is_orphan(s, heads, sp)))
    for d in prod:
        if SEH.is_head(d.smufl_name) or d.smufl_name.startswith("rest"):
            print("  prod %s %.2f c=(%.0f,%.0f)" % (d.smufl_name, d.confidence, *SEH._centre(SEH._box(d))))
    for d in det.detect(c, conf_threshold=0.05):
        if (SEH.is_head(d.smufl_name) or d.smufl_name.startswith("rest")) and d.confidence < 0.25:
            print("  sub  %s %.2f c=(%.0f,%.0f)" % (d.smufl_name, d.confidence, *SEH._centre(SEH._box(d))))
    k, r, n = SEH.candidates_for_cell(stems, prod, det.detect(c, conf_threshold=SEH.FLOOR), grid)
    print("  kept", [(x["read_from"], round(x["score"], 2), x["end"]) for x in k], "refused", len(r), "orphans", n)
