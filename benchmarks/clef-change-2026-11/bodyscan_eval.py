"""2.251 carry round 2: the F body slid along a staff with NO dot witness (`clef_pagewide.f_body_scan`), on the staves where a carry
runs (every staff step 1 claims a change on), right of the first change: every local maximum >= FLOOR, ranked, with what stands there
by step 1's claims (a claimed clef within a space, or nothing).

python3 work-2.251/bodyscan_eval.py PLATE PAGES BOXES.jsonl CLAIMS.json [FLOOR]
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import scan_claims as SC  # noqa: E402
from tools.omr.staged import claims as CL  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

plate, pages, bpath, cpath = sys.argv[1:5]
floor = float(sys.argv[5]) if len(sys.argv) > 5 else 0.4
want = []
for part in pages.split(","):
    a, _, b = part.partition("-")
    want.extend(range(int(a), int(b or a) + 1))
boxes = SC.load_boxes(bpath)
claims = [c for c in json.load(open(cpath)) if not c.get("candidate")]
rows = []
for pg in want:
    chg = [c for c in claims if c["page"] == pg and c["change"]]
    if not chg:
        continue
    ink = SC.page_ink(plate, pg)
    st = list(SC.staves_of(plate, pg))
    per = []
    for s, li, t, cells in st:
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        per.append((lines, sp, [b[1] for b in boxes.get((pg, s, li), []) if b[0] == "clefF" and CL.is_clef_box(b[0], b[1], sp)]))
    tps = CP.f_templates(ink, per)
    for s, li, t, cells in st:
        mine = [c for c in chg if (c["system"], c["staff"]) == (s, li)]
        if not mine or not cells:
            continue
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        order = sorted(cells)
        x0 = min(c["area"][0] for c in mine)
        for r in CP.f_body_scan(ink, lines, sp, x0, cells[order[-1]][2], tps):
            if r["match"]["score"] < floor:
                continue
            x = r["x"]
            near = [c for c in claims if (c["page"], c["system"], c["staff"]) == (pg, s, li) and c["area"][0] - sp <= x <= c["area"][2] + sp]
            cell = max([k for k in order if cells[k][0] <= x] or [order[0]])
            rows.append((r["match"]["score"], pg, s, li, cell, round(x), ",".join("%s/%s" % (c["family"], c["kind"]) for c in near) or "-"))
    print("page", pg, file=sys.stderr)
for r in sorted(rows, reverse=True):
    print(*r)
