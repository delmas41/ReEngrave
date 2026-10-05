#!/usr/bin/env python3
"""lane-ledger-accidental (2026-10-04): ONE crop sheet for tiles 5, 6, 2 of
Sean's 10-wrong sheet, at x6, real print.

red = the detector's head box; purple = detector accidental boxes; orange
solid = rungs the reader KEPT (final ladder); magenta dashed = rungs the bare
ink offers that the reader dropped (label says the rule); yellow tint = ink
blanked by `_exclude_other_heads_ink` (other heads + accidentals); cyan ticks
= the staff lines at the head's x.  Every drawn line is pixel-checked: the
ink fraction on its row vs 0.5 sp above / below (printed on the tile).

    python3 benchmarks/omr-local-staff-2026-09/accidental_sheet.py [subject...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import accidental_census as ac  # noqa: E402
import edge_census as ec  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT = HERE.parents[1] / "out" / "print" / "ledgers" / "accidental"
SCALE = 6
SUBJECTS = ["glyph/3/0/0/7/1", "glyph/3/0/0/7/2", "glyph/3/0/0/2/4"]
ARM_KW = None      # --arm=NAME draws the same tiles under one of score_accidental.ARMS
RED, PURPLE, ORANGE, MAGENTA, YELLOW, CYAN = (
    (0, 0, 255), (200, 0, 160), (0, 140, 255), (255, 0, 255), (0, 230, 255), (255, 255, 0))


def row_ink(gray, y, cx, sp, thr):
    x0, x1 = int(cx - 1.1 * sp), int(cx + 1.1 * sp)
    r = gray[int(round(y)), x0:x1]
    return float((r <= thr).mean())


def blanked_mask(h, side_sign, cx, sp, others):
    """Page-coordinate boolean mask of ink `_exclude_other_heads_ink` blanks
    in the main window (the same window/threshold `measure_ledger_rungs` uses)."""
    gray = h["gray"]
    ys = sorted(h["lines"])
    edge_y = ys[0] if side_sign < 0 else ys[-1]
    near = edge_y + side_sign * 0.30 * sp
    far = edge_y + side_sign * lg.MAX_SPACES * sp
    yy0, yy1 = int(max(0, min(near, far))), int(min(gray.shape[0], max(near, far)))
    x0 = int(max(0, cx - lg.WINDOW_HALF_WIDTH_SPACES * sp))
    x1 = int(min(gray.shape[1], cx + lg.WINDOW_HALF_WIDTH_SPACES * sp))
    win = gray[yy0:yy1, x0:x1]
    thr = lg._otsu_threshold(win)
    raw = win <= thr
    ex = lg._exclude_other_heads_ink(raw, others, x0, yy0, sp, gray, thr)
    m = np.zeros(gray.shape, bool)
    m[yy0:yy1, x0:x1] = raw & ~ex
    return m, thr


CAUSE = {
    "glyph/3/0/0/7/1": ["CAUSE: the stack's LOWER head (7/2) has ink outside its undersized box;",
                        "row y434 survives the exclusion because accidental ink 5px left of",
                        "that head counts as 'ledger continues left' (white gap, not connected)."],
    "glyph/3/0/0/7/2": ["CAUSE (not the accidental): the head is on L1 (y424, evidenced) but the",
                        "ladder also holds the stack's L2/L3 (396, 376) beyond it; 'through'",
                        "credited all three (gap -3.87 sp). no-accidental run gives the same -6."],
    "glyph/3/0/0/2/4": ["CAUSE (not an accidental): the 2nd ledger (y~415) juts out of the",
                        "neighbour head 2/9 on ONE side; the exclusion blanks 2/9's rows",
                        "(needs both sides) so it is never offered; y395 then reads 'through'."],
}


def tile(h, pos, reason, tr):
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ys = sorted(h["lines"])
    sp = (ys[-1] - ys[0]) / 4
    sign = -1.0 if cy < ys[0] else 1.0
    side = "above" if sign < 0 else "below"
    edge = ys[0] if sign < 0 else ys[-1]
    others = [b for (s, b) in h["boxes"] if s != h["subject"]] + [b for (_s, b) in h["acc"]]
    kw = ARM_KW or {}
    with lg.exclusion_rules(connected=kw.get("connected_continuation", False)):
        mask, thr = blanked_mask(h, sign, cx, sp, others)
    bare = [float(v) for v in ec._ORIG_MEASURE(
        gray, ys, cx, head_y=cy, exclude_boxes=None, head_box_x=None).get(side, [])]
    walked = {round(c["y"], 1): c["passed"] for c in tr["clears"]}
    final = tr["final_ladder"]
    drops = []
    for y in bare:
        if any(abs(y - f) <= 0.35 * sp for f in final):
            continue
        near_w = [p for w_, p in walked.items() if abs(w_ - y) <= 0.35 * sp]
        why = ("excluded (other head / accidental ink)" if not near_w
               else "clears_box" if not near_w[0] else "collapse/derive")
        drops.append((y, why))
    ext = [y0, y1] + list(final) + [d[0] for d in drops]
    if sign < 0:
        lo_y, hi_y = min(ext) - 1.5 * sp, edge + 1.2 * sp
    else:
        lo_y, hi_y = edge - 1.2 * sp, max(ext) + 1.5 * sp
    cx0, cx1 = int(cx - 6 * sp), int(cx + 4 * sp)
    cy0, cy1 = int(max(0, lo_y)), int(min(gray.shape[0], hi_y))
    crop = gray[cy0:cy1, cx0:cx1]
    img = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    img = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_NEAREST)
    ov = img.copy()
    mm = cv2.resize(mask[cy0:cy1, cx0:cx1].astype(np.uint8), None, fx=SCALE, fy=SCALE,
                    interpolation=cv2.INTER_NEAREST).astype(bool)
    ov[mm] = YELLOW
    img = cv2.addWeighted(ov, 0.7, img, 0.3, 0)

    def P(x, y):
        return int(round((x - cx0) * SCALE)), int(round((y - cy0) * SCALE))

    for y in ys:  # staff line ticks at the left margin
        cv2.line(img, P(cx0, y), P(cx0 + 0.5 * sp, y), CYAN, 2)
    for _s, (ax0, ay0, ax1, ay1) in h["acc"]:
        if ax1 >= cx0 and ax0 <= cx1 and ay1 >= cy0 and ay0 <= cy1:
            cv2.rectangle(img, P(ax0, ay0), P(ax1, ay1), PURPLE, 2)
    cv2.rectangle(img, P(x0, y0), P(x1, y1), RED, 2)
    report = []
    for i, y in enumerate(final):
        ink = row_ink(gray, y, cx, sp, thr)
        off = [row_ink(gray, y + d * 0.5 * sp, cx, sp, thr) for d in (-1, 1)]
        cv2.line(img, P(cx - 2 * sp, y), P(cx + 2 * sp, y), ORANGE, 2)
        cv2.putText(img, f"L{i+1} y{y:.0f}", P(cx + 2.05 * sp, y + 2), 0, 0.5, ORANGE, 1)
        report.append(f"kept L{i+1} y={y:.1f} ink={ink:.2f} off={off[0]:.2f}/{off[1]:.2f}")
    for y, why in drops:
        ink = row_ink(gray, y, cx, sp, thr)
        off = [row_ink(gray, y + d * 0.5 * sp, cx, sp, thr) for d in (-1, 1)]
        for xx in np.arange(cx - 2 * sp, cx + 2 * sp, 6):
            cv2.line(img, P(xx, y), P(xx + 3, y), MAGENTA, 2)
        cv2.putText(img, f"drop y{y:.0f} {why[:14]}", P(cx - 6 * sp + 2, y - 2), 0, 0.45, MAGENTA, 1)
        report.append(f"drop y={y:.1f} ({why}) ink={ink:.2f} off={off[0]:.2f}/{off[1]:.2f}")
    head = f"{h['subject']} we={pos} ref={h['truth']}  sp={sp:.1f}px"
    bar = np.full((70, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, head, (4, 18), 0, 0.55, (0, 0, 0), 1)
    cv2.putText(bar, reason[:95], (4, 38), 0, 0.42, (60, 60, 60), 1)
    cv2.putText(bar, f"acc boxes: {[a['gap_sp'] for a in ac.left_accidentals(h)]} sp left",
                (4, 58), 0, 0.42, (60, 60, 60), 1)
    note = np.full((60, img.shape[1], 3), 255, np.uint8)
    for i, ln in enumerate(CAUSE.get(h["subject"], []) if ARM_KW is None else []):
        cv2.putText(note, ln, (4, 16 + 18 * i), 0, 0.42, (0, 0, 160), 1)
    return np.vstack([bar, img, note]), report, dict(sp=sp, cx=cx, cy=cy, box=h["box"],
                                              final=final, drops=drops, bare=bare)


def main():
    ec.install()
    lg.derive_far_head_step = ac._derive
    global ARM_KW, OUT
    subs = [a for a in sys.argv[1:] if a.startswith("glyph/")] or SUBJECTS
    for a in sys.argv[1:]:
        if a.startswith("--arm="):
            import score_accidental as sa  # noqa: E402
            ARM_KW = sa.ARMS[a[6:]]
            OUT = OUT / ("arm_" + a[6:].replace("+", "_"))
    heads = {h["subject"]: h for h in ec.load_heads("beethoven5-litolff")}
    tiles = []
    for s in subs:
        h = heads[s]
        pos, reason, tr = ac.read(h, record=True, **(ARM_KW or {}))
        t, rep, meta = tile(h, pos, reason, tr)
        print(s, "we", pos, "ref", h["truth"], "|", reason)
        print("  box", [round(v, 1) for v in h["box"]], "staff", [round(v, 1) for v in h["lines"]],
              "sp %.2f" % meta["sp"])
        print("  bare candidates", [round(v, 1) for v in meta["bare"]], "final",
              [round(v, 1) for v in meta["final"]])
        for r in rep:
            print("   ", r)
        tiles.append(t)
    OUT.mkdir(parents=True, exist_ok=True)
    for s, t in zip(subs, tiles):
        cv2.imwrite(str(OUT / (s.replace("/", "_") + ".png")), t)
    H = max(t.shape[0] for t in tiles)
    W = max(t.shape[1] for t in tiles)
    pad = [np.pad(t, ((0, H - t.shape[0]), (0, W - t.shape[1] + 8), (0, 0)),
                  constant_values=255) for t in tiles]
    cv2.imwrite(str(OUT / "accidental_sheet.png"), np.hstack(pad))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
