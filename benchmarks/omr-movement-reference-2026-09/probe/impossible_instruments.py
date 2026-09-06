"""Staves named an instrument their MOVEMENT does not contain.

This reaches every staff, not just the full systems the exact scorer can judge,
and it needs no per-page reading: Beethoven 5's first three movements have no
Piccolo, no Contrabassoon and no Trombones -- the reference encodings' own part
lists say so (mvt 1/2/3 = 18 parts, mvt 4 = 23) -- so any such name on a page
before the finale is categorically impossible, whatever the page prints.

A reader with a musician's eye catches these instantly; a coverage number hides
them, because they are named with full confidence.
"""
from __future__ import annotations
import json
import sys
import collections

FINALE_ONLY = {"Piccolo", "Contrabassoon", "Trombone"}
FINALE_FIRST_PAGE = 44          # crops/p44-margin.png

path = sys.argv[1]
r = json.load(open(path))
rows = []
for page in r.get("pages", []):
    pi = page.get("page_index")
    for sy in page.get("systems", []):
        for st in sy.get("staves", []):
            rows.append((pi, sy.get("system_index"), st.get("instrument")))
print(f"INPUT ASSERTION: staff-records={len(rows)} "
      f"pages={len({p for p, _, _ in rows})}")
if not rows:
    print("REFUSING: no staff records")
    raise SystemExit(1)

bad = [(p, s, i) for p, s, i in rows if p < FINALE_FIRST_PAGE and i in FINALE_ONLY]
before = [x for x in rows if x[0] < FINALE_FIRST_PAGE]
print(f"staves before the finale (page < {FINALE_FIRST_PAGE}): {len(before)}")
print(f"named a finale-only instrument              : {len(bad)}"
      f"  ({len(bad)/max(1,len(before)):.4f})")
c = collections.Counter(i for _, _, i in bad)
for k, v in c.most_common():
    print(f"    {v:4d}  {k}")
pages = sorted({p for p, _, _ in bad})
print(f"  on pages: {pages}")
