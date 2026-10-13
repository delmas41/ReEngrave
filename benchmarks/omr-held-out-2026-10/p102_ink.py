"""ROADMAP 2.102 probe: the unclassified ink components (`Q.INK`) of one cell.

    python3 benchmarks/omr-held-out-2026-10/p102_ink.py REC cell/p/s/st/c
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

r = load_record(sys.argv[1])["record"]
c = sys.argv[2]
n = 0
for o in r["observations"]:
    if o["quantity"] == "ink" and (o["subject"] == c or o["subject"].startswith(c + "/")):
        n += 1
        print(o["subject"], str(o["value"])[:60],
              {k: v for k, v in (o.get("detail") or {}).items() if len(str(v)) < 90})
print("ink rows:", n)
