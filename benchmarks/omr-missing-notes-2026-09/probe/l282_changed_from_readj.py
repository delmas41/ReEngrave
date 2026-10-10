#!/usr/bin/env python3
"""l282_changed_from_readj: the heads whose ADJUDICATE duration verdict differs between two `l282_readj.py` arms of one
record (default base -> full), in the `l282_diff.py --json` shape (key, old, new, box in page px, class), for
`l282_tiles.py`. ROADMAP 2.82. A reading probe.

    python3 l282_changed_from_readj.py --prefix DIR/tag --record R --out changed.json [--from base --to full]
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RO  # noqa: E402


def label(s):
    k, b, c, r = s
    if k == "decided":
        return f"decided {b}"
    if k == "narrowed":
        return f"narrowed {r} {list(c)}"
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="frm", default="base")
    ap.add_argument("--to", default="full")
    a = ap.parse_args()
    f = json.load(open(f"{a.prefix}-{a.frm}.json"))["verdicts"]
    t = json.load(open(f"{a.prefix}-{a.to}.json"))["verdicts"]
    run = RO.load_run(a.record)
    out = []
    for k, v in f.items():
        w = t.get(k)
        if w == v or k not in run.glyphs:
            continue
        g = run.glyphs[k]
        out.append({"key": k, "old": label(v), "new": label(w), "box": list(g.box_page) if g.box_page else None,
                    "cls": g.cls, "old_reason": v[3], "new_reason": w[3]})
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"{len(out)} changed heads {a.frm} -> {a.to} -> {a.out}")


if __name__ == "__main__":
    main()
