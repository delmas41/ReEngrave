"""2.277 held-tile probe: re-adjudicate ONLY some pages of a saved slice (flag per env), dump every verdict / observation row whose subject contains a prefix.
usage: place_diff.py PLATE TAG OUT.json PAGES(comma) PREFIX [PREFIX...]     e.g. brahms 20261104-night out.json 0,8 /8/0/8/
Also writes the exported MusicXML next to OUT (OUT.musicxml) so a bar can be read."""
import json, os, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import lane_report as LR
from tools.omr.staged.review import rerun as RR

plate, tag, out, pages = sys.argv[1:5]
prefixes = sys.argv[5:]
keep = {int(p) for p in pages.split(",")}
rec = LR.load_slices(LR.slice_dir(plate, tag))
for k in ("observations", "abstentions", "verdicts"):
    rec[k] = [r for r in rec[k] if LR.page_of(r.get("subject")) is None or LR.page_of(r.get("subject")) in keep]
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
res = {"record": log.to_json(), "summary": log.summary()}
rows = []
for kind in ("verdicts", "observations"):
    for r in res["record"][kind]:
        s = r["subject"]
        if any(p in s for p in prefixes):
            v = r.get("value")
            rows.append([kind, r["id"], s, r["quantity"], r.get("outcome"), v if not isinstance(v, (dict, list)) else json.dumps(v)[:160], r.get("reason"),
                         json.dumps(r.get("detail"))[:300] if kind == "verdicts" else None])
json.dump(rows, open(out, "w"))
from tools.omr.staged import export as E
xml, report = E.to_musicxml(res)
open(out + ".musicxml", "w").write(xml)
json.dump({k: report.get(k) for k in report if k in ("bars_written_red", "notes_not_written_total", "partial_bars", "red_bars", "bars_held_out", "bars_held_out_sum")}, open(out + ".report.json", "w"), default=str)
print("rows", len(rows), "xml", len(xml))
