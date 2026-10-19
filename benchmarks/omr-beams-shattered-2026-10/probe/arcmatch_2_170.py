"""2.170: do the 2.166 stroke_only beam boxes match a Q.BEAM_STROKE row (detector, identical box) or contain a CV stroke?
usage: arcmatch_2_170.py SLICEDIR/DOC"""
import glob
import json
import sys
from collections import Counter, defaultdict

D = sys.argv[1]
arcg = {}
gbox, strokes = {}, defaultdict(list)
for p in sorted(glob.glob(D + "/p*.observations.jsonl")):
    for l in open(p):
        o = json.loads(l)
        q = o["quantity"]
        if q == "system_arc":
            for tb in o["detail"].get("through_boxes") or []:
                if tb.get("stroke_only") and str(tb.get("class")).startswith("beam"):
                    arcg[tb["glyph"]] = o["id"]
        elif q == "glyph_box" and o["subject"].startswith("glyph/"):
            gbox[o["subject"]] = o["value"]
        elif q == "beam_stroke":
            strokes[o["subject"]].append((o["reader"], o["value"]))
c = Counter()
for g in arcg:
    v = gbox.get(g)
    if v is None:
        c["no_glyph_box"] += 1
        continue
    cell = "cell/" + "/".join(g.split("/")[1:5])
    box = tuple(round(float(t), 1) for t in v[1:5])
    det = [s for r, s in strokes[cell] if r == "detector" and tuple(round(float(t), 1) for t in s) == box]
    cvin = [s for r, s in strokes[cell] if r == "cv_lines" and s[0] >= box[0] and s[1] >= box[1]
            and s[0] + s[2] <= box[0] + box[2] and s[1] + s[3] <= box[1] + box[3]]
    c["det_match" if det else "det_nomatch"] += 1
    c["cv_inside" if cvin else "no_cv_inside"] += 1
    xo = [s for r, s in strokes[cell] if r == "cv_lines" and s[0] <= box[0] + box[2] and s[0] + s[2] >= box[0]]
    c["dropped_by_kept_beams(cv overlaps in x)" if xo else "kept_as_candidate"] += 1
    if not det and c["shown"] < 3:
        c["shown"] += 1
        print(g, v, [s for r, s in strokes[cell] if r == "detector"][:4])
print(len(arcg), dict(c))
