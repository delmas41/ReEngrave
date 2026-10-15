"""2.120 round 2 (c): detector boxes of Brahms p0 (record 20261013-night) through the table, against Sean's truth.
python3 measure2/detector.py > measure2/detector.out ; needs measure2/brahms_p0.pkl (extract_record.py) + truth2_rows.json"""
import json, sys, pickle, collections, statistics
sys.path.insert(0, ".")
import table as T1, table2 as T2, descriptors as D1, descriptors2 as D
REPO = "/Users/seanjohnson/Desktop/ReEngrave"
P = pickle.load(open("measure2/brahms_p0.pkl", "rb"))
page = json.load(open(REPO + "/data/hand-truth/pages/imslp317803/0.json"))
OV = {k: v for k, v in json.load(open("truth_overrides.json")).items() if not k.startswith("_")}
T = [dict(id=b["id"], cls=OV[b["id"]]["now"] if b["id"] in OV else b["cls"], rect=b["rect"]) for b in page["boxes"]]
for t in T: t["sym"] = T1.symbol_of(t["cls"])
g = D1.page_gray(P["pdf"], 0); m = D1.StaffModel(page)
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i) if i > 0 else 0.0
# bucket truth for speed
import bisect
def best_truth(box):
    best, bi = 0.0, None
    for t in T:
        r = t["rect"]
        if r[2] < box[0] or r[0] > box[2] or r[3] < box[1] or r[1] > box[3]: continue
        v = iou(box, r)
        if v > best: best, bi = v, t
    return best, bi
S2 = T2.SYMBOLS
rows = []
for x in P["rows"]:
    b = x["box_page"]
    d = D.describe(b, g, m)
    c2, _ = T2.candidates(d); c1, _ = T1.candidates(d)
    iu, t = best_truth(b)
    rows.append(dict(key=x["key"], cls=x["cls"], dsym=T1.symbol_of(x["cls"]), score=x["score"], status=x["status"], refusal=x["refusal"],
                     iou=iu, tid=t["id"] if t else None, tsym=t["sym"] if t else None, tcls=t["cls"] if t else None,
                     all2=sorted(c2["all"]), common2=sorted(c2["common"]), all1=sorted(c1["all"]), d=d))
json.dump(rows, open("measure2/detector_rows.json", "w"))
n = len(rows)
print("detector boxes on p0:", n, "| status", dict(collections.Counter(r["status"] for r in rows)))
print("detector classes outside the table (symbol None):", collections.Counter(r["cls"] for r in rows if r["dsym"] is None).most_common(8))
strong = [r for r in rows if r["iou"] >= 0.5]; weak = [r for r in rows if 0.0 < r["iou"] < 0.5]; none = [r for r in rows if r["iou"] == 0.0]
print("\nIoU vs Sean's truth: strong >=0.5: %d | partial 0<IoU<0.5: %d | no truth overlap: %d" % (len(strong), len(weak), len(none)))
def rep(label, rs, key="all2"):
    inn = [r for r in rs if r["dsym"] in r[key]]
    return "%-34s n%4d" % (label, len(rs))
for key, nm in (("all1", "ROUND-1 table"), ("all2", "ROUND-2 table")):
    print("\n==== %s ====" % nm)
    sx = [r for r in strong if r["dsym"] is not None and r["tsym"] is not None]
    wrong = [r for r in sx if r["dsym"] != r["tsym"]]; right = [r for r in sx if r["dsym"] == r["tsym"]]
    print("strong-matched with a table symbol on both sides: %d | detector class == truth: %d | detector class != truth (errors): %d" % (len(sx), len(right), len(wrong)))
    caught = [r for r in wrong if r["dsym"] not in r[key]]
    print(" ERRORS CAUGHT (detector's class eliminated by the table): %d / %d (%.0f%%); and the true symbol survives in the set: %d of those" % (
        len(caught), len(wrong), 100 * len(caught) / max(1, len(wrong)), sum(r["tsym"] in r[key] for r in caught)))
    print(" by (detector -> truth), errors:", collections.Counter((r["dsym"], r["tsym"]) for r in wrong).most_common(12))
    print(" by (detector -> truth), CAUGHT:", collections.Counter((r["dsym"], r["tsym"]) for r in caught).most_common(12))
    harm = [r for r in right if r["dsym"] not in r[key]]
    print(" CORRECT detections the table would ELIMINATE (harm): %d / %d" % (len(harm), len(right)), collections.Counter(r["dsym"] for r in harm).most_common(8))
    print("   truth symbol absent from the set on detector boxes (strong): %d / %d" % (sum(r["tsym"] not in r[key] for r in sx), len(sx)))
    fa = [r for r in none if r["dsym"] is not None]
    fa_c = [r for r in fa if r["dsym"] not in r[key]]
    print(" FALSE ALARMS (no truth overlap) with a table class: %d | eliminated by the table: %d (%.0f%%)" % (len(fa), len(fa_c), 100 * len(fa_c) / max(1, len(fa))))
    print("   false alarms by class (n, eliminated):", sorted(((c, sum(1 for r in fa if r["cls"] == c), sum(1 for r in fa_c if r["cls"] == c)) for c in set(r["cls"] for r in fa)), key=lambda z: -z[1])[:12])
    wk = [r for r in weak if r["dsym"] is not None]
    print(" PARTIAL overlap boxes (0<IoU<0.5): %d | class == overlapping truth: %d | eliminated: %d" % (len(wk), sum(r["dsym"] == r["tsym"] for r in wk), sum(r["dsym"] not in r[key] for r in wk)))
# refused
print("\n==== REFUSED boxes (adjudicate status 'refused') under the ROUND-2 table ====")
rf = [r for r in rows if r["status"] == "refused"]
print("refused total", len(rf), "| matched truth strong:", sum(r["iou"] >= 0.5 for r in rf), "| partial:", sum(0 < r["iou"] < 0.5 for r in rf), "| none:", sum(r["iou"] == 0 for r in rf))
by = collections.defaultdict(list)
for r in rf: by[r["refusal"][0] + " / " + r["refusal"][1]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    st = [r for r in v if r["iou"] >= 0.5]
    tr = collections.Counter(r["tsym"] for r in st)
    surv = [r for r in st if r["tsym"] in r["all2"] and r["tsym"] is not None]
    small = [r for r in surv if len(r["all2"]) <= 3]
    print("%-52s n%3d | truth strong %2d: %s | true symbol in set %d | set<=3: %d | no-truth %d" % (k, len(v), len(st), dict(tr.most_common(5)), len(surv), len(small), sum(r["iou"] == 0 for r in v)))
print("\nrefused with strong truth: is the refusal RIGHT (truth is not what the family refuses) and can the table name what it is?")
for r in rf:
    if r["iou"] >= 0.5 and r["refusal"][1] in ("too_narrow", "stacked_head_duplicate", "clipped_fragment", "head_cut_piece", "is_a_beam_piece", "is_a_time_signature_digit", "tremolo_slash_crosses_stem", "notehead_is_a_duplicate_box"):
        print("  %-14s %-26s det %-20s truth %-18s(%s) set %s" % (r["key"][6:], r["refusal"][1], r["cls"], r["tcls"], r["tid"], "/".join(r["all2"])))
