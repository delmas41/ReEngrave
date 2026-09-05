"""Transplant ONLY the class-logit rows of named classes from specialist
checkpoints into a base — the conservative composite.

`merge_class_head.py` goes the other direction: it keeps the fine-tune's whole
detect head (box branch + shared convs included) and restores the base's rows
for classes the corpus does not teach. That leaves every class reading through
the specialist's drifted shared convs. This tool starts from the BASE and moves
only the named classes' rows of the final 1x1 class convs
(model.22.cv3.{0,1,2}.2, one weight row + one bias per class), so every other
class stays bit-exact with the base by construction. The transplanted rows were
trained against the specialist's own (slightly drifted) shared convs, so the
mismatch risk moves onto the kept classes alone — the probe decides which
direction wins.

Duplicated names: the 208 space names 40 classes twice; every index of a name
moves.

    python3 .../transplant_class_rows.py --base prod.pt --out composite.pt \
        --graft tie=ties_best.pt --graft slur=slurs_best.pt
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch

CLASSES = Path("tools/omr/training/deepscoresv2_208_classes.json")


def load(p):
    return torch.load(p, map_location="cpu", weights_only=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--graft", action="append", required=True,
                    help="<class-name>=<ckpt.pt>, repeatable; a comma list of "
                         "names is allowed on the left")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    names = json.loads(CLASSES.read_text())
    ckpt = load(a.base)
    sd = ckpt["model"].state_dict()
    moved = 0
    for spec in a.graft:
        cls_part, path = spec.split("=", 1)
        want = {c.strip() for c in cls_part.split(",")}
        idxs = [i for i, n in enumerate(names) if n in want]
        if not idxs:
            raise SystemExit(f"no class index named {want}")
        ft = load(path)["model"].state_dict()
        for scale in range(3):
            for suffix in ("weight", "bias"):
                key = f"model.22.cv3.{scale}.2.{suffix}"
                for i in idxs:
                    if not torch.equal(sd[key][i], ft[key][i]):
                        sd[key][i] = ft[key][i].clone()
                        moved += 1
        print(f"  {sorted(want)} rows from {Path(path).name} "
              f"(indices {idxs})")
    ckpt["model"].load_state_dict(sd)
    torch.save(ckpt, a.out)
    print(f"moved {moved} rows -> {a.out}")


if __name__ == "__main__":
    main()
