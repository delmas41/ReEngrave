"""ROADMAP 2.159 -- what the located-box slit reading would do, offline, before any code: (1) control: the page-raster
reading on the detector box vs the stored cell-raster reading; (2) the head_fill_from_ink heads: located rows_share, and
whether 2.148's first step would decide (rows_share >= 0.18 with a stem of its own); (3) Sean's judged BLACK-classed heads
(both fills): the located reading on every one that has a located box, split by the detector box being head-sized or not.
usage: located_eval_2_159.py OUTDIR DOC"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from separate_2_159 import gate  # noqa: E402

OUT, DOC = sys.argv[1:3]
L = json.load(open(os.path.join(OUT, "located_%s.json" % DOC)))
H0 = json.load(open(os.path.join(OUT, "heads_%s.json" % DOC)))


def same_head(s):
    """The located box holds the detector box's own centre (it moved within one head, not onto a neighbour)."""
    bb = H0[s]["glyph_box"]["detail"]["bbox_page_px"]
    x, y, w, h = L[s]["box_page"]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    return x <= cx <= x + w and y <= cy <= y + h


L = {s: v for s, v in L.items() if s in H0 and same_head(s)} if "--same-head" in sys.argv else L
H = json.load(open(os.path.join(OUT, "heads_%s.json" % DOC)))
C = {r["subject"]: r for r in json.load(open(os.path.join(OUT, "causes.json")))[DOC]["rows"]}

# (1) control on every judged + hf head with both readings
diff = []
for s, h in H.items():
    st = (((h.get("notehead_ink") or {}).get("detail") or {}).get("interior_white") or {}).get("rows_share")
    pg = ((L.get(s) or {}).get("iw_det") or {}).get("rows_share")
    if st is not None and pg is not None:
        diff.append((abs(st - pg), s, st, pg))
diff.sort(reverse=True)
agree = sum(1 for d in diff if (d[2] >= 0.18) == (d[3] >= 0.18))
print("CONTROL detector-box rows_share, cell (stored) vs page (probe): n=%d, same side of 0.18: %d; worst %s" % (
    len(diff), agree, [(round(a, 2), s, b, c) for a, s, b, c in diff[:4]]))

# (2) hf heads
dec = []
n_loc = 0
for s, r in C.items():
    loc = L.get(s)
    if loc is None:
        continue
    n_loc += 1
    rs = loc["iw"]["rows_share"]
    fill = "hollow" if rs >= 0.18 else "black" if rs <= 0.06 else None
    if r["cause"].startswith("box_"):
        dec.append((s, r["cause"], bool(r["stems"]), fill, rs, loc["src"], r.get("crops")))
print("hf heads %d, with a located box %d; not-head-sized with a located box %d" % (len(C), n_loc, len(dec)))
import collections  # noqa: E402
print("  located reading on not-head-sized hf heads (cause, own stem, fill):",
      sorted(collections.Counter((c[:14], st, str(f)) for _, c, st, f, _, _, _ in dec).items()))
for d in dec:
    if d[6]:
        print("  crop", d[6], d[0], d[1], "stem", d[2], "located fill", d[3], d[4], d[5])

# (3) judged
for s, h in H.items():
    for j in h.get("judged", []):
        cls = ((h.get("notehead_class") or {}).get("value")) or ""
        if not cls.startswith("noteheadBlack") or s not in L:
            continue
        g = gate(h)
        rs = L[s]["iw"]["rows_share"]
        truth = "hollow" if j["value"] >= 2 else "black"
        call = "hollow" if rs >= 0.18 else "black" if rs <= 0.06 else "between"
        flag = "" if call in (truth, "between") else "   <-- WRONG"
        print("  judged %-7s det-box head-sized=%-5s located rs=%.3f -> %-7s %s %s %s%s" % (
            truth, g[0] if g else None, rs, call, s, j["item"], j["tile"], flag))
