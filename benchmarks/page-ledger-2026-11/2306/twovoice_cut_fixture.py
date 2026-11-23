"""2.306 two-voice piece: cut real-page windows for `page_stems.read` from page-stem dumps (the reader's exact inputs pickled during a real gather,
`r15 gather_dump.py`), one window per named head, all into one fixture file. Same cut as r15_cut_fixture.py (a stroke's contacts kept only inside
its window). Usage: twovoice_cut_fixture.py OUT.json NAME dump.pkl:hid:expect [...]   expect = unison | one:<up|down> | old"""
import sys, json, pickle

out_p, name = sys.argv[1], sys.argv[2]
wins, cache = [], {}
for spec in sys.argv[3:]:
    dp, hid, expect = spec.split(":", 2)
    if dp not in cache:
        cache.clear()
        cache[dp] = pickle.load(open(dp, "rb"))
    D = cache[dp]
    hb = {h["id"]: h for h in D["heads"]}
    h0 = hb[int(hid)]
    sp = float(h0["sp"])
    b = h0["box"]
    X0, Y0, X1, Y1 = b[0] - 6 * sp, b[1] - 10 * sp, b[2] + 6 * sp, b[3] + 10 * sp
    inw = lambda bb: bb[2] >= X0 and bb[0] <= X1 and bb[3] >= Y0 and bb[1] <= Y1
    heads = [dict(id=h["id"], members=h["members"], box=list(h["box"]), sp=h["sp"], ink=bool(h.get("ink")), strokes=list(h.get("strokes") or ()))
             for h in D["heads"] if inw(h["box"])]
    verts = [dict(ord=int(v["ord"]), box=list(v["box"]), sp=v["sp"]) for v in D["verticals"] if inw(v["box"])]
    cross = [dict(ord=int(c["ord"]), box=list(c["box"]), kind=c["kind"]) for c in D["crossers"] if inw(c["box"])]
    keep = {int(o) for o, s in D["strokes"].items() if inw(s["box"])}
    strokes = {str(o): dict(box=list(D["strokes"][o]["box"]), kind=D["strokes"][o]["kind"],
                            touches=[[int(j), float(c)] for j, c in D["strokes"][o].get("touches") or () if int(j) in keep]) for o in sorted(keep)}
    held = {str(o): w for o, w in D["held"].items() if int(o) in keep}
    wins.append(dict(page=D["page"], head=int(hid), member=h0["members"][0], expect=expect, window=[X0, Y0, X1, Y1], heads=heads, verticals=verts,
                     crossers=cross, strokes=strokes, held=held))
    print(dp.split("/")[-2:], hid, expect, len(heads), "heads", len(verts), "verticals", len(strokes), "strokes")
json.dump(dict(name=name, windows=wins), open(out_p, "w"))
