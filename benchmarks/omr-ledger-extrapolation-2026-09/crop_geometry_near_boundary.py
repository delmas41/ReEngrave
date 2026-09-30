"""Readable crops off the 600 dpi page binary: one staff, >= 1000 px wide.
Staff lines GREY, measured ledgers ORANGE, each labelled with its pitch
(clef from the staged CLEF verdict). The head's measured ink rows: BLUE
corner brackets. Header: subject, truth in words, geometry / 2.44 / ledger_grid / C."""
import json, sys, math, numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab56d1d321c30c4bd")
from tools.omr.pitch_resolver import _pitch_from_position as P
def pn(s, clef):
    try: return P(s, clef or "treble") if s is not None else "no answer"
    except Exception: return str(s)
try:
    F = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
    Fs = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
except Exception:
    F = Fs = ImageFont.load_default()
tag, outdir, which = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
outdir.mkdir(parents=True, exist_ok=True)
rows = json.load(open(f"{tag}-geom2.json")); B = np.load(f"{tag}-page.npy")
for r in rows:
    m = r["measured"]; T = m.get("step")
    if which == "wrong" and not (T is not None and r["geometry"] != T): continue
    if which == "readable" and T is None: continue
    if which == "sean" and r["group"] != "sean": continue
    sp, px, cl = r["sp"], r["px"], r["clef"]
    staff = m["staff"]; lad = m["ladder"]
    hr = m.get("head_rows") or [int(r["py"] - 0.5 * sp), int(r["py"] + 0.5 * sp)]
    ys = staff + lad + hr
    y0 = int(min(ys) - 1.5 * sp); y1 = int(max(ys) + 1.5 * sp)
    x0 = int(px - 8 * sp); x1 = int(px + 8 * sp)
    k = max(1, math.ceil(1000 / (x1 - x0)))
    crop = B[y0:y1, x0:x1]
    im = Image.fromarray(((~crop) * 255).astype(np.uint8)).convert("RGB").resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST)
    Wd = im.size[0]
    canvas = Image.new("RGB", (Wd + 170, im.size[1] + 110), "white"); canvas.paste(im, (0, 110))
    d = ImageDraw.Draw(canvas)
    edge_step = 0 if r["side"] == "above" else 8; sign = -1 if r["side"] == "above" else 1
    for i, L in enumerate(staff):
        yy = 110 + (L - y0) * k
        d.line([(Wd, yy), (Wd + 20, yy)], fill=(120, 120, 120), width=3)
        d.text((Wd + 24, yy - 10), f"staff {pn(2 * i, cl)}", fill=(90, 90, 90), font=Fs)
    for n, L in enumerate(lad, 1):
        yy = 110 + (L - y0) * k
        d.line([(0, yy), (40, yy)], fill=(255, 130, 0), width=4); d.line([(Wd - 40, yy), (Wd + 20, yy)], fill=(255, 130, 0), width=4)
        d.text((Wd + 24, yy - 10), f"ledger {pn(edge_step + sign * 2 * n, cl)}", fill=(220, 100, 0), font=Fs)
    hx = (px - x0) * k; t, b = [110 + (v - y0) * k for v in hr]; hw = 0.75 * sp * k
    for sx in (-1, 1):
        for yy, sy in ((t, 1), (b, -1)):
            d.line([(hx + sx * hw, yy), (hx + sx * hw * 0.55, yy)], fill=(0, 80, 255), width=4)
            d.line([(hx + sx * hw, yy), (hx + sx * hw, yy + sy * 0.35 * sp * k)], fill=(0, 80, 255), width=4)
    truth = f"PRINT: {pn(T, cl)} ({m.get('words')})" if T is not None else f"PRINT: unreadable ({m.get('why')})"
    d.text((6, 4), f"{r['subject']}  [{r['group']}]  clef {cl}  staff_pos {r['staff_pos']}" + (f"  Sean: {r['sean']}" if r.get("sean") else ""), fill="black", font=F)
    d.text((6, 34), truth, fill=(0, 0, 160), font=F)
    d.text((6, 64), f"geometry {pn(r['geometry'], cl)} | 2.44 {pn(r['A'], cl)} | ledger_grid {pn(r['B'], cl)} | C clean-count {pn(m.get('C'), cl)}", fill="black", font=F)
    canvas.save(outdir / f"{tag}-{r['group']}-{r['subject'].replace('/', '-')}.png")
