"""arcs-r2: the 12 tiles by a stated seeded rule.  python3 select_tiles_r2.py OUT_SELECTION.json SEED

RULE (fixed before the draw; `random.Random(SEED)`): (1) the formerly wrong runs that are STILL WRITTEN on the new tree (the five named failures all abstain now: no tile; listed in the report), then the
two wrong ones found on the new tree by my look (old seed #07 Litolff p5 run 97, #17 Litolff p5 run 18; fresh seed #06 Brahms p18 run 42) -- the honest test of my look; (2) runs written by BOTH trees whose
bound heads CHANGED (base vs new), seeded draw; (3) the rest from the fresh 30 (pick-new2-fresh.json) not yet used, seeded draw. Order: shuffled with the same generator (tile numbers carry no meaning).
"""
import json
import random
import sys

R = "/private/tmp/claude-501/scr-arcs-r2/"
seed = int(sys.argv[2])
rnd = random.Random(seed)
PIC = {"litolff": {"hold": "pick-new2-hold-litolff", "dev": "pick-new2-dev-litolff"}, "brahms": {"hold": "pick-new2-hold-brahms", "dev": "pick-new2-dev-brahms"}}
HOLD = {"litolff": {5, 13, 15}, "brahms": {11, 18, 20}}


def written(label, plate, st):
    out = {}
    for v in json.load(open(R + "pick-%s-%s-%s/%s.on.extra.json" % (label, st, plate, plate))):
        pg = int(v["subject"].split("/")[1])
        for r in v["detail"]["runs"]:
            if r["status"] == "written" and r.get("piece") is None:
                out[(pg, r["ordinal"])] = (r["start"], r["stop"], r["kind"])
    return out


items, seen = [], set()
def add(plate, st, pg, rn, why):
    if (plate, pg, rn) in seen:
        return
    seen.add((plate, pg, rn))
    items.append(dict(plate=plate, pickdir=R + PIC[plate][st], page=pg, run=rn, why=why))

for plate, pg, rn, why in (("litolff", 5, 97, "found wrong on the new tree (old seed 07)"), ("litolff", 5, 18, "found wrong on the new tree (old seed 17)"), ("brahms", 18, 42, "found wrong on the new tree (fresh seed 06)")):
    add(plate, "hold", pg, rn, why)
changed = []
for plate in ("litolff", "brahms"):
    for st in ("hold", "dev"):
        b, n = written("base", plate, st), written("new2", plate, st)
        for k, v in n.items():
            if k in b and (b[k][0] != v[0] or b[k][1] != v[1]):
                changed.append((plate, st, k[0], k[1]))
print("runs written by both trees with changed bound heads:", len(changed))
rnd.shuffle(changed)
for plate, st, pg, rn in changed[:6]:
    add(plate, st, pg, rn, "binding changed base->new")
fresh = [x for x in json.load(open(R + "pick-new2-fresh.json"))["sample"]]
rnd.shuffle(fresh)
for x in fresh:
    if len(items) >= 12:
        break
    add(x["plate"], "hold", x["page"], x["run"], "fresh sample (%s)" % x["category"])
rnd.shuffle(items)
json.dump(dict(seed=seed, rule=__doc__.split("RULE")[1].split("\n\n")[0] if "RULE" in __doc__ else "", items=items), open(sys.argv[1], "w"), indent=1)
print(len(items), "items")
