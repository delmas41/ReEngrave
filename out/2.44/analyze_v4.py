import collections
from tools.omr.staged import record_io
from tools.omr.pitch_resolver import _pitch_from_position

MARGIN = 0.15


def boundary_distance(raw):
    return 0.5 - abs(raw - round(raw))


for name, path in [("Litolff p3", "out/2.44/litolff-p3-arm2.json"),
                    ("Brahms p1", "out/2.44/brahms-p1-arm2.json")]:
    rec = record_io.load_record(path)["record"]
    pos_by_subj = {o["subject"]: o["value"] for o in rec["observations"]
                  if o["quantity"] == "notehead_staff_position"}
    led_obs = {o["subject"]: o for o in rec["observations"]
              if o["quantity"] == "ledger_printed_position"}
    led_abs = {}
    for a in rec["abstentions"]:
        if a["quantity"] == "ledger_printed_position":
            led_abs.setdefault(a["subject"], a["reason"])

    far_subjects = set(led_obs) | set(led_abs)
    near_far = [(s, pos_by_subj[s], boundary_distance(pos_by_subj[s]))
               for s in far_subjects if s in pos_by_subj
               and boundary_distance(pos_by_subj[s]) <= MARGIN]

    print(f"=== {name}: {len(far_subjects)} far heads total, "
         f"{len(near_far)} of them near-boundary (<= {MARGIN}) ===")
    n_obs = sum(1 for s, _, _ in near_far if s in led_obs)
    reasons_abs = collections.Counter(led_abs[s] for s, _, _ in near_far
                                      if s in led_abs)
    print(f"  ledger reading present: {n_obs} / {len(near_far)}")
    print("  abstain reasons:", dict(reasons_abs))

    pitch_v = {v["subject"]: v for v in rec["verdicts"]
              if v["quantity"] == "pitch" and v["decider"] == "restate_pitch"}
    reason_counts = collections.Counter()
    substitutions = []
    for s, raw, bd in near_far:
        v = pitch_v.get(s)
        r = v["reason"] if v else "no_pitch_verdict"
        reason_counts[r] += 1
        if r == "position_and_clef_ledger":
            substitutions.append((s, raw, bd, led_obs[s]["value"],
                                  int(round(raw)), v["value"]))
    print("  final restate_pitch reasons:", dict(reason_counts))
    print(f"  genuine substitutions: {len(substitutions)}")
    for row in substitutions:
        print("   ", row)
