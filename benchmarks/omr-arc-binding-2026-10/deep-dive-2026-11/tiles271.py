"""Sean's 2.271 closest-note tiles 2,4,5,9,10,12 settled from the record (measure only): for each tile the pair the 2.271 r1 arm wrote -> the curve
that bound it, whole or piece, how many arcs were written over that ink, and what the arm without the flag wrote. python3 tiles271.py"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ledger as LG
import written as W

D = pathlib.Path("scratch/dd")
ANS = json.load(open("benchmarks/omr-arc-binding-2026-10/answers-2.271-closest-r1.json"))["answers"]
WANT = {2, 4, 5, 9, 10, 12}


def load(plate, arm):
    dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, arm))))
    xml = (D / ("%s.%s.musicxml" % (plate, arm))).read_text()
    res = LG.build(dump, xml)
    return dump, res, W.parse(xml)


cache = {}
out = []
for a in ANS:
    if a["tile"] not in WANT:
        continue
    k = a["key"]
    plate = k["plate"]
    if plate not in cache:
        cache[plate] = {arm: load(plate, arm) for arm in ("r1closest", "r1off")}
    dump, res, wr = cache[plate]["r1closest"]
    dump0, res0, wr0 = cache[plate]["r1off"]
    pair = (k["start"], k["stop"])
    rows = [r for r in res["rows"] if r.get("pair") == pair or (r.get("binding") or {}).get("start") == pair[0] and (r.get("binding") or {}).get("stop") == pair[1]]
    print("=== tile %d  %s p%d %s %s -> %s | Sean: %s" % (a["tile"], plate, k["page"], k["kind"], pair[0], pair[1], a["sean"][:110]))
    print("   written in r1closest: slur=%s tie=%s ; in r1off: slur=%s tie=%s" % (pair in set(wr["slurs"]), pair in set(wr["ties"]), pair in set(wr0["slurs"]), pair in set(wr0["ties"])))
    for r in rows:
        pb = r.get("binding") or {}
        print("   curve %s pieces=%d classes=%s has_curve=%s fate=%s" % (r["curve"], r["n_pieces"], r["classes"], r["has_curve"], r["fate"]))
        print("      trace x %s..%s y %s,%s  stroke_left=%s stroke_right=%s sp=%s  piece box=%s" % (
            r["x_left"], r["x_right"], r["y_left"], r["y_right"], r.get("stroke_left"), r.get("stroke_right"), r["sp"], [round(x) for x in r["box"]]))
        print("      left=%s" % json.dumps(pb.get("left")))
        print("      right=%s" % json.dumps(pb.get("right")))
        # neighbours on the staff: other curves whose ends meet this one's ends
        for o in res["rows"]:
            if o is r or o["staff"] != r["staff"] or o.get("x_left") is None or o["fate"] == "not_an_arc":
                continue
            sp = r["sp"]
            dxr = (o["x_left"] - r["x_right"]) / sp
            dxl = (r["x_left"] - o["x_right"]) / sp
            dyr = abs(o["y_left"] - r["y_right"]) / sp
            dyl = abs(o["y_right"] - r["y_left"]) / sp
            if (-1 <= dxr <= 4 and dyr <= 2.5) or (-1 <= dxl <= 4 and dyl <= 2.5):
                print("      NEIGHBOUR curve %s fate=%s trace x %s..%s classes=%s via_closest=%s/%s dxr=%.1f dxl=%.1f" % (
                    o["curve"], o["fate"], o["x_left"], o["x_right"], o["classes"], (o.get("binding") or {}).get("left", {}).get("via_closest"),
                    (o.get("binding") or {}).get("right", {}).get("via_closest"), dxr, dxl))
    out.append(dict(tile=a["tile"], plate=plate, page=k["page"], pair=pair, curves=[r["curve"] for r in rows],
                    boxes=[r["box"] for r in rows], sp=[r["sp"] for r in rows], extents=[(r["x_left"], r["x_right"]) for r in rows]))
json.dump(out, open(D / "tiles271.json", "w"), default=str)
