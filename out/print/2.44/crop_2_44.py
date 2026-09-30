"""ROADMAP 2.44 print check — crops every pitch this lane's substitution
actually CHANGED, plus one CONFLICT case (the substitution declined and the
staff's own extrapolated reading stood).

Renders the real PDF page at 600 dpi (the CLI's own default), crops a window
around the head, and draws:
  - the staff's OUTER line (from this reader's own page-frame anchor,
    derived from the pre-existing `Q.LEDGER_RUNG_INK` `want_y_page` rows at
    two steps -- the SAME evenly-spaced prediction `gather_notehead_
    positions` extrapolates, in solid YELLOW, labelled "extrapolated")
  - every MEASURED printed ledger this lane's own reader found, converted
    from its own canonical-frame `note` field into page pixels via the
    scale ratio between canonical and page-frame spacing (both already on
    the record), in solid RED
  - the head's own `bbox_page_px`, a corner bracket (CLAUDE.md, "the
    SUBJECT marked")
  - a text label naming the OLD (extrapolated) pitch, the NEW (measured)
    pitch and Sean's own confirmed print reading where known

No source-text assertions; reads the record ONLY through
`record_io.load_record`.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab56d1d321c30c4bd")

from tools.omr.staged.record_io import load_record
from tools.omr.pitch_resolver import _pitch_from_position

DPI = 600
OUT_DIR = Path(__file__).resolve().parent


def _staff_of(subject: str) -> str:
    # glyph/p/s/st/c/g -> staff/p/s/st
    parts = subject.split("/")
    return "/".join(["staff"] + parts[1:4])


def _find(rows, subject, quantity):
    return [o for o in rows if o["subject"] == subject and o["quantity"] == quantity]


def _page_edge_and_spacing(obs, subject, candidate):
    """Recover the PAGE-frame staff edge and spacing from the OLD (2.6d/
    2.37), still-gathered `Q.LEDGER_RUNG_INK` rows at two steps toward
    `candidate` -- `want_y_page = edge -/+ k*spacing_page`, so two steps
    solve for both unknowns with no other conversion needed."""
    rows = [o for o in obs if o["subject"] == subject
           and o["quantity"] == "ledger_rung_ink"
           and o["detail"].get("candidate") == candidate]
    by_step = {o["detail"]["step"]: o["detail"]["want_y_page"] for o in rows}
    if 1 not in by_step or 2 not in by_step:
        return None, None
    w1, w2 = by_step[1], by_step[2]
    spacing = abs(w1 - w2)
    # sign: whether the ladder counts DOWN in page-y (below staff) or UP
    # (above staff) is recoverable from which is larger
    if w1 > w2:      # counting UPWARD (above the staff): w1 nearer edge
        edge = w1 + spacing
    else:
        edge = w1 - spacing
    return edge, spacing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--confirmed", default=None,
                    help="Sean's confirmed pitch, if known, for the label")
    args = ap.parse_args(argv)

    import fitz
    from PIL import Image, ImageDraw, ImageFont

    rec = load_record(args.record)["record"]
    obs = rec["observations"]
    subject = args.subject
    staff = _staff_of(subject)

    gbox = _find(obs, subject, "glyph_box")[0]
    px0, py0, px1, py1 = gbox["detail"]["bbox_page_px"]
    head_cx = (px0 + px1) / 2.0
    head_cy = (py0 + py1) / 2.0

    pos_rows = _find(obs, subject, "notehead_staff_position")
    pos_raw = pos_rows[0]["value"] if pos_rows else None
    old_step = int(round(float(pos_raw))) if pos_raw is not None else None

    led_rows = _find(obs, subject, "ledger_printed_position")
    led_value = led_rows[0]["value"] if led_rows else None
    led_detail = led_rows[0]["detail"] if led_rows else {}
    note = led_detail.get("note", "")

    css_rows = _find(obs, subject.rsplit("/", 1)[0].replace("glyph", "cell", 1)
                     if False else subject, "cell_staff_space")
    # cell_staff_space is filed on the CELL subject, not the glyph -- derive
    # the cell key the same way gather.py does (page/system/staff/cell).
    parts = subject.split("/")
    cell_key = "/".join(["cell"] + parts[1:5])
    css_rows = _find(obs, cell_key, "cell_staff_space")
    spacing_canon = css_rows[0]["value"] if css_rows else None

    edge_page, spacing_page = _page_edge_and_spacing(obs, subject, staff)
    up = (spacing_canon / spacing_page) if (spacing_canon and spacing_page) else None

    m = re.search(r"rungs \(canonical y\) \[([^\]]*)\], head centre ([\d.]+)", note)
    rung_ys_page = []
    if m and up:
        canon_list = [float(x) for x in m.group(1).split(",") if x.strip()]
        canon_head = float(m.group(2))
        for cy in canon_list:
            rung_ys_page.append(head_cy + (cy - canon_head) / up)

    old_pitch = _pitch_from_position(old_step, "treble") if old_step is not None else None
    new_step = int(round(float(led_value))) if led_value is not None else None
    new_pitch = _pitch_from_position(new_step, "treble") if new_step is not None else None

    doc = fitz.open(args.pdf)
    pno = int(parts[1])
    page = doc[pno]
    zoom = DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pad = 80
    clip = fitz.Rect((head_cx - 220) / zoom, (min([head_cy, edge_page or head_cy] + rung_ys_page) - pad) / zoom,
                     (head_cx + 220) / zoom, (max([head_cy, edge_page or head_cy] + rung_ys_page) + pad) / zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGB")
    draw = ImageDraw.Draw(img)

    ox = clip.x0 * zoom
    oy = clip.y0 * zoom

    def to_xy(px, py):
        return (px - ox, py - oy)

    w = img.width
    if edge_page is not None:
        y = edge_page - oy
        draw.line([(0, y), (w, y)], fill=(230, 200, 0), width=2)
        draw.text((4, y - 14), "extrapolated staff edge", fill=(180, 140, 0))
        for k in range(1, 4):
            for sign in (-1, 1):
                yy = edge_page + sign * k * (spacing_page or 0) - oy
                draw.line([(0, yy), (w, yy)], fill=(230, 200, 0), width=1)

    for i, ry in enumerate(rung_ys_page):
        y = ry - oy
        draw.line([(0, y), (w, y)], fill=(220, 0, 0), width=2)
        draw.text((w - 140, y - 14), f"measured ledger {i+1}", fill=(200, 0, 0))

    hx0, hy0 = to_xy(px0, py0)
    hx1, hy1 = to_xy(px1, py1)
    draw.rectangle([hx0, hy0, hx1, hy1], outline=(0, 120, 255), width=3)
    bl = 14
    draw.line([(hx0, hy0), (hx0 + bl, hy0)], fill=(0, 120, 255), width=3)
    draw.line([(hx0, hy0), (hx0, hy0 + bl)], fill=(0, 120, 255), width=3)

    label = (f"{subject}\nold(staff-extrapolated)={old_pitch} (step {old_step})\n"
            f"new(measured ledgers)={new_pitch} (step {new_step}, "
            f"{led_detail.get('bracket')})")
    if args.confirmed:
        label += f"\nSean confirmed: {args.confirmed}"
    draw.multiline_text((4, 4), label, fill=(0, 0, 0))

    out_path = OUT_DIR / f"{args.tag}.png"
    img.save(out_path)
    print(f"wrote {out_path}  old={old_pitch} new={new_pitch} "
         f"edge_page={edge_page} spacing_page={spacing_page} up={up} "
         f"rungs_page={rung_ys_page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
