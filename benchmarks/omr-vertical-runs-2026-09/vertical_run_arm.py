"""THE ARM: does the vertical-run population make Sean's barline test ASKABLE?

Three questions, and the first two could not be asked at all before
`Q.VERTICAL_RUN` existed:

  1  ⚠️ THE FAITHFULNESS CONTROL, FIRST AND BEFORE ANY DELTA IS READ.
     `line_detection.py` is on the path every stem arm in this repo proves
     faithful before reporting a number, and the shared records' own stroke
     counts are the bar: **1,920 = 1,920** on Litolff and **2,305 = 2,305** on
     Breitkopf. This re-cuts the same pages and asserts the flag-OFF stroke set
     reproduces the record's, cell by cell. A mismatch ABORTS -- a candidate
     population measured off a tree whose survivors have moved would attribute
     with total confidence.

  2  SEAN'S BARLINE TEST: *a barline's two ends sit ON the outer staff lines; a
     stem's do not.* Computable for the first time, because the rows now carry
     the run's endpoints in PAGE PIXELS and `Q.STAFF_LINES` is page pixels.
     Scored against the population the crop pass adjudicated **12 of 12 as
     NOT-A-NOTEHEAD, every one a box 0.40-0.45 spaces wide on a vertical rule**
     -- i.e. the print-settled barlines -- with the ACCEPTED runs as the
     control population.
     ⚠️ A NEGATIVE IS A FIRST-CLASS RESULT. If the test does not separate them
     the arm says so; §7 of the breakthrough document is the precedent, where a
     prediction failed its own falsification test the day it was written.

  3  THE LENGTH ASYMMETRY as a DISTRIBUTION, split by what the record says each
     run coincides with -- §9 of `docs/proposal-2026-09-18-boxing-is-a-
     decision.md`: length is a POSITIVE identifier for every vertical mark
     whose length is enumerable and NO identifier at all for a stem.

  4  THE COST, plainly: rows per page and MB per page. `Q.INK` alone is
     0.6 MB/page (Litolff) and 3.1 MB/page (Breitkopf) against records already
     in the hundreds of MB, and record size WAS the standing argument against
     ink-first gathering. If this is expensive the arm says so; that is a real
     argument against the default ever flipping.

⚠️ REACH BEFORE ACCURACY, and the arm EXITS NON-ZERO DECLARING ITSELF DEAD at
zero reach. A clean believable zero is the failure mode of every probe on this
thread.

⚠️ NO OMR-NED FIGURE, deliberately: the metric is symmetric, pays for emitting
fewer symbols, and this change emits nothing at all.

⚠️ THIS IS A GATHER CHANGE. `readjudicate.py` and `reexport_arm.py` rebuild
from a saved record and are STRUCTURALLY BLIND to it; pricing its effect on a
FILE needs two full re-gathers, which this arm does not take and does not
claim.

⚠️ PUBLISHERS ARE REPORTED APART, NEVER POOLED. Litolff MERGES and Breitkopf
SHATTERS; a pooled figure over the two is a figure about the mix.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def overlaps(a, b) -> bool:
    """Both boxes as CORNERS `(x0, y0, x1, y1)`. ⚠️ Spelled out because three
    box conventions disagree in one record and reading one as another gives a
    negative width and a clean believable zero."""
    return (min(a[2], b[2]) - max(a[0], b[0]) > 0
            and min(a[3], b[3]) - max(a[1], b[1]) > 0)


def pct(vals, p):
    """The shipped percentile spelling -- `v[int(f*len(v))]`, never numpy, so
    the figures are comparable with every other arm on this thread."""
    if not vals:
        return None
    v = sorted(vals)
    return v[min(len(v) - 1, int(p * len(v)))]


# ─────────────────────────────────────────────────────────────────────────────
# SEAN'S RULE
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️⚠️ CONVENTION ASSUMED: Sean's own, 2026-09-18 -- *"Bar lines are the length
# of a staff or they extend to other systems"*, so a barline's two ends sit ON
# the outer staff lines while a stem runs from a notehead to a beam and stops
# wherever the music needs it to.
#
# ⚠️ THE TOLERANCE IS SWEPT AND REPORTED AS A CURVE, NOT SET. A single value
# would be a threshold fitted to whichever population was looked at first, and
# the plate's own warp is the reason a value cannot be read off the print: this
# repo measures a barline's x drifting 40 page px top to bottom, and the staff
# lines themselves are traced to 8-17 px of tilt. So the arm prints the whole
# sweep and the finding is the SHAPE.
TOLERANCES = (0.15, 0.25, 0.40, 0.60, 1.00)


def ends_on_its_own_staff(y_top, y_bot, lines, spacing, tol_spaces):
    """THE NARROW FORM: both ends on the run's OWN staff's outer lines."""
    if not lines or not spacing:
        return None
    tol = tol_spaces * spacing
    return (abs(y_top - min(lines)) <= tol
            and abs(y_bot - max(lines)) <= tol)


def ends_on_any_staff(y_top, y_bot, page_lines, spacing, tol_spaces):
    """⚠️⚠️ THE WIDE FORM, AND SEAN'S RULE HAS BOTH HALVES IN IT: *"Bar lines
    are the length of a staff OR THEY EXTEND TO OTHER SYSTEMS."* So the top end
    sits on SOME staff's top line and the bottom on SOME staff's bottom line,
    which for a single-staff barline is the narrow form and for a systemic one
    is two different staves.

    ⚠️ IT EXISTS BECAUSE THE NARROW FORM CAME BACK A CLEAN ZERO ON THE
    PRINT-SETTLED POPULATION, and the reason was arithmetic rather than a
    refutation: a barline spanning ONE staff is 4.0 staff spaces, which is
    INSIDE the accepted window (min 2.0, max 8.0) and at the median of the stem
    distribution (3.93) -- §9's own observation. So a run in the `too TALL`
    bucket, which is the bucket the crop pass settled as barlines, is by
    definition MORE than 8 spaces: it crosses staves, and its ends are nowhere
    near ONE staff's outer lines. Testing only the own staff is a narrow
    operationalisation of a rule whose own wording is wider, and Sean's
    instruction on S4 governs: *"don't give up -- adjust the rules to be
    broader."* Both forms are reported; neither replaces the other."""
    if not page_lines or not spacing:
        return None
    tol = tol_spaces * spacing
    tops = [min(v) for v in page_lines]
    bots = [max(v) for v in page_lines]
    return (any(abs(y_top - t) <= tol for t in tops)
            and any(abs(y_bot - b) <= tol for b in bots))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="comma list, 0-based")
    ap.add_argument("--record", required=True,
                    help="the SHARED record: the faithfulness control")
    ap.add_argument("--crop-rows", default=None,
                    help="omr-stem-crop-pass rows json (the print join)")
    ap.add_argument("--crop-manifest", default=None)
    ap.add_argument("--crop-adjudication", default=None)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--break-faithfulness", action="store_true",
                    help="POSITIVE CONTROL: corrupt the control so it FAILS, "
                         "proving it can. A control that has never been seen "
                         "to fail is not a control.")
    a = ap.parse_args()
    pages = [int(x) for x in a.pages.split(",")]

    from tools.omr.staged import gather as G
    from tools.omr.staged.gather import _system_local
    from tools.omr.staged.record import Log, Q
    from tools.omr import line_detection as LD
    from tools.omr.staged.pipeline import prepare_pages

    out: dict = {"label": a.label, "pages": pages, "pdf": a.pdf,
                 "record": a.record}

    # ── the record's own strokes, per cell, BEFORE anything is re-cut ────────
    rec_strokes: dict[str, list] = collections.defaultdict(list)
    lines_of: dict[str, list] = {}
    spacing_of: dict[str, float] = {}
    glyphs: dict[str, list] = collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "stem":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 4:
                p = o["subject"].split("/")
                # ⚠️ RESTRICTED TO THE PAGES RE-CUT, and the first run of this
                # arm is why the line exists: the record holds 1,920 strokes
                # over FOUR pages and a one-page re-cut yields 190, so the
                # control refused with `190 = 1920? NO` -- correctly, and for
                # the wrong reason. A control that refuses for the wrong reason
                # is indistinguishable from one that refuses for the right one.
                if int(p[1]) in pages:
                    rec_strokes["cell/" + "/".join(p[1:5])].append(
                        tuple(float(x) for x in v))
        elif q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "staff_spacing":
            try:
                spacing_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "glyph_box":
            v = o.get("value")
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(v, list) and len(v) == 5 and bp:
                p = o["subject"].split("/")
                glyphs["cell/" + "/".join(p[1:5])].append(
                    (str(v[0]), [float(x) for x in bp]))
    n_rec = sum(len(v) for v in rec_strokes.values())
    print(f"{a.label}: the record holds {n_rec} stem rows over "
          f"{len(rec_strokes)} cells of pages {pages}", flush=True)
    out["record_stem_rows"] = n_rec

    # ── re-cut, and run the SHIPPED rung both ways ──────────────────────────
    t0 = time.time()
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=a.dpi), pages))
    print(f"re-cut {len(pages)} page(s) in {time.time() - t0:.0f}s", flush=True)

    mine_off: dict[str, list] = {}
    mine_on: dict[str, list] = {}
    runs: list[dict] = []
    cells_seen = 0
    old = os.environ.get(G.VERTICAL_RUNS_ENV)
    try:
        for (pws, cells), pg in prepared:
            local = _system_local(pws.staves)
            keyed = [c for c in cells if local.get(c.staff_index) is not None]
            cells_seen += len(keyed)
            for arm, store in (("0", mine_off), ("1", mine_on)):
                os.environ[G.VERTICAL_RUNS_ENV] = arm
                log = Log()
                G.gather_cv_lines(log, keyed, local)
                for row in log.all_rows():
                    if getattr(row, "quantity", None) != Q.STEM:
                        continue
                    v = getattr(row, "value", None)
                    if v is None:
                        continue
                    p = row.subject.to_key().split("/")
                    store.setdefault("cell/" + "/".join(p[1:5]), []).append(
                        tuple(float(x) for x in v))
                if arm == "1":
                    for row in log.all_rows():
                        if getattr(row, "quantity", None) != Q.VERTICAL_RUN:
                            continue
                        if getattr(row, "value", None) is None:
                            continue
                        d = row.detail
                        key = row.subject.to_key().split("/")
                        runs.append({
                            "page": int(key[1]),
                            "subject": row.subject.to_key(),
                            "cell": "cell/" + "/".join(key[1:5]),
                            "staff": "staff/" + "/".join(key[1:4]),
                            "outcome": d["run_outcome"],
                            "accepted": d["run_accepted"],
                            "by_dimension": d["run_refused_by_dimension"],
                            "h_spaces": d.get("run_height_spaces"),
                            "w_spaces": d.get("run_width_spaces"),
                            "page_box": d.get("run_bbox_page_px"),
                            "y_top": d.get("run_y_top_page"),
                            "y_bot": d.get("run_y_bottom_page"),
                            "fill": d["run_ink_fill"],
                        })
    finally:
        if old is None:
            os.environ.pop(G.VERTICAL_RUNS_ENV, None)
        else:
            os.environ[G.VERTICAL_RUNS_ENV] = old

    # ── 1. REACH, FIRST ─────────────────────────────────────────────────────
    n_off = sum(len(v) for v in mine_off.values())
    n_on = sum(len(v) for v in mine_on.values())
    out["cells"] = cells_seen
    out["reach"] = {"candidates": len(runs), "strokes_flag_off": n_off,
                    "strokes_flag_on": n_on}
    print(f"REACH: {len(runs)} vertical-run candidates over {cells_seen} cells",
          flush=True)
    if not runs:
        print("DEAD: zero candidates -- nothing to measure", file=sys.stderr)
        json.dump(out, open(a.json, "w"), indent=1)
        return 2

    # ── 2. THE FAITHFULNESS CONTROL ─────────────────────────────────────────
    if a.break_faithfulness:
        # ⚠️ THE POSITIVE CONTROL, AND IT ANNOUNCES ITSELF. Drop one stroke so
        # the comparison MUST fail; a control never seen to fail is not one.
        for k in sorted(mine_off):
            if mine_off[k]:
                mine_off[k] = mine_off[k][1:]
                print(f"  [--break-faithfulness] dropped a stroke from {k}",
                      flush=True)
                break
    drift = [k for k in set(rec_strokes) | set(mine_off)
             if sorted(rec_strokes.get(k, ())) != sorted(mine_off.get(k, ()))]
    out["faithfulness"] = {
        "record_strokes": n_rec, "recut_flag_off": n_off,
        "cells_disagreeing": len(drift),
        "identical": (n_rec == n_off and not drift),
    }
    print(f"FAITHFULNESS flag-OFF: {n_off} = {n_rec}? "
          f"{'YES' if n_rec == n_off else 'NO'}; "
          f"cells disagreeing: {len(drift)}", flush=True)
    if drift or n_rec != n_off:
        print("ABORT: the re-cut does not reproduce the record's strokes. "
              "Every number below would attribute against a moved baseline.",
              file=sys.stderr)
        out["aborted"] = "faithfulness"
        json.dump(out, open(a.json, "w"), indent=1)
        return 3
    # and flag-ON must leave them alone too
    on_drift = [k for k in set(mine_on) | set(mine_off)
                if sorted(mine_on.get(k, ())) != sorted(mine_off.get(k, ()))]
    out["faithfulness"]["flag_on_moves_strokes"] = len(on_drift)
    print(f"FAITHFULNESS flag-ON:  {n_on} strokes, cells moved: {len(on_drift)}",
          flush=True)
    if on_drift or n_on != n_off:
        print("ABORT: the FLAG moved a stroke. It is required not to.",
              file=sys.stderr)
        out["aborted"] = "flag_on_moved_strokes"
        json.dump(out, open(a.json, "w"), indent=1)
        return 4

    # ── 3. THE OUTCOME CENSUS ───────────────────────────────────────────────
    census = collections.Counter(r["outcome"] for r in runs)
    out["outcomes"] = dict(census)
    print("\n== the candidate population, by fate")
    for why, n in census.most_common():
        print(f"  {why:<48} {n:>6}  {n / len(runs):>6.1%}")
    n_dim = sum(1 for r in runs if r["by_dimension"])
    out["refused_by_dimension"] = n_dim
    print(f"  {'-> refused by a DIMENSION bound':<48} {n_dim:>6}  "
          f"{n_dim / len(runs):>6.1%}")

    # ── 4. SEAN'S BARLINE TEST ──────────────────────────────────────────────
    # every staff's line set, per page -- the WIDE form needs the page, not
    # the run's own staff
    page_lines: dict[int, list] = collections.defaultdict(list)
    for key, v in lines_of.items():
        page_lines[int(key.split("/")[1])].append(v)
    scored = 0
    for r in runs:
        lines = lines_of.get(r["staff"])
        sp = spacing_of.get(r["staff"])
        if r["y_top"] is None or not lines or not sp:
            r["ends"] = r["ends_any"] = None
            continue
        scored += 1
        r["ends"] = {t: ends_on_its_own_staff(r["y_top"], r["y_bot"],
                                              lines, sp, t)
                     for t in TOLERANCES}
        r["ends_any"] = {t: ends_on_any_staff(r["y_top"], r["y_bot"],
                                              page_lines[r["page"]], sp, t)
                         for t in TOLERANCES}
        # ⚠️⚠️ THE SIGNED OFFSETS, SO A ZERO RATE CAN BE DIAGNOSED RATHER
        # THAN MERELY REPORTED. A predicate that never fires says only "not
        # within tolerance"; these say BY HOW MUCH and IN WHICH DIRECTION, and
        # a systematic offset in one direction is a different finding from a
        # scatter. Positive = the run's end is BELOW the line.
        r["d_top"] = (r["y_top"] - min(lines)) / sp
        r["d_bot"] = (r["y_bot"] - max(lines)) / sp
        # how many staves the run's own span covers, as context on both
        r["staves_spanned"] = sum(
            1 for v in page_lines[r["page"]]
            if min(v) >= r["y_top"] - sp and max(v) <= r["y_bot"] + sp)
    out["barline_test"] = {"scorable": scored, "of": len(runs),
                           "tolerances": list(TOLERANCES)}
    print(f"\n== Sean's barline test: {scored} of {len(runs)} runs carry BOTH "
          f"a page box and their staff's lines")
    if not scored:
        print("DEAD: no run can be scored -- the page frame or the staff "
              "lines are missing", file=sys.stderr)
        json.dump(out, open(a.json, "w"), indent=1)
        return 2

    by_outcome: dict = {}
    for form, field in (("OWN staff (narrow)", "ends"),
                        ("ANY staff (Sean's wide form)", "ends_any")):
        print(f"\n  -- both ends on the outer lines of the {form}")
        print(f"  {'outcome':<44} {'n':>5} " +
              " ".join(f"{t:>6}" for t in TOLERANCES))
        for why in [k for k, _ in census.most_common()]:
            grp = [r for r in runs if r["outcome"] == why and r[field]]
            if not grp:
                continue
            rates = {t: sum(1 for r in grp if r[field][t]) / len(grp)
                     for t in TOLERANCES}
            by_outcome.setdefault(field, {})[why] = {
                "n": len(grp), "fires": rates}
            print(f"  {why:<44} {len(grp):>5} " +
                  " ".join(f"{rates[t]:>6.1%}" for t in TOLERANCES))
    out["barline_test"]["by_outcome"] = by_outcome
    spanned = collections.Counter(r.get("staves_spanned")
                                  for r in runs if r["ends"])
    out["barline_test"]["staves_spanned"] = {str(k): v
                                             for k, v in spanned.items()}
    print("\n  -- WHY a rate is what it is: the signed end offsets, in staff "
          "spaces\n     (+ = the run's end is BELOW the line; 0 = exactly on "
          "it)")
    print(f"  {'outcome':<44} {'n':>5} {'d_top p05':>10} {'med':>7} "
          f"{'p95':>7} | {'d_bot p05':>10} {'med':>7} {'p95':>7}")
    offsets: dict = {}
    for why in [k for k, _ in census.most_common()]:
        grp = [r for r in runs if r["outcome"] == why and r.get("d_top")
               is not None]
        if not grp:
            continue
        dt = [r["d_top"] for r in grp]
        db = [r["d_bot"] for r in grp]
        offsets[why] = {
            "n": len(grp),
            "d_top": [round(pct(dt, 0.05), 2), round(statistics.median(dt), 2),
                      round(pct(dt, 0.95), 2)],
            "d_bot": [round(pct(db, 0.05), 2), round(statistics.median(db), 2),
                      round(pct(db, 0.95), 2)]}
        o = offsets[why]
        print(f"  {why:<44} {len(grp):>5} {o['d_top'][0]:>10.2f} "
              f"{o['d_top'][1]:>7.2f} {o['d_top'][2]:>7.2f} | "
              f"{o['d_bot'][0]:>10.2f} {o['d_bot'][1]:>7.2f} "
              f"{o['d_bot'][2]:>7.2f}")
    out["barline_test"]["end_offsets"] = offsets
    print("\n  staves a run's span fully covers: " +
          ", ".join(f"{k}:{v}" for k, v in sorted(spanned.items(),
                                                  key=lambda kv: kv[0])))

    # ── 5. THE PRINT JOIN: the 12 the crop pass settled ─────────────────────
    if a.crop_rows and a.crop_manifest and a.crop_adjudication:
        rows = json.load(open(a.crop_rows))["rows"]
        tiles = json.load(open(a.crop_manifest))["tiles"]
        verd = {r["id"]: r["verdict"]
                for r in json.load(open(a.crop_adjudication))["rows"]}
        box_of = {r["subject"]: r for r in rows}
        # ⚠️ THE PRINT-SETTLED POPULATION: the `too TALL` bucket's sample, 12
        # of 12 adjudicated `not_a_notehead`, every one "a box 0.40-0.45
        # spaces wide on a vertical rule" -- barlines, read off the plate.
        want = [t for t in tiles
                if t.get("bucket", "").startswith("too TALL")
                and verd.get(t["id"]) == "not_a_notehead"]
        # ⚠️ AND THE CONTROL IS ALSO FROM THE PRINT, not from the pipeline: the
        # same pass's heads the eye saw a STEM on. A control drawn from the
        # accepted runs would be scoring the filter against itself.
        ctrl = [t for t in tiles
                if verd.get(t["id"], "").startswith("stem_printed")]
        print(f"\n== the PRINT join: {len(want)} adjudicated barlines, "
              f"{len(ctrl)} adjudicated stems")

        def runs_under(tile):
            r = box_of.get(tile["subject"])
            if not r or not r.get("bbox_page_px"):
                return None, None
            box = r["bbox_page_px"]
            cell = "cell/" + "/".join(tile["subject"].split("/")[1:5])
            hit = [x for x in runs
                   if x["cell"] == cell and x["page_box"]
                   and overlaps(box, x["page_box"])]
            return hit, r

        join = {"barlines": [], "stems": []}
        for name, pop in (("barlines", want), ("stems", ctrl)):
            for tile in pop:
                hit, r = runs_under(tile)
                if hit is None:
                    continue
                rec = {"id": tile["id"], "subject": tile["subject"],
                       "n_runs": len(hit)}
                if hit:
                    tall = max(hit, key=lambda x: x["h_spaces"] or 0.0)
                    rec.update(h_spaces=tall["h_spaces"],
                               w_spaces=tall["w_spaces"],
                               outcome=tall["outcome"],
                               staves_spanned=tall.get("staves_spanned"),
                               ends={str(t): (tall["ends"] or {}).get(t)
                                     for t in TOLERANCES},
                               ends_any={str(t): (tall["ends_any"] or {}).get(t)
                                         for t in TOLERANCES})
                join[name].append(rec)
        out["print_join"] = join
        for field, form in (("ends", "OWN staff"), ("ends_any", "ANY staff")):
            print(f"  -- {form}")
            print(f"  {'population':<12} {'joined':>7} {'with a run':>11} " +
                  " ".join(f"{t:>6}" for t in TOLERANCES))
            for name in ("barlines", "stems"):
                g = [r for r in join[name] if r["n_runs"]]
                if not join[name]:
                    continue
                rates = [f"{sum(1 for r in g if r[field].get(str(t))):>6}"
                         for t in TOLERANCES]
                print(f"  {name:<12} {len(join[name]):>7} {len(g):>11} " +
                      " ".join(rates))
        if not [r for r in join["barlines"] if r["n_runs"]]:
            print("  ⚠️ DEAD on this half: no adjudicated barline joins a run "
                  "-- the join, not the test, is what failed", file=sys.stderr)

    # ── 6. THE LENGTH DISTRIBUTION, by what the run coincides with ──────────
    #
    # ⚠️ §9's claim: length is a POSITIVE identifier for every vertical mark
    # whose length is enumerable and NO identifier at all for a stem. This is
    # the distribution that claim predicts, split by the detector's own class
    # over the run's box -- which is COVERAGE and NOT an assertion of identity
    # (`CLAIM.COVERAGE`), so the buckets are named "coincides with", never "is".
    KINDS = (("accidental", "accidental"), ("clef", "clef"),
             ("notehead", "notehead"), ("barline", "barline"),
             ("rest", "rest"), ("timeSig", "meter"), ("key", "keysig"))
    buckets: dict[str, list] = collections.defaultdict(list)
    for r in runs:
        if r["h_spaces"] is None or not r["page_box"]:
            continue
        names = [n for (n, b) in glyphs.get(r["cell"], ())
                 if overlaps(b, r["page_box"])]
        hit = set()
        for n in names:
            for pre, label in KINDS:
                if n.lower().startswith(pre.lower()):
                    hit.add(label)
        if not hit:
            buckets["(no detection over it)"].append(r["h_spaces"])
        elif len(hit) == 1:
            buckets[hit.pop()].append(r["h_spaces"])
        else:
            buckets["(several kinds)"].append(r["h_spaces"])
    out["height_by_coincidence"] = {}
    print("\n== height in STAFF SPACES, by what the detector put over the run")
    print(f"  {'coincides with':<24} {'n':>6} {'p05':>7} {'median':>7} "
          f"{'p95':>7}")
    for k in sorted(buckets, key=lambda k: -len(buckets[k])):
        v = buckets[k]
        row = {"n": len(v), "p05": pct(v, 0.05),
               "median": round(statistics.median(v), 2), "p95": pct(v, 0.95)}
        out["height_by_coincidence"][k] = row
        print(f"  {k:<24} {row['n']:>6} {row['p05']:>7.2f} "
              f"{row['median']:>7.2f} {row['p95']:>7.2f}")

    # ── 7. THE COST ─────────────────────────────────────────────────────────
    #
    # ⚠️ MEASURED BY SERIALISING THE ROWS, not estimated from a field count.
    on_log = Log()
    # rebuild one page's rows to size them honestly -- the same shape
    # `log.to_json()` writes into a record.
    sized = json.dumps([
        {"id": "obs:000000", "subject": r["subject"],
         "quantity": "vertical_run", "value": [0, 0, 0, 0],
         "reader": "cv_lines", "frame": "cell:0", "score": None,
         "detail": {"run_outcome": r["outcome"], "run_accepted": r["accepted"],
                    "run_refused_by_dimension": r["by_dimension"],
                    "run_ink_area_px": 0, "run_ink_fill": r["fill"],
                    "run_n_candidates": 0, "image": "no_staff",
                    "staff_lines_erased": True,
                    "run_width_spaces": r["w_spaces"],
                    "run_height_spaces": r["h_spaces"],
                    "run_staff_space_px": 100.0,
                    "run_bbox_page_px": r["page_box"],
                    "run_y_top_page": r["y_top"],
                    "run_y_bottom_page": r["y_bot"],
                    "run_x_center_page": 0.0},
         "basis": []}
        for r in runs])
    per_row = len(sized) / max(1, len(runs))
    out["cost"] = {
        "rows": len(runs), "pages": len(pages),
        "rows_per_page": round(len(runs) / len(pages), 1),
        "bytes_per_row": round(per_row, 1),
        "mb_per_page": round(len(sized) / len(pages) / 1e6, 3),
    }
    print(f"\n== COST: {len(runs)} rows over {len(pages)} page(s) = "
          f"{out['cost']['rows_per_page']} rows/page at "
          f"{out['cost']['bytes_per_row']} bytes = "
          f"{out['cost']['mb_per_page']} MB/page")
    del on_log

    json.dump(out, open(a.json, "w"), indent=1)
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
