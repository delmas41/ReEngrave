"""Blind tiles: the bar outlined in blue on its staff (named), nothing of ours drawn.
python3 tiles.py <outdir> <arm litolff record> <arm brahms record> <doc:cell> [<doc:cell> ...]"""
import sys, os, json
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3034cd5523b00cbf")
import fitz
from PIL import Image, ImageDraw, ImageFont
from tools.omr.staged import readout
out_dir = sys.argv[1]
RECS = {"litolff": sys.argv[2], "brahms": sys.argv[3]}
TITLES = {"litolff": "Beethoven 5 (Litolff)", "brahms": "Brahms 1 (Breitkopf)"}
os.makedirs(out_dir, exist_ok=True)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
runs = {d: readout.load_run(p) for d, p in RECS.items()}
docs = {d: fitz.open(r.pdf) for d, r in runs.items()}
man = []
for n, spec in enumerate(sys.argv[4:], 1):
    d, cell = spec.split(":")
    run = runs[d]
    _, p, sy, st, c = cell.split("/")
    x0, y0, x1, y1 = run.obs_at(cell, "cell_box")[0]["value"]
    lines = run.obs_at(f"staff/{p}/{sy}/{st}", "staff_lines")[0]["value"]
    sp = (lines[-1] - lines[0]) / 4.0
    inst = (run.standing(f"staff/{p}/{sy}/{st}", "instrument", "ADJUDICATE") or {}).get("value") or {}
    name = inst.get("name") if isinstance(inst, dict) else None
    cx0, cx1 = x0 - 6 * sp, x1 + 6 * sp
    cy0, cy1 = lines[0] - 9 * sp, lines[-1] + 9 * sp
    Z = 2 if sp < 25 else 1
    clip = fitz.Rect(cx0 * 72 / 600, cy0 * 72 / 600, cx1 * 72 / 600, cy1 * 72 / 600)
    pix = docs[d][int(p)].get_pixmap(dpi=600 * Z, clip=clip)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    dr = ImageDraw.Draw(im)
    dr.rectangle([(x0 - cx0) * Z, (lines[0] - cy0 - sp) * Z, (x1 - cx0) * Z, (lines[-1] - cy0 + sp) * Z], outline=(30, 90, 230), width=5)
    out = Image.new("RGB", (im.width, im.height + 100), "white"); out.paste(im, (0, 100)); dd = ImageDraw.Draw(out)
    dd.text((10, 8), f"Dynamics tile {n} -- {TITLES[d]}, page {int(p) + 1}", fill="black", font=font)
    dd.text((10, 50), f"Blue box = one bar on the {name or 'unnamed'} staff", fill=(30, 90, 230), font=font)
    f = f"dyn_{n:02d}.png"
    out.save(os.path.join(out_dir, f))
    man.append({"n": n, "doc": d, "cell": cell, "staff_name": name, "file": f})
json.dump({"question": "What dynamic markings are printed for this staff in the blue bar?", "tiles": man},
          open(os.path.join(out_dir, "manifest.json"), "w"), indent=1)
print(len(man), "tiles")
