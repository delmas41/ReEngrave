"""2.279: print every verdict (brief) of the given subjects, newest standing per quantity (READ-ONLY).

usage: python3 probe/2.279/show.py RECORD SUB [SUB...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT          # noqa: E402,F401
from tools.omr.staged.record_io import load_record      # noqa: E402

d = load_record(sys.argv[1])
rec = EXPORT.Record(d) if hasattr(EXPORT, "Record") else d
subs = set(sys.argv[2:])
for v in rec.verdicts:
    if v["subject"] in subs:
        val = v.get("value")
        if isinstance(val, dict):
            val = {k: val[k] for k in list(val)[:6]}
        print(v["subject"], v["quantity"], v["outcome"], v.get("reason"), v.get("decider"), json.dumps(val, default=str)[:160],
              json.dumps([(c.get("value") if not isinstance(c.get("value"), dict) else c["value"].get("beats"), c.get("support")) for c in (v.get("candidates") or ())], default=str)[:200])
