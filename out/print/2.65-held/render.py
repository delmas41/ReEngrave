"""ROADMAP 2.65: the eight 09-29 held-bar tiles (`benchmarks/omr-bar-sum-holdout-2026-09/out/print/held-2026-09-29-*`),
re-cut BLIND from Brahms 1 Breitkopf pdf page 1: the bar outlined in blue on its staff, staff named, nothing of ours drawn.
Cell boxes from today's small re-gather (main 404285f3). Usage: render.py <brahms p1 record>"""
import json, os, sys
import fitz
from PIL import Image, ImageDraw, ImageFont
from tools.omr.staged import readout
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "../../../benchmarks/omr-bar-sum-holdout-2026-09/out/print/held-2026-09-29-manifest.json")
PDF = os.path.join(HERE, "../../../library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
run = readout.load_run(sys.argv[1]); doc = fitz.open(PDF)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
man = []
for t in json.load(open(SRC)):
    k = t["cell"]; _, p, sy, st, c = k.split("/")
    x0, y0, x1, y1 = run.obs_at(k, "cell_box")[0]["value"]
    lines = run.obs_at(f"staff/{p}/{sy}/{st}", "staff_lines")[0]["value"]
    sp = (lines[-1] - lines[0]) / 4.0
    inst = (run.standing(f"staff/{p}/{sy}/{st}", "instrument", "ADJUDICATE") or {}).get("value") or {}
    name = inst.get("name") if isinstance(inst, dict) else None
    cx0, cx1 = x0 - 6 * sp, x1 + 6 * sp; cy0, cy1 = lines[0] - 8 * sp, lines[-1] + 8 * sp
    clip = fitz.Rect(cx0 * 72 / 600, cy0 * 72 / 600, cx1 * 72 / 600, cy1 * 72 / 600)
    pix = doc[int(p)].get_pixmap(dpi=600, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples); d = ImageDraw.Draw(im)
    d.rectangle([x0 - cx0, lines[0] - cy0 - sp, x1 - cx0, lines[-1] - cy0 + sp], outline=(30, 90, 230), width=5)
    out = Image.new("RGB", (im.width, im.height + 100), "white"); out.paste(im, (0, 100)); dd = ImageDraw.Draw(out)
    dd.text((10, 8), f"Held-bar tile {t['n']} of 8 -- Brahms 1 (Breitkopf), page {int(p) + 1}", fill="black", font=font)
    dd.text((10, 50), f"Blue box = one bar on the {name or 'unnamed'} staff", fill=(30, 90, 230), font=font)
    f = f"held_{t['n']}.png"; out.save(os.path.join(HERE, f))
    man.append({"n": t["n"], "cell": k, "staff_name": name, "file": f, "record_says_0929": t["record_says"]})
json.dump({"question": "What does this staff print in the blue bar?", "tiles": man}, open(os.path.join(HERE, "manifest.json"), "w"), indent=1)
print(len(man))
