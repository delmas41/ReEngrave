"""2.305 r9 -- for every arc the OLD paths wrote (old box slurs, old record tie pairs) on Sean's swept Brahms p0 cells: which detector arc
boxes made it and why the page pass did not write that ink itself (the run the box witnesses and its status / reason word, or "no run").

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/arcs-combined-2026-11/r9 python3 .../r9/explain_old.py OUTPREFIX

Boxes are found by PLACE: the arc boxes whose owner is the staff of the arc's first note, kind decided, not replaced by a written page run,
whose x-range overlaps the stretch between the two notes' boxes. Reads only.
"""
from __future__ import annotations

import collections
import json
import sys

import judge as J


def staff_of(rg):
    p = rg.split("/")
    return "staff/%s/%s/%s" % (p[1], p[2], p[3])


def main():
    pre = sys.argv[1]
    facts = json.load(open(pre + ".facts.json"))
    sp = json.load(open(pre + ".spans.json"))
    rows = json.load(open(pre + ".tally.json"))
    glyphs = facts["glyphs"]
    boxes = sp["arc_boxes"]
    runs = sp["runs"] or []
    runs_of_box = collections.defaultdict(list)
    for r in runs:
        for w in (r.get("witnesses") or []):
            runs_of_box[w].append(r)
    reasons = collections.Counter()
    for r in rows:
        if r["verdict"] == "unread":
            continue
        if r["who"] == "his":
            w = r["written"]
            src, a, b, verdict = w["src"], w["a"], w["b"], r["verdict"] + " (his %s %s)" % (r["kind"], r["id"])
        else:
            src, a, b, verdict = r["src"], r["a"], r["b"], "wrong:" + r["why"]
        srcs = {x.replace("~chord", "") for x in (src or [])}
        if not srcs & {"old_box", "record_tie"}:
            continue
        ba, bb = glyphs[a]["box"], glyphs[b]["box"]
        x0, x1 = min(ba[0], bb[0]), max(ba[2], bb[2])
        st = {staff_of(a), staff_of(b)}
        hits = []
        for bx in boxes:
            if bx["replaced"] or not bx["box"] or bx["kind"] not in ("slur", "tie") or bx["not_arc"]:
                continue
            own = bx["owner"] if isinstance(bx["owner"], str) else staff_of(bx["sub"])
            if own not in st:
                continue
            bx0, bx1 = bx["box"][0], bx["box"][2]
            ov = min(x1, bx1) - max(x0, bx0)
            if ov <= 0.3 * (bx1 - bx0):
                continue
            rr = runs_of_box.get(bx["sub"]) or []
            desc = []
            for q in rr:
                d = q["status"]
                if q["status"] != "written":
                    d += ":" + str(q.get("why"))
                    ub = q.get("unbound") or {}
                    if ub:
                        d += "[" + ",".join("%s=%s" % (s, (ub[s] or {}).get("unbound")) for s in ub) + "]"
                else:
                    d += "->%s %s..%s" % (q.get("kind"), q.get("start"), q.get("stop"))
                desc.append(d)
            cv = bx.get("curve") or {}
            hits.append(dict(sub=bx["sub"], kind=bx["kind"], own=own, box=[round(v) for v in bx["box"]],
                             runs=desc or ["witnesses no page run"],
                             curve=(cv.get("why") or ("bound %s %s..%s" % (cv.get("kind"), cv.get("start"), cv.get("stop")))) if cv else None))
        key = "+".join(sorted(srcs))
        print("%-38s %-22s %s -> %s" % (verdict, key, a, b))
        for h in hits:
            print("     box %s %s own=%s x %s..%s runs=%s curve=%s" % (h["sub"], h["kind"], h["own"], h["box"][0], h["box"][2], h["runs"], h["curve"]))
            reasons[(verdict.split(" ")[0].split(":")[0], h["runs"][0].split("[")[0].split("->")[0])] += 1
        if not hits:
            reasons[(verdict.split(" ")[0].split(":")[0], "no box found")] += 1
    print("first-run reason by verdict:", dict(reasons))


if __name__ == "__main__":
    main()
