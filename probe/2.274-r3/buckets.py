"""2.274 r3: the FIRST stage that goes wrong, for each of the 109 printed arcs (153 hand boxes) of Brahms p0, flag OFF and flag ON.
    python3 buckets.py [census3.json]   -> buckets.json + the table.   Reads census3.json (audit.py) -- changes no pipeline code.

Order of tests (the first that fails names the bucket; each test is a measurement on the record or the file, none is our own opinion of the arc):
   RIGHT  strict scorer (truth_p0: both ends within 2.5 sp, same staff, kind) OR the audited scorer (audit.py: open ends at a cell edge, same mark counted once, match by place)
   7  scorer / truth: the printed arc is not a scorable mark:  ghost (hand box over no arc ink: no run, every detector box refused), chain (a group of separate arcs joined by the scorer, > 35 sp),
      half (the file DOES hold an arc over it that fits it except for an end past an OPEN cell edge, already counted for its other half), cross-system arc (scorer drops it; the join needs page 1)
   8  head not written: the hand notehead at an end is not in the file (the bar's duration unread: no `<note>`), so no arc can attach
   1  never boxed: no detector arc box covers it (box_cov < 0.15)
   2  boxed in part: boxes cover < 0.8 and no whole run witnessed it
   3  page-ink run missing / short / over-merged (a run that reaches >= 3 sp past an end into the next arc)
   4  run whole, not witnessed
   5  witnessed and whole, but binder abstained or bound an end to the wrong note (reason named)
   6  bound right, lost or changed later (export)
OFF has no page-ink stages: 3 and 4 do not exist there; the detector box is the only source.
"""
import collections
import json
import sys
from load import *   # noqa

C = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "census3.json"))
rec = record("on")
gb = {}
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/"):
        b = o["detail"]["bbox_page_px"]
        gb[o["subject"]] = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


import audit_spans as AS  # noqa
ON_SPANS = AS.spans('on')
_roff = record('off')
gbx = {o['subject']: (o['detail']['bbox_page_px'][0] + o['detail']['bbox_page_px'][2]) / 2 for o in _roff['observations'] if o['quantity'] == 'glyph_box' and o['subject'].startswith('glyph/0/')}
SYSARC = {o['subject']: o['detail'] for o in _roff['observations'] if o['quantity'] == 'system_arc' and o['subject'].startswith('glyph/0/')}
MK, _H, _PA = marks()
MEM = {}
for m in MK:
    for i in m["members"]:
        MEM[i] = (m["members"], m["rel"])


def right(c, arm):
    return c["strict_" + arm] == "right" or c["aud_" + arm] == "right"


def classify(c, arm):
    if right(c, arm):
        return "right", ""
    e = c["bind"][0] if c["bind"] else None
    heads_missing = [s for s, h in c["heads"].items() if h.get("hand_head") and not h.get("written_" + arm)]
    # reach of the best run past the printed arc's CLOSED ends only (past an OPEN cell edge the printed arc continues: the other half was never boxed, that is not a merge)
    past = 0.0
    for r in c["runs"][:1]:
        pl = 0.0 if c["open_L"] else (c["x0"] - r["run_x0"]) / SP
        pr = 0.0 if c["open_R"] else (r["run_x1"] - c["x1"]) / SP
        past = max(pl, pr, 0.0)
    # ---- 7: the printed arc is not a scorable mark
    if c["ghost"]:
        return "7", "ghost: hand box over no arc ink (no run, every detector box refused)"
    if c["chain"] and not right(c, "on") and not right(c, "off"):
        return "7", "chain: separate arcs joined by the scorer's grouping (%.0f sp)" % c["width_sp"]
    # a second label over the same printed mark, whose partner is already counted right
    mem, rel = MEM[c["n"]]
    if len(mem) > 1 and any(right(C[k], arm) for k in mem if k != c["n"]):
        return "7", "%s label: the same printed mark is already counted right through P%s" % ("/".join(rel), [k for k in mem if k != c["n"]])
    # ---- 8 before the arc stages: no head, no arc can attach
    if heads_missing:
        return "8", "hand notehead at %s end not in the file (bar not written)" % "/".join(heads_missing)
    if e and e["status"] == "abstained" and e["why"] == "system_edge":
        return "7", "cross-system arc (binder: system_edge; scorer skips arcs across systems; needs page 1)"
    # ---- GATHER: boxes (OFF right means a detector box existed)
    if c["box_cov"] < 0.15 and not (arm == "on" and right(c, "off")):
        return "1", "no detector arc box covers it"
    whole_run = c["run_cov"] >= 0.8
    if arm == "off":
        if c["box_cov_kept"] < 0.8 and c["curve_cov"] < 0.8:
            return "2", "boxes cover %.2f (kept %.2f), join curve %.2f" % (c["box_cov"], c["box_cov_kept"], c["curve_cov"])
        # the old path: detector boxes -> `system_arc` curve (join_traces) -> anchors (the notes the curve binds to) -> export.  Anchors on both printed ends: lost later (6); else the curve/anchor is the loss (5)
        best = []
        for sub, val in c["curves"]:
            d = SYSARC.get(sub)
            if not d:
                continue
            al, ar = d.get("anchor_left"), d.get("anchor_right")
            okl = al in gbx and abs(gbx[al] - c["x0"]) / SP <= REACH
            okr = ar in gbx and abs(gbx[ar] - c["x1"]) / SP <= REACH
            best.append((val, okl, okr))
        if any(l and r for _, l, r in best):
            return "6", "old path: the join curve is anchored on both printed ends and the arc is not in the file (export)"
        return "5", "old path: no join curve anchored on both printed ends (%s)" % ("/".join(sorted({v for v, _, _ in best})) or "no curve")
    if c["box_cov"] < 0.8 and not whole_run and not right(c, "off"):
        return "2", "boxes cover %.2f, no whole run" % c["box_cov"]
    # ---- GATHER: page-ink run
    if not c["runs"]:
        return "3", "no page-ink run on it"
    if not whole_run:
        return "3", "best run covers %.2f of it" % c["run_cov"]
    ents = c["bind"]
    if not ents:
        return "4", "run whole, no binding entry"
    # an entry written with both ends on this arc's notes (an end past an OPEN cell edge may lie further out)
    def fit(e):
        a, b = e.get("start"), e.get("stop")
        if a not in gb or b not in gb:
            return None
        dl, dr = (gb[a][0] - c["x0"]) / SP, (gb[b][0] - c["x1"]) / SP
        okl = abs(dl) <= REACH or (c["open_L"] and dl < 0)
        okr = abs(dr) <= REACH or (c["open_R"] and dr > 0)
        return (okl and okr), dl, dr

    def present(e):
        for w in ON_SPANS:
            if w["same"] and w["staff"] == "/".join(e["start"].split("/")[2:4]) and abs(w["cl"] - gb[e["start"]][0]) <= 35 and abs(w["cr"] - gb[e["stop"]][0]) <= 35:
                return True
        return False
    written = [e for e in ents if e["status"] == "written"]
    good = [e for e in written if fit(e) and fit(e)[0]]
    if good:
        e = good[0]
        if present(e):
            return "7", "the file holds this arc (run %d, %s -> %s) but the scorer did not credit it (a stacked / duplicate label took the one written arc)" % (e["ordinal"], e["start"].split("/", 2)[2], e["stop"].split("/", 2)[2])
        return "6", "bound right (run %d, %s -> %s) and NOT in the file (export)" % (e["ordinal"], e["start"].split("/", 2)[2], e["stop"].split("/", 2)[2])
    if past >= 3.0:
        return "3", "run over-merged: it reaches %.1f sp past a closed end into the next arc" % past
    if written:
        e = written[0]
        f = fit(e)
        return "5", "binder bound an end to the wrong note (run %d: start %+.1f sp, stop %+.1f sp from the printed ends)" % (e["ordinal"], f[1], f[2]) if f else "binder wrote it, head box unknown"
    if any(e["status"] == "not_witnessed" for e in ents):
        return "4", "run whole, not witnessed"
    e = ents[0]
    return "5", "binder abstained: %s" % e["why"]


out = []
for arm in ("off", "on"):
    cnt = collections.Counter()
    boxes = collections.Counter()
    for c in C:
        b, why = classify(c, arm)
        c["bucket_" + arm], c["why_" + arm] = b, why
        cnt[b] += 1
        boxes[b] += c["hand_boxes"]
    print(arm.upper(), "printed arcs:", dict(sorted(cnt.items())), "| hand boxes:", dict(sorted(boxes.items())))
json.dump(C, open("buckets.json", "w"), indent=1, default=str)
for c in C:
    if c["bucket_on"] != "right" or c["bucket_off"] != "right":
        print("P%-3d %-5s %-4s %4.1fsp  OFF %-2s  ON %-2s  ON: %s" % (c["n"], c["staff"], c["kind"], c["width_sp"], c["bucket_off"], c["bucket_on"], c["why_on"][:110]))
