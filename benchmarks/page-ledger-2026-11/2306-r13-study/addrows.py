"""2.306 r13 study: the O sample is drawn from ALL head boxes, so add minimal trace rows for sampled boxes that are not real heads (so look.py
can draw them). Usage: addrows.py"""
import json
from common import *
for plate in ("lit", "bra"):
    D = load(plate)
    ups = cell_up(D)
    T = json.load(open(S + "/r13/%s.trace.json" % plate))
    have = {r["g"] for r in T}
    sm = json.load(open(S + "/r13/%s.samples.json" % plate))
    add = 0
    for g in sm["O"]:
        if g in have:
            continue
        o, n = old_answer(D, g), new_answer(D, g)
        T.append(dict(g=g, page=pg(g), hid=None, head_box=D["heads"][g]["box"], new_head_box=None, has_oval=None, cls=D["cls"].get(g), old_stem=o["stem"],
                      old_why=o["why"], old_dir=o["direction"], old_dir_why=o["dir_why"], old_box=stem_page_box(D, ups, o["stem"]), old_xfrac=None,
                      new_read=n["read"], new_how=n["how"], new_dir=n["direction"], new_stroke=n["stroke"], new_box=(n["row"] or {}).get("stem_box"),
                      sp=staff_sp(D, g), written_off=g in D["written_off"], written_on=g in D["written_on"], not_real=True))
        add += 1
    json.dump(T, open(S + "/r13/%s.trace.json" % plate, "w"))
    print(plate, "added", add)
