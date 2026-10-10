#!/usr/bin/env python3
"""l281_peek: print everything a record holds about a few `beam_discounted_uncertain`
heads -- the schema look that precedes `l281_extract.py` (ROADMAP 2.81, Phase 1).

Reads a record with `ijson` (CLAUDE.md §5a: `load_record` needs ~6.6x the file).
A reading probe only; it decides nothing and writes nothing but stdout.

    python3 l281_peek.py RECORD [--n 3] [--reason beam_discounted_uncertain]
"""
import argparse
import json
import sys
from pathlib import Path

import ijson

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged.record import Q  # noqa: E402


def short(o, n=700):
    s = json.dumps(o, default=str)
    return s if len(s) <= n else s[:n] + f"...<{len(s)}>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--reason", default="beam_discounted_uncertain")
    a = ap.parse_args()

    picked = []
    with open(a.record, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            if v["quantity"] == Q.DURATION and v.get("reason") == a.reason \
                    and v["decider"] == "adjudicate_duration":
                picked.append(v["subject"])
                if len(picked) >= a.n:
                    break
    print("picked", picked)
    cells = {}
    for k in picked:
        p = k.split("/")
        cells[k] = "cell/" + "/".join(p[1:5])
    want_subj = set(picked) | set(cells.values())

    print("\n=== verdicts on the heads (all stages) ===")
    with open(a.record, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            if v["subject"] in picked:
                v = dict(v)
                v.pop("basis", None)
                v.pop("considered", None)
                v.pop("correlated", None)
                print(short(v))
    print("\n=== observations on the heads and their cells ===")
    with open(a.record, "rb") as fh:
        for o in ijson.items(fh, "record.observations.item", use_float=True):
            if o["subject"] in want_subj and o["quantity"] in (
                    Q.GLYPH_BOX, Q.STEM, Q.STEM_TIP_INK, Q.STEM_SLASH,
                    Q.NOTEHEAD_INK, Q.HEAD_STEM_REACH, Q.BEAM_STROKE_INK,
                    Q.BEAM_STROKE, Q.NOTEHEAD_CLASS, Q.AUG_DOT):
                o = dict(o)
                o.pop("basis", None)
                print(short(o, 500))
    print("\n=== abstentions on the cells ===")
    with open(a.record, "rb") as fh:
        for o in ijson.items(fh, "record.abstentions.item", use_float=True):
            if o["subject"] in want_subj and o["quantity"] in (
                    Q.STEM_TIP_INK, Q.STEM_SLASH, Q.BEAM_STROKE):
                o = dict(o)
                o.pop("basis", None)
                print(short(o, 500))


if __name__ == "__main__":
    main()
