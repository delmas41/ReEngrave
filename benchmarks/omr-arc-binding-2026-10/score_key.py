"""2.281: score a written MusicXML's arcs against the CORRECTED Brahms p0 key (key-brahms-p0-corrected.json), by place, never by hand-box id.

    python3 score_key.py WORKDIR ARM [--reach 2.5] [--list] [--drop N] [--shift SP]

A written arc is the pair of glyph keys (`rg`) of its two notes (page-ink-2026-11/step2/arcs.arcs_of_xml); each end is the box centre of its head.
A key arc is RIGHT when ONE written arc has its start head within REACH sp (x) of the key's left end and its stop head within REACH of the right end, both heads within
6 sp (y) of the key arc's y band, and the kinds agree (kind-conflict key arcs accept either).  `other_kind` = ends right, kind wrong.  Cross-system arcs are not scored.
Reach: 2.5 sp slurs, 3.5 sp ties (a tie's hand box is loose at both ends: the heads sit inside it).  One written arc satisfies one key arc.
Controls that can fail: --drop N removes N random written arcs (score must fall), --shift SP moves every key arc SP spaces (score must collapse).
"""
import collections
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402

SP = 32.0
KEY = json.load(open(HERE / "key-brahms-p0-corrected.json"))


def head_boxes(record_path, page=0):
    out = {}
    for o in json.loads(pathlib.Path(record_path).read_text())["observations"]:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and o["subject"].startswith("glyph/%d/" % page):
            out[o["subject"]] = [float(v) for v in b]
    return out


def written(work, arm, page=0, drop=0):
    work = pathlib.Path(work)
    xml = (work / ("%s.musicxml" % arm)).read_text()
    boxes = head_boxes(work / ("%s.record.json" % arm), page)
    spans = []
    for a in A.arcs_of_xml(xml):
        if not a["start"].startswith("glyph/%d/" % page) or a["start"] not in boxes or a["stop"] not in boxes:
            continue
        ba, bz = boxes[a["start"]], boxes[a["stop"]]
        xa, xz = (ba[0] + ba[2]) / 2, (bz[0] + bz[2]) / 2
        if xz < xa:
            xa, xz, ba, bz = xz, xa, bz, ba
        spans.append(dict(kind=a["kind"], xa=xa, xz=xz, ya=(ba[1] + ba[3]) / 2, yz=(bz[1] + bz[3]) / 2, start=a["start"], stop=a["stop"]))
    if drop:
        random.Random(7).shuffle(spans)
        spans = spans[drop:]
    return spans


def yd(y, y0, y1):
    return 0.0 if y0 <= y <= y1 else min(abs(y - y0), abs(y - y1))


def score(spans, reach=2.5, shift=0.0, list_rows=False):
    """global greedy assignment: every feasible (key, written) pair, cheapest first (kind-right pairs before other-kind ones); one written arc satisfies one key arc."""
    keys = [k for k in KEY["arcs"] if k["scorable"]]
    pairs = []
    for ki, k in enumerate(keys):
        r = (3.5 if k["kind"] == "tie" else reach) * SP if reach == 2.5 else reach * SP
        x0, x1 = k["x0"] + shift * SP, k["x1"] + shift * SP
        for i, s in enumerate(spans):
            if abs(s["xa"] - x0) <= r and abs(s["xz"] - x1) <= r and yd(s["ya"], k["y0"], k["y1"]) <= 6 * SP and yd(s["yz"], k["y0"], k["y1"]) <= 6 * SP:
                good = bool(k["kind_conflict"] or s["kind"] == k["kind"])
                cost = abs(s["xa"] - x0) + abs(s["xz"] - x1) + yd(s["ya"], k["y0"], k["y1"]) + yd(s["yz"], k["y0"], k["y1"])
                pairs.append((not good, cost, ki, i, good))
    pairs.sort()
    used_k, used_w = {}, set()
    for _ng, cost, ki, i, good in pairs:
        if ki in used_k or i in used_w:
            continue
        used_k[ki] = (i, good)
        used_w.add(i)
    res = collections.Counter()
    rows = []
    for ki, k in enumerate(keys):
        if ki in used_k:
            i, good = used_k[ki]
            res["right" if good else "other_kind"] += 1
            rows.append((k["id"], k["kind"], k["x0"], k["x1"], "right" if good else "other_kind", spans[i]))
        else:
            res["none"] += 1
            rows.append((k["id"], k["kind"], k["x0"], k["x1"], "none", None))
    res["keys"] = len(keys)
    res["written_unmatched"] = len(spans) - len(used_w)
    return res, rows


if __name__ == "__main__":
    argv = sys.argv[1:]
    work, arm = argv[0], argv[1]
    reach = float(argv[argv.index("--reach") + 1]) if "--reach" in argv else 2.5
    drop = int(argv[argv.index("--drop") + 1]) if "--drop" in argv else 0
    shift = float(argv[argv.index("--shift") + 1]) if "--shift" in argv else 0.0
    sp = written(work, arm, drop=drop)
    res, rows = score(sp, reach, shift)
    print(arm, "reach", reach, "drop", drop, "shift", shift, "written", len(sp), dict(res))
    kinds = collections.Counter()
    for r in rows:
        kinds[(r[1], r[4])] += 1
    print(dict(kinds))
    if "--list" in argv:
        for r in rows:
            print(r[:5])
