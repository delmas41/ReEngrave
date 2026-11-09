"""2.280 r2 step 1 (the CAUSE): of the old micro test's false stems (not-note heads arm B filed a stem for) and its agreement disagreements,
how many sit on boxes 2.277 now refuses (claimed_by:*) or counts as a copy (a mark with another box)?  Reads the old micro output
(out/2.280-micro/proto_*.json, agree_disagreements.json) and the re-adjudicated records (flag ON: REC_ON, flag OFF: REC_OFF).
usage: q2_cause.py REC_ON_ROOT REC_OFF_ROOT        (each holds <plate>/verdicts.jsonl)"""
import collections
import json
import sys

ON, OFF = sys.argv[1:3]


def load(root, plate):
    head, cf = {}, {}
    for line in open("%s/%s/verdicts.jsonl" % (root, plate)):
        if '"notehead_is_not_a_notehead"' in line:
            v = json.loads(line)
            head[v["subject"]] = (v["outcome"], v["reason"])
        elif '"claim_final"' in line:
            v = json.loads(line)
            if v["quantity"] == "stroke_owner":
                c = (v.get("detail") or {}).get("claim_final") or {}
                for g, h in (c.get("held") or {}).items():
                    cf.setdefault(g, {})["held"] = (h["by"], h["share"])
                for g, m in (c.get("marks") or {}).items():
                    cf.setdefault(g, {})["mark"] = m
    return head, cf


def fate(head, cf, s):
    h = head.get(s, ("none", "none"))
    c = cf.get(s, {})
    tag = []
    if h[1].startswith("claimed_by"):
        tag.append("REFUSED " + h[1])
    if "mark" in c:
        tag.append("COPY mark=%s%s" % (c["mark"], " (this is the root)" if c["mark"] == s else ""))
    if "held" in c:
        tag.append("held %s %.2f" % c["held"])
    return h, tag


tot = collections.Counter()
for plate in ("litolff", "brahms"):
    on, off = load(ON, plate), load(OFF, plate)
    d = json.load(open("out/2.280-micro/proto_%s.json" % plate))["results"]
    print("\n=== %s: the old micro test's FALSE STEMS (not-note heads that arm B filed)" % plate)
    for s, r in d.items():
        if "notnote30" in r["groups"] and r["B"]["status"] == "filed":
            h1, t1 = fate(*on, s)
            h0, t0 = fate(*off, s)
            refused_or_copy = any(t.startswith(("REFUSED", "COPY")) for t in t1)
            tot["false_stems"] += 1
            tot["false_stems_now_refused_or_copy"] += bool(refused_or_copy)
            print("  %s label=%s dir=%s  flag-OFF: %s %s | flag-ON: %s %s" % (s, r["label"], r["B"]["direction"], h0, t0, h1, t1))
    dis = json.load(open("out/2.280-micro/agree_disagreements.json"))
    print("\n=== %s: agreement disagreements (old micro, 118 over both plates); fate of each head under 2.277" % plate)
    c = collections.Counter()
    for item in dis:
        k = item[0]
        if not k.startswith(plate + ":"):
            continue
        s = k.split(":", 1)[1]
        h1, t1 = fate(*on, s)
        kind = item[1] if item[1] == "abstain" else "disagree"
        refused_or_copy = any(t.startswith(("REFUSED", "COPY")) for t in t1)
        c[(kind, "refused/copy now" if refused_or_copy else "plain")] += 1
        tot["dis_" + kind] += 1
        tot["dis_%s_refused_or_copy" % kind] += bool(refused_or_copy)
    print("  ", dict(c))
print("\nTOTAL", dict(tot))
