"""ROADMAP 2.168 -- score the off/on replay (`replay_2_168.py`): notes turned blue per plate, values changed (must be 0), Set B,
and the precision of the mark on every judged note it turned blue.
usage: score_2_168.py OUTDIR OUT.json"""
import collections
import json
import os
import pathlib
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged as J  # noqa: E402

OUTDIR, OUT = sys.argv[1:3]
VALKEYS = ("outcome", "written", "dots", "beats", "beam_levels", "rest", "measure_rest")


def vkey(b):
    b = b or {}
    # a DECIDED note's candidates are the mark itself (the bar's alternative); only a NARROWED note's candidates are its value
    return tuple(b.get(k) for k in VALKEYS) + ((tuple(b.get("cands") or ()),) if b.get("outcome") == "narrowed" else ())

idx = json.loads(J.INDEX_PATH.read_text())
key_b = {k["glyph"]: k for k in json.load(open("out/2.162/tiles-key-b.json"))}
res = {}
for doc in ("litolff", "brahms"):
    p_off, p_on = (os.path.join(OUTDIR, "%s.%s.json" % (doc, a)) for a in ("off", "on"))
    if not (os.path.exists(p_off) and os.path.exists(p_on)):
        continue
    off, on = json.load(open(p_off)), json.load(open(p_on))
    gl_off, gl_on = off["glyphs"], on["glyphs"]
    changed = [g for g in set(gl_off) | set(gl_on)
               if vkey(gl_off.get(g)) != vkey(gl_on.get(g))]
    meters_changed = [s for s in set(off["meters"]) | set(on["meters"]) if off["meters"].get(s) != on["meters"].get(s)]
    marked = {m["glyph"]: m for m in on["marked"]}
    rec_on = pathlib.Path(os.path.join(OUTDIR, "%s.on.record.json" % doc))
    sc = J.score(idx, rec_on, doc)
    judged_marked = []
    for t in sc["tiles"]:
        subs = t.get("subjects") or t.get("subject") or []
        subs = [subs] if isinstance(subs, str) else [x for x in subs if isinstance(x, str)]
        hit = [s for s in subs if s in marked]
        if hit:
            judged_marked.append(dict(item=t["item"], tile=t["tile"], subject=hit[0], answer=t["answer"],
                                      status=t["status"], note=t.get("note"),
                                      kept=marked[hit[0]]["kept"]["beats"], alt=marked[hit[0]]["alternative"].get("beats")))
    setb = []
    for g, k in key_b.items():
        if k["doc"] != doc:
            continue
        setb.append(dict(n=k["n"], glyph=g, blue=g in marked, role=k["role"]))
    res[doc] = dict(blue_on=len(marked), blue_off=len(off["marked"]), values_changed=len(changed),
                    changed_sample=changed[:10], meters_changed=len(meters_changed),
                    guessed_by_rule_off=off["guessed_by_rule"], guessed_by_rule_on=on["guessed_by_rule"],
                    judged_blue=len(judged_marked),
                    judged_blue_wrong=sum(1 for j in judged_marked if j["status"] == "wrong"),
                    judged_blue_right=sum(1 for j in judged_marked if j["status"] == "right"),
                    judged_blue_other=sum(1 for j in judged_marked if j["status"] not in ("right", "wrong")),
                    judged_rows=judged_marked, setB=setb)
    print(doc, {k: v for k, v in res[doc].items() if k not in ("judged_rows", "setB", "changed_sample")})
    print("  setB", [(s["n"], s["blue"]) for s in setb])
json.dump(res, open(OUT, "w"), indent=1, default=str)
