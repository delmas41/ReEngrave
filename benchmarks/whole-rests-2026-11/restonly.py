"""summary of the rest-only red bars: per bar, record rows that bear on a rest. restonly.py PLATE (litolff|brahms)"""
import json, sys, collections
sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record

S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/"
LIT = {"A": "2/0/5/5 2/1/3/0 2/1/6/12 4/0/0/1 4/0/1/0 6/0/1/0 6/0/1/1 6/0/1/2 6/0/1/3 6/0/1/4 6/0/3/0 8/0/0/0 9/1/5/1 10/0/2/0",
       "B": "2/1/6/11 4/0/0/3 4/1/5/10 6/0/1/5 6/0/4/7 8/0/0/6 8/0/1/4 8/0/4/1 11/0/8/4 16/0/6/11"}
BRA = {"A": "4/1/6/5 4/1/6/7 5/1/4/3 8/0/0/12 8/1/5/9 12/0/7/10 12/1/7/2 12/1/7/8",
       "B": "4/0/4/7 4/1/0/2 8/0/0/0 8/0/0/5 8/0/1/11 8/0/7/5 8/0/10/1 8/1/0/5 8/1/1/11 8/1/2/9 8/1/4/0 12/0/8/1 12/1/0/5 12/1/0/6 12/1/1/4 12/1/5/0 12/1/5/5 12/1/8/3 12/1/8/8 12/1/8/9 14/0/0/3 14/1/2/1 14/1/5/2 19/0/6/9 25/1/1/1"}
plate = sys.argv[1]
SEL = LIT if plate == "litolff" else BRA
tag = "lit-a" if plate == "litolff" else "bra-a"
bars = {}
for st, s in SEL.items():
    for b in s.split():
        bars[b] = st
f = json.load(open(S + "2311/%s.facts.json" % tag))
r = load_record(S + "2311/%s.record.json" % tag)
rec = r.get("record", r)
want_q = {"empty_bar_rest_search", "empty_bar_whole_rest", "rest_duration", "rest_value", "cell_box"}
out = collections.defaultdict(list)


def cellof(subj):
    p = subj.split("/")
    if p[0] == "cell" and len(p) == 5:
        return "/".join(p[1:5])
    if p[0] == "glyph" and len(p) == 6:
        return "/".join(p[1:5])
    return None


for kind in ("observations", "verdicts", "abstentions"):
    for o in rec.get(kind) or []:
        s = o.get("subject", "")
        c = cellof(s)
        if c in bars:
            q = o.get("quantity")
            if kind == "observations" and q in ("glyph_conf", "stroke", "glyph_strokes", "page_mark", "page_mark_owner", "ledger_ink_under", "cell_ink_pieces", "cell_staff_space", "ink"):
                continue
            v = o.get("value")
            vs = v if isinstance(v, str) else json.dumps(v)
            out[c].append((kind[:3], s, q, o.get("outcome"), o.get("reason"), vs[:90]))
res = {}
for c, st in sorted(bars.items()):
    p = c.split("/")
    gl = [(k.split("/")[-1], g["cls"], g["fate"]) for k, g in f["glyphs"].items() if k.startswith("glyph/%s/" % c) and g["cls"] != "ledgerLine" and g["cls"] != "staff"]
    rows = [x for x in out[c] if x[2] not in ("glyph_box",)]
    res[c] = dict(stratum=st, glyphs=gl, rows=rows)
json.dump(res, open(S + "restonly-%s.json" % plate, "w"), default=str)
for c, d in res.items():
    print("==", c, d["stratum"], d["glyphs"])
    for x in d["rows"]:
        print("   ", x[0], x[1].split("/")[-1] if x[1].startswith("glyph") else "cell", x[2], x[3], x[4], x[5])
