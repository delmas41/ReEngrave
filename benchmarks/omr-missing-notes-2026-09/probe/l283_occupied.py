#!/usr/bin/env python3
"""l283_occupied: how often the tip window is OCCUPIED (a beam stroke or another detection overlaps it, so the reader abstains
before it looks), under the OLD window (1.0-2.5 spaces back, 0.9 wide) and the NEW one (from 0.3 past the tip back to the stem's
own head or 3.6 spaces, 1.5 wide), per stem end, off a saved record's own rows and `gather._stem_tip_blockers`; and WHICH
detection classes (or CV beam strokes) are the occupants. The new window is bigger, so it can only block more: this prices that.
ROADMAP 2.83 probe.

    python3 l283_occupied.py --record rec.json [--pages 0,1]
"""
import argparse
import collections
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def det(name, v):
    return types.SimpleNamespace(smufl_name=name, x_canonical=float(v[0]), y_canonical=float(v[1]),
                                 width_canonical=float(v[2]), height_canonical=float(v[3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pages", default=None)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    run = RD.load_run(a.record)
    by_cell = collections.defaultdict(lambda: {"dets": [], "beams": [], "stems": [], "heads": [], "space": None})
    for k, g in run.glyphs.items():
        if pages is not None and g.page not in pages:
            continue
        c = by_cell[g.cell_key]
        if g.box_canon:
            x0, y0, x1, y1 = g.box_canon
            c["dets"].append(det(g.cls or "", (x0, y0, x1 - x0, y1 - y0)))
            if (g.cls or "").startswith("notehead"):
                c["heads"].append((x0, y0, x1 - x0, y1 - y0))
    stem_obs = {}
    for o in run.observations:
        q = o["quantity"]
        if q not in (Q.STEM, Q.BEAM_STROKE, Q.CELL_STAFF_SPACE):
            continue
        sub = o["subject"]
        if not sub.startswith("cell/"):
            continue
        p = int(sub.split("/")[1])
        if pages is not None and p not in pages:
            continue
        c = by_cell[sub]
        if q == Q.STEM:
            c["stems"].append((o["id"], tuple(o["value"])))
        elif q == Q.BEAM_STROKE:
            c["beams"].append(det("beam", o["value"]))
        else:
            c["space"] = float(o["value"])
    tally = collections.Counter()
    cls_of = {}
    occupants = collections.Counter()
    occ_old = collections.Counter()
    occ_new = collections.Counter()
    newly = collections.Counter()
    for ck, c in by_cell.items():
        sp = c["space"]
        if not sp:
            continue
        for sid, (x, y, w, h) in c["stems"]:
            x0, x1 = x, x + w
            for end, tip_y, sign in (("top", y, 1.0), ("bottom", y + h, -1.0)):
                blockers = G._stem_tip_blockers(c["beams"], c["dets"], sp, own_stem=(x, y, w, h))
                tol = G.STEM_TIP_BLOCKER_TOLERANCE_SPACES * sp
                edge, here = G._head_edge_for_end(c["heads"], x0, x1, tip_y, sign, sp)
                # old window
                wy0, wy1 = sorted((tip_y + sign * 1.0 * sp, tip_y + sign * 2.5 * sp))
                old = (x1, wy0, x1 + 0.9 * sp, wy1)
                far = 3.6 if edge is None else min(3.6, (edge - tip_y) * sign / sp - 0.1)
                far = max(far, -0.3)
                ny0, ny1 = sorted((tip_y - sign * 0.3 * sp, tip_y + sign * far * sp))
                new = (x1, ny0, x1 + 1.5 * sp, ny1)

                def hit(win):
                    shr = (win[0] + tol, win[1] + tol, win[2] - tol, win[3] - tol)
                    return [b for b in blockers if G._rects_overlap(shr, b)]
                ho, hn = hit(old), hit(new)
                if not here:
                    tally["tips_nonhead"] += 1
                    tally["occupied_old_nonhead"] += int(bool(ho))
                    tally["occupied_new_nonhead"] += int(bool(hn))
                    for b in hn:
                        cls_of[id(b)] = getattr(b, "smufl_name", "?")
                    for cl in {getattr(b, "smufl_name", "?") for b in hn}:
                        occupants[cl] += 1
                tally["ends"] += 1
                tally["head_at_this_end"] += int(here)
                if ho:
                    tally["occupied_old"] += 1
                if hn:
                    tally["occupied_new"] += 1
                if hn and not ho:
                    tally["newly_occupied"] += 1
                    newly[len(hn)] += 1
                if not hn and ho:
                    tally["newly_free"] += 1
    print(dict(tally))
    print('occupant classes under the NEW window, non-head ends (ends blocked by at least one box of that class):')
    for k, n in occupants.most_common(14):
        print('  ', n, k)


if __name__ == "__main__":
    main()
