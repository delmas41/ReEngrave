"""ROADMAP 2.12h.b -- manager follow-up (trace only): is the return to 6/8,
printed right after the 9/8 bar, gathered anywhere inside `system/1/0`?

Same discipline as `crop_opening_meter.py`: reads `cell_box`/`staff_lines`/
`staff_spacing` from the already-saved whole-movement Brahms record via
`record_io.load_record` (geometry only, no detector, no re-gather, no
re-adjudication), renders the PDF page straight off disk, crops cell 1 (the
bar right after the system's own opening bar -- where a same-system return
would be printed) and cell 2 (the only cell in this system where `_meter_
changes` forms ANY paired digit candidate at all, on staff 7 alone) on a
clean staff and on staff 7 itself.
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
        (1, 0, 1, 1, "sys1-0-return-cell1-staff1-clean"),
        (1, 0, 7, 1, "sys1-0-return-cell1-staff7"),
        (1, 0, 7, 2, "sys1-0-return-cell2-staff7-spurious4-4"),
        (1, 0, 1, 2, "sys1-0-return-cell2-staff1-clean"),
    ]

    page_cache: dict = {}
    manifest = {"label": "brahms1-breitkopf-2.12h.b", "pdf": pdf, "dpi": dpi,
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

        fname = f"m212hb-brahms1-breitkopf-{label}.png"
        crop.save(out_dir / fname)
        sidecar = {
            "cell_subject": cell_key,
            "staff_subject": staff_key,
            "bbox_page_px": box,
            "caveat": "the bracket is the CELL FRAME, not any one glyph",
            "file": fname,
            "VERDICT_none_yet": None,
        }
        (out_dir / f"m212hb-brahms1-breitkopf-{label}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  -> {fname}", file=sys.stderr)

    (out_dir / "m212hb-crop-manifest.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest["tiles"]), "of": len(targets)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
