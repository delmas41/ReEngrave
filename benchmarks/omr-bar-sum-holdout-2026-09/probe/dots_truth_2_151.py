"""ROADMAP 2.151 -- score every augmentation dot and every dotted head of Sean's hand-truth page (Brahms 317803 pdf 0)
against a SMALL record (STAGED; re-decided from the record's own GATHER rows, through INFER), one arm per call.

Per truth dot: was it boxed (a `Q.AUG_DOT` glyph whose page box overlaps it), its live `Q.DOT_ROLE`, and the head it names.
Per truth head carrying a dot (the nearest truth head/rest to the dot's left): our head's live `Q.DURATION` --
dotted / PLAIN (decided with no dot: silent) / narrowed with or without a dotted candidate / abstained / no head.
Control: truth heads with NO dot whose duration is decided dotted (a false dot).
usage: dots_truth_2_151.py RECORD.json OUT.json [ENV=VAL ...]   (env applies to the replay)"""
import collections, json, os, sys
sys.path.insert(0, ".")
REC, OUT = sys.argv[1], sys.argv[2]
for kv in sys.argv[3:]:
    k, v = kv.split("=", 1)
    os.environ[k] = v
PAGE = 0
HT = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
SP = 32.0


def R(b):
    x0, y0, x1, y1 = b["rect"]
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


T = [dict(id=b["id"], cls=b["cls"], r=R(b)) for b in HT["boxes"]]
tdots = [t for t in T if t["cls"] == "augmentationDot"]
theads = [t for t in T if t["cls"].startswith("notehead") or t["cls"].startswith("rest")]


def ov(a, b, pad=0.0):
    return min(a[2], b[2]) + pad > max(a[0], b[0]) and min(a[3], b[3]) + pad > max(a[1], b[1])


def owner(d):
    dr = d["r"]
    dcy = (dr[1] + dr[3]) / 2
    best, bs = None, 1e9
    for h in theads:
        hr = h["r"]
        gap = (dr[0] - hr[2]) / SP
        dy = (dcy - (hr[1] + hr[3]) / 2) / SP
        if -0.3 <= gap <= 2.5 and abs(dy) <= 1.0:
            s = gap + 2 * abs(dy)
            if s < bs:
                bs, best = s, h
    return best


rec = json.load(open(REC))
rec = rec.get("record", rec)
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

log, _ = RR.rebuild_gather(rec)
del rec
RR.run_stages(log)
d = log.to_json()
boxes, cls, all_boxes = {}, {}, {}
for o in d["observations"]:
    if o["quantity"] == Q.GLYPH_BOX and (o.get("detail") or {}).get("bbox_page_px"):
        all_boxes[o["subject"]] = o["detail"]["bbox_page_px"]
    if o["quantity"] == Q.GLYPH_BOX and o["subject"].startswith("glyph/%d/" % PAGE):
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb:
            boxes[o["subject"]] = bb
            cls[o["subject"]] = o["value"][0] if isinstance(o["value"], list) else None
dotsubs = {o["subject"] for o in d["observations"]
           if o["quantity"] == Q.AUG_DOT and o["subject"].startswith("glyph/%d/" % PAGE)}
sup = {v["supersedes"] for v in d["verdicts"] if v.get("supersedes")}
live = {}
for v in d["verdicts"]:
    if v["id"] in sup:
        continue
    live[(v["subject"], v["quantity"])] = v
headsubs = [s for s, c in cls.items() if c and (c.startswith("notehead") or c.startswith("rest"))]


def ours(tr):
    best, ba = None, 0
    for s in headsubs:
        b = boxes[s]
        a = max(0, min(b[2], tr[2]) - max(b[0], tr[0])) * max(0, min(b[3], tr[3]) - max(b[1], tr[1]))
        if a > ba:
            ba, best = a, s
    return best


def dur_kind(s):
    if s is None:
        return "no_head_box"
    v = live.get((s, Q.DURATION))
    if v is None:
        return "no_duration_verdict"
    if v["outcome"] == "decided":
        n = (v["value"] or {}).get("dots", 0) if isinstance(v["value"], dict) else 0
        return "decided_dotted" if n else "decided_PLAIN"
    if v["outcome"] == "narrowed":
        has = any(isinstance(c.get("value"), dict) and c["value"].get("dots") for c in v.get("candidates") or [])
        return "narrowed_with_dotted" if has else "narrowed_no_dotted"
    return "abstained:" + str(v["reason"])


rows, c_dot, c_head = [], collections.Counter(), collections.Counter()
dotted_heads = {}
for t in tdots:
    mine = [s for s in dotsubs if s in boxes and ov(boxes[s], t["r"], 0.2 * SP)]
    o = owner(t)
    oh = ours(o["r"]) if o else None
    if o:
        dotted_heads.setdefault(o["id"], (o, oh, []))[2].append(t["id"])
    roles = []
    if not mine:
        kind = "not_boxed"
    else:
        rv = [live.get((s, Q.DOT_ROLE)) for s in mine]
        roles = ["%s:%s" % (r["outcome"], r["value"] if r["outcome"] == "decided" else r["reason"]) if r else "no_role"
                 for r in rv]
        named = [(r.get("detail") or {}).get("head") for r in rv if r]
        if any(x == "decided:augmentation" for x in roles):
            kind = "augmentation_on_right_head" if oh and oh in named else "augmentation_other_head"
        else:
            kind = roles[0]
    c_dot[kind] += 1
    rows.append(dict(truth=t["id"], rect=t["r"], ours=mine, roles=roles, kind=kind, owner=o and o["id"],
                     owner_cls=o and o["cls"], our_head=oh, head_duration=dur_kind(oh)))
for hid, (o, oh, ds) in dotted_heads.items():
    c_head[dur_kind(oh)] += 1
false_dot = collections.Counter()
false_rows = []
for h in theads:
    if h["id"] in dotted_heads:
        continue
    s = ours(h["r"])
    k = dur_kind(s)
    if k in ("decided_dotted", "narrowed_with_dotted"):
        false_dot[k] += 1
        false_rows.append(dict(truth=h["id"], our=s, kind=k))
heads = []
for hid, (o, oh, ds) in dotted_heads.items():
    v = live.get((oh, Q.DURATION), {}) if oh else {}
    heads.append(dict(truth=hid, cls=o["cls"], rect=o["r"], our=oh, dots=ds, duration=dur_kind(oh),
                      reason=v.get("reason"), decider=v.get("decider"), value=v.get("value")))
res = dict(env={k: os.environ.get(k) for k in sorted(os.environ) if k.startswith("OMR_")},
           dots=dict(c_dot), dotted_heads=dict(c_head), undotted_heads_given_a_dot=dict(false_dot),
           false_rows=false_rows, rows=rows, heads=heads,
           # every page's live duration, for the base/arm diff (`diff_2_151.py`)
           durations={s: [v["outcome"], (v["value"] or {}).get("written") if isinstance(v["value"], dict) else None,
                          (v["value"] or {}).get("dots") if isinstance(v["value"], dict) else None, v["reason"],
                          v.get("decider"),
                          sorted({(c.get("value") or {}).get("written") for c in v.get("candidates") or []
                                  if isinstance(c.get("value"), dict)}, key=str)]
                      for (s, q), v in live.items() if q == Q.DURATION and s.startswith("glyph/")},
           page_boxes={s: b for s, b in all_boxes.items()})
json.dump(res, open(OUT, "w"), indent=0, default=str)
print("truth dots", len(tdots), dict(c_dot))
print("dotted heads", len(dotted_heads), dict(c_head))
print("false dots on undotted heads", dict(false_dot))
