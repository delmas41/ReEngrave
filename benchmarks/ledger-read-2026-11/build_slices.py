"""2.255: the ON arm's record -- the 20261029-night slices with GATHER's far-head ledger rows replaced by the re-read with
OMR_LEDGER_READ on, ONLY where the flag-off re-read reproduces the record (the control) and the flag changes the reading.
Rows replaced: the own `far_head_ledger_position` row and the own-candidate `far_head_owner_ledger` row.
usage: build_slices.py OUT_DIR PLATE BASE.json ON.json [PLATE BASE ON ...]"""
import json
import os
import shutil
import sys

from tools.omr.staged import lane_report as LR

out = sys.argv[1]
args = sys.argv[2:]
for i in range(0, len(args), 3):
    plate, bj, oj = args[i:i + 3]
    A = json.load(open(bj))["heads"]
    B = json.load(open(oj))["heads"]
    change = {s: B[s] for s in A if A[s]["same"] and A[s]["got"] != B[s]["got"]}
    # the neighbour-candidate owner rows the flag changes (OWNER=1 re-reads): replaced only where the record's row for
    # that candidate is an abstention and the flag now reads a position
    nbch = {s: B[s]["nb"] for s in A if A[s].get("nb") and B[s].get("nb") and A[s]["nb"] != B[s]["nb"]
            and B[s]["nb"][1] is not None and A[s]["nb"][1] is None}
    src = LR.slice_dir(plate, "20261029-night")
    dst = os.path.join(out, plate)
    os.makedirs(dst, exist_ok=True)
    shutil.copy(src / "stamp.json", os.path.join(dst, "stamp.json"))
    shutil.copy(src / "verdicts.jsonl", os.path.join(dst, "verdicts.jsonl"))
    geo = {}
    obs_out = open(os.path.join(dst, "observations.jsonl"), "w")
    abs_out = open(os.path.join(dst, "abstentions.jsonl"), "w")
    n_rm = n_add = 0

    def own(s):
        p = s.split("/")
        return "staff/%s/%s/%s" % (p[1], p[2], p[3])

    template = {}
    for kind, fh in (("observations", obs_out), ("abstentions", abs_out)):
        for l in open(src / ("%s.jsonl" % kind)):
            r = json.loads(l)
            s, q = r.get("subject"), r.get("quantity")
            if s in change and (q == "far_head_ledger_position"
                                or (q == "far_head_owner_ledger" and (r.get("detail") or {}).get("candidate") == own(s))):
                template[(s, q)] = r
                n_rm += 1
                continue
            if (s in nbch and kind == "abstentions" and q == "far_head_owner_ledger"
                    and (r.get("detail") or {}).get("candidate") == nbch[s][0]):
                d = dict(r.get("detail") or {}, ledger_reason=nbch[s][2], read_by="2.255 OMR_LEDGER_READ re-read")
                obs_out.write(json.dumps(dict(id=r["id"].replace("abs:", "obs:") + "r", subject=s, quantity=q,
                                              value=int(nbch[s][1]), reader=r["reader"], frame=r["frame"], score=None,
                                              detail=d, basis=[])) + "\n")
                n_rm += 1
                n_add += 1
                print("   neighbour row", s, nbch[s])
                continue
            fh.write(l)
    for s, v in change.items():
        got = v["got"]
        for q in ("far_head_ledger_position", "far_head_owner_ledger"):
            t = template.get((s, q))
            if t is None:
                continue
            d = dict(t.get("detail") or {})
            d["ledger_reason"] = got[2]
            d["read_by"] = "2.255 OMR_LEDGER_READ re-read"
            if got[0] == "pos":
                row = dict(id=t["id"].replace("abs:", "obs:") + "r", subject=s, quantity=q, value=int(got[1]),
                           reader=t["reader"], frame=t["frame"], score=None, detail=d, basis=[])
                obs_out.write(json.dumps(row) + "\n")
            else:
                row = dict(id=t["id"].replace("obs:", "abs:") + "r", subject=s, quantity=q, reader=t["reader"],
                           frame=t["frame"], reason="ledger_not_read", detail=d)
                abs_out.write(json.dumps(row) + "\n")
            n_add += 1
    obs_out.close()
    abs_out.close()
    print(plate, "changed subjects", len(change), "rows removed", n_rm, "added", n_add, sorted(change))
