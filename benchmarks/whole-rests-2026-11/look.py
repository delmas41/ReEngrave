import json, sys, os, pickle
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/note-loss-funnel-2026-11")
from redbars_tiles import staff_geometry
from redbars_tiles_more import draw_tile, sheet

S = sys.argv[1]
L = json.load(open(S + "/looked315.json"))
F = {"litolff": "lit-a", "brahms": "bra-a"}
geo = {}
gp = S + "/geo315.pkl"
if os.path.exists(gp):
    geo = pickle.load(open(gp, "rb"))
for plate in L:
    if plate in geo:
        continue
    wanted = set()
    for b in L[plate]["looked"]:
        wanted.add("staff/%d/%d/%d" % (b["page"], b["system"], b["staff"]))
        wanted.add("cell/%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"]))
    geo[plate] = staff_geometry(S + "/2311/%s.record.json" % F[plate], wanted)
    pickle.dump(geo, open(gp, "wb"))
print("geo done")
os.makedirs(S + "/look315", exist_ok=True)
for plate in L:
    f = json.load(open(S + "/2311/%s.facts.json" % F[plate]))
    bs = L[plate]["looked"]
    for i in range(0, len(bs), 6):
        tiles = []
        for b in bs[i:i + 6]:
            crop, _ = draw_tile(plate, f, geo[plate], b, nout=900)
            tiles.append(crop)
        sheet(tiles, S + "/look315/%s-%02d.png" % (plate, i // 6), cols=2, W=900)
    print(plate, "sheets", (len(bs) + 5) // 6)
