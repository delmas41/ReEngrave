#!/usr/bin/env python3
"""lane-ledger-exclusion (2026-10-04): the crops.  One row per head, BEFORE
(control) on the left and AFTER (an arm) on the right, x6, real print.

red = the detector's head box; grey thin = every OTHER detector notehead box
near it, labelled with the staff that owns it (`s8` = staff 8); purple thin =
accidental boxes; yellow = ink `_exclude_other_heads_ink` blanked in that arm;
orange solid = rungs the reader COUNTED (final ladder); magenta dashed =
rungs the bare ink offers that the reader did NOT count (label = why); cyan
ticks = the staff lines at the head's x.  Every drawn line is pixel-checked:
ink fraction on its row within +-1.1 sp of the head's x vs the rows 0.5 sp
above / below (printed under each panel).

    python3 benchmarks/omr-local-staff-2026-09/exclusion_sheet.py [--arm NAME] [subject...]
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
import score_exclusion as se  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT = HERE.parents[1] / "out" / "print" / "ledgers" / "exclusion"
SCALE = 6
# tiles 2, 7, 9 of Sean's sheet, then the other heads the arm changes
SUBJECTS = ["glyph/3/0/0/2/4", "glyph/3/0/7/4/3", "glyph/3/0/7/7/0",
            "glyph/3/0/0/7/1", "glyph/3/0/0/7/2"]
TILE = {"glyph/3/0/0/2/4": "tile 2", "glyph/3/0/7/4/3": "tile 7", "glyph/3/0/7/7/0": "tile 9",
        "glyph/3/0/0/7/1": "tile 5", "glyph/3/0/0/7/2": "tile 6"}
NOTE = {
    "glyph/3/0/0/2/4": "rule: one_sided -- the 2nd ledger (y416) juts right out of neighbour 2/9 only; still wrong: the head box is too low (other lane).",
    "glyph/3/0/7/4/3": "rule: same_ink_other_staff -- s6 4/3 overlaps this head's box 63%: the same ink; its blanking (yellow, left) erased the ledger through the head.",
    "glyph/3/0/7/7/0": "rule: same_ink_other_staff -- s8 7/1 overlaps this head's box 59%: the same ink; its blanking erased the middle row of the head.",
    "glyph/3/0/0/7/1": "rules: connected (drops the false y434 row) + one_sided (keeps the lower head's through-ledger, juts RIGHT at y427-429). UNCONFIRMED: tip or ledger?",
    "glyph/3/0/0/7/2": "rule: drop_rungs_beyond_head (lane-ledger-accidental): the walk's L2/L3 are drawn, but they lie beyond the head's far edge and are not counted for it.",
}
RED, PURPLE, ORANGE, MAGENTA, YELLOW, CYAN, GREY = (
    (0, 0, 255), (200, 0, 160), (0, 140, 255), (255, 0, 255), (0, 230, 255), (255, 255, 0),
    (120, 120, 120))


def row_ink(gray, y, cx, sp, thr):
    x0, x1 = int(cx - 1.1 * sp), int(cx + 1.1 * sp)
    r = gray[int(round(y)), x0:x1]
    return float((r <= thr).mean())


def arm_rules(kw):
    return dict(connected=kw.get("connected_continuation", False),
                own_box=None, one_sided=kw.get("one_sided_jut", False))


def blanked_mask(h, kw, sign, cx, sp):
    gray = h["gray"]
    ys = sorted(h["lines"])
    edge_y = ys[0] if sign < 0 else ys[-1]
    near = edge_y + sign * 0.30 * sp
    far = edge_y + sign * lg.MAX_SPACES * sp
    yy0, yy1 = int(max(0, min(near, far))), int(min(gray.shape[0], max(near, far)))
    x0 = int(max(0, cx - lg.WINDOW_HALF_WIDTH_SPACES * sp))
    x1 = int(min(gray.shape[1], cx + lg.WINDOW_HALF_WIDTH_SPACES * sp))
    win = gray[yy0:yy1, x0:x1]
    thr = lg._otsu_threshold(win)
    raw = win <= thr
    others = lg.exclusion_boxes_for(
        h["subject"], h["box"], h["boxes"], h["acc"],
        drop_same_ink_other_staff=kw.get("drop_same_ink_other_staff", False))
    with lg.exclusion_rules(**arm_rules(kw)):
        ex = lg._exclude_other_heads_ink(raw, others, x0, yy0, sp, gray, thr)
    m = np.zeros(gray.shape, bool)
    m[yy0:yy1, x0:x1] = raw & ~ex
    return m, thr, others


def panel(h, arm, kw, extent):
    gray = h["gray"]
    x0, y0, x1, y1 = h["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ys = sorted(h["lines"])
    sp = (ys[-1] - ys[0]) / 4
    sign = -1.0 if cy < ys[0] else 1.0
    side = "above" if sign < 0 else "below"
    edge = ys[0] if sign < 0 else ys[-1]
    pos, reason, tr = ac.read(h, record=True, **kw)
    mask, thr, used = blanked_mask(h, kw, sign, cx, sp)
    bare = [float(v) for v in ec._ORIG_MEASURE(
        gray, ys, cx, head_y=cy, exclude_boxes=None, head_box_x=None).get(side, [])]
    walked = {round(c["y"], 1): c["passed"] for c in tr["clears"]}
    final = tr["final_ladder"]
    drops = []
    for y in bare:
        if any(abs(y - f) <= 0.35 * sp for f in final):
            continue
        near_w = [p for w_, p in walked.items() if abs(w_ - y) <= 0.35 * sp]
        why = ("blanked (other head/accidental)" if not near_w
               else "clears_box" if not near_w[0] else "collapse/derive")
        drops.append((y, why))
    lo_y, hi_y = extent
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

    for y in ys:
        cv2.line(img, P(cx0, y), P(cx0 + 0.5 * sp, y), CYAN, 2)
    for _s, (ax0, ay0, ax1, ay1) in h["acc"]:
        if ax1 >= cx0 and ax0 <= cx1 and ay1 >= cy0 and ay0 <= cy1:
            cv2.rectangle(img, P(ax0, ay0), P(ax1, ay1), PURPLE, 1)
    for sub, (bx0, by0, bx1, by1) in h["boxes"]:
        if sub == h["subject"]:
            continue
        if bx1 >= cx0 and bx0 <= cx1 and by1 >= cy0 and by0 <= cy1:
            cv2.rectangle(img, P(bx0, by0), P(bx1, by1), GREY, 1)
            cv2.putText(img, "s" + sub.split("/")[3] + " " + sub.split("/")[-2] + "/" + sub.split("/")[-1],
                        P(bx1 + 1, by0 + 6), 0, 0.4, GREY, 1)
    cv2.rectangle(img, P(x0, y0), P(x1, y1), RED, 2)
    report = []
    for i, y in enumerate(final):
        ink = row_ink(gray, y, cx, sp, thr)
        off = [row_ink(gray, y + d * 0.5 * sp, cx, sp, thr) for d in (-1, 1)]
        cv2.line(img, P(cx - 2 * sp, y), P(cx + 2 * sp, y), ORANGE, 2)
        cv2.putText(img, f"L{i+1} y{y:.0f}", P(cx + 2.05 * sp, y + 2), 0, 0.5, ORANGE, 1)
        report.append(f"counted L{i+1} y={y:.1f} ink={ink:.2f} off={off[0]:.2f}/{off[1]:.2f}")
    for y, why in drops:
        ink = row_ink(gray, y, cx, sp, thr)
        off = [row_ink(gray, y + d * 0.5 * sp, cx, sp, thr) for d in (-1, 1)]
        for xx in np.arange(cx - 2 * sp, cx + 2 * sp, 6):
            cv2.line(img, P(xx, y), P(xx + 3, y), MAGENTA, 2)
        cv2.putText(img, f"thrown y{y:.0f} {why}", P(cx - 6 * sp + 2, y - 2), 0, 0.45, MAGENTA, 1)
        report.append(f"thrown y={y:.1f} ({why}) ink={ink:.2f} off={off[0]:.2f}/{off[1]:.2f}")
    verdict = ec.verdict(pos, h["truth"])
    bar = np.full((54, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, f"{arm}: we={pos} ({verdict})  ref={h['truth']}", (4, 18), 0, 0.6,
                (0, 0, 0) if verdict == "right" else (0, 0, 190), 1)
    cv2.putText(bar, reason[:100], (4, 40), 0, 0.4, (60, 60, 60), 1)
    rep = np.full((18 * max(1, len(report)) + 8, img.shape[1], 3), 255, np.uint8)
    for i, ln in enumerate(report):
        cv2.putText(rep, ln, (4, 16 + 18 * i), 0, 0.42, (0, 0, 0), 1)
    return np.vstack([bar, img, rep]), dict(pos=pos, verdict=verdict, report=report,
                                            final=final, drops=drops, ys=ys, sp=sp, sign=sign, edge=edge)


def main():
    ec.install()
    lg.derive_far_head_step = ac._derive
    arm = "conn+same+one+drop"
    for a in sys.argv[1:]:
        if a.startswith("--arm="):
            arm = a[6:]
    subs = [a for a in sys.argv[1:] if a.startswith("glyph/")] or SUBJECTS
    heads = {h["subject"]: h for h in ec.load_heads("beethoven5-litolff")}
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in subs:
        h = heads[s]
        # one common vertical extent so before/after line up
        x0, y0, x1, y1 = h["box"]
        ys = sorted(h["lines"])
        sp = (ys[-1] - ys[0]) / 4
        sign = -1.0 if (y0 + y1) / 2 < ys[0] else 1.0
        pre = [ac.read(h, record=True, **kw)[2]["final_ladder"] for kw in (se.ARMS["control"], se.ARMS[arm])]
        ext_y = [y0, y1] + [y for f in pre for y in f]
        edge = ys[0] if sign < 0 else ys[-1]
        if sign < 0:
            ext = (min(ext_y) - 1.5 * sp, edge + 1.2 * sp)
        else:
            ext = (edge - 1.2 * sp, max(ext_y) + 1.5 * sp)
        (pb, mb), (pa, ma) = [panel(h, n, se.ARMS[n], ext) for n in ("control", arm)]
        H = max(pb.shape[0], pa.shape[0])
        pad = lambda p: np.pad(p, ((0, H - p.shape[0]), (0, 10), (0, 0)), constant_values=255)  # noqa: E731
        title = np.full((30, pb.shape[1] + pa.shape[1] + 20, 3), 255, np.uint8)
        cv2.putText(title, f"{TILE.get(s, '')}  {s}   BEFORE (control)  ->  AFTER ({arm})   ref {h['truth']}",
                    (4, 21), 0, 0.65, (0, 0, 0), 2)
        note = np.full((22, title.shape[1], 3), 255, np.uint8)
        cv2.putText(note, NOTE.get(s, ""), (4, 16), 0, 0.45, (0, 0, 160), 1)
        row = np.vstack([title, np.hstack([pad(pb), pad(pa)]), note])
        cv2.imwrite(str(OUT / (s.replace("/", "_") + ".png")), row)
        rows.append(row)
        print(s, TILE.get(s, ""), "before", mb["pos"], mb["verdict"], "-> after", ma["pos"], ma["verdict"], "ref", h["truth"])
        for tag, m in (("before", mb), ("after ", ma)):
            for r in m["report"]:
                print("   ", tag, r)
    W = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((0, 12), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    cv2.imwrite(str(OUT / "exclusion_sheet.png"), sheet)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
