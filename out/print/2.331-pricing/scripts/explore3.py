import sys, json, collections, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record
res = load_record(sys.argv[1])
r = res["record"]
keys = collections.Counter()
for o in r["observations"]:
    if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("owner") == "word" and o["detail"].get("source") == "direction_word":
        keys.update(o["detail"].keys())
        if "letter_rows" in o["detail"] or "letters_of_word" in o["detail"]:
            print(json.dumps(o, default=str)[:800])
print(keys)
