#!/usr/bin/env python3
"""THE ARM: with the CELL removed, is Sean's barline test still a negative?

The predecessor lane (`benchmarks/omr-vertical-runs-2026-09`) made his test
computable and got a clean negative — **19 of 19 print-settled barlines fire at
NO tolerance while 6 of 58 adjudicated stems do** — and then diagnosed it: the
runs are measured inside a MEASURE CELL, whose reach is the staff plus 4 + 4
staff spaces, so a barline TALLER than that has its ends clipped BY the crop.
Median end offsets of **−4.00 / +4.00 spaces on both publishers**; ten of
nineteen barlines reading `h = 12.00` exactly. **The test was UNAVAILABLE.**

This arm re-asks it with the cell taken out of the path
(`tools/omr/vertical_runs_page.py`, the whole page, no filters), against the
SAME print-adjudicated population, at the SAME tolerance sweep, with the SAME
two forms of the rule. Nothing else moves, so a change in the answer is
attributable to the window and to nothing else.

⚠️ WHAT WOULD FALSIFY THE REPAIR rather than the rule: if the end offsets STILL
pile at ±4.00 spaces, the page reader is not reading the page. That is checked
BEFORE the test is reported (§3), and the arm says so rather than printing a
result it cannot stand behind.

⚠️ THE ARM IS DEAD AT ZERO REACH and exits non-zero saying so — a reader that
found nothing and a page that prints nothing are the same table otherwise.

    python3 benchmarks/omr-vertical-runs-page-2026-09/page_run_arm.py \
      --pdf library/editions/.../imslp984073.pdf --pages 1,2,3,4 \
      --crop-rows   benchmarks/omr-stem-crop-pass-2026-09/out/litolff-rows.json \
      --crop-manifest benchmarks/omr-stem-crop-pass-2026-09/out/crop-manifest-litolff.json \
      --crop-adjudication benchmarks/omr-stem-crop-pass-2026-09/ADJUDICATION-litolff.json \
      --label "Litolff Beethoven 5 pp.1-4" --json out/litolff.json

No weights. It needs `library/` and ~30 s per four pages.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ⚠️ THE TOLERANCE IS SWEPT AND REPORTED AS A CURVE, NOT SET — inherited
# verbatim from the predecessor arm, because changing the sweep and the window
# in one step would make the two results incomparable, which is the only thing
# this arm is for.
TOLERANCES = (0.15, 0.25, 0.40, 0.60, 1.00)


def overlaps(a, b) -> bool:
    """Two `[x0, y0, x1, y1]` page boxes share any area."""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    return round(s[min(len(s) - 1, int(p * len(s)))], 3)


def ends_on_its_own_staff(y_top, y_bot, lines, spacing, tol_spaces):
    """THE NARROW FORM: both ends on the run's OWN staff's outer lines."""
    if not lines or not spacing:
        return None
    tol = tol_spaces * spacing
    return (abs(y_top - min(lines)) <= tol
            and abs(y_bot - max(lines)) <= tol)


def ends_on_any_staff(y_top, y_bot, page_lines, spacing, tol_spaces):
    """THE WIDE FORM — *"or they extend to other systems"*: the top end on SOME
    staff's top line and the bottom on SOME staff's bottom line."""
    if not page_lines or not spacing:
        return None
    tol = tol_spaces * spacing
    return (any(abs(y_top - min(v)) <= tol for v in page_lines)
            and any(abs(y_bot - max(v)) <= tol for v in page_lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="comma list, 0-based")
    ap.add_argument("--crop-rows", default=None)
    ap.add_argument("--crop-manifest", default=None)
    ap.add_argument("--crop-adjudication", default=None)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--blind-the-reader", action="store_true",
                    help="POSITIVE CONTROL ON THE CONTROLS: hand the reader a "
                         "blank page, so every table below must go to zero and "
                         "the arm must declare itself DEAD. A control that has "
                         "never been seen to fail is not a control.")
    a = ap.parse_args()
    pages = [int(x) for x in a.pages.split(",")]

    import numpy as np
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.vertical_runs_page import (read_page_vertical_runs,
                                              page_staff_spacing)
    from tools.omr import line_detection as LD

    out: dict = {"label": a.label, "pages": pages, "pdf": a.pdf,
                 "blinded": bool(a.blind_the_reader)}

    t0 = time.time()
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=a.dpi), pages))
    print(f"{a.label}: re-cut {len(pages)} page(s) in {time.time() - t0:.0f}s",
          flush=True)

    runs: list[dict] = []
    cell_stems: list[dict] = []
    lines_by_page: dict[int, list] = {}
    spacing_by_page: dict[int, float] = {}

    for (pws, cells), pg in prepared:
        page_lines = []
        for s in pws.staves:
            ys = sorted(float(y) for y in (getattr(s, "line_ys", None) or ()))
            if ys:
                page_lines.append(ys)
        lines_by_page[pg] = page_lines
        sp = page_staff_spacing(pws.staves)
        spacing_by_page[pg] = sp
        if sp <= 1.0:
            print(f"  page {pg}: NO staff-space unit -- skipped, not defaulted",
                  file=sys.stderr)
            continue

        img = pws.page
        if a.blind_the_reader:
            # ⚠️ A blank render of the same shape and dtype: the reader is
            # handed a real page object whose ink is gone, so the failure this
            # proves is the READER's silence and not an exception.
            class _Blank:
                rgb = np.full_like(pws.page.rgb, 255)
            img = _Blank()

        t1 = time.time()
        found = read_page_vertical_runs(img, pws.staves, spacing=sp)
        print(f"  page {pg}: {len(found)} page runs "
              f"({time.time() - t1:.1f}s, spacing {sp:.1f}px, "
              f"{len(page_lines)} staves)", flush=True)
        for r in found:
            lines = (page_lines[r.staff_index]
                     if r.staff_index is not None
                     and r.staff_index < len(page_lines) else None)
            runs.append({
                "page": pg, "staff": r.staff_index,
                "page_box": [r.x, r.y, r.x + r.w, r.y + r.h],
                "y_top": r.y_top, "y_bot": r.y_bottom,
                "x_center": r.x_center,
                "h_spaces": r.height_spaces, "w_spaces": r.width_spaces,
                "staves_spanned": r.staves_spanned,
                "fill": round(r.area / float(max(1, r.w * r.h)), 4),
                # ⚠️ Offsets in SIGNED staff spaces, `+` = below the line —
                # the predecessor's convention, so the ±4.00 signature is
                # directly comparable rather than merely similar.
                "d_top": (round((r.y_top - min(lines)) / sp, 2)
                          if lines else None),
                "d_bot": (round((r.y_bottom - max(lines)) / sp, 2)
                          if lines else None),
                "ends": {t: ends_on_its_own_staff(r.y_top, r.y_bottom,
                                                  lines, sp, t)
                         for t in TOLERANCES},
                "ends_any": {t: ends_on_any_staff(r.y_top, r.y_bottom,
                                                  page_lines, sp, t)
                             for t in TOLERANCES},
            })

        # ── the cross-reader control: the CELL path on the same pages ───────
        # ⚠️ NOT a faithfulness control and it must not be read as one. The two
        # readers see different windows BY DESIGN, so their counts SHOULD
        # differ; what this catches is the page reader being blind — if it
        # misses the ink the cell path accepted, nothing below means anything.
        for c in cells:
            for d in LD.detect_stems(c):
                up = getattr(c, "upscale_factor", None)
                box = getattr(c, "bbox_page_px", None)
                if not up or not box or len(box) != 4:
                    continue
                cell_stems.append({
                    "page": pg,
                    "page_box": [box[0] + d.x_canonical / up,
                                 box[1] + d.y_canonical / up,
                                 box[0] + (d.x_canonical + d.width_canonical) / up,
                                 box[1] + (d.y_canonical + d.height_canonical) / up]})

    out["reach"] = {"page_runs": len(runs), "cell_stems": len(cell_stems),
                    "pages": len(prepared)}
    print(f"\n== REACH: {len(runs)} page runs, {len(cell_stems)} cell-path "
          f"stems over {len(prepared)} page(s)")
    if not runs:
        print("⚠️ DEAD: the page reader produced NO run. Every table below "
              "would be a property of that silence, not of the page.",
              file=sys.stderr)
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        json.dump(out, open(a.json, "w"), indent=1)
        return 2

    # ── 2. THE CROSS-READER CONTROL ─────────────────────────────────────────
    by_page: dict[int, list] = collections.defaultdict(list)
    for r in runs:
        by_page[r["page"]].append(r)
    covered = sum(1 for s in cell_stems
                  if any(overlaps(s["page_box"], r["page_box"])
                         for r in by_page[s["page"]]))
    rate = covered / len(cell_stems) if cell_stems else 0.0
    out["cross_reader"] = {"cell_stems": len(cell_stems),
                           "found_by_page_reader": covered, "rate": rate}
    print(f"== cross-reader control: {covered} of {len(cell_stems)} cell-path "
          f"stems have a page run over them ({rate:.1%})")
    if cell_stems and rate < 0.5:
        print("  ⚠️ the page reader is missing most of what the cell path "
              "accepted -- read nothing below as a result about barlines",
              file=sys.stderr)

    # ── 3. THE DECISIVE CONTROL: has the CELL's signature gone? ─────────────
    #
    # ⚠️ THIS IS THE ONE THAT DECIDES WHETHER THE REST IS READABLE. The
    # predecessor's `too TALL` bucket read d_top −4.00 / d_bot +4.00 on BOTH
    # publishers, to two decimals, because those are the cell's own pads. If
    # the same numbers come back here the window did not actually change.
    tall = [r for r in runs
            if r["h_spaces"] and r["h_spaces"] > 8.0
            and r["d_top"] is not None]
    sig = {}
    if tall:
        sig = {"n": len(tall),
               "d_top_median": round(statistics.median(
                   r["d_top"] for r in tall), 2),
               "d_bot_median": round(statistics.median(
                   r["d_bot"] for r in tall), 2),
               "at_exactly_pm4": sum(1 for r in tall
                                     if abs(r["d_top"] + 4.0) < 0.05
                                     and abs(r["d_bot"] - 4.0) < 0.05)}
    out["cell_signature"] = sig
    print(f"\n== the CELL signature on runs over 8 spaces (n={len(tall)}): "
          f"d_top median {sig.get('d_top_median')}, "
          f"d_bot median {sig.get('d_bot_median')}, "
          f"{sig.get('at_exactly_pm4')} still at exactly ±4.00")
    if tall and sig["at_exactly_pm4"] / len(tall) > 0.25:
        print("  ⚠️⚠️ THE CROP SIGNATURE SURVIVED: this is not reading the "
              "page. The test below is still unavailable.", file=sys.stderr)

    # ── 4. heights, and how many staves a run spans ─────────────────────────
    hs = [r["h_spaces"] for r in runs if r["h_spaces"]]
    out["heights"] = {"p05": pct(hs, 0.05), "median": pct(hs, 0.5),
                      "p95": pct(hs, 0.95), "max": round(max(hs), 2)}
    spans = collections.Counter(r["staves_spanned"] for r in runs)
    out["staves_spanned"] = {str(k): v for k, v in sorted(spans.items())}
    print(f"== height (spaces) p05/median/p95/max: {out['heights']['p05']} / "
          f"{out['heights']['median']} / {out['heights']['p95']} / "
          f"{out['heights']['max']}")
    print(f"== staves spanned: "
          + ", ".join(f"{k}:{v}" for k, v in sorted(spans.items())[:8]))

    # ── 5. SEAN'S TEST over the whole population ────────────────────────────
    fires = {f: {t: sum(1 for r in runs if r[f][t]) for t in TOLERANCES}
             for f in ("ends", "ends_any")}
    out["barline_test_population"] = {
        f: {str(t): v for t, v in d.items()} for f, d in fires.items()}
    print(f"\n== Sean's test over all {len(runs)} runs")
    print(f"  {'form':<10} " + " ".join(f"{t:>6}" for t in TOLERANCES))
    for f, name in (("ends", "own"), ("ends_any", "any")):
        print(f"  {name:<10} "
              + " ".join(f"{fires[f][t]:>6}" for t in TOLERANCES))

    # ── 6. THE PRINT JOIN — the same adjudicated population as before ───────
    if a.crop_rows and a.crop_manifest and a.crop_adjudication:
        rows = json.load(open(a.crop_rows))["rows"]
        tiles = json.load(open(a.crop_manifest))["tiles"]
        verd = {r["id"]: r["verdict"]
                for r in json.load(open(a.crop_adjudication))["rows"]}
        box_of = {r["subject"]: r for r in rows}
        want = [t for t in tiles
                if t.get("bucket", "").startswith("too TALL")
                and verd.get(t["id"]) == "not_a_notehead"]
        ctrl = [t for t in tiles
                if verd.get(t["id"], "").startswith("stem_printed")]
        print(f"\n== the PRINT join: {len(want)} adjudicated barlines, "
              f"{len(ctrl)} adjudicated stems")

        join: dict = {"barlines": [], "stems": []}
        for name, pop in (("barlines", want), ("stems", ctrl)):
            for tile in pop:
                r = box_of.get(tile["subject"])
                if not r or not r.get("bbox_page_px"):
                    continue
                box = r["bbox_page_px"]
                pg = int(tile["subject"].split("/")[1])
                hit = [x for x in by_page.get(pg, [])
                       if overlaps(box, x["page_box"])]
                rec = {"id": tile["id"], "subject": tile["subject"],
                       "n_runs": len(hit)}
                if hit:
                    # ⚠️ THE TALLEST run over the tile, matching the
                    # predecessor's choice: a crop tile is a small box and
                    # several runs can cross it, and the mark the eye settled
                    # is the long one.
                    tallest = max(hit, key=lambda x: x["h_spaces"] or 0.0)
                    rec.update(h_spaces=tallest["h_spaces"],
                               w_spaces=tallest["w_spaces"],
                               staves_spanned=tallest["staves_spanned"],
                               d_top=tallest["d_top"], d_bot=tallest["d_bot"],
                               ends={str(t): tallest["ends"][t]
                                     for t in TOLERANCES},
                               ends_any={str(t): tallest["ends_any"][t]
                                         for t in TOLERANCES})
                join[name].append(rec)
        out["print_join"] = join

        for field, form in (("ends", "OWN staff"), ("ends_any", "ANY staff")):
            print(f"  -- {form}")
            print(f"  {'population':<12} {'joined':>7} {'with a run':>11} "
                  + " ".join(f"{t:>6}" for t in TOLERANCES))
            for name in ("barlines", "stems"):
                if not join[name]:
                    continue
                g = [r for r in join[name] if r["n_runs"]]
                cells_ = [f"{sum(1 for r in g if r[field].get(str(t))):>6}"
                          for t in TOLERANCES]
                print(f"  {name:<12} {len(join[name]):>7} {len(g):>11} "
                      + " ".join(cells_))
        if not [r for r in join["barlines"] if r["n_runs"]]:
            print("  ⚠️ DEAD on this half: no adjudicated barline joins a run "
                  "-- the join, not the test, is what failed", file=sys.stderr)

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.json, "w"), indent=1)
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
