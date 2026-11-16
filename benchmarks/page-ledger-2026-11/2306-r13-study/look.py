"""2.306 r13 study, MY look (a lead, never evidence): per head two panels -- LEFT the print as it is (un-erased page, nothing drawn but a small
blue tick under the head); RIGHT the same crop with what the readers hold: the page map's strokes (vertical green, held vertical red, blob grey,
horizontal light blue, curve pink -- thin outlines), the head box NEW used (blue), OLD's stem box (orange), NEW's stem box (magenta).
Usage (cwd = repo root): look.py lit|bra OUT.png glyph [glyph ...]   or   look.py lit|bra OUT.png @list.json"""
import sys, os, json
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from PIL import Image, ImageDraw

_pages = {}


def page_img(plate, p):
    if (plate, p) not in _pages:
        fn = "%s/r13/page-%s-%d.png" % (S, plate, p)
        if not os.path.exists(fn):
            from tools.omr.preprocessing import render_page
            Image.fromarray(render_page(PDF[plate], p, dpi=600).rgb).convert("RGB").save(fn)
        _pages[(plate, p)] = Image.open(fn).convert("RGB")
    return _pages[(plate, p)]


COL = dict(vertical=(0, 160, 0), blob=(140, 140, 140), horizontal=(60, 140, 255), curve=(255, 105, 180), barline=(120, 60, 0))


def panel(plate, D, T, held_of, g, zoom=None, half_w=5.0, half_h=6.5, label=None):
    r = T[g]
    p = r["page"]
    sp = r["sp"]
    im = page_img(plate, p)
    hb = r["head_box"]
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    x0, y0, x1, y1 = int(cx - half_w * sp), int(cy - half_h * sp), int(cx + half_w * sp), int(cy + half_h * sp)
    z = zoom or max(2, int(round(60.0 / sp)))
    left = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.LANCZOS)
    right = left.copy()
    dl, dr = ImageDraw.Draw(left), ImageDraw.Draw(right)
    f = lambda b: [(b[0] - x0) * z, (b[1] - y0) * z, (b[2] - x0) * z, (b[3] - y0) * z]
    tx = (cx - x0) * z
    ty = (hb[3] - y0) * z + 6
    dl.line([tx - 6, ty + 8, tx, ty, tx + 6, ty + 8], fill=(0, 0, 255), width=2)
    for i, s in D["pstrokes"][p].items():
        b = s["box"]
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        col = (230, 0, 0) if (i in held_of.get(p, {}) and s["kind"] == "vertical") else COL.get(s["kind"], (0, 0, 0))
        dr.rectangle(f(b), outline=col, width=1)
    nb = r.get("new_head_box") or hb
    dr.rectangle(f(nb), outline=(0, 0, 255), width=2)
    if r.get("old_box"):
        b = r["old_box"]
        dr.rectangle(f([b[0] - 1.5, b[1], b[2] + 1.5, b[3]]), outline=(255, 140, 0), width=2)
    if r.get("new_box"):
        b = r["new_box"]
        dr.rectangle(f([b[0] - 3, b[1] - 1, b[2] + 3, b[3] + 1]), outline=(255, 0, 255), width=1)
    W, H = left.size
    out = Image.new("RGB", (W * 2 + 6, H + 34), "white")
    out.paste(left, (0, 34))
    out.paste(right, (W + 6, 34))
    d = ImageDraw.Draw(out)
    d.text((2, 2), label or g, fill=(0, 0, 0))
    d.text((2, 16), "OLD %s %s | NEW %s %s" % (r.get("old_why"), r.get("old_dir"), r.get("new_how"), r.get("new_dir")), fill=(160, 0, 0))
    return out


def sheet(plate, glyphs, outp, cols=4, labels=None):
    import replay as RP
    D = load(plate)
    T = {r["g"]: r for r in json.load(open("%s/r13/%s.trace.json" % (S, plate)))}
    held_of = {p: RP.inputs(D, p)[2] for p in sorted({T[g]["page"] for g in glyphs})}
    tiles = [panel(plate, D, T, held_of, g, label=(labels or {}).get(g)) for g in glyphs]
    W, H = max(t.width for t in tiles), max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (W + 8), rows * (H + 8)), (255, 255, 255))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % cols) * (W + 8), (i // cols) * (H + 8)))
    sh.save(outp)
    return outp


if __name__ == "__main__":
    plate, outp, gl = sys.argv[1], sys.argv[2], sys.argv[3:]
    labels = None
    if gl and gl[0].startswith("@"):
        j = json.load(open(gl[0][1:]))
        gl = [t["g"] if isinstance(t, dict) else t for t in j]
        labels = {t["g"]: t.get("label") for t in j if isinstance(t, dict)}
    print(sheet(plate, gl, outp, labels=labels))
