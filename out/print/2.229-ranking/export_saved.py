"""2.229: export a saved record's OWN verdicts (no re-adjudication) restricted to the loaded pages, through lane_report's traced export + parser.
usage: export_saved.py RECORD WORKDIR PLATE PAGES TAG"""
import json, pathlib, sys, time
from tools.omr.staged import lane_report as L, export as E
from tools.omr.staged.record_io import load_record
rec, work, plate, pages, tag = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3], {int(x) for x in sys.argv[4].split(",")}, sys.argv[5]
t0 = time.time()
res = load_record(rec)
r = res["record"] if "record" in res else res
if "record" not in res:
    res = {"record": res, "summary": {}}
keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
for k in ("observations", "abstentions", "verdicts"):
    r[k] = [x for x in r[k] if keep(x)]
boxes = L.glyph_boxes(r["observations"])
with L.traced_export():
    xml, report = E.to_musicxml(res)
sym = L.parse_symbols(xml, boxes)
red = report.get("bars_written_red") or {}
out = dict(plate=plate, arm=tag, mode="saved", hosts=sym["hosts"], loose=sym["loose"],
           red_bars=L._count(red.get("bars") if isinstance(red, dict) else red), bars_held_out=L._count(report.get("bars_held_out_sum")),
           notes_not_written=report.get("notes_not_written_total"), blue_marks=xml.count('color="%s"' % E.GUESS_COLOR), seconds=round(time.time() - t0, 1))
work.mkdir(parents=True, exist_ok=True)
(work / ("%s.%s.musicxml" % (plate, tag))).write_text(xml)
(work / ("%s.%s.symbols.json" % (plate, tag))).write_text(json.dumps(out, default=str))
(work / ("%s.%s.report.json" % (plate, tag))).write_text(json.dumps(report, default=str))
print("done", plate, tag, len(sym["hosts"]), "hosts", out["seconds"], "s")
