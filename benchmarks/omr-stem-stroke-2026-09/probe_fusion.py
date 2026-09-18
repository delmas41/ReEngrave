"""IS THE INK ACTUALLY FUSED? The blob distribution, on both publishers.

⚠️⚠️ THIS PROBE EXISTS TO CHECK A PREMISE I WAS HANDED, NOT TO CONFIRM IT.
`docs/handoff-2026-09-17-the-ink-is-fused.md` §3 states *"the morphological
opening yields 3 connected components with a median height of 811 px, in a
cell whose staff spacing is 100 px ... 8.1 staff spaces -- one blob holding
stems, beams and noteheads together"* and concludes **"THERE IS NO STEM
COMPONENT TO FIND"**. Its own §6 says that is **ONE DOCUMENT and ONE
SPOT-CHECKED CELL** -- *"it explains the direction of the result and does not
measure how often."*

Everything a within-blob reader is for rests on that claim, so it is measured
here as a DISTRIBUTION over every cell of both plates.

⚠️ THE CENSUS IS NOT THIS MEASUREMENT AND CANNOT BE. `rejection_census.py`
says a component fails a SHAPE test -- that a component is 3 spaces wide is
not evidence that it is a stem PLUS a notehead PLUS a beam. The direct test
of a merge is how many NOTEHEADS one component covers, which needs the
record's head boxes, and that is what this adds.

Three questions, in order of how much they would change the plan:

  Q1  how many components does a cell's opening yield, and how tall are they?
  Q2  what share of components cover MORE THAN ONE notehead -- a merge across
      notes, which no filter can undo;
  Q3  of the components the census blames (WIDE / TALL), what share cover at
      least one head, i.e. are a stem fused to its own head rather than
      unrelated furniture?

⚠️ FAITHFULNESS, per cell, before any number is read: the opening replicated
here must give `detect_stems` the identical ACCEPTED set. Any cell where it
does not is excluded and reported -- the control `rejection_census.py`
established, reused rather than restated.

⚠️ It reports the two publishers APART. The census's top cause INVERTS
between them, so a pooled blob distribution would average two populations
that are known to differ.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))] if v else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr import line_detection as ld
    from tools.omr.line_detection import (_binary_ink, _staff_line_spacing,
                                          STEM_KERNEL_MARGIN,
                                          STEM_MAX_HEIGHT_LINES)

    heads = collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") != "glyph_box":
            continue
        v = o.get("value")
        if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
            p = o["subject"].split("/")
            heads["cell/" + "/".join(p[1:5])].append(
                tuple(float(x) for x in v[1:]))

    pages = [int(x) for x in a.pages.split(",")]
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))

    per_cell_n, comp_h, comp_w, spacing_seen = [], [], [], []
    tally = collections.Counter()
    heads_per_comp = collections.Counter()
    blame = collections.Counter()
    cells = drift = 0
    for (pws, cs), pg in prepared:
        local = _system_local(pws.staves)
        for c in cs:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            src = (c.image_no_staff
                   if getattr(c, "image_no_staff", None) is not None
                   else c.image)
            if src is None or src.size == 0:
                continue
            sp = _staff_line_spacing(c)
            if sp <= 1.0:
                continue
            ink = _binary_ink(src)
            kh = max(3, int(round(sp * 2.0 * STEM_KERNEL_MARGIN)))
            opened = cv2.morphologyEx(
                ink, cv2.MORPH_OPEN,
                cv2.getStructuringElement(cv2.MORPH_RECT, (1, kh)))
            num, _, stats, _ = cv2.connectedComponentsWithStats(opened,
                                                                connectivity=8)
            # -- FAITHFULNESS: the accepted set must equal detect_stems' --
            min_h = int(round(sp * 2.0))
            max_h = int(round(sp * STEM_MAX_HEIGHT_LINES))
            max_w = max(3, int(round(sp * 0.6)))
            em = max(int(round(sp * 0.8)), 12)
            mine = []
            for i in range(1, num):
                x, y, w, h, ar = stats[i]
                if (min_h <= h <= max_h and w <= max_w
                        and x >= em and x + w <= c.width - em
                        and ar >= max(4, sp * 0.5) and h / max(1, w) >= 3.0):
                    mine.append((float(x), float(y), float(w), float(h)))
            real = sorted((float(d.x_canonical), float(d.y_canonical),
                           float(d.width_canonical), float(d.height_canonical))
                          for d in ld.detect_stems(c, drop_accidental_pairs=False))
            if sorted(mine) != real:
                drift += 1
                continue
            cells += 1
            spacing_seen.append(sp)
            hs = heads.get(ck, [])
            n_real = num - 1
            per_cell_n.append(n_real)
            for i in range(1, num):
                x, y, w, h, ar = stats[i]
                box = (float(x), float(y), float(w), float(h))
                comp_h.append(h / sp)
                comp_w.append(w / sp)
                nh = sum(1 for b in hs if overlaps(b, box))
                heads_per_comp[min(nh, 4)] += 1
                tall = h > max_h
                wide = w > max_w
                if nh >= 2:
                    tally["covers 2+ noteheads (a MERGE across notes)"] += 1
                elif nh == 1 and h >= min_h:
                    tally["covers 1 notehead, >= 2 spaces tall"] += 1
                elif nh == 1:
                    tally["covers 1 notehead, shorter than 2 spaces"] += 1
                else:
                    tally["covers NO notehead"] += 1
                if wide or tall:
                    k = ("WIDE" if wide and not tall else
                         "TALL" if tall and not wide else "WIDE+TALL")
                    blame[f"{k}, {min(nh,2)}{'+' if nh>=2 else ''} head(s)"] += 1

    print(f"{a.label}")
    print(f"cells measured: {cells}   EXCLUDED for drift: {drift}")
    if cells == 0:
        print("DEAD: no cell measured", file=sys.stderr)
        return 2
    if drift > cells * 0.02:
        print("DEAD: the replicated opening has drifted from detect_stems",
              file=sys.stderr)
        return 2

    print(f"\n== Q1 components per cell after the opening  (handoff sec.3 "
          f"spot-checked ONE cell at 3)")
    print(f"   n={len(per_cell_n)}  median {statistics.median(per_cell_n):.0f}"
          f"  mean {statistics.fmean(per_cell_n):.1f}"
          f"  p10 {pct(per_cell_n,0.10):.0f}  p90 {pct(per_cell_n,0.90):.0f}"
          f"  max {max(per_cell_n)}")
    print(f"   staff spacing seen: median {statistics.median(spacing_seen):.0f} px")
    print(f"\n== component HEIGHT in staff spaces  (handoff spot-check: median "
          f"8.1; the cap is {STEM_MAX_HEIGHT_LINES})")
    print(f"   n={len(comp_h)}  median {statistics.median(comp_h):.2f}"
          f"  p10 {pct(comp_h,0.10):.2f}  p90 {pct(comp_h,0.90):.2f}"
          f"  max {max(comp_h):.2f}")
    over = sum(1 for x in comp_h if x > STEM_MAX_HEIGHT_LINES)
    print(f"   over the {STEM_MAX_HEIGHT_LINES}-space cap: {over} "
          f"({over/len(comp_h):.1%})")
    print(f"\n== component WIDTH in staff spaces  (the cap is 0.6)")
    print(f"   median {statistics.median(comp_w):.2f}"
          f"  p90 {pct(comp_w,0.90):.2f}  max {max(comp_w):.2f}")
    wide = sum(1 for x in comp_w if x > 0.6)
    print(f"   over the 0.6-space cap: {wide} ({wide/len(comp_w):.1%})")

    print(f"\n== Q2 how many NOTEHEADS does one component cover?  "
          f"(2+ is a merge no filter can undo)")
    tot = sum(heads_per_comp.values())
    for k in sorted(heads_per_comp):
        lab = f"{k}+ heads" if k == 4 else f"{k} head(s)"
        print(f"   {lab:<12} {heads_per_comp[k]:>7} {heads_per_comp[k]/tot:>7.1%}")
    print(f"\n== what each component IS")
    for k, n in tally.most_common():
        print(f"   {k:<44} {n:>7} {n/tot:>7.1%}")
    print(f"\n== Q3 the components the census BLAMES, by how many heads they cover")
    for k, n in blame.most_common():
        print(f"   {k:<36} {n:>7}")

    out = {"label": a.label, "cells": cells, "drift": drift,
           "components": tot,
           "comps_per_cell": {"median": statistics.median(per_cell_n),
                              "mean": round(statistics.fmean(per_cell_n), 2),
                              "p90": pct(per_cell_n, 0.90),
                              "max": max(per_cell_n)},
           "height_spaces": {"median": round(statistics.median(comp_h), 3),
                             "p90": round(pct(comp_h, 0.90), 3),
                             "max": round(max(comp_h), 3),
                             "over_cap": over},
           "width_spaces": {"median": round(statistics.median(comp_w), 3),
                            "p90": round(pct(comp_w, 0.90), 3),
                            "over_cap": wide},
           "heads_per_component": {str(k): v
                                   for k, v in sorted(heads_per_comp.items())},
           "what_it_is": dict(tally), "blamed": dict(blame)}
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
