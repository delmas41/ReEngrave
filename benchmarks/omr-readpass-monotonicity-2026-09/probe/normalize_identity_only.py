#!/usr/bin/env python3
"""Make an `identity_only.py` blob loadable by the phase-0 harness.

`load.py` chooses its shape on `pages[0]` being a dict.  `identity_only.py`
writes page DICTS with empty `systems`, so it is read as the "staff" shape and
yields zero staff records — even though its `absent_instrument_veto.staff_slots`
holds all 1616.  Rewriting `pages` as page NUMBERS routes it to the compose
branch, which is where its records actually live.  Nothing else is touched.

    normalize_identity_only.py IN.json OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

r = json.loads(Path(sys.argv[1]).read_text())
pages = r.get("pages") or []
if pages and isinstance(pages[0], dict):
    r["pages"] = [p.get("page_index") for p in pages]
    r["normalized_by"] = "normalize_identity_only.py"
Path(sys.argv[2]).write_text(json.dumps(r, sort_keys=True))
print(f"{sys.argv[2]}: {len(r['pages'])} page numbers, "
      f"{len(r['contextual']['absent_instrument_veto']['staff_slots'])} "
      "staff slots")
