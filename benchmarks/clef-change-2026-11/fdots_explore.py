"""2.251 carry, exploration: every dot pair straddling the F line (line 4) on every staff of the given pages, with the body score
left of it against the page's own header F clefs. Known F clefs (header and change claims) vs everything else.

python3 work-2.251/fdots_explore.py PLATE PAGES BOXES.jsonl CLAIMS.json
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import scan_claims as SC  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

plate, pages, bpath, cpath = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
want = []
for part in pages.split(","):
    a, _, b = part.partition("-")
    want.extend(range(int(a), int(b or a) + 1))
boxes = SC.load_boxes(bpath)
claims = json.load(open(cpath))
def templates_of(ink, pg):
    """The page's own READ F clefs (a clef-sized `clefF` box passing its dots), each body a template."""
    out = []
    for s, li, t, cells in SC.staves_of(plate, pg):
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        for name, pb, sc, c, subj in boxes.get((pg, s, li), []):
            if name != "clefF" or (pb[3] - pb[1]) / sp < 2.0:
                continue
            ll = CP.local_lines(ink, lines, sp, pb[0])
            got = CP.read_box(name, pb, ink, ll, sp)
            if not got["passed"] or not got.get("body"):
                continue
            dr = got.get("dots_right")
            prs = [p for p in CP.f_dot_pairs(ink, lines, sp, pb[0] - 2 * sp, pb[2] + 2 * sp) if dr and abs(p["x_right"] - dr) <= 0.3 * sp]
            if not prs:
                continue
            body = list(got["body"])
            body[2] = min(body[2], prs[0]["x_left"] - 1)
            tp = CP.f_template(ink, lines, sp, body, prs[0]["x_left"])
            if tp:
                tp["where"] = (s, li, round(pb[0]))
                out.append(tp)
    return out


ALL = []
for pg in want:
    for t in templates_of(SC.page_ink(plate, pg), pg):
        t["where"] = (pg,) + t["where"]
        ALL.append(t)
# one template per page (the plate prints one glyph; a few sizes)
POOL, seen = [], set()
for t in ALL:
    if t["where"][0] not in seen and len(POOL) < 8:
        seen.add(t["where"][0]); POOL.append(t)
print("templates", [t["where"] for t in POOL])
for pg in want:
    ink = SC.page_ink(plate, pg)
    for s, li, t, cells in SC.staves_of(plate, pg):
        if not cells:
            continue
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        order = sorted(cells)
        x_lo, x_hi = cells[order[0]][0], cells[order[-1]][2]
        known = [c for c in claims if (c["page"], c["system"], c["staff"]) == (pg, s, li) and c["family"] == "F"]
        fbox = [b for b in boxes.get((pg, s, li), []) if b[0] == "clefF"]
        for p in CP.f_dot_pairs(ink, lines, sp, x_lo, x_hi):
            tps = [t for t in POOL if not (t["where"][:3] == (pg, s, li) and abs(t["where"][3] - p["x_left"]) < 4 * sp)]
            body = CP.f_body_shape(ink, lines, sp, p, tps)
            k = any(c["area"][0] - sp <= p["x_left"] <= c["area"][2] + sp for c in known)
            hasbox = any(b[1][0] - sp <= p["x_left"] <= b[1][2] + 2 * sp for b in fbox)
            cell = max([k2 for k2 in order if cells[k2][0] <= p["x_left"]] or [order[0]])
            print(pg, s, li, "c%d" % cell, round(p["x_left"]), "KNOWN" if k else ("box" if hasbox else "-"),
                  round(p["residual"], 2), body)
