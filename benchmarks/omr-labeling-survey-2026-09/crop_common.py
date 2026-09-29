"""Shared crop-rendering for the rest-experiment visual-check sheets.

Sean, 2026-09-29 (relayed after seeing a DIFFERENT audit's crops confuse
him): every crop must show at least the whole bar and the staff above/below,
shaded as bands; be >= 1000 px wide; draw every relevant box in a distinct
thick color with a large legend ON the image; and carry ONE plain question
at the top with exact answer codes. Never ask him to judge something the
crop doesn't draw.

This module renders the FULL cell (never a tight sub-crop around one box) --
these training cells are already cut tall (typically ~1200 px) to span a
whole system for cross-staff ownership (CLAUDE.md Sec 10), so the full cell
already contains the bar's own staff and, usually, ink above/below it. A
sub-crop would defeat exactly the thing Sean flagged.
"""
from __future__ import annotations

from pathlib import Path

MIN_WIDTH = 1200   # margin over Sean's ">= 1000 px" floor


def render_cell(image_path: str, ys: list, boxes: list, title: str, question: str,
                legend: list, out_path: Path) -> bool:
    """boxes: [(x0,y0,x1,y1,color,label), ...] in the cell's OWN pixel coords.
    legend: [(color, text), ...]. Renders the full cell, staff band(s) shaded,
    every box drawn thick with its label, a legend block, and one title +
    question line, all in a font that reads at contact-sheet scale."""
    import cv2
    from PIL import Image, ImageDraw, ImageFont

    img = cv2.imread(image_path)
    if img is None:
        return False
    H, W = img.shape[:2]
    zoom = max(2, -(-MIN_WIDTH // W))  # ceil division: smallest int zoom hitting MIN_WIDTH

    base = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    base = base.resize((W * zoom, H * zoom), Image.LANCZOS).convert("RGBA")

    if ys:
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        top, bot = (min(ys) * zoom, max(ys) * zoom)
        od.rectangle([0, top, base.width, bot], fill=(255, 210, 60, 50))
        for y in ys:
            yy = y * zoom
            od.line([(0, yy), (base.width, yy)], fill=(90, 90, 90, 210), width=max(2, zoom // 2))
        base = Image.alpha_composite(base, overlay)
    base = base.convert("RGB")
    dr = ImageDraw.Draw(base)

    box_font = ImageFont.load_default(size=max(18, 5 * zoom))
    for (x0, y0, x1, y1, color, label) in boxes:
        dr.rectangle([x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom], outline=color, width=max(4, zoom))
        if label:
            ly = max(0, y0 * zoom - box_font.size - 4)
            tw = dr.textlength(label, font=box_font)
            dr.rectangle([x0 * zoom, ly, x0 * zoom + tw + 8, ly + box_font.size + 4],
                        fill=(255, 255, 255, 230), outline=color, width=2)
            dr.text((x0 * zoom + 4, ly + 2), label, fill=color, font=box_font)

    # ── header band: title, ONE question with codes, legend ────────────────
    title_font = ImageFont.load_default(size=22)
    q_font = ImageFont.load_default(size=24)
    leg_font = ImageFont.load_default(size=20)
    pad = 10
    header_h = 34 + 34 + 30 * len(legend) + pad
    out_im = Image.new("RGB", (base.width, base.height + header_h), "white")
    hd = ImageDraw.Draw(out_im)
    hd.text((pad, pad), title, fill=(0, 0, 0), font=title_font)
    hd.text((pad, pad + 30), question, fill=(120, 0, 0), font=q_font)
    ly = pad + 30 + 34
    for color, text in legend:
        hd.rectangle([pad, ly + 4, pad + 26, ly + 24], outline=color, fill=color, width=3)
        hd.text((pad + 34, ly), text, fill=(0, 0, 0), font=leg_font)
        ly += 30
    out_im.paste(base, (0, header_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_im.save(out_path)
    return True


def render_pair(before_path: str, after_path: str, ys: list, box, title: str, question: str,
                 legend: list, out_path: Path) -> bool:
    """Side-by-side BEFORE/AFTER of the full cell, same box drawn on both."""
    import cv2
    from PIL import Image, ImageDraw, ImageFont

    imgs = [cv2.imread(p) for p in (before_path, after_path)]
    if any(im is None for im in imgs):
        return False
    H, W = imgs[0].shape[:2]
    zoom = max(2, -(-((MIN_WIDTH // 2)) // W))

    panels = []
    box_font = ImageFont.load_default(size=max(18, 5 * zoom))
    for img in imgs:
        p = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        p = p.resize((W * zoom, H * zoom), Image.LANCZOS).convert("RGBA")
        if ys:
            overlay = Image.new("RGBA", p.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            top, bot = (min(ys) * zoom, max(ys) * zoom)
            od.rectangle([0, top, p.width, bot], fill=(255, 210, 60, 50))
            for y in ys:
                yy = y * zoom
                od.line([(0, yy), (p.width, yy)], fill=(90, 90, 90, 210), width=max(2, zoom // 2))
            p = Image.alpha_composite(p, overlay)
        p = p.convert("RGB")
        dr = ImageDraw.Draw(p)
        if box:
            x0, y0, x1, y1, color, label = box
            dr.rectangle([x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom], outline=color, width=max(4, zoom))
            if label:
                ly = max(0, y0 * zoom - box_font.size - 4)
                dr.text((x0 * zoom + 4, ly + 2), label, fill=color, font=box_font)
        panels.append(p)

    gap = 16
    w = panels[0].width * 2 + gap
    title_font = ImageFont.load_default(size=22)
    q_font = ImageFont.load_default(size=24)
    leg_font = ImageFont.load_default(size=20)
    lab_font = ImageFont.load_default(size=26)
    pad = 10
    header_h = 34 + 34 + 30 * len(legend) + pad
    panel_label_h = 34
    out_im = Image.new("RGB", (w, panels[0].height + header_h + panel_label_h), "white")
    hd = ImageDraw.Draw(out_im)
    hd.text((pad, pad), title, fill=(0, 0, 0), font=title_font)
    hd.text((pad, pad + 30), question, fill=(120, 0, 0), font=q_font)
    ly = pad + 30 + 34
    for color, text in legend:
        hd.rectangle([pad, ly + 4, pad + 26, ly + 24], outline=color, fill=color, width=3)
        hd.text((pad + 34, ly), text, fill=(0, 0, 0), font=leg_font)
        ly += 30
    hd.text((pad, header_h), "BEFORE", fill=(0, 0, 0), font=lab_font)
    hd.text((panels[0].width + gap + pad, header_h), "AFTER (painted)", fill=(0, 0, 0), font=lab_font)
    out_im.paste(panels[0], (0, header_h + panel_label_h))
    out_im.paste(panels[1], (panels[0].width + gap, header_h + panel_label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_im.save(out_path)
    return True
