"""ROADMAP 2.12d -- crops of systems whose mid-staff meter reading was
DECLINED (`meter_change_not_system_wide`), for Sean.

Self-contained by design (CLAUDE.md §5b/§13: a lane report is a ledger, check
it against the tree): given a list of declined change subjects (produced by
scanning the FRESH whole-movement Brahms record for `Q.METER` segments with
`corroborated: False` -- the exact candidates 2.12d now declines) and the
SAME record, this script reads the record ONCE via `record_io.load_record`
(the one sanctioned reader) for `cell_box`/`staff_lines`/`staff_spacing`
geometry only, renders each bar's own PAGE straight off the PDF (no
detector, no re-gather, no re-adjudication), crops the CELL the declined
candidate was filed at, draws the READING staff's own lines (CLAUDE.md
`feedback_send_sean_the_crop`: the crop must NAME the staff and draw ITS
lines, never a neighbour's), brackets the cell frame, and writes the
declined value and its support in the margin. Sean adjudicates; this job
only cuts the crop.

⚠️ THE BRACKET IS THE CELL, NOT THE GLYPH. `Q.METER_GLYPH` carries only
`x_canonical`/`y_center` (the rescaled, per-cell coordinate frame CLAUDE.md
§10 says "cannot answer a cross-staff question" and everything else in this
project also declines to crop from) -- no page-pixel bbox is filed for this
family. The cell frame is the same subject `crop_funnel.py` already brackets
for 2.8's own crops, and it is named as a caveat in every sidecar rather than
overstated as a glyph-level bracket.

    python3 crop_declined_meter.py --record <record.json> \
        --declined declined_meter_bars.json --out-dir out/print/m212d-...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--declined", required=True,
                    help="JSON: {pdf, label, items: [{subject, page, system, "
                         "staff, from_cell, numerator, denominator, raw, "
                         "support, staves_reading_it}]}")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw

    from tools.omr.preprocessing import render_page
    from tools.omr.staged import record_io

    spec = json.loads(Path(a.declined).read_text())
    pdf, label, items = spec["pdf"], spec["label"], spec["items"]

    print(f"loading {a.record} via record_io.load_record "
         f"(geometry only) ...", file=sys.stderr)
    data = record_io.load_record(a.record)
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
    provenance = data.get("provenance")
    del rec, data
    print(f"geometry rows: {len(staff_lines)} staff_lines, "
         f"{len(staff_spacing)} staff_spacing, {len(cell_box)} cell_box",
         file=sys.stderr)
    if provenance:
        print(f"record provenance: {provenance.get('commit')} "
             f"dirty={provenance.get('dirty')}", file=sys.stderr)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    page_cache: dict = {}
    manifest = {"label": label, "pdf": pdf, "dpi": a.dpi, "tiles": []}

    for i, item in enumerate(items):
        page, system, staff = item["page"], item["system"], item["staff"]
        cell = item["from_cell"]
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
            pi = render_page(pdf, page, dpi=a.dpi)
            arr = getattr(pi, "rgb", None)
            if arr is None:
                arr = getattr(pi, "binary")
            arr_np = np.asarray(arr)
            page_cache[page] = Image.fromarray(
                arr_np if arr_np.ndim == 3 else np.stack([arr_np] * 3, axis=-1))
        img = page_cache[page]

        px0, py0, px1, py1 = box
        cx0 = int(max(0, px0 - 2.5 * spacing))
        cx1 = int(min(img.width, px1 + 2.5 * spacing))
        cy0 = int(max(0, min(line_ys) - 3.5 * spacing))
        cy1 = int(min(img.height, max(line_ys) + 2.0 * spacing))

        crop = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
        UPSCALE = 5
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

        raw = item.get("raw") or f"{item['numerator']}/{item['denominator']}"
        label_line1 = (f"p{page} sys{system} staff{staff} cell{cell}  "
                       f"declined: {raw}  support {item.get('support')}")
        label_line2 = (f"read by staff(s) {item.get('staves_reading_it')} "
                       f"of this system only -- DECLINED (meter_change_"
                       f"not_system_wide)")
        draw.rectangle([(2, 2), (crop.width - 2, 46)], fill=(255, 255, 255))
        draw.text((6, 4), label_line1, fill=(0, 0, 0))
        draw.text((6, 24), label_line2, fill=(150, 0, 0))

        tile_id = f"{page}-{system}-{staff}-{cell}"
        fname = f"m212d-{label}-declined-{tile_id}.png"
        crop.save(out_dir / fname)
        sidecar = {
            "subject": item.get("subject"),
            "quantity": "meter",
            "cell_subject": cell_key,
            "staff_subject": staff_key,
            "declined_reason": "meter_change_not_system_wide",
            "numerator": item["numerator"], "denominator": item["denominator"],
            "raw": raw, "support": item.get("support"),
            "staves_reading_it": item.get("staves_reading_it"),
            "bbox_page_px": box,
            "caveat": "the bracket is the CELL FRAME the reading was filed "
                      "at, not the glyph itself -- Q.METER_GLYPH carries no "
                      "page-pixel bbox for this family (see script docstring)",
            "file": fname,
            "VERDICT_none_yet": None,
        }
        (out_dir / f"m212d-{label}-declined-{tile_id}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  [{i+1}/{len(items)}] {cell_key} -> {fname}", file=sys.stderr)

    (out_dir / f"m212d-crop-manifest-{label}.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest["tiles"]), "of": len(items)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
