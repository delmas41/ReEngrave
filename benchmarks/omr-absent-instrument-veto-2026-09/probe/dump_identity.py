"""Per-staff identity as the JSON records it: page, system, staff, slot, name, source."""
from __future__ import annotations
import json
import sys

path = sys.argv[1]
r = json.load(open(path))
ctx = r.get("contextual") or {}
print("reference:", [s.get("instrument") for s in ctx.get("reference", [])])
print("instruments_from_score_order =", ctx.get("instruments_from_score_order"),
      " from_roster =", ctx.get("instruments_from_roster"),
      " ambiguous_resolved =", ctx.get("ambiguous_labels_resolved"))
print("vetoed_absent_instruments =", len(ctx.get("absent_instrument_vetoes", []) or []))
n = 0
for page in r.get("pages", []):
    pi = page.get("page_index")
    for sy in page.get("systems", []):
        si = sy.get("system_index")
        names, srcs, labs = [], [], []
        for st in sy.get("staves", []):
            n += 1
            names.append(st.get("instrument") or "-")
            srcs.append((st.get("instrument_source") or "-")[:5])
            labs.append((st.get("instrument_label") or "").strip() or "-")
        print(f"  p{pi}.s{si} ({len(names)}): " + " | ".join(names))
        print(f"        src : " + " | ".join(srcs))
        print(f"        lab : " + " | ".join(labs))
print("staff-records:", n)
