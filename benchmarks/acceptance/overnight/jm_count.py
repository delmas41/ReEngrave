"""One streamed pass over a Litolff record: every stacked_head_duplicate refusal (with its ink pair), every stacked_head_fit
abstention. usage: jm_count.py RECORD OUT.json"""
import json
import sys

sys.path.insert(0, '.')
from tools.omr.staged.judged import iter_array

rec, out = sys.argv[1], sys.argv[2]
ref, ab = [], []
for v in iter_array(__import__("pathlib").Path(rec), "verdicts"):
    if v.get("quantity") == "notehead_is_not_a_notehead" and v.get("reason") == "stacked_head_duplicate":
        d = v.get("detail") or {}
        ref.append({"subject": v["subject"], "dup_of": d.get("duplicate_of"), "this": d.get("stacked_head_this_ink"),
                    "other": d.get("stacked_head_other_ink"), "cls": d.get("class"),
                    "sig": {k: d.get("stacked_head_signal", {}).get(k) for k in ("k", "near_miss", "class_decided_by_ink")}})
for a in iter_array(__import__("pathlib").Path(rec), "abstentions"):
    if a.get("quantity") == "stacked_head_fit":
        ab.append({"subject": a["subject"], "reason": a.get("reason"), "margin": (a.get("detail") or {}).get("margin")})
json.dump({"refusals": ref, "fit_abstentions": ab}, open(out, "w"))
print(len(ref), len(ab))
