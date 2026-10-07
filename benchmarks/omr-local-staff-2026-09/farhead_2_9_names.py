"""lane-farhead-2-9: the instrument the 10-07 record names for every staff ({"staff/p/s/k": name}), for the sheet's captions.
ONE load_record per record; READ ONLY.
  python3 farhead_2_9_names.py <record.json> <out.json>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.staged.record_io import load_record

if __name__ == "__main__":
    res = load_record(sys.argv[1])
    rec = res["record"]
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    out = {}
    for v in rec["verdicts"]:
        if v["id"] in sup or v["quantity"] != "instrument" or v["outcome"] != "decided":
            continue
        val = v.get("value")
        out[v["subject"]] = (val or {}).get("name") if isinstance(val, dict) else str(val)
    Path(sys.argv[2]).write_text(json.dumps(out))
    print(sys.argv[2], len(out))
