#!/usr/bin/env python3
"""l281_miss_rows: stream the GATHER rows of a few PAGES out of a whole-movement record into a small
JSON, so one page can be re-adjudicated (`l281_miss_rebuild.py`) without loading the 5.3 GB record
(`record_io.load_record` is ~6.6x the file resident; this is the `ijson` reader of `l281_extract.py`).

Keeps every observation and abstention whose subject is on one of the pages, plus the document-level
rows (a subject with no page). Also keeps, per page, the SAVED ADJUDICATE duration verdicts (outcome,
reason, candidates) -- the control the rebuild is compared against.

    python3 l281_miss_rows.py --record R --pages 0,2,7 --out rows.json
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")}
    t0 = time.time()
    out = {"pages": sorted(pages), "observations": [], "abstentions": [], "saved_duration": {}}
    with open(a.record, "rb") as fh:
        for o in ijson.items(fh, "record.observations.item", use_float=True):
            p = page_of(o["subject"])
            if p is None or p in pages:
                out["observations"].append(o)
    print(f"observations kept {len(out['observations'])} {time.time() - t0:.0f}s", flush=True)
    with open(a.record, "rb") as fh:
        for o in ijson.items(fh, "record.abstentions.item", use_float=True):
            p = page_of(o["subject"])
            if p is None or p in pages:
                out["abstentions"].append(o)
    print(f"abstentions kept {len(out['abstentions'])} {time.time() - t0:.0f}s", flush=True)
    with open(a.record, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            if v["quantity"] != Q.DURATION or v["decider"] != "adjudicate_duration":
                continue
            p = page_of(v["subject"])
            if p in pages:
                out["saved_duration"][v["subject"]] = {
                    "outcome": v["outcome"], "reason": v.get("reason"), "value": v.get("value"),
                    "cands": [c.get("value") for c in (v.get("candidates") or [])]}
    print(f"saved duration verdicts {len(out['saved_duration'])} {time.time() - t0:.0f}s", flush=True)
    Path(a.out).write_text(json.dumps(out, separators=(",", ":"), default=str))
    print(f"wrote {a.out} ({Path(a.out).stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
