"""SECTION 5's FALSIFICATION TEST, ASKED DIRECTLY.

`docs/handoff-2026-09-17-the-ink-is-fused.md` §5:

    if the stem's ink inside a fused component cannot be separated from the
    notehead's by a column profile, a within-blob reader is not available and
    the answer is upstream (binarisation, or the detector).

So this asks exactly that, of the components `rejection_census.py` blames,
and of NOTHING else. It builds no reader and recovers no head; it reports
whether the separation EXISTS. A clean negative here retires the whole §4b
plan and is the most valuable thing this probe can return.

THE TEST. Inside one rejected component's own mask, `stroke_columns` reads
the per-column longest ink run and bands adjacent columns only where they
AGREE about where that run starts and ends. A stem's columns agree (it is one
stroke a hairline wide); a notehead's do not, and neither do a beam's. If a
band survives `detect_stems`' own height, width, area and aspect filters and
covers the head, the stem's ink was separable inside the blob.

⚠️⚠️ THE POSITIVE CONTROL IS THE LOAD-BEARING PART, because this probe's
failure mode is a believable zero. The identical profile is run over the
components `detect_stems` ACCEPTED -- strokes it already calls stems -- and
must find a band in essentially all of them. If it does not, the profile is
not a stem reader and no number below it means anything, so the probe exits
non-zero rather than print a rate.

⚠️ FAITHFULNESS, per cell: the replicated opening must give `detect_stems`
the identical accepted set, or the cell is excluded and reported. Reused from
`rejection_census.py` rather than restated.

⚠️ THE TOLERANCE IS SWEPT, NOT SET. `AGREE_SPACES` is the one number this
thread does not already own, so every arm below is reported at five values
and the FINDINGS says whether it sits on a plateau or an empty interval.
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402
from stroke_columns import read_strokes  # noqa: E402

SWEEP = (0.10, 0.15, 0.25, 0.40, 0.60)


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def inside(band, comp) -> bool:
    """Does this band lie in that component's box?"""
    bx, by, bw, bh = band
    cx, cy, cw, ch = comp
    return (bx + bw / 2 >= cx and bx + bw / 2 <= cx + cw
            and by + bh / 2 >= cy and by + bh / 2 <= cy + ch)


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

    heads, klass = {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "glyph_box":
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
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))

    # per cell, per agree value: the bands found inside REJECTED components,
    # plus the control counts over ACCEPTED ones.
    rej_bands: dict[float, dict[str, list]] = {g: {} for g in SWEEP}
    rej_noedge: dict[float, dict[str, list]] = {g: {} for g in SWEEP}
    ctrl = {g: collections.Counter() for g in SWEEP}
    rej_by_reason = {g: collections.Counter() for g in SWEEP}
    rej_total = collections.Counter()
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
            num, labels, stats, _ = cv2.connectedComponentsWithStats(
                opened, connectivity=8)
            min_h = int(round(sp * 2.0))
            max_h = int(round(sp * STEM_MAX_HEIGHT_LINES))
            max_w = max(3, int(round(sp * 0.6)))
            em = max(int(round(sp * 0.8)), 12)

            accepted, rejected = [], []
            for i in range(1, num):
                x, y, w, h, ar = stats[i]
                ok = (min_h <= h <= max_h and w <= max_w
                      and x >= em and x + w <= c.width - em
                      and ar >= max(4, sp * 0.5) and h / max(1, w) >= 3.0)
                (accepted if ok else rejected).append(i)
            mine = sorted((float(stats[i][0]), float(stats[i][1]),
                           float(stats[i][2]), float(stats[i][3]))
                          for i in accepted)
            real = sorted((float(d.x_canonical), float(d.y_canonical),
                           float(d.width_canonical), float(d.height_canonical))
                          for d in ld.detect_stems(c, drop_accidental_pairs=False))
            if mine != real:
                drift += 1
                continue
            cells += 1

            for g in SWEEP:
                # WARNING: THE SHIPPED READER, ON THE WHOLE CELL, ONCE. The
                # first version of this probe ran its OWN copy of the profile
                # over each component submask; that copy carried two defects
                # the shipped code's unit tests later found, and running it
                # per component also left the edge filter with no cell to
                # measure against. Both go away by asking the question of the
                # reader that SHIPS: a band lying INSIDE a rejected component
                # is the stroke that component's shape hid.
                bands = [(float(b.x_canonical), float(b.y_canonical),
                          float(b.width_canonical), float(b.height_canonical))
                         for b in read_strokes(ink, sp, c.width,
                                               agree_spaces=g)]
                got, got_noedge = [], list(bands)
                for i in rejected:
                    x, y, w, h, ar = stats[i]
                    bb = [b for b in bands if inside(b, (x, y, w, h))]
                    got.extend(bb)
                    reason = ("too SHORT" if h < min_h else
                              "too TALL" if h > max_h else
                              "too WIDE" if w > max_w else
                              "at a CELL EDGE" if (x < em or x + w > c.width - em)
                              else "AREA/ASPECT")
                    if g == SWEEP[0]:
                        rej_total[reason] += 1
                    rej_by_reason[g][f"{reason} -> band" if bb
                                     else f"{reason} -> none"] += 1
                rej_bands[g][ck] = got
                rej_noedge[g][ck] = got_noedge
                # POSITIVE CONTROL: does it re-find the ACCEPTED components?
                for i in accepted:
                    x, y, w, h, ar = stats[i]
                    hit = any(overlaps((x, y, w, h), b) for b in bands)
                    ctrl[g]["reproduced" if hit else "LOST"] += 1

    print(f"cells measured: {cells}   EXCLUDED for drift: {drift}")
    if cells == 0:
        print("DEAD: no cell measured", file=sys.stderr)
        return 2
    if drift > cells * 0.02:
        print("DEAD: the replicated opening has drifted from detect_stems",
              file=sys.stderr)
        return 2

    out = {"label": a.label, "cells": cells, "drift": drift,
           "no_stem": len(missing),
           "rejected_components": dict(rej_total), "sweep": {}}

    print(f"\n== POSITIVE CONTROL: does the column profile re-find the strokes "
          f"`detect_stems` ALREADY accepts?")
    print(f"{'agree (spaces)':>15} {'reproduced':>11} {'LOST':>7} {'rate':>8}")
    for g in SWEEP:
        r, l = ctrl[g]["reproduced"], ctrl[g]["LOST"]
        print(f"{g:>15.2f} {r:>11} {l:>7} {r/max(1,r+l):>7.1%}")
    best = max(SWEEP, key=lambda g: ctrl[g]["reproduced"]
               / max(1, ctrl[g]["reproduced"] + ctrl[g]["LOST"]))
    rate = (ctrl[best]["reproduced"]
            / max(1, ctrl[best]["reproduced"] + ctrl[best]["LOST"]))
    if rate < 0.95:
        print(f"\nDEAD: the column profile cannot re-find the stems we already "
              f"read (best {rate:.1%} at agree={best}). It is not a stem "
              f"reader, so nothing below it is evidence.", file=sys.stderr)
        Path(a.json).write_text(json.dumps(out, indent=1))
        return 2

    print(f"\n== SECTION 5: inside a REJECTED component, is a stroke separable?")
    print(f"{'agree':>7} {'bands':>7} {'heads a band covers':>21} "
          f"{'share':>7}   {'(no edge filter)':>18}")
    for g in SWEEP:
        def covers(store):
            return sum(1 for s in missing
                       if any(overlaps(heads[s], b[:4])
                              for b in store[g].get(
                                  "cell/" + "/".join(s.split("/")[1:5]), [])))
        spoke = covers(rej_bands)
        loose = covers(rej_noedge)
        nb = sum(len(v) for v in rej_bands[g].values())
        out["sweep"][str(g)] = {
            "control": dict(ctrl[g]), "bands": nb,
            "heads_a_band_covers": spoke,
            "heads_a_band_covers_no_edge_filter": loose,
            "share_of_no_stem": round(spoke / max(1, len(missing)), 4),
            "by_reason": dict(rej_by_reason[g])}
        print(f"{g:>7.2f} {nb:>7} {spoke:>21} "
              f"{spoke/max(1,len(missing)):>6.1%}   {loose:>18}")

    print(f"\n== which REJECTION does a separable stroke live inside? "
          f"(agree=0.25)")
    g = 0.25
    keys = sorted({k.split(" -> ")[0] for k in rej_by_reason[g]})
    print(f"{'rejected as':<20} {'components':>11} {'a band inside':>14} {'rate':>8}")
    for k in keys:
        y = rej_by_reason[g].get(f"{k} -> band", 0)
        n = y + rej_by_reason[g].get(f"{k} -> none", 0)
        print(f"{k:<20} {n:>11} {y:>14} {y/max(1,n):>7.1%}")

    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
