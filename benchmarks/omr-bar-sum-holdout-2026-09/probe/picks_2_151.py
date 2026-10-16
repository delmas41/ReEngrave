"""ROADMAP 2.151 -- the tile picks: every head the arm changed (dotted, or narrowed with a dotted candidate), every head
beside a dot-shaped refused box the arm did NOT change (declined), and random plain / dotted controls.
usage: picks_2_151.py OUT.json RECORD OFF.json ON.json [RECORD OFF.json ON.json ...]  (Brahms page px, 33 per space)"""
import json, random, sys

SP = 33.0
OUT = sys.argv[1]
args = sys.argv[2:]
rng = random.Random(2151)
picks, plain, dotted = [], [], []
for i in range(0, len(args), 3):
    rec = json.load(open(args[i]))
    rec = rec.get("record", rec)
    off, on = json.load(open(args[i + 1])), json.load(open(args[i + 2]))
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    refusal = {v["subject"]: v for v in rec["verdicts"]
               if v["quantity"] == "notehead_is_not_a_notehead" and v["id"] not in sup}
    box, cls = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px"):
            box[o["subject"]] = o["detail"]["bbox_page_px"]
            cls[o["subject"]] = o["value"][0]
    del rec
    kept = [s for s, c in cls.items() if c.startswith("notehead") and not (refusal.get(s) or {}).get("value")]
    D0, D1 = off["durations"], on["durations"]
    changed = set()
    for s in kept:
        a, b = D0.get(s), D1.get(s)
        if a == b or b is None:
            continue
        dotted_now = (b[0] == "decided" and b[2]) or (b[0] == "narrowed" and any(
            w not in (a[5] if a else []) for w in b[5]))
        was_dotted = a and a[0] == "decided" and a[2]
        if dotted_now and not was_dotted:
            changed.add(s)
            picks.append(dict(doc="brahms", glyph=s, bbox=box[s], role="changed", base=a, arm=b))
    for m, v in refusal.items():
        if not v.get("value") or v.get("reason") not in ("too_narrow", "is_a_dot") or m not in box:
            continue
        mb = box[m]
        if (mb[2] - mb[0]) / SP > 0.75 or (mb[3] - mb[1]) / SP > 0.75:
            continue
        cy = (mb[1] + mb[3]) / 2
        best = None
        for s in kept:
            if s.split("/")[:3] != m.split("/")[:3]:
                continue
            hb = box[s]
            gap, dy = (mb[0] - hb[2]) / SP, (cy - (hb[1] + hb[3]) / 2) / SP
            if -0.1 <= gap <= 1.5 and abs(dy) <= 0.8:
                sc = gap + 2 * abs(dy)
                if best is None or sc < best[0]:
                    best = (sc, s)
        if best and best[1] not in changed and (D1.get(best[1]) or [None])[0] == "decided" \
                and not D1[best[1]][2]:
            picks.append(dict(doc="brahms", glyph=best[1], bbox=box[best[1]], role="declined",
                              base=D0.get(best[1]), arm=D1.get(best[1]), mark=m))
    for s in kept:
        a, b = D0.get(s), D1.get(s)
        if a and a == b and a[0] == "decided" and a[1] in (1.0, 1.5, 2.0, 3.0):
            (dotted if a[2] else plain).append(dict(doc="brahms", glyph=s, bbox=box[s],
                                                     role="dotted_control" if a[2] else "plain_control",
                                                     base=a, arm=b))
seen, uniq = set(), []
for p in picks:
    if p["glyph"] not in seen:
        seen.add(p["glyph"]); uniq.append(p)
n_ctrl = 5
uniq += rng.sample(plain, min(n_ctrl, len(plain))) + rng.sample(dotted, min(n_ctrl, len(dotted)))
json.dump(uniq, open(OUT, "w"), indent=0)
import collections
print(len(uniq), dict(collections.Counter(p["role"] for p in uniq)))
