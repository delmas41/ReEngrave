"""What the GATHER view draws, rendered from the SERVER'S OWN PAYLOAD.

⚠️ THIS IS NOT A SECOND VIEWER. It takes `/api/gather`'s JSON and
`/api/crop.png`'s raster from a RUNNING `tools.omr.staged.review.server` and
draws the overlays with the same arithmetic the page's JS uses --
`crop = (page - crop.page_px[0..1]) * crop.zoom` -- so what it proves is that
the payload the browser receives lands on the ink. A box drawn here in the
wrong place is a box the page would draw in the wrong place.

It exists because this session could not drive a browser at `127.0.0.1:5060`
(navigation denied in its environment), and *"I could not take a screenshot"*
and *"the overlays line up"* are different facts. This renders the second one
from the first one's data.

    python3 benchmarks/omr-stage-review-2026-09/probe/render_gather_overlay.py \\
        --staff staff/3/0/9 --out benchmarks/omr-stage-review-2026-09/out
"""
from __future__ import annotations

import argparse
import io
import json
import urllib.request
from pathlib import Path

FAMILY = {"notehead": (198, 40, 40), "rest": (21, 101, 192),
          "clef": (106, 27, 154), "key": (0, 131, 143),
          "accidental": (239, 108, 0), "other": (117, 117, 117)}
GREEN = (10, 143, 77)
GREY = (150, 150, 150)
WRITTEN = (27, 127, 59)


def main() -> int:
    from PIL import Image, ImageDraw

    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5060")
    ap.add_argument("--staff", default="staff/3/0/9")
    ap.add_argument("--out", default="benchmarks/omr-stage-review-2026-09/out")
    ap.add_argument("--first-cell", type=int, default=0)
    ap.add_argument("--last-cell", type=int, default=7)
    a = ap.parse_args()

    g = json.loads(urllib.request.urlopen(
        f"{a.base}/api/gather?staff={a.staff}").read())
    meta = json.loads(urllib.request.urlopen(
        f"{a.base}/api/crop_meta?staff={a.staff}").read())
    raw = urllib.request.urlopen(f"{a.base}/api/crop.png?staff={a.staff}").read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")

    c = g["crop"]
    ox, oy, z = c["page_px"][0], c["page_px"][1], c["zoom"]

    def X(v):
        return (v - ox) * z

    def Y(v):
        return (v - oy) * z

    # the window the page would be scrolled to
    cells = {int(cc["index"]): cc for cc in g["cells"]}
    xs = [cells[i]["box"] for i in range(a.first_cell, a.last_cell + 1)
          if i in cells]
    lo = X(min(b[0] for b in xs)) - 20
    hi = X(max(b[2] for b in xs)) + 20

    dr = ImageDraw.Draw(im)
    for y in g["staff_lines"]:
        dr.line([(0, Y(y)), (im.width, Y(y))], fill=GREEN, width=1)
    for cc in g["cells"]:
        for bx in (cc["box"][0], cc["box"][2]):
            dr.line([(X(bx), 0), (X(bx), im.height)], fill=GREY, width=1)
        dr.text((X(cc["box"][0]) + 5, 6), str(cc["bar"]), fill=GREY)
    for b in g["boxes"]:
        if not b["bbox_page_px"]:
            continue
        p = b["bbox_page_px"]
        dr.rectangle([X(p[0]), Y(p[1]), X(p[2]), Y(p[3])],
                     outline=FAMILY.get(b["family"], GREY), width=2)
        if b["written"]:
            dr.rectangle([X(p[0]) - 3, Y(p[1]) - 3, X(p[2]) + 3, Y(p[3]) + 3],
                         outline=WRITTEN, width=2)

    band = 66
    crop = im.crop((int(max(0, lo)), 0, int(min(im.width, hi)), im.height))
    out = Image.new("RGB", (crop.width, crop.height + band), "white")
    out.paste(crop, (0, band))
    cd = ImageDraw.Draw(out)
    ctl = meta["control"]
    counts = g["counts"]
    cd.text((6, 6), f"GATHER view, {a.staff} = {g['part_name']}, page "
                    f"{g['page']} system {g['system'] + 1}, bars "
                    f"{cells[a.first_cell]['bar']}-{cells[a.last_cell]['bar']} "
                    f"(file numbering)   frame control "
                    f"{'PASSED' if ctl.get('ok') else 'FAILED'}, contrast "
                    f"{ctl.get('contrast')}", fill=(0, 0, 0))
    cd.text((6, 22), "GREEN horizontals = Q.STAFF_LINES.  GREY verticals = "
                     "Q.CELL_BOX, numbered as the FILE numbers them.",
            fill=GREEN)
    cd.text((6, 38), "  ".join(f"{k}" for k in FAMILY), fill=(0, 0, 0))
    x = 6
    for k, col in FAMILY.items():
        cd.text((x, 52), k, fill=col)
        x += 8 * len(k) + 16
    cd.text((x, 52), f"| boxed {counts['heads_boxed']}  written "
                     f"{counts['heads_written']}  lost {counts['heads_lost']}",
            fill=(0, 0, 0))

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (f"gather-{a.staff.replace('/', '-')}-cells"
            f"{a.first_cell}-{a.last_cell}.png")
    out.save(out_dir / name)
    (out_dir / name.replace(".png", ".json")).write_text(json.dumps({
        "staff": a.staff, "crop": c, "frame_control": ctl,
        "counts": counts, "boxes_drawn": len(g["boxes"]),
        "source": "the running review server's own /api/gather payload",
    }, indent=1))
    print(f"wrote {out_dir / name}  ({out.width}x{out.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
