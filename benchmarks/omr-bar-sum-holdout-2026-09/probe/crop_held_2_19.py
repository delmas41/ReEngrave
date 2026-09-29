"""ROADMAP 2.19 -- eight banded crops of held Breitkopf p1 bars, for Sean.

Reads the saved p1 record ONCE (via `record_io.load_record`) for geometry
only -- `Q.STAFF_LINES`, `Q.STAFF_SPACING`, `Q.CELL_BOX`, and each subject
glyph's own `bbox_page_px` -- and the base dump `held_funnel_2_19.py` wrote,
for which glyphs make each event. Renders the page straight off the PDF at
the gather's own DPI (600). No detector, no re-adjudication.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL: every drawn staff's own lines must
be materially darker than a half-space off them on the render, or the crop
is REFUSED (`crop_losers_2_6b._frame_ok`, imported, not restated).

⚠️ THE STAFF THE BAR IS FILED ON IS A TRANSLUCENT GREEN BAND with its lines
drawn over the print; a second staff named by the subject (an owner) is
BLUE. The bar's own `Q.CELL_BOX` x-span is marked by two red verticals and
the subject glyphs are bracketed RED at the exact box.

    python3 .../crop_held_2_19.py <record.json> <base-dump.json> <pdf>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-owner-domain-2026-09"))

OUT = HERE.parent / "out" / "print"
PREFIX = "held-2026-09-29"
DPI = 600

# (name, cell, event-x window in the cell frame or None, extra staff, what
#  the record says) -- chosen off FINDINGS §15's table, not sampled.
JOBS = [
    ("meter-header-read-as-head-staff0", (1, 0, 0, 0), (440, 480), None,
     "HEADER (bar 8). Print: 9/8. Template read 9/4 on 10 staves (runner-up "
     "6/4); a 'noteheadWhole' c4.0 event stands where the digits are."),
    ("meter-header-read-as-heads-staff1", (1, 0, 1, 0), (440, 480), None,
     "HEADER (bar 8). Print: 9/8. Four 'noteheadWhole' heads, one c4.0 "
     "chord event, stand where the digits are."),
    ("meter-change-bar9-read-as-heads-staff0", (1, 0, 0, 1), (180, 215),
     None, "BAR 9. Print: a 6/8 change on every staff. No meter reader "
     "fired here; three heads (c4.0 chord) stand where the digits are."),
    ("meter-change-bar9-read-as-heads-staff3", (1, 0, 3, 1), (180, 215),
     None, "BAR 9. Print: 6/8 change. Two 'noteheadWhole' heads (c2.0) "
     "stand where the digits are."),
    ("W-released-too-narrow-junk", (1, 0, 5, 2), None, None,
     "RELEASED by 2.19. One whole rest + 11 boxes refused not_a_notehead:"
     "too_narrow; size_measure_rest now marks it the bar."),
    ("W-released-duplicate-box", (1, 0, 1, 4), None, None,
     "RELEASED by 2.19. One whole rest + a second box on it refused "
     "rest_is_a_duplicate_box (2.15)."),
    ("W-released-neighbour-staff-rest", (1, 0, 7, 3), None, (1, 0, 8),
     "RELEASED by 2.19. One whole rest + staff 8's whole rest seen through "
     "the pad (glyph_owner DECIDED staff/1/0/8, distance). BLUE = staff 8."),
    ("W-still-held-system1-meter-abstained", None, None, None,
     "STILL HELD. A lone whole rest on system 1, where Q.METER abstains "
     "(carry_not_corroborated) so size_measure_rest never runs; the file "
     "carries 9/4 and 2.8 judges 4.0 against 9.0."),
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
    # the one system-1 W bar still held: the first, by cell, whose only
    # stream is a lone unmarked dotless 4-beat rest with nothing refused
    held_w = sorted(
        k for k, b in bars.items() if k[1] == 1 and len(b["streams"]) == 1
        and len(b["streams"][0]) == 1
        and b["streams"][0][0]["kind"] == "rest"
        and b["streams"][0][0]["beats"] == 4.0
        and not b["streams"][0][0]["measure_rest"]
        and not b["refused_in_cell"])
    jobs = [j if j[1] is not None else (j[0], held_w[0], None, None, j[4])
            for j in JOBS]

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

    pm = fitz.open(pdf)[1].get_pixmap(dpi=DPI)
    page = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    arr = np.asarray(page.convert("L"), dtype=float)
    font = ImageFont.load_default(size=26)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for n, (name, cell, xwin, extra, says) in enumerate(jobs, 1):
        p, s, st, c = cell
        skey = f"staff/{p}/{s}/{st}"
        ckey = f"cell/{p}/{s}/{st}/{c}"
        b = bars.get(cell)
        staves = [skey] + ([f"staff/{extra[0]}/{extra[1]}/{extra[2]}"]
                           if extra else [])
        ok = [_frame_ok(arr, lines[k], spacing[k]) for k in staves]
        if not all(o[0] for o in ok):
            manifest.append({"n": n, "name": name, "refused":
                             f"FRAME CONTROL FAILED {[round(o[1], 1) for o in ok]}"})
            continue
        # the subject glyphs: every glyph of the bar's events (or those in
        # the x window), plus refused boxes for the released bars
        subs = []
        for stream in (b["streams"] if b else []):
            for e in stream:
                if xwin and not (xwin[0] <= e["x"] <= xwin[1]):
                    continue
                subs += [g for g in e["glyphs"] if g]
        if not xwin and b:
            subs += [r["glyph"] for r in b["refused_in_cell"]]
        subs = sorted(set(subs))
        x0, _y0, x1, _y1 = cbox[ckey]
        sp = spacing[skey]
        ys = [y for k in staves for y in lines[k]]
        cy0 = int(min(ys) - 5 * sp)
        cy1 = int(max(ys) + 5 * sp)
        if xwin:
            gx = [gbox[g][1][0] for g in subs if g in gbox] + \
                 [gbox[g][1][2] for g in subs if g in gbox]
            cx0, cx1 = int(min(gx) - 8 * sp), int(max(gx) + 8 * sp)
        else:
            cx0, cx1 = int(x0 - 2 * sp), int(x1 + 2 * sp)
        cx0, cy0 = max(0, cx0), max(0, cy0)
        Z = 2
        crop = page.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for k, rgb in zip(staves, ((0, 170, 60), (30, 90, 255))):
            top, bot = (min(lines[k]) - cy0) * Z, (max(lines[k]) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=rgb + (50,))
            for y in lines[k]:
                od.line([0, (y - cy0) * Z, crop.width, (y - cy0) * Z],
                        fill=rgb + (200,), width=2)
        for xx in (x0, x1):
            od.line([(xx - cx0) * Z, 0, (xx - cx0) * Z, crop.height],
                    fill=(220, 0, 0, 200), width=3)
        for g in subs:
            if g not in gbox:
                continue
            bx0, by0, bx1, by1 = gbox[g][1]
            X0, Y0 = (bx0 - cx0) * Z - 4, (by0 - cy0) * Z - 4
            X1, Y1 = (bx1 - cx0) * Z + 4, (by1 - cy0) * Z + 4
            L = 12
            for a, bb in (((X0, Y0), (X0 + L, Y0)), ((X0, Y0), (X0, Y0 + L)),
                          ((X1, Y1), (X1 - L, Y1)), ((X1, Y1), (X1, Y1 - L))):
                od.line([a, bb], fill=(220, 0, 0, 255), width=3)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        import textwrap
        W = max(crop.width, 1100)
        text = [f"#{n} {ckey}  GREEN = filed staff {skey}"
                + (f"  BLUE = {staves[1]}" if extra else ""),
                "red verticals = the bar's Q.CELL_BOX x-span; red corners = "
                "subject boxes"]
        text += textwrap.wrap(says, width=int(W / 14))
        hh = 8 + 34 * len(text)
        head = Image.new("RGB", (W, hh), "white")
        hd = ImageDraw.Draw(head)
        for i, t in enumerate(text):
            hd.text((8, 6 + 34 * i), t, fill="black", font=font)
        sheet = Image.new("RGB", (W, crop.height + hh), "white")
        sheet.paste(head, (0, 0))
        sheet.paste(crop, (0, hh))
        fn = f"{PREFIX}-{n:02d}-{name}.png"
        sheet.save(OUT / fn)
        manifest.append({
            "n": n, "file": fn, "cell": ckey,
            "measure_in_file": (b or {}).get("report", {}).get("measure"),
            "part": (b or {}).get("report", {}).get("part"),
            "staves_drawn": staves, "subjects_bracketed": subs,
            "judged_quarters": (b or {}).get("detail", {}).get("want_quarters"),
            "read_quarters": (b or {}).get("detail", {}).get("quarters"),
            "record_says": says,
            "frame_contrast": [round(o[1], 1) for o in ok],
            "VERDICT_none_yet": None})
        print("wrote", fn)
    (OUT / f"{PREFIX}-manifest.json").write_text(
        json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
