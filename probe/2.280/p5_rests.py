"""2.280 probe 5: for the 'no vertical ink' bucket (stratum A): is the kept 'head' a rest? what else is boxed on it, what do its own ink rows say.
usage: p5_rests.py plate RERUN.json BUCKETS.json"""
import collections
import json
import sys

plate, rr, bk = sys.argv[1:4]
R = json.load(open(rr))
B = json.load(open(bk))
none = [s for s, b in B.items() if b["stratum"] == "A" and b["cause"].startswith("0")]
want = set(none)
cells = {"cell/" + s[6:].rsplit("/", 1)[0] for s in none}
info = collections.defaultdict(dict)
boxes = collections.defaultdict(list)
SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/"
for l in open(SL + plate + "/observations.jsonl"):
    o = json.loads(l)
    q = o["quantity"]
    s = o["subject"]
    if q == "glyph_box":
        ck = "cell/" + s[6:].rsplit("/", 1)[0]
        if ck in cells:
            boxes[ck].append((s, o["value"], o["score"], o["detail"].get("category")))
    if s in want and q in ("page_mark", "head_ink", "rest_ink_contact", "unboxed_rest_shape", "glyph_conf"):
        info[s][q] = (o["value"], {k: v for k, v in o["detail"].items() if k in ("family", "why", "margin", "fill")})
for s in none:
    ck = "cell/" + s[6:].rsplit("/", 1)[0]
    x, y, w, h = R[s]["box"]
    ov = [(b[0].split("/")[-1], b[1][0], round(b[2] or 0, 2)) for b in boxes[ck]
          if b[0] != s and b[1][1] < x + w and b[1][1] + b[1][3] > x and b[1][2] < y + h and b[1][2] + b[1][4] > y]
    print(s, R[s]["cls"][:20], "w%.2f h%.2f" % (R[s]["w_sp"], R[s]["h_sp"]), "head_ink", (info[s].get("head_ink") or [None])[0],
          "overlap", ov, "pm", (info[s].get("page_mark") or [None, {}])[1].get("family"))
