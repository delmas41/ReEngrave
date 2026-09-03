"""Evaluate candidate snap fixes against Sean's final hollow-campaign classes.

For every labeled notehead (see probe_snap_ledger.collect_rows), snap its box
centre with each candidate and score agreement with the labeled class:

  baseline   — snap_to_staff as shipped (constant-spacing extrapolation)
  ink        — snap_to_staff fed the rungs measure_ledger_rungs reads off the
               cell image at the note's own x (the production fix path)
  const-F    — extrapolation at F x the staff spacing, expressed as synthetic
               rungs (the "measure one corrected constant" candidate)

Interpretation guardrails:
  * Click-placed boxes sit ON the old grid and their class DEFAULTED to the
    old suggestion, so baseline "agreement" on them includes every unnoticed
    miss; a disagreement is Sean pressing `c`. The number that matters is
    the TRANSITIONS: rows a candidate recovers (baseline wrong -> right) vs
    rows it breaks (baseline right -> wrong), and the in-staff rows, which
    must not move at all.
  * The ink candidate is NOT circular: it is judged against Sean's classes,
    which the rung reader never sees.

Run from the repo root:

    python3 benchmarks/omr-snap-ledger-2026-09/eval_fix_on_verdicts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from probe_snap_ledger import BATCHES, collect_rows, find_cell_image  # noqa: E402

from tools.omr.annotate.ledger_grid import measure_ledger_rungs  # noqa: E402
from tools.omr.annotate.server import snap_to_staff  # noqa: E402

ZONES = ["inside", "1st ledger zone", "2nd ledger zone", "3rd+ ledger zone"]


def load_gray(path: Path, cache: dict):
    if path not in cache:
        import numpy as np
        from PIL import Image

        with Image.open(path) as img:
            cache[path] = np.asarray(img.convert("L"), dtype=np.uint8)
    return cache[path]


def refine_center(img, cx: float, cy: float, spacing: float):
    """Estimate the notehead's TRUE centre from its white counter.

    The stored box centre is an artifact of the OLD grid (click-placed boxes
    were re-centred onto the old snapped_y), so judging any candidate at the
    stored centre is biased toward the old grid. A hollow head's counter is
    the one landmark that is independent of both grids: the area-weighted
    centroid of the white components near the stored centre. An on-line
    note's counter is split in two by the ledger through it — the weighted
    union of both halves centres back on the line. Returns (cx, cy) or None
    when no counter-sized white component is found (closed counter, heavy
    bleed), in which case the caller keeps the stored centre.
    """
    import cv2
    import numpy as np

    h, w = img.shape
    r = 0.9 * spacing
    x0, x1 = int(max(0, cx - r)), int(min(w, cx + r))
    y0, y1 = int(max(0, cy - r)), int(min(h, cy + r))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    win = img[y0:y1, x0:x1]
    _, ink = cv2.threshold(win, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    white = (ink == 0).astype(np.uint8)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(white, 4)
    lo_a, hi_a = 0.02 * spacing**2, 0.9 * spacing**2
    # Only the white the note's own centre touches counts — probe the stored
    # centre and four near offsets (an on-line note's centre pixel is ON the
    # ledger's ink; the probes reach the counter halves either side of it).
    labels_hit = set()
    for dy in (0.0, -0.18, 0.18, -0.35, 0.35):
        xi, yi = int(cx - x0), int(cy + dy * spacing - y0)
        if 0 <= xi < win.shape[1] and 0 <= yi < win.shape[0]:
            lab = labels[yi, xi]
            if lab > 0:
                labels_hit.add(int(lab))
    keep = []
    for i in labels_hit:
        x, y, ww, hh, area = stats[i]
        if not (lo_a <= area <= hi_a):
            continue
        if x == 0 or y == 0 or x + ww >= win.shape[1] or y + hh >= win.shape[0]:
            continue  # touches the window border — background, not a counter
        keep.append((x, y, ww, hh))
    if not keep:
        return None
    # Union bbox centre, not area centroid: for a counter split into two
    # lobes by the ledger through it, the union spans both lobes and centres
    # back on the line even when the lobes are unequal.
    uy0 = min(y for _, y, _, _ in keep)
    uy1 = max(y + hh for _, y, _, hh in keep)
    ux0 = min(x for x, _, _, _ in keep)
    ux1 = max(x + ww for x, _, ww, _ in keep)
    if uy1 - uy0 > 1.2 * spacing or ux1 - ux0 > 1.4 * spacing:
        return None  # not counter-shaped
    rx = (ux0 + ux1) / 2.0 + x0
    ry = (uy0 + uy1) / 2.0 + y0
    if abs(ry - cy) > 0.6 * spacing:
        return None
    return rx, ry


def synthetic_rungs(ys: list[float], factor: float) -> dict[str, list[float]]:
    top, bottom = min(ys), max(ys)
    gaps = sorted(ys[i + 1] - ys[i] for i in range(len(ys) - 1))
    mid = len(gaps) // 2
    spacing = gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2.0
    return {
        "above": [top - k * spacing * factor for k in range(1, 7)],
        "below": [bottom + k * spacing * factor for k in range(1, 7)],
    }


def main() -> None:
    rows = collect_rows(BATCHES)
    manifests = {
        b: {e["cell_id"]: e for e in json.loads((REPO / b / "cells.json").read_text())}
        for b in BATCHES
    }
    gray_cache: dict = {}

    candidates = ["baseline", "ink"] + [f"const-{f:.2f}" for f in (1.03, 1.05, 1.08)]
    verdicts: dict[str, list[bool]] = {c: [] for c in candidates}
    refined_verdicts: dict[str, list[bool]] = {c: [] for c in candidates}
    kept_rows = []
    n_rung_rows = 0
    n_refined = 0
    rungs_by_row = []

    for r in rows:
        entry = manifests[r["batch"]][r["cell_id"]]
        ys = entry["staff_line_ys_canonical"]
        img_path = find_cell_image(r["cell_id"], r["png_rel"])
        if img_path is None:
            continue
        img = load_gray(img_path, gray_cache)
        if img.shape[1] != entry.get("cell_canonical_w") or img.shape[0] != entry.get(
            "cell_canonical_h"
        ):
            continue
        kept_rows.append(r)

        refined = refine_center(img, r["cx"], r["cy"], r["spacing"])
        if refined is not None:
            n_refined += 1
            rcx, rcy = refined
        else:
            rcx, rcy = r["cx"], r["cy"]
        r["refined"] = refined is not None

        base = snap_to_staff(ys, r["cy"])
        verdicts["baseline"].append(base["position"] == r["truth"])
        refined_verdicts["baseline"].append(
            snap_to_staff(ys, rcy)["position"] == r["truth"]
        )

        rungs = measure_ledger_rungs(img, ys, r["cx"])
        side = rungs["above"] if r["direction"] == "above" else rungs["below"]
        if r["direction"] != "inside" and side:
            n_rung_rows += 1
        rungs_by_row.append(rungs)
        ink = snap_to_staff(ys, r["cy"], ledger_rungs=rungs)
        verdicts["ink"].append(ink["position"] == r["truth"])
        rungs_at_refined = measure_ledger_rungs(img, ys, rcx)
        refined_verdicts["ink"].append(
            snap_to_staff(ys, rcy, ledger_rungs=rungs_at_refined)["position"]
            == r["truth"]
        )

        for f in (1.03, 1.05, 1.08):
            synth = synthetic_rungs(ys, f)
            got = snap_to_staff(ys, r["cy"], ledger_rungs=synth)
            verdicts[f"const-{f:.2f}"].append(got["position"] == r["truth"])
            refined_verdicts[f"const-{f:.2f}"].append(
                snap_to_staff(ys, rcy, ledger_rungs=synth)["position"] == r["truth"]
            )

    print(f"rows evaluated: {len(kept_rows)} (of {len(rows)}; the rest lack an image)")
    print(f"rows with a counter-refined centre: {n_refined}/{len(kept_rows)}")
    out_rows = [i for i, r in enumerate(kept_rows) if r["zone"] != "inside"]
    print(
        f"out-of-staff rows with at least one measured rung on their side: "
        f"{n_rung_rows}/{len(out_rows)}"
    )
    print()
    for name, vd in (("STORED centres", verdicts), ("REFINED centres", refined_verdicts)):
        print(f"\n=== judged at {name} ===")
        header = f"{'zone':18s} {'n':>4s} " + " ".join(f"{c:>12s}" for c in candidates)
        print(header)
        for zone in ZONES:
            idx = [i for i, r in enumerate(kept_rows) if r["zone"] == zone]
            line = f"{zone:18s} {len(idx):4d} "
            for c in candidates:
                agree = sum(1 for i in idx if vd[c][i])
                line += f" {agree:5d} {agree / len(idx) if idx else 0:5.1%}"
            print(line)
        print("Transitions vs baseline (out-of-staff rows only):")
        for c in candidates[1:]:
            rec = [i for i in out_rows if not vd["baseline"][i] and vd[c][i]]
            broke = [i for i in out_rows if vd["baseline"][i] and not vd[c][i]]
            print(f"  {c:12s} recovered={len(rec):3d}  broke={len(broke):3d}")
            if c == "ink":
                for i in broke:
                    r = kept_rows[i]
                    side = (
                        rungs_by_row[i]["above"]
                        if r["direction"] == "above"
                        else rungs_by_row[i]["below"]
                    )
                    print(
                        f"      BROKE {r['batch'].split('/')[-1]}/{r['cell_id']} "
                        f"{r['class']} d={r['d_out_spaces']}sp {r['direction']} "
                        f"refined={r.get('refined')} "
                        f"rungs={[round(v, 1) for v in side]}"
                    )
                for i in [
                    j for j in out_rows if not vd["baseline"][j] and not vd["ink"][j]
                ]:
                    r = kept_rows[i]
                    side = (
                        rungs_by_row[i]["above"]
                        if r["direction"] == "above"
                        else rungs_by_row[i]["below"]
                    )
                    print(
                        f"      STILL WRONG {r['batch'].split('/')[-1]}/{r['cell_id']} "
                        f"{r['class']} d={r['d_out_spaces']}sp {r['direction']} "
                        f"refined={r.get('refined')} "
                        f"rungs={[round(v, 1) for v in side]}"
                    )

    print("\nBias-aware splits (stored centres, out-of-staff rows):")
    overrides = [
        i for i in out_rows
        if not verdicts["baseline"][i]
        and abs(kept_rows[i]["dy_to_grid"]) <= 1.5
        and not kept_rows[i]["bbox_clamped"]
    ]
    rec = sum(1 for i in overrides if verdicts["ink"][i])
    print(
        f"  Sean's explicit `c`-press overrides (click-placed, old snap wrong): "
        f"ink now suggests his class on {rec}/{len(overrides)}"
    )
    freehand = [
        i for i in out_rows
        if abs(kept_rows[i]["dy_to_grid"]) > 1.5 or kept_rows[i]["bbox_clamped"]
    ]
    fb = sum(1 for i in freehand if verdicts["baseline"][i])
    fi = sum(1 for i in freehand if verdicts["ink"][i])
    print(
        f"  hand-positioned boxes (centres free of the old grid, unbiased): "
        f"baseline {fb}/{len(freehand)}, ink {fi}/{len(freehand)}"
    )

    print("\nIn-staff rows: candidate must equal baseline on every one (stored centres).")
    ins = [i for i, r in enumerate(kept_rows) if r["zone"] == "inside"]
    for c in candidates[1:]:
        moved = sum(1 for i in ins if verdicts[c][i] != verdicts["baseline"][i])
        print(f"  {c:12s} changed on {moved} of {len(ins)} in-staff rows")


if __name__ == "__main__":
    main()
