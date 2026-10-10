"""Print crops of the scorer's commonest misses -- DIAGNOSTIC, not evidence about the reader.

    python3 -m tools.omr.hand_truth.score ... --pdf <score.pdf> --crops-dir out/print/1.7-d1-score

A crop is cut from the PDF at the page's own DPI by ``preprocessing.render_page`` -- the render the
gather and the labeling session both use -- and carries (CLAUDE.md §6b "a crop with a ruler"):

* GREEN   the hand-truth box of the SUBJECT (a miss), with a corner bracket in yellow on its exact extent;
* RED     every box the record gathered in the window, thin (so a miss shows as green with no red on it,
          a wrong class or a duplicate as red on or beside it);
* BLUE    the five staff lines the cutter measured for that bar (the ruler), with a tick at each end;
* a header strip naming the kind, the cell, the box, how Sean got it onto the page, and the FRAME
  CONTROL for both sides: mean ink darkness ON each staff line minus half a space off it
  (``readout.frame_control``'s own measure). Positive means the lines land on ink; a crop whose frame
  control is not positive is the wrong frame and says so in its strip.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from tools.omr.hand_truth import score as S

GREEN, RED, BLUE, YELLOW = (0, 170, 0), (220, 30, 30), (40, 90, 230), (230, 190, 0)


def truth_frame_control(image: np.ndarray, page) -> float:
    """``readout.frame_control``'s measure, over the TRUTH's staff lines (the cutter's, in page px)."""
    arr = image.mean(axis=2) if image.ndim == 3 else image
    dark = 255.0 - arr.astype(float)
    on, off = [], []
    for b in S.staff_bands(page):
        x0, x1 = int(max(0, b.rect[0])), int(min(dark.shape[1], b.rect[2]))
        for y in b.lines:
            for yy, bucket in ((y, on), (y + b.space / 2.0, off)):
                r = int(round(yy))
                if 0 <= r < dark.shape[0] and x1 > x0:
                    bucket.append(float(dark[r, x0:x1].mean()))
    return float(np.mean(on) - np.mean(off)) if on and off else float("nan")


def _bracket(img, rect, color, t=3, n=14):
    import cv2

    x0, y0, x1, y1 = (int(round(v)) for v in rect)
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(img, (x, y), (x + sx * n, y), color, t)
        cv2.line(img, (x, y), (x, y + sy * n), color, t)


def cut(report: Dict[str, Any], pdf: Path, out_dir: Path, kinds: Sequence[Dict[str, Any]],
        *, page=None) -> List[Path]:
    import cv2
    from tools.omr.preprocessing import render_page

    page = page or report["_page"]
    run = report["_run"]
    pi = report["record"]["page_index"]
    img = np.asarray(render_page(str(pdf), pi, dpi=page.dpi).rgb).copy()
    rec_fc = S.RO.frame_control(img, run, pi)
    truth_fc = truth_frame_control(img, page)
    out_dir.mkdir(parents=True, exist_ok=True)
    bands = S.staff_bands(page)
    sp = float(np.median([b.space for b in bands])) if bands else 20.0
    paths: List[Path] = []
    glyphs: Sequence[S.ReadGlyph] = report["_glyphs"]
    for rank, k in enumerate(kinds, 1):
        x0, y0, x1, y1 = k["example_rect"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        wx, wy = int(10 * sp), int(5.5 * sp)
        X0, Y0 = int(max(0, cx - wx)), int(max(0, cy - wy))
        X1, Y1 = int(min(img.shape[1], cx + wx)), int(min(img.shape[0], cy + wy))
        crop = img[Y0:Y1, X0:X1].copy()
        sc = 2
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)

        def tf(r):
            return ((r[0] - X0) * sc, (r[1] - Y0) * sc, (r[2] - X0) * sc, (r[3] - Y0) * sc)

        for g in glyphs:
            if g.rect[2] > X0 and g.rect[0] < X1 and g.rect[3] > Y0 and g.rect[1] < Y1:
                a = tf(g.rect)
                cv2.rectangle(crop, (int(a[0]), int(a[1])), (int(a[2]), int(a[3])), RED, 1)
        for b in bands:
            if b.rect[0] <= cx <= b.rect[2] and b.lines[0] - 3 * sp <= cy <= b.lines[-1] + 3 * sp:
                for y in b.lines:
                    yy = int((y - Y0) * sc)
                    if 0 <= yy < crop.shape[0]:
                        cv2.line(crop, (0, yy), (14, yy), BLUE, 2)
                        cv2.line(crop, (crop.shape[1] - 15, yy), (crop.shape[1] - 1, yy), BLUE, 2)
        a = tf((x0, y0, x1, y1))
        cv2.rectangle(crop, (int(a[0]), int(a[1])), (int(a[2]), int(a[3])), GREEN, 2)
        _bracket(crop, a, YELLOW)
        head = np.full((64, crop.shape[1], 3), 255, np.uint8)
        t1 = f"#{rank} {k['family']}/{k['truth_class']} {k['cause']}  cell {k['example_cell']}  box {k['example_box']}"
        t2 = (f"GREEN=truth box (yellow brackets = subject)  RED=record boxes  BLUE=staff lines   "
              f"frame: record {rec_fc:+.1f} truth {truth_fc:+.1f} ({'OK' if min(rec_fc, truth_fc) > 0 else 'FAIL'})")
        cv2.putText(head, t1, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(head, t2, (6, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1, cv2.LINE_AA)
        out = np.vstack([head, crop])
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-",
                      f"{rank}-{k['family']}-{k['truth_class']}-{k['cause'].split(':')[0]}-{k['example_cell']}")
        p = out_dir / f"{safe}.png"
        cv2.imwrite(str(p), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        paths.append(p)
    return paths


def cut_cells(report: Dict[str, Any], pdf: Path, out_dir: Path, cell_ids: Sequence[str], *, scale: int = 1,
              page=None, image=None) -> List[Path]:
    """Whole-cell crops with EVERY truth box (green, labelled by class) and every record box (red) drawn,
    for looking at what Sean boxed against what was gathered (header cells, a suspect label)."""
    import cv2
    from tools.omr.preprocessing import render_page

    page = page or report["_page"]
    pi = report["record"]["page_index"]
    img = image if image is not None else np.asarray(render_page(str(pdf), pi, dpi=page.dpi).rgb).copy()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for cid in cell_ids:
        c = page.cell(cid)
        X0, Y0, X1, Y1 = (int(v) for v in c.rect)
        crop = cv2.resize(img[Y0:Y1, X0:X1].copy(), None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        for g in report["_glyphs"]:
            if g.rect[2] > X0 and g.rect[0] < X1 and g.rect[3] > Y0 and g.rect[1] < Y1:
                cv2.rectangle(crop, (int((g.rect[0] - X0) * scale), int((g.rect[1] - Y0) * scale)),
                              (int((g.rect[2] - X0) * scale), int((g.rect[3] - Y0) * scale)), RED, 1)
        for it in report["_items"]:
            if it.rect[2] > X0 and it.rect[0] < X1 and it.rect[3] > Y0 and it.rect[1] < Y1:
                a = ((it.rect[0] - X0) * scale, (it.rect[1] - Y0) * scale, (it.rect[2] - X0) * scale,
                     (it.rect[3] - Y0) * scale)
                cv2.rectangle(crop, (int(a[0]), int(a[1])), (int(a[2]), int(a[3])), GREEN, 2)
                cv2.putText(crop, it.cls.replace("noteheadBlack", "nB").replace("OnLine", "L"), (int(a[0]), max(10, int(a[1]) - 3)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, GREEN, 1, cv2.LINE_AA)
        for b in S.staff_bands(page):
            if b.cell_id == cid:
                for y in b.lines:
                    yy = int((y - Y0) * scale)
                    cv2.line(crop, (0, yy), (14, yy), BLUE, 2)
        head = np.full((26, crop.shape[1], 3), 255, np.uint8)
        cv2.putText(head, f"cell {cid}  GREEN=truth  RED=record  BLUE=staff lines", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        p = out_dir / f"cell-{cid}.png"
        cv2.imwrite(str(p), cv2.cvtColor(np.vstack([head, crop]), cv2.COLOR_RGB2BGR))
        paths.append(p)
    return paths


def cut_ink(report: Dict[str, Any], pdf: Path, out_dir: Path, centres: Sequence[Tuple[float, float]],
            *, page=None, half: Tuple[int, int] = (450, 300)) -> List[Path]:
    """Windows around page points showing the ink components the repo's coverage control lists
    (MAGENTA) beside the truth boxes (GREEN): what the control is actually calling "unboxed" -- on a
    thick-lined scan, mostly staff-line slivers and barlines nobody boxed, not missed notes."""
    import cv2
    from tools.omr.preprocessing import render_page

    page = page or report["_page"]
    pi = report["record"]["page_index"]
    img = np.asarray(render_page(str(pdf), pi, dpi=page.dpi).rgb).copy()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for cx, cy in centres:
        X0, Y0, X1, Y1 = int(cx - half[0]), int(cy - half[1]), int(cx + half[0]), int(cy + half[1])
        crop = img[max(0, Y0):Y1, max(0, X0):X1].copy()
        X0, Y0 = max(0, X0), max(0, Y0)
        for r in report["_uncovered"]:
            if r[2] > X0 and r[0] < X1 and r[3] > Y0 and r[1] < Y1:
                cv2.rectangle(crop, (int(r[0] - X0), int(r[1] - Y0)), (int(r[2] - X0), int(r[3] - Y0)),
                              (200, 0, 200), 2)
        for it in report["_items"]:
            r = it.rect
            if r[2] > X0 and r[0] < X1 and r[3] > Y0 and r[1] < Y1:
                cv2.rectangle(crop, (int(r[0] - X0), int(r[1] - Y0)), (int(r[2] - X0), int(r[3] - Y0)), GREEN, 2)
                cv2.putText(crop, it.cls[:14], (int(r[0] - X0), max(10, int(r[1] - Y0) - 3)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 120, 0), 1, cv2.LINE_AA)
        head = np.full((26, crop.shape[1], 3), 255, np.uint8)
        cv2.putText(head, "MAGENTA = ink the coverage control lists (<50% under a truth box)  GREEN = truth boxes",
                    (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        p = out_dir / f"ink-uncovered-{int(cx)}-{int(cy)}.png"
        cv2.imwrite(str(p), cv2.cvtColor(np.vstack([head, crop]), cv2.COLOR_RGB2BGR))
        paths.append(p)
    return paths
