"""ROADMAP 2.105 (b): per stacked-head slot group (cell, stem, side, slot) that
had a `stacked_head_duplicate` refusal: how many members stay LIVE (kept /
narrowed / abstained), by ADJUDICATE status? 0 = 'neither', >=2 = 'both'.
usage: group_sweep.py RECORD [--list N]"""
import collections
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
groups = collections.defaultdict(list)
for o in run.observations:
    if o["quantity"] != Q.STACKED_HEAD_FIT or not isinstance(o["value"], list):
        continue
    d = o.get("detail") or {}
    cell = "/".join(o["subject"].split("/")[1:5])
    groups[(cell, d.get("stem"), d.get("side"), o["value"][1])].append(o["subject"])
subj_of = {o["id"]: o["subject"].split("/")[-1] for o in run.observations
           if o["quantity"] in (Q.GLYPH_BOX, Q.STACKED_HEAD_FIT)}
c = collections.Counter()
ex =collections.defaultdict(list)
for key, members in groups.items():
    refs = [m for m in members
            if (run.standing(m, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE") or {}).get("reason") == "stacked_head_duplicate"]
    if not refs:
        continue
    live = [m for m in members if adjudicate_status(run, run.glyphs[m])[0] in ("kept", "narrowed", "abstained")]
    n = len(live)
    c[min(n, 3)] += 1
    ex[min(n, 3)].append((key[0], [(m.split("/")[-1], run.glyphs[m].cls, adjudicate_status(run, run.glyphs[m])[0],
                                    (run.standing(m, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE") or {}).get("reason"),
                                    ((run.standing(m, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE") or {}).get("detail") or {}).get("duplicate_of") and "->" + subj_of.get(((run.standing(m, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE") or {}).get("detail") or {}).get("duplicate_of")))
                                   for m in members]))
print("groups with a stacked_head_duplicate refusal:", sum(c.values()), "live-members histogram:", dict(sorted(c.items())))
for n in (0, 2, 3):
    print("--- live =", n)
    for e in ex[n][:int(sys.argv[3]) if len(sys.argv) > 3 else 12]:
        print(e)
