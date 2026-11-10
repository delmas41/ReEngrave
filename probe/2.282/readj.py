"""2.280 r2: re-adjudicate the saved 20261104-night slice (flags as the env says) and write it back in slice format
(observations.jsonl / verdicts.jsonl / abstentions.jsonl) into OUT_DIR, so p1_population.py and the micro test read it unchanged.
usage: readj.py PLATE OUT_DIR     (OMR_CLAIM_FINAL=0|1 from the environment)"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import lane_report as LR            # noqa: E402
from tools.omr.staged.review import rerun as RR           # noqa: E402

plate, out = sys.argv[1:3]
t0 = time.time()
rec = LR.load_slices(LR.slice_dir(plate, "20261104-night"))
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
del rec
RR.run_stages(log)
res = log.to_json()
print("keys", list(res), "stages %.0fs" % (time.time() - t0), flush=True)
os.makedirs(out, exist_ok=True)
for k, fn in (("observations", "observations.jsonl"), ("verdicts", "verdicts.jsonl"), ("abstentions", "abstentions.jsonl")):
    with open(os.path.join(out, fn), "w") as f:
        for o in res.get(k, []):
            f.write(json.dumps(o) + "\n")
json.dump({"OMR_CLAIM_FINAL": os.environ.get("OMR_CLAIM_FINAL")}, open(os.path.join(out, "stamp.json"), "w"))
print("done %.0fs" % (time.time() - t0))
