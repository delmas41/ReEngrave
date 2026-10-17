"""ROADMAP 2.158 -- a STATIC estimate (stored verdicts, no replay) of the bars the lone-event exemption could reach: a staff's
bar whose live durations group into ONE event (decided/narrowed members all NARROWED, none a rest), under a DECIDED meter
with a printed reason, where each member has exactly one candidate filling the bar. Approximate (no `_left_the_bar`, no
solver guards); used only to choose the systems a slice replay must hold. Streamed.
usage: static_2_158.py RECORD.json OUT.json"""
import collections
import json
import sys

import ijson

REC, OUT = sys.argv[1:3]
dur = collections.defaultdict(dict)       # cell -> glyph -> chain
ev, met = {}, {}
gone = collections.defaultdict(list)    # glyph -> verdicts that may set it aside (`_left_the_bar`, approximated)
LEAVE = ("notehead_is_not_a_notehead", "rest_is_not_a_rest", "glyph_owner", "notehead_is_an_eighth_rest")


def live(ch):
    sup = {v.get("supersedes") for v in ch if v.get("supersedes")}
    l = [v for v in ch if v["id"] not in sup] or ch
    return l[-1]


with open(REC, "rb") as fh:
    for v in ijson.items(fh, "record.verdicts.item", use_float=True):
        s, q = v["subject"], v["quantity"]
        if q == "duration" and s.startswith("glyph/"):
            p = s.split("/")
            dur["cell/" + "/".join(p[1:5])].setdefault(int(p[5]), []).append(v)
        elif q in LEAVE and s.startswith("glyph/"):
            gone[s].append(v)
        elif q == "event" and s.startswith("cell/"):
            ev.setdefault(s, []).append(v)
        elif q == "meter" and s.startswith("system/"):
            met.setdefault(s, []).append(v)


def at(mv, cell):
    segs = mv.get("segments") or [mv]
    cur = None
    for sg in segs:
        if int(sg.get("from_cell") or 0) <= cell:
            cur = sg
    return cur


def left(c, g):
    rows = collections.defaultdict(list)
    for v in gone.get("glyph/%s/%d" % (c[5:], g), ()):
        rows[v["quantity"]].append(v)
    lv = {q: live(ch) for q, ch in rows.items()}
    reinst = lv.get("notehead_is_an_eighth_rest", {}).get("value") is True
    for q in ("notehead_is_not_a_notehead", "rest_is_not_a_rest"):
        if q in lv and lv[q]["outcome"] == "decided" and lv[q]["value"] is True and not (reinst and q.startswith("notehead")):
            return True
    o = lv.get("glyph_owner")
    staff = "staff/" + "/".join(c.split("/")[1:4])
    return bool(o and o["outcome"] == "decided" and isinstance(o["value"], str) and o["value"] != staff)


hits, why = [], collections.Counter()
for c, by in dur.items():
    p = c.split("/")
    lv = {g: live(ch) for g, ch in by.items() if not left(c, g)}
    members = {g: v for g, v in lv.items() if v["outcome"] in ("decided", "narrowed")}
    if not any(v["outcome"] == "narrowed" for v in members.values()):
        continue
    why["has_narrowing"] += 1
    if c not in ev:
        why["no_event"] += 1
        continue
    e = live(ev[c])
    events = [set(x.get("glyphs", ())) & set(lv) for x in (e["value"] or {}).get("events", ())]
    events = [x for x in events if x]
    if len(events) != 1:
        why["not_one_event"] += 1
        continue
    if any(v["outcome"] == "decided" for v in members.values()):
        why["decided_member"] += 1
        continue
    if any(any((cd.get("value") or {}).get("is_rest") for cd in v.get("candidates") or []) for v in members.values()):
        why["rest"] += 1
        continue
    m = met.get("system/%s/%s" % (p[1], p[2]))
    m = live(m) if m else None
    if not m or m["outcome"] != "decided" or m.get("reason") not in ("voted", "carried", "carried_uncontested"):
        why["meter"] += 1
        continue
    sg = at(m["value"], int(p[4]))
    if not sg or not sg.get("numerator"):
        why["no_meter_in_force"] += 1
        continue
    target = sg["numerator"] * 4.0 / sg["denominator"]
    ok = all(sum(1 for cd in v.get("candidates") or [] if abs(((cd.get("value") or {}).get("beats") or -9) - target) < 1e-6) == 1
             for v in members.values())
    if not ok:
        why["not_exactly_one_fills"] += 1
        continue
    why["HIT"] += 1
    hits.append({"cell": c, "target": target, "glyphs": sorted(members),
                 "reasons": sorted({v.get("reason") for v in members.values()}),
                 "cands": sorted({(cd.get("value") or {}).get("beats") for v in members.values()
                                  for cd in v.get("candidates") or []} - {None})})
json.dump({"why": why, "hits": hits}, open(OUT, "w"), indent=0)
print(dict(why))
print("systems", sorted({tuple(int(x) for x in h["cell"].split("/")[1:3]) for h in hits}))
