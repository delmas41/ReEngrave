"""2.251 step 3 (lane-2.251-dots): the F dot finder on EVERY staff, flag OMR_CLEF_DOT_FUSED off vs on. For each staff after the header
window: every dot pair `f_dot_pairs` finds, scored by `f_body_match` (the same body witness `f_nobox` uses); rows with score >= FLOOR.
Boxed F claims (step 1, `scan_page`) are listed per page too, so a boxed read that moves shows. Measures only.

OMR_CLEF_DOT_FUSED=0|1 python3 work-2.251/dots_scan.py PLATE PAGES BOXES.jsonl OUT.json [WORKERS]
"""
import json, os, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
os.environ["OMR_CLEF_CARRY"] = "0"
os.environ.setdefault("CLEF_INK_CACHE", "/private/tmp/claude-501/s/ink")
import scan_claims as SC  # noqa: E402
from tools.omr.staged import claims as CL  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

FLOOR = 0.40
plate, pages, bpath, out = sys.argv[1:5]
workers = int(sys.argv[5]) if len(sys.argv) > 5 else 3
want = []
for part in pages.split(","):
    a, _, b = part.partition("-")
    want.extend(range(int(a), int(b or a) + 1))


def do(pg):
    boxes = SC.load_boxes(bpath)
    ink = SC.page_ink(plate, pg)
    st = list(SC.staves_of(plate, pg))
    per = []
    for s, li, t, cells in st:
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        per.append((lines, sp, [b[1] for b in boxes.get((pg, s, li), []) if b[0] == "clefF" and CL.is_clef_box(b[0], b[1], sp)]))
    tps = CP.f_templates(ink, per)
    claims = SC.scan_page(plate, pg, boxes, ink=ink)
    rows = {"page": pg, "templates": len(tps), "pairs": [], "claims": claims}
    if not tps:
        return rows
    for s, li, t, cells in st:
        if not cells:
            continue
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        order = sorted(cells)
        xh = cells[order[0]][0] + CP.HEADER_WINDOW_SPACES * sp
        xe = cells[order[-1]][2]

        def cell_at(x):
            return max([k for k in order if cells[k][0] <= x] or [order[0]])

        def near(x):
            return ["%s/%s%s" % (c["family"], c["kind"], "" if c["change"] else "(hdr)") for c in claims
                    if (c["system"], c["staff"]) == (s, li) and c["area"][0] - sp <= x <= c["area"][2] + sp]
        for p in CP.f_dot_pairs(ink, lines, sp, xh, xe):
            m = CP.f_body_match(ink, sp, p, tps)
            sc = m.get("score", 0)
            rows["pairs"].append({"score": sc, "page": pg, "system": s, "staff": li, "cell": cell_at(p["x_left"]), "x": round(p["x_left"]),
                                  "near": near(p["x_left"]), "sp": sp, "dy": round((p["dots"][1][1] - p["dots"][0][1]) / sp, 2), "radius": p.get("radius")})
    print("page", pg, "pairs", len(rows["pairs"]), file=sys.stderr, flush=True)
    return rows


if __name__ == "__main__":
    with Pool(workers) as p:
        res = p.map(do, want, chunksize=1)
    json.dump(res, open(out, "w"))
