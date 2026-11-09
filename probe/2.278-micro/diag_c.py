"""POST-HOC DIAGNOSTIC (variant C, NOT the test): the same group reader with the old per-stroke shape + thickness test restored (kind horizontal, thickness >= 0.5 sp).
Shows what the two-stem rule alone lets in. usage: python3 probe/2.278-micro/diag_c.py brahms|litolff"""
import sys, pickle, json, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import truth as T, groups as G, heads as H
from tools.omr.staged import judged as J
plate = sys.argv[1]
D = pickle.load(open(f"out/2.278-micro/{plate}.pkl", "rb"))
pages = sorted(D["pages"])
for diag in (False, True):
    for win in ("A", "B2"):
        out = H.run(D, pages, window=win, diag_shape=diag)
        c = collections.Counter(o["status"] for o in out)
        print(f"diag_shape={diag!s:5} window {win:2}: narrowed {len(out)} decided {c['beam'] + c['plain']} ({(c['beam'] + c['plain']) / len(out):.3f}) beam-owned {c['beam']} plain {c['plain']}")
if plate == "brahms":
    P = D["pages"][0]
    d, B, F, S = T.load_truth()
    M = T.match_stems(S, P["strokes"], {t["stem"] for t in P["tips"]}); inv = {o: i for i, o in M.items()}
    beamed = {i for i in M if T.classify(S[i], B, F)[0] == "beamed"}
    for diag in (False, True):
        r = G.read_page(P, diag_shape=diag)
        bound = {s for s, x in r["rows"].items() if x["owned"]}
        bt = {inv[s] for s in bound if s in inv}; tp = len(bt & beamed)
        print(f"bar1 diag_shape={diag!s:5}: precision {tp}/{len(bt)} = {tp / len(bt):.3f} coverage {tp}/{len(beamed)} = {tp / len(beamed):.3f} certified strokes {len(r['certified'])}")
