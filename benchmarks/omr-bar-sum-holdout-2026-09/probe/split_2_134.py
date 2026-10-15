"""ROADMAP 2.134: split an enriched dump into held / partial dumps (by the `kind`
held_funnel_2_134.py set), so classify_held_2_96.py (unchanged) runs on each and
its own partition-sums control applies per kind.

    python3 .../split_2_134.py <label-2.134.held.json>   -> <label>-held.json, <label>-partial.json
"""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
d = json.load(open(p))
base = p.name.split("-2.134")[0]
for kind in ("held", "partial"):
    e = dict(d)
    e["bars"] = [b for b in d["bars"] if b["kind"] == kind]
    e["label"] = f"{base}-{kind}"
    out = p.with_name(f"{base}-{kind}.json")
    json.dump(e, open(out, "w"), default=str)
    print(kind, len(e["bars"]), "->", out)
