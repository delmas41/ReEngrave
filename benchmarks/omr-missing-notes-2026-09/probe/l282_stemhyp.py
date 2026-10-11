#!/usr/bin/env python3
"""l282_stemhyp: Sean's two hypotheses about the lost beams (2026-10-10: *"Some of the beams are getting confused with
staff lines - maybe it is a thickness issue - or is it because it is not registering the stems well enough."*), tested on
EVERY truth beam of his hand-truth page (Brahms 317803 pdf 0, 89 fully labeled cells). ROADMAP 2.82. A reading probe.

(a) THICKNESS. For every truth beam: does a staff line pass through its band (it LIES ON a line), and what thickness (in
    staff-line thicknesses) do the strokes over it measure -- split by "on a line" / "clear of every line". A beam on a line
    that is measured thin would show as a lower ratio in the first group.
(b) STEMS. For every truth beam, every truth head under it (Sean's beam box on its stem, or, where his page boxes no stem for
    the head, his beam box over it): did ADJUDICATE decide a stem for the head (`Q.HEAD_STEM`), and what did the CV stem
    finder (`line_detection.detect_stems`, run on the same prepared cell the gather reads, `candidates_out` = every
    vertical run, accepted AND refused, with the first refusing filter) see at the head: an accepted stem, a run refused
    `too WIDE` (the stem fused with the stack of heads on it), refused otherwise, or nothing.
(b') THE COUNTERFACTUAL. Re-run the CV beam reader (`detect_beams`) on every cell with the `too WIDE` runs of anchor height
    (>= the 2.8-space anchor floor) ADDED to the stem set it joins beams to -- a PROBE of the cause, not a product change --
    and count how many truth beams then get a CV stroke, and how many strokes land where Sean's truth has no beam.

    python3 l282_stemhyp.py --record R --ext ext.json --tb tb.json [--json out.json]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_tiles import PDFS  # noqa: E402
from l281_truth import Truth, in_full_cell  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def pick_cell(cells, cx, cy):
    best = None
    for c in cells:
        bb = getattr(c, "bbox_page_px", None)
        if not bb or not (bb[0] <= cx <= bb[2] and bb[1] <= cy <= bb[3]):
            continue
        lines = list(getattr(c, "staff_line_ys_canonical", None) or [])
        if len(lines) < 2:
            continue
        cyc = (cy - bb[1]) * c.upscale_factor
        d = abs(cyc - (lines[0] + lines[-1]) / 2.0)
        if best is None or d < best[0]:
            best = (d, c)
    return best[1] if best else None


def to_canon(c, x0, y0, x1, y1):
    bb, up = c.bbox_page_px, c.upscale_factor
    return ((x0 - bb[0]) * up, (y0 - bb[1]) * up, (x1 - bb[0]) * up, (y1 - bb[1]) * up)


def overlap1(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tb", required=True, help="l282_truthbeams.py --json (arm or base)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    T = Truth()
    full = S.Scope(T.full)
    run = RO.load_run(a.record)
    ext = json.load(open(a.ext))
    tb_rows = json.load(open(a.tb))["rows"]
    truth_beams = [b for b in T.beams if full.holds(b.rect)]
    bands = S.staff_bands(T.page)

    # ---- records heads <-> truth heads
    read, keys = [], []
    for k, g in run.glyphs.items():
        if g.page == 0 and g.box_page is not None and str(g.cls or "").startswith("notehead"):
            read.append((len(read), tuple(g.box_page), g.cls))
            keys.append(k)
    pairs, _ot, _or = S.match_boxes([(h.idx, h.rect, h.cls) for h in T.heads], read)
    head_key = {t: keys[r] for t, (r, _i) in pairs.items()}

    # ---- which truth heads stand under which truth beam
    under = collections.defaultdict(list)
    for h in T.heads:
        if not full.holds(h.rect) or h.idx not in head_key:
            continue
        d = T.derive(h)
        ids = d.get("beam_ids") or (d.get("marks_near") or {}).get("beams") or []
        for bid in ids:
            under[bid].append((h, d))

    from tools.omr.staged.pipeline import prepare_pages
    (pws, cells), = prepare_pages(PDFS["brahms"], [0])
    percell = {}

    def cell_data(c):
        key = id(c)
        if key not in percell:
            cand = []
            stems = LD.detect_stems(c, candidates_out=cand)
            beams0 = LD.detect_beams(c, stems=stems, rescue_tall=True)
            sp = LD._staff_line_spacing(c)
            fused = []
            for v in cand:
                if v.outcome == LD.RUN_TOO_WIDE and v.h >= 2.8 * sp:
                    fused.append(LD.LineDetection(smufl_name="stem", category="stem", x_canonical=v.x, y_canonical=v.y,
                                                  width_canonical=v.w, height_canonical=v.h, confidence=1.0))
            beams1 = LD.detect_beams(c, stems=list(stems) + fused, rescue_tall=True) if fused else beams0
            percell[key] = (sp, cand, stems, beams0, beams1, fused)
        return percell[key]

    rows = []
    tally = collections.Counter()
    seen_by = collections.Counter()
    for b in truth_beams:
        cx, cy = (b.rect[0] + b.rect[2]) / 2, (b.rect[1] + b.rect[3]) / 2
        c = pick_cell(cells, cx, cy)
        row = {"truth_beam": b.id, "rect": [round(v) for v in b.rect]}
        if c is None:
            row["note"] = "no cell"
            rows.append(row)
            continue
        sp, cand, stems, beams0, beams1, fused = cell_data(c)
        tbx = to_canon(c, *b.rect)

        def hit(bm):
            return (overlap1(bm.x_canonical, bm.x_canonical + bm.width_canonical, tbx[0], tbx[2]) > 0.5 * (tbx[2] - tbx[0])
                    and overlap1(bm.y_canonical, bm.y_canonical + bm.height_canonical, tbx[1], tbx[3]) > 0)
        row["cv_stroke_base"] = any(hit(bm) for bm in beams0)
        row["cv_stroke_if_fused_stems_anchor"] = any(hit(bm) for bm in beams1)
        # (a) does a staff line pass through the beam's own band? (the truth box IS the band)
        band = next((bd for bd in bands if bd.rect[0] <= cx <= bd.rect[2] and abs((bd.lines[0] + bd.lines[-1]) / 2 - cy)
                     < 6 * bd.space), None)
        on = None
        if band:
            on = sum(1 for ly in band.lines if b.rect[1] - 2 <= ly <= b.rect[3] + 2)
        row["lines_through_the_beam"] = on
        strokes = [r for r in tb_rows if r["is_beam"] and r["cov"].get("beam") and r["cov"]["beam"][2] == b.id
                   and r.get("ratio") is not None]
        row["stroke_ratios"] = sorted(round(r["ratio"], 2) for r in strokes)
        # (b) the heads under it
        hs = []
        for h, d in under.get(b.id, []):
            k = head_key[h.idx]
            v = run.standing(k, Q.HEAD_STEM, "ADJUDICATE")
            st = "none" if v is None else (v["outcome"] + (":" + str(v.get("reason")) if v["outcome"] != "decided" else ""))
            hb = to_canon(c, *h.rect)
            saw = []
            for vr in cand:
                if overlap1(vr.x, vr.x + vr.w, hb[0] - 0.4 * sp, hb[2] + 0.4 * sp) > 0 and vr.h >= 2.0 * sp \
                        and vr.y <= hb[3] + 0.5 * sp and vr.y + vr.h >= hb[1] - 0.5 * sp:
                    saw.append(vr.outcome)
            if not saw:
                kind = "nothing"
            elif "accepted" in saw:
                kind = "accepted stem"
            elif any("WIDE" in s_ for s_ in saw):
                kind = "run refused too WIDE (fused with the heads' stack)"
            else:
                kind = "refused: " + "/".join(sorted(set(saw)))
            hs.append({"head": k, "head_stem": st, "stem_finder_saw": kind})
            tally[("head_stem_decided" if st == "decided" else "head_stem_not_decided")] += 1
            seen_by[(("decided" if st == "decided" else "NOT decided"), kind)] += 1
        row["heads"] = hs
        rows.append(row)

    real = [r for r in rows if r["truth_beam"] != "q883"]          # q883: Sean's slip, a staff line (print crop)
    print(f"truth beams in the 89 fully labeled cells: {len(rows)}; excluding the truth slip q883: {len(real)}\n")
    print("== (a) THICKNESS: does a beam that LIES ON a staff line measure thin? ==")
    for lab, sel in (("a staff line passes through the beam", [r for r in real if r.get("lines_through_the_beam")]),
                     ("clear of every line", [r for r in real if r.get("lines_through_the_beam") == 0])):
        best = [max(r["stroke_ratios"]) for r in sel if r["stroke_ratios"]]
        under175 = [r["truth_beam"] for r in sel if r["stroke_ratios"] and max(r["stroke_ratios"]) < 1.75]
        nostroke = [r["truth_beam"] for r in sel if not r["stroke_ratios"]]
        if best:
            sb = sorted(best)
            print(f"   {lab:40s} n={len(sel):2d}  best stroke per beam: min {sb[0]:.2f} median {sb[len(sb)//2]:.2f} max {sb[-1]:.2f}; "
                  f"beams whose BEST stroke is under 1.75: {under175}; beams with no stroke at all: {nostroke}")
    print("\n== (b) STEMS: every head under a truth beam ==")
    allh = [(r["truth_beam"], h) for r in real for h in r.get("heads", [])]
    dec = sum(1 for _b, h in allh if h["head_stem"] == "decided")
    print(f"   heads under the {len(real)} real truth beams: {len(allh)}; with a DECIDED stem: {dec}; not: {len(allh) - dec}")
    for (d, kind), n in sorted(seen_by.items(), key=lambda t: -t[1]):
        print(f"      stem {d:11s} | the CV stem finder saw: {kind}: {n}")
    print("\n== per truth beam ==")
    for r in real:
        hs = r.get("heads", [])
        nd = sum(1 for h in hs if h["head_stem"] == "decided")
        print(f"   {r['truth_beam']:8s} heads {len(hs):2d} decided stem {nd:2d} | CV stroke today: "
              f"{'yes' if r.get('cv_stroke_base') else 'NO ':3s} | CV stroke if the fused columns anchored: "
              f"{'yes' if r.get('cv_stroke_if_fused_stems_anchor') else 'NO '} | lines through {r.get('lines_through_the_beam')} | "
              f"stroke ratios {r.get('stroke_ratios')}")
    base_n = sum(1 for r in real if r.get("cv_stroke_base"))
    cf_n = sum(1 for r in real if r.get("cv_stroke_if_fused_stems_anchor"))
    print(f"\n== (b') COUNTERFACTUAL: truth beams with a CV stroke over them: today {base_n}/{len(real)}; "
          f"if the 'too WIDE' fused columns of anchor height anchored: {cf_n}/{len(real)} ==")
    # strokes the counterfactual adds where Sean's truth has no beam (fully labeled cells only)
    added, extra_nonbeam = 0, []
    for c in cells:
        key = id(c)
        if key not in percell:
            continue
        sp, cand, stems, beams0, beams1, fused = percell[key]
        if beams1 is beams0:
            continue
        b0 = {(bm.x_canonical, bm.y_canonical, bm.width_canonical, bm.height_canonical) for bm in beams0}
        for bm in beams1:
            if (bm.x_canonical, bm.y_canonical, bm.width_canonical, bm.height_canonical) in b0:
                continue
            added += 1
            px = (c.bbox_page_px[0] + bm.x_canonical / c.upscale_factor, c.bbox_page_px[1] + bm.y_canonical / c.upscale_factor,
                  c.bbox_page_px[0] + (bm.x_canonical + bm.width_canonical) / c.upscale_factor,
                  c.bbox_page_px[1] + (bm.y_canonical + bm.height_canonical) / c.upscale_factor)
            if any(min(px[2], b.rect[2]) - max(px[0], b.rect[0]) > 0 and min(px[3], b.rect[3]) - max(px[1], b.rect[1]) > 0
                   for b in T.beams):
                continue
            if in_full_cell(T.full, [(px[0] + px[2]) / 2, (px[1] + px[3]) / 2] * 2) is not None:
                extra_nonbeam.append([round(v) for v in px])
    print(f"   cells re-run with fused anchors: {sum(1 for v in percell.values() if v[4] is not v[3])} of {len(percell)} read; "
          f"CV strokes added: {added}; of them standing where Sean's truth has NO beam, inside his fully labeled cells: "
          f"{len(extra_nonbeam)} {extra_nonbeam[:8]}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
