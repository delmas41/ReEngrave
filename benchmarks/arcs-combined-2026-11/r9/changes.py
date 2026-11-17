"""2.305 r9 -- every arc the lane CHANGED (written ON before -> ON after, the same gather re-adjudicated): added, removed, or kind changed, with the ink
the reader held for it (a page run's points; a curve's boxes; for an arc the old box path wrote, the detector boxes it was paired from).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 changes.py BEFORE_PREFIX AFTER_PREFIX PLATE OUT.json
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import judge as J  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402


def arcs(pre):
    f = json.load(open(pre + ".facts.json"))
    sp = json.load(open(pre + ".spans.json"))
    chord_of, head = {}, None
    for h in f["written"]:
        if h.get("kind") != "note":
            continue
        if not h.get("chord"):
            head = h["rg"]
        chord_of[h["rg"]] = head if h.get("chord") else h["rg"]
    ck = lambda rg: chord_of.get(rg, rg)   # noqa: E731
    out = {}
    for k, a, b, _x, _y in J.xml_arcs(f["xml"], lambda r: None):
        if a and b:
            out.setdefault(frozenset((ck(a), ck(b))), []).append(k)
    spans = {}
    for s in sp["spans"]:
        spans.setdefault(frozenset((ck(s["a"]), ck(s["b"]))), []).append(s)
    return out, spans, f, sp, ck


INK_BOXES = []      # the individual boxes behind the last `ink_of` answer (a cap and a cup stay two boxes)


def ink_of(span, rec_runs, boxes, f, a, b):
    if span and span["src"] == "page_arc" and span.get("key", "").startswith("page_arc/"):
        pts = rec_runs.get(span["key"].split("/", 1)[1])
        if pts:
            INK_BOXES[:] = [[min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]]
            return INK_BOXES[0], "page run %s" % span["key"]
    if span and span["src"] == "curve" and span.get("key"):
        bs = [bx["box"] for bx in boxes if (bx.get("curve") or {}).get("curve") == span["key"] and bx["box"]]
        if bs:
            INK_BOXES[:] = [[min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs)]]
            return INK_BOXES[0], "curve %s" % span["key"]
    # old paths / unknown: the detector arc boxes over the stretch between the two notes, on their staff
    ga, gb = f["glyphs"][a]["box"], f["glyphs"][b]["box"]
    x0, x1 = min(ga[0], gb[0]), max(ga[2], gb[2])
    st = {"staff/%s" % "/".join(k.split("/")[1:4]) for k in (a, b)}
    bs = []
    for bx in boxes:
        own = bx["owner"] if isinstance(bx["owner"], str) else "staff/%s" % "/".join(bx["sub"].split("/")[1:4])
        if bx["box"] and bx["kind"] in ("slur", "tie") and own in st and not bx["replaced"]:
            sp = 32.0 if a.startswith("glyph/0/") else 26.0          # (a crop guide only: Brahms / Litolff staff space, px)
            ys = (ga[1] + ga[3]) / 2.0, (gb[1] + gb[3]) / 2.0
            inside = bx["box"][0] >= x0 - sp and bx["box"][2] <= x1 + sp
            near_y = min(abs((bx["box"][1] + bx["box"][3]) / 2.0 - y) for y in ys) <= 3 * sp
            if inside and near_y:
                bs.append(bx["box"])
    if bs:
        INK_BOXES[:] = [list(x) for x in bs]
        return [min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs)], "detector boxes (old path)"
    return None, "no ink found"


def main():
    bpre, apre, plate, out = sys.argv[1:5]
    B, Bs, bf, bsp, bck = arcs(bpre)
    A, As, af, asp, ack = arcs(apre)
    rec = load_record(apre + ".record.json")["record"]
    runs = {o["id"]: (o.get("detail") or {}).get("points") for o in rec["observations"] if o["quantity"] == "page_arc" and o.get("value") == "run"}
    lines = {o["subject"]: o.get("value") for o in rec["observations"] if o["quantity"] == "staff_lines"}
    del rec
    # an old tie pair's ink is exactly the detector boxes `Q.TIE_PAIR` named it from (before arm)
    brec = load_record(bpre + ".record.json")["record"]
    abox = {o["subject"]: (o.get("detail") or {}).get("bbox_page_px") for o in brec["observations"] if o["quantity"] == "arc_box"}
    tie_boxes = {}
    for v in brec["verdicts"]:
        if v["quantity"] == "tie_pair" and v["outcome"] == "decided" and isinstance(v.get("value"), dict):
            k = frozenset((bck(str(v["value"]["start"])), bck(str(v["value"]["stop"]))))
            if abox.get(v["subject"]):
                tie_boxes.setdefault(k, []).append(abox[v["subject"]])
    del brec
    # the page reader's OWN ink at each place (Sean 2026-11-16, tile rule: the box is always the page reader's run, never a detector box)
    arec = load_record(apre + ".record.json")["record"]
    pruns = {o["id"]: (o.get("detail") or {}).get("points") or [] for o in arec["observations"] if o["quantity"] == "page_arc" and o.get("value") == "run"}
    pnames = {}
    for v in arec["verdicts"]:
        if v["quantity"] == "page_arc_binding":
            for x in (v.get("detail") or {}).get("runs") or ():
                nm = {ack(str(n)) for n in (x.get("start"), x.get("stop"), (x.get("left") or {}).get("head"), (x.get("right") or {}).get("head")) if n}
                pnames.setdefault(x["row"], set()).update(nm)
    del arec

    def page_run_at(a, b, ga, gb):
        both = [r for r, nm in pnames.items() if {ack(a), ack(b)} <= nm and pruns.get(r)]
        if both:
            pts = pruns[both[0]]
            return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)], both[0]
        x0, x1 = min(ga[0], gb[0]), max(ga[2], gb[2])
        ys = [(ga[1] + ga[3]) / 2.0, (gb[1] + gb[3]) / 2.0]
        sp = 32.0 if a.startswith("glyph/0/") else 15.75
        best = None
        for r, pts in pruns.items():
            inside = [p for p in pts if x0 <= p[0] <= x1 and min(abs(p[1] - y) for y in ys) <= 2.5 * sp]
            if pts and len(inside) >= 0.6 * len(pts) and (best is None or len(inside) > best[0]):
                best = (len(inside), r)
        if best:
            pts = pruns[best[1]]
            return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)], best[1]
        return None, None

    rows = []
    for key in sorted(set(B) | set(A), key=lambda k: sorted(k)):
        kb, ka = sorted(B.get(key, [])), sorted(A.get(key, []))
        if kb == ka:
            continue
        a, b = sorted(key) if len(key) == 2 else (next(iter(key)),) * 2
        if ka and not kb:
            change, sp_, f, sp = "added", (As.get(key) or [None])[0], af, asp
        elif kb and not ka:
            change, sp_, f, sp = "removed", (Bs.get(key) or [None])[0], bf, bsp
        else:
            change, sp_, f, sp = "changed %s -> %s" % (kb, ka), (As.get(key) or [None])[0], af, asp
        INK_BOXES[:] = []
        ink, why = ink_of(sp_, runs if change != "removed" else {}, sp["arc_boxes"], f, a, b)
        if (sp_ or {}).get("src") in ("record_tie", "curve_tie") and change == "removed" and tie_boxes.get(key):
            bs = tie_boxes[key]
            INK_BOXES[:] = [list(x) for x in bs]
            ink, why = [min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs)], "the tie pair's own boxes"
        if change == "removed" and sp_ and sp_["src"] == "page_arc":
            ink, why = None, "page run (before)"
        prb, prid = page_run_at(a, b, f["glyphs"][a]["box"], f["glyphs"][b]["box"])
        rows.append(dict(plate=plate, change=change, page_run_box=prb, page_run=prid, a=a, b=b, before=kb, after=ka, src=(sp_ or {}).get("src"), ink=ink, ink_boxes=[list(x) for x in INK_BOXES] if ink else [], ink_from=why, staff_lines=lines.get("staff/%s" % "/".join(a.split("/")[1:4])),
                         page=int(a.split("/")[1]), a_box=f["glyphs"][a]["box"], b_box=f["glyphs"][b]["box"]))
    json.dump(rows, open(out, "w"), indent=0)
    for r in rows:
        print(r["change"], r["a"], r["b"], r["src"], r["ink_from"])
    print(len(rows), "changes")


if __name__ == "__main__":
    main()
