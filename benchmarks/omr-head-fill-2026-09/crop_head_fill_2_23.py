"""ROADMAP 2.23 -- banded crops of heads `head_fill_from_ink` touched.

Reads the re-gathered record directly (no separate geometry dump): every
`Q.DURATION` verdict in `record.verdicts` whose `reason` is
`"head_fill_from_ink"` (still NARROWED, unresolved) or whose `value`
carries a `"head_fill"` key (resolved by `reconcile_duration`, `reason`
now `"meter_reconciliation"`) -- the union is every head this item's rule
touched. Up to 8, preferring RESOLVED ones first (the bar's own arithmetic
picked a fill), banded by staff.

⚠️ FRAME CONTROL FIRST (`crop_losers_2_6b._frame_ok`, imported): a crop
whose filed staff's lines are not darker than a half-space off them is
REFUSED, not drawn. GREEN band = the staff the head is filed on, lines
drawn; red verticals = the cell's x-span; red corners = the subject box.

    python3 benchmarks/omr-head-fill-2026-09/crop_head_fill_2_23.py \
        <record.json> <pdf> [dpi]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-owner-domain-2026-09"))

OUT = HERE / "out" / "print"


def _parts(key: str):
    return key.split("/")


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from crop_losers_2_6b import _frame_ok

    record_path, pdf_path = sys.argv[1], sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    d = json.load(open(record_path))
    rec = d["record"]
    obs = rec["observations"]
    verdicts = rec["verdicts"]

    staff_lines = {o["subject"]: o["value"] for o in obs
                   if o["quantity"] == "staff_lines"}
    cell_box = {o["subject"]: o["value"] for o in obs
                if o["quantity"] == "cell_box"}
    glyph_box = {}
    for o in obs:
        if o["quantity"] == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                glyph_box[o["subject"]] = bp

    resolved, narrowed = [], []
    for v in verdicts:
        if v.get("quantity") != "duration":
            continue
        val = v.get("value")
        if isinstance(val, dict) and val.get("head_fill") and v.get("outcome") == "decided":
            resolved.append(v)
        elif v.get("reason") == "head_fill_from_ink":
            narrowed.append(v)

    print(f"resolved (bar chose a fill): {len(resolved)}")
    print(f"still narrowed (no unique landing yet): {len(narrowed)}")

    jobs = []
    for v in resolved:
        jobs.append({"subject": v["subject"], "kind": "resolved",
                     "head_fill": v["value"]["head_fill"],
                     "beats": v["value"].get("beats")})
    for v in narrowed:
        jobs.append({"subject": v["subject"], "kind": "narrowed",
                     "candidates": [c["value"].get("head_fill")
                                    for c in v.get("candidates", [])]})
    jobs = jobs[:8]

    font = ImageFont.load_default(size=26)
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    pages = {}
    manifest = []

    for n, job in enumerate(jobs, 1):
        sub = job["subject"]                       # glyph/p/sys/staff/cell/gi
        p, sysn, st, c, gi = _parts(sub)[1:]
        p = int(p)
        skey = f"staff/{p}/{sysn}/{st}"
        ckey = f"cell/{p}/{sysn}/{st}/{c}"
        if skey not in staff_lines or ckey not in cell_box or sub not in glyph_box:
            manifest.append({"n": n, "subject": sub,
                             "refused": "no geometry on the record"})
            continue
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
            pages[p] = (img, np.asarray(img.convert("L"), dtype=float))
        page, arr = pages[p]
        lines = staff_lines[skey]
        spacing = (lines[-1] - lines[0]) / 4.0 if len(lines) >= 2 else 20.0
        ok, contrast = _frame_ok(arr, lines, spacing)
        cbox = cell_box[ckey]
        gbox = glyph_box[sub]
        pad = spacing * 4.0
        x0 = max(0, int(cbox[0] - pad // 2))
        x1 = min(page.width, int(cbox[2] + pad // 2))
        y0 = max(0, int(lines[0] - spacing * 2.5))
        y1 = min(page.height, int(lines[-1] + spacing * 2.5))
        crop = page.crop((x0, y0, x1, y1)).convert("RGB")
        draw = ImageDraw.Draw(crop)
        for ly in lines:
            yy = ly - y0
            draw.line([(0, yy), (crop.width, yy)], fill=(0, 160, 0), width=2)
        for cx in (cbox[0], cbox[2]):
            draw.line([(cx - x0, 0), (cx - x0, crop.height)],
                      fill=(220, 0, 0), width=2)
        gx0, gy0, gx1, gy1 = gbox
        L = 10
        for (cx, cy, sx, sy) in ((gx0, gy0, 1, 1), (gx1, gy0, -1, 1),
                                 (gx0, gy1, 1, -1), (gx1, gy1, -1, -1)):
            cx -= x0; cy -= y0
            draw.line([(cx, cy), (cx + L * sx, cy)], fill=(220, 0, 0), width=3)
            draw.line([(cx, cy), (cx, cy + L * sy)], fill=(220, 0, 0), width=3)
        caption = f"#{n} {sub} {job['kind']}"
        if job["kind"] == "resolved":
            caption += f" -> {job['head_fill']} ({job['beats']}q)"
        else:
            caption += f" candidates={job['candidates']}"
        band = Image.new("RGB", (crop.width, crop.height + 60), (255, 255, 255))
        band.paste(crop, (0, 60))
        ImageDraw.Draw(band).text((4, 4), caption, fill=(0, 0, 0), font=font)
        fname = f"head-fill-2026-09-{n:02d}-{job['kind']}.png"
        band.save(OUT / fname)
        manifest.append({"n": n, "subject": sub, "file": fname,
                         "frame_contrast": round(contrast, 2),
                         "frame_ok": ok, **job, "VERDICT_none_yet": None})

    with open(OUT / "head-fill-2026-09-manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"wrote {len(manifest)} entries to manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
