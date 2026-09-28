"""ROADMAP 2.12h -- crops of Brahms 1/i's opening-meter header window on
`system/1/0` (page 1, the first system of the second gathered page), for
Sean.

Self-contained (CLAUDE.md §5b/§13): reads the fresh whole-movement Brahms
record ONCE via `record_io.load_record` for geometry only (`cell_box`,
`staff_lines`, `staff_spacing`), renders the PDF page straight off disk (no
detector, no re-gather, no re-adjudication), crops cell 0 (which carries the
header -- clef/key/meter -- up to the first barline, the same frame
`Q.METER_GLYPH`'s cell-0 digit detections sit in) plus cell 1 for context,
draws the reading staff's OWN lines (never a neighbour's), and for contrast
also crops `system/0/0`'s last cell (7), which is the courtesy/cautionary
signature the record already reads as a corroborated 9/8 on 9 staves.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import numpy as np
    from PIL import Image, ImageDraw

    from tools.omr.preprocessing import render_page
    from tools.omr.staged import record_io

    record_path = ("/Users/seanjohnson/Desktop/ReEngrave/library/"
                   "_shared-records/"
                   "brahms1-breitkopf-mvt1-whole-20260928.record.json")
    pdf = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
           "symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-"
           "brahms--imslp317803.pdf")
    dpi = 600
    out_dir = HERE / "out" / "print" / "m212h-brahms1-breitkopf"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading {record_path} via record_io.load_record "
          f"(geometry only) ...", file=sys.stderr)
    data = record_io.load_record(record_path)
    rec = data.get("record", data)
    staff_lines: dict = {}
    staff_spacing: dict = {}
    cell_box: dict = {}
    for o in rec["observations"]:
        q = o.get("quantity")
        if q == "staff_lines":
            staff_lines[o["subject"]] = o["value"]
        elif q == "staff_spacing":
            staff_spacing[o["subject"]] = o["value"]
        elif q == "cell_box":
            cell_box[o["subject"]] = o["value"]
    print(f"geometry rows: {len(staff_lines)} staff_lines, "
          f"{len(staff_spacing)} staff_spacing, {len(cell_box)} cell_box",
          file=sys.stderr)
    del rec, data

    # (page, system, staff, cell, label)
    targets = [
        (1, 0, 1, 0, "sys1-0-opening-cell0-staff1"),
        (1, 0, 1, 1, "sys1-0-opening-cell1-staff1"),
        (1, 0, 4, 0, "sys1-0-opening-cell0-staff4"),
        (1, 0, 6, 0, "sys1-0-opening-cell0-staff6"),
        (1, 0, 8, 0, "sys1-0-opening-cell0-staff8"),
        (0, 0, 1, 7, "sys0-0-cautionary-cell7-staff1"),
    ]

    page_cache: dict = {}
    manifest = {"label": "brahms1-breitkopf", "pdf": pdf, "dpi": dpi,
                "tiles": []}

    for page, system, staff, cell, label in targets:
        staff_key = f"staff/{page}/{system}/{staff}"
        cell_key = f"cell/{page}/{system}/{staff}/{cell}"
        line_ys = staff_lines.get(staff_key)
        spacing = staff_spacing.get(staff_key) or 40.0
        box = cell_box.get(cell_key)
        if not box or not line_ys:
            print(f"  SKIP {cell_key}: missing geometry "
                  f"(cell_box={bool(box)} staff_lines={bool(line_ys)})",
                  file=sys.stderr)
            continue

        if page not in page_cache:
            print(f"rendering page {page} ...", file=sys.stderr)
            pi = render_page(pdf, page, dpi=dpi)
            arr = getattr(pi, "rgb", None)
            if arr is None:
                arr = getattr(pi, "binary")
            arr_np = np.asarray(arr)
            page_cache[page] = Image.fromarray(
                arr_np if arr_np.ndim == 3 else np.stack([arr_np] * 3, axis=-1))
        img = page_cache[page]

        px0, py0, px1, py1 = box
        cx0 = int(max(0, px0 - 1.0 * spacing))
        cx1 = int(min(img.width, px1 + 1.0 * spacing))
        cy0 = int(max(0, min(line_ys) - 3.5 * spacing))
        cy1 = int(min(img.height, max(line_ys) + 2.0 * spacing))

        crop = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
        UPSCALE = 4
        crop = crop.resize((crop.width * UPSCALE, crop.height * UPSCALE),
                            Image.NEAREST)
        draw = ImageDraw.Draw(crop)

        for ly in line_ys:
            y = (ly - cy0) * UPSCALE
            draw.line([(0, y), (crop.width, y)], fill=(70, 130, 220),
                       width=max(1, UPSCALE // 3))

        bx0, by0 = (px0 - cx0) * UPSCALE, (py0 - cy0) * UPSCALE
        bx1, by1 = (px1 - cx0) * UPSCALE, (py1 - cy0) * UPSCALE
        draw.rectangle([(bx0, by0), (bx1, by1)], outline=(220, 20, 20),
                       width=max(2, UPSCALE // 2))

        label_line = f"p{page} sys{system} staff{staff} cell{cell}  {label}"
        draw.rectangle([(2, 2), (crop.width - 2, 26)], fill=(255, 255, 255))
        draw.text((6, 4), label_line, fill=(0, 0, 0))

        fname = f"m212h-brahms1-breitkopf-{label}.png"
        crop.save(out_dir / fname)
        sidecar = {
            "cell_subject": cell_key,
            "staff_subject": staff_key,
            "bbox_page_px": box,
            "caveat": "the bracket is the CELL FRAME (header + first bar for "
                      "cell 0), not any one glyph -- Q.METER_GLYPH carries no "
                      "page-pixel bbox for this family",
            "file": fname,
            "VERDICT_none_yet": None,
        }
        (out_dir / f"m212h-brahms1-breitkopf-{label}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  -> {fname}", file=sys.stderr)

    (out_dir / "m212h-crop-manifest.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest["tiles"]), "of": len(targets)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
