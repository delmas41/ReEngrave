"""2.294: re-adjudicate a saved GATHER slice (flag env as given) and save the full decided record (observations, abstentions, verdicts) as json.
usage: python3 -m benchmarks... no; run as: python3 benchmarks/shared-crossing-test-2026-11/adj_record.py PLATE OUT.json [NAME=V ...]"""
import json, os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
plate, out = sys.argv[1], sys.argv[2]
for a in sys.argv[3:]:
    k, v = a.split("=", 1); os.environ[k] = v
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import lane_report as LR
from tools.omr.staged.review import rerun as RR
src = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/claim-readout-slices-%s.main" % plate)
rec = LR.load_slices(src)
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
res = log.to_json()
pathlib.Path(out).write_text(json.dumps(res, default=str))
print(plate, "obs", len(res["observations"]), "abs", len(res["abstentions"]), "ver", len(res["verdicts"]))
