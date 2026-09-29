"""ROADMAP 3.2b -- print crops of the ties the RECORD now pairs on Litolff p3.

Reads ONLY `out/3.2b-litolff-p3-crops-cache.json` (written once by
`probe/readjudicate_tie_pair.py --crops-cache` over the acceptance Litolff
record); never touches the record. Crops come from the PDF at the gather's
own DPI (600).

Two populations, ≤ 8 crops in all (Sean's proof budget):
  * `linked` -- a pair `Q.TIE_PAIR` decided and EXPORT marked;
  * `contradiction` -- a pair `Q.TIE_PAIR` decided whose two placed pitches
    differ, so EXPORT refused it. The question there is WHICH is wrong: the
    pair, or one of the two pitches.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL: the home staff's own
`Q.STAFF_LINES` must be materially darker than a half-space off them on the
render, or the crop is REFUSED (`crop_losers_2_6b._frame_ok`, reused).
⚠️ THE STAFF IS DRAWN (a GREEN band on the staff the tie is filed on), the
START head is bracketed RED and labelled S, the STOP head bracketed MAGENTA
and labelled E, every arc that named the pair is outlined ORANGE. Every
manifest row carries `VERDICT_none_yet: null`.

    python3 benchmarks/omr-tie-pairing-2026-09/crop_ties_3_2b.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CACHE = HERE / "out" / "3.2b-litolff-p3-crops-cache.json"
OUT_DIR = HERE / "out" / "print"
DPI = 600
SEED = 20260929
N_LINKED = 5
N_CONTRA = 3

sys.path.insert(0, str(REPO_ROOT / "benchmarks" / "omr-owner-domain-2026-09"))
from crop_losers_2_6b import _frame_ok  # noqa: E402


def _pdf() -> Path:
    from tools.library.score_library import library_root
    return library_root() / (
        "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--"
        "henry-litolff-s-verlag-1870--imslp984073.pdf")


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    sys.path.insert(0, str(REPO_ROOT))
    font = ImageFont.load_default(size=20)
    rng = random.Random(SEED)
    cache = json.loads(CACHE.read_text())
    linked = list(cache["linked"])
    contra = list(cache["contradictions"])
    rng.shuffle(linked)
    print(f"population: linked={len(linked)} contradictions={len(contra)}")
    if not linked and not contra:
        print("DEAD: nothing to crop")
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(_pdf()))
    pages = {}

    def get_page(p):
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else Image.frombytes(
                      "L", (pm.width, pm.height), pm.samples).convert("RGB"))
            pages[p] = (im, np.asarray(im.convert("L"), dtype=float))
        return pages[p]

    def bracket(dr, box, cx0, cy0, Z, rgb, label, big):
        bx0, by0 = (box[0] - cx0) * Z, (box[1] - cy0) * Z
        bx1, by1 = (box[2] - cx0) * Z, (box[3] - cy0) * Z
        arm = max(12, int((bx1 - bx0) * 0.45))
        for ax, ay, dx, dy in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                               (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm, ay)], fill=rgb, width=6)
            dr.line([(ax, ay), (ax, ay + dy * arm)], fill=rgb, width=6)
        dr.text((bx0, by0 - big.size - 6), label, fill=rgb, font=big)

    manifest, refused = [], []
    n = 0
    for kind, pool, want in (("linked", linked, N_LINKED),
                             ("contradiction", contra, N_CONTRA)):
        made = 0
        for item in pool:
            if made >= want:
                break
            if not (item["start_box"] and item["stop_box"]
                    and item["staff_lines"]):
                refused.append({**item, "why": "missing geometry"})
                continue
            page = int(item["start"].split("/")[1])
            im, arr = get_page(page)
            sp = float(item["staff_spacing"] or 20.0)
            ok, contrast = _frame_ok(arr, item["staff_lines"], sp)
            if not ok:
                refused.append({**item, "why": f"FRAME CONTROL FAILED "
                                               f"{contrast:.1f}"})
                continue
            n += 1
            made += 1
            name = f"3.2b-tie-{n:02d}.png"
            boxes = [item["start_box"], item["stop_box"]] + [
                b for b in item["arc_boxes"] if b]
            xs = [b[0] for b in boxes] + [b[2] for b in boxes]
            ys = ([b[1] for b in boxes] + [b[3] for b in boxes]
                  + list(item["staff_lines"]))
            cx0 = int(max(0, min(xs) - 14 * sp))
            cx1 = int(min(im.width, max(xs) + 14 * sp))
            cy0 = int(max(0, min(ys) - 6 * sp))
            cy1 = int(min(im.height, max(ys) + 6 * sp))
            Z = 2
            crop = im.crop((cx0, cy0, cx1, cy1)).resize(
                ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
            overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            lines = item["staff_lines"]
            top, bot = (min(lines) - cy0) * Z, (max(lines) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=(0, 170, 60, 45))
            for ly in lines:
                y = (ly - cy0) * Z
                od.line([(0, y), (crop.width, y)], fill=(0, 170, 60, 200),
                        width=3)
            crop = Image.alpha_composite(crop.convert("RGBA"),
                                         overlay).convert("RGB")
            dr = ImageDraw.Draw(crop)
            big = ImageFont.load_default(size=max(28, int(sp * Z * 0.8)))
            for b in item["arc_boxes"]:
                if b:
                    dr.rectangle([(b[0] - cx0) * Z, (b[1] - cy0) * Z,
                                  (b[2] - cx0) * Z, (b[3] - cy0) * Z],
                                 outline=(255, 140, 0), width=4)
            bracket(dr, item["start_box"], cx0, cy0, Z, (220, 0, 0), "S", big)
            bracket(dr, item["stop_box"], cx0, cy0, Z, (200, 0, 200), "E", big)
            # ruler: one tick per staff space off the top line
            y, k = (min(lines) - cy0) * Z, 0
            while y < crop.height:
                dr.line([(2, y), (16 if k % 5 else 26, y)],
                        fill=(0, 90, 200), width=2)
                y += sp * Z
                k += 1
            q = ("Q: is S~E ONE printed tie? (yes / it is a slur / "
                 "wrong notes / not a tie at all)" if kind == "linked" else
                 "Q: is S~E a printed tie? if yes, which pitch is misread "
                 "(S / E)? if no, what is the arc?")
            title = [
                (f"{name}  {kind.upper()}  pdf idx {page}  staff "
                 f"{item['staff']} (GREEN)", (0, 0, 0)),
                (f"S={item['start']} {item['pitches'][0]}   "
                 f"E={item['stop']} {item['pitches'][1]}", (120, 0, 80)),
                (f"arc(s) ORANGE: {', '.join(item['arcs'])}", (160, 90, 0)),
                (q, (0, 0, 0)),
            ]
            band = 22 * (len(title) + 1)
            out = Image.new("RGB", (crop.width, crop.height + band), "white")
            out.paste(crop, (0, band))
            cd = ImageDraw.Draw(out)
            for i, (text, color) in enumerate(title):
                cd.text((6, 4 + i * 22), text, fill=color, font=font)
            out.save(OUT_DIR / name)
            manifest.append({
                "n": n, "file": name, "kind": kind, "page": page,
                "staff": item["staff"], "start": item["start"],
                "stop": item["stop"], "pitches": item["pitches"],
                "arcs": item["arcs"], "start_box": item["start_box"],
                "stop_box": item["stop_box"],
                "frame_contrast": round(contrast, 2),
                "question": q[3:], "VERDICT_none_yet": None})
    (OUT_DIR / "3.2b-manifest.json").write_text(json.dumps({
        "roadmap_item": "3.2b",
        "cache": str(CACHE.relative_to(REPO_ROOT)),
        "record_provenance": cache.get("record"),
        "dpi": DPI, "seed": SEED,
        "population": {"linked": len(linked),
                       "contradictions": len(contra)},
        "crops": manifest, "refused": refused}, indent=1))
    print(f"wrote {len(manifest)} crops, refused {len(refused)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
