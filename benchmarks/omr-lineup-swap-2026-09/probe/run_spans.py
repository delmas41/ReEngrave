"""`movement_reference.lineup_spans` on a committed label dump, flag off vs on.

The A/B the rule has to pass before anything downstream is worth running: the
count-derived spans must be unchanged with `OMR_LINEUP_SWAP_SPLIT` off, and the
one-span controls and known boundaries must be unchanged with it on.

    run_spans.py LABELS.json [LABELS.json ...]

⚠️ The label evidence is filtered to `slots.MIN_LABEL_CONFIDENCE` here, because
that is what `SystemView.labels` carries at the real call site — scoring on
labels the pipeline would not align on would measure a rule nobody can ship.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import movement_reference as mr          # noqa: E402
from tools.omr.slots import MIN_LABEL_CONFIDENCE        # noqa: E402


def evidence(rows):
    """`(page_systems, page_labels)` in `lineup_spans`' two shapes."""
    page_systems, page_labels = [], []
    for r in sorted(rows, key=lambda r: r["page"]):
        by_staff = {l["staff_index"]: l["instrument"] for l in r["labels"]
                    if l["instrument"]
                    and l["confidence"] in MIN_LABEL_CONFIDENCE}
        per_system, offset = [], 0
        for n in r["systems"]:
            per_system.append([by_staff.get(offset + k) for k in range(n)])
            offset += n
        page_systems.append((r["page"], list(r["systems"])))
        page_labels.append((r["page"], per_system))
    return page_systems, page_labels


def ranges(spans):
    return [[s[0], s[-1]] for s in spans if s]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels", nargs="+")
    args = ap.parse_args()

    for path in args.labels:
        rows = json.load(open(path))
        ps, pl = evidence(rows)
        os.environ["OMR_LINEUP_SWAP_SPLIT"] = "0"
        off_noev = ranges(mr.lineup_spans(ps))
        off = ranges(mr.lineup_spans(ps, pl))
        os.environ["OMR_LINEUP_SWAP_SPLIT"] = "1"
        on_noev = ranges(mr.lineup_spans(ps))
        on = ranges(mr.lineup_spans(ps, pl))
        name = Path(path).stem.replace("labels-", "")
        print(f"\n{name}: {len(rows)} pages")
        print(f"  flag off, no evidence : {off_noev}")
        print(f"  flag off, evidence    : {off}")
        print(f"  flag ON,  no evidence : {on_noev}")
        print(f"  flag ON,  evidence    : {on}")
        assert off == off_noev == on_noev, "FLAG-OFF IS NOT INERT"
        print("  " + ("SPLIT" if on != off else "unchanged"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
