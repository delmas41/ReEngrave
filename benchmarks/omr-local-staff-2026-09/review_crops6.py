#!/usr/bin/env python3
"""lane-ledger-rungs round 6 (2026-10-0x) -- diagnostic crops for the
stacked-thirds convention (DECISIONS 2026-10-0x, Sean: "when there are
multiple note heads stacked in thirds and neither of them has a line
through them then there must be a line between them and to go looking
for it").

Measured result (FINDINGS.md "round 6"): the real-score table is
UNCHANGED from round 5 -- none of the three real chord stacks this round
targets (`glyph/3/0/0/2/4`+`/2/9`, `/2/1`+`/2/3`, `/6/1`+`/6/2`) satisfy
the convention's own "neither has a line through it" guard, because
their CURRENT (pre-round-6) reading already registers a through-head
rung on at least one side -- itself a separate, pre-existing confound
(an oversized/merged Litolff detector box whose own widest row sits near
its geometric centre). These crops show exactly that: both heads of
each named pair, their real measured rungs, and the pair's own midpoint
(drawn dashed where the convention's own guard would apply it, SKIPPED
and labelled where an existing through-head rung blocks it per Sean's
own stated rule).

Also includes every chord pair the convention's guard DOES fire on
across the whole gathered movement (found by `heads_are_a_third_apart` +
`has_through_head_rung`, 9 on Litolff + 22 on Brahms) that falls within
EITHER document's truth-scored population -- reported as none this
round (the headline table is unchanged for that reason, not because the
mechanism never fires: it fires on real ink, just not on a currently
truth-scorable head).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers" / "r6"

RED = (0, 0, 255)
GREEN = (0, 170, 0)
ORANGE = (30, 140, 255)
PURPLE = (200, 0, 200)
BLACK = (0, 0, 0)
MIN_WIDTH = 600

NAMED_PAIRS = [
    ("beethoven5-litolff", "glyph/3/0/0/2/4", "glyph/3/0/0/2/9"),
    ("beethoven5-litolff", "glyph/3/0/0/2/1", "glyph/3/0/0/2/3"),
    ("beethoven5-litolff", "glyph/3/0/0/6/1", "glyph/3/0/0/6/2"),
]


def _own_rungs(gray, ys, box, subject, page_boxes, side):
    cx = (box[0] + box[2]) / 2.0
    cy = (box[1] + box[3]) / 2.0
    others = [b for (s, b) in page_boxes if s != subject]
    return lg.measure_ledger_rungs(
        gray, ys, cx, head_y=cy, exclude_boxes=others,
        head_box_x=(box[0], box[2]),
    ).get(side, [])


def render_pair_crop(gray, box_a, box_b, sub_a, sub_b, ys, spacing, out_path,
                      label_lines):
    cy_a, cy_b = (box_a[1] + box_a[3]) / 2.0, (box_b[1] + box_b[3]) / 2.0
    top, bottom = ys[0], ys[-1]
    side = "above" if cy_a < top else "below"
    cx_mid = (box_a[0] + box_a[2] + box_b[0] + box_b[2]) / 4.0

    margin = 1.6 * spacing
    wy0 = min(cy_a, cy_b, top) - margin
    wy1 = max(cy_a, cy_b, bottom) + margin
    wx0 = cx_mid - 3.2 * spacing
    wx1 = cx_mid + 3.2 * spacing
    native_w = max(1, int(round(wx1 - wx0)))
    native_h = max(1, int(round(wy1 - wy0)))
    scale = max(3, -(-MIN_WIDTH // native_w))
    out_w, out_h = native_w * scale, native_h * scale

    h, w = gray.shape
    px0, py0 = max(0, int(wx0)), max(0, int(wy0))
    px1, py1 = min(w, int(wx0) + native_w), min(h, int(wy0) + native_h)
    canvas = np.full((native_h, native_w, 3), 255, dtype=np.uint8)
    if px1 > px0 and py1 > py0:
        patch = cv2.cvtColor(gray[py0:py1, px0:px1], cv2.COLOR_GRAY2BGR)
        canvas[py0 - int(wy0):py1 - int(wy0),
              px0 - int(wx0):px1 - int(wx0)] = patch
    big = cv2.resize(canvas, (out_w, out_h), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return (int(round((px - wx0) * scale)), int(round((py - wy0) * scale)))

    for ly in ys:
        if ly < wy0 or ly > wy1:
            continue
        _, by = to_big(wx0, ly)
        cv2.line(big, (0, by), (out_w, by), GREEN, 1)

    for box, colour in ((box_a, RED), (box_b, RED)):
        bx0, by0 = to_big(box[0], box[1])
        bx1, by1 = to_big(box[2], box[3])
        cv2.rectangle(big, (bx0, by0), (bx1, by1), colour, max(1, scale // 3))

    TEXT_W = max(out_w, 1100)
    text_h = 20 + len(label_lines) * 22 + 10
    tile = np.full((out_h + text_h, TEXT_W, 3), 255, dtype=np.uint8)
    tile[:out_h, :out_w, :] = big
    for i, t in enumerate(label_lines):
        cv2.putText(tile, t[:170], (6, out_h + 20 + i * 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.48, BLACK, 1, cv2.LINE_AA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), tile)
    return big, to_big, scale


def draw_rung(big, to_big, scale, y, x_lo, x_hi, dashed: bool):
    _, by = to_big(0, y)
    bx0, _ = to_big(x_lo, y)
    bx1, _ = to_big(x_hi, y)
    if not dashed:
        cv2.line(big, (max(0, bx0), by), (bx1, by), ORANGE, max(2, scale // 2))
    else:
        x = bx0
        while x < bx1:
            cv2.line(big, (x, by), (min(bx1, x + scale), by), PURPLE,
                    max(2, scale // 2))
            x += 2 * scale


def main() -> int:
    index_lines = [
        "# lane-ledger-rungs round 6 diagnostic crops (2026-10-0x)", "",
        "Stacked-thirds convention (DECISIONS 2026-10-0x). Measured "
        "result: the real-score table is UNCHANGED from round 5 -- see "
        "FINDINGS.md for why (the 3 named pairs' current reading already "
        "shows a through-head rung on at least one side, blocking the "
        "convention's own guard). These are diagnostic crops, not "
        "changed-answer crops.", "",
    ]
    tiles = []

    for doc_id, sub_a, sub_b in NAMED_PAIRS:
        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        boxes_by_page = score._notehead_boxes_by_page(rec)

        box_obs_a = rec.obs(Q.GLYPH_BOX, sub_a)
        box_obs_b = rec.obs(Q.GLYPH_BOX, sub_b)
        box_a = tuple(float(v) for v in (box_obs_a[-1].get("detail") or {}).get("bbox_page_px"))
        box_b = tuple(float(v) for v in (box_obs_b[-1].get("detail") or {}).get("bbox_page_px"))
        page = int(sub_a.split("/")[1])
        gray = pages.get(page)
        staff_key = "staff/" + "/".join(sub_a.split("/")[1:4])
        ys = sorted(float(v) for v in rec.obs(Q.STAFF_LINES, staff_key)[-1]["value"])
        spacing = (ys[-1] - ys[0]) / 4.0
        top, bottom = ys[0], ys[-1]
        cy_a = (box_a[1] + box_a[3]) / 2.0
        side = "above" if cy_a < top else "below"
        sign = -1.0 if side == "above" else 1.0
        edge = top if side == "above" else bottom

        page_boxes = boxes_by_page.get(page, [])
        rungs_a = _own_rungs(gray, ys, box_a, sub_a, page_boxes, side)
        rungs_b = _own_rungs(gray, ys, box_b, sub_b, page_boxes, side)
        through_a = lg.has_through_head_rung(rungs_a, box_a)
        through_b = lg.has_through_head_rung(rungs_b, box_b)
        is_third = lg.heads_are_a_third_apart(box_a, box_b, spacing)
        dist_sp = abs(cy_a - (box_b[1] + box_b[3]) / 2.0) / spacing

        guard_fires = is_third and not through_a and not through_b
        if guard_fires:
            lateral = [b for (s, b) in page_boxes if s not in (sub_a, sub_b)]
            if sign * (cy_a - edge) >= sign * ((box_b[1] + box_b[3]) / 2.0 - edge):
                outer, inner = box_a, box_b
            else:
                outer, inner = box_b, box_a
            res = lg.third_stack_rung(gray, outer, inner, spacing, exclude_boxes=lateral)
        else:
            res = None

        label = [
            f"{sub_a}  vs  {sub_b}  ({doc_id})",
            f"centres {dist_sp:.3f} staff spaces apart (third range "
            f"{lg.THIRD_STACK_SPACING_RANGE})",
            f"{sub_a} own rungs: {[round(r,1) for r in rungs_a]}  "
            f"through_head={through_a}",
            f"{sub_b} own rungs: {[round(r,1) for r in rungs_b]}  "
            f"through_head={through_b}",
        ]
        if guard_fires:
            label.append(
                f"GUARD FIRES -> implied/confirmed rung at y={res['y']:.1f} "
                f"({'ink-confirmed' if res['confirmed'] else 'implied_by_third'})"
            )
        else:
            why = []
            if not is_third:
                why.append("not a third apart")
            if through_a:
                why.append(f"{sub_a} already through-head")
            if through_b:
                why.append(f"{sub_b} already through-head")
            label.append("GUARD DOES NOT FIRE -- " + "; ".join(why))

        safe = f"{doc_id}-{sub_a.replace('/', '-')}-{sub_b.replace('/', '-')}.png"
        out_path = OUT_DIR / safe
        big, to_big, scale = render_pair_crop(
            gray, box_a, box_b, sub_a, sub_b, ys, spacing, out_path, label,
        )
        x_lo = min(box_a[0], box_b[0]) - spacing
        x_hi = max(box_a[2], box_b[2]) + spacing
        for ry in rungs_a + rungs_b:
            draw_rung(big, to_big, scale, ry, x_lo, x_hi, dashed=False)
        if guard_fires:
            draw_rung(big, to_big, scale, res["y"], x_lo, x_hi,
                     dashed=not res["confirmed"])
        text_h = big.shape[0]
        tile = cv2.imread(str(out_path))
        tile[:big.shape[0], :big.shape[1], :] = big
        cv2.imwrite(str(out_path), tile)
        tiles.append(out_path)

        index_lines.append(f"- `{safe}` — " + " | ".join(label))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")
    print(f"wrote {len(tiles)} diagnostic crops to {OUT_DIR}")

    # contact sheet
    imgs = [cv2.imread(str(p)) for p in tiles]
    imgs = [im for im in imgs if im is not None]
    if imgs:
        tile_w = 700
        resized = []
        for im in imgs:
            hh, ww = im.shape[:2]
            s = tile_w / ww
            resized.append(cv2.resize(im, (tile_w, int(hh * s))))
        cols = 2
        rows = -(-len(resized) // cols)
        row_h = max(im.shape[0] for im in resized)
        sheet = np.full((row_h * rows, tile_w * cols, 3), 255, dtype=np.uint8)
        for i, im in enumerate(resized):
            r, c = divmod(i, cols)
            sheet[r * row_h: r * row_h + im.shape[0], c * tile_w: c * tile_w + tile_w] = im
        out = REPO / "out" / "print" / "ledgers" / "r6_sheet.png"
        cv2.imwrite(str(out), sheet)
        print(f"wrote contact sheet ({len(resized)} tiles) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
