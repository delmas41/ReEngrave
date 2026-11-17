"""Brahms p0 (Sean's fully swept cells): rests by KIND right / wrong / unread, and how many of his labelled rests sit in a red bar.
   judge_rests.py FACTS.json"""
import json, sys, collections, re
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/note-loss-funnel-2026-11")
import judge as J
import redbars
from tools.omr.staged.judged import boxes_overlap

facts = json.load(open(sys.argv[1]))
page, truth, u, in_scope, swept = J.load_truth(J.TRUTH)
pg = {k: g for k, g in facts["glyphs"].items() if g["page"] == 0}
written = [h for h in facts["written"] if h["page"] == 0]
wnotes = [h for h in written if h["kind"] == "note"]
wrests = [h for h in written if h["kind"] == "rest"]
trests = [t for t in truth if t.family == "rest"]
rp = sorted(((boxes_overlap(h["box"], t.rect)[1], i, j) for i, t in enumerate(trests) for j, h in enumerate(wrests) if boxes_overlap(h["box"], t.rect)[0]), reverse=True)
r2w, rused = {}, set()
for _iou, i, j in rp:
    if i in r2w or j in rused:
        continue
    r2w[i] = j
    rused.add(j)
want = {"restWhole": ("whole", "?"), "restQuarter": ("quarter",), "rest8th": ("eighth",), "rest16th": ("16th",), "restHalf": ("half",)}
red = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in redbars.run(facts, {0})}
bars_by_cell = collections.defaultdict(list)
for t in trests:
    m = re.match(r"s(\d+)-st(\d+)-m(\d+)", t.cell_id)
    bars_by_cell[(0, int(m.group(1)), int(m.group(2)), int(m.group(3)))].append(t)
# every labelled mark per swept cell, to say whether the bar holds only rests
fam_by_cell = collections.defaultdict(collections.Counter)
for t in truth:
    m = re.match(r"s(\d+)-st(\d+)-m(\d+)", t.cell_id)
    fam_by_cell[(0, int(m.group(1)), int(m.group(2)), int(m.group(3)))][t.family] += 1
rows = collections.defaultdict(collections.Counter)
detail = []
for i, t in enumerate(trests):
    m = re.match(r"s(\d+)-st(\d+)-m(\d+)", t.cell_id)
    key = (0, int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if i in r2w:
        h = wrests[r2w[i]]
        ok = h["type"] in want.get(t.cls, ())
        out = "right" if ok else "wrong"
        why = "" if ok else "his %s, written %s" % (t.cls, h["type"])
    else:
        asnote = [h for h in wnotes if boxes_overlap(h["box"], t.rect)[0]]
        if asnote:
            out, why = "wrong", "written as a %s note" % asnote[0]["type"]
        else:
            cp = [g["fate"] for g in pg.values() if (g["rest"] or g["head"]) and boxes_overlap(g["box"], t.rect)[0]]
            out, why = "unread", ("fates: " + ",".join(sorted({str(x) for x in cp}))) if cp else "no box"
    rows[t.cls][out] += 1
    only_rests = set(fam_by_cell[key]) <= {"rest", "ledger_line", "barline", "text", "dynamic_letter", "brace", "arc", "slur", "tie", "fermata", "clef", "key", "time_signature", "meter"}
    detail.append((t.id, t.cls, out, why, key, key in red, dict(fam_by_cell[key])))
fakes = 0
for j, h in enumerate(wrests):
    if j in rused or not in_scope(h["box"]):
        continue
    fakes += 1
    rows["(fake rest written)"]["wrong"] += 1
for k, c in sorted(rows.items()):
    print("%-22s right %d wrong %d unread %d" % (k, c["right"], c["wrong"], c["unread"]))
print("labelled rests", len(trests), "in swept cells; in a red bar:", sum(1 for d in detail if d[5]))
for d in detail:
    if d[1] == "restWhole" or d[5] or d[2] != "right":
        print(d)
