"""ROADMAP 2.21 -- banded crops of Breitkopf p1 bars whose minimal fix set
(2.19, `classify_held_2_19.py`) needs `V` (a voice split), so Sean can answer
the convention question before any code (rule 3).

Reads the saved p1 record ONCE (via `record_io.load_record`) for geometry
only -- `Q.STAFF_LINES`, `Q.STAFF_SPACING`, `Q.CELL_BOX`, and each subject
glyph's own `bbox_page_px` -- and 2.19's own base dump
(`out/r219/held-brahms-p1-base.json`) for which glyphs the record's
`Q.VOICES` verdict put in which stream. Renders the page straight off the
PDF at the gather's own DPI (600). No detector, no re-adjudication, no
`tools/` change.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL: every drawn staff's own lines must
be materially darker than a half-space off them on the render, or the crop
is REFUSED (`crop_losers_2_6b._frame_ok`, imported, not restated).

⚠️ THE STAFF THE BAR IS FILED ON IS A TRANSLUCENT GREEN BAND with its lines
drawn over the print; the bar's own `Q.CELL_BOX` x-span is two red
verticals. Heads the record's `Q.VOICES` verdict put in voice 1 are boxed
ORANGE, voice 2 PURPLE -- a legend states which is which on every sheet.

    python3 .../crop_voice_split_2_21.py <record.json> <held-base-dump.json> <pdf>
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-owner-domain-2026-09"))

OUT = HERE.parent / "out" / "print"
PREFIX = "voice-2026-09-29"
DPI = 600

VOICE_COLOURS = ((255, 140, 0), (150, 40, 200))  # orange voice 1, purple voice 2

# The 8 bars whose minimal fix set is `MV` ALONE (no other confound) --
# chosen off classify_held_2_19.py's own per-bar table (FINDINGS §15c),
# not sampled. (cell, measure-in-file, what the two streams read as pitch
# sequences in x-order -- the fact the crop exists to check).
JOBS = [
    ((1, 0, 1, 5), 6,
     "Time order by x: rest, rest, Db5(v2), Db5(v2), E4(v1). The two "
     "streams never sound together -- v1's only note comes AFTER v2's."),
    ((1, 0, 1, 6), 7,
     "Time order by x: E4(v1), B4(v2), B4(v2), Db4(v1). One descent "
     "crossing back over itself; no shared x."),
    ((1, 1, 3, 5), 13,
     "Time order by x: Ab3, G3, F3 (v2), then Eb3, Db3, Ab2 (v1) -- ONE "
     "continuous descending scale, split where the stem flips."),
    ((1, 0, 10, 2), 3,
     "Time order by x: B4(v2), 3 shared rests, Ab4(v1), Ab4(v1). No note "
     "of v1 and v2 shares an x."),
    ((1, 0, 11, 4), 5,
     "Time order by x: Ab3(v2), F4(v2), Ab3(v1), Ab3(v1), G3(v1), G3(v1). "
     "A leap around the middle line, not two lines sounding together."),
    ((1, 1, 10, 3), 11,
     "Time order by x: F3(v1), D4(v1), C4(v2), Bb3(v1), Bb3(v1), C4+C4(v2). "
     "No shared x between v1 and v2."),
    ((1, 1, 11, 0), 8,
     "Time order by x: Db3(v2), then FIVE repeats of Gb2(v1). v2's one "
     "note finishes before v1 starts."),
    ((1, 1, 11, 3), 11,
     "Time order by x: Bb2, Bb2, C3, D3 (v1), then D3, Eb3 (v2) -- one "
     "continuous ascending bass line."),
]


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from crop_losers_2_6b import _frame_ok
    from tools.omr.staged.record_io import load_record

    rec_path, dump_path, pdf = sys.argv[1:4]
    dump = json.load(open(dump_path))
    bars = {tuple(b["cell"]): b for b in dump["bars"]}

    doc = load_record(rec_path)
    rec = doc.get("record", doc)
    lines, spacing, cbox, gbox = {}, {}, {}, {}
    for o in rec["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "staff_lines" and o["frame"] == "page":
            lines[s] = list(o["value"])
        elif q == "staff_spacing" and o["frame"] == "page":
            spacing[s] = float(o["value"])
        elif q == "cell_box":
            cbox[s] = list(o["value"])
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                gbox[s] = (o["value"], bp)

    pdoc = fitz.open(pdf)
    pm = pdoc[1].get_pixmap(dpi=DPI)
    page = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    arr = np.asarray(page.convert("L"), dtype=float)
    font = ImageFont.load_default(size=26)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for n, (cell, measure, says) in enumerate(JOBS, 1):
        p, s, st, c = cell
        skey = f"staff/{p}/{s}/{st}"
        ckey = f"cell/{p}/{s}/{st}/{c}"
        b = bars.get(cell)
        if b is None:
            manifest.append({"n": n, "cell": ckey, "refused": "bar not in dump"})
            continue
        ok, contrast = _frame_ok(arr, lines[skey], spacing[skey])
        if not ok:
            manifest.append({"n": n, "cell": ckey,
                             "refused": f"FRAME CONTROL FAILED {round(contrast, 1)}"})
            continue
        voice_of = {}
        for vi, stream in enumerate(b["streams"]):
            for e in stream:
                for g in (e.get("glyphs") or []):
                    if g:
                        voice_of.setdefault(g, vi)
        x0, _y0, x1, _y1 = cbox[ckey]
        sp = spacing[skey]
        ys = lines[skey]
        cy0 = int(min(ys) - 5 * sp)
        cy1 = int(max(ys) + 5 * sp)
        cx0, cx1 = int(x0 - 2 * sp), int(x1 + 2 * sp)
        cx0, cy0 = max(0, cx0), max(0, cy0)
        Z = 2
        crop = page.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        top, bot = (min(ys) - cy0) * Z, (max(ys) - cy0) * Z
        od.rectangle([0, top, crop.width, bot], fill=(0, 170, 60) + (50,))
        for y in ys:
            od.line([0, (y - cy0) * Z, crop.width, (y - cy0) * Z],
                    fill=(0, 170, 60, 200), width=2)
        for xx in (x0, x1):
            od.line([(xx - cx0) * Z, 0, (xx - cx0) * Z, crop.height],
                    fill=(220, 0, 0, 200), width=3)
        for g, vi in voice_of.items():
            if g not in gbox:
                continue
            rgb = VOICE_COLOURS[vi % len(VOICE_COLOURS)]
            bx0, by0, bx1, by1 = gbox[g][1]
            X0, Y0 = (bx0 - cx0) * Z - 5, (by0 - cy0) * Z - 5
            X1, Y1 = (bx1 - cx0) * Z + 5, (by1 - cy0) * Z + 5
            od.rectangle([X0, Y0, X1, Y1], outline=rgb + (255,), width=4)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        W = max(crop.width, 1150)
        text = [f"#{n} {ckey}  measure {measure} in file  GREEN band = the "
                "filed staff",
                "red verticals = the bar's Q.CELL_BOX x-span  "
                "ORANGE box = voice 1  PURPLE box = voice 2"]
        text += textwrap.wrap(says, width=int(W / 14))
        text.append("QUESTION: is this ONE line whose stem flips at the "
                     "middle line, or genuinely two voices?")
        hh = 8 + 34 * len(text)
        head = Image.new("RGB", (W, hh), "white")
        hd = ImageDraw.Draw(head)
        for i, t in enumerate(text):
            hd.text((8, 6 + 34 * i), t, fill="black", font=font)
        sheet = Image.new("RGB", (W, crop.height + hh), "white")
        sheet.paste(head, (0, 0))
        sheet.paste(crop, (0, hh))
        fn = f"{PREFIX}-{n:02d}.png"
        sheet.save(OUT / fn)
        manifest.append({
            "n": n, "file": fn, "cell": ckey, "measure_in_file": measure,
            "voices_glyphs": {str(vi): sorted(g for g, vv in voice_of.items()
                                              if vv == vi)
                              for vi in {0, 1}},
            "record_says": says,
            "frame_contrast": round(contrast, 1),
            "VERDICT_none_yet": None})
        print("wrote", fn)
    (OUT / f"{PREFIX}-manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
