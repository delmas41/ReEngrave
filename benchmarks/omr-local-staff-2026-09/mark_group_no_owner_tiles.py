"""ROADMAP 2.58c -- the review tiles for the marks seen 2+ times that have no (single) owner.

One tile = ONE image, ONE column, ONE plain question (Sean, 2026-10-08: sheets one tile at a time). Each tile draws the
WHOLE system the mark sits in, every staff named at the left (instrument from the record's own verdict, else the printed
margin label, else "no label"), the two candidate staves outlined (blue = A, green = B -- assigned by a seeded shuffle, so
the letter says nothing about what any rule decided), and the note in ORANGE. The page is rendered in exactly the pixel
frame GATHER used (`frame.render_page_matching_gather`); the staff outlines come from the record's `staff_lines`.

  python3 benchmarks/omr-local-staff-2026-09/mark_group_no_owner_tiles.py <ext_litolff.json> <ext_brahms.json> \
      [--replay-litolff r.json --replay-brahms r.json]

Writes out/print/mark_group_no_owner/tile_NN.png, questions.txt and key.json (the answer key: what the record's saved
rule said, what the 2.58c rule says -- NOT drawn on the tiles).
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import numpy as np  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402
from tools.library.score_library import library_root  # noqa: E402

OUT = REPO / "out/print/mark_group_no_owner"
LIB = library_root()
PDF = {"litolff": LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
WORK = {"litolff": "Beethoven 5, Litolff", "brahms": "Brahms 1, Breitkopf"}
FONT = "/System/Library/Fonts/Helvetica.ttc"
BLUE, GREEN, ORANGE = (0, 90, 255), (0, 150, 0), (255, 110, 0)
SEED = 20261008
#: tile order: causes interleaved so no run of one kind
ORDER = [("litolff", "mg/13/1/36"), ("brahms", "mg/18/1/599"), ("litolff", "mg/14/0/46"), ("brahms", "mg/2/1/56"),
         ("litolff", "mg/6/1/374"), ("brahms", "mg/21/0/223"), ("litolff", "mg/4/1/178"), ("litolff", "mg/16/0/415"),
         ("brahms", "mg/5/1/35"), ("litolff", "mg/4/1/181")]


def font(n):
    return ImageFont.truetype(FONT, n)


def staff_label(k, st):
    n = int(k.split("/")[-1]) + 1
    iv = st.get("instrument")
    ml = st.get("margin") or []
    if isinstance(iv, dict) and iv.get("name"):
        nm = iv["name"]
        if ml and nm in ("Violin", "Horn", "Clarinet", "Trumpet", "Bassoon"):
            nm += f" ({ml[0]})"
        return f"staff {n}: {nm}"
    if ml:
        return f"staff {n}: \"{ml[0]}\""
    return f"staff {n}: no label"


def short(k, st):
    return staff_label(k, st).replace(": ", ", ")


def wrap(text, f, width, dr):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=f) <= width:
            cur = t
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    return out


def candidates(d, note):
    st = d["staves"]
    homes, owners = [], []
    for m in d["members"]:
        if m["refused"]:
            continue
        homes.append("staff/" + "/".join(m["subject"].split("/")[1:4]))
        for dec, out, val, rsn, sup in m["owner"]:
            if out == "decided" and val:
                owners.append(val)
    c = []
    for k in homes + owners:
        if k not in c and k in st:
            c.append(k)
    if len(c) < 2:
        cy = (note[1] + note[3]) / 2
        others = sorted((k for k in st if k not in c),
                        key=lambda k: abs(cy - (st[k]["lines"][0] + st[k]["lines"][-1]) / 2))
        c += others[:2 - len(c)]
    return c[:2]


def tile(n, tag, gid, d, replay, rng):
    members = [m for m in d["members"] if not m["refused"]] or d["members"]
    rep = max(members, key=lambda m: m["conf"] or 0)
    note = rep["bbox"]
    cx, cy = (note[0] + note[2]) / 2, (note[1] + note[3]) / 2
    st = d["staves"]
    cand = candidates(d, note)
    ab = cand[:]
    rng.shuffle(ab)                       # A/B by seeded shuffle: the letter carries no information
    A, B = ab
    keys = sorted(st, key=lambda k: int(k.split("/")[-1]))
    sp = float(np.median([(st[k]["lines"][-1] - st[k]["lines"][0]) / 4 for k in keys]))
    pi = render_page_matching_gather(PDF[tag], d["page"], 600)
    img = np.asarray(pi.rgb)
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    half = int(min(max(24 * sp, 420), 700))
    x0, x1 = max(0, int(cx - half)), min(img.shape[1], int(cx + half))
    y0 = int(min(st[k]["lines"][0] for k in keys) - 2.5 * sp)
    y1 = int(max(st[k]["lines"][-1] for k in keys) + 2.5 * sp)
    y0, y1 = max(0, y0), min(img.shape[0], y1)
    crop = img[y0:y1, x0:x1]
    scale = max(1.0, 1250.0 / crop.shape[1])
    big = Image.fromarray(crop).resize((int(crop.shape[1] * scale), int(crop.shape[0] * scale)), Image.LANCZOS)
    G = 420                                # name column
    W = G + big.size[0] + 10
    q = (f"Which staff does the orange note belong to: {short(A, st[A])} or {short(B, st[B])}?")
    head = f"Tile {n:02d}  -  {WORK[tag]}, PDF page {d['page']}, system {d['system'] + 1}"
    f20, f22, f26 = font(20), font(22), font(26)
    tmp = ImageDraw.Draw(Image.new("RGB", (W, 10)))
    qlines = wrap(q, f26, W - 30, tmp)
    foot_h = 20 + 34 * len(qlines) + 70
    top_h = 52
    im = Image.new("RGB", (W, top_h + big.size[1] + foot_h), "white")
    dr = ImageDraw.Draw(im)
    dr.text((15, 12), head, fill=(0, 0, 0), font=f26)
    im.paste(big, (G, top_h))
    fx = lambda x: G + (x - x0) * scale
    fy = lambda y: top_h + (y - y0) * scale
    for k in keys:
        ls = st[k]["lines"]
        col = BLUE if k == A else GREEN if k == B else None
        lab = staff_label(k, st[k])
        ty = fy((ls[0] + ls[-1]) / 2) - 12
        dr.text((10, ty), lab[:30], fill=col or (60, 60, 60), font=f22 if col else f20)
        if col:
            dr.text((10, ty + 26), "A" if k == A else "B", fill=col, font=f26)
            dr.rectangle([G + 2, fy(ls[0] - 1.1 * sp), G + big.size[0] - 3, fy(ls[-1] + 1.1 * sp)], outline=col, width=5)
    r = max(24, 1.0 * sp * scale)
    hx, hy = fx(cx), fy(cy)
    dr.ellipse([hx - r, hy - r, hx + r, hy + r], outline=ORANGE, width=5)
    ax, ay = hx + r + 90, hy - r - 60
    tip = (hx + r * 0.72, hy - r * 0.72)
    dr.line([(ax, ay), tip], fill=ORANGE, width=5)
    dr.polygon([tip, (tip[0] + 22, tip[1] - 5), (tip[0] + 5, tip[1] - 22)], fill=ORANGE)
    dr.text((ax + 6, ay - 26), "the orange note", fill=ORANGE, font=f22)
    y = top_h + big.size[1] + 14
    dr.rectangle([15, y + 4, 40, y + 26], outline=BLUE, width=4)
    dr.text((48, y), "A", fill=BLUE, font=f22)
    dr.rectangle([90, y + 4, 115, y + 26], outline=GREEN, width=4)
    dr.text((123, y), "B", fill=GREEN, font=f22)
    dr.ellipse([165, y + 2, 190, y + 28], outline=ORANGE, width=4)
    dr.text((198, y), "the note", fill=ORANGE, font=f22)
    y += 44
    for ln in qlines:
        dr.text((15, y), ln, fill=(0, 0, 0), font=f26)
        y += 34
    path = OUT / f"tile_{n:02d}.png"
    im.save(path)
    final = {}
    for s, o, nw, _ in replay.get("diff", []):
        final[s] = nw
    key = dict(tile=n, work=tag, group=gid, cause=d["cause"], page=d["page"], system=d["system"],
               A=staff_label(A, st[A]), B=staff_label(B, st[B]), note=rep["subject"],
               members=[dict(subject=m["subject"], cls=m["cls"], refused=m["refused"], saved=m["owner"],
                             new_rule=final.get(m["subject"])) for m in d["members"]],
               size=im.size)
    return q, key


def main(argv):
    lit, brh = (json.loads(Path(p).read_text()) for p in argv[:2])
    rep = {"litolff": {}, "brahms": {}}
    for i, a in enumerate(argv):
        if a == "--replay-litolff":
            rep["litolff"] = json.loads(Path(argv[i + 1]).read_text())
        if a == "--replay-brahms":
            rep["brahms"] = json.loads(Path(argv[i + 1]).read_text())
    data = {"litolff": lit, "brahms": brh}
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    qs, keys = [], []
    for n, (tag, gid) in enumerate(ORDER, 1):
        q, key = tile(n, tag, gid, data[tag]["tiles"][gid], rep[tag], rng)
        qs.append(f"Tile {n:02d}: {q}")
        keys.append(key)
        print(n, tag, gid, key["size"], q)
    (OUT / "questions.txt").write_text("\n".join(qs) + "\n")
    (OUT / "key.json").write_text(json.dumps(keys, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1:])
