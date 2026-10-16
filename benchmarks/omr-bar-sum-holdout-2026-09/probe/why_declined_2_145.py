"""2.145 -- why the gate declined a head the 2.99 windows read as a rest.
usage: why_declined_2_145.py RECORD "p,s;..." HEAD_SUBJECT [...]
Replays the systems with the flag ON and, for each head, reports which test of `head_rest_shape.read_head_ink` returned None."""
import os
import sys

import ijson

sys.path.insert(0, ".")
P, SYS, HEADS = sys.argv[1], sys.argv[2], sys.argv[3:]
keep = {tuple(int(x) for x in t.split(",")) for t in SYS.split(";") if t}


def want(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return (int(p[1]), int(p[2])) in keep
    return True


rec = {"observations": [], "abstentions": []}
with open(P, "rb") as f:
    for k in rec:
        f.seek(0)
        for it in ijson.items(f, "record.%s.item" % k, use_float=True):
            if want(it["subject"]):
                rec[k].append(it)
os.environ["OMR_HEAD_INK_IS_A_REST"] = "1"
from tools.omr.staged.adjudicators import head_rest_shape as H  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

events = []
orig_touch, orig_cover = H._geom.stem_touches_head, H._cover


def touch(s, h):
    r = orig_touch(s, h)
    if r:
        events.append(("stem_touches", tuple(round(x) for x in h), tuple(round(x) for x in s)))
    return r


H._geom.stem_touches_head = touch


def cover(a, b):
    r = orig_cover(a, b)
    events.append(("cover", tuple(round(x) for x in a), tuple(round(x) for x in b), round(r, 2)))
    return r


H._cover = cover
orig_read = H.read_head_ink


def read(ev, cell, head_row, clusters):
    events.clear()
    r = orig_read(ev, cell, head_row, clusters)
    if head_row.subject.to_key() in HEADS:
        for c in clusters:
            d = c.detail or {}
            print("   cluster", c.subject.to_key(), d.get("covered_by"), d.get("coverage"), d.get("bbox_canonical"))
        print("   head", head_row.value)
        print(head_row.subject.to_key(), "->", None if r is None else (r.value, r.displaced), list(events))
    return r


H.read_head_ink = read
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
