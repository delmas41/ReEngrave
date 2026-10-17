"""ROADMAP 2.155 -- PROBE: base vs arm records (same pages, same code, `--through adjudicate`): every glyph whose `adjudicate_duration`
verdict differs (outcome, reason, written, candidates), and the Q.STEM / Q.BEAM_STEM_JOIN row counts per arm.
usage: diff_2_155.py BASE.record.json ARM.record.json OUT.json"""
import json
import sys
from collections import Counter


def load(p):
    r = json.load(open(p))
    return r.get("record", r)


def dur(r):
    out = {}
    for v in r["verdicts"]:
        if v["quantity"] == "duration" and v.get("decider") == "adjudicate_duration" and v["subject"] not in out:
            val = v["value"] if isinstance(v["value"], dict) else {}
            out[v["subject"]] = (v["outcome"], v.get("reason"), val.get("written"),
                                 tuple(sorted(c.get("written") for c in (v.get("candidates") or []) if isinstance(c, dict)
                                              and c.get("written") is not None)))
    return out


a, b = load(sys.argv[1]), load(sys.argv[2])
for name, r in (("base", a), ("arm", b)):
    c = Counter(o["quantity"] for o in r["observations"] if o["quantity"] in ("stem", "beam_stroke", "beam_stem_join"))
    j = Counter(o["value"] for o in r["observations"] if o["quantity"] == "beam_stem_join")
    print(name, dict(c), "join values", dict(j))
da, db = dur(a), dur(b)
ch = [(g, da.get(g), db.get(g)) for g in sorted(set(da) | set(db)) if da.get(g) != db.get(g)]
kinds = Counter((x[0] if x else None, y[0] if y else None, x[2] if x else None, y[2] if y else None) for _g, x, y in ch)
print("duration verdicts", len(da), "changed", len(ch))
for k, n in kinds.most_common():
    print("  ", n, k)
json.dump([dict(glyph=g, base=x, arm=y) for g, x, y in ch], open(sys.argv[3], "w"), indent=0)
