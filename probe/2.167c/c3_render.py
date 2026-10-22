"""2.167c probe 3: render one held bar: LEFT the page crop, RIGHT the exporter's events (what it summed) drawn / listed.
Import `render_bar(doc_key, row, ...)`. Colours: black READ, blue #1F6FEB GUESSED, red UNREAD / not-written ink.
"""
import os

import fitz
from PIL import Image, ImageDraw, ImageFont

LIT = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
BRA = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
_DOCS = {}
BLUE, RED, BLACK, GREY = (31, 111, 235), (210, 30, 30), (0, 0, 0), (120, 120, 120)


def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def doc(key):
    if key not in _DOCS:
        _DOCS[key] = fitz.open(LIT if key == "lit" else BRA)
    return _DOCS[key]


TYPE = {"whole": "w", "half": "h", "quarter": "q", "eighth": "8", "16th": "16", "32nd": "32", "64th": "64"}


def val(e):
    t = TYPE.get(e.get("duration_type"), str(e.get("duration_type")))
    return t + "." * int(e.get("dots") or 0)


def ev_status(e):
    """READ / GUESSED for an event as the exporter wrote it."""
    for h in e.get("heads", []):
        if h.get("guess"):
            return "G"
    if e.get("rest") and e["rest"].get("guess"):
        return "G"
    return "R"


def crop(key, row, zoom, pad_sp=1.0):
    sp = row["spacing"]
    x0, y0, x1, y1 = row["box"]
    top = row["top"]
    r = (x0 - pad_sp * sp, top - 6.5 * sp, x1 + pad_sp * sp, top + 10.5 * sp)
    k = 72 / 600
    pix = doc(key)[row["page"]].get_pixmap(matrix=fitz.Matrix(600 / 72, 600 / 72), clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx = zoom * 1.0
    im = im.resize((int(im.width * sx), int(im.height * sx)), Image.LANCZOS)
    f = im.width / (r[2] - r[0])
    return im, r, f


def render_bar(key, row, zoom=2.0, width_text=330, draw_boxes=True, header=None, footer=None, show_unwritten=True):
    sp = row["spacing"]
    im, r, f = crop(key, row, zoom)
    d = ImageDraw.Draw(im)
    # barline guides
    x0, y0, x1, y1 = row["box"]
    for bx in (x0, x1):
        d.line([((bx - r[0]) * f, 0), ((bx - r[0]) * f, im.height)], fill=(150, 200, 150), width=1)
    ft = font(15)
    fs = font(12)
    if draw_boxes:
        for i, e in enumerate(row["events"]):
            items = [h.get("bbox_page") for h in e.get("heads", [])] if e["kind"] == "chord" else [(e["rest"] or {}).get("bbox_page")]
            col = BLUE if ev_status(e) == "G" else (0, 150, 0)
            for bb in items:
                if not bb:
                    continue
                bx0, by0 = (bb[0] - r[0]) * f, (bb[1] - r[1]) * f
                bx1, by1 = (bb[0] + bb[2] - r[0]) * f, (bb[1] + bb[3] - r[1]) * f
                d.rectangle([bx0, by0, bx1, by1], outline=col, width=1)
                d.text((bx0, by0 - 14), str(i + 1), fill=col, font=fs)
        if show_unwritten:
            wr = {h.get("glyph") for e in row["events"] for h in e.get("heads", [])} | {(e["rest"] or {}).get("glyph") for e in row["events"]}
            for b in row.get("boxes", []):
                if b["sub"] in wr or not b.get("bbox"):
                    continue
                if str(b["fate"]).startswith("not_a_notehead") or b["fate"] in ("owned_by_another_staff", "mark_group_duplicate", "written"):
                    continue
                bb = b["bbox"]
                d.rectangle([(bb[0] - r[0]) * f, (bb[1] - r[1]) * f, (bb[2] - r[0]) * f, (bb[3] - r[1]) * f], outline=RED, width=2)
    return im


def events_text(row):
    """lines, colour per line"""
    div = row["held"]["divisions"]
    lines = []
    for i, e in enumerate(row["events"]):
        if e["kind"] == "rest":
            s = "r%s%s" % (val(e), " (bar)" if (e.get("rest") or {}).get("measure_rest") else "")
        else:
            ps = "+".join(h.get("pitch", "?") for h in e["heads"])
            s = "%s %s %s" % (val(e), ps, {"up": "^", "down": "v"}.get(e.get("stem_direction"), "?"))
        lines.append(("%d  %s  [%.2g]" % (i + 1, s, e["units"] / div), BLUE if ev_status(e) == "G" else BLACK))
    return lines
