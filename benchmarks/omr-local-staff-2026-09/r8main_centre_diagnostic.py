#!/usr/bin/env python3
"""lane-ledger-r8-main (2026-10-04): DIAGNOSTIC ONLY -- not a result, not a
headline. For the Litolff heads `score_four_causes_cd` leaves undecided
(rungs_after = abstain), trace each head's centre row from its OWN ink
and ask the middle-row probe the same question with that centre
(`head_center_y`) instead of the box middle. Reports per head: box,
box-middle, traced centre, what the probe says both ways, and the
position the reader returns with the traced centre. Draws a crop (x3):
red = detector box, green = the supplied centre row, orange = rungs
`measure_ledger_rungs` finds from the ink. Prints the page's own ink
darkness at each drawn row so the lines can be verified to sit on ink.

    OMRNED_PYTHON=... python3 benchmarks/omr-local-staff-2026-09/r8main_centre_diagnostic.py [subject ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import score_truth_set_rungs as s  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

DOC = "beethoven5-litolff"
OUT = REPO / "out/print/ledgers/r8main"
SCALE = 3


def trace_centre(gray, box, spacing):
    """Centre row of the head's ink in a narrow column band at the box's
    x middle: the vertical run of rows with >50% dark pixels that
    CONTAINS the box's own middle row, bridging gaps up to 0.3 spacing
    (a hollow head's hole). Returns (centre, top, bottom) or None."""
    x0, y0, x1, y1 = box
    w = x1 - x0
    cx = (x0 + x1) / 2.0
    ya = int(y0 - 1.5 * spacing)
    yb = int(y1 + 1.5 * spacing)
    band = gray[ya:yb, int(cx - 0.2 * w):int(cx + 0.2 * w) + 1]
    dark = (band < 128).mean(axis=1) > 0.5
    mid = int(round((y0 + y1) / 2.0)) - ya
    if not (0 <= mid < len(dark)):
        return None
    bridge = int(0.3 * spacing)
    # grow from the box middle (or the nearest dark row to it)
    cand = [i for i in range(len(dark)) if dark[i]]
    if not cand:
        return None
    seed = min(cand, key=lambda i: abs(i - mid))
    top = bot = seed
    gap = 0
    i = seed
    while i > 0:
        i -= 1
        if dark[i]:
            top, gap = i, 0
        else:
            gap += 1
            if gap > bridge:
                break
    gap = 0
    i = seed
    while i < len(dark) - 1:
        i += 1
        if dark[i]:
            bot, gap = i, 0
        else:
            gap += 1
            if gap > bridge:
                break
    return (ya + (top + bot) / 2.0, float(ya + top), float(ya + bot))


def ink_at(gray, box, y):
    x0, _y0, x1, _y1 = box
    w = x1 - x0
    cx = (x0 + x1) / 2.0
    row = gray[int(round(y)), int(cx - 0.2 * w):int(cx + 0.2 * w) + 1]
    return float((row < 128).mean())


def stub_rows(gray, box, y, spacing):
    """Verification the filled head cannot give (its own column is 100%
    ink): ink at a column just LEFT of the box (a ledger's stub), rows
    y-4..y+4. Returns (row of the darkest stub pixel, dark rows list)."""
    x0 = box[0]
    col = gray[int(round(y)) - 4:int(round(y)) + 5, int(x0 - 0.5 * spacing)]
    return [int(round(y)) - 4 + i for i, v in enumerate(col) if v < 128]


def main(argv):
    want = set(argv)
    loaded = s.ts.load_doc(DOC)
    rows = s._far_head_rows(DOC, loaded)
    rec = loaded["rec"]
    pages = s.PageCache(loaded["cfg"])
    boxes_by_page = s._notehead_boxes_by_page(rec)
    acc_by_page = s._accidental_boxes_by_page(rec)
    base = s.score_doc(DOC, four_causes_cd=True)
    abstain = {h["subject"] for h in base["per_head"] if h["v_after"] == "abstain"}
    targets = want or abstain
    OUT.mkdir(parents=True, exist_ok=True)
    for r in rows:
        sub = r["subject"]
        if sub not in targets:
            continue
        gray = pages.get(r["page"])
        box = tuple(r["page_box"])
        gl = [float(y) for y in rec.obs(Q.STAFF_LINES, r["staff_key"])[-1]["value"]]
        lines = s.frame_lines_for_head(gray, gl, box)
        sp = (lines[-1] - lines[0]) / 4.0
        x0, y0, x1, y1 = box
        mid = (y0 + y1) / 2.0
        tr = trace_centre(gray, box, sp)
        others = [b for (s_, b) in boxes_by_page.get(r["page"], []) if s_ != sub]
        others += [b for (_s, b) in acc_by_page.get(r["page"], [])]
        ev_box = lg.head_middle_rung_evidence(gray, box, sp, others)
        ev_ctr = (lg.head_middle_rung_evidence(gray, box, sp, others,
                                               head_center_y=tr[0])
                  if tr else None)
        kw = dict(page_accidental_boxes=acc_by_page.get(r["page"], []),
                  four_causes_cd=True)
        pos0, why0 = s.reader_absolute_position(
            gray, lines, box, sub, boxes_by_page.get(r["page"], []), **kw)
        pos1, why1 = (s.reader_absolute_position(
            gray, lines, box, sub, boxes_by_page.get(r["page"], []),
            head_center_y=tr[0], **kw) if tr else (None, "no trace"))
        truth = r["truth_pitches"]
        side = "above" if mid < lines[0] else "below"
        rungs = lg.measure_ledger_rungs(
            gray, lines, (x0 + x1) / 2.0, head_y=mid, exclude_boxes=others,
            head_box_x=(x0, x1)).get(side, [])
        print(f"== {sub}  truth_pos={[h['truth_pos'] for h in base['per_head'] if h['subject']==sub]}")
        print(f"   box={[round(v,1) for v in box]} box_mid={mid:.1f} spacing={sp:.1f}")
        if tr:
            print(f"   traced ink run rows {tr[1]:.0f}..{tr[2]:.0f} -> centre {tr[0]:.1f} "
                  f"(offset from box middle {tr[0]-mid:+.1f}px)")
        print(f"   probe@box_mid -> {ev_box}; probe@traced_centre -> {ev_ctr}")
        print(f"   reader@box_mid -> {pos0} ({why0})")
        print(f"   reader@traced_centre -> {pos1} ({why1})")
        print(f"   rungs from ink ({side}): {[round(v,1) for v in rungs]}")
        # ---- crop, x3
        pad_x, pad_y = int(4 * sp), int(3 * sp)
        cx0, cx1 = int(x0 - pad_x), int(x1 + pad_x)
        cy0, cy1 = int(min(y0, mid) - pad_y), int(max(y1, mid) + pad_y)
        cy0 = min(cy0, int(lines[0]) - int(0.5 * sp)) if side == "above" else cy0
        cy1 = max(cy1, int(lines[-1]) + int(0.5 * sp)) if side == "below" else cy1
        crop = Image.fromarray(gray[cy0:cy1, cx0:cx1]).convert("RGB")
        crop = crop.resize((crop.width * SCALE, crop.height * SCALE), Image.NEAREST)
        d = ImageDraw.Draw(crop)

        def Y(y):
            return (y - cy0) * SCALE

        def X(x):
            return (x - cx0) * SCALE
        for ly in lines:
            if cy0 <= ly <= cy1:
                d.line([(0, Y(ly)), (14, Y(ly))], fill=(120, 120, 255), width=1)
        for ry in rungs:
            d.line([(0, Y(ry)), (crop.width, Y(ry))], fill=(255, 140, 0), width=1)
            print(f"   orange rung y={ry:.1f}: dark rows at the left stub column "
                  f"(x0-0.5sp), y-4..y+4: {stub_rows(gray, box, ry, sp)}")
        d.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline=(255, 0, 0), width=1)
        if tr:
            d.line([(X(x0) - 20, Y(tr[0])), (X(x1) + 20, Y(tr[0]))],
                   fill=(0, 200, 0), width=1)
            print(f"   green centre y={tr[0]:.1f}: traced run {tr[1]:.0f}..{tr[2]:.0f} "
                  f"(run height {(tr[2]-tr[1])/sp:.2f} sp; a run over ~1.6 sp merged "
                  f"with other ink and its centre is NOT usable)")
        name = sub.replace("/", "-")
        path = OUT / f"{DOC}-{name}.png"
        crop.save(path)
        print(f"   crop: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
