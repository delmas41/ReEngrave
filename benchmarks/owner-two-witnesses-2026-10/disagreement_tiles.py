"""ROADMAP 2.216 (read-only count): blind crops of heads where the stem and the ledger reading name DIFFERENT staves.
Nothing of ours is drawn: the head is boxed in orange, the two candidate staves are outlined and named (A blue, B green,
seeded shuffle so the letter says nothing), a ruler in staff spaces runs down the left of the crop. The answer key is key.json.
  python3 benchmarks/owner-two-witnesses-2026-10/disagreement_tiles.py <extract.json litolff> <brahms> <rec litolff> <rec brahms>
"""
import json, random, sys, pathlib, collections
REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmarks/omr-local-staff-2026-09")); sys.path.insert(0, str(REPO))
import numpy as np
from PIL import Image, ImageDraw
from frame import render_page_matching_gather
import mark_group_no_owner_tiles as MG
from tools.omr.staged.judged import iter_array

OUT = REPO / "out/print/2.216"; OUT.mkdir(parents=True, exist_ok=True)
CHOSEN = [("litolff", "glyph/6/0/0/8/9"), ("litolff", "glyph/6/1/0/9/4"), ("litolff", "glyph/14/0/1/8/0"), ("litolff", "glyph/16/0/0/14/0"),
          ("brahms", "glyph/3/0/0/2/2"), ("brahms", "glyph/7/1/3/1/2"), ("brahms", "glyph/11/0/2/0/15"), ("brahms", "glyph/24/1/3/2/5")]


def staves(rec, want):
    info = collections.defaultdict(dict)
    for o in iter_array(pathlib.Path(rec), "observations"):
        k = o["subject"].split("/")
        if o["quantity"] in ("staff_lines", "margin_label") and len(k) == 4 and k[0] == "staff" and (int(k[1]), int(k[2])) in want:
            st = info[(int(k[1]), int(k[2]))].setdefault(o["subject"], dict(lines=None, instrument=None, margin=[]))
            if o["quantity"] == "staff_lines" and st["lines"] is None: st["lines"] = o["value"]
            elif o["quantity"] == "margin_label": st["margin"].append(o["value"])
    sup = set()
    for v in iter_array(pathlib.Path(rec), "verdicts"):
        k = v["subject"].split("/")
        if v["quantity"] == "instrument" and v["outcome"] == "decided" and len(k) == 4 and (int(k[1]), int(k[2])) in want \
                and v["subject"] in info[(int(k[1]), int(k[2]))]:
            info[(int(k[1]), int(k[2]))][v["subject"]]["instrument"] = v["value"]
    return info


def main(a):
    data = {"litolff": json.load(open(a[0])), "brahms": json.load(open(a[1]))}
    recs = {"litolff": a[2], "brahms": a[3]}
    rng = random.Random(2216)
    info = {}
    for tag in recs:
        want = {(int(h.split("/")[1]), int(h.split("/")[2])) for t, h in CHOSEN if t == tag}
        want |= {(p, s) for p, s in [(int(data[tag]["ver"][h]["stem_owner"].split("/")[1]), int(data[tag]["ver"][h]["stem_owner"].split("/")[2])) for t, h in CHOSEN if t == tag]}
        info[tag] = staves(recs[tag], want)
    order = list(CHOSEN); rng.shuffle(order)
    keys, qs = [], []
    for n, (tag, head) in enumerate(order, 1):
        v = data[tag]["ver"][head]
        so, lo = v["stem_owner"], v["ledger_owner"]
        page, sysi = int(so.split("/")[1]), int(so.split("/")[2])
        st = {k: x for k, x in info[tag][(page, sysi)].items() if x["lines"]}
        ks = sorted(st, key=lambda k: int(k.split("/")[-1]))
        A, B = [so, lo]; rng.shuffle(A_B := [so, lo]); A, B = A_B
        sp = float(np.median([(st[k]["lines"][-1] - st[k]["lines"][0]) / 4 for k in ks]))
        box = data[tag]["box"][head][1]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        pi = render_page_matching_gather(MG.PDF[tag], page, 600)
        img = np.asarray(pi.rgb)
        if img.ndim == 2: img = np.stack([img] * 3, axis=-1)
        half = int(min(max(24 * sp, 420), 700))
        x0, x1 = max(0, int(cx - half)), min(img.shape[1], int(cx + half))
        shown = [k for k in ks if abs(int(k.split("/")[-1]) - int(so.split("/")[-1])) <= 2 or abs(int(k.split("/")[-1]) - int(lo.split("/")[-1])) <= 2]
        y0 = max(0, int(min(st[k]["lines"][0] for k in shown) - 2.5 * sp)); y1 = min(img.shape[0], int(max(st[k]["lines"][-1] for k in shown) + 2.5 * sp))
        crop = img[y0:y1, x0:x1]
        scale = max(1.0, 1250.0 / crop.shape[1])
        big = Image.fromarray(crop).resize((int(crop.shape[1] * scale), int(crop.shape[0] * scale)), Image.LANCZOS)
        G = 420; W = G + big.size[0] + 10
        q = f"Which staff does the boxed note belong to: {MG.short(A, st[A])} or {MG.short(B, st[B])}?"
        f22, f28 = MG.font(22), MG.font(28)
        tmp = ImageDraw.Draw(Image.new("RGB", (W, 10)))
        ql = MG.wrap(q, f28, W - 30, tmp)
        top_h, foot_h = 56, 20 + 38 * len(ql) + 70
        im = Image.new("RGB", (W, top_h + big.size[1] + foot_h), "white"); dr = ImageDraw.Draw(im)
        dr.text((15, 12), f"Tile {n:02d}  -  {MG.WORK[tag]}, PDF page {page}, system {sysi + 1}", fill=(0, 0, 0), font=f28)
        im.paste(big, (G, top_h))
        fx = lambda x: G + (x - x0) * scale
        fy = lambda y: top_h + (y - y0) * scale
        for k in shown:
            ls = st[k]["lines"]; col = MG.BLUE if k == A else MG.GREEN if k == B else None
            ty = fy((ls[0] + ls[-1]) / 2) - 12
            dr.text((10, ty), MG.staff_label(k, st[k])[:30], fill=col or (60, 60, 60), font=f22 if col else MG.font(20))
            if col:
                dr.text((10, ty + 26), "A" if k == A else "B", fill=col, font=MG.font(26))
                dr.rectangle([G + 2, fy(ls[0] - 1.1 * sp), G + big.size[0] - 3, fy(ls[-1] + 1.1 * sp)], outline=col, width=5)
        # ruler: one tick per staff space, 0 at the head's centre, along the left edge of the crop
        rx = G - 4
        dr.line([(rx, fy(y0)), (rx, fy(y1))], fill=(0, 0, 0), width=2)
        m = int((cy - y0) / sp) + 2; i = -m
        while cy + i * sp < y1:
            yy = cy + i * sp
            if yy >= y0:
                dr.line([(rx - (16 if i % 5 == 0 else 8), fy(yy)), (rx, fy(yy))], fill=(0, 0, 0), width=2)
                if i % 5 == 0: dr.text((rx - 70, fy(yy) - 10), f"{i:+d}", fill=(0, 0, 0), font=MG.font(18))
            i += 1
        pad = 0.25 * sp
        dr.rectangle([fx(box[0] - pad), fy(box[1] - pad), fx(box[2] + pad), fy(box[3] + pad)], outline=MG.ORANGE, width=5)
        y = top_h + big.size[1] + 14
        dr.rectangle([15, y + 4, 40, y + 26], outline=MG.BLUE, width=4); dr.text((48, y), "A", fill=MG.BLUE, font=f22)
        dr.rectangle([90, y + 4, 115, y + 26], outline=MG.GREEN, width=4); dr.text((123, y), "B", fill=MG.GREEN, font=f22)
        dr.rectangle([165, y + 4, 190, y + 26], outline=MG.ORANGE, width=4); dr.text((198, y), "the boxed note.  Ruler at left: one tick per staff space, 0 = the note's centre", fill=MG.ORANGE, font=f22)
        y += 44
        for ln in ql: dr.text((15, y), ln, fill=(0, 0, 0), font=f28); y += 38
        im.save(OUT / f"tile_{n:02d}.png")
        qs.append(f"Tile {n:02d}: {q}")
        keys.append(dict(tile=n, doc=tag, head=head, A=MG.staff_label(A, st[A]), B=MG.staff_label(B, st[B]), stem_says=MG.staff_label(so, st[so]),
                         ledger_says=MG.staff_label(lo, st[lo]), stem_dir=v["stem"]))
    (OUT / "questions.txt").write_text("\n".join(qs) + "\n"); (OUT / "key.json").write_text(json.dumps(keys, indent=1))
    print("\n".join(qs))

main(sys.argv[1:])
