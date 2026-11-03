"""What the detector drew at each print-confirmed clef change (lane-report slice, GATHER rows only).

python3 work-2.251/boxes.py PLATE "pg:sys:stafflocal:c0:c1" ...
"""
import json, os, sys

sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
import crops  # noqa: E402

SL = "library/_shared-records/lane-report-slices-20261029-night"


def main():
    plate = sys.argv[1]
    want = []
    for a in sys.argv[2:]:
        pg, s, sl, c0, c1 = (int(x) for x in a.split(":"))
        d = crops.cmap(plate, pg)
        staves = sorted([t for t in d["staves"] if t["system_index"] == s], key=lambda t: t["line_ys"][0])
        st = staves[sl]
        want.append((pg, s, sl, c0, c1, (st["line_ys"][4] - st["line_ys"][0]) / 4.0, a))
    keys = {(pg, s, g): w for w in want for (pg, s, g) in [(w[0], w[1], w[2])]}
    hits = {w[6]: [] for w in want}
    with open(f"{SL}/{plate}/observations.jsonl") as f:
        for line in f:
            if '"glyph_box"' not in line:
                continue
            r = json.loads(line)
            if r["quantity"] != "glyph_box":
                continue
            p = r["subject"].split("/")
            pg, s, g, c = int(p[1]), int(p[2]), int(p[3]), int(p[4])
            for w in want:
                if (w[0], w[1], w[2]) == (pg, s, g) and w[3] <= c <= w[4]:
                    bb = r["detail"]["bbox_page_px"]
                    hits[w[6]].append((round(bb[0]), c, r["value"][0], round(r["score"], 2),
                                       round((bb[2] - bb[0]) / w[5], 1), round((bb[3] - bb[1]) / w[5], 1), r["subject"]))
    for k, v in hits.items():
        print("==", k)
        seen = set()
        for h in sorted(v):
            key = (h[0] // 4, h[2])
            if key in seen:
                continue  # padded-cell copy
            seen.add(key)
            print("  x=%d c%d %-22s %.2f w=%.1fsp h=%.1fsp %s" % h)


main()
