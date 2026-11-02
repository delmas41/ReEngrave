"""Filled-class head boxes TALLER than any head (2.245's HEAD_BLOB_H_SP max) whose own ink fills less than a head (HEAD_FILL_MIN), on the
night slices: how many the reading keeps today.  usage: tall_census.py PLATE UNIT"""
import json
import sys

S = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/%s/" % sys.argv[1]
u = float(sys.argv[2])
box, ink, kept = {}, {}, {}
for line in open(S + "observations.jsonl"):
    if '"glyph_box"' in line or '"notehead_ink"' in line:
        o = json.loads(line)
        if o["quantity"] == "glyph_box" and str(o["value"][0]).startswith("noteheadBlack"):
            box[o["subject"]] = o["detail"]["bbox_page_px"]
        elif o["quantity"] == "notehead_ink":
            ink[o["subject"]] = o["value"]
for line in open(S + "verdicts.jsonl"):
    if '"notehead_is_not_a_notehead"' in line[:200]:
        v = json.loads(line)
        if v["quantity"] == "notehead_is_not_a_notehead":
            kept[v["subject"]] = (v["outcome"], v["value"], v["reason"])
hits = []
for s, b in box.items():
    h = (b[3] - b[1]) / u
    if h >= 1.5 and ink.get(s) is not None and ink[s] < 0.6:
        hits.append((s, [round(x) for x in b], round(h, 2), round(ink[s], 2), kept.get(s)))
print(sys.argv[1], "tall + under-filled filled-class boxes:", len(hits), " kept as heads:",
      sum(1 for h in hits if h[4] and h[4][0] == "decided" and h[4][1] is False))
for h in hits:
    print("  ", h)
