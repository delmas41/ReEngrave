"""2.306 r13 study, the swap experiment: OLD's JOIN RULE on NEW's INK, to tell "the rule differs" from "the ink differs".
For every head where OLD stems and NEW refuses: take the page map's whole vertical runs (NEW's `join_runs`, the stems as NEW would hold them) and
apply OLD's test -- the run's box touches the head's detector box (within 0.12 of the head's height), nothing else. Buckets:
  one run, OLD's column          the ink is there and whole enough; OLD's looser rule alone takes it (rule difference)
  one run, but another claim holds it   the ink is there; NEW may not take it (claim order)
  several runs touch             on NEW's ink OLD's rule would not be unique either: NEW's map holds verticals OLD's finder never called stems
  no run touches                 NEW's map has no vertical where OLD has a stem (ink difference)
Also, the other way: is each of NEW's rival candidates a stroke OLD's finder filed as a stem at all?
Usage (cwd = repo root): swap.py lit|bra"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import replay as RP
from tools.omr.staged import page_stems as PS

plate = sys.argv[1]
D = load(plate)
ups = cell_up(D)
T = json.load(open("%s/r13/%s.trace.json" % (S, plate)))
A = [r for r in T if r["old_stem"] and r["new_read"] is False and r["new_how"] != "two_voices"]
byp = collections.defaultdict(list)
for r in A:
    byp[r["page"]].append(r)
old_boxes = collections.defaultdict(list)      # page -> OLD stem rows in page px
for sid, st in D["stems"].items():
    if st["reader"] == "cv_lines":
        b = stem_page_box(D, ups, sid)
        if b:
            old_boxes[pg(st["cell"])].append(b)


def touch(sb, hb, tol):
    return sb[0] <= hb[2] + tol and sb[2] >= hb[0] - tol and sb[1] <= hb[3] + tol and sb[3] >= hb[1] - tol


def col(a, b, sp):
    ov = min(a[3], b[3]) - max(a[1], b[1])
    return abs((a[0] + a[2]) / 2.0 - (b[0] + b[2]) / 2.0) <= max(3.0, 0.35 * sp) and ov >= 0.5 * min(a[3] - a[1], b[3] - b[1])


c = collections.Counter()
by_how = collections.defaultdict(collections.Counter)
rival = collections.Counter()
out = {}
for p, rs in byp.items():
    heads, verticals, held, crossers, strokes = RP.inputs(D, p)
    runs, _ = PS.join_runs(verticals, heads, crossers, {})
    ps = D["pstrokes"][p]
    for r in rs:
        hb, sp, ob = r["head_box"], r["sp"], r["old_box"]
        tol = 0.12 * (hb[3] - hb[1])
        tall = [u for u in runs if (u["box"][3] - u["box"][1]) >= 2.0 * sp and (u["box"][3] - u["box"][1]) <= 8.0 * sp]
        tt = [u for u in tall if touch(u["box"], hb, tol)]
        anyt = [u for u in runs if touch(u["box"], hb, tol)]
        mine = [u for u in tt if ob and col(u["box"], ob, sp)]
        if len(tt) == 1 and mine:
            k = "one run touches the head box, in OLD's column"
            if any(m in held for m in tt[0]["members"]):
                k += ", but another claim holds it (%s)" % held[next(m for m in tt[0]["members"] if m in held)]
        elif len(tt) > 1 and mine:
            k = "several runs touch the head box (OLD's among them)"
        elif tt:
            k = "a run touches the head box, but not in OLD's column"
        elif anyt:
            k = "only a run shorter than 2 sp or longer than 8 sp touches (OLD's finder would not call it a stem)"
        else:
            k = "no vertical run of the page map touches the head box"
        c[k] += 1
        by_how[r["new_how"]][k.split(",")[0].split("(")[0].strip()] += 1
        out[r["g"]] = k
        for cd in r.get("new_cands") or ():
            o = cd.get("stroke")
            if o is None or o not in ps:
                continue
            run = next((u for u in runs if o in u["members"]), None)
            b = run["box"] if run else ps[o]["box"]
            known = any(col(b, x, sp) for x in old_boxes[p])
            rival[(r["new_how"], "OLD's finder has a stem row here" if known else "OLD's finder has NO stem row here")] += 1
json.dump(out, open("%s/r13/%s.swap.json" % (S, plate), "w"))
print(plate, "OLD stems, NEW refuses:", len(A))
for k, v in c.most_common():
    print("  %4d  %s" % (v, k))
print(" by NEW's reason word:")
for h, cc in by_how.items():
    print("   %-28s %s" % (h, dict(cc)))
print(" NEW's candidate strokes on these heads:", dict(rival))
