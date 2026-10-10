#!/usr/bin/env python3
"""lud_side_check: for the kept -> narrowed notes whose ONLY newly-differing guard input is the stem side
(None -> up/down, the 2.77b ruler fallback), which of the strokes it dropped were the other guards'?

rhythm.py narrows with `beam_discounted_uncertain` when
  (discount_removed_all_marks and (own_stems or reach_stem)) or ink_removed_all_marks or far_removed_all_marks.
Last night `reach_stem` did not exist, so a head with no CV stem could not take the first branch, and
`far_removed_all_marks` did not exist. This reads tonight's counters for the side-only group to see which
branch it took.
"""
import collections
import json
import sys

doc = sys.argv[1]
b = json.load(open(f"out/scratch-lud/extract-{doc}.json"))["dur"]
import csv
rows = [r for r in csv.DictReader(open(f"benchmarks/acceptance/overnight/20261010-night/undecided/changed-notes-{doc}.csv"))
        if r["kind"] == "kept_to_narrowed" and not r["ink_refusal_why"] and "stem side None->" in r["what_changed"]]
c = collections.Counter()
for r in rows:
    d = b[r["subject"]]["detail"]
    nb, arc, far = int(d.get("beams_neighbour_staff") or 0), int(d.get("beams_decided_arc") or 0), int(d.get("beams_far_side") or 0)
    stems = int(d.get("stems_attached") or 0)
    key = []
    if nb:
        key.append("neighbour-staff strokes dropped")
    if arc:
        key.append("decided-arc strokes dropped")
    if far:
        key.append("far-side strokes dropped")
    c[(" + ".join(key) or "no stroke dropped by any counter", f"stems_attached={stems}")] += 1
print(f"{doc}: {len(rows)} notes with the stem side as the only newly-differing guard input")
for k, n in c.most_common():
    print(f"  {n:4d}  {k[0]}   {k[1]}")
