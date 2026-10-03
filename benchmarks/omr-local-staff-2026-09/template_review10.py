#!/usr/bin/env python3
"""lane-ledger-template (2026-10-02, Sean): ONE review sheet, no re-score.

Sean, after reading `template_geom_templates.jpg`: "NO SCORING this
round, only templates and one review sheet." Manager's read of that
sheet: (1) the ~2 deg outer tilt was an artefact of fitting WITH the
staff lines left in; (2) the hollow template (thin ring, big empty
centre) does not look like a real Litolff half note; (3) the "real
head" comparison panels were not framed on the heads at all.

This script does NOT call `score_head_template.score_doc_with_templates`
or anything that compares a reader's answer to round 8 -- it only builds
geometry templates (`measure_head_tilt.py`'s re-measured, line-masked
tilt + axis-ratio numbers) and MATCHES them against 10 real far heads
for display. A verdict (on-line/space, margin) and a reference TICK are
shown for visual calibration only -- never tallied, never compared to
round 8.

    python3 benchmarks/omr-local-staff-2026-09/template_review10.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import score_head_template as sht  # noqa: E402
import measure_head_tilt as mht  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.geometry import (  # noqa: E402
    STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES,
)
from tools.omr.annotate import ledger_grid as lg  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers"
OUT_PATH = OUT_DIR / "template_review10.jpg"
MAX_SHEET_W = 2600
JPEG_QUALITY = 85
ZOOM = 4
PAD_SPACES_X = 2.2
PAD_SPACES_Y = 2.8  # generous -- ledgers must be fully in frame

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
CYAN = (220, 200, 0)
YELLOW = (0, 220, 220)
BLACK = (0, 0, 0)

#: Always-included subjects (the brief's own named heads).
MUST_INCLUDE = ["glyph/3/0/7/0/7", "glyph/3/0/7/2/4", "glyph/3/0/8/6/10"]


def _position_to_y(pos: float, lines, spacing: float) -> float:
    return lines[0] + pos * (spacing / 2.0)


def _select_10(doc_id: str, loaded) -> list:
    """A diverse, hand-stated mix -- filled/hollow, above/below,
    on-ledger/in-space -- NEVER chosen by truth agreement (CLAUDE.md
    rule 5, "no default flips on agreement with our own reading"). Class
    and parity are GATHER facts (detector class, staff position's own
    parity), not a truth comparison."""
    rec = loaded["rec"]
    rows = score._far_head_rows(doc_id, loaded)
    boxes_by_page = sht._page_glyph_boxes(rec)
    out = []
    seen = set()
    must = [r for r in rows if r["subject"] in MUST_INCLUDE]
    for r in must:
        out.append(r)
        seen.add(r["subject"])

    buckets = {}
    for r in rows:
        if r["subject"] in seen:
            continue
        entry = {s: (cls, box) for (s, cls, box) in boxes_by_page.get(r["page"], [])}
        found = entry.get(r["subject"])
        if found is None:
            continue
        cls, _box = found
        kind = "filled" if "Black" in cls else ("hollow" if (
            "Half" in cls or "Whole" in cls) else None)
        if kind is None:
            continue
        pos = int(round(r["raw_pos"]))
        side = "above" if pos < 4 else "below"
        parity = "on_ledger" if pos % 2 == 0 else "in_space"
        key = (kind, side, parity)
        buckets.setdefault(key, []).append(r)

    need = 10 - len(out)
    keys = sorted(buckets.keys())
    i = 0
    while need > 0 and keys:
        key = keys[i % len(keys)]
        bucket = buckets.get(key, [])
        if bucket:
            r = bucket.pop(0)
            if r["subject"] not in seen:
                out.append(r)
                seen.add(r["subject"])
                need -= 1
        else:
            keys.remove(key)
            if not keys:
                break
            continue
        i += 1
    return out[:10]


def _draw_template_outline(crop, to_tile, cx, cy, kind, scale, outer_axes_native,
                           angle_deg):
    """Yellow rotated-ellipse outline + centre cross at the MATCHED
    centre, sized from this doc's own measured outer axes (native px)."""
    center_tile = to_tile(cx, cy)
    ax_px = (int(outer_axes_native[0] / 2.0 * scale),
            int(outer_axes_native[1] / 2.0 * scale))
    cv2.ellipse(crop, center_tile, ax_px, -angle_deg, 0, 360, YELLOW, 2)
    cs_ = 10
    cv2.line(crop, (center_tile[0] - cs_, center_tile[1]),
              (center_tile[0] + cs_, center_tile[1]), YELLOW, 2)
    cv2.line(crop, (center_tile[0], center_tile[1] - cs_),
              (center_tile[0], center_tile[1] + cs_), YELLOW, 2)


def _head_tile(doc_id, row, rec, pages, templates_by_page, outer_tilt, outer_axes_native):
    box = row["page_box"]
    staff_key = row["staff_key"]
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    global_lines = [float(y) for y in line_rows[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    subject = row["subject"]

    boxes_by_page = sht._page_glyph_boxes(rec)
    entry = {s: (cls, b) for (s, cls, b) in boxes_by_page.get(row["page"], [])}
    cls, _b = entry.get(subject, ("noteheadBlackOnLine", box))
    kind = "filled" if "Black" in cls else "hollow"

    others = [b for (s, c, b) in boxes_by_page.get(row["page"], []) if s != subject]
    templates = sht.templates_for_page(templates_by_page, row["page"])
    match = ht.match_head_template(gray, box, spacing, templates, exclude_boxes=others,
                                   kind=kind)

    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    clef_v = rec.value(Q.CLEF, staff_key)
    truth_pos = sorted(set(score.truth_positions(row["truth_pitches"], str(clef_v))))
    geom_pos = int(round(row["raw_pos"]))
    ref_pos = truth_pos[0] if truth_pos else geom_pos
    ref_y = _position_to_y(ref_pos, lines, spacing)

    match_cy = match["center_y"] if match else (y0 + y1) / 2.0
    all_ys = [min(lines), max(lines), y0, y1, ref_y, match_cy]
    crop_x0 = max(0, int(cx - PAD_SPACES_X * spacing))
    crop_x1 = min(gray.shape[1], int(cx + PAD_SPACES_X * spacing))
    crop_y0 = max(0, int(min(all_ys) - PAD_SPACES_Y * spacing))
    crop_y1 = min(gray.shape[0], int(max(all_ys) + PAD_SPACES_Y * spacing))
    crop = cv2.cvtColor(gray[crop_y0:crop_y1, crop_x0:crop_x1], cv2.COLOR_GRAY2BGR)
    h0, w0 = crop.shape[:2]
    crop = cv2.resize(crop, (w0 * ZOOM, h0 * ZOOM), interpolation=cv2.INTER_NEAREST)

    def to_tile(px, py):
        return (int((px - crop_x0) * ZOOM), int((py - crop_y0) * ZOOM))

    for ly in lines:
        p0, p1 = to_tile(crop_x0, ly), to_tile(crop_x1, ly)
        cv2.line(crop, p0, p1, GREEN, 2)

    tl, br = to_tile(x0, y0), to_tile(x1, y1)
    cv2.rectangle(crop, tl, br, RED, 1)

    if match and match.get("best_variant") is not None:
        _draw_template_outline(crop, to_tile, cx, match_cy, kind, ZOOM,
                               outer_axes_native, outer_tilt.get(kind, 0.0))

    cyan_x0 = to_tile(cx - 1.2 * spacing, ref_y)[0]
    cyan_x1 = to_tile(cx + 1.2 * spacing, ref_y)[0]
    cyan_y = to_tile(cx, ref_y)[1]
    cv2.line(crop, (cyan_x0, cyan_y), (cyan_x1, cyan_y), CYAN, 3)

    variant_label = (match["best_variant"] if match and match.get("best_variant")
                     else "none")
    margin_label = f"{match['margin']:.3f}" if match and match.get("margin") is not None else "n/a"
    undecided = match.get("undecided") if match else True
    lines_text = [
        f"{doc_id}  {subject}  ({kind})",
        f"template match: {variant_label}{'  UNDECIDED' if undecided else ''}  "
        f"margin={margin_label}",
        "green=staff lines  yellow=matched template  cyan=reference tick",
    ]
    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    text_w = max(cv2.getTextSize(t, font, font_scale, thickness)[0][0] for t in lines_text)
    canvas_w = max(crop.shape[1], text_w + 16)
    legend_h = 24 * (len(lines_text) + 1)
    out = np.full((crop.shape[0] + legend_h, canvas_w, 3), 255, dtype=np.uint8)
    out[:crop.shape[0], :crop.shape[1]] = crop
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, crop.shape[0] + 20 + i * 22),
                    font, font_scale, BLACK, thickness, cv2.LINE_AA)
    return out


def _templates_panel(doc_id, templates_by_page, info):
    tiles = []
    page = sorted(k for k in templates_by_page.keys() if k != "pooled")[0]
    tmpls = templates_by_page[page]
    for key in sorted(tmpls.keys()):
        kind, variant = key
        tmpl = tmpls[key]
        img = (tmpl.img * 255).clip(0, 255).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        img = cv2.resize(img, (img.shape[1] * 3, img.shape[0] * 3),
                         interpolation=cv2.INTER_NEAREST)
        label = f"{kind}/{variant}"
        cv2.putText(img, label, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, BLACK, 1,
                    cv2.LINE_AA)
        tiles.append(img)
    h = max(t.shape[0] for t in tiles)
    row = np.full((h, sum(t.shape[1] for t in tiles) + 8 * (len(tiles) - 1), 3),
                  255, dtype=np.uint8)
    x = 0
    for t in tiles:
        row[:t.shape[0], x:x + t.shape[1]] = t
        x += t.shape[1] + 8
    caption = f"{doc_id} templates (page {page}): {info}"
    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
    out = np.full((row.shape[0] + 20, row.shape[1], 3), 255, dtype=np.uint8)
    out[:row.shape[0], :row.shape[1]] = row
    cv2.putText(out, caption[:180], (4, row.shape[0] + 15), font, font_scale, BLACK,
                thickness, cv2.LINE_AA)
    return out


def main() -> int:
    panels = []
    head_tiles = []
    for doc_id in ts.DOCS:
        print(f"=== {doc_id} ===")
        measurements = mht.collect_doc_measurements(doc_id)
        summary = mht.summarize(doc_id, measurements)
        outer_tilt = {k: v.get("outer_tilt_deg", 0.0) for k, v in summary.items()}
        outer_axes_native = {k: v.get("outer_axes_px", (
            STANDARD_HEAD_WIDTH_SPACES * 16, STANDARD_HEAD_HEIGHT_SPACES * 16))
            for k, v in summary.items()}
        templates_by_page, info = sht.build_geometry_templates_for_doc(doc_id)
        panels.append(_templates_panel(doc_id, templates_by_page, info))

        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        want = 7 if doc_id == "beethoven5-litolff" else 3
        remaining = max(0, min(want, 10 - len(head_tiles)))
        selected = _select_10(doc_id, loaded)[:remaining] if remaining else []
        for row in selected:
            tile = _head_tile(doc_id, row, rec, pages, templates_by_page,
                              outer_tilt, outer_axes_native.get("filled", (20, 20)))
            head_tiles.append(tile)
        print()

    # 10 head tiles total across both docs, 2 columns.
    head_tiles = head_tiles[:10]
    cols = 2
    tile_w = max(t.shape[1] for t in head_tiles)
    tile_h = max(t.shape[0] for t in head_tiles)
    rows_n = (len(head_tiles) + cols - 1) // cols
    heads_sheet = np.full((rows_n * tile_h, cols * tile_w, 3), 255, dtype=np.uint8)
    for i, t in enumerate(head_tiles):
        r, c = divmod(i, cols)
        th, tw = t.shape[:2]
        heads_sheet[r * tile_h:r * tile_h + th, c * tile_w:c * tile_w + tw] = t

    panel_w = max(p.shape[1] for p in panels)
    panels_resized = []
    for p in panels:
        if p.shape[1] != panel_w:
            f = panel_w / p.shape[1]
            p = cv2.resize(p, (panel_w, int(p.shape[0] * f)))
        panels_resized.append(p)
    panels_stack = np.full((sum(p.shape[0] for p in panels_resized), panel_w, 3),
                           255, dtype=np.uint8)
    y = 0
    for p in panels_resized:
        panels_stack[y:y + p.shape[0], :p.shape[1]] = p
        y += p.shape[0]

    full_w = max(panels_stack.shape[1], heads_sheet.shape[1])

    def pad_to_width(img, w):
        if img.shape[1] == w:
            return img
        out = np.full((img.shape[0], w, 3), 255, dtype=np.uint8)
        out[:, :img.shape[1]] = img
        return out

    panels_stack = pad_to_width(panels_stack, full_w)
    heads_sheet = pad_to_width(heads_sheet, full_w)
    sheet = np.vstack([panels_stack, heads_sheet])

    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    print(f"wrote {OUT_PATH} ({len(head_tiles)} head tiles, "
          f"{sheet.shape[1]}x{sheet.shape[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
