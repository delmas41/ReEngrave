"""2.291 MY look (not for Sean): contact sheets of bars from PLATE.bars.json, labelled, written heads/rests green, dropped heads/rests red.
usage: look.py BARS.json PLATE OUT_PREFIX [status=red] [N per sheet=8] [cols=4]
Bars are cropped barline to barline (the cell's x extent) and the staff +-3.5 spaces; the staff is one staff of the system (a bar of one instrument)."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw   # noqa: E402

from tools.omr.staged import lane_report as LR   # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

_PG = {}


def page_img(plate, page):
    k = (plate, page)
    if k not in _PG:
        _PG.clear()
        _PG[k] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), page, dpi=600).rgb).convert("RGB")
    return _PG[k]


def bar_crop(plate, b, draw=True, vpad=3.5, hpad=0.6, scale=None):
    u = LR.PLATES[plate]["unit"]
    p, s, st, c = b["key"]
    im = page_img(plate, p)
    x0, _y0, x1, _y1 = b["cell_box"]
    ys = b["staff_lines"]
    top, bot = min(ys), max(ys)
    box = (int(x0 - hpad * u), int(top - vpad * u), int(x1 + hpad * u), int(bot + vpad * u))
    cr = im.crop(box).copy()
    if draw:
        d = ImageDraw.Draw(cr)
        for g in b["glyphs"]:
            if not (g["head"] or g["rest"]) or not g["box"]:
                continue
            col = (0, 150, 0) if g["fate"] in ("written", "written_relocated") else (220, 0, 0)
            gb = g["box"]
            d.rectangle([gb[0] - box[0], gb[1] - box[1], gb[2] - box[0], gb[3] - box[1]], outline=col, width=1)
    sc = scale or (3.0 if u < 20 else 1.6)
    return cr.resize((int(cr.width * sc), int(cr.height * sc)), Image.LANCZOS)


def label(b):
    r = b["red"] or {}
    ev = []
    for q in (b.get("red_rows") or []):
        ev.append("%s%s%s" % ("r" if q["kind"] == "rest" else "n", q["beats"], "g" if q["status"] == "GUESSED" else ""))
    return "p%d s%d st%d c%d m%s %s want %s got %s | %s" % (b["key"][0], b["key"][1], b["key"][2], b["key"][3], b["measure"],
                                                             (b["why"] or "")[:22], r.get("want_quarters"), r.get("counted_quarters"), " ".join(ev))


def main():
    f, plate, outp = sys.argv[1:4]
    status = sys.argv[4] if len(sys.argv) > 4 else "red"
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    cols = int(sys.argv[6]) if len(sys.argv) > 6 else 2
    bars = [b for b in json.load(open(f)) if status == "all" or b["status"] == status]
    sel = sys.argv[7].split(",") if len(sys.argv) > 7 else None
    if sel:
        bars = [b for b in bars if "%d/%d/%d/%d" % tuple(b["key"]) in sel]
    for k in range(0, len(bars), n):
        grp = bars[k:k + n]
        ims = [bar_crop(plate, b) for b in grp]
        labs = [label(b) for b in grp]
        W = max(i.width for i in ims)
        rows = (len(ims) + cols - 1) // cols
        rh = [max(i.height for i in ims[r * cols:(r + 1) * cols]) + 16 for r in range(rows)]
        sh = Image.new("RGB", (cols * (W + 6) + 6, sum(rh) + 6), (255, 255, 255))
        d = ImageDraw.Draw(sh)
        y = 4
        for r in range(rows):
            for cc in range(cols):
                i = r * cols + cc
                if i >= len(ims):
                    break
                x = 6 + cc * (W + 6)
                d.text((x, y), "%d %s" % (k + i + 1, labs[i]), fill=(0, 0, 0))
                sh.paste(ims[i], (x, y + 13))
            y += rh[r]
        out = "%s_%02d.png" % (outp, k // n + 1)
        sh.save(out)
        print(out, len(grp))


if __name__ == "__main__":
    main()
