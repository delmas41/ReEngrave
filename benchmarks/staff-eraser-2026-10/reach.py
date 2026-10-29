"""ROADMAP 2.206 (read-only, NO gather): what the staff-line eraser takes that is not the line, and what it leaves that is.

usage: reach.py PLATE BOXES.json OUT.json [PAGE ...]

For every cell of the frozen-sample pages (`pipeline.prepare_pages`, the same cells a gather cuts) and every staff line, the eraser's own
per-column reading is recomputed (`staff_line_removal._vertical_runs_through`, its thickness, its crossing cut) and the line's LOCAL path is
modelled independently of the erase: per column, the centre and height of the run in "pure line" columns (run <= 1.5 x the line's median
thickness and not saturated), running-median over +-0.5 sp, interpolated across the columns a symbol covers. The line's band is that
centre +- (local height / 2 + BAND_PAD_PX).

  OVERCUT  = ink the eraser set to paper that lies OUTSIDE the line's band (ink a mark should keep), within 0.5 sp of the line. Counted
             in a column only when that column's overcut is >= MIN_OVERCUT_SP tall (below that it is the line's own ragged edge).
  RESIDUE  = line-band ink the eraser kept in a column whose run is taller than the cut but reaches <= RESIDUE_EXTRA_SP beyond the band
             (nothing crosses there: the line is locally thicker than the cut, and stays).

Every overcut / residue pixel is attributed to every detector box (from an existing gathered record; the detector reads the unerased cell)
that contains it; the rest is `unboxed`. The same is done for the candidate fixes (`VARIANTS`), each recomputed from the cell's binary;
the `main` variant is asserted byte-equal to the cell's real `image_no_staff`.
"""
import json
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr import staff_line_removal as SLR  # noqa: E402
from tools.omr.staged import gather as G, pipeline  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
PAGES = {"litolff": [2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}

BAND_PAD_PX = 2.0
MIN_OVERCUT_SP = 0.05
RESIDUE_EXTRA_SP = 0.08
PURE_FACTOR = 1.5
WIN_SP = 0.5
CHUNK_H_SP = 0.08
CHUNK_AREA_SP2 = 0.01


def line_model(heights, tops, bottoms, present, sat, t, w, sp):
    """Per column (centre, half-height) of the line from pure-line columns, running median, interpolated."""
    pure = present & ~sat & (heights <= PURE_FACTOR * t)
    xs = np.nonzero(pure)[0]
    if xs.size < 3:
        return None
    cen = (tops[xs] + bottoms[xs]) / 2.0
    hh = heights[xs] / 2.0
    half = max(2, int(WIN_SP * sp))
    cs, hs = np.empty(xs.size), np.empty(xs.size)
    lo = np.searchsorted(xs, xs - half)
    hi = np.searchsorted(xs, xs + half, side="right")
    for i in range(xs.size):
        cs[i] = np.median(cen[lo[i]:hi[i]])
        hs[i] = np.median(hh[lo[i]:hi[i]])
    allx = np.arange(w)
    return np.interp(allx, xs, cs), np.interp(allx, xs, hs)


def runs(ink, y, walk, search):
    """The eraser's walk with `max_search=walk` (main passes cap), plus a per-column flag: the walk stopped at its bound."""
    h_, t_, b_, p_ = SLR._vertical_runs_through(ink, y, walk, radius=search)
    R = int(max(2, walk + 2))
    a, _ = SLR._anchor_rows(ink, y, search)
    sat = p_ & (((a - t_) >= R) | ((b_ - a) >= R))
    return h_, t_, b_, p_, sat


def erase_variant(binary, line_ys, variant):
    """Re-implementation of `remove_staff_lines_from_cell` with switches; 'main' reproduces it exactly (asserted by the caller).

    reach : the walk goes at least ceil(cut)+1 rows each side, so a run whose one side alone reaches the cut is too tall (kept).
    band  : reach, and a run under the cut but taller than the line's own local height loses only the line's band rows.
    """
    h, w = binary.shape
    ink = binary == 0
    spacing = (line_ys[-1] - line_ys[0]) / 4.0 if len(line_ys) >= 2 else 0.0
    cap = max(1, int(round(SLR.MAX_LINE_THICKNESS_SPACES * spacing))) if spacing > 0 else h
    to_erase = np.zeros((h, w), dtype=bool)
    diag = []
    rows = np.arange(h)[:, None]
    for y in line_ys:
        y = int(round(y))
        if not (0 <= y < h):
            continue
        search = int(round(SLR.LINE_SEARCH_RADIUS_SPACES * spacing)) if spacing > 0 else 0
        heights, tops, bottoms, present, sat = runs(ink, y, cap, search)
        if not present.any():
            continue
        t = SLR._line_thickness(heights[present], cap)
        cut = t * SLR.LINE_CROSSING_FACTOR
        if spacing > 0:
            cut = min(cut, SLR.MAX_ERASABLE_RUN_SPACES * spacing)
        cut = max(cut, t + 1.0)
        sat_main = sat.copy()
        if variant in ("reach", "band"):
            walk = max(cap, int(np.ceil(cut)) + 1)
            if walk > cap:
                heights, tops, bottoms, present, sat = runs(ink, y, walk, search)
        erase_cols = present & (heights <= cut)
        model = line_model(heights, tops, bottoms, present, sat, t, w, spacing or 100.0)
        if variant == "band" and model is not None:
            cen, hh = model
            lo_b = np.floor(cen - hh - BAND_PAD_PX).astype(int)
            hi_b = np.ceil(cen + hh + BAND_PAD_PX).astype(int)
            pure = heights <= (2 * hh + 2 * BAND_PAD_PX)
            t_eff = np.where(pure, tops, np.maximum(tops, lo_b))
            b_eff = np.where(pure, bottoms, np.minimum(bottoms, hi_b))
            band = (rows >= t_eff[None, :]) & (rows <= b_eff[None, :]) & erase_cols[None, :]
        else:
            band = (rows >= tops[None, :]) & (rows <= bottoms[None, :]) & erase_cols[None, :]
        to_erase |= band
        diag.append(dict(y=y, t=t, cut=cut, cap=cap, heights=heights, tops=tops, bottoms=bottoms, present=present, sat=sat,
                         sat_main=sat_main, erase_cols=erase_cols, model=model))
    out = binary.copy()
    out[to_erase] = 255
    return out, diag, spacing


def measure(binary, erased, diag, spacing, boxes, model_from=None):
    """Overcut / residue pixels per line, attributed to boxes. `model_from` = the main diag, so every variant is judged by ONE line model."""
    h, w = binary.shape
    ink = binary == 0
    took = ink & (erased != 0)
    sp = spacing or 100.0
    over_mask = np.zeros((h, w), dtype=bool)
    resid_mask = np.zeros((h, w), dtype=bool)
    sat_mask = np.zeros((h, w), dtype=bool)
    rows = np.arange(h)[:, None]
    lines = []
    for i, d in enumerate(diag):
        m = (model_from[i]["model"] if model_from is not None else d["model"])
        if m is None:
            continue
        cen, hh = m
        lo_b = cen - hh - BAND_PAD_PX
        hi_b = cen + hh + BAND_PAD_PX
        near = (rows >= (cen - 0.5 * sp)[None, :]) & (rows <= (cen + 0.5 * sp)[None, :])
        outside = (rows < lo_b[None, :]) | (rows > hi_b[None, :])
        oc = took & near & outside
        col_h = oc.sum(axis=0)
        oc &= (col_h >= MIN_OVERCUT_SP * sp)[None, :]
        over_mask |= oc
        sat_mask[:, d["sat_main"] & d["erase_cols"]] |= near[:, d["sat_main"] & d["erase_cols"]]
        kept = d["present"] & ~d["erase_cols"]
        extra = np.maximum(lo_b - d["tops"], 0) + np.maximum(d["bottoms"] - hi_b, 0)
        res_cols = kept & (extra <= RESIDUE_EXTRA_SP * sp)
        inband = (rows >= lo_b[None, :]) & (rows <= hi_b[None, :])
        resid_mask |= ink & (erased == 0) & inband & res_cols[None, :]
        lines.append(dict(t_sp=round(d["t"] / sp, 3), cut_sp=round(d["cut"] / sp, 3), cap=d["cap"],
                          n_sat_erased=int((d["sat_main"] & d["erase_cols"]).sum()), n_cols=int(d["present"].sum())))
    # CHUNKS: an overcut is a mark's ink only when it is a real piece -- >= CHUNK_H_SP tall and >= CHUNK_AREA_SP2 in area. The rest is the
    # line's own fillet where it meets a stem / barline, or a ragged edge (crop look on Litolff p16: those are 1-6 px dashes).
    n, lab, stats, _ = cv2.connectedComponentsWithStats(over_mask.astype(np.uint8), connectivity=8)
    keep = np.zeros(n, dtype=bool)
    for j in range(1, n):
        keep[j] = stats[j, cv2.CC_STAT_HEIGHT] >= CHUNK_H_SP * sp and stats[j, cv2.CC_STAT_AREA] >= CHUNK_AREA_SP2 * sp * sp
    over_mask = keep[lab]
    per_box = []
    covered = np.zeros((h, w), dtype=bool)
    for b in boxes:
        cls, x, y, bw, bh = b[0], int(b[1]), int(b[2]), int(np.ceil(b[3])), int(np.ceil(b[4]))
        x0, y0, x1, y1 = max(0, x), max(0, y), min(w, x + bw), min(h, y + bh)
        if x1 <= x0 or y1 <= y0:
            per_box.append(None)
            continue
        if cls != "staff":
            covered[y0:y1, x0:x1] = True
        oc = over_mask[y0:y1, x0:x1]
        rs = resid_mask[y0:y1, x0:x1]
        colmax = int(oc.sum(axis=0).max()) if oc.size else 0
        satc = int(sat_mask[y0:y1, x0:x1].any(axis=0).sum())
        per_box.append(dict(cls=cls, box=[x0, y0, x1 - x0, y1 - y0], over_px=int(oc.sum()), over_colmax_sp=round(colmax / sp, 3), sat_cols=satc,
                            over_cols=int((oc.sum(axis=0) > 0).sum()), resid_px=int(rs.sum()), own_px=int(ink[y0:y1, x0:x1].sum())))
    return dict(boxes=per_box, unboxed_over=int((over_mask & ~covered).sum()), unboxed_resid=int((resid_mask & ~covered).sum()),
                over=int(over_mask.sum()), resid=int(resid_mask.sum()), erased_px=int(took.sum())), lines


VARIANTS = ("main", "reach", "band")


def main():
    plate, boxes_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    pages = [int(a) for a in sys.argv[4:]] or PAGES[plate]
    allboxes = json.load(open(boxes_path))
    res = dict(plate=plate, cells={})
    for pg in pages:
        pws, cells = pipeline.prepare_pages(PDF[plate], [pg], dpi=600)[0]
        loc = G.gather_geometry(G.Log(), pws)
        for c in cells:
            key = loc.get(c.staff_index)
            if key is None or getattr(c, "binary", None) is None:
                continue
            ck = "%d/%s/%s/%s" % (pg, key[0], key[1], c.measure_index)
            line_ys = list(c.staff_line_ys_canonical or [])
            if len(line_ys) < 2:
                continue
            boxes = allboxes.get(ck, [])
            row = {}
            main_diag = None
            for v in VARIANTS:
                er, diag, spacing = erase_variant(c.binary, line_ys, v)
                if v == "main":
                    assert np.array_equal(er, c.image_no_staff), ck   # the re-implementation IS the eraser
                    main_diag = diag
                m, lines = measure(c.binary, er, diag, spacing, boxes, model_from=main_diag)
                row[v] = m
                if v == "main":
                    row["lines"] = lines
                    row["sp"] = spacing
            res["cells"][ck] = row
        print(plate, pg, len(res["cells"]), time.strftime("%H:%M:%S"), flush=True)
        json.dump(res, open(out, "w"))


if __name__ == "__main__":
    main()
