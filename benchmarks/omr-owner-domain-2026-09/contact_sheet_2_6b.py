"""ROADMAP 2.6b — one contact sheet of all 24 `o26b-*` crops, labelled by
number, so Sean can answer in one pass.

    python3 benchmarks/omr-owner-domain-2026-09/contact_sheet_2_6b.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "out" / "print"
MANIFEST = OUT_DIR / "o26b-manifest.json"
COLS = 4
CELL_W, CELL_H = 620, 560
PAD = 10


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    crops = sorted(manifest["crops"], key=lambda c: c["n"])
    n_rows = -(-len(crops) // COLS)

    sheet = Image.new(
        "RGB", (COLS * CELL_W, n_rows * CELL_H), "white")
    dr = ImageDraw.Draw(sheet)
    font_big = ImageFont.load_default(size=34)
    font_small = ImageFont.load_default(size=16)

    for i, c in enumerate(crops):
        row, col = divmod(i, COLS)
        x0, y0 = col * CELL_W, row * CELL_H
        im = Image.open(OUT_DIR / c["file"]).convert("RGB")
        scale = min((CELL_W - 2 * PAD) / im.width,
                    (CELL_H - 2 * PAD - 26) / im.height)
        w, h = int(im.width * scale), int(im.height * scale)
        thumb = im.resize((w, h), Image.LANCZOS)
        px = x0 + (CELL_W - w) // 2
        py = y0 + 26 + (CELL_H - 26 - h) // 2
        sheet.paste(thumb, (px, py))
        dr.rectangle([x0, y0, x0 + CELL_W - 1, y0 + CELL_H - 1],
                     outline=(180, 180, 180), width=1)
        kind = "L" if c["kind"] == "loser" else "W"
        label_color = (200, 0, 0) if kind == "L" else (0, 130, 0)
        dr.text((x0 + 6, y0 + 2), f"#{c['n']:02d} [{kind}]", fill=label_color,
                font=font_big)
        term = c.get("deciding_term", "")
        direction = "upper->lower" if c.get("direction", "").startswith(
            "own_is_upper") else "lower->upper"
        cap = f"{c['subject']}  {term}  {direction}"
        dr.text((x0 + 6, y0 + CELL_H - 18), cap, fill=(0, 0, 0),
                font=font_small)

    out_path = OUT_DIR / "o26b-contact-sheet.png"
    sheet.save(out_path)
    print(f"wrote {out_path}  ({sheet.width}x{sheet.height}, "
          f"{len(crops)} crops)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
