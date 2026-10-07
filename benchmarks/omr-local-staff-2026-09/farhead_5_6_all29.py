"""lane-farhead-5-6: replay the reader on the 29 Brahms far heads that went decided (10-06) -> abstained (10-07). Read only.
  python3 farhead_5_6_all29.py <x/new.json> <x/base.json> <x7 night extract> <out.json>
Prints per head: base answer, replay now, the note-first detail (kind/how/line_y/edge/rungs/k/gaps)."""
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import overnight_1004_report as R


def heads_29(newj, basej):
    n = json.loads(Path(newj).read_text())["glyphs"]
    b = json.loads(Path(basej).read_text())["glyphs"]
    out = []
    for s, g in n.items():
        nb = (b.get(s) or {}).get("np")
        nn = g.get("np")
        if nb and nn and nb.get("outcome") == "decided" and nb.get("reason") == "ledger_position" and nn["outcome"] == "abstained":
            out.append(s)
    return sorted(out, key=lambda s: tuple(int(v) for v in s.split("/")[1:]))


if __name__ == "__main__":
    newj, basej, src, out = sys.argv[1:5]
    for kw in sys.argv[5:]:               # e.g. flank_refine_bounded=1
        k, v = kw.split("=")
        D.FH.READER_KEYWORDS[k] = v == "1"
    heads = heads_29(newj, basej)
    data, rep = D.load(src)
    res = {}
    for s in heads:
        g, r, cap, gl, ctx = D.read_one(rep, data, s)
        d = (r.get("detail") or {}).get("note_first") or {}
        res[s] = dict(pos=r["pos"], reason=r["reason"], edge=cap.get("edge"), rungs=cap.get("rungs"), sp=cap.get("sp"),
                      box=g["box"], nf={k: d.get(k) for k in ("kind", "how", "line_y", "k", "gaps", "between", "seen_on_flanks")})
        print(s, "now", r["pos"], r["reason"][:60], "| line", d.get("how"), d.get("line_y"), "edge", cap.get("edge"),
              "rungs", [round(v, 1) for v in cap.get("rungs", [])], flush=True)
    Path(out).write_text(json.dumps(res, default=str))
