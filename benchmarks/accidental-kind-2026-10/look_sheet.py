"""2.247: a LOOK sheet (for the lane's own check of a count -- not Sean's tiles; labels drawn): crops of written accidentals from
written_join.py rows, each labelled `n class->written (source)`. usage: look_sheet.py ROWS.json PLATE OUT.png FILTER [N] [SEED]
FILTER: classdecided | disagree | agreeflat | all | pair:CLASS_TYPE:STROKE_TYPE (census rows; * = any)"""
import json
import random
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402


def pick(rows, f, plate=None):
    out = []
    for r in rows:
        if "written" not in r:          # a census.py row (box level): the stroke type in place of the written kind
            if r.get("plate") != plate:
                continue
            r = dict(r, written=str(r["t"]), detector_type=r["dt"], source="strokes")
        if f.startswith("pair:"):
            _p, a, b = f.split(":")
            if r.get("plate") == plate and r["detector_type"] == a and (b == "*" or r["written"] == b):
                out.append(r)
            continue
        if not r.get("page_box"):
            continue
        dt = r.get("detector_type") or ("natural" if "Natural" in r["cls"] else "flat" if "Flat" in r["cls"] else "sharp")
        if f == "classdecided" and r["source"] != "strokes":
            out.append(r)
        elif f == "disagree" and r["source"] == "strokes" and dt != r["written"]:
            out.append(r)
        elif f == "agreeflat" and r["source"] == "strokes" and r["written"] == "flat":
            out.append(r)
        elif f == "all":
            out.append(r)
    return out


def main(rows_path, plate, out_png, f, n=40, seed=2247):
    rows = pick(json.load(open(rows_path)), f, plate)
    random.Random(int(seed)).shuffle(rows)
    rows = sorted(rows[: int(n)], key=lambda r: r["page"])
    u = LR.PLATES[plate]["unit"]
    tiles, cache = [], {}
    for i, r in enumerate(rows, 1):
        if r["page"] not in cache:
            cache.clear()
            cache[r["page"]] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[plate]["pdf"]), r["page"], dpi=600).rgb).convert("RGB")
        im = cache[r["page"]]
        b = r["page_box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        crop = im.crop((int(cx - 2 * u), int(cy - 2.5 * u), int(cx + 3 * u), int(cy + 2.5 * u))).resize((260, 260))
        d = ImageDraw.Draw(crop)
        d.text((2, 2), "%d %s>%s %s" % (i, (r.get("detector_type") or r["cls"])[:3], r["written"][:3], (r.get("why") or r["source"])[:14]), fill=(220, 0, 0))
        tiles.append(crop)
        r["look"] = i
    cols = 6
    sheet = Image.new("RGB", (cols * 264, ((len(tiles) + cols - 1) // cols) * 264), (255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 264, (i // cols) * 264))
    sheet.save(out_png)
    json.dump(rows, open(out_png.replace(".png", ".json"), "w"), indent=0)
    print(len(rows), "crops ->", out_png)


if __name__ == "__main__":
    main(*sys.argv[1:])
