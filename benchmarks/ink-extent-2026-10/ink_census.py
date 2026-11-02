"""2.248 cause census: the detector's NOTEHEAD box against the head's own ink extent (`Q.HEAD_INK` 'trimmed', 2.220's
reading grown from the box rows +-0.45 sp, page raster) -- how often the box stops >= 0.25 sp short of the ink, by plate,
split by whether the short box is a CELL-EDGE TWIN (a notehead box of another staff's cell holds the same head whole)
and by what the reading does with it (`notehead_is_not_a_notehead` verdict when the source holds verdicts).

usage: ink_census.py PLATE=SOURCE[=PAGES] ...   SOURCE = a slice dir (observations/abstentions/verdicts.jsonl) or a record.json"""
import collections
import json
import os
import sys

WANT = ('"glyph_box"', '"head_ink"', '"notehead_is_not_a_notehead"', '"notehead_recentre"', '"notehead_staff_position"')


def rows(src):
    if os.path.isdir(src):
        for f in ("observations.jsonl", "abstentions.jsonl", "verdicts.jsonl"):
            p = os.path.join(src, f)
            if not os.path.exists(p):
                continue
            for line in open(p):
                if any(w in line for w in WANT):
                    yield json.loads(line)
    else:
        rec = json.load(open(src))
        rec = rec.get("record", rec)
        for k in ("observations", "abstentions", "verdicts"):
            for r in rec.get(k, ()):
                yield r


def census(plate, src, pages=None):
    box, ink, nn, rc, pos = {}, {}, {}, {}, {}
    for r in rows(src):
        s = r.get("subject") or ""
        if not s.startswith("glyph/"):
            continue
        if pages is not None and int(s.split("/")[1]) not in pages:
            continue
        q = r.get("quantity")
        d = r.get("detail") or {}
        if q == "glyph_box" and d.get("category") == "notehead":
            box[s] = d["bbox_page_px"]
        elif q == "head_ink" and d.get("trimmed"):
            ink[s] = (d["trimmed"], d.get("extent_sp"), d.get("not_one_head"))
        elif q == "notehead_is_not_a_notehead" and "outcome" in r:
            nn[s] = (r["outcome"], r.get("value"), r.get("reason"))
        elif q == "notehead_recentre" and "value" in r:
            rc[s] = r["value"]
        elif q == "notehead_staff_position" and "value" in r and "outcome" not in r:
            pos[s] = r["value"]
    by_page = collections.defaultdict(list)
    for s, b in box.items():
        by_page[s.split("/")[1]].append((s, b))
    c = collections.Counter()
    fate = collections.Counter()
    ex = []
    for s, b in box.items():
        if s not in ink:
            c["no head_ink extent"] += 1
            continue
        t, ext, why = ink[s]
        h_px = b[3] - b[1]
        sp = (t[3] - t[1]) / ext[1] if ext and ext[1] else None
        if not sp:
            continue
        c["heads with an ink extent"] += 1
        short = max(b[1] - t[1], t[3] - b[3], b[0] - t[0], t[2] - b[2]) / sp
        if short < 0.25:
            continue
        c["box >= 0.25 sp short of its ink"] += 1
        st = s.split("/")[3]
        twin = None
        for s2, b2 in by_page[s.split("/")[1]]:
            if s2.split("/")[3] == st or s2.split("/")[2] != s.split("/")[2]:
                continue
            if (b2[3] - b2[1]) <= h_px + 0.25 * sp:
                continue
            if min(b[2], b2[2]) - max(b[0], b2[0]) > 0.5 * (b[2] - b[0]) and min(b[3], b2[3]) - max(b[1], b2[1]) > 0:
                twin = s2
                break
        kind = "cell-edge twin" if twin else "only box on its head"
        c["  " + kind] += 1
        v = nn.get(s)
        tag = ("refused:%s" % v[2]) if v and v[0] == "decided" and v[1] is True else ("read as a head" if v else "no verdict in source")
        fate[(kind, tag, "recentred" if isinstance(rc.get(s), list) else "box centre")] += 1
        if not twin and len(ex) < 10:
            ex.append((s, [round(x, 1) for x in b], t, round(short, 2), why))
    # the pitch: the position is read from the BOX centre (gather_notehead_positions); where the box is one head's only box
    # and its ink is ONE head (head_ink not_one_head None) running into no other notehead box of its cell, where would the
    # INK centre put it?
    pc = collections.Counter()
    moved = []
    for s, b in box.items():
        if s not in ink or s not in pos or ink[s][2] is not None:
            continue
        t, ext, _ = ink[s]
        sp = (t[3] - t[1]) / ext[1] if ext and ext[1] else None
        if not sp:
            continue
        cellk = s.rsplit("/", 1)[0]
        mates = [b2 for s2, b2 in box.items() if s2 != s and s2.rsplit("/", 1)[0] == cellk
                 and min(t[2], b2[2]) - max(t[0], b2[0]) > 0 and min(t[3], b2[3]) - max(t[1], b2[1]) > 0.15 * sp
                 and not (b2[1] >= b[1] - 1 and b2[3] <= b[3] + 1)]
        pc["one-head ink"] += 1
        if mates:
            pc["  ink runs into another head box (left out)"] += 1
            continue
        d_steps = ((t[1] + t[3]) / 2.0 - (b[1] + b[3]) / 2.0) / (sp / 2.0)
        p0 = pos[s]
        if round(p0) != round(p0 + d_steps):
            pc["  rounded position differs (box centre vs ink centre)"] += 1
            if len(moved) < 40:
                moved.append((s, [round(x, 1) for x in b], t, round(p0, 2), round(p0 + d_steps, 2)))
    print(plate, dict(c))
    print("   pitch:", dict(pc))
    with open("/tmp/2248_moved_%s.json" % plate if False else os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "moved_%s.json" % plate), "w") as f:
        json.dump(moved, f)
    for k, v in sorted(fate.items(), key=lambda kv: -kv[1]):
        print("   %4d  %s" % (v, " | ".join(k)))
    for e in ex:
        print("   only-box example", e)


def main(*args):
    for a in args:
        parts = a.split("=")
        census(parts[0], parts[1], set(int(p) for p in parts[2].split(",")) if len(parts) > 2 else None)


if __name__ == "__main__":
    main(*sys.argv[1:])
