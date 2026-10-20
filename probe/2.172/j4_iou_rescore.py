"""2.172 step 2: re-score Sean's judged RESTS by BOX OVERLAP, not glyph key. The tiles whose key-scored status differs between the OFF and an ON record (j1) are the
only ones that can differ (key scoring is unchanged elsewhere). Subject box = the OFF record's box for the judged subject (glyph box, or the CV unboxed-rest box);
in each arm the evidence is every glyph whose box overlaps it (IoU > 0.3) and carries a decided duration; right = one of them is a rest of Sean's value, wrong = they
carry something else (a note, another rest value), not_found = none.
usage: j4_iou_rescore.py PLATE ARM [ARM...]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
pl, arms = sys.argv[1], sys.argv[2:]


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def same(a, b):
    """IoU > 0.3, or either box's centre inside the other (a small box inside a rest-sized box is the same ink)."""
    if iou(a, b) > 0.3:
        return True
    ca, cb = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    return (b[0] <= ca[0] <= b[2] and b[1] <= ca[1] <= b[3]) or (a[0] <= cb[0] <= a[2] and a[1] <= cb[1] <= a[3])


BEATS = {"4 rest": 1.0, "8 rest": 0.5}
off_t = json.load(open(ROOT / ("probe/2.172/data/judged_%s_off.json" % pl)))["tiles"]
off_t = {(t["item"], t["tile"]): t for t in (off_t.values() if isinstance(off_t, dict) else off_t)}
recs = {a: json.loads(open(ROOT / ("rec172/%s-%s.record.json" % (pl, a))).read())["record"] for a in ["off"] + arms}


def boxes_and_dur(R):
    box, dur = {}, {}
    for o in R["observations"]:
        det = o.get("detail") or {}
        b = det.get("bbox_page_px") or det.get("bbox")
        if o["subject"].startswith("glyph/") and b and o["quantity"] in ("glyph_box", "unboxed_rest_shape"):
            box[o["subject"]] = b
    for v in R["verdicts"]:
        if v.get("quantity") == "duration" and v.get("outcome") == "decided" and isinstance(v.get("value"), dict):
            dur[v["subject"]] = v["value"]
    return box, dur


bd = {a: boxes_and_dur(R) for a, R in recs.items()}
for arm in arms:
    changed = []
    on_t = json.load(open(ROOT / ("probe/2.172/data/judged_%s_%s.json" % (pl, arm))))["tiles"]
    on_t = on_t.values() if isinstance(on_t, dict) else on_t
    for t in on_t:
        o = off_t.get((t["item"], t["tile"]))
        if o and o["status"] != t["status"]:
            changed.append((t, o))
    print("==", pl, arm, "key-scored changes:", len(changed))
    for t, o in changed:
        sub = t["subject"]
        ans = str(t["answer"]).strip()
        want = BEATS.get(ans)
        row = []
        for a in ["off", arm]:
            box, dur = bd[a]
            sb = bd["off"][0].get(sub)
            if sb is None:
                row.append("no subject box")
                continue
            ev = [(g, dur[g]) for g, b in box.items() if g in dur and same(sb, b)]
            right = [g for g, v in ev if v.get("is_rest") and want is not None and abs(v.get("beats", -1) - want) < 1e-6]
            if right:
                row.append("right (%s)" % right[0].split("/")[-1])
            elif ev:
                row.append("wrong " + str([(g.split("/")[-1], v.get("beats"), v.get("is_rest")) for g, v in ev][:3]))
            else:
                row.append("not_found")
        print("  ", t["item"], t["tile"], sub, "| Sean:", ans, "| key:", o["status"], "->", t["status"], "| by overlap OFF:", row[0], "| ON:", row[1])
