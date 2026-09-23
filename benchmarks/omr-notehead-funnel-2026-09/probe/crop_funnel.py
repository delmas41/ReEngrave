"""ONE print crop of the staff the funnel is about, with the funnel drawn on it.

Sean asked where the Viola's notes went. The table says *the detector boxed
48 heads and the exporter wrote none of them*; this picture is how he checks
that sentence against the plate with his own eyes:

  * the staff the record FILED the heads on is named, and its five recorded
    `Q.STAFF_LINES` are traced across the crop in GREEN
    (`omr-infer-duration-print-2026-09`'s lesson: a crop that shows two
    staves and commits to neither is not evidence);
  * every DETECTOR notehead box is drawn RED -- so a head with no red box is
    a head the detector never found;
  * every head the exporter WROTE is drawn GREEN over the red -- so a red box
    with no green is a head that was found and then refused;
  * the cell (bar) boundaries the record read are drawn as faint vertical
    rules with the printed bar number, so a bar can be pointed at;
  * a staff-space ruler runs down the left edge.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL. The record's boxes are filed against
a raster at the gather's own DPI (600 here, from the record's own
`provenance.settings.args.dpi`). If the page this script renders is not that
raster, nothing drawn on it is evidence. The control is
`crop_inferred._frame_ok`, REUSED rather than restated: the staff's own five
lines must be materially darker than a half-space off them. A page that fails
is REFUSED, not cropped with a caveat.

    python3 benchmarks/omr-notehead-funnel-2026-09/probe/crop_funnel.py \
        --funnel <scratchpad>/funnel.json --pdf <edition.pdf> \
        --first-cell 0 --last-cell 7 --out-dir benchmarks/omr-notehead-funnel-2026-09/out/print
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402

# ⚠️ THE FRAME CONTROL IS IMPORTED, NOT COPIED. Same reason the refusal
# buckets are instrumented rather than restated in `funnel.py`.
_spec = importlib.util.spec_from_file_location(
    "crop_inferred",
    ROOT / "benchmarks/omr-infer-duration-print-2026-09/probe/crop_inferred.py")
_ci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ci)
_frame_ok = _ci._frame_ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--funnel", required=True, help="funnel.py --out-json")
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--first-cell", type=int, default=0)
    ap.add_argument("--last-cell", type=int, default=7)
    ap.add_argument("--first-printed-bar", type=int, default=49)
    ap.add_argument("--staff-name", default="Viola")
    ap.add_argument("--zoom", type=int, default=4)
    ap.add_argument("--out-dir", default="benchmarks/omr-notehead-funnel-2026-09/out/print")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    F = json.loads(Path(a.funnel).read_text())
    dpi = int(F["provenance"]["settings"]["args"]["dpi"])
    st_key = F["subject_staff"]                  # staff/P/S/T
    _, P, S, T = st_key.split("/")
    P, S, T = int(P), int(S), int(T)

    d = load_record(a.record)
    idx = {}
    for o in d["record"]["observations"]:
        if o["quantity"] in ("staff_lines", "staff_spacing", "cell_box"):
            idx[(o["quantity"], o["subject"])] = o["value"]

    lines = idx[("staff_lines", st_key)]
    spacing = float(idx[("staff_spacing", st_key)])
    cells = {c: idx.get(("cell_box", f"cell/{P}/{S}/{T}/{c}"))
             for c in range(a.first_cell, a.last_cell + 1)}
    if any(v is None for v in cells.values()):
        raise SystemExit(f"no cell_box for some of {sorted(cells)}")

    doc = fitz.open(a.pdf)
    pm = doc[P].get_pixmap(dpi=dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples) if pm.n >= 3
          else Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))
    arr = np.asarray(im.convert("L"), dtype=float)
    ok, contrast = _frame_ok(arr, lines, spacing)
    print(f"raster {im.width}x{im.height} @ {dpi}dpi   frame contrast {contrast:.2f}")
    if not ok:
        raise SystemExit("FRAME CONTROL FAILED — this render is not the "
                         "record's raster; nothing drawn on it is evidence")

    x0 = min(c[0] for c in cells.values())
    x1 = max(c[2] for c in cells.values())
    pad_x, pad_y = spacing * 3, spacing * 7
    cx0 = int(max(0, x0 - pad_x))
    cx1 = int(min(im.width, x1 + pad_x))
    cy0 = int(max(0, lines[0] - pad_y))
    cy1 = int(min(im.height, lines[-1] + pad_y))
    Z = a.zoom
    crop = im.crop((cx0, cy0, cx1, cy1)).resize(
        ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
    dr = ImageDraw.Draw(crop)

    def X(x): return (x - cx0) * Z
    def Y(y): return (y - cy0) * Z

    GREEN, RED, BLUE, GREY = (0, 150, 60), (215, 0, 0), (0, 90, 200), (150, 150, 150)

    # the staff the heads are FILED on
    for ly in lines:
        dr.line([(0, Y(ly)), (crop.width, Y(ly))], fill=GREEN, width=1)

    # the bars, as the record partitioned them
    for c, box in sorted(cells.items()):
        for bx in (box[0], box[2]):
            dr.line([(X(bx), 0), (X(bx), crop.height)], fill=GREY, width=1)
        dr.text((X(box[0]) + 4, 4), str(a.first_printed_bar + c), fill=GREY)

    # a staff-space ruler
    y, k = lines[0], 0
    while Y(y) < crop.height:
        if Y(y) >= 0:
            dr.line([(2, Y(y)), (14 if k % 5 else 22, Y(y))], fill=BLUE, width=1)
        y += spacing
        k += 1

    n_box = n_written = 0
    for sub, g in sorted(F["subject_glyphs"].items()):
        if not (a.first_cell <= g["cell"] <= a.last_cell):
            continue
        b = g["page_box_corners"]
        if not b:
            continue
        n_box += 1
        dr.rectangle([X(b[0]), Y(b[1]), X(b[2]), Y(b[3])], outline=RED, width=2)
        if g["written"]:
            n_written += 1
            dr.rectangle([X(b[0]) - 2, Y(b[1]) - 2, X(b[2]) + 2, Y(b[3]) + 2],
                         outline=GREEN, width=2)

    refused = {}
    for sub, g in F["subject_glyphs"].items():
        if a.first_cell <= g["cell"] <= a.last_cell:
            for r in g["refused"]:
                refused[r] = refused.get(r, 0) + 1

    band = 76
    out = Image.new("RGB", (crop.width, crop.height + band), "white")
    out.paste(crop, (0, band))
    cd = ImageDraw.Draw(out)
    cd.text((6, 4), f"{st_key}  =  {a.staff_name}, page {P} system {S+1}, "
                    f"printed bars {a.first_printed_bar + a.first_cell}"
                    f"-{a.first_printed_bar + a.last_cell}"
                    f"   (frame control passed, contrast {contrast:.1f})",
            fill=(0, 0, 0))
    cd.text((6, 20), "GREEN horizontal lines  =  the five Q.STAFF_LINES this "
                     "staff is filed on.    GREY verticals  =  the bars "
                     "the record read, numbered as PRINTED.", fill=GREEN)
    cd.text((6, 36), f"RED box  =  a detector notehead box  ({n_box} here).    "
                     f"GREEN box  =  a head the exporter WROTE  ({n_written} here).",
            fill=RED)
    cd.text((6, 52), "refused: " + (", ".join(f"{k} x{v}" for k, v in
                                              sorted(refused.items())) or "none"),
            fill=(120, 0, 0))

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (f"litolff-p{P}-s{S}-st{T}-{a.staff_name.lower()}-bars"
            f"{a.first_printed_bar + a.first_cell}-"
            f"{a.first_printed_bar + a.last_cell}.png")
    out.save(out_dir / name)
    (out_dir / (name.replace(".png", ".json"))).write_text(json.dumps({
        "staff": st_key, "staff_name": a.staff_name, "pdf": a.pdf, "dpi": dpi,
        "frame_contrast": round(contrast, 2), "crop_page_px": [cx0, cy0, cx1, cy1],
        "zoom": Z, "detector_notehead_boxes": n_box, "written": n_written,
        "refused": refused,
    }, indent=2))
    print(f"wrote {out_dir / name}   boxes={n_box} written={n_written} "
          f"refused={refused}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
