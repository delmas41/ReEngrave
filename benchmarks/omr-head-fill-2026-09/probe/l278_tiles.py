"""ROADMAP 2.78 Phase 1 -- BLIND tiles for Sean: one stem (with every mark on it)
per tile.

PATH: STAGED, GATHER + ADJUDICATE records only. Each tile is the printed page at
the gather's own DPI (the SAME deskewed raster the record's boxes live in --
`preprocessing.render_page(...).rgb`, so the bracket lands on the subject, not
near it), x2, red corner brackets on the stem and its heads, and NOTHING else
drawn: no reading, no colour coding, no label of ours. The question is neutral.
`manifest.json` holds what the tree read (per head) and the cause bucket; it is
NOT shown to the judge. Tile order is SHUFFLED (fixed seed) so the order does
not say which cause a tile is.

FRAME CONTROL (a control that can fail, CLAUDE.md rule 7): before a page is cut,
`readout.frame_control` must be > 0 on the render, and must go non-positive on
the same render shifted half a staff space -- else the script stops.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_tiles.py \
        --record lit=LIT.record.json --pop lit=LIT.pop.json \
        --record brahms=B.record.json --pop brahms=B.pop.json \
        --select selection.json --out out/print/2.78-review

`selection.json`: [{"doc": "lit", "stem": "obs:000123", "note": "why picked"}]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

TITLES = {"lit": "Beethoven 5 (Litolff)", "brahms": "Brahms 1 (Breitkopf)"}


def _title(doc):
    """`lit_B` -> the document title: the tag after `_` only keeps records of one document apart."""
    return TITLES.get(doc, TITLES.get(doc.split("_")[0], doc))
QUESTION = ("What note value is printed on this stem, and is every mark on it "
            "a notehead?")
HALF_W, HALF_H = 260, 190        # window half-size at 600 dpi, as 2.71's tiles
Z = 2


def main(argv=None):
    sys.path.insert(0, os.getcwd())
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from tools.omr.staged import readout
    from tools.omr.preprocessing import render_page

    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="append", default=[])
    ap.add_argument("--pop", action="append", default=[])
    ap.add_argument("--select", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=278)
    a = ap.parse_args(argv)
    recs = dict(r.split("=", 1) for r in a.record)
    pops = dict(p.split("=", 1) for p in a.pop)
    runs = {k: readout.load_run(v) for k, v in recs.items()}
    pop = {}
    for k, v in pops.items():
        blob = json.load(open(v))
        (label, body), = [(kk, vv) for kk, vv in blob.items()
                          if isinstance(vv, dict) and "groups" in vv]
        # a stem row id is unique per record; two pools of one document are merged
        pop.setdefault(k, {}).update({g["stem"]: g for g in body["groups"]})
    sel = json.load(open(a.select))
    random.Random(a.seed).shuffle(sel)
    os.makedirs(a.out, exist_ok=True)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)

    renders = {}
    frame = {}

    def page_rgb(doc, page):
        k = (doc, page)
        if k not in renders:
            run = runs[doc]
            pi = render_page(run.pdf, page, dpi=run.dpi)
            renders[k] = (pi.rgb, pi.skew_correction_deg)
            fc = readout.frame_control(pi.rgb, run, page)
            # staff space from the first staff of the page, for the shifted case
            sp = None
            for key in run.by_subject:
                if key.startswith(f"staff/{page}/"):
                    lines = run.obs_at(key, "staff_lines")
                    if lines:
                        ys = [float(y) for y in lines[0]["value"]]
                        if len(ys) > 1:
                            sp = (ys[-1] - ys[0]) / (len(ys) - 1)
                            break
            shifted = None
            if sp:
                shifted = readout.frame_control(
                    np.roll(pi.rgb, int(round(sp / 2.0)), axis=0), run, page)
            frame[k] = {"page": page, "frame_control": fc,
                        "shifted_half_space": shifted,
                        "skew_correction_deg": pi.skew_correction_deg}
            ok = fc is not None and fc > 0 and (shifted is None or shifted <= 0
                                                or shifted < fc)
            print(f"frame control {doc} p{page}: on-line {fc} ; same page "
                  f"shifted half a space {shifted} ; skew {pi.skew_correction_deg}")
            if not ok or fc <= 0:
                raise SystemExit(f"FRAME CONTROL FAILED for {doc} page {page}: "
                                 "the record's boxes do not sit on the print")
        return renders[k][0]

    manifest = []
    for n, s in enumerate(sel, 1):
        doc, sid = s["doc"], s["stem"]
        g = pop[doc][sid]
        run = runs[doc]
        dpi = run.dpi
        rgb = page_rgb(doc, g["page"])
        boxes = [h["box_page"] for h in g["heads"] if h["box_page"]]
        if g.get("stem_box_page"):
            boxes.append(g["stem_box_page"])
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[2] for b in boxes)
        y1 = max(b[3] for b in boxes)
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        k = dpi / 600.0
        hw = max(HALF_W * k, (x1 - x0) / 2.0 + 90 * k)
        hh = max(HALF_H * k, (y1 - y0) / 2.0 + 90 * k)
        cx0, cy0 = int(round(cx - hw)), int(round(cy - hh))
        cx1, cy1 = int(round(cx + hw)), int(round(cy + hh))
        H, W = rgb.shape[:2]
        canvas = np.full((cy1 - cy0, cx1 - cx0, 3), 255, dtype=np.uint8)
        sx0, sy0 = max(cx0, 0), max(cy0, 0)
        sx1, sy1 = min(cx1, W), min(cy1, H)
        canvas[sy0 - cy0:sy1 - cy0, sx0 - cx0:sx1 - cx0] = rgb[sy0:sy1, sx0:sx1]
        im = Image.fromarray(canvas).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        a_, b_, c_, e_ = ((x0 - cx0) * Z - 12, (y0 - cy0) * Z - 12,
                          (x1 - cx0) * Z + 12, (y1 - cy0) * Z + 12)
        d = ImageDraw.Draw(im)
        for (px, py, sx, sy) in ((a_, b_, 1, 1), (c_, b_, -1, 1),
                                 (a_, e_, 1, -1), (c_, e_, -1, -1)):
            d.line([(px, py), (px + sx * 22, py)], fill=(220, 0, 0), width=5)
            d.line([(px, py), (px, py + sy * 22)], fill=(220, 0, 0), width=5)
        out = Image.new("RGB", (im.width, im.height + 60), "white")
        out.paste(im, (0, 60))
        ImageDraw.Draw(out).text(
            (10, 12), f"Tile {n} of {len(sel)} -- {_title(doc)}",
            fill="black", font=font)
        fn = f"tile_{n:02d}.png"
        out.save(os.path.join(a.out, fn))
        manifest.append({
            "n": n, "file": fn, "pdf_page_index": g["page"],
            "page_box_600dpi": [int(round(x0)), int(round(y0)),
                                int(round(x1)), int(round(y1))],
            "subject": [h["key"] for h in g["heads"]],
            "stem_row": sid,
            "question": QUESTION,
            # ---- ours: never shown to the judge ----
            "cause": g["primary"], "cause_sub": g["sub"],
            "picked_because": s.get("note"),
            "read_ours": [{"head": h["key"], "class": h["cls"],
                           "outcome": h["outcome"], "reason": h["reason"],
                           "values": h["vals"],
                           # ROADMAP 2.78 Phase 2: the stem's value as it now applies to this head
                           **({"stem_value_after": h["after"]} if h.get("after") else {})}
                          for h in g["heads"]],
            "slash_rows_on_stem": g.get("slash_rows_on_stem"),
        })
    json.dump({"dpi": dpi, "note": ("tiles cut from the gather's own deskewed "
                                    "raster; the bracket is the union of the "
                                    "stem box and its heads' boxes; ours is "
                                    "never shown to the judge"),
               "frame_control": list(frame.values()),
               "tiles": manifest},
              open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print("ok", len(manifest), "->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
