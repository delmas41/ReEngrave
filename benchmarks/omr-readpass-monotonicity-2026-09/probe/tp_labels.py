#!/usr/bin/env python3
"""Where the ambiguous `Tp.` labels actually are, in the cached read pass.

The overturn `_resolve_ambiguous_labels` performs is written to the SLOT, so it
is document-wide; the co-occurrence block that can refuse it is evaluated per
SYSTEM.  This prints the population, so the asymmetry is countable.

    tp_labels.py CACHE_DIR
"""
from __future__ import annotations

import collections
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.instruments import AMBIGUOUS_ALIASES   # noqa: E402

cache = Path(sys.argv[1])
by_alias = collections.Counter()
tp_rows = []
for blob in sorted(cache.glob("p*.pkl")):
    pi = int(blob.stem[1:])
    pws, labels = pickle.loads(blob.read_bytes())
    sysof = {s.staff_index: s.system_index for s in pws.staves}
    names_by_system: dict[int, set[str]] = {}
    for lab in labels:
        if lab.matched and lab.instrument:
            names_by_system.setdefault(
                sysof.get(lab.staff_index, 0), set()).add(lab.instrument.name)
    for lab in labels:
        alias = lab.alias or ""
        if alias in AMBIGUOUS_ALIASES:
            by_alias[alias] += 1
        if alias != "tp":
            continue
        sy = sysof.get(lab.staff_index, 0)
        tp_rows.append((pi, sy, lab.staff_index,
                        lab.instrument.name if lab.instrument else None,
                        "Trumpet" in (names_by_system.get(sy) or set())))

print("ambiguous aliases read across the document:", dict(by_alias))
blocked = sum(1 for r in tp_rows if r[4])
print(f"`Tp.` labels: {len(tp_rows)};  systems that ALSO name Trumpet under "
      f"another alias (so the overturn is refused there): {blocked};  "
      f"systems that do not (so the overturn fires): {len(tp_rows) - blocked}")
for r in tp_rows:
    print(f"  p{r[0]:>2} sys{r[1]} staff{r[2]:>2} lexicon={r[3]:<8} "
          f"trumpet_named_on_system={r[4]}")
