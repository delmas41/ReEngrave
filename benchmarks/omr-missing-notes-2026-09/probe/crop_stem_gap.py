"""ROADMAP 2.17 -- crops of the STEM-GAP population: `duration_narrowed:
beams_ambiguous` notes with `stems_attached==0` AND no accepted `Q.STEM`
row within one notehead width of the head (the cell had none at all, or
its nearest accepted stem belongs to a different note entirely) --
`stem_yield.py`'s own `stem_gap_far_or_empty` bucket.

⚠️ NO RECORD READ HERE, same discipline as `crop_beams_ambiguous.py`: every
geometry fact (`staff_lines`, `staff_spacing`, `cell_box`, the glyph's own
PAGE-frame `bbox_page`) was already pulled out of the ONE
`record_io.load_record` call inside `stem_yield.py` and sits in its
`out/stem_yield_<label>.json`. This script is a straight adaptation of
`crop_beams_ambiguous.py`'s own drawing code (banded staff, blue cell
frame, red corner brackets on the subject) -- kept byte-similar on purpose
so a reviewer comparing the two crop sets is comparing DATA, not a second
drawing convention.

    python3 benchmarks/omr-missing-notes-2026-09/probe/crop_stem_gap.py \\
        --in benchmarks/omr-missing-notes-2026-09/probe/out/stem_yield_breitkopf.json \\
        --label breitkopf
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "out" / "print"
DPI = 600
N_CROPS = 12


def main() -> int:
    import fitz
    from PIL import Image, ImageDraw, ImageFont

    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--label", required=True)
    a = ap.parse_args()

    data = json.loads(Path(a.inp).read_text())
    pdf_path = data["pdf"]
    examples = data["examples"]["stem_gap_far_or_empty"]
    geometry = data["geometry"]

    by_page: dict = {}
    for e in examples:
        if not geometry.get(e["subject"]):
            continue
        p = geometry[e["subject"]]["page"]
        by_page.setdefault(p, []).append(e)
    chosen = []
    for p in sorted(by_page):
        chosen.extend(by_page[p][:2])
        if len(chosen) >= N_CROPS:
            break
    chosen = chosen[:N_CROPS]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    font = ImageFont.load_default(size=20)

    manifest = {"label": f"stem_gap_{a.label}", "pdf": pdf_path, "dpi": DPI,
                "record": data["record"], "provenance": data["provenance"],
                "tiles": []}

    pages_cache: dict = {}

    def get_page(p):
        if p not in pages_cache:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else
                  Image.frombytes("L", (pm.width, pm.height),
                                  pm.samples).convert("RGB"))
            pages_cache[p] = im
        return pages_cache[p]

    for i, e in enumerate(chosen):
        sub = e["subject"]
        geo = geometry[sub]
        page, system, staff, cell = (geo["page"], geo["system"],
                                      geo["staff"], geo["cell"])
        line_ys = geo["staff_lines"]
        spacing = geo["staff_spacing"] or 40.0
        cell_box = geo["cell_box"]
        bbox_page = e.get("bbox_page")
        if not line_ys or not cell_box or not bbox_page:
            print(f"  SKIP {sub}: missing geometry "
                  f"(lines={bool(line_ys)} cell={bool(cell_box)} "
                  f"glyph={bool(bbox_page)})", file=sys.stderr)
            continue

        im = get_page(page)
        cx0f, cy0f, cx1f, cy1f = cell_box
        gx0, gy0, gx1, gy1 = bbox_page

        pad_x = 1.2 * spacing
        cx0 = int(max(0, min(cx0f, gx0) - pad_x))
        cx1 = int(min(im.width, max(cx1f, gx1) + pad_x))
        top_y = min(min(line_ys), gy0, cy0f)
        bot_y = max(max(line_ys), gy1, cy1f)
        cy0 = int(max(0, top_y - 2.5 * spacing))
        cy1 = int(min(im.height, bot_y + 2.0 * spacing))

        Z = 4
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)

        overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        top = (min(line_ys) - cy0) * Z
        bot = (max(line_ys) - cy0) * Z
        od.rectangle([0, top, crop.width, bot], fill=(30, 90, 255, 45))
        for ly in line_ys:
            y = (ly - cy0) * Z
            if 0 <= y < crop.height:
                od.line([(0, y), (crop.width, y)], fill=(30, 90, 255, 230),
                         width=4)
        big = ImageFont.load_default(size=max(24, int(spacing * Z * 0.55)))
        label = f"staff {page}/{system}/{staff}"
        od.rectangle([12, top + 4, 12 + od.textlength(label, font=big) + 12,
                     top + big.size + 12], fill=(255, 255, 255, 235),
                    outline=(30, 90, 255, 255), width=3)
        od.text((18, top + 6), label, fill=(30, 90, 255, 255), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")
        dr = ImageDraw.Draw(crop)

        bx0, by0 = (cx0f - cx0) * Z, (cy0f - cy0) * Z
        bx1, by1 = (cx1f - cx0) * Z, (cy1f - cy0) * Z
        dr.rectangle([(bx0, by0), (bx1, by1)], outline=(30, 90, 255), width=3)

        hx0, hy0 = (gx0 - cx0) * Z, (gy0 - cy0) * Z
        hx1, hy1 = (gx1 - cx0) * Z, (gy1 - cy0) * Z
        arm = max(14, int((hx1 - hx0) * 0.5))
        for (ax, ay, dx, dy) in ((hx0, hy0, 1, 1), (hx1, hy0, -1, 1),
                                  (hx0, hy1, 1, -1), (hx1, hy1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0), width=6)
            dr.line([(ax, ay), (ax, ay + dy * arm)], fill=(220, 0, 0), width=6)

        detail = e.get("detail") or {}
        gap_kind = "CELL_EMPTY" if not e.get("cell_stem_rows") else (
            f"FAR ({e.get('min_dist_notehead_widths'):.2f} notehead widths)"
            if e.get("min_dist_notehead_widths") is not None else "FAR")
        line1 = (f"p{page} sys{system} staff{staff} cell{cell}  "
                 f"glyph={sub.split('/')[-1]}  [stem_gap: {gap_kind}]")
        line2 = (f"beam_evidence={detail.get('beam_evidence')}  "
                 f"stems_attached={detail.get('stems_attached')}  "
                 f"yolo_beams={detail.get('yolo_beams')}  "
                 f"cv_beams={detail.get('cv_beams')}")
        line3 = (f"certain={detail.get('levels_certain')}  "
                 f"possible={detail.get('levels_possible')}  "
                 f"n_cell_stem_rows={len(e.get('cell_stem_rows') or [])}")

        band_h = 76
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        for j, text in enumerate((line1, line2, line3)):
            cd.text((6, 4 + j * 22), text, fill=(0, 0, 0) if j == 0
                     else (150, 0, 0), font=font)

        tile_id = f"{page}-{system}-{staff}-{cell}-{sub.split('/')[-1]}"
        fname = f"stem_gap-{a.label}-{tile_id}.png"
        out_im.save(OUT_DIR / fname)
        sidecar = {
            "subject": sub,
            "cause": "duration_narrowed:beams_ambiguous / stem_gap",
            "gap_kind": gap_kind,
            "page": page, "system": system, "staff": staff, "cell": cell,
            "detail": detail,
            "min_dist_notehead_widths": e.get("min_dist_notehead_widths"),
            "cell_stem_rows": e.get("cell_stem_rows"),
            "bbox_page": bbox_page,
            "file": fname,
            "VERDICT_none_yet": None,
        }
        (OUT_DIR / f"stem_gap-{a.label}-{tile_id}.json").write_text(
            json.dumps(sidecar, indent=2))
        manifest["tiles"].append(sidecar)
        print(f"  [{i + 1}/{len(chosen)}] {sub} -> {fname}", file=sys.stderr)

    (OUT_DIR / f"stem-gap-crop-manifest-{a.label}.json").write_text(
        json.dumps(manifest, indent=2))
    print(json.dumps({"cut": len(manifest["tiles"]), "of": len(chosen)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
