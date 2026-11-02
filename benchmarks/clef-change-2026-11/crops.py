"""Crops of the PRINT (nothing of ours drawn) for the 2.251 count.

python3 work-2.251/crops.py page PLATE PG SCALE OUT          -- whole page, scaled
python3 work-2.251/crops.py strip PLATE PG SYS STAFF C0 C1 OUT -- one staff (+/- 0.8 staff above/below), cells C0..C1, x3 zoom
"""
import gzip, json, os, sys
from functools import lru_cache
from PIL import Image, ImageDraw

sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "library"
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
CM = {"litolff": "library/_shared-records/cell-maps/55d95838e0709b92-dpi600",
      "brahms": "library/_shared-records/cell-maps/be40c09fbd9f55f0-dpi600"}
CACHE = "work-2.251/pages"


def page_img(plate, pg):
    os.makedirs(CACHE, exist_ok=True)
    p = f"{CACHE}/{plate}-p{pg}.png"
    if not os.path.exists(p):
        Image.fromarray(render_page(os.path.join(LIB, PDF[plate]), pg, dpi=600).rgb).convert("RGB").save(p)
    return Image.open(p)


@lru_cache(None)
def cmap(plate, pg):
    return json.load(gzip.open(f"{CM[plate]}/pages/p{pg:03d}.json.gz"))


def strip(plate, pg, sys_i, staff_local, c0, c1, label=""):
    d = cmap(plate, pg)
    staves = sorted([s for s in d["staves"] if s["system_index"] == sys_i], key=lambda s: s["line_ys"][0])
    st = staves[staff_local]
    gidx = st["staff_index"]
    cells = [c["v"] for c in d["cells"] if c["v"]["system_index"] == sys_i and c["v"]["staff_index"] == gidx]
    cells = {c["measure_index"]: c["bbox_page_px"]["$t"] for c in cells}
    c0 = max(c0, min(cells)); c1 = min(c1, max(cells))
    x0 = cells[c0][0] - 10
    x1 = cells[c1][2] + 10
    sp = (st["line_ys"][4] - st["line_ys"][0]) / 4.0
    y0 = int(st["line_ys"][0] - 5 * sp); y1 = int(st["line_ys"][4] + 5 * sp)
    im = page_img(plate, pg).crop((x0, y0, x1, y1))
    z = 3
    im = im.resize((im.width * z, im.height * z), Image.LANCZOS)
    # cell ticks ABOVE the crop (a strip, not drawn on the ink) so a cell index can be named
    band = Image.new("RGB", (im.width, 40), "white")
    dr = ImageDraw.Draw(band)
    for mi in range(c0, c1 + 1):
        bx = (cells[mi][0] - x0) * z
        dr.line([(bx, 20), (bx, 40)], fill="black", width=2)
        dr.text((bx + 4, 2), f"c{mi}", fill="black")
    dr.text((im.width - 400, 2), label, fill="black")
    out = Image.new("RGB", (im.width, im.height + 40), "white")
    out.paste(band, (0, 0)); out.paste(im, (0, 40))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "page":
        plate, pg, scale, out = a[1], int(a[2]), float(a[3]), a[4]
        im = page_img(plate, pg)
        im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS).save(out)
    elif a[0] == "strip":
        plate, pg, s, st, c0, c1, out = a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), int(a[6]), a[7]
        strip(plate, pg, s, st, c0, c1).save(out)
