"""ROADMAP 2.175 -- seeded sample of CANDIDATE unison heads (a stem each way) per plate, as contact sheets for my own look.

usage: sample_2_175.py PLATE(lit|bra) ON.json ON.record.json OUTDIR [N=36] [SEED=2175]
  ON.json         the replay's flag-ON result (`unison.rows`: every Q.UNISON_VOICES verdict by glyph subject)
  ON.record.json  its mini record (the glyph boxes in PAGE pixels)
  -> OUTDIR/<plate>_sheet_<k>.png (6 crops per sheet, numbered), OUTDIR/<plate>_sample.json (index -> subject, verdict)
Nothing of ours is drawn except ONE blue box on the head (ours, not Sean's, not evidence)."""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SP = {"lit": 16.0, "bra": 12.5}
BLUE = (31, 111, 235)
NOT_CANDIDATE = ("not_a_unison", "flag_off")


def boxes_of(path):
    rec = json.load(open(path))
    out = {}
    for o in rec["observations"]:
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb and o["subject"] not in out:
            out[o["subject"]] = bb
    return out


def candidates(on_json):
    d = json.load(open(on_json))
    rows = d["unison"]["rows"]
    return {s: r for s, r in rows.items() if r["reason"] not in NOT_CANDIDATE}


def crop(doc, plate, bb, margin_sp=4.5, zoom=2.0):
    m = margin_sp * SP[plate]
    r = (bb[0] - 2.2 * m, bb[1] - m, bb[2] + 2.2 * m, bb[3] + m)
    pix = doc.get_pixmap(matrix=fitz.Matrix(600 / 72 * zoom, 600 / 72 * zoom), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    f = im.width / (r[2] - r[0])
    d = ImageDraw.Draw(im)
    d.rectangle([(bb[0] - r[0]) * f - 2, (bb[1] - r[1]) * f - 2, (bb[2] - r[0]) * f + 2, (bb[3] - r[1]) * f + 2], outline=BLUE, width=3)
    return im


def main():
    plate, on_json, rec_json, outdir = sys.argv[1:5]
    n = int(sys.argv[5]) if len(sys.argv) > 5 else 36
    seed = int(sys.argv[6]) if len(sys.argv) > 6 else 2175
    os.makedirs(outdir, exist_ok=True)
    cand = candidates(on_json)
    boxes = boxes_of(rec_json)
    subs = sorted(s for s in cand if s in boxes)
    random.Random(seed).shuffle(subs)
    pick = subs[:n]
    doc = fitz.open(PDF[plate])
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    ims = []
    index = {}
    for i, s in enumerate(pick, 1):
        page = int(s.split("/")[1])
        im = crop(doc[page], plate, boxes[s])
        cell = Image.new("RGB", (520, 330), "white")
        im.thumbnail((520, 300))
        cell.paste(im, (0, 28))
        ImageDraw.Draw(cell).text((4, 4), "%d  %s" % (i, s.replace("glyph/", "")), fill=(0, 0, 0), font=fnt)
        ims.append(cell)
        index[i] = {"subject": s, "reason": cand[s]["reason"], "outcome": cand[s]["outcome"]}
    for k in range(0, len(ims), 6):
        sheet = Image.new("RGB", (1040, 990), "white")
        for j, c in enumerate(ims[k:k + 6]):
            sheet.paste(c, ((j % 2) * 520, (j // 2) * 330))
        sheet.save(os.path.join(outdir, "%s_sheet_%d.png" % (plate, k // 6 + 1)))
    json.dump({"candidates": len(cand), "with_box": len(subs), "picked": index,
               "by_reason": {r: sum(1 for x in cand.values() if x["reason"] == r) for r in sorted({x["reason"] for x in cand.values()})}},
              open(os.path.join(outdir, "%s_sample.json" % plate), "w"), indent=1)
    print(plate, "candidates", len(cand), "sampled", len(pick))


main()
