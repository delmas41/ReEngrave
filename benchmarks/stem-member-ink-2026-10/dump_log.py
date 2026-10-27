"""ROADMAP 2.210 probe. Replay a plate's saved rows (tag, sample pages) through the stages with the current tree and dump the whole
log JSON (observations + verdicts) for offline analysis.   python3 dump_log.py PLATE TAG OUT.json"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import lane_report as LR
from tools.omr.staged.review import rerun as RR
plate, tag, out = sys.argv[1:4]
s = LR.load_sample()["plates"][plate]
keep = set(s["pages"]) | set(s.get("context_pages", []))
rec = LR.load_slices(LR.slice_dir(plate, tag))
for k in ("observations", "abstentions"):
    rec[k] = [r for r in rec[k] if LR.page_of(r.get("subject")) is None or LR.page_of(r.get("subject")) in keep]
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
json.dump(log.to_json(), open(out, "w"), default=str)
print(plate, "ok")
