"""ROADMAP 2.8 funnel diagnosis (2026-09-28) -- crops of held-out bars, one
per top-3 cause x 4, for Sean.

Self-contained by design (CLAUDE.md 5c/13: a lane report is a ledger, check
it against the tree): given a bar list (`funnel_bars.json`, the exact bars
the FINDINGS section names) and the SAME fresh whole-movement record the
funnel was computed from, this script reads the record ONCE via
`record_io.load_record` (the one sanctioned reader -- CLAUDE.md SS4b) for
`cell_box`/`staff_lines`/`staff_spacing` ONLY, renders each bar's own PAGE
directly from the PDF (`render_page` -- no detector, no re-gather, no
re-adjudication), crops the bar, draws its staff's lines, brackets the bar's
own cell frame, and writes the judged meter, the true meter, and the
computed sum in the margin. Sean adjudicates; this job only cuts the crop
(CLAUDE.md `feedback_send_sean_the_crop`).

    python3 probe/crop_funnel.py \
        --record /path/to/brahms1-breitkopf-whole-movement-*.record.json \
        --bars probe/funnel_bars.json \
        --out-dir out/print/funnel-2026-09-28
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True,
                    help="the fresh whole-movement record (read ONCE, geometry only)")
    ap.add_argument("--bars", required=True, help="funnel_bars.json")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw

    from tools.omr.preprocessing import render_page
    from tools.omr.staged import record_io

    spec = json.loads(Path(a.bars).read_text())
    pdf = spec["pdf"]
    label = spec["label"]
    bars = spec["bars"]

    print(f"loading {a.record} via record_io.load_record "
         f"(geometry only -- staff_lines/staff_spacing/cell_box) ...",
         file=sys.stderr)
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

    for i, bar in enumerate(bars):
        page, system, staff, cell = bar["page"], bar["system"], bar["staff"], bar["cell"]
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
        # x span: the bar's own cell frame plus 1.5 spaces either side.
        cx0 = int(max(0, px0 - 1.5 * spacing))
        cx1 = int(min(img.width, px1 + 1.5 * spacing))
        # y span: the whole staff band plus 2 spaces margin above (for the
        # written annotation) and below.
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

        # the bar itself, bracketed -- the cell frame the hold-out judged.
        bx0, by0 = (px0 - cx0) * UPSCALE, (py0 - cy0) * UPSCALE
        bx1, by1 = (px1 - cx0) * UPSCALE, (py1 - cy0) * UPSCALE
        draw.rectangle([(bx0, by0), (bx1, by1)], outline=(220, 20, 20),
                       width=max(2, UPSCALE // 2))

        want_q = bar["want_quarters"]
        true_q = bar["true_quarters"]
        sums = bar["sum_quarters"]
        label_line1 = (f"p{page} sys{system} staff{staff} cell{cell}  "
                       f"m.{bar['measure']}  {bar['part']}  [{bar['cause']}]")
        label_line2 = (f"judged meter: {want_q}q   true meter: {true_q}q   "
                       f"read sum: {sums}")
        draw.rectangle([(2, 2), (crop.width - 2, 46)], fill=(255, 255, 255))
        draw.text((6, 4), label_line1, fill=(0, 0, 0))
        draw.text((6, 24), label_line2, fill=(150, 0, 0))

        tile_id = f"{page}-{system}-{staff}-{cell}"
        fname = f"funnel-{label}-{bar['cause']}-{tile_id}.png"
        crop.save(out_dir / fname)
        sidecar = {
            "subject": cell_key,
            "cause": bar["cause"],
            "page": page, "system": system, "staff": staff, "cell": cell,
            "measure": bar["measure"], "part": bar["part"],
            "want_quarters": want_q, "true_quarters": true_q,
            "sum_quarters": sums,
            "note": bar["note"],
            "bbox_page_px": box,
            "file": fname,
            # Sean adjudicates; this job only cuts the crop.
            "VERDICT_none_yet": None,
        }
        (out_dir / f"funnel-{label}-{bar['cause']}-{tile_id}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  [{i+1}/{len(bars)}] {cell_key} -> {fname}", file=sys.stderr)

    (out_dir / f"funnel-crop-manifest-{label}.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest["tiles"]), "of": len(bars)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
