#!/usr/bin/env python3
"""lane-ledger-rungs round 5 review crops (2026-10-0x): every truth-set
head whose rung answer CHANGED from round 3's committed reader, plus
every head still WRONG or ABSTAINING after round 5's three fixes (clean
middle ledger masked by a narrow neighbour-exclusion margin + a too-strict
walk-widen trigger; one-sided ledgers beside a space-sitting head;
hand-drawn x-drift followed per rung). Measurement/drawing only -- see
FINDINGS.md "lane-ledger-rungs round 5" for the fault-by-fault writeup.

Each crop (>=600px wide, same style as rounds 1-3): red detector box, the
real 5 staff lines (green, never extended, rendered from the head's OWN
page), every measured rung (orange, with its own x-extent and a
filled/hollow mark, with other noteheads' boxes already excluded from the
ink before the rung was measured), the outer staff line the count starts
from, and the full arithmetic `derive_far_head_step` produced, alongside
the round-3 (committed) reader's own answer for comparison. Every drawn
rung and staff line is pixel-row checked against the SAME raster the
reader read.
"""
from __future__ import annotations

import importlib.util
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

# The round-3 (committed, pre-round-5) reader, loaded as a SEPARATE module
# from the tree's own last commit -- never a flag toggle, so "before" is
# not this lane's own code (CLAUDE.md rule 7).
import subprocess  # noqa: E402

import tempfile  # noqa: E402

_BEFORE_SRC = Path(tempfile.gettempdir()) / "lane_ledger_rungs_r5_ledger_grid_before.py"
_BEFORE_SRC.write_text(
    subprocess.run(
        ["git", "show", "HEAD:tools/omr/annotate/ledger_grid.py"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
)
_spec = importlib.util.spec_from_file_location("lg_before_r5", _BEFORE_SRC)
lg_before = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lg_before)

OUT_DIR = REPO / "out" / "print" / "ledgers" / "r5"

RED = (0, 0, 255)
GREEN = (0, 170, 0)
BLUE = (255, 120, 0)
ORANGE = (30, 140, 255)
BLACK = (0, 0, 0)
MIN_WIDTH = 600


def render_crop(gray, box, lines, subject, out_path, truth_pos, geom_pos,
                after_pos, reason, cause, other_boxes, before_pos, before_reason):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lines = sorted(lines)
    top, bottom = lines[0], lines[-1]
    spacing = (bottom - top) / 4.0
    side = "above" if cy < top else "below"
    edge = top if side == "above" else bottom
    sign = -1.0 if side == "above" else 1.0
    near_y = y1 if side == "above" else y0

    # NOTE: `head_box_y` (fault 2's one-sided rule) is deliberately NOT
    # passed here -- it is held back from the real scoring path (measured
    # net negative, see FINDINGS), so the crop must draw exactly what the
    # shipped reader actually used, not the held-back variant.
    items = lg.measure_ledger_rungs(
        gray, lines, cx, head_y=cy, exclude_boxes=other_boxes,
        head_box_x=(x0, x1),
    )[side]

    # --- window ---
    farthest = cy
    for ry in items:
        farthest = min(farthest, ry) if side == "above" else max(farthest, ry)
    margin = 1.4 * spacing
    wy0 = min(top, farthest, near_y) - margin
    wy1 = max(bottom, farthest, near_y) + margin
    wx0 = cx - 2.2 * spacing
    wx1 = cx + 2.2 * spacing
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

    pixel_checks = []
    for ly in lines:
        if ly < wy0 or ly > wy1:
            continue
        _, by = to_big(wx0, ly)
        cv2.line(big, (0, by), (out_w, by), GREEN, 1)
        pixel_checks.append(("staff_line", ly))

    edge_pos = 0 if side == "above" else 8
    _, oby = to_big(wx0, edge)
    cv2.line(big, (0, oby), (28, oby), BLUE, 5)
    cv2.putText(big, f"START pos{edge_pos}",
               (32, oby - 6 if side == "above" else oby + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.55, BLUE, 2, cv2.LINE_AA)

    # near-edge tick (where the gap is measured from)
    _, nby = to_big(wx0, near_y)
    cv2.line(big, (0, nby), (18, nby), (160, 0, 160), 3)

    rung_items_drawn = []
    for ry in items:
        ex0, ex1 = lg_rung_extent(gray, ry, cx, spacing, other_boxes)
        _, by = to_big(wx0, ry)
        bx0, _ = to_big(ex0, ry)
        bx1, _ = to_big(ex1, ry)
        cv2.line(big, (max(0, bx0), by), (min(out_w, bx1), by), ORANGE,
                max(2, scale // 2))
        mx, _ = to_big(cx, ry)
        cv2.circle(big, (mx, by), 7, ORANGE, -1)
        pixel_checks.append(("rung", ry, (ex0, ex1)))
        rung_items_drawn.append(ry)

    bx0, by0 = to_big(x0, y0)
    bx1, by1 = to_big(x1, y1)
    cv2.rectangle(big, (bx0, by0), (bx1, by1), RED, max(1, scale // 3))
    ccx, ccy = to_big(cx, cy)
    cv2.line(big, (ccx - 8, ccy), (ccx + 8, ccy), RED, 2)
    cv2.line(big, (ccx, ccy - 8), (ccx, ccy + 8), RED, 2)

    TEXT_W = max(out_w, 1050)
    lines_txt = [
        f"{subject}",
        f"truth pos={truth_pos}  geometry pos={geom_pos}  rungs-r5 pos={after_pos}",
        f"round-3 (committed) rungs pos={before_pos}  reason: {before_reason}",
        f"{len(rung_items_drawn)} rung(s) found (after excluding other noteheads' own ink)",
        f"r5 arithmetic: {reason}",
        f"cause: {cause}",
    ]
    text_h = 20 + len(lines_txt) * 22 + 10
    tile = np.full((out_h + text_h, TEXT_W, 3), 255, dtype=np.uint8)
    tile[:out_h, :out_w, :] = big
    for i, t in enumerate(lines_txt):
        cv2.putText(tile, t[:160], (6, out_h + 20 + i * 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.48, BLACK, 1, cv2.LINE_AA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), tile)

    report = []
    for check in pixel_checks:
        if check[0] == "staff_line":
            _, ly = check
            y_lo, y_hi = max(0, int(ly) - 1), min(h, int(ly) + 2)
            x_lo, x_hi = max(0, int(cx) - 20), min(w, int(cx) + 20)
            strip = gray[y_lo:y_hi, x_lo:x_hi] < 128
            cov = float(strip.any(axis=0).mean()) if strip.size else 0.0
            report.append(f"staff_line y={ly:.1f} coverage={cov:.2f} {'OK' if cov >= 0.5 else 'MISS'}")
        else:
            _, ry, ex = check
            x_lo, x_hi = max(0, int(ex[0])), min(w, int(ex[1]) + 1)
            y_lo, y_hi = max(0, int(ry) - 1), min(h, int(ry) + 2)
            if x_hi <= x_lo:
                report.append(f"rung y={ry:.1f} NO EXTENT")
                continue
            strip = gray[y_lo:y_hi, x_lo:x_hi] < 128
            cov = float(strip.any(axis=0).mean())
            report.append(f"rung y={ry:.1f} coverage={cov:.2f} {'OK' if cov >= 0.5 else 'MISS'}")
    return report


def lg_rung_extent(gray, y, x_probe, spacing, exclude_boxes):
    """The drawn x-extent of a rung at y, off the SAME excluded-ink read
    the reader used (so the drawing matches what was actually measured)."""
    h, w = gray.shape
    y_i = int(round(y))
    y0, y1 = max(0, y_i - 1), min(h, y_i + 2)
    x_half = int(round(2.5 * spacing))
    x0 = max(0, int(round(x_probe)) - x_half)
    x1 = min(w, int(round(x_probe)) + x_half)
    window = gray[y0:y1, x0:x1].copy()
    for (bx0, by0, bx1, by1) in exclude_boxes:
        ex0, ey0 = max(int(bx0), x0), max(int(by0), y0)
        ex1, ey1 = min(int(bx1) + 1, x1), min(int(by1) + 1, y1)
        if ex1 > ex0 and ey1 > ey0:
            window[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0] = 255
    thr = lg._otsu_threshold(window)
    ink_cols = (window <= thr).any(axis=0)
    bridge = int(round(lg.RUNG_BRIDGE_GAP_SPACES * spacing))
    runs = []
    n = len(ink_cols)
    i = 0
    while i < n:
        if ink_cols[i]:
            j = i
            while j < n and ink_cols[j]:
                j += 1
            if runs and i - runs[-1][1] <= bridge:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    if not runs:
        return (x_probe - 0.5 * spacing, x_probe + 0.5 * spacing)
    probe_col = int(round(x_probe)) - x0
    containing = [r for r in runs if r[0] <= probe_col < r[1]]
    r = containing[0] if containing else min(
        runs, key=lambda r: min(abs(r[0] - probe_col), abs(r[1] - 1 - probe_col))
    )
    return float(x0 + r[0]), float(x0 + r[1] - 1)


def cause_for(h, reason, changed):
    if changed:
        return "ANSWER CHANGED in round 5 (see before/after on the tile)"
    if h["v_after"] == "abstain":
        return f"reader abstained -- {reason}"
    # wrong: name the shape of the mismatch
    if "ambiguous" in reason:
        return "ambiguous gap between touching and half-a-space -- abstain zone too narrow or a real edge case"
    if "passes through" in reason or reason.startswith("last rung"):
        return "rung matched as through-head but lands on the wrong ledger -- count or walk may be off by one rung"
    if "touching" in reason:
        return "classified as touching (space) but reference disagrees -- gap measurement or reference mapping"
    if "next ledger" in reason:
        return "classified as on-the-next-ledger (half-space rule) but reference disagrees -- gap measurement or reference mapping"
    return "see arithmetic text"


def _reader_pos(lg_mod, gray, lines, box, subject, others):
    """Same arithmetic as `score_truth_set_rungs.reader_absolute_position`,
    parameterised by WHICH `ledger_grid` module reads the ink -- lets this
    script compare the round-3 (committed) reader against round 5's own
    code on the identical real heads, never a flag toggle."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    ys = sorted(lines)
    spacing = (ys[-1] - ys[0]) / 4.0
    top, bottom = ys[0], ys[-1]
    if cy < top:
        side, edge, sign, edge_pos, near_y = "above", top, -1.0, 0, y1
    else:
        side, edge, sign, edge_pos, near_y = "below", bottom, 1.0, 8, y0
    # Same note as `render_crop`: `head_box_y` is held back from the real
    # path, so the "round5" comparison reader does not pass it either.
    kwargs = dict(head_y=cy, exclude_boxes=others, head_box_x=(x0, x1))
    items = lg_mod.measure_ledger_rungs(gray, ys, cx, **kwargs).get(side, [])
    step = lg_mod.derive_far_head_step(items, edge, sign, near_y, spacing)
    if step["offset"] is None:
        return None, step["reason"]
    return edge_pos + int(sign * step["offset"]), step["reason"]


def main() -> int:
    index_lines = [
        "# lane-ledger-rungs round 5 review crops (2026-10-0x)", "",
        "Every truth-set head whose rung answer CHANGED from the round-3 "
        "(committed) reader, listed FIRST, followed by every head still "
        "wrong or abstaining after round 5's three fixes (clean middle "
        "ledger masked by a too-narrow neighbour-exclusion margin + a "
        "too-strict walk-widen trigger; one-sided ledgers beside a "
        "space-sitting head; hand-drawn x-drift followed per rung). "
        "Measurement/drawing only -- see FINDINGS.md.", "",
    ]
    cause_counts: dict = {}
    total = 0
    changed_total = 0
    sheet_order: list[Path] = []

    for doc_id in ts.DOCS:
        loaded = ts.load_doc(doc_id)
        r = score.score_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        boxes_by_page = score._notehead_boxes_by_page(rec)
        rows = {row["subject"]: row for row in score._far_head_rows(doc_id, loaded)}

        per_head_rows = []
        for h in r["per_head"]:
            row = rows.get(h["subject"])
            if row is None:
                continue
            line_rows = rec.obs(Q.STAFF_LINES, row["staff_key"])
            lines = [float(v) for v in line_rows[-1]["value"]]
            gray = pages.get(row["page"])
            others = [b for (s, b) in boxes_by_page.get(row["page"], [])
                     if s != row["subject"]]
            before_pos, before_reason = _reader_pos(
                lg_before, gray, lines, row["page_box"], row["subject"], others
            )
            changed = (before_pos != h["after_pos"])
            if not changed and h["v_after"] == "right":
                continue  # unchanged AND right -- nothing to show
            per_head_rows.append(dict(
                h=h, row=row, lines=lines, gray=gray, others=others,
                before_pos=before_pos, before_reason=before_reason,
                changed=changed,
            ))

        # changed heads first, matching the task's ordering for the sheet
        per_head_rows.sort(key=lambda d: (not d["changed"], d["h"]["subject"]))

        for d in per_head_rows:
            h, row = d["h"], d["row"]
            total += 1
            if d["changed"]:
                changed_total += 1
            cause = cause_for(h, h["reason"], d["changed"])
            safe = f"{doc_id}-{h['subject'].replace('/', '-')}.png"
            out_path = OUT_DIR / safe
            pix_report = render_crop(
                d["gray"], row["page_box"], d["lines"], h["subject"], out_path,
                h["truth_pos"], h["geom_pos"], h["after_pos"], h["reason"],
                cause, d["others"], d["before_pos"], d["before_reason"],
            )
            sheet_order.append(out_path)
            cause_counts[cause] = cause_counts.get(cause, 0) + 1
            tag = "CHANGED" if d["changed"] else h["v_after"]
            index_lines.append(
                f"- `{safe}` — {h['subject']} ({doc_id}, {tag}): "
                f"truth={h['truth_pos']} geom={h['geom_pos']} "
                f"round3={d['before_pos']} round5={h['after_pos']}. cause: {cause}"
            )
            bad = [p for p in pix_report if "MISS" in p or "NO EXTENT" in p]
            if bad:
                index_lines.append(f"  pixel-check issues: {bad}")

    index_lines.append("")
    index_lines.append(f"## {changed_total} of {total} tiles are answer changes")
    index_lines.append("")
    index_lines.append("## Cause counts")
    for cause, n in sorted(cause_counts.items(), key=lambda kv: -kv[1]):
        index_lines.append(f"- {n}: {cause}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.md").write_text("\n".join(index_lines) + "\n")
    print(f"wrote {total} crops to {OUT_DIR} ({changed_total} answer changes)")
    for cause, n in sorted(cause_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n}: {cause}")

    _write_contact_sheet(sheet_order[:20])
    return 0


def _write_contact_sheet(tiles: "list[Path]") -> None:
    if not tiles:
        return
    imgs = [cv2.imread(str(p)) for p in tiles]
    imgs = [im for im in imgs if im is not None]
    if not imgs:
        return
    tile_w = 520
    resized = []
    for im in imgs:
        h, w = im.shape[:2]
        scale = tile_w / w
        resized.append(cv2.resize(im, (tile_w, int(h * scale))))
    cols = 4
    rows = -(-len(resized) // cols)
    row_h = max(im.shape[0] for im in resized)
    sheet = np.full((row_h * rows, tile_w * cols, 3), 255, dtype=np.uint8)
    for i, im in enumerate(resized):
        r, c = divmod(i, cols)
        sheet[r * row_h: r * row_h + im.shape[0], c * tile_w: c * tile_w + tile_w] = im
    out = REPO / "out" / "print" / "ledgers" / "r5_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet)
    print(f"wrote contact sheet ({len(resized)} tiles) to {out}")


if __name__ == "__main__":
    raise SystemExit(main())
