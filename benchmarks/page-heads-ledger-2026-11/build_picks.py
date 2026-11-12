"""ROADMAP 2.290 build -- the tile pool for `make_tiles_build.py` from a lane-report work dir (READ-ONLY).

    python3 benchmarks/page-heads-ledger-2026-11/build_picks.py WORKDIR OUT.json --lost GLYPH,... --undecided out/m290/part-litolff/disagreements.json,...

Each item: plate, page, box = the CLAIMED extent of the head (the union of its claimed page strokes' boxes; a head with no claim: its representative
box), strokes = those page-stroke boxes (the tile tints the dark pixels inside them), staff_band = the head's own staff lines +- 1.5 sp, why.
  lost       the ON head that holds each listed glyph (a note lost or changed)
  undecided  one box of each partition disagreement the comparison could not decide by rule (near_oval, little_ink, two_ovals on a fused stroke)
  chord      the heads of the 2.291 chord bars on these pages (tiles 7, 10)
  ledger     every head claim on the ledger (the tile draw picks from these)
"""
import argparse
import json
import pathlib

CHORD_CELLS = {"litolff": ["2/1/4/14", "2/0/2/3"], "brahms": ["4/1/2/0"]}


def load(path):
    d = json.loads(pathlib.Path(path).read_text())
    return d.get("record", d)["observations"]


def index(obs):
    st, boxes, mg, claims, staff = {}, {}, {}, [], {}
    for o in obs:
        q, s, d = o.get("quantity"), o.get("subject", ""), o.get("detail") or {}
        if q == "page_stroke":
            st[(int(s.split("/")[1]), int(d["ordinal"]))] = [float(v) for v in d["bbox_page_px"]]
        elif q == "glyph_box" and d.get("category") == "notehead":
            boxes[s] = [float(v) for v in d["bbox_page_px"]]
        elif q == "mark_group":
            mg[s] = (o["value"], d)
        elif q == "claimed_area" and d.get("source") == "page_head_one" and d.get("page_strokes"):
            claims.append(dict(id=o["id"], page=int(s.split("/")[1]), strokes=d["page_strokes"], members=d.get("members") or [], rep=d.get("rep")))
        elif q == "staff_lines" and s.startswith("staff/"):
            staff[s] = [float(v) for v in o["value"]]
    return st, boxes, mg, claims, staff


def item(plate, glyph, st, boxes, claims, staff, why):
    page = int(glyph.split("/")[1])
    cl = next((c for c in claims if glyph in c["members"]), None)
    sb = [st[(page, i)] for i in (cl["strokes"] if cl else []) if (page, i) in st]
    if sb:
        box = [min(b[0] for b in sb), min(b[1] for b in sb), max(b[2] for b in sb), max(b[3] for b in sb)]
    else:
        box = boxes.get(glyph)
    lines = staff.get("staff/" + "/".join(glyph.split("/")[1:4]))
    sp = (lines[-1] - lines[0]) / 4.0 if lines else 16.0
    band = [lines[0] - 1.5 * sp, lines[-1] + 1.5 * sp] if lines else [box[1] - 4 * sp, box[3] + 4 * sp]
    band = [min(band[0], box[1] - 0.5 * sp), max(band[1], box[3] + 0.5 * sp)]
    return dict(plate=plate, page=page, glyph=glyph, box=[round(v, 1) for v in box], strokes=sb, claim=cl["id"] if cl else None,
                members=cl["members"] if cl else [glyph], staff_band=[round(v, 1) for v in band], why=why)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--lost", default="")
    ap.add_argument("--undecided", default="")
    a = ap.parse_args()
    w = pathlib.Path(a.work)
    pool = {"lost": [], "undecided": [], "chord": [], "ledger": []}
    idx = {p: index(load(w / ("%s.on.gathered.record.json" % p))) for p in ("litolff", "brahms") if (w / ("%s.on.gathered.record.json" % p)).exists()}
    for g in [x for x in a.lost.split(",") if x]:
        plate, glyph = g.split(":")
        st, boxes, mg, claims, staff = idx[plate]
        pool["lost"].append(item(plate, glyph, st, boxes, claims, staff, "lost_or_changed"))
    for f in [x for x in a.undecided.split(",") if x]:
        plate = "litolff" if "litolff" in f else "brahms"
        st, boxes, mg, claims, staff = idx[plate]
        for d in json.loads(pathlib.Path(f).read_text()):
            if d["cls"] in ("near_oval", "little_ink") or (d["cls"] == "two_ovals" and (d["dy_sp"] or 0) < 1.0):
                pool["undecided"].append(item(plate, d["a"], st, boxes, claims, staff, "partition:%s:%s" % (d["cls"], d["b"])))
    for plate, (st, boxes, mg, claims, staff) in idx.items():
        for cell in CHORD_CELLS.get(plate, []):
            for g in sorted(k for k in boxes if "/".join(k.split("/")[1:5]) == cell and k in mg and mg[k][1].get("head_ink_px")):
                pool["chord"].append(item(plate, g, st, boxes, claims, staff, "chord_2.291:" + cell))
        for c in claims:
            pool["ledger"].append(item(plate, c["rep"], st, boxes, claims, staff, "newly_on_ledger"))
    pathlib.Path(a.out).write_text(json.dumps(pool, indent=0))
    print({k: len(v) for k, v in pool.items()})


if __name__ == "__main__":
    main()
