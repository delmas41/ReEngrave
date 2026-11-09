"""2.278: automatic sub-bucketing of narrowed heads from the verdict's own detail. usage: buckets.py DIAG.jsonl"""
import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
N = [r for r in R if r["fate"] == "duration_narrowed"]


def bucket(r):
    d = r.get("d", {}); reason = r.get("reason")
    bfs = r.get("bfs") or {}
    lc, lp = d.get("levels_certain"), d.get("levels_possible")
    st = d.get("stems_attached")
    sig = []
    if reason == "beams_ambiguous":
        sig.append("certain=%s possible=%s" % (lc, lp))
        sig.append("stems=%s" % st)
        sig.append("bfs=%s" % bfs.get("settled"))
        sig.append("cv=%s yolo=%s kept=%s" % (d.get("cv_beams"), d.get("yolo_beams"), d.get("yolo_kept")))
    elif reason == "beam_discounted_uncertain":
        sig.append("stems=%s" % st)
        sig.append("notbyink=%s" % d.get("beams_not_by_ink"))
        sig.append("far=%s nb=%s arc=%s beyond=%s ledger=%s" % (d.get("beams_far_side"), d.get("beams_neighbour_staff"), d.get("beams_decided_arc"), d.get("beams_beyond_stem"), d.get("beams_ledger_line")))
        sig.append("cv=%s yolo=%s kept=%s" % (d.get("cv_beams"), d.get("yolo_beams"), d.get("yolo_kept")))
        sig.append("evid_holds=%s" % d.get("bare_stem_evidence_holds"))
    return reason + " | " + " ; ".join(sig)


c = collections.Counter(bucket(r) for r in N)
for k, v in c.most_common(60): print(v, k)
print()
print(collections.Counter(r["reason"] for r in N))
