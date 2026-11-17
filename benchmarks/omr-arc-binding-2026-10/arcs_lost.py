"""Arcs, ONE COMBINED STACK: every arc the two arms do not share, one by one, with its place, a class candidate and a look crop.

    python3 arcs_lost.py list  PLATE WORK_DIR [--pages 0,4,5]                 # one line per lost / gained / kind-changed arc
    python3 arcs_lost.py crops PLATE WORK_DIR OUT_DIR [--pages ...] [--cat lost,gained,kind]   # my look crops (heads ticked blue, ON arcs over it green, the ink run / detector span orange)

WORK_DIR = a `lane_report --out DIR/work` folder: PLATE.off|on.musicxml, PLATE.off|on.gathered.record.json, PLATE.on.extra.json (the page-arc binding verdicts).
Arcs are (kind, start glyph key, stop glyph key) read from the WRITTEN file (page-ink-2026-11/step2/arcs.arcs_of_xml); two arcs are the same when kind and BOTH note
columns agree (arcs.same_end: the same key or a chord mate / twin box within 0.8 head heights in x).

CLASS CANDIDATES (a first sort, never the verdict; the verdict is the crop):
  kind_change   an ON arc stands on the same two note columns with the other kind
  inside_page   an ON arc of the same staff covers at least 70% of the OFF arc's x extent (a detector twin / piece folded into one page arc)
  nothing_over  no ON arc of that staff overlaps it: a real loss, or not an arc
"""
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402

PDFS = {
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}


def load_record(path):
    rec = json.loads(pathlib.Path(path).read_text())
    obs = rec["observations"] if "observations" in rec else rec["record"]["observations"]
    boxes, rows, arcboxes = {}, {}, {}
    for o in obs:
        d = o.get("detail") or {}
        b = d.get("bbox_page_px")
        if b and str(o["subject"]).startswith("glyph/"):
            boxes.setdefault(o["subject"], dict(box=[float(v) for v in b]))
        if o["quantity"] == "page_arc":
            rows[o["id"]] = o
    return boxes, rows


def staff_of(key):
    return A.staff_of(key)


def cx(box):
    return (box[0] + box[2]) / 2.0


def arcs_of(work, plate, arm):
    return A.arcs_of_xml((pathlib.Path(work) / ("%s.%s.musicxml" % (plate, arm))).read_text())


def span(a, boxes):
    ba, bz = boxes.get(a["start"]), boxes.get(a["stop"])
    if not ba or not bz:
        return None
    x0, x1 = sorted([cx(ba["box"]), cx(bz["box"])])
    y = (ba["box"][1] + ba["box"][3] + bz["box"][1] + bz["box"][3]) / 4.0
    return x0, x1, y


def classify(plate, work, pages=None):
    work = pathlib.Path(work)
    boxes, rows = load_record(work / ("%s.on.gathered.record.json" % plate))
    boxes_off, _ = load_record(work / ("%s.off.gathered.record.json" % plate))
    for k, v in boxes_off.items():
        boxes.setdefault(k, v)
    off, on = arcs_of(work, plate, "off"), arcs_of(work, plate, "on")
    extra = json.loads((work / ("%s.on.extra.json" % plate)).read_text())
    runs = {}
    for v in extra:
        for r in v["detail"]["runs"]:
            if r["status"] == "written":
                runs[(r.get("start"), r.get("stop"))] = r

    def pg(a):
        s = staff_of(a["start"])
        return None if s is None else s[0]
    if pages is not None:
        off = [a for a in off if pg(a) in pages]
        on = [a for a in on if pg(a) in pages]
    lost, gained, kept = A.diff_arcs(off, on, boxes)
    out = []

    def ink_run_for(a):
        sp = span(a, boxes)
        if not sp:
            return None
        best = None
        for oid, o in rows.items():
            d = o["detail"]
            if o["value"] != "run" or not d.get("bbox_page_px"):
                continue
            b = d["bbox_page_px"]
            ov = min(b[2], sp[1]) - max(b[0], sp[0])
            if ov <= 0 or not (b[1] - 40 <= sp[2] <= b[3] + 40):
                continue
            if best is None or ov > best[0]:
                best = (ov, b, d.get("space_page_px", 32.0))
        return best

    def place(a, which):
        r = runs.get((a["start"], a["stop"])) or runs.get((a["stop"], a["start"]))
        if which == "on" and r is not None and r.get("row") in rows:
            return [float(v) for v in rows[r["row"]]["detail"]["bbox_page_px"]], "run"
        ir = ink_run_for(a)
        if ir:
            return [float(v) for v in ir[1]], "run_over"
        sp = span(a, boxes)
        if sp:
            return [sp[0], sp[2] - 40, sp[1], sp[2] + 40], "heads"
        return None, None

    for cat, arcset, side in (("lost", lost, "off"), ("gained", gained, "on")):
        for a in arcset:
            sp = span(a, boxes)
            if sp is None:
                continue
            s = staff_of(a["start"])
            other = on if cat == "lost" else off
            cls = "nothing_over"
            for b in other:
                if staff_of(b["start"]) != s:
                    continue
                if A.same_end(a["start"], b["start"], boxes) and A.same_end(a["stop"], b["stop"], boxes) and a["kind"] != b["kind"]:
                    cls = "kind_change"
                    break
            if cls == "nothing_over":
                for b in other:
                    sb = span(b, boxes)
                    if sb is None or staff_of(b["start"]) != s:
                        continue
                    ov = min(sb[1], sp[1]) - max(sb[0], sp[0])
                    if ov >= 0.7 * max(sp[1] - sp[0], 1.0) and abs(sb[2] - sp[2]) < 200:
                        cls = "inside_page" if cat == "lost" else "inside_old"
                        break
                    if cat == "gained" and ov > 0 and abs(sb[2] - sp[2]) < 200:
                        cls = "overlaps_old"
            bx, how = place(a, side)
            out.append(dict(cat=cat, cls=cls, kind=a["kind"], start=a["start"], stop=a["stop"], page=pg(a), staff=list(s[1:]) if s else None,
                            x0=round(sp[0]), x1=round(sp[1]), y=round(sp[2]), box=bx, how=how))
    # kind changes are listed once (lost side)
    return out, boxes, rows, kept, off, on


def draw(plate, it, boxes, others, out, pagecache):
    import cv2
    import fitz
    import numpy as np
    pno = it["page"]
    if (plate, pno) not in pagecache:
        d = fitz.open(PDFS[plate])
        pix = d[pno].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
        pagecache.clear()
        pagecache[(plate, pno)] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
    img = pagecache[(plate, pno)]
    sp = 32.0
    bx = it["box"]
    xs = [it["x0"], it["x1"]]
    ys = [it["y"] - 170, it["y"] + 70]
    X0, X1 = int(max(0, min(xs) - 6 * sp)), int(min(img.shape[1], max(xs) + 6 * sp))
    Y0, Y1 = int(max(0, min(ys) - 4.5 * sp)), int(min(img.shape[0], max(ys) + 4.5 * sp))
    im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
    def curve(a, col, lift, th):
        sb = span(a, boxes)
        if sb is None:
            return
        ba, bz = boxes[a["start"]]["box"], boxes[a["stop"]]["box"]
        pa = ((ba[0] + ba[2]) / 2 - X0, (ba[1] + ba[3]) / 2 - Y0 + lift)
        pz = ((bz[0] + bz[2]) / 2 - X0, (bz[1] + bz[3]) / 2 - Y0 + lift)
        h = min(70.0, 0.1 * abs(pz[0] - pa[0]) + 12)
        mid = ((pa[0] + pz[0]) / 2, min(pa[1], pz[1]) - h * 2)
        pts = [((1 - t) ** 2 * pa[0] + 2 * (1 - t) * t * mid[0] + t * t * pz[0], (1 - t) ** 2 * pa[1] + 2 * (1 - t) * t * mid[1] + t * t * pz[1]) for t in [i / 40.0 for i in range(41)]]
        cv2.polylines(im, [np.array(pts, np.int32)], False, col, th)
    for b in others:
        sb = span(b, boxes)
        if sb is None or sb[1] < X0 or sb[0] > X1 or abs(sb[2] - it["y"]) > 150:
            continue
        curve(b, (0, 170, 0) if b["kind"] == "slur" else (0, 0, 220), -60, 2)
    curve(it, (0, 140, 255), -60, 3)
    for k in (it["start"], it["stop"]):
        if k in boxes:
            b = boxes[k]["box"]
            cv2.rectangle(im, (int(b[0] - X0), int(b[1] - Y0)), (int(b[2] - X0), int(b[3] - Y0)), (255, 80, 0), 2)
    s = min(0.7, 1500.0 / im.shape[1])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), im)


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd, plate, work = a[0], a[1], a[2]
    pages = None
    if "--pages" in a:
        pages = {int(x) for x in a[a.index("--pages") + 1].split(",")}
    items, boxes, rows, kept, off, on = classify(plate, work, pages)
    if cmd == "list":
        c = collections.Counter((it["page"], it["cat"], it["cls"], it["kind"]) for it in items)
        for k, v in sorted(c.items()):
            print(k, v)
        print("kept (same kind, same two note columns):", len(kept), "| OFF arcs", len(off), "| ON arcs", len(on))
        for it in sorted(items, key=lambda i: (i["page"], i["cat"], i["cls"], i["x0"])):
            print(it["cat"], it["cls"], "p%d" % it["page"], it["kind"], "staff", it["staff"], "x", it["x0"], "-", it["x1"], "y", it["y"], it["how"])
    elif cmd == "crops":
        outd = pathlib.Path(a[3])
        outd.mkdir(parents=True, exist_ok=True)
        cats = a[a.index("--cat") + 1].split(",") if "--cat" in a else ["lost"]
        pc = {}
        idx = []
        for i, it in enumerate(sorted(items, key=lambda i: (i["page"], i["cat"], i["cls"], i["x0"])), 1):
            if it["cat"] not in cats or it["box"] is None:
                continue
            name = "%s-p%d-%s-%s-%03d.png" % (plate, it["page"], it["cat"], it["cls"], i)
            draw(plate, it, boxes, on if it["cat"] == "lost" else off, outd / name, pc)
            idx.append(name)
        print(len(idx), "crops ->", outd)
