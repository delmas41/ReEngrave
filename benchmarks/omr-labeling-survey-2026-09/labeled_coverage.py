#!/usr/bin/env python3
"""Count hand-labeled YOLO boxes per class across every data/user-labeled/vN-*
version. This is the reproducible evidence behind the "symbol axis" of
SURVEY_DESIGN.md: it shows which detector classes already have many examples
(noteheadBlack ~690) and which are near-blind spots (graceNote* 0, ornament* 0,
noteheadWhole* ~23, timeSig digits ~1 each).

    python3 benchmarks/omr-labeling-survey-2026-09/labeled_coverage.py
    python3 benchmarks/omr-labeling-survey-2026-09/labeled_coverage.py --zeros

Class ids are mapped through data/user-labeled/catalog.yaml's 208-class name
list. Ids >= 208 are the custom classes the nc=208 cap filters out (barlines,
textDynamic). Run from the MAIN checkout. Dependency-free apart from PyYAML,
which the training stack already requires.
"""
from __future__ import annotations

import argparse
import collections
import glob
import os

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROOT = os.path.join(REPO, "data", "user-labeled")

# Classes that are detected by classical CV upstream, never YOLO-labelled
# (CLAUDE.md, "Hand-label cells"): they train as background if boxed.
CV_STRUCTURAL = {"staff", "stem", "beam", "brace", "ledgerLine", "legerLine"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zeros", action="store_true",
                    help="also list YOLO classes with ZERO labelled boxes")
    args = ap.parse_args()

    names = yaml.safe_load(open(os.path.join(ROOT, "catalog.yaml")))["names"]

    per_ver: dict[str, tuple] = {}
    total = collections.Counter()
    for vd in sorted(glob.glob(os.path.join(ROOT, "v*"))):
        if not os.path.isdir(vd):
            continue
        cnt = collections.Counter()
        cells = 0
        for lf in glob.glob(os.path.join(vd, "labels", "*.txt")):
            cells += 1
            for line in open(lf):
                line = line.strip()
                if line:
                    cnt[int(line.split()[0])] += 1
        per_ver[os.path.basename(vd)] = (cnt, cells)
        total.update(cnt)

    print("=== per-version ===")
    for vn, (cnt, cells) in per_ver.items():
        print(f"{vn:34s} cells={cells:4d} boxes={sum(cnt.values()):5d} classes={len(cnt)}")

    print("\n=== boxes per class, all versions unioned (descending) ===")
    for cid, n in sorted(total.items(), key=lambda x: -x[1]):
        nm = names[cid] if cid < len(names) else f"<custom id {cid}>"
        flag = "  [CV structural — should not be labelled]" if nm in CV_STRUCTURAL else ""
        print(f"{n:6d}  {nm}{flag}")

    if args.zeros:
        seen = set(total)
        print("\n=== YOLO classes with ZERO labelled boxes (blind spots) ===")
        for cid, nm in enumerate(names):
            if cid not in seen and nm not in CV_STRUCTURAL:
                print(f"    {nm}")


if __name__ == "__main__":
    main()
