"""2.97: are the settled heads CLEAN? For every bar the arm settled, per head:
 owner   : this staff's own (glyph_owner decided == own) / unread / ANOTHER staff
 dup     : its page box overlaps (IoU > 0.3) another kept glyph box of the bar
 stem    : unused here
   python3 clean_2_97.py ARM.pkl OUT.json
A bar is DIRTY if any settled head is another staff's, has a duplicate box,
or is not on this staff's own lines (centre outside staff +-1.5 spaces)."""
import collections
import json
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Outcome, Q  # noqa: E402


def part_of(v):
    if v.decider == "reconcile_duration":
        if (v.detail or {}).get("chord_of"):
            return "chord"
        if (v.detail or {}).get("settled_alongside"):
            return "single"
        return None
    if v.decider == "infer:collapse_narrowed_by_bar":
        return "columns" if (v.detail or {}).get("bar_unknown_events", 1) >= 2 else "single"
    return None


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0


def box_of(log, sub):
    r = log.rows(Q.GLYPH_BOX, sub)
    return [float(x) for x in (r[-1].detail or {}).get("bbox_page_px")] if r and (r[-1].detail or {}).get("bbox_page_px") else None


log = pickle.load(open(sys.argv[1], "rb"))
bars = collections.defaultdict(list)
for v in list(log._vrd.values()):
    cur = log.verdict(Q.DURATION, v.subject)
    if cur is None or cur.id != v.id or v.outcome is not Outcome.DECIDED:
        continue
    p = part_of(v)
    if p:
        s = v.subject
        bars[(s.page, s.system, s.staff, s.cell)].append((p, s, v))
res = {}
tally = collections.Counter()
for key, hs in bars.items():
    cell = R.cell(*key)
    kept = []
    for q in C._standing(log, cell, Q.DURATION):
        if C._left_the_bar(log, q.subject) is None and not C._is_rest(q):
            b = box_of(log, q.subject)
            if b:
                kept.append((q.subject, b))
    lines = log.rows(Q.STAFF_LINES, R.staff(*key[:3]))
    ln = lines[-1].value if lines else None
    why = []
    for p, s, v in hs:
        ow = log.verdict(Q.GLYPH_OWNER, s)
        if ow is None or ow.outcome is not Outcome.DECIDED:
            o = "unread"
        else:
            o = "own" if (ow.value == key[2] or str(ow.value).endswith("/%d" % key[2]) or (isinstance(ow.value, dict) and ow.value.get("staff") == key[2])) else "other:%s" % (ow.value,)
        b = box_of(log, s)
        dup = bool(b) and any(oth != s and iou(b, ob) > 0.3 for oth, ob in kept)
        off = False
        if b and ln:
            sp = (ln[-1] - ln[0]) / 4.0
            cy = (b[1] + b[3]) / 2
            off = cy < ln[0] - 1.6 * sp or cy > ln[-1] + 1.6 * sp
        xdup = False
        if b:
            for r in log.rows(Q.GLYPH_BOX, R.system(key[0], key[1]), scope=R.Scope.SELF_AND_DESCENDANTS):
                if r.subject.staff == key[2] or r.subject == s:
                    continue
                ob = (r.detail or {}).get("bbox_page_px")
                if ob and iou(b, [float(x) for x in ob]) > 0.3 and \
                        C._left_the_bar(log, r.subject) is None:
                    xdup = True
                    break
        if xdup:
            why.append("other_staff_box_on_same_ink")
        if o.startswith("other"):
            why.append("owner_other")
        if dup:
            why.append("duplicate_box")
        if off:
            why.append("off_staff")
        tally[("owner", o.split(":")[0])] += 1
    res["/".join(map(str, key))] = {"part": hs[0][0], "dirty": sorted(set(why))}
    for w in set(why):
        tally[("dirty", hs[0][0], w)] += 1
    tally[("bars", hs[0][0])] += 1
    if why:
        tally[("dirty_bars", hs[0][0])] += 1
for k, v in sorted(tally.items(), key=str):
    print(k, v)
json.dump(res, open(sys.argv[2], "w"), indent=1)
