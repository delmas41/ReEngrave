"""ROADMAP 2.296 measure (b): one line per (plate, arm, naming) from the `ink_number.json` files `ink_kinds.py --out` wrote.

    python3 benchmarks/dynamics-not-words-2026-11/ink_table.py DIR [DIR ...]      # DIR = out/ink/<plate>-<off|on>[--by-category]
"""
import json
import pathlib
import sys

print("%-34s %10s %10s %10s %10s %9s %9s %9s" % ("run", "dark px", "word px", "dynamic px", "dyn+word", "weak px", "twice px", "none px"))
for d in sys.argv[1:]:
    j = json.load(open(pathlib.Path(d) / "ink_number.json"))
    t = j["total"]
    one = dict(t["one"])["by_kind"]
    lines = dict(t["lines"])
    print("%-34s %10d %10d %10d %10d %9d %9d %9d" % (pathlib.Path(d).name, t["ink_px"], one.get("word", 0), one.get("dynamic", 0),
                                                   one.get("word", 0) + one.get("dynamic", 0), lines["weak"], lines["twice"], lines["none"]))
