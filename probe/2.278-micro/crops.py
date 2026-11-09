"""12 blind crops for Sean (out/print/2.278-micro): one stroke the prototype read (or refused), a thin box on it, both end stems in view. Seeded (278).
usage: python3 probe/2.278-micro/crops.py
"""
import sys, pickle, json, random, collections
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import render as RN, groups as G

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/print/2.278-micro"
OUT.mkdir(parents=True, exist_ok=True)
LIT_PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
rng = random.Random(278)
PL = {"brahms": (pickle.load(open(ROOT / "out/2.278-micro/brahms.pkl", "rb")), RN.PDFS["brahms"]),
      "litolff": (pickle.load(open(ROOT / "out/2.278-micro/litolff.pkl", "rb")), LIT_PDF)}


def levels_of(res, o):
    ls = []
    for run in res["certified"][o]:
        for (s, end, g) in run:
            e = res["rows"][s]["ends"].get(end)
            if e and e["levels"]:
                ls.append(e["levels"])
    return max(ls) if ls else 0


def pool(plate, page, **kw):
    D, _ = PL[plate]
    P = D["pages"][page]
    return P, G.read_page(P, **kw)


def pick_certified(plate, pages, nlev, n):
    cands = []
    for p in pages:
        P, r = pool(plate, p)
        for o, runs in r["certified"].items():
            if levels_of(r, o) == nlev and len({t[0] for run in runs for t in run}) >= 2:
                cands.append((plate, p, o))
    rng.shuffle(cands)
    return cands[:n]


def pick_refused_arc(plate, pages, n):
    cands = []
    for p in pages:
        P, r = pool(plate, p, use_claims=False)
        for o in r["certified"]:
            if P["claimed"].get(o) == "arc":
                cands.append((plate, p, o))
    rng.shuffle(cands)
    return cands[:n]


def pick_refused_single(plate, pages, n):
    cands = []
    for p in pages:
        P, r = pool(plate, p)
        for o, js in r["uncertified"].items():
            k = P["strokes"][o]
            if len({j[0] for j in js}) == 1 and (k["thick"] or 0) >= 0.5 and (k["length"] or 0) >= 1.0 and o not in P["claimed"]:
                cands.append((plate, p, o))
    rng.shuffle(cands)
    return cands[:n]


picks = []
picks += [("read", *c) for c in pick_certified("brahms", [5, 14, 19, 25], 1, 4)]
picks += [("read", *c) for c in pick_certified("brahms", [4, 5, 14, 19, 25], 2, 2)]
picks += [("read", *c) for c in pick_certified("litolff", [2, 4, 6, 16], 1, 1)]
picks += [("read", *c) for c in pick_certified("litolff", [2, 4, 6, 16], 2, 1)]
picks += [("refused_arc", *c) for c in pick_refused_arc("brahms", [0, 5, 14], 2)]
picks += [("refused_single_stem", *c) for c in pick_refused_single("brahms", [5, 14, 19], 1)]
picks.append(("read_false_by_my_look", "brahms", 0, 1206))
rng.shuffle(picks)
key = {}
for i, (kind, plate, page, o) in enumerate(picks, 1):
    D, pdf = PL[plate]
    P = D["pages"][page]
    r = G.read_page(P) if kind != "refused_arc" else G.read_page(P, use_claims=False)
    k = P["strokes"][o]
    img = RN.page_image(pdf, page)
    sp = k["sp"]
    if o in r["certified"]:
        st = sorted({t[0] for run in r["certified"][o] for t in run}, key=lambda s: r["SG"][s]["x"])
    else:
        st = sorted({j[0] for j in r["uncertified"].get(o, [])}, key=lambda s: r["SG"][s]["x"])
    xs = [k["bbox"][0], k["bbox"][2]] + [r["SG"][s]["x"] for s in st]
    ys = [k["bbox"][1], k["bbox"][3]] + [v for s in st for v in (r["SG"][s]["top"], r["SG"][s]["bot"])]
    x0, x1 = min(xs) - 5 * sp, max(xs) + 5 * sp
    y0, y1 = min(ys) - 3.5 * sp, max(ys) + 3.5 * sp
    b = k["bbox"]
    c = RN.crop(img, x0, y0, x1, y1, [dict(rect=[b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3], color=(0, 0, 255))], scale=0.8 if sp > 25 else 1.6, thick=1)
    fn = f"tile_{i:02d}.png"
    cv2.imwrite(str(OUT / fn), c)
    lv = levels_of(r, o) if o in r["certified"] else None
    key[str(i)] = dict(file=fn, plate=plate, page=page, stroke=o, stroke_box_page_px=b, thickness_spaces=k["thick"], length_spaces=k["length"],
                       prototype=kind, stems_joined=len(st), levels_read=lv, question="Is the boxed stroke a beam joining these notes, and how many beams?",
                       claimed_by=P["claimed"].get(o), staff=k.get("staff"))
json.dump(key, open(OUT / "key.json", "w"), indent=1, default=str)
print(json.dumps({i: (v["plate"], v["page"], v["prototype"], v["levels_read"], v["stems_joined"]) for i, v in key.items()}))
