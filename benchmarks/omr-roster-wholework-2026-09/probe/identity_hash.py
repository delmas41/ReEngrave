"""Hash the identity vector of a run: (page, system, staff) -> instrument.

Lets two arms be compared exactly without diffing megabytes of detections.
"""
from __future__ import annotations
import hashlib
import json
import sys

for path in sys.argv[1:]:
    r = json.load(open(path))
    rows = []
    for page in r.get("pages", []):
        for sy in page.get("systems", []):
            sts = sorted(sy.get("staves", []),
                         key=lambda s: s.get("staff_geometry", {})
                         .get("line_ys_page", [0])[0])
            for i, st in enumerate(sts):
                rows.append((page.get("page_index"), sy.get("system_index"), i,
                             st.get("slot_index"), st.get("instrument"),
                             st.get("instrument_source")))
    blob = json.dumps(rows, sort_keys=True).encode()
    print(f"{hashlib.sha256(blob).hexdigest()[:16]}  n={len(rows):5d}  {path}")
