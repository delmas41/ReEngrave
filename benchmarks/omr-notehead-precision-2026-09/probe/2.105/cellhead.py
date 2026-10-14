"""ROADMAP 2.105 (b): every notehead-class box in the cells of the named
subjects, with its not-a-notehead verdict and the stacked-head detail.
usage: cellhead.py RECORD KEY [KEY...]   (KEY = glyph/p/s/st/c/g)"""
import json
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
for key in sys.argv[2:]:
    sub = run.glyphs[key]
    print("=====", key, "cell", sub.cell_key)
    for g in sorted(run.glyphs.values(), key=lambda g: g.index):
        if g.cell_key != sub.cell_key or not (g.cls or "").startswith("notehead"):
            continue
        st, why = adjudicate_status(run, g)
        v = run.standing(g.key, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE")
        d = (v or {}).get("detail") or {}
        fit = run.obs_at(g.key, Q.STACKED_HEAD_FIT)
        print(("*" if g.key == key else " "), g.key, g.cls, [round(x) for x in g.box_page], g.score and round(g.score, 2),
              st, (v or {}).get("reason"))
        if fit:
            print("     fit", fit[-1]["value"], {k: fit[-1]["detail"].get(k) for k in ("stem", "side", "ink")})
        for k in ("stacked_head_signal", "duplicate_of", "stacked_head_this_ink", "stacked_head_other_ink"):
            if k in d:
                print("     ", k, json.dumps(d[k])[:300])
