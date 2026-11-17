"""ROADMAP 2.313 -- list the changed places of one kind between two arms (lane_report's own diff).

    PYTHONPATH=. python3 benchmarks/landing-check-2026-11/changes.py WORKROOT plate BASE OTHER KIND [KIND ...]
"""
import json
import pathlib
import sys

from tools.omr.staged import lane_report as LR

root, plate, base, other = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
load = lambda a: json.loads((root / a / ("%s.%s.symbols.json" % (plate, a))).read_text())
d = LR.diff_arms(load(base), load(other), tol=0.5 * LR.PLATES[plate]["unit"])
for c in d["changes"]:
    if c["kind"] in sys.argv[5:]:
        print({k: (v if k != "host" else None) for k, v in c.items() if k in ("kind", "side", "value", "rg", "page", "box", "was", "now", "measure", "part")}, str(c)[:300])
