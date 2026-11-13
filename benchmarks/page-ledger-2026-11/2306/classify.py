"""2306 r6: one cause per note written OFF and not ON (and per eighth -> quarter), first that applies, upstream first:
  stitch   the head's page stem is a run stitched over > 1 sp of empty paper (stitch_check dump)
  nbr      its own duration reading drops MORE strokes as 'the neighbour staff's beam' ON (the neighbour cell holds the page reader's view)
  view     its ON stem row is a page VIEW (reader cv_page_stems: no beam-level / beam-join rows) and its own reading changed
  dir      the page's stem direction differs from OFF's and its own reading changed
  own      its own reading changed, none of the above
  mate:X   its own reading is unchanged; a head on the same stem / in the same chord changed, by cause X
  bar      its own reading is unchanged and no mate changed: the bar (EVALUATE/INFER) wrote it OFF and not ON
Usage: classify.py RFPREFIX STEMROWS.txt STITCH.json WHY.txt"""
import sys, json, re, collections
pre, rowsf, stf, why = sys.argv[1:5]
rd = {l.split()[0]: l.split()[2] for l in open(rowsf)}
stitch = json.load(open(stf))
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
targets = {}
for line in open(why):
    m = re.match(r"(LOST|EIGHTH->QUARTER) (glyph/\S+) ", line)
    if m:
        targets[m.group(2)] = m.group(1)


def index(D):
    first, last = {}, collections.defaultdict(dict)
    for v in D["verdicts"]:
        if v["q"] == "duration" and v["s"] not in first:
            first[v["s"]] = v
        last[v["s"]][v["q"]] = v
    return first, last


FA, LA = index(A)
FB, LB = index(B)
sig = lambda v: v and (v["o"], v["r"], json.dumps(v["v"], sort_keys=True, default=str))
nb = lambda v: int(((v or {}).get("d") or {}).get("beams_neighbour_staff") or 0)
# page stem rows of the ON record: glyph -> (page_stroke) from the head_stem detail
def own_cause(g):
    a, b = FA.get(g), FB.get(g)
    hb = LB[g].get("head_stem") or {}
    st = (hb.get("d") or {}).get("page_stroke")
    p = g.split("/")[1]
    if st is not None and (stitch.get("%s/%s" % (p, st)) or [None, 0])[1] > 1.0:
        return "stitch"
    changed = sig(a) != sig(b)
    if nb(b) > nb(a) and changed:
        return "nbr"
    if changed and hb.get("o") == "decided" and rd.get(str(hb.get("v"))) == "cv_page_stems":
        return "view"
    da, db = (LA[g].get("stem_direction") or {}).get("v"), (LB[g].get("stem_direction") or {}).get("v")
    if changed and da != db:
        return "dir"
    if changed:
        return "own"
    return None


def mates(g):
    out = set()
    for L in (LA, LB):
        sv = L[g].get("stem_value") or {}
        out |= set(((sv.get("d") or {}).get("members")) or [])
    cell = "/".join(g.split("/")[:5])
    # heads of the same cell that share the ON or OFF stem row
    for L in (LA, LB):
        hs = (L[g].get("head_stem") or {}).get("v")
        if hs:
            for s, qs in L.items():
                if s.startswith(cell + "/") and (qs.get("head_stem") or {}).get("v") == hs:
                    out.add(s)
    out.discard(g)
    return out


res = collections.Counter()
rows = []
for g, kind in sorted(targets.items()):
    c = own_cause(g)
    if c is None:
        mc = sorted({own_cause(m) for m in mates(g)} - {None})
        if mc:
            c = "mate:" + "+".join(mc)
        else:
            cell = "/".join(g.split("/")[:5]) + "/"
            bm = sorted({own_cause(m) for m in set(LA) | set(LB) if m.startswith(cell) and m != g} - {None})
            c = "bar-mate:" + "+".join(bm) if bm else "bar"
    res[(kind, c)] += 1
    rows.append((kind, g, c))
for k, n in sorted(res.items()):
    print("%3d  %-16s %s" % (n, k[0], k[1]))
print()
for r in rows:
    print(*r)
