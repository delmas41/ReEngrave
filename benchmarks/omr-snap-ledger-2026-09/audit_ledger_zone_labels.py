"""Audit hand-drawn labels where the two known failure modes live.

Companion to `../omr-cell-grid-tilt-2026-09/audit_labels_vs_measured_grid.py`,
which audits INSIDE-staff parity. This one covers what that cannot:

**(1) Ledger-zone parity.** Out-of-staff noteheads, where the click-to-box
snap extrapolates the parity grid past the staff and can hand the labeler a
wrong OnLine/InSpace suggestion. Measured on the Brahms 1 / Breitkopf
completion pass (2026-09-03): **6 suspect of 76 ledger-zone labels (~8%)
against 0 inside-staff parity errors** over the same cells.

⚠️ **Measure the INK, never the BOX.** A click-placed box inherits the
slot the snap chose, so a box centre is biased toward the grid that placed
it — evaluating a grid question at stored box centres re-measures the old
grid. The scanned-weights session checked the same three labels at box
centres, got the opposite answer on two of them, and was wrong both times.
So the parity here comes from the notehead's own blob on the
staff-line-removed `*_nostaff.png`, not from the label's rectangle.

**(2) Shape-vs-class.** A parity audit is blind to a symbol labeled the
wrong KIND. A rest is a wide flat block and a notehead is a round-ish oval,
and the two do not overlap: on that same batch the corrected whole rest
measured **2.13 x 0.72 staff spaces, aspect 2.97:1**, against a median
black notehead of **1.19 x 1.00, aspect 1.19:1**. One such error was in the
batch (a whole rest labeled `noteheadBlackInSpace`), sitting INSIDE the
staff, so neither parity auditor would ever have found it. Credit to the
scanned-weights session for this discriminator.

Read-only: it writes nothing and changes no label.

    python3 benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py \
        --batch benchmarks/omr-labeling-simrock-2026-09
    # no --batch: every benchmarks/omr-labeling-* batch that has verdicts

⚠️ Run from the MAIN checkout. `benchmarks/*/cells/` is gitignored, so in a
worktree the images are absent and every cell abstains.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    from PIL import Image
    from scipy import ndimage
except ImportError as exc:  # pragma: no cover - environment guard
    print(f"needs pillow + scipy: {exc}", file=sys.stderr)
    raise SystemExit(2)

REPO = Path(__file__).resolve().parents[2]

# A label whose measured parity disagrees is only reported when the blob sits
# this close to a half-step slot; further out means the blob is not cleanly a
# notehead (a stem, a beam stub, two merged heads) and the read is not worth
# putting in front of a human.
MAX_OFF_GRID = 0.35
# Outside this band (in staff spacings beyond the outer lines) is "ledger zone".
INSIDE_PAD = 0.25
# Shape gate: a notehead is about as tall as a staff space and never wide and
# flat; rest glyphs (whole/half blocks especially) are. Deliberately loose —
# it is a flag for a human, not a classifier.
REST_MIN_ASPECT = 2.0
HEAD_MAX_ASPECT = 1.8


def blob_centre(im: np.ndarray, cx: float, cy: float, sp: float) -> float | None:
    """y of the notehead-sized ink blob nearest (cx, cy) on a nostaff image."""
    x0, x1 = int(max(0, cx - 1.1 * sp)), int(min(im.shape[1], cx + 1.1 * sp))
    y0, y1 = int(max(0, cy - 1.1 * sp)), int(min(im.shape[0], cy + 1.1 * sp))
    if x1 <= x0 or y1 <= y0:
        return None
    lab, n = ndimage.label(im[y0:y1, x0:x1] < 128)
    best = None
    for i in range(1, n + 1):
        yy, xx = np.nonzero(lab == i)
        if len(yy) < 0.15 * sp * sp:
            continue
        if (yy.max() - yy.min()) > 1.8 * sp or (xx.max() - xx.min()) > 2.2 * sp:
            continue
        d = abs(yy.mean() + y0 - cy) + abs(xx.mean() + x0 - cx)
        if best is None or d < best[0]:
            best = (d, yy.mean() + y0)
    return None if best is None else best[1]


def audit_batch(batch: Path) -> dict:
    man_p, vdir = batch / "cells.json", batch / "verdicts"
    if not man_p.exists() or not vdir.exists():
        return {}
    man = {e["cell_id"]: e for e in json.loads(man_p.read_text())}
    parity_sus, shape_sus = [], []
    n_ledger = n_labels = n_noimg = 0
    for vf in sorted(vdir.glob("*.verdict.json")):
        try:
            v = json.loads(vf.read_text())
        except json.JSONDecodeError:
            continue
        cid = v.get("cell_id")
        entry = man.get(cid)
        if entry is None:
            continue
        ys = sorted(entry.get("staff_line_ys_canonical") or [])
        if len(ys) < 5:
            continue
        sp = float(np.median(np.diff(ys)))
        if sp <= 0:
            continue
        img_p = batch / "cells" / f"{cid}_nostaff.png"
        im = np.array(Image.open(img_p).convert("L")) if img_p.exists() else None
        if im is None:
            n_noimg += 1
        for a in v.get("added_detections", []):
            if str(a.get("id", "")).startswith("M"):
                continue                       # a pre-fill's box, not a human's
            cls = a.get("human_class") or ""
            bb = a.get("bbox") or {}
            if not cls or not bb.get("w"):
                continue
            n_labels += 1
            w_sp, h_sp = bb["w"] / sp, bb["h"] / sp
            aspect = bb["w"] / bb["h"] if bb["h"] else 0.0
            # (2) shape vs class — applies everywhere, inside the staff too
            if cls.startswith("notehead") and aspect >= REST_MIN_ASPECT:
                shape_sus.append((cid, cls, f"{w_sp:.2f}x{h_sp:.2f}sp aspect {aspect:.2f}:1",
                                  "wide flat block labeled a notehead — a rest?"))
            elif cls.startswith("rest") and aspect <= 1.0 and h_sp <= 1.4:
                shape_sus.append((cid, cls, f"{w_sp:.2f}x{h_sp:.2f}sp aspect {aspect:.2f}:1",
                                  "notehead-shaped box labeled a rest?"))
            # (1) ledger-zone parity
            if not (cls.startswith("notehead")
                    and (cls.endswith("OnLine") or cls.endswith("InSpace"))):
                continue
            cy, cx = bb["y"] + bb["h"] / 2.0, bb["x"] + bb["w"] / 2.0
            if ys[0] - INSIDE_PAD * sp <= cy <= ys[-1] + INSIDE_PAD * sp:
                continue                       # inside staff: the tilt auditor's job
            n_ledger += 1
            if im is None:
                continue
            by = blob_centre(im, cx, cy, sp)
            if by is None:
                continue
            step = (by - ys[0]) / (sp / 2.0)
            off = abs(step - round(step))
            measured = "OnLine" if round(step) % 2 == 0 else "InSpace"
            stored = "OnLine" if cls.endswith("OnLine") else "InSpace"
            if measured != stored and off < MAX_OFF_GRID:
                parity_sus.append((cid, cls, cls.replace(stored, measured),
                                   step, off, abs(by - cy)))
    return {"batch": batch.name, "n_labels": n_labels, "n_ledger": n_ledger,
            "n_noimg": n_noimg, "parity": parity_sus, "shape": shape_sus}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--batch", type=Path, action="append", default=None,
                    help="batch directory (repeatable); default: every "
                         "benchmarks/omr-labeling-* with a verdicts/ dir")
    args = ap.parse_args()
    # Relative paths resolve against the CWD, not this file's checkout: the
    # cell images are gitignored, so this has to be runnable from the main
    # checkout even when the script itself sits in a worktree.
    if args.batch:
        batches = [b if b.is_absolute() else (Path.cwd() / b) for b in args.batch]
    else:
        root = Path.cwd() if (Path.cwd() / "benchmarks").is_dir() else REPO
        batches = sorted(p for p in (root / "benchmarks").glob("omr-labeling-*")
                         if (p / "verdicts").is_dir())
    tot_l = tot_led = 0
    tot_p: list = []
    tot_s: list = []
    for b in batches:
        r = audit_batch(b)
        if not r:
            print(f"  (skipped {b}: no cells.json/verdicts)")
            continue
        tot_l += r["n_labels"]; tot_led += r["n_ledger"]
        tot_p += r["parity"]; tot_s += r["shape"]
        note = f"  ⚠️ {r['n_noimg']} cells had no _nostaff image" if r["n_noimg"] else ""
        print(f"{r['batch']:52} labels={r['n_labels']:>4} ledger-zone={r['n_ledger']:>4} "
              f"parity-suspect={len(r['parity'])} shape-suspect={len(r['shape'])}{note}")
    print(f"\nTOTAL: {tot_l} human labels, {tot_led} in the ledger zone")
    if tot_p:
        print(f"\nLEDGER-ZONE PARITY suspects ({len(tot_p)}) — measured on the ink, not the box:")
        for cid, cls, to, step, off, dy in sorted(tot_p, key=lambda r: r[4]):
            print(f"  {cid:30} {cls:22} -> {to:22} step={step:6.2f} "
                  f"off-grid={off:.2f} box_is_{dy:.0f}px_from_ink")
    if tot_s:
        print(f"\nSHAPE-vs-CLASS suspects ({len(tot_s)}) — a parity audit cannot see these:")
        for cid, cls, geom, why in tot_s:
            print(f"  {cid:30} {cls:22} {geom:28} {why}")
    if not tot_p and not tot_s:
        print("\nno suspects.")
    print("\n(read-only: nothing was written; each hit is a candidate for a human, "
          "not an automatic correction)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
