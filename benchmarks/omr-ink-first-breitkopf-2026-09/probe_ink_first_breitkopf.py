"""The ink-first test on the SHATTERING plate, joined to the print.

`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §7 is the governing
falsification test:

    comparing the ink extent against the detector's box should sort the
    *already-adjudicated* failures into distinct, countable shapes ... IF THAT
    TABLE COMES BACK UNDIFFERENTIATED -- if the disagreement does not separate
    cases the print has already settled -- THE FRAMING IS WRONG and the
    detector's box is as good a subject as the ink.

It was run on 2026-09-18 (`benchmarks/omr-ink-extent-2026-09`) and did NOT hold
on Litolff, with two stated reasons: that plate MERGES, so "is this a merge?"
cannot discriminate there; and the test was run BOX-FIRST, the arrangement the
document argues against. It named its own blocker: a Breitkopf record with
`OMR_INK` on.

This runs it on Breitkopf, ink-first, with a residue split.

⚠️ WHAT "INK-FIRST" MEANS HERE, because it is the method finding of the run
before this one. BOX-FIRST asks *what ink is inside my box* -- it clips to the
box, so it can never see that the box is a carved-out sub-part of something
bigger, which is one of the four shapes §7 predicts. INK-FIRST makes the PIECE
the subject and the box an annotation on it: how much of the PIECE does the box
claim, how many pieces does the box straddle, what is the piece's own extent
and aspect. The print verdicts are ON BOXES, so the join must still go through a
box -- what changes is which object's extent the numbers describe.

⚠️ NO INVENTED SHAPE CUTS. The run before this one reported its own cuts as
"invented rather than measured" and would not stand on them. The separation
question is asked THRESHOLD-FREE first, with AUC (P[a random junk box scores
above a random real box]; null 0.5) against a permutation null, and a cut is
named only where the distributions leave a gap. The four-way §7 sort is
reported afterwards, descriptively, with every cut's provenance stated.

READ-ONLY with respect to `tools/`: nothing here is imported by the pipeline,
and this script writes only under its own benchmark directory.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# Constants, and where each one comes from
# ─────────────────────────────────────────────────────────────────────────────

#: ⚠️ THE ONLY PLACE A NUMBER IS ASSERTED ABOUT SHAPE, and every one is either
#: a SHIPPED constant read out of the tree's own documented filters or is
#: marked INVENTED. `detect_stems`' six filters are documented in CLAUDE.md as
#: `too TALL (h > 8.0 spaces)`, `too WIDE (w > 0.6 spaces)`,
#: `too SHORT (h < 2.0 spaces)` -- those three are the vertical-run window and
#: are reused verbatim rather than re-chosen.
STEM_MIN_H_SPACES = 2.0      # shipped: detect_stems `too SHORT`
STEM_MAX_W_SPACES = 0.6      # shipped: detect_stems `too WIDE`
STEM_MAX_H_SPACES = 8.0      # shipped: detect_stems `too TALL`

#: ⚠️ INVENTED, and used ONLY to split residue from marks in the census --
#: never in the separation test, whose axes are all continuous. A quarter of a
#: staff space is a quarter of a notehead's height; nothing in the tree fixes
#: it. The census reports the sweep 0.15/0.25/0.40 beside it so a reader can
#: see whether the split is load-bearing.
SPECK_MAX_SPACES = 0.25
SPECK_SWEEP = (0.15, 0.25, 0.40)

#: A notehead is ~1.0 space tall and ~1.3 wide (CLAUDE.md's width lane,
#: measured 1.26-1.78). Anything past 4 staff spaces in BOTH dimensions is a
#: merge by any reading. INVENTED as a census boundary only.
BLOB_MIN_SPACES = 4.0

#: Control tolerance: the ink row's own `width_spaces` must reproduce from its
#: canonical corners. The run before this one measured median error 0.0000 over
#: 7,093 rows, so this is loose by three orders of magnitude and still catches
#: a convention error, which is what it is for.
BOX_CONVENTION_TOL_SPACES = 0.02

PERMUTATIONS = 2000


# ─────────────────────────────────────────────────────────────────────────────
# Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_observations(path):
    """Rows from either a full staged record or a GATHER-only dump.

    ⚠️ RAISES rather than returning empty. `pipeline.run_staged` writes
    `result["record"]` while `gather_only.py` writes the log at top level, and
    a reader that guessed wrong would report a clean, believable ZERO -- which
    this repo has paid for repeatedly. An unrecognised shape is a refusal.
    """
    with open(path) as f:
        doc = json.load(f)
    meta = {}
    if "observations" in doc:
        log = doc
    elif isinstance(doc.get("record"), dict) and "observations" in doc["record"]:
        log = doc["record"]
        # ⚠️ `settings` is nested INSIDE `provenance` (`__main__.py` does
        # `prov["settings"] = _settings(args)` before writing), not beside it.
        # Reading it at the top level returns None and the run reports "env
        # overrides: None" -- a believable blank rather than an error, on the
        # one field that says which FLAGS produced the record.
        prov = doc.get("provenance") or {}
        meta = {"provenance": {k: v for k, v in prov.items()
                               if k != "settings"},
                "settings": prov.get("settings") or doc.get("settings")}
    else:
        raise SystemExit(
            f"REFUSED: {path} is neither a staged record nor a gather dump "
            f"(top-level keys: {sorted(doc.keys())[:8]})")
    obs = log.get("observations")
    if not obs:
        raise SystemExit(f"REFUSED: {path} carries no observations")
    return obs, meta


def subject_parts(subject):
    """`glyph/<page>/<system>/<staff>/<cell>/<index>` -> the tuple.

    ⚠️ The KIND is the FIRST segment, not the last -- a `key.rsplit('/',1)[0]`
    on a subject key is a defect this repo has already recorded.
    """
    bits = subject.split("/")
    return bits[0], tuple(bits[1:])


def cell_of(subject):
    kind, rest = subject_parts(subject)
    return tuple(rest[:4])


def index_rows(obs):
    ink_by_cell = defaultdict(list)
    glyph_by_subject = {}
    conf_by_subject = {}
    space_by_cell = {}
    for o in obs:
        q = o.get("quantity")
        s = o.get("subject") or ""
        if q == "ink":
            ink_by_cell[cell_of(s)].append(o)
        elif q == "glyph_box":
            glyph_by_subject[s] = o
        elif q == "glyph_conf":
            conf_by_subject[s] = o.get("value")
        elif q == "cell_staff_space":
            space_by_cell[cell_of(s)] = o.get("value")
    return ink_by_cell, glyph_by_subject, conf_by_subject, space_by_cell


# ─────────────────────────────────────────────────────────────────────────────
# Geometry -- ⚠️ THE TWO CONVENTIONS, ASSERTED AT THE READ SITE
# ─────────────────────────────────────────────────────────────────────────────

def glyph_canonical_wh(row):
    """`Q.GLYPH_BOX.value` is `[name, x, y, w, h]` -- a WIDTH box, name first."""
    v = row["value"]
    if not (isinstance(v, (list, tuple)) and len(v) == 5
            and isinstance(v[0], str)):
        raise SystemExit(f"REFUSED: glyph_box value is not [name,x,y,w,h]: {v}")
    return float(v[3]), float(v[4])


def ink_canonical_corners(row):
    """`Q.INK.detail.ink_bbox_canonical` is `[x0, y0, x1, y1]` -- CORNERS.

    ⚠️ The opposite convention from `Q.GLYPH_BOX.value`, in the same record.
    Read alike, a notehead's width comes out negative and the run reports a
    clean `NO_INK_UNDER_BOX` -- exactly what happened on 2026-09-18.
    """
    b = row["detail"]["ink_bbox_canonical"]
    x0, y0, x1, y1 = (float(v) for v in b)
    if not (x1 > x0 and y1 > y0):
        raise SystemExit(
            f"REFUSED: ink_bbox_canonical is not corners: {b} on {row['subject']}")
    return x0, y0, x1, y1


def page_corners(row):
    """`detail.bbox_page_px` is CORNERS for BOTH quantities (control B checks)."""
    b = (row.get("detail") or {}).get("bbox_page_px")
    if not b:
        return None
    x0, y0, x1, y1 = (float(v) for v in b)
    return x0, y0, x1, y1


def inter_area(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy


def box_area(a):
    return max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])


# ─────────────────────────────────────────────────────────────────────────────
# Controls
# ─────────────────────────────────────────────────────────────────────────────

def control_box_conventions(obs, ink_rows, glyph_rows, out):
    """CONTROL B -- each quantity's box is read in ITS OWN convention.

    Two halves, and the second is the one with teeth: the ink row's canonical
    corners must reproduce the row's OWN `width_spaces`, and the same corners
    read as `[x, y, w, h]` must NOT. Without the second half the control passes
    for a reader that happens never to have been given a wrong box.
    """
    errs, wrong_errs = [], []
    for r in ink_rows:
        d = r["detail"]
        sp = float(d.get("cell_staff_space_px") or 0.0)
        if sp <= 0:
            continue
        x0, y0, x1, y1 = ink_canonical_corners(r)
        errs.append(abs((x1 - x0) / sp - float(d["width_spaces"])))
        # the SAME numbers read as a width box: x1 would be a width
        wrong_errs.append(abs(x1 / sp - float(d["width_spaces"])))
    ratio_errs = []
    for r in glyph_rows:
        w, h = glyph_canonical_wh(r)
        pc = page_corners(r)
        if not pc or h <= 0:
            continue
        pw, ph = pc[2] - pc[0], pc[3] - pc[1]
        if ph <= 0:
            continue
        ratio_errs.append(abs((w / h) - (pw / ph)))
    ok = bool(errs) and median(errs) <= BOX_CONVENTION_TOL_SPACES
    teeth = bool(wrong_errs) and median(wrong_errs) > BOX_CONVENTION_TOL_SPACES
    ratio_ok = bool(ratio_errs) and median(ratio_errs) <= 0.02
    out.append(f"  B1 ink corners reproduce width_spaces   median err "
               f"{median(errs):.4f} spaces over {len(errs)} rows -> "
               f"{'PASS' if ok else 'FAIL'}")
    out.append(f"  B1' the SAME numbers read as [x,y,w,h]  median err "
               f"{median(wrong_errs):.4f} spaces -> "
               f"{'control has TEETH' if teeth else 'VACUOUS'}")
    out.append(f"  B2 glyph canonical w/h == page w/h      median err "
               f"{median(ratio_errs):.4f} over {len(ratio_errs)} rows -> "
               f"{'PASS' if ratio_ok else 'FAIL'}")
    return ok and teeth and ratio_ok


def control_document_identity(tiles, glyph_by_subject, out, label):
    """CONTROL A -- the record and the verdicts are about the SAME document.

    ⚠️ A subject's last coordinate is an index into the detector's output list,
    so a subject key from ANOTHER document can land on a real row here by pure
    coincidence: the 2026-09-18 draft joined Breitkopf verdicts to the Litolff
    record and 11 of 26 "matched". Presence is therefore NOT the test. The test
    is that the record's own class name for each matched subject equals the
    class the crop manifest recorded when the tile was cut.
    """
    present = agree = 0
    disagreements = []
    for t in tiles:
        row = glyph_by_subject.get(t["subject"])
        if row is None:
            continue
        present += 1
        got = row["value"][0]
        want = t.get("cls")
        if want is None or got == want:
            agree += 1
        else:
            disagreements.append((t["id"], t["subject"], want, got))
    rate = (agree / present) if present else 0.0
    out.append(f"  A  [{label}] subjects present {present}/{len(tiles)}, "
               f"class agrees {agree}/{present} ({rate:.3f})")
    for d in disagreements[:5]:
        out.append(f"       DISAGREE {d[0]} {d[1]}: manifest {d[2]!r} "
                   f"record {d[3]!r}")
    return present, agree, rate


# ─────────────────────────────────────────────────────────────────────────────
# Statistics -- threshold-free
# ─────────────────────────────────────────────────────────────────────────────

def median(xs):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def auc(pos, neg):
    """P[a random `pos` scores above a random `neg`], ties counted as half.

    Threshold-free, so it cannot be gamed by a cut chosen after the fact, and
    its null is exactly 0.5 -- which is what makes "undifferentiated" a
    statement this probe can actually make.
    """
    if not pos or not neg:
        return float("nan")
    s = 0.0
    for a in pos:
        for b in neg:
            s += 1.0 if a > b else (0.5 if a == b else 0.0)
    return s / (len(pos) * len(neg))


def auc_null(values, n_pos, seed=20260922, k=PERMUTATIONS):
    """Permutation null for AUC: shuffle the LABELS, keep the values."""
    rng = random.Random(seed)
    vals = list(values)
    out = []
    for _ in range(k):
        rng.shuffle(vals)
        out.append(auc(vals[:n_pos], vals[n_pos:]))
    out.sort()
    return out[int(0.025 * k)], out[int(0.5 * k)], out[int(0.975 * k)]


def widest_empty_interval(pos, neg):
    """The largest gap between the two populations' sorted values.

    This repo's own tell for a real convention is a MEASURED EMPTY INTERVAL,
    against a smooth slope with a threshold fitted into it. Returns
    (gap, lo, hi) for the widest range containing no value of EITHER group.
    """
    xs = sorted(set(list(pos) + list(neg)))
    if len(xs) < 2:
        return 0.0, None, None
    best = (0.0, None, None)
    for a, b in zip(xs, xs[1:]):
        if b - a > best[0]:
            best = (b - a, a, b)
    return best


# ─────────────────────────────────────────────────────────────────────────────
# The ink-first description of an adjudicated box
# ─────────────────────────────────────────────────────────────────────────────

def describe(tile, glyph_row, ink_rows, conf, attribution="fill"):
    """Ink-first features for one adjudicated box, in PAGE pixels.

    ⚠️ PAGE PIXELS, not canonical: both quantities carry `bbox_page_px` as
    CORNERS, so the join needs no convention conversion at all, and the one
    trap that broke the previous run cannot arise in the joining arithmetic.
    The canonical boxes are still read -- by control B, whose job is to catch
    exactly that.
    """
    gb = page_corners(glyph_row)
    if gb is None:
        return None
    gb_area = box_area(gb)
    if gb_area <= 0:
        return None
    sp = float((glyph_row.get("detail") or {}).get("staff_space_px") or 0.0)

    # ⚠️⚠️ ATTRIBUTION IS FILL-WEIGHTED, AND THE FIRST DRAFT OF THIS PROBE WAS
    # WRONG WITHOUT IT. A piece's `bbox_page_px` is its BOUNDING BOX, and a
    # sprawling beam-and-stem merge has a bounding box covering half the cell
    # while its ink is nowhere near this particular box -- so ranking by raw
    # bbox intersection attributed almost every box to the biggest blob in its
    # cell, and `box_share_of_piece` then came back tiny for EVERY verdict,
    # making the CARVED axis vacuous rather than negative. Weighting the
    # overlap by the piece's own `ink_fill` estimates the INK in the overlap
    # instead of the AREA, which is the quantity the question is about. The
    # pilot's junk/real fill medians (0.074 vs 0.266) are exactly the spread
    # that makes the weighting bite.
    touching = []
    for r in ink_rows:
        ib = page_corners(r)
        if ib is None:
            continue
        ia = inter_area(gb, ib)
        if ia > 0:
            fill = float(r["detail"].get("ink_fill") or 0.0)
            w = ia * max(fill, 1e-6) if attribution == "fill" else ia
            touching.append((w, ia, r, ib))
    if not touching:
        return {"tile": tile, "n_pieces": 0, "no_ink": True}

    touching.sort(key=lambda t: -t[0])
    total_expected = sum(t[0] for t in touching) or 1.0
    n_substantial = sum(1 for t in touching if t[0] / total_expected >= 0.05)
    _w, ia, prim, pb = touching[0]
    pd = prim["detail"]
    pb_area = box_area(pb)

    w_sp = float(pd.get("width_spaces") or 0.0)
    h_sp = float(pd.get("height_spaces") or 0.0)
    gw, gh = glyph_canonical_wh(glyph_row)
    csp = float(pd.get("cell_staff_space_px") or 0.0)

    return {
        "tile": tile,
        "no_ink": False,
        # ── SHATTERED axis: how many separate pieces this one box straddles.
        #    `n_pieces` counts every piece whose bbox touches; `n_substantial`
        #    only those carrying >=5% of the expected ink in the overlap, which
        #    is the count a reader would make by eye.
        "n_pieces": len(touching),
        "n_substantial": n_substantial,
        # ── MERGE axis: the piece's extent against the box's
        "ink_over_box": pb_area / gb_area,
        # ── CARVED SUB-PART axis: how much of the PIECE the box claims
        "box_share_of_piece": (ia / pb_area) if pb_area > 0 else float("nan"),
        # ── BARLINE axis: the piece's own aspect, in staff spaces
        "piece_w_spaces": w_sp,
        "piece_h_spaces": h_sp,
        "piece_aspect": (h_sp / w_sp) if w_sp > 0 else float("nan"),
        # ── the ink layer's own merge warning, carried rather than recomputed
        "n_components": pd.get("ink_n_components"),
        "share_of_cell": pd.get("ink_share_of_cell"),
        "coverage": pd.get("ink_detector_coverage"),
        "ink_fill": pd.get("ink_fill"),
        # ── BOX-ALONE features, for the arrangement comparison
        "box_w_spaces": (gw / csp) if csp > 0 else float("nan"),
        "box_h_spaces": (gh / csp) if csp > 0 else float("nan"),
        "box_aspect": (gh / gw) if gw > 0 else float("nan"),
        "conf": conf,
    }


# ─────────────────────────────────────────────────────────────────────────────
# The residue split -- the whole ink population, not just adjudicated boxes
# ─────────────────────────────────────────────────────────────────────────────

def stratum(w_sp, h_sp, speck_cut=SPECK_MAX_SPACES):
    big = max(w_sp, h_sp)
    if big < speck_cut:
        return "SPECK"
    if (h_sp >= STEM_MIN_H_SPACES and w_sp <= STEM_MAX_W_SPACES):
        return "VERTICAL" if h_sp <= STEM_MAX_H_SPACES else "VERTICAL_TALL"
    if w_sp >= BLOB_MIN_SPACES and h_sp >= BLOB_MIN_SPACES:
        return "BLOB"
    return "MARK_SIZED"


def census(ink_rows, speck_cut=SPECK_MAX_SPACES):
    rows = defaultdict(lambda: {"n": 0, "area": 0.0, "zero_det": 0,
                                "cov": [], "n_comp": []})
    total_area = 0.0
    for r in ink_rows:
        d = r["detail"]
        w_sp = float(d.get("width_spaces") or 0.0)
        h_sp = float(d.get("height_spaces") or 0.0)
        a = float(d.get("ink_area_px") or 0.0)
        cov = float(d.get("ink_detector_coverage") or 0.0)
        k = stratum(w_sp, h_sp, speck_cut)
        e = rows[k]
        e["n"] += 1
        e["area"] += a
        e["cov"].append(cov)
        e["n_comp"].append(d.get("ink_n_components"))
        if cov <= 0.0:
            e["zero_det"] += 1
        total_area += a
    return rows, total_area


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

REAL = {"stem_printed_down", "stem_printed_up", "no_stem_printed"}
JUNK = {"not_a_notehead"}

#: The whole-note pass adjudicated WHAT THE PRINT SHOWS rather than a stem
#: direction, so its rows have to be mapped into this file's vocabulary.
#: ⚠️ `dotted_half_note` maps to REAL: the record's CLASS is false there, but
#: the ink IS a notehead, which is the only question this probe asks.
PRINT_SHOWS_TO_VERDICT = {
    "time_signature_digit_8": "not_a_notehead",
    "hairpin_or_beam_wedge": "not_a_notehead",
    "staff_line_gap": "not_a_notehead",
    "dotted_half_note": "stem_printed_up",
    "possibly_a_real_whole_note": "no_stem_printed",
}


def extra_breitkopf_tiles(crop_root, P):
    """The two OTHER Breitkopf print passes, tagged and reported apart.

    ⚠️⚠️ THEY ARE DIFFERENT SAMPLES AND MUST NOT BE SILENTLY POOLED. The
    `sample` rows were drawn from the rejection census's six buckets; the
    `standoff` rows are exactly the heads on which two of our own readers
    DISAGREE; the `wholenotes` rows are heads the record calls WHOLE while
    still giving them a stem direction. Each is stratified on something
    different, and only the first is stratified on geometry. They are loaded
    so the separation question has more than 33 junk cases to stand on, and
    every table that uses them prints the per-source split beside the pooled
    number.
    """
    out = []
    # ── the 26-head standoff ────────────────────────────────────────────────
    man = json.load(open(os.path.join(
        crop_root, "out", "crop-manifest-standoff.json")))
    adj = json.load(open(os.path.join(
        crop_root, "ADJUDICATION-standoff.json")))
    by_id = {r["id"]: r for r in adj["rows"]}
    for t in man["tiles"]:
        v = by_id.get(t["id"])
        if v:
            out.append({**t, "verdict": v["verdict"], "source": "standoff",
                        "flags": [], "confidence": v.get("confidence")})
    # ── the whole-note contradiction ────────────────────────────────────────
    man = json.load(open(os.path.join(
        crop_root, "out", "crop-manifest-wholenotes-B.json")))
    adj = json.load(open(os.path.join(
        crop_root, "ADJUDICATION-wholenotes.json")))
    by_id = {r["id"]: r for r in adj["rows"]
             if r.get("publisher") == "Breitkopf"}
    unmapped = Counter()
    for t in man["tiles"]:
        v = by_id.get(t["id"])
        if not v:
            continue
        verdict = PRINT_SHOWS_TO_VERDICT.get(v.get("print_shows"))
        if verdict is None:
            unmapped[v.get("print_shows")] += 1
            continue
        out.append({**t, "verdict": verdict, "source": "wholenotes",
                    "flags": [], "confidence": v.get("confidence")})
    if unmapped:
        P(f"  ⚠️ whole-note rows with no mapping, EXCLUDED: {dict(unmapped)}")
    return out

AXES = [
    ("ink_over_box", "MERGE: piece extent / box extent"),
    ("box_share_of_piece", "CARVED: box's share of the piece"),
    ("n_pieces", "SHATTERED: pieces this box straddles"),
    ("n_substantial", "SHATTERED: pieces carrying >=5% of its ink"),
    ("piece_aspect", "BARLINE: piece h/w"),
    ("piece_h_spaces", "piece height (spaces)"),
    ("piece_w_spaces", "piece width (spaces)"),
    ("n_components", "cell's component count (merge warning)"),
    ("share_of_cell", "piece's share of its cell's ink"),
    ("coverage", "detector coverage of the piece"),
    ("ink_fill", "piece fill"),
]

BOX_ONLY_AXES = [
    ("box_w_spaces", "BOX ALONE: box width (spaces)"),
    ("box_h_spaces", "BOX ALONE: box height (spaces)"),
    ("box_aspect", "BOX ALONE: box h/w"),
    ("conf", "BOX ALONE: detector confidence"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--crop-root",
                    default="benchmarks/omr-stem-crop-pass-2026-09")
    ap.add_argument("--plate", choices=("breitkopf", "litolff"),
                    default="breitkopf",
                    help="which plate's print verdicts to join. `litolff` is "
                         "the MERGING plate and is the control arm: the same "
                         "instrument on the document where the predecessor "
                         "ran box-first and found nothing.")
    ap.add_argument("--expect-pdf", default=None,
                    help="substring the crop manifest's pdf must contain; "
                         "defaults to the plate's own IMSLP id")
    ap.add_argument("--wrong-join", action="store_true",
                    help="POSITIVE CONTROL: join the LITOLFF verdicts instead")
    ap.add_argument("--drop-junk", action="store_true",
                    help="POSITIVE CONTROL: discard every `not_a_notehead` "
                         "verdict, emptying one side of the separation. ⚠️ It "
                         "exists because a guard can only be mutation-tested "
                         "in a state where it FAILS -- with both sides "
                         "populated, deleting the DEAD guard changes nothing "
                         "and the arm reports a false survivor.")
    ap.add_argument("--attribution", choices=("fill", "area"), default="fill",
                    help="how a box is attributed to an ink piece. 'fill' "
                         "weights the bbox overlap by the piece's own ink_fill "
                         "(expected INK in the overlap); 'area' is raw bbox "
                         "overlap. ⚠️ THE CHOICE MOVES THE RESULT and both "
                         "arms are reported in FINDINGS rather than one being "
                         "chosen silently.")
    ap.add_argument("--population", choices=("main", "all"), default="main",
                    help="'main' is the 106-tile census sample; 'all' adds "
                         "the 26-head standoff and the whole-note pass, which "
                         "are DIFFERENTLY STRATIFIED and reported apart.")
    ap.add_argument("--speck-cut", type=float, default=SPECK_MAX_SPACES)
    ap.add_argument("--out", default=None)
    ap.add_argument("--json-out", default=None,
                    help="machine-readable summary, so the two-plate table is "
                         "assembled from the probe's own numbers rather than "
                         "re-typed out of its prose")
    a = ap.parse_args()

    out = []
    P = out.append

    obs, meta = load_observations(a.record)
    ink_by_cell, glyph_by_subject, conf_by_subject, space_by_cell = \
        index_rows(obs)
    ink_rows = [r for rs in ink_by_cell.values() for r in rs]

    P("=" * 78)
    P("THE INK-FIRST TEST ON THE SHATTERING PLATE -- breakthrough doc §7")
    P("=" * 78)
    P(f"record         : {a.record}")
    if meta.get("provenance"):
        P(f"provenance     : {meta['provenance']}")
    if meta.get("settings"):
        env = (meta["settings"] or {}).get("env_overrides")
        P(f"env overrides  : {env}")
    P(f"attribution    : {a.attribution}")
    P(f"ink rows       : {len(ink_rows)}")
    P(f"glyph_box rows : {len(glyph_by_subject)}")
    P(f"cells with ink : {len(ink_by_cell)}")
    pages = sorted({s.split('/')[1] for s in glyph_by_subject})
    P(f"pages in record: {pages}")

    if not ink_rows:
        P("DEAD: this record carries NO ink rows -- the arm cannot run.")
        emit(out, a.out)
        return 2

    # ── the verdicts ────────────────────────────────────────────────────────
    #: ⚠️ `--wrong-join` is the DELIBERATE mismatch: it joins the OTHER
    #: plate's verdicts, which control A must then refuse. Keeping it as "the
    #: other plate" rather than a hardcoded name means the control stays a
    #: control when `--plate litolff` is the subject.
    other = {"breitkopf": "litolff", "litolff": "breitkopf"}[a.plate]
    which = other if a.wrong_join else a.plate
    expect = a.expect_pdf or (
        "imslp984073" if which == "litolff" else "imslp317803")
    man = json.load(open(os.path.join(
        a.crop_root, "out", f"crop-manifest-{which}.json")))
    adj = json.load(open(os.path.join(
        a.crop_root, f"ADJUDICATION-{which}.json")))
    by_id = {r["id"]: r for r in adj["rows"]}
    tiles = []
    for t in man["tiles"]:
        v = by_id.get(t["id"])
        if v:
            tiles.append({**t, "verdict": v["verdict"], "source": "sample",
                          "flags": v.get("flags") or [],
                          "confidence": v.get("confidence")})
    if a.population == "all" and not a.wrong_join and which == "breitkopf":
        tiles += extra_breitkopf_tiles(a.crop_root, P)
    P(f"verdicts       : {len(tiles)} (population={a.population})")
    P(f"manifest pdf   : {man.get('pdf')}")

    P("")
    P("CONTROLS")
    ok_ident = True
    present, agree, rate = control_document_identity(
        tiles, glyph_by_subject, out, which)
    if a.wrong_join:
        P("       ^ this is the POSITIVE CONTROL arm: a LITOLFF adjudication")
        P("         against a BREITKOPF record. It MUST fail class agreement;")
        P("         subjects that are merely PRESENT are the coincidence the")
        P("         2026-09-18 draft was caught by (11 of 26).")
    if expect not in (man.get("pdf") or ""):
        P(f"  A' REFUSED: manifest pdf does not contain {expect!r}")
        ok_ident = False
    if present == 0:
        P("  DEAD: not one adjudicated subject is in this record.")
        emit(out, a.out)
        return 2
    if rate < 1.0:
        P("  A  -> FAIL (a class disagreement means these are not the same "
          "boxes; the join is refused)")
        ok_ident = False
    else:
        P("  A  -> PASS")

    ok_box = control_box_conventions(obs, ink_rows,
                                     list(glyph_by_subject.values()), out)
    if not (ok_ident and ok_box):
        P("")
        P("REFUSED: a control failed, so no table is reported.")
        emit(out, a.out)
        return 2

    # ── describe every adjudicated box, ink-first ───────────────────────────
    feats = []
    for t in tiles:
        row = glyph_by_subject.get(t["subject"])
        if row is None:
            continue
        f = describe(t, row, ink_by_cell.get(cell_of(t["subject"]), []),
                     conf_by_subject.get(t["subject"]), a.attribution)
        if f:
            feats.append(f)

    P("")
    P("REACH -- the population, before any rate")
    vh = Counter(f["tile"]["verdict"] for f in feats)
    for k, v in vh.most_common():
        P(f"  {k:24} {v}")
    no_ink = [f for f in feats if f["no_ink"]]
    P(f"  boxes with NO ink piece touching them: {len(no_ink)}")
    P(f"  joined and describable                : "
      f"{len([f for f in feats if not f['no_ink']])}")
    buckets = Counter(f["tile"].get("bucket") for f in feats)
    P("  ⚠️ census bucket the tile was SAMPLED from (the sample is stratified")
    P("     on geometry, so every AUC below is conditional on this):")
    for k, v in buckets.most_common():
        P(f"       {str(k):42} {v}")

    good = [f for f in feats if not f["no_ink"]]
    if a.drop_junk:
        good = [f for f in good if f["tile"]["verdict"] not in JUNK]
        P("  ⚠️ --drop-junk: every confirmed non-notehead discarded. This arm "
          "MUST reach the DEAD exit.")
    pos = [f for f in good if f["tile"]["verdict"] in JUNK]
    neg = [f for f in good if f["tile"]["verdict"] in REAL]
    P("")
    P(f"SEPARATION SET: {len(pos)} print-confirmed NON-noteheads vs "
      f"{len(neg)} print-confirmed noteheads")
    ps = Counter(f["tile"].get("source") for f in pos)
    ns = Counter(f["tile"].get("source") for f in neg)
    P(f"  by SOURCE (differently stratified, never silently pooled):")
    for s in sorted(set(ps) | set(ns)):
        P(f"       {s:12} junk {ps.get(s,0):>3}   real {ns.get(s,0):>3}")
    P(f"  (cannot_tell excluded: "
      f"{len([f for f in good if f['tile']['verdict'] == 'cannot_tell'])})")
    if not pos or not neg:
        P("  DEAD: one side of the separation is empty on this record.")
        emit(out, a.out)
        return 2

    # ── the table §7 asks for ───────────────────────────────────────────────
    P("")
    P("§7's QUESTION, THRESHOLD-FREE. AUC = P[junk scores above real].")
    P("A permutation null (2000 draws) gives the band a real axis must clear.")
    P("")
    P(f"  {'axis':46} {'junk med':>9} {'real med':>9} {'AUC':>6} "
      f"{'null 95% band':>16} {'sep?':>5}")
    results = []
    for key, desc in AXES + BOX_ONLY_AXES:
        pv = [float(f[key]) for f in pos
              if f.get(key) is not None and not math.isnan(float(f[key]))]
        nv = [float(f[key]) for f in neg
              if f.get(key) is not None and not math.isnan(float(f[key]))]
        if len(pv) < 3 or len(nv) < 3:
            P(f"  {desc:46} {'-':>9} {'-':>9} {'DEAD':>6}  n too small")
            continue
        A = auc(pv, nv)
        lo, _mid, hi = auc_null(pv + nv, len(pv))
        sep = "YES" if (A > hi or A < lo) else "no"
        gap, glo, ghi = widest_empty_interval(pv, nv)
        results.append((desc, key, A, lo, hi, sep, gap, glo, ghi,
                        median(pv), median(nv)))
        P(f"  {desc:46} {median(pv):9.3f} {median(nv):9.3f} {A:6.3f} "
          f"[{lo:.3f},{hi:.3f}]   {sep:>3}")

    P("")
    P("WIDEST EMPTY INTERVAL per axis -- this repo's own tell for a real")
    P("convention (a gap), against a smooth slope with a cut fitted into it.")
    for desc, key, A, lo, hi, sep, gap, glo, ghi, mp, mn in sorted(
            results, key=lambda r: -abs(r[2] - 0.5)):
        span = max(mp, mn) - min(mp, mn)
        rel = (gap / abs(span)) if span else float("nan")
        P(f"  {desc:46} gap {gap:9.4f} in "
          f"({'-' if glo is None else f'{glo:.4f}'}, "
          f"{'-' if ghi is None else f'{ghi:.4f}'})  "
          f"AUC {A:.3f}  {'SEPARATES' if sep == 'YES' else ''}")

    # ── WITHIN-STRATUM, which is the honest version of the question ─────────
    P("")
    P("WITHIN-STRATUM. ⚠️⚠️ THE SAMPLE IS NOT A RANDOM SAMPLE OF BOXES: it was")
    P("drawn from the rejection census's buckets, and on Breitkopf the junk is")
    P("concentrated in `too TALL` (12/12) and `at a CELL EDGE` (11/12), which")
    P("are defined BY GEOMETRY. So every pooled AUC above is inflated for ink")
    P("and box features ALIKE, and the only place the question can be asked")
    P("cleanly is inside a bucket that holds both classes.")
    strata = defaultdict(lambda: {"pos": [], "neg": []})
    for f in pos:
        strata[f["tile"].get("bucket")]["pos"].append(f)
    for f in neg:
        strata[f["tile"].get("bucket")]["neg"].append(f)
    any_clean = False
    for b, e in sorted(strata.items(), key=lambda kv: -len(kv[1]["pos"])):
        if len(e["pos"]) < 3 or len(e["neg"]) < 3:
            P(f"  {str(b):48} junk {len(e['pos']):>2} real {len(e['neg']):>2}"
              f"   -- too few, DEAD")
            continue
        any_clean = True
        P(f"  {str(b):48} junk {len(e['pos']):>2} real {len(e['neg']):>2}")
        for key, desc in AXES + BOX_ONLY_AXES:
            pv = [float(f[key]) for f in e["pos"]
                  if f.get(key) is not None and not math.isnan(float(f[key]))]
            nv = [float(f[key]) for f in e["neg"]
                  if f.get(key) is not None and not math.isnan(float(f[key]))]
            if len(pv) < 3 or len(nv) < 3:
                continue
            A = auc(pv, nv)
            lo, _m, hi = auc_null(pv + nv, len(pv))
            mark = "  <-- SEPARATES" if (A > hi or A < lo) else ""
            P(f"       {desc:44} AUC {A:5.3f}  null [{lo:.3f},{hi:.3f}]{mark}")
    if not any_clean:
        P("  DEAD: no bucket holds >=3 of both classes on this record, so the")
        P("  pooled table cannot be corrected for its own sampling here.")

    # ── §7's ACTUAL FALSIFIER ───────────────────────────────────────────────
    ink_axes = {k for k, _ in AXES}
    ink_best = max((r for r in results if r[1] in ink_axes),
                   key=lambda r: abs(r[2] - 0.5), default=None)
    box_best = max((r for r in results if r[1] not in ink_axes),
                   key=lambda r: abs(r[2] - 0.5), default=None)
    P("")
    P("=" * 78)
    P("§7's FALSIFIER: *the detector's box is as good a subject as the ink*")
    P("=" * 78)
    P("⚠️ AUC is reported as |AUC-0.5|+0.5 (direction-free): an axis on which")
    P("   junk scores LOWER separates exactly as well as one where it scores")
    P("   higher, and the sign is a fact about the axis, not about the case.")
    if ink_best:
        P(f"  best INK-derived axis : {ink_best[0]:44} "
          f"AUC {ink_best[2]:.3f} -> {0.5 + abs(ink_best[2]-0.5):.3f}")
    if box_best:
        P(f"  best BOX-ALONE axis   : {box_best[0]:44} "
          f"AUC {box_best[2]:.3f} -> {0.5 + abs(box_best[2]-0.5):.3f}")
    if ink_best and box_best:
        di = abs(ink_best[2] - 0.5)
        db = abs(box_best[2] - 0.5)
        P("")
        if db >= di:
            P("  ⚠️⚠️ THE BOX-ALONE AXIS SEPARATES AT LEAST AS WELL AS THE BEST")
            P("       INK AXIS. That is §7's own falsifying condition, stated")
            P("       in its own words, arriving on the plate it named as the")
            P("       test's natural home.")
        else:
            P("  The best ink axis separates better than any box-alone axis,")
            P(f"  by {di - db:.3f} in |AUC-0.5|. ⚠️ That is a DIFFERENCE, not a")
            P("  validation: read the empty-interval column before calling it")
            P("  a discriminator, and read the sampling caveat above it.")

    # ── the four-way §7 sort, descriptively ─────────────────────────────────
    P("")
    P("§7's FOUR-WAY SORT, reported descriptively. ⚠️ THE CUTS ARE DERIVED")
    P("from the CONFIRMED-NOTEHEAD population's own percentiles, not measured")
    P("from an empty interval, and are therefore fitted to this plate. They")
    P("are here because §7 asks for this table, NOT as a proposed rule.")
    cut_merge = pct(sorted(float(f["ink_over_box"]) for f in neg), 0.95)
    cut_shatter = pct(sorted(float(f["n_substantial"]) for f in neg), 0.95)
    cut_carved = pct(sorted(float(f["box_share_of_piece"]) for f in neg), 0.05)
    P(f"  MERGE     cut: ink_over_box      > p95(real) = {cut_merge:.2f}")
    P(f"  SHATTERED cut: n_substantial     > p95(real) = {cut_shatter:.0f}")
    P(f"  CARVED    cut: box_share_of_piece < p05(real) = {cut_carved:.4f}")
    P(f"  BARLINE   cut: piece h >= {STEM_MIN_H_SPACES} and w <= "
      f"{STEM_MAX_W_SPACES} spaces  (SHIPPED detect_stems bounds)")

    def shape(f):
        if (f["piece_h_spaces"] >= STEM_MIN_H_SPACES
                and f["piece_w_spaces"] <= STEM_MAX_W_SPACES):
            return "BARLINE"
        if f["n_substantial"] > cut_shatter:
            return "SHATTERED"
        if f["box_share_of_piece"] < cut_carved:
            return "CARVED"
        if f["ink_over_box"] > cut_merge:
            return "MERGE"
        return "AGREES"

    P("")
    P(f"  {'print verdict':24} {'n':>4}  shapes")
    for verdict in ("not_a_notehead", "stem_printed_down", "stem_printed_up",
                    "no_stem_printed", "cannot_tell"):
        sub = [f for f in good if f["tile"]["verdict"] == verdict]
        if not sub:
            continue
        sh = Counter(shape(f) for f in sub)
        P(f"  {verdict:24} {len(sub):>4}  "
          f"{', '.join(f'{k} {v}' for k, v in sh.most_common())}")

    # ── residue split over the WHOLE ink population ─────────────────────────
    P("")
    P("THE RESIDUE SPLIT -- the whole ink population, which is the thing the")
    P("42.5% / 36%-of-area figures were missing. `Q.INK` filters nothing, so")
    P("a zero-detection piece is only missed music if it is MARK-SIZED.")
    rows, total = census(ink_rows, a.speck_cut)
    P(f"  {'stratum':14} {'n':>7} {'% of n':>8} {'% of AREA':>10} "
      f"{'zero-det':>9} {'median cov':>11}")
    n_tot = sum(e["n"] for e in rows.values())
    for k in ("SPECK", "MARK_SIZED", "VERTICAL", "VERTICAL_TALL", "BLOB"):
        e = rows.get(k)
        if not e:
            continue
        P(f"  {k:14} {e['n']:>7} {100*e['n']/n_tot:>7.1f}% "
          f"{100*e['area']/total:>9.1f}% "
          f"{e['zero_det']:>4}/{e['n']:<4} {median(e['cov']):>11.3f}")
    P(f"  {'TOTAL':14} {n_tot:>7} {100.0:>7.1f}% {100.0:>9.1f}%")
    P(f"  ⚠️ SPECK cut is INVENTED ({a.speck_cut} spaces). Sweep of the "
      f"count share:")
    for c in SPECK_SWEEP:
        r2, t2 = census(ink_rows, c)
        n2 = sum(e["n"] for e in r2.values())
        sp = r2.get("SPECK", {"n": 0, "area": 0.0})
        P(f"       cut {c:>4}: SPECK {100*sp['n']/n2:5.1f}% of pieces, "
          f"{100*sp['area']/t2:5.2f}% of area")

    zero = [r for r in ink_rows
            if float(r['detail'].get('ink_detector_coverage') or 0.0) <= 0.0]
    P("")
    P(f"  pieces with ZERO detector coverage: {len(zero)} "
      f"({100*len(zero)/len(ink_rows):.1f}%)")
    zs = Counter(stratum(float(r['detail'].get('width_spaces') or 0),
                         float(r['detail'].get('height_spaces') or 0),
                         a.speck_cut) for r in zero)
    zarea = defaultdict(float)
    for r in zero:
        zarea[stratum(float(r['detail'].get('width_spaces') or 0),
                      float(r['detail'].get('height_spaces') or 0),
                      a.speck_cut)] += float(r['detail'].get('ink_area_px') or 0)
    za = sum(zarea.values()) or 1.0
    for k, v in zs.most_common():
        P(f"      {k:14} {v:>6} ({100*v/len(zero):5.1f}% of them, "
          f"{100*zarea[k]/za:5.1f}% of their area)")

    if a.json_out:
        ink_axes2 = {k for k, _ in AXES}
        summary = {
            "record": a.record,
            "plate": which,
            "population": a.population,
            "attribution": a.attribution,
            "provenance": meta.get("provenance"),
            "settings": meta.get("settings"),
            "ink_rows": len(ink_rows),
            "glyph_rows": len(glyph_by_subject),
            "cells_with_ink": len(ink_by_cell),
            "pages": pages,
            "subjects_present": present,
            "class_agreement": rate,
            "n_junk": len(pos),
            "n_real": len(neg),
            "n_cannot_tell": len([f for f in good
                                  if f["tile"]["verdict"] == "cannot_tell"]),
            "by_source": {s: {"junk": ps.get(s, 0), "real": ns.get(s, 0)}
                          for s in sorted(set(ps) | set(ns))},
            "axes": [{"axis": d, "key": k, "kind":
                      "ink" if k in ink_axes2 else "box_alone",
                      "auc": A, "null_lo": lo, "null_hi": hi,
                      "separates": sep == "YES", "gap": gap,
                      "median_junk": mp, "median_real": mn}
                     for d, k, A, lo, hi, sep, gap, glo, ghi, mp, mn
                     in results],
            "residue": {k: {"n": e["n"], "area": e["area"],
                            "zero_det": e["zero_det"],
                            "median_coverage": median(e["cov"])}
                        for k, e in rows.items()},
            "residue_total_area": total,
            "zero_coverage_pieces": len(zero),
            "zero_coverage_by_stratum": dict(zs),
        }
        os.makedirs(os.path.dirname(a.json_out) or ".", exist_ok=True)
        with open(a.json_out, "w") as f:
            json.dump(summary, f, indent=1, default=str)
        P(f"\nwrote {a.json_out}")

    emit(out, a.out)
    return 0


def emit(lines, path):
    text = "\n".join(lines)
    print(text)
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    sys.exit(main())
