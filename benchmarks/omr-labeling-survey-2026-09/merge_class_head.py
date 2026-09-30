"""Give a fine-tune back the classes it never saw — by surgery, not training.

Every method tried in round 5 collapses the same class families, and the reason
is structural rather than a bad hyper-parameter: this corpus contains ~30 of the
model's 208 classes, so on every training image the other ~178 receive nothing
but negative gradient. Freezing, warmup, learning rate and teacher rehearsal all
leave that intact, because all of them are still training the classification
head against a corpus that says those classes are absent.

But a YOLOv8 detect head is per-class in its LAST layer: `model.22.cv3.{0,1,2}.2`
is a 1x1 convolution whose output channels are the 208 classes, one row of
weights and one bias each. A class this corpus never labels has exactly one
place its "this is absent" evidence can live — and the fine-tune still knows
the right values for the class(es) its OWN corpus taught it. So the graft
starts from BASE — every tensor, unconditionally — and moves onto it only the
KEPT classes' rows of that one 1x1 conv, from the fine-tune. Nothing else
about base moves: not the backbone, not the neck, not the shared
box-regression branch (`model.22.cv2.*`), not the DFL layer, and not any
OTHER class's row of `cv3`. `--keep`/`--min-labels` say which classes are
"kept" (grafted FROM the fine-tune); every class not kept is simply base's row,
untouched — the naming is about the DONOR, `restore` never described a
direction of copy on this repo's tree, only an outcome.

⚠️ **A grafted row is not free and is not the same as never having trained
that class.** The row was learned against the fine-tune's own (possibly
drifted, if `model.22` was not frozen during its training) features, and it
now reads through BASE's features instead. Whether that recovers the class is
an empirical question — which is the point of doing it as a cheap local step
with a screen behind it, rather than as another GPU arm.

⚠️ **Bug fixed 2026-09-29 (`benchmarks/omr-weights-ab-2026-09/`):** earlier
versions of this tool did the graft backwards — they started from the
FINE-TUNE'S entire state dict and patched only the NON-kept classes' rows
from base, leaving `model.22.cv2.*` (box regression), the DFL layer, the
whole backbone/neck, and every OTHER class's row of `cv3` as the
FINE-TUNE'S, not base's. A tensor-level diff of the shipped production graft
(`hollow-graft-shift09-2026-09-04.pt`, commit `0e9f005b`) against its
recorded base (`hollow-ft-2026-09-03.pt`) and its donor fine-tune
(`round5-sweep/distill25/epoch0.pt`) confirms production was built this way:
589 of 595 tensors are bit-identical to the FINE-TUNE (including every
`model.22.cv2.*` and every backbone/neck conv), and only 187 happen to equal
base (mostly BatchNorm buffers that coincide numerically) — the box-placement
network every symbol reads through in production today is `distill25`'s, not
`hollow-ft-2026-09-03`'s. `transplant_class_rows.py` was already built the
correct way round (base-anchored) and did not share this bug; `--import-rows`
below was also already base-anchored. Only the plain `--ft`/`--base` (no
`--import-rows`) path had the direction backwards, and it is what
`compose_specialists.sh` and the shipped graft both called.

⚠️ **Only classes with ZERO labels are grafted by default's complement** — a
class the corpus labels a little is a class the fine-tune was meant to
change; grafting it in is the point. `--min-labels` moves that line and
prints what it moved.

    python3 .../merge_class_head.py --ft <ft.pt> --base <base.pt> --out <out.pt>
    python3 .../merge_class_head.py ... --labels-root data/user-labeled-distill
"""
from __future__ import annotations

import argparse
import json
import glob
import collections
from pathlib import Path

REPO = Path.cwd()
CLASS_NAMES_JSON = REPO / "tools" / "omr" / "training" / "deepscoresv2_208_classes.json"
CLS_LAYERS = ["model.22.cv3.0.2", "model.22.cv3.1.2", "model.22.cv3.2.2"]


def label_class_counts(root: Path, versions: list[str]) -> collections.Counter:
    c = collections.Counter()
    for v in versions:
        for f in glob.glob(str(root / v / "labels" / "*.txt")):
            for line in open(f):
                parts = line.split()
                if len(parts) == 5:
                    c[int(parts[0])] += 1
    return c


def read_versions(root: Path) -> list[str]:
    out = []
    for line in (root / "catalog-versions.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def verify_graft(out_path, base_path, allowed_rows, names) -> int:
    """SELF-CHECK (Sean, 2026-09-29): prove the written file IS what the
    recipe says -- every tensor bit-identical to --base except the per-class
    head rows of the classes this run chose to graft. Printed every build;
    returns 3 (and says why) if anything else changed. Added after the
    2026-09-04 ship was found to be almost the whole fine-tune (589 of 595
    tensors) with nobody having looked."""
    import torch
    out_sd = torch.load(str(out_path), map_location="cpu",
                        weights_only=False)["model"].state_dict()
    base_sd = torch.load(str(base_path), map_location="cpu",
                         weights_only=False)["model"].state_dict()
    allowed = set(allowed_rows)
    head_keys = {f"{l}.{s}" for l in CLS_LAYERS for s in ("weight", "bias")}
    same, changed, bad = 0, [], []
    for k, v in base_sd.items():
        w = out_sd.get(k)
        if w is None or w.shape != v.shape:
            bad.append(f"{k}: missing or reshaped")
            continue
        if torch.equal(w, v):
            same += 1
            continue
        changed.append(k)
        if k not in head_keys:
            bad.append(f"{k}: not a per-class head row, yet it changed")
            continue
        rows = {i for i in range(v.shape[0]) if not torch.equal(w[i], v[i])}
        if not rows <= allowed:
            bad.append(f"{k}: rows {sorted(rows - allowed)[:8]} changed "
                       "but were not grafted")
    print(f"SELF-CHECK: {same} of {len(base_sd)} tensors identical to --base; "
          f"{len(changed)} changed, only in the rows of "
          f"{sorted(names[i] for i in allowed)}")
    if bad:
        print("SELF-CHECK FAILED -- the file is not what the recipe says:")
        for b in bad[:20]:
            print("  ", b)
        return 3
    print("SELF-CHECK PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ft", type=Path, default=None,
                    help="the fine-tune to graft FROM. Not needed "
                         "with --import-rows, which carries the "
                         "rows already.")
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--labels-root", type=Path,
                    default=REPO / "data" / "user-labeled")
    ap.add_argument("--min-labels", type=int, default=1,
                    help="a class with FEWER than this many boxes in the "
                         "training labels is restored from the base. 1 means "
                         "'restore only what was never labeled at all'.")
    ap.add_argument("--keep", nargs="*", default=None,
                    help="explicit class NAMES to keep from the fine-tune; "
                         "every other class is restored from the base. This is "
                         "the specialist graft — say what the campaign was FOR "
                         "and give the base back everything else. Overrides "
                         "--min-labels. ⚠️ A name that occurs at more than one "
                         "index keeps ALL of them: the 208-class space has 40 "
                         "duplicated names (`augmentationDot` at 40 and 159, "
                         "`slur` at 68 and 176 …) because DSv2 carries two "
                         "naming families, and keeping only one index would "
                         "leave the class half-fine-tuned.")
    ap.add_argument("--bias-shift", type=float, default=0.0,
                    help="subtract this from the BIAS of every KEPT class — a "
                         "per-class confidence floor baked into the weights, "
                         "because the pipeline has one global conf_threshold "
                         "and the grafted classes are the only ones that need "
                         "a different one. The graft's whole axis-2 cost is "
                         "extra half-noteheads on the two Beethoven rows "
                         "(`wrong note head` 30 -> 72), which is recall bought "
                         "with precision; this is the dial that sells some "
                         "back. Shift for a threshold move p0 -> p1 is "
                         "logit(p1) - logit(p0): 0.25 -> 0.45 is 0.90, "
                         "0.25 -> 0.60 is 1.50.")
    ap.add_argument("--export-rows", type=Path, default=None,
                    help="write ONLY the kept classes' head rows to this .npz "
                         "and exit. A specialist's knowledge of its own symbol "
                         "lives in those rows and nowhere else, so this is the "
                         "whole transferable artifact — ~20 KB against an 88 MB "
                         "checkpoint, which matters when the rented box's "
                         "uplink is the bottleneck. Pair with --import-rows.")
    ap.add_argument("--import-rows", type=Path, default=None,
                    help="graft rows exported by --export-rows onto --base. "
                         "--ft is not needed and is ignored.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    import torch

    names = json.loads(CLASS_NAMES_JSON.read_text())
    versions = read_versions(a.labels_root if
                             (a.labels_root / "catalog-versions.txt").exists()
                             else REPO / "data" / "user-labeled")
    counts = label_class_counts(a.labels_root, versions)
    if a.keep:
        want = set(a.keep)
        unknown = want - set(names)
        if unknown:
            print(f"  unknown class name(s): {sorted(unknown)}")
            return 2
        kept = [i for i, n in enumerate(names) if n in want]
        why = f"--keep {sorted(want)}"
    else:
        kept = [i for i in range(len(names)) if counts.get(i, 0) >= a.min_labels]
        why = f"at least {a.min_labels} boxes in the corpus"
    restore = [i for i in range(len(names)) if i not in set(kept)]
    print(f"labels root: {a.labels_root}  versions: {len(versions)}  "
          f"boxes: {sum(counts.values())}")
    print(f"classes KEPT from the fine-tune ({len(kept)}, {why}): "
          f"{sorted({names[i] for i in kept})}")
    print(f"classes RESTORED from the base ({len(restore)})")

    import numpy as np

    if a.import_rows:
        base = torch.load(str(a.base), map_location="cpu", weights_only=False)
        base_sd = base["model"].state_dict()
        blob = np.load(str(a.import_rows))
        idx = [int(i) for i in blob["class_ids"]]
        moved = 0
        for layer in CLS_LAYERS:
            for suffix in ("weight", "bias"):
                k = f"{layer}.{suffix}"
                arr = torch.from_numpy(blob[k])
                for n, c in enumerate(idx):
                    base_sd[k][c] = arr[n]
                    moved += 1
        if a.bias_shift:
            for layer in CLS_LAYERS:
                for c in idx:
                    base_sd[f"{layer}.bias"][c] -= a.bias_shift
        print(f"imported {moved} rows for {len(idx)} classes "
              f"({[names[i] for i in idx]}) at bias shift {a.bias_shift}")
        if a.dry_run:
            return 0
        base["model"].load_state_dict(base_sd)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        torch.save(base, str(a.out))
        print("wrote ->", a.out)
        return verify_graft(a.out, a.base, idx, names)

    if a.ft is None:
        print("--ft is required unless --import-rows is given")
        return 2
    ft = torch.load(str(a.ft), map_location="cpu", weights_only=False)
    ft_sd = ft["model"].state_dict()

    if a.export_rows:
        out = {"class_ids": np.asarray(kept, dtype=np.int32)}
        for layer in CLS_LAYERS:
            for suffix in ("weight", "bias"):
                k = f"{layer}.{suffix}"
                out[k] = ft_sd[k][kept].clone().numpy()
        a.export_rows.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(a.export_rows), **out)
        sz = a.export_rows.stat().st_size
        print(f"exported {len(kept)} classes' rows "
              f"({[names[i] for i in kept]}) -> {a.export_rows} ({sz/1024:.0f} KB)")
        return 0

    # The graft is anchored on BASE, unconditionally, for every tensor.
    # Only the KEPT classes' rows of the per-class 1x1 convs move, from the
    # fine-tune, onto base's own state dict. Everything else — backbone,
    # neck, the shared box-regression branch (model.22.cv2.*), the DFL
    # layer, and every NON-kept class's own row — is base's, bit-exact,
    # because it is simply never written. (Fixed 2026-09-29: this used to
    # start from `ft` and patch the restored classes from base, which left
    # box regression and every other shared tensor as the fine-tune's own,
    # drifted, values — see the module docstring.)
    base = torch.load(str(a.base), map_location="cpu", weights_only=False)
    base_sd = base["model"].state_dict()

    moved = 0
    for layer in CLS_LAYERS:
        for suffix in ("weight", "bias"):
            k = f"{layer}.{suffix}"
            if k not in ft_sd or k not in base_sd:
                print(f"  MISSING {k} — head layout is not what this expects")
                return 2
            if ft_sd[k].shape != base_sd[k].shape:
                print(f"  SHAPE MISMATCH {k}: {tuple(ft_sd[k].shape)} vs "
                      f"{tuple(base_sd[k].shape)}")
                return 2
            for c in kept:
                base_sd[k][c] = ft_sd[k][c].clone()
                moved += 1
    print(f"grafted {moved} per-class parameter rows across "
          f"{len(CLS_LAYERS)} head scales onto --base — every other tensor "
          f"(backbone, neck, model.22.cv2.* box regression, DFL, and the "
          f"{len(restore)} non-kept classes' own rows) stays bit-exact to "
          f"--base")

    if a.bias_shift:
        for layer in CLS_LAYERS:
            k = f"{layer}.bias"
            for c in kept:
                base_sd[k][c] -= a.bias_shift
        print(f"shifted the bias of {len(kept)} kept classes by "
              f"-{a.bias_shift} across {len(CLS_LAYERS)} scales — a "
              f"conf 0.25 detection of those classes now needs "
              f"~{1/(1+pow(2.718281828, -(a.bias_shift + -1.0986))):.2f} "
              f"of the pre-shift score")

    if a.dry_run:
        return 0
    base["model"].load_state_dict(base_sd)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(base, str(a.out))
    print("wrote ->", a.out)
    return verify_graft(a.out, a.base, kept, names)


if __name__ == "__main__":
    raise SystemExit(main())
