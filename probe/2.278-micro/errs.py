import sys, pickle, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import truth as T, groups as G
D = pickle.load(open(sys.argv[1], "rb")); P = D["pages"][0]
d, B, F, S = T.load_truth()
stem_ords = sorted({t["stem"] for t in P["tips"]})
M = T.match_stems(S, P["strokes"], set(stem_ords)); inv = {o: i for i, o in M.items()}
cls = {i: T.classify(S[i], B, F)[0] for i in M}
r = G.read_page(P)
bound = {s for s, x in r["rows"].items() if x["owned"]}
print("WRONG class (bound, truth not beamed):")
for s in sorted(bound):
    if s in inv and cls[inv[s]] != "beamed":
        k = P["strokes"][s]; print("  stem", s, k["bbox"], cls[inv[s]], r["rows"][s])
print("MISSED (truth beamed with row, not bound):")
for i in sorted(i for i, c in cls.items() if c == "beamed"):
    if M[i] not in bound:
        k = P["strokes"][M[i]]; print("  truth stem", i, "stroke", M[i], k["bbox"], r["rows"][M[i]], T.classify(S[i], B, F)[1])
print("BOUND stems with no truth stem:")
for s in sorted(bound):
    if s not in inv:
        k = P["strokes"][s]; print("  stem", s, [round(v) for v in k["bbox"]], "len_sp", round(k["length"], 2), r["rows"][s]["ends"])
print("CERTIFIED strokes not on a truth beam:")
for o in sorted(r["certified"]):
    k = P["strokes"][o]; x0, y0, x1, y1 = k["bbox"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if not any(b["rect"][0] - 16 <= cx <= b["rect"][2] + 16 and b["rect"][1] - 16 <= cy <= b["rect"][3] + 16 for b in B):
        runs = r["certified"][o]
        print("  stroke", o, k["kind"], [round(v) for v in k["bbox"]], "thick", k["thick"], "len", k["length"], "stems", [[t[0] for t in run] for run in runs])
print("TRUTH beams with no certified stroke on them:")
for j, b in enumerate(B):
    hit = [o for o in r["certified"] if (lambda k: b["rect"][0] - 16 <= (k["bbox"][0] + k["bbox"][2]) / 2 <= b["rect"][2] + 16 and b["rect"][1] - 16 <= (k["bbox"][1] + k["bbox"][3]) / 2 <= b["rect"][3] + 16)(P["strokes"][o])]
    if not hit:
        print("  truth beam", j, [round(v) for v in b["rect"]], b["cell_id"])
