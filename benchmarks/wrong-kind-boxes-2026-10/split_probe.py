"""ROADMAP 2.245 round 3 -- run `box_kind.split_wide_heads` OFFLINE on real cells (the master cell map) for named wide head boxes, and
draw what it finds. The fast loop for the head-shape rules: no re-gather. Boxes come from the 20261029-night slices (detector indices
are the same under the master cell map). Usage:
  python3 benchmarks/wrong-kind-boxes-2026-10/split_probe.py OUT_DIR plate:glyph/... [plate:glyph/... ...]
Writes OUT_DIR/probe.png (one panel per box: the cell crop, the wide box orange, each found head green, each vetoed blob red) and
prints the split info.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import look  # noqa: E402
from tools.omr.staged import box_kind as BK  # noqa: E402
from tools.omr.staged import cell_map as CM  # noqa: E402

SL = look.SL


def rows_for(plate, g):
    cell = "cell/" + "/".join(g.split("/")[1:5])
    out = subprocess.run(["grep", "-F", '"subject": "%s"' % g, str(SL / plate / "observations.jsonl")], capture_output=True, text=True).stdout
    box = next(json.loads(l) for l in out.splitlines() if '"glyph_box"' in l)
    out = subprocess.run(["grep", "-F", '"subject": "%s"' % cell, str(SL / plate / "observations.jsonl")], capture_output=True, text=True).stdout
    cb = next(json.loads(l) for l in out.splitlines() if '"cell_box"' in l)
    # every detector box of the cell (the narrow heads and clefs the split reads)
    pre = '"subject": "glyph/%s/' % "/".join(g.split("/")[1:5])
    out = subprocess.run(["grep", "-F", pre, str(SL / plate / "observations.jsonl")], capture_output=True, text=True).stdout
    dets = [json.loads(l) for l in out.splitlines() if '"quantity": "glyph_box"' in l]
    return box, cb, dets


@dataclasses.dataclass
class _D:
    smufl_name: str
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 0.3


def D(v):
    return _D(v[0], int(v[1]), int(v[2]), int(v[3]), int(v[4]))


def main(out_dir, specs):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    panels = []
    for spec in specs:
        plate, g = spec.split(":")
        page = int(g.split("/")[1])
        box, cb, dets = rows_for(plate, g)
        (pws, cells), = CM.load_prepared(look.pdf_of(plate), [page])
        c = min(cells, key=lambda c: sum(abs(a - b) for a, b in zip(c.bbox_page_px, cb["value"])))
        lines = list(c.staff_line_ys_canonical)
        sp = (lines[-1] - lines[0]) / (len(lines) - 1)
        ds = [D(d["value"]) for d in sorted(dets, key=lambda d: int(d["subject"].split("/")[-1]))]
        idx = int(g.split("/")[-1])
        order = [int(d["subject"].split("/")[-1]) for d in sorted(dets, key=lambda d: int(d["subject"].split("/")[-1]))]
        res, info = BK.split_wide_heads(ds, c.image_no_staff, sp, staff_top=lines[0])
        me = info.get(order.index(idx), {})
        print(spec, "sp=%.1f" % sp, json.dumps(me))
        img = Image.fromarray(np.asarray(c.image_no_staff)).convert("RGB")
        d = ImageDraw.Draw(img)
        v = box["value"]
        d.rectangle([v[1], v[2], v[1] + v[3], v[2] + v[4]], outline=(255, 120, 0), width=4)
        for k in (me.get("box_kind") or {}).get("added", []):
            a = res[k]
            d.rectangle([a.x_canonical, a.y_canonical, a.x_canonical + a.width_canonical, a.y_canonical + a.height_canonical],
                        outline=(0, 170, 0), width=4)
        for vb in (me.get("box_kind") or {}).get("vetoed", []):
            d.rectangle([vb[0], vb[1], vb[0] + vb[2], vb[1] + vb[3]], outline=(220, 0, 0), width=3)
        x0, y0 = max(0, v[1] - 300), max(0, v[2] - 400)
        crop = img.crop((x0, y0, min(img.width, v[1] + v[3] + 300), min(img.height, v[2] + v[4] + 400)))
        crop.thumbnail((360, 360))
        panels.append((spec, crop))
    W = Image.new("RGB", (370 * min(4, len(panels)), 380 * ((len(panels) + 3) // 4)), "white")
    dr = ImageDraw.Draw(W)
    for i, (spec, p) in enumerate(panels):
        x, y = (i % 4) * 370, (i // 4) * 380
        W.paste(p, (x, y + 14))
        dr.text((x, y), spec[-26:], fill=(0, 0, 0))
    W.save(out / "probe.png")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
