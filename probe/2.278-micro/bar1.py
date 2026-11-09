"""Bar 1: Brahms p0 hand truth. precision = bound stems that are truth-beamed / bound stems that match a truth stem; coverage = truth-beamed stems
(that have a stem row) bound. Controls: shift 12 px; no two-stem rule. Comparators on the same stems: the landed M4a tip reading, the cell reader.

usage: python3 probe/2.278-micro/bar1.py out/2.278-micro/brahms.pkl [--dump out.json]
"""
import sys, pickle, json, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import truth as T
import groups as G

D = pickle.load(open(sys.argv[1], "rb"))
P = D["pages"][0]
d, B, F, S = T.load_truth()
stem_ords = sorted({t["stem"] for t in P["tips"]})
M = T.match_stems(S, P["strokes"], set(stem_ords))
cls = {i: T.classify(S[i], B, F)[0] for i in M}
inv = {o: i for i, o in M.items()}      # stem stroke -> truth stem index
beamed_truth = {i for i, c in cls.items() if c == "beamed"}


def score(res, label):
    bound = {s for s, r in res["rows"].items() if r["owned"]}
    bound_truth = {inv[s] for s in bound if s in inv}
    nt = len(bound) - len(bound_truth)
    tp = len(bound_truth & beamed_truth)
    prec = tp / len(bound_truth) if bound_truth else float("nan")
    cov = tp / len(beamed_truth)
    wrong = sorted(bound_truth - beamed_truth)
    n_strokes = len(res["certified"])
    truth_beam_hit = collections.Counter()
    print(f"{label:34s} bound stems {len(bound):3d} (matched to truth {len(bound_truth)}, no truth stem {nt})  precision {tp}/{len(bound_truth)} = {prec:.3f}  "
          f"coverage {tp}/{len(beamed_truth)} = {cov:.3f}  certified strokes {n_strokes}  wrong-class: {collections.Counter(cls[i] for i in wrong)}")
    return dict(bound=bound, bound_truth=bound_truth, wrong=wrong, prec=prec, cov=cov, strokes=set(res["certified"]))


base = G.read_page(P)
r0 = score(base, "GROUP READER (certified, 2 stems)")
sh12 = G.read_page(P, shift_px=12.0)
score(sh12, "control: every stroke shifted +12 px")
sh12b = G.read_page(P, shift_px=-12.0)
score(sh12b, "control: every stroke shifted -12 px")
no2 = G.read_page(P, two_stem=False)
r2 = score(no2, "control: two-stem rule removed")

# comparators on the same stems
tipbeamed = collections.defaultdict(bool)
for t in P["tips"]:
    if t["stem_beamed"]:
        tipbeamed[t["stem"]] = True
m4 = {s for s, v in tipbeamed.items() if v}
m4_truth = {inv[s] for s in m4 if s in inv}
tp = len(m4_truth & beamed_truth)
print(f"{'M4a landed tip reading stem_beamed':34s} bound {len(m4)} matched {len(m4_truth)} precision {tp}/{len(m4_truth)} = {tp/max(1,len(m4_truth)):.3f} coverage {tp}/{len(beamed_truth)} = {tp/len(beamed_truth):.3f}")
cl = D["cell_levels"]
cellb = set()
for t in P["tips"]:
    for r in t["stem_rows"]:
        if cl.get(r, 0) and cl[r] >= 1:
            cellb.add(t["stem"])
c_truth = {inv[s] for s in cellb if s in inv}
tp = len(c_truth & beamed_truth)
print(f"{'cell reader beam_stem_levels>=1':34s} bound {len(cellb)} matched {len(c_truth)} precision {tp}/{len(c_truth)} = {tp/max(1,len(c_truth)):.3f} coverage {tp}/{len(beamed_truth)} = {tp/len(beamed_truth):.3f}")

# what does the no-two-stem control admit: strokes not touching a truth beam box
def stroke_in_truth_beam(o):
    k = P["strokes"][o]
    x0, y0, x1, y1 = k["bbox"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return any(b["rect"][0] - 16 <= cx <= b["rect"][2] + 16 and b["rect"][1] - 16 <= cy <= b["rect"][3] + 16 for b in B)

def nontruth_strokes(res):
    return sorted(o for o in res["certified"] if not stroke_in_truth_beam(o))

print("non-truth certified strokes: group reader", len(nontruth_strokes(base)), "| no-two-stem control", len(nontruth_strokes(no2)),
      "| of which kinds", collections.Counter(P["strokes"][o]["kind"] for o in nontruth_strokes(no2)))
# the M4a-filed beams that are not on a truth beam
m4a_beams = [b for b in P["pbeams"] if b["role"] == "beam"]
print("M4a role=beam strokes", len(m4a_beams), "not on a truth beam:", sum(1 for b in m4a_beams if not stroke_in_truth_beam(b["ordinal"])))
print("certified strokes", len(base["certified"]), "truth beams", len(B), " | claimed horizontal/curve strokes skipped", base["claimed_skipped"], "cut by barline", base["cut_by_bar"])
if "--dump" in sys.argv:
    out = sys.argv[sys.argv.index("--dump") + 1]
    json.dump(dict(wrong=r0["wrong"], missed=sorted(beamed_truth - r0["bound_truth"]),
                   nontruth=nontruth_strokes(base), nontruth_no2=nontruth_strokes(no2)), open(out, "w"))
