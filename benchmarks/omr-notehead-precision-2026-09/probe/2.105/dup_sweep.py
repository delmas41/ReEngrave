"""ROADMAP 2.105 (b): for every box refused `stacked_head_duplicate`, what
became of the box it names as its winner? usage: dup_sweep.py RECORD"""
import collections
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
obs_subject = {o["id"]: o["subject"] for o in run.observations if o["quantity"] in (Q.GLYPH_BOX, Q.STACKED_HEAD_FIT)}
c = collections.Counter()
bad = []
for g in run.glyphs.values():
    v = run.standing(g.key, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE")
    if not v or v.get("reason") != "stacked_head_duplicate" or v.get("value") is not True:
        continue
    win = (v.get("detail") or {}).get("duplicate_of")
    wk = obs_subject.get(win)
    if wk is None:
        c["winner_unknown"] += 1
        continue
    st, _ = adjudicate_status(run, run.glyphs[wk])
    dv = run.standing(wk, Q.DURATION, "ADJUDICATE")
    c[(st, (dv or {}).get("outcome"))] += 1
    if st != "kept":
        bad.append((g.key, g.cls, wk, run.glyphs[wk].cls, st))
print(sum(c.values()), dict(c))
for b in bad[:40]:
    print(b)
