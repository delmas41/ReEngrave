"""2.247: the member strokes of accidental boxes, for designing the natural-vs-flat shape test offline (STAGED GATHER stroke map, read only).
Items: Sean's 142 hand boxes on Brahms pp.0-3 (truth = his label; 2.197 truth, the 2.201 held-out set) and census.py rows (detector boxes,
truth unknown: class + stroke type only). Cells are re-cut per page (`pipeline.prepare_pages`), the box mapped page -> canonical cell px.
usage: dump_strokes.py OUT.json [--census N_PER_PAIR]"""
import collections
import json
import os
import random
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-accidental-family-2026-10")
from tools.omr.staged import accidental_family as AF  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import pipeline  # noqa: E402
from tools.omr.staged import stroke_map as SM  # noqa: E402
import cause_cut as CC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def stroke_row(s, ext, sp):
    x, y, w, h = s.box
    return {"kind": s.kind, "x0": round((x - ext[0]) / sp, 2), "y0": round((y - ext[1]) / sp, 2), "w": round(w / sp, 2), "h": round(h / sp, 2),
            "len": round(s.length_sp, 2), "angle": round(s.angle_deg, 1), "thick": round(s.thickness_sp, 2), "fill": round(s.fill, 2),
            "hole": s.hole_share, "sag": s.sagitta_sp, "area": round(s.area_sp2, 3)}


def read_items(plate, items):
    by = collections.defaultdict(list)
    for it in items:
        by[it["page"]].append(it)
    out = []
    for page, its in sorted(by.items()):
        pws, cells = pipeline.prepare_pages(CC.PDF[plate], [page], dpi=600)[0]
        smap = {}
        for it in its:
            bx0, by0, bx1, by1 = it["page_box"]
            best = None
            for c in cells:
                cb = c.bbox_page_px
                ix = max(0, min(bx1, cb[2]) - max(bx0, cb[0]))
                iy = max(0, min(by1, cb[3]) - max(by0, cb[1]))
                fr = ix * iy / max(1e-9, (bx1 - bx0) * (by1 - by0))
                if best is None or fr > best[0]:
                    best = (fr, c)
            fr, c = best
            grid = G._cell_grid(c)
            if grid is None:
                continue
            sp = grid[1] * 2.0
            if id(c) not in smap:
                smap[id(c)] = SM.map_strokes(c.image_no_staff, sp, list(c.staff_line_ys_canonical), c.binary)
            res = smap[id(c)]
            up, cb = c.upscale_factor, c.bbox_page_px
            box = ((bx0 - cb[0]) * up, (by0 - cb[1]) * up, (bx1 - cb[0]) * up, (by1 - cb[1]) * up)
            fam = AF.family_row(it["cls"], box, res.strokes, SM.strokes_in_box(res, box), sp, masks=res.masks, scale=res.scale)
            ext = fam["box"]
            out.append(dict(it, type=fam["type"], why=fam["why"], feat=fam["features"], cell_frac=round(fr, 2), sp=sp,
                            ext_sp=[round((ext[2] - ext[0]) / sp, 2), round((ext[3] - ext[1]) / sp, 2)],
                            members=[stroke_row(res.strokes[i], ext, sp) for i in fam["members"]]))
    return out


def main(out_path, *a):
    n_pair = int(a[a.index("--census") + 1]) if "--census" in a else 0
    truth = json.load(open("benchmarks/omr-accidental-family-2026-10/data/truth_brahms.json"))["items"]
    items = [dict(src="hand:" + t["src"], plate="brahms", page=t["page"], page_box=t["box"], cls=t["cls"], sean=t["type"]) for t in truth]
    out = read_items("brahms", items)
    if n_pair:
        cen = json.load(open(os.path.join(HERE, "data", "census.json")))
        rng = random.Random(2247)
        for plate in ("litolff", "brahms"):
            sel = []
            groups = collections.defaultdict(list)
            for r in cen:
                if r["plate"] == plate and r.get("page_box"):
                    groups[(r["dt"], r["t"])].append(r)
            for k in [("natural", "flat"), ("sharp", "flat"), ("flat", "flat"), ("natural", "natural"), ("flat", "natural"), ("flat", "unclear")]:
                g = groups.get(k, [])
                rng.shuffle(g)
                sel += g[:n_pair]
            out += read_items(plate, [dict(src="census", plate=plate, page=r["page"], page_box=r["page_box"], cls=r["cls"], subject=r["subject"],
                                           night_type=r["t"], dt=r["dt"]) for r in sel])
    json.dump(out, open(out_path, "w"), indent=0, default=float)
    print(len(out), "->", out_path)


if __name__ == "__main__":
    main(*sys.argv[1:])
