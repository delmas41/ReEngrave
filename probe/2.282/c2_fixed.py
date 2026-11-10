"""2.282: the fixed checks (Sean's tiles of 2026-11-09), traced through a re-adjudicated slice: what else has a box on the ink, how the stroke owner
settled each stroke under the head box, what the notehead / accidental verdicts say, whether a stem touches it.
usage: c2_fixed.py SLICE_ROOT PLATE SUBJECT [SUBJECT ...]       (SLICE_ROOT holds litolff/ brahms/)"""
import collections
import json
import sys

root, plate = sys.argv[1:3]
subs = sys.argv[3:]
d = "%s/%s" % (root, plate)
glyph, cellof = {}, collections.defaultdict(list)
strokes = {}
gs = {}
for line in open(d + "/observations.jsonl"):
    if '"glyph_box"' in line or '"glyph_strokes"' in line or '"stroke"' in line:
        o = json.loads(line)
        q = o["quantity"]
        if q == "glyph_box" and (o["detail"] or {}).get("bbox_page_px"):
            cell = "cell/" + o["subject"][6:].rsplit("/", 1)[0]
            glyph[o["subject"]] = dict(cls=o["value"][0], box=o["detail"]["bbox_page_px"], score=o.get("score"), cell=cell, reader=o.get("reader"))
            cellof[cell].append(o["subject"])
        elif q == "glyph_strokes":
            gs[o["subject"]] = (o["value"], o["detail"].get("shares"))
        elif q == "stroke" and o["subject"].startswith("glyph/"):
            cell = "cell/" + o["subject"][6:].rsplit("/", 1)[0]
            strokes[(cell, int(o["subject"].rsplit("/", 1)[1]) - 375000)] = dict(kind=o["value"], len=o["detail"].get("length_spaces"),
                                                                              thick=o["detail"].get("thickness_spaces"), page=o["detail"].get("bbox_page_px"))
cells = {glyph[s]["cell"] for s in subs if s in glyph}
verd = collections.defaultdict(list)
owner = {}
for line in open(d + "/verdicts.jsonl"):
    v = json.loads(line)
    sub = v["subject"]
    c = "cell/" + sub[6:].rsplit("/", 1)[0] if sub.startswith("glyph/") else sub
    if c not in cells:
        continue
    if v["quantity"] == "stroke_owner":
        owner[sub] = v
    elif sub.startswith("glyph/"):
        verd[sub].append((v["quantity"], v["outcome"], v.get("reason"), v["value"] if not isinstance(v["value"], (dict, list)) else "..."))


def ov(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


for s in subs:
    g = glyph.get(s)
    if g is None:
        print("\n==", s, "NO BOX")
        continue
    print("\n==", s, "box", [round(x) for x in g["box"]], "cls", g["cls"], "score %.2f" % (g["score"] or 0))
    for t in cellof[g["cell"]]:
        h = glyph[t]
        o = ov(g["box"], h["box"])
        if o >= 0.15:
            print("   box", t.split("/")[-1], h["cls"], "score %.2f" % (h["score"] or 0), "overlap %.2f" % o, h["reader"])
            for q in verd.get(t, []):
                if q[0] in ("notehead_is_not_a_notehead", "accidental_is_not_an_accidental", "accidental_owner", "rest_is_not_a_rest", "stem_value", "head_stem", "duration"):
                    print("        ", q)
    ow = owner.get(g["cell"])
    own = (ow.get("detail") or {}) if ow else {}
    strs = gs.get(s, ([], []))[0]
    for o_ in strs:
        st = strokes.get((g["cell"], o_), {})
        e = (own.get("strokes") or {}).get(str(o_))
        print("   stroke", o_, st.get("kind"), "len", st.get("len"), "thick", st.get("thick"), "->", e if e is None else [e[0], e[1], e[3], [(c[0].split('/')[-1], c[1], c[3], c[4][:40]) for c in e[4]]])
    # vertical strokes of the cell touching the head box
    for (c, o_), st in strokes.items():
        if c != g["cell"] or o_ in strs or not st["page"] or st["kind"] != "vertical":
            continue
        pb = st["page"]
        hb = g["box"]
        if pb[2] >= hb[0] - 4 and pb[0] <= hb[2] + 4 and pb[3] >= hb[1] - 4 and pb[1] <= hb[3] + 4:
            e = (own.get("strokes") or {}).get(str(o_))
            print("   nearby vertical", o_, "len", st["len"], "->", e if e is None else [e[0], e[1], e[3], [(c2[0].split('/')[-1], c2[1], c2[3]) for c2 in e[4]]])
    cf = (own.get("claim_final") or {})
    print("   claim_final held:", {k: v for k, v in (cf.get("held") or {}).items() if k == s})
