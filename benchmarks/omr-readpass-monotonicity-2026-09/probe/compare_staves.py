#!/usr/bin/env python3
"""Are the two passes' STAVES the same page structure?

If they are, the only thing left between them is code, and a bisect is honest.
If they are not, part of the drift is phase-1 segmentation and the identity
join is being handed a different page.

    compare_staves.py EXTRACT.json CACHE_DIR
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

extract = json.loads(Path(sys.argv[1]).read_text())
cache = Path(sys.argv[2])

a = {}
for p in extract["pages"]:
    sysmap = {}
    for s in p.get("systems", []):
        sysmap[s.get("system_index")] = sorted(
            st["staff_index"] for st in s.get("staves", []))
    a[p["page_index"]] = sysmap

b = {}
for blob in sorted(cache.glob("p*.pkl")):
    pi = int(blob.stem[1:])
    pws, _labels = pickle.loads(blob.read_bytes())
    sysmap = {}
    for st in pws.staves:
        sysmap.setdefault(st.system_index, []).append(st.staff_index)
    b[pi] = {k: sorted(v) for k, v in sysmap.items()}

pages = sorted(set(a) | set(b))
diff = [p for p in pages if a.get(p) != b.get(p)]
print(f"pages compared: {len(pages)}   pages differing: {len(diff)}")
na = sum(len(v) for m in a.values() for v in m.values())
nb = sum(len(v) for m in b.values() for v in m.values())
print(f"staff records: extract {na}   cache {nb}")
for p in diff[:20]:
    print(f"  p{p}: extract {a.get(p)}")
    print(f"       cache   {b.get(p)}")
