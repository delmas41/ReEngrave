"""2.331 pricing: re-adjudicate a saved ON-arm gathered record on THIS tree and re-export it traced (rg= glyph keys)."""
import sys, json, time, pathlib, subprocess
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
from tools.omr.staged.record_io import load_record, dump_to_file
from tools.omr.staged.review import rerun as RR
from tools.omr.staged import export as E
from tools.omr.staged.lane_report import traced_export

src, out_rec, out_xml = sys.argv[1:4]
t0 = time.time()
res = load_record(src)
rec = res.get("record", res)
print("top keys", list(res.keys())[:20], "record keys", list(rec.keys())[:20], flush=True)
n_old = len(rec.get("verdicts") or [])
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
newrec = log.to_json()
for k, v in rec.items():
    if k not in newrec and k != "verdicts":
        newrec[k] = v
result = {"record": newrec, "summary": log.summary()}
if "record" in res:
    for k, v in res.items():
        if k not in result:
            result[k] = v
print("old verdicts", n_old, "new", len(newrec["verdicts"]), "t", round(time.time() - t0), flush=True)
with traced_export():
    xml, report = E.to_musicxml(result)
pathlib.Path(out_xml).write_text(xml)
pathlib.Path(out_xml + ".report.json").write_text(json.dumps(report, default=str))
dump_to_file(result, out_rec)
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print("done", head, "t", round(time.time() - t0), flush=True)
