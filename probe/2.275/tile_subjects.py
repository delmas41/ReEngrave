"""2.275: write the subject list of the pattern tiles per plate (for claims_probe.py) and, given the two probe outputs, print one line per tile.
usage: tile_subjects.py split KEY.json OUTPREFIX     |     tile_subjects.py lines KEY.json LIT_CLAIMS.json BRA_CLAIMS.json"""
import json
import sys

mode, keyp = sys.argv[1], sys.argv[2]
K = json.load(open(keyp))["tiles"]
if mode == "split":
    for plate in ("litolff", "brahms"):
        json.dump({v["subject"]: n for n, v in K.items() if v["plate"] == plate}, open("%s_%s.json" % (sys.argv[3], plate), "w"))
else:
    res = {}
    for p in sys.argv[3:5]:
        for x in json.load(open(p)):
            res[x["sub"]] = x
    for n, v in sorted(K.items(), key=lambda kv: int(kv[0])):
        x = res[v["subject"]]
        fams = ",".join("%s(%s %.2f)" % (f[0], f[1], f[2]) for f in x["stroke_families"][:3]) or "no stroke under the box"
        area = ",".join("%s %.2f" % (k, a[0]) for k, a in x["area"].items()) or "none"
        print("%2s %-7s p%-2s s%s st%-2s c%-2s | %-34s | area claim: %-24s | strokes: %-44s | slash rows in cell %d | first refusal: %s" % (
            n, v["plate"], v["page"], v["system"], v["staff"], v["cell"], x["bucket"].replace("refused:", "").replace("not_a_notehead:", ""),
            area, fams, x["slash_rows_in_cell"], x["refusal_reason"]))
