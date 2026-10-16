"""ROADMAP 2.151 -- two dot losses the hand-truth page and Sean's 2.146 tiles 23/34 point at (STAGED; a record's own
ADJUDICATE verdicts, nothing re-decided):

  A. a DOT BOXED AS A NOTEHEAD: a notehead-class box the notehead gate refused (any reason), dot-sized (both sides
     <= 0.6 sp), standing in a kept head's augmentation place (gap -0.1..1.5 sp right of it, |dy| <= 0.8 sp) -- the
     head's duration carries no dot from it;
  B. a REFUSED HEAD THAT TAKES A DOT: a `Q.DOT_ROLE` augmentation verdict, or a duration's own `dots`, on a head the
     notehead gate refused, while a kept head at the same place is undotted.
usage: dot_as_head_2_151.py RECORD.json [SPACE_PX]   (SPACE_PX: page px per staff space, default 33)"""
import collections, json, sys

rec = json.load(open(sys.argv[1]))
rec = rec.get("record", rec)
SP = float(sys.argv[2]) if len(sys.argv) > 2 else 33.0
box, cls = {}, {}
for o in rec["observations"]:
    if o["quantity"] == "glyph_box":
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb:
            box[o["subject"]] = bb
            cls[o["subject"]] = o["value"][0]
sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
live = {}
for v in rec["verdicts"]:
    if v["id"] not in sup:
        live[(v["subject"], v["quantity"])] = v


def refused(s):
    v = live.get((s, "notehead_is_not_a_notehead"))
    return v is not None and v["outcome"] == "decided" and v["value"] is True


def dots_of(s):
    v = live.get((s, "duration"))
    if v and v["outcome"] == "decided" and isinstance(v["value"], dict):
        return v["value"].get("dots") or 0
    if v and v["outcome"] == "narrowed":
        return "narrowed:" + ",".join(sorted({str((c.get("value") or {}).get("dots")) for c in v.get("candidates") or []}))
    return None if v is None else v["outcome"]


heads = [s for s, c in cls.items() if c.startswith("notehead")]
kept = [s for s in heads if not refused(s)]
by_sys = collections.defaultdict(list)
for s in kept:
    by_sys["/".join(s.split("/")[:3])].append(s)
A = []
reasons = collections.Counter()
for s in heads:
    if not refused(s):
        continue
    b = box[s]
    w, h = (b[2] - b[0]) / SP, (b[3] - b[1]) / SP
    if w > 0.6 or h > 0.6:
        continue
    cy = (b[1] + b[3]) / 2
    best = None
    for k in by_sys["/".join(s.split("/")[:3])]:
        hb = box[k]
        gap = (b[0] - hb[2]) / SP
        dy = (cy - (hb[1] + hb[3]) / 2) / SP
        if -0.1 <= gap <= 1.5 and abs(dy) <= 0.8:
            sc = gap + 2 * abs(dy)
            if best is None or sc < best[0]:
                best = (sc, k, round(gap, 2), round(dy, 2))
    if best:
        r = live[(s, "notehead_is_not_a_notehead")]["reason"]
        reasons[r] += 1
        A.append(dict(glyph=s, cls=cls[s], size=(round(w, 2), round(h, 2)), refusal=r, head=best[1], gap=best[2],
                      dy=best[3], head_dots=dots_of(best[1])))
print("A. dot-sized refused 'heads' in a kept head's dot place:", len(A), dict(reasons))
print("   their heads' dots:", dict(collections.Counter(str(a["head_dots"]) for a in A)))
B = []
for (s, q), v in live.items():
    if q != "dot_role" or v["outcome"] != "decided" or v["value"] != "augmentation":
        continue
    hd = (v.get("detail") or {}).get("head")
    if hd and refused(hd):
        B.append(dict(dot=s, head=hd, head_reason=live[(hd, "notehead_is_not_a_notehead")]["reason"]))
B2 = [s for s in heads if refused(s) and isinstance(dots_of(s), int) and dots_of(s) > 0]
print("B. augmentation dots naming a REFUSED head:", len(B), dict(collections.Counter(b["head_reason"] for b in B)))
print("   refused heads whose (stale) duration carries a dot:", len(B2))
json.dump(dict(A=A, B=B, B2=B2), open(sys.argv[1].rsplit("/", 1)[-1] + ".dot_as_head.json", "w"), indent=0)
