"""ARC CURVE-ONLY TEST: crops of NEW writes (written ON, not OFF). One staff window; the WHOLE arc (traced extent) boxed in thin orange; both bound
notes inside the window; nothing else of ours drawn. The bound heads / kind go in key.json, never into the pictures. Measure only.

    python3 cut_new_crops.py OUTDIR  PLATE:CMP.json:ON.arcs.json [...]   (8 crops in all, drawn at random, seed 2188, alternating plates)
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crops as C      # noqa: E402
from PIL import ImageDraw   # noqa: E402

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
pools = {}
for arg in sys.argv[2:]:
    plate, cmpf, arcs = arg.split(":")
    cmp_ = json.load(open(cmpf))
    dump = json.load(open(arcs))
    heads = {h["subject"]: h["box"] for h in dump["heads"]}
    rows = [r for r in cmp_["new"] if r.get("pair")]
    pools[plate] = (rows, heads)
rng = random.Random(2188)
picks = []
plates = list(pools)
for pl in plates:
    rng.shuffle(pools[pl][0])
i = 0
while len(picks) < 8 and any(pools[pl][0] for pl in plates):
    pl = plates[i % len(plates)]
    i += 1
    if pools[pl][0]:
        picks.append((pl, pools[pl][0].pop()))
key = []
for n, (plate, r) in enumerate(picks, 1):
    heads = pools[plate][1]
    sp = r["sp"]
    box = list(r["box"])
    if r.get("x_left") is not None:
        box[0], box[2] = min(box[0], r["x_left"]), max(box[2], r["x_right"])
    pr = r["pair"]
    hb = [heads[k] for k in pr if k in heads]
    wx0 = min([box[0]] + [b[0] for b in hb]) - 2 * sp
    wx1 = max([box[2]] + [b[2] for b in hb]) + 2 * sp
    wy0 = min([box[1]] + [b[1] for b in hb]) - 4 * sp
    wy1 = max([box[3]] + [b[3] for b in hb]) + 4 * sp
    im = C.page_image(plate, r["page"])
    W, H = im.size
    win = (max(0, int(wx0)), max(0, int(wy0)), min(W, int(wx1)), min(H, int(wy1)))
    c = im.crop(win).copy()
    d = ImageDraw.Draw(c)
    t = max(2, int(sp * 0.12))
    bx = (box[0] - 0.3 * sp - win[0], box[1] - 0.3 * sp - win[1], box[2] + 0.3 * sp - win[0], box[3] + 0.3 * sp - win[1])
    for k in range(t):
        d.rectangle((bx[0] - k, bx[1] - k, bx[2] + k, bx[3] + k), outline=C.ORANGE)
    if c.width > 1500:
        from PIL import Image
        c = c.resize((1500, int(c.height * 1500 / c.width)), Image.LANCZOS)
    c.save(out / ("%02d.png" % n))
    key.append(dict(n=n, plate=plate, page=r["page"], curve=r["curve"], pieces=r["pieces"], kind=r.get("kind"), pair=list(pr), ext_gap=r.get("ext_gap"),
                    binding={k: v for k, v in (r.get("binding") or {}).items() if k in ("relation", "between", "rule", "split", "group", "side")}))
(out / "key.json").write_text(json.dumps(key, indent=1, default=str))
print("wrote", len(key), "crops to", out)
