"""2.291: sort every RED bar into a cause family from the bar's own export numbers and glyph rows (rules fixed here, BEFORE reading the print;
the print check and Sean's tiles then test them).  usage: classify.py OUT.json BARS.json [BARS.json ...]

Per bar (red status only), from `capture.py`'s rows:
  want, counted (per voice); delta = the voice furthest from the bar (counted - want);
  written events = glyph rows with fate written/written_relocated and head or rest;
  TWIN     two WRITTEN head/rest boxes overlap by >= 50% of the smaller box (one mark counted twice);
  FALSE    a WRITTEN rest whose box is wider than 3 staff spaces (a staff-line / beam piece read as a rest), or whole rests >= 2 in the bar;
  VOICES   written heads show BOTH stem directions (up and down) and the bar was NOT split into two voices (or a voice is short);
  SHORT    delta < 0 and none of the above, no unread glyph named: a member of the bar was never read (never boxed, or claimed as another mark);
  LONG     delta > 0 and none of the above: a DECIDED value is too long (flag / beam / dot not read, or a rest read one class too long);
First match in that order = the cause recorded (upstream first: a mark counted twice or invented before values before voices before members).
"""
import collections
import json
import sys

U = {"litolff": 15.75, "brahms": 32.0}


def area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def inter(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, w) * max(0.0, h)


def classify(b):
    r = b["red"]
    u = U[b["plate"]]
    want = r["want_quarters"]
    cnt = r["counted_quarters"]
    deltas = [c - want for c in cnt]
    delta = max(deltas, key=abs)
    ws = [g for g in b["glyphs"] if (g["head"] or g["rest"]) and g["fate"] in ("written", "written_relocated") and g["box"]]
    feats = {"delta": round(delta, 3), "two_voice": r["two_voice"], "n_written": len(ws)}
    twin = False
    for i in range(len(ws)):
        for j in range(i + 1, len(ws)):
            a, c = ws[i]["box"], ws[j]["box"]
            if inter(a, c) >= 0.5 * min(area(a), area(c)) and (ws[i]["head"] == ws[j]["head"]):
                twin = True
    wide_rest = any(g["rest"] and (g["box"][2] - g["box"][0]) > 3.0 * u for g in ws)
    whole_rests = sum(1 for q in (b.get("red_rows") or []) if q["kind"] == "rest" and q["beats"] == 4.0)
    dirs = {g["stem_dir"] for g in ws if g["head"] and g.get("stem_dir") in ("up", "down")}
    feats.update(twin=twin, wide_rest=wide_rest, whole_rests=whole_rests, dirs=sorted(dirs))
    if twin:
        fam = "TWIN"
    elif wide_rest or whole_rests >= 2 or (whole_rests >= 1 and len(b.get("red_rows") or []) > 1):
        fam = "FALSE"
    elif len(dirs) == 2 and (not r["two_voice"] or delta < 0):
        fam = "VOICES"
    elif delta < 0:
        fam = "SHORT"
    else:
        fam = "LONG"
        # sub-cause of LONG: a flag / beam box stands at a written head whose value is a quarter or longer (the mark is there, the value ignores it)
        beats = {q.get("glyph"): q["beats"] for q in (b.get("red_rows") or []) if q["kind"] == "note"}
        near = False
        for g in b["glyphs"]:
            c = (g["cls"] or "").lower()
            if g["box"] and ("flag" in c or c.startswith("beam")):
                gx = (g["box"][0] + g["box"][2]) / 2
                for h in ws:
                    if h["head"] and beats.get(h["sub"], 0) >= 1.0 and abs((h["box"][0] + h["box"][2]) / 2 - gx) < 2.5 * u:
                        near = True
        feats["flag_or_beam_near_long_head"] = near
        if near:
            fam = "LONG_FLAG"
    return fam, feats


def main():
    out = sys.argv[1]
    res = []
    for f in sys.argv[2:]:
        for b in json.load(open(f)):
            if not b["red"]:
                continue
            fam, feats = classify(b)
            res.append({"plate": b["plate"], "key": b["key"], "measure": b["measure"], "why": b["why"], "family": fam, **feats,
                        "want": b["red"]["want_quarters"], "counted": b["red"]["counted_quarters"],
                        "notes": b["red"]["noteheads_and_rests"], "meter": (b.get("meter") or {}).get("reason")})
    json.dump(res, open(out, "w"), indent=1)
    for plate in ("litolff", "brahms"):
        rows = [x for x in res if x["plate"] == plate]
        c = collections.Counter(x["family"] for x in rows)
        n = collections.Counter()
        for x in rows:
            n[x["family"]] += x["notes"]
        print(plate, "bars", len(rows), "notes", sum(n.values()))
        for k, v in c.most_common():
            print("   %-7s %3d bars  %4d notes" % (k, v, n[k]))


main()
