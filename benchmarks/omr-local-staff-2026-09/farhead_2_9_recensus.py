"""lane-farhead-2-9: after the articulation rule was NARROWED (only a wedge class; only a box beside THIS head) the census need not be
re-run over every far head: the narrowed rule fires on a SUBSET of the heads the first census saw it fire on, and the hidden-ledger look
is untouched. Re-read the ON arm for the first census's decided -> abstain heads only, patch them in, print the tallies.
  python3 farhead_2_9_recensus.py <old census.json> <x7 extract> <doc> <out.json>"""
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D

if __name__ == "__main__":
    old, src, doc, out = sys.argv[1:5]
    c = json.loads(Path(old).read_text())
    data, rep = D.load(src, doc)
    D.FH.READER_KEYWORDS["look_where_it_must_be"] = True
    res = c["res"]
    for s in c["lost"]:
        g, r, cap, gl, ctx = D.read_one(rep, data, s)
        nf = (r.get("detail") or {}).get("note_first") or {}
        res[s]["on"] = [r["pos"], r["reason"][:90]]
        res[s]["between_on"] = nf.get("between")
    ok = {s: v for s, v in res.items() if "error" not in v}
    dec = lambda a: sum(1 for v in ok.values() if v[a][0] is not None)
    resc = [s for s, v in ok.items() if v["off"][0] is None and v["on"][0] is not None]
    lost = [s for s, v in ok.items() if v["off"][0] is not None and v["on"][0] is None]
    chg = [s for s, v in ok.items() if v["off"][0] is not None and v["on"][0] is not None and v["off"][0] != v["on"][0]]
    print("==", doc, "far heads", len(res), "| decided OFF", dec("off"), "ON", dec("on"), "| abstain OFF", len(ok) - dec("off"), "ON", len(ok) - dec("on"))
    print("   rescued:", len(resc), "sides", dict(collections.Counter(ok[s]["sides"] for s in resc)),
          "| decided -> abstain:", len(lost), "| decided -> other answer:", len(chg))
    Path(out).write_text(json.dumps(dict(doc=doc, res=res, rescued=resc, lost=lost, changed=chg), default=str))
