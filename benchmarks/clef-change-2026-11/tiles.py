"""2.251 step 1's 12 blind tiles: what the page-wide clef reader found (claims) and nearly found (near-misses), drawn from the PRINT
with one thin orange box sized to the mark at its own staff's position -- nothing of ours named on the tile. Key separate.

python3 work-2.251/tiles.py OUTDIR SEED
Pool (the reader's own functions on the print raster + the cell maps' staves; the same raster the pipeline reads):
  change  -- a passing C bar or a passing clefF box inside a system (past the header window)
  header  -- a passing C bar in the header window (controls: the header clef is read today)
  near    -- a bar that failed on its bowls / a clefF box that failed its dots, inside a system
"""
import json, os, random, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import crops  # noqa: E402
from tools.omr.staged import clef_pagewide as CP  # noqa: E402

PAGES = {"litolff": list(range(1, 17)), "brahms": [1, 3, 4, 5, 12, 14, 19, 25]}


def pool():
    out = []
    for plate, pages in PAGES.items():
        boxes = {}
        sl = f"library/_shared-records/lane-report-slices-20261029-night/{plate}/observations.jsonl"
        for line in open(sl):
            if '"glyph_box"' in line and '"clefF' in line:
                r = json.loads(line)
                if r["quantity"] == "glyph_box":
                    p = r["subject"].split("/")
                    boxes.setdefault((int(p[1]), int(p[2]), int(p[3])), []).append(r["detail"]["bbox_page_px"])
        for pg in pages:
            ink = np.asarray(crops.page_img(plate, pg).convert("L")) < 128
            d = crops.cmap(plate, pg)
            for s in sorted({t["system_index"] for t in d["staves"]}):
                staves = sorted([t for t in d["staves"] if t["system_index"] == s], key=lambda t: t["line_ys"][0])
                for li, st in enumerate(staves):
                    ly = st["line_ys"]; sp = (ly[4] - ly[0]) / 4
                    head = st["x_start"] + CP.HEADER_WINDOW_SPACES * sp
                    for c in CP.c_bars(ink, ly, sp, st["x_start"], st["x_end"]):
                        if c["why"] == "bar_too_thin":
                            continue
                        area = CP.c_area(c, sp)
                        kind = "near" if not c["passed"] else ("header" if c["x0"] <= head else "change")
                        nm = CP.name_c(c["middle_y"], c["lines_local"])[0] if c["passed"] else None
                        out.append(dict(plate=plate, page=pg, system=s, staff=li, area=area, cls=kind, family="C",
                                        read=nm, why=c["why"]))
                    seen = []
                    for bb in boxes.get((pg, s, li), []):
                        if (bb[3] - bb[1]) / sp < 2.0 or bb[0] <= head or any(abs(bb[0] - x) < 2 * sp for x in seen):
                            continue
                        seen.append(bb[0])
                        ll = CP.local_lines(ink, ly, sp, bb[0])
                        got = CP.read_box("clefF", bb, ink, ll, sp)
                        out.append(dict(plate=plate, page=pg, system=s, staff=li, area=CP.f_claim_area(got, bb, sp),
                                        cls="change" if got["passed"] else "near", family="F", read=got["kind"], why=got["why"]))
    return out


def tile(t):
    d = crops.cmap(t["plate"], t["page"])
    st = sorted([x for x in d["staves"] if x["system_index"] == t["system"]], key=lambda x: x["line_ys"][0])[t["staff"]]
    ly = st["line_ys"]; sp = (ly[4] - ly[0]) / 4
    a = t["area"]
    x0, x1 = int(a[0] - 6 * sp), int(a[2] + 6 * sp)
    y0, y1 = int(ly[0] - 4 * sp), int(ly[4] + 4 * sp)
    im = crops.page_img(t["plate"], t["page"]).crop((x0, y0, x1, y1)).convert("RGB")
    z = 3
    im = im.resize((im.width * z, im.height * z), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    dr.rectangle([(a[0] - x0) * z, (a[1] - y0) * z, (a[2] - x0) * z, (a[3] - y0) * z], outline=(255, 140, 0), width=3)
    return im


def main():
    out, seed = sys.argv[1], int(sys.argv[2])
    os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
    rng = random.Random(seed)
    P = pool()
    by = {k: [t for t in P if t["cls"] == k] for k in ("change", "header", "near")}
    print({k: len(v) for k, v in by.items()})
    def draw(cls, plate, n, family=None):
        c = [t for t in by[cls] if t["plate"] == plate and (family is None or t["family"] == family)]
        return rng.sample(c, min(n, len(c)))
    pick = (draw("change", "litolff", 2, "C") + draw("change", "litolff", 2, "F") + draw("change", "brahms", 2, "C")
            + draw("change", "brahms", 1, "F") + draw("header", "litolff", 1) + draw("header", "brahms", 1)
            + draw("near", "litolff", 2) + draw("near", "brahms", 1))
    print({(k, pl, f): len([t for t in by[k] if t["plate"] == pl and t["family"] == f]) for k in by for pl in PAGES for f in "CF"})
    rest = [t for t in by["change"] if t not in pick]
    while len(pick) < 12 and rest:                     # a stratum with too few (Brahms F inside a system: 0) is topped up from the changes
        pick.append(rest.pop(rng.randrange(len(rest))))
    rng.shuffle(pick)
    key = []
    for i, t in enumerate(pick, 1):
        tile(t).save(os.path.join(out, "tiles", f"{i:02d}.png"))
        key.append(dict(tile=i, **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in t.items() if k != "area"},
                        area=[round(v, 1) for v in t["area"]]))
    json.dump({"seed": seed, "what": "2.251 step 1 tiles, stratified: found inside a system (Litolff 2 C + 2 F, Brahms 2 C + 1 F), 2 header controls, 3 near-misses (shuffled)",
               "pool": {k: len(v) for k, v in by.items()}, "tiles": key}, open(os.path.join(out, "key.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
