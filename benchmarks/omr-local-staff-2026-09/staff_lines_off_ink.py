"""How far are the RECORDED staff lines from the printed ink?  (lane-staff-lines-off-ink, 2026-10-06)

STAGED + LEGACY share this (`staff_detector.detect_staves` is the one source).

For every staff the record holds (`Q.STAFF_LINES`, `reader=geometry`), measure
the printed line rows at several x positions on the page image the gather used
(`frame.render_page_matching_gather`), in columns CLEAR of noteheads/barlines:
a column band is clean when, in the staff's own rows plus 1.5 spaces each side,
exactly five horizontal runs are found and their gaps are even (each gap within
25% of the median gap). The line's printed place is the run centre on the
BINARY the detector read, and, as an independent witness, the darkness-weighted
centroid of the same rows on the GRAY page (so a binarisation bias shows up as
the two disagreeing).

offset = printed - recorded, in px (positive = ink BELOW the recorded line);
sp = offset / the staff's own median gap.

    python3 benchmarks/omr-local-staff-2026-09/staff_lines_off_ink.py count DOC [--pages 1,2] --out x.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from frame import render_page_matching_gather  # noqa: E402

RECORDS = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
DOCS = {
    "litolff": RECORDS / "beethoven5-litolff-mvt1-whole-20261006-night-combined.record.json",
    "brahms": RECORDS / "brahms1-breitkopf-mvt1-whole-20261006-night-combined.record.json",
}
N_COLS = 10
BAND = 9           # px of columns averaged per sample
STEP = 6


def recorded_staves(doc: str):
    from tools.omr.staged.record_io import load_record
    rec = load_record(DOCS[doc])
    pdf = rec["provenance"]["settings"]["args"]["pdf"]
    dpi = rec["provenance"]["settings"]["args"]["dpi"]
    out = {}
    for o in rec["record"]["observations"]:
        if o["quantity"] == "staff_lines" and o["subject"].startswith("staff/"):
            _, p, s, k = o["subject"].split("/")
            out[(int(p), int(s), int(k))] = [float(v) for v in o["value"]]
    return pdf, dpi, out


def runs_in(frac: np.ndarray, thr: float):
    """contiguous index runs where frac >= thr -> list of (start, end_inclusive)"""
    m = frac >= thr
    out, i, n = [], 0, len(m)
    while i < n:
        if m[i]:
            j = i
            while j + 1 < n and m[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def sample_column(binary, gray, x, y0, y1, rec_lines, sp):
    """five printed line centres at column x, or None if the column is not clean."""
    h, w = binary.shape
    xa, xb = max(0, x - BAND // 2), min(w, x + BAND // 2 + 1)
    ra = max(0, int(y0 - 1.5 * sp))
    rb = min(h, int(y1 + 1.5 * sp) + 1)
    ink = (binary[ra:rb, xa:xb] == 0).mean(axis=1)
    rs = runs_in(ink, 0.6)
    # a line run is thin: <= 0.45 sp thick (a head or a beam is thicker)
    rs = [r for r in rs if (r[1] - r[0] + 1) <= 0.45 * sp]
    if len(rs) != 5:
        return None
    cen = np.array([(a + b) / 2.0 + ra for a, b in rs])
    gaps = np.diff(cen)
    med = float(np.median(gaps))
    if med < 0.6 * sp or med > 1.4 * sp or np.any(np.abs(gaps - med) > 0.25 * med):
        return None
    # the five found must be the staff's own: nearest recorded line within 1.0 sp
    if np.any(np.abs(cen - np.array(rec_lines)) > 1.0 * sp):
        return None
    # gray centroid of each line's rows (+-1 px) -- independent of binarisation
    g = 255.0 - gray[:, xa:xb].mean(axis=1)
    gcen = []
    for (a, b), c in zip(rs, cen):
        lo, hi = int(a + ra) - 2, int(b + ra) + 3
        w_ = g[lo:hi] - g[lo:hi].min()
        gcen.append(float((w_ * np.arange(lo, hi)).sum() / max(w_.sum(), 1e-9)) + 0.0)
    return cen, np.array(gcen)


def measure_staff(binary, gray, rec_lines, x_start, x_end):
    sp = (rec_lines[-1] - rec_lines[0]) / 4.0
    xs, cens, gcens = [], [], []
    for x in range(int(x_start) + 8, int(x_end) - 8, STEP):
        r = sample_column(binary, gray, x, rec_lines[0], rec_lines[-1], rec_lines, sp)
        if r is not None:
            xs.append(x); cens.append(r[0]); gcens.append(r[1])
    if not xs:
        return None
    # ten evenly spaced among the clean ones (by x rank)
    idx = np.unique(np.linspace(0, len(xs) - 1, min(N_COLS, len(xs))).round().astype(int))
    xs = np.array(xs)[idx]
    cens = np.array(cens)[idx] - np.array(rec_lines)[None, :]
    gcens = np.array(gcens)[idx] - np.array(rec_lines)[None, :]
    return dict(sp=sp, xs=xs.tolist(), off=cens.tolist(), goff=gcens.tolist(),
                n_clean=len(idx))


def classify(m, x_start, x_end):
    off = np.array(m["off"])             # (n, 5)
    xs = np.array(m["xs"], float)
    sp = m["sp"]
    mean_per_x = off.mean(axis=1)
    med = float(np.median(off))
    worst = float(np.abs(off).max())
    # tilt: linear fit of mean offset against x; slope * staff width
    if len(xs) >= 4 and np.ptp(xs) > 4 * sp:
        a, b = np.polyfit(xs, mean_per_x, 1)
        resid = mean_per_x - (a * xs + b)
        tilt_px = a * np.ptp(xs)
        resid_sd = float(resid.std())
    else:
        tilt_px, resid_sd = 0.0, 0.0
    # per-line: spread of the median offsets of the five lines
    per_line = np.median(off, axis=0)
    line_spread = float(per_line.max() - per_line.min())
    # spacing: recorded vs printed gap
    return dict(med_px=med, worst_px=worst, tilt_px=float(tilt_px),
                resid_sd_px=resid_sd, line_spread_px=line_spread,
                per_line_med=per_line.tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", choices=list(DOCS))
    ap.add_argument("--pages", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from tools.omr.staff_detector import detect_staves

    pdf, dpi, rec = recorded_staves(a.doc)
    pages = sorted({p for p, _, _ in rec})
    if a.pages:
        want = {int(v) for v in a.pages.split(",")}
        pages = [p for p in pages if p in want]
    res = []
    for p in pages:
        pi = render_page_matching_gather(pdf, p, dpi=dpi)
        pws = detect_staves(pi)
        # control: detector on this frame reproduces the record's lines
        det = {}
        for st in pws.staves:
            det[(st.system_index, st.staff_index)] = st
        gray = pi.rgb.mean(axis=2) if pi.rgb.ndim == 3 else pi.rgb
        # match record staves to detector staves by line positions
        n_match = 0
        for (pp, s, k), lines in sorted(rec.items()):
            if pp != p:
                continue
            st = next((t for t in pws.staves if [float(v) for v in t.line_ys] == lines), None)
            if st is None:
                res.append(dict(doc=a.doc, page=p, staff=f"{p}/{s}/{k}", lines=lines, error="no detector match"))
                continue
            n_match += 1
            m = measure_staff(pi.binary, gray, lines, st.x_start, st.x_end)
            row = dict(doc=a.doc, page=p, staff=f"{p}/{s}/{k}", lines=lines,
                       x_start=st.x_start, x_end=st.x_end,
                       thickness=st.line_thickness_px, wander=st.line_wander_px,
                       skew=pi.skew_correction_deg)
            if m is None:
                row["error"] = "no clean column"
            else:
                row.update(m)
                row.update(classify(m, st.x_start, st.x_end))
            res.append(row)
        print(f"{a.doc} p{p}: record staves matched {n_match}", flush=True)
    Path(a.out).write_text(json.dumps(res))


if __name__ == "__main__":
    main()
