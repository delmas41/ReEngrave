"""lane-farhead-vs-geometry: the staff NAMES for the tile captions -- the standing `instrument` verdict per staff, from ONE
load_record (read only).   python3 farhead_vs_geometry_names.py <record.json> <out.json>   ->  {staff key: name}"""
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tools.omr.staged.record_io import load_record


def main(src, dst):
    res = load_record(src)
    rec = res["record"]
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    out = {}
    for v in rec["verdicts"]:
        if v["quantity"] != "instrument" or v["id"] in sup or v["outcome"] != "decided":
            continue
        val = v.get("value")
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                pass
        if isinstance(val, dict) and val.get("name"):
            out[v["subject"]] = val["name"]
    Path(dst).write_text(json.dumps(out))
    print(dst, len(out))


if __name__ == "__main__":
    main(*sys.argv[1:3])
