"""Sean's judged answers scored on two arms by the lane report's own scorer: right -> wrong (must be 0) and the rest (measure only).
python3 judged_arm.py PLATE BASE ARM [ARM ...]   (reads scratch/dd/PLATE.ARM.{mini-record.json,arcs.json})"""
import json
import pathlib
import sys

ROOT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b")
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L     # noqa: E402

D = ROOT / "scratch" / "dd"
plate, base = sys.argv[1], sys.argv[2]
bh = json.load(open(D / ("%s.%s.arcs.json" % (plate, base))))["hosts"]
for arm in sys.argv[3:]:
    ah = json.load(open(D / ("%s.%s.arcs.json" % (plate, arm))))["hosts"]
    try:
        out = L.judged_moves(D / ("%s.%s.mini-record.json" % (plate, base)), D / ("%s.%s.mini-record.json" % (plate, arm)), plate, bh, ah)
    except FileNotFoundError as e:
        print(arm, "no mini-record", e)
        continue
    keys = {k: (len(v) if isinstance(v, list) else v) for k, v in out.items() if k not in ("matched",)}
    print(arm, json.dumps(keys, default=str)[:600])
    for k in ("worse", "lost", "unwritten_wrong"):
        for r in out.get(k, ())[:5]:
            print("   ", k, json.dumps(r, default=str)[:260])
