"""2.306 r14: every head of Sean's swept Brahms p0 cells whose BEAM or FLAG judge.py scores, with how the exporter grouped the written note
(`r14_beam_groups.py`): under a read beam box (and where that box stands against the note's stem tip), a synthetic run, or alone. Ours.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/page-ledger-2026-11/2306/r14_flag_tally.py FACTS.json GROUPS.json
"""
import collections
import json
import sys

import judge as J

facts = json.load(open(sys.argv[1]))
groups = json.load(open(sys.argv[2]))
res = J.judge(facts)
page, truth, u, in_scope, swept = J.load_truth(J.TRUTH)
heads, att = J.attach(truth, u)
hid = {t.id: t for t in heads}
from tools.omr.staged.judged import boxes_overlap  # noqa: E402
w = [h for h in facts["written"] if h["page"] == 0 and h["kind"] == "note"]


def written_for(t):
    best = max(((boxes_overlap(h["box"], t.rect)[1], i) for i, h in enumerate(w) if boxes_overlap(h["box"], t.rect)[0]), default=None)
    return w[best[1]] if best else None


tally = collections.Counter()
rows = []
for kind in ("flag", "beam"):
    c = res["C"].get(kind)
    for (what, why), items in c.ex.items():
        for i in items:
            t = hid.get(i)
            if t is None:
                continue
            h = written_for(t)
            g = groups.get(h["rg"]) if h else None
            pick = None if g is None else g.get("pick")
            if isinstance(pick, dict):
                stem = att[t.id]["stem"]
                b = pick["box"]
                tip_y = None
                if stem is not None:
                    tip_y = stem.rect[1] if att[t.id]["direction"] == "up" else stem.rect[3]
                near_tip = tip_y is not None and b[1] - 1.0 * u <= tip_y <= b[1] + b[3] + 1.0 * u
                pk = "box(%s%s)" % ("tip" if near_tip else "NOT at its stem tip", ",suspect" if pick.get("suspect") else "")
            else:
                pk = str(pick)
            tally[(kind, what, why.split(" (")[0], pk)] += 1
            rows.append(dict(kind=kind, what=what, why=why, id=i, rg=h and h["rg"], pick=pick))
for k, n in sorted(tally.items()):
    print(n, k)
json.dump(rows, open(sys.argv[2] + ".tally.json", "w"), default=str)
