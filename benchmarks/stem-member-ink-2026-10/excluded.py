"""2.210: replay a plate's saved rows with the current tree and write every stem_value verdict whose reason is not_a_member, with its kind
(detail of the OTHER verdicts on the stem carries `beam_end_boxes`).  python3 excluded.py PLATE TAG OUT.json   (env flags as the shell has)"""
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
V = log.to_json()["verdicts"]
kinds = {}
for v in V:
    if v["quantity"] == "stem_value":
        for k, x in ((v.get("detail") or {}).get("beam_end_boxes") or {}).items():
            kinds[k] = x
nm = sorted({v["subject"] for v in V if v["quantity"] == "stem_value" and v.get("reason") == "not_a_member"})
json.dump(dict(plate=plate, not_a_member=nm, kinds=kinds), open(out, "w"), default=str)
print(plate, len(nm), len(kinds))
