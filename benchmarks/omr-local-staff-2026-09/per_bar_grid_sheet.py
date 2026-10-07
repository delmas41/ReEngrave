"""ROADMAP 2.57 sheet: 8 fixed bars, old grid red, new grid blue, against the ink.

  python3 benchmarks/omr-local-staff-2026-09/per_bar_grid_sheet.py <litolff.extract.json> <brahms.extract.json>

Each panel is one bar (the cell's own box), numbered. Red = the five rows the
bar was stored with before (`OMR_CELL_LINE_FIND` off), blue = after. Two
in-staff heads whose half-step position changed are bracketed (A, B) and named
in words, counting lines and spaces from the BOTTOM of the staff, before ->
after. The drawn lines are re-read from the panel's own pixels and compared to
the rows they were meant to be drawn at (DRAWING CHECK).
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from per_bar_grid_one_line_off import DOCS  # noqa: E402

Z = 3
RED, BLUE, GREEN = (220, 0, 0), (0, 80, 255), (0, 150, 0)
LINE_ORD = ["5th line (top)", "4th line", "3rd line", "2nd line", "1st line (bottom)"]


def words(step: int) -> str:
    """Half-steps from the top line (0 = top line) in words, counting from the bottom."""
    if 0 <= step <= 8:
        if step % 2 == 0:
            return LINE_ORD[step // 2]
        return ["", "space between 4th and 5th line", "", "space between 3rd and 4th line", "",
                "space between 2nd and 3rd line", "", "space between 1st and 2nd line"][step]
    if step < 0:
        n = -step
        return f"space above the staff" if n == 1 else (f"line above the staff ({n // 2}th ledger)" if n % 2 == 0 else f"space {n // 2 + 1} above the staff")
    n = step - 8
    return "space below the staff" if n == 1 else f"ledger line {n // 2} below" if n % 2 == 0 else f"space {n // 2 + 1} below the staff"


def load():
    grid = {}
    for doc in ("litolff", "brahms"):
        for f in glob.glob(str(HERE / "out" / f"grid_{doc}_*.json")):
            for r in json.load(open(f)):
                grid[(doc, r["cell"])] = r
    return grid


def pick(grid, ex, doc, want):
    """Bars whose grid changed by >= 0.5 sp and that hold >= 2 in-staff heads whose step moved."""
    cands = {}
    for g, h in ex[doc]["heads"].items():
        cell = "cell/" + "/".join(g.split("/")[1:5])
        r = grid.get((doc, cell))
        if not r or "on" not in r or "off" not in r:
            continue
        if abs(r["on"]["shift"] - r["off"]["shift"]) < 0.5 * r["off"]["spacing"]:
            continue
        a, b = r["off"]["canon"], r["on"]["canon"]
        sp = (a[-1] - a[0]) / 4.0
        _n, _x, yc, _w, hc = h["box"]
        yc_c = yc + hc / 2.0
        s0 = (yc_c - a[0]) / (sp / 2.0)
        s1 = (yc_c - b[0]) / (((b[-1] - b[0]) / 4.0) / 2.0)
        if -0.5 <= s0 <= 8.5 and round(s0) != round(s1):
            cands.setdefault(cell, []).append((g, h, round(s0), round(s1)))
    out = [(c, v) for c, v in sorted(cands.items()) if len(v) >= 2]
    return out


def panel(doc, cell, heads, pi_cache, n, pdf_render):
    r = grid_global[(doc, cell)]
    page = int(cell.split("/")[1])
    key = (doc, page)
    if key not in pi_cache:
        pi_cache[key] = pdf_render(str(DOCS[doc][0]), page, dpi=DOCS[doc][1])
    pi = pi_cache[key]
    x0, y0, x1, y1 = r["off"]["box"]
    crop = Image.fromarray(pi.rgb[y0:y1, x0:x1]).convert("RGB")
    im = crop.resize((crop.width * Z, crop.height * Z), Image.NEAREST)
    d = ImageDraw.Draw(im)
    drawn = []
    for arm, col in (("off", RED), ("on", BLUE)):
        sh = r[arm]["shift"]
        for y in r[arm]["ys"]:
            py = (y + sh - y0) * Z + Z // 2
            if not 0 <= py < im.height:
                continue
            # alternate blocks so a red row and the blue row one spacing away
            # that lands on it can both be read (red = even blocks, blue = odd)
            blk = 18 * Z
            for bx in range(0 if arm == "off" else blk, im.width, 2 * blk):
                d.line([(bx, py), (min(bx + blk - 1, im.width), py)], fill=col, width=1)
            drawn.append((arm, col, py))
    scale = r["off"]["scale"]
    for tag, (g, h, s0, s1) in zip("AB", heads[:2]):
        _n, xc, yc, wc, hc = h["box"]
        bx0, by0 = (xc / scale) * Z, (yc / scale) * Z
        bx1, by1 = ((xc + wc) / scale) * Z, ((yc + hc) / scale) * Z
        L = 8
        for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            d.line([(px, py), (px + dx * L, py)], fill=GREEN, width=2)
            d.line([(px, py), (px, py + dy * L)], fill=GREEN, width=2)
        d.text((bx0, by0 - 14), tag, fill=GREEN)
    # DRAWING CHECK: re-read the drawn rows from the pixels
    arr = np.asarray(im)
    errs = []
    for arm, col, py in drawn:
        m = (np.abs(arr[:, :, 0].astype(int) - col[0]) < 6) & (np.abs(arr[:, :, 1].astype(int) - col[1]) < 6) & (np.abs(arr[:, :, 2].astype(int) - col[2]) < 6)
        rows = np.flatnonzero(m.sum(axis=1) > 0.3 * im.width)
        if len(rows):
            errs.append(float(np.min(np.abs(rows - py))))
        else:
            errs.append(99.0)
    cap = [f"{n}. {doc} {cell[5:]}  red = before, blue = after"]
    for tag, (g, h, s0, s1) in zip("AB", heads[:2]):
        cap.append(f"   {tag}: {words(s0)}  ->  {words(s1)}")
    return im, cap, max(errs)


grid_global = {}

if __name__ == "__main__":
    from tools.omr.preprocessing import render_page

    grid_global.update(load())
    ex = {"litolff": json.load(open(sys.argv[1])), "brahms": json.load(open(sys.argv[2]))}
    sel = []
    for doc, take in (("litolff", 6), ("brahms", 2)):
        c = pick(grid_global, ex, doc, take)
        seen, chosen, rest = set(), [], []
        for cell, v in c:
            k = cell.rsplit("/", 1)[0]
            (rest if k in seen else chosen).append((doc, cell, v))
            seen.add(k)
        sel += (chosen + rest)[:take]
    if len(sel) < 8:                      # fill from Litolff's other fixed bars
        have = {c for _, c, _ in sel}
        extra = [(d, c, v) for d, c, v in [("litolff", c, v) for c, v in pick(grid_global, ex, "litolff", 99)] if c not in have]
        sel += extra[:8 - len(sel)]
    print("selected", [(d, c) for d, c, _ in sel])
    cache = {}
    panels, caps, maxerr = [], [], 0.0
    for n, (doc, cell, v) in enumerate(sel, 1):
        im, cap, e = panel(doc, cell, [(g, h, s0, s1) for g, h, s0, s1 in v], cache, n, render_page)
        panels.append(im)
        caps.append(cap)
        maxerr = max(maxerr, e)
        print(cap[0], "| drawn-vs-pixel max err %.2f px (x%d)" % (e, Z))
    # lay out 2 columns
    colw = max(p.width for p in panels) + 20
    rows = [(panels[i], caps[i], panels[i + 1] if i + 1 < len(panels) else None, caps[i + 1] if i + 1 < len(panels) else None)
            for i in range(0, len(panels), 2)]
    font = ImageFont.load_default()
    heights = [max(p[0].height, p[2].height if p[2] else 0) + 70 for p in rows]
    sheet = Image.new("RGB", (2 * colw + 20, sum(heights) + 20), "white")
    dr = ImageDraw.Draw(sheet)
    y = 10
    for (p1, c1, p2, c2), h in zip(rows, heights):
        for k, (p, c) in enumerate(((p1, c1), (p2, c2))):
            if p is None:
                continue
            x = 10 + k * colw
            for i, line in enumerate(c):
                dr.text((x, y + i * 14), line, fill="black", font=font)
            sheet.paste(p, (x, y + 48))
        y += h
    out = ROOT / "out" / "print" / "per_bar_grid_one_line_off.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("DRAWING CHECK: max |drawn row - pixel row| over all panels = %.2f px at x%d (<= 1 expected)" % (maxerr, Z))
    print("saved", out, sheet.size)
