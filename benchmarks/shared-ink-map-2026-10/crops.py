"""ROADMAP 2.194 -- crops of reader disagreements for a LOOK (mine, then Sean's if he wants them). Nothing of ours drawn but one
orange box on the head (lane_report's neutral marker). Reads results/disagreements.json + the slices for page boxes; renders the
sample pages once (preprocessing.render_page, 600 dpi, same as lane_report.cut_tiles). Writes out/print/2.194-ink-map/<kind>_<n>.png,
a sheet per kind and key.json (outside the tile folder). Read-only on the tree.
"""
from __future__ import annotations
import json, os, random, sys
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/plan-2.194-ink-map")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged.lane_report import LIB, PLATES

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261020-night"
OUT = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/plan-2.194-ink-map/out/print/2.194-ink-map"
ORANGE = (255, 140, 0)
PER_KIND = {"beams_presence": 3, "fill": 2, "stems_finder_stem_reach_none": 2, "ledgers": 2}   # per plate
SEED = 2194

def page_boxes(plate, wanted):
    boxes = {}
    with open(os.path.join(ROOT, plate, "observations.jsonl"), "rb") as fh:
        for line in fh:
            if b'"glyph_box"' not in line: continue
            o = json.loads(line)
            if o["subject"] in wanted and o["quantity"] == "glyph_box":
                boxes[o["subject"]] = ((o.get("detail") or {}).get("bbox_page_px"), o["value"][0])
    return boxes

def main():
    dis = json.load(open(os.path.join(HERE, "results", "disagreements.json")))
    rng = random.Random(SEED)
    os.makedirs(os.path.join(OUT, "tiles"), exist_ok=True)
    key = []; n = 0
    for plate in ("litolff", "brahms"):
        picks = []
        for kind, k in PER_KIND.items():
            cases = dis[plate]["cases"].get(kind, [])
            for c in rng.sample(cases, min(k, len(cases))): picks.append((kind, c))
        boxes = page_boxes(plate, {c[0] for _k, c in picks})
        pages = {}
        for kind, c in picks:
            s = c[0]; bx, cls = boxes.get(s, (None, None))
            if not bx: continue
            pg = int(s.split("/")[1])
            if pg not in pages:
                pages[pg] = Image.fromarray(render_page(str(LIB / PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
            im = pages[pg]; x0, y0, x1, y1 = bx; w, h = x1 - x0, y1 - y0
            pad = max(w, h) * 2.5
            crop = im.crop((int(x0 - pad), int(y0 - pad), int(x1 + pad), int(y1 + pad)))
            d = ImageDraw.Draw(crop)
            d.rectangle([pad, pad, pad + w, pad + h], outline=ORANGE, width=3)
            scale = 3 if crop.width < 400 else 2
            crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
            n += 1; fn = f"{n:02d}_{plate}_{kind}.png"; crop.save(os.path.join(OUT, "tiles", fn))
            key.append({"tile": n, "file": fn, "plate": plate, "kind": kind, "subject": s, "class": cls, "case": c})
            print(n, plate, kind, s, cls, c[1:])
    json.dump(key, open(os.path.join(OUT, "key.json"), "w"), indent=1)
    # one contact sheet
    tiles = [Image.open(os.path.join(OUT, "tiles", k["file"])) for k in key]
    if tiles:
        tw = 420; th = 420; cols = 5; rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 24)), "white"); dr = ImageDraw.Draw(sheet)
        for i, t in enumerate(tiles):
            t = t.copy(); t.thumbnail((tw, th))
            x, y = (i % cols) * tw, (i // cols) * (th + 24)
            sheet.paste(t, (x, y + 24)); dr.text((x + 4, y + 4), f"{i+1}", fill=(0, 0, 0))
        sheet.save(os.path.join(OUT, "sheet.png"))
    print("wrote", len(key), "tiles to", OUT)

if __name__ == "__main__":
    main()
