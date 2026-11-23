"""2306 r11, MY look: page-map strokes around given heads, 4x, outlined by kind (vertical green, blob orange, horizontal blue, other grey), the
detector head box red, ordinals written small. Usage (cwd = tree): r11_strokes_look.py REC PDF OUT.png glyph ..."""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw
rec, pdf, outp, gs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
pages = {int(g.split("/")[1]) for g in gs}
R = json.load(open(rec))["record"]
st = collections.defaultdict(list)
gbox = {}
for o in R["observations"]:
    q, d = o["quantity"], o.get("detail") or {}
    if not o["subject"].startswith(("page/", "glyph/")) or int(o["subject"].split("/")[1]) not in pages:
        continue
    if q == "page_stroke":
        st[int(o["subject"].split("/")[1])].append((int(d["ordinal"]), o["value"], d["bbox_page_px"]))
    elif q == "glyph_box" and d.get("bbox_page_px"):
        gbox[o["subject"]] = d["bbox_page_px"]
del R
col = {"vertical": (0, 160, 0), "blob": (255, 120, 0), "horizontal": (0, 0, 255)}
tiles = []
cache = {}
for g in gs:
    p = int(g.split("/")[1])
    if p not in cache:
        cache[p] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    hb = gbox[g]
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    X0, Y0, X1, Y1 = int(cx - 45), int(cy - 70), int(cx + 45), int(cy + 70)
    S = 4
    t = cache[p].crop((X0, Y0, X1, Y1)).resize(((X1 - X0) * S, (Y1 - Y0) * S), Image.NEAREST)
    dr = ImageDraw.Draw(t)
    for o, k, b in st[p]:
        if b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1:
            continue
        r = [(b[0] - X0) * S, (b[1] - Y0) * S, (b[2] - X0) * S, (b[3] - Y0) * S]
        dr.rectangle(r, outline=col.get(k, (150, 150, 150)), width=1)
        dr.text((r[0] + 2, r[1] + 1), str(o), fill=col.get(k, (150, 150, 150)))
    dr.rectangle([(hb[0] - X0) * S, (hb[1] - Y0) * S, (hb[2] - X0) * S, (hb[3] - Y0) * S], outline=(255, 0, 0), width=2)
    dr.text((3, 3), g, fill=(255, 0, 0))
    tiles.append(t)
sheet = Image.new("RGB", (sum(t.width for t in tiles) + 10 * len(tiles), max(t.height for t in tiles)), "white")
x = 0
for t in tiles:
    sheet.paste(t, (x, 0))
    x += t.width + 10
sheet.save(outp)
print(outp)
