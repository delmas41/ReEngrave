"""ROADMAP 2.12f -- the BLIND review tiles for Sean.

    python3 benchmarks/omr-shape-role-2026-09/cut_artic_tiles.py \
        <selection.json> --out out/print/2.12f-review

`selection.json` is a list of dicts (n, doc, pdf, page, subject, mark_bbox_page,
read_before, read_after, category). Each tile is a crop of the PDF page cut at
the gather's own 600 dpi in the gather's own pixel frame
(`benchmarks/omr-local-staff-2026-09/frame.render_page_matching_gather`), with a
red CORNER BRACKET on the exact mark and NOTHING of ours drawn -- no head box,
no colour, no staff name, no verdict. The question is neutral and the same for
every tile, so a tile cannot say what we read. `manifest.json` carries
`read_before` / `read_after`, which Sean never sees.

THE FRAME CONTROL THAT CAN FAIL (CLAUDE.md Sec.6b): the ink inside the mark's
own box must be at least FRAME_RATIO_MIN times the mean ink of the eight boxes
around it AND its centroid must sit at the box centre (FRAME_CENTROID_MAX). The
same test is run on the box shifted (40, 40) px, which MUST fail on most tiles
-- a control that passes whatever it is shown is not one. (Two earlier drafts
could not tell the frame from a wrong one -- 7 of 12 real vs 5 of 12 shifted,
then 12 vs 7 -- on notation this dense, and were replaced.)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-local-staff-2026-09"))

import cv2                                   # noqa: E402
import numpy as np                           # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402

DPI = 600
QUESTION = ("Which note does the mark in the brackets belong to, and is it "
            "above or below that note?")
RED = (200, 0, 0)
FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
FONT_S = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
DOCNAME = {"brahms": "Brahms 1 (Breitkopf)", "litolff": "Beethoven 5 (Litolff)"}


def _ink(binary, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    h, w = binary.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float((binary[y0:y1, x0:x1] == 0).mean())


#: A detector box is TIGHT on a small dark glyph, so (a) the ink inside it is
#: concentrated -- at least FRAME_RATIO_MIN times the mean ink of the eight boxes
#: around it -- and (b) the ink's centroid sits near the box centre, within
#: FRAME_CENTROID_MAX of the box's own size on each axis.
FRAME_RATIO_MIN = 1.5
FRAME_CENTROID_MAX = 0.3


def frame_control(binary, box, shift=(0, 0)):
    """`(ratio, centroid_offset, passes)` for `box` displaced by `shift` px."""
    dx0, dy0 = shift
    x0, y0, x1, y1 = box[0] + dx0, box[1] + dy0, box[2] + dx0, box[3] + dy0
    w, h = x1 - x0, y1 - y0
    here = _ink(binary, (x0, y0, x1, y1))
    ring = [_ink(binary, (x0 + dx * w, y0 + dy * h, x1 + dx * w, y1 + dy * h))
            for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]
    around = sum(ring) / len(ring)
    ratio = (here / around) if around > 1e-9 else float("inf")
    bx0, by0, bx1, by1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    sub = binary[max(0, by0):by1, max(0, bx0):bx1] == 0
    if not sub.any():
        return ratio, (1.0, 1.0), False
    ys, xs = np.nonzero(sub)
    off = (abs(xs.mean() + 0.5 - sub.shape[1] / 2.0) / max(1, sub.shape[1]),
           abs(ys.mean() + 0.5 - sub.shape[0] / 2.0) / max(1, sub.shape[0]))
    ok = (ratio >= FRAME_RATIO_MIN and off[0] <= FRAME_CENTROID_MAX
          and off[1] <= FRAME_CENTROID_MAX)
    return ratio, off, ok


def bracket(img, box, pad, arm, thick):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                             (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(img, (cx, cy), (cx + sx * arm, cy), RED[::-1], thick)
        cv2.line(img, (cx, cy), (cx, cy + sy * arm), RED[::-1], thick)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sel = json.load(open(a.selection))
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = {}
    manifest = {"dpi": DPI, "tiles": []}
    ctl = {"real_pass": 0, "shifted_pass": 0, "n": 0}
    total = len(sel)
    for t in sel:
        key = (t["pdf"], t["page"])
        if key not in cache:
            pg = render_page_matching_gather(t["pdf"], t["page"], DPI)
            cache[key] = (cv2.cvtColor(pg.rgb, cv2.COLOR_RGB2BGR), pg.binary)
        rgb, binary = cache[key]
        mb = [float(v) for v in t["mark_bbox_page"]]
        ratio, off, ok = frame_control(binary, mb)
        _r2, _o2, ok_shift = frame_control(binary, mb, shift=(40, 40))
        ctl["n"] += 1
        ctl["real_pass"] += int(ok)
        ctl["shifted_pass"] += int(ok_shift)
        # a staff space ~ 2.2 x a tenuto/accent box height on these scans; the
        # window is sized from the doc, not from the mark, so tiles are alike
        space = 25.0 if t["doc"] == "brahms" else 15.5
        hw, hh = int(15 * space), int(9 * space)
        cx, cy = (mb[0] + mb[2]) / 2.0, (mb[1] + mb[3]) / 2.0
        x0, x1 = int(cx - hw), int(cx + hw)
        y0, y1 = int(cy - hh), int(cy + hh)
        H, W = rgb.shape[:2]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        crop = rgb[y0:y1, x0:x1].copy()
        sc = 1040.0 / crop.shape[1]
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        box_c = [(mb[0] - x0) * sc, (mb[1] - y0) * sc,
                 (mb[2] - x0) * sc, (mb[3] - y0) * sc]
        bracket(crop, box_c, pad=int(0.45 * space * sc), arm=int(0.7 * space * sc),
                thick=3)
        head_h, foot_h = 56, 96
        img = Image.new("RGB", (crop.shape[1], crop.shape[0] + head_h + foot_h),
                        (255, 255, 255))
        img.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)),
                  (0, head_h))
        dr = ImageDraw.Draw(img)
        dr.text((10, 10), "Tile %d of %d -- %s" % (t["n"], total,
                                                   DOCNAME[t["doc"]]),
                font=FONT, fill=(0, 0, 0))
        dr.text((10, head_h + crop.shape[0] + 12), QUESTION, font=FONT_S,
                fill=(0, 0, 0))
        fn = "tile_%02d.png" % t["n"]
        img.save(out / fn)
        manifest["tiles"].append({
            "n": t["n"], "file": fn, "pdf_page_index": t["page"],
            "page_box_600dpi": [int(round(v)) for v in mb],
            "subject": t["subject"], "question": QUESTION,
            "read_before": t["read_before"], "read_after": t["read_after"],
            "category": t.get("category"),
            "frame_control": {"ink_ratio": round(ratio, 2),
                              "centroid_offset": [round(off[0], 2),
                                                  round(off[1], 2)],
                              "passes": bool(ok)}})
        print(fn, t["doc"], t["subject"], "ratio %.2f centroid %s pass=%s | "
              "shifted (40,40) pass=%s" % (ratio, [round(o, 2) for o in off],
                                           ok, ok_shift))
    manifest["frame_control"] = {
        "tiles": ctl["n"],
        "ratio_threshold": FRAME_RATIO_MIN,
        "centroid_offset_max": FRAME_CENTROID_MAX,
        "real_box_passes": ctl["real_pass"],
        "SHIFTED_(40,40)px_box_passes(control, must be low)":
            ctl["shifted_pass"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest["frame_control"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
