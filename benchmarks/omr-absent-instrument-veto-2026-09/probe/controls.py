"""The pre-registered controls, all of them, at one window.

Each row is a claim someone can check: the page set, how many vetoes fire, and
what they are. A control that must fire nothing prints `0`.

Usage:  controls.py [window] [rule]
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from show_vetoes import load                                   # noqa: E402
from tools.omr.absent_instrument import find_vetoes            # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"

CONTROLS = [
    ("report-p1p44.extract.json", "beethoven --pages 1,44", "must fire 0"),
    ("brahms-p10.extract.json", "brahms --pages 10", "must fire 0"),
    ("brahms-p10p75.extract.json", "brahms --pages 10,75", "must fire 0"),
    ("report-p23p44.extract.json", "beethoven --pages 23,44",
     "must remove 6 trombones"),
]


def main(window=0, rule="span"):
    print(f"rule={rule} window={window}")
    for name, label, expect in CONTROLS:
        path = OUT / name
        if not path.exists():
            print(f"  {label:26s} MISSING {name}")
            continue
        _r, ev, sbs, nm, src, refn = load(path)
        vs = find_vetoes(staff_keys=list(sbs), slot_by_staff=sbs,
                         instrument_name_by_slot=nm, instrument_source=src,
                         evidence=ev, window=window, rule=rule,
                         reference_size=refn)
        c = collections.Counter(v["instrument"] for v in vs)
        detail = ", ".join(f"{k} x{v}" for k, v in c.most_common()) or "-"
        print(f"  {label:26s} vetoes={len(vs):3d}  {detail:40s} ({expect})")


if __name__ == "__main__":
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    r = sys.argv[2] if len(sys.argv) > 2 else "span"
    main(w, r)
