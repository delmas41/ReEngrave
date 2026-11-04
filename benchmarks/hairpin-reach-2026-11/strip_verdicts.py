"""ROADMAP 2.261: a gathered record with its verdicts removed, so `reuse_gathers.py` re-runs ADJUDICATE..EXPORT in BOTH arms from the same
GATHER rows (a record written by the lane report's gather carries the OFF tree's verdicts, which an ON arm would keep -- fix 3 first
read 'words -14' and no pitch change because of that).

    python3 benchmarks/hairpin-reach-2026-11/strip_verdicts.py IN.record.json OUT.record.json
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged.record_io import load_record  # noqa: E402

whole = load_record(sys.argv[1])
rec = whole.get("record", whole)
print("verdicts before", len(rec.get("verdicts") or ()))
rec["verdicts"] = []
pathlib.Path(sys.argv[2]).write_text(json.dumps(whole, default=str))
print("wrote", sys.argv[2])
