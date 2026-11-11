"""Arcs, ONE COMBINED STACK: the 12 blind tiles for Sean, by a stated seeded rule.

    python3 arcs_tiles.py OUT_DIR KEY_JSON LOOKS_JSON SEED PLATE:WORK:pages [PLATE:WORK:pages ...]

RULE (fixed before the draw): (1) every lost arc my look called "real" (LOOKS_JSON maps "plate:p<page>:<start>><stop>" to a class; "real_lost" counts) and every kind change,
in page order; (2) then GAINED arcs (written ON, not OFF), drawn with random.Random(SEED), up to 10 in all; (3) then 2 UNCHANGED controls (an arc both arms write, same kind,
same two note columns), drawn with the same generator. At most 12 tiles.

One tile = one staff strip cut from the printed page (600 dpi), 6 spaces either side of the arc and its two notes, ONE thin orange box round the arc's own ink (the page-ink run; for a
lost arc the run that stands over it, else the detector box), nothing else drawn. The key (which arm, what we expect) is written to KEY_JSON, never into OUT_DIR.
Question: "Is the boxed mark one arc? Does it start and stop on these notes? Tie or slur?"
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
import arcs_lost as L  # noqa: E402


def strip(plate, it, boxes, out, pagecache):
    import cv2
    import fitz
    import numpy as np
    pno = it["page"]
    if (plate, pno) not in pagecache:
        d = fitz.open(L.PDFS[plate])
        pix = d[pno].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
        pagecache.clear()
        pagecache[(plate, pno)] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
    img = pagecache[(plate, pno)]
    sp = 32.0
    bx = it["box"]
    hs = [boxes[k]["box"] for k in (it["start"], it["stop"]) if k in boxes]
    xs = [bx[0], bx[2]] + [h[0] for h in hs] + [h[2] for h in hs]
    ys = [bx[1], bx[3]] + [h[1] for h in hs] + [h[3] for h in hs]
    X0, X1 = int(max(0, min(xs) - 6 * sp)), int(min(img.shape[1], max(xs) + 6 * sp))
    Y0, Y1 = int(max(0, min(ys) - 3.5 * sp)), int(min(img.shape[0], max(ys) + 3.5 * sp))
    im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im, (int(bx[0] - X0 - 3), int(bx[1] - Y0 - 3)), (int(bx[2] - X0 + 3), int(bx[3] - Y0 + 3)), (0, 140, 255), 2)
    s = min(0.7, 1400.0 / im.shape[1])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), im)


def main():
    out = pathlib.Path(sys.argv[1])
    keyf = pathlib.Path(sys.argv[2])
    looks = json.load(open(sys.argv[3])) if sys.argv[3] != "-" else {}
    seed = int(sys.argv[4])
    pool_real, pool_gain, pool_same = [], [], []
    boxes_by_plate = {}
    for spec in sys.argv[5:]:
        plate, work, pg = spec.split(":")
        pages = {int(x) for x in pg.split(",")}
        items, boxes, rows, kept, off, on = L.classify(plate, work, pages)
        boxes_by_plate[(plate, work)] = boxes
        for it in items:
            it["plate"], it["work"] = plate, work
            k = "%s:p%d:%s>%s" % (plate, it["page"], it["start"], it["stop"])
            it["k"] = k
            if it["box"] is None:
                continue
            if it["cat"] == "lost" and (it["cls"] == "kind_change" or looks.get(k) == "real_lost"):
                pool_real.append(it)
            elif it["cat"] == "gained" and it["cls"] != "kind_change":
                pool_gain.append(it)
        for a, b in kept:
            sp = L.span(b, boxes)
            if sp is None:
                continue
            bx, how = None, None
            r = None
            pool_same.append(dict(cat="same", cls="same", kind=b["kind"], start=b["start"], stop=b["stop"], page=L.staff_of(b["start"])[0], x0=round(sp[0]), x1=round(sp[1]), y=round(sp[2]),
                                  box=[sp[0], sp[2] - 45, sp[1], sp[2] + 45], how="heads", plate=plate, work=work, k="%s:same:%s>%s" % (plate, b["start"], b["stop"])))
    rnd = random.Random(seed)
    pool_real.sort(key=lambda i: (i["plate"], i["page"], i["x0"]))
    rnd.shuffle(pool_gain)
    rnd.shuffle(pool_same)
    pick = pool_real[:12]
    pick += pool_gain[:max(0, 10 - len(pick))]
    pick = pick[:10] + pool_same[:2]
    rnd.shuffle(pick)
    out.mkdir(parents=True, exist_ok=True)
    key = []
    pc = {}
    for i, it in enumerate(pick, 1):
        name = "%02d.png" % i
        strip(it["plate"], it, boxes_by_plate.get((it["plate"], it["work"])) or {}, out / name, pc)
        key.append(dict(tile=name, plate=it["plate"], page=it["page"], cat=it["cat"], cls=it["cls"], kind=it["kind"], start=it["start"], stop=it["stop"], x=[it["x0"], it["x1"]], y=it["y"], how=it["how"]))
    keyf.write_text(json.dumps(dict(question="Is the boxed mark one arc? Does it start and stop on these notes? Tie or slur?", seed=seed,
                                    rule="all real-lost + kind-changed first, then gained (seeded), then 2 unchanged controls (seeded)", tiles=key), indent=1))
    print(len(key), "tiles ->", out, "| real-lost pool", len(pool_real), "gained pool", len(pool_gain), "same pool", len(pool_same))


if __name__ == "__main__":
    main()
