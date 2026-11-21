import sys, json, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record
res = load_record(sys.argv[1])
r = res["record"]
obs = {o["id"]: o for o in r["observations"]}
n = 0
for v in r["verdicts"]:
    if v["quantity"] == "dynamic" and v.get("value"):
        print(json.dumps({k: x for k, x in v.items() if k not in ("considered", "correlated")}, default=str)[:2000])
        for u in v.get("used") or ():
            if u in obs:
                print("  used", json.dumps(obs[u], default=str)[:400])
        n += 1
        if n >= 2:
            break
for o in r["observations"]:
    if o["quantity"] == "direction_word":
        print(json.dumps(o, default=str)[:600]); break
for o in r["observations"]:
    if o["quantity"] == "dynamic_letter_neighbours":
        print(json.dumps(o, default=str)[:600]); break
