"""2.306 r14, MY look (leads, not Sean's): crops of Brahms p0 around Sean's labelled heads (truth ids), each drawn with HIS head (blue) and his
stem (green, the one judge.py attaches), and the page stem the record holds for the written glyph there (orange, `Q.PAGE_STEM` stem_box).
Several crops side by side in one PNG.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/page-ledger-2026-11/2306/r14_look.py PAGE.png REC.record.json FACTS.json OUT.png q1,q2,...
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

import judge as J
from tools.omr.staged.judged import boxes_overlap
from tools.omr.staged.record_io import load_record

page_png, rec_p, facts_p, out_p, ids = sys.argv[1:6]
ids = ids.split(",")
facts = json.load(open(facts_p))
rec = load_record(rec_p)["record"]
pstem = {}
for o in rec["observations"]:
    if o["quantity"] == "page_stem":
        pstem[o["subject"]] = (o.get("detail") or {}).get("stem_box")
pstem_ab = {}
for a in rec.get("abstentions") or ():
    if a.get("quantity") == "page_stem":
        d = a.get("detail") or {}
        pstem_ab[a["subject"]] = d.get("how") or d.get("note")
page, truth, u, in_scope, swept = J.load_truth(J.TRUTH)
heads, att = J.attach(truth, u)
w = [h for h in facts["written"] if h["page"] == 0 and h["kind"] == "note"]
img = Image.open(page_png).convert("RGB")
tiles = []
for t in heads:
    if t.id not in ids:
        continue
    a = att[t.id]
    im = img.copy()
    dr = ImageDraw.Draw(im)
    r = t.rect
    dr.rectangle([r[0] - 3, r[1] - 3, r[2] + 3, r[3] + 3], outline=(0, 0, 255), width=3)
    if a["stem"] is not None:
        s = a["stem"].rect
        dr.rectangle([s[0] - 4, s[1], s[2] + 4, s[3]], outline=(0, 170, 0), width=2)
    best = max(((boxes_overlap(h["box"], r)[1], i) for i, h in enumerate(w) if boxes_overlap(h["box"], r)[0]), default=None)
    label = t.id
    if best:
        rg = w[best[1]]["rg"]
        sb = pstem.get(rg)
        if sb:
            dr.rectangle([sb[0] - 8, sb[1] - 2, sb[2] + 8, sb[3] + 2], outline=(255, 140, 0), width=3)
        label += " " + rg + " " + str(pstem_ab.get(rg) or "")
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    crop = im.crop((int(cx - 7 * u), int(cy - 7 * u), int(cx + 7 * u), int(cy + 7 * u)))
    ImageDraw.Draw(crop).text((4, 4), label, fill=(200, 0, 0))
    tiles.append(crop)
if tiles:
    W = sum(t.width for t in tiles[:4])
    rows = [tiles[i:i + 4] for i in range(0, len(tiles), 4)]
    out = Image.new("RGB", (W, rows and sum(max(t.height for t in rw) for rw in rows)), "white")
    y = 0
    for rw in rows:
        x = 0
        for t in rw:
            out.paste(t, (x, y))
            x += t.width
        y += max(t.height for t in rw)
    out.save(out_p)
print(len(tiles), "crops")
