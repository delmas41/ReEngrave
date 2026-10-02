#!/usr/bin/env python3
"""lane-ledger-template (2026-10-02, Sean): two phone-sized contact
sheets for the GEOMETRY-drawn head templates (`head_template.
build_geometry_templates`, `score_head_template.
build_geometry_templates_for_doc`).

DRAWING ONLY -- same local-monkeypatch measurement harness as
`template_sheets.py`, nothing wired into any product/default path.

  1. template_geom_templates.jpg -- each drawn geometry template, next
     to 3 REAL clean heads from that same page at the SAME canonical
     scale, so Sean can compare shape and tilt directly.
  2. template_geom_changed.jpg -- every far head whose verdict differs
     round8 -> geom_template, matched template overlaid at its own
     matched centre.

    python3 benchmarks/omr-local-staff-2026-09/template_geom_sheets.py
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
import template_sheets as tsh  # noqa: E402 (reuse `_tile`'s drawing helpers)
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.annotate import head_template as ht  # noqa: E402

OUT_DIR = REPO / "out" / "print" / "ledgers"
COLS = 3
MAX_SHEET_W = 2600
JPEG_QUALITY = 85
UPSCALE = 3

RED = (0, 0, 220)
GREEN = (60, 190, 60)
ORANGE = (30, 140, 255)
YELLOW = (0, 220, 220)
BLACK = (0, 0, 0)


def _template_patch(tmpl: "ht.Template") -> np.ndarray:
    img = (tmpl.img * 255).clip(0, 255).astype(np.uint8)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return cv2.resize(img, (img.shape[1] * UPSCALE, img.shape[0] * UPSCALE),
                      interpolation=cv2.INTER_NEAREST)


def _real_head_patch(gray, box, spacing) -> np.ndarray:
    """A real clean head, cropped the SAME way `head_template.
    _extract_canonical_patch` does, so it sits at the SAME canonical
    scale as the drawn template beside it."""
    patch = ht._extract_canonical_patch(gray, (box[0] + box[2]) / 2.0,
                                        (box[1] + box[3]) / 2.0, spacing)
    if patch is None:
        patch = np.zeros((ht.CANONICAL_H, ht.CANONICAL_W), dtype=np.float32)
    img = (patch * 255).clip(0, 255).astype(np.uint8)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return cv2.resize(img, (img.shape[1] * UPSCALE, img.shape[0] * UPSCALE),
                      interpolation=cv2.INTER_NEAREST)


def _row_tile(doc_id, page_label, key, tmpl, real_patches, real_subjects):
    drawn = _template_patch(tmpl)
    patches = [drawn] + real_patches
    h = max(p.shape[0] for p in patches)
    w = sum(p.shape[1] for p in patches) + 8 * (len(patches) - 1)
    row = np.full((h, w, 3), 255, dtype=np.uint8)
    x = 0
    for p in patches:
        row[:p.shape[0], x:x + p.shape[1]] = p
        x += p.shape[1] + 8

    kind, variant = key
    lines_text = [
        f"{doc_id}  page={page_label}  {kind}/{variant} (geometry, drawn)",
        "left: drawn template -- right: " + ", ".join(real_subjects),
    ]
    font, font_scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    text_w = max(cv2.getTextSize(t, font, font_scale, thickness)[0][0] for t in lines_text)
    canvas_w = max(row.shape[1], text_w + 16)
    legend_h = 24 * (len(lines_text) + 1)
    out = np.full((row.shape[0] + legend_h, canvas_w, 3), 255, dtype=np.uint8)
    out[:row.shape[0], :row.shape[1]] = row
    for i, t in enumerate(lines_text):
        cv2.putText(out, t, (8, row.shape[0] + 20 + i * 22),
                    font, font_scale, BLACK, thickness, cv2.LINE_AA)
    return out


def build_templates_sheet():
    tiles = []
    for doc_id in ts.DOCS:
        templates_by_page, info = sht.build_geometry_templates_for_doc(doc_id)
        print(f"  {doc_id}: {info}")

        loaded = ts.load_doc(doc_id)
        rec = loaded["rec"]
        pages = score.PageCache(loaded["cfg"])
        far_rows = score._far_head_rows(doc_id, loaded)
        far_pages = sorted({r["page"] for r in far_rows})

        for page in far_pages:
            gray = pages.get(page)
            glyph_boxes = sht._page_glyph_boxes(rec).get(page, [])
            by_subject = {s: (cls, box) for (s, cls, box) in glyph_boxes}

            # 3 clean on-staff heads per kind for comparison.
            examples = {"filled": [], "hollow": []}
            for o in rec.observations:
                if o["quantity"] != Q.NOTEHEAD_STAFF_POSITION:
                    continue
                sub = o["subject"]
                if int(sub.split("/")[1]) != page:
                    continue
                from tools.omr.annotate import ledger_grid as lg
                pos = float(o["value"])
                if lg.far_head_needs_ledger_read(int(round(pos))):
                    continue
                entry = by_subject.get(sub)
                if entry is None:
                    continue
                cls, box = entry
                kind = "filled" if "Black" in cls else ("hollow" if (
                    "Half" in cls or "Whole" in cls) else None)
                if kind is None or len(examples[kind]) >= 3:
                    continue
                staff_key = f"staff/{sub.split('/')[1]}/{sub.split('/')[2]}/{sub.split('/')[3]}"
                line_rows = rec.obs(Q.STAFF_LINES, staff_key)
                if not line_rows:
                    continue
                global_lines = [float(y) for y in line_rows[-1]["value"]]
                lines = score.frame_lines_for_head(gray, global_lines, box)
                spacing = (max(lines) - min(lines)) / 4.0
                examples[kind].append((sub, box, spacing))

            tmpls = templates_by_page.get(page, {})
            for key in sorted(tmpls.keys()):
                kind, variant = key
                ex = examples.get(kind, [])
                real_patches = [_real_head_patch(gray, box, spacing)
                               for (_s, box, spacing) in ex]
                real_subjects = [s for (s, _b, _sp) in ex]
                tiles.append(_row_tile(doc_id, str(page), key, tmpls[key],
                                       real_patches, real_subjects))

    if not tiles:
        print("  no geometry templates built -- nothing to sheet")
        return

    tile_w = max(t.shape[1] for t in tiles)
    tile_h = max(t.shape[0] for t in tiles)
    sheet = np.full((len(tiles) * tile_h, tile_w, 3), 255, dtype=np.uint8)
    for i, t in enumerate(tiles):
        th, tw = t.shape[:2]
        sheet[i * tile_h:i * tile_h + th, :tw] = t

    if sheet.shape[1] > MAX_SHEET_W:
        f = MAX_SHEET_W / sheet.shape[1]
        sheet = cv2.resize(sheet, (int(sheet.shape[1] * f), int(sheet.shape[0] * f)),
                           interpolation=cv2.INTER_AREA)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jpg_path = OUT_DIR / "template_geom_templates.jpg"
    cv2.imwrite(str(jpg_path), sheet, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    print(f"  wrote {jpg_path} ({len(tiles)} tiles, {sheet.shape[1]}x{sheet.shape[0]})")


def main() -> int:
    print("=== template_geom_templates.jpg ===")
    build_templates_sheet()

    print("\n=== template_geom_changed.jpg ===")
    templates_by_doc = {}
    for doc_id in ts.DOCS:
        templates_by_page, _info = sht.build_geometry_templates_for_doc(doc_id)
        templates_by_doc[doc_id] = templates_by_page
    tsh.build_changed_sheet(templates_by_doc)
    # `build_changed_sheet` always writes `template_changed.jpg` -- rename
    # to this sheet's own name so neither run overwrites the other.
    src = OUT_DIR / "template_changed.jpg"
    dst = OUT_DIR / "template_geom_changed.jpg"
    if src.exists():
        src.replace(dst)
        print(f"  renamed to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
