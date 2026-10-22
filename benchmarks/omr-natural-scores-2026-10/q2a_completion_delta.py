"""ROADMAP 2.196 Q2a. Stdlib only. The training cells of the production accidental rows (v7 + v8, labeled 2026-09-02 for hollow noteheads
only) were later COMPLETED by hand (v13-v21, 2026-09-03: "human hollow+rests+accidentals+clefs"). Same image stem in both = same cell.
Every accidental box that a completed label has and the v7/v8 label does not is a printed accidental that hollow-ft was taught as BACKGROUND.
usage: q2a_completion_delta.py DATA_ROOT OUT.json"""
import collections, glob, hashlib, json, pathlib, sys
ROOT, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
G = {59: "flat", 60: "flat", 170: "flat", 61: "natural", 62: "natural", 171: "natural", 63: "sharp", 64: "sharp", 172: "sharp", 65: "double", 66: "double", 173: "double", 174: "double"}
frac = lambda k: int.from_bytes(hashlib.sha256(k.encode()).digest()[:8], "big") / 2 ** 64
src = {}                                    # stem -> (version, labels)
for v in ("v7-2026-09-02-hollow", "v8-2026-09-02-hollow2-5pub"):
    for f in glob.glob(str(ROOT / v / "labels" / "*.txt")):
        src[pathlib.Path(f).stem] = (v, [l.split() for l in open(f) if len(l.split()) >= 5])
done = {}
for v in sorted(ROOT.glob("v1[3-9]-*")) + sorted(ROOT.glob("v2[01]-*")):
    for f in glob.glob(str(v / "labels" / "*.txt")):
        done[pathlib.Path(f).stem] = (v.name, [l.split() for l in open(f) if len(l.split()) >= 5])
shared = sorted(set(src) & set(done))
print("v7+v8 cells", len(src), "completed cells (v13-v21)", len(done), "same stem in both", len(shared))
tot = collections.Counter(); tot_train = collections.Counter(); per_pub = collections.defaultdict(collections.Counter)
cells_with = collections.Counter(); ex = []
for s in shared:
    sv, sl = src[s]; dv, dl = done[s]
    in_src = collections.Counter(G[int(p[0])] for p in sl if int(p[0]) in G)
    in_done = collections.Counter(G[int(p[0])] for p in dl if int(p[0]) in G)
    train = frac(f"reengrave:{sv}:{s}") >= 0.15           # train split of the v7/v8 version hollow-ft saw
    for k in ("natural", "flat", "sharp", "double"):
        d = in_done[k] - in_src[k]
        tot[k] += d; per_pub[dv][k] += d
        if train:
            tot_train[k] += d
    if in_done["natural"] - in_src["natural"] > 0:
        cells_with["natural"] += 1; cells_with["natural_train"] += train
    if sum(in_done.values()) - sum(in_src.values()) > 0:
        cells_with["any"] += 1; cells_with["any_train"] += train
        if len(ex) < 400: ex.append((s, dv, train, dict(in_done)))
print("accidentals present in completed label but absent from v7/v8 label (all shared cells):", dict(tot))
print("  same, only cells in the TRAIN split hollow-ft used:", dict(tot_train))
print("cells with >=1 such accidental:", dict(cells_with), "of", len(shared), "shared cells; train-split shared cells:", sum(frac(f'reengrave:{src[s][0]}:{s}') >= .15 for s in shared))
print("per completed version:", {k: dict(v) for k, v in per_pub.items()})
json.dump(dict(shared=len(shared), total=tot, train=tot_train, cells_with=cells_with, per_version={k: dict(v) for k, v in per_pub.items()}, examples=ex), open(OUT, "w"), indent=1)
