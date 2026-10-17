"""ROADMAP 2.160 -- join Sean's judged glyph tiles (benchmarks/acceptance/judged-tiles.json) and the 2.158 lone-event
guesses to the per-head rows `heads_2_160.py` wrote, and print the distributions of `notehead_ink` (and its raw / net /
off-line readings), detector confidence and arc gap for REAL heads (Sean gave a value) vs NON-heads (Sean: not a note /
a rest / tile 14's tie tail). A judged key is a snapshot of one gather, so a key is taken only when the night record's
box under that key overlaps the tile's page box (IoU >= 0.3, or the box's centre lies inside the tile's page box, which is often the crop); else the best-overlapping notehead box on that page is
taken at IoU >= 0.3; else the tile is counted unmatched. Tiles with no page box are taken by key alone (flagged).
usage: join_2_160.py HEADS_LITOLFF.json HEADS_BRAHMS.json TILES_KEY_2158.json OUT.json"""
import collections
import json
import sys

HL, HB, KEY, OUT = sys.argv[1:5]
H = {"litolff": json.load(open(HL))["heads"], "brahms": json.load(open(HB))["heads"]}
by_page = {d: collections.defaultdict(list) for d in H}
for d, hs in H.items():
    for g, h in hs.items():
        by_page[d][g.split("/")[1]].append(g)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def match(doc, subj, pbox):
    hs = H[doc]
    if pbox is None:
        return (subj, "key_only") if subj in hs else (None, "no_box_no_key")
    if subj in hs:
        b = hs[subj]["box"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if iou(b, pbox) >= 0.3 or (pbox[0] <= cx <= pbox[2] and pbox[1] <= cy <= pbox[3]):
            return subj, "key+box"   # the tile's page box is often the crop around the glyph, not its box
    best = max(((iou(hs[g]["box"], pbox), g) for g in by_page[doc].get(subj.split("/")[1], ())), default=(0, None))
    if best[0] >= 0.3:
        return best[1], "box"
    return None, "unmatched"


tiles = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
rows = []
seen = set()
miss = collections.Counter()
for t in tiles:
    if t["doc"] not in H or t["subject_kind"] != "glyph" or not t["subject"]:
        continue
    ak = t["answer_kind"]
    if ak in ("duration", "duration_multi"):
        side = "real"
    elif ak == "not_a_note":
        side = "non"
    elif ak == "rest":
        side = "rest"
    elif t["item"] == "2.158-review" and t["tile"] in ("14", 14):
        side = "non"         # tile 14: a tie's tail boxed as a head (2.158 FINDINGS)
    else:
        continue
    g, how = match(t["doc"], t["subject"], t.get("page_box"))
    if g is None:
        miss[(t["doc"], side, how)] += 1
        continue
    if (t["doc"], g) in seen:
        continue
    seen.add((t["doc"], g))
    rows.append(dict(doc=t["doc"], glyph=g, side=side, how=how, item=t["item"], tile=t["tile"], answer=t["answer"],
                     value=t.get("value"), **H[t["doc"]][g]))

# the lone-event guesses (2.158 replay: Litolff 19 + Brahms 1) with Sean's 2.158 answers where he gave one
key = {r["glyph"]: r for r in json.load(open(KEY)) if r["role"] == "lone_event"}
LONE = {"litolff": ["glyph/1/0/9/11/1", "glyph/10/0/3/2/1", "glyph/10/1/1/8/8", "glyph/10/1/10/5/4", "glyph/11/0/1/10/7",
                    "glyph/11/0/1/9/2", "glyph/11/0/2/12/2", "glyph/11/0/2/8/3", "glyph/11/1/7/8/2", "glyph/14/0/3/3/6",
                    "glyph/14/0/3/5/0", "glyph/14/1/3/11/4", "glyph/14/1/3/12/1", "glyph/3/1/2/17/6", "glyph/5/1/4/2/1",
                    "glyph/5/1/6/5/2", "glyph/7/0/3/2/2", "glyph/9/0/4/2/8", "glyph/9/1/7/1/3"],
        "brahms": ["glyph/12/0/2/6/9"]}
lone = []
for d, gs in LONE.items():
    for g in gs:
        lone.append(dict(doc=d, glyph=g, side="non" if g == "glyph/5/1/4/2/1" else "real", tile=(key.get(g) or {}).get("n"),
                         **H[d][g]))

json.dump(dict(judged=rows, lone=lone, unmatched={"|".join(k): v for k, v in miss.items()}), open(OUT, "w"), indent=0)


def q(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return "n=0"
    p = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
    return "n=%d min %.3f p05 %.3f p25 %.3f med %.3f max %.3f" % (len(xs), xs[0], p(.05), p(.25), p(.5), xs[-1])


print("unmatched", dict(miss))
for title, rs in (("JUDGED", rows), ("LONE-EVENT GUESSES", lone)):
    print("==", title)
    for d in ("litolff", "brahms"):
        for side in ("real", "non", "rest"):
            sub = [r for r in rs if r["doc"] == d and r["side"] == side]
            if not sub:
                continue
            print(d, side, "count", len(sub))
            for f in ("ink", "ink_raw", "ink_net", "ink_off", "conf"):
                print("   %-8s %s" % (f, q([r[f] for r in sub])))
            print("   arc_gap  %s" % q([r["arc"][0] if r["arc"] else None for r in sub]))
            print("   arc<=0.5sp %d  left_gap<=0.5sp %d" % (
                sum(1 for r in sub if r["arc"] and r["arc"][0] <= 0.5),
                sum(1 for r in sub if r["left_gap_sp"] is not None and r["left_gap_sp"] <= 0.5)))
