"""lane-staccato-unread: review tiles, ONE image per tile, ONE plain question per tile.

    python3 staccato_unread_tiles.py BEFORE_lito AFTER_lito BEFORE_brahms AFTER_brahms [--seed 20261008]

Tile 1 = Sean's case (Litolff `12/1/6/2/9`); tiles 2-10 = seeded draws (3 Litolff, 6 Brahms) from the dots the reader
left unread and now reads as a staccato.  Each tile: one column, staff names at the left (the staff that boxed the dot
and the staff of its note are marked), the dot ORANGE, its note GREEN.  Writes `out/print/staccato_unread/tile_NN.png`,
`questions.txt` and `tiles.json`.
"""
import json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUT = HERE.parents[1] / "out/print/staccato_unread"
DOC = {"lito": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
ORANGE, GREEN, GREY = (255, 140, 0), (0, 160, 0), (110, 110, 110)
FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
FONT_B = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
SC = 2                      # crop zoom
HALF_SP = 21                # half width of the crop in staff spaces -> >= 1300 px at 16 px/sp
LEFT = 330                  # name margin, px


def staff_name(R, skey, n_in_sys=None):
    nm = R["inst"].get(skey)
    idx = int(skey.split("/")[3]) + 1
    return (nm if nm else "no name read") + f"  (staff {idx})"


def tile(short, key, B, A, no, page_cache):
    d, e = B["dots"][key], A["dots"][key]
    page = int(key.split("/")[1]); sysi = int(key.split("/")[2]); kdot = int(key.split("/")[3])
    owner = (e["role"]["d"] or {}).get("owner")
    head = next(h for h in e["heads"] if h["k"] == owner)
    own = (head["own"] or {}).get("v")           # the note's decided owner, else the strip that filed it
    knote = int((own if isinstance(own, str) and own.startswith("staff/") else owner).split("/")[3])
    if (short, page) not in page_cache:
        page_cache[(short, page)] = cv2.cvtColor(
            render_page_matching_gather(ts.DOCS[DOC[short]]["pdf"], page, 600).rgb, cv2.COLOR_RGB2BGR)
    g = page_cache[(short, page)]
    pb = d["pb"]
    k = (pb[2] - pb[0]) / d["box"][2]
    spp = d["space"] * k
    cx, cy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
    # staves of this system shown: from one above the higher of the two to one below the lower
    skeys = {int(s.split("/")[3]): s for s in A["staff_lines"] if s.startswith(f"staff/{page}/{sysi}/")}
    lo, hi = min(kdot, knote) - 1, max(kdot, knote) + 1
    shown = [skeys[i] for i in range(lo, hi + 1) if i in skeys]
    ys = [y for s in shown for y in A["staff_lines"][s]]
    y0, y1 = int(min(ys) - 2.5 * spp), int(max(ys) + 2.5 * spp)
    y0, y1 = max(0, min(y0, int(cy - 3 * spp))), min(g.shape[0], max(y1, int(cy + 3 * spp), int(head["pb"][3] + 2 * spp)))
    x0, x1 = int(cx - HALF_SP * spp), int(cx + HALF_SP * spp)
    x0, x1 = max(0, x0), min(g.shape[1], x1)
    crop = g[y0:y1, x0:x1].copy()
    crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_CUBIC)

    def R_(b):
        return (int((b[0] - x0) * SC), int((b[1] - y0) * SC), int((b[2] - x0) * SC), int((b[3] - y0) * SC))
    a = R_(pb); hb = R_(head["pb"])
    pad = 7
    cv2.rectangle(crop, (hb[0] - 2, hb[1] - 2), (hb[2] + 2, hb[3] + 2), GREEN[::-1], 3)
    cv2.rectangle(crop, (a[0] - pad, a[1] - pad), (a[2] + pad, a[3] + pad), ORANGE[::-1], 3)
    W = LEFT + crop.shape[1]
    # words
    dot_staff = f"staff/{page}/{sysi}/{kdot}"
    note_staff = f"staff/{page}/{sysi}/{knote}"
    words = [
        f"BEFORE: the reader could not tell what this dot is (it left it unread).",
        "AFTER: it reads the dot as a staccato on the green note"
        + (f", a note filed under {staff_name(A, note_staff)}." if note_staff != dot_staff else "."),
        "ORANGE box = the dot.   GREEN box = the note it stands over.",
    ]
    head_h = 96
    cap_h = 14 + 36 * (len(words) + 1)
    H = head_h + crop.shape[0] + cap_h
    img = Image.new("RGB", (W, H), (255, 255, 255))
    img.paste(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)), (LEFT, head_h))
    dr = ImageDraw.Draw(img)
    dr.text((10, 8), f"Tile {no}.  {DOC[short].split('-')[1].capitalize()}, pdf page {page}", font=FONT_B, fill=(0, 0, 0))
    dr.text((10, 48), f"Is the orange dot a staccato on the green note, or a dot that lengthens it?", font=FONT_B, fill=(0, 0, 0))
    # staff names at the left, at each staff's middle line
    for s in shown:
        ln = A["staff_lines"][s]
        ym = (ln[2] - y0) * SC + head_h
        name = staff_name(A, s)
        tag = ""
        if s == dot_staff and s == note_staff:
            tag = "the dot and its note"
        elif s == dot_staff:
            tag = "boxed the dot"
        elif s == note_staff:
            tag = "holds the note"
        col = (0, 0, 0)
        dr.text((8, ym - 26), name, font=FONT, fill=col)
        if tag:
            dr.text((8, ym + 2), tag, font=FONT, fill=ORANGE if s == dot_staff else GREEN)
    y = head_h + crop.shape[0] + 14
    for i, w in enumerate(words):
        dr.text((10, y + 36 * i), w, font=FONT, fill=(0, 0, 0) if i < 2 else GREY)
    dr.text((10, y + 36 * len(words)), f"{short} {key.replace('glyph/', '')}", font=FONT, fill=GREY)
    dr.rectangle((0, 0, W - 1, H - 1), outline=(180, 180, 180))
    arr = np.array(img)
    return arr, dict(n=no, doc=short, page=page, subject=key, note=owner, dot_staff=dot_staff, note_staff=note_staff,
                     words=words, size=list(arr.shape[:2][::-1]))


def main(a, seed):
    Bl, Al, Bb, Ab = (json.load(open(p)) for p in a[:4])
    BB = {"lito": Bl, "brahms": Bb}; AA = {"lito": Al, "brahms": Ab}
    pool = {s: [k for k, d in BB[s]["dots"].items()
                if d["role"]["o"] != "decided" and AA[s]["dots"][k]["role"]["o"] == "decided"
                and AA[s]["dots"][k]["role"]["v"] == "staccato"
                and ((AA[s]["dots"][k]["role"]["d"] or {}).get("owner"))] for s in BB}
    print({s: len(v) for s, v in pool.items()})
    rng = random.Random(seed)
    sean = ("lito", "glyph/12/1/6/2/9")
    picks = [sean]
    for s, n in (("lito", 3), ("brahms", 6)):
        pl = [k for k in pool[s] if (s, k) != sean]
        rng.shuffle(pl)
        used_pages = set()
        for k in pl:
            pg = k.split("/")[1]
            if pg in used_pages:
                continue
            used_pages.add(pg)
            picks.append((s, k))
            if len([p for p in picks if p[0] == s]) >= n + (1 if s == "lito" else 0):
                break
    OUT.mkdir(parents=True, exist_ok=True)
    cache, info = {}, []
    for no, (s, k) in enumerate(picks, 1):
        arr, meta = tile(s, k, BB[s], AA[s], no, cache)
        cv2.imwrite(str(OUT / f"tile_{no:02d}.png"), cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        info.append(meta)
        print(no, s, k, meta["size"])
    (OUT / "tiles.json").write_text(json.dumps(info, indent=1))
    (OUT / "questions.txt").write_text("\n".join(
        f"{m['n']}. {DOC[m['doc']].split('-')[1].capitalize()} p{m['page']} {m['subject'].replace('glyph/', '')}: "
        "Is the orange dot a staccato on the green note, or a dot that lengthens it?" for m in info) + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    main([x for x in args if not x.startswith("--")][:4], int(args[args.index("--seed") + 1]) if "--seed" in args else 20261008)
