"""2306 r6: (1) every head whose first duration reading drops MORE strokes as 'the neighbour staff's beam' ON than OFF, and what happened to its value;
(2) the page reader's stem VIEWS (reader cv_page_stems) filed in a cell for a glyph that the ON record says is OWNED BY ANOTHER STAFF (a padded copy)
-- the views the neighbour-beam rule then reads as that cell's own staff's stems. Usage: nbr_census.py RFPREFIX REC.json STEMROWS.txt"""
import sys, json, re, collections
pre, rec_p, rowsf = sys.argv[1], sys.argv[2], sys.argv[3]
rd = {l.split()[0]: (l.split()[1], l.split()[2]) for l in open(rowsf)}
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))


def firsts(D, q):
    o = {}
    for v in D["verdicts"]:
        if v["q"] == q and v["s"] not in o:
            o[v["s"]] = v
    return o


def lasts(D, q):
    return {v["s"]: v for v in D["verdicts"] if v["q"] == q}


da, db = firsts(A, "duration"), firsts(B, "duration")
fa, fb = lasts(A, "duration"), lasts(B, "duration")
own = lasts(B, "glyph_owner")
nb = lambda v: int(((v or {}).get("d") or {}).get("beams_neighbour_staff") or 0)
sig = lambda v: v and "%s:%s" % (v["o"], (v["v"] or {}).get("written") if isinstance(v["v"], dict) else None)
c = collections.Counter()
more = []
for g, v in db.items():
    if nb(v) > nb(da.get(g)):
        more.append(g)
        c[(sig(da.get(g)) == sig(v), "final %s -> %s" % (sig(fa.get(g)), sig(fb.get(g))))] += 1
print("heads whose own reading drops more strokes as the neighbour staff's beam ON:", len(more))
for k, n in c.most_common():
    print("  %3d own reading %s | %s" % (n, "unchanged" if k[0] else "CHANGED", k[1]))
# (2) views filed for other-staff copies
txt = open(rec_p, encoding="utf-8").read()
views_for = collections.defaultdict(list)
for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","value":"(obs:[0-9]+)"', txt):
    g, sid = m.group(1), m.group(2)
    if rd.get(sid, ("", ""))[1] == "cv_page_stems":
        views_for[sid].append(g)
del txt


def copy_of_other(g):
    v = own.get(g)
    return bool(v and v["o"] == "decided" and isinstance(v["v"], str) and v["v"] != "staff/" + "/".join(g.split("/")[1:4]))


n_views = len(views_for)
only_copies = [s for s, gs in views_for.items() if all(copy_of_other(g) for g in gs)]
print("views filed:", n_views, "| filed ONLY for heads the ON record gives to another staff:", len(only_copies))
print("glyph_owner verdict examples:", [(g, own[g]["o"], own[g]["r"], own[g]["v"]) for g in list(views_for[only_copies[0]])[:2]] if only_copies else None)
# the lost / changed heads that drop a neighbour beam: does the neighbour cell hold such a copy-view?
cellviews = collections.defaultdict(list)
for s in only_copies:
    cellviews[rd[s][0]].append(s)
hit = 0
for g in more:
    p, sy, st, ce = g.split("/")[1:5]
    if any(cellviews.get("cell/%s/%s/%d/%s" % (p, sy, int(st) + d, ce)) for d in (-1, 1)):
        hit += 1
print("of the %d heads dropping more neighbour beams, the neighbour cell holds a view filed only for a copy of another staff's head: %d" % (len(more), hit))
