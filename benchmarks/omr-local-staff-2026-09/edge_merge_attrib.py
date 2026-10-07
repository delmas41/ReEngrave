"""lane-edge-merge-unseen-ledgers (2026-10-06): which switch changed how many heads. BEFORE = the per-bar-grid reader with the four switches
off (`farhead_per_bar_grid_oos.py scan` 'new' arm); each AFTER = `edge_merge_oos.py scan` with EM_ONLY=<switch> (or all on).

  python3 edge_merge_attrib.py before.json all_on.json only_a.json only_b.json ...
"""
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_per_bar_grid_report as R


def reads(path):
    out = {}
    for s, r in json.loads(Path(path).read_text())["heads"].items():
        if r.get("new"):
            out[s] = r["new"]["read"]
    return out


if __name__ == "__main__":
    before = reads(sys.argv[1])
    for p in sys.argv[2:]:
        after = reads(p)
        c = collections.Counter()
        for s, b in before.items():
            a = after.get(s)
            if a is None:
                continue
            c["n"] += 1
            c["decided_before"] += b["pos"] is not None
            c["decided_after"] += a["pos"] is not None
            c["implausible_before"] += R.implausible(b)
            c["implausible_after"] += R.implausible(a)
            if b["pos"] is None and a["pos"] is not None:
                c["abstain->decided"] += 1
            elif b["pos"] is not None and a["pos"] is None:
                c["decided->abstain"] += 1
            elif b["pos"] != a["pos"]:
                c["moved"] += 1
        print(Path(p).name, dict(c))
