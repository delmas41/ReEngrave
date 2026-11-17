"""2.281: 12 blind tiles for Sean on what OMR_ARC_MEETING_AT_HEAD changes.  One staff per tile, ONE thin orange box round the page-ink run the file writes as an arc (the written file's
arc, drawn at its own place), nothing else of ours.  Question for every tile: "Is the boxed arc one arc, and which two notes does it join?"  The key (which arm, what we expect) is written to
out/print/2.281/key.json, NEVER into the tile folder.

    python3 tiles_281.py ARMS_DIR_BRAHMS ARMS_DIR_LITOLFF [--seed N]

Mix (seeded): up to 7 runs the flag turns from refused (`continues_in_another_curve`) into written, 3 written the same in both arms (control: the flag must not move them), 2 runs
that STAY refused with the flag on (control: the refusal is right if the box is half of a longer arc).
"""
import json
import pathlib
import random
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "print" / "2.281" / "tiles"
KEYF = ROOT / "out" / "print" / "2.281" / "key.json"
PDFS = {
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
CACHE = {}


def page_img(plate, page):
    k = (plate, page)
    if k not in CACHE:
        import fitz
        d = fitz.open(PDFS[plate])
        pix = d[page].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
        CACHE[k] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w).copy()
    return CACHE[k]


def load(path):
    rec = json.load(open(path))
    obs = rec["observations"]
    boxes = {}
    for o in obs:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and str(o["subject"]).startswith("glyph/"):
            boxes.setdefault(o["subject"], [float(v) for v in b])
    rows = {o["id"]: o for o in obs if o["quantity"] == "page_arc" and o["value"] == "run"}
    runs = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "page_arc_binding" and v.get("detail"):
            pg = str(v["subject"])
            for e in v["detail"]["runs"]:
                runs[(pg, e["ordinal"], e.get("piece"))] = e
    return boxes, rows, runs


def classify(base_dir, plate):
    """-> list of dict(plate, page, ordinal, why, bbox, staff, start/stop heads)"""
    wb, wr, wruns = load(pathlib.Path(base_dir) / ("%s.write.record.json" % plate))
    mb, mr, mruns = load(pathlib.Path(base_dir) / ("%s.meet.record.json" % plate))
    out = []
    for k, m in mruns.items():
        w = wruns.get(k)
        if w is None:
            continue
        cont = lambda e: any((u or {}).get("unbound") == "continues_in_another_curve" for u in (e.get("unbound") or {}).values())
        if not m.get("witnesses") and not (w["status"] == "abstained" and m["status"] == "abstained" and cont(w) and cont(m)):
            continue
        row = mr.get(m["row"])
        if row is None:
            continue
        pg = int(k[0].split("/")[1])
        d = row["detail"]
        item = dict(plate=plate, page=pg, ordinal=k[1], piece=k[2], bbox=d["bbox_page_px"], sp=float(d["space_page_px"]), staff=d.get("staff"),
                    write_status=w["status"], meet_status=m["status"], write_why=w.get("why"), meet_start=m.get("start"), meet_stop=m.get("stop"),
                    write_start=w.get("start"), write_stop=w.get("stop"), kind=m.get("kind"), boxes=mb)
        if w["status"] == "abstained" and m["status"] == "written":
            item["why"] = "gained"
        elif w["status"] == "written" and m["status"] == "written" and (w.get("start"), w.get("stop")) != (m.get("start"), m.get("stop")):
            item["why"] = "changed"
        elif w["status"] == "written" and m["status"] == "written":
            item["why"] = "same"
        elif w["status"] == "abstained" and m["status"] == "abstained" and cont(w) and cont(m):
            item["why"] = "kept_refused"
        elif w["status"] == "written" and m["status"] == "abstained":
            item["why"] = "lost"
        else:
            continue
        out.append(item)
    return out


def draw(item, name):
    img = page_img(item["plate"], item["page"])
    sp = item["sp"]
    bx = list(item["bbox"])
    heads = [item["boxes"][k] for k in (item.get("meet_start"), item.get("meet_stop")) if k in item["boxes"]]
    xs = [bx[0], bx[2]] + [h[0] for h in heads] + [h[2] for h in heads]
    ys = [bx[1], bx[3]] + [h[1] for h in heads] + [h[3] for h in heads]
    X0, X1 = int(max(0, min(xs) - 7 * sp)), int(min(img.shape[1], max(xs) + 7 * sp))
    Y0, Y1 = int(max(0, min(ys) - 4.5 * sp)), int(min(img.shape[0], max(ys) + 4.5 * sp))
    im = cv2.cvtColor(img[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im, (int(bx[0] - X0 - 3), int(bx[1] - Y0 - 3)), (int(bx[2] - X0 + 3), int(bx[3] - Y0 + 3)), (0, 140, 255), 2)
    s = min(0.7, 1400.0 / im.shape[1])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT / name), im)
    return im.shape


if __name__ == "__main__":
    argv = sys.argv[1:]
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 2281
    OUT.mkdir(parents=True, exist_ok=True)
    pools = {}
    for plate, d in (("brahms", argv[0]), ("litolff", argv[1])):
        for it in classify(d, plate):
            pools.setdefault(it["why"], []).append(it)
    print({k: len(v) for k, v in pools.items()})
    rnd = random.Random(seed)
    for v in pools.values():
        rnd.shuffle(v)
    pick = []
    want = [("gained", 7), ("changed", 0), ("same", 3), ("kept_refused", 2)]
    for why, n in want:
        pick += pools.get(why, [])[:n]
    short = 12 - len(pick)
    if short > 0:                      # fill from what is left (gained first, then changed, then same)
        for why in ("gained", "changed", "same", "kept_refused"):
            for it in pools.get(why, []):
                if short > 0 and it not in pick:
                    pick.append(it)
                    short -= 1
    rnd.shuffle(pick)
    key = []
    for i, it in enumerate(pick[:12], 1):
        name = "%02d.png" % i
        shape = draw(it, name)
        key.append(dict(tile=name, plate=it["plate"], page=it["page"], run=it["ordinal"], piece=it["piece"], category=it["why"], flag_off_status=it["write_status"], flag_off_why=it["write_why"],
                        flag_on_status=it["meet_status"], written_start=it["meet_start"], written_stop=it["meet_stop"], kind=it["kind"], shape=list(shape)))
        print(name, it["plate"], it["page"], it["ordinal"], it["why"])
    KEYF.write_text(json.dumps(dict(question="Is the boxed arc one arc, and which two notes does it join?", seed=seed, drawn="one thin orange box round the page-ink run; nothing else", tiles=key), indent=1, default=str))
