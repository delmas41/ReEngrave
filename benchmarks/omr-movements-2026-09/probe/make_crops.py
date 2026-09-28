"""Cut the print-check crops for ROADMAP 4.2b's one real boundary
(Beethoven 5 / Litolff imslp984073, pdf 0-idx pages 16-17).

Frame control: each crop reports its own min/max pixel value so a flat
(all-white, all-black) crop is visible as a failure rather than passing
silently -- CLAUDE.md rule 7, "a control must be able to fail".

Regenerate RENDER_DIR's two PNGs with (pdftoppm 1-indexed page N == staged
0-indexed page N-1, so 0-idx pages 16/17 are pdftoppm pages 17/18):

    pdftoppm -f 17 -l 18 -r 600 -png \\
        library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \\
        <scratch>/render600/p
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RENDER_DIR = Path("<scratch>/render600")  # see docstring above
OUT_DIR = Path(__file__).resolve().parents[1] / "out" / "print"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# pdftoppm 1-indexed page N == staged 0-indexed page N-1
PAGE16_PNG = RENDER_DIR / "p-17.png"   # 0-idx page 16 -- end of movement 1
PAGE17_PNG = RENDER_DIR / "p-18.png"   # 0-idx page 17 -- Andante con moto opening


def _font(size):
    for candidate in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                      "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _frame_stats(im):
    gray = im.convert("L")
    lo, hi = gray.getextrema()
    return lo, hi, (hi - lo)


def _caption(draw, xy, text, color="red"):
    x, y = xy
    draw.rectangle([x - 2, y - 2, x + 6.5 * len(text) + 2, y + 20], fill="white", outline=color)
    draw.text((x, y), text, fill=color, font=_font(16))


def crop_boundary_head():
    """system/17/0's own header -- tempo word bracketed, full margin names
    visible, the wider indent visible against the continuation crop below."""
    im = Image.open(PAGE17_PNG).convert("RGB")
    box = (0, 230, 1750, 1950)
    crop = im.crop(box)
    draw = ImageDraw.Draw(crop)
    # tempo word bbox (page px) -- offset into the crop's own frame
    tw_box = [878.0, 288.0, 1302.0, 317.0]
    x0, y0, x1, y1 = (tw_box[0] - box[0], tw_box[1] - box[1],
                      tw_box[2] - box[0], tw_box[3] - box[1])
    # corner bracket on the exact tempo-word box, not a margin tick
    br = 14
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                           (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([(cx, cy), (cx + dx * br, cy)], fill="red", width=4)
        draw.line([(cx, cy), (cx, cy + dy * br)], fill="red", width=4)
    _caption(draw, (x0 - 4, y1 + 6), "tempo_word (cell 0, category=tempo)")
    # margin label column bracket -- FULL names
    draw.rectangle([2, 20, 260, 1710], outline="blue", width=4)
    _caption(draw, (6, 1716), "label_reset: FULL names (Flauti./Oboi./Clarinetti in B./.../Basso.)", color="blue")
    lo, hi, spread = _frame_stats(crop)
    path = OUT_DIR / "movements-01-boundary-head.png"
    crop.save(path)
    return path, {"page_px_box": list(box), "frame_min": lo, "frame_max": hi,
                  "frame_spread": spread}


def crop_continuation_head():
    """system/16/1's own header -- the CONTINUATION system directly before
    the boundary: abbreviated labels, no tempo word, no wider indent."""
    im = Image.open(PAGE16_PNG).convert("RGB")
    box = (0, 1980, 1750, 3200)
    crop = im.crop(box)
    draw = ImageDraw.Draw(crop)
    draw.rectangle([2, 20, 260, 1010], outline="blue", width=4)
    _caption(draw, (6, 1016), "abbreviated labels (Fl./Ob./Cl./Fag./Cor./Tr./Tp.) -- no reset, no tempo word here", color="blue")
    lo, hi, spread = _frame_stats(crop)
    path = OUT_DIR / "movements-02-continuation-head.png"
    crop.save(path)
    return path, {"page_px_box": list(box), "frame_min": lo, "frame_max": hi,
                  "frame_spread": spread}


def crop_tempo_word_zoom():
    """A tight zoom on the exact tempo-word box the DIRECTION_WORD reader
    filed, corner-bracketed -- the SUBJECT, not a margin tick at its x."""
    im = Image.open(PAGE17_PNG).convert("RGB")
    tw_box = [878.0, 288.0, 1302.0, 317.0]
    pad = 60
    box = (int(tw_box[0]) - pad, int(tw_box[1]) - pad,
          int(tw_box[2]) + pad, int(tw_box[3]) + pad)
    crop = im.crop(box).resize(
        ((box[2] - box[0]) * 3, (box[3] - box[1]) * 3), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)
    scale = 3
    x0 = (tw_box[0] - box[0]) * scale
    y0 = (tw_box[1] - box[1]) * scale
    x1 = (tw_box[2] - box[0]) * scale
    y1 = (tw_box[3] - box[1]) * scale
    br = 18
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                           (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([(cx, cy), (cx + dx * br, cy)], fill="red", width=3)
        draw.line([(cx, cy), (cx, cy + dy * br)], fill="red", width=3)
    _caption(draw, (10, crop.size[1] - 30),
            "subject glyph/17/0/0/0/90000: 'Andante con moto.' (tesseract)")
    lo, hi, spread = _frame_stats(crop)
    path = OUT_DIR / "movements-03-tempo-word-zoom.png"
    crop.save(path)
    return path, {"page_px_box": [tw_box[0] - pad, tw_box[1] - pad,
                                  tw_box[2] + pad, tw_box[3] + pad],
                  "subject": "glyph/17/0/0/0/90000", "frame_min": lo,
                  "frame_max": hi, "frame_spread": spread}


def main():
    manifest = {"window": {"pages_0idx": [16, 17], "dpi": 600,
                           "boundary_system": "system/17/0",
                           "continuation_system_shown": "system/16/1"},
               "crops": []}
    for fn, question in (
        (crop_boundary_head, "Does this system's header show a tempo heading "
                             "and FULL instrument names, wider than the "
                             "system before it?"),
        (crop_continuation_head, "Does the system directly before the "
                                 "boundary show only abbreviated labels and "
                                 "no tempo word?"),
        (crop_tempo_word_zoom, "Is the bracketed text really 'Andante con "
                               "moto' -- a tempo heading, not a dynamic or "
                               "expression mark?"),
    ):
        path, detail = fn()
        entry = {"file": path.name, "question": question, **detail,
                "VERDICT_none_yet": None}
        manifest["crops"].append(entry)
        print(f"wrote {path} frame_spread={detail['frame_spread']}")

    manifest_path = OUT_DIR / "crop-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
