"""lane-farhead-2-9 (2026-10-07): the whole-population census of `look_where_it_must_be` OFF vs ON on every far head of a 10-07
record (replay of the extract, same raster and per-bar grid; GATHER+ADJUDICATE reading only, no gather). Writes
{subject: {off: [pos, reason], on: [pos, reason], how, sides, rung_dropped}} and prints decided / abstain counts before and after,
the abstains rescued by the look (and on how many sides the jut was found), decided -> abstain, and decided answers that changed.
CONTROL (can fail): the OFF arm's position must equal the record's own decided position (`fh`/`fh_abs`); the count printed.

  python3 farhead_2_9_census.py <x7 extract> <doc> <out.json> [--pages a,b]
"""
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import overnight_1004_report as R


def read(rep, data, s, on):
    D.FH.READER_KEYWORDS["look_where_it_must_be"] = on
    g, r, cap, gl, ctx = D.read_one(rep, data, s)
    nf = (r.get("detail") or {}).get("note_first") or {}
    return r, nf


if __name__ == "__main__":
    src, doc, out = sys.argv[1:4]
    pages = set(int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")) if "--pages" in sys.argv else None
    data, rep = D.load(src, doc)
    G = data["glyphs"]
    far = [s for s, g in G.items() if R.is_far(g) and "geo" in g and "box" in g and ("fh" in g or "fh_abs" in g)]
    far = [s for s in far if pages is None or R.page_of(s) in pages]
    far.sort(key=lambda s: tuple(int(v) for v in s.split("/")[1:]))
    res, errs = {}, 0
    for i, s in enumerate(far):
        try:
            r0, nf0 = read(rep, data, s, False)
            r1, nf1 = read(rep, data, s, True)
        except Exception as e:                      # noqa: BLE001 -- counted, never hidden
            errs += 1
            res[s] = dict(error=repr(e)[:120])
            continue
        look = nf1.get("hidden_ledger_look") or {}
        res[s] = dict(off=[r0["pos"], r0["reason"][:90]], on=[r1["pos"], r1["reason"][:90]], how=nf1.get("how"),
                      sides=look.get("sides"), looked=bool(look), between_off=nf0.get("between"), between_on=nf1.get("between"),
                      rec=(G[s].get("fh") or G[s].get("fh_abs") or {}).get("value"))
        if i % 500 == 0:
            print(i, "/", len(far), flush=True)
    ok = [v for v in res.values() if "error" not in v]
    dec = lambda arm: sum(1 for v in ok if v[arm][0] is not None)
    resc = [s for s, v in res.items() if "error" not in v and v["off"][0] is None and v["on"][0] is not None]
    lost = [s for s, v in res.items() if "error" not in v and v["off"][0] is not None and v["on"][0] is None]
    chg = [s for s, v in res.items() if "error" not in v and v["off"][0] is not None and v["on"][0] is not None and v["off"][0] != v["on"][0]]
    ctrl = sum(1 for v in ok if (v["rec"] == v["off"][0]) or (v["rec"] is None and v["off"][0] is None))
    print("==", doc, "far heads", len(far), "errors", errs, "| decided OFF", dec("off"), "ON", dec("on"), "| abstain OFF", len(ok) - dec("off"), "ON", len(ok) - dec("on"))
    print("   rescued (abstain -> decided):", len(resc), "by how:", dict(collections.Counter(res[s]["how"] for s in resc)),
          "jut sides found:", dict(collections.Counter(res[s]["sides"] for s in resc)))
    print("   decided -> abstain:", len(lost), "| decided -> other answer:", len(chg))
    print("   CONTROL: OFF arm equals the record's own position on", ctrl, "of", len(ok))
    Path(out).write_text(json.dumps(dict(doc=doc, res=res, rescued=resc, lost=lost, changed=chg), default=str))
