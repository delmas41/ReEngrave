"""2.274 step 2 hold-out, re-run on the combined stack's tree: the SAME measure as FINDINGS "2.274 step 2 ROUND 2" (criteria 1 and 2), from real gathers (both flags OFF vs ON).

    python3 holdout_runs.py summary PLATE:WORK:pages [...]                 # pools, statuses, abstain reasons
    python3 holdout_runs.py pick SEED OUT.json PLATE:WORK:pages [...]      # 10 replaced + 10 new + 10 unchanged WRITTEN runs (pick30's draw)
    python3 holdout_runs.py crops IN.json OUT_DIR                           # my look crops: run trace (orange), bound heads (green start / magenta stop), OFF arcs over it (blue)
Criterion 1: of 30 seeded written runs my look finds start and stop on the right notes in >= 27. Criterion 2: of the replaced runs (<= 20) at most 2 were right in OFF and are wrong or
gone ON; and no OFF arc that no written run overlaps is lost.
"""
import collections
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
sys.path.insert(0, str(HERE))
import arcs as A  # noqa: E402
import arcs_lost as L  # noqa: E402


def load(plate, work, pages):
    work = pathlib.Path(work)
    boxes, rows = L.load_record(work / ("%s.on.gathered.record.json" % plate))
    boxes_off, _ = L.load_record(work / ("%s.off.gathered.record.json" % plate))
    for k, v in boxes_off.items():
        boxes.setdefault(k, v)
    off = A.arcs_of_xml((work / ("%s.off.musicxml" % plate)).read_text())
    extra = [v for v in json.loads((work / ("%s.on.extra.json" % plate)).read_text()) if int(v["subject"].split("/")[1]) in pages]
    runs = {}
    for o in rows.values():
        if o["value"] == "run":
            runs[(L.A.staff_of and int(o["subject"].split("/")[1]), o["detail"]["ordinal"])] = o["detail"]
    return off, extra, boxes, runs, rows


def records(plate, work, pages):
    off, extra, boxes, runs, rows = load(plate, work, pages)
    # A.per_run reads span_of(box) = boxes[key]["box"]
    recs = A.per_run(extra, off, boxes, runs)
    for r in recs:
        r["plate"] = plate
        r["work"] = str(work)
    return recs, off, boxes, runs


def main():
    a = sys.argv[1:]
    if a[0] in ("summary", "pick"):
        specs = a[1:] if a[0] == "summary" else a[3:]
        allrecs = []
        for spec in specs:
            plate, work, pg = spec.split(":")
            pages = {int(x) for x in pg.split(",")}
            recs, off, boxes, runs = records(plate, work, pages)
            allrecs += recs
            c = collections.Counter(r["status"] for r in recs)
            w = [r for r in recs if r["status"] == "written"]
            print(plate, sorted(pages), "witnessed runs", len(recs), dict(c), "| written vs OFF", dict(collections.Counter(r["off"] for r in w)),
                  "| abstain why", dict(collections.Counter(r["why"] for r in recs if r["status"] == "abstained")))
        if a[0] == "pick":
            pool = {"replaced": [], "new": [], "unchanged": []}
            for r in allrecs:
                if r["status"] != "written":
                    continue
                cat = {"whole": "unchanged", "none": "new"}.get(r["off"], "replaced")
                pool[cat].append(dict(category=cat, plate=r["plate"], work=r["work"], page=r["page"], run=r["ordinal"], piece=r.get("piece"), kind=r["kind"], off=r["off"],
                                      start=r["start"], stop=r["stop"], x0=r["x0"], x1=r["x1"], staff=list(r["staff"]),
                                      off_overlap=[(o["kind"], o["start"], o["stop"]) for o in r["off_overlap"]]))
            rng = random.Random(int(a[1]))
            pick = []
            for cat in ("replaced", "new", "unchanged"):
                items = pool[cat]
                rng.shuffle(items)
                pick += items[:10]
            rng.shuffle(pick)
            for i, it in enumerate(pick, 1):
                it["n"] = i
            json.dump(dict(seed=int(a[1]), pools={k: len(v) for k, v in pool.items()}, sample=pick, replaced_all=pool["replaced"]), open(a[2], "w"), indent=1)
            print({k: len(v) for k, v in pool.items()}, "picked", len(pick))
    elif a[0] == "crops":
        import cv2
        import fitz
        import numpy as np
        d = json.load(open(a[1]))
        outd = pathlib.Path(a[2])
        outd.mkdir(parents=True, exist_ok=True)
        cache = {}
        items = d["sample"] if "--all-replaced" not in a else d["replaced_all"]
        for i, it in enumerate(items, 1):
            plate, work, page = it["plate"], it["work"], it["page"]
            if (plate, work) not in cache:
                cache.clear()
                cache[(plate, work)] = load(plate, work, {page})
            off, extra, boxes, runs, rows = cache[(plate, work)]
            if (plate, work, page) not in cache:
                _off, _e, _b, runs2, _r = load(plate, work, {page})
                cache[(plate, work, page)] = runs2
            row = runs.get((page, it["run"]))
            if row is None:
                continue
            fk = ("img", plate, page)
            if fk not in cache:
                for k in [k for k in cache if k[0] == "img"]:
                    del cache[k]
                dd = fitz.open(L.PDFS[plate])
                pix = dd[page].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
                cache[fk] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
            img = cache[fk]
            pts = np.array(row["points"], float)
            sp = 32.0
            hb = [boxes[k]["box"] for k in (it["start"], it["stop"]) if k in boxes]
            xs = list(pts[:, 0]) + [b[0] for b in hb] + [b[2] for b in hb]
            ys = list(pts[:, 1]) + [b[1] for b in hb] + [b[3] for b in hb]
            X0, X1 = int(max(0, min(xs) - 5 * sp)), int(min(img.shape[1], max(xs) + 5 * sp))
            Y0, Y1 = int(max(0, min(ys) - 3 * sp)), int(min(img.shape[0], max(ys) + 4 * sp))
            im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
            cv2.polylines(im, [np.array([(p[0] - X0, p[1] - Y0) for p in pts], np.int32)], False, (0, 140, 255), 2)
            for k, col in ((it["start"], (0, 160, 0)), (it["stop"], (200, 0, 200))):
                if k in boxes:
                    b = boxes[k]["box"]
                    cv2.rectangle(im, (int(b[0] - X0), int(b[1] - Y0)), (int(b[2] - X0), int(b[3] - Y0)), col, 3)
            for kind, s0, s1 in it["off_overlap"]:
                if s0 in boxes and s1 in boxes:
                    ba, bz = boxes[s0]["box"], boxes[s1]["box"]
                    cv2.line(im, (int((ba[0] + ba[2]) / 2 - X0), int(ba[3] - Y0 + 10)), (int((bz[0] + bz[2]) / 2 - X0), int(bz[3] - Y0 + 10)), (230, 120, 0) if kind == "slur" else (0, 0, 220), 2)
            s = min(0.8, 1000.0 / im.shape[1])
            im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            cv2.rectangle(im, (0, 0), (im.shape[1], 16), (255, 255, 255), -1)
            cv2.putText(im, "%02d %s p%d run%s %s %s OFF=%s" % (it.get("n", i), it["plate"], page, it["run"], it["category"], it["kind"], it["off"]), (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
            cv2.imwrite(str(outd / ("%02d.png" % it.get("n", i))), im)
        print("crops ->", outd)


if __name__ == "__main__":
    main()
