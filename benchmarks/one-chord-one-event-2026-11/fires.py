"""2.300 retire-as-you-land: how often do the readers the fix might make redundant FIRE, flag OFF vs ON (env decides).
    OMR_ONE_CHORD_ONE_EVENT=0|1 PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/fires.py PLATE PAGES OUT.json
Counts (all verdicts of the replayed pages): Q.HEAD_STEM by reason; Q.DURATION verdicts carrying `stem_bridge` (OMR_HEAD_STEM_BRIDGE, 2.161);
Q.HEAD_STEM_REACH rows; export drops named chord_value_undecided (2.89 `_chords_whose_value_would_be_voted`); events holding >1 head.
"""
import collections
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
sys.path.insert(0, ".")
from tools.omr.staged import conservation as C, export as E  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

plate, pages, out = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], sys.argv[3]
rows = C.load_pages(plate, pages, C.DEFAULT_TAG)
log, _ = RR.rebuild_gather(rows)
RR.run_stages(log)
rec = log.to_json()
res = {"flag": os.environ.get("OMR_ONE_CHORD_ONE_EVENT"), "plate": plate, "pages": pages}
hs = collections.Counter()
bridge = 0
for v in rec["verdicts"]:
    if v["quantity"] == Q.HEAD_STEM:
        hs[(v["outcome"], v.get("reason"))] += 1
    if v["quantity"] == Q.DURATION and "stem_bridge" in (v.get("detail") or {}):
        bridge += 1
res["head_stem"] = {"%s:%s" % k: n for k, n in sorted(hs.items(), key=lambda t: -t[1])}
res["duration_with_stem_bridge"] = bridge
res["head_stem_reach_rows"] = sum(1 for o in rec["observations"] if o["quantity"] == Q.HEAD_STEM_REACH)
xml, report = E.to_musicxml({"record": rec, "summary": log.summary()})


def find(x, key, acc):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == key and isinstance(v, (int, float)):
                acc.append(v)
            find(v, key, acc)
    elif isinstance(x, list):
        for v in x:
            find(v, key, acc)


acc = []
find(report, "chord_value_undecided", acc)
res["chord_value_undecided"] = acc
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res)[:600])
