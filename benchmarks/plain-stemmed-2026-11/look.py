"""Part 0b look sheets: 40 seeded cases per plate from the no-flag-no-beam population; target orange, chord mates blue."""
import json, random, sys, collections
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, "benchmarks/note-loss-funnel-2026-11")
from checksheet import page_image

S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad"
POP = json.load(open(S + "/p314/pop.json"))
OUTD = Path(S + "/p314/look")
OUTD.mkdir(exist_ok=True)
ORANGE, BLUE = (255, 140, 0), (30, 90, 255)
W = 760
facts = {p: json.load(open(f"{S}/2311/{t}.facts.json"))["glyphs"] for p, t in (("litolff", "lit-a"), ("brahms", "bra-a"))}
extra = {p: json.load(open(f"{S}/2311/{t}.extra.json")) for p, t in (("litolff", "lit-a"), ("brahms", "bra-a"))}


def render(plate, r):
    it = r["it"]
    page, system, staff = it["page"], it["system"], it["staff"]
    lines = extra[plate]["staff_lines"]["%d/%d/%d" % (page, system, staff)]
    sp = (lines[4] - lines[0]) / 4.0
    im = page_image(plate, page)
    boxes = [(it["head_box"], ORANGE)]
    sb = it.get("stem_box")
    if sb:
        boxes.append((sb, ORANGE))
    for m in r["mates"]:
        gm = facts[plate][m["key"]]
        boxes.append((gm["box"], BLUE))
    xs = [b[0] for b, _ in boxes] + [b[2] for b, _ in boxes]
    ys = [b[1] for b, _ in boxes] + [b[3] for b, _ in boxes]
    top = min(min(ys) - 2.5 * sp, lines[0] - 1.5 * sp)
    bot = max(max(ys) + 2.5 * sp, lines[4] + 1.5 * sp)
    cx = (min(xs) + max(xs)) / 2
    cw = max(16 * sp, (max(xs) - min(xs)) + 4 * sp)
    X0, X1, Y0, Y1 = int(cx - cw / 2), int(cx + cw / 2), int(top), int(bot)
    canvas = Image.new("RGB", (X1 - X0, Y1 - Y0), (255, 255, 255))
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(im.width, X1), min(im.height, Y1)
    canvas.paste(im.crop((sx0, sy0, sx1, sy1)), (sx0 - X0, sy0 - Y0))
    s = W / canvas.width
    crop = canvas.resize((W, int(round(canvas.height * s))), Image.LANCZOS)
    d = ImageDraw.Draw(crop)
    for b, col in boxes[::-1]:
        d.rectangle([round((b[0] - X0) * s), round((b[1] - Y0) * s), round((b[2] - X0) * s), round((b[3] - Y0) * s)], outline=col, width=2)
    return crop


def sheet(tiles, labels, out, cols=2):
    Wt = max(t.width for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    rh = [max(t.height for t in tiles[r * cols:(r + 1) * cols]) for r in range(rows)]
    sh = Image.new("RGB", (cols * (Wt + 12) + 12, sum(h + 30 for h in rh) + 12), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    y = 12
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(tiles):
                continue
            x = 12 + c * (Wt + 12)
            d.text((x, y + 4), labels[i], fill=(0, 0, 0))
            sh.paste(tiles[i], (x, y + 22))
        y += rh[r] + 30
    sh.save(out)


sel = {}
for plate in ("litolff", "brahms"):
    pop = sorted(POP[plate], key=lambda r: r["it"]["key"])
    rng = random.Random(2314)
    sel[plate] = rng.sample(pop, 40)
key = []
n = 0
for plate in ("litolff", "brahms"):
    rows = sel[plate]
    for s0 in range(0, 40, 6):
        imgs, labs = [], []
        for r in rows[s0:s0 + 6]:
            n += 1
            imgs.append(render(plate, r))
            labs.append("%s#%d %s p%d" % (plate[:3], rows.index(r) + 1, r["it"]["key"], r["it"]["page"]))
            key.append(dict(plate=plate, n=rows.index(r) + 1, key=r["it"]["key"]))
        sheet(imgs, labs, OUTD / ("%s_%02d.png" % (plate, s0 // 6 + 1)))
json.dump(key, open(OUTD / "key.json", "w"))
json.dump({p: [r["it"]["key"] for r in v] for p, v in sel.items()}, open(OUTD / "sel.json", "w"))
print("ok", n)
