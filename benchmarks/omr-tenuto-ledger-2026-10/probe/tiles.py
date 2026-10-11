"""ROADMAP 2.84 -- crops of articulation boxes, BLIND, phone-sized.

    python3 benchmarks/omr-tenuto-ledger-2026-10/probe/tiles.py SEL.json \
        --out out/print/2.84-review [--question "..."]

`SEL.json`: a list of {n, doc (brahms|litolff), page, subject, mark_bbox_page,
read (hidden from Sean), category (hidden)}. Each tile is the PDF cut at the
gather's own 600 dpi in the gather's own frame (`render_page_matching_gather`),
a red CORNER BRACKET on the mark, a BIG tile number, and NOTHING of ours drawn.
The frame control is 2.12f's (`cut_artic_tiles.frame_control`), run on the real
box and on the box shifted (40, 40) px, which must fail on most tiles.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-local-staff-2026-09"))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-shape-role-2026-09"))

import cv2                                   # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402
from cut_artic_tiles import bracket, frame_control  # noqa: E402

DPI = 600
PDF = {
    "brahms": "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68"
              "--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": "library/editions/beethoven/symphony-5-op67/beethoven--symphony"
               "-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
DOCNAME = {"brahms": "Brahms 1", "litolff": "Beethoven 5"}
QUESTION = "Bracketed mark: ledger line (L) or tenuto (T)?"
BIG = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
MID = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("--out", required=True)
    ap.add_argument("--question", default=QUESTION)
    a = ap.parse_args(argv)
    sel = json.load(open(a.selection))
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = {}
    manifest = {"dpi": DPI, "question": a.question, "tiles": []}
    real = shifted = 0
    for t in sel:
        key = (t["doc"], t["page"])
        if key not in cache:
            pg = render_page_matching_gather(str(REPO / PDF[t["doc"]]),
                                             t["page"], DPI)
            cache[key] = (cv2.cvtColor(pg.rgb, cv2.COLOR_RGB2BGR), pg.binary)
        rgb, binary = cache[key]
        mb = [float(v) for v in t["mark_bbox_page"]]
        ratio, off, ok = frame_control(binary, mb)
        _r, _o, ok_s = frame_control(binary, mb, shift=(40, 40))
        real += int(ok)
        shifted += int(ok_s)
        space = 25.0 if t["doc"] == "brahms" else 15.5
        hw, hh = int(9 * space), int(9 * space)
        cx, cy = (mb[0] + mb[2]) / 2.0, (mb[1] + mb[3]) / 2.0
        H, W = rgb.shape[:2]
        x0, x1 = max(0, int(cx - hw)), min(W, int(cx + hw))
        y0, y1 = max(0, int(cy - hh)), min(H, int(cy + hh))
        crop = rgb[y0:y1, x0:x1].copy()
        sc = 1000.0 / crop.shape[1]
        crop = cv2.resize(crop, None, fx=sc, fy=sc,
                          interpolation=cv2.INTER_CUBIC)
        box_c = [(mb[0] - x0) * sc, (mb[1] - y0) * sc,
                 (mb[2] - x0) * sc, (mb[3] - y0) * sc]
        bracket(crop, box_c, pad=int(0.45 * space * sc),
                arm=int(0.7 * space * sc), thick=5)
        head_h, foot_h = 140, 80
        img = Image.new("RGB", (crop.shape[1], crop.shape[0] + head_h + foot_h),
                        (255, 255, 255))
        img.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)),
                  (0, head_h))
        dr = ImageDraw.Draw(img)
        dr.text((16, 10), str(t["n"]), font=BIG, fill=(0, 0, 0))
        dr.text((200, 50), DOCNAME[t["doc"]], font=MID, fill=(90, 90, 90))
        dr.text((16, head_h + crop.shape[0] + 16), a.question, font=MID,
                fill=(0, 0, 0))
        fn = "tile_%02d.png" % t["n"]
        img.save(out / fn)
        manifest["tiles"].append({
            "n": t["n"], "file": fn, "doc": t["doc"],
            "pdf_page_index": t["page"], "subject": t["subject"],
            "page_box_600dpi": [int(round(v)) for v in mb],
            "read": t.get("read"), "category": t.get("category"),
            "frame_control": {"ink_ratio": round(ratio, 2),
                              "centroid_offset": [round(off[0], 2),
                                                  round(off[1], 2)],
                              "passes": bool(ok)}})
        print(fn, t["doc"], t["subject"], "pass=%s shifted=%s" % (ok, ok_s))
    manifest["frame_control"] = {
        "tiles": len(sel), "real_box_passes": real,
        "SHIFTED_(40,40)px_box_passes(control, must be low)": shifted}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest["frame_control"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
