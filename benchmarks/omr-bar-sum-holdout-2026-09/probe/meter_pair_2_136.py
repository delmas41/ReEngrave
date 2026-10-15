"""2.136: print a carried meter verdict beside the verdict it was carried from, for k systems of a depth file.

    python3 meter_pair_2_136.py RECORD brah-meter-depth.json k
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, depth_path, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
rows = [r for r in json.load(open(depth_path))["rows"] if r.get("end") == "changed_between_systems"]
want = {f"system/{r['cell'][0]}/{r['cell'][1]}" for r in rows[:: max(1, len(rows) // k)][:k]}
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
by_id = {v["id"]: v for v in rec["verdicts"] if v["quantity"] == "meter"}
for v in by_id.values():
    if v["subject"] in want and v["reason"] in ("carried", "carried_uncontested"):
        src = next((by_id[r] for r in v.get("used") or () if r in by_id), None)
        print(v["subject"], v["reason"], json.dumps(v["value"])[:260])
        print("   FROM", src["subject"] if src else None, src["reason"] if src else None,
              json.dumps(src["value"])[:260] if src else None)
