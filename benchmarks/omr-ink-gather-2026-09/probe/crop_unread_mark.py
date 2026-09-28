"""ROADMAP 2.4c — crops of every bar `adjudicate_unread_mark` fires on.

Self-contained: re-runs GATHER -> ADJUDICATE -> EVALUATE with `--ink-rows`
(`ink_component_rows=True`) in-process for one page, exactly the CLI's own
call shape (`tools.omr.staged.pipeline.run_staged`), so there is no giant
intermediate record file to keep or commit. The new decision
(`adjudicators.unread_mark.adjudicate_unread_mark`) runs automatically as
part of `adjudicate.ORDER` -- this script only READS its verdicts, exactly
as `crop_refused.py` (roadmap 2.4a) reads `notehead_is_not_a_notehead`'s.

⚠️ THESE ARE THE BARS THE RULE MARKS, NOT A VERDICT ON THEM. Sean adjudicates;
this job only cuts the crop, names the staff and draws its lines (CLAUDE.md
`feedback_send_sean_the_crop`: a crop in the gap between two staves commits
to neither and is not evidence -- the staff lines below are drawn from the
SAME `Q.STAFF_LINES` row the decision itself read).

    python3 probe/crop_unread_mark.py \
        --pdf <litolff.pdf> --page 3 --label litolff \
        --weights <weights.pt> --n 6 --out-dir out/print
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record import Subject  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw

    from tools.omr.preprocessing import render_page
    from tools.omr.staged import pipeline
    from tools.omr.yolo_detector import YoloDetector

    detector = YoloDetector(a.weights)
    result = pipeline.run_staged(
        a.pdf, [a.page], detector=detector, dpi=a.dpi,
        ink_component_rows=True, surya_fallback=False, ocr_fallback=False,
        progress=True)
    rec = result["record"]

    fired = [v for v in rec["verdicts"]
             if v["quantity"] == "unread_mark" and v["outcome"] == "decided"
             and v["value"] is True]
    fired.sort(key=lambda v: v["subject"])
    print(f"{a.label} p{a.page}: {len(fired)} fired unread_mark verdicts",
         file=sys.stderr)
    if not fired:
        print("DEAD: nothing fired on this page", file=sys.stderr)
        return 2
    picked = fired[:a.n]

    staff_lines: dict = {}   # staff subject key -> [line_ys, spacing]
    for o in rec["observations"]:
        if o["quantity"] == "staff_lines":
            staff_lines.setdefault(o["subject"], [None, None])[0] = o["value"]
        if o["quantity"] == "staff_spacing":
            staff_lines.setdefault(o["subject"], [None, None])[1] = o["value"]

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"rendering page {a.page} ...", file=sys.stderr)
    pi = render_page(a.pdf, a.page, dpi=a.dpi)
    arr = getattr(pi, "rgb", None)
    if arr is None:
        arr = getattr(pi, "binary")
    arr_np = np.asarray(arr)
    img = Image.fromarray(
        arr_np if arr_np.ndim == 3 else np.stack([arr_np] * 3, axis=-1))

    manifest = {"label": a.label, "pdf": a.pdf, "page": a.page,
               "dpi": a.dpi, "tiles": []}

    for v in picked:
        sub = Subject.from_key(v["subject"])
        d = v.get("detail") or {}
        box = d.get("bbox_page_px")
        if not box:
            print(f"  SKIP {v['subject']}: no page box in detail", file=sys.stderr)
            continue
        staff_key = f"staff/{sub.page}/{sub.system}/{sub.staff}"
        line_ys, spacing = staff_lines.get(staff_key, (None, None))
        spacing = spacing or 40.0
        px0, py0, px1, py1 = box
        col_x = d.get("column_x_page")

        # x span: the component plus 4 spaces either side, widened to reach
        # the corroborated column if it falls outside that (so the OTHER
        # staff's evidence is not cropped away).
        xs = [px0 - 4.0 * spacing, px1 + 4.0 * spacing]
        if col_x is not None:
            xs += [col_x - spacing, col_x + spacing]
        cx0, cx1 = int(max(0, min(xs))), int(min(img.width, max(xs)))
        # y span: the whole staff band (its 5 lines) plus 2 spaces margin,
        # WIDENED to the flagged box's own y if that falls outside it --
        # "the crop must NAME the staff the subject is filed on and DRAW its
        # lines", never crop between two staves, and never crop the subject
        # itself off canvas. ⚠️ A BOX FAR FROM ITS OWN STAFF'S BAND IS A
        # FINDING, NOT A BUG TO HIDE: the first draft of this script cropped
        # tightly to the staff band alone and silently cut a real candidate
        # (`cell/3/0/1/3`, 3.6 spaces below staff 1's bottom line) off the
        # visible image entirely -- exactly the cross-staff-bleed risk
        # CLAUDE.md SS10 names, and the crop must SHOW it so Sean can judge
        # it, not crop it away.
        if line_ys:
            cy0 = int(max(0, min(min(line_ys) - 2.0 * spacing,
                                 py0 - 1.0 * spacing)))
            cy1 = int(min(img.height, max(max(line_ys) + 2.0 * spacing,
                                          py1 + 1.0 * spacing)))
        else:
            cy0 = int(max(0, py0 - 3.0 * spacing))
            cy1 = int(min(img.height, py1 + 3.0 * spacing))

        crop = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
        # ⚠️ UPSCALED FOR LEGIBILITY. A native crop at this page's own DPI is
        # 2-6 staff spaces on a side (Litolff's page-frame spacing measures
        # 15.75px), which prints as a postage stamp; NEAREST keeps every
        # pixel edge sharp rather than smearing the ink into grey.
        UPSCALE = 6
        crop = crop.resize((crop.width * UPSCALE, crop.height * UPSCALE),
                           Image.NEAREST)
        draw = ImageDraw.Draw(crop)

        # the staff lines, drawn -- the frame the box below is filed in.
        if line_ys:
            for ly in line_ys:
                y = (ly - cy0) * UPSCALE
                draw.line([(0, y), (crop.width, y)], fill=(70, 130, 220),
                         width=max(1, UPSCALE // 3))

        # ⚠️ NEIGHBOURING STAVES, IN GREY, WHEN THE CROP REACHES THEM. Not
        # this decision's own evidence -- shown only so a crop widened to
        # reach a far-from-its-staff box (above) can be judged for
        # cross-staff bleed at a glance, rather than needing a second crop.
        for other_staff in (sub.staff - 1, sub.staff + 1):
            if other_staff < 0:
                continue
            other_key = f"staff/{sub.page}/{sub.system}/{other_staff}"
            other_lines, _sp = staff_lines.get(other_key, (None, None))
            if not other_lines:
                continue
            for ly in other_lines:
                if not (cy0 <= ly <= cy1):
                    continue
                y = (ly - cy0) * UPSCALE
                draw.line([(0, y), (crop.width, y)], fill=(160, 160, 160),
                         width=max(1, UPSCALE // 4))

        # the corroborated column, a dashed vertical line.
        if col_x is not None:
            x = (col_x - cx0) * UPSCALE
            for y in range(0, crop.height, 6 * UPSCALE):
                draw.line([(x, y), (x, min(y + 3 * UPSCALE, crop.height))],
                         fill=(30, 160, 60), width=max(2, UPSCALE // 2))

        # the flagged component itself -- corner brackets on the EXACT box.
        bx0, by0 = (px0 - cx0) * UPSCALE, (py0 - cy0) * UPSCALE
        bx1, by1 = (px1 - cx0) * UPSCALE, (py1 - cy0) * UPSCALE
        L = max(6.0 * UPSCALE, 0.35 * (bx1 - bx0))
        for (x, y, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                               (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            draw.line([(x, y), (x + dx * L, y)], fill=(220, 20, 20),
                     width=max(2, UPSCALE // 2))
            draw.line([(x, y), (x, y + dy * L)], fill=(220, 20, 20),
                     width=max(2, UPSCALE // 2))

        label = (f"p{sub.page} sys{sub.system} staff{sub.staff} cell{sub.cell}")
        draw.rectangle([(2, 2), (10 + 7 * len(label), 16)], fill=(255, 255, 255))
        draw.text((4, 3), label, fill=(0, 0, 0))

        tile_id = v["subject"].replace("/", "-")
        fname = f"u24c-{a.label}-{tile_id}.png"
        crop.save(out_dir / fname)
        sidecar = {
            "subject": v["subject"], "page": sub.page, "system": sub.system,
            "staff": sub.staff, "cell": sub.cell, "reason": "unread_mark",
            "ink_components": d.get("ink_components"),
            "width_spaces": d.get("width_spaces"),
            "height_spaces": d.get("height_spaces"),
            "bbox_page_px": box,
            "column_x_page": col_x,
            "column_witnesses": d.get("column_witnesses"),
            "column_n_witness": d.get("column_n_witness"),
            "excluded_by_guard": d.get("excluded_by_guard"),
            "file": fname,
            # Sean adjudicates; this job only cuts the crop.
            "VERDICT_none_yet": None,
        }
        (out_dir / f"u24c-{a.label}-{tile_id}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  {v['subject']} -> {fname}", file=sys.stderr)

    (out_dir / f"u24c-crop-manifest-{a.label}.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"picked": len(manifest["tiles"]), "of_fired": len(fired)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
