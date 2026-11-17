"""ROADMAP 2.313 -- one line per facts file: export fates of every glyph and the red-bar kinds (reads only).

    python3 benchmarks/landing-check-2026-11/fates.py A.facts.json [B.facts.json ...]
"""
import collections
import json
import sys

for n in sys.argv[1:]:
    f = json.load(open(n))
    print(n.split("/")[-1])
    print("  fates", collections.Counter(g.get("fate") for g in f["glyphs"].values()).most_common(10))
    print("  bars", {k: len(v) for k, v in f["bars"].items() if hasattr(v, "__len__")})
