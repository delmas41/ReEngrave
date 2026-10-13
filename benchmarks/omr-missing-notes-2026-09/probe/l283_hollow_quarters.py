#!/usr/bin/env python3
"""l283_hollow_quarters: in a record, the black-classed heads whose NOTEHEAD_INK reads decisively hollow (2.23's cut, any of the three readings) and whose standing
duration is nonetheless DECIDED `head_and_marks` -- a hollow-looking head written as the detector's black -- split by the detector box's height in staff spaces
(<= 1.8: one head; > 1.8: a cluster) and by whether the CV beam reader RAN EMPTY on the cell (the beamless-cell shape 2.70 reaches and 2.23's narrowing does not).
ROADMAP 2.83 fix round: how many heads a narrowing in the beamless-cell case would touch, and on how many the answer is a decided half in main.

    python3 l283_hollow_quarters.py rec.json [rec2.json ...]
"""
import collections
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

CENTER_MAX, GAP_MIN = 0.75, 0.1


def hollow(detail):
    for k in ("ink_raw", "ink_net", "ink_off_line"):
        r = detail.get(k)
        if isinstance(r, dict):
            w = r.get("windows") or {}
            c, rg = w.get("center"), w.get("ring")
            if c is not None and rg is not None and c <= CENTER_MAX and (rg - c) >= GAP_MIN:
                return True
    return False


def main():
    NK = int(os.environ.get("NKEYS", "3"))
    for path in sys.argv[1:]:
        run = RD.load_run(path)
        space_of = {o["subject"]: float(o["value"]) for o in run.observations if o["quantity"] == Q.CELL_STAFF_SPACE}
        ink = {}
        for o in run.observations:
            if o["quantity"] == Q.NOTEHEAD_INK:
                ink[o["subject"]] = o.get("detail") or {}
        out = collections.Counter()
        keys = collections.defaultdict(list)
        for key, g in run.glyphs.items():
            if not (g.cls or "").startswith("notehead") or "Black" not in (g.cls or "") or not g.box_canon:
                continue
            d = ink.get(key)
            if not d or not hollow(d):
                continue
            du = run.standing(key, Q.DURATION, "ADJUDICATE")
            if du is None:
                continue
            sp = space_of.get(g.cell_key)
            if not sp:
                continue
            h = (g.box_canon[3] - g.box_canon[1]) / sp
            det = du.get("detail") or {}
            klass = "one_head" if h <= 1.8 else "cluster"
            tag = f"{du.get('outcome')}:{du.get('reason')}|beam_evidence={det.get('beam_evidence')}|{klass}"
            out[tag] += 1
            if len(keys[tag]) < 60:
                keys[tag].append(key)
        print(path.split("/")[-1])
        for tag, n in sorted(out.items(), key=lambda t: -t[1]):
            print(f"   {n:4d}  {tag}   e.g. {keys[tag][:NK]}")


if __name__ == "__main__":
    main()
