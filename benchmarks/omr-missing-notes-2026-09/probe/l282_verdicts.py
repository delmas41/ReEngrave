#!/usr/bin/env python3
"""l282_verdicts: the standing `Q.DURATION` verdicts (every stage) of named note-head subjects, streamed
from a record, with the verdict's `detail` (the strokes it counted and refused, by id). ROADMAP 2.82.
A reading probe.

    python3 l282_verdicts.py --record R --heads glyph/0/0/0/3/3,glyph/0/0/0/4/6 [--prefix glyph/0/0/0/3/]
"""
import argparse
import json
import sys
from pathlib import Path

import ijson

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged.record import Q  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--heads", default="")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--decider", default="adjudicate_duration")
    ap.add_argument("--max", type=int, default=50)
    a = ap.parse_args()
    want = {h for h in a.heads.split(",") if h}
    n = 0
    with open(a.record, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            if v["quantity"] != Q.DURATION:
                continue
            s = v["subject"]
            if not ((want and s in want) or (a.prefix and s.startswith(a.prefix))):
                continue
            if a.decider and v["decider"] != a.decider:
                continue
            slim = {k: v[k] for k in v if k not in ("basis", "considered", "correlated")}
            print(json.dumps(slim, default=str)[:2500])
            print()
            n += 1
            if n >= a.max:
                break


if __name__ == "__main__":
    main()
