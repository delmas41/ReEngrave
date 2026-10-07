import math
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
            led_abs.setdefault(a["subject"], a)

    near = []
    for s, raw in pos_by_subj.items():
        bd = boundary_distance(raw)
        if bd <= MARGIN and s in led_obs or s in led_abs:
            if bd <= MARGIN:
                near.append((s, raw, bd))

    print(f"=== {name}: {len(near)} near-boundary far heads (<= {MARGIN}) ===")
    n_obs = sum(1 for s, _, _ in near if s in led_obs)
    n_abs = sum(1 for s, _, _ in near if s in led_abs)
    n_neither = len(near) - n_obs - n_abs
    print(f"  ledger reading present: {n_obs}, abstained: {n_abs}, neither row: {n_neither}")

    pitch_v = {v["subject"]: v for v in rec["verdicts"]
              if v["quantity"] == "pitch" and v["decider"] == "restate_pitch"}
    changed = []
    for s, raw, bd in near:
        v = pitch_v.get(s)
        if v is None:
            continue
        old_step = int(round(raw))
        old_pitch = _pitch_from_position(old_step, "treble")
        if v["reason"] == "position_and_clef_ledger":
            changed.append((s, raw, bd, led_obs[s]["value"],
                           led_obs[s]["detail"].get("bracket"),
                           old_pitch, v["value"]))
    print(f"  substituted (ledger won the tiebreak): {len(changed)}")
    for c in changed:
        print("   ", c)
    reasons = {}
    for s, raw, bd in near:
        v = pitch_v.get(s)
        r = v["reason"] if v else None
        reasons[r] = reasons.get(r, 0) + 1
    print("  reasons among near-boundary heads:", reasons)
