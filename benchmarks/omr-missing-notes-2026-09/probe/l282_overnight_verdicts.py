#!/usr/bin/env python3
"""l282_overnight_verdicts: the standing ADJUDICATE `Q.DURATION` verdict of every note head on named pages of an
OVERNIGHT whole-movement record, streamed (the Brahms record is 5.3 GB), in the summary shape `l282_diff.py`
uses: `[kind, beats, candidates, reason]`. ROADMAP 2.82. A reading probe.

WHY IT IS A VALID BASE. The overnight record's tree (main `26fdb4d0`) and this lane's base (`d4131ce4`) differ in
`tools/` only by the hand-truth scorer and ROADMAP 2.79 (EVALUATE/EXPORT), and the control below compares this
file with a fresh base gather of pages 0-1 / 0-3: every head's verdict must agree (a mismatch is printed).

    python3 l282_overnight_verdicts.py --record R --pages 23,18,12 --out base.json
"""
import argparse
import json
import sys
from pathlib import Path

import ijson

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import trace  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def beats(v):
    return v.get("beats") if isinstance(v, dict) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")}
    stage_cache = {}
    out = {}
    with open(a.record, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            if v["quantity"] != Q.DURATION:
                continue
            s = v["subject"]
            p = s.split("/")
            if p[0] != "glyph" or int(p[1]) not in pages:
                continue
            dec = v["decider"]
            if dec not in stage_cache:
                stage_cache[dec] = trace.stage_of_decider(dec)
            if stage_cache[dec] != "ADJUDICATE":
                continue
            if v["outcome"] == "decided":
                out[s] = ["decided", beats(v.get("value")), None, v.get("reason")]
            elif v["outcome"] == "narrowed":
                c = sorted({beats(x.get("value")) for x in (v.get("candidates") or []) if beats(x.get("value")) is not None})
                out[s] = ["narrowed", None, c, v.get("reason")]
            else:
                out[s] = [v["outcome"], None, None, v.get("reason")]
    Path(a.out).write_text(json.dumps(out))
    print(f"{len(out)} heads' ADJUDICATE duration verdicts on pages {sorted(pages)} -> {a.out}")


if __name__ == "__main__":
    main()
