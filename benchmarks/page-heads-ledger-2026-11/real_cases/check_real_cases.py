"""ROADMAP 2.290 build -- Sean's named marks, one by one, against a gather made with the 2.290 flags ON (READ-ONLY).

    python3 benchmarks/page-heads-ledger-2026-11/real_cases/check_real_cases.py ON.record.json --plate litolff [--out DIR]

For every case of `cases.json` on a page the record holds (build_cases.py: what Sean said and what this lane must do with it), from the record's own
rows: the notehead boxes standing on the tile's box (the ONE identity's `Q.MARK_GROUP` rows: group, head ink, how), the page heads among them, and the
head claims (`Q.CLAIMED_AREA` source `page_head_one`) whose claimed page strokes lie on the box (`Q.PAGE_STROKE` boxes). With the record's verdicts
(`--through adjudicate`), also whether the cell's stroke owner gave those strokes to the page head (the claim reached the ledger). AGREES / DISAGREES
per case, by its expectation:

  head          exactly ONE head claim on the box (and the box's boxes are one head)
  part_of_head  at most one head claim on the box
  not_head      no head claim whose strokes lie mostly inside the box
  tall_box      the tall box is no head of its own (its MARK_GROUP how is tall_read; no claim has it as representative)
  chord         the bar's heads are at least two page heads
  metronome     reported only
"""
import argparse
import collections
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def inside_share(inner, outer):
    ix = min(inner[2], outer[2]) - max(inner[0], outer[0])
    iy = min(inner[3], outer[3]) - max(inner[1], outer[1])
    a = (inner[2] - inner[0]) * (inner[3] - inner[1])
    if ix <= 0 or iy <= 0 or a <= 0:
        return 0.0
    return ix * iy / a


def load(path):
    d = json.loads(pathlib.Path(path).read_text())
    rec = d.get("record", d)
    return rec.get("observations") or [], rec.get("verdicts") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rec")
    ap.add_argument("--plate", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    obs, verdicts = load(a.rec)
    pages = sorted({int(o["subject"].split("/")[1]) for o in obs if o.get("subject", "").startswith("page/")})
    boxes, mg, strokes, claims = {}, {}, {}, []
    for o in obs:
        q, s, d = o.get("quantity"), o.get("subject", ""), o.get("detail") or {}
        if q == "glyph_box" and d.get("category") == "notehead":
            boxes[s] = [float(v) for v in d.get("bbox_page_px") or ()]
        elif q == "mark_group" and d.get("identity") == "page_head":
            mg[s] = (o["value"], d)
        elif q == "page_stroke":
            strokes[(int(s.split("/")[1]), int(d["ordinal"]))] = [float(v) for v in d["bbox_page_px"]]
        elif q == "claimed_area" and d.get("source") == "page_head_one" and d.get("page_strokes"):
            claims.append(dict(id=o["id"], page=int(s.split("/")[1]), strokes=[int(i) for i in d["page_strokes"]], members=d.get("members") or [],
                               rep=d.get("rep"), oval=d.get("oval")))
    # which claims the stroke owner gave strokes to (the claim is on the ledger), by claim row id
    on_ledger = collections.Counter()
    for v in verdicts:
        if v.get("quantity") != "stroke_owner":
            continue
        for _o, ent in (((v.get("detail") or {}).get("strokes")) or {}).items():
            if ent and ent[0] in ("decided", "merged") and ent[2] and str(ent[2][0]).startswith("page_head/"):
                on_ledger[str(ent[2][0])[len("page_head/"):]] += 1
    cases = [c for c in json.loads((HERE / "cases.json").read_text())["cases"] if c["plate"] == a.plate and c["page"] in pages]
    res = []
    for c in cases:
        p = c["page"]
        r = dict(id=c["id"], page=p, expect=c["expect"], sean=c["sean"])
        if c["expect"] == "chord":
            cell = "/".join(map(str, c["cell"]))
            inked = {k: mg[k] for k in mg if "/".join(k.split("/")[1:5]) == cell and mg[k][1].get("head_ink_px")}
            heads = {v[0] for v in inked.values()}
            r.update(boxes=len(inked), heads=len(heads), verdict="AGREES" if len(heads) >= 2 else "DISAGREES")
            res.append(r)
            continue
        B = c["box"]
        mine = [k for k, bx in boxes.items() if int(k.split("/")[1]) == p and bx and (inside_share(bx, B) >= 0.5 or inside_share(B, bx) >= 0.5)]
        groups = {mg[k][0] for k in mine if k in mg}
        hows = sorted({mg[k][1].get("head_how") for k in mine if k in mg})
        cut = 0.5 if c["expect"] == "not_head" else 0.3
        on = []
        for cl in claims:
            if cl["page"] != p:
                continue
            got = [i for i in cl["strokes"] if (p, i) in strokes and inside_share(strokes[(p, i)], B) >= cut]
            if got:
                on.append(dict(claim=cl["id"], strokes=got, members=len(cl["members"]), rep=cl["rep"], ledger_strokes=on_ledger.get(cl["id"], 0)))
        n = len(on)
        e = c["expect"]
        if e == "head":
            ok = n == 1
        elif e == "part_of_head":
            ok = n <= 1
        elif e == "not_head":
            ok = n == 0
        elif e == "tall_box":
            ok = all(mg[k][1].get("head_how") == "tall_read" for k in mine if k in mg and inside_share(B, boxes[k]) >= 0.8) and not any(
                cl["rep"] in mine and inside_share(B, boxes[cl["rep"]]) >= 0.8 for cl in claims if cl["page"] == p)
        else:
            ok = None
        r.update(boxes=len(mine), heads=len(groups), how=hows, claims=on, verdict={True: "AGREES", False: "DISAGREES", None: "REPORTED"}[ok])
        res.append(r)
    tally = collections.Counter((r["expect"], r["verdict"]) for r in res)
    lines = ["%s: %d cases on pages %s (record %s)" % (a.plate, len(res), pages, a.rec)]
    for r in res:
        cl = r.get("claims")
        lines.append("  %-14s p%-3s %-12s %-9s boxes %s heads %s claims %s %s | Sean: %s" % (
            r["id"], r["page"], r["expect"], r["verdict"], r.get("boxes"), r.get("heads"),
            "-" if cl is None else len(cl), "" if not cl else "(ledger strokes %s)" % [x["ledger_strokes"] for x in cl], r["sean"][:60]))
    lines.append("tally: " + ", ".join("%s %s %d" % (k[0], k[1], v) for k, v in sorted(tally.items())))
    print("\n".join(lines))
    if a.out:
        od = pathlib.Path(a.out)
        od.mkdir(parents=True, exist_ok=True)
        (od / ("real_cases-%s.txt" % a.plate)).write_text("\n".join(lines) + "\n")
        (od / ("real_cases-%s.json" % a.plate)).write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
