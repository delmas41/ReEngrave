"""2.248: what the reading does with each cell-edge twin (a short notehead box whose head is boxed whole in another staff's
cell): its `notehead_is_not_a_notehead` verdict and its `glyph_owner`, plus the named tile places.
usage: fate.py RECORD.json [glyph ...]"""
import collections
import json
import sys


def main(path, *named):
    rec = json.load(open(path))
    rec = rec.get("record", rec)
    box, nn, own = {}, {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            box[o["subject"]] = o["detail"]["bbox_page_px"]
    for v in rec["verdicts"]:
        if v["quantity"] == "notehead_is_not_a_notehead":
            nn[v["subject"]] = (v["outcome"], v.get("value"), v.get("reason"))
        elif v["quantity"] == "glyph_owner":
            own[v["subject"]] = (v.get("value"), v.get("reason"))
    by = collections.defaultdict(list)
    for s, b in box.items():
        by[tuple(s.split("/")[1:3])].append((s, b))
    fate = collections.Counter()
    for s, b in box.items():
        h = b[3] - b[1]
        twin = None
        for s2, b2 in by[tuple(s.split("/")[1:3])]:
            if s2.split("/")[3] == s.split("/")[3] or (b2[3] - b2[1]) < 1.5 * h:
                continue
            if min(b[2], b2[2]) - max(b[0], b2[0]) > 0.5 * (b[2] - b[0]) and min(b[3], b2[3]) - max(b[1], b2[1]) > 0:
                twin = s2
        if not twin:
            continue
        v = nn.get(s)
        fate["refused:%s" % v[2] if v and v[0] == "decided" and v[1] is True else "read as a head (%s)" % (v[2] if v else "no verdict")] += 1
    print("cell-edge twins (box < 2/3 of an overlapping head box in another staff's cell):", sum(fate.values()))
    for k, n in fate.most_common():
        print("   %4d %s" % (n, k))
    for g in named:
        print(g, box.get(g), nn.get(g), own.get(g))


if __name__ == "__main__":
    main(*sys.argv[1:])
