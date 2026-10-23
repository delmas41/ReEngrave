"""2.197 C11: what the MISSES share. For each in-bar truth item of a census json: success = the note Sean's head carries is written with the right accidental
(E2 == alter_right/elem_right); features: distance from the cell's left edge (staff spaces; a barline for cell>0), first event after the barline,
size (staff spaces), other-class boxes touching it, a neighbour accidental, system/staff/page; split by outcome stage of failure.
usage: c11_features.py CENSUS.json VIEW.json PDF UNIT [OUT.json]"""
import sys, json, collections, statistics, fitz
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, iou, fam
cen = json.load(open(sys.argv[1])); view = View(sys.argv[2]); UNIT = float(sys.argv[4])
doc = fitz.open(sys.argv[3]); cache = {}
def ink(pg):
    if pg not in cache:
        pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
        import numpy as np
        cache[pg] = np.frombuffer(pix.samples, dtype="uint8").reshape(pix.height, pix.width) < 128
    return cache[pg]
rows = []
for x in cen:
    if x["role"] != "3_in_bar": continue
    tb = x["box"]; pg = x["page"]; w = (tb[2] - tb[0]) / UNIT; h = (tb[3] - tb[1]) / UNIT
    ok = x.get("E2") == "alter_right/elem_right"
    if x["G"] == "not_boxed": stage = "GATHER:not_boxed"
    elif not x.get("offered_right_kind"): stage = "GATHER:right_class_not_offered"
    elif str(x.get("A", "")).startswith("abstained") or x.get("A") in (None, "no_accidental_row"): stage = "ADJUDICATE:" + str(x.get("A"))
    elif not ok: stage = "WRITE/CHOICE:" + str(x.get("E2"))
    else: stage = "ok"
    d = 4.0 / 600 * 600
    near = collections.Counter()
    for g in view.boxes.get(pg, ()):
        if g["box"] is tb: continue
        v = iou(tb, g["box"])
        # intersecting the truth box dilated by 0.2 sp, not itself an accidental of this ink
        eb = [tb[0] - 0.2 * UNIT, tb[1] - 0.2 * UNIT, tb[2] + 0.2 * UNIT, tb[3] + 0.2 * UNIT]
        if g["box"][2] < eb[0] or g["box"][0] > eb[2] or g["box"][3] < eb[1] or g["box"][1] > eb[3]: continue
        c = g["cls"]
        if fam(c) and v >= 0.3: continue
        fam_ = ("accidental(other)" if fam(c) else "notehead" if c.lower().startswith("notehead") else "rest" if c.lower().startswith("rest") else "slur/tie" if c.lower() in ("slur", "tie") else
                "beam/flag" if "beam" in c.lower() or "flag" in c.lower() else "ledger" if "ledger" in c.lower() else "barline/clef/time" if any(t in c.lower() for t in ("barline", "clef", "timesig", "brace")) else "other:" + c)
        near[fam_] += 1
    I = ink(pg); x0, y0, x1, y1 = [int(round(v)) for v in tb]
    rside = I[y0:y1, x1:x1 + 4].mean() if x1 + 4 <= I.shape[1] else 0.0
    lside = I[y0:y1, max(0, x0 - 4):x0].mean()
    rows.append(dict(src=x["src"], page=pg, system=x["system"], staff=x["staff"], cell=x["cell"], type=x["type"], ok=ok, stage=stage, w=round(w, 2), h=round(h, 2),
                     xl=x.get("x_from_cell_left_sp"), first_event=not any(((hh["box"][0] + hh["box"][2]) / 2 < tb[0]) for hh in [] ), touching=dict(near),
                     ink_right4px=round(float(rside), 2), ink_left4px=round(float(lside), 2), conf=(x["boxes_on_ink"][0]["conf"] if x["boxes_on_ink"] else None)))
json.dump(rows, open(sys.argv[5] if len(sys.argv) > 5 else "/dev/null", "w"), default=str)
def rate(f):
    a = [r for r in rows if f(r)]; return "%d/%d" % (sum(1 for r in a if not r["ok"]), len(a))
print("n in-bar items", len(rows), "failures", sum(1 for r in rows if not r["ok"]))
print("by stage", collections.Counter(r["stage"].split(":")[0] + ":" + r["stage"].split(":", 1)[-1][:34] for r in rows if not r["ok"]))
for name, f in (("xl<=1.5sp (just after the barline)", lambda r: r["xl"] is not None and r["xl"] <= 1.5 and r["cell"] > 0),
                ("xl 1.5-4", lambda r: r["xl"] is not None and 1.5 < r["xl"] <= 4), ("xl>4", lambda r: r["xl"] is not None and r["xl"] > 4),
                ("cell 0 (bar 1)", lambda r: r["cell"] == 0), ("touching a notehead box", lambda r: r["touching"].get("notehead")),
                ("touching slur/tie", lambda r: r["touching"].get("slur/tie")), ("touching beam/flag", lambda r: r["touching"].get("beam/flag")),
                ("touching ledger", lambda r: r["touching"].get("ledger")), ("neighbour accidental", lambda r: r["touching"].get("accidental(other)")),
                ("touching a barline/clef/time", lambda r: r["touching"].get("barline/clef/time")),
                ("natural", lambda r: r["type"] == "natural"), ("flat", lambda r: r["type"] == "flat"), ("sharp", lambda r: r["type"] == "sharp"),
                ("ink within 4px on the right", lambda r: r["ink_right4px"] > 0.5), ("no ink within 4px on the right", lambda r: r["ink_right4px"] <= 0.5),
                ("box h < 2.4 sp", lambda r: r["h"] < 2.4), ("box h >= 2.4 sp", lambda r: r["h"] >= 2.4)):
    print("  %-38s fail %s" % (name, rate(f)))
for t in ("src", "page"):
    print(" by", t, {k: rate(lambda r, k=k: r[t] == k) for k in sorted({r[t] for r in rows})})
print(" by (system,staff) with failures:", collections.Counter((r["page"], r["staff"]) for r in rows if not r["ok"]).most_common(8))
