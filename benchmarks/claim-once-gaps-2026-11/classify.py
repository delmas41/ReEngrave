"""2.322 measure 3: head boxes (share>=.10 by a non-head claim) covered by Sean's judged answers / judged claim tiles, real head or not, written or not,
by group, and what each candidate refusal rule would do to them.    python3 classify.py PLATE DATADIR"""
import collections
import json
import pathlib
import re
import sys

plate, data = sys.argv[1], pathlib.Path(sys.argv[2])
LATER = {"accidental", "arc", "hairpin", "dynamic", "mark", "dot", "rest"}
heads = {h["subject"]: h for h in json.load(open(data / ("%s_heads2.json" % plate)))}
cov = json.load(open(data / ("%s_covered.json" % plate)))


def verdict(c):
    real, notreal = [], []
    for j in c["judged"]:
        k, a = j["answer_kind"], (j["answer"] or "").lower()
        if k in ("duration", "duration_multi"):
            real.append("judged:" + str(j["value"]))
        elif k in ("not_a_note", "rest"):
            notreal.append("judged:" + str(j["value"]))
        elif re.search(r"\bnot a (half|quarter|eighth|note)\b", a):
            notreal.append("judged:" + a[:30])
        elif re.search(r"(half|eighth|quarter|note head|notehead)", a) and "not a" not in a:
            real.append("judged:" + a[:30])
        elif re.search(r"dynamic|part of", a):
            notreal.append("judged:" + a[:30])
    for t in c["claims"]:
        if t["kind"] == "notehead":
            real.append("claim:" + str(t["value"]))
        elif t["kind"] not in ("unmapped",):
            notreal.append("claim:" + t["kind"])
    if real and notreal:
        return "conflict", real, notreal
    if real:
        return "real", real, notreal
    if notreal:
        return "not_a_head", real, notreal
    return "unclear", real, notreal


rows = []
for c in cov:
    h = heads[c["subject"]]
    v, r, n = verdict(c)
    rows.append({"subject": c["subject"], "claimant": c["claimant"], "tier": "later" if c["claimant"] in LATER else "earlier", "share": c["share"],
                 "grp": "ge50" if c["share"] >= 0.5 else "10-50", "written": c["written"], "truth": v, "r": r, "n": n,
                 "head_only_px": h["head_only_px"], "ink": h["ink"]})
tab = collections.Counter()
for r in rows:
    tab[(r["grp"], r["tier"], r["truth"], "written" if r["written"] else "unwritten")] += 1
print("covered heads (share>=.10, judged by Sean or a judged claim tile):", len(rows))
for k in sorted(tab):
    print("  ", k, tab[k])
print("--- real (or conflicting) heads that are WRITTEN: the RIGHT ones a refusal could break")
for r in sorted(rows, key=lambda r: (r["truth"], r["claimant"])):
    if r["truth"] in ("real", "conflict") and r["written"]:
        print("   REAL+WRITTEN", r["subject"], r["claimant"], r["share"], "head-only px", r["head_only_px"], r["r"][:2], r["n"][:1])
print("--- non-heads still written")
for r in rows:
    if r["truth"] == "not_a_head" and r["written"]:
        print("   NOT-HEAD WRITTEN", r["subject"], r["claimant"], r["share"], r["n"][:2])
print("--- real heads NOT written")
for r in rows:
    if r["truth"] == "real" and not r["written"]:
        print("   REAL NOT WRITTEN", r["subject"], r["claimant"], r["share"], "head-only px", r["head_only_px"], r["r"][:2])
for X in (0.5, 0.75):
    for own in (False, True):
        brk = [r for r in rows if r["written"] and r["share"] >= X and r["truth"] in ("real", "conflict") and (not own or r["head_only_px"] == 0)]
        gain = [r for r in rows if r["written"] and r["share"] >= X and r["truth"] == "not_a_head" and (not own or r["head_only_px"] == 0)]
        print("rule: refuse written head when claimant share>=%.2f%s : would break %d real, would fix %d not-a-head (judged-covered only)" % (
            X, " and no head-only ink" if own else "", len(brk), len(gain)))
json.dump(rows, open(data / ("%s_classified.json" % plate), "w"), indent=1)
