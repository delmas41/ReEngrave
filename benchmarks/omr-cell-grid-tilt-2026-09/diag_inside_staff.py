"""Diagnose the 9 inside-staff snap disagreements: are the stored
staff_line_ys_canonical wrong at the labeled note's x?

For each flagged cell:
  - measure the PRINTED line positions at a grid of x samples (thin bands of
    near-fully-inked rows in a 2.8-spacing-wide column window, matched to the
    nearest stored line within 0.55 spacing),
  - report displacement (measured - stored) per line per x,
  - at each label point, rebuild the half-step grid from the measured lines at
    that x and ask what parity the TRUE geometry gives,
  - render a full-cell overlay + a zoom crop per label.

Outputs to OUTDIR (argv[1]).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
SHAMIR = MAIN / ".claude/worktrees/peaceful-shamir-d12e52"
V8 = MAIN / "data/user-labeled/v8-2026-09-02-hollow2-5pub/images"

# (batch_rel, cell_id, [(cx, cy, class, suggested)])
CASES = [
    ("benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1",
     "brahms1-p2-sys1-s21-m6",
     [(254.0, 750.5, "noteheadHalfOnLine", "in_space")]),
    ("benchmarks/omr-labeling-hollow2-2026-09-eulenburg-scheherazade",
     "schehe-p4-sys0-s3-m0",
     [(1046.0, 533.0, "noteheadWholeOnLine", "in_space")]),
    ("benchmarks/omr-labeling-hollow2-2026-09-litolff-hires",
     "beet5hr-p48-sys0-s14-m0",
     [(865.0, 930.0, "noteheadWholeInSpace", "on_line")]),
    ("benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9",
     "dvorak9-p8-sys0-s4-m12",
     [(288.0, 449.5, "noteheadHalfOnLine", "in_space"),
      (286.0, 550.5, "noteheadHalfOnLine", "in_space")]),
    ("benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1",
     "mahler1-p3-sys0-s7-m5",
     [(641.0, 695.5, "noteheadHalfInSpace", "on_line")]),
    ("benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1",
     "mahler1-p4-sys0-s0-m9",
     [(264.5, 747.0, "noteheadHalfOnLine", "in_space")]),
    ("benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1",
     "mahler1-p4-sys0-s1-m9",
     [(264.0, 647.5, "noteheadHalfOnLine", "in_space"),
      (285.0, 748.5, "noteheadHalfOnLine", "in_space")]),
]


def load_manifest(batch_rel: str) -> dict:
    for root in (MAIN, SHAMIR):
        p = root / batch_rel / "cells.json"
        if p.exists():
            return {e["cell_id"]: e for e in json.loads(p.read_text())}
    raise FileNotFoundError(batch_rel)


def find_image(batch_rel: str, cell_id: str) -> Path | None:
    for c in (MAIN / batch_rel / "cells" / f"{cell_id}.png",
              V8 / f"{cell_id}.png",
              SHAMIR / batch_rel / "cells" / f"{cell_id}.png"):
        if c.exists():
            return c
    return None


def measure_bands_at_x(ink: np.ndarray, x: float, spacing: float) -> list[tuple[float, float, float]]:
    """Thin near-fully-inked row bands in a 2.8-spacing window around x.
    Returns (band_center_y, thickness, ink_frac)."""
    h, w = ink.shape
    half = 1.4 * spacing
    x0, x1 = int(max(0, x - half)), int(min(w, x + half))
    if x1 - x0 < spacing:
        return []
    win = ink[:, x0:x1]
    frac = win.mean(axis=1)
    bands = []
    yi = 0
    while yi < h:
        if frac[yi] >= 0.70:
            j = yi
            while j < h and frac[j] >= 0.70:
                j += 1
            thick = j - yi
            if thick <= 0.40 * spacing:
                rows = np.arange(yi, j, dtype=float)
                weights = frac[yi:j]
                center = float((rows * weights).sum() / weights.sum())
                bands.append((center, float(thick), float(weights.max())))
            yi = j
        else:
            yi += 1
    return bands


def match_lines(bands, ys_stored, spacing):
    """For each stored line y, nearest band within 0.55 spacing (else None)."""
    out = []
    for sy in ys_stored:
        cands = [b for b in bands if abs(b[0] - sy) <= 0.55 * spacing]
        out.append(min(cands, key=lambda b: abs(b[0] - sy))[0] if cands else None)
    return out


def parity_from_measured(meas_ys, ys_stored, spacing, cy):
    """Half-step grid from measured lines at this x; missing lines filled by
    shifting the stored y by the median measured displacement."""
    disp = [m - s for m, s in zip(meas_ys, ys_stored) if m is not None]
    if not disp:
        return None, None, None
    med_disp = float(np.median(disp))
    grid = [m if m is not None else s + med_disp for m, s in zip(meas_ys, ys_stored)]
    # slots: lines at grid[i] (even step 2i), spaces at midpoints (odd)
    slots = []
    for i, gy in enumerate(grid):
        slots.append((2 * i, gy, "on_line"))
        if i + 1 < len(grid):
            slots.append((2 * i + 1, (gy + grid[i + 1]) / 2.0, "in_space"))
    step, sy, par = min(slots, key=lambda s: abs(s[1] - cy))
    return par, sy, med_disp


def main() -> None:
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    report = []
    for batch_rel, cell_id, labels in CASES:
        man = load_manifest(batch_rel)
        entry = man[cell_id]
        ys = sorted(entry["staff_line_ys_canonical"])
        img_path = find_image(batch_rel, cell_id)
        rec = {"cell": cell_id, "batch": batch_rel.split("/")[-1],
               "stored_ys": ys, "gaps": [ys[i + 1] - ys[i] for i in range(4)]}
        if img_path is None:
            rec["error"] = "no image"
            report.append(rec)
            continue
        gray = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        rec["image"] = str(img_path)
        rec["dims_ok"] = (gray.shape[1] == entry.get("cell_canonical_w")
                          and gray.shape[0] == entry.get("cell_canonical_h"))
        spacing = float(np.median(np.diff(ys)))
        _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        ink = ink > 0
        w = gray.shape[1]
        # x sample grid: 13 columns, staying 1 spacing off the edges
        xs = np.linspace(spacing, w - spacing, 13)
        profile = []  # per x: displacement per line
        for x in xs:
            bands = measure_bands_at_x(ink, float(x), spacing)
            meas = match_lines(bands, ys, spacing)
            profile.append({
                "x": round(float(x), 1),
                "disp": [None if m is None else round(m - s, 1)
                         for m, s in zip(meas, ys)],
            })
        rec["profile"] = profile
        rec["labels"] = []
        for (cx, cy, cls, suggested) in labels:
            bands = measure_bands_at_x(ink, cx, spacing)
            meas = match_lines(bands, ys, spacing)
            par, slot_y, med_disp = parity_from_measured(meas, ys, spacing, cy)
            truth = "on_line" if cls.endswith("OnLine") else "in_space"
            rec["labels"].append({
                "cx": cx, "cy": cy, "class": cls, "old_suggested": suggested,
                "measured_lines_at_cx": [None if m is None else round(m, 1) for m in meas],
                "disp_at_cx": [None if m is None else round(m - s, 1)
                               for m, s in zip(meas, ys)],
                "median_disp_at_cx": None if med_disp is None else round(med_disp, 1),
                "parity_from_measured": par,
                "agrees_with_sean": par == truth if par else None,
            })
        report.append(rec)

        # ---- renders ----
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        for sy in ys:  # stored lines, orange, full width
            cv2.line(img, (0, int(sy)), (w, int(sy)), (0, 140, 255), 3)
        for p in profile:  # measured line points, red dots
            for d, sy in zip(p["disp"], ys):
                if d is not None:
                    cv2.circle(img, (int(p["x"]), int(sy + d)), 7, (0, 0, 255), -1)
        for (cx, cy, cls, _s) in labels:
            cv2.circle(img, (int(cx), int(cy)), 12, (0, 200, 0), 3)
        scale = min(1.0, 1400.0 / w)
        full = cv2.resize(img, (int(w * scale), int(img.shape[0] * scale)))
        cv2.imwrite(str(outdir / f"{cell_id}__full.png"), full)

        for li, (cx, cy, cls, _s) in enumerate(labels):
            x0 = int(max(0, cx - 3.5 * spacing))
            x1 = int(min(w, cx + 3.5 * spacing))
            y0 = int(max(0, ys[0] - 1.5 * spacing))
            y1 = int(min(gray.shape[0], ys[-1] + 1.5 * spacing))
            crop = img[y0:y1, x0:x1].copy()
            cv2.putText(crop, cls.replace("notehead", ""), (6, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 120, 0), 2)
            cv2.imwrite(str(outdir / f"{cell_id}__zoom{li}.png"), crop)

    (outdir / "report.json").write_text(json.dumps(report, indent=1))
    # console summary
    for rec in report:
        print("=" * 78)
        print(rec["cell"], "| stored gaps", rec["gaps"], "| dims_ok", rec.get("dims_ok"))
        if "error" in rec:
            print("  ERROR:", rec["error"])
            continue
        print("  displacement (measured - stored) per line, across x:")
        for p in rec["profile"]:
            ds = ["  .  " if d is None else f"{d:+5.1f}" for d in p["disp"]]
            print(f"    x={p['x']:7.1f}  " + " ".join(ds))
        for lab in rec["labels"]:
            print(f"  LABEL {lab['class']:22s} cx={lab['cx']:.0f} cy={lab['cy']:.0f}"
                  f"  disp_at_cx={lab['disp_at_cx']}"
                  f"  parity(measured)={lab['parity_from_measured']}"
                  f"  agrees_with_sean={lab['agrees_with_sean']}")


if __name__ == "__main__":
    main()
