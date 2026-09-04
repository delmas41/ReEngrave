"""Probe: does snap_to_staff suggest the wrong variant on ledger notes?

Sean reported that the single-symbol click-to-box snap sometimes suggests
on-line for a note that is in-space — on LEDGER LINES only, never inside the
staff. The suspected mechanism: inside the staff the parity grid anchors on
the cell's own MEASURED line positions, but beyond the staff `snap_to_staff`
extrapolates at the median staff spacing — and ledger lines are engraved at
their own pitch, so the error accumulates with distance and eventually flips
the half-space parity.

Ground truth is free: the hollow-campaign verdicts hold Sean's final class
for every added notehead. Two layers:

  1. ARITHMETIC — re-run the exact server snap on each labeled notehead's
     box centre and compare the suggested variant to the labeled class,
     bucketed by distance from the staff edge. NOTE the asymmetry in what a
     disagreement means: click-placed boxes (hollow2/3) were re-centred onto
     the snapped grid point and their class DEFAULTED to the suggestion, so
     a stored class that disagrees is a case where Sean explicitly pressed
     `c` to override — a lower bound on the wrong-suggestion rate, since a
     miss he didn't notice leaves no trace.

  2. INK — for each out-of-staff labeled notehead, read the actual ledger
     rung positions out of the cell image (a rung is a thin band of long
     horizontal ink runs crossing the note's x) and measure the real rung
     pitch against the staff spacing the extrapolation assumes.

Run from the repo root:

    python3 benchmarks/omr-snap-ledger-2026-09/probe_snap_ledger.py \
        --out benchmarks/omr-snap-ledger-2026-09/probe_results.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.annotate.server import _staff_spacing, snap_to_staff  # noqa: E402

BATCHES = [
    "benchmarks/omr-labeling-hollow-2026-08",
    "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1",
    "benchmarks/omr-labeling-hollow2-2026-09-eulenburg-scheherazade",
    "benchmarks/omr-labeling-hollow2-2026-09-litolff-hires",
    "benchmarks/omr-labeling-hollow2-2026-09-peters-mahler5",
    "benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9",
    "benchmarks/omr-labeling-hollow3-2026-09-durand-lamer",
    "benchmarks/omr-labeling-hollow3-2026-09-jurgenson-tchaikovsky1",
    "benchmarks/omr-labeling-hollow3-2026-09-novello-elgar1",
    "benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1",
]


def _main_checkout() -> Path | None:
    """Resolve the MAIN checkout from a worktree (cell PNGs are gitignored
    and live only where labeling ran)."""
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
        p = (REPO / common).resolve() if not Path(common).is_absolute() else Path(common)
        root = p.parent
        return root if (root / "tools").is_dir() else None
    except Exception:
        return None


def _image_candidates(cell_id: str, png_rel: str) -> list[Path]:
    cands = [REPO / png_rel]
    main = _main_checkout()
    if main is not None:
        cands.append(main / png_rel)
    for vdir in sorted((REPO / "data/user-labeled").glob("v*/images")):
        cands.append(vdir / f"{cell_id}.png")
    return cands


def find_cell_image(cell_id: str, png_rel: str) -> Path | None:
    for c in _image_candidates(cell_id, png_rel):
        if c.exists():
            return c
    return None


def truth_parity(class_name: str) -> str | None:
    if not class_name.startswith("notehead"):
        return None
    if class_name.endswith("OnLine"):
        return "on_line"
    if class_name.endswith("InSpace"):
        return "in_space"
    return None


def zone_of(d_out_spaces: float) -> str:
    """Bucket by distance beyond the nearer edge line, in staff spaces.

    0.0 = on the edge line. 0.5 = the space just beyond. 1.0 = 1st ledger.
    """
    if d_out_spaces <= 0.25:
        return "inside"
    if d_out_spaces <= 1.25:
        return "1st ledger zone"
    if d_out_spaces <= 2.25:
        return "2nd ledger zone"
    return "3rd+ ledger zone"


def collect_rows(batch_dirs: list[str]) -> list[dict]:
    rows = []
    for bdir in batch_dirs:
        broot = REPO / bdir
        manifest = {e["cell_id"]: e for e in json.loads((broot / "cells.json").read_text())}
        vdir = broot / "verdicts-merged"
        if not vdir.is_dir():
            vdir = broot / "verdicts"
        for vf in sorted(vdir.glob("*.verdict.json")):
            v = json.loads(vf.read_text())
            entry = manifest.get(v.get("cell_id"))
            if entry is None:
                continue
            ys = entry.get("staff_line_ys_canonical") or []
            spacing = _staff_spacing(ys)
            if spacing is None:
                continue
            top, bottom = min(ys), max(ys)

            def emit(source: str, cls: str, bbox: dict) -> None:
                parity = truth_parity(cls)
                if parity is None or not bbox:
                    return
                cx = bbox["x"] + bbox["w"] / 2.0
                cy = bbox["y"] + bbox["h"] / 2.0
                snapped = snap_to_staff(ys, cy)
                if snapped is None:
                    return
                if cy < top:
                    d_out = (top - cy) / spacing
                    direction = "above"
                elif cy > bottom:
                    d_out = (cy - bottom) / spacing
                    direction = "below"
                else:
                    d_out = 0.0
                    direction = "inside"
                cell_h = entry.get("cell_canonical_h")
                clamped = bbox["y"] <= 0 or (
                    cell_h is not None and bbox["y"] + bbox["h"] >= cell_h
                )
                rows.append({
                    "batch": bdir,
                    "cell_id": v["cell_id"],
                    "source": source,
                    "class": cls,
                    "truth": parity,
                    "suggested": snapped["position"],
                    "agree": snapped["position"] == parity,
                    "step": snapped["step"],
                    "cx": cx,
                    "cy": cy,
                    "dy_to_grid": cy - snapped["snapped_y"],
                    "spacing": spacing,
                    "d_out_spaces": round(d_out, 3),
                    "direction": direction,
                    "zone": zone_of(d_out),
                    "bbox_clamped": clamped,
                    "png_rel": entry.get("cell_png_path", ""),
                })

            for a in v.get("added_detections", []):
                emit("added", a.get("human_class", ""), a.get("bbox") or {})
            for det in v.get("detections", []):
                verdict = det.get("verdict")
                if verdict == "TP":
                    cls = det.get("model_predicted_class", "")
                elif verdict == "WRONG_CATEGORY":
                    cls = det.get("human_corrected_class") or ""
                else:
                    continue
                emit("model", cls, det.get("human_bbox") or det.get("model_bbox") or {})
    return rows


def report_arithmetic(rows: list[dict]) -> dict:
    print("=" * 72)
    print("LAYER 1 — snap suggestion vs Sean's final class")
    print("=" * 72)
    zones = ["inside", "1st ledger zone", "2nd ledger zone", "3rd+ ledger zone"]
    pooled = {}
    for zone in zones:
        zrows = [r for r in rows if r["zone"] == zone]
        n = len(zrows)
        bad = [r for r in zrows if not r["agree"]]
        rate = (len(bad) / n) if n else 0.0
        pooled[zone] = {"n": n, "disagree": len(bad), "rate": round(rate, 4)}
        print(f"{zone:18s}  n={n:4d}  disagree={len(bad):3d}  rate={rate:6.1%}")
    print()
    print("Disagreements (each one is Sean explicitly overriding the suggestion):")
    for r in rows:
        if r["agree"]:
            continue
        print(
            f"  {r['batch'].split('/')[-1]:44s} {r['cell_id']:28s} "
            f"{r['class']:24s} d_out={r['d_out_spaces']:5.2f}sp "
            f"{r['direction']:6s} suggested={r['suggested']:8s} "
            f"clamped={r['bbox_clamped']}"
        )
    print()
    # Sanity: click-placed centres should sit ON the grid (|dy| <= 1px after
    # int rounding) unless the box was clamped at the cell edge or hand-moved.
    free = [r for r in rows if abs(r["dy_to_grid"]) > 1.5 and not r["bbox_clamped"]]
    print(f"Rows with centres OFF the current grid (hand-drawn/moved): {len(free)}")
    return pooled


# ---------------------------------------------------------------------------
# Layer 2 — measure the real ledger rung positions from the ink
# ---------------------------------------------------------------------------


def rung_bands(
    img_gray, cx: float, y_from: float, y_to: float, spacing: float
) -> list[tuple[float, float]]:
    """Thin bands of long horizontal ink runs crossing x=cx, between y_from
    and y_to (exclusive of the staff body). Returns (band_center_y, run_len).
    """
    import numpy as np

    h, w = img_gray.shape[:2]
    x0 = max(0, int(cx - 1.1 * spacing))
    x1 = min(w, int(cx + 1.1 * spacing))
    yy0, yy1 = int(max(0, min(y_from, y_to))), int(min(h, max(y_from, y_to)))
    if x1 - x0 < spacing or yy1 - yy0 < 2:
        return []
    window = img_gray[yy0:yy1, x0:x1]
    # Otsu on the window's own histogram — scans vary too much for a fixed
    # threshold.
    import cv2

    _, ink = cv2.threshold(window, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = ink > 0
    cx_local = cx - x0
    need_cross = (int(cx_local - 0.1 * spacing), int(cx_local + 0.1 * spacing))
    row_run = []
    for yi in range(ink.shape[0]):
        row = ink[yi]
        # longest run containing the centre columns
        run_len = 0
        j = 0
        n = row.shape[0]
        best = 0
        while j < n:
            if row[j]:
                k = j
                while k < n and row[k]:
                    k += 1
                if k > need_cross[0] and j < need_cross[1]:
                    best = max(best, k - j)
                j = k
            else:
                j += 1
        row_run.append(best)
    min_len = 1.30 * spacing
    bands: list[tuple[float, float]] = []
    yi = 0
    n = len(row_run)
    while yi < n:
        if row_run[yi] >= min_len:
            j = yi
            while j < n and row_run[j] >= min_len:
                j += 1
            thickness = j - yi
            if thickness <= 0.40 * spacing:
                ys_band = list(range(yi, j))
                center = sum(ys_band) / len(ys_band) + yy0
                bands.append((center, max(row_run[yi:j])))
            yi = j
        else:
            yi += 1
    return bands


def ladder_from_bands(
    edge_y: float, direction: str, bands: list[tuple[float, float]], spacing: float
) -> list[float]:
    """Walk outward from the staff edge line, one rung per staff space,
    accepting the band nearest each expected position (window 0.65..1.35 of
    the last pitch). Rejects half-pitch fakes (hollow-note cap arcs)."""
    sign = -1.0 if direction == "above" else 1.0
    ladder = [edge_y]
    pitch = spacing
    while True:
        expected = ladder[-1] + sign * pitch
        cands = [
            b for b in bands
            if 0.65 * pitch <= sign * (b[0] - ladder[-1]) <= 1.35 * pitch
        ]
        if not cands:
            break
        best = min(cands, key=lambda b: abs(b[0] - expected))
        ladder.append(best[0])
        pitch = abs(ladder[-1] - ladder[-2])
    return ladder


def report_ink(rows: list[dict]) -> dict:
    try:
        import cv2  # noqa: F401
        import numpy as np  # noqa: F401
    except ImportError:
        print("cv2/numpy unavailable — skipping ink layer")
        return {}
    import cv2

    print("=" * 72)
    print("LAYER 2 — measured ledger rung pitch vs staff spacing")
    print("=" * 72)
    out_rows = [r for r in rows if r["direction"] != "inside" and r["d_out_spaces"] > 0.6]
    gap_records = []  # (batch, k, gap/spacing)
    n_img_missing = 0
    for r in out_rows:
        img_path = find_cell_image(r["cell_id"], r["png_rel"])
        if img_path is None:
            n_img_missing += 1
            continue
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            n_img_missing += 1
            continue
        # staff geometry from the batch manifest (canonical px)
        broot = REPO / r["batch"]
        manifest = {e["cell_id"]: e for e in json.loads((broot / "cells.json").read_text())}
        entry = manifest[r["cell_id"]]
        ys = sorted(entry["staff_line_ys_canonical"])
        if img.shape[1] != entry.get("cell_canonical_w") or img.shape[0] != entry.get(
            "cell_canonical_h"
        ):
            n_img_missing += 1
            continue
        spacing = r["spacing"]
        edge_y = ys[0] if r["direction"] == "above" else ys[-1]
        # search from just outside the edge line to a space past the note
        if r["direction"] == "above":
            y_from = r["cy"] - 1.6 * spacing
            y_to = edge_y - 0.30 * spacing
        else:
            y_from = edge_y + 0.30 * spacing
            y_to = r["cy"] + 1.6 * spacing
        bands = rung_bands(img, r["cx"], y_from, y_to, spacing)
        ladder = ladder_from_bands(edge_y, r["direction"], bands, spacing)
        for k in range(1, len(ladder)):
            gap = abs(ladder[k] - ladder[k - 1]) / spacing
            gap_records.append({
                "batch": r["batch"].split("/")[-1],
                "cell_id": r["cell_id"],
                "k": k,
                "gap_over_spacing": round(gap, 4),
            })
    print(f"out-of-staff labeled notes: {len(out_rows)}, images missing/mismatched: {n_img_missing}")
    if not gap_records:
        print("no rungs measured")
        return {}

    def stats(vals: list[float]) -> str:
        vals = sorted(vals)
        n = len(vals)
        med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        return f"n={n:4d} median={med:.3f} p10={vals[int(0.1 * n)]:.3f} p90={vals[min(n - 1, int(0.9 * n))]:.3f}"

    print("\nrung gap / staff spacing, by rung index (k=1 is edge line -> 1st ledger):")
    by_k: dict[int, list[float]] = {}
    for g in gap_records:
        by_k.setdefault(g["k"], []).append(g["gap_over_spacing"])
    for k in sorted(by_k):
        print(f"  k={k}: {stats(by_k[k])}")
    print("\nby batch (all k pooled):")
    by_b: dict[str, list[float]] = {}
    for g in gap_records:
        by_b.setdefault(g["batch"], []).append(g["gap_over_spacing"])
    for b in sorted(by_b):
        print(f"  {b:44s} {stats(by_b[b])}")
    return {"gap_records": gap_records}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-ink", action="store_true")
    args = ap.parse_args()

    rows = collect_rows(BATCHES)
    print(f"collected {len(rows)} labeled notehead rows "
          f"({sum(1 for r in rows if r['source'] == 'added')} added, "
          f"{sum(1 for r in rows if r['source'] == 'model')} model)\n")
    pooled = report_arithmetic(rows)
    ink = {} if args.no_ink else report_ink(rows)

    if args.out:
        args.out.write_text(json.dumps({
            "pooled_by_zone": pooled,
            "rows": rows,
            "ink": ink,
        }, indent=1))
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
