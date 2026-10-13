"""ROADMAP 2.102: how many `collapse_bare_stem_by_bar` settlements are shorter
than the stem's longest candidate (Sean 2026-10-12: no eighth without a flag/beam)?

    python3 benchmarks/omr-held-out-2026-10/p102_eighths.py REC [REC ...]
"""
import collections
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

for path in sys.argv[1:]:
    r = load_record(path)["record"]
    c = collections.Counter()
    for v in r["verdicts"]:
        if v["decider"] == "infer:collapse_bare_stem_by_bar" and v["outcome"] == "decided":
            c["settled"] += 1
            c[f"beats={v['value'].get('beats')}"] += 1
    print(path.split("/")[-1], dict(c))
