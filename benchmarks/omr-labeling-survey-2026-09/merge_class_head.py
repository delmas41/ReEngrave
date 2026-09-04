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
place its "this is absent" evidence can live — and the base checkpoint still
holds the right values for that row. So take the fine-tune, and for every class
the training labels do not contain, put the BASE's row back.

⚠️ **This is not free and is not the same as never having trained.** The
features feeding the head drift too, so a restored row is the base's opinion
applied to slightly different features. Whether that recovers the class is an
empirical question — which is the point of doing it as a cheap local step with a
screen behind it, rather than as another GPU arm.

⚠️ **Only classes with ZERO labels are restored by default.** A class the corpus
labels a little is a class the fine-tune was meant to change; restoring it would
undo the training that was wanted. `--min-labels` moves that line and prints
what it moved.

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ft", type=Path, required=True)
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

    ft = torch.load(str(a.ft), map_location="cpu", weights_only=False)
    base = torch.load(str(a.base), map_location="cpu", weights_only=False)
    ft_sd = ft["model"].state_dict()
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
            for c in restore:
                ft_sd[k][c] = base_sd[k][c].clone()
                moved += 1
    print(f"restored {moved} per-class parameter rows across "
          f"{len(CLS_LAYERS)} head scales")

    if a.dry_run:
        return 0
    ft["model"].load_state_dict(ft_sd)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(ft, str(a.out))
    print("wrote ->", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
