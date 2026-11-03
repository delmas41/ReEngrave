"""2.251 carry: the no-box F reader exactly as GATHER runs it (per-page templates from the page's clef-sized `clefF` boxes,
`clef_pagewide.f_nobox` from the header window to the staff's end), every pair scoring >= the candidate score, ranked.
Each line: score, read?, page, system, staff, cell, dots x, claimed-by-step-1 (a boxed F within a space)?

python3 work-2.251/nobox_eval.py PLATE PAGES BOXES.jsonl CLAIMS.json
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import scan_claims as SC  # noqa: E402
from tools.omr.staged import claims as CL  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

plate, pages, bpath, cpath = sys.argv[1:5]
want = []
for part in pages.split(","):
    a, _, b = part.partition("-")
    want.extend(range(int(a), int(b or a) + 1))
boxes = SC.load_boxes(bpath)
claims = json.load(open(cpath))
rows = []
for pg in want:
    ink = SC.page_ink(plate, pg)
    per = []
    st = list(SC.staves_of(plate, pg))
    for s, li, t, cells in st:
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        per.append((lines, sp, [b[1] for b in boxes.get((pg, s, li), []) if b[0] == "clefF" and CL.is_clef_box(b[0], b[1], sp)]))
    tps = CP.f_templates(ink, per)
    for s, li, t, cells in st:
        if not cells:
            continue
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        order = sorted(cells)
        for nb in CP.f_nobox(ink, lines, sp, cells[order[0]][0] + CP.HEADER_WINDOW_SPACES * sp, cells[order[-1]][2], tps):
            x = nb["pair"]["x_left"]
            boxed = any(c["family"] == "F" and (c["page"], c["system"], c["staff"]) == (pg, s, li) and c["area"][0] - sp <= x <= c["area"][2] + sp
                        for c in claims if not c.get("candidate"))
            inside = any((c["page"], c["system"], c["staff"]) == (pg, s, li) and c["area"][0] <= x <= c["area"][2]
                         for c in claims if not c.get("candidate"))
            cell = max([k for k in order if cells[k][0] <= x] or [order[0]])
            rows.append((nb["match"]["score"], nb["read"], pg, s, li, cell, round(x), "BOXED-F" if boxed else ("in-claim" if inside else "-")))
    print("page", pg, "templates", len(tps), file=sys.stderr)
for r in sorted(rows, reverse=True):
    print(*r)
