"""ROADMAP 2.58d -- review tiles for the stem witness: ONE image per tile, ONE column, ONE plain question each.

Tiles 1-2 are Sean's tiles 3 and 7 of `out/print/mark_group_no_owner/` (the Trumpet/Timpani head and the Clarinet/Oboe
head); tiles 3-10 are EIGHT SEEDED CHANGES the stem witness makes on the 10-07 day records (3 where the stem moves a head
away from the nearer staff, 3 where the stem and the ledger reading disagree and the head now abstains, 2 where the stem
answers a head the ledgers could not). Each tile draws the WHOLE system, every staff named at the left, the two candidate
staves outlined (blue = A, green = B, assigned by a seeded shuffle so the letter says nothing), the head ORANGE and its
STEM drawn as the orange line the reader measured. The answer key (what the rules said) is in key.json, NOT on the tiles.

  python3 benchmarks/omr-local-staff-2026-09/stem_owner_tiles.py <lito.pkl> <lito_stems.json> <lito_replay.json> \
      <brahms.pkl> <brahms_stems.json> <brahms_replay.json> <lito.record.json> <brahms.record.json>
"""
import collections
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402
import mark_group_no_owner_tiles as MG  # noqa: E402
import stem_owner_lib as L  # noqa: E402
from stem_owner_replay import CONFIRMED  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

OUT = REPO / "out/print/stem_owner"
SEED = 20261008
FONT_SIZES = (22, 24, 28)
#: Sean's two tiles, as the mark-group sheet's key names them: (doc, the head the tile marked)
SEAN = [("litolff", "glyph/14/0/6/1/1"), ("litolff", "glyph/4/1/2/4/3")]


def load_doc(pkl, stems, replay):
    return dict(data=L.load(pkl), stems=json.load(open(stems)), rep=json.load(open(replay))["heads"])


def pick(docs, rng):
    """8 seeded changes, one per mark, from the two docs; returns [(doc, head, kind)]."""
    pools = collections.defaultdict(list)
    for tag, d in docs.items():
        grp = {}
        for g, members in L.groups(d["data"]).items():
            for m in members:
                grp[m] = g
        seen = set()
        for h, r in sorted(d["rep"].items()):
            if r["off"][:2] == r["on"][:2] or r["stem"] not in ("down", "up") or h in CONFIRMED[tag]:
                continue
            g = grp.get(h, h)
            if (tag, g) in seen:
                continue
            kind = ("disagree" if r["on"][2] == "stem_disagrees" and r["off"][2] == "ledger_note_first"
                    else "moved" if r["off"][2] == "distance" and r["on"][2] == "stem_toward_staff"
                    else "answered" if r["off"][2] == "far_no_rungs" and r["on"][2] == "stem_toward_staff"
                    else None)
            if kind is None:
                continue
            seen.add((tag, g))
            pools[(kind, tag)].append(h)
    out = []
    for kind, n_l, n_b in (("moved", 1, 2), ("disagree", 1, 2), ("answered", 1, 1)):
        for tag, n in (("litolff", n_l), ("brahms", n_b)):
            pool = pools[(kind, tag)]
            for h in rng.sample(pool, min(n, len(pool))):
                out.append((tag, h, kind))
    rng.shuffle(out)
    return out


def system_info(rec_path, wanted):
    """{(page, system): {staff key: dict(lines, instrument, margin)}} for the wanted systems, ONE load_record."""
    rec = load_record(rec_path)["record"]
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    want = set(wanted)
    info = collections.defaultdict(dict)
    for o in rec["observations"]:
        k = o["subject"].split("/")
        if o["quantity"] in ("staff_lines", "margin_label") and len(k) == 4 and k[0] == "staff" \
                and (int(k[1]), int(k[2])) in want:
            st = info[(int(k[1]), int(k[2]))].setdefault(o["subject"], dict(lines=None, instrument=None, margin=[]))
            if o["quantity"] == "staff_lines" and st["lines"] is None:
                st["lines"] = o["value"]
            elif o["quantity"] == "margin_label":
                st["margin"].append(o["value"])
    for v in rec["verdicts"]:
        k = v["subject"].split("/")
        if v["quantity"] == "instrument" and v["id"] not in sup and v["outcome"] == "decided" and len(k) == 4 \
                and (int(k[1]), int(k[2])) in want and v["subject"] in info[(int(k[1]), int(k[2]))]:
            info[(int(k[1]), int(k[2]))][v["subject"]]["instrument"] = v["value"]
    return info


def draw_tile(n, tag, head, d, staves, cands, rng, label):
    page, sysi = int(head.split("/")[1]), int(head.split("/")[2])
    box = d["stems"][head]["head_box_page"]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    st = {k: v for k, v in staves.items() if v["lines"]}
    keys = sorted(st, key=lambda k: int(k.split("/")[-1]))
    ab = list(cands)
    rng.shuffle(ab)
    A, B = ab
    sp = float(np.median([(st[k]["lines"][-1] - st[k]["lines"][0]) / 4 for k in keys]))
    pi = render_page_matching_gather(MG.PDF[tag], page, 600)
    img = np.asarray(pi.rgb)
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    half = int(min(max(24 * sp, 420), 700))
    x0, x1 = max(0, int(cx - half)), min(img.shape[1], int(cx + half))
    y0 = max(0, int(min(st[k]["lines"][0] for k in keys) - 2.5 * sp))
    y1 = min(img.shape[0], int(max(st[k]["lines"][-1] for k in keys) + 2.5 * sp))
    crop = img[y0:y1, x0:x1]
    scale = max(1.0, 1250.0 / crop.shape[1])
    big = Image.fromarray(crop).resize((int(crop.shape[1] * scale), int(crop.shape[0] * scale)), Image.LANCZOS)
    G = 420
    W = G + big.size[0] + 10
    q = f"Which staff does the orange note belong to: {MG.short(A, st[A])} or {MG.short(B, st[B])}?"
    head_txt = f"Tile {n:02d}  -  {MG.WORK[tag]}, PDF page {page}, system {sysi + 1}"
    f22, f26, f28 = MG.font(22), MG.font(26), MG.font(28)
    tmp = ImageDraw.Draw(Image.new("RGB", (W, 10)))
    qlines = MG.wrap(q, f28, W - 30, tmp)
    foot_h = 20 + 38 * len(qlines) + 130
    top_h = 56
    im = Image.new("RGB", (W, top_h + big.size[1] + foot_h), "white")
    dr = ImageDraw.Draw(im)
    dr.text((15, 12), head_txt, fill=(0, 0, 0), font=f28)
    im.paste(big, (G, top_h))
    fx = lambda x: G + (x - x0) * scale
    fy = lambda y: top_h + (y - y0) * scale
    for k in keys:
        ls = st[k]["lines"]
        col = MG.BLUE if k == A else MG.GREEN if k == B else None
        lab = MG.staff_label(k, st[k])
        ty = fy((ls[0] + ls[-1]) / 2) - 12
        dr.text((10, ty), lab[:30], fill=col or (60, 60, 60), font=f22 if col else MG.font(20))
        if col:
            dr.text((10, ty + 26), "A" if k == A else "B", fill=col, font=f26)
            dr.rectangle([G + 2, fy(ls[0] - 1.1 * sp), G + big.size[0] - 3, fy(ls[-1] + 1.1 * sp)], outline=col, width=5)
    s = d["stems"][head]
    way = s["direction"]
    tip = s[f"{way}_tip_y"]
    xe = box[0] + 1.5 if way == "down" else box[2] - 1.5
    dr.line([(fx(xe), fy(cy)), (fx(xe), fy(tip))], fill=MG.ORANGE, width=6)
    dr.line([(fx(xe) - 14, fy(tip)), (fx(xe) + 14, fy(tip))], fill=MG.ORANGE, width=6)
    r = max(24, 1.0 * sp * scale)
    hx, hy = fx(cx), fy(cy)
    dr.ellipse([hx - r, hy - r, hx + r, hy + r], outline=MG.ORANGE, width=5)
    ax, ay = hx + r + 90, hy - r - 60
    tipp = (hx + r * 0.72, hy - r * 0.72)
    dr.line([(ax, ay), tipp], fill=MG.ORANGE, width=5)
    dr.polygon([tipp, (tipp[0] + 22, tipp[1] - 5), (tipp[0] + 5, tipp[1] - 22)], fill=MG.ORANGE)
    dr.text((ax + 6, ay - 28), "the orange note and its stem", fill=MG.ORANGE, font=f22)
    y = top_h + big.size[1] + 14
    dr.rectangle([15, y + 4, 40, y + 26], outline=MG.BLUE, width=4)
    dr.text((48, y), "A", fill=MG.BLUE, font=f22)
    dr.rectangle([90, y + 4, 115, y + 26], outline=MG.GREEN, width=4)
    dr.text((123, y), "B", fill=MG.GREEN, font=f22)
    dr.ellipse([165, y + 2, 190, y + 28], outline=MG.ORANGE, width=4)
    dr.text((198, y), "the note (circle) and its stem (line down or up from it)", fill=MG.ORANGE, font=f22)
    y += 44
    for ln in qlines:
        dr.text((15, y), ln, fill=(0, 0, 0), font=f28)
        y += 38
    path = OUT / f"tile_{n:02d}.png"
    im.save(path)
    return q, dict(tile=n, doc=tag, head=head, label=label, A=MG.staff_label(A, st[A]), B=MG.staff_label(B, st[B]),
                   size=list(im.size), stem=dict(direction=way, tip_y=tip, ext_spaces=s.get(f"{way}_ext")),
                   off=d["rep"][head]["off"], on=d["rep"][head]["on"],
                   off_final=d["rep"][head]["off_final"], on_final=d["rep"][head]["on_final"])


def main(argv):
    lp, ls, lr, bp, bs, br, lrec, brec = argv
    docs = {"litolff": load_doc(lp, ls, lr), "brahms": load_doc(bp, bs, br)}
    rng = random.Random(SEED)
    chosen = [(t, h, "Sean's tile %d of the mark-group sheet" % k) for (t, h), k in zip(SEAN, (3, 7))]
    for tag, h, kind in pick(docs, rng):
        chosen.append((tag, h, {"moved": "stem moves the head to the farther staff",
                                "disagree": "stem and ledger reading disagree: now abstains",
                                "answered": "ledgers could not read it: stem answers"}[kind]))
    recpath = {"litolff": lrec, "brahms": brec}
    info = {}
    for tag in docs:
        wanted = {(int(h.split("/")[1]), int(h.split("/")[2])) for t, h, _ in chosen if t == tag}
        info[tag] = system_info(recpath[tag], wanted)
    OUT.mkdir(parents=True, exist_ok=True)
    qs, keys = [], []
    for n, (tag, head, label) in enumerate(chosen, 1):
        d = docs[tag]
        page, sysi = int(head.split("/")[1]), int(head.split("/")[2])
        cands = [c for c in {o["detail"]["candidate"] for o in d["data"]["obs"]
                             if o["quantity"] == "glyph_band_distance" and o["subject"] == head}]
        cands = sorted(cands)[:2]
        q, key = draw_tile(n, tag, head, d, info[tag][(page, sysi)], cands, rng, label)
        qs.append(f"Tile {n:02d}: {q}")
        keys.append(key)
        print(n, tag, head, label, key["size"])
    (OUT / "questions.txt").write_text("\n".join(qs) + "\n")
    (OUT / "key.json").write_text(json.dumps(keys, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1:9])
