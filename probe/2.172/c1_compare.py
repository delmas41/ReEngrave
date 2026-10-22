"""2.172 (c)(d)(e)(f): compare the OFF and ON records and exports of one plate. usage: c1_compare.py lit|bra  -> prints, and data/compare_<plate>.json
 GATHER: every production (reader `detector`) glyph box of OFF is in ON with the same class/box/score (kept symbols dropped = 0), new boxes by view/family.
 ADJUDICATE: for the glyphs both records carry, verdicts that changed (quantity, outcome).
 EXPORT: notes / rests / unread-bar marks in the musicxml, bars marked red, the log's accounting lines.
 NEW-BOX BARS: the bars (page/system/staff/cell) of the new view boxes and whether OFF held that bar out."""
import collections
import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "rec172"
plate = sys.argv[1]
ARM = sys.argv[2] if len(sys.argv) > 2 else "on"


def load(arm):
    d = json.loads(open(REC / ("%s-%s.record.json" % (plate, arm))).read())
    R = d["record"]
    glyphs = {}
    for o in R["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/"):
            det = o.get("detail") or {}
            glyphs[o["subject"]] = (o.get("reader"), o["value"][0], tuple(o["value"][1:5]), round(o.get("score") or 0, 4), det)
    ver = {}
    for v in R["verdicts"]:
        if v.get("subject", "").startswith("glyph/"):
            ver.setdefault(v["subject"], {})[v["quantity"]] = (v.get("outcome"), v.get("reason"), str(v.get("value"))[:60])
    return glyphs, ver


def mx(arm):
    t = ET.parse(REC / ("%s-%s.musicxml" % (plate, arm)))
    notes = rests = 0
    for n in t.getroot().iter("note"):
        if n.find("rest") is not None:
            rests += 1
        else:
            notes += 1
    red = sum(1 for e in t.getroot().iter() if (e.get("color") or "").upper() == "#D00000")
    return notes, rests, red


go, vo = load("off")
gn, vn = load(ARM)
prod_off = {k: v for k, v in go.items() if v[0] == "detector"}
missing = [k for k, v in prod_off.items() if gn.get(k, (None,))[:4] != v[:4]]
print("OFF production boxes", len(prod_off), "-> missing or changed in ON:", len(missing))
new = {k: v for k, v in gn.items() if v[0] == "yolo_detector_view"}
print("ON new view boxes", len(new), dict(collections.Counter((v[4].get("view"), v[4].get("family")) for v in new.values())))
other_new = [k for k in gn if k not in go and gn[k][0] != "yolo_detector_view"]
print("other glyphs only in ON (not view-sourced):", len(other_new))
changed = collections.Counter()
nchg = 0
for k, qs in vo.items():
    if k not in gn:
        continue
    for q, val in qs.items():
        nv = vn.get(k, {}).get(q)
        if nv != val:
            changed[(q, val[0], (nv or ("none",))[0])] += 1
            nchg += 1
print("verdicts on OFF's glyphs that differ in ON:", nchg)
for k, v in changed.most_common(14):
    print("   ", k, v)
print("notes, rests, red-marked elements  OFF", mx("off"), " ON(%s)" % ARM, mx(ARM))
cell_of = lambda s: "/".join(s.split("/")[1:5])
bars = collections.Counter(cell_of(k) for k in new)
print("bars with new boxes:", len(bars))
json.dump(dict(new={k: dict(cls=v[1], box=v[2], conf=v[3], view=v[4].get("view"), fam=v[4].get("family"), pg=v[4].get("bbox_page_px")) for k, v in new.items()},
               verdict_changes={str(k): v for k, v in changed.items()}, missing=missing),
          open(str(ROOT) + "/probe/2.172/data/compare_%s%s.json" % (plate, "" if ARM == "on" else "_" + ARM), "w"))
