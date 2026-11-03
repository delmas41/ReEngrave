"""ROADMAP 2.254 round 3 blind tiles for Sean, cut from the ON arm's EXPORTED places (a lane_report work dir), from a spec of items:

    python3 benchmarks/hairpin-reach-2026-11/tiles_r3.py WORKDIR SPEC.json out/print/2.254-r3-tiles   # key: out/print/2.254-r3-tiles-key.json

SPEC: a list of {"role", "plate", "page", "staff": "sys/staff", "box": [x0, y0, x1, y1] (the mark, page px), "with": [subjects whose glyph
boxes the crop must hold whole: a span's start and stop notes], "lane_wrote": "..."}. One staff each; ONE thin orange box sized to the
mark, nothing else drawn. Round-2 lesson (tile 5): a span tile's crop holds the WHOLE start and stop notes -- heads, stems, flags, dots --
and both hairpin ends, so the crop is the union of the hairpin and those notes' boxes plus 2.5 spaces, and reaches from 4 spaces above
the staff (stems, ledger notes) to 1.5 spaces under the lowest mark.
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tiles as T1  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402

SEED = 2254


def glyph_boxes(rec, subjects):
    want, out = set(subjects), {}
    if not want:
        return out
    for it in iter_array(rec, "observations"):
        if it.get("subject") in want and it.get("quantity") == "glyph_box":
            bb = (it.get("detail") or {}).get("bbox_page_px")
            if bb and len(bb) == 4:
                out[it["subject"]] = [float(v) for v in bb]
    return out


def main(work, spec, out):
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page
    work, out = pathlib.Path(work), pathlib.Path(out)
    items = json.loads(pathlib.Path(spec).read_text())
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    rng = random.Random(SEED)
    rng.shuffle(items)
    need = {}
    for it in items:
        need.setdefault(it["plate"], set()).update(it.get("with") or ())
    boxes = {pl: glyph_boxes(work / ("%s.on.gathered.record.json" % pl), subs) for pl, subs in need.items()}
    cache, key, tiles, renders = {}, [], [], {}
    for n, it in enumerate(items, 1):
        plate, page = it["plate"], int(it["page"])
        sys_, staff = (int(v) for v in it["staff"].split("/"))
        top, bot, sp, _pws = T1.staff_box(plate, page, sys_, staff, cache)
        if (plate, page) not in renders:
            renders.clear()
            renders[(plate, page)] = Image.fromarray(render_page(T1.C.EDITIONS[plate][0], page, dpi=600).rgb).convert("RGB")
        im = renders[(plate, page)]
        b = [float(v) for v in it["box"]]
        allb = [b] + [boxes[plate][s] for s in it.get("with") or () if s in boxes[plate]]
        missing = [s for s in it.get("with") or () if s not in boxes[plate]]
        x0 = int(max(0, min(v[0] for v in allb) - 2.5 * sp))
        x1 = int(min(im.width, max(v[2] for v in allb) + 2.5 * sp))
        if x1 - x0 < 12 * sp:
            c = (x0 + x1) / 2.0
            x0, x1 = int(max(0, c - 6 * sp)), int(min(im.width, c + 6 * sp))
        y0 = int(max(0, min(top - 4 * sp, min(v[1] for v in allb) - 1.0 * sp)))
        y1 = int(min(im.height, max(bot, max(v[3] for v in allb)) + 1.5 * sp))
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([b[0] - 3 - x0, b[1] - 3 - y0, b[2] + 3 - x0, b[3] + 3 - y0], outline=T1.ORANGE, width=2)
        W = 760
        crop = crop.resize((W, max(1, int(W * crop.height / crop.width))))
        crop.save(out / ("tile_%02d.png" % n))
        tiles.append(crop)
        key.append(dict(tile=n, role=it["role"], plate=plate, page=page, staff=it["staff"], box=[round(v, 1) for v in b],
                        width_spaces=round((b[2] - b[0]) / sp, 2), lane_wrote=it.get("lane_wrote"), subject=it.get("subject"),
                        notes_in_crop=it.get("with") or [], notes_missing_box=missing, crop_origin=[x0, y0], crop_size=[x1 - x0, y1 - y0]))
    cols = 3
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * 768 + 8, ((len(tiles) + cols - 1) // cols) * (h + 30) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for n, t in enumerate(tiles):
        x, y = 8 + (n % cols) * 768, 8 + (n // cols) * (h + 30)
        d.text((x, y + 2), "%d" % (n + 1), fill=(0, 0, 0))
        sheet.paste(t, (x, y + 18))
    sheet.save(out / "sheet.png")
    (out / "README.md").write_text(
        "# 2.254 round 3 tiles\n\nEach picture is one staff of a scanned page with ONE thin orange box and nothing else drawn. The box "
        "only says where to look.\n\n**Question, for every tile:** what is the mark in the box? If it is a hairpin, on which note does "
        "it start and on which note does it stop; if it is a note, what is its value; if it is a word, what does it say.\n\nAnswer by "
        "tile number.\n")
    (out.parent / (out.name + "-key.json")).write_text(json.dumps(key, indent=1, default=str))
    print("tiles", len(key), {k: sum(x["role"] == k for x in key) for k in sorted({x["role"] for x in key})})


if __name__ == "__main__":
    main(*sys.argv[1:4])
