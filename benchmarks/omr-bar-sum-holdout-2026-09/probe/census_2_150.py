"""ROADMAP 2.150 -- what every KEPT rest box stands on, from cached rows (cache_2_150.py). STAGED rows; decides nothing.
usage: census_2_150.py ROWS.json [glyph ...]   (named glyphs: print their neighbourhood)
Per rest box (canonical cell frame, sizes in the cell's staff spaces):
  w, h                  the box
  stem_in / stem_cross  a Q.STEM row overlapping the box (after GATHER's refuse_owned removed strokes >= 0.8 inside it)
  head_touch            a notehead box touching/overlapping the rest box (standing, i.e. not refused)
  head_end              a standing notehead box touching the rest box at its TOP or BOTTOM end, x-overlapping it
  flag_touch            a detector flag box overlapping the rest box
  text_touch            a dynamic/text/letter box overlapping it
  beam_touch            a detector beam box overlapping it"""
import json, sys, collections

d = json.load(open(sys.argv[1]))
NAMED = sys.argv[2:]
B, V = d["boxes"], d["verdicts"]
by_cell = collections.defaultdict(list)
for s, b in B.items():
    by_cell[s.rsplit("/", 1)[0].replace("glyph/", "cell/")].append((s, b))
stems = collections.defaultdict(list)
for rid, cell, v in d["stems"]:
    stems[cell].append((rid, v))


def ov(a, b, tol=0.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax <= bx + bw + tol and ax + aw >= bx - tol and ay <= by + bh + tol and ay + ah >= by - tol)


def standing_head(s):
    v = V.get(s, {}).get("notehead_is_not_a_notehead")
    return not (v and v[0] == "decided" and v[1])


def features(s, cls):
    b = B.get(s)
    cell = s.rsplit("/", 1)[0].replace("glyph/", "cell/")
    sp = (d["cells"].get(cell) or {}).get("space")
    if not b or not sp:
        return None
    x, y, w, h = b[2]
    box = (x, y, w, h)
    f = dict(w=round(w / sp, 2), h=round(h / sp, 2))
    f["stem_rows"] = [rid for rid, sv in stems.get(cell, []) if ov(box, sv)]
    tol = 0.15 * sp
    heads, ends, flags, texts, beams = [], [], [], [], []
    for o, ob in by_cell.get(cell, []):
        if o == s:
            continue
        oc = str(ob[0])
        obox = tuple(ob[2])
        if not ov(box, obox, tol):
            continue
        if oc.startswith("notehead"):
            if standing_head(o):
                heads.append(o)
                # at an END: the head's vertical centre is beyond the rest box's top or bottom third
                hc = obox[1] + obox[3] / 2
                if hc < y + h * 0.25 or hc > y + h * 0.75:
                    ends.append(o)
        elif oc.startswith("flag"):
            flags.append(o)
        elif oc.startswith("dynamic") or oc in ("text",) or oc.startswith("letter"):
            texts.append(o)
        elif oc == "beam":
            beams.append(o)
    f.update(heads=heads, head_end=ends, flags=flags, texts=texts, beams=beams)
    return f


rows = []
for s, cls in d["rest_rows"].items():
    v = V.get(s, {}).get("rest_is_not_a_rest")
    if not v or v[0] != "decided" or v[1] is not False:
        continue
    f = features(s, cls)
    if f is None:
        continue
    rows.append((s, cls, f))
print("kept rest boxes:", len(rows))
for cls in ("restQuarter", "rest8th", "rest16th", "restWhole", "restHalf"):
    sub = [f for s, c, f in rows if c == cls]
    if not sub:
        continue
    n = len(sub)
    cnt = collections.Counter()
    for f in sub:
        cnt["stem"] += bool(f["stem_rows"])
        cnt["head_touch"] += bool(f["heads"])
        cnt["head_end"] += bool(f["head_end"])
        cnt["flag"] += bool(f["flags"])
        cnt["text"] += bool(f["texts"])
        cnt["beam"] += bool(f["beams"])
        cnt["narrow<0.45"] += f["w"] < 0.45
        cnt["any_of_stem_head_flag"] += bool(f["stem_rows"] or f["head_end"] or f["flags"])
    ws = sorted(f["w"] for f in sub)
    hs = sorted(f["h"] for f in sub)
    q = lambda a, p: a[min(len(a) - 1, int(p * len(a)))]
    print("%-12s n=%5d  w p5/50/95 %.2f/%.2f/%.2f  h p5/50/95 %.2f/%.2f/%.2f  %s" % (
        cls, n, q(ws, .05), q(ws, .5), q(ws, .95), q(hs, .05), q(hs, .5), q(hs, .95), dict(cnt)))
for g in NAMED:
    cls = d["rest_rows"].get(g)
    print(g, cls, B.get(g, [None])[:3], V.get(g, {}).get("rest_is_not_a_rest"), V.get(g, {}).get("duration"))
    print("   ", features(g, cls))
json.dump([dict(glyph=s, cls=c, **f) for s, c, f in rows], open(sys.argv[1].replace("-rows.json", "-census.json"), "w"))
