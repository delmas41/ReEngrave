"""2.280 micro: SECONDARY counts (not bars). (1) PROXY for 'would the value become decidable by the existing tip/flag/beam readers': for each head arm B filed, what ink stands at the
stem tip (a detector beam box / flag box within 0.6 sp of the tip = a reader has something to read; nothing = a bare tip). This is NOT a re-adjudication.
(2) judged exposure: Sean's judged items whose subject key is a head arm B would file for. usage: m5_secondary.py"""
import collections
import json

SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/"
idx = json.load(open("benchmarks/acceptance/judged-tiles.json"))
items = idx["tiles"]
judged = collections.defaultdict(list)
for it in items:
    for s in (it.get("subjects") or [it.get("subject")]):
        if s:
            judged[(it.get("doc"), s)].append((it.get("question_kind"), it.get("answer_kind"), it.get("value")))
for plate in ("litolff", "brahms"):
    res = json.load(open("out/2.280-micro/proto_%s.json" % plate))["results"]
    marks = []
    for line in open(SL + plate + "/observations.jsonl"):
        if '"glyph_box"' in line:
            o = json.loads(line)
            if o["quantity"] == "glyph_box" and o["value"][0] and (o["value"][0] == "beam" or o["value"][0].startswith("flag")) and o["detail"].get("bbox_page_px"):
                marks.append((o["value"][0], o["detail"]["bbox_page_px"]))
    for grp in ("real51", "decided299"):
        c = collections.Counter()
        for s, r in res.items():
            if grp not in r["groups"]:
                continue
            B = r["B"]
            if B["status"] != "filed":
                c["no row filed"] += 1
                continue
            bx = B["box"]
            ty = bx[1] if B["direction"] == "up" else bx[3]
            sp = r["sp"]
            near = [m for m, b in marks if b[0] - 0.6 * sp <= bx[2] and b[2] + 0.6 * sp >= bx[0] and b[1] - 0.6 * sp <= ty <= b[3] + 0.6 * sp]
            c["row filed, beam at tip" if "beam" in near else "row filed, flag at tip" if near else "row filed, bare tip (nothing for a beam/flag reader to read)"] += 1
        print(plate, grp, dict(c))
    ex = [(s, judged[(plate, s)]) for s, r in res.items() if r["B"]["status"] == "filed" and "agree200" not in r["groups"] and judged.get((plate, s))]
    print(plate, "judged items whose key is a head arm B files a NEW row for (no-stem heads):", len(ex), ex[:5])
