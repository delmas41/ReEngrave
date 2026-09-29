"""ROADMAP 2.21 pricing: `Q.VOICES`' own reason census on one record,
re-decided in-process with the tree this file sits in (`review.rerun`, no
re-gather). Run once on a base tree (no 2.21) and once on the arm (with it)
and diff the two JSON dumps.

    python3 .../price_voices_2_21.py <record.json> --out <dump.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from tools.omr.staged.record import Q, Outcome
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    doc = load_record(a.record)
    rec = doc["record"] if "record" in doc else doc
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)

    by_reason = collections.Counter()
    two_voice_cells = []
    for v in log.all_verdicts():
        if v.quantity != Q.VOICES:
            continue
        by_reason[(v.outcome.value if hasattr(v.outcome, "value")
                  else str(v.outcome), v.reason)] += 1
        if v.outcome is Outcome.DECIDED and isinstance(v.value, dict) \
                and int(v.value.get("n_voices") or 1) >= 2:
            two_voice_cells.append(v.subject)

    out = {"record": a.record, "by_reason": {f"{k[0]}/{k[1]}": n
                                             for k, n in by_reason.items()},
           "n_two_voice_cells": len(two_voice_cells),
           "two_voice_cells": sorted(two_voice_cells)}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out["by_reason"], indent=1))
    print("n_two_voice_cells", out["n_two_voice_cells"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
