"""Shrink a transcription to the part this benchmark reasons about.

A whole-work run is ~100 MB of detections; the veto reads four things — each
staff's page, system, index and emitted name, plus the `report` block. The
extract keeps the same SHAPE as the full JSON (`pages[].systems[].staves[]`,
`contextual.absent_instrument_veto`), so every probe here runs on it unchanged
and the committed artefact is the one the numbers were computed from.

Usage:  extract.py FULL.json OUT.json
"""
from __future__ import annotations

import json
import sys

src, dst = sys.argv[1], sys.argv[2]
r = json.load(open(src))
out = {
    "source": src,
    "source_pdf": r.get("source_pdf"),
    "pages": [
        {"page_index": p.get("page_index"),
         "systems": [
             {"system_index": s.get("system_index"),
              "staves": [
                  {"staff_index": st.get("staff_index"),
                   "instrument": st.get("instrument"),
                   "instrument_source": st.get("instrument_source"),
                   "instrument_veto": st.get("instrument_veto"),
                   "slot_index": st.get("slot_index"),
                   "staff_geometry": {"line_ys_page": (
                       st.get("staff_geometry", {}).get("line_ys_page") or [0])[:1]}}
                  for st in s.get("staves", [])]}
             for s in p.get("systems", [])]}
        for p in r.get("pages", [])],
    "contextual": {
        k: (r.get("contextual") or {}).get(k)
        for k in ("reference", "absent_instrument_veto",
                  "instruments_from_score_order", "instruments_from_roster",
                  "ambiguous_labels_resolved", "labelled_staves")},
}
json.dump(out, open(dst, "w"), sort_keys=True)
print(f"{dst}: pages={len(out['pages'])} "
      f"staves={sum(len(s['staves']) for p in out['pages'] for s in p['systems'])}")
