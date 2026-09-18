"""CROP THE PRINT for every head in the pre-registered sample — BLIND.

⚠️⚠️ IT OPENS WITH A FRAME CONTROL THAT CAN FAIL, for the reason
`omr-second-publisher-pricing-2026-09/probe/whole_rest_crops.py` gives: a crop
is evidence only if the rendered page is the frame `bbox_page_px` is filed in,
and a wrong DPI or rasteriser moves every box by the same amount so the result
LOOKS like a reading fault. Each page's `Q.STAFF_LINES` rows are checked
against the ink under them -- a staff line is a long dark run, so the claimed
row must be materially darker than a row a half space off it. Default ABORTS.

⚠️ 600 dpi is not a choice made here: it is the staged gather's own default,
and for Litolff it is EXACTLY the embedded raster's native resolution
(2897x3813 on a 347.64pt page = 600.1 dpi), so nothing is upsampled. For
Breitkopf the native raster is 5248x6905 on 711.59pt = 531 dpi, so a 600-dpi
render upsamples 1.13x and buys no detail -- recorded, not corrected, because
changing the dpi would invalidate every box.

⚠️⚠️ NOTHING IS DRAWN OVER THE INK. The question is whether a thin stroke
touches a notehead, and the precedent's 3px red box outline sits exactly where
a stem attaches -- it would hide the evidence it was drawn to point at. So the
subject head is placed at the CENTRE of its tile by construction and marked
only by ticks in the tile's outer margins: staff-line stubs (blue) at the left
and right edges, and a red crosshair tick on all four edges. No annotation is
within the music.

⚠️⚠️ BLIND. Tiles carry an opaque id only. The bucket, the notehead class and
whether a head is a POSITIVE CONTROL are held in `--manifest` and are not on
the image -- knowing a head is in `too WIDE` is knowing to expect a stem, and
knowing one is a control is knowing a stroke is there. Controls are shuffled
in among the sample by the same seed.

    python3 probe/crop_stems.py --sample SAMPLE.json --rows out/X-rows.json \
        --decided out/X-decided.json --label-prefix L --which 0 \
        --out-dir out/print --manifest out/crop-manifest-litolff.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

SEED = 20260918
PAD_X_SPACES = 2.2      # enough to see which SIDE a stroke stands on
PAD_Y_SPACES = 5.0      # a stem is ~3.5 spaces, a stem+flag ~4.5
# WARNING 100 px per staff space is not cosmetic. Litolff's plate carries
# 15.5 px per space at its NATIVE 600 dpi, so ONE SOURCE PIXEL is 0.065 of a
# space and a stem is 2-3 px wide. At 72 px/space a stem renders 10-14 px and
# fused regions were not adjudicable; at 100 the source pixel grid itself is
# visible, which is the honest limit of what this plate can be asked.
PX_PER_SPACE = 100.0
MARGIN_FRAC = 0.09      # the outer band the only annotation lives in


def _page_image(pdf, page, dpi):
    from tools.omr.preprocessing import render_page
    pi = render_page(pdf, page, dpi=dpi)
    # ⚠️⚠️ `rgb` first, and on THESE TWO PLATES IT MAKES NO DIFFERENCE, which
    # is itself the finding. The precedent asks for `rgb` so a human sees the
    # grey the binariser threw away -- but both embedded rasters are `bpc: 1`,
    # GENUINELY BITONAL, and `render_page`'s `rgb`, its `binary` and a direct
    # `fitz` grey render all come back with exactly TWO distinct values. There
    # is no grey to recover, so a fused blob in a tile is fused ON THE PLATE
    # and not by our binarisation. Kept in this order anyway: a third plate
    # may be 8-bit and then the order matters.
    for attr in ("rgb", "binary"):
        arr = getattr(pi, attr, None)
        if arr is not None:
            return arr
    raise SystemExit("render_page gave no image array -- schema changed")


def _frame_ok(arr, line_ys, spacing, *, margin):
    import numpy as np
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = max(1, int(round(spacing / 2.0)))
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    return (float(sum(off) / len(off) - sum(on) / len(on)) >= margin,
            float(sum(off) / len(off) - sum(on) / len(on)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--decided", required=True)
    ap.add_argument("--which", type=int, required=True,
                    help="index into SAMPLE.json['publishers']")
    ap.add_argument("--label-prefix", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--per-sheet", type=int, default=3)
    ap.add_argument("--ids", nargs="*", default=None,
                    help="ZOOM MODE: only these tile ids, tighter and bigger. "
                         "The ids are stable because the blinding shuffle is "
                         "seeded, so a hard tile can be re-asked without "
                         "re-drawing the sample or learning what it is.")
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--frame-margin", type=float, default=8.0)
    ap.add_argument("--no-require-frame", action="store_true")
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw

    sample = json.loads(Path(a.sample).read_text())
    pub = sample["publishers"][a.which]
    rows = {r["subject"]: r for r in json.loads(Path(a.rows).read_text())["rows"]}
    dec = {r["subject"]: r
           for r in json.loads(Path(a.decided).read_text())["rows"]}
    pdf = pub["pdf"]
    if not Path(pdf).is_file():
        print(f"NO PDF AT {pdf} — this probe renders the page the record was "
              "gathered from and cannot substitute anything for it.",
              file=sys.stderr)
        return 2
    print(f"{pub['label']}\npdf  {pdf}\ndpi  {a.dpi}")

    todo = []
    for bucket, st in pub["strata"].items():
        for s in st["subjects"]:
            todo.append({"subject": s, "kind": "sample", "bucket": bucket,
                         "row": rows[s]})
    for s, read in pub["positive_control"]["subjects"]:
        todo.append({"subject": s, "kind": "control", "bucket": "CONTROL",
                     "read_direction": read, "row": dec[s]})
    print(f"reach: {len(todo)} crops "
          f"({sum(1 for t in todo if t['kind']=='sample')} sample, "
          f"{sum(1 for t in todo if t['kind']=='control')} control)")
    if not todo:
        print("DEAD: nothing to crop", file=sys.stderr)
        return 2

    # ── BLIND: shuffle, then number. The id encodes nothing. ──────────────
    random.Random(f"{SEED}:crops:{pub['label']}").shuffle(todo)
    for i, t in enumerate(todo, 1):
        t["id"] = f"{a.label_prefix}{i:03d}"
    if a.ids:
        want = set(a.ids)
        todo = [t for t in todo if t["id"] in want]
        print(f"ZOOM: {len(todo)} of {len(want)} requested ids found")
        if not todo:
            print("DEAD: none of those ids exist", file=sys.stderr)
            return 2

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pages = {}
    frame_report = []
    for pg in sorted({t["row"]["where"]["page"] for t in todo}):
        arr = np.asarray(_page_image(pdf, pg, a.dpi))
        any_row = next(t["row"] for t in todo if t["row"]["where"]["page"] == pg)
        ok, contrast = _frame_ok(arr, any_row["staff_lines"],
                                 any_row["staff_spacing"],
                                 margin=a.frame_margin)
        frame_report.append({"page": pg, "staff": any_row["staff_key"],
                             "ok": ok, "contrast": round(contrast, 2)})
        print(f"FRAME page {pg} via {any_row['staff_key']}: claimed staff rows "
              f"are {contrast:+.1f} grey levels darker than a half space off "
              f"-> {'OK' if ok else 'FAILED'}")
        if not ok and not a.no_require_frame:
            print("FRAME CONTROL FAILED: the render is not the frame the "
                  "boxes are filed in, so every crop would be of the wrong "
                  "place. Refusing to write crops that would be adjudicated.",
                  file=sys.stderr)
            return 2
        pages[pg] = Image.fromarray(arr).convert("RGB")

    tiles = []
    for t in todo:
        r = t["row"]
        sp = float(r["staff_spacing"])
        bb = r["bbox_page_px"]
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        px = (PAD_X_SPACES / a.zoom) * sp + (bb[2] - bb[0]) / 2
        py = (PAD_Y_SPACES / a.zoom) * sp
        x0, y0, x1, y1 = cx - px, cy - py, cx + px, cy + py
        crop = pages[r["where"]["page"]].crop(
            (int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))))
        scale = (PX_PER_SPACE * a.zoom) / sp
        w, h = max(1, int(round(crop.width * scale))), \
            max(1, int(round(crop.height * scale)))
        # NEAREST: honest on bitonal ink -- it invents no grey.
        crop = crop.resize((w, h), Image.NEAREST)
        d = ImageDraw.Draw(crop)
        mw = max(6, int(w * MARGIN_FRAC))
        X = lambda v: (v - x0) * scale          # noqa: E731
        Y = lambda v: (v - y0) * scale          # noqa: E731
        for ly in r["staff_lines"]:
            yy = Y(ly)
            if -2 <= yy <= h + 2:
                d.line([(0, yy), (mw, yy)], fill=(70, 140, 255), width=2)
                d.line([(w - mw, yy), (w, yy)], fill=(70, 140, 255), width=2)
        # the red crosshair, on the four EDGES only -- it touches no music
        hx, hy = X(cx), Y(cy)
        d.line([(0, hy), (mw * 0.55, hy)], fill=(230, 0, 0), width=3)
        d.line([(w - mw * 0.55, hy), (w, hy)], fill=(230, 0, 0), width=3)
        d.line([(hx, 0), (hx, mw * 0.55)], fill=(230, 0, 0), width=3)
        d.line([(hx, h - mw * 0.55), (hx, h)], fill=(230, 0, 0), width=3)
        # ⚠️ CORNER BRACKETS, never a box outline. The subject head must be
        # identifiable in dense music -- a crosshair on the tile edge says
        # WHERE but not HOW BIG, and on a fused plate that is the difference
        # between adjudicating this head and adjudicating its neighbour. But
        # a stem attaches at the MIDDLE of the box's left or right edge, so
        # only the corners may be drawn: each arm is a quarter of its side
        # and the mid-edge is left bare.
        g = 5
        bx0, by0 = X(bb[0]) - g, Y(bb[1]) - g
        bx1, by1 = X(bb[2]) + g, Y(bb[3]) + g
        ax, ay = (bx1 - bx0) * 0.28, (by1 - by0) * 0.28
        M = (255, 0, 220)
        for (px_, py_, sx, sy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                   (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            d.line([(px_, py_), (px_ + sx * ax, py_)], fill=M, width=3)
            d.line([(px_, py_), (px_, py_ + sy * ay)], fill=M, width=3)
        tiles.append((t["id"], crop))

    # ── sheets ────────────────────────────────────────────────────────────
    from PIL import ImageFont
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
    made = 0
    bar = 40
    for i in range(0, len(tiles), a.per_sheet):
        chunk = tiles[i:i + a.per_sheet]
        th = max(c.height for _, c in chunk)
        tw = max(c.width for _, c in chunk)
        gap = 18
        sheet = Image.new("RGB", (len(chunk) * (tw + gap) + gap,
                                  th + bar + gap * 2), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        for j, (tid, c) in enumerate(chunk):
            ox = gap + j * (tw + gap)
            sheet.paste(c, (ox + (tw - c.width) // 2, bar + gap))
            d.rectangle([ox - 2, bar + gap - 2, ox + tw + 1,
                         bar + gap + th + 1], outline=(40, 40, 40), width=2)
            d.text((ox + 6, 8), tid, fill=(0, 0, 0), font=font)
        tag = ("zoom-" + chunk[0][0]) if a.ids else f"{i // a.per_sheet + 1:02d}"
        name = f"sheet-{a.label_prefix}-{tag}.png"
        sheet.save(out / name)
        made += 1
    print(f"\n{len(tiles)} tiles -> {made} sheets in {out}")

    Path(a.manifest).write_text(json.dumps({
        "label": pub["label"], "pdf": pdf, "dpi": a.dpi,
        "frame_control": frame_report,
        "px_per_space": PX_PER_SPACE,
        "pad_x_spaces": PAD_X_SPACES, "pad_y_spaces": PAD_Y_SPACES,
        "crop_reach_note":
            "each tile spans %.1f staff spaces vertically (%.1f either side "
            "of the head centre) and %.1f horizontally plus the head's own "
            "width, so a stem of the usual 3.5 spaces is fully inside it and "
            "an absence in the tile IS an absence in that window"
            % (2 * PAD_Y_SPACES, PAD_Y_SPACES, 2 * PAD_X_SPACES),
        "tiles": [{"id": t["id"], "subject": t["subject"], "kind": t["kind"],
                   "bucket": t["bucket"],
                   "read_direction": t.get("read_direction"),
                   "cls": t["row"].get("cls"),
                   "width_cap_recovered": t["row"].get("width_cap_recovered"),
                   "staff_spacing": t["row"].get("staff_spacing"),
                   "where": t["row"]["where"]}
                  for t in todo],
    }, indent=1))
    print(f"wrote {a.manifest}")
    return 0 if made else 2


if __name__ == "__main__":
    raise SystemExit(main())
