"""Page-level provenance probe for the inside-staff snap disagreements.

For each flagged (pdf, page, system, staff, measure):
  1. re-run the cutter's exact phase-1 (render 600dpi, detect_staves,
     detect_barlines, extract_measures, PAD=5.0),
  2. check the re-cut cell's staff_line_ys_canonical against the batch
     manifest (does today's code reproduce the stored geometry?),
  3. trace the PRINTED line y at many x across the staff's full width on the
     page binary, report residual (printed - staff.line_ys) per line,
  4. mark the flagged measure's x-range, report line_wander_px.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(MAIN))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr import measure_extractor as _me  # noqa: E402

_me.PAD_ABOVE_STAFF_LINES = 5.0
_me.PAD_BELOW_STAFF_LINES = 5.0

CASES = [
    # (pdf, page0, system, staff, measure, manifest_ys, label: canonical disp seen)
    ("library/editions/dvorak/symphony-9-op95/dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf",
     7, 0, 4, 12, [400, 499, 602, 705, 800], "dvorak9-p8-sys0-s4-m12"),
    ("library/editions/mahler/symphony-1-gmw-11/mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf",
     2, 0, 7, 5, [598, 695, 800, 897, 998], "mahler1-p3-sys0-s7-m5"),
    ("library/editions/mahler/symphony-1-gmw-11/mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf",
     3, 0, 0, 9, [600, 698, 796, 898, 1000], "mahler1-p4-sys0-s0-m9"),
    ("library/editions/mahler/symphony-1-gmw-11/mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf",
     3, 0, 1, 9, [598, 697, 800, 895, 998], "mahler1-p4-sys0-s1-m9"),
    ("library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
     1, 1, 21, 6, [400, 499, 598, 701, 800], "brahms1-p2-sys1-s21-m6"),
    ("library/editions/rimsky-korsakov/scheherazade-op35/rimsky-korsakov--scheherazade-op35--eulenburg--imslp1010338.pdf",
     3, 0, 3, 0, [284, 352, 423, 497, 569], "schehe-p4-sys0-s3-m0"),
    ("library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf",
     47, 0, 14, 0, [557, 651, 748, 839, 930], "beet5hr-p48-sys0-s14-m0"),
]


def bands_at_x(ink: np.ndarray, x: float, spacing: float, y0: int, y1: int):
    h, w = ink.shape
    half = 1.4 * spacing
    xa, xb = int(max(0, x - half)), int(min(w, x + half))
    ya, yb = max(0, y0), min(h, y1)
    if xb - xa < spacing or yb - ya < 4:
        return []
    win = ink[ya:yb, xa:xb]
    frac = win.mean(axis=1)
    out = []
    yi = 0
    n = len(frac)
    while yi < n:
        if frac[yi] >= 0.70:
            j = yi
            while j < n and frac[j] >= 0.70:
                j += 1
            if (j - yi) <= 0.45 * spacing:
                rows = np.arange(yi, j, dtype=float)
                wts = frac[yi:j]
                out.append(float((rows * wts).sum() / wts.sum()) + ya)
            yi = j
        else:
            yi += 1
    return out


def main() -> None:
    results = []
    page_cache = {}
    for pdf_rel, page0, sysi, sti, mi, man_ys, name in CASES:
        key = (pdf_rel, page0)
        if key not in page_cache:
            img = render_page(MAIN / pdf_rel, page0, dpi=600)
            pws = detect_staves(img)
            pws = _me.detect_barlines(pws)
            cells = _me.extract_measures(pws)
            page_cache[key] = (img, pws, cells)
        img, pws, cells = page_cache[key]

        ink = img.binary > 0
        if ink.mean() > 0.5:  # polarity: want ink=True
            ink = ~ink

        cell = next((c for c in cells if c.system_index == sysi
                     and c.staff_index == sti and c.measure_index == mi), None)
        staff = next((s for s in pws.staves if s.staff_index == sti), None)
        rec = {"name": name}
        if staff is None:
            rec["error"] = f"staff {sti} not found (have {[s.staff_index for s in pws.staves]})"
            results.append(rec)
            print(json.dumps(rec))
            continue
        ys = list(staff.line_ys)
        spacing = float(staff.line_spacing_px)
        rec["staff_line_ys"] = ys
        rec["spacing"] = round(spacing, 2)
        rec["wander_px"] = staff.line_wander_px
        rec["thickness"] = staff.line_thickness_px

        if cell is not None:
            rec["recut_canonical_ys"] = list(cell.staff_line_ys_canonical)
            rec["manifest_ys"] = man_ys
            rec["reproduces_manifest"] = list(cell.staff_line_ys_canonical) == man_ys
            rec["cell_bbox_page"] = list(cell.bbox_page_px)
            rec["upscale"] = round(cell.upscale_factor, 4)
        else:
            rec["error_cell"] = (
                "cell not found; cells for staff: "
                + str(sorted((c.system_index, c.measure_index)
                             for c in cells if c.staff_index == sti))[:300])

        # staff x extent from its cells
        xs_cells = [c.bbox_page_px for c in cells if c.staff_index == sti]
        if xs_cells:
            x_lo = min(b[0] for b in xs_cells)
            x_hi = max(b[2] for b in xs_cells)
        else:
            x_lo, x_hi = 0, ink.shape[1]
        y_top, y_bot = min(ys), max(ys)
        pad = int(0.7 * spacing)

        xs = np.linspace(x_lo + spacing, x_hi - spacing, 21)
        prof = []
        for x in xs:
            bb = bands_at_x(ink, float(x), spacing, y_top - pad, y_bot + pad)
            resid = []
            for sy in ys:
                cands = [b for b in bb if abs(b - sy) <= 0.55 * spacing]
                resid.append(round(min(cands, key=lambda b: abs(b - sy)) - sy, 1)
                             if cands else None)
            prof.append({"x": int(x), "resid": resid})
        rec["profile"] = prof
        results.append(rec)

        print("=" * 90)
        print(name, f"| spacing={spacing:.1f} wander={staff.line_wander_px}"
              f" | line_ys={ys}")
        if cell is not None:
            print(f"  recut canonical ys {list(cell.staff_line_ys_canonical)}"
                  f"  manifest {man_ys}  match={rec['reproduces_manifest']}"
                  f"  bbox_x=[{cell.bbox_page_px[0]},{cell.bbox_page_px[2]}]"
                  f" upscale={cell.upscale_factor:.3f}")
        else:
            print(" ", rec.get("error_cell"))
        print("  residual (printed - line_ys) per line across the staff width:")
        for p in prof:
            mark = ""
            if cell is not None and cell.bbox_page_px[0] <= p["x"] < cell.bbox_page_px[2]:
                mark = "  <-- flagged measure"
            ds = ["  .  " if d is None else f"{d:+5.1f}" for d in p["resid"]]
            print(f"    x={p['x']:6d}  " + " ".join(ds) + mark)

    out = Path(__file__).parent / "page_probe_results.json"
    out.write_text(json.dumps(results, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
