"""REACH, AND THEN THE CUTS — `OMR_WHOLE_REST_INK` on a SECOND PUBLISHER.

The rule deletes pitched notes. Its six constants are the p05/p95 of ONE
document's own 395 correctly-detected `restWhole` glyphs (Beethoven 5 / Litolff
`984073`, a low-res bitonal 1870 plate), and two of the six sit on a plateau one
step wide or less. This asks the only question that can be asked of that from
the outside: **does the band a second publisher's OWN whole rests occupy agree
with the band that shipped?**

It answers three things, in this order, and REFUSES to report any of them if the
one before it is empty:

  1. POSITIVE CONTROL — does this record hold the two populations at all
     (noteheads with a page box; `restWhole` with a page box)?
  2. THE BAND — this document's own p05/p95 of height and aspect, computed by
     the identical percentile rule the shipped cuts were read off, so the two
     numbers are comparable rather than merely both being percentiles.
  3. THE FIRES — every notehead the SHIPPED rule would delete, and separately
     every one a rule rebuilt on THIS document's own band would delete.

⚠️ THE CONSTANTS ARE IMPORTED, NEVER RESTATED. A second copy of a number this
project paid to measure is how two copies drift; the shipped values arrive from
`tools.omr.staged.adjudicators.rhythm` and the geometry from its own
`_staff_step`, so this probe cannot silently disagree with the decision it is
about.

⚠️ THIS IS NOT AN ACCURACY MEASUREMENT AND CANNOT BE ONE. A band agreeing says
the cuts transfer as a DESCRIPTION of whole rests; only crops say whether the
glyphs it fires on are whole rests. `--crops-for` writes the fire list for
`whole_rest_crops.py`.

    python3 whole_rest_reach.py --cache cache.json --json out/reach.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators import rhythm as R  # noqa: E402


def _k(subject: str, n: int):
    """The first `n` integer coordinates of a subject key."""
    return tuple(int(x) for x in subject.split("/")[1:1 + n])


def _pct(values, f):
    """The percentile rule the SHIPPED cuts were read off, reproduced exactly.

    ⚠️ Not `numpy.percentile`. The shipped 0.46/0.84/1.63/3.09 came from
    `v[min(len(v)-1, int(f*len(v)))]` on a sorted list, and a different
    interpolation would make this document's numbers incomparable with them for
    a reason that has nothing to do with the documents.
    """
    return values[min(len(values) - 1, int(f * len(values)))]


def load(cache_path):
    c = json.load(open(cache_path))
    box, cls, rest, conf, lines, spacing = {}, {}, {}, {}, {}, {}
    for o in c["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                box[s] = pb
        elif q == "notehead_class":
            cls[s] = o["value"]
        elif q == "rest":
            rest[s] = o["value"]
        elif q == "glyph_conf":
            conf[s] = o.get("score")
        elif q == "staff_lines":
            lines[_k(s, 3)] = o["value"]
        elif q == "staff_spacing":
            spacing[_k(s, 3)] = o["value"]
    return c, box, cls, rest, conf, lines, spacing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--label", default="this document")
    ap.add_argument("--json")
    ap.add_argument("--crops-for", help="write the SHIPPED rule's fires here")
    ap.add_argument("--near-miss-for",
                    help="write the near-miss non-fires here")
    a = ap.parse_args()

    c, box, cls, rest, conf, lines, spacing = load(a.cache)

    def geom(sub):
        """(height in staff spaces, aspect, staff step) — the decision's own."""
        pb, k = box.get(sub), _k(sub, 3)
        ly, sp = lines.get(k), spacing.get(k)
        if not pb or not ly or not sp:
            return None
        step = R._staff_step(pb, ly, sp)
        if step is None:
            return None
        h = (pb[3] - pb[1]) / sp
        w = (pb[2] - pb[0]) / sp
        if h <= 0:
            return None
        return h, w / h, step

    heads = [s for s in cls if s in box]
    wr = [s for s in rest if s in box
          and str(rest[s]).lower().startswith("restwhole")]

    print(f"=== 1. POSITIVE CONTROL — {a.label} ===")
    print(f"  provenance                    {c.get('provenance')}")
    print(f"  noteheads with a page box     {len(heads)}")
    print(f"  restWhole  with a page box    {len(wr)}")
    if not heads or not wr:
        print("DEAD INSTRUMENT: a population this probe is about is EMPTY, so "
              "every number below would be a zero that means nothing.",
              file=sys.stderr)
        return 2

    rg = [g for s in wr if (g := geom(s))]
    if not rg:
        print("DEAD INSTRUMENT: no `restWhole` has usable staff geometry.",
              file=sys.stderr)
        return 2
    hs = sorted(g[0] for g in rg)
    asps = sorted(g[1] for g in rg)
    steps = sorted(g[2] for g in rg)
    band = {"n": len(rg),
            "height_p05": _pct(hs, .05), "height_p95": _pct(hs, .95),
            "aspect_p05": _pct(asps, .05), "aspect_p95": _pct(asps, .95),
            "step_p05": _pct(steps, .05), "step_p95": _pct(steps, .95),
            "height_median": _pct(hs, .50), "aspect_median": _pct(asps, .50)}

    head_g = [g for s in heads if (g := geom(s))]
    hh = sorted(g[0] for g in head_g)
    ha = sorted(g[1] for g in head_g)

    print()
    print(f"=== 2. THE BAND — {a.label}'s OWN {len(rg)} whole rests ===")
    print(f"  {'':<22} {'SHIPPED (Litolff)':>18} {'THIS DOCUMENT':>16}"
          f" {'delta':>9}")
    for name, shipped, mine in (
            ("max height (spaces)", R.WHOLE_REST_INK_MAX_HEIGHT_SPACES,
             band["height_p95"]),
            ("min aspect", R.WHOLE_REST_INK_MIN_ASPECT, band["aspect_p05"]),
            ("max aspect", R.WHOLE_REST_INK_MAX_ASPECT, band["aspect_p95"]),
    ):
        print(f"  {name:<22} {shipped:>18.3f} {mine:>16.3f} "
              f"{mine - shipped:>+9.3f}")
    print(f"  {'(p05 height)':<22} {'0.460':>18} {band['height_p05']:>16.3f}")
    print(f"  {'whole-rest step':<22} {R.WHOLE_REST_STEP:>18.3f} "
          f"{_pct(steps, .50):>16.3f}  (median of this doc's own)")
    print(f"  {'   its p05 / p95':<22} {'':>18} "
          f"{band['step_p05']:.2f} / {band['step_p95']:.2f}")
    print(f"  noteheads here: height median {_pct(hh, .50):.3f}, "
          f"aspect median {_pct(ha, .50):.3f}")

    # ── 3. the fires ────────────────────────────────────────────────────────
    # NEIGHBOUR index: per staff, this document's whole rests by cell and step.
    by_staff = collections.defaultdict(list)
    for s in wr:
        g = geom(s)
        if g:
            by_staff[_k(s, 3)].append((int(s.split("/")[4]), g[2]))

    def neighbour(sub, step):
        cell = int(sub.split("/")[4])
        for c2, step2 in by_staff.get(_k(sub, 3), ()):
            if (abs(c2 - cell) <= R.WHOLE_REST_NEIGHBOUR_BARS
                    and abs(step2 - step) <= R.WHOLE_REST_NEIGHBOUR_STEPS):
                return {"cell": c2, "staff_step": round(step2, 3)}
        return None

    per_cell_heads = collections.Counter(_k(s, 5) for s in heads)
    per_cell_rest = collections.Counter(_k(s, 5) for s in rest if s in box)

    def shaped(h, asp, *, mine):
        """SHIPPED uses the decision's own predicate; MINE rebuilds the same
        SHAPE test on this document's own percentiles, so the only thing that
        differs between the two columns is the numbers."""
        if not mine:
            return R._rest_shaped(h, asp)
        return (h <= band["height_p95"]
                and band["aspect_p05"] <= asp <= band["aspect_p95"])

    rows = []
    for s in heads:
        g = geom(s)
        if not g:
            continue
        h, asp, step = g
        at_slot = abs(step - R.WHOLE_REST_STEP) <= R.WHOLE_REST_STEP_TOLERANCE
        nb = None if at_slot else neighbour(s, step)
        rows.append({
            "subject": s, "height": round(h, 3), "aspect": round(asp, 3),
            "step": round(step, 3), "conf": conf.get(s), "cls": cls[s],
            "shape_shipped": shaped(h, asp, mine=False),
            "shape_mine": shaped(h, asp, mine=True),
            "slot": at_slot, "neighbour": nb,
            "position": bool(at_slot or nb),
            "alone_in_bar": (per_cell_heads[_k(s, 5)] == 1
                             and per_cell_rest[_k(s, 5)] == 0),
        })

    def fires(key):
        return [r for r in rows if r[key] and r["position"]]

    f_shipped, f_mine = fires("shape_shipped"), fires("shape_mine")
    shape_only = [r for r in rows if r["shape_shipped"]]
    pos_only = [r for r in rows if r["position"]]

    print()
    print(f"=== 3. THE FIRES over {len(rows)} noteheads with geometry ===")
    print(f"  SHAPE alone (shipped cuts)                 {len(shape_only)}")
    print(f"  POSITION alone (slot or neighbouring bar)  {len(pos_only)}")
    print(f"  SHIPPED RULE  = shape+position             {len(f_shipped)}"
          f"   <-- these are the notes it DELETES")
    print(f"  rebuilt on THIS document's own band        {len(f_mine)}")
    both = {r["subject"] for r in f_shipped} & {r["subject"] for r in f_mine}
    print(f"  in both                                     {len(both)}"
          f"   (shipped-only {len(f_shipped) - len(both)}, "
          f"mine-only {len(f_mine) - len(both)})")
    w = collections.Counter("slot" if r["slot"] else "neighbouring_bar"
                            for r in f_shipped)
    print(f"  witness split (shipped)                    {dict(w)}")

    if f_shipped:
        print()
        print("  every SHIPPED fire:")
        for i, r in enumerate(sorted(f_shipped, key=lambda r: r["subject"])):
            print(f"   {i:>3}  {r['subject']:<26} h={r['height']:5.2f} "
                  f"asp={r['aspect']:6.2f} step={r['step']:+6.2f} "
                  f"conf={(r['conf'] or 0):.2f} cls={r['cls']:<24} "
                  f"alone={int(r['alone_in_bar'])} nb={r['neighbour']}")
    else:
        print()
        print("  ⚠️ THE SHIPPED RULE FIRES ON NOTHING HERE. That is a REAL and "
              "REPORTABLE answer about this document — but it is not a clean "
              "bill of health for the rule, and the two populations above are "
              "what say the instrument was alive when it produced this zero.")

    if a.crops_for:
        json.dump([_crop_row(r) for r in
                   sorted(f_shipped, key=lambda r: r["subject"])],
                  open(a.crops_for, "w"), indent=1)
        print(f"\n  wrote {len(f_shipped)} fires -> {a.crops_for}")

    if a.near_miss_for:
        near = _near_misses(rows, band)
        json.dump([_crop_row(r) for r in near], open(a.near_miss_for, "w"),
                  indent=1)
        print(f"  wrote {len(near)} NEAR MISSES -> {a.near_miss_for}")

    if a.json:
        json.dump({"provenance": c.get("provenance"), "label": a.label,
                   "band": band,
                   "shipped": {"max_height":
                               R.WHOLE_REST_INK_MAX_HEIGHT_SPACES,
                               "min_aspect": R.WHOLE_REST_INK_MIN_ASPECT,
                               "max_aspect": R.WHOLE_REST_INK_MAX_ASPECT,
                               "step": R.WHOLE_REST_STEP,
                               "step_tol": R.WHOLE_REST_STEP_TOLERANCE,
                               "nb_bars": R.WHOLE_REST_NEIGHBOUR_BARS,
                               "nb_steps": R.WHOLE_REST_NEIGHBOUR_STEPS},
                   "counts": {"noteheads": len(heads), "restWhole": len(wr),
                              "rows": len(rows),
                              "shape_only": len(shape_only),
                              "position_only": len(pos_only),
                              "fires_shipped": len(f_shipped),
                              "fires_own_band": len(f_mine),
                              "in_both": len(both)},
                   "fires_shipped": f_shipped, "fires_own_band": f_mine,
                   "rows": rows}, open(a.json, "w"), indent=1)
        print(f"  wrote reach -> {a.json}")
    return 0


def _crop_row(r):
    """A `whole_rest_crops.py` row — page/system/staff/cell from the key."""
    p, s, st, cl, g = (int(x) for x in r["subject"].split("/")[1:])
    extra = ({"near_miss_because": r["near_miss_because"]}
             if "near_miss_because" in r else {})
    return {**extra, "subject": r["subject"],
            "where": {"page": p, "system": s, "staff": st, "cell": cl,
                      "glyph": g},
            "part": f"p{p}s{s}st{st}", "measure": cl,
            "height_spaces": r["height"], "aspect": r["aspect"],
            "staff_step": r["step"], "conf": r["conf"], "cls": r["cls"],
            "witness": ("slot" if r["slot"]
                        else ("neighbouring_bar" if r["neighbour"] else None)),
            "excess": r.get("excess"),
            "shape_shipped": r["shape_shipped"],
            "shape_mine": r["shape_mine"],
            "alone_in_bar": r["alone_in_bar"]}


def _near_misses(rows, band):
    """Glyphs the rule does NOT delete but which sit just outside a cut.

    ⚠️ THE FALSE-NEGATIVE SIDE, WHICH NOBODY HAS LOOKED AT. A rule that deletes
    music is usually audited on what it deletes; the other question is what it
    KEEPS that it should not, and on a second publisher that is where a band
    that failed to transfer would show. Selected as: POSITION already agrees
    (so the only thing refusing is SHAPE) and the shape misses by one of the
    two narrow cuts, or the document's OWN band would have admitted it.
    """
    out = []
    for r in rows:
        if r["shape_shipped"] or not r["position"]:
            continue
        h, asp = r["height"], r["aspect"]
        why, excess = [], 0.0
        if h > R.WHOLE_REST_INK_MAX_HEIGHT_SPACES:
            if h <= 1.10:
                why.append("height_just_over")
            excess = max(excess, (h - R.WHOLE_REST_INK_MAX_HEIGHT_SPACES)
                         / R.WHOLE_REST_INK_MAX_HEIGHT_SPACES)
        if asp < R.WHOLE_REST_INK_MIN_ASPECT:
            if asp >= 1.20:
                why.append("aspect_just_under")
            excess = max(excess, (R.WHOLE_REST_INK_MIN_ASPECT - asp)
                         / R.WHOLE_REST_INK_MIN_ASPECT)
        if asp > R.WHOLE_REST_INK_MAX_ASPECT:
            why.append("aspect_over_the_max")
            excess = max(excess, (asp - R.WHOLE_REST_INK_MAX_ASPECT)
                         / R.WHOLE_REST_INK_MAX_ASPECT)
        if r["shape_mine"]:
            why.append("this_document_own_band_would_admit_it")
        if why:
            row = dict(r)
            row["near_miss_because"] = why
            # ⚠️ HOW CLOSE IT CAME, as a FRACTION of the cut it failed, so the
            # three cuts are comparable. Sorting by this is what makes a
            # "sample near the cuts" a defined set rather than a convenient
            # one -- the crops that follow are the top of this ranking, and
            # anybody can re-derive which ones they were.
            row["excess"] = round(excess, 4)
            out.append(row)
    return sorted(out, key=lambda r: (r["excess"], r["subject"]))


if __name__ == "__main__":
    raise SystemExit(main())
