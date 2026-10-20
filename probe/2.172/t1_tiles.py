"""2.172 blind tiles for Sean: ONE blue box on the item asked about, nothing of ours drawn. Tiles and key come from THIS ONE RUN; `--check` re-reads
both and verifies they are equal (count, names, sha256 of every png).
Selection: new boxes the ON arm's view found (reader yolo_detector_view) on the re-gathered pages, none of them judged by Sean (a view box is new, so its
glyph id cannot be in judged-tiles), stratified over plate x family, seeded; plus 2 controls: (1) a production black head at conf >= 0.8 (answer: notehead),
(2) a blank spot inside a staff, 3+ staff spaces from every box (answer: other / nothing).
usage: t1_tiles.py            -> out/print/2.172-review/tile_NN.png, key.json (key is NOT for Sean)
       t1_tiles.py --check"""
import hashlib
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
REC = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-2.172")
OUT = ROOT / "out/print/2.172-review"
PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
BLUE_RGB = (0x1F, 0x6F, 0xEB)
SEED = 2172
KEY = ROOT / "probe/2.172/data/tiles_key.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check():
    key = json.load(open(KEY))
    pngs = sorted(p.name for p in OUT.glob("tile_*.png"))
    names = sorted(t["file"] for t in key["tiles"])
    assert pngs == names, ("tiles and key differ in names", pngs, names)
    for t in key["tiles"]:
        assert sha(OUT / t["file"]) == t["sha256"], ("png changed after the key was written", t["file"])
    print("OK: %d tiles, key equal (names and sha256)" % len(pngs))


def load(plate):
    d = json.loads(open(REC / ("%s-on.record.json" % plate)).read())
    R = d["record"]
    rows = []
    for o in R["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/"):
            det = o.get("detail") or {}
            rows.append(dict(sub=o["subject"], cls=o["value"][0], conf=o.get("score"), bbox=det.get("bbox_page_px"), reader=o.get("reader"),
                             view=det.get("view"), family=det.get("family"), phases=det.get("phases_found")))
    return rows


def main():
    rnd = random.Random(SEED)
    cands = []
    prod_heads = {}
    allbox = {}
    for plate in ("lit", "bra"):
        rows = load(plate)
        allbox[plate] = [r for r in rows if r["bbox"]]
        for r in rows:
            if not r["bbox"]:
                continue
            if r["reader"] == "yolo_detector_view":
                cands.append(dict(plate=plate, **r))
            elif r["reader"] == "detector" and r["cls"].startswith("noteheadBlack") and (r["conf"] or 0) >= 0.8:
                prod_heads.setdefault(plate, []).append(dict(plate=plate, **r))
    strata = {}
    for c in cands:
        strata.setdefault((c["plate"], c["family"]), []).append(c)
    for v in strata.values():
        rnd.shuffle(v)
    print({k: len(v) for k, v in sorted(strata.items())})
    chosen = []
    keys = sorted(strata)
    while len(chosen) < 10 and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(chosen) < 10:
                chosen.append(strata[k].pop())
    items = [dict(c, role="new_view_box", asked="what is the symbol in the blue box") for c in chosen]
    ph = prod_heads.get("lit", []) + prod_heads.get("bra", [])
    h = rnd.choice(ph)
    items.append(dict(h, role="control_production_head"))
    # blank control: a point inside a staff of a Brahms/Litolff cell, 3+ spaces from every box
    plate = rnd.choice(["lit", "bra"])
    boxes = allbox[plate]
    pg = int(boxes[0]["sub"].split("/")[1])
    blank_pages = {}
    for _ in range(2000):
        b0 = rnd.choice([b for b in boxes if b["cls"].startswith("notehead")])
        w = b0["bbox"][2] - b0["bbox"][0]
        sp = w / 1.3
        cx = b0["bbox"][0] + rnd.uniform(-8, 8) * sp
        cy = (b0["bbox"][1] + b0["bbox"][3]) / 2 + rnd.uniform(-2, 2) * sp
        pgi = int(b0["sub"].split("/")[1])
        if (plate, pgi) not in blank_pages:
            from tools.omr.preprocessing import render_page
            blank_pages[(plate, pgi)] = render_page(PDF[plate], pgi, dpi=600).rgb
        win = blank_pages[(plate, pgi)][int(cy - 2.5 * sp):int(cy + 2.5 * sp), int(cx - 2.5 * sp):int(cx + 2.5 * sp)]
        ink = float((win.mean(axis=2) < 128).mean()) if win.size else 0.0
        if not (0.04 <= ink <= 0.3):
            continue    # a blank control must sit among staff lines, not in the white margin
        if all(abs((bb["bbox"][0] + bb["bbox"][2]) / 2 - cx) > 3 * sp or abs((bb["bbox"][1] + bb["bbox"][3]) / 2 - cy) > 3 * sp for bb in boxes):
            items.append(dict(plate=plate, sub=b0["sub"], cls="(blank)", conf=None, bbox=[cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2],
                              reader=None, view=None, family=None, phases=None, role="control_blank"))
            break
    rnd.shuffle(items)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("tile_*.png"):
        p.unlink()
    pages = {}
    tiles = []
    for i, it in enumerate(items, 1):
        pg = int(it["sub"].split("/")[1])
        k = (it["plate"], pg)
        if k not in pages:
            from tools.omr.preprocessing import render_page
            pages[k] = render_page(PDF[it["plate"]], pg, dpi=600).rgb
        img = pages[k]
        x0, y0, x1, y1 = it["bbox"]
        w = max(x1 - x0, 1.0)
        sp = 15.5 if it["plate"] == "lit" else 16.0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        half = int(7 * sp)
        X0, Y0 = int(cx - 1.5 * half), int(cy - half)
        X1, Y1 = int(cx + 1.5 * half), int(cy + half)
        crop = img[max(0, Y0):Y1, max(0, X0):X1].copy()
        sc = 3
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        pad = 0.15 * sp
        bx0, by0 = int((x0 - pad - max(0, X0)) * sc), int((y0 - pad - max(0, Y0)) * sc)
        bx1, by1 = int((x1 + pad - max(0, X0)) * sc), int((y1 + pad - max(0, Y0)) * sc)
        cv2.rectangle(crop, (bx0, by0), (bx1, by1), BLUE_RGB, 2)
        f = "tile_%02d.png" % i
        cv2.imwrite(str(OUT / f), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        tiles.append(dict(file=f, plate=it["plate"], page=pg, role=it["role"], subject=it["sub"], cls=it["cls"], conf=it["conf"], view=it["view"],
                          family=it["family"], phases_found=it["phases"], bbox=it["bbox"], sha256=sha(OUT / f)))
    json.dump(dict(seed=SEED, tiles=tiles), open(KEY, "w"), indent=1)
    (OUT / "README.md").write_text(
        "# 2.172: what is the symbol in the blue box? (%d tiles, blind)\n\n"
        "One question for every tile: **what is the symbol inside the blue box** -- dot (augmentation dot), flag, rest (say which), notehead, or other?\n\n"
        "Each tile is a crop of the printed page with a single blue frame. Nothing of ours is drawn on it. Some frames sit on a real symbol and some on nothing at all; "
        "say what you see, not what you expect.\n\nTiles: `tile_01.png` .. `tile_%02d.png`. (Our key is kept apart, in the lane's probe data.)\n" % (len(tiles), len(tiles)))
    print("wrote", len(tiles), "tiles")
    check()


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
