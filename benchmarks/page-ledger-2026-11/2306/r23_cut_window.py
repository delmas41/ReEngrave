"""2.306 r23: cut real-page windows for `page_stems.read` from the reader's exact inputs pickled during a gather (r23 `gather_dump.py`: it wraps
`page_stems.read` and pickles its arguments per page), one window per named glyph, appended to one fixture file. Same cut as r19_cut_window.py
(6 spaces each side, 10 above and below; a stroke's contacts kept only inside the window), but the head is named by a glyph key.
Usage: r23_cut_window.py OUT.json NAME@DUMP.pkl@GLYPH_KEY@EXPECT [...]"""
import json
import os
import pickle
import sys

out_p = sys.argv[1]
out = json.load(open(out_p)) if os.path.exists(out_p) else {}
for spec in sys.argv[2:]:
    name, dp, key, expect = spec.split("@")
    D = pickle.load(open(dp, "rb"))
    h0 = next(h for h in D["heads"] if key in h["members"])
    sp = float(h0["sp"])
    b = h0["box"]
    X0, Y0, X1, Y1 = b[0] - 6 * sp, b[1] - 10 * sp, b[2] + 6 * sp, b[3] + 10 * sp
    inw = lambda bb: bb[2] >= X0 and bb[0] <= X1 and bb[3] >= Y0 and bb[1] <= Y1
    heads = [dict(id=h["id"], members=h["members"], box=list(h["box"]), sp=h["sp"], sp_own=bool(h.get("sp_own")), ink=bool(h.get("ink")),
                  strokes=list(h.get("strokes") or ()), tall=bool(h.get("tall"))) for h in D["heads"] if inw(h["box"])]
    verts = [dict(ord=int(v["ord"]), box=list(v["box"]), sp=v["sp"]) for v in D["verticals"] if inw(v["box"])]
    cross = [dict(ord=int(c["ord"]), box=list(c["box"]), kind=c["kind"]) for c in D["crossers"] if inw(c["box"])]
    keep = {int(o) for o, s in D["strokes"].items() if inw(s["box"])}
    strokes = {str(o): dict(box=list(D["strokes"][o]["box"]), kind=D["strokes"][o]["kind"],
                            touches=[[int(j), float(c)] for j, c in D["strokes"][o].get("touches") or () if int(j) in keep]) for o in sorted(keep)}
    held = {str(o): w for o, w in D["held"].items() if int(o) in keep}
    out[name] = dict(page=D["page"], head=h0["id"], member=key, expect=expect, window=[X0, Y0, X1, Y1], heads=heads,
                     verticals=verts, crossers=cross, strokes=strokes, held=held)
    print(name, key, h0["id"], expect, len(heads), "heads", len(verts), "verticals", len(strokes), "strokes")
json.dump(out, open(out_p, "w"))
