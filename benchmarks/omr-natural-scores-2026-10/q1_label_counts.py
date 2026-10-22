"""ROADMAP 2.196 Q1. Stdlib only. Counts accidental / key-accidental boxes in the label corpus, per dataset version.

Class ids (tools/omr/training/deepscoresv2_208_classes.json): the model spells the accidentals TWICE.
  series A (59-66):   flat 59, flatSmall 60, natural 61, naturalSmall 62, sharp 63, sharpSmall 64, doubleSharp 65, doubleFlat 66
  series B (170-174): flat 170, natural 171, sharp 172, doubleSharp 173, doubleFlat 174
  keys: keyFlat 67, keyNatural 68, keySharp 69
usage: q1_label_counts.py DATA_ROOT(data/user-labeled) OUT.json
Production training set of the accidental rows (see FINDINGS Q3): hollow-ft-2026-09-03 = 1 epoch (epoch0) on v1-v4 (2x oversampled train split) + v7 + v8
(train split, hash 'reengrave:<version>:<stem>' < 0.15 -> val, as build_catalog_yaml does)."""
import collections, glob, hashlib, json, pathlib, sys

ROOT, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
GROUP = {59: "flat", 60: "flat", 170: "flat", 61: "natural", 62: "natural", 171: "natural", 63: "sharp", 64: "sharp", 172: "sharp",
         65: "double", 66: "double", 173: "double", 174: "double", 67: "keyFlat", 68: "keyNatural", 69: "keySharp"}
SPELL = {59: "A", 60: "A", 61: "A", 62: "A", 63: "A", 64: "A", 65: "A", 66: "A", 170: "B", 171: "B", 172: "B", 173: "B", 174: "B"}


def frac(key):
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") / 2 ** 64


def count(vdir, split=None, seed="reengrave"):
    c = collections.Counter(); cells = 0; cells_with = 0
    for f in sorted(glob.glob(str(vdir / "labels" / "*.txt"))):
        stem = pathlib.Path(f).stem
        if split and (frac(f"{seed}:{vdir.name}:{stem}") < 0.15) != (split == "val"):
            continue
        cells += 1
        hit = False
        for l in open(f):
            p = l.split()
            if len(p) >= 5 and int(p[0]) in GROUP:
                c[GROUP[int(p[0])]] += 1
                c["row%d" % int(p[0])] += 1
                hit = True
        cells_with += hit
    return dict(cells=cells, cells_with_any=cells_with, **c)


res = {"all_cells": {}, "train_split": {}}
vers = sorted(p for p in ROOT.glob("v*") if p.is_dir())
for v in vers:
    res["all_cells"][v.name] = count(v)
    res["train_split"][v.name] = count(v, "train")
# production-weights training set for the accidental rows
prod = collections.Counter()
for name, mult in [("v1-2026-05-18-orchestral", 2), ("v2-2026-06-08-beet5", 2), ("v3-2026-06-09-mahler5", 2), ("v4-2026-06-10-la-mer", 2),
                   ("v7-2026-09-02-hollow", 1), ("v8-2026-09-02-hollow2-5pub", 1)]:
    d = ROOT / "_nc208" / name if name.startswith(("v1-", "v2-", "v3-", "v4-")) else ROOT / name
    r = count(d, "train")
    res.setdefault("hollowft_trainset_detail", {})[name] = dict(r, mult=mult, dir=str(d))
    for k, n in r.items():
        prod[k] += n * mult
res["hollowft_trainset_weighted"] = dict(prod)
json.dump(res, open(OUT, "w"), indent=1)
print("%-38s %6s %5s | %5s %5s %5s %5s | %7s %7s %7s | A/B natural" % ("version (all cells)", "cells", "cw", "nat", "flat", "sharp", "dbl", "keyFl", "keyNat", "keySh"))
for n, r in res["all_cells"].items():
    print("%-38s %6d %5d | %5d %5d %5d %5d | %7d %7d %7d | %d/%d" % (n[:38], r["cells"], r["cells_with_any"], r.get("natural", 0), r.get("flat", 0), r.get("sharp", 0), r.get("double", 0),
          r.get("keyFlat", 0), r.get("keyNatural", 0), r.get("keySharp", 0), r.get("row61", 0) + r.get("row62", 0), r.get("row171", 0)))
print("HOLLOW-FT TRAIN SET (weighted x2 for v1-v4):", {k: v for k, v in prod.items() if not k.startswith("row")})
