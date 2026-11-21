"""2306: replay ONE record gathered with OMR_PAGE_STEMS=1 through ADJUDICATE..INFER twice (flag 0 / 1) on THIS tree (cwd), and count
  - real heads with no stem row OFF (head_stem abstained no_stem): ON now stemmed (by reason) / still abstaining, why (the page reading's `how`);
  - heads whose stem join changed (gained / lost / other stem), and their duration OFF -> ON;
  - page 0 of Brahms: page stems (owner-stem claims) and the OFF cell stems vs Sean's labels: right / not his / missed.
Writes REC.2306-ab-<label>.json (per head changes) for the tiles. Usage: stem_ab.py REC.json LABEL [--truth FILE]"""
import sys, os, json, collections, gc
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged.review import rerun as RR

path, label = sys.argv[1], sys.argv[2]
truth = sys.argv[sys.argv.index("--truth") + 1] if "--truth" in sys.argv else None
res = load_record(path)
rec = res["record"]
obs = rec["observations"]
abst = rec["abstentions"]
pg = lambda s: int(s.split("/")[1])


def arm(on):
    os.environ["OMR_PAGE_STEMS"] = "1" if on else "0"
    r = {"observations": obs, "abstentions": abst, "verdicts": [], "format": rec.get("format")}
    log, _ = RR.rebuild_gather(r)
    RR.run_stages(log)
    j = log.to_json()
    keep = ("head_stem", "duration", "notehead_is_not_a_notehead", "stem_direction")
    out = collections.defaultdict(dict)
    for v in j["verdicts"]:
        if v["quantity"] in keep:
            out[v["quantity"]][v["subject"]] = {k: v.get(k) for k in ("outcome", "value", "reason", "detail")}
    del log, j
    gc.collect()
    return out


OFF = arm(False)
ON = arm(True)
refused = {s for s, v in OFF["notehead_is_not_a_notehead"].items() if v["outcome"] == "decided" and v["value"] is True}
twin = {s for s, v in OFF["duration"].items() if v["reason"] == "owned_by_another_staff"}
real = set(OFF["head_stem"]) - refused - twin
pstem = {}
for a in abst:
    if a["quantity"] == "page_stem":
        pstem[a["subject"]] = "abstain:" + str((a.get("detail") or {}).get("how") or (a.get("detail") or {}).get("note"))
for o in obs:
    if o["quantity"] == "page_stem":
        pstem[o["subject"]] = "read:" + str((o.get("detail") or {}).get("how"))
nost = {s for s in real if OFF["head_stem"][s]["outcome"] == "abstained" and OFF["head_stem"][s]["reason"] == "no_stem"}
now = collections.Counter()
still = collections.Counter()
for s in nost:
    v = ON["head_stem"].get(s)
    if v and v["outcome"] == "decided":
        now[v["reason"]] += 1
    else:
        still[(v and v["reason"], pstem.get(s, "no page reading"))] += 1
print("PLATE/LABEL", label, "pages", sorted({pg(s) for s in real}), "real heads", len(real))
print("no-stem heads OFF:", len(nost), "| ON have a stem:", sum(now.values()), dict(now), "| still none:", sum(still.values()))
for k, n in still.most_common():
    print("     still", n, k)


def stem_box(v):
    d = (v or {}).get("detail") or {}
    return tuple(d.get("stem_box") or ()) if v and v["outcome"] == "decided" else None


changes = []
cnt = collections.Counter()
for s in sorted(real):
    a, b = OFF["head_stem"].get(s), ON["head_stem"].get(s)
    sa, sb = stem_box(a), stem_box(b)
    if sa == sb:
        continue
    kind = "gained" if sa is None else ("lost" if sb is None else "other_stem")
    cnt[kind] += 1
    da, db = OFF["duration"].get(s), ON["duration"].get(s)
    changes.append(dict(glyph=s, kind=kind, off=a and [a["outcome"], a["reason"]], on=b and [b["outcome"], b["reason"]], on_detail=(b or {}).get("detail"),
                        off_detail=(a or {}).get("detail"), dur_off=da and [da["outcome"], da["reason"], da["value"]], dur_on=db and [db["outcome"], db["reason"], db["value"]],
                        page_reading=pstem.get(s)))
print("stem join changes on real heads:", dict(cnt))
dc = collections.Counter()
for c in changes:
    vo = c["dur_off"] and (c["dur_off"][0], json.dumps(c["dur_off"][2], sort_keys=True))
    vn = c["dur_on"] and (c["dur_on"][0], json.dumps(c["dur_on"][2], sort_keys=True))
    dc[(c["kind"], "same value" if vo == vn else "%s -> %s" % (vo and vo[0], vn and vn[0]))] += 1
print("   duration with them:", dict(dc))
allv = collections.Counter((v["outcome"], v["reason"]) for s, v in ON["head_stem"].items() if s in real)
print("ON head_stem on real heads:", allv.most_common(12))
json.dump(changes, open(path + ".2306-ab-%s.json" % label, "w"), default=str)

if truth:
    T = json.load(open(truth))
    ts = [b["rect"] for b in T["boxes"] if b["cls"] == "stem"]

    def hit(t, b):
        tx, bx = (t[0] + t[2]) / 2.0, (b[0] + b[2]) / 2.0
        ov = min(t[3], b[3]) - max(t[1], b[1])
        return abs(tx - bx) <= 8 and ov >= 0.5 * min(t[3] - t[1], b[3] - b[1])
    mine = [o["detail"]["stem_box"] for o in obs if o["quantity"] == "claimed_area" and pg(o["subject"]) == 0
            and (o.get("detail") or {}).get("owner") == "stem" and o["value"] != "census"]
    found = sum(1 for t in ts if any(hit(t, b) for b in mine))
    right = sum(1 for b in mine if any(hit(t, b) for t in ts))
    print("Brahms p0 page stems vs Sean's %d labels: right %d, not his %d, his missed %d" % (len(ts), right, len(mine) - right, len(ts) - found))
