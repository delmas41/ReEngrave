"""ROADMAP 2.153b -- why does a page slice's OFF arm differ from the stored live duration verdict? Replays ONE page (OFF) and
tallies (stored decider/reason -> replay decider/reason) and whether the first ADJUDICATE verdict agrees.
usage: ctl_2_153b.py DOC SLICEDIR PAGE [CTX]     CTX = number of preceding pages to include (default 1)"""
import collections
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, P = sys.argv[1], sys.argv[2], int(sys.argv[3])
CTX = int(sys.argv[4]) if len(sys.argv) > 4 else 1
D = os.path.join(SD, DOC)


def rows(tag, kind):
    p = os.path.join(D, "%s.%s.jsonl" % (tag, kind))
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def chains(vs):
    c = collections.defaultdict(list)
    for v in vs:
        if v["quantity"] == "duration" and v["subject"].startswith("glyph/%d/" % P):
            c[v["subject"]].append(v)
    return c


def live(ch):
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
    return ([x for x in ch if x["id"] not in sup] or ch)[-1]


def k(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    return (v["outcome"], val.get("beats"), v.get("decider"), v.get("reason"))


tags = ["common"] + ["p%02d" % q for q in range(max(P - CTX, 0), P + 1)]
rec = {kk: [r for t in tags for r in rows(t, kk)] for kk in ("observations", "abstentions")}
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
new = chains(log.to_json()["verdicts"])
old = chains(rows("p%02d" % P, "verdicts"))
first = collections.Counter()
tal = collections.Counter()
for g, ch in old.items():
    a, b = live(ch), live(new.get(g) or [None]) if new.get(g) else None
    fa = next((x for x in ch if x.get("decider") == "adjudicate_duration"), None)
    fb = next((x for x in new.get(g, []) if x.get("decider") == "adjudicate_duration"), None)
    first["first_adj " + ("agree" if (fa and fb and k(fa) == k(fb)) or (fa is None and fb is None) else "differ")] += 1
    if b is None or k(a) != k(b):
        tal["%s/%s -> %s/%s" % (a.get("decider"), a.get("reason"), b and b.get("decider"), b and b.get("reason"))] += 1
print("ctx", CTX, dict(first), "live differ", sum(tal.values()))
for t, n in tal.most_common(12):
    print("  %4d %s" % (n, t))
