#!/usr/bin/env python3
"""l283_hollow_boxes: over a record, every notehead-classed glyph whose standing ADJUDICATE duration is `hollow_head_bare_stem` (2.70's decided
half) or whose NOTEHEAD_INK reads decisively hollow (2.23's cut: center <= 0.75 and ring - center >= 0.1 on ANY of the three readings), with
its detector box measured in STAFF SPACES (height, width) -- a notehead is about 1.0-1.4 spaces tall and 1.3 wide (CLAUDE.md 10), so a box
2.5 spaces tall is not one head and the fill windows laid inside it measure the wrong thing (Sean's tile 10, Litolff pdf 15
`glyph/15/1/3/17/5`: a filled quarter, read hollow, box 2.8 spaces tall). ROADMAP 2.83 fix round probe. Read-only.

    python3 l283_hollow_boxes.py rec.json [rec2.json ...] [--bins]
"""
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

CENTER_MAX, GAP_MIN = 0.75, 0.1


def hollow_by_ink(detail):
    for k in ("ink_raw", "ink_net", "ink_off_line"):
        r = detail.get(k)
        if not isinstance(r, dict):
            continue
        w = r.get("windows") or {}
        c, rg = w.get("center"), w.get("ring")
        if c is None or rg is None:
            continue
        if c <= CENTER_MAX and (rg - c) >= GAP_MIN:
            return True
    return False


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    for path in paths:
        run = RD.load_run(path)
        space_of = {}
        for o in run.observations:
            if o["quantity"] == Q.CELL_STAFF_SPACE:
                space_of[o["subject"]] = float(o["value"])
        rows = []
        for key, g in run.glyphs.items():
            if not (g.cls or "").startswith("notehead") or not g.box_canon:
                continue
            ink = [o for o in run.observations if False]
            du = run.standing(key, Q.DURATION, "ADJUDICATE")
            sp = space_of.get(g.cell_key)
            if not sp:
                continue
            x0, y0, x1, y1 = g.box_canon
            rows.append((key, g.cls, (y1 - y0) / sp, (x1 - x0) / sp, du and du.get("reason")))
        print(path, len(rows), "heads with a box")
        by = collections.defaultdict(list)
        for key, cls, h, w, reason in rows:
            by[reason].append((h, w, key))
        for reason in ("hollow_head_bare_stem", "head_fill_from_ink", "head_and_marks"):
            hs = sorted(h for h, _w, _k in by.get(reason, []))
            if not hs:
                continue
            n = len(hs)
            q = lambda p: hs[min(n - 1, int(p * n))]
            print(f"  {reason:24s} n={n:5d} height spaces: min {hs[0]:.2f} p10 {q(.1):.2f} median {q(.5):.2f} p90 {q(.9):.2f} p99 {q(.99):.2f} max {hs[-1]:.2f}; "
                  f">1.8: {sum(1 for h in hs if h > 1.8)}  >2.2: {sum(1 for h in hs if h > 2.2)}")
        tall = sorted(((h, w, k) for h, w, k in by.get("hollow_head_bare_stem", []) if h > 1.8), reverse=True)
        for h, w, k in tall[:25]:
            print(f"     TALL hollow-decided {k}  h {h:.2f} w {w:.2f}")


if __name__ == "__main__":
    main()
