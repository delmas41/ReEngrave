"""lane-farhead-5-6: how far does `refine_line_on_flanks` move the note's line, on every far head of the 10-07 record?
Replays the reader (spy on the refine) and writes {subject: [how, y_in, y_out, seen, decided_pos, replay_pos]}. Read only.
  python3 farhead_5_6_refine_census.py <x7 extract> <doc> <out.json> [--pages a,b]"""
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import night_1007_replay as NR
import overnight_1004_report as R
from tools.omr.annotate import ledger_grid as lg

if __name__ == "__main__":
    src, doc, out = sys.argv[1:4]
    for kw in sys.argv[4:]:               # e.g. flank_refine_bounded=1
        if "=" in kw:
            k, v = kw.split("=")
            D.FH.READER_KEYWORDS[k] = v == "1"
    pages = set(int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")) if "--pages" in sys.argv else None
    data, rep = D.load(src, doc)
    G = data["glyphs"]
    far = [s for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g and ("fh" in g or "fh_abs" in g)]
    far.sort(key=lambda s: tuple(int(v) for v in s.split("/")[1:]))
    cap = {}
    orig = lg.refine_line_on_flanks

    def spy(img, y, box, sp, **kw):
        r = orig(img, y, box, sp, **kw)
        cap["r"] = (float(y), float(r[0]), bool(r[1]), float(sp))
        return r
    lg.refine_line_on_flanks = spy
    res = {}
    cur = None
    for s in far:
        p = R.page_of(s)
        if pages and p not in pages:
            continue
        if cur is not None and p != cur:
            rep.gray.pop(cur, None)
        cur = p
        cap.clear()
        try:
            g, r, c, gl, ctx = D.read_one(rep, data, s)
        except Exception as e:
            res[s] = dict(err=repr(e))
            continue
        nf = (r.get("detail") or {}).get("note_first") or {}
        dec = G[s].get("fh")
        res[s] = dict(how=nf.get("how"), kind=nf.get("kind"), refine=cap.get("r"), rec=(None if dec is None else dec["value"]),
                      pos=r["pos"], sp=c.get("sp"), reason=r["reason"][:70])
        if len(res) % 500 == 0:
            print(len(res), "of", len(far), flush=True)
    Path(out).write_text(json.dumps(res))
    print("wrote", out, len(res))
