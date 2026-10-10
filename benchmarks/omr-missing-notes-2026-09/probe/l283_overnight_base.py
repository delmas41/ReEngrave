#!/usr/bin/env python3
"""l283_overnight_base: the standing ADJUDICATE `Q.DURATION` verdicts of chosen PAGES out of a whole-movement record, streamed
with `ijson` (the 5.3 GB Brahms record is never loaded: `load_record` is ~6.6x the file), as the BASE of heads on pages this
lane did not re-gather on the base tree. Valid as a base only because `tools/omr/staged/{gather,adjudicators}` and the
readers are byte-identical between the record's tree (`26fdb4d0`, dirty False) and this lane's base (`faf913f4`):
`git diff --stat 26fdb4d0 faf913f4 -- tools/omr/staged/gather.py tools/omr/staged/adjudicators` is empty (FINDINGS 2.83). The
2.81 lane's own control reproduced every saved duration verdict on nine of these pages exactly (FINDINGS 17.9).

    python3 l283_overnight_base.py --record R --pages 1,2,3 --out base.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

import ijson

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged.record import Q  # noqa: E402


def page_of(subject):
    p = subject.split("/")
    if len(p) >= 2 and p[0] != "document":
        try:
            return int(p[1])
        except ValueError:
            return None
    return None


def levels(v):
    if v["outcome"] == "decided":
        val = v.get("value")
        return [val.get("beam_levels")] if isinstance(val, dict) else []
    out = []
    for c in v.get("candidates") or []:
        val = c.get("value") if isinstance(c, dict) else None
        if isinstance(val, dict):
            out.append(val.get("beam_levels"))
    return sorted({x for x in out if x is not None})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")}
    t0 = time.time()
    out = {}
    with open(a.record, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            if v["quantity"] != Q.DURATION or v["decider"] != "adjudicate_duration":
                continue
            if page_of(v["subject"]) not in pages:
                continue
            out[v["subject"]] = {"outcome": v["outcome"], "reason": v.get("reason"), "levels": levels(v)}
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")))
    print(f"{len(out)} verdicts on pages {sorted(pages)} in {time.time() - t0:.0f}s -> {a.out}")


if __name__ == "__main__":
    main()
