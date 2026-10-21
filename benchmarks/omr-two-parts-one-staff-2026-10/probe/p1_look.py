"""ROADMAP 2.182 -- what the record holds in the bars 2.179 labelled (fv two parts, d rest chain).

usage: python3 benchmarks/omr-two-parts-one-staff-2026-10/probe/p1_look.py RECORD CENSUS LABELS OUT.json
Per labelled bar: Q.EVENT's events (kind, x, glyphs), each glyph's Q.STEM_DIRECTION / Q.NOTEHEAD_STAFF_POSITION / Q.DURATION,
the bar's Q.VOICES verdict. Read-only.
"""
import json
import sys

rec_path, census_path, labels_path, out_path = sys.argv[1:5]
census = json.load(open(census_path))
labels = {}
for line in open(labels_path):
    if line.startswith("#") or "|" not in line:
        continue
    i, codes, text = [x.strip() for x in line.split("|", 2)]
    labels[int(i)] = (codes.split(), text)
want = {}
for i, e in enumerate(census):
    codes = labels[i][0]
    if "fv" in codes or "d" in codes:
        want.setdefault(e["bar"], (i, codes, labels[i][1]))
cells = {"cell/" + k for k in want}
data = json.load(open(rec_path))
rec = data["record"]
Q = {"stem_direction", "duration", "rest_is_not_a_rest", "notehead_is_not_a_notehead"}
gl = {}
cellv = {}
for v in rec["verdicts"]:
    s = v.get("subject") or ""
    q = v.get("quantity")
    if s.startswith("cell/") and s in cells and q in ("event", "voices"):
        cellv.setdefault(s, {})[q] = {k: v.get(k) for k in ("outcome", "value", "reason", "detail")}
    elif s.startswith("glyph/") and q in Q:
        ck = "cell/" + "/".join(s.split("/")[1:5])
        if ck in cells:
            val = v.get("value")
            if q == "duration" and isinstance(val, dict):
                val = val.get("beats")
            gl.setdefault(s, {})[q] = (v.get("outcome"), val, v.get("reason"))
for o in rec["observations"]:
    s = o.get("subject") or ""
    if o.get("quantity") in ("notehead_staff_position", "glyph_box") and s.startswith("glyph/"):
        ck = "cell/" + "/".join(s.split("/")[1:5])
        if ck in cells:
            if o["quantity"] == "glyph_box":
                gl.setdefault(s, {}).setdefault("box", (o["value"][0], (o.get("detail") or {}).get("bbox_page_px")))
            else:
                gl.setdefault(s, {})["pos_obs"] = o["value"]
out = []
for bar, (i, codes, text) in sorted(want.items(), key=lambda kv: kv[1][0]):
    c = "cell/" + bar
    cv = cellv.get(c, {})
    evs = ((cv.get("event") or {}).get("value") or {}).get("events") or []
    rows = []
    for e in evs:
        gs = []
        for g in e.get("glyphs") or ():
            s = "glyph/%s/%d" % (bar, g)
            G = gl.get(s, {})
            gs.append(dict(g=g, cls=(G.get("box") or [None])[0], dir=G.get("stem_direction"),
                           pos=G.get("pos_obs"), dur=G.get("duration"), box=(G.get("box") or [None, None])[1]))
        rows.append(dict(kind=e.get("kind"), x=e.get("x"), glyphs=gs, unison=bool(e.get("unison"))))
    vo = cv.get("voices") or {}
    out.append(dict(i=i, bar=bar, codes=codes, text=text,
                    voices=dict(outcome=vo.get("outcome"), reason=vo.get("reason"), value=vo.get("value"),
                                detail={k: (vo.get("detail") or {}).get(k) for k in ("merged_quarters", "target_quarters", "stream_quarters", "separation", "rule_1_same_beat", "why")}),
                    events=rows))
json.dump(out, open(out_path, "w"), indent=0, default=str)
print("wrote", len(out))
