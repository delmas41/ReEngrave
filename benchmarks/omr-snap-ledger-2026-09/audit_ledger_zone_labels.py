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

**(3) Edge fragments.** A notehead-shaped label sitting in the cell's own
padding, cut off by the crop — the same fault `transcribe._drop_clipped_
notehead_fragments` already screens the DETECTOR's output for, applied
here for the first time to HAND-DRAWN labels, which face the identical
ambiguous ink and have never been checked. Found live in the training
corpus (v3-2026-06-09-mahler5, v4-2026-06-10-la-mer, 2026-09-03): two
`notehead*` labels at 0.51–0.54 staff spaces tall — inside the measured
fragment band (0.29–0.56 sp) and well under the genuine-notehead floor
(0.60+) — each with its box touching the cell's own top or bottom edge.
Rendered crops confirmed both are the clipped tip of ink from the
NEIGHBOURING staff's system, not a symbol in this measure at all — so the
right correction is likely delete, not relabel. Needs no image (manifest
geometry only), so it also reaches the batches this file's other two
checks cannot (`_nostaff.png` missing). Credit: scanned-weights session,
who found the two live cells and the missing WHERE-in-the-cell field that
settled it after an initial height-only read called them rests.

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
# `transcribe._CLIPPED_NOTEHEAD_MAX_SPACES` — an exact port of an already
# measured, already-shipped discriminator (fragments run 0.29-0.56sp,
# genuine edge-touching noteheads 0.77+), applied here to HAND-DRAWN labels
# for the first time. No image needed: manifest geometry only.
CLIPPED_NOTEHEAD_MAX_SPACES = 0.6
# ⚠️ The ORIGINAL discriminator's edge test is 1px, because a MODEL's box
# wraps exactly the ink the crop left it (the ink is cut off at row 0, so
# the box starts there too). A HAND-DRAWN box has no such guarantee — the
# two live cases this was built to catch sit 7px/100sp=0.07sp and
# 22px/79.75sp=0.28sp from the cell's true edge, not 1px, because the human
# drew a small margin around the visible sliver rather than tracing it
# exactly. So the edge test here is in STAFF SPACES, generous enough for
# that drawing slack (checked against both known cases) while still
# meaning "near the cell's own boundary": a genuine mid-cell short note (a
# different, unrelated problem) would not land here by chance.
CELL_EDGE_TOLERANCE_SPACES = 0.5


def blob_centre(im: np.ndarray, cx: float, cy: float, sp: float) -> tuple[float, float, float] | None:
    """(y, height_sp, width_sp) of the notehead-sized ink blob nearest (cx, cy)
    on a nostaff image.

    ⚠️ **This centroid is WRONG whenever a ledger rung print-merges into the
    same connected component as the head** (measured 2026-09-03, on the
    Simrock/Dvořák 9 batch, an out-of-sample test the scanned-weights session
    ran): the rung's own mass pulls the centroid toward it, by up to a full
    half-step — enough to flip the reported parity. `height_sp`/`width_sp`
    are returned so a caller can show them alongside a flagged label, but
    ⚠️ **do not use them to auto-reject or auto-correct** — five candidate
    fixes were tried and measured against BOTH the 6 confirmed-correct Brahms
    corrections and the Simrock false positives, and none generalises:
    a size cutof (width > ~1.8-2.0sp) looks discriminating on the 4 Simrock
    false positives alone, but 40 of 76 Brahms ledger-zone labels — all
    independently uncontested — ALSO measure above 1.8sp, so the same cutoff
    that would catch Simrock's rung-merges flags most of Brahms's clean
    labels too. A tighter width filtered directly on the box ("keep only
    rows whose local ink run is under some multiple of the head's width")
    resolves the Simrock cases 4/4 but breaks all 6 Brahms cases, because it
    only has room to detect the rung's excess where the human's drawn BOX
    has generous padding around the head — Simrock's boxes do, Brahms's do
    not, and the filter silently degenerates to plain box-centroid (already
    known unreliable) wherever it doesn't. See
    LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md "The rung-merge failure mode" for
    the full comparison. The safe use of `height_sp`/`width_sp` is what this
    docstring is doing right now: telling the next person not to trust a
    number here without looking at the actual ink, the same way this one
    was found.
    """
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
        h_px, w_px = yy.max() - yy.min(), xx.max() - xx.min()
        if h_px > 1.8 * sp or w_px > 2.2 * sp:
            continue
        d = abs(yy.mean() + y0 - cy) + abs(xx.mean() + x0 - cx)
        if best is None or d < best[0]:
            best = (d, yy.mean() + y0, h_px / sp, w_px / sp)
    return None if best is None else (best[1], best[2], best[3])


def audit_batch(batch: Path) -> dict:
    man_p, vdir = batch / "cells.json", batch / "verdicts"
    if not man_p.exists() or not vdir.exists():
        return {}
    man = {e["cell_id"]: e for e in json.loads(man_p.read_text())}
    parity_sus, shape_sus, edge_sus = [], [], []
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
            # (3) edge fragments — a notehead-labeled box, too short to be one,
            # with its own top or bottom touching the cell's crop boundary.
            # Uses the LABEL's own bbox height (h_sp above), computed before
            # the ledger-parity block below reassigns h_sp/w_sp from the blob.
            cell_h = entry.get("cell_canonical_h")
            if cls.startswith("notehead") and cell_h and h_sp < CLIPPED_NOTEHEAD_MAX_SPACES:
                top, bottom = bb["y"], bb["y"] + bb["h"]
                tol_px = CELL_EDGE_TOLERANCE_SPACES * sp
                if top <= tol_px or bottom >= cell_h - tol_px:
                    edge = "top" if top <= tol_px else "bottom"
                    edge_sus.append((cid, cls, h_sp, edge))
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
            r = blob_centre(im, cx, cy, sp)
            if r is None:
                continue
            by, h_sp, w_sp = r
            step = (by - ys[0]) / (sp / 2.0)
            off = abs(step - round(step))
            measured = "OnLine" if round(step) % 2 == 0 else "InSpace"
            stored = "OnLine" if cls.endswith("OnLine") else "InSpace"
            if measured != stored and off < MAX_OFF_GRID:
                parity_sus.append((cid, cls, cls.replace(stored, measured),
                                   step, off, abs(by - cy), h_sp, w_sp))
    return {"batch": batch.name, "n_labels": n_labels, "n_ledger": n_ledger,
            "n_noimg": n_noimg, "parity": parity_sus, "shape": shape_sus,
            "edge": edge_sus}


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
    tot_e: list = []
    for b in batches:
        r = audit_batch(b)
        if not r:
            print(f"  (skipped {b}: no cells.json/verdicts)")
            continue
        tot_l += r["n_labels"]; tot_led += r["n_ledger"]
        tot_p += r["parity"]; tot_s += r["shape"]; tot_e += r["edge"]
        note = f"  ⚠️ {r['n_noimg']} cells had no _nostaff image" if r["n_noimg"] else ""
        print(f"{r['batch']:52} labels={r['n_labels']:>4} ledger-zone={r['n_ledger']:>4} "
              f"parity-suspect={len(r['parity'])} shape-suspect={len(r['shape'])} "
              f"edge-suspect={len(r['edge'])}{note}")
    print(f"\nTOTAL: {tot_l} human labels, {tot_led} in the ledger zone")
    if tot_p:
        print(f"\nLEDGER-ZONE PARITY suspects ({len(tot_p)}) — measured on the ink, not the box.")
        print("⚠️ h_sp/w_sp are context, not a verdict — width alone does NOT separate a real "
              "rung-merge from a normal label (measured: 40 of 76 Brahms ledger-zone labels, "
              "all uncontested, also exceed 1.8sp wide). Every row here is a candidate for a "
              "HUMAN to look at the actual ink, per LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md.")
        for cid, cls, to, step, off, dy, h_sp, w_sp in sorted(tot_p, key=lambda r: r[4]):
            print(f"  {cid:30} {cls:22} -> {to:22} step={step:6.2f} "
                  f"off-grid={off:.2f} box_is_{dy:.0f}px_from_ink  blob={h_sp:.2f}x{w_sp:.2f}sp")
    if tot_s:
        print(f"\nSHAPE-vs-CLASS suspects ({len(tot_s)}) — a parity audit cannot see these:")
        for cid, cls, geom, why in tot_s:
            print(f"  {cid:30} {cls:22} {geom:28} {why}")
    if tot_e:
        print(f"\nEDGE-FRAGMENT suspects ({len(tot_e)}) — a notehead label under "
              f"{CLIPPED_NOTEHEAD_MAX_SPACES}sp tall, touching the cell's own crop "
              "boundary. Likely ink from the NEIGHBOURING staff, not this measure — "
              "the correction is probably delete, not relabel. Manifest-only; needs "
              "no image.")
        for cid, cls, h_sp, edge in sorted(tot_e, key=lambda r: r[2]):
            print(f"  {cid:30} {cls:22} h={h_sp:.2f}sp  touches cell's {edge} edge")
    if not tot_p and not tot_s and not tot_e:
        print("\nno suspects.")
    print("\n(read-only: nothing was written; each hit is a candidate for a human, "
          "not an automatic correction)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
