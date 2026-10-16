"""ROADMAP 2.153 -- write a MINI record (the slice's observations + the replay's verdicts) per ARM, so
`python3 -m tools.omr.staged.judged score REC --doc DOC` can score it against Sean's judged index (his answers are the truth).
Tiles outside the slice's systems come out `not_found`, identically in both arms.
usage: replay_record_2_153.py SLICE.json OUTPREFIX ARM [ARM ...]      ARM = name  or  name:ENV=val,ENV2=val
-> OUTPREFIX.<name>.record.json"""
import json
import os
import sys

sys.path.insert(0, ".")
SL, PREFIX = sys.argv[1:3]
rec = json.load(open(SL))
from tools.omr.staged.review import rerun as RR  # noqa: E402

sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import replay_util_2_153 as RU  # noqa: E402

for arm in sys.argv[3:]:
    name, _, env = arm.partition(":")
    saved = {}
    for kv in [e for e in env.split(",") if e]:
        k, v = kv.split("=")
        saved[k] = os.environ.get(k)
        os.environ[k] = v
    log, _ = RU.rebuild(rec)
    RR.run_stages(log)
    d = log.to_json()
    json.dump({"record": {"observations": rec["observations"], "abstentions": [], "verdicts": d["verdicts"]}},
              open("%s.%s.record.json" % (PREFIX, name), "w"), default=str)
    print(name, len(d["verdicts"]), flush=True)
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
