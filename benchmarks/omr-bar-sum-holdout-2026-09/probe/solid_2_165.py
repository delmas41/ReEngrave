"""ROADMAP 2.165 -- what does "solid" mean? MEASURED against Sean's judged answers, never an assumed cut.
Reads the OFF replay (`replay_2_165.py`: per-glyph live duration verdict + the reader's own evidence keys) and Sean's judged
tiles (`judged-tiles.json` through `judged.score`, plus Set B from `out/2.162/tiles-key-b.json` and his typed answers), and
tabulates for every judged DECIDED duration the evidence class the reader recorded against right / wrong.
usage: solid_2_165.py OUTDIR DOC [DOC...]  -> prints tables; writes OUTDIR/solid.json"""
import collections
import json
import os
import pathlib
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged as J  # noqa: E402

OUTDIR, DOCS = sys.argv[1], sys.argv[2:]
idx = json.loads(J.INDEX_PATH.read_text())
SETB = {1: .5, 2: .5, 3: 1.0, 4: .5, 5: 1.5, 6: 1.5, 7: .5, 8: 1.0, 9: .5, 10: .5}      # Sean's answers in beats (quarter = 1)
key_b = {k["glyph"]: k for k in json.load(open("out/2.162/tiles-key-b.json"))}
rows = []
for doc in DOCS:
    off = json.load(open(os.path.join(OUTDIR, "%s.off.json" % doc)))
    gl = off["glyphs"]
    sc = J.score(idx, pathlib.Path(os.path.join(OUTDIR, "%s.off.record.json" % doc)), doc)
    for t in sc["tiles"]:
        subs = t["subject"] if isinstance(t["subject"], list) else [t["subject"]]
        subs = [s for s in subs if isinstance(s, str)]
        if len(subs) != 1 or t["status"] not in ("right", "wrong", "narrowed"):
            continue
        g = gl.get(subs[0])
        if not g:
            continue
        rows.append(dict(doc=doc, item=t["item"], tile=t["tile"], glyph=subs[0], status=t["status"], g=g))
    for g, k in key_b.items():
        if k["doc"] != doc or g not in gl:
            continue
        beats = gl[g]["beats"]
        # Set B was judged on the BASE (2.162) reading of the note; the OFF replay's live reading is the decided one the bar disputes
        rows.append(dict(doc=doc, item="2.162-review-b", tile=k["n"], glyph=g, g=gl[g],
                         status="right" if beats == SETB[k["n"]] else "wrong"))


def cls(r):
    g = r["g"]
    e = g.get("ev") or {}
    return (g["outcome"], e.get("origin_decider") or g.get("decider"), e.get("origin_reason") or g.get("reason"),
            e.get("beam_evidence"), "refused_strokes" if e.get("beams_not_by_ink") else "no_refused", "rest" if g["rest"] else "note")


tab = collections.defaultdict(collections.Counter)
for r in rows:
    tab[cls(r)][r["status"]] += 1
print("judged duration notes with a standing verdict:", len(rows))
print("%-95s %5s %5s %5s" % ("class (outcome, origin decider, reason, beam_evidence, strokes, kind)", "right", "wrong", "narr"))
for k, c in sorted(tab.items(), key=lambda kv: -sum(kv[1].values())):
    print("%-95s %5d %5d %5d" % (k, c["right"], c["wrong"], c["narrowed"]))
json.dump([dict(r, cls=list(cls(r))) for r in rows], open(os.path.join(OUTDIR, "solid.json"), "w"), default=str, indent=0)
