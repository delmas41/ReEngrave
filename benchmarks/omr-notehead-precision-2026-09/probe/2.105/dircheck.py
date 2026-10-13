"""Why did `direction` change on cell/2/1/7/0? usage: dircheck.py BASE ARM CELLKEY"""
import json
import sys

from tools.omr.staged.readout import load_run

for p in sys.argv[1:3]:
    run = load_run(p)
    for s, k, r in run.rows_at(sys.argv[3]):
        if k == "verdict" and r["quantity"] == "direction":
            print(p.split("/")[-4], r["outcome"], r["reason"], json.dumps(r.get("value"))[:200], json.dumps(r.get("detail"))[:300])
    words = [r for s, k, r in run.rows_at(sys.argv[3]) if k == "observation" and "word" in r["quantity"]]
    print("  word obs", [(r["quantity"], str(r["value"])[:30]) for r in words][:6])
