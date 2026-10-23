"""ROADMAP 2.203 count (read-only): of the live `accidental_owner` verdicts
abstained `owned_by_another_staff`, how many have a GLYPH_OWNER verdict
`staff_band_no_box` (no twin on the owning staff) vs `staff_band` with a twin,
and what did the twin's own accidental_owner verdict say.
STAGED. Streams record.verdicts only (Brahms is ~9 GB).
usage: count_no_twin.py RECORD OUT.json"""
import sys, json, collections, ijson
KEEP = ("id", "subject", "quantity", "outcome", "value", "reason", "supersedes", "detail")
acc, own = {}, {}
sup = set()
boxes = {}   # accidental glyph subject -> page bbox (the ink's own box)
cells = collections.defaultdict(list)   # (page, system, staff, cell) -> accidental glyph subjects
CONTEST_IOU = 0.3   # gather.CONTEST_IOU
def iou(a, b):
    iw = min(a[2], b[2]) - max(a[0], b[0]); ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0: return 0.0
    i = iw * ih
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)
with open(sys.argv[1], "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "accidental" \
                and (o["detail"].get("bbox_page_px") or None):
            boxes[o["subject"]] = o["detail"]["bbox_page_px"]
            _, p_, s_, st_, c_, _i = o["subject"].split("/")
            cells[(p_, s_, st_, c_)].append(o["subject"])
with open(sys.argv[1], "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        q = v.get("quantity")
        if q not in ("accidental_owner", "glyph_owner"):
            continue
        r = {k: v.get(k) for k in KEEP}
        if v.get("supersedes"):
            sup.add(v["supersedes"])
        (acc if q == "accidental_owner" else own).setdefault(v["subject"], []).append(r)
def live(d, s):
    L = [r for r in d.get(s, []) if r["id"] not in sup]
    return L[-1] if L else None
C = collections.Counter(); rows = []
under = sum(1 for s in acc if live(acc, s)["reason"] == "ownership_undecided")
for s in acc:
    a = live(acc, s)
    if a["reason"] != "owned_by_another_staff":
        continue
    g = live(own, s)
    gr = g["reason"] if g else "no_glyph_owner_verdict"
    d = (g or {}).get("detail") or {}
    ostaff = (g or {}).get("value")
    twin = d.get("owner_box")
    if not twin and ostaff and s in boxes:
        _, p_, s_, st_, c_, _i = s.split("/")
        best = 0.0
        for cand in cells.get((p_, s_, ostaff.split("/")[-1], c_), []):
            v_ = iou(boxes[s], boxes[cand])
            if v_ > CONTEST_IOU and v_ > best:
                best, twin = v_, cand
    row = dict(subject=s, glyph_owner=ostaff, owner_reason=gr, twin=twin, bbox=boxes.get(s))
    C["glyph_owner_reason:" + gr] += 1
    if not twin:
        C["no_twin"] += 1; row["cat"] = "no_twin"
    elif True:
        t = live(acc, twin)
        if t is None:
            C["twin_no_accidental_verdict"] += 1; row["cat"] = "twin_no_acc_verdict"
        elif t["outcome"] == "decided":
            C["twin_decided"] += 1; row["cat"] = "twin_decided"
        else:
            C["twin_abstained"] += 1; C["twin_abstained:" + t["reason"]] += 1
            row["cat"] = "twin_abstained"; row["twin_reason"] = t["reason"]
    rows.append(row)
C["owned_by_another_staff_total"] = len(rows); C["ownership_undecided"] = under
print(json.dumps(C, indent=1, sort_keys=True))
json.dump(dict(counts=C, rows=rows), open(sys.argv[2], "w"))
