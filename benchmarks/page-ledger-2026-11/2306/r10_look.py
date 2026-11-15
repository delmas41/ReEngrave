"""2306 r10, MY look (leads only): for rows of r10_near's dump, a 3x crop: the head box the reader used (blue), the nearest vertical run (green),
every page-map stroke in the window outlined thin grey. Usage (cwd = tree): r10_look.py DUMP.json REC.json PDF OUTPNG CLASS N"""
import sys, os, json, re
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw
dump, rec, pdf, outp, cls, n = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
rows = [r for r in json.load(open(dump)) if r.get("offline") == "no_stroke"]


def ff(r):
    b = r.get("nearest")
    if not b:
        return "none"
    ks = [k for k, m in b["fails"]]
    if not ks:
        return "passes"
    if "x_off_edge" in ks:
        return "x_in" if b["dx_out"] < 0 else "x_out"
    return ks[0]


rows = [r for r in rows if ff(r) == cls][:n]
txt = open(rec, encoding="utf-8").read()
tiles = []
pages = {}
for r in rows:
    p = int(r["g"].split("/")[1])
    if p not in pages:
        pages[p] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    im = pages[p].copy()
    dr = ImageDraw.Draw(im)
    hb = r["head_box"]
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    W = 70
    for m in re.finditer(r'"subject":"page/%d","quantity":"page_stroke","value":"([a-z]+)".{0,200}?"bbox_page_px":\[([^\]]*)\]' % p, txt):
        b = [float(v) for v in m.group(2).split(",")]
        if b[2] >= cx - W and b[0] <= cx + W and b[3] >= cy - 2 * W and b[1] <= cy + 2 * W:
            dr.rectangle(b, outline=(170, 170, 170), width=1)
    dr.rectangle(hb, outline=(0, 0, 255), width=1)
    st = r["nearest"]
    if st:
        for mo in st["members"]:
            m = re.search(r'"subject":"page/%d","quantity":"page_stroke","value":"[a-z]+".{0,200}?"ordinal":%d,.{0,200}?"bbox_page_px":\[([^\]]*)\]' % (p, mo), txt)
            if m:
                dr.rectangle([float(v) for v in m.group(1).split(",")], outline=(0, 170, 0), width=1)
    t = im.crop((int(cx - W), int(cy - 2 * W), int(cx + W), int(cy + 2 * W))).resize((3 * 2 * W, 3 * 4 * W), Image.NEAREST)
    ImageDraw.Draw(t).text((3, 3), r["g"] + " " + str(st and (st["dx_out"], st["gap"], st["reach"])), fill=(255, 0, 0))
    tiles.append(t)
sheet = Image.new("RGB", (len(tiles) * tiles[0].width, tiles[0].height), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, (i * t.width, 0))
sheet.save(outp)
print(outp, [r["g"] for r in rows])
