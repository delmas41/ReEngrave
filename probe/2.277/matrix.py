"""2.277 measure step: the claim x later-reader matrix, from a dump.py table (one plate, flag OFF).

usage: matrix.py DUMP.json [--cut 0.5] [--json OUT]

For every detector box: its family (stroke_owner.family_of), the share of ITS OWN ink (sum over the strokes under it of stroke ink x share
inside the box) that the stroke owner gave to each OTHER family, and its fate (the precision verdict's reason).  Rows: the family that
holds >= cut of the box's ink (barline, word, bracket, clef, ... ; the 'earlier' claim kinds are the area families + whole_rest);
columns: what the later reader did with the box -- refused BY THAT CLAIM (claimed_by:*), refused by something else (named), or KEPT.
"""
import collections
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import stroke_owner as SO     # noqa: E402

args = sys.argv[1:]
cut = 0.5
if "--cut" in args:
    cut = float(args[args.index("--cut") + 1])
D = json.load(open(args[0]))
rows = D["rows"]
EARLY = set(SO.AREA_OWNERS) | {"whole_rest"}


def held_by(r):
    tot, by = 0.0, collections.Counter()
    for o, sh, cov, ink, kind, own in r["strokes"]:
        if ink is None:
            continue
        w = ink * sh
        tot += w
        if own and own[0] in ("decided", "merged") and own[1]:
            by[own[1]] += w
    return tot, by


def fate_of(r):
    for q, (val, reason, outcome) in r["fate"].items():
        if val is True:
            return "refused:" + str(reason)
        if val is False:
            return "kept"
        return "abstained:" + str(reason)
    return "no_verdict"


M = collections.defaultdict(collections.Counter)      # (box family, holder) -> fate counter
dist = collections.defaultdict(list)
for r in rows:
    fam = SO.family_of(r["cls"], r.get("cat"))
    if fam is None or fam in SO.CONSUMERS:
        continue
    tot, by = held_by(r)
    if tot <= 0:
        continue
    for f, w in by.items():
        if f in EARLY and f != fam:
            sh = w / tot
            dist[(fam, f)].append(sh)
            if sh >= cut:
                M[(fam, f)][fate_of(r)] += 1
print("cut", cut, "plate", D["plate"], "boxes", len(rows))
for (fam, f), c in sorted(M.items(), key=lambda t: -sum(t[1].values())):
    n = sum(c.values())
    claim_ref = sum(v for k, v in c.items() if k.startswith("refused:claimed_by") or k.startswith("refused:not_a"))
    kept = c.get("kept", 0)
    print("%-10s held by %-15s n=%-5d kept=%-5d  by-claim=%-4d  other: %s" % (fam, f, n, kept, c.get("refused:claimed_by:" + f, 0),
          dict(c.most_common(6))))
print("--- held-share histogram (head boxes by holder)")
for (fam, f), v in sorted(dist.items()):
    if fam not in ("head", "rest", "accidental"):
        continue
    h = collections.Counter(min(int(x * 10), 9) for x in v)
    print("%-10s %-15s n=%-5d deciles:%s" % (fam, f, len(v), [h.get(i, 0) for i in range(10)]))
if "--json" in args:
    json.dump({"%s|%s" % k: dict(v) for k, v in M.items()}, open(args[args.index("--json") + 1], "w"), indent=1)
