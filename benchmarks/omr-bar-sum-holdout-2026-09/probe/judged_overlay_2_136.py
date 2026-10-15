"""2.136 step 2: a small stand-in record for `judged score`, OFF and ON.

    python3 judged_overlay_2_136.py RECORD NEW_VERDICTS.json OUT_PREFIX

Streams the 6.8 GB record once (judged's own `iter_array`), keeps the `observations` and `verdicts` of
every subject the judged index names (any document), and writes
  OUT_PREFIX.off.json   exactly those rows (== the record, as far as judged looks)
  OUT_PREFIX.on.json    the same plus the verdicts the flag-ON rule admitted (each supersedes its prior).
Then `python3 -m tools.omr.staged.judged score OUT_PREFIX.{off,on}.json --doc brahms`.
The OFF overlay is checked against the full record by running judged on both (see FINDINGS).
"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged as J  # noqa: E402

rec, newp, pre = sys.argv[1:4]
idx = json.load(open(J.INDEX_PATH))
subjects = set()
for r in idx["tiles"]:
    subjects.update(r["subjects"] or ([r["subject"]] if r["subject"] else []))
obs = [o for o in J.iter_array(J.pathlib.Path(rec), "observations") if o.get("subject") in subjects]
ver = [v for v in J.iter_verdicts(J.pathlib.Path(rec))
       if v.get("subject") in subjects and v.get("quantity") in J._QUANTITIES]
new = [v for v in json.load(open(newp)) if v["subject"] in subjects]
json.dump({"observations": obs, "verdicts": ver}, open(pre + ".off.json", "w"))
json.dump({"observations": obs, "verdicts": ver + new}, open(pre + ".on.json", "w"))
print(len(subjects), "judged subjects;", len(obs), "obs;", len(ver), "verdicts;", len(new), "new verdicts on judged subjects")
