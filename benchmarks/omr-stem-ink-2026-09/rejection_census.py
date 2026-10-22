"""WHY IS EACH MISSING STEM REJECTED? The filter chain, instrumented.

`filter_sweep_arm.py` relaxed the four filters `detect_stems` exposes as
KEYWORDS and reached 287 of 793. `erasure_arm.py` then refuted the obvious
explanation for the other 506: reading the ORIGINAL raster instead of the
staff-line-erased one recovers FEWER (268 vs 287), so the erasure is not what
breaks them.

What that sweep could not reach is the THREE filters that are not parameters:

    if x < edge_margin or x + w > cell_w - edge_margin:   # 0.8 staff spaces
    if area < max(4, line_spacing * 0.5):
    if h / max(1, w) < 3.0:

This replicates the chain component by component and counts the FIRST test
each one fails, so every rejection has a named reason and the reasons sum.

⚠️ A REPLICATION IS ONLY EVIDENCE IF IT IS FAITHFUL, so the census runs the
real `detect_stems` on the same cell and asserts the accepted set is
IDENTICAL. Any cell where it is not is reported and excluded rather than
counted -- a re-implementation that has drifted would otherwise attribute
blame with total confidence.

⚠️ NOTE THE KERNEL DEPENDS ON `min_height_lines`, so relaxing that floor also
SHRINKS the opening kernel and changes which components exist at all. That is
why the sweep's stroke total FELL when the floor was lowered, and it is why
this census fixes the shipped kernel and varies nothing.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
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


def census(cell, ld):
    """Every component the opening produces, with the FIRST test it fails."""
    from tools.omr.line_detection import (_binary_ink, _staff_line_spacing,
                                          STEM_KERNEL_MARGIN)
    src = (cell.image_no_staff
           if getattr(cell, "image_no_staff", None) is not None else cell.image)
    if src is None or src.size == 0:
        return []
    line_spacing = _staff_line_spacing(cell)
    if line_spacing <= 1.0:
        return []
    cell_w = cell.width
    edge_margin = max(int(round(line_spacing * 0.8)), 12)
    ink = _binary_ink(src)
    kernel_h = max(3, int(round(line_spacing * 2.0 * STEM_KERNEL_MARGIN)))
    opened = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_h)))
    num, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    min_h = int(round(line_spacing * 2.0))
    max_h = int(round(line_spacing * ld.STEM_MAX_HEIGHT_LINES))
    max_w = max(3, int(round(line_spacing * 0.6)))
    rows = []
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if h < min_h:
            why = "too SHORT (h < 2.0 spaces)"
        elif h > max_h:
            why = "too TALL (h > 8.0 spaces)"
        elif w > max_w:
            why = "too WIDE (w > 0.6 spaces)"
        elif x < edge_margin or x + w > cell_w - edge_margin:
            why = "at a CELL EDGE (0.8 spaces)"
        elif area < max(4, line_spacing * 0.5):
            why = "too little AREA"
        elif h / max(1, w) < 3.0:
            why = "ASPECT < 3:1"
        else:
            why = "ACCEPTED (before the pair rule)"
        rows.append((why, (float(x), float(y), float(w), float(h))))
    return rows


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

    heads = {}
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") != "glyph_box":
            continue
        v = o.get("value")
        if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
            heads[o["subject"]] = tuple(float(x) for x in v[1:])
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}
    print(f"{a.label}: {len(missing)} heads abstain `no_stem`")

    pages = [int(x) for x in a.pages.split(",")]
    t0 = time.time()
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))
    print(f"re-cut in {time.time() - t0:.0f}s")

    per_cell: dict[str, list] = {}
    drift = 0
    for (pws, cells), pg in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            rows = census(c, ld)
            # ⚠️ FAITHFULNESS CONTROL, per cell.
            mine = sorted(b for why, b in rows
                          if why == "ACCEPTED (before the pair rule)")
            real = sorted((float(d.x_canonical), float(d.y_canonical),
                           float(d.width_canonical), float(d.height_canonical))
                          for d in ld.detect_stems(c, drop_accidental_pairs=False))
            if mine != real:
                drift += 1
                continue
            per_cell[ck] = rows
    print(f"cells censused: {len(per_cell)}   EXCLUDED for drift: {drift}")
    if drift > len(per_cell) * 0.02:
        print("DEAD: the replication has drifted from detect_stems",
              file=sys.stderr)
        return 2

    # for each missing head, the reason of the component that WOULD have
    # been its stem -- the nearest rejected one overlapping it
    tally = collections.Counter()
    for s in missing:
        p = s.split("/")
        ck = "cell/" + "/".join(p[1:5])
        rows = per_cell.get(ck)
        if rows is None:
            tally["cell not censused"] += 1
            continue
        hit = [why for why, b in rows if overlaps(heads[s], b)]
        if not hit:
            tally["NO component overlaps the head at all"] += 1
        elif any(w.startswith("ACCEPTED") for w in hit):
            tally["a component WAS accepted (pair rule dropped it)"] += 1
        else:
            tally[min(hit, key=lambda w: hit.count(w))] += 1

    print(f"\n== why each of the {len(missing)} heads has no stem")
    print(f"{'reason':<46} {'n':>6} {'share':>8}")
    out = {"label": a.label, "no_stem": len(missing), "reasons": {}}
    for why, n in tally.most_common():
        out["reasons"][why] = n
        print(f"{why:<46} {n:>6} {n/len(missing):>7.1%}")
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
