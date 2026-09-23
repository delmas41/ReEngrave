"""ROADMAP 2.7 — MEASURE the accidental->notehead window, never guess it.

The legacy pair rule (`transcribe._pair_accidentals_to_noteheads`) admits a
notehead whose y-centre is within `0.6 * the accidental's own height` and puts
no bound at all on x.  ⚠️ BOTH HALVES ARE UNMEASURED: the y window is derived
from the MARK'S OWN BOX, which is the mistake the augmentation-dot gate paid
193 edits for (see `ownership.adjudicate_articulation_owner`'s own warning),
and an unbounded x lets a glyph at the head of a bar claim a note four beats
away.

This prints the two histograms off a SAVED record so the window can be read off
the gap rather than asserted:

  * dx — from the accidental's RIGHT edge to the notehead's LEFT edge,
    in STAFF SPACES (`Q.CELL_STAFF_SPACE`, the cell's own unit).
  * dy — |y-centre difference|, in staff spaces.

⚠️ IT DECIDES NOTHING. It measures the population; the window it suggests is
recorded in FINDINGS.md and typed into `ownership.py` as a named constant.

    python3 probe/gap_histogram.py --record <rec.json> --label litolff
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402


def _pct(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round((len(s) - 1) * p))))
    return round(s[i], 4)


def _hist(xs, lo, hi, step):
    edges, counts = [], []
    x = lo
    while x < hi:
        counts.append(sum(1 for v in xs if x <= v < x + step))
        edges.append(round(x, 3))
        x += step
    return list(zip(edges, counts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--all-classes", dest="in_bar_only", action="store_false",
                    help="include keyFlat/keySharp/keyNatural (the signature's "
                         "own glyphs), which the default excludes")
    ap.add_argument("--anchor-flat", type=float, default=0.5,
                    help="where in a FLAT's box the pitch it names sits, as a "
                         "fraction of the box height from the top. 0.5 is the "
                         "uncorrected box centre; Bravura says 0.715")
    ap.add_argument("--dx-window", type=float, default=1.75,
                    help="the x window, in staff spaces, that the conditional "
                         "dy histogram is measured INSIDE")
    a = ap.parse_args()

    rec = load_record(a.record)
    rec = rec.get("record", rec)

    boxes: dict = {}        # cell key -> [(gi, class, x, y, w, h, category)]
    space: dict = {}        # cell key -> staff space, canonical px
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "cell_staff_space":
            space[o["subject"]] = float(o["value"])
        elif q == "glyph_box":
            sub = o["subject"]
            cell = sub.rsplit("/", 1)[0].replace("glyph/", "cell/", 1)
            v = o["value"]
            if not isinstance(v, (list, tuple)) or len(v) < 5:
                continue
            cat = (o.get("detail") or {}).get("category")
            boxes.setdefault(cell, []).append(
                (int(sub.rsplit("/", 1)[1]), str(v[0]), float(v[1]),
                 float(v[2]), float(v[3]), float(v[4]), cat))

    classes: dict = {}
    dxs, dys, dys_near = [], [], []
    dys_inwindow: list = []
    by_class_dy: dict = {}
    signed: dict = {}
    anchor: dict = {}
    only: dict = {}
    only_frac: dict = {}
    no_head_right = 0
    total = 0
    in_bar = 0
    for cell, items in boxes.items():
        sp = space.get(cell)
        heads = [i for i in items if i[6] == "notehead"]
        for gi, cls, x, y, w, h, cat in items:
            if cat != "accidental":
                continue
            classes[cls] = classes.get(cls, 0) + 1
            total += 1
            # ⚠️ `keyFlat` / `keySharp` / `keyNatural` ARE THE SIGNATURE'S OWN
            # GLYPHS and are NOT the in-bar accidental this item is about. The
            # detector draws the distinction itself and `a.in_bar_only` honours
            # it: 2,058 - 527 = the 1,531 the roadmap names.
            if a.in_bar_only and cls.lower().startswith("key"):
                continue
            in_bar += 1
            if sp is None:
                continue
            ax1 = x + w
            # ⚠️⚠️ THE FLAT'S BOX IS NOT CENTRED ON THE PITCH IT NAMES, and
            # `--anchor-flat` is how that is MEASURED rather than argued. A
            # flat carries an ASCENDER above its bowl, so its bounding box
            # extends upward from the note; a sharp, a natural and a double
            # sharp are symmetric about theirs. Bravura -- the SMuFL reference
            # font, an EXTERNAL source and not our own reading -- puts the
            # flat's box centre 0.528 staff spaces ABOVE its origin and its
            # anchor at 0.715 of the box height from the top, against 0.501 /
            # 0.504 / 0.504 for sharp / natural / double sharp. Run with and
            # without: if the correction is real the second mode in the dy
            # histogram collapses, and if it is not, nothing moves.
            frac = (a.anchor_flat if cls.lower().startswith(
                ("accidentalflat", "accidentaldoubleflat")) else 0.5)
            ayc = y + h * frac
            cands = [hd for hd in heads if hd[2] + hd[4] >= ax1]
            if not cands:
                no_head_right += 1
                continue
            # nearest to the right by x, regardless of height
            near = min(cands, key=lambda hd: max(0.0, hd[2] - ax1))
            dxs.append(max(0.0, near[2] - ax1) / sp)
            dys_near.append(abs((near[3] + near[5] / 2.0) - ayc) / sp)
            # and the best height match among those within 3 spaces of x
            close = [hd for hd in cands if (hd[2] - ax1) / sp <= 3.0]
            if close:
                best = min(close,
                           key=lambda hd: abs((hd[3] + hd[5] / 2.0) - ayc))
                dys.append(abs((best[3] + best[5] / 2.0) - ayc) / sp)
            # ⚠️ THE CONDITIONAL MEASUREMENT, AND IT IS THE ONE THE WINDOW IS
            # CUT FROM. Unconditioned, `dy` is a MIXTURE: an accidental whose
            # own head the detector missed picks up whatever head is nearest in
            # height, and that population has no window. Restricted to the
            # glyphs already INSIDE the x window, the remainder is the pairs
            # the rule will actually be asked about. Reported in POSITIONS
            # (half-spaces, `Q.NOTEHEAD_STAFF_POSITION`'s own unit), because
            # one diatonic step is 1.0 of them and the question the tolerance
            # settles is whether the NEXT step could also fit.
            inx = [hd for hd in cands
                   if (hd[2] - ax1) / sp <= a.dx_window]
            if inx:
                b2 = min(inx, key=lambda hd: abs((hd[3] + hd[5] / 2.0) - ayc))
                dpos = abs((b2[3] + b2[5] / 2.0) - ayc) / (sp / 2.0)
                dys_inwindow.append(dpos)
                by_class_dy.setdefault(cls, []).append(dpos)
                # ⚠️⚠️ SIGNED, AND THE SIGN IS AN ENGRAVING FACT, NOT NOISE.
                # A flat is drawn with an ASCENDER above its bowl, so its
                # bounding box extends UPWARD from the pitch it names and its
                # box centre is NOT that pitch; a sharp and a natural are
                # symmetric about theirs. Unsigned, that asymmetry reads as a
                # wider tolerance and the window gets loosened to swallow a
                # systematic offset -- the shape this project has already paid
                # for. Larger canonical y is LOWER on the page, so a positive
                # value here means the head sits BELOW the glyph's box centre.
                hyc = b2[3] + b2[5] / 2.0
                signed.setdefault(cls, []).append((hyc - ayc) / (sp / 2.0))
                if h:
                    anchor.setdefault(cls, []).append((hyc - y) / h)
                # ⚠️⚠️ THE UNBIASED ESTIMATOR, AND WITHOUT IT THE NUMBER ABOVE
                # CANNOT BE READ. `b2` was chosen as the head NEAREST IN
                # HEIGHT, so its offset is selected on the very quantity being
                # estimated and is pulled toward zero by construction -- a
                # measurement that agrees with our own choosing, which rule 5
                # forbids using as evidence. Where exactly ONE head stands in
                # the x window there was no choice to make, and that
                # sub-population estimates the offset honestly.
                if len(inx) == 1 and h:
                    only.setdefault(cls, []).append((hyc - ayc) / (sp / 2.0))
                    only_frac.setdefault(cls, []).append((hyc - y) / h)

    out = {
        "label": a.label,
        "record": a.record,
        "accidental_glyphs": total,
        "in_bar_only": a.in_bar_only,
        "in_bar_glyphs": in_bar,
        "by_class": dict(sorted(classes.items(), key=lambda kv: -kv[1])),
        "no_notehead_to_the_right": no_head_right,
        "dx_spaces": {
            "n": len(dxs),
            "p05": _pct(dxs, 0.05), "p25": _pct(dxs, 0.25),
            "median": _pct(dxs, 0.5), "p75": _pct(dxs, 0.75),
            "p90": _pct(dxs, 0.90), "p95": _pct(dxs, 0.95),
            "p99": _pct(dxs, 0.99),
            "max": round(max(dxs), 3) if dxs else None,
            "hist_0_to_6_step_0.25": _hist(dxs, 0, 6, 0.25),
        },
        "dy_spaces_best_height_within_3sp": {
            "n": len(dys),
            "median": _pct(dys, 0.5), "p75": _pct(dys, 0.75),
            "p90": _pct(dys, 0.90), "p95": _pct(dys, 0.95),
            "p99": _pct(dys, 0.99),
            "max": round(max(dys), 3) if dys else None,
            "hist_0_to_3_step_0.1": _hist(dys, 0, 3, 0.1),
        },
        "dx_window_spaces_used": a.dx_window,
        "anchor_flat_used": a.anchor_flat,
        "dy_positions_inside_dx_window": {
            "n": len(dys_inwindow),
            "median": _pct(dys_inwindow, 0.5), "p75": _pct(dys_inwindow, 0.75),
            "p90": _pct(dys_inwindow, 0.90), "p95": _pct(dys_inwindow, 0.95),
            "p99": _pct(dys_inwindow, 0.99),
            "max": round(max(dys_inwindow), 3) if dys_inwindow else None,
            "hist_0_to_4_step_0.1": _hist(dys_inwindow, 0, 4, 0.1),
            "by_class_median": {c: _pct(v, 0.5)
                                for c, v in sorted(by_class_dy.items())},
            "by_class_n": {c: len(v) for c, v in sorted(by_class_dy.items())},
            "by_class_p90": {c: _pct(v, 0.90)
                             for c, v in sorted(by_class_dy.items())},
        },
        "signed_dy_positions_by_class": {
            c: {"n": len(v), "p25": _pct(v, 0.25), "median": _pct(v, 0.5),
                "p75": _pct(v, 0.75)}
            for c, v in sorted(signed.items())},
        "UNBIASED_only_one_head_in_window_signed_dy_positions": {
            c: {"n": len(v), "p25": _pct(v, 0.25), "median": _pct(v, 0.5),
                "p75": _pct(v, 0.75)}
            for c, v in sorted(only.items())},
        "UNBIASED_only_one_head_in_window_anchor_fraction": {
            c: {"n": len(v), "p25": _pct(v, 0.25), "median": _pct(v, 0.5),
                "p75": _pct(v, 0.75)}
            for c, v in sorted(only_frac.items())},
        "head_centre_as_fraction_of_glyph_height_by_class": {
            c: {"n": len(v), "p25": _pct(v, 0.25), "median": _pct(v, 0.5),
                "p75": _pct(v, 0.75)}
            for c, v in sorted(anchor.items())},
        "dy_spaces_nearest_by_x": {
            "n": len(dys_near),
            "median": _pct(dys_near, 0.5), "p90": _pct(dys_near, 0.90),
            "hist_0_to_3_step_0.1": _hist(dys_near, 0, 3, 0.1),
        },
    }
    text = json.dumps(out, indent=2)
    if a.out:
        Path(a.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
