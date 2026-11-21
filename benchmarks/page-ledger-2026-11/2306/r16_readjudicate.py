"""2.306 r16 control: ONE gather, re-adjudicated twice in this process's tree -- OMR_PAGE_STEMS off, then on -- and exported the way lane_report's
arm exports (the gather's own stored verdicts dropped first, as `lane_report --from adjudicate` does). Like with like: same gather, same pages,
same tree; only the flag at ADJUDICATE differs. Writes <out>/<plate>.<arm>.symbols.json and prints the diff by kind.
Usage: r16_readjudicate.py PLATE GATHERED.record.json OUTDIR PAGES(comma)"""
import os, sys, json, pathlib
sys.path.insert(0, os.getcwd())
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
from tools.omr.staged import export as E
from tools.omr.staged.review import rerun as RR

plate, recp, out, pages = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), [int(p) for p in sys.argv[4].split(',')]
out.mkdir(parents=True, exist_ok=True)
syms = {}
_got = {}
_orig_mc = E.marks_census


def _capture(rec, fates):
    _got["fates"] = dict(fates)
    return _orig_mc(rec, fates)


E.marks_census = _capture
fates_by_arm = {}
for arm, val in (("off", "0"), ("on", "1")):
    os.environ["OMR_PAGE_STEMS"] = val
    res = load_record(recp)
    rec = res.get("record", res)
    boxes = L.glyph_boxes(rec["observations"])
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    del res, rec
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    from tools.omr.staged.judged import _QUANTITIES as _JQ
    _obs = [o for o in result["record"]["observations"] if o.get("quantity") == "glyph_box"]
    (out / ("%s.%s.mini-record.json" % (plate, arm))).write_text(json.dumps(
        {"observations": _obs, "abstentions": [], "verdicts": [v for v in result["record"]["verdicts"] if v["quantity"] in _JQ]}))
    del log
    with L.traced_export():
        xml, _rep = E.to_musicxml(result)
    sym = L.parse_symbols(xml, boxes)
    cp = set(pages)
    sym["hosts"] = [h for h in sym["hosts"] if h.get("page") is None or h.get("page") in cp]
    sym["loose"] = [h for h in sym.get("loose", []) if h.get("page") is None or h.get("page") in cp]
    sym["red_bars"] = L._count(((_rep.get("bars_written_red") or {}).get("bars")))
    fates_by_arm[arm] = {k: v for k, v in _got.get("fates", {}).items() if k.startswith("glyph/") and int(k.split("/")[1]) in cp}
    (out / ("%s.%s.symbols.json" % (plate, arm))).write_text(json.dumps(sym))
    syms[arm] = sym
    del result
import pickle
pickle.dump(fates_by_arm, open(out / ("%s.fates.pkl" % plate), "wb"))
d = L.diff_arms(syms["off"], syms["on"], L.PLATES[plate]["unit"])
print(plate, "red bars", syms["off"].get("red_bars"), "->", syms["on"].get("red_bars"), "hosts", len(syms["off"]["hosts"]), "->", len(syms["on"]["hosts"]),
      {k: {kk: vv for kk, vv in v.items() if vv} for k, v in d["counts"].items() if any(v.values())})

jm = L.judged_moves(out / ("%s.off.mini-record.json" % plate), out / ("%s.on.mini-record.json" % plate), plate,
                    syms["off"]["hosts"], syms["on"]["hosts"])
print(plate, "judged:", {k: v for k, v in jm.items() if not isinstance(v, (list, dict))})
