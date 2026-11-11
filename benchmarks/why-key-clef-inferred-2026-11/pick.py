"""2.292 seeded selections.   python3 select.py CLS.json OUT_DIR   (CLS = classify.py output over Lall + Ball)
GROUPS (from classify.py causes): G1 crushed count (K1), G2 marker kind (K3, K4), G3 key blocked by an unread clef / clef filled (K6, C*), G4 a right
read or a printed key with no marker box (K2, K7 with fill != 0), G5 blank signature filled 0 (fill 0: K5, K7 with fill 0, K9).
SANITY (my look; 15): random.Random(2921), one pass: every G3 and G4 staff-system first (these are few), then fill up round-robin over G1, G2, G5.
TILES (blind; 12): random.Random(2922); plan per plate: Litolff G1 2, G2 2, G3 2, G4 2, G5 2 (10); Brahms 2 from whichever groups it has (G1, G5 first);
a group short of its quota is topped up from Litolff G1/G2; the 12 are then shuffled with the same RNG. Tiles never repeat a staff-system used in sanity? -- they
may (sanity is not evidence).
"""
import json
import random
import sys

res = json.load(open(sys.argv[1]))
outdir = sys.argv[2]


def group(r, kind):
    c = r["cause"][:2]
    if c == "K5":
        return "G5"
    if kind == "clefs":
        return "G3"
    if c == "K1":
        return "G1"
    if c in ("K3", "K4"):
        return "G2"
    if c == "K6":
        return "G3"
    if c == "K2" or (c == "K7" and r["fill"] != 0):
        return "G4"
    return "G5"


cells = {}
for kind in ("keys", "clefs"):
    for r in res[kind]:
        key = (r["plate"], group(r, kind))
        cells.setdefault(key, [])
        if all(x["staff"] != r["staff"] or x["json"] != r["src"] for x in cells[key]):
            cells[key].append(dict(plate=r["plate"], json=r["src"], staff=r["staff"], bucket="%s %s" % (kind[:-1], r["cause"][:2]), group=group(r, kind)))

print({k: len(v) for k, v in sorted(cells.items())})
rng = random.Random(2921)
san = []
for g in ("G3", "G4"):
    for p in ("litolff", "brahms"):
        san += cells.get((p, g), [])
pools = {k: list(v) for k, v in cells.items() if k[1] in ("G1", "G2", "G5")}
for v in pools.values():
    rng.shuffle(v)
order = sorted(pools)
i = 0
while len(san) < 15 and any(pools.values()):
    k = order[i % len(order)]
    i += 1
    if pools[k]:
        san.append(pools[k].pop())
san = san[:15]
json.dump(san, open(outdir + "/sel_sanity.json", "w"), indent=1)

rng = random.Random(2922)
quota = [("litolff", "G1", 2), ("litolff", "G2", 2), ("litolff", "G3", 2), ("litolff", "G4", 2), ("litolff", "G5", 2)]
tiles = []
used = set()


def take(plate, g, n):
    pool = sorted(cells.get((plate, g), []), key=lambda x: (x["json"], x["staff"]))
    pool = [x for x in pool if (x["json"], x["staff"]) not in used]
    rng.shuffle(pool)
    got = pool[:n]
    for x in got:
        used.add((x["json"], x["staff"]))
    return got


for plate, g, n in quota:
    tiles += take(plate, g, n)
for g in ("G1", "G5", "G2", "G4", "G3"):          # Brahms: first groups that have cases, up to 2 tiles
    need = 2 - len([t for t in tiles if t["plate"] == "brahms"])
    if need > 0:
        tiles += take("brahms", g, need)
for g in ("G1", "G2", "G5", "G4"):
    if len(tiles) >= 12:
        break
    tiles += take("litolff", g, 1)
rng.shuffle(tiles)
json.dump(tiles[:12], open(outdir + "/sel_tiles.json", "w"), indent=1)
print("sanity", len(san), "tiles", len(tiles[:12]), [(t["plate"], t["group"]) for t in tiles[:12]])
