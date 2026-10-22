#!/usr/bin/env python3
"""Slot stability: does a slot mean the same instrument on every system/page?

Metric is label PURITY — of every (slot, read label) observation, the fraction
agreeing with that slot's modal label. A slot that means Flute on 11 systems and
Horn on 1 scores 11/12. This needs no hand labelling: the instrument labels come
from the PDF text layer, and the question is only whether the alignment keeps
them consistent.

Usage: python3 benchmarks/omr-system-grouping-2026-08/eval_slots.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page
from tools.omr.slots import assign_slots, labels_by_staff
from tools.omr.staff_detector import detect_staves
from tools.omr.staff_labels import read_staff_labels

B9 = ("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp/"
      "beethoven-symphony-9/pdfs/imslp-516488/score.pdf")
PAGES = (20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75)


def main() -> int:
    pages, labels = [], []
    for p in PAGES:
        pws = detect_staves(render_page(B9, p, dpi=300))
        pages.append(pws)
        labels.append(labels_by_staff(read_staff_labels(pws)))

    reference = assign_slots(pages, labels)
    print(f"reference layout — {len(reference)} slots")
    for s in reference:
        print(f"   slot {s.index:2d}  group {s.group_index}  {s.instrument or '(unlabelled)'}")

    obs: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    unassigned = assigned = 0
    for pws, lab in zip(pages, labels):
        for st in pws.staves:
            if st.slot_index < 0:
                unassigned += 1
                continue
            assigned += 1
            if st.staff_index in lab:
                obs[st.slot_index][lab[st.staff_index]] += 1

    total = sum(sum(c.values()) for c in obs.values())
    pure = sum(c.most_common(1)[0][1] for c in obs.values())
    print(f"\nstaves assigned a slot : {assigned}/{assigned + unassigned}"
          f"  ({unassigned} unassigned)")
    print(f"label purity           : {pure}/{total} ({pure / max(1, total):.0%})")
    print(f"slots with no disagreement at all: "
          f"{sum(1 for c in obs.values() if len(c) == 1)}/{len(obs)}")
    for slot, c in sorted(obs.items()):
        if len(c) > 1:
            print(f"   slot {slot:2d}: {dict(c.most_common())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
