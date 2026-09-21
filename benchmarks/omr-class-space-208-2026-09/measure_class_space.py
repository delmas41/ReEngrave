#!/usr/bin/env python3
"""THE MEASUREMENT: which names did the coverage tool check that cannot fire,
and which shipped names did it never check?

Run from the repo root:  python3 benchmarks/omr-class-space-208-2026-09/measure_class_space.py

⚠️ THREE SPACES, AND CONFLATING ANY TWO IS HOW THE DEFECT HAPPENED.

  SNAPSHOT  `training/deepscores_classes.py:DEEPSCORES_V2_CLASSES`, 146 names.
            The TRAINING dataset's list, consumed by `prepare_yolo_data.py`
            and `verdicts_to_yolo_labels.py`. Changing it touches the training
            corpus. It is NOT what the detector emits.

  RAW 208   `class_aliases.vocabulary()` -- the committed manifest of the
            shipped checkpoint, 208 ids / 168 distinct names (40 names appear
            at both a fine and a coarse id).

  CANONICAL What a CONSUMER can actually see: 157 names. `yolo_detector`
            applies `class_aliases.canonicalize_names` at the one place the
            model's own `names` are read, so the 11 aliased coarse spellings
            never arrive under their own name.

The coverage instrument must audit the CANONICAL space. Auditing SNAPSHOT is
the bug; auditing RAW would be a different, newer bug -- it would report six
`dynamicLetter*` classes as live for `Q.DYNAMIC_LETTER` when none can arrive.

⚠️ NEEDS NO WEIGHTS. Every number here is a property of committed files. The
weights are read only by `--verify-weights`, which is the manifest's own
provenance check and skips loudly when they are absent.
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr import class_aliases                              # noqa: E402
from tools.omr.staged import gather_coverage as GC               # noqa: E402
from tools.omr.training.deepscores_classes import (              # noqa: E402
    DEEPSCORES_V2_CLASSES as SNAPSHOT)

PRODUCTION_WEIGHTS = (Path(__file__).resolve().parents[2] / "omr-weights"
                      / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


def spaces() -> dict:
    vocab = class_aliases.vocabulary()
    return {
        "snapshot": set(SNAPSHOT),
        "raw": set(vocab),
        "canonical": {class_aliases.canonical(n) for n in vocab},
        "_ids": len(vocab),
    }


def _by_family(names) -> dict:
    out = collections.defaultdict(list)
    for n in sorted(names):
        out[GC._family(n)].append(n)
    return dict(sorted(out.items()))


def _print_families(title: str, names) -> None:
    fams = _by_family(names)
    print(f"\n{title}  ({len(names)} names, {len(fams)} families)")
    for fam, ns in fams.items():
        print(f"    {fam:<16} {len(ns):>2}  {', '.join(ns)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-weights", action="store_true",
                    help="also check the manifest against the shipped checkpoint")
    args = ap.parse_args()

    s = spaces()
    print("=" * 78)
    print("THE THREE SPACES")
    print("=" * 78)
    print(f"  snapshot (deepscores_classes.py) : {len(s['snapshot']):>4} names")
    print(f"  shipped manifest, ids            : {s['_ids']:>4}")
    print(f"  shipped manifest, distinct names : {len(s['raw']):>4}")
    print(f"  CANONICAL (what a consumer sees) : {len(s['canonical']):>4}")
    print(f"  audited by gather_coverage now   : {len(set(GC._detector_classes())):>4}")

    cannot_fire = s["snapshot"] - s["canonical"]
    never_checked = s["canonical"] - s["snapshot"]

    print("\n" + "=" * 78)
    print("SET A -- CHECKED BUT CANNOT FIRE  (in the snapshot, not in the")
    print("         canonical shipped space: no detection can ever carry it)")
    print("=" * 78)
    _print_families("by family", cannot_fire)

    print("\n" + "=" * 78)
    print("SET B -- SHIPPED BUT NEVER CHECKED  (a consumer can see it; the")
    print("         snapshot has no such name)")
    print("=" * 78)
    _print_families("by family", never_checked)

    print("\n" + "=" * 78)
    print("THE DYNAMICS CLAIM, TESTED  (dossier: 'six that cannot fire and")
    print("         misses the six that can')")
    print("=" * 78)
    dyn = lambda xs: sorted(n for n in xs if n.lower().startswith("dynamic"))
    print(f"  cannot fire   : {len(dyn(cannot_fire))}  {dyn(cannot_fire)}")
    print(f"  never checked : {len(dyn(never_checked))}  {dyn(never_checked)}")
    print(f"  never checked, if the RAW 208 were used instead: "
          f"{dyn(s['raw'] - s['snapshot'])}")
    print("  ⚠️ The first half is exactly right. The second is FALSE against the")
    print("     canonical space and TRUE only against the raw one -- and the raw")
    print("     six are `dynamicLetter*`, which `canonicalize_names` renames at")
    print("     the detector, so not one of them can reach a consumer.")

    print("\n" + "=" * 78)
    print("FAMILIES")
    print("=" * 78)
    fs = {GC._family(n) for n in s["snapshot"]}
    fr = {GC._family(n) for n in s["raw"]}
    fc = {GC._family(n) for n in s["canonical"]}
    print(f"  snapshot {len(fs)}   raw {len(fr)}   canonical {len(fc)}")
    print(f"  phantom (snapshot only, cannot fire) : {sorted(fs - fc)}")
    print(f"  real but never audited               : {sorted(fc - fs)}")
    print(f"  raw-only, gone under canonicalization: {sorted(fr - fc)}")
    print("  ⚠️ The last row is why the space must be canonicalized: a probe")
    print("     using the RAW 208 reports those families as unnamed gaps when")
    print("     the detector renames them away before anything sees them.")

    if args.verify_weights:
        print("\n" + "=" * 78)
        print("MANIFEST vs SHIPPED CHECKPOINT")
        print("=" * 78)
        if not PRODUCTION_WEIGHTS.exists():
            print(f"  LOUD SKIP: no weights at {PRODUCTION_WEIGHTS}")
            print("  The manifest is UNVERIFIED against a checkpoint on this machine.")
            return 0
        import warnings
        try:
            import torch
        except ImportError:
            print("  LOUD SKIP: torch is not installed.")
            return 0
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ck = torch.load(PRODUCTION_WEIGHTS, map_location="cpu",
                            weights_only=False)
        names = ck["model"].names
        shipped = [names[i] for i in range(len(names))]
        ok = shipped == class_aliases.vocabulary()
        print(f"  checkpoint : {PRODUCTION_WEIGHTS.name}")
        print(f"  ids        : {len(shipped)}")
        print(f"  identical index-for-index to the manifest : {ok}")
        if not ok:
            for i, (a, b) in enumerate(zip(shipped, class_aliases.vocabulary())):
                if a != b:
                    print(f"    id {i}: checkpoint={a!r} manifest={b!r}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
