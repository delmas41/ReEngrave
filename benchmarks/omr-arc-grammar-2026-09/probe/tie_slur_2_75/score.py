"""Score arc kind against Sean's hand-labelled Brahms pdf 0 (tie/slur boxes).

usage: score.py record.json [record2.json ...]   (prints a table per record)
Truth: data/hand-truth/pages/imslp317803/0.json, cls in (tie, slur), labeler sean.
Match: each truth box -> the kept arc (not refused as not-an-arc) of page 0 with the
highest IoU (>= 0.30).  Reports kind agreement, and per-arc list with --list.
"""
import json
import sys
import collections

from tools.omr.staged import record_io

TRUTH = "data/hand-truth/pages/imslp317803/0.json"


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u


def arcs_of(path, page=0):
    if path.endswith("rows.json"):
        out = []
        for r in json.load(open(path)):
            if int(r["sub"].split("/")[1]) != page or not r["box"]:
                continue
            out.append(dict(sub=r["sub"], box=r["box"], det=r["det"], refused=r["refused"],
                            kind=r["kind"], kreason=r["reason"], detail=r.get("rule"), owner=None))
        return out
    r = record_io.load_record(path)["record"]
    box = {}
    for o in r["observations"]:
        if o["quantity"] == "arc_box":
            box[o["subject"]] = o
    ver = collections.defaultdict(dict)
    for v in r["verdicts"]:
        if v["quantity"] in ("arc_kind", "arc_is_not_an_arc", "arc_owner"):
            ver[v["subject"]][v["quantity"]] = v
    out = []
    for sub, o in box.items():
        parts = sub.split("/")
        if int(parts[1]) != page:
            continue
        pb = o["detail"].get("bbox_page_px")
        if not pb:
            continue
        nv = ver[sub].get("arc_is_not_an_arc")
        refused = bool(nv and nv["outcome"] == "decided" and nv["value"] is True)
        kv = ver[sub].get("arc_kind")
        kind = kv["value"] if kv and kv["outcome"] == "decided" else None
        out.append(dict(sub=sub, box=pb, det=o["value"], refused=refused,
                        kind=kind, kreason=(kv or {}).get("reason"),
                        detail=(kv or {}).get("detail"),
                        owner=(ver[sub].get("arc_owner") or {}).get("value")))
    return out


def main():
    truth = [b for b in json.load(open(TRUTH))["boxes"]
             if b["cls"] in ("tie", "slur") and b.get("labeler") == "sean"]
    for path in sys.argv[1:]:
        if path.startswith("--"):
            continue
        arcs = [a for a in arcs_of(path) if not a["refused"]]
        print("==", path, "kept arcs on page 0:", len(arcs),
              "truth boxes:", len(truth))
        tally = collections.Counter()
        rows = []
        for t in truth:
            best, bi = None, 0.0
            for a in arcs:
                i = iou(t["rect"], a["box"])
                if i > bi:
                    best, bi = a, i
            if best is None or bi < 0.30:
                tally[(t["cls"], "no_match")] += 1
                rows.append((t["cls"], None, bi, t["rect"]))
                continue
            tally[(t["cls"], best["kind"] or "abstained")] += 1
            rows.append((t["cls"], best, bi, t["rect"]))
        for k in sorted(tally, key=str):
            print("  truth %-5s -> ours %-10s %d" % (k[0], k[1], tally[k]))
        right = sum(v for k, v in tally.items() if k[0] == k[1])
        matched = sum(v for k, v in tally.items() if k[1] != "no_match")
        print("  right %d of %d matched (%d truth boxes)" % (right, matched, len(truth)))
        if "--list" in sys.argv:
            for cls, a, i, rect in rows:
                if "--mismatch" in sys.argv and a is not None and a["kind"] == cls:
                    continue
                print("   ", cls, None if a is None else (a["sub"], a["det"], a["kind"], a["kreason"]), round(i, 2), [round(x) for x in rect])


main()
