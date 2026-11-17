"""Why does the empty-bar whole-rest search miss a whole rest? Re-cut one page's cells and print every ink piece of the named bars,
measured exactly as gather_empty_bar_rest_search measures it.   searchprobe.py PLATE PAGE p/s/st/c ..."""
import json, sys
sys.path.insert(0, ".")
import numpy as np
from tools.omr.staged.pipeline import prepare_pages
from tools.omr.staged import gather as G
from tools.omr.staged.adjudicators import rhythm as RH
from tools.omr.staged.lane_report import LIB, PLATES

S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/"
plate, page = sys.argv[1], int(sys.argv[2])
bars = sys.argv[3:]
tag = "lit-a" if plate == "litolff" else "bra-a"
extra = json.load(open(S + "2311/%s.extra.json" % tag))
want = {b: extra["cell_box"][b] for b in bars}
pp = prepare_pages(str(LIB / PLATES[plate]["pdf"]), [page], dpi=600)
pws, cells = pp[0]
print("cells", len(cells))
for b, box in want.items():
    best = None
    for c in cells:
        cb = getattr(c, "bbox_page_px", None)
        if not cb:
            continue
        d = sum(abs(a - b2) for a, b2 in zip(cb, box))
        if best is None or d < best[0]:
            best = (d, c)
    d, c = best
    lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
    grid = G._cell_grid(c)
    comps = G._ink_components(c)
    print("=== bar", b, "match d=%.1f" % d, "cell_box", c.bbox_page_px, "lines", [round(x, 1) for x in lines], "grid", grid)
    if not grid or not comps:
        print("   no grid/comps")
        continue
    half = grid[1]
    sp = half * 2.0
    bottom = lines[-1]
    W = c.image_no_staff.shape[1]
    for (x, y, w, h, area) in comps:
        hs, ws = h / sp, w / sp
        asp = ws / hs if hs else 0
        step = (bottom - (y + h / 2.0)) / half
        shaped = RH._rest_shaped(hs, asp)
        dev_w, dev_h = abs(step - RH.WHOLE_REST_STEP), abs(step - RH.HALF_REST_STEP)
        print("   comp x=%d y=%d w=%d h=%d  h_sp=%.2f w_sp=%.2f aspect=%.2f step=%.2f  shaped=%s dev_whole=%.2f dev_half=%.2f  xc=%.2f of bar" % (
            x, y, w, h, hs, ws, asp, step, shaped, dev_w, dev_h, (x + w / 2) / W))
