"""2.280 r3: Sean's Brahms p0 hand labels as a SECOND WITNESS for STEMS only (DECISIONS 2026-11-10: stems live inside one cell, so the
cell-frame limit does not hurt them; the page is not a standing test). Page-pixel frame, dpi 600, both sides.
For each of our KEPT real heads on page 0 (heads.py rows): is there a hand 'stem' box touching the head (hand-head match first), and which way?
usage: hand.py HEADS.jsonl [HAND.json]"""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
hand = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "data/hand-truth/pages/imslp317803/0.json"))
HB = [b for b in hand["boxes"] if str(b["cls"]).startswith("notehead")]
HS = [b["rect"] for b in hand["boxes"] if b["cls"] == "stem"]
COPY = ("owned_by_another_staff", "mark_group_duplicate")


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0


def hand_stem(hb, tol):
    """stem boxes of the hand set that touch the head box (gap <= tol px both ways)."""
    x0, y0, x1, y1 = hb
    out = []
    for s in HS:
        dx = max(0.0, s[0] - x1, x0 - s[2])
        dy = max(0.0, s[1] - y1, y0 - s[3])
        if dx <= tol and dy <= tol:
            out.append(s)
    return out


pg = [r for r in rows if r["page"] == 0 and r["kept"] and r["fate"] not in COPY and r["fate"] != "ink_is_a_whole_rest" and r["page_box"]]
res = collections.Counter()
detail = []
for r in pg:
    hb = max(HB, key=lambda b: iou(b["rect"], r["page_box"]))
    if iou(hb["rect"], r["page_box"]) < 0.4:
        res["no hand head here (ours not on a hand head)"] += 1
        continue
    h = hb["rect"]
    tol = 0.35 * (h[3] - h[1])          # head height ~ 1 staff space; 0.35 sp tolerance
    st = hand_stem(h, tol)
    hand_has = bool(st)
    if hand_has:
        s = st[0]
        cx = (h[0] + h[2]) / 2
        side = "right" if (s[0] + s[2]) / 2 > cx else "left"
        up = (s[1] + s[3]) / 2 < (h[1] + h[3]) / 2
        hd = "up" if up else "down"
    else:
        side = hd = None
    ours = r["n_stem"] > 0
    k = ("hand stem" if hand_has else "hand: no stem", "ours row" if ours else "ours NO row")
    res[k] += 1
    if hand_has and not ours:
        detail.append((r["sub"], r["page_box"], hd, side, (r["head_stem"] or [None])[0:2], (r["duration"] or [None])[0:2], r["fate"]))
print("our kept real heads on p0:", len(pg))
for k, v in sorted(res.items(), key=str):
    print("  ", k, v)
print("hand stem present, ours no row: %d" % len(detail))
for d in detail[:40]:
    print("   ", d)
json.dump(detail, open("out/stems-rerun/hand_missed.json", "w"))
