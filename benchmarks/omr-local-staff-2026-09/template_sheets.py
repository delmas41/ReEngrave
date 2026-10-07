#!/usr/bin/env python3
"""lane-ledger-template (2026-10-02): two phone-sized contact sheets for
the head-TEMPLATE matcher (`tools/omr/annotate/head_template.py`).

DRAWING ONLY -- no record mutation, no re-gather, no change to
`tools/omr/annotate/head_template.py`; the evidence-function substitution
is the SAME local monkeypatch `score_head_template.py` already uses,
scoped to this process only.

  1. template_templates.jpg -- every (kind, variant) template actually
     built per document (page-level + the document-pooled fallback),
     shown as its own canonical ink image with the HEAD mask (yellow)
     and the LINE-ROW mask(s) (orange) outlined, captioned with the
     exemplar count that built it.
  2. template_changed.jpg -- every far head whose verdict differs
     round8 -> template (raw substitution), drawn with: the best-
     matching template's own outline overlaid at its MATCHED centre
     (yellow), the local staff lines (green), the detector box (red),
     the reference tick (cyan). Caption: "reference X -- round 8 Y --
     template Z (on-line/space, margin m)".

    python3 benchmarks/omr-local-staff-2026-09/template_sheets.py
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
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers"

TARGET_TILE_W = 700
UPSCALE = 3
PAD_SPACES_X = 3.0
PAD_SPACES_Y = 1.75
COLS = 3
MAX_SHEET_W = 2600
JPEG_QUALITY = 85

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
CYAN = (220, 200, 0)
YELLOW = (0, 220, 220)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def _position_to_y(pos: float, lines, spacing: float) -> float:
    return lines[0] + pos * (spacing / 2.0)


# ---------------------------------------------------------------------------
# sheet 1: the templates themselves
# ---------------------------------------------------------------------------

def _template_tile(doc_id: str, page_label: str, key, tmpl: "ht.Template"):
    kind, variant = key
    img = (tmpl.img * 255).clip(0, 255).astype(np.uint8)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    img = cv2.resize(img, (img.shape[1] * UPSCALE, img.shape[0] * UPSCALE),
                     interpolation=cv2.INTER_NEAREST)

    def mask_outline(mask, color):
        m = cv2.resize(mask.astype(np.uint8) * 255,
                       (img.shape[1], img.shape[0]),
                       interpolation=cv2.INTER_NEAREST)
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, contours, -1, color, 2)

    mask_outline(ht.HEAD_MASK, YELLOW)
    for comp in tmpl.line_mask_components:
        mask_outline(comp, ORANGE)

    lines_text = [f"{doc_id}  page={page_label}", f"{kind} / {variant}  (n={tmpl.n})"]
    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    text_w = max(cv2.getTextSize(t, font, font_scale, thickness)[0][0] for t in lines_text)
    canvas_w = max(img.shape[1], text_w + 16)
    legend_h = 24 * (len(lines_text) + 1)
    out = np.full((img.shape[0] + legend_h, canvas_w, 3), 255, dtype=np.uint8)
    out[:img.shape[0], :img.shape[1]] = img
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, img.shape[0] + 20 + i * 22),
                    font, font_scale, BLACK, thickness, cv2.LINE_AA)
    return out


def build_templates_sheet():
    tiles = []
    for doc_id in ts.DOCS:
        templates_by_page, counts = sht.build_templates_for_doc(doc_id)
        print(f"  {doc_id}: {counts}")
        for page, tmpls in templates_by_page.items():
            label = "pooled" if page == "pooled" else str(page)
            for key in sorted(tmpls.keys()):
                tiles.append(_template_tile(doc_id, label, key, tmpls[key]))

    if not tiles:
        print("  no templates built -- nothing to sheet")
        return

    tile_w = max(t.shape[1] for t in tiles)
    tile_h = max(t.shape[0] for t in tiles)
    rows_n = (len(tiles) + COLS - 1) // COLS
    sheet = np.full((rows_n * tile_h, COLS * tile_w, 3), 255, dtype=np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, COLS)
        th, tw = t.shape[:2]
        sheet[r * tile_h:r * tile_h + th, c * tile_w:c * tile_w + tw] = t

    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jpg_path = OUT_DIR / "template_templates.jpg"
    cv2.imwrite(str(jpg_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    print(f"  wrote {jpg_path} ({len(tiles)} tiles, {sheet.shape[1]}x{sheet.shape[0]})")


# ---------------------------------------------------------------------------
# sheet 2: every head whose verdict changed
# ---------------------------------------------------------------------------

def _live_flip_subjects(templates_by_doc):
    out = {}
    for doc_id in ts.DOCS:
        round8 = score.score_doc(doc_id, four_causes_cd=True)
        template_run = sht.score_doc_with_templates(doc_id, templates_by_doc[doc_id])
        before_by = {h["subject"]: h for h in round8["per_head"]}
        after_by = {h["subject"]: h for h in template_run["per_head"]}
        flips = sorted(
            sub for sub, hb in before_by.items()
            if hb["v_after"] != after_by.get(sub, {}).get("v_after")
        )
        out[doc_id] = flips
    return out


def _tile(doc_id, row, rec, pages, nb_by_page, acc_by_page, templates_by_page):
    box = row["page_box"]
    staff_key = row["staff_key"]
    line_rows = rec.obs(Q.STAFF_LINES, staff_key)
    global_lines = [float(y) for y in line_rows[-1]["value"]]
    gray = pages.get(row["page"])
    lines = score.frame_lines_for_head(gray, global_lines, box)
    spacing = (max(lines) - min(lines)) / 4.0
    subject = row["subject"]

    round8_pos, round8_reason = score.reader_absolute_position(
        gray, lines, box, subject, nb_by_page.get(row["page"], []),
        page_accidental_boxes=acc_by_page.get(row["page"], []), four_causes_cd=True,
    )

    originals = sht._install_template_evidence(templates_by_page, nb_by_page)
    try:
        template_pos, template_reason = score.reader_absolute_position(
            gray, lines, box, subject, nb_by_page.get(row["page"], []),
            page_accidental_boxes=acc_by_page.get(row["page"], []), four_causes_cd=True,
        )
    finally:
        sht._restore_evidence(originals)

    others = [b for (s, b) in nb_by_page.get(row["page"], []) if s != subject]
    others = others + [b for (s, b) in acc_by_page.get(row["page"], [])]
    templates = sht.templates_for_page(templates_by_page, row["page"])
    match = ht.match_head_template(gray, box, spacing, templates, exclude_boxes=others)

    geom_pos = int(round(row["raw_pos"]))
    clef_v = rec.value(Q.CLEF, staff_key)
    truth_pos = sorted(set(score.truth_positions(row["truth_pitches"], str(clef_v))))
    ref_pos = truth_pos[0] if truth_pos else geom_pos

    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    ref_y = _position_to_y(ref_pos, lines, spacing)

    match_cy = match["center_y"] if match else (y0 + y1) / 2.0
    all_ys = [min(lines), max(lines), y0, y1, ref_y, match_cy]
    crop_x0 = max(0, int(cx - PAD_SPACES_X * spacing))
    crop_x1 = min(gray.shape[1], int(cx + PAD_SPACES_X * spacing))
    crop_y0 = max(0, int(min(all_ys) - PAD_SPACES_Y * spacing))
    crop_y1 = min(gray.shape[0], int(max(all_ys) + PAD_SPACES_Y * spacing))
    crop = cv2.cvtColor(gray[crop_y0:crop_y1, crop_x0:crop_x1], cv2.COLOR_GRAY2BGR)
    h0, w0 = crop.shape[:2]
    scale = max(UPSCALE, int(np.ceil(TARGET_TILE_W / max(w0, 1))))
    crop = cv2.resize(crop, (w0 * scale, h0 * scale), interpolation=cv2.INTER_NEAREST)

    def to_tile(px, py):
        return (int((px - crop_x0) * scale), int((py - crop_y0) * scale))

    for ly in lines:
        p0, p1 = to_tile(crop_x0, ly), to_tile(crop_x1, ly)
        cv2.line(crop, p0, p1, GREEN, 2)

    if match and match.get("best_variant") is not None:
        from tools.omr.staged.geometry import (
            STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES,
        )
        hw = STANDARD_HEAD_WIDTH_SPACES * spacing / 2.0
        hh = STANDARD_HEAD_HEIGHT_SPACES * spacing / 2.0
        center_tile = to_tile(cx, match_cy)
        axes_tile = (int(hw * scale), int(hh * scale))
        cv2.ellipse(crop, center_tile, axes_tile, 0, 0, 360, YELLOW, 2)
        cs_ = 10
        cv2.line(crop, (center_tile[0] - cs_, center_tile[1]),
                  (center_tile[0] + cs_, center_tile[1]), YELLOW, 2)
        cv2.line(crop, (center_tile[0], center_tile[1] - cs_),
                  (center_tile[0], center_tile[1] + cs_), YELLOW, 2)

    tl, br = to_tile(x0, y0), to_tile(x1, y1)
    cv2.rectangle(crop, tl, br, RED, 1)

    cyan_x0 = to_tile(cx - 1.2 * spacing, ref_y)[0]
    cyan_x1 = to_tile(cx + 1.2 * spacing, ref_y)[0]
    cyan_y = to_tile(cx, ref_y)[1]
    cv2.line(crop, (cyan_x0, cyan_y), (cyan_x1, cyan_y), CYAN, 3)

    def _verdict(pos):
        if pos is None:
            return "undecided"
        return "right" if pos in truth_pos else "wrong"

    round8_label = f"{round8_pos}" if round8_pos is not None else "undecided"
    template_label = f"{template_pos}" if template_pos is not None else "undecided"
    variant_label = (match["best_variant"] if match and match.get("best_variant")
                     else "none")
    margin_label = f"{match['margin']:.3f}" if match and match.get("margin") is not None else "n/a"
    lines_text = [
        f"{doc_id}  {subject}",
        f"reference {ref_pos} -- round 8 {round8_label} ({_verdict(round8_pos)}) "
        f"-- template {template_label} ({_verdict(template_pos)})",
        f"template match: {variant_label}, margin {margin_label}"[:100],
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


def build_changed_sheet(templates_by_doc):
    live_flips = _live_flip_subjects(templates_by_doc)
    for doc_id, subs in live_flips.items():
        print(f"  live flips, {doc_id}: {len(subs)} {subs}")

    tiles = []
    for doc_id, subs in live_flips.items():
        if not subs:
            continue
        loaded = ts.load_doc(doc_id)
        rows_by_subject = {r["subject"]: r for r in score._far_head_rows(doc_id, loaded)}
        pages = score.PageCache(loaded["cfg"])
        nb_by_page = score._notehead_boxes_by_page(loaded["rec"])
        acc_by_page = score._accidental_boxes_by_page(loaded["rec"])
        for sub in subs:
            row = rows_by_subject.get(sub)
            if row is None:
                continue
            tile = _tile(doc_id, row, loaded["rec"], pages, nb_by_page, acc_by_page,
                        templates_by_doc[doc_id])
            tiles.append(tile)

    if not tiles:
        print("  no heads qualify for template_changed.jpg -- nothing to sheet")
        return

    tile_w = max(t.shape[1] for t in tiles)
    tile_h = max(t.shape[0] for t in tiles)
    rows_n = (len(tiles) + COLS - 1) // COLS
    sheet = np.full((rows_n * tile_h, COLS * tile_w, 3), 255, dtype=np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, COLS)
        th, tw = t.shape[:2]
        sheet[r * tile_h:r * tile_h + th, c * tile_w:c * tile_w + tw] = t

    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jpg_path = OUT_DIR / "template_changed.jpg"
    cv2.imwrite(str(jpg_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    print(f"  wrote {jpg_path} ({len(tiles)} tiles, {sheet.shape[1]}x{sheet.shape[0]})")


def main() -> int:
    print("=== template_templates.jpg ===")
    build_templates_sheet()

    print("\n=== template_changed.jpg ===")
    templates_by_doc = {}
    for doc_id in ts.DOCS:
        templates_by_page, _counts = sht.build_templates_for_doc(doc_id)
        templates_by_doc[doc_id] = templates_by_page
    build_changed_sheet(templates_by_doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
