"""2.306 r14: replay ONE record (gathered with OMR_PAGE_STEMS=1) through ADJUDICATE..EXPORT on THIS tree (cwd), arm OFF and/or ON, and write
per arm a re-adjudicated record (`OUT.ARM.record.json`) and the 2.311 funnel facts (`OUT.ARM.facts.json`, `extract.py`'s own code), so judge.py
scores a re-adjudicated record against a re-adjudicated record (CLAUDE §6: same stages, same gather).

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-11/2306/r14_replay.py REC.record.json OUTPREFIX [--arms off,on]
"""
import gc
import json
import os
import sys

sys.path[:0] = [os.getcwd(), os.path.join(os.getcwd(), "benchmarks/note-loss-funnel-2026-11")]
from tools.omr.staged.record_io import load_record, dumps_for_file  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402
import extract as X  # noqa: E402

path, outp = sys.argv[1], sys.argv[2]
ARMS = sys.argv[sys.argv.index("--arms") + 1].split(",") if "--arms" in sys.argv else ["off", "on"]
rec = load_record(path)["record"]
obs, abst = rec["observations"], rec["abstentions"]
for arm, on in (("off", "0"), ("on", "1")):
    if arm not in ARMS:
        continue
    os.environ["OMR_PAGE_STEMS"] = on
    log, _ = RR.rebuild_gather({"observations": obs, "abstentions": abst, "verdicts": [], "format": rec.get("format")})
    RR.run_stages(log)
    j = {"record": log.to_json(), "summary": log.summary()}
    j["record"]["provenance"] = dict(rec.get("provenance") or {}, r14_replay=dict(arm=arm, source=path))
    rp = "%s.%s.record.json" % (outp, arm)
    with open(rp, "w") as f:
        f.write(dumps_for_file(j))
    del log, j
    gc.collect()
    X.main(rp, "%s.%s.facts.json" % (outp, arm))
    print(arm, "done", rp, flush=True)
