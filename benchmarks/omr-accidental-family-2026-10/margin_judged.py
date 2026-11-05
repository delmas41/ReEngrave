"""2.263: join Sean's judged accidental tiles to the accidental_family reading in a saved record BY PLACE (page + overlapping box), never by key alone.
Inputs: margin_extract.py output (family observations + glyph boxes) and margin_owners.py output (decided owner verdicts), per plate.
usage: python3 benchmarks/omr-accidental-family-2026-10/margin_judged.py SCRATCH_DIR OUT.json   (run from the repo root)"""
import json, os, sys
sys.path.insert(0, ".")
from tools.omr.staged import judged as J

R = "/Users/seanjohnson/Desktop/ReEngrave/"
W = R + ".claude/worktrees/"
# (set, dir holding answers.json + key.json). 2.201 / 2.201b / 2.203 keys were never kept (answers only): they cannot be placed.
SETS = [("2.186b", "out/print/2.186b-accidentals/"), ("2.190", "out/print/2.190-accidental-shape/"), ("2.192", "out/print/2.192-phantom-accidental/"),
        ("2.193", R + "out/print-archive/lane-2.209/2.193-missing-naturals/"), ("2.199b", W + "lane-2.199/out/lane-report/2.199b/")]
# tile sets whose box is ON the accidental (2.247 r1-r3: answers.json is {"answers": {tile: words}}); the type is the word in Sean's answer
BOX_ON_ACCIDENTAL = [("2.247", "out/print/2.247-tiles/"), ("2.247r2", "out/print/2.247-r2-tiles/"), ("2.247r3", "out/print/2.247-r3-tiles/")]
UNIT = {"litolff": 15.75, "brahms": 32.0}


def norm(s):
    s = str(s).lower()
    for k in ("natural", "flat", "sharp"):
        if s.startswith(k):
            return k
    if s.startswith("none"):
        return "none"
    if "tremolo" in s:
        return "none"
    for k in ("natural", "flat", "sharp"):
        if k in s:
            return k
    if "rest" in s:
        return "rest"
    return None


def load_tiles():
    out = []
    for name, d in SETS:
        ans = {t["tile"]: t for t in json.load(open(d + "answers.json"))["tiles"]}
        key = json.load(open(d + "key.json"))
        key = key if isinstance(key, list) else key.get("tiles", key)
        for k in key:
            a = ans.get(k["tile"])
            if a:
                out.append(dict(set=name, tile=k["tile"], plate=k["plate"], page=int(k["page"]), box=[float(v) for v in k["box"]], sean_raw=a["sean"],
                                sean=norm(a["sean"]), role=k.get("role"), side=k.get("side"), rg=k.get("rg") or k.get("acc"), cls=k.get("cls")))
    for name, d in BOX_ON_ACCIDENTAL:
        ans = json.load(open(d + "answers.json"))["answers"]
        key = json.load(open(d + "key.json"))
        key = key if isinstance(key, list) else key.get("tiles", key)
        for k in key:
            a = ans.get(str(k["tile"]))
            if a:
                out.append(dict(set=name, tile=k["tile"], plate=k["plate"], page=int(k["page"]), box=[float(v) for v in k["box"]], sean_raw=a,
                                sean=norm(a), role=k.get("role"), side=None, rg=k.get("subject"), cls=k.get("cls"), box_on_accidental=True))
    return out


def page_of(sub):
    return int(sub.split("/")[1])


def load_plate(S, plate):
    boxes = json.load(open(S + plate + ".jsonl.boxes.json"))
    fam = {}
    for l in open(S + plate + ".jsonl"):
        r = json.loads(l)
        fam.setdefault(r["subject"], r)
    owners = {}
    for l in open(S + plate + ".owners.jsonl"):
        r = json.loads(l)
        if r["family"]:
            owners.setdefault(r["subject"], []).append(r)
    return boxes, fam, owners


def match(t, boxes, fam, owners):
    """Candidates: (A) a family row whose own head (owner verdict value) overlaps the tile's box; (B) a family row whose box overlaps the tile's box;
    (C) a family row standing directly left of the tile's box (the tile boxes the NOTE). Each: how, subject, row."""
    u = UNIT[t["plate"]]
    tb = t["box"]
    hits = {}
    for sub, rs in owners.items():
        if page_of(sub) != t["page"]:
            continue
        for r in rs:
            hb = boxes.get(r["head"])
            if hb and J.boxes_overlap(hb, tb)[0]:
                hits.setdefault(sub, ("A:head_under_tile_box", r))
    if t.get("box_on_accidental"):
        # the tile box IS the accidental's: the one family row of best IoU with it (>= 0.3); a neighbour's box that merely contains its centre is not it
        best = None
        for sub, r in fam.items():
            ab = boxes.get(sub)
            if page_of(sub) != t["page"] or not ab:
                continue
            iou = J.boxes_overlap(ab, tb)[1]
            if iou >= 0.3 and (best is None or iou > best[0]):
                best = (iou, sub, r)
        if best:
            own = owners.get(best[1])
            hits[best[1]] = ("B:accidental_box_iou%.2f" % best[0], dict(own[0], family=best[2]["family"]) if own else best[2])
        return hits
    for sub, r in fam.items():
        if page_of(sub) != t["page"] or sub in hits:
            continue
        ab = boxes.get(sub)
        if not ab:
            continue
        if J.boxes_overlap(ab, tb)[0]:
            hits[sub] = ("B:accidental_box_in_tile_box", r)
        else:
            gap = tb[0] - ab[2]
            if -0.5 * u <= gap <= 2.5 * u and ab[3] > tb[1] - u and ab[1] < tb[3] + u:
                hits[sub] = ("C:left_of_tile_box", r)
    return hits


if __name__ == "__main__":
    S, out = sys.argv[1].rstrip("/") + "/", sys.argv[2]
    P = {p: load_plate(S, p) for p in ("litolff", "brahms")}
    res = []
    for t in load_tiles():
        boxes, fam, owners = P[t["plate"]]
        hits = match(t, boxes, fam, owners)
        rows = []
        for sub, (how, r) in hits.items():
            if t.get("box_on_accidental") and how[0] == "C":
                continue
            f = r["family"]
            rows.append(dict(sub=sub, how=how, type=f.get("type"), why=f.get("why"), margin=f.get("margin"), detector_type=f.get("detector_type"),
                             stagger_top=(f.get("features") or {}).get("stagger_top_sp"), stagger_bot=(f.get("features") or {}).get("stagger_bottom_sp"),
                             head=r.get("head"), owned=("vid" in r), written=r.get("written")))
        res.append(dict(t, matches=sorted(rows, key=lambda x: x["how"])))
    json.dump(res, open(out, "w"), indent=1)
    from collections import Counter
    print(len(res), "tiles;", Counter(len(r["matches"]) for r in res), Counter(m["how"][0] for r in res for m in r["matches"]))
