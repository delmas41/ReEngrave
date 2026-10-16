"""ROADMAP 2.140 -- for every DECIDED eighth (beats 0.5, beam_levels 1) with a read stem, count the beam strokes the PAGE RASTER
shows at that stem, measured LOCALLY (CLAUDE.md section 5), independent of the record's beam rows (STAGED GATHER rows are
read only for the head box, its CV stem tip and the cell frame). The raster is NOT erased of staff lines first; staff-line
rows are filled only where ink stands on both sides of the line (a beam crossing it) so a line cannot split or add a stroke.

    python3 count_2_140.py lit|brah ROWS.json DURATIONS.json OUT.json [--pages 1,2] [--glyphs g1,g2]

A stroke = a vertical ink run, in the column 0.45 staff spaces beside the stem (the side with the longer run at the tip),
within [tip - 2.4 sp, tip + 0.3 sp], at least 0.28 sp thick. A run >= 1.6x the cell's single-beam thickness (median of runs
from notes whose runs are all single) counts twice (two beams fused: no gap to see).
"""
import json, sys, collections
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"brah": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
       "lit": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
MIN_TH_SP = 0.36
WIN_BEFORE_SP, WIN_AFTER_SP = 2.4, 0.3
OFFSET_SP = 0.45


def load(rows_path):
    """heads {glyph: page bbox}, stems {cell: [page (x0,y0,x1,y1)]} (CV stems, cell frame -> page by the cell's own
    detector-box scale), lines {(page,system,staff): [y]}."""
    heads, lines, scale, rawstems = {}, {}, {}, collections.defaultdict(list)
    for r in json.load(open(rows_path)):
        q, s = r["quantity"], r["subject"]
        if q == "glyph_box":
            d = r["detail"] or {}
            bp = d.get("bbox_page_px")
            if d.get("category") == "notehead":
                heads[s] = bp
            cell = tuple(int(x) for x in s.split("/")[1:5])
            v = r["value"]
            if bp and v[3] > 0 and cell not in scale:
                sc = (bp[2] - bp[0]) / v[3 - 1 + 0] if False else (bp[2] - bp[0]) / v[3 - 0] if False else None
                # value = [name, x, y, w, h] in the cell frame
                w, h = v[3], v[4]
                if w > 0:
                    sc = (bp[2] - bp[0]) / w
                    scale[cell] = (sc, bp[0] - v[1] * sc, bp[1] - v[2] * sc)
        elif q == "stem" and r["reader"] == "cv_lines":
            rawstems[tuple(int(x) for x in s.split("/")[1:5])].append(r["value"])
        elif q == "staff_lines":
            lines[tuple(int(x) for x in s.split("/")[1:4])] = r["value"]
    stems = {}
    for cell, vs in rawstems.items():
        if cell in scale:
            sc, ox, oy = scale[cell]
            stems[cell] = [(ox + x * sc, oy + y * sc, ox + (x + w) * sc, oy + (y + h) * sc) for x, y, w, h in vs]
    return heads, stems, lines


def column_ink(img, x, y0, y1, lines, half):
    """Boolean ink down column x (3 px wide), rows y0..y1. A staff-line BAND (line +- half px) is ink only where ink stands
    outside it on at least one side AND the raw ink is continuous from that side across the band (a beam crossing or touching
    the line); a lone line is erased, so it is never a stroke."""
    raw = (img[y0:y1, max(x - 1, 0):x + 2] > 0).mean(axis=1) >= 0.5
    col = raw.copy()
    n = len(col)
    for ly in lines:
        i = int(round(ly)) - y0
        lo, hi = i - half, i + half          # band rows lo..hi inclusive
        if hi < 0 or lo >= n:
            continue
        above = lo - 1 >= 0 and raw[lo - 1]
        below = hi + 1 < n and raw[hi + 1]
        for r in range(max(lo, 0), min(hi, n - 1) + 1):
            keep = False
            if above and raw[lo:r + 1].all():
                keep = True
            if below and raw[r:hi + 1].all():
                keep = True
            col[r] = keep
    return col


def runs(col):
    out, start = [], None
    for i, v in enumerate(col):
        if v and start is None:
            start = i
        if (not v or i == len(col) - 1) and start is not None:
            end = i if not v else i + 1
            out.append((start, end))
            start = None
    return out


def own_stem(head, stems, sp):
    """The CV stem standing on this head: x-range within 0.35 sp of the head's left or right edge, and its y-range touching the
    head's own y-range (0.4 sp slack). Returns (side, stem box) or None."""
    hx0, hy0, hx1, hy1 = head
    best = None
    for sb in stems:
        x0, y0, x1, y1 = sb
        xc = (x0 + x1) / 2
        if not (hx0 - 0.35 * sp <= xc <= hx1 + 0.35 * sp):
            continue
        if y1 < hy0 - 1.0 * sp or y0 > hy1 + 1.0 * sp:
            continue
        up_ext, down_ext = hy0 - y0, y1 - hy1
        side = "up" if up_ext > down_ext else "down"
        ext = max(up_ext, down_ext)
        if ext < 1.5 * sp:
            continue
        if best is None or ext > best[2]:
            best = (side, sb, ext)
    return None if best is None else best[:2]


def measure(img, head, stems, lines):
    """Uses the PRODUCT function `gather.beam_runs_at_stem_end` on the PAGE raster (page px), so probe and reader cannot differ."""
    from tools.omr.staged.gather import beam_runs_at_stem_end
    sp = float(np.mean(np.diff(lines)))
    o = own_stem(head, stems, sp)
    if o is None:
        return None
    side, sb = o
    tip = sb[1] if side == "up" else sb[3]
    end = "top" if side == "up" else "bottom"
    r = beam_runs_at_stem_end(img > 0, (sb[0] + sb[2]) / 2.0, tip, end, sp, list(lines), 0.0)
    return {"stem_x": int(round((sb[0] + sb[2]) / 2.0)), "tip_y": float(tip), "sp": sp, "side": side,
            "cols": {k: [[a, b, t] for a, b, t, _r in r[k]] for k in ("left", "right")}, "reach": {k: [x[3] for x in r[k]] for k in ("left", "right")}}


def main():
    mov, rows_path, dur_path, out_path = sys.argv[1:5]
    pages = None
    glyphs = None
    if "--pages" in sys.argv:
        pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")}
    if "--glyphs" in sys.argv:
        glyphs = set(sys.argv[sys.argv.index("--glyphs") + 1].split(","))
    heads, stems, lines = load(rows_path)
    dur = json.load(open(dur_path)) if dur_path != "-" else {}
    if glyphs is not None:
        todo = sorted(glyphs)
    else:
        todo = sorted(k for k, v in dur.items() if v[0] == "decided" and v[1] == 0.5 and v[2] == 1 and k in heads)
    res = {}
    cache = {}
    for g in todo:
        p = int(g.split("/")[1])
        if pages is not None and p not in pages:
            continue
        if p not in cache:
            cache = {p: (np.asarray(Image.fromarray(render_page(PDF[mov], p, dpi=600).rgb).convert("L")) < 128).astype(np.uint8)}
        img = cache[p]
        st = tuple(int(x) for x in g.split("/")[1:4])
        cell = tuple(int(x) for x in g.split("/")[1:5])
        if g not in heads or st not in lines or cell not in stems:
            res[g] = {"skip": "no_head_stem_or_staff"}
            continue
        m = measure(img, heads[g], stems[cell], lines[st])
        res[g] = m if m else {"skip": "no_own_stem"}
        if m:
            m["dur"] = dur.get(g)
    json.dump(res, open(out_path, "w"))
    c = collections.Counter()
    for g, m in res.items():
        if "skip" in m:
            c[m["skip"]] += 1
            continue
        n = max((len(v) for v in m["cols"].values()), default=0)
        c[f"runs{n}"] += 1
    print(dict(c))


main()
