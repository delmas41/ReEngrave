#!/usr/bin/env python3
"""l283_occupants: which boxes make a head's stem-tip window OCCUPIED, under the NEW window and the OLD one, off a record's own rows
and `gather._stem_tip_blockers` (the observer's own blocker set, the stem's own flag boxes set aside). For every given head: its
decided stem, the end its direction points away from, the window, and each overlapping box with its class and overlap. ROADMAP 2.83
probe.

    python3 l283_occupants.py --record rec.json key [key ...]
"""
import argparse
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    for key in a.keys:
        g = run.glyphs[key]
        cell = g.cell_key
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        if hs is None or hs["outcome"] != "decided" or sd is None or sd["outcome"] != "decided":
            print(key, "no decided stem/direction")
            continue
        sp = float(run.obs_at(cell, Q.CELL_STAFF_SPACE)[-1]["value"])
        stem = next(o["value"] for o in run.obs_at(cell, Q.STEM) if o["id"] == hs["value"])
        x, y, w, h = stem
        sign = 1.0 if sd["value"] == "up" else -1.0
        tip_y = y if sign > 0 else y + h
        dets, beams, heads = [], [], []
        for k2, g2 in run.glyphs.items():
            if g2.cell_key == cell and g2.box_canon:
                x0, y0, x1, y1 = g2.box_canon
                dets.append(types.SimpleNamespace(smufl_name=g2.cls or "", x_canonical=x0, y_canonical=y0,
                                                  width_canonical=x1 - x0, height_canonical=y1 - y0, key=k2))
                if (g2.cls or "").startswith("notehead"):
                    heads.append((x0, y0, x1 - x0, y1 - y0))
        for o in run.obs_at(cell, Q.BEAM_STROKE):
            bx, by, bw, bh = o["value"]
            beams.append(types.SimpleNamespace(smufl_name="BEAM_STROKE(" + str(o.get("reader")) + ")", x_canonical=bx,
                                               y_canonical=by, width_canonical=bw, height_canonical=bh, key=o["id"]))
        edge, here = G._head_edge_for_end(heads, x, x + w, tip_y, sign, sp)
        far = 3.6 if edge is None else min(3.6, (edge - tip_y) * sign / sp - 0.1)
        ny0, ny1 = sorted((tip_y - sign * 0.3 * sp, tip_y + sign * far * sp))
        new = (x + w, ny0, x + w + 1.5 * sp, ny1)
        oy0, oy1 = sorted((tip_y + sign * 1.0 * sp, tip_y + sign * 2.5 * sp))
        old = (x + w, oy0, x + w + 0.9 * sp, oy1)
        tol = 0.1 * sp
        print(f"== {key} direction {sd['value']} tip_y {tip_y:.0f} stem {tuple(round(v) for v in stem)} space {sp:.0f} head_here {here} edge {edge}")
        for name, win in (("NEW", new), ("OLD", old)):
            shr = (win[0] + tol, win[1] + tol, win[2] - tol, win[3] - tol)
            wide = G.DEFAULT_BAND_CONFIG.max_blank_width_spaces * sp if hasattr(G, "DEFAULT_BAND_CONFIG") else None
            hits = []
            for d in beams + dets:
                box = (d.x_canonical, d.y_canonical, d.x_canonical + d.width_canonical, d.y_canonical + d.height_canonical)
                if G._rects_overlap(shr, box):
                    own = G._is_flag_detection(d) and G._flag_box_hangs_off_stem(d, (x, y, w, h), sp)
                    hits.append((d.smufl_name, [round(v) for v in box], "own flag" if own else "", getattr(d, "key", "")))
            print(f"   {name} window {tuple(round(v) for v in win)}: {len(hits)} overlapping boxes")
            for hh in hits[:8]:
                print("      ", hh)


if __name__ == "__main__":
    main()
