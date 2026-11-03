"""2.251 F cut-off measurement (test-2.251-f-cutoff). For every staff of the given pages: (A) every dot pair + body match (f_nobox's own
inputs, all scores >= FLOOR_A) and (B) the body slid along the whole staff with no dot witness (f_body_scan), local maxima >= FLOOR_B.
Each row notes the step-1 claim standing within a space. Measures only.

python3 work-2.251/fcut_scan.py PLATE PAGES BOXES.jsonl OUT.json [WORKERS]
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

FLOOR_A, FLOOR_B = 0.40, 0.40
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
    rows = {"page": pg, "templates": len(tps), "pairs": [], "scan": [], "claims": claims}
    if not tps:
        print("page", pg, "no template", file=sys.stderr, flush=True)
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
            if m.get("score", 0) >= FLOOR_A and "box" in m:
                rows["pairs"].append({"score": m["score"], "page": pg, "system": s, "staff": li, "cell": cell_at(p["x_left"]),
                                      "x": round(p["x_left"]), "near": near(p["x_left"]), "sp": sp})
        for r in CP.f_body_scan(ink, lines, sp, xh, xe, tps):
            if r["match"]["score"] >= FLOOR_B:
                rows["scan"].append({"score": r["match"]["score"], "page": pg, "system": s, "staff": li, "cell": cell_at(r["x"]),
                                     "x": round(r["x"]), "near": near(r["x"]), "box": r["match"]["box"], "sp": sp})
    print("page", pg, "templates", len(tps), "pairs", len(rows["pairs"]), "scan", len(rows["scan"]), file=sys.stderr, flush=True)
    return rows


if __name__ == "__main__":
    with Pool(workers) as p:
        res = p.map(do, want, chunksize=1)
    json.dump(res, open(out, "w"))
