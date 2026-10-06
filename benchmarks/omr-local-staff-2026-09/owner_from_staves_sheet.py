"""lane-owner-from-staves (2026-10-06): ONE sheet of 12 seeded OWNER CHANGES the staves tier makes (flag ON vs OFF, one
tree, `owner_from_staves_ab.py`), each drawn on the print with BOTH staves' five lines at the head's own x.

    python3 benchmarks/omr-local-staff-2026-09/owner_from_staves_sheet.py DOC REC.record.json AB.json OUT.png [seed]
    (DOC: litolff | brahms; AB.json: the A/B file run with AB_DROP_OWNER_LEDGERS=1 = the DEFAULT tree's decisions)

Colours: ORANGE box = the head as the detector boxed it (the copy filed on the OLD owner's cell). BLUE lines = the OLD
owner's five lines. CYAN lines = the NEW owner's five lines. Both measured LOCALLY off the page raster at the head's x
(`far_head_reader.frame_lines_for_head`), never the page-wide fit. Each tile says in words where the note lies on the
new owner's lines. Every drawn line is re-measured against pixel rows in columns clear of the head (a control that can
fail: the sheet reports how many land within 2 px of an ink row).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import owner_from_staves_count as C  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402
from tools.library.score_library import library_root  # noqa: E402
from tools.omr.annotate import far_head_reader as FH  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

PDFS = {
    "litolff": library_root() / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": library_root() / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
ORANGE, BLUE, CYAN = (0, 140, 255), (255, 80, 0), (200, 200, 0)
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


def remeasure(gray, y, x0, x1, thr):
    x0, x1 = max(0, x0), min(gray.shape[1], x1)
    if x1 <= x0:
        return None
    rows = [r for r in range(int(y) - 6, int(y) + 7)
            if 0 <= r < gray.shape[0] and (gray[r, x0:x1] <= thr).mean() >= 0.5]
    if not rows:
        return None
    runs, cur = [], [rows[0]]
    for r in rows[1:]:
        if r == cur[-1] + 1:
            cur.append(r)
        else:
            runs.append(cur)
            cur = [r]
    runs.append(cur)
    return abs(float(np.mean(min(runs, key=lambda c: abs(np.mean(c) - y)))) - y)


def where_it_lies(cy, lines):
    top, bot = lines[0], lines[-1]
    half = (bot - top) / 8.0
    pos = (cy - top) / half
    k = int(round(pos))
    if pos < -0.5 or pos > 8.5:
        return f"lies {abs(pos if pos < 0 else pos - 8):.1f} half-steps OUTSIDE it", pos
    if abs(pos - k) <= 0.35:
        if k % 2 == 0:
            return f"lies on its {ORD[k // 2 + 1]} line (from top)", pos
        return f"lies in its {ORD[(k + 1) // 2]} space (from top)", pos
    return f"lies between line and space ({pos:.1f} half-steps down)", pos


def stkey(s):
    p = s.split("/")
    return f"{int(p[3])} (system {int(p[2])})"


def tile(no, subj, row, staves, boxes, gray, checks):
    p, sy, st, c, gi = C.parse(subj)
    new_key, old_key = row["on"]["value"], row["off"]["value"]
    _name, bb = boxes[subj]
    cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
    fl = {}
    for key in (old_key, new_key):
        S = staves[key]
        fl[key] = FH.frame_lines_for_head(gray, S["lines"], bb)
        assert len(fl[key]) == 5
    sp = (fl[new_key][-1] - fl[new_key][0]) / 4.0
    scale = 30.0 / sp
    ys = [y for key in fl for y in fl[key]] + [bb[1], bb[3]]
    xa, xb = int(cx - 4.5 * sp), int(cx + 4.5 * sp)
    ya, yb = int(min(ys) - 1.0 * sp), int(max(ys) + 1.0 * sp)
    xa, ya = max(0, xa), max(0, ya)
    crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    W = crop.shape[1]
    thr = min(int(np.percentile(gray[ya:yb, xa:xb], 25) + 40), 140)
    far_cols = ((int(cx - 4.2 * sp), int(cx - 1.2 * sp)), (int(cx + 1.2 * sp), int(cx + 4.2 * sp)))

    def Y(y):
        return int(round((y - ya) * scale))

    for key, colour in ((old_key, BLUE), (new_key, CYAN)):
        for li, y in enumerate(fl[key]):
            cv2.line(crop, (0, Y(y)), (W - 1, Y(y)), colour, 2)
            offs = [remeasure(gray, y, *cols, thr) for cols in far_cols]
            offs = [o for o in offs if o is not None]
            checks.append((no, "old" if key == old_key else "new", li, None if not offs else round(min(offs), 1)))
    cv2.rectangle(crop, (int(round((bb[0] - xa) * scale)), Y(bb[1])), (int(round((bb[2] - xa) * scale)), Y(bb[3])), ORANGE, 2)
    where, pos = where_it_lies(cy, fl[new_key])
    how = ("duplicate copy dropped (new owner has its own box)" if row["on"].get("owner_box")
           else "owner has no box: copy dropped, none written")
    good = sum(1 for c in checks if c[0] == no and c[3] is not None and c[3] <= 2.0)
    lines = [f"{no}  moved from staff {stkey(old_key)} to staff {stkey(new_key)}  (p{p})",
             f"the note {where}",
             how,
             f"lines re-measured vs pixel rows: {good} of 10 within 2 px"]
    return crop, lines, pos


def main(doc, rec_path, ab_path, out, seed=20261006):
    ab = json.load(open(ab_path))["results"]
    changed = sorted(k for k, r in ab.items() if r["off"]["value"] != r["on"]["value"])
    picks = random.Random(seed).sample(changed, min(12, len(changed)))
    rec = load_record(rec_path)
    staves, boxes, _pos, _bands, _verdict = C.collect(rec)
    grays = {}
    checks, cells = [], []
    TW = 420
    for no, subj in enumerate(picks, 1):
        page = C.parse(subj)[0]
        if page not in grays:
            grays[page] = cv2.cvtColor(render_page_matching_gather(PDFS[doc], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        crop, lines, _pos = tile(no, subj, ab[subj], staves, boxes, grays[page], checks)
        H = crop.shape[0]
        canvas = np.full((H + 80, TW, 3), 255, np.uint8)
        w = min(TW, crop.shape[1])
        canvas[:H, :w] = crop[:, :w]
        for i, t in enumerate(lines):
            cv2.putText(canvas, t, (4, H + 16 + 16 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0) if i < 2 else ((0, 0, 160) if i == 2 else (90, 90, 90)), 1, cv2.LINE_AA)
        cells.append(canvas)
        print(no, doc, subj, "|", lines[1], "|", "twin" if ab[subj]["on"].get("owner_box") else "no box on the new owner")
    rows_img = []
    for r0 in range(0, len(cells), 4):
        grp = cells[r0:r0 + 4]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < 4:
            grp.append(np.full((h, TW + 8, 3), 255, np.uint8))
        rows_img.append(np.hstack(grp))
    body = np.vstack(rows_img)
    legend_lines = ["ORANGE box: the head as the detector boxed it, filed on the OLD owner's cell.   BLUE: the old owner's five lines.   CYAN: the new owner's five lines.",
                    "Both staves' lines measured locally at the head's x off the page raster. Words under each tile say where the note lies on the NEW owner's lines.",
                    f"12 seeded (seed {seed}) of {len(changed)} owner changes, default tree, flag OMR_OWNER_FROM_STAVES ON vs OFF. Not yet adjudicated by Sean."]
    legend = np.full((26 * len(legend_lines) + 6, body.shape[1], 3), 255, np.uint8)
    for i, t in enumerate(legend_lines):
        cv2.putText(legend, t, (8, 20 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, np.vstack([legend, body]))
    ok = [c for c in checks if c[3] is not None and c[3] <= 2.0]
    bad = [c for c in checks if c[3] is not None and c[3] > 2.0]
    none = [c for c in checks if c[3] is None]
    print(f"drawn lines {len(checks)} | within 2 px of an ink row: {len(ok)} | off by more than 2 px: {bad} | no ink row: {none}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 20261006)
