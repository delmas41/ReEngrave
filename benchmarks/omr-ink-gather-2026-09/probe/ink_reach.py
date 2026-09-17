"""`Q.INK`: reach, composition, alignment, and a null — in that order.

⚠️ REACH FIRST, AND THE ARM DECLARES ITSELF DEAD AT ZERO. Every sibling probe
in this repo does (`direction_arm.py`, `rest_dot_arm.py`, the wedge arm), and
`local_arm.sh` is the one that did not and reported a full table over a domain
of nothing. If the gatherer produces no row, exit non-zero and say so.

⚠️ IT DRIVES THE SHIPPED GATHERER. `gather_ink` is called with the flag on and
the rows are read back out of a real `Log` -- not re-derived here. A probe that
reproduces the rule instead of running it measures the probe.

⚠️ ALIGNMENT IS THE DELIVERABLE, NOT THE ROW COUNT. A count of blobs is worth
nothing; the claim `A-DUR-5` rests on is that unnamed ink LINES UP across
staves. The column analysis reuses `ONSET_COLUMN_TOLERANCE_SPACES` -- the
constant this repo already measured against a null for exactly the question
"are these two staves at the same x" -- rather than inventing a second notion
of the same thing.

⚠️⚠️ AND THE NULL IS THE DISCRIMINATOR, NOT A SANITY CHECK. Staff residue
aligns with the STAFF LINES: horizontal, at a line's own y, running the staff's
width. A printed mark aligns ACROSS STAVES at a column: vertical, at one x, on
several staves at once. Those are different geometries, so if columns of
unexplained ink survive a null that destroys only the cross-staff phase while
residue-shaped rows do not, the null is what separates them.

The null is a CIRCULAR SHIFT of each staff's own component x positions inside
its own cell span -- it keeps every within-staff interval and every shape
exactly as printed and destroys only the phase, the same null
`adjudicate_onset_column` was measured against. Beating a re-draw would only
show that music is not uniform noise.

Usage:
    python3 probe/ink_reach.py <pdf> <page> [--cell N] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("OMR_DIRECTION_TEXT", "0")   # not this arm's subject
os.environ["OMR_INK"] = "1"

from tools.omr.staged import gather as G                       # noqa: E402
from tools.omr.staged import record as R                       # noqa: E402
from tools.omr.staged.record import Log, Q                     # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (             # noqa: E402
    ONSET_COLUMN_TOLERANCE_SPACES)

WEIGHTS = str(ROOT / "omr-weights"
              / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")

#: Below this share of its box covered by non-span detections, a component's
#: classification is ABSENT. ⚠️ NOT A FILTER AND NOT A GATE -- every row is
#: reported either way; this is the probe's own reporting split, so that
#: "unnamed ink lines up" can be stated separately from "ink lines up".
UNNAMED_BELOW = 0.5


# ── the shape census: what KIND of thing is each row? ────────────────────────
#
# ⚠️ A COMPOSITION, NOT A FALSE-POSITIVE RATE. Sean, 2026-09-17: staff residue
# is not a false row, it is correctly gathered ink a later stage should NAME.
# So the population is described, never trimmed, and these buckets are the
# probe's own vocabulary -- nothing in `tools/` knows them.

def shape_of(row) -> str:
    d = row.detail
    w = d.get("width_spaces")
    h = d.get("height_spaces")
    if w is None or h is None:
        return "no_unit"
    if w < 0.25 and h < 0.25:
        return "speck"
    if h < 0.30 and w >= 2.0:
        return "line_residue"          # long, flat, a staff line's own shape
    if w < 0.50 and h >= 3.0:
        return "vertical"              # a barline, a stem, a bracket
    if w >= 4.0 and h >= 4.0:
        return "blob"                  # a merge: too big to be one mark
    return "mark_sized"


def load_rows(pdf: str, page: int):
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.yolo_detector import YoloDetector
    t0 = time.time()
    prepared = prepare_pages(pdf, [page], dpi=600)
    pws, cells = prepared[0]
    t1 = time.time()
    det = YoloDetector(WEIGHTS)
    log = Log()
    local = G.gather_geometry(log, pws)
    G.gather_systems(log, pws, getattr(pws, "used_bridging", True))
    G.gather_measures(log, pws, cells, local)
    detections = G.gather_detections(log, cells, local, detector=det)
    t2 = time.time()
    G.gather_ink(log, cells, local, detections)
    t3 = time.time()
    rows = [r for r in log.all_rows() if getattr(r, "quantity", None) == Q.INK]
    obs = [r for r in rows if getattr(r, "detail", None) and "ink_area_px" in r.detail]
    refusals = [r for r in rows if r not in obs]
    n_det = sum(len(v) for v in detections.values())
    return {
        "pws": pws, "cells": cells, "rows": obs, "refusals": refusals,
        "n_detections": n_det, "local": local,
        "t_prepare": t1 - t0, "t_detect": t2 - t1, "t_ink": t3 - t2,
    }


def spacing_of(rows) -> float:
    vals = [r.detail["cell_staff_space_px"] / (r.detail["width_spaces"] or 1)
            for r in rows[:1]]                      # unused; kept explicit
    return 0.0


def page_spacing(pws) -> float:
    """Staff-line spacing in PAGE pixels — the unit a cross-staff column is in.

    ⚠️ The MEDIAN across the system's staves: one warped staff must not set the
    unit for the rest. Same rule `_system_spacing` states for `Q.ONSET_COLUMN`.
    """
    vals = [float(s.line_spacing_px) for s in pws.staves
            if getattr(s, "line_spacing_px", None)]
    return statistics.median(vals) if vals else 0.0


def columns(points, tol_px):
    """Group (x, staff) points into columns, the way `adjudicate_onset_column`
    does: within the tolerance of the column's OWN centre.

    ⚠️ SINGLE-LINK CHAINING IS REFUSED, and that refusal is inherited rather
    than re-decided: a first cut of the onset work merged onsets 323 px apart
    on a dense bar by walking neighbour to neighbour.
    """
    cols = []
    for x, st in sorted(points):
        if cols and abs(x - (sum(p[0] for p in cols[-1]) / len(cols[-1]))) <= tol_px:
            cols[-1].append((x, st))
        else:
            cols.append([(x, st)])
    return cols


def column_table(rows, tol_px, *, only_unnamed=False, shifts=None):
    """Per cell: how many columns, and how many are witnessed by >= 2 staves.

    `shifts` maps a staff to a circular offset in px — the null.
    """
    # ⚠️⚠️ THE KEY IS (SYSTEM, CELL) AND KEYING ON THE CELL ALONE IS A REAL BUG
    # THAT WAS WRITTEN AND MEASURED HERE. A cell index RESTARTS at 0 on each
    # system, so on a page with two systems `cell 3` names two different bars
    # at two different page x, and pooling them puts unrelated ink in one
    # column span -- which destroys alignment BY CONSTRUCTION and reads as
    # "this publisher's ink does not line up". Litolff p.62 is one system and
    # could not expose it; Breitkopf Brahms 1 p.1 is TWENTY-SEVEN staves in
    # TWO systems and did, immediately. Same defect CLAUDE.md records for the
    # duration arm's bar figures.
    per_cell = {}
    for r in rows:
        d = r.detail
        if "x_center_page" not in d:
            continue
        if only_unnamed and d["ink_detector_coverage"] >= UNNAMED_BELOW:
            continue
        sub = r.subject
        per_cell.setdefault((sub.system, sub.cell), []).append(
            (d["x_center_page"], sub.staff, d.get("bbox_page_px")))

    out = []
    for cell, pts in sorted(per_cell.items()):
        xs = [p[0] for p in pts]
        lo, hi = min(xs), max(xs)
        span = max(1.0, hi - lo)
        moved = []
        for x, st, _b in pts:
            if shifts is not None:
                x = lo + ((x - lo) + shifts.get(st, 0.0)) % span
            moved.append((x, st))
        cols = columns(moved, tol_px)
        wit = [len({s for _x, s in c}) for c in cols]
        out.append({
            "system": cell[0], "cell": cell[1],
            "n_rows": len(pts),
            "n_staves": len({s for _x, s in moved}),
            "n_columns": len(cols),
            "n_corroborated": sum(1 for w in wit if w >= 2),
            "max_witnesses": max(wit) if wit else 0,
            "alone": sum(1 for w in wit if w == 1),
        })
    return out


def summarise(table):
    if not table:
        return {}
    return {
        "cells": len(table),
        "rows": sum(t["n_rows"] for t in table),
        "columns": sum(t["n_columns"] for t in table),
        "corroborated": sum(t["n_corroborated"] for t in table),
        "alone": sum(t["alone"] for t in table),
        "rows_per_column": round(
            sum(t["n_rows"] for t in table)
            / max(1, sum(t["n_columns"] for t in table)), 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, default=None,
                    help="report this cell staff by staff (the pre-registered "
                         "target)")
    ap.add_argument("--system", type=int, default=0,
                    help="which system the --cell belongs to; a cell index\n                         RESTARTS at 0 on each system")
    ap.add_argument("--null-seeds", type=int, default=5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    got = load_rows(a.pdf, a.page)
    rows, pws = got["rows"], got["pws"]

    # ── 1. REACH, and the arm is DEAD at zero ───────────────────────────────
    print(f"REACH  rows={len(rows)}  refusals={len(got['refusals'])}  "
          f"staves={len(pws.staves)}  cells={len(got['cells'])}  "
          f"detections={got['n_detections']}")
    print(f"COST   prepare {got['t_prepare']:.1f}s  detect {got['t_detect']:.1f}s"
          f"  ink {got['t_ink']:.2f}s")
    if not rows:
        print("DEAD: gather_ink produced no row. Nothing below is a measurement.")
        return 2

    # ── 2. COMPOSITION, never a filtered number ─────────────────────────────
    census = {}
    named = {}
    for r in rows:
        k = shape_of(r)
        census[k] = census.get(k, 0) + 1
        if r.detail["ink_detector_coverage"] >= UNNAMED_BELOW:
            named[k] = named.get(k, 0) + 1
    print("\nCOMPOSITION of the whole population (nothing removed):")
    for k in sorted(census, key=lambda k: -census[k]):
        n = census[k]
        cl = named.get(k, 0)
        print(f"  {k:14s} {n:6d}  ({100*n/len(rows):5.1f}%)   "
              f"classified {cl:5d}  unclassified {n-cl:5d}")
    n_named = sum(named.values())
    print(f"  {'TOTAL':14s} {len(rows):6d}            "
          f"classified {n_named:5d}  unclassified {len(rows)-n_named:5d}")

    # ── 3. ALIGNMENT, against a null ────────────────────────────────────────
    sp = page_spacing(pws)
    tol = sp * ONSET_COLUMN_TOLERANCE_SPACES
    print(f"\nALIGNMENT  staff spacing {sp:.1f} page px, tolerance "
          f"{ONSET_COLUMN_TOLERANCE_SPACES} spaces = {tol:.1f} px")

    result = {"reach": {"rows": len(rows), "refusals": len(got["refusals"]),
                        "staves": len(pws.staves), "cells": len(got["cells"]),
                        "detections": got["n_detections"]},
              "cost_s": {"prepare": round(got["t_prepare"], 2),
                         "detect": round(got["t_detect"], 2),
                         "ink": round(got["t_ink"], 3)},
              "composition": census, "classified": named,
              "tolerance_spaces": ONSET_COLUMN_TOLERANCE_SPACES,
              "staff_spacing_page_px": round(sp, 2),
              "arms": {}}

    def arm(label, subset, **kw):
        if len(subset) < 20:
            print(f"\n  {label}: {len(subset)} rows — TOO FEW, not scored")
            result["arms"][label] = {"rows": len(subset), "note": "too few"}
            return
        real = summarise(column_table(subset, tol, **kw))
        nulls = []
        for seed in range(a.null_seeds):
            rnd = random.Random(20260917 + seed)
            shifts = {s: rnd.uniform(0, 1e4) for s in range(len(pws.staves))}
            nulls.append(summarise(column_table(subset, tol, shifts=shifts, **kw)))
        nm = {k: statistics.mean(n[k] for n in nulls) for k in real}
        print(f"\n  {label}:")
        for k in ("rows", "columns", "corroborated", "alone"):
            r_, n_ = real[k], nm[k]
            ratio = (r_ / n_) if n_ else float("nan")
            print(f"    {k:14s} real {r_:7d}   null {n_:9.1f}   "
                  f"ratio {ratio:5.2f}")
        result["arms"][label] = {"real": real, "null_mean": nm,
                                 "null_seeds": a.null_seeds}

    arm("all ink", rows)
    arm("unclassified only", rows, only_unnamed=True)

    # ⚠️⚠️ THE SHAPE ARMS ARE SEAN'S OWN DISCRIMINATOR, TESTED RATHER THAN
    # ASSERTED. Staff residue aligns with the STAFF LINES -- horizontal, at a
    # line's own y, running the staff's width -- while a printed mark aligns
    # ACROSS STAVES at a column. Those are different geometries, so if the
    # layer is worth having, `vertical` and `mark_sized` rows should beat the
    # null and `line_residue` and `speck` rows should not. A bucket too small
    # to score says SO rather than producing a ratio nobody should read.
    print("\n  by SHAPE — does the geometry separate?")
    for shape in sorted(census, key=lambda k: -census[k]):
        arm(f"shape:{shape}", [r for r in rows if shape_of(r) == shape])

    # ── 4. THE PRE-REGISTERED TARGET ────────────────────────────────────────
    if a.cell is not None:
        print(f"\nTARGET cell {a.cell}, staff by staff:")
        per_staff = {}
        for r in rows:
            if r.subject.cell != a.cell or r.subject.system != a.system:
                continue
            per_staff.setdefault(r.subject.staff, []).append(r)
        tgt = []
        for st in sorted(per_staff):
            rs = sorted(per_staff[st],
                        key=lambda r: -r.detail["ink_area_px"])
            print(f"  staff {st:2d}  rows={len(rs):3d}")
            for r in rs[:4]:
                d = r.detail
                state = ("classified  " if d["ink_detector_coverage"]
                         >= UNNAMED_BELOW else "UNCLASSIFIED")
                print(f"      {state} x={d['ink_bbox_canonical'][0]/d['cell_staff_space_px']:5.2f}"
                      f" w={d['width_spaces']:5.2f} h={d['height_spaces']:5.2f} sp"
                      f"  cov={d['ink_detector_coverage']:.2f}"
                      f"  page_x={d.get('x_center_page', float('nan')):8.1f}"
                      f"  {','.join(d['ink_explained_by'][:2])}")
            tgt.append({"staff": st, "n_rows": len(rs),
                        "rows": [{k: r.detail.get(k) for k in
                                  ("width_spaces", "height_spaces",
                                   "ink_detector_coverage", "x_center_page",
                                   "ink_explained_by")} for r in rs[:6]]})
        result["target_cell"] = {"cell": a.cell, "staves": tgt}
        # ⚠️ The target is a COLUMN, so it is counted as one: how many staves
        # carry a row in the widest column of this cell, and how many of those
        # rows are unclassified. The x drifts down the page (the plate's own
        # warp), which is exactly why the count is taken in PAGE pixels under
        # the shipped tolerance and not by eye.
        pts = [(r.detail["x_center_page"], r.subject.staff, r)
               for r in rows if r.subject.cell == a.cell
               and r.subject.system == a.system
               and "x_center_page" in r.detail]
        cols = columns([(x, s) for x, s, _r in pts], tol)
        best = max(cols, key=lambda c: len({s for _x, s in c})) if cols else []
        st_in = {s for _x, s in best}
        unnamed = sum(
            1 for x, s, r in pts
            if (x, s) in {(px, ps) for px, ps in best}
            and r.detail["ink_detector_coverage"] < UNNAMED_BELOW)
        print(f"\n  widest column in cell {a.cell}: {len(st_in)} of "
              f"{len(per_staff)} staves, {unnamed} of {len(best)} rows "
              f"unclassified")
        result["target_cell"]["widest_column"] = {
            "staves": len(st_in), "of": len(per_staff),
            "rows": len(best), "unclassified": unnamed,
            "x_page": round(sum(x for x, _s in best) / max(1, len(best)), 1)}

        # ⚠️⚠️ A TOLERANCE SWEEP, REPORTED AND NOT ACTED ON. The shipped
        # `ONSET_COLUMN_TOLERANCE_SPACES` was measured for note onsets on a
        # Breitkopf page and is used here unchanged, because inventing a
        # second notion of "same x" is exactly what this probe must not do.
        # What the sweep SHOWS is that a printed column does not stay within
        # it across seventeen staves of THIS plate: the page's own warp moves
        # one printed column by most of a staff space top to bottom. That is a
        # fact about the plate, it is why the count is taken in page pixels,
        # and MOVING THE CONSTANT ON IT WOULD BE FITTING TO ONE PAGE.
        sweep = []
        for t in (0.05, 0.10, 0.25, 0.50, 1.00):
            cs = columns([(x, s) for x, s, _r in pts], sp * t)
            b = max(cs, key=lambda c: len({s for _x, s in c})) if cs else []
            sweep.append({"tolerance_spaces": t,
                          "widest_column_staves": len({s for _x, s in b}),
                          "n_columns": len(cs)})
            print(f"    tolerance {t:4.2f} sp ({sp*t:5.1f} px): widest column "
                  f"{sweep[-1]['widest_column_staves']:2d} of "
                  f"{len(per_staff)} staves, {len(cs):3d} columns in the cell")
        result["target_cell"]["tolerance_sweep"] = sweep

    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(result, indent=1))
        print("\nwrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
