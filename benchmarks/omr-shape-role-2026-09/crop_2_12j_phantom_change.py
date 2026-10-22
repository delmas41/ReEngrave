"""ROADMAP 2.12j -- crops of systems whose mid-staff `4/4` change was
DECIDED (`change_only`, corroborated at the bare absolute floor of 2) on a
MINORITY of a 13-14-staff system, for Sean.

Self-contained (CLAUDE.md §5b/§13: a lane report is a ledger, check it
against the tree): reads ONLY the geometry rows this crop needs
(`staff_lines`, `staff_spacing`, `cell_box`) for the specific subjects named
below, streamed via `ijson` directly from `record.observations` -- NOT the
full `record_io.load_record` (the sanctioned reader for a whole record), because
this record is 1.6 GB and these three quantities are never pooled (pooling
in `record_io` applies only to a VERDICT's own id-list fields -- `considered`,
`basis`, `correlated` -- never to an observation's `value`; see that module's
own docstring), so a direct stream over `observations` for these three
`quantity` strings reproduces exactly what the sanctioned reader would hand
back for them, at a fraction of the cost. No detector, no re-gather, no
re-adjudication -- this needed none of that, only the pages rendered
straight off the PDF.

⚠️ THE BRACKET IS THE CELL, NOT THE GLYPH -- same caveat as `crop_declined_
meter.py` (2.12d): `Q.METER_GLYPH` carries only `x_canonical`/`y_center` (a
per-cell, rescaled coordinate frame), no page-pixel bbox for this family.

    python3 crop_2_12j_phantom_change.py --out-dir out/print/m212j-...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

RECORD = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
          "redecide-92b6ab04/out-redecide/brahms/amended.record.json")
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
       "symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-"
       "brahms--imslp317803.pdf")

#: The four representative DECIDED `change_only` segments cropped for Sean,
#: out of the eleven found on the whole-movement re-decision (`benchmarks/
#: omr-shape-role-2026-09/FINDINGS.md` PART 8's own table has all eleven).
#: `page` here is the PDF page index (= the `system/<page>/<local>` first
#: number the record and this benchmark's other scripts already use).
ITEMS = [
    {"page": 2, "system": 0, "cell": 4, "staves": [6, 8],
     "numerator": 4, "denominator": 4, "support": 6.0,
     "coverage": "2 of 14 (14.3%)"},
    {"page": 3, "system": 0, "cell": 6, "staves": [2, 4, 5, 7],
     "numerator": 4, "denominator": 4, "support": 11.5,
     "coverage": "4 of 14 (28.6%)"},
    {"page": 9, "system": 1, "cell": 7, "staves": [9, 10],
     "numerator": 4, "denominator": 4, "support": 5.5,
     "coverage": "2 of 13 (15.4%)"},
    {"page": 12, "system": 0, "cell": 12, "staves": [4, 5],
     "numerator": 4, "denominator": 4, "support": 5.0,
     "coverage": "2 of 14 (14.3%)"},
]


def _needed_subjects():
    """{staff_subject, cell_subject-for-every-staff-in-the-item}."""
    staff_subjects = set()
    cell_subjects = set()
    for item in ITEMS:
        for st in item["staves"]:
            staff_subjects.add(f"staff/{item['page']}/{item['system']}/{st}")
            cell_subjects.add(
                f"cell/{item['page']}/{item['system']}/{st}/{item['cell']}")
    return staff_subjects, cell_subjects


def main() -> int:
    import ijson
    import numpy as np
    from PIL import Image, ImageDraw

    from tools.omr.preprocessing import render_page

    out_dir = Path(sys.argv[sys.argv.index("--out-dir") + 1]
                  if "--out-dir" in sys.argv else HERE / "out" / "print" /
                  "m212j-phantom-change")
    out_dir.mkdir(parents=True, exist_ok=True)

    staff_subjects, cell_subjects = _needed_subjects()
    staff_lines: dict = {}
    staff_spacing: dict = {}
    cell_box: dict = {}
    print(f"streaming {RECORD} via ijson (geometry only, "
         f"{len(staff_subjects)} staves / {len(cell_subjects)} cells) ...",
         file=sys.stderr)
    with open(RECORD, "rb") as f:
        for o in ijson.items(f, "record.observations.item"):
            subj = o.get("subject")
            q = o.get("quantity")
            if q == "staff_lines" and subj in staff_subjects:
                staff_lines[subj] = o["value"]
            elif q == "staff_spacing" and subj in staff_subjects:
                staff_spacing[subj] = o["value"]
            elif q == "cell_box" and subj in cell_subjects:
                cell_box[subj] = o["value"]
    print(f"geometry rows: {len(staff_lines)} staff_lines, "
         f"{len(staff_spacing)} staff_spacing, {len(cell_box)} cell_box "
         f"(wanted {len(staff_subjects)}/{len(staff_subjects)}/"
         f"{len(cell_subjects)})", file=sys.stderr)

    page_cache: dict = {}
    manifest = {"label": "brahms1-breitkopf", "pdf": PDF, "dpi": 600,
               "tiles": []}

    for item in ITEMS:
        page, system, cell = item["page"], item["system"], item["cell"]
        staves = item["staves"]
        if page not in page_cache:
            print(f"rendering page {page} ...", file=sys.stderr)
            pi = render_page(PDF, page, dpi=600)
            arr = getattr(pi, "rgb", None)
            if arr is None:
                arr = getattr(pi, "binary")
            arr_np = np.asarray(arr)
            page_cache[page] = Image.fromarray(
                arr_np if arr_np.ndim == 3 else np.stack([arr_np] * 3, axis=-1))
        img = page_cache[page]

        # Bracket EVERY reading staff's own cell in one crop -- the reading
        # is a claim about several staves at once, and the crop should show
        # exactly the staves the corroboration counted, each with its OWN
        # lines drawn (CLAUDE.md `feedback_send_sean_the_crop`).
        boxes = []
        all_lines = []
        for st in staves:
            staff_key = f"staff/{page}/{system}/{st}"
            cell_key = f"cell/{page}/{system}/{st}/{cell}"
            box = cell_box.get(cell_key)
            lines = staff_lines.get(staff_key)
            if not box or not lines:
                print(f"  SKIP {cell_key}: missing geometry "
                     f"(cell_box={bool(box)} staff_lines={bool(lines)})",
                     file=sys.stderr)
                continue
            boxes.append((st, box, lines))
            all_lines.extend(lines)
        if not boxes:
            print(f"  SKIP page {page} sys {system} cell {cell}: "
                 f"no geometry for any staff", file=sys.stderr)
            continue

        spacing0 = float(
            staff_spacing.get(f"staff/{page}/{system}/{boxes[0][0]}") or 40.0)
        px0 = float(min(b[1][0] for b in boxes))
        px1 = float(max(b[1][2] for b in boxes))
        all_lines = [float(v) for v in all_lines]
        cy0 = int(max(0, min(all_lines) - 3.5 * spacing0))
        cy1 = int(min(img.height, max(all_lines) + 3.5 * spacing0))
        cx0 = int(max(0, px0 - 2.5 * spacing0))
        cx1 = int(min(img.width, px1 + 2.5 * spacing0))

        crop = img.crop((cx0, cy0, cx1, cy1)).convert("RGB")
        UPSCALE = 4
        crop = crop.resize((crop.width * UPSCALE, crop.height * UPSCALE),
                           Image.NEAREST)
        draw = ImageDraw.Draw(crop)

        for st, box, lines in boxes:
            box = [float(v) for v in box]
            for ly in lines:
                y = (float(ly) - cy0) * UPSCALE
                draw.line([(0, y), (crop.width, y)], fill=(70, 130, 220),
                         width=max(1, UPSCALE // 3))
            bx0, by0 = (box[0] - cx0) * UPSCALE, (box[1] - cy0) * UPSCALE
            bx1, by1 = (box[2] - cx0) * UPSCALE, (box[3] - cy0) * UPSCALE
            draw.rectangle([(bx0, by0), (bx1, by1)], outline=(220, 20, 20),
                          width=max(2, UPSCALE // 2))
            draw.text((bx0 + 4, by0 + 2), f"staff {st}", fill=(220, 20, 20))

        raw = f"{item['numerator']}/{item['denominator']}"
        label_line1 = (f"p{page} sys{system} cell{cell}  DECIDED "
                       f"change_only: {raw}  support {item['support']}")
        label_line2 = (f"read by staff(s) {staves} only -- "
                       f"{item['coverage']} of this system's own staves")
        draw.rectangle([(2, 2), (crop.width - 2, 46)], fill=(255, 255, 255))
        draw.text((6, 4), label_line1, fill=(0, 0, 0))
        draw.text((6, 24), label_line2, fill=(150, 0, 0))

        tile_id = f"{page}-{system}-{cell}"
        fname = f"m212j-phantom-{tile_id}.png"
        crop.save(out_dir / fname)
        sidecar = {
            "cell_subjects": [f"cell/{page}/{system}/{st}/{cell}"
                             for st in staves],
            "quantity": "meter",
            "decided_reason": "change_only",
            "numerator": item["numerator"], "denominator": item["denominator"],
            "raw": raw, "support": item["support"],
            "staves_reading_it": staves,
            "coverage_of_system": item["coverage"],
            "caveat": "the bracket is the CELL FRAME each reading staff was "
                      "filed at, not the glyph itself -- Q.METER_GLYPH "
                      "carries no page-pixel bbox for this family",
            "file": fname,
            "VERDICT_none_yet": None,
        }
        (out_dir / f"m212j-phantom-{tile_id}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  {page}/{system}/{cell} -> {fname}", file=sys.stderr)

    (out_dir / "m212j-crop-manifest.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest["tiles"]), "of": len(ITEMS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
