"""Compare reading policies offline on the rows of direction_stop_experiment.py.

    python3 direction_stop_analyze.py <dir with stop_*.json>

Policies (the lexicon is NOT touched; `lookup` as shipped):
  P0 current      : Surya (20 s guard, no cap) first, Tesseract second            time = sum(surya_guard) + sum(tess)
  P1 tess-first   : Tesseract on all; Surya (20 s guard, no cap) only where Tesseract fails the lexicon
  P2 tess+cap     : Tesseract on all; Surya with the width-scaled cap only on failures
  P3 tess+cap+retry: P2, then ONE uncapped guarded Surya read of crops still failing   (time = P2 + their guard times)
  P4 cap-first    : Surya capped on all, Tesseract second
"""
import json, glob, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.direction_lexicon import lookup

d = sys.argv[1]
POL = ["P0", "P1", "P2", "P3", "P4"]


def ok(t):
    return bool(t) and lookup(t) is not None


def key(r, t):
    h = lookup(t)
    return (r["staff"], r["measure"], r["x"], " ".join(h.text.lower().replace(".", " ").split()))


tot_t = {p: 0.0 for p in POL}
words_all = {p: [] for p in POL}
print(f"{'page':8}{'cands':>6}" + "".join(f"{p+' s':>9}{p+' w':>6}" for p in POL))
for f in sorted(glob.glob(os.path.join(d, "stop_*.json"))):
    rows = json.load(open(f))["rows"]
    tag = os.path.basename(f)[5:-5]
    T = {p: 0.0 for p in POL}; W = {p: set() for p in POL}
    for r in rows:
        te, sg, sc = r["tess"], r["surya_guard"], r["surya_cap"]
        # P0
        T["P0"] += r["t_surya_guard"] + r["t_tess"]
        for t in (sg, te):
            if ok(t):
                W["P0"].add(key(r, t)); break
        # P1
        T["P1"] += r["t_tess"]
        if ok(te):
            W["P1"].add(key(r, te))
        else:
            T["P1"] += r["t_surya_guard"]
            if ok(sg):
                W["P1"].add(key(r, sg))
        # P2 / P3
        T["P2"] += r["t_tess"]; T["P3"] += r["t_tess"]
        if ok(te):
            W["P2"].add(key(r, te)); W["P3"].add(key(r, te))
        else:
            T["P2"] += r["t_surya_cap"]; T["P3"] += r["t_surya_cap"]
            if ok(sc):
                W["P2"].add(key(r, sc)); W["P3"].add(key(r, sc))
            else:
                T["P3"] += r["t_surya_guard"]
                if ok(sg):
                    W["P3"].add(key(r, sg))
        # P4
        T["P4"] += r["t_surya_cap"] + r["t_tess"]
        for t in (sc, te):
            if ok(t):
                W["P4"].add(key(r, t)); break
    print(f"{tag:8}{len(rows):>6}" + "".join(f"{T[p]:>9.1f}{len(W[p]):>6}" for p in POL))
    for p in POL:
        tot_t[p] += T[p]; words_all[p].append((tag, W[p]))
print("TOTAL s " + "".join(f"{p}={tot_t[p]:.0f} " for p in POL))
for p in POL[1:]:
    lost = []; gained = []
    for (tag, w0), (_t, wp) in zip(words_all["P0"], words_all[p]):
        lost += [(tag,) + k for k in sorted(w0 - wp)]; gained += [(tag,) + k for k in sorted(wp - w0)]
    print(p, "LOST vs P0:", lost, "| GAINED:", gained)
n_te = n_all = 0
for f in glob.glob(os.path.join(d, "stop_*.json")):
    for r in json.load(open(f))["rows"]:
        if ok(r["surya_guard"]) or ok(r["tess"]) or ok(r["surya_cap"]):
            n_all += 1; n_te += ok(r["tess"])
print(f"crops read right by any reader: {n_all}; by Tesseract alone: {n_te}")
