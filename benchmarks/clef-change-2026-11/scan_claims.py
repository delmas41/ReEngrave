"""2.251 carry: step 1's clef claims re-run OFF-LINE on whole pages (cell-map staves and cells, the print raster, the night record's
detector boxes from `extract_boxes.py`), the same witnesses `gather.gather_clef_pagewide` uses (C bar + bowls; a clef-sized box + its
second witness; no C claim on a clef-sized G/F box). Header-window clefs are listed too (the return a new system reprints).

python3 work-2.251/scan_claims.py PLATE PAGES BOXES.jsonl [OUT.json]
Each claim: page, system, staff (local, top to bottom), cell, x, family, kind, change, witnesses.
"""
import json, os, sys
from collections import defaultdict
import numpy as np

sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import crops  # noqa: E402
from tools.omr.staged import claims as CL  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402


INK_CACHE = os.environ.get("CLEF_INK_CACHE", "/tmp/clef-ink")


def page_ink(plate, pg):
    """The page's ink exactly as GATHER sees it: `render_page(...).binary == 0` (the array the cell map hashes as `binary`)."""
    from tools.omr.preprocessing import render_page
    os.makedirs(INK_CACHE, exist_ok=True)
    p = os.path.join(INK_CACHE, "%s-p%d.npy" % (plate, pg))
    if os.path.exists(p):
        return np.load(p)
    ink = np.asarray(render_page(os.path.join(crops.LIB, crops.PDF[plate]), pg, dpi=600).binary) == 0
    np.save(p, ink)
    return ink


def overlap_share(a, b):
    iw, ih = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    aw, ah = a[2] - a[0], a[3] - a[1]
    return iw * ih / (aw * ah) if iw > 0 and ih > 0 and aw > 0 and ah > 0 else 0.0


def load_boxes(path):
    out = defaultdict(list)
    seen = set()
    for line in open(path):
        r = json.loads(line)
        _, pg, s, st, c, gi = r["s"].split("/")
        bb = r["bb"]
        if not bb:
            continue
        key = (int(pg), int(s), int(st), r["c"], round(bb[0] / 6), round(bb[1] / 6))
        if key in seen:
            continue                       # padded-cell copy
        seen.add(key)
        out[(int(pg), int(s), int(st))].append((r["c"], bb, r["sc"], int(c), r["s"]))
    return out


def staves_of(plate, pg):
    d = crops.cmap(plate, pg)
    by_sys = defaultdict(list)
    for t in d["staves"]:
        by_sys[t["system_index"]].append(t)
    cells = defaultdict(dict)
    for c in d["cells"]:
        v = c["v"]
        cells[(v["system_index"], v["staff_index"])][v["measure_index"]] = v["bbox_page_px"]["$t"]
    for s in sorted(by_sys):
        for li, t in enumerate(sorted(by_sys[s], key=lambda t: t["line_ys"][0])):
            yield s, li, t, cells[(s, t["staff_index"])]


def scan_page(plate, pg, boxes, ink=None, extra=None):
    """Every clef step 1 claims on page `pg` (`extra`: a callable(ink, lines, sp, x_lo, x_hi, staff_boxes) -> more claims, the
    reader under test)."""
    if ink is None:
        ink = page_ink(plate, pg)
    out = []
    templates = []
    if os.environ.get("OMR_CLEF_CARRY") == "1":
        per = []
        for s, li, t, mycells in staves_of(plate, pg):
            lines = [float(v) for v in t["line_ys"]]
            sp = (lines[4] - lines[0]) / 4.0
            per.append((lines, sp, [b[1] for b in boxes.get((pg, s, li), []) if b[0] == "clefF" and CL.is_clef_box(b[0], b[1], sp)]))
        templates = CP.f_templates(ink, per)
    for s, li, t, mycells in staves_of(plate, pg):
        if not mycells:
            continue
        lines = [float(v) for v in t["line_ys"]]
        sp = (lines[4] - lines[0]) / 4.0
        order = sorted(mycells)
        x_lo, x_hi = mycells[order[0]][0], mycells[order[-1]][2]

        def cell_at(x):
            got = order[0]
            for k in order:
                if mycells[k][0] <= x:
                    got = k
            return got
        found = []
        for cand in CP.c_bars(ink, lines, sp, x_lo, x_hi):
            if not cand["passed"]:
                continue
            nm, ln, res = CP.name_c(cand["middle_y"], cand.get("lines_local") or lines)
            found.append({"area": CP.c_area(cand, sp), "family": "C", "kind": nm, "witnesses": ["c_bar", "c_bowls"]})
        sb = boxes.get((pg, s, li), [])
        other = []
        for name, pb, sc, c, subj in sb:
            if not CL.is_clef_box(name, pb, sp):
                continue
            if name.startswith(("clefG", "clefF")):
                other.append(pb)
            ll = CP.local_lines(ink, lines, sp, pb[0])
            got = CP.read_box(name, pb, ink, ll, sp)
            if not got["passed"]:
                continue
            if got["family"] == "C" and any(CL.overlaps(f["area"], pb) for f in found):
                continue
            area = CP.f_claim_area(got, pb, sp) if got["family"] == "F" else list(pb)
            if any(CL.overlaps(f["area"], area) and f["family"] == got["family"] for f in found):
                continue
            found.append({"area": area, "family": got["family"], "kind": got["kind"], "witnesses": ["detector_box", got["family"]]})
        if templates:
            for nb in CP.f_nobox(ink, lines, sp, mycells[order[0]][0] + CP.HEADER_WINDOW_SPACES * sp, x_hi, templates):
                if any(f["family"] == "F" and CL.overlaps(f["area"], nb["area"]) for f in found):
                    continue
                if nb["read"]:
                    found.append({"area": nb["area"], "family": "F", "kind": "bass", "witnesses": ["f_dots", "f_body_template"]})
                else:
                    out.append({"page": pg, "system": s, "staff": li, "cell": None, "x": round(nb["area"][0]), "family": "F",
                                "kind": None, "change": True, "candidate": True, "score": nb["match"]["score"], "area": nb["area"],
                                "x_cand": round(nb["pair"]["x_left"] - 0.3 * sp)})
        if extra is not None:
            for f in extra(ink, lines, sp, x_lo, x_hi, sb):
                if not any(CL.overlaps(g["area"], f["area"]) for g in found):
                    found.append(f)
        for f in found:
            if f["family"] == "C" and any(overlap_share(f["area"], b) >= 0.2 for b in other):
                continue
            k = cell_at(f["area"][0])
            change = not (k == order[0] and (f["area"][0] - mycells[k][0]) / sp <= CP.HEADER_WINDOW_SPACES)
            out.append({"page": pg, "system": s, "staff": li, "cell": k, "x": round(f["area"][0]), "family": f["family"],
                        "kind": f["kind"], "change": change, "witnesses": f["witnesses"], "area": [round(v, 1) for v in f["area"]]})
    return out


if __name__ == "__main__":
    plate, pages, bpath = sys.argv[1], sys.argv[2], sys.argv[3]
    want = []
    for part in pages.split(","):
        a, _, b = part.partition("-")
        want.extend(range(int(a), int(b or a) + 1))
    boxes = load_boxes(bpath)
    allc = []
    for pg in want:
        allc.extend(scan_page(plate, pg, boxes))
        print("page", pg, "claims", sum(1 for c in allc if c["page"] == pg), file=sys.stderr)
    if len(sys.argv) > 4:
        json.dump(allc, open(sys.argv[4], "w"), indent=0)
    for c in allc:
        print(c["page"], c["system"], c["staff"], c["cell"], c["x"], c["family"], c["kind"], "change" if c["change"] else "header")
