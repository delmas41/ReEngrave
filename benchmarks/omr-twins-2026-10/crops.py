"""2.119 step 4: blind A/B crop sheets for the top 5 split points. Nothing of ours drawn except a small red corner bracket on the note.
python3 crops.py -> out/crops/sheet_N.png + out/crops/LEGEND.md"""
import json, random, sys, collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parent))
import raster as R
OUT = Path(__file__).resolve().parent / "out"; CR = OUT / "crops"; CR.mkdir(exist_ok=True)
a = json.load(open(OUT / "analysis_ranked.json"))
bd = json.load(open(OUT / "brahms_p0.json")); ld = json.load(open(OUT / "litolff_p1.json"))
gray = {"brahms": R.page_gray(bd["pdf"], 0), "litolff": R.page_gray(ld["pdf"], 1)}
FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
PXSP = 40      # output pixels per staff space
rng = random.Random(2119)
SHEETS = [("A duration narrowed", 1), ("B bar-sum hold-out", 2), ("C detector: no box", 3), ("D partial-bar gap", 4), ("E refused not-a-notehead", 5)]

def page_rect(doc, t): return t["rect"] if doc == "brahms" else t.get("rect_page")
def space_px(doc, t): return t["space"] if doc == "brahms" else t["space"] * t["scale"]

def crop(doc, t, bar_level):
    r = page_rect(doc, t); sp = space_px(doc, t); g = gray[doc]
    cx, cy = (r[0]+r[2])/2, (r[1]+r[3])/2
    if bar_level and doc == "brahms":
        cr = t["cell_rect"]; x0, x1 = max(cr[0], cx - 14*sp), min(cr[2], cx + 14*sp)
    else:
        x0, x1 = cx - 7.5*sp, cx + 7.5*sp
    y0, y1 = cy - 6*sp, cy + 6*sp
    H, W = g.shape
    x0, y0, x1, y1 = [int(round(v)) for v in (max(0, x0), max(0, y0), min(W, x1), min(H, y1))]
    im = Image.fromarray(g[y0:y1, x0:x1]).convert("RGB")
    k = PXSP / sp
    im = im.resize((max(1, int(im.width*k)), max(1, int(im.height*k))), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    bx0, by0, bx1, by1 = [(v - o)*k for v, o in zip(r, (x0, y0, x0, y0))]
    pad = 0.18*PXSP; bx0, by0, bx1, by1 = bx0-pad, by0-pad, bx1+pad, by1+pad
    L = 0.45*min(bx1-bx0, by1-by0); T = 4; red = (230, 0, 0)
    for (x, y, sx, sy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        d.line([(x, y), (x+sx*L, y)], fill=red, width=T); d.line([(x, y), (x, y+sy*L)], fill=red, width=T)
    return im

def labelled(im, lab):
    W = im.width + 20; H = im.height + 64
    out = Image.new("RGB", (W, H), "white"); ImageDraw.Draw(out).text((14, 6), lab, fill="black", font=FONT)
    out.paste(im, (10, 54)); ImageDraw.Draw(out).rectangle([10, 54, 10+im.width-1, 54+im.height-1], outline=(150, 150, 150), width=1)
    return out

legend = ["# 2.119 twins study -- crop sheets (LEGEND: not shown to Sean with the sheets)", "",
          "Each sheet: three rows, each row a pair A | B. One of the two is a note that reached the file (written), the other a look-alike that did not. "
          "A red corner bracket marks the note; nothing else of ours is drawn. Which side is the written one is a seeded coin flip per row (listed below).", ""]
for grp, n in SHEETS:
    cand = []
    for doc in ("brahms", "litolff"):
        T = {t["id"]: t for t in a[doc]["truth"]}
        for p in a[doc]["pairs"]:
            m, w = T[p["missed"]], T[p["written"]]
            if m.get("split_group") != grp or page_rect(doc, m) is None or page_rect(doc, w) is None: continue
            cand.append((p["tier"], p["size_diff_sp"], doc, m, w, p))
    cand.sort(key=lambda x: (x[0], x[1]))
    pick, seen = [], set()
    subs = set()
    for passno in (1, 2):
        for c in cand:
            key = (c[2], tuple(c[3]["cell"]) if isinstance(c[3]["cell"], list) else c[3]["cell"])
            if key in seen or len(pick) == 3: continue
            if passno == 1 and c[3]["split_fine"] in subs: continue
            seen.add(key); subs.add(c[3]["split_fine"]); pick.append(c)
    rows = []; legend.append(f"## sheet_{n}.png -- split point **{grp}**"); legend.append("")
    bar_level = grp.startswith(("B", "D"))
    for i, (tier, sd, doc, m, w, p) in enumerate(pick):
        written_is_A = rng.random() < 0.5
        A, B = (w, m) if written_is_A else (m, w)
        ia, ib = labelled(crop(doc, A, bar_level), "A"), labelled(crop(doc, B, bar_level), "B")
        W = ia.width + ib.width + 30; H = max(ia.height, ib.height)
        row = Image.new("RGB", (W, H), "white"); row.paste(ia, (0, 0)); row.paste(ib, (ia.width + 30, 0)); rows.append(row)
        def where(t): return (f"Brahms 317803 pdf 0, system {t['system']} staff {t['staff']}, cell {t['cell']}" if doc == "brahms"
                              else f"Litolff 984073 idx 1, system/staff/bar {tuple(t['cell'])}")
        legend.append(f"- row {i+1}: **{'A' if written_is_A else 'B'} = written**, **{'B' if written_is_A else 'A'} = not written** ({m['split_fine']}; the missed twin's fate: `{m['code']}`). "
                      f"Written twin `{w['id']}` ({w['code']}) at {where(w)}; missed twin `{m['id']}` at {where(m)}. Pairing: {p['rule']}, tier {p['tier']}, size difference {p['size_diff_sp']} sp.")
    legend.append("")
    Wt = max(r.width for r in rows); Ht = sum(r.height for r in rows) + 20*(len(rows)-1)
    sheet = Image.new("RGB", (Wt, Ht), "white"); y = 0
    for r in rows: sheet.paste(r, (0, y)); y += r.height + 20
    sheet.save(CR / f"sheet_{n}.png")
    print(grp, len(pick), sheet.size)
(CR / "LEGEND.md").write_text("\n".join(legend))
