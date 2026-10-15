"""2.137: re-decide ONLY `notehead_is_not_a_notehead` over a saved record, flag off then on.

    python3 benchmarks/omr-head-fill-2026-09/probe/2.137_redecide.py RECORD.json OUT.json

No gather, no re-run of the other deciders (`adjudicate.run(order=(that quantity,))`, the way the unit tests
drive it). CONTROL: the flag-OFF arm must reproduce the saved record's verdict counts for the quantity
(reason by reason); if it does not, the limited re-run is not the record's own decision and the arm is void.
Output: counts per arm, the control comparison, and every subject the flag newly refuses with its
margin, tightest axis and `refused_via`.
"""
import collections
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged import adjudicate, adjudicators  # noqa: E402,F401
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

rec_path, out_path = sys.argv[1], sys.argv[2]
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
saved = collections.Counter(
    (v["value"], v["reason"]) for v in rec["verdicts"]
    if v["quantity"] == "notehead_is_not_a_notehead")


def arm(flag):
    if flag:
        os.environ["OMR_SLASH_AT_STEM_END"] = "1"
    else:
        os.environ.pop("OMR_SLASH_AT_STEM_END", None)
    log, _ = RR.rebuild_gather(rec)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    out = {}
    for v in log._vrd.values():
        if v.quantity == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD:
            out[v.subject.to_key()] = v
    return out


base = arm(False)
base_map = {k: (v.value, v.reason) for k, v in base.items()}
base_counts = collections.Counter((v.value, v.reason) for v in base.values())
control = {"saved": {str(k): n for k, n in saved.items()},
           "off_arm": {str(k): n for k, n in base_counts.items()},
           "identical": dict(saved) == dict(base_counts)}
del base
arm_on = arm(True)
# per subject against the flag-OFF arm itself (the saved record differs from it only where a
# decider this limited run omits fed the verdict -- Brahms `is_a_meter_digit`, 30 subjects)
newly = []
for sub, v in arm_on.items():
    if v.value is True and base_map.get(sub, (None, None))[0] is not True:
        newly.append({"subject": sub, "reason": v.reason, "margin": v.margin,
                      "axis": (v.detail or {}).get("margin_axis"),
                      "via": (v.detail or {}).get("refused_via"),
                      "signal": (v.detail or {}).get("tremolo_slash_signal")})
lost = [s for s, (val, why) in base_map.items()
        if val is True and s in arm_on and arm_on[s].value is not True]
changed_reason = [{"subject": s, "was": base_map[s][1], "now": arm_on[s].reason}
                  for s in arm_on if base_map.get(s, (None, None))[0] is True
                  and arm_on[s].value is True and arm_on[s].reason != base_map[s][1]]
res = {"record": rec_path, "control": control,
       "on_counts": {str(k): n for k, n in collections.Counter(
           (v.value, v.reason) for v in arm_on.values()).items()},
       "newly_refused": newly, "refused_off_arm_but_kept_now": lost,
       "refused_both_but_reason_changed": changed_reason}
json.dump(res, open(out_path, "w"), indent=1, default=str)
print("control identical:", control["identical"], "| newly refused:", len(newly),
      "| lost refusals:", len(lost))
