import sys, pickle, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import truth as T, groups as G
D = pickle.load(open(sys.argv[1], "rb")); P = D["pages"][0]
d, B, F, S = T.load_truth()
stem_ords = sorted({t["stem"] for t in P["tips"]})
M = T.match_stems(S, P["strokes"], set(stem_ords)); inv = {o: i for i, o in M.items()}
beamed = {i for i in M if T.classify(S[i], B, F)[0] == "beamed"}
def run(label, **kw):
    r = G.read_page(P, **kw)
    bound = {s for s, x in r["rows"].items() if x["owned"]}
    bt = {inv[s] for s in bound if s in inv}; tp = len(bt & beamed)
    print(f"{label:34s} bound {len(bound):3d} matched {len(bt):3d} precision {tp}/{len(bt)} = {tp/max(1,len(bt)):.3f}  coverage {tp}/{len(beamed)} = {tp/len(beamed):.3f}  strokes {len(r['certified'])}")
run("no shift")
for dy in (12, -12, 24, -24, 48, -48, 96):
    run(("PRE-REG" if abs(dy) == 12 else "extra") + f": vertical {dy:+d} px", shift_px=float(dy))
for dx in (12, -12, 24, 48):
    run(f"extra: horizontal {dx:+d} px", shift_x=float(dx))
print("--- what protects precision: the claims, or the two-stem rule (extra, not pre-registered)")
run("claims on, two-stem on (reader)")
run("claims on, two-stem OFF", two_stem=False)
run("claims OFF, two-stem on", use_claims=False)
run("claims OFF, two-stem OFF", use_claims=False, two_stem=False)
import json
def nontruth(res):
    out = []
    for o in res["certified"]:
        k = P["strokes"][o]; x0, y0, x1, y1 = k["bbox"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if not any(b["rect"][0] - 16 <= cx <= b["rect"][2] + 16 and b["rect"][1] - 16 <= cy <= b["rect"][3] + 16 for b in B):
            out.append(o)
    return out
for lab, kw in (("reader", {}), ("two-stem OFF", dict(two_stem=False)), ("claims OFF", dict(use_claims=False)), ("claims OFF + two-stem OFF", dict(use_claims=False, two_stem=False))):
    r = G.read_page(P, **kw); nt = nontruth(r)
    cl = collections.Counter(P["claimed"].get(o, "unclaimed") for o in nt)
    print(f"{lab:28s} certified strokes not on a truth beam: {len(nt):4d}  by claim owner: {dict(cl)}")
