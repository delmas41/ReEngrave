"""Campaign-wide audit: every INSIDE-STAFF click-placed label vs the grid
measured from the cell's own printed lines at that label's x.

For each added notehead label in the 10 hollow batches whose centre sits
inside the staff band (same zone rule as the probe):
  - measure printed line bands at cx (2.8-spacing window, >=70% fill, thin),
  - match to stored lines within 0.55 spacing; need >=3 matched, fill the
    rest by median displacement,
  - true parity = nearest half-step slot on the MEASURED grid,
  - report: median displacement (grid error at this label), true parity vs
    stored-grid parity vs Sean's class, and the margin.

Outputs: distribution of grid error over labels/cells, silent-miss
candidates (Sean's class agrees with the OLD grid but disagrees with the
measured one), and box-centre displacement from the true slot.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
SHAMIR = MAIN / ".claude/worktrees/peaceful-shamir-d12e52"

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

VDIRS = [MAIN / "data/user-labeled/v8-2026-09-02-hollow2-5pub/images",
         MAIN / "data/user-labeled/v7-2026-09-02-hollow/images"]


def find_image(batch_rel: str, cell_id: str) -> Path | None:
    cands = [MAIN / batch_rel / "cells" / f"{cell_id}.png",
             SHAMIR / batch_rel / "cells" / f"{cell_id}.png"]
    cands += [v / f"{cell_id}.png" for v in VDIRS]
    for c in cands:
        if c.exists():
            return c
    return None


def load_json_either(rel: str):
    for root in (MAIN, SHAMIR):
        p = root / rel
        if p.exists():
            return json.loads(p.read_text())
    return None


def bands_at_x(ink, x, spacing):
    h, w = ink.shape
    half = 1.4 * spacing
    xa, xb = int(max(0, x - half)), int(min(w, x + half))
    if xb - xa < spacing:
        return []
    win = ink[:, xa:xb]
    frac = win.mean(axis=1)
    out = []
    yi = 0
    while yi < h:
        if frac[yi] >= 0.70:
            j = yi
            while j < h and frac[j] >= 0.70:
                j += 1
            if (j - yi) <= 0.40 * spacing:
                rows = np.arange(yi, j, dtype=float)
                wts = frac[yi:j]
                out.append(float((rows * wts).sum() / wts.sum()))
            yi = j
        else:
            yi += 1
    return out


def snap_parity(ys, cy):
    slots = []
    for i, gy in enumerate(ys):
        slots.append((gy, "on_line"))
        if i + 1 < len(ys):
            slots.append(((gy + ys[i + 1]) / 2.0, "in_space"))
    sy, par = min(slots, key=lambda s: abs(s[0] - cy))
    # margin to the runner-up of opposite parity
    other = min((abs(s[0] - cy) for s in slots if s[1] != par), default=None)
    return par, sy, abs(sy - cy), other


def main() -> None:
    img_cache = {}
    rows = []
    n_no_img = 0
    for b in BATCHES:
        man = load_json_either(f"{b}/cells.json")
        if man is None:
            print(f"WARN no manifest {b}", file=sys.stderr)
            continue
        man = {e["cell_id"]: e for e in man}
        vdir = None
        for root in (MAIN, SHAMIR):
            for name in ("verdicts-merged", "verdicts"):
                d = root / b / name
                if d.is_dir():
                    vdir = d
                    break
            if vdir:
                break
        for vf in sorted(vdir.glob("*.verdict.json")):
            v = json.loads(vf.read_text())
            entry = man.get(v.get("cell_id"))
            if entry is None:
                continue
            ys = sorted(entry.get("staff_line_ys_canonical") or [])
            if len(ys) < 5:
                continue
            spacing = float(np.median(np.diff(ys)))
            for a in v.get("added_detections", []):
                cls = a.get("human_class", "")
                if not cls.startswith("notehead"):
                    continue
                if cls.endswith("OnLine"):
                    truth = "on_line"
                elif cls.endswith("InSpace"):
                    truth = "in_space"
                else:
                    continue
                bbox = a.get("bbox") or {}
                if not bbox:
                    continue
                cx = bbox["x"] + bbox["w"] / 2.0
                cy = bbox["y"] + bbox["h"] / 2.0
                # inside-staff only (same 0.25-spacing tolerance as the probe)
                if cy < ys[0] - 0.25 * spacing or cy > ys[-1] + 0.25 * spacing:
                    continue
                stored_par, stored_slot, d_stored, _ = snap_parity(ys, cy)
                key = (b, v["cell_id"])
                if key not in img_cache:
                    p = find_image(b, v["cell_id"])
                    if p is None:
                        img_cache[key] = None
                    else:
                        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                        if g is None or g.shape[0] != entry.get("cell_canonical_h"):
                            img_cache[key] = None
                        else:
                            _, ib = cv2.threshold(
                                g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                            img_cache[key] = ib > 0
                ink = img_cache[key]
                if ink is None:
                    n_no_img += 1
                    continue
                bb = bands_at_x(ink, cx, spacing)
                meas = []
                for sy in ys:
                    cands = [c for c in bb if abs(c - sy) <= 0.55 * spacing]
                    meas.append(min(cands, key=lambda c: abs(c - sy)) if cands else None)
                n_matched = sum(m is not None for m in meas)
                if n_matched < 3:
                    disp = None
                    true_par = None
                    margin = None
                    d_true_slot = None
                else:
                    disp = float(np.median([m - s for m, s in zip(meas, ys)
                                            if m is not None]))
                    grid = [m if m is not None else s + disp
                            for m, s in zip(meas, ys)]
                    true_par, true_slot, d_true, d_other = snap_parity(grid, cy)
                    margin = None if d_other is None else d_other - d_true
                    d_true_slot = d_true
                rows.append({
                    "batch": b.split("/")[-1], "cell_id": v["cell_id"],
                    "class": cls, "truth": truth,
                    "cx": round(cx, 1), "cy": round(cy, 1),
                    "spacing": spacing,
                    "on_old_grid": abs(cy - stored_slot) <= 1.5,
                    "stored_parity": stored_par,
                    "n_matched": n_matched,
                    "grid_err": None if disp is None else round(disp, 1),
                    "grid_err_sp": None if disp is None else round(disp / spacing, 3),
                    "true_parity": true_par,
                    "margin": None if margin is None else round(margin, 1),
                    "d_true_slot_sp": None if d_true_slot is None else round(d_true_slot / spacing, 3),
                })

    out = Path(__file__).parent / "audit_rows.json"
    out.write_text(json.dumps(rows, indent=1))

    ok = [r for r in rows if r["true_parity"] is not None]
    print(f"inside-staff added-notehead labels: {len(rows)} "
          f"({len(ok)} with measured grid, {n_no_img} lacked images)")

    errs = np.array([abs(r["grid_err_sp"]) for r in ok])
    print("\n|grid error| at label x, in staff spaces:")
    for th in (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5):
        print(f"  > {th:.2f} sp: {(errs > th).sum():3d} labels")
    print(f"  median {np.median(errs):.3f}  p90 {np.percentile(errs, 90):.3f}"
          f"  max {errs.max():.3f}")

    by_cell = {}
    for r in ok:
        by_cell.setdefault((r["batch"], r["cell_id"]), []).append(abs(r["grid_err_sp"]))
    worst = sorted(by_cell.items(), key=lambda kv: -np.median(kv[1]))[:15]
    print("\nworst cells by median |grid error| (sp):")
    for (b, c), v in worst:
        print(f"  {np.median(v):5.3f}  {b:46s} {c}  ({len(v)} labels)")

    print("\nSean's class vs MEASURED grid parity:")
    dis = [r for r in ok if r["true_parity"] != r["truth"]]
    print(f"  disagree: {len(dis)} / {len(ok)}")
    silent = [r for r in dis if r["stored_parity"] == r["truth"]]
    caught = [r for r in dis if r["stored_parity"] != r["truth"]]
    print(f"    of which stored grid AGREED with Sean (measured-vs-both, "
          f"suspect my measurement or odd ink): {len(silent)}")
    for r in silent:
        print(f"      {r['batch']:44s} {r['cell_id']:26s} {r['class']:22s}"
              f" grid_err={r['grid_err_sp']:+.2f}sp margin={r['margin']}px n={r['n_matched']}")
    print(f"    of which stored grid ALSO disagreed with Sean (the probe's 9): {len(caught)}")

    print("\nSILENT MISS candidates — Sean's class = OLD grid suggestion, "
          "measured grid says OTHER parity (click-placed only):")
    sm = [r for r in ok if r["on_old_grid"] and r["true_parity"] != r["truth"]
          and r["stored_parity"] == r["truth"]]
    for r in sm:
        print(f"  {r['batch']:44s} {r['cell_id']:26s} {r['class']:22s}"
              f" grid_err={r['grid_err_sp']:+.2f}sp margin={r['margin']}px"
              f" d_true={r['d_true_slot_sp']}sp")

    print("\nbox-centre displacement from TRUE slot (click-placed labels, sp):")
    dd = np.array([r["d_true_slot_sp"] for r in ok if r["on_old_grid"]])
    if len(dd):
        print(f"  n={len(dd)} median {np.median(dd):.3f} p90 {np.percentile(dd, 90):.3f}"
              f" max {dd.max():.3f}; >0.25sp: {(dd > 0.25).sum()}")


if __name__ == "__main__":
    main()
