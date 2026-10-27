"""2.210 rule-7 look: contact sheet of crops (6 x 8 staff spaces tall enough for the stem), orange = the member box, and (--strokes) the
covered strokes tinted: green owned, red unowned, blue contested. Usage: look.py OUT.png [--strokes] plate:glyph[:label] ...
Reads /private/tmp/.../members.pkl-like dict via MEMBERS env (a pickle {plate: [rows]})."""
import os, pickle, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page
args = sys.argv[1:]
out = args.pop(0); strokes = "--strokes" in args; args = [a for a in args if a != "--strokes"]
M = pickle.load(open(os.environ["MEMBERS"], "rb"))
by = {(p, r["key"]): r for p in M for r in M[p]}
tiles, cache = [], {}
for a in args:
    plate, g, *lab = a.split(":"); pk = plate; plate = {"lit": "litolff", "bra": "brahms"}.get(plate, plate)
    r = by[(pk, g)]; bb = r["bb"]; page = int(g.split("/")[1]); u = LR.PLATES[plate]["unit"]
    if (plate, page) not in cache:
        cache.clear(); cache[(plate, page)] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600).rgb).convert("RGB")
    im = cache[(plate, page)]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    x0, y0, x1, y1 = max(0, int(cx - 4 * u)), max(0, int(cy - 7 * u)), int(cx + 4 * u), int(cy + 7 * u)
    c = im.crop((x0, y0, x1, y1)).copy(); d = ImageDraw.Draw(c, "RGBA")
    if strokes:
        for s in r["strokes"]:
            if s.get("pb"):
                col = {"owned": (0, 160, 0, 90), "free": (230, 0, 0, 90), "contested": (0, 0, 230, 90)}[s["own"]]
                d.rectangle([s["pb"][0] - x0, s["pb"][1] - y0, s["pb"][2] - x0, s["pb"][3] - y0], fill=col)
    d.rectangle([bb[0] - x0, bb[1] - y0, bb[2] - x0, bb[3] - y0], outline=(255, 140, 0), width=max(2, int(u / 8)))
    TW = int(os.environ.get("TW", "300")); c = c.resize((TW, int(TW * c.height / c.width)))
    ImageDraw.Draw(c).text((3, 3), (lab[0] if lab else g[6:]), fill=(200, 0, 200))
    tiles.append(c)
cols = int(os.environ.get("COLS", "4")); TW = int(os.environ.get("TW", "300")); rows = (len(tiles) + cols - 1) // cols; h = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (TW + 4), rows * (h + 4)), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * (TW + 4), (i // cols) * (h + 4)))
sheet.save(out); print(out, sheet.size)
