"""ROADMAP 2.288 round 4 -- the lane's OWN look (a lead, never evidence: rule 7): every whole/half rest claim of one page of an ON record on one contact sheet, claimed ink tinted blue, staff line
not tinted, the box thin, a number in the corner. Sean's blind tiles are the evidence.

    python3 benchmarks/rests-claim-first-2026-11/contact_sheet_r4.py RECORD PDF PAGE OUT.png
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, ".")
import numpy as np
from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page

HERE = pathlib.Path(__file__).parent
_s = importlib.util.spec_from_file_location("t4", HERE / "tiles_288_r4.py")
T4 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(T4)
T3 = T4.T3


def main():
    rec, pdf, page, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    claims, strokes = T4.claims_of(rec, [page])
    sts = strokes[page]
    img = render_page(pdf, page, 600)
    sps = [d["staff_space_local_px"] for d in sts.values() if d.get("staff_space_local_px")]
    sp = float(np.median(sps))
    tiles = []
    for n, (k, c) in enumerate(sorted(claims.items()), 1):
        sbs = [sts[j]["bbox_page_px"] for j in c["ids"] if j in sts]
        if not sbs:
            continue
        box = [min(b[0] for b in sbs), min(b[1] for b in sbs), max(b[2] for b in sbs), max(b[3] for b in sbs)]
        t = T3.tile(img, box, sbs, sp)
        w, h = t.size
        t = t.crop((w // 2 - 130, h // 2 - 75, w // 2 + 130, h // 2 + 75))
        ImageDraw.Draw(t).text((3, 2), "%d %s %s" % (n, c["cls"][4:], c["subject"][5:]), fill=(200, 0, 0))
        tiles.append(t)
    cols = 8
    sheet = Image.new("RGB", (cols * 260, ((len(tiles) + cols - 1) // cols) * 150), (255, 255, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 260, (i // cols) * 150))
    sheet.save(out)
    print(len(tiles), "claims")


if __name__ == "__main__":
    main()
