"""ROADMAP 2.141h -- the systems (page,system) of every bar that matters, as the --staves argument of arm_2_141h.py.
    python3 staves_2_141h.py lit|brah   (reads out/2.141/causes-*.json, 2.141/tiles-key.json, 2.136-step2/tiles-key.json)"""
import json, sys
from pathlib import Path
O = Path(__file__).resolve().parent.parent / "out"
mov = sys.argv[1]
cells = [c["cell"] for c in json.load(open(O / f"2.141/causes-{mov}.json"))]
if mov == "lit":
    cells += [t["cell"] for t in json.load(open(O / "2.141/tiles-key.json"))["tiles"]]
cells += [t["cell"] for t in json.load(open(O / "2.136-step2/tiles-key.json"))["tiles"] if t["movement"] == mov]
print(";".join(f"{a},{b}" for a, b in sorted({tuple(c[:2]) for c in cells})))
