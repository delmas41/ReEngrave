"""ROADMAP 2.102 probe: durations ADJUDICATE filed on a head it had already
refused as a notehead.

    python3 benchmarks/omr-held-out-2026-10/p102_refused.py REC [REC ...]
(final adjudicate-stage verdict per glyph; inferred rows are skipped)
"""
import collections
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

for path in sys.argv[1:]:
    r = load_record(path)["record"]
    refused = {}
    dur = {}
    for v in r["verdicts"]:
        if v["quantity"] == "notehead_is_not_a_notehead" and v["outcome"] == "decided" \
                and v["value"] is True:
            refused[v["subject"]] = v["reason"]
        if v["quantity"] == "duration" and v["decider"] == "adjudicate_duration":
            dur[v["subject"]] = v
    c = collections.Counter()
    for s, why in refused.items():
        d = dur.get(s)
        c[(why, "no duration" if d is None else f"{d['outcome']}:{d['reason']}")] += 1
    print(path.split("/")[-1], "refused heads:", len(refused))
    for (why, what), n in c.most_common(14):
        print("   ", n, why, "->", what)
