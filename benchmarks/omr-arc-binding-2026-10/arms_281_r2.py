"""2.281 r2: arcs gained / lost between the two arms of a replay (OMR_ARC_MEETING_AT_HEAD 0 -> 1) on today's main, with the page place of each, and blind tiles.

    python3 arms_281_r2.py list  PLATE GATHERED_RECORD WORK_DIR            # WORK_DIR = lane_report --out DIR/work (plate.off|on.musicxml, .extra.json)
    python3 arms_281_r2.py tiles PLATE GATHERED_RECORD WORK_DIR OUT_DIR KEY_JSON [--n 12] [--seed N] [--skip KEYS.json]

An arc is (kind, start glyph key, stop glyph key) read from the WRITTEN file (page-ink-2026-11/step2/arcs.arcs_of_xml); its box is the page-ink run the binder wrote it from
(the run's `Q.PAGE_ARC` row, via the arm's `.extra.json`), or, for a detector-box arc no run witnesses, the span of its two heads.  Tiles: one staff strip, ONE thin orange box,
nothing else of ours; the key (which arm, what we expect) goes to KEY_JSON, never into the tile folder.
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402

PDFS = {
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}


def load_record(path):
    rec = json.load(open(path))
    obs = rec["observations"] if "observations" in rec else rec["record"]["observations"]
    boxes, rows = {}, {}
    for o in obs:
        d = o.get("detail") or {}
        b = d.get("bbox_page_px")
        if b and str(o["subject"]).startswith("glyph/"):
            boxes.setdefault(o["subject"], [float(v) for v in b])
        if o["quantity"] == "page_arc":
            rows[o["id"]] = o
    return boxes, rows


def arms(work, plate):
    out = {}
    for arm in ("off", "on"):
        xml = (pathlib.Path(work) / ("%s.%s.musicxml" % (plate, arm))).read_text()
        extra = json.load(open(pathlib.Path(work) / ("%s.%s.extra.json" % (plate, arm))))
        runs = {}
        for v in extra:
            for r in v["detail"]["runs"]:
                if r["status"] == "written":
                    runs[(r.get("start"), r.get("stop"))] = r
        out[arm] = ({(a["kind"], a["start"], a["stop"]) for a in A.arcs_of_xml(xml)}, runs)
    return out


def place(arc, runs, rows, boxes):
    kind, s, z = arc
    r = runs.get((s, z)) or runs.get((z, s))
    if r is not None and r.get("row") in rows:
        b = rows[r["row"]]["detail"]["bbox_page_px"]
        return [float(v) for v in b], "run", float(rows[r["row"]]["detail"].get("space_page_px", 32))
    if s in boxes and z in boxes:
        a, c = boxes[s], boxes[z]
        return [min(a[0], c[0]), min(a[1], c[1]), max(a[2], c[2]), max(a[3], c[3])], "heads", 32.0
    return None, None, 32.0


def diff(plate, rec, work):
    boxes, rows = load_record(rec)
    a = arms(work, plate)
    off, on = a["off"][0], a["on"][0]
    items = []
    for cat, arcset, runs in (("gained", on - off, a["on"][1]), ("lost", off - on, a["off"][1]), ("same", on & off, a["on"][1])):
        for arc in sorted(arcset):
            b, how, sp = place(arc, runs, rows, boxes)
            if b is None:
                continue
            items.append(dict(cat=cat, kind=arc[0], start=arc[1], stop=arc[2], box=b, how=how, sp=sp, page=int(arc[1].split("/")[1]),
                              x=round((b[0] + b[2]) / 2), y=round((b[1] + b[3]) / 2)))
    return items, boxes


def draw(plate, it, boxes, out):
    import cv2
    import fitz
    import numpy as np
    d = fitz.open(PDFS[plate])
    pix = d[it["page"]].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
    bx, sp = it["box"], it["sp"]
    hs = [boxes[k] for k in (it["start"], it["stop"]) if k in boxes]
    xs = [bx[0], bx[2]] + [h[0] for h in hs] + [h[2] for h in hs]
    ys = [bx[1], bx[3]] + [h[1] for h in hs] + [h[3] for h in hs]
    X0, X1 = int(max(0, min(xs) - 7 * sp)), int(min(img.shape[1], max(xs) + 7 * sp))
    Y0, Y1 = int(max(0, min(ys) - 4.5 * sp)), int(min(img.shape[0], max(ys) + 4.5 * sp))
    im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im, (int(bx[0] - X0 - 3), int(bx[1] - Y0 - 3)), (int(bx[2] - X0 + 3), int(bx[3] - Y0 + 3)), (0, 140, 255), 2)
    s = min(0.7, 1400.0 / im.shape[1])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), im)


if __name__ == "__main__":
    cmd, plate, rec, work = sys.argv[1:5]
    items, boxes = diff(plate, rec, work)
    if cmd == "list":
        for it in items:
            if it["cat"] != "same":
                print(it["cat"], "p%d" % it["page"], it["kind"], "x", it["x"], "y", it["y"], it["start"], "->", it["stop"], it["how"])
        import collections
        print(collections.Counter((it["page"], it["cat"], it["kind"]) for it in items))
    else:
        out, keyf = pathlib.Path(sys.argv[5]), pathlib.Path(sys.argv[6])
        n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
        seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 2281
        skip = set(json.load(open(sys.argv[sys.argv.index("--skip") + 1]))) if "--skip" in sys.argv else set()
        out.mkdir(parents=True, exist_ok=True)
        rnd = random.Random(seed)
        pools = {c: [i for i in items if i["cat"] == c and (i["start"], i["stop"]) not in skip] for c in ("gained", "lost", "same")}
        for v in pools.values():
            rnd.shuffle(v)
        pick = pools["gained"][:8] + pools["lost"][:4] + pools["same"][:3]
        pick = pick[:n]
        rnd.shuffle(pick)
        key = []
        for i, it in enumerate(pick, 1):
            name = "%02d.png" % i
            draw(plate, it, boxes, out / name)
            key.append(dict(tile=name, plate=plate, **{k: it[k] for k in ("page", "cat", "kind", "start", "stop", "how", "x", "y")}))
        keyf.write_text(json.dumps(dict(question="Is the boxed arc one arc, does it start and stop on these notes, and is it a tie or a slur?", tiles=key), indent=1))
        print(len(key), "tiles ->", out)
