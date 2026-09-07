#!/usr/bin/env python3
"""Pull the CLEF READINGS out of a full transcription, and nothing else.

`extract.py` keeps four fields per staff and `clef` is not among them, which is
why the committed pass-A artefact cannot answer the question this benchmark
asks.  The full 125 MB run does.  What comes out here is exactly what
`contextual._read_clefs_by_slot` consumes: `(page, system, staff) -> (clef,
clef_source)`, with `clef_source` present being the admission test.

    extract_clefs.py FULL.json OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

src, dst = sys.argv[1], sys.argv[2]
r = json.load(open(src))
rows = []
n_staff = n_clef = 0
for p in r.get("pages", []):
    for s in p.get("systems", []):
        for st in s.get("staves", []):
            n_staff += 1
            if not st.get("clef_source"):
                continue
            n_clef += 1
            rows.append([p.get("page_index"), s.get("system_index"),
                         st.get("staff_index"), st.get("clef"),
                         st.get("clef_source")])
Path(dst).write_text(json.dumps({"source": src, "n_staff": n_staff,
                                 "n_with_clef_source": n_clef, "rows": rows}))
print(f"{dst}: {n_clef} of {n_staff} staves carry a read clef")
